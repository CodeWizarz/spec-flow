# Phase 2: Insights Generation Research

## Technical Discoveries

### Backend Architecture
1. **Data Model**: We need an `Insight` model in `apps/api/plane/signals/models.py`. It should have `workspace`, `title`, `problem_statement`, and an `evidence` JSONField (to store arrays of quotes/sources).
2. **Celery Task**: `apps/api/plane/bgtasks/signals_tasks.py` will host `generate_insights_task(workspace_id)`. It needs to fetch all `Signal` objects with `processing_status='processed'` (which means they have text but haven't been factored into insights yet, or we can use a new status `insight_generated`).
3. **LLM Integration**: Use the `openai` Python package. The prompt must request JSON output matching the `Insight` model schema.
4. **REST Endpoints**: Add `WorkspaceInsightViewSet` in `views.py` so the React frontend can fetch the generated insights. Also, add an `@action(detail=False, methods=['post'])` to `WorkspaceSignalViewSet` called `generate_insights` to trigger the celery task manually.

### Frontend Architecture
1. **MobX Store**: `insights.store.ts` inside `packages/shared-state` to fetch insights and trigger generation.
2. **Service**: `insights.service.ts` connecting to `/api/workspaces/:slug/insights/`.
3. **React View**: A new page `apps/web/src/pages/workspace/insights/index.tsx`. It displays each insight as a Card, showing the `title`, `problem_statement`, and an accordion/list for `evidence` quotes.

## Validation Architecture
- **Dependency**: The OpenAI python package must exist or we should gracefully handle `ImportError` if Plane doesn't have it by default.
- **API Tests**: Triggering `/generate_insights` should return a 202 Accepted.
- **Frontend tests**: User can navigate to Insights tab and view them.
