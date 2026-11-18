"""Transliteracja ukraińskiego (i rosyjskiej pisowni imion) na pismo łacińskie w siedmiu systemach.

Własny kod, bez zewnętrznych bibliotek i bez danych z korpusu treningowego Privatizera. Systemy (nazwa w gold =
`Wartosc.translit`):

* `kmu2010` – Postanowienie Gabinetu Ministrów Ukrainy nr 55 z 27.01.2010 (transliteracja ukraińskiego alfabetu
  łacinką w paszportach i dokumentach): reguły pozycyjne dla є, ї, й, ю, я (na początku wyrazu `Ye Yi Y Yu Ya`,
  w środku `ie i i iu ia`), `зг` → `zgh`, apostrof i znak miękki pomijane;
* `paszport_zsrr` – dawny zapis paszportowy, rosyjsko-podobny: tablica rosyjskich paszportów (ICAO 9303: ю → IU,
  я → IA, й → I, щ → SHCH, х → KH, ц → TS) z literami ukraińskimi bez własnych reguł (г → G, и i і i ї → I, є → E);
  pisany jest wielkimi literami, jak w paszporcie;
* `polski` – polska praktyka transkrypcji z ukraińskiego (Szewczenko, Ołeksandr, Jurij, Hryhorij): г → h, ґ → g,
  х → ch, ш → sz, щ → szcz, ч → cz, в → w, и → y, л → ł (przed і, ь, є, ю, я → l), ь zmiękcza (ń, ś, ć, ź),
  я/ю/є po spółgłosce → ia/iu/ie, końcówki -ський/-цький → -ski/-cki;
* `niemiecki` – zapis niemiecki (Duden): Schewtschenko (ш → sch, ч → tsch, щ → schtsch, в → w, ж → sh, з → s, ц → z);
* `francuski` – zapis francuski: Chevtchenko (ш → ch, ч → tch, щ → chtch, ж → j, у → ou, ю → iou, я → ia);
* `iso9` – ISO 9:1995 (tablica 1, znaki diakrytyczne, odwracalna): Ševčenko, Kìïv, Ûrìj; wynik w NFC;
* `ascii_dorazne` – nieformalny zapis „na klawiaturze”: niespójny (Oleksandr / Olexandr / Aleksandr), losowany z
  `rng` (domyślnie deterministycznie z tekstu).

Duże litery: wyraz pisany wielkimi literami daje wynik wielkimi, wyraz zaczynający się wielką literą – wielką pierwszą
literę wyniku (`Щ` → `Shch`). Znaki spoza cyrylicy zostają bez zmian. Litery rosyjskie (ё, ы, э, ъ) są obsługiwane, bo
rosyjska pisownia imion osób ukraińskich jest dozwolonym przypadkiem (`pisownia_rosyjska_imion`); to uzupełnienie
tablic, nie ich oficjalna część.
"""
from __future__ import annotations

import random
import re
import unicodedata
from collections.abc import Callable

SYSTEMY: tuple[str, ...] = ("kmu2010", "paszport_zsrr", "polski", "niemiecki", "francuski", "iso9", "ascii_dorazne")

APOSTROFY = "'ʼ’`′‘"
_CYRYLICA = "А-Яа-яЁёЄєІіЇїҐґЪъЫыЭэ"
_SLOWO = re.compile(f"[{_CYRYLICA}{re.escape(APOSTROFY)}]*[{_CYRYLICA}][{_CYRYLICA}{re.escape(APOSTROFY)}]*")
_SAMOGLOSKI_UK = "аеєиіїоуюяёыэ"


def ma_cyrylice(tekst: str) -> bool:
    """Czy tekst zawiera jakąkolwiek literę cyrylicy (Unicode blok Cyrillic)."""
    return any("Ѐ" <= c <= "ӿ" for c in tekst)


# ----------------------------------------------------------------------------- tablice
_KMU = {"а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e", "ж": "zh", "з": "z", "и": "y",
        "і": "i", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
        "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ь": "", "ъ": "",
        "ы": "y", "э": "e"}
