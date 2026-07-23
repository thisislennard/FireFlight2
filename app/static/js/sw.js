// Minimaler Service Worker fuer den Web-Push-Rundlauftest aus dem normalen Browser (Phase 4,
// Notifications-Kern). Bewusst mit Standard-Scope ("/static/js/") statt Root-Scope registriert --
// die eigentlichen, installierbaren PWA-Service-Worker mit Root-/"/rc/"-Scope (manifest-desktop.
// webmanifest, manifest-rc.webmanifest) sind Restrukturierungsplan-Abschnitt 4, Phasen 5/11.

self.addEventListener("push", (event) => {
  let payload = { title: "FireFlight2", body: "" };
  if (event.data) {
    try {
      payload = event.data.json();
    } catch (err) {
      payload.body = event.data.text();
    }
  }
  event.waitUntil(
    self.registration.showNotification(payload.title || "FireFlight2", {
      body: payload.body || "",
      data: payload.data || {},
      icon: "/static/img/icon-mark.png",
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url === url && "focus" in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(url);
      }
      return undefined;
    })
  );
});
