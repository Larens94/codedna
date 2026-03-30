"""app/models/user.py — User model and related entities.

exports: User
used_by: auth service → authentication, user service → CRUD operations
rules:   passwords must be hashed with argon2; email must be unique and validated
agent:   Product Architect | 2024-03-30 | implemented user model with proper constraints
         message: "consider adding index on email for faster lookups"
"""

import re
from typing import List, Optional
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """User account for authentication and authorization.
    
    Rules:
        Email must be unique and validated
        Password must be hashed with argon2
        Last login tracked for security auditing
    """
    
    __tablename__ = "users"
    
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Unique user identifier",
    )
    
    email = Column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        doc="User email address (unique)",
    )
    
    username = Column(
        String(100),
        nullable=True,
        unique=True,
        index=True,
        doc="Optional username (unique if provided)",
    )
    
    password_hash = Column(
        String(255),
        nullable=False,
        doc="Argon2 hashed password",
    )
    
    first_name = Column(
        String(100),
        nullable=True,
        doc="User's first name",
    )
    
    last_name = Column(
        String(100),
        nullable=True,
        doc="User's last name",
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether user account is active",
    )
    
    is_superuser = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether user has superuser privileges",
    )
    
    email_verified = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether email has been verified",
    )
    
    last_login = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of last successful login",
    )
    
    # Relationships
    organization_memberships = relationship(
        "OrganizationMember",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
        doc="Organization memberships for this user",
    )
    
    created_agents = relationship(
        "Agent",
        back_populates="created_by_user",
        foreign_keys="Agent.created_by",
        lazy="selectin",
        doc="Agents created by this user",
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_users_email_lower", func.lower(email), unique=True),
        Index("ix_users_username_lower", func.lower(username), unique=True),
    )
    
    @validates("email")
    def validate_email(self, key: str, email: str) -> str:
        """Validate email format.
        
        Args:
            key: Field name
            email: Email address to validate
            
        Returns:
            str: Validated email
            
        Raises:
            ValueError: If email format is invalid
        """
        if not email:
            raise ValueError("Email cannot be empty")
        
        # Basic email validation regex
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, email):
            raise ValueError("Invalid email format")
        
        return email.lower()
    
    @validates("username")
    def validate_username(self, key: str, username: Optional[str]) -> Optional[str]:
        """Validate username format.
        
        Args:
            key: Field name
            username: Username to validate
            
        Returns:
            Optional[str]: Validated username or None
            
        Raises:
            ValueError: If username format is invalid
        """
        if username is None:
            return None
        
        username = username.strip()
        if not username:
            return None
        
        # Username validation
        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(username) > 100:
            raise ValueError("Username must be at most 100 characters")
        if not re.match(r"^[a-zA-Z0-9_.-]+$", username):
            raise ValueError("Username can only contain letters, numbers, dots, hyphens, and underscores")
        
        return username.lower()
    
    @property
    def full_name(self) -> str:
        """Get user's full name.
        
        Returns:
            str: Full name (first + last) or email if no name
        """
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.email
    
    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated.
        
        Returns:
            bool: True if user is active and email verified
        """
        return self.is_active and self.email_verified
    
    def __repr__(self) -> str:
        """String representation of user."""
        return f"<User(id={self.id}, email='{self.email}')>"