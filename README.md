# Benchmark anonimizacji dokumentów

Repozytorium publicznego testu porównawczego narzędzi do wykrywania i maskowania danych osobowych w dokumentach
(modele i narzędzia open source uruchamiane na CPU oraz Privatizer by Legal Geek). Autor testu: Legal Geek.

**Stan na 2026-11-18: wyniki opublikowane.** Repozytorium zawiera raport z wynikami (PDF z osobnym aneksem liczbowym),
kod testu, konfiguracje uczestników open source i korpus syntetyczny.

**Prerejestracja (2026-11-04).** Metodykę (miary, wagi, reguły sędziów wycieku, progi z kalibracji na części dev, listę
uczestników, środowisko oceny) i sumy kontrolne korpusu opublikowano w tym repozytorium **przed** przebiegami na splicie
testowym, z których liczone są wyniki. Data pierwszego commita jest dowodem, że ustalenia zapisano, zanim ktokolwiek
zobaczył wyniki. Zamrożenie potwierdza tag `prerejestracja-1` w repozytorium kodu testu (commit
`071ebc81dc4e570b5ac96c16be0133217fc476af`). Pliki `metodyka/` z prerejestracji to dokumenty z tego commita; w wersji
publicznej pominięto wyłącznie nazwy wewnętrznych maszyn i adnotacje organizacyjne – treść metodyki jest identyczna. Sumy
kontrolne korpusu (`metodyka/SHA256SUMS-*`) są skopiowane bez zmian.

## Zawartość

| Ścieżka | Co to |
|---|---|
| [`raport/raport.pdf`](raport/raport.pdf) | Raport z wynikami: rankingi „tekst” i „pliki”, metodyka, ograniczenia, ujawnienia, aneks odtworzenia |
| [`raport/aneks-liczbowy.pdf`](raport/aneks-liczbowy.pdf) | Aneks liczbowy: tabele per uczestnik, test, język, format, kategoria i miejsce, mierzone wydania i odciski sędziów |
| `metodyka/` | Prerejestracja (`prerejestracja.md`, `punktacja.md`, `wagi_punktow.json`, `progi.json`, `uczestnicy.md`, `przypadki.md`, `SHA256SUMS-*`) oraz dokumenty uzupełniające: zakres gold, znane ograniczenia, kontrola domen, miejsca ukryte, identyfikacja pośrednia, sędziowie warstwy trudnej, wyniki kontroli kontaminacji, środowiska |
| `pbench/` | Kod testu: generator korpusu (trzon i warstwa trudnych przypadków), protokół uczestnika, uruchamianie, sędziowie wycieku (tekst i pliki), kalibracja, agregacja, pomiar czasu |
| `uczestnicy/<id>/` | Uczestnicy open source (grupy A i B): adapter `run.py`, projekt `uv` z plikiem blokady, deklaracja `uczestnik.toml`, opis konfiguracji `KONFIG.md`; `uczestnicy/_wspolne/` – kod wspólny |
| `uczestnicy/privatizer-*/`, `uczestnicy/presidio-lgp/` | Konfiguracja i zasady oceny uczestników z Privatizerem: `KONFIG.md`, `uczestnik.toml`, `etykiety.json`, `odmowy.json` (adaptery nie są publiczne, niżej) |
| `korpus/`, `korpus-trudne/` | Korpus syntetyczny: trzon (1000 dokumentów, 5 języków) i warstwa trudnych przypadków (290 dokumentów); manifest z danymi wzorcowymi (gold), licencja korpusu |
| `raport/` | Generator raportu: rozdziały, szablony, czcionki, grafika, kontrola treści |
| `narzedzia/` | Narzędzia pomocnicze (kontrola domen, kontrola warstwy trudnej, zakresy przykładów) |
| `tests/` | Testy kodu |

Zagregowanych wyników w postaci plików CSV nie publikujemy; liczby są w raporcie i aneksie liczbowym.

## Jak odtworzyć

