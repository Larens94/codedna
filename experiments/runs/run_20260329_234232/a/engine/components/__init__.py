"""__init__.py - Example components for ECS demonstration.

exports: Position, Velocity, PlayerInput, Sprite, Transform components
used_by: Example systems, gameplay integration
rules:   All components must be dataclasses, data-only
agent:   GameEngineer | 2024-1-15 | Created example components for ECS demo
"""

from dataclasses import dataclass, field
from typing import Tuple, Optional
from ..component import Component


@dataclass
class Position(Component):
    """Position component for 2D/3D coordinates.
    
    Rules: Uses meters for physics, pixels for rendering (conversion needed).
    """
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    def __add__(self, other: 'Position') -> 'Position':
        """Add two positions."""
        return Position(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __sub__(self, other: 'Position') -> 'Position':
        """Subtract two positions."""
        return Position(self.x - other.x, self.y - other.y, self.z - other.z)
    
    def distance_to(self, other: 'Position') -> float:
        """Calculate distance to another position."""
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return (dx*dx + dy*dy + dz*dz) ** 0.5
    
    def as_tuple(self) -> Tuple[float, float, float]:
        """Convert to tuple."""
        return (self.x, self.y, self.z)


@dataclass
class Velocity(Component):
    """Velocity component for movement.
    
    Rules: Meters per second for physics.
    """
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    def magnitude(self) -> float:
        """Calculate velocity magnitude."""
        return (self.x*self.x + self.y*self.y + self.z*self.z) ** 0.5
    
    def normalize(self) -> 'Velocity':
        """Return normalized velocity (unit vector)."""
        mag = self.magnitude()
        if mag == 0:
            return Velocity(0, 0, 0)
        return Velocity(self.x/mag, self.y/mag, self.z/mag)
    
    def scale(self, factor: float) -> 'Velocity':
        """Scale velocity by factor."""
        return Velocity(self.x * factor, self.y * factor, self.z * factor)


@dataclass
class PlayerInput(Component):
    """Player input component for controllable entities.
    
    Rules: Updated by input system, read by movement system.
    """
    move_x: float = 0.0  # -1 to 1 for left/right
    move_y: float = 0.0  # -1 to 1 for up/down
    jump: bool = False
    action: bool = False
    sprint: bool = False
    
    def is_moving(self) -> bool:
        """Check if player is trying to move."""
        return abs(self.move_x) > 0.1 or abs(self.move_y) > 0.1


@dataclass
class Sprite(Component):
    """Sprite component for 2D rendering.
    
    Rules: Texture name references asset manager.
    """
    texture: str = ""
    width: float = 1.0
    height: float = 1.0
    color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)  # RGBA
    visible: bool = True
    
    def get_size(self) -> Tuple[float, float]:
        """Get sprite dimensions."""
        return (self.width, self.height)


@dataclass
class Transform(Component):
    """Transform component for hierarchical transformations.
    
    Rules: Combines position, rotation, scale for rendering.
    """
    position: Position = field(default_factory=Position)
    rotation: float = 0.0  # Degrees
    scale_x: float = 1.0
    scale_y: float = 1.0
    scale_z: float = 1.0
    parent: Optional[int] = None  # Entity ID of parent
    
    def get_world_position(self, world) -> Position:
        """Calculate world position considering parent transform."""
        if self.parent is None:
            return self.position
        
        # Get parent transform
        parent_entity = world.get_entity(self.parent)
        if not parent_entity:
            return self.position
            
        parent_transform = parent_entity.get_component(Transform)
        if not parent_transform:
            return self.position
            
        # Recursively get parent world position
        parent_world_pos = parent_transform.get_world_position(world)
        return parent_world_pos + self.position


__all__ = ['Position', 'Velocity', 'PlayerInput', 'Sprite', 'Transform']