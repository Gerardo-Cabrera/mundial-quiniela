#!/bin/sh
# Preparación de arranque, ANTES de la app y en CUALQUIER despliegue (Render,
# docker compose, docker run): Render/Railway pueden sobrescribir el CMD, pero no
# el ENTRYPOINT, así que esto corre siempre sin depender del start command.
set -e

# 1) Migraciones — FATAL: si fallan, la app no arranca (esquema íntegro).
alembic upgrade head

# 2) Aprovisionar las cuentas de los participantes — idempotente (solo crea las
#    que falten) y NO fatal: si falla, se loguea y la API arranca igual. Imprime
#    una línea-resumen greppable: `[create_participant_users] OK — creadas=N …`.
python -m scripts.create_participant_users \
  || echo "[create_participant_users] ADVERTENCIA - el aprovisionamiento de cuentas fallo, la API continua"

exec "$@"
