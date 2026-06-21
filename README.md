# 🏆 Mundial Quiniela App

Aplicación de quiniela basada en el Mundial FIFA 2026 con sistema de puntuación por fases.

## Stack

| Capa | Tecnología |
|------|-----------|
| Frontend | React 18 + Vite + TypeScript |
| Estilos | Tailwind CSS |
| Estado | Zustand + React Query |
| i18n | react-i18next (textos de la UI en `frontend/src/i18n/locales/`) |
| Backend | FastAPI + Python 3.12 |
| Base de Datos | PostgreSQL |
| ORM | SQLAlchemy 2.0 (async) |
| Migraciones | Alembic |
| Scheduler | APScheduler (sync datos del Mundial) |
| API Fútbol | API-Football (RapidAPI) |

## Estructura

```
mundial-quiniela/
├── backend/        # FastAPI
├── frontend/       # React + Vite
├── docker-compose.yml
└── README.md
```

## Quick Start

**Requisito**: PostgreSQL instalado y corriendo en el host (la app usa la
instancia nativa del sistema, no un contenedor — los datos no dependen de Docker).

### 1. Crear la base de datos (una sola vez)

```bash
psql -d postgres -c "CREATE ROLE mundial LOGIN PASSWORD 'mundial_pass'"
psql -d postgres -c "CREATE DATABASE mundial_quiniela OWNER mundial"
```

### 2. Configurar variables de entorno

```bash
# Backend
cp backend/.env.example backend/.env
# Edita backend/.env con tus credenciales (API_FOOTBALL_KEY, etc.)

# Frontend
cp frontend/.env.example frontend/.env
```

### 3. Levantar con Docker Compose

```bash
docker compose up -d
```

Las migraciones se aplican automáticamente al arrancar el backend
(que corre con `network_mode: host` para alcanzar el PostgreSQL local).

> **Respaldo**: `pg_dump -h localhost -U mundial mundial_quiniela > backup.sql`

### 4. Crear el primer administrador (opcional)

Los endpoints admin (forzar la sincronización de datos) requieren
un usuario con `is_admin`. Tras registrarte en la app:

```bash
psql -d mundial_quiniela -c "UPDATE users SET is_admin = true WHERE email = 'tu@email.com';"
```

### 5. Levantar manualmente (alternativa a Docker)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8001
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## URLs

| Servicio | URL |
|---------|-----|
| Frontend | http://localhost:5174 |
| Backend API | http://localhost:8001 |
| Swagger Docs | http://localhost:8001/docs |
| ReDoc | http://localhost:8001/redoc |

## Producción

```bash
# 1. Contraseña de la BD (raíz del proyecto)
echo "POSTGRES_PASSWORD=una-contraseña-fuerte" > .env

# 2. Configura backend/.env: SECRET_KEY propio, API_FOOTBALL_KEY, etc.
#    (con APP_ENV=production el SECRET_KEY por defecto bloquea el arranque)

# 3. Levantar (migraciones incluidas; frontend compilado servido por nginx en :80)
docker compose -f docker-compose.prod.yml up -d --build
```

## Tests

```bash
cd backend
pytest
```

## Sistema de Puntuación

> **Los puntos son acumulativos**: se suman según lo que se acierte. Si aciertas
> el **resultado exacto**, sumas su valor **más** el de victoria/empate (acertar
> el exacto implica acertar el resultado); y si aciertas el **primer goleador**,
> también se suma. Ej. (grupos, 2-1 con goleador): 8 + 5 + 3 = **16**.
>
> El **1er gol** se acierta por **jugador** (primer goleador), no por equipo: se
> elige un jugador de las plantillas de los dos equipos del partido y se compara
> por id contra el goleador real.

### Fase de Grupos
| Acierto | Puntos |
|---------|--------|
| Victoria | 5 pts |
| Empate | 6 pts |
| 1er Gol (primer goleador) | 3 pts |
| Resultado Exacto | 8 pts |

### Fases de Eliminación (desde 16avos)
| Acierto | Puntos |
|---------|--------|
| Victoria | 8 pts |
| Empate | 9 pts |
| 1er Gol (primer goleador) | 5 pts |
| Resultado Exacto | 11 pts |
