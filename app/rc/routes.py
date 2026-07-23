from __future__ import annotations

import uuid

from flask import Blueprint, current_app, g, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.audit.service import log_event
from app.auth.models import QUALIFICATION_PILOT, User
from app.auth.services import AccountLockedError, authenticate
from app.core.exceptions import ValidationError
from app.core.models import get_setting
from app.extensions import db
from app.modules.incidents.models import FLIGHT_STATUS_APPROVED, FLIGHT_STATUS_DRAFT, Flight, Incident
from app.modules.incidents.services import (
    complete_flight,
    create_draft_flight,
    create_incident,
    normalize_incident_kind,
    request_flight_start,
)
from app.modules.incidents.wizard_fields import (
    FIELD_KEY_END_LOCATION,
    FIELD_KEY_HAD_ISSUES,
    FIELD_KEY_INCIDENT_KIND,
    FIELD_KEY_NOTES,
    FIELD_KEY_PURPOSE,
    FIELD_KEY_START_LOCATION,
    FIELD_KEY_SYNCED,
)
from app.notifications.service import send_to_users
from app.rc.forms import DevicePairForm, RcPinForm
from app.rc.services import mark_paired, resolve_device_by_key
from app.rc.wizard_flow import collect_field_answers, get_flight_end_wizard, get_preflight_wizard
from app.roles.models import Role
from app.wizards.runner import WizardRunner

bp = Blueprint("rc", __name__, url_prefix="/rc")

DEVICE_COOKIE_NAME = "rc_device_token"
DEVICE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365 * 5  # 5 Jahre -- physisches Gerät, keine Ablaufroutine vorgesehen
_DEVICE_EXEMPT_ENDPOINTS = {"rc.pair", "rc.service_worker"}
_LOGIN_CANDIDATE_SESSION_KEY = "rc_login_candidate_id"
_PREFLIGHT_STATE_KEY = "rc_preflight_state"
_FLIGHT_END_STATE_KEY = "rc_flight_end_state"
_ACTIVE_FLIGHT_SESSION_KEY = "rc_active_flight_id"
# Bediener-spezifischer Session-Zustand, der beim Bedienerwechsel (rc.logout) NICHT an den nächsten
# Bediener desselben Geräts weitergereicht werden darf -- sonst würde z. B. der nächste Pilot den
# noch offenen Flug der vorigen Person sehen (Phase 12).
_OPERATOR_SESSION_KEYS = (_PREFLIGHT_STATE_KEY, _FLIGHT_END_STATE_KEY, _ACTIVE_FLIGHT_SESSION_KEY)


