from flask import Blueprint, abort, make_response, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from app.audit.service import log_event
from app.core.models import get_setting
from app.core.security.permissions import clear_active_role_cache
from app.extensions import db
from app.roles.services import selectable_roles

bp = Blueprint("roles", __name__, url_prefix="/roles")


@bp.route("/select", methods=["GET"])
@login_required
def select():
    roles = selectable_roles(current_user)
    if not roles:
        abort(403)
    skip_if_single = get_setting("skip_role_selection_if_single_role", default=True)
    if len(roles) == 1 and skip_if_single:
        return _activate(roles[0])
    return render_template("roles/select.html", roles=roles)


@bp.route("/activate/<uuid:role_id>", methods=["POST"])
@login_required
def activate(role_id):
    role = next((r for r in selectable_roles(current_user) if r.id == role_id), None)
    if role is None:
        abort(403)
    return _activate(role)


def _activate(role):
    session["active_role_id"] = str(role.id)
    current_user.last_used_role_id = role.id
    db.session.commit()
    clear_active_role_cache()
    log_event("role.switch", result="success", object_type="role", object_id=str(role.id))

    redirect_to = url_for("dashboards.view")
    if request.headers.get("HX-Request"):
        # HTMX soll hier eine echte Browser-Navigation auslösen (nicht nur den Response-Body
        # ins auslösende Element swappen) — Sidebar/Topbar/Berechtigungen ändern sich komplett.
        response = make_response("", 204)
        response.headers["HX-Redirect"] = redirect_to
        return response
    return redirect(redirect_to)
