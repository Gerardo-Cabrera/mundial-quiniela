FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Correr sin privilegios (en dev el volumen montado solo requiere lectura).
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# El entrypoint aplica `alembic upgrade head` antes de cualquier comando, así las
# migraciones corren solas en todo despliegue (no dependen del start command de
# Render/Railway). Se invoca con `sh` para no depender del bit de ejecución (el
# bind mount de dev sobreescribe /app con el dir del host). El CMD puede
# sobrescribirse (compose, Render) sin perder las migraciones.
ENTRYPOINT ["sh", "/app/docker-entrypoint.sh"]
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
