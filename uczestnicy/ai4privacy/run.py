"""Uczestnik `ai4privacy`: model PII ai4privacy (ModernBERT-base, wielojęzyczny, z kategoriami) przez `transformers`, poziom tekst.

Model `ai4privacy/llama-ai4privacy-multilingual-categorical-anonymiser-openpii` (MIT, rewizja przypięta) uruchamiany
standardowym potokiem `token-classification` biblioteki transformers (`aggregation_strategy="simple"` – jak w widżecie i API
inferencji HF). Pakietu `ai4privacy` z PyPI (własne dekodowanie BIO) NIE używamy: jego plik LICENSE to „All rights reserved”
(brak licencji otwartej) – zob. KONFIG.md. Okna tokenowe 512 (jak okno pakietu) z zakładką 12% i scalaniem offsetów
(`../_wspolne/okna.py`). Konfiguracja i uzasadnienie: KONFIG.md."""
from __future__ import annotations

import os
import sys
from importlib import metadata
from pathlib import Path

KATALOG = Path(__file__).resolve().parent
sys.path.insert(0, str(KATALOG.parent / "_wspolne"))

import okna  # noqa: E402
import protokol_uczestnika as pu  # noqa: E402

MODEL = "ai4privacy/llama-ai4privacy-multilingual-categorical-anonymiser-openpii"
REWIZJA = "83ef30d5e7c9d113ad80ce745b564cdd2320c5d5"
SHA256_WAG = "400b96e14b636df9ee6305e37e7986095e40d0e1840f3c1a907584986fa66c0c"   # model.safetensors (LFS oid)
LIMIT_TOKENOW = 512                          # okno pakietu autorów (README: „Sliding window (512/256 stride)”)
ZAPAS_TOKENOW = 40                           # tokeny specjalne + różnice retokenizacji podłańcucha
MAX_TOKENOW = int(os.environ.get("PBENCH_OKNO_TOKENOW", LIMIT_TOKENOW - ZAPAS_TOKENOW))
PROG_DOMYSLNY = 0.01                         # `score_threshold` domyślny pakietu (podłoga protokołu: 0.05)


def main() -> None:
    pu.ustaw_watki()
    from huggingface_hub import snapshot_download
    from transformers import pipeline

    sciezka = snapshot_download(MODEL, revision=REWIZJA, allow_patterns=["*.json", "model.safetensors"])
    potok = pipeline("token-classification", model=sciezka, aggregation_strategy="simple", device=-1)
    prog = pu.wczytaj_prog(KATALOG, PROG_DOMYSLNY)

    def okno(podtekst: str):
        return [(int(e["start"]), int(e["end"]), e["entity_group"], float(e["score"]))
                for e in potok(podtekst) if e["end"] > e["start"]]

    def analizuj(tekst: str, jezyk: str) -> list:
        if not tekst.strip():
            return []
        wyk = okna.analizuj_oknami(tekst, okna.okna_tokenowe(tekst, potok.tokenizer, MAX_TOKENOW), okno)
        return [w for w in wyk if w[3] >= prog]

    wersje = {"transformers": metadata.version("transformers"), "torch": metadata.version("torch"),
              "model": f"{MODEL}@{REWIZJA}", "model_safetensors_sha256": SHA256_WAG, "agregacja": "simple"}
    pu.petla(wersje, analizuj)


if __name__ == "__main__":
    main()
