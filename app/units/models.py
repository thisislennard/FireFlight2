import uuid

from sqlalchemy import Boolean, Column, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models import TimestampMixin, UUIDPrimaryKeyMixin
from app.extensions import db

unit_managers = Table(
    "unit_managers",
    db.metadata,
    Column("unit_id", UUID(as_uuid=True), ForeignKey("units.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


class Unit(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """Drohneneinheit -- neue Entität zwischen Organisation und User (Restrukturierungsplan
    Abschnitt 4). Eigenes Package statt Erweiterung von app/organizations/, weil Organization laut
    docs/architecture.md bewusst ein Single-Tenant-Platzhalter bleiben soll. Voraussetzung für
    Nutzerprofile (Phase 7) und Einsatz/Übung (Phase 9)."""

    __tablename__ = "units"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    organization = relationship("Organization")
    managers = relationship("User", secondary=unit_managers, back_populates="managed_units")

    def __repr__(self) -> str:
        return f"<Unit {self.name!r}>"
