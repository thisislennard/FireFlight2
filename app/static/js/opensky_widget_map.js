document.addEventListener("DOMContentLoaded", function () {
  if (typeof L === "undefined") {
    return;
  }

  L.Icon.Default.imagePath = "/static/lib/leaflet/images/";

  document.querySelectorAll(".opensky-widget-map").forEach(function (mapEl) {
    if (mapEl.dataset.leafletInitialized) {
      return;
    }
    mapEl.dataset.leafletInitialized = "1";

    var dataEl = document.getElementById(mapEl.dataset.mapData);
    var aircraft = dataEl ? JSON.parse(dataEl.textContent) : [];
    var centerLat = parseFloat(mapEl.dataset.centerLat);
    var centerLon = parseFloat(mapEl.dataset.centerLon);

    var map = L.map(mapEl).setView([centerLat, centerLon], 9);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>-Mitwirkende',
    }).addTo(map);

    L.circleMarker([centerLat, centerLon], { radius: 5, color: "#c0392b" })
      .addTo(map)
      .bindPopup("Standort Feuerwehr");

    aircraft.forEach(function (entry) {
      var lines = [
        "<strong>" + (entry.callsign || entry.icao24) + "</strong>",
        entry.origin_country || "",
      ];
      if (entry.altitude_m != null) {
        lines.push("Höhe: " + Math.round(entry.altitude_m) + " m");
      }
      if (entry.velocity_kmh != null) {
        lines.push("Geschw.: " + entry.velocity_kmh + " km/h");
      }
      L.marker([entry.lat, entry.lon]).addTo(map).bindPopup(lines.join("<br>"));
    });
  });
});
