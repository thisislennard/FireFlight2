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

- **Phase 8 — Wizard-Engine**: bewusst nur die generische Engine, nicht die konkreten Preflight-/
  Flugstart-/Flugende-Inhalte aus dem Konzeptdokument Abschnitt 5.2-5.5 -- die sind Umfang von Phase 12
  (RC-Wizard-Inhalte), sobald Phase 9 (Einsatz/Übung) und Phase 11 (RC-PWA-Vollausbau) existieren, an
  die ein echter Wizard-Lauf andocken kann. Neues Kern-Package `app/wizards/`: `Wizard`/`WizardStep`
  (Migration `bfe16e421ba5`, `WizardStep.config` als JSONB analog zu `DashboardWidget.config`),
  Step-Typ-Registry (`app/wizards/step_types.py`, analog zu `dashboards/widgets.py`s
  `WidgetRegistry`) mit fünf generischen Typen: `info` (reiner Text, immer weiterschaltbar),
  `checklist` (alle Punkte müssen angehakt sein), `confirmation` (eine Bestätigungs-Checkbox),
  `text_input` (Freitext, optional Pflicht), `choice` (eine Option aus fester Liste) -- deckt die in
  Abschnitt 5.2-5.5 beschriebenen Inhalte (Preflight-Checkliste, Einsatz/Übung-Auswahl, Freitext-Zweck,
  Abschlussfragen) ab, ohne sie bereits fest zu verdrahten. Bewusst **kein** `location`-Step-Typ (GPS+
  Zeit-Auto-Erfassung aus Abschnitt 5.2/5.5) -- ohne echten Verbraucher wäre die nötige
  Browser-Geolocation-JS-Anbindung unverifizierbar spekulativ, kommt mit Phase 9/12, wenn eine echte
  Flugbuch-Persistenz dafür existiert.

  `app/wizards/runner.py: WizardRunner` ist der generische Laufzeit-Motor (Schritt validieren → bei
  Erfolg weiterschalten, sonst auf derselben Seite mit Fehlermeldung bleiben -- Konzeptdokument
  Abschnitt 5.6: "Weiterkommen erst möglich, wenn bestimmte Aktionen ausgeführt wurden"), operiert auf
  einem beliebigen mutable Zustands-Dict. Aktuell einziger Konsument ist die **Admin-Vorschau**
  (`/administration/wizards/<id>/preview`, Zustand in der Flask-Session, rein ephemer) -- ein echter
  RC-Lauf mit Persistenz in ein Flugbuch ist Phase-9/12-Umfang und wird dieselbe Validierungslogik
  voraussichtlich mit einem anderen Zustands-Backend wiederverwenden. Bewusst **kein**
  Zwei-Knopf-Ende-Bildschirm ("Selbe Person, neuer Flug" / "Komplett neu" aus Abschnitt 5.6) -- das ist
  RC-Kiosk-spezifisch (Phase 11/12), die generische Vorschau hat nur "Neu starten". Bewusst **keine**
  client-seitige Button-Deaktivierung per JS -- die serverseitige Gate-Prüfung erfüllt die fachliche
  Anforderung vollständig, UI-Politur (Button erst aktiv, wenn erfüllt) ist Phase-11/12-Umfang für die
  echte RC-Kiosk-Oberfläche.

  Admin-CRUD unter `/administration/wizards` (neue Berechtigungen `wizards.view`/`wizards.manage`,
  analog zu `units`/`rc_devices`): Wizard anlegen/bearbeiten/(de)aktivieren, Schritte hinzufügen
  (Step-Typ wählen, startet mit `default_config`) / config-spezifisch bearbeiten (Formularfelder
  dynamisch aus `WizardStepTypeDefinition.config_fields`, z. B. "eine Zeile je Punkt" für Checklisten-
  Items) / löschen / per Auf-/Ab-Buttons neu sortieren (`move_step()` tauscht mit dem sortierten
  Nachbarn, robust gegenüber Lücken nach Löschungen -- keine feste `position ± 1`-Arithmetik).
  `flask seed-test-data` legt einen Beispiel-Wizard an, der alle fünf Step-Typen demonstriert.

  Migration gegen die reale lokale Dev-DB verifiziert (Autogenerate schlug wieder das Droppen der
  DJI-Alttabellen vor -- bewusst nicht übernommen, wie bei `ad2f3b109171`/`f07570aabbd1`). 30 neue
  Tests (`tests/test_wizards.py`): Step-Typ-Validierung, Service-CRUD, `WizardRunner` (inkl. inaktiver
  Schritte, Zurück/Reset), Admin-Routen, vollständiger Vorschau-Durchlauf. Live gegen den echten
  Dev-Server verifiziert: kompletter 5-Schritt-Durchlauf des Beispiel-Wizards inkl. Checklisten-Gate
  (unvollständig abgewiesen, vollständig durchgelassen), Freitext-Pflichtfeld-Gate, Abschluss-Bildschirm
  und Reset; 403 für Nutzer ohne `wizards.*`-Berechtigung bestätigt. Testsuite 139/139 grün.
  **Nebenfund bei der Live-Verifikation:** ein per `curl`/Bash unter Windows übergebener Umlaut
  ("Übung") kam serverseitig verstümmelt an (Shell/curl-Encoding-Artefakt dieser Maschine, nicht
  reproduzierbar mit Pythons `requests`-Bibliothek oder im echten Browser) -- kein Anwendungsfehler,
  nur eine Einschränkung des `curl`-Testwerkzeugs auf dieser Maschine für nicht-ASCII-Formulardaten.

