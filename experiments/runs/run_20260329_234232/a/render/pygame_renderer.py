"""pygame_renderer.py — Pygame-based 2D sprite renderer.

exports: PygameRenderer class
used_by: render/main.py → SpriteRenderer
rules:   Must maintain 60 FPS, support sprite batching, integrate with ECS
agent:   GraphicsSpecialist | 2024-03-29 | Implemented Pygame renderer with sprite batching
"""

import pygame
import glm
from typing import Dict, List, Tuple, Optional, Set, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


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
class SpriteBatch:
    """Batch of sprites to render together."""
    texture: pygame.Surface
    sprites: List[Tuple[pygame.Rect, pygame.Rect]]  # (dest_rect, source_rect)
    layer: RenderLayer
    blend_mode: int = pygame.BLEND_ALPHA_SDL2


class PygameRenderer:
    """Pygame-based 2D sprite renderer with batching and ECS integration.
    
    Features:
    - Sprite batching for performance
    - Texture caching and management
    - Camera/viewport system
    - Z-ordering with render layers
    - 60 FPS target with vsync
    """
    
    def __init__(self):
        """Initialize renderer (does not create window)."""
        self._initialized = False
        self._window = None
        self._screen = None
        self._clock = None
        self._clear_color = (0, 0, 0, 255)
        
        # Texture cache
        self._texture_cache: Dict[str, pygame.Surface] = {}
        self._texture_refs: Dict[str, int] = {}
        
        # Sprite batching
        self._sprite_batches: Dict[RenderLayer, Dict[str, SpriteBatch]] = {}
        self._current_batches: Dict[RenderLayer, Dict[str, SpriteBatch]] = {}
        
        # Camera
        self._camera_position = glm.vec2(0, 0)
        self._camera_zoom = 1.0
        self._viewport_size = (800, 600)
        
        # Performance tracking
        self._frame_count = 0
        self._fps = 60
        self._target_fps = 60
        
        # Initialize render layers
        for layer in RenderLayer:
            self._sprite_batches[layer] = {}
            self._current_batches[layer] = {}
    
    def initialize(self, title: str = "Game", width: int = 1280, 
                  height: int = 720, fullscreen: bool = False) -> bool:
        """Initialize Pygame and create window.
        
        Args:
            title: Window title
            width: Window width in pixels
            height: Window height in pixels
            fullscreen: Whether to start in fullscreen mode
            
        Returns:
            bool: True if initialization successful
        """
        try:
            # Initialize Pygame
            pygame.init()
            
            # Set up display
            flags = pygame.SCALED | pygame.RESIZABLE
            if fullscreen:
                flags |= pygame.FULLSCREEN
            
            self._window = pygame.display.set_mode((width, height), flags)
            self._screen = self._window
            pygame.display.set_caption(title)
            
            # Create clock for FPS control
            self._clock = pygame.time.Clock()
            
            # Set viewport size
            self._viewport_size = (width, height)
            
            # Initialize font system
            pygame.font.init()
            
            # Create default font
            self._default_font = pygame.font.Font(None, 24)
            
            self._initialized = True
            logger.info(f"Pygame renderer initialized: {width}x{height}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Pygame renderer: {e}")
            self.shutdown()
            return False
    
    def begin_frame(self) -> bool:
        """Begin rendering frame.
        
        Returns:
            bool: True if should continue rendering
            
        Rules: Must be called at start of each frame.
        """
        if not self._initialized:
            return False
        
        # Clear current batches
        for layer in RenderLayer:
            self._current_batches[layer].clear()
        
        # Clear screen
        self._screen.fill(self._clear_color)
        
        return True
    
    def end_frame(self) -> None:
        """End rendering frame and update display.
        
        Rules: Must be called at end of each frame.
        """
        if not self._initialized:
            return
        
        # Render all batches in layer order
        for layer in RenderLayer:
            for batch_key, batch in self._current_batches[layer].items():
                self._render_batch(batch)
        
        # Update display
        pygame.display.flip()
        
        # Maintain FPS
        self._clock.tick(self._target_fps)
        self._frame_count += 1
        
        # Update FPS counter every second
        if self._frame_count % 60 == 0:
            self._fps = self._clock.get_fps()
    
    def load_texture(self, texture_path: str) -> Optional[pygame.Surface]:
        """Load texture from file with caching.
        
        Args:
            texture_path: Path to texture file
            
        Returns:
            pygame.Surface or None if failed
        """
        if texture_path in self._texture_cache:
            self._texture_refs[texture_path] += 1
            return self._texture_cache[texture_path]
        
        try:
            # Load image
            surface = pygame.image.load(texture_path).convert_alpha()
            
            # Cache texture
            self._texture_cache[texture_path] = surface
            self._texture_refs[texture_path] = 1
            
            logger.debug(f"Loaded texture: {texture_path}")
            return surface
            
        except Exception as e:
            logger.error(f"Failed to load texture {texture_path}: {e}")
            return None
    
    def release_texture(self, texture_path: str) -> None:
        """Release reference to texture.
        
        Args:
            texture_path: Path to texture file
        """
        if texture_path in self._texture_refs:
            self._texture_refs[texture_path] -= 1
            
            if self._texture_refs[texture_path] <= 0:
                # Remove from cache
                if texture_path in self._texture_cache:
                    del self._texture_cache[texture_path]
                del self._texture_refs[texture_path]
                logger.debug(f"Released texture: {texture_path}")
    
    def draw_sprite(self, texture: pygame.Surface, 
                   position: Tuple[float, float],
                   source_rect: Optional[pygame.Rect] = None,
                   scale: float = 1.0,
                   rotation: float = 0.0,
                   layer: RenderLayer = RenderLayer.OBJECTS,
                   blend_mode: int = pygame.BLEND_ALPHA_SDL2) -> None:
        """Queue a sprite for rendering.
        
        Args:
            texture: Texture surface to draw
            position: World position (x, y)
            source_rect: Source rectangle in texture (None for entire texture)
            scale: Scale factor
            rotation: Rotation in degrees
            layer: Render layer for z-ordering
            blend_mode: Pygame blend mode
        """
        if not self._initialized:
            return
        
        # Apply camera transform
        screen_pos = self.world_to_screen(position)
        
        # Get texture size
        if source_rect:
            sprite_size = (source_rect.width * scale, source_rect.height * scale)
        else:
            sprite_size = (texture.get_width() * scale, texture.get_height() * scale)
        
        # Create destination rectangle
        dest_rect = pygame.Rect(
            screen_pos[0] - sprite_size[0] / 2,
            screen_pos[1] - sprite_size[1] / 2,
            sprite_size[0],
            sprite_size[1]
        )
        
        # Use texture memory address as batch key
        batch_key = str(texture.get_buffer().raw)
        
        # Get or create batch
        if batch_key not in self._current_batches[layer]:
            self._current_batches[layer][batch_key] = SpriteBatch(
                texture=texture,
                sprites=[],
                layer=layer,
                blend_mode=blend_mode
            )
        
        # Add sprite to batch
        batch = self._current_batches[layer][batch_key]
        batch.sprites.append((dest_rect, source_rect or texture.get_rect()))
    
    def _render_batch(self, batch: SpriteBatch) -> None:
        """Render a sprite batch.
        
        Args:
            batch: SpriteBatch to render
        """
        # Use blits for batch rendering (Pygame 2.0+)
        if hasattr(pygame, 'blits'):
            blit_list = [(batch.texture, dest_rect, src_rect) 
                        for dest_rect, src_rect in batch.sprites]
            self._screen.blits(blit_list, doreturn=False)
        else:
            # Fallback for older Pygame
            for dest_rect, src_rect in batch.sprites:
                self._screen.blit(batch.texture, dest_rect, src_rect)
    
    def world_to_screen(self, world_pos: Tuple[float, float]) -> Tuple[float, float]:
        """Convert world coordinates to screen coordinates.
        
        Args:
            world_pos: World position (x, y)
            
        Returns:
            Screen position (x, y)
        """
        # Apply camera transform
        screen_x = (world_pos[0] - self._camera_position.x) * self._camera_zoom
        screen_y = (world_pos[1] - self._camera_position.y) * self._camera_zoom
        
        # Center on screen
        screen_x += self._viewport_size[0] / 2
        screen_y += self._viewport_size[1] / 2
        
        return (screen_x, screen_y)
    
    def screen_to_world(self, screen_pos: Tuple[float, float]) -> Tuple[float, float]:
        """Convert screen coordinates to world coordinates.
        
        Args:
            screen_pos: Screen position (x, y)
            
        Returns:
            World position (x, y)
        """
        # Remove screen center offset
        world_x = screen_pos[0] - self._viewport_size[0] / 2
        world_y = screen_pos[1] - self._viewport_size[1] / 2
        
        # Apply inverse camera transform
        world_x = world_x / self._camera_zoom + self._camera_position.x
        world_y = world_y / self._camera_zoom + self._camera_position.y
        
        return (world_x, world_y)
    
    def set_camera_position(self, x: float, y: float) -> None:
        """Set camera position in world coordinates.
        
        Args:
            x: World X coordinate
            y: World Y coordinate
        """
        self._camera_position = glm.vec2(x, y)
    
    def set_camera_zoom(self, zoom: float) -> None:
        """Set camera zoom level.
        
        Args:
            zoom: Zoom factor (1.0 = normal, >1.0 = zoom in, <1.0 = zoom out)
        """
        self._camera_zoom = max(0.1, min(10.0, zoom))
    
    def get_camera_position(self) -> Tuple[float, float]:
        """Get camera position.
        
        Returns:
            (x, y) camera position
        """
        return (self._camera_position.x, self._camera_position.y)
    
    def get_camera_zoom(self) -> float:
        """Get camera zoom level.
        
        Returns:
            Zoom factor
        """
        return self._camera_zoom
    
    def set_clear_color(self, r: int, g: int, b: int, a: int = 255) -> None:
        """Set background clear color.
        
        Args:
            r: Red component (0-255)
            g: Green component (0-255)
            b: Blue component (0-255)
            a: Alpha component (0-255)
        """
        self._clear_color = (r, g, b, a)
    
    def get_window_size(self) -> Tuple[int, int]:
        """Get current window size.
        
        Returns:
            (width, height) tuple
        """
        return self._viewport_size
    
    def set_window_size(self, width: int, height: int) -> None:
        """Set window size.
        
        Args:
            width: New width
            height: New height
        """
        if self._initialized:
            self._window = pygame.display.set_mode((width, height), 
                                                  self._window.get_flags())
            self._screen = self._window
            self._viewport_size = (width, height)
    
    def get_fps(self) -> float:
        """Get current FPS.
        
        Returns:
            Current frames per second
        """
        return self._fps
    
    def set_target_fps(self, fps: int) -> None:
        """Set target FPS.
        
        Args:
            fps: Target frames per second
        """
        self._target_fps = fps
    
    def shutdown(self) -> None:
        """Shutdown renderer and clean up resources."""
        logger.info("Shutting down Pygame renderer...")
        
        # Clear texture cache
        self._texture_cache.clear()
        self._texture_refs.clear()
        
        # Clear batches
        self._sprite_batches.clear()
        self._current_batches.clear()
        
        # Quit Pygame
        pygame.quit()
        
        self._initialized = False
        logger.info("Pygame renderer shutdown complete")
    
    @property
    def initialized(self) -> bool:
        """Check if renderer is initialized."""
        return self._initialized
    
    @property
    def screen(self) -> Optional[pygame.Surface]:
        """Get the screen surface."""
        return self._screen