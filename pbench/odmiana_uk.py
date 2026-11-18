"""Odmiana ukraińskich imion, imion odojcowskich i nazwisk przez przypadki (do gniazd szablonów `{osoba.pelne:rod}`).

Zakres: imiona, imiona po ojcu i nazwiska ze słowników generatora (`pbench/dane/slowniki/uk`). Reguły wg typu wyrazu,
bez zewnętrznych słowników; funkcje są deterministyczne i bez efektów ubocznych. Przypadki (nazwy łacińskie skrótów):
`mian` (називний), `rod` (родовий), `dav` (давальний), `zna` (знахідний), `oru` (орудний), `mis` (місцевий),
`kl` (кличний). Dla osób w dokumentach przyjęto celownik na -у/-ю (Шевченку Івану Петровичу), nie -ові.

Typy nazwisk męskich: -ко/-енко (odmieniane jak rzeczowniki męskie na -о: Шевченка), -ук/-юк/-ак/-ик (Мельничука), -ський/
-цький/-ий (przymiotnikowe: Ковальського), -ич (Мартиновича, końcówka -ем), -ов/-ев/-єв/-ін (Ковальова, orz. -им),
-ець (Кравця, wypadanie e), -ь (Коваля), -а (Сороки, jak rzeczowniki żeńskie). Nazwiska żeńskie: przymiotnikowe i -ова/-іна
(Ковальської, Ковальової) oraz na -а (Сороки) odmieniają się; pozostałe (Шевченко, Мельничук, Кравець) są nieodmienne.
Imiona z wymianą głoski: Ольга → Ользі, Федір → Федора. Wołacz wyjątkowy: Олег → Олеже.
Nazwiska żeńskie utworzone od męskich na -ий (Білий → Біла, Бережний → Бережна) odmieniają się przymiotnikowo (Білої);
rozpoznaje je lista pochodna ze słownika nazwisk generatora (ogólna końcówka -на/-ла objęłaby też rzeczowniki, np. Калина).
Nazwisko Бондар (rzeczownik miękki: бондаря) odmienia się jak Коваль: Бондаря, Бондарем, wołacz Бондарю.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

PRZYPADKI: tuple[str, ...] = ("mian", "rod", "dav", "zna", "oru", "mis", "kl")

_SAMOGLOSKI = "аеєиіїоуюяё"
_SYCZACE = "чшщж"
_TWARDE_TYLNOJEZYKOWE = "кгх"
#: Wymiana tylnojęzykowej przed -і (celownik/miejscownik rzeczowników żeńskich na -а).
_WYMIANA = {"г": "з", "к": "ц", "х": "с"}

#: Imiona męskie z nietypową odmianą: forma podstawowa -> temat przed końcówkami „а/у/ом”.
_TEMATY_IMION = {"Федір": "Федор", "Ігор": "Ігор"}
#: Imiona na spółgłoskę o miękkim temacie (końcówki -я/-ю/-ем).
_MIEKKIE_IMIONA = frozenset({"Ігор"})

_ADJ_M = {"rod": "ого", "dav": "ому", "zna": "ого", "oru": "им", "mis": "ому"}
_ADJ_F = {"rod": "ої", "dav": "ій", "zna": "у", "oru": "ою", "mis": "ій"}
_ZENSKIE_PRZYM = ("ська", "цька", "зька", "ова", "ева", "єва", "іна", "їна")
#: Wołacz imion, który nie wynika z reguły (Олег → Олеже, a nie „Олегу”).
_KLICZNY_WYJATKI = {"Олег": "Олеже"}
#: Nazwiska męskie o temacie miękkim (rzeczowniki na -р odmieniane jak -ь): Бондар → Бондаря.
_NAZWISKA_MIEKKIE = frozenset({"Бондар"})
_SLOWNIK_NAZWISK = Path(__file__).resolve().parent / "dane" / "slowniki" / "uk" / "nazwiska.txt"


@lru_cache(maxsize=1)
def _zenskie_od_ij() -> frozenset[str]:
    """Żeńskie formy nazwisk męskich na -ий (nie -ський/-цький/-зький) ze słownika generatora: Біла, Бережна, Підгорна."""
    wynik = set()
    for linia in _SLOWNIK_NAZWISK.read_text(encoding="utf-8").splitlines():
        forma = linia.partition("|")[0]                               # pierwsza kolumna: pisownia ukraińska
        if forma.endswith("ий") and not forma.endswith(("ський", "цький", "зький")):
            wynik.add(forma[:-2] + "а")
    return frozenset(wynik)
_MESKIE_PRZYM = ("ський", "цький", "зький", "ий")
_MESKIE_POSESYWNE = ("ов", "ев", "єв", "ін", "їн")


def _zenskie_a(s: str, przyp: str) -> str:
    """Rzeczowniki żeńskie (i męskie) na -а: Олена, Ольга, Сорока, Микола."""
    t = s[:-1]
    if przyp == "zna":
        return t + "у"
    if przyp == "oru":
        return t + "ою"
    if przyp == "kl":
        return t + "о"
    if przyp == "rod":
        return t + "и"
    if t and t[-1] in _WYMIANA:                    # dav/mis: Ольга → Ользі, Сорока → Сороці
        return t[:-1] + _WYMIANA[t[-1]] + "і"
    return t + "і"


def _zenskie_ja(s: str, przyp: str) -> str:
    """Rzeczowniki żeńskie na -я: Наталія → Наталії, Зоя → Зої, Леся → Лесі."""
    t = s[:-1]
    po_samogloskowej = bool(t) and t[-1] in _SAMOGLOSKI
    if po_samogloskowej:
        return t + {"rod": "ї", "dav": "ї", "zna": "ю", "oru": "єю", "mis": "ї", "kl": "є"}[przyp]
    return t + {"rod": "і", "dav": "і", "zna": "ю", "oru": "ею", "mis": "і", "kl": "ю"}[przyp]


def _meskie_twarde(t: str, przyp: str, kl_e: bool = True) -> str:
    """Temat męski twardy + końcówka (Олександр → Олександра, Мороз → Мороза, Мельник → Мельника)."""
    if przyp in ("rod", "zna"):
        return t + "а"
    if przyp in ("dav", "mis"):
        return t + "у"
    if przyp == "oru":
        return t + ("ем" if t[-1:] in _SYCZACE else "ом")
    return t + ("е" if kl_e and t[-1:] not in _TWARDE_TYLNOJEZYKOWE + _SYCZACE else "у")     # kl


def _meskie_miekkie(t: str, przyp: str) -> str:
    """Temat męski miękki (po usunięciu -ь/-й): Василь → Василя, Андрій → Андрія, Коваль → Коваля."""
    if przyp in ("rod", "zna"):
        return t + "я"
    if przyp in ("dav", "mis", "kl"):
        return t + "ю"
    return t + ("єм" if t[-1:] in _SAMOGLOSKI else "ем")        # Андрієм / Василем


def _przymiotnikowe(s: str, przyp: str, plec: str) -> str:
    if plec == "K":
        return s if przyp in ("mian", "kl") else s[:-1] + _ADJ_F[przyp]
    return s if przyp in ("mian", "kl") else s[:-2] + _ADJ_M[przyp]


def _imie(s: str, plec: str, przyp: str) -> str:
    if plec == "K":
        if s.endswith("я"):
            return _zenskie_ja(s, przyp)
        if s.endswith("а"):
            return _zenskie_a(s, przyp)
        return s
    if przyp == "kl" and s in _KLICZNY_WYJATKI:
        return _KLICZNY_WYJATKI[s]
    if s.endswith("а"):                                           # Микола, Лука
        return _zenskie_a(s, przyp)
    if s.endswith("о"):                                           # Петро, Дмитро, Михайло, Данило
        t = s[:-1]
        return t + {"rod": "а", "dav": "у", "zna": "а", "oru": "ом", "mis": "у", "kl": "е"}[przyp]
    if s.endswith(("ій", "й", "ь")):
        return _meskie_miekkie(s[:-1], przyp)
    if s in _MIEKKIE_IMIONA:
        return _meskie_miekkie(s, przyp)
    return _meskie_twarde(_TEMATY_IMION.get(s, s), przyp)


def _po_batkovi(s: str, plec: str, przyp: str) -> str:
    if plec == "K":                                               # -івна, -ївна, -овна
        return _zenskie_a(s, przyp) if s.endswith("а") else s
    return _meskie_twarde(s, przyp, kl_e=False)                  # -ович, -йович, -ич: temat na szczelinową ч


def _nazwisko(s: str, plec: str, przyp: str) -> str:
    if plec == "K":
        if s.endswith(_ZENSKIE_PRZYM) or s in _zenskie_od_ij():
            return _przymiotnikowe(s, przyp, "K")
        if s.endswith("а"):
            return _zenskie_a(s, przyp)
        if s.endswith("я"):                                       # Цибуля
            return _zenskie_ja(s, przyp)
        return s                                                  # Шевченко, Мельничук, Кравець: nieodmienne
    if s.endswith(_MESKIE_PRZYM):
        return _przymiotnikowe(s, przyp, "M")
    if s.endswith(_MESKIE_POSESYWNE) and len(s) > 3:              # Ковальов, Бондарев, Лисін
        if przyp in ("rod", "zna"):
            return s + "а"
        if przyp in ("dav", "mis"):
            return s + "у"
        return s + "им" if przyp == "oru" else s + "е"
    if s.endswith("ець") and len(s) > 4:                          # Кравець → Кравця
        return s[:-3] + {"rod": "ця", "dav": "цю", "zna": "ця", "oru": "цем", "mis": "цю", "kl": "че"}[przyp]
    if s.endswith("о"):                                           # Шевченко, Бойко
        return s[:-1] + {"rod": "а", "dav": "у", "zna": "а", "oru": "ом", "mis": "у", "kl": "у"}[przyp]
    if s.endswith("а"):                                           # Сорока (męskie na -а)
        return _zenskie_a(s, przyp)
    if s.endswith("я"):                                           # Цибуля
        return _zenskie_ja(s, przyp)
    if s.endswith(("ь", "й")):                                    # Коваль, Гайдай
        return _meskie_miekkie(s[:-1], przyp)
    if s in _NAZWISKA_MIEKKIE:                                    # Бондар → Бондаря
        return _meskie_miekkie(s, przyp)
    return _meskie_twarde(s, przyp)


_ROZDZIELACZE = " -"


def odmien_slowo(slowo: str, rodzaj: str, plec: str, przypadek: str) -> str:
    """Pojedynczy wyraz (bez spacji) jako `imie|po_batkovi|nazwisko` danej płci (`M|K`) w przypadku."""
    if przypadek not in PRZYPADKI:
        raise ValueError(f"nieznany przypadek: {przypadek!r} (dozwolone: {', '.join(PRZYPADKI)})")
    if plec not in ("M", "K"):
        raise ValueError(f"nieznana płeć: {plec!r}")
    if rodzaj not in ("imie", "po_batkovi", "nazwisko"):
        raise ValueError(f"nieznany rodzaj wyrazu: {rodzaj!r}")
    if przypadek == "mian" or not slowo:
        return slowo
    f = {"imie": _imie, "po_batkovi": _po_batkovi, "nazwisko": _nazwisko}[rodzaj]
    return f(slowo, plec, przypadek)


def _czlony(tekst: str, rodzaj: str, plec: str, przypadek: str) -> str:
    """Odmienia każdy człon (spacje i łączniki zostają): „Мельник-Кравчук”, „Іван Петро”."""
    return " ".join("-".join(odmien_slowo(c, rodzaj, plec, przypadek) for c in sp.split("-")) for sp in tekst.split(" "))


def odmien(imie: str, po_batkovi: str, nazwisko: str, plec: str, przypadek: str, uklad: str = "NIP") -> str:
    """Imię, imię po ojcu i nazwisko w przypadku, w kolejności `uklad` (N – nazwisko, I – imię, P – po batkovi).

    Domyślnie „ПІБ” (Шевченка Івана Петровича); `IP` – „Івана Петровича”, `IN` – „Івана Шевченка”. Puste człony pomijane."""
    wartosci = {"N": (nazwisko, "nazwisko"), "I": (imie, "imie"), "P": (po_batkovi, "po_batkovi")}
    if not set(uklad) <= set(wartosci):
        raise ValueError(f"niepoprawny układ: {uklad!r}")
    return " ".join(_czlony(wartosci[k][0], wartosci[k][1], plec, przypadek) for k in uklad if wartosci[k][0])


# ----------------------------------------------------------------------------- data w całości słownie (poświadczenia notarialne)
_PORZADKOWE_DOP = ("", "першого", "другого", "третього", "четвертого", "п’ятого", "шостого", "сьомого", "восьмого",
                   "дев’ятого", "десятого", "одинадцятого", "дванадцятого", "тринадцятого", "чотирнадцятого",
                   "п’ятнадцятого", "шістнадцятого", "сімнадцятого", "вісімнадцятого", "дев’ятнадцятого")
_DZIESIATKI = {2: ("двадцять", "двадцятого"), 3: ("тридцять", "тридцятого"), 4: ("сорок", "сорокового"),
               5: ("п’ятдесят", "п’ятдесятого"), 6: ("шістдесят", "шістдесятого"), 7: ("сімдесят", "сімдесятого"),
               8: ("вісімдесят", "вісімдесятого"), 9: ("дев’яносто", "дев’яностого")}


def _porzadkowe_dop(n: int) -> str:
    """Liczebnik porządkowy w dopełniaczu dla 1–99: 3 → третього, 22 → двадцять другого, 30 → тридцятого."""
    if n < 20:
        return _PORZADKOWE_DOP[n]
    dz, j = divmod(n, 10)
    return _DZIESIATKI[dz][1] if j == 0 else f"{_DZIESIATKI[dz][0]} {_PORZADKOWE_DOP[j]}"


def data_slownie_pelna(d) -> str:
    """Data w całości słownie, jak w poświadczeniu notarialnym: 22.12.2023 →
    „двадцять другого грудня дві тисячі двадцять третього року” (lata 2001–2099)."""
    from .dane.wspolne import MIESIACE
    if not 2001 <= d.year <= 2099:
        raise ValueError(f"data słownie: rok {d.year} poza zakresem 2001–2099")
    return f"{_porzadkowe_dop(d.day)} {MIESIACE['uk'][d.month - 1]} дві тисячі {_porzadkowe_dop(d.year - 2000)} року"