- **Phase 9 — Einsatz/Übung + Flugbuch**: erstes echtes Fachmodul über das Modul-Registry-System aus
  Phase 1 (`app/modules/incidents/`) -- deckte dabei zwei latente, seit Phase 1 nie mit einem echten
  Modul durchgespielte Bugs in `app/templates/base.html` auf: die Sidebar-Navigation aus
  `module_navigation` rendert `entry.endpoint` als rohen `href`-Wert statt `url_for(entry.endpoint)`
  aufzurufen, **und** filtert nicht auf die Berechtigung des Eintrags (jeder eingeloggte Nutzer hätte
  jeden Modul-Navigationslink gesehen, unabhängig von seinen Rechten). Beides gefixt. Zwei
  Nutzerentscheidungen vor der Umsetzung eingeholt (Rückfrage, da im Konzeptdokument Abschnitt 6/7 nur
  knapp beschrieben und im 15-Phasen-Plan keine eigene Drohnen-/Akkuverwaltungs-Phase vorgesehen ist):
  Drohne/Akku als Freitextfeld statt Fremdschlüssel (kein Geräte-Modul vorhanden), und Flugbuch-Felder
  orientiert an dem, was der künftige RC-Wizard erfassen wird (Konzeptdokument Abschnitt 5.2-5.5),
  **plus** durchgehende manuelle Pflege über Desktop und durchgängige Standort-Anzeige auf einer Karte
  (Nutzeranforderung, ohne auf Phase 11/12 zu warten).

  Neue Kern-Modelle `Incident` (Einsatz/Übung, `kind` "einsatz"/"uebung", kann mehrere Flüge umfassen)
  und `Flight` (Pilot/Kamera-Operator als FK auf `User` -- nutzt die Qualifikationsfelder aus Phase 7
  fürs Admin-UI-Hinweis "keine Pilot-Qualifikation" bei der Crew-Auswahl, verhindert sie aber nicht;
  `drone_label`/`battery_label` bewusst Freitext; Start-/End-Zeit+Standort; Abschlussfragen `synced`/
  `had_issues` aus Konzeptdokument Abschnitt 5.5). Migration `6fedb0635366`.

  **Karte**: Leaflet 1.9.4 lokal vendored (`app/static/lib/leaflet/`, kein CDN, konsistent mit dem
  Rest des Projekts) -- lädt aber die eigentlichen Kartenkacheln von `tile.openstreetmap.org` extern,
  dafür CSP `img-src` einmalig um genau diesen Host erweitert (`app/__init__.py: _security_headers`).
  Flug-Standorte werden serverseitig zu einfachen JSON-Objekten reduziert (keine SQLAlchemy-Objekte
  direkt in `| tojson`) und über einen `<script type="application/json">`-Block eingebettet (kein
  Inline-`<script>` mit Logik nötig, bleibt CSP-`script-src 'self'`-konform) -- `static/js/
  incidents_map.js` liest sie aus und zeichnet Marker mit Popup (Einsatz/Übung, Crew, Link zum
  Flug). `static/js/geolocation_capture.js`: "Aktuellen Standort verwenden"-Button im Flug-Formular
  nutzt `navigator.geolocation` als Komfortfunktion -- rein progressive Verbesserung, Standort bleibt
  auch manuell eintippbar, Formular funktioniert ohne Geolocation-Zustimmung.

  Admin-/Desktop-CRUD unter `/incidents/` (neue Modul-Berechtigungen `incidents.view`/`incidents.edit`
  über `IncidentsModule.register_permissions()`, nicht `DEFAULT_PERMISSIONS`): Einsätze/Übungen anlegen/
  bearbeiten/abschließen/wieder öffnen, Flüge je Einsatz anlegen/bearbeiten/löschen, `/incidents/karte`
  (alle Flüge mit Standort), `/incidents/logbuch` (`services.logbook_summary()`: pro Person Anzahl
  Einsatz-/Übungsflüge, zählt sowohl als Pilot als auch als Kamera-Operator, filterbar nach Jahr/Monat
  über `Flight.started_at`). `incidents.view`/`incidents.edit` default an die Rollen vergeben, deren
  Name/Zweck fachlich naheliegt (Dokumentation, Pilot/Kamera, Flugleiter, Einsatzleiter je view+edit;
  Einheitsführer, TEL-ELW nur view; Gerätewart unverändert ohne Zugriff) -- über den bestehenden
  Rollen-Editor jederzeit admin-anpassbar.

  **Nebenfund, echter Bug (nicht nur Testartefakt):** `app/core/utilities/time.py: to_local()` existiert
  seit Ausbaustufe 1, wurde aber bis zu den neuen Flugbuch-Templates **nirgends tatsächlich aufgerufen**
  -- dabei zeigte sich, dass `ZoneInfo("Europe/Berlin")` unter Windows (und vermutlich im schlanken
  `python:3.12-slim`-Docker-Image, da Debian-Slim-Images kein System-Tzdata mitbringen) ohne das
  `tzdata`-PyPI-Paket mit `ZoneInfoNotFoundError` fehlschlägt. `tzdata==2026.3` zu `requirements.txt`
  ergänzt -- behebt das für `to_local()` **und** die neue Formular-Gegenrichtung
  `parse_local_datetime()` gleichermaßen, sowohl lokal als auch im Produktions-Container.

  `flask seed-test-data` legt eine Beispiel-Übung und einen Beispiel-Einsatz mit je einem Flug an
  (unterschiedliche Personen/Zeiträume, einer mit vollständigem Start+End-Standort für die
  Karten-Vorschau, einer nur mit Start-Standort und `had_issues=True` für Abschlussfragen-Testdaten).
  Migration gegen die reale lokale Dev-DB verifiziert (Drift-Check zeigt nur die bekannten
  DJI-Alttabellen, wie bei allen vorherigen Phasen bewusst nicht gedroppt). 39 neue Tests
  (`tests/test_incidents.py`), inkl. Regressionstests für die beiden Navigation-Bugfixes. Live gegen
  den echten Dev-Server verifiziert: Sidebar-Link erscheint/verschwindet korrekt je nach Berechtigung,
  Einsatz+Flug manuell über Desktop angelegt, Abschließen/Wiedereröffnen, Karte lädt mit eingebetteten
  Koordinaten und korrektem CSP-Header, Logbuch zeigt Testdaten-Personen, 403 für Rolle ohne
  `incidents.*`. Testsuite 156/156 grün.

