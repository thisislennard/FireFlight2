from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
import uuid

from app.integrations.dji_flighthub.base import DJIFlightHubApiError, DJIFlightHubClient, ExternalRecord

_API_PREFIX = "/openapi/v0.1"
_REQUEST_TIMEOUT_SECONDS = 10


class LiveDJIFlightHubClient(DJIFlightHubClient):
    """Echte Anbindung an die DJI-FlightHub-2-Business-OpenAPI (s. `docs/dji-flighthub2-api.md`).

    Ein Organization Key deckt die ganze Organisation ab, `project_uuid` wird pro Aufruf übergeben
    (nicht im Konstruktor fest verdrahtet), da eine Organisation mehrere Projekte haben kann. Nur
    lesende Endpunkte — Task anlegen, Gerätebefehle, Kamera-/RTK-/Livestream-Steuerung sind bewusst
    nicht angebunden (s. Modul-Docstring in `base.py`)."""

    def __init__(self, base_url: str, org_key: str, language: str = "en") -> None:
        self._base_url = base_url.rstrip("/")
        self._org_key = org_key
        self._language = language

    def _request(self, path: str, params: dict | None = None, project_uuid: str | None = None) -> dict | list:
        url = f"{self._base_url}{_API_PREFIX}{path}"
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            if clean:
                url = f"{url}?{urllib.parse.urlencode(clean)}"
        headers = {
            "X-User-Token": self._org_key,
            "X-Request-Id": str(uuid.uuid4()),
            "X-Language": self._language,
            "Accept": "application/json",
        }
        if project_uuid:
            headers["X-Project-Uuid"] = project_uuid
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT_SECONDS) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                pass
            if exc.code == 401:
                raise DJIFlightHubApiError("Authentifizierung fehlgeschlagen (401) — Organization Key prüfen.") from exc
            if exc.code == 403:
                raise DJIFlightHubApiError("Zugriff verweigert (403) — Projekt-Berechtigungen prüfen.") from exc
            if exc.code == 404:
                raise DJIFlightHubApiError(f"Endpunkt nicht gefunden (404): {path}") from exc
            raise DJIFlightHubApiError(f"HTTP-Fehler {exc.code}: {exc.reason}{(' – ' + body) if body else ''}") from exc
        except urllib.error.URLError as exc:
            reason = str(exc.reason)
            if "timed out" in reason.lower():
                raise DJIFlightHubApiError(f"Zeitüberschreitung — Server antwortet nicht: {self._base_url}") from exc
            raise DJIFlightHubApiError(f"Netzwerkfehler: {reason}") from exc

        if raw.lstrip().startswith("<!DOCTYPE") or raw.lstrip().startswith("<html"):
            raise DJIFlightHubApiError(
                "Server antwortete mit einer HTML-Seite statt JSON — Basis-URL zeigt vermutlich auf die "
                "Web-Oberfläche statt auf den API-Server."
            )
        try:
            body = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DJIFlightHubApiError(f"Unerwartetes Antwortformat (kein JSON): {raw[:120]}") from exc

        code = body.get("code")
        if code not in (0, None):
            raise DJIFlightHubApiError(f"DJI-API-Fehler {code}: {body.get('message', '')}")
        return body.get("data", {})

    def test_connection(self) -> bool:
        self._request("/project", params={"usage": "simple"})
        return True

    def list_projects(self) -> list[ExternalRecord]:
        data = self._request("/project")
        items = (data or {}).get("list") or []
        return [ExternalRecord(item.get("uuid", ""), item) for item in items]

    def list_devices(self) -> list[ExternalRecord]:
        data = self._request("/device")
        items = (data or {}).get("list") or []
        records = []
        for item in items:
            sn = ((item.get("gateway") or {}).get("sn")) or ((item.get("drone") or {}).get("sn")) or ""
            records.append(ExternalRecord(sn, item))
        return records

    def list_project_devices(self, project_uuid: str) -> list[ExternalRecord]:
        data = self._request("/project/device", project_uuid=project_uuid)
        items = (data or {}).get("list") or []
        records = []
        for item in items:
            sn = ((item.get("gateway") or {}).get("sn")) or ((item.get("drone") or {}).get("sn")) or ""
            records.append(ExternalRecord(sn, item))
        return records

    def get_system_status(self) -> dict:
        return self._request("/system_status")

    def get_device_state(self, project_uuid: str, device_sn: str) -> dict | None:
        try:
            return self._request(f"/device/{urllib.parse.quote(device_sn)}/state", project_uuid=project_uuid)
        except DJIFlightHubApiError:
            return None

    def get_hms(self, project_uuid: str, device_sn_list: list[str] | None = None) -> list[ExternalRecord]:
        params = {"device_sn_list": ",".join(device_sn_list)} if device_sn_list else None
        data = self._request("/device/hms", params=params, project_uuid=project_uuid)
        items = (data or {}).get("list") or []
        return [ExternalRecord(item.get("device_sn", ""), item) for item in items]

    def list_flight_tasks(self, project_uuid: str, sn: str, begin_at: int, end_at: int) -> list[ExternalRecord]:
        data = self._request(
            "/flight-task/list", params={"sn": sn, "begin_at": begin_at, "end_at": end_at}, project_uuid=project_uuid
        )
        items = (data or {}).get("list") or []
        return [ExternalRecord(item.get("uuid", ""), item) for item in items]

    def get_flight_task_media(self, project_uuid: str, task_uuid: str) -> list[ExternalRecord]:
        data = self._request(f"/flight-task/{urllib.parse.quote(task_uuid)}/media", project_uuid=project_uuid)
        items = (data or {}).get("list") or []
        return [ExternalRecord(item.get("uuid", ""), item) for item in items]

    def get_flight_task_track(self, project_uuid: str, task_uuid: str) -> dict | None:
        try:
            return self._request(f"/flight-task/{urllib.parse.quote(task_uuid)}/track", project_uuid=project_uuid)
        except DJIFlightHubApiError:
            return None

    def list_waylines(self, project_uuid: str) -> list[ExternalRecord]:
        data = self._request("/wayline", project_uuid=project_uuid)
        items = (data or {}).get("list") or []
        return [ExternalRecord(item.get("id", ""), item) for item in items]
