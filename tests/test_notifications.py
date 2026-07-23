import pytest
import requests
from pywebpush import WebPushException

from app.extensions import db
from app.notifications import service
from app.notifications.models import NotificationLog, PushSubscription
from tests.conftest import login


class FakeResponse:
    def __init__(self, status_code, text="error"):
        self.status_code = status_code
        self.text = text


def _subscribe(user, endpoint="https://push.example.org/abc", p256dh="p256dh-key", auth="auth-key"):
    return service.subscribe(user, endpoint=endpoint, p256dh=p256dh, auth=auth, user_agent="pytest-agent")


# --- subscribe/unsubscribe -----------------------------------------------------------


def test_subscribe_creates_new_subscription(app, admin_user):
    subscription = _subscribe(admin_user)
    assert subscription.id is not None
    assert subscription.user_id == admin_user.id
    assert subscription.is_active is True
    assert PushSubscription.query.count() == 1


def test_subscribe_upserts_by_endpoint_instead_of_duplicating(app, admin_user):
    _subscribe(admin_user, p256dh="key-1")
    second = _subscribe(admin_user, p256dh="key-2")

    assert PushSubscription.query.count() == 1
    assert second.p256dh == "key-2"


def test_subscribe_on_existing_endpoint_reassigns_to_new_user(app, admin_user, regular_user):
    _subscribe(admin_user)
    reassigned = _subscribe(regular_user)  # gleicher Default-Endpoint -- simuliert RC-Bedienerwechsel

    assert PushSubscription.query.count() == 1
    assert reassigned.user_id == regular_user.id


def test_unsubscribe_removes_own_subscription(app, admin_user):
    subscription = _subscribe(admin_user)
    removed = service.unsubscribe(admin_user, subscription.endpoint)
    assert removed is True
    assert PushSubscription.query.count() == 0


def test_unsubscribe_does_not_remove_other_users_subscription(app, admin_user, regular_user):
    subscription = _subscribe(admin_user)
    removed = service.unsubscribe(regular_user, subscription.endpoint)
    assert removed is False
    assert PushSubscription.query.count() == 1


def test_unsubscribe_unknown_endpoint_returns_false(app, admin_user):
    assert service.unsubscribe(admin_user, "https://push.example.org/does-not-exist") is False


# --- send_to_user / send_to_role -----------------------------------------------------


def test_send_to_user_without_subscription_returns_empty_list(app, admin_user):
    assert service.send_to_user(admin_user, title="Hallo", body="Welt") == []
    assert NotificationLog.query.count() == 0


def test_send_to_user_delivers_and_logs_success(app, admin_user, monkeypatch):
    _subscribe(admin_user)
    monkeypatch.setattr(service, "webpush", lambda **kwargs: None)

    logs = service.send_to_user(admin_user, title="Hallo", body="Welt")

    assert len(logs) == 1
    assert logs[0].status == "sent"
    assert NotificationLog.query.count() == 1
    assert PushSubscription.query.first().is_active is True


@pytest.mark.parametrize("status_code", [404, 410])
def test_send_to_user_deactivates_subscription_on_gone_response(app, admin_user, monkeypatch, status_code):
    subscription = _subscribe(admin_user)

    def _raise(**kwargs):
        raise WebPushException("gone", response=FakeResponse(status_code))

    monkeypatch.setattr(service, "webpush", _raise)

    logs = service.send_to_user(admin_user, title="Hallo", body="Welt")

    assert logs[0].status == "expired"
    db.session.refresh(subscription)
    assert subscription.is_active is False


def test_send_to_user_keeps_subscription_active_on_other_errors(app, admin_user, monkeypatch):
    subscription = _subscribe(admin_user)

    def _raise(**kwargs):
        raise WebPushException("server error", response=FakeResponse(500))

    monkeypatch.setattr(service, "webpush", _raise)

    logs = service.send_to_user(admin_user, title="Hallo", body="Welt")

    assert logs[0].status == "failed"
    db.session.refresh(subscription)
    assert subscription.is_active is True


