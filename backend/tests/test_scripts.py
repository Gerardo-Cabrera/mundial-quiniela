"""Tests del script de aprovisionamiento de cuentas (scripts/create_participant_users)."""
import pytest

from scripts.create_participant_users import email_for

# Lista canónica de equipos participantes (igual que la migración 0003 / la BD).
PARTICIPANT_TEAMS = [
    "Jax FC", "Genkidama F.C", "Jihyo F.C", "Rojos Del Ávila", "Fiebruos C.F",
    "Dragon Lord F.C", "Super Marihuana nos Blue F.C", "Rostyn Saca Las Actas F.C",
    "Super Saiyajins C.F", "Megalink FC", "Caramelo De Chocolate FC", "Jack F.C",
    "Mugion ce FC", "Soldier Boy", "Petare F.C", "Choupa-Mesta Draco FC",
]


@pytest.mark.parametrize("team, expected", [
    ("Jax FC", "jaxfc@gmail.com"),                              # espacios
    ("Genkidama F.C", "genkidamafc@gmail.com"),                 # puntos
    ("Rojos Del Ávila", "rojosdelavila@gmail.com"),             # acentos → ascii
    ("Choupa-Mesta Draco FC", "choupamestadracofc@gmail.com"),  # guion
])
def test_email_for_slugifies(team, expected):
    assert email_for(team, "gmail.com") == expected


def test_email_for_respects_domain():
    assert email_for("Jax FC", "quiniela.com") == "jaxfc@quiniela.com"


def test_email_for_unique_across_all_participants():
    """Los 16 equipos producen correos distintos (la columna email es UNIQUE)."""
    emails = [email_for(t, "gmail.com") for t in PARTICIPANT_TEAMS]
    assert len(set(emails)) == len(emails)
