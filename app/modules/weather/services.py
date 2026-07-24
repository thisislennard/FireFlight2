from __future__ import annotations

import logging

import requests
from flask import current_app

from app.core.utilities.external_cache import cached

logger = logging.getLogger(__name__)

_BRIGHT_SKY_URL = "https://api.brightsky.dev/current_weather"
_REQUEST_TIMEOUT_SECONDS = 5

# Bright Sky (https://brightsky.dev/) ist ein freier Wrapper um die DWD-Open-Data-Schnittstelle --
# kein API-Key nötig, liefert Messwerte der nächstgelegenen DWD-Station zu gegebenen Koordinaten.
# Für Flugbetrieb relevante Teilmenge der Felder ausgewählt (Konzeptdokument Abschnitt 10: "relevant
# für Drohnenbetrieb" -- Wind/Böen/Sicht/Niederschlag stehen daher vor reinen Komfortwerten).
_RELEVANT_FIELDS = [
    "temperature", "condition", "icon", "wind_speed_10", "wind_gust_speed_10", "wind_direction_10",
    "precipitation_10", "cloud_cover", "visibility", "timestamp",
]


def _fetch_current_weather() -> dict | None:
    lat = current_app.config["WEATHER_LOCATION_LAT"]
    lon = current_app.config["WEATHER_LOCATION_LON"]
    try:
        response = requests.get(
            _BRIGHT_SKY_URL, params={"lat": lat, "lon": lon}, timeout=_REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        weather = response.json().get("weather") or {}
    except (requests.RequestException, ValueError) as exc:
        logger.warning("DWD-Wetterabruf (Bright Sky) fehlgeschlagen: %s", exc)
        return None
    return {field: weather.get(field) for field in _RELEVANT_FIELDS}


def get_current_weather() -> dict | None:
    """Aktuelle Wetterdaten für den Standort aus `WEATHER_LOCATION_LAT/LON`, kurzzeitig gecacht
    (`WEATHER_CACHE_SECONDS`) -- `None`, wenn Bright Sky/DWD nicht erreichbar war."""
    ttl = current_app.config["WEATHER_CACHE_SECONDS"]
    return cached("weather:current", ttl, _fetch_current_weather)
