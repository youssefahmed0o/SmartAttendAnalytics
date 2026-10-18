self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open('smart-attend-cache').then((cache) => {
      return cache.addAll([
        '/login',
        '/static/css/bootstrap.min.css' // أضف المسارات الأساسية التي تريد حفظها
      ]);
    })
  );
});

self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then((response) => {
      return response || fetch(e.request);
    })
  );
});
