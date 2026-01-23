"use client"

import { useState } from 'react'
import {
  MapPin,
  Navigation,
  ChevronDown,
  ChevronRight,
  X,
  Plus,
  Sparkles,
  Target,
  List,
} from 'lucide-react'
import { Input } from './ui/input'
import { Button } from './ui/button'
import { Slider } from './ui/slider'
import { Badge } from './ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
} from './ui/dialog'
import { Checkbox } from './ui/checkbox'
import { useLanguage } from '@/contexts/LanguageContext'
import { SearchFilters } from '@/types'
import { reverseGeocode } from '@/lib/api'

interface SearchScreenProps {
  onStartSearch: (filters: SearchFilters) => void
  onShowResults?: () => void
}

// Category data structure
const categoryData = {
  Concert: {
    label: 'Concerts & Party',
    color: '#8B5CF6',
    subcategories: [
      'pop-rock',
      'electronic',
      'jazz-blues',
      'classical',
      'hip-hop',
      'folk',
      'metal-punk',
      'world-music',
    ],
  },
  Theater: {
    label: 'Theater & Stage',
    color: '#EF4444',
    subcategories: ['drama', 'musical', 'comedy', 'dance-ballet', 'opera', 'poetry'],
  },
  Art: {
    label: 'Art & Museums',
    color: '#3B82F6',
    subcategories: ['exhibition', 'museum', 'gallery', 'photography', 'film', 'architecture'],
  },
  Family: {
    label: 'Family & Kids',
    color: '#10B981',
    subcategories: ['children-theater', 'workshops', 'playground-events', 'family-concerts'],
  },
  Sport: {
    label: 'Sports & Recreation',
    color: '#F59E0B',
    subcategories: ['football', 'basketball', 'tennis', 'running', 'cycling', 'fitness-yoga'],
  },
  Markets: {
    label: 'Markets & Fairs',
    color: '#6366F1',
    subcategories: ['flea-market', 'christmas-market', 'food-market', 'trade-fair'],
  },
  Food: {
    label: 'Food & Culinary',
    color: '#EC4899',
    subcategories: ['food-festivals', 'wine-tasting', 'cooking-classes', 'street-food'],
  },
  Knowledge: {
    label: 'Knowledge & Workshops',
    color: '#14B8A6',
    subcategories: ['talks', 'seminars', 'workshops', 'networking', 'tech-meetups'],
  },
}

const defaultFilters: SearchFilters = {
  location: '',
  useCurrentLocation: false,
  radius: 25,
  categories: [],
  subcategories: [],
  timeRange: 'thisWeek',
  dateFrom: undefined,
  dateTo: undefined,
  budget: {
    min: 0,
    max: 300,
    onlyFree: false,
  },
  keywords: '',
  quickFilters: [],
  specialTags: [],
  searchMode: 'standard',
  eventFrequency: [],
  advancedFilters: {
    accessibility: [],
    ageGroups: [],
    features: [],
    catering: [],
  },
}

