"""Sanity sędziego plikowego na prawdziwym korpusie (nie jest testem jednostkowym – długo trwa, korzysta z OCR).

`uv run python -m pbench.sedzia.sanity --korpus korpus --na-format-jezyk 2 --procesy 12`

Na próbce (domyślnie po 2 dokumenty z każdej pary format × język; ≥ 80 dokumentów) sprawdza:

(a) **oryginał jako wynik** – wszystkie wartości możliwe do wycieku wyciekają; wartości obrazowe, których OCR nie
    znajduje w oryginale, są `niewykrywalne` (a nie „nieznalezione”);
(b) **„idealny uczestnik”** – dokument odtworzony z ziarna (`korpus.generuj_dokument(..., maskuj=…)`), z tekstem każdej
    `Wartosc` zamienionym na `[KATEGORIA_n]` (stałe n na encję = rolę `encja(id)`), wyrenderowany tym samym rendererem
    (także obrazy: logo, podpis, strony skanu rysują już zamiennik) → 0 wycieków, spójność 1,0, struktura ~1,0;
(d) **uczestnik częściowy** (maskuje połowę ról: wykryć ma wszystkie niezamaskowane), **uczestnik „dane fikcyjne”** (podmiana na wartości z innych dokumentów, stale na rolę: 0 wycieków; raportowana reszta) i **oryginał zrasteryzowany** (PDF → obrazy stron: OCR ma odnaleźć tekst);
(c) **plik uszkodzony** (1 KB bajtów bez struktury formatu; obcięcie do 200 B raportowane osobno) → NIECZYTELNY; **pusty** → PUSTY.

Wynik: JSON z liczbami, listą rozbieżności i czasami (stdout) – używany do raportu zadania 10.
"""
from __future__ import annotations

import argparse
import dataclasses
import io
import json
import os
import random
import tempfile
import time
import zlib
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from ..korpus import ZIARNO, Pozycja, generuj_dokument
from ..model import Dokument, Element, Wartosc
from . import obrazy
from .normalizacja import normalizuj
from .plik import _tokeny, encja, ocen_plik, zbuduj_leksykon


def wartosci_wpisu(wpis: dict) -> list[Wartosc]:
    """`gold_plik` + `gold_obrazy` z krotnością: wartość obrazowa występuje raz na każdy obraz/stronę, na której jest
    (nagłówek biegnący skanu = kilka egzemplarzy tego samego `id`); wartości `gold_plik` obrazowe, których nie ma w
    żadnym `gold_obrazy`, dochodzą raz. Wartości tekstowe – raz na `id`."""
    gold_plik = [Wartosc.from_dict(w) for w in wpis["gold_plik"]]
    wynik = [w for w in gold_plik if not w.w_pikselach]
    w_obrazach = [Wartosc.from_dict(w) for o in wpis["gold_obrazy"] for w in o["wartosci"]]
    znane = {w.id for w in w_obrazach}
    return wynik + w_obrazach + [w for w in gold_plik if w.w_pikselach and w.id not in znane]


class Maskowanie:
    """Zamienia tekst każdej `Wartosc` w dokumencie na `[KATEGORIA_n]` (n stałe dla roli `encja(id)`, dopełnione `_` do długości oryginału; jedna instancja na
    plik, więc numeracja jest wspólna dla treści i załącznika e-maila). Zwraca kopię dokumentu."""

    def __init__(self) -> None:
        self.numery: dict[tuple[str, str], int] = {}

    def _zamien(self, w: Wartosc) -> Wartosc:
        n = self.numery.setdefault((w.kategoria, encja(w.id)), len(self.numery) + 1)
        if not w.tekst:
            return w
        ph = f"[{w.kategoria}_{n}]"
        return dataclasses.replace(w, tekst=ph + "_" * (len(w.tekst) - len(ph)))   # ta sama długość: układ strony bez zmian

    def __call__(self, d: Dokument) -> Dokument:
        n = Dokument.from_dict(d.to_dict())
        n.elementy = [Element(e.rodzaj, [f if isinstance(f, str) else self._zamien(f) for f in e.fragmenty], e.atrybuty)
                      for e in n.elementy]
        n.metadane = {k: (v if isinstance(v, str) else self._zamien(v)) for k, v in n.metadane.items()}
        n.ukryte = [Element(e.rodzaj, [f if isinstance(f, str) else self._zamien(f) for f in e.fragmenty], e.atrybuty)
                    for e in n.ukryte]
        return n


maskuj_dokument = Maskowanie


