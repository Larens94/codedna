"""users.py — User profile and organization management schemas.

exports: ProfileUpdate, OrgCreate, OrgInvite, OrgMemberResponse, UsageStats, TeamMember, TeamInvite, TeamResponse
used_by: users.py router
rules:   must validate email uniqueness; must enforce role-based permissions
agent:   BackendEngineer | 2024-01-15 | created user and organization schemas
         message: "implement organization management with proper role-based access control"
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, EmailStr, validator
import re


class ProfileUpdate(BaseModel):
    """Schema for updating user profile."""
    
    full_name: Optional[str] = Field(None, max_length=255, description="User full name")
    avatar_url: Optional[str] = Field(None, max_length=500, description="Avatar URL")
    
    @validator("avatar_url")
    def validate_avatar_url(cls, v):
        """Validate avatar URL format."""
        if v is not None:
            if not re.match(r"^https?://", v):
                raise ValueError("Avatar URL must start with http:// or https://")
            if len(v) > 500:
                raise ValueError("Avatar URL must be 500 characters or less")
        return v


class OrgCreate(BaseModel):
    """Schema for creating an organization."""
    
    name: str = Field(..., min_length=1, max_length=255, description="Organization name")
    description: Optional[str] = Field(None, description="Organization description")
    website: Optional[str] = Field(None, description="Organization website")
    billing_email: Optional[EmailStr] = Field(None, description="Billing email address")
    
    @validator("website")
    def validate_website(cls, v):
        """Validate website URL format."""
        if v is not None:
            if not re.match(r"^https?://", v):
                raise ValueError("Website must start with http:// or https://")
        return v


class OrgInvite(BaseModel):
    """Schema for inviting users to organization."""
    
    email: EmailStr = Field(..., description="Email address to invite")
    role: str = Field("member", description="Role for the invited user")
    
    @validator("role")
    def validate_role(cls, v):
        """Validate role value."""
        allowed_roles = ["member", "admin", "owner"]
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of: {', '.join(allowed_roles)}")
        return v


class OrgMemberResponse(BaseModel):
    """Schema for organization member response."""
    
    user_id: int = Field(..., description="User ID")
    public_id: str = Field(..., description="Public user ID")
    email: EmailStr = Field(..., description="User email")
    full_name: Optional[str] = Field(None, description="User full name")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    role: str = Field(..., description="Organization role")
    joined_at: datetime = Field(..., description="Join timestamp")
    
    class Config:
        from_attributes = True


class TeamMember(BaseModel):
    """Schema for team member response."""
    
    id: str = Field(..., description="Public user ID")
    email: EmailStr = Field(..., description="User email")
    full_name: Optional[str] = Field(None, description="User full name")
    role: str = Field(..., description="Team role")
    joined_at: datetime = Field(..., description="Join timestamp")
    is_active: bool = Field(..., description="User active status")
    
    class Config:
        from_attributes = True


class TeamInvite(BaseModel):
    """Schema for team invitation response."""
    
    team_id: str = Field(..., description="Team ID")
    team_name: str = Field(..., description="Team name")
    invitee_email: EmailStr = Field(..., description="Invitee email")
    invited_by: EmailStr = Field(..., description="Inviter email")
    role: str = Field(..., description="Assigned role")
    invited_at: str = Field(..., description="Invitation timestamp")
    status: str = Field(..., description="Invitation status")
    
    class Config:
        from_attributes = True


class TeamResponse(BaseModel):
    """Schema for team response."""
    
    id: str = Field(..., description="Team ID")
    name: str = Field(..., description="Team name")
    email: EmailStr = Field(..., description="Team email")
    role: str = Field(..., description="Current user role")
    member_count: int = Field(..., description="Number of members")
    agent_count: int = Field(..., description="Number of agents")
    created_at: datetime = Field(..., description="Creation timestamp")
    is_active: bool = Field(..., description="Team active status")
    
    class Config:
        from_attributes = True


class UsageStats(BaseModel):
    """Schema for usage statistics response."""
    
    timeframe: str = Field(..., description="Timeframe (day, week, month, year)")
    start_date: datetime = Field(..., description="Start date of timeframe")
    end_date: datetime = Field(..., description="End date of timeframe")
    total_runs: int = Field(..., description="Total agent runs")
    total_credits_used: float = Field(..., description="Total credits used")
    total_cost: float = Field(..., description="Total cost in USD")
    runs_by_agent: Dict[str, int] = Field(..., description="Runs grouped by agent")
    credits_by_day: Dict[str, float] = Field(..., description="Daily credit usage")
    average_run_cost: float = Field(..., description="Average cost per run")
    peak_usage_day: Optional[str] = Field(None, description="Day with peak usage")
    
    class Config:
        from_attributes = True