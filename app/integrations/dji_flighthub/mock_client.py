from __future__ import annotations

from app.integrations.dji_flighthub.base import DJIFlightHubClient, ExternalRecord

_PROJECT_A = "93df839d-ae74-4f04-842e-2f1f81c89a66"
_PROJECT_B = "a1b2c3d4-1111-2222-3333-444455556666"
_DOCK_SN = "7CTDM3D00BZNVZ"
_DRONE_SN = "1581F6Q8D242100CPWEK"
_HANDHELD_SN = "0M3SEC1234A5678"
_TASK_UUID = "3f8c9e10-3a4a-4e4e-9b8e-6f0b4a7c9d21"
_WAYLINE_ID = "be903684-5423-45b9-b81d-0df2824be6f9"

_DOCK_RECORD = {
    "gateway": {
        "sn": _DOCK_SN,
        "callsign": "Dock Gerätehaus",
        "device_model": {"key": "3-2-0", "name": "DJI Dock 2", "class": "airport"},
        "device_online_status": True,
        "mode_code": 0,
        "camera_list": [{"camera_index": "165-0-7", "available_camera_positions": ["indoor", "outdoor"], "camera_position": "outdoor"}],
    },
    "drone": {
        "sn": _DRONE_SN,
        "callsign": "M3TD-01",
        "device_model": {"key": "0-91-1", "name": "DJI Matrice 3TD", "class": "drone"},
        "device_online_status": True,
        "mode_code": 0,
        "camera_list": [{"camera_index": "81-0-0", "lens_list": [{"available_lens_types": ["normal", "wide", "zoom", "ir"], "lens_type": "wide"}]}],
    },
}
_HANDHELD_RECORD = {
    "drone": {
        "sn": _HANDHELD_SN,
        "callsign": "Mavic-3E-Handheld",
        "device_model": {"key": "0-77-0", "name": "DJI Mavic 3E", "class": "drone"},
        "device_online_status": False,
        "mode_code": 0,
        "camera_list": [{"camera_index": "66-0-0", "lens_list": [{"available_lens_types": ["normal", "zoom"], "lens_type": "normal"}]}],
    }
}


