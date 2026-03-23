"""
Supermemory integration — persistent semantic memory for SpecFlow.
API base: https://api.supermemory.ai
containerTag = workspace slug (one memory space per workspace)
"""

import logging
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _base_url() -> str:
    """
    Returns the Supermemory base URL.
    Priority: SUPERMEMORY_BASE_URL env (local) → default cloud API.
    """
    return getattr(settings, "SUPERMEMORY_BASE_URL", "https://api.supermemory.ai").rstrip("/")


# ─── core helpers ─────────────────────────────────────────────────────────────


def _headers() -> dict:
    key = getattr(settings, "SUPERMEMORY_API_KEY", "")
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return headers


def _enabled() -> bool:
    has_key = bool(getattr(settings, "SUPERMEMORY_API_KEY", ""))
    has_local = getattr(settings, "SUPERMEMORY_BASE_URL", "") not in ("", "https://api.supermemory.ai")
    return has_key or has_local


# ─── document operations ──────────────────────────────────────────────────────


def add_document(
    workspace_slug: str,
    content: str,
    metadata: Optional[dict] = None,
) -> Optional[str]:
    """
    Add a document to Supermemory scoped to the workspace.
    Returns the document ID on success, None otherwise.
    """
    if not _enabled():
        return None
    try:
        payload = {
            "content": content,
            "containerTags": [workspace_slug],
            "metadata": metadata or {},
        }
        resp = requests.post(
            f"{_base_url()}/v3/documents",
            json=payload,
            headers=_headers(),
            timeout=10,
        )
        if resp.ok:
            return resp.json().get("id")
        logger.warning(
            "Supermemory add_document failed: %s %s",
            resp.status_code,
            resp.text[:200],
        )
    except Exception as exc:
        logger.error("Supermemory add_document error: %s", exc)
    return None


def search(
    workspace_slug: str,
    query: str,
    limit: int = 10,
) -> list:
    """
    Semantic search over the workspace's Supermemory documents.
    Returns a list of result dicts (each has at minimum a 'content' key).
    """
    if not _enabled():
        return []
    try:
        payload = {
            "query": query,
            "containerTags": [workspace_slug],
            "limit": limit,
        }
        resp = requests.post(
            f"{_base_url()}/v3/search",
            json=payload,
            headers=_headers(),
            timeout=10,
        )
        if resp.ok:
            data = resp.json()
            return data.get("results", data if isinstance(data, list) else [])
        logger.warning(
            "Supermemory search failed: %s %s",
            resp.status_code,
            resp.text[:200],
        )
    except Exception as exc:
        logger.error("Supermemory search error: %s", exc)
    return []


def add_memory(
    workspace_slug: str,
    content: str,
    metadata: Optional[dict] = None,
) -> Optional[str]:
    """
    Add a direct memory entry (low-latency v4 API — ideal for decisions/outcomes).
    Returns the memory ID on success, None otherwise.
    """
    if not _enabled():
        return None
    try:
        payload = {
            "content": content,
            "containerTags": [workspace_slug],
            "metadata": metadata or {},
        }
        resp = requests.post(
            f"{_base_url()}/v4/memories",
            json=payload,
            headers=_headers(),
            timeout=10,
        )
        if resp.ok:
            result = resp.json()
            return result.get("id") or result.get("memoryId")
        logger.warning(
            "Supermemory add_memory failed: %s %s",
            resp.status_code,
            resp.text[:200],
        )
    except Exception as exc:
        logger.error("Supermemory add_memory error: %s", exc)
    return None


# ─── context retrieval ────────────────────────────────────────────────────────


def get_context_for_query(
    workspace_slug: str,
    query: str,
    max_chars: int = 2000,
) -> str:
    """
    Fetch the most relevant past context from Supermemory for an AI prompt.
    Returns a formatted string ready for injection into a system prompt.
    """
    results = search(workspace_slug, query, limit=8)
    if not results:
        return ""

    lines = ["## Relevant Past Context from Product Memory (via Supermemory):"]
    total = 0
    for r in results:
        chunk = r.get("content") or r.get("text") or str(r)
        if total + len(chunk) > max_chars:
            break
        lines.append(f"- {chunk[:500]}")
        total += len(chunk)
    return "\n".join(lines)


# ─── typed convenience wrappers ───────────────────────────────────────────────


def store_signal(
    workspace_slug: str,
    signal_id: str,
    title: str,
    content: str,
) -> Optional[str]:
    """Store a customer signal in Supermemory. Returns doc ID."""
    return add_document(
        workspace_slug,
        f"[SIGNAL] {title}\n{content}",
        metadata={"type": "signal", "signal_id": signal_id},
    )


def store_insight(
    workspace_slug: str,
    insight_id: str,
    theme: str,
    problem: str,
    root_cause: str,
) -> Optional[str]:
    """Store an extracted insight in Supermemory. Returns doc ID."""
    return add_document(
        workspace_slug,
        f"[INSIGHT] Theme: {theme}\nProblem: {problem}\nRoot Cause: {root_cause}",
        metadata={"type": "insight", "insight_id": insight_id},
    )


def store_spec(
    workspace_slug: str,
    spec_id: str,
    feature_name: str,
    solution: str,
    status: str = "proposed",
) -> Optional[str]:
    """Store a generated spec in Supermemory. Returns doc ID."""
    return add_document(
        workspace_slug,
        f"[SPEC][{status.upper()}] Feature: {feature_name}\nSolution: {solution}",
        metadata={"type": "spec", "spec_id": spec_id, "status": status},
    )


def store_decision(
    workspace_slug: str,
    feature_name: str,
    decision: str,
    reason: str = "",
) -> Optional[str]:
    """
    Record a product decision (approved / rejected) in Supermemory.
    Uses the v4 memory endpoint for fast recall at query time.
    Returns memory ID.
    """
    return add_memory(
        workspace_slug,
        f"[DECISION] Feature '{feature_name}' was {decision}. Reason: {reason}",
        metadata={"type": "decision", "feature": feature_name, "decision": decision},
    )


def store_outcome(
    workspace_slug: str,
    feature_name: str,
    outcome: str,
    confidence: float = 0.0,
) -> Optional[str]:
    """
    Record an experiment / feature outcome in Supermemory.
    Used by the Experimentation Engine to feed results back into memory.
    Returns memory ID.
    """
    return add_memory(
        workspace_slug,
        f"[OUTCOME] Feature '{feature_name}': {outcome} (confidence: {confidence:.0%})",
        metadata={
            "type": "outcome",
            "feature": feature_name,
            "confidence": confidence,
        },
    )


def search_past_rejections(workspace_slug: str, feature_query: str) -> list:
    """
    Convenience search: find past rejected or failed features similar to a query.
    Helps the Spec Agent avoid duplicating rejected work.
    """
    return search(workspace_slug, f"{feature_query} rejected failed duplicate", limit=5)
