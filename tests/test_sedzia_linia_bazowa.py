"""Linia bazowa sędziego plikowego: kopia oryginału wycieka 100 % ocenianych wartości (mianownik symetryczny).

Wymaga wygenerowanego korpusu (`korpus/`, poza gitem) i danych Tesseracta; bez nich testy są pomijane."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pbench import ocr
from pbench.sedzia.plik import leksykon_z_manifestu, ocen_plik
from pbench.sedzia.sanity import wartosci_wpisu
from pbench.sedzia.tekst import RegulyWycieku

KORPUS = Path(__file__).resolve().parent.parent / "korpus"
MANIFEST = KORPUS / "manifest.jsonl"

pytestmark = [
    pytest.mark.filterwarnings("ignore"),
    pytest.mark.skipif(not MANIFEST.exists(), reason="brak wygenerowanego korpusu"),
    pytest.mark.skipif(not all(ocr.dostepny(j) for j in ("pl", "en", "es", "de", "fr")) if MANIFEST.exists() else True,
                       reason="brak danych Tesseracta"),
]


def _proba() -> list[dict]:
    """Stała próba: wszystkie skany dev + co 6. pozostały dokument dev (≥ 30 dokumentów, wszystkie formaty)."""
    dev = [json.loads(l) for l in MANIFEST.read_text(encoding="utf-8").splitlines() if l.strip()]
    dev = [w for w in dev if w["split"] == "dev"]
    skany = [w for w in dev if w["format"] == "skan"]
    reszta = [w for w in dev if w["format"] != "skan"][::6]
    return skany + reszta


PROBA = _proba() if MANIFEST.exists() else []


def test_proba_ma_co_najmniej_30_dokumentow_i_wszystkie_skany():
    assert len(PROBA) >= 30
    assert sum(1 for w in PROBA if w["format"] == "skan") >= 10


@pytest.mark.parametrize("wpis", PROBA, ids=[w["id"] for w in PROBA])
def test_kopia_oryginalu_wycieka_wszystkie_oceniane_wartosci(wpis, monkeypatch, tmp_path_factory):
    monkeypatch.setenv("PBENCH_OCR_CACHE", str(KORPUS.parent / ".cache" / "ocr"))
    o = ocen_plik(KORPUS / wpis["plik"], KORPUS / wpis["plik"], wartosci_wpisu(wpis), RegulyWycieku(),
                  leksykon=leksykon_z_manifestu(MANIFEST))
    assert o.status == "OK"
    assert len(o.wycieki) == o.wartosci_ocenione > 0
