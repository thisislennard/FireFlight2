from datetime import datetime, timezone

import pytest

from app.core.exceptions import ValidationError
from app.extensions import db
from app.modules.incidents.models import Flight, Incident
from app.modules.incidents.services import (
    add_flight,
    close_incident,
    create_incident,
    delete_flight,
    list_flights_with_location,
    logbook_summary,
    reopen_incident,
    update_flight,
)
from tests.conftest import login


# --- Services --------------------------------------------------------------------------------


def test_create_incident_rejects_invalid_kind(app, organization):
    with pytest.raises(ValidationError):
        create_incident(organization.id, kind="foo", title="X")


def test_create_incident_rejects_empty_title(app, organization):
    with pytest.raises(ValidationError):
        create_incident(organization.id, kind="einsatz", title="   ")


def test_close_and_reopen_incident(app, organization):
    incident = create_incident(organization.id, kind="uebung", title="Test")
    close_incident(incident)
    assert incident.is_closed is True
    reopen_incident(incident)
    assert incident.is_closed is False


def test_deleting_incident_cascades_to_flights(app, organization):
    incident = create_incident(organization.id, kind="uebung", title="Test")
    flight = add_flight(incident, purpose="Test")
    db.session.delete(incident)
    db.session.commit()
    assert db.session.get(Flight, flight.id) is None


def test_update_and_delete_flight(app, organization):
    incident = create_incident(organization.id, kind="uebung", title="Test")
    flight = add_flight(incident, purpose="Alt")
    update_flight(flight, purpose="Neu")
    db.session.refresh(flight)
    assert flight.purpose == "Neu"
    delete_flight(flight)
    assert db.session.get(Flight, flight.id) is None


def test_list_flights_with_location_filters_correctly(app, organization):
    incident = create_incident(organization.id, kind="uebung", title="Test")
    add_flight(incident, purpose="ohne Standort")
    with_loc = add_flight(incident, purpose="mit Standort", start_lat=50.0, start_lon=8.0)
    results = list_flights_with_location(organization.id)
    assert [f.id for f in results] == [with_loc.id]


def test_logbook_summary_counts_per_person_and_kind(app, organization, roles):
    from app.auth.services import create_user

    pilot = create_user(
        organization_id=organization.id, username="pilot1", email="p1@example.org",
        pin="4726", display_name="Pilot Eins",
    )
    cam = create_user(
        organization_id=organization.id, username="cam1", email="c1@example.org",
        pin="4726", display_name="Kamera Eins",
    )

    uebung = create_incident(organization.id, kind="uebung", title="Ü1")
    add_flight(uebung, pilot_id=pilot.id, camera_operator_id=cam.id,
               started_at=datetime(2026, 6, 1, tzinfo=timezone.utc))
    einsatz = create_incident(organization.id, kind="einsatz", title="E1")
    add_flight(einsatz, pilot_id=pilot.id, started_at=datetime(2026, 6, 2, tzinfo=timezone.utc))

    rows = {r["user"].id: r for r in logbook_summary(organization.id)}
    assert rows[pilot.id]["uebung_count"] == 1
    assert rows[pilot.id]["einsatz_count"] == 1
    assert rows[cam.id]["uebung_count"] == 1
    assert rows[cam.id]["einsatz_count"] == 0


def test_logbook_summary_filters_by_year_and_month(app, organization):
    from app.auth.services import create_user

    pilot = create_user(
        organization_id=organization.id, username="pilotY", email="py@example.org",
        pin="4726", display_name="Pilot Y",
    )
    incident = create_incident(organization.id, kind="uebung", title="Ü")
    add_flight(incident, pilot_id=pilot.id, started_at=datetime(2025, 3, 1, tzinfo=timezone.utc))
    add_flight(incident, pilot_id=pilot.id, started_at=datetime(2026, 6, 1, tzinfo=timezone.utc))

    rows_2026 = {r["user"].id: r for r in logbook_summary(organization.id, year=2026)}
    assert rows_2026[pilot.id]["uebung_count"] == 1

    rows_june = {r["user"].id: r for r in logbook_summary(organization.id, year=2026, month=6)}
    assert rows_june[pilot.id]["uebung_count"] == 1

    assert logbook_summary(organization.id, year=2026, month=5) == []


# --- Routen ------------------------------------------------------------------------------------


