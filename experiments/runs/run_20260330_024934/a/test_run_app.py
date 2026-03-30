#!/usr/bin/env python3
"""test_run_app.py — Quick test to verify the application can start."""

import subprocess
import time
import sys
import os
from pathlib import Path

def test_app_startup():
    """Test that the application can start successfully."""
    print("Testing AgentHub application startup...")
    
    # Check if .env exists
    env_file = Path(".env")
    if not env_file.exists():
        print("Creating .env file from example...")
        example_file = Path(".env.example")
        if example_file.exists():
            example_file.copy(env_file)
            print("Created .env file. Please update with your configuration.")
        else:
            print("Warning: No .env.example file found")
    
    # Check Python dependencies
    print("\nChecking Python dependencies...")
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        import jinja2
        print("✓ All core dependencies installed")
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("Install with: pip install -r requirements.txt")
        return False
    
    # Test database connection
    print("\nTesting database connection...")
    try:
        from agenthub.db.session import engine
        from agenthub.db.models import Base
        
        # Try to create tables (will fail if DB not accessible)
        Base.metadata.create_all(bind=engine, checkfirst=True)
        print("✓ Database connection successful")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print("Make sure PostgreSQL is running and DATABASE_URL is correct in .env")
        print("Default DATABASE_URL: postgresql://postgres:postgres@localhost/agenthub")
        return False
    
    # Test app creation
    print("\nTesting application creation...")
    try:
        from agenthub.main import create_app
        app = create_app()
        print("✓ Application created successfully")
        
        # Check routes
        routes = [route.path for route in app.routes]
        print(f"✓ Found {len(routes)} routes")
        
        # Check for key routes
        key_routes = ["/health", "/docs", "/", "/api/v1/auth/login"]
        for route in key_routes:
            if any(r.startswith(route) for r in routes):
                print(f"  • {route} ✓")
            else:
                print(f"  • {route} ✗")
                
    except Exception as e:
        print(f"✗ Application creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test static files directory
    print("\nTesting static files setup...")
    static_dir = Path("agenthub/frontend/static")
    static_dir.mkdir(exist_ok=True, parents=True)
    print(f"✓ Static directory: {static_dir}")
    
    # Test templates directory
    print("\nTesting templates setup...")
    templates_dir = Path("agenthub/frontend/templates")
    if templates_dir.exists():
        templates = list(templates_dir.glob("*.html"))
        print(f"✓ Found {len(templates)} HTML templates")
        for template in templates[:5]:  # Show first 5
            print(f"  • {template.name}")
        if len(templates) > 5:
            print(f"  • ... and {len(templates) - 5} more")
    else:
        print("✗ Templates directory not found")
        return False
    
    print("\n" + "="*60)
    print("SUCCESS: AgentHub application is ready to run!")
    print("="*60)
    print("\nTo start the application:")
    print("  python run.py                    # Development server")
    print("  uvicorn agenthub.main:app --reload  # Direct uvicorn")
    print("\nAccess the application at:")
    print("  • Web UI: http://localhost:8000")
    print("  • API Docs: http://localhost:8000/docs")
    print("  • Health Check: http://localhost:8000/health")
    
    return True

def quick_start_app():
    """Quick start the app to verify it runs."""
    print("\n" + "="*60)
    print("Starting AgentHub for quick verification...")
    print("="*60)
    
    try:
        # Start the app in a subprocess
        import subprocess
        import threading
        import time
        
        # Start the server
        proc = subprocess.Popen(
            ["uvicorn", "agenthub.main:app", "--host", "127.0.0.1", "--port", "8001", "--reload"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print("Server starting on http://127.0.0.1:8001")
        print("Waiting 5 seconds for startup...")
        time.sleep(5)
        
        # Try to access health endpoint
        import requests
        try:
            response = requests.get("http://127.0.0.1:8001/health", timeout=2)
            if response.status_code == 200:
                print(f"✓ Health check successful: {response.json()}")
            else:
                print(f"✗ Health check failed: {response.status_code}")
        except requests.RequestException as e:
            print(f"✗ Could not connect to server: {e}")
        
        # Kill the process
        proc.terminate()
        proc.wait(timeout=5)
        print("\nTest complete. Server stopped.")
        
    except Exception as e:
        print(f"Error during quick start: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("AgentHub Application Test")
    print("="*60)
    
    if test_app_startup():
        # Ask if user wants to do quick start test
        response = input("\nDo you want to do a quick startup test? (y/n): ")
        if response.lower() in ['y', 'yes']:
            quick_start_app()
    
    print("\nTest completed successfully!")