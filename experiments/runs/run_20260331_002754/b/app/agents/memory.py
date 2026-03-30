"""Persistent memory for agents with key-value storage and similarity search."""

import json
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, func
from sqlalchemy.orm import Session

from app import db
from app.agents.exceptions import MemoryError


logger = logging.getLogger(__name__)


class MemoryType(str, Enum):
    """Types of memory storage."""
    
    NONE = 'none'
    KEY_VALUE = 'key_value'
    SEMANTIC = 'semantic'


# Database model for memory storage
class AgentMemory(db.Model):
    """Database model for storing agent memories."""
    
    __tablename__ = 'agent_memories'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    agent_id = Column(String(100), nullable=False, index=True)
    memory_key = Column(String(200), nullable=False, index=True)
    memory_value = Column(Text, nullable=False)
    embedding = Column(JSON)  # Vector embedding for semantic search
    metadata = Column(JSON)  # Additional metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'agent_id', 'memory_key', name='uq_user_agent_key'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'agent_id': self.agent_id,
            'memory_key': self.memory_key,
            'memory_value': self.memory_value,
            'embedding': self.embedding,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class MemoryStore(ABC):
    """Abstract base class for memory stores."""
    
    @abstractmethod
    def set(self, key: str, value: str, metadata: Optional[Dict] = None) -> None:
        """Store a value with the given key."""
        pass
    
    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Retrieve a value by key."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a value by key."""
        pass
    
    @abstractmethod
    def search(self, query: str, limit: int = 5) -> List[Tuple[str, str, float]]:
        """Search for similar memories.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of (key, value, similarity_score) tuples
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all memories."""
        pass


class KeyValueMemory(MemoryStore):
    """Simple key-value memory store using database."""
    
    def __init__(self, user_id: int, agent_id: str, db_session: Session):
        """Initialize key-value memory store.
        
        Args:
            user_id: User ID
            agent_id: Agent ID
            db_session: Database session
        """
        self.user_id = user_id
        self.agent_id = agent_id
        self.db_session = db_session
    
    def set(self, key: str, value: str, metadata: Optional[Dict] = None) -> None:
        """Store a value with the given key.
        
        Args:
            key: Memory key
            value: Memory value
            metadata: Additional metadata
        """
        try:
            # Check if key already exists
            memory = self.db_session.query(AgentMemory).filter_by(
                user_id=self.user_id,
                agent_id=self.agent_id,
                memory_key=key,
            ).first()
            
            if memory:
                # Update existing
                memory.memory_value = value
                memory.metadata = metadata or {}
                memory.updated_at = datetime.utcnow()
            else:
                # Create new
                memory = AgentMemory(
                    user_id=self.user_id,
                    agent_id=self.agent_id,
                    memory_key=key,
                    memory_value=value,
                    metadata=metadata or {},
                )
                self.db_session.add(memory)
            
            self.db_session.commit()
            logger.debug(f'Stored memory: {key} -> {value[:50]}...')
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f'Failed to store memory: {e}')
            raise MemoryError(f'Failed to store memory: {str(e)}')
    
    def get(self, key: str) -> Optional[str]:
        """Retrieve a value by key.
        
        Args:
            key: Memory key
            
        Returns:
            Memory value or None if not found
        """
        try:
            memory = self.db_session.query(AgentMemory).filter_by(
                user_id=self.user_id,
                agent_id=self.agent_id,
                memory_key=key,
            ).first()
            
            return memory.memory_value if memory else None
            
        except Exception as e:
            logger.error(f'Failed to retrieve memory: {e}')
            raise MemoryError(f'Failed to retrieve memory: {str(e)}')
    
    def delete(self, key: str) -> bool:
        """Delete a value by key.
        
        Args:
            key: Memory key
            
        Returns:
            True if deleted, False if not found
        """
        try:
            result = self.db_session.query(AgentMemory).filter_by(
                user_id=self.user_id,
                agent_id=self.agent_id,
                memory_key=key,
            ).delete()
            
            self.db_session.commit()
            deleted = result > 0
            
            if deleted:
                logger.debug(f'Deleted memory: {key}')
            
            return deleted
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f'Failed to delete memory: {e}')
            raise MemoryError(f'Failed to delete memory: {str(e)}')
    
    def search(self, query: str, limit: int = 5) -> List[Tuple[str, str, float]]:
        """Search for memories containing query text.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of (key, value, similarity_score) tuples
        """
        try:
            # Simple text search in key and value
            memories = self.db_session.query(AgentMemory).filter_by(
                user_id=self.user_id,
                agent_id=self.agent_id,
            ).filter(
                (AgentMemory.memory_key.contains(query)) |
                (AgentMemory.memory_value.contains(query))
            ).limit(limit).all()
            
            results = []
            for memory in memories:
                # Simple similarity score based on occurrence
                key_score = 2.0 if query.lower() in memory.memory_key.lower() else 0.0
                value_score = 1.0 if query.lower() in memory.memory_value.lower() else 0.0
                score = key_score + value_score
                
                if score > 0:
                    results.append((memory.memory_key, memory.memory_value, score))
            
            # Sort by score descending
            results.sort(key=lambda x: x[2], reverse=True)
            
            return results
            
        except Exception as e:
            logger.error(f'Failed to search memories: {e}')
            raise MemoryError(f'Failed to search memories: {str(e)}')
    
    def clear(self) -> None:
        """Clear all memories for this agent."""
        try:
            self.db_session.query(AgentMemory).filter_by(
                user_id=self.user_id,
                agent_id=self.agent_id,
            ).delete()
            
            self.db_session.commit()
            logger.info(f'Cleared all memories for agent {self.agent_id}')
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f'Failed to clear memories: {e}')
            raise MemoryError(f'Failed to clear memories: {str(e)}')
    
    def list_keys(self) -> List[str]:
        """List all memory keys for this agent.
        
        Returns:
            List of memory keys
        """
        try:
            memories = self.db_session.query(AgentMemory).filter_by(
                user_id=self.user_id,
                agent_id=self.agent_id,
            ).all()
            
            return [memory.memory_key for memory in memories]
            
        except Exception as e:
            logger.error(f'Failed to list memory keys: {e}')
            raise MemoryError(f'Failed to list memory keys: {str(e)}')


