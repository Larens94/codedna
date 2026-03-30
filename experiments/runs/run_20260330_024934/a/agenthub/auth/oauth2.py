"""oauth2.py — OAuth2 authentication scheme and login route.

exports: oauth2_scheme, router, login_for_access_token
used_by: main.py → router registration, dependencies.py → get_current_user
rules:   must implement OAuth2 password flow; must return JWT tokens
agent:   FrontendDesigner | 2024-01-15 | OAuth2 authentication implementation
         message: "implement social OAuth2 providers (Google, GitHub)"
"""

from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from agenthub.auth.jwt import create_access_token, create_refresh_token
from agenthub.auth.security import verify_password
from agenthub.db.session import get_db
from agenthub.db.models import User, AuditLog
from agenthub.config import settings

router = APIRouter()

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=True
)


def create_audit_log(
    db: Session,
    user_id: Optional[int],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """Create an audit log entry for authentication events."""
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(audit_log)
    db.commit()


@router.post("/login", response_model=dict)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> dict:
    """OAuth2 password flow login endpoint.
    
    Args:
        form_data: OAuth2 form data (username=email, password)
        db: Database session
        
    Returns:
        Dictionary with access_token, token_type, expires_in, and refresh_token
        
    Raises:
        HTTPException: If authentication fails
        
    Rules:
        - Must validate email and password
        - Must check user is active
        - Must return JWT access token and refresh token
        - Must create audit log entry
    """
    # Get user by email (username field in OAuth2 form)
    user = db.query(User).filter(User.email == form_data.username).first()
    
    # Authentication failure
    if not user or not verify_password(form_data.password, user.password_hash):
        # Create audit log for failed login attempt
        create_audit_log(
            db=db,
            user_id=None,
            action="login_failed",
            resource_type="user",
            details={"email": form_data.username, "reason": "invalid_credentials"}
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        create_audit_log(
            db=db,
            user_id=user.id,
            action="login_blocked",
            resource_type="user",
            resource_id=str(user.public_id),
            details={"reason": "inactive_account"}
        )
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": str(user.public_id),
            "email": user.email,
            "is_superuser": user.is_superuser,
            "name": user.full_name or user.email.split('@')[0]
        },
        expires_delta=access_token_expires
    )
    
    # Create refresh token
    refresh_token = create_refresh_token(
        data={
            "sub": str(user.public_id),
            "email": user.email
        }
    )
    
    # Create audit log for successful login
    create_audit_log(
        db=db,
        user_id=user.id,
        action="login_success",
        resource_type="user",
        resource_id=str(user.public_id)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": int(access_token_expires.total_seconds()),
        "refresh_token": refresh_token,
        "user": {
            "id": str(user.public_id),
            "email": user.email,
            "name": user.full_name or user.email.split('@')[0],
            "is_superuser": user.is_superuser
        }
    }


@router.post("/refresh", response_model=dict)
async def refresh_access_token(
    refresh_token: str,
    db: Session = Depends(get_db),
) -> dict:
    """Refresh access token using refresh token.
    
    Args:
        refresh_token: Valid refresh token
        db: Database session
        
    Returns:
        New access token
        
    Raises:
        HTTPException: If refresh token is invalid
        
    Rules:
        - Must validate refresh token
        - Must check user exists and is active
        - Must return new access token
    """
    from agenthub.auth.jwt import decode_token
    
    try:
        # Decode refresh token
        payload = decode_token(refresh_token)
        
        # Check token type
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user ID from token
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user from database
        user = db.query(User).filter(User.public_id == user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": str(user.public_id),
                "email": user.email,
                "is_superuser": user.is_superuser,
                "name": user.full_name or user.email.split('@')[0]
            },
            expires_delta=access_token_expires
        )
        
        # Create audit log
        create_audit_log(
            db=db,
            user_id=user.id,
            action="token_refresh",
            resource_type="user",
            resource_id=str(user.public_id)
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": int(access_token_expires.total_seconds())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/logout")
async def logout_user(
    current_user: User = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> dict:
    """Logout user (client-side token invalidation).
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Success message
        
    Rules:
        - Must create audit log
        - Must provide guidance for client-side token invalidation
    """
    # In production, you would:
    # 1. Add token to blacklist (Redis)
    # 2. Store until token expiration
    # 3. Check blacklist in token validation
    
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="logout",
        resource_type="user",
        resource_id=str(current_user.public_id)
    )
    
    return {
        "message": "Successfully logged out. Please discard your tokens on the client side.",
        "instructions": [
            "Remove access_token from localStorage/sessionStorage",
            "Remove refresh_token from secure storage",
            "Clear authentication headers from API client"
        ]
    }


@router.get("/me", response_model=dict)
async def get_current_user_info(
    current_user: User = Depends(oauth2_scheme),
) -> dict:
    """Get current authenticated user information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User information (excluding sensitive data)
        
    Rules:
        - Must not return password hash or other sensitive data
        - Must include user roles and permissions
    """
    return {
        "id": str(current_user.public_id),
        "email": current_user.email,
        "name": current_user.full_name or current_user.email.split('@')[0],
        "is_superuser": current_user.is_superuser,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "updated_at": current_user.updated_at.isoformat() if current_user.updated_at else None
    }


@router.post("/validate")
async def validate_token(
    token: str = Depends(oauth2_scheme),
) -> dict:
    """Validate an access token.
    
    Args:
        token: JWT access token
        
    Returns:
        Token validation result
        
    Rules:
        - Must validate token signature and expiration
        - Must return token claims if valid
    """
    from agenthub.auth.jwt import decode_token
    
    try:
        payload = decode_token(token)
        
        # Check token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        
        return {
            "valid": True,
            "claims": {
                "sub": payload.get("sub"),
                "email": payload.get("email"),
                "is_superuser": payload.get("is_superuser"),
                "exp": payload.get("exp"),
                "iat": payload.get("iat")
            }
        }
        
    except HTTPException as e:
        return {
            "valid": False,
            "error": e.detail,
            "status_code": e.status_code
        }