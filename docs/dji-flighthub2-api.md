# DJI FlightHub 2 OpenAPI — Endpunkt-Referenz

Vollständige Recherche der DJI-FlightHub-2-Business-OpenAPI, Grundlage für die geplante Ablösung von
`MockDJIFlightHubClient` durch eine echte Anbindung (s. `CLAUDE.md`, Verlauf 2026-07-22). Quelle:
Apifox-Doku, Share-Link `https://s.apifox.cn/484eaf38-faef-488e-ad9b-8edffac94406`. Die Seite ist eine
JS-SPA und liefert bei normalem Abruf keinen Inhalt — Zugriff funktioniert über die `llms.txt`-Konvention:
`{share-url}/llms.txt` liefert den vollständigen Link-Index aller Unterseiten (Titel + URL, gruppiert
nach Kategorie), jede Einzelseite ist danach über `{share-url}/api-{id}.md` bzw. `{share-url}/doc-{id}.md`
als Markdown abrufbar. `{share-url}/llms-full.txt` existiert nicht (404) — der Umweg über Link-Index +
Einzelabruf ist nötig.

## Authentifizierung

Bei jedem Request per Header:

| Header | Pflicht | Bedeutung |
|---|---|---|
| `X-User-Token` | ja | Organization Key (JWT), aus FlightHub 2 → Meine Organisation → Einstellungen → FlightHub Sync |
| `X-Project-Uuid` | ja | Projekt-UUID, aus `data.list.uuid` der Projektliste (`GET /project`) |
| `X-Request-Id` | ja | neue UUID **pro Request** |
| `X-Language` | ja | `zh` oder `en` |

Base-URL: `https://fh.dji.com` + Pfad (Cloud) bzw. `http://<IP>:30812` (On-Premises) — wie in v1
(`FireFlight/backend/modules/flighthub/service.py`) bereits verwendet. Alle Pfade unten ohne den
gemeinsamen Prefix `/openapi/v0.1`.

## Organisation & Projekte

| Methode + Pfad | Zweck |
|---|---|
| `GET /project` | Projektliste der Organisation (Name, UUID, Standort-Mittelpunkt) |
| `GET /project/sts-token` | Temporäre OSS/S3-Upload-Credentials für das Projekt |
| `PUT /project/member` | Personen zum Projekt hinzufügen/aktualisieren |

## Geräte

| Methode + Pfad | Zweck |
|---|---|
| `GET /device` | Geräteliste organisationsweit: Dock+Drohne, Modell, Online-Status, Kameras/Objektive, `mode_code` |
| `GET /project/device` | Dieselbe Geräteliste, aber auf ein Projekt eingeschränkt |
| `GET /device/{sn}/state` | Volle Telemetrie: Akku, GPS, RTK, Storage, Firmware, Netzwerk — Schema variiert je Gerätemodell (Dock 1/2, Matrice-Serie, RC, …) |
| `GET /device/hms` | Health-Management-Alerts: `level` (notification/reminder/warning), `module`, `in_the_key` (on_the_ground/in_the_sky), Code+Nachricht |
| `POST /device/{sn}/command` | Steuerbefehle: `return_home`, `return_specific_home`, `return_home_cancel`, `flighttask_pause`, `flighttask_recovery` |
| `POST /device/control` | Steuerungshoheit für Flug/Payload anfordern (Pflicht vor Kamera-/Objektiv-/Qualitäts-Änderungen) |
| `DELETE /device/control` | Steuerungshoheit abgeben |
| `POST /device/change-camera` | Dock-Kamera indoor/outdoor umschalten |
| `POST /device/change-lens` | Objektiv wechseln (wide/zoom/ir) |
| `PUT /device/stream/quality` | Videoqualität setzen (adaptive/smooth/ultra_high_definition) |
| `POST /device/{sn}/rtk` | Custom-Network-RTK konfigurieren (host/port/account/password/mount_point) |

## Livestream

| Methode + Pfad | Zweck |
|---|---|
| `POST /live-stream/start` | Liefert direkt eine WHEP/WebRTC-Playback-URL zum Einbetten — **implementiert** (2026-07-22, einzige Steuerfunktion in FireFlight2, s. `docs/architecture.md`) |
| `POST /live-stream/converter` | RTMP- oder GB28181-Stream-Weiterleitung an Drittsysteme anlegen |
| `GET /live-stream/converter` | Liste der Weiterleitungen mit Status (running/failed/initialized) |
| `PUT /live-stream/converter/{id}` | Auto-Weiterleitung an/aus |
| `DELETE /live-stream/converter/{id}` | Weiterleitung löschen |

## Flugaufgaben (Kern fürs Flugbuch)

| Methode + Pfad | Zweck |
|---|---|
| `POST /flight-task` | Task anlegen (Wayline, Dock, Zeitplan/Wiederholung, RTH-Verhalten, `min_battery_capacity`) |
| `GET /flight-task/{uuid}` | Status/Details (waiting/executing/success/paused/terminated/…) |
| `GET /flight-task/list` | Liste, Pflichtparameter `sn`+`begin_at`+`end_at`, optional Status-/Typ-Filter |
| `GET /flight-task/{uuid}/media` | Erzeugte Fotos/Videos/PPK mit `preview_url` + `original_url` (Download), bis 10.000 Ressourcen |
| `GET /flight-task/{uuid}/track` | GPS-Trajektorie (`timestamp`/`latitude`/`longitude`/`height`), Gesamtdistanz+dauer |

## Flugrouten (Waylines)

| Methode + Pfad | Zweck |
|---|---|
| `GET /wayline` | Liste (Name, Gerätemodell, `template_types`: waypoint/mapping_2d/3d/facade/solid/mapping_gobject) |
| `GET /wayline/{id}` | Details inkl. `download_url` der Routendatei, Distanz, Punktanzahl |

