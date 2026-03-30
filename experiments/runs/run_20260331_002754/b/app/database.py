"""Database configuration for AgentHub with FastAPI and Flask integration."""

from typing import Generator, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.ext.declarative import declarative_base

from app.core.config import settings

# Use the same declarative base as Flask-SQLAlchemy
from app import db

# Create engine using settings
# Note: We use db.engine if it exists (after Flask app initialization),
# otherwise create a new engine with the same parameters
engine = create_engine(
    settings.DATABASE_URL,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
    pool_pre_ping=settings.DATABASE_POOL_PRE_PING,
    echo=settings.DEBUG,
    future=True,  # Use SQLAlchemy 2.0 style
)

# Create session factory for FastAPI
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)

# Scoped session for thread safety
scoped_session_factory = scoped_session(SessionLocal)


def get_db() -> Generator[Session, None, None]:
    """Get database session dependency for FastAPI.
    
    Yields:
        SQLAlchemy session
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_scoped_session() -> Session:
    """Get a scoped session for background tasks.
    
    Returns:
        Scoped SQLAlchemy session
    """
    return scoped_session_factory()


def init_flask_engine(flask_app):
    """Initialize Flask-SQLAlchemy engine and bind it to our session factory.
    
    This ensures both Flask and FastAPI use the same engine.
    
    Args:
        flask_app: Flask application instance
    """
    global engine, SessionLocal, scoped_session_factory
    
    # Use Flask's engine
    flask_engine = db.get_engine(flask_app)
    if flask_engine:
        engine = flask_engine
        # Recreate session factories with Flask's engine
        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
            future=True,
        )
        scoped_session_factory = scoped_session(SessionLocal)


# Import all models to ensure they are registered with SQLAlchemy
# This is important for Alembic migrations and querying
from app.models.user import User, UserSession
from app.models.agent import Agent, AgentVersion, AgentReview, Tag, AgentStatus, AgentCategory
from app.models.agent_run import AgentRun, AgentRunLog, AgentRunStatus
from app.models.subscription import (
    Plan, PlanType, Subscription, SubscriptionStatus, BillingCycle,
    BillingAccount, Invoice, InvoiceStatus
)
from app.models.organization import Organization, OrganizationRole, OrgMembership
from app.models.memory import Memory, MemoryType, MemoryImportance, MemoryAssociation
from app.models.usage_log import UsageLog, UsageType, ProviderType, PricingRate
from app.models.audit_log import AuditLog, AuditAction, AuditSeverity
from app.models.scheduled_task import ScheduledTask, TaskRun, TaskStatus, TaskRecurrence
from app.models.credit import (
    CreditAccount, CreditTransaction, CreditPlan, CreditTransactionType
)

# Export all models for easy import
__all__ = [
    # Core models
    'User', 'UserSession',
    'Agent', 'AgentVersion', 'AgentReview', 'Tag', 'AgentStatus', 'AgentCategory',
    'AgentRun', 'AgentRunLog', 'AgentRunStatus',
    
    # Subscription and billing
    'Plan', 'PlanType', 'Subscription', 'SubscriptionStatus', 'BillingCycle',
    'BillingAccount', 'Invoice', 'InvoiceStatus',
    
    # Organization
    'Organization', 'OrganizationRole', 'OrgMembership',
    
    # Memory
    'Memory', 'MemoryType', 'MemoryImportance', 'MemoryAssociation',
    
    # Usage tracking
    'UsageLog', 'UsageType', 'ProviderType', 'PricingRate',
    
    # Audit logging
    'AuditLog', 'AuditAction', 'AuditSeverity',
    
    # Scheduled tasks
    'ScheduledTask', 'TaskRun', 'TaskStatus', 'TaskRecurrence',
    
    # Credit system
    'CreditAccount', 'CreditTransaction', 'CreditPlan', 'CreditTransactionType',
    
    # Database utilities
    'get_db', 'get_scoped_session', 'init_flask_engine',
]