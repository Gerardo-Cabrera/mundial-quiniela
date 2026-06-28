"""
Fixtures compartidos para tests de integración.
Usa una base de datos SQLite en memoria para aislamiento.
"""
import os

# Debe definirse ANTES de importar la app para que Settings lo lea.
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import event, StaticPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.models.team import Team
from app.models.participant_team import ParticipantTeam
from app.models.player import Player

# Selecciones del Mundial usadas por los tests. En producción se sincronizan
# desde API-Football a la tabla `teams`; aquí se siembran unas pocas para aislar
# las pruebas de la red.
SEED_TEAMS = ["Argentina", "Brazil", "France", "Spain", "England", "Mexico"]

# Equipos de los participantes. En producción los siembra la migración 0003 en
# `participant_teams`; aquí se siembran los que usan los tests de registro.
SEED_PARTICIPANT_TEAMS = ["Jax FC", "Genkidama F.C", "Megalink FC", "Soldier Boy"]

# Jugadores (plantillas). En producción los sincroniza el job sync_players a la
# tabla `players`; aquí se siembran unos pocos para los tests de primer goleador.
SEED_PLAYERS = [
    {"api_player_id": 10, "name": "L. Messi", "team_api_id": 1, "team_name": "Argentina"},
    {"api_player_id": 20, "name": "Neymar", "team_api_id": 2, "team_name": "Brazil"},
    {"api_player_id": 30, "name": "T. Müller", "team_api_id": 99, "team_name": "Germany"},
]

engine_test = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
TestSessionLocal = async_sessionmaker(engine_test, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db

# Los jobs del scheduler usan app.database.AsyncSessionLocal DIRECTAMENTE, así 
# que el override de arriba no los cubre. Se reapunta a la BD de test para que 
# cualquier job disparado dentro de un endpoint (p. ej. el backfill que puntúa 
# partidos ya finalizados) use SQLite y no toque la BD real.
import app.services.scheduler as _scheduler_module  # noqa: E402

_scheduler_module.AsyncSessionLocal = TestSessionLocal


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Crea todas las tablas antes de cada test y las elimina después."""
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as session:
        session.add_all([
            Team(api_team_id=i, name=name)
            for i, name in enumerate(SEED_TEAMS, start=1)
        ])
        session.add_all([ParticipantTeam(name=name) for name in SEED_PARTICIPANT_TEAMS])
        session.add_all([Player(**p) for p in SEED_PLAYERS])
        await session.commit()
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    """Cliente HTTP asíncrono para testing de endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient):
    """Cliente autenticado: registra un usuario y retorna el client con token."""
    register_data = {
        "team_name": "Jax FC",
        "email": "test@test.com",
        "password": "testpass123",
    }
    await client.post("/api/auth/register", json=register_data)

    login_data = {"email": "test@test.com", "password": "testpass123"}
    login_resp = await client.post("/api/auth/login", json=login_data)
    token = login_resp.json()["access_token"]

    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest_asyncio.fixture
async def admin_client(auth_client: AsyncClient):
    """Cliente autenticado con privilegios de admin."""
    async with TestSessionLocal() as session:
        user = await session.get(User, 1)
        user.is_admin = True
        await session.commit()
    return auth_client
