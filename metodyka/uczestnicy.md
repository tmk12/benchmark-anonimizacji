# Uczestnicy benchmarku – decyzje o doborze

Szczegóły konfiguracji każdego uczestnika: `uczestnicy/<id>/KONFIG.md`. Ten plik zbiera decyzje o tym, kto bierze udział.

## Rozważeni i odrzuceni

| Kandydat | Decyzja | Powód |
|---|---|---|
| `iiiorg/piiranha-v1-detect-personal-information` (Piiranha, mDeBERTa, en/de/fr/es/it/nl) | rozważony, odrzucony – licencja CC-BY-NC-ND 4.0 (niekomercyjna) | Licencja zabrania użycia komercyjnego, a opublikowane porównanie firmy mogłoby je za takie uchodzić. Model nie został pobrany ani uruchomiony. |
| Anonimizator CLARIN-PL (`gitlab.clarin-pl.eu/nlpworkers/anonymizer`, commit `e8c11a21c62ed1a3b63bbdebb3c231831403dadd`, 2026-09-22) | rozważony, odrzucony – brak licencji i brak samodzielnego uruchomienia lokalnie | Repozytorium nie ma pliku licencji (drzewo sprawdzone rekurencyjnie, GitLab: `license: null`) – bez licencji nie wolno go uruchamiać w publicznym porównaniu. Ponadto repozytorium ma własne tylko detektory wzorcowe (`src/detectors/{date,email,phone,url,number,user}`, tylko pl), a NER pochodzi wyłącznie z usług CLARIN-PL: anonimizator czyta gotowe adnotacje NER z łańcucha usług CLARIN (`any2txt → morphodita → liner2 (model 5nam) → anonymizer`, CCL) albo JSONL z workerów `wiktorner`/GLiNER uruchamianych przez LPMN (usługi sieciowe CLARIN-PL); zależności `lpmn_client_biz`, `nlp-ws` – z indeksu `pypi.clarin-pl.eu`. Lokalnie na CPU, bez usług sieciowych, uruchomić się go nie da. |
| Liner2 (CLARIN-PL, `github.com/CLARIN-PL/Liner2`) | rozważony, odrzucony – ogólny NER, a nie anonimizator; martwy i trudny do uruchomienia | Ostatnia zmiana 2023-06-05; Java 8 + CRF++ (kompilacja natywna) i wejście CCL z tagera morfologicznego (WCRFT/MorphoDiTa) – osobny łańcuch narzędzi i modeli z repozytorium CLARIN. Polski NER CLARIN-PL jest w benchmarku reprezentowany przez `clarin-pl/FastPDN` (kandydat porównany przy wyborze modelu `presidio-pl-ner`, `uczestnicy/presidio-pl-ner/KONFIG.md`). |
| pakiet `ai4privacy` z PyPI (0.5.0, dekodowanie własne autorów) | rozważony, odrzucony – brak licencji otwartej; w benchmarku tylko sam model | Plik `LICENSE` pakietu: „All rights reserved.”; repozytorium z metadanych (`github.com/MikeDoes/ai4privacy`) niedostępne publicznie. Model, który pakiet ładuje (`ai4privacy/llama-ai4privacy-multilingual-categorical-anonymiser-openpii`), ma licencję MIT – uczestnik `ai4privacy` uruchamia go standardowym potokiem transformers (adnotacja w `uczestnicy/ai4privacy/KONFIG.md`). |
| pakiet `pdf-redactor` 0.0.1 z PyPI | zastąpiony kodem z repozytorium autorów | Opublikowany z forka `vitalbeats/pdf-redactor`, nie przez autorów – uczestnik `pdf-redactor` instaluje `JoshData/pdf-redactor` z przypiętego commitu. |

## Odstępstwa od kodu i domyślnej konfiguracji autorów

