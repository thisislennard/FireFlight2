# FireFlight2 – Struktur-/Architektur-Spezifikation (Nutzer-Vorgabe)

Wörtliche Vorgabe des Nutzers vom 2026-07-19 für Technik, Architektur und Funktionsumfang der ersten Ausbaustufe. Referenz-Dokument — Zusammenfassung und daraus abgeleitete Entscheidungen stehen in `CLAUDE.md`. Die Design-Vorgaben folgen separat (siehe `docs/spec-design.md`, sobald vom Nutzer geliefert).

---

Du bist ein erfahrener Senior-Softwarearchitekt und Full-Stack-Entwickler. Erstelle von Grund auf eine neue Webanwendung mit dem Namen **FireFlight2**.

FireFlight2 soll langfristig als zentrale Arbeits-, Informations- und Dokumentationsplattform für den Drohneneinsatz einer Feuerwehr dienen. Die Anwendung soll Informationen aus **DJI FlightHub 2** mit eigenen Eingaben und später ergänzten Fachmodulen verbinden.

In dieser ersten Entwicklungsphase sollen ausdrücklich noch keine vollständigen Fachmodule wie Einsatzverwaltung, Flugplanung, Gerätedokumentation oder Medienauswertung implementiert werden. Zunächst soll ein sauberer, stabiler und erweiterbarer Anwendungskern entstehen.

## 1. Technische Grundvorgaben

Verwende folgende Technologien:

* Python
* Flask
* PostgreSQL
* SQLAlchemy
* Flask-Migrate beziehungsweise Alembic
* serverseitiges HTML-Rendering mit Jinja2
* JavaScript nur dort, wo es sinnvoll erforderlich ist
* bevorzugt HTMX oder vergleichbare schlanke Technik für dynamische Bereiche
* responsives CSS-Framework oder ein eigenes schlankes Designsystem
* Docker
* Docker Compose für die lokale und produktionsnahe Ausführung

Die Flask-Anwendung soll in **einem eigenen App-Container** laufen.

PostgreSQL soll aus Gründen der Stabilität und Wartbarkeit als eigener Datenbank-Container betrieben werden. Das gesamte Projekt muss über einen einzigen Docker-Compose-Befehl gestartet werden können.

Beispiel:

```bash
docker compose up -d --build
```

Das Projekt muss vollständig containerisiert sein. Auf dem Host sollen außer Docker und Docker Compose keine zusätzlichen Abhängigkeiten notwendig sein.

## 2. Architektur

Baue FireFlight2 als **modularen Monolithen**.

Das bedeutet:

* eine gemeinsame Flask-Anwendung,
* ein gemeinsamer Anwendungskern,
* eine gemeinsame PostgreSQL-Datenbank,
* klar getrennte interne Module,
* keine unnötigen Microservices,
* keine enge Kopplung zwischen Fachbereichen,
* spätere Fachmodule müssen ohne grundlegenden Umbau ergänzt werden können.

Verwende eine Flask Application Factory und Flask Blueprints.

Beispielhafte Projektstruktur:

```text
fireflight2/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   │
│   ├── core/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── exceptions/
│   │   ├── security/
│   │   └── utilities/
│   │
│   ├── auth/
│   │   ├── routes.py
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── forms.py
│   │   └── permissions.py
│   │
│   ├── users/
│   ├── organizations/
│   ├── roles/
│   ├── dashboards/
│   ├── integrations/
│   │   └── dji_flighthub/
│   ├── administration/
│   ├── audit/
│   ├── notifications/
│   │
│   ├── modules/
│   │   ├── registry.py
│   │   └── base.py
│   │
│   ├── templates/
│   ├── static/
│   └── database/
│
├── migrations/
├── tests/
├── docker/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── README.md
└── run.py
```

Die genaue Struktur darf verbessert werden, sofern die Trennung der Verantwortlichkeiten erhalten bleibt.

## 3. Zentrale Leitidee

