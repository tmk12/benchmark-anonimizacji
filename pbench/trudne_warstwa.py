"""Pełna warstwa trudnych przypadków (zadanie H6b, spec §11): rozkład per przypadek, plan, split, budowa i sumy kontrolne.

Rozkład (`ROZKLAD`) jest jedynym źródłem liczby dokumentów: przypadek -> dokumenty per język (+ uzasadnienie). Z niego
powstają plan (`zaplanuj_warstwe`), tabela w `metodyka/przypadki.md` (`tabela_rozkladu`; zgodność pilnuje test) i budowa
(`zbuduj_warstwe`, CLI `uv run pbench-trudne --cel korpus-trudne --pelna`). Warunki rozkładu (`sprawdz_rozklad`): łącznie
`LICZBA_DOKUMENTOW` ± `TOLERANCJA`, każdy przypadek ≥ `MIN_DOKUMENTOW` dokumentów i ≥ `MIN_DEV` w dev, każdy przypadek we
wszystkich językach, w których ma generator (`trudne._pary`), PL zawsze, gdy przypadek go dopuszcza (tylko
`cyrylica_dokument_uk` jest wyłącznie ukraiński).

Plan przypadku: formaty wg udziałów trzonu przeliczonych na formaty możliwe dla przypadku (jak `trudne.zaplanuj_przypadek`),
języki przydzielane kolejnym pozycjom formatu wg pozostałej części kontyngentu języka (język musi mieć typ w tym formacie),
typ – najrzadziej dotąd użyty typ języka w tym formacie – tak, żeby każdy język miał możliwie różne formaty i typy. Identyfikatory jak
w warstwie (`h-<skrót>-<język>-<typ>-<nr>`); ziarno dokumentu zależy tylko od `(ZIARNO_TRUDNE, id)`, więc dokument o tym samym
identyfikatorze co w budowie pojedynczego przypadku ma tę samą treść.

Split (`przydziel_split_warstwy`): w każdym przypadku dev = max(`MIN_DEV`, round(0,2·n)); kontyngent dev rozdzielony na
języki, a w języku na formaty metodą największych reszt z limitem – dev nie zabiera ostatniego dokumentu żadnego języka ani
formatu przypadku (split test ma je wszystkie); który dokument – rozstrzyga skrót ziarna i `id` (jak w trzonie).
`trudne.przydziel_split` (budowa pojedynczego przypadku) zaokrągla po językach, więc przypadek z 1–2 dokumentami na język
nie miałby w ogóle dev – dlatego pełna warstwa ma własny podział.

Sumy kontrolne (`sumy_kontrolne`): plik `SHA256SUMS-trudne` w formacie `sha256sum` (GNU coreutils: `<64 hex>  <ścieżka>`,
dwie spacje, tryb tekstowy, ścieżki względem katalogu warstwy, posortowane), obejmuje każdy plik dokumentu, każdy `.txt`,
`manifest.jsonl` i `statystyki.json` (te same rodzaje plików co opublikowany `korpus/SHA256SUMS-trzon`); sprawdzenie: `cd korpus-trudne && sha256sum -c ../metodyka/SHA256SUMS-trudne`.
"""
from __future__ import annotations

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
from typing import Any

from . import korpus, przypadki as P, trudne
from .trudne import PREFIKS_ID, ZIARNO_TRUDNE, PozycjaTrudna

#: Łączna liczba dokumentów warstwy (spec §11: „~300 dokumentów”) i dopuszczalne odchylenie.
LICZBA_DOKUMENTOW = 300
TOLERANCJA = 40
MIN_DOKUMENTOW = 8
MIN_DEV = 2
#: Kolejność języków w tabelach (pięć języków trzonu, potem ukraiński).
KOLEJNOSC_JEZYKOW = ("pl", "en", "es", "de", "fr", "uk")
#: Plik sum kontrolnych warstwy (do prerejestracji) – w repozytorium, obok metodyki.
PLIK_SUM = Path(__file__).resolve().parent.parent / "metodyka" / "SHA256SUMS-trudne"
#: Statystyki warstwy (w katalogu warstwy; objęte sumami jak `statystyki.json` trzonu).
PLIK_STATYSTYK = "statystyki.json"


