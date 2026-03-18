/**
 * Service Worker - 让游戏支持离线使用（PWA）
 * 第一次打开后，即使没有网络也能继续游玩
 */

const CACHE = 'dailaoer-v1';
const FILES = ['/', '/index.html', '/style.css', '/cards.js', '/gameLogic.js', '/main.js', '/manifest.json'];

// 安装时缓存所有文件
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll(FILES))
  );
  self.skipWaiting();
});

// 激活时清理旧缓存
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// 请求时优先用缓存，缓存没有再走网络
self.addEventListener('fetch', e => {
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
});
