"""app/services/user_service.py — User management service.

exports: UserService
used_by: app/services/container.py → ServiceContainer.users, API user endpoints
rules:   must validate email uniqueness; handle soft deletes; enforce organization membership
agent:   Product Architect | 2024-03-30 | created user service skeleton
         message: "implement email verification flow with expiration and rate limiting"
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.exceptions import NotFoundError, ConflictError, ValidationError
from app.services.container import ServiceContainer

logger = logging.getLogger(__name__)

# In-memory user store (keyed by email) — dev/demo only; no Postgres needed
_users_by_email: Dict[str, Dict[str, Any]] = {}
_users_by_id: Dict[str, Dict[str, Any]] = {}


@dataclass
class UserRecord:
    id: int
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    username: Optional[str]
    is_active: bool
    email_verified: bool
    created_at: datetime
    hashed_password: str


class UserService:
    """User management service.
    
    Rules:
        All user operations must respect organization boundaries
        Email addresses must be unique across the system
        Soft deletes only - never permanently delete user data without compliance approval
        Password updates require current password verification
    """
    
    def __init__(self, container: ServiceContainer):
        """Initialize user service.
        
        Args:
            container: Service container with dependencies
        """
        self.container = container
        logger.info("UserService initialized")
    
    async def get_user_by_id(self, user_id: str) -> Dict[str, Any]:
        """Get user by ID.
        
        Args:
            user_id: User ID (UUID string)
            
        Returns:
            User information (excluding sensitive fields)
            
        Raises:
            NotFoundError: If user doesn't exist
        """
        # TODO: Implement database query
        # 1. Query users table by ID
        # 2. Include organization information
        # 3. Exclude hashed_password, email_verification_token, etc.
        # 4. Raise NotFoundError if not found or soft-deleted
        
        raise NotImplementedError("get_user_by_id not yet implemented")
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email (including sensitive fields for authentication)."""
        return _users_by_email.get(email.lower())
    
    async def create_user(
        self,
        email: str,
        password: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        username: Optional[str] = None,
        organization_id: Optional[str] = None,
    ) -> "UserRecord":
        """Create new user (in-memory store for dev/demo)."""
        email_lower = email.lower()
        if email_lower in _users_by_email:
            raise ConflictError(f"Email already registered: {email}")

        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
        hashed = pwd_context.hash(password)

        user_id = len(_users_by_id) + 1
        record = {
            "id": user_id,
            "email": email_lower,
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "is_active": True,
            "email_verified": True,   # skip email verification in dev
            "created_at": datetime.utcnow(),
            "hashed_password": hashed,
        }
        _users_by_email[email_lower] = record
        _users_by_id[str(user_id)] = record

        return UserRecord(
            id=user_id,
            email=email_lower,
            first_name=first_name,
            last_name=last_name,
            username=username,
            is_active=True,
            email_verified=True,
            created_at=record["created_at"],
            hashed_password=hashed,
        )
    
    async def update_user(
        self,
        user_id: str,
        updates: Dict[str, Any],
        current_user_id: str,
    ) -> Dict[str, Any]:
        """Update user information.
        
        Args:
            user_id: User ID to update
            updates: Dictionary of fields to update
            current_user_id: ID of user making the request (for authorization)
            
        Returns:
            Updated user information
            
        Raises:
            NotFoundError: If user doesn't exist
            AuthorizationError: If current user doesn't have permission
            ValidationError: If updates are invalid
        """
        # TODO: Implement user update
        # 1. Check permissions (users can update themselves, org admins can update members)
        # 2. Validate updates (can't change email without verification, etc.)
        # 3. Update user record
        # 4. Return updated user information
        
        raise NotImplementedError("update_user not yet implemented")
    
    async def update_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
    ) -> None:
        """Update user password.
        
        Args:
            user_id: User ID
            current_password: Current plain text password for verification
            new_password: New plain text password
            
        Raises:
            NotFoundError: If user doesn't exist
            AuthenticationError: If current password is incorrect
            ValidationError: If new password doesn't meet requirements
        """
        # TODO: Implement password update
        # 1. Get user with hashed_password
        # 2. Verify current password
        # 3. Validate new password strength
        # 4. Hash new password
        # 5. Update user record
        # 6. Revoke all refresh tokens (force re-login on all devices)
        
        raise NotImplementedError("update_password not yet implemented")
    
    async def deactivate_user(self, user_id: str, deactivated_by: str) -> None:
        """Deactivate user account (soft delete).
        
        Args:
            user_id: User ID to deactivate
            deactivated_by: ID of user performing deactivation
            
        Raises:
            NotFoundError: If user doesn't exist
            AuthorizationError: If not authorized to deactivate user
        """
        # TODO: Implement user deactivation
        # 1. Check permissions (users can deactivate themselves, super admins can deactivate anyone)
        # 2. Update user: is_active=False, deleted_at=now, deleted_by=deactivated_by
        # 3. Revoke all refresh tokens
        # 4. Log deactivation event
        
        raise NotImplementedError("deactivate_user not yet implemented")
    
    async def reactivate_user(self, user_id: str, reactivated_by: str) -> Dict[str, Any]:
        """Reactivate previously deactivated user.
        
        Args:
            user_id: User ID to reactivate
            reactivated_by: ID of user performing reactivation
            
        Returns:
            Reactivated user information
            
        Raises:
            NotFoundError: If user doesn't exist
            AuthorizationError: If not authorized to reactivate user
        """
        # TODO: Implement user reactivation
        # 1. Check permissions (super admin only)
        # 2. Update user: is_active=True, deleted_at=None, deleted_by=None
        # 3. Return user information
        
        raise NotImplementedError("reactivate_user not yet implemented")
    
    async def update_last_login(self, user_id: str) -> None:
        """Update user's last login timestamp (in-memory)."""
        record = _users_by_id.get(str(user_id))
        if record:
            record["last_login_at"] = datetime.utcnow()

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID from in-memory store."""
        return _users_by_id.get(str(user_id))
    
    async def initiate_email_verification(self, user_id: str) -> str:
        """Initiate email verification process.
        
        Args:
            user_id: User ID
            
        Returns:
            Verification token (for testing)
            
        Raises:
            NotFoundError: If user doesn't exist
        """
        # TODO: Implement email verification initiation
        # 1. Generate verification token with expiration
        # 2. Store token hash in database
        # 3. Send verification email with link
        # 4. Return token (for testing only)
        
        raise NotImplementedError("initiate_email_verification not yet implemented")
    
    async def verify_email(self, token: str) -> Dict[str, Any]:
        """Verify email using verification token.
        
        Args:
            token: Verification token
            
        Returns:
            User information after verification
            
        Raises:
            AuthenticationError: If token is invalid or expired
        """
        # TODO: Implement email verification
        # 1. Hash token and look up user
        # 2. Check token expiration
        # 3. Update user: is_verified=True, email_verified_at=now()
        # 4. Clear verification token
        # 5. Return user information
        
        raise NotImplementedError("verify_email not yet implemented")
    
    async def list_users(
        self,
        organization_id: str,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """List users in organization with pagination.
        
        Args:
            organization_id: Organization ID
            page: Page number (1-indexed)
            per_page: Number of users per page
            search: Optional search term for email or name
            role: Optional role filter
            is_active: Optional active status filter
            
        Returns:
            Dictionary with users list and pagination metadata
        """
        # TODO: Implement user listing
        # 1. Query organization_members join users
        # 2. Apply filters
        # 3. Apply pagination
        # 4. Return users (excluding sensitive fields) and pagination info
        
        raise NotImplementedError("list_users not yet implemented")
    
    async def get_user_organizations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all organizations a user belongs to.
        
        Args:
            user_id: User ID
            
        Returns:
            List of organizations with membership details
        """
        # TODO: Implement user organizations query
        # 1. Query organization_members join organizations
        # 2. Return list with organization details and member role
        
        raise NotImplementedError("get_user_organizations not yet implemented")