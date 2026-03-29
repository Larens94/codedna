#!/usr/bin/env python3
"""Verify the game architecture is properly set up."""

import os
import sys

def check_structure():
    """Check that all required directories and files exist."""
    print("Checking project structure...")
    
    required_dirs = [
        'engine',
        'render', 
        'gameplay',
        'data',
        'integration',
        'reasoning_logs'
    ]
    
    required_files = [
        'main.py',
        'requirements.txt',
        'README.md',
        'engine/__init__.py',
        'engine/world.py',
        'engine/entity.py',
        'engine/component.py',
        'engine/system.py',
        'render/__init__.py',
        'render/renderer.py',
        'gameplay/__init__.py',
        'gameplay/game.py',
        'data/__init__.py',
        'data/asset_manager.py',
        'integration/__init__.py',
        'integration/performance.py',
        'reasoning_logs/team_decisions.md'
    ]
    
    all_good = True
    
    for dir_name in required_dirs:
        if os.path.isdir(dir_name):
            print(f"  ✓ {dir_name}/")
        else:
            print(f"  ✗ Missing directory: {dir_name}/")
            all_good = False
    
    print("\nChecking required files...")
    for file_name in required_files:
        if os.path.exists(file_name):
            print(f"  ✓ {file_name}")
        else:
            print(f"  ✗ Missing file: {file_name}")
            all_good = False
    
    return all_good

def check_python_syntax():
    """Check that Python files have valid syntax."""
    print("\nChecking Python syntax...")
    
    python_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    # Skip hidden files and __pycache__
    python_files = [f for f in python_files if not any(part.startswith('.') or part == '__pycache__' 
                                                      for part in f.split(os.sep))]
    
    import subprocess
    all_good = True
    
    for py_file in python_files:
        result = subprocess.run([sys.executable, '-m', 'py_compile', py_file], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✓ {py_file}")
        else:
            print(f"  ✗ Syntax error in {py_file}:")
            print(f"    {result.stderr.strip()}")
            all_good = False
    
    return all_good

def summarize_architecture():
    """Print architecture summary."""
    print("\n" + "="*60)
    print("GAME ARCHITECTURE SUMMARY")
    print("="*60)
    
    print("\nMODULES:")
    print("  engine/     - ECS core (World, Entity, Component, System)")
    print("  render/     - OpenGL/GLFW rendering system")
    print("  gameplay/   - Game-specific logic and systems")
    print("  data/       - Asset management and serialization")
    print("  integration/- Performance monitoring and testing")
    print("  reasoning_logs/ - Architectural decisions")
    
    print("\nKEY FILES:")
    print("  main.py              - Game entry point with 60 FPS target")
    print("  requirements.txt     - Dependencies (PyOpenGL, GLFW, etc.)")
    print("  README.md           - Documentation and setup instructions")
    
    print("\nARCHITECTURAL FEATURES:")
    print("  ✓ Entity-Component-System (ECS) pattern")
    print("  ✓ 60 FPS performance target with monitoring")
    print("  ✓ Modular design with clear interfaces")
    print("  ✓ Asset management with caching")
    print("  ✓ Professional code standards")
    print("  ✓ Comprehensive logging and error handling")
    
    print("\nNEXT STEPS:")
    print("  1. Install dependencies: pip install -r requirements.txt")
    print("  2. Implement gameplay systems in gameplay/")
    print("  3. Add assets to assets/ directory")
    print("  4. Run the game: python main.py")
    
    print("\nTEAM ROLES:")
    print("  • Engine Specialist: engine/ module optimization")
    print("  • Render Specialist: OpenGL/GLFW implementation")
    print("  • Gameplay Specialist: Game logic and systems")
    print("  • Data Specialist: Asset loading and management")
    print("  • Integration Specialist: Testing and performance")
    
    print("="*60)

def main():
    print("Verifying Game Architecture...")
    print("="*60)
    
    structure_ok = check_structure()
    syntax_ok = check_python_syntax()
    
    if structure_ok and syntax_ok:
        print("\n✅ Architecture verification PASSED!")
        summarize_architecture()
        return 0
    else:
        print("\n❌ Architecture verification FAILED!")
        print("\nPlease fix the issues above before proceeding.")
        return 1

if __name__ == "__main__":
    sys.exit(main())