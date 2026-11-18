"""Uczestnik `flair`: Flair `SequenceTagger` z modelem `flair/ner-multi` (ogólny NER: PER, LOC, ORG, MISC), poziom tekst.

Jak w karcie modelu i samouczku Flair („How to tag a whole corpus”): tekst dzielony na zdania `SegtokSentenceSplitter`,
`tagger.predict(zdania)`, spany `ner` z pozycją znakową zdania w tekście (`Sentence.start_position`). Model to LSTM-CRF na
osadzeniach znakowych Flair – bez limitu tokenów, więc bez okien. Zwracamy PER, LOC, ORG (MISC – „inne nazwy” – pomijamy, jak
`labels_to_ignore` w Presidio). Konfiguracja i uzasadnienie: KONFIG.md."""
from __future__ import annotations

import sys
from importlib import metadata
from pathlib import Path

KATALOG = Path(__file__).resolve().parent
sys.path.insert(0, str(KATALOG.parent / "_wspolne"))

import protokol_uczestnika as pu  # noqa: E402

MODEL = "flair/ner-multi"
REWIZJA = "efbff7533ea394ebf7c0b4877ad13b8e42a76922"
SHA256_WAG = "9e73a46f5156d8602bde5c1d0d60e658e0dc00339949ca3dfcada6188f28678c"   # pytorch_model.bin (LFS oid)
ETYKIETY = ("PER", "LOC", "ORG")
PROG_DOMYSLNY = 0.0                          # Flair nie filtruje spanów progiem (podłoga protokołu: 0.05)


def main() -> None:
    pu.ustaw_watki()
    from flair.models import SequenceTagger
    from flair.splitter import SegtokSentenceSplitter
    from huggingface_hub import snapshot_download

    sciezka = Path(snapshot_download(MODEL, revision=REWIZJA, allow_patterns=["pytorch_model.bin"]))
    tagger = SequenceTagger.load(str(sciezka / "pytorch_model.bin"))
    dzielnik = SegtokSentenceSplitter()
    prog = pu.wczytaj_prog(KATALOG, PROG_DOMYSLNY)

    def analizuj(tekst: str, jezyk: str) -> list:
        if not tekst.strip():
            return []
        zdania = dzielnik.split(tekst)
        tagger.predict(zdania)
        wyniki = []
        for zdanie in zdania:
            for span in zdanie.get_spans("ner"):
                if span.tag in ETYKIETY and span.score >= prog:
                    s = zdanie.start_position + span.start_position
                    wyniki.append((s, zdanie.start_position + span.end_position, span.tag, float(span.score)))
        return sorted(wyniki)

    wersje = {"flair": metadata.version("flair"), "torch": metadata.version("torch"), "model": f"{MODEL}@{REWIZJA}",
              "model_pytorch_model_bin_sha256": SHA256_WAG}
    pu.petla(wersje, analizuj)


if __name__ == "__main__":
    main()
