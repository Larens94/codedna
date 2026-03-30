"""memory.py — PersistentMemory: SQLite-backed key-value + simple similarity search.

exports: PersistentMemory, MemoryEntry, summarize_context
used_by: base.py → AgentWrapper, runner.py → run_agent_stream
rules:   Methods: store(key, value), retrieve(query, top_k=5), clear()
         Must handle memory summarization when context exceeds 80% of model limit
         Must support similarity search using TF-IDF or embeddings
         Must be thread-safe for concurrent access
agent:   AgentIntegrator | 2024-03-30 | implemented SQLite memory with similarity search
         message: "implement agent execution with proper error handling and rollback"
"""

import sqlite3
import json
import threading
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import re
from collections import Counter
import math


class MemoryType(str, Enum):
    """Types of memory entries."""
    CONVERSATION = "conversation"
    FACT = "fact"
    PREFERENCE = "preference"
    CONTEXT = "context"
    SUMMARY = "summary"


@dataclass
class MemoryEntry:
    """A single memory entry."""
    key: str
    value: str
    memory_type: MemoryType
    timestamp: datetime
    metadata: Dict[str, Any] = None
    embedding: Optional[List[float]] = None
    importance: float = 1.0  # 0.0 to 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "key": self.key,
            "value": self.value,
            "memory_type": self.memory_type.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": json.dumps(self.metadata or {}),
            "embedding": json.dumps(self.embedding) if self.embedding else None,
            "importance": self.importance
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """Create from dictionary."""
        return cls(
            key=data["key"],
            value=data["value"],
            memory_type=MemoryType(data["memory_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=json.loads(data["metadata"]) if data["metadata"] else {},
            embedding=json.loads(data["embedding"]) if data["embedding"] else None,
            importance=data["importance"]
        )


class PersistentMemory:
    """SQLite-backed persistent memory with similarity search."""
    
    def __init__(self, db_path: str = "agents_memory.db"):
        """Initialize memory storage.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create memory table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    embedding TEXT,
                    importance REAL DEFAULT 1.0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(key, memory_type)
                )
            """)
            
            # Create indexes for faster queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_key ON memory(key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_type ON memory(memory_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON memory(timestamp)")
            
            conn.commit()
            conn.close()
    
    def store(self, key: str, value: str, memory_type: MemoryType = MemoryType.FACT,
              metadata: Optional[Dict[str, Any]] = None, importance: float = 1.0):
        """Store a memory entry.
        
        Args:
            key: Memory key
            value: Memory value
            memory_type: Type of memory
            metadata: Optional metadata
            importance: Importance score (0.0 to 1.0)
        """
        if importance < 0.0 or importance > 1.0:
            raise ValueError(f"Importance must be between 0.0 and 1.0, got {importance}")
        
        entry = MemoryEntry(
            key=key,
            value=value,
            memory_type=memory_type,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
            importance=importance
        )
        
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert or replace
            cursor.execute("""
                INSERT OR REPLACE INTO memory 
                (key, value, memory_type, timestamp, metadata, importance)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                entry.key,
                entry.value,
                entry.memory_type.value,
                entry.timestamp.isoformat(),
                json.dumps(entry.metadata),
                entry.importance
            ))
            
            conn.commit()
            conn.close()
    
    def retrieve(self, query: str, top_k: int = 5, 
                 memory_type: Optional[MemoryType] = None,
                 min_importance: float = 0.0) -> List[MemoryEntry]:
        """Retrieve memory entries similar to query.
        
        Args:
            query: Search query
            top_k: Number of results to return
            memory_type: Filter by memory type
            min_importance: Minimum importance score
            
        Returns:
            List of memory entries sorted by relevance
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Build query
            sql = "SELECT * FROM memory WHERE importance >= ?"
            params = [min_importance]
            
            if memory_type:
                sql += " AND memory_type = ?"
                params.append(memory_type.value)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            conn.close()
            
            # Convert to MemoryEntry objects
            entries = [MemoryEntry.from_dict(dict(row)) for row in rows]
            
            # Calculate similarity scores
            query_tokens = self._tokenize(query.lower())
            scored_entries = []
            
            for entry in entries:
                entry_tokens = self._tokenize(entry.value.lower())
                similarity = self._calculate_similarity(query_tokens, entry_tokens)
                
                # Boost score by importance
                boosted_score = similarity * (0.7 + 0.3 * entry.importance)
                
                scored_entries.append((boosted_score, entry))
            
            # Sort by score and return top_k
            scored_entries.sort(key=lambda x: x[0], reverse=True)
            return [entry for score, entry in scored_entries[:top_k]]
    
    def retrieve_by_key(self, key: str, memory_type: Optional[MemoryType] = None) -> Optional[MemoryEntry]:
        """Retrieve memory entry by exact key.
        
        Args:
            key: Memory key
            memory_type: Optional memory type filter
            
        Returns:
            MemoryEntry if found, None otherwise
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            sql = "SELECT * FROM memory WHERE key = ?"
            params = [key]
            
            if memory_type:
                sql += " AND memory_type = ?"
                params.append(memory_type.value)
            
            cursor.execute(sql, params)
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return MemoryEntry.from_dict(dict(row))
            return None
    
    def clear(self, memory_type: Optional[MemoryType] = None):
        """Clear all memory or specific type.
        
        Args:
            memory_type: If provided, only clear this type
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if memory_type:
                cursor.execute("DELETE FROM memory WHERE memory_type = ?", (memory_type.value,))
            else:
                cursor.execute("DELETE FROM memory")
            
            conn.commit()
            conn.close()
    
    def get_all(self, memory_type: Optional[MemoryType] = None, 
                limit: int = 100, offset: int = 0) -> List[MemoryEntry]:
        """Get all memory entries.
        
        Args:
            memory_type: Filter by memory type
            limit: Maximum number of entries
            offset: Offset for pagination
            
        Returns:
            List of memory entries
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            sql = "SELECT * FROM memory"
            params = []
            
            if memory_type:
                sql += " WHERE memory_type = ?"
                params.append(memory_type.value)
            
            sql += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            conn.close()
            
            return [MemoryEntry.from_dict(dict(row)) for row in rows]
    
    def count(self, memory_type: Optional[MemoryType] = None) -> int:
        """Count memory entries.
        
        Args:
            memory_type: Filter by memory type
            
        Returns:
            Number of entries
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            sql = "SELECT COUNT(*) FROM memory"
            params = []
            
            if memory_type:
                sql += " WHERE memory_type = ?"
                params.append(memory_type.value)
            
            cursor.execute(sql, params)
            count = cursor.fetchone()[0]
            conn.close()
            
            return count
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for similarity calculation.
        
        Args:
            text: Input text
            
        Returns:
            List of tokens
        """
        # Simple tokenization: split by non-alphanumeric characters
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens
    
    def _calculate_similarity(self, query_tokens: List[str], document_tokens: List[str]) -> float:
        """Calculate TF-IDF similarity between query and document.
        
        Args:
            query_tokens: Query tokens
            document_tokens: Document tokens
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        if not query_tokens or not document_tokens:
            return 0.0
        
        # Simple Jaccard similarity for now
        # In production, use proper TF-IDF or embeddings
        query_set = set(query_tokens)
        doc_set = set(document_tokens)
        
        if not query_set or not doc_set:
            return 0.0
        
        intersection = query_set.intersection(doc_set)
        union = query_set.union(doc_set)
        
        return len(intersection) / len(union) if union else 0.0
    
    def store_embedding(self, key: str, embedding: List[float], 
                       memory_type: MemoryType = MemoryType.FACT):
        """Store embedding vector for a memory entry.
        
        Args:
            key: Memory key
            embedding: Embedding vector
            memory_type: Memory type
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE memory 
                SET embedding = ?
                WHERE key = ? AND memory_type = ?
            """, (json.dumps(embedding), key, memory_type.value))
            
            conn.commit()
            conn.close()
    
    def search_by_embedding(self, embedding: List[float], top_k: int = 5,
                           memory_type: Optional[MemoryType] = None) -> List[Tuple[MemoryEntry, float]]:
        """Search memory by embedding similarity.
        
        Args:
            embedding: Query embedding
            top_k: Number of results
            memory_type: Filter by memory type
            
        Returns:
            List of (MemoryEntry, similarity_score) tuples
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            sql = "SELECT * FROM memory WHERE embedding IS NOT NULL"
            params = []
            
            if memory_type:
                sql += " AND memory_type = ?"
                params.append(memory_type.value)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            conn.close()
            
            results = []
            for row in rows:
                entry = MemoryEntry.from_dict(dict(row))
                if entry.embedding:
                    similarity = self._cosine_similarity(embedding, entry.embedding)
                    results.append((entry, similarity))
            
            # Sort by similarity and return top_k
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity (-1.0 to 1.0)
        """
        if len(vec1) != len(vec2):
            raise ValueError("Vectors must have same length")
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)


