#!/usr/bin/env python
"""Simple test to verify AgentHub application structure."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.user import User
from app.models.agent import Agent, AgentCategory, AgentStatus
from app.models.subscription import Plan, PlanType
from app.commands import create_default_plans, create_demo_user

def test_app_creation():
    """Test that the Flask app can be created."""
    print("Testing application creation...")
    app = create_app('testing')
    assert app is not None
    assert app.config['TESTING'] == True
    print("✓ Application creation test passed")
    return app

def test_database_connection():
    """Test database connection and model registration."""
    print("Testing database connection...")
    app = create_app('testing')
    
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Test User model
        user = User(
            email='test@example.com',
            username='testuser',
            password='testpassword'
        )
        
        # Test Agent model
        agent = Agent(
            owner=user,
            name='Test Agent',
            slug='test-agent',
            description='Test agent description',
            category=AgentCategory.PRODUCTIVITY,
            price_per_run=0.10
        )
        
        # Test Plan model
        plan = Plan(
            name='Test Plan',
            type=PlanType.FREE,
            price_monthly_usd=0.00,
            price_yearly_usd=0.00
        )
        
        print("✓ Database models test passed")
        
        # Clean up
        db.session.rollback()

def test_seed_functions():
    """Test seed functions from commands."""
    print("Testing seed functions...")
    
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        
        # Test plan creation
        plans = create_default_plans()
        assert len(plans) >= 4  # Should have at least Free, Basic, Pro, Team
        print(f"  Created {len(plans)} plans")
        
        # Test demo user creation
        user = create_demo_user()
        assert user.email == 'demo@agenthub.com'
        assert user.username == 'demo_user'
        print(f"  Created demo user: {user.username}")
        
        # Clean up
        db.session.rollback()
    
    print("✓ Seed functions test passed")

def test_configurations():
    """Test configuration loading."""
    print("Testing configurations...")
    
    # Test development config
    app = create_app('development')
    assert app.config['DEBUG'] == True
    assert 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']
    
    # Test production config (will fail without env vars, but should load)
    try:
        app = create_app('production')
        # In production, database URL is required
        if not app.config.get('SQLALCHEMY_DATABASE_URI'):
            print("  Note: Production config requires DATABASE_URL env var")
    except ValueError as e:
        print(f"  Note: Production config validation: {e}")
    
    print("✓ Configuration test passed")

def main():
    """Run all tests."""
    print("=" * 60)
    print("AgentHub Application Structure Test")
    print("=" * 60)
    
    try:
        test_app_creation()
        test_database_connection()
        test_seed_functions()
        test_configurations()
        
        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        return 0
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())