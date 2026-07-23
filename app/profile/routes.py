from __future__ import annotations

import uuid

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from app.auth.models import User
from app.auth.services import update_own_profile
from app.core.exceptions import ValidationError
from app.core.utilities.uploads import delete_profile_image, profile_image_path, save_profile_image

bp = Blueprint("profile", __name__, url_prefix="/profile")

_IMAGE_MIMETYPES = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}


@bp.route("/", methods=["GET", "POST"])
@login_required
def view():
    error = None
    if request.method == "POST":
        try:
            update_own_profile(
                current_user,
                email=request.form.get("email", "").strip(),
                phone_number=request.form.get("phone_number", "").strip() or None,
            )
            image_file = request.files.get("profile_image")
            if image_file and image_file.filename:
                save_profile_image(current_user, image_file)
            flash("Profil aktualisiert.", "success")
            return redirect(url_for("profile.view"))
        except ValidationError as exc:
            error = exc.message
    return render_template("profile/view.html", error=error)


@bp.route("/image/remove", methods=["POST"])
@login_required
def remove_image():
    delete_profile_image(current_user)
    flash("Profilbild entfernt.", "success")
    return redirect(url_for("profile.view"))


@bp.route("/image/<uuid:user_id>")
@login_required
def image(user_id: uuid.UUID):
    # Jeder eingeloggte Nutzer darf jedes Profilbild sehen (internes Single-Tenant-System, kein
    # sensibler Inhalt) -- nur die Bearbeitung ist auf das eigene Konto beschränkt (Route oben).
    user = User.query.get_or_404(user_id)
    path = profile_image_path(user)
    if path is None:
        abort(404)
    ext = path.suffix.lstrip(".")
    return send_file(path, mimetype=_IMAGE_MIMETYPES.get(ext, "application/octet-stream"))
