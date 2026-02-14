"""Pydantic schemas for user-related endpoints."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class ProfileResponse(BaseModel):
    id: str
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    preferred_language: str = "en"
    default_location: str = ""
    default_radius_km: int = 25
    default_search_mode: str = "standard"
    notify_event_reminders: bool = True
    notify_new_events: bool = True
    created_at: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    preferred_language: Optional[str] = None
    default_location: Optional[str] = None
    default_radius_km: Optional[int] = None
    default_search_mode: Optional[str] = None
    notify_event_reminders: Optional[bool] = None
    notify_new_events: Optional[bool] = None


class SearchHistoryItem(BaseModel):
    id: str
    query: str
    location: Optional[str] = None
    category: Optional[str] = None
    radius_km: Optional[int] = None
    results_count: int = 0
    filters: dict[str, Any] = {}
    created_at: str


class SearchHistoryResponse(BaseModel):
    items: list[SearchHistoryItem]
    total: int


class FavoriteCreateRequest(BaseModel):
    event_id: str
    event_data: dict[str, Any] = {}
    notes: str = ""


class FavoriteItem(BaseModel):
    id: str
    event_id: str
    event_data: dict[str, Any] = {}
    notes: str = ""
    created_at: str


class FavoritesResponse(BaseModel):
    items: list[FavoriteItem]
    total: int
