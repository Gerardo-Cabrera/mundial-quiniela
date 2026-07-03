# Quiniela Agent Kit

Plantillas reutilizables para arrancar una **quiniela de fútbol** de cualquier
competición (Mundial, UEFA Champions League, …) con las mismas convenciones de trabajo
y patrones de arquitectura. Genérico: lo específico de la competición vive en config.

## Archivos

| Archivo | Qué es | Dónde va en el repo nuevo |
|---|---|---|
| `AGENTS.md` | Instrucciones de trabajo del agente (rol, commits, PRs, Docker, lint, i18n, docs) | **Raíz** del repo (Claude Code lo carga solo). También sirve como `CLAUDE.md`. |
| `SKILL.md` | Playbook de dominio (modelo, scoring, sync, reglas, vistas, trampas) | `.claude/skills/football-pool-quiniela/SKILL.md` (skill invocable) |
| `MEMORY.md` | Semilla de memoria: convenciones transferibles + qué re-derivar | Directorio de memoria del proyecto; separa cada bloque en su archivo |

## Cómo usarlo en un proyecto nuevo (p. ej. UCL)

1. Copia `AGENTS.md` a la raíz; copia `SKILL.md` a `.claude/skills/football-pool-quiniela/`.
2. Siembra la memoria con los bloques **transferibles** de `MEMORY.md`; **no** copies los
   marcados como "re-derivar" (BD, proveedor de API, red) — se escriben al descubrirlos.
3. Sigue el **checklist §9 del SKILL** (ajusta `LEAGUE_ID`/`SEASON`/`TOURNAMENT_TZ`, mapeo
   de rondas→fase, tablas de puntos, seed de equipos). El resto del sistema se reutiliza.

## Cómo optimizar el proceso de reutilización

De menos a más automatización:

1. **Separar convenciones de hechos** (lo más importante): las convenciones
   transferibles van en `AGENTS.md` + skill (viajan entre proyectos); los hechos del
   entorno van en **memoria** (por proyecto). Así el kit no arrastra credenciales ni
   detalles de un hosting concreto.
2. **Empaquetar como Claude Code plugin** (marketplace interno): un plugin que traiga el
   skill + settings + hooks (p. ej. un hook que corra ruff/eslint al terminar) se instala
   en cualquier repo con un comando, en vez de copiar archivos a mano.
3. **Repo starter / cookiecutter**: un template con el backend/frontend base ya cableado
   (auth, scheduler, scoring, vistas, CI, Docker) parametrizado por competición
   (`{{league_id}}`, `{{season}}`, `{{timezone}}`, tablas de puntos). `git clone` + rellenar
   variables y tienes la quiniela nueva.
4. **CI compartido**: reutiliza el `ci.yml` (ruff + pytest + eslint + build,
   `permissions: contents: read`, cachés) como workflow reutilizable.
5. **Un skill de scaffolding** que, dado el nombre de la competición y su `LEAGUE_ID`,
   genere la config, el mapeo de fases y el seed — el 90% de lo que cambia entre
   Mundial y UCL.

**Regla de oro**: si algo se repetiría idéntico en la próxima quiniela, va al kit
(AGENTS/skill/plugin); si cambia por competición, va a config; si es del entorno, va a
memoria.
