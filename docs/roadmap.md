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

- **Phase 4 — Notifications-Kern (Web-Push)**: neues Kern-Package `app/notifications/`
  (`PushSubscription`, `NotificationLog`, Migration `ad2f3b109171`). `PushSubscription.endpoint`
  (nicht `user_id`) ist der stabile Schlüssel — `subscribe()` upserted darauf, damit ein
  Bedienerwechsel auf demselben Gerät (später RC) die Zeile umhängt statt zu duplizieren.
  `app/notifications/service.py`: `subscribe`/`unsubscribe`/`send_to_user`/`send_to_users`/
  `send_to_role`; Zustellung über `pywebpush` (neu in `requirements.txt`), bei 404/410-Antwort wird
  die Subscription automatisch deaktiviert, bei sonstigen HTTP- oder Netzwerkfehlern (`requests`-
  Exceptions, z. B. unerreichbarer Endpoint) bleibt sie aktiv und der Fehler landet nur im
  `NotificationLog`. VAPID-Schlüssel als rohe base64url-Strings (`app/core/security/vapid.py`,
  CLI `flask notifications generate-vapid-keys`) statt PEM — kompatibel sowohl mit
  `PushManager.subscribe()` im Browser als auch direkt mit `pywebpush`. Neue Env-Variablen
  `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY`/`VAPID_CLAIMS_EMAIL` (`.env.example`, `docker-compose.yml`);
  ohne sie läuft die App normal weiter, nur Push-Versand ist deaktiviert (`ValidationError` bei
  Sendeversuch). Neue Route `/notifications/settings` (Topbar-Link „Benachrichtigungen") lässt jeden
  eingeloggten Nutzer für sein aktuelles Gerät Push aktivieren/deaktivieren und eine
  Testbenachrichtigung an sich selbst schicken — Verifikation ist laut Restrukturierungsplan bewusst
  ein manueller Rundlauftest im echten Browser (DevTools → Application → Service Worker/Push), kein
  automatisierbarer Test. Minimaler Service Worker `app/static/js/sw.js` (Push-/Notificationclick-
  Handler) mit Standard-Scope `/static/js/` registriert — bewusst **kein** Root-/`/rc/`-Scope, das ist
  Sache der echten PWA-Manifeste aus Phase 5/11. 20 neue Tests in `tests/test_notifications.py`
  (Subscribe-Upsert, Unsubscribe-Ownership-Check, Send-Erfolg/404/410/Serverfehler/Netzwerkfehler,
  send_to_role, Routen). Migration gegen die reale lokale Dev-DB verifiziert (`flask db upgrade` +
  anschließender `flask db migrate`-Drift-Check zeigt nur noch die bereits bekannten,
  DJI-Alttabellen — keine eigene Drift). Live-Rundlauftest (Subscribe/Unsubscribe-Routen) per `curl`
  gegen den laufenden Dev-Server bestätigt; der eigentliche Push-Zustellungstest mit einer echten
  Browser-Subscription steht noch aus (nicht automatisiert ausgeführt, s. „Als Nächstes").

- **Phase 5 — RC-Hardware-Feasibility-Spike (reduzierter Umfang)**: neues Kern-Package `app/rc/`
  (`RcDevice`-Modell, Migration `e2ceaef6caed`). Bewusste Vereinfachung gegenüber dem Plantext: der
  Geräteschlüssel (`device_key_hash`) ist zugleich der langlebige `rc_device_token`-Cookie-Wert -- kein
  separates, rotierbares Session-Token, um beim genannten Drei-Felder-Modell zu bleiben; bei
  Kompromittierung hilft nur `regenerate_device_key()` (danach muss das Gerät neu gekoppelt werden).
  Zwei getrennte Sitzungsebenen wie geplant: Geräte-Session rein über den Cookie
  (`app/rc/routes.py: _load_device()`, iteriert aktive Geräte und vergleicht den Werkzeug-Hash -- bei
  der kleinen Anzahl physischer RCs unproblematisch), Bediener-Session über normalen Flask-Login nach
  PIN-Eingabe (`app.auth.services.authenticate()` wiederverwendet) zusätzlich mit
  `session["rc_device_id"]` verknüpft. `/rc/logout` ("Person wechseln") meldet nur den Bediener ab,
  der Geräte-Cookie bleibt unangetastet -- kein `session.clear()` wie beim Desktop-Logout. Eigener
  `login_manager.blueprint_login_views = {"rc": "rc.login"}` (app/__init__.py) verhindert, dass
  `@login_required` auf `/rc/`-Routen zur Desktop-Login-Seite umleitet (Flask-Login-Default wäre sonst
  `auth.login` gewesen -- hätte den Kiosk-Kontext gesprengt). `manifest-rc.webmanifest` (Scope `/rc/`)
  + `/rc/sw.js` (eigene Route statt `/static/js/sw-rc.js` direkt, damit der Scope aus dem Request-Pfad
  automatisch `/rc/` wird) mit Push-/Notificationclick-Handler, inhaltlich identisch zu
  `/static/js/sw.js`. `app/static/js/notifications.js` dafür generalisiert (`data-sw-url`-Attribut
  statt hartkodierter Service-Worker-URL, neue `#notifications-test-send`-Wiring), `/notifications/
  test-send` unterstützt jetzt Content Negotiation (Accept: application/json → JSON-Antwort statt
  Redirect+Flash) speziell für den RC-Kiosk-Kontext. Admin-UI unter `/administration/rc-devices`
  (neue Berechtigungen `rc_devices.view`/`rc_devices.manage`): Geräte anlegen (Klartext-Schlüssel wird
  **einmalig** auf einer eigenen Seite angezeigt, nie gespeichert), Schlüssel neu vergeben,
  aktivieren/deaktivieren, sowie ein Textfeld für die DJI-Pilot-2-Deep-Link-URL (generische
  `SystemSetting`, Key `rc_dji_pilot2_deeplink_url`) -- **bewusst kein geratener URL-Scheme**: der
  "Zu DJI Pilot 2 wechseln"-Button auf `/rc/home` bleibt ausgeblendet, bis der Nutzer den korrekten
  Wert auf der echten RC Plus ermittelt hat. Qualifikationsfilter (`RcDevice.required_qualification`)
  ist als Feld/Admin-Auswahl vorhanden, aber wie geplant noch **nicht ausgewertet** (kommt mit Phase
  7/Profiles). Neues CLI-Kommando `flask seed-test-data` (überfällig seit Phase 1, jetzt nachgeholt):
  ein Testuser pro Standardrolle (`test_<rollenschlüssel>`, PIN 4726) sowie die zwei laut Plan
  geforderten `RcDevice`-Testeinträge (`required_qualification` `pilot`/`camera_operator`) --
  idempotent, wird künftig um weitere Phasen-Testdaten ergänzt. 19 neue Tests in `tests/test_rc.py`
  (Pairing mit richtigem/falschem Schlüssel, Geräte-Persistenz über Operator-Logout hinweg,
  Deaktivierung erzwingt Neu-Pairing, Blueprint-Login-View-Redirect, Admin-CRUD, Berechtigungsprüfung,
  CLI-Idempotenz) plus 1 neuer Test für die JSON-Variante von `/notifications/test-send`. Kompletter
  Pairing→Login→Home-Rundlauf **per `curl` gegen den echten laufenden Dev-Server verifiziert**
  (inkl. `/static/manifest-rc.webmanifest` und `/rc/sw.js`). **Nicht verifiziert (braucht die echte
  DJI RC Plus, s. Restrukturierungsplan):** PWA-Installierbarkeit, Hintergrund-Push bei minimierter
  App unter DJIs Energie-/Hintergrundrichtlinien, tatsächlicher App-Wechsel zu DJI Pilot 2, sowie der
  allgemeine Browser-Push-Rundlauftest aus Phase 4 (echte Subscription) -- beides bewusst offen
  gelassen, das ist der eigentliche Zweck dieses Hardware-Spikes.

- **Phase 6 — Drohneneinheiten**: neues Kern-Package `app/units/` (`Unit`-Modell, `unit_managers`-
  m:n-Tabelle, `User.home_unit_id`, Migration `c610af27d089` -- alle drei Änderungen in einer
  Migration, da eng gekoppelt: `users.home_unit_id` referenziert `units.id`). Ein User gehört maximal
  einer "Heimat"-Einheit an (`home_unit_id`), kann aber unabhängig davon mehrere Einheiten *managen*
  (`managed_units`/`unit_managers`) -- Grundlage für Phase 7 (Nutzerprofile: "welche Einheit(en) darf
  ich managen") und Phase 9 (Einsatz/Übung). `app/units/services.py`: CRUD + `set_unit_managers()`
  (setzt die komplette Manager-Liste, kein Einzel-Hinzufügen) + `unit_members()` (liest über
  `User.home_unit_id`, keine eigene Zwischentabelle nötig) + `assign_home_unit()`. Admin-UI unter
  `/administration/units` (neue Berechtigungen `units.view`/`units.manage`): Liste, Anlegen/Bearbeiten
  mit Manager-Checkboxen (analog zum Rollen-Berechtigungs-Editor), Aktivieren/Deaktivieren; die
  Mitgliederliste einer Einheit ist dort nur lesend (Zuordnung erfolgt über die neue
  "Heimateinheit"-Auswahl im bestehenden Benutzer-Editor `/administration/users/<id>`, nicht
  umgekehrt). `flask seed-test-data` um 3 Testeinheiten mit **überlappenden Managern** erweitert
  (`test_unit_leader`/`test_tel_elw`/`test_incident_commander` verwalten jeweils mehrere Einheiten),
  wie im Restrukturierungsplan für die Phase-6-Testdaten gefordert -- Zuordnung wird nur bei
  Erstanlage einer Einheit gesetzt, nicht bei jedem erneuten Lauf überschrieben. 21 neue Tests in
  `tests/test_units.py`. Migration gegen die reale lokale Dev-DB angewendet, Drift-Check zeigt nur
  die bekannten DJI-Alttabellen. Live per `curl` verifiziert: Admin-Login → `/roles/select` (aktive
  Rolle muss vor jeder `permission_required`-Route einmal aktiviert werden, sonst 403 -- reiner
  Login allein reicht nicht) → `/administration/units` zeigt alle drei Testeinheiten,
  Benutzer-Editor zeigt die neue Heimateinheit-Auswahl korrekt befüllt.

- **Phase 7 — Nutzerprofil-Erweiterung**: Konzeptdokument (`fireflight2-konzept-struktur.md`)
  Abschnitt 8 diente als Detailquelle, da der Restrukturierungsplan selbst nicht im Repo liegt.
  `User` um `is_pilot`/`is_camera_operator` (zwei Booleans statt m:n-Tabelle -- nur zwei fest
  benannte Werte, ein User kann laut Konzept beide gleichzeitig haben), `phone_number` und
  `profile_image_filename` erweitert (Migration `f07570aabbd1`); neue Konstanten
  `app.auth.models.QUALIFICATION_PILOT`/`QUALIFICATION_CAMERA_OPERATOR`/`QUALIFICATIONS` sind jetzt
  die einzige Quelle der Wahrheit dafür, `app/rc/services.py: create_device()` validiert
  `required_qualification` seither tatsächlich dagegen (vorher deklariert, aber nie geprüft).
  **Der eigentliche Qualifikationsfilter ist jetzt scharf**: `app/rc/routes.py: login()` prüft nach
  erfolgreicher PIN-Eingabe `user.has_qualification(device.required_qualification)` und weist bei
  Nichterfüllung mit einer eigenen Fehlermeldung ab, ohne das als Fehlversuch gegen die
  Sperr-Eskalation zu zählen (PIN war korrekt, es ist kein Bruteforce-Indiz). Bewusst **kein**
  Zwei-Schritt-„User aus Liste wählen"-UI wie im Konzeptdokument Abschnitt 5.1 beschrieben -- das
  bleibt Umfang für Phase 11 (RC-PWA-Vollausbau); Phase 7 behält den bestehenden einstufigen
  Username+PIN-Login bei und ergänzt nur die Zugriffsprüfung. Qualifikationen sind Admin-verwaltet
  (`administration/users/<id>`, Checkboxen neben Rollen/Heimateinheit), nicht Self-Service --
  passend zur Konzeptdoku-Unterscheidung zwischen "Übersicht" (Einheit/Funktion/Rollen, nur lesend
  im Profil) und "persönlichen Daten" (E-Mail/Telefon/Bild, dort tatsächlich änderbar).

  Neues Kern-Package `app/profile/` (`GET/POST /profile/`): Self-Service-Bearbeitung von E-Mail
  (mit Eindeutigkeitsprüfung gegen andere Konten) und Telefonnummer, Profilbild-Upload/-Entfernung,
  read-only Übersicht (Heimateinheit, verwaltete Einheiten, Funktion, Rollen) -- Datenquellen
  vollständig aus Phase 6 (`Unit`/`unit_managers`) und den Rollen/Qualifikationen oben. Neuer
  Nav-Link „Mein Profil" im Topbar neben „Benachrichtigungen".

  Profilbild-Upload (`app/core/utilities/uploads.py`, neues Modul, keine neue Abhängigkeit) validiert
  per **Magic-Bytes** (PNG/JPEG/WebP-Signatur), nicht Dateiendung oder Client-Content-Type -- verhindert
  z. B. eine als „.png" umbenannte Datei mit anderem Inhalt. Max. 5 MB, ein Bild pro User
  (server-generierter Dateiname `<user_id>.<ext>`, alter Datei-Inhalt wird beim Ersetzen gelöscht).
  Speicherort bewusst unter `instance_path/uploads/profile_images/`, nicht `app/static/` (Nutzerinhalte
  getrennt vom versionierten Code) -- dafür neues Docker-Volume `fireflight2-uploads-data:/app/instance`
  (`docker-compose.yml`), sonst gingen Bilder bei jedem Image-Rebuild verloren. `Dockerfile` legt das
  Zielverzeichnis vor dem `chown` an, damit das non-root-Image beim ersten Volume-Mount die korrekten
  Rechte aus dem Image-Layer übernimmt (Docker kopiert Inhalt+Rechte eines bereits im Image
  existierenden Verzeichnisses in ein frisch erzeugtes named volume). Serviert über eine eigene,
  login-geschützte Route (`GET /profile/image/<user_id>`, jeder eingeloggte Nutzer darf jedes
  Profilbild sehen -- internes Single-Tenant-System, kein sensibler Inhalt), Content-Type wird anhand
  der beim Upload gesniffter Extension gesetzt, nicht dem Dateisystem-Mimetype-Guess überlassen.

  `flask seed-test-data` erweitert: `test_pilot_camera` bekommt bei Erstanlage beide Qualifikationen
  (deckt beide vorhandenen RC-Testgeräte ab). Migration gegen die reale lokale Dev-DB verifiziert
  (`flask db upgrade` + anschließender `flask db migrate`-Drift-Check zeigt nur noch die bekannten
  DJI-Alttabellen). Beim Autogenerate-Lauf schlug Alembic wieder das Droppen der DJI-Alttabellen vor --
  bewusst nicht übernommen, konsistent mit der Entscheidung in `ad2f3b109171` (Phase 4). 23 neue Tests
  (`tests/test_profile.py`, `tests/test_rc.py` um Qualifikationsfilter-Fälle ergänzt). Live gegen den
  echten Dev-Server verifiziert: Admin setzt Qualifikation über `/administration/users/<id>` →
  RC-Login mit passender Qualifikation erfolgreich, mit fehlender Qualifikation abgewiesen (eigene
  Fehlermeldung, kein Fehlversuchszähler) → Self-Service-Profil (E-Mail/Telefon geändert, echtes PNG
  hochgeladen, per `GET /profile/image/<id>` mit korrektem `Content-Type: image/png` abgerufen, wieder
  entfernt → danach 404). Testsuite 111/111 grün. **Nebenfund beim Live-Test:** lokale Dev-DB hatte für
  den `admin`-Account ein von der Dokumentation abweichendes PIN (vermutlich aus einer früheren
  manuellen Testsitzung) -- lokal auf `4726` zurückgesetzt, kein Code-Bug.

Testsuite insgesamt: 111/111 grün (`pytest`, lokal gegen `fireflight2_test`).

### Als Nächstes (Reihenfolge s. Restrukturierungsplan)
Hardware-Verifikation auf der echten DJI RC Plus (Phase 4/5 zusammen, s. o.: Push-Rundlauftest im
normalen Browser zuerst, danach PWA-Installation über `/rc/pair` → `/rc/home` mit einem der beiden
`seed-test-data`-Testgeräte, Hintergrund-Push, DJI-Pilot-2-Deep-Link-URL ermitteln und in
Administration → RC-Geräte eintragen) → Phase 8 Wizard-Engine → Phase 9 Einsatz/Übung + Flugbuch →
Phase 10 Tickets + Wartungsintervalle → Phase 11 RC-PWA-Vollausbau (u. a. das im Konzeptdokument
Abschnitt 5.1 beschriebene Zwei-Schritt-Login mit Nutzerauswahl vor PIN-Eingabe) → Phase 12
RC-Wizard-Inhalte → Phase 13 fachliche Dashboard-Module → Phase 14 externe Integrationen
(DWD/OpenSky) → Phase 15 Tests und Dokumentation.

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
