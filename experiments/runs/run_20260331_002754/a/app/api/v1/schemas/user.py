"""app/api/v1/schemas/user.py — Pydantic schemas for user endpoints.

exports: UserCreate, UserUpdate, UserResponse, UserListResponse
used_by: app/api/v1/users.py → request/response validation
rules:   exclude password_hash from response schemas; validate email format
agent:   BackendEngineer | 2024-03-31 | created user schemas with validation
         message: "consider adding rate limiting to user registration endpoint"
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator
from .base import BaseSchema, PaginatedResponse


class UserCreate(BaseSchema):
    """Schema for user registration."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=100, description="Password (min 8 characters)")
    first_name: Optional[str] = Field(None, min_length=1, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Last name")
    username: Optional[str] = Field(None, min_length=3, max_length=100, description="Username (optional)")


class UserUpdate(BaseSchema):
    """Schema for updating user profile."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Last name")
    username: Optional[str] = Field(None, min_length=3, max_length=100, description="Username")


class PasswordChange(BaseSchema):
    """Schema for password change."""
    current_password: str = Field(..., min_length=8, max_length=100, description="Current password")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password (min 8 characters)")


class UserResponse(BaseSchema):
    """Schema for user response (excluding sensitive data)."""
    id: int = Field(..., description="User ID")
    email: str = Field(..., description="Email address")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    username: Optional[str] = Field(None, description="Username")
    is_active: bool = Field(..., description="Whether user account is active")
    email_verified: bool = Field(..., description="Whether email has been verified")
    last_login: Optional[datetime] = Field(None, description="Timestamp of last login")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class UserWithOrganizationsResponse(UserResponse):
    """User response including organization memberships."""
    organizations: List["UserOrganizationInfo"] = Field(default=[], description="Organization memberships")


class UserOrganizationInfo(BaseSchema):
    """Organization membership info for user response."""
    id: int = Field(..., description="Organization ID")
    name: str = Field(..., description="Organization name")
    slug: str = Field(..., description="Organization slug")
    role: str = Field(..., description="User's role in organization")
    joined_at: datetime = Field(..., description="When user joined organization")


class UserListResponse(PaginatedResponse[UserResponse]):
    """Paginated response for user list."""
    pass