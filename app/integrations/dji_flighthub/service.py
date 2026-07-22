from __future__ import annotations

import time
from datetime import datetime, timezone

from flask import current_app
from flask_login import current_user

from app.extensions import db
from app.integrations.dji_flighthub.base import DJIFlightHubApiError, DJIFlightHubClient, ExternalRecord
from app.integrations.dji_flighthub.live_client import LiveDJIFlightHubClient
from app.integrations.dji_flighthub.mock_client import MockDJIFlightHubClient
from app.integrations.dji_flighthub.models import ExternalReference, IntegrationConfig, IntegrationSyncRun

INTEGRATION_KEY = "dji_flighthub"

# Caps für die "alles auf einmal"-Übersichtsseite — verhindert, dass eine große Organisation
# hunderte API-Calls auf einmal auslöst. Rein administrative/Explorationszwecke, keine Vollsynchronisierung.
MAX_DEVICES_WITH_DETAIL = 10
MAX_TASKS_PER_DEVICE = 5
MAX_TASKS_WITH_DETAIL_PER_DEVICE = 3
TASK_LOOKBACK_SECONDS = 90 * 24 * 3600


def get_or_create_config(organization_id) -> IntegrationConfig:
    config = IntegrationConfig.query.filter_by(
        organization_id=organization_id, integration_key=INTEGRATION_KEY
    ).first()
    if config is None:
        config = IntegrationConfig(organization_id=organization_id, integration_key=INTEGRATION_KEY)
        db.session.add(config)
        db.session.commit()
    return config


def dsgvo_acknowledged(config: IntegrationConfig) -> bool:
    return bool((config.settings or {}).get("dsgvo_ack"))


def get_credentials(config: IntegrationConfig) -> dict:
    """Zugangsdaten: DB-Werte (über die Administrationsoberfläche gepflegt) haben Vorrang,
    `DJI_FLIGHTHUB_*`-Umgebungsvariablen dienen nur als optionaler Deployment-Default (z. B. Docker),
    damit ein frisch aufgesetzter Container nicht zwingend einmal durch die UI konfiguriert werden muss."""
    settings = config.settings or {}
    cfg = current_app.config
    return {
        "org_key": settings.get("org_key") or cfg.get("DJI_FLIGHTHUB_ORG_KEY", ""),
        "project_uuid": settings.get("project_uuid") or cfg.get("DJI_FLIGHTHUB_PROJECT_UUID", ""),
        "base_url": settings.get("base_url") or cfg.get("DJI_FLIGHTHUB_BASE_URL") or "https://fh.dji.com",
    }


def credentials_present(config: IntegrationConfig) -> bool:
    creds = get_credentials(config)
    return bool(creds["org_key"] and creds["project_uuid"])


def save_config(
    config: IntegrationConfig, *, org_key: str | None, project_uuid: str, base_url: str, dsgvo_ack: bool
) -> IntegrationConfig:
    """Speichert Zugangsdaten + DSGVO-Bestätigung. `org_key` wird im Formular nie vorausgefüllt
    (Passwortfeld) — leer gelassen heißt „unverändert lassen", nicht „löschen"."""
    settings = dict(config.settings or {})
    if org_key:
        settings["org_key"] = org_key
    settings["project_uuid"] = project_uuid.strip()
    settings["base_url"] = base_url.strip() or "https://fh.dji.com"
    settings["dsgvo_ack"] = dsgvo_ack
    config.settings = settings
    config.is_enabled = bool(settings.get("org_key") and settings["project_uuid"])
    db.session.commit()
    return config


def get_client(config: IntegrationConfig | None = None) -> DJIFlightHubClient:
    kill_switch_off = not current_app.config.get("DJI_FLIGHTHUB_ENABLED", True)
    if not kill_switch_off and config is not None and credentials_present(config) and dsgvo_acknowledged(config):
        creds = get_credentials(config)
        return LiveDJIFlightHubClient(base_url=creds["base_url"], org_key=creds["org_key"], project_uuid=creds["project_uuid"])
    return MockDJIFlightHubClient()


