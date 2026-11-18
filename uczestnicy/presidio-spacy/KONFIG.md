# presidio-spacy

Microsoft Presidio Analyzer z silnikiem NLP spaCy – konfiguracja domyślna autorów rozszerzona o wszystkie 5 języków
korpusu. Poziom: tylko **tekst** (Presidio jest analizatorem tekstu; nie ma przetwarzania plików).

## Wersje (przypięte w `pyproject.toml`, `uv.lock` w repo)

| Składnik | Wersja | Licencja |
|---|---|---|
| presidio-analyzer | 2.2.366 | MIT |
| spaCy | 3.8.18 | MIT |
| `pl_core_news_lg` | 3.8.0 (wheel sha256 `3bc7296c…dcc0`) | GNU GPL 3.0 |
| `en_core_web_lg` | 3.8.0 (sha256 `293e9547…ab63`) | MIT |
| `es_core_news_lg` | 3.8.0 (sha256 `7c6c2127…050b`) | GNU GPL 3.0 |
| `de_core_news_lg` | 3.8.0 (sha256 `36fda650…9fed`) | MIT |
| `fr_core_news_lg` | 3.8.0 (sha256 `da5bf7fc…45de`) | LGPL-LR |

Modele spaCy pochodzą z oficjalnych wydań `explosion/spacy-models` na GitHubie (URL i pełne sha256 w `uv.lock`);
nie są pobierane z HF, więc `vendor/hf` nie jest używany. Środowisko: CPU, bez torcha (spaCy/thinc).

## Źródło „najlepszej konfiguracji”

Dokumentacja autorów: <https://microsoft.github.io/presidio/analyzer/languages/> (wiele języków: osobny model spaCy per
język w `NlpEngineProvider`), <https://microsoft.github.io/presidio/analyzer/nlp_engines/spacy_stanza/> oraz plik
`conf/spacy_multilingual.yaml` z pakietu (mapowanie etykiet, `low_confidence_score_multiplier` 0.4 dla ORG). Wybrano
największe (`lg`) modele spaCy dostępne dla każdego z 5 języków; dla PL i ES, gdzie Presidio nie dostarcza
rozpoznawaczy NER w rejestrze domyślnym (domyślny rejestr zna tylko `en`), rejestr budowany jest ręcznie dla każdego języka.

Rozstrzygnięcia integratora (wszystkie konieczne, by Presidio w ogóle działało w PL/ES/DE/FR):

* **Rejestr per język** (`../_wspolne/presidio_wspolne.py`): domyślny `default_recognizers.yaml` ładuje rozpoznawacze
  tylko dla `en` (i kilku języków wybranych rozpoznawaczy); dla każdego z 5 języków rejestrujemy rozpoznawacze
  wzorcowe i krajowe z `supported_language` = język dokumentu.
* **Etykiety modelu polskiego** (NKJP: `persName`, `placeName`, `geogName`, `orgName`, `date`, `time`) nie występują w
  domyślnym mapowaniu Presidio – dopisane do `model_to_presidio_entity_mapping` (bez tego Presidio ignoruje całe NER
  dla polskiego). `MISC` (de/es/fr) pozostaje niemapowane (Presidio nie ma odpowiednika).
* **Telefon**: domyślne regiony `PhoneRecognizer` (US GB DE FR IL IN CA BR) nie zawierają PL ani ES; dopisujemy region
  kraju języka dokumentu oraz PL i ES (numery z „+” działają niezależnie od regionów).
* ORG pozostaje z `low_confidence_score_multiplier` 0.4 (jak w konfiguracji autorów).

## Rozpoznawacze (wydanie 2.2.366) per język

Wzorcowe, dla każdego z 5 języków: `EmailRecognizer`→EMAIL_ADDRESS, `UrlRecognizer`→URL, `IpRecognizer`→IP_ADDRESS,
`IbanRecognizer`→IBAN_CODE, `CreditCardRecognizer`→CREDIT_CARD, `CryptoRecognizer`→CRYPTO,
`DateRecognizer`→DATE_TIME, `MacAddressRecognizer`→MAC_ADDRESS, `UuidRecognizer`→UUID,
`PhoneRecognizer`→PHONE_NUMBER (regiony jw.), `SpacyRecognizer`→PERSON, ORGANIZATION, LOCATION, DATE_TIME, NRP.

Krajowe (wszystkie wbudowane dostępne w tym wydaniu dla danego kraju):

| Język | Rozpoznawacze krajowe |
|---|---|
| pl | `PlPeselRecognizer`→PL_PESEL (w wydaniu brak NIP/REGON/KRS/dowodu – dopisuje je `presidio-pl-ner`) |
| en | USA: `UsSsn`, `UsItin`, `UsPassport`, `UsLicense`, `UsBank`, `UsMbi`, `UsNpi`; Wielka Brytania: `Nhs`, `UkNino`, `UkPassport`, `UkDrivingLicence`, `UkPostcode`, `UkVehicleRegistration`; `MedicalLicense` |
| es | `EsNif`, `EsNie`, `EsPassport` |
| de | `DeTaxId`, `DeTaxNumber`, `DeVatId`, `DeSocialSecurity`, `DeHealthInsurance`, `DeIdCard`, `DePassport`, `DeFuehrerschein`, `DeKfz`, `DePlz`, `DeHandelsregister`, `DeBsnr`, `DeLanr` |
| fr | brak (wydanie nie zawiera rozpoznawaczy francuskich) |

