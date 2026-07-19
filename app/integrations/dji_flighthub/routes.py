from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.audit.service import log_event
from app.core.security.permissions import permission_required
from app.integrations.dji_flighthub.service import get_or_create_config, run_sync

bp = Blueprint("dji_flighthub", __name__, url_prefix="/administration/integrations/dji-flighthub")


@bp.route("/", methods=["GET"])
@login_required
@permission_required("integrations.view")
def status():
    config = get_or_create_config(current_user.organization_id)
    return render_template("integrations/dji_flighthub/status.html", config=config)


@bp.route("/sync", methods=["POST"])
@login_required
@permission_required("integrations.sync")
def simulate_sync():
    config = get_or_create_config(current_user.organization_id)
    run = run_sync(config, simulated=True)
    log_event(
        "integration.sync_failed" if run.status == "failed" else "integration.sync_started",
        result=run.status,
        object_type="integration_sync_run",
        object_id=str(run.id),
    )
    return redirect(url_for("dji_flighthub.status"))
