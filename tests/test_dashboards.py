from jinja2 import ChoiceLoader, DictLoader

from tests.conftest import login


def test_dashboard_created_automatically_for_role(app, roles):
    from app.dashboards.services import get_or_create_dashboard

    dashboard = get_or_create_dashboard(roles["pilot_camera"])
    assert dashboard.role_id == roles["pilot_camera"].id


def test_widget_can_be_added_and_saved(app, roles):
    from app.dashboards.services import add_widget, get_or_create_dashboard

    dashboard = get_or_create_dashboard(roles["pilot_camera"])
    widget = add_widget(dashboard, widget_type="heading", title="Test", config={"text": "Hallo"})
    assert widget.id is not None
    assert widget in dashboard.widgets


def test_dashboard_view_renders_for_logged_in_user(client, admin_user, roles):
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")
    response = client.get("/dashboard/")
    assert response.status_code == 200


def test_admin_can_add_widget_via_editor(client, admin_user, roles):
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")
    role_id = roles["pilot_camera"].id
    response = client.post(f"/administration/dashboards/{role_id}/widgets", data={"widget_type": "metric"})
    assert response.status_code == 302

    from app.dashboards.services import get_or_create_dashboard

    dashboard = get_or_create_dashboard(roles["pilot_camera"])
    assert any(w.widget_type == "metric" for w in dashboard.widgets)


def test_module_widget_with_template_renders_via_fallback_include(client, admin_user, roles, app):
    """Andockpunkt fuer Fachmodul-Widgets (spec-struktur.md Abschnitt 11): ein Widget-Typ, der ueber
    die Registry mit einem eigenen `template` registriert wird, muss ueber den Fallback-Zweig von
    dashboards/_widget.html gerendert werden, inkl. Zugriff auf `widget` im eigenen Partial."""
    from app.dashboards.services import add_widget, get_or_create_dashboard
    from app.dashboards.widgets import WidgetDefinition, widget_registry

    widget_registry.register(
        WidgetDefinition(
            "custom_test_widget", "Custom Test", {}, template="dashboards/_custom_test_widget.html"
        )
    )
    original_loader = app.jinja_env.loader
    app.jinja_env.loader = ChoiceLoader(
        [DictLoader({"dashboards/_custom_test_widget.html": '<div class="custom-marker">{{ widget.title }}</div>'}), original_loader]
    )
    try:
        login(client)
        client.post(f"/roles/activate/{roles['administrator'].id}")
        dashboard = get_or_create_dashboard(roles["administrator"])
        add_widget(dashboard, widget_type="custom_test_widget", title="Modul-Widget", config={})

        response = client.get("/dashboard/")
        body = response.get_data(as_text=True)
        assert response.status_code == 200
        assert "custom-marker" in body
        assert "Modul-Widget" in body
    finally:
        app.jinja_env.loader = original_loader
        widget_registry._widgets.pop("custom_test_widget", None)
