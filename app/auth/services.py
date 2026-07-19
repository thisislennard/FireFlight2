from datetime import datetime, timedelta, timezone

from flask import current_app
from sqlalchemy import or_

from app.audit.service import log_event
from app.auth.models import User
from app.core.exceptions import ValidationError
from app.core.security.passwords import hash_password, verify_password
from app.extensions import db


class AccountLockedError(Exception):
    """Konto ist wegen zu vieler fehlgeschlagener Loginversuche vorübergehend gesperrt."""


def find_user_by_identifier(identifier: str) -> User | None:
    return User.query.filter(or_(User.username == identifier, User.email == identifier)).first()


def authenticate(identifier: str, password: str) -> User | None:
    """Login mit Benutzername oder E-Mail. Gibt bei falschem Passwort/unbekanntem Nutzer/
    deaktiviertem Konto bewusst dieselbe generische None-Antwort zurück (kein Informationsleck über
    Kontostatus). Bei Sperre wird separat AccountLockedError geworfen (eigene Nutzermeldung sinnvoll,
    da der Nutzer sein Passwort ja bereits korrekt eingegeben haben könnte)."""
    user = find_user_by_identifier(identifier)

    if user and user.locked_until and user.locked_until > datetime.now(timezone.utc):
        log_event("auth.login_failed", result="failure", user=user, extra_data={"reason": "locked"})
        raise AccountLockedError()

    if not user or not user.is_active_account or not verify_password(user.password_hash, password):
        if user:
            _register_failed_attempt(user)
        log_event("auth.login_failed", result="failure", extra_data={"identifier": identifier})
        return None

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()
    log_event("auth.login", result="success", user=user)
    return user


def _register_failed_attempt(user: User) -> None:
    max_attempts = current_app.config["LOGIN_MAX_FAILED_ATTEMPTS"]
    lockout_minutes = current_app.config["LOGIN_LOCKOUT_MINUTES"]
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= max_attempts:
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=lockout_minutes)
    db.session.commit()


def create_user(*, organization_id, username: str, email: str, password: str, display_name: str) -> User:
    user = User(
        organization_id=organization_id,
        username=username,
        email=email,
        password_hash=hash_password(password),
        display_name=display_name,
    )
    db.session.add(user)
    db.session.commit()
    return user


def list_users(organization_id):
    return User.query.filter_by(organization_id=organization_id).order_by(User.username).all()


def set_user_active(user: User, is_active: bool) -> None:
    if not is_active:
        from app.roles.services import ensure_not_last_administrator

        ensure_not_last_administrator(user)
    user.is_active_account = is_active
    db.session.commit()


def assign_roles(user: User, role_ids: list) -> None:
    from app.roles.models import Role
    from app.roles.services import ensure_not_last_administrator

    was_administrator = any(r.key == "administrator" for r in user.roles)
    will_be_administrator = any(str(rid) in {str(r.id) for r in Role.query.filter(
        Role.id.in_(role_ids), Role.key == "administrator"
    ).all()} for rid in role_ids)
    if was_administrator and not will_be_administrator:
        ensure_not_last_administrator(user)

    roles = Role.query.filter(Role.id.in_(role_ids)).all()
    user.roles = roles
    db.session.commit()


def request_password_reset(user: User) -> str:
    """Vorbereitete Passwort-zurücksetzen-Struktur (spec-struktur.md Abschnitt 6). Erzeugt aktuell
    nur ein Einmal-Token; der eigentliche Mail-Versand ist bewusst noch nicht angebunden (kein
    Mail-Server in Phase 1 gefordert) — siehe docs/architecture.md."""
    import secrets

    if not user.is_active_account:
        raise ValidationError("Deaktivierte Konten können ihr Passwort nicht zurücksetzen.")
    return secrets.token_urlsafe(32)
