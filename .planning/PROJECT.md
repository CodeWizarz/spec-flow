# PROJECT

## What This Is
SpecFlow: An AI-powered product specification engine built on top of the existing Plane codebase. 

## Core Value
Users upload customer feedback (interviews, support tickets, notes). The system analyzes this unstructured data and directly answers "What should we build next?", outputting comprehensive spec documents (feature recommendations, evidence, UI/data/workflow changes, and coding-agent-ready development tasks). 

## Constraints & Parameters
- **Scope**: We are extending Plane, not rebuilding it. 
- **Focus**: Keep the UI minimal. The emphasis is entirely on backend data processing and high-quality AI outputs.
- **Milestone 1**: Must include Signals module, Insights generation, and Spec generator.

## Requirements

### Validated
*(Inferred from existing Plane codebase)*
- ✓ Workspace and Project structural foundation
- ✓ Authentication and basic permissions
- ✓ Internal REST API patterns (Django/DRF)
- ✓ Extensible component system (React/Turborepo)

### Active
- [ ] **Signals Module**: Store and manage unstructured customer feedback.
- [ ] **Insights Generation**: Analyze stored signals to extract recurring themes and core problems.
- [ ] **Spec Generator**: Translate insights into a full implementation spec containing:
     - Feature recommendation
     - Customer evidence (quotes)
     - UI, data model, and workflow change definitions
     - Development tasks strictly formatted for AI coding agents (Cursor/Claude Code)

### Out of Scope
- Rebuilding existing Plane features
- Complex, highly interactive reporting dashboards (UI should be kept minimal for M1)
- Automated code execution (We output tasks for agents, we do not execute the changes to Plane itself)

## Key Decisions
| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Implement as Plane extension | Reduces duplicated effort and leverages existing workspace/project hierarchy | Pending |
| Minimal UI for Milestone 1 | Focus developer energy on underlying AI prompts, data ingestion, and spec quality | Pending |

---
*Last updated: 2026-03-21 after initialization*

## Evolution
This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state
