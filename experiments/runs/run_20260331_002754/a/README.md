# AgentHub SaaS Platform

A multi-tenant SaaS platform for creating, managing, and deploying AI agents powered by the Agno framework.

## Features

- **Multi-tenancy**: Isolated organizations with role-based access control
- **AI Agent Management**: Create, configure, and deploy AI agents with various LLM providers
- **Conversation Sessions**: Stateful chat sessions with token counting and memory
- **Usage Tracking**: Real-time usage monitoring and credit-based billing
- **Billing Integration**: Stripe integration for subscription management
- **Async Processing**: Background task processing with Celery
- **File Storage**: S3-compatible storage for agent artifacts
- **RESTful API**: Fully documented OpenAPI 3.0 specification
- **Production Ready**: Dockerized, scalable, and monitored

## Architecture

### System Overview
```
┌─────────────────────────────────────────────────────────────────────┐
│                          Client Layer (SPA)                         │
├─────────────────────────────────────────────────────────────────────┤
│                         API Gateway (FastAPI)                       │
├─────────────────────────────────────────────────────────────────────┤
│      Service Layer          │          Agent Runtime Layer          │
│  • User Service             │  • Agent Session Manager             │
│  • Org Service              │  • Token Counter                     │
│  • Agent Service            │  • Memory Manager                    │
│  • Task Service             │  • Agno Integration                  │
│  • Billing Service          │  • Streaming Handler                 │
│  • Analytics Service        │                                      │
├─────────────────────────────────────────────────────────────────────┤
│                      Data Access Layer (SQLAlchemy)                 │
├─────────────────────────────────────────────────────────────────────┤
│                    PostgreSQL │ Redis │ Object Storage              │
└─────────────────────────────────────────────────────────────────────┘
```

### Technology Stack
- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15+ with async SQLAlchemy
- **Cache & Sessions**: Redis 7+
- **Object Storage**: MinIO / AWS S3
- **Message Queue**: Redis + Celery
- **Authentication**: JWT + OAuth2
- **Monitoring**: Prometheus + Grafana
- **Containerization**: Docker + Docker Compose

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local development)
- OpenAI API key (optional, for AI features)

### Quick Start with Docker Compose

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/agenthub.git
   cd agenthub
   ```

2. Create environment file:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

3. Start all services:
   ```bash
   docker-compose up -d
   ```

4. Access the services:
   - API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)
   - pgAdmin: http://localhost:5050 (admin@agenthub.dev/admin)
   - Redis Commander: http://localhost:8081

### Local Development

1. Install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Set up environment variables:
   ```bash
   export DATABASE_URL="postgresql+asyncpg://agenthub:agenthub_password@localhost:5432/agenthub"
   export REDIS_URL="redis://localhost:6379/0"
   export JWT_SECRET_KEY="your-secret-key-change-this"
   ```

3. Run database migrations:
   ```bash
   alembic upgrade head
   ```

4. Start the development server:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## Project Structure

```
agenthub/
├── app/                          # Main application package
│   ├── api/                      # API routes and endpoints
│   │   └── v1/                   # API version 1
│   ├── core/                     # Core application code
│   │   ├── config.py            # Configuration management
│   │   ├── database.py          # Database connection
│   │   └── redis.py             # Redis client
│   ├── models/                  # SQLAlchemy models
│   │   ├── user.py              # User model
│   │   ├── organization.py      # Organization model
│   │   ├── agent.py             # Agent model
│   │   ├── task.py              # Task model
│   │   ├── usage.py             # Usage tracking model
│   │   └── billing.py           # Billing models
│   ├── services/                # Business logic services
│   │   ├── auth.py              # Authentication service
│   │   ├── users.py             # User service
│   │   ├── organizations.py     # Organization service
│   │   ├── agents.py            # Agent service
│   │   ├── sessions.py          # Session service
│   │   ├── tasks.py             # Task service
│   │   ├── billing.py           # Billing service
│   │   └── agent_runtime.py     # Agent execution service
│   ├── middleware/              # FastAPI middleware
│   ├── dependencies/            # FastAPI dependencies
│   └── main.py                  # Application factory
├── alembic/                     # Database migrations
├── docs/                        # Documentation
├── scripts/                     # Utility scripts
├── tests/                       # Test suite
├── docker-compose.yml          # Docker Compose configuration
├── Dockerfile                  # Docker build file
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## API Documentation

Once the application is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Authentication
Most endpoints require JWT authentication. To authenticate:

1. Register a user:
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com", "password": "password123"}'
   ```

2. Login to get tokens:
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com", "password": "password123"}'
   ```

3. Use the access token in requests:
   ```bash
   curl -X GET http://localhost:8000/api/v1/users/me \
     -H "Authorization: Bearer <access_token>"
   ```

## Database Schema

Key tables:
- `users`: User accounts
- `organizations`: Tenant organizations
- `organization_members`: Organization membership with roles
- `agents`: AI agent configurations
- `agent_sessions`: Conversation sessions
- `session_messages`: Chat messages
- `tasks`: Background tasks
- `usage_records`: Usage tracking for billing
- `billing_invoices`: Billing invoices
- `billing_line_items`: Invoice line items

See [docs/architecture.md](docs/architecture.md) for detailed schema.

## Deployment

### Production Deployment with Docker

1. Build the Docker image:
   ```bash
   docker build -t agenthub/api:latest .
   ```

2. Run with production configuration:
   ```bash
   docker run -d \
     --name agenthub-api \
     -p 8000:8000 \
     -e DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db" \
     -e REDIS_URL="redis://host:6379/0" \
     -e JWT_SECRET_KEY="your-secret-key" \
     agenthub/api:latest
   ```

### Kubernetes Deployment

See `k8s/` directory for Kubernetes manifests:
- Deployment
- Service
- Ingress
- ConfigMap
- Secret

### Cloud Deployment (AWS)

1. **RDS PostgreSQL**: Multi-AZ for high availability
2. **ElastiCache Redis**: For caching and sessions
3. **S3 Bucket**: For file storage
4. **ECS/EKS**: Container orchestration
5. **ALB**: Load balancing with SSL termination
6. **CloudFront**: CDN for static assets

## Development

### Code Style
- **Formatter**: Black
- **Linter**: Flake8
- **Import Sorter**: isort
- **Type Checking**: mypy

Run code quality checks:
```bash
black app/
isort app/
flake8 app/
mypy app/
```

### Testing
```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=app --cov-report=html

# Run specific test module
pytest tests/test_users.py -v
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Monitoring & Observability

- **Health Endpoint**: `GET /health`
- **Metrics Endpoint**: `GET /metrics` (Prometheus format)
- **Structured Logging**: JSON format for log aggregation
- **Error Tracking**: Sentry integration
- **Performance Monitoring**: OpenTelemetry traces

## Security

- **Authentication**: JWT with short-lived access tokens and refresh tokens
- **Authorization**: Role-based access control (RBAC)
- **Data Encryption**: TLS/SSL for transit, encryption at rest
- **Input Validation**: Pydantic models for all API requests
- **Rate Limiting**: Per-organization rate limiting
- **Security Headers**: Helmet.js equivalent for FastAPI

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- Documentation: [docs.agenthub.dev](https://docs.agenthub.dev)
- Issues: [GitHub Issues](https://github.com/your-org/agenthub/issues)
- Discord: [Join our community](https://discord.gg/agenthub)

## Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL toolkit
- [Agno](https://github.com/agno-agi/agno) - AI agent framework
- [Stripe](https://stripe.com/) - Payment processing