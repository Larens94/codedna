#!/usr/bin/env python3
"""Simple test to verify imports work."""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing imports...")

try:
    # Test engine imports
    from engine import World, Entity, Component, System
    print("✓ Engine imports: World, Entity, Component, System")
    
    # Test that Component is abstract
    try:
        comp = Component()
        print("✗ ERROR: Component should be abstract")
    except (TypeError, NotImplementedError):
        print("✓ Component is properly abstract")
    
    # Test gameplay import
    from gameplay import Game
    print("✓ Gameplay import: Game")
    
    # Test data import
    from data import AssetManager
    print("✓ Data import: AssetManager")
    
    # Test integration import
    from integration import PerformanceMonitor
    print("✓ Integration import: PerformanceMonitor")
    
    # Test main module
    import main
    print("✓ Main module imports")
    
    print("\n✅ All imports successful!")
    print("\nProject structure is correct.")
    print("\nNext: Install dependencies with: pip install -r requirements.txt")
    print("Then run: python main.py")
    
except ImportError as e:
    print(f"\n❌ Import error: {e}")
    print("\nCheck that all __init__.py files exist and export the correct names.")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)