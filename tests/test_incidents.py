from datetime import datetime, timezone

import pytest

from app.core.exceptions import ValidationError
from app.extensions import db
from app.modules.incidents.models import (
    FLIGHT_STATUS_APPROVED,
    FLIGHT_STATUS_DRAFT,
    FLIGHT_STATUS_PENDING_APPROVAL,
    KIND_EINSATZ,
    KIND_UEBUNG,
    Flight,
    Incident,
)
from app.modules.incidents.services import (
    add_flight,
    approve_flight_start,
    close_incident,
    complete_flight,
    create_draft_flight,
    create_incident,
    delete_flight,
    list_flights_with_location,
    list_pending_approval_flights,
    logbook_summary,
    normalize_incident_kind,
    reopen_incident,
    request_flight_start,
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


def test_list_flights_with_location_limit_returns_most_recent(app, organization):
    incident = create_incident(organization.id, kind="uebung", title="Test")
    older = add_flight(
        incident, purpose="alt", start_lat=50.0, start_lon=8.0,
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    newer = add_flight(
        incident, purpose="neu", start_lat=50.1, start_lon=8.1,
        started_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    results = list_flights_with_location(organization.id, limit=1)
    assert [f.id for f in results] == [newer.id]
    assert older.id not in [f.id for f in results]


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


# --- Startanfrage-Workflow (Phase 12) -----------------------------------------------------------


def test_normalize_incident_kind():
    assert normalize_incident_kind("Einsatz") == KIND_EINSATZ
    assert normalize_incident_kind("einsatz") == KIND_EINSATZ
    assert normalize_incident_kind("Übung") == KIND_UEBUNG
    assert normalize_incident_kind("Sonstiges") == KIND_UEBUNG
    assert normalize_incident_kind(None) == KIND_UEBUNG


def test_create_draft_flight_sets_status_and_start_fields(app, organization, roles):
    from app.auth.services import create_user

    pilot = create_user(
        organization_id=organization.id, username="draftpilot", email="draftpilot@example.org",
        pin="4726", display_name="Draft Pilot",
    )
    incident = create_incident(organization.id, kind="uebung", title="T")
    flight = create_draft_flight(incident, pilot=pilot, purpose="Testflug", start_lat=50.1, start_lon=8.5)

    assert flight.flight_status == FLIGHT_STATUS_DRAFT
    assert flight.pilot_id == pilot.id
    assert flight.camera_operator_id is None
    assert flight.started_at is not None
    assert flight.start_lat == 50.1
    assert flight.start_lon == 8.5


def test_request_and_approve_flight_start(app, organization, admin_user):
    incident = create_incident(organization.id, kind="uebung", title="T")
    flight = create_draft_flight(incident, pilot=admin_user)

    request_flight_start(flight)
    assert flight.flight_status == FLIGHT_STATUS_PENDING_APPROVAL
    assert flight.start_requested_at is not None

    approve_flight_start(flight, approved_by=admin_user)
    assert flight.flight_status == FLIGHT_STATUS_APPROVED
    assert flight.start_approved_at is not None
    assert flight.start_approved_by_id == admin_user.id


def test_list_pending_approval_flights_filters_correctly(app, organization):
    incident = create_incident(organization.id, kind="uebung", title="T")
    draft = create_draft_flight(incident)
    pending = create_draft_flight(incident)
    request_flight_start(pending)
    approved = create_draft_flight(incident)
    request_flight_start(approved)
    approve_flight_start(approved, approved_by=None)

    result_ids = {f.id for f in list_pending_approval_flights(organization.id)}
    assert result_ids == {pending.id}
    assert draft.id not in result_ids
    assert approved.id not in result_ids


def test_complete_flight_sets_end_fields_and_status(app, organization):
    incident = create_incident(organization.id, kind="uebung", title="T")
    flight = create_draft_flight(incident)
    request_flight_start(flight)
    approve_flight_start(flight, approved_by=None)

    complete_flight(flight, end_lat=50.2, end_lon=8.6, synced=True, had_issues=False, notes="Alles gut")

    assert flight.flight_status == "completed"
    assert flight.ended_at is not None
    assert flight.end_lat == 50.2
    assert flight.end_lon == 8.6
    assert flight.synced is True
    assert flight.had_issues is False
    assert flight.notes == "Alles gut"


# --- Routen: Startanfragen -----------------------------------------------------------------------


def test_pending_approvals_requires_permission(client, app, organization, roles):
    from app.auth.services import create_user

    user = create_user(
        organization_id=organization.id, username="norights_approve", email="norights_approve@example.org",
        pin="4726", display_name="Ohne Rechte",
    )
    user.roles = [roles["pilot_camera"]]  # hat incidents.edit, aber nicht incidents.approve_flights
    db.session.commit()

    login(client, username="norights_approve")
    client.post(f"/roles/activate/{roles['pilot_camera'].id}")
    response = client.get("/incidents/freigaben")
    assert response.status_code == 403


def test_flight_leader_can_approve_flight(client, app, organization, roles):
    from app.auth.services import create_user

    leader = create_user(
        organization_id=organization.id, username="leader1", email="leader1@example.org",
        pin="4726", display_name="Leader Eins",
    )
    leader.roles = [roles["flight_leader"]]
    pilot = create_user(
        organization_id=organization.id, username="approvee", email="approvee@example.org",
        pin="4726", display_name="Approvee",
    )
    db.session.commit()

    incident = create_incident(organization.id, kind="uebung", title="T")
    flight = create_draft_flight(incident, pilot=pilot)
    request_flight_start(flight)

    login(client, username="leader1")
    client.post(f"/roles/activate/{roles['flight_leader'].id}")

    response = client.get("/incidents/freigaben")
    assert response.status_code == 200
    assert pilot.display_name in response.get_data(as_text=True)

    approve_response = client.post(f"/incidents/{incident.id}/flights/{flight.id}/approve")
    assert approve_response.status_code == 302
    db.session.refresh(flight)
    assert flight.flight_status == FLIGHT_STATUS_APPROVED
    assert flight.start_approved_by_id == leader.id


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
