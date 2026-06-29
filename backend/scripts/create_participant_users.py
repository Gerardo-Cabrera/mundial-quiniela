"""
Aprovisiona las cuentas de los participantes de la quiniela.

Como el registro está cerrado (el Mundial ya inició), este script crea un usuario
por cada equipo participante que aún NO tenga cuenta, generando el correo a partir
del nombre del equipo (slug + dominio). Es idempotente: omite los equipos que ya
tienen usuario. Por defecto OMITE el equipo del admin ("Super Saiyajins C.F"), que
ya tiene su correo (admin@gmail.com).

El correo es solo el identificador de inicio de sesión (la app no envía emails).

Uso (desde el directorio backend/, en local o en producción):

    python -m scripts.create_participant_users              # contraseña aleatoria por usuario
    python -m scripts.create_participant_users --dry-run    # solo muestra qué haría
    python -m scripts.create_participant_users --password X # contraseña compartida
    python -m scripts.create_participant_users --domain quiniela.com

Producción (Render / Supabase): usa la misma DATABASE_URL de la app (variable de
entorno). En Render, ejecútalo como comando puntual del servicio backend (Shell o
Job); contra Supabase basta con que DATABASE_URL apunte a Supabase.

⚠️ La salida incluye las contraseñas en texto plano (para entregárselas a cada
participante). Trátala con cuidado: en Render/Supabase queda en los logs.
"""
import argparse
import asyncio
import secrets
import unicodedata

from app.core.security import hash_password
from app.crud import participant_team_crud, user_crud
from app.database import AsyncSessionLocal

# Equipo del admin: ya tiene cuenta (admin@gmail.com), se omite por defecto.
DEFAULT_SKIP_TEAMS = ["Super Saiyajins C.F"]
DEFAULT_DOMAIN = "gmail.com"


def email_for(team_name: str, domain: str) -> str:
    """Correo determinista a partir del nombre del equipo: minúsculas, sin acentos
    ni símbolos (solo [a-z0-9]). Ej.: 'Rojos Del Ávila' -> 'rojosdelavila@dominio'."""
    ascii_name = unicodedata.normalize("NFKD", team_name).encode("ascii", "ignore").decode()
    slug = "".join(c for c in ascii_name.lower() if c.isalnum())
    return f"{slug}@{domain}"


async def provision(*, domain: str, password: str | None, skip_teams: set[str], dry_run: bool):
    created: list[tuple[str, str, str]] = []
    skipped: list[tuple[str, str]] = []
    async with AsyncSessionLocal() as db:
        for team in await participant_team_crud.get_all_names(db):
            if team in skip_teams:
                skipped.append((team, "omitido (admin / configurado)"))
                continue
            if await user_crud.get_by_team(db, team):
                skipped.append((team, "ya tiene cuenta"))
                continue
            email = email_for(team, domain)
            if await user_crud.get_by_email(db, email):
                skipped.append((team, f"correo {email} ya en uso"))
                continue
            pwd = password or secrets.token_urlsafe(9)
            if not dry_run:
                await user_crud.create(
                    db, team_name=team, email=email, hashed_password=hash_password(pwd)
                )
            created.append((team, email, pwd))
        if not dry_run:
            await db.commit()

    title = "DRY-RUN (no se creó nada)" if dry_run else "Cuentas creadas"
    print(f"\n=== {title} ({len(created)}) ===")
    if created:
        w = max(len(t) for t, _, _ in created)
        for team, email, pwd in created:
            print(f"  {team:<{w}}  {email:<34}  {pwd}")
    if skipped:
        print(f"\n--- Omitidos ({len(skipped)}) ---")
        for team, reason in skipped:
            print(f"  {team}: {reason}")
    print()


def main() -> None:
    p = argparse.ArgumentParser(description="Aprovisiona las cuentas de los participantes.")
    p.add_argument("--domain", default=DEFAULT_DOMAIN, help=f"Dominio del correo (def: {DEFAULT_DOMAIN})")
    p.add_argument("--password", default=None, help="Contraseña compartida; por defecto una aleatoria por usuario")
    p.add_argument("--skip-team", action="append", default=None,
                   help=f"Equipo(s) a omitir; reemplaza el valor por defecto {DEFAULT_SKIP_TEAMS}")
    p.add_argument("--dry-run", action="store_true", help="Muestra qué haría sin escribir en la BD")
    args = p.parse_args()
    skip = set(args.skip_team if args.skip_team is not None else DEFAULT_SKIP_TEAMS)
    asyncio.run(provision(
        domain=args.domain, password=args.password, skip_teams=skip, dry_run=args.dry_run,
    ))


if __name__ == "__main__":
    main()
