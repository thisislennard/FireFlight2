from __future__ import annotations

import logging

from flask import Flask, redirect, render_template, session, url_for
from flask_login import current_user

from app.config import CONFIG_BY_NAME, get_config_name
from app.core.exceptions import NotFoundError, PermissionDenied, ValidationError
from app.extensions import csrf, db, limiter, login_manager, migrate


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    config_name = config_name or get_config_name()
    app.config.from_object(CONFIG_BY_NAME.get(config_name, CONFIG_BY_NAME["production"]))

    _init_extensions(app)
    _register_blueprints(app)
    _register_modules(app)
    _register_error_handlers(app)
    _register_hooks(app)
    _register_cli(app)
    _register_root_route(app)
    _configure_logging(app)

    return app


def _init_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    # Der RC-Kiosk-Zugang (app/rc/) hat eine eigene Login-Seite -- ohne diese Zuordnung würde
    # @login_required auf /rc/-Routen bei fehlender Session auf die Desktop-Login-Seite umleiten und
    # damit aus dem Kiosk-Kontext herausfallen.
    login_manager.blueprint_login_views = {"rc": "rc.login"}
    csrf.init_app(app)
    limiter.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        from app.auth.models import User

        return db.session.get(User, user_id)


def _register_blueprints(app: Flask) -> None:
    # Reihenfolge bewusst: auth/roles/dashboards zuerst (werden von administration per url_for
    # referenziert und müssen daher schon registrierte Endpunkte haben).
    from app.administration.routes import bp as administration_bp
    from app.auth.routes import bp as auth_bp
    from app.dashboards.routes import bp as dashboards_bp
    from app.notifications.routes import bp as notifications_bp
    from app.profile.routes import bp as profile_bp
    from app.rc.routes import bp as rc_bp
    from app.roles.routes import bp as roles_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(roles_bp)
    app.register_blueprint(dashboards_bp)
    app.register_blueprint(administration_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(rc_bp)


def _register_modules(app: Flask) -> None:
    from app.modules.installed import INSTALLED_MODULES
    from app.modules.registry import module_registry

    module_registry.reset()
    for module in INSTALLED_MODULES:
        module_registry.register(module, app)


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(PermissionDenied)
    def _permission_denied(exc):
        return render_template("errors/403.html"), 403

    @app.errorhandler(ValidationError)
    def _validation_error(exc):
        return render_template("errors/500.html", message=exc.message), 400

    @app.errorhandler(NotFoundError)
    def _domain_not_found(exc):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def _http_forbidden(exc):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def _http_not_found(exc):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def _http_server_error(exc):
        db.session.rollback()
        return render_template("errors/500.html"), 500


def _register_hooks(app: Flask) -> None:
    from app.core.utilities.time import to_local
    from app.dashboards.widgets import widget_registry

    # add_template_global() statt context_processor: render_widget() wird in view.html per
    # `{% from ... import render_widget %}` OHNE `with context` importiert, daher sind
    # context_processor-Werte im Makro nicht sichtbar -- echte Jinja-Globals (wie url_for) schon.
    app.add_template_global(widget_registry.get, name="widget_definition")
    app.add_template_global(to_local, name="to_local")

    @app.before_request
    def _load_active_role():
        from app.core.security.permissions import get_active_role

        get_active_role()

    @app.after_request
    def _security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            # img-src erlaubt zusätzlich den OSM-Tile-Host für die Flugbuch-Karte
            # (app/modules/incidents/, Leaflet lokal vendored unter static/lib/leaflet/ -- nur die
            # Kartenkacheln selbst kommen extern, kein Script/Connect-Zugriff auf Fremd-Hosts nötig).
            "default-src 'self'; img-src 'self' data: https://tile.openstreetmap.org; "
            "style-src 'self'; script-src 'self'; connect-src 'self'",
        )
        return response

    @app.context_processor
    def _inject_globals():
        from app.core.security.permissions import get_active_role, role_has_permission
        from app.modules.registry import module_registry

        active_role = get_active_role()
        return {
            "active_role": active_role,
            "has_permission": lambda key: role_has_permission(active_role, key),
            "module_navigation": module_registry.navigation,
        }


def _register_cli(app: Flask) -> None:
    from app.cli import register_cli

    register_cli(app)


def _register_root_route(app: Flask) -> None:
    @app.route("/")
    def index():
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not session.get("active_role_id"):
            return redirect(url_for("roles.select"))
        return redirect(url_for("dashboards.view"))


def _configure_logging(app: Flask) -> None:
    if not app.debug:
        logging.basicConfig(level=logging.INFO)
