"""
Carga pronósticos desde notas de texto (estilo WhatsApp) usando el backfill.

Parsea uno o más archivos de notas, mapea cada participante a su equipo, busca el
partido por los equipos (tolerante a la zona horaria: el match se identifica por el
PAR de equipos, único en fase de grupos), resuelve el primer goleador contra la
plantilla del partido y carga todo de forma idempotente. Reutiliza la lógica
existente (crud + pipeline de puntos del scheduler + `email_for`); no la duplica.

Sirve para CUALQUIER fecha: re-ejecútalo a medida que lleguen más notas. Los
usuarios nuevos (que no existan aún) se crean con la contraseña inicial compartida.

Lo MANUAL vive en archivos aparte:
  - mapeo/sobrenombres: `scripts/backfill_aliases.py` (edítalo);
  - lo que el script no pueda resolver (goleadores, líneas ilegibles, participantes
    sin mapear) se vuelca en un archivo de reporte (--report).

Uso (desde backend/, local o con DATABASE_URL apuntando a Supabase para prod):

    python -m scripts.backfill_predictions --notes ruta/al/dir_o_archivo [--dry-run]
    python -m scripts.backfill_predictions --notes notas/ --report revisar.txt

⚠️ Idempotente (upsert por usuario+partido): reenviar corrige. Con --dry-run solo
parsea y reporta, sin escribir.
"""
import argparse
import asyncio
import difflib
import logging
import re
import unicodedata
from pathlib import Path

from app.core.security import hash_password
from app.crud import (
    match_crud, participant_team_crud, player_crud, prediction_crud, user_crud,
)
from app.database import AsyncSessionLocal
from app.models.match import Match, MatchStatus
from app.models.participant_team import ParticipantTeam
from app.services.scheduler import calculate_pending_points, sync_first_goals
from scripts.backfill_aliases import PARTICIPANT_TEAM, SCORER_ALIASES, TEAM_ES_EN
from scripts.create_participant_users import DEFAULT_DOMAIN, DEFAULT_PASSWORD, email_for

logging.disable(logging.INFO)  # silencia el echo de SQLAlchemy

_DATE_RE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")
_SCORER_PREFIX = re.compile(r"^\s*(primer\s+gol|gol)\s*:?\s*", re.IGNORECASE)
# Claves de equipo más largas primero, para que "corea del sur" gane a "corea".
_TEAM_KEYS = sorted(TEAM_ES_EN, key=len, reverse=True)