DJI FlightHub 2 ist kein isoliertes Zusatzmodul, das nur auf einer einzelnen Seite verwendet wird.

DJI FlightHub 2 soll langfristig eine der wichtigsten zentralen Datenquellen für die gesamte Anwendung sein.

FireFlight2 kombiniert:

1. automatisch übernommene Informationen aus DJI FlightHub 2,
2. manuell in FireFlight2 eingegebene Informationen,
3. automatisch durch FireFlight2 erzeugte Informationen,
4. Informationen aus später hinzugefügten Modulen und Integrationen.

Die Benutzer sollen später nicht zwischen „DJI-Daten" und „FireFlight2-Daten" wechseln müssen. Die Daten sollen in gemeinsamen Ansichten sinnvoll zusammengeführt werden.

Beispiel:

Ein Flug wird aus DJI FlightHub 2 übernommen und enthält möglicherweise:

* Drohne,
* Pilot,
* Startzeit,
* Landezeit,
* Flugdauer,
* Flugroute,
* Telemetrie,
* Flughöhe,
* Akkudaten,
* Bilder,
* Videos,
* Live-Positionen.

In FireFlight2 werden dazu später Informationen ergänzt wie:

* Einsatznummer,
* Einsatz,
* Einsatzabschnitt,
* Flugauftrag,
* Flugleiter,
* Kameraoperator,
* besondere Feststellungen,
* Freigaben,
* Dokumentationshinweise,
* Bewertungen,
* Maßnahmen.

Es soll daraus ein gemeinsamer Datensatz entstehen.

## 4. DJI-FlightHub-2-Integration vorbereiten

In dieser ersten Version muss noch keine vollständige reale DJI-API-Anbindung umgesetzt werden, sofern dafür noch keine Zugangsdaten oder abschließend definierte API-Endpunkte vorhanden sind.

Erstelle aber bereits eine saubere Integrationsarchitektur.

Die DJI-Integration soll mindestens folgende interne Komponenten vorsehen:

```text
DJI-FlightHub-Integration
├── Client
├── Authentifizierung
├── Synchronisationsservice
├── Mapper
├── Datenvalidierung
├── Fehlerbehandlung
├── Synchronisationsprotokoll
├── Zuordnung externer und interner Datensätze
└── Repository beziehungsweise Datenzugriff
```

Definiere klare Interfaces beziehungsweise abstrakte Basisklassen, sodass später die echte DJI-Anbindung ergänzt werden kann.

Vermeide, dass spätere Fachmodule direkt mit der DJI-API kommunizieren.

Der gewünschte Datenfluss lautet:

```text
DJI FlightHub 2
        │
        ▼
DJI-Integrationsschicht
        │
        ▼
Interne FireFlight2-Datenmodelle
        │
        ▼
Services und Fachmodule
        │
        ▼
Dashboards und Benutzeroberfläche
```

Bereite außerdem einen Mock- oder Demo-Connector vor, mit dem Testdaten eingelesen werden können.

Im Administrationsbereich soll es bereits eine einfache Statusseite geben mit:

* Integrationsstatus,
* konfiguriert oder nicht konfiguriert,
* letzter Synchronisationsversuch,
* letzte erfolgreiche Synchronisierung,
* letzter Fehler,
* Anzahl zuletzt verarbeiteter Datensätze,
* Schaltfläche für eine simulierte Synchronisierung.

Zugangsdaten dürfen niemals fest im Quellcode gespeichert werden.

Nutze dafür Umgebungsvariablen und eine `.env.example`.

## 5. Organisation

In der ersten Version gibt es nur eine Organisation.

Trotzdem soll die Organisation bereits als eigenes Datenbankobjekt existieren, damit die Anwendung später erweitert werden kann.

Es soll zunächst keine Organisationsauswahl und keine komplexe Mandantenfähigkeit geben.

Die erste Organisation kann beim Initialisieren des Systems angelegt werden.

Beispiel:

```text
Feuerwehr Liederbach
```

