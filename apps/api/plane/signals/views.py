import hashlib
import hmac

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from plane.bgtasks.signals_tasks import (
    generate_insights_task,
    generate_spec_task,
    prioritize_specs_task,
    process_signal_file_task,
)
from plane.db.models import Workspace
from plane.signals.models import GeneratedSpec, Insight, Outcome, ProductMemory, Signal, SpecIssue
from plane.signals.serializers import (
    GeneratedSpecSerializer,
    InsightSerializer,
    OutcomeSerializer,
    ProductMemorySerializer,
    SignalSerializer,
    SpecIssueSerializer,
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class WorkspaceSignalViewSet(viewsets.ModelViewSet):
    serializer_class = SignalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Signal.objects.filter(workspace__slug=self.kwargs.get("slug")).order_by("-created_at")

    def perform_create(self, serializer):
        workspace = get_object_or_404(Workspace, slug=self.kwargs.get("slug"))
        instance = serializer.save(workspace=workspace)
        if instance.file:
            process_signal_file_task.delay(str(instance.id))

    @action(detail=False, methods=["post"])
    def generate(self, request, slug):
        workspace = get_object_or_404(Workspace, slug=slug)
        generate_insights_task.delay(str(workspace.id))
        return Response({"message": "Insights generation queued"})


class WorkspaceInsightViewSet(viewsets.ModelViewSet):
    serializer_class = InsightSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Insight.objects.filter(workspace__slug=self.kwargs.get("slug")).order_by("-created_at")


class WorkspaceSpecViewSet(viewsets.ModelViewSet):
    serializer_class = GeneratedSpecSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return GeneratedSpec.objects.filter(workspace__slug=self.kwargs.get("slug")).order_by("-created_at")

    @action(detail=False, methods=["post"])
    def generate(self, request, slug):
        workspace = get_object_or_404(Workspace, slug=slug)
        insight_ids = request.data.get("insight_ids", None)
        generate_spec_task.delay(str(workspace.id), insight_ids)
        return Response({"message": "Spec generation queued"})

    @action(detail=True, methods=["patch"])
    def update_status(self, request, slug, pk):
        spec = get_object_or_404(GeneratedSpec, pk=pk, workspace__slug=slug)
        new_status = request.data.get("status")
        valid = [c[0] for c in GeneratedSpec.Status.choices]
        if new_status not in valid:
            return Response({"error": f"Invalid status. Must be one of: {valid}"}, status=400)
        spec.status = new_status
        spec.save(update_fields=["status", "updated_at"])

        # If completed → add to product memory
        if new_status == GeneratedSpec.Status.COMPLETED:
            feature_name = spec.spec_json.get("feature_name", spec.title)
            ProductMemory.objects.get_or_create(
                workspace=spec.workspace,
                spec=spec,
                defaults={
                    "category": ProductMemory.Category.SHIPPED,
                    "title": feature_name,
                    "summary": spec.spec_json.get("solution", ""),
                    "metadata": {"spec_id": str(spec.id)},
                },
            )
            # Generate "Feature shipped" signal to close the loop
            Signal.objects.create(
                workspace=spec.workspace,
                title=f"Feature shipped: {feature_name}",
                content=f"Spec '{feature_name}' was marked completed. Solution: {spec.spec_json.get('solution', '')}",
                source="system",
                processing_status="processed",
            )

        if new_status == GeneratedSpec.Status.REJECTED:
            feature_name = spec.spec_json.get("feature_name", spec.title)
            ProductMemory.objects.get_or_create(
                workspace=spec.workspace,
                spec=spec,
                defaults={
                    "category": ProductMemory.Category.REJECTED,
                    "title": feature_name,
                    "summary": spec.spec_json.get("problem", ""),
                    "metadata": {"spec_id": str(spec.id), "reason": request.data.get("reason", "")},
                },
            )

        return Response(GeneratedSpecSerializer(spec).data)

    @action(detail=True, methods=["post"])
    def agent_payload(self, request, slug, pk):
        """Generate and return a structured agent prompt for Cursor / Claude Code."""
        spec = get_object_or_404(GeneratedSpec, pk=pk, workspace__slug=slug)
        j = spec.spec_json

        tasks = j.get("tasks", [])
        payload = {
            "feature_name": j.get("feature_name", spec.title),
            "problem": j.get("problem", ""),
            "user_story": j.get("user_story", ""),
            "solution": j.get("solution", ""),
            "files": sorted({f for t in tasks for f in t.get("read_first", [])}),
            "tasks": tasks,
            "instructions": [
                f"Implement: {j.get('feature_name', spec.title)}",
                f"Problem to solve: {j.get('problem', '')}",
                "Follow the task list strictly. Edit only the files listed in read_first.",
                "Do not change unrelated files.",
                "After completing all tasks, run tests if available.",
            ],
            "prompt": _build_agent_prompt(j, spec.title),
        }

        spec.agent_payload = payload
        spec.save(update_fields=["agent_payload", "updated_at"])
        return Response(payload)

    @action(detail=True, methods=["post"])
    def create_issue(self, request, slug, pk):
        """Create a SpecIssue linked to this spec."""
        spec = get_object_or_404(GeneratedSpec, pk=pk, workspace__slug=slug)
        workspace = spec.workspace

        title = request.data.get("title") or spec.spec_json.get("feature_name", spec.title)
        description = request.data.get("description") or spec.spec_json.get("solution", "")
        assignee_email = request.data.get("assignee_email", "")

        issue = SpecIssue.objects.create(
            workspace=workspace,
            spec=spec,
            title=title,
            description=description,
            assignee_email=assignee_email or None,
            status=SpecIssue.Status.TODO,
        )
        # Move spec to in_progress if still proposed
        if spec.status == GeneratedSpec.Status.PROPOSED:
            spec.status = GeneratedSpec.Status.IN_PROGRESS
            spec.save(update_fields=["status", "updated_at"])

        return Response(SpecIssueSerializer(issue).data, status=201)

    @action(detail=True, methods=["post"])
    def execute(self, request, slug, pk):
        """
        Execute Agent: generate code, create branch, open PR.
        POST /api/workspaces/<slug>/specs/<pk>/execute/
        """
        spec = get_object_or_404(GeneratedSpec, pk=pk, workspace__slug=slug)

        if spec.execution_status in ("generating", "pending"):
            return Response(
                {"error": "Execution already in progress", "execution_status": spec.execution_status},
                status=400,
            )

        from plane.execution.agent import execute_spec_task

        execute_spec_task.delay(str(spec.id), triggered_by=str(request.user.id))

        GeneratedSpec.objects.filter(id=pk).update(execution_status="pending")
        return Response(
            {
                "message": "Execution queued",
                "spec_id": str(spec.id),
                "execution_status": "pending",
            },
            status=202,
        )


class WorkspaceSpecIssueViewSet(viewsets.ModelViewSet):
    serializer_class = SpecIssueSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SpecIssue.objects.filter(
            workspace__slug=self.kwargs.get("slug"),
            spec_id=self.kwargs.get("spec_pk"),
        ).order_by("created_at")

    def perform_create(self, serializer):
        workspace = get_object_or_404(Workspace, slug=self.kwargs.get("slug"))
        spec = get_object_or_404(GeneratedSpec, pk=self.kwargs.get("spec_pk"), workspace=workspace)
        serializer.save(workspace=workspace, spec=spec)

    @action(detail=True, methods=["patch"])
    def update_status(self, request, slug, spec_pk, pk):
        issue = get_object_or_404(SpecIssue, pk=pk, spec_id=spec_pk, workspace__slug=slug)
        new_status = request.data.get("status")
        valid = [c[0] for c in SpecIssue.Status.choices]
        if new_status not in valid:
            return Response({"error": f"Invalid status. Must be one of: {valid}"}, status=400)

        issue.status = new_status
        issue.save(update_fields=["status", "updated_at"])

        # If done → close the loop: generate signal + check if spec can be completed
        if new_status == SpecIssue.Status.DONE:
            spec = issue.spec
            feature_name = spec.spec_json.get("feature_name", spec.title)
            Signal.objects.create(
                workspace=issue.workspace,
                title=f"Feature shipped: {feature_name}",
                content=(
                    f"Issue '{issue.title}' was marked done as part of spec '{feature_name}'. "
                    f"Solution implemented: {spec.spec_json.get('solution', '')}"
                ),
                source="system",
                processing_status="processed",
            )
            # Auto-complete spec if all issues are done
            all_issues = spec.issues.all()
            if all_issues.exists() and all(i.status == SpecIssue.Status.DONE for i in all_issues):
                spec.status = GeneratedSpec.Status.COMPLETED
                spec.save(update_fields=["status", "updated_at"])
                ProductMemory.objects.get_or_create(
                    workspace=spec.workspace,
                    spec=spec,
                    defaults={
                        "category": ProductMemory.Category.SHIPPED,
                        "title": feature_name,
                        "summary": spec.spec_json.get("solution", ""),
                        "metadata": {"spec_id": str(spec.id), "auto_completed": True},
                    },
                )

        return Response(SpecIssueSerializer(issue).data)


class WorkspaceProductMemoryViewSet(viewsets.ModelViewSet):
    serializer_class = ProductMemorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ProductMemory.objects.filter(workspace__slug=self.kwargs.get("slug"))
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        workspace = get_object_or_404(Workspace, slug=self.kwargs.get("slug"))
        serializer.save(workspace=workspace)


# ─── Webhook Ingestion ────────────────────────────────────────────────────────


@method_decorator(csrf_exempt, name="dispatch")
class WorkspaceWebhookIngestView(APIView):
    """
    Accept webhook signals from external sources (Slack, Intercom, Zendesk, generic).
    POST /api/workspaces/<slug>/webhooks/ingest/

    Supported payload formats:
      - Slack:    {"type": "event_callback", "event": {"text": "...", "user": "..."}}
      - Intercom: {"type": "conversation.created", "data": {"item": {...}}}
      - Generic:  {"source": "...", "title": "...", "content": "..."}

    Optional HMAC verification via X-Webhook-Signature header + WEBHOOK_SECRET env var.
    Auto-triggers insight generation when a signal spike is detected (≥5 in 1 h).
    """

    permission_classes = [AllowAny]

    def post(self, request, slug):
        workspace = get_object_or_404(Workspace, slug=slug)

        # Optional HMAC signature verification
        secret = getattr(settings, "WEBHOOK_SECRET", "")
        if secret:
            sig = request.META.get("HTTP_X_WEBHOOK_SIGNATURE", "")
            expected = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected):
                return Response({"error": "Invalid signature"}, status=403)

        data = request.data
        source = data.get("source", "webhook")

        # ── Slack event format ────────────────────────────────────────────────
        if data.get("type") == "event_callback":
            event = data.get("event", {})
            text = event.get("text", "").strip()
            if not text:
                return Response({"status": "ignored"})
            title = f"Slack message from {event.get('user', 'unknown')}"
            content = text
            source = "slack"

        # ── Intercom conversation format ───────────────────────────────────────
        elif data.get("type", "").startswith("conversation"):
            item = data.get("data", {}).get("item", {})
            msg = item.get("conversation_message", {})
            content = msg.get("body", "") or str(msg.get("author", {}).get("name", ""))
            title = f"Intercom: {data.get('type', 'message')}"
            source = "intercom"

        # ── Generic / Zendesk format ───────────────────────────────────────────
        else:
            title = data.get("title", f"Webhook signal from {source}")
            content = data.get("content") or data.get("body") or data.get("text") or str(data)[:500]

        if not content:
            return Response({"status": "ignored — empty content"})

        signal = Signal.objects.create(
            workspace=workspace,
            title=str(title)[:255],
            content=content,
            source=source,
            processing_status="pending",
            source_metadata={"raw_payload": str(data)[:1000], "source": source},
        )

        # Store in Supermemory immediately
        try:
            from plane.signals import supermemory as sm

            doc_id = sm.store_signal(slug, str(signal.id), signal.title, signal.content or "")
            if doc_id:
                Signal.objects.filter(id=signal.id).update(supermemory_doc_id=doc_id)
        except Exception:
            pass

        # Auto-trigger insight generation on signal spike (≥5 pending in last hour)
        from datetime import timedelta

        from django.utils import timezone

        recent_count = Signal.objects.filter(
            workspace=workspace,
            processing_status="pending",
            created_at__gte=timezone.now() - timedelta(hours=1),
        ).count()

        if recent_count >= 5:
            generate_insights_task.delay(str(workspace.id))

        return Response(
            {"status": "created", "signal_id": str(signal.id)},
            status=201,
        )


