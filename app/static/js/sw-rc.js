// Service Worker fuer den RC-PWA-Zugang (app/rc/), unter /rc/sw.js ausgeliefert (app/rc/routes.py:
// service_worker()) -- der Pfad der Request-URL bestimmt den Scope, daher Scope automatisch "/rc/".
// Inhaltlich aktuell identisch zu /static/js/sw.js (Phase 4/5-Spike); eigene Datei statt Wieder-
// verwendung, weil Push-Darstellung/-Routing fuer den RC-Kiosk-Kontext (Phase 11) absehbar abweicht.

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
  const url = (event.notification.data && event.notification.data.url) || "/rc/home";
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
