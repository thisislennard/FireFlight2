from app.core.models import set_setting
from app.extensions import db
from app.modules.incidents.models import (
    FLIGHT_STATUS_APPROVED,
    FLIGHT_STATUS_DRAFT,
    FLIGHT_STATUS_PENDING_APPROVAL,
    Flight,
    Incident,
)
from app.modules.incidents.services import approve_flight_start
from app.modules.incidents.wizard_fields import (
    FIELD_KEY_END_LOCATION,
    FIELD_KEY_HAD_ISSUES,
    FIELD_KEY_INCIDENT_KIND,
    FIELD_KEY_NOTES,
    FIELD_KEY_PURPOSE,
    FIELD_KEY_START_LOCATION,
    FIELD_KEY_SYNCED,
)
from app.rc.services import create_device
from app.wizards.services import add_step, create_wizard
from tests.conftest import login


def _pair(client, organization, **kwargs):
    device, device_key = create_device(organization.id, label="RC-Testgerät", **kwargs)
    client.post("/rc/pair", data={"device_key": device_key})
    return device


def _login_two_step(client, user, pin="4726"):
    client.post("/rc/login", data={"user_id": str(user.id)})
    return client.post("/rc/login", data={"pin": pin})


def _setup_wizards(organization):
    """Kleine Preflight-/Flugende-Wizards mit denselben field_key-Zuordnungen wie in
    `flask seed-test-data`, nur mit einem einzigen Checklisten-Punkt für kürzere Testläufe."""
    preflight = create_wizard(organization.id, key="test_preflight", name="Test-Preflight")
    add_step(preflight, step_type="checklist", title="Checkliste", config={"items": ["Punkt 1"]})
    add_step(preflight, step_type="choice", title="Art", config={"label": "Art", "options": ["Einsatz", "Übung"]},
             field_key=FIELD_KEY_INCIDENT_KIND)
    add_step(preflight, step_type="text_input", title="Zweck", config={"label": "Zweck", "required": True},
             field_key=FIELD_KEY_PURPOSE)
    add_step(preflight, step_type="location", title="Standort", config={"label": "Standort"},
             field_key=FIELD_KEY_START_LOCATION)

    flight_end = create_wizard(organization.id, key="test_flight_end", name="Test-Flugende")
    add_step(flight_end, step_type="location", title="Standort", config={"label": "Standort"},
             field_key=FIELD_KEY_END_LOCATION)
    add_step(flight_end, step_type="choice", title="Sync", config={"label": "Synchronisiert?", "options": ["Ja", "Nein"]},
             field_key=FIELD_KEY_SYNCED)
    add_step(flight_end, step_type="choice", title="Mängel", config={"label": "Mängel?", "options": ["Ja", "Nein"]},
             field_key=FIELD_KEY_HAD_ISSUES)
    add_step(flight_end, step_type="text_input", title="Notizen", config={"label": "Notizen", "required": False},
             field_key=FIELD_KEY_NOTES)

    set_setting("rc_preflight_wizard_id", str(preflight.id))
    set_setting("rc_flight_end_wizard_id", str(flight_end.id))
    return preflight, flight_end


def _run_preflight(client, *, incident_kind="Übung", purpose="Testflug", lat="50.1", lon="8.5"):
    client.post("/rc/preflight", data={"action": "next", "answer_items": "0"})
    client.post("/rc/preflight", data={"action": "next", "answer": incident_kind})
    client.post("/rc/preflight", data={"action": "next", "answer": purpose})
    return client.post("/rc/preflight", data={"action": "next", "lat": lat, "lon": lon})


def _run_flight_end(client, *, synced="Ja", had_issues="Nein", lat="50.2", lon="8.6", notes=""):
    client.post("/rc/flight-end", data={"action": "next", "lat": lat, "lon": lon})
    client.post("/rc/flight-end", data={"action": "next", "answer": synced})
    client.post("/rc/flight-end", data={"action": "next", "answer": had_issues})
    return client.post("/rc/flight-end", data={"action": "next", "answer": notes})


# --- Preflight ohne konfigurierten Wizard --------------------------------------------------------


def test_preflight_shows_missing_page_without_configured_wizard(client, app, organization, regular_user):
    regular_user.is_pilot = True
    db.session.commit()
    _pair(client, organization)
    _login_two_step(client, regular_user)

    response = client.get("/rc/preflight")
    assert response.status_code == 200
    assert "nicht konfiguriert" in response.get_data(as_text=True)


# --- Preflight: kompletter Durchlauf inkl. Einsatz-Neuanlage --------------------------------------