def run_sync(config: IntegrationConfig, *, simulated: bool = True) -> IntegrationSyncRun:
    run = IntegrationSyncRun(
        integration_config_id=config.id,
        is_simulated=simulated,
        triggered_by_user_id=getattr(current_user, "id", None) if current_user.is_authenticated else None,
    )
    db.session.add(run)
    db.session.commit()

    try:
        client = get_client(config)
        devices = client.list_devices()
        for record in devices:
            _upsert_external_reference(config.organization_id, "DJI_FLIGHTHUB", record)
        run.records_processed = len(devices)
        run.status = "success"
    except Exception as exc:  # noqa: BLE001 - Sync-Fehler müssen sichtbar protokolliert werden, dürfen die App nicht crashen
        run.status = "failed"
        run.error_message = str(exc)[:1000]
        current_app.logger.exception("DJI FlightHub Synchronisierung fehlgeschlagen")
    finally:
        run.finished_at = datetime.now(timezone.utc)
        db.session.commit()

    return run


def _upsert_external_reference(organization_id, source: str, record: ExternalRecord) -> ExternalReference:
    ref = ExternalReference.query.filter_by(
        organization_id=organization_id, source=source, external_id=record.external_id
    ).first()
    now = datetime.now(timezone.utc)
    if ref is None:
        ref = ExternalReference(
            organization_id=organization_id,
            source=source,
            external_id=record.external_id,
            internal_object_type="device",
            first_imported_at=now,
        )
        db.session.add(ref)
    ref.last_synced_at = now
    ref.raw_payload = record.payload
    ref.sync_error = None
    db.session.commit()
    return ref


def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs), None
    except DJIFlightHubApiError as exc:
        return None, str(exc)
    except Exception as exc:  # noqa: BLE001 - jede Sektion der Übersicht darf unabhängig fehlschlagen
        current_app.logger.exception("DJI FlightHub Übersicht: Abschnitt fehlgeschlagen (%s)", getattr(fn, "__name__", fn))
        return None, str(exc)


def _device_sns_from_records(devices: list[ExternalRecord] | None) -> list[str]:
    sns: list[str] = []
    for record in devices or []:
        for key in ("gateway", "drone"):
            sn = (record.payload.get(key) or {}).get("sn")
            if sn and sn not in sns:
                sns.append(sn)
    return sns


def gather_flighthub_overview(config: IntegrationConfig) -> dict:
    """Ruft alle lesenden Endpunkte auf einmal ab, für die Administrations-Übersichtsseite.

    Jeder Abschnitt ist unabhängig fehlertolerant (`_safe`) — ein einzelner fehlschlagender Endpunkt
    (z. B. weil ein Gerät offline ist) darf die restliche Seite nicht mitreißen."""
    client = get_client(config)
    overview: dict = {"client_type": "live" if isinstance(client, LiveDJIFlightHubClient) else "mock"}

    overview["system_status"], overview["system_status_error"] = _safe(client.get_system_status)
    overview["projects"], overview["projects_error"] = _safe(client.list_projects)
    overview["devices"], overview["devices_error"] = _safe(client.list_devices)

    device_sns = _device_sns_from_records(overview["devices"])[:MAX_DEVICES_WITH_DETAIL]
    overview["device_sns"] = device_sns

    overview["hms"], overview["hms_error"] = _safe(client.get_hms, device_sns or None)

    device_states = {}
    for sn in device_sns:
        state, error = _safe(client.get_device_state, sn)
        device_states[sn] = {"state": state, "error": error}
    overview["device_states"] = device_states

    overview["waylines"], overview["waylines_error"] = _safe(client.list_waylines)

    now = int(time.time())
    begin_at = now - TASK_LOOKBACK_SECONDS
    flight_tasks_by_device = {}
    for sn in device_sns:
        tasks, error = _safe(client.list_flight_tasks, sn, begin_at, now)
        entry: dict = {"tasks": [], "error": error}
        for record in (tasks or [])[:MAX_TASKS_PER_DEVICE]:
            entry["tasks"].append(
                {"uuid": record.external_id, "payload": record.payload, "media": None, "media_error": None, "track": None, "track_error": None}
            )
        for task_info in entry["tasks"][:MAX_TASKS_WITH_DETAIL_PER_DEVICE]:
            media, media_error = _safe(client.get_flight_task_media, task_info["uuid"])
            task_info["media"], task_info["media_error"] = media, media_error
            track, track_error = _safe(client.get_flight_task_track, task_info["uuid"])
            task_info["track"], task_info["track_error"] = track, track_error
        flight_tasks_by_device[sn] = entry
    overview["flight_tasks_by_device"] = flight_tasks_by_device
    overview["task_lookback_days"] = TASK_LOOKBACK_SECONDS // 86400
    overview["max_tasks_with_detail_per_device"] = MAX_TASKS_WITH_DETAIL_PER_DEVICE

    return overview
