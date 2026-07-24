# Architekturentscheidungen

Dokumentiert die Entscheidungen, die bei der Umsetzung von Ausbaustufe 1 und 2 getroffen wurden —
vor allem dort, wo die Vorgaben (`docs/spec-struktur.md`, `fireflight2-konzept-struktur.md`) bewusst
Freiraum ließen. Diese Datei sammelt die **durable** Entscheidungen (gelten weiterhin für neuen
Code); die chronologische Herleitung mit allen Zwischenständen/Live-Verifikationen je Phase steht in
`docs/roadmap.md` und sollte dort nachgeschlagen werden, nicht hier dupliziert werden. Für den
Gesamtstatus siehe `docs/roadmap.md`.

## Primärschlüssel: UUID statt Auto-Increment
Alle Tabellen nutzen `UUID`-Primärschlüssel (`app/core/models.py: UUIDPrimaryKeyMixin`), clientseitig
per `uuid.uuid4()` erzeugt. Vorteil: IDs sind kollisionsfrei generierbar, ohne einen Insert
abzuwarten — praktisch für Services, die mehrere zusammenhängende Objekte in einer Transaktion
anlegen, und verhindert, dass fortlaufende IDs Rückschlüsse auf Datenmengen zulassen.

## `user_roles`/`role_permissions` als reine Tabellen, nicht als eigene Modelle
Die m:n-Beziehungen sind als SQLAlchemy `Table`-Objekte definiert (`app/roles/models.py`), nicht als
volle ORM-Klassen. `user_roles.assigned_at` bekommt seinen Wert über den Spalten-Default; eigene
Business-Logik auf der Zuordnung selbst war nicht gefordert. Spart Komplexität gegenüber dem
Association-Object-Pattern, ohne die im Datenmodell (spec-struktur.md Abschnitt 14) geforderten
Tabellen/Spalten zu verlieren.

## Rollen-Systemschutz über `is_system`, nicht über Namens-Vergleiche
Die Administrator-Rolle bekommt `is_system=True`. `role_has_permission()`
(`app/core/security/permissions.py`) gibt für Systemrollen immer `True` zurück, statt Wildcard-
Permission-Zeilen in der DB zu pflegen. Erfüllt die Vorgabe "keine hart codierten Rollennamen für
Berechtigungsprüfungen" im Kern (`if role.is_system`, nicht `if role.key == "administrator"`), auch
wenn `is_system` selbst als Flag hart im Seed-Code steht — das Flag ist aber generisch und würde für
jede künftige Systemrolle funktionieren, nicht nur für "Administrator".

## Rollenwechsel: `HX-Redirect` statt HTMX-Standard-Swap
Der Rollenwechsel-Dropdown in der Kopfzeile nutzt `hx-post`. Die Route
(`app/roles/routes.py: _activate`) erkennt HTMX-Requests am `HX-Request`-Header und antwortet mit
dem `HX-Redirect`-Response-Header statt einem normalen Redirect. Grund: Ein Rollenwechsel ändert
Sidebar, Berechtigungen und Dashboard komplett — ein normaler HTMX-Swap (der nur das auslösende
Element ersetzt) wäre hier falsch. `HX-Redirect` erzwingt eine echte Browser-Navigation.

## CSRF für HTMX: Header statt verstecktem Formularfeld
`base.html` setzt `hx-headers='{"X-CSRFToken": "..."}'` auf `<body>`, sodass jeder von HTMX
ausgelöste Request automatisch den CSRF-Header mitschickt. Flask-WTFs `CSRFProtect` akzeptiert
`X-CSRFToken`/`X-CSRF-Token`-Header standardmäßig zusätzlich zum Formularfeld — kein Sonderfall im
Backend nötig.

## `hx-boost="true"` auf `<body>` statt handgeschriebener Partial-Responses
Statt für jede Seite zwei Antwortvarianten (voll/Partial) zu pflegen, boostet HTMX alle normalen
Links/Formulare automatisch zu asynchronen Requests mit History-Push. Das erfüllt "bevorzugt HTMX für
dynamische Bereiche" wirtschaftlich, ohne dass jede Route zwischen normalem und HTMX-Request
unterscheiden müsste — Ausnahme ist der Rollenwechsel (s. o.), der wegen des App-weiten Effekts eine
echte Navigation braucht.

