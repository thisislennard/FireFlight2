from __future__ import annotations

from typing import TYPE_CHECKING

from app.modules.base import FireFlightModule
from app.modules.registry import NavigationEntry

if TYPE_CHECKING:
    from flask import Flask

    from app.modules.registry import ModuleRegistry


class IncidentsModule(FireFlightModule):
    """Einsatz-/Übungsverwaltung + Flugbuch (Restrukturierungsplan Phase 9). Erstes Fachmodul, das
    tatsächlich über das in Phase 1 gebaute Modul-Registry-System (app/modules/) andockt -- dabei
    wurden zwei latente Bugs in der bis dahin nie mit einem echten Modul durchgespielten
    Navigation-Rendering-Logik gefunden und behoben, s. app/templates/base.html."""

    key = "incidents"
    name = "Einsätze & Flugbuch"
    version = "1.0.0"
    description = "Einsatz-/Übungsverwaltung und Flugbuch."

    def register_blueprints(self, app: "Flask") -> None:
        from app.modules.incidents.routes import bp

        app.register_blueprint(bp)

    def register_permissions(self, registry: "ModuleRegistry") -> None:
        registry.add_permission("incidents.view", "Einsätze/Flugbuch ansehen")
        registry.add_permission("incidents.edit", "Einsätze/Flüge anlegen/bearbeiten")
        # Phase 12: Startanfragen genehmigen (Konzeptdokument Abschnitt 5.3) -- bewusst getrennt von
        # incidents.edit, da das breit vergeben ist (jede Crew darf Flüge anlegen/bearbeiten), die
        # Freigabe eines Flugstarts aber eine engere Führungsentscheidung ist.
        registry.add_permission("incidents.approve_flights", "Startanfragen für Flüge genehmigen")

    def register_navigation(self, registry: "ModuleRegistry") -> None:
        registry.add_navigation(
            NavigationEntry(
                label="Flugbuch", endpoint="incidents.list_incidents", icon="book-open", permission="incidents.view"
            )
        )
        registry.add_navigation(
            NavigationEntry(
                label="Startanfragen", endpoint="incidents.pending_approvals", icon="check-circle",
                permission="incidents.approve_flights",
            )
        )

    def register_widgets(self, registry: "ModuleRegistry") -> None:
        from app.dashboards.widgets import WidgetDefinition

        # Erstes fachliches Dashboard-Widget (Restrukturierungsplan Phase 13, Konzeptdokument
        # Abschnitt 9: "Karte -- aktuelle Standorte der Piloten"). Zeigt die neuesten Flüge mit
        # erfasstem Standort kompakt im Dashboard, mit Link zur vollen Kartenseite (Phase 9).
        registry.add_widget(
            WidgetDefinition(
                key="incidents.flight_map", label="Flugbuch-Karte", default_config={"limit": 10},
                template="modules/incidents/_widget_flight_map.html",
            )
        )

    def register_template_globals(self, app: "Flask") -> None:
        from app.modules.incidents.widgets import flight_map_widget_data

        app.add_template_global(flight_map_widget_data, name="incidents_flight_map_widget_data")
