"""test_game_run.py — Quick test to verify game runs.

exports: test_game_initialization()
used_by: Development verification
rules:   Must not modify game state, run quickly
agent:   Game Director | 2024-01-15 | Created game verification test
"""

import sys
import logging
from gameplay.game import Game

logging.basicConfig(level=logging.WARNING)  # Reduce log noise for test

def test_game_initialization():
    """Test that game initializes correctly."""
    print("Testing game initialization...")
    
    try:
        # Create game instance
        game = Game()
        
        # Try to initialize
        success = game.initialize()
        
        if success:
            print("✓ Game initialized successfully")
            
            # Check that modules were created
            if game.world:
                print("✓ ECS world created")
            else:
                print("✗ ECS world not created")
                
            if game.renderer:
                print("✓ Renderer created")
            else:
                print("✗ Renderer not created")
                
            if game.asset_manager:
                print("✓ Asset manager created")
            else:
                print("✗ Asset manager not created")
                
            # Shutdown cleanly
            game.shutdown()
            print("✓ Game shutdown cleanly")
            
            return True
        else:
            print("✗ Game initialization failed")
            return False
            
    except Exception as e:
        print(f"✗ Exception during test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_module_imports():
    """Test that all required modules can be imported."""
    print("\nTesting module imports...")
    
    modules_to_test = [
        ("engine", "World"),
        ("render", "Renderer"),
        ("data", "AssetManager"),
        ("gameplay.components", "Position"),
        ("gameplay.systems", "MovementSystem"),
        ("integration.performance", "PerformanceMonitor"),
    ]
    
    all_imports_ok = True
    for module_name, class_name in modules_to_test:
        try:
            exec(f"from {module_name} import {class_name}")
            print(f"✓ {module_name}.{class_name}")
        except ImportError as e:
            print(f"✗ {module_name}.{class_name}: {e}")
            all_imports_ok = False
    
    return all_imports_ok

def test_assets_directory():
    """Test that assets directory exists with required files."""
    print("\nTesting assets directory...")
    
    import os
    from pathlib import Path
    
    assets_dir = Path("assets")
    if not assets_dir.exists():
        print("✗ Assets directory does not exist")
        return False
    
    print(f"✓ Assets directory exists at: {assets_dir.absolute()}")
    
    # Check for config file
    config_file = assets_dir / "game_config.json"
    if config_file.exists():
        print(f"✓ Config file exists: {config_file}")
        
        # Try to load it
        try:
            import json
            with open(config_file, 'r') as f:
                config = json.load(f)
            print(f"✓ Config file is valid JSON")
            print(f"  Game title: {config.get('game', {}).get('title', 'Unknown')}")
        except Exception as e:
            print(f"✗ Failed to load config: {e}")
            return False
    else:
        print(f"✗ Config file missing: {config_file}")
        return False
    
    return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("2D RPG Game - Integration Test")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Module imports
    tests_total += 1
    if test_module_imports():
        tests_passed += 1
    
    # Test 2: Assets directory
    tests_total += 1
    if test_assets_directory():
        tests_passed += 1
    
    # Test 3: Game initialization (quick test without full render)
    tests_total += 1
    print("\nNote: Game initialization test may open a window briefly")
    print("Press ESC or close window to continue...")
    if test_game_initialization():
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Test Results: {tests_passed}/{tests_total} passed")
    
    if tests_passed == tests_total:
        print("✓ All tests passed! Game should run correctly.")
        print("\nTo run the full game:")
        print("  python main.py")
        return 0
    else:
        print("✗ Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())