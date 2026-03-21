# Conventions

## Global Guidelines
- **TypeScript**: Strict mode is enabled. All files must be properly typed.
- **Imports**: Use `workspace:*` for internal monorepo packages and `catalog:` for external dependencies to maintain consistency.
- **Naming Constraints**:
  - `camelCase` for variables and functions.
  - `PascalCase` for React components and TypeScript types/interfaces.
- **Error Handling**: Use try-catch blocks with proper error types, and log errors appropriately.

## Frontend & Packages
- **State Management**: Reactive patterns are utilized. Shared state is centralized in `packages/shared-state` using MobX.
- **UI Components**: Must be built within `@plane/ui` and developed/documented using Storybook for isolation and reusability.
- **Styling**: Tailwind CSS is the standard. Custom classes should be avoided in favor of Tailwind utility classes where possible.

## Backend (Django API)
- **Formatting & Linting**: Ruff is the standard tool (`tool.ruff` in `pyproject.toml`).
- **Style**: Adheres to PEP8 standards. Variable naming follows standard Python `snake_case`, classes `PascalCase`.
- **Complexity**: Ruff limits McCabe complexity to 10 to ensure readable code.

## Tooling
- **Check/Fix Workflows**: 
  - `pnpm fix` (runs format & lint fixes via `oxfmt` and `oxlint`).
  - `pnpm check` (runs all checks including `check:types`).
