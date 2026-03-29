"""camera.py — Camera and viewport management system.

exports: CameraSystem class
used_by: render/main.py → CameraSystem
rules:   Must handle world-to-screen transforms, viewport culling, camera effects
agent:   GraphicsSpecialist | 2024-03-29 | Implemented camera system with effects
"""

import glm
import pygame
from typing import Tuple, Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import math
import random
import logging

logger = logging.getLogger(__name__)


class CameraMode(Enum):
    """Camera movement modes."""
    FOLLOW = "follow"  # Follow target entity
    FREE = "free"      # Free movement
    LOCKED = "locked"  # Locked position
    SHAKE = "shake"    # Shake effect


@dataclass
class CameraShake:
    """Camera shake effect data."""
    intensity: float = 0.0
    duration: float = 0.0
    frequency: float = 10.0
    decay: float = 0.9
    elapsed: float = 0.0
    seed: int = field(default_factory=lambda: random.randint(0, 1000))


class CameraSystem:
    """Camera management system for viewport control and effects.
    
    Features:
    - World-to-screen coordinate transformation
    - Viewport culling for performance
    - Camera effects (shake, zoom, lerp)
    - Multiple camera support
    - Screen bounds checking
    """
    
    def __init__(self, viewport_width: int = 800, viewport_height: int = 600):
        """Initialize camera system.
        
        Args:
            viewport_width: Viewport width in pixels
            viewport_height: Viewport height in pixels
        """
        self._viewport_size = glm.vec2(viewport_width, viewport_height)
        self._position = glm.vec2(0, 0)
        self._target_position = glm.vec2(0, 0)
        self._zoom = 1.0
        self._target_zoom = 1.0
        self._rotation = 0.0
        
        # Camera bounds (optional)
        self._bounds: Optional[Tuple[float, float, float, float]] = None  # min_x, min_y, max_x, max_y
        
        # Camera effects
        self._shake: Optional[CameraShake] = None
        self._lerp_speed = 5.0  # Camera follow speed
        self._zoom_speed = 2.0   # Zoom interpolation speed
        
        # Camera mode
        self._mode = CameraMode.FREE
        self._target_entity: Optional[int] = None  # Entity ID to follow
        
        # Viewport culling
        self._culling_enabled = True
        
        # Transform cache
        self._transform_dirty = True
        self._world_to_screen_matrix = glm.mat3(1.0)
        self._screen_to_world_matrix = glm.mat3(1.0)
    
    def update(self, delta_time: float) -> None:
        """Update camera state.
        
        Args:
            delta_time: Time since last update in seconds
        """
        # Update camera shake
        if self._shake:
            self._update_shake(delta_time)
        
        # Update camera position based on mode
        if self._mode == CameraMode.FOLLOW and self._target_entity is not None:
            # In a real implementation, this would query the entity's position
            # For now, just interpolate to target position
            self._position = glm.mix(self._position, self._target_position, 
                                   self._lerp_speed * delta_time)
        
        elif self._mode == CameraMode.SHAKE and self._shake:
            # Shake mode overrides position
            pass
        
        # Apply bounds
        if self._bounds:
            self._apply_bounds()
        
        # Update zoom interpolation
        if abs(self._zoom - self._target_zoom) > 0.001:
            self._zoom = glm.mix(self._zoom, self._target_zoom, 
                               self._zoom_speed * delta_time)
        
        # Mark transform as dirty
        self._transform_dirty = True
    
    def _update_shake(self, delta_time: float) -> None:
        """Update camera shake effect.
        
        Args:
            delta_time: Time since last update
        """
        if not self._shake:
            return
        
        self._shake.elapsed += delta_time
        
        if self._shake.elapsed >= self._shake.duration:
            self._shake = None
            return
        
        # Calculate current intensity with decay
        progress = self._shake.elapsed / self._shake.duration
        current_intensity = self._shake.intensity * (1.0 - progress) * self._shake.decay
        
        # Generate shake offset using Perlin-like noise
        random.seed(self._shake.seed + int(self._shake.elapsed * self._shake.frequency))
        shake_x = (random.random() * 2 - 1) * current_intensity
        shake_y = (random.random() * 2 - 1) * current_intensity
        
        # Apply shake to position
        self._position.x += shake_x
        self._position.y += shake_y
    
    def _apply_bounds(self) -> None:
        """Apply camera bounds to current position."""
        if not self._bounds:
            return
        
        min_x, min_y, max_x, max_y = self._bounds
        
        # Calculate effective viewport size in world units
        half_viewport_w = (self._viewport_size.x / 2) / self._zoom
        half_viewport_h = (self._viewport_size.y / 2) / self._zoom
        
        # Clamp position to bounds
        self._position.x = max(min_x + half_viewport_w, min(max_x - half_viewport_w, self._position.x))
        self._position.y = max(min_y + half_viewport_h, min(max_y - half_viewport_h, self._position.y))
    
    def _update_transform_matrices(self) -> None:
        """Update world-to-screen and screen-to-world transformation matrices."""
        if not self._transform_dirty:
            return
        
        # Create transformation matrix
        # Order: Scale (zoom) -> Rotate -> Translate
        
        # 1. Scale to viewport center
        center_x = self._viewport_size.x / 2
        center_y = self._viewport_size.y / 2
        
        # 2. Create transformation matrix
        scale = glm.mat3(self._zoom, 0, 0,
                        0, self._zoom, 0,
                        0, 0, 1)
        
        cos_rot = math.cos(math.radians(self._rotation))
        sin_rot = math.sin(math.radians(self._rotation))
        rotate = glm.mat3(cos_rot, -sin_rot, 0,
                         sin_rot, cos_rot, 0,
                         0, 0, 1)
        
        translate = glm.mat3(1, 0, center_x - self._position.x * self._zoom,
                           0, 1, center_y - self._position.y * self._zoom,
                           0, 0, 1)
        
        # Combine: translate * rotate * scale
        self._world_to_screen_matrix = translate * rotate * scale
        
        # Inverse for screen-to-world
        self._screen_to_world_matrix = glm.inverse(self._world_to_screen_matrix)
        
        self._transform_dirty = False
    
    def world_to_screen(self, world_pos: glm.vec2) -> glm.vec2:
        """Convert world coordinates to screen coordinates.
        
        Args:
            world_pos: World position
            
        Returns:
            Screen position
        """
        self._update_transform_matrices()
        
        # Transform point
        result = self._world_to_screen_matrix * glm.vec3(world_pos.x, world_pos.y, 1)
        return glm.vec2(result.x, result.y)
    
    def screen_to_world(self, screen_pos: glm.vec2) -> glm.vec2:
        """Convert screen coordinates to world coordinates.
        
        Args:
            screen_pos: Screen position
            
        Returns:
            World position
        """
        self._update_transform_matrices()
        
        # Transform point
        result = self._screen_to_world_matrix * glm.vec3(screen_pos.x, screen_pos.y, 1)
        return glm.vec2(result.x, result.y)
    
    def is_in_viewport(self, world_pos: glm.vec2, radius: float = 0.0) -> bool:
        """Check if a point is within the viewport.
        
        Args:
            world_pos: World position to check
            radius: Radius around point to consider
            
        Returns:
            True if point is visible in viewport
        """
        screen_pos = self.world_to_screen(world_pos)
        
        # Check if within screen bounds with margin
        margin = radius * self._zoom
        return (-margin <= screen_pos.x <= self._viewport_size.x + margin and
                -margin <= screen_pos.y <= self._viewport_size.y + margin)
    
    def get_viewport_bounds(self) -> Tuple[float, float, float, float]:
        """Get world-space bounds of the viewport.
        
        Returns:
            (min_x, min_y, max_x, max_y) in world coordinates
        """
        # Convert screen corners to world coordinates
        top_left = self.screen_to_world(glm.vec2(0, 0))
        bottom_right = self.screen_to_world(self._viewport_size)
        
        return (top_left.x, top_left.y, bottom_right.x, bottom_right.y)
    
    def set_position(self, x: float, y: float) -> None:
        """Set camera position.
        
        Args:
            x: World X coordinate
            y: World Y coordinate
        """
        self._position = glm.vec2(x, y)
        self._transform_dirty = True
    
    def set_target_position(self, x: float, y: float) -> None:
        """Set target position for interpolation.
        
        Args:
            x: Target world X coordinate
            y: Target world Y coordinate
        """
        self._target_position = glm.vec2(x, y)
    
    def set_zoom(self, zoom: float) -> None:
        """Set camera zoom.
        
        Args:
            zoom: Zoom factor (1.0 = normal)
        """
        self._zoom = max(0.1, min(10.0, zoom))
        self._transform_dirty = True
    
    def set_target_zoom(self, zoom: float) -> None:
        """Set target zoom for interpolation.
        
        Args:
            zoom: Target zoom factor
        """
        self._target_zoom = max(0.1, min(10.0, zoom))
    
    def zoom_to_point(self, point: glm.vec2, zoom: float) -> None:
        """Zoom camera to a specific point.
        
        Args:
            point: World point to zoom toward
            zoom: New zoom factor
        """
        # Convert point to screen space at current zoom
        screen_point = self.world_to_screen(point)
        
        # Set new zoom
        old_zoom = self._zoom
        self.set_zoom(zoom)
        
        # Adjust position so screen_point stays in same screen position
        new_world_point = self.screen_to_world(screen_point)
        offset = point - new_world_point
        self._position += offset
        
        self._transform_dirty = True
    
    def set_rotation(self, degrees: float) -> None:
        """Set camera rotation.
        
        Args:
            degrees: Rotation in degrees
        """
        self._rotation = degrees % 360
        self._transform_dirty = True
    
    def set_bounds(self, min_x: float, min_y: float, max_x: float, max_y: float) -> None:
        """Set camera movement bounds.
        
        Args:
            min_x: Minimum X coordinate
            min_y: Minimum Y coordinate
            max_x: Maximum X coordinate
            max_y: Maximum Y coordinate
        """
        self._bounds = (min_x, min_y, max_x, max_y)
    
    def clear_bounds(self) -> None:
        """Clear camera bounds."""
        self._bounds = None
    
    def shake(self, intensity: float = 5.0, duration: float = 0.5, 
             frequency: float = 10.0, decay: float = 0.9) -> None:
        """Apply camera shake effect.
        
        Args:
            intensity: Shake intensity in pixels
            duration: Shake duration in seconds
            frequency: Shake frequency in Hz
            decay: Intensity decay per frame (0-1)
        """
        self._shake = CameraShake(
            intensity=intensity,
            duration=duration,
            frequency=frequency,
            decay=decay
        )
        self._mode = CameraMode.SHAKE
    
    def set_mode(self, mode: CameraMode) -> None:
        """Set camera mode.
        
        Args:
            mode: Camera mode
        """
        self._mode = mode
        
        if mode != CameraMode.SHAKE and self._shake:
            self._shake = None
    
    def set_target_entity(self, entity_id: Optional[int]) -> None:
        """Set entity to follow.
        
        Args:
            entity_id: Entity ID to follow, or None to stop following
        """
        self._target_entity = entity_id
        if entity_id is not None:
            self._mode = CameraMode.FOLLOW
    
    def set_viewport_size(self, width: int, height: int) -> None:
        """Set viewport size.
        
        Args:
            width: New width in pixels
            height: New height in pixels
        """
        self._viewport_size = glm.vec2(width, height)
        self._transform_dirty = True
    
    def get_position(self) -> Tuple[float, float]:
        """Get camera position.
        
        Returns:
            (x, y) camera position
        """
        return (self._position.x, self._position.y)
    
    def get_zoom(self) -> float:
        """Get camera zoom.
        
        Returns:
            Zoom factor
        """
        return self._zoom
    
    def get_viewport_size(self) -> Tuple[int, int]:
        """Get viewport size.
        
        Returns:
            (width, height) in pixels
        """
        return (int(self._viewport_size.x), int(self._viewport_size.y))
    
    def get_transform_matrix(self) -> glm.mat3:
        """Get world-to-screen transformation matrix.
        
        Returns:
            Transformation matrix
        """
        self._update_transform_matrices()
        return self._world_to_screen_matrix
    
    def enable_culling(self, enabled: bool) -> None:
        """Enable or disable viewport culling.
        
        Args:
            enabled: True to enable culling
        """
        self._culling_enabled = enabled
    
    @property
    def culling_enabled(self) -> bool:
        """Check if culling is enabled."""
        return self._culling_enabled
    
    @property
    def mode(self) -> CameraMode:
        """Get current camera mode."""
        return self._mode