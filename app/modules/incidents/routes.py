from __future__ import annotations

import uuid

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.audit.service import log_event
from app.auth.models import User
from app.core.exceptions import ValidationError
from app.core.security.permissions import ensure_permission, get_active_role, permission_required
from app.core.utilities.time import parse_local_datetime
from app.modules.incidents import services
from app.modules.incidents.models import INCIDENT_KINDS, Flight, Incident
from app.notifications.service import send_to_user

bp = Blueprint("incidents", __name__, url_prefix="/incidents")


def _parse_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _flight_fields_from_form(form) -> dict:
    pilot_id = form.get("pilot_id") or None
    camera_operator_id = form.get("camera_operator_id") or None
    return dict(
        pilot_id=uuid.UUID(pilot_id) if pilot_id else None,
        camera_operator_id=uuid.UUID(camera_operator_id) if camera_operator_id else None,
        drone_label=form.get("drone_label") or None,
        battery_label=form.get("battery_label") or None,
        purpose=form.get("purpose") or None,
        started_at=parse_local_datetime(form.get("started_at")),
        start_lat=_parse_float(form.get("start_lat")),
        start_lon=_parse_float(form.get("start_lon")),
        ended_at=parse_local_datetime(form.get("ended_at")),
        end_lat=_parse_float(form.get("end_lat")),
        end_lon=_parse_float(form.get("end_lon")),
        synced="synced" in form,
        had_issues="had_issues" in form,
        notes=form.get("notes") or None,
    )


def _crew_choices():
    return User.query.filter_by(organization_id=current_user.organization_id).order_by(User.display_name).all()


# --- Einsätze/Übungen ----------------------------------------------------------------------------


