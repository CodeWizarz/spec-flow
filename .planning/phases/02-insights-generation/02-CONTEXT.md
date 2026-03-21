# Phase 2: Insights Generation - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning
**Source:** Autonomous GSD requirements compilation

<domain>
## Phase Boundary

The Insights Generation phase (Phase 2) builds the intelligence layer of SpecFlow. It bridges the gap between raw unstructured feedback (Signals) and structured product direction. This phase will take all active signals in a workspace, feed them into an LLM via a background Celery task, and generate structured `Insight` records capturing recurring themes and problems.
</domain>

<decisions>
## Implementation Decisions

### Data Modeling
- **Insight Model**: Create `Insight` model in `apps/api/plane/insights` (or `plane.signals` extended). It should belong to a `Workspace`. Let's create a new Django app `plane.insights`.
- Fields: `title`, `description` (the theme/problem), `evidence` (JSON array of quotes or direct source references mapping back to Signals), `status` (active/archived).

### AI Processing
- Use a dedicated Celery task, e.g., `generate_insights_task(workspace_id)`.
- It will query all recent `Signal` records that haven't been processed into insights, compile their content into a prompt, and use `openai` (or `litellm` if Plane uses it) to generate a JSON response.
- The JSON output must strictly contain an array of insights with title, problem description, and exact quotes.

### Integration
- **Trigger**: A manual "Generate Insights" button on the UI that hits a POST endpoint `/api/workspaces/:slug/insights/generate/`.
- **View**: A React UI page listing discovered insights, leveraging `@plane/ui` components (Cards or Tables).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Foundational Architecture
- `.planning/phases/01-signals-module/01-PLAN.md` — Shows how we built standard Django apps for SpecFlow
- `.planning/1-CONTEXT.md` — Explains the async requirement (Celery)
</canonical_refs>

<specifics>
## Specific Ideas
- Prompt engineering inside the Celery task requires a `system` prompt focusing on product management best practices.
</specifics>

<deferred>
## Deferred Ideas
- Automated routing to issue trackers based on insights (v2)
- Re-running insights generation interactively over custom date ranges
</deferred>

---

*Phase: 02-insights-generation*
*Context gathered: 2026-03-21 via Discussion*
