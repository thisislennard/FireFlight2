from datetime import datetime
from zoneinfo import ZoneInfo

from flask import current_app


def to_local(dt: datetime | None) -> datetime | None:
    """Wandelt einen UTC-Zeitstempel in die konfigurierte Anzeige-Zeitzone um (Standard Europe/Berlin)."""
    if dt is None:
        return None
    tz_name = current_app.config.get("TIMEZONE", "Europe/Berlin")
    return dt.astimezone(ZoneInfo(tz_name))
