"""Vector store for memory embeddings using SQLite."""

import logging
import json
import sqlite3
import numpy as np
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class EmbeddingModel(Enum):
    """Embedding model options."""
    
    # OpenAI models
    TEXT_EMBEDDING_ADA_002 = 'text-embedding-ada-002'
    TEXT_EMBEDDING_3_SMALL = 'text-embedding-3-small'
    TEXT_EMBEDDING_3_LARGE = 'text-embedding-3-large'
    
    # Local models (if implemented)
    ALL_MINILM_L6_V2 = 'all-MiniLM-L6-v2'
    ALL_MPNET_BASE_V2 = 'all-mpnet-base-v2'


class VectorStoreError(Exception):
    """Base exception for vector store errors."""
    pass


class VectorStore:
    """Vector store for memory embeddings using SQLite with VSS extension."""
    
    def __init__(self, db_path: str = 'memories.db', dimension: int = 1536):
        """Initialize vector store.
        
        Args:
            db_path: Path to SQLite database
            dimension: Embedding dimension (default 1536 for text-embedding-ada-002)
        """
        self.db_path = db_path
        self.dimension = dimension
        self.connection = None
        self._initialize_database()
    
    def _initialize_database(self) -> None:
        """Initialize SQLite database with VSS extension if available."""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            
            # Enable WAL mode for better concurrency
            self.connection.execute('PRAGMA journal_mode=WAL')
            
            # Load SQLite VSS extension if available
            try:
                self.connection.enable_load_extension(True)
                self.connection.load_extension('vector0')
                self.connection.load_extension('vss0')
                self.connection.enable_load_extension(False)
                logger.info("SQLite VSS extension loaded successfully")
                self.vss_available = True
            except Exception as e:
                logger.warning(f"SQLite VSS extension not available: {e}. Using fallback.")
                self.vss_available = False
            
            # Create tables
            self._create_tables()
            
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise VectorStoreError(f"Database initialization failed: {e}")
    
    def _create_tables(self) -> None:
        """Create necessary tables for vector storage."""
        cursor = self.connection.cursor()
        
        # Create memories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_vectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id INTEGER NOT NULL,
                agent_id INTEGER,
                user_id INTEGER,
                organization_id INTEGER,
                embedding BLOB NOT NULL,
                dimension INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(memory_id)
            )
        ''')
        
        # Create index for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_memory_vectors_agent_user 
            ON memory_vectors(agent_id, user_id)
        ''')
        
        # Create VSS virtual table if extension is available
        if self.vss_available:
            try:
                cursor.execute(f'''
                    CREATE VIRTUAL TABLE IF NOT EXISTS vss_memories USING vss0(
                        embedding({self.dimension})
                    )
                ''')
            except Exception as e:
                logger.warning(f"Failed to create VSS table: {e}. Using fallback.")
                self.vss_available = False
        
        self.connection.commit()
    
    def add_embedding(
        self,
        memory_id: int,
        embedding: List[float],
        agent_id: Optional[int] = None,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
    ) -> bool:
        """Add embedding to vector store.
        
        Args:
            memory_id: Memory ID
            embedding: Embedding vector
            agent_id: Optional agent ID
            user_id: Optional user ID
            organization_id: Optional organization ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if len(embedding) != self.dimension:
                raise ValueError(f"Embedding dimension mismatch: expected {self.dimension}, got {len(embedding)}")
            
            # Convert embedding to bytes
            embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()
            
            cursor = self.connection.cursor()
            
            # Insert into main table
            cursor.execute('''
                INSERT OR REPLACE INTO memory_vectors 
                (memory_id, agent_id, user_id, organization_id, embedding, dimension)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (memory_id, agent_id, user_id, organization_id, embedding_bytes, self.dimension))
            
            # Insert into VSS table if available
            if self.vss_available:
                cursor.execute('''
                    INSERT OR REPLACE INTO vss_memories(rowid, embedding)
                    VALUES (?, ?)
                ''', (cursor.lastrowid, embedding_bytes))
            
            self.connection.commit()
            logger.debug(f"Added embedding for memory {memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add embedding for memory {memory_id}: {e}")
            self.connection.rollback()
            return False
    
    def get_embedding(self, memory_id: int) -> Optional[List[float]]:
        """Get embedding for memory.
        
        Args:
            memory_id: Memory ID
            
        Returns:
            Embedding vector or None if not found
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                SELECT embedding, dimension FROM memory_vectors 
                WHERE memory_id = ?
            ''', (memory_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            embedding_bytes = row['embedding']
            dimension = row['dimension']
            
            # Convert bytes to list of floats
            embedding = np.frombuffer(embedding_bytes, dtype=np.float32).tolist()
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to get embedding for memory {memory_id}: {e}")
            return None
    
    def search_similar(
        self,
        query_embedding: List[float],
        limit: int = 10,
        agent_id: Optional[int] = None,
        user_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Search for similar embeddings.
        
        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results
            agent_id: Filter by agent ID
            user_id: Filter by user ID
            organization_id: Filter by organization ID
            threshold: Similarity threshold (0.0 to 1.0)
            
        Returns:
            List of similar memories with similarity scores
        """
        try:
            if len(query_embedding) != self.dimension:
                raise ValueError(f"Query embedding dimension mismatch: expected {self.dimension}, got {len(query_embedding)}")
            
            query_bytes = np.array(query_embedding, dtype=np.float32).tobytes()
            
            # Build WHERE clause for filters
            where_clauses = []
            params = []
            
            if agent_id is not None:
                where_clauses.append('agent_id = ?')
                params.append(agent_id)
            
            if user_id is not None:
                where_clauses.append('user_id = ?')
                params.append(user_id)
            
            if organization_id is not None:
                where_clauses.append('organization_id = ?')
                params.append(organization_id)
            
            where_sql = ' AND '.join(where_clauses) if where_clauses else '1=1'
            
            results = []
            
            if self.vss_available:
                # Use VSS for efficient similarity search
                cursor = self.connection.cursor()
                
                # Search using VSS
                cursor.execute(f'''
                    SELECT 
                        mv.memory_id,
                        mv.agent_id,
                        mv.user_id,
                        mv.organization_id,
                        vss_distance(vm.embedding, ?) as distance
                    FROM vss_memories vm
                    JOIN memory_vectors mv ON vm.rowid = mv.id
                    WHERE {where_sql}
                    ORDER BY distance
                    LIMIT ?
                ''', [query_bytes] + params + [limit])
                
                for row in cursor.fetchall():
                    # Convert distance to similarity (1 - normalized distance)
                    # VSS distance is Euclidean distance
                    distance = row['distance']
                    # Approximate conversion to cosine similarity
                    # This is a simplification - actual conversion depends on vector normalization
                    similarity = max(0.0, 1.0 - (distance / 2.0))
                    
                    if similarity >= threshold:
                        results.append({
                            'memory_id': row['memory_id'],
                            'agent_id': row['agent_id'],
                            'user_id': row['user_id'],
                            'organization_id': row['organization_id'],
                            'similarity': similarity,
                            'distance': distance,
                        })
                        
            else:
                # Fallback: brute-force similarity calculation
                cursor = self.connection.cursor()
                cursor.execute(f'''
                    SELECT 
                        memory_id,
                        agent_id,
                        user_id,
                        organization_id,
                        embedding
                    FROM memory_vectors
                    WHERE {where_sql}
                ''', params)
                
                query_vector = np.array(query_embedding, dtype=np.float32)
                
                for row in cursor.fetchall():
                    embedding_bytes = row['embedding']
                    stored_vector = np.frombuffer(embedding_bytes, dtype=np.float32)
                    
                    # Calculate cosine similarity
                    similarity = self._cosine_similarity(query_vector, stored_vector)
                    
                    if similarity >= threshold:
                        results.append({
                            'memory_id': row['memory_id'],
                            'agent_id': row['agent_id'],
                            'user_id': row['user_id'],
                            'organization_id': row['organization_id'],
                            'similarity': float(similarity),
                            'distance': float(1.0 - similarity),
                        })
                
                # Sort by similarity and limit
                results.sort(key=lambda x: x['similarity'], reverse=True)
                results = results[:limit]
            
            logger.debug(f"Found {len(results)} similar memories")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search similar embeddings: {e}")
            return []
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors.
        
        Args:
            a: First vector
            b: Second vector
            
        Returns:
            Cosine similarity (-1 to 1)
        """
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(np.dot(a, b) / (norm_a * norm_b))
    
    def delete_embedding(self, memory_id: int) -> bool:
        """Delete embedding for memory.
        
        Args:
            memory_id: Memory ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.connection.cursor()
            
            # Get the rowid for VSS table
            cursor.execute('SELECT id FROM memory_vectors WHERE memory_id = ?', (memory_id,))
            row = cursor.fetchone()
            
            if row:
                rowid = row['id']
                
                # Delete from VSS table if available
                if self.vss_available:
                    cursor.execute('DELETE FROM vss_memories WHERE rowid = ?', (rowid,))
                
                # Delete from main table
                cursor.execute('DELETE FROM memory_vectors WHERE memory_id = ?', (memory_id,))
                
                self.connection.commit()
                logger.debug(f"Deleted embedding for memory {memory_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete embedding for memory {memory_id}: {e}")
            self.connection.rollback()
            return False
    
    def update_embedding(
        self,
        memory_id: int,
        embedding: List[float],
    ) -> bool:
        """Update embedding for memory.
        
        Args:
            memory_id: Memory ID
            embedding: New embedding vector
            
        Returns:
            True if successful, False otherwise
        """
        return self.add_embedding(memory_id, embedding)  # add_embedding uses INSERT OR REPLACE
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics.
        
        Returns:
            Dictionary of statistics
        """
        try:
            cursor = self.connection.cursor()
            
            # Get total embeddings count
            cursor.execute('SELECT COUNT(*) as count FROM memory_vectors')
            total_count = cursor.fetchone()['count']
            
            # Get dimension distribution
            cursor.execute('SELECT dimension, COUNT(*) as count FROM memory_vectors GROUP BY dimension')
            dimension_stats = {row['dimension']: row['count'] for row in cursor.fetchall()}
            
            return {
                'total_embeddings': total_count,
                'dimension_stats': dimension_stats,
                'vss_available': self.vss_available,
                'database_path': self.db_path,
            }
            
        except Exception as e:
            logger.error(f"Failed to get vector store stats: {e}")
            return {}
    
    def close(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def __del__(self) -> None:
        """Destructor to ensure connection is closed."""
        self.close()


class EmbeddingService:
    """Service for generating embeddings using various models."""
    
    def __init__(self, model: EmbeddingModel = EmbeddingModel.TEXT_EMBEDDING_ADA_002, api_key: Optional[str] = None):
        """Initialize embedding service.
        
        Args:
            model: Embedding model to use
            api_key: API key for cloud models (optional for local models)
        """
        self.model = model
        self.api_key = api_key
        self._local_model = None
        
        # Initialize based on model type
        if model.value.startswith('text-embedding'):
            # OpenAI model
            self.model_type = 'openai'
            self.dimension = self._get_openai_dimension(model)
        else:
            # Local model
            self.model_type = 'local'
            self.dimension = self._get_local_dimension(model)
    
    def _get_openai_dimension(self, model: EmbeddingModel) -> int:
        """Get dimension for OpenAI model.
        
        Args:
            model: OpenAI embedding model
            
        Returns:
            Embedding dimension
        """
        dimensions = {
            EmbeddingModel.TEXT_EMBEDDING_ADA_002: 1536,
            EmbeddingModel.TEXT_EMBEDDING_3_SMALL: 1536,
            EmbeddingModel.TEXT_EMBEDDING_3_LARGE: 3072,
        }
        return dimensions.get(model, 1536)
    
    def _get_local_dimension(self, model: EmbeddingModel) -> int:
        """Get dimension for local model.
        
        Args:
            model: Local embedding model
            
        Returns:
            Embedding dimension
        """
        dimensions = {
            EmbeddingModel.ALL_MINILM_L6_V2: 384,
            EmbeddingModel.ALL_MPNET_BASE_V2: 768,
        }
        return dimensions.get(model, 384)
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector or None if failed
        """
        try:
            if self.model_type == 'openai':
                return self._generate_openai_embedding(text)
            else:
                return self._generate_local_embedding(text)
                
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    def _generate_openai_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding using OpenAI API.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector or None if failed
        """
        try:
            import openai
            
            if not self.api_key:
                raise ValueError("OpenAI API key required")
            
            openai.api_key = self.api_key
            
            response = openai.Embedding.create(
                model=self.model.value,
                input=text,
            )
            
            embedding = response['data'][0]['embedding']
            return embedding
            
        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {e}")
            return None
    
    def _generate_local_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding using local model.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector or None if failed
        """
        try:
            # Lazy load sentence-transformers
            if self._local_model is None:
                from sentence_transformers import SentenceTransformer
                self._local_model = SentenceTransformer(self.model.value)
            
            embedding = self._local_model.encode(text, convert_to_numpy=True).tolist()
            return embedding
            
        except ImportError:
            logger.error("sentence-transformers not installed. Install with: pip install sentence-transformers")
            return None
        except Exception as e:
            logger.error(f"Local embedding generation failed: {e}")
            return None
    
    def batch_generate_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors (or None for failed ones)
        """
        try:
            if self.model_type == 'openai':
                return self._batch_generate_openai_embeddings(texts)
            else:
                return self._batch_generate_local_embeddings(texts)
                
        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            return [None] * len(texts)
    
    def _batch_generate_openai_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Batch generate embeddings using OpenAI API.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        try:
            import openai
            
            if not self.api_key:
                raise ValueError("OpenAI API key required")
            
            openai.api_key = self.api_key
            
            # OpenAI has limits on batch size
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                response = openai.Embedding.create(
                    model=self.model.value,
                    input=batch,
                )
                
                batch_embeddings = [item['embedding'] for item in response['data']]
                all_embeddings.extend(batch_embeddings)
            
            return all_embeddings
            
        except Exception as e:
            logger.error(f"OpenAI batch embedding generation failed: {e}")
            return [None] * len(texts)
    
    def _batch_generate_local_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Batch generate embeddings using local model.
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        try:
            # Lazy load sentence-transformers
            if self._local_model is None:
                from sentence_transformers import SentenceTransformer
                self._local_model = SentenceTransformer(self.model.value)
            
            embeddings = self._local_model.encode(texts, convert_to_numpy=True).tolist()
            return embeddings
            
        except ImportError:
            logger.error("sentence-transformers not installed")
            return [None] * len(texts)
        except Exception as e:
            logger.error(f"Local batch embedding generation failed: {e}")
            return [None] * len(texts)