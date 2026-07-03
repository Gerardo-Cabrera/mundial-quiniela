from datetime import datetime, timezone


def as_utc(dt: datetime) -> datetime:
    """Normaliza un datetime a UTC-aware. SQLite devuelve valores naive y PostgreSQL
    aware; asumir UTC en los naive evita comparar naive con aware (TypeError)."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
