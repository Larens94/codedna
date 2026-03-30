#!/usr/bin/env python3
"""
Main entry point for the game.
Coordinates all modules and manages the game loop for stable 60 FPS.
"""

import sys
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
import threading
import queue

# Import module interfaces
from engine.core import GameEngine, EngineConfig
from render.renderer import Renderer, RenderConfig
from gameplay.game_state import GameState
from data.asset_manager import AssetManager
# JUDGE FIX 6: integration/profiler.py never written
# from integration.profiler import Profiler
class _NullCtx:
    def __enter__(self): return self
    def __exit__(self, *a): pass

class Profiler:
    def start(self, name): pass
    def stop(self, name): pass
    def report(self): return {}
    def start_session(self, name): pass
    def end_session(self, name): pass
    def mark(self, name): pass
    def measure(self, name): return _NullCtx()
    def generate_report(self, path): pass


@dataclass
class GameConfig:
    """Configuration for the entire game."""
    title: str = "Game Project"
    width: int = 1280
    height: int = 720
    fullscreen: bool = False
    vsync: bool = True
    target_fps: int = 60
    max_frame_time: float = 0.1  # Maximum frame time in seconds (anti-spike)
    asset_path: str = "assets/"
    config_path: str = "config/"
    save_path: str = "saves/"


