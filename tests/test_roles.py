from app.extensions import db
from tests.conftest import login


def _create_multi_role_user(organization, roles, username="multi"):
    from app.auth.services import create_user

    user = create_user(
        organization_id=organization.id,
        username=username,
        email=f"{username}@example.org",
        pin="4726",
        display_name="Multi Rolle",
    )
    user.roles = [roles["pilot_camera"], roles["flight_leader"]]
    db.session.commit()
    return user


def test_single_role_user_is_redirected_straight_to_dashboard(client, admin_user):
    login(client)
    response = client.get("/roles/select")
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


def test_multi_role_user_sees_selection_page(client, app, organization, roles):
    _create_multi_role_user(organization, roles)
    login(client, username="multi")
    response = client.get("/roles/select")
    assert response.status_code == 200
    assert "In welcher Funktion" in response.get_data(as_text=True)


def test_role_switch_updates_session(client, app, organization, roles):
    user = _create_multi_role_user(organization, roles, username="multi2")
    login(client, username="multi2")

    r1 = client.post(f"/roles/activate/{roles['pilot_camera'].id}")
    assert r1.status_code == 302
    with client.session_transaction() as sess:
        assert sess["active_role_id"] == str(roles["pilot_camera"].id)

    r2 = client.post(f"/roles/activate/{roles['flight_leader'].id}")
    assert r2.status_code == 302
    with client.session_transaction() as sess:
        assert sess["active_role_id"] == str(roles["flight_leader"].id)


def test_user_cannot_activate_unassigned_role(client, app, organization, roles):
    _create_multi_role_user(organization, roles, username="multi3")
    login(client, username="multi3")
    response = client.post(f"/roles/activate/{roles['administrator'].id}")
    assert response.status_code == 403


def test_permission_check_denies_unauthorized_access(client, app, organization, roles):
    from app.auth.services import create_user

    user = create_user(
        organization_id=organization.id, username="norights", email="norights@example.org",
        pin="4726", display_name="Ohne Rechte",
    )
    user.roles = [roles["documentation"]]  # hat nur dashboard.view
    db.session.commit()

    login(client, username="norights")
    client.post(f"/roles/activate/{roles['documentation'].id}")
    response = client.get("/administration/users")
    assert response.status_code == 403


def test_admin_can_create_role_and_assign_permissions(client, admin_user, roles):
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")
    response = client.post("/administration/roles/new", data={"key": "custom_role", "name": "Testrolle"})
    assert response.status_code == 302

    from app.roles.models import Role

    created = Role.query.filter_by(key="custom_role").first()
    assert created is not None

    response = client.post(
        f"/administration/roles/{created.id}",
        data={"name": "Testrolle", "permission_keys": ["dashboard.view", "audit.view"]},
    )
    assert response.status_code == 302
    db.session.refresh(created)
    assert {p.key for p in created.permissions} == {"dashboard.view", "audit.view"}


def test_last_administrator_cannot_be_disabled(client, admin_user, roles):
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")
    response = client.post(f"/administration/users/{admin_user.id}/toggle-active")
    assert response.status_code == 302
    db.session.refresh(admin_user)
    assert admin_user.is_active_account is True


def test_role_without_dashboard_permission_lands_on_no_landing_page(client, app, organization, roles):
    """Rolle ohne dashboard.view (z. B. künftig Gerätewart) darf nach Aktivierung nicht in einen
    rohen 403 laufen, sondern muss auf der Hinweisseite landen (s. Restrukturierungsplan Abschnitt 2)."""
    from app.auth.services import create_user
    from app.roles.services import set_role_permissions

    set_role_permissions(roles["equipment_officer"], [])
    user = create_user(
        organization_id=organization.id, username="geraetewart_test", email="geraetewart_test@example.org",
        pin="4726", display_name="Gerätewart Test",
    )
    user.roles = [roles["equipment_officer"]]
    db.session.commit()

    login(client, username="geraetewart_test")
    response = client.post(f"/roles/activate/{roles['equipment_officer'].id}")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/roles/no-landing")

    follow = client.get(response.headers["Location"])
    assert follow.status_code == 200
    assert "kein Startbereich konfiguriert" in follow.get_data(as_text=True)


def test_role_with_custom_landing_endpoint_redirects_there(client, admin_user, roles):
    from app.roles.services import update_role

    update_role(roles["documentation"], landing_endpoint="administration.audit_log")
    from app.auth.services import create_user

    user = create_user(
        organization_id=roles["documentation"].organization_id, username="doku_test", email="doku_test@example.org",
        pin="4726", display_name="Doku Test",
    )
    user.roles = [roles["documentation"]]
    db.session.commit()

    login(client, username="doku_test")
    response = client.post(f"/roles/activate/{roles['documentation'].id}")
    assert response.status_code == 302
    assert "/administration/audit-log" in response.headers["Location"]


def test_role_editor_offers_dashboard_only_when_permission_present(client, admin_user, roles):
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")

    from app.roles.services import set_role_permissions

    set_role_permissions(roles["equipment_officer"], [])
    response = client.get(f"/administration/roles/{roles['equipment_officer'].id}")
    assert response.status_code == 200
    assert 'value="dashboards.view"' not in response.get_data(as_text=True)
