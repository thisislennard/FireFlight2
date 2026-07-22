# FireFlight2 – Roadmap

Lebendes Dokument: hält fest, was aus `docs/spec-struktur.md` (Ausbaustufe 1) bereits umgesetzt und
live verifiziert ist, was in dieser Session noch aussteht, und was bewusst auf später verschoben wurde.
Bei jeder neuen Session zuerst hier nachsehen, bevor an einem der Punkte weitergearbeitet wird.

## Status: Ausbaustufe 1 (spec-struktur.md)

### Fertig und live verifiziert (lokal, venv + PostgreSQL 18 via scoop, DB `fireflight2`/`fireflight2_test`)
- **Projektgrundlage**: Ordnerstruktur, `requirements.txt`, `.env.example`, `.gitignore`, `.dockerignore`
- **Docker**: `Dockerfile` (non-root, Gunicorn), `docker-compose.yml` (App+DB, Healthchecks), `docker/entrypoint.sh` (wartet auf DB, führt Migrationen aus) — **nicht** mit echtem `docker compose up` getestet, da auf dieser Maschine kein Docker installiert ist. Struktur folgt Standardmustern, sollte aber beim ersten echten Docker-Lauf gegengeprüft werden
- **Flask Application Factory** (`app/__init__.py`), Config (`app/config.py`, Dev/Test/Prod), Extensions (`app/extensions.py`: SQLAlchemy, Migrate, Login, CSRF, Limiter)
- **Datenmodell** (alle 13 Tabellen aus spec-struktur.md Abschnitt 14, per `flask db migrate` erzeugt und per `flask db upgrade` angewendet): `organizations`, `users`, `roles`, `permissions`, `user_roles`, `role_permissions`, `dashboards`, `dashboard_widgets`, `system_settings`, `audit_logs`, `integration_configs`, `integration_sync_runs`, `external_references`
- **Auth**: Login/Logout, PBKDF2/scrypt-Hashing (Werkzeug), Session-Fixation-Schutz (`session.clear()` vor Login), CSRF (Flask-WTF, global), Rate-Limiting (Flask-Limiter, 10/min auf Login), Konto-Sperre nach 5 Fehlversuchen (15 Min), Open-Redirect-Schutz — **live getestet**: Login-Erfolg, falsches Passwort, Redirect-Kette
- **Rollen & Berechtigungen**: 8 Standardrollen + 21 Berechtigungen geseedet, Rollenauswahl-Seite mit Auto-Skip bei genau einer Rolle (Systemeinstellung), Rollenwechsel per Kopfzeilen-Dropdown (HTMX + `HX-Redirect`), granulares Permission-System (`permission_required`-Decorator + `ensure_permission` für Services), Schutz des letzten Administrators — **live getestet**: Login als Admin und als rechtearme Testrolle, 403 bei fehlender Berechtigung bestätigt
- **Dashboards**: Widget-Registry mit 9 Basiswidgets, Admin-Editor (Hinzufügen/Entfernen/Titel/Größe), rollenspezifisches Dashboard mit 12-Spalten-Raster — **live getestet**: Widget per POST hinzugefügt, erscheint nach Reload
- **Modul-Registry-System**: `FireFlightModule`-Basisklasse + `ModuleRegistry`, noch ohne konkrete Fachmodule (bewusst, s. u.)
- **DJI-FlightHub-Integration (Grundstruktur)**: abstrakte `DJIFlightHubClient`-Basisklasse, `MockDJIFlightHubClient` mit Testdaten, Sync-Service inkl. `ExternalReference`-Upsert, Admin-Statusseite mit Historie — **live getestet**: simulierte Synchronisierung erzeugt echten `IntegrationSyncRun`, 2 Mock-Geräte verarbeitet
- **Administration**: Benutzer (Liste/Anlegen/Bearbeiten/Rollen zuweisen/Deaktivieren), Rollen (Liste/Anlegen/Bearbeiten/Berechtigungen/Deaktivieren), Dashboard-Editor pro Rolle, Organisation, Audit-Log mit Filter+Pagination — **live getestet**: alle Seiten liefern 200 als Admin
- **CLI `flask init-fireflight`**: Organisation, Rollen/Berechtigungen, Dashboards, erster Administrator — **live getestet**: zweimal hintereinander ausgeführt, keine Duplikate (Idempotenz bestätigt)
- **Templates + Design-System**: Basis-Layout (Sidebar 220px/Bottom-Tab-Bar <760px), alle Administrationsseiten, Fehlerseiten (403/404/500), CSS-Tokens 1:1 aus `docs/spec-design.md`, Archivo-Font + HTMX lokal vendored (kein CDN)
- **Security-Header**: CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy (`app/__init__.py: _security_headers`)

