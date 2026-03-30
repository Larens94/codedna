#!/usr/bin/env python
"""Demonstration of AgentHub seed functionality."""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set test environment
os.environ['FLASK_ENV'] = 'development'

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.commands import (
    create_default_plans, 
    create_demo_user, 
    create_marketplace_agents,
    create_tags,
    associate_tags_with_agents,
    create_demo_agent_runs
)

def main():
    """Demonstrate seed functionality."""
    print("=" * 60)
    print("AgentHub Seed Functionality Demonstration")
    print("=" * 60)
    
    # Create application
    app = create_app()
    
    with app.app_context():
        # Create database tables
        print("\n1. Creating database tables...")
        db.create_all()
        print("   ✓ Tables created")
        
        # Create default plans
        print("\n2. Creating default subscription plans...")
        plans = create_default_plans()
        db.session.commit()
        print(f"   ✓ Created {len(plans)} plans:")
        for plan in plans:
            print(f"     - {plan.name}: ${plan.price_monthly_usd}/month")
        
        # Create demo user
        print("\n3. Creating demo user...")
        user = create_demo_user()
        db.session.commit()
        print(f"   ✓ Created demo user:")
        print(f"     - Username: {user.username}")
        print(f"     - Email: {user.email}")
        print(f"     - Name: {user.first_name} {user.last_name}")
        
        # Create marketplace agents
        print("\n4. Creating 6 marketplace agents...")
        agents = create_marketplace_agents(user)
        db.session.commit()
        print(f"   ✓ Created {len(agents)} agents:")
        for agent in agents:
            print(f"     - {agent.name} (${agent.price_per_run}/run)")
            print(f"       Category: {agent.category.value}")
            print(f"       Status: {agent.status.value}")
        
        # Create tags
        print("\n5. Creating tags...")
        tags = create_tags()
        db.session.commit()
        print(f"   ✓ Created {len(tags)} tags:")
        tag_names = [tag.name for tag in tags]
        print(f"     Tags: {', '.join(tag_names)}")
        
        # Associate tags with agents
        print("\n6. Associating tags with agents...")
        associate_tags_with_agents(agents, tags)
        db.session.commit()
        
        for agent in agents[:2]:  # Show first 2 agents with tags
            agent_tags = [tag.name for tag in agent.tags]
            print(f"     - {agent.name}: {', '.join(agent_tags)}")
        print(f"     ... and {len(agents) - 2} more agents tagged")
        
        # Create demo agent runs
        print("\n7. Creating demo agent runs...")
        runs = create_demo_agent_runs(user, agents[:3])  # Runs for first 3 agents
        db.session.commit()
        print(f"   ✓ Created {len(runs)} agent runs")
        
        # Show statistics
        print("\n8. Final statistics:")
        from app.models.user import User
        from app.models.agent import Agent, AgentRun
        
        total_users = User.query.count()
        total_agents = Agent.query.count()
        total_runs = AgentRun.query.count()
        
        print(f"   - Total users: {total_users}")
        print(f"   - Total agents: {total_agents}")
        print(f"   - Total agent runs: {total_runs}")
        
        # Show sample agent run
        sample_run = AgentRun.query.first()
        if sample_run:
            print(f"\n9. Sample agent run:")
            print(f"   - Agent: {sample_run.agent.name}")
            print(f"   - Status: {sample_run.status.value}")
            print(f"   - Execution time: {sample_run.execution_time_ms}ms")
            print(f"   - Cost: ${sample_run.cost_usd}")
        
        print("\n" + "=" * 60)
        print("Seed demonstration completed successfully!")
        print("=" * 60)
        
        # Instructions for using the seeded data
        print("\nNext steps:")
        print("1. Start the Flask server: python run.py")
        print("2. Login with demo credentials:")
        print("   - Email: demo@agenthub.com")
        print("   - Password: demopassword123")
        print("3. Explore the API at http://localhost:5000/api/v1/")
        print("4. Check health endpoint: http://localhost:5000/health")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\nError during demonstration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)