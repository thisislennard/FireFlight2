import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import UUIDPrimaryKeyMixin, utcnow
from app.extensions import db


class AuditLog(UUIDPrimaryKeyMixin, db.Model):
    """Unveränderliches Protokoll wichtiger Aktionen (spec-struktur.md Abschnitt 16). Bewusst ohne
    updated_at/TimestampMixin — ein Log-Eintrag wird nie nachträglich verändert."""

    __tablename__ = "audit_logs"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    role_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"))
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    object_type: Mapped[str | None] = mapped_column(String(100))
    object_id: Mapped[str | None] = mapped_column(String(100))
    result: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    ip_address: Mapped[str | None] = mapped_column(String(64))
    extra_data: Mapped[dict | None] = mapped_column(JSONB)

    def __repr__(self) -> str:
        return f"<AuditLog {self.action!r} {self.result!r}>"
