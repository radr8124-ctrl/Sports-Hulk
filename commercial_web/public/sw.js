/* Sports Zenith PWA: explicitly NEVER cache scores, account info, prices or API. */
'use strict'
const CACHE = 'sports-zenith-offline-shell-v1'
const STATIC_OFFLINE = ['/offline.html', '/app-icons/zenith-192.png', '/app-icons/zenith-512.png']
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(STATIC_OFFLINE)).then(() => self.skipWaiting()))
})
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys
    .filter(key => key.startsWith('sports-zenith-offline-shell-') && key !== CACHE)
    .map(key => caches.delete(key)))).then(() => self.clients.claim()))
})
self.addEventListener('fetch', event => {
  const req = event.request
  if (req.method !== 'GET' || req.mode !== 'navigate') return
  const url = new URL(req.url)
  if (url.origin !== self.location.origin || url.pathname.startsWith('/api/')) return
  event.respondWith(fetch(req, {cache: 'no-store'}).catch(async () => {
    const cache = await caches.open(CACHE)
    return await cache.match('/offline.html') || new Response('Sports Zenith is offline.', {
      status: 503, headers: {'content-type': 'text/plain; charset=utf-8', 'cache-control':'no-store'},
    })
  }))
})
