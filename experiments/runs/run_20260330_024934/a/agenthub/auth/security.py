"""security.py — Password hashing and API key generation utilities.

exports: hash_password, verify_password, generate_api_key
used_by: api/auth.py → register_user, change_password; api/users.py → create_api_key
rules:   must use bcrypt for passwords; must generate cryptographically secure API keys
agent:   FrontendDesigner | 2024-01-15 | Security utilities for authentication
         message: "implement API key rate limiting and usage tracking"
"""

import secrets
import hashlib
from typing import Tuple
from passlib.context import CryptContext

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hash a plain text password using bcrypt.
    
    Args:
        plain_password: Plain text password to hash
        
    Returns:
        Hashed password string
        
    Rules:
        - Must use bcrypt with appropriate work factor
        - Must return string suitable for database storage
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
        
    Returns:
        True if password matches hash, False otherwise
        
    Rules:
        - Must be timing-attack resistant
        - Must handle bcrypt verification errors gracefully
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # Log the error in production
        return False


def generate_api_key() -> str:
    """Generate a cryptographically secure API key.
    
    Returns:
        API key as hexadecimal string (64 characters)
        
    Rules:
        - Must use cryptographically secure random generator
        - Must return hex string for easy storage and transmission
        - Must be sufficiently long (32 bytes = 256 bits)
    """
    # Generate 32 random bytes (256 bits)
    random_bytes = secrets.token_bytes(32)
    
    # Convert to hexadecimal string
    api_key = random_bytes.hex()
    
    return api_key


def generate_api_key_pair() -> Tuple[str, str]:
    """Generate an API key pair (public ID and secret key).
    
    Returns:
        Tuple of (public_id, secret_key)
        
    Rules:
        - Public ID should be shorter and can be shown to users
        - Secret key should be longer and kept confidential
        - Both must be cryptographically secure
    """
    # Generate public ID (16 bytes = 128 bits)
    public_id_bytes = secrets.token_bytes(16)
    public_id = public_id_bytes.hex()
    
    # Generate secret key (32 bytes = 256 bits)
    secret_key_bytes = secrets.token_bytes(32)
    secret_key = secret_key_bytes.hex()
    
    return public_id, secret_key


def hash_api_key(api_key: str) -> str:
    """Hash an API key for secure storage.
    
    Args:
        api_key: Plain API key string
        
    Returns:
        Hashed API key using SHA-256
        
    Rules:
        - Must use cryptographic hash function
        - Must be one-way (cannot retrieve original key)
        - Must be deterministic (same input = same output)
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(provided_key: str, stored_hash: str) -> bool:
    """Verify an API key against its stored hash.
    
    Args:
        provided_key: API key provided by user
        stored_hash: Hashed API key stored in database
        
    Returns:
        True if key matches hash, False otherwise
        
    Rules:
        - Must use constant-time comparison
        - Must handle verification errors gracefully
    """
    try:
        # Hash the provided key
        provided_hash = hash_api_key(provided_key)
        
        # Use secrets.compare_digest for constant-time comparison
        return secrets.compare_digest(provided_hash, stored_hash)
    except Exception:
        # Log the error in production
        return False


def generate_password_reset_token() -> str:
    """Generate a secure password reset token.
    
    Returns:
        URL-safe token string
        
    Rules:
        - Must be sufficiently long for security
        - Must be URL-safe for email links
        - Must be cryptographically secure
    """
    return secrets.token_urlsafe(32)


def generate_email_verification_token() -> str:
    """Generate a secure email verification token.
    
    Returns:
        URL-safe token string
        
    Rules:
        - Must be sufficiently long for security
        - Must be URL-safe for email links
        - Must be cryptographically secure
    """
    return secrets.token_urlsafe(24)


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """Validate password strength.
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Rules:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)
    
    if not has_upper:
        return False, "Password must contain at least one uppercase letter"
    if not has_lower:
        return False, "Password must contain at least one lowercase letter"
    if not has_digit:
        return False, "Password must contain at least one digit"
    if not has_special:
        return False, "Password must contain at least one special character"
    
    return True, "Password is strong"


def generate_secure_random_string(length: int = 32) -> str:
    """Generate a cryptographically secure random string.
    
    Args:
        length: Length of the string in bytes (default: 32)
        
    Returns:
        URL-safe random string
        
    Rules:
        - Must use cryptographically secure random generator
        - Must be URL-safe
    """
    return secrets.token_urlsafe(length)


def mask_api_key(api_key: str, visible_chars: int = 4) -> str:
    """Mask an API key for display purposes.
    
    Args:
        api_key: Full API key
        visible_chars: Number of characters to show at the end
        
    Returns:
        Masked API key (e.g., "****...abcd")
        
    Rules:
        - Must hide most of the key for security
        - Should show last few characters for identification
    """
    if len(api_key) <= visible_chars:
        return "*" * len(api_key)
    
    hidden_part = "*" * (len(api_key) - visible_chars)
    visible_part = api_key[-visible_chars:]
    
    return f"{hidden_part}{visible_part}"