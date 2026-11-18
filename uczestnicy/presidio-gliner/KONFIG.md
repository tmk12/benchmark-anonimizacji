# presidio-gliner

Microsoft Presidio Analyzer z `GLiNERRecognizer` (checkpoint PII) zamiast NER spaCy. Poziom: tylko **tekst**.

## Wersje (przypięte, `uv.lock` w repo)

| Składnik | Wersja / rewizja | Licencja |
|---|---|---|
| presidio-analyzer | 2.2.366 | MIT |
| gliner | 0.2.29 | Apache-2.0 |
| torch (CPU) / transformers | 2.15.0+cpu / 4.57.6 | BSD-3 / Apache-2.0 |
| spaCy + `*_core_news_lg` (tokenizacja, lematyzacja) | jak w `presidio-spacy` (3.8.18 / 3.8.0) | MIT / modele: GPL-3.0 (pl, es), MIT (en, de), LGPL-LR (fr) |
| `urchade/gliner_multi_pii-v1` | rewizja HF `1fcf13e85f4eef5394e1fcd406cf2ca9ea82351d` | Apache-2.0 |
| `microsoft/mdeberta-v3-base` (szkielet GLiNER: tokenizer i konfiguracja) | rewizja `a0484667b22365f84929a935b5e50a51f71f159d` | MIT |

Modele w `vendor/hf` (HF_HOME), potem `HF_HUB_OFFLINE=1`. Checkpoint ten sam, który ma być oceniany w zadaniu 13b
(zgodnie z rozstrzygnięciem kontrolera).

## Źródło „najlepszej konfiguracji”

Dokumentacja Presidio: <https://microsoft.github.io/presidio/analyzer/nlp_engines/gliner/> oraz plik `conf/slim.yaml`
w pakiecie (spaCy tylko do tokenizacji/lematyzacji, `GLiNERRecognizer` zamiast `SpacyRecognizer`, rozpoznawacze wzorcowe
i krajowe jak zwykle). `GLiNERRecognizer` domyślnie używa właśnie `urchade/gliner_multi_pii-v1`, `flat_ner=True`,
`multi_label=False`, `threshold=0.30`.

* Silnik NLP: spaCy z modelami `lg` dla 5 języków, **bez** `SpacyRecognizer` (NER spaCy wyłączony z rejestru).
* Rozpoznawacze wzorcowe/krajowe per język: identycznie jak w `presidio-spacy` (zob. jego KONFIG.md); rejestr budowany
  w `../_wspolne/presidio_wspolne.py`.
* Jeden załadowany model GLiNER, zarejestrowany jako `GLiNERRecognizer` dla każdego z 5 języków.
* Etykiety GLiNER podane jawnie (`entity_mapping` w `run.py`; ≤ 25 – `max_types` modelu). Presidio nie ma encji na część
  z nich – wtedy nazwa własna (kolumna 2). Wszystko surowe, mapowanie do gold w `etykiety.json`.

| Etykieta GLiNER | Encja Presidio / własna | Kategorie gold (`etykiety.json`) |
|---|---|---|
| person | PERSON | OSOBA |
| organization | ORGANIZATION | ORGANIZACJA |
| address | LOCATION | ADRES |
| postal code | POSTAL_CODE | KOD_POCZTOWY |
| date of birth | DATE_TIME | DATA_UR (DATA – przez `DateRecognizer`, ta sama encja) |
| email | EMAIL_ADDRESS | EMAIL |
| phone number | PHONE_NUMBER | TELEFON |
| ip address | IP_ADDRESS | IP |
| iban | IBAN_CODE | RACHUNEK |
| bank account number | BANK_ACCOUNT | RACHUNEK |
| credit card number | CREDIT_CARD | KARTA |
| passport number | PASSPORT | PASZPORT |
| identity card number | ID_CARD | DOWOD |
| national id number | NATIONAL_ID | PESEL, DNI, NUSS, NIR |
| social security number | SSN | SSN, SVNR, NUSS, NINO, NIR |
| tax identification number | TAX_ID | NIP, NR_PODATKOWY, VAT, CIF, EIN, SIREN |
| driver's license number | DRIVER_LICENSE | PRAWO_JAZDY |
| license plate number | LICENSE_PLATE | NR_REJESTRACYJNY |
| registration number | REGISTRATION_NUMBER | NR_REJESTRU, KRS, REGON, NR_REJESTRACYJNY |
| health insurance number | HEALTH_INSURANCE | KVNR, MBI, NHS |
| medical condition | MEDICAL_CONDITION | ZDROWIE |
| username | USERNAME | LOGIN |

