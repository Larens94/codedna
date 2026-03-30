"""app/models/base.py — Base model classes and mixins.

exports: Base, TimestampMixin
used_by: all other models → inherit from Base and mixins
rules:   all models must include timestamps; UUID primary keys for distributed systems
agent:   Product Architect | 2024-03-30 | created base model with UUID and timestamps
         message: "consider adding soft delete mixin for data retention compliance"
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy.sql import expression


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models.
    
    Rules:
        All models inherit from this class
        Provides table naming convention
    """
    
    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name.
        
        Returns:
            str: Table name in snake_case
        """
        return cls.__name__.lower()


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps.
    
    Rules:
        All models should include this mixin
        updated_at auto-updates on record modification
    """
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when record was created",
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Timestamp when record was last updated",
    )


class UUIDMixin:
    """Mixin for UUID primary key.
    
    Rules:
        Use for tables that need distributed ID generation
        PostgreSQL gen_random_uuid() for default
    """
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
        doc="Unique identifier (UUID v4)",
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality.
    
    Rules:
        deleted_at is NULL for active records
        Use for compliance with data retention policies
    """
    
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when record was soft deleted (NULL if active)",
    )
    
    @property
    def is_deleted(self) -> bool:
        """Check if record is soft deleted."""
        return self.deleted_at is not None