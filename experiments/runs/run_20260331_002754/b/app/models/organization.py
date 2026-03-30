"""Organization and team models for multi-tenancy support."""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from app import db


class OrganizationRole(enum.Enum):
    """Organization member role enumeration."""
    
    OWNER = 'owner'
    ADMIN = 'admin'
    MEMBER = 'member'
    GUEST = 'guest'


class Organization(db.Model):
    """Organization model for team collaboration.
    
    Attributes:
        id: Primary key
        name: Organization name
        slug: URL-friendly organization identifier (unique)
        description: Organization description
        logo_url: URL to organization logo
        website: Organization website
        is_active: Whether organization is active
        max_members: Maximum number of members allowed
        billing_account_id: Foreign key to billing account for org-wide billing
        created_at: Creation timestamp
        updated_at: Last update timestamp
        members: Organization memberships
        agents: Agents owned by organization
        runs: Agent runs under organization
    """
    
    __tablename__ = 'organizations'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    logo_url = Column(String(500))
    website = Column(String(500))
    is_active = Column(Boolean, default=True)
    max_members = Column(Integer, default=10)
    billing_account_id = Column(Integer, ForeignKey('billing_accounts.id', ondelete='SET NULL'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    billing_account = relationship('BillingAccount')
    members = relationship('OrgMembership', back_populates='organization', cascade='all, delete-orphan')
    agents = relationship('Agent', back_populates='organization', cascade='all, delete-orphan')
    runs = relationship('AgentRun', back_populates='organization', cascade='all, delete-orphan')
    
    def get_member_count(self) -> int:
        """Get number of active members in organization.
        
        Returns:
            Number of active members
        """
        return len([m for m in self.members if m.is_active])
    
    def get_owner(self) -> Optional['OrgMembership']:
        """Get the organization owner membership.
        
        Returns:
            Owner membership or None if not found
        """
        for member in self.members:
            if member.role == OrganizationRole.OWNER:
                return member
        return None
    
    def can_invite_members(self, user_id: int) -> bool:
        """Check if user can invite new members.
        
        Args:
            user_id: User ID to check
            
        Returns:
            True if user can invite, False otherwise
        """
        membership = next((m for m in self.members if m.user_id == user_id), None)
        if not membership:
            return False
        
        return membership.role in (OrganizationRole.OWNER, OrganizationRole.ADMIN)
    
    def to_dict(self, include_members: bool = False) -> dict:
        """Convert organization to dictionary representation.
        
        Args:
            include_members: Whether to include members list
            
        Returns:
            Dictionary representation of organization
        """
        data = {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'logo_url': self.logo_url,
            'website': self.website,
            'is_active': self.is_active,
            'max_members': self.max_members,
            'member_count': self.get_member_count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_members:
            data['members'] = [membership.to_dict(include_user=True) for membership in self.members]
        
        return data
    
    def __repr__(self) -> str:
        return f'<Organization {self.name} ({self.slug})>'


class OrgMembership(db.Model):
    """Organization membership model.
    
    Attributes:
        id: Primary key
        organization_id: Foreign key to organization
        user_id: Foreign key to user
        role: Member role
        is_active: Whether membership is active
        joined_at: When user joined organization
        invited_by: User who invited this member
        created_at: Creation timestamp
        updated_at: Last update timestamp
        organization: Associated organization
        user: Associated user
    """
    
    __tablename__ = 'org_memberships'
    
    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role = Column(Enum(OrganizationRole), default=OrganizationRole.MEMBER, nullable=False)
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime, default=datetime.utcnow)
    invited_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship('Organization', back_populates='members')
    user = relationship('User')
    inviter = relationship('User', foreign_keys=[invited_by])
    
    def can_manage_agents(self) -> bool:
        """Check if member can manage agents.
        
        Returns:
            True if member can manage agents, False otherwise
        """
        return self.role in (OrganizationRole.OWNER, OrganizationRole.ADMIN)
    
    def can_manage_billing(self) -> bool:
        """Check if member can manage billing.
        
        Returns:
            True if member can manage billing, False otherwise
        """
        return self.role == OrganizationRole.OWNER
    
    def can_manage_members(self) -> bool:
        """Check if member can manage other members.
        
        Returns:
            True if member can manage members, False otherwise
        """
        return self.role in (OrganizationRole.OWNER, OrganizationRole.ADMIN)
    
    def to_dict(self, include_user: bool = False, include_organization: bool = False) -> dict:
        """Convert membership to dictionary representation.
        
        Args:
            include_user: Whether to include user details
            include_organization: Whether to include organization details
            
        Returns:
            Dictionary representation of membership
        """
        data = {
            'id': self.id,
            'organization_id': self.organization_id,
            'user_id': self.user_id,
            'role': self.role.value if self.role else None,
            'is_active': self.is_active,
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'invited_by': self.invited_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'can_manage_agents': self.can_manage_agents(),
            'can_manage_billing': self.can_manage_billing(),
            'can_manage_members': self.can_manage_members(),
        }
        
        if include_user and self.user:
            data['user'] = self.user.to_dict()
        
        if include_organization and self.organization:
            data['organization'] = self.organization.to_dict()
        
        return data
    
    def __repr__(self) -> str:
        return f'<OrgMembership User {self.user_id} in Org {self.organization_id} ({self.role.value})>'