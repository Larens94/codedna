# Test file
"""
Input management system.
Handles keyboard, mouse, and gamepad input with action mapping.
"""

from typing import Dict, Set, List, Tuple, Optional, Any, Callable
from enum import Enum, IntFlag
import glfw
import time


class InputAction(Enum):
    """Input actions that can be mapped to physical inputs."""
    MOVE_UP = "move_up"
    MOVE_DOWN = "move_down"
    MOVE_LEFT = "move_left"
    MOVE_RIGHT = "move_right"
    JUMP = "jump"
    ATTACK = "attack"
    INTERACT = "interact"
    PAUSE = "pause"
    MENU_UP = "menu_up"
    MENU_DOWN = "menu_down"
    MENU_SELECT = "menu_select"
    MENU_BACK = "menu_back"


class InputState(IntFlag):
    """Input state flags."""
    NONE = 0
    PRESSED = 1
    RELEASED = 2
    HELD = 4
    JUST_PRESSED = 8  # Pressed this frame
    JUST_RELEASED = 16  # Released this frame


class Key:
    """GLFW key constants for easy reference."""
    # Arrow keys
    UP = glfw.KEY_UP
    DOWN = glfw.KEY_DOWN
    LEFT = glfw.KEY_LEFT
    RIGHT = glfw.KEY_RIGHT
    
    # WASD keys
    W = glfw.KEY_W
    A = glfw.KEY_A
    S = glfw.KEY_S
    D = glfw.KEY_D
    
    # Space and shift
    SPACE = glfw.KEY_SPACE
    LEFT_SHIFT = glfw.KEY_LEFT_SHIFT
    RIGHT_SHIFT = glfw.KEY_RIGHT_SHIFT
    
    # Control keys
    LEFT_CONTROL = glfw.KEY_LEFT_CONTROL
    RIGHT_CONTROL = glfw.KEY_RIGHT_CONTROL
    
    # Alt keys
    LEFT_ALT = glfw.KEY_LEFT_ALT
    RIGHT_ALT = glfw.KEY_RIGHT_ALT
    
    # Function keys
    ESCAPE = glfw.KEY_ESCAPE
    ENTER = glfw.KEY_ENTER
    TAB = glfw.KEY_TAB
    
    # Mouse buttons
    MOUSE_LEFT = glfw.MOUSE_BUTTON_LEFT
    MOUSE_RIGHT = glfw.MOUSE_BUTTON_RIGHT
    MOUSE_MIDDLE = glfw.MOUSE_BUTTON_MIDDLE


class InputContext:
    """Context for input mapping (menu vs gameplay)."""
    
    def __init__(self, name: str):
        """
        Initialize an input context.
        
        Args:
            name: Name of the context
        """
        self.name = name
        self.action_mappings: Dict[InputAction, Set[int]] = {}
        self.enabled = True
    
    def map_action(self, action: InputAction, key: int):
        """
        Map an action to a key.
        
        Args:
            action: The action to map
            key: The key code
        """
        if action not in self.action_mappings:
            self.action_mappings[action] = set()
        self.action_mappings[action].add(key)
    
    def unmap_action(self, action: InputAction, key: int):
        """
        Unmap an action from a key.
        
        Args:
            action: The action to unmap
            key: The key code
        """
        if action in self.action_mappings:
            self.action_mappings[action].discard(key)
    
    def get_keys_for_action(self, action: InputAction) -> Set[int]:
        """
        Get all keys mapped to an action.
        
        Args:
            action: The action to get keys for
            
        Returns:
            Set of key codes
        """
        return self.action_mappings.get(action, set())
    
    def is_action_mapped(self, action: InputAction, key: int) -> bool:
        """
        Check if a key is mapped to an action.
        
        Args:
            action: The action to check
            key: The key code
            
        Returns:
            True if the key is mapped to the action
        """
        return key in self.action_mappings.get(action, set())


