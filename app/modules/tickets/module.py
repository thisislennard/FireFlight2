from __future__ import annotations

from typing import TYPE_CHECKING

from app.modules.base import FireFlightModule
from app.modules.registry import NavigationEntry

if TYPE_CHECKING:
    from flask import Flask

    from app.modules.registry import ModuleRegistry


class TicketsModule(FireFlightModule):
    """Technische Probleme (Tickets) + Wartungsintervalle (Restrukturierungsplan Phase 10,
    Konzeptdokument Abschnitt 9/10). Zweites Fachmodul über das Modul-Registry-System (nach
    app/modules/incidents/ in Phase 9). Ticket-Erstellung ist bewusst breit zugänglich (jede Crew
    meldet Probleme), Verwaltung/Wartung ist Gerätewart-Domäne -- s. app/roles/defaults.py, wo die
    Gerätewart-Rolle als erste tatsächlich `landing_endpoint` nutzt statt des Dashboard-Defaults
    (Konzeptdokument Abschnitt 10: "Rollen ohne Dashboard", Infrastruktur seit Phase 2 vorbereitet)."""

    key = "tickets"
    name = "Tickets & Wartung"
    version = "1.0.0"
    description = "Technische Probleme und Wartungsintervalle."

    def register_blueprints(self, app: "Flask") -> None:
        from app.modules.tickets.routes import bp

        app.register_blueprint(bp)

    def register_permissions(self, registry: "ModuleRegistry") -> None:
        registry.add_permission("tickets.view", "Tickets ansehen")
        registry.add_permission("tickets.create", "Tickets erstellen, kommentieren, Anhänge hochladen")
        registry.add_permission("tickets.manage", "Tickets verwalten (Status, löschen)")
        registry.add_permission("maintenance.view", "Wartungsplan ansehen")
        registry.add_permission("maintenance.manage", "Wartungsregeln anlegen/bearbeiten, als erledigt melden")

    def register_navigation(self, registry: "ModuleRegistry") -> None:
        registry.add_navigation(
            NavigationEntry(label="Tickets", endpoint="tickets.list_tickets", icon="alert-circle",
                             permission="tickets.view")
        )
        registry.add_navigation(
            NavigationEntry(label="Wartung", endpoint="tickets.list_maintenance", icon="wrench",
                             permission="maintenance.view")
        )

    def register_widgets(self, registry: "ModuleRegistry") -> None:
        from app.dashboards.widgets import WidgetDefinition

        # Zweites fachliches Dashboard-Widget (Restrukturierungsplan Phase 13, Konzeptdokument
        # Abschnitt 9: "Technisches Problem -- Ticket erstellen, inkl. Foto-Möglichkeit"). Läuft
        # direkt im Dashboard statt über die eigene Ticket-Erstellungsseite, s. tickets.widget_report.
        registry.add_widget(
            WidgetDefinition(
                key="tickets.report_form", label="Technisches Problem melden", default_config={},
                template="modules/tickets/_widget_report_form.html",
            )
        )

    def register_template_globals(self, app: "Flask") -> None:
        from app.modules.tickets.widgets import report_form_widget_data

        app.add_template_global(report_form_widget_data, name="tickets_report_form_widget_data")
