from __future__ import annotations

import uuid
from datetime import datetime

from app.core.exceptions import ValidationError
from app.core.models import utcnow
from app.core.utilities.uploads import (
    delete_ticket_attachment_file,
    save_ticket_attachment_file,
)
from app.extensions import db
from app.modules.tickets.models import (
    TICKET_STATUSES,
    MaintenanceEvent,
    MaintenanceRule,
    Ticket,
    TicketAttachment,
    TicketComment,
)


# --- Tickets --------------------------------------------------------------------------------------


def list_tickets(organization_id: uuid.UUID, *, status: str | None = None) -> list[Ticket]:
    query = Ticket.query.filter_by(organization_id=organization_id)
    if status:
        query = query.filter_by(status=status)
    return query.order_by(Ticket.created_at.desc()).all()


def create_ticket(
    organization_id: uuid.UUID, *, title: str, description: str | None, drone_label: str | None, created_by
) -> Ticket:
    title = title.strip()
    if not title:
        raise ValidationError("Titel darf nicht leer sein.")
    ticket = Ticket(
        organization_id=organization_id, title=title, description=description or None,
        drone_label=drone_label or None, created_by_id=created_by.id if created_by else None,
    )
    db.session.add(ticket)
    db.session.commit()
    return ticket


def set_ticket_status(ticket: Ticket, status: str) -> Ticket:
    if status not in TICKET_STATUSES:
        raise ValidationError("Ungültiger Status.")
    ticket.status = status
    db.session.commit()
    return ticket


def add_comment(ticket: Ticket, *, author, body: str) -> TicketComment:
    body = body.strip()
    if not body:
        raise ValidationError("Kommentar darf nicht leer sein.")
    comment = TicketComment(ticket_id=ticket.id, author_id=author.id if author else None, body=body)
    db.session.add(comment)
    db.session.commit()
    return comment


def add_attachment(ticket: Ticket, *, file, uploaded_by) -> TicketAttachment:
    filename = save_ticket_attachment_file(file)
    attachment = TicketAttachment(
        ticket_id=ticket.id, filename=filename, original_filename=file.filename or None,
        uploaded_by_id=uploaded_by.id if uploaded_by else None,
    )
    db.session.add(attachment)
    db.session.commit()
    return attachment


def delete_attachment(attachment: TicketAttachment) -> None:
    delete_ticket_attachment_file(attachment.filename)
    db.session.delete(attachment)
    db.session.commit()


# --- Wartungsintervalle -------------------------------------------------------------------------


def list_maintenance_rules(organization_id: uuid.UUID, *, include_inactive: bool = True) -> list[MaintenanceRule]:
    query = MaintenanceRule.query.filter_by(organization_id=organization_id)
    if not include_inactive:
        query = query.filter_by(is_active=True)
    return query.order_by(MaintenanceRule.title).all()


def create_maintenance_rule(
    organization_id: uuid.UUID, *, title: str, description: str | None, interval_days: int,
    warning_days_before: int,
) -> MaintenanceRule:
    title = title.strip()
    if not title:
        raise ValidationError("Titel darf nicht leer sein.")
    if interval_days <= 0:
        raise ValidationError("Das Intervall muss mindestens 1 Tag betragen.")
    if warning_days_before < 0:
        raise ValidationError("Die Warnfrist darf nicht negativ sein.")
    rule = MaintenanceRule(
        organization_id=organization_id, title=title, description=description or None,
        interval_days=interval_days, warning_days_before=warning_days_before,
    )
    db.session.add(rule)
    db.session.commit()
    return rule


def update_maintenance_rule(rule: MaintenanceRule, **fields) -> MaintenanceRule:
    for key, value in fields.items():
        setattr(rule, key, value)
    db.session.commit()
    return rule


def deactivate_maintenance_rule(rule: MaintenanceRule) -> None:
    rule.is_active = False
    db.session.commit()


def activate_maintenance_rule(rule: MaintenanceRule) -> None:
    rule.is_active = True
    db.session.commit()


def mark_maintenance_completed(
    rule: MaintenanceRule, *, completed_by, completed_at: datetime | None = None, notes: str | None = None
) -> MaintenanceEvent:
    event = MaintenanceEvent(
        rule_id=rule.id, completed_at=completed_at or utcnow(),
        completed_by_id=completed_by.id if completed_by else None, notes=notes or None,
    )
    db.session.add(event)
    db.session.commit()
    return event


def rules_due_or_warning(organization_id: uuid.UUID) -> list[MaintenanceRule]:
    return [
        rule for rule in MaintenanceRule.query.filter_by(organization_id=organization_id, is_active=True).all()
        if rule.is_due or rule.is_warning
    ]
