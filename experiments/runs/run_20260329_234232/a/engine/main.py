"""main.py - Engine module entry point with GameEngine class.

exports: GameEngine(), StateMachine(), run_game() -> None
used_by: main.py → GameApplication
rules:   Must maintain 60 FPS fixed timestep, proper state transitions
agent:   GameEngineer | 2024-1-15 | Implemented GameEngine with fixed timestep loop
"""

import time
import logging
from typing import Dict, Any, Optional, Callable
from enum import Enum, auto
from dataclasses import dataclass
from .world import World
from .entity import Entity
from .component import Component
from .system import System

logger = logging.getLogger(__name__)


class GameState(Enum):
    """Game state enumeration."""
    BOOT = auto()
    MENU = auto()
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()
    QUIT = auto()


class StateMachine:
    """Finite state machine for game states.
    
    exports: StateMachine class
    used_by: GameEngine → manage game states
    rules:   States must have enter/update/exit methods, transitions must be defined
    """
    
    def __init__(self):
        """Initialize state machine."""
        self.current_state: Optional[GameState] = None
        self.states: Dict[GameState, Dict[str, Callable]] = {}
        self.transitions: Dict[GameState, Dict[GameState, Callable]] = {}
        
    def add_state(self, state: GameState, 
                  on_enter: Optional[Callable] = None,
                  on_update: Optional[Callable] = None,
                  on_exit: Optional[Callable] = None) -> None:
        """Add a state with optional callbacks.
        
        Args:
            state: State to add
            on_enter: Called when entering state
            on_update: Called each frame while in state
            on_exit: Called when exiting state
        """
        self.states[state] = {
            'enter': on_enter,
            'update': on_update,
            'exit': on_exit
        }
    
    def add_transition(self, from_state: GameState, to_state: GameState,
                      condition: Optional[Callable] = None) -> None:
        """Add a transition between states.
        
        Args:
            from_state: Starting state
            to_state: Target state
            condition: Optional condition function that returns bool
        """
        if from_state not in self.transitions:
            self.transitions[from_state] = {}
        self.transitions[from_state][to_state] = condition
    
    def change_state(self, new_state: GameState) -> bool:
        """Change to a new state.
        
        Args:
            new_state: State to transition to
            
        Returns:
            bool: True if transition successful
            
        Rules: Calls exit on old state, enter on new state.
        """
        if self.current_state == new_state:
            return True
            
        # Check if transition is allowed
        if self.current_state and self.current_state in self.transitions:
            if new_state not in self.transitions[self.current_state]:
                logger.warning(f"Transition from {self.current_state} to {new_state} not allowed")
                return False
                
            # Check condition if exists
            condition = self.transitions[self.current_state][new_state]
            if condition and not condition():
                return False
        
        # Exit current state
        if self.current_state and self.current_state in self.states:
            exit_callback = self.states[self.current_state]['exit']
            if exit_callback:
                try:
                    exit_callback()
                except Exception as e:
                    logger.error(f"Error in state exit callback for {self.current_state}: {e}")
        
        old_state = self.current_state
        self.current_state = new_state
        
        # Enter new state
        if new_state in self.states:
            enter_callback = self.states[new_state]['enter']
            if enter_callback:
                try:
                    enter_callback()
                except Exception as e:
                    logger.error(f"Error in state enter callback for {new_state}: {e}")
        
        logger.info(f"State changed: {old_state} -> {new_state}")
        return True
    
    def update(self) -> None:
        """Update current state.
        
        Rules: Called each frame while game is running.
        """
        if self.current_state and self.current_state in self.states:
            update_callback = self.states[self.current_state]['update']
            if update_callback:
                try:
                    update_callback()
                except Exception as e:
                    logger.error(f"Error in state update callback for {self.current_state}: {e}")


