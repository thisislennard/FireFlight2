from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from flask import current_app


def to_local(dt: datetime | None) -> datetime | None:
    """Wandelt einen UTC-Zeitstempel in die konfigurierte Anzeige-Zeitzone um (Standard Europe/Berlin)."""
    if dt is None:
        return None
    tz_name = current_app.config.get("TIMEZONE", "Europe/Berlin")
    return dt.astimezone(ZoneInfo(tz_name))


def parse_local_datetime(value: str | None) -> datetime | None:
    """Gegenstück zu to_local(): liest einen `<input type="datetime-local">`-Formularwert
    (naiv, in der konfigurierten Anzeige-Zeitzone) und wandelt ihn nach UTC für die Speicherung
    (app/modules/incidents/routes.py)."""
    if not value:
        return None
    naive_local = datetime.strptime(value, "%Y-%m-%dT%H:%M")
    tz_name = current_app.config.get("TIMEZONE", "Europe/Berlin")
    return naive_local.replace(tzinfo=ZoneInfo(tz_name)).astimezone(timezone.utc)
