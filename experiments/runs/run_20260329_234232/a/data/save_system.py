"""save_system.py — SQLite-based save/load system for game state.

exports: SaveSystem class
used_by: data/main.py → SaveSystem()
rules:   Must support multiple save slots, compression, and ECS component serialization
agent:   DataArchitect | 2024-01-15 | Implemented SQLite schema with game state tables
"""

import os
import json
import sqlite3
import logging
import zlib
import pickle
from typing import Dict, Any, Optional, List, Tuple, Union
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
import hashlib

logger = logging.getLogger(__name__)