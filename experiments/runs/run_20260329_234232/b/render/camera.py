"""
Camera system for 2D RPG.
Handles viewport management, world-to-screen transformations, and camera effects.
"""

import pygame
from typing import Tuple, Optional, List, Dict, Any
from dataclasses import dataclass
import math
import random


@dataclass
class CameraConfig:
    """Configuration for camera behavior."""
    viewport_width: int = 1280
    viewport_height: int = 720
    zoom: float = 1.0
    min_zoom: float = 0.5
    max_zoom: float = 2.0
    zoom_speed: float = 0.1
    smooth_follow: bool = True
    follow_speed: float = 5.0
    bounds: Optional[Tuple[float, float, float, float]] = None  # min_x, min_y, max_x, max_y
    deadzone_radius: float = 100.0  # Radius where camera doesn't follow


class CameraSystem:
    """
    Camera system for 2D games with smooth following, zoom, and effects.
    
    Features:
    - Smooth camera following with deadzone
    - Zoom functionality with limits
    - Screen shake effects
    - World-to-screen coordinate transformations
    - Viewport culling
    """
    
    def __init__(self, config: CameraConfig):
        """
        Initialize the camera system.
        
        Args:
            config: Camera configuration
        """
        self.config = config
        
        # Camera state
        self.position = pygame.Vector2(0, 0)
        self.target_position = pygame.Vector2(0, 0)
        self.target_entity = None
        self.zoom = config.zoom
        self.rotation = 0.0
        
        # Screen shake
        self.shake_intensity = 0.0
        self.shake_duration = 0.0
        self.shake_timer = 0.0
        self.shake_offset = pygame.Vector2(0, 0)
        
        # Interpolation
        self.last_position = pygame.Vector2(0, 0)
        self.render_position = pygame.Vector2(0, 0)
        
        # Viewport
        self.viewport = pygame.Rect(0, 0, config.viewport_width, config.viewport_height)
        self.half_viewport = pygame.Vector2(config.viewport_width // 2, 
                                          config.viewport_height // 2)
        
        # Performance tracking
        self.culled_objects = 0
        self.total_objects = 0
        
    def set_target(self, target_position: Tuple[float, float], 
                  immediate: bool = False):
        """
        Set camera target position.
        
        Args:
            target_position: Target (x, y) position
            immediate: If True, jump to target immediately
        """
        self.target_position = pygame.Vector2(target_position)
        
        if immediate:
            self.position = self.target_position.copy()
    
    def follow_entity(self, entity, immediate: bool = False):
        """
        Set camera to follow an entity.
        
        Args:
            entity: Entity to follow (must have position attribute)
            immediate: If True, jump to entity immediately
        """
        self.target_entity = entity
        
        if immediate and hasattr(entity, 'position'):
            self.position = pygame.Vector2(entity.position)
            self.target_position = self.position.copy()
    
    def update(self, delta_time: float):
        """
        Update camera position and effects.
        
        Args:
            delta_time: Time since last update in seconds
        """
        # Update target position if following entity
        if self.target_entity and hasattr(self.target_entity, 'position'):
            self.target_position = pygame.Vector2(self.target_entity.position)
        
        # Apply smooth following with deadzone
        if self.config.smooth_follow:
            self._update_smooth_follow(delta_time)
        else:
            self.position = self.target_position.copy()
        
        # Apply bounds
        self._apply_bounds()
        
        # Update screen shake
        self._update_screen_shake(delta_time)
        
        # Store last position for interpolation
        self.last_position = self.position.copy()
    
    def _update_smooth_follow(self, delta_time: float):
        """Update smooth camera following with deadzone."""
        # Calculate distance to target
        distance = self.target_position - self.position
        distance_length = distance.length()
        
        # Check if within deadzone
        if distance_length <= self.config.deadzone_radius:
            return
        
        # Normalize and apply follow speed
        if distance_length > 0:
            direction = distance.normalize()
            move_distance = min(distance_length, 
                              self.config.follow_speed * distance_length * delta_time)
            self.position += direction * move_distance
    
    def _apply_bounds(self):
        """Apply camera bounds if configured."""
        if self.config.bounds is None:
            return
        
        min_x, min_y, max_x, max_y = self.config.bounds
        
        # Calculate visible area
        visible_width = self.viewport.width / self.zoom
        visible_height = self.viewport.height / self.zoom
        
        # Apply bounds
        self.position.x = max(min_x + visible_width / 2, 
                            min(max_x - visible_width / 2, self.position.x))
        self.position.y = max(min_y + visible_height / 2, 
                            min(max_y - visible_height / 2, self.position.y))
    
    def _update_screen_shake(self, delta_time: float):
        """Update screen shake effect."""
        if self.shake_timer > 0:
            self.shake_timer -= delta_time
            
            # Calculate shake intensity (decay over time)
            intensity = self.shake_intensity * (self.shake_timer / self.shake_duration)
            
            # Generate random offset
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(0, intensity)
            self.shake_offset = pygame.Vector2(
                math.cos(angle) * distance,
                math.sin(angle) * distance
            )
            
            # Reset when done
            if self.shake_timer <= 0:
                self.shake_offset = pygame.Vector2(0, 0)
                self.shake_intensity = 0
                self.shake_duration = 0
    
    def apply_screen_shake(self, intensity: float, duration: float):
        """
        Apply screen shake effect.
        
        Args:
            intensity: Maximum shake distance in pixels
            duration: Shake duration in seconds
        """
        self.shake_intensity = intensity
        self.shake_duration = duration
        self.shake_timer = duration
    
    def zoom_in(self, amount: Optional[float] = None):
        """
        Zoom camera in.
        
        Args:
            amount: Zoom amount, uses config zoom_speed if None
        """
        if amount is None:
            amount = self.config.zoom_speed
        
        self.zoom = min(self.config.max_zoom, self.zoom + amount)
    
    def zoom_out(self, amount: Optional[float] = None):
        """
        Zoom camera out.
        
        Args:
            amount: Zoom amount, uses config zoom_speed if None
        """
        if amount is None:
            amount = self.config.zoom_speed
        
        self.zoom = max(self.config.min_zoom, self.zoom - amount)
    
    def set_zoom(self, zoom: float):
        """
        Set camera zoom level.
        
        Args:
            zoom: New zoom level (clamped to min/max)
        """
        self.zoom = max(self.config.min_zoom, 
                       min(self.config.max_zoom, zoom))
    
    def world_to_screen(self, world_pos: Tuple[float, float]) -> Tuple[float, float]:
        """
        Convert world coordinates to screen coordinates.
        
        Args:
            world_pos: World (x, y) position
            
        Returns:
            Screen (x, y) position
        """
        # Apply camera position and zoom
        screen_x = (world_pos[0] - self.render_position.x) * self.zoom + self.half_viewport.x
        screen_y = (world_pos[1] - self.render_position.y) * self.zoom + self.half_viewport.y
        
        # Apply screen shake
        screen_x += self.shake_offset.x
        screen_y += self.shake_offset.y
        
        return (screen_x, screen_y)
    
    def screen_to_world(self, screen_pos: Tuple[float, float]) -> Tuple[float, float]:
        """
        Convert screen coordinates to world coordinates.
        
        Args:
            screen_pos: Screen (x, y) position
            
        Returns:
            World (x, y) position
        """
        # Remove screen shake
        screen_x = screen_pos[0] - self.shake_offset.x
        screen_y = screen_pos[1] - self.shake_offset.y
        
        # Apply inverse camera position and zoom
        world_x = (screen_x - self.half_viewport.x) / self.zoom + self.render_position.x
        world_y = (screen_y - self.half_viewport.y) / self.zoom + self.render_position.y
        
        return (world_x, world_y)
    
    def update_interpolation(self, alpha: float):
        """
        Update render position for smooth interpolation.
        
        Args:
            alpha: Interpolation factor between updates (0-1)
        """
        self.render_position = self.last_position.lerp(self.position, alpha)
    
    def is_visible(self, world_pos: Tuple[float, float], 
                  radius: float = 0) -> bool:
        """
        Check if a point is visible in the camera viewport.
        
        Args:
            world_pos: World (x, y) position to check
            radius: Radius around point to consider
            
        Returns:
            True if visible, False otherwise
        """
        screen_pos = self.world_to_screen(world_pos)
        
        # Check if within viewport with margin
        margin = radius * self.zoom
        return (screen_pos[0] + margin >= 0 and 
                screen_pos[0] - margin <= self.viewport.width and
                screen_pos[1] + margin >= 0 and 
                screen_pos[1] - margin <= self.viewport.height)
    
    def get_visible_rect(self) -> pygame.Rect:
        """
        Get the visible world area as a rectangle.
        
        Returns:
            pygame.Rect of visible world area
        """
        visible_width = self.viewport.width / self.zoom
        visible_height = self.viewport.height / self.zoom
        
        return pygame.Rect(
            self.render_position.x - visible_width / 2,
            self.render_position.y - visible_height / 2,
            visible_width,
            visible_height
        )
    
    def cull_objects(self, objects: List[Any], 
                    get_position_func = None) -> List[Any]:
        """
        Cull objects outside the viewport for performance.
        
        Args:
            objects: List of objects to cull
            get_position_func: Function to get position from object
            
        Returns:
            List of visible objects
        """
        self.total_objects = len(objects)
        visible_objects = []
        visible_rect = self.get_visible_rect()
        
        for obj in objects:
            # Get position from object
            if get_position_func:
                pos = get_position_func(obj)
            elif hasattr(obj, 'position'):
                pos = obj.position
            elif hasattr(obj, 'rect'):
                pos = (obj.rect.centerx, obj.rect.centery)
            else:
                # Assume object is a position tuple
                pos = obj
            
            # Check visibility
            if visible_rect.collidepoint(pos):
                visible_objects.append(obj)
        
        self.culled_objects = self.total_objects - len(visible_objects)
        return visible_objects
    
    def get_view_matrix(self) -> List[float]:
        """
        Get camera view matrix for shaders.
        
        Returns:
            4x4 view matrix as list of floats
        """
        # For 2D, we create a simple orthographic projection
        # that accounts for camera position, zoom, and rotation
        
        # Translation
        tx = -self.render_position.x
        ty = -self.render_position.y
        
        # Scale (zoom)
        sx = self.zoom
        sy = self.zoom
        
        # Rotation (not commonly used in 2D, but available)
        angle = math.radians(self.rotation)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        # 2D transformation matrix (3x3 for 2D)
        # [ cos*a*sx, -sin*a*sx, tx ]
        # [ sin*a*sy,  cos*a*sy, ty ]
        # [ 0,         0,        1  ]
        
        return [
            cos_a * sx, -sin_a * sx, 0, tx,
            sin_a * sy,  cos_a * sy, 0, ty,
            0, 0, 1, 0,
            0, 0, 0, 1
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get camera statistics.
        
        Returns:
            Dictionary with camera metrics
        """
        return {
            'position': (self.position.x, self.position.y),
            'zoom': self.zoom,
            'visible_area': self.get_visible_rect(),
            'culled_objects': self.culled_objects,
            'total_objects': self.total_objects,
            'culling_efficiency': self.culled_objects / max(1, self.total_objects),
            'screen_shake_active': self.shake_timer > 0
        }
    
    def resize_viewport(self, width: int, height: int):
        """
        Handle viewport resize.
        
        Args:
            width: New viewport width
            height: New viewport height
        """
        self.viewport.width = width
        self.viewport.height = height
        self.half_viewport = pygame.Vector2(width // 2, height // 2)