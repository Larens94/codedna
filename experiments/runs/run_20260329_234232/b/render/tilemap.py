"""
Tilemap rendering system for 2D RPG environments.
Handles loading, rendering, and culling of tile-based maps.
"""

import pygame
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import json
import math


@dataclass
class Tile:
    """Represents a single tile in the map."""
    texture_id: str
    position: Tuple[int, int]  # grid coordinates
    layer: int = 0
    collidable: bool = False
    animated: bool = False
    animation_speed: float = 1.0
    animation_frames: List[str] = None
    current_frame: int = 0
    frame_time: float = 0.0
    
    def __post_init__(self):
        if self.animation_frames is None:
            self.animation_frames = [self.texture_id]


@dataclass
class TileLayer:
    """Layer of tiles in the map."""
    name: str
    tiles: List[Tile] = None
    visible: bool = True
    opacity: float = 1.0
    parallax_factor: float = 1.0  # for parallax scrolling
    
    def __post_init__(self):
        if self.tiles is None:
            self.tiles = []


@dataclass
class TileChunk:
    """Chunk of tiles for efficient culling and rendering."""
    position: Tuple[int, int]  # chunk coordinates
    tiles: List[Tile] = None
    bounds: pygame.Rect = None
    
    def __post_init__(self):
        if self.tiles is None:
            self.tiles = []
        
        # Calculate bounds from tiles
        if self.tiles:
            min_x = min(t.position[0] for t in self.tiles)
            min_y = min(t.position[1] for t in self.tiles)
            max_x = max(t.position[0] for t in self.tiles)
            max_y = max(t.position[1] for t in self.tiles)
            self.bounds = pygame.Rect(min_x, min_y, 
                                     max_x - min_x + 1, 
                                     max_y - min_y + 1)


