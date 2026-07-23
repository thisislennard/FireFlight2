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
]

DEFAULT_ROLES = [
    {
        "key": "documentation", "name": "Dokumentation", "icon": "file-text", "sort_order": 10,
        "permissions": ["dashboard.view"],
    },
    {
        "key": "unit_leader", "name": "Einheitsführer", "icon": "shield", "sort_order": 20,
        "permissions": ["dashboard.view", "users.view"],
    },
    {
        "key": "pilot_camera", "name": "Pilot/Kamera", "icon": "video", "sort_order": 30,
        "permissions": ["dashboard.view"],
    },
    {
        "key": "flight_leader", "name": "Flugleiter", "icon": "navigation", "sort_order": 40,
        "permissions": ["dashboard.view"],
    },
    {
        "key": "incident_commander", "name": "Einsatzleiter/SBI", "icon": "radio", "sort_order": 50,
        "permissions": ["dashboard.view", "users.view"],
    },
    {
        "key": "equipment_officer", "name": "Gerätewart", "icon": "tool", "sort_order": 60,
        "permissions": ["dashboard.view"],
    },
    {
        "key": "tel_elw", "name": "TEL-ELW", "icon": "truck", "sort_order": 70,
        "permissions": ["dashboard.view"],
    },
    {
        # is_system=True -> automatisch alle Berechtigungen (app/core/security/permissions.py),
        # zusätzlich besonders geschützt (kann nicht deaktiviert werden, letzter Administrator
        # kann nicht entfernt werden, s. app/roles/services.py).
        "key": "administrator", "name": "Administrator", "icon": "settings", "sort_order": 100,
        "is_system": True, "permissions": [],
    },
]
