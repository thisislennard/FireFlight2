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

    def register_navigation(self, registry: "ModuleRegistry") -> None:
        registry.add_navigation(
            NavigationEntry(
                label="Flugbuch", endpoint="incidents.list_incidents", icon="book-open", permission="incidents.view"
            )
        )