@dataclass(frozen=True)
class Rozklad:
    """Liczba dokumentów przypadku per język i uzasadnienie (do `metodyka/przypadki.md`)."""

    jezyki: dict[str, int]
    uzasadnienie: str

    @property
    def n(self) -> int:
        return sum(self.jezyki.values())


_PIEC_8 = {"pl": 4, "en": 1, "es": 1, "de": 1, "fr": 1}         # połowa PL jak w trzonie, każdy inny język co najmniej raz
_PIEC_10 = {"pl": 2, "en": 2, "es": 2, "de": 2, "fr": 2}        # dwa formaty/typy przypadku w każdym języku
_WSTAWKI_8 = {"pl": 4, "en": 2, "de": 2}

#: Rozkład warstwy: przypadek -> języki i uzasadnienie (kolejność = rejestr `przypadki.PRZYPADKI`).
ROZKLAD: dict[str, Rozklad] = {
    P.UKRYTA_DOCX: Rozklad(_PIEC_8, "jeden format; minimum, bo każdy dokument niesie kilka rodzajów elementów ukrytych"),
    P.UKRYTA_XLSX: Rozklad(_PIEC_10, "oba typy arkusza (lista płac, faktura) w każdym języku"),
    P.UKRYTA_PPTX: Rozklad(_PIEC_8, "jeden typ (prezentacja) i jeden format; minimum"),
    P.UKRYTA_PDF: Rozklad(_PIEC_8, "jeden format; zaczernienie i niezgodna warstwa OCR w każdym języku"),
    P.UKRYTA_POCZTA: Rozklad(_PIEC_10, "oba formaty poczty (EML, MSG) w każdym języku"),
    P.ODMIANA_NAZWISK: Rozklad({"pl": 8}, "tylko polski (odmiana nazwisk i formy rodzinne to zjawisko polszczyzny)"),
    P.NAZWISKA_ZWYKLE_SLOWA: Rozklad(_PIEC_8, "minimum; pułapki pospolite w każdym języku"),
    P.ZDROBNIENIA: Rozklad(_PIEC_8, "minimum; zdrobnienia w każdym języku"),
    P.NAZWISKO_IMIE: Rozklad(_PIEC_8, "minimum; zapis NAZWISKO Imię w każdym języku"),
    P.PARAFY: Rozklad(_PIEC_8, "minimum; parafy w każdym języku"),
    P.LICZBY_SLOWNIE: Rozklad(_PIEC_8, "minimum; liczebniki słowne w każdym języku"),
    P.CYRYLICA_DOKUMENT_UK: Rozklad({"uk": 12}, "tylko ukraiński; więcej, bo sześć typów i sześć formatów (także skan i poczta)"),
    P.CYRYLICA_WSTAWKA: Rozklad(_WSTAWKI_8, "szablony wstawek są tylko w PL, EN i DE (spec §11 pkt 3: dokument PL/EN/DE)"),
    P.TRANSLITERACJA: Rozklad({"pl": 4, "en": 3, "de": 3},
                              "PL, EN, DE jak wstawki; więcej, bo dwa układy zapisów (z cyrylicą i same transliteracje)"),
    P.HOMOGLIFY: Rozklad({"pl": 4, "en": 2, "es": 2, "de": 2, "fr": 2},
                         "szablony trzonu w pięciu językach; więcej, bo osiem formatów (także XLSX, PPTX, poczta, skan)"),
    P.PISOWNIA_ROSYJSKA_IMION: Rozklad(_WSTAWKI_8, "PL, EN, DE jak wstawki (osoby ukraińskie w dokumentach tych języków)"),
    P.POSREDNIE_FUNKCJA_FIRMA: Rozklad(_PIEC_8, "minimum; miara opisowa poza punktami"),
    P.POSREDNIE_RZADKA_CHOROBA: Rozklad(_PIEC_8, "minimum; miara opisowa poza punktami"),
    P.POSREDNIE_WIEK_MIEJSCOWOSC: Rozklad(_PIEC_8, "minimum; miara opisowa poza punktami"),
    P.POSREDNIE_DZIALKA_GPS: Rozklad(_PIEC_8, "minimum; miara opisowa poza punktami"),
    P.SKROTY_PO_PELNYM: Rozklad(_PIEC_8, "minimum; dokumenty długie (> 3 okna modelu)"),
    P.GRANICA_OKNA: Rozklad(_PIEC_8, "minimum; kilka wartości na granicach okien w każdym dokumencie"),
    P.DLUGIE_LISTY_OSOB: Rozklad(_PIEC_8, "minimum; listy ≥ 100 osób (także XLSX)"),
    P.ZNAKI_ZEROWEJ_SZEROKOSCI: Rozklad(_PIEC_8, "minimum; DOCX i PDF"),
    P.RTL: Rozklad(_PIEC_8, "minimum; DOCX i PDF"),
    P.ZEPSUTY_TOUNICODE: Rozklad(_PIEC_8, "minimum; tylko PDF"),
    P.PRZENIESIENIA: Rozklad(_PIEC_8, "minimum; tylko PDF"),
    P.DWIE_KOLUMNY: Rozklad(_PIEC_8, "minimum; DOCX i PDF"),
    P.OBROCONE_STRONY: Rozklad(_PIEC_8, "minimum; PDF i skan"),
    P.SKAN_PIECZATKI: Rozklad(_PIEC_8, "minimum; DOCX i PDF"),
    P.ZRZUT_EKRANU: Rozklad(_PIEC_8, "minimum; DOCX i PDF"),
    P.ZNAK_WODNY: Rozklad(_PIEC_8, "minimum; DOCX i PDF"),
    P.CYTOWANE_WATKI_VCARD: Rozklad(_PIEC_10, "oba formaty poczty (EML, MSG) w każdym języku"),
    P.FORMATY_RTF_ODT: Rozklad(_PIEC_10, "oba formaty (RTF, ODT) w każdym języku"),
}


