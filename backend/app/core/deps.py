from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jwt import InvalidTokenError
from app.database import get_db
from app.core.security import decode_token
from app.models.user import User

# HTTPBearer (no OAuth2): en Swagger el botón «Authorize» pide solo el token
# (un campo «Value»), sin client_id/client_secret. auto_error=False para que la
# ausencia de cabecera devuelva 401 (no el 403 por defecto), conservando el
# contrato que ya espera el frontend y los tests.
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise credentials_exception
    try:
        payload = decode_token(credentials.credentials)
        raw_sub = payload.get("sub")
        if raw_sub is None:
            raise credentials_exception
        user_id = int(raw_sub)
    # ValueError: un sub no numérico debe dar 401, no un 500 sin capturar.
    except (InvalidTokenError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Acceso denegado")
    return current_user
