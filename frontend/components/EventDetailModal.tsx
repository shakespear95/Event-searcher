"use client"

import {
  Calendar,
  MapPin,
  Clock,
  Palette,
  Music,
  Users,
  UtensilsCrossed,
  TreePine,
  Trophy,
  Theater,
  PartyPopper,
  Building2,
  ShoppingBag,
  ExternalLink,
  Phone,
  Globe,
  Heart,
  X,
  Share2,
  Navigation,
} from 'lucide-react'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from './ui/dialog'
import { Separator } from './ui/separator'
import { useLanguage } from '@/contexts/LanguageContext'
import { formatDate, formatTime, getCategoryImage } from '@/lib/utils'

interface EventDetailModalProps {
  event: {
    id: string
    title: string
    location: string
    exactAddress?: string
    date: string
    time?: string
    image: string
    category: string
    description?: string
    price?: string
    specialFeature?: string
    source?: string
    tickets?: {
      type: 'free' | 'link' | 'website' | 'phone'
      value?: string
      label?: string
    }
    performers?: string[]
    genre?: string
    availabilityStatus?: string
  }
  isOpen: boolean
  onClose: () => void
  isFavorite?: boolean
  onToggleFavorite?: () => void
}

const getCategoryIcon = (category: string) => {
  const categoryLower = category.toLowerCase()

  if (categoryLower.includes('art') || categoryLower.includes('exhibition')) return Palette
  if (categoryLower.includes('concert') || categoryLower.includes('music')) return Music
  if (categoryLower.includes('workshop')) return Users
  if (categoryLower.includes('festival') || categoryLower.includes('food')) return UtensilsCrossed
  if (categoryLower.includes('outdoor')) return TreePine
  if (categoryLower.includes('sport')) return Trophy
  if (categoryLower.includes('theater') || categoryLower.includes('theatre')) return Theater
  if (categoryLower.includes('party') || categoryLower.includes('club')) return PartyPopper
  if (categoryLower.includes('market')) return ShoppingBag

  return Building2
}

