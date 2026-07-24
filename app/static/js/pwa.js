// Registriert den Büro-PWA-Service-Worker proaktiv auf jeder Seite (nicht erst beim Klick auf
// "Push aktivieren" wie bisher nur auf /notifications/settings) -- eine installierbare PWA
// braucht laut Chrome-Installierbarkeitskriterien eine aktive Service-Worker-Registrierung, die
// den Manifest-`start_url` abdeckt, bevor der Browser den Installieren-Dialog anbietet.
document.addEventListener("DOMContentLoaded", function () {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(function () {
      // Installierbarkeit ist ein Komfortmerkmal -- ein fehlgeschlagenes Register (z. B. kein
      // HTTPS in einer lokalen Testumgebung) darf die Desktop-Oberfläche nicht beeinträchtigen.
    });
  }
});
