import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(dateString: string, locale: string = 'en-US') {
  const date = new Date(dateString)
  return {
    day: date.getDate().toString(),
    month: date.toLocaleDateString(locale, { month: 'short' }),
    weekday: date.toLocaleDateString(locale, { weekday: 'short' }),
    fullDate: date.toLocaleDateString(locale, {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }
}

export function formatTime(timeString?: string) {
  if (!timeString) return ''
  const [hours, minutes] = timeString.split(':')
  return `${hours}:${minutes}`
}

export function formatPrice(price?: number, isFree?: boolean) {
  if (isFree) return 'Free'
  if (price === undefined || price === null) return ''
  if (price === 0) return 'Free'
  return `$${price.toFixed(2)}`
}

export function mapPriceRangeToBackend(maxBudget: number): string {
  if (maxBudget <= 0) return 'free'
  if (maxBudget <= 50) return 'budget'
  if (maxBudget <= 100) return 'mid'
  return 'premium'
}

// Map frontend category names to backend enum values
const categoryMapping: Record<string, string> = {
  'Concert': 'music',
  'Theater': 'theater',
  'Art': 'arts_culture',
  'Family': 'family',
  'Sport': 'sports',
  'Markets': 'markets',
  'Food': 'food_drinks',
  'Knowledge': 'workshops',
}

export function mapCategoryToBackend(frontendCategory: string): string {
  return categoryMapping[frontendCategory] || frontendCategory.toLowerCase()
}

// Category-based placeholder images using picsum.photos (reliable placeholder service)
// Each ID corresponds to a specific image style
const categoryImages: Record<string, string> = {
  // Music & Entertainment (concert/stage images)
  'music': 'https://picsum.photos/seed/music/400/300',
  'concert': 'https://picsum.photos/seed/concert/400/300',
  'live music': 'https://picsum.photos/seed/livemusic/400/300',

  // Theater & Performance
  'theater': 'https://picsum.photos/seed/theater/400/300',
  'theatre': 'https://picsum.photos/seed/theatre/400/300',
  'performance': 'https://picsum.photos/seed/performance/400/300',

  // Art & Culture
  'art': 'https://picsum.photos/seed/art/400/300',
  'exhibition': 'https://picsum.photos/seed/exhibition/400/300',
  'museum': 'https://picsum.photos/seed/museum/400/300',
  'arts_culture': 'https://picsum.photos/seed/culture/400/300',

  // Food & Drinks
  'food': 'https://picsum.photos/seed/food/400/300',
  'food_drinks': 'https://picsum.photos/seed/dining/400/300',
  'restaurant': 'https://picsum.photos/seed/restaurant/400/300',
  'dining': 'https://picsum.photos/seed/dinner/400/300',

  // Wine & Tasting
  'wine': 'https://picsum.photos/seed/wine/400/300',
  'tasting': 'https://picsum.photos/seed/tasting/400/300',
  'wine tasting': 'https://picsum.photos/seed/winetasting/400/300',

  // Sports & Fitness
  'sports': 'https://picsum.photos/seed/sports/400/300',
  'sport': 'https://picsum.photos/seed/sport/400/300',
  'fitness': 'https://picsum.photos/seed/fitness/400/300',

  // Outdoor & Nature
  'outdoor': 'https://picsum.photos/seed/outdoor/400/300',
  'nature': 'https://picsum.photos/seed/nature/400/300',
  'hiking': 'https://picsum.photos/seed/hiking/400/300',

  // Markets & Shopping
  'market': 'https://picsum.photos/seed/market/400/300',
  'markets': 'https://picsum.photos/seed/markets/400/300',
  'shopping': 'https://picsum.photos/seed/shopping/400/300',

  // Party & Nightlife
  'party': 'https://picsum.photos/seed/party/400/300',
  'nightlife': 'https://picsum.photos/seed/nightlife/400/300',
  'club': 'https://picsum.photos/seed/club/400/300',

  // Workshops & Learning
  'workshop': 'https://picsum.photos/seed/workshop/400/300',
  'workshops': 'https://picsum.photos/seed/learning/400/300',
  'class': 'https://picsum.photos/seed/class/400/300',
  'seminar': 'https://picsum.photos/seed/seminar/400/300',

  // Family & Kids
  'family': 'https://picsum.photos/seed/family/400/300',
  'kids': 'https://picsum.photos/seed/kids/400/300',
  'children': 'https://picsum.photos/seed/children/400/300',

  // Festival
  'festival': 'https://picsum.photos/seed/festival/400/300',

  // Networking & Business
  'networking': 'https://picsum.photos/seed/networking/400/300',
  'business': 'https://picsum.photos/seed/business/400/300',
  'meetup': 'https://picsum.photos/seed/meetup/400/300',
}

// Default fallback image
const defaultEventImage = 'https://picsum.photos/seed/event/400/300'

export function getCategoryImage(category: string, title?: string): string {
  const categoryLower = category.toLowerCase()
  const titleLower = (title || '').toLowerCase()

  // Check title for specific keywords first (more specific match)
  if (titleLower.includes('wine') || titleLower.includes('tasting')) {
    return categoryImages['wine']
  }
  if (titleLower.includes('concert') || titleLower.includes('live music')) {
    return categoryImages['concert']
  }
  if (titleLower.includes('festival')) {
    return categoryImages['festival']
  }

  // Check category mappings
  for (const [key, url] of Object.entries(categoryImages)) {
    if (categoryLower.includes(key)) {
      return url
    }
  }

  // Check title for any category keywords
  for (const [key, url] of Object.entries(categoryImages)) {
    if (titleLower.includes(key)) {
      return url
    }
  }

  return defaultEventImage
}

export function computeDateRange(timeRange: string): { dateFrom?: string; dateTo?: string } {
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  switch (timeRange) {
    case 'today':
      return {
        dateFrom: today.toISOString().split('T')[0],
        dateTo: today.toISOString().split('T')[0]
      }
    case 'tomorrow': {
      const tomorrow = new Date(today)
      tomorrow.setDate(tomorrow.getDate() + 1)
      return {
        dateFrom: tomorrow.toISOString().split('T')[0],
        dateTo: tomorrow.toISOString().split('T')[0]
      }
    }
    case 'thisWeek': {
      const endOfWeek = new Date(today)
      endOfWeek.setDate(endOfWeek.getDate() + (7 - endOfWeek.getDay()))
      return {
        dateFrom: today.toISOString().split('T')[0],
        dateTo: endOfWeek.toISOString().split('T')[0]
      }
    }
    case 'thisWeekend': {
      const saturday = new Date(today)
      saturday.setDate(saturday.getDate() + (6 - saturday.getDay()))
      const sunday = new Date(saturday)
      sunday.setDate(sunday.getDate() + 1)
      return {
        dateFrom: saturday.toISOString().split('T')[0],
        dateTo: sunday.toISOString().split('T')[0]
      }
    }
    case 'nextWeek': {
      const endDate = new Date(today)
      endDate.setDate(endDate.getDate() + 7)
      return {
        dateFrom: today.toISOString().split('T')[0],
        dateTo: endDate.toISOString().split('T')[0]
      }
    }
    case 'nextMonth': {
      const nextMonth = new Date(today)
      nextMonth.setMonth(nextMonth.getMonth() + 1)
      return {
        dateFrom: today.toISOString().split('T')[0],
        dateTo: nextMonth.toISOString().split('T')[0]
      }
    }
    default:
      return {}
  }
}