## Design-System: CSS-Variablen 1:1 aus dem Guide, App-Shell-Layout ergänzt
`app/static/css/app.css` übernimmt alle Tokens/Komponenten-Klassen aus `docs/spec-design.md` wörtlich.
Das Sidebar-/Topbar-/Dashboard-Grid-Layout selbst war im Guide nicht enthalten (der Guide zeigt nur
Einzelkomponenten) und wurde ergänzt, orientiert an dessen eigener Vorgabe (220px Sidebar Desktop,
Bottom-Tab-Bar <760px, kein separates Mobile-Design).

## Dark-Mode-Werte pragmatisch abgeleitet
Der gelieferte Design-Guide enthält nur Light-Mode-Werte. Für `:root[data-theme="dark"]` wurden
`--color-bg`/`--color-surface`/`--color-text`/`--color-divider` aus den bereits vorhandenen
Neutral-Ramps abgeleitet (`--color-neutral-900` als Hintergrund usw.), der Akzentton bleibt
unverändert (deckt sich mit der Vorgabe "Akzentton bleibt in beiden Modi identisch"). Es gibt aktuell
noch keinen Theme-Umschalter in der UI — nur die CSS-Grundlage dafür.

## Icons: Textfelder statt echter Lucide-Einbindung
`Role.icon` ist ein freies Textfeld (z. B. `"shield"`), wird aber in Ausbaustufe 1 nirgends als
tatsächliches SVG-Icon gerendert. Eine vollständige Lucide-Einbindung (Sprite oder Einzel-SVGs) war
gegenüber Kern-Funktionalität (Auth, Rollen, Dashboards) nachrangig — siehe `docs/roadmap.md`.

## DJI-FlightHub-2-Integration entfernt (2026-07-23)
Die zuvor hier dokumentierte echte DJI-FlightHub-2-Anbindung (`app/integrations/dji_flighthub/`,
Mock- und Live-Client, Livestream/WHEP-Player, Administrationsoberfläche) wurde auf Nutzerwunsch
komplett aus dem Code entfernt, um zunächst einen sauberen Kern ohne externe Integrationen fertigzustellen
(Ausbaustufe 2 zunächst ohne Integrationen). Die generische `external_references`-Tabelle (Herkunft von
Daten, spec-struktur.md Abschnitt 15) bleibt bestehen, da sie nicht DJI-spezifisch ist. Die zwei
DJI-spezifischen Tabellen `integration_configs`/`integration_sync_runs` existieren als Altlast aus der
initialen Migration ggf. noch in bereits migrierten Datenbanken, werden aber von keinem Modell mehr
referenziert. Vollständige Historie der Implementierung und Recherche: `CLAUDE.md` Abschnitt „Verlauf"
und `docs/dji-flighthub2-api.md` (bleibt als Referenz erhalten, falls die Integration später
zurückkommt).

## Migrationen: Ein Pfad statt zwei
Anders als FireFlight v1 (nummerierte Migrationsskripte **plus** separate `_org_alter_statements()`
für Org-Schemas, dort eine dokumentierte Fehlerquelle) gibt es in FireFlight2 nur einen Migrationspfad:
Flask-Migrate/Alembic gegen die eine gemeinsame Datenbank. Möglich, weil Ausbaustufe 1 bewusst
Single-Tenant ist (kein Schema-pro-Organisation, s. `CLAUDE.md` Tech-Stack-Tabelle).

## Verifikation der Ausbaustufe 1
Lokal gegen echtes PostgreSQL getestet (nicht nur SQLite/Mocks), da UUID- und JSONB-Spaltentypen
Postgres-spezifisch sind: `flask db upgrade` gegen `fireflight2`, `flask init-fireflight` zweimal
(Idempotenz), vollständiger Login→Rollenauswahl→Dashboard→Administration-Flow per `curl` inkl.
CSRF-Header, 22 pytest-Tests gegen `fireflight2_test`. Docker selbst wurde **nicht** getestet (auf der
Entwicklungsmaschine nicht installiert) — Details in `docs/roadmap.md`.

