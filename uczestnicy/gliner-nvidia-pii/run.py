"""Uczestnik `gliner-nvidia-pii`: samodzielny GLiNER `nvidia/gliner-PII` (NVIDIA, na bazie urchade/gliner_large-v2.1).

Konfiguracja wg karty modelu: `predict_entities(tekst, etykiety, threshold=0.3)` (próg ewaluacji autorów) z nazwami typów
zbioru treningowego Nemotron-PII (snake_case, np. `phone_number`, `user_name`). Okna tokenowe GLiNER (`max_len` 384)
z zakładką 20%, scalanie offsetów znakowych (`../_wspolne/okna.py`). Szczegóły i uzasadnienie: KONFIG.md."""
from __future__ import annotations

import sys
from pathlib import Path

KATALOG = Path(__file__).resolve().parent
sys.path.insert(0, str(KATALOG.parent / "_wspolne"))

import gliner_wspolne as gw  # noqa: E402
import protokol_uczestnika as pu  # noqa: E402

MODEL = "nvidia/gliner-PII"
REWIZJA = "bd23e8ef4425fd04e34c5204ab49ffaa706eae79"
MAX_LEN = 384                       # `max_len` z gliner_config.json
LIMIT_OKNA = 320
PROG_DOMYSLNY = 0.30                # karta: „We evaluated the model using threshold=0.3”

# Typy zbioru treningowego Nemotron-PII (nvidia/Nemotron-PII, 54 różne etykiety w próbce 1500 rekordów testu) istotne dla
# kategorii gold, w dwóch grupach po ≤ 25 (`max_types` modelu: trenowano z ≤ 25 typami w przebiegu; grupy = osobne przebiegi).
ETYKIETY = [
    ["first_name", "last_name", "company_name", "street_address", "city", "county", "state", "country", "postcode",
     "email", "phone_number", "fax_number", "date_of_birth", "date", "url", "ipv4", "ipv6", "mac_address", "user_name"],
    ["ssn", "tax_id", "account_number", "bank_routing_number", "swift_bic", "credit_debit_card", "password",
     "license_plate", "vehicle_identifier", "medical_record_number", "health_plan_beneficiary_number",
     "certificate_license_number", "customer_id", "employee_id", "unique_id", "device_identifier", "api_key", "pin",
     "blood_type"],
]


def main() -> None:
    pu.ustaw_watki()
    sciezka = gw.pobierz(MODEL, REWIZJA)
    model = gw.zaladuj(sciezka)
    assert all(len(g) <= model.config.max_types for g in ETYKIETY)
    wersje = {"gliner": gw.wersja("gliner"), "torch": gw.wersja("torch"), "transformers": gw.wersja("transformers"),
              "hf:gliner": f"{MODEL}@{REWIZJA}"}
    gw.main(model=model, etykiety=ETYKIETY, flat_ner=False,   # powód: KONFIG.md (flat_ner=True gubi całe e-maile)
             prog_domyslny=PROG_DOMYSLNY, katalog=KATALOG,
            max_tokenow=gw.limit_okna(MAX_LEN, LIMIT_OKNA), wersje=wersje)


if __name__ == "__main__":
    main()
