# Phase 2: Insights Generation - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning
**Source:** Refined for AI reasoning and structured output

---

<domain>
## Phase Boundary

The Insights Generation phase (Phase 2) builds the intelligence layer of SpecFlow.

It transforms raw customer feedback (Signals) into structured product insights that help answer:
**"What problems are users actually facing, and why?"**

This phase must focus on **reasoning, not just clustering**.

The system:

* Processes all Signals in a workspace
* Uses an LLM to extract structured insights
* Stores results as `Insight` records

  </domain>

---

<decisions>
## Implementation Decisions

### Data Modeling

Create a new Django app: `plane.insights`

**Insight Model fields:**

* `workspace` (FK)
* `theme` (string)
* `problem` (text)
* `root_cause` (text) ← CRITICAL
* `evidence` (JSONField: array of quotes)
* `frequency` (integer, approximate count)
* `created_at`
* `status` (active/archived)

---

### AI Processing

Use a Celery task:

`generate_insights_task(workspace_id)`

Flow:

1. Fetch all active Signals for workspace
2. Concatenate content (with limits if needed)
3. Send to LLM API
4. Parse structured JSON response
5. Store as Insight records

---

### LLM Output Contract (STRICT)

The LLM MUST return JSON in this format:

[
{
"theme": "short label",
"problem": "clear description of user problem",
"root_cause": "why this problem is happening",
"evidence": ["exact user quote", "..."],
"frequency": number
}
]

---

### Prompt Behavior

The AI should:

* Extract recurring problems (not just summarize)
* Group similar issues into themes
* Identify **root causes** (why users are facing this)
* Include real user quotes as evidence
* Estimate frequency (rough count is fine)

The AI should NOT:

* Generate dashboards
* Add analytics or charts
* Be verbose or generic

---

### Integration

**Trigger:**
POST `/api/workspaces/:slug/insights/generate/`

* Kicks off Celery task

---

**UI:**

* Button: "Generate Insights"
* Display insights as list/cards
* Each insight shows:

  * Theme
  * Problem
  * Root Cause
  * Evidence (expandable)
  * Frequency

Keep UI minimal.

---

### Storage Strategy

* Insights are stored after generation
* Regeneration overwrites previous insights (v1 simplicity)

  </decisions>

---

<canonical_refs>

## Canonical References

* `.planning/phases/01-signals-module/01-PLAN.md`
* `.planning/1-CONTEXT.md`
  </canonical_refs>

---

<specifics>
## Specific Notes

* Use strong system prompt focused on product reasoning
* Prefer deterministic JSON output (low temperature)

  </specifics>

---

<deferred>
## Deferred Ideas (NOT in v1)

* Real-time streaming insights
* Advanced filtering / segmentation
* Automated prioritization scoring
* Direct integration to issue trackers

  </deferred>

---

*Phase: 02-insights-generation*
*Context refined for reasoning-driven AI system*
