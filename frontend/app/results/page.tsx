"use client"

import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Header } from '@/components/Header'
import { EventCard } from '@/components/EventCard'
import { MapView } from '@/components/MapView'
import { searchEvents } from '@/lib/api'
import { computeDateRange, mapPriceRangeToBackend, mapCategoryToBackend, getCategoryImage } from '@/lib/utils'
import { useLanguage } from '@/contexts/LanguageContext'
import { EventResult, EventDisplayProps, SearchRequest } from '@/types'
import { Loader2, SearchX, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'

function ResultsContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { t } = useLanguage()

  const [events, setEvents] = useState<EventDisplayProps[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'list' | 'map'>('list')
  const [favorites, setFavorites] = useState<Set<string>>(new Set())

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
      price: event.pricing.is_free
        ? t('event.free')
        : event.pricing.price
          ? `$${event.pricing.price}`
          : event.pricing.price_range,
      specialFeature: event.is_hidden_gem ? 'Hidden Gem' : undefined,
      source: event.source.source_api,
      latitude: event.location.coordinates?.[0],
      longitude: event.location.coordinates?.[1],
      tickets: event.pricing.is_free
        ? { type: 'free' }
        : event.pricing.booking_url
          ? { type: 'link', value: event.pricing.booking_url, label: 'Book Now' }
          : undefined,
      isFavorite: favorites.has(event.event_id),
      onToggleFavorite: () => toggleFavorite(event.event_id),
    }
  }

  const toggleFavorite = (eventId: string) => {
    setFavorites((prev) => {
      const newFavorites = new Set(prev)
      if (newFavorites.has(eventId)) {
        newFavorites.delete(eventId)
      } else {
        newFavorites.add(eventId)
      }
      return newFavorites
    })
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
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="w-10 h-10 animate-spin text-primary mb-4" />
            <p className="text-muted-foreground">{t('common.loading')}</p>
          </div>
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
