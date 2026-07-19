from flask import has_request_context, request
from flask_login import current_user

from app.audit.models import AuditLog
from app.core.security.permissions import get_active_role
from app.extensions import db


def log_event(
    action: str,
    *,
    result: str = "success",
    object_type: str | None = None,
    object_id: str | None = None,
    extra_data: dict | None = None,
    user=None,
    organization_id=None,
) -> AuditLog:
    """Schreibt einen Audit-Log-Eintrag. Nie Passwörter/Tokens/Zugangsdaten in extra_data ablegen
    (spec-struktur.md Abschnitt 16)."""
    actor = user if user is not None else (current_user if current_user.is_authenticated else None)
    active_role = get_active_role() if has_request_context() else None

    entry = AuditLog(
        action=action,
        result=result,
        object_type=object_type,
        object_id=object_id,
        extra_data=extra_data,
        user_id=getattr(actor, "id", None),
        role_id=getattr(active_role, "id", None),
        organization_id=organization_id or getattr(actor, "organization_id", None),
        ip_address=request.remote_addr if has_request_context() else None,
    )
    db.session.add(entry)
    db.session.commit()
    return entry
