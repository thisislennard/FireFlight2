import re
import uuid

from flask import Blueprint, abort, current_app, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from app.audit.models import AuditLog
from app.audit.service import log_event
from app.auth.models import User
from app.auth.services import (
    assign_roles,
    create_user,
    list_users,
    set_qualifications,
    set_user_active,
    unlock_account,
)
from app.core.exceptions import ValidationError
from app.core.security.passwords import is_trivial_pin
from app.core.security.permissions import ensure_permission, get_active_role, permission_required, role_has_permission
from app.core.models import get_setting, set_setting
from app.dashboards.models import DashboardWidget
from app.dashboards.services import add_widget, get_or_create_dashboard, remove_widget, update_widget
from app.dashboards.widgets import widget_registry
from app.extensions import db
from app.organizations.models import Organization
from app.rc.models import RcDevice
from app.rc.services import (
    activate_device,
    create_device,
    deactivate_device,
    list_devices,
    regenerate_device_key,
)
from app.roles.models import Permission, Role
from app.roles.services import create_role, deactivate_role, set_role_permissions, update_role
from app.units.models import Unit
from app.units.services import (
    activate_unit,
    assign_home_unit,
    create_unit,
    deactivate_unit,
    list_units,
    set_unit_managers,
    unit_members,
    update_unit,
)
from app.wizards.models import Wizard, WizardStep
from app.wizards.runner import WizardRunner, session_key
from app.wizards.services import (
    activate_wizard,
    add_step,
    config_from_form,
    create_wizard,
    deactivate_wizard,
    delete_step,
    list_wizards,
    move_step,
    update_step,
    update_wizard,
)
from app.wizards.step_types import step_type_registry

bp = Blueprint("administration", __name__, url_prefix="/administration")


@bp.before_request
@login_required
def _guard():
    ensure_permission(get_active_role(), "administration.access")


@bp.route("/")
def index():
    return render_template("administration/index.html")


# --- Benutzer ----------------------------------------------------------------

@bp.route("/users")
@permission_required("users.view")
def users():
    return render_template("administration/users.html", users=list_users(current_user.organization_id))


@bp.route("/users/new", methods=["GET", "POST"])
@permission_required("users.create")
def user_new():
    error = None
    if request.method == "POST":
        try:
            pin = request.form["pin"]
            if not re.fullmatch(r"\d{4}", pin):
                raise ValidationError("Die PIN muss aus genau 4 Ziffern bestehen.")
            if is_trivial_pin(pin):
                raise ValidationError("Diese PIN ist zu leicht zu erraten. Bitte eine andere PIN wählen.")
            new_user = create_user(
                organization_id=current_user.organization_id,
                username=request.form["username"].strip(),
                email=request.form["email"].strip(),
                pin=pin,
                display_name=request.form["display_name"].strip(),
            )
            log_event("user.create", result="success", object_type="user", object_id=str(new_user.id))
            return redirect(url_for("administration.user_edit", user_id=new_user.id))
        except Exception as exc:  # noqa: BLE001 - Formularfehler sollen dem Nutzer angezeigt werden
            error = str(exc)
    return render_template("administration/user_edit.html", user=None, error=error, all_roles=[], all_units=[])


@bp.route("/users/<uuid:user_id>", methods=["GET", "POST"])
@permission_required("users.edit")
def user_edit(user_id):
    user = User.query.get_or_404(user_id)
    error = None
    all_roles = (
        Role.query.filter_by(organization_id=current_user.organization_id, is_active=True)
        .order_by(Role.sort_order)
        .all()
    )
    all_units = (
        Unit.query.filter_by(organization_id=current_user.organization_id, is_active=True)
        .order_by(Unit.name)
        .all()
    )
    if request.method == "POST":
        try:
            ensure_permission(get_active_role(), "users.assign_roles")
            user.display_name = request.form.get("display_name", user.display_name)
            user.email = request.form.get("email", user.email)
            role_ids = [uuid.UUID(v) for v in request.form.getlist("role_ids")]
            assign_roles(user, role_ids)
            home_unit_id = request.form.get("home_unit_id") or None
            assign_home_unit(user, uuid.UUID(home_unit_id) if home_unit_id else None)
            set_qualifications(
                user,
                is_pilot="is_pilot" in request.form,
                is_camera_operator="is_camera_operator" in request.form,
            )
            log_event("user.edit", result="success", object_type="user", object_id=str(user.id))
            return redirect(url_for("administration.users"))
        except ValidationError as exc:
            error = exc.message
    return render_template(
        "administration/user_edit.html", user=user, error=error, all_roles=all_roles, all_units=all_units
    )


