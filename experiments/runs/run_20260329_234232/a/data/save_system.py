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


class SaveSystem:
    """SQLite-based save/load system — stub to allow game boot."""

    def __init__(self, db_path: str = "saves/game.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None

    def initialize(self) -> bool:
        try:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS saves "
                "(slot INTEGER PRIMARY KEY, data BLOB, timestamp TEXT)"
            )
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"SaveSystem init failed: {e}")
            return False

    def save(self, slot: int, data: Dict[str, Any]) -> bool:
        if not self._conn:
            return False
        try:
            blob = zlib.compress(pickle.dumps(data))
            self._conn.execute(
                "INSERT OR REPLACE INTO saves VALUES (?, ?, ?)",
                (slot, blob, datetime.now().isoformat())
            )
            self._conn.commit()
            return True
        except Exception as e:
            logger.error(f"Save failed: {e}")
            return False

    def load(self, slot: int) -> Optional[Dict[str, Any]]:
        if not self._conn:
            return None
        try:
            row = self._conn.execute(
                "SELECT data FROM saves WHERE slot=?", (slot,)
            ).fetchone()
            if row:
                return pickle.loads(zlib.decompress(row[0]))
        except Exception as e:
            logger.error(f"Load failed: {e}")
        return None

    def shutdown(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None