from __future__ import annotations

import uuid

from flask import url_for
from sqlalchemy import extract

from app.auth.models import User
from app.core.exceptions import ValidationError
from app.core.models import utcnow
from app.extensions import db
from app.modules.incidents.models import (
    FLIGHT_STATUS_APPROVED,
    FLIGHT_STATUS_COMPLETED,
    FLIGHT_STATUS_DRAFT,
    FLIGHT_STATUS_PENDING_APPROVAL,
    INCIDENT_KINDS,
    KIND_EINSATZ,
    KIND_UEBUNG,
    Flight,
    Incident,
)


def list_incidents(organization_id: uuid.UUID, *, include_closed: bool = True) -> list[Incident]:
    query = Incident.query.filter_by(organization_id=organization_id)
    if not include_closed:
        query = query.filter_by(is_closed=False)
    return query.order_by(Incident.created_at.desc()).all()


def create_incident(organization_id: uuid.UUID, *, kind: str, title: str, description: str | None = None) -> Incident:
    if kind not in INCIDENT_KINDS:
        raise ValidationError("Ungültige Einsatzart.")
    title = title.strip()
    if not title:
        raise ValidationError("Titel darf nicht leer sein.")
    incident = Incident(organization_id=organization_id, kind=kind, title=title, description=description)
    db.session.add(incident)
    db.session.commit()
    return incident


def update_incident(incident: Incident, **fields) -> Incident:
    for key, value in fields.items():
        setattr(incident, key, value)
    db.session.commit()
    return incident


def close_incident(incident: Incident) -> None:
    incident.is_closed = True
    db.session.commit()


def reopen_incident(incident: Incident) -> None:
    incident.is_closed = False
    db.session.commit()


def add_flight(incident: Incident, **fields) -> Flight:
    flight = Flight(incident_id=incident.id, **fields)
    db.session.add(flight)
    db.session.commit()
    return flight


def update_flight(flight: Flight, **fields) -> Flight:
    for key, value in fields.items():
        setattr(flight, key, value)
    db.session.commit()
    return flight


def delete_flight(flight: Flight) -> None:
    db.session.delete(flight)
    db.session.commit()


def list_flights_with_location(organization_id: uuid.UUID, *, limit: int | None = None) -> list[Flight]:
    """Für die Kartenansicht -- alle Flüge mit mindestens einem gesetzten Standort (Start oder
    Ende). `limit` (neueste zuerst) ist für das kompakte Dashboard-Widget (Phase 13) gedacht -- die
    volle Kartenseite ruft ohne Limit auf, dort bestimmen alle Punkte gemeinsam den Kartenausschnitt,
    Reihenfolge ist dort irrelevant."""
    query = (
        Flight.query.join(Incident)
        .filter(Incident.organization_id == organization_id)
        .filter(
            ((Flight.start_lat.isnot(None)) & (Flight.start_lon.isnot(None)))
            | ((Flight.end_lat.isnot(None)) & (Flight.end_lon.isnot(None)))
        )
        .order_by(Flight.started_at.desc())
    )
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def serialize_flight_marker(flight: Flight) -> dict:
    """Gemeinsame JSON-Serialisierung für Kartenmarker -- genutzt von der vollen Kartenseite
    (`incidents.map_view`) und dem Flugbuch-/Karten-Widget (Phase 13), damit beide dieselben Felder
    liefern und nicht auseinanderlaufen. Nur einfache, JSON-serialisierbare Werte -- `{{ ... | tojson
    }}` kann keine SQLAlchemy-Objekte direkt serialisieren."""
    return {
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
    }


def normalize_incident_kind(raw: str | None) -> str:
    """Bildet die freie Antwort eines Wizard-"choice"-Schritts (Admin-konfigurierter Options-Text)
    auf einen der beiden festen Incident-Kind-Werte ab (Phase 12, app/rc/wizard_flow.py) --
    tolerant gegenüber Groß-/Kleinschreibung, fällt auf "uebung" zurück, wenn der Text nicht
    eindeutig nach "Einsatz" klingt (der sicherere Default: eine fälschlich als Übung geloggte
    Übung ist unkritisch, ein fälschlich als Übung geloggter Einsatz verzerrt die Statistik mehr)."""
    return KIND_EINSATZ if "einsatz" in (raw or "").strip().lower() else KIND_UEBUNG


