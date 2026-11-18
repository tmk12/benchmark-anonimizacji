"""Sędzia tekstowy: wyciek wartości, fałszywe wykrycia (FP), pokrycie znakowe i char-F2 na jednym dokumencie.

Wejście: `gold` (GoldSpan-y z manifestu, `gold_z_wpisu`), `wykrycia` uczestnika na tym samym tekście (offsety znakowe
[start, end)), `tekst` i `RegulyWycieku`. Etykiety uczestnika są ignorowane (label-blind). Wszystkie rozstrzygnięcia są
zapisane w tym module i w `RegulyWycieku`; tu skrót reguł (to ich brzmienie trafia do prerejestracji):

1. Wartość = wszystkie `GoldSpan`-y o tym samym `wartosc_id` (części rozbite na komórki/runy). Wartość wycieka, jeśli
   w którymkolwiek z jej spanów pozostaje odsłonięty „fragment identyfikujący”. Pokrycie liczy się na formie wstawionej
   do tekstu (`tekst[start:end]`), więc odmiana (np. „Jana Kowalskiego”) nie wymaga żadnej normalizacji.
2. Znak jest pokryty, jeśli leży w którymkolwiek wykryciu (wykrycia scala się; poza tekstem są przycinane).
3. Kategorie spoza `KATEGORIE_ID`: span dzieli się na tokeny `\\w+` (Unicode). Token liczy się, jeśli ma
   ≥ `min_dl_tokenu` znaków (domyślnie 3); jest odsłonięty, jeśli ma ciągły niepokryty fragment długości
   ≥ max(`min_dl_tokenu`, ceil(`ulamek_tokenu`·długość)), domyślnie ułamek 0,5 (odporność na 1–2 znaki różnicy
   granic). W EMAIL/URL nie liczą się tokeny: schemat (http/https/ftp), `www`, `mailto` i końcowa etykieta domeny
   (TLD); część lokalna i pozostałe etykiety domeny liczą się. Wyciek =
   którykolwiek liczący się token odsłonięty. Rodzaj: „pelny” – wszystkie liczące się tokeny wartości odsłonięte,
   „czesciowy” – tylko część. Wartość bez liczącego się tokenu (np. „ul.”, numer domu) nie może wyciec – poza inicjałami (pkt 4).
   Słowa opisowe nazw organizacji (`SLOWA_OPISOWE_ORGANIZACJI`, J1 – „Kancelaria”, „Radców Prawnych”, „PartG mbB”, „LLP”) w
   kategorii ORGANIZACJA liczą się do „pelny”, ale odsłonięte same nie dają wycieku: wyciek = odsłonięty liczący się token spoza
   nich albo wszystkie liczące się tokeny odsłonięte („pelny”, także nazwa złożona z samych słów opisowych).
4. Kategorie z `KATEGORIE_ID` (identyfikatory, numery, adresy sieciowe, telefon, kod pocztowy – J3): bierze się znaki
   alfanumeryczne spanu poza etykietami (`ETYKIETY_ID`, J1 – „Routing No.”, „Account No.”, „Claim No.”, „n.º”: słowa etykiety
   w spanie gold rachunku i sygnatury są pomijane jak separatory; ciąg łączy się ponad etykietą – końcówka jednego numeru i początek
   następnego tworzą jeden ciąg, co tylko zaostrza ocenę)
   (separatory – spacje, myślniki, kropki, ukośniki – są pomijane i nie przerywają ciągu). Wyciek = odsłonięty ciąg
   ≥ `min_cyfr_id` (domyślnie 4) kolejnych takich znaków; dla wartości krótszej niż próg próg = jej długość. Rodzaj:
   „pelny” – żaden znak alfanumeryczny nie jest pokryty, inaczej „czesciowy”. Inicjały (`KATEGORIE_INICJALOW`, H6a) – tą samą
   regułą ciągu alfanumerycznego, z progiem równym długości (wyciek = wszystkie litery inicjałów odsłonięte: „J.K.” z pokrytym
   „K” nie wycieka, „Pan K.” z odsłoniętym „K” – wycieka).
5. Wartość wycieka raz (niezależnie od liczby jej spanów); `miejsce` = miejsce pierwszego spanu z odsłoniętym
   fragmentem; `kategoria` = kategoria pierwszego spanu wartości.
6. FP: `fp_znaki` = niebiałe znaki pokryte wykryciami poza WSZYSTKIMI spanami gold (po scaleniu wykryć);
   `fp_spany` = liczba ciągłych odcinków pokrycia (scalone wykrycia: nakładające się/zagnieżdżone/stykające się = jeden)
   bez przecięcia z żadnym spanem gold.
7. `pokrycie_znakowe` = pokryte niebiałe znaki gold / niebiałe znaki gold (1.0 gdy gold pusty). Precyzja znakowa
   = pokryte gold / (pokryte gold + `fp_znaki`) (1.0 gdy nic nie pokryto); `char_f2` = F-beta z β = 2 z precyzji i
   pokrycia (0.0 gdy mianownik 0).
8. `kategorie` (miara „w deklarowanym zakresie”): oceniane są tylko wartości z tych kategorii (wycieki, pokrycie,
   char-F2); FP liczone jak zawsze względem całego gold, a wykrycia na gold spoza zakresu nie są ani trafieniem,
   ani FP.
9. `posrednie` (identyfikacja pośrednia, H5 – pole manifestu, `pbench.posrednie`; osobna miara poza punktami): kombinacja
   jest przerwana, gdy któryś jej składnik NIE jest widoczny. Widoczny = pełny wyciek RDZENIA składnika (pole `rdzen`:
   fragmenty tekstu składnika – liczba wieku, numer działki z obrębem, liczby współrzędnych…) regułą pkt 3–4: każdy fragment
   rdzenia to osobny span, rodzaj „pelny” = wszystkie liczące się jednostki fragmentów odsłonięte w całości; reszta tekstu
   składnika („-letni”, „obręb”, litera półkuli) nie liczy się. Składnik gold – rdzeń w spanie jego `wartosc_id` o tekście
   składnika (span o innym tekście – część wartości rozbitej – cały span), kategoria wartości; składnik spoza gold – rdzeń
   w każdym wystąpieniu jego tekstu osobno, kategoria reguły `posrednie.kategoria_reguly(rola)`; widoczny, gdy któreś
   wystąpienie ma rdzeń w całości odsłonięty. Składnik bez liczącej się jednostki (nie może wyciec) – kombinacja nieoceniona
   (`przerwana` = None). Wystąpienia składników spoza gold (cały tekst) są wyłączone z FP (pkt 6): ich zamaskowanie to nie
   jest nadmiarowe maskowanie (tylko w dokumentach z kombinacjami; pokrycie i char-F2 liczą się nadal względem gold).

Homoglify (H6a): sędzia tekstowy ocenia pokrycie offsetów oryginalnego tekstu, więc zapis wartości (homoglify, transliteracja)
nie wymaga porównania napisów – uczestnik, który „naprawi” homoglify u siebie, ale nie oznaczy znaków wartości, ma wyciek; szkielet
znaków mylących (`normalizacja.szkielet`) dotyczy sędziego plikowego. `OcenaDokumentu.ocenione_id` – identyfikatory wartości
ocenionych (miara opisowa poziomu encji w `pbench.ocen`).

Implementacja jest liniowa względem długości tekstu i liczby wykryć (tablice pokrycia numpy, bez O(n²)).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import yaml

from .. import posrednie as _posrednie
from ..linearyzacja import GoldSpan
from ..model import Wykrycie

#: Kategorie ocenianie jako identyfikatory (ciąg alfanumeryczny zamiast tokenów słownych).
KATEGORIE_ID: frozenset[str] = frozenset({
    "PESEL", "NIP", "REGON", "KRS", "DOWOD", "PASZPORT", "PRAWO_JAZDY", "NR_ID", "NR_REJESTRACYJNY",
    "KSIEGA_WIECZYSTA", "SYGNATURA", "NR_REJESTRU", "IDENTYFIKATOR", "MRZ", "DNI", "CIF", "NUSS", "SSN", "EIN",
    "MBI", "NINO", "NHS", "NR_PODATKOWY", "VAT", "SVNR", "KVNR", "NIR", "SIREN", "RACHUNEK", "KARTA", "KRYPTO",
    "IP", "MAC", "UUID", "TELEFON",
    # (J3) kod pocztowy – ciąg znaków alfanumerycznych jak identyfikator, jednakowo w każdym języku („28-333”, „28333”, „28 333”;
    # dotąd tokeny słowne: polski „28-333” w sędzi plikowym nie mógł wyciec, a 5-cyfrowe kody DE/ES/FR – tak)
    "KOD_POCZTOWY",
})
#: Inicjały (parafy, „Pan K.”): ciąg alfanumeryczny jak `KATEGORIE_ID`, próg = długość (orzeczenie kontrolera do H2, H6a).
KATEGORIE_INICJALOW: frozenset[str] = frozenset({"INICJALY"})

#: Etykiety w spanach gold identyfikatorów (orzeczenie kontrolera J1, A/S1): gold rachunku i sygnatury bywa zapisany z etykietą
#: („Routing No. 015757092, Account No. 60431799632”, „Claim No. QB-2020-014548”, „Procedimiento Ordinario n.º 123/2024”).
#: Słowa etykiety nie identyfikują wartości – sędzia tekstowy i plikowy pomijają je przy liczeniu wycieku (reguła ciągu
#: alfanumerycznego obejmuje tylko znaki spoza etykiet); wyciek to nadal odsłonięty numer, pełny albo częściowy wg tych samych progów.
#: Listy per kategoria i język (spis dla prerejestracji); stosowana jest suma języków danej kategorii (span gold nie niesie
#: języka), a etykieta pasuje tylko jako całe słowa (granice liter i cyfr), bez rozróżniania wielkości liter. Na liście są
#: wyłącznie czyste etykiety – oznaczenia stałe, takie same w każdej wartości (orzeczenie kontrolera J1-fix1, I1 wariant a).
#: NIE są etykietami opisowe części oznaczenia sprawy, w każdym języku tak samo: polski wydział i repertorium („VII Ca”,
#: „NS-REJ.KRS”), hiszpański rodzaj postępowania („Procedimiento Ordinario”, „Juicio Verbal”, „Rollo de Apelación”…),
#: niemieckie „O”/„C” w Aktenzeichen, angielskie prefiksy wydziału („QB”, „KB”) i „CV”/„cv”; także litery tablicy
#: rejestracyjnej i kod kraju IBAN – zostają ciągiem identyfikatora (odsłonięte przy zamaskowanym numerze wyciekają częściowo).
ETYKIETY_ID: dict[str, dict[str, tuple[str, ...]]] = {
    "RACHUNEK": {
        "pl": ("Nr rachunku", "Numer rachunku", "Nr konta", "Numer konta", "IBAN"),
        "en": ("Routing No.", "Routing Number", "Account No.", "Account Number", "Sort Code", "IBAN"),
        "de": ("Kontonummer", "Konto-Nr.", "IBAN"),
        "es": ("N.º de cuenta", "Número de cuenta", "IBAN"),
        "fr": ("N° de compte", "Numéro de compte", "IBAN"),
    },
    "SYGNATURA": {
        "pl": ("Sygn. akt", "Sygnatura akt", "Sygn."),
        "en": ("Claim No.", "Case No.", "Case Number", "No."),
        "de": ("Az.", "Aktenzeichen", "Geschäftszeichen"),
        # „Autos” (= akta, jak „Sygn. akt”) i „n.º”; rodzaj postępowania (`pbench.dane.es`) to część oznaczenia, nie etykieta
        "es": ("n.º", "Autos"),
        # „RG” – répertoire général: jeden rejestr, ta sama litera w każdym numerze sprawy (`pbench.dane.fr`), część etykiety
        # „N° RG” – nie odróżnia sprawy (w przeciwieństwie do repertorium polskiego czy rodzaju postępowania hiszpańskiego)
        "fr": ("N° RG", "RG n°", "RG", "n°"),
    },
}


def _wzor_etykiet(etykiety: Iterable[str]) -> re.Pattern:
    """Alternatywa etykiet (najdłuższe najpierw): spacje w etykiecie = dowolne białe znaki; granica przed etykietą i po
    etykiecie kończącej się literą/cyfrą (sąsiedni znak nie jest literą ani cyfrą)."""
    czesci = []
    for e in sorted(set(etykiety), key=len, reverse=True):
        w = r"\s+".join(re.escape(s) for s in e.split())
        czesci.append(r"(?<![^\W_])" + w + (r"(?![^\W_])" if e[-1].isalnum() else ""))
    return re.compile("|".join(czesci), re.IGNORECASE)


_WZORY_ETYKIET_ID: dict[str, re.Pattern] = {k: _wzor_etykiet(e for lista in j.values() for e in lista)
                                             for k, j in ETYKIETY_ID.items()}


def zakresy_etykiet(span: str, kategoria: str) -> list[tuple[int, int]]:
    """Zakresy [od, do) etykiet (`ETYKIETY_ID`) w tekście spanu gold identyfikatora kategorii `kategoria`."""
    wzor = _WZORY_ETYKIET_ID.get(kategoria)
    return [m.span() for m in wzor.finditer(span)] if wzor else []


#: Słowa opisowe nazw organizacji (orzeczenie kontrolera J1, D): rodzaj kancelarii i forma prawna („Kancelaria Radców Prawnych”,
#: „PartG mbB”, „SELARL”, „LLP”). Odsłonięte same nie dają wycieku częściowego nazwy (sędzia tekstowy: kategoria ORGANIZACJA;
#: sędzia plikowy: słowa zastrzeżone leksykonu, `plik.SLOWA_ZASTRZEZONE`); nazwa odsłonięta w całości nadal wycieka („pelny”).
#: Bez słów, które bywają nazwiskami albo rdzeniem nazwy (np. „Law”, „Chambers” – nazwiska, „Lex” z „Kancelaria Lex”).
#: Postać po casefold (porównanie bez wielkości liter); tokeny krótsze niż `min_dl_tokenu` („sp”, „AG”) i tak się nie liczą.
SLOWA_OPISOWE_ORGANIZACJI: dict[str, frozenset[str]] = {
    "pl": frozenset({"kancelaria", "kancelarii", "prawna", "prawnicza", "radców", "radcy", "prawnych", "prawnego",
                     "adwokacka", "adwokacki", "adwokatów", "notarialna", "wspólnicy", "wspólników", "spółka",
                     "komandytowa", "partnerska", "jawna", "akcyjna", "cywilna"}),
    "en": frozenset({"llp", "llc", "ltd", "limited", "inc", "corp", "plc", "solicitors", "attorneys", "lawyers",
                     "associates", "legal", "firm", "partners"}),
    "de": frozenset({"kanzlei", "rechtsanwälte", "rechtsanwalt", "rechtsanwältin", "rechtsanwaltskanzlei",
                     "rechtsanwaltsgesellschaft", "partg", "mbb", "partnerschaft", "partnerschaftsgesellschaft", "partner",
                     "kollegen", "gmbh", "ggmbh", "ohg", "haftungsbeschränkt"}),
    "es": frozenset({"abogados", "abogado", "asesores", "letrados", "asociados", "bufete", "despacho", "slp", "slu",
                     "sociedad", "profesional"}),
    "fr": frozenset({"cabinet", "avocats", "avocat", "associés", "selarl", "selas", "scp", "aarpi", "sarl", "sas",
                     "sasu", "eurl", "société"}),
}
#: Suma języków `SLOWA_OPISOWE_ORGANIZACJI` (span gold nie niesie języka).
SLOWA_OPISOWE: frozenset[str] = frozenset().union(*SLOWA_OPISOWE_ORGANIZACJI.values())
#: Kategorie, w których słowa opisowe nie dają same wycieku (sędzia tekstowy).
KATEGORIE_OPISOWE: frozenset[str] = frozenset({"ORGANIZACJA"})

_TOKEN = re.compile(r"\w+")
_BIALE = re.compile(r"\s+")
_PREFIKS_URL = re.compile(r"(?:mailto:)?(?:(?:https?|ftp)://)?(?:www\.)?", re.IGNORECASE)
_NAGLOWEK_REGUL = "reguly_wycieku"
_BLOK_YAML = re.compile(r"```ya?ml[ \t]*\n(.*?)```", re.DOTALL)


@dataclass(frozen=True)
class RegulyWycieku:
    """Progi reguły wycieku (zamrażane w `metodyka/prerejestracja.md`, blok YAML pod kluczem `reguly_wycieku`)."""

    min_dl_tokenu: int = 3
    min_cyfr_id: int = 4
    #: Token (nie-ID) jest odsłonięty, gdy ma niepokryty ciąg ≥ max(min_dl_tokenu, ceil(ulamek_tokenu · długość)).
    ulamek_tokenu: float = 0.5
    #: Sędzia plikowy: token występujący w gold ≥ tego ułamka dokumentów danego języka jest „leksykonem korpusu”
    #: (imiona, formy prawne, miasta powtarzane w danych fikcyjnych) i nie liczy się jako pojedynczy token wycieku.
    prog_leksykonu: float = 0.05
    kategorie_id: frozenset[str] = field(default=KATEGORIE_ID)

    @classmethod
    def wczytaj(cls, sciezka: str | Path) -> RegulyWycieku:
        """Czyta blok YAML z prerejestracji. Brak pliku → domyślne; plik bez bloku `reguly_wycieku` lub z nieznanym
        kluczem → `ValueError`."""
        p = Path(sciezka)
        if not p.exists():
            return cls()
        for blok in _BLOK_YAML.findall(p.read_text(encoding="utf-8")):
            dane = yaml.safe_load(blok)
            if isinstance(dane, dict) and _NAGLOWEK_REGUL in dane:
                return cls(**_przygotuj(dane[_NAGLOWEK_REGUL] or {}))
        raise ValueError(f"{p}: brak bloku yaml z kluczem `{_NAGLOWEK_REGUL}:`")


def _przygotuj(dane: dict[str, Any]) -> dict[str, Any]:
    znane = {f.name for f in fields(RegulyWycieku)}
    nieznane = set(dane) - znane
    if nieznane:
        raise ValueError(f"nieznane klucze reguł wycieku: {sorted(nieznane)}")
    wynik = dict(dane)
    if "kategorie_id" in wynik:
        wynik["kategorie_id"] = frozenset(wynik["kategorie_id"])
    return wynik


@dataclass
class OcenaDokumentu:
    """Wynik oceny jednego dokumentu przez uczestnika."""

    #: (wartosc_id, kategoria, miejsce, rodzaj: "pelny"|"czesciowy") – po jednej pozycji na wyciekłą wartość.
    wycieki: list[tuple[str, str, str, str]]
    fp_znaki: int
    fp_spany: int
    pokrycie_znakowe: float
    char_f2: float
    #: liczba ocenianych wartości, które mogły wyciec (miały choć jeden liczący się fragment).
    wartosci_ocenione: int = 0
    #: identyfikacja pośrednia (pkt 9): po kombinacji `{id, rodzaj, przerwana: bool|None, widoczne: [id składników]}`;
    #: None – dokument bez pola `posrednie` (trzon) albo ocena bez niego.
    posrednie: list[dict[str, Any]] | None = None
    #: identyfikatory wartości ocenionych (`wartosci_ocenione` = ich liczba), w kolejności gold
    ocenione_id: list[str] = field(default_factory=list)


def gold_z_wpisu(wpis: dict[str, Any]) -> list[GoldSpan]:
    """`GoldSpan`-y z pola `gold_tekst` wpisu manifestu korpusu."""
    return [GoldSpan(g["start"], g["end"], g["wartosc_id"], g["kategoria"], g["miejsce"]) for g in wpis["gold_tekst"]]


def _maska(n: int, przedzialy: list[tuple[int, int]]) -> np.ndarray:
    """Maska boolowska długości n pokryta sumą przedziałów [s, e) (liniowo, bez pętli po znakach)."""
    if not przedzialy:
        return np.zeros(n, dtype=bool)
    a = np.array(przedzialy, dtype=np.int64)
    delta = np.bincount(a[:, 0], minlength=n + 1) - np.bincount(a[:, 1], minlength=n + 1)
    return np.cumsum(delta[:n]) > 0


def _niebiale(tekst: str) -> np.ndarray:
    return ~_maska(len(tekst), [m.span() for m in _BIALE.finditer(tekst)])


def _ignorowane(span: str, kategoria: str) -> list[tuple[int, int]]:
    """Zakresy nieidentyfikujące w EMAIL/URL: schemat, `www`, `mailto` i końcowa etykieta domeny (TLD)."""
    if kategoria not in ("EMAIL", "URL"):
        return []
    wynik = []
    pre = _PREFIKS_URL.match(span).end()
    if pre:
        wynik.append((0, pre))
    if "@" in span:
        host_od = span.rindex("@") + 1
    elif kategoria == "URL":
        host_od = pre
    else:
        return wynik
    host_do = len(span)
    for znak in "/?#":
        i = span.find(znak, host_od)
        if i != -1:
            host_do = min(host_do, i)
    host = span[host_od:host_do]
    host = host.split(":", 1)[0]  # port
    kropka = host.rfind(".")
    if kropka != -1:
        wynik.append((host_od + kropka + 1, host_od + len(host)))
    return wynik


def _najdluzszy_niepokryty(cov: bytes, a: int, b: int) -> int:
    maks = seria = 0
    for i in range(a, b):
        if cov[i]:
            seria = 0
        else:
            seria += 1
            maks = max(maks, seria)
    return maks


def _jednostki(tekst: str, s: GoldSpan, cov: bytes, r: RegulyWycieku) -> list[tuple[bool, bool]]:
    """Liczące się jednostki spanu jako (odsłonięta – sama daje wyciek, „pełna” – odsłonięta w całości); pusta lista = span nie
    może przeciec. Słowo opisowe nazwy organizacji (`SLOWA_OPISOWE`) nie jest odsłonięte samo, ale liczy się do „pełnej”."""
    span = tekst[s.start:s.end]
    if s.kategoria in r.kategorie_id or s.kategoria in KATEGORIE_INICJALOW:
        etykiety = zakresy_etykiet(span, s.kategoria)
        poz = [i for i, c in enumerate(span) if c.isalnum() and not any(a <= i < b for a, b in etykiety)]
        if not poz:
            return []
        prog = len(poz) if s.kategoria in KATEGORIE_INICJALOW else min(r.min_cyfr_id, len(poz))
        seria = maks = 0
        pokryte = False
        for i in poz:
            if cov[s.start + i]:
                seria, pokryte = 0, True
            else:
                seria += 1
                maks = max(maks, seria)
        return [(maks >= prog, not pokryte)]
    wynik = []
    ign = _ignorowane(span, s.kategoria)
    opisowe = s.kategoria in KATEGORIE_OPISOWE
    for m in _TOKEN.finditer(span):
        dl = m.end() - m.start()
        if dl < r.min_dl_tokenu or any(a <= m.start() and m.end() <= b for a, b in ign):
            continue
        prog = max(r.min_dl_tokenu, math.ceil(r.ulamek_tokenu * dl))
        odsloniety = _najdluzszy_niepokryty(cov, s.start + m.start(), s.start + m.end()) >= prog
        wynik.append((odsloniety and not (opisowe and m.group().casefold() in SLOWA_OPISOWE), odsloniety))
    return wynik


def _scal(przedzialy: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Suma przedziałów [s, e): nakładające się lub stykające się łączone w jeden."""
    wynik: list[list[int]] = []
    for s, e in sorted(p for p in przedzialy if p[1] > p[0]):
        if wynik and s <= wynik[-1][1]:
            wynik[-1][1] = max(wynik[-1][1], e)
        else:
            wynik.append([s, e])
    return [(s, e) for s, e in wynik]