#: litera -> (na początku wyrazu, w środku/na końcu)
_KMU_POZ = {"є": ("ye", "ie"), "ї": ("yi", "i"), "й": ("y", "i"), "ю": ("yu", "iu"), "я": ("ya", "ia"),
            "ё": ("yo", "io")}

_ZSRR = {"а": "A", "б": "B", "в": "V", "г": "G", "ґ": "G", "д": "D", "е": "E", "є": "E", "ж": "ZH", "з": "Z",
         "и": "I", "і": "I", "ї": "I", "й": "I", "к": "K", "л": "L", "м": "M", "н": "N", "о": "O", "п": "P",
         "р": "R", "с": "S", "т": "T", "у": "U", "ф": "F", "х": "KH", "ц": "TS", "ч": "CH", "ш": "SH",
         "щ": "SHCH", "ъ": "IE", "ы": "Y", "ь": "", "э": "E", "ю": "IU", "я": "IA", "ё": "E"}

_POLSKI = {"а": "a", "б": "b", "в": "w", "г": "h", "ґ": "g", "д": "d", "е": "e", "ж": "ż", "з": "z", "и": "y",
           "і": "i", "й": "j", "к": "k", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
           "у": "u", "ф": "f", "х": "ch", "ц": "c", "ч": "cz", "ш": "sz", "щ": "szcz", "ъ": "", "ы": "y",
           "э": "e", "ё": "jo"}
#: litery iotowane po polsku: (po samogłosce, na początku i po apostrofie) / (po spółgłosce)
_POLSKI_IOT = {"я": ("ja", "ia"), "ю": ("ju", "iu"), "є": ("je", "ie"), "ї": ("ji", "i")}
_POLSKI_MIEKKIE = {"n": "ń", "s": "ś", "c": "ć", "z": "ź"}
_POLSKI_LOGICZNE_L = "іьєюя"

_NIEMIECKI = {"а": "a", "б": "b", "в": "w", "г": "h", "ґ": "g", "д": "d", "е": "e", "є": "je", "ж": "sh", "з": "s",
              "и": "y", "і": "i", "ї": "ji", "й": "j", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p",
              "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "ch", "ц": "z", "ч": "tsch", "ш": "sch",
              "щ": "schtsch", "ь": "", "ъ": "", "ы": "y", "э": "e", "ю": "ju", "я": "ja", "ё": "jo"}

_FRANCUSKI = {"а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e", "є": "ie", "ж": "j", "з": "z",
              "и": "y", "і": "i", "ї": "ï", "й": "i", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p",
              "р": "r", "с": "s", "т": "t", "у": "ou", "ф": "f", "х": "kh", "ц": "ts", "ч": "tch", "ш": "ch",
              "щ": "chtch", "ь": "", "ъ": "", "ы": "y", "э": "e", "ю": "iou", "я": "ia", "ё": "io"}

#: ISO 9:1995, tablica 1 (alfabety słowiańskie), z literami ukraińskimi; ґ = g + U+0300, ь = ʹ (U+02B9).
_ISO9 = {"а": "a", "б": "b", "в": "v", "г": "g", "ґ": "g̀", "д": "d", "е": "e", "ё": "ë", "є": "ê", "ж": "ž",
         "з": "z", "и": "i", "і": "ì", "ї": "ï", "й": "j", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
         "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "c", "ч": "č", "ш": "š",
         "щ": "ŝ", "ъ": "ʺ", "ы": "y", "ь": "ʹ", "э": "è", "ю": "û", "я": "â"}

