from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ExternalRecord:
    external_id: str
    payload: dict = field(default_factory=dict)


class DJIFlightHubApiError(Exception):
    """Fehler beim Sprechen mit der echten DJI-FlightHub-2-API (Netzwerk, Auth, API-Fehlercode)."""


class DJIFlightHubClient(ABC):
    """Abstrakte Basis für die DJI-FlightHub-2-Anbindung (spec-struktur.md Abschnitt 4).

    Spätere Fachmodule dürfen NIE direkt mit der DJI-API sprechen — immer über diese Schicht
    (Datenfluss: DJI FlightHub 2 -> Integrationsschicht -> interne Datenmodelle -> Services/Fachmodule
    -> Dashboards/UI). Zwei Implementierungen: `MockDJIFlightHubClient` (Demo-Daten, immer verfügbar)
    und `LiveDJIFlightHubClient` (echte Business-OpenAPI, s. `docs/dji-flighthub2-api.md`). Alle
    Methoden hier sind lesend — Endpunkte, die auf echter Hardware wirken (Task anlegen, Gerätebefehle,
    Kamera/RTK/Livestream-Steuerung), sind bewusst noch nicht angebunden.
    """

    @abstractmethod
    def test_connection(self) -> bool:
        ...

    @abstractmethod
    def list_devices(self) -> list[ExternalRecord]:
        """Geräte (Dock+Drohne) organisationsweit. payload enthält die vollen `gateway`/`drone`-Felder."""

    @abstractmethod
    def list_projects(self) -> list[ExternalRecord]:
        ...

    @abstractmethod
    def get_system_status(self) -> dict:
        ...

    @abstractmethod
    def get_device_state(self, device_sn: str) -> dict | None:
        """Volle Telemetrie eines Geräts. Feldumfang ist modellabhängig (Dock 1/2, Matrice-Serie, RC, …)."""

    @abstractmethod
    def get_hms(self, device_sn_list: list[str] | None = None) -> list[ExternalRecord]:
        """Health-Management-Alerts je Gerät. external_id = device_sn, payload = Alert-Liste."""

    @abstractmethod
    def list_flight_tasks(self, sn: str, begin_at: int, end_at: int) -> list[ExternalRecord]:
        """Flugaufgaben eines Docks im Zeitraum [begin_at, end_at] (Unix-Timestamps)."""

    @abstractmethod
    def get_flight_task_media(self, task_uuid: str) -> list[ExternalRecord]:
        ...

    @abstractmethod
    def get_flight_task_track(self, task_uuid: str) -> dict | None:
        ...

    @abstractmethod
    def list_waylines(self) -> list[ExternalRecord]:
        ...
