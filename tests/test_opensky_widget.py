import pytest
import requests

from app.core.utilities import external_cache
from app.modules.opensky import services
from tests.conftest import login

_AIRCRAFT_WITH_POSITION = [
    "3c6444", "DLH9LP  ", "Germany", 1690000000, 1690000000, 8.50, 50.10, 3048.0, False,
    210.5, 90.0, 0.0, None, 3100.0, "1000", False, 0,
]
_AIRCRAFT_WITHOUT_POSITION = [
    "abcdef", None, "France", None, 1690000000, None, None, None, True,
    None, None, None, None, None, None, False, 0,
]

_SAMPLE_RESPONSE = {"time": 1690000000, "states": [_AIRCRAFT_WITH_POSITION, _AIRCRAFT_WITHOUT_POSITION]}


class _FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def _reset_cache():
    external_cache.reset()
    yield
    external_cache.reset()


# --- Service ---------------------------------------------------------------------------------


def test_get_nearby_aircraft_parses_and_filters_positionless_entries(app, monkeypatch):
    monkeypatch.setattr(services.requests, "get", lambda *a, **k: _FakeResponse(_SAMPLE_RESPONSE))
    with app.app_context():
        aircraft = services.get_nearby_aircraft()
    assert len(aircraft) == 1
    entry = aircraft[0]
    assert entry["icao24"] == "3c6444"
    assert entry["callsign"] == "DLH9LP"
    assert entry["lat"] == 50.10
    assert entry["lon"] == 8.50
    assert entry["altitude_m"] == 3048.0
    assert entry["velocity_kmh"] == round(210.5 * 3.6)


def test_get_nearby_aircraft_returns_none_on_request_error(app, monkeypatch):
    monkeypatch.setattr(services.requests, "get", lambda *a, **k: (_ for _ in ()).throw(requests.ConnectionError()))
    with app.app_context():
        assert services.get_nearby_aircraft() is None


def test_get_nearby_aircraft_is_cached_within_ttl(app, monkeypatch):
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(1)
        return _FakeResponse(_SAMPLE_RESPONSE)

    monkeypatch.setattr(services.requests, "get", fake_get)
    with app.app_context():
        services.get_nearby_aircraft()
        services.get_nearby_aircraft()
    assert len(calls) == 1


def test_bounding_box_is_centered_on_configured_location(app):
    with app.app_context():
        bbox = services._bounding_box(50.08, 8.45, 50)
    assert bbox["lamin"] < 50.08 < bbox["lamax"]
    assert bbox["lomin"] < 8.45 < bbox["lomax"]


# --- Widget/Dashboard --------------------------------------------------------------------------


def test_opensky_widget_registered(app):
    from app.dashboards.widgets import widget_registry

    definition = widget_registry.get("opensky.map")
    assert definition is not None
    assert definition.template == "modules/opensky/_widget_opensky_map.html"


def test_opensky_widget_renders_data_on_dashboard(client, app, organization, roles, regular_user, monkeypatch):
    from app.dashboards.services import add_widget, get_or_create_dashboard

    monkeypatch.setattr(services.requests, "get", lambda *a, **k: _FakeResponse(_SAMPLE_RESPONSE))

    dashboard = get_or_create_dashboard(roles["pilot_camera"])
    add_widget(dashboard, widget_type="opensky.map", title=None, config={})

    login(client, username="pilot")
    client.post(f"/roles/activate/{roles['pilot_camera'].id}")
    response = client.get("/dashboard/")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "opensky-widget-map" in body
    assert "DLH9LP" in body


def test_opensky_widget_shows_unavailable_state_on_error(client, app, organization, roles, regular_user, monkeypatch):
    from app.dashboards.services import add_widget, get_or_create_dashboard

    monkeypatch.setattr(services.requests, "get", lambda *a, **k: (_ for _ in ()).throw(requests.Timeout()))

    dashboard = get_or_create_dashboard(roles["pilot_camera"])
    add_widget(dashboard, widget_type="opensky.map", title=None, config={})

    login(client, username="pilot")
    client.post(f"/roles/activate/{roles['pilot_camera'].id}")
    response = client.get("/dashboard/")
    assert "aktuell nicht verfügbar" in response.get_data(as_text=True)
