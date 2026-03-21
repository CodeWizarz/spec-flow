# Testing

## Overview
All features require comprehensive unit tests. The project enforces quality checks across both the frontend and backend.

## Backend Testing
- **Framework**: `pytest`
- **Configuration**: Managed via `pytest.ini` and `.coveragerc`.
- **Execution**: 
  - Tests are primarily run using `run_tests.py` or the `run_tests.sh` wrapper script in `apps/api/`.
  - Specific test targeting is supported through these scripts.

## Frontend Testing
- **Unit Testing**: Tests reside alongside components and utilities in their respective `apps/` or `packages/`.
- **UI Components**: `@plane/ui` relies heavily on Storybook for component-level visual and functional isolation (run via `pnpm --filter=@plane/ui storybook` on port 6006).

## Continuous Integration
- Pre-commit hooks run via `husky` and `lint-staged` to enforce passing linters/formatters (`oxfmt`, `oxlint`) before code is committed.
