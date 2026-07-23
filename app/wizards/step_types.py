from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ConfigField:
    """Beschreibt ein einzelnes Config-Feld eines Step-Typs fürs Admin-Editor-Formular (welches
    Eingabeelement, welche Beschriftung) -- die eigentlichen Werte liegen in WizardStep.config."""

    key: str
    label: str
    kind: str  # "text" | "textarea" | "lines" (mehrzeilig -> Liste) | "bool"


@dataclass(frozen=True)
class WizardStepTypeDefinition:
    key: str
    label: str
    default_config: dict
    config_fields: tuple[ConfigField, ...]
    # Liest die Nutzer-Antwort eines Laufs aus dem eingereichten Formular (app/wizards/runner.py).
    parse_answer: Callable[..., object]
    # Prüft, ob die Antwort das "Weiterkommen erst möglich, wenn bestimmte Aktionen ausgeführt
    # wurden"-Kriterium erfüllt (Konzeptdokument Abschnitt 5.6).
    validate: Callable[[dict, object], bool]


class WizardStepTypeRegistry:
    def __init__(self) -> None:
        self._types: dict[str, WizardStepTypeDefinition] = {}

    def register(self, definition: WizardStepTypeDefinition) -> None:
        self._types[definition.key] = definition

    def get(self, key: str) -> WizardStepTypeDefinition | None:
        return self._types.get(key)

    def all(self) -> list[WizardStepTypeDefinition]:
        return sorted(self._types.values(), key=lambda t: t.label)


step_type_registry = WizardStepTypeRegistry()


def parse_lines(text: str) -> list[str]:
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def config_field_value_from_form(field: ConfigField, form) -> object:
    """Liest den Wert eines einzelnen Config-Felds aus dem Step-Editor-Formular (Admin pflegt
    WizardStep.config) -- Gegenstück zu WizardStepTypeDefinition.parse_answer, das die Antwort
    eines Nutzer-*Laufs* liest, nicht die Konfiguration selbst."""
    if field.kind == "lines":
        return parse_lines(form.get(field.key, ""))
    if field.kind == "bool":
        return field.key in form
    return form.get(field.key, "")


# --- info: reiner Anzeigetext, immer sofort weiterschaltbar --------------------------------------

step_type_registry.register(
    WizardStepTypeDefinition(
        key="info",
        label="Informationstext",
        default_config={"body": ""},
        config_fields=(ConfigField("body", "Text", "textarea"),),
        parse_answer=lambda form, config: None,
        validate=lambda config, answer: True,
    )
)


# --- checklist: mehrere Punkte, alle müssen abgehakt sein ---------------------------------------


def _parse_checklist_answer(form, config):
    return sorted({int(v) for v in form.getlist("answer_items") if v.isdigit()})


def _validate_checklist(config, answer):
    items = config.get("items") or []
    if not items:
        return True
    return set(answer or []) == set(range(len(items)))


step_type_registry.register(
    WizardStepTypeDefinition(
        key="checklist",
        label="Checkliste",
        default_config={"items": []},
        config_fields=(ConfigField("items", "Punkte (eine Zeile je Punkt)", "lines"),),
        parse_answer=_parse_checklist_answer,
        validate=_validate_checklist,
    )
)


# --- confirmation: eine einzelne Bestätigungs-Checkbox -------------------------------------------

step_type_registry.register(
    WizardStepTypeDefinition(
        key="confirmation",
        label="Bestätigung",
        default_config={"label": "Ich bestätige."},
        config_fields=(ConfigField("label", "Text der Bestätigung", "text"),),
        parse_answer=lambda form, config: form.get("answer") == "on",
        validate=lambda config, answer: answer is True,
    )
)


# --- text_input: Freitextfeld, optional Pflicht ---------------------------------------------------

step_type_registry.register(
    WizardStepTypeDefinition(
        key="text_input",
        label="Freitext",
        default_config={"label": "", "required": True},
        config_fields=(
            ConfigField("label", "Feldbeschriftung", "text"),
            ConfigField("required", "Pflichtfeld", "bool"),
        ),
        parse_answer=lambda form, config: (form.get("answer") or "").strip(),
        validate=lambda config, answer: (not config.get("required", True)) or bool(answer),
    )
)


# --- choice: eine Option aus einer festen Liste ----------------------------------------------------

step_type_registry.register(
    WizardStepTypeDefinition(
        key="choice",
        label="Auswahl",
        default_config={"label": "", "options": []},
        config_fields=(
            ConfigField("label", "Frage", "text"),
            ConfigField("options", "Optionen (eine Zeile je Option)", "lines"),
        ),
        parse_answer=lambda form, config: form.get("answer") or "",
        validate=lambda config, answer: answer in (config.get("options") or []),
    )
)
