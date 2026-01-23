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

// Category-based placeholder images using Unsplash
const categoryImages: Record<string, string> = {
  // Music & Entertainment
  'music': 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=400&h=300&fit=crop',
  'concert': 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=400&h=300&fit=crop',
  'live music': 'https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=400&h=300&fit=crop',

  // Theater & Performance
  'theater': 'https://images.unsplash.com/photo-1503095396549-807759245b35?w=400&h=300&fit=crop',
  'theatre': 'https://images.unsplash.com/photo-1503095396549-807759245b35?w=400&h=300&fit=crop',
  'performance': 'https://images.unsplash.com/photo-1503095396549-807759245b35?w=400&h=300&fit=crop',

  // Art & Culture
  'art': 'https://images.unsplash.com/photo-1531243269054-5ebf6f34081e?w=400&h=300&fit=crop',
  'exhibition': 'https://images.unsplash.com/photo-1531243269054-5ebf6f34081e?w=400&h=300&fit=crop',
  'museum': 'https://images.unsplash.com/photo-1531243269054-5ebf6f34081e?w=400&h=300&fit=crop',
  'arts_culture': 'https://images.unsplash.com/photo-1531243269054-5ebf6f34081e?w=400&h=300&fit=crop',

  // Food & Drinks
  'food': 'https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=400&h=300&fit=crop',
  'food_drinks': 'https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=400&h=300&fit=crop',
  'restaurant': 'https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=400&h=300&fit=crop',
  'dining': 'https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=400&h=300&fit=crop',

  // Wine & Tasting
  'wine': 'https://images.unsplash.com/photo-1510812431401-41d2bd2722f3?w=400&h=300&fit=crop',
  'tasting': 'https://images.unsplash.com/photo-1510812431401-41d2bd2722f3?w=400&h=300&fit=crop',
  'wine tasting': 'https://images.unsplash.com/photo-1510812431401-41d2bd2722f3?w=400&h=300&fit=crop',

  // Sports & Fitness
  'sports': 'https://images.unsplash.com/photo-1546519638-68e109498ffc?w=400&h=300&fit=crop',
  'sport': 'https://images.unsplash.com/photo-1546519638-68e109498ffc?w=400&h=300&fit=crop',
  'fitness': 'https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=400&h=300&fit=crop',

  // Outdoor & Nature
  'outdoor': 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=400&h=300&fit=crop',
  'nature': 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=400&h=300&fit=crop',
  'hiking': 'https://images.unsplash.com/photo-1551632811-561732d1e306?w=400&h=300&fit=crop',

  // Markets & Shopping
  'market': 'https://images.unsplash.com/photo-1488459716781-31db52582fe9?w=400&h=300&fit=crop',
  'markets': 'https://images.unsplash.com/photo-1488459716781-31db52582fe9?w=400&h=300&fit=crop',
  'shopping': 'https://images.unsplash.com/photo-1488459716781-31db52582fe9?w=400&h=300&fit=crop',

  // Party & Nightlife
  'party': 'https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=400&h=300&fit=crop',
  'nightlife': 'https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=400&h=300&fit=crop',
  'club': 'https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=400&h=300&fit=crop',

  // Workshops & Learning
  'workshop': 'https://images.unsplash.com/photo-1552664730-d307ca884978?w=400&h=300&fit=crop',
  'workshops': 'https://images.unsplash.com/photo-1552664730-d307ca884978?w=400&h=300&fit=crop',
  'class': 'https://images.unsplash.com/photo-1552664730-d307ca884978?w=400&h=300&fit=crop',
  'seminar': 'https://images.unsplash.com/photo-1552664730-d307ca884978?w=400&h=300&fit=crop',

  // Family & Kids
  'family': 'https://images.unsplash.com/photo-1609220136736-443140cffec6?w=400&h=300&fit=crop',
  'kids': 'https://images.unsplash.com/photo-1609220136736-443140cffec6?w=400&h=300&fit=crop',
  'children': 'https://images.unsplash.com/photo-1609220136736-443140cffec6?w=400&h=300&fit=crop',

  // Festival
  'festival': 'https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?w=400&h=300&fit=crop',

  // Networking & Business
  'networking': 'https://images.unsplash.com/photo-1515187029135-18ee286d815b?w=400&h=300&fit=crop',
  'business': 'https://images.unsplash.com/photo-1515187029135-18ee286d815b?w=400&h=300&fit=crop',
  'meetup': 'https://images.unsplash.com/photo-1515187029135-18ee286d815b?w=400&h=300&fit=crop',
}

// Default fallback image
const defaultEventImage = 'https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=400&h=300&fit=crop'

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
      const nextMonday = new Date(today)
      nextMonday.setDate(nextMonday.getDate() + (8 - nextMonday.getDay()))
      const nextSunday = new Date(nextMonday)
      nextSunday.setDate(nextSunday.getDate() + 6)
      return {
        dateFrom: nextMonday.toISOString().split('T')[0],
        dateTo: nextSunday.toISOString().split('T')[0]
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
