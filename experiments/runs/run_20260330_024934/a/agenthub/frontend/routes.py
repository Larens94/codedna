"""routes.py — Jinja2 page routes for frontend interface.

exports: router_frontend
used_by: main.py → router registration
rules:   must extend base.html; must use Jinja2 autoescape; must include CSRF tokens
agent:   FrontendDesigner | 2024-01-15 | Frontend page routes with authentication
         message: "implement server-side rendering for agent marketplace data"
"""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from agenthub.db.session import get_db
from agenthub.db.models import User, Agent, Task, CreditAccount
from agenthub.auth.dependencies import get_current_user
from agenthub.config import settings

router_frontend = APIRouter()

# Configure templates
templates = Jinja2Templates(directory="agenthub/frontend/templates")


def get_context(request: Request, user: Optional[User] = None) -> Dict[str, Any]:
    """Get base template context with common variables."""
    context = {
        "request": request,
        "user": user,
        "settings": settings,
        "is_authenticated": user is not None,
    }
    
    if user:
        context.update({
            "user_id": str(user.public_id),
            "user_email": user.email,
            "user_name": user.full_name or user.email.split('@')[0],
            "is_superuser": user.is_superuser,
        })
    
    return context


@router_frontend.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Landing page - public access."""
    context = get_context(request)
    context["page_title"] = "AgentHub - Multi-Agent Orchestration Platform"
    context["page_description"] = "Build, deploy, and manage AI agents at scale"
    
    return templates.TemplateResponse("index.html", context)


@router_frontend.get("/marketplace", response_class=HTMLResponse)
async def marketplace(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Agent marketplace - requires authentication."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login?next=/marketplace"}
        )
    
    # Get available agents
    agents = db.query(Agent).filter(Agent.is_public == True).all()
    
    context = get_context(request, current_user)
    context.update({
        "page_title": "Agent Marketplace",
        "agents": agents,
        "categories": ["All", "Data Analysis", "Content Creation", "Automation", "Research"],
        "sort_options": ["Popular", "Newest", "Price: Low to High", "Price: High to Low"],
    })
    
    return templates.TemplateResponse("marketplace.html", context)


@router_frontend.get("/studio", response_class=HTMLResponse)
async def studio(
    request: Request,
    agent_id: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Agent studio for testing and configuration - requires authentication."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login?next=/studio"}
        )
    
    agent = None
    if agent_id:
        agent = db.query(Agent).filter(Agent.public_id == agent_id).first()
    
    # Get user's agents
    user_agents = db.query(Agent).filter(Agent.owner_id == current_user.id).all()
    
    context = get_context(request, current_user)
    context.update({
        "page_title": "Agent Studio",
        "selected_agent": agent,
        "user_agents": user_agents,
        "agent_templates": [
            {"id": "data_analyzer", "name": "Data Analyzer", "description": "Analyze and visualize data"},
            {"id": "content_writer", "name": "Content Writer", "description": "Generate written content"},
            {"id": "automation_bot", "name": "Automation Bot", "description": "Automate repetitive tasks"},
            {"id": "research_assistant", "name": "Research Assistant", "description": "Research and summarize information"},
        ],
    })
    
    return templates.TemplateResponse("studio.html", context)


@router_frontend.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """User dashboard with analytics - requires authentication."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login?next=/dashboard"}
        )
    
    # Get user's credit account
    credit_account = db.query(CreditAccount).filter(
        CreditAccount.user_id == current_user.id
    ).first()
    
    # Get recent tasks
    recent_tasks = db.query(Task).filter(
        Task.user_id == current_user.id
    ).order_by(Task.created_at.desc()).limit(10).all()
    
    # Get usage statistics (mock data for now)
    usage_data = {
        "daily": [10, 20, 15, 25, 30, 35, 40],
        "weekly": [150, 180, 200, 220, 240],
        "monthly": [800, 950, 1100, 1250],
    }
    
    context = get_context(request, current_user)
    context.update({
        "page_title": "Dashboard",
        "credit_balance": credit_account.balance if credit_account else 0.0,
        "recent_tasks": recent_tasks,
        "usage_data": usage_data,
        "active_agents": len([a for a in recent_tasks if a.status == "running"]),
        "total_runs": len(recent_tasks),
        "success_rate": 85,  # Mock success rate
    })
    
    return templates.TemplateResponse("dashboard.html", context)


@router_frontend.get("/scheduler", response_class=HTMLResponse)
async def scheduler(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Task scheduler interface - requires authentication."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login?next=/scheduler"}
        )
    
    # Get scheduled tasks
    scheduled_tasks = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.scheduled_at.isnot(None)
    ).order_by(Task.scheduled_at).all()
    
    # Get user's agents for scheduling
    user_agents = db.query(Agent).filter(Agent.owner_id == current_user.id).all()
    
    context = get_context(request, current_user)
    context.update({
        "page_title": "Task Scheduler",
        "scheduled_tasks": scheduled_tasks,
        "user_agents": user_agents,
        "schedule_options": [
            {"value": "once", "label": "Run Once"},
            {"value": "hourly", "label": "Hourly"},
            {"value": "daily", "label": "Daily"},
            {"value": "weekly", "label": "Weekly"},
            {"value": "monthly", "label": "Monthly"},
            {"value": "cron", "label": "Custom Cron"},
        ],
        "timezones": ["UTC", "America/New_York", "Europe/London", "Asia/Tokyo"],
    })
    
    return templates.TemplateResponse("scheduler.html", context)


