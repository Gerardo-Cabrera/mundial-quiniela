"""
Datos MANUALES para el backfill de pronósticos (scripts/backfill_predictions.py).

Es lo único que requiere intervención humana: edítalo a medida que se sumen
participantes o aparezcan sobrenombres/typos de goleadores. El script hace el resto
(parsear, mapear equipos, buscar el partido, resolver el goleador y cargar).

Las claves se comparan NORMALIZADAS (minúsculas, sin acentos ni símbolos), así que
basta una subcadena distintiva de cómo aparece el nombre en las notas.
"""

# ── Participantes ─────────────────────────────────────────────────────────────
# clave = subcadena distintiva del nombre en las notas; valor = team_name OFICIAL.
# Si el participante aún no tiene usuario, el script lo crea (contraseña 12345678).
PARTICIPANT_TEAM = {
    "saiyajins":     "Super Saiyans C.F",   # el admin (admin@gmail.com); ya existe
    "genkidama":     "Genkidama F.C",
    "jihyo":         "Jihyo F.C",
    "fiebruos":      "Fiebruos C.F",
    "soldierboy":    "Soldier Boy",
    "rojosdelavila": "Rojos Del Ávila",
    "mugionce":      "Mugion ce FC",
    "petare":        "Petare F.C",
    "omegalink":     "Megalink FC",
    # Usuarios nuevos (se crean al cargar sus pronósticos):
    "desk":          "Desk FC",
    "flamex":        "Flamex F.C",
    "putas":         "Putas FC",
    "16132":         "106+16=132 F.C",
    "getsugatensho": "Getsugatensho F.C",
    "freestyle":     "Freestyle FC",
    "sobamelabolai": "Sobamelabolai F.C",
}

# ── Equipos ───────────────────────────────────────────────────────────────────
# nombre en español (como aparece en las notas) -> nombre EXACTO en la BD (inglés).
# Las claves más largas tienen prioridad (se buscan primero) para no confundir
# "corea" dentro de "corea del sur".
TEAM_ES_EN = {
    "mexico": "Mexico", "sudafrica": "South Africa",
    "corea del sur": "South Korea", "sur corea": "South Korea", "corea": "South Korea",
    "republica checa": "Czechia", "rep checa": "Czechia", "checa": "Czechia",
    "canada": "Canada", "bosnia": "Bosnia & Herzegovina",
    "estados unidos": "USA", "usa": "USA", "paraguay": "Paraguay",
    "qatar": "Qatar", "suiza": "Switzerland",
    "brasil": "Brazil", "marruecos": "Morocco",
    "haiti": "Haiti", "escocia": "Scotland",
    "australia": "Australia", "turquia": "Türkiye",
    "alemania": "Germany", "curazao": "Curaçao",
    "paises bajos": "Netherlands", "holanda": "Netherlands", "japon": "Japan",
    "costa de marfil": "Ivory Coast", "ecuador": "Ecuador",
    "suecia": "Sweden", "tunez": "Tunisia",
    "espana": "Spain", "cabo verde": "Cape Verde Islands",
    "belgica": "Belgium", "egipto": "Egypt",
    "arabia saudi": "Saudi Arabia", "arabia": "Saudi Arabia", "uruguay": "Uruguay",
    "iran": "Iran", "nueva zelanda": "New Zealand",
    "francia": "France", "senegal": "Senegal",
    "irak": "Iraq", "noruega": "Norway",
    "argentina": "Argentina", "argelia": "Algeria",
    "austria": "Austria", "jordania": "Jordan",
}

# ── Goleadores ────────────────────────────────────────────────────────────────
# Solo para sobrenombres/typos que el apellido directo NO resuelve contra la
# plantilla. clave = subcadena normalizada en la nota -> término de búsqueda real.
# Los que no resuelvan ni así se cargan SIN goleador y se reportan.
SCORER_ALIASES = {
    "vini":   "Vinicius",
    "halaand": "Haaland", "halland": "Haaland", "haland": "Haaland", "haalnd": "Haaland",
    "mbape":  "Mbappe",
    "julian": "Julian Alvarez",
    "raul jimenes": "Jimenez", "raul jimenez": "Jimenez", "gimenez": "Gimenez",
}
