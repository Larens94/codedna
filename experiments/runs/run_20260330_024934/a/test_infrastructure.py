#!/usr/bin/env python3
"""Test the infrastructure components."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agenthub.db.models import Base, User, Agent, AgentRun, ScheduledTask, CreditAccount, Invoice, OrgMembership, AuditLog
from agenthub.db.session import engine, SessionLocal
from agenthub.config import settings

def test_database_models():
    """Test that database models can be imported and inspected."""
    print("Testing database models...")
    
    # Check all models are defined
    models = [User, Agent, AgentRun, ScheduledTask, CreditAccount, Invoice, OrgMembership, AuditLog]
    
    for model in models:
        print(f"  ✓ {model.__name__}: {model.__tablename__}")
        
        # Check required columns
        required_columns = ['id', 'created_at']
        for col in required_columns:
            if hasattr(model, col):
                print(f"    - Has {col} column")
            else:
                print(f"    ✗ Missing {col} column")
    
    print("Database models test completed.\n")

def test_billing_components():
    """Test that billing components can be imported."""
    print("Testing billing components...")
    
    try:
        from agenthub.billing.credits import CreditEngine, deduct_credits, get_balance
        from agenthub.billing.stripe import StripeIntegration, create_checkout_session
        from agenthub.billing.invoices import InvoiceGenerator, generate_invoice_pdf
        from agenthub.billing.plans import PLANS, get_user_plan
        
        print("  ✓ CreditEngine imported")
        print("  ✓ StripeIntegration imported")
        print("  ✓ InvoiceGenerator imported")
        print("  ✓ PLANS configuration loaded")
        
        # Check plan structure
        required_plans = ['free', 'starter', 'pro', 'enterprise']
        for plan in required_plans:
            if plan in PLANS:
                print(f"    ✓ {plan} plan defined")
            else:
                print(f"    ✗ {plan} plan missing")
                
    except ImportError as e:
        print(f"  ✗ Import error: {e}")
    
    print("Billing components test completed.\n")

def test_scheduler_components():
    """Test that scheduler components can be imported."""
    print("Testing scheduler components...")
    
    try:
        from agenthub.scheduler.setup import SchedulerManager, get_scheduler, add_scheduled_job
        from agenthub.scheduler.runner import TaskRunner, execute_scheduled_task
        
        print("  ✓ SchedulerManager imported")
        print("  ✓ TaskRunner imported")
        
    except ImportError as e:
        print(f"  ✗ Import error: {e}")
    
    print("Scheduler components test completed.\n")

def test_api_routers():
    """Test that API routers can be imported."""
    print("Testing API routers...")
    
    try:
        from agenthub.api.teams import router as teams_router
        from agenthub.api.usage import router as usage_router
        from agenthub.api.billing import router as billing_router
        
        print("  ✓ Teams router imported")
        print("  ✓ Usage router imported")
        print("  ✓ Billing router imported")
        
        # Check routes
        teams_routes = [route.path for route in teams_router.routes]
        print(f"    Teams routes: {len(teams_routes)} endpoints")
        
        usage_routes = [route.path for route in usage_router.routes]
        print(f"    Usage routes: {len(usage_routes)} endpoints")
        
    except ImportError as e:
        print(f"  ✗ Import error: {e}")
    
    print("API routers test completed.\n")

def test_workers():
    """Test that worker components can be imported."""
    print("Testing worker components...")
    
    try:
        from agenthub.workers.processor import JobProcessor, enqueue_agent_run, get_job_status
        
        print("  ✓ JobProcessor imported")
        print("  ✓ Worker functions imported")
        
    except ImportError as e:
        print(f"  ✗ Import error: {e}")
    
    print("Worker components test completed.\n")

def test_configuration():
    """Test configuration settings."""
    print("Testing configuration...")
    
    required_settings = [
        'DATABASE_URL',
        'SECRET_KEY',
        'DB_POOL_SIZE',
        'DB_MAX_OVERFLOW',
        'STRIPE_SECRET_KEY',
        'CREDIT_EXCHANGE_RATE',
        'AGENT_EXECUTION_TIMEOUT',
        'SCHEDULER_INTERVAL'
    ]
    
    for setting in required_settings:
        if hasattr(settings, setting):
            value = getattr(settings, setting)
            if value is not None:
                print(f"  ✓ {setting}: Configured")
            else:
                print(f"  ⚠ {setting}: Not set (using default)")
        else:
            print(f"  ✗ {setting}: Missing from settings")
    
    print("Configuration test completed.\n")

def main():
    """Run all tests."""
    print("=" * 60)
    print("AgentHub Infrastructure Test Suite")
    print("=" * 60)
    print()
    
    test_database_models()
    test_billing_components()
    test_scheduler_components()
    test_api_routers()
    test_workers()
    test_configuration()
    
    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()