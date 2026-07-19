from __future__ import annotations

from typing import TYPE_CHECKING

from app.modules.base import FireFlightModule

if TYPE_CHECKING:
    from flask import Flask


class NavigationEntry:
    def __init__(self, *, label: str, endpoint: str, icon: str | None = None, permission: str | None = None):
        self.label = label
        self.endpoint = endpoint
        self.icon = icon
        self.permission = permission


class ModuleRegistry:
    def __init__(self) -> None:
        self._modules: dict[str, FireFlightModule] = {}
        self.navigation: list[NavigationEntry] = []

    def register(self, module: FireFlightModule, app: "Flask") -> None:
        if module.key in self._modules:
            raise ValueError(f"Modul '{module.key}' ist bereits registriert")
        self._modules[module.key] = module
        module.register_blueprints(app)
        module.register_permissions(self)
        module.register_widgets(self)
        module.register_navigation(self)

    def add_navigation(self, entry: NavigationEntry) -> None:
        self.navigation.append(entry)

    def get(self, key: str) -> FireFlightModule | None:
        return self._modules.get(key)

    def all(self) -> list[FireFlightModule]:
        return list(self._modules.values())


module_registry = ModuleRegistry()
