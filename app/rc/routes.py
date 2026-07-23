from __future__ import annotations

import uuid

from flask import Blueprint, current_app, g, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.audit.service import log_event
from app.auth.models import User
from app.auth.services import AccountLockedError, authenticate
from app.core.models import get_setting
from app.extensions import db
from app.rc.forms import DevicePairForm, RcPinForm
from app.rc.services import mark_paired, resolve_device_by_key

bp = Blueprint("rc", __name__, url_prefix="/rc")

DEVICE_COOKIE_NAME = "rc_device_token"
DEVICE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365 * 5  # 5 Jahre -- physisches Gerät, keine Ablaufroutine vorgesehen
_DEVICE_EXEMPT_ENDPOINTS = {"rc.pair", "rc.service_worker"}
_LOGIN_CANDIDATE_SESSION_KEY = "rc_login_candidate_id"


def _qualified_candidates(device) -> list[User]:
    """Nutzer für Schritt 1 der RC-Anmeldung (Konzeptdokument Abschnitt 5.1): "nur User mit
    passender Qualifikation [...] werden angezeigt". Ohne Qualifikationsfilter am Gerät wird nicht
    jeder aktive Nutzer gezeigt, sondern nur wer überhaupt Pilot- oder Kamera-Qualifikation hat --
    ein Gerät ohne Filter bedeutet "beide Rollen erlaubt", nicht "jede Person erlaubt"."""
    users = (
        User.query.filter_by(organization_id=device.organization_id, is_active_account=True)
        .order_by(User.display_name)
        .all()
    )
    if device.required_qualification:
        return [u for u in users if u.has_qualification(device.required_qualification)]
    return [u for u in users if u.qualifications]


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
    """Zwei-Schritt-Login (Konzeptdokument Abschnitt 5.1, Phase 11): Schritt 1 -- Nutzer aus der
    qualifikationsgefilterten Liste antippen (Zustand nur `_LOGIN_CANDIDATE_SESSION_KEY` in der
    Session, noch keine echte Anmeldung). Schritt 2 -- nur noch PIN-Eingabe für den bereits
    ausgewählten Nutzer. "Anderer Nutzer"/`rc.login_reselect` springt zurück zu Schritt 1."""
    if current_user.is_authenticated:
        return redirect(url_for("rc.home"))

    candidate_id = session.get(_LOGIN_CANDIDATE_SESSION_KEY)
    candidate = db.session.get(User, uuid.UUID(candidate_id)) if candidate_id else None

    if candidate is None:
        candidates = _qualified_candidates(g.rc_device)
        if request.method == "POST":
            selected = next((u for u in candidates if str(u.id) == request.form.get("user_id")), None)
            if selected is not None:
                session[_LOGIN_CANDIDATE_SESSION_KEY] = str(selected.id)
                return redirect(url_for("rc.login"))
        return render_template("rc/login_select.html", candidates=candidates, device=g.rc_device)

    form = RcPinForm()
    error = None
    if form.validate_on_submit():
        try:
            user = authenticate(candidate.username, form.pin.data)
        except AccountLockedError as exc:
            error = (
                "Konto ist gesperrt. Bitte einen Administrator kontaktieren, um die Sperre aufzuheben."
                if exc.requires_admin_unlock
                else "Konto vorübergehend gesperrt. Bitte in einigen Minuten erneut versuchen."
            )
        else:
            if user is None:
                error = "PIN ist falsch."
            elif not user.has_qualification(g.rc_device.required_qualification):
                # PIN war korrekt -- bewusst KEIN _register_failed_attempt/Lockout, das ist kein
                # Bruteforce-Indiz, sondern ein "falsches Gerät für diese Qualifikation"-Fall
                # (Phase 7: Qualifikationsfilter, Konzeptdokument Abschnitt 5.1). In der Praxis sollte
                # das dank der gefilterten Auswahl in Schritt 1 nicht mehr auftreten -- bleibt als
                # Verteidigung gegen zwischenzeitlich geänderte Qualifikationen bestehen.
                log_event("rc_device.operator_login_denied", result="failure", user=user,
                           object_type="rc_device", object_id=str(g.rc_device.id),
                           extra_data={"reason": "qualification_mismatch",
                                       "required": g.rc_device.required_qualification})
                error = "Dieses Gerät ist für eine andere Qualifikation vorgesehen. Ihr Konto ist dafür nicht freigeschaltet."
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
    return render_template("rc/login_pin.html", form=form, error=error, device=g.rc_device, candidate=candidate)


@bp.route("/login/reselect", methods=["POST"])
def login_reselect():
    """"Anderer Nutzer": zurück zu Schritt 1 der RC-Anmeldung, ohne die Geräte-Session zu berühren."""
    session.pop(_LOGIN_CANDIDATE_SESSION_KEY, None)
    return redirect(url_for("rc.login"))


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
