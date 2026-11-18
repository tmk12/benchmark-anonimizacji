# openai-privacy-filter

OpenAI Privacy Filter – `openai/privacy-filter` uruchamiany oficjalnym pakietem `opf`. Poziom: tylko **tekst**.

## Weryfikacja źródła (istnieją złośliwe klony)

- Repozytorium HF **`openai/privacy-filter`**: organizacja `openai` ma na HF znacznik **zweryfikowana** (`isVerified: true`, API
  `huggingface.co/api/organizations/openai/overview`), karta wskazuje repozytorium kodu `github.com/openai/privacy-filter`
  i demo `huggingface.co/spaces/openai/privacy-filter`; w repozytorium kodu (organizacja GitHub `openai`) licencja Apache-2.0.
- Rewizja HF przypięta: **`7ffa9a043d54d1be65afb281eddf0ffbe629385b`** (stan z 2026-10-30; ostatnia zmiana repozytorium 2026-04-22);
  `original/model.safetensors` sha256 `9c262cbe68a0c8a50590a648ef8341a2b7d3be1fa11dfb79893fe0b03ce57b5c`.
- Kod: `github.com/openai/privacy-filter` commit **`f7f00ca7fb869683eb732c010299d901457f19c3`** (HEAD `main`), instalowany z gita przez
  `pyproject.toml` / `uv.lock` (pakiet `opf` 0.1.0).
- Licencja: **Apache-2.0** (metadane karty, plik LICENSE repozytorium kodu) – brak ograniczeń użycia komercyjnego i porównań.

## Wersje (przypięte, `uv.lock` w repo)

torch 2.15.0+cpu, tiktoken 0.14.0, numpy 2.5.4, safetensors 0.8.0, huggingface_hub 2.4.0, opf 0.1.0 (commit wyżej). Wagi w
`vendor/hf` (HF_HOME, tylko podkatalog `original/` – format `opf`, bez ONNX), potem `HF_HUB_OFFLINE=1`. Słownik tiktoken `o200k_base`
(wskazany w `original/config.json`, `"encoding": "o200k_base"`) leży w `vendor/tiktoken` (`TIKTOKEN_CACHE_DIR`; pierwszy start wymaga
sieci, pobiera plik z publicznego magazynu OpenAI, jak robi to sam `opf`).

## Źródło „najlepszej konfiguracji”

Karta modelu i README repozytorium kodu: <https://huggingface.co/openai/privacy-filter>, <https://github.com/openai/privacy-filter>.
- **Dekodowanie:** ograniczony **Viterbi** BIOES z `viterbi_calibration.json` (punkt pracy `default`, wszystkie 6 biasów = 0) – domyślne dla
  `opf` (`decode_mode="viterbi"`); autorzy podają, że zastępuje niezależny argmax. Punktów pracy o większej czułości nie dobieramy
  (kalibracja progów dotyczy `wynik` i jest w zad. 16; biasy Viterbiego zostają domyślne).
- Przycinanie białych znaków ze spanów (`trim_whitespace=True`, domyślne), CPU, typy etykiet bez zwijania (`output_mode="typed"`).
- **Okno:** karta: kontekst 128 000 tokenów (`default_n_ctx`), uwaga pasmowa ±128 tokenów (efektywne okno 257). Pakiet `opf` na CPU
  domyślnie używa **4096** tokenów (`_resolve_n_ctx`: „safer context size”) – tyle samo przyjmujemy. Tekst dzielony na okna po 4096 tokenów
  tiktoken z zakładką 12,5% (512 tokenów); każdy token bierze logity z okna, w którym leży dalej od sztucznej krawędzi (środek zakładki
  dzieli sąsiadów), potem **jedno** dekodowanie Viterbiego po całym dokumencie – bez sklejania spanów z okien. Offsety znakowe z
  `decode_text_with_offsets`. Jak w `opf` (`decoded_mismatch`) różnica treści po dekodowaniu (niesparowane surrogaty → U+FFFD) nie przerywa dokumentu, bo długość w znakach
  się zgadza i offsety pozostają dokładne; inna długość to realny błąd (`blad` dokumentu, nie maskujemy). Test: emoji i znaki łączące (surrogaty nie występują w korpusie z plików UTF-8 i nie przejdą protokołu JSONL). Różnica wobec `opf redact`: okna z zakładką
  zamiast ciętych bez zakładki (rozstrzygnięcie 3); dla tekstów < 4096 tokenów wynik identyczny z oficjalnym.
