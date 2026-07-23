import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models import TimestampMixin, UUIDPrimaryKeyMixin, utcnow
from app.extensions import db

user_roles = Table(
    "user_roles",
    db.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("assigned_at", DateTime(timezone=True), nullable=False, default=utcnow),
)

role_permissions = Table(
    "role_permissions",
    db.metadata,
    Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Permission(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """Zentral registrierte Berechtigungen (spec-struktur.md Abschnitt 9) — werden über
    app/roles/defaults.py geseedet, nicht hart im Code auf Rollennamen geprüft."""

    __tablename__ = "permissions"

    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    def __repr__(self) -> str:
        return f"<Permission {self.key!r}>"


class Role(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("organization_id", "key", name="uq_roles_org_key"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    icon: Mapped[str | None] = mapped_column(String(100))
    accent_color: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Ziel-Endpoint nach Rollenaktivierung (app/roles/routes.py:_resolve_role_landing). Default deckt
    # den bisherigen Fall (Dashboard) ab; Rollen ohne dashboard.view-Recht (z. B. künftig Gerätewart)
    # landen dann auf roles.no_landing statt einem rohen 403.
    landing_endpoint: Mapped[str] = mapped_column(String(150), nullable=False, default="dashboards.view")

    organization = relationship("Organization")
    permissions = relationship("Permission", secondary=role_permissions, backref="roles")
    users = relationship("User", secondary=user_roles, back_populates="roles")

    def __repr__(self) -> str:
        return f"<Role {self.key!r}>"
