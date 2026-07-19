# FireFlight2 – Projektübersicht für Claude Code

## Was ist FireFlight2?
Von-Grund-auf-Neuentwicklung von FireFlight (`G:\5 GitHub\FireFlight`) — Drohnenflug-Logbuch für Feuerwehren/BOS-Einheiten. **Kein Fork, kein Code-Import** — v1 dient ausschließlich als fachliche Referenz für den Funktionsumfang, nicht als Codebasis. Repo: `github.com/thisislennard/FireFlight2`.

v1 bleibt unangetastet produktiv unter `G:\5 GitHub\FireFlight`. Volle Architektur-/Security-/Design-Referenz von v1: `FireFlight/CLAUDE.md`, Nutzer-Feature-Liste: `FireFlight/README.md`.

## Warum Neuentwicklung statt Weiterentwicklung von v1
- **Technische Basis modernisieren** — weg vom frameworklosen Python-Stdlib-HTTP-Server (`http.server.ThreadingHTTPServer`) aus v1
- **Architektur/Code-Qualität** — v1 ist über die Zeit gewachsen (viele Module, gemischte Patterns), FireFlight2 soll von Anfang an sauberer/konsistenter strukturiert sein
- **Feature-Set neu denken** — nicht nur Technik, auch der Funktionsumfang selbst wird überdacht; konkrete neue Features werden ergänzt, sobald besprochen

## Tech-Stack (Entscheidungen bisher)
| Bereich | Entscheidung | Begründung |
|---|---|---|
| Backend | **Flask** | Bewusst wie in [LiFeOS](../LiFeOS) und [LayerOS](../LayerOS) statt v1s frameworklosem Ansatz oder FastAPI — Konsistenz mit anderen Projekten des Nutzers, vertrautes Ökosystem (Flask-Login, Flask-WTF/CSRF, SQLAlchemy) |
| Frontend | **Vanilla JS SPA, kein Build-Step/Bundler** | Wie v1 — kein React/Vue, direkt deploybar ohne npm-Pipeline |
| Datenbank | **PostgreSQL** | Wie v1. Migrations-Tooling noch offen (v1-Muster mit nummerierten Skripten vs. Alembic, da jetzt SQLAlchemy im Spiel ist) |
| Multi-Tenancy | **Vorerst keine — Single-Tenant, nur eine Organisation** | Explizite Nutzer-Entscheidung. v1s Schema-pro-Org-Modell (`org_<slug>` Postgres-Schema) wird **nicht** übernommen. Falls später doch Multi-Tenancy gebraucht wird: `org_id`-Spalten-Modell empfohlen statt Schema-pro-Org — v1 hatte mit dem doppelten Migrationspfad (nummerierte Migration **und** `_org_alter_statements()` in `backend/superadmin/service.py`) ein dokumentiertes, wiederkehrendes Bug-Muster (Änderungen kamen in echten Org-Schemas nicht an, siehe `FireFlight/CLAUDE.md`, Abschnitt „2026-07-14 — FlightHub-2-Ablösung: Umsetzung"). Mit `org_id`-Spalte gibt es nur einen Migrationspfad; Isolation ließe sich über eine Basis-Model-Klasse/Query-Mixin erzwingen, optional zusätzlich Postgres Row-Level-Security |
| Design | **Komplett neues Design-System** | v1s Theme (Dark-first, Orange-Akzent `#e07b39`, siehe `FireFlight/CLAUDE.md` Abschnitt „Design-System/Optik") wird **nicht** übernommen. Konkrete Richtung noch offen |

## Offene Punkte (werden ergänzt, sobald besprochen)
- Feature-Umfang zum Start: schlanker Kern vs. volle v1-Parität von Anfang an eingeplant
- Konkrete neue Module/Funktionen ggü. v1
- Design-Richtung (Farben, Stimmung, Vorbilder)
- Migrations-Tooling (Alembic vs. eigenes Skript-System wie v1/LiFeOS)
- Auth-Ansatz (Flask-Login wie LiFeOS? 2FA/TOTP wie v1 übernehmen?)
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
- **DJI-FlightHub-2-Anbindung** (Business-OpenAPI): Geräte+HMS-Status, Flüge/Tasks mit GPS-Track, Medien-Galerie, Flugrouten (Waylines), Live-Videostream (WebRTC/WHEP), Import in eigenes Flugbuch. Volle Endpunkt-Referenz falls übernommen: `FireFlight/docs/FLIGHTHUB2_API.md`
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
- **DJI-FlightHub-2 Business-API**: `fh.dji.com` liefert nur die Web-Oberfläche (HTML), nicht die API — echte Basis-URL ist ein regionsspezifisches DJI-Gateway (z. B. `es-flight-api-us.djigate.com`), muss über Browser-DevTools (F12 → Netzwerk) ermittelt werden. API liefert bei leeren Listen `"list": null` statt `[]` — beim Parsen mit `(x.get("data") or {}).get("list") or []` statt `.get("list", [])` abfangen. Jeder Request braucht `X-Request-Id`-Header (UUID). Volle Referenz falls übernommen: `FireFlight/docs/FLIGHTHUB2_API.md`
- **CSP von v1** verbietet Inline-JS (`script-src 'self'`) — falls übernommen: alle Skripte als eigene Dateien unter `js/`, kein Inline-`<script>`
- **Passwort-Hashing** in v1: PBKDF2-HMAC-SHA256, 120.000 Iterationen, 16-Byte-Salt — als Mindeststandard falls kein Framework-Default (z. B. Flask-Bcrypt) gewählt wird

## Verlauf / Planungsentscheidungen
### 2026-07-19 — Projektstart, erste Architekturentscheidungen
Nutzer möchte FireFlight komplett neu bauen (kein Fork/Weiterentwicklung), Ordner `FireFlight2` existierte bereits mit GitHub-Remote. In einer Planungssession (Plan-Mode) wurden folgende Grundsatzentscheidungen getroffen: Backend Flask (statt v1s Stdlib-Server oder FastAPI), Frontend bleibt Vanilla-JS-SPA ohne Build-Step wie v1, Multi-Tenancy wird vorerst komplett weggelassen (nur eine Organisation), Design-System wird komplett neu entworfen statt v1-Theme zu übernehmen. Motivation für den Neuanfang: technische Basis modernisieren, Architektur/Code-Qualität verbessern, Feature-Set neu denken. Feature-Umfang zum Start, konkrete neue Features und Design-Richtung wurden vom Nutzer noch nicht final festgelegt (siehe „Offene Punkte" oben) — diese Datei wird ergänzt, sobald die Antworten vorliegen.
