# AgentHub - Complete System Architecture

## Overview

AgentHub is a SaaS platform for discovering, running, and managing AI agents through a marketplace model. The system follows a monolithic architecture with clear separation of concerns, designed for scalability and maintainability.

## Technology Stack

### Backend Framework
- **Flask 2.3.3**: Lightweight WSGI web application framework with extensions
- **Celery 5.3.1**: Distributed task queue for asynchronous processing
- **Redis 7.x**: Message broker for Celery and caching layer

### Database & ORM
- **PostgreSQL 15**: Primary relational database (production)
- **SQLite**: Development and testing database
- **SQLAlchemy 2.0**: Python SQL toolkit and ORM
- **Alembic**: Database migration tool

### Authentication & Security
- **Flask-JWT-Extended**: JWT-based authentication
- **Flask-Bcrypt**: Password hashing
- **Flask-CORS**: Cross-Origin Resource Sharing
- **python-jose**: JWT encoding/decoding

### API & Serialization
- **Flask-RESTful**: REST API framework
- **Marshmallow**: Object serialization/deserialization
- **Pydantic**: Data validation and settings management

### External Integrations
- **Stripe**: Payment processing and subscription management
- **Agno Framework**: AI agent execution platform
- **Flask-Mail**: Email notifications
- **Requests**: HTTP client for external APIs

### Development & Testing
- **pytest**: Testing framework
- **black**: Code formatting
- **flake8**: Code linting
- **mypy**: Type checking

### Monitoring & Logging
- **structlog**: Structured logging
- **Prometheus Flask Exporter**: Metrics collection
- **Flower**: Celery monitoring

## System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Applications                     │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐   │
│  │   Web App   │  │  Mobile App │  │   3rd Party API  │   │
│  └─────────────┘  └─────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   API Gateway / Load Balancer               │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    Flask Application Server                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                   Application Layer                  │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │  │
│  │  │   Auth   │ │  Agents  │ │ Marketplace │ │ Billing│ │  │
│  │  │  Module  │ │  Module  │ │  Module   │ │ Module │ │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └─────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                               │
                 ┌─────────────┼─────────────┐
                 ▼             ▼             ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Service Layer │  │   Data Layer    │  │   Task Layer    │
│ ┌─────────────┐ │  │ ┌─────────────┐ │  │ ┌─────────────┐ │
│ │  Agent      │ │  │ │  Database   │ │  │ │   Celery    │ │
│ │  Service    │ │  │ │  Models     │ │  │ │   Workers   │ │
│ ├─────────────┤ │  │ ├─────────────┤ │  │ ├─────────────┤ │
│ │  Billing    │ │  │ │ Repositories│ │  │ │ Scheduled   │ │
│ │  Service    │ │  │ │             │ │  │ │   Tasks     │ │
│ ├─────────────┤ │  │ └─────────────┘ │  │ └─────────────┘ │
│ │  User       │ │  │                 │  │                 │
│ │  Service    │ │  │                 │  │                 │
│ └─────────────┘ │  │                 │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 External Service Integrations               │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────┐   │
│  │    Stripe   │  │    Agno     │  │   Email Service  │   │
│  │  Payments   │  │  Framework  │  │   (SendGrid)     │   │
│  └─────────────┘  └─────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. Application Layer (Flask App Factory)
- **Application Factory Pattern**: Modular app initialization
- **Configuration Management**: Environment-based configs
- **Dependency Management**: Clean service instantiation
- **Extension Initialization**: Centralized extension setup

#### 2. API Layer (RESTful Endpoints)
- **Blueprint Architecture**: Modular route organization
- **Versioned API**: `/api/v1/` URL prefix
- **Request Validation**: Marshmallow schemas
- **Error Handling**: Consistent error responses
- **Authentication Middleware**: JWT validation

#### 3. Service Layer (Business Logic)
- **Agent Service**: Agent lifecycle management
- **Billing Service**: Subscription and payment processing
- **User Service**: User management and authentication
- **Marketplace Service**: Agent discovery and search
- **Execution Service**: Agent run orchestration