## Kartenannotation

| Methode + Pfad | Zweck |
|---|---|
| `POST /map/element` | Punkt/Linie/Fläche (GeoJSON-artige Geometrie + Farbe) auf der Karte anlegen |

## 3D-/2D-Modelle (aus Flug-Task-Ordnern)

| Methode + Pfad | Zweck |
|---|---|
| `GET /model` | Liste fertiger Modelle |
| `GET /model/{id}` | Details inkl. Download-/Preview-URL |
| `POST /model/create` | Reconstruction aus `task_folder_id` anstoßen (Qualitätsstufe, Ausgabeformate b3dm/osgb/ply/obj/…) |

## Open Modeling (eigenständiger Foto-Upload → Reconstruction, unabhängig von FlightHub-Flügen)

| Methode + Pfad | Zweck |
|---|---|
| `POST /open_model/stores/obtain_token` | Upload-Credentials für eigene Fotos |
| `POST /open_model/stores/upload_callback` | Upload abschließen (Dateiliste + Etags) |
| `GET /open_model/resource/{uuid}` | Ressourcen-Status (ImportSuccess/WaitingDelete/Deleted) |
| `DELETE /open_model/resource/{uuid}` | Ressource löschen |
| `POST /open_model/models/reconstruction/start` | 2D/3D/3DGS/LiDAR-Reconstruction starten |
| `POST /open_model/models/{uuid}/reconstruction/stop` | Reconstruction stoppen (Bild-Kontingent wird erstattet) |
| `GET /open_model/models/running` | Laufende Reconstructions mit Fortschritt |
| `GET /open_model/models/{uuid}` | Modell-Details/Status |
| `DELETE /open_model/models/{uuid}` | Modell löschen |

## Einordnung für FireFlight2

**Geräte** (inkl. HMS), **Flugaufgaben** (inkl. Media+Track) und **Waylines** sind der direkte Kern
fürs Flugbuch. **Livestream** ist für ELW/Einsatzleitung interessant. **Annotation**, **3D-Modelle**
und **Open Modeling** sind eher Kartierungs-/Lagebild-Funktionen — für die aktuelle Ausbaustufe
nachrangig, s. `docs/roadmap.md`.

Alle Schreib-/Steuerendpunkte (Task anlegen, Gerätebefehle, Kamera/Objektiv/RTK, Livestream/Converter,
Annotation, Modelle) wirken auf echte Hardware bzw. echte Cloud-Ressourcen. Empfehlung: erste
Implementierungsstufe rein lesend (Projekte, Geräte, HMS, Task-Liste+Medien+Track, Waylines) in der
Administration sichtbar machen, bevor Steuerbefehle gebaut werden.

## Bekannter Bezug zu v1

v1 (`FireFlight/backend/modules/flighthub/service.py`) nutzt bereits `X-User-Token` + `X-Project-Uuid`
und genau 3 dieser Endpunkte (`/project` zum Verbindungstest, `/device`, `/flight-record` — Hinweis:
laut dieser Recherche heißt der Flug-Endpunkt aktuell `/flight-task/list`, nicht `/flight-record`; vor
Übernahme in FireFlight2 gegenprüfen, ob sich die API seit v1s Implementierung geändert hat oder v1
einen älteren/anderen Endpunkt-Namen verwendet). v1 setzt bisher **keinen** `X-Request-Id`-Header, der
laut aktueller Doku aber Pflicht ist — bei Portierung von v1-Code beachten.

## `https://fh.dji.com` ist NICHT die API-Basis-URL (2026-07-22 definitiv bestätigt)

Ein echter Verbindungstest gegen `https://fh.dji.com/openapi/v0.1/system_status` lieferte HTML statt
JSON — auch **ohne** jeden Auth-Header, unabhängig vom User-Agent. Response-Header zeigen `Server:
AmazonS3` + `Via: ... CloudFront` — `fh.dji.com` ist ein rein statisches S3/CloudFront-Hosting für die
Vue-Web-Oberfläche, kann also grundsätzlich keine Server-Logik/API ausliefern. Jeder unbekannte Pfad
liefert vermutlich den SPA-Shell-Fallback (`index.html`), daher der HTML-statt-JSON-Fehler.

Im JS-Bundle der Web-Oberfläche (`lib-axios.*.js`) ist die echte API-Basis-URL als Laufzeit-Config
sichtbar: `baseURL = e.baseURL || window.CURRENT_BE_ENV_CONFIG?.server_url`. `CURRENT_BE_ENV_CONFIG`
startet leer (`{zone_id:"", server_url:"", ...}`) und wird erst nach Login durch einen internen
Zonen-/Konfigurationsabruf befüllt (`initConfig(e)` setzt `server_url` aus einem Objekt `e`, dessen
Quelle sich im minifizierten Bundle nicht ohne Weiteres zurückverfolgen ließ) — die echte API-Host ist
also **account-/regionsspezifisch und erst nach Login ermittelbar**, nicht von außen erratbar. Damit
ist die alte, ursprünglich unbestätigte Notiz zu einem regionsspezifischen DJI-Gateway (z. B. etwas wie
`*.djigate.com`) im Kern bestätigt, auch wenn der exakte Hostname nicht öffentlich auffindbar war.

**So findet man die echte Basis-URL:** in FlightHub 2 einloggen (`fh.dji.com`) → Browser-DevTools (F12)
→ Netzwerk-Tab → Filter auf „Fetch/XHR" → eine beliebige Aktion ausführen (z. B. Projekt öffnen oder
Geräteliste ansehen) → bei einem der API-Requests den **Host** aus der Request-URL ablesen (nicht
`fh.dji.com`) → diesen Host als Base-URL im FireFlight2-Formular eintragen.
