import uuid
from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models import TimestampMixin, UUIDPrimaryKeyMixin
from app.extensions import db

# Einzige Quelle der Wahrheit für die beiden Funktionen aus dem Konzeptdokument (Abschnitt 5.1) --
# app/rc/services.py validiert RcDevice.required_qualification dagegen (Phase 7: der Filter wird
# erst hier scharf geschaltet, s. app/rc/routes.py: login()).
QUALIFICATION_PILOT = "pilot"
QUALIFICATION_CAMERA_OPERATOR = "camera_operator"
QUALIFICATIONS = (QUALIFICATION_PILOT, QUALIFICATION_CAMERA_OPERATOR)


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
    # Zugehörigkeit zu genau einer "Heimat"-Drohneneinheit (app/units/) -- Grundlage für Phase 7
    # (Profile) und Phase 9 (Einsatz/Übung). Ein User kann zusätzlich mehrere Einheiten *managen*
    # (managed_units), unabhängig von seiner eigenen Zugehörigkeit.
    home_unit_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("units.id"))
    # "Funktion" aus dem Konzeptdokument (Abschnitt 5.1/8) -- bewusst zwei Booleans statt einer
    # m:n-Tabelle wie unit_managers: es gibt nur diese zwei fest benannten Werte, ein User kann laut
    # Konzept BEIDE gleichzeitig haben (nicht exklusiv wie eine Rolle). Admin-verwaltet
    # (administration/users/<id>), nicht Self-Service -- steuert den RC-Gerätezugang (app/rc/).
    is_pilot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_camera_operator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Self-Service-Profildaten (Phase 7, Konzeptdokument Abschnitt 8) -- im Unterschied zu den
    # Admin-verwalteten Feldern oben über app/profile/ vom User selbst änderbar.
    phone_number: Mapped[str | None] = mapped_column(String(50))
    # Nur der generierte Dateiname (z. B. "<user_id>.jpg"), nie ein clientseitig gelieferter Pfad --
    # verhindert Path Traversal beim Servieren (app/profile/routes.py). Tatsächliche Datei liegt unter
    # app/core/utilities/uploads.py: profile_image_dir().
    profile_image_filename: Mapped[str | None] = mapped_column(String(255))

    organization = relationship("Organization")
    roles = relationship("Role", secondary="user_roles", back_populates="users")
    last_used_role = relationship("Role", foreign_keys=[last_used_role_id])
    home_unit = relationship("Unit", foreign_keys=[home_unit_id])
    managed_units = relationship("Unit", secondary="unit_managers", back_populates="managers")

    def get_id(self) -> str:
        return str(self.id)

    @property
    def qualifications(self) -> list[str]:
        quals = []
        if self.is_pilot:
            quals.append(QUALIFICATION_PILOT)
        if self.is_camera_operator:
            quals.append(QUALIFICATION_CAMERA_OPERATOR)
        return quals

    def has_qualification(self, key: str | None) -> bool:
        """`key=None` steht für "kein Filter" (RcDevice.required_qualification unset) -- gilt immer
        als erfüllt, s. app/rc/routes.py: login()."""
        if not key:
            return True
        return key in self.qualifications

    @property
    def is_active(self) -> bool:
        # Überschreibt UserMixin.is_active — Flask-Login verweigert damit deaktivierten Konten
        # automatisch die Session (s. spec-struktur.md Abschnitt 6 "deaktivierbare Benutzerkonten").
        return self.is_active_account

    def __repr__(self) -> str:
        return f"<User {self.username!r}>"
