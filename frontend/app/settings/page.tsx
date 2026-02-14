"use client"

import { useRouter } from 'next/navigation'
import { useTheme } from 'next-themes'
import { ArrowLeft, Globe, Moon, Bell, Search, User, LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { useLanguage } from '@/contexts/LanguageContext'
import { useUserPreferences } from '@/contexts/UserPreferencesContext'
import { useAuth } from '@/contexts/AuthContext'
import { Language } from '@/types'
import { useEffect, useState } from 'react'
import { AuthModal } from '@/components/AuthModal'

const languageOptions: { value: Language; label: string }[] = [
  { value: 'en', label: 'English' },
  { value: 'de', label: 'Deutsch' },
  { value: 'fr', label: 'Français' },
  { value: 'es', label: 'Español' },
]

export default function SettingsPage() {
  const router = useRouter()
  const { language, setLanguage, t } = useLanguage()
  const { theme, setTheme } = useTheme()
  const { preferences, updateNotifications, updateSearchDefaults } = useUserPreferences()
  const { user, signOut } = useAuth()
  const [mounted, setMounted] = useState(false)
  const [authOpen, setAuthOpen] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  const handleBack = () => {
    router.back()
  }

  return (
    <>
    <main className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-background/95 backdrop-blur sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={handleBack}>
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <h1 className="text-xl font-bold">{t('settings.title')}</h1>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-6 max-w-2xl">
        <div className="space-y-6">
          {/* Account */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="w-5 h-5" />
                Account
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {user ? (
                <>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Email</span>
                    <span className="text-sm font-medium">{user.email}</span>
                  </div>
                  <Separator />
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Display Name</span>
                    <span className="text-sm font-medium">
                      {user.user_metadata?.display_name || user.email?.split('@')[0]}
                    </span>
                  </div>
                  <Separator />
                  <Button
                    variant="outline"
                    className="w-full"
                    onClick={() => signOut()}
                  >
                    <LogOut className="w-4 h-4 mr-2" />
                    Sign Out
                  </Button>
                </>
              ) : (
                <Button
                  className="w-full"
                  onClick={() => setAuthOpen(true)}
                >
                  <User className="w-4 h-4 mr-2" />
                  Sign In / Create Account
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Language Settings */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Globe className="w-5 h-5" />
                {t('settings.language')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Select value={language} onValueChange={(value) => setLanguage(value as Language)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {languageOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </CardContent>
          </Card>

          {/* App Settings */}
          <Card>
            <CardHeader>
              <CardTitle>{t('settings.appSettings')}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Dark Mode Toggle */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Moon className="w-5 h-5 text-muted-foreground" />
                  <span>{t('settings.darkMode')}</span>
                </div>
                {mounted && (
                  <Switch
                    checked={theme === 'dark'}
                    onCheckedChange={(checked) => setTheme(checked ? 'dark' : 'light')}
                  />
                )}
              </div>

              <Separator />

              {/* Notification Settings */}
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <Bell className="w-5 h-5 text-muted-foreground" />
                  <span className="font-medium">{t('settings.notifications')}</span>
                </div>

                <div className="ml-8 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm">{t('settings.eventReminders')}</p>
                      <p className="text-xs text-muted-foreground">{t('settings.eventRemindersDesc')}</p>
                    </div>
                    <Switch
                      checked={preferences.notifications.eventReminders}
                      onCheckedChange={(checked) => updateNotifications({ eventReminders: checked })}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm">{t('settings.newEventsInArea')}</p>
                      <p className="text-xs text-muted-foreground">{t('settings.newEventsInAreaDesc')}</p>
                    </div>
                    <Switch
                      checked={preferences.notifications.newEventsInArea}
                      onCheckedChange={(checked) => updateNotifications({ newEventsInArea: checked })}
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Search Defaults */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Search className="w-5 h-5" />
                {t('settings.searchDefaults')}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Default Location */}
              <div className="space-y-2">
                <label className="text-sm font-medium">{t('settings.defaultLocation')}</label>
                <Input
                  placeholder={t('settings.defaultLocationPlaceholder')}
                  value={preferences.searchDefaults.defaultLocation}
                  onChange={(e) => updateSearchDefaults({ defaultLocation: e.target.value })}
                />
              </div>

              {/* Default Radius */}
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  {t('settings.defaultRadius')}: {preferences.searchDefaults.defaultRadius} km
                </label>
                <Slider
                  value={[preferences.searchDefaults.defaultRadius]}
                  onValueChange={(value) => updateSearchDefaults({ defaultRadius: value[0] })}
                  max={100}
                  min={1}
                  step={1}
                />
              </div>

              {/* Default Search Mode */}
              <div className="space-y-2">
                <label className="text-sm font-medium">{t('settings.defaultSearchMode')}</label>
                <Select
                  value={preferences.searchDefaults.defaultSearchMode}
                  onValueChange={(value) => updateSearchDefaults({ defaultSearchMode: value as 'standard' | 'discover' })}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="standard">{t('search.standard')}</SelectItem>
                    <SelectItem value="discover">{t('search.discover')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* About */}
          <Card>
            <CardHeader>
              <CardTitle>{t('settings.about')}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Version</span>
                <span>1.0.0</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Build</span>
                <span>Next.js 14</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </main>

    <AuthModal open={authOpen} onOpenChange={setAuthOpen} />
    </>
  )
}
