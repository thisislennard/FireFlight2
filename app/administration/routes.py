import uuid

from flask import Blueprint, abort, current_app, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.audit.models import AuditLog
from app.audit.service import log_event
from app.auth.models import User
from app.auth.services import assign_roles, create_user, list_users, set_user_active
from app.core.exceptions import ValidationError
from app.core.security.permissions import ensure_permission, get_active_role, permission_required
from app.dashboards.models import DashboardWidget
from app.dashboards.services import add_widget, get_or_create_dashboard, remove_widget, update_widget
from app.dashboards.widgets import widget_registry
from app.extensions import db
from app.organizations.models import Organization
from app.roles.models import Permission, Role
from app.roles.services import create_role, deactivate_role, set_role_permissions, update_role

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
            new_user = create_user(
                organization_id=current_user.organization_id,
                username=request.form["username"].strip(),
                email=request.form["email"].strip(),
                password=request.form["password"],
                display_name=request.form["display_name"].strip(),
            )
            log_event("user.create", result="success", object_type="user", object_id=str(new_user.id))
            return redirect(url_for("administration.user_edit", user_id=new_user.id))
        except Exception as exc:  # noqa: BLE001 - Formularfehler sollen dem Nutzer angezeigt werden
            error = str(exc)
    return render_template("administration/user_edit.html", user=None, error=error, all_roles=[])


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
    if request.method == "POST":
        try:
            ensure_permission(get_active_role(), "users.assign_roles")
            user.display_name = request.form.get("display_name", user.display_name)
            user.email = request.form.get("email", user.email)
            role_ids = [uuid.UUID(v) for v in request.form.getlist("role_ids")]
            assign_roles(user, role_ids)
            log_event("user.edit", result="success", object_type="user", object_id=str(user.id))
            return redirect(url_for("administration.users"))
        except ValidationError as exc:
            error = exc.message
    return render_template("administration/user_edit.html", user=user, error=error, all_roles=all_roles)


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
        )
        ensure_permission(get_active_role(), "roles.assign_permissions")
        set_role_permissions(role, request.form.getlist("permission_keys"))
        log_event("role.edit", result="success", object_type="role", object_id=str(role.id))
        return redirect(url_for("administration.roles"))
    return render_template(
        "administration/role_edit.html", role=role, error=None,
        all_permissions=Permission.query.order_by(Permission.key).all(),
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
