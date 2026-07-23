import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models import TimestampMixin, UUIDPrimaryKeyMixin
from app.extensions import db


class RcDevice(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """Physische DJI-RC-Plus-Fernbedienung. Einmalig vom Administrator angelegt (dabei wird der
    Geräteschlüssel im Klartext EINMALIG angezeigt), danach auf dem Gerät über `/rc/pair` gekoppelt.

    Bewusste Vereinfachung für den Hardware-Feasibility-Spike (Restrukturierungsplan Phase 5): der
    Geräteschlüssel ist zugleich der langlebige Cookie-Wert (`rc_device_token`) -- kein separates,
    rotierbares Session-Token. Das deckt sich mit den im Plan für `RcDevice` genannten drei Feldern
    (label, device_key_hash, required_qualification). Bei Kompromittierung hilft nur
    `regenerate_device_key()` (app/rc/services.py), das Gerät muss danach neu gekoppelt werden."""

    __tablename__ = "rc_devices"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(150), nullable=False)
    device_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # "pilot" / "camera_operator" -- validierter String wie AuditLog.result, kein natives Enum.
    # In Phase 5 noch ungenutzt (Qualifikationsfilter kommt erst mit Phase 7/Profiles, s. Roadmap).
    required_qualification: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    paired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    organization = relationship("Organization")

    def __repr__(self) -> str:
        return f"<RcDevice {self.label!r}>"
