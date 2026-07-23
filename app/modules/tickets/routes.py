from __future__ import annotations

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from app.audit.service import log_event
from app.core.exceptions import ValidationError
from app.core.security.permissions import ensure_permission, get_active_role, permission_required
from app.core.utilities.time import parse_local_datetime
from app.core.utilities.uploads import ticket_attachment_path
from app.modules.tickets import services
from app.modules.tickets.models import TICKET_STATUSES, MaintenanceRule, Ticket, TicketAttachment

bp = Blueprint("tickets", __name__, url_prefix="/tickets")

_ATTACHMENT_MIMETYPES = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}


# --- Tickets --------------------------------------------------------------------------------------


@bp.route("/")
@login_required
@permission_required("tickets.view")
def list_tickets():
    status = request.args.get("status") or None
    return render_template(
        "tickets/list.html",
        tickets=services.list_tickets(current_user.organization_id, status=status),
        statuses=TICKET_STATUSES, active_status=status,
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
@permission_required("tickets.create")
def ticket_new():
    error = None
    if request.method == "POST":
        try:
            ticket = services.create_ticket(
                current_user.organization_id,
                title=request.form.get("title", ""),
                description=request.form.get("description") or None,
                drone_label=request.form.get("drone_label") or None,
                created_by=current_user,
            )
            log_event("ticket.create", result="success", object_type="ticket", object_id=str(ticket.id))
            return redirect(url_for("tickets.ticket_detail", ticket_id=ticket.id))
        except ValidationError as exc:
            error = exc.message
    return render_template("tickets/ticket_edit.html", error=error)


@bp.route("/melden", methods=["POST"])
@login_required
@permission_required("tickets.create")
def widget_report():
    """Ziel des Dashboard-Widgets "Technisches Problem melden" (Phase 13, Konzeptdokument
    Abschnitt 9: "Ticket erstellen, inkl. Foto-Möglichkeit") -- anders als `ticket_new` (eigene
    Seite, Weiterleitung auf die Detailseite) läuft das Widget direkt im Dashboard und erstellt
    Ticket + optionales Foto in einem Aufwasch, Rückmeldung per Flash statt Detailseite."""
    try:
        ticket = services.create_ticket(
            current_user.organization_id,
            title=request.form.get("title", ""),
            description=request.form.get("description") or None,
            drone_label=request.form.get("drone_label") or None,
            created_by=current_user,
        )
        photo = request.files.get("photo")
        if photo and photo.filename:
            services.add_attachment(ticket, file=photo, uploaded_by=current_user)
        log_event("ticket.create", result="success", object_type="ticket", object_id=str(ticket.id))
        flash("Meldung erstellt.", "success")
    except ValidationError as exc:
        flash(exc.message, "error")
    return redirect(url_for("dashboards.view"))


@bp.route("/<uuid:ticket_id>")
@login_required
@permission_required("tickets.view")
def ticket_detail(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    return render_template("tickets/ticket_detail.html", ticket=ticket, statuses=TICKET_STATUSES)


@bp.route("/<uuid:ticket_id>/status", methods=["POST"])
@login_required
@permission_required("tickets.manage")
def ticket_set_status(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    try:
        services.set_ticket_status(ticket, request.form.get("status", ""))
        log_event("ticket.status_changed", result="success", object_type="ticket", object_id=str(ticket.id),
                   extra_data={"status": ticket.status})
    except ValidationError:
        abort(400)
    return redirect(url_for("tickets.ticket_detail", ticket_id=ticket.id))


@bp.route("/<uuid:ticket_id>/comments", methods=["POST"])
@login_required
@permission_required("tickets.create")
def ticket_add_comment(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    try:
        comment = services.add_comment(ticket, author=current_user, body=request.form.get("body", ""))
        log_event("ticket.comment", result="success", object_type="ticket", object_id=str(ticket.id),
                   extra_data={"comment_id": str(comment.id)})
    except ValidationError:
        pass
    return redirect(url_for("tickets.ticket_detail", ticket_id=ticket.id))


@bp.route("/<uuid:ticket_id>/attachments", methods=["POST"])
@login_required
@permission_required("tickets.create")
def ticket_add_attachment(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    file = request.files.get("attachment")
    error = None
    if file and file.filename:
        try:
            services.add_attachment(ticket, file=file, uploaded_by=current_user)
            log_event("ticket.attachment_add", result="success", object_type="ticket", object_id=str(ticket.id))
        except ValidationError as exc:
            error = exc.message
    if error:
        return render_template("tickets/ticket_detail.html", ticket=ticket, statuses=TICKET_STATUSES, error=error)
    return redirect(url_for("tickets.ticket_detail", ticket_id=ticket.id))


@bp.route("/<uuid:ticket_id>/attachments/<uuid:attachment_id>")
@login_required
@permission_required("tickets.view")
def ticket_attachment(ticket_id, attachment_id):
    attachment = TicketAttachment.query.filter_by(id=attachment_id, ticket_id=ticket_id).first_or_404()
    path = ticket_attachment_path(attachment.filename)
    if path is None:
        abort(404)
    ext = path.suffix.lstrip(".")
    return send_file(path, mimetype=_ATTACHMENT_MIMETYPES.get(ext, "application/octet-stream"))


@bp.route("/<uuid:ticket_id>/attachments/<uuid:attachment_id>/delete", methods=["POST"])
@login_required
@permission_required("tickets.manage")
def ticket_attachment_delete(ticket_id, attachment_id):
    attachment = TicketAttachment.query.filter_by(id=attachment_id, ticket_id=ticket_id).first_or_404()
    services.delete_attachment(attachment)
    log_event("ticket.attachment_delete", result="success", object_type="ticket", object_id=str(ticket_id))
    return redirect(url_for("tickets.ticket_detail", ticket_id=ticket_id))


# --- Wartungsintervalle -------------------------------------------------------------------------


@bp.route("/wartung")
@login_required
@permission_required("maintenance.view")
def list_maintenance():
    return render_template(
        "tickets/maintenance_list.html", rules=services.list_maintenance_rules(current_user.organization_id)
    )


@bp.route("/wartung/neu", methods=["GET", "POST"])
@login_required
@permission_required("maintenance.manage")
def maintenance_new():
    error = None
    if request.method == "POST":
        try:
            rule = services.create_maintenance_rule(
                current_user.organization_id,
                title=request.form.get("title", ""),
                description=request.form.get("description") or None,
                interval_days=int(request.form.get("interval_days") or 0),
                warning_days_before=int(request.form.get("warning_days_before") or 0),
            )
            log_event("maintenance.create", result="success", object_type="maintenance_rule",
                       object_id=str(rule.id))
            return redirect(url_for("tickets.maintenance_detail", rule_id=rule.id))
        except ValidationError as exc:
            error = exc.message
    return render_template("tickets/maintenance_edit.html", rule=None, error=error)


@bp.route("/wartung/<uuid:rule_id>", methods=["GET", "POST"])
@login_required
@permission_required("maintenance.view")
def maintenance_detail(rule_id):
    rule = MaintenanceRule.query.get_or_404(rule_id)
    if request.method == "POST":
        ensure_permission(get_active_role(), "maintenance.manage")
        services.update_maintenance_rule(
            rule,
            title=request.form.get("title", rule.title).strip() or rule.title,
            description=request.form.get("description") or None,
            interval_days=int(request.form.get("interval_days") or rule.interval_days),
            warning_days_before=int(request.form.get("warning_days_before") or rule.warning_days_before),
        )
        log_event("maintenance.edit", result="success", object_type="maintenance_rule", object_id=str(rule.id))
        return redirect(url_for("tickets.maintenance_detail", rule_id=rule.id))
    return render_template("tickets/maintenance_edit.html", rule=rule, error=None)


@bp.route("/wartung/<uuid:rule_id>/erledigt", methods=["POST"])
@login_required
@permission_required("maintenance.manage")
def maintenance_complete(rule_id):
    rule = MaintenanceRule.query.get_or_404(rule_id)
    services.mark_maintenance_completed(
        rule, completed_by=current_user, completed_at=parse_local_datetime(request.form.get("completed_at")),
        notes=request.form.get("notes") or None,
    )
    log_event("maintenance.completed", result="success", object_type="maintenance_rule", object_id=str(rule.id))
    return redirect(url_for("tickets.maintenance_detail", rule_id=rule.id))


@bp.route("/wartung/<uuid:rule_id>/toggle-active", methods=["POST"])
@login_required
@permission_required("maintenance.manage")
def maintenance_toggle_active(rule_id):
    rule = MaintenanceRule.query.get_or_404(rule_id)
    if rule.is_active:
        services.deactivate_maintenance_rule(rule)
    else:
        services.activate_maintenance_rule(rule)
    return redirect(url_for("tickets.list_maintenance"))
