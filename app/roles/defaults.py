"""Zentrale Registry der Standard-Berechtigungen und -Rollen (spec-struktur.md Abschnitte 7 & 9).

Wird bei der Ersteinrichtung (`flask init-fireflight`) in die Datenbank geseedet — Administratoren
können Rollen/Berechtigungen danach über die Administrationsoberfläche anpassen. Diese Liste ist der
Ausgangszustand, nicht die einzige Quelle der Wahrheit zur Laufzeit.
"""

DEFAULT_PERMISSIONS = [
    ("dashboard.view", "Dashboard ansehen"),
    ("dashboard.edit", "Eigenes Dashboard bearbeiten"),
    ("dashboard.manage", "Dashboards aller Rollen verwalten"),
    ("users.view", "Benutzer ansehen"),
    ("users.create", "Benutzer anlegen"),
    ("users.edit", "Benutzer bearbeiten"),
    ("users.disable", "Benutzer aktivieren/deaktivieren"),
    ("users.assign_roles", "Rollen zuweisen"),
    ("roles.view", "Rollen ansehen"),
    ("roles.create", "Rollen anlegen"),
    ("roles.edit", "Rollen bearbeiten"),
    ("roles.disable", "Rollen deaktivieren"),
    ("roles.assign_permissions", "Berechtigungen zuweisen"),
    ("organization.view", "Organisation ansehen"),
    ("organization.edit", "Organisation bearbeiten"),
    ("administration.access", "Administrationsbereich betreten"),
    ("audit.view", "Audit-Log ansehen"),
    ("settings.view", "Einstellungen ansehen"),
    ("settings.edit", "Einstellungen bearbeiten"),
    ("rc_devices.view", "RC-Geräte ansehen"),
    ("rc_devices.manage", "RC-Geräte anlegen/koppeln/deaktivieren"),
    ("units.view", "Drohneneinheiten ansehen"),
    ("units.manage", "Drohneneinheiten anlegen/bearbeiten/Manager zuweisen"),
    ("wizards.view", "Wizards ansehen/Vorschau"),
    ("wizards.manage", "Wizards anlegen/bearbeiten/Schritte konfigurieren"),
]

DEFAULT_ROLES = [
    {
        # Rollenname deutet direkt auf die Zuständigkeit fürs Flugbuch hin.
        "key": "documentation", "name": "Dokumentation", "icon": "file-text", "sort_order": 10,
        "permissions": ["dashboard.view", "incidents.view", "incidents.edit"],
    },
    {
        "key": "unit_leader", "name": "Einheitsführer", "icon": "shield", "sort_order": 20,
        "permissions": ["dashboard.view", "users.view", "incidents.view"],
    },
    {
        # Pilot/Kamera-Crew ist laut Konzeptdokument (Abschnitt 5.2-5.5) diejenige, die Flüge am
        # RC Plus selbst erfasst -- braucht daher auch am Desktop Bearbeitungsrechte.
        "key": "pilot_camera", "name": "Pilot/Kamera", "icon": "video", "sort_order": 30,
        "permissions": ["dashboard.view", "incidents.view", "incidents.edit"],
    },
    {
        "key": "flight_leader", "name": "Flugleiter", "icon": "navigation", "sort_order": 40,
        "permissions": ["dashboard.view", "incidents.view", "incidents.edit"],
    },
    {
        "key": "incident_commander", "name": "Einsatzleiter/SBI", "icon": "radio", "sort_order": 50,
        "permissions": ["dashboard.view", "users.view", "incidents.view", "incidents.edit"],
    },
    {
        "key": "equipment_officer", "name": "Gerätewart", "icon": "tool", "sort_order": 60,
        "permissions": ["dashboard.view"],
    },
    {
        "key": "tel_elw", "name": "TEL-ELW", "icon": "truck", "sort_order": 70,
        "permissions": ["dashboard.view", "incidents.view"],
    },
    {
        # is_system=True -> automatisch alle Berechtigungen (app/core/security/permissions.py),
        # zusätzlich besonders geschützt (kann nicht deaktiviert werden, letzter Administrator
        # kann nicht entfernt werden, s. app/roles/services.py).
        "key": "administrator", "name": "Administrator", "icon": "settings", "sort_order": 100,
        "is_system": True, "permissions": [],
    },
]
