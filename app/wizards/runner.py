from __future__ import annotations

import uuid

from app.wizards.models import Wizard, WizardStep
from app.wizards.step_types import step_type_registry


def session_key(wizard_id: uuid.UUID) -> str:
    return f"wizard_preview_{wizard_id}"


class WizardRunner:
    """Generischer Laufzeit-Motor: gegeben ein Wizard + ein mutable Zustands-Dict (aktuell die
    Flask-Session, s. app/administration/routes.py: wizard_preview()), schaltet nur weiter, wenn der
    Step-Typ die eingereichte Antwort als vollständig validiert (Konzeptdokument Abschnitt 5.6:
    "Weiterkommen erst möglich, wenn bestimmte Aktionen ausgeführt wurden"). Aktuell einziger
    Konsument ist die Admin-Vorschau (Phase 8) -- ein echter RC-Lauf mit Persistenz in ein Flugbuch
    ist Phase 9/12-Umfang und wird diese Klasse voraussichtlich mit einem anderen Zustands-Backend
    als der Session wiederverwenden, die Schritt-Validierungslogik bleibt dieselbe."""

    def __init__(self, wizard: Wizard, state: dict):
        self.wizard = wizard
        self.state = state
        self.steps: list[WizardStep] = [s for s in wizard.steps if s.is_active]

    @property
    def current_index(self) -> int:
        return self.state.get("step_index", 0)

    @property
    def current_step(self) -> WizardStep | None:
        if 0 <= self.current_index < len(self.steps):
            return self.steps[self.current_index]
        return None

    @property
    def is_finished(self) -> bool:
        return len(self.steps) > 0 and self.current_index >= len(self.steps)

    @property
    def progress(self) -> tuple[int, int]:
        return (min(self.current_index, len(self.steps)), len(self.steps))

    def submit(self, form) -> bool:
        step = self.current_step
        if step is None:
            return False
        definition = step_type_registry.get(step.step_type)
        if definition is None:
            return False
        answer = definition.parse_answer(form, step.config)
        if not definition.validate(step.config, answer):
            return False
        self.state.setdefault("answers", {})[str(step.id)] = answer
        self.state["step_index"] = self.current_index + 1
        return True

    def back(self) -> None:
        self.state["step_index"] = max(0, self.current_index - 1)

    def reset(self) -> None:
        self.state["step_index"] = 0
        self.state["answers"] = {}
