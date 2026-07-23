# Fireflight 2 – Konzeptnotizen (strukturiert)

## 1. Zugriffswege

Fireflight 2 wird über zwei getrennte Zugänge genutzt:

1. **Büro-Nutzung** – Zugriff über Laptop, Tablet oder Handy als normale Website, mit Möglichkeit zur Installation als PWA.
2. **DJI RC Plus** – gesonderter Link, der als eigene PWA auf der Fernbedienung installiert wird.

## 2. Tech Stack

- Flask
- CSS
- PostgreSQL-Datenbank
- Alles containerisiert in Docker

## 3. Rollen- und Login-System (Desktop)

- Login über Username + selbst änderbare 4-stellige PIN
- Nach Login: Rollen-Auswahl (immer nur eine Rolle gleichzeitig aktiv)
- Unten rechts dauerhaft ein „Rolle wechseln“-Button
- Nach Rollen-Auswahl: Weiterleitung auf das zur Rolle passende Dashboard
- Ein User sieht bei der Rollen-Auswahl nur die Rollen, die ihm zugewiesen sind – nicht zugewiesene Rollen erscheinen gar nicht erst
- Definition, welche Rolle was darf, ist später durch den Admin konfigurierbar (Details noch offen)

## 4. Dashboard-System

- Dashboards und Rollen sollen **modular** aufgebaut sein
- Alle Module (Livestream, Fluginformationen, Standorte, etc.) liegen zunächst im Admin-Bereich
- Der Admin baut daraus die Dashboards pro Rolle selbst zusammen
- Konkrete Inhalte der einzelnen Dashboards sind noch nicht abschließend definiert

## 5. DJI RC Plus – PWA

### 5.1 Anmeldung
- Beide Fernbedienungen sind dauerhaft in der PWA angemeldet (eine als Pilot, eine als Kamera-Operator)
- Beim Öffnen startet ein Wizard (durch Admin am Desktop frei konfigurierbar)
- Schritt 1: Auswahl, welcher User die Fernbedienung gerade bedient (nur User mit passender Qualifikation – Pilot oder Kamera-Operator, werden angezeigt)
  - Ein User kann beide Qualifikationen haben und somit an beiden Fernbedienungen genutzt werden
  - Pro Fernbedienung jedoch immer nur ein User gleichzeitig
- Schritt 2: PIN-Abfrage des ausgewählten Users

### 5.2 Preflight-Check (Wizard)
Nach erfolgreicher PIN-Eingabe:
- Preflight-Checkliste: Flug angemeldet, Drohne richtig aufgeklappt, Umfeld beachtet, Luftraum kontrolliert, etc.
- Abfrage: Einsatz oder Übung
- Bei beiden: Freitextfeld, worum es geht
- PWA erfasst automatisch Standort und Uhrzeit → Eintrag in die Flugliste

### 5.3 Flugstart
- Button „Flug starten“
- Bestimmte Funktionen/Rollen erhalten Push-Benachrichtigung (z. B. Flugleiter wird über Start informiert)
- Zusätzlich: Möglichkeit, eine **Startanfrage** zu stellen, die über die Desktop-Version genehmigt werden muss
- Nach Genehmigung: Button „Zu DJI Pilot 2 springen“ → öffnet die DJI-Pilot-2-App

### 5.4 Während des Flugs
- PWA läuft im Hintergrund weiter
- Flugleiter (o. ä. Funktion) kann Push-Benachrichtigungen an die Fernbedienungen senden
- Push-Benachrichtigungen sind eine essenzielle Kernfunktion

### 5.5 Flugende
- User kehrt zur PWA zurück, beendet den Flug
- Erneute Erfassung von Standort und Uhrzeit
- Abschlussfragen, z. B.: Flüge synchronisiert?, Gab es Mängel?, etc.

### 5.6 Wizard – allgemeine Regeln
- Einzelne Wizard-Seiten sind frei konfigurierbar
- Layout ist immer gleich: unten rechts „Weiter“-Button, unten links „Zurück“-Button
- Weiterkommen erst möglich, wenn bestimmte Aktionen auf der Seite ausgeführt wurden
- Admin kann den Wizard am Desktop konfigurieren, inkl. Vorschau
- Am Ende des Wizards: Seite mit Auswahl „Selbe Person, neuer Flug“ oder „Komplett neu“ → startet Wizard von vorne

## 6. Einsatz / Übung – Konzept

- Ein Einsatz oder eine Übung kann mehrere Flüge umfassen
- An der Fernbedienung kann man sich in einen laufenden Einsatz/Übung einbuchen, um dort weiterzumachen
- Im Logbuch soll pro Person sichtbar sein, wie viele Einsatzflüge und Übungsflüge gemacht wurden – filterbar nach Jahr und Monat

## 7. Logbuch

- Zeigt pro Person die Anzahl an Einsatz- und Übungsflügen
- Filterbar nach Jahr und Monat

## 8. Nutzerprofil

Jeder User hat ein eigenes Profil mit:
- Profilbild (änderbar)
- Persönliche Daten (E-Mail, Telefonnummer)
- Übersicht: in welcher Drohneneinheit er sich befindet
- Übersicht: welche Einheit(en) er ggf. managen darf (falls mehrere vorhanden)
- Übersicht: welche Funktion er hat (Pilot / Kamera-Operator)
- Übersicht: welche Rollen er hat

## 9. Dashboard-Module (Übersicht)

- **Livestream** – Auswahl eines Streams oder bis zu 4 gleichzeitig, je nachdem welche aktiv sind
- **Push-Benachrichtigung an Fernbedienungen senden** – mit Auswahl, an welche (Fernbedienungen müssen entsprechend gepflegt werden)
- **Flüge genehmigen**
- **Drohnen-Status-Übersicht** – wo läuft gerade ein Flug, wo nicht, wer fliegt, wer ist Kamera-Operator
- **Aktive Rollen im Einsatz** – welche Rollen sind gerade in meinem Einsatz aktiv
- **Karte** – aktuelle Standorte der Piloten
- **Wetterdaten vom DWD** – relevant für Drohnenbetrieb
- **OpenSkyMap-Einbindung** – zur frühzeitigen Erkennung von Flugzeugen
- **Technisches Problem** – Ticket erstellen, inkl. Foto-Möglichkeit

## 10. Rollen ohne Dashboard

- Bestimmte Rollen (z. B. **Gerätewarte**) haben kein klassisches Dashboard, sondern nur ein Ticket-System für Probleme an der Drohne etc.
- Diese Rollen können außerdem Wartungsintervalle setzen und erhalten dazu Push-Benachrichtigungen