def liczba_dev(n: int) -> int:
    """Liczba dokumentów dev przypadku o `n` dokumentach: ~20%, co najmniej `MIN_DEV`."""
    return max(MIN_DEV, round(korpus.UDZIAL_DEV * n))


def jezyki_przypadku(przypadek: str) -> list[str]:
    """Języki, w których przypadek ma generator (kolejność `KOLEJNOSC_JEZYKOW`)."""
    jezyki = {j for j, _ in trudne._pary(przypadek)}
    return [j for j in KOLEJNOSC_JEZYKOW if j in jezyki]


def sprawdz_rozklad(rozklad: dict[str, Rozklad] = ROZKLAD) -> None:
    """ValueError, gdy rozkład łamie warunki z docstringu modułu."""
    if list(rozklad) != list(P.PRZYPADKI):
        raise ValueError("rozkład musi obejmować wszystkie przypadki rejestru w jego kolejności")
    suma = sum(r.n for r in rozklad.values())
    if abs(suma - LICZBA_DOKUMENTOW) > TOLERANCJA:
        raise ValueError(f"łącznie {suma} dokumentów, dozwolone {LICZBA_DOKUMENTOW} ± {TOLERANCJA}")
    for przypadek, r in rozklad.items():
        mozliwe = jezyki_przypadku(przypadek)
        if r.n < MIN_DOKUMENTOW or liczba_dev(r.n) < MIN_DEV:
            raise ValueError(f"{przypadek}: {r.n} dokumentów (min. {MIN_DOKUMENTOW})")
        if sorted(r.jezyki) != sorted(mozliwe) or min(r.jezyki.values()) < 1:
            raise ValueError(f"{przypadek}: języki {sorted(r.jezyki)}, przypadek ma generatory w {mozliwe}")


# ----------------------------------------------------------------------------- plan
def _formaty_przypadku(przypadek: str) -> list[tuple[str, int]]:
    """Formaty możliwe dla przypadku z udziałami (jak w `trudne.zaplanuj_przypadek`)."""
    pary = trudne._pary(przypadek)
    udzialy = (*korpus.UDZIALY_FORMATOW,
               *((f, u) for f, u in trudne.UDZIALY_DODATKOWE if f in P.FORMATY_PRZYPADKU.get(przypadek, ())))
    return [(fmt, u) for fmt, u in udzialy if any(fmt in trudne.formaty_dla(*p) for p in pary)
            and P.FORMAT_PRZYPADKU.get(przypadek, fmt) == fmt and fmt in P.FORMATY_PRZYPADKU.get(przypadek, (fmt,))]


