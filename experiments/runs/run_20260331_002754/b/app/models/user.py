"""User model for AgentHub."""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from flask_bcrypt import generate_password_hash, check_password_hash

from app import db


class User(db.Model):
    """User model representing platform users.
    
    Attributes:
        id: Primary key
        email: User's email address (unique)
        username: User's display name (unique)
        password_hash: Hashed password
        is_active: Whether user account is active
        is_admin: Whether user has admin privileges
        email_verified: Whether email has been verified
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        billing_account: Associated billing account
        subscriptions: User's subscriptions
        agents: User's created agents
        runs: Agent runs initiated by user
    """
    
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    avatar_url = Column(String(500))
    bio = Column(Text)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    billing_account = relationship('BillingAccount', back_populates='user', uselist=False, cascade='all, delete-orphan')
    subscriptions = relationship('Subscription', back_populates='user', cascade='all, delete-orphan')
    agents = relationship('Agent', back_populates='owner', cascade='all, delete-orphan')
    runs = relationship('AgentRun', back_populates='user', cascade='all, delete-orphan')
    
    def __init__(self, email: str, username: str, password: str, **kwargs):
        """Initialize a new user.
        
        Args:
            email: User's email address
            username: User's display name
            password: Plain text password (will be hashed)
            **kwargs: Additional user attributes
        """
        self.email = email
        self.username = username
        self.set_password(password)
        
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def set_password(self, password: str) -> None:
        """Hash and set user password.
        
        Args:
            password: Plain text password
        """
        self.password_hash = generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password: str) -> bool:
        """Check if password matches the stored hash.
        
        Args:
            password: Plain text password to check
            
        Returns:
            True if password matches, False otherwise
        """
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert user to dictionary representation.
        
        Args:
            include_sensitive: Whether to include sensitive fields
            
        Returns:
            Dictionary representation of user
        """
        data = {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'avatar_url': self.avatar_url,
            'bio': self.bio,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'email_verified': self.email_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_sensitive:
            data.update({
                'billing_account': self.billing_account.to_dict() if self.billing_account else None,
                'subscription_count': len(self.subscriptions),
                'agent_count': len(self.agents),
                'run_count': len(self.runs),
            })
        
        return data
    
    def __repr__(self) -> str:
        return f'<User {self.username} ({self.email})>'


class UserSession(db.Model):
    """User session model for managing active sessions.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to user
        session_token: Unique session token
        refresh_token: Refresh token for JWT rotation
        user_agent: Browser/device user agent string
        ip_address: Client IP address
        expires_at: Session expiration timestamp
        created_at: Session creation timestamp
        user: Associated user
    """
    
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), unique=True, nullable=False, index=True)
    user_agent = Column(Text)
    ip_address = Column(String(45))  # IPv6 maximum length
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship('User', backref='sessions')
    
    def __repr__(self) -> str:
        return f'<UserSession {self.session_token[:8]}... for User {self.user_id}>'