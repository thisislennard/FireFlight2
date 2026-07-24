# FireFlight2

Zentrale Arbeits-, Informations- und Dokumentationsplattform für den Drohneneinsatz einer Feuerwehr.

Von Grund auf neu gebaut (kein Fork von v1): ein sauberer, stabiler und erweiterbarer
Anwendungskern (Auth, Rollen/Berechtigungen, rollenbasierte Dashboards, Modul-Registry,
Ausbaustufe 1) **plus** die darauf aufbauenden Fachmodule und die Büro-/RC-PWA-Infrastruktur aus
Ausbaustufe 2: PIN-Login, zwei getrennte PWA-Zugänge (Büro-Web + DJI-RC-Plus-Gerät), ein
admin-konfigurierbares Wizard-System für Preflight/Flugstart/Flugende, Web-Push-Benachrichtigungen,
Einsatz-/Übungsverwaltung mit Flugbuch und Karte, Tickets/Wartungsintervalle, Nutzerprofile mit
Qualifikationen, Drohneneinheiten sowie zwei externe Dashboard-Widgets (DWD-Wetter, OpenSky-Luftraum).
Vollständiger Umsetzungsstand, was noch offen ist und was bewusst verschoben wurde:
[`docs/roadmap.md`](docs/roadmap.md).

Externe Integrationen mit Zustand/Sync (wie die zwischenzeitlich gebaute, dann wieder entfernte
DJI-FlightHub-2-Anbindung) sind aktuell bewusst **nicht** enthalten — nur schreibgeschützte,
nicht organisationsbezogene Direktanbindungen an freie öffentliche APIs (DWD/OpenSky, s. u.).

## Architekturübersicht

FireFlight2 ist ein **modularer Monolith**: eine Flask-Anwendung, ein gemeinsamer Kern, klar getrennte
interne Bereiche, eine gemeinsame PostgreSQL-Datenbank. Schichtung: Routes → Services → Repositories/ORM
→ SQLAlchemy → PostgreSQL. Fachmodule docken über ein internes Modul-Registry-System an
(`app/modules/`, `INSTALLED_MODULES` in `app/modules/installed.py`), ohne den Kern umzubauen — jedes
Modul kann eigene Blueprints, Berechtigungen, Dashboard-Widgets, Navigationseinträge und
Jinja-Template-Globals registrieren (`app/modules/base.py: FireFlightModule`).

Zwei getrennte, unabhängig installierbare PWA-Zugänge: die normale Desktop-/Büro-Oberfläche und ein
eigener Kiosk-Zugang für am DJI-RC-Plus-Controller montierte Geräte (`app/rc/`, eigenes
`manifest-rc.webmanifest` + Service Worker, geräteseitige Kopplung getrennt von der
Bediener-Anmeldung).

Vollständige Architektur-/Design-Vorgabe und Entscheidungen: [`docs/spec-struktur.md`](docs/spec-struktur.md),
[`docs/spec-design.md`](docs/spec-design.md), [`docs/architecture.md`](docs/architecture.md).
Konzeptvorgabe für Ausbaustufe 2: [`fireflight2-konzept-struktur.md`](fireflight2-konzept-struktur.md).

## Projektstruktur

