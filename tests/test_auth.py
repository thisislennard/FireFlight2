from app.auth.services import set_user_active
from tests.conftest import login


def test_login_success_redirects(client, admin_user):
    response = login(client)
    assert response.status_code == 302


def test_login_wrong_password_fails(client, admin_user):
    response = login(client, password="falsches-passwort")
    assert response.status_code == 200
    assert "falsch" in response.get_data(as_text=True)


def test_disabled_user_cannot_login(client, regular_user):
    set_user_active(regular_user, False)
    response = login(client, username="pilot")
    assert response.status_code == 200
    assert "falsch" in response.get_data(as_text=True)


def test_account_locks_after_too_many_failed_attempts(client, app, regular_user):
    for _ in range(5):
        login(client, username="pilot", password="falsch")

    response = login(client, username="pilot", password="Sup3rSecret!")
    assert response.status_code == 200
    assert "gesperrt" in response.get_data(as_text=True)


def test_root_redirects_unauthenticated_to_login(client):
    response = client.get("/")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]