def zakresy_skladnikow(posrednie: list[dict[str, Any]], tekst: str) -> list[tuple[int, int]]:
    """Wystąpienia (przedziały [start, end) w `tekst`) składników kombinacji spoza gold (`wartosc_id` = null)."""
    return [z for k in posrednie for s in k["skladniki"] if s["wartosc_id"] is None
            for z in _posrednie.wystapienia(tekst, s["tekst"])]


def _widoczny(spany: list[GoldSpan], tekst: str, cov: bytes, reguly: RegulyWycieku) -> bool | None:
    """Pełny wyciek jednego wystąpienia (spany części wartości): wszystkie liczące się jednostki odsłonięte w całości
    (rodzaj „pelny” pkt 3–5). None – brak liczącej się jednostki."""
    jednostki = [j for s in spany for j in _jednostki(tekst, s, cov, reguly)]
    return all(p for _, p in jednostki) if jednostki else None


def _rdzen(s: dict[str, Any], od: int, kategoria: str) -> list[GoldSpan]:
    """Spany fragmentów rdzenia składnika `s` w wystąpieniu jego tekstu zaczynającym się w `od` (brak pola `rdzen` – cały tekst)."""
    zakresy = _posrednie.zakresy_rdzenia(s["tekst"], s.get("rdzen") or [s["tekst"]]) or [(0, len(s["tekst"]))]
    return [GoldSpan(od + a, od + b, s["id"], kategoria, s["miejsce"]) for a, b in zakresy]