export function EventDetailModal({
  event,
  isOpen,
  onClose,
  isFavorite = false,
  onToggleFavorite,
}: EventDetailModalProps) {
  const { t, language } = useLanguage()

  const locale =
    language === 'de'
      ? 'de-DE'
      : language === 'fr'
        ? 'fr-FR'
        : language === 'es'
          ? 'es-ES'
          : 'en-US'

  const { day, month, fullDate } = formatDate(event.date, locale)
  const CategoryIcon = getCategoryIcon(event.category)
  const eventImage = event.image || getCategoryImage(event.category, event.title)

  const handleTicketAction = () => {
    if (!event.tickets) return

    switch (event.tickets.type) {
      case 'link':
      case 'website':
        if (event.tickets.value) {
          window.open(event.tickets.value, '_blank')
        }
        break
      case 'phone':
        if (event.tickets.value) {
          window.location.href = `tel:${event.tickets.value}`
        }
        break
    }
  }

  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: event.title,
          text: `${event.title} - ${fullDate} in ${event.location}`,
          url: window.location.href,
        })
      } catch (err) {
        console.log('Error sharing:', err)
      }
    } else {
      const shareText = `${event.title} - ${fullDate} in ${event.location}`
      navigator.clipboard.writeText(shareText)
    }
  }

  const handleDirections = () => {
    const address = event.exactAddress || event.location
    const mapsUrl = `https://maps.google.com/maps?q=${encodeURIComponent(address)}`
    window.open(mapsUrl, '_blank')
  }

  const handleAddToCalendar = () => {
    const eventDate = new Date(event.date)

    let startDateTime: Date
    if (event.time) {
      const [hours, minutes] = event.time.split(':')
      startDateTime = new Date(eventDate)
      startDateTime.setHours(parseInt(hours), parseInt(minutes), 0, 0)
    } else {
      startDateTime = new Date(eventDate)
      startDateTime.setHours(18, 0, 0, 0)
    }

    const endDateTime = new Date(startDateTime)
    endDateTime.setHours(endDateTime.getHours() + 2)

    const formatICSDate = (date: Date) => {
      return date.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z'
    }

    const startDateFormatted = formatICSDate(startDateTime)
    const endDateFormatted = formatICSDate(endDateTime)

    const icsContent = [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//WhatsUP//Event Calendar//EN',
      'BEGIN:VEVENT',
      `DTSTART:${startDateFormatted}`,
      `DTEND:${endDateFormatted}`,
      `SUMMARY:${event.title}`,
      `DESCRIPTION:${event.description || ''}${event.price ? `\\n\\nPrice: ${event.price}` : ''}${event.specialFeature ? `\\n\\nSpecial: ${event.specialFeature}` : ''}`,
      `LOCATION:${event.exactAddress || event.location}`,
      `UID:${event.id}@whatsup.app`,
      'END:VEVENT',
      'END:VCALENDAR',
    ].join('\r\n')

    const blob = new Blob([icsContent], { type: 'text/calendar;charset=utf-8' })
    const link = document.createElement('a')
    link.href = window.URL.createObjectURL(blob)
    link.download = `whatsup-${event.title.replace(/[^a-z0-9]/gi, '-').toLowerCase()}.ics`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(link.href)
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl w-full h-[90vh] sm:h-[85vh] p-0 overflow-hidden flex flex-col">
        <DialogHeader className="sr-only">
          <DialogTitle>{event.title}</DialogTitle>
          <DialogDescription>
            {event.category} - {fullDate} in {event.location}
          </DialogDescription>
        </DialogHeader>

        {/* Hero Image */}
        <div className="relative h-48 sm:h-64 md:h-80 flex-shrink-0">
          <img
            src={eventImage}
            alt={event.title}
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />

          <Button
            variant="outline"
            size="icon"
            className="absolute top-4 right-4 bg-white/90 hover:bg-white border-0 shadow-lg z-10"
            onClick={onClose}
          >
            <X className="w-5 h-5 text-gray-700" />
            <span className="sr-only">Close modal</span>
          </Button>

          <div className="absolute top-4 left-4 bg-white rounded-lg p-3 text-center shadow-lg">
            <div className="text-2xl font-bold text-primary">{day}</div>
            <div className="text-sm text-muted-foreground uppercase">{month.slice(0, 3)}</div>
          </div>

          <div className="absolute top-4 left-20 bg-white/90 rounded-lg p-2 shadow-lg">
            <div className="flex items-center gap-2">
              <CategoryIcon className="w-5 h-5 text-primary" />
              <span className="text-sm font-medium">{event.category}</span>
            </div>
          </div>

          <div className="absolute bottom-4 sm:bottom-6 left-4 sm:left-6 right-4 sm:right-6">
            <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-white mb-1 leading-tight">
              {event.title}
            </h1>
            {event.performers && event.performers.length > 0 && (
              <p className="text-sm text-white/80 mb-2">
                {event.performers.join(', ')}
              </p>
            )}
            <div className="flex items-center gap-3 sm:gap-4 text-white/90 flex-wrap">
              <div className="flex items-center gap-1">
                <MapPin className="w-4 h-4" />
                <span className="text-sm">{event.location}</span>
              </div>
              {event.time && (
                <div className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  <span className="text-sm">
                    {formatTime(event.time)} {t('event.oclock')}
                  </span>
                </div>
              )}
              {event.genre && (
                <Badge variant="secondary" className="text-xs bg-white/20 text-white border-0">
                  {event.genre}
                </Badge>
              )}
              {event.availabilityStatus && (
                <Badge
                  variant="secondary"
                  className={`text-xs border-0 ${
                    event.availabilityStatus === 'onsale'
                      ? 'bg-green-500/80 text-white'
                      : event.availabilityStatus === 'offsale'
                        ? 'bg-red-500/80 text-white'
                        : 'bg-white/20 text-white'
                  }`}
                >
                  {event.availabilityStatus === 'onsale' ? 'On Sale' : event.availabilityStatus === 'offsale' ? 'Off Sale' : event.availabilityStatus === 'cancelled' ? 'Cancelled' : event.availabilityStatus}
                </Badge>
              )}
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent">
          <div className="p-4 sm:p-6">
            <div className="max-w-4xl mx-auto space-y-4 sm:space-y-6">
              {/* Action Buttons */}
              <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
                {onToggleFavorite && (
                  <Button
                    variant={isFavorite ? 'default' : 'outline'}
                    size="sm"
                    onClick={onToggleFavorite}
                    className={isFavorite ? 'bg-red-500 hover:bg-red-600' : ''}
                  >
                    <Heart className={`w-4 h-4 mr-2 ${isFavorite ? 'fill-current' : ''}`} />
                    {isFavorite ? t('event.saved') : t('event.save')}
                  </Button>
                )}

                <Button variant="outline" size="sm" onClick={handleAddToCalendar}>
                  <Calendar className="w-4 h-4 mr-2" />
                  {t('event.calendar')}
                </Button>

                <Button variant="outline" size="sm" onClick={handleShare}>
                  <Share2 className="w-4 h-4 mr-2" />
                  {t('event.share')}
                </Button>

                <Button variant="outline" size="sm" onClick={handleDirections}>
                  <Navigation className="w-4 h-4 mr-2" />
                  {t('event.directions')}
                </Button>

                {event.source && <Badge variant="secondary">Source: {event.source}</Badge>}
              </div>

              <Separator />

              {/* Details Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
                <div className="space-y-4">
                  <div>
                    <h3 className="font-semibold mb-2">{t('event.date')} & {t('event.time')}</h3>
                    <div className="space-y-1">
                      <p>{fullDate}</p>
                      {event.time && (
                        <p>
                          {formatTime(event.time)} {t('event.oclock')}
                        </p>
                      )}
                    </div>
                  </div>

                  <div>
                    <h3 className="font-semibold mb-2">{t('event.location')}</h3>
                    <div className="space-y-1">
                      <p>{event.location}</p>
                      {event.exactAddress && (
                        <p className="text-sm text-muted-foreground">{event.exactAddress}</p>
                      )}
                    </div>
                  </div>

                  {event.price && (
                    <div>
                      <h3 className="font-semibold mb-2">{t('event.price')}</h3>
                      <p className="text-lg font-medium text-green-600">{event.price}</p>
                    </div>
                  )}

                  {event.specialFeature && (
                    <div>
                      <h3 className="font-semibold mb-2">Special</h3>
                      <div className="flex items-center gap-2">
                        <span className="text-orange-500">*</span>
                        <span>{event.specialFeature}</span>
                      </div>
                    </div>
                  )}
                </div>

                <div className="space-y-4">
                  {event.description && (
                    <div>
                      <h3 className="font-semibold mb-2">Description</h3>
                      <p className="text-muted-foreground leading-relaxed">{event.description}</p>
                    </div>
                  )}

                  {event.tickets && (
                    <div>
                      <h3 className="font-semibold mb-2">{t('event.tickets')}</h3>
                      <div className="space-y-2">
                        {event.tickets.type === 'free' ? (
                          <Badge variant="outline" className="text-green-600 border-green-600">
                            {t('event.free')}
                          </Badge>
                        ) : (
                          <Button onClick={handleTicketAction} className="w-full sm:w-auto">
                            {event.tickets.type === 'link' && (
                              <ExternalLink className="w-4 h-4 mr-2" />
                            )}
                            {event.tickets.type === 'website' && <Globe className="w-4 h-4 mr-2" />}
                            {event.tickets.type === 'phone' && <Phone className="w-4 h-4 mr-2" />}
                            {event.tickets.label ||
                              (event.tickets.type === 'phone'
                                ? event.tickets.value
                                : t('event.tickets'))}
                          </Button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <Separator />

              <div className="bg-muted/50 rounded-lg p-4 mb-6">
                <h3 className="font-semibold mb-2">Event ID</h3>
                <p className="text-sm text-muted-foreground font-mono">{event.id}</p>
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
