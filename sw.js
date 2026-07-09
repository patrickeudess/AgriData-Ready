/* AfriData Ready : service worker.
   Objectif : mises a jour automatiques quand l'utilisateur est en ligne,
   tout en gardant un fonctionnement 100% hors-ligne. */
const CACHE = 'afridata-v2';
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
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('message', event => {
  if (event.data === 'skipWaiting') self.skipWaiting();
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  const sameOrigin = url.origin === self.location.origin;

  // Page (navigation) + index.html + manifest : RESEAU D'ABORD.
  // -> l'utilisateur en ligne recoit toujours la derniere version ;
  //    hors-ligne, on sert la derniere version mise en cache.
  const isShell = req.mode === 'navigate' || url.pathname.endsWith('/index.html') || url.pathname.endsWith('/manifest.webmanifest');
  if (isShell) {
    event.respondWith(
      fetch(req).then(resp => {
        if (resp && resp.status === 200) {
          const copy = resp.clone();
          caches.open(CACHE).then(c => c.put('./index.html', copy)).catch(() => {});
        }
        return resp;
      }).catch(() => caches.match('./index.html').then(c => c || caches.match(req)))
    );
    return;
  }

  // Bibliotheques / assets same-origin : stale-while-revalidate.
  // -> reponse instantanee depuis le cache, mise a jour en arriere-plan.
  if (sameOrigin) {
    event.respondWith(
      caches.match(req).then(cached => {
        const network = fetch(req).then(resp => {
          if (resp && resp.status === 200 && resp.type === 'basic') {
            const copy = resp.clone();
            caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {});
          }
          return resp;
        }).catch(() => cached);
        return cached || network;
      })
    );
  }
});
