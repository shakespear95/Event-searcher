import { createClient, SupabaseClient } from '@supabase/supabase-js'

let _client: SupabaseClient | null = null

export function getSupabaseClient(): SupabaseClient | null {
  if (_client) return _client
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
  console.log('[Supabase] URL configured:', !!url, url ? url.substring(0, 30) + '...' : 'MISSING')
  console.log('[Supabase] Anon key configured:', !!key, key ? key.substring(0, 20) + '...' : 'MISSING')
  if (!url || !key) {
    console.error('[Supabase] Client NOT initialized - missing env vars')
    return null
  }
  _client = createClient(url, key)
  console.log('[Supabase] Client initialized successfully')
  return _client
}
