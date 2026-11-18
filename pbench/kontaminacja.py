"""Kontrola kontaminacji: odsetek 8-gramów słownych szablonów i korpusu obecnych w danych treningowych modelu.

Mierzony model to Privatizer v1.3.0b24: model `lgp-1.0-rc`, paczka `1.0.0rc5`. Zbiór referencyjny obejmuje **całą linię
treningową** modelu (mieszanki treningowe i walidacyjne wszystkich składników wag). Opis linii (składniki, przebiegi, kroki,
lista plików) czyta się z pliku linii (`--linia`, domyślnie `metodyka/linia-modelu-rc5.json` – plik nie jest publikowany,
bo opisuje wewnętrzne dane treningowe); ścieżki są względne wobec `--legal-texts` (katalog danych treningowych, argument
wymagany). Skład wag jest porównywany z `soup.json` modelu, a liczba wierszy mieszanki każdego składnika z `config.json` jego
przebiegu (pole `zgodne`). Pliki są tylko czytane.

Metoda: tekst małymi literami, ciągi liter i cyfr (`[^\\W_]+`, bez interpunkcji), 8 kolejnych słów → skrót 64-bit
(słowa: blake2b-8, kolejne słowa łączone mnożeniem modulo 2^64). Zbiór referencyjny = wszystkie unikalne skróty z
pól `input` (bez próbkowania; w plikach dev `row.input`). Mierzymy odsetek **unikalnych** 8-gramów obecnych w zbiorze
referencyjnym:

* (a) bloki szablonów (`Blok.tekst_z_gniazdami`; gniazda `{…}`, nowe linie i separatory komórek ` | ` dzielą tekst na
  odcinki – 8-gram nie przechodzi przez gniazdo, bo wartość jest losowana),
* (b) wygenerowane teksty korpusu (`<id>.txt`), z wartościami.

Frazy formułkowe: 8-gramy występujące w blokach szablonów co najmniej 3 różnych typów dokumentów (`prog_typow`;
liczone po wszystkich językach – 8-gram jest jednojęzyczny). Raport podaje odsetek ogółem i po ich wyłączeniu.
Wynik zawiera wyłącznie liczby, odsetki i ścieżki (żadnych fragmentów tekstu treningowego).

Procedura:

    # pełna linia na maszynie z danymi treningowymi (zapis: metodyka/kontaminacja.json)
    uv run pbench-kontaminacja --korpus korpus/ --legal-texts <katalog-danych-treningowych>

    # brakujący plik referencyjny (np. mieszanka tylko na innej maszynie): na tamtej maszynie samo numpy + stdlib
    python kontaminacja.py --tylko-skroty --wejscie train.jsonl val.jsonl --wyjscie <id-zrodla>.npy
    # tu: dołączenie gotowych skrótów (nazwa pliku bez .npy = id źródła z pliku linii, albo ID=PLIK.npy)
    uv run pbench-kontaminacja --legal-texts <katalog> --skroty-zewnetrzne <id-zrodla>.npy ...

Bez pliku i bez dostarczonych skrótów źródło trafia na listę braków, a `zbior_referencyjny.kompletny` = false.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np

N_GRAM = 8
PROG_TYPOW = 3
CEL_ODSETEK = 0.01
LINIA = Path(__file__).resolve().parent.parent / "metodyka" / "linia-modelu-rc5.json"
MODELE_DIR = Path.home() / ".cache" / "lgp-models"
#: Rozmiar zakresu pliku przetwarzanego przez jeden proces (bajty).
ROZMIAR_KAWALKA = 8 << 20
_SLOWO = re.compile(r"[^\W_]+")
_DZIELNIK_SZABLONU = re.compile(r"\{[^{}]*\}|\n| \| ")
_MNOZNIK = np.uint64(0x9E3779B97F4A7C15)


class _SkrotySlow(dict):
    def __missing__(self, slowo: str) -> np.uint64:
        w = self[slowo] = np.uint64(int.from_bytes(hashlib.blake2b(slowo.encode(), digest_size=8).digest(), "big"))
        return w


_SLOWA = _SkrotySlow()


def osmiogramy(tekst: str) -> np.ndarray:
    """Skróty 64-bit wszystkich (powtarzających się też) 8-gramów słownych tekstu."""
    slowa = np.array([_SLOWA[s] for s in _SLOWO.findall(tekst.lower())], dtype=np.uint64)
    m = len(slowa) - N_GRAM + 1
    if m <= 0:
        return np.empty(0, dtype=np.uint64)
    with np.errstate(over="ignore"):
        h = slowa[:m].copy()
        for i in range(1, N_GRAM):
            h = h * _MNOZNIK + slowa[i:i + m]
    return h


def okna_z_cyfra(tekst: str) -> np.ndarray:
    """Maska równoległa do `osmiogramy(tekst)`: 8-gram zawiera słowo z cyfrą (numer artykułu, rok, sygnatura…)."""
    slowa = _SLOWO.findall(tekst.lower())
    m = len(slowa) - N_GRAM + 1
    if m <= 0:
        return np.empty(0, dtype=bool)
    suma = np.concatenate([[0], np.cumsum([any(c.isdigit() for c in s) for s in slowa])])
    return suma[N_GRAM:] - suma[:m] > 0


def osmiogramy_odcinkow(odcinki: list[str]) -> np.ndarray:
    wyniki = [osmiogramy(o) for o in odcinki]
    return np.concatenate(wyniki) if wyniki else np.empty(0, dtype=np.uint64)


# ----------------------------------------------------------------------------- zbiór referencyjny
def _tekst(wiersz: dict) -> str:
    """Pole `input` wiersza treningowego (mieszanki: `input`; pliki dev: `row.input`)."""
    return wiersz["input"] if "input" in wiersz else wiersz["row"]["input"]


def _zakres(args: tuple[str, int, int]) -> tuple[np.ndarray, int]:
    sciezka, od, do = args
    kawalki: list[np.ndarray] = []
    wierszy = 0
    with open(sciezka, "rb") as f:
        if od:
            f.seek(od - 1)
            f.readline()   # linia przecinająca granicę należy do poprzedniego zakresu
        while f.tell() < do:
            linia = f.readline()
            if not linia:
                break
            kawalki.append(np.unique(osmiogramy(_tekst(json.loads(linia)))))
            wierszy += 1
    return (np.unique(np.concatenate(kawalki)) if kawalki else np.empty(0, dtype=np.uint64)), wierszy


def skroty_plikow(sciezki: list[Path], procesy: int | None = None) -> tuple[np.ndarray, list[int]]:
    """Posortowana tablica unikalnych skrótów 8-gramów z pól `input` plików JSONL i liczba wierszy każdego pliku."""
    zadania: list[tuple[str, int, int]] = []
    numery: list[int] = []
    for n, sciezka in enumerate(sciezki):
        rozmiar = Path(sciezka).stat().st_size
        kawalki = max(1, min(256, rozmiar // ROZMIAR_KAWALKA))
        granice = [rozmiar * i // kawalki for i in range(kawalki + 1)]
        zadania += [(str(sciezka), granice[i], granice[i + 1]) for i in range(kawalki)]
        numery += [n] * kawalki
    wiersze = [0] * len(sciezki)
    czesci: list[np.ndarray] = []
    with ProcessPoolExecutor(max_workers=procesy or max(1, min(8, (os.cpu_count() or 2) - 2))) as pula:
        for n, (h, w) in zip(numery, pula.map(_zakres, zadania)):
            czesci.append(h)
            wiersze[n] += w
    return (np.unique(np.concatenate(czesci)) if czesci else np.empty(0, dtype=np.uint64)), wiersze


def wczytaj_linie(sciezka: Path | None = None) -> dict[str, Any]:
    return json.loads(Path(sciezka or LINIA).read_text(encoding="utf-8"))


def _pliki_zrodla(katalog: Path, wpis: dict[str, Any]) -> list[str]:
    """Ścieżki (względne) istniejących plików źródła; wzorzec z `*` rozwijany w katalogu danych treningowych."""
    rel = wpis["sciezka"]
    if "*" in rel:
        return sorted(str(p.relative_to(katalog)) for p in katalog.glob(rel))
    return [rel] if (katalog / rel).is_file() else []


def _id_npy(spec: str) -> tuple[str, Path]:
    if "=" in spec:
        i, p = spec.split("=", 1)
        return i, Path(p)
    return Path(spec).stem, Path(spec)


def zbior_referencyjny(katalog: Path, linia: dict[str, Any] | None = None, procesy: int | None = None,
                       skroty_zewnetrzne: list[str] | None = None,
                       ) -> tuple[list[tuple[dict[str, Any], np.ndarray]], dict[str, Any]]:
    """Skróty każdego źródła linii modelu: lista (opis, tablica unikalnych skrótów) i opis zbioru
    (`kompletny`, `braki`). Źródło bez pliku bierze skróty z `skroty_zewnetrzne` (id źródła = nazwa pliku .npy)."""
    katalog = Path(katalog)
    linia = linia or wczytaj_linie()
    zewn = dict(_id_npy(s) for s in (skroty_zewnetrzne or []))
    zrodla: list[tuple[dict[str, Any], np.ndarray]] = []
    braki: list[str] = []
    for wpis in linia["pliki_referencyjne"]:
        pliki = _pliki_zrodla(katalog, wpis)
        if pliki:
            for rel in pliki:
                h, (n,) = skroty_plikow([katalog / rel], procesy)
                zrodla.append(({"id": wpis["id"], "sciezka": rel, "wierszy": n, "osmiogramow_unikalnych": int(len(h)),
                                "z_pliku_npy": False}, h))
        elif wpis["id"] in zewn:
            h = np.unique(np.load(zewn[wpis["id"]]).astype(np.uint64))
            zrodla.append(({"id": wpis["id"], "sciezka": wpis["sciezka"], "wierszy": None,
                            "osmiogramow_unikalnych": int(len(h)), "z_pliku_npy": True}, h))
        else:
            braki.append(wpis["sciezka"])
    return zrodla, {"kompletny": not braki, "braki": braki}


def polacz(zrodla: list[tuple[dict[str, Any], np.ndarray]]) -> np.ndarray:
    czesci = [h for _, h in zrodla]
    return np.unique(np.concatenate(czesci)) if czesci else np.empty(0, dtype=np.uint64)


def _konfigi(katalog: Path, wzorzec: str) -> list[int]:
    return [json.loads(p.read_text(encoding="utf-8"))["rows"] for p in sorted(katalog.glob(wzorzec))]


def sprawdz_linie(katalog: Path, linia: dict[str, Any], zrodla: list[tuple[dict[str, Any], np.ndarray]],
                  modele: Path | None = None) -> dict[str, Any]:
    """Zgodność opisu linii: liczba wierszy mieszanki każdego składnika z `config.json` jego przebiegu (tylko odczyt)
    oraz skład zupy w `soup.json` modelu z plikiem linii."""
    katalog = Path(katalog)
    wiersze = {o["id"]: o["wierszy"] for o, _ in zrodla if o["wierszy"] is not None and not o["sciezka"].endswith("*")}
    wpisy = [dict(linia["baza"], configi=linia["baza"]["config"], przebieg_rola="baza")] + \
            [dict(s, przebieg_rola="skladnik") for s in linia["skladniki"]]
    skladniki: list[dict[str, Any]] = []
    for w in wpisy:
        konf = _konfigi(katalog, w["configi"])
        wczytane = wiersze.get(w["mieszanka_train"])
        zgodne = bool(konf) and wczytane is not None and all(k == wczytane for k in konf)
        skladniki.append({"przebieg": w["przebieg"], "rola": w["przebieg_rola"], "krok": w.get("krok"),
                          "prep_from": w["prep_from"], "mieszanka_train": w["mieszanka_train"],
                          "wierszy_w_configach": konf, "wierszy_w_mieszance": wczytane,
                          "zgodne": zgodne if konf and wczytane is not None else None})
    plik = Path(modele or MODELE_DIR) / linia["zupa_plik"]
    zupa: dict[str, Any] = {"plik": linia["zupa_plik"], "zgodne": None}
    if plik.is_file():
        zrodla_zupy = json.loads(plik.read_text(encoding="utf-8"))["sources"]
        z_pliku = sorted((s["path"].split("/runs/")[1].split("/")[0], round(s["weight"], 6)) for s in zrodla_zupy)
        z_linii = sorted((s["przebieg"], round(s["waga"], 6)) for s in linia["skladniki"])
        zupa.update(skladniki=[p for p, _ in z_pliku], zgodne=z_pliku == z_linii)
    return {"model": linia["model"], "paczka": linia["paczka"], "wagi": linia["wagi"], "skladniki": skladniki, "zupa": zupa}


# ----------------------------------------------------------------------------- pomiar
def _wspolne(zapytanie: np.ndarray, ref: np.ndarray) -> np.ndarray:
    """Maska: które skróty `zapytanie` występują w posortowanej `ref`."""
    if not len(ref) or not len(zapytanie):
        return np.zeros(len(zapytanie), dtype=bool)
    idx = np.minimum(np.searchsorted(ref, zapytanie), len(ref) - 1)
    return ref[idx] == zapytanie


def _miara(unikalne: np.ndarray, ref: np.ndarray, wystapienia: np.ndarray | None = None) -> dict[str, Any]:
    maska = _wspolne(unikalne, ref)
    wynik: dict[str, Any] = {"osmiogramow_unikalnych": int(len(unikalne)), "wspolnych": int(maska.sum()),
                             "odsetek": float(maska.mean()) if len(unikalne) else 0.0}
    if wystapienia is not None:
        m = _wspolne(wystapienia, ref)
        wynik["wystapien"] = int(len(wystapienia))
        wynik["wystapien_wspolnych"] = int(m.sum())
        wynik["odsetek_wystapien"] = float(m.mean()) if len(wystapienia) else 0.0
    return wynik


def _bez(a: np.ndarray, formulowe: np.ndarray) -> np.ndarray:
    return a[~np.isin(a, formulowe)]


def _szablony() -> dict[tuple[str, str], list[str]]:
    from .szablony import SZABLONY
    return {k: [b.tekst_z_gniazdami for s in sz.sekcje for b in s.bloki] for k, sz in SZABLONY.items()}


def opis_zbioru(zrodla: list[tuple[dict[str, Any], np.ndarray]], stan: dict[str, Any]) -> dict[str, Any]:
    """Pole `zbior_referencyjny` wyniku (liczby i ścieżki; bez treści)."""
    return {"zrodla": [o for o, _ in zrodla],
            "osmiogramow_unikalnych": int(len(polacz(zrodla))), "probkowanie": "brak (100% wierszy)",
            "kompletny": stan["kompletny"], "braki": stan["braki"]}


def raport(korpus: Path, ref: np.ndarray, zbior: dict[str, Any], linia: dict[str, Any] | None = None) -> dict[str, Any]:
    """Raport kontaminacji szablonów (a) i wygenerowanego korpusu (b) względem zbioru referencyjnego `ref`
    (posortowane unikalne skróty; opis w `zbior`, patrz `opis_zbioru`; `linia` – wynik `sprawdz_linie`)."""
    # szablony: 8-gramy per (język, typ), formułkowe = w blokach >= PROG_TYPOW różnych typów
    typy_ngramu: dict[int, set[str]] = defaultdict(set)
    per_szablon: dict[tuple[str, str], np.ndarray] = {}
    z_cyfra: dict[int, bool] = {}
    for (jezyk, typ), bloki in _szablony().items():
        odcinki = [o for b in bloki for o in _DZIELNIK_SZABLONU.split(b)]
        h = osmiogramy_odcinkow(odcinki)
        z_cyfra.update(zip(h.tolist(), np.concatenate([okna_z_cyfra(o) for o in odcinki]).tolist()))
        h = np.unique(h)
        per_szablon[(jezyk, typ)] = h
        for x in h.tolist():
            typy_ngramu[x].add(typ)
    formulowe = np.array(sorted(x for x, t in typy_ngramu.items() if len(t) >= PROG_TYPOW), dtype=np.uint64)
    szablony_wszystkie = np.unique(np.concatenate(list(per_szablon.values())))
    po_jezykach: dict[str, Any] = {}
    for jezyk in sorted({j for j, _ in per_szablon}):
        h = np.unique(np.concatenate([v for (j, _), v in per_szablon.items() if j == jezyk]))
        po_jezykach[jezyk] = {"ogolem": _miara(h, ref), "poza_formulowymi": _miara(_bez(h, formulowe), ref)}

    # korpus: teksty poziomu 1
    wpisy = [json.loads(w) for w in (Path(korpus) / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    per_jezyk: dict[str, list[np.ndarray]] = defaultdict(list)
    for w in wpisy:
        per_jezyk[w["jezyk"]].append(osmiogramy((Path(korpus) / w["plik_txt"]).read_text(encoding="utf-8")))
    wyst_wszystkie = np.concatenate([a for l in per_jezyk.values() for a in l])
    korpus_jezyki: dict[str, Any] = {}
    for jezyk, lista in sorted(per_jezyk.items()):
        wyst = np.concatenate(lista)
        korpus_jezyki[jezyk] = {"ogolem": _miara(np.unique(wyst), ref, wyst),
                                "poza_formulowymi": _miara(_bez(np.unique(wyst), formulowe), ref, _bez(wyst, formulowe))}
    uni = np.unique(wyst_wszystkie)

    poza = _miara(_bez(szablony_wszystkie, formulowe), ref)
    # diagnostyka: ile wspólnych 8-gramów szablonów to powołania z cyframi (artykuły, §, lata), a ile słowa bez cyfr
    bez_formulowych = _bez(szablony_wszystkie, formulowe)
    maska_wsp = _wspolne(bez_formulowych, ref)
    cyfra = np.array([z_cyfra[x] for x in bez_formulowych.tolist()], dtype=bool)
    diagnostyka = {
        "szablony_poza_formulowymi_z_cyfra": {"osmiogramow": int(cyfra.sum()), "wspolnych": int((maska_wsp & cyfra).sum()),
                                               "odsetek": float(maska_wsp[cyfra].mean()) if cyfra.any() else 0.0},
        "szablony_poza_formulowymi_bez_cyfr": {"osmiogramow": int((~cyfra).sum()),
                                                "wspolnych": int((maska_wsp & ~cyfra).sum()),
                                                "odsetek": float(maska_wsp[~cyfra].mean()) if (~cyfra).any() else 0.0},
    }
    korpus_poza = _miara(_bez(uni, formulowe), ref, _bez(wyst_wszystkie, formulowe))
    return {
        "data": dt.date.today().isoformat(),
        "n_gram": N_GRAM,
        "metoda": "8-gramy słowne: małe litery, ciągi liter i cyfr bez interpunkcji, skrót 64-bit; odsetek "
                  "unikalnych 8-gramów obecnych w treningu (bez próbkowania)",
        "linia_modelu": linia,
        "zbior_referencyjny": zbior,
        "frazy_formulowe": {
            "definicja": f"8-gramy występujące w blokach szablonów co najmniej {PROG_TYPOW} różnych typów dokumentów",
            "prog_typow": PROG_TYPOW, "liczba": int(len(formulowe)),
            "odsetek_8gramow_szablonow": float(len(formulowe) / len(szablony_wszystkie)),
        },
        "szablony": {"ogolem": _miara(szablony_wszystkie, ref), "poza_formulowymi": poza, "po_jezykach": po_jezykach},
        "korpus": {"dokumentow": len(wpisy), "ogolem": _miara(uni, ref, wyst_wszystkie),
                   "poza_formulowymi": korpus_poza, "po_jezykach": korpus_jezyki},
        "diagnostyka": diagnostyka,
        "cel": {"odsetek_maks": CEL_ODSETEK,
                "szablony_poza_formulowymi": poza["odsetek"] < CEL_ODSETEK,
                "korpus_poza_formulowymi": korpus_poza["odsetek"] < CEL_ODSETEK},
    }


def tylko_skroty(wejscia: list[Path], wyjscie: Path, procesy: int | None = None) -> dict[str, int]:
    """Zapisuje unikalne skróty 8-gramów z pól `input` plików JSONL (uint64, .npy; bez treści)."""
    h, wiersze = skroty_plikow(list(wejscia), procesy)
    wyjscie = Path(wyjscie)
    wyjscie.parent.mkdir(parents=True, exist_ok=True)
    with open(wyjscie, "wb") as f:   # bez dopisywania rozszerzenia przez numpy
        np.save(f, h)
    return {"wierszy": sum(wiersze), "osmiogramow_unikalnych": int(len(h))}


def _zapisz(sciezka: Path, wynik: dict[str, Any]) -> None:
    sciezka.parent.mkdir(parents=True, exist_ok=True)
    sciezka.write_text(json.dumps(wynik, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pbench-kontaminacja", description="Kontrola kontaminacji korpusu vs trening.")
    ap.add_argument("--korpus", type=Path, default=Path("korpus"))
    ap.add_argument("--legal-texts", type=Path, default=None, help="katalog danych treningowych (wymagany poza --tylko-skroty)")
    ap.add_argument("--linia", type=Path, default=None, help="opis linii modelu (domyślnie metodyka/linia-modelu-rc5.json)")
    ap.add_argument("--wyjscie", type=Path, default=Path("metodyka/kontaminacja.json"))
    ap.add_argument("--korpus-trudne", type=Path, default=None, help="dodatkowo warstwa trudna (zbiór referencyjny liczony raz)")
    ap.add_argument("--wyjscie-trudne", type=Path, default=Path("metodyka/kontaminacja-trudne.json"))
    ap.add_argument("--skroty-zewnetrzne", action="append", default=[], metavar="[ID=]PLIK.npy",
                    help="gotowe skróty brakującego źródła (id = nazwa pliku bez .npy); można wielokrotnie")
    ap.add_argument("--tylko-skroty", action="store_true", help="tylko policz skróty z --wejscie i zapisz do --wyjscie (.npy)")
    ap.add_argument("--wejscie", type=Path, nargs="+", default=[])
    ap.add_argument("--procesy", type=int, default=None)
    a = ap.parse_args(argv)
    if a.tylko_skroty:
        if not a.wejscie or a.wyjscie == Path("metodyka/kontaminacja.json"):
            ap.error("--tylko-skroty wymaga --wejscie i --wyjscie X.npy")
        print(json.dumps(tylko_skroty(a.wejscie, a.wyjscie, a.procesy)))
        return 0
    if a.legal_texts is None:
        ap.error("--legal-texts jest wymagany (katalog danych treningowych modelu)")
    linia = wczytaj_linie(a.linia)
    zrodla, stan = zbior_referencyjny(a.legal_texts, linia, a.procesy, a.skroty_zewnetrzne)
    info = sprawdz_linie(a.legal_texts, linia, zrodla)
    wyniki = [(a.korpus, a.wyjscie)]
    if a.korpus_trudne:
        wyniki += [(a.korpus_trudne, a.wyjscie_trudne)]
    for korpus_k, sciezka in wyniki:
        wynik = raport(korpus_k, polacz(zrodla), opis_zbioru(zrodla, stan), info)
        _zapisz(sciezka, wynik)
        print(json.dumps({"wyjscie": str(sciezka), "kompletny": wynik["zbior_referencyjny"]["kompletny"],
                          "szablony_poza_formulowymi": wynik["szablony"]["poza_formulowymi"]["odsetek"],
                          "korpus_poza_formulowymi": wynik["korpus"]["poza_formulowymi"]["odsetek"],
                          "cel": wynik["cel"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
