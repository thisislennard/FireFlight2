# Architekturentscheidungen

Dokumentiert die Entscheidungen, die bei der Umsetzung von Ausbaustufe 1 getroffen wurden — vor
allem dort, wo `docs/spec-struktur.md` bewusst Freiraum ließ ("triff bei kleineren offenen Fragen
selbstständig sinnvolle, pragmatische Entscheidungen"). Für den Gesamtstatus siehe `docs/roadmap.md`.

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
gegenüber Kern-Funktionalität (Auth, Rollen, Dashboards, DJI-Grundstruktur) nachrangig — siehe
`docs/roadmap.md`.

## DJI-Integration: echte Anbindung, Zugangsdaten über die Administrationsoberfläche
`IntegrationConfig.settings` (JSONB) speichert pro Organisation Organization Key (X-User-Token),
Projekt-UUID (X-Project-Uuid), Base-URL und die DSGVO-Bestätigung — gepflegt über ein Formular auf
`/administration/integrations/dji-flighthub/` (Berechtigung `integrations.configure`), analog zu v1s
Einstellungsseite. Das Org-Key-Feld wird im Formular nie mit dem echten Wert vorausgefüllt (Passwort-
Input, leer lassen = unverändert lassen) — Zugangsdaten landen dadurch zwar in der DB, aber nie
hartkodiert im Quellcode (spec-struktur.md Abschnitt 4). `DJI_FLIGHTHUB_ORG_KEY`/`_PROJECT_UUID`/
`_BASE_URL`-Umgebungsvariablen sind nur ein optionaler Deployment-Default, falls die DB-Werte leer sind;
`DJI_FLIGHTHUB_ENABLED` (Default `true`) ist ein globaler Not-Aus-Schalter unabhängig vom DB-Zustand.

`get_client()` (`app/integrations/dji_flighthub/service.py`) liefert `LiveDJIFlightHubClient` nur, wenn
**alle drei** Bedingungen erfüllt sind: Not-Aus nicht aktiv, Org Key + Projekt-UUID vorhanden (DB oder
Env), **und** `settings.dsgvo_ack=true` — sonst immer `MockDJIFlightHubClient`. So kann eine echte
Anbindung nie versehentlich ohne bewusste DSGVO-Bestätigung aktiv werden. Beide Client-Implementierungen
erfüllen dieselbe erweiterte `DJIFlightHubClient`-Schnittstelle (`base.py`) — die Übersichtsseite sieht
in Mock- wie Live-Betrieb identisch aus, nur mit Demo- statt Echtdaten. Nur lesende Endpunkte angebunden
(Systemstatus, Projekte, Geräte, Telemetrie, HMS, Flugaufgaben inkl. Medien/Track, Waylines) — Steuer-
endpunkte (Task anlegen, Gerätebefehle, Kamera/RTK/Livestream) bewusst nicht, s. `docs/dji-flighthub2-api.md`.
`gather_flighthub_overview()` deckelt die Anzahl paralleler Detail-Abfragen (Geräte/Tasks), um bei
großen Organisationen nicht unkontrolliert viele API-Calls auf einmal auszulösen — reine
Administrations-/Explorationsseite, kein Vollsynchronisierungsmechanismus.

## Migrationen: Ein Pfad statt zwei
Anders als FireFlight v1 (nummerierte Migrationsskripte **plus** separate `_org_alter_statements()`
für Org-Schemas, dort eine dokumentierte Fehlerquelle) gibt es in FireFlight2 nur einen Migrationspfad:
Flask-Migrate/Alembic gegen die eine gemeinsame Datenbank. Möglich, weil Ausbaustufe 1 bewusst
Single-Tenant ist (kein Schema-pro-Organisation, s. `CLAUDE.md` Tech-Stack-Tabelle).

## Verifikation dieser Ausbaustufe
Lokal gegen echtes PostgreSQL getestet (nicht nur SQLite/Mocks), da UUID- und JSONB-Spaltentypen
Postgres-spezifisch sind: `flask db upgrade` gegen `fireflight2`, `flask init-fireflight` zweimal
(Idempotenz), vollständiger Login→Rollenauswahl→Dashboard→Administration-Flow per `curl` inkl.
CSRF-Header, 22 pytest-Tests gegen `fireflight2_test`. Docker selbst wurde **nicht** getestet (auf der
Entwicklungsmaschine nicht installiert) — Details in `docs/roadmap.md`.