def zaplanuj_rozklad(przypadek: str, jezyki: dict[str, int], ziarno: int = ZIARNO_TRUDNE) -> list[PozycjaTrudna]:
    """Pozycje przypadku wg kontyngentów języków (posortowane po `id`); opis algorytmu – docstring modułu."""
    pary = trudne._pary(przypadek)
    n = sum(jezyki.values())
    mozliwe = _formaty_przypadku(przypadek)
    ile = korpus._najwiekszych_reszt([n * u / sum(w for _, w in mozliwe) for _, u in mozliwe], n)
    formaty = [fmt for (fmt, _), k in zip(mozliwe, ile) for _ in range(k)]
    random.Random(korpus._klucz(ziarno, "warstwa-formaty", przypadek)).shuffle(formaty)
    # remisy języków: stała kolejność z ziarna (nie zawsze PL pierwszy)
    porzadek = sorted(jezyki, key=lambda j: korpus._klucz(ziarno, "warstwa-jezyki", przypadek, j))
    typy: dict[str, list[str]] = {}
    for j in jezyki:
        typy[j] = sorted({t for jj, t in pary if jj == j})
        random.Random(korpus._klucz(ziarno, "warstwa-typy", przypadek, j)).shuffle(typy[j])
    pozostalo = dict(jezyki)
    uzyte: Counter = Counter()
    numery: Counter = Counter()
    wynik = []
    for fmt in formaty:
        kandydaci = [j for j in porzadek if pozostalo[j] > 0 and any(fmt in trudne.formaty_dla(j, t) for t in typy[j])]
        if not kandydaci:
            raise ValueError(f"{przypadek}: żaden język z kontyngentem nie ma typu w formacie {fmt}")
        # najpierw język z największą pozostałą częścią kontyngentu, potem ten, który ma najmniej pozycji w tym formacie
        jezyk = min(kandydaci, key=lambda j: (-pozostalo[j] / jezyki[j], uzyte[(j, fmt)], porzadek.index(j)))
        pozostalo[jezyk] -= 1
        uzyte[(jezyk, fmt)] += 1
        # typ języka najrzadziej dotąd użyty, który ma ten format (remisy – kolejność przetasowanej listy typów)
        typ = min((t for t in typy[jezyk] if fmt in trudne.formaty_dla(jezyk, t)),
                  key=lambda t: (numery[(jezyk, t)], typy[jezyk].index(t)))
        numery[(jezyk, typ)] += 1
        wynik.append(PozycjaTrudna(f"{PREFIKS_ID}{P.SKROTY[przypadek]}-{jezyk}-{typ}-{numery[(jezyk, typ)]:04d}",
                                   jezyk, typ, fmt, przypadek))
    return sorted(wynik, key=lambda p: p.id)


def zaplanuj_warstwe(ziarno: int = ZIARNO_TRUDNE, rozklad: dict[str, Rozklad] = ROZKLAD,
                     przypadki: tuple[str, ...] | None = None) -> list[PozycjaTrudna]:
    """Plan całej warstwy (posortowany po `id`); `przypadki` – tylko te (identyfikatory bez zmian)."""
    plan = [p for przypadek, r in rozklad.items() if przypadki is None or przypadek in przypadki
            for p in zaplanuj_rozklad(przypadek, r.jezyki, ziarno)]
    return sorted(plan, key=lambda p: p.id)


