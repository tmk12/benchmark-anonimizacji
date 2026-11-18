# privatizer-tekst-gliner (aneks – wariant krzyżowy)

**Potok tekstowy Privatizera z obcym modelem:** wszystko jak w `privatizer-tekst` (serwer aplikacji, `POST /api/jobs/text`,
reguły, pola, scalanie, lista wyjątków, rozchodzenie powtórzeń, przebieg na wersalikach, maskowanie – kod wydania bez zmian),
ale fragmenty „modelu” daje GLiNER **`nvidia/gliner-PII`** zamiast Legal Geek Privatizer (RC). Poziom: **tekst**. Wariant jest
w **aneksie, poza rankingami** (`aneks = true`, `metodyka/uczestnicy.md` – „Warianty krzyżowe”): mierzy wkład potoku
aplikacji przy innym modelu, nie jest produktem. GLiNER `nvidia/gliner-PII` wybrany jako najlepszy w T2 wśród GLiNER w pilocie.

## Co jest czym

| Składnik | Skąd | Wersja / rewizja | Licencja |
|---|---|---|---|
| Potok (reguły, pola, scalanie, wyjątki, maskowanie, serwer) | Privatizer, wydanie z tagu (`git archive` tagu, jak `privatizer-tekst`) | **v1.3.0b24** (`6ed25e2ea415a02a4a93c000ee630bda34f19f3b`) | własna (Legal Geek) |
| Model | `nvidia/gliner-PII` (organizacja `nvidia`, repozytorium oficjalne, bez bramki) | rewizja HF `bd23e8ef4425fd04e34c5204ab49ffaa706eae79`, `pytorch_model.bin` sha256 `a4dfd0dcbd718acc86dca65fa99f1097d2796c8d7a681e1bc42f40f946c03802` | NVIDIA Open Model License (ustalenia w `gliner-nvidia-pii/KONFIG.md`: użycie lokalne i komercyjne dozwolone, publikacja wyników nie jest ograniczona, wag nie redystrybuujemy) |
| gliner | PyPI | 0.2.29 (ta sama w `gliner-nvidia-pii` i w `uv.lock` wydania) | Apache-2.0 |
| torch (CPU) / transformers | jak `uv.lock` wydania | 2.14.0+cpu / 4.57.6 (`gliner-nvidia-pii`: torch 2.15.0 – różnice numeryczne pomijalne) | BSD-3 / Apache-2.0 |

Wagi w `vendor/hf` (HF_HOME, poza gitem, `HF_HUB_OFFLINE=1` w przebiegu). Model LGP **nie jest ładowany**: folder modelu
w katalogu modeli procesu ma tylko znacznik `.complete` (bez kontenera `.lgm`); licencja jak w `privatizer-tekst` (plan `pro`).

## Jak podmieniony jest detektor (kod Privatizera bez zmian)

Serwer startuje przez `../_wspolne/detektor_krzyzowy.py` zamiast `python -m lgprivatizer`. W procesie serwera, przed startem
aplikacji, każdy wpis `lgprivatizer.detect.backends.BACKENDS` (z niego `engine.get_detector` bierze detektor modelu) wskazuje
`detektor.py:zbuduj_detektor`; potem `lgprivatizer` startuje przez `runpy` dokładnie jak z `-m`. Obiekt implementuje interfejs
`Detector` z `lgprivatizer/detect/base.py` tagu (`predict(texts, categories, sensitivity)` → `Span`, `chunk_chars`,
`chunk_overlap`, `kandydaci`), zarejestrowany pod identyfikatorem modelu domyślnego (`lgp-1.0-rc`), więc aplikacja ładuje go
tak jak swój model (`POST /api/models/lgp-1.0-rc/load`), a zadanie musi iść z „modelem” (`sprawdz_model`).

- **Etykiety, próg, okna, `flat_ner`** – z uczestnika samodzielnego `gliner-nvidia-pii` (jego `run.py` ładowany jako moduł,
  analiza przez `gliner_wspolne.analizator`, ta sama funkcja co w przebiegu samodzielnym): 2 grupy etykiet Nemotron-PII
  (osobne przebiegi), próg **0,30** (próg ewaluacji autorów; po kalibracji – `gliner-nvidia-pii/prog.json`, ten sam co
  samodzielnie), `flat_ner=False`, okna 320 tokenów GLiNER z zakładką 20%. `PBENCH_SUROWE` nie działa: próg jest wejściem potoku
  (fragmenty poniżej progu nie trafiają do scalania i rozchodzenia po dokumencie), a nie filtrem wyniku – jak u uczestników
  Privatizera, wariant nie ma trybu surowego do kalibracji.
- **Okno silnika:** `chunk_chars` = 10⁹ – `engine._chunks` oddaje dokument (wiersze sklejone spacją, jak każdemu modelowi)
  w jednym kawałku, a okna liczy GLiNER-owa część jak samodzielnie (okno LGP 2560/448 znaków nie dotyczy obcego modelu).
- **Kandydaci poniżej progu** (`kandydaci`, `slownik_encji`) wyłączeni – obcy model nie zna progów kategorii Privatizera;
  tryb czułości (domyślny `balanced`) nie zmienia progu GLiNER.
- **Krawędzie fragmentu** przycina `backends._trim` (białe znaki i interpunkcja na brzegach) – kontrakt obu adapterów wydania.
- **Wątki:** z ustawienia orkiestratora (`OMP_NUM_THREADS` = `--watki`, `torch.set_num_threads`), jak u uczestników samodzielnych –
  nie polityka wydania (`_configure_threads`: połowa wątków logicznych), która przy kilku procesach nadsubskrybuje maszynę; zapis w `wersje`.

## Etykiety GLiNER → kategorie Privatizera (stała `KATEGORIE` w `detektor.py`, `categories.py` b24)