| Uczestnik | Odstępstwo | Powód i dowód równoważności |
|---|---|---|
| `openai-privacy-filter` | Warstwa MoE na CPU podmieniona na wersję zgrupowaną po ekspertach (float32), zamiast referencyjnej ścieżki `opf` (kopiowanie wag 4 ekspertów na token + `bmm`). Okna 4096 tokenów z zakładką 12,5% i jedno dekodowanie Viterbiego po dokumencie (`opf` tnie bez zakładki). | Referencyjna ścieżka liczyła 100-390 s na dokument ~600 tokenów (1 wątek), co uniemożliwiało przebieg korpusu; wersja zgrupowana jest ok. 10-15x szybsza. Ta sama arytmetyka (bramka top-4, softmax, SwiGLU, zaokrąglenie), zmienia się tylko kolejność sumowania. Test porównuje ją z kodem autorów (`PBENCH_MOE_ORYGINAL=1`) na krótkim i długim tekście: identyczne spany, różnica wyniku < 0,02 (0,0016 na dokumencie DE); wariant zapisany w `wersje.json` (`moe`). |
| `stanza` | Polski: model `nkjp_bert` zamiast `nkjp` z pakietu `default_accurate`. Zwracane tylko typy odpowiadające kategoriom gold (uzasadnienie każdego pominiętego typu w `KONFIG.md`). | `nkjp_bert` jest oficjalnym modelem wydania 1.15.0 (szkielet `allegro/herbert-base-cased`, CC-BY-4.0, rewizja przypięta); pakiety autorów go nie wybierają, a „najlepsza uczciwa konfiguracja” wymaga najlepszego dostępnego modelu. Stanza to ogólny NER, nie detektor PII. |

## Język zastępczy (ukraiński)

Dokumenty warstwy trudnej po ukraińsku (`uk`) dostaje każdy uczestnik – także ten, który ukraińskiego nie deklaruje (w tym pomiarze:
wszyscy). Reguła jest jedna dla wszystkich (`pbench.uruchom.JEZYKI_ZASTEPCZE`, `jezyk_uzyty`): uczestnik deklarujący `uk`
przetwarza dokument jako `uk`; inny – w pierwszym zadeklarowanym języku z listy **pl, en, de, es, fr**. Polski jest pierwszy, bo
z pięciu języków benchmarku jest ukraińskiemu najbliższy (język słowiański; osoby z Ukrainy w korpusie mają też zapisy w polskiej
transliteracji), angielski – drugi, bo to język domyślny większości narzędzi. Zapytanie protokołu niesie język użyty, a wynik
surowy (`wyniki/surowe/<id>/<split>/<poziom>.jsonl`) i rekord oceny – pole `jezyk_uzyty` obok `jezyk` dokumentu. Dokument nie
jest „nieobsługiwany” (`pominiety`), jeśli uczestnik ma jakikolwiek język z listy; ukraiński jest poza T4 (`punktacja.md`).

## Kalibracja progów grupy A

Grupa A: pełna kalibracja progu na części dev (`pbench.kalibracja`, `pbench-kalibruj`). Miara: średnia `char_f2` dokumentów dev
liczona sędzią tekstowym tą samą funkcją co `pbench-ocen`, wszystkie języki razem (jeden próg na uczestnika), siatka 0,01–0,04 co 0,01 i 0,05–0,95 co
0,05, remis → wyższy próg. Procedura i tabela progów: `metodyka/prerejestracja.md`, pkt 4 (kalibracja na dev, przed zamrożeniem). Surowe wyniki dev zbiera się w trybie podłogi (`PBENCH_SUROWE=1`: próg 0,01, uczestnik zwraca wykrycia
ze swoimi wynikami pewności). Privatizer nie jest kalibrowany (mierzymy wydanie).

| Uczestnik | Kalibracja | Uzasadnienie (sprawdzone w `run.py`) |
|---|---|---|
| `presidio-spacy` | **kalibrowany** | wynik rozpoznawaczy Presidio (spaCy NER, wzorce); filtr `wynik >= prog` po analizatorze |
| `presidio-pl-ner` | **kalibrowany** | jak wyżej; jego `prog.json` dziedziczą uczestnicy plikowi grupy B |
| `presidio-gliner` | **kalibrowany** | wynik GLiNER-a i rozpoznawaczy Presidio; domyślny autorów 0,30 |
| `gliner-nvidia-pii` | **kalibrowany** | wynik spanu GLiNER (model uruchamiany przy 0,05, filtr `prog.json` po scaleniu okien); domyślny 0,30 |
| `gliner-urchade-pii` | **kalibrowany** | jak wyżej; domyślny 0,50 |
| `gliner-knowledgator-pii` | **kalibrowany** | jak wyżej; domyślny 0,30 |
| `openai-privacy-filter` | **kalibrowany** | wynik własny = średnie prawdopodobieństwo tagów BIOES spanu (autorzy: Viterbi bez progu) |
| `stanza` | bez kalibracji | NER nie zwraca pewności spanów (`wynik` = 1,0): próg nie ma wpływu, `kalibruj` zwraca None |
| `presidio-lgp` (aneks) | dziedziczy | próg końcowy = `prog.json` `presidio-gliner` (`KATALOG_GLINER` w `run.py`); ta sama konfiguracja Presidio, inny rozpoznawacz NER |
| `privatizer-tekst-gliner` (aneks) | dziedziczy | `prog.json` `gliner-nvidia-pii` (`detektor_krzyzowy.prog_samodzielnego`) |
| `privatizer-tekst-opf` (aneks) | dziedziczy | `prog.json` `openai-privacy-filter` (jw.) |
| `presidio-wrapper-plikowy`, `pdf-redactor`, `presidio-image-redactor` (grupa B) | dziedziczą | `prog.json` `presidio-pl-ner` (`presidio_plikowe`) |
| `scrubadub`, `flair`, `ai4privacy` (grupa B, tekst) | bez kalibracji | domyślne ustawienia autorów |

