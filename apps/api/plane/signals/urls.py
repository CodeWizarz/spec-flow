from django.urls import path

from plane.signals.views import (
    WorkspaceHealthView,
    WorkspaceInsightViewSet,
    WorkspaceOutcomeViewSet,
    WorkspacePrioritizeSpecsView,
    WorkspaceProductMemoryViewSet,
    WorkspaceSearchMemoryView,
    WorkspaceSignalViewSet,
    WorkspaceSpecIssueViewSet,
    WorkspaceSpecViewSet,
    WorkspaceWebhookIngestView,
)

# ── Signals ────────────────────────────────────────────────────────────────────
signal_list = WorkspaceSignalViewSet.as_view({"get": "list", "post": "create"})
signal_generate = WorkspaceSignalViewSet.as_view({"post": "generate"})
signal_detail = WorkspaceSignalViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"})

# ── Insights ───────────────────────────────────────────────────────────────────
insight_list = WorkspaceInsightViewSet.as_view({"get": "list", "post": "create"})
insight_detail = WorkspaceInsightViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"})

# ── Specs ──────────────────────────────────────────────────────────────────────
spec_list = WorkspaceSpecViewSet.as_view({"get": "list"})
spec_generate = WorkspaceSpecViewSet.as_view({"post": "generate"})
spec_detail = WorkspaceSpecViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"})
spec_update_status = WorkspaceSpecViewSet.as_view({"patch": "update_status"})
spec_agent_payload = WorkspaceSpecViewSet.as_view({"post": "agent_payload"})
spec_create_issue = WorkspaceSpecViewSet.as_view({"post": "create_issue"})

# ── Spec Issues (nested under a spec) ─────────────────────────────────────────
spec_issue_list = WorkspaceSpecIssueViewSet.as_view({"get": "list", "post": "create"})
spec_issue_detail = WorkspaceSpecIssueViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)
spec_issue_update_status = WorkspaceSpecIssueViewSet.as_view({"patch": "update_status"})

# ── Product Memory ─────────────────────────────────────────────────────────────
memory_list = WorkspaceProductMemoryViewSet.as_view({"get": "list", "post": "create"})
memory_detail = WorkspaceProductMemoryViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)

# ── Execution ──────────────────────────────────────────────────────────────────
spec_execute = WorkspaceSpecViewSet.as_view({"post": "execute"})

# ── Outcomes ───────────────────────────────────────────────────────────────────
outcome_list = WorkspaceOutcomeViewSet.as_view({"get": "list", "post": "create"})
outcome_record = WorkspaceOutcomeViewSet.as_view({"post": "record"})
outcome_detail = WorkspaceOutcomeViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"})

urlpatterns = [
    # ── Signals ────────────────────────────────────────────────────────────────
    path(
        "api/workspaces/<slug:slug>/signals/",
        signal_list,
        name="workspace-signals",
    ),
    # NOTE: literal sub-paths must come BEFORE the <uuid:pk> pattern
    path(
        "api/workspaces/<slug:slug>/signals/generate/",
        signal_generate,
        name="workspace-signal-generate",
    ),
    path(
        "api/workspaces/<slug:slug>/signals/<uuid:pk>/",
        signal_detail,
        name="workspace-signal-detail",
    ),
    # ── Insights ───────────────────────────────────────────────────────────────
    path(
        "api/workspaces/<slug:slug>/insights/",
        insight_list,
        name="workspace-insights",
    ),
    path(
        "api/workspaces/<slug:slug>/insights/<uuid:pk>/",
        insight_detail,
        name="workspace-insight-detail",
    ),
    # ── Specs ──────────────────────────────────────────────────────────────────
    path(
        "api/workspaces/<slug:slug>/specs/",
        spec_list,
        name="workspace-specs",
    ),
    # literal sub-paths before <uuid:pk>
    path(
        "api/workspaces/<slug:slug>/specs/generate/",
        spec_generate,
        name="workspace-spec-generate",
    ),
    path(
        "api/workspaces/<slug:slug>/specs/prioritize/",
        WorkspacePrioritizeSpecsView.as_view(),
        name="workspace-specs-prioritize",
    ),
    path(
        "api/workspaces/<slug:slug>/specs/<uuid:pk>/",
        spec_detail,
        name="workspace-spec-detail",
    ),
    path(
        "api/workspaces/<slug:slug>/specs/<uuid:pk>/status/",
        spec_update_status,
        name="workspace-spec-status",
    ),
    path(
        "api/workspaces/<slug:slug>/specs/<uuid:pk>/agent-payload/",
        spec_agent_payload,
        name="workspace-spec-agent-payload",
    ),
    path(
        "api/workspaces/<slug:slug>/specs/<uuid:pk>/create-issue/",
        spec_create_issue,
        name="workspace-spec-create-issue",
    ),
    # ── Spec Issues (nested under spec) ───────────────────────────────────────
    path(
        "api/workspaces/<slug:slug>/specs/<uuid:spec_pk>/issues/",
        spec_issue_list,
        name="workspace-spec-issues",
    ),
    path(
        "api/workspaces/<slug:slug>/specs/<uuid:spec_pk>/issues/<uuid:pk>/",
        spec_issue_detail,
        name="workspace-spec-issue-detail",
    ),
    path(
        "api/workspaces/<slug:slug>/specs/<uuid:spec_pk>/issues/<uuid:pk>/status/",
        spec_issue_update_status,
        name="workspace-spec-issue-status",
    ),
    # ── Product Memory ─────────────────────────────────────────────────────────
    path(
        "api/workspaces/<slug:slug>/memory/",
        memory_list,
        name="workspace-memory",
    ),
    path(
        "api/workspaces/<slug:slug>/memory/search/",
        WorkspaceSearchMemoryView.as_view(),
        name="workspace-memory-search",
    ),
    path(
        "api/workspaces/<slug:slug>/memory/<uuid:pk>/",
        memory_detail,
        name="workspace-memory-detail",
    ),
    # ── Execution ─────────────────────────────────────────────────────────────
    path(
        "api/workspaces/<slug:slug>/specs/<uuid:pk>/execute/",
        spec_execute,
        name="workspace-spec-execute",
    ),
    # ── Outcomes ──────────────────────────────────────────────────────────────
    path(
        "api/workspaces/<slug:slug>/outcomes/",
        outcome_list,
        name="workspace-outcomes",
    ),
    path(
        "api/workspaces/<slug:slug>/outcomes/record/",
        outcome_record,
        name="workspace-outcomes-record",
    ),
    path(
        "api/workspaces/<slug:slug>/outcomes/<uuid:pk>/",
        outcome_detail,
        name="workspace-outcome-detail",
    ),
    # ── Webhook Ingestion ──────────────────────────────────────────────────────
    path(
        "api/workspaces/<slug:slug>/webhooks/ingest/",
        WorkspaceWebhookIngestView.as_view(),
        name="workspace-webhook-ingest",
    ),
    # ── Product Health Dashboard ───────────────────────────────────────────────
    path(
        "api/workspaces/<slug:slug>/health/",
        WorkspaceHealthView.as_view(),
        name="workspace-health",
    ),
]
