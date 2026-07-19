from __future__ import annotations

from datetime import datetime, timezone

from flask import current_app
from flask_login import current_user

from app.extensions import db
from app.integrations.dji_flighthub.base import DJIFlightHubClient, ExternalRecord
from app.integrations.dji_flighthub.mock_client import MockDJIFlightHubClient
from app.integrations.dji_flighthub.models import ExternalReference, IntegrationConfig, IntegrationSyncRun

INTEGRATION_KEY = "dji_flighthub"


def get_or_create_config(organization_id) -> IntegrationConfig:
    config = IntegrationConfig.query.filter_by(
        organization_id=organization_id, integration_key=INTEGRATION_KEY
    ).first()
    if config is None:
        config = IntegrationConfig(organization_id=organization_id, integration_key=INTEGRATION_KEY)
        db.session.add(config)
        db.session.commit()
    return config


def get_client() -> DJIFlightHubClient:
    # Echte Anbindung folgt erst, sobald DJI-Zugangsdaten/Endpunkte bestätigt sind (s. Modul-Docstring).
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
        client = get_client()
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
