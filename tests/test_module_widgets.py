import io

from werkzeug.datastructures import FileStorage

from app.extensions import db
from app.modules.incidents.services import add_flight, create_incident
from app.modules.tickets.models import Ticket
from tests.conftest import login

_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000a49444154789c6360000002000155273d05000000"
    "0049454e44ae426082"
)


def _png_file(name="a.png"):
    return FileStorage(stream=io.BytesIO(_PNG_BYTES), filename=name)


def _role_with_only_dashboard_view(organization):
    """Testrolle ohne `incidents.view`/`tickets.create` -- keine der Standardrollen (s.
    app/roles/defaults.py) hat `dashboard.view`, aber keine der beiden Fachberechtigungen, daher
    für die "Keine Berechtigung"-Zweige der Widgets hier gezielt konstruiert."""
    from app.roles.services import create_role, set_role_permissions

    role = create_role(organization.id, key="widget_test_role", name="Widget-Testrolle")
    set_role_permissions(role, ["dashboard.view"])
    return role


def _add_user_with_role(organization, role, username="widgetuser"):
    from app.auth.services import create_user

    user = create_user(
        organization_id=organization.id, username=username, email=f"{username}@example.org",
        pin="4726", display_name="Widget User",
    )
    user.roles = [role]
    db.session.commit()
    return user


# --- Registry ---------------------------------------------------------------------------------


def test_incidents_flight_map_widget_registered(app):
    from app.dashboards.widgets import widget_registry

    definition = widget_registry.get("incidents.flight_map")
    assert definition is not None
    assert definition.template == "modules/incidents/_widget_flight_map.html"


def test_tickets_report_form_widget_registered(app):
    from app.dashboards.widgets import widget_registry

    definition = widget_registry.get("tickets.report_form")
    assert definition is not None
    assert definition.template == "modules/tickets/_widget_report_form.html"


# --- Flugbuch-/Karten-Widget --------------------------------------------------------------------


def test_flight_map_widget_shows_markers_for_permitted_role(client, app, organization, roles, regular_user):
    from app.dashboards.services import add_widget, get_or_create_dashboard

    incident = create_incident(organization.id, kind="einsatz", title="Widget-Test-Einsatz")
    add_flight(incident, purpose="X", start_lat=50.11, start_lon=8.55)

    dashboard = get_or_create_dashboard(roles["pilot_camera"])
    add_widget(dashboard, widget_type="incidents.flight_map", title=None, config={"limit": 10})

    login(client, username="pilot")
    client.post(f"/roles/activate/{roles['pilot_camera'].id}")
    response = client.get("/dashboard/")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Widget-Test-Einsatz" in body
    assert "Vollständige Karte" in body


def test_flight_map_widget_shows_empty_state_without_flights(client, app, organization, roles, regular_user):
    from app.dashboards.services import add_widget, get_or_create_dashboard

    dashboard = get_or_create_dashboard(roles["pilot_camera"])
    add_widget(dashboard, widget_type="incidents.flight_map", title=None, config={"limit": 10})

    login(client, username="pilot")
    client.post(f"/roles/activate/{roles['pilot_camera'].id}")
    response = client.get("/dashboard/")
    assert "Noch keine Flüge mit erfasstem Standort" in response.get_data(as_text=True)


def test_flight_map_widget_denies_role_without_incidents_view(client, app, organization, roles):
    from app.dashboards.services import add_widget, get_or_create_dashboard

    role = _role_with_only_dashboard_view(organization)
    _add_user_with_role(organization, role)
    dashboard = get_or_create_dashboard(role)
    add_widget(dashboard, widget_type="incidents.flight_map", title=None, config={})

    login(client, username="widgetuser")
    client.post(f"/roles/activate/{role.id}")
    response = client.get("/dashboard/")
    assert "Keine Berechtigung" in response.get_data(as_text=True)
    assert "Vollständige Karte" not in response.get_data(as_text=True)


