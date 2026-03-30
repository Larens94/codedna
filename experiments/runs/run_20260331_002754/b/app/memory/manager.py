"""Memory manager for agent memories with vector similarity search."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models.memory import Memory, MemoryType, MemoryImportance, MemoryAssociation
from app.models.agent import Agent
from app.models.user import User
from app.memory.vector_store import VectorStore, EmbeddingService, EmbeddingModel

logger = logging.getLogger(__name__)


class MemoryManagerError(Exception):
    """Base exception for memory manager errors."""
    pass


class MemoryManager:
    """Memory manager for agent memories with vector similarity search."""
    
    def __init__(self, db_session: Session, vector_store: Optional[VectorStore] = None):
        """Initialize memory manager.
        
        Args:
            db_session: SQLAlchemy database session
            vector_store: VectorStore instance (optional, creates default if not provided)
        """
        self.db = db_session
        self.vector_store = vector_store or VectorStore()
        self.embedding_service = None  # Lazy initialization
    
    def _get_embedding_service(self) -> EmbeddingService:
        """Get or create embedding service.
        
        Returns:
            EmbeddingService instance
        """
        if self.embedding_service is None:
            # TODO: Get API key from config
            from app.core.config import settings
            api_key = getattr(settings, 'OPENAI_API_KEY', None)
            
            self.embedding_service = EmbeddingService(
                model=EmbeddingModel.TEXT_EMBEDDING_ADA_002,
                api_key=api_key,
            )
        
        return self.embedding_service
    
    def create_memory(
        self,
        content: str,
        memory_type: MemoryType,
        agent_id: Optional[int] = None,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        importance: MemoryImportance = MemoryImportance.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None,
        expires_in_days: Optional[int] = None,
        generate_embedding: bool = True,
    ) -> Optional[Memory]:
        """Create a new memory.
        
        Args:
            content: Memory content text
            memory_type: Type of memory
            agent_id: Optional agent ID
            user_id: Optional user ID
            organization_id: Optional organization ID
            importance: Memory importance level
            metadata: Additional metadata
            expires_in_days: Days until memory expires
            generate_embedding: Whether to generate embedding
            
        Returns:
            Memory instance or None if failed
        """
        try:
            # Calculate expiration date
            expires_at = None
            if expires_in_days:
                expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
            
            # Create memory
            memory = Memory(
                content=content,
                memory_type=memory_type,
                agent_id=agent_id,
                user_id=user_id,
                organization_id=organization_id,
                importance=importance,
                metadata=metadata or {},
                expires_at=expires_at,
            )
            
            self.db.add(memory)
            self.db.commit()
            self.db.refresh(memory)
            
            # Generate and store embedding
            if generate_embedding:
                self._generate_and_store_embedding(memory)
            
            logger.info(f"Created memory {memory.id} of type {memory_type.value}")
            return memory
            
        except Exception as e:
            logger.error(f"Failed to create memory: {e}")
            self.db.rollback()
            return None
    
    def _generate_and_store_embedding(self, memory: Memory) -> bool:
        """Generate and store embedding for memory.
        
        Args:
            memory: Memory instance
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate embedding
            embedding_service = self._get_embedding_service()
            embedding = embedding_service.generate_embedding(memory.content)
            
            if embedding is None:
                logger.warning(f"Failed to generate embedding for memory {memory.id}")
                return False
            
            # Store embedding in vector store
            success = self.vector_store.add_embedding(
                memory_id=memory.id,
                embedding=embedding,
                agent_id=memory.agent_id,
                user_id=memory.user_id,
                organization_id=memory.organization_id,
            )
            
            if success:
                # Update memory with embedding dimension
                memory.embedding_dim = len(embedding)
                self.db.commit()
                logger.debug(f"Stored embedding for memory {memory.id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to generate/store embedding for memory {memory.id}: {e}")
            return False
    
    def get_memory(self, memory_id: int) -> Optional[Memory]:
        """Get memory by ID.
        
        Args:
            memory_id: Memory ID
            
        Returns:
            Memory instance or None if not found
        """
        try:
            memory = self.db.query(Memory).get(memory_id)
            if memory:
                memory.record_access()
                self.db.commit()
            
            return memory
            
        except Exception as e:
            logger.error(f"Failed to get memory {memory_id}: {e}")
            return None
    
    def update_memory(
        self,
        memory_id: int,
        content: Optional[str] = None,
        importance: Optional[MemoryImportance] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_in_days: Optional[int] = None,
    ) -> Optional[Memory]:
        """Update memory.
        
        Args:
            memory_id: Memory ID
            content: New content (optional)
            importance: New importance (optional)
            metadata: New metadata (optional)
            expires_in_days: New expiration in days (optional)
            
        Returns:
            Updated Memory instance or None if failed
        """
        try:
            memory = self.db.query(Memory).get(memory_id)
            if not memory:
                return None
            
            # Update fields
            if content is not None:
                memory.content = content
                # Regenerate embedding if content changed
                self._generate_and_store_embedding(memory)
            
            if importance is not None:
                memory.importance = importance
            
            if metadata is not None:
                memory.update_metadata(metadata)
            
            if expires_in_days is not None:
                if expires_in_days == 0:
                    memory.expires_at = None
                else:
                    memory.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
            
            memory.updated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Updated memory {memory_id}")
            return memory
            
        except Exception as e:
            logger.error(f"Failed to update memory {memory_id}: {e}")
            self.db.rollback()
            return None
    
    def delete_memory(self, memory_id: int) -> bool:
        """Delete memory.
        
        Args:
            memory_id: Memory ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            memory = self.db.query(Memory).get(memory_id)
            if not memory:
                return False
            
            # Delete from vector store
            self.vector_store.delete_embedding(memory_id)
            
            # Delete from database
            self.db.delete(memory)
            self.db.commit()
            
            logger.info(f"Deleted memory {memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            self.db.rollback()
            return False
    
    def search_memories(
        self,
        query: str,
        limit: int = 10,
        agent_id: Optional[int] = None,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        memory_type: Optional[MemoryType] = None,
        threshold: float = 0.7,
        include_expired: bool = False,
    ) -> List[Dict[str, Any]]:
        """Search memories by semantic similarity.
        
        Args:
            query: Search query text
            limit: Maximum number of results
            agent_id: Filter by agent ID
            user_id: Filter by user ID
            organization_id: Filter by organization ID
            memory_type: Filter by memory type
            threshold: Similarity threshold (0.0 to 1.0)
            include_expired: Whether to include expired memories
            
        Returns:
            List of memories with similarity scores
        """
        try:
            # Generate embedding for query
            embedding_service = self._get_embedding_service()
            query_embedding = embedding_service.generate_embedding(query)
            
            if query_embedding is None:
                logger.warning("Failed to generate query embedding")
                return []
            
            # Search similar embeddings
            similar_results = self.vector_store.search_similar(
                query_embedding=query_embedding,
                limit=limit * 2,  # Get extra to filter by type
                agent_id=agent_id,
                user_id=user_id,
                organization_id=organization_id,
                threshold=threshold,
            )
            
            # Get full memory objects for results
            results = []
            memory_ids = [r['memory_id'] for r in similar_results]
            
            if not memory_ids:
                return results
            
            # Query memories
            query_filter = Memory.id.in_(memory_ids)
            
            if memory_type:
                query_filter = and_(query_filter, Memory.memory_type == memory_type)
            
            if not include_expired:
                query_filter = and_(
                    query_filter,
                    or_(
                        Memory.expires_at == None,
                        Memory.expires_at > datetime.utcnow(),
                    )
                )
            
            memories = self.db.query(Memory).filter(query_filter).all()
            
            # Map memories by ID for quick lookup
            memory_map = {memory.id: memory for memory in memories}
            
            # Combine similarity scores with memory data
            for similar_result in similar_results:
                memory_id = similar_result['memory_id']
                if memory_id in memory_map:
                    memory = memory_map[memory_id]
                    
                    # Record access
                    memory.record_access()
                    
                    results.append({
                        'memory': memory.to_dict(),
                        'similarity': similar_result['similarity'],
                        'distance': similar_result['distance'],
                    })
                    
                    # Stop when we have enough results
                    if len(results) >= limit:
                        break
            
            self.db.commit()
            
            # Sort by similarity (descending)
            results.sort(key=lambda x: x['similarity'], reverse=True)
            
            logger.debug(f"Found {len(results)} similar memories for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []
    
    def get_memories(
        self,
        agent_id: Optional[int] = None,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        memory_type: Optional[MemoryType] = None,
        importance: Optional[MemoryImportance] = None,
        limit: int = 100,
        offset: int = 0,
        include_expired: bool = False,
    ) -> List[Memory]:
        """Get memories with filters.
        
        Args:
            agent_id: Filter by agent ID
            user_id: Filter by user ID
            organization_id: Filter by organization ID
            memory_type: Filter by memory type
            importance: Filter by importance
            limit: Maximum number of memories to return
            offset: Offset for pagination
            include_expired: Whether to include expired memories
            
        Returns:
            List of Memory instances
        """
        try:
            query = self.db.query(Memory)
            
            # Apply filters
            if agent_id is not None:
                query = query.filter_by(agent_id=agent_id)
            
            if user_id is not None:
                query = query.filter_by(user_id=user_id)
            
            if organization_id is not None:
                query = query.filter_by(organization_id=organization_id)
            
            if memory_type is not None:
                query = query.filter_by(memory_type=memory_type)
            
            if importance is not None:
                query = query.filter_by(importance=importance)
            
            if not include_expired:
                query = query.filter(
                    or_(
                        Memory.expires_at == None,
                        Memory.expires_at > datetime.utcnow(),
                    )
                )
            
            # Apply ordering and pagination
            memories = query.order_by(
                Memory.importance.desc(),
                Memory.access_count.desc(),
                Memory.created_at.desc(),
            ).offset(offset).limit(limit).all()
            
            # Record access for retrieved memories
            for memory in memories:
                memory.record_access()
            
            self.db.commit()
            
            return memories
            
        except Exception as e:
            logger.error(f"Failed to get memories: {e}")
            return []
    
    def create_association(
        self,
        source_memory_id: int,
        target_memory_id: int,
        association_type: str = 'related',
        strength: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[MemoryAssociation]:
        """Create association between memories.
        
        Args:
            source_memory_id: Source memory ID
            target_memory_id: Target memory ID
            association_type: Type of association
            strength: Association strength (0.0-1.0)
            metadata: Additional metadata
            
        Returns:
            MemoryAssociation instance or None if failed
        """
        try:
            # Check if memories exist
            source = self.db.query(Memory).get(source_memory_id)
            target = self.db.query(Memory).get(target_memory_id)
            
            if not source or not target:
                return None
            
            # Create association
            association = MemoryAssociation(
                source_memory_id=source_memory_id,
                target_memory_id=target_memory_id,
                association_type=association_type,
                strength=strength,
                metadata=metadata or {},
            )
            
            self.db.add(association)
            self.db.commit()
            
            logger.debug(f"Created association {source_memory_id} -> {target_memory_id} ({association_type})")
            return association
            
        except Exception as e:
            logger.error(f"Failed to create memory association: {e}")
            self.db.rollback()
            return None
    
    def get_associated_memories(
        self,
        memory_id: int,
        association_type: Optional[str] = None,
        min_strength: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """Get memories associated with a memory.
        
        Args:
            memory_id: Memory ID
            association_type: Filter by association type
            min_strength: Minimum association strength
            
        Returns:
            List of associated memories with association details
        """
        try:
            query = self.db.query(MemoryAssociation).filter(
                or_(
                    MemoryAssociation.source_memory_id == memory_id,
                    MemoryAssociation.target_memory_id == memory_id,
                ),
                MemoryAssociation.strength >= min_strength,
            )
            
            if association_type:
                query = query.filter_by(association_type=association_type)
            
            associations = query.all()
            
            results = []
            for assoc in associations:
                # Determine direction
                if assoc.source_memory_id == memory_id:
                    direction = 'outgoing'
                    other_memory_id = assoc.target_memory_id
                else:
                    direction = 'incoming'
                    other_memory_id = assoc.source_memory_id
                
                # Get other memory
                other_memory = self.db.query(Memory).get(other_memory_id)
                if other_memory:
                    results.append({
                        'association': {
                            'id': assoc.id,
                            'type': assoc.association_type,
                            'strength': assoc.strength,
                            'direction': direction,
                            'metadata': assoc.metadata or {},
                            'created_at': assoc.created_at.isoformat() if assoc.created_at else None,
                        },
                        'memory': other_memory.to_dict(),
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get associated memories for {memory_id}: {e}")
            return []
    
    def cleanup_expired_memories(self) -> int:
        """Clean up expired memories.
        
        Returns:
            Number of memories cleaned up
        """
        try:
            # Find expired memories
            expired_memories = self.db.query(Memory).filter(
                Memory.expires_at != None,
                Memory.expires_at <= datetime.utcnow(),
            ).all()
            
            count = 0
            for memory in expired_memories:
                # Delete from vector store
                self.vector_store.delete_embedding(memory.id)
                
                # Delete from database
                self.db.delete(memory)
                count += 1
            
            self.db.commit()
            
            logger.info(f"Cleaned up {count} expired memories")
            return count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired memories: {e}")
            self.db.rollback()
            return 0
    
    def get_memory_stats(
        self,
        agent_id: Optional[int] = None,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get memory statistics.
        
        Args:
            agent_id: Filter by agent ID
            user_id: Filter by user ID
            organization_id: Filter by organization ID
            
        Returns:
            Dictionary of memory statistics
        """
        try:
            query = self.db.query(Memory)
            
            # Apply filters
            if agent_id is not None:
                query = query.filter_by(agent_id=agent_id)
            
            if user_id is not None:
                query = query.filter_by(user_id=user_id)
            
            if organization_id is not None:
                query = query.filter_by(organization_id=organization_id)
            
            # Get counts by type
            memories = query.all()
            
            stats = {
                'total': len(memories),
                'by_type': {},
                'by_importance': {},
                'expired': 0,
                'total_access_count': 0,
            }
            
            for memory in memories:
                # Count by type
                type_key = memory.memory_type.value
                stats['by_type'][type_key] = stats['by_type'].get(type_key, 0) + 1
                
                # Count by importance
                importance_key = memory.importance.value
                stats['by_importance'][importance_key] = stats['by_importance'].get(importance_key, 0) + 1
                
                # Count expired
                if memory.is_expired():
                    stats['expired'] += 1
                
                # Sum access count
                stats['total_access_count'] += memory.access_count
            
            # Add vector store stats
            vector_stats = self.vector_store.get_stats()
            stats['vector_store'] = vector_stats
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {}