/* Zenith website + iOS/Android network-safety gate.
   When network drops, hide old odds and scores rather than present stale
   information as current. Never persist user data or cache API responses. */
;(() => {
  const native = Boolean(window.Capacitor?.isNativePlatform?.())
  const gateId = 'sports-zenith-connection-gate'
  let existingState = null
  let checking = false

  const tell = (message) => {
    const el = document.getElementById(gateId + '-status')
    if (el) el.textContent = message
  }

  const showOffline = () => {
    if (typeof document === 'undefined') return
    const root = document.getElementById('root')
    if (!root || !document.body) return
    if (!existingState) {
      existingState = {
        oldVisibility: root.style.visibility,
        oldAriaHidden: root.getAttribute('aria-hidden'),
      }
    }
    root.style.visibility = 'hidden'
    root.setAttribute('aria-hidden', 'true')
    if (document.getElementById(gateId)) return
    const overlay = document.createElement('div')
    overlay.id = gateId
    overlay.setAttribute('role', 'alertdialog')
    overlay.setAttribute('aria-modal', 'true')
    overlay.setAttribute('aria-label', 'Connection lost')
    overlay.style.cssText = 'position:fixed;inset:0;z-index:2147483647;display:flex;align-items:center;justify-content:center;background:#f6f8fb;color:#071a2b;padding:22px;font-family:system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;'
    overlay.innerHTML = `<div style="max-width:400px;width:100%;padding:30px 24px;border-radius:24px;border:1px solid #e2e8f0;background:white;box-shadow:0 15px 35px rgba(7,26,43,.08);text-align:center">
      <div style="font-weight:900;font-size:14px;letter-spacing:.12em;color:#087cc1">SPORTS ZENITH</div>
      <h1 style="font-size:25px;line-height:1.2;margin:18px 0 10px">Connection lost</h1>
      <p style="font-size:15px;line-height:1.6;color:#475569">Live scores, sportsbook prices and predictions are hidden while you're offline so old information isn't mistaken for current results.</p>
      <p id="${gateId}-status" role="status" style="font-size:13px;color:#64748b;margin:16px 0">Connect to the internet to refresh Sports Zenith.</p>
      <button id="${gateId}-retry" type="button" style="width:100%;min-height:48px;border:0;border-radius:12px;background:#087cc1;color:white;font-size:15px;font-weight:700;cursor:pointer">Retry connection</button>
    </div>`
    document.body.appendChild(overlay)
    overlay.querySelector('button')?.addEventListener('click', recover)
    overlay.querySelector('button')?.focus()
  }

  // Do not reveal a stale in-memory React screen merely because the browser
  // reports "online". Require a real, uncached Zenith API health response and
  // reload to fetch fresh market/score data and restore the app's state.
  const recover = async () => {
    if (checking || !document.getElementById(gateId)) return
    checking = true
    tell('Checking live connection…')
    try {
      const response = await window.fetch('/api/health', {
        cache: 'no-store',
        signal: typeof AbortSignal !== 'undefined' && AbortSignal.timeout
          ? AbortSignal.timeout(7000) : undefined,
      })
      if (!response.ok) throw new Error('HEALTH_NOT_OK')
      const body = await response.json()
      if (body?.status !== 'ok' || !body.sources) throw new Error('HEALTH_NOT_ZENITH')
      window.location.reload()
    } catch {
      tell('Still offline. Reconnect, then tap Retry connection.')
    } finally {
      checking = false
    }
  }

  const start = () => {
    if (typeof document !== 'undefined') {
      window.addEventListener('offline', showOffline)
      window.addEventListener('online', () => { void recover() })
      if (navigator.onLine === false) showOffline()
    }
    if (native) return
    const protocol = window.location.protocol
    const host = window.location.hostname
    const secure = protocol === 'https:' ||
      (protocol === 'http:' && (host === 'localhost' || host === '127.0.0.1'))
    if (!secure || !('serviceWorker' in navigator)) return
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sw.js', {scope: '/'})
        .catch(() => { /* Optional PWA install; never affect the live dashboard. */ })
    }, {once: true})
  }

  if (typeof document === 'undefined' || document.readyState !== 'loading') start()
  else document.addEventListener('DOMContentLoaded', start, {once: true})
})()
