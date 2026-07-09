/* AfriData Ready : service worker for offline use (100% local, no network needed once cached) */
const CACHE = 'afridata-v1';
const ASSETS = [
  './',
  './index.html',
  './manifest.webmanifest',
  './libs/papaparse.min.js',
  './libs/xlsx.full.min.js',
  './libs/jszip.min.js',
  './libs/FileSaver.min.js',
  './assets/logo_afridata_ready_white.png',
  './assets/icon-192.png',
  './assets/icon-512.png',
  './assets/icon-maskable-512.png',
  './assets/apple-touch-icon.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  // Navigations : renvoyer index.html depuis le cache (app shell), reseau en secours
  if (req.mode === 'navigate') {
    event.respondWith(
      caches.match('./index.html').then(cached => cached || fetch(req).catch(() => caches.match('./index.html')))
    );
    return;
  }
  // Autres ressources : cache d'abord, puis reseau (et mise en cache au passage)
  event.respondWith(
    caches.match(req).then(cached => {
      if (cached) return cached;
      return fetch(req).then(resp => {
        if (resp && resp.status === 200 && resp.type === 'basic') {
          const copy = resp.clone();
          caches.open(CACHE).then(cache => cache.put(req, copy));
        }
        return resp;
      }).catch(() => cached);
    })
  );
});
