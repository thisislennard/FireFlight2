from __future__ import annotations

from flask import current_app

from app.modules.opensky import services


def nearby_aircraft_widget_data(widget) -> dict:
    """Datenquelle für das OpenSky-Luftraum-Widget (`_widget_opensky_map.html`, Phase 14) -- als
    Jinja-Global registriert (app/modules/opensky/module.py). Keine eigene Berechtigungsprüfung
    nötig, analog zum Wetter-Widget: öffentliche, nicht organisationsbezogene Daten."""
    aircraft = services.get_nearby_aircraft()
    return {
        "available": aircraft is not None,
        "aircraft": aircraft or [],
        "center": {"lat": current_app.config["OPENSKY_LOCATION_LAT"], "lon": current_app.config["OPENSKY_LOCATION_LON"]},
    }
