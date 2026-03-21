# Phase 1: Signals Module Context

## Implementation Decisions

### 1. Data Model Anchoring
- **Decision:** Signals are tied to a `Workspace`, not a `Project`.
- **Reasoning:** Customer feedback (signals) often spans multiple projects or applies to the product generally. Tying them to the workspace level allows cross-project insights to be generated later in the pipeline.

### 2. Ingestion Format & Processing
- **Decision:** Dual-path processing depending on payload type.
  - **Simple text input:** Process immediately (synchronously) during the API request.
  - **File uploads (e.g., PDFs, images):** Process asynchronously via Celery (`bgtasks`) to extract text.
- **Reasoning:** Keeps the API snappy for standard feedback entry but offloads heavy document parsing to background workers.

### 3. State Management
- **Decision:** Signals are deposited directly into the active pool.
- **Reasoning:** Keep Milestone 1 simple. No manual triage or review queue is needed before the AI can analyze the uploaded signals.

## Code Context Guidelines
- **Models:** The `Signal` model should use `Workspace` as a foreign key or related entity.
- **Background Tasks:** Leverage `apps/api/plane/bgtasks/` and `celery.py` for defining the async file extraction jobs.
- **API:** Build standard REST endpoints for CRUD operations and handling multipart uploads if a file is present.