@bp.route("/")
@login_required
@permission_required("incidents.view")
def list_incidents():
    include_closed = request.args.get("include_closed", "1") != "0"
    return render_template(
        "incidents/list.html",
        incidents=services.list_incidents(current_user.organization_id, include_closed=include_closed),
        include_closed=include_closed,
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
@permission_required("incidents.edit")
def incident_new():
    error = None
    if request.method == "POST":
        try:
            incident = services.create_incident(
                current_user.organization_id,
                kind=request.form.get("kind", ""),
                title=request.form.get("title", ""),
                description=request.form.get("description") or None,
            )
            log_event("incident.create", result="success", object_type="incident", object_id=str(incident.id))
            return redirect(url_for("incidents.incident_detail", incident_id=incident.id))
        except ValidationError as exc:
            error = exc.message
    return render_template("incidents/incident_edit.html", incident=None, error=error, kinds=INCIDENT_KINDS)


@bp.route("/<uuid:incident_id>", methods=["GET", "POST"])
@login_required
@permission_required("incidents.view")
def incident_detail(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    if request.method == "POST":
        ensure_permission(get_active_role(), "incidents.edit")
        services.update_incident(
            incident,
            title=request.form.get("title", incident.title).strip() or incident.title,
            description=request.form.get("description") or None,
        )
        log_event("incident.edit", result="success", object_type="incident", object_id=str(incident.id))
        return redirect(url_for("incidents.incident_detail", incident_id=incident.id))
    return render_template("incidents/incident_detail.html", incident=incident, kinds=INCIDENT_KINDS)


@bp.route("/<uuid:incident_id>/close", methods=["POST"])
@login_required
@permission_required("incidents.edit")
def incident_close(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    services.close_incident(incident)
    log_event("incident.close", result="success", object_type="incident", object_id=str(incident.id))
    return redirect(url_for("incidents.incident_detail", incident_id=incident.id))


@bp.route("/<uuid:incident_id>/reopen", methods=["POST"])
@login_required
@permission_required("incidents.edit")
def incident_reopen(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    services.reopen_incident(incident)
    log_event("incident.reopen", result="success", object_type="incident", object_id=str(incident.id))
    return redirect(url_for("incidents.incident_detail", incident_id=incident.id))


# --- Flüge -----------------------------------------------------------------------------------------


@bp.route("/<uuid:incident_id>/flights/new", methods=["GET", "POST"])
@login_required
@permission_required("incidents.edit")
def flight_new(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    error = None
    if request.method == "POST":
        try:
            flight = services.add_flight(incident, **_flight_fields_from_form(request.form))
            log_event("flight.create", result="success", object_type="flight", object_id=str(flight.id))
            return redirect(url_for("incidents.incident_detail", incident_id=incident.id))
        except ValidationError as exc:
            error = exc.message
    return render_template(
        "incidents/flight_edit.html", incident=incident, flight=None, error=error, crew_choices=_crew_choices()
    )


@bp.route("/<uuid:incident_id>/flights/<uuid:flight_id>", methods=["GET", "POST"])
@login_required
@permission_required("incidents.view")
def flight_edit(incident_id, flight_id):
    flight = Flight.query.filter_by(id=flight_id, incident_id=incident_id).first_or_404()
    error = None
    if request.method == "POST":
        ensure_permission(get_active_role(), "incidents.edit")
        try:
            services.update_flight(flight, **_flight_fields_from_form(request.form))
            log_event("flight.edit", result="success", object_type="flight", object_id=str(flight.id))
            return redirect(url_for("incidents.incident_detail", incident_id=incident_id))
        except ValidationError as exc:
            error = exc.message
    return render_template(
        "incidents/flight_edit.html", incident=flight.incident, flight=flight, error=error,
        crew_choices=_crew_choices(),
    )


@bp.route("/<uuid:incident_id>/flights/<uuid:flight_id>/delete", methods=["POST"])
@login_required
@permission_required("incidents.edit")
def flight_delete(incident_id, flight_id):
    flight = Flight.query.filter_by(id=flight_id, incident_id=incident_id).first_or_404()
    services.delete_flight(flight)
    log_event("flight.delete", result="success", object_type="flight", object_id=str(flight_id))
    return redirect(url_for("incidents.incident_detail", incident_id=incident_id))


# --- Karte -----------------------------------------------------------------------------------------


@bp.route("/karte")
@login_required
@permission_required("incidents.view")
def map_view():
    flights = services.list_flights_with_location(current_user.organization_id)
    # Nur einfache, JSON-serialisierbare Werte -- {{ ... | tojson }} kann keine SQLAlchemy-Objekte
    # direkt serialisieren.
    markers = []
    for flight in flights:
        markers.append({
            "incident_title": flight.incident.title,
            "kind": flight.incident.kind,
            "pilot": flight.pilot.display_name if flight.pilot else None,
            "camera_operator": flight.camera_operator.display_name if flight.camera_operator else None,
            "started_at": flight.started_at.isoformat() if flight.started_at else None,
            "start": {"lat": flight.start_lat, "lon": flight.start_lon}
            if flight.start_lat is not None and flight.start_lon is not None else None,
            "end": {"lat": flight.end_lat, "lon": flight.end_lon}
            if flight.end_lat is not None and flight.end_lon is not None else None,
            "detail_url": url_for("incidents.flight_edit", incident_id=flight.incident_id, flight_id=flight.id),
        })
    return render_template("incidents/map.html", markers=markers)


# --- Startanfragen (Phase 12, Konzeptdokument Abschnitt 5.3) -------------------------------------


@bp.route("/freigaben")
@login_required
@permission_required("incidents.approve_flights")
def pending_approvals():
    return render_template(
        "incidents/pending_approvals.html", flights=services.list_pending_approval_flights(current_user.organization_id)
    )


@bp.route("/<uuid:incident_id>/flights/<uuid:flight_id>/approve", methods=["POST"])
@login_required
@permission_required("incidents.approve_flights")
def flight_approve(incident_id, flight_id):
    flight = Flight.query.filter_by(id=flight_id, incident_id=incident_id).first_or_404()
    services.approve_flight_start(flight, approved_by=current_user)
    log_event("flight.approved", result="success", object_type="flight", object_id=str(flight.id))

    operator = flight.pilot or flight.camera_operator
    if operator is not None:
        try:
            send_to_user(operator, title="Flug freigegeben", body="Dein Flug wurde freigegeben.")
        except ValidationError:
            pass  # VAPID evtl. nicht konfiguriert -- die Genehmigung selbst darf trotzdem gelten
    return redirect(url_for("incidents.pending_approvals"))


# --- Logbuch --------------------------------------------------------------------------------------


@bp.route("/logbuch")
@login_required
@permission_required("incidents.view")
def logbook():
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    return render_template(
        "incidents/logbook.html",
        rows=services.logbook_summary(current_user.organization_id, year=year, month=month),
        year=year, month=month,
    )
