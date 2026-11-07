/* Harbor PWA service worker — app shell + safe network rules */
var CACHE = "harbor-shell-v9";
var SHELL = [
  "/",
  "/offline",
  "/static/offline.html",
  "/static/shop.css?v=75",
  "/static/harbor-ui.css?v=34",
  "/static/harbor-icon-192.png",
  "/static/harbor-icon-512.png",
  "/static/harbor-icon-maskable-192.png",
  "/static/harbor-icon-maskable-512.png",
  "/static/harbor-apple-touch-180.png",
  "/manifest.webmanifest"
];

function sameOrigin(url) {
  return url.origin === self.location.origin;
}

function isBypass(url, request) {
  var path = url.pathname;
  if (!sameOrigin(url)) return true;
  if (request.method !== "GET") return true;
  // Never intercept payments / PayPal / mutating admin APIs
  if (
    path.indexOf("/checkout") === 0 ||
    path.indexOf("/payment") === 0 ||
    path.indexOf("/orders/") === 0 && path.indexOf("/paypal") !== -1 ||
    path.indexOf("/paypal") !== -1 ||
    path.indexOf("/webhooks/") === 0 ||
    path.indexOf("/admin/") === 0 ||
    path.indexOf("/api/") === 0 ||
    path.indexOf("/lp/") === 0
  ) {
    return true;
  }
  return false;
}

function isShellAsset(url) {
  var path = url.pathname;
  if (path.indexOf("/static/") !== 0) return false;
  // product/catalog images stay network / browser cache
  if (path.indexOf("/static/catalog/") === 0 || path.indexOf("/static/products/") === 0) return false;
  return true;
}

function isNavigation(request) {
  return request.mode === "navigate" ||
    (request.destination === "document") ||
    (request.headers.get("accept") || "").indexOf("text/html") !== -1;
}

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(CACHE).then(function (cache) {
      return cache.addAll(SHELL);
    }).then(function () {
      return self.skipWaiting();
    }).catch(function () {
      return self.skipWaiting();
    })
  );
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (key) {
        return key.indexOf("harbor-") === 0 && key !== CACHE;
      }).map(function (key) {
        return caches.delete(key);
      }));
    }).then(function () {
      return self.clients.claim();
    })
  );
});

self.addEventListener("message", function (event) {
  if (event.data && event.data.type === "SKIP_WAITING") {
    self.skipWaiting();
  }
});

self.addEventListener("fetch", function (event) {
  var request = event.request;
  var url;
  try {
    url = new URL(request.url);
  } catch (err) {
    return;
  }

  if (isBypass(url, request)) {
    return;
  }

  // HTML navigations: network-first, offline fallback
  if (isNavigation(request) && sameOrigin(url)) {
    event.respondWith(
      fetch(request).then(function (response) {
        var copy = response.clone();
        if (response.ok && url.pathname === "/") {
          caches.open(CACHE).then(function (cache) {
            cache.put("/", copy);
          });
        }
        return response;
      }).catch(function () {
        return caches.match(request).then(function (hit) {
          return hit || caches.match("/offline") || caches.match("/static/offline.html");
        });
      })
    );
    return;
  }

  // Versioned /static shell assets: cache-first
  if (isShellAsset(url)) {
    event.respondWith(
      caches.open(CACHE).then(function (cache) {
        return cache.match(request).then(function (hit) {
          var fetchPromise = fetch(request).then(function (response) {
            if (response && response.ok) {
              cache.put(request, response.clone());
            }
            return response;
          }).catch(function () {
            return hit;
          });
          return hit || fetchPromise;
        });
      })
    );
    return;
  }

  // Same-origin JSON-ish / other GETs that are not payment: network-first with soft cache
  if (sameOrigin(url) && request.method === "GET") {
    event.respondWith(
      fetch(request).then(function (response) {
        return response;
      }).catch(function () {
        return caches.match(request);
      })
    );
  }
});
