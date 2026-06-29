#!/bin/sh
# Aplica las migraciones ANTES de arrancar la app (idempotente). Así el esquema
# queda al día en cualquier despliegue —Render, docker compose, docker run— sin
# depender del comando de arranque (Render puede sobrescribir el CMD, pero no el
# ENTRYPOINT). El comando solo necesita lanzar la app.
set -e
alembic upgrade head
exec "$@"
