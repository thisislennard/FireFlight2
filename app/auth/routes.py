from flask import Blueprint, redirect, render_template, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.audit.service import log_event
from app.auth.forms import LoginForm, PinChangeForm
from app.auth.services import AccountLockedError, authenticate, change_pin
from app.core.exceptions import ValidationError
from app.extensions import limiter

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("roles.select"))

    form = LoginForm()
    error = None
    if form.validate_on_submit():
        try:
            user = authenticate(form.identifier.data.strip(), form.pin.data)
        except AccountLockedError as exc:
            if exc.requires_admin_unlock:
                error = "Konto ist gesperrt. Bitte einen Administrator kontaktieren, um die Sperre aufzuheben."
            else:
                error = "Konto vorübergehend gesperrt. Bitte in einigen Minuten erneut versuchen."
        else:
            if user is None:
                error = "Benutzername/E-Mail oder PIN ist falsch."
            else:
                session.clear()  # Session-Fixation: Inhalt einer evtl. vorbestehenden Session verwerfen
                login_user(user)
                return redirect(url_for("roles.select"))

    return render_template("auth/login.html", form=form, error=error)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    log_event("auth.logout", result="success")
    session.clear()
    logout_user()
    return redirect(url_for("auth.login"))


@bp.route("/pin/change", methods=["GET", "POST"])
@login_required
def pin_change():
    form = PinChangeForm()
    error = None
    success = None
    if form.validate_on_submit():
        try:
            change_pin(current_user, current_pin=form.current_pin.data, new_pin=form.new_pin.data)
            success = "PIN erfolgreich geändert."
        except ValidationError as exc:
            error = exc.message
    return render_template("auth/pin_change.html", form=form, error=error, success=success)