# ─── Product Health Dashboard ─────────────────────────────────────────────────


class WorkspaceHealthView(APIView):
    """
    Real-time product health metrics for a workspace.
    GET /api/workspaces/<slug>/health/

    Returns:
      - signal velocity (1h / 24h / 7d), spike flag, source breakdown
      - top insight themes and recurring problems
      - spec status distribution and priority queue (top proposed specs)
      - Supermemory semantic context for "critical issues"
      - active alerts (anomalies / spikes)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        from datetime import timedelta

        from django.db.models import Count
        from django.utils import timezone

        workspace = get_object_or_404(Workspace, slug=slug)
        now = timezone.now()

        signals_qs = Signal.objects.filter(workspace=workspace)
        insights_qs = Insight.objects.filter(workspace=workspace)
        specs_qs = GeneratedSpec.objects.filter(workspace=workspace)

        # ── Signal velocity ──────────────────────────────────────────────────
        signals_1h = signals_qs.filter(created_at__gte=now - timedelta(hours=1)).count()
        signals_24h = signals_qs.filter(created_at__gte=now - timedelta(hours=24)).count()
        signals_7d = signals_qs.filter(created_at__gte=now - timedelta(days=7)).count()
        spike_detected = signals_1h >= 5

        source_breakdown = list(signals_qs.values("source").annotate(count=Count("id")).order_by("-count"))

        # ── Insights ─────────────────────────────────────────────────────────
        top_insights = list(insights_qs.order_by("-frequency")[:5].values("theme", "problem", "frequency"))
        recurring = list(
            insights_qs.filter(frequency__gte=3).order_by("-frequency")[:5].values("theme", "frequency", "problem")
        )

        # ── Specs ─────────────────────────────────────────────────────────────
        spec_status = list(specs_qs.values("status").annotate(count=Count("id")))

        priority_queue = []
        for s in (
            specs_qs.filter(status="proposed")
            .order_by("-priority_score")[:5]
            .values("id", "title", "priority_score", "impact_score", "effort_score", "status")
        ):
            s["id"] = str(s["id"])
            priority_queue.append(s)

        # ── Supermemory context ───────────────────────────────────────────────
        sm_context = ""
        try:
            from plane.signals import supermemory as sm

            sm_context = sm.get_context_for_query(slug, "critical user problems and pain points", max_chars=600)
        except Exception:
            pass

        # ── Alerts ────────────────────────────────────────────────────────────
        alerts = []
        if spike_detected:
            alerts.append(
                {
                    "type": "spike",
                    "message": f"Signal spike detected: {signals_1h} signals in the last hour",
                    "severity": "high",
                }
            )
        if priority_queue:
            top = priority_queue[0]
            alerts.append(
                {
                    "type": "build_next",
                    "message": f"Recommended build next: {top['title']} (priority {top['priority_score']})",
                    "severity": "info",
                }
            )

        return Response(
            {
                "signals": {
                    "total": signals_qs.count(),
                    "last_1h": signals_1h,
                    "last_24h": signals_24h,
                    "last_7d": signals_7d,
                    "spike_detected": spike_detected,
                    "by_source": source_breakdown,
                },
                "insights": {
                    "total": insights_qs.count(),
                    "top_themes": top_insights,
                    "recurring_problems": recurring,
                },
                "specs": {
                    "total": specs_qs.count(),
                    "by_status": spec_status,
                    "priority_queue": priority_queue,
                },
                "memory_context": sm_context,
                "alerts": alerts,
            }
        )


# ─── Semantic Memory Search ───────────────────────────────────────────────────


class WorkspaceSearchMemoryView(APIView):
    """
    Semantic search over Supermemory for past product decisions.
    POST /api/workspaces/<slug>/memory/search/
    Body: {"query": "...", "limit": 10}
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        get_object_or_404(Workspace, slug=slug)
        query = request.data.get("query", "").strip()
        if not query:
            return Response({"error": "query is required"}, status=400)

        try:
            from plane.signals import supermemory as sm

            results = sm.search(slug, query, limit=int(request.data.get("limit", 10)))
        except Exception as exc:
            return Response({"error": str(exc), "results": []})

        return Response({"query": query, "results": results})