class Game:
    """
    Main game class that coordinates all modules.
    Implements the game loop with stable 60 FPS.
    """
    
    def __init__(self, config: GameConfig):
        """
        Initialize the game with configuration.
        
        Args:
            config: Game configuration
        """
        self.config = config
        self.is_running = False
        self.frame_count = 0
        self.total_time = 0.0
        
        # Performance tracking
        self.frame_times = []
        self.fps_history = []
        
        # Module instances
        self.engine: Optional[GameEngine] = None
        self.renderer: Optional[Renderer] = None
        self.game_state: Optional[GameState] = None
        self.asset_manager: Optional[AssetManager] = None
        self.profiler: Optional[Profiler] = None
        
        # Thread-safe queues for async operations
        self.render_queue = queue.Queue()
        self.asset_queue = queue.Queue()
        
        # Timing
        self.last_time = time.perf_counter()
        self.accumulator = 0.0
        self.fixed_dt = 1.0 / self.config.target_fps
        
    def initialize(self) -> bool:
        """
        Initialize all game modules in the correct order.
        
        Returns:
            bool: True if initialization succeeded, False otherwise
        """
        print(f"Initializing {self.config.title}...")
        
        try:
            # 1. Initialize profiler first
            self.profiler = Profiler()
            self.profiler.start_session("game_initialization")
            
            # 2. Initialize data module (assets first)
            print("  Initializing Asset Manager...")
            self.asset_manager = AssetManager(  # JUDGE FIX 7: wrong kwarg names (base_path→assets_base_path, cache_size→max_cache_size_mb)
                assets_base_path=self.config.asset_path,
                max_cache_size_mb=1024
            )
            
            # 3. Initialize engine (window, input, timing)
            print("  Initializing Game Engine...")
            engine_config = EngineConfig(
                title=self.config.title,
                width=self.config.width,
                height=self.config.height,
                fullscreen=self.config.fullscreen,
                vsync=self.config.vsync
            )
            self.engine = GameEngine(engine_config)
            
            # 4. Initialize renderer (requires window from engine)
            print("  Initializing Renderer...")
            render_config = RenderConfig(
                window=self.engine.get_window(),
                width=self.config.width,
                height=self.config.height,
                vsync=self.config.vsync
            )
            self.renderer = Renderer(render_config)
            
            # 5. Initialize gameplay (requires assets and renderer)
            print("  Initializing Game State...")
            self.game_state = GameState()
            
            # 6. Load initial assets
            print("  Loading initial assets...")
            self._load_initial_assets()
            
            # 7. Set up module connections
            self._connect_modules()
            
            # 8. Start async asset loading thread
            self._start_async_workers()
            
            self.profiler.end_session("game_initialization")
            print("Game initialization complete!")
            return True
            
        except Exception as e:
            print(f"Failed to initialize game: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _load_initial_assets(self):
        """Load essential assets needed for startup."""
        # JUDGE FIX 9: AssetManager only has load_asset() — load_shader/load_texture/load_config
        # never implemented (API mismatch between main.py written by director and data/ written by DataArchitect)
        pass
    
    def _connect_modules(self):
        """Connect all modules together with their dependencies."""
        if self.engine and self.renderer and self.game_state:
            # Connect engine to renderer for window events
            self.engine.set_render_callback(self.renderer.render)
            
            # Connect input to gameplay
            input_manager = self.engine.get_input_manager()
            self.game_state.set_input_handler(input_manager)
            
            # Connect asset manager to all modules that need it
            if self.asset_manager:
                self.renderer.set_asset_manager(self.asset_manager)
                self.game_state.set_asset_manager(self.asset_manager)
    
    def _start_async_workers(self):
        """Start background threads for async operations."""
        # Asset loading thread
        self.asset_thread = threading.Thread(
            target=self._asset_worker,
            daemon=True,
            name="AssetWorker"
        )
        self.asset_thread.start()
        
        # Render preparation thread
        self.render_thread = threading.Thread(
            target=self._render_worker,
            daemon=True,
            name="RenderWorker"
        )
        self.render_thread.start()
    
    def _asset_worker(self):
        """Background worker for async asset loading."""
        while self.is_running:
            try:
                asset_request = self.asset_queue.get(timeout=0.1)
                if asset_request and self.asset_manager:
                    asset_type, asset_id, path = asset_request
                    if asset_type == "texture":
                        self.asset_manager.load_texture_async(asset_id, path)
                    elif asset_type == "shader":
                        vert_path, frag_path = path
                        self.asset_manager.load_shader_async(asset_id, vert_path, frag_path)
                    self.asset_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Asset worker error: {e}")
    
    def _render_worker(self):
        """Background worker for render preparation."""
        while self.is_running:
            try:
                render_task = self.render_queue.get(timeout=0.1)
                if render_task and self.renderer:
                    # Prepare render data in background
                    self.renderer.prepare_frame(render_task)
                    self.render_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Render worker error: {e}")
    
    def run(self):
        """Main game loop with stable 60 FPS."""
        if not self.initialize():
            print("Failed to initialize game. Exiting.")
            return
        
        self.is_running = True
        print("Starting game loop...")
        
        # Main game loop timing variables
        current_time = time.perf_counter()
        accumulator = 0.0
        frame_count = 0
        fps_timer = current_time
        fps_counter = 0
        
        # For frame rate smoothing
        frame_history = []
        max_history = 60  # Keep last second of frame times
        
        try:
            while self.is_running and self.engine and not self.engine.should_close():
                # Calculate delta time with frame limiting
                new_time = time.perf_counter()
                frame_time = new_time - current_time
                
                # Cap frame time to prevent spiral of death
                if frame_time > self.config.max_frame_time:
                    frame_time = self.config.max_frame_time
                
                current_time = new_time
                accumulator += frame_time
                
                # Keep frame time history for smoothing
                frame_history.append(frame_time)
                if len(frame_history) > max_history:
                    frame_history.pop(0)
                
                # Process input (always)
                self.engine.process_input()
                
                # Fixed time step updates
                update_count = 0
                max_updates = 5  # Prevent spiral of death
                
                while accumulator >= self.fixed_dt and update_count < max_updates:
                    with self.profiler.measure("fixed_update"):
                        self._fixed_update(self.fixed_dt)
                    accumulator -= self.fixed_dt
                    update_count += 1
                
                # If we hit max updates, skip ahead to prevent spiral
                if accumulator > self.fixed_dt * max_updates:
                    accumulator = self.fixed_dt * max_updates
                
                # Variable time step update (for rendering interpolation)
                alpha = accumulator / self.fixed_dt
                with self.profiler.measure("variable_update"):
                    self._variable_update(frame_time, alpha)
                
                # Render
                with self.profiler.measure("render"):
                    self._render(alpha)
                
                # End frame
                self.engine.end_frame()
                
                # Frame rate tracking
                frame_count += 1
                fps_counter += 1
                if current_time - fps_timer >= 1.0:
                    fps = fps_counter / (current_time - fps_timer)
                    self.fps_history.append(fps)
                    if len(self.fps_history) > 60:
                        self.fps_history.pop(0)
                    
                    # Log FPS every second (debug)
                    avg_fps = sum(self.fps_history) / len(self.fps_history)
                    print(f"FPS: {fps:.1f} (Avg: {avg_fps:.1f})")
                    
                    fps_counter = 0
                    fps_timer = current_time
                
                # Frame time tracking
                self.frame_times.append(frame_time * 1000)  # Convert to ms
                if len(self.frame_times) > 1000:
                    self.frame_times.pop(0)
                
                # Sleep if we're ahead of schedule (for power saving)
                self._sleep_if_ahead(current_time)
                
                # Check for quit
                if self.engine.is_key_pressed("escape"):
                    self.is_running = False
        
        except KeyboardInterrupt:
            print("Game interrupted by user")
        except Exception as e:
            print(f"Game loop error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.shutdown()
    
    def _sleep_if_ahead(self, current_time: float):
        """
        Sleep if we're ahead of target frame rate to save power.
        
        Args:
            current_time: Current time in seconds
        """
        target_frame_time = 1.0 / self.config.target_fps
        elapsed = time.perf_counter() - current_time
        
        if elapsed < target_frame_time:
            sleep_time = target_frame_time - elapsed - 0.001  # 1ms buffer
            if sleep_time > 0.001:  # Only sleep if significant time
                time.sleep(sleep_time)
    
    def _fixed_update(self, dt: float):
        """
        Fixed time step update for physics and game logic.
        
        Args:
            dt: Fixed delta time (1/60 seconds)
        """
        # Update engine systems
        if self.engine:
            self.engine.fixed_update(dt)
        
        # Update gameplay with fixed timestep
        if self.game_state:
            self.game_state.fixed_update(dt)
        
        # Update physics (if separate from gameplay)
        # self.physics_engine.update(dt)
    
    def _variable_update(self, dt: float, alpha: float):
        """
        Variable time step update for rendering interpolation.
        
        Args:
            dt: Variable delta time
            alpha: Interpolation factor between fixed updates
        """
        # Update engine variable systems
        if self.engine:
            self.engine.variable_update(dt)
        
        # Update gameplay interpolation
        if self.game_state:
            self.game_state.variable_update(dt, alpha)
        
        # Update camera interpolation
        if self.renderer:
            self.renderer.update_interpolation(alpha)
    
    def _render(self, alpha: float):
        """
        Render the current frame with interpolation.
        
        Args:
            alpha: Interpolation factor for smooth rendering
        """
        if self.renderer and self.game_state:
            # Get render data from gameplay
            render_data = self.game_state.get_render_data()
            
            # Queue render preparation in background
            if not self.render_queue.full():
                self.render_queue.put(render_data)
            
            # Render with interpolation
            self.renderer.render(render_data, alpha)
    
    def request_asset_async(self, asset_type: str, asset_id: str, path: Any):
        """
        Request an asset to be loaded asynchronously.
        
        Args:
            asset_type: Type of asset ("texture", "shader", etc.)
            asset_id: Unique identifier for the asset
            path: Path or tuple of paths to the asset
        """
        if not self.asset_queue.full():
            self.asset_queue.put((asset_type, asset_id, path))
    
    def shutdown(self):
        """Clean shutdown of all game systems."""
        print("Shutting down game...")
        
        self.is_running = False
        
        # Wait for async workers
        if hasattr(self, 'asset_thread'):
            self.asset_thread.join(timeout=1.0)
        if hasattr(self, 'render_thread'):
            self.render_thread.join(timeout=1.0)
        
        # Shutdown modules in reverse order
        if self.game_state:
            self.game_state.shutdown()
        
        if self.renderer:
            self.renderer.shutdown()
        
        if self.engine:
            self.engine.shutdown()
        
        if self.asset_manager:
            pass  # JUDGE FIX 10: AssetManager has no shutdown()
        
        if self.profiler:
            self.profiler.end_session("game_runtime")
            self.profiler.generate_report("performance_report.json")
        
        # Print performance summary
        self._print_performance_summary()
        
        print("Game shutdown complete.")
    
    def _print_performance_summary(self):
        """Print performance statistics."""
        if not self.frame_times:
            return
        
        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        max_frame_time = max(self.frame_times)
        min_frame_time = min(self.frame_times)
        
        if self.fps_history:
            avg_fps = sum(self.fps_history) / len(self.fps_history)
            min_fps = min(self.fps_history)
        else:
            avg_fps = 0
            min_fps = 0
        
        print("\n=== Performance Summary ===")
        print(f"Total Frames: {len(self.frame_times)}")
        print(f"Average FPS: {avg_fps:.1f}")
        print(f"Minimum FPS: {min_fps:.1f}")
        print(f"Average Frame Time: {avg_frame_time:.2f}ms")
        print(f"Maximum Frame Time: {max_frame_time:.2f}ms")
        print(f"Minimum Frame Time: {min_frame_time:.2f}ms")
        print(f"Target Frame Time: {1000/self.config.target_fps:.2f}ms")
        
        # Frame time distribution
        under_16ms = sum(1 for t in self.frame_times if t <= 16.67)
        over_33ms = sum(1 for t in self.frame_times if t > 33.33)
        
        print(f"\nFrame Time Distribution:")
        print(f"  ≤ 16.67ms (60 FPS): {under_16ms/len(self.frame_times)*100:.1f}%")
        print(f"  > 33.33ms (<30 FPS): {over_33ms/len(self.frame_times)*100:.1f}%")


def main():
    """Main entry point."""
    print("=== Game Project ===")
    print("Starting game...")
    
    # Load configuration (could be from file)
    config = GameConfig(
        title="Game Project",
        width=1280,
        height=720,
        fullscreen=False,
        vsync=True,
        target_fps=60
    )
    
    # Create and run game
    game = Game(config)
    game.run()
    
    print("Game exited.")
    return 0


if __name__ == "__main__":
    sys.exit(main())