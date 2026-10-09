/* Mobile-only backend URL bridge. The existing website remains same-origin.
   Only trusted Zenith /api paths and published JSON feeds may cross to
   a configured HTTPS Zenith origin inside a packaged native WebView. */
const ROOT_SNAPSHOT = /^\/[a-zA-Z0-9_-]+\.json(?:[?#].*)?$/
const API_PATH = /^\/api(?:\/|[?#]|$)/
const BRIDGE_STATE = Symbol.for('sports-zenith.native.verified-api-bridge')

export function normalizeZenithApiOrigin(input) {
  if (typeof input !== 'string' || !input.trim()) return null
  let parsed
  try { parsed = new URL(input) } catch { return null }
  if (parsed.protocol !== 'https:' || parsed.username || parsed.password ||
      parsed.pathname !== '/' || parsed.search || parsed.hash ||
      !parsed.hostname.includes('.') || parsed.hostname === 'localhost' ||
      /^\d{1,3}(?:\.\d{1,3}){3}$/.test(parsed.hostname)) return null
  return parsed.origin
}

export function nativeZenithUrl(input, origin) {
  if (typeof input !== 'string' || !origin) return input
  if (!input.startsWith('/') || input.startsWith('//') ||
      input === '/manifest.json' || input.startsWith('/manifest.json?') ||
      input.includes('/../') || input.includes('/./') ||
      !(API_PATH.test(input) || ROOT_SNAPSHOT.test(input))) return input
  return origin + input
}

export function createZenithNativeFetch(originalFetch, origin, native = false) {
  if (!native) return originalFetch
  const checked = normalizeZenithApiOrigin(origin)
  if (!checked) throw new Error('Sports Zenith mobile requires a verified HTTPS API origin.')
  return function zenithNativeFetch(input, options) {
    let result = input
    if (typeof input === 'string') {
      result = nativeZenithUrl(input, checked)
    } else if (typeof Request !== 'undefined' && input instanceof Request) {
      const local = typeof location !== 'undefined' ? location.origin : 'capacitor://localhost'
      if (input.url.startsWith(local + '/')) {
        const relative = input.url.slice(local.length)
        const routed = nativeZenithUrl(relative, checked)
        if (routed !== relative) result = new Request(routed, input)
      }
    }
    return originalFetch(result, options)
  }
}

export function installZenithNativeApiBridge() {
  if (typeof window === 'undefined') return false
  if (!window.Capacitor?.isNativePlatform?.()) return false
  const origin = import.meta.env.VITE_MOBILE_API_ORIGIN
  if (!normalizeZenithApiOrigin(origin)) {
    throw new Error('Verified Sports Zenith HTTPS server address is required for native apps.')
  }
  if (window[BRIDGE_STATE]) return true
  window.fetch = createZenithNativeFetch(window.fetch.bind(window), origin, true)
  window[BRIDGE_STATE] = origin
  return true
}
