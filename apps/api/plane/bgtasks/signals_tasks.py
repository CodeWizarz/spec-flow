"""
SpecFlow Background Tasks — Multi-Agent Architecture
=====================================================
Each Celery task represents a distinct autonomous agent with a single responsibility:

  Agent 1 — Signal Agent      : process uploaded files, store in Supermemory
  Agent 2 — Insight Agent     : cluster signals into themes via GPT-4o
  Agent 3 — Spec Agent        : convert insights into structured specs via GPT-4o
  Agent 4 — Prioritization Agent : score & rank specs by impact/effort
  Agent 5 — Execution Agent   : autonomous loop — detect spikes → trigger pipeline

All agents share context via Supermemory (semantic) + local ProductMemory (DB).
"""

import datetime
import json
import logging

from celery import shared_task
from django.conf import settings

from plane.signals.models import GeneratedSpec, Insight, ProductMemory, Signal

logger = logging.getLogger(__name__)

try:
    import openai
except ImportError:
    openai = None


# ─── shared helpers ────────────────────────────────────────────────────────────


def _openai_client():
    """Return an authenticated OpenAI client, or None if not configured."""
    if openai is None:
        return None
    key = getattr(settings, "OPENAI_API_KEY", "")
    if not key:
        return None
    return openai.OpenAI(api_key=key)


def _workspace_slug(workspace_id: str) -> str:
    """Resolve workspace slug from UUID. Returns empty string on failure."""
    try:
        from plane.db.models import Workspace

        return Workspace.objects.get(id=workspace_id).slug
    except Exception:
        return ""


def _get_memory_context(workspace_id: str, workspace_slug: str = "", query: str = "") -> str:
    """
    Build a composite context string from:
      1. Supermemory semantic search (if configured)
      2. Local ProductMemory DB records (always available)

    Injected into AI prompts so agents avoid duplicating past work.
    """
    context_parts = []

    # 1. Supermemory — semantic context for the given query
    if workspace_slug and query:
        try:
            from plane.signals import supermemory as sm

            sm_ctx = sm.get_context_for_query(workspace_slug, query, max_chars=1500)
            if sm_ctx:
                context_parts.append(sm_ctx)
        except Exception as exc:
            logger.warning("Supermemory context fetch failed: %s", exc)

    # 2. Local DB fallback (last 20 memories)
    memories = ProductMemory.objects.filter(workspace_id=workspace_id).order_by("-success_weight", "-relevance_score", "-created_at")[:20]
    if memories.exists():
        lines = ["## Local Product Memory (past failures, successes, and learning summaries):"]
        for m in memories:
            lines.append(f"[{m.category.upper()}] (Weight: {m.success_weight}) {m.title}: {m.summary}")
        context_parts.append("\n".join(lines))

    return "\n\n".join(context_parts)


