"""Kalibracja progu uczestnika grupy A na części dev (spec §3–4): próg maksymalizujący char-F2 sędziego tekstowego.

    uv run pbench-kalibruj --uczestnik <id> --wyniki wyniki/ [--zapisz]

Wejście: wyniki surowe dev uczestnika zebrane w trybie podłogi (`PBENCH_SUROWE=1` → próg 0,05, uczestnik zwraca wykrycia
ze swoimi wynikami pewności): `<wyniki>/surowe/<id>/dev/tekst.jsonl`. Dla każdego progu siatki wykrycia z wynikiem poniżej progu
są odrzucane (`wynik >= próg` zostaje – jak filtr uczestników, `protokol_uczestnika.wczytaj_prog`), a dokument oceniany tą samą
funkcją co `pbench-ocen` (`ocen._ocen_tekstowo`, sędzia `ocen_tekst`, reguły z `metodyka/prerejestracja.md`) – bez własnej logiki
oceny. Miara progu = **średnia z `char_f2` dokumentów dev** (wszystkie języki razem: jeden próg na uczestnika); dokumenty bez
wyniku (`blad`, `pominiety`) wchodzą z pustymi wykryciami, jak w ocenie (od progu nie zależą). Remis → wyższy próg.

Uczestnik bez wyniku pewności (wszystkie wykrycia z tym samym wynikiem albo brak wykryć – np. `stanza`, `scrubadub`) nie jest
kalibrowany: `kalibruj` zwraca None, `prog.json` nie powstaje. `--zapisz` zapisuje `uczestnicy/<id>/prog.json`
(`{"prog": x, ...}`; czyta go `wczytaj_prog`, pozostałe pola to metadane: siatka, F2 dla każdego progu, data, commit sędziego,
liczba dokumentów)."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import ocen
from .uruchom import KORZEN, wczytaj_manifest

#: Siatka domyślna: 0,01 … 0,04 co 0,01 (optimum modeli GLiNER wypadło na brzegu 0,05), potem 0,05 … 0,95 co 0,05.
SIATKA = [0.01, 0.02, 0.03, 0.04] + [round(0.05 * i, 2) for i in range(1, 20)]
EPS = 1e-12                                      # tolerancja remisu średnich F2


def _surowe_dev(wyniki_dev: Path, poziom: str = "tekst") -> Path:
    """`wyniki_dev` – katalog `surowe/<id>/dev` albo wprost plik `tekst.jsonl`."""
    p = Path(wyniki_dev)
    return p if p.is_file() else p / f"{poziom}.jsonl"


def ma_wynik_pewnosci(surowe: dict[str, dict[str, Any]]) -> bool:
    """Czy wykrycia niosą wynik pewności: co najmniej dwie różne wartości wyniku w całym dev."""
    wyniki = {w[3] for rek in surowe.values() for w in rek.get("wykrycia", ())}
    return len(wyniki) > 1


def _f2_dokumentu(arg: tuple) -> float:
    """Zadanie puli: `char_f2` jednego dokumentu przy progu (ta sama ocena co `pbench-ocen`)."""
    wpis, rek, prog, korpus, reguly = arg
    wyk = [w for w in rek.get("wykrycia", ()) if w[3] >= prog]
    return float(ocen._ocen_tekstowo(wpis, {"wykrycia": wyk}, Path(korpus), Path(reguly))["char_f2"])


def krzywa(wyniki_dev: Path, siatka: list[float], *, korpus: Path = KORZEN / "korpus",
           reguly: Path = ocen.REGULY_DOMYSLNE, procesy: int | None = 1) -> tuple[dict[float, float], int] | None:
    """Średnie `char_f2` dev dla każdego progu siatki i liczba ocenianych dokumentów; None – uczestnik bez wyniku pewności."""
    surowe = ocen._wczytaj_surowe(_surowe_dev(wyniki_dev))
    if not ma_wynik_pewnosci(surowe):
        return None
    wpisy = [w for w in wczytaj_manifest(Path(korpus)) if w["split"] == "dev" and w["id"] in surowe]
    if not wpisy:
        raise ValueError(f"brak dokumentów dev z wynikiem surowym w {wyniki_dev}")
    n = procesy or min(8, os.cpu_count() or 1)
    f2: dict[float, float] = {}
    for prog in siatka:
        zadania = [(w, surowe[w["id"]], prog, str(korpus), str(reguly)) for w in wpisy]
        if n <= 1:
            wartosci = [_f2_dokumentu(z) for z in zadania]
        else:
            with ProcessPoolExecutor(max_workers=n) as pula:
                wartosci = list(pula.map(_f2_dokumentu, zadania, chunksize=8))
        f2[prog] = sum(wartosci) / len(wartosci)
    return f2, len(wpisy)


def wybierz_prog(f2: dict[float, float]) -> float:
    """Próg o największej średniej F2; remis (do `EPS`) → wyższy próg."""
    maks = max(f2.values())
    return max(p for p, v in f2.items() if v >= maks - EPS)


def kalibruj(id: str, wyniki_dev: Path, siatka: list[float] | None = None, *, korpus: Path = KORZEN / "korpus",
             reguly: Path = ocen.REGULY_DOMYSLNE, procesy: int | None = 1) -> float | None:
    """Próg maksymalizujący char-F2 na dev dla uczestnika `id` (surowe wyniki dev w `wyniki_dev`); None – uczestnik bez wyniku
    pewności (nie kalibrujemy)."""
    k = krzywa(wyniki_dev, siatka or SIATKA, korpus=korpus, reguly=reguly, procesy=procesy)
    return None if k is None else wybierz_prog(k[0])


def commit_sedziego() -> str | None:
    """Commit, w którym ostatnio zmieniono sędziego (`pbench/sedzia`); None poza repozytorium."""
    try:
        w = subprocess.run(["git", "log", "-1", "--format=%H", "--", "pbench/sedzia"], cwd=KORZEN, capture_output=True,
                           text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return w or None


def zapisz_prog(katalog_uczestnika: Path, prog: float, f2: dict[float, float], liczba_dokumentow: int) -> Path:
    """Zapisuje `<katalog>/prog.json` (`prog` + metadane kalibracji)."""
    cel = Path(katalog_uczestnika) / "prog.json"
    cel.write_text(json.dumps({
        "prog": prog, "metryka": "srednia char_f2 dokumentow dev (wszystkie jezyki)", "siatka": list(f2),
        "f2": {f"{p:.2f}": round(v, 6) for p, v in f2.items()}, "liczba_dokumentow": liczba_dokumentow,
        "data": datetime.now(timezone.utc).isoformat(timespec="seconds"), "commit_sedziego": commit_sedziego(),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return cel


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pbench-kalibruj", description="Kalibruje próg uczestnika grupy A na dev (max char-F2).")
    ap.add_argument("--uczestnik", required=True)
    ap.add_argument("--wyniki", type=Path, default=KORZEN / "wyniki", help="katalog wyników (surowe/<id>/dev/tekst.jsonl)")
    ap.add_argument("--zapisz", action="store_true", help="zapisz uczestnicy/<id>/prog.json")
    ap.add_argument("--korpus", type=Path, default=KORZEN / "korpus")
    ap.add_argument("--uczestnicy", type=Path, default=KORZEN / "uczestnicy")
    ap.add_argument("--reguly", type=Path, default=ocen.REGULY_DOMYSLNE)
    ap.add_argument("--procesy", type=int, help="liczba procesów oceny (domyślnie min(8, CPU))")
    a = ap.parse_args(argv)
    k = krzywa(a.wyniki / "surowe" / a.uczestnik / "dev", SIATKA, korpus=a.korpus, reguly=a.reguly, procesy=a.procesy)
    if k is None:
        print(f"{a.uczestnik}: brak wyniku pewności (jeden wynik we wszystkich wykryciach) – bez kalibracji, prog.json nie powstaje.")
        return 0
    f2, n = k
    prog = wybierz_prog(f2)
    for p, v in f2.items():
        print(f"  {p:.2f}  F2 {v:.4f}{'  <-' if p == prog else ''}")
    print(f"{a.uczestnik}: próg {prog:.2f} (dokumentów dev: {n})")
    if a.zapisz:
        print("zapisano", zapisz_prog(a.uczestnicy / a.uczestnik, prog, f2, n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