### Für diese Session noch offen
- [x] **Tests (pytest)**: `tests/conftest.py` + `test_auth.py`, `test_roles.py`, `test_dashboards.py`, `test_init.py`, `test_dji_integration.py`, `test_audit.py` — 22/22 grün gegen `fireflight2_test`
- [x] **README.md** (Projektbeschreibung, Architektur, Setup, Docker-Start, Migrationen, Tests, Env-Variablen, Standardrollen, Berechtigungssystem, Modulsystem, Dashboard-System, DJI-Integrationsarchitektur, Backup, Update, Reverse-Proxy-Betrieb — spec-struktur.md Abschnitt 24)
- [x] **docs/architecture.md** (Architekturentscheidungen dokumentiert, spec-struktur.md Abschnitt 28)
- [x] `CLAUDE.md` final synchronisiert (Status „Ausbaustufe 1 implementiert", Verweis auf diese Roadmap)
- [ ] Mit Nutzer abstimmen: Commit + ggf. Push nach GitHub (bisher nur lokal auf der Maschine, `git status`/`git add` noch nicht ausgeführt)

## Bewusst nicht in Ausbaustufe 1 (spec-struktur.md Abschnitt 26)
Einsatzverwaltung, vollständiges Flugbuch, Geräteverwaltung, Karten/GIS, Medienstreaming, Live-Telemetrie,
echte DJI-Produktivintegration, Mandantenfähigkeit, Microservices — siehe `CLAUDE.md` „Kernkonzepte".

## Bekannte Lücken / nächste Schritte nach Ausbaustufe 1
- **Echte DJI-FlightHub-2-Anbindung**: `LiveDJIFlightHubClient` implementiert (2026-07-22, nur lesende
  Endpunkte: Systemstatus, Projekte, Geräte, Telemetrie, HMS, Flugaufgaben inkl. Medien/Track, Waylines
  — s. `docs/dji-flighthub2-api.md`), Zugangsdaten über Admin-Formular auf
  `/administration/integrations/dji-flighthub/` pflegbar, DSGVO-Gate wie in v1. **Noch offen:** mit
  echten Zugangsdaten gegen die echte Organisation verifizieren — ein Testlauf mit einem ungültigen
  Test-Key ergab, dass `https://fh.dji.com/openapi/v0.1/system_status` eine HTML-Seite statt JSON
  liefert (Fehlerbehandlung dafür ist vorhanden, aber die Ursache noch nicht geklärt: ungültiger Key
  oder falsche Basis-URL/regionsspezifisches Gateway, wie v1 das teils vermutet hatte) — sobald echte
  Zugangsdaten vorliegen, Base-URL im Formular ggf. auf die per Browser-DevTools ermittelte echte
  API-Basis-URL umstellen. Steuerendpunkte (Task anlegen, Gerätebefehle, Kamera/RTK/Livestream) bewusst
  nicht angebunden.
- **2FA/TOTP**: in spec-struktur.md nicht erwähnt, in v1 vorhanden — Entscheidung mit Nutzer offen
- **Dark-Mode-Farbwerte**: aktuell pragmatisch aus den Neutral-/Accent-Ramps abgeleitet (`app/static/css/app.css`,
  `:root[data-theme="dark"]`), keine vom Nutzer gelieferten exakten Werte — bei Bedarf nachschärfen
- **Passwort-zurücksetzen**: Struktur vorbereitet (`app/auth/services.py: request_password_reset`), aber kein
  Mail-Versand angebunden (kein Mail-Server in Ausbaustufe 1 gefordert)
- **Lucide-Icons**: `Role.icon` wird aktuell nur als Textfeld gespeichert, keine echte Icon-Anzeige — spätere
  Ergänzung z. B. per SVG-Sprite
- **Systemeinstellungen-UI**: `system_settings`-Tabelle + Helper (`app/core/models.py: get_setting/set_setting`)
  existieren, aber keine Admin-Oberfläche zum Bearbeiten (z. B. `skip_role_selection_if_single_role`) — bisher
  nur direkt in der DB änderbar
- **Erste echte Fachmodule** (Reihenfolge mit Nutzer klären): Einsatzverwaltung, Flugbuch, Geräte-/Akkuverwaltung,
  Wartung, Wiki — jeweils als `FireFlightModule`-Unterklasse in `app/modules/` andocken
- **Docker tatsächlich testen**: sobald Docker auf einer Zielmaschine verfügbar ist, `docker compose up -d --build`
  + `docker compose exec fireflight2-app flask init-fireflight` end-to-end durchspielen (in dieser Session nur
  über lokalen venv+PostgreSQL-Pfad verifiziert, s. o.)
- **Multi-Tenancy**: falls später gebraucht, `org_id`-Spalten-Modell (nicht Schema-pro-Org) — Begründung in
  `CLAUDE.md` Tech-Stack-Tabelle
