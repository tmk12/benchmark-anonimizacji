# presidio-pl-ner

Microsoft Presidio Analyzer z silnikiem NLP `transformers` (NER HF per język) i własnymi polskimi rozpoznawaczami z sumą
kontrolną. Poziom: tylko **tekst**. Konfiguracja „kompetentnego integratora Presidio dla dokumentów polskich i
zagranicznych”.

## Wersje (przypięte, `uv.lock` w repo)

presidio-analyzer 2.2.366 (MIT), spaCy 3.8.18, spacy-huggingface-pipelines 0.0.4, transformers 4.57.6, torch 2.15.0+cpu
(indeks pytorch CPU), sentencepiece 0.2.2, protobuf 7.36.2. Modele spaCy `*_core_*_lg` 3.8.0 jak w `presidio-spacy`
(wyłącznie tokenizacja/lematyzacja; NER pochodzi z modeli transformers).

## Modele NER (HF, rewizje przypięte w `modele.json`, `vendor/hf`, potem offline)

| Język | Model | Rewizja | Licencja |
|---|---|---|---|
| pl | `lexedit/herbert-polish-legal-ner` (HerBERT-base fine-tuned, polski prawniczy NER z klasami PII) | `3b0f37e527cd65f863dde911ab908da6b3b2534a` | CC-BY-4.0 |
| en | `dslim/bert-large-NER` | `6fe43d9ec0bba0f67e367ecd74399216fc409c7f` | MIT |
| es | `Davlan/xlm-roberta-large-ner-hrl` | `1f929ffad9b7353f9c84b0b3f579fc3bb0b3685e` | AFL-3.0 |
| de | `FacebookAI/xlm-roberta-large-finetuned-conll03-german` | `1fbcc7a00a69ce5ab754623154a8e9cc6ba868e2` | brak w karcie ("More information needed"); repo FacebookAI, wagi XLM-R: MIT |
| fr | `Jean-Baptiste/camembert-ner` | `ef35fe7767c1dad71f5c853838cdd80d0b3441ed` | MIT |

Źródło konfiguracji: dokumentacja Presidio „Transformers NLP engine” (<https://microsoft.github.io/presidio/analyzer/nlp_engines/transformers/>,
`conf/transformers.yaml` z pakietu): model spaCy do tokenizacji + model transformers do NER, mapowanie etykiet modelu na encje Presidio.

### Wybór modelu polskiego (zbiór dev, 46 dokumentów PL: 3 na typ + 1 lista płac; 6 kandydatów)

Wszystkie kandydaty uruchomione tym samym uczestnikiem (identyczne rozpoznawacze wzorcowe/PL, `aggregation_strategy=simple`),
oceniane `pbench-ocen` na dev. „Wycieki NER” = wycieki w kategoriach OSOBA, ORGANIZACJA, ADRES, MIEJSCOWOSC, KRAJ, REGION,
MIEJSCE_UR, DATA, DATA_UR (reszta zależy od wzorców, wspólnych dla kandydatów).

| Kandydat (licencja) | Wycieki (wszystkie kat.) | Wycieki NER | w tym OSOBA / ORG | char-F2 (średnia) | FP (znaki) |
|---|---|---|---|---|---|
| `lexedit/herbert-polish-legal-ner` (CC-BY-4.0) | 420/2213 | 46 | 5 / 16 | **0.877** | 1118 |
| `pczarnik/herbert-base-ner` (CC-BY-4.0, HerBERT-NER) | 613/2213 | 235 | 0 / 15 | 0.717 | 9430 |
| `clarin-pl/FastPDN` (CC-BY-4.0, CLARIN-PL) | 679/2213 | 263 | 32 / 3 | 0.750 | 2404 |
| `Babelscape/wikineural-multilingual-ner` (CC-BY-NC-SA-4.0) | 692/2213 | 268 | 6 / 34 | 0.714 | 2521 |
| `ivlcic/xlmr-ner-slavic-pline` (Apache-2.0) | 796/2213 | 389 | 157 / 6 | 0.734 | 3004 |
| `julian-schelb/roberta-ner-multilingual` (MIT) | 1716/2213 | 862 | 507 / 121 | 0.422 (1 timeout) | 997 |

