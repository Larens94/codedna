"""
Data module - Asset management and serialization.
Responsible for loading, caching, and serializing game data.
"""

from .asset_manager import AssetManager, AssetType
from .serializer import Serializer
# JUDGE FIX 4: config_manager.py and save_system.py are empty stubs (DataArchitect ran out of tool calls)
# from .config_manager import ConfigManager
# from .save_system import SaveSystem

__all__ = [
    'AssetManager',
    'AssetType',
    'Serializer',
]