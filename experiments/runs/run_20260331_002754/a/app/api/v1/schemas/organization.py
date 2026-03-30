"""app/api/v1/schemas/organization.py — Pydantic schemas for organization endpoints.

exports: OrganizationCreate, OrganizationUpdate, OrganizationResponse, OrganizationMemberCreate, OrganizationMemberUpdate, OrganizationMemberResponse
used_by: app/api/v1/organizations.py → request/response validation
rules:   slug must be URL-safe; role hierarchy validation
agent:   BackendEngineer | 2024-03-31 | created organization schemas with validation
         message: "verify slug uniqueness across organizations"
"""

import re
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from .base import BaseSchema, PaginatedResponse


class OrganizationCreate(BaseSchema):
    """Schema for creating an organization."""
    name: str = Field(..., min_length=1, max_length=255, description="Organization name")
    slug: str = Field(..., min_length=3, max_length=100, description="URL-safe identifier (lowercase letters, numbers, hyphens)")
    description: Optional[str] = Field(None, description="Organization description")
    billing_email: Optional[str] = Field(None, description="Email for billing notifications")
    plan_tier: str = Field(default="free", description="Subscription plan tier (free, pro, enterprise)")
    monthly_credit_limit: int = Field(default=1000, ge=0, description="Monthly credit limit")

    @validator('slug')
    def validate_slug(cls, v):
        """Validate slug format."""
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('Slug can only contain lowercase letters, numbers, and hyphens')
        if v.startswith('-') or v.endswith('-'):
            raise ValueError('Slug cannot start or end with hyphen')
        if '--' in v:
            raise ValueError('Slug cannot contain consecutive hyphens')
        return v.lower()
    
    @validator('plan_tier')
    def validate_plan_tier(cls, v):
        """Validate plan tier."""
        valid_tiers = {'free', 'pro', 'enterprise'}
        if v not in valid_tiers:
            raise ValueError(f'Plan tier must be one of {valid_tiers}')
        return v


class OrganizationUpdate(BaseSchema):
    """Schema for updating an organization."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Organization name")
    description: Optional[str] = Field(None, description="Organization description")
    billing_email: Optional[str] = Field(None, description="Email for billing notifications")
    plan_tier: Optional[str] = Field(None, description="Subscription plan tier")
    monthly_credit_limit: Optional[int] = Field(None, ge=0, description="Monthly credit limit")
    is_active: Optional[bool] = Field(None, description="Whether organization is active")

    @validator('plan_tier')
    def validate_plan_tier(cls, v):
        """Validate plan tier."""
        if v is None:
            return v
        valid_tiers = {'free', 'pro', 'enterprise'}
        if v not in valid_tiers:
            raise ValueError(f'Plan tier must be one of {valid_tiers}')
        return v


class OrganizationResponse(BaseSchema):
    """Schema for organization response."""
    id: int = Field(..., description="Organization ID")
    name: str = Field(..., description="Organization name")
    slug: str = Field(..., description="URL-safe identifier")
    description: Optional[str] = Field(None, description="Organization description")
    billing_email: Optional[str] = Field(None, description="Email for billing notifications")
    plan_tier: str = Field(..., description="Subscription plan tier")
    monthly_credit_limit: int = Field(..., description="Monthly credit limit")
    stripe_customer_id: Optional[str] = Field(None, description="Stripe customer ID")
    stripe_subscription_id: Optional[str] = Field(None, description="Stripe subscription ID")
    is_active: bool = Field(..., description="Whether organization is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    owner_id: Optional[int] = Field(None, description="Owner user ID")


class OrganizationStats(BaseSchema):
    """Organization statistics."""
    member_count: int = Field(..., description="Number of members")
    agent_count: int = Field(..., description="Number of agents")
    task_count: int = Field(..., description="Number of tasks")
    monthly_usage: Dict[str, Any] = Field(..., description="Monthly usage statistics")
    credit_balance: float = Field(..., description="Available credits")


class OrganizationWithStatsResponse(OrganizationResponse):
    """Organization response with statistics."""
    stats: OrganizationStats = Field(..., description="Organization statistics")


class OrganizationMemberCreate(BaseSchema):
    """Schema for adding a member to an organization."""
    user_id: int = Field(..., description="User ID to add")
    role: str = Field(..., description="Member role (owner, admin, member, viewer)")
    
    @validator('role')
    def validate_role(cls, v):
        """Validate role."""
        valid_roles = {'owner', 'admin', 'member', 'viewer'}
        if v not in valid_roles:
            raise ValueError(f'Role must be one of {valid_roles}')
        return v


class OrganizationMemberInvite(BaseSchema):
    """Schema for inviting a member via email."""
    email: str = Field(..., description="Email address to invite")
    role: str = Field(..., description="Member role (admin, member, viewer)")
    
    @validator('role')
    def validate_role(cls, v):
        """Validate role (cannot invite as owner)."""
        valid_roles = {'admin', 'member', 'viewer'}
        if v not in valid_roles:
            raise ValueError(f'Role must be one of {valid_roles}')
        return v


class OrganizationMemberUpdate(BaseSchema):
    """Schema for updating organization member."""
    role: str = Field(..., description="New role (owner, admin, member, viewer)")
    
    @validator('role')
    def validate_role(cls, v):
        """Validate role."""
        valid_roles = {'owner', 'admin', 'member', 'viewer'}
        if v not in valid_roles:
            raise ValueError(f'Role must be one of {valid_roles}')
        return v


class OrganizationMemberResponse(BaseSchema):
    """Schema for organization member response."""
    id: int = Field(..., description="Membership ID")
    organization_id: int = Field(..., description="Organization ID")
    user_id: int = Field(..., description="User ID")
    role: str = Field(..., description="Member role")
    invited_by: Optional[int] = Field(None, description="User who invited this member")
    invited_at: Optional[datetime] = Field(None, description="When invitation was sent")
    joined_at: datetime = Field(..., description="When member joined")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    user_email: str = Field(..., description="Member email")
    user_name: Optional[str] = Field(None, description="Member name")


class OrganizationListResponse(PaginatedResponse[OrganizationResponse]):
    """Paginated response for organization list."""
    pass


class OrganizationMemberListResponse(PaginatedResponse[OrganizationMemberResponse]):
    """Paginated response for organization member list."""
    pass


# Import datetime after class definitions to avoid circular import
from datetime import datetime