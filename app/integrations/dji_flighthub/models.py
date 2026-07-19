import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models import TimestampMixin, UUIDPrimaryKeyMixin, utcnow
from app.extensions import db


class IntegrationConfig(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """Nicht-geheime Einstellungen einer Integration. Zugangsdaten kommen ausschließlich aus
    Umgebungsvariablen (spec-struktur.md Abschnitt 4) — diese Tabelle speichert keine Secrets."""

    __tablename__ = "integration_configs"
    __table_args__ = (
        UniqueConstraint("organization_id", "integration_key", name="uq_integration_configs_org_key"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    integration_key: Mapped[str] = mapped_column(String(100), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    settings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    sync_runs = relationship(
        "IntegrationSyncRun",
        back_populates="integration_config",
        order_by="IntegrationSyncRun.started_at.desc()",
    )


class IntegrationSyncRun(UUIDPrimaryKeyMixin, db.Model):
    __tablename__ = "integration_sync_runs"

    integration_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("integration_configs.id", ondelete="CASCADE"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    records_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(String(1000))
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    integration_config = relationship("IntegrationConfig", back_populates="sync_runs")


class ExternalReference(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """Generische Zuordnung externer Datensätze zu internen Objekten (spec-struktur.md Abschnitt 15) —
    verhindert, dass künftige Fachmodelle mit DJI-spezifischen Feldern überladen werden."""

    __tablename__ = "external_references"
    __table_args__ = (
        UniqueConstraint("organization_id", "source", "external_id", name="uq_external_references_source_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String(200), nullable=False)
    internal_object_type: Mapped[str] = mapped_column(String(100), nullable=False)
    internal_object_id: Mapped[str | None] = mapped_column(String(100))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_imported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sync_error: Mapped[str | None] = mapped_column(String(1000))
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)