Jeder Benutzer, jede Rolle und jedes Dashboard gehört zu dieser Organisation.

Vermeide jedoch eine komplexe Multi-Tenant-Architektur in dieser ersten Version.

## 6. Anmeldung

Implementiere ein sicheres Authentifizierungssystem.

Benötigte Funktionen:

* Login mit Benutzername oder E-Mail-Adresse,
* sicher gehashte Passwörter,
* Logout,
* Sitzungsverwaltung,
* Schutz vor Session-Fixation,
* CSRF-Schutz,
* deaktivierbare Benutzerkonten,
* letzter erfolgreicher Login,
* fehlgeschlagene Loginversuche protokollieren,
* vorbereitete Passwort-zurücksetzen-Struktur.

Verwende sichere und etablierte Verfahren. Passwörter dürfen niemals im Klartext gespeichert oder protokolliert werden.

## 7. Rollen

Folgende Rollen sollen bei der Ersteinrichtung automatisch angelegt werden:

* Dokumentation
* Einheitsführer
* Pilot/Kamera
* Flugleiter
* Einsatzleiter/SBI
* Gerätewart
* TEL-ELW
* Administrator

Diese Rollen dürfen nicht ausschließlich fest im Quellcode hinterlegt sein.

Sie sollen als Datenbankdatensätze angelegt werden und später durch einen Administrator bearbeitet werden können.

Ein Administrator soll:

* Rollen erstellen,
* Rollen bearbeiten,
* Rollen deaktivieren,
* Rollen kopieren,
* Rollen sortieren,
* Rollen mit einem Icon versehen,
* Rollen mit einer Beschreibung versehen,
* Rollen mit einer dezenten Akzentfarbe versehen,
* Rollen Benutzern zuweisen,
* Berechtigungen zu Rollen hinzufügen oder entfernen,
* Dashboards der Rollen konfigurieren können.

Systemkritische Rollen oder Berechtigungen dürfen nicht versehentlich vollständig gelöscht werden können.

Die Administratorrolle benötigt einen besonderen Schutz, damit nicht der letzte Administrator entfernt oder deaktiviert werden kann.

## 8. Rollenauswahl nach dem Login

Nach erfolgreichem Login soll der Benutzer nicht direkt auf ein allgemeines Dashboard gelangen.

Stattdessen soll eine Rollenauswahl erscheinen.

Überschrift:

```text
In welcher Funktion arbeitest du heute?
```

Es werden ausschließlich die Rollen angezeigt, die dem angemeldeten Benutzer zugewiesen sind.

Jede Rolle soll als gut erkennbare Karte dargestellt werden mit:

* Rollenname,
* Icon,
* Kurzbeschreibung,
* optionaler Akzentfarbe.

Nach Auswahl wird diese Rolle zur aktiven Sitzungsrolle.

Die aktive Rolle bestimmt:

* das sichtbare Dashboard,
* die sichtbare Navigation,
* die verfügbaren Funktionen,
* die Berechtigungen für die aktuelle Sitzung.

Ein Benutzer kann mehrere Rollen besitzen.

Die Rolle soll während der Sitzung über ein Dropdown in der Kopfzeile gewechselt werden können, ohne dass sich der Benutzer neu anmelden muss.

Bei nur einer zugewiesenen Rolle kann die Auswahlseite automatisch übersprungen werden. Diese Funktion soll über eine Systemeinstellung aktivierbar beziehungsweise deaktivierbar sein.

Die zuletzt verwendete Rolle darf optional gespeichert werden.

## 9. Berechtigungssystem

Implementiere ein echtes Berechtigungssystem.

Prüfe nicht nur hart auf bestimmte Rollennamen wie:

```python
if user.role == "Administrator":
```

Stattdessen sollen Rollen einzelne Berechtigungen bündeln.

Beispielhafte Berechtigungen:

