"""app/api/v1/users.py — User management endpoints.

exports: router (user endpoints)
used_by: app/api/v1/router.py → router inclusion
rules:   users can only access their own data unless admin; password changes require current password
agent:   BackendEngineer | 2024-03-31 | created user management endpoints
         message: "implement email verification flow with rate limiting"
"""

from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import EmailStr

from app.services import ServiceContainer
from app.dependencies import get_services
from app.dependencies import get_current_user
from app.api.v1.schemas import (
    UserCreate, UserUpdate, PasswordChange, UserResponse,
    UserWithOrganizationsResponse, UserListResponse, PaginationParams
)

# Create router
router = APIRouter(tags=["users"])


@router.get("/", response_model=UserListResponse)
async def list_users(
    pagination: PaginationParams = Depends(),
    search: str = Query(None, description="Search by email or name"),
    is_active: bool = Query(None, description="Filter by active status"),
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """List users (admin only).
    
    Rules:
        Requires superuser privileges
        Returns paginated list of users
        Excludes sensitive fields
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    
    try:
        result = await services.users.list_users(
            page=pagination.page,
            per_page=pagination.per_page,
            search=search,
            is_active=is_active,
        )
        return UserListResponse(
            items=result["items"],
            total=result["total"],
            page=pagination.page,
            per_page=pagination.per_page,
            total_pages=(result["total"] + pagination.per_page - 1) // pagination.per_page,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Create new user (admin only).
    
    Rules:
        Requires superuser privileges
        Email must be unique
        Password is hashed before storage
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    
    try:
        user = await services.users.create_user(
            email=user_data.email,
            password=user_data.password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            username=user_data.username,
        )
        return UserResponse(**user.dict() if hasattr(user, 'dict') else user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/me", response_model=UserWithOrganizationsResponse)
async def get_current_user_profile(
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Get current user profile.
    
    Rules:
        Returns complete profile including organization memberships
        Always accessible to authenticated user
    """
    try:
        user_profile = await services.users.get_user_profile(current_user.id)
        organizations = await services.users.get_user_organizations(current_user.id)
        
        return UserWithOrganizationsResponse(
            **user_profile.dict() if hasattr(user_profile, 'dict') else user_profile,
            organizations=organizations,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Get user by ID.
    
    Rules:
        Users can view their own profile
        Admins can view any user profile
        Excludes sensitive fields
    """
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view other user profiles",
        )
    
    try:
        user = await services.users.get_user_by_id(user_id)
        return UserResponse(**user.dict() if hasattr(user, 'dict') else user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Update user profile.
    
    Rules:
        Users can update their own profile
        Admins can update any user profile
        Email changes require verification
    """
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update other user profiles",
        )
    
    try:
        user = await services.users.update_user(
            user_id=user_id,
            updates=user_data.dict(exclude_unset=True),
            current_user_id=current_user.id,
        )
        return UserResponse(**user.dict() if hasattr(user, 'dict') else user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    user_id: int,
    password_data: PasswordChange,
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> None:
    """Change user password.
    
    Rules:
        Users can change their own password with current password
        Admins can change any password without current password
        Invalidates all existing sessions
    """
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change other user passwords",
        )
    
    try:
        await services.users.update_password(
            user_id=user_id,
            current_password=password_data.current_password if user_id == current_user.id else None,
            new_password=password_data.new_password,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{user_id}/verify-email/initiate")
async def initiate_email_verification(
    user_id: int,
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> dict:
    """Initiate email verification process.
    
    Rules:
        Users can initiate for themselves
        Admins can initiate for any user
        Sends verification email
    """
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot initiate verification for other users",
        )
    
    try:
        token = await services.users.initiate_email_verification(user_id)
        return {"message": "Verification email sent", "token": token}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{user_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: int,
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> None:
    """Deactivate user account (soft delete).
    
    Rules:
        Users can deactivate themselves
        Admins can deactivate any user
        Preserves data for compliance
    """
    if user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot deactivate other users",
        )
    
    try:
        await services.users.deactivate_user(
            user_id=user_id,
            deactivated_by=current_user.id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{user_id}/reactivate", response_model=UserResponse)
async def reactivate_user(
    user_id: int,
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Reactivate previously deactivated user (admin only).
    
    Rules:
        Requires superuser privileges
        Restores user access
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    
    try:
        user = await services.users.reactivate_user(
            user_id=user_id,
            reactivated_by=current_user.id,
        )
        return UserResponse(**user.dict() if hasattr(user, 'dict') else user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/search/by-email", response_model=UserResponse)
async def search_user_by_email(
    email: EmailStr = Query(..., description="Email address to search"),
    services: ServiceContainer = Depends(get_services),
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Search user by email (admin only).
    
    Rules:
        Requires superuser privileges
        Returns user profile
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    
    try:
        user = await services.users.get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return UserResponse(**user.dict() if hasattr(user, 'dict') else user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )