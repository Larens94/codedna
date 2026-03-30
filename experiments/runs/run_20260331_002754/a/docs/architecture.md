# AgentHub SaaS Architecture

## Technology Stack

### Backend
- **Framework**: FastAPI (async, auto-generated docs, type hints)
- **Database**: PostgreSQL 15+ (primary), Redis 7+ (caching, sessions, queues)
- **ORM**: SQLAlchemy 2.0 + asyncpg driver
- **Migrations**: Alembic
- **Authentication**: JWT (access/refresh tokens), API keys (hash-salted)
- **Task Queue**: Celery + Redis broker (for long-running agent tasks)
- **Background Scheduler**: APScheduler (for periodic tasks)
- **Email**: SendGrid / SMTP via FastAPI-Mail
- **File Storage**: AWS S3 / MinIO (for agent outputs, file uploads)

### Frontend
- **Framework**: Next.js 14 (React, App Router)
- **UI Library**: shadcn/ui + Tailwind CSS
- **State Management**: Zustand
- **API Client**: TanStack Query (React Query)
- **Forms**: React Hook Form + Zod validation

### Infrastructure
- **Containerization**: Docker + Docker Compose (development)
- **Orchestration**: Kubernetes (production)
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana
- **Logging**: Structured JSON logs with Loki
- **Tracing**: OpenTelemetry

### External Integrations
- **AI Agent Framework**: Agno (via Python SDK)
- **Payment Processing**: Stripe (subscriptions, usage billing)
- **Analytics**: PostHog (self-hosted)
- **Error Tracking**: Sentry

## Directory Structure

```
agenthub-saas/
├── docker/
│   ├── db/
│   ├── redis/
│   └── nginx/
├── docs/
│   ├── architecture.md
│   └── api-specs/
├── src/
│   ├── main.py                      # Application entry point
│   ├── config/                      # Configuration management
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── database.py
│   │   ├── security.py
│   │   └── celery.py
│   ├── core/                        # Core application logic
│   │   ├── __init__.py
│   │   ├── app_factory.py           # Main application factory
│   │   ├── database.py              # Database session management
│   │   ├── security.py              # Authentication/authorization
│   │   ├── dependencies.py          # FastAPI dependency injection
│   │   ├── middleware.py            # Custom middleware
│   │   └── exceptions.py            # Custom exceptions
│   ├── api/                         # API layer
│   │   ├── __init__.py
│   │   ├── v1/                      # API version 1
│   │   │   ├── __init__.py
│   │   │   ├── router.py            # Main router aggregator
│   │   │   ├── auth/
│   │   │   ├── users/
│   │   │   ├── organizations/
│   │   │   ├── agents/
│   │   │   ├── tasks/
│   │   │   ├── billing/
│   │   │   └── admin/
│   │   └── schemas/                 # Pydantic models
│   │       ├── auth.py
│   │       ├── users.py
│   │       └── ...
│   ├── models/                      # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── organization.py
│   │   ├── agent.py
│   │   ├── task.py
│   │   ├── usage.py
│   │   ├── billing.py
│   │   └── base.py                  # Base model with common fields
│   ├── services/                    # Business logic services
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── agent_service.py
│   │   ├── task_service.py
│   │   ├── billing_service.py
│   │   ├── agno_integration.py      # Agno framework integration
│   │   ├── stripe_integration.py
│   │   └── scheduler_service.py
│   ├── workers/                     # Celery workers
│   │   ├── __init__.py
│   │   ├── celery_app.py
│   │   └── tasks/
│   │       ├── agent_tasks.py
│   │       ├── billing_tasks.py
│   │       └── notification_tasks.py
│   ├── utils/                       # Utility functions
│   │   ├── __init__.py
│   │   ├── validators.py
│   │   ├── security.py
│   │   ├── datetime.py
│   │   └── file_storage.py
│   └── tests/                       # Test suite
│       ├── __init__.py
│       ├── conftest.py
│       ├── api/
│       ├── services/
│       └── utils/
├── frontend/                        # Next.js frontend
│   ├── app/
│   ├── components/
│   ├── lib/
│   └── public/
├── scripts/                         # Deployment/management scripts
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.frontend
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml                   # Python project config
└── .env.example
```

## Core Architecture Patterns

### Application Factory Pattern
- **Purpose**: Enable multiple application instances with different configurations (testing, development, production)
- **Implementation**: `create_app()` function in `core/app_factory.py` that:
  - Loads configuration from environment variables
  - Initializes database connection pool
  - Sets up dependency injection container
  - Registers all middleware
  - Mounts API routers
  - Configures Celery integration
  - Returns configured FastAPI instance

### Database Layer
- **Async SQLAlchemy 2.0**: Non-blocking database operations
- **Session Management**: Request-scoped sessions with automatic cleanup
- **Model Inheritance**: All models inherit from `Base` with:
  - `id` (UUID primary key)
  - `created_at` (timestamp)
  - `updated_at` (timestamp, auto-update)
  - `deleted_at` (soft delete support)
