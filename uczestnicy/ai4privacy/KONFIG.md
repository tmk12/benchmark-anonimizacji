# ai4privacy

Model PII **ai4privacy** `ai4privacy/llama-ai4privacy-multilingual-categorical-anonymiser-openpii` (ModernBERT-base dotrenowany na
zbiorze `ai4privacy/open-pii-masking-500k-ai4privacy`; 20 typów PII, BIO), uruchamiany standardowym potokiem `transformers`.
Grupa B (bez kalibracji). Poziom: tylko **tekst**.

## Wersje (przypięte, `uv.lock` w repo)

| Składnik | Wersja / rewizja | Licencja |
|---|---|---|
| torch (CPU) / transformers | 2.15.0+cpu / 4.57.6 | BSD-3 / Apache-2.0 |
| `ai4privacy/llama-ai4privacy-multilingual-categorical-anonymiser-openpii` | rewizja HF `83ef30d5e7c9d113ad80ce745b564cdd2320c5d5`, `model.safetensors` sha256 `400b96e14b636df9ee6305e37e7986095e40d0e1840f3c1a907584986fa66c0c` (599 MB) | MIT (karta i tag repozytorium) |

Repozytorium oficjalne (organizacja `ai4privacy` na HF, bez bramki). Pobrane tylko `*.json` i `model.safetensors` (bez wariantów ONNX)
do `vendor/hf` (suma zgodna z LFS oid HF), potem offline.

## Dlaczego model, a nie pakiet `ai4privacy` z PyPI

Autorzy publikują też pakiet `ai4privacy` (PyPI 0.5.0, `protect()`/`observe()`), który ładuje ten sam model (`classify_pii=True`;
`multilingual=True` – wariant bez kategorii; domyślnie – model angielski) i dekoduje wyniki własnym, 9-krokowym przetwarzaniem
(okna 512/256, „anti-O bias”, poprawki B/I, rozszerzanie do granic słów…). **Pakietu nie używamy:** jego plik `LICENSE` brzmi
„Copyright (c) 2025 Michael Anthony. All rights reserved.” (brak licencji otwartej; repozytorium z metadanych PyPI,
`github.com/MikeDoes/ai4privacy`, nie istnieje publicznie – 404, sprawdzone 2026-11-01). Kodu pakietu nie kopiujemy ani nie
odtwarzamy. Model ma licencję MIT, więc uruchamiamy go tak, jak karta wskazuje (`library_name: transformers`,
`token-classification`; karta nie podaje kodu użycia): `pipeline("token-classification", aggregation_strategy="simple")` –
agregacja domyślna widżetu i API inferencji HF.

Licencja zbioru treningowego (`ai4privacy/open-pii-masking-500k-ai4privacy`, sprawdzone 2026-11-01): CC-BY-4.0 (karta zbioru:
`license: other`, `license_name: cc-by-4.0`).

**Konsekwencja (do adnotacji w raporcie):** bez dekodowania pakietu model wykrywa słabiej – np. w „Please contact John Smith by email
john.smith@example.com…” e-mail jest wykryty tylko we fragmencie („.smith”), bo większość jego tokenów ma najwyższe
prawdopodobieństwo „O”. Wynik tego uczestnika mierzy **model ai4privacy w standardowym potoku transformers**, nie produkt/pakiet
ai4privacy.

## Konfiguracja

* Model kategorii (`…-categorical-…`) – wielojęzyczny i z typami (potrzebne do `etykiety.json`); to wariant, który pakiet wybiera
  dla `classify_pii=True`.
* Okna tokenowe jak okno pakietu (README pakietu: „Sliding window (512/256 stride)”): limit 512 tokenów minus 40 zapasu
  (`PBENCH_OKNO_TOKENOW`), zakładka 12%, scalanie offsetów (`../_wspolne/okna.py`), odrzucanie wykryć na sztucznej krawędzi.
* Próg: domyślny `score_threshold` pakietu to 0.01 (podłoga protokołu 0.05; `prog.json`/`PBENCH_SUROWE=1` jak w grupie A). Wynik =
  średnia pewność tokenów encji (`simple`).
* Offsety z potoku mogą obejmować wiodącą spację (tokenizer BPE ModernBERT) – sędzia liczy pokrycie znaków, spacja nie szkodzi.

## Etykiety → kategorie gold (`etykiety.json`)

GIVENNAME, SURNAME → OSOBA; CITY → MIEJSCOWOSC, MIEJSCE_UR; STREET, BUILDINGNUM → ADRES; ZIPCODE → KOD_POCZTOWY; DATE → DATA,
DATA_UR; EMAIL → EMAIL; TELEPHONENUM → TELEFON; CREDITCARDNUMBER → KARTA; SOCIALNUM → PESEL, SSN, NINO, NUSS, SVNR, NIR;
IDCARDNUM → DOWOD, DNI, NR_ID; PASSPORTNUM → PASZPORT; DRIVERLICENSENUM → PRAWO_JAZDY; TAXNUM → NIP, NR_PODATKOWY, EIN. Bez
odpowiednika w gold (zwracane, ale poza zakresem): TITLE, SEX, GENDER, AGE, TIME. Model wielojęzyczny – te same etykiety w każdym
języku (`metodyka/zakres-gold.md` pkt 4).

## Języki

Uruchamiany na 5 językach (R37). Oficjalnie (karta): **en, es, de, fr** (oraz it, nl, hi, te – poza korpusem); polskiego brak.