def _strip_accents(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def _norm_alnum(s: str) -> str:
    return "".join(c for c in _strip_accents(s).lower() if c.isalnum())


def _norm_text(s: str) -> str:
    """minúsculas, sin acentos, solo [a-z0-9 ] (para detectar equipos en una línea)."""
    return "".join(c if c.isalnum() else " " for c in _strip_accents(s).lower())


def _find_teams(line: str) -> list[str]:
    """Equipos (nombre EN de la BD) mencionados en la línea, en orden de aparición.
    Los paréntesis son anotaciones ("(penal para Argentina)"), no datos: se quitan
    para no confundir una línea de goleador con un partido."""
    t = f" {_norm_text(re.sub(r'\(.*?\)', ' ', line))} "
    used = [False] * len(t)
    found: list[tuple[int, str]] = []
    for key in _TEAM_KEYS:
        idx = t.find(f" {key} ")
        if idx != -1 and not any(used[idx : idx + len(key) + 2]):
            found.append((idx, TEAM_ES_EN[key]))
            for i in range(idx, idx + len(key) + 2):
                used[i] = True
    found.sort()
    # equipos distintos preservando el orden
    out: list[str] = []
    for _, en in found:
        if en not in out:
            out.append(en)
    return out


def _ints(line: str) -> list[int]:
    return [int(n) for n in re.findall(r"\d+", line)]


def _clean_scorer(line: str) -> str | None:
    txt = _SCORER_PREFIX.sub("", line).strip(" .:-")
    txt = re.sub(r"\(.*?\)", "", txt).strip()  # quita aclaraciones "(penal)"
    return txt if _norm_alnum(txt) else None


def _inline_scorer(line: str) -> str | None:
    """Goleador escrito en la MISMA línea del marcador ('Turquía 3-1 Yilmaz',
    'Suecia 3 vs Túnez 1 gyokeres', '2-1 Ali'): el texto tras el último número, si no
    es un equipo (p. ej. 'Australia 0 vs 1 Turquía' → sin goleador). None si no hay."""
    nums = list(re.finditer(r"\d+", line))
    if not nums:
        return None
    tail = line[nums[-1].end():]
    return None if _find_teams(tail) else _clean_scorer(tail)


def _tokens(s: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", _strip_accents(s).lower()) if len(t) >= 2]


def _participant_for(text: str) -> str | None:
    n = _norm_alnum(text)
    for key, team in PARTICIPANT_TEAM.items():
        if key in n:
            return team
    return None


def _parse_date(line: str):
    m = _DATE_RE.search(line)
    if not m:
        return None
    d, mo, y = (int(x) for x in m.groups())
    try:
        from datetime import date
        return date(y, mo, d)
    except ValueError:
        return None


class MatchIndex:
    """Búsqueda de partidos por PAR de equipos (o un equipo) validada por fecha. El
    par es único en grupos; la validación por fecha evita colisiones con un mismo
    par en eliminatorias y descarta líneas ilegibles que forman un par espurio."""

    def __init__(self, matches: list[Match]):
        self.by_pair: dict[frozenset, list[Match]] = {}
        self.by_team: dict[str, list[Match]] = {}
        for m in matches:
            self.by_pair.setdefault(frozenset((m.home_team, m.away_team)), []).append(m)
            self.by_team.setdefault(m.home_team, []).append(m)
            self.by_team.setdefault(m.away_team, []).append(m)

    def lookup(self, teams: list[str], note_date) -> Match | None:
        if len(teams) >= 2:
            cands, tol = self.by_pair.get(frozenset(teams[:2]), []), 3
        elif len(teams) == 1:
            cands, tol = self.by_team.get(teams[0], []), 2
        else:
            return None
        if not cands:
            return None
        if note_date is None:  # sin fecha solo si el par es inequívoco
            return cands[0] if len(cands) == 1 else None
        best = min(cands, key=lambda m: abs((m.match_date.date() - note_date).days))
        return best if abs((best.match_date.date() - note_date).days) <= tol else None


def _parse_blocks(text: str):
    """Genera (participante_or_None, fecha, [(teams, home, away, scorer_text)], report)."""
    blocks = re.split(r"^-{3,}\s*$", text, flags=re.MULTILINE)
    # Cada archivo corresponde a UNA jornada: si un bloque no trae fecha (p. ej. el
    # primero del archivo), se hereda la primera fecha que aparezca en el archivo
    # (sin ella, un pronóstico de un solo equipo que juega varios partidos no se
    # podría desambiguar y se perdería).
    current_date = next((d for ln in text.splitlines() if (d := _parse_date(ln))), None)
    for raw in blocks:
        lines = [l.rstrip() for l in raw.splitlines()]
        for l in lines:
            d = _parse_date(l)
            if d:
                current_date = d
        participant = next(
            (p for l in lines if (p := _participant_for(l))), None
        )
        yield participant, current_date, lines


def _extract_predictions(lines, index, note_date, report, who):
    """Devuelve [(match, home, away, scorer_text)] de un bloque; lo no parseable va al report."""
    preds = []
    n = len(lines)
    i = 0
    while i < n:
        line = lines[i]
        teams = _find_teams(line)
        if not teams:
            i += 1
            continue
        nl = _norm_text(line)
        nums = _ints(line)
        scores = None
        score_line_idx = i
        if "empate" in nl and nums:
            scores = (nums[0], nums[0])
        elif len(nums) >= 2:
            scores = (nums[0], nums[1])
        else:
            j = i + 1  # formato partido / marcador en líneas separadas
            while j < n and not lines[j].strip():
                j += 1
            if j < n and not _find_teams(lines[j]):
                nn, nlj = _ints(lines[j]), _norm_text(lines[j])
                if "empate" in nlj and nn:
                    scores, score_line_idx = (nn[0], nn[0]), j
                elif len(nn) >= 2:
                    scores, score_line_idx = (nn[0], nn[1]), j
        if scores is None:
            report.append(("marcador_ilegible", who, line.strip()))
            i += 1
            continue
        match = index.lookup(teams, note_date)
        if match is None:
            report.append(("partido_desconocido", who, line.strip()))
            i = score_line_idx + 1
            continue
        # El primer equipo nombrado lleva el primer marcador.
        if teams[0] == match.home_team:
            home, away = scores
        else:
            away, home = scores
        # Goleador: en la MISMA línea del marcador ("Turquía 3-1 Yilmaz") o, si no, en
        # la primera línea no vacía siguiente que no sea otro partido ni la fecha.
        scorer = _inline_scorer(lines[score_line_idx])
        if scorer is None:
            j = score_line_idx + 1
            while j < n and not lines[j].strip():
                j += 1
            # La línea siguiente es goleador solo si no es otro partido, ni la fecha, ni
            # el nombre del participante (un partido sin goleador al final del bloque no
            # debe "tragarse" el marcador del participante como si fuera el goleador).
            if (j < n and not _find_teams(lines[j]) and not _parse_date(lines[j])
                    and not _participant_for(lines[j])):
                scorer = _clean_scorer(lines[j])
                score_line_idx = j
        preds.append((match, home, away, scorer))
        i = score_line_idx + 1
    return preds


def _match_score(scorer_tokens: list[str], player_name: str) -> int:
    """Coincidencia por tokens: +2 token exacto, +1 token muy parecido (typos)."""
    pt = _tokens(player_name)
    s = 0
    for st in scorer_tokens:
        if st in pt:
            s += 2
        elif any(difflib.SequenceMatcher(None, st, p).ratio() >= 0.8 for p in pt):
            s += 1
    return s


async def _resolve_scorer(db, match, scorer_text, squads, report, who):
    """Resuelve el goleador contra las DOS plantillas del partido (alta confianza)."""
    if not scorer_text:
        return None, None
    # Alias por PALABRA completa del nombre normalizado: tolera iniciales/sufijos
    # ("K. Mbape", "Vini Jr") sin falsos positivos por subcadena (p. ej. "arda" dentro
    # de "Bardakci"). El alias solo cambia el término de búsqueda; la resolución sigue
    # siendo contra la plantilla del partido.
    words = f" {' '.join(_norm_text(scorer_text).split())} "
    search = next((v for k, v in SCORER_ALIASES.items() if f" {k} " in words), scorer_text)
    toks = _tokens(search)
    if not toks:
        return None, None
    if match.id not in squads:
        squads[match.id] = await player_crud.get_for_teams(db, [match.home_team, match.away_team])
    scored = sorted(
        ((_match_score(toks, p.name), p) for p in squads[match.id]),
        key=lambda x: x[0], reverse=True,
    )
    detail = f"{scorer_text} → {match.home_team} vs {match.away_team}"
    best = scored[0][0] if scored else 0
    if best == 0:
        report.append(("goleador_no_resuelto", who, detail))
        return None, None
    tied = [p for s, p in scored if s == best]
    if len(tied) > 1:
        # Desempate por inicial: las plantillas guardan "X. Apellido"; si el texto de
        # búsqueda empieza por la inicial de UN solo empatado, se elige ese (p. ej.
        # "Jonathan David"/"J. David" -> J. David, no P. David). Si no, queda ambiguo.
        initial = _strip_accents(search.strip())[:1].lower()
        tied = [p for p in tied if p.name[:1].lower() == initial]
        if len(tied) != 1:
            report.append(("goleador_ambiguo", who, detail))
            return None, None
    return tied[0].api_player_id, tied[0].name


async def _ensure_user(db, team_name, domain, dry_run):
    """Devuelve (user, creado). Crea el participante (participant_team + user) si no
    existe; en dry-run no escribe (devuelve (None, True) para reportar la creación)."""
    user = await user_crud.get_by_team(db, team_name)
    if user:
        return user, False
    if dry_run:
        return None, True
    if not await participant_team_crud.exists(db, team_name):
        db.add(ParticipantTeam(name=team_name))
        await db.flush()
    user = await user_crud.create(
        db, team_name=team_name, email=email_for(team_name, domain),
        hashed_password=hash_password(DEFAULT_PASSWORD), must_change_password=True,
    )
    return user, True


async def run(*, notes_paths, domain, dry_run, report_path):
    files = []
    for p in notes_paths:
        path = Path(p)
        files.extend(sorted(path.glob("*.txt")) if path.is_dir() else [path])
    if not files:
        print(f"Sin archivos .txt en {notes_paths}")
        return

    report: list[tuple[str, str, str]] = []
    created_users: list[str] = []
    squads: dict[int, list] = {}
    loaded = 0
    any_finished = False

    async with AsyncSessionLocal() as db:
        index = MatchIndex(await match_crud.get_all(db))
        for f in files:
            text = f.read_text(encoding="utf-8")
            for participant, note_date, lines in _parse_blocks(text):
                cand = next((l.strip() for l in lines if l.strip()), "")
                if participant is None:
                    if _find_teams("\n".join(lines)):  # bloque con partidos pero sin participante mapeado
                        report.append(("participante_sin_mapear", f.name, cand[:60]))
                    continue
                preds = _extract_predictions(lines, index, note_date, report, participant)
                if not preds:
                    continue
                user, created = await _ensure_user(db, participant, domain, dry_run)
                if created and participant not in created_users:  # un usuario, una vez
                    created_users.append(participant)
                for match, home, away, scorer_text in preds:
                    fg_id, fg_name = await _resolve_scorer(db, match, scorer_text, squads, report, participant)
                    if not dry_run:
                        await prediction_crud.upsert(
                            db, user_id=user.id, match_id=match.id,
                            predicted_home=home, predicted_away=away,
                            first_goal_player_id=fg_id, first_goal_player=fg_name,
                        )
                    if match.status == MatchStatus.FINISHED:
                        any_finished = True
                    loaded += 1
        if not dry_run:
            await db.commit()

    # Pipeline de puntos para los partidos ya finalizados (igual que el backfill HTTP).
    if any_finished and not dry_run:
        await sync_first_goals()
        await calculate_pending_points()

    _print_summary(loaded, created_users, report, dry_run, report_path)


def _print_summary(loaded, created_users, report, dry_run, report_path):
    mode = "DRY-RUN (no se escribió)" if dry_run else "Cargados"
    print(f"\n=== {mode}: {loaded} pronósticos | usuarios nuevos: {len(created_users)} ===")
    for u in created_users:
        print(f"  + usuario creado: {u}  (contraseña inicial {DEFAULT_PASSWORD})")
    # El reporte se reescribe SIEMPRE (también con 0 ítems) para que nunca quede
    # obsoleto respecto a la última corrida.
    by_kind: dict[str, list[str]] = {}
    for kind, who, detail in report:
        by_kind.setdefault(kind, []).append(f"[{who}] {detail}")
    lines = [f"# Revisión manual del backfill ({len(report)} ítems)\n"]
    for kind, items in by_kind.items():
        lines.append(f"\n## {kind} ({len(items)})")
        lines.extend(f"  - {it}" for it in items)
    if not report:
        lines.append("\n✅ Sin ítems pendientes de revisión manual.")
    Path(report_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    if report:
        print(f"\n⚠️  {len(report)} ítems para revisión manual → {report_path}")
        for kind, items in by_kind.items():
            print(f"   {kind}: {len(items)}")
    else:
        print(f"\n✅ Sin ítems pendientes de revisión manual → {report_path}")
    print()


def main():
    p = argparse.ArgumentParser(description="Carga pronósticos desde notas vía backfill.")
    p.add_argument("--notes", nargs="+", required=True, help="Archivo(s) o directorio(s) con las notas .txt")
    p.add_argument("--domain", default=DEFAULT_DOMAIN, help=f"Dominio de los correos nuevos (def: {DEFAULT_DOMAIN})")
    p.add_argument("--report", default="scripts/backfill_manual_review.txt", help="Archivo de revisión manual")
    p.add_argument("--dry-run", action="store_true", help="Parsea y reporta sin escribir en la BD")
    args = p.parse_args()
    asyncio.run(run(
        notes_paths=args.notes, domain=args.domain,
        dry_run=args.dry_run, report_path=args.report,
    ))


if __name__ == "__main__":
    main()
