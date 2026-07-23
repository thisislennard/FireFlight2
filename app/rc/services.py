from __future__ import annotations

import secrets
import uuid

from app.core.models import utcnow
from app.core.security.passwords import hash_device_key, verify_device_key
from app.extensions import db
from app.rc.models import RcDevice

DEVICE_KEY_VALID_QUALIFICATIONS = ("pilot", "camera_operator")


def create_device(
    organization_id: uuid.UUID, *, label: str, required_qualification: str | None = None
) -> tuple[RcDevice, str]:
    """Legt ein neues RC-Gerät an und gibt den Klartext-Geräteschlüssel EINMALIG zurück -- danach ist
    nur noch der Hash gespeichert (kein Wiederherstellen, nur `regenerate_device_key()`)."""
    device_key = secrets.token_urlsafe(24)
    device = RcDevice(
        organization_id=organization_id,
        label=label,
        required_qualification=required_qualification or None,
        device_key_hash=hash_device_key(device_key),
    )
    db.session.add(device)
    db.session.commit()
    return device, device_key


def regenerate_device_key(device: RcDevice) -> str:
    """Invalidiert den bisherigen Geräteschlüssel (z. B. bei Verlust/Diebstahl) -- das Gerät muss
    danach über `/rc/pair` neu gekoppelt werden, die bestehende Cookie-Session wird ungültig."""
    device_key = secrets.token_urlsafe(24)
    device.device_key_hash = hash_device_key(device_key)
    device.paired_at = None
    device.last_seen_at = None
    db.session.commit()
    return device_key


def resolve_device_by_key(raw_key: str) -> RcDevice | None:
    """Sucht unter allen aktiven Geräten eines mit passendem Schlüssel. Iteriert bewusst über alle
    (statt Hash als Lookup-Key) -- die Anzahl physischer RC-Geräte pro Feuerwehr ist klein (allenfalls
    einige Dutzend), ein Werkzeug-Hash ist konstruktionsbedingt nicht direkt vergleichbar."""
    if not raw_key:
        return None
    for device in RcDevice.query.filter_by(is_active=True).all():
        if verify_device_key(device.device_key_hash, raw_key):
            return device
    return None


def mark_paired(device: RcDevice) -> None:
    now = utcnow()
    device.last_seen_at = now
    if device.paired_at is None:
        device.paired_at = now
    db.session.commit()


def list_devices(organization_id: uuid.UUID) -> list[RcDevice]:
    return RcDevice.query.filter_by(organization_id=organization_id).order_by(RcDevice.label).all()


def deactivate_device(device: RcDevice) -> None:
    device.is_active = False
    db.session.commit()


def activate_device(device: RcDevice) -> None:
    device.is_active = True
    db.session.commit()
