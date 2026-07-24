// Service Worker fuer Web-Push (Phase 4, Notifications-Kern) UND die Büro-PWA-Installierbarkeit
// (offene Frage aus dem Restrukturierungsplan, nachgezogen nach Phase 15). Wird unter zwei Pfaden
// ausgeliefert: /static/js/sw.js (Standard-Scope, historisch) und /sw.js (Root-Scope, app/__init__.py:
// service_worker() -- der Pfad der REQUEST-URL bestimmt den Scope). Neue Registrierungen (app/static/
// js/pwa.js, app/static/js/notifications.js) nutzen /sw.js, damit ein Nutzer die Desktop-Oberfläche
// als installierbare PWA nutzen kann.

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