Fragment ma jedną kategorię. Etykieta obejmująca kilka kategorii idzie do kategorii ogólnej tak, jak w adapterze modelu wydania
(`GLINER2_MAP`: „national/tax identification number” → `NR_ID`, „contract or account reference” i „professional licence
number” → `IDENTYFIKATOR`); podtyp z sumą kontrolną (PESEL, SSN, NIP…) rozstrzygają przy scalaniu reguły wydania.

| Etykiety GLiNER | Kategoria Privatizera |
|---|---|
| first_name, last_name | OSOBA |
| company_name | ORGANIZACJA |
| street_address | ADRES |
| city / county, state / country / postcode | MIEJSCOWOSC / REGION / KRAJ / KOD_POCZTOWY |
| email; phone_number, fax_number; url; ipv4, ipv6 | EMAIL; TELEFON; URL; IP |
| mac_address | MAC (domyślnie wyłączona – fragmenty odpadają jak w wydaniu) |
| user_name | LOGIN |
| date_of_birth; date | DATA_UR; DATA |
| ssn | SSN – kategoria istnieje w `categories.py` b24 (włączona we wszystkich profilach); `SSN` i `NR_ID` mają w silniku ten sam zestaw reguł sum (`_NUMERY_Z_SUMA`), więc dla potoku wybór nie zmienia walidacji |
| tax_id | NR_ID |
| account_number, bank_routing_number, swift_bic | RACHUNEK |
| credit_debit_card | KARTA |
| password, api_key, pin | SEKRET |
| license_plate, vehicle_identifier | NR_REJESTRACYJNY |
| medical_record_number, health_plan_beneficiary_number, certificate_license_number, customer_id, employee_id, unique_id, device_identifier | IDENTYFIKATOR |
| blood_type | ZDROWIE |

**Deklaracja (`etykiety.json`, J2):** jak `privatizer-tekst` (kategorie włączone w ustawieniach domyślnych wydania, mapowanie
tożsamościowe), z jedną różnicą wynikającą z komponentu: `OSOBA` → tylko `OSOBA` (GLiNER zwraca imię i nazwisko –
`first_name`/`last_name` – nie inicjały, a reguła inicjałów jest domyślnie wyłączona). `blood_type` → `ZDROWIE` jest w mapowaniu, ale
`ZDROWIE` jest w wydaniu domyślnie wyłączona, więc silnik odrzuca te fragmenty i `ZDROWIE` nie jest zadeklarowana. Kategorie reguł – jak w `privatizer-reguly`.

## Dowód, co zmierzono (`wersje`)

Jak `privatizer-tekst` (`tag`, `commit`, `zrodla_sha`, paczki `slowniki_*`/`twarze_*`/`ocr_*`,
`manifest_serial`, `czulosc`, `kanal`) oraz dowód z procesu serwera (plik zapisany przez fabrykę po załadowaniu; brak pliku =
start przerwany): `adapter` = `DetektorKrzyzowy`, `zarejestrowany_jako` = `lgp-1.0-rc`, `model`, `hf:model` (repozytorium@rewizja),
`wagi_pytorch_model_bin_sha256` (liczona z pliku i porównana z przypiętą – inna = start przerwany), `gliner`, `prog_modelu`,
`okno_tokenow`, `zakladka`, `flat_ner`, `watki`. Brak pól `kontener_*` – kontener LGP nie istnieje w procesie.

## Czego ten wariant NIE mierzy

GLiNER w potoku nie ma kalibracji Privatizera: progów per kategoria i trybów czułości, kandydatów poniżej progu potwierdzanych
w dokumencie, taksonomii etykiet prawniczych (sygnatury, księgi wieczyste, numery rejestrów), okna dobranego do modelu. Potok
był strojony pod model LGP (np. scalanie z regułami, rozchodzenie powtórzeń). Wynik to analiza wkładu modelu i potoku, a nie
ocena produktu ani GLiNER-a.

## Języki

Uruchamiany na 5 językach (R37). `jezyki_oficjalne = ["en"]` – karta modelu (`language: [en]`), tak jak `gliner-nvidia-pii`;
potok Privatizera obsługuje wszystkie 5.

## Czasy

Przekroczenie czasu liczy się jako dokument z wyciekiem (`punktacja.md`), więc limit dobrano pomiarem (reguła:
`metodyka/uczestnicy.md`, „Czas i wątki”). Pomiar 2026-11-01: **5 najdłuższych dokumentów dev (tekst)** – po jednym na język, tabele
„lista płac” 20–23 tys. znaków – 1 proces, `--watki 4` (`OMP_NUM_THREADS`), maszyna obciążona innymi zadaniami (load ~20 na 20
rdzeniach) i równolegle z pomiarem `privatizer-tekst-opf`:

| Dokument | Czas |
|---|---|
| es-lista_plac-0005 | 1143 s |
| en-lista_plac-0004 | 1285 s |
| fr-lista_plac-0002 | 1692 s |
| de-lista_plac-0004 | 1908 s |
| pl-lista_plac-0008 | 2123 s |

Maksimum 2123 s → `timeout_s` **5400** (≥ 2,5x maksimum; `CZEKANIE_S` w `run.py` 5340 < `timeout_s`), `start_timeout_s` 900. Wcześniejsza
próbka na CV (mediana 138 s) i limit 1800 były za niskie dla tabel: pierwszy pomiar z limitem 1740 s przerwał dokument
`de-lista_plac-0004`. Czasy są górnym oszacowaniem (obciążona maszyna, GLiNER w potoku liczy oba przebiegi silnika, także na
wersalikach); pozostałe dokumenty dev są krótsze (liczba znaków). Zamiast podnosić limit przy zmianie sprzętu – powtórzyć pomiar.
