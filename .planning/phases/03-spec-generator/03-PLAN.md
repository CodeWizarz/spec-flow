---
title: "Phase 3: Spec Generator Execution Plan"
wave: 1
depends_on: []
files_modified:
  - apps/api/plane/signals/models.py
  - apps/api/plane/signals/serializers.py
  - apps/api/plane/signals/views.py
  - apps/api/plane/signals/urls.py
  - apps/api/plane/bgtasks/signals_tasks.py
  - packages/services/src/spec.service.ts
  - packages/shared-state/src/spec.store.ts
  - apps/web/src/pages/workspace/specs/index.tsx
autonomous: true
requirements:
  - SPC-01
  - SPC-02
  - SPC-03
  - SPC-04
---

# Phase 3: Spec Generator Execution Plan

## Objective
Convert selected insights into formal implementation specifications entirely utilizing structured JSON as the source of truth, deriving markdown only dynamically for export.

## Tasks

### 1. Create Django Spec Model & Serializer (Backend)
<read_first>
- apps/api/plane/signals/models.py
- apps/api/plane/signals/serializers.py
</read_first>
<action>
1. In `apps/api/plane/signals/models.py`, add `GeneratedSpec(WorkspaceBaseModel):`.
   - `workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="specs")`
   - `title = models.CharField(max_length=255)`
   - `spec_json = models.JSONField(default=dict)`
2. Add `GeneratedSpecSerializer` in `serializers.py` tracking these fields.
</action>
<acceptance_criteria>
- Django migration logic functions against the existing `Workspace` base model constraints.
</acceptance_criteria>

### 2. Implement LLM Spec Task (Backend)
<read_first>
- apps/api/plane/bgtasks/signals_tasks.py
</read_first>
<action>
1. Add `@shared_task def generate_spec_task(workspace_id, insight_ids=None):`.
2. Extract the relevant `Insight` objects by `insight_ids`.
3. Call `openai` with `response_format={ "type": "json_object" }` requesting JSON format `{"data": { ... }}`.
4. The system prompt MUST enforce returning keys: `feature_name` (string), `problem` (string), `user_story` (string), `solution` (string), `ui_changes` (array), `data_model_changes` (array), `workflow_changes` (array), and `tasks` (array of objects with `read_first` and `action`).
5. Save the output to a new `GeneratedSpec` storing the extracted `"data"` dynamically in `spec_json`.
</action>
<acceptance_criteria>
- Task correctly aggregates problem context from selected insights and produces valid JSON matching the exact schema without free text.
</acceptance_criteria>

### 3. Build REST Endpoints (Backend)
<read_first>
- apps/api/plane/signals/views.py
- apps/api/plane/signals/urls.py
</read_first>
<action>
1. Create `WorkspaceSpecViewSet(viewsets.ModelViewSet)`.
2. Add an `@action(detail=False, methods=['post'])` to trigger `generate_spec_task.delay(workspace.id, request.data.get('insight_ids', []))`.
3. Register the router `/api/workspaces/:slug/specs/` and the generate action in URLs.
</action>
<acceptance_criteria>
- The `/generate/` endpoint correctly queues the generation task.
</acceptance_criteria>

### 4. Create Frontend Service and Store (Frontend)
<read_first>
- packages/services/src/spec.service.ts
- packages/shared-state/src/spec.store.ts
</read_first>
<action>
1. Scaffold `spec.service.ts` routing to `/api/workspaces/:slug/specs/`.
2. Scaffold `spec.store.ts` orchestrating MobX lists `specs: any[]` and exposing an `isGenerating` loading state.
</action>
<acceptance_criteria>
- React store reliably mirrors the background task initiation sequence.
</acceptance_criteria>

### 5. Build Spec Generator UI & Export (Frontend)
<read_first>
- apps/web/src/pages/workspace/specs/index.tsx
</read_first>
<action>
1. Create `apps/web/src/pages/workspace/specs/index.tsx`.
2. Map existing stored specs as interactive list elements.
3. When selecting a spec, iterate over `spec_json` to draw UI blocks for each dictionary key natively (e.g. mapping `ui_changes` array output to `<li>`). 
4. Implement a "Download as .md" button that compiles the JSON fields into Agent-style Markdown templates using string literals (`<read_first>`, `<action>`), and exports via Blob download logic.
</action>
<acceptance_criteria>
- Complete alignment with SPC-04 allowing offline preservation of AI logic paths formatted functionally on the fly.
</acceptance_criteria>

## Verification
- must_haves:
  - Source payload utilizes raw JSON representation in Postgres backend.
  - Generates Agent-compatible XML-based markdown templates only at the UI download stage natively.
