# gliner-knowledgator-pii

Samodzielny GLiNER `knowledgator/gliner-pii-large-v1.0` (Knowledgator + Wordcab), wariant **large**. Poziom: tylko **tekst**.

## Wersje (przypięte, `uv.lock` w repo)

| Składnik | Wersja / rewizja | Licencja |
|---|---|---|
| gliner | 0.2.29 | Apache-2.0 |
| torch (CPU) / transformers | 2.15.0+cpu / 4.57.6 | BSD-3 / Apache-2.0 |
| `knowledgator/gliner-pii-large-v1.0` | rewizja HF `f847f54fbc97ad6e78bfa20ed9c5e5d5c43327b9`, `pytorch_model.bin` sha256 `5fa17d94fe963bb09de7cd747a7a02bc2f74898a9b72ecba001f0d884ab01ab2` (1,76 GB) | Apache-2.0 |

Szkielet `microsoft/deberta-v3-large` – tokenizer w repozytorium modelu, konfiguracja kodera w `gliner_config.json`.
Modele w `vendor/hf` (HF_HOME), potem `HF_HUB_OFFLINE=1`; pobierane bez plików ONNX.

## Wybór wariantu (organizacja knowledgator, rodzina PII)

Oficjalne checkpointy PII: `gliner-pii-{edge,small,base,large}-v1.0` i `gliner-stream-pii-v1.0` (wszystkie Apache-2.0,
wszystkie `language: en` w karcie, znacznik „multilingual” bez listy języków). Karta, F1 na zbiorze autorów
`synthetic-multi-pii-ner-v1`: edge 75,50%, small 76,84%, base 80,99%, **large 83,25%** (precyzja 87,42%, czułość 79,4%) –
wybrany **large**, najlepszy wg autorów; działa na CPU (570 M parametrów, wolniejszy od base/small). Wielojęzycznego checkpointu
PII u knowledgatora nie ma (`gliner-x-*` to ogólny NER wielojęzyczny, bez strojenia PII – nie jest „checkpointem PII”,
poza zakresem tego uczestnika). Alternatywy do ewentualnego porównania: `gliner-pii-base-v1.0` (rewizja
`61726e0ad791dcab3e29339bbec3ad42ded65641`; pobranie do `vendor/hf` zostało, ładowanie offline wymaga dodatkowego tokenizera).

`gliner_config.json` (large): `max_len` 768, `max_types` 30, `span_mode: token_level`, `max_width` 100.

## Źródło „najlepszej konfiguracji”

Karta: <https://huggingface.co/knowledgator/gliner-pii-large-v1.0> – `predict_entities(tekst, etykiety, threshold=0.3)`
(„Recommended starting point for production: 0.3”), etykiety z jej list: 60+ predefiniowanych kategorii, zero-shot dla pozostałych.
**Polityka `flat_ner`:** domyślna karty/biblioteki, `flat_ner=True`.
Model pytany z progiem 0.05, filtr progu po scaleniu okien.

## Etykiety (30 = `max_types`, jeden przebieg na okno)

Nazwy z list karty (personal, contact, financial, healthcare, id documents) plus naturalne nazwy zero-shot (zalecane przez kartę)
dla kategorii gold, których lista nie ma: `organization`, `date`, `iban`, `national id number`, `tax identification number`,
`identity card number`, `registration number`. Mapowanie w `etykiety.json` (miara pomocnicza; żadne wykrycie nie jest odrzucane).

| Etykieta GLiNER | Kategorie gold |
|---|---|
| name | OSOBA |
| organization | ORGANIZACJA |
| dob / date | DATA_UR / DATA |
| email address | EMAIL |
| phone number | TELEFON |
| ip address / url | IP / URL |
| location address, location street | ADRES |
| location city / state / country / zip | MIEJSCOWOSC, MIEJSCE_UR / REGION / KRAJ / KOD_POCZTOWY |
| iban, bank account | RACHUNEK |
| credit card | KARTA |
| money | KWOTA |
| ssn | SSN, SVNR, NUSS, NINO, NIR |
| national id number | PESEL, DNI, NUSS, NIR |
| tax identification number | NIP, NR_PODATKOWY, VAT, CIF, EIN, SIREN |
| passport number / identity card number / driver license | PASZPORT / DOWOD / PRAWO_JAZDY |
| vehicle id | NR_REJESTRACYJNY |
| registration number | NR_REJESTRU, KRS, REGON |
| username / password | LOGIN / SEKRET |
| healthcare number / condition | KVNR, MBI, NHS / ZDROWIE |

## Języki

Oficjalnie: **en** (metadane karty: `language: [en]`; znacznik „multilingual” nie wskazuje języków). Pozostałe 4 języki korpusu uruchamiane poza zakresem oficjalnym.
Test granicy okna używa `PBENCH_SUROWE=1`, bo prawdziwy e-mail dostał wynik 0.289 < próg karty 0.30 (to pewność modelu, nie błąd okien).
Uwaga o jakości: model słabo wykrywa generyczne „John Smith” (wynik < 0.05 w zdaniu „Please contact John Smith…”), co jest cechą modelu (poprawnie wykrywa np. „Mr. Adam Nowak”); test dymny używa więc „Adam Nowak”.

Ruling R37: uczestnik **uruchamiany jest na wszystkich 5 językach** (`jezyki`); `jezyki_oficjalne` w `uczestnik.toml` wskazuje języki oficjalnie obsługiwane wg karty/dokumentacji (sędzia: flaga `w_zakresie_oficjalnym`, miara „w zakresie oficjalnym”).

## Próg i wynik

Domyślny 0.30 (karta). `prog.json` po kalibracji; `PBENCH_SUROWE=1` → 0.05. `wynik` = pewność GLiNER.

## Okna (długie teksty)

`max_len` 768 słów (splitter `whitespace` = `okna.TokenizerGliner`). Okno **384 tokeny** (połowa limitu: koszt CPU rośnie kwadratowo,
modele GLiNER trenowane na krótkich rekordach), zakładka 20%, cięcia na białych znakach, odrzucanie wykryć dotykających sztucznej
krawędzi, scalanie offsetów znakowych.
