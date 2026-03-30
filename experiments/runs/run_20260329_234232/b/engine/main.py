"""
Main engine module exports and game runner.
"""

from .core import GameEngine, EngineConfig
from .ecs import World, Entity, Component, System, TransformComponent, VelocityComponent, RenderComponent, CollisionComponent
from .input import InputManager, InputAction, Key, InputContext
from .scene import Scene, SceneManager, SceneNode
from .time import TimeManager
from .events import Event, EventManager, EventBus, EventPriority, subscribe_to
# from .physics import PhysicsEngine  # JUDGE FIX 1: physics.py is empty (GameEngineer placeholder)


def run_game(config: EngineConfig):
    """
    Run the game with the given configuration.
    
    Args:
        config: Engine configuration
    """
    engine = GameEngine(config)
    
    try:
        # Initialize subsystems
        engine.input_manager = InputManager()
        engine.time_manager = TimeManager(target_fps=60)
        engine.scene_manager = SceneManager()
        
        # Set up the main game loop
        engine.is_running = True
        engine.start_time = engine.get_time()
        
        print("Game started!")
        
        # Main game loop
        while engine.is_running and not engine.should_close():
            # Calculate delta time
            current_time = engine.get_time()
            dt = current_time - engine.start_time if engine.start_time > 0 else 0.0167
            engine.start_time = current_time
            
            # Process input
            engine.process_input()
            
            # Fixed update (physics)
            engine.fixed_update(1.0 / 60.0)
            
            # Variable update (game logic)
            engine.variable_update(dt)
            
            # Render
            if engine.render_callback:
                engine.render_callback(dt)
            
            # End frame
            engine.end_frame()
            
            # Check for quit
            if engine.is_key_pressed("escape"):
                engine.is_running = False
        
    except KeyboardInterrupt:
        print("Game interrupted by user")
    except Exception as e:
        print(f"Game error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        engine.shutdown()
    
    print("Game ended")


# Convenience function for quick startup
def quick_start(title: str = "Game", width: int = 1280, height: int = 720):
    """
    Quick start function for testing.
    
    Args:
        title: Window title
        width: Window width
        height: Window height
    """
    config = EngineConfig(
        title=title,
        width=width,
        height=height,
        fullscreen=False,
        vsync=True
    )
    
    run_game(config)


if __name__ == "__main__":
    # Run a simple test if executed directly
    quick_start("Engine Test", 800, 600)