"""Wspólne dla plikowych uczestników Presidio (grupa B): analizator w konfiguracji `presidio-pl-ner` i pętla protokołu plikowego.

Plikowi uczestnicy (`presidio-wrapper-plikowy`, `pdf-redactor`, `presidio-image-redactor`) wykrywają dane tym samym
analizatorem co uczestnik tekstowy `presidio-pl-ner` – kod konfiguracji (`zbuduj`, modele z `modele.json`, okna tokenowe,
próg z `presidio-pl-ner/prog.json`) jest ładowany wprost z `../presidio-pl-ner/run.py`, a nie kopiowany, więc obie
konfiguracje nie mogą się rozjechać. Projekt uv uczestnika plikowego musi mieć te same wersje zależności co
`presidio-pl-ner` (sprawdza to test)."""
from __future__ import annotations

import importlib.util
import json
import sys
import traceback
from pathlib import Path
from typing import Callable

import okna
import presidio_wspolne as pw
import protokol_uczestnika as pu

KATALOG_PL_NER = Path(__file__).resolve().parent.parent / "presidio-pl-ner"


def _modul_pl_ner():
    """`presidio-pl-ner/run.py` jako moduł (bez uruchamiania `main`)."""
    spec = importlib.util.spec_from_file_location("presidio_pl_ner_run", KATALOG_PL_NER / "run.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


class AnalizatorPlNer:
    """Analizator `presidio-pl-ner` (te same modele, rozpoznawacze, okna i próg) dla uczestników plikowych.

    `analizuj(tekst, jezyk)` → `[(start, koniec, encja Presidio, wynik)]`; `wyniki_presidio(...)` – to samo jako
    `RecognizerResult` (dla `presidio-anonymizer` i `presidio-image-redactor`)."""

    def __init__(self) -> None:
        from transformers import AutoTokenizer
        self.modul = _modul_pl_ner()
        self.analizator, sciezki = self.modul.zbuduj()
        self.tokenizery = {j: AutoTokenizer.from_pretrained(p) for j, p in sciezki.items()}
        self.prog = pu.wczytaj_prog(KATALOG_PL_NER, self.modul.PROG_DOMYSLNY)

    def analizuj(self, tekst: str, jezyk: str) -> list[tuple[int, int, str, float]]:
        if not tekst.strip():
            return []
        def okno(podtekst: str):
            return pw.tlumacz_wyniki(self.analizator.analyze(text=podtekst, language=jezyk))
        wyk = okna.analizuj_oknami(tekst, okna.okna_tokenowe(tekst, self.tokenizery[jezyk], self.modul.MAX_TOKENOW), okno)
        return [w for w in wyk if w[3] >= self.prog]

    def wyniki_presidio(self, tekst: str, jezyk: str) -> list:
        from presidio_analyzer import RecognizerResult
        return [RecognizerResult(etykieta, s, e, wynik) for s, e, etykieta, wynik in self.analizuj(tekst, jezyk)]

    def wersje(self) -> dict[str, str]:
        return {"presidio-analyzer": pw.wersja("presidio-analyzer"), "spacy": pw.wersja("spacy"),
                "transformers": pw.wersja("transformers"), "torch": pw.wersja("torch"),
                "konfiguracja": "presidio-pl-ner", "prog": str(self.prog),
                **{f"hf:{j}": "{}@{}".format(*self.modul._model(j)) for j in self.modul.JEZYKI}}


def petla_plikowa(wersje: dict[str, str], przetworz: Callable[[Path, Path, str], Path]) -> None:
    """Pętla protokołu dla poziomu plik: `przetworz(plik_wej, plik_wyj, jezyk)` → ścieżka faktycznie zapisanego pliku
    (R42: zgłaszamy rzeczywistą ścieżkę). Wyjątek → odpowiedź `blad` (bez treści dokumentu), proces żyje dalej."""
    pu._wyslij({"gotowy": True, "wersje": wersje})
    for linia in sys.stdin:
        if not linia.strip():
            continue
        zad = json.loads(linia)
        try:
            if "plik_wej" not in zad:
                raise ValueError("uczestnik obsługuje tylko poziom plik")
            zapisany = przetworz(Path(zad["plik_wej"]), Path(zad["plik_wyj"]), zad["jezyk"])
            pu._wyslij({"id": zad["id"], "plik_wyj": str(zapisany)})
        except Exception as e:                                    # noqa: BLE001 – błąd dokumentu nie zabija procesu
            traceback.print_exc(file=sys.stderr)
            pu._wyslij({"id": zad["id"], "blad": f"{type(e).__name__}: {str(e)[:300]}"})
