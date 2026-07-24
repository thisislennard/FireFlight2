from __future__ import annotations

from typing import TYPE_CHECKING

from app.modules.base import FireFlightModule

if TYPE_CHECKING:
    from flask import Flask

    from app.modules.registry import ModuleRegistry


class OpenSkyModule(FireFlightModule):
    """OpenSky-Luftraum-Dashboard-Widget (Restrukturierungsplan Phase 14, Konzeptdokument:
    "OpenSkyMap-Einbindung -- zur frühzeitigen Erkennung von Flugzeugen"). Wie das Wetter-Widget
    bewusst als "schlanke Direktanbindung" ohne eigene Integrationsschicht umgesetzt, s.
    app/modules/weather/module.py."""

    key = "opensky"
    name = "Luftraum (OpenSky)"
    version = "1.0.0"
    description = "Bemannte/unbemannte Luftfahrzeuge im Umkreis, über die freie OpenSky-API (anonym)."

    def register_widgets(self, registry: "ModuleRegistry") -> None:
        from app.dashboards.widgets import WidgetDefinition

        registry.add_widget(
            WidgetDefinition(
                key="opensky.map", label="Luftraum (OpenSky)", default_config={},
                template="modules/opensky/_widget_opensky_map.html",
            )
        )

    def register_template_globals(self, app: "Flask") -> None:
        from app.modules.opensky.widgets import nearby_aircraft_widget_data

        app.add_template_global(nearby_aircraft_widget_data, name="opensky_map_widget_data")
