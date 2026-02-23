"use client"

import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Header } from '@/components/Header'
import { EventCard } from '@/components/EventCard'
import { MapView } from '@/components/MapView'
import { searchEvents, getFavorites, addFavorite, removeFavorite } from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'
import { computeDateRange, mapPriceRangeToBackend, mapCategoryToBackend, getCategoryImage } from '@/lib/utils'
import { useLanguage } from '@/contexts/LanguageContext'
import { EventResult, EventDisplayProps, SearchRequest } from '@/types'
import { Loader2, SearchX, RefreshCw, MapPin, Calendar } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'

const searchMessages = [
  'Searching event databases...',
  'Checking local venues...',
  'Scanning ticket platforms...',
  'Finding events near you...',
  'Analyzing results...',
  'Almost there...',
]

function SkeletonCard() {
  return (
    <Card className="overflow-hidden border-0 shadow-sm">
      <div className="hidden md:flex gap-0">
        <div className="w-32 h-36 flex-shrink-0 bg-muted animate-pulse" />
        <div className="flex-1 p-5 space-y-3">
          <div className="flex gap-2">
            <div className="h-6 w-20 bg-muted animate-pulse rounded-full" />
          </div>
          <div className="h-5 w-3/4 bg-muted animate-pulse rounded" />
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-muted" />
            <div className="h-4 w-1/2 bg-muted animate-pulse rounded" />
          </div>
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-muted" />
            <div className="h-4 w-1/3 bg-muted animate-pulse rounded" />
          </div>
          <div className="h-4 w-full bg-muted animate-pulse rounded" />
        </div>
      </div>
      <div className="md:hidden flex gap-3 p-3">
        <div className="w-20 h-24 flex-shrink-0 bg-muted animate-pulse rounded-lg" />
        <div className="flex-1 space-y-2">
          <div className="h-4 w-16 bg-muted animate-pulse rounded-full" />
          <div className="h-4 w-3/4 bg-muted animate-pulse rounded" />
          <div className="h-3 w-1/2 bg-muted animate-pulse rounded" />
          <div className="h-3 w-1/3 bg-muted animate-pulse rounded" />
        </div>
      </div>
    </Card>
  )
}

function SearchLoadingAnimation({ location }: { location: string }) {
  const [messageIndex, setMessageIndex] = useState(0)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    const msgInterval = setInterval(() => {
      setMessageIndex(prev => (prev + 1) % searchMessages.length)
    }, 2500)
    return () => clearInterval(msgInterval)
  }, [])

  useEffect(() => {
    const progressInterval = setInterval(() => {
      setProgress(prev => Math.min(prev + Math.random() * 8, 90))
    }, 500)
    return () => clearInterval(progressInterval)
  }, [])

  return (
    <div className="space-y-6">
      {/* Animated header */}
      <div className="flex flex-col items-center py-8">
        <div className="relative mb-4">
          <div className="w-16 h-16 rounded-full border-4 border-primary/20 flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
          <div
            className="absolute inset-0 rounded-full border-4 border-transparent border-t-primary animate-spin"
            style={{ animationDuration: '1.5s' }}
          />
        </div>
        <p className="text-lg font-medium mb-1">Searching in {location}</p>
        <p className="text-sm text-muted-foreground animate-pulse transition-all duration-500">
          {searchMessages[messageIndex]}
        </p>
        {/* Progress bar */}
        <div className="w-64 h-1.5 bg-muted rounded-full mt-4 overflow-hidden">
          <div
            className="h-full bg-primary rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Skeleton cards */}
      <div className="grid gap-4 md:gap-6">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className="animate-pulse"
            style={{ animationDelay: `${i * 150}ms`, opacity: 1 - i * 0.15 }}
          >
            <SkeletonCard />
          </div>
        ))}
      </div>
    </div>
  )
}

function ResultsContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { t } = useLanguage()

  const [events, setEvents] = useState<EventDisplayProps[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'list' | 'map'>('list')
  const [favorites, setFavorites] = useState<Set<string>>(new Set())
  const [rawEvents, setRawEvents] = useState<EventResult[]>([])
  const { user } = useAuth()

  // Load favorites from DB on mount
  useEffect(() => {
    if (!user) return
    getFavorites()
      .then(({ items }) => {
        setFavorites(new Set(items.map((f) => f.event_id)))
      })
      .catch((err) => console.error('Failed to load favorites:', err))
  }, [user])

  // Parse search params
  const location = searchParams.get('location') || ''
  const radius = parseInt(searchParams.get('radius') || '25')
  const mode = searchParams.get('mode') || 'standard'
  const timeRange = searchParams.get('timeRange') || 'thisWeek'
  const categories = searchParams.get('categories')?.split(',').filter(Boolean) || []
  const priceRange = searchParams.get('priceRange') || ''
  const query = searchParams.get('query') || ''

  // Convert EventResult to EventDisplayProps
  const mapEventToDisplay = (event: EventResult): EventDisplayProps => {
    const startDate = new Date(event.timing.start_datetime)
    const timeStr = startDate.toTimeString().slice(0, 5)

    // Build display price string
    const currency = event.pricing.price_currency || 'USD'
    const currencySymbol = currency === 'EUR' ? '\u20AC' : currency === 'CHF' ? 'CHF ' : currency === 'GBP' ? '\u00A3' : '$'
    let priceDisplay: string | undefined
    let priceRangeDisplay: string | undefined
    if (event.pricing.is_free) {
      priceDisplay = t('event.free')
    } else if (event.pricing.price_info) {
      priceDisplay = event.pricing.price_info
    } else if (event.pricing.price_min != null) {
      priceDisplay = `${currencySymbol}${event.pricing.price_min}`
      if (event.pricing.price_max && event.pricing.price_max !== event.pricing.price_min) {
        priceDisplay += ` - ${currencySymbol}${event.pricing.price_max}`
        priceRangeDisplay = priceDisplay
      }
    } else if (event.pricing.price) {
      priceDisplay = `${currencySymbol}${event.pricing.price}`
    }

    // Booking URL: prefer pricing.booking_url, fall back to source URL for ticketmaster
    const bookingUrl = event.pricing.booking_url
      || (event.source.source_api === 'ticketmaster' ? event.source.source_url : undefined)

    return {
      id: event.event_id,
      title: event.event_name,
      location: event.location.venue_name
        ? `${event.location.venue_name}, ${event.location.city}`
        : event.location.city,
      exactAddress: event.location.address,
      date: startDate.toISOString().split('T')[0],
      time: timeStr,
      image: event.image_url || getCategoryImage(event.category, event.event_name),
      category: event.category,
      description: event.description,
      price: priceDisplay,
      specialFeature: event.is_hidden_gem ? 'Hidden Gem' : undefined,
      source: event.source.source_api,
      latitude: event.location.coordinates?.[0],
      longitude: event.location.coordinates?.[1],
      tickets: event.pricing.is_free
        ? { type: 'free' }
        : bookingUrl
          ? { type: 'link', value: bookingUrl, label: 'Get Tickets' }
          : undefined,
      isFavorite: favorites.has(event.event_id),
      onToggleFavorite: () => toggleFavorite(event.event_id),
      // Rich metadata
      performers: event.performers,
      genre: event.genre,
      priceRange: priceRangeDisplay,
      bookingUrl: bookingUrl,
      availabilityStatus: event.availability_status,
      images: event.images,
    }
  }

  const toggleFavorite = async (eventId: string) => {
    const isFav = favorites.has(eventId)

    // Optimistic update
    setFavorites((prev) => {
      const next = new Set(prev)
      if (isFav) next.delete(eventId)
      else next.add(eventId)
      return next
    })

    if (user) {
      try {
        if (isFav) {
          await removeFavorite(eventId)
        } else {
          const eventData = rawEvents.find((e) => e.event_id === eventId)
          await addFavorite(eventId, eventData ? (eventData as unknown as Record<string, unknown>) : {})
        }
      } catch (err) {
        console.error('Failed to update favorite:', err)
        // Revert on failure
        setFavorites((prev) => {
          const next = new Set(prev)
          if (isFav) next.add(eventId)
          else next.delete(eventId)
          return next
        })
      }
    }
  }

  const fetchEvents = async () => {
    if (!location) {
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const dateRange = computeDateRange(timeRange)

      const searchRequest: SearchRequest = {
        query: query || `events in ${location}`,
        location: location,
        radius_km: radius,
        hidden_gems: mode === 'discover',
        ...(categories.length > 0 && { category: mapCategoryToBackend(categories[0]) }),
        ...(dateRange.dateFrom && { date_from: dateRange.dateFrom }),
        ...(dateRange.dateTo && { date_to: dateRange.dateTo }),
        ...(priceRange && { price_range: priceRange }),
      }

      const response = await searchEvents(searchRequest)
      setRawEvents(response.events)
      const mappedEvents = response.events.map(mapEventToDisplay)
      setEvents(mappedEvents)
    } catch (err) {
      console.error('Search error:', err)
      setError(err instanceof Error ? err.message : 'Failed to search events')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchEvents()
  }, [location, radius, mode, timeRange, categories.join(','), priceRange, query])

  const handleSettingsClick = () => {
    router.push('/settings')
  }

  const handleBackToSearch = () => {
    router.push('/')
  }

  // Update events with favorite status
  const eventsWithFavorites = events.map((event) => ({
    ...event,
    isFavorite: favorites.has(event.id),
    onToggleFavorite: () => toggleFavorite(event.id),
  }))

  return (
    <main className="min-h-screen bg-background">
      <Header
        onSettingsClick={handleSettingsClick}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        showViewToggle={events.length > 0}
      />

      <div className="container mx-auto px-4 py-6">
        {/* Search Summary */}
        {location && (
          <div className="mb-4 flex items-center justify-between">
            <div className="text-sm text-muted-foreground">
              {loading
                ? t('common.loading')
                : `${events.length} events found near ${location}`}
            </div>
            <Button variant="outline" size="sm" onClick={handleBackToSearch}>
              New Search
            </Button>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <SearchLoadingAnimation location={location} />
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="flex flex-col items-center justify-center py-20">
            <SearchX className="w-16 h-16 text-muted-foreground mb-4" />
            <p className="text-lg font-medium mb-2">{t('common.error')}</p>
            <p className="text-muted-foreground mb-4">{error}</p>
            <Button onClick={fetchEvents}>
              <RefreshCw className="w-4 h-4 mr-2" />
              {t('common.retry')}
            </Button>
          </div>
        )}

        {/* No Results State */}
        {!loading && !error && events.length === 0 && location && (
          <div className="flex flex-col items-center justify-center py-20">
            <SearchX className="w-16 h-16 text-muted-foreground mb-4" />
            <p className="text-lg font-medium mb-2">{t('common.noResults')}</p>
            <p className="text-muted-foreground mb-4">Try adjusting your search filters</p>
            <Button onClick={handleBackToSearch}>New Search</Button>
          </div>
        )}

        {/* No Location State */}
        {!loading && !location && (
          <div className="flex flex-col items-center justify-center py-20">
            <p className="text-lg font-medium mb-4">Start searching for events</p>
            <Button onClick={handleBackToSearch}>Go to Search</Button>
          </div>
        )}

        {/* Results */}
        {!loading && !error && events.length > 0 && (
          <>
            {viewMode === 'list' ? (
              <div className="grid gap-4 md:gap-6">
                {eventsWithFavorites.map((event) => (
                  <EventCard key={event.id} {...event} />
                ))}
              </div>
            ) : (
              <MapView events={eventsWithFavorites} />
            )}
          </>
        )}
      </div>
    </main>
  )
}

export default function ResultsPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-background flex items-center justify-center">
          <Loader2 className="w-10 h-10 animate-spin text-primary" />
        </div>
      }
    >
      <ResultsContent />
    </Suspense>
  )
}
