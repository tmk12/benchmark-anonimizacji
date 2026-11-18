# presidio-lgp (aneks – wariant krzyżowy)

**Microsoft Presidio z modelem Legal Geek Privatizer (RC) jako rozpoznawaczem NER** – konfiguracja jak `presidio-gliner`
(silnik NLP spaCy tylko do tokenizacji/lematyzacji, rozpoznawacze wzorcowe i krajowe, ten sam rejestr), ale zamiast
`GLiNERRecognizer` rozpoznawacz `LgpRecognizer` z modelem `lgp-1.0-rc`. Poziom: tylko **tekst**. Wariant jest w **aneksie, poza
rankingami** (`aneks = true`, `metodyka/uczestnicy.md` – „Warianty krzyżowe”): mierzy wkład modelu LGP bez potoku aplikacji
(reguł, pól, scalania, wyjątków, rozchodzenia) w otoczeniu otwartego narzędzia; nie jest produktem.

## Co jest czym

| Składnik | Wersja / rewizja | Licencja |
|---|---|---|
| presidio-analyzer | 2.2.366 (jak `presidio-gliner`) | MIT |
| spaCy + `*_core_news_lg` (tokenizacja, lematyzacja) | 3.8.18 / 3.8.0 (jak `presidio-gliner`) | MIT / modele: GPL-3.0 (pl, es), MIT (en, de), LGPL-LR (fr) |
| Model `lgp-1.0-rc` („Legal Geek Privatizer (RC)”), paczka `1.0.0rc5`, kontener `.lgm` | kod ładowania z wydania **v1.3.0b24** (`6ed25e2ea415a02a4a93c000ee630bda34f19f3b`, jak `privatizer-model`) | własna (Legal Geek) |
| torch (CPU) / transformers | 2.14.0+cpu / 4.57.6 (jak `uv.lock` wydania) | BSD-3 / Apache-2.0 |
| numpy | 2.4.6 (rozwiązanie wspólne ze spaCy/thinc; `uv.lock` wydania: 2.5.4 – jak w `presidio-gliner`) | BSD-3 |

Anonimizatora Presidio na poziomie tekstu nie używamy (jak `presidio-gliner`): wynikiem są fragmenty z analizatora.

## Model: ładowany tak jak w `privatizer-model`

Ta sama ścieżka kodu co `privatizer-model` (KONFIG.md tamtego uczestnika): `engine.get_detector("lgp-1.0-rc")` – kontener
odszyfrowany w pamięci, sumy pozycji sprawdzone przez aplikację. Wag nie kopiujemy. Bez modelu proces nie wstaje (bez cichej
degradacji).

`LgpRecognizer.analyze` woła model jak `privatizer-model` (ta sama funkcja): wiersze
(`\r\n` → `\n`), okna modelu 2560/448 znaków (`det.chunk_chars`/`chunk_overlap` z kontenera), partie po 8, `Engine._map_back`,
kategorie zadane modelowi = domyślne świeżej instalacji w języku dokumentu (bez `WLASNE`), progi kategorii z trybu czułości
wydania (`balanced`). Bez reguł, pól, wyjątków i rozchodzenia powtórzeń. Encja Presidio = `LGP_` + kategoria Privatizera, na
którą adapter mapuje etykietę modelu (`LGP_OSOBA`, `LGP_NR_ID`…). Jeden załadowany model, rozpoznawacz zarejestrowany dla
każdego z 5 języków; analizator dostaje cały dokument (okna robi model; rozpoznawacze wzorcowe działają na całym tekście).
LGP ma własne okna wydania (wewnątrz detektora, 2560/448 znaków), więc pełny dokument jest przekazywany zgodnie z wydaniem;
`presidio-gliner` tnie dokument na okna 320 tokenów z zakładką 20% (w `GLiNERRecognizer`), więc rozpoznawacze wzorcowe i wzmacniacz
kontekstu `presidio-lgp` widzą tekst bez tego podziału – różnica poza NER, wpływ tylko na krawędzie okien `presidio-gliner`.

