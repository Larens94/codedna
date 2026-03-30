"""Memory models for agent memory storage with vector embeddings."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, JSON, BLOB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app import db


class MemoryType(enum.Enum):
    """Memory type enumeration."""
    
    SHORT_TERM = 'short_term'
    LONG_TERM = 'long_term'
    EPISODIC = 'episodic'
    SEMANTIC = 'semantic'


class MemoryImportance(enum.Enum):
    """Memory importance level."""
    
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class Memory(db.Model):
    """Memory model for agent memory storage.
    
    Attributes:
        id: Primary key
        agent_id: Foreign key to agent (if agent-specific memory)
        user_id: Foreign key to user (if user-specific memory)
        organization_id: Foreign key to organization (if org memory)
        memory_type: Type of memory
        content: Memory content text
        embedding: Vector embedding (BLOB) for similarity search
        embedding_dim: Dimension of embedding vector
        importance: Memory importance level
        metadata: Additional metadata (JSON)
        access_count: Number of times memory has been accessed
        last_accessed: Last access timestamp
        expires_at: Optional expiration timestamp
        created_at: Creation timestamp
        updated_at: Last update timestamp
        agent: Associated agent
        user: Associated user
        organization: Associated organization
    """
    
    __tablename__ = 'memories'
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey('agents.id', ondelete='CASCADE'))
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'))
    memory_type = Column(Enum(MemoryType), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(BLOB)  # Vector embedding for similarity search
    embedding_dim = Column(Integer)  # Dimension of embedding vector
    importance = Column(Enum(MemoryImportance), default=MemoryImportance.MEDIUM)
    metadata = Column(JSON)  # JSON metadata
    access_count = Column(Integer, default=0)
    last_accessed = Column(DateTime)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        db.Index('ix_memories_agent_user_type', 'agent_id', 'user_id', 'memory_type'),
        db.Index('ix_memories_created_at', 'created_at'),
        db.Index('ix_memories_expires_at', 'expires_at'),
    )
    
    # Relationships
    agent = relationship('Agent')
    user = relationship('User')
    organization = relationship('Organization')
    
    def get_metadata_dict(self) -> Dict[str, Any]:
        """Get metadata as dictionary.
        
        Returns:
            Metadata dictionary
        """
        return self.metadata or {}
    
    def update_metadata(self, updates: Dict[str, Any]) -> None:
        """Update metadata with new values.
        
        Args:
            updates: Dictionary of metadata updates
        """
        current = self.get_metadata_dict()
        current.update(updates)
        self.metadata = current
    
    def record_access(self) -> None:
        """Record memory access."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
    
    def is_expired(self) -> bool:
        """Check if memory has expired.
        
        Returns:
            True if expired, False otherwise
        """
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def get_embedding_vector(self) -> Optional[List[float]]:
        """Decode embedding from BLOB to list of floats.
        
        Returns:
            List of floats or None if no embedding
        """
        if not self.embedding:
            return None
        
        import struct
        # Assuming embedding is stored as little-endian floats
        return list(struct.unpack(f'{self.embedding_dim}f', self.embedding))
    
    def set_embedding_vector(self, vector: List[float]) -> None:
        """Encode embedding vector to BLOB.
        
        Args:
            vector: List of floats
        """
        import struct
        self.embedding_dim = len(vector)
        self.embedding = struct.pack(f'{len(vector)}f', *vector)
    
    def to_dict(self, include_embedding: bool = False) -> Dict[str, Any]:
        """Convert memory to dictionary representation.
        
        Args:
            include_embedding: Whether to include embedding vector
            
        Returns:
            Dictionary representation of memory
        """
        data = {
            'id': self.id,
            'agent_id': self.agent_id,
            'user_id': self.user_id,
            'organization_id': self.organization_id,
            'memory_type': self.memory_type.value if self.memory_type else None,
            'content': self.content,
            'importance': self.importance.value if self.importance else None,
            'metadata': self.get_metadata_dict(),
            'access_count': self.access_count,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_expired': self.is_expired(),
        }
        
        if include_embedding:
            data['embedding'] = self.get_embedding_vector()
            data['embedding_dim'] = self.embedding_dim
        
        return data
    
    def __repr__(self) -> str:
        return f'<Memory {self.id} ({self.memory_type.value}): {self.content[:50]}...>'


class MemoryAssociation(db.Model):
    """Association between memories for creating memory graphs.
    
    Attributes:
        id: Primary key
        source_memory_id: Foreign key to source memory
        target_memory_id: Foreign key to target memory
        association_type: Type of association
        strength: Association strength (0.0-1.0)
        metadata: Additional metadata (JSON)
        created_at: Creation timestamp
    """
    
    __tablename__ = 'memory_associations'
    
    id = Column(Integer, primary_key=True)
    source_memory_id = Column(Integer, ForeignKey('memories.id', ondelete='CASCADE'), nullable=False)
    target_memory_id = Column(Integer, ForeignKey('memories.id', ondelete='CASCADE'), nullable=False)
    association_type = Column(String(50))  # e.g., 'similar', 'related', 'causal', 'temporal'
    strength = Column(Float, default=0.5)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    source_memory = relationship('Memory', foreign_keys=[source_memory_id])
    target_memory = relationship('Memory', foreign_keys=[target_memory_id])
    
    def __repr__(self) -> str:
        return f'<MemoryAssociation {self.source_memory_id} -> {self.target_memory_id} ({self.association_type})>'