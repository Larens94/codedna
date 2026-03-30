"""test_structure.py — Verify the basic structure and imports work.

exports: test_imports(), test_models(), test_config()
used_by: development verification
rules:   must not modify database; must be safe to run anytime
agent:   ProductArchitect | 2024-01-15 | created basic structure verification
         message: "add comprehensive integration tests for each module"
"""

import sys
import os

def test_imports() -> bool:
    """Test that all main modules can be imported."""
    print("Testing imports...")
    
    modules_to_test = [
        "agenthub.main",
        "agenthub.config",
        "agenthub.db.models",
        "agenthub.db.session",
        "agenthub.seed",
        "agenthub.cli",
    ]
    
    all_imports_ok = True
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"  ✅ {module_name}")
        except ImportError as e:
            print(f"  ❌ {module_name}: {e}")
            all_imports_ok = False
    
    return all_imports_ok


def test_config() -> bool:
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    try:
        from agenthub.config import settings
        print(f"  ✅ Settings loaded")
        print(f"     APP_NAME: {settings.APP_NAME}")
        print(f"     DEBUG: {settings.DEBUG}")
        print(f"     DATABASE_URL: {settings.DATABASE_URL[:30]}...")
        return True
    except Exception as e:
        print(f"  ❌ Failed to load settings: {e}")
        return False


def test_models() -> bool:
    """Test model definitions."""
    print("\nTesting models...")
    
    try:
        from agenthub.db.models import Base, User, Agent, AgentRun
        print(f"  ✅ Base model: {Base}")
        print(f"  ✅ User model: {User}")
        print(f"  ✅ Agent model: {Agent}")
        print(f"  ✅ AgentRun model: {AgentRun}")
        
        # Check table names
        assert User.__tablename__ == "users"
        assert Agent.__tablename__ == "agents"
        assert AgentRun.__tablename__ == "agent_runs"
        print(f"  ✅ Table names are correct")
        
        return True
    except Exception as e:
        print(f"  ❌ Model test failed: {e}")
        return False


def test_directory_structure() -> bool:
    """Verify required directories exist."""
    print("\nTesting directory structure...")
    
    required_dirs = [
        "agenthub",
        "agenthub/api",
        "agenthub/auth",
        "agenthub/db",
        "docs",
    ]
    
    all_dirs_ok = True
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"  ✅ {dir_name}/")
        else:
            print(f"  ❌ {dir_name}/ (missing)")
            all_dirs_ok = False
    
    return all_dirs_ok


def test_files_exist() -> bool:
    """Verify required files exist."""
    print("\nTesting required files...")
    
    required_files = [
        "agenthub/main.py",
        "agenthub/config.py",
        "agenthub/db/models.py",
        "agenthub/db/session.py",
        "agenthub/seed.py",
        "agenthub/cli.py",
        "agenthub/api/__init__.py",
        "agenthub/api/agents.py",
        "agenthub/api/auth.py",
        "agenthub/api/billing.py",
        "agenthub/api/scheduler.py",
        "agenthub/api/users.py",
        "agenthub/auth/dependencies.py",
        "requirements.txt",
        "README.md",
        "docs/architecture.md",
        ".env.example",
    ]
    
    all_files_ok = True
    for file_name in required_files:
        if os.path.exists(file_name):
            print(f"  ✅ {file_name}")
        else:
            print(f"  ❌ {file_name} (missing)")
            all_files_ok = False
    
    return all_files_ok


def main() -> None:
    """Run all structure tests."""
    print("=" * 60)
    print("AgentHub Structure Verification")
    print("=" * 60)
    
    tests = [
        test_directory_structure,
        test_files_exist,
        test_imports,
        test_config,
        test_models,
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"  ❌ Test {test_func.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    all_passed = all(results)
    if all_passed:
        print("✅ All tests passed! The structure is correct.")
        print("\nNext steps:")
        print("1. Copy .env.example to .env")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Create tables: python -m agenthub.cli create-tables")
        print("4. Seed database: python -m agenthub.cli seed")
        print("5. Run server: uvicorn agenthub.main:app --reload")
    else:
        print("❌ Some tests failed. Please check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()