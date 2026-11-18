"""Uczestnik `gliner-knowledgator-pii`: samodzielny GLiNER `knowledgator/gliner-pii-large-v1.0` (Knowledgator + Wordcab).

Konfiguracja wg karty modelu: `predict_entities(tekst, etykiety, threshold=0.3)` z nazwami typów z jej list PII (60+ predefiniowanych
kategorii, zero-shot dla pozostałych). Okna tokenowe GLiNER z zakładką 20%, scalanie offsetów znakowych (`../_wspolne/okna.py`).
Szczegóły, wybór wariantu modelu i uzasadnienie: KONFIG.md."""
from __future__ import annotations

import sys
from pathlib import Path

KATALOG = Path(__file__).resolve().parent
sys.path.insert(0, str(KATALOG.parent / "_wspolne"))

import gliner_wspolne as gw  # noqa: E402
import protokol_uczestnika as pu  # noqa: E402

MODEL = "knowledgator/gliner-pii-large-v1.0"
REWIZJA = "f847f54fbc97ad6e78bfa20ed9c5e5d5c43327b9"
# Szkielet microsoft/deberta-v3-large: tokenizer w repozytorium modelu, konfiguracja kodera w `gliner_config.json` (encoder_config).
MAX_LEN = 768                       # `max_len` z gliner_config.json (słowa wg splittera GLiNER)
# Okno 384 tokenów = połowa limitu: koszt CPU rośnie kwadratowo z długością, a model trenowano na krótkich rekordach;
# zapas na cofnięcie krawędzi do granicy słowa mieści się z dużym marginesem.
LIMIT_OKNA = 384
PROG_DOMYSLNY = 0.30                # karta: „Recommended starting point for production: threshold=0.3”

# Typy z list kategorii na karcie (personal / contact / financial / healthcare / id) plus naturalne nazwy zero-shot dla
# kategorii gold, których karta nie wymienia (iban, national id number, tax identification number, identity card number,
# registration number, organization, date). 30 = `max_types` modelu (jeden przebieg na okno).
ETYKIETY = [
    "name", "organization", "dob", "date", "email address", "phone number", "ip address", "url",
    "location address", "location street", "location city", "location state", "location country", "location zip",
    "iban", "bank account", "credit card", "money", "ssn", "national id number", "tax identification number",
    "passport number", "identity card number", "driver license", "vehicle id", "registration number",
    "username", "password", "healthcare number", "condition",
]


def main() -> None:
    pu.ustaw_watki()
    sciezka = gw.pobierz(MODEL, REWIZJA)
    model = gw.zaladuj(sciezka)
    assert len(ETYKIETY) <= model.config.max_types
    wersje = {"gliner": gw.wersja("gliner"), "torch": gw.wersja("torch"), "transformers": gw.wersja("transformers"),
              "hf:gliner": f"{MODEL}@{REWIZJA}"}
    gw.main(model=model, etykiety=[ETYKIETY], prog_domyslny=PROG_DOMYSLNY, katalog=KATALOG,
            max_tokenow=gw.limit_okna(MAX_LEN, LIMIT_OKNA), wersje=wersje)


if __name__ == "__main__":
    main()
