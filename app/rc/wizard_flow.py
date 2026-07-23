from __future__ import annotations

import uuid

from app.core.models import get_setting
from app.extensions import db
from app.wizards.models import Wizard


def get_preflight_wizard() -> Wizard | None:
    wizard_id = get_setting("rc_preflight_wizard_id")
    return db.session.get(Wizard, uuid.UUID(wizard_id)) if wizard_id else None


def get_flight_end_wizard() -> Wizard | None:
    wizard_id = get_setting("rc_flight_end_wizard_id")
    return db.session.get(Wizard, uuid.UUID(wizard_id)) if wizard_id else None


def collect_field_answers(runner) -> dict[str, object]:
    """Bildet die Antworten eines abgeschlossenen Wizard-Laufs generisch auf `field_key`-Werte ab
    (app/wizards/models.py: WizardStep.field_key) -- nur Schritte mit gesetztem field_key liefern
    hier einen Eintrag, alle anderen (z. B. eine reine Checkliste) schalten nur weiter, ohne dass
    ihre Antwort irgendwo landet. Bewusst hier statt in app/wizards/ -- die Engine selbst bleibt
    fachlich neutral, das Mapping auf Flight-/Incident-Felder ist Sache des RC-Verbrauchers."""
    answers_by_step_id = runner.state.get("answers", {})
    result: dict[str, object] = {}
    for step in runner.steps:
        if not step.field_key:
            continue
        answer = answers_by_step_id.get(str(step.id))
        if answer is not None:
            result[step.field_key] = answer
    return result
