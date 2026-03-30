#!/usr/bin/env python3
"""run.py — Development server runner for AgentHub.

Usage:
    python run.py [--host HOST] [--port PORT] [--reload] [--workers WORKERS]

Examples:
    python run.py                    # Start with defaults
    python run.py --host 0.0.0.0     # Listen on all interfaces
    python run.py --port 8080        # Use port 8080
    python run.py --reload           # Enable auto-reload
    python run.py --workers 4        # Start with 4 workers
"""

import argparse
import os
import sys
import subprocess
import time
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        import jinja2
        return True
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please install requirements: pip install -r requirements.txt")
        return False

def check_env_file():
    """Check if .env file exists, create from example if not."""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists():
        if env_example.exists():
            print(f"Creating .env file from {env_example}")
            env_example.copy(env_file)
            print("Please update .env with your configuration")
            return False
        else:
            print("Warning: No .env or .env.example file found")
            return True
    return True

def check_database():
    """Check if database is accessible."""
    try:
        from agenthub.db.session import engine
        from agenthub.db.models import Base
        
        # Try to connect
        with engine.connect() as conn:
            print("✓ Database connection successful")
            
        # Check if tables exist
        inspector = sqlalchemy.inspect(engine)
        tables = inspector.get_table_names()
        
        if not tables:
            print("⚠ Database is empty, tables will be created on startup")
        else:
            print(f"✓ Found {len(tables)} tables in database")
            
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print("Please ensure PostgreSQL is running and DATABASE_URL is correct")
        return False

def start_server(host, port, reload, workers):
    """Start the FastAPI server."""
    cmd = [
        "uvicorn", 
        "agenthub.main:app",
        "--host", host,
        "--port", str(port),
    ]
    
    if reload:
        cmd.append("--reload")
        cmd.extend(["--reload-dir", "agenthub"])
        
    if workers > 1:
        cmd.extend(["--workers", str(workers)])
    
    print(f"Starting AgentHub server on http://{host}:{port}")
    print(f"  • Auto-reload: {'enabled' if reload else 'disabled'}")
    print(f"  • Workers: {workers}")
    print(f"  • API Docs: http://{host}:{port}/docs")
    print(f"  • Frontend: http://{host}:{port}/")
    print("\nPress Ctrl+C to stop\n")
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nServer stopped")
    except Exception as e:
        print(f"Error starting server: {e}")
        return False
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Run AgentHub development server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on code changes")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes (default: 1)")
    parser.add_argument("--skip-checks", action="store_true", help="Skip dependency and environment checks")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("AgentHub Development Server")
    print("=" * 60)
    
    if not args.skip_checks:
        print("\n[1/3] Checking dependencies...")
        if not check_dependencies():
            sys.exit(1)
        
        print("\n[2/3] Checking environment...")
        if not check_env_file():
            # Give user a chance to update .env
            input("\nPress Enter after updating .env file, or Ctrl+C to cancel...")
        
        print("\n[3/3] Checking database...")
        if not check_database():
            print("\nTo start PostgreSQL with Docker:")
            print("  docker run -d --name agenthub-postgres -p 5432:5432 \\")
            print("    -e POSTGRES_DB=agenthub -e POSTGRES_PASSWORD=postgres \\")
            print("    postgres:15-alpine")
            print("\nOr update DATABASE_URL in .env file")
            sys.exit(1)
    
    print("\n" + "=" * 60)
    start_server(args.host, args.port, args.reload, args.workers)

if __name__ == "__main__":
    main()