"""Bekanntes Vokabular für `WizardStep.field_key` (Phase 12) -- bildet Antworten eines RC-
Wizard-Laufs generisch auf Felder von `Incident`/`Flight` ab, s. app/rc/wizard_flow.py.

Bewusst nicht Teil von app/wizards/ (die Engine bleibt fachlich neutral, kennt kein Flugbuch) --
dieses Modul importiert *von* der Wizard-Engine, nicht umgekehrt. Der Admin-Step-Editor
(app/administration/routes.py) importiert diese Liste nur für die Auswahl-Dropdown-Anzeige.
"""
from __future__ import annotations

FIELD_KEY_PURPOSE = "purpose"
FIELD_KEY_INCIDENT_KIND = "incident_kind"
FIELD_KEY_START_LOCATION = "start_location"
FIELD_KEY_END_LOCATION = "end_location"
FIELD_KEY_SYNCED = "synced"
FIELD_KEY_HAD_ISSUES = "had_issues"
FIELD_KEY_NOTES = "notes"

# (Wert, Label, Hinweis) -- Hinweis erklärt im Step-Editor, welcher Step-Typ dazu erwartet wird.
RC_WIZARD_FIELD_CHOICES: list[tuple[str, str, str]] = [
    ("", "Keine Zuordnung", ""),
    (FIELD_KEY_PURPOSE, "Zweck des Fluges", "erwartet Step-Typ „Freitext“"),
    (FIELD_KEY_INCIDENT_KIND, "Einsatz/Übung", 'erwartet Step-Typ „Auswahl“ mit Optionen "Einsatz"/"Übung"'),
    (FIELD_KEY_START_LOCATION, "Start-Standort", "erwartet Step-Typ „Standort erfassen“"),
    (FIELD_KEY_END_LOCATION, "End-Standort", "erwartet Step-Typ „Standort erfassen“"),
    # Bewusst "Auswahl" statt "Bestätigung": Bestätigung verlangt laut app/wizards/step_types.py
    # IMMER eine angehakte Checkbox zum Weiterkommen (validate: answer is True) -- für echte
    # Ja/Nein-Fragen, bei denen beide Antworten gültig sein müssen, ist "Auswahl" mit den Optionen
    # "Ja"/"Nein" der richtige Step-Typ (app/rc/routes.py interpretiert die Antwort "Ja" als true).
    (FIELD_KEY_SYNCED, "Flüge synchronisiert?", 'erwartet Step-Typ „Auswahl“ mit Optionen "Ja"/"Nein"'),
    (FIELD_KEY_HAD_ISSUES, "Gab es Mängel?", 'erwartet Step-Typ „Auswahl“ mit Optionen "Ja"/"Nein"'),
    (FIELD_KEY_NOTES, "Notizen", "erwartet Step-Typ „Freitext“"),
]
