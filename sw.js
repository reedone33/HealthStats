/* ============================================================================
   SERVICE WORKER — Health Stats
   ============================================================================
   A service worker is a small script the browser keeps running quietly in the
   background, sitting between the app and the network. It does two jobs here:

     1. Lets the app be installed to your home screen and opened with no
        connection at all.

     2. Decides what comes from the network and what comes from the saved copy.

   THE IMPORTANT BIT — how health.json is treated
   ----------------------------------------------
   The app shell (this page, the icons) is served from the saved copy first,
   because it rarely changes and loading instantly is nice.

   But your DATA is handled the opposite way round: the app always tries the
   network first for health.json, and only falls back to the saved copy if
   you're offline. Without that, you'd publish new health data and the app
   would keep cheerfully showing you last month's numbers with no clue that
   anything was wrong. Stale health data is worse than no health data.

   TO PUBLISH AN UPDATE: change CACHE_VERSION below. That name change is what
   tells every browser to throw away its old copy and fetch everything fresh.
   update.command does this for you automatically.
   ========================================================================== */

const CACHE_VERSION = 'health-20260815-1507';
const SHELL_CACHE = CACHE_VERSION + '-shell';
const DATA_CACHE  = CACHE_VERSION + '-data';

// The files that make up the app itself.
const SHELL = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/icon-512-maskable.png',
  './icons/apple-touch-icon.png',
  './icons/favicon-32.png'
];

// --- Install: save the app shell --------------------------------------------
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(SHELL_CACHE)
      // addAll fails entirely if any single file is missing, which would leave
      // the app uninstallable. Adding them one at a time is more forgiving.
      .then(cache => Promise.all(SHELL.map(url => cache.add(url).catch(() => {}))))
      .then(() => self.skipWaiting())   // take over straight away
  );
});

// --- Activate: throw away caches from older versions ------------------------
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(names => Promise.all(
        names.filter(n => !n.startsWith(CACHE_VERSION))
             .map(n => caches.delete(n))
      ))
      .then(() => self.clients.claim())
  );
});

// --- Fetch: decide where each request is answered from ----------------------
self.addEventListener('fetch', event => {
  const req = event.request;
  if(req.method !== 'GET') return;          // never interfere with anything else

  const url = new URL(req.url);

  // YOUR DATA — network first, saved copy only as a fallback.
  if(url.pathname.endsWith('health.json')){
    event.respondWith(
      fetch(req)
        .then(res => {
          // Keep a copy so the app still opens on a plane.
          const copy = res.clone();
          caches.open(DATA_CACHE).then(c => c.put(req, copy));
          return res;
        })
        .catch(() => caches.match(req))     // offline: last known data
    );
    return;
  }

  // CHART.JS from the CDN — saved copy first, since it never changes.
  if(url.hostname === 'cdn.jsdelivr.net'){
    event.respondWith(
      caches.match(req).then(hit => hit || fetch(req).then(res => {
        const copy = res.clone();
        caches.open(SHELL_CACHE).then(c => c.put(req, copy));
        return res;
      }))
    );
    return;
  }

  // THE PAGE ITSELF — network first, saved copy as fallback.
  //
  // This started out cache-first, which caused a nasty failure: publishing a
  // new index.html alongside a new health.json meant the browser could pair
  // the OLD page with the NEW data. The old code didn't understand the new
  // file and fell over with a confusing error.
  //
  // Fetching the page from the network first keeps the two in step. The page
  // is only about 40 KB, so the cost is negligible, and the saved copy still
  // covers you when there's no connection.
  if(req.mode === 'navigate' || url.pathname.endsWith('.html') || url.pathname.endsWith('/')){
    event.respondWith(
      fetch(req)
        .then(res => {
          const copy = res.clone();
          caches.open(SHELL_CACHE).then(c => c.put(req, copy));
          return res;
        })
        .catch(() => caches.match(req).then(hit => hit || caches.match('./index.html')))
    );
    return;
  }

  // EVERYTHING ELSE (icons, manifest) — saved copy first, network as backup.
  // These genuinely don't change between updates.
  event.respondWith(
    caches.match(req).then(hit => hit || fetch(req).catch(() => caches.match('./index.html')))
  );
});
