# FireFlight2 – Roadmap

Lebendes Dokument: hält fest, was aus `docs/spec-struktur.md` (Ausbaustufe 1) bereits umgesetzt und
live verifiziert ist, was in dieser Session noch aussteht, und was bewusst auf später verschoben wurde.
Bei jeder neuen Session zuerst hier nachsehen, bevor an einem der Punkte weitergearbeitet wird.

## Status: Ausbaustufe 2 (fireflight2-konzept-struktur.md)

Erweitert Ausbaustufe 1 um die dort bewusst ausgeklammerten Fachmodule (Einsatz/Übung, Flugbuch,
Wizard-System, Tickets/Wartung, Nutzerprofile, Drohneneinheiten) sowie neue, bisher nicht verankerte
Infrastruktur (PIN-Login, zwei PWA-Zugänge Büro/DJI-RC-Plus, Web-Push). Architektur- und Phasenplan
(15 Phasen) am 2026-07-23 erarbeitet und vom Nutzer freigegeben — Kontext, alle Grundsatzentscheidungen
und die vollständige Phasenreihenfolge stehen im Restrukturierungsplan (nicht Teil des Repos). Zwei
offene Punkte aus der Planung: Deployment-Kontext des Büro-Zugangs (offenes Internet vs. VPN/internes
Netz) noch nicht entschieden — PIN-Sicherheitsrisiko (nur 10.000 Kombinationen) daher weiterhin
ungelöst dokumentiert; der RC-Hardware-Feasibility-Test wird laut Nutzerentscheidung vorgezogen (nicht
erst nach allen Fachmodulen).

### Fertig und live verifiziert
- **Phase 1 — Modul-Registry-Bootstrap**: `app/modules/installed.py` (`INSTALLED_MODULES`-Liste),
  `ModuleRegistry.add_permission()`/`add_widget()`/`reset()`, `app/__init__.py: _register_modules()`
  beim App-Start, `seed_permissions()` merged jetzt `module_registry.permissions`,
  `WidgetDefinition.template`-Feld + Fallback-`{% include %}` in `dashboards/_widget.html` (als echtes
  Jinja-Template-Global registriert, nicht per `context_processor` — Makro-Import ohne `with context`
  sieht sonst keine context_processor-Werte, nur echte Jinja-Globals wie `url_for`). Neue Tests:
  `tests/test_modules.py`, `test_module_widget_with_template_renders_via_fallback_include`
  (`tests/test_dashboards.py`).
- **Phase 2 — Rollen ohne Dashboard**: `Role.landing_endpoint` (Migration `b087a1bfd48f`),
  `_resolve_role_landing()` in `app/roles/routes.py` ersetzt den harten Redirect auf `dashboards.view`,
  neue Seite `roles/no_landing.html` statt rohem 403, Admin-Rollen-Editor bietet Landing-Ziele gefiltert
  auf die Permissions der Rolle an (`ModuleRegistry.navigation` als Quelle für künftige Fachmodul-Ziele).
  Neue Tests in `tests/test_roles.py`.
- **Phase 3 — PIN-Login-Migration**: `User.password_hash` → `pin_hash` (Migration `eb781f84828e`, per
  `flask db upgrade` **gegen die reale lokale Dev-DB verifiziert**, nicht nur `db.create_all()` in
  Tests), neue Felder `must_change_pin`, `pin_set_at`, `lockout_count`, `last_lockout_at`,
  `requires_admin_unlock`. `app/core/security/passwords.py`: `hash_pin`/`verify_pin`/`is_trivial_pin`
  (Denylist trivialer PINs). `LoginForm.pin` (4-Ziffern-Regex), neues `PinChangeForm` +
  `GET/POST /auth/pin/change` (Link im Topbar). Progressive Sperr-Eskalation in
  `app/auth/services.py:_register_failed_attempt` — 1. Sperre 15 Min, 2. Sperre 60 Min (Eskalation
  verfällt nach 24h ohne neue Sperre), ab der 3. Sperre `requires_admin_unlock=True` (kein Ablauf
  mehr, nur per neuer Admin-Aktion `POST /administration/users/<id>/unlock` aufhebbar, Button in
  `user_edit.html`). `LOGIN_MAX_FAILED_ATTEMPTS` 5→3 (`app/config.py`). CLI `flask init-fireflight
  --admin-pin` / `FIREFLIGHT_ADMIN_PIN` ersetzt `--admin-password`. Admin-Anlageformular
  (`/administration/users/new`) prüft Format + Denylist serverseitig. Lokale Dev-DB (`fireflight2`)
  einmalig auf die neue Migration gehoben, bestehender `admin`-Account-Login auf PIN `4726` gesetzt
  (alter Passwort-Hash war nach der Spaltenumbenennung nicht mehr als PIN nutzbar — erwartete,
  dokumentierte Breaking Change, da noch keine echten Produktivnutzer existieren). 15 neue/umgeschriebene
  Tests in `tests/test_auth.py` (Format-Validierung, alle drei Sperrstufen, PIN-Wechsel, Admin-Unlock,
  Admin-Anlage mit/ohne triviale PIN). **Offener Punkt (nicht vom Nutzer entschieden):** Deployment-
  Kontext des Büro-Zugangs (offen/VPN) weiterhin ungeklärt — bei offenem Internetzugriff bleibt die PIN
  (nur 10.000 Kombinationen) die einzige Hürde, Empfehlung Betrieb hinter VPN/Reverse-Proxy mit
  IP-Allowlist steht noch aus.

