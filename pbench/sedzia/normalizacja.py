"""Wspólna normalizacja tekstu dla sędziów (tekstowego i plikowego).

Sędzia tekstowy porównuje wyłącznie offsety, więc sam niczego nie normalizuje – te funkcje służą sędziemu plikowemu
(porównanie tekstu wyciągniętego z pliku wynikowego z wartościami wzorcowymi).

**Szkielet** (`szkielet`, H6a): litery cyrylicy i greki mylone z literami łacińskimi (homoglify) sprowadzone do łacińskiego
odpowiednika – dwa zapisy o tym samym szkielecie wyglądają tak samo („Kоwalski” z cyrylicznym „о” = „Kowalski”, „Κοwalski”
z greckimi „Κ” i „ο” – też).
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable

#: Różne znaki myślnika/minusa sprowadzane do „-”.
_MYSLNIKI = dict.fromkeys(map(ord, "‐‑‒–—―−­"), "-")
_BIALE = re.compile(r"\s+")
#: Znaki formatujące niewidoczne dla czytelnika (zero-width, miękki łącznik, BOM): usuwane przed porównaniem.
_FORMATUJACE = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\u00ad\ufeff"), None)
#: Przeniesienie wyrazu: łącznik tuż po znaku wyrazu i koniec wiersza (z ewentualnymi spacjami) przed znakiem wyrazu albo
#: znacznik łącznika końca wiersza, który zostawia PDFium (U+FFFE, bez znaku nowego wiersza). Zwykły myślnik w wierszu
#: („Nowak-Kowalski”, „2020 – 2021”) nie pasuje.
_PRZENIESIENIE = re.compile(r"(?<=\w)[-\u2010\u2011\u00ad][ \t]*\r?\n[ \t]*(?=\w)|\ufffe")
#: Szkielet: litera cyrylicy -> łacińska o tym samym kształcie. Źródło: Unicode Technical Standard #39 (Unicode Security
#: Mechanisms), plik `confusables.txt` – pary Cyrillic -> Latin (prototyp łaciński) dla liter ukraińskiego alfabetu i liter, które
#: wstawia `pbench.homoglify` (а е о р с х у і, А В С Е Н І К М О Р Т Х У), oraz ј ѕ ԁ һ ӏ ԛ ԝ ї. Tablica jest po casefold
#: (porównanie sędziego nie rozróżnia wielkości liter), więc litery mylone tylko jako WIELKIE (В/B, Н/H, К/K, М/M, Т/T) są
#: zapisane małymi (в -> b, н -> h…): „ВОНА” i „BOHA” to ten sam zapis, a „вона” i „boha” – dwa (małe litery różne), ale po
#: casefold obie pary mają ten sam szkielet. Kierunek odwrotny (łacina wmieszana w wyraz cyrylicki) daje ten sam szkielet,
#: bo porównuje się szkielety OBU stron. Na tekście bez cyrylicy szkielet jest tożsamością (trzon korpusu bez zmian).
SZKIELET_CYR_LAC: dict[str, str] = {
    "а": "a", "в": "b", "е": "e", "к": "k", "м": "m", "н": "h", "о": "o", "р": "p", "с": "c", "т": "t", "у": "y",
    "х": "x", "і": "i", "ї": "ï", "ј": "j", "ѕ": "s", "ԁ": "d", "һ": "h", "ӏ": "l", "ԛ": "q", "ԝ": "w",
}
#: Szkielet greki (poprawka H6a, M2): litera grecka -> łacińska o tym samym kształcie, to samo źródło (UTS #39 `confusables.txt`,
#: pary Greek -> Latin, tylko litera ↔ litera). Tablica jest po NFKC i casefold, więc obowiązuje ta sama zasada co dla cyrylicy:
#: mała litera, którą UTS #39 mapuje na zwykłą małą literę łacińską, ma ten odpowiednik (α a, γ y, ι i, ν v, ο o, ρ p, σ o);
#: pozostałe – odpowiednik pary WIELKICH liter zapisany małymi (Β/B -> β b, Ε/E -> ε e, Ζ/Z, Η/H, Κ/K, Μ/M, Τ/T, Υ/Y, Χ/X).
#: Poza zakresem (jeden znak po casefold ma dwa kształty): wielkie „Ν” (casefold „ν” = „v”, nie „n”) i sigma księżycowa „ϲ”
#: (NFKC daje „σ” = „o”, nie „c”).
SZKIELET_GR_LAC: dict[str, str] = {
    "α": "a", "β": "b", "γ": "y", "ε": "e", "ζ": "z", "η": "h", "ι": "i", "κ": "k", "μ": "m", "ν": "v", "ο": "o",
    "ρ": "p", "σ": "o", "τ": "t", "υ": "y", "χ": "x", "ϳ": "j",
}
_SZKIELET = str.maketrans({**SZKIELET_CYR_LAC, **SZKIELET_GR_LAC})
_ZNAKI_SZKIELETU = re.compile("[" + "".join(SZKIELET_CYR_LAC) + "".join(SZKIELET_GR_LAC) + "]")
_BEZ_DIAKRYTYKOW = {ord("ł"): "l", ord("đ"): "d", ord("ø"): "o", ord("ı"): "i", ord("æ"): "ae", ord("œ"): "oe"}


def normalizuj(s: str) -> str:
    """NFKC, NBSP i inne białe znaki → pojedyncza spacja, myślniki → „-”, małe litery (casefold), bez brzegów."""
    s = unicodedata.normalize("NFKC", s).translate(_FORMATUJACE).translate(_MYSLNIKI)
    return _BIALE.sub(" ", s).strip().casefold()


def same_alnum(s: str) -> str:
    """Tylko litery i cyfry (po NFKC, casefold): usuwa spacje, myślniki, kropki i inne separatory."""
    return "".join(c for c in unicodedata.normalize("NFKC", s).translate(_FORMATUJACE).casefold() if c.isalnum())


def zloz_diakrytyki(s: str) -> str:
    """Sprowadza do liter bez znaków diakrytycznych (ą→a, ł→l, ü→u…): „Dabrowski” trafia „Dąbrowski”. Wejście
    zwykle już po `normalizuj` (małe litery)."""
    s = s.translate(_BEZ_DIAKRYTYKOW)
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def szkielet(s: str) -> str:
    """Szkielet tekstu po `normalizuj` (małe litery): litery cyrylicy i greki mylone z łacińskimi -> łacina (`SZKIELET_CYR_LAC`,
    `SZKIELET_GR_LAC`)."""
    return s.translate(_SZKIELET)


def ma_znaki_szkieletu(s: str) -> bool:
    """Czy tekst (po `normalizuj`) ma literę, którą zmienia `szkielet` (cyrylicę albo grekę o kształcie litery łacińskiej)."""
    return _ZNAKI_SZKIELETU.search(s) is not None


def zloz_szkielet(s: str) -> str:
    """Postać złożona do porównania wariantowego: szkielet bez znaków diakrytycznych (`zloz_diakrytyki(szkielet(s))`)."""
    return zloz_diakrytyki(szkielet(s))


def wzor_inicjalow(tekst: str) -> re.Pattern:
    """Dokładny wzorzec inicjałów (`INICJALY`: „JK”, „J.K.”, „K.”, „jk”) na tekście po `normalizuj`: litery i kropki jak
    w wartości (białe znaki wartości i po kropce – dowolna liczba spacji), z granicami – przed i po wzorcu nie ma litery
    ani cyfry („JK” nie trafia w „JKL” ani w „AJK”, „K.” nie trafia w „k.c.”)."""
    czesci: list[str] = []
    for c in normalizuj(tekst):
        if c.isspace() or c == ".":
            if c == ".":
                czesci.append(r"\.")
            if not czesci or czesci[-1] != r"\s*":
                czesci.append(r"\s*")
        else:
            czesci.append(re.escape(c))
    while czesci and czesci[-1] == r"\s*":
        czesci.pop()
    return re.compile(r"(?<![^\W_])" + "".join(czesci) + r"(?![^\W_])")


def ile_inicjalow(wzor: re.Pattern, teksty: Iterable[str]) -> int:
    """Liczba trafień wzorca inicjałów (`wzor_inicjalow`) w tekstach po `normalizuj`. Jedna miara dla reguły niejednoznaczności
    sędziego plikowego (`plik.niejednoznaczne`) i dla generatorów warstwy trudnej (`trudne_wspolne.inicjaly_jednoznaczne`):
    inicjały są niejednoznaczne, gdy wzorzec trafia w CAŁYM tekście dokumentu (razem z gold – także dopasowanie przechodzące
    przez granicę gold, np. honoryfikat „M.” spoza gold i inicjał gold „L.”: „M. L.”) częściej niż w tekstach wartości gold."""
    return sum(len(wzor.findall(t)) for t in teksty)


def polacz_przeniesienia(s: str) -> str:
    """Skleja wyrazy rozdzielone łącznikiem na końcu wiersza („Kowal-\\nski” -> „Kowalski”, „Kowal\\ufffeski” -> „Kowalski”).
    Zwykłe myślniki w obrębie wiersza zostają. To TYLKO dodatkowy widok do wyszukiwania (wyraz złożony „Nowak-\\nKowalski” ma
    też zapis niesklejony, który sędzia przeszukuje równolegle)."""
    return _PRZENIESIENIE.sub("", s)
