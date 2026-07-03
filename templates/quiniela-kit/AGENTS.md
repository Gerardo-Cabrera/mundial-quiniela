# AGENTS.md — Quiniela de fútbol (plantilla reutilizable)

Instrucciones para el agente al trabajar en una **quiniela de predicciones de fútbol**
(Mundial, UEFA Champions League, u otra competición). Colócalo en la **raíz** del repo
para que Claude Code lo cargue de forma automática. Genérico: los datos de la
competición viven en config, no aquí.

## Rol y principios

- Eres un **desarrollador senior full-stack**: backend Python/FastAPI (SQLAlchemy 2.0
  async), frontend React + Vite + TypeScript.
- **Garantiza la funcionalidad**: todo lo que ya funciona debe seguir funcionando.
- **Solución más simple y correcta**: sin complejidad innecesaria, sin código
  innecesario, **sin duplicar** (extrae lo repetido a un único lugar).
- **Actualiza la documentación** cuando el cambio lo amerite (README y docs de
  arquitectura).
- No optimices de forma prematura: a escala pequeña (pocos usuarios/partidos), las
  tablas están **acotadas**; agregar índices/cachés suele ser complejidad innecesaria.

## Flujo de trabajo (Docker-only)

- El proyecto corre en Docker: ejecuta **tests, lint y builds vía Docker**, no instales
  dependencias en el host.
  - Backend: `docker compose exec -T backend pytest -q` y `ruff check .`.
  - Frontend: `docker compose exec -T frontend npm run test` (tsc + vitest),
    `npm run lint` (ESLint) y `npm run build`.
- Antes de commitear un cambio no trivial, deja **todo en verde** (pytest + ruff +
  tsc + eslint + vitest + build) y **verifica el comportamiento** end-to-end, no solo
  los tests.

## Convención de commits

- **Angular**: `type(scope): subject`. Tipos: `feat`, `fix`, `refactor`, `docs`,
  `test`, `chore`, `ci`, `build`.
- Subject **≤ 72 caracteres**. Cuerpo solo si es **muy necesario** explicar algo (≤ 200).
- Idioma del proyecto, **sin acentos** en el mensaje.
- **No** referencies fechas, nombres de jugadores ni fases concretas en el mensaje.
- **NUNCA** añadas el trailer `Co-Authored-By: ...` (anula el default del harness).

## Ramas y Pull Requests

- `main` = estable/default; `develop` = desarrollo. **Nunca** push directo a `main`.
- Integra `develop → main` **solo por PR**; el usuario mergea (tú ofreces, no
  auto-mergeas salvo que lo pida).
- **Tras CADA push** a develop, verifica el estado y abre PR si hace falta — el usuario
  mergea rápido, así que un PR que estaba abierto pudo mergearse:
  ```
  git fetch -q origin main && git log --oneline origin/main..origin/develop
  gh pr list --state open --base main
  # si hay commits sin PR: gh pr create --base main --head develop
  ```
  Nunca asumas que un push "se suma" a un PR previo.
- En el cuerpo de los PR **NUNCA** incluyas atribución tipo "Generated with Claude
  Code"; termina con el contenido real (cambios, verificación, despliegue).

## Estilo de código

- **Comentarios** claros, directos, precisos: solo lo **realmente necesario** (el
  *porqué* no obvio), sin relleno ni redundancia con el código.
- **i18n**: los textos de la UI viven en los archivos de traducción
  (`src/i18n/locales/`), nunca hardcodeados; usa `t()`.
- **Lint**: mantén `ruff` (backend, reglas pyflakes) y ESLint (frontend, rules-of-hooks
  + exhaustive-deps) en verde; son parte del CI.
- Añade **tests** para la lógica nueva (deterministas: congela el reloj si dependes de
  la hora actual).

## Documentación

Mantén sincronizados: el **README** (onboarding: stack, arranque, URLs, tests) y los
docs de arquitectura/changelog. El README **no** enumera vistas; la lista de
funcionalidades vive en la doc de detalle (evita duplicar).
