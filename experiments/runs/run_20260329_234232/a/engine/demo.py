"""demo.py - Engine module demonstration.

exports: run_engine_demo() -> None
used_by: Development demonstration, architecture showcase
rules:   Must demonstrate all engine features working together
agent:   GameEngineer | 2024-1-15 | Created comprehensive engine demo
"""

import logging
import time
from typing import List
from .main import GameEngine, StateMachine, GameState
from .world import World
from .entity import Entity
from .components import Position, Velocity, PlayerInput, Sprite
from .systems import MovementSystem, PlayerMovementSystem, ExampleSystem, InputSystem

logger = logging.getLogger(__name__)


def run_engine_demo() -> None:
    """Run comprehensive engine demonstration."""
    print("\n" + "="*70)
    print("GAME ENGINE DEMONSTRATION")
    print("="*70)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Part 1: ECS Core Demonstration
    print("\n1. ECS CORE ARCHITECTURE")
    print("-"*40)
    _demo_ecs_core()
    
    # Part 2: Game Engine with State Machine
    print("\n2. GAME ENGINE WITH STATE MACHINE")
    print("-"*40)
    _demo_game_engine()
    
    # Part 3: Complete Integration
    print("\n3. COMPLETE ENGINE INTEGRATION")
    print("-"*40)
    _demo_complete_integration()
    
    print("\n" + "="*70)
    print("ENGINE DEMONSTRATION COMPLETE")
    print("="*70)


def _demo_ecs_core() -> None:
    """Demonstrate ECS core features."""
    print("Creating ECS World...")
    world = World()
    
    print("Creating example entities...")
    
    # Create player entity
    player = world.create_entity()
    player.add_component(Position(x=0, y=0, z=0))
    player.add_component(Velocity(x=0.5, y=0.2, z=0))
    player.add_component(PlayerInput())
    player.add_component(Sprite(texture="player.png"))
    
    # Create NPC entities
    npcs: List[Entity] = []
    for i in range(3):
        npc = world.create_entity()
        npc.add_component(Position(x=i*3-3, y=i-1, z=0))
        npc.add_component(Velocity(x=0.3, y=0, z=0))
        npc.add_component(Sprite(texture=f"npc_{i}.png"))
        npcs.append(npc)
    
    print(f"Created {len(npcs) + 1} entities")
    
    # Add systems
    print("Adding systems...")
    movement_system = MovementSystem()
    world.add_system(movement_system)
    
    # Demonstrate queries
    print("\nQuery demonstrations:")
    all_entities = world.query_entities(set())
    positioned = world.query_entities({Position})
    moving = world.query_entities({Position, Velocity})
    players = world.query_entities({PlayerInput})
    
    print(f"  Total entities: {len(all_entities)}")
    print(f"  With Position: {len(positioned)}")
    print(f"  With Position+Velocity: {len(moving)}")
    print(f"  Player entities: {len(players)}")
    
    # Demonstrate component access
    print("\nComponent access:")
    player_pos = player.get_component(Position)
    if player_pos:
        print(f"  Player position: ({player_pos.x:.1f}, {player_pos.y:.1f}, {player_pos.z:.1f})")
    
    # Demonstrate system execution
    print("\nRunning systems for 2 seconds (simulated)...")
    updates = 120  # 2 seconds at 60 FPS
    
    for i in range(updates):
        world.update()
        
        # Show progress every 20 updates
        if i % 20 == 0 and player_pos:
            print(f"  Update {i:3d}: Player at ({player_pos.x:.1f}, {player_pos.y:.1f})")
    
    print("ECS demonstration complete!")


def _demo_game_engine() -> None:
    """Demonstrate game engine with state machine."""
    print("Creating GameEngine...")
    engine = GameEngine()
    
    # Add custom state behavior
    def on_playing_enter_custom():
        print("  >>> Entered PLAYING state (custom callback)")
    
    def on_paused_enter_custom():
        print("  >>> Entered PAUSED state (custom callback)")
    
    # Override default state callbacks
    engine.state_machine.states[GameState.PLAYING]['enter'] = on_playing_enter_custom
    engine.state_machine.states[GameState.PAUSED]['enter'] = on_paused_enter_custom
    
    # Add event subscribers
    def on_state_changed(event_type, from_state, to_state):
        print(f"  Event: {event_type} - {from_state} -> {to_state}")
    
    engine.event_system.subscribe("menu_entered", 
                                 lambda: on_state_changed("menu_entered", None, "MENU"))
    engine.event_system.subscribe("playing_entered",
                                 lambda: on_state_changed("playing_entered", None, "PLAYING"))
    
    print("\nState transitions:")
    
    # Start engine
    engine.start()
    
    # Manually trigger some transitions
    print("  Changing state: BOOT -> MENU")
    engine.state_machine.change_state(GameState.MENU)
    
    print("  Changing state: MENU -> PLAYING")
    engine.state_machine.change_state(GameState.PLAYING)
    
    print("  Changing state: PLAYING -> PAUSED")
    engine.state_machine.change_state(GameState.PAUSED)
    
    print("  Changing state: PAUSED -> PLAYING")
    engine.state_machine.change_state(GameState.PLAYING)
    
    print("  Changing state: PLAYING -> GAME_OVER")
    engine.state_machine.change_state(GameState.GAME_OVER)
    
    print("  Changing state: GAME_OVER -> MENU")
    engine.state_machine.change_state(GameState.MENU)
    
    print("  Requesting quit...")
    engine.quit()
    
    # Run a few updates to process quit state
    for i in range(5):
        engine.update()
        time.sleep(0.01)
    
    print("GameEngine demonstration complete!")


