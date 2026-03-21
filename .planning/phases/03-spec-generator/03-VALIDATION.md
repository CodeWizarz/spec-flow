---
phase: 3
phase-slug: 03-spec-generator
date: 2026-03-21
---

# Phase 3: Spec Generator Validation Architecture

## Dimensions

### 1. Requirements Validation
- SPC-01: Full spec outputs strictly to a PostgreSQL JSONField.
- SPC-02: Output explicitly separates features, UI, data model, and workflow sections inside the JSON graph.
- SPC-03: Development tasks include XML-style boundaries (`read_first`, `action`) as structured array items.
- SPC-04: The browser derives a `.md` file with correct headers from the JSON data dynamically.

### 2. Integration Validation
- `insight_ids` are mapped effectively. If empty, the backend processes all recent active insights. 

### 3. Stability
- Markdown string encodings correctly display in the browser.