Etykiety GLiNER – w zakresie w każdym języku (rozpoznawacz zarejestrowany dla wszystkich 5); encje rozpoznawaczy krajowych
(`PL_*`, `US_*`/`UK_*`/`MEDICAL_LICENSE`, `ES_*`, `DE_*`) – tylko w języku, dla którego są zarejestrowane (w `etykiety.json` słownik
język → kategorie; `metodyka/zakres-gold.md` pkt 4, J1-fix3); `ES_NIF` → DNI, NR_PODATKOWY (bez CIF – wzorzec DNI; CIF jest w
zakresie przez `TAX_ID`).

## Języki

Oficjalnie (karta checkpointu `urchade/gliner_multi_pii-v1`): en, fr, de, es, pt, it – bez PL; Presidio samo deklaruje GLiNER dla dowolnego języka, szkielet mDeBERTa-v3 jest wielojęzyczny. Rozpoznawacz zarejestrowany dla wszystkich 5.

Ruling R37: uczestnik **uruchamiany jest na wszystkich 5 językach** (`jezyki`); `jezyki_oficjalne` w `uczestnik.toml` wskazuje języki oficjalnie obsługiwane wg karty/dokumentacji (sędzia: flaga `w_zakresie_oficjalnym`, miara „w zakresie oficjalnym”).

## Próg i wynik

Domyślny autorów: `threshold` = 0.30. Model jest uruchamiany z progiem 0.05 (podłoga siatki kalibracji), a filtr
`prog.json` (domyślnie 0.30; `PBENCH_SUROWE=1` → 0.05) stosowany jest po scaleniu okien. Uwaga: przy progu modelu 0.05 wybór
nienakładających się spanów (`flat_ner`) działa na większym zbiorze kandydatów niż przy 0.30 – wyniki zbliżone, ale
nie bit-w-bit takie jak w ustawieniu autorów; kalibracja (zad. 16) odbywa się w tym samym trybie co przebieg końcowy.
`wynik` = pewność GLiNER dla encji z modelu, a dla wzorców wynik rozpoznawacza Presidio.

## Okna (długie teksty)

`max_len` modelu = 384 słów (token GLiNER = słowo lub znak interpunkcji). Własne okna liczone w
tokenach GLiNER (ten sam splitter co w bibliotece: `\w+(?:[-_]\w+)*|\S`; `okna.TokenizerGliner`), nie w znakach:
maks. 320 tokenów (`PBENCH_OKNO_TOKENOW`; zapas na cofnięcie krawędzi do granicy słowa, w praktyce ≤ 352 < 384)
z zakładką 20%, cięcia na białych znakach, odrzucanie wykryć dotykających sztucznej krawędzi,
scalanie offsetów znakowych (`../_wspolne/okna.py`). Wbudowany chunker Presidio (250/50 znaków) jest wyłączony
(`chunk_size=10**9`), by test granicy okna dotyczył kodu harnessu; zasada jest ta sama (okno ze słowną granicą i zakładką).


## Uwagi

* Presidio zwraca wykrycia nakładające się (np. URL i EMAIL); przekazywane są wszystkie.
* Brak poziomu plik.