@bp.route("/users/<uuid:user_id>/toggle-active", methods=["POST"])
@permission_required("users.disable")
def user_toggle_active(user_id):
    user = User.query.get_or_404(user_id)
    try:
        set_user_active(user, not user.is_active_account)
        log_event(
            "user.disable" if not user.is_active_account else "user.enable",
            result="success", object_type="user", object_id=str(user.id),
        )
    except ValidationError as exc:
        log_event("user.disable", result="failure", object_type="user", object_id=str(user.id),
                   extra_data={"reason": exc.message})
    return redirect(url_for("administration.users"))


@bp.route("/users/<uuid:user_id>/unlock", methods=["POST"])
@permission_required("users.edit")
def user_unlock(user_id):
    user = User.query.get_or_404(user_id)
    unlock_account(user)
    log_event("user.unlock", result="success", object_type="user", object_id=str(user.id))
    return redirect(url_for("administration.user_edit", user_id=user.id))


# --- Rollen --------------------------------------------------------------------

@bp.route("/roles")
@permission_required("roles.view")
def roles():
    role_list = Role.query.filter_by(organization_id=current_user.organization_id).order_by(Role.sort_order).all()
    return render_template("administration/roles.html", roles=role_list)


@bp.route("/roles/new", methods=["GET", "POST"])
@permission_required("roles.create")
def role_new():
    error = None
    if request.method == "POST":
        try:
            role = create_role(
                current_user.organization_id,
                key=request.form["key"].strip(),
                name=request.form["name"].strip(),
                description=request.form.get("description") or None,
                icon=request.form.get("icon") or None,
                accent_color=request.form.get("accent_color") or None,
            )
            log_event("role.create", result="success", object_type="role", object_id=str(role.id))
            return redirect(url_for("administration.role_edit", role_id=role.id))
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
    return render_template(
        "administration/role_edit.html", role=None, error=error,
        all_permissions=Permission.query.order_by(Permission.key).all(),
    )


def _landing_choices_for_role(role: Role) -> list[tuple[str, str]]:
    """Zielendpunkte, die im Editor als Startbereich einer Rolle wählbar sind -- gefiltert auf die
    Berechtigungen, die die Rolle aktuell besitzt (spec-struktur.md-Erweiterung: Rollen ohne
    Dashboard). `dashboards.view` erscheint nur, wenn die Rolle `dashboard.view` hat; weitere Ziele
    kommen aus `ModuleRegistry.navigation`, sobald Fachmodule eigene Navigationseinträge liefern."""
    from app.modules.registry import module_registry

    choices = []
    if role_has_permission(role, "dashboard.view"):
        choices.append(("dashboards.view", "Dashboard"))
    for entry in module_registry.navigation:
        if entry.permission is None or role_has_permission(role, entry.permission):
            choices.append((entry.endpoint, entry.label))
    return choices


@bp.route("/roles/<uuid:role_id>", methods=["GET", "POST"])
@permission_required("roles.edit")
def role_edit(role_id):
    role = Role.query.get_or_404(role_id)
    if request.method == "POST":
        update_role(
            role,
            name=request.form.get("name", role.name),
            description=request.form.get("description") or None,
            icon=request.form.get("icon") or None,
            accent_color=request.form.get("accent_color") or None,
            sort_order=int(request.form.get("sort_order", role.sort_order) or role.sort_order),
            landing_endpoint=request.form.get("landing_endpoint") or "dashboards.view",
        )
        ensure_permission(get_active_role(), "roles.assign_permissions")
        set_role_permissions(role, request.form.getlist("permission_keys"))
        log_event("role.edit", result="success", object_type="role", object_id=str(role.id))
        return redirect(url_for("administration.roles"))
    return render_template(
        "administration/role_edit.html", role=role, error=None,
        all_permissions=Permission.query.order_by(Permission.key).all(),
        landing_choices=_landing_choices_for_role(role),
    )


@bp.route("/roles/<uuid:role_id>/deactivate", methods=["POST"])
@permission_required("roles.disable")
def role_deactivate(role_id):
    role = Role.query.get_or_404(role_id)
    try:
        deactivate_role(role)
        log_event("role.disable", result="success", object_type="role", object_id=str(role.id))
    except ValidationError as exc:
        log_event("role.disable", result="failure", object_type="role", object_id=str(role.id),
                   extra_data={"reason": exc.message})
    return redirect(url_for("administration.roles"))


# --- Dashboards ------------------------------------------------------------------

