from __future__ import annotations

from app.integrations.dji_flighthub.base import DJIFlightHubClient, ExternalRecord


class MockDJIFlightHubClient(DJIFlightHubClient):
    """Demo-Connector mit Testdaten (spec-struktur.md Abschnitt 4) — ersetzt die echte Business-API-
    Anbindung, solange keine bestätigten Zugangsdaten/Endpunkte für FireFlight2 vorliegen."""

    def test_connection(self) -> bool:
        return True

    def list_devices(self) -> list[ExternalRecord]:
        return [
            ExternalRecord("mock-device-1", {"model": "DJI M30T", "name": "Demo-Drohne 1", "online": True}),
            ExternalRecord("mock-device-2", {"model": "DJI Mavic 3E", "name": "Demo-Drohne 2", "online": False}),
        ]

    def list_projects(self) -> list[ExternalRecord]:
        return [ExternalRecord("mock-project-1", {"name": "Demo-Projekt"})]
