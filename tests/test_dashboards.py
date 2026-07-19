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
