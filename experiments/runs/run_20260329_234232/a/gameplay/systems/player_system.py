"""player_system.py — Handles player input and character control.

exports: PlayerSystem class
used_by: gameplay/main.py → Game._initialize_gameplay
rules:   Processes keyboard input for player movement
agent:   GameplayDesigner | 2024-01-15 | Created player system
"""

import pygame
from typing import Set, Type, Optional
from engine.system import System
from engine.component import Component
from gameplay.components.player import Player
from gameplay.components.movement import InputState, Position, Velocity, Acceleration


class PlayerSystem(System):
    """System for processing player input and controlling player character.

    Rules:
    - Reads keyboard state for WASD/arrow keys via pygame
    - Updates InputState component
    - Converts input to movement acceleration
    """

    def __init__(self, window=None):
        required_components: Set[Type[Component]] = {Player, InputState}
        super().__init__(required_components)
        self._move_speed = 5.0
        self._sprint_multiplier = 2.0
        self._jump_force = 8.0

    def update(self, world, delta_time: float) -> None:
        entities = self.query_entities(world)
        keys = pygame.key.get_pressed()

        for entity in entities:
            input_state = entity.get_component(InputState)
            velocity = entity.get_component(Velocity)
            acceleration = entity.get_component(Acceleration)

            # Reset acceleration
            acceleration.x = 0.0
            acceleration.y = 0.0
            acceleration.z = 0.0

            # Read keyboard state via pygame
            input_state.move_forward  = bool(keys[pygame.K_w] or keys[pygame.K_UP])
            input_state.move_backward = bool(keys[pygame.K_s] or keys[pygame.K_DOWN])
            input_state.move_left     = bool(keys[pygame.K_a] or keys[pygame.K_LEFT])
            input_state.move_right    = bool(keys[pygame.K_d] or keys[pygame.K_RIGHT])
            input_state.sprint        = bool(keys[pygame.K_LSHIFT])
            input_state.jump          = bool(keys[pygame.K_SPACE])
            input_state.crouch        = bool(keys[pygame.K_LCTRL])
            
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