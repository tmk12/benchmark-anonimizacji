# presidio-wrapper-plikowy

**Nasz naiwny wrapper plikowy – nie produkt.** Microsoft Presidio (analizator w konfiguracji `presidio-pl-ner`) + podmiana tekstu
w DOCX/XLSX/PPTX typowymi bibliotekami Pythona. Grupa B (bez kalibracji). Poziom: **plik**; formaty: docx, xlsx, pptx.

W raporcie opisywany jako wzorzec **„co zostaje, gdy anonimizuje się tylko tekst”**: tak wygląda typowa integracja Presidio
z dokumentami biurowymi (Presidio analizuje i zamienia tekst, a nie pliki), a jej wynik pokazuje, ile danych zostaje w miejscach,
do których taki kod nie sięga. Wynik nie jest oceną Presidio ani żadnego produktu.

## Wersje (przypięte, `uv.lock` w repo)

| Składnik | Wersja | Licencja |
|---|---|---|
| presidio-analyzer / presidio-anonymizer | 2.2.366 / 2.2.366 | MIT |
| python-docx | 1.2.0 | MIT |
| openpyxl | 3.1.5 | MIT |
| python-pptx | 1.0.2 | MIT |
| spaCy, transformers, torch (CPU), modele NER | jak w `presidio-pl-ner` (te same wersje – pilnuje test `test_plikowi_maja_wersje_presidio_pl_ner`) | zob. `../presidio-pl-ner/KONFIG.md` |

## Wykrywanie

Analizator **dokładnie jak `presidio-pl-ner`**: kod konfiguracji (`zbuduj`, modele i rewizje z `modele.json`, rozpoznawacze PL
z sumą kontrolną, okna tokenowe, próg z `presidio-pl-ner/prog.json`) ładowany wprost z `../presidio-pl-ner/run.py` przez
`../_wspolne/presidio_plikowe.py` (bez kopii, więc konfiguracje nie mogą się rozjechać). Wykrycia → `presidio-anonymizer`
z operatorem domyślnym (`replace` → `<TYP_ENCJI>`, np. `<PERSON>`). `etykiety.json` = jak w `presidio-pl-ner` (wrapper zamienia
wszystko, co analizator wykryje).

## Podmiana w plikach – wzorzec typowego integratora (źródła)

| Format | Co wrapper robi | Źródło wzorca |
|---|---|---|
| DOCX | akapity treści głównej (`Document.paragraphs`) i komórki tabel (`Document.tables` → wiersze → komórki, komórka scalona raz); akapit z wykryciem: stare przebiegi usunięte (`paragraph.clear()`), tekst po anonimizacji w jednym nowym przebiegu; komórka: `cell.text = …` | projekt „document_redaction” (seanpedrickcase, Presidio + python-docx), funkcja `handle_docx_anonymisation` w `tools/data_anonymise.py`, rewizja `2de2455a39db2de99f71945b0ed59c178997dbe3` (<https://huggingface.co/spaces/seanpedrickcase/document_redaction>): ten sam podział (akapity + komórki tabel), ta sama zamiana (`element.clear(); element.add_run(new_text)` / `cell.text = new_text`), bez nagłówków, stopek i metadanych. Kod nie jest kopiowany (projekt na AGPL-3.0) – wzorzec opisany i napisany od nowa. |
| XLSX | wszystkie arkusze (`workbook.worksheets`), `iter_rows()`, komórki tekstowe (`data_type == "s"`) → `cell.value = …`; formuły i liczby bez zmian | dokumentacja openpyxl, „Tutorial” (<https://openpyxl.readthedocs.io/en/3.1/tutorial.html>): `load_workbook`, `iter_rows`, `cell.value`, `save` |
| PPTX | slajdy → kształty z ramką tekstu (`shape.has_text_frame`) → akapity; akapit z wykryciem: `paragraph.text = …` (setter zastępuje przebiegi jednym) | dokumentacja python-pptx, „Getting Started” → „extract all text from slides in presentation” (<https://python-pptx.readthedocs.io/en/latest/user/quickstart.html>): pętla `slides` → `shapes` → `has_text_frame` → `paragraphs` |

Jednostką analizy jest akapit / komórka (jak w źródłach): kontekst zdania zostaje, kontekst dokumentu – nie.

**Czego wrapper świadomie NIE dotyka** (typowe przykłady też nie): nagłówki i stopki, przypisy, komentarze, śledzone zmiany
(`w:del`), pola i kody pól, pola tekstowe/kształty w DOCX, tabele zagnieżdżone, hiperłącza jako adresy, metadane
(`docProps/core.xml`: autor, tytuł…), w XLSX – komentarze, nazwy arkuszy, nagłówki/stopki wydruku, pamięć podręczna tabel
przestawnych, metadane (ukryte arkusze i wiersze są przetwarzane jak zwykłe – `worksheets` je zawiera); w PPTX – tabele, grupy
kształtów, wykresy, notatki prelegenta, układy i wzorce slajdów, metadane. Element bez wykrycia zostaje nietknięty
(formatowanie przebiegów zachowane).

## Format wyniku (R42)

Ten sam format co wejście (`.docx`/`.xlsx`/`.pptx`); uczestnik zwraca rzeczywistą ścieżkę zapisanego pliku. Błąd odczytu lub
zapisu = `blad` (dla sędziego brak pliku wynikowego).

## Języki, próg

Jak `presidio-pl-ner`: uruchamiany na 5 językach (R37), oficjalnie wszystkie 5. Próg: `presidio-pl-ner/prog.json`, gdy istnieje
(kalibracja grupy A dotyczy analizatora), inaczej domyślny autorów (0, podłoga 0.05). Sam wrapper nie ma parametrów do kalibracji.

**Wyjątek od „bez kalibracji” (grupa B):** próg jest dziedziczony z konfiguracji bazowej `presidio-pl-ner` także po jej kalibracji
(zob. `metodyka/uczestnicy.md`, sekcja grupy B).

## Uwagi

* Start ładuje pięć modeli NER (`start_timeout_s` 900); analiza akapit po akapicie – listy płac XLSX (setki komórek) najdłużej
  (`timeout_s` 1800).
