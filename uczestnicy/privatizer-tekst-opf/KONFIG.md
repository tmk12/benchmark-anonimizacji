# privatizer-tekst-opf (aneks – wariant krzyżowy)

**Potok tekstowy Privatizera z obcym modelem:** wszystko jak w `privatizer-tekst` (serwer aplikacji, `POST /api/jobs/text`,
reguły, pola, scalanie, lista wyjątków, rozchodzenie powtórzeń, przebieg na wersalikach, maskowanie – kod wydania bez zmian),
ale fragmenty „modelu” daje **OpenAI Privacy Filter** (`openai/privacy-filter`) zamiast Legal Geek Privatizer (RC). Poziom:
**tekst**. Wariant jest w **aneksie, poza rankingami** (`aneks = true`, `metodyka/uczestnicy.md` – „Warianty krzyżowe”): mierzy
wkład potoku aplikacji przy innym modelu, nie jest produktem.

## Co jest czym

| Składnik | Skąd | Wersja / rewizja | Licencja |
|---|---|---|---|
| Potok (reguły, pola, scalanie, wyjątki, maskowanie, serwer) | Privatizer, wydanie z tagu (`git archive` tagu, jak `privatizer-tekst`) | **v1.3.0b24** (`6ed25e2ea415a02a4a93c000ee630bda34f19f3b`) | własna (Legal Geek) |
| Model | wyłącznie oficjalne `openai/privacy-filter` (organizacja `openai` na HF zweryfikowana – `openai-privacy-filter/KONFIG.md`) | rewizja HF `7ffa9a043d54d1be65afb281eddf0ffbe629385b`, `original/model.safetensors` sha256 `9c262cbe68a0c8a50590a648ef8341a2b7d3be1fa11dfb79893fe0b03ce57b5c` | Apache-2.0 |
| Pakiet `opf` | github.com/openai/privacy-filter | commit `f7f00ca7fb869683eb732c010299d901457f19c3` (0.1.0), jak `openai-privacy-filter` | Apache-2.0 |
| tiktoken / safetensors | PyPI | 0.14.0 / 0.8.0 (jak `openai-privacy-filter`) | MIT / Apache-2.0 |
| torch (CPU) / numpy / huggingface_hub | jak `uv.lock` wydania | 2.14.0+cpu / 2.5.4 / 0.36.2 (`openai-privacy-filter`: torch 2.15.0, huggingface_hub 2.4.0 – `transformers` 4.57.6 wydania wymaga huggingface_hub < 1; czyta tę samą migawkę offline) | BSD-3 / BSD-3 / Apache-2.0 |

Wagi w `vendor/hf` (tylko `original/`, format `opf`), słownik `o200k_base` w `vendor/tiktoken`, `HF_HUB_OFFLINE=1` w przebiegu.
Model LGP **nie jest ładowany**: folder modelu w katalogu modeli procesu ma tylko znacznik `.complete` (bez kontenera `.lgm`);
licencja jak w `privatizer-tekst` (plan `pro`).

## Jak podmieniony jest detektor (kod Privatizera bez zmian)

Tak samo jak w `privatizer-tekst-gliner` (zob. jego KONFIG.md): serwer startuje przez `../_wspolne/detektor_krzyzowy.py`, który
w procesie serwera podmienia wpisy `detect.backends.BACKENDS` na `detektor.py:zbuduj_detektor` i uruchamia `lgprivatizer` jak
`-m`; obiekt implementuje `Detector` z `detect/base.py` tagu i jest zarejestrowany pod `lgp-1.0-rc`.

- **Model, dekodowanie, okna, próg** – z uczestnika samodzielnego `openai-privacy-filter` (jego `run.py` ładowany jako moduł,
  analiza przez jego `zbuduj`, ta sama funkcja co w przebiegu samodzielnym): dekoder Viterbiego z `viterbi_calibration.json`
  (punkt pracy `default`), okna 4096 tokenów tiktoken z zakładką 12,5% i jedno dekodowanie po kawałku, szybsza warstwa MoE
  (odstępstwo opisane w `metodyka/uczestnicy.md`), wynik = średnie prawdopodobieństwo tagów spanu, próg = podłoga **0,05**
  (autorzy: twarde dekodowanie bez progu; po kalibracji – `openai-privacy-filter/prog.json`). `PBENCH_SUROWE` nie działa
  (próg jest wejściem potoku, nie filtrem wyniku).
- **Okno silnika:** `chunk_chars` = 10⁹ – `engine._chunks` oddaje dokument (wiersze sklejone spacją) w jednym kawałku, okna
  liczy część OPF jak samodzielnie.