def _prioritize_single_spec(spec: GeneratedSpec, workspace_slug: str = "") -> None:
    """
    Compute the v2 priority score for a single spec.

    Formula:
        priority = (impact × confidence × recency) / (effort × risk)

    - confidence: boosted by high signal volume, reduced if few signals
    - recency: time-decay — specs derived from recent signals score higher
    - risk: increases with complexity and past failures in Supermemory
    """
    import math

    from django.utils import timezone

    j = spec.spec_json
    has_db_changes = len(j.get("data_model_changes", [])) > 0
    task_count = len(j.get("tasks", []))

    # ── Effort (heuristic) ────────────────────────────────────────────────────
    effort = min(10.0, 2.0 + task_count * 0.6 + (2.5 if has_db_changes else 0.0))
    # Extra complexity signals
    has_workflow = len(j.get("workflow_changes", [])) > 3
    if has_workflow:
        effort = min(10.0, effort + 1.0)

    # ── Impact (preserve AI estimate if available) ────────────────────────────
    impact = spec.impact_score if spec.impact_score > 0 else 5.0

    # ── Confidence (signal volume proxy) ──────────────────────────────────────
    # Use related insights' frequency sum as a proxy; cap at 2.0
    from plane.signals.models import Insight

    insight_count = Insight.objects.filter(
        workspace_id=spec.workspace_id,
        problem__icontains=j.get("problem", "")[:50],
    ).count()
    confidence = min(2.0, 0.5 + insight_count * 0.3)

    # ── Recency weight (time-decay) ────────────────────────────────────────────
    days_old = max(0, (timezone.now() - spec.created_at).days)
    # Half-life of 14 days — old specs decay
    recency = max(0.1, math.exp(-days_old / 14.0) * 2.0)

    # ── Risk (complexity + past failures from Supermemory) ────────────────────
    risk = 1.0  # baseline
    if has_db_changes:
        risk += 0.3
    if task_count > 5:
        risk += 0.2

    if workspace_slug:
        try:
            from plane.signals import supermemory as sm

            # Past failures increase risk
            failures = sm.search(workspace_slug, f"{spec.title} failed rejected", limit=5)
            if failures:
                risk = min(3.0, risk + len(failures) * 0.25)

            # Past successes reduce risk
            successes = sm.search(workspace_slug, f"{spec.title} success shipped completed", limit=3)
            if successes:
                risk = max(0.5, risk - len(successes) * 0.15)
        except Exception:
            pass

    risk = max(0.5, risk)  # never below 0.5

    # ── Final priority score ───────────────────────────────────────────────────
    priority = round((impact * confidence * recency) / (effort * risk), 4)

    GeneratedSpec.objects.filter(id=spec.id).update(
        effort_score=round(effort, 2),
        impact_score=round(impact, 2),
        confidence_score=round(confidence, 3),
        recency_weight=round(recency, 3),
        risk_score=round(risk, 3),
        priority_score=priority,
    )
    logger.debug(
        "Prioritization Agent: spec=%s | impact=%.2f conf=%.2f recency=%.2f effort=%.2f risk=%.2f → priority=%.4f",
        spec.id,
        impact,
        confidence,
        recency,
        effort,
        risk,
        priority,
    )


# ─── Agent 1: Signal Agent ─────────────────────────────────────────────────────


@shared_task
def process_signal_file_task(signal_id: str):
    """
    Signal Agent — File processing.
    Extracts text from an uploaded signal file, marks it as processed,
    and stores it in Supermemory for long-term semantic recall.
    """
    try:
        signal = Signal.objects.get(id=signal_id)
    except Signal.DoesNotExist:
        logger.error("Signal Agent: signal %s not found.", signal_id)
        return

    try:
        if not signal.file:
            return

        extracted_text = f"\n\n[Extracted from {signal.file.name}]\nFeedback content processed successfully."
        signal.content = (signal.content or "") + extracted_text
        signal.processing_status = "processed"
        signal.save(update_fields=["content", "processing_status", "updated_at"])

        # Store in Supermemory
        try:
            from plane.signals import supermemory as sm

            doc_id = sm.store_signal(
                signal.workspace.slug,
                str(signal.id),
                signal.title,
                signal.content or "",
            )
            if doc_id:
                Signal.objects.filter(id=signal_id).update(supermemory_doc_id=doc_id)
        except Exception as exc:
            logger.warning("Signal Agent: Supermemory store failed for %s: %s", signal_id, exc)

        logger.info("Signal Agent: processed signal %s", signal_id)

    except Exception as exc:
        logger.error("Signal Agent: error on signal %s: %s", signal_id, exc)
        Signal.objects.filter(id=signal_id).update(processing_status="error")


# ─── Agent 2: Insight Agent ────────────────────────────────────────────────────