#### 4. Data Layer (Persistence)
- **Repository Pattern**: Data access abstraction
- **SQLAlchemy Models**: Database schema definition
- **Alembic Migrations**: Schema evolution
- **Connection Pooling**: Database performance optimization

#### 5. Task Layer (Background Processing)
- **Celery Workers**: Asynchronous job processing
- **Task Scheduling**: Periodic background jobs
- **Result Backends**: Task result storage
- **Monitoring**: Flower dashboard for task monitoring

#### 6. Integration Layer (External Services)
- **Agno Integration**: AI agent framework client
- **Stripe Integration**: Payment processing
- **Email Integration**: Transactional email sending
- **File Storage**: Cloud storage integration

### Data Model

#### Core Entities

1. **User**
   - Authentication credentials and profile
   - Subscription relationships
   - Billing account association
   - Agent ownership and usage tracking

2. **Agent**
   - Marketplace listing metadata
   - Version management through AgentVersion
   - Pricing and categorization
   - Owner relationships and permissions

3. **AgentVersion**
   - Versioned agent configurations
   - Agno framework integration IDs
   - Active version tracking
   - Configuration schema validation

4. **AgentRun**
   - Execution tracking and history
   - Input/output data storage
   - Performance metrics collection
   - Cost calculation and billing

5. **Subscription**
   - Plan association and billing cycle
   - Status tracking (active, canceled, expired)
   - Stripe subscription ID mapping
   - Renewal and cancellation logic

6. **Plan**
   - Tier definitions and pricing
   - Feature sets and limits
   - Stripe price ID mapping
   - Upgrade/downgrade paths

7. **BillingAccount**
   - Payment method information
   - Invoice generation and management
   - Credit balance tracking
   - Tax calculation support

#### Database Schema Relationships

```
User 1───┐ 1 BillingAccount
│          │
│ 1        │
▼          ▼
Subscription ──── 1 Plan
│
│ *
▼
Agent ──── * AgentVersion
│          │
│ *        │ 1
▼          ▼
AgentRun ──── User
```

### API Design

#### Authentication Flow
1. **Registration**: `POST /api/v1/auth/register`
2. **Login**: `POST /api/v1/auth/login` → Returns access/refresh tokens
3. **Token Refresh**: `POST /api/v1/auth/refresh`
4. **Logout**: `POST /api/v1/auth/logout`

#### Rate Limiting Strategy
- **Free Tier**: 100 requests/minute
- **Basic Tier**: 500 requests/minute  
- **Pro Tier**: 2000 requests/minute
- **Team Tier**: 5000 requests/minute

#### Pagination & Filtering
- **Cursor-based pagination**: For large datasets
- **Field selection**: Reduce payload size
- **Filtering**: By category, price, rating, etc.
- **Sorting**: By popularity, price, recency

#### Webhook Support
- **Stripe Events**: Payment success, subscription changes
- **Agent Execution Events**: Run completion, errors
- **User Events**: Registration, plan changes

### Security Architecture

#### Authentication & Authorization
- **JWT with RSA256**: Asymmetric signing for enhanced security
- **Refresh Token Rotation**: Automatic token refresh with rotation
- **Role-Based Access Control**: User, Admin, SuperAdmin roles
- **Resource-Level Permissions**: Fine-grained access control

#### Data Protection
- **Encryption at Rest**: Sensitive data encryption in database
- **HTTPS Enforcement**: TLS 1.3 required for all endpoints
- **Secure Password Storage**: bcrypt with high work factor (12 rounds)
- **Input Validation & Sanitization**: SQL injection and XSS prevention

#### API Security
- **CORS Configuration**: Strict origin validation
- **Rate Limiting**: Tier-based request limits
- **Request Validation**: Schema-based input validation
- **Security Headers**: HSTS, CSP, XSS protection

### Deployment Architecture

