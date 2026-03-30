"""
Core engine system.
Manages the main game loop, window, and coordinates all engine subsystems.
"""

import time
from typing import Optional, Callable, Any
from dataclasses import dataclass
import glfw
import sys


@dataclass
class EngineConfig:
    """Configuration for the game engine."""
    title: str = "Game Engine"
    width: int = 1280
    height: int = 720
    fullscreen: bool = False
    vsync: bool = True
    msaa_samples: int = 4
    resizable: bool = True
    debug_mode: bool = False


class GameEngine:
    """
    Main game engine class.
    Manages window, input, timing, and coordinates engine subsystems.
    """
    
    def __init__(self, config: EngineConfig):
        """
        Initialize the game engine.
        
        Args:
            config: Engine configuration
        """
        self.config = config
        self.window = None
        self.is_running = False
        
        # Subsystems
        self.scene_manager = None
        self.input_manager = None
        self.time_manager = None
        
        # Callbacks
        self.render_callback: Optional[Callable[[float], None]] = None
        self.update_callback: Optional[Callable[[float], None]] = None
        
        # Performance tracking
        self.frame_count = 0
        self.start_time = 0.0
        
        # Initialize GLFW and create window
        self._initialize_glfw()
    
    def _initialize_glfw(self):
        """Initialize GLFW and create window."""
        if not glfw.init():
            raise RuntimeError("Failed to initialize GLFW")
        
        # Configure window hints
        glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
        glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
        glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
        glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, True)
        
        if self.config.debug_mode:
            glfw.window_hint(glfw.OPENGL_DEBUG_CONTEXT, True)
        
        if self.config.msaa_samples > 1:
            glfw.window_hint(glfw.SAMPLES, self.config.msaa_samples)
        
        glfw.window_hint(glfw.RESIZABLE, self.config.resizable)
        
        # Create window
        monitor = glfw.get_primary_monitor() if self.config.fullscreen else None
        self.window = glfw.create_window(
            self.config.width,
            self.config.height,
            self.config.title,
            monitor,
            None
        )
        
        if not self.window:
            glfw.terminate()
            raise RuntimeError("Failed to create GLFW window")
        
        # Make context current
        glfw.make_context_current(self.window)
        
        # Set vsync
        glfw.swap_interval(1 if self.config.vsync else 0)
        
        # Set callbacks
        glfw.set_window_size_callback(self.window, self._on_window_resize)
        glfw.set_key_callback(self.window, self._on_key_event)
        glfw.set_mouse_button_callback(self.window, self._on_mouse_button)
        glfw.set_cursor_pos_callback(self.window, self._on_mouse_move)
        glfw.set_scroll_callback(self.window, self._on_mouse_scroll)
        
        print(f"Engine initialized: {self.config.width}x{self.config.height}")
    
    def _on_window_resize(self, window, width, height):
        """Handle window resize events."""
        self.config.width = width
        self.config.height = height
        
        if self.render_callback:
            # Notify renderer of resize
            pass
    
    def _on_key_event(self, window, key, scancode, action, mods):
        """Handle keyboard events."""
        if self.input_manager:
            self.input_manager.handle_key_event(key, scancode, action, mods)
    
    def _on_mouse_button(self, window, button, action, mods):
        """Handle mouse button events."""
        if self.input_manager:
            self.input_manager.handle_mouse_button(button, action, mods)
    
    def _on_mouse_move(self, window, xpos, ypos):
        """Handle mouse movement events."""
        if self.input_manager:
            self.input_manager.handle_mouse_move(xpos, ypos)
    
    def _on_mouse_scroll(self, window, xoffset, yoffset):
        """Handle mouse scroll events."""
        if self.input_manager:
            self.input_manager.handle_mouse_scroll(xoffset, yoffset)
    
    def get_window(self) -> Any:
        """
        Get the GLFW window handle.
        
        Returns:
            The GLFW window object
        """
        return self.window
    
    def get_input_manager(self):
        """
        Get the input manager instance.
        
        Returns:
            InputManager instance
        """
        return self.input_manager
    
    def set_render_callback(self, callback: Callable[[float], None]):
        """
        Set the render callback function.
        
        Args:
            callback: Function to call each frame for rendering
        """
        self.render_callback = callback
    
    def set_update_callback(self, callback: Callable[[float], None]):
        """
        Set the update callback function.
        
        Args:
            callback: Function to call each frame for updating
        """
        self.update_callback = callback
    
    def process_input(self):
        """Process all input events for this frame."""
        glfw.poll_events()
        
        if self.input_manager:
            self.input_manager.update()
    
    def fixed_update(self, dt: float):
        """
        Fixed time step update.
        
        Args:
            dt: Fixed delta time
        """
        if self.scene_manager:
            self.scene_manager.fixed_update(dt)
        
        if self.update_callback:
            self.update_callback(dt)
    
    def variable_update(self, dt: float):
        """
        Variable time step update.
        
        Args:
            dt: Variable delta time
        """
        if self.time_manager:
            self.time_manager.update(dt)
        
        if self.scene_manager:
            self.scene_manager.variable_update(dt)
    
    def end_frame(self):
        """End the current frame and swap buffers."""
        glfw.swap_buffers(self.window)
        self.frame_count += 1
    
    def should_close(self) -> bool:
        """
        Check if the window should close.
        
        Returns:
            True if window should close
        """
        return glfw.window_should_close(self.window)
    
    def is_key_pressed(self, key: str) -> bool:
        """
        Check if a key is currently pressed.
        
        Args:
            key: Key name or code
            
        Returns:
            True if key is pressed
        """
        if self.input_manager:
            return self.input_manager.is_key_pressed(key)
        return False
    
    def get_mouse_position(self) -> tuple[float, float]:
        """
        Get current mouse position.
        
        Returns:
            Tuple of (x, y) mouse coordinates
        """
        if self.input_manager:
            return self.input_manager.get_mouse_position()
        return (0.0, 0.0)
    
    def get_time(self) -> float:
        """
        Get current engine time in seconds.
        
        Returns:
            Current time in seconds
        """
        return glfw.get_time()
    
    def get_frame_count(self) -> int:
        """
        Get total frame count since start.
        
        Returns:
            Frame count
        """
        return self.frame_count
    
    def get_fps(self) -> float:
        """
        Calculate current FPS.
        
        Returns:
            Frames per second
        """
        current_time = self.get_time()
        elapsed = current_time - self.start_time
        
        if elapsed > 0:
            return self.frame_count / elapsed
        return 0.0
    
    def shutdown(self):
        """Shutdown the engine and clean up resources."""
        print("Shutting down engine...")
        
        if self.scene_manager:
            self.scene_manager.shutdown()
        
        if self.input_manager:
            self.input_manager.shutdown()
        
        if self.window:
            glfw.destroy_window(self.window)
        
        glfw.terminate()
        print("Engine shutdown complete.")