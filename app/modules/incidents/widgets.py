from __future__ import annotations

from flask_login import current_user

from app.core.security.permissions import get_active_role, role_has_permission
from app.modules.incidents import services

_DEFAULT_LIMIT = 10


def flight_map_widget_data(widget) -> dict:
    """Datenquelle für das Flugbuch-/Karten-Widget (`_widget_flight_map.html`, Phase 13) -- als
    Jinja-Global registriert statt über den Request-Kontext, s. app/modules/base.py:
    register_template_globals. Prüft die Berechtigung selbst statt sich auf `has_permission()` aus
    dem Template zu verlassen, da diese Context-Processor-Werte im Widget-Include nicht sichtbar
    sind (nur echte Globals)."""
    role = get_active_role()
    if not role_has_permission(role, "incidents.view"):
        return {"allowed": False, "markers": []}
    limit = (widget.config or {}).get("limit") or _DEFAULT_LIMIT
    flights = services.list_flights_with_location(current_user.organization_id, limit=limit)
    return {"allowed": True, "markers": [services.serialize_flight_marker(f) for f in flights]}
