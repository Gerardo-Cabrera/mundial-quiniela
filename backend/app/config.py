import json
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_SECRET_KEY = "change-me-in-production"


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://mundial:mundial_pass@localhost:5432/mundial_quiniela"

    # Security
    SECRET_KEY: str = INSECURE_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 días

    # API-Football: hay dos formas de acceder a la MISMA API con distinta
    # autenticación. El proveedor cambia host y cabecera:
    #   - "apisports": acceso directo (https://v3.football.api-sports.io,
    #     cabecera 'x-apisports-key'); las keys son de 32 caracteres.
    #   - "rapidapi":  vía RapidAPI (host *.p.rapidapi.com, cabeceras
    #     'X-RapidAPI-Key'/'X-RapidAPI-Host'); las keys son de ~50 caracteres.
    # "auto" deduce el proveedor por el host configurado. Usar el host/cabecera
    # equivocados devuelve 403 Forbidden.
    API_FOOTBALL_KEY: str = ""
    API_FOOTBALL_PROVIDER: str = "auto"  # auto | apisports | rapidapi
    API_FOOTBALL_HOST: str = "v3.football.api-sports.io"
    API_FOOTBALL_TIMEOUT: float = 30.0
    # Mundial FIFA: league ID 1 en API-Football; temporada = año del torneo.
    LEAGUE_ID: int = 1
    SEASON: int = 2026
    # Zona horaria del torneo para agrupar partidos por "jornada" (día). El cierre
    # de pronósticos es 1 h antes del primer partido del día; agrupar en UTC
    # partiría los partidos nocturnos en dos días. IANA (zoneinfo, stdlib).
    TOURNAMENT_TZ: str = "America/Mexico_City"

    # Scheduler intervals
    # (Las selecciones no llevan intervalo: se sincronizan una sola vez al
    # arrancar porque no cambian durante el torneo.)
    SYNC_PLAYERS_HOURS: int = 72  # plantillas: cada ~3 días (cambian por lesiones, altas)
    # Sync de fixtures ADAPTATIVO (ver sync_fixtures): rápido mientras hay un partido
    # EN JUEGO y espaciado el resto, para no malgastar cuota de API.
    SYNC_FIXTURES_MINUTES: int = 1        # cadencia mientras hay un partido en juego (near-real-time)
    SYNC_FIXTURES_IDLE_MINUTES: int = 30  # cadencia de respaldo cuando no hay partidos en juego
    SYNC_GOALS_HOURS: int = 1
    CALC_POINTS_MINUTES: int = 30
    JOB_MAX_RETRIES: int = 3
    JOB_RETRY_DELAY_SECONDS: int = 10
    # Plazo para ejecutar una corrida retrasada (suspensión, reload, pausa del loop)
    # en vez de descartarla, evitando que los datos queden congelados. Mecanismo
    # (coalesce + misfire) detallado en scheduler.py.
    JOB_MISFIRE_GRACE_SECONDS: int = 3600
    # Fallback de finalización: si un partido de FASE DE GRUPOS sigue marcado LIVE
    # pasados estos MINUTOS desde el kickoff, se considera finalizado. 135 min cubre
    # 90' + descanso + añadido + margen, sin finalizar uno que aún va en añadido
    # largo. No aplica a eliminatorias (prórroga/penales pueden superarlo).
    MATCH_FINISH_FALLBACK_MINUTES: int = 135

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "60/minute"
    # Límite más estricto para /auth/* (login y registro): frena ataques de
    # fuerza bruta de credenciales sin molestar al uso legítimo.
    RATE_LIMIT_AUTH: str = "10/minute"
    # Endpoints admin de sync manual: cada llamada consume cuota de API-Football
    # Tope holgado para re-syncs legítimos que frena clics/scripts en ráfaga que 
    # agotarían la cuota.
    RATE_LIMIT_SYNC: str = "10/hour"

    # Scoring: si tras este plazo la API no entrega el primer gol de un partido
    # finalizado, se calculan los puntos sin ese dato para no bloquearlos.
    FIRST_GOAL_GRACE_HOURS: int = 48

    # App
    APP_ENV: str = "development"
    APP_VERSION: str = "1.0.0"
    # str (no List[str]): pydantic-settings exige JSON en env vars para tipos
    # complejos y rompería el arranque con el formato simple del .env.
    CORS_ORIGINS: str = "http://localhost:5174"

    @property
    def cors_origins_list(self) -> list[str]:
        """Acepta lista separada por comas o JSON: ambos formatos de .env funcionan."""
        raw = self.CORS_ORIGINS.strip()
        if raw.startswith("["):
            try:
                return [str(origin) for origin in json.loads(raw)]
            except json.JSONDecodeError:
                pass
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def football_provider(self) -> str:
        """Proveedor efectivo. 'auto' se resuelve por el host (RapidAPI usa
        dominios *.rapidapi.com); cualquier otro host se trata como api-sports."""
        provider = self.API_FOOTBALL_PROVIDER.strip().lower()
        if provider in ("apisports", "rapidapi"):
            return provider
        return "rapidapi" if "rapidapi" in self.API_FOOTBALL_HOST.lower() else "apisports"

    @property
    def football_base_url(self) -> str:
        """URL base v3 según el proveedor."""
        if self.football_provider == "rapidapi":
            return "https://api-football-v1.p.rapidapi.com/v3"
        return "https://v3.football.api-sports.io"

    @property
    def football_headers(self) -> dict[str, str]:
        """Cabeceras de autenticación según el proveedor."""
        if self.football_provider == "rapidapi":
            return {
                "X-RapidAPI-Key": self.API_FOOTBALL_KEY,
                "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com",
            }
        return {"x-apisports-key": self.API_FOOTBALL_KEY}

    # Normaliza el driver de la URL de la BD a asyncpg: los proveedores gestionados
    # (p. ej. Supabase) entregan la cadena como 'postgresql://...' o 'postgres://...',
    # pero el engine async usa el dialecto 'postgresql+asyncpg://'. Se hace strip()
    # primero: un espacio/salto de línea en el .env saltaría el startswith (dejando
    # un driver sync) y, además, rompería la conexión aunque la URL ya fuera asyncpg.
    @field_validator("DATABASE_URL")
    @classmethod
    def _force_asyncpg_driver(cls, v: str) -> str:
        v = v.strip()
        if v.startswith(("postgres://", "postgresql://")):
            v = "postgresql+asyncpg://" + v.split("://", 1)[1]
        return v

    @model_validator(mode="after")
    def _check_production_secret(self) -> "Settings":
        if self.APP_ENV == "production" and self.SECRET_KEY == INSECURE_SECRET_KEY:
            raise ValueError(
                "SECRET_KEY inseguro: define un SECRET_KEY propio en producción (.env)."
            )
        return self

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
