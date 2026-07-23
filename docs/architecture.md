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

## Verifikation dieser Ausbaustufe
Lokal gegen echtes PostgreSQL getestet (nicht nur SQLite/Mocks), da UUID- und JSONB-Spaltentypen
Postgres-spezifisch sind: `flask db upgrade` gegen `fireflight2`, `flask init-fireflight` zweimal
(Idempotenz), vollständiger Login→Rollenauswahl→Dashboard→Administration-Flow per `curl` inkl.
CSRF-Header, 22 pytest-Tests gegen `fireflight2_test`. Docker selbst wurde **nicht** getestet (auf der
Entwicklungsmaschine nicht installiert) — Details in `docs/roadmap.md`.