## Ausbaustufe 2 — Entscheidungen

### Fachmodul-Widgets: eigene Berechtigungsprüfung in Python statt im Template
Widget-Partials werden per `{% include %}` in ein Makro eingebunden (`dashboards/_widget.html:
render_widget`) — ein Makro-Include ohne `with context` sieht keine `context_processor`-Werte wie
`current_user`/`has_permission()`, nur echte Jinja-Globals. Fachmodul-Widgets registrieren ihre
Datenfunktion deshalb über `FireFlightModule.register_template_globals()` als echten
`app.add_template_global(...)` und prüfen die nötige Berechtigung selbst (`role_has_permission(
get_active_role(), "...")`) statt sich auf `has_permission()` aus dem Template zu verlassen. Gilt
für alle Fachmodul-Widgets seit Phase 13 (Flugbuch-Karte, Ticket-Meldeformular); die beiden
externen Widgets aus Phase 14 (Wetter/OpenSky) brauchen die Prüfung nicht, da ihre Daten nicht
organisationsbezogen sind — s. u.

### Sidebar-Navigation: `url_for()` und Berechtigungsfilter nicht vergessen
Bis Phase 9 nie mit einem echten Fachmodul durchgespielt, dabei zwei latente Bugs in `base.html`
gefunden: `module_navigation`-Einträge wurden als roher `href`-Wert statt über `url_for(entry.
endpoint)` gerendert, und nicht auf `entry.permission` gefiltert (jeder eingeloggte Nutzer hätte
jeden Modul-Navigationslink gesehen). Analog bei Phase 10 fürs hartkodierte "Dashboard"-Sidebar-Item
(kein `has_permission('dashboard.view')`-Check) und `_resolve_role_landing()` (prüfte bei
individuell gesetztem `landing_endpoint` nur, ob sich die URL bauen lässt, nicht ob die Rolle dort
eine Berechtigung hat). Lehre für neue Module: Navigation/Landing-Logik mit einer echten,
rechtearmen Testrolle durchspielen, nicht nur mit Administrator.

### RC-PWA: zwei getrennte Sitzungsebenen statt einer
Der RC-Kiosk-Zugang trennt Geräte-Session (langlebiger Cookie, Werkzeug-Hash-Vergleich gegen
`RcDevice.device_key_hash`, `app/rc/routes.py: _load_device()`) von Bediener-Session (normaler
Flask-Login nach PIN-Eingabe, zusätzlich mit `session["rc_device_id"]` verknüpft). "Person
wechseln" meldet nur den Bediener ab, der Geräte-Cookie bleibt bestehen. Eigener
`login_manager.blueprint_login_views = {"rc": "rc.login"}`, da der Flask-Login-Default sonst auf die
Desktop-Login-Seite umgeleitet hätte. Bewusste Vereinfachung: der Geräteschlüssel ist zugleich der
Cookie-Wert (kein separates, rotierbares Session-Token) — bei Kompromittierung hilft nur
`regenerate_device_key()`, danach muss das Gerät neu gekoppelt werden. Beim Bedienerwechsel müssen
alle bediener-spezifischen Session-Schlüssel (`rc_active_flight_id`, `rc_preflight_state`,
`rc_flight_end_state`, s. `_OPERATOR_SESSION_KEYS`) explizit geleert werden — sonst sieht der
nächste Bediener denselben Geräts den noch offenen Flug der vorigen Person (realer Bug, Phase 12).