class Czesciowe(Maskowanie):
    """Uczestnik maskujący tylko połowę ról (parzysty crc32 roli): pozytywna kontrola – sędzia musi znaleźć resztę."""

    @staticmethod
    def zamaskowana(wid: str) -> bool:
        return zlib.crc32(encja(wid.removeprefix("zal:")).encode()) % 2 == 0   # załącznik: ta sama rola co w treści

    def _zamien(self, w: Wartosc) -> Wartosc:
        return super()._zamien(w) if self.zamaskowana(w.id) else w


class Sztuczne(Maskowanie):
    """Uczestnik podmieniający każdą wartość na wartość tej samej kategorii i języka z INNEGO dokumentu korpusu, stale
    na rolę (dane fikcyjne zamiast znaczników). Oczekiwane 0 wycieków; reszta = kolizje korpusu."""

    def __init__(self, doc: str, pula: dict, zakazane: frozenset[str] = frozenset()) -> None:
        super().__init__()
        self.doc, self.pula, self.wybor, self.zakazane = doc, pula, {}, zakazane

    def _zamien(self, w: Wartosc) -> Wartosc:
        if not w.tekst:
            return w
        klucz = (w.kategoria, encja(w.id))
        if klucz not in self.wybor:
            rnd = random.Random(zlib.crc32(f"{self.doc}|{klucz}".encode()))
            kand = [t for d, t in self.pula.get((w.kategoria, w.jezyk), ()) if d != self.doc]
            rnd.shuffle(kand)
            # zamiennik rozłączny tokenowo z całym gold tego dokumentu (inaczej „wyciek” to kolizja danych fikcyjnych)
            self.wybor[klucz] = next((t for t in kand if not (set(_tokeny(t)) & self.zakazane)), "X")
        return dataclasses.replace(w, tekst=self.wybor[klucz])


_PULA: dict = {}
_LEKSYKON: dict = {}


def _init(pula: dict, leksykon: dict) -> None:
    _PULA.update(pula)
    _LEKSYKON.update(leksykon)


