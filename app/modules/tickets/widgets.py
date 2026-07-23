from __future__ import annotations

from app.core.security.permissions import get_active_role, role_has_permission


def report_form_widget_data(widget) -> dict:
    """Datenquelle für das "Technisches Problem melden"-Widget (`_widget_report_form.html`,
    Phase 13, Konzeptdokument Abschnitt 9) -- als Jinja-Global registriert statt über den
    Request-Kontext, s. app/modules/base.py: register_template_globals."""
    role = get_active_role()
    return {"allowed": role_has_permission(role, "tickets.create")}
