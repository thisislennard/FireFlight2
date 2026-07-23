# FireFlight2 – Projektübersicht für Claude Code

## Was ist FireFlight2?
Von-Grund-auf-Neuentwicklung von FireFlight (`G:\5 GitHub\FireFlight`) — Drohnenflug-Logbuch für Feuerwehren/BOS-Einheiten. **Kein Fork, kein Code-Import** — v1 dient ausschließlich als fachliche Referenz für den Funktionsumfang, nicht als Codebasis. Repo: `github.com/thisislennard/FireFlight2`.

v1 bleibt unangetastet produktiv unter `G:\5 GitHub\FireFlight`. Volle Architektur-/Security-/Design-Referenz von v1: `FireFlight/CLAUDE.md`, Nutzer-Feature-Liste: `FireFlight/README.md`.

**Vollständige Struktur-/Architektur-Vorgabe des Nutzers:** `docs/spec-struktur.md` (wörtliche Spezifikation vom 2026-07-19, Ausbaustufe 1). **Vollständige Design-Vorgabe:** `docs/spec-design.md` (Design-Tokens, Komponenten-CSS, Begründungen). **Konzeptvorgabe Ausbaustufe 2:** `fireflight2-konzept-struktur.md` (Fachmodule + PWA/Push, vom Nutzer 2026-07-23 geliefert) — daraus abgeleiteter Restrukturierungs-/Phasenplan wurde vom Nutzer freigegeben, liegt nicht im Repo. **Umsetzungsstand/Roadmap:** `docs/roadmap.md` — was aus welcher Ausbaustufe bereits implementiert und live verifiziert ist, was noch offen ist, was bewusst verschoben wurde. Vor jeder neuen Session zuerst dort nachsehen. Diese Datei hier fasst zusammen und verweist dorthin — bei Detailfragen zuerst dort nachsehen.

## Umsetzungsstand
Ausbaustufe 1 aus `docs/spec-struktur.md` ist **implementiert und lokal live verifiziert** (venv + lokales PostgreSQL, da auf dieser Maschine kein Docker installiert ist): Datenmodell, Auth, Rollen/Berechtigungen, Dashboards, Modul-Registry, Administration, CLI-Init, Templates/Design. Ausbaustufe 2 (Fachmodule + PWA/Push aus `fireflight2-konzept-struktur.md`) ist **in Arbeit** — Phase 1 (Modul-Registry-Bootstrap), Phase 2 (Rollen ohne Dashboard), Phase 3 (PIN-Login-Migration, Passwort komplett ersetzt), Phase 4 (Notifications-Kern, Web-Push), Phase 5 (RC-Hardware-Feasibility-Spike, reduzierter Umfang), Phase 6 (Drohneneinheiten), Phase 7 (Nutzerprofil-Erweiterung inkl. scharf geschaltetem RC-Qualifikationsfilter), Phase 8 (generische Wizard-Engine, noch ohne echte Fachinhalte), Phase 9 (Einsatz/Übung + Flugbuch mit Karte, erstes echtes Fachmodul über das Modul-Registry-System), Phase 10 (Tickets + Wartungsintervalle, Gerätewart als erste Rolle ohne Dashboard) und Phase 11 (Teilumfang: Zwei-Schritt-RC-Login) sind umgesetzt und getestet, weitere 4 Phasen (RC-Wizard-Inhalte inkl. Zwei-Knopf-Ende-Bildschirm, Dashboard-Module, externe Integrationen, Tests/Doku) stehen aus -- plus die weiterhin ausstehende Hardware-Verifikation auf der echten DJI RC Plus. Die eigentliche Hardware-Verifikation von Phase 4/5 (echter Browser-/RC-Push-Rundlauf auf der realen DJI RC Plus) ist noch offen — nur Code + automatisierte Tests + `curl`-Rundlauf gegen den Dev-Server sind verifiziert. Die zuvor implementierte DJI-FlightHub-2-Integration wurde am 2026-07-23 auf Nutzerwunsch **komplett wieder entfernt** (kein Fachmodul/keine Integration soll den Kern ablenken, bevor dieser fertig steht) — Details im Verlauf unten. Details, offene Punkte und nächste Schritte: `docs/roadmap.md`.

## Warum Neuentwicklung statt Weiterentwicklung von v1
- **Technische Basis modernisieren** — weg vom frameworklosen Python-Stdlib-HTTP-Server (`http.server.ThreadingHTTPServer`) aus v1
- **Architektur/Code-Qualität** — v1 ist über die Zeit gewachsen (viele Module, gemischte Patterns), FireFlight2 soll von Anfang an sauberer/konsistenter strukturiert sein
- **Feature-Set neu denken** — nicht nur Technik, auch der Funktionsumfang selbst wird überdacht; konkrete neue Features werden ergänzt, sobald besprochen