- **Repository Pattern**: Services interact with models via repository pattern for testability

### Authentication & Authorization
- **JWT Tokens**: Access tokens (15 min) + refresh tokens (7 days)
- **API Keys**: Per-agent API keys for programmatic access
- **Role-Based Access Control (RBAC)**:
  - `super_admin` (system-wide admin)
  - `org_admin` (organization admin)
  - `org_member` (organization member)
  - `agent` (service account for agents)
- **Organization Isolation**: All data queries automatically scoped to user's organization

### Configuration Management
- **Environment Variables**: Primary configuration source
- **Pydantic Settings**: Type-safe settings validation with `.env` support
- **Feature Flags**: Toggle features without deployment
- **Multiple Environments**: `development`, `staging`, `production`, `testing`

### Error Handling
- **Structured Error Responses**: Consistent JSON error format
- **HTTP Status Codes**: Proper use of 4xx/5xx codes
- **Exception Hierarchy**: Custom exceptions for different error types
- **Global Exception Handlers**: Centralized error handling middleware

## Database Schema Design

### Core Entities

#### Users (`users` table)
- `id` (UUID, primary key)
- `email` (unique, indexed)
- `hashed_password` (argon2 hash)
- `full_name`
- `is_active` (boolean)
- `is_verified` (boolean)
- `role` (enum: super_admin, org_admin, org_member)
- `current_organization_id` (FK to organizations)
- `email_verified_at` (timestamp)
- `last_login_at` (timestamp)
- `created_at`, `updated_at`, `deleted_at`

#### Organizations (`organizations` table)
- `id` (UUID, primary key)
- `name` (unique within system)
- `slug` (URL-friendly identifier)
- `owner_id` (FK to users)
- `is_active` (boolean)
- `plan_tier` (enum: free, pro, enterprise)
- `billing_email`
- `stripe_customer_id`
- `stripe_subscription_id`
- `trial_ends_at` (timestamp)
- `created_at`, `updated_at`, `deleted_at`

#### Organization Members (`organization_members` table)
- `id` (UUID, primary key)
- `organization_id` (FK to organizations)
- `user_id` (FK to users)
- `role` (enum: admin, member)
- `invited_by_id` (FK to users)
- `invited_at` (timestamp)
- `joined_at` (timestamp)
- `created_at`, `updated_at`

#### Agents (`agents` table)
- `id` (UUID, primary key)
- `organization_id` (FK to organizations)
- `name`
- `description`
- `type` (enum: text, voice, vision, multimodal)
- `config` (JSONB - agent configuration)
- `api_key_hash` (hashed API key for agent authentication)
- `api_key_last_used` (timestamp)
- `is_active` (boolean)
- `created_by_id` (FK to users)
- `created_at`, `updated_at`, `deleted_at`

#### Tasks (`tasks` table)
- `id` (UUID, primary key)
- `organization_id` (FK to organizations)
- `agent_id` (FK to agents)
- `type` (enum: async, sync, scheduled)
- `status` (enum: pending, running, completed, failed, cancelled)
- `input_data` (JSONB - task input)
- `output_data` (JSONB - task output/result)
- `error_message` (text)
- `started_at` (timestamp)
- `completed_at` (timestamp)
- `scheduled_for` (timestamp for scheduled tasks)
- `priority` (integer)
- `metadata` (JSONB - additional metadata)
- `created_by_id` (FK to users)
- `created_at`, `updated_at`

#### Usage Records (`usage_records` table)
- `id` (UUID, primary key)
- `organization_id` (FK to organizations)
- `agent_id` (FK to agents, nullable)
- `task_id` (FK to tasks, nullable)
- `metric_type` (enum: token_count, execution_time, api_call, storage_bytes)
- `metric_value` (decimal)
- `cost_in_cents` (integer)
- `recorded_at` (timestamp)
- `billing_period` (string, e.g., "2024-03")
- `is_billed` (boolean)
- `created_at`

#### Billing Events (`billing_events` table)
- `id` (UUID, primary key)
- `organization_id` (FK to organizations)
- `type` (enum: subscription_created, subscription_updated, payment_succeeded, payment_failed, invoice_created)
- `stripe_event_id` (unique)
- `stripe_customer_id`
- `stripe_subscription_id` (nullable)
- `stripe_invoice_id` (nullable)
- `data` (JSONB - full event data from Stripe)
- `processed_at` (timestamp)
- `created_at`

#### Audit Logs (`audit_logs` table)
- `id` (UUID, primary key)
- `organization_id` (FK to organizations, nullable)
- `user_id` (FK to users, nullable)
- `action` (string - e.g., "user.login", "agent.create")
- `resource_type` (string - e.g., "user", "agent")
- `resource_id` (UUID, nullable)
- `ip_address` (string)
- `user_agent` (string)
- `metadata` (JSONB - additional context)
- `created_at`