class SemanticMemory(KeyValueMemory):
    """Memory store with semantic similarity search using embeddings."""
    
    def __init__(
        self,
        user_id: int,
        agent_id: str,
        db_session: Session,
        embedding_model: str = 'all-MiniLM-L6-v2',
    ):
        """Initialize semantic memory store.
        
        Args:
            user_id: User ID
            agent_id: Agent ID
            db_session: Database session
            embedding_model: Name of embedding model to use
        """
        super().__init__(user_id, agent_id, db_session)
        self.embedding_model = embedding_model
        self._embedding_function = None
    
    def _get_embedding_function(self):
        """Lazy load embedding function."""
        if self._embedding_function is None:
            try:
                # Try to import sentence-transformers
                from sentence_transformers import SentenceTransformer
                self._embedding_function = SentenceTransformer(self.embedding_model)
                logger.info(f'Loaded embedding model: {self.embedding_model}')
            except ImportError:
                logger.warning('sentence-transformers not installed, using OpenAI embeddings')
                self._embedding_function = self._get_openai_embedding_function()
        
        return self._embedding_function
    
    def _get_openai_embedding_function(self):
        """Get OpenAI embedding function."""
        try:
            import openai
            openai_client = openai.OpenAI()
            
            def embed(text: str) -> List[float]:
                response = openai_client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=text,
                )
                return response.data[0].embedding
            
            return embed
        except ImportError:
            logger.error('OpenAI not installed, cannot create embeddings')
            raise MemoryError('Embedding model not available')
    
    def _create_embedding(self, text: str) -> List[float]:
        """Create embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        try:
            embed_func = self._get_embedding_function()
            embedding = embed_func(text)
            
            # Convert to list if it's a numpy array
            if hasattr(embedding, 'tolist'):
                embedding = embedding.tolist()
            
            return embedding
        except Exception as e:
            logger.error(f'Failed to create embedding: {e}')
            raise MemoryError(f'Failed to create embedding: {str(e)}')
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity score
        """
        try:
            import numpy as np
            
            v1 = np.array(vec1)
            v2 = np.array(vec2)
            
            dot_product = np.dot(v1, v2)
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return float(dot_product / (norm1 * norm2))
        except Exception as e:
            logger.error(f'Failed to calculate similarity: {e}')
            return 0.0
    
    def set(self, key: str, value: str, metadata: Optional[Dict] = None) -> None:
        """Store a value with embedding.
        
        Args:
            key: Memory key
            value: Memory value
            metadata: Additional metadata
        """
        try:
            # Create embedding for the value
            embedding = self._create_embedding(value)
            
            # Check if key already exists
            memory = self.db_session.query(AgentMemory).filter_by(
                user_id=self.user_id,
                agent_id=self.agent_id,
                memory_key=key,
            ).first()
            
            if memory:
                # Update existing
                memory.memory_value = value
                memory.embedding = embedding
                memory.metadata = metadata or {}
                memory.updated_at = datetime.utcnow()
            else:
                # Create new
                memory = AgentMemory(
                    user_id=self.user_id,
                    agent_id=self.agent_id,
                    memory_key=key,
                    memory_value=value,
                    embedding=embedding,
                    metadata=metadata or {},
                )
                self.db_session.add(memory)
            
            self.db_session.commit()
            logger.debug(f'Stored semantic memory: {key}')
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f'Failed to store semantic memory: {e}')
            raise MemoryError(f'Failed to store semantic memory: {str(e)}')
    
    def search(self, query: str, limit: int = 5) -> List[Tuple[str, str, float]]:
        """Search for semantically similar memories.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of (key, value, similarity_score) tuples
        """
        try:
            # Create embedding for query
            query_embedding = self._create_embedding(query)
            
            # Get all memories for this agent
            memories = self.db_session.query(AgentMemory).filter_by(
                user_id=self.user_id,
                agent_id=self.agent_id,
            ).all()
            
            # Calculate similarities
            results = []
            for memory in memories:
                if memory.embedding:
                    similarity = self._cosine_similarity(query_embedding, memory.embedding)
                    if similarity > 0.1:  # Threshold
                        results.append((memory.memory_key, memory.memory_value, similarity))
            
            # Sort by similarity descending
            results.sort(key=lambda x: x[2], reverse=True)
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f'Failed to search semantic memories: {e}')
            raise MemoryError(f'Failed to search semantic memories: {str(e)}')