@router_frontend.get("/workspace", response_class=HTMLResponse)
async def workspace(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Team workspace and settings - requires authentication."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login?next=/workspace"}
        )
    
    # Get user's agents
    user_agents = db.query(Agent).filter(Agent.owner_id == current_user.id).all()
    
    # Get team members (mock for now)
    team_members = [
        {"name": "You", "email": current_user.email, "role": "Owner", "status": "active"},
        {"name": "Alex Johnson", "email": "alex@example.com", "role": "Developer", "status": "active"},
        {"name": "Sam Wilson", "email": "sam@example.com", "role": "Analyst", "status": "pending"},
    ]
    
    context = get_context(request, current_user)
    context.update({
        "page_title": "Workspace",
        "user_agents": user_agents,
        "team_members": team_members,
        "workspace_settings": {
            "name": f"{current_user.email.split('@')[0]}'s Workspace",
            "max_agents": 10,
            "max_concurrent": 3,
            "data_retention": 30,
        },
    })
    
    return templates.TemplateResponse("workspace.html", context)


@router_frontend.get("/billing", response_class=HTMLResponse)
async def billing(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Billing and usage page - requires authentication."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login?next=/billing"}
        )
    
    # Get credit account
    credit_account = db.query(CreditAccount).filter(
        CreditAccount.user_id == current_user.id
    ).first()
    
    # Get billing history (mock for now)
    billing_history = [
        {"date": "2024-01-15", "description": "Agent Execution Credits", "amount": 25.00, "status": "paid"},
        {"date": "2024-01-01", "description": "Monthly Subscription", "amount": 49.99, "status": "paid"},
        {"date": "2023-12-15", "description": "Agent Execution Credits", "amount": 18.50, "status": "paid"},
        {"date": "2023-12-01", "description": "Monthly Subscription", "amount": 49.99, "status": "paid"},
    ]
    
    # Get usage summary
    usage_summary = {
        "current_month": {
            "agent_runs": 142,
            "compute_hours": 8.5,
            "data_processed": "2.4 GB",
            "estimated_cost": 42.75,
        },
        "previous_month": {
            "agent_runs": 118,
            "compute_hours": 6.8,
            "data_processed": "1.9 GB",
            "estimated_cost": 35.60,
        },
    }
    
    context = get_context(request, current_user)
    context.update({
        "page_title": "Billing & Usage",
        "credit_balance": credit_account.balance if credit_account else 0.0,
        "billing_history": billing_history,
        "usage_summary": usage_summary,
        "payment_methods": [
            {"type": "card", "last4": "4242", "expiry": "12/25", "default": True},
        ],
        "plans": [
            {"name": "Starter", "price": 0, "features": ["3 agents", "100 runs/month", "Basic support"]},
            {"name": "Pro", "price": 49.99, "features": ["10 agents", "1000 runs/month", "Priority support", "Team collaboration"]},
            {"name": "Enterprise", "price": 199.99, "features": ["Unlimited agents", "Custom limits", "24/7 support", "Custom integrations"]},
        ],
    })
    
    return templates.TemplateResponse("billing.html", context)


# Authentication pages
@router_frontend.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    next_url: Optional[str] = None,
    error: Optional[str] = None,
):
    """Login page."""
    context = get_context(request)
    context.update({
        "page_title": "Login - AgentHub",
        "next_url": next_url,
        "error": error,
    })
    
    return templates.TemplateResponse("auth/login.html", context)


@router_frontend.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    error: Optional[str] = None,
):
    """Registration page."""
    context = get_context(request)
    context.update({
        "page_title": "Register - AgentHub",
        "error": error,
    })
    
    return templates.TemplateResponse("auth/register.html", context)


@router_frontend.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(
    request: Request,
    token: Optional[str] = None,
    error: Optional[str] = None,
):
    """Password reset page."""
    context = get_context(request)
    context.update({
        "page_title": "Reset Password - AgentHub",
        "token": token,
        "error": error,
    })
    
    return templates.TemplateResponse("auth/reset.html", context)


@router_frontend.get("/api-keys", response_class=HTMLResponse)
async def api_keys_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """API key management page - requires authentication."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login?next=/api-keys"}
        )
    
    # Get user's API keys (mock for now)
    api_keys = [
        {"name": "Production Key", "key": "sk_prod_****abcd", "created": "2024-01-10", "last_used": "2024-01-15"},
        {"name": "Development Key", "key": "sk_dev_****efgh", "created": "2024-01-05", "last_used": "2024-01-14"},
        {"name": "CI/CD Key", "key": "sk_cicd_****ijkl", "created": "2024-01-01", "last_used": "2024-01-13"},
    ]
    
    context = get_context(request, current_user)
    context.update({
        "page_title": "API Keys - AgentHub",
        "api_keys": api_keys,
    })
    
    return templates.TemplateResponse("auth/api_keys.html", context)


# Health check endpoint for frontend
@router_frontend.get("/health")
async def frontend_health():
    """Frontend health check."""
    return {"status": "healthy", "service": "agenthub-frontend"}