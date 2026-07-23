from datetime import datetime, timedelta, timezone

from flask import current_app
from sqlalchemy import or_

from app.audit.service import log_event
from app.auth.models import User
from app.core.exceptions import ValidationError
from app.core.security.passwords import hash_pin, verify_pin
from app.extensions import db

# Eskalationsstufe verfällt nach 24h ohne neue Sperre, damit vereinzelte Tippfehler über Wochen
# hinweg nicht zur Dauersperre (Stufe 3) führen -- s. _register_failed_attempt().
LOCKOUT_STREAK_RESET = timedelta(hours=24)


class AccountLockedError(Exception):
    """Konto ist wegen zu vieler fehlgeschlagener Loginversuche gesperrt -- entweder vorübergehend
    (Ablauffrist) oder dauerhaft nach der 3. Eskalationsstufe (nur per Admin-Aktion aufhebbar)."""

    def __init__(self, requires_admin_unlock: bool = False):
        self.requires_admin_unlock = requires_admin_unlock
        super().__init__()


def find_user_by_identifier(identifier: str) -> User | None:
    return User.query.filter(or_(User.username == identifier, User.email == identifier)).first()


def _is_locked(user: User) -> bool:
    if user.requires_admin_unlock:
        return True
    return bool(user.locked_until and user.locked_until > datetime.now(timezone.utc))


def authenticate(identifier: str, pin: str) -> User | None:
    """Login mit Benutzername oder E-Mail + 4-stelliger PIN. Gibt bei falscher PIN/unbekanntem
    Nutzer/deaktiviertem Konto bewusst dieselbe generische None-Antwort zurück (kein Informationsleck
    über Kontostatus). Bei Sperre wird separat AccountLockedError geworfen (eigene Nutzermeldung
    sinnvoll, da der Nutzer seine PIN ja bereits korrekt eingegeben haben könnte)."""
    user = find_user_by_identifier(identifier)

    if user and _is_locked(user):
        log_event("auth.login_failed", result="failure", user=user, extra_data={"reason": "locked"})
        raise AccountLockedError(requires_admin_unlock=user.requires_admin_unlock)

    if not user or not user.is_active_account or not verify_pin(user.pin_hash, pin):
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
    """Progressive Sperr-Eskalation: bei nur 10.000 möglichen 4-stelligen PINs ist Lockout die
    einzige wirksame Verteidigung gegen Brute-Force. 1. Sperre kurz, 2. Sperre länger, ab der
    3. Sperre (innerhalb desselben 24h-Fensters) ist das Konto erst nach einem manuellen Admin-Reset
    wieder nutzbar statt nach einer Ablauffrist."""
    max_attempts = current_app.config["LOGIN_MAX_FAILED_ATTEMPTS"]
    user.failed_login_attempts += 1
    if user.failed_login_attempts < max_attempts:
        db.session.commit()
        return

    now = datetime.now(timezone.utc)
    if user.last_lockout_at and (now - user.last_lockout_at) > LOCKOUT_STREAK_RESET:
        user.lockout_count = 0
    user.lockout_count += 1
    user.last_lockout_at = now
    user.failed_login_attempts = 0

    stages = current_app.config["LOGIN_LOCKOUT_STAGES_MINUTES"]
    if user.lockout_count <= len(stages):
        user.locked_until = now + timedelta(minutes=stages[user.lockout_count - 1])
    else:
        user.locked_until = None
        user.requires_admin_unlock = True
    db.session.commit()


def create_user(*, organization_id, username: str, email: str, pin: str, display_name: str) -> User:
    user = User(
        organization_id=organization_id,
        username=username,
        email=email,
        pin_hash=hash_pin(pin),
        pin_set_at=datetime.now(timezone.utc),
        display_name=display_name,
    )
    db.session.add(user)
    db.session.commit()
    return user


def change_pin(user: User, *, current_pin: str, new_pin: str) -> None:
    """Self-Service-PIN-Wechsel -- verlangt die aktuelle PIN, unabhängig vom Formular auch hier
    geprüft, nicht nur in der UI (spec-struktur.md Abschnitt 9: serverseitige Prüfung ist Pflicht)."""
    if not verify_pin(user.pin_hash, current_pin):
        raise ValidationError("Aktuelle PIN ist falsch.")
    user.pin_hash = hash_pin(new_pin)
    user.must_change_pin = False
    user.pin_set_at = datetime.now(timezone.utc)
    db.session.commit()
    log_event("auth.pin_changed", result="success", user=user)


def unlock_account(user: User) -> None:
    """Admin-Aktion für die 3. Sperrstufe (`requires_admin_unlock`), die keine automatische
    Ablauffrist mehr hat -- ohne diese Aktion bliebe das Konto dauerhaft gesperrt."""
    user.failed_login_attempts = 0
    user.locked_until = None
    user.requires_admin_unlock = False
    user.lockout_count = 0
    db.session.commit()
    log_event("auth.account_unlocked", result="success", user=user)


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


def request_pin_reset(user: User) -> str:
    """Vorbereitete PIN-zurücksetzen-Struktur (spec-struktur.md Abschnitt 6, ursprünglich für
    Passwörter vorgesehen). Erzeugt aktuell nur ein Einmal-Token; der eigentliche Mail-Versand ist
    bewusst noch nicht angebunden (kein Mail-Server in Ausbaustufe 1 gefordert) — siehe
    docs/architecture.md."""
    import secrets

    if not user.is_active_account:
        raise ValidationError("Deaktivierte Konten können ihre PIN nicht zurücksetzen.")
    return secrets.token_urlsafe(32)
