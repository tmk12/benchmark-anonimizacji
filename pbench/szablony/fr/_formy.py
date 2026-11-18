"""Skróty do pisania szablonów FR: gniazda rodzaju gramatycznego (`{rola.rodzaj:m|k}`) z przyimkiem i rodzajnikiem
w jednym gnieździe („au défendeur/à la défenderesse”), tytuły przed nazwiskiem i nazwisko wielkimi literami.

Zasady, których pilnują testy: ściągnięcia (au/du/aux) stoją w gnieździe płci, nie w tekście stałym; przed zmiennym
imieniem zawsze stoi tytuł („de Monsieur …”, „de Maître …”), bo samo imię mogłoby zaczynać się od samogłoski
(„d'Alice”); „de Angers” (elizja przed miastem) załatwia pole `barreau`/`sad.nazwa` generatora."""
from __future__ import annotations


def g(rola: str, m: str, f: str) -> str:
    """Gniazdo rodzaju: forma męska `m` albo żeńska `f` wg płci osoby roli."""
    return "{" + rola + ".rodzaj:" + m + "|" + f + "}"


def civ(rola: str) -> str:
    """Tytuł grzecznościowy: Monsieur / Madame."""
    return g(rola, "Monsieur", "Madame")


def nom(rola: str) -> str:
    """Imię i nazwisko wielkimi literami, jak w pismach procesowych: „Jean DUPONT”."""
    return "{" + rola + ".imie} {" + rola + ".nazwisko:upper}"


def pel(rola: str) -> str:
    """Tytuł i imię z nazwiskiem: „Monsieur Jean Dupont”."""
    return civ(rola) + " {" + rola + ".pelne}"


def acte(rola: str) -> str:
    """Tytuł i imię z nazwiskiem wielkimi literami: „Madame Marie DUPONT”."""
    return civ(rola) + " " + nom(rola)


# --- strony postępowania (role `demandeur` i `defendeur`)
DEM = g("demandeur", "le demandeur", "la demanderesse")
DEM_C = g("demandeur", "Le demandeur", "La demanderesse")
DEM_DU = g("demandeur", "du demandeur", "de la demanderesse")
DEM_AU = g("demandeur", "au demandeur", "à la demanderesse")
DEM_POUR = DEM     # „pour le demandeur” – bez ściągnięcia
DEF = g("defendeur", "le défendeur", "la défenderesse")
DEF_C = g("defendeur", "Le défendeur", "La défenderesse")
DEF_DU = g("defendeur", "du défendeur", "de la défenderesse")
DEF_AU = g("defendeur", "au défendeur", "à la défenderesse")
# --- apel: pozwany w I instancji = appelant, powód = intimé
APP = g("defendeur", "l'appelant", "l'appelante")
APP_C = g("defendeur", "L'appelant", "L'appelante")
INT = g("demandeur", "l'intimé", "l'intimée")
INT_C = g("demandeur", "L'intimé", "L'intimée")
INT_AU = g("demandeur", "à l'intimé", "à l'intimée")