#### Development Environment
- **Local Development**: Flask dev server + SQLite
- **Docker Compose**: PostgreSQL + Redis + Flask + Celery
- **Hot Reloading**: Automatic code reload on changes
- **Debug Tools**: Flask debug toolbar, logging

#### Production Environment
- **Web Server**: Gunicorn with 4-8 workers
- **Reverse Proxy**: Nginx with SSL termination
- **Database**: PostgreSQL with read replicas
- **Cache**: Redis cluster with persistence
- **Load Balancer**: HAProxy or cloud load balancer
- **CDN**: Cloudflare or AWS CloudFront for static assets

#### Container Orchestration
- **Docker**: Application containerization
- **Docker Compose**: Local development and testing
- **Kubernetes**: Production orchestration (future)
- **Service Mesh**: Istio for traffic management (future)

### Scalability Strategy

#### Horizontal Scaling
- **Stateless Application Servers**: Multiple Flask instances
- **Database Connection Pooling**: PgBouncer for PostgreSQL
- **Session Storage**: Redis for distributed sessions
- **Load Balancing**: Round-robin or least connections

#### Database Scaling
- **Read Replicas**: For reporting and analytics queries
- **Connection Pooling**: SQLAlchemy engine configuration
- **Query Optimization**: Indexes on frequently queried columns
- **Partitioning**: Time-based partitioning for large tables

#### Caching Strategy
- **Redis Cache**: Frequently accessed data
- **Database Query Caching**: SQLAlchemy cache extension
- **CDN Caching**: Static assets and API responses
- **Browser Caching**: Cache-control headers

### Monitoring & Observability

#### Metrics Collection
- **Application Metrics**: Response times, error rates, request volume
- **Business Metrics**: User growth, agent usage, revenue
- **Infrastructure Metrics**: CPU, memory, disk, network
- **Custom Metrics**: Agent execution times, costs, success rates

#### Logging Strategy
- **Structured Logging**: JSON format with correlation IDs
- **Centralized Logging**: ELK stack or cloud logging service
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Audit Logging**: Sensitive operations and data access

#### Alerting & Notification
- **Error Rate Alerts**: Threshold-based error notifications
- **Performance Alerts**: Response time degradation
- **Business Alerts**: Usage spikes or drops
- **Infrastructure Alerts**: Resource exhaustion

### Development Workflow

#### Local Development Setup
1. Clone repository and install dependencies
2. Configure environment variables (.env file)
3. Start Docker services (PostgreSQL, Redis)
4. Run database migrations
5. Seed database with demo data
6. Start Flask development server
7. Start Celery worker and beat scheduler

#### Testing Strategy
- **Unit Tests**: Isolated component testing
- **Integration Tests**: API endpoint testing
- **End-to-End Tests**: Full workflow testing
- **Load Tests**: Performance and scalability testing
- **Security Tests**: Vulnerability scanning

#### CI/CD Pipeline
1. **Code Commit**: Trigger automated build
2. **Code Quality**: Linting, formatting, type checking
3. **Testing**: Automated test suite execution
4. **Security Scan**: Dependency and code vulnerability scanning
5. **Build & Package**: Docker image creation
6. **Deployment**: Staging and production deployment
7. **Verification**: Health checks and smoke tests

### Project Structure

