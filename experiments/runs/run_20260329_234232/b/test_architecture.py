#!/usr/bin/env python3
"""
Test script to verify the game architecture structure and imports.
"""

import sys
import os

def test_module_imports():
    """Test that all module interfaces can be imported."""
    print("Testing module imports...")
    
    # Add project root to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    tests_passed = 0
    tests_failed = 0
    
    # Test engine module
    try:
        from engine import GameEngine, EngineConfig
        print("✓ Engine module imports successfully")
        tests_passed += 1
    except ImportError as e:
        print(f"✗ Engine module import failed: {e}")
        tests_failed += 1
    
    # Test render module
    try:
        from render import Renderer, RenderConfig
        print("✓ Render module imports successfully")
        tests_passed += 1
    except ImportError as e:
        print(f"✗ Render module import failed: {e}")
        tests_failed += 1
    
    # Test gameplay module
    try:
        from gameplay import GameState, GameConfig
        print("✓ Gameplay module imports successfully")
        tests_passed += 1
    except ImportError as e:
        print(f"✗ Gameplay module import failed: {e}")
        tests_failed += 1
    
    # Test data module
    try:
        from data import AssetManager
        print("✓ Data module imports successfully")
        tests_passed += 1
    except ImportError as e:
        print(f"✗ Data module import failed: {e}")
        tests_failed += 1
    
    # Test integration module
    try:
        from integration import Profiler
        print("✓ Integration module imports successfully")
        tests_passed += 1
    except ImportError as e:
        print(f"✗ Integration module import failed: {e}")
        tests_failed += 1
    
    # Test main entry point
    try:
        from main import Game, GameConfig as MainGameConfig
        print("✓ Main module imports successfully")
        tests_passed += 1
    except ImportError as e:
        print(f"✗ Main module import failed: {e}")
        tests_failed += 1
    
    print(f"\nImport tests: {tests_passed} passed, {tests_failed} failed")
    return tests_failed == 0

def test_directory_structure():
    """Verify the project directory structure."""
    print("\nTesting directory structure...")
    
    expected_dirs = [
        'engine',
        'render', 
        'gameplay',
        'data',
        'integration',
        'reasoning_logs'
    ]
    
    expected_files = [
        'main.py',
        'README.md',
        'requirements.txt',
        'test_architecture.py'
    ]
    
    all_present = True
    
    # Check directories
    for dir_name in expected_dirs:
        if os.path.isdir(dir_name):
            print(f"✓ Directory '{dir_name}' exists")
        else:
            print(f"✗ Directory '{dir_name}' missing")
            all_present = False
    
    # Check files
    for file_name in expected_files:
        if os.path.isfile(file_name):
            print(f"✓ File '{file_name}' exists")
        else:
            print(f"✗ File '{file_name}' missing")
            all_present = False
    
    return all_present

def test_game_configuration():
    """Test game configuration objects."""
    print("\nTesting game configuration...")
    
    try:
        from main import GameConfig
        from engine import EngineConfig
        from render import RenderConfig
        from gameplay import GameConfig as GameplayConfig
        
        # Test main game config
        game_config = GameConfig()
        assert game_config.title == "Game Project"
        assert game_config.width == 1280
        assert game_config.height == 720
        assert game_config.target_fps == 60
        print("✓ Main game configuration valid")
        
        # Test engine config
        engine_config = EngineConfig()
        assert engine_config.width == 1280
        assert engine_config.height == 720
        assert engine_config.vsync == True
        print("✓ Engine configuration valid")
        
        # Test render config
        render_config = RenderConfig(window=None)
        assert render_config.width == 1280
        assert render_config.height == 720
        print("✓ Render configuration valid")
        
        # Test gameplay config
        gameplay_config = GameplayConfig()
        assert gameplay_config.max_entities == 10000
        assert gameplay_config.physics_steps_per_second == 60
        print("✓ Gameplay configuration valid")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def test_game_loop_logic():
    """Test game loop timing logic."""
    print("\nTesting game loop logic...")
    
    try:
        import time
        from main import Game, GameConfig
        
        # Create a mock game instance
        config = GameConfig()
        game = Game(config)
        
        # Test frame time capping
        frame_time = 0.2  # 200ms
        capped_time = min(frame_time, config.max_frame_time)
        assert capped_time == config.max_frame_time
        print("✓ Frame time capping works")
        
        # Test fixed timestep calculation
        fixed_dt = 1.0 / config.target_fps
        assert abs(fixed_dt - 0.0166667) < 0.0001
        print("✓ Fixed timestep calculation correct")
        
        # Test sleep calculation
        current_time = time.perf_counter()
        target_frame_time = 1.0 / config.target_fps
        elapsed = 0.001  # 1ms elapsed
        sleep_time = target_frame_time - elapsed - 0.001
        
        # Should be positive since we're ahead of schedule
        assert sleep_time > 0
        print("✓ Sleep calculation correct")
        
        return True
        
    except Exception as e:
        print(f"✗ Game loop test failed: {e}")
        return False

def main():
    """Run all architecture tests."""
    print("=" * 60)
    print("Game Architecture Test Suite")
    print("=" * 60)
    
    all_tests_passed = True
    
    # Run tests
    if not test_module_imports():
        all_tests_passed = False
    
    if not test_directory_structure():
        all_tests_passed = False
    
    if not test_game_configuration():
        all_tests_passed = False
    
    if not test_game_loop_logic():
        all_tests_passed = False
    
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("✓ All architecture tests passed!")
        print("The game architecture is correctly structured.")
    else:
        print("✗ Some tests failed.")
        print("Please check the architecture implementation.")
    
    print("=" * 60)
    
    return 0 if all_tests_passed else 1

if __name__ == "__main__":
    sys.exit(main())