# stanza

Stanza (Stanford NLP Group) – **ogólny NER** (osoby, organizacje, miejsca, daty, kwoty) dla 5 języków korpusu. Poziom: tylko **tekst**.

> **To nie jest detektor PII.** Stanza ma modele rozpoznawania jednostek nazwanych wytrenowane na korpusach newsowych/encyklopedycznych
> (NKJP, OntoNotes, CoNLL02, GermEval2014, WikiNER) i nie wykrywa e-maili, telefonów, numerów dokumentów, rachunków ani adresów
> ulicznych. Jest w benchmarku jako **baza odniesienia „co daje zwykły NER”**; jego niska czułość na identyfikatory jest oczekiwana.

## Wersje (przypięte, `uv.lock` w repo)

| Składnik | Wersja / rewizja | Licencja |
|---|---|---|
| stanza | 1.15.0 (wydana 2026-10-01) | Apache-2.0 |
| torch (CPU) / transformers / peft / sacremoses | 2.15.0+cpu / 4.57.6 / 0.21.2 / 0.2.0 (tokenizer HerBERT) | BSD-3 / Apache-2.0 / Apache-2.0 / MIT |
| modele Stanza | zasoby wydania **v1.15.0** (tag repozytoriów HF `stanfordnlp/stanza-{pl,en,es,de,fr}`; sha tagu: pl `1930012370854bb19fb29e33e86203fef47c7941`, en `874d96177337b9e82cc4d4e188554cd91242d79b`, es `6c5cf2278847a76cd1efd05ee4fddd80594b569d`, de `a8ecd6c8b4f81298918eade263208fedccddd652`, fr `caeb7742148cb0368e4a0f2c68a0f7b09bc22880`) | Apache-2.0 (metadane karty każdego repozytorium) |
| `google/electra-large-discriminator` (en) | `c13c3df7efadc2162f42588bd28eb4e187d602a5` | Apache-2.0 |
| `german-nlp-group/electra-base-german-uncased` (de) | `16e66fe6c6d52b459b7de7330bc9db2c62f3620d` | MIT |
| `allegro/herbert-base-cased` (pl; organizacja `allegro` zweryfikowana na HF) | `50e33e0567be0c0b313832314c586e3df0dc2297` | CC-BY-4.0 (metadane karty) |
| `camembert/camembert-large` (fr; obecnie `almanach/camembert-large`) | `c6e4955c7654931d38dd1b103e8a83fc69e46b53` | karta `almanach/camembert-large` **nie deklaruje licencji**; rodzina CamemBERT jest na MIT (siostrzana karta <https://huggingface.co/almanach/camembert-base>: `license: mit`) – dla wariantu large brak potwierdzenia na karcie, do odnotowania w raporcie |

Rewizja HerBERT-a jest wymuszana w kodzie (`herbert.py`): pobranie `allegro/herbert-base-cased@50e33e05…`, sprawdzenie przed i po wczytaniu potoku, że `refs/main` w cache HF wskazuje tę rewizję (niezgodność = jawny błąd); rewizja trafia do `wersje` (`hf:herbert`).

Modele Stanza pobierane `stanza.download(..., package="default_accurate", model_dir=vendor/stanza)` (dla pl dodatkowo `processors={"ner": "nkjp_bert", ...}`) (zasoby wydania v1.15.0 z
oficjalnych repozytoriów `stanfordnlp` – adresy zaszyte w pakiecie `stanza`); transformery szkieletowe z HF do `vendor/hf`; potem
działanie wyłącznie offline (`download_method=None`, `HF_HUB_OFFLINE=1`). Modele leżą w `vendor/` (poza gitem). Repozytoria
`stanfordnlp` nie mają znacznika „zweryfikowana” na HF, ale są jedynym źródłem, na które wskazuje kod pakietu `stanza` i dokumentacja
(<https://stanfordnlp.github.io/stanza/>).

## Źródło konfiguracji

Dokumentacja: <https://stanfordnlp.github.io/stanza/ner_models.html>, <https://stanfordnlp.github.io/stanza/ner.html>. Procesory
`tokenize,mwt,ner` (NER Stanzy wymaga tokenizacji; `mwt` rozwija wielotokenowe słowa). Dla en/es/de/fr **pakiet `default_accurate`** (wariant
„najdokładniejszy” wg autorów: modele z transformerem tam, gdzie istnieją); dla **polskiego** – oficjalny model `nkjp_bert` (jest w
`resources.json` wydania 1.15.0, szkielet HerBERT), a nie `nkjp` wybierany przez wszystkie pakiety autorów, bo tytuł „najlepsza uczciwa
konfiguracja” wymaga najlepszego dostępnego oficjalnego modelu (oczekujemy, że wariant z BERT-em jest co najmniej tak dobry jak LSTM+charlm – to założenie, nie pomiar; Stanza nie podaje
osobnego F1 dla `nkjp_bert` – tabela autorów ma jeden wiersz NKJP 88,73 – więc przewagi nie liczbujemy). Pozostałe procesory PL jak w `default_accurate`.

| Język | Model NER | Korpus treningowy / F1 wg tabeli autorów |
|---|---|---|
| pl | `nkjp_bert` (HerBERT + charlm oscar; tokenize `pdb_charlm`, mwt `pdb`) | NKJP, F1 88,73 (Karol Saputa; tabela dotyczy modelu domyślnego) |
| en | `ontonotes-ww-multi_electra-large` | OntoNotes (18 typów), F1 88,8 |
| es | `conll02` (charlm newswiki) | CoNLL02, F1 88,1 (alternatywa AnCora 88,6 nie jest w pakiecie autorów i ma inny zestaw typów) |
| de | `germeval2014_german-nlp-electra` | GermEval2014, F1 85,2 |
| fr | `wikinergold_camembert-large` | WikiNER, F1 92,9 |

Brak progu i brak pewności: Stanza nie zwraca prawdopodobieństwa spanu, więc `wynik` = 1,0 dla każdego wykrycia, a `prog.json` nie ma
wpływu (kalibracja progu jest nieistotna dla tego uczestnika).

## Okna

Brak twardego limitu długości tekstu w Stanza (tokenizator znakowy, NER na zdaniach, wewnętrzne cięcie sekwencji dla transformerów).
Dla ograniczenia pamięci i długich „zdań” bez interpunkcji tekst dzielony jest na okna po **5000 znaków** z zakładką 10% (500 znaków,
cięcie na białych znakach; `../_wspolne/okna.py`), wykrycia dotykające sztucznej krawędzi okna są odrzucane, identyczne
z różnych okien scalane. Offsety = `start_char`/`end_char` Stanza (znakowe względem okna) przesunięte do oryginału.

## Typy Stanza → kategorie gold

Filtr typów ustalono przed oglądaniem wyników dev. Zwracane typy odpowiadają kategoriom gold; reszta jest pomijana z uzasadnieniem:

| Typ Stanza | Etykieta wyjściowa | Kategorie gold |
|---|---|---|
| PER, PERSON, persName | PER | OSOBA |
| ORG, ORGANIZATION, orgName | ORG | ORGANIZACJA |
| LOC, GPE, placeName, geogName | LOC | MIEJSCOWOSC, KRAJ, REGION, MIEJSCE_UR |
| DATE, date | DATE | DATA, DATA_UR (tylko pl i en) |
| MONEY | MONEY | KWOTA (tylko en) |

Pominięte: **FAC** (OntoNotes: budynki, lotniska, autostrady, mosty – obiekty, nie adres pocztowy; gold ADRES to adres korespondencyjny, więc FAC
nie jest nim; mapowanie na ADRES zawyżałoby fałszywe trafienia), **NORP** (narodowość/grupa polityczna – dane szczególne tylko w kontekście,
w gold brak takiej kategorii), **MISC/OTH** (worek typu „inne”: wydarzenia, tytuły, nazwy własne; w es/de/fr nie zawiera osób, bo te mają
osobne PER), **TIME/PERCENT/QUANTITY/ORDINAL/CARDINAL** (nie dane osobowe), **PRODUCT/EVENT/WORK_OF_ART/LAW/LANGUAGE** (nie dane osobowe),
**formy `*deriv`/`*part` GermEval** (przymiotniki pochodne i człony złożeń, np. „Berliner”; nie identyfikują osoby/miejsca jako wartości do redakcji).

Mapowanie w `etykiety.json` służy tylko mierze pomocniczej „w deklarowanym zakresie”, liczonej per język dokumentu (J1-fix3,
`metodyka/zakres-gold.md` pkt 4): typ DATE zwracają tylko modele NKJP (pl) i OntoNotes (en), MONEY – tylko OntoNotes; CoNLL02,
GermEval2014 i WikiNER mają wyłącznie PER/ORG/LOC/MISC, więc w `etykiety.json` DATE i MONEY to słowniki język → kategorie. Typy LOC/GPE nie odróżniają ulicy od miasta –
adresy uliczne (ADRES) w praktyce nie są wykrywane.

## Języki

Dokumentacja modeli: pl (NKJP), en (OntoNotes), es (CoNLL02), de (GermEval2014), fr (WikiNER) – `jezyki_oficjalne` = wszystkie 5, `jezyki` = 5.
Pipeline każdego języka ładowany leniwie (dopiero gdy przyjdzie dokument tego języka).