Wymagania: Python 3.12 i `uv`; Linux, obliczenia na CPU. Ocena plikowa wymaga środowiska z prerejestracji (Tesseract
z danymi językowymi w `vendor/tessdata` o sumach z `metodyka/prerejestracja.md`, LibreOffice, czcionki Liberation) –
szczegóły w `metodyka/srodowiska.md` i w aneksie odtworzenia raportu.

```bash
uv sync
uv run pytest -q --ignore=tests/test_uczestnicy_oss.py      # testy kodu (test uczestników OSS uruchamia modele z vendor/hf)

# korpus z repozytorium: kontrola sum
(cd korpus && sha256sum -c ../metodyka/SHA256SUMS-trzon)
(cd korpus-trudne && sha256sum -c ../metodyka/SHA256SUMS-trudne)

# odtworzenie korpusu z kodu do osobnych katalogów i porównanie sum
uv run pbench-korpus --ziarno 20261103 --cel odtworzony/korpus/
uv run pbench-trudne --ziarno 20261104 --cel odtworzony/korpus-trudne --pelna
(cd odtworzony/korpus && sha256sum -c ../../metodyka/SHA256SUMS-trzon)
(cd odtworzony/korpus-trudne && sha256sum -c ../../metodyka/SHA256SUMS-trudne)

# uczestnik open source: środowisko, przebieg na splicie testowym, ocena
uv sync --frozen --project uczestnicy/<id>
uv run pbench-uruchom --uczestnik <id> --split test --poziom tekst
uv run pbench-ocen    --uczestnik <id> --split test --poziom tekst

# agregacja: oba rankingi, bootstrap, analiza wrażliwości
uv run pbench-agreguj --split test --wyniki wyniki --wyniki-trudne wyniki/trudne --czasy wyniki/czas/czasy.jsonl

# raport
uv run --group raport playwright install chromium
uv run --group raport python -m raport.buduj --wyniki <katalog zbiorczy> --cel raport/build/raport.pdf --cel-aneks raport/build/aneks-liczbowy.pdf
```

Ocena plikowa (`--poziom plik`) sprawdza środowisko oceny i przy niezgodności z prerejestracją kończy się bez oceny.
Kontrola kontaminacji (`pbench-kontaminacja`) wymaga danych treningowych mierzonego modelu i opisu jego linii treningowej –
nie są publiczne; opublikowano jej wynik liczbowy (`metodyka/kontaminacja*.json`).

## Privatizer

Privatizer by Legal Geek jest programem komercyjnym. Adaptery uczestników z Privatizerem (`uczestnicy/privatizer-*`,
`uczestnicy/presidio-lgp`) ładują wydanie programu i jego model, więc nie są publiczne. Privatizera mierzono przez API aplikacji zainstalowanej
z instalatora (wydanie i plan licencji jak w rozdziale „Metodyka” raportu). Konfiguracja i zasady oceny są w
`uczestnicy/privatizer-*/` i `uczestnicy/presidio-lgp/`: `KONFIG.md` (opis), `uczestnik.toml` (deklaracja), `etykiety.json`
(mapowanie etykiet na kategorie gold) i `odmowy.json` (komunikaty aplikacji liczone jako odmowa). Wyniki Privatizera nie są więc
odtwarzalne z tego repozytorium bez programu; pozostałych uczestników można uruchomić według poleceń wyżej.
Ranking mierzy tryb domyślny Privatizera; tryb „Maksymalna ochrona” i warianty krzyżowe są w aneksie, poza rankingami.

## Zobowiązania

- **Korpus jest w pełni syntetyczny** – żadnych danych prawdziwych osób; zbieżność wymyślonych danych z istniejącymi
  osobami jest przypadkowa.
- **Korpus jest deterministyczny:** wygenerował go kod z commita zamrożenia z ziarnami `20261103` (trzon) i `20261104`
  (warstwa trudna); każdy może odtworzyć pliki i porównać je z `metodyka/SHA256SUMS-*`.
- **Metodyka jest zamrożona.** Każda zmiana miar, reguł sędziów, kalibracji, korpusu albo uczestników byłaby nową wersją
  prerejestracji opisaną w raporcie razem z wynikami obu wersji.
- Zespoły Privatizera nie mają dostępu do splitu testowego; korpus nie służy do treningu ani walidacji modelu.

## Licencje

