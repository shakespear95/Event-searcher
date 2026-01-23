"use client"

import { useState } from 'react'
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
  Heart,
  ArrowRight,
} from 'lucide-react'
import { Card } from './ui/card'
import { Badge } from './ui/badge'
import { Button } from './ui/button'
import { EventDetailModal } from './EventDetailModal'
import { useLanguage } from '@/contexts/LanguageContext'
import { EventDisplayProps } from '@/types'
import { formatDate } from '@/lib/utils'

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

export function EventCard({
  id,
  title,
  location,
  exactAddress,
  date,
  time,
  image,
  category,
  description,
  price,
  specialFeature,
  source,
  tickets,
  isFavorite = false,
  onToggleFavorite,
}: EventDisplayProps) {
  const { t, language } = useLanguage()
  const [showDetailModal, setShowDetailModal] = useState(false)

  const locale = language === 'de' ? 'de-DE' : language === 'fr' ? 'fr-FR' : language === 'es' ? 'es-ES' : 'en-US'
  const { day, month } = formatDate(date, locale)
  const CategoryIcon = getCategoryIcon(category)

  const eventData = {
    id,
    title,
    location,
    exactAddress,
    date,
    time,
    image,
    category,
    description,
    price,
    specialFeature,
    source,
    tickets,
  }

  return (
    <>
      <Card
        className="overflow-hidden hover:shadow-lg transition-all duration-200 cursor-pointer group border-0 shadow-sm hover:scale-[1.01] bg-card"
        onClick={() => setShowDetailModal(true)}
      >
        {/* Mobile Layout */}
        <div className="md:hidden">
          <div className="flex gap-3 p-3">
            <div className="relative w-20 h-24 flex-shrink-0 overflow-hidden rounded-lg">
              <img
                src={image || '/placeholder-event.jpg'}
                alt={title}
                className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
              />
              <div className="absolute top-1 left-1 bg-white/95 backdrop-blur-sm rounded px-1.5 py-0.5 text-center shadow-sm">
                <div className="text-xs font-bold text-primary leading-none">{day}</div>
                <div className="text-xs text-muted-foreground uppercase leading-none">
                  {month.slice(0, 3)}
                </div>
              </div>
            </div>

            <div className="flex-1 min-w-0 space-y-1.5">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  <CategoryIcon className="w-3 h-3 text-primary flex-shrink-0" />
                  <Badge variant="secondary" className="text-xs px-1.5 py-0.5 h-auto">
                    {category}
                  </Badge>
                </div>
                {onToggleFavorite && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation()
                      onToggleFavorite()
                    }}
                    className="h-6 w-6 p-0 hover:bg-red-50 dark:hover:bg-red-950"
                  >
                    <Heart
                      className={`w-3 h-3 transition-colors ${
                        isFavorite
                          ? 'fill-red-500 text-red-500'
                          : 'text-muted-foreground hover:text-red-500'
                      }`}
                    />
                  </Button>
                )}
              </div>

              <h3 className="font-semibold text-sm leading-tight line-clamp-2 group-hover:text-primary transition-colors">
                {title}
              </h3>

              <div className="space-y-0.5">
                <div className="flex items-center gap-1">
                  <MapPin className="w-3 h-3 text-muted-foreground flex-shrink-0" />
                  <span className="text-xs text-muted-foreground truncate">{location}</span>
                </div>
                {time && (
                  <div className="flex items-center gap-1">
                    <Clock className="w-3 h-3 text-muted-foreground flex-shrink-0" />
                    <span className="text-xs text-muted-foreground">
                      {time} {t('event.oclock')}
                    </span>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between gap-2 flex-wrap">
                {price && <div className="text-sm font-semibold text-green-600">{price}</div>}
              </div>

              {specialFeature && (
                <div className="flex items-center gap-1">
                  <span className="text-orange-500 text-xs">*</span>
                  <span className="text-xs text-orange-600 font-medium truncate">
                    {specialFeature}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Desktop Layout */}
        <div className="hidden md:flex gap-0">
          <div className="relative w-32 h-36 flex-shrink-0 overflow-hidden">
            <img
              src={image || '/placeholder-event.jpg'}
              alt={title}
              className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
            />
            <div className="absolute inset-0 bg-gradient-to-r from-transparent to-black/10" />

            <div className="absolute top-3 left-3 bg-white/95 backdrop-blur-sm rounded-lg px-2 py-1.5 text-center shadow-sm">
              <div className="text-sm font-bold text-primary leading-none">{day}</div>
              <div className="text-xs text-muted-foreground uppercase leading-none mt-0.5">
                {month.slice(0, 3)}
              </div>
            </div>

            {price && (
              <div className="absolute bottom-3 left-3 bg-green-600/90 backdrop-blur-sm text-white px-2 py-1 rounded-md text-xs font-medium shadow-sm">
                {price}
              </div>
            )}
          </div>

          <div className="flex-1 p-5 min-w-0 flex flex-col">
            <div className="flex items-start justify-between gap-3 mb-3">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <CategoryIcon className="w-4 h-4 text-primary" />
                </div>
                <Badge variant="secondary" className="text-xs px-2.5 py-1">
                  {category}
                </Badge>
              </div>

              <div className="flex items-center gap-2 flex-shrink-0">
                {source && (
                  <Badge variant="outline" className="text-xs px-2 py-0.5">
                    {source}
                  </Badge>
                )}
                {onToggleFavorite && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation()
                      onToggleFavorite()
                    }}
                    className="h-8 w-8 p-0 hover:bg-red-50 dark:hover:bg-red-950 opacity-70 group-hover:opacity-100 transition-opacity"
                  >
                    <Heart
                      className={`w-4 h-4 transition-colors ${
                        isFavorite
                          ? 'fill-red-500 text-red-500'
                          : 'text-muted-foreground hover:text-red-500'
                      }`}
                    />
                  </Button>
                )}
              </div>
            </div>

            <h3 className="font-semibold text-lg leading-tight line-clamp-2 mb-3 group-hover:text-primary transition-colors">
              {title}
            </h3>

            <div className="space-y-2 mb-3">
              <div className="flex items-center gap-2">
                <MapPin className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                <span className="text-sm text-muted-foreground truncate">{location}</span>
              </div>
              {time && (
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                  <span className="text-sm text-muted-foreground">
                    {time} {t('event.oclock')}
                  </span>
                </div>
              )}
            </div>

            {description && description.trim() !== '' && (
              <p className="text-sm text-muted-foreground line-clamp-2 leading-relaxed mb-3">
                {description}
              </p>
            )}

            {specialFeature && (
              <div className="flex items-center gap-2 mb-3">
                <span className="text-orange-500">*</span>
                <span className="text-sm text-orange-600 font-medium">{specialFeature}</span>
              </div>
            )}

            <div className="flex-grow"></div>

            <div className="flex items-center justify-between pt-3 border-t border-border/50">
              <div className="flex-1"></div>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 px-3 text-sm opacity-0 group-hover:opacity-100 transition-opacity ml-3 hover:bg-primary/10"
                onClick={(e) => {
                  e.stopPropagation()
                  setShowDetailModal(true)
                }}
              >
                {t('event.details')}
                <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
          </div>
        </div>
      </Card>

      <EventDetailModal
        event={eventData}
        isOpen={showDetailModal}
        onClose={() => setShowDetailModal(false)}
        isFavorite={isFavorite}
        onToggleFavorite={onToggleFavorite}
      />
    </>
  )
}