def test_send_to_user_keeps_subscription_active_on_network_error(app, admin_user, monkeypatch):
    subscription = _subscribe(admin_user)

    def _raise(**kwargs):
        raise requests.exceptions.ConnectionError("endpoint unreachable")

    monkeypatch.setattr(service, "webpush", _raise)

    logs = service.send_to_user(admin_user, title="Hallo", body="Welt")

    assert logs[0].status == "failed"
    db.session.refresh(subscription)
    assert subscription.is_active is True


def test_send_to_user_skips_inactive_subscriptions(app, admin_user, monkeypatch):
    subscription = _subscribe(admin_user)
    subscription.is_active = False
    db.session.commit()
    calls = []
    monkeypatch.setattr(service, "webpush", lambda **kwargs: calls.append(kwargs))

    logs = service.send_to_user(admin_user, title="Hallo", body="Welt")

    assert logs == []
    assert calls == []


def test_send_to_role_sends_to_every_subscribed_user(app, admin_user, regular_user, roles, monkeypatch):
    _subscribe(admin_user, endpoint="https://push.example.org/admin")
    _subscribe(regular_user, endpoint="https://push.example.org/pilot")
    monkeypatch.setattr(service, "webpush", lambda **kwargs: None)

    admin_user.roles = [roles["administrator"]]
    regular_user.roles = [roles["administrator"]]
    db.session.commit()

    logs = service.send_to_role(roles["administrator"], title="Alarm", body="Test")

    assert len(logs) == 2
    assert {log.user_id for log in logs} == {admin_user.id, regular_user.id}


def test_send_to_user_without_vapid_keys_raises(app, admin_user, monkeypatch):
    from app.core.exceptions import ValidationError

    _subscribe(admin_user)
    app.config["VAPID_PRIVATE_KEY"] = ""

    with pytest.raises(ValidationError):
        service.send_to_user(admin_user, title="Hallo", body="Welt")


# --- Routen --------------------------------------------------------------------------


def test_settings_page_requires_login(client):
    response = client.get("/notifications/settings")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_subscribe_route_creates_subscription(client, admin_user):
    login(client)
    response = client.post(
        "/notifications/subscribe",
        json={"endpoint": "https://push.example.org/route", "keys": {"p256dh": "p", "auth": "a"}},
    )
    assert response.status_code == 200
    assert PushSubscription.query.filter_by(endpoint="https://push.example.org/route").count() == 1


def test_subscribe_route_rejects_incomplete_payload(client, admin_user):
    login(client)
    response = client.post("/notifications/subscribe", json={"endpoint": "https://push.example.org/route"})
    assert response.status_code == 400


def test_unsubscribe_route_removes_subscription(client, admin_user):
    login(client)
    client.post(
        "/notifications/subscribe",
        json={"endpoint": "https://push.example.org/route2", "keys": {"p256dh": "p", "auth": "a"}},
    )
    response = client.post("/notifications/unsubscribe", json={"endpoint": "https://push.example.org/route2"})
    assert response.status_code == 200
    assert response.get_json()["status"] == "unsubscribed"


def test_test_send_route_flashes_error_without_subscription(client, admin_user):
    login(client)
    # Accept: text/html explizit setzen -- entspricht einem normalen Browser-Formular-Submit
    # (app/templates/notifications/settings.html). Der RC-Kiosk-Zugang nutzt stattdessen JSON,
    # s. test_test_send_route_returns_json_when_requested.
    response = client.post(
        "/notifications/test-send", follow_redirects=True, headers={"Accept": "text/html"}
    )
    assert response.status_code == 200
    assert "Kein aktives Gerät" in response.get_data(as_text=True)


def test_test_send_route_returns_json_when_requested(client, admin_user):
    login(client)
    response = client.post("/notifications/test-send", headers={"Accept": "application/json"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "error"
    assert "Kein aktives Gerät" in payload["message"]
