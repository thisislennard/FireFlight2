from functools import wraps

from flask import g, session
from flask_login import current_user

from app.core.exceptions import PermissionDenied


def get_active_role():
    """Liest die aktive Sitzungsrolle aus der Session und cached sie pro Request auf `g`."""
    if not hasattr(g, "_active_role"):
        role = None
        role_id = session.get("active_role_id")
        if current_user.is_authenticated and role_id:
            role = next(
                (r for r in current_user.roles if str(r.id) == str(role_id) and r.is_active),
                None,
            )
        g._active_role = role
    return g._active_role


def clear_active_role_cache() -> None:
    if hasattr(g, "_active_role"):
        del g._active_role


def role_has_permission(role, permission_key: str) -> bool:
    if role is None:
        return False
    if role.is_system:
        # Systemrollen (z. B. Administrator) sind bewusst nicht auf einzelne
        # Berechtigungen angewiesen — s. spec-struktur.md Abschnitt 7 (Schutz der Administratorrolle).
        return True
    return any(p.key == permission_key for p in role.permissions)


def ensure_permission(role, permission_key: str) -> None:
    """Serverseitige Berechtigungsprüfung — auch für den Einsatz in Services, nicht nur Routen."""
    if not role_has_permission(role, permission_key):
        raise PermissionDenied(permission_key)


def permission_required(permission_key: str):
    """Decorator für Routen. Wirft PermissionDenied (siehe app/__init__.py Errorhandler -> 403)."""

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            ensure_permission(get_active_role(), permission_key)
            return view(*args, **kwargs)

        return wrapped

    return decorator