def create_draft_flight(
    incident: Incident, *, pilot=None, camera_operator=None, drone_label: str | None = None,
    purpose: str | None = None, start_lat: float | None = None, start_lon: float | None = None,
) -> Flight:
    """Preflight-Wizard abgeschlossen (Konzeptdokument Abschnitt 5.2): legt den Flug mit Start-
    Zeitpunkt+Standort an, aber noch ohne Freigabe -- "Flug starten" (request_flight_start) ist ein
    separater, späterer Schritt."""
    flight = Flight(
        incident_id=incident.id,
        pilot_id=pilot.id if pilot else None,
        camera_operator_id=camera_operator.id if camera_operator else None,
        drone_label=drone_label,
        purpose=purpose,
        started_at=utcnow(),
        start_lat=start_lat,
        start_lon=start_lon,
        flight_status=FLIGHT_STATUS_DRAFT,
    )
    db.session.add(flight)
    db.session.commit()
    return flight


def request_flight_start(flight: Flight) -> None:
    flight.flight_status = FLIGHT_STATUS_PENDING_APPROVAL
    flight.start_requested_at = utcnow()
    db.session.commit()


def approve_flight_start(flight: Flight, *, approved_by) -> None:
    flight.flight_status = FLIGHT_STATUS_APPROVED
    flight.start_approved_at = utcnow()
    flight.start_approved_by_id = approved_by.id if approved_by else None
    db.session.commit()


def list_pending_approval_flights(organization_id: uuid.UUID) -> list[Flight]:
    return (
        Flight.query.join(Incident)
        .filter(Incident.organization_id == organization_id, Flight.flight_status == FLIGHT_STATUS_PENDING_APPROVAL)
        .order_by(Flight.start_requested_at)
        .all()
    )


def complete_flight(
    flight: Flight, *, end_lat: float | None = None, end_lon: float | None = None,
    synced: bool = False, had_issues: bool = False, notes: str | None = None,
) -> None:
    """Flugende-Wizard abgeschlossen (Konzeptdokument Abschnitt 5.5)."""
    flight.ended_at = utcnow()
    flight.end_lat = end_lat
    flight.end_lon = end_lon
    flight.synced = synced
    flight.had_issues = had_issues
    flight.notes = notes
    flight.flight_status = FLIGHT_STATUS_COMPLETED
    db.session.commit()


def logbook_summary(organization_id: uuid.UUID, *, year: int | None = None, month: int | None = None) -> list[dict]:
    """Pro Person: Anzahl Einsatz-/Übungsflüge, in denen sie Pilot ODER Kamera-Operator war
    (Konzeptdokument Abschnitt 6/7: "pro Person", nicht nur "als Pilot"). Filterbar nach Jahr/Monat,
    bezogen auf `Flight.started_at` -- Flüge ohne erfasste Startzeit tauchen bei aktivem Filter nicht
    auf (können keinem Zeitraum zugeordnet werden), zählen aber in der ungefilterten Ansicht mit."""
    query = Flight.query.join(Incident).filter(Incident.organization_id == organization_id)
    if year is not None:
        query = query.filter(extract("year", Flight.started_at) == year)
    if month is not None:
        query = query.filter(extract("month", Flight.started_at) == month)

    counts: dict[uuid.UUID, dict[str, int]] = {}
    for flight in query.all():
        for user_id in {flight.pilot_id, flight.camera_operator_id}:
            if user_id is None:
                continue
            entry = counts.setdefault(user_id, {"einsatz": 0, "uebung": 0})
            entry["einsatz" if flight.incident.kind == KIND_EINSATZ else "uebung"] += 1

    users_by_id = {u.id: u for u in User.query.filter(User.id.in_(counts.keys())).all()}
    result = [
        {"user": users_by_id[uid], "einsatz_count": c["einsatz"], "uebung_count": c["uebung"]}
        for uid, c in counts.items()
        if uid in users_by_id
    ]
    result.sort(key=lambda r: r["user"].display_name)
    return result