@bp.route("/dashboards/<uuid:role_id>", methods=["GET"])
@permission_required("dashboard.manage")
def dashboard_edit(role_id):
    role = Role.query.get_or_404(role_id)
    dashboard = get_or_create_dashboard(role)
    return render_template(
        "administration/dashboard_edit.html", role=role, dashboard=dashboard,
        widget_types=widget_registry.all(),
    )


@bp.route("/dashboards/<uuid:role_id>/widgets", methods=["POST"])
@permission_required("dashboard.manage")
def dashboard_add_widget(role_id):
    role = Role.query.get_or_404(role_id)
    dashboard = get_or_create_dashboard(role)
    definition = widget_registry.get(request.form.get("widget_type", ""))
    if definition is None:
        abort(400)
    add_widget(dashboard, widget_type=definition.key, title=definition.label, config=dict(definition.default_config))
    log_event("dashboard.edit", result="success", object_type="dashboard", object_id=str(dashboard.id))
    return redirect(url_for("administration.dashboard_edit", role_id=role.id))


@bp.route("/dashboards/<uuid:role_id>/widgets/<uuid:widget_id>", methods=["POST"])
@permission_required("dashboard.manage")
def dashboard_update_widget(role_id, widget_id):
    widget = DashboardWidget.query.get_or_404(widget_id)
    update_widget(
        widget,
        title=request.form.get("title", widget.title),
        width=int(request.form.get("width", widget.width) or widget.width),
        height=int(request.form.get("height", widget.height) or widget.height),
    )
    log_event("dashboard.edit", result="success", object_type="dashboard_widget", object_id=str(widget.id))
    return redirect(url_for("administration.dashboard_edit", role_id=role_id))


@bp.route("/dashboards/<uuid:role_id>/widgets/<uuid:widget_id>/delete", methods=["POST"])
@permission_required("dashboard.manage")
def dashboard_delete_widget(role_id, widget_id):
    widget = DashboardWidget.query.get_or_404(widget_id)
    remove_widget(widget)
    log_event("dashboard.edit", result="success", object_type="dashboard_widget", object_id=str(widget_id))
    return redirect(url_for("administration.dashboard_edit", role_id=role_id))


# --- Organisation ------------------------------------------------------------------

@bp.route("/organization", methods=["GET", "POST"])
@permission_required("organization.view")
def organization():
    org = Organization.query.get_or_404(current_user.organization_id)
    if request.method == "POST":
        ensure_permission(get_active_role(), "organization.edit")
        org.name = request.form.get("name", org.name)
        org.short_name = request.form.get("short_name") or None
        org.timezone = request.form.get("timezone", org.timezone)
        db.session.commit()
        log_event("organization.edit", result="success", object_type="organization", object_id=str(org.id))
    return render_template("administration/organization.html", organization=org)


# --- Audit-Log -----------------------------------------------------------------------

@bp.route("/audit-log")
@permission_required("audit.view")
def audit_log():
    page = request.args.get("page", 1, type=int)
    action_filter = request.args.get("action") or None
    query = (
        AuditLog.query.filter_by(organization_id=current_user.organization_id)
        .order_by(AuditLog.created_at.desc())
    )
    if action_filter:
        query = query.filter(AuditLog.action == action_filter)
    pagination = query.paginate(page=page, per_page=25, error_out=False)
    actions = [row[0] for row in db.session.query(AuditLog.action).distinct().order_by(AuditLog.action)]
    return render_template(
        "administration/audit_log.html", pagination=pagination, action_filter=action_filter, actions=actions
    )


# --- RC-Geräte (app/rc/) ---------------------------------------------------------------

@bp.route("/rc-devices", methods=["GET", "POST"])
@permission_required("rc_devices.view")
def rc_devices():
    if request.method == "POST":
        ensure_permission(get_active_role(), "rc_devices.manage")
        set_setting("rc_dji_pilot2_deeplink_url", request.form.get("dji_pilot2_deeplink_url", "").strip() or None)
        log_event("rc_device.deeplink_updated", result="success")
        return redirect(url_for("administration.rc_devices"))
    return render_template(
        "administration/rc_devices.html",
        devices=list_devices(current_user.organization_id),
        dji_pilot2_deeplink=get_setting("rc_dji_pilot2_deeplink_url") or "",
    )


@bp.route("/rc-devices/new", methods=["GET", "POST"])
@permission_required("rc_devices.manage")
def rc_device_new():
    error = None
    if request.method == "POST":
        try:
            label = request.form["label"].strip()
            if not label:
                raise ValidationError("Bezeichnung darf nicht leer sein.")
            required_qualification = request.form.get("required_qualification") or None
            device, device_key = create_device(
                current_user.organization_id, label=label, required_qualification=required_qualification
            )
            log_event("rc_device.create", result="success", object_type="rc_device", object_id=str(device.id))
            return render_template("administration/rc_device_key.html", device=device, device_key=device_key)
        except ValidationError as exc:
            error = exc.message
    return render_template("administration/rc_device_edit.html", error=error)