def _demo_complete_integration() -> None:
    """Demonstrate complete engine integration."""
    print("Creating integrated game engine...")
    
    # Create engine with ECS world
    engine = GameEngine()
    
    # Add example system to create entities
    example_system = ExampleSystem()
    engine.world.add_system(example_system, priority=0)
    
    # Add movement system
    movement_system = MovementSystem()
    engine.world.add_system(movement_system, priority=1)
    
    # Add player movement system
    player_movement_system = PlayerMovementSystem()
    engine.world.add_system(player_movement_system, priority=2)
    
    # Start engine
    engine.start()
    engine.state_machine.change_state(GameState.PLAYING)
    
    print("\nRunning integrated simulation for 3 seconds...")
    print("(60 FPS fixed timestep with variable rendering)")
    
    start_time = time.perf_counter()
    frames = 0
    fixed_updates = 0
    
    # Run for 3 seconds
    while time.perf_counter() - start_time < 3.0:
        should_continue = engine.update()
        
        if not should_continue:
            break
        
        frames += 1
        fixed_updates += 1  # Each update includes at least one fixed update
        
        # Show progress every 30 frames (0.5 seconds at 60 FPS)
        if frames % 30 == 0:
            # Query current entity count
            entities = engine.world.query_entities({Position})
            fps = engine.get_fps()
            
            print(f"  Frame {frames:3d}: {len(entities)} entities, FPS: {fps}")
    
    elapsed = time.perf_counter() - start_time
    
    print(f"\nSimulation complete:")
    print(f"  Total frames: {frames}")
    print(f"  Total time: {elapsed:.2f}s")
    print(f"  Average FPS: {frames/elapsed:.1f}")
    
    # Get performance stats
    stats = engine.get_frame_time_stats()
    print(f"  Frame time - Min: {stats['min']:.2f}ms, Max: {stats['max']:.2f}ms, Avg: {stats['avg']:.2f}ms")
    
    # Check if we maintained target FPS
    target_fps = engine.target_fps
    actual_fps = frames / elapsed
    
    if actual_fps >= target_fps * 0.9:  # Within 90% of target
        print(f"  ✓ Maintained target FPS ({actual_fps:.1f}/{target_fps})")
    else:
        print(f"  ✗ Below target FPS ({actual_fps:.1f}/{target_fps})")
    
    # Cleanup
    engine.stop()
    print("Integrated demonstration complete!")


def interactive_demo() -> None:
    """Run interactive engine demonstration."""
    print("\n" + "="*70)
    print("INTERACTIVE ENGINE DEMONSTRATION")
    print("="*70)
    
    engine = GameEngine()
    
    # Setup interactive state
    def print_state():
        if engine.state_machine.current_state:
            print(f"\nCurrent state: {engine.state_machine.current_state.name}")
    
    def print_help():
        print("\nAvailable commands:")
        print("  menu    - Go to menu state")
        print("  play    - Go to playing state")
        print("  pause   - Go to paused state")
        print("  over    - Go to game over state")
        print("  quit    - Quit the engine")
        print("  stats   - Show performance stats")
        print("  help    - Show this help")
        print("  exit    - Exit interactive mode")
    
    # Start engine
    engine.start()
    engine.state_machine.change_state(GameState.MENU)
    
    print("Engine started in MENU state")
    print_help()
    
    # Interactive loop
    while engine.running:
        try:
            cmd = input("\nengine> ").strip().lower()
            
            if cmd == "menu":
                engine.state_machine.change_state(GameState.MENU)
                print_state()
            elif cmd == "play":
                engine.state_machine.change_state(GameState.PLAYING)
                print_state()
            elif cmd == "pause":
                engine.state_machine.change_state(GameState.PAUSED)
                print_state()
            elif cmd == "over":
                engine.state_machine.change_state(GameState.GAME_OVER)
                print_state()
            elif cmd == "quit":
                engine.quit()
                print("Quitting engine...")
            elif cmd == "stats":
                stats = engine.get_frame_time_stats()
                print(f"FPS: {engine.get_fps()}")
                print(f"Frame times - Min: {stats['min']:.2f}ms, Max: {stats['max']:.2f}ms, Avg: {stats['avg']:.2f}ms")
            elif cmd == "help":
                print_help()
            elif cmd == "exit":
                print("Exiting interactive mode...")
                engine.quit()
                break
            else:
                print(f"Unknown command: {cmd}")
                print("Type 'help' for available commands")
            
            # Update engine
            engine.update()
            
        except KeyboardInterrupt:
            print("\nInterrupted by user")
            engine.quit()
            break
        except Exception as e:
            print(f"Error: {e}")
    
    # Cleanup
    engine.stop()
    print("Interactive demonstration complete!")


if __name__ == "__main__":
    print("Choose demonstration mode:")
    print("  1. Full automated demo")
    print("  2. Interactive demo")
    
    try:
        choice = input("Enter choice (1 or 2): ").strip()
        
        if choice == "2":
            interactive_demo()
        else:
            run_engine_demo()
    except KeyboardInterrupt:
        print("\nDemonstration cancelled by user")
    except Exception as e:
        print(f"Error running demonstration: {e}")