Kod: Apache-2.0 (`LICENSE`). Dokumentacja, wyniki i raport: CC BY 4.0 (`LICENSE-docs.md`).
**Korpus** (`korpus/`, `korpus-trudne/`): licencja własna – `korpus/LICENCJA-KORPUSU.md` (wiążąca wersja polska, tłumaczenie
angielskie w tym samym pliku). Wolno go używać do testowania, oceny i porównywania narzędzi oraz rozpowszechniać
z uznaniem autorstwa, ale **nie wolno go używać do trenowania, dostrajania ani walidacji modeli uczenia maszynowego**.
Zastrzeżenie eksploracji tekstu i danych (art. 4 ust. 3 dyrektywy (UE) 2019/790) ma także postać odczytu maszynowego
(`tdmrep.json`).

---

# Document anonymization benchmark (EN)

Public comparative test of tools that detect and mask personal data in documents (CPU-runnable open-source models
and tools, and Privatizer by Legal Geek). Author: Legal Geek. Documents and code comments are in Polish.

**As of 2026-11-18 the results are published.** The repository contains the results report (PDF with a separate numeric
annex), the test code, the open-source participant configurations and the synthetic corpus. Aggregated results are not
published as CSV files; the figures are in the report and the numeric annex.

**Pre-registration (2026-11-04).** The methodology (measures, weights, leak-judge rules, thresholds calibrated on the dev
split, participants, evaluation environment) and corpus checksums were published here **before** the scored runs on the
test split; the date of the first commit proves they were fixed before anyone saw results. The freeze is the tag
`prerejestracja-1` in the test code repository (commit `071ebc81dc4e570b5ac96c16be0133217fc476af`). The pre-registration
files in `metodyka/` are the documents from that commit; the public version omits only internal machine names and
organisational notes – the methodology is identical. Corpus checksums are copied unchanged.

Contents: [`raport/raport.pdf`](raport/raport.pdf) (report), [`raport/aneks-liczbowy.pdf`](raport/aneks-liczbowy.pdf) (numeric annex), `metodyka/` (pre-registration and
supplementary methodology), `pbench/` (corpus generator, participant protocol, runner, leak judges, calibration,
aggregation, timing), `uczestnicy/<id>/` (open-source participants with `uv` lock files), `korpus/` and `korpus-trudne/`
(synthetic corpus: 1000 core documents in 5 languages and 290 hard-case documents), `raport/` (report generator),
`narzedzia/` (helper tools), `tests/`.

Reproduction: `uv sync`; check the corpus with `sha256sum -c` against `metodyka/SHA256SUMS-*`; regenerate it with
`uv run pbench-korpus --ziarno 20261103` and `uv run pbench-trudne --ziarno 20261104 --pelna` into separate directories and
compare checksums; run an open-source participant with `pbench-uruchom`, score with `pbench-ocen`, aggregate with
`pbench-agreguj`, build the report with `python -m raport.buduj` (commands above). The contamination check needs the
measured model's training data and lineage, which are not public; its numeric result is published
(`metodyka/kontaminacja*.json`).

Privatizer is a commercial program. The Privatizer participant adapters load the program release and its model and are
not public. Privatizer was measured through the API of the application installed from its installer. Its configuration and
scoring rules are in `uczestnicy/privatizer-*/` and `uczestnicy/presidio-lgp/` (`KONFIG.md`, `uczestnik.toml`, `etykiety.json`,
`odmowy.json`); the Privatizer results therefore cannot be reproduced from this repository without the program. The
ranking measures Privatizer's default mode; the “Maximum protection” mode and cross variants are in an annex outside the
rankings. Privatizer teams have no access to the test split, and the corpus is not used to train or validate the model.

Licences: code Apache-2.0; documentation, results and report CC BY 4.0; the corpus is under its own licence
(`korpus/LICENCJA-KORPUSU.md`, Polish version binding, English translation included) permitting testing, evaluation and
comparison of tools but **prohibiting use for training, fine-tuning or validating machine-learning models**; the text and
data mining reservation (Art. 4(3) of Directive (EU) 2019/790) is also machine-readable (`tdmrep.json`).
