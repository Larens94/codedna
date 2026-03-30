"""app/agents/memory_manager.py — Persistent memory with key-value storage and similarity search.

exports: MemoryManager, MemoryEntry, VectorMemory
used_by: app/agents/agent_wrapper.py → memory persistence, app/agents/agent_builder.py → memory configuration
rules:   Memory must be isolated per organization/agent; vector embeddings enable semantic search
agent:   AgentIntegrator | 2024-12-05 | implemented persistent memory with similarity search
         message: "implement memory summarization for long conversations"
"""

import logging
import json
import sqlite3
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import hashlib
import pickle

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """Memory entry with metadata."""
    key: str
    value: str
    embedding: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = None
    created_at: datetime = None
    accessed_at: datetime = None
    access_count: int = 0
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.accessed_at is None:
            self.accessed_at = self.created_at


class VectorMemory:
    """Vector memory for semantic search using embeddings."""
    
    def __init__(self, dimension: int = 384):
        """Initialize vector memory.
        
        Args:
            dimension: Embedding dimension
        """
        self.dimension = dimension
        self.embeddings: List[np.ndarray] = []
        self.entries: List[MemoryEntry] = []
    
    def add(self, entry: MemoryEntry) -> None:
        """Add entry with embedding.
        
        Args:
            entry: Memory entry with embedding
        """
        if entry.embedding is None:
            raise ValueError("Entry must have embedding for vector memory")
        
        if len(entry.embedding) != self.dimension:
            raise ValueError(f"Embedding dimension mismatch: expected {self.dimension}, got {len(entry.embedding)}")
        
        self.embeddings.append(entry.embedding)
        self.entries.append(entry)
    
    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Tuple[MemoryEntry, float]]:
        """Search for similar entries using cosine similarity.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            
        Returns:
            List of (entry, similarity_score) tuples
        """
        if not self.embeddings:
            return []
        
        # Convert to numpy array
        embeddings_array = np.array(self.embeddings)
        query_array = np.array(query_embedding)
        
        # Calculate cosine similarity
        # Normalize embeddings
        norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
        embeddings_norm = embeddings_array / np.maximum(norms, 1e-10)
        
        query_norm = query_array / np.maximum(np.linalg.norm(query_array), 1e-10)
        
        similarities = np.dot(embeddings_norm, query_norm)
        
        # Get top_k indices
        if top_k > len(similarities):
            top_k = len(similarities)
        
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        return [(self.entries[i], float(similarities[i])) for i in top_indices]
    
    def clear(self) -> None:
        """Clear all entries."""
        self.embeddings = []
        self.entries = []


