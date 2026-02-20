import { SearchRequest, SearchResponse, Category, FilterOptions, UserProfile, SearchHistoryItem, FavoriteItem } from '@/types';
import { getSupabaseClient } from '@/lib/supabase';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Debug: Log the API URL being used (remove after debugging)
if (typeof window !== 'undefined') {
  console.log('[API] Using backend URL:', API_BASE);
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  const client = getSupabaseClient();
  if (client) {
    const { data: { session } } = await client.auth.getSession();
    if (session?.access_token) {
      console.log('[API] Auth header: Bearer token present, user:', session.user?.email);
      return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${session.access_token}`,
      };
    }
    console.log('[API] No active session - sending unauthenticated request');
  } else {
    console.log('[API] No Supabase client - sending unauthenticated request');
  }
  return { 'Content-Type': 'application/json' };
}

/**
 * Search for events using the FastAPI backend
 */
export async function searchEvents(params: SearchRequest): Promise<SearchResponse> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE}/api/v1/search`, {
    method: 'POST',
    headers,
    body: JSON.stringify(params),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Search failed' }));
    throw new Error(error.detail || 'Search failed');
  }

  return response.json();
}

/**
 * Get available categories from the backend
 */
export async function getCategories(): Promise<Category[]> {
  const response = await fetch(`${API_BASE}/api/v1/search/categories`);

  if (!response.ok) {
    throw new Error('Failed to fetch categories');
  }

  return response.json();
}

/**
 * Get filter options from the backend
 */
export async function getFilterOptions(): Promise<FilterOptions> {
  const response = await fetch(`${API_BASE}/api/v1/search/filters`);

  if (!response.ok) {
    throw new Error('Failed to fetch filter options');
  }

  return response.json();
}

/**
 * Health check for the API
 */
export async function checkHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE}/health`);

  if (!response.ok) {
    throw new Error('API health check failed');
  }

  return response.json();
}

/**
 * Reverse geocode coordinates to get location name
 * Uses BigDataCloud free API (CORS-friendly)
 */
export async function reverseGeocode(
  latitude: number,
  longitude: number
): Promise<string> {
  try {
    const response = await fetch(
      `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${latitude}&longitude=${longitude}&localityLanguage=en`
    );

    if (!response.ok) {
      throw new Error('Geocoding failed');
    }

    const data = await response.json();

    const placeName =
      data.city ||
      data.locality ||
      data.principalSubdivision ||
      `${latitude.toFixed(4)}, ${longitude.toFixed(4)}`;

    const country = data.countryName || '';
    return country ? `${placeName}, ${country}` : placeName;
  } catch (error) {
    console.error('Reverse geocoding error:', error);
    return `${latitude.toFixed(4)}, ${longitude.toFixed(4)}`;
  }
}

// --- User API functions ---

export async function getProfile(): Promise<UserProfile> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE}/api/v1/users/me`, { headers });
  if (!response.ok) throw new Error('Failed to fetch profile');
  return response.json();
}

export async function updateProfile(data: Partial<UserProfile>): Promise<UserProfile> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE}/api/v1/users/me`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to update profile');
  return response.json();
}

export async function getSearchHistory(limit = 50): Promise<{ items: SearchHistoryItem[]; total: number }> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE}/api/v1/users/me/search-history?limit=${limit}`, { headers });
  if (!response.ok) throw new Error('Failed to fetch search history');
  return response.json();
}

export async function clearSearchHistory(): Promise<void> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE}/api/v1/users/me/search-history`, {
    method: 'DELETE',
    headers,
  });
  if (!response.ok) throw new Error('Failed to clear search history');
}

export async function getFavorites(): Promise<{ items: FavoriteItem[]; total: number }> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE}/api/v1/users/me/favorites`, { headers });
  if (!response.ok) throw new Error('Failed to fetch favorites');
  return response.json();
}

export async function addFavorite(eventId: string, eventData: Record<string, unknown> = {}): Promise<FavoriteItem> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE}/api/v1/users/me/favorites`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ event_id: eventId, event_data: eventData }),
  });
  if (!response.ok) {
    if (response.status === 409) throw new Error('Already in favorites');
    throw new Error('Failed to add favorite');
  }
  return response.json();
}

export async function removeFavorite(eventId: string): Promise<void> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE}/api/v1/users/me/favorites/${encodeURIComponent(eventId)}`, {
    method: 'DELETE',
    headers,
  });
  if (!response.ok) throw new Error('Failed to remove favorite');
}
