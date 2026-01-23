import { SearchRequest, SearchResponse, Category, FilterOptions } from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Debug: Log the API URL being used (remove after debugging)
if (typeof window !== 'undefined') {
  console.log('[API] Using backend URL:', API_BASE);
}

/**
 * Search for events using the FastAPI backend
 */
export async function searchEvents(params: SearchRequest): Promise<SearchResponse> {
  const response = await fetch(`${API_BASE}/api/v1/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
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
