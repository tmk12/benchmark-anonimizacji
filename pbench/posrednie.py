"""Identyfikacja pośrednia (spec §11 pkt 4, zadanie H5): pole manifestu `posrednie`, jego walidacja i agregacja miary.

Kombinacja to kilka informacji, z których łącznie da się wskazać osobę nienazwaną w dokumencie (funkcja + firma, rzadka
choroba + zakład pracy, wiek + mała miejscowość, działka + GPS). Pole `posrednie` wpisu manifestu warstwy trudnej:

    [{"id": "k1", "rodzaj": "<przypadek posrednie_*>",
      "skladniki": [{"id": "k1.<rola>", "rola": "<rola>", "tekst": "<tekst w dokumencie>", "miejsce": "<miejsce>",
                     "wartosc_id": "<id wartości gold>" | null, "rdzen": ["<fragment tekstu>", ...]}, ...]}, ...]

`wartosc_id` – identyfikator wartości `gold_tekst` (składnik będący zwykłą kategorią gold: ORGANIZACJA, MIEJSCOWOSC, ZDROWIE,
ADRES…); null – składnik spoza kategorii (funkcja, wiek, rok urodzenia, szkoła, numer działki, GPS): NIE jest gold miary
głównej, jest tylko tutaj. `rdzen` – rdzeń identyfikujący: fragmenty `tekst` w kolejności, rozłączne (wiek – liczba „47”, rok –
rok, szkoła – numer albo nazwa, działka – numer i identyfikator obrębu, GPS – liczby współrzędnych bez liter półkul i symboli,
choroba – nazwa bez słów „choroba/zespół/disease…”, pozostałe – cały tekst). Kombinacja ma co najmniej dwa składniki; wyjątek
– `ROLE_JEDNOSKLADNIKOWE` (numer działki i współrzędne GPS domu – każde samo wskazuje dom, więc każde jest osobną kombinacją
jednoskładnikową). Wpisy trzonu nie mają pola (trzon bez zmian bajtowych), pozostałe przypadki warstwy trudnej – pustą listę.

**Miara** (osobna, poza punktami T/P – `metodyka/posrednie.md`): kombinacja jest „przerwana” u uczestnika, gdy co najmniej
jeden jej składnik NIE jest widoczny w wyniku. Widoczny = pełny wyciek RDZENIA składnika regułą sędziego (tekst –
`sedzia.tekst`, pliki – `sedzia.plik`, z OCR tam, gdzie dotyczy), tą samą co dla gold: zamaskowanie samej etykiety („-letni”,
„obręb”, litery „E”) nie przerywa kombinacji, zamaskowanie liczby – przerywa. Składnik gold ocenia się z kategorią swojej
wartości; składnik spoza gold – z kategorią reguły `kategoria_reguly` (oznaczenie z liczbą: identyfikator, funkcja: tokeny
słów). Odsetek kombinacji przerwanych – `agreguj` (ogółem, per rodzaj, per rola kombinacji jednoskładnikowej – działka i GPS
osobno – i per język, bootstrap po dokumentach); błąd sędziego na dokumencie = jego kombinacje nieprzerwane (`nieprzerwane`,
fail-closed), poza kombinacjami nieocenianymi z oryginału (`None` u wszystkich uczestników – poza mianownikiem).
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

import numpy as np

from . import przypadki as P

KLUCZE_KOMBINACJI: tuple[str, ...] = ("id", "rodzaj", "skladniki")
KLUCZE_SKLADNIKA: tuple[str, ...] = ("id", "rola", "tekst", "miejsce", "wartosc_id", "rdzen")
#: Role, których składnik sam tworzy kombinację (jednoskładnikową): numer działki z obrębem i współrzędne GPS domu – każde samo
#: wskazuje nieruchomość, w której mieszka osoba-cel (orzeczenie kontrolera do przeglądu H5, I1).
ROLE_JEDNOSKLADNIKOWE: frozenset[str] = frozenset({"dzialka", "gps"})
#: Role składników spoza gold, które są oznaczeniem z liczbą albo nazwą własną (wiek, rok, szkoła, numer działki, współrzędne):
#: oceniane regułą identyfikatora (ciąg znaków alfanumerycznych – zamaskowanie samej liczby „47” w „47-letni” albo numeru szkoły
#: przerywa składnik; reguła tokenów pomija tokeny krótsze niż `min_dl_tokenu`, a „52°13′47″N” nie ma żadnego liczącego się tokenu).
ROLE_JAK_ID: frozenset[str] = frozenset({"wiek", "rok_urodzenia", "szkola", "dzialka", "gps"})
#: Kategoria reguły dla ról `ROLE_JAK_ID` (należy do `KATEGORIE_ID` sędziów) i dla pozostałych składników spoza gold (reguła
#: tokenów słów: poza `KATEGORIE_ID` i kategoriami „jak identyfikator”). To tylko wybór reguły – nie kategoria gold, nie waga.
KATEGORIA_ID = "IDENTYFIKATOR"
KATEGORIA_SLOWNA = "WLASNE"
#: Ziarno i liczba powtórzeń bootstrapu (jak inne miary: 1000 powtórzeń po dokumentach, 95%).
ZIARNO_BOOTSTRAP = 20261031
POWTORZENIA = 1000


def kategoria_reguly(rola: str) -> str:
    """Kategoria, której regułą sędzia ocenia składnik spoza gold o roli `rola`."""
    return KATEGORIA_ID if rola in ROLE_JAK_ID else KATEGORIA_SLOWNA


def zakresy_rdzenia(tekst: str, rdzen: Iterable[str]) -> list[tuple[int, int]] | None:
    """Fragmenty rdzenia jako przedziały [start, end) w `tekst` składnika: każdy szukany za końcem poprzedniego (kolejność
    i rozłączność). None – któregoś fragmentu nie ma (pusty fragment też)."""
    wynik: list[tuple[int, int]] = []
    od = 0
    for r in rdzen:
        i = tekst.find(r, od) if r else -1
        if i == -1:
            return None
        wynik.append((i, i + len(r)))
        od = i + len(r)
    return wynik


def odcinki_rdzenia(tekst: str, rdzen: Iterable[str]) -> list[str]:
    """Rdzeń jako odcinki tekstu do szukania bez offsetów (sędzia plikowy): kolejne fragmenty rozdzielone wyłącznie znakami
    niealfanumerycznymi tworzą jeden odcinek („50”, „10”, „32.3” → „50°10′32.3”; „52.276167”, „16.726554” → cały zapis)."""
    zakresy = zakresy_rdzenia(tekst, rdzen) or [(0, len(tekst))]
    odcinki = [list(zakresy[0])]
    for a, b in zakresy[1:]:
        if any(c.isalnum() for c in tekst[odcinki[-1][1]:a]):
            odcinki.append([a, b])
        else:
            odcinki[-1][1] = b
    return [tekst[a:b] for a, b in odcinki]


def wystapienia(tekst: str, fraza: str) -> list[tuple[int, int]]:
    """Wszystkie (nienakładające się) wystąpienia `fraza` w `tekst` jako przedziały [start, end)."""
    wynik: list[tuple[int, int]] = []
    i = tekst.find(fraza) if fraza else -1
    while i != -1:
        wynik.append((i, i + len(fraza)))
        i = tekst.find(fraza, i + len(fraza))
    return wynik


def sprawdz(wpis: dict[str, Any]) -> None:
    """Walidacja pola `posrednie` wpisu manifestu (ValueError). Brak pola (trzon) albo pusta lista – poprawne. Kombinacja:
    klucze `KLUCZE_KOMBINACJI`, rodzaj z `P.POSREDNIE`, co najmniej dwa składniki (jeden – tylko składnik roli z
    `ROLE_JEDNOSKLADNIKOWE`); składnik: klucze `KLUCZE_SKLADNIKA`, `id` unikalne w dokumencie, niepusty tekst, `wartosc_id` =
    null albo identyfikator z `gold_tekst` o tym samym tekście, `rdzen` – niepusta lista fragmentów `tekst` w kolejności,
    rozłącznych, każdy ze znakiem alfanumerycznym."""
    kombinacje = wpis.get("posrednie")
    if kombinacje is None:
        return
    if not isinstance(kombinacje, list):
        raise ValueError("posrednie: oczekiwana lista")
    gold = {}
    for g in wpis.get("gold_tekst", []):
        gold.setdefault(g["wartosc_id"], []).append(g["tekst"])
    ids: set[str] = set()
    for k in kombinacje:
        if not isinstance(k, dict) or set(k) != set(KLUCZE_KOMBINACJI):
            raise ValueError(f"posrednie: kombinacja {k!r} – klucze {KLUCZE_KOMBINACJI}")
        if k["rodzaj"] not in P.POSREDNIE:
            raise ValueError(f"posrednie: nieznany rodzaj {k['rodzaj']!r}")
        if not isinstance(k["skladniki"], list) or not k["skladniki"]:
            raise ValueError(f"posrednie: kombinacja {k['id']!r} bez składników")
        if len(k["skladniki"]) == 1 and (not isinstance(k["skladniki"][0], dict)
                                         or k["skladniki"][0].get("rola") not in ROLE_JEDNOSKLADNIKOWE):
            raise ValueError(f"posrednie: kombinacja {k['id']!r} ma mniej niż dwa składniki (jeden – tylko role "
                             f"{sorted(ROLE_JEDNOSKLADNIKOWE)})")
        for x in (k["id"], *(s.get("id") if isinstance(s, dict) else None for s in k["skladniki"])):
            if not isinstance(x, str) or not x or x in ids:
                raise ValueError(f"posrednie: identyfikator {x!r} pusty albo powtórzony")
            ids.add(x)
        for s in k["skladniki"]:
            if not isinstance(s, dict) or set(s) != set(KLUCZE_SKLADNIKA):
                raise ValueError(f"posrednie: składnik {s!r} – klucze {KLUCZE_SKLADNIKA}")
            if not isinstance(s["tekst"], str) or not s["tekst"].strip() or not isinstance(s["rola"], str) or not s["rola"]:
                raise ValueError(f"posrednie: składnik {s['id']!r} bez tekstu albo roli")
            if s["wartosc_id"] is not None and s["tekst"] not in gold.get(s["wartosc_id"], ()):
                raise ValueError(f"posrednie: składnik {s['id']!r} – brak wartości gold {s['wartosc_id']!r} o tym tekście")
            r = s["rdzen"]
            if (not isinstance(r, list) or not r or not all(isinstance(x, str) and any(c.isalnum() for c in x) for x in r)
                    or zakresy_rdzenia(s["tekst"], r) is None):
                raise ValueError(f"posrednie: składnik {s['id']!r} – rdzeń {r!r} nie jest ciągiem fragmentów tekstu")


def do_manifestu(kombinacje: list[dict[str, Any]], wpis: dict[str, Any], tekst: str) -> list[dict[str, Any]]:
    """Kombinacje generatora (`trudne_posrednie.kombinacje`) jako pole manifestu: miejsce składnika gold = miejsce jego wartości
    w `gold_tekst` (po przycięciu dokumentu do formatu), składnik spoza gold stoi w treści. Sprawdza, że tekst składnika spoza gold
    występuje w tekście poziomu 1 dokładnie raz, a wartość składnika gold – w `gold_tekst` (ValueError)."""
    miejsca = {g["wartosc_id"]: g["miejsce"] for g in wpis["gold_tekst"]}
    wynik = []
    for k in kombinacje:
        skladniki = []
        for s in k["skladniki"]:
            if s["wartosc_id"] is None:
                if len(wystapienia(tekst, s["tekst"])) != 1:
                    raise ValueError(f"składnik {s['id']!r} ({s['tekst']!r}) nie występuje w tekście dokładnie raz")
                miejsce = s["miejsce"]
            elif s["wartosc_id"] in miejsca:
                miejsce = miejsca[s["wartosc_id"]]
            else:
                raise ValueError(f"składnik {s['id']!r}: wartość {s['wartosc_id']!r} poza gold_tekst")
            skladniki.append({**s, "miejsce": miejsce})
        wynik.append({"id": k["id"], "rodzaj": k["rodzaj"], "skladniki": skladniki})
    return wynik


def ocena_kombinacji(k: dict[str, Any], przerwana: bool | None, widoczne: list[str]) -> dict[str, Any]:
    """Rekord oceny kombinacji `k` (pole `posrednie` rekordu `pbench.ocen`): `{id, rodzaj, przerwana, widoczne}`, a kombinacja
    jednoskładnikowa (`ROLE_JEDNOSKLADNIKOWE`) ma też `rola` – działka i GPS raportowane osobno (`agreguj`, `podrodzaje`)."""
    wynik: dict[str, Any] = {"id": k["id"], "rodzaj": k["rodzaj"], "przerwana": przerwana, "widoczne": widoczne}
    if len(k["skladniki"]) == 1:
        wynik["rola"] = k["skladniki"][0]["rola"]
    return wynik


def nieprzerwane(kombinacje: list[dict[str, Any]], oryginal: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Ocena fail-closed kombinacji dokumentu bez oceny sędziego (błąd sędziego): każda kombinacja NIEPRZERWANA, wszystkie
    składniki widoczne – jak dokument bez wyniku uczestnika (`metodyka/punktacja.md`: dokument z błędem = z wyciekiem);
    kombinacje zostają w mianowniku. `oryginal` – ocena kopii oryginału tym samym sędzią (gdy udała się): kombinacja nieoceniona
    na oryginale (`przerwana` = None – składnik bez liczącej się jednostki albo niewidoczny w oryginale) jest nieoceniona także
    tutaj – nie wchodzi do mianownika u nikogo, także u uczestnika z błędem sędziego (uwaga m1 przeglądu H5)."""
    bez_oceny = {k["id"] for k in oryginal or () if k.get("przerwana") is None}
    return [ocena_kombinacji(k, None if k["id"] in bez_oceny else False, [s["id"] for s in k["skladniki"]])
            for k in kombinacje]


