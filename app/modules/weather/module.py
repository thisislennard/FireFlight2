from __future__ import annotations

from typing import TYPE_CHECKING

from app.modules.base import FireFlightModule

if TYPE_CHECKING:
    from flask import Flask

    from app.modules.registry import ModuleRegistry


class WeatherModule(FireFlightModule):
    """DWD-Wetter-Dashboard-Widget (Restrukturierungsplan Phase 14, Konzeptdokument: "Wetterdaten
    vom DWD -- relevant für Drohnenbetrieb"). Bewusst "schlanke Direktanbindung" statt eigener
    Integrationsschicht mit Mock-/Live-Client wie einst bei DJI FlightHub -- kein eigenes
    `app/integrations/`-Package, keine Admin-Konfiguration, keine Sync-Jobs (Nutzerentscheidung,
    s. docs/roadmap.md Phase 14)."""

    key = "weather"
    name = "Wetter (DWD)"
    version = "1.0.0"
    description = "Aktuelle DWD-Wetterdaten für den Standort, über die freie Bright-Sky-API."

    def register_widgets(self, registry: "ModuleRegistry") -> None:
        from app.dashboards.widgets import WidgetDefinition

        registry.add_widget(
            WidgetDefinition(
                key="weather.current", label="Wetter (DWD)", default_config={},
                template="modules/weather/_widget_weather.html",
            )
        )

    def register_template_globals(self, app: "Flask") -> None:
        from app.modules.weather.widgets import current_weather_widget_data

        app.add_template_global(current_weather_widget_data, name="weather_current_widget_data")
