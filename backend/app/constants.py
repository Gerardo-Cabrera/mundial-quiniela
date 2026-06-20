"""
Constantes compartidas de la aplicación Mundial Quiniela.

Los catálogos de equipos NO se hardcodean aquí, se leen de la BD:

- Equipos de los participantes (con los que se registran los jugadores):
  tabla `participant_teams`, sembrada en la migración 0003 y leída vía
  app/crud/participant_teams.py. Valida el registro y alimenta `GET /config/teams`.

- Selecciones del Mundial FIFA 2026: tabla `teams`, sincronizada desde
  API-Football (app/services/scheduler.sync_teams) y leída vía app/crud/teams.py.
  Así los nombres coinciden EXACTAMENTE con los que devuelve la API para los partidos.
"""
