from app.extensions import db
from app.rc.models import RcDevice
from app.rc.services import create_device, deactivate_device, regenerate_device_key, resolve_device_by_key
from tests.conftest import login


def _create_device(organization, label="RC-Testgerät", required_qualification=None):
    return create_device(organization.id, label=label, required_qualification=required_qualification)


# --- Services --------------------------------------------------------------------------


def test_resolve_device_by_key_finds_matching_device(app, organization):
    device, device_key = _create_device(organization)
    resolved = resolve_device_by_key(device_key)
    assert resolved is not None
    assert resolved.id == device.id


def test_resolve_device_by_key_returns_none_for_wrong_key(app, organization):
    _create_device(organization)
    assert resolve_device_by_key("not-the-right-key") is None


def test_resolve_device_by_key_returns_none_for_empty_key(app, organization):
    _create_device(organization)
    assert resolve_device_by_key("") is None


def test_deactivated_device_is_not_resolvable(app, organization):
    device, device_key = _create_device(organization)
    deactivate_device(device)
    assert resolve_device_by_key(device_key) is None


def test_regenerate_device_key_invalidates_old_key(app, organization):
    device, old_key = _create_device(organization)
    new_key = regenerate_device_key(device)
    assert resolve_device_by_key(old_key) is None
    assert resolve_device_by_key(new_key).id == device.id


# --- Routen: Geräte-Pairing --------------------------------------------------------------


def test_home_without_paired_device_redirects_to_pair(client):
    response = client.get("/rc/home")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/rc/pair")


def test_pair_with_wrong_key_shows_error_and_sets_no_cookie(client, app, organization):
    _create_device(organization)
    response = client.post("/rc/pair", data={"device_key": "wrong"})
    assert response.status_code == 200
    assert "Ungültiger" in response.get_data(as_text=True) or "Unbekannter" in response.get_data(as_text=True)
    assert "rc_device_token" not in response.headers.get("Set-Cookie", "")


def test_pair_with_correct_key_redirects_to_login_and_persists_across_requests(client, app, organization):
    device, device_key = _create_device(organization)
    response = client.post("/rc/pair", data={"device_key": device_key})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/rc/login")

    # Cookie wird vom Testclient automatisch mitgeschickt -- Folgeanfrage muss NICHT erneut pairen.
    follow = client.get("/rc/login")
    assert follow.status_code == 200
    assert device.label in follow.get_data(as_text=True)

    db.session.refresh(device)
    assert device.paired_at is not None


def test_login_page_unreachable_without_paired_device(client):
    response = client.get("/rc/login")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/rc/pair")


# --- Routen: Operator-Login/-Logout -------------------------------------------------------


def _pair(client, organization, **kwargs):
    device, device_key = _create_device(organization, **kwargs)
    client.post("/rc/pair", data={"device_key": device_key})
    return device


def test_operator_login_succeeds_and_reaches_home(client, app, organization, admin_user):
    _pair(client, organization)
    response = client.post("/rc/login", data={"identifier": "admin", "pin": "4726"})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/rc/home")

    with client.session_transaction() as sess:
        assert "rc_device_id" in sess

    follow = client.get("/rc/home")
    assert follow.status_code == 200
    assert admin_user.display_name in follow.get_data(as_text=True)


def test_unauthenticated_home_redirects_to_rc_login_not_desktop_login(client, app, organization):
    _pair(client, organization)
    response = client.get("/rc/home")
    assert response.status_code == 302
    assert "/rc/login" in response.headers["Location"]
    assert "/auth/login" not in response.headers["Location"]


def test_wrong_pin_shows_error_on_rc_login(client, app, organization, admin_user):
    _pair(client, organization)
    response = client.post("/rc/login", data={"identifier": "admin", "pin": "0000"})
    assert response.status_code == 200
    assert "falsch" in response.get_data(as_text=True)


def test_logout_keeps_device_paired_but_requires_new_login(client, app, organization, admin_user):
    _pair(client, organization)
    client.post("/rc/login", data={"identifier": "admin", "pin": "4726"})

    response = client.post("/rc/logout")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/rc/login")

    # Kein erneutes Pairing nötig -- direkt wieder die Login-Seite, nicht /rc/pair.
    login_page = client.get("/rc/login")
    assert login_page.status_code == 200

    # Erneuter Login ohne erneutes Pairing funktioniert (Geräte-Session blieb bestehen).
    relogin = client.post("/rc/login", data={"identifier": "admin", "pin": "4726"})
    assert relogin.status_code == 302
    assert relogin.headers["Location"].endswith("/rc/home")


def test_deactivating_device_forces_new_pairing(client, app, organization, admin_user):
    device = _pair(client, organization)
    client.post("/rc/login", data={"identifier": "admin", "pin": "4726"})
    deactivate_device(device)

    response = client.get("/rc/home")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/rc/pair")


# --- Admin-UI ----------------------------------------------------------------------------


def test_admin_can_create_device_and_see_key_once(client, admin_user, roles):
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")

    response = client.post(
        "/administration/rc-devices/new", data={"label": "RC Plus – Fahrzeug 1", "required_qualification": "pilot"}
    )
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Geräteschlüssel" in body

    device = RcDevice.query.filter_by(label="RC Plus – Fahrzeug 1").first()
    assert device is not None
    assert device.required_qualification == "pilot"


def test_non_admin_without_permission_gets_403_on_rc_devices(client, app, organization, roles):
    from app.auth.services import create_user

    user = create_user(
        organization_id=organization.id, username="norights_rc", email="norights_rc@example.org",
        pin="4726", display_name="Ohne Rechte",
    )
    user.roles = [roles["documentation"]]  # hat nur dashboard.view
    db.session.commit()

    login(client, username="norights_rc")
    client.post(f"/roles/activate/{roles['documentation'].id}")
    response = client.get("/administration/rc-devices")
    assert response.status_code == 403


def test_admin_can_toggle_device_active(client, admin_user, roles, organization):
    device, _ = _create_device(organization)
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")

    response = client.post(f"/administration/rc-devices/{device.id}/toggle-active")
    assert response.status_code == 302
    db.session.refresh(device)
    assert device.is_active is False


def test_admin_can_set_dji_pilot2_deeplink(client, admin_user, roles):
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")

    response = client.post("/administration/rc-devices", data={"dji_pilot2_deeplink_url": "dji://open"})
    assert response.status_code == 302

    from app.core.models import get_setting

    assert get_setting("rc_dji_pilot2_deeplink_url") == "dji://open"


# --- CLI: seed-test-data -------------------------------------------------------------------


def test_seed_test_data_is_idempotent(app):
    runner = app.test_cli_runner()
    init_result = runner.invoke(args=["init-fireflight"], env={"FIREFLIGHT_ADMIN_PIN": "4726"})
    assert init_result.exit_code == 0, init_result.output

    from app.auth.models import User

    result1 = runner.invoke(args=["seed-test-data"])
    assert result1.exit_code == 0, result1.output
    user_count_after_first = User.query.count()
    device_count_after_first = RcDevice.query.count()
    assert device_count_after_first == 2

    result2 = runner.invoke(args=["seed-test-data"])
    assert result2.exit_code == 0, result2.output
    assert User.query.count() == user_count_after_first
    assert RcDevice.query.count() == device_count_after_first
