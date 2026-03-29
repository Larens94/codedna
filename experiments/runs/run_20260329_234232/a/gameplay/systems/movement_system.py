"""movement_system.py — Handles entity movement and physics.

exports: MovementSystem class
used_by: gameplay/main.py → Game._initialize_gameplay
rules:   Updates Position based on Velocity, applies friction
agent:   GameplayDesigner | 2024-01-15 | Created movement system
"""

import glm
from typing import Set, Type
from engine.system import System
from engine.component import Component
from gameplay.components.movement import Position, Velocity, Acceleration


class MovementSystem(System):
    """System for updating entity positions based on velocity and acceleration.
    
    Rules:
    - Updates Position components based on Velocity
    - Applies friction to Velocity
    - Integrates Acceleration into Velocity
    - Handles basic collision constraints
    """
    
    def __init__(self):
        """Initialize movement system."""
        required_components: Set[Type[Component]] = {Position}
        super().__init__(required_components)
        
    def update(self, world, delta_time: float) -> None:
        """Update entity positions.
        
        Args:
            world: World to operate on
            delta_time: Time since last update
        """
        entities = self.query_entities(world)
        
        for entity in entities:
            position = entity.get_component(Position)
            velocity = entity.get_component(Velocity)
            acceleration = entity.get_component(Acceleration)
            
            if velocity:
                # Apply acceleration if present
                if acceleration:
                    velocity.x += acceleration.x * delta_time
                    velocity.y += acceleration.y * delta_time
                    velocity.z += acceleration.z * delta_time
                    
                    # Clamp acceleration
                    accel_mag = (acceleration.x**2 + acceleration.y**2 + acceleration.z**2) ** 0.5
                    if accel_mag > acceleration.max_acceleration:
                        scale = acceleration.max_acceleration / accel_mag
                        acceleration.x *= scale
                        acceleration.y *= scale
                        acceleration.z *= scale
                
                # Apply friction
                velocity.x *= velocity.friction
                velocity.y *= velocity.friction
                velocity.z *= velocity.friction
                
                # Clamp to max speed
                speed = velocity.speed()
                if speed > velocity.max_speed:
                    scale = velocity.max_speed / speed
                    velocity.x *= scale
                    velocity.y *= scale
                    velocity.z *= scale
                
                # Update position
                position.x += velocity.x * delta_time
                position.y += velocity.y * delta_time
                position.z += velocity.z * delta_time
    
    def fixed_update(self, world, fixed_delta_time: float) -> None:
        """Physics update with fixed timestep.
        
        Args:
            world: World to operate on
            fixed_delta_time: Fixed timestep duration
        """
        # For more accurate physics, use fixed_update
        # This ensures consistent movement regardless of framerate
        self.update(world, fixed_delta_time)