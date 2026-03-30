"""
Database module for SQLite game data storage.
Handles database connections, schema creation, and migrations.
"""

import sqlite3
import json
import os
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime
from pathlib import Path
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Database operation error."""
    pass


class MigrationError(Exception):
    """Database migration error."""
    pass


class DatabaseManager:
    """
    Manages SQLite database connections and operations.
    """
    
    CURRENT_SCHEMA_VERSION = 1
    
    def __init__(self, db_path: str = "saves/game.db"):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure database directory exists."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    
    def connect(self) -> sqlite3.Connection:
        """
        Connect to database.
        
        Returns:
            Database connection
        """
        if self.connection is None:
            try:
                self.connection = sqlite3.connect(
                    self.db_path,
                    detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
                )
                self.connection.row_factory = sqlite3.Row
                # Enable foreign keys
                self.connection.execute("PRAGMA foreign_keys = ON")
                # Enable WAL mode for better concurrency
                self.connection.execute("PRAGMA journal_mode = WAL")
                logger.info(f"Connected to database: {self.db_path}")
            except sqlite3.Error as e:
                logger.error(f"Failed to connect to database: {e}")
                raise DatabaseError(f"Database connection failed: {e}")
        
        return self.connection
    
    def disconnect(self):
        """Disconnect from database."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Disconnected from database")
    
    def initialize_database(self):
        """
        Initialize database with schema.
        """
        conn = self.connect()
        
        try:
            # Create schema version table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
            """)
            
            # Get current schema version
            current_version = self.get_schema_version()
            
            if current_version == 0:
                # Fresh database, create all tables
                self._create_schema_v1()
                self._set_schema_version(1, "Initial schema")
                logger.info("Created initial database schema")
            elif current_version < self.CURRENT_SCHEMA_VERSION:
                # Run migrations
                self._run_migrations(current_version)
            else:
                logger.info(f"Database schema is up to date (version {current_version})")
            
            conn.commit()
            
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseError(f"Database initialization failed: {e}")
    
    def get_schema_version(self) -> int:
        """
        Get current schema version.
        
        Returns:
            Schema version, 0 if no version table
        """
        conn = self.connect()
        
        try:
            # Check if version table exists
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='schema_version'
            """)
            
            if cursor.fetchone() is None:
                return 0
            
            # Get latest version
            cursor = conn.execute("""
                SELECT MAX(version) as max_version FROM schema_version
            """)
            
            result = cursor.fetchone()
            return result['max_version'] if result and result['max_version'] is not None else 0
            
        except sqlite3.Error as e:
            logger.error(f"Failed to get schema version: {e}")
            return 0
    
    def _set_schema_version(self, version: int, description: str = ""):
        """
        Set schema version.
        
        Args:
            version: Schema version
            description: Version description
        """
        conn = self.connect()
        
        conn.execute("""
            INSERT INTO schema_version (version, description)
            VALUES (?, ?)
        """, (version, description))
    
    def _create_schema_v1(self):
        """
        Create version 1 schema.
        """
        conn = self.connect()
        
        # Save slots table
        conn.execute("""
            CREATE TABLE save_slots (
                slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_played TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                play_time_seconds INTEGER DEFAULT 0,
                character_name TEXT,
                character_class TEXT,
                character_level INTEGER DEFAULT 1,
                world_name TEXT,
                thumbnail_data BLOB,
                is_auto_save BOOLEAN DEFAULT 0,
                is_quick_save BOOLEAN DEFAULT 0,
                metadata_json TEXT DEFAULT '{}',
                UNIQUE(slot_name)
            )
        """)
        
        # Game state table
        conn.execute("""
            CREATE TABLE game_state (
                state_id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot_id INTEGER NOT NULL,
                game_time_seconds REAL DEFAULT 0,
                real_time_seconds REAL DEFAULT 0,
                current_scene TEXT,
                player_entity_id TEXT,
                difficulty TEXT DEFAULT 'normal',
                game_mode TEXT DEFAULT 'singleplayer',
                world_seed INTEGER,
                flags_json TEXT DEFAULT '{}',
                variables_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (slot_id) REFERENCES save_slots(slot_id) ON DELETE CASCADE,
                UNIQUE(slot_id)
            )
        """)
        
        # Entities table
        conn.execute("""
            CREATE TABLE entities (
                entity_id TEXT PRIMARY KEY,
                slot_id INTEGER NOT NULL,
                entity_type TEXT NOT NULL,
                entity_name TEXT,
                position_x REAL DEFAULT 0,
                position_y REAL DEFAULT 0,
                rotation REAL DEFAULT 0,
                scale_x REAL DEFAULT 1,
                scale_y REAL DEFAULT 1,
                is_active BOOLEAN DEFAULT 1,
                is_persistent BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata_json TEXT DEFAULT '{}',
                FOREIGN KEY (slot_id) REFERENCES save_slots(slot_id) ON DELETE CASCADE
            )
        """)
        
        # Components table
        conn.execute("""
            CREATE TABLE components (
                component_id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT NOT NULL,
                slot_id INTEGER NOT NULL,
                component_type TEXT NOT NULL,
                component_data_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE,
                FOREIGN KEY (slot_id) REFERENCES save_slots(slot_id) ON DELETE CASCADE,
                UNIQUE(entity_id, component_type)
            )
        """)
        
        # Inventory table
        conn.execute("""
            CREATE TABLE inventory (
                inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT NOT NULL,
                slot_id INTEGER NOT NULL,
                item_slot INTEGER NOT NULL,
                item_id TEXT NOT NULL,
                item_type TEXT NOT NULL,
                item_name TEXT NOT NULL,
                item_data_json TEXT NOT NULL,
                quantity INTEGER DEFAULT 1,
                is_equipped BOOLEAN DEFAULT 0,
                equipment_slot TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE,
                FOREIGN KEY (slot_id) REFERENCES save_slots(slot_id) ON DELETE CASCADE,
                UNIQUE(entity_id, item_slot)
            )
        """)
        
        # Quests table
        conn.execute("""
            CREATE TABLE quests (
                quest_id TEXT NOT NULL,
                slot_id INTEGER NOT NULL,
                quest_name TEXT NOT NULL,
                quest_state TEXT NOT NULL,
                quest_data_json TEXT NOT NULL,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                objectives_json TEXT DEFAULT '{}',
                rewards_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (quest_id, slot_id),
                FOREIGN KEY (slot_id) REFERENCES save_slots(slot_id) ON DELETE CASCADE
            )
        """)
        
        # World state table
        conn.execute("""
            CREATE TABLE world_state (
                world_state_id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot_id INTEGER NOT NULL,
                region_id TEXT NOT NULL,
                state_key TEXT NOT NULL,
                state_value TEXT NOT NULL,
                state_type TEXT DEFAULT 'string',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (slot_id) REFERENCES save_slots(slot_id) ON DELETE CASCADE,
                UNIQUE(slot_id, region_id, state_key)
            )
        """)
        
        # Create indexes for performance
        conn.execute("CREATE INDEX idx_entities_slot ON entities(slot_id)")
        conn.execute("CREATE INDEX idx_components_entity ON components(entity_id)")
        conn.execute("CREATE INDEX idx_components_slot ON components(slot_id)")
        conn.execute("CREATE INDEX idx_inventory_entity ON inventory(entity_id)")
        conn.execute("CREATE INDEX idx_inventory_slot ON inventory(slot_id)")
        conn.execute("CREATE INDEX idx_quests_slot ON quests(slot_id)")
        conn.execute("CREATE INDEX idx_world_state_slot ON world_state(slot_id)")
        
        logger.info("Created schema version 1")
    
    def _run_migrations(self, from_version: int):
        """
        Run migrations from current version to latest.
        
        Args:
            from_version: Current schema version
        """
        conn = self.connect()
        
        # Migration scripts would go here
        # For now, just update version
        for version in range(from_version + 1, self.CURRENT_SCHEMA_VERSION + 1):
            try:
                # Execute migration for this version
                migration_method = getattr(self, f"_migrate_to_v{version}", None)
                if migration_method:
                    migration_method(conn)
                    self._set_schema_version(version, f"Migrated to version {version}")
                    logger.info(f"Migrated database to version {version}")
                else:
                    logger.warning(f"No migration method for version {version}")
                    
            except Exception as e:
                conn.rollback()
                logger.error(f"Migration to version {version} failed: {e}")
                raise MigrationError(f"Migration failed: {e}")
        
        conn.commit()
    
    def execute_query(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute a SQL query.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Database cursor
        """
        conn = self.connect()
        
        try:
            cursor = conn.execute(query, params)
            return cursor
        except sqlite3.Error as e:
            logger.error(f"Query execution failed: {e}")
            raise DatabaseError(f"Query failed: {e}")
    
    def execute_many(self, query: str, params_list: List[tuple]) -> sqlite3.Cursor:
        """
        Execute a SQL query with multiple parameter sets.
        
        Args:
            query: SQL query string
            params_list: List of parameter tuples
            
        Returns:
            Database cursor
        """
        conn = self.connect()
        
        try:
            cursor = conn.executemany(query, params_list)
            return cursor
        except sqlite3.Error as e:
            logger.error(f"Batch query execution failed: {e}")
            raise DatabaseError(f"Batch query failed: {e}")
    
    def begin_transaction(self):
        """Begin a database transaction."""
        conn = self.connect()
        conn.execute("BEGIN TRANSACTION")
    
    def commit_transaction(self):
        """Commit current transaction."""
        conn = self.connect()
        conn.commit()
    
    def rollback_transaction(self):
        """Rollback current transaction."""
        conn = self.connect()
        conn.rollback()
    
    def backup_database(self, backup_path: str) -> bool:
        """
        Create a backup of the database.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if backup successful
        """
        try:
            # Ensure backup directory exists
            backup_dir = os.path.dirname(backup_path)
            if backup_dir:
                os.makedirs(backup_dir, exist_ok=True)
            
            # Disconnect first to ensure all changes are written
            if self.connection:
                self.connection.commit()
                self.disconnect()
            
            # Copy database file
            import shutil
            shutil.copy2(self.db_path, backup_path)
            
            # Reconnect
            self.connect()
            
            logger.info(f"Database backed up to: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            # Try to reconnect
            try:
                self.connect()
            except:
                pass
            return False
    
    def restore_database(self, backup_path: str) -> bool:
        """
        Restore database from backup.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if restore successful
        """
        if not os.path.exists(backup_path):
            logger.error(f"Backup file not found: {backup_path}")
            return False
        
        try:
            # Disconnect from current database
            if self.connection:
                self.disconnect()
            
            # Remove current database if exists
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
            
            # Copy backup to database location
            import shutil
            shutil.copy2(backup_path, self.db_path)
            
            # Reconnect
            self.connect()
            
            logger.info(f"Database restored from: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            # Try to reconnect
            try:
                self.connect()
            except:
                pass
            return False
    
    def get_database_info(self) -> Dict[str, Any]:
        """
        Get database information.
        
        Returns:
            Dictionary with database info
        """
        conn = self.connect()
        
        info = {
            'path': self.db_path,
            'schema_version': self.get_schema_version(),
            'tables': [],
            'size_bytes': 0
        }
        
        try:
            # Get table information
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            
            tables = cursor.fetchall()
            info['tables'] = [table['name'] for table in tables]
            
            # Get database size
            if os.path.exists(self.db_path):
                info['size_bytes'] = os.path.getsize(self.db_path)
            
            # Get row counts for major tables
            for table in ['save_slots', 'entities', 'components', 'inventory', 'quests']:
                if table in info['tables']:
                    cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")
                    result = cursor.fetchone()
                    info[f'{table}_count'] = result['count'] if result else 0
            
        except sqlite3.Error as e:
            logger.error(f"Failed to get database info: {e}")
        
        return info
    
    def optimize_database(self):
        """
        Optimize database performance.
        """
        conn = self.connect()
        
        try:
            # Vacuum to defragment database
            conn.execute("VACUUM")
            
            # Analyze for query optimization
            conn.execute("ANALYZE")
            
            # Update statistics
            conn.execute("PRAGMA optimize")
            
            logger.info("Database optimized")
            
        except sqlite3.Error as e:
            logger.error(f"Database optimization failed: {e}")
    
    def calculate_checksum(self) -> str:
        """
        Calculate checksum of database file.
        
        Returns:
            MD5 checksum of database file
        """
        if not os.path.exists(self.db_path):
            return ""
        
        try:
            import hashlib
            
            hash_md5 = hashlib.md5()
            with open(self.db_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            
            return hash_md5.hexdigest()
            
        except Exception as e:
            logger.error(f"Failed to calculate checksum: {e}")
            return ""
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()