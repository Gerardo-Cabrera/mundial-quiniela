"""
Tests del parseo de configuración (CORS_ORIGINS, DATABASE_URL).
Regresión: con List[str], pydantic-settings exigía JSON en el .env y el
formato simple (http://localhost:5173) rompía el arranque de la app.
"""
from app.config import Settings


def test_cors_single_origin():
    s = Settings(CORS_ORIGINS="http://localhost:5173")
    assert s.cors_origins_list == ["http://localhost:5173"]


def test_cors_comma_separated():
    s = Settings(CORS_ORIGINS="http://localhost:5173, https://miapp.com")
    assert s.cors_origins_list == ["http://localhost:5173", "https://miapp.com"]


def test_cors_json_format_backwards_compatible():
    s = Settings(CORS_ORIGINS='["http://localhost:5173", "https://miapp.com"]')
    assert s.cors_origins_list == ["http://localhost:5173", "https://miapp.com"]


def test_cors_plain_env_var_does_not_crash(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://a.com,http://b.com")
    s = Settings()
    assert s.cors_origins_list == ["http://a.com", "http://b.com"]


def test_database_url_normalizes_to_asyncpg():
    # Proveedores gestionados (Supabase) entregan 'postgresql://' o 'postgres://';
    # el engine async necesita el driver asyncpg.
    for scheme in ("postgresql", "postgres"):
        s = Settings(DATABASE_URL=f"{scheme}://u:p@host:5432/db")
        assert s.DATABASE_URL == "postgresql+asyncpg://u:p@host:5432/db"


def test_database_url_keeps_explicit_driver():
    url = "postgresql+asyncpg://u:p@host:5432/db"
    assert Settings(DATABASE_URL=url).DATABASE_URL == url
