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
    @click.option("--admin-pin", default=None, help="4-stellige PIN des ersten Administrators")
    def init_fireflight(admin_username, admin_email, admin_pin):
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
            pin = admin_pin or os.environ.get("FIREFLIGHT_ADMIN_PIN")
            if not pin:
                pin = click.prompt(
                    "Initial-PIN (4 Ziffern) für den ersten Administrator", hide_input=True, confirmation_prompt=True
                )
            user = create_user(
                organization_id=organization.id,
                username=username,
                email=email,
                pin=pin,
                display_name="Administrator",
            )
            user.roles = [admin_role]
            db.session.commit()
            click.echo(f"Erster Administrator angelegt: {username}")
        else:
            click.echo("Administrator existiert bereits, kein neuer Account angelegt.")

        click.echo("Initialisierung abgeschlossen.")

    @app.cli.group("notifications")
    def notifications_group():
        """Befehle rund um Web-Push-Benachrichtigungen (app/notifications/)."""

    @notifications_group.command("generate-vapid-keys")
    def generate_vapid_keys():
        """Erzeugt ein neues VAPID-Schlüsselpaar (roh, base64url) für Web-Push. Ausgabe direkt als
        VAPID_PUBLIC_KEY/VAPID_PRIVATE_KEY in die Umgebung übernehmen -- werden nicht in der DB
        gespeichert, da Änderungen daran alle bestehenden Subscriptions ungültig machen (der Public
        Key ist Teil der PushManager.subscribe()-Anfrage im Browser)."""
        from app.core.security.vapid import generate_vapid_keypair

        public_key, private_key = generate_vapid_keypair()
        click.echo(f"VAPID_PUBLIC_KEY={public_key}")
        click.echo(f"VAPID_PRIVATE_KEY={private_key}")

    @app.cli.command("seed-test-data")
    def seed_test_data():
        """Idempotente Test-/Demodaten für lokale Entwicklung/QA -- ein Testuser pro Standardrolle
        (PIN 4726), zwei RC-Testgeräte und mehrere Drohneneinheiten mit überlappenden Managern, wie
        im Restrukturierungsplan-Abschnitt „Testuser & Testdaten" für Ausbaustufe 2 gefordert. NICHT
        für Produktivbetrieb -- feste, bekannte PIN. Wird bei jeder neuen Phase um deren Testdaten
        erweitert (aktuell: bis Phase 6). Manager-/Heimateinheit-Zuordnung wird nur bei der
        Erstanlage einer Einheit gesetzt, nicht bei jedem erneuten Lauf überschrieben -- ein
        Administrator könnte sie inzwischen manuell geändert haben."""
        from app.auth.models import User
        from app.auth.services import create_user
        from app.rc.models import RcDevice
        from app.rc.services import create_device
        from app.units.models import Unit
        from app.units.services import assign_home_unit, create_unit, set_unit_managers
        from app.wizards.models import Wizard
        from app.wizards.services import add_step, create_wizard

        organization = Organization.query.first()
        if organization is None:
            click.echo("Keine Organisation gefunden -- zuerst `flask init-fireflight` ausführen.")
            return

        roles = seed_roles(organization.id)

        created_users = 0
        for key, role in roles.items():
            username = f"test_{key}"
            if User.query.filter_by(username=username).first() is not None:
                continue
            user = create_user(
                organization_id=organization.id,
                username=username,
                email=f"{username}@example.org",
                pin="4726",
                display_name=f"Test {role.name}",
            )
            user.roles = [role]
            if key == "pilot_camera":
                # Deckt beide RC-Testgeräte ab (s. u.) -- entspricht dem Konzeptdokument Abschnitt 5.1
                # ("Ein User kann beide Qualifikationen haben").
                user.is_pilot = True
                user.is_camera_operator = True
            db.session.commit()
            created_users += 1
        click.echo(f"{created_users} neue Testuser angelegt (PIN 4726, sofern noch nicht vorhanden).")

        rc_test_devices = [
            ("RC-Testgerät Pilot", "pilot"),
            ("RC-Testgerät Kamera", "camera_operator"),
        ]
        created_devices = []
        for label, qualification in rc_test_devices:
            if RcDevice.query.filter_by(organization_id=organization.id, label=label).first() is not None:
                continue
            device, device_key = create_device(organization.id, label=label, required_qualification=qualification)
            created_devices.append((device, device_key))
        if created_devices:
            click.echo("Neue RC-Testgeräte angelegt (Geräteschlüssel jetzt notieren, wird nie wieder angezeigt):")
            for device, device_key in created_devices:
                click.echo(f"  {device.label}: {device_key}")
        else:
            click.echo("RC-Testgeräte existieren bereits.")

        def _user(username):
            return User.query.filter_by(organization_id=organization.id, username=username).first()

        # Überlappende Manager, um unit_managers und spätere "welche Einheit(en) darf ich managen"-
        # Ansichten (Phase 7) mit mehr als einem trivialen Fall zu prüfen.
        unit_plan = [
            ("Einheit Nord", ["test_unit_leader", "test_incident_commander"], "test_pilot_camera"),
            ("Einheit Süd", ["test_incident_commander", "test_tel_elw"], "test_flight_leader"),
            ("Einheit Zentral", ["test_unit_leader", "test_tel_elw"], "test_equipment_officer"),
        ]
        created_units = 0
        for name, manager_usernames, member_username in unit_plan:
            if Unit.query.filter_by(organization_id=organization.id, name=name).first() is not None:
                continue
            unit = create_unit(organization.id, name=name)
            managers = [_user(u) for u in manager_usernames if _user(u) is not None]
            set_unit_managers(unit, [m.id for m in managers])
            member = _user(member_username)
            if member is not None:
                assign_home_unit(member, unit.id)
            created_units += 1
        click.echo(f"{created_units} neue Drohneneinheiten angelegt (sofern noch nicht vorhanden).")

        # Beispiel-Wizard (Phase 8), deckt alle fünf Step-Typen ab -- dient sowohl als Anschauungs-
        # material für die Admin-Vorschau als auch als Fixture für Tests.
        if Wizard.query.filter_by(organization_id=organization.id, key="beispiel_wizard").first() is None:
            wizard = create_wizard(
                organization.id, key="beispiel_wizard", name="Beispiel-Wizard",
                description="Demonstriert alle Step-Typen der Wizard-Engine (Phase 8).",
            )
            add_step(wizard, step_type="info", title="Willkommen", config={
                "body": "Dieser Beispiel-Wizard zeigt alle verfügbaren Step-Typen."
            })
            add_step(wizard, step_type="checklist", title="Preflight-Checkliste", config={
                "items": ["Flug angemeldet", "Drohne aufgeklappt", "Umfeld beachtet", "Luftraum kontrolliert"]
            })
            add_step(wizard, step_type="choice", title="Art des Fluges", config={
                "label": "Handelt es sich um einen Einsatz oder eine Übung?", "options": ["Einsatz", "Übung"]
            })
            add_step(wizard, step_type="text_input", title="Zweck", config={
                "label": "Worum geht es?", "required": True
            })
            add_step(wizard, step_type="confirmation", title="Bestätigung", config={
                "label": "Ich habe alle Angaben wahrheitsgemäß gemacht."
            })
            click.echo("Beispiel-Wizard angelegt.")
        else:
            click.echo("Beispiel-Wizard existiert bereits.")

        click.echo("Testdaten sichergestellt.")