## Grupa B – konfiguracja z dokumentacji autorów, bez kalibracji (z jednym wyjątkiem)

Uczestnicy grupy B biegną w najlepszej konfiguracji opisanej przez autorów (źródło w `KONFIG.md` każdego), **bez kalibracji progu
na dev** – w tabelach wyników oznaczeni jako grupa B. Plikowi wykrywają dane analizatorem w konfiguracji `presidio-pl-ner`
(kod ładowany z `uczestnicy/presidio-pl-ner/run.py` przez `uczestnicy/_wspolne/presidio_plikowe.py`, te same wersje zależności)
i zgłaszają rzeczywistą ścieżkę zapisanego pliku (R42).

**Wyjątek od „bez kalibracji”:** grupa B bez kalibracji, z wyjątkiem uczestników plikowych opartych na konfiguracji `presidio-pl-ner`
(`presidio-wrapper-plikowy`, `pdf-redactor`, `presidio-image-redactor`), które dziedziczą jej próg (`uczestnicy/presidio-pl-ner/prog.json`,
gdy kalibracja grupy A go zapisze; inaczej domyślny autorów). Konfiguracja bazowa = Presidio + pl-NER także po jego kalibracji; sam
wrapper, pdf-redactor ani redaktor obrazów nie mają własnych parametrów do kalibracji. Uczestnicy tekstowi (`scrubadub`, `flair`,
`ai4privacy`) zostają przy domyślnych ustawieniach autorów.

| Uczestnik | Poziom, formaty | Narzędzie i konfiguracja | Języki oficjalne | Licencja |
|---|---|---|---|---|
| `scrubadub` | tekst | scrubadub 2.0.1, `Scrubber(locale=…)` – detektory domyślne (e-mail, URL, telefon, karta, dane logowania, Twitter; `en_US` + SSN), bez detektorów nazwisk – punkt odniesienia „same regexy” | en | Apache-2.0 |
| `flair` | tekst | Flair 0.15.1, `flair/ner-multi` (PER/LOC/ORG; MISC pominięte), podział na zdania Segtok – ogólny NER | en, es, de | MIT (biblioteka); model `flair/ner-multi`: brak licencji w karcie modelu – zostaje z adnotacją w raporcie, wagi nie są redystrybuowane (`znane-ograniczenia.md` w repozytorium kodu) |
| `ai4privacy` | tekst | model `ai4privacy/llama-ai4privacy-multilingual-categorical-anonymiser-openpii` w potoku `token-classification` transformers (`simple`), okna 512 – **sam model, bez pakietu autorów** (pakiet bez licencji otwartej) | en, es, de, fr | MIT (model); zbiór treningowy `ai4privacy/open-pii-masking-500k-ai4privacy`: CC-BY-4.0 (karta zbioru: `license: other`, `license_name: cc-by-4.0`) |
| `presidio-image-redactor` | plik: skan | Presidio Image Redactor 0.0.62: strony PDF → obrazy 300 dpi → OCR Tesseract (język dokumentu) + analizator `presidio-pl-ner` → czarne prostokąty → PDF | pl, en, es, de, fr | MIT |
| `pdf-redactor` | plik: pdf | `JoshData/pdf-redactor` @ `12ad5c68`: wyrażenia regularne z wartości wykrytych analizatorem `presidio-pl-ner` (tekst z PDFium) → zamiana na `X` w warstwie tekstu, czyszczenie Info/XMP; rozpakowanie i linearyzacja biblioteką qpdf (pikepdf) jak w README | pl, en, es, de, fr | CC0-1.0 |
| `presidio-wrapper-plikowy` | plik: docx, xlsx, pptx | **nasz naiwny wrapper** (nie produkt): analizator `presidio-pl-ner` + `presidio-anonymizer` (`<TYP>`) na akapitach i komórkach tabel (python-docx), komórkach tekstowych (openpyxl), akapitach kształtów (python-pptx) | pl, en, es, de, fr | MIT (składniki) |

