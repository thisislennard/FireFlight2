from __future__ import annotations

import uuid

from app.core.exceptions import ValidationError
from app.extensions import db
from app.wizards.models import Wizard, WizardStep
from app.wizards.step_types import config_field_value_from_form, step_type_registry


def list_wizards(organization_id: uuid.UUID) -> list[Wizard]:
    return Wizard.query.filter_by(organization_id=organization_id).order_by(Wizard.name).all()


def create_wizard(organization_id: uuid.UUID, *, key: str, name: str, description: str | None = None) -> Wizard:
    if Wizard.query.filter_by(key=key).first() is not None:
        raise ValidationError("Dieser Schlüssel wird bereits von einem anderen Wizard verwendet.")
    wizard = Wizard(organization_id=organization_id, key=key, name=name, description=description)
    db.session.add(wizard)
    db.session.commit()
    return wizard


def update_wizard(wizard: Wizard, **fields) -> Wizard:
    for key, value in fields.items():
        setattr(wizard, key, value)
    db.session.commit()
    return wizard


def deactivate_wizard(wizard: Wizard) -> None:
    wizard.is_active = False
    db.session.commit()


def activate_wizard(wizard: Wizard) -> None:
    wizard.is_active = True
    db.session.commit()


def config_from_form(step_type: str, form) -> dict:
    """Baut WizardStep.config aus dem Step-Editor-Formular anhand der Feldbeschreibung des
    jeweiligen Step-Typs (app/wizards/step_types.py) -- unbekannte step_types werden von der Route
    bereits vorher abgewiesen (s. administration/routes.py)."""
    definition = step_type_registry.get(step_type)
    if definition is None:
        raise ValidationError("Unbekannter Step-Typ.")
    return {field.key: config_field_value_from_form(field, form) for field in definition.config_fields}


def add_step(wizard: Wizard, *, step_type: str, title: str, config: dict) -> WizardStep:
    if step_type_registry.get(step_type) is None:
        raise ValidationError("Unbekannter Step-Typ.")
    step = WizardStep(
        wizard_id=wizard.id, step_type=step_type, title=title, position=len(wizard.steps), config=config
    )
    db.session.add(step)
    db.session.commit()
    return step


def update_step(step: WizardStep, *, title: str, config: dict) -> WizardStep:
    step.title = title
    step.config = config
    db.session.commit()
    return step


def delete_step(step: WizardStep) -> None:
    db.session.delete(step)
    db.session.commit()


def move_step(step: WizardStep, direction: str) -> None:
    """Vertauscht die Position mit dem direkten Nachbarn in der aktuellen Sortierreihenfolge --
    arbeitet über die sortierte Nachbarliste statt über `position ± 1`, damit Lücken (nach
    Löschungen) die Reihenfolge nicht durcheinanderbringen."""
    siblings = sorted(step.wizard.steps, key=lambda s: s.position)
    index = siblings.index(step)
    neighbor_index = index - 1 if direction == "up" else index + 1
    if neighbor_index < 0 or neighbor_index >= len(siblings):
        return
    neighbor = siblings[neighbor_index]
    step.position, neighbor.position = neighbor.position, step.position
    db.session.commit()
