# Architecture

## Overview
Plane is structured as a scalable, service-oriented monorepo. It separates concerns between the client applications, the core RESTful API, and real-time synchronization.

### 1. Client Applications (`apps/web`, `apps/admin`, `apps/space`)
- **Web App**: Built with React Router (v7) and Vite. Serves as the primary user interface for workspace management, project tracking, and issues.
- **Component Model**: The frontend relies heavily on isolated, shared packages within `packages/` (e.g., `@plane/ui` for UI components, `@plane/editor` for rich text editing).
- **State Management**: Uses MobX to manage complex reactive state across the application (`@plane/shared-state`), combined with SWR for data fetching.

### 2. Core API (`apps/api`)
- **Django Framework**: Provides the core business logic, authentication, permissions, and REST APIs.
- **Data Persistence**: Backed by PostgreSQL. Complex queries and aggregations are handled via Django ORM.
- **Asynchronous Tasks**: Relies on Celery and Redis to handle background processing (emails, integrations sync, exports).

### 3. Real-time Service (`apps/live`)
- A dedicated microservice responsible for real-time collaboration and live updates across clients.
- Communicates with clients via WebSockets.
- Uses Redis Pub/Sub to listen for specific events broadcasted by the API and push them to relevant clients.

### 4. Reverse Proxy (`apps/proxy`)
- Used in deployment and local development to route traffic appropriately to `web`, `api`, or `live` based on the path (e.g., `/api` -> `apps/api`).
