"use client"

import { useState } from 'react'
import { Settings, Map, List, User } from 'lucide-react'
import { Button } from './ui/button'
import { useLanguage } from '@/contexts/LanguageContext'
import { useAuth } from '@/contexts/AuthContext'
import { AuthModal } from './AuthModal'

interface HeaderProps {
  onSettingsClick?: () => void
  viewMode?: 'list' | 'map'
  onViewModeChange?: (mode: 'list' | 'map') => void
  showViewToggle?: boolean
}

export function Header({
  onSettingsClick,
  viewMode = 'list',
  onViewModeChange,
  showViewToggle = false,
}: HeaderProps) {
  const { t } = useLanguage()
  const { user, loading } = useAuth()
  const [authOpen, setAuthOpen] = useState(false)

  const userInitial = user?.email?.[0]?.toUpperCase() || '?'

  return (
    <>
      <header className="border-b bg-background/95 backdrop-blur sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-xl font-bold text-primary">{t('search.title')}</span>
              <span className="text-sm text-muted-foreground font-medium hidden sm:inline">
                Find unique events!
              </span>
            </div>

            <div className="flex items-center gap-2">
              {showViewToggle && onViewModeChange && (
                <div className="flex items-center bg-muted rounded-lg p-1">
                  <Button
                    variant={viewMode === 'list' ? 'default' : 'ghost'}
                    size="sm"
                    onClick={() => onViewModeChange('list')}
                    className="h-8 px-3"
                  >
                    <List className="w-4 h-4 mr-1" />
                    <span className="hidden sm:inline">List</span>
                  </Button>
                  <Button
                    variant={viewMode === 'map' ? 'default' : 'ghost'}
                    size="sm"
                    onClick={() => onViewModeChange('map')}
                    className="h-8 px-3"
                  >
                    <Map className="w-4 h-4 mr-1" />
                    <span className="hidden sm:inline">Map</span>
                  </Button>
                </div>
              )}

              {!loading && (
                user ? (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-9 w-9 rounded-full bg-primary text-primary-foreground text-sm font-bold"
                    onClick={onSettingsClick}
                    title={user.email || 'Profile'}
                  >
                    {userInitial}
                  </Button>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setAuthOpen(true)}
                    className="h-9"
                  >
                    <User className="w-4 h-4 mr-1" />
                    Sign In
                  </Button>
                )
              )}

              <Button
                variant="ghost"
                size="icon"
                onClick={onSettingsClick}
                className="h-9 w-9"
              >
                <Settings className="w-5 h-5" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      <AuthModal open={authOpen} onOpenChange={setAuthOpen} />
    </>
  )
}
