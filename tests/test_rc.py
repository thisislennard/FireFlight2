import pytest

from app.core.exceptions import ValidationError
from app.extensions import db
from app.rc.models import RcDevice
from app.rc.services import create_device, deactivate_device, regenerate_device_key, resolve_device_by_key
from tests.conftest import login


def _create_device(organization, label="RC-Testgerät", required_qualification=None):
    return create_device(organization.id, label=label, required_qualification=required_qualification)


def test_create_device_rejects_unknown_qualification(app, organization):
    with pytest.raises(ValidationError):
        create_device(organization.id, label="X", required_qualification="ninja")


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


def _select_candidate(client, user):
    """Schritt 1 des Zwei-Schritt-Logins: Nutzer aus der Liste antippen."""
    return client.post("/rc/login", data={"user_id": str(user.id)})


def _login_two_step(client, user, pin="4726"):
    """Kompletter Zwei-Schritt-RC-Login (Konzeptdokument Abschnitt 5.1, Phase 11): Schritt 1 Nutzer
    auswählen, Schritt 2 PIN eingeben."""
    _select_candidate(client, user)
    return client.post("/rc/login", data={"pin": pin})


def test_operator_login_succeeds_and_reaches_home(client, app, organization, admin_user):
    admin_user.is_pilot = True
    db.session.commit()
    _pair(client, organization)
    response = _login_two_step(client, admin_user)
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
    admin_user.is_pilot = True
    db.session.commit()
    _pair(client, organization)
    response = _login_two_step(client, admin_user, pin="0000")
    assert response.status_code == 200
    assert "falsch" in response.get_data(as_text=True)


def test_logout_keeps_device_paired_but_requires_new_login(client, app, organization, admin_user):
    admin_user.is_pilot = True
    db.session.commit()
    _pair(client, organization)
    _login_two_step(client, admin_user)

    response = client.post("/rc/logout")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/rc/login")

    # Kein erneutes Pairing nötig -- direkt wieder Schritt 1 der Login-Seite, nicht /rc/pair.
    login_page = client.get("/rc/login")
    assert login_page.status_code == 200

    # Erneuter Login ohne erneutes Pairing funktioniert (Geräte-Session blieb bestehen).
    relogin = _login_two_step(client, admin_user)
    assert relogin.status_code == 302
    assert relogin.headers["Location"].endswith("/rc/home")


def test_deactivating_device_forces_new_pairing(client, app, organization, admin_user):
    admin_user.is_pilot = True
    db.session.commit()
    device = _pair(client, organization)
    _login_two_step(client, admin_user)
    deactivate_device(device)

    response = client.get("/rc/home")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/rc/pair")


# --- Zwei-Schritt-Login: Nutzerauswahl (Phase 11) -------------------------------------------


def test_login_step1_lists_only_users_with_a_qualification(client, app, organization, regular_user):
    from app.auth.services import create_user

    regular_user.is_pilot = True
    unqualified = create_user(
        organization_id=organization.id, username="unqualified", email="unqualified@example.org",
        pin="4726", display_name="Ohne Qualifikation",
    )
    db.session.commit()

    _pair(client, organization)  # kein required_qualification
    response = client.get("/rc/login")
    body = response.get_data(as_text=True)
    assert regular_user.display_name in body
    assert unqualified.display_name not in body


def test_login_step1_filters_by_device_required_qualification(client, app, organization, regular_user):
    from app.auth.services import create_user

    regular_user.is_pilot = True
    camera_only = create_user(
        organization_id=organization.id, username="cam_only", email="cam_only@example.org",
        pin="4726", display_name="Nur Kamera",
    )
    camera_only.is_camera_operator = True
    db.session.commit()

    _pair(client, organization, required_qualification="pilot")
    response = client.get("/rc/login")
    body = response.get_data(as_text=True)
    assert regular_user.display_name in body
    assert camera_only.display_name not in body