```text
dashboard.view
dashboard.edit
dashboard.manage

users.view
users.create
users.edit
users.disable
users.assign_roles

roles.view
roles.create
roles.edit
roles.disable
roles.assign_permissions

organization.view
organization.edit

integrations.view
integrations.configure
integrations.sync

administration.access

audit.view

settings.view
settings.edit
```

Die Berechtigungen sollen zentral registriert und über Decorators oder vergleichbare Mechanismen geprüft werden können.

Beispiel:

```python
@permission_required("roles.edit")
def edit_role():
    ...
```

Berechtigungen müssen zusätzlich in Services geprüft werden. Eine reine Prüfung in der Benutzeroberfläche ist nicht ausreichend.

Das Ausblenden eines Buttons ersetzt keine serverseitige Berechtigungsprüfung.

## 10. Dashboards

Jede Rolle erhält ein eigenes Dashboard.

Das Dashboard soll datenbankbasiert und konfigurierbar sein.

Es soll aus Widgets bestehen, die in einem Raster angeordnet werden.

Verwende beispielsweise ein 12-Spalten-System.

Ein Widget benötigt mindestens:

* eindeutige ID,
* Widget-Typ,
* Titel,
* Position,
* Breite,
* Höhe,
* Konfiguration als JSONB,
* Aktivstatus,
* Sichtbarkeit,
* zugehöriges Dashboard,
* Erstellungsdatum,
* Änderungsdatum.

Das Dashboard benötigt mindestens:

* Name,
* zugehörige Rolle,
* Beschreibung,
* Layout-Konfiguration,
* Aktivstatus,
* Versions- oder Änderungsinformation.

In der ersten Version reichen einfache Basiswidgets:

* Überschrift,
* Informationstext,
* Schnellzugriff,
* Statusanzeige,
* Kennzahl,
* Hinweis,
* Warnung,
* leeres Platzhalter-Widget,
* DJI-Integrationsstatus.

Die eigentlichen fachlichen Inhalte und weiteren Widgets kommen später als eigenständige Module hinzu.

Erstelle einen grundlegenden Dashboard-Editor für Administratoren.

Der Editor soll mindestens ermöglichen:

* Widget hinzufügen,
* Widget löschen,
* Titel ändern,
* Größe ändern,
* Position ändern,
* Widget konfigurieren,
* Dashboard speichern,
* Vorschau anzeigen.

Drag-and-Drop ist erwünscht, sofern es sauber und wartbar umgesetzt werden kann. Eine funktionierende einfache Lösung ist wichtiger als unnötig komplexe JavaScript-Logik.

## 11. Modulsystem

Alle späteren fachlichen Inhalte sollen nachträglich als Module ergänzt werden.

Beispiele für spätere Module:

* Einsatzverwaltung,
* Flugverwaltung,
* Flugaufträge,
* Live-Lage,
* Kartenansicht,
* Mediendokumentation,
* Geräteverwaltung,
* Akkuverwaltung,
* Wartungen,
* Checklisten,
* Flugbuch,
* Berichte,
* Exporte,
* Benachrichtigungen,
* Wetter,
* Luftrauminformationen,
* Auswertungen.

Diese Module sollen in der ersten Version noch nicht vollständig entwickelt werden.

Erstelle stattdessen ein internes Modul- beziehungsweise Plugin-Registry-System.

Ein Modul soll später registrieren können:

* Name,
* technische Kennung,
* Version,
* Beschreibung,
* benötigte Berechtigungen,
* eigene Blueprints,
* Navigationseinträge,
* eigene Datenmodelle,
* eigene Services,
* eigene Dashboard-Widgets,
* eigene Hintergrundaufgaben,
* eigene Konfigurationsoptionen,
* eigene Integrationen.

Beispielhafte Moduldefinition:

```python
class FireFlightModule:
    key = "equipment"
    name = "Geräteverwaltung"
    version = "1.0.0"

    def register_blueprints(self, app):
        pass

    def register_permissions(self, registry):
        pass

    def register_widgets(self, registry):
        pass

    def register_navigation(self, registry):
        pass
```