class MemoryManager:
    """Persistent memory manager with key-value storage and similarity search.
    
    Rules:
        Memory is isolated by namespace (org_id + agent_id)
        Supports key-value lookup and semantic search
        Automatically manages SQLite connections
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize memory manager.
        
        Args:
            db_path: Path to SQLite database file (default: in-memory)
        """
        self.db_path = db_path or ":memory:"
        self._init_database()
        
        # In-memory vector stores per namespace
        self.vector_stores: Dict[str, VectorMemory] = {}
    
    def _init_database(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_entries (
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    embedding BLOB,
                    metadata TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    accessed_at TIMESTAMP NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    PRIMARY KEY (namespace, key)
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_namespace ON memory_entries (namespace)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at ON memory_entries (created_at)
            """)
            
            conn.commit()
    
    def _get_namespace(self, organization_id: str, agent_id: Optional[str] = None) -> str:
        """Get namespace for organization and agent.
        
        Args:
            organization_id: Organization identifier
            agent_id: Optional agent identifier
            
        Returns:
            Namespace string
        """
        if agent_id:
            return f"{organization_id}:{agent_id}"
        return organization_id
    
    def store(
        self,
        organization_id: str,
        key: str,
        value: str,
        agent_id: Optional[str] = None,
        embedding: Optional[np.ndarray] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store value in memory.
        
        Args:
            organization_id: Organization identifier
            key: Memory key
            value: Memory value
            agent_id: Optional agent identifier for isolation
            embedding: Optional embedding vector for semantic search
            metadata: Optional metadata dictionary
        """
        namespace = self._get_namespace(organization_id, agent_id)
        now = datetime.now()
        
        # Prepare data for database
        embedding_blob = None
        if embedding is not None:
            embedding_blob = pickle.dumps(embedding)
        
        metadata_json = json.dumps(metadata or {})
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memory_entries 
                (namespace, key, value, embedding, metadata, created_at, accessed_at, access_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                namespace,
                key,
                value,
                embedding_blob,
                metadata_json,
                now.isoformat(),
                now.isoformat(),
                0,  # Will be incremented on access
            ))
            
            conn.commit()
        
        # Update vector store if embedding provided
        if embedding is not None:
            if namespace not in self.vector_stores:
                dimension = len(embedding) if embedding is not None else 384
                self.vector_stores[namespace] = VectorMemory(dimension=dimension)
            
            entry = MemoryEntry(
                key=key,
                value=value,
                embedding=embedding,
                metadata=metadata or {},
                created_at=now,
                accessed_at=now,
            )
            self.vector_stores[namespace].add(entry)
        
        logger.info(f"Stored memory entry: {namespace}/{key}")
    
    def retrieve(
        self,
        organization_id: str,
        key: str,
        agent_id: Optional[str] = None,
    ) -> Optional[MemoryEntry]:
        """Retrieve value from memory by key.
        
        Args:
            organization_id: Organization identifier
            key: Memory key
            agent_id: Optional agent identifier
            
        Returns:
            MemoryEntry if found, None otherwise
        """
        namespace = self._get_namespace(organization_id, agent_id)
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT value, embedding, metadata, created_at, accessed_at, access_count
                FROM memory_entries
                WHERE namespace = ? AND key = ?
            """, (namespace, key))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            value, embedding_blob, metadata_json, created_at_str, accessed_at_str, access_count = row
            
            # Update access info
            conn.execute("""
                UPDATE memory_entries
                SET accessed_at = ?, access_count = access_count + 1
                WHERE namespace = ? AND key = ?
            """, (now.isoformat(), namespace, key))
            conn.commit()
            
            # Parse data
            embedding = None
            if embedding_blob:
                embedding = pickle.loads(embedding_blob)
            
            metadata = json.loads(metadata_json)
            created_at = datetime.fromisoformat(created_at_str)
            accessed_at = datetime.fromisoformat(accessed_at_str)
            
            return MemoryEntry(
                key=key,
                value=value,
                embedding=embedding,
                metadata=metadata,
                created_at=created_at,
                accessed_at=accessed_at,
                access_count=access_count + 1,
            )
    
    def retrieve_similar(
        self,
        organization_id: str,
        query_embedding: np.ndarray,
        top_k: int = 5,
        agent_id: Optional[str] = None,
        min_similarity: float = 0.0,
    ) -> List[Tuple[MemoryEntry, float]]:
        """Retrieve similar memories using semantic search.
        
        Args:
            organization_id: Organization identifier
            query_embedding: Query embedding vector
            top_k: Number of results to return
            agent_id: Optional agent identifier
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of (MemoryEntry, similarity_score) tuples
        """
        namespace = self._get_namespace(organization_id, agent_id)
        
        if namespace not in self.vector_stores:
            # Try to load from database
            self._load_vector_store(namespace)
        
        if namespace not in self.vector_stores:
            return []
        
        results = self.vector_stores[namespace].search(query_embedding, top_k)
        
        # Filter by similarity threshold
        filtered = [(entry, score) for entry, score in results if score >= min_similarity]
        
        # Update access counts for retrieved entries
        now = datetime.now()
        with sqlite3.connect(self.db_path) as conn:
            for entry, _ in filtered:
                conn.execute("""
                    UPDATE memory_entries
                    SET accessed_at = ?, access_count = access_count + 1
                    WHERE namespace = ? AND key = ?
                """, (now.isoformat(), namespace, entry.key))
            conn.commit()
        
        return filtered
    
    def _load_vector_store(self, namespace: str) -> None:
        """Load vector store from database for namespace.
        
        Args:
            namespace: Namespace to load
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT key, value, embedding, metadata, created_at, accessed_at, access_count
                FROM memory_entries
                WHERE namespace = ?
                AND embedding IS NOT NULL
            """, (namespace,))
            
            rows = cursor.fetchall()
            if not rows:
                return
            
            # Determine dimension from first embedding
            first_embedding = pickle.loads(rows[0][2])
            dimension = len(first_embedding)
            
            vector_store = VectorMemory(dimension=dimension)
            
            for row in rows:
                key, value, embedding_blob, metadata_json, created_at_str, accessed_at_str, access_count = row
                
                embedding = pickle.loads(embedding_blob)
                metadata = json.loads(metadata_json)
                created_at = datetime.fromisoformat(created_at_str)
                accessed_at = datetime.fromisoformat(accessed_at_str)
                
                entry = MemoryEntry(
                    key=key,
                    value=value,
                    embedding=embedding,
                    metadata=metadata,
                    created_at=created_at,
                    accessed_at=accessed_at,
                    access_count=access_count,
                )
                vector_store.add(entry)
            
            self.vector_stores[namespace] = vector_store
        
        logger.info(f"Loaded vector store for namespace '{namespace}' with {len(rows)} entries")
    
    def delete(
        self,
        organization_id: str,
        key: str,
        agent_id: Optional[str] = None,
    ) -> bool:
        """Delete memory entry by key.
        
        Args:
            organization_id: Organization identifier
            key: Memory key
            agent_id: Optional agent identifier
            
        Returns:
            True if deleted, False if not found
        """
        namespace = self._get_namespace(organization_id, agent_id)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM memory_entries
                WHERE namespace = ? AND key = ?
            """, (namespace, key))
            
            deleted = cursor.rowcount > 0
            conn.commit()
        
        # Remove from vector store if present
        if namespace in self.vector_stores:
            # Recreate vector store without the deleted entry
            self._load_vector_store(namespace)
        
        logger.info(f"Deleted memory entry: {namespace}/{key}" if deleted else f"Memory entry not found: {namespace}/{key}")
        return deleted
    
    def clear(
        self,
        organization_id: str,
        agent_id: Optional[str] = None,
    ) -> int:
        """Clear all memories for organization/agent.
        
        Args:
            organization_id: Organization identifier
            agent_id: Optional agent identifier
            
        Returns:
            Number of entries deleted
        """
        namespace = self._get_namespace(organization_id, agent_id)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM memory_entries
                WHERE namespace = ?
            """, (namespace,))
            
            deleted_count = cursor.rowcount
            conn.commit()
        
        # Clear vector store
        if namespace in self.vector_stores:
            del self.vector_stores[namespace]
        
        logger.info(f"Cleared {deleted_count} memory entries for namespace '{namespace}'")
        return deleted_count
    
    def list_keys(
        self,
        organization_id: str,
        agent_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[str]:
        """List memory keys for organization/agent.
        
        Args:
            organization_id: Organization identifier
            agent_id: Optional agent identifier
            limit: Maximum number of keys to return
            offset: Offset for pagination
            
        Returns:
            List of keys
        """
        namespace = self._get_namespace(organization_id, agent_id)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT key FROM memory_entries
                WHERE namespace = ?
                ORDER BY accessed_at DESC
                LIMIT ? OFFSET ?
            """, (namespace, limit, offset))
            
            keys = [row[0] for row in cursor.fetchall()]
        
        return keys
    
    def get_stats(
        self,
        organization_id: str,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get memory statistics.
        
        Args:
            organization_id: Organization identifier
            agent_id: Optional agent identifier
            
        Returns:
            Statistics dictionary
        """
        namespace = self._get_namespace(organization_id, agent_id)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_entries,
                    COUNT(embedding) as vector_entries,
                    SUM(LENGTH(value)) as total_size,
                    AVG(access_count) as avg_access_count,
                    MAX(accessed_at) as last_accessed
                FROM memory_entries
                WHERE namespace = ?
            """, (namespace,))
            
            row = cursor.fetchone()
        
        if not row or row[0] == 0:
            return {
                "total_entries": 0,
                "vector_entries": 0,
                "total_size_bytes": 0,
                "avg_access_count": 0,
                "last_accessed": None,
            }
        
        return {
            "total_entries": row[0],
            "vector_entries": row[1],
            "total_size_bytes": row[2] or 0,
            "avg_access_count": row[3] or 0,
            "last_accessed": row[4],
        }


# Global memory manager instance
memory_manager = MemoryManager()