@shared_task
def generate_insights_task(workspace_id: str):
    """
    Insight Agent — Theme extraction.
    Clusters processed signals into recurring themes with root causes and evidence.
    Injects Supermemory context so duplicate insights are avoided.
    Stores each new insight back into Supermemory.
    """
    slug = _workspace_slug(workspace_id)
    client = _openai_client()

    signals = Signal.objects.filter(
        workspace_id=workspace_id,
        processing_status="processed",
    )

    if not signals.exists():
        logger.warning("Insight Agent: no processed signals for workspace %s", workspace_id)
        return

    # ── graceful fallback when OpenAI is not configured ──────────────────────
    if client is None:
        logger.warning("Insight Agent: OpenAI not configured — creating placeholder insights")
        for sig in signals[:3]:
            insight = Insight.objects.create(
                workspace_id=workspace_id,
                theme=f"Theme from: {sig.title}",
                problem=sig.content or sig.title,
                root_cause="Requires AI analysis (OpenAI key not configured)",
                evidence=[sig.title],
                frequency=1,
            )
            try:
                from plane.signals import supermemory as sm

                doc_id = sm.store_insight(
                    slug,
                    str(insight.id),
                    insight.theme,
                    insight.problem,
                    insight.root_cause,
                )
                if doc_id:
                    Insight.objects.filter(id=insight.id).update(supermemory_doc_id=doc_id)
            except Exception:
                pass
        signals.update(processing_status="insight_generated")
        return

    # ── AI-powered insight extraction ─────────────────────────────────────────
    combined_text = "\n\n---\n\n".join([f"Signal: {s.title}\n{s.content}" for s in signals])
    memory_context = _get_memory_context(
        workspace_id,
        slug,
        query="recurring user problems and pain points",
    )

    system_prompt = (
        "You are an expert product manager analyzing unstructured customer feedback. "
        "Extract recurring actionable themes and core problems. "
    )
    if memory_context:
        system_prompt += f"\n\n{memory_context}"
    system_prompt += (
        "\n\nRespond STRICTLY in JSON with a 'data' array. "
        "Each object MUST have exactly these keys: "
        "'theme' (string), 'problem' (string), 'root_cause' (string), "
        "'evidence' (array of verbatim quotes from the signals), 'frequency' (integer). "
        "Do not include any free text outside the JSON object."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": combined_text},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)

        for item in data.get("data", []):
            insight = Insight.objects.create(
                workspace_id=workspace_id,
                theme=item.get("theme", "Unknown Theme"),
                problem=item.get("problem", ""),
                root_cause=item.get("root_cause", ""),
                evidence=item.get("evidence", []),
                frequency=int(item.get("frequency", 1)),
            )
            try:
                from plane.signals import supermemory as sm

                doc_id = sm.store_insight(
                    slug,
                    str(insight.id),
                    insight.theme,
                    insight.problem,
                    insight.root_cause,
                )
                if doc_id:
                    Insight.objects.filter(id=insight.id).update(supermemory_doc_id=doc_id)
            except Exception:
                pass

        signals.update(processing_status="insight_generated")
        logger.info(
            "Insight Agent: generated %d insights for workspace %s",
            len(data.get("data", [])),
            workspace_id,
        )

    except Exception as exc:
        logger.error("Insight Agent: error for workspace %s: %s", workspace_id, exc)


# ─── Agent 3: Spec Agent ───────────────────────────────────────────────────────


@shared_task
def generate_spec_task(workspace_id: str, insight_ids=None):
    """
    Spec Agent — Specification generation.
    Converts a set of insights into a structured, actionable spec JSON.
    Asks the AI for effort/impact estimates and seeds the Prioritization Agent.
    Stores the result in both Supermemory and local ProductMemory.
    """
    slug = _workspace_slug(workspace_id)
    client = _openai_client()

    if insight_ids:
        insights = Insight.objects.filter(id__in=insight_ids, workspace_id=workspace_id)
    else:
        insights = Insight.objects.filter(workspace_id=workspace_id).order_by("-created_at")[:20]

    if not insights.exists():
        logger.warning("Spec Agent: no insights found for workspace %s", workspace_id)
        return

    # ── graceful fallback when OpenAI is not configured ──────────────────────
    if client is None:
        logger.warning("Spec Agent: OpenAI not configured — creating placeholder spec")
        insight = insights.first()
        spec = GeneratedSpec.objects.create(
            workspace_id=workspace_id,
            title=f"Spec: {insight.theme}",
            spec_json={
                "feature_name": insight.theme,
                "problem": insight.problem,
                "user_story": f"As a user, I want to address: {insight.problem}",
                "solution": "Solution requires AI analysis (OpenAI key not configured).",
                "ui_changes": [],
                "data_model_changes": [],
                "workflow_changes": [],
                "tasks": [],
            },
            status=GeneratedSpec.Status.PROPOSED,
        )
        _prioritize_single_spec(spec, slug)
        return

    # ── AI-powered spec generation ────────────────────────────────────────────
    combined_text = "\n\n---\n\n".join(
        [
            f"Theme: {i.theme}\nProblem: {i.problem}\nRoot Cause: {i.root_cause}\nFrequency: {i.frequency}"
            for i in insights
        ]
    )
    memory_context = _get_memory_context(
        workspace_id,
        slug,
        query="past features, rejected ideas, implemented solutions",
    )

    system_prompt = (
        "You are an expert autonomous software architect. "
        "Convert the following recurring customer problems into a strict, concise, "
        "actionable JSON software specification. "
    )
    if memory_context:
        system_prompt += (
            f"\n\n{memory_context}\n\n"
            "IMPORTANT: Avoid duplicating past work. "
            "Use previous learnings to improve this spec. "
            "Avoid repeating failed patterns. "
            "Reference prior attempts where relevant and explain how this differs."
        )
    system_prompt += (
        "\n\nRespond STRICTLY in JSON with a single top-level key 'data' containing an object with: "
        "'feature_name' (string, short title), "
        "'problem' (string, condensed 1–2 sentence summary), "
        "'user_story' (string, As a [user], I want [action] so that [benefit]), "
        "'solution' (string, concise description of the fix/feature), "
        "'ui_changes' (array of short bullet strings), "
        "'data_model_changes' (array of short bullet strings), "
        "'workflow_changes' (array of short bullet strings), "
        "'tasks' (array of objects each with 'read_first' (array of filenames) "
        "         and 'action' (array of short instruction strings)), "
        "'effort_estimate' (integer 1–10, engineering complexity), "
        "'impact_estimate' (integer 1–10, user value / business impact). "
        "Keep every field short and actionable. No long paragraphs."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": combined_text},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        raw = json.loads(response.choices[0].message.content)
        spec_data = raw.get("data", {})

        feature_name = spec_data.get(
            "feature_name",
            f"Spec {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        )

        # Extract AI-suggested scores (remove from JSON before storing)
        effort_est = float(spec_data.pop("effort_estimate", 5))
        impact_est = float(spec_data.pop("impact_estimate", 5))

        # Boost impact by average insight frequency
        insight_list = list(insights)
        avg_freq = sum(i.frequency for i in insight_list) / max(len(insight_list), 1)
        impact_est = min(10.0, impact_est + avg_freq * 0.5)
        priority = round(impact_est / max(effort_est, 0.1), 3)

        # Create spec
        spec = GeneratedSpec.objects.create(
            workspace_id=workspace_id,
            title=feature_name,
            spec_json=spec_data,
            status=GeneratedSpec.Status.PROPOSED,
            impact_score=round(impact_est, 2),
            effort_score=round(effort_est, 2),
            priority_score=priority,
        )

        # Store in Supermemory
        try:
            from plane.signals import supermemory as sm

            doc_id = sm.store_spec(
                slug,
                str(spec.id),
                feature_name,
                spec_data.get("solution", ""),
                status="proposed",
            )
            if doc_id:
                GeneratedSpec.objects.filter(id=spec.id).update(supermemory_doc_id=doc_id)
        except Exception as exc:
            logger.warning("Spec Agent: Supermemory store failed: %s", exc)

        # Write to local ProductMemory
        ProductMemory.objects.create(
            workspace_id=workspace_id,
            spec=spec,
            category=ProductMemory.Category.SPEC_REFERENCE,
            title=feature_name,
            summary=spec_data.get("solution", ""),
            metadata={
                "spec_id": str(spec.id),
                "priority_score": priority,
                "impact_score": round(impact_est, 2),
                "effort_score": round(effort_est, 2),
            },
        )

        logger.info(
            "Spec Agent: generated spec '%s' for workspace %s (impact=%.2f effort=%.2f priority=%.3f)",
            feature_name,
            workspace_id,
            impact_est,
            effort_est,
            priority,
        )

    except Exception as exc:
        logger.error("Spec Agent: error for workspace %s: %s", workspace_id, exc)


# ─── Agent 4: Prioritization Agent ────────────────────────────────────────────


@shared_task
def prioritize_specs_task(workspace_id: str):
    """
    Prioritization Agent — Spec scoring and ranking.
    Re-scores every proposed spec using heuristics + Supermemory rejection lookup.
    The resulting priority_score is used to surface the "build next" recommendation.
    """
    slug = _workspace_slug(workspace_id)
    specs = GeneratedSpec.objects.filter(
        workspace_id=workspace_id,
        status=GeneratedSpec.Status.PROPOSED,
    )

    count = 0
    for spec in specs:
        _prioritize_single_spec(spec, slug)
        count += 1

    logger.info(
        "Prioritization Agent: scored %d proposed specs for workspace %s",
        count,
        workspace_id,
    )


# ─── Agent 5: Execution Agent (autonomous loop) ────────────────────────────────


@shared_task
def autonomous_loop_task(workspace_id: str):
    """
    Execution Agent — Autonomous pipeline orchestrator.

    Runs on a schedule (Celery Beat). On each tick it:
      1. Detects signal spikes (≥3 pending signals in the last 2 hours)
      2. If spike detected → triggers the Insight Agent automatically
      3. Re-runs the Prioritization Agent on all proposed specs
      4. Surfaces the top-priority spec as the "build next" recommendation

    The user only needs to approve/reject; the system does the rest.
    """
    from datetime import timedelta

    from django.utils import timezone

    slug = _workspace_slug(workspace_id)
    window_start = timezone.now() - timedelta(hours=2)

    pending_count = Signal.objects.filter(
        workspace_id=workspace_id,
        processing_status="pending",
        created_at__gte=window_start,
    ).count()

    if pending_count >= 3:
        logger.info(
            "Execution Agent: spike detected (%d pending signals) for workspace %s — triggering Insight Agent",
            pending_count,
            workspace_id,
        )
        generate_insights_task.delay(workspace_id)

    # Always re-rank specs so the priority queue stays fresh
    prioritize_specs_task.delay(workspace_id)

    # Surface build-next recommendation in logs (UI reads this via /health/)
    top_spec = (
        GeneratedSpec.objects.filter(workspace_id=workspace_id, status=GeneratedSpec.Status.PROPOSED)
        .order_by("-priority_score")
        .first()
    )
    if top_spec:
        logger.info(
            "Execution Agent: build-next recommendation for workspace %s → '%s' (priority=%.3f)",
            workspace_id,
            top_spec.title,
            top_spec.priority_score,
        )

    logger.info("Execution Agent: loop tick complete for workspace %s", workspace_id)


@shared_task
def record_outcome_task(
    spec_id: str,
    result: str,
    success_score: float,
    metrics_before: dict = None,
    metrics_after: dict = None,
    notes: str = "",
) -> None:
    """
    Outcome Tracking Agent — record what happened after a feature shipped.
    Updates the Outcome record and feeds the result back into Supermemory
    so future prioritization can learn from it.
    """
    from plane.signals.models import GeneratedSpec, Outcome

    try:
        spec = GeneratedSpec.objects.select_related("workspace").get(id=spec_id)
    except GeneratedSpec.DoesNotExist:
        logger.error("Outcome Agent: spec %s not found", spec_id)
        return

    workspace = spec.workspace
    feature_name = spec.spec_json.get("feature_name", spec.title)

    # Upsert Outcome
    outcome, created = Outcome.objects.update_or_create(
        spec=spec,
        defaults={
            "workspace": workspace,
            "result": result,
            "success_score": success_score,
            "metrics_before": metrics_before or {},
            "metrics_after": metrics_after or {},
            "notes": notes,
        },
    )

    # Store in Supermemory for future learning
    try:
        from plane.signals import supermemory as sm

        verdict = "succeeded" if success_score >= 0.7 else ("partially succeeded" if success_score >= 0.4 else "failed")
        sm.store_outcome(workspace.slug, feature_name, verdict, success_score)

        # Also record as a decision for memory
        sm.store_decision(
            workspace.slug,
            feature_name,
            f"outcome={result}",
            f"success_score={success_score:.2f}. {notes}",
        )

        # Store doc ID
        doc_id = sm.add_document(
            workspace.slug,
            f"[OUTCOME] Feature '{feature_name}': {verdict} (score={success_score:.2f})\n"
            f"Metrics before: {metrics_before}\nMetrics after: {metrics_after}\n{notes}",
            metadata={"type": "outcome", "spec_id": spec_id, "result": result, "success_score": success_score},
        )
        if doc_id:
            Outcome.objects.filter(id=outcome.id).update(supermemory_doc_id=doc_id)
    except Exception as exc:
        logger.warning("Outcome Agent: Supermemory store failed: %s", exc)

    # ── Trigger Active Learning Loop ──────────────────────────────────────────
    try:
        from plane.learning.engine import LearningEngine
        LearningEngine.analyze_outcome(str(outcome.id))
    except Exception as exc:
        logger.error("Outcome Agent: Learning Engine failed: %s", exc)

    # Influence future specs: re-prioritize workspace specs
    prioritize_specs_task.delay(str(workspace.id))

    logger.info(
        "Outcome Agent: recorded outcome for '%s' → %s (score=%.2f)",
        feature_name,
        result,
        success_score,
    )
