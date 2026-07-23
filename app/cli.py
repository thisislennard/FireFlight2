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

    @app.cli.group("maintenance")
    def maintenance_group():
        """Befehle rund um Wartungsintervalle (app/modules/tickets/)."""

    @maintenance_group.command("check-due")
    def maintenance_check_due():
        """Prüft fällige/bald fällige Wartungsregeln und benachrichtigt per Web-Push (Konzeptdokument
        Abschnitt 10). Diese leichtgewichtige App hat keine eingebaute Zeitsteuerung -- gedacht für
        einen externen Cron-Job (Host-Cron beim Docker-Deployment, s. docs/roadmap.md)."""
        from app.core.exceptions import ValidationError
        from app.modules.tickets.services import rules_due_or_warning
        from app.notifications.service import send_to_users
        from app.roles.models import Role

        organization = Organization.query.first()
        if organization is None:
            click.echo("Keine Organisation gefunden.")
            return

        due = rules_due_or_warning(organization.id)
        if not due:
            click.echo("Keine fälligen oder bald fälligen Wartungsregeln.")
            return

        roles = Role.query.filter_by(organization_id=organization.id).all()
        target_roles = [
            role for role in roles
            if role.is_system or any(p.key == "maintenance.manage" for p in role.permissions)
        ]
        # Über eindeutige User dedupliziert, damit ein Nutzer mit mehreren berechtigten Rollen nicht
        # mehrfach dieselbe Push-Nachricht erhält.
        target_users = list(
            {u.id: u for role in target_roles for u in role.users if u.is_active_account}.values()
        )

        titles = ", ".join(rule.title for rule in due)
        body = f"{len(due)} Wartungsregel(n) fällig oder bald fällig: {titles}"
        try:
            send_to_users(target_users, title="Wartung fällig", body=body)
        except ValidationError as exc:
            # Kein Traceback für einen erwartbaren Konfigurationszustand (VAPID-Schlüssel fehlen,
            # z. B. auf einer frischen Installation vor dem ersten `generate-vapid-keys`-Lauf) --
            # der Cron-Job soll das als klaren, aber sauberen Fehlschlag sehen, kein Absturz.
            click.echo(f"Web-Push fehlgeschlagen: {exc.message}", err=True)
            raise SystemExit(1) from exc
        click.echo(f"{len(due)} Regel(n), {len(target_users)} Nutzer benachrichtigt.")

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
        from app.modules.incidents.models import Incident
        from app.modules.incidents.services import add_flight, create_incident
        from app.modules.tickets.models import MaintenanceRule, Ticket
        from app.modules.tickets.services import (
            add_comment,
            create_maintenance_rule,
            create_ticket,
            mark_maintenance_completed,
        )
        from app.core.models import set_setting
        from app.modules.incidents.wizard_fields import (
            FIELD_KEY_END_LOCATION,
            FIELD_KEY_HAD_ISSUES,
            FIELD_KEY_INCIDENT_KIND,
            FIELD_KEY_NOTES,
            FIELD_KEY_PURPOSE,
            FIELD_KEY_START_LOCATION,
            FIELD_KEY_SYNCED,
        )
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

        # Beispiel-Einsatz/-Übung mit zwei Flügen (Phase 9) -- deckt Logbuch-Zählung (zwei
        # verschiedene Personen, Einsatz UND Übung) sowie die Karte (Start-/End-Standort) ab.
        from datetime import datetime, timezone

        if Incident.query.filter_by(organization_id=organization.id, title="Übung Testgelände").first() is None:
            pilot = _user("test_pilot_camera")
            leader = _user("test_flight_leader")

            uebung = create_incident(
                organization.id, kind="uebung", title="Übung Testgelände",
                description="Testdaten für Logbuch und Karte.",
            )
            add_flight(
                uebung,
                pilot_id=pilot.id if pilot else None,
                camera_operator_id=pilot.id if pilot else None,
                drone_label="M30T FF Kelkheim",
                purpose="Übungsflug für Testdaten",
                started_at=datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc),
                start_lat=50.0782, start_lon=8.4482,
                ended_at=datetime(2026, 6, 15, 10, 30, tzinfo=timezone.utc),
                end_lat=50.0790, end_lon=8.4490,
                synced=True,
            )

            einsatz = create_incident(
                organization.id, kind="einsatz", title="Einsatz Vermisstensuche (Test)",
                description="Testdaten für Logbuch und Karte.",
            )
            add_flight(
                einsatz,
                pilot_id=leader.id if leader else None,
                camera_operator_id=pilot.id if pilot else None,
                drone_label="M30T FF Kelkheim",
                purpose="Suchflug für Testdaten",
                started_at=datetime(2026, 7, 2, 20, 0, tzinfo=timezone.utc),
                start_lat=50.0820, start_lon=8.4400,
                synced=False, had_issues=True, notes="Testdaten, keine echte Meldung.",
            )
            click.echo("Beispiel-Einsatz/-Übung mit Flügen angelegt.")
        else:
            click.echo("Beispiel-Einsatz/-Übung existiert bereits.")

        # Beispiel-Ticket + Wartungsregeln (Phase 10) -- eine überfällige und eine erst kürzlich
        # erledigte Regel, damit beide Anzeigezustände (Fällig/OK) in den Testdaten vorkommen.
        # `pilot` wird hier bewusst neu aufgelöst statt der Variable aus dem Einsatz-Block oben
        # wiederzuverwenden -- die ist nur gesetzt, wenn dessen if-Zweig in diesem Lauf tatsächlich
        # ausgeführt wurde (sonst NameError bei einem erneuten `seed-test-data`-Lauf).
        equipment_officer_test = _user("test_equipment_officer")
        if Ticket.query.filter_by(organization_id=organization.id, title="Kamera wackelt (Test)").first() is None:
            ticket = create_ticket(
                organization.id, title="Kamera wackelt (Test)",
                description="Testdaten -- Kamera-Gimbal zeigt Vibrationen im Video.",
                drone_label="M30T FF Kelkheim", created_by=_user("test_pilot_camera"),
            )
            add_comment(ticket, author=equipment_officer_test, body="Wird geprüft (Testdaten).")
            click.echo("Beispiel-Ticket angelegt.")
        else:
            click.echo("Beispiel-Ticket existiert bereits.")

        if MaintenanceRule.query.filter_by(organization_id=organization.id, title="Akku-Sichtprüfung (Test)") \
                .first() is None:
            overdue_rule = create_maintenance_rule(
                organization.id, title="Akku-Sichtprüfung (Test)",
                description="Testdaten -- absichtlich überfällig.",
                interval_days=30, warning_days_before=7,
            )
            mark_maintenance_completed(
                overdue_rule, completed_by=equipment_officer_test,
                completed_at=datetime(2026, 1, 1, tzinfo=timezone.utc), notes="Testdaten.",
            )
            ok_rule = create_maintenance_rule(
                organization.id, title="Propeller-Check (Test)",
                description="Testdaten -- kürzlich erledigt.",
                interval_days=90, warning_days_before=14,
            )
            mark_maintenance_completed(ok_rule, completed_by=equipment_officer_test, notes="Testdaten.")
            click.echo("Beispiel-Wartungsregeln angelegt.")
        else:
            click.echo("Beispiel-Wartungsregeln existieren bereits.")

        # RC-Preflight-/Flugende-Wizards (Phase 12) -- echte Inhalte statt des generischen
        # Beispiel-Wizards aus Phase 8, mit field_key-Zuordnung auf Flight-/Incident-Felder
        # (app/modules/incidents/wizard_fields.py). Werden zusätzlich als SystemSetting hinterlegt,
        # damit die seed-Testgeräte ohne manuellen Admin-Schritt sofort nutzbar sind.
        if Wizard.query.filter_by(organization_id=organization.id, key="rc_preflight_test").first() is None:
            preflight_wizard = create_wizard(
                organization.id, key="rc_preflight_test", name="RC-Preflight (Test)",
                description="Preflight-Check vor Flugstart (Konzeptdokument Abschnitt 5.2).",
            )
            add_step(preflight_wizard, step_type="checklist", title="Preflight-Checkliste", config={
                "items": ["Flug angemeldet", "Drohne richtig aufgeklappt", "Umfeld beachtet", "Luftraum kontrolliert"]
            })
            add_step(preflight_wizard, step_type="choice", title="Einsatz oder Übung?",
                      config={"label": "Worum handelt es sich?", "options": ["Einsatz", "Übung"]},
                      field_key=FIELD_KEY_INCIDENT_KIND)
            add_step(preflight_wizard, step_type="text_input", title="Zweck",
                      config={"label": "Worum geht es?", "required": True}, field_key=FIELD_KEY_PURPOSE)
            add_step(preflight_wizard, step_type="location", title="Standort",
                      config={"label": "Aktueller Standort"}, field_key=FIELD_KEY_START_LOCATION)
            set_setting("rc_preflight_wizard_id", str(preflight_wizard.id))
            click.echo("RC-Preflight-Test-Wizard angelegt und als aktiv hinterlegt.")
        else:
            click.echo("RC-Preflight-Test-Wizard existiert bereits.")

        if Wizard.query.filter_by(organization_id=organization.id, key="rc_flight_end_test").first() is None:
            flight_end_wizard = create_wizard(
                organization.id, key="rc_flight_end_test", name="RC-Flugende (Test)",
                description="Abschlussfragen nach Flugende (Konzeptdokument Abschnitt 5.5).",
            )
            add_step(flight_end_wizard, step_type="location", title="Standort",
                      config={"label": "Standort bei Landung"}, field_key=FIELD_KEY_END_LOCATION)
            add_step(flight_end_wizard, step_type="choice", title="Synchronisiert?",
                      config={"label": "Flüge synchronisiert?", "options": ["Ja", "Nein"]},
                      field_key=FIELD_KEY_SYNCED)
            add_step(flight_end_wizard, step_type="choice", title="Mängel?",
                      config={"label": "Gab es Mängel?", "options": ["Ja", "Nein"]},
                      field_key=FIELD_KEY_HAD_ISSUES)
            add_step(flight_end_wizard, step_type="text_input", title="Notizen",
                      config={"label": "Notizen (optional)", "required": False}, field_key=FIELD_KEY_NOTES)
            set_setting("rc_flight_end_wizard_id", str(flight_end_wizard.id))
            click.echo("RC-Flugende-Test-Wizard angelegt und als aktiv hinterlegt.")
        else:
            click.echo("RC-Flugende-Test-Wizard existiert bereits.")

        click.echo("Testdaten sichergestellt.")
