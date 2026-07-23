import base64
import io

import pytest

from app.auth.models import QUALIFICATION_CAMERA_OPERATOR, QUALIFICATION_PILOT
from app.core.exceptions import ValidationError
from app.core.utilities.uploads import profile_image_path, save_profile_image
from app.extensions import db
from tests.conftest import login

# Kleinstmögliches echtes PNG (1x1, transparent) -- für die Magic-Byte-Erkennung reicht der
# Header, der Rest des Testinhalts muss kein dekodierbares Bild sein.
_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
_JPEG_BYTES = b"\xff\xd8\xff" + b"\x00" * 32
_WEBP_BYTES = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 16


# --- Modell: Qualifikationen ---------------------------------------------------------------


def test_user_without_qualifications_has_qualification_none_only(app, organization, roles):
    from app.auth.services import create_user

    user = create_user(
        organization_id=organization.id, username="noqual", email="noqual@example.org",
        pin="4726", display_name="Ohne Qualifikation",
    )
    assert user.qualifications == []
    assert user.has_qualification(None) is True
    assert user.has_qualification(QUALIFICATION_PILOT) is False


def test_user_can_have_both_qualifications(app, organization, roles):
    from app.auth.services import create_user

    user = create_user(
        organization_id=organization.id, username="bothqual", email="bothqual@example.org",
        pin="4726", display_name="Beide Qualifikationen",
    )
    user.is_pilot = True
    user.is_camera_operator = True
    db.session.commit()
    assert set(user.qualifications) == {QUALIFICATION_PILOT, QUALIFICATION_CAMERA_OPERATOR}
    assert user.has_qualification(QUALIFICATION_PILOT) is True
    assert user.has_qualification(QUALIFICATION_CAMERA_OPERATOR) is True


# --- Admin: Qualifikationen setzen -----------------------------------------------------------


def test_admin_can_set_qualifications_via_user_edit(client, admin_user, roles, organization, regular_user):
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")

    response = client.post(
        f"/administration/users/{regular_user.id}",
        data={
            "display_name": regular_user.display_name,
            "email": regular_user.email,
            "role_ids": [str(roles["pilot_camera"].id)],
            "is_pilot": "on",
            "is_camera_operator": "on",
        },
    )
    assert response.status_code == 302
    db.session.refresh(regular_user)
    assert regular_user.is_pilot is True
    assert regular_user.is_camera_operator is True


def test_admin_unchecking_qualification_removes_it(client, admin_user, roles, organization, regular_user):
    regular_user.is_pilot = True
    db.session.commit()
    login(client)
    client.post(f"/roles/activate/{roles['administrator'].id}")

    client.post(
        f"/administration/users/{regular_user.id}",
        data={
            "display_name": regular_user.display_name,
            "email": regular_user.email,
            "role_ids": [str(roles["pilot_camera"].id)],
        },
    )
    db.session.refresh(regular_user)
    assert regular_user.is_pilot is False


# --- Self-Service-Profil: E-Mail/Telefon -------------------------------------------------------


def test_profile_view_renders_for_any_logged_in_user(client, regular_user):
    login(client, username="pilot")
    response = client.get("/profile/")
    assert response.status_code == 200
    assert regular_user.display_name in response.get_data(as_text=True)


def test_profile_update_email_and_phone(client, app, regular_user):
    login(client, username="pilot")
    response = client.post("/profile/", data={"email": "neu@example.org", "phone_number": "+49 170 1234567"})
    assert response.status_code == 302
    db.session.refresh(regular_user)
    assert regular_user.email == "neu@example.org"
    assert regular_user.phone_number == "+49 170 1234567"


def test_profile_update_rejects_email_already_used_by_other_account(client, app, organization, roles, regular_user):
    from app.auth.services import create_user

    create_user(
        organization_id=organization.id, username="other", email="taken@example.org",
        pin="4726", display_name="Andere Person",
    )
    login(client, username="pilot")
    response = client.post("/profile/", data={"email": "taken@example.org", "phone_number": ""})
    assert response.status_code == 200
    assert "bereits" in response.get_data(as_text=True)
    db.session.refresh(regular_user)
    assert regular_user.email != "taken@example.org"