def test_non_admin_without_permission_gets_403_on_incidents(client, app, organization, roles):
    from app.auth.services import create_user

    user = create_user(
        organization_id=organization.id, username="norights_inc", email="norights_inc@example.org",
        pin="4726", display_name="Ohne Rechte",
    )
    user.roles = [roles["equipment_officer"]]  # keine incidents.*-Rechte
    db.session.commit()

    login(client, username="norights_inc")
    client.post(f"/roles/activate/{roles['equipment_officer'].id}")
    response = client.get("/incidents/")
    assert response.status_code == 403


def test_documentation_role_can_create_incident_and_flight(client, app, organization, roles):
    from app.auth.services import create_user

    user = create_user(
        organization_id=organization.id, username="doku", email="doku@example.org",
        pin="4726", display_name="Doku",
    )
    user.roles = [roles["documentation"]]
    db.session.commit()

    login(client, username="doku")
    client.post(f"/roles/activate/{roles['documentation'].id}")

    response = client.post("/incidents/new", data={"kind": "uebung", "title": "Testübung"})
    assert response.status_code == 302
    incident = Incident.query.filter_by(title="Testübung").first()
    assert incident is not None

    response2 = client.post(
        f"/incidents/{incident.id}/flights/new",
        data={"purpose": "Testflug", "started_at": "2026-06-15T10:00", "start_lat": "50.1", "start_lon": "8.5"},
    )
    assert response2.status_code == 302
    db.session.refresh(incident)
    assert len(incident.flights) == 1
    assert incident.flights[0].start_lat == 50.1
    assert incident.flights[0].started_at is not None


def test_close_and_reopen_incident_route(client, admin_user, roles, organization):
    incident = create_incident(organization.id, kind="einsatz", title="Test")
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")

    response = client.post(f"/incidents/{incident.id}/close")
    assert response.status_code == 302
    db.session.refresh(incident)
    assert incident.is_closed is True

    response2 = client.post(f"/incidents/{incident.id}/reopen")
    assert response2.status_code == 302
    db.session.refresh(incident)
    assert incident.is_closed is False


def test_flight_delete_route(client, admin_user, roles, organization):
    incident = create_incident(organization.id, kind="einsatz", title="Test")
    flight = add_flight(incident, purpose="X")
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")

    response = client.post(f"/incidents/{incident.id}/flights/{flight.id}/delete")
    assert response.status_code == 302
    assert db.session.get(Flight, flight.id) is None


def test_map_view_embeds_marker_data(client, admin_user, roles, organization):
    incident = create_incident(organization.id, kind="einsatz", title="Test")
    add_flight(incident, purpose="X", start_lat=50.1, start_lon=8.5)
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")

    response = client.get("/incidents/karte")
    assert response.status_code == 200
    assert "50.1" in response.get_data(as_text=True)


def test_logbook_view_renders_person(client, admin_user, roles, organization):
    incident = create_incident(organization.id, kind="einsatz", title="Test")
    add_flight(incident, pilot_id=admin_user.id, started_at=datetime(2026, 6, 1, tzinfo=timezone.utc))
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")

    response = client.get("/incidents/logbuch")
    assert response.status_code == 200
    assert admin_user.display_name in response.get_data(as_text=True)


# --- Navigation (Bugfix-Regression) ------------------------------------------------------------


def test_sidebar_shows_flugbuch_link_for_user_with_permission(client, admin_user, roles):
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")

    response = client.get("/dashboard/")
    body = response.get_data(as_text=True)
    assert 'href="/incidents/"' in body
    assert "Flugbuch" in body


def test_sidebar_hides_flugbuch_link_for_user_without_permission(client, app, organization, roles):
    from app.auth.services import create_user

    user = create_user(
        organization_id=organization.id, username="noincidents", email="noincidents@example.org",
        pin="4726", display_name="Kein Flugbuch",
    )
    user.roles = [roles["equipment_officer"]]
    db.session.commit()

    login(client, username="noincidents")
    client.post(f"/roles/activate/{roles['equipment_officer'].id}")

    response = client.get("/dashboard/")
    assert "Flugbuch" not in response.get_data(as_text=True)


# --- CLI: seed-test-data -------------------------------------------------------------------------


def test_seed_test_data_creates_example_incidents_and_flights(app):
    runner = app.test_cli_runner()
    runner.invoke(args=["init-fireflight"], env={"FIREFLIGHT_ADMIN_PIN": "4726"})

    result1 = runner.invoke(args=["seed-test-data"])
    assert result1.exit_code == 0, result1.output
    assert Incident.query.count() == 2
    total_flights = sum(len(i.flights) for i in Incident.query.all())
    assert total_flights == 2

    result2 = runner.invoke(args=["seed-test-data"])
    assert result2.exit_code == 0, result2.output
    assert Incident.query.count() == 2
