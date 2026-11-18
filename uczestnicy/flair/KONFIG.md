# flair

**Flair** (flairNLP, <https://github.com/flairNLP/flair>) z modelem **`flair/ner-multi`** – standardowy 4-klasowy NER dla czterech
języków CoNLL (LSTM-CRF na osadzeniach znakowych Flair + GloVe/FastText). Ogólny NER, nie detektor PII. Grupa B (bez kalibracji).
Poziom: tylko **tekst**.

## Wersje (przypięte, `uv.lock` w repo)

| Składnik | Wersja / rewizja | Licencja |
|---|---|---|
| flair | 0.15.1 | MIT |
| segtok (podział na zdania) | 1.5.11 | MIT |
| torch (CPU) / transformers | 2.15.0+cpu / 4.57.6 | BSD-3 / Apache-2.0 |
| `flair/ner-multi` | rewizja HF `efbff7533ea394ebf7c0b4877ad13b8e42a76922`, `pytorch_model.bin` sha256 `9e73a46f5156d8602bde5c1d0d60e658e0dc00339949ca3dfcada6188f28678c` (1,72 GB) | brak pola licencji w karcie; model jest „standardowym modelem dostarczanym z Flair” (karta), biblioteka MIT; dane treningowe CoNLL-03/02 – jak modele CoNLL w grupie A (`dslim/bert-large-NER`, XLM-R CoNLL-03 niemiecki) |

Repozytorium oficjalne (organizacja `flair` na HF, bez bramki). Model pobrany raz do `vendor/hf` (suma zgodna z LFS oid HF), potem
offline. Plik to pickle torch (ładowany przez `SequenceTagger.load`) – źródło oficjalne, rewizja i suma przypięte.

## Konfiguracja – wg karty modelu i samouczka Flair

Karta (<https://huggingface.co/flair/ner-multi>): `SequenceTagger.load("flair/ner-multi")`, `tagger.predict(sentence)`,
`sentence.get_spans("ner")`. Dla całych tekstów – samouczek Flair „How to tag a whole corpus”
(<https://flairnlp.github.io/docs/tutorial-basics/how-to-tag-corpus>): `SegtokSentenceSplitter().split(tekst)` →
`tagger.predict(zdania)`. Offset znakowy wykrycia = `Sentence.start_position` (pozycja zdania w tekście, ustawiana przez dzielnik)
+ `Span.start_position`. Model nie ma limitu tokenów – bez okien. Ładowanie z lokalnej ścieżki przypiętej migawki
(`snapshot_download(…, revision=…)`), co odpowiada `SequenceTagger.load("flair/ner-multi")` bez sieci.

## Etykiety → kategorie gold (`etykiety.json`)

PER → OSOBA; LOC → MIEJSCOWOSC, REGION, KRAJ, MIEJSCE_UR; ORG → ORGANIZACJA. **MISC** („other name”: narodowości, wydarzenia, nazwy
własne innego typu) nie jest zwracany – jak `labels_to_ignore` MISC w Presidio i pominięte typy w `stanza`. Wynik = pewność spanu
z Flair; Flair nie stosuje progu (domyślny 0, podłoga protokołu 0.05, `prog.json`/`PBENCH_SUROWE=1` jak w grupie A).

## Języki

Uruchamiany na 5 językach (R37). Oficjalnie (karta): **en, de, es** (oraz nl, poza korpusem); francuski „kind of works” – poza
oficjalnymi; polskiego model nie zna.

## Uwagi

* Start: ładowanie modelu ~30 s. Długie tabele bez interpunkcji (listy płac) dają bardzo długie „zdania” – `timeout_s` 1800.
