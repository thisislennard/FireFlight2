import io
from datetime import datetime, timedelta, timezone

import pytest
from werkzeug.datastructures import FileStorage

from app.core.exceptions import ValidationError
from app.extensions import db
from app.modules.tickets.models import TICKET_STATUS_CLOSED, MaintenanceRule, Ticket, TicketAttachment
from app.modules.tickets.services import (
    activate_maintenance_rule,
    add_attachment,
    add_comment,
    create_maintenance_rule,
    create_ticket,
    deactivate_maintenance_rule,
    delete_attachment,
    list_maintenance_rules,
    mark_maintenance_completed,
    rules_due_or_warning,
    set_ticket_status,
    update_maintenance_rule,
)
from tests.conftest import login

_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000a49444154789c6360000002000155273d05000000"
    "0049454e44ae426082"
)


def _png_file(name="a.png"):
    return FileStorage(stream=io.BytesIO(_PNG_BYTES), filename=name)


# --- Services: Tickets --------------------------------------------------------------------------


def test_create_ticket_rejects_empty_title(app, organization):
    with pytest.raises(ValidationError):
        create_ticket(organization.id, title="  ", description=None, drone_label=None, created_by=None)


def test_set_ticket_status_rejects_unknown_status(app, organization):
    ticket = create_ticket(organization.id, title="T", description=None, drone_label=None, created_by=None)
    with pytest.raises(ValidationError):
        set_ticket_status(ticket, "archived")


def test_set_ticket_status_updates(app, organization):
    ticket = create_ticket(organization.id, title="T", description=None, drone_label=None, created_by=None)
    set_ticket_status(ticket, TICKET_STATUS_CLOSED)
    assert ticket.status == TICKET_STATUS_CLOSED


def test_add_comment_rejects_empty_body(app, organization):
    ticket = create_ticket(organization.id, title="T", description=None, drone_label=None, created_by=None)
    with pytest.raises(ValidationError):
        add_comment(ticket, author=None, body="   ")


def test_add_and_delete_attachment(app, organization):
    ticket = create_ticket(organization.id, title="T", description=None, drone_label=None, created_by=None)
    attachment = add_attachment(ticket, file=_png_file(), uploaded_by=None)
    assert attachment.filename.endswith(".png")
    assert TicketAttachment.query.count() == 1

    delete_attachment(attachment)
    assert TicketAttachment.query.count() == 0


def test_deleting_ticket_cascades_comments_and_attachments(app, organization):
    ticket = create_ticket(organization.id, title="T", description=None, drone_label=None, created_by=None)
    add_comment(ticket, author=None, body="Hallo")
    add_attachment(ticket, file=_png_file(), uploaded_by=None)
    db.session.delete(ticket)
    db.session.commit()
    assert Ticket.query.count() == 0
    from app.modules.tickets.models import TicketComment

    assert TicketComment.query.count() == 0
    assert TicketAttachment.query.count() == 0


# --- Services: Wartungsregeln --------------------------------------------------------------------


def test_create_maintenance_rule_rejects_invalid_interval(app, organization):
    with pytest.raises(ValidationError):
        create_maintenance_rule(organization.id, title="R", description=None, interval_days=0, warning_days_before=7)


def test_create_maintenance_rule_rejects_negative_warning(app, organization):
    with pytest.raises(ValidationError):
        create_maintenance_rule(
            organization.id, title="R", description=None, interval_days=30, warning_days_before=-1
        )


def test_rule_without_events_uses_created_at_as_baseline(app, organization):
    rule = create_maintenance_rule(organization.id, title="R", description=None, interval_days=30, warning_days_before=7)
    assert rule.last_completed_at == rule.created_at
    assert rule.next_due_at == rule.created_at + timedelta(days=30)


def test_mark_completed_updates_next_due_at(app, organization):
    rule = create_maintenance_rule(organization.id, title="R", description=None, interval_days=30, warning_days_before=7)
    completed_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    mark_maintenance_completed(rule, completed_by=None, completed_at=completed_at, notes="Erledigt")
    db.session.refresh(rule)
    assert rule.last_completed_at == completed_at
    assert rule.next_due_at == completed_at + timedelta(days=30)


