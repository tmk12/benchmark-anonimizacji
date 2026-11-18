"""Uczestnik `presidio-spacy`: Microsoft Presidio Analyzer + spaCy (`*_core_news_lg`/`en_core_web_lg`), poziom tekst.

Konfiguracja i uzasadnienie: KONFIG.md. Okna znakowe (limit spaCy `max_length` = 1 mln znaków; okno 50 tys. ogranicza
pamięć) z zakładką 10% i scalaniem offsetów (`../_wspolne/okna.py`)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

KATALOG = Path(__file__).resolve().parent
sys.path.insert(0, str(KATALOG.parent / "_wspolne"))

import okna  # noqa: E402
import presidio_wspolne as pw  # noqa: E402
import protokol_uczestnika as pu  # noqa: E402
from presidio_analyzer.nlp_engine import NlpEngineProvider  # noqa: E402

MODELE = {"pl": "pl_core_news_lg", "en": "en_core_web_lg", "es": "es_core_news_lg", "de": "de_core_news_lg",
          "fr": "fr_core_news_lg"}
ROZMIAR_OKNA = int(os.environ.get("PBENCH_OKNO_ZNAKI", "50000"))
PROG_DOMYSLNY = 0.0                         # `default_score_threshold: 0` w konfiguracji autorów (default_analyzer.yaml)

# Etykiety modeli spaCy → encje Presidio. Baza: spacy_multilingual.yaml autorów; dopisane etykiety NKJP modelu polskiego
# (persName/placeName/geogName/orgName/date/time), których domyślne mapowanie nie zna, oraz MISC (niemapowane: ignorowane).
MAPOWANIE_NER = {
    "PER": "PERSON", "PERSON": "PERSON", "persName": "PERSON",
    "NORP": "NRP", "FAC": "LOCATION", "LOC": "LOCATION", "LOCATION": "LOCATION", "GPE": "LOCATION",
    "placeName": "LOCATION", "geogName": "LOCATION",
    "ORG": "ORGANIZATION", "ORGANIZATION": "ORGANIZATION", "orgName": "ORGANIZATION",
    "DATE": "DATE_TIME", "TIME": "DATE_TIME", "date": "DATE_TIME", "time": "DATE_TIME",
}


def zbuduj():
    konf = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": j, "model_name": m} for j, m in MODELE.items()],
        "ner_model_configuration": {
            "model_to_presidio_entity_mapping": MAPOWANIE_NER,
            "low_confidence_score_multiplier": 0.4,
            "low_score_entity_names": ["ORG", "ORGANIZATION", "orgName"],
            "labels_to_ignore": [],
        },
    }
    nlp = NlpEngineProvider(nlp_configuration=konf).create_engine()
    return pw.zbuduj_analizator(nlp)


def main() -> None:
    pu.ustaw_watki()
    analizator = zbuduj()
    prog = pu.wczytaj_prog(KATALOG, PROG_DOMYSLNY)

    def analizuj(tekst: str, jezyk: str) -> list:
        def okno(podtekst: str):
            return pw.tlumacz_wyniki(analizator.analyze(text=podtekst, language=jezyk))
        wyk = okna.analizuj_oknami(tekst, okna.okna_znakowe(tekst, ROZMIAR_OKNA), okno)
        return [w for w in wyk if w[3] >= prog]

    wersje = {"presidio-analyzer": pw.wersja("presidio-analyzer"), "spacy": pw.wersja("spacy"),
              **{m: pw.wersja(m.replace("_", "-")) for m in MODELE.values()}}
    pu.petla(wersje, analizuj)


if __name__ == "__main__":
    main()
