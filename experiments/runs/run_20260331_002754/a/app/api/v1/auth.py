"""app/api/v1/auth.py — Authentication endpoints (login, register, token refresh).

exports: router (auth endpoints)
used_by: app/api/v1/__init__.py → router inclusion
rules:   passwords must be hashed with argon2; refresh tokens must be stored securely
agent:   Product Architect | 2024-03-30 | created authentication endpoints
         message: "verify that refresh token rotation prevents replay attacks"
"""

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field

from app.services import ServiceContainer, get_services

# Create router
router = APIRouter(tags=["authentication"])

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# Request/Response Models
class UserRegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    username: str | None = Field(None, min_length=3, max_length=100)


class UserRegisterResponse(BaseModel):
    """User registration response."""
    id: int
    email: str
    message: str


class TokenResponse(BaseModel):
    """Token response for login/refresh."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str


class UserProfileResponse(BaseModel):
    """User profile response."""
    id: int
    email: str
    first_name: str | None
    last_name: str | None
    username: str | None
    is_active: bool
    email_verified: bool
    created_at: str


@router.post("/register", response_model=UserRegisterResponse)
async def register_user(
    request: UserRegisterRequest,
    services: ServiceContainer = Depends(get_services),
) -> Any:
    """Register a new user.
    
    Rules:
        Email must be unique
        Password is hashed with argon2
        Email verification is required before login
    """
    try:
        user = await services.users.create_user(
            email=request.email,
            password=request.password,
            first_name=request.first_name,
            last_name=request.last_name,
            username=request.username,
        )
        
        # TODO: Send email verification
        
        return UserRegisterResponse(
            id=user.id,
            email=user.email,
            message="User registered successfully. Please check your email for verification.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    services: ServiceContainer = Depends(get_services),
) -> Any:
    """Login with email and password.
    
    Rules:
        User must be active and email verified
        Returns access token and refresh token
        Updates last login timestamp
    """
    try:
        tokens = await services.auth.authenticate_user(
            email=form_data.username,  # OAuth2 uses username field for email
            password=form_data.password,
        )
        
        return TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=timedelta(minutes=15).seconds,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: TokenRefreshRequest,
    services: ServiceContainer = Depends(get_services),
) -> Any:
    """Refresh access token using refresh token.
    
    Rules:
        Refresh token must be valid and not expired
        Old refresh token is invalidated
        New refresh token is issued (rotation)
    """
    try:
        tokens = await services.auth.refresh_tokens(request.refresh_token)
        
        return TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=timedelta(minutes=15).seconds,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
    services: ServiceContainer = Depends(get_services),
) -> Any:
    """Logout user by invalidating tokens.
    
    Rules:
        Access token is blacklisted
        Refresh token is revoked
    """
    await services.auth.logout(token)
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user(
    services: ServiceContainer = Depends(get_services),
    token: str = Depends(oauth2_scheme),
) -> Any:
    """Get current user profile.
    
    Rules:
        Requires valid access token
        Returns user profile information
    """
    user = await services.auth.get_current_user(token)
    
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        is_active=user.is_active,
        email_verified=user.email_verified,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )