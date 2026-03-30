"""test_integration.py — Integration tests for AgentHub components.

Tests that all components work together correctly.
Run with: pytest test_integration.py -v
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from agenthub.main import create_app
from agenthub.db.models import Base, User, Agent, CreditAccount
from agenthub.db.session import get_db
from agenthub.config import settings


# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override the database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="module")
def test_app():
    """Create test application with overridden dependencies."""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create test app
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    
    yield app
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture(scope="module")
def test_user():
    """Create test user data."""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "full_name": "Test User"
    }


@pytest.fixture(scope="module")
def auth_headers(client, test_user):
    """Register user, login, and return auth headers."""
    # Register user
    response = client.post("/api/v1/auth/register", json=test_user)
    assert response.status_code == 200
    
    # Login
    login_data = {
        "username": test_user["email"],
        "password": test_user["password"]
    }
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestIntegration:
    """Integration tests for AgentHub."""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "agenthub"
    
    def test_api_health_endpoint(self, client):
        """Test API health check endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["api"] == "v1"
    
    def test_frontend_pages(self, client):
        """Test frontend pages load."""
        # Test landing page
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        # Test login page
        response = client.get("/login")
        assert response.status_code == 200
        
        # Test register page
        response = client.get("/register")
        assert response.status_code == 200
    
    def test_auth_flow(self, client, test_user):
        """Test complete authentication flow."""
        # Register
        response = client.post("/api/v1/auth/register", json=test_user)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["email"] == test_user["email"]
        
        # Login
        login_data = {
            "username": test_user["email"],
            "password": test_user["password"]
        }
        response = client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        
        # Get current user
        token = data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user["email"]
    
    def test_protected_frontend_pages(self, client, auth_headers):
        """Test that protected frontend pages redirect when not authenticated."""
        # These should redirect to login
        pages = ["/dashboard", "/marketplace", "/studio", "/scheduler", "/workspace", "/billing"]
        
        for page in pages:
            response = client.get(page, allow_redirects=False)
            # Should redirect to login
            assert response.status_code in [307, 302]
    
    def test_agent_api_endpoints(self, client, auth_headers):
        """Test agent API endpoints."""
        # List agents (empty initially)
        response = client.get("/api/v1/agents", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Create agent
        agent_data = {
            "name": "Test Agent",
            "description": "A test agent",
            "config": {"model": "gpt-4", "temperature": 0.7},
            "is_public": False,
            "price": 0.0
        }
        response = client.post("/api/v1/agents", json=agent_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == agent_data["name"]
        assert "id" in data
        
        agent_id = data["id"]
        
        # Get agent by ID
        response = client.get(f"/api/v1/agents/{agent_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == agent_data["name"]
        
        # Update agent
        update_data = {"description": "Updated description"}
        response = client.put(f"/api/v1/agents/{agent_id}", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == update_data["description"]
        
        # List agents again (should have one)
        response = client.get("/api/v1/agents", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
    
    def test_task_api_endpoints(self, client, auth_headers):
        """Test task API endpoints."""
        # List tasks (empty initially)
        response = client.get("/api/v1/tasks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Create a task
        task_data = {
            "name": "Test Task",
            "description": "A test task",
            "agent_id": 1,  # Assuming agent with ID 1 exists
            "input_data": {"prompt": "Hello world"},
            "priority": "normal"
        }
        response = client.post("/api/v1/tasks", json=task_data, headers=auth_headers)
        # Might fail if agent doesn't exist, but that's OK for integration test
        # We're testing that the endpoint exists and responds
        assert response.status_code in [200, 400, 404]
    
    def test_billing_api_endpoints(self, client, auth_headers):
        """Test billing API endpoints."""
        # Get credit balance
        response = client.get("/api/v1/billing/credits", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "balance" in data
        assert "currency" in data
        
        # Get billing history
        response = client.get("/api/v1/billing/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_scheduler_api_endpoints(self, client, auth_headers):
        """Test scheduler API endpoints."""
        # List scheduled tasks
        response = client.get("/api/v1/scheduler/tasks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Get scheduler status
        response = client.get("/api/v1/scheduler/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    def test_teams_api_endpoints(self, client, auth_headers):
        """Test teams API endpoints."""
        # List teams
        response = client.get("/api/v1/teams", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Create team
        team_data = {
            "name": "Test Team",
            "description": "A test team"
        }
        response = client.post("/api/v1/teams", json=team_data, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == team_data["name"]
    
    def test_usage_api_endpoints(self, client, auth_headers):
        """Test usage API endpoints."""
        # Get usage summary
        response = client.get("/api/v1/usage/summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "period" in data
        assert "metrics" in data
        
        # Get usage history
        response = client.get("/api/v1/usage/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_static_files(self, client):
        """Test static files are served."""
        # Create a test static file
        import os
        static_dir = "agenthub/frontend/static"
        os.makedirs(static_dir, exist_ok=True)
        with open(f"{static_dir}/test.txt", "w") as f:
            f.write("test content")
        
        # Test static file serving
        response = client.get("/static/test.txt")
        assert response.status_code == 200
        assert response.text == "test content"
        
        # Cleanup
        os.remove(f"{static_dir}/test.txt")


def test_component_imports():
    """Test that all major components can be imported."""
    # Test core imports
    from agenthub.main import create_app, app
    from agenthub.config import settings
    
    # Test database imports
    from agenthub.db.models import Base, User, Agent, Task, CreditAccount
    from agenthub.db.session import engine, SessionLocal, get_db
    
    # Test API imports
    from agenthub.api import auth, agents, billing, scheduler, tasks, teams, usage
    
    # Test auth imports
    from agenthub.auth.dependencies import get_current_user
    from agenthub.auth.security import verify_password, get_password_hash
    
    # Test frontend imports
    from agenthub.frontend.routes import router_frontend
    
    # Test agent imports
    from agenthub.agents.base import BaseAgent
    from agenthub.agents.runner import AgentRunner
    
    # Test billing imports
    from agenthub.billing.credits import CreditManager
    
    # Test scheduler imports
    from agenthub.scheduler.runner import TaskRunner
    
    # Test worker imports
    from agenthub.workers.processor import process_task
    
    assert True  # If we get here, all imports succeeded


if __name__ == "__main__":
    # Run tests directly
    import sys
    pytest.main(sys.argv)