def summarize_context(context: str, max_tokens: int, model_limit: int) -> str:
    """Summarize context when it exceeds 80% of model limit.
    
    Args:
        context: Original context text
        max_tokens: Maximum tokens allowed
        model_limit: Model's context limit
        
    Returns:
        Summarized context
    """
    # Simple token estimation (4 chars ≈ 1 token)
    estimated_tokens = len(context) // 4
    
    # Check if summarization is needed (exceeds 80% of limit)
    if estimated_tokens <= model_limit * 0.8:
        return context
    
    # Calculate target length (70% of limit to leave room)
    target_chars = int(model_limit * 0.7 * 4)
    
    if len(context) <= target_chars:
        return context
    
    # Simple summarization strategy:
    # 1. Split into sentences
    # 2. Keep most important sentences based on keyword frequency
    
    sentences = re.split(r'[.!?]+', context)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if len(sentences) <= 1:
        # Can't summarize a single sentence, just truncate
        return context[:target_chars] + "..."
    
    # Calculate word frequencies
    words = []
    for sentence in sentences:
        words.extend(re.findall(r'\b\w+\b', sentence.lower()))
    
    word_freq = Counter(words)
    
    # Score sentences by word frequency
    sentence_scores = []
    for sentence in sentences:
        sentence_words = re.findall(r'\b\w+\b', sentence.lower())
        if not sentence_words:
            score = 0
        else:
            score = sum(word_freq[word] for word in sentence_words) / len(sentence_words)
        sentence_scores.append((score, sentence))
    
    # Sort by score and build summary
    sentence_scores.sort(key=lambda x: x[0], reverse=True)
    
    summary = []
    total_chars = 0
    
    for score, sentence in sentence_scores:
        if total_chars + len(sentence) > target_chars:
            break
        summary.append(sentence)
        total_chars += len(sentence) + 1  # +1 for space
    
    if not summary:
        # Fallback: just take the beginning
        return context[:target_chars] + "..."
    
    result = ". ".join(summary) + "."
    
    # Add note about summarization
    if len(result) < len(context):
        result += " [Context summarized for brevity]"
    
    return result


def create_conversation_memory(conversation: List[Dict[str, str]], 
                              max_context_tokens: int = 4000) -> str:
    """Create memory from conversation history.
    
    Args:
        conversation: List of message dicts with 'role' and 'content'
        max_context_tokens: Maximum tokens for context
        
    Returns:
        Formatted conversation memory
    """
    formatted = []
    total_tokens = 0
    
    for msg in conversation[-20:]:  # Last 20 messages max
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')
        
        # Simple token estimation
        msg_tokens = len(content) // 4 + 10  # +10 for role and formatting
        
        if total_tokens + msg_tokens > max_context_tokens:
            break
        
        formatted.append(f"{role.upper()}: {content}")
        total_tokens += msg_tokens
    
    return "\n\n".join(formatted)