@bp.route("/rc-devices/<uuid:device_id>/regenerate-key", methods=["POST"])
@permission_required("rc_devices.manage")
def rc_device_regenerate_key(device_id):
    device = RcDevice.query.get_or_404(device_id)
    device_key = regenerate_device_key(device)
    log_event("rc_device.regenerate_key", result="success", object_type="rc_device", object_id=str(device.id))
    return render_template("administration/rc_device_key.html", device=device, device_key=device_key)


@bp.route("/rc-devices/<uuid:device_id>/toggle-active", methods=["POST"])
@permission_required("rc_devices.manage")
def rc_device_toggle_active(device_id):
    device = RcDevice.query.get_or_404(device_id)
    if device.is_active:
        deactivate_device(device)
        log_event("rc_device.disable", result="success", object_type="rc_device", object_id=str(device.id))
    else:
        activate_device(device)
        log_event("rc_device.enable", result="success", object_type="rc_device", object_id=str(device.id))
    return redirect(url_for("administration.rc_devices"))


# --- Drohneneinheiten (app/units/) ------------------------------------------------------

@bp.route("/units")
@permission_required("units.view")
def units():
    return render_template(
        "administration/units.html", units=list_units(current_user.organization_id)
    )


@bp.route("/units/new", methods=["GET", "POST"])
@permission_required("units.manage")
def unit_new():
    error = None
    if request.method == "POST":
        try:
            name = request.form["name"].strip()
            if not name:
                raise ValidationError("Name darf nicht leer sein.")
            unit = create_unit(
                current_user.organization_id, name=name, description=request.form.get("description") or None
            )
            log_event("unit.create", result="success", object_type="unit", object_id=str(unit.id))
            return redirect(url_for("administration.unit_edit", unit_id=unit.id))
        except ValidationError as exc:
            error = exc.message
    return render_template(
        "administration/unit_edit.html", unit=None, error=error, all_users=[], members=[]
    )


@bp.route("/units/<uuid:unit_id>", methods=["GET", "POST"])
@permission_required("units.manage")
def unit_edit(unit_id):
    unit = Unit.query.get_or_404(unit_id)
    if request.method == "POST":
        update_unit(
            unit,
            name=request.form.get("name", unit.name).strip() or unit.name,
            description=request.form.get("description") or None,
        )
        set_unit_managers(unit, [uuid.UUID(v) for v in request.form.getlist("manager_ids")])
        log_event("unit.edit", result="success", object_type="unit", object_id=str(unit.id))
        return redirect(url_for("administration.units"))
    all_users = User.query.filter_by(organization_id=current_user.organization_id).order_by(User.display_name).all()
    return render_template(
        "administration/unit_edit.html", unit=unit, error=None, all_users=all_users, members=unit_members(unit)
    )


@bp.route("/units/<uuid:unit_id>/toggle-active", methods=["POST"])
@permission_required("units.manage")
def unit_toggle_active(unit_id):
    unit = Unit.query.get_or_404(unit_id)
    if unit.is_active:
        deactivate_unit(unit)
        log_event("unit.disable", result="success", object_type="unit", object_id=str(unit.id))
    else:
        activate_unit(unit)
        log_event("unit.enable", result="success", object_type="unit", object_id=str(unit.id))
    return redirect(url_for("administration.units"))


# --- Wizards (app/wizards/) -------------------------------------------------------------------

@bp.route("/wizards")
@permission_required("wizards.view")
def wizards():
    return render_template("administration/wizards.html", wizards=list_wizards(current_user.organization_id))


@bp.route("/wizards/new", methods=["GET", "POST"])
@permission_required("wizards.manage")
def wizard_new():
    error = None
    if request.method == "POST":
        try:
            wizard = create_wizard(
                current_user.organization_id,
                key=request.form["key"].strip(),
                name=request.form["name"].strip(),
                description=request.form.get("description") or None,
            )
            log_event("wizard.create", result="success", object_type="wizard", object_id=str(wizard.id))
            return redirect(url_for("administration.wizard_edit", wizard_id=wizard.id))
        except ValidationError as exc:
            error = exc.message
    return render_template("administration/wizard_edit.html", wizard=None, error=error,
                            step_types=step_type_registry.all())


