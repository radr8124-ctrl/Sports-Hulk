import { createClient } from '@insforge/sdk'

const baseUrl = import.meta.env.VITE_INSFORGE_URL
const anonKey = import.meta.env.VITE_INSFORGE_ANON_KEY

export const insforgeConfigured = Boolean(baseUrl && anonKey)

// The shipped web app uses the same first-party origin for auth.
// The existing Node server proxies only six narrowly approved /api/auth routes
// to InsForge, preserving HttpOnly refresh cookies on sportszenith.com for
// Safari. Local Vite development and non-http native shells use the provider.
const firstPartyAuthOrigin = import.meta.env.PROD && typeof window !== 'undefined' &&
  ['http:', 'https:'].includes(window.location.protocol)
  ? window.location.origin : null

export const insforge = insforgeConfigured
  ? createClient({ baseUrl:firstPartyAuthOrigin || baseUrl, anonKey })
  : null
