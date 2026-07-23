from app.extensions import db
from app.units.models import Unit
from app.units.services import (
    activate_unit,
    assign_home_unit,
    create_unit,
    deactivate_unit,
    list_units,
    set_unit_managers,
    unit_members,
    update_unit,
)
from tests.conftest import login


# --- Services --------------------------------------------------------------------------


def test_create_unit_and_list(app, organization):
    unit = create_unit(organization.id, name="Einheit Nord", description="Nordkreis")
    assert unit.id is not None
    assert unit.is_active is True
    assert list_units(organization.id) == [unit]


def test_update_unit(app, organization):
    unit = create_unit(organization.id, name="Einheit Nord")
    update_unit(unit, name="Einheit Nordost", description="Neu")
    db.session.refresh(unit)
    assert unit.name == "Einheit Nordost"
    assert unit.description == "Neu"


def test_deactivate_and_activate_unit(app, organization):
    unit = create_unit(organization.id, name="Einheit Nord")
    deactivate_unit(unit)
    assert unit.is_active is False
    activate_unit(unit)
    assert unit.is_active is True


def test_set_unit_managers_supports_overlap(app, organization, roles):
    from app.auth.services import create_user

    user_a = create_user(
        organization_id=organization.id, username="mgr_a", email="mgr_a@example.org",
        pin="4726", display_name="Manager A",
    )
    user_b = create_user(
        organization_id=organization.id, username="mgr_b", email="mgr_b@example.org",
        pin="4726", display_name="Manager B",
    )
    unit_a = create_unit(organization.id, name="Einheit A")
    unit_b = create_unit(organization.id, name="Einheit B")

    set_unit_managers(unit_a, [user_a.id, user_b.id])
    set_unit_managers(unit_b, [user_b.id])

    assert {u.id for u in unit_a.managers} == {user_a.id, user_b.id}
    assert {u.id for u in unit_b.managers} == {user_b.id}
    assert set(user_b.managed_units) == {unit_a, unit_b}


def test_assign_home_unit_and_unit_members(app, organization, roles):
    from app.auth.services import create_user

    unit = create_unit(organization.id, name="Einheit Nord")
    member = create_user(
        organization_id=organization.id, username="member1", email="member1@example.org",
        pin="4726", display_name="Mitglied Eins",
    )
    assert unit_members(unit) == []

    assign_home_unit(member, unit.id)
    assert unit_members(unit) == [member]

    assign_home_unit(member, None)
    assert unit_members(unit) == []


# --- Admin-Routen ------------------------------------------------------------------------


def test_admin_can_create_and_edit_unit(client, admin_user, roles, organization):
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")

    response = client.post("/administration/units/new", data={"name": "Einheit Nord", "description": "Nordkreis"})
    assert response.status_code == 302

    unit = Unit.query.filter_by(name="Einheit Nord").first()
    assert unit is not None

    response = client.post(
        f"/administration/units/{unit.id}",
        data={"name": "Einheit Nord", "description": "Aktualisiert", "manager_ids": [str(admin_user.id)]},
    )
    assert response.status_code == 302
    db.session.refresh(unit)
    assert unit.description == "Aktualisiert"
    assert admin_user in unit.managers


def test_non_admin_without_permission_gets_403_on_units(client, app, organization, roles):
    from app.auth.services import create_user

    user = create_user(
        organization_id=organization.id, username="norights_units", email="norights_units@example.org",
        pin="4726", display_name="Ohne Rechte",
    )
    user.roles = [roles["documentation"]]
    db.session.commit()

    login(client, username="norights_units")
    client.post(f"/roles/activate/{roles['documentation'].id}")
    response = client.get("/administration/units")
    assert response.status_code == 403


def test_admin_can_toggle_unit_active(client, admin_user, roles, organization):
    unit = create_unit(organization.id, name="Einheit Nord")
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")

    response = client.post(f"/administration/units/{unit.id}/toggle-active")
    assert response.status_code == 302
    db.session.refresh(unit)
    assert unit.is_active is False


def test_admin_can_set_home_unit_via_user_edit(client, admin_user, roles, organization, regular_user):
    unit = create_unit(organization.id, name="Einheit Nord")
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")

    response = client.post(
        f"/administration/users/{regular_user.id}",
        data={
            "display_name": regular_user.display_name,
            "email": regular_user.email,
            "role_ids": [str(roles["pilot_camera"].id)],
            "home_unit_id": str(unit.id),
        },
    )
    assert response.status_code == 302
    db.session.refresh(regular_user)
    assert regular_user.home_unit_id == unit.id


# --- CLI: seed-test-data (Einheiten) -------------------------------------------------------


def test_seed_test_data_creates_units_with_overlapping_managers(app):
    runner = app.test_cli_runner()
    init_result = runner.invoke(args=["init-fireflight"], env={"FIREFLIGHT_ADMIN_PIN": "4726"})
    assert init_result.exit_code == 0, init_result.output

    result1 = runner.invoke(args=["seed-test-data"])
    assert result1.exit_code == 0, result1.output
    assert Unit.query.count() == 3

    from app.auth.models import User

    user_count_after_first = User.query.count()
    manager_usernames = {m.username for u in Unit.query.all() for m in u.managers}
    assert "test_unit_leader" in manager_usernames
    unit_counts = [len(u.managers) for u in Unit.query.all()]
    assert all(count >= 1 for count in unit_counts)

    # Überlappung: mindestens ein Manager verwaltet mehr als eine Einheit.
    manager_ids = [m.id for u in Unit.query.all() for m in u.managers]
    assert len(manager_ids) != len(set(manager_ids))

    result2 = runner.invoke(args=["seed-test-data"])
    assert result2.exit_code == 0, result2.output
    assert Unit.query.count() == 3
    assert User.query.count() == user_count_after_first  # keine Duplikate durch erneuten Lauf