## API Layer Design

### RESTful Endpoints
- **Versioning**: URL path versioning (`/api/v1/...`)
- **Resource-Oriented**: Nouns as resources, HTTP methods as actions
- **Nested Resources**: When appropriate (e.g., `/api/v1/organizations/{org_id}/agents`)
- **Pagination**: Cursor-based pagination for lists
- **Filtering & Sorting**: Query parameters for filtering, sorting, field selection

### Request/Response Models
- **Pydantic Schemas**: Separate models for:
  - `CreateSchema` (input for POST)
  - `UpdateSchema` (input for PATCH)
  - `ResponseSchema` (output for GET)
  - `ListSchema` (paginated list response)
- **Validation**: Automatic validation with informative error messages
- **Serialization**: Custom serializers for complex types

### Rate Limiting
- **Token Bucket Algorithm**: Redis-backed rate limiting
- **Tiers**: Different limits based on plan tier
- **Headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

## Integration Points

### Agno Framework Integration
- **Service Layer**: `AgnoIntegrationService` handles communication with Agno SDK
- **Async Execution**: Non-blocking agent execution via Celery tasks
- **State Management**: Store agent state in Redis for long-running conversations
- **Streaming Support**: Server-Sent Events (SSE) for real-time output

### Stripe Integration
- **Webhooks**: Secure endpoint for Stripe events
- **Idempotency**: Prevent duplicate event processing
- **Sync Service**: Periodic sync of subscription status
- **Usage-Based Billing**: Metered billing based on usage records

### Task Queue (Celery)
- **Broker**: Redis as message broker
- **Result Backend**: Redis for task results
- **Task Routing**: Separate queues for different task types
- **Retry Logic**: Exponential backoff for failed tasks
- **Monitoring**: Flower for Celery monitoring

### Scheduler (APScheduler)
- **In-Process Scheduler**: For lightweight periodic tasks
- **Persistent Storage**: SQLAlchemy job store for cluster deployments
- **Job Types**:
  - Usage aggregation (daily)
  - Subscription checks (hourly)
  - Agent health checks (every 5 minutes)
  - Audit log cleanup (weekly)

## Security Considerations

### Data Protection
- **Encryption at Rest**: Database fields with sensitive data encrypted
- **Encryption in Transit**: TLS 1.3 for all communications
- **API Key Storage**: Hash-salted API keys (like passwords)

### Access Control
- **Organization Isolation**: Row-level security via application logic
- **Principle of Least Privilege**: Minimal permissions for each role
- **API Key Scopes**: Fine-grained permissions per API key

### Audit & Compliance
- **Comprehensive Logging**: All actions logged to audit table
- **Data Retention Policies**: Automated cleanup of old data
- **GDPR Compliance**: Right to erasure, data export tools

## Deployment Architecture

### Development Environment
- **Docker Compose**: Single command to start all services
- **Hot Reload**: Automatic reload on code changes
- **Test Data**: Seed scripts for development data

### Production Environment
- **Kubernetes**: Container orchestration
- **Horizontal Pod Autoscaler**: Automatic scaling based on CPU/memory
- **Ingress Controller**: Nginx for load balancing and SSL termination
- **Persistent Volumes**: For database and file storage
- **Backup Strategy**: Automated database backups

### High Availability
- **Database**: PostgreSQL with read replicas
- **Redis**: Redis Cluster for high availability
- **Stateless Application**: FastAPI instances can be scaled horizontally
- **Load Balancer**: Round-robin load balancing with health checks

### Monitoring & Observability
- **Metrics**: Prometheus metrics endpoint
- **Log Aggregation**: Loki for centralized logs
- **Distributed Tracing**: OpenTelemetry for request tracing
- **Alerting**: AlertManager for critical issues

## Scaling Strategy

### Database Scaling
- **Read Replicas**: For reporting and analytics queries
- **Connection Pooling**: PgBouncer for connection management
- **Query Optimization**: Indexing strategy, query analysis

### Application Scaling
- **Stateless Design**: No local session storage
- **Horizontal Scaling**: Add more FastAPI instances as needed
- **Caching Strategy**: Redis cache for frequently accessed data

### File Storage Scaling
- **CDN Integration**: For static assets and agent outputs
- **Multi-Region**: S3 cross-region replication for global access

## Migration Strategy

### Zero-Downtime Deployments
- **Blue-Green Deployment**: Switch between identical environments
- **Database Migrations**: Backward-compatible schema changes
- **Feature Flags**: Roll out features gradually

### Data Migration
- **Alembic Migrations**: Version-controlled schema changes
- **Data Backfills**: Scripts for data transformation
- **Rollback Plan**: Quick rollback procedure for failed deployments

---

*Last Updated: 2024-03-30*
*Author: Product Architect*