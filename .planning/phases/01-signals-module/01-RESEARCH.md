# Phase 1: Signals Module Research

## Technical Discoveries

### Backend (Django) Integration
1. **Model Hierarchy**: Plane's data models are located in `apps/api/plane`. A new module should likely be created as a new app or within `space` or `workspace`. Since Signals are tied to workspaces, adding `apps/api/plane/signals` is the standard Django pattern, complete with `models.py`, `serializers.py`, and `views.py`.
2. **Async Task Processing (Celery)**: 
   - Celery is configured in `apps/api/plane/celery.py`. 
   - Tasks live in `apps/api/plane/bgtasks/`. We need a new task e.g. `process_signal_file_task(signal_id)` to extract text from files in the background.
3. **Storage**: File uploads expect multipart form data. Django will handle uploads via standard `FileField` or S3 storage backends depending on `django-storages` setup in Plane. Note: ensure we don't block the API thread during I/O.

### Frontend (React/Vite) Integration
1. **API Services**: `packages/services` is where axios calls are wrapped. Need `signal.service.ts` for CRUD operations.
2. **State Management**: `packages/shared-state` holds MobX stores. Need a new `SignalStore` that manages caching and invalidation of signal lists at the workspace level.
3. **UI Components**: UI must remain minimal. We should reuse components from `@plane/ui` like `Button`, `Input`, `Table` built on Headless UI/Tailwind.
4. **Routing**: `apps/web/react-router.config.ts` handles routing. A new nested route under `/workspace/:workspaceSlug/signals` should be created.

## Validation Architecture
- **API Tests**: Add pytest coverage in `apps/api/plane/signals/tests/`. Ensure standard auth tokens provide access.
- **Frontend Tests**: Unit test `SignalStore` in `packages/shared-state` using vitest.
