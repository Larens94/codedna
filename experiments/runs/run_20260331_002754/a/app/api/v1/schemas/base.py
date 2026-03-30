"""app/api/v1/schemas/base.py — Base Pydantic schemas for API.

exports: BaseSchema, PaginationParams, PaginatedResponse
used_by: all other schema modules as base classes
rules:   must use proper type hints; must include example data for OpenAPI docs
agent:   Product Architect | 2024-03-30 | created base schemas with pagination support
         message: "add UUID validation for all ID fields using pydantic types"
"""

from datetime import datetime
from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel, Field, ConfigDict
from pydantic.generics import GenericModel

DataT = TypeVar("DataT")


class BaseSchema(BaseModel):
    """Base schema with common configuration.
    
    Rules:
        All schemas should inherit from this
        Extra fields are ignored by default (security)
        ORM mode is enabled for compatibility with SQLAlchemy models
    """
    model_config = ConfigDict(
        from_attributes=True,  # Enable ORM mode (formerly `orm_mode`)
        populate_by_name=True,  # Allow population by field name
        extra="ignore",  # Ignore extra fields (security)
        json_schema_extra={
            "example": {}  # Override in subclasses
        }
    )


class PaginationParams(BaseSchema):
    """Pagination parameters for list endpoints.
    
    Rules:
        Page is 1-indexed (not 0-indexed)
        Limits should have reasonable defaults and maximums
    """
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(default=None, description="Field to sort by")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="Sort order: asc or desc")


class PaginatedResponse(GenericModel, Generic[DataT]):
    """Generic paginated response wrapper.
    
    Rules:
        Used for all list endpoints
        Includes pagination metadata
    """
    items: List[DataT] = Field(description="List of items on current page")
    total: int = Field(description="Total number of items across all pages")
    page: int = Field(description="Current page number")
    per_page: int = Field(description="Items per page")
    total_pages: int = Field(description="Total number of pages")
    
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
    )


# Common field definitions for reuse
class TimestampMixin(BaseSchema):
    """Mixin for timestamps fields."""
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    deleted_at: Optional[datetime] = Field(default=None, description="Soft deletion timestamp")


class IDMixin(BaseSchema):
    """Mixin for ID field."""
    id: str = Field(description="Unique identifier (UUID)")


class AuditMixin(BaseSchema):
    """Mixin for audit fields."""
    created_by: Optional[str] = Field(default=None, description="User ID who created the record")
    updated_by: Optional[str] = Field(default=None, description="User ID who last updated the record")