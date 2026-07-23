document.addEventListener("DOMContentLoaded", function () {
  if (typeof L === "undefined") {
    return;
  }

  // Leaflet ermittelt den Bildpfad normalerweise automatisch aus der Script-URL, das ist aber nicht
  // in jedem Ladekontext zuverlässig -- deshalb explizit gesetzt (Bilder liegen neben leaflet.js).
  L.Icon.Default.imagePath = "/static/lib/leaflet/images/";

  document.querySelectorAll(".incidents-widget-map").forEach(function (mapEl) {
    if (mapEl.dataset.leafletInitialized) {
      return;
    }
    mapEl.dataset.leafletInitialized = "1";

    var dataEl = document.getElementById(mapEl.dataset.mapData);
    var markers = dataEl ? JSON.parse(dataEl.textContent) : [];

    var map = L.map(mapEl);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>-Mitwirkende',
    }).addTo(map);

    var bounds = [];
    markers.forEach(function (entry) {
      var point = entry.start || entry.end;
      if (!point) {
        return;
      }
      var lines = [
        "<strong>" + entry.incident_title + "</strong> (" + (entry.kind === "einsatz" ? "Einsatz" : "Übung") + ")",
      ];
      if (entry.pilot) {
        lines.push("Pilot: " + entry.pilot);
      }
      lines.push('<a href="' + entry.detail_url + '">Details</a>');
      L.marker([point.lat, point.lon]).addTo(map).bindPopup(lines.join("<br>"));
      bounds.push([point.lat, point.lon]);
    });

    if (bounds.length > 0) {
      map.fitBounds(bounds, { padding: [20, 20] });
    } else {
      // Rhein-Main als Fallback-Mittelpunkt (Region Feuerwehr Liederbach).
      map.setView([50.08, 8.45], 10);
    }
  });
});
