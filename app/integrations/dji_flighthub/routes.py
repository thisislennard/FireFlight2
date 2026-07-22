from flask import Blueprint, current_app, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.audit.service import log_event
from app.core.security.permissions import permission_required
from app.integrations.dji_flighthub.service import (
    credentials_present,
    dsgvo_acknowledged,
    gather_flighthub_overview,
    get_credentials,
    get_or_create_config,
    run_sync,
    save_config,
)

bp = Blueprint("dji_flighthub", __name__, url_prefix="/administration/integrations/dji-flighthub")


@bp.route("/", methods=["GET"])
@login_required
@permission_required("integrations.view")
def status():
    config = get_or_create_config(current_user.organization_id)
    overview = gather_flighthub_overview(config)
    creds = get_credentials(config)
    return render_template(
        "integrations/dji_flighthub/status.html",
        config=config,
        overview=overview,
        credentials_present=credentials_present(config),
        dsgvo_acknowledged=dsgvo_acknowledged(config),
        project_uuid=creds["project_uuid"],
        base_url=creds["base_url"],
        org_key_set=bool(creds["org_key"]),
        kill_switch_enabled=current_app.config.get("DJI_FLIGHTHUB_ENABLED", True),
    )


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


@bp.route("/config", methods=["POST"])
@login_required
@permission_required("integrations.configure")
def save_config_route():
    config = get_or_create_config(current_user.organization_id)
    save_config(
        config,
        org_key=request.form.get("org_key", "").strip(),
        project_uuid=request.form.get("project_uuid", ""),
        base_url=request.form.get("base_url", ""),
        dsgvo_ack=request.form.get("dsgvo_ack") == "on",
    )
    log_event(
        "integration.config_saved",
        result="success",
        object_type="integration_config",
        object_id=str(config.id),
    )
    return redirect(url_for("dji_flighthub.status"))