Es ist nicht notwendig, dass Module während des laufenden Betriebs als fremde ZIP-Dateien installiert werden können.

Es reicht zunächst ein sauberes internes Modulsystem, bei dem neue Module als getrennte Python-Pakete im Projekt ergänzt und zentral registriert werden.

Module dürfen nicht unnötig voneinander abhängig sein.

Gemeinsame Funktionen gehören in den Core.

## 12. Navigation

Die Navigation soll abhängig von der aktiven Rolle und den vorhandenen Berechtigungen aufgebaut werden.

Desktop-Aufbau:

* linke Seitenleiste,
* einklappbar,
* Icons und Beschriftungen,
* oberer Bereich mit Hauptnavigation,
* unterer Bereich mit Administration und Einstellungen.

Kopfzeile:

* Name der aktuellen Seite,
* Status wichtiger Systeme,
* aktive Rolle als Dropdown,
* Benutzerprofil,
* Logout.

Beispiel:

```text
FireFlight2

Dashboard
DJI-Daten
Weitere Module

Administration
Einstellungen
```

Menüpunkte ohne Berechtigung dürfen nicht angezeigt werden.

Trotzdem müssen die zugehörigen Routen zusätzlich serverseitig geschützt sein.

## 13. Design

Siehe separates Dokument `docs/spec-design.md` (folgt).

## 14. Datenmodell

Erstelle ein sauberes relationales Datenmodell in PostgreSQL.

Mindestens benötigte Tabellen beziehungsweise Entitäten:

```text
organizations
users
roles
permissions
user_roles
role_permissions
dashboards
dashboard_widgets
system_settings
audit_logs
integration_configs
integration_sync_runs
external_references
```

Sinnvolle zusätzliche Tabellen dürfen ergänzt werden.

Nutze PostgreSQL-Funktionen sinnvoll:

* UUIDs oder gut begründete Primärschlüssel,
* JSONB für flexible Widget-Konfigurationen,
* Indizes,
* eindeutige Constraints,
* Foreign Keys,
* sinnvolle Löschregeln,
* Zeitstempel,
* optimistische Sperren oder Versionsfelder, wo sinnvoll.

Verwende Zeitzonen korrekt. Zeitstempel sollen intern konsistent und bevorzugt in UTC gespeichert werden. In der Oberfläche sollen sie in der konfigurierten lokalen Zeitzone angezeigt werden.

Die Standardzeitzone ist:

```text
Europe/Berlin
```

## 15. Herkunft von Daten

Bereite das Datenmodell darauf vor, dass Informationen unterschiedliche Ursprünge besitzen können.

Mögliche Datenquellen:

```text
DJI_FLIGHTHUB
MANUAL
FIREFLIGHT_SYSTEM
OTHER_INTEGRATION
```

Für synchronisierte oder später zusammengeführte Datensätze soll nachvollziehbar sein:

* aus welcher Quelle sie stammen,
* welche externe ID sie besitzen,
* wann sie zuletzt synchronisiert wurden,
* wann sie erstmals importiert wurden,
* ob ein Synchronisationsfehler vorliegt,
* ob Daten intern ergänzt wurden.

Erstelle dafür eine allgemeine Struktur wie `external_references` oder eine vergleichbare saubere Lösung.

Vermeide es, jedes spätere Datenmodell direkt mit DJI-spezifischen Feldern zu überladen.

## 16. Audit-Logging

Implementiere ein grundlegendes Audit-Log.

Protokolliert werden sollen mindestens:

* Login,
* fehlgeschlagener Login,
* Logout,
* Rollenwechsel,
* Benutzer erstellt,
* Benutzer geändert,
* Benutzer deaktiviert,
* Rolle erstellt,
* Rolle geändert,
* Berechtigungen geändert,
* Dashboard geändert,
* Integration konfiguriert,
* Synchronisation gestartet,
* Synchronisation fehlgeschlagen.

