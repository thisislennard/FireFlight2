from __future__ import annotations

from flask import Blueprint, current_app, g, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.audit.service import log_event
from app.auth.forms import LoginForm
from app.auth.services import AccountLockedError, authenticate
from app.core.models import get_setting
from app.rc.forms import DevicePairForm
from app.rc.services import mark_paired, resolve_device_by_key

bp = Blueprint("rc", __name__, url_prefix="/rc")

DEVICE_COOKIE_NAME = "rc_device_token"
DEVICE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365 * 5  # 5 Jahre -- physisches Gerät, keine Ablaufroutine vorgesehen
_DEVICE_EXEMPT_ENDPOINTS = {"rc.pair", "rc.service_worker"}


@bp.before_request
def _load_device():
    g.rc_device = resolve_device_by_key(request.cookies.get(DEVICE_COOKIE_NAME, ""))
    if request.endpoint in _DEVICE_EXEMPT_ENDPOINTS:
        return None
    if g.rc_device is None:
        return redirect(url_for("rc.pair"))
    return None


@bp.route("/pair", methods=["GET", "POST"])
def pair():
    if g.rc_device is not None:
        return redirect(url_for("rc.login"))

    form = DevicePairForm()
    error = None
    if form.validate_on_submit():
        device_key = form.device_key.data.strip()
        device = resolve_device_by_key(device_key)
        if device is None:
            error = "Unbekannter oder ungültiger Geräteschlüssel."
        else:
            mark_paired(device)
            log_event("rc_device.paired", result="success", object_type="rc_device", object_id=str(device.id))
            response = redirect(url_for("rc.login"))
            response.set_cookie(
                DEVICE_COOKIE_NAME,
                device_key,
                max_age=DEVICE_COOKIE_MAX_AGE,
                httponly=True,
                secure=current_app.config["SESSION_COOKIE_SECURE"],
                samesite="Strict",
            )
            return response
    return render_template("rc/pair.html", form=form, error=error)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("rc.home"))

    form = LoginForm()
    error = None
    if form.validate_on_submit():
        try:
            user = authenticate(form.identifier.data.strip(), form.pin.data)
        except AccountLockedError as exc:
            error = (
                "Konto ist gesperrt. Bitte einen Administrator kontaktieren, um die Sperre aufzuheben."
                if exc.requires_admin_unlock
                else "Konto vorübergehend gesperrt. Bitte in einigen Minuten erneut versuchen."
            )
        else:
            if user is None:
                error = "Benutzername/E-Mail oder PIN ist falsch."
            else:
                # session.clear() wie beim Desktop-Login (Session-Fixation-Schutz) -- die
                # Geräte-Zuordnung wird danach neu gesetzt, die Geräte-Session selbst (Cookie) ist
                # davon unabhängig (Restrukturierungsplan Abschnitt 4).
                device_id = str(g.rc_device.id)
                session.clear()
                session["rc_device_id"] = device_id
                login_user(user)
                log_event("rc_device.operator_login", result="success", user=user,
                           object_type="rc_device", object_id=device_id)
                return redirect(url_for("rc.home"))
    return render_template("rc/login.html", form=form, error=error, device=g.rc_device)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """"Person wechseln": meldet nur den Bediener ab. Die Geräte-Session hängt allein am
    `rc_device_token`-Cookie (bleibt unangetastet) und wird beim nächsten Login neu mit der Session
    verknüpft -- daher bewusst kein `session.clear()` wie beim Desktop-Logout, nur der
    Bediener-spezifische `rc_device_id`-Eintrag wird aufgeräumt."""
    log_event("rc_device.operator_logout", result="success")
    logout_user()
    session.pop("rc_device_id", None)
    return redirect(url_for("rc.login"))


@bp.route("/home")
@login_required
def home():
    return render_template(
        "rc/home.html",
        device=g.rc_device,
        vapid_public_key=current_app.config["VAPID_PUBLIC_KEY"],
        dji_pilot2_deeplink=get_setting("rc_dji_pilot2_deeplink_url"),
    )


@bp.route("/sw.js")
def service_worker():
    # Eigene Route statt direkt /static/js/sw-rc.js: der Browser leitet den Service-Worker-Scope aus
    # dem Pfad der REQUEST-URL ab, nicht aus dem Speicherort der Datei -- nur so bekommt der
    # RC-Service-Worker automatisch Scope "/rc/" ohne zusätzlichen Service-Worker-Allowed-Header.
    return current_app.send_static_file("js/sw-rc.js")
