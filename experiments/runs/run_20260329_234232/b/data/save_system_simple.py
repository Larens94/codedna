"""
Save System for game state management.
Provides save/load functionality with SQLite backend.
"""

import json
import os
import logging
import sqlite3
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
import hashlib
from dataclasses import dataclass, field
from enum import Enum

from .database import DatabaseManager
from .serializer import Serializer

logger = logging.getLogger(__name__)


class SaveError(Exception):
    """Save operation error."""
    pass


class LoadError(Exception):
    """Load operation error."""
    pass


@dataclass
class SaveSlotInfo:
    """Information about a save slot."""
    slot_id: int
    slot_name: str
    created_at: datetime
    last_played: datetime
    play_time_seconds: int
    character_name: str
    character_class: str
    character_level: int
    world_name: str
    is_auto_save: bool
    is_quick_save: bool
    metadata: Dict[str, Any] = field(default_factory=dict)