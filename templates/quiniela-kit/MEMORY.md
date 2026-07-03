# MEMORY.md — semilla de memoria portable

La memoria persiste **hechos** entre sesiones. Separa lo **transferible** (convenciones
de trabajo, abajo — cópialas a cualquier quiniela) de lo **específico del proyecto**
(credenciales, proveedores, red — **re-derívalo por proyecto**, no lo copies a ciegas).

Ubicación en un proyecto nuevo: guarda cada bloque como un archivo en el directorio de
memoria del proyecto y deja este índice como `MEMORY.md` (una línea por memoria).

## Índice (transferibles)

- **docker-no-host-deps** — correr tests/lint/builds vía Docker, no instalar en el host.
- **commit-message-style** — Angular, subject ≤72, cuerpo solo si muy necesario (≤200);
  sin fechas/jugadores/fases; idioma del proyecto sin acentos.
- **no-coauthor-trailer** — NUNCA el trailer "Co-Authored-By: ..." en los commits.
- **no-claude-code-pr-trailer** — NUNCA "Generated with Claude Code" ni atribución en el
  cuerpo de los PR.
- **git-branch-model** — main = estable, develop = desarrollo, integrar por PR
  develop→main; nunca push directo a main.
- **pr-open-immediately** — tras CADA push a develop, verificar con `gh pr list` y abrir
  PR si no hay; no asumir que el push "se suma" a un PR previo (el usuario mergea rápido).
- **code-comments-style** — comentarios claros/directos/precisos; solo lo necesario (el
  porqué no obvio), sin relleno.
- **frontend-i18n** — textos de UI en archivos de traducción (react-i18next), nunca
  hardcodear; usar `t()`.
- **readme-scope** — README = onboarding/setup + puntuación; NO lista vistas (eso vive en
  la doc de detalle); no duplicar.
- **scheduler-stall-heuristic** — un partido colgado "EN VIVO" suele ser sync/fallback vs
  stall del scheduler (suspensión del proceso); revisar primero los logs del scheduler.

## Cuerpos (transferibles)

Cada uno como memoria `feedback`/`reference` con frontmatter `name`/`description`.

- **docker-no-host-deps** (feedback): El proyecto está dockerizado; ejecuta pytest, ruff,
  npm test/lint/build **dentro de los contenedores**. No instales dependencias ni corras
  binarios en el host.
- **commit-message-style** (feedback): Angular `type(scope): subject`, subject ≤72,
  cuerpo ≤200 solo si aporta. Sin acentos. No menciones fechas, jugadores ni fases.
- **no-coauthor-trailer** (feedback): No añadas `Co-Authored-By` a ningún commit.
- **no-claude-code-pr-trailer** (feedback): No añadas atribución a Claude en el cuerpo de
  los PR; termina con el contenido real.
- **git-branch-model** (reference): main default/estable, develop desarrollo. Integra por
  PR develop→main; el usuario mergea.
- **pr-open-immediately** (feedback): Tras cada push a develop, `git fetch origin main` +
  `git log origin/main..origin/develop` + `gh pr list --state open --base main`; si hay
  commits sin PR, abre uno. Nunca digas "esto se suma al PR #N".
- **code-comments-style** (feedback): Comentarios necesarios y precisos; sin redundancia.
- **frontend-i18n** (project): UI text en `src/i18n/locales/`; usa `t()`.
- **readme-scope** (reference): README = setup + puntuación; features en la doc de detalle.
- **scheduler-stall-heuristic** (reference): "EN VIVO" colgado → distinguir sync/fallback
  de un stall del scheduler; mira los logs del scheduler primero.

## NO copiar (re-derivar por proyecto)

Son hechos del entorno concreto; escríbelos de nuevo cuando los descubras:

- **Conexión a la BD** (proveedor gestionado, pooler, driver): depende del hosting.
- **Proveedor/plan de la API de fútbol** (host, cabecera, cuota, acceso a la temporada).
- **Peculiaridades de red del host** (p. ej. VPN/MTU que rompe builds de Docker).
- **Cuentas/seed** concretos (dominios de correo, nombres reales de participantes).
