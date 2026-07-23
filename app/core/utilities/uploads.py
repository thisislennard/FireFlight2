from __future__ import annotations

import uuid
from pathlib import Path

from flask import current_app
from werkzeug.datastructures import FileStorage

from app.core.exceptions import ValidationError

# Magic-Bytes statt Dateiendung/Content-Type des Clients -- beides ist frei fälschbar. Deckt die
# einzigen Formate ab, die wir akzeptieren; erkennt nebenbei z. B. eine als ".jpg" umbenannte SVG
# (potenzieller Stored-XSS-Vektor, da SVG Skripte enthalten kann) zuverlässig als "kein Bild".
_IMAGE_SIGNATURES: dict[bytes, str] = {
    b"\x89PNG\r\n\x1a\n": "png",
    b"\xff\xd8\xff": "jpg",
    b"RIFF": "webp",  # zusätzlich unten auf "WEBP" ab Byte 8 geprüft (RIFF ist ein Container-Format)
}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
# Alias -- Name aus Phase 7, an dem tests/test_profile.py hängt; MAX_IMAGE_BYTES ist der allgemeinere
# Name, seit auch Ticket-Anhänge (Phase 10) dieselbe Grenze nutzen.
MAX_PROFILE_IMAGE_BYTES = MAX_IMAGE_BYTES


def _sniff_extension(header: bytes) -> str | None:
    if header[:8] == b"RIFF" + header[4:8] and header[8:12] == b"WEBP":
        return "webp"
    for signature, ext in _IMAGE_SIGNATURES.items():
        if signature != b"RIFF" and header.startswith(signature):
            return ext
    return None


def _validated_extension(file: FileStorage) -> str:
    """Gemeinsame Validierung für alle Bild-Uploads (Profilbild, Ticket-Anhänge): liest Größe +
    Magic-Bytes, wirft ValidationError bei leerem/zu großem/nicht erkanntem Inhalt, gibt sonst die
    erkannte Dateiendung zurück."""
    header = file.stream.read(16)
    file.stream.seek(0, 2)
    size = file.stream.tell()
    file.stream.seek(0)

    if size == 0:
        raise ValidationError("Die Datei ist leer.")
    if size > MAX_IMAGE_BYTES:
        raise ValidationError("Das Bild darf höchstens 5 MB groß sein.")

    ext = _sniff_extension(header)
    if ext is None:
        raise ValidationError("Nur PNG-, JPEG- oder WebP-Bilder sind erlaubt.")
    return ext


def profile_image_dir() -> Path:
    """Liegt bewusst unter `instance_path`, nicht `app/static/` -- Nutzerinhalte sollen getrennt vom
    versionierten App-Code bleiben. In Docker über ein eigenes Volume persistiert (docker-compose.yml:
    fireflight2-uploads-data), sonst gingen Profilbilder bei jedem Image-Rebuild verloren."""
    path = Path(current_app.instance_path) / "uploads" / "profile_images"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_profile_image(user, file: FileStorage) -> None:
    """Validiert per Magic-Bytes (nicht Dateiendung/Content-Type) und speichert unter einem
    server-generierten Dateinamen `<user_id>.<ext>` -- ein User hat immer höchstens ein Profilbild,
    ein erneuter Upload ersetzt es. Wirft ValidationError bei leerem/zu großem/nicht erkanntem Inhalt."""
    ext = _validated_extension(file)
    delete_profile_image(user)
    target = profile_image_dir() / f"{user.id}.{ext}"
    file.save(target)
    user.profile_image_filename = target.name

    from app.extensions import db

    db.session.commit()


def delete_profile_image(user) -> None:
    if user.profile_image_filename:
        old_path = profile_image_dir() / user.profile_image_filename
        old_path.unlink(missing_ok=True)
        user.profile_image_filename = None

    from app.extensions import db

    db.session.commit()


def profile_image_path(user) -> Path | None:
    if not user.profile_image_filename:
        return None
    path = profile_image_dir() / user.profile_image_filename
    return path if path.is_file() else None


def ticket_attachment_dir() -> Path:
    """Analog zu profile_image_dir(), aber ein Ticket kann beliebig viele Anhänge haben -- daher
    zufällige Dateinamen statt eines festen Slots pro Datensatz (app/modules/tickets/)."""
    path = Path(current_app.instance_path) / "uploads" / "ticket_attachments"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_ticket_attachment_file(file: FileStorage) -> str:
    """Validiert wie save_profile_image() per Magic-Bytes und speichert unter einem zufälligen
    Dateinamen. Gibt nur den Dateinamen zurück -- das Anlegen der TicketAttachment-Zeile (mit
    Original-Dateiname fürs Anzeigen) ist Sache von app/modules/tickets/services.py."""
    ext = _validated_extension(file)
    filename = f"{uuid.uuid4()}.{ext}"
    file.save(ticket_attachment_dir() / filename)
    return filename


def ticket_attachment_path(filename: str) -> Path | None:
    path = ticket_attachment_dir() / filename
    return path if path.is_file() else None


def delete_ticket_attachment_file(filename: str) -> None:
    (ticket_attachment_dir() / filename).unlink(missing_ok=True)