class MockDJIFlightHubClient(DJIFlightHubClient):
    """Demo-Connector mit Testdaten (spec-struktur.md Abschnitt 4) — Feldform bewusst identisch zu
    `LiveDJIFlightHubClient`, damit die Integrations-Oberfläche auch ohne echte Zugangsdaten den
    vollen Funktionsumfang zeigt. Bildet zwei Projekte ab (eines mit Dock+Drohne und vollen
    Flugdaten, eines mit einer reinen Handheld-Drohne ohne Dock/Flugaufgaben), um die
    projektübergreifende Übersicht realistisch zu demonstrieren."""

    def test_connection(self) -> bool:
        return True

    def list_projects(self) -> list[ExternalRecord]:
        return [
            ExternalRecord(
                _PROJECT_A,
                {
                    "name": "Feuerwehr Liederbach",
                    "introduction": "Demo-Projekt (Mock-Connector)",
                    "uuid": _PROJECT_A,
                    "created_at": 1737331200,
                    "updated_at": 1737331200,
                    "project_work_center_point": {"latitude": 50.1155, "longitude": 8.4569},
                },
            ),
            ExternalRecord(
                _PROJECT_B,
                {
                    "name": "Übungsgelände Nord",
                    "introduction": "Zweites Demo-Projekt — zeigt projektübergreifende Abfrage (Mock-Connector)",
                    "uuid": _PROJECT_B,
                    "created_at": 1737331200,
                    "updated_at": 1737331200,
                    "project_work_center_point": {"latitude": 50.1450, "longitude": 8.4700},
                },
            ),
        ]

    def list_devices(self) -> list[ExternalRecord]:
        return [ExternalRecord(_DOCK_SN, _DOCK_RECORD), ExternalRecord(_HANDHELD_SN, _HANDHELD_RECORD)]

    def list_project_devices(self, project_uuid: str) -> list[ExternalRecord]:
        if project_uuid == _PROJECT_A:
            return [ExternalRecord(_DOCK_SN, _DOCK_RECORD)]
        if project_uuid == _PROJECT_B:
            return [ExternalRecord(_HANDHELD_SN, _HANDHELD_RECORD)]
        return []

    def get_system_status(self) -> dict:
        return {"code": 0, "message": "OK (Mock-Connector, keine echte Verbindung)"}

    def get_device_state(self, project_uuid: str, device_sn: str) -> dict | None:
        if project_uuid != _PROJECT_A or device_sn != _DOCK_SN:
            return None
        return {
            "device_sn": _DOCK_SN,
            "device_model": {"key": "3-2-0", "name": "DJI Dock 2", "class": "airport"},
            "device_state": {
                "firmware_version": "10.02.0301",
                "battery_capacity_percent": 100,
                "network_state": {"type": "4g", "quality": 5},
                "storage": {"total": 256000, "used": 41200},
                "position": {"latitude": 50.1155, "longitude": 8.4569, "height": 165.2},
                "note": "Feldform je Gerätemodell unterschiedlich — hier nur ein Beispielausschnitt (Mock)",
            },
        }

    def get_hms(self, project_uuid: str, device_sn_list: list[str] | None = None) -> list[ExternalRecord]:
        if project_uuid != _PROJECT_A:
            return []
        return [
            ExternalRecord(
                _DOCK_SN,
                {
                    "list": [
                        {
                            "level": "reminder",
                            "module": "device_management",
                            "in_the_key": "on_the_ground",
                            "code": "0x1A2B0001",
                            "message": "Routinewartung in 12 Tagen fällig (Mock-Beispiel)",
                            "imminent": False,
                        }
                    ]
                },
            ),
        ]

    def list_flight_tasks(self, project_uuid: str, sn: str, begin_at: int, end_at: int) -> list[ExternalRecord]:
        if project_uuid != _PROJECT_A or sn != _DOCK_SN:
            return []
        return [
            ExternalRecord(
                _TASK_UUID,
                {
                    "name": "Übungsflug Gerätehaus",
                    "uuid": _TASK_UUID,
                    "task_type": "immediate",
                    "status": "success",
                    "sn": _DOCK_SN,
                    "wayline_uuid": _WAYLINE_ID,
                    "begin_at": begin_at,
                    "end_at": end_at,
                    "run_at": begin_at,
                    "completed_at": end_at,
                    "current_waypoint_index": 5,
                    "total_waypoints": 5,
                },
            )
        ]

    def get_flight_task_media(self, project_uuid: str, task_uuid: str) -> list[ExternalRecord]:
        if project_uuid != _PROJECT_A or task_uuid != _TASK_UUID:
            return []
        return [
            ExternalRecord(
                "8a2f3c10-media-0001",
                {
                    "name": "DJI_20260722090000_0001_V.jpeg",
                    "file_type": "image",
                    "suffix": "jpeg",
                    "size": 8_200_000,
                    "preview_url": "",
                    "original_url": "",
                    "create_at": "2026-07-22T09:00:00Z",
                },
            )
        ]

    def get_flight_task_track(self, project_uuid: str, task_uuid: str) -> dict | None:
        if project_uuid != _PROJECT_A or task_uuid != _TASK_UUID:
            return None
        return {
            "name": "Übungsflug Gerätehaus",
            "status": "success",
            "wayline_uuid": _WAYLINE_ID,
            "track": {
                "track_id": "mock-track-0001",
                "drone_sn": _DRONE_SN,
                "flight_distance": 842,
                "flight_duration": 320,
                "points": [
                    {"timestamp": 1737529200, "latitude": 50.1155, "longitude": 8.4569, "height": 0},
                    {"timestamp": 1737529260, "latitude": 50.1161, "longitude": 8.4578, "height": 45.2},
                    {"timestamp": 1737529320, "latitude": 50.1149, "longitude": 8.4583, "height": 48.0},
                ],
            },
        }

    def list_waylines(self, project_uuid: str) -> list[ExternalRecord]:
        if project_uuid != _PROJECT_A:
            return []
        return [
            ExternalRecord(
                _WAYLINE_ID,
                {
                    "id": _WAYLINE_ID,
                    "name": "Standardroute Gerätehaus",
                    "device_model_key": "0-91-1",
                    "template_types": ["waypoint"],
                    "update_time": 1737331200,
                    "payload_information": [{"domain": "1", "type": "81", "lens_type": "wide"}],
                },
            )
        ]

    def start_livestream(
        self, project_uuid: str, sn: str, camera_index: str, quality_type: str = "adaptive", video_expire: int = 3600
    ) -> dict:
        return {
            "url": "",
            "url_type": "mock",
            "expire_ts": 0,
            "message": "Mock-Connector: kein echtes Gerät verbunden, daher keine echte Stream-URL.",
        }
