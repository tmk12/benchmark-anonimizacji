"""Generator korpusu: plan (rozkład języków, formatów i typów), podział dev/test, renderowanie plików i manifest.

CLI: `uv run pbench-korpus --ziarno 20261103 --cel korpus/` → `<cel>/<id>.<ext>` (plik), `<cel>/<id>.txt` (linearyzacja
poziomu 1) i `<cel>/manifest.jsonl` (jedna linia na dokument, posortowana po `id`).

Wynik zależy wyłącznie od ziarna głównego: ziarno dokumentu to stabilny skrót (ziarno, id), więc ani kolejność, ani
liczba procesów, ani `--limit` nie zmieniają zawartości dokumentu. Plik i tekst poziomu 1 powstają z tego samego
`Dokumentu` (po `przytnij_dla`). Pola wpisu manifestu:

* `id`, `jezyk`, `typ`, `format` (`docx|pdf|skan|xlsx|pptx|eml|msg|doc`; warstwa trudna także `rtf|odt`), `utrudnienia` (posortowane; e-mail z załącznikiem
  ma też `utrudnienia_zalacznika`), `split` (`dev|test`), `plik`, `plik_txt`, `sha256` (pliku);
* `gold_tekst` – `GoldSpan` z linearyzacji (`start`, `end`, `wartosc_id`, `kategoria`, `miejsce`, `tekst`); skan: tekst
  ze strony przed skanowaniem (plik nie ma warstwy tekstu);
* `gold_plik` – autorytatywna lista `Wartosc` z renderera (miejsce = gdzie leży w pliku; `zal:` = załącznik e-maila);
* `gold_obrazy` – wartości obrazów (logo, podpis, strony skanu) i ramki: `ramki` w pikselach obrazu, `strona` (skan:
  numer strony; PDF: `polozenia` = (id wartości, strona od 1, ramka w pt od lewego dolnego rogu));
* `ostrzezenia` – np. wartości zgubione przez konwersję DOC.

Wartości z obrazów nie trafiają do `gold_tekst`. E-mail z załącznikiem: załącznik to `notatka` zbudowana tym samym
`Generator`-em i `Kontekst`-em (osoby, sąd i sprawa się powtarzają).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from .budowa import Wynik, zbuduj_z_kontekstem
from .dane import Generator
from .dane.wspolne import BazowyGenerator
from .linearyzacja import linearyzuj_z_wartosciami
from .model import Dokument, Obraz, Wartosc
from .szablony import JEZYKI, SZABLONY, TYPY, TYPY_DODATKOWE, TYPY_PRYWATNE
from .utrudnienia import (UTRUDNIENIA_DOCX, UTRUDNIENIA_EML, UTRUDNIENIA_PDF, UTRUDNIENIA_PPTX, UTRUDNIENIA_XLSX,
                          przytnij_dla)

ZIARNO = 20261103
LICZEBNOSC_PL = 500
LICZEBNOSC_INNE = 125
#: Udziały formatów w każdym języku (%; kolejność rozstrzyga remisy przy zaokrąglaniu z zachowaniem sumy).
UDZIALY_FORMATOW: tuple[tuple[str, int], ...] = (
    ("docx", 30), ("pdf", 20), ("skan", 10), ("xlsx", 10), ("pptx", 8), ("eml", 8), ("msg", 7), ("doc", 7),
)
UDZIAL_DEV = 0.2
#: Typy medyczne (łącznie `LICZBA_MEDYCZNYCH` z 1000) i dokumenty prywatne (osoby fizyczne; `TYPY_PRYWATNE`),
#: które zajmują zwolnione miejsca (`LICZBA_PRYWATNYCH`).
TYPY_MEDYCZNE: tuple[str, ...] = ("med_wypis", "med_zaswiadczenie", "med_skierowanie")
LICZBA_MEDYCZNYCH = 67
LICZBA_PRYWATNYCH = 67
#: Prawdopodobieństwo wylosowania utrudnienia formatu (papier firmowy częściej – jest typowy).
P_UTRUDNIENIA = 0.6
P_PAPIER_FIRMOWY = 0.8
#: Typy „papierowe” – tylko one trafiają do skanów (med_skierowanie istnieje tylko po polsku).
TYPY_SKANU: tuple[str, ...] = ("umowa", "pozew", "pelnomocnictwo", "wezwanie", "wyrok", "odpis_rejestru", "faktura",
                               "med_wypis", "med_zaswiadczenie", "med_skierowanie", "cv", *TYPY_PRYWATNE)
_TYPY_ARKUSZA = ("lista_plac", "faktura")
_NIETEKSTOWE = frozenset({"lista_plac", "prezentacja", "email"})
#: Utrudnienia dozwolone w formacie (skan: widoczne na kartce – zob. `pbench.render.skan.UTRUDNIENIA_SKAN`).
_UTRUDNIENIA_FORMATU: dict[str, frozenset[str]] = {
    "docx": UTRUDNIENIA_DOCX, "doc": UTRUDNIENIA_DOCX, "pdf": UTRUDNIENIA_PDF, "xlsx": UTRUDNIENIA_XLSX,
    "pptx": UTRUDNIENIA_PPTX, "eml": UTRUDNIENIA_EML, "msg": UTRUDNIENIA_EML,
    "skan": frozenset({"papier_firmowy", "tabele", "przypisy", "podpis"}),
    "rtf": UTRUDNIENIA_DOCX, "odt": UTRUDNIENIA_DOCX,       # warstwa trudna (H4b), zob. `WYMUSZONE_UTRUDNIENIA`
}
ROZSZERZENIA = {"docx": "docx", "pdf": "pdf", "skan": "pdf", "xlsx": "xlsx", "pptx": "pptx", "eml": "eml",
                "msg": "msg", "doc": "doc", "rtf": "rtf", "odt": "odt"}
#: Formaty warstwy trudnej spoza trzonu (H4b, `formaty_rtf_odt`): utrudnienia jak w DOCX (`_UTRUDNIENIA_FORMATU`), a te, bez
#: których plik nie miałby wszystkich miejsc formatu (nagłówek/stopka, tabela, komentarz, metadane), są zawsze włączone.
WYMUSZONE_UTRUDNIENIA: dict[str, frozenset[str]] = {
    f: frozenset({"papier_firmowy", "tabele", "komentarze", "metadane"}) for f in ("rtf", "odt")}


@dataclass(frozen=True)
class Pozycja:
    """Pozycja planu korpusu: dokument do wygenerowania."""

    id: str
    jezyk: str
    typ: str
    format: str


#: Warstwa wpisu manifestu bez pola `warstwa` (trzon korpusu nie ma go – opublikowane sumy kontrolne manifestu trzonu).
WARSTWA_TRZON = "trzon"


def warstwa(wpis: dict[str, Any]) -> str:
    """Warstwa wpisu manifestu: `trzon` (brak pola `warstwa`) albo `trudne` (warstwa trudnych przypadków)."""
    return wpis.get("warstwa", WARSTWA_TRZON)


def ziarno_dokumentu(ziarno: int, id_dok: str) -> int:
    """Stabilne ziarno dokumentu – zależy tylko od ziarna głównego i identyfikatora."""
    return int.from_bytes(hashlib.sha256(f"{ziarno}:{id_dok}".encode()).digest()[:8], "big")


def _klucz(ziarno: int, *czesci: str) -> str:
    return hashlib.sha256(":".join((str(ziarno), *czesci)).encode()).hexdigest()


def _najwiekszych_reszt(wagi: list[float], suma: int) -> list[int]:
    """Podział `suma` proporcjonalny do `wagi` (metoda największych reszt; remisy – kolejność wag)."""
    calk = [int(w) for w in wagi]
    reszty = sorted(range(len(wagi)), key=lambda i: (-(wagi[i] - calk[i]), i))
    for i in reszty[:suma - sum(calk)]:
        calk[i] += 1
    return calk


def _typy_formatu(jezyk: str, fmt: str) -> list[str]:
    istnieje = [t for t in (*TYPY, *TYPY_DODATKOWE.get(jezyk, ())) if (jezyk, t) in SZABLONY]   # bez `TYPY_PRYWATNE`
    if fmt == "xlsx":
        return [t for t in _TYPY_ARKUSZA if t in istnieje]
    if fmt == "pptx":
        return ["prezentacja"]
    if fmt in ("eml", "msg"):
        return ["email"]
    if fmt == "skan":
        return [t for t in TYPY_SKANU if t in istnieje]
    return [t for t in istnieje if t not in _NIETEKSTOWE]


#: Proporcje dokumentów medycznych między `TYPY_MEDYCZNE` (54 : 55 : 25) – rozkład docelowy dzieli
#: `LICZBA_MEDYCZNYCH` w tych proporcjach.
PROPORCJE_MEDYCZNE: tuple[int, ...] = (54, 55, 25)
#: Typy prawne, z których uzupełnia się miejsca prywatne, gdyby zwolnionych dokumentów medycznych było mniej niż
#: `LICZBA_PRYWATNYCH` (zależy od ziarna planu wyjściowego), i formaty tekstowe, w których wolno je zamienić.
_TYPY_PRAWNE = ("umowa", "pozew", "wezwanie", "pelnomocnictwo", "wyrok", "protokol", "notatka")
_FORMATY_TEKSTOWE = ("docx", "pdf", "skan", "doc")


def _przydziel_typy(wiersze: dict[str, list[tuple[str, str]]], ziarno: int) -> dict[str, list[tuple[str, str]]]:
    """Rozkład typów na planie wyjściowym (`wiersze`: język → lista (format, typ) z cyklicznego przydziału).

    1. **Medyczne:** dokładnie `LICZBA_MEDYCZNYCH` pozycji zostaje typami `TYPY_MEDYCZNE`, w proporcjach
       `PROPORCJE_MEDYCZNE` (metoda największych reszt; remis – kolejność `TYPY_MEDYCZNE`); w obrębie typu liczba pozycji
       zostających w języku jest proporcjonalna do jego udziału w planie wyjściowym (ta sama metoda). Które pozycje
       zostają, rozstrzyga skrót (ziarno, język, typ, numer pozycji).
    2. **Prywatne:** zwolnione pozycje medyczne zajmują typy `TYPY_PRYWATNE` – dokładnie `LICZBA_PRYWATNYCH` pozycji,
       w języku proporcjonalnie do udziału zwolnionych pozycji. Pozycje języka posortowane po (format, skrót ziarna i
       pozycji) dostają typy cyklicznie, a licznik cyklu biegnie przez języki w kolejności `JEZYKI`: typy prywatne liczą
       się 23/22/22 (pierwszy dostaje nadwyżkę), a w każdym języku i formacie różnią się najwyżej o jedną sztukę.
    3. **Wyrównanie:** plan wyjściowy daje liczbę dokumentów medycznych zależną od ziarna (nie zawsze 134). Zwolnionych
       ponad `LICZBA_PRYWATNYCH` dostaje zwykłe typy dopuszczone w ich formacie (bez medycznych i prywatnych); gdy
       zwolnionych jest mniej, brakujące miejsca prywatne zajmują pozycje typów `_TYPY_PRAWNE` w formatach tekstowych."""
    poz = {t: {j: [i for i, (_, typ) in enumerate(w) if typ == t] for j, w in wiersze.items()} for t in TYPY_MEDYCZNE}
    lacznie = [sum(len(v) for v in poz[t].values()) for t in TYPY_MEDYCZNE]
    cele = _najwiekszych_reszt([LICZBA_MEDYCZNYCH * p / sum(PROPORCJE_MEDYCZNE) for p in PROPORCJE_MEDYCZNE],
                               LICZBA_MEDYCZNYCH)
    if any(c > n for c, n in zip(cele, lacznie)):
        raise ValueError(f"plan wyjściowy ma za mało dokumentów medycznych: {lacznie}, potrzeba {cele}")
    zwolnione: dict[str, list[int]] = {j: [] for j in wiersze}
    for t, cel, n in zip(TYPY_MEDYCZNE, cele, lacznie):
        jezyki = [j for j in wiersze if poz[t][j]]
        zostaje = _najwiekszych_reszt([len(poz[t][j]) * cel / n for j in jezyki], cel)
        for j, ile in zip(jezyki, zostaje):
            kolejnosc = sorted(poz[t][j], key=lambda i: _klucz(ziarno, "med", j, t, str(i)))
            zwolnione[j] += kolejnosc[ile:]
    for j in zwolnione:
        zwolnione[j].sort(key=lambda i: _klucz(ziarno, "zwolnione", j, str(i)))
    wszystkie = sum(len(v) for v in zwolnione.values())
    wynik = {j: list(w) for j, w in wiersze.items()}
    if wszystkie >= LICZBA_PRYWATNYCH:
        kwoty = _najwiekszych_reszt([LICZBA_PRYWATNYCH * len(zwolnione[j]) / wszystkie for j in wiersze],
                                    LICZBA_PRYWATNYCH)
    else:
        kwoty = [len(zwolnione[j]) for j in wiersze]
    prywatne: dict[str, list[int]] = {}
    for j, k in zip(wiersze, kwoty):
        prywatne[j] = zwolnione[j][:k]
        for n, i in enumerate(zwolnione[j][k:]):        # nadwyżka zwolnionych: zwykłe typy formatu
            fmt = wiersze[j][i][0]
            zwykle = [t for t in _typy_formatu(j, fmt) if t not in TYPY_MEDYCZNE]
            random.Random(_klucz(ziarno, "zwykle", j, fmt)).shuffle(zwykle)
            wynik[j][i] = (fmt, zwykle[n % len(zwykle)])
    brak = LICZBA_PRYWATNYCH - sum(len(v) for v in prywatne.values())
    if brak > 0:                                         # za mało zwolnionych: uzupełnienie z typów prawnych
        kandydaci = {j: sorted((i for i, (fmt, typ) in enumerate(w) if typ in _TYPY_PRAWNE and fmt in _FORMATY_TEKSTOWE),
                               key=lambda i: _klucz(ziarno, "uzupelnienie", j, str(i))) for j, w in wiersze.items()}
        dodatkowo = _najwiekszych_reszt([brak * len(kandydaci[j]) / sum(map(len, kandydaci.values())) for j in wiersze],
                                        brak)
        for j, k in zip(wiersze, dodatkowo):
            prywatne[j] += kandydaci[j][:k]
    licznik = 0
    for j in wiersze:
        for i in sorted(prywatne[j], key=lambda i: (wiersze[j][i][0], _klucz(ziarno, "prywatne", j, str(i)))):
            wynik[j][i] = (wiersze[j][i][0], TYPY_PRYWATNE[licznik % len(TYPY_PRYWATNE)])
            licznik += 1
    return wynik


def zaplanuj(ziarno: int = ZIARNO, jezyki: tuple[str, ...] | None = None, formaty: tuple[str, ...] | None = None,
             limit: int | None = None) -> list[Pozycja]:
    """Plan korpusu posortowany po `id`. Identyfikatory nie zależą od filtrów `jezyki`/`formaty`/`limit`
    (filtry tylko wybierają pozycje; `limit` – deterministycznie przez skrót identyfikatora).

    Najpierw plan wyjściowy: format wg udziałów, typ cyklicznie po przetasowaniu typów dopuszczonych w
    formacie (bez `TYPY_PRYWATNE`). Potem `_przydziel_typy` zmniejsza liczbę dokumentów medycznych do
    `LICZBA_MEDYCZNYCH` i oddaje zwolnione miejsca typom prywatnym (dokładnie `LICZBA_PRYWATNYCH`)."""
    wiersze_j: dict[str, list[tuple[str, str]]] = {}
    for jezyk in JEZYKI:
        n = LICZEBNOSC_PL if jezyk == "pl" else LICZEBNOSC_INNE
        ile = _najwiekszych_reszt([n * u / 100 for _, u in UDZIALY_FORMATOW], n)
        wiersze: list[tuple[str, str]] = []
        for (fmt, _), k in zip(UDZIALY_FORMATOW, ile):
            typy = _typy_formatu(jezyk, fmt)
            random.Random(_klucz(ziarno, "typy", jezyk, fmt)).shuffle(typy)
            wiersze += [(fmt, typy[i % len(typy)]) for i in range(k)]   # round-robin po przetasowaniu
        wiersze_j[jezyk] = wiersze
    pelny: list[Pozycja] = []
    for jezyk, wiersze in _przydziel_typy(wiersze_j, ziarno).items():
        numery: Counter = Counter()
        for fmt, typ in wiersze:
            numery[typ] += 1
            pelny.append(Pozycja(f"{jezyk}-{typ}-{numery[typ]:04d}", jezyk, typ, fmt))
    plan = [p for p in pelny if (jezyki is None or p.jezyk in jezyki) and (formaty is None or p.format in formaty)]
    if limit is not None and limit < len(plan):
        plan = sorted(plan, key=lambda p: _klucz(ziarno, "limit", p.id))[:limit]
    return sorted(plan, key=lambda p: p.id)


def przydziel_split(plan: list[Pozycja], ziarno: int = ZIARNO) -> dict[str, str]:
    """Podział dev/test (~20/80) stratyfikowany po języku × typie × formacie, niezależny od kolejności `plan`.

    W każdej warstwie dev dostaje floor(0,2·n) dokumentów, a brakujące do `round(0,2·n_języka)` – warstwy tego samego
    języka z największą resztą (remisy: skrót ziarna i warstwy), więc każdy język ma ~20% dev. Który dokument warstwy
    trafia do dev – rozstrzyga skrót ziarna i `id`."""
    warstwy: dict[tuple[str, str, str], list[str]] = {}
    for p in plan:
        warstwy.setdefault((p.jezyk, p.typ, p.format), []).append(p.id)
    wynik: dict[str, str] = {}
    for jezyk in sorted({k[0] for k in warstwy}):
        klucze = sorted(k for k in warstwy if k[0] == jezyk)
        wagi = [UDZIAL_DEV * len(warstwy[k]) for k in klucze]
        calk = [int(w) for w in wagi]
        kolejnosc = sorted(range(len(klucze)),
                           key=lambda i: (-(wagi[i] - calk[i]), _klucz(ziarno, "split", *klucze[i])))
        n_jezyka = sum(len(warstwy[k]) for k in klucze)
        for i in kolejnosc[:round(UDZIAL_DEV * n_jezyka) - sum(calk)]:
            calk[i] += 1
        for k, ile_dev in zip(klucze, calk):
            for j, i in enumerate(sorted(warstwy[k], key=lambda i: _klucz(ziarno, "dev", i))):
                wynik[i] = "dev" if j < ile_dev else "test"
    return wynik


def losuj_utrudnienia(p: Pozycja, ziarno: int, ma_podpis: bool) -> set[str]:
    """Utrudnienia formatu: każde niezależnie (p=0,6; papier firmowy 0,8; `podpis` tylko gdy dokument ma podpis)."""
    rng = random.Random(_klucz(ziarno, "utrudnienia", p.id))
    wynik = set()
    for u in sorted(_UTRUDNIENIA_FORMATU[p.format]):
        szansa = P_PAPIER_FIRMOWY if u == "papier_firmowy" else P_UTRUDNIENIA
        wylosowane = rng.random() < szansa   # losowanie zawsze, żeby `ma_podpis` nie przesuwało pozostałych
        if wylosowane and (u != "podpis" or ma_podpis):
            wynik.add(u)
    return wynik | WYMUSZONE_UTRUDNIENIA.get(p.format, frozenset())


# ----------------------------------------------------------------------------- generacja dokumentu
def _wartosc_json(w: Wartosc) -> dict[str, Any]:
    return w.to_dict()


def _obraz_json(o: Obraz, polozenia: list | None = None) -> dict[str, Any]:
    wpis: dict[str, Any] = {"id": o.id, "wartosci": [_wartosc_json(w) for w in o.wartosci],
                            "ramki": [[wid, list(bbox)] for wid, bbox in o.ramki]}
    if o.id.rsplit("-strona", 1)[-1].isdigit() and "-strona" in o.id:
        wpis["strona"] = int(o.id.rsplit("-strona", 1)[-1])
    if polozenia:
        ids = {w.id for w in o.wartosci}
        wpis["polozenia"] = [[wid, nr, [round(float(x), 2) for x in r]] for wid, nr, r in polozenia if wid in ids]
    return wpis


def _renderuj(p: Pozycja, d: Dokument, plik: Path, utr: set[str],
              seed: int, budowa: Any = None) -> tuple[list[Wartosc], list[dict], list[str]]:
    """Renderuje `d` w formacie `p.format` (poza pocztą); zwraca (gold pliku, gold obrazów, ostrzeżenia)."""
    ostrzezenia: list[str] = []
    f = p.format
    if f == "docx":
        from .render.docx import renderuj_docx
        r = renderuj_docx(d, plik, utr)
        return r.wartosci, [_obraz_json(o) for o in r.obrazy], ostrzezenia
    if f == "doc":
        from .render.doc import renderuj_doc
        r = renderuj_doc(d, plik, utr)
        return r.wartosci, [_obraz_json(o) for o in r.obrazy], list(r.ostrzezenia)
    if f in ("rtf", "odt"):            # warstwa trudna (H4b): konwersja LibreOffice'em jak DOC
        from .render.odt import renderuj_odt
        from .render.rtf import renderuj_rtf
        r = (renderuj_rtf if f == "rtf" else renderuj_odt)(d, plik, utr)
        return r.wartosci, [_obraz_json(o) for o in r.obrazy], list(r.ostrzezenia)
    if f == "pdf":
        from .render.pdf import renderuj_pdf
        r = renderuj_pdf(d, plik, utr) if budowa is None else renderuj_pdf(d, plik, utr, kolumny=budowa.kolumny)
        return r.wartosci, [_obraz_json(o, r.umiejscowienie) for o in r.obrazy], ostrzezenia
    if f == "skan":
        from .render.skan import renderuj_skan
        r = renderuj_skan(d, plik, random.Random(seed ^ 0x5CA4), utr)
        ostrzezenia += [f"skan: brak ramki wartości {w.id}" for w in r.nieznalezione]
        return r.wartosci, [_obraz_json(o) for o in r.obrazy], ostrzezenia
    if f == "xlsx":
        from .render.xlsx import render_xlsx
        return render_xlsx(d, plik, utr), [], ostrzezenia
    if f == "pptx":
        from .render.pptx import renderuj_pptx
        r = renderuj_pptx(d, plik, utr)
        return r.wartosci, [_obraz_json(o) for o in r.obrazy], ostrzezenia
    raise ValueError(f"nieznany format: {f!r}")


def _renderuj_poczte(p: Pozycja, d: Dokument, plik: Path, utr: set[str], zal: Dokument | None,
                     utr_zal: set[str] | None) -> tuple[list[Wartosc], list[dict], list[str]]:
    if p.format == "eml":
        from .render.eml import renderuj_eml as render
    else:
        from .render.msg import renderuj_msg as render
    r = render(d, plik, utr, zal, utr_zal)
    return r.wartosci, [_obraz_json(o) for o in r.obrazy_zalacznika], []


def _plik_ze_skrotem(plik: Path) -> str:
    return hashlib.sha256(plik.read_bytes()).hexdigest()


class Budowa(Protocol):
    """Własny sposób budowy dokumentu (warstwa trudnych przypadków, `pbench.trudne`); trzon korpusu go nie używa."""

    def dokument(self, p: Pozycja, seed: int) -> tuple[Wynik, BazowyGenerator]: ...

    def zalacznik(self, p: Pozycja, seed: int, gen: BazowyGenerator, wynik: Wynik) -> Wynik: ...

    #: liczba kolumn renderera PDF (1 = zwykły układ)
    kolumny: int

    def po_renderze(self, plik: Path, d: Dokument, gold_obrazy: list[dict[str, Any]]) -> tuple[list[Wartosc], list[dict[str, Any]]]: ...


def _wpis_gold_tekstu(s: Any, w: Wartosc) -> dict[str, Any]:
    wpis = {"start": s.start, "end": s.end, "wartosc_id": s.wartosc_id, "kategoria": s.kategoria,
            "miejsce": s.miejsce, "tekst": w.tekst}
    # pola warstwy trudnej tylko gdy ustawione: wpisy trzonu pozostają bajtowo takie same
    if w.translit is not None:
        wpis["translit"] = w.translit
    if w.encja is not None:
        wpis["encja"] = w.encja
    if w.cechy:
        wpis["cechy"] = list(w.cechy)
    return wpis


def generuj_dokument(p: Pozycja, ziarno: int, split: str, cel: Path,
                     maskuj: Callable[[Dokument], Dokument] | None = None,
                     budowa: Budowa | None = None) -> dict[str, Any]:
    """Buduje, przycina, renderuje i linearyzuje jeden dokument; zapisuje plik i `.txt`, zwraca wpis manifestu.

    `maskuj` (tylko dla sanity sędziego plikowego – „idealny uczestnik”): funkcja zamieniająca teksty wartości w
    dokumencie (i w załączniku e-maila) tuż przed renderowaniem; plik jest wtedy plikiem „po anonimizacji”.
    `budowa` (warstwa trudnych przypadków): własna budowa dokumentu i załącznika zamiast szablonów trzonu."""
    seed = ziarno_dokumentu(ziarno, p.id)
    if budowa is None:
        gen = Generator(p.jezyk, seed)
        wynik = zbuduj_z_kontekstem(SZABLONY[(p.jezyk, p.typ)], gen, random.Random(f"pbench-korpus:{seed}"))
    else:
        wynik, gen = budowa.dokument(p, seed)
    d = wynik.dokument
    d.id, d.format = p.id, p.format
    utr = losuj_utrudnienia(p, ziarno, ma_podpis=any(e.rodzaj == "podpis" for e in d.elementy))
    # skan przycinamy jak PDF (renderer skanu robi to samo): tekst poziomu 1 = to, co jest na kartce
    d = przytnij_dla("pdf" if p.format == "skan" else p.format, d, utr)
    tekst, spany, wartosci_spanow = linearyzuj_z_wartosciami(d)
    if maskuj is not None:
        d = maskuj(d)

    plik = cel / f"{p.id}.{ROZSZERZENIA[p.format]}"
    wpis: dict[str, Any] = {"id": p.id, "jezyk": p.jezyk, "typ": p.typ, "format": p.format,
                            "utrudnienia": sorted(utr), "split": split, "plik": plik.name, "plik_txt": f"{p.id}.txt"}
    if p.format in ("eml", "msg"):
        zal = utr_zal = None
        if "zalacznik" in utr:
            zal0 = (zbuduj_z_kontekstem(SZABLONY[(p.jezyk, "notatka")], gen, random.Random(f"pbench-zal:{seed}"),
                                        wspolne=wynik) if budowa is None else budowa.zalacznik(p, seed, gen, wynik)).dokument
            zal0.id, zal0.format = f"{p.id}-zal", "docx"
            utr_zal = losuj_utrudnienia(Pozycja(zal0.id, p.jezyk, "notatka", "docx"), ziarno,
                                        ma_podpis=any(e.rodzaj == "podpis" for e in zal0.elementy))
            zal = przytnij_dla("docx", zal0, utr_zal)
            if maskuj is not None:
                zal = maskuj(zal)
            wpis["utrudnienia_zalacznika"] = sorted(utr_zal)
        gold_plik, gold_obrazy, ostrzezenia = _renderuj_poczte(p, d, plik, utr, zal, utr_zal)
        if budowa is not None:      # warstwa trudnych przypadków: załączniki przypadku dopisane do gotowej wiadomości
            dodatkowe, gold_obrazy = budowa.po_renderze(plik, d, gold_obrazy)
            gold_plik = [*gold_plik, *dodatkowe]
    else:
        gold_plik, gold_obrazy, ostrzezenia = _renderuj(p, d, plik, utr, seed, budowa)
        if budowa is not None:      # warstwa trudnych przypadków: treść ukryta i dodatki dopisane do gotowego pliku
            dodatkowe, gold_obrazy = budowa.po_renderze(plik, d, gold_obrazy)
            gold_plik = [*gold_plik, *dodatkowe]
    (cel / wpis["plik_txt"]).write_bytes(tekst.encode("utf-8"))
    wpis["sha256"] = _plik_ze_skrotem(plik)
    wpis["gold_tekst"] = [_wpis_gold_tekstu(s, w) for s, w in zip(spany, wartosci_spanow)]
    wpis["gold_plik"] = [_wartosc_json(w) for w in gold_plik]
    wpis["gold_obrazy"] = gold_obrazy
    wpis["ostrzezenia"] = ostrzezenia
    return wpis


def _zadanie(arg: tuple[Pozycja, int, str, str]) -> dict[str, Any]:
    p, ziarno, split, cel = arg
    try:
        return generuj_dokument(p, ziarno, split, Path(cel))
    except Exception as e:  # noqa: BLE001 - błąd jednego dokumentu nie ma zatrzymać reszty; raportujemy na końcu
        return {"id": p.id, "blad": f"{type(e).__name__}: {e}"}


def statystyki(manifest: list[dict[str, Any]]) -> dict[str, Any]:
    """Liczby dokumentów: łącznie, per język × format × split oraz ostrzeżenia."""
    licz: Counter = Counter((w["jezyk"], w["format"], w["split"]) for w in manifest)
    return {"dokumentow": len(manifest),
            "po_jezyku_formacie_splicie": {f"{j}/{f}/{s}": n for (j, f, s), n in sorted(licz.items())},
            "po_splicie": dict(Counter(w["split"] for w in manifest)),
            "ostrzezenia": sum(len(w["ostrzezenia"]) for w in manifest)}


def generuj(cel: Path, ziarno: int = ZIARNO, procesy: int | None = None, limit: int | None = None,
            jezyki: tuple[str, ...] | None = None, formaty: tuple[str, ...] | None = None,
            postep: bool = True) -> list[dict[str, Any]]:
    """Generuje korpus w `cel` i zapisuje `manifest.jsonl`; zwraca wpisy (posortowane po `id`).

    Split liczony jest na pozycjach faktycznie generowanych (przy `--limit` – na podzbiorze).
    Błędy pojedynczych dokumentów: wpisy bez `blad` zostają zapisane, a funkcja zgłasza `RuntimeError` z listą błędów."""
    cel = Path(cel)
    cel.mkdir(parents=True, exist_ok=True)
    plan = zaplanuj(ziarno, jezyki, formaty, limit)
    split = przydziel_split(plan, ziarno)
    zadania = [(p, ziarno, split[p.id], str(cel)) for p in plan]
    n_proc = procesy or max(1, (os.cpu_count() or 2) - 2)
    wyniki: list[dict[str, Any]] = []
    start = time.monotonic()
    if n_proc == 1:
        iterator: Any = map(_zadanie, zadania)
        pula = None
    else:
        pula = ProcessPoolExecutor(max_workers=n_proc)
        iterator = pula.map(_zadanie, zadania, chunksize=1)
    try:
        for i, w in enumerate(iterator, 1):
            wyniki.append(w)
            if postep and i % 50 == 0:
                print(f"[{i}/{len(zadania)}] {time.monotonic() - start:.0f} s", file=sys.stderr, flush=True)
    finally:
        if pula is not None:
            pula.shutdown()
    bledy = [w for w in wyniki if "blad" in w]
    dobre = sorted((w for w in wyniki if "blad" not in w), key=lambda w: w["id"])
    with (cel / "manifest.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for w in dobre:
            f.write(json.dumps(w, ensure_ascii=False) + "\n")
    if bledy:
        raise RuntimeError("błędy generacji: " + "; ".join(f"{b['id']}: {b['blad']}" for b in bledy[:10])
                           + (f" (łącznie {len(bledy)})" if len(bledy) > 10 else ""))
    return dobre


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pbench-korpus", description="Generuje syntetyczny korpus benchmarku.")
    ap.add_argument("--ziarno", type=int, default=ZIARNO)
    ap.add_argument("--cel", type=Path, default=Path("korpus"))
    ap.add_argument("--procesy", type=int, default=None, help="liczba procesów (domyślnie nproc-2)")
    ap.add_argument("--limit", type=int, default=None, help="tylko N dokumentów (deterministyczny podzbiór; testy)")
    ap.add_argument("--jezyki", default=None, help="lista oddzielona przecinkami, np. pl,en")
    ap.add_argument("--formaty", default=None, help="lista oddzielona przecinkami, np. docx,pdf")
    a = ap.parse_args(argv)
    wpisy = generuj(a.cel, a.ziarno, a.procesy, a.limit,
                    tuple(a.jezyki.split(",")) if a.jezyki else None,
                    tuple(a.formaty.split(",")) if a.formaty else None)
    st = statystyki(wpisy)
    (a.cel / "statystyki.json").write_text(json.dumps(st, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(st["po_splicie"]), "dokumentów:", st["dokumentow"], "ostrzeżeń:", st["ostrzezenia"])
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
