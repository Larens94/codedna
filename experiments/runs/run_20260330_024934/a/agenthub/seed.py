"""seed.py — Database seeding with demo users and marketplace agents.

exports: seed_database(), create_demo_users(), create_marketplace_agents()
used_by: cli.py, development setup scripts
rules:   must not overwrite existing data; must use proper password hashing
agent:   ProductArchitect | 2024-01-15 | created seed script with 6 marketplace agents
         message: "verify password hashing uses bcrypt with proper salt rounds"
"""

import sys
from typing import List, Dict, Any
from datetime import datetime, timezone
from passlib.context import CryptContext

from agenthub.db.session import SessionLocal, engine
from agenthub.db.models import Base, User, Agent, CreditAccount

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash password using bcrypt.
    
    Rules:   must use secure salt rounds; must verify against hash
    message: claude-sonnet-4-6 | 2024-01-15 | consider making salt rounds configurable
    """
    # bcrypt has 72-byte limit, truncate if longer (should not happen with demo passwords)
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    return pwd_context.hash(password)


def create_demo_users(db) -> Dict[str, User]:
    """Create demo users for testing.
    
    Rules:   must create admin and regular users; must set up credit accounts
    message: claude-sonnet-4-6 | 2024-01-15 | add more realistic user profiles
    """
    demo_users = [
        {
            "email": "admin@agenthub.com",
            "password": "AdminPass123!",
            "full_name": "System Administrator",
            "is_superuser": True,
            "initial_credits": 1000.0,
        },
        {
            "email": "alice@example.com",
            "password": "AlicePass123!",
            "full_name": "Alice Johnson",
            "is_superuser": False,
            "initial_credits": 500.0,
        },
        {
            "email": "bob@example.com",
            "password": "BobPass123!",
            "full_name": "Bob Smith",
            "is_superuser": False,
            "initial_credits": 250.0,
        },
        {
            "email": "charlie@startup.com",
            "password": "CharliePass123!",
            "full_name": "Charlie Brown",
            "is_superuser": False,
            "initial_credits": 100.0,
        },
    ]
    
    created_users = {}
    
    for user_data in demo_users:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data["email"]).first()
        if existing_user:
            print(f"User {user_data['email']} already exists, skipping...")
            created_users[user_data["email"]] = existing_user
            continue
        
        # Create user
        user = User(
            email=user_data["email"],
            password_hash=hash_password(user_data["password"]),
            full_name=user_data["full_name"],
            is_superuser=user_data["is_superuser"],
            is_active=True,
        )
        db.add(user)
        db.flush()  # Get user ID
        
        # Create credit account
        credit_account = CreditAccount(
            user_id=user.id,
            balance=user_data["initial_credits"],
            currency="USD",
        )
        db.add(credit_account)
        
        created_users[user_data["email"]] = user
    
    return created_users


def create_marketplace_agents(db, owner: User) -> List[Agent]:
    """Create 6 marketplace agents for the demo.
    
    Rules:   must have diverse categories and pricing; must be public
    message: claude-sonnet-4-6 | 2024-01-15 | add more sophisticated agent configurations
    """
    marketplace_agents = [
        {
            "name": "Content Summarizer",
            "slug": "content-summarizer",
            "description": "Summarizes long articles, reports, and documents into concise summaries.",
            "system_prompt": "You are a professional summarizer. Provide clear, concise summaries that capture the main points and key insights. Focus on accuracy and readability.",
            "model": "claude-3-5-sonnet",
            "temperature": 0.3,
            "max_tokens": 1000,
            "price_per_run": 0.5,
            "category": "content",
            "tags": ["summarization", "content", "productivity"],
            "config": {
                "max_input_length": 10000,
                "summary_length": "medium",
                "include_bullet_points": True,
            },
        },
        {
            "name": "Code Review Assistant",
            "slug": "code-review-assistant",
            "description": "Reviews code for best practices, bugs, and security issues.",
            "system_prompt": "You are a senior software engineer conducting code reviews. Analyze the code for: 1) Bugs and logical errors, 2) Security vulnerabilities, 3) Performance issues, 4) Code style and best practices, 5) Test coverage. Provide actionable feedback.",
            "model": "gpt-4",
            "temperature": 0.2,
            "max_tokens": 2000,
            "price_per_run": 1.0,
            "category": "development",
            "tags": ["code", "review", "security", "best-practices"],
            "config": {
                "languages": ["python", "javascript", "typescript", "java"],
                "strictness": "balanced",
                "include_examples": True,
            },
        },
        {
            "name": "Business Plan Generator",
            "slug": "business-plan-generator",
            "description": "Creates comprehensive business plans with market analysis and financial projections.",
            "system_prompt": "You are a business consultant helping entrepreneurs create professional business plans. Structure the plan with: Executive Summary, Market Analysis, Company Description, Organization & Management, Marketing & Sales Strategy, Financial Projections, Funding Request (if applicable).",
            "model": "claude-3-5-sonnet",
            "temperature": 0.4,
            "max_tokens": 3000,
            "price_per_run": 2.5,
            "category": "business",
            "tags": ["planning", "strategy", "finance", "startup"],
            "config": {
                "include_financial_templates": True,
                "market_research_depth": "standard",
                "export_formats": ["pdf", "docx"],
            },
        },
        {
            "name": "Customer Support Bot",
            "slug": "customer-support-bot",
            "description": "Handles common customer inquiries with empathy and accuracy.",
            "system_prompt": "You are a customer support representative. Be empathetic, helpful, and accurate. If you don't know the answer, admit it and offer to escalate. Always maintain a professional and friendly tone.",
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 800,
            "price_per_run": 0.3,
            "category": "support",
            "tags": ["customer-service", "faq", "automation"],
            "config": {
                "knowledge_base_integration": True,
                "escalation_threshold": 0.8,
                "multilingual_support": True,
            },
        },
        {
            "name": "Data Analysis Assistant",
            "slug": "data-analysis-assistant",
            "description": "Analyzes datasets and provides insights, visualizations, and recommendations.",
            "system_prompt": "You are a data analyst. Given a dataset or data description, provide: 1) Key statistics and insights, 2) Potential visualizations, 3) Trends and patterns, 4) Actionable recommendations, 5) Limitations and caveats.",
            "model": "claude-3-5-sonnet",
            "temperature": 0.3,
            "max_tokens": 1500,
            "price_per_run": 1.5,
            "category": "analytics",
            "tags": ["data", "analysis", "insights", "visualization"],
            "config": {
                "supported_formats": ["csv", "json", "excel"],
                "statistical_methods": ["descriptive", "correlation", "trend"],
                "visualization_types": ["chart", "graph", "dashboard"],
            },
        },
        {
            "name": "Creative Writing Coach",
            "slug": "creative-writing-coach",
            "description": "Helps with creative writing projects, providing feedback and inspiration.",
            "system_prompt": "You are a creative writing coach and editor. Provide constructive feedback on: 1) Plot and structure, 2) Character development, 3) Dialogue, 4) Setting and description, 5) Voice and style. Be encouraging but honest.",
            "model": "claude-3-5-sonnet",
            "temperature": 0.8,
            "max_tokens": 1200,
            "price_per_run": 0.8,
            "category": "creative",
            "tags": ["writing", "editing", "feedback", "creative"],
            "config": {
                "genres": ["fiction", "non-fiction", "poetry", "screenplay"],
                "feedback_depth": "detailed",
                "inspiration_prompts": True,
            },
        },
    ]
    
    created_agents = []
    
    for agent_data in marketplace_agents:
        # Check if agent already exists
        existing_agent = db.query(Agent).filter(Agent.slug == agent_data["slug"]).first()
        if existing_agent:
            print(f"Agent {agent_data['slug']} already exists, skipping...")
            created_agents.append(existing_agent)
            continue
        
        # Create agent
        agent = Agent(
            **agent_data,
            owner_id=owner.id,
            is_public=True,
            is_active=True,
        )
        db.add(agent)
        created_agents.append(agent)
    
    return created_agents


def seed_database() -> None:
    """Main seeding function.
    
    Rules:   must commit only if all operations succeed; must rollback on error
    message: claude-sonnet-4-6 | 2024-01-15 | add progress indicators and summary report
    """
    print("Starting database seeding...")
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Create demo users
        print("Creating demo users...")
        users = create_demo_users(db)
        
        # Create marketplace agents (owned by admin)
        print("Creating marketplace agents...")
        admin_user = users["admin@agenthub.com"]
        agents = create_marketplace_agents(db, admin_user)
        
        # Commit all changes
        db.commit()
        
        print(f"\n✅ Seeding completed successfully!")
        print(f"   Created {len(users)} users")
        print(f"   Created {len(agents)} marketplace agents")
        print(f"\nDemo credentials:")
        for email, user in users.items():
            print(f"   {email}: password = {email.split('@')[0]}Pass123!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()