def test_is_due_and_is_warning_flags(app, organization):
    rule = create_maintenance_rule(organization.id, title="R", description=None, interval_days=10, warning_days_before=3)
    mark_maintenance_completed(rule, completed_by=None, completed_at=datetime.now(timezone.utc) - timedelta(days=1))
    db.session.refresh(rule)
    assert rule.is_due is False
    assert rule.is_warning is False

    overdue = create_maintenance_rule(organization.id, title="R2", description=None, interval_days=10, warning_days_before=3)
    mark_maintenance_completed(overdue, completed_by=None, completed_at=datetime.now(timezone.utc) - timedelta(days=20))
    db.session.refresh(overdue)
    assert overdue.is_due is True

    warning = create_maintenance_rule(organization.id, title="R3", description=None, interval_days=10, warning_days_before=3)
    mark_maintenance_completed(warning, completed_by=None, completed_at=datetime.now(timezone.utc) - timedelta(days=8))
    db.session.refresh(warning)
    assert warning.is_due is False
    assert warning.is_warning is True


def test_rules_due_or_warning_excludes_ok_and_inactive_rules(app, organization):
    ok_rule = create_maintenance_rule(organization.id, title="OK", description=None, interval_days=30, warning_days_before=3)
    mark_maintenance_completed(ok_rule, completed_by=None)

    overdue = create_maintenance_rule(organization.id, title="Overdue", description=None, interval_days=10, warning_days_before=3)
    mark_maintenance_completed(overdue, completed_by=None, completed_at=datetime.now(timezone.utc) - timedelta(days=20))

    inactive_overdue = create_maintenance_rule(organization.id, title="InactiveOverdue", description=None, interval_days=10, warning_days_before=3)
    mark_maintenance_completed(inactive_overdue, completed_by=None, completed_at=datetime.now(timezone.utc) - timedelta(days=20))
    deactivate_maintenance_rule(inactive_overdue)

    due = {r.id for r in rules_due_or_warning(organization.id)}
    assert due == {overdue.id}


def test_activate_deactivate_maintenance_rule(app, organization):
    rule = create_maintenance_rule(organization.id, title="R", description=None, interval_days=30, warning_days_before=7)
    deactivate_maintenance_rule(rule)
    assert rule.is_active is False
    activate_maintenance_rule(rule)
    assert rule.is_active is True


def test_update_maintenance_rule_changes_fields(app, organization):
    rule = create_maintenance_rule(organization.id, title="R", description=None, interval_days=30, warning_days_before=7)
    update_maintenance_rule(rule, title="Neu", interval_days=60)
    db.session.refresh(rule)
    assert rule.title == "Neu"
    assert rule.interval_days == 60


def test_list_maintenance_rules_filters_inactive(app, organization):
    active = create_maintenance_rule(organization.id, title="Active", description=None, interval_days=30, warning_days_before=7)
    inactive = create_maintenance_rule(organization.id, title="Inactive", description=None, interval_days=30, warning_days_before=7)
    deactivate_maintenance_rule(inactive)

    assert {r.id for r in list_maintenance_rules(organization.id)} == {active.id, inactive.id}
    assert {r.id for r in list_maintenance_rules(organization.id, include_inactive=False)} == {active.id}


# --- Routen: Tickets ------------------------------------------------------------------------------


def test_non_permission_user_gets_403_on_tickets(client, app, organization, roles):
    from app.auth.services import create_user

    user = create_user(
        organization_id=organization.id, username="norights_tix", email="norights_tix@example.org",
        pin="4726", display_name="Ohne Rechte",
    )
    user.roles = []
    db.session.commit()
    login(client, username="norights_tix")
    response = client.get("/tickets/")
    assert response.status_code == 403