- **Phase 10 — Tickets + Wartungsintervalle**: zweites Fachmodul über das Modul-Registry-System
  (`app/modules/tickets/`, nach `app/modules/incidents/` in Phase 9). Konzeptdokument Abschnitt 9
  rahmt "Technisches Problem melden" als breit zugängliche Dashboard-Funktion (jede Crew), während
  Abschnitt 10 Gerätewart als Rolle *ohne* Dashboard beschreibt, die stattdessen Tickets verwaltet und
  Wartungsintervalle pflegt -- deshalb granulare Berechtigungen: `tickets.view`/`tickets.create`
  (breit vergeben: Dokumentation, Pilot/Kamera, Flugleiter, Einsatzleiter, Einheitsführer, TEL-ELW)
  vs. `tickets.manage`/`maintenance.view`/`maintenance.manage` (nur Gerätewart).

  **Rollen ohne Dashboard wird zum ersten Mal echt genutzt:** Gerätewart verliert `dashboard.view`
  und bekommt `landing_endpoint = "tickets.list_tickets"` -- Infrastruktur seit Phase 2 vorbereitet,
  aber bis jetzt nie mit einer echten Rolle belegt. Dabei zwei weitere latente Lücken gefunden, exakt
  wie schon bei Phase 9s Modul-Registry-Erstnutzung: (1) der hartkodierte "Dashboard"-Sidebar-Link in
  `base.html` war nie berechtigungsgeprüft -- für eine Rolle ohne `dashboard.view` wäre er ein
  garantierter 403-Link gewesen, jetzt hinter `has_permission('dashboard.view')`. (2)
  `_resolve_role_landing()` prüfte bei einem individuell gesetzten `landing_endpoint` nur, ob sich die
  URL bauen lässt, nicht ob die Rolle dort überhaupt eine Berechtigung hat -- unproblematisch, solange
  `landing_endpoint` ausschließlich über den (bereits Permission-gefilterten) Admin-Editor gesetzt
  wurde, aber `seed_roles()` setzt es jetzt auch, und Berechtigungen können sich danach unabhängig
  ändern. Fix: für Ziele, die einem `ModuleRegistry.navigation`-Eintrag mit bekannter Berechtigung
  entsprechen, wird die jetzt geprüft; für alles andere (z. B. ein Admin setzt `administration.audit_log`
  von Hand als Landing-Ziel) bleibt das alte, permissivere Verhalten erhalten, um einen bestehenden
  Phase-2-Test nicht zu brechen, der genau das erwartet.

  Datenmodell: `Ticket` (+`TicketComment`, `TicketAttachment`) und `MaintenanceRule` (+`MaintenanceEvent`)
  in einem Modul, analog zu Incident+Flight in Phase 9. `MaintenanceRule` speichert kein
  `last_completed_at`-Feld -- wird aus dem jüngsten `MaintenanceEvent` abgeleitet (Fallback
  `created_at`), damit es nie mit der Ereignis-Historie auseinanderlaufen kann; `next_due_at`/
  `warning_at`/`is_due`/`is_warning` sind Properties darauf. Migration `31acde4e81fe`.

  Foto-Anhänge für Tickets nutzen dieselbe Magic-Byte-Validierung wie die Profilbilder aus Phase 7
  (`app/core/utilities/uploads.py`, jetzt generalisiert: `MAX_IMAGE_BYTES` statt
  `MAX_PROFILE_IMAGE_BYTES` als Basis-Konstante, Alias für Rückwärtskompatibilität mit
  `tests/test_profile.py`), aber mit zufälligen statt festen Dateinamen, da ein Ticket beliebig viele
  Anhänge haben kann (kein 1:1-Slot pro Datensatz wie beim Profilbild). Kein neues Docker-Volume nötig
  -- liegt unter demselben `instance_path`-Volume, das Phase 7 schon eingerichtet hat.

  **Fälligkeits-Push:** `flask maintenance check-due` (neue CLI-Gruppe) prüft fällige/bald fällige
  Regeln und schickt einmal pro Lauf eine zusammengefasste Push-Nachricht (nicht eine pro Regel, um
  Spam bei mehreren gleichzeitig fälligen Regeln zu vermeiden) an alle Nutzer mit `maintenance.manage`
  -Berechtigung (über Rollen dedupliziert, damit niemand mit mehreren berechtigten Rollen doppelt
  benachrichtigt wird). Diese leichtgewichtige App hat keine eingebaute Zeitsteuerung -- der Befehl ist
  für einen externen Cron-Job gedacht (Host-Cron beim Docker-Deployment); fehlende VAPID-Konfiguration
  wird sauber als Fehlermeldung + Exit-Code 1 behandelt statt als Traceback.

  `flask seed-test-data` legt ein Beispiel-Ticket (mit Kommentar) sowie zwei Wartungsregeln an (eine
  bewusst überfällig, eine kürzlich erledigt -- deckt beide Anzeigezustände ab). Migration gegen die
  reale lokale Dev-DB verifiziert (Drift-Check zeigt nur die bekannten DJI-Alttabellen, wie bei allen
  vorherigen Phasen bewusst nicht gedroppt). 32 neue Tests (`tests/test_tickets.py`) -- die
  `_resolve_role_landing()`-Präzisierung wurde bewusst so eng geschnitten, dass beide betroffenen
  bestehenden Phase-2-Tests in `tests/test_roles.py` unverändert grün bleiben, keine Testdatei musste
  angepasst werden. Live gegen den echten Dev-Server verifiziert:
  Gerätewart-Login landet direkt auf `/tickets/` statt Dashboard (kein Dashboard-Link im Menü mehr),
  Ticket samt Foto-Anhang über eine Pilot/Kamera-Rolle angelegt (Status ändern dort korrekt mit 403
  abgewiesen), Wartungsregel von Gerätewart angelegt und als erledigt gemeldet, `flask maintenance
  check-due` erst mit sauberer Fehlermeldung ohne VAPID-Konfiguration, dann erfolgreich mit echten
  VAPID-Schlüsseln (3 benachrichtigte Nutzer für die überfällige Testregel). Testsuite 182/182 grün.

