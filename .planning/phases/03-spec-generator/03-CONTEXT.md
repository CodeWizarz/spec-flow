# Phase 3: Spec Generator - Context

## Goal

Convert Insights into structured, implementation-ready product specifications.

This is the core feature of SpecFlow.

This is NOT a document generator.

---

## Data Modeling

Create a new model: `GeneratedSpec`

Fields:

* workspace (FK)
* insight (FK)
* spec_json (JSONField) ← PRIMARY STORAGE
* created_at

Do NOT store only markdown.

---

## Output Format (STRICT)

The AI must return structured JSON:

{
"feature_name": "",
"problem": "",
"user_story": "",
"solution": "",
"ui_changes": [],
"data_model_changes": [],
"workflow_changes": [],
"tasks": {
"backend": [],
"frontend": []
}
}

---

## AI Behavior

The AI should:

* Convert insights into actionable implementation plans
* Be concise and structured
* Avoid long paragraphs
* Focus on execution clarity

---

## Processing

Use Celery task:
`generate_spec_task(insight_id)`

Steps:

1. Fetch Insight
2. Send structured prompt to LLM
3. Parse JSON
4. Store in `spec_json`

---

## UI

* Button: "Generate Spec" on each Insight

* Display spec in structured sections:

  * Feature
  * Problem
  * UI Changes
  * Tasks

* Optional: allow markdown export (generated from JSON)

---

## Constraints

* JSON is source of truth
* Markdown is optional output
* No long essays
* No generic AI text
