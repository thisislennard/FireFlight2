document.addEventListener("DOMContentLoaded", function () {
  var mapEl = document.getElementById("incidents-map");
  if (!mapEl || typeof L === "undefined") {
    return;
  }

  // Leaflet ermittelt den Bildpfad normalerweise automatisch aus der Script-URL, das ist aber nicht
  // in jedem Ladekontext zuverlässig -- deshalb explizit gesetzt (Bilder liegen neben leaflet.js).
  L.Icon.Default.imagePath = "/static/lib/leaflet/images/";

  var dataEl = document.getElementById("incidents-map-data");
  var markers = dataEl ? JSON.parse(dataEl.textContent) : [];

  var map = L.map(mapEl);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>-Mitwirkende',
  }).addTo(map);

  var bounds = [];
  markers.forEach(function (entry) {
    [
      { point: entry.start, label: "Start" },
      { point: entry.end, label: "Ende" },
    ].forEach(function (part) {
      if (!part.point) {
        return;
      }
      var marker = L.marker([part.point.lat, part.point.lon]).addTo(map);
      var lines = [
        "<strong>" + entry.incident_title + "</strong> (" + (entry.kind === "einsatz" ? "Einsatz" : "Übung") + ")",
        part.label + (entry.started_at ? " – " + new Date(entry.started_at).toLocaleString("de-DE") : ""),
      ];
      if (entry.pilot) {
        lines.push("Pilot: " + entry.pilot);
      }
      if (entry.camera_operator) {
        lines.push("Kamera: " + entry.camera_operator);
      }
      lines.push('<a href="' + entry.detail_url + '">Details</a>');
      marker.bindPopup(lines.join("<br>"));
      bounds.push([part.point.lat, part.point.lon]);
    });
  });

  if (bounds.length > 0) {
    map.fitBounds(bounds, { padding: [30, 30] });
  } else {
    // Rhein-Main als Fallback-Mittelpunkt (Region Feuerwehr Liederbach), falls noch keine Flüge
    // mit Standort erfasst sind.
    map.setView([50.08, 8.45], 10);
  }
});
