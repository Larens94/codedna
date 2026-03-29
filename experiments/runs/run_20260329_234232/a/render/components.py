"""components.py — ECS components for rendering.

exports: Sprite, Transform, CameraFollow, ParticleEmitter
used_by: engine/world.py → entity component storage
rules:   Components must be data-only, no logic
agent:   GraphicsSpecialist | 2024-03-29 | Created rendering components for ECS
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict, Any
import glm
from enum import Enum


class RenderLayer(Enum):
    """Render layers for z-ordering."""
    BACKGROUND = 0
    TERRAIN = 1
    OBJECTS = 2
    CHARACTERS = 3
    EFFECTS = 4
    UI = 5
    OVERLAY = 6


@dataclass
class Sprite:
    """Sprite rendering component.
    
    Stores data for rendering a 2D sprite.
    """
    texture_path: str = ""  # Path to texture file
    texture_rect: Optional[Tuple[int, int, int, int]] = None  # (x, y, width, height) in texture
    color: Tuple[int, int, int, int] = (255, 255, 255, 255)  # RGBA tint color
    layer: RenderLayer = RenderLayer.OBJECTS
    visible: bool = True
    flip_x: bool = False
    flip_y: bool = False
    blend_mode: int = 0  # Pygame blend mode constant
    
    # Animation properties
    current_frame: int = 0
    frame_time: float = 0.0
    animation_speed: float = 0.0  # Frames per second
    looping: bool = True
    
    # Cached texture (managed by render system)
    _texture: Any = field(default=None, init=False, repr=False)
    _texture_loaded: bool = field(default=False, init=False, repr=False)


@dataclass
class Transform:
    """Transform component for position, rotation, and scale.
    
    Used for both 2D and 3D transformations.
    """
    # Position
    position: glm.vec3 = field(default_factory=lambda: glm.vec3(0, 0, 0))
    
    # Rotation (in degrees)
    rotation: glm.vec3 = field(default_factory=lambda: glm.vec3(0, 0, 0))
    
    # Scale
    scale: glm.vec3 = field(default_factory=lambda: glm.vec3(1, 1, 1))
    
    # Local transform relative to parent
    local_position: glm.vec3 = field(default_factory=lambda: glm.vec3(0, 0, 0))
    local_rotation: glm.vec3 = field(default_factory=lambda: glm.vec3(0, 0, 0))
    local_scale: glm.vec3 = field(default_factory=lambda: glm.vec3(1, 1, 1))
    
    # Hierarchy
    parent: Optional[int] = None  # Entity ID of parent
    children: List[int] = field(default_factory=list)  # Entity IDs of children
    
    # Cached matrices
    _world_matrix: glm.mat4 = field(default_factory=lambda: glm.mat4(1.0), init=False, repr=False)
    _local_matrix: glm.mat4 = field(default_factory=lambda: glm.mat4(1.0), init=False, repr=False)
    _dirty: bool = field(default=True, init=False, repr=False)
    
    def get_position_2d(self) -> Tuple[float, float]:
        """Get 2D position (x, y)."""
        return (self.position.x, self.position.y)
    
    def set_position_2d(self, x: float, y: float) -> None:
        """Set 2D position."""
        self.position.x = x
        self.position.y = y
        self._dirty = True
    
    def move_2d(self, dx: float, dy: float) -> None:
        """Move in 2D space."""
        self.position.x += dx
        self.position.y += dy
        self._dirty = True


@dataclass
class CameraFollow:
    """Component marking an entity as a camera follow target."""
    priority: int = 0  # Higher priority cameras follow this target
    offset: glm.vec2 = field(default_factory=lambda: glm.vec2(0, 0))  # Screen offset
    smoothness: float = 5.0  # Lerp speed (higher = smoother)


@dataclass
class ParticleEmitter:
    """Particle system emitter component."""
    # Emission properties
    emitting: bool = True
    emission_rate: float = 10.0  # Particles per second
    burst_count: int = 0  # One-time burst particles
    
    # Particle properties
    particle_lifetime: Tuple[float, float] = (1.0, 3.0)  # Min, max lifetime
    particle_speed: Tuple[float, float] = (50.0, 150.0)  # Min, max speed
    particle_size: Tuple[float, float] = (4.0, 16.0)  # Min, max size
    particle_color_start: Tuple[int, int, int, int] = (255, 255, 255, 255)
    particle_color_end: Tuple[int, int, int, int] = (255, 255, 255, 0)
    
    # Emission shape
    emission_angle: Tuple[float, float] = (0, 360)  # Min, max angle in degrees
    emission_radius: float = 0.0  # Circular emission radius
    
    # Physics
    gravity: glm.vec2 = field(default_factory=lambda: glm.vec2(0, 98.0))  # Gravity force
    damping: float = 0.99  # Velocity damping per second
    
    # Internal state
    _time_since_emission: float = 0.0
    _particle_count: int = 0
    _max_particles: int = 1000


@dataclass
class UIElement:
    """UI element component."""
    element_type: str = "panel"  # panel, button, label, progress_bar, etc.
    position: Tuple[float, float] = (0, 0)  # Screen position
    size: Tuple[float, float] = (100, 50)  # Width, height
    visible: bool = True
    interactive: bool = False
    
    # Style
    background_color: Tuple[int, int, int, int] = (50, 50, 50, 200)
    border_color: Tuple[int, int, int, int] = (100, 100, 100, 255)
    border_width: int = 2
    
    # Text properties (for labels/buttons)
    text: str = ""
    text_color: Tuple[int, int, int] = (255, 255, 255)
    font_size: int = 24
    text_align: str = "center"  # left, center, right
    
    # Progress bar specific
    progress: float = 0.5  # 0.0 to 1.0
    progress_color: Tuple[int, int, int, int] = (0, 200, 0, 255)
    
    # Event handlers (would be callbacks in a real implementation)
    on_click: Optional[str] = None  # Event name to trigger


@dataclass 
class Light2D:
    """2D light component for dynamic lighting."""
    color: Tuple[int, int, int, int] = (255, 255, 255, 255)
    intensity: float = 1.0
    radius: float = 100.0
    falloff: float = 2.0  # Light falloff exponent
    
    # Light type
    light_type: str = "point"  # point, directional, spotlight
    direction: glm.vec2 = field(default_factory=lambda: glm.vec2(0, -1))  # For directional/spot
    angle: float = 45.0  # For spotlight
    cast_shadows: bool = False