import uuid
from datetime import datetime, timedelta

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models import TimestampMixin, UUIDPrimaryKeyMixin, utcnow
from app.extensions import db

TICKET_STATUS_OPEN = "open"
TICKET_STATUS_IN_PROGRESS = "in_progress"
TICKET_STATUS_CLOSED = "closed"
TICKET_STATUSES = (TICKET_STATUS_OPEN, TICKET_STATUS_IN_PROGRESS, TICKET_STATUS_CLOSED)


class Ticket(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """Technisches Problem (Konzeptdokument Abschnitt 9/10) -- Erstellen ist bewusst breit
    zugänglich (jede Crew soll ein Problem melden können), Status/Verwaltung ist Gerätewart-Domäne
    (`tickets.manage`), s. app/roles/defaults.py. `drone_label` bewusst Freitext wie
    `Flight.drone_label` (app/modules/incidents/) -- kein Geräte-Modul vorhanden."""

    __tablename__ = "tickets"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    drone_label: Mapped[str | None] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=TICKET_STATUS_OPEN)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    organization = relationship("Organization")
    created_by = relationship("User", foreign_keys=[created_by_id])
    comments = relationship(
        "TicketComment", back_populates="ticket", order_by="TicketComment.created_at", cascade="all, delete-orphan"
    )
    attachments = relationship(
        "TicketAttachment", back_populates="ticket", order_by="TicketAttachment.created_at",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Ticket {self.title!r}>"


class TicketComment(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "ticket_comments"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(String(2000), nullable=False)

    ticket = relationship("Ticket", back_populates="comments")
    author = relationship("User")


class TicketAttachment(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """`filename` ist der server-generierte Name (app/core/utilities/uploads.py:
    save_ticket_attachment_file(), UUID-basiert -- verhindert Path Traversal beim Servieren);
    `original_filename` nur zur Anzeige, nie für Dateisystemzugriffe verwendet."""

    __tablename__ = "ticket_attachments"

    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    ticket = relationship("Ticket", back_populates="attachments")
    uploaded_by = relationship("User")


class MaintenanceRule(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """Wartungsintervall (Konzeptdokument Abschnitt 10: "Wartungsintervalle setzen [...] und
    Push-Benachrichtigungen erhalten"). Kein separates `last_completed_at`-Feld -- wird aus dem
    jüngsten `MaintenanceEvent` abgeleitet (Fallback `created_at`, falls noch nie erledigt), damit es
    nie mit der Ereignis-Historie auseinanderlaufen kann."""

    __tablename__ = "maintenance_rules"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False)
    warning_days_before: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    organization = relationship("Organization")
    events = relationship(
        "MaintenanceEvent", back_populates="rule", order_by="MaintenanceEvent.completed_at.desc()",
        cascade="all, delete-orphan",
    )

    @property
    def last_completed_at(self) -> datetime:
        return self.events[0].completed_at if self.events else self.created_at

    @property
    def next_due_at(self) -> datetime:
        return self.last_completed_at + timedelta(days=self.interval_days)

    @property
    def warning_at(self) -> datetime:
        return self.next_due_at - timedelta(days=self.warning_days_before)

    @property
    def is_due(self) -> bool:
        return utcnow() >= self.next_due_at

    @property
    def is_warning(self) -> bool:
        return not self.is_due and utcnow() >= self.warning_at

    def __repr__(self) -> str:
        return f"<MaintenanceRule {self.title!r}>"


class MaintenanceEvent(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "maintenance_events"

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("maintenance_rules.id", ondelete="CASCADE"), nullable=False
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    completed_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    notes: Mapped[str | None] = mapped_column(String(1000))

    rule = relationship("MaintenanceRule", back_populates="events")
    completed_by = relationship("User")
