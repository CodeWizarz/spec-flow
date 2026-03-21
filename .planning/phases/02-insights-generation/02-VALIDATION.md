---
phase: 2
phase-slug: 02-insights-generation
date: 2026-03-21
---

# Phase 2: Insights Generation Validation Architecture

## Dimensions

### 1. Requirements Validation
- INS-01, INS-02: LLM payload maps directly to themes and core problems.
- INS-03: Evidence is displayed in the UI.

### 2. Integration Validation
- Celery correctly processes the large string chunks without blowing memory (in production this requires chunking, but for V1 MVP, a single prompt is acceptable).

### 3. Output Quality
- Generated JSON structurally matches the `Insight` database schema. Failure to parse must be caught gracefully and logged.

### 4. Code Quality
- All added files follow standard repo formatting.
