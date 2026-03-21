# Tech Stack

## Frontend (Web & App)
- **Framework**: React, React Router (v7)
- **State Management**: MobX (via `@plane/shared-state`), `swr` for data fetching
- **Styling**: Tailwind CSS
- **Build Tool**: Vite, Turbo repo for monorepo management
- **Language**: TypeScript (strict mode enabled)
- **UI Components**: `@plane/ui` internal package (Tailwind-based, Headless UI, Radix/Popper)
- **Editor**: ProseMirror-based rich text editor (`@plane/editor`)

## Backend (API)
- **Framework**: Django, Django Rest Framework (DRF)
- **Language**: Python (>=3.9)
- **Database**: PostgreSQL (via Django ORM)
- **Caching & Async**: Redis (via Celery/Channels)
- **Task Queue**: Celery

## Tooling & Quality
- **Package Manager**: pnpm (workspaces)
- **Linting**: OxLint (`oxlint`)
- **Formatting**: OxFmt (`oxfmt`)
- **Type Checking**: TypeScript (`tsc`)
- **Git Hooks**: Husky, lint-staged
- **Monorepo Tool**: Turborepo

## Services
- **Proxy**: Nginx (via `apps/proxy`)
- **Real-time**: Custom live service (`apps/live`)
