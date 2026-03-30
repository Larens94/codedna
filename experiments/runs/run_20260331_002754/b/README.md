# AgentHub - AI Agent Marketplace

AgentHub is a SaaS platform for discovering, running, and managing AI agents through a marketplace model. Users can browse, purchase, and execute AI agents for various tasks, while developers can publish and monetize their AI agents.

## Features

- **User Management**: Registration, authentication, profile management
- **Agent Marketplace**: Browse, search, and discover AI agents
- **Agent Execution**: Run agents with custom inputs, track execution history
- **Subscription System**: Tiered pricing plans with Stripe integration
- **Agent Management**: Create, version, and publish AI agents
- **Task Queue**: Asynchronous agent execution with Celery
- **API**: RESTful API with JWT authentication
- **Admin Dashboard**: User and agent management (CLI-based for now)

## Technology Stack

### Backend
- **Framework**: Flask (Python)
- **Database**: PostgreSQL (production), SQLite (development)
- **ORM**: SQLAlchemy with Alembic migrations
- **Task Queue**: Celery with Redis broker
- **Authentication**: JWT with Flask-JWT-Extended
- **API Documentation**: OpenAPI/Swagger (planned)
- **Payment Processing**: Stripe integration

### Agent Integration
- **Primary Framework**: Agno AI Agent Framework
- **Abstract Layer**: Support for multiple agent frameworks

### Deployment
- **Containerization**: Docker & Docker Compose
- **Production**: Gunicorn + Nginx (recommended)
- **Monitoring**: Prometheus + Grafana (planned)

## Project Structure

```
agenthub/
├── app/                          # Application package
│   ├── __init__.py              # Application factory
│   ├── config.py                # Configuration classes
│   ├── models/                  # SQLAlchemy models
│   ├── api/                     # API endpoints
│   ├── schemas/                 # Request/response schemas
│   ├── services/                # Business logic services
│   ├── integrations/            # External service integrations
│   ├── tasks/                   # Celery tasks
│   ├── utils/                   # Utilities and helpers
│   └── commands.py              # CLI commands
├── migrations/                  # Alembic database migrations
├── docs/                       # Documentation
├── tests/                      # Test suite
├── .env.example                # Environment template
├── requirements.txt            # Python dependencies
├── docker-compose.yml          # Docker development setup
└── README.md                   # This file
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL (or SQLite for development)
- Redis (for Celery)
- Stripe account (for payments)

### 1. Local Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd agenthub

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Initialize database
flask db upgrade

# Seed database with demo data
flask seed-db

# Create admin user (optional)
flask create-admin

# Run development server
python run.py

# In another terminal, run Celery worker
celery -A app.tasks worker --loglevel=info

# In another terminal, run Celery beat for scheduled tasks
celery -A app.tasks beat --loglevel=info
```

### 2. Docker Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd agenthub

# Copy environment file
cp .env.example .env

# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 3. Access the Application

- **API**: http://localhost:5000/api/v1/
- **Health Check**: http://localhost:5000/health
- **Flower (Celery Monitoring)**: http://localhost:5555 (if using Docker)
- **API Documentation**: Swagger UI at /api/docs (planned)

## API Documentation

### Authentication

All API endpoints (except public ones) require JWT authentication.

```bash
# Register a new user
curl -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "username": "testuser", "password": "password123"}'

# Login
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Use the access token in subsequent requests
curl -X GET http://localhost:5000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

### Agent Marketplace

```bash
# Browse published agents
curl -X GET http://localhost:5000/api/v1/marketplace/agents

# Get agent details
curl -X GET http://localhost:5000/api/v1/agents/{agent_id}

# Execute an agent
curl -X POST http://localhost:5000/api/v1/agents/{agent_id}/run \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"input": {"text": "Content to summarize"}}'
```

## Database Schema

### Core Tables

1. **users**: User accounts and profiles
2. **agents**: AI agent definitions
3. **agent_versions**: Versioned agent configurations
4. **agent_runs**: Agent execution history
5. **subscriptions**: User subscription plans
6. **plans**: Subscription plan definitions
7. **billing_accounts**: User billing information
8. **invoices**: Billing invoices

See `docs/architecture.md` for detailed schema documentation.

## CLI Commands

```bash
# Seed database with demo data
flask seed-db

# Create admin user
flask create-admin --email admin@example.com --username admin

# Run Celery worker
flask run-worker

# Database migrations
flask db init          # Initialize migrations
flask db migrate       # Create migration
flask db upgrade       # Apply migrations
flask db downgrade     # Rollback migration
```

## Testing

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_auth.py
```

## Deployment

### Production Considerations

1. **Database**: Use PostgreSQL with connection pooling
2. **Web Server**: Use Gunicorn with Nginx reverse proxy
3. **Static Files**: Use CDN or Nginx for static file serving
4. **SSL**: Enable HTTPS with Let's Encrypt
5. **Monitoring**: Set up logging, metrics, and alerts
6. **Backups**: Regular database backups

### Environment Variables (Production)

Required production environment variables:

```bash
FLASK_ENV=production
SECRET_KEY=<strong-secret-key>
JWT_SECRET_KEY=<strong-jwt-secret-key>
DATABASE_URL=postgresql://user:password@host/dbname
CELERY_BROKER_URL=redis://redis-host:6379/0
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
AGNO_API_KEY=<your-agno-api-key>
```

## Development

### Code Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Write docstrings for all public functions/classes
- Run black for code formatting: `black .`
- Run flake8 for linting: `flake8`

### Branch Strategy

- `main`: Production-ready code
- `develop`: Development branch
- `feature/*`: Feature branches
- `hotfix/*`: Hotfix branches

### Commit Convention

- feat: New feature
- fix: Bug fix
- docs: Documentation changes
- style: Code style changes (formatting, etc.)
- refactor: Code refactoring
- test: Adding or updating tests
- chore: Maintenance tasks

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

[Specify License - e.g., MIT]

## Support

- Documentation: [Link to docs]
- Issues: [GitHub Issues]
- Email: support@agenthub.com

## Demo Data

After running `flask seed-db`, the following demo data is created:

- **Demo User**: demo@agenthub.com / demopassword123
- **6 Marketplace Agents**:
  1. Content Summarizer
  2. Code Review Assistant
  3. Social Media Content Creator
  4. Financial Analyst
  5. Customer Support Bot
  6. Creative Writing Assistant
- **Subscription Plans**: Free, Basic, Pro, Team
- **Sample Agent Runs**: 3 runs for each of the first 3 agents

## Roadmap

### Phase 1 (Current)
- [x] User authentication and management
- [x] Agent marketplace basic functionality
- [x] Agent execution framework
- [x] Basic subscription system
- [x] Database schema and models
- [x] API endpoints for core functionality

### Phase 2 (Next)
- [ ] Real-time agent execution updates
- [ ] Advanced agent search and discovery
- [ ] User reviews and ratings
- [ ] Agent analytics dashboard
- [ ] WebSocket support
- [ ] Advanced billing features

### Phase 3 (Future)
- [ ] Multi-tenant support
- [ ] Agent workflow composition
- [ ] Advanced analytics and reporting
- [ ] Mobile application
- [ ] Enterprise features (SSO, audit logs)
- [ ] Integration with multiple AI platforms