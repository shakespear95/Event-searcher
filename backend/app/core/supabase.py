"""
Supabase client singleton.
Uses service role key for server-side operations (bypasses RLS).
"""
from supabase import create_client, Client

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("core.supabase")

_client: Client | None = None


def get_supabase_client() -> Client:
    """Get or create the Supabase client (service role)."""
    global _client
    if _client is None:
        if not settings.supabase_url or not settings.supabase_service_key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set for user features"
            )
        _client = create_client(settings.supabase_url, settings.supabase_service_key)
        logger.info("Supabase client initialized")
    return _client
