from typing import Callable, TypeVar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import Base

M = TypeVar("M", bound=Base)


async def upsert_by_key(
    db: AsyncSession,
    model: type[M],
    rows: list[dict],
    key: str,
    *,
    on_update: Callable[[M, dict], None] | None = None,
) -> int:
    """Upsert idempotente de `rows` por el campo único `key`.

    Carga los registros existentes en UNA query y resuelve el upsert en memoria
    Reejecutable sin duplicar. `on_update`, si se pasa, se invoca con 
    (objeto_existente, fila) ANTES de aplicar los cambios para inspeccionar el 
    estado previo (p. ej. detectar un cambio de marcador). Retorna cuántas filas 
    se procesaron.
    """
    if not rows:
        return 0
    result = await db.execute(select(model))
    existing = {getattr(o, key): o for o in result.scalars().all()}
    for row in rows:
        obj = existing.get(row[key])
        if obj is not None:
            if on_update is not None:
                on_update(obj, row)
            for k, v in row.items():
                setattr(obj, k, v)
        else:
            db.add(model(**row))
    await db.flush()
    return len(rows)
