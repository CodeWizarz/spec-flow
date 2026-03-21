# Phase 3: Spec Generator - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning
**Source:** Autonomous GSD requirements compilation

<domain>
## Phase Boundary

The Spec Generator phase (Phase 3) acts as the output layer of SpecFlow. It connects the extracted recurring insights into a comprehensive implementation specification. This involves prompting an LLM to recommend features, UI changes, data model changes, workflow adjustments, and crucially, an itemized task list specifically formatted for autonomous coding agents (Cursor/Claude Code). Users can review and download the raw Markdown spec.
</domain>

<decisions>
## Implementation Decisions

### Data Modeling
- **Spec Model**: Create `GeneratedSpec` model in `apps/api/plane/signals/models.py` (associating it with `Workspace`).
- Fields: `title`, `content` (Markdown string), `status` (draft/published), `created_at`, `updated_at`.

### AI Processing
- Create a Celery task `generate_spec_task(workspace_id, insight_ids)`. The user passes an array of selected Insights they want to act on.
- The LLM System Prompt will strictly instruct the model to output a GitHub-flavored Markdown document with the following sections: `Feature Recommendation`, `Customer Evidence`, `UI Changes`, `Data Model Changes`, `Workflow Changes`, and `Agent Development Tasks`.
- The Agent Development tasks MUST be formatted as a checklist with `<read_first>` and `<action>` pairs, to be directly plug-and-play for AI agents.

### Integration
- **API**: A POST endpoint `/api/workspaces/:slug/specs/generate/` accepting `{ insight_ids: [...] }`.
- **UI**: A React UI page (`/workspace/:workspaceSlug/specs`) listing generated specs. 
- **View/Export**: Clicking a spec displays the Markdown rendered as HTML. Include a "Download Markdown" `Button` implementation leveraging browser Blob API.
</decisions>

<canonical_refs>
## Canonical References

### Foundational Architecture
- `.planning/phases/01-signals-module/01-PLAN.md` — Django apps structure
- `.planning/phases/02-insights-generation/02-PLAN.md` — LLM background processing patterns
</canonical_refs>

<specifics>
## Specific Ideas
- Prompt engineering inside the Celery task requires explicit guidance on how Claude Code and Cursor expect instructions (concrete step-by-step XML boundaries).
</specifics>

<deferred>
## Deferred Ideas
- Auto-creating Linear/Jira/Plane issues instead of (or in addition to) the Markdown file. (v2 scope)
</deferred>

---

*Phase: 03-spec-generator*
*Context gathered: 2026-03-21 via Discussion*
