// 离线缓存：网络再差也能秒开上次看过的数据
const SHELL = 'lhb-shell-v1';
const DATA = 'lhb-data-v1';
const SHELL_FILES = ['./', 'manifest.webmanifest', 'icon-192.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(SHELL_FILES)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== SHELL && k !== DATA).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return; // 直连东财不经过这里
  if (url.pathname.endsWith('/data/index.json')) e.respondWith(networkFirst(e.request, 4000));
  else if (url.pathname.includes('/data/')) e.respondWith(cacheFirst(e.request));
  else e.respondWith(staleWhileRevalidate(e.request));
});

// 日期列表：优先网络，4 秒没回就先用缓存
async function networkFirst(req, ms) {
  const cache = await caches.open(DATA);
  const net = fetch(req).then(r => {
    if (r.ok) cache.put(req, r.clone());
    return r;
  });
  const first = await Promise.race([net.catch(() => null), new Promise(res => setTimeout(res, ms))]);
  if (first) return first;
  return (await cache.match(req)) || net;
}

// 每日数据：URL 带版本号，命中即用；新版本进来时删掉同一天的旧版本
async function cacheFirst(req) {
  const cache = await caches.open(DATA);
  const hit = await cache.match(req);
  if (hit) return hit;
  const r = await fetch(req);
  if (r.ok) {
    const path = new URL(req.url).pathname;
    for (const k of await cache.keys()) {
      if (new URL(k.url).pathname === path && k.url !== req.url) cache.delete(k);
    }
    cache.put(req, r.clone());
  }
  return r;
}

// 页面本身：先给缓存，后台更新，下次打开生效
async function staleWhileRevalidate(req) {
  const cache = await caches.open(SHELL);
  const hit = await cache.match(req, { ignoreSearch: true });
  const net = fetch(req)
    .then(r => {
      if (r.ok) cache.put(req, r.clone());
      return r;
    })
    .catch(() => null);
  return hit || (await net) || new Response('离线，且没有缓存', { status: 503 });
}
