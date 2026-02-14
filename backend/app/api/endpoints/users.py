"""
User API endpoints.
Profile, search history, and favorites management.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import AuthenticatedUser, required_user
from app.core.logging import get_logger
from app.core.supabase import get_supabase_client
from app.schemas.user import (
    FavoriteCreateRequest,
    FavoriteItem,
    FavoritesResponse,
    ProfileResponse,
    ProfileUpdateRequest,
    SearchHistoryItem,
    SearchHistoryResponse,
)

router = APIRouter()
logger = get_logger("api.users")


@router.get("/me", response_model=ProfileResponse)
async def get_profile(user: AuthenticatedUser = Depends(required_user)):
    """Get the current user's profile."""
    client = get_supabase_client()
    result = client.table("profiles").select("*").eq("id", user.id).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    return ProfileResponse(email=user.email, **result.data)


@router.patch("/me", response_model=ProfileResponse)
async def update_profile(
    body: ProfileUpdateRequest,
    user: AuthenticatedUser = Depends(required_user),
):
    """Update the current user's profile."""
    client = get_supabase_client()
    updates = body.model_dump(exclude_none=True)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    result = (
        client.table("profiles")
        .update(updates)
        .eq("id", user.id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Profile not found")

    return ProfileResponse(email=user.email, **result.data[0])


@router.get("/me/search-history", response_model=SearchHistoryResponse)
async def get_search_history(
    limit: int = 50,
    user: AuthenticatedUser = Depends(required_user),
):
    """Get the user's search history."""
    client = get_supabase_client()
    result = (
        client.table("search_history")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    items = [SearchHistoryItem(**row) for row in (result.data or [])]
    return SearchHistoryResponse(items=items, total=len(items))


@router.delete("/me/search-history")
async def clear_search_history(user: AuthenticatedUser = Depends(required_user)):
    """Clear all search history for the user."""
    client = get_supabase_client()
    client.table("search_history").delete().eq("user_id", user.id).execute()
    return {"message": "Search history cleared"}


@router.get("/me/favorites", response_model=FavoritesResponse)
async def get_favorites(user: AuthenticatedUser = Depends(required_user)):
    """Get the user's favorites."""
    client = get_supabase_client()
    result = (
        client.table("favorites")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .execute()
    )

    items = [FavoriteItem(**row) for row in (result.data or [])]
    return FavoritesResponse(items=items, total=len(items))


@router.post("/me/favorites", response_model=FavoriteItem, status_code=201)
async def add_favorite(
    body: FavoriteCreateRequest,
    user: AuthenticatedUser = Depends(required_user),
):
    """Add an event to favorites."""
    client = get_supabase_client()

    try:
        result = (
            client.table("favorites")
            .insert({
                "user_id": user.id,
                "event_id": body.event_id,
                "event_data": body.event_data,
                "notes": body.notes,
            })
            .execute()
        )
    except Exception as e:
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="Event already in favorites")
        raise

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to add favorite")

    return FavoriteItem(**result.data[0])


@router.delete("/me/favorites/{event_id}")
async def remove_favorite(
    event_id: str,
    user: AuthenticatedUser = Depends(required_user),
):
    """Remove an event from favorites."""
    client = get_supabase_client()
    result = (
        client.table("favorites")
        .delete()
        .eq("user_id", user.id)
        .eq("event_id", event_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Favorite not found")

    return {"message": "Favorite removed"}
