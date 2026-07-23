from __future__ import annotations

import uuid

from app.extensions import db
from app.units.models import Unit


def create_unit(organization_id: uuid.UUID, *, name: str, description: str | None = None) -> Unit:
    unit = Unit(organization_id=organization_id, name=name, description=description)
    db.session.add(unit)
    db.session.commit()
    return unit


def update_unit(unit: Unit, **fields) -> Unit:
    for key, value in fields.items():
        setattr(unit, key, value)
    db.session.commit()
    return unit


def set_unit_managers(unit: Unit, user_ids: list) -> Unit:
    from app.auth.models import User

    unit.managers = User.query.filter(User.id.in_(user_ids)).all()
    db.session.commit()
    return unit


def deactivate_unit(unit: Unit) -> None:
    unit.is_active = False
    db.session.commit()


def activate_unit(unit: Unit) -> None:
    unit.is_active = True
    db.session.commit()


def list_units(organization_id: uuid.UUID) -> list[Unit]:
    return Unit.query.filter_by(organization_id=organization_id).order_by(Unit.name).all()


def unit_members(unit: Unit) -> list:
    from app.auth.models import User

    return User.query.filter_by(home_unit_id=unit.id).order_by(User.display_name).all()


def assign_home_unit(user, unit_id: uuid.UUID | None) -> None:
    user.home_unit_id = unit_id
    db.session.commit()