### Wizard-Engine: generischer Runner, fachliche Bedeutung erst über `field_key`
`app/wizards/` bleibt fachlich neutral (Step-Typen `info`/`checklist`/`confirmation`/`text_input`/
`choice`/`location`, `WizardRunner` validiert nur "kann weitergeschaltet werden"). Die Zuordnung
einer Antwort zu einem Flugbuch-Feld läuft über die optionale `WizardStep.field_key`-Spalte plus
`app/modules/incidents/wizard_fields.py` als reinem RC-Verbraucher (`app/rc/wizard_flow.py:
collect_field_answers()`) — die Engine selbst kennt "Flugbuch" nicht. Wichtige Detailentscheidung:
für echte Ja/Nein-Fragen mit `field_key` (z. B. "Synchronisiert?") ist `choice` mit Optionen
"Ja"/"Nein" der richtige Step-Typ, nicht `confirmation` — `confirmation` erzwingt immer eine
angehakte Checkbox zum Weiterkommen, taugt also nur für echte Zustimmungsfragen, nicht für
Ja/Nein-Datenerfassung.

### Magic-Byte-Validierung statt Dateiendung/Content-Type bei Uploads
Profilbilder (Phase 7) und Ticket-Foto-Anhänge (Phase 10) werden über die tatsächlichen
PNG/JPEG/WebP-Signaturbytes validiert (`app/core/utilities/uploads.py`), nicht über die vom Client
gesendete Dateiendung/den Content-Type-Header (beides fälschbar). Nutzerinhalte liegen unter
`instance_path/uploads/`, nicht `app/static/` (getrennt vom versionierten Code, eigenes
Docker-Volume `fireflight2-uploads-data`), und werden über eine eigene, login-geschützte Route
serviert statt direkt als statische Datei.

### Externe Read-Only-APIs: schlanke Direktanbindung statt Integrationsschicht (Phase 14)
Nach der DJI-FlightHub-2-Erfahrung (volle Mock-/Live-Client-Architektur gebaut, dann komplett
wieder entfernt, s. u.) bewusste Entscheidung: für schreibgeschützte, nicht organisationsbezogene
externe Daten ohne Persistenzbedarf (DWD-Wetter, OpenSky-Luftraum) ruft das jeweilige Fachmodul die
externe API direkt auf, ohne eigene `app/integrations/`-Schicht, ohne Admin-Konfiguration, ohne
Sync-Jobs. Ein einfacher, genereller In-Prozess-TTL-Cache (`app/core/utilities/external_cache.py`,
`cached(key, ttl, fetch)`) schützt vor allem gegen Rate-Limits (OpenSky: 400 anonyme Requests/Tag)
und cacht bewusst auch Fehlerfälle (verhindert Retry-Stürme bei einem API-Ausfall). Bekannte
Einschränkung: mehrere Gunicorn-Worker in Produktion hätten je einen eigenen Cache — für die
geringe Nutzerzahl dieser App hingenommen. Das generelle Prinzip "Fachmodule sprechen nie direkt
mit einer externen API" (s. u.) gilt weiterhin für zustandsbehaftete/organisationsspezifische
Integrationen.

### CSP: punktuelle Lockerungen statt genereller Aufweichung
Die strikte Basis-CSP (`script-src 'self'`, kein Inline-JS) bleibt bestehen; wo eine echte externe
Abhängigkeit unvermeidbar ist, wird gezielt genau dieser eine Host freigegeben statt der ganzen
Direktive: `img-src` um `tile.openstreetmap.org` erweitert (Leaflet-Kartenkacheln, Phase 9), sonst
keine weiteren Lockerungen. Karten-Marker-Daten werden serverseitig zu reinen JSON-Objekten
reduziert und über einen `<script type="application/json">`-Block eingebettet statt per Inline-JS
gerendert, bleibt damit CSP-konform.

## Verifikation der Ausbaustufe 2
Jede Phase wurde einzeln gegen die reale lokale Dev-Datenbank migriert (nie nur `db.create_all()`
in Tests) und, wo sinnvoll, per `curl`/echtem Browser-Rundlauf gegen den laufenden Dev-Server
verifiziert — Details je Phase in `docs/roadmap.md`. Zwei Kategorien bleiben bewusst offen, da sie
echte Hardware bzw. einen laufenden Produktivbetrieb voraussetzen, die auf der Entwicklungsmaschine
nicht verfügbar sind: der komplette Push-/PWA-/Hintergrund-Rundlauf auf der echten DJI RC Plus
(Phase 4/5/12) und ein echter Docker-Compose-Lauf (s. o., gilt unverändert seit Ausbaustufe 1).
