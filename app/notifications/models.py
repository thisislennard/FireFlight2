import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.models import TimestampMixin, UUIDPrimaryKeyMixin, utcnow
from app.extensions import db


class PushSubscription(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """Eine Web-Push-Subscription pro Browser/Geräte-Kombination. `endpoint` (nicht `user_id`) ist
    der stabile Schlüssel -- auf der RC wechselt der Bediener, aber die Browser-Subscription bleibt
    gleich, daher wird bei jedem Subscribe per Upsert-auf-`endpoint` umgehängt statt eine zweite
    Zeile anzulegen (Restrukturierungsplan Abschnitt 4)."""

    __tablename__ = "push_subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    endpoint: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    p256dh: Mapped[str] = mapped_column(String(255), nullable=False)
    auth: Mapped[str] = mapped_column(String(255), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(500))
    # Wird bei 404/410-Antwort des Push-Diensts automatisch deaktiviert (app/notifications/service.py)
    # statt die Zeile zu löschen -- erhält den Verlauf für NotificationLog.subscription_id.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User")

    def __repr__(self) -> str:
        return f"<PushSubscription {self.endpoint[:40]!r}>"


class NotificationLog(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """Protokoll aller Zustellversuche (spec-struktur.md-Muster wie AuditLog), je Empfänger-Subscription
    ein Eintrag -- damit Flugleiter-/Wartungs-Push in späteren Fachmodulen nachvollziehbar bleibt."""

    __tablename__ = "notification_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("push_subscriptions.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(String(500), nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="sent")
    error_message: Mapped[str | None] = mapped_column(String(1000))

    user = relationship("User")
    subscription = relationship("PushSubscription")

    def __repr__(self) -> str:
        return f"<NotificationLog {self.title!r} {self.status!r}>"
