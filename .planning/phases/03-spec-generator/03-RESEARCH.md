# Phase 3: Spec Generation Research

## Technical Discoveries

### Backend Architecture
1. **Data Model**: `GeneratedSpec` requires a title and a `spec_json` JSONField.
2. **LLM Formatting**: We will use strict structured output (JSON object) enforcing the keys: `feature_name`, `problem`, `user_story`, `solution`, `ui_changes`, `data_model_changes`, `workflow_changes`, `tasks`. 
3. **Agent Schema Compliance**: `tasks` should be an array of objects. We will derive Markdown locally when generating the download file, building `<read_first>` and `<action>` logic from the structured tasks natively.

### Frontend Architecture
1. **UI Rendering**: The view maps over the JSON object keys to create structured components (e.g., standard generic Cards displaying arrays of strings for `ui_changes`).
2. **Export Functionality**: A simple standard anchor tag with a download attribute backed by a `URL.createObjectURL(new Blob(...))` compiling the JSON fields logically into a `.md` template on the client side.
