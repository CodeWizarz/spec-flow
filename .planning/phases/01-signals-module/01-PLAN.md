---
title: "Phase 1: Signals Module Backend & Frontend Execution Plan"
wave: 1
depends_on: []
files_modified:
  - apps/api/plane/signals/models.py
  - apps/api/plane/signals/views.py
  - apps/api/plane/signals/serializers.py
  - apps/api/plane/signals/urls.py
  - apps/api/plane/bgtasks/signals_tasks.py
  - packages/services/src/signals.service.ts
  - packages/shared-state/src/signals.store.ts
  - apps/web/src/pages/workspace/signals/index.tsx
autonomous: true
requirements:
  - SIG-01
  - SIG-02
  - SIG-03
---

# Phase 1: Signals Module Backend & Frontend Execution Plan

## Objective
Implement early pipeline for ingesting, storing, and viewing customer feedback signals. This includes the Django backend models, Celery async processing, and basic React views using existing `@plane/ui` components.

## Tasks

### 1. Create Django Models and Serializers for Signals (Backend)
<read_first>
- apps/api/plane/workspace/models.py
- apps/api/plane/signals/models.py
- apps/api/plane/signals/serializers.py
- .planning/1-CONTEXT.md
</read_first>
<action>
1. Under `apps/api/plane/signals`, create `models.py` (if it doesn't exist) and define the `Signal` model.
2. The `Signal` model MUST inherit from the standard `ProjectBaseModel` or `WorkspaceBaseModel` and include:
   - `workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="signals")`
   - `title = models.CharField(max_length=255)`
   - `content = models.TextField(blank=True, null=True)`
   - `file = models.FileField(upload_to="signals/", blank=True, null=True)`
   - `source = models.CharField(max_length=50, default="manual")`
   - `processing_status = models.CharField(max_length=20, default="pending")` # can be 'pending', 'processed', 'error'
3. Create `serializers.py` defining `SignalSerializer` that serializes all fields above.
</action>
<acceptance_criteria>
- `apps/api/plane/signals/models.py` contains `class Signal(` with a ForeignKey to Workspace.
- `apps/api/plane/signals/serializers.py` contains `SignalSerializer` handling the `Workspace` relationship.
- Running `python manage.py makemigrations` exits 0 with a new migration for `signals`. 
</acceptance_criteria>

### 2. Implement Celery Async Processing (Backend)
<read_first>
- apps/api/plane/bgtasks/signals_tasks.py
- apps/api/plane/signals/models.py
- .planning/1-CONTEXT.md
</read_first>
<action>
1. Create `apps/api/plane/bgtasks/signals_tasks.py`.
2. Define an async celery task `@shared_task` named `process_signal_file_task(signal_id)`.
3. The task should retrieve the `Signal` by ID. If `signal.file` exists, extract basic text (for v1, a placeholder or simple utf-8 decode is fine) and append to `signal.content`.
4. Update `signal.processing_status = "processed"` and `.save()`.
</action>
<acceptance_criteria>
- `apps/api/plane/bgtasks/signals_tasks.py` contains `@shared_task` and `def process_signal_file_task`.
- The task sets `processing_status = "processed"`.
</acceptance_criteria>

### 3. Build REST Endpoints (Backend)
<read_first>
- apps/api/plane/signals/views.py
- apps/api/plane/signals/urls.py
- apps/api/plane/bgtasks/signals_tasks.py
- .planning/1-CONTEXT.md
</read_first>
<action>
1. Create `WorkspaceSignalViewSet` in `views.py` handling CRUD via `ModelViewSet`. Use `Permission` classes standard to Plane `WorkspaceOwnerPermission` or similar.
2. In the `create` generic method, if `request.FILES.get('file')` is present, attach it to the `Signal`.
3. At the end of `perform_create`, call `process_signal_file_task.delay(instance.id)`.
4. Register the viewset in `urls.py`.
</action>
<acceptance_criteria>
- `apps/api/plane/signals/views.py` contains `class WorkspaceSignalViewSet`.
- `process_signal_file_task.delay(instance.id)` is explicitly called when creating a signal.
- `urls.py` correctly registers the ViewSet.
</acceptance_criteria>

### 4. Create Frontend Service and Store (Frontend)
<read_first>
- packages/services/src/signals.service.ts
- packages/shared-state/src/signals.store.ts
- apps/api/plane/signals/urls.py
</read_first>
<action>
1. Create `packages/services/src/signals.service.ts` with `SignalService` class that uses `APIService` to POST and GET `/api/workspaces/:workspaceSlug/signals/`.
2. Support `multipart/form-data` in the `createSignal` method for file uploads.
3. Create `packages/shared-state/src/signals.store.ts` implementing a standard MobX list store (`fetchSignals`, `createSignal`) referencing `SignalService`.
</action>
<acceptance_criteria>
- `packages/services/src/signals.service.ts` contains `createSignal` capable of handling FormData.
- `packages/shared-state/src/signals.store.ts` manages reactive signal arrays.
</acceptance_criteria>

### 5. Build Minimal Signal UI (Frontend)
<read_first>
- apps/web/src/pages/workspace/signals/index.tsx
- apps/web/react-router.config.ts
- .planning/1-CONTEXT.md
</read_first>
<action>
1. Create a workspace-level page `apps/web/src/pages/workspace/signals/index.tsx`.
2. Render a simple `<Table>` (from `@plane/ui`) mapping over `signalStore.signals`.
3. Include an "Upload Feedback" `<Button>` that opens a modal with a file `<Input>` and text area.
4. Hook up the form submit to `signalStore.createSignal`. 
5. Add the route `/workspace/:workspaceSlug/signals` to the React Router configuration.
</action>
<acceptance_criteria>
- `apps/web/src/pages/workspace/signals/index.tsx` exists and imports `@plane/ui`.
- React Router config includes the signals route.
</acceptance_criteria>

## Verification
- must_haves:
  - The API allows POST requests containing files.
  - The Celery task successfully flips the status flag.
  - The React UI lists created signals.
