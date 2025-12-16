"""
Security utilities for password hashing and JWT token management.

Uses:
- passlib + bcrypt for password hashing (industry standard, secure)
- PyJWT for JWT token creation and validation
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import pytz
from passlib.context import CryptContext

# Configure bcrypt context for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a plain-text password using bcrypt.

    Args:
        password: Plain-text password to hash

    Returns:
        Bcrypt-hashed password string

    Example:
        >>> hashed = hash_password("mypassword")
        >>> hashed.startswith("$2b$")
        True
    """
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plain-text password against a bcrypt hash.

    Args:
        plain: Plain-text password to verify
        hashed: Bcrypt-hashed password to verify against

    Returns:
        True if password matches, False otherwise

    Example:
        >>> hashed = hash_password("mypassword")
        >>> verify_password("mypassword", hashed)
        True
        >>> verify_password("wrongpassword", hashed)
        False
    """
    return pwd_context.verify(plain, hashed)


def create_jwt(
    data: Dict,
    token_type: str = "access",
    expires_delta: Optional[timedelta] = None,
) -> Tuple[str, str]:
    """
    Create a JWT token with unique JTI for revocation tracking.

    Args:
        data: Data to encode in the token (e.g., {"user_id": "uuid", "username": "admin"})
        token_type: Type of token - "access" or "refresh"
        expires_delta: Optional expiration time delta. If not provided:
                      - access tokens expire in 15 minutes
                      - refresh tokens expire in 30 days

    Returns:
        Tuple of (token_string, jti) where jti is unique ID for revocation tracking

    Example:
        >>> token, jti = create_jwt(
        ...     {"user_id": "abc123", "username": "admin"},
        ...     token_type="access",
        ...     expires_delta=timedelta(minutes=15)
        ... )
        >>> isinstance(token, str) and len(token) > 0
        True
        >>> isinstance(jti, str) and len(jti) > 0
        True
    """
    import jwt

    from settings import settings

    if not settings.JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY not configured in settings")

    # Set default expiration based on token type
    if expires_delta is None:
        if token_type == "access":
            expires_delta = timedelta(minutes=15)
        elif token_type == "refresh":
            expires_delta = timedelta(days=30)
        else:
            expires_delta = timedelta(hours=1)

    # Use Cairo timezone for consistency
    cairo_tz = pytz.timezone("Africa/Cairo")
    now = datetime.now(cairo_tz)
    expire = now + expires_delta

    # Generate unique JTI for revocation tracking
    jti = str(uuid.uuid4())

    # Build payload
    to_encode = {
        **data,
        "exp": expire,
        "iat": now,
        "jti": jti,
        "type": token_type,
    }

    # Encode token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return encoded_jwt, jti


def decode_jwt(token: str) -> Dict:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string to decode

    Returns:
        Decoded payload dict

    Raises:
        jwt.ExpiredSignatureError: If token has expired
        jwt.InvalidTokenError: If token signature is invalid
        ValueError: If JWT_SECRET_KEY is not configured

    Example:
        >>> token, _ = create_jwt({"user_id": "abc123"})
        >>> payload = decode_jwt(token)
        >>> payload["user_id"]
        'abc123'
    """
    import jwt

    from settings import settings

    if not settings.JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY not configured in settings")

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise
    except jwt.InvalidTokenError:
        raise


def get_password_hash(password: str) -> str:
    """
    Alias for hash_password for backward compatibility.

    Args:
        password: Plain-text password to hash

    Returns:
        Bcrypt-hashed password string
    """
    return hash_password(password)
