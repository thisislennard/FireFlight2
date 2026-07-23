import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models import TimestampMixin, UUIDPrimaryKeyMixin
from app.extensions import db


class Wizard(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """Admin-konfigurierbare Schrittfolge (Restrukturierungsplan Phase 8 -- Konzeptdokument
    Abschnitt 5.6: "Einzelne Wizard-Seiten sind frei konfigurierbar [...] Admin kann den Wizard am
    Desktop konfigurieren, inkl. Vorschau"). Bewusst nur die generische Engine: die konkreten
    Preflight-/Flugstart-/Flugende-Inhalte aus Abschnitt 5.2-5.5 sind Umfang von Phase 12
    (RC-Wizard-Inhalte), sobald Phase 9 (Einsatz/Übung) und Phase 11 (RC-PWA-Vollausbau) existieren,
    an die ein Wizard-Lauf andocken kann."""

    __tablename__ = "wizards"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    organization = relationship("Organization")
    steps = relationship(
        "WizardStep", back_populates="wizard", order_by="WizardStep.position", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Wizard {self.key!r}>"


class WizardStep(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "wizard_steps"

    wizard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wizards.id", ondelete="CASCADE"), nullable=False
    )
    # Schlüssel aus app/wizards/step_types.py: step_type_registry -- validierter String wie
    # RcDevice.required_qualification, kein natives Enum (s. dortige Begründung).
    step_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Schema abhängig vom step_type (z. B. {"items": [...]} bei "checklist"), s. step_types.py:
    # WizardStepTypeDefinition.config_fields -- analog zu DashboardWidget.config.
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    wizard = relationship("Wizard", back_populates="steps")

    def __repr__(self) -> str:
        return f"<WizardStep {self.title!r}>"