def _active_flight() -> Flight | None:
    flight_id = session.get(_ACTIVE_FLIGHT_SESSION_KEY)
    return db.session.get(Flight, uuid.UUID(flight_id)) if flight_id else None


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
    verknüpft -- daher bewusst kein `session.clear()` wie beim Desktop-Logout. Zusätzlich zu
    `rc_device_id` werden ab Phase 12 auch alle Bediener-spezifischen Wizard-/Flug-Zustände entfernt
    (`_OPERATOR_SESSION_KEYS`) -- sonst würde der nächste Bediener desselben Geräts den noch offenen
    Flug der vorigen Person sehen."""
    log_event("rc_device.operator_logout", result="success")
    logout_user()
    session.pop("rc_device_id", None)
    for key in _OPERATOR_SESSION_KEYS:
        session.pop(key, None)
    return redirect(url_for("rc.login"))


@bp.route("/home")
@login_required
def home():
    return render_template(
        "rc/home.html",
        device=g.rc_device,
        vapid_public_key=current_app.config["VAPID_PUBLIC_KEY"],
        dji_pilot2_deeplink=get_setting("rc_dji_pilot2_deeplink_url"),
        flight=_active_flight(),
    )


# --- Preflight-/Flugstart-/Flugende-Wizard (Phase 12, Konzeptdokument Abschnitt 5.2-5.6) ----------


@bp.route("/preflight", methods=["GET", "POST"])
@login_required
def preflight():
    if _active_flight() is not None:
        return redirect(url_for("rc.home"))

    wizard = get_preflight_wizard()
    if wizard is None:
        return render_template("rc/wizard_missing.html", kind="Preflight")

    state = session.get(_PREFLIGHT_STATE_KEY, {})
    runner = WizardRunner(wizard, state)

    error = None
    if request.method == "POST":
        action = request.form.get("action", "next")
        if action == "back":
            runner.back()
        elif not runner.submit(request.form):
            error = "Bitte alle erforderlichen Angaben machen, bevor du weitergehst."
        session[_PREFLIGHT_STATE_KEY] = runner.state

    if error is None and runner.is_finished:
        return redirect(url_for("rc.preflight_incident"))

    return render_template(
        "rc/wizard_step.html", wizard=wizard, runner=runner, error=error, back_url=url_for("rc.home")
    )


@bp.route("/preflight/incident", methods=["GET", "POST"])
@login_required
def preflight_incident():
    """Konzeptdokument Abschnitt 6: "An der Fernbedienung kann man sich in einen laufenden
    Einsatz/Übung einbuchen, um dort weiterzumachen" -- Auswahl zwischen bestehenden offenen
    Einsätzen/Übungen passender Art oder Neuanlage, direkt im Anschluss an den Preflight-Wizard."""
    if _active_flight() is not None:
        return redirect(url_for("rc.home"))

    wizard = get_preflight_wizard()
    state = session.get(_PREFLIGHT_STATE_KEY)
    if wizard is None or not state:
        return redirect(url_for("rc.preflight"))
    runner = WizardRunner(wizard, state)
    if not runner.is_finished:
        return redirect(url_for("rc.preflight"))

    answers = collect_field_answers(runner)
    kind = normalize_incident_kind(answers.get(FIELD_KEY_INCIDENT_KIND))
    open_incidents = (
        Incident.query.filter_by(organization_id=current_user.organization_id, kind=kind, is_closed=False)
        .order_by(Incident.created_at.desc())
        .all()
    )

    error = None
    if request.method == "POST":
        incident_id = request.form.get("incident_id")
        new_title = request.form.get("new_title", "").strip()
        incident = None
        if incident_id:
            incident = next((i for i in open_incidents if str(i.id) == incident_id), None)
        elif new_title:
            try:
                incident = create_incident(current_user.organization_id, kind=kind, title=new_title)
            except ValidationError as exc:
                error = exc.message
        else:
            error = "Bitte einen Einsatz/eine Übung wählen oder einen Titel für einen neuen eingeben."

        if incident is not None:
            # Welche Crew-Rolle der Bediener einnimmt, richtet sich nach dem Qualifikationsfilter
            # dieses Geräts (bzw. der eigenen Qualifikation bei einem ungefilterten Gerät) -- ein
            # Gerät bildet bewusst nur EINE Rolle je Flug ab, s. docs/roadmap.md "Phase 12".
            qualification = g.rc_device.required_qualification
            is_pilot_seat = qualification == QUALIFICATION_PILOT or (
                qualification is None and current_user.is_pilot
            )
            location = answers.get(FIELD_KEY_START_LOCATION) or {}
            flight = create_draft_flight(
                incident,
                pilot=current_user if is_pilot_seat else None,
                camera_operator=None if is_pilot_seat else current_user,
                purpose=answers.get(FIELD_KEY_PURPOSE),
                start_lat=location.get("lat"),
                start_lon=location.get("lon"),
            )
            session.pop(_PREFLIGHT_STATE_KEY, None)
            session[_ACTIVE_FLIGHT_SESSION_KEY] = str(flight.id)
            log_event("flight.preflight_completed", result="success", user=current_user,
                       object_type="flight", object_id=str(flight.id))
            return redirect(url_for("rc.home"))

    return render_template("rc/preflight_incident.html", incidents=open_incidents, kind=kind, error=error)


@bp.route("/flight/start", methods=["POST"])
@login_required
def flight_start():
    """"Flug starten" (Konzeptdokument Abschnitt 5.3) -- ist zugleich die Startanfrage: die eigentliche
    Freigabe ("Zu DJI Pilot 2 wechseln" wird erst danach sichtbar) erfolgt über das Desktop-Genehmigungs-UI
    (app/modules/incidents/routes.py: flight_approve)."""
    flight = _active_flight()
    if flight is None or flight.flight_status != FLIGHT_STATUS_DRAFT:
        return redirect(url_for("rc.home"))

    request_flight_start(flight)
    log_event("flight.start_requested", result="success", user=current_user,
               object_type="flight", object_id=str(flight.id))

    roles = Role.query.filter_by(organization_id=current_user.organization_id).all()
    approver_roles = [
        role for role in roles
        if role.is_system or any(p.key == "incidents.approve_flights" for p in role.permissions)
    ]
    approvers = list({u.id: u for role in approver_roles for u in role.users if u.is_active_account}.values())
    try:
        send_to_users(
            approvers, title="Startanfrage",
            body=f"{current_user.display_name} bittet um Freigabe für einen Flug.",
        )
    except ValidationError:
        pass  # VAPID evtl. nicht konfiguriert -- die Startanfrage selbst darf trotzdem funktionieren

    return redirect(url_for("rc.home"))


@bp.route("/flight-end", methods=["GET", "POST"])
@login_required
def flight_end():
    flight = _active_flight()
    if flight is None or flight.flight_status != FLIGHT_STATUS_APPROVED:
        return redirect(url_for("rc.home"))

    wizard = get_flight_end_wizard()
    if wizard is None:
        return render_template("rc/wizard_missing.html", kind="Flugende")

    state = session.get(_FLIGHT_END_STATE_KEY, {})
    runner = WizardRunner(wizard, state)

    error = None
    if request.method == "POST":
        action = request.form.get("action", "next")
        if action == "back":
            runner.back()
        elif not runner.submit(request.form):
            error = "Bitte alle erforderlichen Angaben machen, bevor du weitergehst."
        session[_FLIGHT_END_STATE_KEY] = runner.state

    if error is None and runner.is_finished:
        answers = collect_field_answers(runner)
        end_location = answers.get(FIELD_KEY_END_LOCATION) or {}
        # FIELD_KEY_SYNCED/FIELD_KEY_HAD_ISSUES erwarten den Step-Typ "choice" mit Optionen
        # "Ja"/"Nein" (s. app/modules/incidents/wizard_fields.py) -- "confirmation" wäre hier falsch,
        # da der die Antwort erzwingt statt beide Ja/Nein-Antworten gleichermaßen zuzulassen.
        complete_flight(
            flight, end_lat=end_location.get("lat"), end_lon=end_location.get("lon"),
            synced=answers.get(FIELD_KEY_SYNCED) == "Ja", had_issues=answers.get(FIELD_KEY_HAD_ISSUES) == "Ja",
            notes=answers.get(FIELD_KEY_NOTES),
        )
        session.pop(_FLIGHT_END_STATE_KEY, None)
        session.pop(_ACTIVE_FLIGHT_SESSION_KEY, None)
        log_event("flight.completed", result="success", user=current_user,
                   object_type="flight", object_id=str(flight.id))
        return redirect(url_for("rc.flight_end_summary"))

    return render_template(
        "rc/wizard_step.html", wizard=wizard, runner=runner, error=error, back_url=url_for("rc.home")
    )


@bp.route("/flight-end/summary")
@login_required
def flight_end_summary():
    return render_template("rc/flight_end_summary.html")


@bp.route("/flight-end/restart", methods=["POST"])
@login_required
def flight_end_restart():
    """"Selbe Person, neuer Flug" (Konzeptdokument Abschnitt 5.6): Bediener bleibt angemeldet, der
    Preflight-Wizard startet von vorne. "Komplett neu" nutzt stattdessen das bestehende `/rc/logout`
    (voller Bedienerwechsel zurück zu Schritt 1 der Anmeldung)."""
    return redirect(url_for("rc.preflight"))


@bp.route("/sw.js")
def service_worker():
    # Eigene Route statt direkt /static/js/sw-rc.js: der Browser leitet den Service-Worker-Scope aus
    # dem Pfad der REQUEST-URL ab, nicht aus dem Speicherort der Datei -- nur so bekommt der
    # RC-Service-Worker automatisch Scope "/rc/" ohne zusätzlichen Service-Worker-Allowed-Header.
    return current_app.send_static_file("js/sw-rc.js")