```text
FireFlight2/
├── app/
│   ├── __init__.py            # Flask Application Factory
│   ├── config.py              # Dev-/Test-/Prod-Konfiguration
│   ├── extensions.py          # SQLAlchemy, Migrate, Login, CSRF, Limiter
│   ├── cli.py                 # flask init-fireflight / seed-test-data / notifications / maintenance
│   ├── core/                  # Basis-Mixins, Security (PIN/Berechtigungen), Uploads, Zeitzone, External-Cache
│   ├── auth/                  # User-Modell, Login/Logout, PIN-Hashing, Sperr-Eskalation
│   ├── roles/                 # Role/Permission-Modelle, Standardrollen, Rollenauswahl/-wechsel
│   ├── organizations/         # Organization-Modell (Single-Tenant)
│   ├── dashboards/            # Dashboard/Widget-Modelle, Widget-Registry (Basiswidgets)
│   ├── notifications/         # Web-Push-Kern (PushSubscription/NotificationLog, VAPID)
│   ├── rc/                    # RC-PWA-Zugang: Gerätekopplung, Zwei-Schritt-Login, Preflight/Flugende
│   ├── units/                 # Drohneneinheiten (Unit, Heimateinheit, Manager)
│   ├── profile/                # Self-Service-Nutzerprofil (E-Mail/Telefon/Profilbild)
│   ├── wizards/                 # Generische Wizard-Engine (Step-Typen, Runner) + Admin-CRUD
│   ├── modules/                  # FireFlightModule-Basisklasse + Registry für Fachmodule
│   │   ├── incidents/              # Einsätze/Übungen + Flugbuch mit Karte
│   │   ├── tickets/                 # Tickets + Wartungsintervalle
│   │   ├── weather/                  # DWD-Wetter-Dashboard-Widget (Bright Sky, schlanke Direktanbindung)
│   │   └── opensky/                   # OpenSky-Luftraum-Dashboard-Widget (anonym, schlanke Direktanbindung)
│   ├── administration/            # Benutzer-/Rollen-/Dashboard-/Org-/Audit-/RC-Geräte-/Wizard-/Einheiten-Verwaltung
│   ├── audit/                     # Audit-Log-Modell + Service
│   ├── templates/, static/         # Jinja2-Templates, CSS-Design-System, HTMX, Archivo-Font, Leaflet (vendored)
├── migrations/                # Alembic-Migrationen (Flask-Migrate)
├── tests/                     # pytest-Suite (236 Tests, Stand Ausbaustufe 2 inkl. Büro-PWA-Nachtrag)
├── docker/entrypoint.sh       # Wartet auf DB, führt Migrationen aus, startet Gunicorn
├── Dockerfile, docker-compose.yml
├── docs/                      # spec-struktur.md, spec-design.md, roadmap.md, architecture.md
└── run.py
```

## Voraussetzungen

**Für den Docker-Betrieb** (empfohlener Weg für Produktion, siehe unten):
- Docker, Docker Compose

**Für lokale Entwicklung ohne Docker:**
- Python — `Dockerfile`/Produktion zielen auf 3.12, lokale Entwicklung auf dieser Maschine läuft
  aktuell unter 3.10.11 (kein bekanntes Kompatibilitätsproblem, aber nie explizit auf 3.12 getestet)
- PostgreSQL 16+ (UUID-/JSONB-Spalten, kein SQLite-Support)
- Abhängigkeiten aus `requirements-dev.txt` (inkl. `requirements.txt`)

## Start mit Docker Compose

```bash
cp .env.example .env
# .env anpassen: SECRET_KEY, POSTGRES_PASSWORD, FIREFLIGHT_ADMIN_PIN
# für Push-Benachrichtigungen zusätzlich VAPID_PUBLIC_KEY/VAPID_PRIVATE_KEY setzen (s. u.)
docker compose up -d --build
docker compose exec fireflight2-app flask init-fireflight
```

Die App ist danach unter `http://localhost:8000` erreichbar. `docker/entrypoint.sh` wartet beim
Start automatisch auf die Datenbank und führt `flask db upgrade` aus — Migrationen müssen nicht
manuell angestoßen werden. Nur die Ersteinrichtung (`init-fireflight`) läuft einmalig manuell.
**Docker selbst wurde auf der Entwicklungsmaschine nie getestet** (kein Docker installiert) — vor
dem ersten echten Produktivlauf gegenprüfen.

## Lokale Entwicklung ohne Docker

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt

$env:FLASK_APP = "run.py"
$env:FLASK_ENV = "development"
$env:SECRET_KEY = "dev-secret"
$env:DATABASE_URL = "postgresql://fireflight2:fireflight2-local@localhost:5432/fireflight2"