Wybór: **`lexedit/herbert-polish-legal-ner`** – najlepszy wg obu kryteriów (najmniej wycieków i najwyższy char-F2, miara
kalibracji grupy A). **Uwaga dla kontrolera:** to rozszerzenie listy kandydatów z briefu (HerBERT-NER / CLARIN-PL); model
lexedit jest NER-em HerBERT dotrenowanym na polskich dokumentach prawnych (PII), więc daje Presidio najsilniejszy
polski NER dostępny publicznie, ale jest to model wyspecjalizowany w anonimizacji prawniczej – dane treningowe „internal
Polish legal documents” (karta), niezależne od naszego korpusu, lecz **nieznane** (nie da się wykluczyć nakładania się z
dokumentami podobnymi do korpusu; wynik PL tego uczestnika należy czytać z tą adnotacją). Split dev benchmarku służył
wyłącznie do wyboru modelu (nie do strojenia ani treningu); test/holdout nie był używany. Ścisły wybór w obrębie briefu: HerBERT-NER
(`pczarnik`, najmniej wycieków osób) albo FastPDN (wyższy char-F2); zamiana to jedna linia w `modele.json` (+ ewentualnie
`PBENCH_MODEL_PL`). Dla innych kandydatów porównanie jest powtarzalne: `PBENCH_JEZYKI=pl PBENCH_MODEL_PL=<repo>`.

### Wybór modeli EN/ES/DE/FR (dev, 11 dokumentów na język, bez list płac; porównanie z kart modeli)

Dwa ramiona: A = modele jednojęzyczne z kart (EN `dslim/bert-large-NER`, ES `MMG/xlm-roberta-large-ner-spanish`,
DE `FacebookAI/xlm-roberta-large-finetuned-conll03-german`, FR `Jean-Baptiste/camembert-ner`), B = jeden wielojęzyczny
`Davlan/xlm-roberta-large-ner-hrl` (PER/ORG/LOC/DATE, 10 języków wysokich zasobów) dla wszystkich czterech.

| Język | A: wycieki / char-F2 | B: wycieki / char-F2 | Wybór |
|---|---|---|---|
| en | 101/299, 0.796 | 102/299, 0.790 | A (remis, MIT) |
| es | 150/311, 0.673 | 140/311, 0.689 | **B** (Davlan) |
| de | 63/311, 0.883 | 89/311, 0.806 | A |
| fr | 117/345, 0.766 | 124/345, 0.780 | A (mniej wycieków, remis F2) |

Próba mała (11 dok./język) – różnice EN i FR w granicach szumu. Nie porównywano modeli PII (to osobni uczestnicy).

## Rozpoznawacze

Wzorcowe i krajowe z wydania 2.2.366 – identyczne jak w `presidio-spacy` (lista w jego KONFIG.md; rejestr
`../_wspolne/presidio_wspolne.py`), **bez** `SpacyRecognizer` ze spaCy: encje NER (PERSON, ORGANIZATION, LOCATION, DATE_TIME…)
dostarcza silnik transformers. Dodatkowo dla pl (`../_wspolne/rozpoznawacze_pl.py`, styl Presidio – `PatternRecognizer` +
`validate_result`):

* `PlNipRecognizer`→PL_NIP: 10 cyfr (opcjonalnie prefiks PL, układy 3-3-2-2 i 3-2-2-3), suma kontrolna mod 11.
* `PlRegonRecognizer`→PL_REGON: 9 lub 14 cyfr, sumy kontrolne wg rozporządzenia REGON.
* `PlKrsRecognizer`→PL_KRS: 10 cyfr zaczynających się od 000 (brak sumy kontrolnej – wynik niski, podnosi go kontekst „KRS”).
* `PlDowodRecognizer`→PL_ID_CARD: 3 litery + 6 cyfr, cyfra kontrolna na 4. pozycji.
* wbudowany `PlPeselRecognizer` (suma kontrolna) i telefon z regionem PL.

