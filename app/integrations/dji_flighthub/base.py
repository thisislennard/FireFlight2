from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ExternalRecord:
    external_id: str
    payload: dict = field(default_factory=dict)


class DJIFlightHubClient(ABC):
    """Abstrakte Basis für die DJI-FlightHub-2-Anbindung (spec-struktur.md Abschnitt 4).

    Spätere Fachmodule dürfen NIE direkt mit der DJI-API sprechen — immer über diese Schicht
    (Datenfluss: DJI FlightHub 2 -> Integrationsschicht -> interne Datenmodelle -> Services/Fachmodule
    -> Dashboards/UI). In dieser Ausbaustufe gibt es nur `MockDJIFlightHubClient`; eine echte
    Implementierung folgt, sobald Zugangsdaten/Endpunkte bestätigt sind — Referenz dafür:
    FireFlight v1 `docs/FLIGHTHUB2_API.md`.
    """

    @abstractmethod
    def test_connection(self) -> bool:
        ...

    @abstractmethod
    def list_devices(self) -> list[ExternalRecord]:
        ...

    @abstractmethod
    def list_projects(self) -> list[ExternalRecord]:
        ...