# ----------------------------------------------------------------------------- agregacja
def _miara(dokumenty: list[tuple[int, int]], rng: np.random.Generator, powtorzenia: int, ufnosc: float) -> dict[str, Any]:
    """Odsetek przerwanych = Σ przerwane / Σ ocenione po dokumentach; przedział – bootstrap percentylowy po dokumentach."""
    k = np.array([d[0] for d in dokumenty], dtype=np.int64)
    n = np.array([d[1] for d in dokumenty], dtype=np.int64)
    razem = int(n.sum())
    wynik: dict[str, Any] = {"dokumenty": len(dokumenty), "kombinacje": razem, "przerwane": int(k.sum()),
                             "odsetek": float(k.sum() / razem) if razem else None, "przedzial": None}
    if razem:
        idx = rng.integers(0, len(dokumenty), size=(powtorzenia, len(dokumenty)))
        mian = n[idx].sum(axis=1)
        proby = np.divide(k[idx].sum(axis=1), mian, out=np.full(powtorzenia, np.nan), where=mian > 0)
        alfa = (1 - ufnosc) / 2
        wynik["przedzial"] = [float(np.nanquantile(proby, alfa)), float(np.nanquantile(proby, 1 - alfa))]
    return wynik


def agreguj(rekordy: Iterable[dict[str, Any]], powtorzenia: int = POWTORZENIA, ziarno: int = ZIARNO_BOOTSTRAP,
            ufnosc: float = 0.95) -> dict[str, Any]:
    """Odsetek kombinacji przerwanych w rekordach ocen JEDNEGO uczestnika (`pbench.ocen`, pole `posrednie` – sędzia tekstowy
    albo plikowy): `ogolem`, `rodzaje` (przypadek `posrednie_*`), `podrodzaje` (kombinacje jednoskładnikowe po roli: rodzaj ->
    rola -> miara, np. `posrednie_dzialka_gps` -> `dzialka`, `gps` – narzędzie chroniące tylko jedno z nich ma tu dwie różne
    liczby; uwaga m2 przeglądu H5) i `jezyki`, każdy `{dokumenty, kombinacje, przerwane, odsetek, przedzial}`; `nieocenione` –
    kombinacje bez oceny (składnik, który nie może wyciec, albo – pliki – niewidoczny w oryginale; poza mianownikiem u wszystkich,
    także przy błędzie sędziego – `nieprzerwane(oryginal=…)`); `bledy_sedziego` – WSZYSTKIE rekordy z `blad_sedziego` (także
    dokumenty bez kombinacji; ich kombinacje `pbench.ocen` zapisuje jako nieprzerwane – `nieprzerwane` – więc zostają
    w mianowniku). Dokument wchodzi do bootstrapu jako całość (kombinacje jednego dokumentu nie są niezależne).
    Rekordy bez pola `posrednie` (trzon, inne przypadki) są pomijane; dokument bez wyniku uczestnika albo nieobsługiwany
    sędziowie oceniają jak kopię oryginału (fail-closed: żadna kombinacja nie jest przerwana). Wynik nie wchodzi do punktów
    (`metodyka/punktacja.md`)."""
    rng = np.random.default_rng(ziarno)
    ogolem: list[tuple[int, int]] = []
    rodzaje: dict[str, list[tuple[int, int]]] = defaultdict(list)
    podrodzaje: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    jezyki: dict[str, list[tuple[int, int]]] = defaultdict(list)
    nieocenione = bledy = 0
    for r in rekordy:
        bledy += "blad_sedziego" in r
        kombinacje = r.get("posrednie")
        if not kombinacje:
            continue
        po_rodzaju: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        po_roli: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
        for k in kombinacje:
            if k["przerwana"] is None:
                nieocenione += 1
                continue
            po_rodzaju[k["rodzaj"]][0] += int(k["przerwana"])
            po_rodzaju[k["rodzaj"]][1] += 1
            if k.get("rola"):
                po_roli[(k["rodzaj"], k["rola"])][0] += int(k["przerwana"])
                po_roli[(k["rodzaj"], k["rola"])][1] += 1
        if not po_rodzaju:
            continue
        suma = (sum(v[0] for v in po_rodzaju.values()), sum(v[1] for v in po_rodzaju.values()))
        ogolem.append(suma)
        jezyki[r["jezyk"]].append(suma)
        for rodzaj, (k, n) in po_rodzaju.items():
            rodzaje[rodzaj].append((k, n))
        for klucz, (k, n) in po_roli.items():
            podrodzaje[klucz].append((k, n))
    wynik = {"ogolem": _miara(ogolem, rng, powtorzenia, ufnosc),
             "rodzaje": {x: _miara(rodzaje[x], rng, powtorzenia, ufnosc) for x in sorted(rodzaje)},
             "jezyki": {x: _miara(jezyki[x], rng, powtorzenia, ufnosc) for x in sorted(jezyki)},
             "nieocenione": nieocenione, "bledy_sedziego": bledy}
    # po pozostałych miarach: kolejne losowania bootstrapu nie zmieniają przedziałów `ogolem`/`rodzaje`/`jezyki`
    wynik["podrodzaje"] = {}
    for rodzaj, rola in sorted(podrodzaje):
        wynik["podrodzaje"].setdefault(rodzaj, {})[rola] = _miara(podrodzaje[(rodzaj, rola)], rng, powtorzenia, ufnosc)
    return wynik
