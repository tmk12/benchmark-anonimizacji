# gliner-nvidia-pii

Samodzielny GLiNER `nvidia/gliner-PII` (NVIDIA; na bazie `urchade/gliner_large-v2.1`, szkielet deberta-v3-large). Poziom: tylko **tekst**.

## Wersje (przypięte, `uv.lock` w repo)

| Składnik | Wersja / rewizja | Licencja |
|---|---|---|
| gliner | 0.2.29 | Apache-2.0 |
| torch (CPU) / transformers | 2.15.0+cpu / 4.57.6 | BSD-3 / Apache-2.0 |
| `nvidia/gliner-PII` | rewizja HF `bd23e8ef4425fd04e34c5204ab49ffaa706eae79`, `pytorch_model.bin` sha256 `a4dfd0dcbd718acc86dca65fa99f1097d2796c8d7a681e1bc42f40f946c03802` (1,78 GB) | NVIDIA Open Model License |

**Licencja (przeczytana przez kontrolera 2026-10-30):** NVIDIA Open Model License
(<https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/>); karta: „ready for commercial/non-commercial use”.
Ustalenia: lokalne użycie i użycie komercyjne dozwolone, **publikowanie wyników nie jest ograniczone**; znaki towarowe NVIDIA
tylko do opisania pochodzenia modelu; informacja licencyjna (notice) wymagana dopiero przy **dystrybucji** modelu – my go nie
redystrybuujemy (wagi tylko w `vendor/hf`, poza gitem). Brak zakazu ewaluacji/benchmarku; zakaz obchodzenia „Guardrail” nie dotyczy
(brak zabezpieczeń do obejścia). Repozytorium oficjalne (organizacja `nvidia`, bez bramki).

## Źródło „najlepszej konfiguracji”

Karta: <https://huggingface.co/nvidia/gliner-PII> – `predict_entities(tekst, etykiety, threshold=…)`; autorzy „evaluated the model using
threshold=0.3” (przykład w karcie: 0.5) → domyślny **0.30**. Etykiety: nazwy typów zbioru treningowego
[Nemotron-PII](https://huggingface.co/datasets/nvidia/Nemotron-PII) (snake_case: `phone_number`, `user_name`…); lista 54 różnych etykiet
odczytana z 1500 rekordów podziału test. `gliner_config.json`: `max_len` 384, `max_types` 25, `words_splitter_type: whitespace`.
**Polityka `flat_ner`:** jedyny uczestnik GLiNER z `flat_ner=False` (odstępstwo od domyślnej karty/biblioteki). Powód zmierzony: przy `flat_ner=True` dla „john.smith@example.com” model zwraca
tylko `first_name`/`last_name` (wynik 1.0 każdy) i gubi resztę adresu, bo remis z całym `email` (1.0) wygrywają krótsze spany;
z `flat_ner=False` zwracany jest też cały `email`. Model pytany z progiem 0.05, filtr progu po scaleniu okien.

## Etykiety (2 grupy po ≤ 25 = `max_types`; każda grupa = osobny przebieg na oknie, wyniki sumowane)

Model trenowano z ≤ 25 typami w przebiegu, więc 38 istotnych etykiet dzielimy na dwie grupy (19 + 19) zamiast jednego promptu
z 38 typami. Pominięte jako bez odpowiednika w gold: `age`, `gender`, `occupation`, `education_level`, `language`, `political_view`,
`race_ethnicity`, `religious_belief`, `sexuality`, `employment_status`, `coordinate`, `time`, `date_time`, `http_cookie`, `biometric_identifier`.
Mapowanie w `etykiety.json` (miara pomocnicza; żadne wykrycie nie jest odrzucane).

| Grupa | Etykiety → kategorie gold |
|---|---|
| 1 | first_name, last_name → OSOBA; company_name → ORGANIZACJA; street_address → ADRES; city → MIEJSCOWOSC, MIEJSCE_UR; county, state → REGION; country → KRAJ; postcode → KOD_POCZTOWY; email → EMAIL; phone_number, fax_number → TELEFON; date_of_birth → DATA_UR; date → DATA; url → URL; ipv4, ipv6 → IP; mac_address → MAC; user_name → LOGIN |
| 2 | ssn → SSN, SVNR, NUSS, NINO, NIR; tax_id → NIP, NR_PODATKOWY, VAT, CIF, EIN, SIREN; account_number, bank_routing_number, swift_bic → RACHUNEK; credit_debit_card → KARTA; password, api_key, pin → SEKRET; license_plate, vehicle_identifier → NR_REJESTRACYJNY; medical_record_number, device_identifier → IDENTYFIKATOR; health_plan_beneficiary_number → KVNR, MBI, NHS; certificate_license_number → IDENTYFIKATOR, NR_ID; customer_id, employee_id, unique_id → IDENTYFIKATOR; blood_type → ZDROWIE |

Imię i nazwisko model zwraca jako osobne spany (`first_name`, `last_name`); sędzia liczy pokrycie sumą spanów, więc to nie szkodzi.
Brak etykiet na paszport/dowód/PESEL (Nemotron-PII ich nie ma jako osobnych typów; `national_id` nie wystąpił w próbce) – to ograniczenie modelu.

## Języki

Oficjalnie: **en** (metadane karty: `language: [en]`; zbiór treningowy angielski, formaty US i międzynarodowe). Pozostałe 4 języki korpusu uruchamiane poza zakresem oficjalnym.

Ruling R37: uczestnik **uruchamiany jest na wszystkich 5 językach** (`jezyki`); `jezyki_oficjalne` w `uczestnik.toml` wskazuje języki oficjalnie obsługiwane wg karty/dokumentacji (sędzia: flaga `w_zakresie_oficjalnym`, miara „w zakresie oficjalnym”).

## Próg i wynik

Domyślny 0.30 (próg ewaluacji autorów). `prog.json` po kalibracji; `PBENCH_SUROWE=1` → 0.05. `wynik` = pewność GLiNER.

## Okna (długie teksty)

`max_len` 384 słów (splitter `whitespace` = `okna.TokenizerGliner`). Okno 320 tokenów (`PBENCH_OKNO_TOKENOW` do testów), zakładka 20%,
cięcia na białych znakach (cofnięcie krawędzi ≤ 32 tokeny < 384), odrzucanie wykryć dotykających sztucznej krawędzi, scalanie offsetów znakowych.
