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
