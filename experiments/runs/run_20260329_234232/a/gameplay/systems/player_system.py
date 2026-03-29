"""player_system.py — Handles player input and character control.

exports: PlayerSystem class
used_by: gameplay/main.py → Game._initialize_gameplay
rules:   Processes keyboard input for player movement
agent:   GameplayDesigner | 2024-01-15 | Created player system
"""

import glfw
from typing import Set, Type, Optional
from engine.system import System
from engine.component import Component
from gameplay.components.player import Player
from gameplay.components.movement import InputState, Position, Velocity, Acceleration


class PlayerSystem(System):
    """System for processing player input and controlling player character.
    
    Rules:
    - Reads keyboard state for WASD/arrow keys
    - Updates InputState component
    - Converts input to movement acceleration
    - Handles player-specific actions
    """
    
    def __init__(self, window):
        """Initialize player system with GLFW window.
        
        Args:
            window: GLFW window for input polling
        """
        required_components: Set[Type[Component]] = {Player, InputState}
        super().__init__(required_components)
        self._window = window
        self._move_speed = 5.0
        self._sprint_multiplier = 2.0
        self._jump_force = 8.0
        
    def update(self, world, delta_time: float) -> None:
        """Process player input and update player state.
        
        Args:
            world: World to operate on
            delta_time: Time since last update
        """
        entities = self.query_entities(world)
        
        for entity in entities:
            input_state = entity.get_component(InputState)
            velocity = entity.get_component(Velocity)
            acceleration = entity.get_component(Acceleration)
            
            if not acceleration:
                # Add Acceleration component if missing
                acceleration = Acceleration()
                entity.add_component(acceleration)
            
            # Reset acceleration
            acceleration.x = 0.0
            acceleration.y = 0.0
            acceleration.z = 0.0
            
            # Read keyboard state
            input_state.move_forward = (
                glfw.get_key(self._window, glfw.KEY_W) == glfw.PRESS or
                glfw.get_key(self._window, glfw.KEY_UP) == glfw.PRESS
            )
            
            input_state.move_backward = (
                glfw.get_key(self._window, glfw.KEY_S) == glfw.PRESS or
                glfw.get_key(self._window, glfw.KEY_DOWN) == glfw.PRESS
            )
            
            input_state.move_left = (
                glfw.get_key(self._window, glfw.KEY_A) == glfw.PRESS or
                glfw.get_key(self._window, glfw.KEY_LEFT) == glfw.PRESS
            )
            
            input_state.move_right = (
                glfw.get_key(self._window, glfw.KEY_D) == glfw.PRESS or
                glfw.get_key(self._window, glfw.KEY_RIGHT) == glfw.PRESS
            )
            
            input_state.sprint = glfw.get_key(self._window, glfw.KEY_LEFT_SHIFT) == glfw.PRESS
            input_state.jump = glfw.get_key(self._window, glfw.KEY_SPACE) == glfw.PRESS
            input_state.crouch = glfw.get_key(self._window, glfw.KEY_LEFT_CONTROL) == glfw.PRESS
            
            # Convert input to movement
            move_x, move_y = input_state.get_movement_vector()
            
            if move_x != 0.0 or move_y != 0.0:
                # Update input timestamp
                input_state.last_input_time = 0.0  # Would be current time
                
                # Calculate movement speed
                speed = self._move_speed
                if input_state.sprint:
                    speed *= self._sprint_multiplier
                if input_state.crouch:
                    speed *= 0.5
                
                # Set acceleration based on input
                acceleration.x = move_x * speed
                acceleration.y = move_y * speed
                
                # Handle jumping
                if input_state.jump and velocity and velocity.z == 0.0:
                    # Simple jump - would need ground detection in real implementation
                    velocity.z = self._jump_force
    
    def get_player_entity(self, world) -> Optional['Entity']:
        """Get the player entity.
        
        Args:
            world: World to query
            
        Returns:
            Optional[Entity]: Player entity if found
        """
        entities = self.query_entities(world)
        return entities[0] if entities else None
    
    def get_player_position(self, world) -> Optional[Position]:
        """Get player position.
        
        Args:
            world: World to query
            
        Returns:
            Optional[Position]: Player position component if found
        """
        player_entity = self.get_player_entity(world)
        if player_entity:
            return player_entity.get_component(Position)
        return None