flask db upgrade
flask init-fireflight
flask run
```

Für Testdaten (Testuser pro Rolle, RC-Testgeräte, Beispiel-Einsatz/-Ticket/-Wizards usw., s. u.)
zusätzlich `flask seed-test-data`. Für Web-Push zusätzlich `flask notifications generate-vapid-keys`
ausführen und die Ausgabe als `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY` setzen — ohne diese Variablen
läuft die App normal weiter, nur der Push-Versand ist deaktiviert.

## Migrationen

Schemaänderungen werden über Flask-Migrate/Alembic verwaltet:

```bash
flask db migrate -m "kurze Beschreibung"
flask db upgrade
```

Aktuellen Stand/Historie prüfen: `flask db current`, `flask db heads`, `flask db history`. Die
initiale Migration (`migrations/versions/aef813582552_initial_schema.py`) legt die 13 Tabellen aus
Ausbaustufe 1 an (`docs/spec-struktur.md` Abschnitt 14); seither kamen über Ausbaustufe 2 weitere
Migrationen für Notifications, RC-Geräte, Drohneneinheiten, Nutzerprofile, Wizards,
Einsätze/Flugbuch, Tickets/Wartung und den RC-Wizard-Flow hinzu (chronologische Liste:
`migrations/versions/`).

## Tests

```bash
# Testdatenbank einmalig anlegen (Postgres, da UUID/JSONB-Spalten kein SQLite unterstützen)
createdb -O fireflight2 fireflight2_test

