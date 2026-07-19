import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UUIDPrimaryKeyMixin:
    """Primärschlüssel als UUID — kollisionsfrei generierbar ohne Rückfrage an die DB (spec-struktur.md Abschnitt 14)."""

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class SystemSetting(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """Generischer Key-Value-Store für Systemeinstellungen (spec-struktur.md Abschnitt 14)."""

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


def get_setting(key: str, default=None):
    row = SystemSetting.query.filter_by(key=key).first()
    if row is None or not isinstance(row.value, dict):
        return default
    return row.value.get("value", default)


def set_setting(key: str, value) -> SystemSetting:
    row = SystemSetting.query.filter_by(key=key).first()
    if row is None:
        row = SystemSetting(key=key, value={"value": value})
        db.session.add(row)
    else:
        row.value = {"value": value}
    db.session.commit()
    return row
