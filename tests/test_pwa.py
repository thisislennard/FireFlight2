import json

from tests.conftest import login


def test_root_scoped_service_worker_matches_static_file(client, app):
    response = client.get("/sw.js")
    assert response.status_code == 200

    static_response = client.get("/static/js/sw.js")
    assert response.get_data() == static_response.get_data()


def test_manifest_is_valid_and_root_scoped(client, app):
    response = client.get("/static/manifest.webmanifest")
    assert response.status_code == 200

    manifest = json.loads(response.get_data(as_text=True))
    assert manifest["start_url"] == "/"
    assert manifest["scope"] == "/"
    assert manifest["display"] == "standalone"
    sizes = {icon["sizes"] for icon in manifest["icons"]}
    assert "192x192" in sizes
    assert "512x512" in sizes


def test_login_page_links_manifest_and_registers_service_worker(client, app):
    response = client.get("/auth/login")
    body = response.get_data(as_text=True)
    assert 'rel="manifest"' in body
    assert "manifest.webmanifest" in body
    assert "js/pwa.js" in body


def test_dashboard_links_manifest_for_authenticated_users(client, app, organization, roles, regular_user):
    login(client, username="pilot")
    client.post(f"/roles/activate/{roles['pilot_camera'].id}")
    response = client.get("/dashboard/")
    body = response.get_data(as_text=True)
    assert 'rel="manifest"' in body
    assert "js/pwa.js" in body
