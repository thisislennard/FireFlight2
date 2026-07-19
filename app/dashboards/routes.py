from flask import Blueprint, render_template
from flask_login import login_required

from app.core.security.permissions import get_active_role, permission_required
from app.dashboards.services import get_or_create_dashboard

bp = Blueprint("dashboards", __name__, url_prefix="/dashboard")


@bp.route("/")
@login_required
@permission_required("dashboard.view")
def view():
    role = get_active_role()
    dashboard = get_or_create_dashboard(role)
    return render_template("dashboards/view.html", dashboard=dashboard, role=role)
