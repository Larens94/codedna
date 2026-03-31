"""app/services/auth_service.py — Authentication and authorization service.

exports: AuthService
used_by: app/services/container.py → ServiceContainer.auth, API auth endpoints
rules:   must validate JWT tokens, hash passwords with argon2, handle refresh tokens
agent:   Product Architect | 2024-03-30 | created auth service skeleton
         message: "implement password strength validation and account lockout after failed attempts"
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.exceptions import AuthenticationError, AuthorizationError, InvalidTokenError
from app.services.container import ServiceContainer

logger = logging.getLogger(__name__)

# In-memory refresh token store: {redis_key: "valid"} — replaces Redis for dev/demo
_refresh_token_store: Dict[str, str] = {}


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str


class AuthService:
    """Authentication and authorization service.
    
    Rules:
        All password hashing uses argon2
        JWT tokens must be signed with strong secret key
        Refresh tokens are stored in Redis for revocation
        All authentication events are logged for audit
    """
    
    def __init__(self, container: ServiceContainer):
        """Initialize auth service.
        
        Args:
            container: Service container with dependencies
        """
        self.container = container
        self.config = container.config
        
        # Password hashing context
        self.pwd_context = CryptContext(
            schemes=["argon2"],
            deprecated="auto",
        )
        
        # JWT configuration
        self.jwt_secret_key = self.config.JWT_SECRET_KEY
        self.jwt_algorithm = self.config.JWT_ALGORITHM
        self.access_token_expire_minutes = self.config.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = self.config.REFRESH_TOKEN_EXPIRE_DAYS
        
        logger.info("AuthService initialized")
    
    # --- Password Hashing ---
    
    def hash_password(self, password: str) -> str:
        """Hash password using argon2.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
            
        Rules:
            Must use argon2 with appropriate parameters
            Must include salt automatically
        """
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash.
        
        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to compare against
            
        Returns:
            True if password matches, False otherwise
        """
        return self.pwd_context.verify(plain_password, hashed_password)
    
    # --- JWT Token Generation ---
    
    def create_access_token(self, user_id: str, organization_id: str, roles: list) -> str:
        """Create JWT access token.
        
        Args:
            user_id: User ID (UUID string)
            organization_id: Organization ID (UUID string)
            roles: List of user roles
            
        Returns:
            JWT access token
            
        Rules:
            Token expires in ACCESS_TOKEN_EXPIRE_MINUTES
            Includes user_id, organization_id, roles, and token type
        """
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "sub": user_id,
            "org": organization_id,
            "roles": roles,
            "type": "access",
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4()),  # Unique token ID for revocation tracking
        }
        
        token = jwt.encode(payload, self.jwt_secret_key, algorithm=self.jwt_algorithm)
        return token
    
    def create_refresh_token(self, user_id: str) -> Tuple[str, str]:
        """Create refresh token and store it in Redis.
        
        Args:
            user_id: User ID (UUID string)
            
        Returns:
            Tuple of (refresh_token, token_id)
            
        Rules:
            Refresh token expires in REFRESH_TOKEN_EXPIRE_DAYS
            Token ID is stored in Redis for revocation
            Each user can have multiple refresh tokens (for multiple devices)
        """
        token_id = str(uuid.uuid4())
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "sub": user_id,
            "type": "refresh",
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": token_id,
        }
        
        token = jwt.encode(payload, self.jwt_secret_key, algorithm=self.jwt_algorithm)

        # Store refresh token in in-memory store (replaces Redis for dev/demo)
        redis_key = f"refresh_token:{user_id}:{token_id}"
        _refresh_token_store[redis_key] = "valid"

        return token, token_id
    
    # --- Token Validation ---
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate JWT token.
        
        Args:
            token: JWT token to decode
            
        Returns:
            Decoded token payload
            
        Raises:
            InvalidTokenError: If token is invalid, expired, or malformed
        """
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret_key,
                algorithms=[self.jwt_algorithm],
            )
            return payload
        except JWTError as e:
            logger.warning(f"JWT decode error: {e}")
            raise InvalidTokenError(f"Invalid token: {e}")
    
    def verify_access_token(self, token: str) -> Dict[str, Any]:
        """Verify access token and return payload.
        
        Args:
            token: JWT access token
            
        Returns:
            Decoded token payload
            
        Raises:
            InvalidTokenError: If token is invalid or expired
            AuthenticationError: If token is not an access token
        """
        payload = self.decode_token(token)
        
        # Check token type
        if payload.get("type") != "access":
            raise AuthenticationError("Invalid token type")
        
        return payload
    
    def verify_refresh_token(self, token: str) -> Tuple[Dict[str, Any], str]:
        """Verify refresh token and check if it's revoked.
        
        Args:
            token: JWT refresh token
            
        Returns:
            Tuple of (payload, token_id)
            
        Raises:
            InvalidTokenError: If token is invalid or expired
            AuthenticationError: If token is not a refresh token or is revoked
        """
        payload = self.decode_token(token)
        
        # Check token type
        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid token type")
        
        token_id = payload.get("jti")
        user_id = payload.get("sub")
        
        if not token_id or not user_id:
            raise InvalidTokenError("Malformed refresh token")
        
        # Check if token exists in in-memory store
        redis_key = f"refresh_token:{user_id}:{token_id}"
        if redis_key not in _refresh_token_store:
            raise AuthenticationError("Refresh token revoked")
        
        return payload, token_id
    
    # --- Authentication ---
    
    async def authenticate_user(self, email: str, password: str) -> TokenPair:
        """Authenticate user and return access + refresh tokens.

        Raises:
            AuthenticationError: If credentials are invalid or account inactive.
        """
        user = await self.container.users.get_user_by_email(email)
        if not user:
            self.verify_password(password, "$argon2id$v=19$m=65536,t=3,p=4$dummy$dummy")
            raise AuthenticationError("Invalid credentials")

        if not user.get("is_active"):
            raise AuthenticationError("Account is deactivated")

        if not self.verify_password(password, user["hashed_password"]):
            raise AuthenticationError("Invalid credentials")

        await self.container.users.update_last_login(user["id"])

        user_id = str(user["id"])
        access_token = self.create_access_token(
            user_id=user_id,
            organization_id="default",
            roles=["org_member"],
        )
        refresh_token, _ = self.create_refresh_token(user_id=user_id)
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    async def get_current_user(self, token: str):
        """Validate access token and return a UserRecord.

        Raises:
            AuthenticationError: If token is invalid or user not found.
        """
        from app.services.user_service import UserRecord
        payload = self.verify_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Invalid token payload")

        user_dict = await self.container.users.get_user_by_id(user_id)
        if not user_dict:
            raise AuthenticationError("User not found")

        return UserRecord(
            id=user_dict["id"],
            email=user_dict["email"],
            first_name=user_dict.get("first_name"),
            last_name=user_dict.get("last_name"),
            username=user_dict.get("username"),
            is_active=user_dict.get("is_active", True),
            email_verified=user_dict.get("email_verified", True),
            created_at=user_dict.get("created_at"),
            hashed_password=user_dict.get("hashed_password", ""),
        )
    
    async def refresh_tokens(self, refresh_token: str) -> TokenPair:
        """Issue a new TokenPair from a valid refresh token (rotation)."""
        payload, token_id = self.verify_refresh_token(refresh_token)
        user_id = payload["sub"]

        # Revoke old token
        old_key = f"refresh_token:{user_id}:{token_id}"
        _refresh_token_store.pop(old_key, None)

        # Issue new tokens
        access_token = self.create_access_token(
            user_id=user_id,
            organization_id="default",
            roles=["org_member"],
        )
        new_refresh_token, _ = self.create_refresh_token(user_id=user_id)
        return TokenPair(access_token=access_token, refresh_token=new_refresh_token)

    async def logout(self, token: str) -> None:
        """Invalidate access token (no-op for in-memory store)."""
        try:
            payload = self.verify_access_token(token)
            # In production: blacklist the token JTI in Redis
        except Exception:
            pass  # Already invalid, ignore

    async def revoke_refresh_token(self, user_id: str, token_id: str) -> None:
        """Revoke a specific refresh token."""
        redis_key = f"refresh_token:{user_id}:{token_id}"
        _refresh_token_store.pop(redis_key, None)

    async def revoke_all_refresh_tokens(self, user_id: str) -> None:
        """Revoke all refresh tokens for a user."""
        keys_to_remove = [k for k in _refresh_token_store if k.startswith(f"refresh_token:{user_id}:")]
        for k in keys_to_remove:
            del _refresh_token_store[k]
    
    # --- Authorization ---
    
    def check_permission(self, user_roles: list, required_roles: list) -> bool:
        """Check if user has required role(s).
        
        Args:
            user_roles: List of user roles
            required_roles: List of required roles (any of them)
            
        Returns:
            True if user has at least one required role
            
        Rules:
            Super admin bypasses all checks
            Role hierarchy: super_admin > org_admin > org_member
        """
        # Super admin can do anything
        if "super_admin" in user_roles:
            return True
        
        # Check if user has any required role
        return any(role in user_roles for role in required_roles)
    
    def require_permission(self, user_roles: list, required_roles: list) -> None:
        """Check permission and raise AuthorizationError if not granted.
        
        Args:
            user_roles: List of user roles
            required_roles: List of required roles
            
        Raises:
            AuthorizationError: If user doesn't have required permission
        """
        if not self.check_permission(user_roles, required_roles):
            raise AuthorizationError(
                f"Required roles: {required_roles}, User roles: {user_roles}"
            )
    
    # --- API Key Authentication ---
    
    async def authenticate_api_key(self, api_key: str) -> Dict[str, Any]:
        """Authenticate agent using API key.
        
        Args:
            api_key: Agent API key
            
        Returns:
            Agent information if authentication successful
            
        Raises:
            AuthenticationError: If API key is invalid
        """
        # TODO: Implement API key authentication
        # 1. Hash the provided API key
        # 2. Look up agent by hashed API key
        # 3. Check if agent is active
        # 4. Update last used timestamp
        # 5. Return agent information
        
        raise NotImplementedError("API key authentication not yet implemented")