def zrasteryzuj(pdf: Path, cel: Path) -> None:
    """PDF → PDF złożony wyłącznie z obrazów stron (200 dpi): tekst przestaje istnieć jako tekst."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(pdf))
    try:
        strony = [doc[i].render(scale=200 / 72).to_pil().convert("RGB") for i in range(len(doc))]
    finally:
        doc.close()
    strony[0].save(cel, save_all=True, append_images=strony[1:], resolution=200)


def _jedno(arg: tuple[dict, str]) -> dict:
    wpis, katalog = arg
    os.environ["PBENCH_OCR_WATKI"] = "2"
    _LEKSYKON.setdefault("pl", frozenset())
    kat = Path(katalog)
    orig = kat / wpis["plik"]
    ws = wartosci_wpisu(wpis)
    by_id = {w.id: w for w in ws}
    czesci_id: dict[str, list[Wartosc]] = {}
    for w in ws:
        czesci_id.setdefault(w.id, []).append(w)
    wynik: dict = {"id": wpis["id"], "format": wpis["format"], "jezyk": wpis["jezyk"], "wartosci": len(ws),
                   "problemy": [], "czasy": {}}
    t0 = time.monotonic()
    try:
        a = ocen_plik(orig, orig, ws, leksykon=_LEKSYKON)
        wynik["czasy"]["oryginal"] = round(time.monotonic() - t0, 1)
        wyciekly = {w[0] for w in a.wycieki}
        pomin = set(a.niewykrywalne) | set(a.niejednoznaczne)
        brak = [w for w in ws if w.id not in wyciekly and w.id not in pomin]
        wynik["a_niejednoznaczne"] = len(a.niejednoznaczne)
        # wartości, które z założenia nie mogą wyciec (bez liczącego się tokenu: pojedyncze znaki, „ul.”)
        wynik["a_niewykrywalne"] = len(a.niewykrywalne)
        wynik["a_ocenione"] = a.wartosci_ocenione
        wynik["a_wycieki"] = len(a.wycieki)
        wynik["a_nieznalezione"] = [(w.id, w.kategoria, w.miejsce, w.tekst) for w in brak
                                    if w.id not in wyciekly][:50]
        wynik["a_niewykr_ids"] = list(a.niewykrywalne)[:20]
        t1 = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="pbench-sanity-") as tmp:
            idealny = generuj_dokument(Pozycja(wpis["id"], wpis["jezyk"], wpis["typ"], wpis["format"]), ZIARNO,
                                       wpis["split"], Path(tmp), maskuj=Maskowanie())
            b = ocen_plik(orig, Path(tmp) / idealny["plik"], ws, leksykon=_LEKSYKON)
            wynik["czasy"]["idealny"] = round(time.monotonic() - t1, 1)
            wynik["b_status"] = b.status
            wynik["b_wycieki"] = [(i, k, m, r) for i, k, m, r in b.wycieki]
            wynik["b_spojnosc"] = b.integralnosc["spojnosc"]
            wynik["b_encje"] = b.integralnosc["encje"]
            wynik["b_struktura"] = b.integralnosc["zachowanie_struktury"]
            wynik["b_struktury"] = b.integralnosc["struktura"]
        # --- uczestnik częściowy (kontrola pozytywna): wycieki = wartości niezamaskowanych ról
        t2 = time.monotonic()
        poz = Pozycja(wpis["id"], wpis["jezyk"], wpis["typ"], wpis["format"])
        with tempfile.TemporaryDirectory(prefix="pbench-sanity-") as tmp:
            r = generuj_dokument(poz, ZIARNO, wpis["split"], Path(tmp), maskuj=Czesciowe())
            c = ocen_plik(orig, Path(tmp) / r["plik"], ws, leksykon=_LEKSYKON)
        # ocena na poziomie TEKSTÓW (wiele `id` ma ten sam tekst, a plik zawiera go tyle razy, ile zostało niezamaskowanych)
        nm = [w for w in ws if not Czesciowe.zamaskowana(w.id) and w.id in wyciekly]
        oczek_teksty = {normalizuj(w.tekst) for w in nm}
        oczek_tokeny = {t for w in nm for t in _tokeny(w.tekst)}
        wykryte = [p for x in c.wycieki for p in czesci_id[x[0]]]
        wykryte_teksty = {normalizuj(w.tekst) for w in wykryte}
        wynik["c_oczekiwane"] = len(oczek_teksty)
        wynik["c_wykryte_z_oczekiwanych"] = len(oczek_teksty & wykryte_teksty)
        wynik["c_nadmiarowe"] = [(w.id, w.tekst) for w in wykryte if normalizuj(w.tekst) not in oczek_teksty
                                 and not (set(_tokeny(w.tekst)) & oczek_tokeny)][:10]
        wynik["c_nie_znalezione"] = [(w.id, w.kategoria, w.miejsce, w.tekst) for w in nm
                                     if normalizuj(w.tekst) not in wykryte_teksty][:10]
        wynik["czasy"]["czesciowy"] = round(time.monotonic() - t2, 1)
        # --- uczestnik „dane fikcyjne”: oczekiwane 0 wycieków
        t3 = time.monotonic()
        sztuczne = Sztuczne(wpis["id"], _PULA, frozenset(t for w in ws for t in _tokeny(w.tekst)))
        with tempfile.TemporaryDirectory(prefix="pbench-sanity-") as tmp:
            r = generuj_dokument(poz, ZIARNO, wpis["split"], Path(tmp), maskuj=sztuczne)
            f = ocen_plik(orig, Path(tmp) / r["plik"], ws, leksykon=_LEKSYKON)
        zam_tokeny = {t for v in sztuczne.wybor.values() for t in _tokeny(v)}
        wynik["f_wycieki"] = [(i, k, m, ro, " | ".join(p.tekst for p in czesci_id[i])) for i, k, m, ro in f.wycieki]
        # wyciek „wyjaśniony kolizją”: token wartości jest też tokenem podstawionej wartości (dane fikcyjne się powtarzają)
        wynik["f_niewyjasnione"] = [x for x in wynik["f_wycieki"] if not ({t for p in czesci_id[x[0]] for t in _tokeny(p.tekst)} & zam_tokeny)]
        wynik["f_spojnosc"] = f.integralnosc["spojnosc"]
        wynik["czasy"]["sztuczne"] = round(time.monotonic() - t3, 1)
        # --- oryginał zrasteryzowany (PDF): tekst tylko jako obraz; OCR ma go odnaleźć
        if wpis["format"] == "pdf":
            t4 = time.monotonic()
            with tempfile.TemporaryDirectory(prefix="pbench-sanity-") as tmp:
                zrasteryzuj(orig, Path(tmp) / "r.pdf")
                rr = ocen_plik(orig, Path(tmp) / "r.pdf", ws, leksykon=_LEKSYKON)
            wynik["r_wykryte"] = len({x[0] for x in rr.wycieki} & wyciekly)
            wynik["r_mozliwe"] = len(wyciekly)
            wynik["czasy"]["raster"] = round(time.monotonic() - t4, 1)
        dane = orig.read_bytes()
        with tempfile.TemporaryDirectory(prefix="pbench-sanity-") as tmp:
            zly = Path(tmp) / orig.name
            zly.write_bytes(dane[:200])
            wynik["c_obciety"] = ocen_plik(orig, zly, ws, leksykon=_LEKSYKON).status   # EML obcięty nadal ma nagłówki: „OK” jest poprawne
            zly.write_bytes(bytes(range(256)) * 4)
            wynik["c_uszkodzony"] = ocen_plik(orig, zly, ws, leksykon=_LEKSYKON).status
            zly.write_bytes(b"")
            wynik["c_pusty"] = ocen_plik(orig, zly, ws, leksykon=_LEKSYKON).status
    except Exception as e:  # noqa: BLE001
        import traceback
        wynik["problemy"].append(f"WYJATEK {type(e).__name__}: {e}\n{traceback.format_exc()[-800:]}")
    wynik["czasy"]["razem"] = round(time.monotonic() - t0, 1)
    return wynik


def wybierz(manifest: list[dict], na_pare: int) -> list[dict]:
    """Po `na_pare` dokumentów z każdej pary format × język (deterministycznie: kolejne identyfikatory co ~N/2)."""
    grupy: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for w in manifest:
        grupy[(w["format"], w["jezyk"])].append(w)
    wynik = []
    for klucz in sorted(grupy):
        g = sorted(grupy[klucz], key=lambda w: w["id"])
        krok = max(1, len(g) // na_pare)
        wynik += g[::krok][:na_pare]
    return wynik


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pbench.sedzia.sanity")
    ap.add_argument("--korpus", type=Path, default=Path("korpus"))
    ap.add_argument("--na-format-jezyk", type=int, default=2)
    ap.add_argument("--procesy", type=int, default=12)
    ap.add_argument("--formaty", default=None)
    ap.add_argument("--wyjscie", type=Path, default=None)
    a = ap.parse_args(argv)
    manifest = [json.loads(l) for l in (a.korpus / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    if a.formaty:
        manifest = [w for w in manifest if w["format"] in a.formaty.split(",")]
    pelny = [json.loads(l) for l in (a.korpus / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    pula: dict = defaultdict(list)
    for w in pelny:
        for g in w["gold_plik"]:
            pula[(g["kategoria"], w["jezyk"])].append((w["id"], g["tekst"]))
    leksykon = zbuduj_leksykon(pelny)
    probka = wybierz(manifest, a.na_format_jezyk)
    print(f"próbka: {len(probka)} dokumentów", flush=True)
    t0 = time.monotonic()
    with ProcessPoolExecutor(max_workers=a.procesy, initializer=_init, initargs=(dict(pula), leksykon)) as ex:
        wyniki = list(ex.map(_jedno, [(w, str(a.korpus)) for w in probka], chunksize=1))
    razem = time.monotonic() - t0
    po_formacie: dict[str, dict] = defaultdict(lambda: Counter())
    for r in wyniki:
        c = po_formacie[r["format"]]
        c["dokumenty"] += 1
        c["wyjatek"] += bool(r["problemy"])
        c["a_nieznalezione"] += len(r.get("a_nieznalezione", []))
        c["b_wycieki"] += len(r.get("b_wycieki", []))
        c["b_dok_z_wyciekiem"] += bool(r.get("b_wycieki"))
        c["b_spojnosc_ne_1"] += (r.get("b_spojnosc") not in (None, 1.0))
        c["b_struktura_lt_095"] += (r.get("b_struktura") is not None and r["b_struktura"] < 0.95)
        c["c_ok"] += (r.get("c_uszkodzony") == "NIECZYTELNY" and r.get("c_pusty") == "PUSTY")
        c["a_niewykrywalne"] += r.get("a_niewykrywalne", 0)
        c["a_niejednoznaczne"] += r.get("a_niejednoznaczne", 0)
        c["a_ocenione"] += r.get("a_ocenione", 0)
        c["wartosci"] += r.get("wartosci", 0)
        c["c_oczekiwane"] += r.get("c_oczekiwane", 0)
        c["c_wykryte"] += r.get("c_wykryte_z_oczekiwanych", 0)
        c["c_nadmiarowe"] += len(r.get("c_nadmiarowe", []))
        c["f_wycieki"] += len(r.get("f_wycieki", []))
        c["f_dok_z_wyciekiem"] += bool(r.get("f_wycieki"))
        c["f_niewyjasnione"] += len(r.get("f_niewyjasnione", []))
        c["r_wykryte"] += r.get("r_wykryte", 0)
        c["r_mozliwe"] += r.get("r_mozliwe", 0)
        c["sek"] += r["czasy"].get("razem", 0)
    podsumowanie = {"dokumentow": len(wyniki), "sekundy_lacznie": round(razem), "po_formacie": {k: dict(v) for k, v in po_formacie.items()}}
    wydruk = {"podsumowanie": podsumowanie, "wyniki": wyniki}
    if a.wyjscie:
        a.wyjscie.write_text(json.dumps(wydruk, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(podsumowanie, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
