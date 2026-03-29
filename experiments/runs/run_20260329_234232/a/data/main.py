"""main.py — Data module main exports.

exports: SaveSystem(), AssetManager(), load_config() -> dict
used_by: gameplay/game.py → Game._save_system, Game._asset_manager
rules:   Must support both binary and JSON serialization where appropriate
agent:   DataArchitect | 2024-01-15 | Implemented SQLite save system, asset manager, config loader
"""

import os
import json
import sqlite3
import logging
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path
from datetime import datetime
import pickle
import zlib

from .save_system import SaveSystem
from .asset_manager import AssetManager
from .config_loader import load_config

logger = logging.getLogger(__name__)

# Re-export the main classes and functions
__all__ = ['SaveSystem', 'AssetManager', 'load_config']

# Default configuration for the data module
DEFAULT_CONFIG = {
    "save": {
        "max_slots": 10,
        "auto_save_interval": 300,  # seconds
        "compression": True,
        "encryption": False
    },
    "assets": {
        "cache_size_mb": 100,
        "texture_formats": ["png", "jpg", "jpeg", "bmp"],
        "sound_formats": ["wav", "ogg", "mp3"],
        "hot_reload": False
    },
    "database": {
        "path": "saves/game.db",
        "wal_mode": True,
        "journal_mode": "WAL"
    }
}

def get_default_config() -> Dict[str, Any]:
    """Get default configuration for data module.
    
    Returns:
        Default configuration dictionary
    """
    return DEFAULT_CONFIG.copy()

def initialize_data_module(config: Optional[Dict[str, Any]] = None) -> Tuple[SaveSystem, AssetManager]:
    """Initialize the data module with configuration.
    
    Args:
        config: Optional configuration override
        
    Returns:
        Tuple of (SaveSystem, AssetManager) instances
    """
    # Merge with defaults
    final_config = get_default_config()
    if config:
        # Deep merge
        def merge_dicts(base, override):
            for key, value in override.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    merge_dicts(base[key], value)
                else:
                    base[key] = value
        
        merge_dicts(final_config, config)
    
    # Create saves directory
    save_dir = Path(final_config["database"]["path"]).parent
    save_dir.mkdir(parents=True, exist_ok=True)
    
    # Create assets directory
    asset_dir = Path("assets")
    asset_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize SaveSystem
    save_system = SaveSystem(
        db_path=final_config["database"]["path"],
        max_slots=final_config["save"]["max_slots"],
        compression=final_config["save"]["compression"],
        wal_mode=final_config["database"]["wal_mode"]
    )
    
    # Initialize AssetManager
    asset_manager = AssetManager(
        asset_root="assets",
        cache_size_mb=final_config["assets"]["cache_size_mb"],
        hot_reload=final_config["assets"]["hot_reload"]
    )
    
    logger.info("Data module initialized successfully")
    return save_system, asset_manager

def save_game_state_to_json(game_state: Dict[str, Any], file_path: Union[str, Path]) -> bool:
    """Save game state to JSON file (for debugging/backup).
    
    Args:
        game_state: Game state dictionary
        file_path: Path to save JSON file
        
    Returns:
        True if successful
    """
    try:
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w') as f:
            json.dump(game_state, f, indent=2, default=str)
        
        logger.info(f"Game state saved to JSON: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save game state to JSON: {e}")
        return False

def load_game_state_from_json(file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """Load game state from JSON file.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Game state dictionary or None if failed
    """
    try:
        file_path = Path(file_path)
        
        with open(file_path, 'r') as f:
            game_state = json.load(f)
        
        logger.info(f"Game state loaded from JSON: {file_path}")
        return game_state
    except Exception as e:
        logger.error(f"Failed to load game state from JSON: {e}")
        return None

def serialize_component(component: Any) -> bytes:
    """Serialize a component to bytes.
    
    Args:
        component: Component to serialize
        
    Returns:
        Serialized bytes
        
    Note: Uses pickle for complex objects, falls back to JSON for simple ones
    """
    try:
        # Try to use component's own serialization first
        if hasattr(component, 'to_dict'):
            data = component.to_dict()
            return json.dumps(data).encode('utf-8')
        
        # Fall back to pickle for complex objects
        return pickle.dumps(component)
    except Exception as e:
        logger.error(f"Failed to serialize component {type(component).__name__}: {e}")
        raise

def deserialize_component(data: bytes, component_type: Optional[type] = None) -> Any:
    """Deserialize bytes to component.
    
    Args:
        data: Serialized bytes
        component_type: Optional expected component type
        
    Returns:
        Deserialized component
    """
    try:
        # Try JSON first
        try:
            json_data = json.loads(data.decode('utf-8'))
            if component_type and hasattr(component_type, 'from_dict'):
                return component_type.from_dict(json_data)
            return json_data
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass
        
        # Fall back to pickle
        component = pickle.loads(data)
        
        # Verify type if specified
        if component_type and not isinstance(component, component_type):
            logger.warning(f"Deserialized component type mismatch: expected {component_type}, got {type(component)}")
        
        return component
    except Exception as e:
        logger.error(f"Failed to deserialize component: {e}")
        raise

def compress_data(data: bytes) -> bytes:
    """Compress data using zlib.
    
    Args:
        data: Data to compress
        
    Returns:
        Compressed data
    """
    return zlib.compress(data)

def decompress_data(data: bytes) -> bytes:
    """Decompress data using zlib.
    
    Args:
        data: Compressed data
        
    Returns:
        Decompressed data
    """
    return zlib.decompress(data)

# Example usage
if __name__ == "__main__":
    # Test the data module
    logging.basicConfig(level=logging.INFO)
    
    # Initialize
    save_system, asset_manager = initialize_data_module()
    
    # Test save system
    test_state = {
        "player": {"name": "Test Player", "level": 1},
        "world": {"time": "12:00", "weather": "sunny"},
        "inventory": ["sword", "shield", "potion"]
    }
    
    # Create a test save
    slot_id = save_system.create_save("Test Save", test_state)
    print(f"Created save in slot {slot_id}")
    
    # List saves
    saves = save_system.list_saves()
    print(f"Available saves: {saves}")
    
    # Load save
    loaded_state = save_system.load_save(slot_id)
    print(f"Loaded state: {loaded_state['player']['name']}")
    
    # Test asset manager
    asset_manager.initialize()
    
    # Cleanup
    save_system.delete_save(slot_id)
    asset_manager.shutdown()