- **Szybsza warstwa MoE (jedyne odstępstwo od kodu autorów):** referencyjna ścieżka CPU `opf` dla każdego tokenu kopiuje wagi 4 ekspertów
  i mnoży je przez `bmm` – ~100-400 s na dokument ~600 tokenów przy 1 wątku (zmierzone), co uniemożliwia przebieg korpusu. `run.py`
  podmienia `MLPBlock.forward` na wersję liczącą to samo w float32 zgrupowaną po ekspertach (jedno `matmul` na eksperta; ta sama
  bramka top-4, softmax, SwiGLU, zaokrąglenie wyjścia do dtype aktywacji; zmienia się tylko kolejność sumowania). Wynik: ok. 10-15x szybciej.
  Równoważność sprawdza test `test_openai_privacy_filter_szybkie_moe_rownowazne_z_kodem_autorow` (`PBENCH_MOE_ORYGINAL=1` = kod autorów:
  te same spany, różnica `wynik` < 0,02; na dokumencie DE 0,0016). Wersja podmiany zapisana w `wersje.json` (`moe`).
- **Wynik (`wynik`):** `opf` nie zwraca pewności. Podajemy średnie prawdopodobieństwo (softmax) przypisanych tagów BIOES po tokenach spanu
  – potrzebne do kalibracji. Próg domyślny autorów: brak (twarde dekodowanie), więc domyślnie podłoga 0.05; `prog.json` / `PBENCH_SUROWE=1`
  jak u pozostałych.

## Etykiety (8 kategorii modelu, nie można ich zmieniać w czasie działania – „static label policy”) → kategorie gold

| Etykieta modelu | Kategorie gold |
|---|---|
| private_person | OSOBA, INICJALY |
| private_address | ADRES |
| private_email | EMAIL |
| private_phone | TELEFON |
| private_url | URL |
| private_date | DATA_UR, DATA |
| account_number | RACHUNEK, KARTA, numery identyfikacyjne (PESEL, NIP, REGON, KRS, DOWOD, PASZPORT, PRAWO_JAZDY, NR_ID, SSN, DNI, NUSS, NIR, SIREN, VAT, CIF, EIN, NR_PODATKOWY, SVNR, KVNR, NHS, NINO, MBI, NR_REJESTRU, IDENTYFIKATOR) |
| secret | SEKRET |

Mapowanie (`etykiety.json`) służy tylko mierze pomocniczej „w deklarowanym zakresie”; żadne wykrycie nie jest odrzucane. Model nie ma
etykiety organizacji, kwoty, zdrowia, rejestracji pojazdu – te kategorie są poza jego zakresem. Samodzielne miejscowości, regiony,
państwa i kody pocztowe, adres IP i login też poza zakresem (zakres deklarowany wg reguły `metodyka/zakres-gold.md` pkt 4 (J2)): karta wymienia maskowanie
lokalizacji jako błąd nadmiarowy („over-redaction of … locations”), a adres IP ani login nie są adresem URL ani sekretem.

## Języki

Karta: „Primarily English; selected multilingual robustness evaluation reported” („Performance may drop on non-English text”) – bez listy
języków. `jezyki_oficjalne = ["en"]`. Ruling R37: uruchamiany na wszystkich 5 językach (`jezyki`); sędzia oznacza dokumenty flagą
`w_zakresie_oficjalnym`.

## Czasy (maszyna silnie obciążona innymi sesjami, load 40-90; 1 wątek)

Dokument ~2000 znaków: ~10-30 s (kod autorów: 100-390 s). Tabele ~20 tys. znaków (okna po 4096 tokenów): do ~200 s. `timeout_s` = 1800.