def test_profile_update_clears_phone_number_with_empty_string(client, app, regular_user):
    regular_user.phone_number = "+49 170 1234567"
    db.session.commit()
    login(client, username="pilot")
    client.post("/profile/", data={"email": regular_user.email, "phone_number": ""})
    db.session.refresh(regular_user)
    assert regular_user.phone_number is None


# --- Profilbild: Service-Validierung (Magic Bytes) ---------------------------------------------


def test_save_profile_image_accepts_png(app, regular_user):
    file = _make_file(_PNG_BYTES, "picture.png")
    save_profile_image(regular_user, file)
    assert regular_user.profile_image_filename == f"{regular_user.id}.png"
    assert profile_image_path(regular_user) is not None


def test_save_profile_image_accepts_jpeg_and_webp(app, regular_user):
    save_profile_image(regular_user, _make_file(_JPEG_BYTES, "a.jpg"))
    assert regular_user.profile_image_filename.endswith(".jpg")
    save_profile_image(regular_user, _make_file(_WEBP_BYTES, "b.webp"))
    assert regular_user.profile_image_filename.endswith(".webp")


def test_save_profile_image_rejects_non_image_content_regardless_of_filename(app, regular_user):
    file = _make_file(b"<script>alert(1)</script>", "innocent.png")
    with pytest.raises(ValidationError):
        save_profile_image(regular_user, file)


def test_save_profile_image_rejects_empty_file(app, regular_user):
    with pytest.raises(ValidationError):
        save_profile_image(regular_user, _make_file(b"", "empty.png"))


def test_save_profile_image_rejects_oversized_file(app, regular_user):
    from app.core.utilities.uploads import MAX_PROFILE_IMAGE_BYTES

    oversized = b"x" * (MAX_PROFILE_IMAGE_BYTES + 1)
    with pytest.raises(ValidationError):
        save_profile_image(regular_user, _make_file(oversized, "huge.png"))


def test_save_profile_image_replaces_previous_image(app, regular_user):
    save_profile_image(regular_user, _make_file(_PNG_BYTES, "a.png"))
    first_path = profile_image_path(regular_user)
    save_profile_image(regular_user, _make_file(_JPEG_BYTES, "b.jpg"))
    assert not first_path.exists()
    assert regular_user.profile_image_filename.endswith(".jpg")


# --- Self-Service-Profil: Bild-Upload/-Entfernen über die Route --------------------------------


def test_profile_upload_via_route_and_serve_image(client, app, regular_user):
    login(client, username="pilot")
    response = client.post(
        "/profile/",
        data={"email": regular_user.email, "phone_number": "", "profile_image": (io.BytesIO(_PNG_BYTES), "me.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 302
    db.session.refresh(regular_user)
    assert regular_user.profile_image_filename is not None

    image_response = client.get(f"/profile/image/{regular_user.id}")
    assert image_response.status_code == 200
    assert image_response.mimetype == "image/png"


def test_profile_upload_via_route_rejects_invalid_content(client, app, regular_user):
    login(client, username="pilot")
    response = client.post(
        "/profile/",
        data={
            "email": regular_user.email, "phone_number": "",
            "profile_image": (io.BytesIO(b"not an image"), "fake.png"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert "Nur PNG" in response.get_data(as_text=True)
    db.session.refresh(regular_user)
    assert regular_user.profile_image_filename is None


def test_profile_remove_image(client, app, regular_user):
    save_profile_image(regular_user, _make_file(_PNG_BYTES, "a.png"))
    login(client, username="pilot")

    response = client.post("/profile/image/remove")
    assert response.status_code == 302
    db.session.refresh(regular_user)
    assert regular_user.profile_image_filename is None

    image_response = client.get(f"/profile/image/{regular_user.id}")
    assert image_response.status_code == 404


# --- CLI: seed-test-data -----------------------------------------------------------------------


def test_seed_test_data_gives_pilot_camera_test_user_both_qualifications(app):
    from app.auth.models import User

    runner = app.test_cli_runner()
    runner.invoke(args=["init-fireflight"], env={"FIREFLIGHT_ADMIN_PIN": "4726"})
    runner.invoke(args=["seed-test-data"])

    user = User.query.filter_by(username="test_pilot_camera").first()
    assert user is not None
    assert user.is_pilot is True
    assert user.is_camera_operator is True


def _make_file(content: bytes, filename: str):
    from werkzeug.datastructures import FileStorage

    return FileStorage(stream=io.BytesIO(content), filename=filename)