# ─── Prioritization trigger ───────────────────────────────────────────────────


class WorkspacePrioritizeSpecsView(APIView):
    """
    Re-score and rank all proposed specs.
    POST /api/workspaces/<slug>/specs/prioritize/
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        workspace = get_object_or_404(Workspace, slug=slug)
        prioritize_specs_task.delay(str(workspace.id))
        return Response({"message": "Prioritization queued"})


class WorkspaceOutcomeViewSet(viewsets.ModelViewSet):
    """CRUD + record endpoint for feature outcomes."""

    serializer_class = OutcomeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Outcome.objects.filter(workspace__slug=self.kwargs.get("slug"))
            .select_related("spec")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        workspace = get_object_or_404(Workspace, slug=self.kwargs.get("slug"))
        serializer.save(workspace=workspace)

    @action(detail=False, methods=["post"])
    def record(self, request, slug):
        """
        Record an outcome for a spec.
        POST /api/workspaces/<slug>/outcomes/record/
        Body: { spec_id, result, success_score, metrics_before, metrics_after, notes }
        """
        workspace = get_object_or_404(Workspace, slug=slug)
        spec_id = request.data.get("spec_id")
        if not spec_id:
            return Response({"error": "spec_id is required"}, status=400)

        from plane.bgtasks.signals_tasks import record_outcome_task

        record_outcome_task.delay(
            spec_id=spec_id,
            result=request.data.get("result", "inconclusive"),
            success_score=float(request.data.get("success_score", 0.0)),
            metrics_before=request.data.get("metrics_before", {}),
            metrics_after=request.data.get("metrics_after", {}),
            notes=request.data.get("notes", ""),
        )
        return Response({"message": "Outcome recording queued", "spec_id": spec_id}, status=202)


# ─── Agent prompt builder (internal) ─────────────────────────────────────────


def _build_agent_prompt(spec_json: dict, fallback_title: str) -> str:
    j = spec_json
    feature = j.get("feature_name", fallback_title)
    lines = [
        f"# Task: Implement — {feature}",
        "",
        f"## Problem\n{j.get('problem', '')}",
        "",
        f"## User Story\n{j.get('user_story', '')}",
        "",
        f"## Solution\n{j.get('solution', '')}",
        "",
    ]
    if j.get("ui_changes"):
        lines += ["## UI Changes"] + [f"- {c}" for c in j["ui_changes"]] + [""]
    if j.get("data_model_changes"):
        lines += ["## Data Model Changes"] + [f"- {c}" for c in j["data_model_changes"]] + [""]
    if j.get("workflow_changes"):
        lines += ["## Workflow Changes"] + [f"- {c}" for c in j["workflow_changes"]] + [""]
    if j.get("tasks"):
        lines += ["## Agent Tasks", ""]
        for i, t in enumerate(j["tasks"], 1):
            lines.append(f"### Task {i}")
            lines.append("<read_first>")
            lines += [f"- {f}" for f in t.get("read_first", [])]
            lines.append("</read_first>")
            lines.append("<action>")
            lines += [f"- {a}" for a in t.get("action", [])]
            lines.append("</action>")
            lines.append("")
    return "\n".join(lines)
