from __future__ import annotations

import os

import click
from flask import Flask

from app.core.models import SystemSetting
from app.extensions import db
from app.organizations.models import Organization
from app.roles.services import seed_roles

DEFAULT_ORG_NAME = "Feuerwehr Liederbach"


def register_cli(app: Flask) -> None:
    @app.cli.command("init-fireflight")
    @click.option("--admin-username", default=None, help="Benutzername des ersten Administrators")
    @click.option("--admin-email", default=None, help="E-Mail des ersten Administrators")
    @click.option("--admin-password", default=None, help="Passwort des ersten Administrators")
    def init_fireflight(admin_username, admin_email, admin_password):
        """Idempotente Ersteinrichtung: Organisation, Berechtigungen, Rollen, Dashboards,
        erster Administrator (spec-struktur.md Abschnitt 21). Kann gefahrlos mehrfach laufen."""
        from app.auth.services import create_user
        from app.dashboards.services import get_or_create_dashboard

        organization = Organization.query.first()
        if organization is None:
            organization = Organization(name=DEFAULT_ORG_NAME)
            db.session.add(organization)
            db.session.commit()
            click.echo(f"Organisation angelegt: {organization.name}")
        else:
            click.echo(f"Organisation existiert bereits: {organization.name}")

        roles = seed_roles(organization.id)
        click.echo(f"Rollen/Berechtigungen sichergestellt ({len(roles)} Rollen).")

        for role in roles.values():
            get_or_create_dashboard(role)
        click.echo("Standard-Dashboards sichergestellt.")

        if SystemSetting.query.filter_by(key="skip_role_selection_if_single_role").first() is None:
            db.session.add(SystemSetting(key="skip_role_selection_if_single_role", value={"value": True}))
            db.session.commit()

        admin_role = roles["administrator"]
        has_admin = len(admin_role.users) > 0
        if not has_admin:
            username = admin_username or os.environ.get("FIREFLIGHT_ADMIN_USERNAME", "admin")
            email = admin_email or os.environ.get("FIREFLIGHT_ADMIN_EMAIL", "admin@example.org")
            password = admin_password or os.environ.get("FIREFLIGHT_ADMIN_PASSWORD")
            if not password:
                password = click.prompt(
                    "Initialpasswort für den ersten Administrator", hide_input=True, confirmation_prompt=True
                )
            user = create_user(
                organization_id=organization.id,
                username=username,
                email=email,
                password=password,
                display_name="Administrator",
            )
            user.roles = [admin_role]
            db.session.commit()
            click.echo(f"Erster Administrator angelegt: {username}")
        else:
            click.echo("Administrator existiert bereits, kein neuer Account angelegt.")

        click.echo("Initialisierung abgeschlossen.")
