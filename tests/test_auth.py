from datetime import datetime, timedelta, timezone

from app.auth.services import set_user_active
from app.extensions import db
from tests.conftest import login


def test_login_success_redirects(client, admin_user):
    response = login(client)
    assert response.status_code == 302


def test_login_wrong_pin_fails(client, admin_user):
    response = login(client, pin="0007")
    assert response.status_code == 200
    assert "falsch" in response.get_data(as_text=True)


def test_login_rejects_malformed_pin_format(client, admin_user):
    response = login(client, pin="12")
    assert response.status_code == 200
    assert "genau 4 Ziffern" in response.get_data(as_text=True)


def test_disabled_user_cannot_login(client, regular_user):
    set_user_active(regular_user, False)
    response = login(client, username="pilot")
    assert response.status_code == 200
    assert "falsch" in response.get_data(as_text=True)


def test_account_locks_after_too_many_failed_attempts(client, app, regular_user):
    for _ in range(3):
        login(client, username="pilot", pin="0007")

    response = login(client, username="pilot", pin="4726")
    assert response.status_code == 200
    assert "gesperrt" in response.get_data(as_text=True)
    db.session.refresh(regular_user)
    assert regular_user.lockout_count == 1


def test_second_lockout_within_24h_escalates_to_longer_stage(client, app, regular_user):
    for _ in range(3):
        login(client, username="pilot", pin="0007")
    db.session.refresh(regular_user)
    assert regular_user.lockout_count == 1
    first_locked_until = regular_user.locked_until

    # Erste Sperre künstlich ablaufen lassen, ohne 15 Minuten zu warten -- simuliert einen zweiten
    # Angriffsversuch innerhalb desselben 24h-Eskalationsfensters.
    regular_user.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.session.commit()

    for _ in range(3):
        login(client, username="pilot", pin="0007")

    db.session.refresh(regular_user)
    assert regular_user.lockout_count == 2
    assert regular_user.locked_until > first_locked_until + timedelta(minutes=16)


def test_third_lockout_requires_admin_unlock(client, app, regular_user):
    regular_user.lockout_count = 2
    regular_user.last_lockout_at = datetime.now(timezone.utc)
    db.session.commit()

    for _ in range(3):
        login(client, username="pilot", pin="0007")

    db.session.refresh(regular_user)
    assert regular_user.requires_admin_unlock is True
    assert regular_user.locked_until is None

    response = login(client, username="pilot", pin="4726")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "gesperrt" in body
    assert "Administrator" in body


def test_admin_can_unlock_account(client, admin_user, regular_user, roles):
    regular_user.requires_admin_unlock = True
    regular_user.lockout_count = 3
    db.session.commit()

    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")
    response = client.post(f"/administration/users/{regular_user.id}/unlock")
    assert response.status_code == 302

    db.session.refresh(regular_user)
    assert regular_user.requires_admin_unlock is False
    assert regular_user.lockout_count == 0

    client.post("/auth/logout")
    response = login(client, username="pilot")
    assert response.status_code == 302


def test_pin_change_success(client, admin_user):
    login(client)
    response = client.post(
        "/auth/pin/change",
        data={"current_pin": "4726", "new_pin": "5931", "new_pin_confirm": "5931"},
    )
    assert response.status_code == 200
    assert "erfolgreich" in response.get_data(as_text=True)

    client.post("/auth/logout")
    response = login(client, pin="5931")
    assert response.status_code == 302


def test_pin_change_rejects_wrong_current_pin(client, admin_user):
    login(client)
    response = client.post(
        "/auth/pin/change",
        data={"current_pin": "0007", "new_pin": "5931", "new_pin_confirm": "5931"},
    )
    assert response.status_code == 200
    assert "falsch" in response.get_data(as_text=True)


def test_pin_change_rejects_trivial_new_pin(client, admin_user):
    login(client)
    response = client.post(
        "/auth/pin/change",
        data={"current_pin": "4726", "new_pin": "1111", "new_pin_confirm": "1111"},
    )
    assert response.status_code == 200
    assert "leicht zu erraten" in response.get_data(as_text=True)


def test_root_redirects_unauthenticated_to_login(client):
    response = client.get("/")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_admin_cannot_create_user_with_trivial_pin(client, admin_user, roles):
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")
    response = client.post(
        "/administration/users/new",
        data={"username": "neuling", "email": "neuling@example.org", "pin": "1234", "display_name": "Neuling"},
    )
    assert response.status_code == 200
    assert "leicht zu erraten" in response.get_data(as_text=True)

    from app.auth.models import User

    assert User.query.filter_by(username="neuling").first() is None


def test_admin_can_create_user_with_valid_pin(client, admin_user, roles):
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")
    response = client.post(
        "/administration/users/new",
        data={"username": "neuling2", "email": "neuling2@example.org", "pin": "5931", "display_name": "Neuling"},
    )
    assert response.status_code == 302

    from app.auth.models import User

    assert User.query.filter_by(username="neuling2").first() is not None
