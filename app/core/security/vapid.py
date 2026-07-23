"""Erzeugung von VAPID-Schlüsselpaaren für Web-Push (app/notifications/). Rohes, base64url-kodiertes
Format statt PEM -- kompatibel sowohl mit `PushManager.subscribe({applicationServerKey: ...})` im
Browser (Public Key) als auch direkt mit `pywebpush.webpush(vapid_private_key=...)` (Private Key,
via `py_vapid.Vapid.from_string`)."""
from __future__ import annotations

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from py_vapid import Vapid02
from py_vapid.utils import b64urlencode, num_to_bytes


def generate_vapid_keypair() -> tuple[str, str]:
    """Gibt (public_key, private_key) als rohe base64url-Strings zurück."""
    vapid = Vapid02()
    vapid.generate_keys()

    public_key = b64urlencode(
        vapid.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    )
    private_key = b64urlencode(num_to_bytes(vapid.private_key.private_numbers().private_value, 32))
    return public_key, private_key
