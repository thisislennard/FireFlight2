from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import TimestampMixin, UUIDPrimaryKeyMixin
from app.extensions import db


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """Existiert schon jetzt als eigenes DB-Objekt, obwohl es in dieser Ausbaustufe nur eine
    Organisation gibt — vorbereitet für spätere Mandantenfähigkeit (spec-struktur.md Abschnitt 5)."""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(50))
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="Europe/Berlin")
    logo_path: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<Organization {self.name!r}>"
