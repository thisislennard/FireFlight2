import os

import pytest

os.environ.setdefault(
    "TEST_DATABASE_URL",
    "postgresql://fireflight2:fireflight2-local@localhost:5432/fireflight2_test",
)

from app import create_app  # noqa: E402
from app.extensions import db as _db  # noqa: E402


@pytest.fixture
def app():
    application = create_app("testing")
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def organization(app):
    from app.organizations.models import Organization

    org = Organization(name="Test-Feuerwehr")
    _db.session.add(org)
    _db.session.commit()
    return org


@pytest.fixture
def roles(app, organization):
    from app.roles.services import seed_roles

    return seed_roles(organization.id)


@pytest.fixture
def admin_user(app, organization, roles):
    from app.auth.services import create_user

    user = create_user(
        organization_id=organization.id,
        username="admin",
        email="admin@example.org",
        pin="4726",
        display_name="Admin Test",
    )
    user.roles = [roles["administrator"]]
    _db.session.commit()
    return user


@pytest.fixture
def regular_user(app, organization, roles):
    from app.auth.services import create_user

    user = create_user(
        organization_id=organization.id,
        username="pilot",
        email="pilot@example.org",
        pin="4726",
        display_name="Pilot Test",
    )
    user.roles = [roles["pilot_camera"]]
    _db.session.commit()
    return user


def login(client, username="admin", pin="4726"):
    return client.post("/auth/login", data={"identifier": username, "pin": pin})
