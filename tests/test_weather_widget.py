import pytest
import requests

from app.core.utilities import external_cache
from app.modules.weather import services
from tests.conftest import login

_SAMPLE_RESPONSE = {
    "weather": {
        "temperature": 13.6, "condition": "dry", "icon": "cloudy", "wind_speed_10": 8.3,
        "wind_gust_speed_10": 12.2, "wind_direction_10": 280, "precipitation_10": 0.0,
        "cloud_cover": 100, "visibility": 38666, "timestamp": "2026-07-24T06:00:00+00:00",
    },
    "sources": [{"id": 1}],
}


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


def test_get_current_weather_success(app, monkeypatch):
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append((url, params, timeout))
        return _FakeResponse(_SAMPLE_RESPONSE)

    monkeypatch.setattr(services.requests, "get", fake_get)
    with app.app_context():
        weather = services.get_current_weather()
    assert weather["temperature"] == 13.6
    assert weather["condition"] == "dry"
    assert len(calls) == 1


def test_get_current_weather_returns_none_on_request_error(app, monkeypatch):
    def fake_get(url, params=None, timeout=None):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(services.requests, "get", fake_get)
    with app.app_context():
        assert services.get_current_weather() is None


def test_get_current_weather_returns_none_on_http_error(app, monkeypatch):
    monkeypatch.setattr(services.requests, "get", lambda *a, **k: _FakeResponse({}, status=503))
    with app.app_context():
        assert services.get_current_weather() is None


def test_get_current_weather_is_cached_within_ttl(app, monkeypatch):
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(1)
        return _FakeResponse(_SAMPLE_RESPONSE)

    monkeypatch.setattr(services.requests, "get", fake_get)
    with app.app_context():
        services.get_current_weather()
        services.get_current_weather()
    assert len(calls) == 1


# --- Widget/Dashboard --------------------------------------------------------------------------


def test_weather_widget_registered(app):
    from app.dashboards.widgets import widget_registry

    definition = widget_registry.get("weather.current")
    assert definition is not None
    assert definition.template == "modules/weather/_widget_weather.html"


def test_weather_widget_renders_data_on_dashboard(client, app, organization, roles, regular_user, monkeypatch):
    from app.dashboards.services import add_widget, get_or_create_dashboard

    monkeypatch.setattr(services.requests, "get", lambda *a, **k: _FakeResponse(_SAMPLE_RESPONSE))

    dashboard = get_or_create_dashboard(roles["pilot_camera"])
    add_widget(dashboard, widget_type="weather.current", title=None, config={})

    login(client, username="pilot")
    client.post(f"/roles/activate/{roles['pilot_camera'].id}")
    response = client.get("/dashboard/")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "13.6 °C" in body
    assert "dry" in body


def test_weather_widget_shows_unavailable_state_on_error(client, app, organization, roles, regular_user, monkeypatch):
    from app.dashboards.services import add_widget, get_or_create_dashboard

    monkeypatch.setattr(services.requests, "get", lambda *a, **k: (_ for _ in ()).throw(requests.Timeout()))

    dashboard = get_or_create_dashboard(roles["pilot_camera"])
    add_widget(dashboard, widget_type="weather.current", title=None, config={})

    login(client, username="pilot")
    client.post(f"/roles/activate/{roles['pilot_camera'].id}")
    response = client.get("/dashboard/")
    assert "aktuell nicht verfügbar" in response.get_data(as_text=True)