## Reszta Presidio – bez zmian względem `presidio-gliner`

Rozpoznawacze wzorcowe i krajowe per język z `../_wspolne/presidio_wspolne.py` (ten sam zestaw: `OGOLNE` + `KRAJOWE[jezyk]`,
telefon z regionem języka), NER spaCy wyłączony z rejestru, `default_score_threshold` 0 (filtr końcowy 0,30 – niżej).

**Próg.** Jak w `presidio-gliner`: filtr końcowy **0,30 dla całego wyjścia analizatora** (wynik rozpoznawaczy wzorcowych i
krajowych też, nie tylko NER) – jedyna różnica między `presidio-lgp` a `presidio-gliner` to rozpoznawacz NER (wraz z jego oknami – wyżej). Fragmenty modelu LGP
mają już progi kategorii wydania ≥ 0,30 (`balanced`, jak w `privatizer-model`), więc filtr nie zmienia wyniku modelu; działa na
wzorcach (np. daty 0,1–0,2, `IP` 0,1, słabe numery 0,05), dokładnie jak w `presidio-gliner`. Próg końcowy to `prog.json` **uczestnika `presidio-gliner`** (kalibracja grupy A
`pbench-kalibruj`; brak pliku → 0,30); sam `presidio-lgp` nie jest kalibrowany i własnego `prog.json` nie czyta. `PBENCH_SUROWE=1`
(podłoga 0,05) jak u pozostałych uczestników Presidio. `wynik` = pewność modelu LGP (adapter) albo wynik rozpoznawacza Presidio.

## Etykiety → kategorie gold (`etykiety.json`, J2)

- Encje rozpoznawaczy Presidio – jak w `presidio-spacy`/`presidio-gliner` (te same rozpoznawacze; krajowe tylko w języku, dla
  którego są zarejestrowane), bez `PERSON`/`ORGANIZATION`/`LOCATION`/`NRP` (NER spaCy wyłączony) i bez encji GLiNER-a.
- `LGP_<kategoria>` – jak `privatizer-model/etykiety.json` (kategorie etykiet taksonomii modelu, `OSOBA` obejmuje `INICJALY`,
  `NR_ID` – numery krajowe i podatkowe, `IDENTYFIKATOR` – także `NR_ID`, `KVNR`, `NHS`, `MBI`), w każdym języku.

## Dowód, co zmierzono (`wersje`)

`presidio-analyzer`, `spacy`, wersje modeli spaCy oraz – jak `privatizer-model` – `lgprivatizer`, `tag`, `commit`, `zrodla_sha`, `torch`, `transformers`, `numpy`, `model`, `paczka_modelu`, `folder_modelu`, `kontener_sha256`
(`a5c954f1…35611d`), `kontener_zgodny_z_rejestrem`, `wagi_model_safetensors_sha256` (`5d73972d…ce76b`, z nagłówka kontenera),
`adapter` (`MmbertBioDetector`), `czulosc`, `kanal`.

## Czego ten wariant NIE mierzy

Model LGP bez potoku aplikacji: bez reguł z sumami kontrolnymi Privatizera, pól formularzy, listy wyjątków, rozchodzenia
powtórzeń i drugiego przebiegu na wersalikach; Presidio nie scala fragmentów modelu z wzorcami tak jak `engine.merge`. To analiza
wkładu modelu w cudzym narzędziu, nie ocena produktu ani Presidio.

## Języki

Model LGP: jeden dla pl/en/es/de/fr; rozpoznawacz zarejestrowany dla wszystkich 5 – `jezyki_oficjalne` = wszystkie 5.

## Uruchomienie

Wymaga modelu `lgp-1.0-rc` załadowanego jak w `privatizer-model` (adapter niepubliczny). Próbka (3 dokumenty EN, 1 proces):
10–14 s na dokument.
