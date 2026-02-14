"use client"

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowLeft, Clock, Heart, Trash2, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuth } from '@/contexts/AuthContext'
import { getSearchHistory, clearSearchHistory, getFavorites, removeFavorite } from '@/lib/api'
import { SearchHistoryItem, FavoriteItem } from '@/types'

export default function ProfilePage() {
  const router = useRouter()
  const { user, loading: authLoading } = useAuth()
  const [history, setHistory] = useState<SearchHistoryItem[]>([])
  const [favorites, setFavorites] = useState<FavoriteItem[]>([])
  const [loadingHistory, setLoadingHistory] = useState(true)
  const [loadingFavorites, setLoadingFavorites] = useState(true)

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/')
    }
  }, [user, authLoading, router])

  useEffect(() => {
    if (!user) return

    getSearchHistory(20)
      .then(({ items }) => setHistory(items))
      .catch((err) => console.error('Failed to load history:', err))
      .finally(() => setLoadingHistory(false))

    getFavorites()
      .then(({ items }) => setFavorites(items))
      .catch((err) => console.error('Failed to load favorites:', err))
      .finally(() => setLoadingFavorites(false))
  }, [user])

  const handleClearHistory = async () => {
    try {
      await clearSearchHistory()
      setHistory([])
    } catch (err) {
      console.error('Failed to clear history:', err)
    }
  }

  const handleRemoveFavorite = async (eventId: string) => {
    try {
      await removeFavorite(eventId)
      setFavorites((prev) => prev.filter((f) => f.event_id !== eventId))
    } catch (err) {
      console.error('Failed to remove favorite:', err)
    }
  }

  if (authLoading || !user) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    )
  }

  return (
    <main className="min-h-screen bg-background">
      <header className="border-b bg-background/95 backdrop-blur sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => router.back()}>
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <h1 className="text-xl font-bold">Profile</h1>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-6 max-w-2xl space-y-6">
        {/* User Info */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="h-14 w-14 rounded-full bg-primary text-primary-foreground flex items-center justify-center text-2xl font-bold">
                {user.email?.[0]?.toUpperCase() || '?'}
              </div>
              <div>
                <p className="font-semibold text-lg">
                  {user.user_metadata?.display_name || user.email?.split('@')[0]}
                </p>
                <p className="text-sm text-muted-foreground">{user.email}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Search History */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Clock className="w-5 h-5" />
                Search History
              </CardTitle>
              {history.length > 0 && (
                <Button variant="ghost" size="sm" onClick={handleClearHistory}>
                  <Trash2 className="w-4 h-4 mr-1" />
                  Clear
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {loadingHistory ? (
              <p className="text-sm text-muted-foreground">Loading...</p>
            ) : history.length === 0 ? (
              <p className="text-sm text-muted-foreground">No search history yet. Start searching for events!</p>
            ) : (
              <div className="space-y-3">
                {history.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-start justify-between p-3 rounded-lg bg-muted/50 hover:bg-muted cursor-pointer"
                    onClick={() => {
                      const params = new URLSearchParams({ location: item.location || '', query: item.query })
                      if (item.category) params.set('categories', item.category)
                      if (item.radius_km) params.set('radius', String(item.radius_km))
                      router.push(`/results?${params.toString()}`)
                    }}
                  >
                    <div className="flex items-start gap-3">
                      <Search className="w-4 h-4 mt-0.5 text-muted-foreground" />
                      <div>
                        <p className="text-sm font-medium">{item.query}</p>
                        <p className="text-xs text-muted-foreground">
                          {item.location && `${item.location} · `}
                          {item.results_count} results · {new Date(item.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Favorites */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Heart className="w-5 h-5" />
              Favorites ({favorites.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loadingFavorites ? (
              <p className="text-sm text-muted-foreground">Loading...</p>
            ) : favorites.length === 0 ? (
              <p className="text-sm text-muted-foreground">No favorites yet. Heart events to save them here!</p>
            ) : (
              <div className="space-y-3">
                {favorites.map((fav) => {
                  const data = fav.event_data as Record<string, unknown>
                  const name = (data.event_name as string) || fav.event_id
                  const location = data.location as Record<string, unknown> | undefined
                  const city = location?.city as string || ''

                  return (
                    <div key={fav.id} className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                      <div>
                        <p className="text-sm font-medium">{name}</p>
                        <p className="text-xs text-muted-foreground">
                          {city && `${city} · `}
                          Saved {new Date(fav.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-destructive"
                        onClick={() => handleRemoveFavorite(fav.event_id)}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </main>
  )
}
