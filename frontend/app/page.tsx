"use client"

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Header } from '@/components/Header'
import { SearchScreen } from '@/components/SearchScreen'
import { SearchFilters } from '@/types'

export default function HomePage() {
  const router = useRouter()

  const handleStartSearch = (filters: SearchFilters) => {
    // Convert filters to URL search params
    const params = new URLSearchParams()

    params.set('location', filters.location)
    params.set('radius', filters.radius.toString())
    params.set('mode', filters.searchMode)
    params.set('timeRange', filters.timeRange)

    if (filters.categories.length > 0) {
      params.set('categories', filters.categories.join(','))
    }

    if (filters.budget.onlyFree) {
      params.set('priceRange', 'free')
    } else if (filters.budget.max < 300) {
      if (filters.budget.max <= 50) {
        params.set('priceRange', 'budget')
      } else if (filters.budget.max <= 100) {
        params.set('priceRange', 'mid')
      } else {
        params.set('priceRange', 'premium')
      }
    }

    if (filters.keywords) {
      params.set('query', filters.keywords)
    }

    router.push(`/results?${params.toString()}`)
  }

  const handleShowResults = () => {
    router.push('/results')
  }

  const handleSettingsClick = () => {
    router.push('/settings')
  }

  return (
    <main className="min-h-screen bg-background">
      <Header onSettingsClick={handleSettingsClick} />
      <SearchScreen
        onStartSearch={handleStartSearch}
        onShowResults={handleShowResults}
      />
    </main>
  )
}