@bp.route("/wizards/<uuid:wizard_id>", methods=["GET", "POST"])
@permission_required("wizards.manage")
def wizard_edit(wizard_id):
    wizard = Wizard.query.get_or_404(wizard_id)
    if request.method == "POST":
        update_wizard(
            wizard,
            name=request.form.get("name", wizard.name).strip() or wizard.name,
            description=request.form.get("description") or None,
        )
        log_event("wizard.edit", result="success", object_type="wizard", object_id=str(wizard.id))
        return redirect(url_for("administration.wizard_edit", wizard_id=wizard.id))
    return render_template("administration/wizard_edit.html", wizard=wizard, error=None,
                            step_types=step_type_registry.all())


@bp.route("/wizards/<uuid:wizard_id>/toggle-active", methods=["POST"])
@permission_required("wizards.manage")
def wizard_toggle_active(wizard_id):
    wizard = Wizard.query.get_or_404(wizard_id)
    if wizard.is_active:
        deactivate_wizard(wizard)
        log_event("wizard.disable", result="success", object_type="wizard", object_id=str(wizard.id))
    else:
        activate_wizard(wizard)
        log_event("wizard.enable", result="success", object_type="wizard", object_id=str(wizard.id))
    return redirect(url_for("administration.wizard_edit", wizard_id=wizard.id))


@bp.route("/wizards/<uuid:wizard_id>/steps", methods=["POST"])
@permission_required("wizards.manage")
def wizard_add_step(wizard_id):
    wizard = Wizard.query.get_or_404(wizard_id)
    definition = step_type_registry.get(request.form.get("step_type", ""))
    if definition is None:
        abort(400)
    title = request.form.get("title", "").strip() or definition.label
    step = add_step(wizard, step_type=definition.key, title=title, config=dict(definition.default_config))
    log_event("wizard.step_add", result="success", object_type="wizard_step", object_id=str(step.id))
    return redirect(url_for("administration.wizard_step_edit", wizard_id=wizard.id, step_id=step.id))


@bp.route("/wizards/<uuid:wizard_id>/steps/<uuid:step_id>", methods=["GET", "POST"])
@permission_required("wizards.manage")
def wizard_step_edit(wizard_id, step_id):
    step = WizardStep.query.filter_by(id=step_id, wizard_id=wizard_id).first_or_404()
    definition = step_type_registry.get(step.step_type)
    if request.method == "POST":
        title = request.form.get("title", "").strip() or step.title
        config = config_from_form(step.step_type, request.form)
        update_step(step, title=title, config=config)
        log_event("wizard.step_edit", result="success", object_type="wizard_step", object_id=str(step.id))
        return redirect(url_for("administration.wizard_edit", wizard_id=wizard_id))
    return render_template("administration/wizard_step_edit.html", step=step, definition=definition)


@bp.route("/wizards/<uuid:wizard_id>/steps/<uuid:step_id>/delete", methods=["POST"])
@permission_required("wizards.manage")
def wizard_step_delete(wizard_id, step_id):
    step = WizardStep.query.filter_by(id=step_id, wizard_id=wizard_id).first_or_404()
    delete_step(step)
    log_event("wizard.step_delete", result="success", object_type="wizard_step", object_id=str(step_id))
    return redirect(url_for("administration.wizard_edit", wizard_id=wizard_id))


@bp.route("/wizards/<uuid:wizard_id>/steps/<uuid:step_id>/move", methods=["POST"])
@permission_required("wizards.manage")
def wizard_step_move(wizard_id, step_id):
    step = WizardStep.query.filter_by(id=step_id, wizard_id=wizard_id).first_or_404()
    move_step(step, request.form.get("direction", ""))
    return redirect(url_for("administration.wizard_edit", wizard_id=wizard_id))


@bp.route("/wizards/<uuid:wizard_id>/preview", methods=["GET", "POST"])
@permission_required("wizards.view")
def wizard_preview(wizard_id):
    wizard = Wizard.query.get_or_404(wizard_id)
    key = session_key(wizard.id)
    state = session.get(key, {})
    runner = WizardRunner(wizard, state)

    error = None
    if request.method == "POST":
        action = request.form.get("action", "next")
        if action == "back":
            runner.back()
        elif action == "reset":
            runner.reset()
        elif not runner.submit(request.form):
            error = "Bitte alle erforderlichen Angaben auf dieser Seite machen, bevor du weitergehst."
        session[key] = runner.state
        if error is None:
            return redirect(url_for("administration.wizard_preview", wizard_id=wizard.id))

    return render_template(
        "administration/wizard_preview.html", wizard=wizard, runner=runner, error=error,
    )
