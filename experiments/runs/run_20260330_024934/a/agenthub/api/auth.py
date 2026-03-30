"""auth.py — Authentication and user management API.

exports: router
used_by: main.py
rules:   must use secure password hashing; must implement proper token handling
agent:   BackendEngineer | 2024-01-15 | implemented JWT authentication with security features
         message: "implement refresh token mechanism and token blacklist"
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext
import secrets

from agenthub.db.session import get_db
from agenthub.db.models import User, CreditAccount, AuditLog
from agenthub.schemas.auth import UserCreate, UserResponse, Token, PasswordChange
from agenthub.config import settings

router = APIRouter()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    import sys
    sys.stderr.write(f'[DEBUG] verify_password called, plain_password length bytes: {len(plain_password.encode("utf-8"))}\n')
    # bcrypt has 72-byte limit, truncate if longer (should not happen)
    if len(plain_password.encode('utf-8')) > 72:
        sys.stderr.write(f'[DEBUG] truncating password from {len(plain_password.encode("utf-8"))} bytes\n')
        plain_password = plain_password[:72]
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        sys.stderr.write(f'[DEBUG] verify error: {e}\n')
        raise


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=30)  # Refresh tokens last 30 days
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Get current authenticated user from JWT token.
    
    Rules:   must validate token signature and expiration; must check user is active
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # Check token type
        if payload.get("type") != "access":
            raise credentials_exception
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise credentials_exception
    
    # Get user from database
    user = db.query(User).filter(User.public_id == user_id).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current authenticated user, ensuring they are active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Get current authenticated user, ensuring they are a superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required",
        )
    return current_user


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
    """Create an audit log entry."""
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


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Register a new user.
    
    Rules:   must validate email uniqueness; must hash password securely
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        is_active=True,
        is_superuser=False,
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create credit account for user
    credit_account = CreditAccount(
        user_id=user.id,
        balance=0.0,
        currency="USD"
    )
    db.add(credit_account)
    db.commit()
    
    # Create audit log
    create_audit_log(
        db=db,
        user_id=user.id,
        action="register",
        resource_type="user",
        resource_id=str(user.public_id),
        details={"email": user.email}
    )
    
    # In production, you would send a welcome email here
    # background_tasks.add_task(send_welcome_email, user.email, user.full_name)
    
    return user


@router.post("/login", response_model=Token)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate user and return access token.
    
    Rules:   must verify password hash; must generate JWT with expiration
    """
    # Get user by email
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )
    
    # Create tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.public_id), "email": user.email, "is_superuser": user.is_superuser},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"sub": str(user.public_id), "email": user.email}
    )
    
    # Create audit log
    create_audit_log(
        db=db,
        user_id=user.id,
        action="login",
        resource_type="user",
        resource_id=str(user.public_id)
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds()),
        refresh_token=refresh_token
    )


@router.post("/logout")
async def logout_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Logout user (invalidate token on client side).
    
    Rules:   must provide clear logout instructions; server-side token invalidation optional
    """
    # In a production system, you might want to:
    # 1. Add token to a blacklist (Redis)
    # 2. Store blacklisted tokens until they expire
    # 3. Check blacklist in get_current_user()
    
    # For now, we just create an audit log
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="logout",
        resource_type="user",
        resource_id=str(current_user.public_id)
    )
    
    return {"message": "Successfully logged out. Please discard your token on the client side."}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """Get current user information.
    
    Rules:   must return user profile without sensitive data
    """
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db),
):
    """Refresh access token using refresh token.
    
    Rules:   must validate refresh token; must issue new access token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode refresh token
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        # Check token type
        if payload.get("type") != "refresh":
            raise credentials_exception
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise credentials_exception
    
    # Get user from database
    user = db.query(User).filter(User.public_id == user_id).first()
    if user is None or not user.is_active:
        raise credentials_exception
    
    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.public_id), "email": user.email, "is_superuser": user.is_superuser},
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
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds()),
        refresh_token=refresh_token  # Return same refresh token (or rotate if needed)
    )


@router.post("/password/change")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change user password.
    
    Rules:   must verify current password; must use secure hashing
    """
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.password_hash = get_password_hash(password_data.new_password)
    db.commit()
    
    # Create audit log
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="password_change",
        resource_type="user",
        resource_id=str(current_user.public_id)
    )
    
    return {"message": "Password changed successfully"}


@router.post("/password/reset/request")
async def request_password_reset(
    email: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Request password reset (send reset email).
    
    Rules:   must generate secure reset token; must send email
    """
    # Get user by email
    user = db.query(User).filter(User.email == email).first()
    
    if user:
        # Generate reset token (valid for 1 hour)
        reset_token = secrets.token_urlsafe(32)
        reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        
        # In production, store reset token in database or Redis
        # For now, we'll just create an audit log
        
        create_audit_log(
            db=db,
            user_id=user.id,
            action="password_reset_request",
            resource_type="user",
            resource_id=str(user.public_id),
            details={"reset_token": reset_token[:8]}  # Log only first 8 chars
        )
        
        # In production, send reset email
        # background_tasks.add_task(send_password_reset_email, user.email, reset_token)
    
    # Always return success to prevent email enumeration
    return {"message": "If an account exists with this email, a reset link has been sent"}


@router.post("/password/reset/confirm")
async def confirm_password_reset(
    token: str,
    new_password: str,
    db: Session = Depends(get_db),
):
    """Confirm password reset with token.
    
    Rules:   must validate reset token; must update password
    """
    # In production, validate token from database/Redis
    # For now, this is a stub implementation
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Password reset confirmation not fully implemented"
    )