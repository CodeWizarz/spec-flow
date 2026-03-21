# Directory Structure

Plane is a Turborepo-based monorepo. Code is divided into deployable applications and reusable packages.

```text
plane/
├── apps/
│   ├── admin/       # Instance administration dashboard
│   ├── api/         # Core Django REST API backend
│   ├── live/        # Real-time WebSocket service
│   ├── proxy/       # Nginx-based reverse proxy
│   ├── space/       # Plane Spaces (public/guest view applications)
│   └── web/         # Main Plane project management application
│
├── packages/
│   ├── codemods/    # Scripts for codebase migrations
│   ├── constants/   # Shared constants across frontend apps
│   ├── decorators/  # Common decorators
│   ├── editor/      # ProseMirror-based rich text editor module
│   ├── hooks/       # Reusable React hooks
│   ├── i18n/        # Internationalization dictionaries and utilities
│   ├── logger/      # Standardized logging library
│   ├── propel/      # AI / propel service connectors 
│   ├── services/    # API interaction services
│   ├── shared-state/# MobX stores and reactive state definitions
│   ├── ui/          # Core design system and UI components (Headless UI + Tailwind)
│   └── utils/       # Shared helper functions
│
├── deployments/     # Docker compose and deployment configuration files
└── docs/            # Project documentation and guides
```

## Workflows
- Internal packages are linked via `workspace:*` (e.g., `"@plane/ui": "workspace:*"`).
- Third-party dependencies use `catalog:` references to ensure identical versions across the monorepo.