- **Phase 11 — RC-PWA-Vollausbau (Teilumfang: Zwei-Schritt-Login)**: nur der Login-Flow-Teil aus dem
  Konzeptdokument Abschnitt 5.1 umgesetzt, bewusst **ohne** den Zwei-Knopf-Ende-Bildschirm ("Selbe
  Person, neuer Flug"/"Komplett neu") aus Abschnitt 5.6 -- der gehört zum Ende eines Wizard-*Laufs*,
  und ohne echte Wizard-Inhalte im RC-Kontext (kommen erst mit Phase 12) gäbe es dafür noch keinen
  sinnvollen Auslösepunkt zu bauen. `/rc/login` ist jetzt zweistufig: Schritt 1 zeigt eine
  qualifikationsgefilterte Liste aktiver Nutzer zum Antippen (`app/rc/routes.py:
  _qualified_candidates()` -- ohne geräteseitigen Filter werden nur Nutzer mit *irgendeiner*
  Qualifikation gezeigt, nicht jeder aktive Account), Auswahl landet nur in der Session
  (`rc_login_candidate_id`), noch keine echte Anmeldung. Schritt 2 fragt nur noch die PIN des bereits
  ausgewählten Nutzers ab (`RcPinForm`, kein Identifier-Feld mehr -- der Nutzer wird nicht mehr
  eingetippt). `/rc/login/reselect` ("Anderer Nutzer") springt zurück zu Schritt 1. Der bestehende
  serverseitige Qualifikationsfilter aus Phase 7 bleibt als Verteidigung in Schritt 2 bestehen, greift
  über die normale Oberfläche aber kaum noch, da Schritt 1 bereits filtert -- nur noch relevant, falls
  sich die Qualifikation eines Nutzers zwischen Auswahl und PIN-Eingabe ändert, oder bei einer direkt
  manipulierten `user_id`, die nicht in der gerenderten Liste stand (wird in Schritt 1 bereits
  abgewiesen, landet gar nicht erst in der Session).

  **Nebenfund, echter Bug (nicht nur Testartefakt):** Das "Person wechseln"-Formular auf
  `rc/home.html` hatte noch **nie** einen CSRF-Token -- RC-Seiten haben (anders als die Desktop-App)
  kein `hx-boost`, das automatisch den `X-CSRFToken`-Header injiziert, und das Formular war ein
  rohes `<form>` ohne `hidden_tag()`. In einem echten Browser ohne manuell nachgebauten Header (wie in
  den bisherigen `curl`/`requests`-Verifikationen dieser Session, die den Header selbst gesetzt haben)
  hätte das mit `400 Bad Request` fehlgeschlagen. Behoben, und alle drei neuen rohen RC-Formulare
  (Schritt 1, "Anderer Nutzer") bekamen von Anfang an ein `csrf_token`-Hidden-Field.

  Zusätzlich, im Zuge der PWA-Politur: `manifest-rc.webmanifest` hatte nur ein einzelnes
  160×160-Icon -- für die von Chrome/Android geprüften Installierbarkeits-Kriterien werden meist
  192×192 und 512×512 erwartet. Mit Pillow (nur als Build-Zeit-Werkzeug genutzt, **nicht** in
  `requirements.txt`) aus dem vorhandenen Icon hochskaliert und als zusätzliche Manifest-Einträge
  ergänzt (`app/static/img/icon-mark-192.png`/`-512.png`).

  **Bewusst nicht angegangen, da neue, bisher in keiner Phase explizit verortete Lücke:** Für die
  "Büro-Nutzung" (Konzeptdokument Abschnitt 1) existiert **kein** eigenes PWA-Manifest -- nur die
  RC-Seite ist als PWA installierbar. Der 15-Phasen-Plan nennt nirgends eine "Büro-PWA"-Phase
  explizit; ob/wann das nachgezogen wird, sollte mit dem Nutzer geklärt werden statt hier
  stillschweigend mit hinein zu wachsen.

  Tests: `tests/test_rc.py` komplett auf den Zwei-Schritt-Flow umgeschrieben (alle Aufrufer von
  `/rc/login` mit `identifier`+`pin` in einem Schritt ersetzt durch einen `_login_two_step()`-Helper);
  fünf neue Tests für Schritt-1-Filterung, Auswahl→Schritt-2-Übergang, Tamper-Schutz und "Anderer
  Nutzer". Live gegen den echten Dev-Server verifiziert: Schritt 1 zeigt nur qualifikationsgefilterte
  Kandidaten, Auswahl führt zu Schritt 2 mit Begrüßung, falsche PIN bleibt auf Schritt 2 mit
  Fehlermeldung, richtige PIN führt zu `/rc/home`, "Anderer Nutzer" springt zurück zu Schritt 1.
  Testsuite 187/187 grün (kein neues DB-Modell, daher keine Migration nötig).

- **Phase 12 — RC-Wizard-Inhalte (voller Umfang inkl. Genehmigung + Push)**: verdrahtet die
  generische Wizard-Engine aus Phase 8 erstmals mit einem echten Verbraucher -- Preflight-Check,
  Flugstart mit Genehmigungspflicht, Flugende, Zwei-Knopf-Ende-Bildschirm (Konzeptdokument Abschnitt
  5.2-5.6). Auf Nutzerentscheidung im **vollen** Umfang umgesetzt, inkl. Startanfrage-Genehmigung
  und automatischer Push-Benachrichtigung an Flugleiter/Einsatzleiter (nicht nur der reduzierte
  Kernablauf).

  **Neuer `location`-Step-Typ** (`app/wizards/step_types.py`) für GPS-Auto-Erfassung, jetzt endlich
  mit einem echten Verbraucher, statt wie in Phase 8 spekulativ gebaut zu werden. **Neue
  `field_key`-Spalte auf `WizardStep`** (Migration `49286e4006a0`) bildet die Antwort eines Schritts
  generisch auf ein Flugbuch-Feld ab (`app/modules/incidents/wizard_fields.py`: Zweck,
  Einsatz/Übung, Start-/End-Standort, Synchronisiert?, Mängel?, Notizen) -- die Wizard-Engine selbst
  bleibt dabei bewusst fachlich neutral, das Mapping liegt in `app/rc/wizard_flow.py:
  collect_field_answers()`, einem reinen RC-Verbraucher. **Wichtiger Design-Fund unterwegs:** der
  Step-Typ `confirmation` erzwingt laut Phase-8-Logik *immer* eine angehakte Checkbox zum
  Weiterkommen -- für echte Ja/Nein-Fragen ("Synchronisiert?", "Mängel?"), bei denen beide Antworten
  gültig sein müssen, ist stattdessen `choice` mit Optionen "Ja"/"Nein" der richtige Step-Typ
  (`app/rc/routes.py` interpretiert die Antwort `"Ja"` als wahr).

  **Flight-Status-Workflow** (`FLIGHT_STATUS_DRAFT` → `PENDING_APPROVAL` → `APPROVED` → `COMPLETED`,
  Migration `49286e4006a0`) nur für RC-gesteuerte Flüge gesetzt -- über Desktop manuell angelegte
  Flüge (Phase 9) lassen `flight_status` bewusst `NULL` (fertige historische Einträge ohne
  Live-Workflow, unverändertes Verhalten). Neue Berechtigung `incidents.approve_flights` (getrennt
  von `incidents.edit`, das breit vergeben ist) an Flugleiter und Einsatzleiter/SBI. Neue
  Desktop-Seite `/incidents/freigaben` listet offene Startanfragen; Genehmigen löst eine
  Push-Rückmeldung an den Piloten aus.

  **RC-Ablauf** (`app/rc/routes.py`, `app/rc/wizard_flow.py`): `/rc/preflight` läuft den
  admin-konfigurierten Preflight-Wizard (Session-Zustand `rc_preflight_state`, analog zur
  Admin-Vorschau aus Phase 8, aber operator-spezifisch statt geteilt); danach
  `/rc/preflight/incident` -- Konzeptdokument Abschnitt 6 ("sich in einen laufenden Einsatz/Übung
  einbuchen"): Liste offener Einsätze/Übungen passender Art oder Neuanlage. Welche Crew-Rolle
  (Pilot/Kamera-Operator) der Flug bekommt, richtet sich nach dem Qualifikationsfilter des Geräts
  bzw. der eigenen Qualifikation bei einem ungefilterten Gerät -- ein Gerät bildet bewusst nur EINE
  Rolle je Flug ab; zwei gleichzeitig genutzte Geräte für denselben physischen Flug erzeugen zwei
  getrennte Flight-Datensätze (bekannte, akzeptierte Vereinfachung ohne echte Hardware zum Testen).
  `/rc/flight/start` ist zugleich die Startanfrage (Push an alle Nutzer mit
  `incidents.approve_flights`, über Rollen dedupliziert). Nach Freigabe schaltet `/rc/home` den
  "Zu DJI Pilot 2"-Button frei. `/rc/flight-end` läuft den Flugende-Wizard, danach der
  Zwei-Knopf-Ende-Bildschirm (`/rc/flight-end/summary`): "Selbe Person, neuer Flug" springt zurück zu
  `/rc/preflight` (Bediener bleibt angemeldet), "Komplett neu" nutzt das bestehende `/rc/logout`.

  **Zwei echte Bugs gefunden, exakt dasselbe Muster wie in Phase 9/10** (Infrastruktur, die beim
  Bauen plausibel aussah, aber nie mit einem echten Fall durchgespielt wurde): (1) Der
  hartkodierte "Person wechseln"-Bedienerwechsel (`/rc/logout`) räumte `rc_device_id` auf, aber nicht
  die neuen Bediener-spezifischen Session-Schlüssel (`rc_active_flight_id`,
  `rc_preflight_state`, `rc_flight_end_state`) -- ohne Fix hätte der nächste Bediener desselben
  Geräts den noch offenen Flug der vorigen Person gesehen und ggf. sogar "Flug starten"/"Flug
  beenden" für einen fremden Flug auslösen können. Jetzt über `_OPERATOR_SESSION_KEYS` beim Logout
  konsequent geleert, mit Regressionstest abgedeckt. (2) Beim erstmaligen echten Ja/Nein-Gebrauch des
  `choice`-Step-Typs mit `field_key` fiel auf, dass die ursprüngliche Wahl `confirmation` für
  "Synchronisiert?"/"Mängel?" das Weiterkommen bei "Nein" verhindert hätte (s. o.) -- vor dem
  Live-Test korrigiert.

  `flask seed-test-data` legt einen echten Preflight- und Flugende-Test-Wizard mit vollständiger
  `field_key`-Zuordnung an und hinterlegt sie automatisch als aktive SystemSettings, damit die
  seed-Testgeräte ohne manuellen Admin-Schritt sofort nutzbar sind. Migration `49286e4006a0` gegen
  die reale lokale Dev-DB angewendet, Drift-Check zeigt nur die bekannten DJI-Alttabellen. 25 neue
  Tests (`tests/test_rc_wizard_flow.py` neu, plus Ergänzungen in `tests/test_wizards.py` und
  `tests/test_incidents.py`). Testsuite 205/205 grün.

  **Live gegen den echten Dev-Server verifiziert**, kompletter Zyklus: Preflight-Wizard (Checkliste,
  Einsatz/Übung, Zweck, Standort) → Einsatz neu angelegt → Flug im Status "draft" → "Flug starten" →
  "pending_approval" → Genehmigung durch `test_flight_leader` in einer **separaten** Desktop-Session
  → "approved", "Zu DJI Pilot 2" wird sichtbar → Flugende-Wizard (Standort, Ja/Nein-Fragen, Notizen)
  → Status "completed" mit allen erwarteten Feldern → Zwei-Knopf-Ende-Bildschirm → "Selbe Person,
  neuer Flug" springt zurück zum Preflight, Bediener bleibt angemeldet. **Testmethodik-Erkenntnis
  (kein Anwendungsfehler):** ein Verifikationsskript, das in einem einzigen Python-Prozess sowohl
  HTTP-Aufrufe gegen den echten Dev-Server als auch eine zusätzliche, direkt im selben Prozess
  erzeugte `create_app()`-Instanz für DB-Zugriffe mischte, zeigte dadurch veraltete Zwischenstände
  bei nachfolgenden HTTP-Abfragen -- mit sauber getrennten Prozessen (exakt wie ein echter Browser +
  eine echte, separate Desktop-Genehmigung) verschwand der Effekt vollständig und alle Schritte
  liefen korrekt durch; die automatisierten Tests waren davon nie betroffen, da `pytest` durchgehend
  eine einzige App-Instanz nutzt.

Testsuite insgesamt: 205/205 grün (`pytest`, lokal gegen `fireflight2_test`).

- **Phase 13 — fachliche Dashboard-Module**: fertig und live verifiziert (Implementierung
  2026-07-23, Live-Verifikation am 2026-07-24 in einer neuen Session abgeschlossen -- Fortsetzung
  nach `git pull`, siehe „Nachtrag 2026-07-24" unten).

**Umgesetzt:** neuer `FireFlightModule.register_template_globals(app)`-Hook (`app/modules/base.py`,
`app/modules/registry.py`) -- Andockpunkt für Jinja-Globals, die Fachmodul-Widget-Templates brauchen,
da `context_processor`-Werte (`current_user`, `has_permission`) im `render_widget`-Makro nicht sichtbar
sind (nur echte Globals, exakt das schon in Phase 1 dokumentierte Muster). Zwei neue Widgets darüber
registriert:
- **Flugbuch-/Karten-Widget** (`incidents.flight_map`, Konzeptdokument Abschnitt 9 "Karte -- aktuelle
  Standorte der Piloten"): `app/modules/incidents/widgets.py: flight_map_widget_data()`, Template
  `app/templates/modules/incidents/_widget_flight_map.html`, kompakte Leaflet-Karte
  (`app/static/js/incidents_widget_map.js`, mehrinstanzfähig über `.incidents-widget-map` +
  `data-map-data`). `list_flights_with_location()` um `limit`-Parameter erweitert (neueste zuerst),
  Marker-Serialisierung in `services.serialize_flight_marker()` ausgelagert und von der vollen
  Kartenseite (`incidents.map_view`) UND dem Widget gemeinsam genutzt, damit beide nicht auseinanderlaufen.
- **"Technisches Problem melden"-Widget** (`tickets.report_form`, Konzeptdokument Abschnitt 9): Formular
  direkt im Dashboard (Titel/Beschreibung/Drohne/Foto), neue Route `POST /tickets/melden`
  (`app/modules/tickets/routes.py: widget_report()`) -- erstellt Ticket + optionales Foto in einem
  Aufwasch (anders als die bestehende `ticket_new`-Seite, die auf die Detailseite weiterleitet), Erfolg/
  Fehler per `flash()` statt eigener Seite.

Beide Widgets prüfen ihre Berechtigung (`incidents.view` bzw. `tickets.create`) selbst in Python
(`role_has_permission(get_active_role(), ...)`) statt sich auf `has_permission()` aus dem Template zu
verlassen -- aus demselben Grund wie oben (Makro-Include sieht keine context_processor-Werte).
`flask seed-test-data` hängt die Widgets exemplarisch an je ein Test-Dashboard (Flugleiter bekommt die
Karte, Pilot/Kamera das Melde-Formular) -- die eigentliche Dashboard-Zusammenstellung bleibt bewusst
Admin-Aufgabe (spec-struktur.md Abschnitt 4), das ist nur für Testdaten/Verifikation. 13 neue Tests
(`tests/test_module_widgets.py` neu, plus 1 in `tests/test_incidents.py` für den `limit`-Parameter).
Testsuite: **218/218 grün.** Keine Migration nötig (keine neuen DB-Spalten).

**Live-Verifikation:** Flugbuch-Karte-Widget gegen den echten Dev-Server bestätigt (2026-07-23) --
`test_flight_leader` eingeloggt, `/dashboard/` zeigt die echte, korrekt nach `limit` begrenzte
Marker-Liste mit realen Flugdaten aus der DB (inkl. `detail_url`, Pilot, Kamera-Operator).
Melde-Formular-Widget bestätigt korrekt zu rendern (`action="/tickets/melden"`, Titel-/Foto-Feld
vorhanden) auf `test_pilot_camera`s Dashboard.

**Nachtrag 2026-07-24 (neue Session, nach `git pull`):** der zuvor unterbrochene `POST
/tickets/melden`-Live-Test zu Ende geführt, per `curl` mit `X-CSRFToken`-Header (Desktop-Formulare
nutzen `hx-headers` statt eines Hidden-Fields, s. `base.html`) gegen den echten Dev-Server:
einmal ohne Foto, einmal mit einem echten 1×1-PNG (Magic-Byte-Validierung bestanden) -- beide Male
`302` zu `/dashboard/` mit Flash `"Meldung erstellt."`, per DB-Check bestätigt, dass Ticket
(inkl. bei Bedarf `TicketAttachment` + Datei unter `instance/uploads/ticket_attachments/`) korrekt
persistiert wurde. Beide Test-Tickets anschließend wieder aus der DB **und** vom Dateisystem
entfernt, um keine Testartefakte zu hinterlassen. Die zuvor erwähnten Alt-Testeinsätze
(`Live-Verifikation Übung`, `Live-Test-Einsatz`) waren in der lokalen Dev-DB **nicht mehr
auffindbar** (nur die beiden regulären `seed-test-data`-Einsätze vorhanden) -- Ursache nicht
geklärt (vermutlich in einer nicht dokumentierten Zwischen-Session bereits aufgeräumt oder DB
zwischenzeitlich neu aufgesetzt), Punkt damit ohne weiteres Zutun erledigt. Vor der Verifikation
musste die lokale Dev-DB erst per `flask db upgrade` von `c610af27d089` (Phase 6) auf
`49286e4006a0` (Phase 12, aktueller Head) gehoben werden -- die Migrationen der Phasen 7-12 waren
auf dieser Maschine noch nicht angewendet, da der zwischenzeitliche Fortschritt in einer anderen
Session/auf einem anderen Weg entstanden und erst per `git pull` auf diese Maschine gekommen war.
Testsuite unverändert 218/218 (keine Code-Änderung, nur Live-Test + Aufräumen).

Testsuite insgesamt (Ausbaustufe 2, Stand Phase 13): 218/218 grün.

- **Phase 14 — externe Dashboard-Module DWD-Wetter + OpenSky**: "schlanke Direktanbindung"
  (Nutzerentscheidung 2026-07-24, nach der Rückfrage zum Umfang -- explizit **kein** eigenes
  `app/integrations/`-Package, keine Mock-/Live-Client-Trennung, keine Admin-Konfigurationsseite,
  keine Sync-Jobs wie einst bei DJI FlightHub, das komplett wieder entfernt wurde). Zwei neue,
  eigenständige `FireFlightModule`s (`app/modules/weather/`, `app/modules/opensky/`), analog zum
  Widget-Muster aus Phase 13, aber ohne eigene Permission-Prüfung -- beide Datenquellen sind
  öffentliche, nicht organisationsbezogene Daten, jede Rolle mit dem Widget auf ihrem Dashboard
  darf es sehen.

  **Wetter-Widget** (`weather.current`): ruft [Bright Sky](https://brightsky.dev/) auf, einen
  freien Wrapper um die DWD-Open-Data-Schnittstelle (kein API-Key nötig), für den konfigurierten
  Standort (`WEATHER_LOCATION_LAT/LON`, Default Feuerwehr Liederbach am Taunus -- identisch mit dem
  seit Phase 9 verwendeten Karten-Fallback-Mittelpunkt). Zeigt die für Flugbetrieb relevante
  Teilmenge (Konzeptdokument: "relevant für Drohnenbetrieb"): Temperatur, Bedingung, Wind/Böen,
  Niederschlag, Bewölkung, Sicht, Messzeitpunkt (über `to_local()` aus Phase 9 in die
  Anzeige-Zeitzone konvertiert).

  **OpenSky-Widget** (`opensky.map`): ruft die freie OpenSky-REST-API anonym auf (kein Key, aber
  nur 400 Requests/Tag erlaubt), Bounding-Box um denselben Standort mit
  `OPENSKY_RADIUS_KM` (Default 50 km, Kleinwinkelnäherung statt Großkreisberechnung -- für diese
  Größenordnung ausreichend genau). Zeigt eine kompakte Leaflet-Karte (`app/static/js/
  opensky_widget_map.js`, lokal vendorte Leaflet-Instanz aus Phase 9 wiederverwendet) mit einem
  Marker je Luftfahrzeug mit aktueller Positionsmeldung (Rufzeichen/Höhe/Geschwindigkeit im
  Popup), gedeckelt auf `_MAX_AIRCRAFT = 30` Einträge -- kein theoretisches Limit: der reale
  Standort liegt nahe Frankfurt Airport, der Live-Test lieferte tatsächlich exakt 30 Flugzeuge
  im Radius (Cap also aktiv genutzt, nicht nur vorsorglich gesetzt).

  **Caching:** neues generisches `app/core/utilities/external_cache.py` (`cached(key, ttl,
  fetch)`), ein simpler In-Prozess-TTL-Cache ohne Redis/DB -- bewusste Vereinfachung passend zur
  "schlanken" Umfangsentscheidung. Cacht auch Fehlerfälle (verhindert Retry-Stürme bei einem
  API-Ausfall), mit der bekannten Einschränkung, dass mehrere Gunicorn-Worker im Produktivbetrieb
  je einen eigenen Cache hätten (für die geringe Nutzerzahl dieser App hingenommen). TTLs:
  `WEATHER_CACHE_SECONDS = 600` (DWD aktualisiert ohnehin nur stündlich), `OPENSKY_CACHE_SECONDS
  = 300` (begrenzt den Verbrauch auf max. 288 Requests/Tag selbst bei Dauerlast, mit Puffer unter
  dem 400er-Tageslimit).

  `requests` (bisher nur transitiv über `pywebpush`) zu `requirements.txt` ergänzt, da jetzt direkt
  verwendet. **Nebenfund beim ersten Testlauf:** das lokale `.venv` auf dieser Maschine hatte
  `tzdata` (seit Phase 9 in `requirements.txt`) nie tatsächlich installiert -- `to_local()` schlug
  beim Rendern des Wetter-Widgets prompt mit `ZoneInfoNotFoundError` fehl, da als erster Codepfad
  seit Phase 9 tatsächlich `ZoneInfo("Europe/Berlin")` in diesem venv auflöste. Kein Anwendungsfehler,
  reine venv-Drift (`pip install -r requirements.txt` nachgeholt).

  Keine Migration nötig (keine neuen DB-Spalten, keine Persistenz -- beide Widgets sind rein
  live-abgefragt+gecacht). 14 neue Tests (`tests/test_weather_widget.py`,
  `tests/test_opensky_widget.py`): Service-Erfolg/-Fehler/Cache-Verhalten mit gemocktem
  `requests.get` (kein echter Netzwerkzugriff in der automatisierten Suite), Widget-Registrierung,
  Dashboard-Rendering inkl. Fehlerzustand. Testsuite: **232/232 grün.** `flask seed-test-data`
  erweitert: beide Widgets zusätzlich zur Flugbuch-Karte auf dem Flugleiter-Test-Dashboard.

  **Live gegen den echten Dev-Server verifiziert** (2026-07-24, `test_flight_leader` eingeloggt,
  `/dashboard/`) -- **mit echten Aufrufen der echten öffentlichen DWD-/OpenSky-Endpunkte** (bewusst
  kein Mock: beides sind Lese-Endpunkte ohne Seiteneffekt, kein Push/Webhook mit Ziel-Domain-Risiko):
  Wetter-Widget zeigte reale Live-Messwerte (14,4 °C, trocken, Wind 6,5 km/h aus 80°, Böen
  11,5 km/h, 0 mm Niederschlag, 100 % Bewölkung, 42,6 km Sicht), OpenSky-Widget zeigte 30 reale
  Flugzeuge mit ICAO24-Adressen im Radius (Cap erreicht, s. o.). Keiner der beiden
  "nicht verfügbar"-Fehlerzustände wurde ausgelöst.

- **Phase 15 — Tests und Dokumentation**: letzte Phase des 15-Phasen-Restrukturierungsplans, im Repo
  selbst nur mit dem knappen Titel benannt (der volle Plantext liegt außerhalb des Repos, s. o.) --
  daher pragmatisch als "Testabdeckung prüfen + README/Architekturdoku auf den aktuellen
  Gesamtstand bringen" ausgelegt statt auf eine nicht mehr auffindbare Detailvorgabe zu warten.

  **`README.md` komplett überarbeitet**: war noch vollständig auf Ausbaustufe 1 stehen geblieben
  (Stand vor Phase 1), unter anderem mit der inzwischen falschen Aussage "vollständige fachliche
  Module... noch nicht enthalten". Neue Abschnitte für PIN-Login/Kontosperre, RC-PWA-Zugang,
  Wizard-System, Web-Push, die vier Fachmodule (Einsätze/Flugbuch, Tickets/Wartung, Wetter,
  OpenSky), Nutzerprofile/Drohneneinheiten und `flask seed-test-data`; Projektstruktur-Baum,
  Umgebungsvariablen-Tabelle (VAPID-Variablen ergänzt) und Tests-Abschnitt (232 statt 22 Tests) auf
  den aktuellen Stand gebracht. **Nebenfund dabei:** README verlangte bisher hart Python 3.12 für
  die lokale Entwicklung, das lokale `.venv` auf dieser Maschine läuft aber tatsächlich unter
  3.10.11 (Dockerfile/Produktion zielen weiterhin auf 3.12) -- als bekannte, nie geprüfte
  Diskrepanz dokumentiert statt einer der beiden Zahlen einfach zu vertrauen.

  **`docs/architecture.md` um einen neuen Abschnitt "Ausbaustufe 2 — Entscheidungen" ergänzt**: die
  über die Phasen verstreuten, weiterhin gültigen Architekturmuster gebündelt (Berechtigungsprüfung
  in Fachmodul-Widgets aus Python statt Template, die beiden Sidebar-/Landing-Navigation-Bugs aus
  Phase 9/10 als Lehre für künftige Module, RC-PWA-Doppel-Session-Modell, Wizard-Engine-Neutralität
  + `field_key`-Andockpunkt, Magic-Byte-Upload-Validierung, die Phase-14-Entscheidung "schlanke
  Direktanbindung" samt Cache-Strategie, punktuelle statt generelle CSP-Lockerungen) -- die
  chronologische Phase-für-Phase-Herleitung bleibt bewusst nur in dieser Roadmap-Datei, nicht
  dupliziert.

  **Testabdeckung geprüft:** keine dedizierte `tests/test_administration.py`, aber die
  Administrationsrouten sind über die jeweiligen Fachbereichs-Testdateien mitabgedeckt
  (Nutzerverwaltung in `test_auth.py`/`test_profile.py`, Rollenverwaltung in `test_roles.py`,
  RC-Geräte-/Einheiten-Verwaltung in `test_rc.py`/`test_units.py`, Dashboard-Editor in
  `test_dashboards.py`) -- keine echte Lücke gefunden, daher bewusst keine neuen Tests nur um
  eine separate Datei zu haben. Volle Suite nach den Doku-Änderungen erneut grün: **232/232.**

  **Bewusst nicht Teil dieser Phase:** die beiden weiterhin offenen, nur vom Nutzer selbst
  durchführbaren Punkte (Hardware-Verifikation auf der echten DJI RC Plus, Docker-Compose-Lauf) --
  s. "Als Nächstes" unten sowie `docs/architecture.md` Abschnitt "Verifikation der Ausbaustufe 2".

### Als Nächstes
Der 15-Phasen-Restrukturierungsplan ist damit inhaltlich vollständig umgesetzt. Verbleibend, beide
nur vom Nutzer selbst durchführbar (keine Entwicklungsaufgabe mehr):
1. **Hardware-Verifikation auf der echten DJI RC Plus** (Phase 4/5/12): Push-Rundlauftest im
   normalen Browser zuerst, danach PWA-Installation über `/rc/pair` → `/rc/home` mit einem der
   beiden `seed-test-data`-Testgeräte, Hintergrund-Push, DJI-Pilot-2-Deep-Link-URL ermitteln und in
   Administration → RC-Geräte eintragen, außerdem der komplette Preflight→Flugstart→Flugende-Zyklus
   auf echter Hardware.
2. **Docker-Compose-Lauf** (`docker compose up -d --build`) auf einer Maschine mit Docker, bisher
   nie getestet (Entwicklungsmaschine hat kein Docker installiert).

Offen und mit dem Nutzer zu klären: ob/wann eine "Büro-PWA" (Installierbarkeit der
Desktop-Oberfläche, Konzeptdokument Abschnitt 1) nachgezogen wird -- im 15-Phasen-Plan bisher
keiner Phase explizit zugeordnet.

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
