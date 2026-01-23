"use client"

import { useState, useEffect, useRef } from 'react'
import { MapPin, Calendar, Clock, X } from 'lucide-react'
import { Card } from './ui/card'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import { EventDetailModal } from './EventDetailModal'
import { useLanguage } from '@/contexts/LanguageContext'
import { EventDisplayProps } from '@/types'
import { formatDate, formatTime } from '@/lib/utils'

interface MapViewProps {
  events: EventDisplayProps[]
}

export function MapView({ events }: MapViewProps) {
  const { t, language } = useLanguage()
  const mapRef = useRef<HTMLDivElement>(null)
  const [map, setMap] = useState<any>(null)
  const [selectedEvent, setSelectedEvent] = useState<EventDisplayProps | null>(null)
  const [showDetailModal, setShowDetailModal] = useState(false)
  const markersRef = useRef<any[]>([])

  const locale =
    language === 'de'
      ? 'de-DE'
      : language === 'fr'
        ? 'fr-FR'
        : language === 'es'
          ? 'es-ES'
          : 'en-US'

  // Initialize Leaflet map
  useEffect(() => {
    let mapInstance: any = null

    const initializeMap = async () => {
      if (typeof window === 'undefined') return

      const L = (await import('leaflet')).default

      // Add Leaflet CSS
      if (!document.querySelector('link[href*="leaflet.css"]')) {
        const link = document.createElement('link')
        link.rel = 'stylesheet'
        link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
        document.head.appendChild(link)
      }

      if (mapRef.current && !mapInstance) {
        // Default center (can be adjusted based on events)
        const centerLat = 47.3769
        const centerLng = 8.5417

        mapInstance = L.map(mapRef.current, {
          center: [centerLat, centerLng],
          zoom: 10,
          zoomControl: false,
        })

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '&copy; OpenStreetMap contributors',
          maxZoom: 18,
        }).addTo(mapInstance)

        L.control
          .zoom({
            position: 'bottomright',
          })
          .addTo(mapInstance)

        setMap(mapInstance)

        // Add event markers
        addEventMarkers(L, mapInstance)
      }
    }

    initializeMap()

    return () => {
      if (mapInstance) {
        mapInstance.remove()
      }
    }
  }, [])

  // Update markers when events change
  useEffect(() => {
    if (map && events.length > 0) {
      addEventMarkers(null, map)
    }
  }, [map, events])

  const addEventMarkers = async (L: any, mapInstance: any) => {
    if (!L) {
      L = (await import('leaflet')).default
    }

    // Remove old markers
    markersRef.current.forEach((marker) => {
      mapInstance.removeLayer(marker)
    })
    markersRef.current = []

    // Add new markers for events with coordinates
    events.forEach((event) => {
      if (
        !event.latitude ||
        !event.longitude ||
        isNaN(event.latitude) ||
        isNaN(event.longitude)
      ) {
        console.warn('Event missing coordinates:', event.title, event.location)
        return
      }

      const customIcon = L.divIcon({
        html: `
          <div class="relative">
            <div class="w-8 h-8 bg-red-500 rounded-full border-2 border-white shadow-lg flex items-center justify-center hover:bg-red-600 transition-colors cursor-pointer">
              <svg class="w-4 h-4 text-white fill-current" viewBox="0 0 24 24">
                <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
              </svg>
            </div>
            <div class="absolute -bottom-1 left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-2 border-r-2 border-t-2 border-transparent border-t-red-500"></div>
          </div>
        `,
        iconSize: [32, 40],
        iconAnchor: [16, 40],
        className: 'custom-event-marker',
      })

      const marker = L.marker([event.latitude, event.longitude], {
        icon: customIcon,
      }).addTo(mapInstance)

      marker.on('click', () => {
        setSelectedEvent(event)
        mapInstance.setView(
          [event.latitude!, event.longitude!],
          Math.max(mapInstance.getZoom(), 12),
          {
            animate: true,
            duration: 0.5,
          }
        )
      })

      marker.bindTooltip(
        `<div class="font-medium">${event.title}</div><div class="text-sm text-gray-600">${event.location}</div>`,
        {
          direction: 'top',
          offset: [0, -10],
          className: 'custom-tooltip',
        }
      )

      markersRef.current.push(marker)
    })

    // Fit map to markers
    if (markersRef.current.length > 0) {
      const group = new L.featureGroup(markersRef.current)
      mapInstance.fitBounds(group.getBounds().pad(0.1))
    }
  }

  const handleCardClick = () => {
    if (selectedEvent) {
      setShowDetailModal(true)
    }
  }

  const handleCloseCard = (e: React.MouseEvent) => {
    e.stopPropagation()
    setSelectedEvent(null)
  }

  return (
    <div className="relative w-full h-[600px] sm:h-[700px] lg:h-[800px] bg-slate-100 rounded-lg overflow-hidden">
      {/* Map Container */}
      <div ref={mapRef} className="absolute inset-0 w-full h-full" style={{ zIndex: 1 }} />

      {/* Event Count Badge */}
      <div className="absolute top-4 right-4 z-[1000] flex flex-col gap-2">
        <div className="bg-white rounded-lg p-2 shadow-sm">
          <div className="flex items-center gap-2 text-sm">
            <MapPin className="w-4 h-4 text-red-500 fill-red-500" />
            <span className="font-medium">{events.length} Events</span>
          </div>
        </div>
      </div>

      {/* Selected Event Card */}
      {selectedEvent && (
        <div
          className="absolute bottom-0 left-0 right-0 z-[1000] transform transition-transform duration-300 ease-out"
          style={{ transform: 'translateY(0)' }}
        >
          <Card
            className="m-4 shadow-xl border-0 cursor-pointer hover:shadow-2xl transition-shadow bg-white/95 backdrop-blur-sm"
            onClick={handleCardClick}
          >
            <div className="p-4">
              <Button
                variant="ghost"
                size="sm"
                className="absolute top-2 right-2 h-8 w-8 p-0 hover:bg-gray-100"
                onClick={handleCloseCard}
              >
                <X className="w-4 h-4" />
              </Button>

              <div className="flex gap-4">
                <div className="flex-shrink-0">
                  <img
                    src={selectedEvent.image || '/placeholder-event.jpg'}
                    alt={selectedEvent.title}
                    className="w-20 h-20 sm:w-24 sm:h-24 rounded-lg object-cover"
                  />
                </div>

                <div className="flex-1 min-w-0 pr-8">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <h3 className="font-semibold text-lg line-clamp-2 leading-tight">
                      {selectedEvent.title}
                    </h3>
                  </div>

                  <div className="space-y-1 text-sm text-muted-foreground">
                    <div className="flex items-center gap-2">
                      <Calendar className="w-4 h-4 flex-shrink-0" />
                      <span>
                        {formatDate(selectedEvent.date, locale).fullDate}
                        {selectedEvent.time && ` - ${formatTime(selectedEvent.time)} ${t('event.oclock')}`}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <MapPin className="w-4 h-4 flex-shrink-0" />
                      <span className="line-clamp-1">{selectedEvent.location}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 mt-2">
                    {selectedEvent.price && (
                      <Badge variant="secondary" className="text-green-600 bg-green-50">
                        {selectedEvent.price}
                      </Badge>
                    )}
                    <Badge variant="outline">{selectedEvent.category}</Badge>
                  </div>
                </div>
              </div>

              <div className="text-center mt-3 pt-3 border-t border-gray-100">
                <p className="text-xs text-muted-foreground">Click for details</p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Event Detail Modal */}
      {showDetailModal && selectedEvent && (
        <EventDetailModal
          event={{
            id: selectedEvent.id,
            title: selectedEvent.title,
            location: selectedEvent.location,
            exactAddress: selectedEvent.exactAddress,
            date: selectedEvent.date,
            time: selectedEvent.time,
            image: selectedEvent.image,
            category: selectedEvent.category,
            description: selectedEvent.description,
            price: selectedEvent.price,
            specialFeature: selectedEvent.specialFeature,
            source: selectedEvent.source,
            tickets: selectedEvent.tickets,
          }}
          isOpen={showDetailModal}
          onClose={() => setShowDetailModal(false)}
          isFavorite={selectedEvent.isFavorite || false}
          onToggleFavorite={selectedEvent.onToggleFavorite}
        />
      )}
    </div>
  )
}
