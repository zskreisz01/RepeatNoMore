"""Security utilities for RepeatNoMore."""

import hashlib
import secrets
from typing import Optional
from datetime import datetime, timedelta

from app.config import get_settings


def generate_session_token() -> str:
    """
    Generate a secure random session token.

    Returns:
        str: Hex-encoded token
    """
    return secrets.token_hex(32)


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """
    Hash a password with salt.

    Args:
        password: Plain text password
        salt: Optional salt (generated if not provided)

    Returns:
        tuple: (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)

    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )

    return hashed.hex(), salt


def verify_password(password: str, hashed_password: str, salt: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        password: Plain text password
        hashed_password: Hashed password
        salt: Salt used for hashing

    Returns:
        bool: True if password matches
    """
    new_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(new_hash, hashed_password)


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """
    Sanitize user input.

    Args:
        text: Input text
        max_length: Maximum allowed length

    Returns:
        str: Sanitized text
    """
    # Truncate to max length
    text = text[:max_length]

    # Remove null bytes
    text = text.replace('\x00', '')

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def is_token_expired(created_at: datetime, timeout_minutes: Optional[int] = None) -> bool:
    """
    Check if a token has expired.

    Args:
        created_at: Token creation timestamp
        timeout_minutes: Timeout in minutes (uses settings if not provided)

    Returns:
        bool: True if expired
    """
    settings = get_settings()
    timeout = timeout_minutes or settings.session_timeout_minutes

    expiry_time = created_at + timedelta(minutes=timeout)
    return datetime.utcnow() > expiry_time


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive data for logging.

    Args:
        data: Sensitive string (e.g., API key, password)
        visible_chars: Number of characters to show at the end

    Returns:
        str: Masked string
    """
    if len(data) <= visible_chars:
        return "*" * len(data)

    return "*" * (len(data) - visible_chars) + data[-visible_chars:]
