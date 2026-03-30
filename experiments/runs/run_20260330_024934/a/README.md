# AgentHub

A multi-agent orchestration platform with marketplace capabilities. Build, deploy, and manage AI agents at scale.

## Features

- **Multi-Agent Orchestration**: Run and coordinate multiple AI agents simultaneously
- **Agent Marketplace**: Discover, purchase, and deploy pre-built agents
- **Task Scheduling**: Schedule agent runs with cron-like expressions
- **Team Collaboration**: Share agents and tasks with team members
- **Billing & Usage Tracking**: Monitor usage and manage billing
- **RESTful API**: Full-featured API for programmatic access
- **Web Interface**: Modern web UI for managing agents and tasks

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+ (optional, for caching and task queue)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd agenthub
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up database**
   ```bash
   # Create database (PostgreSQL must be running)
   createdb agenthub
   
   # Or use Docker
   docker run -d --name agenthub-postgres -p 5432:5432 \
     -e POSTGRES_DB=agenthub -e POSTGRES_PASSWORD=postgres \
     postgres:15-alpine
   ```

5. **Run the application**
   ```bash
   python run.py
   ```

6. **Access the application**
   - Web UI: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## Docker Deployment

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Services

- **app**: FastAPI application (port 8000)
- **postgres**: PostgreSQL database (port 5432)
- **redis**: Redis cache and message broker (port 6379)
- **celery-worker**: Background task processor
- **celery-beat**: Scheduled task scheduler
- **nginx**: Reverse proxy (port 80/443)

## Project Structure

```
agenthub/
├── api/                    # API endpoints
│   ├── auth.py            # Authentication endpoints
│   ├── agents.py          # Agent management
│   ├── billing.py         # Billing and payments
│   ├── scheduler.py       # Task scheduling
│   ├── tasks.py           # Task management
│   ├── teams.py           # Team collaboration
│   └── usage.py           # Usage tracking
├── agents/                # Agent implementations
│   ├── base.py           # Base agent class
│   ├── catalog.py        # Agent catalog
│   ├── runner.py         # Agent execution engine
│   ├── studio.py         # Agent development studio
│   └── memory.py         # Agent memory management
├── auth/                  # Authentication
│   ├── dependencies.py   # FastAPI dependencies
│   ├── jwt.py           # JWT token handling
│   ├── oauth2.py        # OAuth2 flows
│   └── security.py      # Password hashing
├── billing/              # Billing system
│   ├── credits.py       # Credit management
│   ├── invoices.py      # Invoice generation
│   ├── plans.py         # Subscription plans
│   └── stripe.py        # Stripe integration
├── db/                   # Database
│   ├── models.py        # SQLAlchemy models
│   ├── session.py       # Database session management
│   └── migrations/      # Alembic migrations
├── frontend/            # Web interface
│   ├── routes.py       # Page routes
│   ├── templates/      # Jinja2 templates
│   └── static/         # Static assets
├── scheduler/           # Task scheduling
│   ├── runner.py       # Task runner
│   └── setup.py        # Scheduler setup
├── schemas/            # Pydantic schemas
│   ├── auth.py        # Authentication schemas
│   ├── agents.py      # Agent schemas
│   ├── billing.py     # Billing schemas
│   ├── scheduler.py   # Scheduler schemas
│   ├── users.py       # User schemas
│   └── __init__.py
├── workers/            # Background workers
│   └── processor.py   # Celery task processor
├── config.py          # Application configuration
├── main.py           # FastAPI app factory
├── cli.py            # Command-line interface
└── seed.py           # Database seeding
```

## API Documentation

### Authentication

All API endpoints (except public ones) require authentication via JWT tokens.

1. **Register a new user**
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{
       "email": "user@example.com",
       "password": "securepassword",
       "full_name": "John Doe"
     }'
   ```

2. **Login**
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{
       "username": "user@example.com",
       "password": "securepassword"
     }'
   ```

3. **Use token**
   ```bash
   curl -X GET http://localhost:8000/api/v1/users/me \
     -H "Authorization: Bearer <access_token>"
   ```

### Key Endpoints

- `GET /api/v1/agents` - List available agents
- `POST /api/v1/agents` - Create a new agent
- `POST /api/v1/agents/{agent_id}/run` - Run an agent
- `GET /api/v1/tasks` - List user tasks
- `POST /api/v1/scheduler/tasks` - Schedule a task
- `GET /api/v1/billing/credits` - Get credit balance
- `POST /api/v1/billing/checkout` - Create payment checkout

## Configuration

### Environment Variables

See `.env.example` for all available options. Key variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection URL | `postgresql://postgres:postgres@localhost/agenthub` |
| `SECRET_KEY` | JWT secret key | (required) |
| `DEBUG` | Enable debug mode | `false` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:8000,http://localhost:3000` |
| `STRIPE_SECRET_KEY` | Stripe API key | (optional) |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |

### Database Configuration

The application uses SQLAlchemy with PostgreSQL. To run migrations:

```bash
# Initialize migrations
alembic init agenthub/db/migrations

# Create migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

## Development

### Setting Up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements.txt
pip install -e .

# Run tests
pytest

# Run with auto-reload
python run.py --reload
```

### Code Style

- Follow PEP 8
- Use type hints
- Document public functions and classes
- Write tests for new features

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=agenthub

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v
```

## Deployment

### Production Checklist

1. **Security**
   - Set `DEBUG=false`
   - Use strong `SECRET_KEY`
   - Enable HTTPS
   - Configure CORS appropriately
   - Set up rate limiting

2. **Database**
   - Use production PostgreSQL instance
   - Regular backups
   - Connection pooling

3. **Monitoring**
   - Enable Prometheus metrics
   - Set up logging
   - Health checks
   - Error tracking

4. **Scaling**
   - Use multiple workers
   - Configure Redis for caching
   - Set up load balancing

### Deployment Options

#### Docker (Recommended)
```bash
docker build -t agenthub .
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host/db \
  -e SECRET_KEY=your-secret-key \
  agenthub
```

#### Kubernetes
```yaml
# Example deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agenthub
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agenthub
  template:
    metadata:
      labels:
        app: agenthub
    spec:
      containers:
      - name: agenthub
        image: agenthub:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: agenthub-secrets
              key: database-url
```

#### Cloud Platforms
- **AWS**: ECS, EKS, or EC2
- **Google Cloud**: Cloud Run, GKE
- **Azure**: Container Instances, AKS
- **Heroku**: Container Registry

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Update documentation
6. Submit a pull request

### Development Workflow

```bash
# Create new feature
git checkout -b feature/new-feature

# Make changes
# Add tests
# Update documentation

# Run tests
pytest

# Commit changes
git add .
git commit -m "Add new feature"

# Push to remote
git push origin feature/new-feature

# Create pull request
```

## License

[Your License Here]

## Support

- Documentation: [Link to docs]
- Issues: [GitHub Issues]
- Email: support@agenthub.com
- Discord/Slack: [Community Link]

## Acknowledgments

- Built with FastAPI
- Uses SQLAlchemy for ORM
- Integrates with Stripe for payments
- Inspired by modern agent frameworks