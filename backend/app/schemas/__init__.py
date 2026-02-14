"""Pydantic schemas for the application"""
from .event import EventResult, EventCategory
from .search import SearchRequest, SearchResponse
from .state import GlobalState
from .user import (
    ProfileResponse,
    ProfileUpdateRequest,
    SearchHistoryItem,
    SearchHistoryResponse,
    FavoriteCreateRequest,
    FavoriteItem,
    FavoritesResponse,
)

__all__ = [
    "EventResult",
    "EventCategory",
    "SearchRequest",
    "SearchResponse",
    "GlobalState",
    "ProfileResponse",
    "ProfileUpdateRequest",
    "SearchHistoryItem",
    "SearchHistoryResponse",
    "FavoriteCreateRequest",
    "FavoriteItem",
    "FavoritesResponse",
]
