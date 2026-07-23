from __future__ import annotations

import uuid

from sqlalchemy import extract

from app.auth.models import User
from app.core.exceptions import ValidationError
from app.extensions import db
from app.modules.incidents.models import KIND_EINSATZ, INCIDENT_KINDS, Flight, Incident


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


def list_flights_with_location(organization_id: uuid.UUID) -> list[Flight]:
    """Für die Kartenansicht -- alle Flüge mit mindestens einem gesetzten Standort (Start oder
    Ende)."""
    return (
        Flight.query.join(Incident)
        .filter(Incident.organization_id == organization_id)
        .filter(
            ((Flight.start_lat.isnot(None)) & (Flight.start_lon.isnot(None)))
            | ((Flight.end_lat.isnot(None)) & (Flight.end_lon.isnot(None)))
        )
        .all()
    )


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
