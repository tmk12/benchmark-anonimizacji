"""Agregacja ocen do dwóch rankingów (T1–T6 „tekst”, P1–P7 „pliki”) i tabel raportu.

    uv run pbench-agreguj [--split test] [--wyniki wyniki] [--korpus korpus] [--wyniki-trudne wyniki/trudne]
                          [--korpus-trudne korpus-trudne] [--czasy wyniki/czas/czasy.jsonl] [--cel wyniki/zbiorcze]
                          [--dopusc-bez-odcisku]

Wzory: `metodyka/punktacja.md` (wagi `metodyka/wagi_punktow.json`, zamrożone) i definicje operacyjne
`metodyka/prerejestracja.md` (pkt 1.1, 1.2, 3) – moduł liczy dokładnie je, niczego w nich nie zmienia.

**Wejście.** Rekordy ocen `<wyniki>/oceny/<uczestnik>/<split>/<poziom>.jsonl` (`pbench-ocen`, schemat w docstringu
`pbench/ocen.py`) – warstwa `trzon` z `--wyniki` i manifestu `--korpus`, warstwa `trudne` (T3/P3, identyfikacja pośrednia,
poziom encji) z `--wyniki-trudne` i `--korpus-trudne`. Uczestnik z poziomem `tekst` jest w rankingu „tekst”, z poziomem `plik`
– w rankingu „pliki”. `aneks = true` w `uczestnicy/<id>/uczestnik.toml` (warianty ablacyjne i krzyżowe): wiersz liczony tymi
samymi wzorami, pokazany osobno (`aneks`), bez miejsca, poza remisami i analizą wrażliwości. Katalogi zaczynające się od `_`
(atrapa) są pomijane. Dokumenty splitu bez rekordu oceny (`brak_oceny`) liczą się jak brak wyniku – także cała warstwa
trudna uczestnika bez jej pliku ocen (T3/P3 = 0, nie „nieliczony”).

**Punktacja.** Każdy dokument ma wagę wycieku s(d) = max w(kat) po wartościach gold, które w nim wyciekły (pełnie lub częściowo),
podzieloną przez 3; dokument bez wycieku s = 0, dokument fail-closed (każdy stan ≠ `ok`) s = 1; T1/P1 = 1 − Σ s(d) / N, T4 = min
po językach tej samej miary, T3/P3 = średnia po przypadkach punktowanych z (1 − Σ_{d∈przypadek} s(d) / liczba dokumentów przypadku)
(przypadki i stratyfikacja bootstrapu: zob. niżej). Wektor `Wektory.wyciek_w` (s(d)) leży obok `Wektory.wyciek` (0/1, liczba
dokumentów z wyciekiem w tabelach opisowych).

**Odcisk sędziego** (`pbench.srodowisko.odcisk_sedziego`, pole `odcisk_sedziego` rekordu): wszystkie rekordy uczestników
jednego poziomu (obie warstwy, także aneks) muszą mieć ten sam odcisk (bez informacyjnego `commit`) – inaczej `NiezgodnyOdcisk`
(CLI: kod 2, nic nie zapisuje). Rekordy bez odcisku (oceny sprzed jego wprowadzenia) – też `NiezgodnyOdcisk`, chyba że
`--dopusc-bez-odcisku` (wyłącznie split dev – pilot; ostrzeżenie). Wspólny odcisk trafia do `odcisk.csv`.

**Bramka publikacji** (prerejestracja pkt 3.1): uczestnik rankingu (bez aneksu) z testem nieliczonym, z dokumentami
`brak_oceny` albo `blad_sedziego` (w dowolnej warstwie) oraz uczestnik deklarujący poziom w `uczestnik.toml` bez pliku ocen trafia
do `niekompletne.csv` (`kompletny = false` w `glowne.csv`); CLI wypisuje wtedy nagłówek NIEKOMPLETNE i kończy się kodem 3
(tabele są zapisane – do analizy, nie do publikacji).

**Stan dokumentu** (`stan_dokumentu`, osobne kolumny raportu): `ok`, `blad` (błąd uczestnika, pad, offset poza tekstem, brak
pliku wynikowego), `timeout`, `nieczytelny`/`pusty` (plik wynikowy), `odmowa`, `nieobslugiwany`, `blad_sedziego`, `brak_oceny`.
Każdy stan poza `ok` jest w T1/T2/T3/T4/P1/P2/P3 dokumentem z wyciekiem (w T1/T3/T4/P1/P3: s = 1), a w T2/P2 jego licznik = mianownik (fail-closed,
prerejestracja pkt 3.1); T5/P5 liczą tylko dokumenty `ok`; P4 – nieobsługiwany poza średnią, inny stan poza `ok` = 0; P6 –
przetworzony = bez `brak_wyniku` i bez `nieobslugiwany`.

**Odmowa.** Komunikat produktu, którym uczestnik celowo odmawia przetworzenia dokumentu (np. Privatizer: EML z załącznikami),
rozpoznawany w polu `blad` rekordu z listy `uczestnicy/<id>/odmowy.json` – `{"komunikaty": ["…"]}`, dopasowanie podciągiem
(opis listy w `KONFIG.md` uczestnika; ta sama zasada dla każdego narzędzia).

**P2** (pkt 3.3): zbiór ocenianych wartości dokumentu = pole rekordu `bazowe` (linia bazowa sędziego plikowego) ∪ identyfikatory
`wycieki`; waga = w(kat) · maks. w(miejsce) wpisów gold wartości (`gold_plik`, `gold_obrazy`). Rekord bez `bazowe` (ocena sprzed
T17a): dokument fail-closed – linią bazową są jego wycieki (ocena kopii oryginału), dokument `ok` – P2 uczestnika nieliczone
(uwaga w raporcie: ponowić `pbench-ocen`). „Wyciek ważony kategorią (plik)” (`P2_kat`) – ten sam zbiór, waga w(kat), opisowo.

**T6/P7** (pkt 1.2) – plik pomiaru czasu `--czasy` (JSONL, po linii na uczestnika × poziom × dokument próby):
`{"uczestnik", "poziom": "tekst"|"plik", "id", "znaki", "pomiary_s": [t1, t2, t3], "status"}`, `status` ∈ `ok`, `blad`,
`timeout`, `odmowa`, `pominiety`; `znaki` – długość `.txt` dokumentu (brak – liczona z korpusu). Czas dokumentu = mediana
pomiarów (`ok`), inaczej +∞; `pominiety` – poza próbą (P6); strony = max(1, znaki / 1800); *t* = mediana s/stronę po próbie;
wynik = min(1, `T_REF` / *t*). Brak pliku albo wierszy uczestnika – test nieliczony (uwaga), suma bez niego. Rozgrzewkę
i warunki pomiaru zapewnia `pbench-czas`, nie agregacja.

**Niepewność** (pkt 3.5): bootstrap po dokumentach `macierz_losowan` – `POWTORZENIA` losowań ze zwracaniem,
`numpy.random.default_rng(ZIARNO)`, najpierw trzon, potem warstwa trudna warstwowana po pełnym zestawie przypadków dokumentu
(`warstwy_przypadkow` – każdy przypadek ma w każdym losowaniu tyle dokumentów co w próbie); te same losowania dla wszystkich uczestników (sparowane). Suma rankingu w każdym losowaniu z tych samych indeksów,
T6/P7 stałe. Przedział 95% – percentyle 2,5 i 97,5; nakładające się przedziały sum dwóch uczestników = remis statystyczny
(`remis_z`). Analiza wrażliwości: zestawy `rowne`, `prywatnosc`, `uzytecznosc` z `wagi_punktow.json`.

**Wyjście** (`--cel`): `glowne.csv` (uczestnik × ranking: wyniki testów ∈ [0,1], punkty, przedziały, suma, miejsce, remisy, stany
dokumentów), `per_jezyk.csv`, `per_format.csv`, `per_typ.csv` (trzon), `per_kategoria.csv`, `per_miejsce.csv` (miejsce gold
wartości), `per_przypadek.csv` (warstwa trudna), `w_zakresie.csv` (zakres deklarowany i oficjalny), `pomocnicze.csv`
(identyfikacja pośrednia z `pbench.posrednie.agreguj`, poziom encji, ścisłe F1 spanów, char-F2, rodzaje wycieków), `czas.csv`
(T6/P7 i wrażliwość na `t_ref`), `wrazliwosc.csv`, `odcisk.csv`, `niekompletne.csv`, `przyklady.jsonl` (po
`PRZYKLADOW_NA_UCZESTNIKA` par przed/po na uczestnika rankingu tekst – pierwsze dokumenty z wyciekiem w kolejności manifestu;
dokumenty syntetyczne).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
import tomllib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from . import posrednie as _posrednie
from . import srodowisko as _srodowisko
from .przypadki import przypadki_punktowane
from .sedzia.tekst import _maska, _niebiale
from .uruchom import KORZEN, wczytaj_manifest

WAGI = KORZEN / "metodyka" / "wagi_punktow.json"
#: Najwyższa waga kategorii – mianownik wagi dokumentu z wyciekiem s(d).
WAGA_MAKS = 3
ZIARNO = _posrednie.ZIARNO_BOOTSTRAP
POWTORZENIA = 1000
UFNOSC = 0.95
#: s na stronę obliczeniową (prerejestracja pkt 1.2) i wartości analizy wrażliwości (opisowo, bez punktów).
T_REF = 1.0
T_REF_WRAZLIWOSC = (0.5, 2.0)
ZNAKI_STRONY = 1800
#: Języki T4 (pięć języków Privatizera; `uk` poza T4).
JEZYKI_T4 = ("pl", "en", "es", "de", "fr")
#: Ranking -> (poziom ocen, testy w kolejności `wagi_punktow.json`).
RANKINGI = {"tekst": ("tekst", ("T1", "T2", "T3", "T4", "T5", "T6")),
            "pliki": ("plik", ("P1", "P2", "P3", "P4", "P5", "P6", "P7"))}
STANY = ("blad", "timeout", "nieczytelny", "pusty", "odmowa", "nieobslugiwany", "blad_sedziego", "brak_oceny")
#: Kolumny stanów w raporcie (stan -> kolumna).
KOLUMNY_STANOW = {"blad": "bledy", "timeout": "timeouty", "nieczytelny": "nieczytelne", "pusty": "puste", "odmowa": "odmowy",
                  "nieobslugiwany": "nieobslugiwane", "blad_sedziego": "bledy_sedziego", "brak_oceny": "brak_oceny"}
#: Pary przed/po na uczestnika rankingu (równo dla każdego, bez limitu globalnego – recenzja T17a, W1).
PRZYKLADOW_NA_UCZESTNIKA = 2


class NiezgodnyOdcisk(ValueError):
    """Rekordy ocen z różnych sędziów/środowisk albo bez odcisku sędziego (docstring modułu)."""


# ----------------------------------------------------------------------------- wagi i deklaracje
def wczytaj_wagi(sciezka: Path = WAGI) -> dict[str, Any]:
    return json.loads(Path(sciezka).read_text(encoding="utf-8"))


def waga_kategorii(wagi: dict[str, Any], kategoria: str) -> int:
    """w(kat) z `wagi_kategorii`; kategoria spoza list – 1 (prerejestracja pkt 3.2)."""
    for w, kategorie in wagi["wagi_kategorii"].items():
        if kategoria in kategorie:
            return int(w)
    return 1


def waga_miejsca(wagi: dict[str, Any], miejsce: str) -> float:
    return float(wagi["wagi_miejsc"].get(miejsce, 1.0))


def wagi_testow(wagi: dict[str, Any], ranking: str, zestaw: str | None = None) -> dict[str, float]:
    """Punkty testów rankingu: domyślne (`ranking_<ranking>`) albo zestaw analizy wrażliwości (test spoza zestawu – 0)."""
    testy = RANKINGI[ranking][1]
    if zestaw is None:
        return {k.split("_", 1)[0]: float(v) for k, v in wagi[f"ranking_{ranking}"].items()}
    z = wagi["analiza_wrazliwosci"][zestaw][f"ranking_{ranking}"]
    if isinstance(z, str):                                # „każdy test 1000/n”
        return {t: 1000 / len(testy) for t in testy}
    return {t: float(z.get(t, 0)) for t in testy}


def czy_aneks(katalog_uczestnika: Path) -> bool:
    try:
        return bool(tomllib.loads((katalog_uczestnika / "uczestnik.toml").read_text(encoding="utf-8")).get("aneks", False))
    except (OSError, tomllib.TOMLDecodeError):
        return False


def poziomy_deklarowane(katalog_uczestnika: Path) -> list[str]:
    """`poziomy` z `uczestnik.toml` (brak albo zły plik – pusta lista)."""
    try:
        p = tomllib.loads((katalog_uczestnika / "uczestnik.toml").read_text(encoding="utf-8")).get("poziomy", [])
    except (OSError, tomllib.TOMLDecodeError):
        return []
    return [x for x in p if isinstance(x, str)] if isinstance(p, list) else []


def komunikaty_odmowy(katalog_uczestnika: Path) -> list[str]:
    """Komunikaty odmowy produktu z `odmowy.json` uczestnika (`{"komunikaty": [...]}`); brak pliku – pusta lista."""
    try:
        d = json.loads((katalog_uczestnika / "odmowy.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [k for k in d.get("komunikaty", []) if isinstance(k, str) and k]


def stan_dokumentu(rek: dict[str, Any] | None, odmowy: Iterable[str] = ()) -> str:
    """Stan dokumentu w raporcie (docstring modułu); każdy poza `ok` jest fail-closed."""
    if rek is None:
        return "brak_oceny"
    if rek.get("blad_sedziego"):
        return "blad_sedziego"
    if rek.get("nieobslugiwany"):
        return "nieobslugiwany"
    if rek.get("brak_wyniku"):
        blad = str(rek.get("blad") or "")
        if any(k in blad for k in odmowy):
            return "odmowa"
        if "timeout" in blad.lower():
            return "timeout"
        if rek.get("status_pliku") == "NIECZYTELNY":
            return "nieczytelny"
        if rek.get("status_pliku") == "PUSTY":
            return "pusty"
        return "blad"
    return "ok"


# ----------------------------------------------------------------------------- wczytywanie
def _jsonl(p: Path) -> dict[str, dict[str, Any]]:
    """Rekordy po `id` (ostatni wygrywa); ucięte wiersze pomijane."""
    wynik: dict[str, dict[str, Any]] = {}
    if p.exists():
        for linia in p.read_text(encoding="utf-8").splitlines():
            try:
                obj = json.loads(linia)
            except ValueError:
                continue
            if isinstance(obj, dict) and "id" in obj:
                wynik[obj["id"]] = obj
    return wynik


def _uczestnicy_poziomu(wyniki: Path, split: str, poziom: str) -> list[str]:
    katalog = Path(wyniki) / "oceny"
    if not katalog.is_dir():
        return []
    return sorted(p.name for p in katalog.iterdir()
                  if not p.name.startswith("_") and (p / split / f"{poziom}.jsonl").exists())


def _poza_gold(tekst: str, gold_tekst: list[dict]) -> int:
    """Znaki niebiałe tekstu poza wszystkimi spanami gold (mianownik T5) – maski sędziego tekstowego."""
    n = len(tekst)
    return int((_niebiale(tekst) & ~_maska(n, [(g["start"], min(g["end"], n)) for g in gold_tekst])).sum())


def _rozszerzenie(wpis: dict) -> str:
    return Path(wpis["plik"]).suffix.lstrip(".").lower()


# ----------------------------------------------------------------------------- wektory dokumentów uczestnika
class Wektory:
    """Miary dokumentów jednego uczestnika na jednym poziomie (kolejność dokumentów = manifest); wszystkie wzory liczą się
    z nich macierzowo (`W @ x`), więc ocena punktowa i każde losowanie bootstrapu to ten sam kod."""

    def __init__(self, n: int) -> None:
        self.stany: list[str] = []
        self.wyciek = np.zeros(n)                                # 0/1: dokument z wyciekiem (liczniki opisowe)
        self.wyciek_w = np.zeros(n)                              # s(d) ∈ [0,1]: waga wycieku dokumentu (T1/T3/T4/P1/P3)
        self.w2_l, self.w2_m = np.zeros(n), np.zeros(n)          # T2 (tekst) / P2 (plik)
        self.k2_l, self.k2_m = np.zeros(n), np.zeros(n)          # P2_kat (plik, opisowo)
        self.fp, self.poza = np.zeros(n), np.zeros(n)            # T5 / P5 (tylko dokumenty `ok`)
        self.integr, self.m_integr = np.zeros(n), np.zeros(n)    # P4
        self.przetw = np.zeros(n)                                # P6
        self.ok = np.zeros(n)
        self.brak_bazowych = 0                                   # dokumenty `ok` bez pola `bazowe` (P2 nieliczone)
        self.brak_nadmiarowych = 0                               # dokumenty `ok` bez pola `nadmiarowe` (P5 nieliczone)
        self.wartosci: list[list[tuple[str, str, bool]]] = []    # (kategoria, miejsce, wyciekła) po wartościach dokumentu
        self.format_zmieniony = 0


def _wartosci_gold_pliku(wpis: dict, wagi: dict) -> dict[str, tuple[str, str]]:
    """Identyfikator -> (kategoria, miejsce o największej wadze) z `gold_plik` i `gold_obrazy` (prerejestracja pkt 3.3)."""
    wynik: dict[str, tuple[str, str]] = {}
    for g in [*wpis.get("gold_plik", ()), *(w for o in wpis.get("gold_obrazy", ()) for w in o["wartosci"])]:
        kat, miejsce = wynik.get(g["id"], (g["kategoria"], g["miejsce"]))
        if waga_miejsca(wagi, g["miejsce"]) > waga_miejsca(wagi, miejsce):
            miejsce = g["miejsce"]
        wynik[g["id"]] = (kat, miejsce)
    return wynik


def wektory(wpisy: list[dict], rekordy: dict[str, dict], poziom: str, wagi: dict, odmowy: Iterable[str] = (),
            poza_gold: list[int] | None = None) -> Wektory:
    """Wektory miar dokumentów (docstring modułu: stany, fail-closed, P2, P4, P5, P6)."""
    odmowy = list(odmowy)
    v = Wektory(len(wpisy))
    for i, wpis in enumerate(wpisy):
        rek = rekordy.get(wpis["id"])
        stan = stan_dokumentu(rek, odmowy)
        ok = stan == "ok"
        v.stany.append(stan)
        v.ok[i] = ok
        wyc_ids = {x[0]: x[1] for x in (rek or {}).get("wycieki") or ()}
        v.wyciek[i] = (not ok) or bool(wyc_ids)
        v.wyciek_w[i] = 1.0 if not ok else 0.0                   # fail-closed: s = 1; dla `ok` poniżej z wyciekłych wartości
        v.przetw[i] = rek is not None and not rek.get("brak_wyniku") and not rek.get("nieobslugiwany")
        if poziom == "tekst":
            ids: dict[str, tuple[str, str]] = {}
            for g in wpis["gold_tekst"]:
                ids.setdefault(g["wartosc_id"], (g["kategoria"], g["miejsce"]))
            wyciekle = set(ids) if not ok else set(wyc_ids)
            v.w2_m[i] = sum(waga_kategorii(wagi, k) for k, _ in ids.values())
            v.w2_l[i] = sum(waga_kategorii(wagi, ids[x][0] if x in ids else wyc_ids[x]) for x in wyciekle)
            if ok and wyciekle:
                v.wyciek_w[i] = max(waga_kategorii(wagi, ids[x][0] if x in ids else wyc_ids[x]) for x in wyciekle) / WAGA_MAKS
            v.wartosci.append([(k, m, wid in wyciekle) for wid, (k, m) in ids.items()])
            if ok and "fp_znaki" in rek:
                v.fp[i], v.poza[i] = rek["fp_znaki"], (poza_gold[i] if poza_gold is not None else 0)
            continue
        # poziom plik
        gold = _wartosci_gold_pliku(wpis, wagi)
        if rek is not None and "bazowe" in rek:
            ocenione = set(rek["bazowe"]) | set(wyc_ids)
        elif not ok and rek is not None and wyc_ids:
            ocenione = set(wyc_ids)                       # ocena kopii oryginału: linia bazowa = jej wycieki
        elif not ok:
            ocenione = set(gold)                          # brak rekordu / błąd sędziego: cały gold pliku
        else:
            ocenione = set(wyc_ids)
            v.brak_bazowych += 1
        wyciekle = ocenione if not ok else set(wyc_ids)
        wartosci = []
        for wid in sorted(ocenione):
            kat, miejsce = gold.get(wid, (wyc_ids.get(wid, ""), "tresc"))   # spoza gold (nie powinno być): miejsce treść
            wk, wm = waga_kategorii(wagi, kat), waga_miejsca(wagi, miejsce)
            v.w2_m[i] += wk * wm
            v.k2_m[i] += wk
            if wid in wyciekle:
                if ok:
                    v.wyciek_w[i] = max(v.wyciek_w[i], wk / WAGA_MAKS)
                v.w2_l[i] += wk * wm
                v.k2_l[i] += wk
            wartosci.append((kat, miejsce, wid in wyciekle))
        v.wartosci.append(wartosci)
        if stan != "nieobslugiwany":
            v.m_integr[i] = 1
            v.integr[i] = _integralnosc(rek.get("integralnosc")) if ok else 0.0
        if ok:
            if isinstance(rek.get("nadmiarowe"), dict):
                v.fp[i], v.poza[i] = rek["nadmiarowe"]["znaki"], rek["nadmiarowe"]["poza_gold"]
            else:
                v.brak_nadmiarowych += 1
            if rek.get("format_wyj") and rek["format_wyj"].lower() != _rozszerzenie(wpis):
                v.format_zmieniony += 1
    return v


def _integralnosc(i: dict | None) -> float:
    """P4 dokumentu: średnia dostępnych składników; `zachowanie_struktury` przy formacie zamienionym – nie dotyczy."""
    if not i:
        return 0.0
    skladniki = [1.0 if i.get("otwiera_sie") else 0.0]
    if i.get("format_zgodny", True) and i.get("zachowanie_struktury") is not None:
        skladniki.append(float(i["zachowanie_struktury"]))
    if i.get("spojnosc") is not None:
        skladniki.append(float(i["spojnosc"]))
    return sum(skladniki) / len(skladniki)


# ----------------------------------------------------------------------------- bootstrap
def macierz_losowan(rng: np.random.Generator, n: int, powtorzenia: int, warstwy: list[str] | None = None) -> np.ndarray:
    """Macierz krotności (powtorzenia × n): wiersz = jedno losowanie ze zwracaniem n dokumentów; `warstwy` – losowanie osobno
    w każdej warstwie (kolejność warstw alfabetyczna), tyle dokumentów, ile ma warstwa."""
    W = np.zeros((powtorzenia, n))
    if n == 0:
        return W
    grupy = [np.arange(n)] if warstwy is None else [
        np.array([i for i, w in enumerate(warstwy) if w == s]) for s in sorted(set(warstwy))]
    wiersze = np.arange(powtorzenia)[:, None]
    for g in grupy:
        idx = g[rng.integers(0, len(g), size=(powtorzenia, len(g)))]
        np.add.at(W, (np.broadcast_to(wiersze, idx.shape), idx), 1)
    return W


def warstwy_przypadkow(przypadki: list[list[str]]) -> list[str]:
    """Warstwa bootstrapu dokumentu warstwy trudnej = pełny zestaw jego przypadków (dokument bez przypadków – `-`): każdy
    przypadek ma wtedy w każdym losowaniu tyle dokumentów co w próbie (prerejestracja pkt 3.5)."""
    return ["|".join(sorted(p)) or "-" for p in przypadki]


def _iloraz(W: np.ndarray, licznik: np.ndarray, mianownik: np.ndarray) -> np.ndarray:
    m = W @ mianownik
    return np.divide(W @ licznik, m, out=np.full(W.shape[0], np.nan), where=m > 0)


def _bez_wycieku(W: np.ndarray, wyciek: np.ndarray, maska: np.ndarray | None = None) -> np.ndarray:
    if maska is not None:
        W = W * maska
    return 1 - _iloraz(W, wyciek, np.ones_like(wyciek))


def _min_jezykow(W: np.ndarray, v: Wektory, jezyki: list[str]) -> np.ndarray | None:
    kol = [_bez_wycieku(W, v.wyciek_w, np.array([j == x for j in jezyki], dtype=float)) for x in JEZYKI_T4 if x in jezyki]
    return np.nanmin(np.vstack(kol), axis=0) if kol else None


def _srednia_przypadkow(W: np.ndarray, wyciek: np.ndarray, przypadki: list[list[str]], punktowane: tuple[str, ...]
                        ) -> tuple[np.ndarray | None, int]:
    wyniki = []
    for p in punktowane:
        maska = np.array([p in pp for pp in przypadki], dtype=float)
        if maska.any():
            wyniki.append(_bez_wycieku(W, wyciek, maska))
    if not wyniki:
        return None, 0
    with np.errstate(all="ignore"):
        return np.nanmean(np.vstack(wyniki), axis=0), len(wyniki)


def _t5(W: np.ndarray, v: Wektory, prog: float) -> tuple[np.ndarray, np.ndarray] | None:
    if not (v.poza > 0).any():
        return None
    u = _iloraz(W, v.fp, v.poza)
    return np.maximum(0.0, 1 - u / prog), u


def miary(ranking: str, v: Wektory, vt: Wektory | None, W: np.ndarray, Wt: np.ndarray | None, jezyki: list[str],
          przypadki: list[list[str]], prog: float) -> dict[str, Any]:
    """Wyniki testów rankingu (∈ [0,1]) dla macierzy losowań `W` (trzon) i `Wt` (trudne): test -> tablica (wiersze `W`) albo
    None (nieliczony); plus miary opisowe (`*_u`, `P2_kat`, `*_przypadki`). T6/P7 – osobno (`wynik_czasu`)."""
    pierwszy, drugi, trzeci = RANKINGI[ranking][1][:3]
    m: dict[str, Any] = {pierwszy: _bez_wycieku(W, v.wyciek_w)}
    m[drugi] = 1 - _iloraz(W, v.w2_l, v.w2_m) if v.brak_bazowych == 0 else None
    if vt is not None and Wt is not None:
        m[trzeci], m[f"{trzeci}_przypadki"] = _srednia_przypadkow(
            Wt, vt.wyciek_w, przypadki, przypadki_punktowane("tekst" if ranking == "tekst" else "plik"))
    else:
        m[trzeci], m[f"{trzeci}_przypadki"] = None, 0
    t5 = _t5(W, v, prog) if v.brak_nadmiarowych == 0 else None
    if ranking == "tekst":
        m["T4"] = _min_jezykow(W, v, jezyki)
        m["T5"], m["T5_u"] = t5 if t5 else (None, None)
    else:
        m["P2_kat"] = 1 - _iloraz(W, v.k2_l, v.k2_m) if v.brak_bazowych == 0 else None
        m["P4"] = _iloraz(W, v.integr, v.m_integr) if v.m_integr.any() else None
        m["P5"], m["P5_u"] = t5 if t5 else (None, None)
        m["P6"] = _iloraz(W, v.przetw, np.ones_like(v.przetw))
    return m


# ----------------------------------------------------------------------------- czas (T6, P7)
def wynik_czasu(s_na_strone: list[float], t_ref: float = T_REF) -> tuple[float, float]:
    """(*t* = mediana s/stronę po próbie, wynik min(1, t_ref / t)); próba z co najmniej połową awarii (+∞) – mediana
    (przy połowie: średnia dwóch środkowych) = ∞, wynik 0."""
    t = statistics.median(s_na_strone)
    if math.isinf(t) or math.isnan(t):
        return math.inf, 0.0
    return t, 1.0 if t <= 0 else min(1.0, t_ref / t)


def wczytaj_czasy(sciezka: Path | None, znaki: dict[str, int]) -> dict[tuple[str, str], list[float]]:
    """(uczestnik, poziom) -> s/stronę dokumentów próby (bez `pominiety`; awaria = +∞)."""
    wynik: dict[tuple[str, str], list[float]] = defaultdict(list)
    if sciezka is None or not Path(sciezka).exists():
        return wynik
    for linia in Path(sciezka).read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(linia)
        except ValueError:
            continue
        if not isinstance(d, dict) or d.get("status") == "pominiety":
            continue
        pomiary = [float(x) for x in d.get("pomiary_s") or ()]
        t_dok = statistics.median(pomiary) if d.get("status") == "ok" and pomiary else math.inf
        strony = max(1.0, float(d.get("znaki", znaki.get(d["id"], 0))) / ZNAKI_STRONY)
        wynik[(d["uczestnik"], d["poziom"])].append(t_dok / strony)
    return wynik


# ----------------------------------------------------------------------------- agregacja
def _przedzial(proby: np.ndarray | None) -> tuple[float | None, float | None]:
    if proby is None or not np.isfinite(proby).any():
        return None, None
    alfa = (1 - UFNOSC) / 2 * 100
    lo, hi = np.nanpercentile(proby, [alfa, 100 - alfa])
    return float(lo), float(hi)


def _wartosc(x: np.ndarray | None) -> float | None:
    if x is None or not np.isfinite(x[0]):
        return None
    return float(x[0])


def _tabela_grup(wiersze: list[dict], ranking: str, uczestnik: str, v: Wektory, wpisy: list[dict], pole: str, prog: float
                 ) -> None:
    grupy: dict[str, list[int]] = defaultdict(list)
    for i, w in enumerate(wpisy):
        grupy[w[pole]].append(i)
    jeden = np.ones((1, len(wpisy)))
    for wartosc, idx in sorted(grupy.items()):
        maska = np.zeros(len(wpisy))
        maska[idx] = 1
        W = jeden * maska
        stany = Counter(v.stany[i] for i in idx)
        r = {"ranking": ranking, "uczestnik": uczestnik, pole: wartosc, "dokumenty": len(idx),
             "z_wyciekiem": int(v.wyciek[idx].sum()), "bez_wycieku": float(_bez_wycieku(W, v.wyciek)[0]),
             "bez_wycieku_wazone": float(_bez_wycieku(W, v.wyciek_w)[0]),
             "wyciek_wazony": _wartosc(_iloraz(W, v.w2_l, v.w2_m))}
        if (W @ v.poza)[0] > 0:
            u = float(_iloraz(W, v.fp, v.poza)[0])
            r.update(nadmiarowe_u=u, nadmiarowe_wynik=max(0.0, 1 - u / prog))
        if ranking == "pliki":
            r["integralnosc"] = _wartosc(_iloraz(W, v.integr, v.m_integr))
        r.update({KOLUMNY_STANOW[s]: stany.get(s, 0) for s in STANY})
        wiersze.append(r)


def _f1_spanow(wpisy: list[dict], surowe: dict[str, dict], v: Wektory) -> dict[str, float] | None:
    """Ścisłe F1 spanów (miara pomocnicza): trafienie = wykrycie o dokładnie tych samych granicach co span gold, bez względu
    na etykietę; spany unikalne w dokumencie; dokument bez wyniku – bez wykryć; mikro po dokumentach."""
    if not surowe:
        return None
    tp = fp = fn = 0
    for i, w in enumerate(wpisy):
        gold = {(g["start"], g["end"]) for g in w["gold_tekst"]}
        rek = surowe.get(w["id"]) if v.stany[i] == "ok" else None
        wyk = {(x[0], x[1]) for x in (rek or {}).get("wykrycia") or ()}
        t = len(gold & wyk)
        tp, fp, fn = tp + t, fp + len(wyk) - t, fn + len(gold) - t
    p = tp / (tp + fp) if tp + fp else 1.0
    r = tp / (tp + fn) if tp + fn else 1.0
    return {"f1_spanow_precyzja": p, "f1_spanow_pokrycie": r, "f1_spanow": 2 * p * r / (p + r) if p + r else 0.0}


def _przyklady(wpisy: list[dict], teksty: dict[str, str], surowe: dict[str, dict], rekordy: dict[str, dict],
               uczestnik: str, ile: int) -> list[dict]:
    """Pary przed/po (poziom tekst): fragment wokół pierwszej wyciekłej wartości dokumentu, wykrycia zastąpione etykietą."""
    wynik = []
    for w in wpisy:
        rek, sur = rekordy.get(w["id"]), surowe.get(w["id"])
        if len(wynik) >= ile or rek is None or stan_dokumentu(rek) != "ok" or not rek.get("wycieki") or not sur:
            continue
        wid = rek["wycieki"][0][0]
        span = next((g for g in w["gold_tekst"] if g["wartosc_id"] == wid), None)
        if span is None:
            continue
        tekst = teksty[w["id"]]
        a, b = max(0, span["start"] - 80), min(len(tekst), span["end"] + 80)
        po, k = [], a
        for s, e, etykieta, *_ in sorted(x for x in sur.get("wykrycia") or () if x[1] > a and x[0] < b):
            s, e = max(s, a), min(e, b)
            if s >= k:
                po += [tekst[k:s], f"[{etykieta}]"]
                k = e
        po.append(tekst[k:b])
        wynik.append({"uczestnik": uczestnik, "id": w["id"], "jezyk": w["jezyk"], "przed": tekst[a:b], "po": "".join(po),
                      "wyciek": rek["wycieki"][0]})
    return wynik


def agreguj(*, split: str, wyniki: Path, korpus: Path, uczestnicy: Path = KORZEN / "uczestnicy",
            wyniki_trudne: Path | None = None, korpus_trudne: Path | None = None, czasy: Path | None = None,
            powtorzenia: int = POWTORZENIA, ziarno: int = ZIARNO, wagi_sciezka: Path | None = None,
            dopusc_bez_odcisku: bool = False) -> dict[str, list]:
    """Oba rankingi i tabele raportu (docstring modułu). Zwraca słownik nazwa tabeli -> lista wierszy. `NiezgodnyOdcisk` –
    rekordy z różnych sędziów albo bez odcisku (bez `dopusc_bez_odcisku`, dozwolonego tylko na split dev).
    `wagi_sciezka` – domyślnie `metodyka/wagi_punktow.json`."""
    if dopusc_bez_odcisku and split != "dev":
        raise ValueError("rekordy bez odcisku sędziego dopuszczalne tylko w pilocie (split dev)")
    wagi = wczytaj_wagi(wagi_sciezka or WAGI)
    prog = float(wagi["progi"]["nadmiarowe_maskowanie_zero_pkt_przy_udziale"])
    wpisy = [w for w in wczytaj_manifest(korpus) if w["split"] == split]
    teksty = {w["id"]: (Path(korpus) / w["plik_txt"]).read_bytes().decode("utf-8") for w in wpisy}
    poza_gold = [_poza_gold(teksty[w["id"]], w["gold_tekst"]) for w in wpisy]
    jezyki = [w["jezyk"] for w in wpisy]
    wpisy_t: list[dict] = []
    if wyniki_trudne is not None and korpus_trudne is not None and (Path(korpus_trudne) / "manifest.jsonl").exists():
        wpisy_t = [w for w in wczytaj_manifest(korpus_trudne) if w["split"] == split]
    przypadki = [list(w.get("przypadki") or ()) for w in wpisy_t]

    tabele: dict[str, list] = defaultdict(list)
    rekordy: dict[tuple[str, str], tuple[dict, dict]] = {}
    for ranking, (poziom, _) in RANKINGI.items():
        for u in _uczestnicy_poziomu(wyniki, split, poziom):
            rekordy[(poziom, u)] = (
                _jsonl(Path(wyniki) / "oceny" / u / split / f"{poziom}.jsonl"),
                _jsonl(Path(wyniki_trudne) / "oceny" / u / split / f"{poziom}.jsonl") if wpisy_t else {})
        tabele["odcisk"] += _sprawdz_odciski(
            poziom, {u: r for (p, u), r in rekordy.items() if p == poziom}, dopusc_bez_odcisku)

    rng = np.random.default_rng(ziarno)
    W_boot = macierz_losowan(rng, len(wpisy), powtorzenia)
    Wt_boot = macierz_losowan(rng, len(wpisy_t), powtorzenia, warstwy=warstwy_przypadkow(przypadki))
    jeden, jeden_t = np.ones((1, len(wpisy))), np.ones((1, len(wpisy_t)))
    czasy_wyn = wczytaj_czasy(czasy, {i: len(t) for i, t in teksty.items()})

    punkty: dict[tuple[str, str], dict[str, float | None]] = {}
    for ranking, (poziom, testy) in RANKINGI.items():
        wagi_r = wagi_testow(wagi, ranking)
        for u in _uczestnicy_poziomu(wyniki, split, poziom):
            odmowy = komunikaty_odmowy(Path(uczestnicy) / u)
            rek, rek_t = rekordy[(poziom, u)]
            v = wektory(wpisy, rek, poziom, wagi, odmowy, poza_gold)
            # warstwa trudna bez pliku ocen uczestnika – wszystkie jej dokumenty `brak_oceny` (fail-closed)
            vt = wektory(wpisy_t, rek_t, poziom, wagi, odmowy) if wpisy_t else None
            pkt = miary(ranking, v, vt, jeden, jeden_t if vt else None, jezyki, przypadki, prog)
            boot = miary(ranking, v, vt, W_boot, Wt_boot if vt else None, jezyki, przypadki, prog)
            czas = czasy_wyn.get((u, poziom))
            szybkosc = testy[-1]
            if czas:
                t_s, wynik_t = wynik_czasu(czas)                 # stała: osobna próbka czasu, bez bootstrapu
                pkt[szybkosc], boot[szybkosc] = np.array([wynik_t]), np.full(powtorzenia, wynik_t)
                pkt[f"{szybkosc}_t"] = t_s
            else:
                pkt[szybkosc] = boot[szybkosc] = None
            uwagi = [f"{t} nieliczony ({_powod(t, v)})" for t in testy if pkt.get(t) is None]
            wiersz: dict[str, Any] = {"ranking": ranking, "uczestnik": u, "aneks": czy_aneks(Path(uczestnicy) / u),
                                      "miejsce": None, "remis_z": [], "suma": 0.0}
            suma_b = np.zeros(powtorzenia)
            for t in testy:
                w = _wartosc(pkt.get(t))
                wiersz[t] = w
                wiersz[f"{t}_pkt"] = None if w is None else wagi_r[t] * w
                wiersz[f"{t}_ci_dol"], wiersz[f"{t}_ci_gora"] = _przedzial(boot.get(t))
                if w is not None:
                    wiersz["suma"] += wagi_r[t] * w
                    suma_b += wagi_r[t] * np.nan_to_num(boot[t], nan=w)
            wiersz["suma_ci_dol"], wiersz["suma_ci_gora"] = _przedzial(suma_b)
            for dodatkowe in ("T5_u", "P5_u", "P2_kat"):
                if dodatkowe in pkt:
                    wiersz[dodatkowe] = _wartosc(pkt[dodatkowe])
            wiersz[f"{testy[2]}_przypadki"] = pkt[f"{testy[2]}_przypadki"]
            wiersz[f"{szybkosc}_t"] = pkt.get(f"{szybkosc}_t")
            stany = Counter(v.stany)
            wiersz.update(dokumenty=len(wpisy), z_wyciekiem=int(v.wyciek.sum()),
                          **{KOLUMNY_STANOW[s]: stany.get(s, 0) for s in STANY})
            if ranking == "pliki":
                wiersz["format_zmieniony"] = v.format_zmieniony
            wiersz["uwagi"] = "; ".join(uwagi)
            braki = _braki(testy, pkt, v, vt)
            wiersz["kompletny"] = not braki
            if not wiersz["aneks"]:
                tabele["niekompletne"] += [{"ranking": ranking, "uczestnik": u, "powod": b} for b in braki]
            tabele["glowne"].append(wiersz)
            punkty[(ranking, u)] = {t: wiersz[t] for t in testy}
            _tabele_szczegolowe(tabele, ranking, poziom, u, v, vt, wpisy, wpisy_t, rek_t, przypadki, prog, czas,
                                Path(wyniki) / "surowe" / u / split, teksty, rek, powtorzenia, ziarno,
                                przyklady=not wiersz["aneks"])
        tabele["niekompletne"] += _niezgloszeni(Path(uczestnicy), Path(wyniki), split, ranking, poziom)
    _miejsca_i_remisy(tabele["glowne"])
    tabele["wrazliwosc"] = _wrazliwosc(tabele["glowne"], punkty, wagi)
    return dict(tabele)


def _sprawdz_odciski(poziom: str, rekordy: dict[str, tuple[dict, dict]], dopusc_bez_odcisku: bool) -> list[dict]:
    """Kontrola odcisku sędziego rekordów poziomu (docstring modułu); zwraca wiersz `odcisk.csv` (pusty – brak odcisków)."""
    grupy: dict[tuple, set[str]] = defaultdict(set)
    commity: dict[tuple, set[str]] = defaultdict(set)
    bez: set[str] = set()
    for u, (rek, rek_t) in sorted(rekordy.items()):
        for warstwa, rr in (("trzon", rek), ("trudne", rek_t)):
            for r in rr.values():
                o = r.get("odcisk_sedziego")
                if not isinstance(o, dict):
                    bez.add(f"{u} ({warstwa})")
                    continue
                klucz = _srodowisko.klucz_odcisku(o)
                grupy[klucz].add(u if warstwa == "trzon" else f"{u} ({warstwa})")
                commity[klucz].add(str(o.get("commit")))
    if len(grupy) > 1:
        opis = "\n  ".join(
            f"odcisk {i}: " + ", ".join(f"{k}={str(x)[:12]}" for k, x in klucz) + " – " + ", ".join(sorted(us))
            for i, (klucz, us) in enumerate(sorted(grupy.items(), key=lambda g: sorted(g[1])), 1))
        raise NiezgodnyOdcisk(f"poziom {poziom}: rekordy ocen pochodzą z różnych sędziów albo środowisk oceny – agregacja "
                              f"przerwana:\n  {opis}\nPonów pbench-ocen dla wszystkich uczestników tym samym sędzią "
                              "i w tym samym środowisku.")
    if bez and not dopusc_bez_odcisku:
        raise NiezgodnyOdcisk(f"poziom {poziom}: rekordy bez odcisku sędziego (ocena sprzed jego wprowadzenia): "
                              f"{', '.join(sorted(bez))}. Ponów pbench-ocen; tylko pilot na dev: --dopusc-bez-odcisku.")
    if bez:
        print(f"UWAGA: poziom {poziom}: rekordy bez odcisku sędziego (dopuszczone – pilot dev): {', '.join(sorted(bez))}",
              file=sys.stderr)
    return [{"poziom": poziom, **dict(klucz), "commit": ";".join(sorted(commity[klucz]))} for klucz in grupy]


def _braki(testy: tuple[str, ...], pkt: dict, v: Wektory, vt: Wektory | None) -> list[str]:
    """Powody, dla których wiersz rankingu nie nadaje się do publikacji (bramka, docstring modułu)."""
    braki = [f"{t} nieliczony" for t in testy if pkt.get(t) is None]
    for prefiks, w in (("", v), ("trudne: ", vt)):
        stany = Counter(w.stany) if w is not None else Counter()
        braki += [f"{prefiks}{s} {stany[s]}" for s in ("brak_oceny", "blad_sedziego") if stany.get(s)]
    return braki


def _niezgloszeni(uczestnicy: Path, wyniki: Path, split: str, ranking: str, poziom: str) -> list[dict]:
    """Uczestnicy rankingu (bez aneksu i atrap) deklarujący poziom w `uczestnik.toml`, a bez pliku ocen."""
    if not uczestnicy.is_dir():
        return []
    obecni = set(_uczestnicy_poziomu(wyniki, split, poziom))
    return [{"ranking": ranking, "uczestnik": k.name, "powod": f"brak pliku ocen (zadeklarowany poziom {poziom})"}
            for k in sorted(uczestnicy.iterdir())
            if k.is_dir() and not k.name.startswith("_") and k.name not in obecni and not czy_aneks(k)
            and poziom in poziomy_deklarowane(k)]


def _powod(test: str, v: Wektory) -> str:
    """Dlaczego test nie jest liczony (kolumna `uwagi`)."""
    if test in ("T6", "P7"):
        return "brak pomiaru czasu"
    if test in ("T3", "P3"):
        return "brak warstwy trudnej (--korpus-trudne/--wyniki-trudne)"
    if test == "P2" and v.brak_bazowych:
        return f"{v.brak_bazowych} rekordów bez `bazowe` – ponów pbench-ocen"
    if test == "P5" and v.brak_nadmiarowych:
        return f"{v.brak_nadmiarowych} rekordów bez `nadmiarowe` – ponów pbench-ocen"
    return "brak dokumentów z wynikiem"


def _tabele_szczegolowe(tabele: dict, ranking: str, poziom: str, u: str, v: Wektory, vt: Wektory | None, wpisy: list[dict],
                        wpisy_t: list[dict], rek_t: dict, przypadki: list[list[str]], prog: float,
                        czas: list[float] | None, katalog_surowych: Path, teksty: dict[str, str], rek: dict,
                        powtorzenia: int, ziarno: int, przyklady: bool = True) -> None:
    for pole, nazwa in (("jezyk", "per_jezyk"), ("format", "per_format"), ("typ", "per_typ")):
        _tabela_grup(tabele[nazwa], ranking, u, v, wpisy, pole, prog)
    for pole, nazwa, k in (("kategoria", "per_kategoria", 0), ("miejsce", "per_miejsce", 1)):
        licz: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for wartosci in v.wartosci:
            for x in wartosci:
                licz[x[k]][0] += 1
                licz[x[k]][1] += x[2]
        for klucz, (n, w) in sorted(licz.items()):
            tabele[nazwa].append({"ranking": ranking, "uczestnik": u, pole: klucz, "wartosci": n, "wyciekle": w,
                                  "odsetek_wyciekow": w / n if n else None})
    if vt is not None:
        for p in sorted({p for pp in przypadki for p in pp}):
            idx = [i for i, pp in enumerate(przypadki) if p in pp]
            tabele["per_przypadek"].append({
                "ranking": ranking, "uczestnik": u, "przypadek": p,
                "punktowany": p in przypadki_punktowane("tekst" if ranking == "tekst" else "plik"),
                "dokumenty": len(idx), "z_wyciekiem": int(vt.wyciek[idx].sum()),
                "bez_wycieku": 1 - float(vt.wyciek[idx].mean()),
                "jezyki": ";".join(sorted({wpisy_t[i]["jezyk"] for i in idx}))})
    # w zakresie deklarowanym i oficjalnym (miary pomocnicze, prerejestracja pkt 3.4)
    zakres = {"ranking": ranking, "uczestnik": u}
    zd = [(i, rek[w["id"]].get("w_zakresie_deklarowanym")) for i, w in enumerate(wpisy)
          if v.stany[i] != "nieobslugiwany" and w["id"] in rek]
    if any(z is not None for _, z in zd):
        dok = [(i, z) for i, z in zd if z is not None or v.stany[i] != "ok"]
        zakres.update(zakres_dokumenty=len(dok),
                      zakres_z_wyciekiem=sum(1 for i, z in dok if v.stany[i] != "ok" or (z and z["wycieki"])),
                      zakres_wartosci=sum(z["wartosci_ocenione"] for _, z in dok if z),
                      zakres_wyciekle=sum(len(z["wycieki"]) for _, z in dok if z))
        zakres["zakres_bez_wycieku"] = 1 - zakres["zakres_z_wyciekiem"] / zakres["zakres_dokumenty"] if dok else None
        zakres["zakres_odsetek_wartosci"] = (zakres["zakres_wyciekle"] / zakres["zakres_wartosci"]
                                             if zakres["zakres_wartosci"] else None)
    ofic = np.array([bool(rek.get(w["id"], {}).get("w_zakresie_oficjalnym", True)) for w in wpisy], dtype=float)
    zakres.update(oficjalne_dokumenty=int(ofic.sum()),
                  oficjalne_bez_wycieku=_wartosc(_bez_wycieku(np.ones((1, len(wpisy))), v.wyciek, ofic)))
    tabele["w_zakresie"].append(zakres)
    # miary pomocnicze
    pom: dict[str, Any] = {"ranking": ranking, "uczestnik": u}
    rekordy = [rek[w["id"]] for w in wpisy if w["id"] in rek]
    pom["wycieki_pelne"] = sum(1 for r in rekordy for x in r.get("wycieki") or () if x[3] == "pelny")
    pom["wycieki_czesciowe"] = sum(1 for r in rekordy for x in r.get("wycieki") or () if x[3] == "czesciowy")
    if poziom == "tekst":
        ok = [r for r, w in zip(rekordy, wpisy) if stan_dokumentu(r) == "ok"]
        pom["char_f2"] = statistics.fmean(r["char_f2"] for r in ok) if ok else None
        pom["pokrycie_znakowe"] = statistics.fmean(r["pokrycie_znakowe"] for r in ok) if ok else None
        pom["fp_spany"] = sum(r.get("fp_spany", 0) for r in ok)
        surowe = _jsonl(katalog_surowych / "tekst.jsonl")
        if f1 := _f1_spanow(wpisy, surowe, v):
            pom.update(f1)
        if przyklady:
            tabele["przyklady"] += _przyklady(wpisy, teksty, surowe, rek, u, PRZYKLADOW_NA_UCZESTNIKA)
    if rek_t:
        posr = _posrednie.agreguj(rek_t.values(), powtorzenia=powtorzenia, ziarno=ziarno)["ogolem"]
        pom.update(posrednie_kombinacje=posr["kombinacje"], posrednie_przerwane=posr["przerwane"],
                   posrednie_odsetek=posr["odsetek"],
                   posrednie_ci_dol=posr["przedzial"][0] if posr["przedzial"] else None,
                   posrednie_ci_gora=posr["przedzial"][1] if posr["przedzial"] else None)
        encje = [r for r in rek_t.values() if "encje_ocenione" in r]
        n_encji = sum(r["encje_ocenione"] for r in encje)
        pom.update(encje_ocenione=n_encji, encje_wyciekle=sum(len(r["wycieki_encji"]) for r in encje),
                   encje_odsetek=sum(len(r["wycieki_encji"]) for r in encje) / n_encji if n_encji else None)
    tabele["pomocnicze"].append(pom)
    # czas
    c: dict[str, Any] = {"ranking": ranking, "uczestnik": u, "dokumenty_proby": len(czas or ()),
                         "awarie": sum(1 for x in czas or () if math.isinf(x))}
    if czas:
        t, wyn = wynik_czasu(czas)
        c.update(s_na_strone=t, wynik=wyn, **{f"wynik_t_ref_{r}": wynik_czasu(czas, r)[1] for r in T_REF_WRAZLIWOSC})
    tabele["czas"].append(c)


def _miejsca_i_remisy(glowne: list[dict]) -> None:
    for ranking in RANKINGI:
        wiersze = sorted((r for r in glowne if r["ranking"] == ranking and not r["aneks"]),
                         key=lambda r: (-r["suma"], r["uczestnik"]))
        for k, r in enumerate(wiersze, 1):
            r["miejsce"] = k
            r["remis_z"] = [x["uczestnik"] for x in wiersze if x is not r and None not in (
                r["suma_ci_dol"], x["suma_ci_dol"]) and r["suma_ci_dol"] <= x["suma_ci_gora"]
                and x["suma_ci_dol"] <= r["suma_ci_gora"]]


def _wrazliwosc(glowne: list[dict], punkty: dict, wagi: dict) -> list[dict]:
    wynik = []
    domyslne = {(r["ranking"], r["uczestnik"]): r["miejsce"] for r in glowne}
    for ranking in RANKINGI:
        for zestaw in wagi["analiza_wrazliwosci"]:
            wr = wagi_testow(wagi, ranking, zestaw)
            sumy = sorted(((sum(wr[t] * x for t, x in p.items() if x is not None), u)
                           for (rk, u), p in punkty.items() if rk == ranking and domyslne.get((rk, u)) is not None),
                          key=lambda s: (-s[0], s[1]))
            for k, (s, u) in enumerate(sumy, 1):
                wynik.append({"zestaw": zestaw, "ranking": ranking, "uczestnik": u, "suma": s, "miejsce": k,
                              "miejsce_domyslne": domyslne[(ranking, u)]})
    return wynik


# ----------------------------------------------------------------------------- zapis
def _komorka(x: Any) -> Any:
    if isinstance(x, float):
        return "" if math.isnan(x) else ("inf" if math.isinf(x) else round(x, 6))
    if isinstance(x, list):
        return ";".join(map(str, x))
    return "" if x is None else x


def zapisz(tabele: dict[str, list], cel: Path) -> None:
    cel = Path(cel)
    cel.mkdir(parents=True, exist_ok=True)
    for nazwa in ("glowne", "per_jezyk", "per_format", "per_typ", "per_kategoria", "per_miejsce", "per_przypadek",
                  "w_zakresie", "pomocnicze", "czas", "wrazliwosc", "odcisk", "niekompletne"):
        wiersze = tabele.get(nazwa, [])
        kolumny: list[str] = []
        for w in wiersze:
            kolumny += [k for k in w if k not in kolumny]
        with (cel / f"{nazwa}.csv").open("w", encoding="utf-8", newline="") as f:
            pis = csv.DictWriter(f, fieldnames=kolumny)
            pis.writeheader()
            for w in wiersze:
                pis.writerow({k: _komorka(w.get(k)) for k in kolumny})
    (cel / "przyklady.jsonl").write_text("".join(json.dumps(p, ensure_ascii=False) + "\n"
                                                 for p in tabele.get("przyklady", [])), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pbench-agreguj", description="Agreguje oceny do rankingów tekst/pliki i tabel raportu.")
    ap.add_argument("--split", default="test", choices=("dev", "test"))
    ap.add_argument("--wyniki", type=Path, default=KORZEN / "wyniki", help="katalog z oceny/ (warstwa trzon)")
    ap.add_argument("--korpus", type=Path, default=KORZEN / "korpus")
    ap.add_argument("--wyniki-trudne", type=Path, default=KORZEN / "wyniki" / "trudne",
                    help="katalog z oceny/ warstwy trudnej (T3/P3)")
    ap.add_argument("--korpus-trudne", type=Path, default=KORZEN / "korpus-trudne")
    ap.add_argument("--uczestnicy", type=Path, default=KORZEN / "uczestnicy")
    ap.add_argument("--czasy", type=Path, default=KORZEN / "wyniki" / "czas" / "czasy.jsonl",
                    help="pomiar czasu (JSONL, docstring modułu); brak pliku – T6/P7 nieliczone")
    ap.add_argument("--cel", type=Path, default=KORZEN / "wyniki" / "zbiorcze")
    ap.add_argument("--powtorzenia", type=int, default=POWTORZENIA)
    ap.add_argument("--dopusc-bez-odcisku", action="store_true",
                    help="tylko pilot (split dev): dopuść rekordy ocen bez odcisku sędziego (z ostrzeżeniem)")
    a = ap.parse_args(argv)
    if a.dopusc_bez_odcisku and a.split != "dev":
        ap.error("--dopusc-bez-odcisku tylko dla pilota (--split dev)")
    try:
        tabele = agreguj(split=a.split, wyniki=a.wyniki, korpus=a.korpus, uczestnicy=a.uczestnicy,
                         wyniki_trudne=a.wyniki_trudne, korpus_trudne=a.korpus_trudne, czasy=a.czasy,
                         powtorzenia=a.powtorzenia, dopusc_bez_odcisku=a.dopusc_bez_odcisku)
    except NiezgodnyOdcisk as e:
        print(f"pbench-agreguj: {e}", file=sys.stderr)
        return 2
    zapisz(tabele, a.cel)
    for r in sorted(tabele.get("glowne", []), key=lambda r: (r["ranking"], r["miejsce"] or 999, r["uczestnik"])):
        ci = f"[{r['suma_ci_dol']:.0f}–{r['suma_ci_gora']:.0f}]" if r["suma_ci_dol"] is not None else ""
        print(f"{r['ranking']:6} {r['miejsce'] or 'aneks':>5} {r['uczestnik']:28} {r['suma']:7.1f} {ci}"
              + (f"  ({r['uwagi']})" if r["uwagi"] else ""))
    zalezy = {(x["ranking"], x["zestaw"]) for x in tabele.get("wrazliwosc", []) if x["miejsce"] != x["miejsce_domyslne"]}
    if zalezy:
        print("Kolejność zależy od wag: " + ", ".join(f"{r}/{z}" for r, z in sorted(zalezy)))
    print(f"Zapisano: {a.cel}")
    if braki := tabele.get("niekompletne"):
        print("NIEKOMPLETNE – rankingu nie publikuje się (prerejestracja pkt 3.1):\n  "
              + "\n  ".join(f"{b['ranking']}/{b['uczestnik']}: {b['powod']}" for b in braki))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