def przydziel_split_warstwy(plan: list[PozycjaTrudna], ziarno: int = ZIARNO_TRUDNE) -> dict[str, str]:
    """Split dev/test pełnej warstwy: w każdym przypadku `liczba_dev(n)` dokumentów dev, rozdzielonych na języki i formaty
    metodą największych reszt (remisy – skrót ziarna) z limitem: dev nigdy nie zabiera ostatniego dokumentu danego języka
    ani formatu przypadku (split test, czyli punktowany, ma każdy język i każdy format przypadku). W przypadku 8-dokumentowym
    (PL 4 + po 1 EN/ES/DE/FR) dev = 2 × PL. W warstwie (język, format) dev dostają dokumenty o najmniejszym skrócie
    `(ziarno, id)`."""
    wynik: dict[str, str] = {}
    for przypadek in sorted({p.przypadek for p in plan}):
        pozycje = [p for p in plan if p.przypadek == przypadek]
        jezyki = Counter(p.jezyk for p in pozycje)
        formaty = Counter(p.format for p in pozycje)
        # format: ile dokumentów dev może jeszcze zabrać w całym przypadku (zostaje ≥ 1 w test)
        zapas_fmt = {f: k - 1 for f, k in formaty.items()}
        # język: ≥ 1 w test i tylko dokumenty formatów, które mają zapas
        limit_j = {j: min(k - 1, sum(1 for p in pozycje if p.jezyk == j and zapas_fmt[p.format] > 0))
                   for j, k in jezyki.items()}
        ile = liczba_dev(len(pozycje))
        for jezyk, ile_j in _rozdziel(jezyki, ile, ziarno, przypadek, limity=limit_j).items():
            w_jezyku = [p for p in pozycje if p.jezyk == jezyk]
            licz_fmt = Counter(p.format for p in w_jezyku)
            limit_f = {f: min(k, zapas_fmt[f]) for f, k in licz_fmt.items()}
            for fmt, ile_f in _rozdziel(licz_fmt, ile_j, ziarno, przypadek, jezyk, limity=limit_f).items():
                zapas_fmt[fmt] -= ile_f
                warstwa = sorted((p.id for p in w_jezyku if p.format == fmt), key=lambda i: korpus._klucz(ziarno, "dev", i))
                for k, i in enumerate(warstwa):
                    wynik[i] = "dev" if k < ile_f else "test"
        test = [p for p in pozycje if wynik[p.id] == "test"]
        if {p.jezyk for p in test} != set(jezyki) or {p.format for p in test} != set(formaty) \
                or len(pozycje) - len(test) != ile:
            raise ValueError(f"{przypadek}: split nie zostawia w test każdego języka i formatu przy {ile} dev")
    return wynik


def _rozdziel(liczby: Counter, ile: int, ziarno: int, *klucz: str, limity: dict[str, int] | None = None) -> dict[str, int]:
    """`ile` rozdzielone proporcjonalnie do `liczby` (największe reszty; remisy – skrót ziarna i klucza). Z `limity`: klucz
    dostaje najwyżej swój limit, nadwyżka przechodzi kolejno do kluczy z zapasem o największym niedoborze wobec udziału."""
    klucze = sorted(liczby, key=lambda k: korpus._klucz(ziarno, "split-warstwy", *klucz, k))
    n = sum(liczby.values())
    udzialy = [ile * liczby[k] / n for k in klucze]
    wynik = dict(zip(klucze, korpus._najwiekszych_reszt(udzialy, ile)))
    if limity is None:
        return wynik
    nadwyzka = sum(max(0, wynik[k] - limity[k]) for k in klucze)
    wynik = {k: min(wynik[k], limity[k]) for k in klucze}
    for _ in range(nadwyzka):
        zapas = [i for i, k in enumerate(klucze) if wynik[k] < limity[k]]
        if not zapas:
            raise ValueError(f"{'/'.join(klucz)}: za mało dokumentów na {ile} dev przy zachowaniu każdej warstwy w test")
        i = min(zapas, key=lambda i: (wynik[klucze[i]] - udzialy[i], i))
        wynik[klucze[i]] += 1
    return wynik


# ----------------------------------------------------------------------------- tabela do metodyki
def _licznik(wartosci: Counter, kolejnosc: tuple[str, ...] | list[str]) -> str:
    return ", ".join(f"{k} {wartosci[k]}" for k in kolejnosc if wartosci[k])


