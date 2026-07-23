from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask

    from app.modules.registry import ModuleRegistry


class FireFlightModule:
    """Basisklasse für spätere Fachmodule (spec-struktur.md Abschnitt 11): Einsatzverwaltung,
    Flugbuch, Geräte-/Akkuverwaltung, Wartung, Wiki usw. werden in dieser Ausbaustufe bewusst noch
    nicht gebaut — dieses Registry-System ist der vorbereitete Andockpunkt dafür.

    Beispiel:
        class EquipmentModule(FireFlightModule):
            key = "equipment"
            name = "Geräteverwaltung"
            version = "1.0.0"

            def register_blueprints(self, app):
                from app.modules.equipment.routes import bp
                app.register_blueprint(bp)
    """

    key: str = ""
    name: str = ""
    version: str = "0.0.0"
    description: str = ""

    def register_blueprints(self, app: "Flask") -> None:
        return None

    def register_permissions(self, registry: "ModuleRegistry") -> None:
        return None

    def register_widgets(self, registry: "ModuleRegistry") -> None:
        return None

    def register_navigation(self, registry: "ModuleRegistry") -> None:
        return None

    def register_template_globals(self, app: "Flask") -> None:
        """Andockpunkt für Jinja-Globals, die eigene Widget-Templates brauchen (Phase 13) --
        context_processor-Werte wie `current_user`/`has_permission` sind im `render_widget`-Makro
        NICHT sichtbar (s. app/__init__.py: _register_hooks), daher holen sich Fachmodul-Widgets ihre
        Daten über hier registrierte echte Jinja-Globals statt über den Request-Kontext."""
        return None
