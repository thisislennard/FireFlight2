from __future__ import annotations

import uuid

from app.core.exceptions import ValidationError
from app.extensions import db
from app.roles.defaults import DEFAULT_PERMISSIONS, DEFAULT_ROLES
from app.roles.models import Permission, Role


def seed_permissions() -> dict[str, Permission]:
    from app.modules.registry import module_registry

    existing = {p.key: p for p in Permission.query.all()}
    for key, description in DEFAULT_PERMISSIONS + module_registry.permissions:
        if key not in existing:
            perm = Permission(key=key, description=description)
            db.session.add(perm)
            existing[key] = perm
    db.session.commit()
    return existing


def seed_roles(organization_id: uuid.UUID) -> dict[str, Role]:
    """Idempotent: legt fehlende Standardrollen/-berechtigungen an, lässt bereits vorhandene
    (ggf. vom Administrator angepasste) Rollen unangetastet außer der Permission-Zuordnung, die bei
    erneutem Lauf wieder auf den Default gesetzt wird (bewusst — deckt sich mit `flask init-fireflight`s
    Idempotenz-Anforderung, s. spec-struktur.md Abschnitt 21)."""
    permissions = seed_permissions()
    existing = {r.key: r for r in Role.query.filter_by(organization_id=organization_id).all()}
    for entry in DEFAULT_ROLES:
        role = existing.get(entry["key"])
        if role is None:
            role = Role(
                organization_id=organization_id,
                key=entry["key"],
                name=entry["name"],
                icon=entry.get("icon"),
                sort_order=entry.get("sort_order", 0),
                is_system=entry.get("is_system", False),
            )
            db.session.add(role)
            existing[entry["key"]] = role
        role.permissions = [permissions[key] for key in entry["permissions"] if key in permissions]
    db.session.commit()
    return existing


def active_administrators(organization_id: uuid.UUID) -> list:
    admin_role = Role.query.filter_by(organization_id=organization_id, key="administrator").first()
    if admin_role is None:
        return []
    return [u for u in admin_role.users if u.is_active_account]


def ensure_not_last_administrator(user) -> None:
    """Schutz der Administratorrolle (spec-struktur.md Abschnitt 7): der letzte aktive Administrator
    darf weder entfernt noch deaktiviert werden."""
    is_administrator = any(r.key == "administrator" for r in user.roles)
    if not is_administrator:
        return
    remaining = [u for u in active_administrators(user.organization_id) if u.id != user.id]
    if not remaining:
        raise ValidationError("Der letzte Administrator kann nicht entfernt oder deaktiviert werden.")


def selectable_roles(user) -> list[Role]:
    return sorted((r for r in user.roles if r.is_active), key=lambda r: (r.sort_order, r.name))


def create_role(organization_id: uuid.UUID, *, key: str, name: str, description: str | None = None,
                 icon: str | None = None, accent_color: str | None = None) -> Role:
    role = Role(
        organization_id=organization_id, key=key, name=name,
        description=description, icon=icon, accent_color=accent_color,
    )
    db.session.add(role)
    db.session.commit()
    return role


def update_role(role: Role, **fields) -> Role:
    for key, value in fields.items():
        setattr(role, key, value)
    db.session.commit()
    return role


def set_role_permissions(role: Role, permission_keys: list[str]) -> Role:
    permissions = Permission.query.filter(Permission.key.in_(permission_keys)).all()
    role.permissions = permissions
    db.session.commit()
    return role


def deactivate_role(role: Role) -> None:
    if role.is_system:
        raise ValidationError("Systemrollen können nicht deaktiviert werden.")
    role.is_active = False
    db.session.commit()