def tabela_rozkladu(ziarno: int = ZIARNO_TRUDNE, rozklad: dict[str, Rozklad] = ROZKLAD) -> str:
    """Tabela Markdown rozkładu (plan i split liczone z kodu) – wstawiana do `metodyka/przypadki.md`."""
    plan = zaplanuj_warstwe(ziarno, rozklad)
    split = przydziel_split_warstwy(plan, ziarno)
    kolejnosc_fmt = [f for f, _ in (*korpus.UDZIALY_FORMATOW, *trudne.UDZIALY_DODATKOWE)]
    wiersze = ["| Przypadek | Skrót | T3 | P3 | Dok. | Dev | Języki | Formaty | Uzasadnienie |",
               "|---|---|---|---|---|---|---|---|---|"]
    tekstowe, plikowe = set(P.przypadki_punktowane("tekst")), set(P.przypadki_punktowane("plik"))
    for przypadek, r in rozklad.items():
        pozycje = [p for p in plan if p.przypadek == przypadek]
        dev = sum(1 for p in pozycje if split[p.id] == "dev")
        wiersze.append(
            f"| `{przypadek}` | `{P.SKROTY[przypadek]}` | {'✓' if przypadek in tekstowe else '–'} "
            f"| {'✓' if przypadek in plikowe else '–'} | {len(pozycje)} | {dev} "
            f"| {_licznik(Counter(p.jezyk for p in pozycje), KOLEJNOSC_JEZYKOW)} "
            f"| {_licznik(Counter(p.format for p in pozycje), kolejnosc_fmt)} | {r.uzasadnienie} |")
    dev = sum(1 for s in split.values() if s == "dev")
    wiersze.append(f"| **razem** | | {len(tekstowe & set(rozklad))} | {len(plikowe & set(rozklad))} | **{len(plan)}** | {dev} "
                   f"| {_licznik(Counter(p.jezyk for p in plan), KOLEJNOSC_JEZYKOW)} "
                   f"| {_licznik(Counter(p.format for p in plan), kolejnosc_fmt)} | |")
    return "\n".join(wiersze) + "\n"


# ----------------------------------------------------------------------------- budowa i sumy kontrolne
def zbuduj_warstwe(cel: Path, ziarno: int = ZIARNO_TRUDNE, procesy: int = 1, przypadki: tuple[str, ...] | None = None,
                   postep: bool = False) -> list[dict[str, Any]]:
    """Buduje warstwę (albo wybrane `przypadki` – identyfikatory i split jak w pełnej warstwie) w `cel`: pliki, teksty,
    `manifest.jsonl` posortowany po `id` i `statystyki.json` (deterministyczne – bez czasu budowy; jak w trzonie objęte
    sumami); zwraca wpisy. Split liczony jest zawsze na planie PEŁNEJ warstwy."""
    cel = Path(cel)
    cel.mkdir(parents=True, exist_ok=True)
    pelny = zaplanuj_warstwe(ziarno)
    split = przydziel_split_warstwy(pelny, ziarno)
    plan = [p for p in pelny if przypadki is None or p.przypadek in przypadki]
    # najdłuższe (LibreOffice, długie dokumenty) najpierw: krótszy czas całej puli; wynik nie zależy od kolejności
    zadania = [(p, ziarno, split[p.id], str(cel)) for p in sorted(plan, key=_koszt, reverse=True)]
    start = time.monotonic()
    wyniki: list[dict[str, Any]] = []
    if procesy <= 1:
        iterator: Any = map(trudne._zadanie, zadania)
        pula = None
    else:
        pula = ProcessPoolExecutor(max_workers=procesy)
        iterator = pula.map(trudne._zadanie, zadania, chunksize=1)
    try:
        for i, w in enumerate(iterator, 1):
            wyniki.append(w)
            if postep and i % 25 == 0:
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
    (cel / PLIK_STATYSTYK).write_text(json.dumps(statystyki(dobre, ziarno), ensure_ascii=False, indent=2) + "\n",
                                      encoding="utf-8", newline="\n")
    return dobre


def _koszt(p: PozycjaTrudna) -> tuple[int, str]:
    wolne = p.format in ("doc", "rtf", "odt", "skan") or p.przypadek in (P.DLUGIE_LISTY_OSOB, P.SKROTY_PO_PELNYM,
                                                                          P.GRANICA_OKNA)
    return int(wolne), p.id