**Naiwny wrapper w raporcie.** `presidio-wrapper-plikowy` jest opisany jako wzorzec **„co zostaje, gdy anonimizuje się tylko
tekst”**: Presidio analizuje tekst, a nie pliki, więc integrator sam wyciąga i podmienia tekst – tak, jak w publicznych
przykładach (źródła w `KONFIG.md`), czyli bez nagłówków, stopek, przypisów, komentarzy, śledzonych zmian, notatek i metadanych.
Wynik pokazuje skalę danych poza zasięgiem takiego kodu; nie jest oceną Presidio ani żadnego produktu.

## Warianty „Maksymalna ochrona” (aneks)

**Ranking mierzy tryb domyślny Privatizera** (świeża instalacja, czułość `balanced`, `KWOTA`
wyłączona), a tryb „Maksymalna ochrona” jest w **aneksie, poza rankingami** (`aneks = true`, jak warianty krzyżowe poniżej).

| Uczestnik | Co to jest | Pytanie, na które odpowiada |
|---|---|---|
| `privatizer-tekst-maks` | Potok `privatizer-tekst` (ten sam kod `run.py`, wydanie i model), przed startem serwera tryb ustawiony funkcją aplikacji `settings.save({"sensitivity": "privacy"})` | Ile zmienia tryb „Maksymalna ochrona” (czułość modelu, wygaszone skróty, kwoty pieniężne) względem trybu domyślnego |
| `privatizer-plik-maks` | Jak wyżej dla `privatizer-plik` (plik → plik) | Jak wyżej, na plikach |

Zasady: tryb nie jest dostrajany ręcznie – ustawia go funkcja aplikacji, która sama dokłada `KWOTA`; opcje zadania niosą kategorie
profilu języka plus `KWOTA`, bo opcje zadania nadpisują kategorie z ustawień (`server._options`). `KWOTA` jest w **zakresie gold**
wariantów maks (`etykiety.json`, `zakres-gold.md`). Wariant wymaga wydania ≥ v1.3.0b22 (wcześniejsze nie włączają kwot trybem –
uczestnik przerywa start). Warianty nie są mierzone czasem. Szczegóły: `uczestnicy/privatizer-*-maks/KONFIG.md`.

## Warianty krzyżowe (aneks)

Trzy warianty rozdzielają wkład **modelu** i **potoku aplikacji** (reguły, pola, scalanie,
lista wyjątków, rozchodzenie powtórzeń, maskowanie). Jak warianty ablacyjne (`privatizer-reguly`) są w **aneksie, poza
rankingami** (`punktacja.md`): deklaracja `aneks = true` w `uczestnik.toml` (pole opcjonalne, domyślnie `false`; orkiestrator
zapisuje je w `wyniki/surowe/<id>/wersje.json`, agregacja wyłącza takich uczestników z rankingów i pokazuje ich osobno).

| Uczestnik | Co to jest | Pytanie, na które odpowiada |
|---|---|---|
| `presidio-lgp` | Presidio jak `presidio-gliner` (spaCy do tokenizacji, te same rozpoznawacze wzorcowe i krajowe), rozpoznawacz NER = model Legal Geek Privatizer (RC) ładowany jak w `privatizer-model`; **ten sam próg końcowy co `presidio-gliner` dla całego wyjścia analizatora** (domyślny 0,30; po kalibracji – `prog.json` `presidio-gliner`) – jedyna różnica konfiguracji to rozpoznawacz NER (i jego okna: LGP ma własne okna wydania wewnątrz detektora) | Ile daje model LGP bez potoku Privatizera, w otoczeniu otwartego narzędzia (porównanie z `presidio-gliner`, `presidio-spacy`) |
| `privatizer-tekst-gliner` | Potok `privatizer-tekst` (wydanie bez zmian), detektor modelu podmieniony na GLiNER `nvidia/gliner-PII` | Ile daje potok Privatizera przy obcym modelu (porównanie z `gliner-nvidia-pii` i `privatizer-tekst`) |
| `privatizer-tekst-opf` | Jak wyżej, detektor = OpenAI Privacy Filter (`openai/privacy-filter`) | Jak wyżej, dla modelu o innej architekturze i stałym zestawie 8 etykiet |

