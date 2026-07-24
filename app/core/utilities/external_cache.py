from __future__ import annotations

import time
from typing import Callable, TypeVar

T = TypeVar("T")

_store: dict[str, tuple[float, object]] = {}


def cached(key: str, ttl_seconds: int, fetch: Callable[[], T]) -> T:
    """Sehr einfacher In-Prozess-Cache mit TTL für schreibgeschützte externe API-Aufrufe (Phase 14:
    DWD-Wetter/OpenSky) -- bewusst kein Redis/DB-Cache für die "schlanke Direktanbindung"-Variante.
    Cacht auch `None`/Fehlerergebnisse von `fetch`, sonst würde ein Ausfall der externen API bei
    mehreren gleichzeitigen Dashboard-Aufrufen keine Schutzwirkung mehr haben. Bekannte Einschränkung:
    bei mehreren Gunicorn-Workern (Produktivbetrieb) hat jeder Worker seinen eigenen Cache -- für die
    geringe Nutzerzahl dieser App als hinnehmbar bewertet, nicht für hohen Traffic gedacht."""
    now = time.monotonic()
    entry = _store.get(key)
    if entry is not None and now - entry[0] < ttl_seconds:
        return entry[1]  # type: ignore[return-value]
    value = fetch()
    _store[key] = (now, value)
    return value


def reset() -> None:
    """Nur für Tests: erzwingt einen frischen `fetch()`-Aufruf beim nächsten `cached()`."""
    _store.clear()
