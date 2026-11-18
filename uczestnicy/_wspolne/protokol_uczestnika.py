"""Wspólna pętla protokołu JSONL uczestnika (stdin → stdout), próg z `prog.json`, tryb surowy do kalibracji.

Uczestnik nie zależy od pakietu `pbench`: protokół jest trywialny (linia `gotowy` z wersjami, potem odpowiedź na każdą
linię zapytania), a ten moduł jest wspólną, minimalną kopią jego strony uczestnika."""
from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path
from typing import Callable

PODLOGA = 0.05                  # dolne ograniczenie progu domyślnego autorów (bez `prog.json`): poniżej niego nic nie zwraca
PODLOGA_SUROWA = 0.01           # najniższy próg siatki kalibracji = próg trybu surowego; `prog.json` 0,01–0,04 jest respektowany


def wczytaj_prog(katalog: Path, domyslny: float) -> float:
    """Próg z `<katalog>/prog.json` (`{"prog": 0.4}`); brak pliku → domyślny autorów. `PBENCH_SUROWE=1` → podłoga surowa.
    `prog.json` nie jest obcinany do `PODLOGA` (kalibracja może wybrać 0,01–0,04); domyślny autorów – tak (jak dotąd)."""
    if os.environ.get("PBENCH_SUROWE") == "1":
        return PODLOGA_SUROWA
    p = Path(katalog) / "prog.json"
    if p.exists():
        return max(PODLOGA_SUROWA, float(json.loads(p.read_text(encoding="utf-8"))["prog"]))
    return max(PODLOGA, domyslny)


def ustaw_watki() -> None:
    """Liczba wątków torch z `OMP_NUM_THREADS` (ustawia ją orkiestrator)."""
    try:
        import torch
    except ImportError:                      # uczestnik bez torcha (spaCy/thinc czyta OMP_NUM_THREADS sam)
        return
    torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", "1")))


_WYJSCIE = sys.stdout
sys.stdout = sys.stderr                      # zabłąkane print()-y bibliotek nie psują protokołu na stdout


def _wyslij(obj: dict) -> None:
    _WYJSCIE.write(json.dumps(obj, ensure_ascii=False) + "\n")
    _WYJSCIE.flush()


def petla(wersje: dict[str, str], analizuj: Callable[[str, str], list]) -> None:
    """`analizuj(tekst, jezyk)` → lista `[start, koniec, etykieta, wynik]`. Wyjątek → odpowiedź `blad` (bez treści dokumentu)."""
    _wyslij({"gotowy": True, "wersje": wersje})
    for linia in sys.stdin:
        if not linia.strip():
            continue
        zad = json.loads(linia)
        try:
            if "tekst" not in zad:
                raise ValueError("uczestnik obsługuje tylko poziom tekst")
            _wyslij({"id": zad["id"], "wykrycia": [list(w) for w in analizuj(zad["tekst"], zad["jezyk"])]})
        except Exception as e:                                    # noqa: BLE001 – błąd dokumentu nie zabija procesu
            traceback.print_exc(file=sys.stderr)
            _wyslij({"id": zad["id"], "blad": f"{type(e).__name__}: {str(e)[:300]}"})
