# Concerns

## Monorepo Management
- Given the high number of interwoven packages in `packages/`, managing the build dependency graph can be complex. Circular dependencies or breaking changes in `packages/ui` or `packages/shared-state` have a wide blast radius across the client applications.

## State Synchronization
- The application blends server-state fetching (via SWR/React Query-like patterns) with global client state (MobX). Ensuring these two paradigms don't conflict or fall out of sync requires careful cache invalidation and reactivity management.

## Real-time Consistency
- The `apps/live` service handles real-time WebSockets synchronization. Ensuring that events broadcasted from the Django API correctly reach Redis, are parsed properly by the Node.js Live server, and then correctly hydrate MobX stores on the client without race conditions is a challenging area of the codebase.

## Permissions & Data Access
- Custom roles and workspace-level permissions apply across both the frontend UI (hiding/showing buttons) and backend (DRF permission classes). Keeping these in sync is crucial to prevent unauthorized access or confusing UI states.