Zasady:
- **Konfiguracja uczestnika samodzielnego.** Każdy model dostaje etykiety, próg i okna swojego uczestnika samodzielnego (kod ładowany z jego `run.py`;
  próg z jego `prog.json` po kalibracji). Model LGP – progi kategorii z trybu czułości wydania, okno z kontenera, jak w
  `privatizer-model`. Tylko oficjalne źródła modeli, rewizje i sumy wag przypięte i sprawdzane przy starcie.
- **Kod Privatizera bez zmian.** Obcy model wchodzi przez interfejs `Detector` wydania (`detect/base.py`): w procesie serwera
  aplikacji `detect.backends.BACKENDS` wskazuje fabrykę uczestnika (`uczestnicy/_wspolne/detektor_krzyzowy.py`), potem
  aplikacja startuje jak zwykle. Model LGP nie jest wtedy w ogóle dostępny (folder modelu bez kontenera, bez klucza treści),
  a `wersje.json` niesie dowód z procesu serwera: rewizję i sumę wag obcego modelu.
- **Czas i wątki.** Warianty w potoku respektują ustawienie wątków orkiestratora (`OMP_NUM_THREADS` = `--watki`, jak uczestnicy
  samodzielni), nie politykę wydania (połowa wątków logicznych). Przekroczenie czasu liczy się jako dokument z wyciekiem
  (`punktacja.md`), więc `timeout_s` wariantu z obcym modelem dobiera się pomiarem: czas na 5 najdłuższych dokumentach dev
  (tekst) i limit z zapasem co najmniej ×2 względem najdłuższego (pomiar zapisany w `KONFIG.md` uczestnika); raport aneksu podaje
  liczbę przekroczeń czasu osobno od wycieków.
- **Języki oficjalne** wariantu = języki modelu NER (karta modelu), nie potoku: `privatizer-tekst-gliner` i `-opf` mają `en`
  (jak ich uczestnicy samodzielni), `presidio-lgp` 5 języków modelu LGP (jak `privatizer-model`), choć `presidio-gliner` ma 4
  z karty swojego GLiNER-a.
- **Agregacja** czyta `aneks` z `uczestnik.toml` (nie tylko z `wersje.json`): przebiegi bez tego pola (np. `privatizer-reguly`)
  nie mają pola w `wersje.json`, a mają być w aneksie.
- **Mapowanie etykiet obcego modelu na kategorie Privatizera** jest jawne (`KATEGORIE` w `detektor.py` uczestnika): jedna
  kategoria na etykietę, etykiety wielu kategorii → kategoria ogólna (`NR_ID`, `IDENTYFIKATOR`), jak w adapterze modelu wydania.

Czego warianty krzyżowe **nie** mierzą:
- wejście obcego modelu różni się od samodzielnego: silnik oddaje tekst ze spłaszczonymi białymi znakami (wiersze sklejone
  spacją; drugi przebieg – znak nowej linii), a uczestnik samodzielny dostaje surowy tekst z `\n` – dla modeli z tokenizerem
  uwzględniającym nowe linie (OPF, tiktoken) to inne tokeny; kontrakt `Detector` wydania tego nie pozwala obejść;
- obcy model w potoku Privatizera nie ma kalibracji Privatizera (progi per kategoria, tryby czułości, kandydaci poniżej progu
  potwierdzani w dokumencie), taksonomii etykiet prawniczych ani okna dobranego do modelu, a potok był strojony pod model LGP –
  słabszy wynik nie znaczy, że model jest gorszy samodzielnie, a lepszy – że potok jest „uniwersalny”;
- model LGP w Presidio nie ma reguł z sumami kontrolnymi Privatizera, scalania (`engine.merge`), pól, wyjątków i rozchodzenia
  powtórzeń – to nie jest ocena żadnego produktu (ani Privatizera, ani Presidio).

To **analiza wkładu** składników, nie porównanie produktów; raport pokazuje te wyniki osobno, z tym zastrzeżeniem.