$env:TEST_DATABASE_URL = "postgresql://fireflight2:fireflight2-local@localhost:5432/fireflight2_test"
pytest
```

236 Tests (Stand Ausbaustufe 2 inkl. Büro-PWA-Nachtrag), u. a.: Login-Erfolg/-Fehlschlag, progressive
Konto-Sperr-Eskalation, PIN-Wechsel/Admin-Unlock, Rollenauswahl/-wechsel inkl. Rollen ohne
Dashboard, Berechtigungsprüfung, Schutz des letzten Administrators, Dashboard-/Widget-Verwaltung,
Modul-Registry-Bootstrap, Web-Push (Subscribe/Unsubscribe/Versand inkl. 404/410-Handling),
RC-Gerätekopplung + Zwei-Schritt-Login + Qualifikationsfilter, Drohneneinheiten, Nutzerprofile
(inkl. Magic-Byte-Bildvalidierung), generische Wizard-Engine + admin-konfigurierte
RC-Wizard-Läufe (Preflight/Flugstart/Genehmigung/Flugende), Einsätze/Flugbuch mit Karte, Tickets +
Wartungsintervalle, die beiden externen Dashboard-Widgets (DWD/OpenSky, mit gemocktem
`requests.get` — **kein** echter Netzwerkzugriff in der automatisierten Suite), Büro-PWA-Manifest/
Service-Worker-Routen, Audit-Log-Einträge, Idempotenz von `init-fireflight`/`seed-test-data`. Externe HTTP-Aufrufe (Push, DWD, OpenSky) werden
in Tests durchgehend gemockt; Live-Verifikation gegen echte Endpunkte läuft separat gegen den
laufenden Dev-Server (Details je Phase in `docs/roadmap.md`).

## Umgebungsvariablen

| Variable | Bedeutung |
|---|---|
| `FLASK_ENV` | `development` / `testing` / `production` |
| `SECRET_KEY` | Flask-Session-/CSRF-Secret — in Produktion zwingend zufällig setzen |
| `DATABASE_URL` | PostgreSQL-Verbindungsstring |
| `TIMEZONE` | Anzeige-Zeitzone, Standard `Europe/Berlin` |
| `SESSION_COOKIE_SECURE` | `true` für HTTPS-Betrieb (Standard), `false` nur für lokales HTTP |
| `FIREFLIGHT_ADMIN_USERNAME` / `_EMAIL` / `_PIN` | Für `flask init-fireflight`: erster Administrator, `_PIN` ist die 4-stellige Login-PIN |
| `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` | Web-Push-Schlüsselpaar, erzeugt per `flask notifications generate-vapid-keys` — ohne diese Werte ist Push-Versand deaktiviert, der Rest der App läuft normal |
| `VAPID_CLAIMS_EMAIL` | Kontakt-E-Mail im Push-VAPID-Claim, Standard `admin@example.org` |

Standort für die beiden externen Dashboard-Widgets (DWD-Wetter/OpenSky) sowie deren Cache-TTLs sind
bewusst **keine** Umgebungsvariablen, sondern feste Konstanten in `app/config.py`
(`WEATHER_LOCATION_LAT/LON`, `OPENSKY_LOCATION_LAT/LON`, `OPENSKY_RADIUS_KM`) — "schlanke
Direktanbindung" ohne Admin-Konfigurationsseite, s. `docs/roadmap.md` Phase 14.

## Standardrollen

Bei `flask init-fireflight` werden acht Rollen angelegt (Dokumentation, Einheitsführer, Pilot/Kamera,
Flugleiter, Einsatzleiter/SBI, Gerätewart, TEL-ELW, Administrator) — als Datenbankdatensätze, nicht
hart im Code, über die Administrationsoberfläche änderbar. Die Administrator-Rolle ist eine
Systemrolle: erhält automatisch alle Berechtigungen, kann nicht deaktiviert werden, der letzte aktive
Administrator kann nicht entfernt/deaktiviert werden. Gerätewart ist die einzige Rolle **ohne**
eigenes Dashboard (`Role.landing_endpoint`, landet stattdessen direkt auf der Ticket-/
Wartungsübersicht) — Rollen können individuell auf ein beliebiges Landing-Ziel statt des Dashboards
gesetzt werden.

## Berechtigungssystem

Granulares Permission-System (`dashboard.view`, `users.edit`, `roles.assign_permissions`, `incidents.view`,
`tickets.manage`, `rc_devices.manage`, `wizards.manage`, `units.manage`, … — Basis-Permissions in
`app/roles/defaults.py`, fachliche Permissions werden von den jeweiligen Modulen selbst über
`FireFlightModule.register_permissions()` ergänzt), geprüft über den `@permission_required(...)`-
Decorator **und** zusätzlich in Services über `ensure_permission(...)`
(`app/core/security/permissions.py`) — nie nur clientseitig über ausgeblendete Buttons. Fachliche
Dashboard-Widgets (Flugbuch-Karte, Ticket-Meldeformular) prüfen ihre Berechtigung zusätzlich selbst
in Python, da Template-Includes den normalen Request-Context-Processor nicht sehen.

## Modulsystem

`app/modules/base.py` definiert die `FireFlightModule`-Basisklasse, `app/modules/registry.py` die
`ModuleRegistry`. Fachmodule registrieren darüber eigene Blueprints, Berechtigungen, Widgets,
Navigationseinträge und Jinja-Template-Globals (für Widget-Daten), ohne den Kern zu verändern —
installierte Module: `app/modules/installed.py`. Aktuell registriert:

- **`incidents`** — Einsätze/Übungen + Flugbuch mit Karte (Leaflet, vendored)
- **`tickets`** — technische Meldungen + Wartungsintervalle (Fälligkeits-Push über `flask maintenance check-due`)
- **`weather`** — DWD-Wetter-Dashboard-Widget (Bright Sky, kein API-Key nötig)
- **`opensky`** — OpenSky-Luftraum-Dashboard-Widget (anonymer Zugriff, Bounding-Box um den konfigurierten Standort)

## Dashboard-System

Jede Rolle hat ein eigenes, datenbankbasiertes Dashboard (`app/dashboards/`) aus Widgets in einem
12-Spalten-Raster. Acht generische Basiswidgets (Überschrift, Informationstext, Schnellzugriff,
Statusanzeige, Kennzahl, Hinweis, Warnung, Platzhalter) plus die vier fachlichen Widgets aus den
oben genannten Modulen (Flugbuch-Karte, Ticket-Meldeformular, DWD-Wetter, OpenSky-Luftraum).
Administratoren bearbeiten Dashboards beliebiger Rollen unter „Administration → Rollen → Bearbeiten“.

## PIN-Login & Kontosperre

Anmeldung über Benutzername + 4-stellige PIN statt Passwort (`app/auth/`, `app/core/security/
passwords.py`: `hash_pin`/`verify_pin`/`is_trivial_pin`-Denylist). Wegen der geringen Kombinatorik
(10.000 mögliche PINs) niedrigerer Sperrschwellwert als bei Passwörtern üblich (3 statt 5
Fehlversuche) und progressive Sperreskalation: 1. Sperre 15 Min., 2. Sperre 60 Min. (verfällt nach
24 h ohne neue Sperre), ab der 3. Sperre `requires_admin_unlock` (kein automatischer Ablauf mehr,
nur per Admin-Aktion aufhebbar). **Bewusst dokumentiertes, ungelöstes Risiko:** ob der Büro-Zugang
hinter einem offenen Internetzugriff oder VPN/interner Netz läuft, ist nicht entschieden — bei
offenem Zugriff bleibt die PIN (10.000 Kombinationen) die einzige Hürde, s. `docs/roadmap.md`.

## Büro-PWA

Die normale Desktop-/Büro-Oberfläche ist als installierbare PWA nutzbar (`app/static/
manifest.webmanifest`, Scope `/`). Root-skopierter Service Worker über die Route `/sw.js`
(`app/__init__.py: service_worker()`, liefert denselben Inhalt wie `/static/js/sw.js` aus, das für
Web-Push aus Phase 4 bereits existierte); `app/static/js/pwa.js` registriert ihn proaktiv auf jeder
Seite, damit Browser den Installieren-Dialog anbieten. Voraussetzung für einen echten
Installieren-Dialog ist HTTPS (oder `localhost`) — die eigentliche Installation in einem echten
Browser hinter einem echten Reverse Proxy ist bisher nicht getestet, s. `docs/roadmap.md`.

## RC-PWA-Zugang

Eigener Kiosk-Zugang für am DJI-RC-Plus-Controller montierte Geräte (`app/rc/`,
`/static/manifest-rc.webmanifest`, `/rc/sw.js`). Geräte-Ebene (langlebiger Cookie, per
Administration → RC-Geräte gekoppelt) getrennt von der Bediener-Ebene (Zwei-Schritt-Login: erst
qualifikationsgefilterte Nutzerliste antippen, dann nur noch PIN eingeben). Nach Login läuft ein
admin-konfigurierter Preflight-Wizard, danach Einbuchen in einen laufenden Einsatz/eine Übung,
Startanfrage mit Genehmigungspflicht (Push an Flugleiter/Einsatzleiter), nach Freigabe Wechsel zu
DJI Pilot 2 (Deep-Link-URL admin-konfigurierbar, standardmäßig leer, da hardwareabhängig), am Ende
ein Flugende-Wizard mit Zwei-Knopf-Abschluss ("Selbe Person, neuer Flug" / "Komplett neu"). Die
tatsächliche Hardware-Verifikation auf der echten DJI RC Plus (PWA-Installation, Hintergrund-Push,
App-Wechsel) steht weiterhin aus, s. `docs/roadmap.md`.

## Wizard-System

Generische, admin-konfigurierbare Wizard-Engine (`app/wizards/`, Administration → Wizards): sechs
Step-Typen (`info`, `checklist`, `confirmation`, `text_input`, `choice`, `location`), serverseitige
Gate-Prüfung vor dem Weiterschalten. Wird sowohl für eine reine Admin-Vorschau als auch für echte
RC-Läufe (Preflight/Flugende, s. o.) genutzt; die optionale `field_key`-Zuordnung eines Schritts
bildet dessen Antwort auf ein Flugbuch-Feld ab (`app/modules/incidents/wizard_fields.py`).

## Web-Push-Benachrichtigungen

`app/notifications/` (VAPID, `pywebpush`): jeder Nutzer kann für sein aktuelles Gerät Push
aktivieren (`/notifications/settings`) und sich selbst eine Testbenachrichtigung schicken. Wird
aktuell für zwei Dinge genutzt: RC-Startanfrage-Genehmigungen (Phase 12) und fällige
Wartungsregeln (`flask maintenance check-due`, für einen externen Cron-Job gedacht — die App hat
keine eingebaute Zeitsteuerung). Ohne `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY` läuft die App normal
weiter, nur der Versand ist deaktiviert.

## Fachmodule

- **Einsätze/Übungen + Flugbuch** (`app/modules/incidents/`): Verwaltung unter „Flugbuch“, Karte
  aller Flüge mit erfasstem Standort (`/incidents/karte`), Logbuch mit Jahres-/Monatsfilter
  (`/incidents/logbuch`). Flüge, die über die RC-PWA laufen, haben einen Status-Workflow
  (`draft` → `pending_approval` → `approved` → `completed`); über Desktop manuell angelegte Flüge
  bleiben ohne diesen Status.
- **Tickets + Wartung** (`app/modules/tickets/`): technische Meldungen inkl. Foto-Anhang
  (Magic-Byte-validiert), Wartungsregeln mit Fälligkeits-/Warnschwelle, abgeleitet aus dem
  jüngsten `MaintenanceEvent` statt einem eigenen Datumsfeld.

## Nutzerprofile & Drohneneinheiten

Jeder Nutzer kann E-Mail/Telefon/Profilbild selbst pflegen (`/profile/`, Magic-Byte-validierter
Bild-Upload). Qualifikationen (Pilot/Kamera-Operator) sind Admin-verwaltet und steuern den
RC-Login-Filter (welche Geräte/Rollen ein Nutzer im Feld sehen/bedienen darf). Drohneneinheiten
(`app/units/`, Administration → Einheiten) bilden eine Heimateinheit je Nutzer plus unabhängig
davon mehrere von einem Nutzer verwaltete Einheiten ab.

## Testdaten

```bash
flask seed-test-data
```

Idempotent, für die lokale Entwicklung/Verifikation gedacht: ein Testuser pro Standardrolle
(`test_<rollenschlüssel>`, PIN `4726`), zwei RC-Testgeräte, drei Testeinheiten mit überlappenden
Managern, ein Beispiel-Wizard, ein Beispiel-Einsatz + eine Beispiel-Übung mit Flügen, ein
Beispiel-Ticket, zwei Wartungsregeln, admin-konfigurierte RC-Preflight-/Flugende-Test-Wizards sowie
die fachlichen Dashboard-Widgets exemplarisch auf zwei Test-Dashboards.

## Backup

Ein Datenbank-Backup über die Admin-Oberfläche ist nicht enthalten. Standard-PostgreSQL-Werkzeuge
verwenden:

```bash
pg_dump -Fc -h localhost -U fireflight2 fireflight2 > fireflight2-backup.dump
pg_restore -h localhost -U fireflight2 -d fireflight2 --clean fireflight2-backup.dump
```

Bei Docker-Betrieb liegen die Datenbank-Daten im benannten Volume `fireflight2-db-data`, hochgeladene
Nutzerinhalte (Profilbilder, Ticket-Fotos) im Volume `fireflight2-uploads-data:/app/instance`
(seit Ausbaustufe 2 Phase 7) — beide Volumes sichern.

## Update-Vorgehen

Code aktualisieren (`git pull`), danach:

```bash
docker compose up -d --build
docker compose exec fireflight2-app flask db upgrade
```

`docker/entrypoint.sh` führt `flask db upgrade` beim Container-Start ohnehin automatisch aus.

## Produktiver Betrieb hinter einem Reverse Proxy

Der App-Container läuft mit Gunicorn auf Port 8000. HTTPS/HTTP2/Zertifikate werden außerhalb der
Anwendung terminiert. Beispiel für Nginx:

```nginx
server {
    listen 443 ssl http2;
    server_name fireflight2.example.org;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

`SESSION_COOKIE_SECURE=true` (Standard) setzt voraus, dass der Proxy tatsächlich HTTPS terminiert.
Für fällige Wartungs-Push-Benachrichtigungen zusätzlich `flask maintenance check-due` per externem
Cron-Job einplanen (die App hat keine eingebaute Zeitsteuerung).
