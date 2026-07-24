from __future__ import annotations

import logging
import math

import requests
from flask import current_app

from app.core.utilities.external_cache import cached

logger = logging.getLogger(__name__)

_STATES_URL = "https://opensky-network.org/api/states/all"
_REQUEST_TIMEOUT_SECONDS = 5
_MAX_AIRCRAFT = 30

# Reihenfolge der Felder im "states"-Array laut OpenSky-REST-Doku (ohne `extended=1`, das die
# Aircraft-Category als zusätzliches 18. Feld anhängen würde -- hier nicht angefordert, da für die
# reine Anzeige nicht gebraucht).
_ICAO24, _CALLSIGN, _ORIGIN_COUNTRY, _LONGITUDE, _LATITUDE = 0, 1, 2, 5, 6
_BARO_ALTITUDE, _ON_GROUND, _VELOCITY, _TRUE_TRACK, _VERTICAL_RATE = 7, 8, 9, 10, 11
_GEO_ALTITUDE = 13


def _bounding_box(lat: float, lon: float, radius_km: float) -> dict[str, float]:
    """Grobe Bounding-Box um einen Mittelpunkt -- für die Größenordnung dieser Anwendung (lokale
    Luftraumbeobachtung um Liederbach) reicht die Kleinwinkelnäherung, keine Großkreisberechnung
    nötig."""
    delta_lat = radius_km / 111.0
    delta_lon = radius_km / (111.0 * max(math.cos(math.radians(lat)), 0.01))
    return {
        "lamin": lat - delta_lat, "lamax": lat + delta_lat,
        "lomin": lon - delta_lon, "lomax": lon + delta_lon,
    }


def _fetch_nearby_aircraft() -> list[dict] | None:
    lat = current_app.config["OPENSKY_LOCATION_LAT"]
    lon = current_app.config["OPENSKY_LOCATION_LON"]
    radius_km = current_app.config["OPENSKY_RADIUS_KM"]
    bbox = _bounding_box(lat, lon, radius_km)
    try:
        response = requests.get(_STATES_URL, params=bbox, timeout=_REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        states = response.json().get("states") or []
    except (requests.RequestException, ValueError) as exc:
        logger.warning("OpenSky-Abruf fehlgeschlagen: %s", exc)
        return None

    aircraft = []
    for state in states:
        state_lat, state_lon = state[_LATITUDE], state[_LONGITUDE]
        if state_lat is None or state_lon is None:
            continue  # Kein aktueller Positionsempfang (z. B. Transponder ohne ADS-B-Out).
        velocity_ms = state[_VELOCITY]
        aircraft.append({
            "icao24": state[_ICAO24],
            "callsign": (state[_CALLSIGN] or "").strip() or None,
            "origin_country": state[_ORIGIN_COUNTRY],
            "lat": state_lat,
            "lon": state_lon,
            "altitude_m": state[_BARO_ALTITUDE] if state[_BARO_ALTITUDE] is not None else state[_GEO_ALTITUDE],
            "velocity_kmh": round(velocity_ms * 3.6) if velocity_ms is not None else None,
            "track": state[_TRUE_TRACK],
            "on_ground": bool(state[_ON_GROUND]),
        })
    return aircraft[:_MAX_AIRCRAFT]


def get_nearby_aircraft() -> list[dict] | None:
    """Flugzeuge im konfigurierten Radius um den Standort (`OPENSKY_LOCATION_LAT/LON`,
    `OPENSKY_RADIUS_KM`), kurzzeitig gecacht (`OPENSKY_CACHE_SECONDS`, s. dort für die
    Rate-Limit-Begründung) -- `None`, wenn OpenSky nicht erreichbar war."""
    ttl = current_app.config["OPENSKY_CACHE_SECONDS"]
    return cached("opensky:states", ttl, _fetch_nearby_aircraft)
