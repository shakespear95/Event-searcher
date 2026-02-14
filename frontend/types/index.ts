// Search Request - matches backend SearchRequest schema
export interface SearchRequest {
  query: string;
  category?: string;
  results_count?: number;
  location: string;
  radius_km?: number;
  date_from?: string;
  date_to?: string;
  time_of_day?: string;
  price_range?: string;
  indoor_outdoor?: string;
  verified_only?: boolean;
  hidden_gems?: boolean;
  weather_safe?: boolean;
  sort_by?: string;
}

// Event Location
export interface EventLocation {
  venue_name?: string;
  address?: string;
  city: string;
  country: string;
  coordinates?: [number, number];
  distance_km?: number;
}

// Event Timing
export interface EventTiming {
  start_datetime: string;
  end_datetime?: string;
  timezone: string;
}

// Event Pricing
export interface EventPricing {
  price?: number;
  is_free: boolean;
  price_range: string;
  booking_url?: string;
}

// Event Weather
export interface EventWeather {
  weather_score: number;
  weather_status: string;
  conditions?: string;
}

// Event Source
export interface EventSource {
  source_url: string;
  source_api: string;
  verified: boolean;
}

// Event Result - matches backend EventResult schema
export interface EventResult {
  event_id: string;
  event_name: string;
  description?: string;
  category: string;
  location: EventLocation;
  timing: EventTiming;
  pricing: EventPricing;
  indoor_outdoor: string;
  weather?: EventWeather;
  source: EventSource;
  image_url?: string;
  is_hidden_gem: boolean;
  relevance_score: number;
}

// Search Response Metadata
export interface SearchMetadata {
  query_id: string;
  execution_time_ms: number;
  total_results: number;
  sources_used: string[];
}

// Search Response - matches backend response format
export interface SearchResponse {
  events: EventResult[];
  metadata: SearchMetadata;
}

// Category Information
export interface Category {
  id: string;
  name: string;
  description?: string;
  icon?: string;
}

// Filter Options
export interface FilterOptions {
  categories: Category[];
  price_ranges: string[];
  time_of_day_options: string[];
  sort_options: string[];
}

// Frontend-specific search filters (for UI state)
export interface SearchFilters {
  location: string;
  useCurrentLocation: boolean;
  radius: number;
  categories: string[];
  subcategories: string[];
  timeRange: string;
  dateFrom?: Date;
  dateTo?: Date;
  budget: {
    min: number;
    max: number;
    onlyFree: boolean;
  };
  keywords: string;
  quickFilters: string[];
  specialTags: string[];
  searchMode: 'standard' | 'discover';
  eventFrequency: string[];
  advancedFilters: {
    accessibility: string[];
    ageGroups: string[];
    features: string[];
    catering: string[];
  };
  showFavoritesOnly?: boolean;
}

// Event display props (mapped from EventResult for UI components)
export interface EventDisplayProps {
  id: string;
  title: string;
  location: string;
  exactAddress?: string;
  date: string;
  time?: string;
  image: string;
  category: string;
  description?: string;
  price?: string;
  specialFeature?: string;
  source?: string;
  latitude?: number;
  longitude?: number;
  tickets?: {
    type: 'free' | 'link' | 'website' | 'phone';
    value?: string;
    label?: string;
  };
  isFavorite?: boolean;
  onToggleFavorite?: () => void;
}

// Translation keys
export interface TranslationStrings {
  search: {
    title: string;
    location: string;
    locationPlaceholder: string;
    radius: string;
    categories: string;
    allCategories: string;
    timePeriod: string;
    budget: string;
    filters: string;
    searchButton: string;
    showResults: string;
    discover: string;
    standard: string;
  };
  event: {
    details: string;
    date: string;
    time: string;
    price: string;
    free: string;
    tickets: string;
    location: string;
    category: string;
    save: string;
    saved: string;
    share: string;
    directions: string;
    calendar: string;
    oclock: string;
  };
  common: {
    loading: string;
    error: string;
    noResults: string;
    retry: string;
    cancel: string;
    apply: string;
    reset: string;
    all: string;
    today: string;
    tomorrow: string;
    thisWeek: string;
    thisWeekend: string;
    nextWeek: string;
    nextMonth: string;
    custom: string;
  };
  settings: {
    title: string;
    language: string;
    darkMode: string;
    notifications: string;
    appSettings: string;
    eventReminders: string;
    eventRemindersDesc: string;
    newEventsInArea: string;
    newEventsInAreaDesc: string;
    searchDefaults: string;
    defaultLocation: string;
    defaultLocationPlaceholder: string;
    defaultRadius: string;
    defaultSearchMode: string;
    about: string;
  };
}

// Supported languages
export type Language = 'en' | 'de' | 'fr' | 'es';

// User Profile
export interface UserProfile {
  id: string;
  email: string;
  display_name?: string;
  avatar_url?: string;
  preferred_language: string;
  default_location: string;
  default_radius_km: number;
  default_search_mode: string;
  notify_event_reminders: boolean;
  notify_new_events: boolean;
  created_at?: string;
}

// Search History Item
export interface SearchHistoryItem {
  id: string;
  query: string;
  location?: string;
  category?: string;
  radius_km?: number;
  results_count: number;
  filters: Record<string, unknown>;
  created_at: string;
}

// Favorite Item
export interface FavoriteItem {
  id: string;
  event_id: string;
  event_data: Record<string, unknown>;
  notes: string;
  created_at: string;
}
