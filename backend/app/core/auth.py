"""
FastAPI authentication dependencies.
Extracts Bearer token and verifies via Supabase auth.
"""
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Request

from app.core.logging import get_logger
from app.core.supabase import get_supabase_client

logger = get_logger("core.auth")


@dataclass
class AuthenticatedUser:
    id: str
    email: str


def _extract_token(request: Request) -> Optional[str]:
    """Extract Bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    return auth_header[7:]


async def optional_user(request: Request) -> Optional[AuthenticatedUser]:
    """
    Returns AuthenticatedUser if valid token present, None otherwise.
    Use for endpoints that work with or without auth (e.g., search).
    """
    token = _extract_token(request)
    if not token:
        logger.debug("No Bearer token in request")
        return None

    logger.info("Token received", token_prefix=token[:20] + "...")
    try:
        client = get_supabase_client()
        logger.debug("Supabase client obtained, verifying token...")
        user_response = client.auth.get_user(token)
        user = user_response.user
        if not user:
            logger.warning("Token valid but no user returned")
            return None
        logger.info("User authenticated", user_id=user.id, email=user.email)
        return AuthenticatedUser(id=user.id, email=user.email)
    except RuntimeError as e:
        logger.error("Supabase client not configured", error=str(e))
        return None
    except Exception as e:
        logger.warning("Token verification failed", error=str(e), error_type=type(e).__name__)
        return None


async def required_user(request: Request) -> AuthenticatedUser:
    """
    Returns AuthenticatedUser or raises 401.
    Use for endpoints that require authentication.
    """
    user = await optional_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