export function SearchScreen({ onStartSearch, onShowResults }: SearchScreenProps) {
  const { t } = useLanguage()
  const [filters, setFilters] = useState<SearchFilters>(defaultFilters)
  const [showCategoriesModal, setShowCategoriesModal] = useState(false)
  const [showBudgetOptions, setShowBudgetOptions] = useState(false)
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set())

  const handleLocationDetection = async () => {
    if (!navigator.geolocation) {
      alert('Geolocation is not supported by this browser')
      return
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords
        const locationName = await reverseGeocode(latitude, longitude)
        setFilters((prev) => ({
          ...prev,
          location: locationName,
          useCurrentLocation: true,
        }))
      },
      (error) => {
        console.error('Error getting location:', error)
        let errorMessage = 'Could not determine location. '

        if (error.code === 1) {
          errorMessage += 'Please allow location access in your browser settings.'
        } else if (error.code === 2) {
          errorMessage += 'Location information is unavailable. Please try again.'
        } else if (error.code === 3) {
          errorMessage += 'Location request timed out. Please try again.'
        } else {
          errorMessage += 'Please try entering your location manually.'
        }

        alert(errorMessage)
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    )
  }

  const updateFilters = (updates: Partial<SearchFilters>) => {
    setFilters((prev) => ({ ...prev, ...updates }))
  }

  const handleStartSearch = () => {
    if (!filters.location.trim()) {
      alert('Please enter a location')
      return
    }

    if (filters.dateFrom && filters.dateTo && filters.dateFrom > filters.dateTo) {
      alert('End date must be after start date')
      return
    }

    onStartSearch(filters)
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-6 max-w-2xl">
        <div className="space-y-6">
          {/* Search Mode */}
          <div className="space-y-3">
            <div className="flex items-center gap-4">
              <label className="font-medium whitespace-nowrap w-8 md:w-32">
                <span className="md:hidden">Mode</span>
                <span className="hidden md:inline">Mode</span>
              </label>
              <div className="flex-1 flex gap-2">
                {(['standard', 'discover'] as const).map((mode) => {
                  const modeInfo =
                    mode === 'discover'
                      ? { icon: <Sparkles className="w-4 h-4" />, label: t('search.discover') }
                      : { icon: <Target className="w-4 h-4" />, label: t('search.standard') }

                  return (
                    <Button
                      key={mode}
                      variant={filters.searchMode === mode ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => updateFilters({ searchMode: mode })}
                      className="flex-1 h-12 md:h-10"
                    >
                      {modeInfo.icon}
                      <span className="ml-1">{modeInfo.label}</span>
                    </Button>
                  )
                })}
              </div>
            </div>
            {filters.searchMode === 'discover' && (
              <div className="text-xs text-muted-foreground p-2 bg-muted/50 rounded">
                Prioritizes unique & experimental events
              </div>
            )}
          </div>

          {/* Location */}
          <div className="space-y-3">
            <div className="flex items-center gap-4">
              <label className="font-medium whitespace-nowrap w-8 md:w-32">
                <span className="md:hidden"><MapPin className="w-4 h-4" /></span>
                <span className="hidden md:inline">{t('search.location')}</span>
              </label>
              <div className="flex-1 flex gap-3">
                <div className="flex-1 relative">
                  <Input
                    placeholder={t('search.locationPlaceholder')}
                    value={filters.location}
                    onChange={(e) =>
                      updateFilters({ location: e.target.value, useCurrentLocation: false })
                    }
                    className="h-12 md:h-10"
                  />
                </div>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={handleLocationDetection}
                  className="h-12 w-12 md:h-10 md:w-10 flex-shrink-0"
                  title="Use current location"
                >
                  <Navigation className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </div>

          {/* Radius */}
          <div className="space-y-3">
            <div className="flex items-center gap-4">
              <label className="font-medium whitespace-nowrap w-8 md:w-32">
                <span className="md:hidden">km</span>
                <span className="hidden md:inline">{t('search.radius')}</span>
              </label>
              <div className="flex-1 flex items-center gap-3">
                <span className="text-sm">{filters.radius} km</span>
                <Slider
                  value={[filters.radius]}
                  onValueChange={(value) => updateFilters({ radius: value[0] })}
                  max={100}
                  min={1}
                  step={1}
                  className="flex-1"
                />
              </div>
            </div>
          </div>

          {/* Categories */}
          {filters.searchMode !== 'discover' && (
            <div className="space-y-3">
              <div className="flex items-center gap-4">
                <label className="font-medium whitespace-nowrap w-8 md:w-32">
                  <span className="md:hidden">Cat</span>
                  <span className="hidden md:inline">{t('search.categories')}</span>
                </label>
                <div className="flex-1">
                  <Dialog open={showCategoriesModal} onOpenChange={setShowCategoriesModal}>
                    <DialogTrigger asChild>
                      <Button variant="outline" className="w-full justify-between h-12 md:h-10">
                        <span>
                          {filters.categories.length > 0
                            ? `${filters.categories.length} Categories`
                            : t('search.allCategories')}
                        </span>
                        <ChevronRight className="w-4 h-4" />
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                      <DialogHeader>
                        <DialogTitle>{t('search.categories')}</DialogTitle>
                        <DialogDescription>
                          Select the event categories you are interested in
                        </DialogDescription>
                      </DialogHeader>
                      <div className="space-y-4">
                        <div className="space-y-2">
                          {Object.entries(categoryData).map(([categoryId, category]) => (
                            <div key={categoryId} className="border rounded-lg p-3">
                              <div className="flex items-center gap-3 mb-2">
                                <Checkbox
                                  checked={filters.categories.includes(categoryId)}
                                  onCheckedChange={() => {
                                    const isSelected = filters.categories.includes(categoryId)
                                    const newCategories = isSelected
                                      ? filters.categories.filter((id) => id !== categoryId)
                                      : [...filters.categories, categoryId]
                                    updateFilters({ categories: newCategories })
                                  }}
                                />
                                <span className="font-medium" style={{ color: category.color }}>
                                  {category.label}
                                </span>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-6 w-6 p-0 ml-auto"
                                  onClick={() => {
                                    const isExpanded = expandedCategories.has(categoryId)
                                    const newExpanded = new Set(expandedCategories)
                                    if (isExpanded) {
                                      newExpanded.delete(categoryId)
                                    } else {
                                      newExpanded.add(categoryId)
                                    }
                                    setExpandedCategories(newExpanded)
                                  }}
                                >
                                  {expandedCategories.has(categoryId) ? (
                                    <ChevronDown className="w-4 h-4" />
                                  ) : (
                                    <ChevronRight className="w-4 h-4" />
                                  )}
                                </Button>
                              </div>

                              {expandedCategories.has(categoryId) && (
                                <div className="pl-6 pt-2 border-t border-border/30">
                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                                    {category.subcategories.map((subcategory: string) => (
                                      <div
                                        key={subcategory}
                                        className="flex items-center space-x-2 p-1 hover:bg-muted/30 rounded text-sm"
                                      >
                                        <Checkbox
                                          id={`subcategory-${subcategory}`}
                                          checked={filters.subcategories.includes(subcategory)}
                                          onCheckedChange={() => {
                                            const isSelected =
                                              filters.subcategories.includes(subcategory)
                                            const newSubcategories = isSelected
                                              ? filters.subcategories.filter(
                                                  (id) => id !== subcategory
                                                )
                                              : [...filters.subcategories, subcategory]
                                            updateFilters({ subcategories: newSubcategories })
                                          }}
                                        />
                                        <label
                                          htmlFor={`subcategory-${subcategory}`}
                                          className="text-sm cursor-pointer flex-1 text-muted-foreground hover:text-foreground"
                                        >
                                          {subcategory.replace(/-/g, ' ')}
                                        </label>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>

                        <div className="flex justify-between">
                          <Button
                            variant="ghost"
                            onClick={() => updateFilters({ categories: [], subcategories: [] })}
                          >
                            {t('common.reset')}
                          </Button>
                          <Button onClick={() => setShowCategoriesModal(false)}>
                            {t('common.apply')}
                          </Button>
                        </div>
                      </div>
                    </DialogContent>
                  </Dialog>
                </div>
              </div>
            </div>
          )}

          {/* Time Period */}
          <div className="space-y-3">
            <div className="flex items-center gap-4">
              <label className="font-medium whitespace-nowrap w-8 md:w-32">
                <span className="md:hidden">When</span>
                <span className="hidden md:inline">{t('search.timePeriod')}</span>
              </label>
              <div className="flex-1">
                <Select
                  value={filters.timeRange}
                  onValueChange={(value) => updateFilters({ timeRange: value })}
                >
                  <SelectTrigger className="w-full justify-between h-12 md:h-10">
                    <SelectValue placeholder={t('search.timePeriod')} />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">{t('common.all')}</SelectItem>
                    <SelectItem value="today">{t('common.today')}</SelectItem>
                    <SelectItem value="tomorrow">{t('common.tomorrow')}</SelectItem>
                    <SelectItem value="thisWeek">{t('common.thisWeek')}</SelectItem>
                    <SelectItem value="thisWeekend">{t('common.thisWeekend')}</SelectItem>
                    <SelectItem value="nextWeek">{t('common.nextWeek')}</SelectItem>
                    <SelectItem value="nextMonth">{t('common.nextMonth')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {/* Budget */}
          <div className="space-y-3">
            <div className="flex items-center gap-4">
              <label className="font-medium whitespace-nowrap w-8 md:w-32">
                <span className="md:hidden">$</span>
                <span className="hidden md:inline">{t('search.budget')}</span>
              </label>
              <div className="flex-1">
                <Button
                  variant="outline"
                  onClick={() => setShowBudgetOptions(!showBudgetOptions)}
                  className="w-full justify-between h-12 md:h-10"
                >
                  <span>
                    {filters.budget.onlyFree
                      ? t('event.free')
                      : filters.budget.max !== 300
                        ? `$${filters.budget.max}`
                        : t('search.budget')}
                  </span>
                  <ChevronDown
                    className={`w-4 h-4 transition-transform ${showBudgetOptions ? 'rotate-180' : ''}`}
                  />
                </Button>
              </div>
            </div>

            {showBudgetOptions && (
              <div className="bg-card border rounded-lg p-4 space-y-3">
                <div className="flex items-center gap-4">
                  <Checkbox
                    checked={filters.budget.onlyFree}
                    onCheckedChange={(checked) =>
                      updateFilters({
                        budget: {
                          ...filters.budget,
                          onlyFree: !!checked,
                          max: checked ? 0 : 300,
                        },
                      })
                    }
                  />
                  <span className="text-sm">Free Events Only</span>
                </div>
                {!filters.budget.onlyFree && (
                  <div className="space-y-2">
                    <Slider
                      value={[filters.budget.max]}
                      onValueChange={(value) =>
                        updateFilters({
                          budget: { ...filters.budget, max: value[0] },
                        })
                      }
                      max={300}
                      min={0}
                      step={5}
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>$0</span>
                      <span>$300+</span>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Search Button */}
          <div className="pt-4 space-y-3">
            <Button
              onClick={handleStartSearch}
              className="w-full h-12 font-medium bg-primary hover:bg-primary/90 text-primary-foreground"
            >
              {t('search.searchButton')}
            </Button>

            {onShowResults && (
              <Button
                onClick={onShowResults}
                variant="outline"
                className="w-full h-12 border-2"
              >
                <List className="w-4 h-4 mr-2" />
                {t('search.showResults')}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
