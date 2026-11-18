"""Uczestnik `stanza`: ogólny NER Stanza (Stanford NLP), pakiet `default_accurate`, 5 języków korpusu.

UWAGA: to bazowy NER ogólnego przeznaczenia (osoby, organizacje, miejsca, daty, kwoty), NIE detektor PII – nie wykrywa
e-maili, telefonów, numerów dokumentów ani adresów ulicznych. Jest punktem odniesienia „co daje zwykły NER”. Stanza nie
zwraca pewności spanów, więc `wynik` = 1.0 (próg nie ma wpływu). Szczegóły: KONFIG.md."""
from __future__ import annotations

import os
import sys
from importlib import metadata
from pathlib import Path

KATALOG = Path(__file__).resolve().parent
KORZEN = KATALOG.parent.parent
sys.path.insert(0, str(KATALOG.parent / "_wspolne"))

import herbert  # noqa: E402
import okna  # noqa: E402
import protokol_uczestnika as pu  # noqa: E402

STANZA_WERSJA = "1.15.0"                     # zasoby modeli: tag v1.15.0 repozytoriów stanfordnlp/stanza-<język> na HF
KATALOG_MODELI = str(KORZEN / "vendor" / "stanza")
JEZYKI = ("pl", "en", "es", "de", "fr")
# Pakiet autorów „default_accurate” (modele z transformerem tam, gdzie istnieją): en ontonotes-ww-multi_electra-large,
# es conll02, de germeval2014_german-nlp-electra, fr wikinergold_camembert-large. Dla polskiego pakiet wskazuje `nkjp` (bez BERT-a),
# ale Stanza publikuje oficjalnie także `nkjp_bert` (szkielet allegro/herbert-base-cased) – bierzemy lepszy: pozostałe procesory
# jak w `default_accurate` (tokenize pdb_charlm, mwt pdb).
PAKIET = "default_accurate"
PAKIET_PL = {"tokenize": "pdb_charlm", "mwt": "pdb", "ner": "nkjp_bert"}
ROZMIAR_OKNA = int(os.environ.get("PBENCH_OKNO_ZNAKI", "5000"))      # znaki; zakładka 10% (okna_znakowe) >> długość wartości
# Typy encji Stanza zbliżone do kategorii PII (reszta: NORP, PRODUCT, EVENT, LAW, LANGUAGE, TIME, PERCENT, QUANTITY, ORDINAL,
# CARDINAL, FAC, MISC/OTH oraz formy *deriv/*part GermEval – to nie są dane osobowe, ich zwracanie tylko zawyżałoby fałszywe trafienia).
TYPY_PII = {
    "PER": "PER", "PERSON": "PER", "persName": "PER",
    "ORG": "ORG", "ORGANIZATION": "ORG", "orgName": "ORG",
    "LOC": "LOC", "GPE": "LOC", "placeName": "LOC", "geogName": "LOC",
    "DATE": "DATE", "date": "DATE",
    "MONEY": "MONEY",
}


def _wersja(pakiet: str) -> str:
    try:
        return metadata.version(pakiet)
    except metadata.PackageNotFoundError:
        return "?"


def main() -> None:
    import stanza

    pu.ustaw_watki()
    potoki: dict[str, object] = {}

    def potok(jezyk: str):
        if jezyk not in potoki:                                 # wczytywane leniwie: tylko języki, które faktycznie przyjdą
            if jezyk == "pl":
                herbert.przypnij()                              # HerBERT w przypiętej rewizji albo jawny błąd (P13c-1)
            potoki[jezyk] = stanza.Pipeline(jezyk, dir=KATALOG_MODELI, processors="tokenize,mwt,ner", package=PAKIET_PL if jezyk == "pl" else PAKIET,
                                            download_method=None, use_gpu=False, verbose=False)
        if jezyk == "pl":
            herbert.potwierdz()
        return potoki[jezyk]

    def analizuj(tekst: str, jezyk: str) -> list:
        if jezyk not in JEZYKI:
            raise ValueError(f"język spoza listy: {jezyk}")
        nlp = potok(jezyk)

        def okno(podtekst: str) -> list:
            return [(e.start_char, e.end_char, TYPY_PII[e.type], 1.0) for e in nlp(podtekst).ents if e.type in TYPY_PII]

        return okna.analizuj_oknami(tekst, okna.okna_znakowe(tekst, ROZMIAR_OKNA), okno)

    wersje = {"stanza": _wersja("stanza"), "torch": _wersja("torch"), "transformers": _wersja("transformers"),
              "stanza:zasoby": f"v{STANZA_WERSJA}", "stanza:pakiet": PAKIET, "stanza:pl": "nkjp_bert",
              "hf:herbert": f"{herbert.MODEL}@{herbert.REWIZJA}"}
    pu.petla(wersje, analizuj)


if __name__ == "__main__":
    main()
