def test_mock_client_lists_devices():
    from app.integrations.dji_flighthub.mock_client import MockDJIFlightHubClient

    client = MockDJIFlightHubClient()
    assert client.test_connection() is True
    devices = client.list_devices()
    assert len(devices) >= 1


def test_simulated_sync_creates_run_and_external_references(app, organization):
    from app.integrations.dji_flighthub.models import ExternalReference
    from app.integrations.dji_flighthub.service import get_or_create_config, run_sync

    config = get_or_create_config(organization.id)
    run = run_sync(config, simulated=True)

    assert run.status == "success"
    assert run.records_processed > 0
    assert run.is_simulated is True
    assert ExternalReference.query.filter_by(organization_id=organization.id, source="DJI_FLIGHTHUB").count() == run.records_processed