class TilemapRenderer:
    """
    Tilemap rendering system with chunk-based loading and culling.
    
    Features:
    - Chunk-based rendering for large maps
    - Viewport culling for performance
    - Multiple layers with parallax
    - Animated tiles
    - Collision data
    """
    
    def __init__(self, sprite_renderer, tile_size: Tuple[int, int] = (32, 32)):
        """
        Initialize tilemap renderer.
        
        Args:
            sprite_renderer: SpriteRenderer instance
            tile_size: Size of each tile in pixels (width, height)
        """
        self.sprite_renderer = sprite_renderer
        self.tile_size = tile_size
        
        # Map data
        self.layers: Dict[str, TileLayer] = {}
        self.chunks: Dict[Tuple[int, int], TileChunk] = {}
        self.chunk_size = 16  # tiles per chunk
        
        # Rendering state
        self.camera = None
        self.visible_chunks: List[TileChunk] = []
        self.visible_tiles = 0
        self.total_tiles = 0
        
        # Performance tracking
        self.chunks_rendered = 0
        self.tiles_rendered = 0
        self.culled_tiles = 0
        
        # Animation state
        self.animation_time = 0.0
        
    def load_from_json(self, filepath: str) -> bool:
        """
        Load tilemap from JSON file.
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Load map properties
            map_width = data.get('width', 100)
            map_height = data.get('height', 100)
            tile_width = data.get('tilewidth', self.tile_size[0])
            tile_height = data.get('tileheight', self.tile_size[1])
            self.tile_size = (tile_width, tile_height)
            
            # Load layers
            for layer_data in data.get('layers', []):
                layer_name = layer_data.get('name', 'layer')
                layer = TileLayer(name=layer_name)
                
                # Load tiles
                if layer_data.get('type') == 'tilelayer':
                    tiles = self._parse_tile_layer(layer_data, layer_name)
                    layer.tiles = tiles
                    
                    # Create chunks
                    self._create_chunks(tiles, layer_name)
                
                self.layers[layer_name] = layer
            
            self.total_tiles = sum(len(layer.tiles) for layer in self.layers.values())
            print(f"Loaded tilemap: {map_width}x{map_height}, {self.total_tiles} tiles")
            return True
            
        except Exception as e:
            print(f"Failed to load tilemap from {filepath}: {e}")
            return False
    
    def _parse_tile_layer(self, layer_data: Dict, layer_name: str) -> List[Tile]:
        """Parse tile layer data."""
        tiles = []
        width = layer_data.get('width', 100)
        height = layer_data.get('height', 100)
        tile_data = layer_data.get('data', [])
        
        for y in range(height):
            for x in range(width):
                tile_index = y * width + x
                tile_id = tile_data[tile_index]
                
                if tile_id > 0:  # 0 means no tile
                    texture_id = f"tile_{tile_id}"
                    tile = Tile(
                        texture_id=texture_id,
                        position=(x, y),
                        layer=len(tiles)  # temporary layer index
                    )
                    tiles.append(tile)
        
        return tiles
    
    def _create_chunks(self, tiles: List[Tile], layer_name: str):
        """Create chunks from tiles."""
        for tile in tiles:
            chunk_x = tile.position[0] // self.chunk_size
            chunk_y = tile.position[1] // self.chunk_size
            chunk_key = (chunk_x, chunk_y, layer_name)
            
            if chunk_key not in self.chunks:
                self.chunks[chunk_key] = TileChunk(
                    position=(chunk_x, chunk_y)
                )
            
            self.chunks[chunk_key].tiles.append(tile)
    
    def set_camera(self, camera):
        """
        Set camera for viewport culling.
        
        Args:
            camera: CameraSystem instance
        """
        self.camera = camera
    
    def update(self, delta_time: float):
        """
        Update tilemap (animations, culling).
        
        Args:
            delta_time: Time since last update in seconds
        """
        # Update animation time
        self.animation_time += delta_time
        
        # Update visible chunks based on camera
        if self.camera:
            self._update_visible_chunks()
        
        # Update animated tiles in visible chunks
        self._update_animated_tiles(delta_time)
    
    def _update_visible_chunks(self):
        """Update list of visible chunks based on camera viewport."""
        if not self.camera:
            self.visible_chunks = list(self.chunks.values())
            return
        
        visible_rect = self.camera.get_visible_rect()
        
        # Convert world rect to chunk coordinates
        chunk_min_x = int(visible_rect.left // (self.chunk_size * self.tile_size[0]))
        chunk_min_y = int(visible_rect.top // (self.chunk_size * self.tile_size[1]))
        chunk_max_x = int(visible_rect.right // (self.chunk_size * self.tile_size[0])) + 1
        chunk_max_y = int(visible_rect.bottom // (self.chunk_size * self.tile_size[1])) + 1
        
        self.visible_chunks = []
        for chunk_key, chunk in self.chunks.items():
            chunk_x, chunk_y, layer_name = chunk_key
            
            # Check if chunk is in visible range
            if (chunk_min_x <= chunk_x <= chunk_max_x and
                chunk_min_y <= chunk_y <= chunk_max_y):
                self.visible_chunks.append(chunk)
    
    def _update_animated_tiles(self, delta_time: float):
        """Update animated tiles in visible chunks."""
        for chunk in self.visible_chunks:
            for tile in chunk.tiles:
                if tile.animated and tile.animation_frames:
                    tile.frame_time += delta_time * tile.animation_speed
                    
                    frame_duration = 0.1  # default frame duration
                    if tile.frame_time >= frame_duration:
                        tile.frame_time = 0
                        tile.current_frame = (tile.current_frame + 1) % len(tile.animation_frames)
                        tile.texture_id = tile.animation_frames[tile.current_frame]
    
    def render(self):
        """
        Render visible tiles.
        """
        self.chunks_rendered = 0
        self.tiles_rendered = 0
        self.culled_tiles = 0
        
        if not self.camera:
            # Render all tiles if no camera
            for chunk in self.chunks.values():
                self._render_chunk(chunk)
            return
        
        # Render visible chunks
        for chunk in self.visible_chunks:
            self._render_chunk(chunk)
    
    def _render_chunk(self, chunk: TileChunk):
        """Render all tiles in a chunk."""
        self.chunks_rendered += 1
        
        for tile in chunk.tiles:
            # Convert grid position to world position
            world_x = tile.position[0] * self.tile_size[0]
            world_y = tile.position[1] * self.tile_size[1]
            
            # Apply layer parallax
            layer = self.layers.get(f"layer_{tile.layer}")
            if layer and layer.parallax_factor != 1.0 and self.camera:
                camera_pos = self.camera.render_position
                parallax_x = camera_pos.x * (1 - layer.parallax_factor)
                parallax_y = camera_pos.y * (1 - layer.parallax_factor)
                world_x += parallax_x
                world_y += parallax_y
            
            # Create sprite for tile
            sprite_id = f"tile_{tile.position[0]}_{tile.position[1]}_{tile.layer}"
            
            # Check if sprite already exists
            if sprite_id not in self.sprite_renderer.sprites:
                self.sprite_renderer.create_sprite(
                    sprite_id=sprite_id,
                    texture_id=tile.texture_id,
                    position=(world_x, world_y),
                    z_index=tile.layer
                )
            else:
                # Update existing sprite
                self.sprite_renderer.update_sprite(
                    sprite_id,
                    texture_id=tile.texture_id,
                    position=(world_x, world_y)
                )
            
            self.tiles_rendered += 1
    
    def get_tile_at(self, grid_x: int, grid_y: int, 
                   layer_name: Optional[str] = None) -> Optional[Tile]:
        """
        Get tile at grid coordinates.
        
        Args:
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate
            layer_name: Optional specific layer
            
        Returns:
            Tile at position or None
        """
        # Find chunk containing position
        chunk_x = grid_x // self.chunk_size
        chunk_y = grid_y // self.chunk_size
        
        if layer_name:
            chunk_keys = [(chunk_x, chunk_y, layer_name)]
        else:
            # Check all layers
            chunk_keys = [(chunk_x, chunk_y, name) 
                         for name in self.layers.keys()]
        
        for chunk_key in chunk_keys:
            if chunk_key in self.chunks:
                chunk = self.chunks[chunk_key]
                for tile in chunk.tiles:
                    if tile.position == (grid_x, grid_y):
                        return tile
        
        return None
    
    def world_to_grid(self, world_x: float, world_y: float) -> Tuple[int, int]:
        """
        Convert world coordinates to grid coordinates.
        
        Args:
            world_x: World X coordinate
            world_y: World Y coordinate
            
        Returns:
            Grid (x, y) coordinates
        """
        grid_x = int(world_x // self.tile_size[0])
        grid_y = int(world_y // self.tile_size[1])
        return (grid_x, grid_y)
    
    def grid_to_world(self, grid_x: int, grid_y: int) -> Tuple[float, float]:
        """
        Convert grid coordinates to world coordinates.
        
        Args:
            grid_x: Grid X coordinate
            grid_y: Grid Y coordinate
            
        Returns:
            World (x, y) coordinates
        """
        world_x = grid_x * self.tile_size[0]
        world_y = grid_y * self.tile_size[1]
        return (world_x, world_y)
    
    def check_collision(self, world_x: float, world_y: float, 
                       radius: float = 0) -> bool:
        """
        Check for collision at world position.
        
        Args:
            world_x: World X coordinate
            world_y: World Y coordinate
            radius: Collision radius
            
        Returns:
            True if collision detected
        """
        grid_pos = self.world_to_grid(world_x, world_y)
        
        # Check tiles in surrounding area based on radius
        check_radius = int(math.ceil(radius / min(self.tile_size)))
        
        for dx in range(-check_radius, check_radius + 1):
            for dy in range(-check_radius, check_radius + 1):
                check_x = grid_pos[0] + dx
                check_y = grid_pos[1] + dy
                
                tile = self.get_tile_at(check_x, check_y)
                if tile and tile.collidable:
                    # Check actual collision with tile bounds
                    tile_world = self.grid_to_world(check_x, check_y)
                    tile_rect = pygame.Rect(
                        tile_world[0], tile_world[1],
                        self.tile_size[0], self.tile_size[1]
                    )
                    
                    # Simple circle-rectangle collision
                    closest_x = max(tile_rect.left, min(world_x, tile_rect.right))
                    closest_y = max(tile_rect.top, min(world_y, tile_rect.bottom))
                    
                    distance = math.sqrt((world_x - closest_x) ** 2 + 
                                       (world_y - closest_y) ** 2)
                    
                    if distance <= radius:
                        return True
        
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get tilemap statistics.
        
        Returns:
            Dictionary with tilemap metrics
        """
        return {
            'total_tiles': self.total_tiles,
            'tiles_rendered': self.tiles_rendered,
            'culled_tiles': self.total_tiles - self.tiles_rendered,
            'chunks_total': len(self.chunks),
            'chunks_rendered': self.chunks_rendered,
            'layers': len(self.layers),
            'culling_efficiency': (self.total_tiles - self.tiles_rendered) / max(1, self.total_tiles)
        }
    
    def cleanup(self):
        """Clean up tilemap resources."""
        # Remove all tile sprites
        for chunk in self.chunks.values():
            for tile in chunk.tiles:
                sprite_id = f"tile_{tile.position[0]}_{tile.position[1]}_{tile.layer}"
                if sprite_id in self.sprite_renderer.sprites:
                    self.sprite_renderer.remove_sprite(sprite_id)
        
        self.layers.clear()
        self.chunks.clear()
        self.visible_chunks.clear()
        
        print("TilemapRenderer cleaned up")