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
Convert selected insights into a formalized markdown implementation specification. This specification will be strictly tailored for autonomous coding agents (Cursor/Claude Code), containing actionable data model updates, UI changes, and <read_first>/<action> blocks.

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
   - `content = models.TextField()`
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
2. Extract the relevant `Insight` objects by `insight_ids`, or all insights if none specified.
3. Call `openai` requesting a Markdown formatted response containing sections for: Feature Recommendation, Evidence, UI Changes, Data Model Changes, Workflow Changes, and Agent Tasks.
4. The system prompt MUST enforce that the Agent Tasks list explicitly uses `<read_first>` and `<action>` syntax compatible with AI coders.
5. Save the output to a new `GeneratedSpec`.
</action>
<acceptance_criteria>
- Task correctly aggregates problem context from selected insights and produces valid markdown models.
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
3. Show the `.content` attribute rendering inside `<pre>` tags (or simple React Markdown if available) when selected.
4. Implement a "Download as .md" button via a Blob trigger `URL.createObjectURL(new Blob([content], { type: 'text/markdown' }))`.
</action>
<acceptance_criteria>
- Complete alignment with SPC-04 allowing offline preservation of AI logic paths.
</acceptance_criteria>

## Verification
- must_haves:
  - Markdown output cleanly details actionable items.
  - Browser correctly downloads `.md` files without CORS/DOM exceptions.