**Wszystkie** wbudowane rozpoznawacze krajowe Presidio 2.2.366 dla krajów zgodnych z językami korpusu (PL, US/UK dla EN,
ES, DE; FR nie ma żadnego w wydaniu) są włączone dla odpowiadającego im języka (lista w `OGOLNE`/`KRAJOWE` w
`../_wspolne/presidio_wspolne.py`); te same reguły obowiązują `presidio-pl-ner` i `presidio-gliner`.

**Słowa kontekstu** (wzmacniające wynik wzorca, np. „SSN”, „passport”) to domyślne, angielskie listy Presidio
(`context` rozpoznawaczy) – biblioteka nie dostarcza ich w PL/ES/DE/FR i niczego tu nie tłumaczymy. To ograniczenie
biblioteki, nie konfiguracji: poza angielskim wzorce bez sumy kontrolnej dostają niższy wynik.

Nie włączono rozpoznawaczy innych krajów (Kanada, Australia, Indie, Korea, Singapur, RPA, Włochy, Nigeria, Szwecja…
– poza zakresem korpusu).

## Język i progi

* Deklarowane języki (`uczestnik.toml`): pl, en, es, de, fr – dla każdego jest model spaCy `lg`.
* Próg: domyślny autorów `default_score_threshold` = 0 (`default_analyzer.yaml`); uczestnik zwraca wykrycia z wynikiem
  ≥ 0.05 (podłoga siatki kalibracji), `prog.json` (`{"prog": x}`, zad. 16) podnosi próg, `PBENCH_SUROWE=1` wyłącza filtr.
* Wynik (`wynik`) = `score` Presidio (NER spaCy ma stałe 0.85, ORG 0.34; wzorce 0.01–1.0 po walidacji sumy kontrolnej i
  kontekście).

## Okna (długie teksty)

Presidio+spaCy nie ma twardego limitu tokenów (spaCy `max_length` = 1 mln znaków), ale dokument dzielony jest na okna
po 50 000 znaków (`PBENCH_OKNO_ZNAKI`) z zakładką ≥ 10%, cięcia na białych znakach; wykrycia dotykające sztucznej
krawędzi okna są odrzucane (kompletną wartość widzi sąsiednie okno), identyczne z różnych okien scalane
(`../_wspolne/okna.py`). Offsety znakowe oryginału.

## Mapowanie etykiet → kategorie gold

Plik `etykiety.json` (etykieta Presidio → lista kategorii `KATEGORIE`; lista pusta = brak odpowiednika w gold; słownik język →
lista – encja rozpoznawacza zarejestrowanego tylko dla tego języka: `PL_*` – pl, `US_*`/`UK_*`/`MEDICAL_LICENSE` – en, `ES_*` – es,
`DE_*` – de). Uczestnik zwraca **surowe etykiety Presidio**; mapowanie służy mierze pomocniczej „w deklarowanym zakresie”.
Kategorie w zakresie = suma wartości z `etykiety.json` dla rozpoznawaczy włączonych w języku dokumentu (`metodyka/zakres-gold.md`
pkt 4, J1-fix3). Najważniejsze: PERSON→OSOBA,
ORGANIZATION→ORGANIZACJA, LOCATION→MIEJSCOWOSC/KRAJ/REGION/MIEJSCE_UR (NER spaCy: miejsca, nie adres pocztowy – jak
w `stanza`), MEDICAL_LICENSE/US_NPI/DE_LANR→NR_ID (numer lekarza), DATE_TIME→DATA/DATA_UR,
EMAIL_ADDRESS→EMAIL, PHONE_NUMBER→TELEFON, IBAN_CODE→RACHUNEK, CREDIT_CARD→KARTA, PL_PESEL→PESEL, US_SSN→SSN,
UK_NINO→NINO, UK_NHS→NHS, ES_NIF→DNI/NR_PODATKOWY (bez CIF: wzorzec `EsNifRecognizer` to cyfry + litera kontrolna DNI, CIF
zaczyna się literą), DE_SOCIAL_SECURITY→SVNR, DE_HEALTH_INSURANCE→KVNR, DE_VAT_ID→VAT.

## Uwagi

* Presidio zwraca wykrycia nakładające się (np. URL i EMAIL na tym samym fragmencie); uczestnik przekazuje je wszystkie
  (wyciek liczony jest sumą pokrycia).
* Czasy na 10 dokumentach dev: zob. raport zadania 13a.

## Języki

Oficjalnie: pl, en, es, de, fr (modele spaCy `*_core_news_lg` / `en_core_web_lg`). Ruling R37: uruchamiany na wszystkich 5; `jezyki_oficjalne` w `uczestnik.toml` → flaga `w_zakresie_oficjalnym` w ocenach.
