"""cli.py — Command-line interface for AgentHub.

exports: main()
used_by: development scripts, deployment automation
rules:   must handle errors gracefully; must provide clear usage instructions
agent:   AgentIntegrator | 2024-03-30 | added agent studio command to CLI
         message: "add more commands for user management and system maintenance"
"""

import argparse
import sys
import asyncio
from typing import Optional

from agenthub.seed import seed_database
from agenthub.db.session import engine
from agenthub.db.models import Base
from agenthub.agents.test_console import run_test_console, test_agent_interactively


def create_tables() -> None:
    """Create database tables.
    
    Rules:   must not drop existing tables; must handle connection errors
    message: claude-sonnet-4-6 | 2024-01-15 | add table verification and health checks
    """
    print("Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully")
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        sys.exit(1)


def drop_tables() -> None:
    """Drop all database tables (development only).
    
    Rules:   must require confirmation; must not run in production
    message: claude-sonnet-4-6 | 2024-01-15 | implement environment check and backup
    """
    print("⚠️  WARNING: This will drop ALL tables and delete ALL data!")
    confirmation = input("Type 'yes' to confirm: ")
    
    if confirmation.lower() != 'yes':
        print("Operation cancelled")
        return
    
    print("Dropping tables...")
    try:
        Base.metadata.drop_all(bind=engine)
        print("✅ Tables dropped successfully")
    except Exception as e:
        print(f"❌ Failed to drop tables: {e}")
        sys.exit(1)


def check_database() -> None:
    """Check database connection and health.
    
    Rules:   must verify connectivity and basic operations
    message: claude-sonnet-4-6 | 2024-01-15 | implement comprehensive health checks
    """
    print("Checking database connection...")
    try:
        with engine.connect() as conn:
            result = conn.execute("SELECT version()")
            db_version = result.scalar()
            print(f"✅ Connected to database: {db_version}")
            
            # Check if tables exist
            table_count = conn.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
            ).scalar()
            print(f"✅ Found {table_count} tables in public schema")
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)


def agent_studio() -> None:
    """Launch the Agent Studio test console.
    
    Rules:   must provide interactive testing of all agent features
    message: AgentIntegrator | 2024-03-30 | implemented agent studio console
    """
    print("Launching Agent Studio Test Console...")
    try:
        asyncio.run(run_test_console())
    except KeyboardInterrupt:
        print("\n\nAgent Studio closed")
    except Exception as e:
        print(f"❌ Agent Studio failed: {e}")
        sys.exit(1)


def list_agents() -> None:
    """List all marketplace agents.
    
    Rules:   must show agent details and capabilities
    message: AgentIntegrator | 2024-03-30 | added agent listing command
    """
    from agenthub.agents.catalog import MARKETPLACE_AGENTS
    
    print("\n" + "=" * 80)
    print("MARKETPLACE AGENTS")
    print("=" * 80)
    
    for i, agent in enumerate(MARKETPLACE_AGENTS, 1):
        print(f"\n{i}. {agent.name}")
        print(f"   Slug: {agent.slug}")
        print(f"   Description: {agent.description}")
        print(f"   Model: {agent.model}")
        print(f"   Temperature: {agent.temperature}")
        print(f"   Max Tokens: {agent.max_tokens}")
        print(f"   Price per run: ${agent.price_per_run}")
        print(f"   Category: {agent.category.value}")
        print(f"   Tags: {', '.join(agent.tags)}")
        print(f"   Required Tools: {', '.join(agent.required_tools)}")
    
    print(f"\nTotal agents: {len(MARKETPLACE_AGENTS)}")
    print("=" * 80)


def test_agent() -> None:
    """Test a specific agent interactively.
    
    Rules:   must accept agent slug as argument
    message: AgentIntegrator | 2024-03-30 | added agent testing command
    """
    parser = argparse.ArgumentParser(description="Test a specific agent")
    parser.add_argument("slug", help="Agent slug to test")
    
    # Parse only the slug argument
    # We need to handle this differently since main() already parses
    if len(sys.argv) > 2 and sys.argv[1] == "test-agent":
        slug = sys.argv[2]
        print(f"Testing agent: {slug}")
        test_agent_interactively(slug)
    else:
        print("Usage: python -m agenthub.cli test-agent <agent-slug>")
        print("\nAvailable agents:")
        from agenthub.agents.catalog import MARKETPLACE_AGENTS
        for agent in MARKETPLACE_AGENTS:
            print(f"  {agent.slug}: {agent.name}")
        sys.exit(1)


def main() -> None:
    """Main CLI entry point.
    
    Rules:   must parse arguments and dispatch to appropriate functions
    message: AgentIntegrator | 2024-03-30 | added agent studio and test commands
    """
    parser = argparse.ArgumentParser(
        description="AgentHub CLI - Development and administration tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m agenthub.cli seed          # Seed database with demo data
  python -m agenthub.cli create-tables # Create database tables
  python -m agenthub.cli check-db      # Check database connection
  python -m agenthub.cli agent-studio  # Launch Agent Studio test console
  python -m agenthub.cli list-agents   # List all marketplace agents
  python -m agenthub.cli test-agent seo-optimizer  # Test SEO Optimizer agent
        """
    )
    
    parser.add_argument(
        "command",
        choices=[
            "seed", 
            "create-tables", 
            "drop-tables", 
            "check-db",
            "agent-studio",
            "list-agents",
            "test-agent"
        ],
        help="Command to execute"
    )
    
    # For test-agent, we need the slug argument
    if len(sys.argv) > 1 and sys.argv[1] == "test-agent":
        if len(sys.argv) < 3:
            print("Error: test-agent requires an agent slug")
            print("Usage: python -m agenthub.cli test-agent <agent-slug>")
            sys.exit(1)
        # Call test_agent function directly
        test_agent()
        return
    
    args = parser.parse_args()
    
    command_handlers = {
        "seed": seed_database,
        "create-tables": create_tables,
        "drop-tables": drop_tables,
        "check-db": check_database,
        "agent-studio": agent_studio,
        "list-agents": list_agents,
        "test-agent": test_agent,  # This won't be called directly due to above check
    }
    
    handler = command_handlers.get(args.command)
    if handler:
        handler()
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()