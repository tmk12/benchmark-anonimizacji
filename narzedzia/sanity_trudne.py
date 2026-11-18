"""Sanity sędziów na całej warstwie trudnych przypadków (H6b; nie jest testem – plikowy z OCR trwa długo).

    uv run python narzedzia/sanity_trudne.py --korpus korpus-trudne --poziom tekst > tekst.json
    uv run python narzedzia/sanity_trudne.py --korpus korpus-trudne --poziom plik --probka 2 --procesy 12 > plik.json
    uv run python narzedzia/sanity_trudne.py --poziom plik --probka 1 --id h-sp-de-cv-0001 --id … > plik.json

Poziom tekst (bez OCR, cała warstwa): oryginał = wykrycia puste (wszystko ma wyciec), uczestnik idealny = wykrycia równe
spanom `gold_tekst` (0 wycieków). Poziom plik (OCR; `--probka N` – N pierwszych dokumentów każdego przypadku wg skrótu `id`,
0 = wszystkie): oryginał = ocena kopii oryginału, idealny = dokument odtworzony z ziarna z wartościami zamienionymi na
`[KATEGORIA_n]` (`sedzia.sanity.Maskowanie`) – jak w testach H1–H6a. Sędziowie bez zmian; leksykon – z manifestu warstwy.
Wynik: JSON (rekordy per dokument + tabela per przypadek główny z planu) na stdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from pbench import ocen, trudne, trudne_warstwa as W
from pbench.sedzia.plik import leksykon_z_manifestu, ocen_plik
from pbench.sedzia.sanity import Maskowanie, wartosci_wpisu

REGULY = ocen.REGULY_DOMYSLNE


def _tekst(arg: tuple[dict, str]) -> dict:
    wpis, korpus = arg
    k = Path(korpus)
    orig = ocen._ocen_tekstowo(wpis, {"wykrycia": []}, k, REGULY)
    ideal = ocen._ocen_tekstowo(wpis, {"wykrycia": [[g["start"], g["end"], g["kategoria"], 1.0] for g in wpis["gold_tekst"]]},
                                k, REGULY)
    return {"id": wpis["id"], "orig_wycieki": len(orig["wycieki"]), "ocenione": orig["wartosci_ocenione"],
            "ideal_wycieki": [w[:2] for w in ideal["wycieki"]], "ideal_fp": ideal["fp_znaki"],
            "posrednie_orig": [k["przerwana"] for k in orig.get("posrednie") or []],
            "posrednie_ideal": [k["przerwana"] for k in ideal.get("posrednie") or []]}


def _plik(arg: tuple[dict, str, str]) -> dict:
    wpis, korpus, przypadek = arg
    k = Path(korpus)
    start = time.monotonic()
    leksykon = leksykon_z_manifestu(k / "manifest.jsonl")
    ws = wartosci_wpisu(wpis)
    orig = k / wpis["plik"]
    a = ocen_plik(orig, orig, ws, leksykon=leksykon, posrednie=wpis.get("posrednie") or None)
    with tempfile.TemporaryDirectory(prefix="pbench-sanity-") as tmp:
        poz = trudne.PozycjaTrudna(wpis["id"], wpis["jezyk"], wpis["typ"], wpis["format"], przypadek)
        r = trudne.generuj_dokument_trudny(poz, trudne.ZIARNO_TRUDNE, wpis["split"], Path(tmp), maskuj=Maskowanie())
        b = ocen_plik(orig, Path(tmp) / r["plik"], ws, leksykon=leksykon, posrednie=wpis.get("posrednie") or None)
    oceniane = {w.id for w in ws} - set(a.niewykrywalne) - set(a.niejednoznaczne)
    return {"id": wpis["id"], "status": a.status, "orig_wycieki": len(a.wycieki), "ocenione": a.wartosci_ocenione,
            "wartosci": len({w.id for w in ws}), "niewykrywalne": len(a.niewykrywalne),
            "niejednoznaczne": len(a.niejednoznaczne),
            "orig_niewyciekle": sorted(oceniane - {w[0] for w in a.wycieki})[:20],
            "ideal_status": b.status, "ideal_wycieki": [list(w) for w in b.wycieki],
            "posrednie_orig": [x["przerwana"] for x in a.posrednie or []],
            "posrednie_ideal": [x["przerwana"] for x in b.posrednie or []], "czas_s": round(time.monotonic() - start, 1)}


def tabela(rekordy: list[dict], glowny: dict[str, str]) -> dict[str, dict]:
    """Per przypadek główny: dokumenty, dokumenty z wyciekiem w oryginale, wycieki oryginału / ocenione, dokumenty
    z wyciekiem u idealnego i liczba jego wycieków."""
    wynik: dict[str, dict] = defaultdict(lambda: {"dok": 0, "orig_dok_z_wyciekiem": 0, "orig_wycieki": 0, "ocenione": 0,
                                                  "ideal_dok_z_wyciekiem": 0, "ideal_wycieki": 0})
    for r in rekordy:
        t = wynik[glowny[r["id"]]]
        t["dok"] += 1
        t["orig_dok_z_wyciekiem"] += r["orig_wycieki"] > 0
        t["orig_wycieki"] += r["orig_wycieki"]
        t["ocenione"] += r["ocenione"]
        t["ideal_dok_z_wyciekiem"] += bool(r["ideal_wycieki"])
        t["ideal_wycieki"] += len(r["ideal_wycieki"])
    return {p: wynik[p] for p in W.ROZKLAD if p in wynik}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--korpus", type=Path, default=Path("korpus-trudne"))
    ap.add_argument("--poziom", choices=("tekst", "plik"), required=True)
    ap.add_argument("--probka", type=int, default=0, help="plik: dokumentów na przypadek (0 = wszystkie)")
    ap.add_argument("--id", action="append", default=[], help="plik: także te dokumenty (powtarzalne; poza próbką)")
    ap.add_argument("--procesy", type=int, default=8)
    a = ap.parse_args(argv)
    wpisy = [json.loads(w) for w in (a.korpus / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    glowny = {p.id: p.przypadek for p in W.zaplanuj_warstwe()}
    start = time.monotonic()
    if a.poziom == "tekst":
        zadania, funkcja = [(w, str(a.korpus)) for w in wpisy], _tekst
    else:
        po_przypadku: dict[str, list[dict]] = defaultdict(list)
        for w in sorted(wpisy, key=lambda w: hashlib.sha256(w["id"].encode()).hexdigest()):
            po_przypadku[glowny[w["id"]]].append(w)
        wybrane = [w for lista in po_przypadku.values() for w in (lista[:a.probka] if a.probka else lista)]
        wybrane += [w for w in wpisy if w["id"] in a.id and w not in wybrane]
        zadania, funkcja = [(w, str(a.korpus), glowny[w["id"]]) for w in wybrane], _plik
    with ProcessPoolExecutor(max_workers=a.procesy) as pula:
        rekordy = list(pula.map(funkcja, zadania, chunksize=1))
    json.dump({"poziom": a.poziom, "dokumentow": len(rekordy), "czas_s": round(time.monotonic() - start),
               "tabela": tabela(rekordy, glowny), "rekordy": rekordy}, sys.stdout, ensure_ascii=False, indent=1)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
