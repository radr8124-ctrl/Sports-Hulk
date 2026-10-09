/* Website install enhancer. Do NOT cache odds, account sessions or scores. */
;(() => {
  if (window.Capacitor?.isNativePlatform?.()) return
  const protocol = window.location.protocol
  const host = window.location.hostname
  const secure = protocol === 'https:' ||
    (protocol === 'http:' && (host === 'localhost' || host === '127.0.0.1'))
  if (!secure || !('serviceWorker' in navigator)) return
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js', {scope: '/'})
      .catch(() => { /* Optional installation; never affect the live sports dashboard. */ })
  }, {once: true})
})()