## Tech-Stack (final für Ausbaustufe 1, per Nutzer-Spezifikation 2026-07-19)
| Bereich | Entscheidung | Begründung |
|---|---|---|
| Backend | **Flask**, Application Factory + Blueprints | Wie in [LiFeOS](../LiFeOS) und [LayerOS](../LayerOS) statt v1s frameworklosem Ansatz oder FastAPI — Konsistenz mit anderen Projekten des Nutzers, vertrautes Ökosystem (Flask-Login, Flask-WTF/CSRF, SQLAlchemy) |
| Frontend | **Serverseitiges Rendering mit Jinja2 + HTMX** (o. ä. schlanke Technik) für dynamische Bereiche, JS nur wo nötig | **Ersetzt die frühere Antwort „Vanilla JS SPA wie v1"** — mit der detaillierten Struktur-Spezifikation hat sich der Nutzer für Server-Rendering statt SPA entschieden |
| Datenbank | **PostgreSQL** + SQLAlchemy, Migrationen über **Flask-Migrate/Alembic** | Löst v1s fehleranfälliges Migrationsmuster ab (s. „Bekannte Learnings" unten) |
| Architektur | **Modularer Monolith**: eine Flask-App, ein Kern (`app/core/`), klar getrennte interne Bereiche (`auth`, `roles`, `dashboards`, `integrations`, `administration`, `audit`, ...), internes **Modul-Registry-System** (`app/modules/`) für spätere Fachmodule. Schichtung Routes → Services → Repositories → SQLAlchemy | Keine Microservices, keine enge Kopplung; spätere Fachmodule (Einsätze, Flugbuch, Geräte, ...) sollen ohne Umbau andockbar sein. Details: `docs/spec-struktur.md` Abschnitt 2 |
| Deployment | **Docker + Docker Compose**, getrennte Container für App (Gunicorn, non-root) und PostgreSQL, Start über ein einziges `docker compose up -d --build` | Auf dem Host außer Docker/Compose keine weiteren Abhängigkeiten nötig |
| Multi-Tenancy | **Single-Tenant zum Start** — `organizations`-Tabelle existiert bereits als DB-Objekt (eine Zeile, z. B. „Feuerwehr Liederbach"), aber keine Organisationsauswahl, keine Mandantenfähigkeit | Explizite Nutzer-Entscheidung. v1s Schema-pro-Org-Modell (`org_<slug>` Postgres-Schema) wird **nicht** übernommen — falls später doch Multi-Tenancy gebraucht wird, `org_id`-Spalten-Modell statt Schema-pro-Org, weil v1 mit dem doppelten Migrationspfad (nummerierte Migration **und** `_org_alter_statements()` in `backend/superadmin/service.py`) ein dokumentiertes, wiederkehrendes Bug-Muster hatte (Änderungen kamen in echten Org-Schemas nicht an, siehe `FireFlight/CLAUDE.md`, Abschnitt „2026-07-14 — FlightHub-2-Ablösung: Umsetzung") |
| Design | **"Modernist"-Design-System** (Nutzer-Vorgabe, `docs/spec-design.md`) | v1s Theme (Dark-first, Orange-Akzent `#e07b39`) wird **nicht** übernommen. Hell (`#f3f2f2`), scharfe Kanten (0px Radius durchgehend), ein Akzent Rot-Orange (`#ec3013`), Schrift **Archivo** (800 Headings/400 Body), Status nie über Farbton sondern Füllstärke+Text+Icon, Icons **Lucide** (2px Stroke), Sidebar 220px Desktop → Bottom-Tab-Bar <760px, Darkmode als Nutzerwahl (Sonne/Mond-Toggle) |

## Kernkonzepte der Ausbaustufe 1 (Details: `docs/spec-struktur.md`)
- **Rollen als Arbeitskontext, nicht nur Rechte-Container** — echte Abkehr von v1: Nach Login wählt der Nutzer explizit „In welcher Funktion arbeitest du heute?" aus seinen zugewiesenen Rollen (Dokumentation, Einheitsführer, Pilot/Kamera, Flugleiter, Einsatzleiter/SBI, Gerätewart, TEL-ELW, Administrator — als DB-Datensätze, nicht hart codiert). Die gewählte Rolle bestimmt Dashboard, Navigation, Funktionsumfang und Berechtigungen der Sitzung; Wechsel jederzeit über Dropdown in der Kopfzeile ohne Re-Login. Bei nur einer Rolle optional automatisch übersprungen (Systemeinstellung)
- **Echtes Berechtigungssystem** — Rollen bündeln granulare Permissions (`dashboard.view`, `users.edit`, `roles.assign_permissions`, ...), geprüft über `@permission_required(...)`-Decorator **und** zusätzlich serverseitig im Service, nie nur UI-seitig. Kein Hardcoden von Rollennamen in Prüfungen
- **Datenbankbasierte, konfigurierbare Dashboards pro Rolle** — Widget-Raster (12-Spalten), Admin-Editor zum Hinzufügen/Bearbeiten/Positionieren von Basiswidgets (Überschrift, Info, Schnellzugriff, Status, Kennzahl, Hinweis, Warnung, Platzhalter). Fachliche Widgets kommen erst mit späteren Modulen
- **Externe Integrationen (z. B. DJI FlightHub 2) aktuell komplett entfernt** — ursprünglich als „zentrale Datenquelle, nicht Nebenmodul" mit eigener Integrationsschicht (`app/integrations/`) konzipiert, wurde die einzige bestehende Implementierung (DJI-FlightHub-2, inkl. Mock-/Live-Client) am 2026-07-23 auf Nutzerwunsch komplett entfernt, um zunächst eine integrationsfreie Basis fertigzustellen (s. Verlauf unten, `docs/architecture.md`). Herkunft von Daten wird weiterhin generisch über `external_references` modelliert (Tabelle bleibt bestehen, ist nicht integrationsspezifisch) — das Prinzip „Fachmodule sprechen nie direkt mit einer externen API" gilt unverändert, sobald wieder eine Integration existiert. Recherche-Referenz falls DJI FlightHub 2 zurückkommt: `docs/dji-flighthub2-api.md`
- **Modul-Registry statt fertiger Fachmodule** — Einsatzverwaltung, Flugbuch, Geräte-/Akkuverwaltung, Karten, Medien, Wartung, Wiki usw. werden in dieser Phase **bewusst nicht gebaut** (siehe v1-Referenzliste unten als spätere Kandidaten). Stattdessen ein `FireFlightModule`-Basisklassen-System (`app/modules/base.py`, `registry.py`), das später Blueprints, Navigation, Permissions, Widgets und Datenmodelle sauber andocken kann

## Offene Punkte (werden ergänzt, sobald besprochen)
- Exakte Dark-Mode-Farbwerte des Design-Systems (im Guide nur Light-Mode-Tokens geliefert, siehe `docs/spec-design.md` Abschnitt „Farben")
- Reihenfolge/Priorität der späteren Fachmodule (Einsatzverwaltung, Flugbuch, Geräte, ...)
- Ob v1s 2FA/TOTP übernommen wird (in der Struktur-Spezifikation nicht erwähnt)
- Ob/wann Multi-Tenancy nachgerüstet wird

## FireFlight v1 – Fachliche Referenz (Funktionsumfang als Ausgangsbasis)
Vollständige Liste: `FireFlight/README.md`, Abschnitt „Funktionen". Kurzfassung als Orientierung, **nicht** automatisch 1:1 Scope für FireFlight2:

- **Flugbuch**: Datum, Start-/Endzeit, Dauer (automatisch berechnet + Plausibilitätsprüfung), Pilot, Kamera-Operator, Drohne, Akku, Zweck, Wetter, Wind, Projekt, Notizen, Anhänge; Liste mit Suche/Filter/Sortierung, CSV-Export, PDF-Druck über Browser
- **Drohnenverwaltung**: Modell, Seriennummer, Inventarnummer, Standort, Status, Streams, Verbrauchsmaterial, Notizen
- **Akkuverwaltung**: Ladezyklen, maximale Zyklen, Status, letzte Ladung
- **Tickets**: Drohnenprobleme mit Kommentaren, Drag-and-drop-Bildanhängen
- **Wartung**: Regeln + Ereignisse mit Fälligkeiten/Warnfristen
- **Statistik-Dashboard**: Flugzeiten, Einsätze, Piloten, Drohnen
- **Wiki/Dokumentation**: Kategorien, Status, Versionen, Verantwortliche, Rollenfreigaben, Dateianhänge
- **DJI-FlightHub-2-Anbindung** (Business-OpenAPI): Geräte+HMS-Status, Flüge/Tasks mit GPS-Track, Medien-Galerie, Flugrouten (Waylines), Live-Videostream (WebRTC/WHEP), Import in eigenes Flugbuch. Volle Endpunkt-Referenz: `docs/dji-flighthub2-api.md`
- **Livestream-Seite** für Drohnenstreams mit Nutzerfreigaben
- **Verbesserungsvorschläge**: Nutzer reichen ein, Admin/Superadmin verwaltet Status+Antwort
- **Auth/Rechte**: Session-Cookie + CSRF, optionale 2FA (TOTP), Rollen mit Boolean-Flags **und** granularem CRUD-Modell pro Modul
- **Audit-Log** für wichtige Aktionen (pseudonymisierte Akteure)
- **Backup/Restore**, Update-Upload-Mechanismus (SHA-256-verifiziertes ZIP, automatisches Backup ersetzter Dateien)
- **Superadmin-Bereich**: Systemverwaltung, Organisationsverwaltung, Lizenzverwaltung, globale Nutzungsbedingungen, DB-/Sicherheitseinstellungen — relevant nur falls Multi-Tenancy später kommt; im Single-Tenant-Start entfällt die Org-Verwaltung, ein normaler Admin-Bereich reicht
- **Rehkitzrettung (RKR)**-Modul — Sonderfunktion, fachlicher Zweck vor Übernahme klären
- Responsive UI, Dark Mode, Logo/Favicon/Branding-Einstellungen

## Bekannte Learnings aus v1 (worauf in FireFlight2 geachtet werden sollte)
- **Migrations-Doppelpflege bei Schema-pro-Org** war fehleranfällig (Änderungen wirkten nur im ungenutzten `public`-Schema) → deshalb bewusste Entscheidung gegen dieses Modell für FireFlight2 (s. Tabelle oben)
- **DJI-FlightHub-2 Business-API**: `https://fh.dji.com` ist **nachweislich nicht** die API-Basis-URL — 2026-07-22 per echtem Verbindungstest bestätigt (`GET /openapi/v0.1/system_status` liefert HTML statt JSON, auch ohne Auth-Header; Response-Header zeigen reines S3/CloudFront-Static-Hosting, keine Server-Logik möglich). Die echte API-Basis-URL ist laut dem JS-Bundle der Web-Oberfläche account-/regionsspezifisch und wird erst nach Login dynamisch ermittelt (`window.CURRENT_BE_ENV_CONFIG.server_url`) — nicht von außen erratbar, muss über Browser-DevTools (F12 → Netzwerk, Host eines echten API-Requests ablesen) ermittelt werden. Damit ist die ursprüngliche Notiz zu einem regionsspezifischen Gateway im Kern bestätigt (exakter Hostname aber weiterhin offen). v1s Code (`FireFlight/backend/modules/flighthub/service.py`) und FireFlight2s bisheriger Default nutzten fälschlich `fh.dji.com` — Details und Nachweis: `docs/dji-flighthub2-api.md`. Bestätigt: Jeder Request braucht `X-Request-Id`-Header (UUID) sowie `X-Language`. Ob leere Listen `"list": null` statt `[]` liefern, ist in der aktuellen Doku nicht explizit dokumentiert — beim Parsen defensiv bleiben (`(x.get("data") or {}).get("list") or []`).
- **CSP von v1** verbietet Inline-JS (`script-src 'self'`) — falls übernommen: alle Skripte als eigene Dateien unter `js/`, kein Inline-`<script>`
- **Passwort-Hashing** in v1: PBKDF2-HMAC-SHA256, 120.000 Iterationen, 16-Byte-Salt — als Mindeststandard falls kein Framework-Default (z. B. Flask-Bcrypt) gewählt wird

## Verlauf / Planungsentscheidungen
### 2026-07-23 (Fortsetzung) — Phase 11 (Teilumfang): Zwei-Schritt-RC-Login umgesetzt
Auf "starte erstmal lokal" (Dev-Server gestartet, Admin-PIN auf Nutzerwunsch auf `1234` gesetzt --
lokal bewusst trotz Denylist trivialer PINs, direkt in der DB) und danach "okay cool dann mach mal
weiter" begonnen. Vollständige Details in `docs/roadmap.md` Abschnitt „Status: Ausbaustufe 2".

Bewusst nur den Login-Flow aus Konzeptdokument Abschnitt 5.1 umgesetzt (Schritt 1: qualifikationsgefilterte
Nutzerliste zum Antippen; Schritt 2: nur noch PIN für den bereits ausgewählten Nutzer), **nicht** den
Zwei-Knopf-Ende-Bildschirm aus Abschnitt 5.6 -- der gehört zum Ende eines Wizard-*Laufs*, und ohne
echte RC-Wizard-Inhalte (erst Phase 12) gäbe es dafür noch keinen sinnvollen Auslösepunkt.

**Zwei echte Funde dabei:** (1) Das "Person wechseln"-Formular auf `rc/home.html` hatte noch nie
einen CSRF-Token -- RC-Seiten haben kein `hx-boost` wie die Desktop-App, das den Header automatisch
injiziert, und es war ein rohes Formular ohne `hidden_tag()`. In einem echten Browser wäre das mit
400 Bad Request fehlgeschlagen; alle bisherigen Live-Verifikationen dieser Session hatten den Header
selbst per `curl`/`requests` nachgebaut und den Bug damit verdeckt. Behoben, neue rohe RC-Formulare
bekamen von Anfang an ein `csrf_token`-Feld. (2) `manifest-rc.webmanifest` hatte nur ein 160×160-Icon
-- für Chromes Installierbarkeits-Kriterien ergänzt um 192×192/512×512 (mit Pillow hochskaliert, nur
als Build-Zeit-Werkzeug, nicht in `requirements.txt`).

**Bewusst nicht angegangen, da neu entdeckte, im 15-Phasen-Plan nirgends verortete Lücke:** Die
"Büro-Nutzung" (Konzeptdokument Abschnitt 1: "mit Möglichkeit zur Installation als PWA") hat noch
kein eigenes PWA-Manifest -- nur die RC-Seite ist installierbar. Mit dem Nutzer zu klären statt
stillschweigend mit hineinzuwachsen.

`tests/test_rc.py` komplett auf den neuen Zwei-Schritt-Flow umgeschrieben (ein `_login_two_step()`-
Helper ersetzt alle direkten `identifier`+`pin`-Posts), fünf neue Tests. **Live gegen den echten
Dev-Server verifiziert:** Schritt 1 zeigt nur qualifikationsgefilterte Kandidaten, Auswahl führt zu
Schritt 2, falsche PIN bleibt mit Fehlermeldung auf Schritt 2, richtige PIN führt zu `/rc/home`,
"Anderer Nutzer" springt zurück zu Schritt 1. Testsuite 187/187 grün, kein neues DB-Modell.

### 2026-07-23 (Fortsetzung) — Phase 10: Tickets + Wartungsintervalle umgesetzt
Auf "ja mach weiter" direkt im Anschluss an Phase 9 begonnen. Vollständige technische Details in
`docs/roadmap.md` Abschnitt „Status: Ausbaustufe 2". Zweites Fachmodul über das Modul-Registry-System
(`app/modules/tickets/`) -- Tickets sind bewusst breit zugänglich (Konzeptdokument Abschnitt 9 rahmt
"Technisches Problem melden" als Dashboard-Funktion für jede Crew), Verwalten/Wartung ist
Gerätewart-Domäne (Abschnitt 10: "Rollen ohne Dashboard").

**Gerätewart wird die erste Rolle, die tatsächlich kein Dashboard hat** -- die Infrastruktur dafür
(`Role.landing_endpoint`, `roles/no_landing.html`) stammt aus Phase 2, wurde aber bis jetzt nie mit
einer echten Rolle durchgespielt. Dabei zwei weitere latente Lücken gefunden (exakt dasselbe Muster
wie die zwei Navigation-Bugs aus Phase 9 -- Infrastruktur, die beim Bauen plausibel aussah, aber nie
mit einem echten Fall getestet wurde): (1) der "Dashboard"-Link in der Sidebar war nie
berechtigungsgeprüft, jetzt hinter `has_permission('dashboard.view')`. (2) `_resolve_role_landing()`
(`app/roles/routes.py`) prüfte bei einem individuellen `landing_endpoint` nur, ob sich die Ziel-URL
bauen lässt, nicht ob die Rolle dort eine Berechtigung hat -- unproblematisch, solange
`landing_endpoint` nur über den bereits Permission-gefilterten Admin-Editor gesetzt wurde, aber
`seed_roles()` setzt es jetzt auch bei der Erstanlage, und Berechtigungen ändern sich danach
unabhängig. Fix so eng wie möglich gehalten: nur für Ziele mit einem bekannten
`ModuleRegistry.navigation`-Eintrag wird die Berechtigung geprüft; für alles andere (z. B.
`administration.audit_log` von Hand als Landing-Ziel gesetzt) bleibt das alte, permissivere Verhalten
-- ein bestehender Phase-2-Test (`test_role_with_custom_landing_endpoint_redirects_there`) verlangt
genau das und sollte nicht angepasst werden müssen, nur weil ein neuer Anwendungsfall dazukam.

Ticket-Fotoanhänge nutzen dieselbe Magic-Byte-Validierung wie Profilbilder aus Phase 7
(`app/core/utilities/uploads.py` generalisiert: `MAX_IMAGE_BYTES` als neue Basis-Konstante,
`MAX_PROFILE_IMAGE_BYTES` bleibt als Alias erhalten, damit `tests/test_profile.py` unverändert bleibt),
aber mit zufälligen statt festen Dateinamen (mehrere Anhänge pro Ticket möglich). Kein neues
Docker-Volume nötig, liegt unter demselben `instance_path`-Volume aus Phase 7.

`flask maintenance check-due` (neue CLI-Gruppe) ist der Fälligkeits-Check aus Konzeptdokument
Abschnitt 10 -- diese App hat keine eingebaute Zeitsteuerung, daher für externen Cron gedacht. Schickt
eine zusammengefasste Nachricht pro Lauf (nicht eine pro fälliger Regel), an alle Nutzer mit
`maintenance.manage`-Berechtigung, über Rollen dedupliziert.

**Live verifiziert** gegen den echten Dev-Server: Login als Gerätewart landet direkt auf `/tickets/`
(kein Dashboard-Link mehr im Menü), Ticket samt Fotoanhang über eine Pilot/Kamera-Rolle angelegt
(Statusänderung dort korrekt mit 403 abgewiesen, nur Gerätewart darf), Wartungsregel angelegt und als
erledigt gemeldet, `flask maintenance check-due` erst mit sauberer Fehlermeldung ohne
VAPID-Konfiguration, danach erfolgreich mit echten Schlüsseln (3 benachrichtigte Nutzer). **Beim
Live-Testen selbst ein Fehler gemacht:** ein zu grobes Regex beim Auslesen der aktuell gesetzten
Rollen-Berechtigungen aus der Editor-Seite lieferte eine leere Liste, wodurch ein Test-Speichervorgang
versehentlich alle Gerätewart-Berechtigungen entfernt hat -- durch erneuten `flask init-fireflight`-Lauf
sofort repariert (`seed_roles()` setzt Berechtigungen bei jedem Lauf zurück, s. Phase-2-Doku), keine
Auswirkung auf Code oder Tests. Testsuite 182/182 grün (32 neue Tests in `tests/test_tickets.py`;
`tests/test_roles.py` blieb dabei bewusst unverändert -- die präzisierte Landing-Logik wurde so eng
geschnitten, dass beide betroffenen bestehenden Tests dort ohne Anpassung weiter grün sind). Migration
`31acde4e81fe` gegen die reale Dev-DB angewendet, Drift-Check zeigt nur die bekannten DJI-Alttabellen.

### 2026-07-23 (Fortsetzung) — Phase 9: Einsatz/Übung + Flugbuch (mit Karte) umgesetzt
Auf "ja dann weiter" direkt im Anschluss an Phase 8 begonnen. Vor der Umsetzung zwei Rückfragen
gestellt, da das Konzeptdokument (Abschnitt 6/7) Einsatz/Übung und Logbuch nur sehr knapp beschreibt
und der 15-Phasen-Plan keine eigene Drohnen-/Akkuverwaltungs-Phase vorsieht, obwohl ein Flugbuch
klassischerweise referenziert, welche Drohne geflogen ist: Nutzer entschied sich für Drohne/Akku als
**Freitextfeld** (kein Geräte-Modul vorhanden, später migrierbar) und für Flugbuch-Felder, die sich an
dem orientieren, was der künftige RC-Wizard erfassen wird (Konzeptdokument Abschnitt 5.2-5.5) — **mit
der zusätzlichen Anforderung**, dass der Standort durchgehend auf einer Karte angezeigt wird und alles
auch manuell über Desktop gepflegt werden kann, nicht erst über den RC-Wizard (der erst in Phase
11/12 kommt).

Vollständige technische Details in `docs/roadmap.md` Abschnitt „Status: Ausbaustufe 2". Wichtigste
Punkte: erstes Fachmodul über das seit Phase 1 vorbereitete, aber nie real genutzte Modul-Registry-
System (`app/modules/incidents/`) — dabei zwei latente Bugs in `app/templates/base.html` gefunden und
behoben, die nur auffallen konnten, sobald `module_navigation` erstmals einen echten Eintrag enthielt:
(1) die Sidebar rendert `entry.endpoint` als rohen `href`, nicht über `url_for()`; (2) der Navigation-
Loop filterte gar nicht nach der Berechtigung des Eintrags — jeder eingeloggte Nutzer hätte jeden
Modul-Link gesehen, unabhängig von Rechten. Karte: Leaflet 1.9.4 lokal vendored (kein CDN), CSP
`img-src` um `tile.openstreetmap.org` erweitert (die einzige externe Abhängigkeit — Kartenkacheln
selbst, nicht Script/Connect). **Nebenfund, echter Bug:** `to_local()` existierte seit Ausbaustufe 1,
wurde aber bis zu diesen Templates nie tatsächlich aufgerufen — `ZoneInfo("Europe/Berlin")` schlägt
ohne das `tzdata`-PyPI-Paket fehl (Windows hat kein System-Tzdata, vermutlich auch das schlanke
`python:3.12-slim`-Docker-Image nicht) — `tzdata==2026.3` ergänzt, behebt es für Produktions- und
Dev-Umgebung gleichermaßen.

**Live verifiziert** gegen den echten Dev-Server: Sidebar-Link erscheint/verschwindet korrekt je nach
`incidents.view`-Berechtigung (Regressionstest für beide Navigation-Bugfixes), Einsatz+Flug komplett
manuell über Desktop angelegt (inkl. Standort), Abschließen/Wiedereröffnen, Karte lädt mit
eingebetteten Koordinaten und korrektem CSP-Header, Logbuch zeigt Testdaten-Personen mit korrekten
Einsatz-/Übungs-Zählungen, 403 für eine Rolle ohne `incidents.*`-Berechtigung bestätigt. Testsuite
156/156 grün (39 neue Tests in `tests/test_incidents.py`). Migration `6fedb0635366` gegen die reale
Dev-DB angewendet, Drift-Check zeigt nur die bekannten DJI-Alttabellen (wie bei allen vorherigen
Phasen bewusst nicht gedroppt).

### 2026-07-23 (Fortsetzung) — Phase 8: Wizard-Engine (generisch) umgesetzt
Auf "okay dann mach mal weiter" direkt im Anschluss an Phase 7 begonnen. Als Vorlage diente das
Dashboard-Widget-System (`app/dashboards/`) — architektonisch am nächsten dran: eine Registry
konfigurierbarer Bausteintypen + eine JSONB-`config`-Spalte pro Instanz + Admin-CRUD. Vollständige
technische Details in `docs/roadmap.md` Abschnitt „Status: Ausbaustufe 2".

Wichtigste Scope-Entscheidung: Phase 8 liefert **nur die generische Engine** (`Wizard`/`WizardStep`,
fünf generische Step-Typen: `info`/`checklist`/`confirmation`/`text_input`/`choice`, Admin-Builder,
Admin-Vorschau), nicht die konkreten Preflight-/Flugstart-/Flugende-Inhalte aus dem Konzeptdokument
Abschnitt 5.2-5.5 — die Roadmap führt „Phase 8 Wizard-Engine" und „Phase 12 RC-Wizard-Inhalte" explizit
getrennt, letztere setzt Phase 9 (Einsatz/Übung) und Phase 11 (RC-PWA-Vollausbau) voraus, an die ein
echter Lauf andocken kann. Bewusst kein `location`-Step-Typ (GPS+Zeit-Auto-Erfassung) — ohne echten
Konsumenten wäre die Browser-Geolocation-JS-Anbindung unverifizierbar spekulativ gewesen. Bewusst auch
kein Zwei-Knopf-Ende-Bildschirm ("Selbe Person, neuer Flug"/"Komplett neu") und keine client-seitige
Button-Deaktivierung per JS — beides RC-Kiosk-Politur, die serverseitige Gate-Prüfung erfüllt die
fachliche Anforderung ("Weiterkommen erst möglich, wenn bestimmte Aktionen ausgeführt wurden") bereits
vollständig.

`app/wizards/runner.py: WizardRunner` ist bewusst generisch auf ein beliebiges mutable Zustands-Dict
geschrieben (aktuell die Flask-Session für die Admin-Vorschau) statt direkt an ein DB-Modell gebunden —
ein echter RC-Lauf mit Flugbuch-Persistenz (Phase 9/12) kann dieselbe Validierungslogik mit einem
anderen Zustands-Backend wiederverwenden, ohne dass zum jetzigen Zeitpunkt schon geraten werden musste,
wie Phase 9 ihre Datenhaltung gestaltet.

**Live verifiziert** gegen den echten Dev-Server: kompletter 5-Schritt-Durchlauf des per
`seed-test-data` angelegten Beispiel-Wizards (Info → Checkliste mit Gate-Test unvollständig/vollständig
→ Auswahl → Freitext mit Pflichtfeld-Gate-Test → Bestätigung → Abschluss-Bildschirm → Reset), 403 für
Nutzer ohne `wizards.*`-Berechtigung. **Nebenfund:** ein per `curl` unter Windows Git Bash übergebener
Umlaut ("Übung") kam serverseitig verstümmelt an — mit Pythons `requests`-Bibliothek reproduzierbar
korrekt, also ein Encoding-Artefakt des `curl`-Testwerkzeugs auf dieser Maschine, kein Anwendungsfehler
(Formulardaten werden serverseitig korrekt als UTF-8 dekodiert). Testsuite 139/139 grün (30 neue Tests
in `tests/test_wizards.py`). Migration `bfe16e421ba5` gegen die reale Dev-DB angewendet, Drift-Check
zeigt nur die bekannten DJI-Alttabellen (Autogenerate schlug erneut deren Drop vor — wie bei
`ad2f3b109171`/`f07570aabbd1` bewusst nicht übernommen).

### 2026-07-23 (Fortsetzung) — Phase 7: Nutzerprofil-Erweiterung umgesetzt
Auf "schau dir die Roadmap an und arbeite weiter" begonnen. Der Restrukturierungsplan mit den
Phase-7-Details liegt nicht im Repo; als Quelle diente stattdessen `fireflight2-konzept-struktur.md`
Abschnitt 8 ("Nutzerprofil") + Abschnitt 5.1 ("Qualifikation"), auf Nutzerhinweis noch einmal gezielt
gelesen. Vollständige technische Details in `docs/roadmap.md` Abschnitt „Status: Ausbaustufe 2".

Kernentscheidung: `User.is_pilot`/`is_camera_operator` als zwei Booleans (nicht wie `unit_managers`
eine m:n-Tabelle) — es gibt nur die zwei im Konzept benannten Werte, ein User kann laut Konzept beide
gleichzeitig haben. `RcDevice.required_qualification` war seit Phase 5 nur ein unausgewertetes Feld
(sogar die eigene Validierungskonstante `DEVICE_KEY_VALID_QUALIFICATIONS` in `app/rc/services.py` wurde
nie benutzt) — beides jetzt scharf geschaltet: `create_device()` validiert dagegen, `rc.login()` prüft
nach korrekter PIN zusätzlich die Qualifikation und weist bei Nichterfüllung ohne Fehlversuchszähler ab
(kein Bruteforce-Indiz). Bewusst NICHT gebaut: das im Konzept beschriebene Zwei-Schritt-„User aus
Liste wählen, dann PIN"-UI für den RC-Login — das bleibt beim bestehenden einstufigen Username+PIN-Login
aus Phase 5, der neue Zwei-Schritt-Flow ist als Umfang für Phase 11 (RC-PWA-Vollausbau) vorgesehen, nicht
Phase 7.

Neues Kern-Package `app/profile/` für Self-Service (E-Mail, Telefonnummer, Profilbild) plus
read-only Übersicht (Heimateinheit/verwaltete Einheiten aus Phase 6, Funktion, Rollen) — abgegrenzt von
den Admin-verwalteten Feldern (Rollen, Heimateinheit, Qualifikation bleiben in
`administration/users/<id>`), exakt der Trennung "persönliche Daten" vs. "Übersicht" aus dem
Konzeptdokument folgend. Profilbild-Upload ist komplett neue Infrastruktur (`app/core/utilities/uploads.py`)
— vorher gab es im Projekt keinerlei Datei-Upload (das `Organization.logo_path`-Feld existierte bereits,
aber ohne jede Upload-Route). Validiert per Magic-Bytes statt Dateiendung/Content-Type (verhindert z. B.
eine umbenannte Nicht-Bild-Datei), max. 5 MB, ein Bild pro User. Neues Docker-Volume
`fireflight2-uploads-data:/app/instance`, damit Profilbilder Container-Rebuilds überleben — `Dockerfile`
legt das Zielverzeichnis vor dem `chown` an, weil Docker beim ersten Mounten eines named volumes Inhalt
und Rechte aus dem bereits im Image vorhandenen Verzeichnis übernimmt.

**Live verifiziert** gegen den echten Dev-Server (venv + lokales PostgreSQL): Admin setzt Qualifikation
über die neuen Checkboxen in `administration/users/<id>` → RC-Gerät mit passender Qualifikation lässt
den Login zu, mit fehlender Qualifikation weist es mit eigener Fehlermeldung ab → Self-Service-Profil
(E-Mail/Telefon geändert, echtes PNG hochgeladen und mit korrektem `Content-Type` wieder abgerufen,
Bild entfernt → danach 404). **Nebenfund dabei:** das PIN des lokalen `admin`-Testaccounts wich von der
Dokumentation ab (vermutlich aus einer früheren manuellen Sitzung) — lokal auf `4726` zurückgesetzt,
kein Code-Bug. Testsuite 111/111 grün (23 neue Tests: `tests/test_profile.py` neu, `tests/test_rc.py`
um Qualifikationsfilter-Fälle ergänzt). Migration `f07570aabbd1` gegen die reale Dev-DB angewendet,
Drift-Check zeigt nur die bekannten DJI-Alttabellen (wie schon bei `ad2f3b109171`, Autogenerate schlug
erneut deren Drop vor — bewusst nicht übernommen).

### 2026-07-19 — Projektstart, erste Architekturentscheidungen
Nutzer möchte FireFlight komplett neu bauen (kein Fork/Weiterentwicklung), Ordner `FireFlight2` existierte bereits mit GitHub-Remote. In einer Planungssession (Plan-Mode) wurden folgende Grundsatzentscheidungen getroffen: Backend Flask (statt v1s Stdlib-Server oder FastAPI), Multi-Tenancy wird vorerst komplett weggelassen (nur eine Organisation), Design-System wird komplett neu entworfen statt v1-Theme zu übernehmen. Motivation für den Neuanfang: technische Basis modernisieren, Architektur/Code-Qualität verbessern, Feature-Set neu denken.

### 2026-07-19 — Vollständige Struktur-Spezifikation vom Nutzer erhalten
Nutzer hat eine sehr detaillierte, 28 Abschnitte umfassende Architektur-/Struktur-Vorgabe geliefert (wörtlich gesichert in `docs/spec-struktur.md`). Kernpunkte gegenüber der ersten Planungsrunde **präzisiert bzw. geändert**: Frontend ist **nicht** Vanilla-JS-SPA wie ursprünglich beantwortet, sondern serverseitiges Jinja2-Rendering + HTMX; Multi-Tenancy-Entscheidung bestätigt (Single-Tenant, `organizations`-Tabelle existiert aber schon); neu dazugekommen sind das Rollen-als-Arbeitskontext-Konzept (Rollenauswahl nach Login, sitzungsweiter Rollenwechsel), das Dashboard-Widget-System pro Rolle, das Modul-Registry-System für spätere Fachmodule und die DJI-FlightHub-2-Integrationsarchitektur als zentrale, aber in Phase 1 gemockte Datenquelle. Vollständige Zusammenfassung in den Abschnitten oben. Design-Vorgabe wurde zunächst als Link (`claude.ai/design/...`) angekündigt, war aber nicht automatisch abrufbar (HTTP 403) — Nutzer hat den Design Guide danach direkt als Datei eingefügt. Nutzer hat angewiesen, in der Zwischenzeit mit der Umsetzung der nicht design-abhängigen Teile (Projektgrundlage, Docker, Auth, Rollen/Berechtigungen) zu beginnen.

### 2026-07-19 — Design-Spezifikation erhalten
Nutzer hat den vollständigen Design Guide geliefert (claude.ai Design-Tool-Export, HTML-Bundle). Relevanter Inhalt (CSS-Tokens, Komponenten-Klassen, Begründungstexte) extrahiert nach `docs/spec-design.md`; Bundler-Runtime/Font-Binärdaten/React-Bundles aus dem Export nicht übernommen (irrelevant für Umsetzung). Design-System-Name im Export: "Modernist" — hell, scharfkantig (0px Radius durchgehend), ein Akzent (`#ec3013`, Rot-Orange, passend zum Feuerwehr-Flammen-Logo), Schrift Archivo, Icons Lucide, Status-Codierung bewusst monochrom über Füllstärke statt Farbton. Deckt sich mit der früheren Nutzer-Entscheidung „komplett neues Design-System, nicht v1-Theme übernehmen". Einzige Lücke: Dark-Mode-Farbwerte nicht im Guide enthalten, nur die Umsetzungsregel (gleiche Variablen am Root überschrieben, Akzent bleibt gleich).

### 2026-07-22 — DJI FlightHub 2 OpenAPI vollständig recherchiert, echte Anbindung als nächstes Ziel
Nutzer möchte `MockDJIFlightHubClient` durch eine echte Anbindung ersetzen, erster Schritt: in der Administration sehen, welche Infos die DJI-API überhaupt liefert (rein lesend, vor Steuerfunktionen). Komplette Endpunkt-Doku der Business-OpenAPI recherchiert (Apifox-Doku ist eine JS-SPA, Zugriff nur über die `llms.txt`-Konvention möglich — Methode und alle 41 Endpunkte/9 Kategorien dokumentiert in `docs/dji-flighthub2-api.md`). Dabei zwei ältere Notizen in diesem Dokument korrigiert: die vermutete `djigate.com`-Gateway-URL und der `FireFlight/docs/FLIGHTHUB2_API.md`-Verweis ließen sich weder im v1-Code noch in der aktuellen Doku bestätigen (Datei existiert nicht; v1 nutzt `fh.dji.com` direkt als Cloud-Basis-URL). Bestätigt: `X-Request-Id`-Header ist Pflicht, v1 setzt ihn bisher nicht. Empfehlung aus der Recherche für die erste Umsetzungsstufe: Geräte/HMS/Flugaufgaben(inkl. Media+Track)/Waylines rein lesend, Livestream danach, Annotation/3D-Modelle/Open-Modeling nachrangig. Konkreter Umsetzungsplan (Credential-Speicherung, echter Client, Settings-Seite, DSGVO-Gate wie in v1) stand als nächster Schritt noch aus.

### 2026-07-22 (Fortsetzung) — Umsetzung, projektübergreifend umgebaut, Basis-URL-Problem bestätigt
Echte Anbindung umgesetzt: `LiveDJIFlightHubClient` (nur lesende Endpunkte) neben `MockDJIFlightHubClient`, Zugangsdaten-Formular in der Administration (nicht nur Env-Variablen — Nutzerkorrektur, s. `docs/architecture.md`). Danach zweite Korrektur durch den Nutzer: eine DJI-Organisation kann mehrere Projekte haben, daher project_uuid als Parameter statt fester Konstruktor-Wert, Projekte werden automatisch über `list_projects()` erkannt statt manuell eingetragen (s. `docs/architecture.md`, `docs/roadmap.md`).

Beim ersten echten Verbindungstest mit echten Zugangsdaten: Fehler "Server antwortete mit HTML statt JSON". Direkter Test von `https://fh.dji.com/openapi/v0.1/system_status` (auch ganz ohne Auth) bestätigte: der Host liefert nur eine statische Vue-SPA (S3/CloudFront, kein Backend möglich). Die echte API-Basis-URL wird laut JS-Bundle der Web-Oberfläche erst nach Login account-/regionsspezifisch ermittelt, ist also nicht von außen erratbar — Nutzer muss sie einmalig per Browser-DevTools ermitteln. Details: `docs/dji-flighthub2-api.md`, Abschnitt „https://fh.dji.com ist NICHT die API-Basis-URL".

### 2026-07-23 — Ausbaustufe 2: Konzeptdokument, Restrukturierungsplan, erste zwei Phasen umgesetzt
Nutzer hat `fireflight2-konzept-struktur.md` geliefert — ein 10-Abschnitte-Konzept, das deutlich über Ausbaustufe 1 hinausgeht und im Kern die dort bewusst ausgeklammerten Fachmodule beschreibt: zwei getrennte PWA-Zugänge (Büro-Web + DJI-RC-Plus-Gerät), Login-Wechsel von Passwort auf Username+4-stellige-PIN, admin-konfigurierbares Wizard-System für Preflight/Flugstart/Flugende, Einsatz-/Übungsverwaltung, Flugbuch/Logbuch, Push-Benachrichtigungen als Kernfunktion, Nutzerprofile mit Drohneneinheiten-Zugehörigkeit, neue Dashboard-Module (Livestream, Drohnen-Status, Karte, Wetter DWD, OpenSky, Tickets). In einer Planungssession (Plan-Mode, 3 parallele Explore-Agenten + 1 Plan-Agent) wurde daraus ein 15-Phasen-Restrukturierungsplan erarbeitet und vom Nutzer freigegeben (liegt nicht im Repo). Zwei Nutzerentscheidungen während der Planung: Deployment-Kontext des Büro-Zugangs (offen/VPN) ist noch nicht entschieden — PIN-Sicherheitsrisiko (nur 10.000 Kombinationen bei rein hashbasiertem Schutz) bleibt daher dokumentiert offen statt gelöst; der Nutzer möchte einen frühen Hardware-Feasibility-Test auf der echten DJI RC Plus, statt strikt der fachlichen Abhängigkeitskette zu folgen — die Phasenreihenfolge zieht den RC-Spike (Phase 5) daher vor die meisten Fachmodule vor. Zusätzliche Auflage: für jede Phase verbindliche Testuser/Testdaten (`flask seed-test-data`, noch zu bauen) statt nur abstrakter pytest-Abdeckung.

Phase 1 (Modul-Registry-Bootstrap) und Phase 2 (Rollen ohne Dashboard) sind umgesetzt und getestet.

### 2026-07-23 (Fortsetzung) — Phase 3: PIN-Login-Migration umgesetzt
Passwort-Login vollständig durch Username + 4-stellige PIN ersetzt (kein Parallelbetrieb, da noch keine echten Produktivnutzer existieren): `User.password_hash` → `pin_hash` (Migration `eb781f84828e`), progressive Sperr-Eskalation (1./2. Sperre zeitbasiert, ab der 3. nur per Admin-Aktion aufhebbar — reine Zeitsperre bietet bei nur 10.000 PIN-Kombinationen zu wenig Schutz), Self-Service-PIN-Wechsel, Denylist trivialer PINs im Self-Service- und Admin-Anlageformular. Migration zusätzlich gegen die reale lokale Dev-DB (`fireflight2`, nicht nur die Test-DB) verifiziert — dabei bestätigt, dass ein bestehender Passwort-Hash nach der Spaltenumbenennung nicht mehr als PIN funktioniert (erwartet, PIN der lokalen `admin`-Testfigur manuell neu gesetzt). Offener Punkt bleibt ungelöst: der Nutzer hat den Deployment-Kontext des Büro-Zugangs (offenes Internet vs. VPN) noch nicht entschieden, wodurch das PIN-Sicherheitsrisiko bei offenem Zugriff bestehen bleibt. Details: `docs/roadmap.md` Abschnitt „Status: Ausbaustufe 2".

### 2026-07-23 (Fortsetzung) — App lokal gestartet, danach DJI-FlightHub-2-Integration komplett entfernt
Nach Abschluss von Phase 3 wurde die App lokal gestartet (venv + lokaler PostgreSQL-Dienst, `python run.py`) und der komplette PIN-Login-Flow per `curl` end-to-end gegen den echten Dev-Server verifiziert (Login → Rollenauswahl-Auto-Skip → Dashboard, 200/302 wie erwartet).

Direkt danach hat der Nutzer angewiesen, die komplette DJI-FlightHub-2-Integration erstmal wieder herauszunehmen, um zunächst eine saubere Basis ohne Integrationen fertigzustellen ("möchte erstmal eine Basis schaffen"). Vollständig entfernt: `app/integrations/dji_flighthub/` (Client-Interface, Mock-/Live-Client, Sync-Service, Routen, Modelle), zugehörige Templates, `app/static/js/whep-player.js`, `tests/test_dji_integration.py`, Blueprint-Registrierung, die CSP-Lockerung für den WHEP-Call (`connect-src` wieder strikt `'self'`), `DJI_FLIGHTHUB_*`-Env-Variablen (Config/.env.example/docker-compose.yml), das `dji_integration_status`-Dashboard-Widget, alle „Integrationen"-Navigationseinträge (Sidebar, Administrationsübersicht) und die `integrations.view/configure/sync`-Berechtigungen (inkl. Entfernen aus `equipment_officer`s Standardrechten). **Bewusst nicht angetastet:** die generische `external_references`-Tabelle (nicht DJI-spezifisch, wird für spätere Module wie das Flugbuch gebraucht) und die physischen `integration_configs`/`integration_sync_runs`-Tabellen in bereits migrierten Datenbanken (dev-DB `fireflight2` hat sie noch aus der initialen Migration) — dort bleiben sie als harmlose Altlast liegen, keine Migration geschrieben, die sie droppt (auf Wunsch nachholbar). Testsuite danach 38/38 grün. Vollständige Recherche-/Implementierungs-Historie der ursprünglichen Integration bleibt oben (2026-07-22-Einträge) und in `docs/dji-flighthub2-api.md` erhalten, falls die Integration später zurückkommt.

### 2026-07-23 (Fortsetzung) — Phase 4: Notifications-Kern (Web-Push) umgesetzt
Neues Kern-Package `app/notifications/` (`PushSubscription`, `NotificationLog`, Migration
`ad2f3b109171`) — Details in `docs/roadmap.md` Abschnitt „Status: Ausbaustufe 2". Beim
Autogenerate-Lauf für die Migration schlug Alembic zusätzlich vor, `integration_sync_runs`,
`external_references` und `integration_configs` zu droppen (kein Modell zeigt mehr auf sie, s.
DJI-Entfernung oben) — bewusst nicht übernommen, Migration nur um die zwei neuen Tabellen bereinigt,
konsistent mit der vorherigen Entscheidung, diese Tabellen als Altlast stehen zu lassen. Beim
Implementieren zwei Bugs vor dem grünen Testlauf gefunden und behoben: (1) `subscribe()` griff nach
`db.session.add()` auf `user.id` zu, bevor alle Felder gesetzt waren — bei einem durch vorheriges
`commit()` expired `user`-Objekt löste der Attributzugriff selbst einen Autoflush aus und schrieb die
Subscription-Zeile vorzeitig mit `user_id=NULL` (NOT-NULL-Verletzung); behoben durch `user.id` vor
dem Anlegen der Zeile zu lesen. (2) `pywebpush.webpush()` wirft bei einem nicht erreichbaren Endpoint
eine rohe `requests.exceptions.RequestException` statt `WebPushException` — ohne zusätzlichen
Except-Zweig hätte das einen unbehandelten 500 in der aufrufenden Route erzeugt; Netzwerkfehler
werden jetzt wie sonstige Zustellfehler geloggt, ohne die Subscription zu deaktivieren (kein
eindeutiges "gone"-Signal). Live gegen die reale lokale Dev-DB verifiziert: Migration angewendet,
anschließender `flask db migrate`-Lauf zeigt keine eigene Drift mehr (nur noch die bekannten
DJI-Alttabellen). Dev-Server gestartet und Subscribe-/Unsubscribe-Routen per `curl` gegen echte
Sessions/CSRF-Tokens bestätigt. **Nicht automatisiert verifiziert:** der eigentliche Push-Zustellversuch
— ein `curl`-Testaufruf gegen `/notifications/test-send` hätte einen echten `pywebpush`-Request an
die (reale, aber synthetische) Test-Endpoint-URL ausgelöst; das wurde bewusst abgebrochen, um keine
unerwünschte Netzwerkanfrage an eine externe Domain zu senden. Der volle Rundlauftest mit einer
echten Browser-Push-Subscription steht laut Restrukturierungsplan ohnehin als manueller Test aus
(`docs/roadmap.md` „Als Nächstes"). Testsuite 58/58 grün.

### 2026-07-23 (Fortsetzung) — Phase 5: RC-Hardware-Feasibility-Spike umgesetzt (reduzierter Umfang)
Auf Nutzeranweisung ("mach weiter mit der roadmap") direkt im Anschluss an Phase 4 umgesetzt, ohne auf
den (nur manuell möglichen) Browser-Push-Rundlauftest aus Phase 4 zu warten. Neues Kern-Package
`app/rc/` (`RcDevice`, Migration `e2ceaef6caed`) — vollständige Details in `docs/roadmap.md` Abschnitt
„Status: Ausbaustufe 2". Wichtigste bewusste Vereinfachung: der Geräteschlüssel dient zugleich als
langlebiger Cookie-Wert (kein separates Session-Token), um exakt bei den drei im Restrukturierungsplan
genannten `RcDevice`-Feldern zu bleiben. Ein reales Korrektheitsproblem vor dem grünen Testlauf
gefunden: Flask-Login leitet `@login_required` standardmäßig auf den global konfigurierten
`login_view` (`auth.login`) um — ohne Gegenmaßnahme wäre ein nicht angemeldeter Zugriff auf `/rc/home`
zur Desktop-Login-Seite gesprungen und hätte den Kiosk-Kontext gesprengt. Behoben über
`login_manager.blueprint_login_views = {"rc": "rc.login"}` (Flask-Login-Feature genau für
Mehr-Bereiche-Apps wie diese). Das überfällige `flask seed-test-data`-Kommando (laut Plan schon ab
Phase 1 gefordert, aber nie gebaut) wurde bei dieser Gelegenheit nachgeholt. Live gegen den echten
Dev-Server per `curl` verifiziert: kompletter Pairing→Operator-Login→Home-Rundlauf mit einem echten
`seed-test-data`-Testgerät, inkl. Manifest- und Service-Worker-Route. **Nicht verifiziert**, weil das
echte DJI-RC-Plus-Hardware braucht (der eigentliche Zweck dieses Spikes): PWA-Installation,
Hintergrund-Push unter DJIs Energie-/Hintergrundrichtlinien, tatsächlicher App-Wechsel zu DJI Pilot 2.
Die DJI-Pilot-2-Deep-Link-URL wurde bewusst NICHT geraten, sondern als leere, admin-konfigurierbare
Einstellung angelegt (Administration → RC-Geräte) — der Button auf `/rc/home` bleibt ausgeblendet, bis
der Nutzer den korrekten Wert auf der echten Hardware ermittelt hat. Testsuite 78/78 grün.

### 2026-07-23 (Fortsetzung) — Phase 6: Drohneneinheiten umgesetzt
Direkt im Anschluss an Phase 5, ebenfalls auf "mach weiter mit der roadmap". Neues Kern-Package
`app/units/` (`Unit`, `unit_managers`-m:n, `User.home_unit_id`, Migration `c610af27d089`) — Details in
`docs/roadmap.md` Abschnitt „Status: Ausbaustufe 2". Ein User hat maximal eine Heimateinheit, kann
aber unabhängig davon mehrere Einheiten managen. Admin-UI unter `/administration/units`; die
Mitgliederzuordnung läuft bewusst über den bestehenden Benutzer-Editor (neue "Heimateinheit"-Auswahl
in `user_edit.html`), nicht über eine eigene Zuordnungs-UI auf der Einheiten-Seite. `flask
seed-test-data` um 3 Testeinheiten mit überlappenden Managern erweitert (Restrukturierungsplan-
Vorgabe für Phase-6-Testdaten). Beim Live-Test gegen den echten Dev-Server eine für dieses Projekt
grundlegende, aber leicht zu vergessende Eigenheit erneut bestätigt: `permission_required`-Routen
scheitern mit 403, solange nach dem Login nicht auch `/roles/select` aufgerufen wurde (setzt erst die
aktive Rolle in der Session) — bloßer Login reicht nicht. Testsuite 88/88 grün.
