/// <reference lib="webworker" />
import { precacheAndRoute, cleanupOutdatedCaches } from "workbox-precaching";
import { registerRoute } from "workbox-routing";
import { CacheFirst, NetworkFirst, StaleWhileRevalidate } from "workbox-strategies";
import { ExpirationPlugin } from "workbox-expiration";
import { clientsClaim } from "workbox-core";

declare let self: ServiceWorkerGlobalScope;

// ── Precache build assets ─────────────────────────────────────────────────────
precacheAndRoute(self.__WB_MANIFEST);
cleanupOutdatedCaches();

// ── Skip waiting & claim clients ──────────────────────────────────────────────
self.skipWaiting();
clientsClaim();

// ── Cache-first: static assets ────────────────────────────────────────────────
registerRoute(
  ({ request }) => request.destination === "style" || request.destination === "script" || request.destination === "worker",
  new CacheFirst({
    cacheName: "zentro-static-v1",
    plugins: [
      new ExpirationPlugin({ maxEntries: 60, maxAgeSeconds: 60 * 60 * 24 * 30 }),
    ],
  })
);

// ── Cache-first: images ───────────────────────────────────────────────────────
registerRoute(
  ({ request }) => request.destination === "image",
  new CacheFirst({
    cacheName: "zentro-images-v1",
    plugins: [
      new ExpirationPlugin({ maxEntries: 80, maxAgeSeconds: 60 * 60 * 24 * 30 }),
    ],
  })
);

// ── Cache-first: Google Fonts ─────────────────────────────────────────────────
registerRoute(
  ({ url }) => url.origin === "https://fonts.googleapis.com" || url.origin === "https://fonts.gstatic.com",
  new CacheFirst({
    cacheName: "zentro-fonts-v1",
    plugins: [
      new ExpirationPlugin({ maxEntries: 10, maxAgeSeconds: 60 * 60 * 24 * 365 }),
    ],
  })
);

// ── Network-first: public API (merchant profiles, menus, etc.) ────────────────
registerRoute(
  ({ url }) => {
    const path = url.pathname;
    return (
      path.startsWith("/api/loyalty/merchant/") &&
      !path.includes("/wallet") &&
      !path.includes("/transfer") &&
      !path.includes("/card-design")
    );
  },
  new NetworkFirst({
    cacheName: "zentro-public-api-v1",
    networkTimeoutSeconds: 5,
    plugins: [
      new ExpirationPlugin({ maxEntries: 30, maxAgeSeconds: 60 * 60 }),
    ],
  })
);

// ── NEVER cache private routes ────────────────────────────────────────────────
// JWT tokens, wallet balances, transactions, orders, transfers, auth endpoints
// are explicitly excluded from all caching strategies above by route matching.

// ── Navigation fallback → offline page ────────────────────────────────────────
registerRoute(
  ({ request }) => request.mode === "navigate",
  new NetworkFirst({
    cacheName: "zentro-navigations-v1",
    networkTimeoutSeconds: 3,
    plugins: [
      new ExpirationPlugin({ maxEntries: 10 }),
    ],
  })
);

// ── Push events ───────────────────────────────────────────────────────────────
self.addEventListener("push", (event) => {
  if (!event.data) return;

  let payload: { title: string; body: string; icon?: string; badge?: string; url?: string; data?: any };

  try {
    payload = event.data.json();
  } catch {
    payload = { title: "Zentro", body: event.data.text() };
  }

  const options: NotificationOptions & { vibrate?: number[]; renotify?: boolean } = {
    body: payload.body,
    icon: payload.icon || "/icons/pwa-192x192.png",
    badge: payload.badge || "/icons/pwa-192x192.png",
    data: payload.data || { url: payload.url || "/" },
    vibrate: [100, 50, 100],
    tag: "zentro-notification",
    renotify: true,
  };

  event.waitUntil(
    self.registration.showNotification(payload.title || "Zentro", options)
  );
});

// ── Notification click events ─────────────────────────────────────────────────
self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const targetUrl = event.notification.data?.url || "/";
  const query = targetUrl.includes("?") ? targetUrl : `${targetUrl}?source=notification`;

  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      // Focus existing window if open
      for (const client of clients) {
        if ("focus" in client) {
          client.navigate(query);
          return client.focus();
        }
      }
      // Open new window
      return self.clients.openWindow(query);
    })
  );
});

// ── Service worker update ─────────────────────────────────────────────────────
self.addEventListener("message", (event) => {
  if (event.data?.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});
