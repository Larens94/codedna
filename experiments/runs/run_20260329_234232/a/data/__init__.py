"""__init__.py — Data module exports.

exports: SaveSystem, AssetManager, load_config, initialize_data_module
used_by: gameplay/, render/, main.py
rules:   All assets must be loaded through AssetManager for tracking
agent:   DataArchitect | 2024-01-15 | Updated for new SQLite save system
"""

from .main import SaveSystem, AssetManager, load_config, initialize_data_module

__all__ = ['SaveSystem', 'AssetManager', 'load_config', 'initialize_data_module']