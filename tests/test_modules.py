from app.dashboards.widgets import WidgetDefinition
from app.modules.base import FireFlightModule
from app.modules.registry import ModuleRegistry, NavigationEntry


class _DummyModule(FireFlightModule):
    key = "dummy"
    name = "Dummy-Modul"
    version = "0.0.1"

    def __init__(self):
        self.blueprint_calls = 0

    def register_blueprints(self, app):
        self.blueprint_calls += 1

    def register_permissions(self, registry):
        registry.add_permission("dummy.view", "Dummy ansehen")

    def register_widgets(self, registry):
        registry.add_widget(WidgetDefinition("dummy_widget", "Dummy-Widget", {}))

    def register_navigation(self, registry):
        registry.add_navigation(NavigationEntry(label="Dummy", endpoint="dummy.index"))


def test_register_calls_all_four_hooks(app):
    registry = ModuleRegistry()
    module = _DummyModule()

    registry.register(module, app)

    assert module.blueprint_calls == 1
    assert ("dummy.view", "Dummy ansehen") in registry.permissions
    assert registry.navigation[0].endpoint == "dummy.index"
    from app.dashboards.widgets import widget_registry

    assert widget_registry.get("dummy_widget") is not None
    widget_registry._widgets.pop("dummy_widget", None)


def test_register_rejects_duplicate_key(app):
    registry = ModuleRegistry()
    registry.register(_DummyModule(), app)

    import pytest

    with pytest.raises(ValueError):
        registry.register(_DummyModule(), app)


def test_reset_clears_modules_navigation_and_permissions(app):
    registry = ModuleRegistry()
    registry.register(_DummyModule(), app)

    registry.reset()

    assert registry.all() == []
    assert registry.navigation == []
    assert registry.permissions == []
    from app.dashboards.widgets import widget_registry

    widget_registry._widgets.pop("dummy_widget", None)


def test_seed_permissions_includes_module_registered_permissions(app, organization):
    from app.modules.registry import module_registry
    from app.roles.services import seed_permissions

    module_registry.reset()
    module_registry.add_permission("dummy.view", "Dummy ansehen")
    try:
        permissions = seed_permissions()
        assert "dummy.view" in permissions
    finally:
        module_registry.reset()


def test_register_modules_is_idempotent_across_repeated_app_creation():
    """create_app() wird u. a. in Tests mehrfach pro Prozess aufgerufen -- module_registry ist aber
    ein Prozess-weites Singleton. Ohne reset() in _register_modules() wuerde die zweite App-Erzeugung
    mit 'bereits registriert' fehlschlagen, sobald INSTALLED_MODULES nicht mehr leer ist."""
    from app import create_app
    from app.modules import installed
    from app.modules.registry import module_registry

    original = installed.INSTALLED_MODULES
    installed.INSTALLED_MODULES = [_DummyModule()]
    try:
        create_app("testing")
        assert module_registry.get("dummy") is not None
        create_app("testing")  # darf nicht mit ValueError abbrechen
        assert module_registry.get("dummy") is not None
    finally:
        installed.INSTALLED_MODULES = original
        module_registry.reset()
        from app.dashboards.widgets import widget_registry

        widget_registry._widgets.pop("dummy_widget", None)
