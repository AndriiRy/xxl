// Офлайн-кэш: после первой загрузки приложение работает без интернета.
const V='xxl-v10082121';
const FILES=['./','./xxl.html','./manifest.webmanifest','./icon-180.png','./icon-192.png','./icon-512.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(V).then(c=>c.addAll(FILES)));self.skipWaiting()});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V).map(k=>caches.delete(k)))));self.clients.claim()});
self.addEventListener('fetch',e=>{
 const u=new URL(e.request.url);
 if(e.request.method!=='GET'||u.pathname.startsWith('/api/'))return;
 // сначала сеть (чтобы получать обновления), без сети — из кэша
 e.respondWith(fetch(e.request).then(r=>{if(r.ok&&u.origin===location.origin){const c=r.clone();caches.open(V).then(ca=>ca.put(e.request,c))}return r})
  .catch(()=>caches.match(e.request,{ignoreSearch:true}).then(r=>r||caches.match('./xxl.html'))));
});
