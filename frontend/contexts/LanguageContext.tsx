"use client"

import React, { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react'
import { Language, TranslationStrings } from '@/types'

// Translation data for all supported languages
const translations: Record<Language, TranslationStrings> = {
  en: {
    search: {
      title: "What's UP",
      location: 'Location',
      locationPlaceholder: 'Enter city or address...',
      radius: 'Radius',
      categories: 'Categories',
      allCategories: 'All Categories',
      timePeriod: 'Time Period',
      budget: 'Budget',
      filters: 'Filters',
      searchButton: 'Search Events',
      showResults: 'Show Previous Results',
      discover: 'Discover',
      standard: 'Standard',
    },
    event: {
      details: 'Details',
      date: 'Date',
      time: 'Time',
      price: 'Price',
      free: 'Free',
      tickets: 'Tickets',
      location: 'Location',
      category: 'Category',
      save: 'Save',
      saved: 'Saved',
      share: 'Share',
      directions: 'Directions',
      calendar: 'Calendar',
      oclock: '',
    },
    common: {
      loading: 'Loading...',
      error: 'An error occurred',
      noResults: 'No events found',
      retry: 'Retry',
      cancel: 'Cancel',
      apply: 'Apply',
      reset: 'Reset',
      all: 'All Dates',
      today: 'Today',
      tomorrow: 'Tomorrow',
      thisWeek: 'This Week',
      thisWeekend: 'This Weekend',
      nextWeek: 'Next Week',
      nextMonth: 'Next Month',
      custom: 'Custom Date Range',
    },
    settings: {
      title: 'Settings',
      language: 'Language',
      darkMode: 'Dark Mode',
      notifications: 'Notifications',
      appSettings: 'App Settings',
      eventReminders: 'Event Reminders',
      eventRemindersDesc: 'Get notified before saved events start',
      newEventsInArea: 'New Events in Your Area',
      newEventsInAreaDesc: 'Get notified when new events match your interests',
      searchDefaults: 'Search Defaults',
      defaultLocation: 'Default Location',
      defaultLocationPlaceholder: 'Enter your default city...',
      defaultRadius: 'Default Radius',
      defaultSearchMode: 'Default Search Mode',
      about: 'About',
    },
  },
  de: {
    search: {
      title: "What's UP",
      location: 'Standort',
      locationPlaceholder: 'Stadt oder Adresse eingeben...',
      radius: 'Radius',
      categories: 'Kategorien',
      allCategories: 'Alle Kategorien',
      timePeriod: 'Zeitraum',
      budget: 'Budget',
      filters: 'Filter',
      searchButton: 'Events suchen',
      showResults: 'Bisherige Ergebnisse anzeigen',
      discover: 'Entdecken',
      standard: 'Standard',
    },
    event: {
      details: 'Details',
      date: 'Datum',
      time: 'Uhrzeit',
      price: 'Preis',
      free: 'Kostenlos',
      tickets: 'Tickets',
      location: 'Ort',
      category: 'Kategorie',
      save: 'Speichern',
      saved: 'Gespeichert',
      share: 'Teilen',
      directions: 'Route',
      calendar: 'Kalender',
      oclock: 'Uhr',
    },
    common: {
      loading: 'Laden...',
      error: 'Ein Fehler ist aufgetreten',
      noResults: 'Keine Events gefunden',
      retry: 'Erneut versuchen',
      cancel: 'Abbrechen',
      apply: 'Anwenden',
      reset: 'Zurücksetzen',
      all: 'Alle Termine',
      today: 'Heute',
      tomorrow: 'Morgen',
      thisWeek: 'Diese Woche',
      thisWeekend: 'Dieses Wochenende',
      nextWeek: 'Nächste Woche',
      nextMonth: 'Nächsten Monat',
      custom: 'Eigener Zeitraum',
    },
    settings: {
      title: 'Einstellungen',
      language: 'Sprache',
      darkMode: 'Dunkelmodus',
      notifications: 'Benachrichtigungen',
      appSettings: 'App-Einstellungen',
      eventReminders: 'Event-Erinnerungen',
      eventRemindersDesc: 'Benachrichtigung vor gespeicherten Events',
      newEventsInArea: 'Neue Events in deiner Nähe',
      newEventsInAreaDesc: 'Benachrichtigung bei neuen passenden Events',
      searchDefaults: 'Sucheinstellungen',
      defaultLocation: 'Standardstandort',
      defaultLocationPlaceholder: 'Standardstadt eingeben...',
      defaultRadius: 'Standardradius',
      defaultSearchMode: 'Standard-Suchmodus',
      about: 'Über',
    },
  },
  fr: {
    search: {
      title: "What's UP",
      location: 'Lieu',
      locationPlaceholder: 'Entrez une ville ou une adresse...',
      radius: 'Rayon',
      categories: 'Catégories',
      allCategories: 'Toutes les catégories',
      timePeriod: 'Période',
      budget: 'Budget',
      filters: 'Filtres',
      searchButton: 'Rechercher des événements',
      showResults: 'Afficher les résultats précédents',
      discover: 'Découvrir',
      standard: 'Standard',
    },
    event: {
      details: 'Détails',
      date: 'Date',
      time: 'Heure',
      price: 'Prix',
      free: 'Gratuit',
      tickets: 'Billets',
      location: 'Lieu',
      category: 'Catégorie',
      save: 'Sauvegarder',
      saved: 'Sauvegardé',
      share: 'Partager',
      directions: 'Itinéraire',
      calendar: 'Calendrier',
      oclock: 'h',
    },
    common: {
      loading: 'Chargement...',
      error: 'Une erreur est survenue',
      noResults: 'Aucun événement trouvé',
      retry: 'Réessayer',
      cancel: 'Annuler',
      apply: 'Appliquer',
      reset: 'Réinitialiser',
      all: 'Toutes les dates',
      today: "Aujourd'hui",
      tomorrow: 'Demain',
      thisWeek: 'Cette semaine',
      thisWeekend: 'Ce week-end',
      nextWeek: 'Semaine prochaine',
      nextMonth: 'Mois prochain',
      custom: 'Période personnalisée',
    },
    settings: {
      title: 'Paramètres',
      language: 'Langue',
      darkMode: 'Mode sombre',
      notifications: 'Notifications',
      appSettings: 'Paramètres de l\'application',
      eventReminders: 'Rappels d\'événements',
      eventRemindersDesc: 'Être notifié avant les événements sauvegardés',
      newEventsInArea: 'Nouveaux événements près de chez vous',
      newEventsInAreaDesc: 'Être notifié des nouveaux événements correspondants',
      searchDefaults: 'Recherche par défaut',
      defaultLocation: 'Lieu par défaut',
      defaultLocationPlaceholder: 'Entrez votre ville par défaut...',
      defaultRadius: 'Rayon par défaut',
      defaultSearchMode: 'Mode de recherche par défaut',
      about: 'À propos',
    },
  },
  es: {
    search: {
      title: "What's UP",
      location: 'Ubicación',
      locationPlaceholder: 'Ingrese ciudad o dirección...',
      radius: 'Radio',
      categories: 'Categorías',
      allCategories: 'Todas las categorías',
      timePeriod: 'Período',
      budget: 'Presupuesto',
      filters: 'Filtros',
      searchButton: 'Buscar eventos',
      showResults: 'Mostrar resultados anteriores',
      discover: 'Descubrir',
      standard: 'Estándar',
    },
    event: {
      details: 'Detalles',
      date: 'Fecha',
      time: 'Hora',
      price: 'Precio',
      free: 'Gratis',
      tickets: 'Entradas',
      location: 'Ubicación',
      category: 'Categoría',
      save: 'Guardar',
      saved: 'Guardado',
      share: 'Compartir',
      directions: 'Direcciones',
      calendar: 'Calendario',
      oclock: '',
    },
    common: {
      loading: 'Cargando...',
      error: 'Ha ocurrido un error',
      noResults: 'No se encontraron eventos',
      retry: 'Reintentar',
      cancel: 'Cancelar',
      apply: 'Aplicar',
      reset: 'Restablecer',
      all: 'Todas las fechas',
      today: 'Hoy',
      tomorrow: 'Mañana',
      thisWeek: 'Esta semana',
      thisWeekend: 'Este fin de semana',
      nextWeek: 'Próxima semana',
      nextMonth: 'Próximo mes',
      custom: 'Rango personalizado',
    },
    settings: {
      title: 'Configuración',
      language: 'Idioma',
      darkMode: 'Modo oscuro',
      notifications: 'Notificaciones',
      appSettings: 'Ajustes de la aplicación',
      eventReminders: 'Recordatorios de eventos',
      eventRemindersDesc: 'Recibe notificaciones antes de tus eventos guardados',
      newEventsInArea: 'Nuevos eventos en tu zona',
      newEventsInAreaDesc: 'Recibe notificaciones de nuevos eventos relevantes',
      searchDefaults: 'Búsqueda predeterminada',
      defaultLocation: 'Ubicación predeterminada',
      defaultLocationPlaceholder: 'Ingrese su ciudad predeterminada...',
      defaultRadius: 'Radio predeterminado',
      defaultSearchMode: 'Modo de búsqueda predeterminado',
      about: 'Acerca de',
    },
  },
}

interface LanguageContextType {
  language: Language
  setLanguage: (lang: Language) => void
  t: (key: string) => string
  translations: TranslationStrings
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined)

interface LanguageProviderProps {
  children: ReactNode
  defaultLanguage?: Language
}

export function LanguageProvider({ children, defaultLanguage = 'en' }: LanguageProviderProps) {
  const [language, setLanguageState] = useState<Language>(defaultLanguage)

  // Restore saved language from localStorage on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('preferred-language') as Language | null
      if (saved && ['en', 'de', 'fr', 'es'].includes(saved)) {
        setLanguageState(saved)
      }
    }
  }, [])

  const setLanguage = useCallback((lang: Language) => {
    setLanguageState(lang)
    if (typeof window !== 'undefined') {
      localStorage.setItem('preferred-language', lang)
    }
  }, [])

  // Helper function to get nested translation by dot notation key
  const t = useCallback(
    (key: string): string => {
      const keys = key.split('.')
      let result: unknown = translations[language]

      for (const k of keys) {
        if (result && typeof result === 'object' && k in result) {
          result = (result as Record<string, unknown>)[k]
        } else {
          return key // Return key if translation not found
        }
      }

      return typeof result === 'string' ? result : key
    },
    [language]
  )

  const value = {
    language,
    setLanguage,
    t,
    translations: translations[language],
  }

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

export function useLanguage() {
  const context = useContext(LanguageContext)
  if (context === undefined) {
    throw new Error('useLanguage must be used within a LanguageProvider')
  }
  return context
}