#: Warianty nieformalne (`ascii_dorazne`): litera -> możliwe zapisy; pierwszy to najczęstszy.
_DORAZNE = {"а": ("a",), "б": ("b",), "в": ("v", "v", "w"), "г": ("h", "h", "g"), "ґ": ("g",), "д": ("d",),
            "е": ("e", "e", "e", "ie"), "є": ("ye", "ie", "e", "ie"), "ж": ("zh", "zh", "j", "g"), "з": ("z",),
            "и": ("y", "y", "i"), "і": ("i",), "ї": ("yi", "i", "ji", "yi"), "й": ("y", "i", "j"), "к": ("k",),
            "л": ("l",), "м": ("m",), "н": ("n",), "о": ("o",), "п": ("p",), "р": ("r",), "с": ("s",),
            "т": ("t",), "у": ("u",), "ф": ("f", "ph"), "х": ("kh", "kh", "h", "x"), "ц": ("ts", "ts", "c", "tz"),
            "ч": ("ch", "ch", "tch", "c"), "ш": ("sh", "sh", "sch", "s"), "щ": ("shch", "shch", "sch", "shh"),
            "ь": ("", "", "'"), "ъ": ("",), "ы": ("y",), "э": ("e",), "ю": ("yu", "yu", "iu", "ju"),
            "я": ("ya", "ya", "ia", "ja"), "ё": ("yo", "e", "io")}


# ----------------------------------------------------------------------------- systemy (wyraz małymi literami)
def _kmu2010(w: str, _rng: random.Random | None = None) -> str:
    wynik = []
    i = 0
    while i < len(w):
        c = w[i]
        if c in APOSTROFY:
            i += 1
            continue
        if c == "з" and w[i + 1:i + 2] == "г":
            wynik.append("zgh")
            i += 2
            continue
        poz = _KMU_POZ.get(c)
        wynik.append((poz[0] if i == 0 else poz[1]) if poz else _KMU.get(c, c))
        i += 1
    return "".join(wynik)


def _paszport_zsrr(w: str, _rng: random.Random | None = None) -> str:
    return "".join("" if c in APOSTROFY else _ZSRR.get(c, c) for c in w)


def _polski(w: str, _rng: random.Random | None = None, rosyjska: bool = False) -> str:
    """Transkrypcja polska; `rosyjska` – odczyt rosyjski (л przed е zostaje „l”: Aleksandr, nie Ałeksandr)."""
    miekkie_l = _POLSKI_LOGICZNE_L + ("е" if rosyjska else "")
    # końcówki przymiotnikowe -ський / -цький: po polsku -ski / -cki
    for konc, pl in (("ський", "ski"), ("цький", "cki"), ("зький", "zki")):
        if w.endswith(konc) and len(w) > len(konc):
            return _polski(w[:-len(konc)], None, rosyjska) + pl
    wynik: list[str] = []
    for i, c in enumerate(w):
        nast = w[i + 1:i + 2]
        poprzednia = w[i - 1] if i else ""
        if c in APOSTROFY:
            continue
        if c == "л":
            podwojne = nast == "л" and w[i + 2:i + 3] in tuple(miekkie_l)       # Ілля, Віталій: „ll” (nie „łl”)
            wynik.append("l" if (nast and nast in miekkie_l) or podwojne else "ł")
        elif c == "ь":
            # miękkie ń/ś/ć/ź także na końcu wyrazu (Кравець → Kraweć, Ірпінь → Irpiń); „ьк” i „ь” przed samogłoską – bez
            if wynik and wynik[-1] in _POLSKI_MIEKKIE and nast != "к" and (not nast or nast not in _SAMOGLOSKI_UK):
                wynik[-1] = _POLSKI_MIEKKIE[wynik[-1]]
        elif c in _POLSKI_IOT:
            po_samogloskowej = i == 0 or poprzednia in _SAMOGLOSKI_UK or poprzednia in APOSTROFY
            if poprzednia == "л" and c in "яює":
                # po л (miękkie „l”) bez „i”: Ляшко → Laszko, Любомир → Lubomyr, Уляна → Ulana, Ілля → Illa
                wynik.append({"я": "a", "ю": "u", "є": "e"}[c])
                continue
            wynik.append(_POLSKI_IOT[c][0 if po_samogloskowej else 1])
        else:
            wynik.append(_POLSKI.get(c, c))
    return "".join(wynik)


def _tabela(tab: dict[str, str]) -> Callable[[str, random.Random | None], str]:
    def f(w: str, _rng: random.Random | None = None) -> str:
        return "".join("" if c in APOSTROFY else tab.get(c, c) for c in w)
    return f