Audit-Einträge sollen mindestens enthalten:

* Benutzer,
* aktive Rolle,
* Aktion,
* betroffene Objektart,
* betroffene Objekt-ID,
* Zeitpunkt,
* Ergebnis,
* optionale Metadaten als JSONB.

Keine Passwörter, Tokens oder geheimen Zugangsdaten protokollieren.

## 17. Performance

Die Anwendung soll von Anfang an performant und sauber aufgebaut sein.

Beachte insbesondere:

* keine unnötigen Datenbankabfragen,
* Vermeidung von N+1-Abfragen,
* sinnvolles Eager Loading,
* gezielte Datenbankindizes,
* Pagination bei Listen,
* serverseitige Filterung,
* keine unnötig großen JSON-Antworten,
* Lazy Loading von selten genutzten UI-Bereichen,
* Wiederverwendung gemeinsamer Services,
* Datenbankverbindungen über Connection Pooling,
* strukturierte Logging-Ausgaben,
* keine teuren Berechnungen in Templates,
* keine direkte Geschäftslogik in Flask-Routen.

Teile den Code in folgende Schichten:

```text
Routes beziehungsweise Controller
        ↓
Services
        ↓
Repositories beziehungsweise Datenzugriff
        ↓
SQLAlchemy und PostgreSQL
```

Die Trennung muss pragmatisch bleiben. Erzeuge keine unnötige Abstraktion ohne tatsächlichen Nutzen.

## 18. Sicherheit

Berücksichtige mindestens:

* CSRF-Schutz,
* sichere Cookies,
* HttpOnly,
* SameSite,
* konfigurierbares Secure-Flag,
* sichere Passwort-Hashes,
* serverseitige Berechtigungsprüfung,
* Schutz vor SQL-Injection durch ORM und parametrisierte Abfragen,
* Escaping in Templates,
* Validierung aller Eingaben,
* keine Secrets im Repository,
* Rate-Limiting für Login,
* Schutz vor Open Redirects,
* sichere Fehlerseiten,
* keine internen Stacktraces im Produktivbetrieb,
* Security Header,
* Content Security Policy, soweit mit der Anwendung sinnvoll möglich.

## 19. Konfiguration

Konfiguriere die Anwendung vollständig über Umgebungsvariablen.

Mindestens:

```env
FLASK_ENV=production
SECRET_KEY=
DATABASE_URL=
POSTGRES_DB=fireflight2
POSTGRES_USER=fireflight2
POSTGRES_PASSWORD=
TIMEZONE=Europe/Berlin

DJI_FLIGHTHUB_ENABLED=false
DJI_FLIGHTHUB_BASE_URL=
DJI_FLIGHTHUB_CLIENT_ID=
DJI_FLIGHTHUB_CLIENT_SECRET=
```

Erstelle eine `.env.example`, aber keine echte `.env` mit produktiven Geheimnissen.

## 20. Docker

Erstelle:

* einen sicheren Dockerfile,
* eine `.dockerignore`,
* eine `docker-compose.yml`,
* Healthchecks,
* persistentes PostgreSQL-Volume,
* internes Docker-Netzwerk,
* automatische Datenbankmigration beim Start oder einen klar dokumentierten Migrationsbefehl,
* einen produktionsgeeigneten WSGI-Server wie Gunicorn.

Der App-Container soll nicht als Root laufen.

Der App-Container soll nur die Flask-Anwendung enthalten.

Der PostgreSQL-Dienst bleibt ein separater Container.

Nutze sinnvolle Startreihenfolgen und Healthchecks. Ein einfaches `depends_on` ohne Gesundheitsprüfung reicht nicht aus.

Beispielhafte Dienste:

```text
fireflight2-app
fireflight2-db
```

Ein optionaler Reverse Proxy soll in dieser ersten Version nicht zwingend notwendig sein. Dokumentiere aber, wie später Nginx, Traefik oder ein vorhandener Reverse Proxy vorgeschaltet werden kann.

