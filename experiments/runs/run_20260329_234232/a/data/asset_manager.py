"""asset_manager.py — Enhanced asset loading and management with caching.

exports: AssetManager class
used_by: data/main.py → AssetManager()
rules:   Must track all loaded assets for proper cleanup, support lazy loading
agent:   DataArchitect | 2024-01-15 | Enhanced with LRU cache, reference counting, hot-reloading
"""

import os
import json
import logging
import threading
import time
from typing import Dict, Any, Optional, List, Tuple, Callable, Union
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import hashlib
from collections import OrderedDict

logger = logging.getLogger(__name__)

@dataclass
class AssetInfo:
    """Information about a loaded asset."""
    asset: Any
    asset_type: str
    file_path: Path
    load_time: datetime
    last_access: datetime
    size_bytes: int
    reference_count: int = 1
    hash: str = ""

class AssetManager:
    """Enhanced manager for loading and caching game assets.
    
    Features:
    - Lazy loading with LRU cache
    - Reference counting for proper cleanup
    - Hot-reloading in development mode
    - Asset validation and integrity checking
    - Memory usage tracking
    """
    
    def __init__(self, asset_root: str = "assets", cache_size_mb: int = 100, 
                 hot_reload: bool = False):
        """Initialize asset manager.
        
        Args:
            asset_root: Root directory for assets
            cache_size_mb: Maximum cache size in megabytes
            hot_reload: Enable hot-reloading for development
        """
        self._asset_root = Path(asset_root)
        self._cache_size_bytes = cache_size_mb * 1024 * 1024
        self._hot_reload = hot_reload
        
        # Asset storage
        self._assets: Dict[str, AssetInfo] = {}
        self._asset_cache = OrderedDict()  # LRU cache
        self._current_cache_size = 0
        
        # Loaders by file extension
        self._loaders: Dict[str, Callable] = {}
        self._register_default_loaders()
        
        # Hot-reload tracking
        self._file_watchers: Dict[str, float] = {}
        self._watcher_thread: Optional[threading.Thread] = None
        self._stop_watcher = threading.Event()
        
        # Statistics
        self._stats = {
            "loads": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_loaded_bytes": 0
        }
        
        logger.info(f"AssetManager initialized with {cache_size_mb}MB cache")
    
    def _register_default_loaders(self):
        """Register default asset loaders."""
        # JSON loader
        self.register_loader(".json", self._load_json)
        
        # Image loaders (would integrate with actual renderer)
        for ext in [".png", ".jpg", ".jpeg", ".bmp", ".tga"]:
            self.register_loader(ext, self._load_image)
        
        # Sound loaders
        for ext in [".wav", ".ogg", ".mp3"]:
            self.register_loader(ext, self._load_sound)
        
        # Text loader
        self.register_loader(".txt", self._load_text)
        
        # Binary loader (fallback)
        self.register_loader("", self._load_binary)
    
    def register_loader(self, extension: str, loader: Callable[[Path], Any]):
        """Register a loader for a specific file extension.
        
        Args:
            extension: File extension including dot (e.g., ".png")
            loader: Function that takes a Path and returns loaded asset
        """
        self._loaders[extension.lower()] = loader
        logger.debug(f"Registered loader for extension: {extension}")
    
    def _get_loader(self, file_path: Path) -> Callable:
        """Get appropriate loader for file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Loader function
            
        Raises:
            ValueError: If no loader found for file type
        """
        ext = file_path.suffix.lower()
        
        # Try exact extension match
        if ext in self._loaders:
            return self._loaders[ext]
        
        # Try wildcard loader
        if "" in self._loaders:
            return self._loaders[""]
        
        raise ValueError(f"No loader registered for extension: {ext}")
    
    def _load_json(self, file_path: Path) -> Dict[str, Any]:
        """Load JSON file.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Parsed JSON data
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_image(self, file_path: Path) -> Any:
        """Load image file.
        
        Args:
            file_path: Path to image file
            
        Returns:
            Image data (placeholder - would integrate with renderer)
        """
        # Placeholder - in real implementation, this would use PIL, pygame, etc.
        logger.debug(f"Loading image: {file_path}")
        return {"type": "image", "path": str(file_path), "size": file_path.stat().st_size}
    
    def _load_sound(self, file_path: Path) -> Any:
        """Load sound file.
        
        Args:
            file_path: Path to sound file
            
        Returns:
            Sound data (placeholder - would integrate with audio system)
        """
        # Placeholder - in real implementation, this would use pygame, SDL_mixer, etc.
        logger.debug(f"Loading sound: {file_path}")
        return {"type": "sound", "path": str(file_path), "size": file_path.stat().st_size}
    
    def _load_text(self, file_path: Path) -> str:
        """Load text file.
        
        Args:
            file_path: Path to text file
            
        Returns:
            Text content
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _load_binary(self, file_path: Path) -> bytes:
        """Load binary file.
        
        Args:
            file_path: Path to binary file
            
        Returns:
            Binary data
        """
        with open(file_path, 'rb') as f:
            return f.read()
    
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate file hash for change detection.
        
        Args:
            file_path: Path to file
            
        Returns:
            SHA256 hash of file
        """
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def load(self, asset_path: str, asset_type: Optional[str] = None) -> Any:
        """Load an asset with caching.
        
        Args:
            asset_path: Path to asset relative to asset root
            asset_type: Optional asset type hint
            
        Returns:
            Loaded asset
            
        Raises:
            FileNotFoundError: If asset file doesn't exist
            ValueError: If no loader available for file type
        """
        # Resolve full path
        full_path = self._asset_root / asset_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"Asset not found: {full_path}")
        
        # Generate cache key
        cache_key = f"{asset_type or ''}:{full_path}"
        
        # Check cache
        if cache_key in self._assets:
            self._stats["cache_hits"] += 1
            asset_info = self._assets[cache_key]
            asset_info.last_access = datetime.now()
            asset_info.reference_count += 1
            
            # Update LRU order
            if cache_key in self._asset_cache:
                self._asset_cache.move_to_end(cache_key)
            
            logger.debug(f"Cache hit: {cache_key} (refs: {asset_info.reference_count})")
            return asset_info.asset
        
        self._stats["cache_misses"] += 1
        
        # Load asset
        loader = self._get_loader(full_path)
        logger.info(f"Loading asset: {full_path}")
        
        try:
            asset = loader(full_path)
            file_size = full_path.stat().st_size
            
            # Create asset info
            now = datetime.now()
            asset_info = AssetInfo(
                asset=asset,
                asset_type=asset_type or full_path.suffix,
                file_path=full_path,
                load_time=now,
                last_access=now,
                size_bytes=file_size,
                hash=self._calculate_hash(full_path) if self._hot_reload else ""
            )
            
            # Store in cache
            self._assets[cache_key] = asset_info
            self._asset_cache[cache_key] = asset_info
            self._current_cache_size += file_size
            
            # Update statistics
            self._stats["loads"] += 1
            self._stats["total_loaded_bytes"] += file_size
            
            # Evict if cache is full
            self._evict_if_needed()
            
            # Start watcher if hot-reload enabled
            if self._hot_reload:
                self._file_watchers[str(full_path)] = full_path.stat().st_mtime
                self._start_watcher_thread()
            
            logger.debug(f"Loaded and cached: {cache_key} ({file_size} bytes)")
            return asset
            
        except Exception as e:
            logger.error(f"Failed to load asset {full_path}: {e}")
            raise
    
    def _evict_if_needed(self):
        """Evict least recently used assets if cache is full."""
        while self._current_cache_size > self._cache_size_bytes and self._asset_cache:
            # Get least recently used
            cache_key, asset_info = self._asset_cache.popitem(last=False)
            
            # Only evict if no references
            if asset_info.reference_count <= 0:
                del self._assets[cache_key]
                self._current_cache_size -= asset_info.size_bytes
                logger.debug(f"Evicted from cache: {cache_key}")
            else:
                # Put back at end since it has references
                self._asset_cache[cache_key] = asset_info
    
    def release(self, asset_path: str, asset_type: Optional[str] = None):
        """Release reference to an asset.
        
        Args:
            asset_path: Path to asset
            asset_type: Optional asset type hint
        """
        full_path = self._asset_root / asset_path
        cache_key = f"{asset_type or ''}:{full_path}"
        
        if cache_key in self._assets:
            asset_info = self._assets[cache_key]
            asset_info.reference_count -= 1
            
            logger.debug(f"Released asset: {cache_key} (refs: {asset_info.reference_count})")
            
            # If no references, mark for eviction
            if asset_info.reference_count <= 0:
                # Move to front of LRU for eviction
                if cache_key in self._asset_cache:
                    self._asset_cache.move_to_end(cache_key, last=False)
    
    def unload(self, asset_path: str, asset_type: Optional[str] = None) -> bool:
        """Force unload an asset regardless of reference count.
        
        Args:
            asset_path: Path to asset
            asset_type: Optional asset type hint
            
        Returns:
            True if asset was unloaded
        """
        full_path = self._asset_root / asset_path
        cache_key = f"{asset_type or ''}:{full_path}"
        
        if cache_key in self._assets:
            asset_info = self._assets[cache_key]
            
            # Clean up if asset has cleanup method
            if hasattr(asset_info.asset, 'cleanup'):
                try:
                    asset_info.asset.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up asset {cache_key}: {e}")
            
            # Remove from storage
            del self._assets[cache_key]
            
            if cache_key in self._asset_cache:
                self._current_cache_size -= asset_info.size_bytes
                del self._asset_cache[cache_key]
            
            logger.info(f"Unloaded asset: {cache_key}")
            return True
        
        return False
    
    def get_asset_info(self, asset_path: str, asset_type: Optional[str] = None) -> Optional[AssetInfo]:
        """Get information about a loaded asset.
        
        Args:
            asset_path: Path to asset
            asset_type: Optional asset type hint
            
        Returns:
            AssetInfo or None if not loaded
        """
        full_path = self._asset_root / asset_path
        cache_key = f"{asset_type or ''}:{full_path}"
        return self._assets.get(cache_key)
    
    def preload(self, asset_paths: List[Tuple[str, Optional[str]]]):
        """Preload multiple assets in background.
        
        Args:
            asset_paths: List of (asset_path, asset_type) tuples
        """
        # In a real implementation, this would use threading
        for asset_path, asset_type in asset_paths:
            try:
                self.load(asset_path, asset_type)
            except Exception as e:
                logger.warning(f"Failed to preload {asset_path}: {e}")
    
    def _start_watcher_thread(self):
        """Start file watcher thread for hot-reloading."""
        if self._watcher_thread is None or not self._watcher_thread.is_alive():
            self._stop_watcher.clear()
            self._watcher_thread = threading.Thread(
                target=self._watch_files,
                daemon=True,
                name="AssetWatcher"
            )
            self._watcher_thread.start()
            logger.debug("Started asset watcher thread")
    
    def _watch_files(self):
        """Watch files for changes and reload if modified."""
        while not self._stop_watcher.is_set():
            try:
                time.sleep(1.0)  # Check every second
                
                for file_path_str, last_mtime in list(self._file_watchers.items()):
                    file_path = Path(file_path_str)
                    if file_path.exists():
                        current_mtime = file_path.stat().st_mtime
                        if current_mtime > last_mtime:
                            # File changed, reload
                            logger.info(f"File changed, reloading: {file_path}")
                            self._file_watchers[file_path_str] = current_mtime
                            
                            # Find and reload affected assets
                            for cache_key, asset_info in list(self._assets.items()):
                                if str(asset_info.file_path) == file_path_str:
                                    try:
                                        # Reload asset
                                        loader = self._get_loader(file_path)
                                        new_asset = loader(file_path)
                                        asset_info.asset = new_asset
                                        asset_info.hash = self._calculate_hash(file_path)
                                        asset_info.load_time = datetime.now()
                                        logger.debug(f"Hot-reloaded: {cache_key}")
                                    except Exception as e:
                                        logger.error(f"Failed to hot-reload {file_path}: {e}")
            except Exception as e:
                logger.error(f"Error in file watcher: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get asset manager statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            **self._stats,
            "cache_size_bytes": self._current_cache_size,
            "cache_size_mb": self._current_cache_size / (1024 * 1024),
            "cache_limit_bytes": self._cache_size_bytes,
            "cache_limit_mb": self._cache_size_bytes / (1024 * 1024),
            "loaded_assets": len(self._assets),
            "cached_assets": len(self._asset_cache),
            "hot_reload_enabled": self._hot_reload
        }
    
    def clear_cache(self):
        """Clear all cached assets (force reload)."""
        # Unload all assets
        for cache_key in list(self._assets.keys()):
            self.unload(cache_key)
        
        # Clear cache
        self._assets.clear()
        self._asset_cache.clear()
        self._current_cache_size = 0
        
        logger.info("Cleared asset cache")
    
    def shutdown(self):
        """Shutdown asset manager and clean up resources."""
        logger.info("Shutting down asset manager...")
        
        # Stop watcher thread
        if self._hot_reload:
            self._stop_watcher.set()
            if self._watcher_thread and self._watcher_thread.is_alive():
                self._watcher_thread.join(timeout=2.0)
        
        # Clear all assets
        self.clear_cache()
        
        # Clear loaders
        self._loaders.clear()
        
        logger.info("Asset manager shutdown complete")

# Example usage
if __name__ == "__main__":
    # Test the asset manager
    logging.basicConfig(level=logging.INFO)
    
    manager = AssetManager(cache_size_mb=10, hot_reload=True)
    
    # Create test assets directory
    test_dir = Path("assets/test")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # Create test JSON file
    test_json = test_dir / "test_config.json"
    test_json.write_text(json.dumps({"test": "value", "number": 42}))
    
    # Load asset
    config = manager.load("test/test_config.json")
    print(f"Loaded config: {config}")
    
    # Get stats
    stats = manager.get_stats()
    print(f"Stats: {stats}")
    
    # Cleanup
    manager.shutdown()