def _iso9(w: str, _rng: random.Random | None = None) -> str:
    """ISO 9:1995 z tablicy 1. Apostrof zapisany jako ʼ (U+02BC): nie mam pewnego źródła normy co do znaku w wyniku
    (U+2019 albo U+02BC), więc wybór pozostaje jak dotąd, a wynik jest odwracalny przez ten sam zestaw apostrofów."""
    return "".join("ʼ" if c in APOSTROFY else _ISO9.get(c, c) for c in w)


def _dorazne(w: str, rng: random.Random | None = None) -> str:
    rng = rng or random.Random(w)
    wynik = []
    i = 0
    while i < len(w):
        c = w[i]
        if c in APOSTROFY:
            i += 1
            continue
        if c == "к" and w[i + 1:i + 2] == "с" and rng.random() < 0.4:      # Олександр → Olexandr
            wynik.append("x")
            i += 2
            continue
        warianty = _DORAZNE.get(c)
        wynik.append(rng.choice(warianty) if warianty else c)
        i += 1
    return "".join(wynik)


_SYSTEM: dict[str, Callable[[str, random.Random | None], str]] = {
    "kmu2010": _kmu2010, "paszport_zsrr": _paszport_zsrr, "polski": _polski, "niemiecki": _tabela(_NIEMIECKI),
    "francuski": _tabela(_FRANCUSKI), "iso9": _iso9, "ascii_dorazne": _dorazne,
}


def _wielkosc(wyraz: str, wynik: str) -> str:
    """Przenosi wielkość liter wyrazu źródłowego na wynik (WIELKIE → WIELKIE, Tytułowe → Tytułowe)."""
    litery = [c for c in wyraz if c.isalpha()]
    if len(litery) > 1 and all(c.isupper() for c in litery):
        return wynik.upper()
    if litery and litery[0].isupper() and wynik:
        return wynik[0].upper() + wynik[1:]
    return wynik


#: Litery rosyjskiej pisowni -> najbliższe ukraińskie (odczyt rosyjski: г = [g], и = [i], ы = [y], э, ё jak е):
#: dzięki temu Александр → Aleksandr, Сергей → Sergei, Ковалёв → Kovalev, а nie wg ukraińskiego odczytu liter.
_RU_NA_UK = str.maketrans({"и": "і", "И": "І", "г": "ґ", "Г": "Ґ", "ы": "и", "Ы": "И", "э": "е", "Э": "Е", "ё": "е", "Ё": "Е",
                           "ъ": "", "Ъ": ""})


def transliteruj(tekst: str, system: str, rng: random.Random | None = None, rosyjska: bool = False) -> str:
    """Tekst z cyrylicą zapisany w `system` (zob. `SYSTEMY`); znaki spoza cyrylicy bez zmian.

    `rng` dotyczy tylko `ascii_dorazne` (domyślnie losowanie wyznaczone przez tekst – ten sam tekst daje ten sam zapis).
    `rosyjska` – tekst w rosyjskiej pisowni (imię/nazwisko osoby ukraińskiej): litery czytane po rosyjsku.
    Wynik `paszport_zsrr` ma zawsze wielkie litery, wynik `iso9` jest w NFC."""
    if system not in _SYSTEM:
        raise ValueError(f"nieznany system transliteracji: {system!r} (dozwolone: {', '.join(SYSTEMY)})")
    if rosyjska:
        tekst = tekst.translate(_RU_NA_UK)
    f = _SYSTEM[system]
    if rosyjska and system == "polski":
        f = lambda w, r=None: _polski(w, r, rosyjska=True)      # noqa: E731
    if system == "ascii_dorazne" and rng is None:
        rng = random.Random(f"translit:{tekst}")

    def zamien(m: re.Match[str]) -> str:
        w = m.group(0)
        wynik = _wielkosc(w, f(w.lower(), rng))
        return wynik.upper() if system == "paszport_zsrr" else wynik

    return unicodedata.normalize("NFC", _SLOWO.sub(zamien, tekst))