- Kandydaci poniżej progu wyłączeni, tryb czułości nie zmienia progu, krawędzie przycina `backends._trim`, wątki z `OMP_NUM_THREADS`
  orkiestratora – jak w `privatizer-tekst-gliner`.

## Etykiety OPF → kategorie Privatizera (stała `KATEGORIE` w `detektor.py`, `categories.py` b24)

| Etykieta modelu | Kategoria Privatizera |
|---|---|
| private_person | OSOBA |
| private_address | ADRES |
| private_email / private_phone / private_url | EMAIL / TELEFON / URL |
| private_date | DATA (datę urodzenia rozpoznają po kontekście reguły wydania) |
| account_number | NR_ID – etykieta obejmuje rachunki, karty i numery identyfikacyjne (`openai-privacy-filter/KONFIG.md`), więc idzie do kategorii ogólnej jak etykiety wielu kategorii w adapterze wydania; podtyp z sumą kontrolną (IBAN, PESEL…) rozstrzygają reguły |
| secret | SEKRET |

**Skutek mapowania `account_number` → `NR_ID` w potoku.** Fragment kategorii `NR_ID` przechodzi w silniku wydania kontrolę sum
(`engine._sumy_modelu`: reguły numerów osobowych i podatkowych z sumą, `_numer_bez_strony`) – numer rachunku lub karty z tej
etykiety jest więc oceniany regułami numerów krajowych, a nie IBAN/Luhn (rachunek i karta to osobne kategorie `RACHUNEK`/`KARTA`
z własnymi regułami sum). Alternatywa `RACHUNEK` miałaby skutek odwrotny: numery osobowe z tej samej etykiety byłyby sprawdzane
sumą rachunku. `GLINER2_MAP` wydania ma osobne „bank account number” → `RACHUNEK`, ale etykieta OPF jest wieloznaczna, więc
kategoria ogólna jest wyborem obronnym, nie odwzorowaniem 1:1 adaptera wydania.

**Deklaracja (`etykiety.json`, J2):** jak `privatizer-tekst` (kategorie włączone w ustawieniach domyślnych wydania, mapowanie
tożsamościowe) bez `ZDROWIE`: model nie ma etykiety zdrowia, a reguła ICD-10 wydania (D35) działa tylko przy ręcznie włączonej kategorii (domyślnie wyłączona) i zwraca sam kod – fragment wartości
gold (J2 pkt 2). `OSOBA` obejmuje `INICJALY` – `private_person` obejmuje inicjały (J2, jak w `openai-privacy-filter`).

## Dowód, co zmierzono (`wersje`)

Jak `privatizer-tekst` (tag, commit, skróty źródeł, paczki, `czulosc`, `kanal`) oraz dowód z procesu serwera (brak =
start przerwany): `adapter` = `DetektorKrzyzowy`, `zarejestrowany_jako` = `lgp-1.0-rc`, `model`, `hf:model`,
`wagi_original_model_safetensors_sha256` (liczona z pliku i porównana z przypiętą), `opf`, `opf:commit`, `tiktoken`,
`dekodowanie`, `moe`, `prog_modelu`, `okno_tokenow`, `zakladka`, `watki`. Brak pól `kontener_*`.

## Czego ten wariant NIE mierzy

OPF w potoku nie ma kalibracji Privatizera (progów per kategoria, trybów czułości, kandydatów), nie zna organizacji, miejscowości,
numerów rejestrowych ani sygnatur (to dają tylko reguły wydania), a potok był strojony pod model LGP. Wynik to analiza wkładu
modelu i potoku, nie ocena produktu ani OPF.

## Języki

Uruchamiany na 5 językach (R37). `jezyki_oficjalne = ["en"]` – karta modelu („Primarily English”), jak `openai-privacy-filter`;
potok Privatizera obsługuje wszystkie 5.

## Czasy

Przekroczenie czasu liczy się jako dokument z wyciekiem (`punktacja.md`), więc limit dobrano pomiarem (reguła:
`metodyka/uczestnicy.md`, „Czas i wątki”). Pomiar 2026-11-01: **5 najdłuższych dokumentów dev (tekst)** (tabele „lista płac”
20–23 tys. znaków, po jednym na język), 1 proces, `--watki 4`, maszyna obciążona (load ~20 na 20 rdzeniach):
en-lista_plac-0004 83 s, es-lista_plac-0005 108 s, pl-lista_plac-0008 171 s, de-lista_plac-0004 218 s, fr-lista_plac-0002 236 s.
Maksimum 236 s → `timeout_s` **1800** (≥ 7x maksimum; jak w `openai-privacy-filter`), `start_timeout_s` 900.