def test_pilot_can_create_ticket_and_comment_but_not_change_status(client, app, organization, roles, regular_user):
    login(client, username="pilot")  # regular_user fixture -> pilot_camera role
    client.post(f"/roles/activate/{roles['pilot_camera'].id}")

    response = client.post("/tickets/new", data={"title": "Kamera defekt", "drone_label": "M30T"})
    assert response.status_code == 302
    ticket = Ticket.query.filter_by(title="Kamera defekt").first()
    assert ticket is not None

    response2 = client.post(f"/tickets/{ticket.id}/comments", data={"body": "Test-Kommentar"})
    assert response2.status_code == 302
    db.session.refresh(ticket)
    assert len(ticket.comments) == 1

    response3 = client.post(f"/tickets/{ticket.id}/status", data={"status": "closed"})
    assert response3.status_code == 403


def test_equipment_officer_can_change_ticket_status(client, app, organization, roles):
    from app.auth.services import create_user

    officer = create_user(
        organization_id=organization.id, username="officer", email="officer@example.org",
        pin="4726", display_name="Officer",
    )
    officer.roles = [roles["equipment_officer"]]
    db.session.commit()

    ticket = create_ticket(organization.id, title="T", description=None, drone_label=None, created_by=None)

    login(client, username="officer")
    client.post(f"/roles/activate/{roles['equipment_officer'].id}")
    response = client.post(f"/tickets/{ticket.id}/status", data={"status": "closed"})
    assert response.status_code == 302
    db.session.refresh(ticket)
    assert ticket.status == "closed"


