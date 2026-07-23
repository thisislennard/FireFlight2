# FireFlight2

Zentrale Arbeits-, Informations- und Dokumentationsplattform für den Drohneneinsatz einer Feuerwehr.

Dies ist die von Grund auf neu gebaute Ausbaustufe 1 (in Ausbaustufe 2 erweitert): ein sauberer,
stabiler und erweiterbarer Anwendungskern (Auth, Rollen/Berechtigungen, rollenbasierte Dashboards,
Modul-Registry). Externe Integrationen (z. B. DJI FlightHub 2) sind aktuell bewusst **nicht**
enthalten — der Fokus liegt zunächst auf einer sauberen Kern-Basis, siehe [`docs/roadmap.md`](docs/roadmap.md).
Vollständige fachliche Module (Einsatzverwaltung, Flugbuch, Geräteverwaltung, …) sind ebenfalls noch
nicht enthalten.

## Architekturübersicht

FireFlight2 ist ein **modularer Monolith**: eine Flask-Anwendung, ein gemeinsamer Kern, klar getrennte
interne Bereiche, eine gemeinsame PostgreSQL-Datenbank. Schichtung: Routes → Services → Repositories/ORM
→ SQLAlchemy → PostgreSQL. Spätere Fachmodule docken über ein internes Modul-Registry-System an
(`app/modules/`), ohne den Kern umzubauen.

Vollständige Architektur-/Design-Vorgabe und Entscheidungen: [`docs/spec-struktur.md`](docs/spec-struktur.md),
[`docs/spec-design.md`](docs/spec-design.md), [`docs/architecture.md`](docs/architecture.md).

## Projektstruktur

```text
FireFlight2/
├── app/
│   ├── __init__.py          # Flask Application Factory
│   ├── config.py            # Dev-/Test-/Prod-Konfiguration
│   ├── extensions.py        # SQLAlchemy, Migrate, Login, CSRF, Limiter
│   ├── cli.py                # flask init-fireflight
│   ├── core/                 # Basis-Mixins, Security (PIN/Berechtigungen), Exceptions, Zeitzone
│   ├── auth/                  # User-Modell, Login/Logout, PIN-Hashing
│   ├── roles/                  # Role/Permission-Modelle, Standardrollen, Rollenauswahl/-wechsel
│   ├── organizations/           # Organization-Modell (Single-Tenant in Ausbaustufe 1)
│   ├── dashboards/                # Dashboard/Widget-Modelle, Widget-Registry
│   ├── modules/                    # FireFlightModule-Basisklasse + Registry für spätere Fachmodule
│   ├── administration/               # Benutzer-/Rollen-/Dashboard-/Org-/Audit-Verwaltung
│   ├── audit/                         # Audit-Log-Modell + Service
│   ├── templates/, static/             # Jinja2-Templates, CSS-Design-System, HTMX, Archivo-Font
├── migrations/                # Alembic-Migrationen (Flask-Migrate)
├── tests/                      # pytest-Suite
├── docker/entrypoint.sh         # Wartet auf DB, führt Migrationen aus, startet Gunicorn
├── Dockerfile, docker-compose.yml
├── docs/                          # spec-struktur.md, spec-design.md, roadmap.md, architecture.md
└── run.py
```

## Voraussetzungen

**Für den Docker-Betrieb** (empfohlener Weg, siehe unten):
- Docker, Docker Compose

**Für lokale Entwicklung ohne Docker:**
- Python 3.12
- PostgreSQL 16+
- Abhängigkeiten aus `requirements-dev.txt`

## Start mit Docker Compose

```bash
cp .env.example .env
# .env anpassen: SECRET_KEY, POSTGRES_PASSWORD, FIREFLIGHT_ADMIN_PIN
docker compose up -d --build
docker compose exec fireflight2-app flask init-fireflight
```

Die App ist danach unter `http://localhost:8000` erreichbar. `docker/entrypoint.sh` wartet beim
Start automatisch auf die Datenbank und führt `flask db upgrade` aus — Migrationen müssen nicht
manuell angestoßen werden. Nur die Ersteinrichtung (`init-fireflight`) läuft einmalig manuell.

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

## Migrationen

Schemaänderungen werden über Flask-Migrate/Alembic verwaltet:

