"""movement.py — Movement and physics components.

exports: Position, Velocity, Acceleration, InputState
used_by: gameplay/systems/movement_system.py, gameplay/systems/player_system.py
rules:   Position required for all movable entities
agent:   GameplayDesigner | 2024-01-15 | Created movement components
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple
import glm
from engine.component import Component


@dataclass
class Position(Component):
    """Spatial position in 3D world.
    
    Attributes:
        x: X coordinate
        y: Y coordinate
        z: Z coordinate
        rotation: Rotation in radians
        scale: Scale factor
    """
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rotation: float = 0.0
    scale: float = 1.0
    
    def to_vec3(self) -> glm.vec3:
        """Convert to glm.vec3.
        
        Returns:
            glm.vec3: Vector representation
        """
        return glm.vec3(self.x, self.y, self.z)
    
    def distance_to(self, other: 'Position') -> float:
        """Calculate distance to another position.
        
        Args:
            other: Other position
            
        Returns:
            float: Distance between positions
        """
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return (dx*dx + dy*dy + dz*dz) ** 0.5


@dataclass
class Velocity(Component):
    """Movement velocity.
    
    Attributes:
        x: X velocity
        y: Y velocity
        z: Z velocity
        max_speed: Maximum speed limit
        friction: Velocity decay factor
    """
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    max_speed: float = 5.0
    friction: float = 0.9
    
    def to_vec3(self) -> glm.vec3:
        """Convert to glm.vec3.
        
        Returns:
            glm.vec3: Vector representation
        """
        return glm.vec3(self.x, self.y, self.z)
    
    def speed(self) -> float:
        """Calculate current speed.
        
        Returns:
            float: Current speed magnitude
        """
        return (self.x*self.x + self.y*self.y + self.z*self.z) ** 0.5


@dataclass
class Acceleration(Component):
    """Movement acceleration.
    
    Attributes:
        x: X acceleration
        y: Y acceleration
        z: Z acceleration
        max_acceleration: Maximum acceleration
    """
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    max_acceleration: float = 10.0


@dataclass
class InputState(Component):
    """Player input state for movement.
    
    Attributes:
        move_forward: W/Up arrow key state
        move_backward: S/Down arrow key state
        move_left: A/Left arrow key state
        move_right: D/Right arrow key state
        jump: Space key state
        sprint: Shift key state
        crouch: Ctrl key state
        last_input_time: Time of last input
    """
    move_forward: bool = False
    move_backward: bool = False
    move_left: bool = False
    move_right: bool = False
    jump: bool = False
    sprint: bool = False
    crouch: bool = False
    last_input_time: float = 0.0
    
    def get_movement_vector(self) -> Tuple[float, float]:
        """Get normalized movement direction from input.
        
        Returns:
            Tuple[float, float]: (x, y) movement direction
        """
        x = 0.0
        y = 0.0
        
        if self.move_forward:
            y += 1.0
        if self.move_backward:
            y -= 1.0
        if self.move_left:
            x -= 1.0
        if self.move_right:
            x += 1.0
        
        # Normalize diagonal movement
        if x != 0.0 and y != 0.0:
            length = (x*x + y*y) ** 0.5
            x /= length
            y /= length
            
        return x, y