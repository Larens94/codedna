"""test_structure.py — Test basic project structure and imports.

Rules: Should run without any game logic implemented.
"""

import sys
import os

def test_imports():
    """Test that all module imports work."""
    print("Testing project structure and imports...")
    
    # Add project root to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    try:
        # Test engine imports
        from engine import World, Entity, Component, System
        print("✓ Engine imports successful")
        
        # Test that Component is abstract
        try:
            comp = Component()
            print("✗ Component should be abstract")
            return False
        except (TypeError, NotImplementedError):
            print("✓ Component is properly abstract")
        
        # Test render imports (may fail if GLFW not installed, that's OK)
        try:
            from render import Renderer, Camera
            print("✓ Render imports successful")
        except ImportError as e:
            print(f"⚠ Render imports: {e} (GLFW/PyOpenGL may not be installed)")
        
        # Test gameplay imports
        from gameplay import Game
        print("✓ Gameplay imports successful")
        
        # Test data imports
        from data import AssetManager
        print("✓ Data imports successful")
        
        # Test integration imports
        from integration import PerformanceMonitor
        print("✓ Integration imports successful")
        
        # Test main entry point
        import main
        print("✓ Main module imports successful")
        
        print("\n✅ All structural tests passed!")
        return True
        
    except ImportError as e:
        print(f"\n❌ Import failed: {e}")
        print("Please check the module structure and __init__.py files")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

def test_directory_structure():
    """Verify required directories exist."""
    print("\nChecking directory structure...")
    
    required_dirs = [
        'engine',
        'render', 
        'gameplay',
        'data',
        'integration',
        'reasoning_logs'
    ]
    
    all_exist = True
    for dir_name in required_dirs:
        if os.path.exists(dir_name) and os.path.isdir(dir_name):
            print(f"✓ Directory exists: {dir_name}/")
        else:
            print(f"✗ Missing directory: {dir_name}/")
            all_exist = False
    
    # Check for required files
    required_files = [
        'main.py',
        'requirements.txt',
        'engine/__init__.py',
        'render/__init__.py',
        'gameplay/__init__.py',
        'data/__init__.py',
        'integration/__init__.py',
        'reasoning_logs/team_decisions.md'
    ]
    
    print("\nChecking required files...")
    for file_name in required_files:
        if os.path.exists(file_name):
            print(f"✓ File exists: {file_name}")
        else:
            print(f"✗ Missing file: {file_name}")
            all_exist = False
    
    return all_exist

if __name__ == "__main__":
    print("=" * 60)
    print("Game Architecture Structure Test")
    print("=" * 60)
    
    dir_ok = test_directory_structure()
    import_ok = test_imports()
    
    print("\n" + "=" * 60)
    if dir_ok and import_ok:
        print("✅ Project structure is correct!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Run the game: python main.py")
        print("3. Implement gameplay systems in gameplay/")
        print("4. Add assets to assets/ directory")
    else:
        print("❌ Project structure needs fixing")
        sys.exit(1)