## 21. Initialisierung

Erstelle einen Initialisierungsbefehl oder ein CLI-Kommando.

Beispiel:

```bash
flask init-fireflight
```

Dieser Befehl soll:

1. die erste Organisation anlegen,
2. die Standardberechtigungen registrieren,
3. die Standardrollen anlegen,
4. für jede Rolle ein leeres Standard-Dashboard anlegen,
5. einen ersten Administrator erstellen oder interaktiv nach dessen Daten fragen.

Der Befehl muss mehrfach ausgeführt werden können, ohne Datensätze doppelt anzulegen.

Die Initialisierung muss idempotent sein.

## 22. Administrationsoberfläche

Erstelle für die erste Version folgende Administrationsbereiche:

### Benutzer

* Benutzerliste,
* Benutzer erstellen,
* Benutzer bearbeiten,
* Benutzer aktivieren und deaktivieren,
* Rollen zuweisen,
* letzte Anmeldung anzeigen.

### Rollen

* Rollenliste,
* Rolle erstellen,
* Rolle bearbeiten,
* Beschreibung,
* Icon,
* Akzentfarbe,
* Aktivstatus,
* Reihenfolge,
* Berechtigungen zuweisen,
* Benutzer der Rolle anzeigen.

### Dashboards

* Dashboard einer Rolle öffnen,
* Widgets hinzufügen,
* Widgets bearbeiten,
* Widgets entfernen,
* Position und Größe speichern,
* Vorschau anzeigen.

### Organisation

* Organisationsname,
* Kurzname,
* Zeitzone,
* Logo-Platzhalter,
* grundlegende Einstellungen.

### Integrationen

* DJI-FlightHub-2-Status,
* Konfiguration,
* simulierte Synchronisierung,
* Synchronisationshistorie,
* Fehlerstatus.

### Audit-Log

* Liste der Audit-Einträge,
* Filter nach Benutzer,
* Filter nach Aktion,
* Filter nach Zeitraum,
* Pagination.

## 23. Tests

Erstelle automatisierte Tests.

Mindestens:

* Login erfolgreich,
* Login fehlgeschlagen,
* deaktivierter Benutzer kann sich nicht anmelden,
* Rollenauswahl funktioniert,
* Benutzer sieht nur zugewiesene Rollen,
* Rollenwechsel funktioniert,
* Berechtigungsprüfung verweigert unzulässigen Zugriff,
* Administrator kann Rolle erstellen,
* Administrator kann Berechtigungen zuweisen,
* Dashboard kann geladen werden,
* Widget kann gespeichert werden,
* Initialisierung ist idempotent,
* DJI-Mock-Synchronisierung erzeugt einen Synchronisationslauf,
* Audit-Log wird geschrieben.

Verwende eine getrennte Testkonfiguration.

## 24. Dokumentation

Erstelle eine ausführliche `README.md`.

Die Dokumentation muss enthalten:

* Projektbeschreibung,
* Architekturübersicht,
* Ordnerstruktur,
* Voraussetzungen,
* Installation,
* Docker-Start,
* Initialisierung,
* Migrationen,
* Tests,
* Umgebungsvariablen,
* Standardrollen,
* Berechtigungssystem,
* Modulsystem,
* Dashboard-System,
* DJI-Integrationsarchitektur,
* Backup der PostgreSQL-Datenbank,
* Update-Vorgehen,
* produktiver Betrieb hinter einem Reverse Proxy.

## 25. Vorgehensweise

Arbeite strukturiert in Phasen.

### Phase 1: Architektur und Projektgrundlage

* Projektstruktur,
* Docker,
* Flask Application Factory,
* Konfiguration,
* PostgreSQL,
* SQLAlchemy,
* Migrationen,
* Logging,
* Fehlerbehandlung.

### Phase 2: Authentifizierung

* Benutzer,
* Login,
* Logout,
* Sitzungen,
* Passwort-Hashing,
* Sicherheitsmaßnahmen.