- **Zwischenschritt — DJI-FlightHub-2-Integration komplett entfernt**: Auf Nutzerwunsch ("erstmal eine
  Basis schaffen") wurde `app/integrations/dji_flighthub/` (Client-Interface, Mock-/Live-Client,
  Sync-Service, Admin-Statusseite, Livestream/WHEP-Player) vollständig aus dem Code entfernt, kein
  Ersatz-Fachmodul an dieser Stelle. Mitentfernt: Blueprint-Registrierung, CSP-Lockerung für den
  WHEP-Call (`connect-src` wieder strikt `'self'`), `DJI_FLIGHTHUB_*`-Env-Variablen, das
  `dji_integration_status`-Widget, die „Integrationen"-Navigationseinträge (Sidebar +
  Administrationsübersicht), die `integrations.*`-Berechtigungen (auch aus `equipment_officer`s
  Standardrechten) und `tests/test_dji_integration.py`. **Bewusst nicht angetastet:** die generische
  `external_references`-Tabelle (nicht DJI-spezifisch, wird für spätere Module wie das Flugbuch
  gebraucht) sowie die physischen `integration_configs`/`integration_sync_runs`-Tabellen einer bereits
  migrierten Datenbank — dort existieren sie als harmlose Altlast weiter, werden aber von keinem Modell
  mehr referenziert; eine Migration, die sie aktiv droppt, wurde nicht geschrieben (kann bei Bedarf
  nachgezogen werden). Vollständige Historie der ursprünglichen Implementierung/Recherche bleibt in
  `CLAUDE.md` „Verlauf" und `docs/dji-flighthub2-api.md` erhalten, falls die Integration später
  zurückkommt.

Testsuite insgesamt: 38/38 grün (`pytest`, lokal gegen `fireflight2_test`).

### Als Nächstes (Reihenfolge s. Restrukturierungsplan)
Phase 4 Notifications-Kern → Phase 5 RC-Hardware-Feasibility-Spike (vorgezogen) → Phase 6
Drohneneinheiten → Phase 7 Nutzerprofil-Erweiterung → Phase 8 Wizard-Engine → Phase 9 Einsatz/Übung +
Flugbuch → Phase 10 Tickets + Wartungsintervalle → Phase 11 RC-PWA-Vollausbau → Phase 12
RC-Wizard-Inhalte → Phase 13 fachliche Dashboard-Module → Phase 14 externe Integrationen (DWD/OpenSky)
→ Phase 15 Tests und Dokumentation.

---

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
- ~~**DJI-FlightHub-Integration (Grundstruktur)**~~ — war implementiert und live getestet, **am 2026-07-23 auf Nutzerwunsch komplett entfernt** (s. Abschnitt „Status: Ausbaustufe 2" oben), um zunächst eine integrationsfreie Basis fertigzustellen
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
- **DJI-FlightHub-2-Anbindung**: war bis 2026-07-23 implementiert (Mock- und Live-Client, projektübergreifende
  Geräte-/HMS-/Telemetrie-Discovery, Livestream), wurde dann auf Nutzerwunsch komplett wieder entfernt,
  um zunächst eine integrationsfreie Basis fertigzustellen — Details s. „Status: Ausbaustufe 2" oben.
  Recherche/Erkenntnisse zur echten API bleiben in `docs/dji-flighthub2-api.md` erhalten, falls die
  Integration später zurückkommt.
- **2FA/TOTP**: in spec-struktur.md nicht erwähnt, in v1 vorhanden — Entscheidung mit Nutzer offen
- **Dark-Mode-Farbwerte**: aktuell pragmatisch aus den Neutral-/Accent-Ramps abgeleitet (`app/static/css/app.css`,
  `:root[data-theme="dark"]`), keine vom Nutzer gelieferten exakten Werte — bei Bedarf nachschärfen
- **PIN-zurücksetzen**: Struktur vorbereitet (`app/auth/services.py: request_pin_reset`), aber kein
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