```bash
flask db migrate -m "kurze Beschreibung"
flask db upgrade
```

Die initiale Migration (`migrations/versions/aef813582552_initial_schema.py`) legt alle 13 Tabellen
aus dem Datenmodell an (siehe `docs/spec-struktur.md` Abschnitt 14).

## Tests

```bash
# Testdatenbank einmalig anlegen (Postgres, da UUID/JSONB-Spalten kein SQLite unterstützen)
createdb -O fireflight2 fireflight2_test

$env:TEST_DATABASE_URL = "postgresql://fireflight2:fireflight2-local@localhost:5432/fireflight2_test"
pytest
```

Deckt u. a. ab: Login-Erfolg/-Fehlschlag, deaktivierte Konten, Konto-Sperre (inkl. progressiver
Eskalation), PIN-Wechsel, Rollenauswahl/-wechsel, Berechtigungsprüfung, Rollen-/Berechtigungs-Verwaltung,
Schutz des letzten Administrators, Dashboard-Erstellung, Widget-Verwaltung, Modul-Registry-Bootstrap,
Idempotenz von `init-fireflight`, Audit-Log-Einträge.

## Umgebungsvariablen

| Variable | Bedeutung |
|---|---|
| `FLASK_ENV` | `development` / `testing` / `production` |
| `SECRET_KEY` | Flask-Session-/CSRF-Secret — in Produktion zwingend zufällig setzen |
| `DATABASE_URL` | PostgreSQL-Verbindungsstring |
| `TIMEZONE` | Anzeige-Zeitzone, Standard `Europe/Berlin` |
| `SESSION_COOKIE_SECURE` | `true` für HTTPS-Betrieb (Standard), `false` nur für lokales HTTP |
| `FIREFLIGHT_ADMIN_USERNAME` / `_EMAIL` / `_PIN` | Für `flask init-fireflight`: erster Administrator, `_PIN` ist die 4-stellige Login-PIN |

## Standardrollen

Bei `flask init-fireflight` werden acht Rollen angelegt (Dokumentation, Einheitsführer, Pilot/Kamera,
Flugleiter, Einsatzleiter/SBI, Gerätewart, TEL-ELW, Administrator) — als Datenbankdatensätze, nicht
hart im Code, über die Administrationsoberfläche änderbar. Die Administrator-Rolle ist eine
Systemrolle: erhält automatisch alle Berechtigungen, kann nicht deaktiviert werden, der letzte aktive
Administrator kann nicht entfernt/deaktiviert werden.

## Berechtigungssystem

Granulares Permission-System (`dashboard.view`, `users.edit`, `roles.assign_permissions`, …, siehe
`app/roles/defaults.py`), geprüft über den `@permission_required(...)`-Decorator **und** zusätzlich
in Services über `ensure_permission(...)` (`app/core/security/permissions.py`) — nie nur clientseitig
über ausgeblendete Buttons.

## Modulsystem

`app/modules/base.py` definiert die `FireFlightModule`-Basisklasse, `app/modules/registry.py` die
`ModuleRegistry`. Spätere Fachmodule registrieren darüber eigene Blueprints, Berechtigungen, Widgets
und Navigationseinträge, ohne den Kern zu verändern. In Ausbaustufe 1 ist noch kein konkretes
Fachmodul registriert.

## Dashboard-System

Jede Rolle hat ein eigenes, datenbankbasiertes Dashboard (`app/dashboards/`) aus Widgets in einem
12-Spalten-Raster. Acht Basiswidgets stehen zur Verfügung (Überschrift, Informationstext,
Schnellzugriff, Statusanzeige, Kennzahl, Hinweis, Warnung, Platzhalter). Administratoren bearbeiten
Dashboards beliebiger Rollen unter „Administration → Rollen → Bearbeiten“.

## Backup

Ein Datenbank-Backup über die Admin-Oberfläche ist in Ausbaustufe 1 nicht enthalten. Bis dahin
Standard-PostgreSQL-Werkzeuge verwenden:

```bash
pg_dump -Fc -h localhost -U fireflight2 fireflight2 > fireflight2-backup.dump
pg_restore -h localhost -U fireflight2 -d fireflight2 --clean fireflight2-backup.dump
```

Bei Docker-Betrieb liegen die Daten im benannten Volume `fireflight2-db-data`.

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
