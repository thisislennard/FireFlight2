from flask import Blueprint, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.audit.service import log_event
from app.auth.forms import LoginForm
from app.auth.services import AccountLockedError, authenticate
from app.extensions import limiter

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _is_safe_redirect(target: str | None) -> bool:
    # Schutz vor Open Redirects: nur relative, selbst beginnende Pfade erlauben (spec-struktur.md Abschnitt 18).
    return bool(target) and target.startswith("/") and not target.startswith("//")


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("roles.select"))

    form = LoginForm()
    error = None
    if form.validate_on_submit():
        try:
            user = authenticate(form.identifier.data.strip(), form.password.data)
        except AccountLockedError:
            error = "Konto vorübergehend gesperrt. Bitte in einigen Minuten erneut versuchen."
        else:
            if user is None:
                error = "Benutzername/E-Mail oder Passwort ist falsch."
            else:
                session.clear()  # Session-Fixation: Inhalt einer evtl. vorbestehenden Session verwerfen
                login_user(user)
                next_url = request.args.get("next")
                return redirect(next_url if _is_safe_redirect(next_url) else url_for("roles.select"))

    return render_template("auth/login.html", form=form, error=error)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    log_event("auth.logout", result="success")
    session.clear()
    logout_user()
    return redirect(url_for("auth.login"))
