"""
Asset Manager for loading and caching game assets.
Provides lazy loading, caching, and resource management for sprites, sounds, and configurations.
"""

import json
import os
import logging
import pygame
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
from pathlib import Path
import hashlib
from dataclasses import dataclass, field
from collections import OrderedDict
import time

logger = logging.getLogger(__name__)


class AssetType(Enum):
    """Types of game assets."""
    SPRITE = "sprite"
    SOUND = "sound"
    MUSIC = "music"
    FONT = "font"
    CONFIG = "config"
    DATA = "data"
    SHADER = "shader"
    TEXTURE = "texture"
    ANIMATION = "animation"
    TILEMAP = "tilemap"


class AssetLoadError(Exception):
    """Asset loading error."""
    pass


@dataclass
class AssetMetadata:
    """Metadata for an asset."""
    asset_id: str
    asset_type: AssetType
    file_path: str
    file_size: int
    load_time: float
    last_accessed: float
    access_count: int = 0
    memory_size: int = 0
    checksum: str = ""
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


class AssetManager:
    """
    Manages loading, caching, and unloading of game assets.
    """
    
    def __init__(self, assets_base_path: str = "assets", max_cache_size_mb: int = 100):
        """
        Initialize asset manager.
        
        Args:
            assets_base_path: Base path for asset files
            max_cache_size_mb: Maximum cache size in megabytes
        """
        self.assets_base_path = Path(assets_base_path)
        self.max_cache_size_bytes = max_cache_size_mb * 1024 * 1024
        
        # Asset cache
        self._cache: Dict[str, Any] = {}
        self._metadata: Dict[str, AssetMetadata] = {}
        
        # Cache management
        self._current_cache_size = 0
        self._access_order = OrderedDict()
        
        # File extension to asset type mapping
        self._extension_map = {
            '.png': AssetType.SPRITE,
            '.jpg': AssetType.SPRITE,
            '.jpeg': AssetType.SPRITE,
            '.bmp': AssetType.SPRITE,
            '.gif': AssetType.SPRITE,
            '.wav': AssetType.SOUND,
            '.mp3': AssetType.SOUND,
            '.ogg': AssetType.SOUND,
            '.ttf': AssetType.FONT,
            '.otf': AssetType.FONT,
            '.json': AssetType.CONFIG,
            '.txt': AssetType.DATA,
            '.csv': AssetType.DATA,
            '.glsl': AssetType.SHADER,
            '.tmx': AssetType.TILEMAP,
        }
        
        # Ensure assets directory exists
        self.assets_base_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Asset manager initialized with base path: {self.assets_base_path}")
    
    def get_asset_type(self, file_path: Union[str, Path]) -> AssetType:
        """
        Determine asset type from file extension.
        
        Args:
            file_path: Path to asset file
            
        Returns:
            Asset type
        """
        path = Path(file_path)
        extension = path.suffix.lower()
        
        if extension in self._extension_map:
            return self._extension_map[extension]
        
        # Default to DATA for unknown extensions
        return AssetType.DATA
    
    def load_asset(self, asset_id: str, file_path: Optional[str] = None, 
                   asset_type: Optional[AssetType] = None, force_reload: bool = False) -> Any:
        """
        Load an asset into cache.
        
        Args:
            asset_id: Unique identifier for the asset
            file_path: Path to asset file (relative to assets_base_path)
            asset_type: Type of asset (auto-detected if None)
            force_reload: Force reload even if already cached
            
        Returns:
            Loaded asset
        """
        # Check if already in cache
        if asset_id in self._cache and not force_reload:
            self._update_access(asset_id)
            return self._cache[asset_id]
        
        # Determine file path
        if file_path is None:
            # Try to find asset by ID
            file_path = self._find_asset_by_id(asset_id)
            if file_path is None:
                raise AssetLoadError(f"Asset not found: {asset_id}")
        
        # Resolve full path
        full_path = self.assets_base_path / file_path
        
        if not full_path.exists():
            raise AssetLoadError(f"Asset file not found: {full_path}")
        
        # Determine asset type
        if asset_type is None:
            asset_type = self.get_asset_type(full_path)
        
        # Load asset based on type
        start_time = time.time()
        
        try:
            if asset_type == AssetType.SPRITE:
                asset = self._load_sprite(full_path)
            elif asset_type == AssetType.SOUND:
                asset = self._load_sound(full_path)
            elif asset_type == AssetType.MUSIC:
                asset = self._load_music(full_path)
            elif asset_type == AssetType.FONT:
                asset = self._load_font(full_path)
            elif asset_type in [AssetType.CONFIG, AssetType.DATA]:
                asset = self._load_data(full_path)
            elif asset_type == AssetType.SHADER:
                asset = self._load_shader(full_path)
            elif asset_type == AssetType.TILEMAP:
                asset = self._load_tilemap(full_path)
            else:
                # Default to binary load
                asset = self._load_binary(full_path)
            
            load_time = time.time() - start_time
            
            # Calculate memory size (estimate)
            memory_size = self._estimate_memory_size(asset, asset_type)
            
            # Create metadata
            metadata = AssetMetadata(
                asset_id=asset_id,
                asset_type=asset_type,
                file_path=str(file_path),
                file_size=full_path.stat().st_size,
                load_time=load_time,
                last_accessed=time.time(),
                access_count=1,
                memory_size=memory_size,
                checksum=self._calculate_checksum(full_path),
                tags=[]
            )
            
            # Add to cache
            self._add_to_cache(asset_id, asset, metadata)
            
            logger.debug(f"Loaded asset: {asset_id} ({asset_type.value}) in {load_time:.3f}s")
            
            return asset
            
        except Exception as e:
            logger.error(f"Failed to load asset {asset_id}: {e}")
            raise AssetLoadError(f"Failed to load asset {asset_id}: {e}")
    
    def _load_sprite(self, file_path: Path) -> pygame.Surface:
        """Load a sprite/image."""
        try:
            return pygame.image.load(str(file_path)).convert_alpha()
        except pygame.error as e:
            raise AssetLoadError(f"Failed to load sprite {file_path}: {e}")
    
    def _load_sound(self, file_path: Path) -> pygame.mixer.Sound:
        """Load a sound effect."""
        try:
            return pygame.mixer.Sound(str(file_path))
        except pygame.error as e:
            raise AssetLoadError(f"Failed to load sound {file_path}: {e}")
    
    def _load_music(self, file_path: Path) -> str:
        """Load music file path (pygame.music loads differently)."""
        return str(file_path)
    
    def _load_font(self, file_path: Path) -> pygame.font.Font:
        """Load a font."""
        try:
            # Default size, can be scaled later
            return pygame.font.Font(str(file_path), 24)
        except pygame.error as e:
            raise AssetLoadError(f"Failed to load font {file_path}: {e}")
    
    def _load_data(self, file_path: Path) -> Any:
        """Load JSON or text data."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() == '.json':
                    return json.load(f)
                else:
                    return f.read()
        except Exception as e:
            raise AssetLoadError(f"Failed to load data {file_path}: {e}")
    
    def _load_shader(self, file_path: Path) -> str:
        """Load shader source code."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise AssetLoadError(f"Failed to load shader {file_path}: {e}")
    
    def _load_tilemap(self, file_path: Path) -> Dict[str, Any]:
        """Load tilemap data."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise AssetLoadError(f"Failed to load tilemap {file_path}: {e}")
    
    def _load_binary(self, file_path: Path) -> bytes:
        """Load binary file."""
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            raise AssetLoadError(f"Failed to load binary file {file_path}: {e}")
    
    def _estimate_memory_size(self, asset: Any, asset_type: AssetType) -> int:
        """Estimate memory usage of an asset."""
        if asset_type == AssetType.SPRITE and isinstance(asset, pygame.Surface):
            # Estimate surface memory: width * height * bytes_per_pixel
            return asset.get_width() * asset.get_height() * 4  # 4 bytes per pixel (RGBA)
        elif asset_type == AssetType.SOUND and isinstance(asset, pygame.mixer.Sound):
            # Rough estimate for sound
            return 1024 * 100  # 100KB estimate
        elif isinstance(asset, str):
            return len(asset.encode('utf-8'))
        elif isinstance(asset, bytes):
            return len(asset)
        elif isinstance(asset, dict) or isinstance(asset, list):
            # Rough estimate for data structures
            return len(str(asset).encode('utf-8'))
        else:
            return 1024  # 1KB default estimate
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of a file."""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    def _find_asset_by_id(self, asset_id: str) -> Optional[str]:
        """Find asset file by ID."""
        # Simple implementation - could be extended with asset manifest
        # For now, assume asset_id is the relative path
        return asset_id
    
    def _add_to_cache(self, asset_id: str, asset: Any, metadata: AssetMetadata):
        """Add asset to cache with LRU management."""
        # Check cache size and evict if needed
        self._manage_cache_size(metadata.memory_size)
        
        # Add to cache
        self._cache[asset_id] = asset
        self._metadata[asset_id] = metadata
        self._access_order[asset_id] = time.time()
        self._current_cache_size += metadata.memory_size
    
    def _update_access(self, asset_id: str):
        """Update access time for an asset."""
        if asset_id in self._metadata:
            self._metadata[asset_id].last_accessed = time.time()
            self._metadata[asset_id].access_count += 1
            self._access_order[asset_id] = time.time()
    
    def _manage_cache_size(self, new_asset_size: int):
        """Manage cache size using LRU eviction."""
        while (self._current_cache_size + new_asset_size > self.max_cache_size_bytes and 
               len(self._cache) > 0):
            # Find least recently used asset
            lru_asset_id = min(self._access_order.items(), key=lambda x: x[1])[0]
            self.unload_asset(lru_asset_id)
    
    def unload_asset(self, asset_id: str) -> bool:
        """
        Unload an asset from cache.
        
        Args:
            asset_id: Asset identifier
            
        Returns:
            True if asset was unloaded
        """
        if asset_id in self._cache:
            # Remove from cache
            metadata = self._metadata[asset_id]
            self._current_cache_size -= metadata.memory_size
            
            del self._cache[asset_id]
            del self._metadata[asset_id]
            if asset_id in self._access_order:
                del self._access_order[asset_id]
            
            logger.debug(f"Unloaded asset: {asset_id}")
            return True
        
        return False
    
    def unload_all(self):
        """Unload all assets from cache."""
        asset_ids = list(self._cache.keys())
        for asset_id in asset_ids:
            self.unload_asset(asset_id)
        
        logger.info("Unloaded all assets from cache")
    
    def get_asset(self, asset_id: str) -> Optional[Any]:
        """
        Get asset from cache (doesn't load if not cached).
        
        Args:
            asset_id: Asset identifier
            
        Returns:
            Asset if cached, None otherwise
        """
        if asset_id in self._cache:
            self._update_access(asset_id)
            return self._cache[asset_id]
        return None
    
    def preload_assets(self, asset_list: List[Tuple[str, str, Optional[AssetType]]]):
        """
        Preload multiple assets.
        
        Args:
            asset_list: List of (asset_id, file_path, asset_type) tuples
        """
        for asset_id, file_path, asset_type in asset_list:
            try:
                self.load_asset(asset_id, file_path, asset_type)
            except AssetLoadError as e:
                logger.warning(f"Failed to preload asset {asset_id}: {e}")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Get cache information.
        
        Returns:
            Dictionary with cache statistics
        """
        total_assets = len(self._cache)
        total_memory_mb = self._current_cache_size / (1024 * 1024)
        max_memory_mb = self.max_cache_size_bytes / (1024 * 1024)
        
        # Count assets by type
        assets_by_type: Dict[str, int] = {}
        for metadata in self._metadata.values():
            asset_type = metadata.asset_type.value
            assets_by_type[asset_type] = assets_by_type.get(asset_type, 0) + 1
        
        return {
            'total_assets': total_assets,
            'total_memory_mb': total_memory_mb,
            'max_memory_mb': max_memory_mb,
            'memory_usage_percent': (total_memory_mb / max_memory_mb * 100) if max_memory_mb > 0 else 0,
            'assets_by_type': assets_by_type,
            'most_accessed': sorted(
                self._metadata.values(),
                key=lambda m: m.access_count,
                reverse=True
            )[:5]
        }
    
    def scan_assets_directory(self) -> List[Dict[str, Any]]:
        """
        Scan assets directory and return list of found assets.
        
        Returns:
            List of asset information dictionaries
        """
        assets = []
        
        for root, dirs, files in os.walk(self.assets_base_path):
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(self.assets_base_path)
                
                asset_type = self.get_asset_type(file_path)
                
                assets.append({
                    'path': str(relative_path),
                    'type': asset_type.value,
                    'size_bytes': file_path.stat().st_size,
                    'modified': file_path.stat().st_mtime
                })
        
        return assets
    
    def create_asset_manifest(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Create manifest of all assets.
        
        Args:
            output_path: Optional path to save manifest
            
        Returns:
            Asset manifest dictionary
        """
        assets = self.scan_assets_directory()
        
        manifest = {
            'generated_at': time.time(),
            'assets_base_path': str(self.assets_base_path),
            'total_assets': len(assets),
            'total_size_bytes': sum(a['size_bytes'] for a in assets),
            'assets': assets
        }
        
        if output_path:
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(manifest, f, indent=2)
                logger.info(f"Asset manifest saved to: {output_path}")
            except Exception as e:
                logger.error(f"Failed to save asset manifest: {e}")
        
        return manifest
    
    def __contains__(self, asset_id: str) -> bool:
        """Check if asset is in cache."""
        return asset_id in self._cache
    
    def __getitem__(self, asset_id: str) -> Any:
        """Get asset with [] syntax (loads if not cached)."""
        return self.load_asset(asset_id)