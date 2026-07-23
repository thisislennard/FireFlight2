from dataclasses import dataclass


@dataclass(frozen=True)
class WidgetDefinition:
    key: str
    label: str
    default_config: dict
    # Optionaler Pfad zu einem eigenen Render-Partial (relativ zu app/templates/), das im
    # Fallback-Zweig von dashboards/_widget.html eingebunden wird -- der Andockpunkt, ueber den
    # Fachmodule eigene Widgets rendern koennen, ohne diese zentrale Datei anzufassen.
    template: str | None = None


class WidgetRegistry:
    """Registry der verfügbaren Dashboard-Widget-Typen (spec-struktur.md Abschnitt 10). Spätere
    Fachmodule können hierüber eigene Widgets registrieren (Abschnitt 11)."""

    def __init__(self) -> None:
        self._widgets: dict[str, WidgetDefinition] = {}

    def register(self, definition: WidgetDefinition) -> None:
        self._widgets[definition.key] = definition

    def get(self, key: str) -> WidgetDefinition | None:
        return self._widgets.get(key)

    def all(self) -> list[WidgetDefinition]:
        return sorted(self._widgets.values(), key=lambda w: w.label)


widget_registry = WidgetRegistry()

_BASE_WIDGETS = [
    WidgetDefinition("heading", "Überschrift", {"text": "Überschrift"}),
    WidgetDefinition("info_text", "Informationstext", {"text": ""}),
    WidgetDefinition("quick_link", "Schnellzugriff", {"label": "", "url": ""}),
    WidgetDefinition("status", "Statusanzeige", {"label": "", "state": "neutral"}),
    WidgetDefinition("metric", "Kennzahl", {"label": "", "value": ""}),
    WidgetDefinition("notice", "Hinweis", {"text": ""}),
    WidgetDefinition("warning", "Warnung", {"text": ""}),
    WidgetDefinition("placeholder", "Platzhalter", {}),
]

for _definition in _BASE_WIDGETS:
    widget_registry.register(_definition)