def ocen_posrednie(posrednie: list[dict[str, Any]], gold: list[GoldSpan], cov: bytes, tekst: str,
                   reguly: RegulyWycieku) -> list[dict[str, Any]]:
    """Kombinacje identyfikacji pośredniej (pkt 9) przy pokryciu `cov` (bajt na znak tekstu, niezerowy = pokryty)."""
    po_id: dict[str, list[GoldSpan]] = {}
    for g in gold:
        po_id.setdefault(g.wartosc_id, []).append(g)
    wynik = []
    for k in posrednie:
        widoczne, oceniona = [], True
        for s in k["skladniki"]:
            if s["wartosc_id"] is not None and s["wartosc_id"] in po_id:
                spany = po_id[s["wartosc_id"]]
                cale = [g for g in spany if tekst[g.start:g.end] == s["tekst"]]
                stany = ([_widoczny(_rdzen(s, g.start, g.kategoria), tekst, cov, reguly) for g in cale] if cale
                         else [_widoczny(spany, tekst, cov, reguly)])
            else:
                kat = _posrednie.kategoria_reguly(s["rola"])
                stany = [_widoczny(_rdzen(s, a, kat), tekst, cov, reguly) for a, _ in _posrednie.wystapienia(tekst, s["tekst"])]
            if all(x is None for x in stany):
                oceniona = False
            elif any(stany):
                widoczne.append(s["id"])
        wynik.append(_posrednie.ocena_kombinacji(k, (len(widoczne) < len(k["skladniki"])) if oceniona else None, widoczne))
    return wynik


