"use client"

import React, { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react'

export interface UserPreferences {
  notifications: {
    eventReminders: boolean
    newEventsInArea: boolean
  }
  searchDefaults: {
    defaultLocation: string
    defaultRadius: number
    defaultSearchMode: 'standard' | 'discover'
  }
}

const defaultPreferences: UserPreferences = {
  notifications: {
    eventReminders: true,
    newEventsInArea: false,
  },
  searchDefaults: {
    defaultLocation: '',
    defaultRadius: 25,
    defaultSearchMode: 'standard',
  },
}

interface UserPreferencesContextType {
  preferences: UserPreferences
  updateNotifications: (updates: Partial<UserPreferences['notifications']>) => void
  updateSearchDefaults: (updates: Partial<UserPreferences['searchDefaults']>) => void
}

const UserPreferencesContext = createContext<UserPreferencesContextType | undefined>(undefined)

const STORAGE_KEY = 'user-preferences'

function loadPreferences(): UserPreferences {
  if (typeof window === 'undefined') return defaultPreferences
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      return {
        notifications: { ...defaultPreferences.notifications, ...parsed.notifications },
        searchDefaults: { ...defaultPreferences.searchDefaults, ...parsed.searchDefaults },
      }
    }
  } catch {}
  return defaultPreferences
}

function savePreferences(prefs: UserPreferences) {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs))
  } catch {}
}

export function UserPreferencesProvider({ children }: { children: ReactNode }) {
  const [preferences, setPreferences] = useState<UserPreferences>(defaultPreferences)

  useEffect(() => {
    setPreferences(loadPreferences())
  }, [])

  const updateNotifications = useCallback((updates: Partial<UserPreferences['notifications']>) => {
    setPreferences(prev => {
      const next = {
        ...prev,
        notifications: { ...prev.notifications, ...updates },
      }
      savePreferences(next)
      return next
    })
  }, [])

  const updateSearchDefaults = useCallback((updates: Partial<UserPreferences['searchDefaults']>) => {
    setPreferences(prev => {
      const next = {
        ...prev,
        searchDefaults: { ...prev.searchDefaults, ...updates },
      }
      savePreferences(next)
      return next
    })
  }, [])

  return (
    <UserPreferencesContext.Provider value={{ preferences, updateNotifications, updateSearchDefaults }}>
      {children}
    </UserPreferencesContext.Provider>
  )
}

export function useUserPreferences() {
  const context = useContext(UserPreferencesContext)
  if (context === undefined) {
    throw new Error('useUserPreferences must be used within a UserPreferencesProvider')
  }
  return context
}