### Phase 3: Rollen und Berechtigungen

* Rollen,
* Permissions,
* Zuordnungen,
* Berechtigungsprüfung,
* Rollenauswahl,
* Rollenwechsel.

### Phase 4: Dashboards

* Dashboard-Datenmodell,
* Widget-Registry,
* erste Basiswidgets,
* Rollen-Dashboard,
* Administrationseditor.

### Phase 5: Modul-Registry

* Modul-Basisklasse,
* Modulregistrierung,
* Registrierung von Navigation,
* Registrierung von Berechtigungen,
* Registrierung von Widgets.

### Phase 6: DJI-Grundstruktur

* Integrationsinterface,
* Mock-Connector,
* Synchronisationsläufe,
* Statusseite,
* Fehlerbehandlung.

### Phase 7: Tests und Dokumentation

* Unit-Tests,
* Integrationstests,
* README,
* Beispielkonfiguration.

## 26. Wichtige Einschränkungen

In dieser ersten Version nicht vollständig implementieren:

* echte Einsatzverwaltung,
* vollständiges Flugbuch,
* vollständige Geräteverwaltung,
* Karten- und GIS-Funktionen,
* Medienstreaming,
* vollständige Live-Telemetrie,
* reale DJI-Produktivintegration ohne bestätigte API-Dokumentation,
* komplexe Mandantenfähigkeit,
* Microservices,
* Kubernetes,
* unnötige Message Broker,
* unnötige externe Abhängigkeiten.

Erstelle stattdessen saubere Erweiterungspunkte und gut erkennbare Platzhalter.

## 27. Qualitätsanforderungen

Der Code muss:

* verständlich,
* wartbar,
* modular,
* sicher,
* performant,
* testbar,
* dokumentiert,
* typisiert, soweit sinnvoll,
* konsistent formatiert sein.

Verwende:

* Type Hints,
* Docstrings für wichtige Services und Interfaces,
* sprechende Namen,
* zentrale Konstanten,
* zentrale Fehlerklassen,
* strukturierte Logs,
* klar getrennte Konfigurationen für Entwicklung, Test und Produktion.

Vermeide:

* riesige einzelne Dateien,
* globale Datenbankzugriffe,
* Geschäftslogik in Templates,
* Geschäftslogik in Routen,
* hart codierte Rollennamen für Berechtigungsprüfungen,
* hart codierte Geheimnisse,
* unkontrollierte direkte Abhängigkeiten zwischen Modulen,
* unnötige Frontend-Komplexität.

## 28. Gewünschtes Ergebnis

Erstelle ein startfähiges Projekt, das nach folgenden Befehlen funktioniert:

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec fireflight2-app flask init-fireflight
```

Danach soll die Anwendung im Browser erreichbar sein.

Der Benutzer soll:

1. sich anmelden,
2. seine Rolle auswählen,
3. das zur Rolle gehörende Dashboard sehen,
4. die Rolle über ein Dropdown wechseln können.

Ein Administrator soll:

1. Benutzer verwalten,
2. Rollen erstellen und bearbeiten,
3. Berechtigungen zuweisen,
4. Benutzer Rollen zuweisen,
5. Rollen-Dashboards konfigurieren,
6. Basiswidgets hinzufügen,
7. den DJI-Integrationsstatus sehen,
8. eine simulierte Synchronisierung starten,
9. das Audit-Log einsehen können.

Beginne mit einer kurzen Architekturübersicht und setze danach das Projekt direkt um.

Triff bei kleineren offenen Fragen selbstständig sinnvolle, pragmatische Entscheidungen. Dokumentiere wichtige Architekturentscheidungen in einer Datei wie:

```text
docs/architecture.md
```

Erstelle keine unnötigen Funktionen außerhalb des beschriebenen Umfangs. Priorisiere einen stabilen, sauberen und erweiterbaren Kern gegenüber möglichst vielen unfertigen Funktionen.