def ocen_tekst(gold: list[GoldSpan], wykrycia: list[Wykrycie], tekst: str, reguly: RegulyWycieku,
               kategorie: set[str] | None = None, posrednie: list[dict[str, Any]] | None = None) -> OcenaDokumentu:
    """Ocenia wykrycia uczestnika względem gold jednego dokumentu (reguły: docstring modułu). `posrednie` – pole manifestu
    dokumentu (pkt 9): ocena kombinacji i wyłączenie składników spoza gold z FP."""
    n = len(tekst)
    wyk = [(w.start, min(w.end, n)) for w in wykrycia if w.start < n]
    cov_mask = _maska(n, wyk)
    gold_wszystko = _maska(n, [(g.start, g.end) for g in gold])
    zakres = gold_wszystko if kategorie is None else _maska(
        n, [(g.start, g.end) for g in gold if g.kategoria in kategorie])
    niebiale = _niebiale(tekst)

    # FP (składniki identyfikacji pośredniej spoza gold – poza miarą nadmiarowości, pkt 9)
    bez_fp = gold_wszystko | _maska(n, zakresy_skladnikow(posrednie, tekst)) if posrednie else gold_wszystko
    fp_znaki = int((cov_mask & ~bez_fp & niebiale).sum())
    suma = np.concatenate(([0], np.cumsum(bez_fp)))
    fp_spany = sum(1 for s, e in _scal(wyk) if suma[e] - suma[s] == 0)

    # pokrycie znakowe i char-F2
    gold_znaki = int((zakres & niebiale).sum())
    trafione = int((zakres & cov_mask & niebiale).sum())
    pokrycie = trafione / gold_znaki if gold_znaki else 1.0
    precyzja = trafione / (trafione + fp_znaki) if trafione + fp_znaki else 1.0
    mian = 4 * precyzja + pokrycie
    f2 = 5 * precyzja * pokrycie / mian if mian else 0.0

    # wycieki wartości
    cov = cov_mask.tobytes()
    wartosci: dict[str, list[GoldSpan]] = {}
    for g in gold:
        wartosci.setdefault(g.wartosc_id, []).append(g)
    wycieki: list[tuple[str, str, str, str]] = []
    ocenione: list[str] = []
    for wid, spany in wartosci.items():
        if kategorie is not None and spany[0].kategoria not in kategorie:
            continue
        jednostki: list[tuple[bool, bool]] = []
        miejsce = miejsce_pelnej = None
        for s in spany:
            j = _jednostki(tekst, s, cov, reguly)
            if miejsce is None and any(o for o, _ in j):
                miejsce = s.miejsce
            if miejsce_pelnej is None and any(p for _, p in j):
                miejsce_pelnej = s.miejsce
            jednostki += j
        if not jednostki:
            continue
        ocenione.append(wid)
        pelny = all(p for _, p in jednostki)
        if miejsce is not None or pelny:          # pełna – także wartość z samych słów opisowych (pkt 3)
            wycieki.append((wid, spany[0].kategoria, miejsce or miejsce_pelnej, "pelny" if pelny else "czesciowy"))
    posr = ocen_posrednie(posrednie, gold, cov, tekst, reguly) if posrednie is not None else None
    return OcenaDokumentu(wycieki, fp_znaki, fp_spany, pokrycie, f2, len(ocenione), posr, ocenione)
