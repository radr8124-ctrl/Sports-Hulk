import { createClient } from '@insforge/sdk'

const baseUrl = import.meta.env.VITE_INSFORGE_URL
const anonKey = import.meta.env.VITE_INSFORGE_ANON_KEY

export const insforgeConfigured = Boolean(baseUrl && anonKey)

export const insforge = insforgeConfigured
  ? createClient({ baseUrl, anonKey })
  : null