def test_ticket_attachment_upload_and_serve_and_delete(client, app, organization, roles):
    from app.auth.services import create_user

    officer = create_user(
        organization_id=organization.id, username="officer2", email="officer2@example.org",
        pin="4726", display_name="Officer 2",
    )
    officer.roles = [roles["equipment_officer"]]
    db.session.commit()
    ticket = create_ticket(organization.id, title="T", description=None, drone_label=None, created_by=None)

    login(client, username="officer2")
    client.post(f"/roles/activate/{roles['equipment_officer'].id}")
    response = client.post(
        f"/tickets/{ticket.id}/attachments",
        data={"attachment": (io.BytesIO(_PNG_BYTES), "photo.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 302
    db.session.refresh(ticket)
    assert len(ticket.attachments) == 1
    attachment = ticket.attachments[0]

    image_response = client.get(f"/tickets/{ticket.id}/attachments/{attachment.id}")
    assert image_response.status_code == 200
    assert image_response.mimetype == "image/png"
    # send_file() haelt den Datei-Handle offen, bis die Response geschlossen wird -- unter Windows
    # (anders als POSIX) blockiert das ein anschliessendes unlink() im selben Prozess/Test.
    image_response.close()

    delete_response = client.post(f"/tickets/{ticket.id}/attachments/{attachment.id}/delete")
    assert delete_response.status_code == 302
    db.session.refresh(ticket)
    assert len(ticket.attachments) == 0


# --- Routen: Wartung -------------------------------------------------------------------------------


def test_equipment_officer_can_manage_maintenance_rules(client, app, organization, roles):
    from app.auth.services import create_user

    officer = create_user(
        organization_id=organization.id, username="officer3", email="officer3@example.org",
        pin="4726", display_name="Officer 3",
    )
    officer.roles = [roles["equipment_officer"]]
    db.session.commit()

    login(client, username="officer3")
    client.post(f"/roles/activate/{roles['equipment_officer'].id}")
    response = client.post(
        "/tickets/wartung/neu", data={"title": "Akku-Check", "interval_days": "30", "warning_days_before": "5"}
    )
    assert response.status_code == 302
    rule = MaintenanceRule.query.filter_by(title="Akku-Check").first()
    assert rule is not None

    complete_response = client.post(f"/tickets/wartung/{rule.id}/erledigt", data={"notes": "Erledigt"})
    assert complete_response.status_code == 302
    db.session.refresh(rule)
    assert len(rule.events) == 1

    toggle_response = client.post(f"/tickets/wartung/{rule.id}/toggle-active")
    assert toggle_response.status_code == 302
    db.session.refresh(rule)
    assert rule.is_active is False


def test_pilot_gets_403_on_maintenance_manage_routes(client, app, organization, roles, regular_user):
    rule = create_maintenance_rule(organization.id, title="R", description=None, interval_days=30, warning_days_before=7)
    login(client, username="pilot")
    client.post(f"/roles/activate/{roles['pilot_camera'].id}")
    response = client.get(f"/tickets/wartung/{rule.id}")
    assert response.status_code == 403


# --- Rollen ohne Dashboard (Gerätewart) ------------------------------------------------------------


def test_equipment_officer_lands_on_tickets_not_dashboard(client, app, organization, roles):
    from app.auth.services import create_user

    officer = create_user(
        organization_id=organization.id, username="officer4", email="officer4@example.org",
        pin="4726", display_name="Officer 4",
    )
    officer.roles = [roles["equipment_officer"]]
    db.session.commit()

    login(client, username="officer4")
    response = client.get("/roles/select")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/tickets/")


def test_equipment_officer_has_no_dashboard_link_but_has_tickets_and_wartung(client, app, organization, roles):
    from app.auth.services import create_user

    officer = create_user(
        organization_id=organization.id, username="officer5", email="officer5@example.org",
        pin="4726", display_name="Officer 5",
    )
    officer.roles = [roles["equipment_officer"]]
    db.session.commit()

    login(client, username="officer5")
    client.post(f"/roles/activate/{roles['equipment_officer'].id}")
    response = client.get("/tickets/")
    body = response.get_data(as_text=True)
    assert 'href="/dashboard/"' not in body
    assert "Tickets" in body
    assert "Wartung" in body


# --- CLI: maintenance check-due -------------------------------------------------------------------


def test_maintenance_check_due_sends_push_to_maintenance_managers(app, organization, roles, monkeypatch):
    from app.auth.services import create_user
    from app.notifications import service as notifications_service
    from app.notifications.models import NotificationLog
    from app.notifications.service import subscribe

    officer = create_user(
        organization_id=organization.id, username="officer6", email="officer6@example.org",
        pin="4726", display_name="Officer 6",
    )
    officer.roles = [roles["equipment_officer"]]
    db.session.commit()
    subscribe(officer, endpoint="https://push.example.org/officer6", p256dh="p", auth="a")
    monkeypatch.setattr(notifications_service, "webpush", lambda **kwargs: None)

    overdue = create_maintenance_rule(organization.id, title="Überfällig", description=None, interval_days=10, warning_days_before=3)
    mark_maintenance_completed(overdue, completed_by=None, completed_at=datetime.now(timezone.utc) - timedelta(days=20))

    runner = app.test_cli_runner()
    result = runner.invoke(args=["maintenance", "check-due"])
    assert result.exit_code == 0, result.output
    assert "1 Nutzer benachrichtigt" in result.output
    assert NotificationLog.query.filter_by(user_id=officer.id).count() == 1


def test_maintenance_check_due_reports_nothing_when_no_rules_due(app, organization):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["maintenance", "check-due"])
    assert result.exit_code == 0, result.output
    assert "Keine" in result.output


# --- CLI: seed-test-data -------------------------------------------------------------------------


def test_seed_test_data_creates_example_ticket_and_maintenance_rules(app):
    runner = app.test_cli_runner()
    runner.invoke(args=["init-fireflight"], env={"FIREFLIGHT_ADMIN_PIN": "4726"})

    result1 = runner.invoke(args=["seed-test-data"])
    assert result1.exit_code == 0, result1.output
    assert Ticket.query.count() == 1
    assert MaintenanceRule.query.count() == 2

    result2 = runner.invoke(args=["seed-test-data"])
    assert result2.exit_code == 0, result2.output
    assert Ticket.query.count() == 1
    assert MaintenanceRule.query.count() == 2
