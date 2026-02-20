"use client"

import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Loader2 } from 'lucide-react'

interface AuthModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

function GoogleIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>
  )
}


export function AuthModal({ open, onOpenChange }: AuthModalProps) {
  const { signIn, signUp, signInWithOAuth } = useAuth()
  const [mode, setMode] = useState<'signin' | 'signup'>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [oauthLoading, setOauthLoading] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const resetForm = () => {
    setEmail('')
    setPassword('')
    setDisplayName('')
    setError(null)
    setSuccess(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    setLoading(true)
    console.log(`[AuthModal] Submit: mode=${mode}, email=${email}`)

    try {
      if (mode === 'signup') {
        const { error } = await signUp(email, password, displayName)
        console.log('[AuthModal] signUp response:', { error })
        if (error) {
          setError(error)
        } else {
          setSuccess('Account created! Check your email to confirm, then sign in.')
          setMode('signin')
        }
      } else {
        const { error } = await signIn(email, password)
        console.log('[AuthModal] signIn response:', { error })
        if (error) {
          setError(error)
        } else {
          onOpenChange(false)
          resetForm()
        }
      }
    } catch (err) {
      console.error('[AuthModal] Unexpected error:', err)
      setError(err instanceof Error ? err.message : 'Unexpected error')
    } finally {
      setLoading(false)
    }
  }

  const handleOAuth = async (provider: 'google') => {
    setError(null)
    setOauthLoading(provider)
    const { error } = await signInWithOAuth(provider)
    if (error) {
      setError(error)
      setOauthLoading(null)
    }
    // On success, user is redirected to OAuth provider
  }

  const switchMode = () => {
    setMode(mode === 'signin' ? 'signup' : 'signin')
    setError(null)
    setSuccess(null)
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { onOpenChange(v); if (!v) resetForm() }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>
            {mode === 'signin' ? 'Sign In' : 'Create Account'}
          </DialogTitle>
          <DialogDescription>
            {mode === 'signin'
              ? 'Sign in to save favorites and track search history.'
              : 'Create an account to get started.'}
          </DialogDescription>
        </DialogHeader>

        {/* OAuth Buttons */}
        <div className="space-y-3">
          <Button
            type="button"
            variant="outline"
            className="w-full"
            disabled={!!oauthLoading}
            onClick={() => handleOAuth('google')}
          >
            {oauthLoading === 'google' ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <GoogleIcon className="w-4 h-4 mr-2" />
            )}
            Continue with Google
          </Button>

        </div>

        {/* Divider */}
        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-background px-2 text-muted-foreground">or</span>
          </div>
        </div>

        {/* Email/Password Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === 'signup' && (
            <div className="space-y-2">
              <label className="text-sm font-medium">Display Name</label>
              <Input
                type="text"
                placeholder="Your name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
              />
            </div>
          )}

          <div className="space-y-2">
            <label className="text-sm font-medium">Email</label>
            <Input
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Password</label>
            <Input
              type="password"
              placeholder="Min. 6 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
            />
          </div>

          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}

          {success && (
            <p className="text-sm text-green-600 dark:text-green-400">{success}</p>
          )}

          <Button type="submit" className="w-full" disabled={loading}>
            {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            {mode === 'signin' ? 'Sign In' : 'Create Account'}
          </Button>

          <p className="text-center text-sm text-muted-foreground">
            {mode === 'signin' ? "Don't have an account? " : 'Already have an account? '}
            <button
              type="button"
              onClick={switchMode}
              className="text-primary hover:underline font-medium"
            >
              {mode === 'signin' ? 'Sign Up' : 'Sign In'}
            </button>
          </p>
        </form>
      </DialogContent>
    </Dialog>
  )
}
