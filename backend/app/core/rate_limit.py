"""
Limiter compartido de slowapi.

Vive en su propio módulo (y no en main.py) para que los routers puedan aplicar
límites por ruta —p. ej. `@limiter.limit(...)` en `/auth/*`— sin provocar un
import circular con la app.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    enabled=settings.RATE_LIMIT_ENABLED,
)