def sumy_kontrolne(cel: Path, wpisy: list[dict[str, Any]] | None = None) -> str:
    """Treść `SHA256SUMS-trudne` (format `sha256sum`, docstring modułu) dla warstwy w `cel`: plik i `.txt` każdego wpisu
    manifestu, `manifest.jsonl` i `statystyki.json` – te same rodzaje plików co opublikowany `SHA256SUMS-trzon`."""
    cel = Path(cel)
    if wpisy is None:
        wpisy = [json.loads(w) for w in (cel / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    sciezki = sorted({"manifest.jsonl", PLIK_STATYSTYK, *(w["plik"] for w in wpisy), *(w["plik_txt"] for w in wpisy)})
    return "".join(f"{hashlib.sha256((cel / s).read_bytes()).hexdigest()}  {s}\n" for s in sciezki)


def wczytaj_sumy(tekst: str) -> dict[str, str]:
    """Ścieżka -> sha256 z treści pliku w formacie `sha256sum`."""
    wynik = {}
    for linia in tekst.splitlines():
        skrot, sciezka = linia.split("  ", 1)
        wynik[sciezka] = skrot
    return wynik


def linia_bazowa(cel: Path, plik_sum: Path = PLIK_SUM) -> dict[str, Any]:
    """Linia bazowa testów (`tests/dane_testowe/trudne_baseline.json`) z warstwy zbudowanej w `cel` i opublikowanego pliku
    sum: skrót pliku sum, liczba dokumentów, liczby per przypadek × split i skrót każdej linii manifestu (po `id`)."""
    linie = (Path(cel) / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    wpisy = [json.loads(w) for w in linie]
    return {"opis": "Warstwa trudnych przypadków (H6b): skrót metodyka/SHA256SUMS-trudne, liczby dokumentów i skróty linii "
                    "manifestu (sha256 linii bez znaku nowego wiersza). Odtworzenie: trudne_warstwa.linia_bazowa.",
            "sumy_sha256": hashlib.sha256(Path(plik_sum).read_bytes()).hexdigest(),
            "dokumentow": len(wpisy),
            "po_przypadku_splicie": statystyki(wpisy)["po_przypadku_splicie"],
            "linie_manifestu": {w["id"]: hashlib.sha256(l.encode()).hexdigest() for w, l in zip(wpisy, linie)}}


def statystyki(wpisy: list[dict[str, Any]], ziarno: int = ZIARNO_TRUDNE) -> dict[str, Any]:
    """Liczby dokumentów: łącznie, per przypadek główny (z planu) × split oraz per oznaczenie `przypadki` (dokument może
    nieść przypadek dodatkowy – `trudne.przypadki_dokumentu`)."""
    glowny = {p.id: p.przypadek for p in zaplanuj_warstwe(ziarno)}
    return {"dokumentow": len(wpisy),
            "po_splicie": dict(sorted(Counter(w["split"] for w in wpisy).items())),
            "po_przypadku_splicie": {f"{k[0]}/{k[1]}": n for k, n in sorted(
                Counter((glowny.get(w["id"], "?"), w["split"]) for w in wpisy).items())},
            "po_oznaczeniu": dict(sorted(Counter(x for w in wpisy for x in w["przypadki"]).items())),
            "ostrzezenia": sum(len(w["ostrzezenia"]) for w in wpisy)}


def main_pelna(cel: Path, ziarno: int, procesy: int | None, sumy: Path | None) -> int:
    """`pbench-trudne --pelna`: buduje warstwę (z `statystyki.json`) i – z `--sumy` – zapisuje plik sum."""
    n = procesy or max(1, (os.cpu_count() or 2) - 2)
    start = time.monotonic()
    wpisy = zbuduj_warstwe(cel, ziarno, n, postep=True)
    czas = time.monotonic() - start
    st = statystyki(wpisy, ziarno)
    if sumy is not None:
        Path(sumy).write_text(sumy_kontrolne(cel, wpisy), encoding="utf-8", newline="\n")
    print(json.dumps(st["po_splicie"]), "dokumentów:", st["dokumentow"], "ostrzeżeń:", st["ostrzezenia"],
          f"czas: {czas:.0f} s (procesy: {n})")
    return 0
