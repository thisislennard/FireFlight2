from __future__ import annotations

from datetime import datetime

from app.core.utilities.time import to_local
from app.modules.weather import services


def current_weather_widget_data(widget) -> dict:
    """Datenquelle für das DWD-Wetter-Widget (`_widget_weather.html`, Phase 14) -- als Jinja-Global
    registriert (app/modules/weather/module.py), analog zum Muster aus Phase 13. Keine eigene
    Berechtigungsprüfung nötig: Wetterdaten sind nicht organisationsbezogen/sensibel, jede Rolle mit
    dem Widget auf ihrem Dashboard darf es sehen."""
    weather = services.get_current_weather()
    if weather is None:
        return {"available": False, "weather": None}
    weather = dict(weather)
    if weather.get("timestamp"):
        try:
            weather["timestamp"] = to_local(datetime.fromisoformat(weather["timestamp"]))
        except ValueError:
            weather["timestamp"] = None
    return {"available": True, "weather": weather}
