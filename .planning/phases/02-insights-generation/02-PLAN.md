---
title: "Phase 2: Insights Generation Execution Plan"
wave: 1
depends_on: []
files_modified:
  - apps/api/plane/signals/models.py
  - apps/api/plane/signals/serializers.py
  - apps/api/plane/signals/views.py
  - apps/api/plane/signals/urls.py
  - apps/api/plane/bgtasks/signals_tasks.py
  - packages/services/src/insights.service.ts
  - packages/shared-state/src/insights.store.ts
  - apps/web/src/pages/workspace/insights/index.tsx
autonomous: true
requirements:
  - INS-01
  - INS-02
  - INS-03
---

# Phase 2: Insights Generation Execution Plan

## Objective
Extract actionable themes and core problems from the unstructured customer signals stored in Phase 1, using an LLM. Display these insights in the frontend with traceable evidence.

## Tasks

### 1. Create Django Insight Model & Serializer (Backend)
<read_first>
- apps/api/plane/signals/models.py
- apps/api/plane/signals/serializers.py
</read_first>
<action>
1. In `apps/api/plane/signals/models.py`, add `Insight(WorkspaceBaseModel):`.
   - `workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="insights")`
   - `title = models.CharField(max_length=255)`
   - `problem_statement = models.TextField()`
   - `evidence = models.JSONField(default=list)`
2. Add `InsightSerializer` in `serializers.py` capturing all fields.
</action>
<acceptance_criteria>
- `apps/api/plane/signals/models.py` contains `class Insight(`.
- `InsightSerializer` successfully serializes the model.
- Running `makemigrations signals` creates a valid migration.
</acceptance_criteria>

### 2. Implement LLM Celery Task (Backend)
<read_first>
- apps/api/plane/bgtasks/signals_tasks.py
</read_first>
<action>
1. In `signals_tasks.py`, add `@shared_task def generate_insights_task(workspace_id):`.
2. Query all `Signal.objects.filter(workspace_id=workspace_id, processing_status='processed')`.
3. Combine their `content` into a single text block.
4. Pass this to a mock LLM generator (or OpenAI if `OPENAI_API_KEY` is present) requesting a JSON array of themes, problems, and evidence quotes.
5. For each returned item, create an `Insight` object.
6. Mark the queried Signals as `processing_status='insight_generated'`.
</action>
<acceptance_criteria>
- `generate_insights_task` fetches processed signals.
- It iterates over the AI JSON response to save `Insight` objects.
- Modifies signal `.processing_status` to `"insight_generated"`.
</acceptance_criteria>

### 3. Build REST Endpoints (Backend)
<read_first>
- apps/api/plane/signals/views.py
- apps/api/plane/signals/urls.py
</read_first>
<action>
1. Create `WorkspaceInsightViewSet(viewsets.ModelViewSet)` in `views.py` returning `Insight.objects.filter(workspace__slug=slug)`.
2. Add a custom `@action(detail=False, methods=['post'])` named `generate` to `WorkspaceSignalViewSet` that triggers `generate_insights_task.delay(workspace.id)` and returns `{"message": "Queued"}`.
3. Register the new ViewSet and endpoint in `urls.py`.
</action>
<acceptance_criteria>
- `WorkspaceInsightViewSet` is present.
- Sending POST to `/api/workspaces/:slug/signals/generate/` explicitly calls the Celery task.
- `urls.py` correctly maps `/api/workspaces/<slug:slug>/insights/`.
</acceptance_criteria>

### 4. Create Frontend Service and Store (Frontend)
<read_first>
- packages/services/src/insights.service.ts
- packages/shared-state/src/insights.store.ts
</read_first>
<action>
1. Create `insights.service.ts` with `InsightService extents APIService`. Add `getInsights(workspaceSlug)` and `generateInsights(workspaceSlug)`.
2. Create `insights.store.ts` (`InsightStore`) utilizing MobX to `fetchInsights` and `triggerGeneration`.
</action>
<acceptance_criteria>
- `insights.service.ts` defines endpoints targeting `/api/workspaces/:slug/insights/`.
- `insights.store.ts` manages reactive insight arrays.
</acceptance_criteria>

### 5. Build Insights React UI (Frontend)
<read_first>
- apps/web/src/pages/workspace/insights/index.tsx
</read_first>
<action>
1. Create `apps/web/src/pages/workspace/insights/index.tsx`.
2. Map over `insightStore.insights` and render a list of cards/sections.
3. Show the `title`, `problem_statement`, and loop through the `evidence` strings to show exactly what users said.
4. Add a `Generate Insights` button hitting the generation endpoint.
</action>
<acceptance_criteria>
- `index.tsx` exists and renders the `Insight` domain model.
- Contains a generic button to trigger generation.
</acceptance_criteria>

## Verification
- must_haves:
  - Insight objects are stored safely in the database containing an array of evidence quotes.
  - Generative processing task runs asynchronously.
  - Output traces explicitly back to original raw signals (INS-03).