```
agenthub/
├── app/                          # Main application package
│   ├── __init__.py              # Application factory
│   ├── config.py                # Configuration classes
│   ├── extensions.py            # Flask extensions initialization
│   │
│   ├── api/                     # API endpoints
│   │   ├── __init__.py
│   │   ├── v1/                  # API version 1
│   │   │   ├── __init__.py
│   │   │   ├── auth.py         # Authentication endpoints
│   │   │   ├── agents.py       # Agent management
│   │   │   ├── marketplace.py  # Marketplace browsing
│   │   │   ├── billing.py      # Billing and subscriptions
│   │   │   ├── users.py        # User management
│   │   │   └── webhooks.py     # Webhook handlers
│   │   └── health.py           # Health check endpoints
│   │
│   ├── models/                  # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── agent.py
│   │   ├── agent_version.py
│   │   ├── agent_run.py
│   │   ├── subscription.py
│   │   ├── plan.py
│   │   └── billing.py
│   │
│   ├── schemas/                 # Marshmallow schemas
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── agent.py
│   │   ├── user.py
│   │   └── billing.py
│   │
│   ├── services/                # Business logic services
│   │   ├── __init__.py
│   │   ├── agent_service.py
│   │   ├── billing_service.py
│   │   ├── user_service.py
│   │   └── marketplace_service.py
│   │
│   ├── integrations/            # External service integrations
│   │   ├── __init__.py
│   │   ├── agno.py             # Agno framework client
│   │   ├── stripe.py           # Stripe payment processing
│   │   ├── email.py            # Email service
│   │   └── storage.py          # File storage service
│   │
│   ├── tasks/                   # Celery tasks
│   │   ├── __init__.py
│   │   ├── celery_app.py       # Celery application setup
│   │   ├── agent_tasks.py      # Agent execution tasks
│   │   ├── billing_tasks.py    # Billing and invoice tasks
│   │   └── maintenance_tasks.py # System maintenance tasks
│   │
│   ├── utils/                   # Utility functions
│   │   ├── __init__.py
│   │   ├── validators.py       # Custom validators
│   │   ├── pagination.py       # Pagination helpers
│   │   ├── exceptions.py       # Custom exceptions
│   │   └── logging.py          # Logging configuration
│   │
│   ├── core/                   # Core application components
│   │   ├── __init__.py
│   │   ├── security.py         # Security utilities
│   │   ├── dependencies.py     # Dependency injection
│   │   └── middleware.py       # Custom middleware
│   │
│   └── commands.py             # CLI commands
│
├── migrations/                  # Alembic database migrations
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_agents.py
│   ├── test_billing.py
│   └── test_integrations.py
│
├── docs/                       # Documentation
│   ├── architecture.md
│   ├── api.md
│   ├── deployment.md
│   └── development.md
│
├── scripts/                    # Utility scripts
│   ├── seed_demo.py
│   ├── backup_db.py
│   └── deploy.sh
│
├── .env.example               # Environment variables template
├── .gitignore
├── requirements.txt           # Python dependencies
├── requirements-dev.txt       # Development dependencies
├── pyproject.toml            # Project configuration
├── Dockerfile                # Docker container definition
├── docker-compose.yml        # Docker Compose setup
├── nginx.conf               # Nginx configuration
├── run.py                   # Application entry point
├── celery_worker.py         # Celery worker entry point
└── README.md                # Project documentation
```

### Key Design Decisions

#### 1. Monolithic Architecture with Clean Modules
- **Decision**: Start with monolithic architecture for MVP
- **Rationale**: Faster development, simpler deployment, easier debugging
- **Future Evolution**: Can extract microservices as needed

#### 2. Flask Framework Selection
- **Decision**: Use Flask over Django or FastAPI
- **Rationale**: Lightweight, flexible, large ecosystem of extensions
- **Trade-offs**: More boilerplate but greater control

#### 3. SQLAlchemy ORM
- **Decision**: Use SQLAlchemy for database abstraction
- **Rationale**: Mature, flexible, supports multiple databases
- **Benefits**: Migration support, connection pooling, query building

#### 4. JWT Authentication
- **Decision**: Stateless JWT authentication
- **Rationale**: Scalable, works well with distributed systems
- **Implementation**: Flask-JWT-Extended with refresh tokens

#### 5. Celery for Background Tasks
- **Decision**: Use Celery for asynchronous processing
- **Rationale**: Mature, feature-rich, good monitoring tools
- **Alternative Considered**: RQ (simpler) and Dramatiq (newer)

#### 6. Agno Framework Integration
- **Decision**: Abstract agent framework behind service layer
- **Rationale**: Can support multiple agent frameworks in future
- **Benefits**: Vendor independence, easier testing, flexibility