class EventSystem:
    """Decoupled event system for game events.
    
    exports: EventSystem class
    used_by: GameEngine, systems → publish/subscribe to events
    rules:   Events are string-based, subscribers must handle their own errors
    """
    
    def __init__(self):
        """Initialize event system."""
        self.subscribers: Dict[str, list] = {}
        
    def subscribe(self, event_type: str, callback: Callable) -> None:
        """Subscribe to an event type.
        
        Args:
            event_type: Event type to subscribe to
            callback: Function to call when event occurs
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """Unsubscribe from an event type.
        
        Args:
            event_type: Event type to unsubscribe from
            callback: Function to remove
        """
        if event_type in self.subscribers:
            if callback in self.subscribers[event_type]:
                self.subscribers[event_type].remove(callback)
    
    def publish(self, event_type: str, *args, **kwargs) -> None:
        """Publish an event to all subscribers.
        
        Args:
            event_type: Type of event to publish
            *args: Positional arguments for callback
            **kwargs: Keyword arguments for callback
        """
        if event_type in self.subscribers:
            # Copy list to avoid modification during iteration
            for callback in self.subscribers[event_type][:]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in event callback for {event_type}: {e}")
    
    def clear(self) -> None:
        """Clear all subscribers."""
        self.subscribers.clear()


class GameEngine:
    """Main game engine with fixed timestep loop.
    
    exports: GameEngine class
    used_by: main.py → GameApplication
    rules:   Must maintain 60 FPS fixed timestep, proper resource management
    """
    
    def __init__(self):
        """Initialize game engine."""
        self.running = False
        self.target_fps = 60
        self.target_frame_time = 1.0 / self.target_fps
        
        # Core systems
        self.world = World()
        self.state_machine = StateMachine()
        self.event_system = EventSystem()
        
        # Timing
        self._last_time = time.perf_counter()
        self._accumulator = 0.0
        self._frame_count = 0
        self._fps = 0
        self._last_fps_update = self._last_time
        
        # Performance tracking
        self._frame_times = []
        self._max_frame_time_history = 100
        
        # Setup default states
        self._setup_default_states()
    
    def _setup_default_states(self) -> None:
        """Setup default game states."""
        # Boot state
        self.state_machine.add_state(
            GameState.BOOT,
            on_enter=self._on_boot_enter,
            on_update=self._on_boot_update
        )
        
        # Menu state
        self.state_machine.add_state(
            GameState.MENU,
            on_enter=self._on_menu_enter,
            on_update=self._on_menu_update,
            on_exit=self._on_menu_exit
        )
        
        # Playing state
        self.state_machine.add_state(
            GameState.PLAYING,
            on_enter=self._on_playing_enter,
            on_update=self._on_playing_update,
            on_exit=self._on_playing_exit
        )
        
        # Paused state
        self.state_machine.add_state(
            GameState.PAUSED,
            on_enter=self._on_paused_enter,
            on_update=self._on_paused_update,
            on_exit=self._on_paused_exit
        )
        
        # Game over state
        self.state_machine.add_state(
            GameState.GAME_OVER,
            on_enter=self._on_game_over_enter,
            on_update=self._on_game_over_update,
            on_exit=self._on_game_over_exit
        )
        
        # Quit state
        self.state_machine.add_state(
            GameState.QUIT,
            on_enter=self._on_quit_enter
        )
        
        # Define transitions
        self.state_machine.add_transition(GameState.BOOT, GameState.MENU)
        self.state_machine.add_transition(GameState.MENU, GameState.PLAYING)
        self.state_machine.add_transition(GameState.PLAYING, GameState.PAUSED)
        self.state_machine.add_transition(GameState.PLAYING, GameState.GAME_OVER)
        self.state_machine.add_transition(GameState.PAUSED, GameState.PLAYING)
        self.state_machine.add_transition(GameState.PAUSED, GameState.MENU)
        self.state_machine.add_transition(GameState.GAME_OVER, GameState.MENU)
        
        # All states can transition to QUIT
        for state in GameState:
            if state != GameState.QUIT:
                self.state_machine.add_transition(state, GameState.QUIT)
        
        # Start in BOOT state
        self.state_machine.change_state(GameState.BOOT)
    
    def _on_boot_enter(self) -> None:
        """Boot state enter callback."""
        logger.info("Game engine booting...")
        
    def _on_boot_update(self) -> None:
        """Boot state update callback."""
        # After boot, go to menu
        self.state_machine.change_state(GameState.MENU)
    
    def _on_menu_enter(self) -> None:
        """Menu state enter callback."""
        logger.info("Entering menu state")
        self.event_system.publish("menu_entered")
    
    def _on_menu_update(self) -> None:
        """Menu state update callback."""
        # Menu logic would go here
        pass
    
    def _on_menu_exit(self) -> None:
        """Menu state exit callback."""
        logger.info("Exiting menu state")
        self.event_system.publish("menu_exited")
    
    def _on_playing_enter(self) -> None:
        """Playing state enter callback."""
        logger.info("Entering playing state")
        self.event_system.publish("playing_entered")
    
    def _on_playing_update(self) -> None:
        """Playing state update callback."""
        # Game logic happens in world.update()
        pass
    
    def _on_playing_exit(self) -> None:
        """Playing state exit callback."""
        logger.info("Exiting playing state")
        self.event_system.publish("playing_exited")
    
    def _on_paused_enter(self) -> None:
        """Paused state enter callback."""
        logger.info("Entering paused state")
        self.event_system.publish("paused_entered")
    
    def _on_paused_update(self) -> None:
        """Paused state update callback."""
        # Pause logic would go here
        pass
    
    def _on_paused_exit(self) -> None:
        """Paused state exit callback."""
        logger.info("Exiting paused state")
        self.event_system.publish("paused_exited")
    
    def _on_game_over_enter(self) -> None:
        """Game over state enter callback."""
        logger.info("Entering game over state")
        self.event_system.publish("game_over_entered")
    
    def _on_game_over_update(self) -> None:
        """Game over state update callback."""
        # Game over logic would go here
        pass
    
    def _on_game_over_exit(self) -> None:
        """Game over state exit callback."""
        logger.info("Exiting game over state")
        self.event_system.publish("game_over_exited")
    
    def _on_quit_enter(self) -> None:
        """Quit state enter callback."""
        logger.info("Entering quit state")
        self.running = False
        self.event_system.publish("quit_entered")
    
    def start(self) -> None:
        """Start the game engine."""
        if self.running:
            logger.warning("Game engine already running")
            return
        
        self.running = True
        logger.info(f"Game engine started with target FPS: {self.target_fps}")
        
        # Start in BOOT state if not already set
        if not self.state_machine.current_state:
            self.state_machine.change_state(GameState.BOOT)
    
    def stop(self) -> None:
        """Stop the game engine."""
        self.running = False
        logger.info("Game engine stopped")
    
    def update(self) -> bool:
        """Update game engine for one frame.
        
        Returns:
            bool: True if should continue, False if should quit
            
        Rules: Maintains fixed timestep for physics, variable for rendering.
        """
        if not self.running:
            return False
        
        # Calculate delta time
        current_time = time.perf_counter()
        delta_time = current_time - self._last_time
        self._last_time = current_time
        
        # Cap delta time to avoid spiral of death
        if delta_time > 0.25:
            delta_time = 0.25
        
        # Update FPS counter
        self._frame_count += 1
        if current_time - self._last_fps_update >= 1.0:
            self._fps = self._frame_count
            self._frame_count = 0
            self._last_fps_update = current_time
            
            # Log FPS periodically
            if self._fps < self.target_fps * 0.9:  # Below 90% of target
                logger.warning(f"Low FPS: {self._fps}/{self.target_fps}")
        
        # Track frame time for performance monitoring
        self._frame_times.append(delta_time * 1000)  # Convert to ms
        if len(self._frame_times) > self._max_frame_time_history:
            self._frame_times.pop(0)
        
        # Fixed timestep accumulation
        self._accumulator += delta_time
        
        # Update state machine
        self.state_machine.update()
        
        # Execute fixed updates (physics)
        fixed_updates = 0
        while self._accumulator >= self.target_frame_time:
            if self.state_machine.current_state == GameState.PLAYING:
                self.world.update()  # This runs fixed_update on systems
            self._accumulator -= self.target_frame_time
            fixed_updates += 1
            
            # Prevent spiral of death
            if fixed_updates > 5:
                logger.warning(f"Too many fixed updates: {fixed_updates}")
                self._accumulator = 0
                break
        
        # Execute variable updates (rendering, input)
        if self.state_machine.current_state != GameState.PAUSED:
            # Variable updates happen here (rendering systems)
            pass
        
        # Check if we should quit
        return self.state_machine.current_state != GameState.QUIT
    
    def get_fps(self) -> float:
        """Get current FPS.
        
        Returns:
            float: Current frames per second
        """
        return self._fps
    
    def get_frame_time_stats(self) -> Dict[str, float]:
        """Get frame time statistics.
        
        Returns:
            Dict with min, max, avg frame times in ms
        """
        if not self._frame_times:
            return {"min": 0, "max": 0, "avg": 0}
        
        return {
            "min": min(self._frame_times),
            "max": max(self._frame_times),
            "avg": sum(self._frame_times) / len(self._frame_times)
        }
    
    def quit(self) -> None:
        """Request engine to quit."""
        self.state_machine.change_state(GameState.QUIT)


def run_game() -> None:
    """Run the game engine (standalone function).
    
    exports: run_game() -> None
    used_by: Direct execution or testing
    rules:   Must handle initialization and cleanup properly
    """
    logger.info("Starting game engine...")
    
    engine = GameEngine()
    engine.start()
    
    try:
        while engine.update():
            # Sleep to maintain target FPS
            frame_time = time.perf_counter() - engine._last_time
            sleep_time = engine.target_frame_time - frame_time
            
            if sleep_time > 0.001:  # Only sleep if meaningful
                time.sleep(sleep_time)
    
    except KeyboardInterrupt:
        logger.info("Game interrupted by user")
    except Exception as e:
        logger.error(f"Game error: {e}")
    finally:
        engine.stop()
        logger.info("Game engine stopped")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run standalone
    run_game()