def test_full_preflight_creates_draft_flight(client, app, organization, regular_user):
    regular_user.is_pilot = True
    db.session.commit()
    _setup_wizards(organization)
    _pair(client, organization)
    _login_two_step(client, regular_user)

    response = _run_preflight(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/rc/preflight/incident")

    picker = client.get("/rc/preflight/incident")
    assert picker.status_code == 200
    assert "Übung" in picker.get_data(as_text=True)

    create_response = client.post("/rc/preflight/incident", data={"new_title": "Testübung RC"})
    assert create_response.status_code == 302
    assert create_response.headers["Location"].endswith("/rc/home")

    incident = Incident.query.filter_by(title="Testübung RC").first()
    assert incident is not None
    assert len(incident.flights) == 1
    flight = incident.flights[0]
    assert flight.flight_status == FLIGHT_STATUS_DRAFT
    assert flight.pilot_id == regular_user.id
    assert flight.purpose == "Testflug"
    assert flight.start_lat == 50.1
    assert flight.start_lon == 8.5

    with client.session_transaction() as sess:
        assert sess.get("rc_active_flight_id") == str(flight.id)

    home = client.get("/rc/home")
    assert "Flug starten" in home.get_data(as_text=True)


def test_preflight_checklist_gate_blocks_incomplete_answer(client, app, organization, regular_user):
    regular_user.is_pilot = True
    db.session.commit()
    _setup_wizards(organization)
    _pair(client, organization)
    _login_two_step(client, regular_user)

    response = client.post("/rc/preflight", data={"action": "next"})  # kein answer_items
    assert response.status_code == 200
    assert "erforderlich" in response.get_data(as_text=True)


def test_preflight_incident_picker_can_join_existing_open_incident(client, app, organization, regular_user):
    regular_user.is_pilot = True
    db.session.commit()
    _setup_wizards(organization)
    from app.modules.incidents.services import create_incident

    existing = create_incident(organization.id, kind="uebung", title="Bestehende Übung")

    _pair(client, organization)
    _login_two_step(client, regular_user)
    _run_preflight(client)

    response = client.post("/rc/preflight/incident", data={"incident_id": str(existing.id)})
    assert response.status_code == 302
    db.session.refresh(existing)
    assert len(existing.flights) == 1


# --- Flugstart / Genehmigung / Flugende / Ende-Bildschirm -----------------------------------------


def test_full_flight_lifecycle(client, app, organization, regular_user, roles, monkeypatch):
    from app.notifications import service as notifications_service

    monkeypatch.setattr(notifications_service, "webpush", lambda **kwargs: None)

    regular_user.is_pilot = True
    db.session.commit()
    _setup_wizards(organization)
    _pair(client, organization)
    _login_two_step(client, regular_user)
    _run_preflight(client)
    client.post("/rc/preflight/incident", data={"new_title": "Lifecycle-Test"})

    flight = Flight.query.join(Incident).filter(Incident.title == "Lifecycle-Test").first()
    assert flight.flight_status == FLIGHT_STATUS_DRAFT

    # Flug starten -> Startanfrage
    start_response = client.post("/rc/flight/start")
    assert start_response.status_code == 302
    db.session.refresh(flight)
    assert flight.flight_status == FLIGHT_STATUS_PENDING_APPROVAL
    assert flight.start_requested_at is not None

    home_pending = client.get("/rc/home")
    assert "wartet auf Freigabe" in home_pending.get_data(as_text=True) or "Freigabe" in home_pending.get_data(as_text=True)

    # Freigabe (simuliert Desktop-Genehmigung, ohne HTTP-Client-Wechsel)
    approve_flight_start(flight, approved_by=None)
    db.session.refresh(flight)
    assert flight.flight_status == FLIGHT_STATUS_APPROVED

    home_approved = client.get("/rc/home")
    assert "Flug beenden" in home_approved.get_data(as_text=True)

    # Flugende-Wizard
    end_response = _run_flight_end(client)
    assert end_response.status_code == 302
    assert end_response.headers["Location"].endswith("/rc/flight-end/summary")

    db.session.refresh(flight)
    assert flight.flight_status == "completed"
    assert flight.synced is True
    assert flight.had_issues is False
    assert flight.end_lat == 50.2

    with client.session_transaction() as sess:
        assert "rc_active_flight_id" not in sess

    summary = client.get("/rc/flight-end/summary")
    assert "Selbe Person" in summary.get_data(as_text=True)
    assert "Komplett neu" in summary.get_data(as_text=True)

    # "Selbe Person, neuer Flug"
    restart_response = client.post("/rc/flight-end/restart")
    assert restart_response.status_code == 302
    assert restart_response.headers["Location"].endswith("/rc/preflight")


def test_flight_start_requires_draft_status(client, app, organization, regular_user):
    regular_user.is_pilot = True
    db.session.commit()
    _pair(client, organization)
    _login_two_step(client, regular_user)

    # Kein aktiver Flug -> keine Wirkung, kein Fehler
    response = client.post("/rc/flight/start")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/rc/home")


def test_flight_end_requires_approved_status(client, app, organization, regular_user):
    regular_user.is_pilot = True
    db.session.commit()
    _setup_wizards(organization)
    _pair(client, organization)
    _login_two_step(client, regular_user)
    _run_preflight(client)
    client.post("/rc/preflight/incident", data={"new_title": "Not-Yet-Approved"})

    # Flug ist erst "draft", noch nicht "approved" -- Flugende darf nicht möglich sein.
    response = client.get("/rc/flight-end")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/rc/home")


# --- Bedienerwechsel: aktiver Flug darf nicht an den nächsten Bediener durchsickern ----------------


def test_logout_clears_active_flight_from_session(client, app, organization, regular_user):
    """Regressionstest für den in Phase 12 gefundenen Bug: ohne das Aufräumen in rc.logout hätte der
    nächste Bediener desselben Geräts den noch offenen Flug der vorigen Person gesehen."""
    regular_user.is_pilot = True
    db.session.commit()
    _setup_wizards(organization)
    _pair(client, organization)
    _login_two_step(client, regular_user)
    _run_preflight(client)
    client.post("/rc/preflight/incident", data={"new_title": "Leak-Test"})

    with client.session_transaction() as sess:
        assert "rc_active_flight_id" in sess

    client.post("/rc/logout")

    with client.session_transaction() as sess:
        assert "rc_active_flight_id" not in sess
        assert "rc_preflight_state" not in sess
