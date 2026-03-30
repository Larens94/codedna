"""Agent models for AgentHub marketplace."""

from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Numeric, ForeignKey, Enum, Table
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
import enum

from app import db


class AgentStatus(enum.Enum):
    """Agent status enumeration."""
    
    DRAFT = 'draft'
    UNDER_REVIEW = 'under_review'
    PUBLISHED = 'published'
    UNPUBLISHED = 'unpublished'
    ARCHIVED = 'archived'


class AgentCategory(enum.Enum):
    """Agent category enumeration."""
    
    PRODUCTIVITY = 'productivity'
    CREATIVE = 'creative'
    ANALYTICAL = 'analytical'
    CUSTOMER_SERVICE = 'customer_service'
    DEVELOPMENT = 'development'
    MARKETING = 'marketing'
    FINANCE = 'finance'
    EDUCATION = 'education'
    HEALTHCARE = 'healthcare'
    OTHER = 'other'


# Association table for agent tags
agent_tags = Table(
    'agent_tags',
    db.Model.metadata,
    Column('agent_id', Integer, ForeignKey('agents.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)


class Tag(db.Model):
    """Tag model for categorizing agents.
    
    Attributes:
        id: Primary key
        name: Tag name (unique)
        slug: URL-friendly tag name (unique)
        description: Tag description
        created_at: Creation timestamp
        agents: Agents associated with this tag
    """
    
    __tablename__ = 'tags'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    slug = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    agents = relationship('Agent', secondary=agent_tags, back_populates='tags')
    
    def __repr__(self) -> str:
        return f'<Tag {self.name}>'


class Agent(db.Model):
    """Agent model representing AI agents in the marketplace.
    
    Attributes:
        id: Primary key
        owner_id: Foreign key to user who owns the agent
        name: Agent name
        slug: URL-friendly agent name (unique)
        description: Detailed agent description
        short_description: Brief agent description for listings
        status: Agent status (draft, published, etc.)
        category: Agent category
        price_per_run: Price per agent run in USD
        is_featured: Whether agent is featured in marketplace
        is_public: Whether agent is publicly visible
        icon_url: Agent icon/image URL
        cover_image_url: Agent cover image URL
        version_count: Number of versions (cached)
        run_count: Number of runs (cached)
        average_rating: Average rating (cached)
        review_count: Number of reviews (cached)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        published_at: When agent was published
        owner: User who owns the agent
        versions: Agent versions
        runs: Agent runs
        reviews: Agent reviews
        tags: Tags associated with agent
    """
    
    __tablename__ = 'agents'
    
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    short_description = Column(String(500))
    status = Column(Enum(AgentStatus), default=AgentStatus.DRAFT, nullable=False)
    category = Column(Enum(AgentCategory), nullable=False)
    price_per_run = Column(Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    is_featured = Column(Boolean, default=False)
    is_public = Column(Boolean, default=True)
    icon_url = Column(String(500))
    cover_image_url = Column(String(500))
    
    # Cached counters for performance
    version_count = Column(Integer, default=0)
    run_count = Column(Integer, default=0)
    average_rating = Column(Numeric(3, 2), default=Decimal('0.00'))
    review_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime)
    
    # Relationships
    owner = relationship('User', back_populates='agents')
    versions = relationship('AgentVersion', back_populates='agent', cascade='all, delete-orphan')
    runs = relationship('AgentRun', back_populates='agent', cascade='all, delete-orphan')
    reviews = relationship('AgentReview', back_populates='agent', cascade='all, delete-orphan')
    tags = relationship('Tag', secondary=agent_tags, back_populates='agents')
    
    @validates('slug')
    def validate_slug(self, key: str, slug: str) -> str:
        """Validate and normalize slug.
        
        Args:
            key: Field name
            slug: Slug value
            
        Returns:
            Normalized slug
        """
        if not slug:
            raise ValueError('Slug cannot be empty')
        # Normalize slug (lowercase, replace spaces with hyphens)
        return slug.lower().replace(' ', '-')
    
    @validates('price_per_run')
    def validate_price(self, key: str, price: Decimal) -> Decimal:
        """Validate price is non-negative.
        
        Args:
            key: Field name
            price: Price value
            
        Returns:
            Validated price
        """
        if price < 0:
            raise ValueError('Price cannot be negative')
        return price
    
    def publish(self) -> None:
        """Publish the agent."""
        if self.status != AgentStatus.PUBLISHED:
            self.status = AgentStatus.PUBLISHED
            self.published_at = datetime.utcnow()
    
    def unpublish(self) -> None:
        """Unpublish the agent."""
        if self.status == AgentStatus.PUBLISHED:
            self.status = AgentStatus.UNPUBLISHED
    
    def to_dict(self, include_details: bool = False) -> dict:
        """Convert agent to dictionary representation.
        
        Args:
            include_details: Whether to include detailed information
            
        Returns:
            Dictionary representation of agent
        """
        data = {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'short_description': self.short_description,
            'description': self.description,
            'status': self.status.value if self.status else None,
            'category': self.category.value if self.category else None,
            'price_per_run': float(self.price_per_run) if self.price_per_run else 0.0,
            'is_featured': self.is_featured,
            'is_public': self.is_public,
            'icon_url': self.icon_url,
            'cover_image_url': self.cover_image_url,
            'version_count': self.version_count,
            'run_count': self.run_count,
            'average_rating': float(self.average_rating) if self.average_rating else 0.0,
            'review_count': self.review_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'owner': {
                'id': self.owner.id,
                'username': self.owner.username,
                'avatar_url': self.owner.avatar_url,
            } if self.owner else None,
            'tags': [tag.name for tag in self.tags],
        }
        
        if include_details:
            data.update({
                'versions': [version.to_dict() for version in self.versions[:5]],  # Limit to 5 latest
                'latest_version': self.versions[-1].to_dict() if self.versions else None,
                'recent_runs': [run.to_dict() for run in self.runs[:5]],  # Limit to 5 recent runs
            })
        
        return data
    
    def update_counters(self) -> None:
        """Update cached counters from related objects."""
        self.version_count = len(self.versions)
        self.run_count = len(self.runs)
        self.review_count = len(self.reviews)
        
        if self.reviews:
            total_rating = sum(review.rating for review in self.reviews)
            self.average_rating = total_rating / self.review_count
        else:
            self.average_rating = Decimal('0.00')
    
    def __repr__(self) -> str:
        return f'<Agent {self.name} ({self.status.value})>'


class AgentVersion(db.Model):
    """Agent version model for versioning agent configurations.
    
    Attributes:
        id: Primary key
        agent_id: Foreign key to agent
        version: Version number (semantic versioning)
        config: Agent configuration (JSON)
        agno_agent_id: Reference to agent in Agno framework
        changelog: Version changelog
        is_active: Whether this version is active
        created_at: Creation timestamp
        agent: Parent agent
    """
    
    __tablename__ = 'agent_versions'
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey('agents.id', ondelete='CASCADE'), nullable=False)
    version = Column(String(20), nullable=False)  # e.g., "1.0.0"
    config = Column(Text, nullable=False)  # JSON configuration
    agno_agent_id = Column(String(100), nullable=False)
    changelog = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    agent = relationship('Agent', back_populates='versions')
    
    def to_dict(self) -> dict:
        """Convert agent version to dictionary representation.
        
        Returns:
            Dictionary representation of agent version
        """
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'version': self.version,
            'agno_agent_id': self.agno_agent_id,
            'changelog': self.changelog,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self) -> str:
        return f'<AgentVersion {self.agent.name} v{self.version}>'


class AgentReview(db.Model):
    """Agent review model for user reviews and ratings.
    
    Attributes:
        id: Primary key
        agent_id: Foreign key to agent
        user_id: Foreign key to user who wrote review
        rating: Rating (1-5)
        title: Review title
        content: Review content
        created_at: Creation timestamp
        updated_at: Last update timestamp
        agent: Reviewed agent
        user: User who wrote review
    """
    
    __tablename__ = 'agent_reviews'
    
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey('agents.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5
    title = Column(String(200))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    agent = relationship('Agent', back_populates='reviews')
    user = relationship('User', backref='reviews')
    
    @validates('rating')
    def validate_rating(self, key: str, rating: int) -> int:
        """Validate rating is between 1 and 5.
        
        Args:
            key: Field name
            rating: Rating value
            
        Returns:
            Validated rating
        """
        if not 1 <= rating <= 5:
            raise ValueError('Rating must be between 1 and 5')
        return rating
    
    def to_dict(self) -> dict:
        """Convert review to dictionary representation.
        
        Returns:
            Dictionary representation of review
        """
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'user': {
                'id': self.user.id,
                'username': self.user.username,
                'avatar_url': self.user.avatar_url,
            } if self.user else None,
            'rating': self.rating,
            'title': self.title,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self) -> str:
        return f'<AgentReview {self.rating} stars for Agent {self.agent_id}>'