class PersistentMemory:
    """Main memory manager that provides appropriate memory store based on type."""
    
    def __init__(
        self,
        user_id: int,
        agent_id: str,
        memory_type: MemoryType = MemoryType.KEY_VALUE,
        db_session: Optional[Session] = None,
        **kwargs,
    ):
        """Initialize persistent memory manager.
        
        Args:
            user_id: User ID
            agent_id: Agent ID
            memory_type: Type of memory store
            db_session: Database session (uses default if None)
            **kwargs: Additional arguments for memory store
        """
        self.user_id = user_id
        self.agent_id = agent_id
        self.memory_type = memory_type
        self.db_session = db_session or db.session
        
        # Initialize appropriate memory store
        if memory_type == MemoryType.NONE:
            self.store = None
        elif memory_type == MemoryType.KEY_VALUE:
            self.store = KeyValueMemory(user_id, agent_id, self.db_session)
        elif memory_type == MemoryType.SEMANTIC:
            embedding_model = kwargs.get('embedding_model', 'all-MiniLM-L6-v2')
            self.store = SemanticMemory(
                user_id, agent_id, self.db_session, embedding_model
            )
        else:
            raise ValueError(f'Unsupported memory type: {memory_type}')
        
        logger.info(f'Initialized {memory_type} memory for agent {agent_id}')
    
    def set(self, key: str, value: str, metadata: Optional[Dict] = None) -> None:
        """Store a memory.
        
        Args:
            key: Memory key
            value: Memory value
            metadata: Additional metadata
        """
        if self.store is None:
            raise MemoryError('Memory store is disabled (type: none)')
        
        self.store.set(key, value, metadata)
    
    def get(self, key: str) -> Optional[str]:
        """Retrieve a memory.
        
        Args:
            key: Memory key
            
        Returns:
            Memory value or None if not found
        """
        if self.store is None:
            raise MemoryError('Memory store is disabled (type: none)')
        
        return self.store.get(key)
    
    def delete(self, key: str) -> bool:
        """Delete a memory.
        
        Args:
            key: Memory key
            
        Returns:
            True if deleted, False if not found
        """
        if self.store is None:
            raise MemoryError('Memory store is disabled (type: none)')
        
        return self.store.delete(key)
    
    def search(self, query: str, limit: int = 5) -> List[Tuple[str, str, float]]:
        """Search memories.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of (key, value, similarity_score) tuples
        """
        if self.store is None:
            return []
        
        return self.store.search(query, limit)
    
    def clear(self) -> None:
        """Clear all memories."""
        if self.store is None:
            raise MemoryError('Memory store is disabled (type: none)')
        
        self.store.clear()
    
    def list_keys(self) -> List[str]:
        """List all memory keys.
        
        Returns:
            List of memory keys
        """
        if self.store is None:
            return []
        
        return self.store.list_keys()
    
    def to_dict(self) -> Dict[str, Any]:
        """Get memory information as dictionary.
        
        Returns:
            Dictionary with memory information
        """
        return {
            'user_id': self.user_id,
            'agent_id': self.agent_id,
            'memory_type': self.memory_type.value,
            'keys_count': len(self.list_keys()) if self.store else 0,
        }