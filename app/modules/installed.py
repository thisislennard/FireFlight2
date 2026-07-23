"""Zentrale Liste der zu ladenden Fachmodule (spec-struktur.md Abschnitt 11).

Bewusst eine explizite Liste statt Filesystem-Scanning (Django-INSTALLED_APPS-Muster) --
Importfehler in einem Modul werden damit sofort beim App-Start sichtbar statt lautlos
uebersprungen. `app._register_modules()` iteriert darueber und ruft `module_registry.register(...)`
auf. Neue Fachmodule werden hier eingetragen, sobald sie existieren.
"""
from __future__ import annotations

from app.modules.base import FireFlightModule
from app.modules.incidents.module import IncidentsModule

INSTALLED_MODULES: list[FireFlightModule] = [
    IncidentsModule(),
]