def test_login_step1_selecting_candidate_advances_to_step2(client, app, organization, regular_user):
    regular_user.is_pilot = True
    db.session.commit()
    _pair(client, organization)

    response = _select_candidate(client, regular_user)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/rc/login")

    step2 = client.get("/rc/login")
    body = step2.get_data(as_text=True)
    assert regular_user.display_name in body
    assert "Anderer Nutzer" in body


def test_login_step2_rejects_tampered_candidate_not_in_list(client, app, organization, regular_user):
    """Nur Nutzer aus der (bereits gefilterten) Kandidatenliste dürfen ausgewählt werden -- eine
    direkt manipulierte user_id, die nicht in der Liste steht, darf nicht zu Schritt 2 führen."""
    from app.auth.services import create_user

    unqualified = create_user(
        organization_id=organization.id, username="tamper", email="tamper@example.org",
        pin="4726", display_name="Tamper",
    )
    db.session.commit()
    _pair(client, organization)

    response = _select_candidate(client, unqualified)
    assert response.status_code == 200  # bleibt auf Schritt 1 (kein Redirect zu sich selbst)
    with client.session_transaction() as sess:
        assert "rc_login_candidate_id" not in sess


def test_login_reselect_returns_to_step1(client, app, organization, regular_user):
    regular_user.is_pilot = True
    db.session.commit()
    _pair(client, organization)
    _select_candidate(client, regular_user)

    step2 = client.get("/rc/login")
    token = step2.get_data(as_text=True).split('name="csrf_token" value="')[1].split('"')[0]
    response = client.post("/rc/login/reselect", data={"csrf_token": token})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/rc/login")

    step1_again = client.get("/rc/login")
    assert regular_user.display_name in step1_again.get_data(as_text=True)
    with client.session_transaction() as sess:
        assert "rc_login_candidate_id" not in sess


# --- Qualifikationsfilter (Phase 7, serverseitige Verteidigung nach Schritt 1) ------------------


def test_operator_login_denied_when_qualification_revoked_between_steps(client, app, organization, regular_user):
    """Schritt 1 filtert bereits auf Qualifikation -- dieser Fall (Ablehnung trotz ausgewähltem
    Kandidaten) kann über die normale Oberfläche kaum noch auftreten, bleibt aber als serverseitige
    Verteidigung bestehen, falls sich die Qualifikation zwischen Schritt 1 und 2 ändert (z. B. ein
    Admin entzieht sie währenddessen)."""
    regular_user.is_pilot = True
    db.session.commit()
    _pair(client, organization, required_qualification="pilot")
    _select_candidate(client, regular_user)

    regular_user.is_pilot = False
    db.session.commit()

    response = client.post("/rc/login", data={"pin": "4726"})
    assert response.status_code == 200
    assert "andere Qualifikation" in response.get_data(as_text=True)


def test_operator_login_succeeds_when_qualification_matches(client, app, organization, regular_user):
    regular_user.is_pilot = True
    db.session.commit()
    _pair(client, organization, required_qualification="pilot")

    response = _login_two_step(client, regular_user)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/rc/home")


def test_operator_login_unaffected_when_device_has_no_qualification_filter(client, app, organization, regular_user):
    regular_user.is_pilot = True
    db.session.commit()
    _pair(client, organization)  # required_qualification=None

    response = _login_two_step(client, regular_user)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/rc/home")


def test_qualification_denial_does_not_count_as_failed_login_attempt(client, app, organization, regular_user):
    regular_user.is_pilot = True
    db.session.commit()
    _pair(client, organization, required_qualification="pilot")
    _select_candidate(client, regular_user)

    regular_user.is_pilot = False
    db.session.commit()

    client.post("/rc/login", data={"pin": "4726"})
    db.session.refresh(regular_user)
    assert regular_user.failed_login_attempts == 0
    assert regular_user.locked_until is None


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
