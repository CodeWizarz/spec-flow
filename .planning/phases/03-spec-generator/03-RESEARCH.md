# Phase 3: Spec Generation Research

## Technical Discoveries

### Backend Architecture
1. **Data Model**: `GeneratedSpec` requires simply a title and content block, tying back to the workspace.
2. **LLM Formatting**: Unlike Phase 2 which enforced strict JSON output, Phase 3 relies on semantic structure (Markdown). We will prompt the model using standard role assignments in `openai` to output pure markdown without code block encapsulations (or strip them before saving).
3. **Agent Schema Compliance**: We must force the model to output steps that Claude Code can run seamlessly. Example format requested in the prompt:
    ```xml
    ### Task 1: Do something
    <read_first>
    - file.py
    </read_first>
    <action>
    - Add function x
    </action>
    ```

### Frontend Architecture
1. **Export Functionality**: A simple standard anchor tag with a download attribute backed by a `URL.createObjectURL(new Blob(...))` serves as a lightweight and reliable `.md` file exporter. No heavy PDF dependencies required.
