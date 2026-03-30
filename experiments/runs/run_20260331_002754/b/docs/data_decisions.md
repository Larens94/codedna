# Data Layer Architecture Decisions

## Date: 2025-02-23

### Database ORM Strategy

**Decision**: Maintain dual database setup for FastAPI and Flask compatibility.

**Rationale**:
- Existing codebase uses Flask-SQLAlchemy (`db.Model`) for models
- Flask app is used for Celery tasks and CLI commands
- FastAPI app needs SQLAlchemy sessions for dependency injection
- Both can share the same database engine and metadata

**Implementation**:
- Keep existing models as `db.Model` (Flask-SQLAlchemy declarative base)
- For FastAPI, create sessions using `db.session` or create new sessions from `db.engine`
- Update `database.py` to use `db.engine` instead of creating separate engine
- Ensure migrations work with Flask-Migrate (Alembic)

### New Models Required

Based on requirements, we need to implement:

1. **Organization** - for multi-tenancy support
2. **OrgMembership** - user membership in organizations
3. **ScheduledTask** - recurring task scheduling
4. **Memory** - agent memory storage with vector embeddings
5. **UsageLog** - token usage tracking and cost calculation
6. **AuditLog** - system audit trail
7. **CreditTransaction** - track credit changes (separate from Invoice)

### Credit System Design

**Architecture**:
- Credits are stored as integer (smallest unit = 1 credit = $0.01)
- Each user has a `CreditAccount` with `balance` and `credit_limit`
- `CreditTransaction` records all changes (deductions, refunds, purchases)
- Real-time balance calculation via `balance = sum(amount)`
- Credit limits enforced per plan type

**Plans**:
- **Free**: 100 credits/month, no rollover
- **Starter**: 1,000 credits/month, $10/month
- **Pro**: 10,000 credits/month, $99/month  
- **Enterprise**: 100,000 credits/month, custom pricing

### Billing Integration

**Stripe Integration**:
- Use `stripe` Python library
- Create checkout sessions for credit purchases
- Webhook handlers for payment events (idempotent)
- Invoice generation via Stripe (with PDF download)

**Idempotency**:
- Store Stripe event IDs to prevent duplicate processing
- Use database transactions for credit updates

### Scheduler Implementation

**Choice**: APScheduler over Celery for simplicity

**Rationale**:
- APScheduler integrates well with FastAPI/Flask
- No external broker required
- Suitable for scheduled tasks (cron-like)
- Celery already used for async tasks, but APScheduler better for recurring

**Implementation**:
- Background scheduler with SQLAlchemy job store
- Job definitions for recurring agent runs
- Task runner that executes agents and saves results

### Memory Manager

**Storage**: SQLite with SQLite-VSS extension for vector similarity

**Alternative**: Use `pgvector` if PostgreSQL, but SQLite-VSS is simpler for development

**Schema**:
- `Memory` table with `agent_id`, `user_id`, `content`, `embedding` (BLOB), `metadata`
- Vector similarity search using cosine distance
- Memory categories: short-term, long-term, episodic

### Token Usage Tracking

**Implementation**:
- `UsageLog` records each API call with token counts
- Real-time cost calculation using provider pricing
- Aggregated daily/monthly usage reports
- Integration with credit system for automatic deduction

### Database Migrations

**Tool**: Flask-Migrate (Alembic) already configured

**Approach**:
- Create migration for new models
- Seed data for demo user and marketplace agents
- Migration scripts should be idempotent

### Seed Script

**Requirements**:
- Create demo user with Free plan credits
- Create 6 marketplace agents with different categories
- Create default pricing plans
- Create sample agent runs for demonstration

### Code Organization

```
app/
├── models/
│   ├── __init__.py
│   ├── user.py
│   ├── agent.py
│   ├── agent_run.py
│   ├── subscription.py
│   ├── organization.py (new)
│   ├── memory.py (new)
│   ├── usage_log.py (new)
│   └── audit_log.py (new)
├── billing/
│   ├── __init__.py
│   ├── credit_engine.py
│   ├── stripe_integration.py
│   └── invoice_generator.py
├── scheduler/
│   ├── __init__.py
│   ├── scheduler.py
│   └── task_runner.py
└── memory/
    ├── __init__.py
    ├── manager.py
    └── vector_store.py
```

### Security Considerations

- Audit logging for all credit transactions
- Rate limiting on credit deduction
- Webhook signature verification
- SQL injection prevention via ORM
- Data encryption at rest for sensitive fields

### Performance Considerations

- Indexes on frequently queried columns
- Batch operations for credit updates
- Caching for plan limits
- Connection pooling for database

### Testing Strategy

- Unit tests for credit engine
- Integration tests for Stripe webhooks
- Performance tests for scheduler
- Memory search accuracy tests