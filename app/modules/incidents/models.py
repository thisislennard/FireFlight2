import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models import TimestampMixin, UUIDPrimaryKeyMixin
from app.extensions import db

KIND_EINSATZ = "einsatz"
KIND_UEBUNG = "uebung"
INCIDENT_KINDS = (KIND_EINSATZ, KIND_UEBUNG)

# Nur für den RC-gesteuerten Live-Ablauf relevant (Phase 12, app/rc/wizard_flow.py) -- über Desktop
# manuell angelegte/nachgetragene Flüge (Phase 9) lassen `flight_status` bewusst NULL, sie sind
# fertige historische Einträge ohne Live-Workflow. draft: Preflight-Wizard abgeschlossen, Flug
# angelegt. pending_approval: "Flug starten" gedrückt, wartet auf Freigabe (Konzeptdokument
# Abschnitt 5.3: "Startanfrage [...] die über die Desktop-Version genehmigt werden muss"). approved:
# freigegeben, "Zu DJI Pilot 2"-Button erscheint. completed: Flugende-Wizard abgeschlossen.
FLIGHT_STATUS_DRAFT = "draft"
FLIGHT_STATUS_PENDING_APPROVAL = "pending_approval"
FLIGHT_STATUS_APPROVED = "approved"
FLIGHT_STATUS_COMPLETED = "completed"
FLIGHT_STATUSES = (FLIGHT_STATUS_DRAFT, FLIGHT_STATUS_PENDING_APPROVAL, FLIGHT_STATUS_APPROVED, FLIGHT_STATUS_COMPLETED)


class Incident(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """Einsatz oder Übung (Konzeptdokument Abschnitt 6) -- kann mehrere Flüge umfassen. Erstes
    echtes Fachmodul über das Modul-Registry-System aus Phase 1 (app/modules/), Restrukturierungsplan
    Phase 9. Bewusst kein Bezug zu einer Drohneneinheit (Unit) -- im Konzept nicht gefordert, mehrere
    Einheiten können sich laut Abschnitt 6 in denselben laufenden Einsatz einbuchen."""

    __tablename__ = "incidents"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # "einsatz" | "uebung"
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    organization = relationship("Organization")
    flights = relationship(
        "Flight", back_populates="incident", order_by="Flight.started_at", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Incident {self.title!r}>"


class Flight(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """Flugbuch-Eintrag (Konzeptdokument Abschnitt 5.2-5.5 + 7). Felder orientieren sich an dem, was
    laut Konzept am RC Plus während des Preflight/Flugstart/Flugende-Wizards erfasst wird (Einsatz/
    Übung-Zuordnung, Zweck, Start-/End-Standort+Zeit, Abschlussfragen) -- der Wizard selbst kommt erst
    mit Phase 12, dieser Datensatz ist aber schon jetzt sowohl manuell über Desktop als auch später vom
    RC-Wizard befüllbar (Nutzerentscheidung). `drone_label`/`battery_label` bewusst Freitext statt
    Fremdschlüssel auf ein Geräte-Modell -- ein solches Modul existiert im 15-Phasen-Plan (noch) nicht,
    Freitext ist migrierbar, sobald es eines gibt."""

    __tablename__ = "flights"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    pilot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    camera_operator_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    drone_label: Mapped[str | None] = mapped_column(String(150))
    battery_label: Mapped[str | None] = mapped_column(String(150))
    purpose: Mapped[str | None] = mapped_column(String(1000))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    start_lat: Mapped[float | None] = mapped_column(Float)
    start_lon: Mapped[float | None] = mapped_column(Float)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_lat: Mapped[float | None] = mapped_column(Float)
    end_lon: Mapped[float | None] = mapped_column(Float)
    # Abschlussfragen aus Konzeptdokument Abschnitt 5.5 ("Flüge synchronisiert?", "Gab es Mängel?").
    synced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    had_issues: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(String(2000))

    # Startanfrage-Genehmigungsworkflow (Phase 12, Konzeptdokument Abschnitt 5.3) -- nur bei
    # RC-gesteuerten Flügen gesetzt, s. FLIGHT_STATUSES oben.
    flight_status: Mapped[str | None] = mapped_column(String(20))
    start_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    start_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    start_approved_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    incident = relationship("Incident", back_populates="flights")
    pilot = relationship("User", foreign_keys=[pilot_id])
    camera_operator = relationship("User", foreign_keys=[camera_operator_id])
    start_approved_by = relationship("User", foreign_keys=[start_approved_by_id])

    def __repr__(self) -> str:
        return f"<Flight {self.id}>"