#### 7. Stripe for Payments
- **Decision**: Use Stripe for subscription management
- **Rationale**: Comprehensive API, excellent documentation, reliability
- **Benefits**: Handles compliance, global payments, subscriptions

### Performance Considerations

#### Database Optimization
- **Indexes**: On frequently queried columns (user_id, agent_id, status)
- **Query Optimization**: Eager loading for relationships, query batching
- **Connection Pooling**: Configured pool size and recycle time
- **Read Replicas**: For reporting and analytics queries

#### API Performance
- **Pagination**: Limit results with cursor-based pagination
- **Caching**: Redis cache for frequently accessed data
- **Compression**: Gzip compression for large responses
- **CDN**: Static assets served via CDN

#### Agent Execution
- **Async Processing**: Agent runs via Celery tasks
- **Timeout Management**: Configurable execution timeouts
- **Resource Limits**: Memory and CPU constraints for agent runs
- **Queue Prioritization**: Priority queues for paid users

### Security Considerations

#### Data Protection
- **Encryption**: Sensitive data encrypted at rest
- **SSL/TLS**: HTTPS enforcement for all communications
- **Password Hashing**: bcrypt with high work factor
- **Data Retention**: Automatic cleanup of old data

#### API Security
- **Input Validation**: Strict schema validation for all inputs
- **SQL Injection Prevention**: ORM usage prevents SQL injection
- **XSS Protection**: Output escaping and content security policy
- **CSRF Protection**: For cookie-based authentication (if used)

#### Compliance
- **GDPR**: User data protection and deletion rights
- **PCI DSS**: Secure payment processing via Stripe
- **SOC 2**: Security controls and auditing (future)
- **Data Privacy**: User consent and data usage transparency

### Monitoring & Maintenance

#### Health Checks
- **Application Health**: `/health` endpoint with dependencies
- **Database Health**: Connection and query performance
- **External Services**: Stripe, Agno, email service status
- **Disk Space**: Storage usage monitoring

#### Backup Strategy
- **Database Backups**: Daily automated backups
- **Off-site Storage**: Encrypted backups to cloud storage
- **Backup Verification**: Regular restore testing
- **Disaster Recovery**: Documented recovery procedures

#### Maintenance Tasks
- **Database Cleanup**: Remove old agent runs and logs
- **Invoice Generation**: Monthly billing cycle processing
- **Usage Statistics**: Daily aggregation of usage metrics
- **System Updates**: Security patches and dependency updates

### Future Enhancements

#### Phase 2 (Next 3-6 Months)
1. **Real-time Features**
   - WebSocket support for live agent execution updates
   - Real-time notifications for users
   - Collaborative agent editing and sharing

2. **Advanced Agent Features**
   - Agent composition and workflow creation
   - Agent performance analytics dashboard
   - Custom agent training interface

3. **Marketplace Enhancements**
   - Advanced search and discovery algorithms
   - User reviews and rating system
   - Agent certification and verification program

#### Phase 3 (6-12 Months)
1. **Enterprise Features**
   - SSO integration (SAML, OIDC)
   - Advanced audit logging and compliance reporting
   - Team management and role-based access control
   - Custom billing and invoicing

2. **Scalability Improvements**
   - Microservices architecture migration
   - Event-driven architecture with message queues
   - Global CDN deployment for reduced latency
   - Multi-region database replication

3. **AI/ML Enhancements**
   - Agent performance optimization using ML
   - Usage prediction and capacity planning
   - Personalized agent recommendations
   - Automated agent testing and validation

## Conclusion

This architecture provides a solid foundation for AgentHub that balances development speed with scalability and maintainability. The modular design allows for incremental improvements and eventual migration to more distributed architectures as the platform grows. The focus on clean separation of concerns, comprehensive testing, and robust security measures ensures a reliable and scalable platform for AI agent marketplace operations.