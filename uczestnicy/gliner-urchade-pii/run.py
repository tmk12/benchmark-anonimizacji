"""Uczestnik `gliner-urchade-pii`: samodzielny GLiNER `urchade/gliner_multi_pii-v1` (bez Presidio), etykiety PII jawnie.

Konfiguracja wg karty modelu: `predict_entities(tekst, etykiety, threshold=...)` z nazwami typów z listy karty (angielskie
nazwy naturalne). Okna tokenowe GLiNER (`max_len` 384) z zakładką 20%, scalanie offsetów znakowych (`../_wspolne/okna.py`).
Szczegóły i uzasadnienie: KONFIG.md."""
from __future__ import annotations

import sys
from pathlib import Path

KATALOG = Path(__file__).resolve().parent
sys.path.insert(0, str(KATALOG.parent / "_wspolne"))

import gliner_wspolne as gw  # noqa: E402
import protokol_uczestnika as pu  # noqa: E402

MODEL = "urchade/gliner_multi_pii-v1"
REWIZJA = "1fcf13e85f4eef5394e1fcd406cf2ca9ea82351d"
# Szkielet (mdeberta-v3-base): `gliner_config.json` nie zawiera konfiguracji kodera ani tokenizera – biblioteka ładuje je po nazwie.
SZKIELET = "microsoft/mdeberta-v3-base@a0484667b22365f84929a935b5e50a51f71f159d"
MAX_LEN = 384                       # `max_len` z gliner_config.json (słowa/znaki interpunkcji wg splittera GLiNER)
LIMIT_OKNA = 320
PROG_DOMYSLNY = 0.50                # `threshold` domyślny `predict_entities` i metody `GLiNER` (karta modelu nie podaje innego)

# Typy z listy karty modelu (≤ 25 = `max_types`), pokrywające kategorie gold; ta sama lista co w `presidio-gliner`.
ETYKIETY = [
    "person", "organization", "address", "postal code", "date of birth", "email", "phone number", "ip address", "iban",
    "bank account number", "credit card number", "passport number", "identity card number", "national id number",
    "social security number", "tax identification number", "driver's license number", "license plate number",
    "registration number", "health insurance number", "medical condition", "username",
]


def main() -> None:
    pu.ustaw_watki()
    sciezka = gw.pobierz(MODEL, REWIZJA, (SZKIELET,))
    model = gw.zaladuj(sciezka)
    assert len(ETYKIETY) <= model.config.max_types
    wersje = {"gliner": gw.wersja("gliner"), "torch": gw.wersja("torch"), "transformers": gw.wersja("transformers"),
              "hf:gliner": f"{MODEL}@{REWIZJA}", "hf:szkielet": SZKIELET}
    gw.main(model=model, etykiety=[ETYKIETY], prog_domyslny=PROG_DOMYSLNY, katalog=KATALOG,
            max_tokenow=gw.limit_okna(MAX_LEN, LIMIT_OKNA), wersje=wersje)


if __name__ == "__main__":
    main()