def test_flight_map_widget_respects_limit(client, app, organization, roles, regular_user):
    from app.dashboards.services import add_widget, get_or_create_dashboard

    incident = create_incident(organization.id, kind="uebung", title="Limit-Test")
    for i in range(3):
        add_flight(incident, purpose=f"Flug {i}", start_lat=50.0 + i, start_lon=8.0)

    dashboard = get_or_create_dashboard(roles["pilot_camera"])
    add_widget(dashboard, widget_type="incidents.flight_map", title=None, config={"limit": 1})

    login(client, username="pilot")
    client.post(f"/roles/activate/{roles['pilot_camera'].id}")
    response = client.get("/dashboard/")
    body = response.get_data(as_text=True)
    # Bei genau einem Marker liefert das Widget genau ein "detail_url"-Vorkommen im eingebetteten JSON.
    assert body.count("Limit-Test") == 1


# --- "Technisches Problem melden"-Widget --------------------------------------------------------


def test_report_form_widget_renders_for_permitted_role(client, app, organization, roles, regular_user):
    from app.dashboards.services import add_widget, get_or_create_dashboard

    dashboard = get_or_create_dashboard(roles["pilot_camera"])
    add_widget(dashboard, widget_type="tickets.report_form", title=None, config={})

    login(client, username="pilot")
    client.post(f"/roles/activate/{roles['pilot_camera'].id}")
    response = client.get("/dashboard/")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'action="/tickets/melden"' in body
    assert 'name="title"' in body
    assert 'name="photo"' in body


def test_report_form_widget_denies_role_without_tickets_create(client, app, organization, roles):
    from app.dashboards.services import add_widget, get_or_create_dashboard

    role = _role_with_only_dashboard_view(organization)
    _add_user_with_role(organization, role)
    dashboard = get_or_create_dashboard(role)
    add_widget(dashboard, widget_type="tickets.report_form", title=None, config={})

    login(client, username="widgetuser")
    client.post(f"/roles/activate/{role.id}")
    response = client.get("/dashboard/")
    body = response.get_data(as_text=True)
    assert "Keine Berechtigung" in body
    assert 'action="/tickets/melden"' not in body


def test_widget_report_creates_ticket_and_redirects_to_dashboard(client, app, organization, roles, regular_user):
    login(client, username="pilot")
    client.post(f"/roles/activate/{roles['pilot_camera'].id}")

    response = client.post(
        "/tickets/melden",
        data={"title": "Akku defekt", "description": "Testdaten", "drone_label": "M30T"},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard/")

    ticket = Ticket.query.filter_by(organization_id=organization.id, title="Akku defekt").first()
    assert ticket is not None
    assert ticket.created_by_id == regular_user.id
    assert ticket.drone_label == "M30T"


def test_widget_report_with_photo_creates_attachment(client, app, organization, roles, regular_user):
    login(client, username="pilot")
    client.post(f"/roles/activate/{roles['pilot_camera'].id}")

    response = client.post(
        "/tickets/melden",
        data={"title": "Kamera verschmutzt", "photo": (io.BytesIO(_PNG_BYTES), "photo.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 302

    ticket = Ticket.query.filter_by(organization_id=organization.id, title="Kamera verschmutzt").first()
    assert ticket is not None
    assert len(ticket.attachments) == 1


def test_widget_report_validation_error_flashes_instead_of_creating_ticket(client, app, organization, roles, regular_user):
    login(client, username="pilot")
    client.post(f"/roles/activate/{roles['pilot_camera'].id}")

    response = client.post("/tickets/melden", data={"title": "   "})
    assert response.status_code == 302

    with client.session_transaction() as sess:
        flashes = sess.get("_flashes", [])
    assert any(category == "error" for category, _ in flashes)
    assert Ticket.query.filter_by(organization_id=organization.id).count() == 0


def test_widget_report_requires_tickets_create_permission(client, app, organization, roles):
    role = _role_with_only_dashboard_view(organization)
    _add_user_with_role(organization, role)

    login(client, username="widgetuser")
    client.post(f"/roles/activate/{role.id}")
    response = client.post("/tickets/melden", data={"title": "Sollte scheitern"})
    assert response.status_code == 403
