const CACHE = 'zynara-v1';
const ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/img/album-cover.jpg',
  '/static/img/placeholder.svg',
  '/static/manifest.json'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  // Always fetch audio and API calls from network
  if (e.request.url.includes('/api/') || e.request.url.includes('/static/songs/')) {
    e.respondWith(fetch(e.request));
    return;
  }
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
});
