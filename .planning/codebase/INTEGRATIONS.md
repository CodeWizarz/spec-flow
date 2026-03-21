# Integrations

## Core Infrastructure
- **Database**: PostgreSQL (Relational DB for core data)
- **Cache / PubSub**: Redis (Session management, caching, real-time sync)
- **Storage**: AWS S3 / MinIO (Asset storage, attachments)

## Third-Party Integrations
- **Authentication**: 
  - OAuth (Google, GitHub, generic SAML/OIDC via standard Django plugins)
- **Email**: SMTP server integrations (SendGrid, AWS SES, etc. via Django email backends)
- **Workspace Sync / Issue Tracking**:
  - GitHub (Sync issues, PRs)
  - GitLab
  - Slack / Discord (Webhooks / Notifications)
- **Analytics / Tracking**:
  - PostHog (for product analytics, often found in Plane setups)

## Internal Ecosystem
- **Live Sync**: `apps/live` for real-time WebSockets synchronization.
- **Proxy**: `apps/proxy` for routing requests between web, api, and live services.
