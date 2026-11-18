# gliner-urchade-pii

Samodzielny GLiNER `urchade/gliner_multi_pii-v1` (bez Presidio/spaCy). Poziom: tylko **tekst**.

## Wersje (przypięte, `uv.lock` w repo)

| Składnik | Wersja / rewizja | Licencja |
|---|---|---|
| gliner | 0.2.29 | Apache-2.0 |
| torch (CPU) / transformers | 2.15.0+cpu / 4.57.6 | BSD-3 / Apache-2.0 |
| `urchade/gliner_multi_pii-v1` | rewizja HF `1fcf13e85f4eef5394e1fcd406cf2ca9ea82351d`, `pytorch_model.bin` sha256 `3003753fba99e40645cf088c7367a2c6211fc174897dc64f1f9c147c29d18d2d` | Apache-2.0 |
| `microsoft/mdeberta-v3-base` (szkielet: tokenizer i konfiguracja kodera, ładowane po nazwie) | rewizja `a0484667b22365f84929a935b5e50a51f71f159d` | MIT |

Modele w `vendor/hf` (HF_HOME), potem `HF_HUB_OFFLINE=1`. Kod wspólny: `../_wspolne/gliner_wspolne.py`, `okna.py`, `protokol_uczestnika.py`.

## Źródło „najlepszej konfiguracji”

Karta modelu: <https://huggingface.co/urchade/gliner_multi_pii-v1> – `GLiNER.from_pretrained(...)` + `predict_entities(tekst, etykiety)`
z listą typów PII (angielskie nazwy naturalne) i domyślnym progiem biblioteki 0.5 (karta nie podaje innego). Model: fine-tuning
`urchade/gliner_multi-v2.1` na `urchade/synthetic-pii-ner-mistral-v1`. `max_len` = 384 słów, `max_types` = 25 (z `gliner_config.json`).

**Polityka `flat_ner`:** domyślna karty/biblioteki, `flat_ner=True` (jak `presidio-gliner`).
Model pytany z progiem 0.05 (podłoga siatki kalibracji), filtr progu po scaleniu okien.

## Etykiety (22 ≤ `max_types` 25, jeden przebieg na okno)

Typy z listy karty modelu pokrywające kategorie gold (ta sama lista, okno i `flat_ner` co w `presidio-gliner`; różnią się: warstwa Presidio
– rozpoznawacze wzorcowe/krajowe i spaCy – oraz próg domyślny: 0.50 tu, 0.30 w Presidio). Mapowanie na `KATEGORIE` w `etykiety.json` (miara pomocnicza; żadne wykrycie nie jest odrzucane).

| Etykieta GLiNER | Kategorie gold |
|---|---|
| person | OSOBA |
| organization | ORGANIZACJA |
| address | ADRES |
| postal code | KOD_POCZTOWY |
| date of birth | DATA_UR |
| email | EMAIL |
| phone number | TELEFON |
| ip address | IP |
| iban, bank account number | RACHUNEK |
| credit card number | KARTA |
| passport number | PASZPORT |
| identity card number | DOWOD |
| national id number | PESEL, DNI, NUSS, NIR |
| social security number | SSN, SVNR, NUSS, NINO, NIR |
| tax identification number | NIP, NR_PODATKOWY, VAT, CIF, EIN, SIREN |
| driver's license number | PRAWO_JAZDY |
| license plate number | NR_REJESTRACYJNY |
| registration number | NR_REJESTRU, KRS, REGON, NR_REJESTRACYJNY |
| health insurance number | KVNR, MBI, NHS |
| medical condition | ZDROWIE |
| username | LOGIN |

Bez odpowiednika w zestawie (nie dodawane, by nie przekroczyć 25): KWOTA, URL, MAC, UUID, SEKRET, SYGNATURA, INICJALY itd.

## Języki

Oficjalne (karta modelu): **en, fr, de, es, pt, it**; z języków korpusu: **en, fr, de, es** – **polskiego karta nie wymienia**, choć szkielet (mDeBERTa-v3) jest wielojęzyczny. PL jest uruchamiany jako test zero-shot poza zakresem oficjalnym.

Ruling R37: uczestnik **uruchamiany jest na wszystkich 5 językach** (`jezyki`); `jezyki_oficjalne` w `uczestnik.toml` wskazuje języki oficjalnie obsługiwane wg karty/dokumentacji (sędzia: flaga `w_zakresie_oficjalnym`, miara „w zakresie oficjalnym”).

## Próg i wynik

Domyślny: 0.50 (biblioteka/karta). `prog.json` (`{"prog": x}`) po kalibracji (zad. 16); `PBENCH_SUROWE=1` → 0.05.
`wynik` = pewność GLiNER dla spanu.

## Okna (długie teksty)

`max_len` = 384 słów (token GLiNER = słowo lub znak interpunkcji wg splittera biblioteki, `okna.TokenizerGliner`).
Okno 320 tokenów (`PBENCH_OKNO_TOKENOW` do testów), zakładka 20%, cięcia na białych znakach (cofnięcie krawędzi dodaje
≤ 32 tokeny < 384), odrzucanie wykryć dotykających sztucznej krawędzi, scalanie offsetów znakowych.
