"""
Sprite rendering system for 2D RPG.
Handles loading, managing, and rendering sprites with z-ordering.
"""

import pygame
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import numpy as np


@dataclass
class Sprite:
    """Represents a single sprite with rendering properties."""
    texture_id: str
    position: Tuple[float, float] = (0.0, 0.0)
    scale: Tuple[float, float] = (1.0, 1.0)
    rotation: float = 0.0
    z_index: int = 0
    visible: bool = True
    color: Tuple[int, int, int, int] = (255, 255, 255, 255)
    flip_x: bool = False
    flip_y: bool = False
    source_rect: Optional[pygame.Rect] = None
    
    def __post_init__(self):
        """Initialize internal state."""
        self._texture = None
        self._dirty = True  # Flag for texture reloading


@dataclass
class SpriteBatch:
    """Groups sprites for efficient rendering."""
    texture_id: str
    sprites: List[Sprite] = None
    blend_mode: int = pygame.BLEND_ALPHA_SDL2
    
    def __post_init__(self):
        """Initialize sprite list if not provided."""
        if self.sprites is None:
            self.sprites = []


class SpriteRenderer:
    """
    Main sprite rendering system with z-ordering and batching.
    
    Features:
    - Efficient sprite batching
    - Z-ordering for depth management
    - Texture atlas support
    - Sprite pooling for performance
    """
    
    def __init__(self, screen: pygame.Surface):
        """
        Initialize the sprite renderer.
        
        Args:
            screen: Pygame surface to render to
        """
        self.screen = screen
        self.sprites: Dict[str, Sprite] = {}
        self.sprite_batches: Dict[str, SpriteBatch] = {}
        self.textures: Dict[str, pygame.Surface] = {}
        self.texture_atlases: Dict[str, Dict[str, pygame.Rect]] = {}
        
        # Performance tracking
        self.draw_calls = 0
        self.sprite_count = 0
        self.batch_count = 0
        
        # Rendering state
        self.current_camera = None
        self.clear_color = (0, 0, 0, 255)
        
        # Sprite pool for reuse
        self.sprite_pool: List[Sprite] = []
        self.max_pool_size = 1000
        
    def load_texture(self, texture_id: str, filepath: str) -> bool:
        """
        Load a texture from file.
        
        Args:
            texture_id: Unique identifier for the texture
            filepath: Path to the image file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            texture = pygame.image.load(filepath).convert_alpha()
            self.textures[texture_id] = texture
            print(f"Loaded texture: {texture_id} ({texture.get_width()}x{texture.get_height()})")
            return True
        except Exception as e:
            print(f"Failed to load texture {texture_id}: {e}")
            return False
    
    def create_texture_atlas(self, atlas_id: str, spritesheet: str, 
                            sprite_size: Tuple[int, int], 
                            spacing: int = 0) -> bool:
        """
        Create a texture atlas from a spritesheet.
        
        Args:
            atlas_id: Unique identifier for the atlas
            spritesheet: Path to the spritesheet image
            sprite_size: Size of each sprite (width, height)
            spacing: Pixels between sprites
            
        Returns:
            True if successful, False otherwise
        """
        try:
            sheet = pygame.image.load(spritesheet).convert_alpha()
            sheet_width, sheet_height = sheet.get_size()
            sprite_width, sprite_height = sprite_size
            
            atlas = {}
            sprite_index = 0
            
            for y in range(0, sheet_height, sprite_height + spacing):
                for x in range(0, sheet_width, sprite_width + spacing):
                    if x + sprite_width <= sheet_width and y + sprite_height <= sheet_height:
                        rect = pygame.Rect(x, y, sprite_width, sprite_height)
                        sprite_id = f"{atlas_id}_{sprite_index}"
                        atlas[sprite_id] = rect
                        sprite_index += 1
            
            self.texture_atlases[atlas_id] = {
                'texture': sheet,
                'sprites': atlas
            }
            
            print(f"Created texture atlas {atlas_id} with {sprite_index} sprites")
            return True
            
        except Exception as e:
            print(f"Failed to create texture atlas {atlas_id}: {e}")
            return False
    
    def create_sprite(self, texture_id: str, position: Tuple[float, float] = (0, 0),
                     z_index: int = 0, sprite_id: Optional[str] = None) -> str:
        """
        Create a new sprite.
        
        Args:
            texture_id: Texture or atlas sprite ID
            position: Initial position (x, y)
            z_index: Rendering depth
            sprite_id: Optional custom ID, generated if None
            
        Returns:
            Sprite ID
        """
        # Reuse sprite from pool if available
        if self.sprite_pool:
            sprite = self.sprite_pool.pop()
            sprite.texture_id = texture_id
            sprite.position = position
            sprite.z_index = z_index
            sprite.visible = True
            sprite._dirty = True
        else:
            sprite = Sprite(
                texture_id=texture_id,
                position=position,
                z_index=z_index
            )
        
        # Generate ID if not provided
        if sprite_id is None:
            sprite_id = f"sprite_{len(self.sprites)}"
        
        self.sprites[sprite_id] = sprite
        
        # Add to appropriate batch
        self._add_to_batch(sprite_id, sprite)
        
        return sprite_id
    
    def _add_to_batch(self, sprite_id: str, sprite: Sprite):
        """Add sprite to appropriate batch based on texture."""
        texture_id = sprite.texture_id
        
        # Check if this is an atlas sprite
        for atlas_id, atlas_data in self.texture_atlases.items():
            if texture_id in atlas_data['sprites']:
                texture_id = atlas_id
                break
        
        if texture_id not in self.sprite_batches:
            self.sprite_batches[texture_id] = SpriteBatch(texture_id=texture_id)
        
        self.sprite_batches[texture_id].sprites.append(sprite)
    
    def update_sprite(self, sprite_id: str, **kwargs):
        """
        Update sprite properties.
        
        Args:
            sprite_id: ID of sprite to update
            **kwargs: Properties to update (position, scale, rotation, etc.)
        """
        if sprite_id not in self.sprites:
            return
        
        sprite = self.sprites[sprite_id]
        
        for key, value in kwargs.items():
            if hasattr(sprite, key):
                setattr(sprite, key, value)
                sprite._dirty = True
        
        # Re-sort if z-index changed
        if 'z_index' in kwargs:
            self._resort_batches()
    
    def remove_sprite(self, sprite_id: str):
        """
        Remove a sprite from rendering.
        
        Args:
            sprite_id: ID of sprite to remove
        """
        if sprite_id not in self.sprites:
            return
        
        sprite = self.sprites[sprite_id]
        
        # Remove from batch
        for batch in self.sprite_batches.values():
            if sprite in batch.sprites:
                batch.sprites.remove(sprite)
                break
        
        # Add to pool for reuse
        if len(self.sprite_pool) < self.max_pool_size:
            self.sprite_pool.append(sprite)
        
        del self.sprites[sprite_id]
    
    def _resort_batches(self):
        """Sort sprites within batches by z-index."""
        for batch in self.sprite_batches.values():
            batch.sprites.sort(key=lambda s: s.z_index)
    
    def set_camera(self, camera):
        """
        Set the active camera for rendering.
        
        Args:
            camera: CameraSystem instance
        """
        self.current_camera = camera
    
    def clear(self, color: Optional[Tuple[int, int, int, int]] = None):
        """
        Clear the screen.
        
        Args:
            color: Clear color, uses default if None
        """
        if color is None:
            color = self.clear_color
        
        self.screen.fill(color)
    
    def render(self):
        """
        Render all sprites with batching and z-ordering.
        """
        self.draw_calls = 0
        self.sprite_count = 0
        
        # Sort batches by texture for minimal texture switches
        sorted_batches = sorted(self.sprite_batches.items(), 
                              key=lambda x: x[0])
        
        for texture_id, batch in sorted_batches:
            if not batch.sprites:
                continue
            
            # Get texture
            texture = self._get_texture(texture_id)
            if texture is None:
                continue
            
            # Render all sprites in this batch
            for sprite in batch.sprites:
                if not sprite.visible:
                    continue
                
                self._render_sprite(sprite, texture)
                self.sprite_count += 1
            
            self.draw_calls += 1
            self.batch_count = len(sorted_batches)
    
    def _get_texture(self, texture_id: str) -> Optional[pygame.Surface]:
        """Get texture surface, handling atlas lookups."""
        # Check if it's a regular texture
        if texture_id in self.textures:
            return self.textures[texture_id]
        
        # Check if it's an atlas
        if texture_id in self.texture_atlases:
            return self.texture_atlases[texture_id]['texture']
        
        return None
    
    def _render_sprite(self, sprite: Sprite, texture: pygame.Surface):
        """
        Render a single sprite.
        
        Args:
            sprite: Sprite to render
            texture: Texture surface
        """
        # Get source rectangle (for atlas sprites)
        source_rect = sprite.source_rect
        
        # Check if this is an atlas sprite
        if sprite.texture_id not in self.textures:
            for atlas_id, atlas_data in self.texture_atlases.items():
                if sprite.texture_id in atlas_data['sprites']:
                    source_rect = atlas_data['sprites'][sprite.texture_id]
                    break
        
        # Get sprite image
        if source_rect:
            sprite_image = texture.subsurface(source_rect)
        else:
            sprite_image = texture
        
        # Apply transformations
        if sprite.scale != (1.0, 1.0):
            new_size = (int(sprite_image.get_width() * sprite.scale[0]),
                       int(sprite_image.get_height() * sprite.scale[1]))
            if new_size[0] > 0 and new_size[1] > 0:
                sprite_image = pygame.transform.scale(sprite_image, new_size)
        
        if sprite.rotation != 0:
            sprite_image = pygame.transform.rotate(sprite_image, sprite.rotation)
        
        if sprite.flip_x or sprite.flip_y:
            sprite_image = pygame.transform.flip(sprite_image, 
                                                sprite.flip_x, 
                                                sprite.flip_y)
        
        # Apply color tint
        if sprite.color != (255, 255, 255, 255):
            sprite_image = sprite_image.copy()
            color_array = pygame.surfarray.pixels3d(sprite_image)
            alpha_array = pygame.surfarray.pixels_alpha(sprite_image)
            
            # Apply color tint (simplified - in production, use shaders)
            # This is a placeholder - proper tinting requires more complex logic
            
            # For now, just set the alpha
            if sprite.color[3] != 255:
                alpha_mult = sprite.color[3] / 255.0
                alpha_array[:] = (alpha_array * alpha_mult).astype(np.uint8)
        
        # Calculate screen position
        screen_pos = sprite.position
        if self.current_camera:
            screen_pos = self.current_camera.world_to_screen(sprite.position)
        
        # Get sprite rect for blitting
        sprite_rect = sprite_image.get_rect()
        sprite_rect.center = (int(screen_pos[0]), int(screen_pos[1]))
        
        # Render sprite
        self.screen.blit(sprite_image, sprite_rect, 
                        special_flags=sprite.blend_mode if hasattr(sprite, 'blend_mode') else 0)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get rendering statistics.
        
        Returns:
            Dictionary with performance metrics
        """
        return {
            'sprites_rendered': self.sprite_count,
            'draw_calls': self.draw_calls,
            'batches': self.batch_count,
            'textures_loaded': len(self.textures),
            'sprites_total': len(self.sprites),
            'sprite_pool_size': len(self.sprite_pool)
        }
    
    def cleanup(self):
        """Clean up resources."""
        self.sprites.clear()
        self.sprite_batches.clear()
        self.textures.clear()
        self.texture_atlases.clear()
        self.sprite_pool.clear()
        
        print("SpriteRenderer cleaned up")