Sumy kontrolne przetestowane na wartościach gold korpusu (wszystkie NIP/REGON/DOWOD przechodzą – test w `tests/test_uczestnicy_oss.py`).

## Rozstrzygnięcia integratora

* **`aggregation_strategy = simple`** (a nie „max” z `conf/transformers.yaml`): przy „max” tokenizer HerBERT (BPE z
  końcówkami słów) ucina encje wielowyrazowe („Jan Kowalski” → „Jan”; na dev dla `pczarnik`: 235 niewykrytych osób przy „max”, 0 przy „simple”), „simple” jest domyślną strategią HF. Wspólne dla wszystkich modeli (użyte też w porównaniach EN/ES/DE/FR).
* Mapowanie etykiet modeli → encje Presidio w `run.py` (`MAPOWANIE_NER`; etykiety MISC pomijane): PER→PERSON,
  ORG→ORGANIZATION, LOC/LOC_PUB/GPE→LOCATION, DATE/TIME→DATE_TIME; lexedit dodatkowo EMAIL, PHONE, IBAN, ID (+MEDICAL_ID),
  DIAGNOSIS→MEDICAL_CONDITION, HEALTH_FACILITY→ORGANIZATION (MONEY i WATERMARK nieprzekazywane). `etykiety.json` – mapowanie
  na kategorie gold (miara „w deklarowanym zakresie”; reguła: `metodyka/zakres-gold.md` pkt 4): LOCATION obejmuje ADRES, bo LOC
  lexedit to adres prywatny (karta: „LOC (private address/location)”); ID lexedit („national id / case / document number”) →
  PESEL, DOWOD, PASZPORT, SYGNATURA; MEDICAL_LICENSE/US_NPI/DE_LANR → NR_ID (numer lekarza); ES_NIF → DNI, NR_PODATKOWY
  (bez CIF – wzorzec DNI). Zakres per język dokumentu (J1-fix3): klasy lexedit (ID, MEDICAL_CONDITION, ADRES z LOCATION) –
  tylko pl (w en/es/de/fr NER CoNLL ich nie ma), rozpoznawacze krajowe – w swoim języku (`PL_*` i `rozpoznawacze_pl` – pl,
  `US_*`/`UK_*`/`MEDICAL_LICENSE` – en, `ES_*` – es, `DE_*` – de); w `etykiety.json` słownik język → kategorie.
* Telefon: regiony jak w `presidio-spacy`.

## Języki, próg, wynik

Oficjalnie: pl, en, es, de, fr (każdy ma model NER i rozpoznawacze). Próg domyślny autorów = 0 (podłoga 0.05, `prog.json`,
`PBENCH_SUROWE=1`). `wynik` = `score` Presidio (pewność modelu HF; dla wzorców wynik rozpoznawacza).

Ruling R37: uczestnik **uruchamiany jest na wszystkich 5 językach** (`jezyki`); `jezyki_oficjalne` w `uczestnik.toml` wskazuje języki oficjalnie obsługiwane wg karty/dokumentacji (sędzia: flaga `w_zakresie_oficjalnym`, miara „w zakresie oficjalnym”).

## Okna (długie teksty)

Okna **tokenowe** wg tokenizera modelu danego języka (limit 512 tokenów, okno 472 = 512 − 40 zapasu na tokeny
specjalne i różnice retokenizacji; `PBENCH_OKNO_TOKENOW`), zakładka 12%, krawędzie na białych znakach, odrzucanie wykryć
dotykających sztucznej krawędzi, scalanie offsetów znakowych (`../_wspolne/okna.py`). Wewnętrzny `stride` HF (16) pozostaje
w konfiguracji jak u autorów, ale okna go nie wymagają.

## Uwagi

* Czas: modele `large` (≈560 mln parametrów dla es/de/fr/en) na CPU są wolne; start procesu ładuje 5 modeli
  (`start_timeout_s` 900, `timeout_s` 600 dla list płac ~20 tys. znaków).
* Brak poziomu plik.