class InputManager:
    """
    Manages input from keyboard, mouse, and gamepad.
    Supports action mapping and input contexts.
    """
    
    def __init__(self):
        """Initialize the input manager."""
        # Current input state
        self.key_states: Dict[int, InputState] = {}
        self.mouse_button_states: Dict[int, InputState] = {}
        self.mouse_position: Tuple[float, float] = (0.0, 0.0)
        self.mouse_delta: Tuple[float, float] = (0.0, 0.0)
        self.mouse_scroll: Tuple[float, float] = (0.0, 0.0)
        
        # Previous frame state for detecting changes
        self.prev_key_states: Dict[int, bool] = {}
        self.prev_mouse_button_states: Dict[int, bool] = {}
        
        # Input contexts
        self.contexts: Dict[str, InputContext] = {}
        self.active_contexts: List[str] = []
        
        # Input buffering
        self.input_buffer: List[Tuple[InputAction, float]] = []  # (action, timestamp)
        self.buffer_duration: float = 0.3  # seconds
        
        # Default context setup
        self._setup_default_contexts()
    
    def _setup_default_contexts(self):
        """Set up default input contexts."""
        # Gameplay context
        gameplay = InputContext("gameplay")
        gameplay.map_action(InputAction.MOVE_UP, Key.W)
        gameplay.map_action(InputAction.MOVE_UP, Key.UP)
        gameplay.map_action(InputAction.MOVE_DOWN, Key.S)
        gameplay.map_action(InputAction.MOVE_DOWN, Key.DOWN)
        gameplay.map_action(InputAction.MOVE_LEFT, Key.A)
        gameplay.map_action(InputAction.MOVE_LEFT, Key.LEFT)
        gameplay.map_action(InputAction.MOVE_RIGHT, Key.D)
        gameplay.map_action(InputAction.MOVE_RIGHT, Key.RIGHT)
        gameplay.map_action(InputAction.JUMP, Key.SPACE)
        gameplay.map_action(InputAction.ATTACK, Key.MOUSE_LEFT)
        gameplay.map_action(InputAction.INTERACT, Key.E)
        gameplay.map_action(InputAction.PAUSE, Key.ESCAPE)
        
        # Menu context
        menu = InputContext("menu")
        menu.map_action(InputAction.MENU_UP, Key.UP)
        menu.map_action(InputAction.MENU_UP, Key.W)
        menu.map_action(InputAction.MENU_DOWN, Key.DOWN)
        menu.map_action(InputAction.MENU_DOWN, Key.S)
        menu.map_action(InputAction.MENU_SELECT, Key.ENTER)
        menu.map_action(InputAction.MENU_SELECT, Key.SPACE)
        menu.map_action(InputAction.MENU_BACK, Key.ESCAPE)
        menu.map_action(InputAction.MENU_BACK, Key.BACKSPACE)
        
        self.add_context(gameplay)
        self.add_context(menu)
        
        # Start with gameplay context active
        self.activate_context("gameplay")
    
    def add_context(self, context: InputContext):
        """
        Add an input context.
        
        Args:
            context: The context to add
        """
        self.contexts[context.name] = context
    
    def remove_context(self, context_name: str):
        """
        Remove an input context.
        
        Args:
            context_name: Name of the context to remove
        """
        if context_name in self.contexts:
            del self.contexts[context_name]
            if context_name in self.active_contexts:
                self.active_contexts.remove(context_name)
    
    def activate_context(self, context_name: str):
        """
        Activate an input context.
        
        Args:
            context_name: Name of the context to activate
        """
        if context_name in self.contexts and context_name not in self.active_contexts:
            self.active_contexts.append(context_name)
    
    def deactivate_context(self, context_name: str):
        """
        Deactivate an input context.
        
        Args:
            context_name: Name of the context to deactivate
        """
        if context_name in self.active_contexts:
            self.active_contexts.remove(context_name)
    
    def handle_key_event(self, key: int, scancode: int, action: int, mods: int):
        """
        Handle a keyboard event from GLFW.
        
        Args:
            key: GLFW key code
            scancode: System-specific scancode
            action: GLFW action (PRESS, RELEASE, REPEAT)
            mods: Modifier keys
        """
        if action == glfw.PRESS:
            self.key_states[key] = InputState.PRESSED | InputState.JUST_PRESSED
        elif action == glfw.RELEASE:
            self.key_states[key] = InputState.RELEASED | InputState.JUST_RELEASED
        elif action == glfw.REPEAT:
            self.key_states[key] = InputState.HELD
    
    def handle_mouse_button(self, button: int, action: int, mods: int):
        """
        Handle a mouse button event from GLFW.
        
        Args:
            button: GLFW mouse button
            action: GLFW action (PRESS, RELEASE)
            mods: Modifier keys
        """
        if action == glfw.PRESS:
            self.mouse_button_states[button] = InputState.PRESSED | InputState.JUST_PRESSED
        elif action == glfw.RELEASE:
            self.mouse_button_states[button] = InputState.RELEASED | InputState.JUST_RELEASED
    
    def handle_mouse_move(self, xpos: float, ypos: float):
        """
        Handle mouse movement.
        
        Args:
            xpos: X position
            ypos: Y position
        """
        old_x, old_y = self.mouse_position
        self.mouse_delta = (xpos - old_x, ypos - old_y)
        self.mouse_position = (xpos, ypos)
    
    def handle_mouse_scroll(self, xoffset: float, yoffset: float):
        """
        Handle mouse scroll.
        
        Args:
            xoffset: Horizontal scroll offset
            yoffset: Vertical scroll offset
        """
        self.mouse_scroll = (xoffset, yoffset)
    
    def update(self):
        """Update input state for the current frame."""
        current_time = time.time()
        
        # Clear just pressed/released flags
        for key in list(self.key_states.keys()):
            state = self.key_states[key]
            if state & InputState.JUST_PRESSED:
                self.key_states[key] = InputState.PRESSED
            elif state & InputState.JUST_RELEASED:
                self.key_states[key] = InputState.RELEASED
        
        for button in list(self.mouse_button_states.keys()):
            state = self.mouse_button_states[button]
            if state & InputState.JUST_PRESSED:
                self.mouse_button_states[button] = InputState.PRESSED
            elif state & InputState.JUST_RELEASED:
                self.mouse_button_states[button] = InputState.RELEASED
        
        # Clear mouse delta and scroll for next frame
        self.mouse_delta = (0.0, 0.0)
        self.mouse_scroll = (0.0, 0.0)
        
        # Clean up input buffer
        self.input_buffer = [(action, ts) for action, ts in self.input_buffer 
                            if current_time - ts <= self.buffer_duration]
    
    def is_key_pressed(self, key: int) -> bool:
        """
        Check if a key is currently pressed.
        
        Args:
            key: Key code
            
        Returns:
            True if key is pressed
        """
        state = self.key_states.get(key, InputState.NONE)
        return bool(state & (InputState.PRESSED | InputState.HELD))
    
    def is_key_just_pressed(self, key: int) -> bool:
        """
        Check if a key was just pressed this frame.
        
        Args:
            key: Key code
            
        Returns:
            True if key was just pressed
        """
        state = self.key_states.get(key, InputState.NONE)
        return bool(state & InputState.JUST_PRESSED)
    
    def is_key_just_released(self, key: int) -> bool:
        """
        Check if a key was just released this frame.
        
        Args:
            key: Key code
            
        Returns:
            True if key was just released
        """
        state = self.key_states.get(key, InputState.NONE)
        return bool(state & InputState.JUST_RELEASED)
    
    def is_mouse_button_pressed(self, button: int) -> bool:
        """
        Check if a mouse button is currently pressed.
        
        Args:
            button: Mouse button code
            
        Returns:
            True if button is pressed
        """
        state = self.mouse_button_states.get(button, InputState.NONE)
        return bool(state & (InputState.PRESSED | InputState.HELD))
    
    def is_action_triggered(self, action: InputAction) -> bool:
        """
        Check if an action is triggered in any active context.
        
        Args:
            action: The action to check
            
        Returns:
            True if action is triggered
        """
        for context_name in reversed(self.active_contexts):  # Check most recent first
            context = self.contexts.get(context_name)
            if context and context.enabled:
                keys = context.get_keys_for_action(action)
                for key in keys:
                    if self.is_key_pressed(key):
                        # Buffer the input
                        self.input_buffer.append((action, time.time()))
                        return True
        return False
    
    def is_action_just_triggered(self, action: InputAction) -> bool:
        """
        Check if an action was just triggered this frame.
        
        Args:
            action: The action to check
            
        Returns:
            True if action was just triggered
        """
        for context_name in reversed(self.active_contexts):
            context = self.contexts.get(context_name)
            if context and context.enabled:
                keys = context.get_keys_for_action(action)
                for key in keys:
                    if self.is_key_just_pressed(key):
                        return True
        return False
    
    def get_action_value(self, action: InputAction) -> float:
        """
        Get the value of an action (for analog input).
        
        Args:
            action: The action to get value for
            
        Returns:
            Float value (0.0 to 1.0)
        """
        # For digital actions, return 1.0 if triggered
        if self.is_action_triggered(action):
            return 1.0
        return 0.0
    
    def get_mouse_position(self) -> Tuple[float, float]:
        """
        Get current mouse position.
        
        Returns:
            Tuple of (x, y) coordinates
        """
        return self.mouse_position
    
    def get_mouse_delta(self) -> Tuple[float, float]:
        """
        Get mouse movement since last frame.
        
        Returns:
            Tuple of (dx, dy) movement
        """
        return self.mouse_delta
    
    def get_mouse_scroll(self) -> Tuple[float, float]:
        """
        Get mouse scroll since last frame.
        
        Returns:
            Tuple of (x, y) scroll
        """
        return self.mouse_scroll
    
    def get_buffered_actions(self) -> List[InputAction]:
        """
        Get actions in the input buffer.
        
        Returns:
            List of buffered actions
        """
        return [action for action, _ in self.input_buffer]
    
    def clear_buffer(self):
        """Clear the input buffer."""
        self.input_buffer.clear()
    
    def get_vector(self, horizontal_action: InputAction, vertical_action: InputAction) -> Tuple[float, float]:
        """
        Get a 2D vector from two actions.
        
        Args:
            horizontal_action: Action for horizontal axis
            vertical_action: Action for vertical axis
            
        Returns:
            Tuple of (x, y) vector values
        """
        x = 0.0
        y = 0.0
        
        if self.is_action_triggered(horizontal_action):
            # Check which specific keys are pressed for direction
            for context_name in reversed(self.active_contexts):
                context = self.contexts.get(context_name)
                if context and context.enabled:
                    keys = context.get_keys_for_action(horizontal_action)
                    for key in keys:
                        if self.is_key_pressed(key):
                            if key in [Key.D, Key.RIGHT]:
                                x += 1.0
                            elif key in [Key.A, Key.LEFT]:
                                x -= 1.0
        
        if self.is_action_triggered(vertical_action):
            for context_name in reversed(self.active_contexts):
                context = self.contexts.get(context_name)
                if context and context.enabled:
                    keys = context.get_keys_for_action(vertical_action)
                    for key in keys:
                        if self.is_key_pressed(key):
                            if key in [Key.W, Key.UP]:
                                y += 1.0
                            elif key in [Key.S, Key.DOWN]:
                                y -= 1.0
        
        # Normalize if diagonal
        if x != 0.0 and y != 0.0:
            length = (x*x + y*y) ** 0.5
            x /= length
            y /= length
        
        return (x, y)
    
    def shutdown(self):
        """Shutdown the input manager."""
        self.key_states.clear()
        self.mouse_button_states.clear()
        self.contexts.clear()
        self.active_contexts.clear()
        self.input_buffer.clear()