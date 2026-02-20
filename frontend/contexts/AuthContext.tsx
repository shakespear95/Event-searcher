"use client"

import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { Session, User, Provider } from '@supabase/supabase-js'
import { getSupabaseClient } from '@/lib/supabase'

interface AuthContextType {
  user: User | null
  session: Session | null
  loading: boolean
  signUp: (email: string, password: string, displayName?: string) => Promise<{ error: string | null }>
  signIn: (email: string, password: string) => Promise<{ error: string | null }>
  signInWithOAuth: (provider: Provider) => Promise<{ error: string | null }>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const client = getSupabaseClient()
    console.log('[Auth] Initializing, client available:', !!client)
    if (!client) {
      console.warn('[Auth] No Supabase client - auth disabled')
      setLoading(false)
      return
    }

    // Get initial session
    client.auth.getSession().then(({ data: { session } }) => {
      console.log('[Auth] Initial session:', session ? `user=${session.user?.email}` : 'none')
      setSession(session)
      setUser(session?.user ?? null)
      setLoading(false)
    }).catch((err) => {
      console.error('[Auth] getSession error:', err)
      setLoading(false)
    })

    // Listen for auth changes
    const { data: { subscription } } = client.auth.onAuthStateChange(
      (event, session) => {
        console.log('[Auth] State change:', event, session ? `user=${session.user?.email}` : 'no session')
        setSession(session)
        setUser(session?.user ?? null)
        setLoading(false)
      }
    )

    return () => subscription.unsubscribe()
  }, [])

  const signUp = useCallback(async (email: string, password: string, displayName?: string) => {
    const client = getSupabaseClient()
    console.log('[Auth] signUp called for:', email)
    if (!client) {
      console.error('[Auth] signUp failed - no Supabase client')
      return { error: 'Auth not configured' }
    }
    const { data, error } = await client.auth.signUp({
      email,
      password,
      options: {
        data: { display_name: displayName || email.split('@')[0] },
      },
    })
    console.log('[Auth] signUp result:', { user: data?.user?.id, session: !!data?.session, error: error?.message })
    if (data?.user && !data?.session) {
      console.log('[Auth] signUp success - email confirmation required')
    }
    return { error: error?.message ?? null }
  }, [])

  const signIn = useCallback(async (email: string, password: string) => {
    const client = getSupabaseClient()
    console.log('[Auth] signIn called for:', email)
    if (!client) {
      console.error('[Auth] signIn failed - no Supabase client')
      return { error: 'Auth not configured' }
    }
    const { data, error } = await client.auth.signInWithPassword({ email, password })
    console.log('[Auth] signIn result:', { user: data?.user?.id, session: !!data?.session, error: error?.message })
    return { error: error?.message ?? null }
  }, [])

  const signInWithOAuth = useCallback(async (provider: Provider) => {
    const client = getSupabaseClient()
    console.log('[Auth] OAuth called for provider:', provider)
    if (!client) {
      console.error('[Auth] OAuth failed - no Supabase client')
      return { error: 'Auth not configured' }
    }
    const redirectTo = typeof window !== 'undefined' ? window.location.origin : undefined
    console.log('[Auth] OAuth redirectTo:', redirectTo)
    const { data, error } = await client.auth.signInWithOAuth({
      provider,
      options: { redirectTo },
    })
    console.log('[Auth] OAuth result:', { url: data?.url, error: error?.message })
    return { error: error?.message ?? null }
  }, [])

  const signOut = useCallback(async () => {
    const client = getSupabaseClient()
    if (client) await client.auth.signOut()
  }, [])

  return (
    <AuthContext.Provider value={{ user, session, loading, signUp, signIn, signInWithOAuth, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
