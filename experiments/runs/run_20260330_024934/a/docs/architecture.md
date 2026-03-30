# AgentHub Architecture

## Overview

AgentHub is a multi-agent orchestration platform built with FastAPI, PostgreSQL, and Redis. It provides a marketplace for AI agents, task scheduling, team collaboration, and billing capabilities.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Applications                      │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────────┐  │
│  │   Web UI    │  │   Mobile    │  │   API Clients     │  │
│  │  (Jinja2)   │  │   Apps      │  │  (Python/JS/etc)  │  │
│  └─────────────┘  └─────────────┘  └────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application Layer                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  API Routes                                           │  │
│  │  • /api/v1/auth/*     - Authentication               │  │
│  │  • /api/v1/agents/*   - Agent management             │  │
│  │  • /api/v1/tasks/*    - Task execution               │  │
│  │  • /api/v1/scheduler/*- Task scheduling              │  │
│  │  • /api/v1/billing/*  - Billing & payments           │  │
│  │  • /api/v1/teams/*    - Team collaboration           │  │
│  │  • /api/v1/usage/*    - Usage tracking               │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Frontend Routes                                      │  │
│  │  • /                 - Landing page                   │  │
│  │  • /dashboard        - User dashboard                 │  │
│  │  • /marketplace      - Agent marketplace              │  │
│  │  • /studio           - Agent development studio       │  │
│  │  • /scheduler        - Task scheduler UI              │  │
│  │  • /workspace        - Team workspace                 │  │
│  │  • /billing          - Billing & usage                │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
┌─────────────────────────────────┐  ┌─────────────────────────┐
│      Business Logic Layer       │  │     Data Access Layer   │
│  ┌─────────────────────────┐   │  │  ┌───────────────────┐  │
│  │  Agent Orchestration    │   │  │  │  SQLAlchemy ORM   │  │
│  │  • AgentRunner          │   │  │  │  • Models         │  │
│  │  • Task execution       │   │  │  │  • Sessions       │  │
│  │  • Memory management    │   │  │  │  • Transactions   │  │
│  └─────────────────────────┘   │  │  └───────────────────┘  │
│  ┌─────────────────────────┐   │  │                         │
│  │  Billing System         │   │  │  ┌───────────────────┐  │
│  │  • CreditManager        │   │  │  │  Redis Cache      │  │
│  │  • Stripe integration   │   │  │  │  • Session cache  │  │
│  │  • Invoice generation   │   │  │  │  • Rate limiting  │  │
│  └─────────────────────────┘   │  │  │  • Task queue     │  │
│  ┌─────────────────────────┐   │  │  └───────────────────┘  │
│  │  Scheduler              │   │  │                         │
│  │  • TaskRunner           │   │  │  ┌───────────────────┐  │
│  │  • Cron scheduling      │   │  │  │  Celery Workers   │  │
│  │  • Retry logic          │   │  │  │  • Async tasks    │  │
│  └─────────────────────────┘   │  │  │  • Background jobs│  │
│  ┌─────────────────────────┐   │  │  └───────────────────┘  │
│  │  Authentication         │   │  └─────────────────────────┘
│  │  • JWT tokens           │   │
│  │  • OAuth2 flows         │   │
│  │  • Password hashing     │   │
│  └─────────────────────────┘   │
└─────────────────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
┌─────────────────────────────────┐  ┌─────────────────────────┐
│       External Services         │  │      Data Storage       │
│  ┌─────────────────────────┐   │  │  ┌───────────────────┐  │
│  │  Stripe                 │   │  │  │  PostgreSQL       │  │
│  │  • Payments             │   │  │  │  • Users          │  │
│  │  • Subscriptions        │   │  │  │  • Agents         │  │
│  └─────────────────────────┘   │  │  │  • Tasks          │  │
│  ┌─────────────────────────┐   │  │  │  • Billing        │  │
│  │  Email Service          │   │  │  │  • Audit logs     │  │
│  │  • Notifications        │   │  │  └───────────────────┘  │
│  │  • Password reset       │   │  │                         │
│  └─────────────────────────┘   │  │  ┌───────────────────┐  │
│  ┌─────────────────────────┐   │  │  │  File Storage     │  │
│  │  AI Model Providers     │   │  │  │  • Agent configs  │  │
│  │  • OpenAI               │   │  │  │  • Task outputs   │  │
│  │  • Anthropic            │   │  │  │  • Logs           │  │
│  │  • Local models         │   │  │  └───────────────────┘  │
│  └─────────────────────────┘   │  └─────────────────────────┘
└─────────────────────────────────┘
```

## Core Components

### 1. FastAPI Application (`main.py`)
- **Purpose**: Application factory and entry point
- **Key Features**:
  - Lifespan management (database connections)
  - Router registration
  - Middleware setup (CORS, trusted hosts)
  - Static file serving
- **Dependencies**: All API and frontend routers

### 2. Database Layer (`db/`)
- **Models** (`models.py`):
  - `User`: Platform users with authentication
  - `Agent`: AI agent definitions and configurations
  - `Task`: Agent execution tasks
  - `CreditAccount`: User credit balances
  - `Invoice`: Billing invoices
  - `Team`: Team collaboration
  - `AuditLog`: Security audit trail
- **Session Management** (`session.py`):
  - SQLAlchemy engine configuration
  - Session factory
  - FastAPI dependency for database sessions

### 3. API Layer (`api/`)
- **Authentication** (`auth.py`): JWT-based auth, registration, login
- **Agents** (`agents.py`): CRUD operations for agents
- **Tasks** (`tasks.py`): Task execution and management
- **Scheduler** (`scheduler.py`): Task scheduling endpoints
- **Billing** (`billing.py`): Payment processing and credit management
- **Teams** (`teams.py`): Team collaboration endpoints
- **Usage** (`usage.py`): Usage tracking and analytics

### 4. Frontend Layer (`frontend/`)
- **Routes** (`routes.py`): Jinja2 template routes
- **Templates**: HTML templates with Bootstrap
- **Static Files**: CSS, JavaScript, images

### 5. Agent System (`agents/`)
- **Base Agent** (`base.py`): Abstract base class for all agents
- **Agent Runner** (`runner.py`): Execution engine for agents
- **Agent Studio** (`studio.py`): Development environment
- **Agent Catalog** (`catalog.py`): Marketplace catalog
- **Memory Management** (`memory.py`): Agent memory persistence

### 6. Billing System (`billing/`)
- **Credit Manager** (`credits.py`): Credit balance operations
- **Stripe Integration** (`stripe.py`): Payment processing
- **Invoice Generation** (`invoices.py`): Invoice creation
- **Subscription Plans** (`plans.py`): Plan definitions

### 7. Scheduler System (`scheduler/`)
- **Task Runner** (`runner.py`): Scheduled task execution
- **Scheduler Setup** (`setup.py`): APScheduler configuration

### 8. Authentication (`auth/`)
- **JWT Handling** (`jwt.py`): Token creation and validation
- **Security Utilities** (`security.py`): Password hashing
- **Dependencies** (`dependencies.py`): FastAPI dependencies
- **OAuth2** (`oauth2.py`): OAuth2 flows

### 9. Background Workers (`workers/`)
- **Task Processor** (`processor.py`): Celery task definitions

## Data Flow

### 1. User Registration Flow
```
User → POST /api/v1/auth/register → Create User → Create CreditAccount → Return JWT
```

### 2. Agent Execution Flow
```
User → POST /api/v1/tasks → Validate credits → Create Task → 
AgentRunner → Execute Agent → Update Task → Deduct credits → Return result
```

### 3. Scheduled Task Flow
```
User → POST /api/v1/scheduler/tasks → Validate schedule → Create ScheduledTask →
Celery Beat → Schedule job → Celery Worker → Execute Task → Update status
```

### 4. Payment Flow
```
User → POST /api/v1/billing/checkout → Create Stripe session → 
User pays → Stripe webhook → Verify payment → Add credits → Send receipt
```

## Database Schema

### Core Tables
```sql
-- Users and authentication
users (id, public_id, email, hashed_password, full_name, is_active, is_superuser, created_at)

-- AI agents
agents (id, public_id, name, description, config, owner_id, is_public, price, rating, created_at)

-- Agent execution tasks
tasks (id, public_id, name, description, agent_id, user_id, input_data, output_data, 
       status, scheduled_at, started_at, completed_at, error_message)

-- Credit management
credit_accounts (id, user_id, balance, currency, created_at, updated_at)
transactions (id, account_id, amount, type, description, reference_id, created_at)

-- Team collaboration
teams (id, public_id, name, description, owner_id, created_at)
team_members (id, team_id, user_id, role, joined_at)

-- Audit logging
audit_logs (id, user_id, action, resource_type, resource_id, details, ip_address, created_at)
```

## Security Architecture

### 1. Authentication
- JWT tokens with configurable expiration
- Password hashing with bcrypt
- Refresh token support
- Password reset via email

### 2. Authorization
- Role-based access control (RBAC)
- Resource-level permissions
- Team-based access control
- API key authentication

### 3. Data Protection
- SQL injection prevention (SQLAlchemy)
- XSS protection (Jinja2 autoescape)
- CSRF protection
- Input validation (Pydantic)

### 4. Audit Trail
- Comprehensive logging
- User action tracking
- Security event monitoring
- Compliance reporting

## Scalability Considerations

### 1. Horizontal Scaling
- Stateless application servers
- Database connection pooling
- Redis for session storage
- Load balancer ready

### 2. Performance Optimization
- Database indexing
- Query optimization
- Response caching
- Background processing

### 3. High Availability
- Database replication
- Redis clustering
- Health checks
- Graceful degradation

## Deployment Architecture

### Development
```
Local Machine → PostgreSQL → Redis → FastAPI (reload)
```

### Production (Docker)
```
Nginx → FastAPI (multiple workers) → PostgreSQL (replica) → Redis (cluster)
         ↑
   Celery Workers
```

### Cloud Deployment
```
Cloud Load Balancer → Auto-scaling group → RDS PostgreSQL → ElastiCache Redis
                              ↑
                       SQS + Lambda (background jobs)
```

## Monitoring and Observability

### 1. Metrics
- Prometheus metrics endpoint
- Custom business metrics
- Database performance metrics
- API response times

### 2. Logging
- Structured logging (JSON)
- Log levels (DEBUG, INFO, WARNING, ERROR)
- Centralized log aggregation
- Correlation IDs

### 3. Alerting
- Health check failures
- Error rate thresholds
- Performance degradation
- Security incidents

## Development Guidelines

### 1. Code Organization
- Follow in-source annotation protocol
- Semantic variable naming
- Type hints for all functions
- Comprehensive docstrings

### 2. Testing Strategy
- Unit tests for business logic
- Integration tests for APIs
- End-to-end tests for critical flows
- Performance tests for scalability

### 3. Documentation
- API documentation (OpenAPI/Swagger)
- Architecture documentation
- Deployment guides
- Troubleshooting guides

## Future Enhancements

### 1. Planned Features
- Real-time agent communication
- Advanced agent memory systems
- Multi-modal agent support
- Agent versioning and deployment

### 2. Technical Improvements
- GraphQL API layer
- WebSocket support
- Advanced caching strategies
- Machine learning model serving

### 3. Platform Expansion
- Mobile applications
- Desktop applications
- CLI tools
- Browser extensions

## Conclusion

AgentHub is designed as a scalable, secure platform for multi-agent orchestration. The architecture supports both technical and business requirements, with clear separation of concerns and extensibility points for future growth.