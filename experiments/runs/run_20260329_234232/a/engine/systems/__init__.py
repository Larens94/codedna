"""__init__.py - Example systems for ECS demonstration.

exports: MovementSystem, InputSystem, RenderingSystem, ExampleSystem
used_by: GameEngine, gameplay integration
rules:   Systems must be stateless, query entities each frame
agent:   GameEngineer | 2024-1-15 | Created example systems for ECS demo
"""

import logging
from typing import Set, Type, Optional
from ..system import System
from ..entity import Entity
from ..world import World
from ..components import Position, Velocity, PlayerInput, Sprite, Transform

logger = logging.getLogger(__name__)


class MovementSystem(System):
    """Movement system for entities with Position and Velocity.
    
    Rules: Fixed timestep for physics accuracy.
    """
    
    def __init__(self):
        """Initialize movement system."""
        super().__init__(required_components={Position, Velocity})
        self.max_speed = 10.0  # meters per second
        self.damping = 0.9  # Velocity damping factor
        
    def fixed_update(self, world: World, fixed_delta_time: float) -> None:
        """Update entity positions based on velocity.
        
        Args:
            world: World to operate on
            fixed_delta_time: Fixed timestep duration
        """
        entities = self.query_entities(world)
        
        for entity in entities:
            position = entity.get_component(Position)
            velocity = entity.get_component(Velocity)
            
            if position and velocity:
                # Apply velocity
                position.x += velocity.x * fixed_delta_time
                position.y += velocity.y * fixed_delta_time
                position.z += velocity.z * fixed_delta_time
                
                # Apply damping
                velocity.x *= self.damping
                velocity.y *= self.damping
                velocity.z *= self.damping
                
                # Clamp to max speed
                speed = velocity.magnitude()
                if speed > self.max_speed:
                    velocity.x = (velocity.x / speed) * self.max_speed
                    velocity.y = (velocity.y / speed) * self.max_speed
                    velocity.z = (velocity.z / speed) * self.max_speed


class PlayerMovementSystem(System):
    """Player movement system for entities with PlayerInput, Position, Velocity.
    
    Rules: Converts input to movement, applies acceleration.
    """
    
    def __init__(self):
        """Initialize player movement system."""
        super().__init__(required_components={PlayerInput, Position, Velocity})
        self.acceleration = 20.0  # meters per second squared
        self.max_speed = 5.0  # meters per second
        self.jump_force = 8.0  # meters per second
        
    def fixed_update(self, world: World, fixed_delta_time: float) -> None:
        """Update player movement based on input.
        
        Args:
            world: World to operate on
            fixed_delta_time: Fixed timestep duration
        """
        entities = self.query_entities(world)
        
        for entity in entities:
            input_comp = entity.get_component(PlayerInput)
            position = entity.get_component(Position)
            velocity = entity.get_component(Velocity)
            
            if not all([input_comp, position, velocity]):
                continue
            
            # Apply horizontal movement
            if input_comp.is_moving():
                # Calculate acceleration
                target_velocity_x = input_comp.move_x * self.max_speed
                target_velocity_y = input_comp.move_y * self.max_speed
                
                # Apply acceleration toward target velocity
                accel_x = (target_velocity_x - velocity.x) * self.acceleration * fixed_delta_time
                accel_y = (target_velocity_y - velocity.y) * self.acceleration * fixed_delta_time
                
                velocity.x += accel_x
                velocity.y += accel_y
            else:
                # Apply friction when not moving
                velocity.x *= 0.8
                velocity.y *= 0.8
            
            # Handle jumping
            if input_comp.jump and abs(velocity.z) < 0.1:  # On ground
                velocity.z = self.jump_force
                input_comp.jump = False  # Consume jump input
            
            # Apply gravity
            velocity.z -= 9.8 * fixed_delta_time  # Earth gravity
            
            # Simple ground collision
            if position.z < 0:
                position.z = 0
                velocity.z = max(velocity.z, 0)  # Stop falling through ground


class InputSystem(System):
    """Input system for processing player input.
    
    Rules: Polls input state, updates PlayerInput components.
    """
    
    def __init__(self):
        """Initialize input system."""
        super().__init__(required_components={PlayerInput})
        self.key_state = {}
        
    def initialize(self, world: World) -> None:
        """Initialize with world reference."""
        super().initialize(world)
        # In real implementation, this would set up GLFW callbacks
        logger.info("InputSystem initialized (would connect to GLFW callbacks)")
    
    def update(self, world: World, delta_time: float) -> None:
        """Update input state.
        
        Args:
            world: World to operate on
            delta_time: Time since last update
        """
        # In real implementation, this would poll GLFW
        # For demo, we'll simulate some input
        entities = self.query_entities(world)
        
        for entity in entities:
            input_comp = entity.get_component(PlayerInput)
            if input_comp:
                # Simulate random movement for demo
                import random
                if random.random() < 0.02:  # 2% chance per frame
                    input_comp.move_x = random.uniform(-1, 1)
                    input_comp.move_y = random.uniform(-1, 1)
                if random.random() < 0.01:  # 1% chance per frame
                    input_comp.jump = True
    
    def set_key_state(self, key: str, pressed: bool) -> None:
        """Set key state (called by GLFW callbacks).
        
        Args:
            key: Key identifier
            pressed: True if pressed, False if released
        """
        self.key_state[key] = pressed
        
        # Update all player input components
        if self._world:
            entities = self.query_entities(self._world)
            for entity in entities:
                input_comp = entity.get_component(PlayerInput)
                if input_comp:
                    # Map keys to input
                    if key == 'W' or key == 'UP':
                        input_comp.move_y = 1.0 if pressed else 0.0
                    elif key == 'S' or key == 'DOWN':
                        input_comp.move_y = -1.0 if pressed else 0.0
                    elif key == 'A' or key == 'LEFT':
                        input_comp.move_x = -1.0 if pressed else 0.0
                    elif key == 'D' or key == 'RIGHT':
                        input_comp.move_x = 1.0 if pressed else 0.0
                    elif key == 'SPACE':
                        input_comp.jump = pressed


