"""app/models/organization.py — Organization and member models for multi-tenancy.

exports: Organization, OrganizationMember
used_by: organization service → CRUD, all services → tenant isolation
rules:   slug must be unique and URL-safe; RBAC with proper role hierarchy
agent:   Product Architect | 2024-03-30 | implemented organization model with RBAC
         message: "verify that slug generation handles collisions gracefully"
"""

import re
from typing import List, Optional
from enum import Enum

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
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

from app.models.base import Base, TimestampMixin


class OrganizationRole(str, Enum):
    """Organization member roles with hierarchical permissions.
    
    Rules:
        Owner: Full access, can manage billing and delete organization
        Admin: Manage members, agents, settings
        Member: Create and use agents
        Viewer: Read-only access
    """
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class Organization(Base, TimestampMixin):
    """Organization (tenant) for multi-tenancy.
    
    Rules:
        Each organization is isolated tenant
        Slug must be unique and URL-safe
        Billing integration via Stripe
    """
    
    __tablename__ = "organizations"
    
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Unique organization identifier",
    )
    
    name = Column(
        String(255),
        nullable=False,
        doc="Organization name",
    )
    
    slug = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        doc="URL-safe organization identifier",
    )
    
    description = Column(
        Text,
        nullable=True,
        doc="Organization description",
    )
    
    billing_email = Column(
        String(255),
        nullable=True,
        doc="Email for billing notifications",
    )
    
    plan_tier = Column(
        String(50),
        default="free",
        nullable=False,
        doc="Subscription plan tier (free, pro, enterprise)",
    )
    
    monthly_credit_limit = Column(
        Integer,
        default=1000,
        nullable=False,
        doc="Monthly credit limit for the organization",
    )
    
    stripe_customer_id = Column(
        String(255),
        nullable=True,
        unique=True,
        doc="Stripe customer ID for billing",
    )
    
    stripe_subscription_id = Column(
        String(255),
        nullable=True,
        unique=True,
        doc="Stripe subscription ID",
    )
    
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether organization is active",
    )
    
    # Relationships
    members = relationship(
        "OrganizationMember",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="selectin",
        doc="Organization members",
    )
    
    agents = relationship(
        "Agent",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="selectin",
        doc="Agents belonging to this organization",
    )
    
    tasks = relationship(
        "Task",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="selectin",
        doc="Tasks belonging to this organization",
    )
    
    usage_records = relationship(
        "UsageRecord",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="selectin",
        doc="Usage records for this organization",
    )
    
    billing_invoices = relationship(
        "BillingInvoice",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="selectin",
        doc="Billing invoices for this organization",
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_organizations_slug_lower", func.lower(slug), unique=True),
        Index("ix_organizations_is_active", is_active),
    )
    
    @validates("slug")
    def validate_slug(self, key: str, slug: str) -> str:
        """Validate organization slug.
        
        Args:
            key: Field name
            slug: Slug to validate
            
        Returns:
            str: Validated slug
            
        Raises:
            ValueError: If slug format is invalid
        """
        if not slug:
            raise ValueError("Slug cannot be empty")
        
        slug = slug.strip().lower()
        
        # Slug validation
        if len(slug) < 3:
            raise ValueError("Slug must be at least 3 characters")
        if len(slug) > 100:
            raise ValueError("Slug must be at most 100 characters")
        if not re.match(r"^[a-z0-9-]+$", slug):
            raise ValueError("Slug can only contain lowercase letters, numbers, and hyphens")
        if slug.startswith("-") or slug.endswith("-"):
            raise ValueError("Slug cannot start or end with hyphen")
        if "--" in slug:
            raise ValueError("Slug cannot contain consecutive hyphens")
        
        return slug
    
    @validates("plan_tier")
    def validate_plan_tier(self, key: str, plan_tier: str) -> str:
        """Validate plan tier.
        
        Args:
            key: Field name
            plan_tier: Plan tier to validate
            
        Returns:
            str: Validated plan tier
            
        Raises:
            ValueError: If plan tier is invalid
        """
        valid_tiers = {"free", "pro", "enterprise"}
        if plan_tier not in valid_tiers:
            raise ValueError(f"Plan tier must be one of {valid_tiers}")
        
        return plan_tier
    
    @property
    def owner(self) -> Optional["OrganizationMember"]:
        """Get organization owner.
        
        Returns:
            Optional[OrganizationMember]: Owner member or None
        """
        for member in self.members:
            if member.role == OrganizationRole.OWNER:
                return member
        return None
    
    def __repr__(self) -> str:
        """String representation of organization."""
        return f"<Organization(id={self.id}, name='{self.name}', slug='{self.slug}')>"


class OrganizationMember(Base, TimestampMixin):
    """Organization membership with role-based access control.
    
    Rules:
        Each user can have only one role per organization
        Role hierarchy: owner > admin > member > viewer
    """
    
    __tablename__ = "organization_members"
    
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Unique membership identifier",
    )
    
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        doc="Organization ID",
    )
    
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="User ID",
    )
    
    role = Column(
        SQLEnum(OrganizationRole),
        default=OrganizationRole.MEMBER,
        nullable=False,
        doc="Member role in organization",
    )
    
    invited_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        doc="User who invited this member",
    )
    
    invited_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="When invitation was sent",
    )
    
    joined_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When member joined the organization",
    )
    
    # Relationships
    organization = relationship(
        "Organization",
        back_populates="members",
        lazy="selectin",
    )
    
    user = relationship(
        "User",
        back_populates="organization_memberships",
        lazy="selectin",
        foreign_keys=[user_id],
    )
    
    inviter = relationship(
        "User",
        lazy="selectin",
        foreign_keys=[invited_by],
    )
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_member"),
        Index("ix_org_members_user_id", user_id),
        Index("ix_org_members_org_id_role", organization_id, role),
    )
    
    @property
    def can_manage_organization(self) -> bool:
        """Check if member can manage organization settings.
        
        Returns:
            bool: True if owner or admin
        """
        return self.role in {OrganizationRole.OWNER, OrganizationRole.ADMIN}
    
    @property
    def can_manage_members(self) -> bool:
        """Check if member can manage other members.
        
        Returns:
            bool: True if owner or admin
        """
        return self.role in {OrganizationRole.OWNER, OrganizationRole.ADMIN}
    
    @property
    def can_create_agents(self) -> bool:
        """Check if member can create agents.
        
        Returns:
            bool: True if owner, admin, or member
        """
        return self.role in {OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.MEMBER}
    
    @property
    def can_view(self) -> bool:
        """Check if member has view access.
        
        Returns:
            bool: True for all roles
        """
        return True
    
    def __repr__(self) -> str:
        """String representation of organization member."""
        return f"<OrganizationMember(org={self.organization_id}, user={self.user_id}, role={self.role})>"