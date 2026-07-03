---
name: football-pool-quiniela
description: >-
  Playbook para construir o extender una quiniela de predicciones de fútbol
  (Mundial, UEFA Champions League, u otra competición) con FastAPI + SQLAlchemy
  async + PostgreSQL y React + Vite + TS. Úsalo al crear el modelo de datos, el
  motor de puntuación, la sincronización con una API de fútbol, las reglas de
  cierre de pronósticos o las vistas de rankings/estadísticas.
---

# Quiniela de fútbol — playbook

Casi todo el sistema es **independiente de la competición**. Lo único que cambia entre
Mundial y Champions vive en **config**; el resto se reutiliza tal cual.

## 1. Qué se parametriza (config, no código)

- `LEAGUE_ID`, `SEASON`, `TOURNAMENT_TZ` (zona para agrupar por "jornada"/día).
- **Fases** y sus **puntos**: fase de grupos vs eliminatorias pagan distinto. En UCL las
  rondas cambian (league phase + playoffs + octavos…); solo se ajusta el mapeo de
  rondas de la API → fase interna y las tablas de puntos.
- Proveedor de la API de fútbol (host/cabecera/plan) y la fuente de equipos.
- Contraseña inicial / dominio de correos para el aprovisionamiento de cuentas.

## 2. Modelo de datos (núcleo)

- `matches`: `api_fixture_id` (único, clave de upsert), equipos, marcador, **fase** y
  **status** (enum), fecha. Campos opcionales que enriquecen la tarjeta: `elapsed`
  (minuto en vivo), `penalty_home/away` (definición por penales), `first_goal_*`
  (primer goleador real).
- `predictions`: `UNIQUE(user_id, match_id)`, marcador pronosticado + `first_goal_player_id`
  (se puntúa por **id** de jugador, no por nombre), `points_earned`, `is_calculated`.
- `users`/`participant_teams`, `teams`, `players` (plantillas para el selector de
  goleador).

## 3. Motor de puntuación (centralizado)

Reglas en **un solo módulo** (`services/scoring.py`). Componentes **acumulativos**:
acertar el resultado (victoria/empate) suma; el **marcador exacto** suma aparte; el
**primer goleador** suma aparte (comparando `api_player_id`). Tablas distintas para
grupos y eliminatorias. Cambiar los puntos = editar dos dicts.

## 4. Sincronización con la API (scheduler)

- **Adaptativa**: consulta rápido mientras hay un partido EN JUEGO (kickoff pasado y
  aún sin FINISHED) → marcador/minuto/primer gol/FT casi en vivo; espaciada el resto,
  para no malgastar cuota.
- **Upserts idempotentes** por `api_fixture_id`; detecta transiciones a FINISHED para
  encadenar el pipeline post-FT (resolver primer gol → puntuar) sin esperar timers.
- **Robustez**: reintentos con backoff, semáforos para acotar concurrencia,
  `coalesce`+`misfire_grace_time` (tras una pausa del proceso corre lo perdido),
  fallback de finalización para grupos, plazo de gracia para el primer gol.
- `parse_fixture` extrae del **mismo payload** el marcador, `status.elapsed`,
  `score.penalty` y la ronda → fase. Añadir un dato de la API = un campo + parse +
  schema + migración + UI (patrón repetible).

## 5. Reglas de negocio clave

- **Cierre de pronósticos por jornada**: editables hasta **1 h antes del primer
  partido del día** (no por partido), para que nadie espere a ver un partido y ajuste
  los demás del día. La "jornada" = día calendario en `TOURNAMENT_TZ`.
- **Ver pronósticos de otros**: se revelan por **jornada iniciada** (una vez que su
  primer partido comenzó, se ven todos los del día, aunque alguno siga `scheduled`).
- **Cálculo de puntos**: al finalizar un partido se puntúa al instante (pipeline) y un
  timer periódico es el respaldo.

## 6. Vistas de agregación (rankings/estadísticas)

Todas siguen el mismo patrón: **una o dos consultas acotadas + agregación en Python**
(cross-DB; SQLite no tiene funciones de zona horaria). Sin N+1, sin índices extra a
esta escala. Ejemplos: leaderboard, resumen por jornada + MVP, aciertos de primer gol y
de marcador exacto + rankings, marcador más repetido.

## 7. Frontend (patrones a reutilizar)

- **Componentes únicos** compartidos: `MatchDayGrid` (agrupado por día), `MatchCard`,
  `PredictionCard`, `RankingList` (+ `RANK_MEDAL`), `PageLoader`, primitivos `ui`.
- Helpers de dominio en `types`: `groupMatchesByDay` (+ regla de cierre), `isMatchPlayed`,
  `isFirstGoalHit`, `isoDayToDate`.
- **React Query** con `refetchInterval` para lo que cambia en vivo; **Zustand** persistido
  para la sesión; **cierre por inactividad** (hook que mide interacción real, no el
  polling); i18n con `react-i18next`.

## 8. Trampas conocidas (cross-DB / TZ)

- Agrupa por día en la **zona del torneo** en Python (no UTC, no funciones SQL de TZ).
- SQLite devuelve datetimes **naive**; normaliza a UTC-aware con un único helper
  (`as_utc`) antes de comparar/convertir.
- El enum de status se guarda por **nombre** (mayúsculas) en Postgres; compara con el
  enum, no con el string en minúsculas.
- Puntúa el primer goleador por **id**, no por nombre (evita ambigüedad).

## 9. Checklist para una nueva competición (p. ej. UCL)

1. Ajusta `LEAGUE_ID`/`SEASON`/`TOURNAMENT_TZ` y el proveedor de la API.
2. Mapea las rondas de la API a las fases internas y define las tablas de puntos.
3. Siembra `participant_teams` (los equipos de los jugadores de la quiniela).
4. Verifica el fallback de finalización y los plazos según el calendario de la
   competición.
5. El resto (scheduler, scoring, vistas, i18n, auth) se reutiliza sin cambios.
