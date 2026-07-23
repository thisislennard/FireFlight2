import uuid
from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models import TimestampMixin, UUIDPrimaryKeyMixin
from app.extensions import db


class User(UUIDPrimaryKeyMixin, TimestampMixin, UserMixin, db.Model):
    __tablename__ = "users"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    username: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    pin_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Erzwingt PIN-Wechsel nach Admin-Anlage/-Reset, bevor der Account regulär nutzbar ist (noch nicht
    # in Routen durchgesetzt -- Feld ist vorbereitet, Erzwingung folgt mit der Admin-Anlage-UI).
    must_change_pin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pin_set_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active_account: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Progressive Sperr-Eskalation (app/auth/services.py:_register_failed_attempt) -- bei nur 10.000
    # möglichen 4-stelligen PINs ist Lockout die einzige wirksame Verteidigung gegen Brute-Force.
    lockout_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_lockout_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requires_admin_unlock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_used_role_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"))

    organization = relationship("Organization")
    roles = relationship("Role", secondary="user_roles", back_populates="users")
    last_used_role = relationship("Role", foreign_keys=[last_used_role_id])

    def get_id(self) -> str:
        return str(self.id)

    @property
    def is_active(self) -> bool:
        # Überschreibt UserMixin.is_active — Flask-Login verweigert damit deaktivierten Konten
        # automatisch die Session (s. spec-struktur.md Abschnitt 6 "deaktivierbare Benutzerkonten").
        return self.is_active_account

    def __repr__(self) -> str:
        return f"<User {self.username!r}>"