class RenderingSystem(System):
    """Rendering system for entities with visual components.
    
    Rules: Variable timestep for smooth rendering.
    """
    
    def __init__(self, renderer=None):
        """Initialize rendering system.
        
        Args:
            renderer: Optional renderer instance (for real implementation)
        """
        super().__init__(required_components={Position, Sprite})
        self.renderer = renderer
        self.camera_position = Position(0, 0, 10)  # Camera 10 units back
        self.camera_zoom = 1.0
        
    def update(self, world: World, delta_time: float) -> None:
        """Update rendering.
        
        Args:
            world: World to operate on
            delta_time: Time since last update
        """
        entities = self.query_entities(world)
        
        # In real implementation, this would:
        # 1. Begin render frame
        # 2. Sort entities by depth/z-order
        # 3. Batch render by texture
        # 4. Apply camera transforms
        
        logger.debug(f"RenderingSystem: Would render {len(entities)} entities")
        
        for entity in entities:
            position = entity.get_component(Position)
            sprite = entity.get_component(Sprite)
            
            if position and sprite and sprite.visible:
                # Calculate screen position (simple orthographic projection)
                screen_x = (position.x - self.camera_position.x) * self.camera_zoom
                screen_y = (position.y - self.camera_position.y) * self.camera_zoom
                
                # In real implementation:
                # self.renderer.draw_sprite(sprite.texture, screen_x, screen_y, 
                #                         sprite.width, sprite.height, sprite.color)
                pass


class ExampleSystem(System):
    """Example system demonstrating ECS patterns.
    
    Rules: Shows how to create, query, and process entities.
    """
    
    def __init__(self):
        """Initialize example system."""
        super().__init__(required_components=set())  # No required components
        
    def initialize(self, world: World) -> None:
        """Initialize system and create example entities."""
        super().initialize(world)
        self._create_example_entities(world)
        
    def _create_example_entities(self, world: World) -> None:
        """Create example entities for demonstration."""
        from ..components import Position, Velocity, PlayerInput, Sprite
        
        logger.info("Creating example entities...")
        
        # Create a player entity
        player = world.create_entity()
        player.add_component(Position(x=0, y=0, z=0))
        player.add_component(Velocity(x=0, y=0, z=0))
        player.add_component(PlayerInput())
        player.add_component(Sprite(texture="player.png", width=1, height=1))
        logger.info(f"Created player entity: {player}")
        
        # Create some NPC entities
        for i in range(5):
            npc = world.create_entity()
            npc.add_component(Position(x=i*2-4, y=i-2, z=0))
            npc.add_component(Velocity(x=0.5, y=0, z=0))
            npc.add_component(Sprite(texture=f"npc_{i%3}.png", width=0.8, height=0.8))
            logger.info(f"Created NPC entity {i}: {npc}")
        
        # Create a stationary entity
        stationary = world.create_entity()
        stationary.add_component(Position(x=0, y=5, z=0))
        stationary.add_component(Sprite(texture="tree.png", width=2, height=3))
        logger.info(f"Created stationary entity: {stationary}")
    
    def update(self, world: World, delta_time: float) -> None:
        """Example update showing various queries."""
        # Query all entities with Position
        positioned_entities = world.query_entities({Position})
        logger.debug(f"Entities with Position: {len(positioned_entities)}")
        
        # Query all entities with Sprite
        sprite_entities = world.query_entities({Sprite})
        logger.debug(f"Entities with Sprite: {len(sprite_entities)}")
        
        # Query player entities (Position + PlayerInput)
        player_entities = world.query_entities({Position, PlayerInput})
        logger.debug(f"Player entities: {len(player_entities)}")
        
        # Example: Find entities near position
        center = Position(0, 0, 0)
        for entity in positioned_entities:
            position = entity.get_component(Position)
            if position and position.distance_to(center) < 5.0:
                # Entity is within 5 units of center
                pass


__all__ = ['MovementSystem', 'PlayerMovementSystem', 'InputSystem', 
           'RenderingSystem', 'ExampleSystem']