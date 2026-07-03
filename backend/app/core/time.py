from datetime import datetime, timezone


def as_utc(dt: datetime) -> datetime:
    """Devuelve `dt` en UTC-aware: si es naive (SQLite los entrega así) asume UTC; si
    ya es aware, lo convierte a UTC. Garantiza el resultado en UTC (fiel al nombre) y
    evita comparar naive con aware (TypeError)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
