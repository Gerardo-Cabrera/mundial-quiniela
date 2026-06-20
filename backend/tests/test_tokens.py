"""
Tests de validación de tokens JWT (migración python-jose → PyJWT).
Todo token inválido debe producir 401, nunca un 500.
"""
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from httpx import AsyncClient

from app.config import settings
from app.core.security import create_access_token, decode_token


def test_token_roundtrip():
    token = create_access_token({"sub": "42"})
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert "exp" in payload


def test_decode_rejects_expired_token():
    expired = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(expired)


@pytest.mark.asyncio
async def test_garbage_token_returns_401(client: AsyncClient):
    client.headers["Authorization"] = "Bearer no-soy-un-jwt"
    resp = await client.get("/api/matches/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_expired_token_returns_401(client: AsyncClient):
    expired = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    client.headers["Authorization"] = f"Bearer {expired}"
    resp = await client.get("/api/matches/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_wrong_signature_returns_401(client: AsyncClient):
    forged = jwt.encode(
        {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "otra-clave-distinta",
        algorithm=settings.ALGORITHM,
    )
    client.headers["Authorization"] = f"Bearer {forged}"
    resp = await client.get("/api/matches/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_non_numeric_sub_returns_401(client: AsyncClient):
    """Regresión: un sub no numérico lanzaba ValueError sin capturar (500)."""
    token = create_access_token({"sub": "no-numerico"})
    client.headers["Authorization"] = f"Bearer {token}"
    resp = await client.get("/api/matches/")
    assert resp.status_code == 401
