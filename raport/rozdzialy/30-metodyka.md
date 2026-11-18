# Metodyka

Rozdział streszcza to, co trzeba wiedzieć, żeby odczytać wyniki. Pełne brzmienie (wzory, reguły sędziów, kalibracja, uczestnicy, korpus, środowisko) jest w prerejestracji w repozytorium benchmarku (`metodyka/`).
{% set wp = (r.wersje.get('privatizer-tekst/tekst') or {}).get('wersje', {}) %}{% set k = m.korpus %}{% set c = m.czas %}{% set s = m.sedzia %}
{% set pr = wagi_punktow.progi %}{% set kw = namespace(waga='n/d') %}{% for w, kategorie in wagi_punktow.wagi_kategorii.items() %}{% if 'KWOTA' in kategorie %}{% set kw.waga = w %}{% endif %}{% endfor %}

## Co jest mierzone

Benchmark sprawdza, co zostaje w dokumencie po anonimizacji. Każdy dokument korpusu ma listę wartości wzorcowych (gold): osoby, adresy, identyfikatory i inne dane wraz z ich położeniem.
Uczestnik dostaje dokument i zwraca wynik. Sędzia – program, nie człowiek – sprawdza, czy wartość wzorcowa jest w wyniku nadal odczytywalna. Odczytywalna wartość to **wyciek**.

Pomiar ma dwa poziomy, więc są dwa rankingi:

- **ranking tekstu** – uczestnik dostaje tekst dokumentu i zwraca wykrycia (przedziały znaków). Sędzia tekstowy ocenia pokrycie wartości wzorcowych wykryciami, bez względu na etykietę wykrycia. Ranking mierzy wykrywanie i maskowanie danych w treści;
- **ranking plików** – uczestnik dostaje plik i zwraca plik wynikowy. Sędzia plikowy przeszukuje całą zawartość wyniku: treść, nagłówki i stopki, przypisy, komentarze, metadane, załączniki i obrazy osadzone (z odczytem OCR). Ranking mierzy to, co faktycznie wychodzi z organizacji.

Narzędzie tylko tekstowe nie dostaje zera w rankingu plików, tylko w nim nie występuje. Warianty pomocnicze (aneks liczbowy) nie mają miejsc w rankingach.

## Prerejestracja

Wzory punktów, wagi, reguły sędziów, kalibrację progów, listę uczestników, korpus i środowisko oceny zapisano w prerejestracji i zamrożono {{ m.daty.zamrozenie }}. Stało się to, zanim jakikolwiek uczestnik został uruchomiony i oceniony
na splicie testowym korpusu; w repozytorium nie było wtedy żadnych wyników testu. Zamrożenie potwierdza znacznik git `prerejestracja-1`. Do punktów weszły wyłącznie przebiegi wykonane kodem i progami uczestników
z commitu zamrożenia oraz ocenione sędziami z tego commitu. Wyniki przebiegów powstały po zamrożeniu. Pomiar czasu nie zmienia zamrożonych definicji, tylko je realizuje.

Mierzono wydanie Privatizer by Legal Geek {{ wp.get('aplikacja', 'n/d') }} z modelem „Legal Geek Privatizer (RC)” w wersji {{ wp.get('model_wersja', 'n/d') }}. Ranking dotyczy trybu domyślnego tego wydania
(świeża instalacja, czułość „zrównoważona”, kategoria `KWOTA` wyłączona). Tryb „Maksymalna ochrona” mierzono osobno i pokazano w aneksie liczbowym.
Wyniki opisują stan produktu w dniu pomiaru; inne wydania Privatizera i inne wersje narzędzi otwartych mogą dać inne wyniki.

## Korpus

Korpus jest w całości syntetyczny: osoby, firmy, adresy, identyfikatory, sygnatury i cytowane orzeczenia są fikcyjne, a dokumenty generuje kod z ustalonego ziarna. Języki: polski, angielski, hiszpański, niemiecki i francuski.
Dane o każdym dokumencie (typ, format, język, wartości wzorcowe, split) opisuje manifest; sumy kontrolne SHA-256 plików korpusu zapisano w prerejestracji.

- **Trzon:** {{ liczba(k.trzon_dokumentow, 0) }} dokumentów ({{ liczba(k.trzon_pl, 0) }} po polsku, po {{ liczba(k.trzon_inny_jezyk, 0) }} w każdym z czterech pozostałych języków). Podział na dev ({{ liczba(k.trzon_dev, 0) }}) i test ({{ liczba(k.trzon_test, 0) }})
  jest warstwowany po języku. Punkty liczy się wyłącznie na splicie testowym; dev służył do kalibracji progów uczestników i do przeglądu reguł sędziów.
  Typy dokumentów: e-maile, faktury, prezentacje, odpisy z rejestrów, pełnomocnictwa, CV, wyroki, pozwy, umowy, wezwania, listy płac, notatki, protokoły, dokumenty medyczne (zaświadczenia, wypisy, skierowania)
  i dokumenty osób fizycznych (umowy najmu i sprzedaży auta, pozwy o zapłatę). Dokumentów medycznych jest {{ liczba(k.medyczne, 0) }} i tyle samo dokumentów osób fizycznych. Formaty: DOCX, PDF, skan, XLSX, EML, PPTX, DOC i MSG.
- **Warstwa trudnych przypadków:** {{ liczba(k.trudne_dokumentow, 0) }} dokumentów ({{ liczba(k.trudne_dev, 0) }} w dev i {{ liczba(k.trudne_test, 0) }} w teście), osobne ziarno i osobne identyfikatory. Obejmuje {{ ile(k.trudne_przypadkow, 'przypadek', 'przypadki', 'przypadków') }}:
  pułapki językowe (odmiana nazwisk, nazwiska będące zwykłymi słowami, zdrobnienia, szyk nazwisko–imię, parafy, liczby słownie), cyrylicę ukraińską z transliteracjami i homoglifami, długie dokumenty i granice okien modeli,
  znaki zerowej szerokości i pismo od prawej do lewej, treść ukrytą w plikach Office, PDF i poczcie, uszkodzone kodowanie i układ stron PDF, wątki pocztowe, formaty RTF i ODT oraz cztery przypadki identyfikacji pośredniej.
  Do punktów wchodzi {{ liczba(k.przypadki_t3, 0) }} przypadków tekstowych (T3) i {{ liczba(k.przypadki_p3, 0) }} plikowych (P3); identyfikacja pośrednia jest miarą opisową poza punktami.
- **Szablony i słowniki:** szablony dokumentów napisano od zera, a słowniki są własne. Kontrola nakładania się korpusu z danymi treningowymi mierzonego modelu (8-gramy słowne) jest opisana w aneksie ujawnień.
- **Rozdzielność od treningu:** Zespoły Privatizera nie mają dostępu do splitu testowego; korpus nie służy do treningu ani walidacji modelu.
- **Identyfikatory:** generatory PESEL, KRS, rachunków, numerów rejestracyjnych, telefonów i innych poprawiono na podstawie źródeł pierwotnych; część pozycji pozostaje niezweryfikowana (rozdział „Ograniczenia”).

## Wartości wzorcowe i zakres

Wartość wzorcowa należy do kategorii (osoba, adres, PESEL, rachunek, e-mail, kwota i inne), która ma wagę. Zakres gold ustalono przed pomiarem i obowiązuje wszystkich uczestników jednakowo:

- nazwy stron, daty i sygnatury **cytowanych orzeczeń** nie są wartościami wzorcowymi; ich zamaskowanie liczy się jako nadmiarowe. Własna sprawa dokumentu jest w gold;
- **rozpoznania, kody ICD i leki** nie są wartościami wzorcowymi (tekst zostaje w dokumencie); pacjent, lekarz, placówka i daty wizyt są. Zamaskowanie rozpoznania lub leku to nadmiarowe maskowanie. Ocena ochrony samej diagnozy jest poza zakresem benchmarku;
- **kwoty** (`KWOTA`, waga {{ kw.waga }}) są w gold. Tryb domyślny Privatizera ich nie maskuje, więc wiersze „w tym kwoty” w porównaniu trybów pokazują ich udział osobno;
- miejsce w nazwie sądu lub rejestru („Sąd Rejonowy w Gdańsku”) nie jest wartością wzorcową.

## Sędziowie i reguły wycieku

Reguły sędziów zapisano w prerejestracji w bloku, który kod wczytuje wprost z dokumentu. Najważniejsze:

- **sędzia tekstowy:** wartość wycieka raz, bez względu na liczbę wystąpień. W kategoriach słownych słowo o długości co najmniej {{ liczba(s.min_dl_tokenu, 0) }} znaków jest odsłonięte, gdy niepokryty ciąg ma co najmniej
  {{ procent(s.ulamek_tokenu, 0) }} jego długości (nie mniej niż {{ liczba(s.min_dl_tokenu, 0) }} znaki). W identyfikatorach wyciekiem jest odsłonięty ciąg co najmniej {{ liczba(s.min_cyfr_id, 0) }} kolejnych znaków alfanumerycznych
  (krótsza wartość – cała), a separatory i etykiety identyfikatorów są pomijane. W e-mailach i URL nie liczą się schemat, `www`, `mailto` i końcówka domeny. Słowa opisowe nazw organizacji same nie dają wycieku;
- **sędzia plikowy:** przeszukuje wszystkie części pliku wynikowego (XML w ZIP, strumienie PDF, metadane, OLE, MIME, załączniki, obrazy osadzone) tymi samymi regułami. Strony PDF czyta przez OCR (Tesseract, {{ liczba(s.ocr_dpi, 0) }} dpi,
  drugi odczyt {{ liczba(s.ocr_dpi_drugi, 0) }} dpi dla wartości nieodnalezionych). Zbiory pomocnicze (wartości niejednoznaczne, linia bazowa) liczy z oryginału i gold, więc są wspólne dla wszystkich uczestników;
- **fail-closed:** błąd uczestnika, przekroczony czas, pusty lub nieczytelny wynik, format poza deklaracją i odmowa przetworzenia liczą się jak dokument z wyciekiem – użytkownik wysłałby oryginał. Odmowy raport pokazuje osobno;
- zamiana formatu (np. DOC na DOCX, MSG na TXT) nie jest błędem ani wyciekiem; składnik „zachowanie struktury” w teście integralności jest wtedy „nie dotyczy”;
- każdy rekord oceny niesie odcisk sędziego (kod, reguły, środowisko). Agregacja przerywa, gdy rekordy jednego poziomu mają różne odciski, więc ranking nie łączy ocen różnych sędziów.

## Uczestnicy

Uczestnik to narzędzie albo model uruchomiony w ustalonej konfiguracji. W rankingu tekstu jest {{ liczba(r.rankingi['tekst'] | length, 0) }} uczestników, w rankingu plików {{ liczba(r.rankingi['pliki'] | length, 0) }};
aneks liczbowy ma {{ ile((r.aneks.get('tekst', []) | length) + (r.aneks.get('pliki', []) | length), 'wariant', 'warianty', 'wariantów') }}. Wszyscy pracowali na procesorze (bez GPU), z tymi samymi rewizjami modeli i wersjami bibliotek z plików blokad (`uv.lock`).
Każdy uczestnik tekstowy dostał dokumenty we wszystkich pięciu językach, także wtedy, gdy deklaruje mniej; zakres deklarowany opisuje miara pomocnicza.

| Grupa | Uczestnik | Poziom | Narzędzie lub model |
|---|---|---|---|
| A | `presidio-spacy` | tekst | Presidio i spaCy (modele `*_core_news_lg`, `en_core_web_lg`) |
| A | `presidio-pl-ner` | tekst | Presidio z modelami NER dla każdego języka (m.in. `lexedit/herbert-polish-legal-ner` dla polskiego) |
| A | `presidio-gliner` | tekst | Presidio z modelem `urchade/gliner_multi_pii-v1` |
| A | `gliner-nvidia-pii` | tekst | `nvidia/gliner-PII` |
| A | `gliner-urchade-pii` | tekst | model `urchade/gliner_multi_pii-v1` |
| A | `gliner-knowledgator-pii` | tekst | model `knowledgator/gliner-pii-large-v1.0` |
| A | `openai-privacy-filter` | tekst | `openai/privacy-filter` (oficjalne repozytorium) |
| A | `stanza` | tekst | Stanza (NER) |
| Privatizer | `privatizer-model` | tekst | sam model „Legal Geek Privatizer (RC)” |
| Privatizer | `privatizer-tekst` | tekst | silnik Privatizera na tekście (model, reguły, scalanie) |
| Privatizer | `privatizer-plik` | pliki | aplikacja Privatizer, plik na wejściu i na wyjściu |
| B | `scrubadub` | tekst | same wyrażenia regularne (punkt odniesienia) |
| B | `flair` | tekst | Flair, model `flair/ner-multi` |
| B | `ai4privacy` | tekst | model `ai4privacy/llama-ai4privacy-multilingual-categorical-anonymiser-openpii` (sam model) |
| B | `presidio-image-redactor` | pliki (skany) | Presidio Image Redactor z OCR |
| B | `pdf-redactor` | pliki (PDF) | `pdf-redactor` z analizatorem `presidio-pl-ner` |
| B | `presidio-wrapper-plikowy` | pliki (DOCX, XLSX, PPTX) | nasz naiwny wrapper: Presidio na tekście akapitów i komórek |

- **Grupa A** to modele i narzędzia otwarte, którym skalibrowano próg pewności na splicie dev (siatka od {{ liczba(m.kalibracja.siatka_min, 2) }} do {{ liczba(m.kalibracja.siatka_max, 2) }}, jedna wartość na uczestnika, miara: średnie char-F2 dokumentów dev). Wyjątek to `stanza`: jego NER nie zwraca pewności spanów, więc próg nie ma wpływu i uczestnik pozostaje bez kalibracji. Wybór zrobiono przed pomiarem.
  Gdy optimum wypadało na brzegu siatki, siatki nie rozszerzano; to ograniczenie działa na korzyść pokrycia (recall) tych uczestników.
- **Grupa B** pracuje w najlepszej konfiguracji opisanej przez autorów, bez kalibracji. Uczestnicy plikowi grupy B dziedziczą konfigurację analizatora `presidio-pl-ner`.
- **Naiwny wrapper** (`presidio-wrapper-plikowy`) jest wzorcem „co zostaje, gdy anonimizuje się tylko tekst”: integrator wyciąga tekst akapitów i komórek, a pomija nagłówki, stopki, przypisy, komentarze, śledzone zmiany, notatki i metadane.
  To nie jest ocena Presidio ani żadnego produktu.
- **Privatizer** to wydanie z aplikacji z instalatora, wołane jej API. `privatizer-model` i `privatizer-tekst` rozdzielają wkład modelu i potoku (reguły z sumami kontrolnymi, pola, scalanie, lista wyjątków, rozchodzenie powtórzeń).
- **Aneks liczbowy** (osobny dokument) zawiera warianty rozdzielające wkład składników: same reguły Privatizera, model Legal Geek Privatizer (RC) w Presidio, potok Privatizera z obcym modelem (GLiNER, OpenAI Privacy Filter) i tryb „Maksymalna ochrona” (tekst i plik).
  To analiza wkładu składników, nie porównanie produktów. Obcy model w potoku Privatizera nie ma kalibracji Privatizera, a potok strojono pod własny model, więc słabszy wynik takiego wariantu nie oznacza słabszego modelu samodzielnie.
- **Dokumenty po ukraińsku** (warstwa trudna) dostaje każdy uczestnik. Uczestnik, który ukraińskiego nie deklaruje, przetwarza je w pierwszym zadeklarowanym języku z listy: polski, angielski, niemiecki, hiszpański, francuski.
  Ukraiński jest poza testem najsłabszego języka (T4), a w T3 i P3 wchodzi jako przypadek.

Uczestników, których rozważono i odrzucono, wymienia aneks odtworzenia. Usługi chmurowe opisano w rozdziale „Wdrożenie”; nie były mierzone ani punktowane.

## Niepewność i remisy

Niepewność liczy bootstrap po dokumentach: {{ liczba(pr.bootstrap_powtorzen, 0) }} losowań ze zwracaniem z ustalonym ziarnem, przedział {{ procent(pr.przedzial_ufnosci, 0) }} z percentyli {{ liczba((1 - pr.przedzial_ufnosci) / 2 * 100, 1) }} i {{ liczba((1 + pr.przedzial_ufnosci) / 2 * 100, 1) }}.
Losowania są sparowane: wszyscy uczestnicy dostają te same indeksy dokumentów, osobno w trzonie i w warstwie trudnej. Warstwę trudną losuje się warstwowo po pełnym zestawie przypadków dokumentu,
więc każdy przypadek ma w każdym losowaniu tyle dokumentów, ile w próbie. Suma rankingu jest liczona w każdym losowaniu z tych samych indeksów; wynik szybkości jest stały i nie ma bootstrapu.
Gdy przedziały sum dwóch uczestników nachodzą na siebie, raport podaje **remis statystyczny** zamiast rozstrzygać miejsce.

## Pomiar szybkości

Szybkość mierzono na jednej maszynie referencyjnej: Apple M1, {{ liczba(c.ram_gb, 0) }} GB RAM, na zasilaczu, z wyłączonym trybem niskiego zużycia energii i bez innych obliczeń. Jeden uczestnik pracował naraz, na jednym dokumencie naraz, bez sieci.
Wszyscy dostali ten sam budżet wątków ({{ liczba(c.watki, 0) }}), a aplikacja Privatizera – ustawienia domyślne wydania.

- **Próbka:** {{ liczba(c.proba_dokumentow, 0) }} dokumentów trzonu ze splitu testowego (polski {{ liczba(c.proba_pl, 0) }}, angielski {{ liczba(c.proba_en, 0) }}, niemiecki {{ liczba(c.proba_de, 0) }}, hiszpański {{ liczba(c.proba_es, 0) }}, francuski {{ liczba(c.proba_fr, 0) }}), wylosowana z ustalonym ziarnem; ta sama dla testów tekstu i plików.
- **Przebieg:** proces uczestnika uruchomiony i model załadowany przed pomiarem (czas startu jest raportowany osobno), {{ liczba(c.rozgrzewka, 0) }} przejście rozgrzewkowe po całej próbce (nieliczone), potem {{ liczba(c.przejscia, 0) }} przejścia mierzone.
  Czas dokumentu to czas ścienny od wysłania zapytania do odebrania kompletnego wyniku, mediana z przejść. Dokument z błędem, przekroczeniem czasu albo odmową ma czas nieskończony (awaria nie może być „szybka”).
- **Wynik:** mediana po dokumentach próbki z czasu dokumentu na stronę obliczeniową, czyli {{ liczba(c.strona_znakow, 0) }} znaków tekstu dokumentu (nie mniej niż jedna strona). Punkty to wartość odniesienia `t_ref` = {{ liczba(c.t_ref_s, 1) }} s na stronę
  podzielona przez ten czas, nie więcej niż pełna waga testu. `t_ref` jest stałą ustaloną przed pomiarem, niezależną od uczestników: dodanie lub usunięcie narzędzia nie zmienia cudzych punktów.
  Przy tej wartości typowy dziesięciostronicowy dokument kancelarii jest gotowy w około dziesięć sekund, czyli tyle, ile użytkownik czeka bez przełączania się do innej pracy. Wpływ na sumę jest ograniczony do wagi testu szybkości; analiza wrażliwości pokazuje wynik także
  przy {{ liczba(c.t_ref_niski_s, 1) }} i {{ liczba(c.t_ref_wysoki_s, 1) }} s na stronę, bez zmiany punktów.
- **Pamięć** to szczyt dla drzewa procesów uczestnika (macOS: `phys_footprint`, próbkowanie co sekundę). Metody pamięci na różnych systemach nie są porównywalne.

## Miary pomocnicze

Poza punktami raport podaje: wynik tylko w kategoriach, które uczestnik deklaruje (w jego języku dokumentu) i tylko w jego językach oficjalnych; poziom encji (encja wycieka, gdy wycieka którykolwiek jej zapis – cyrylica, transliteracje,
homoglify, inicjały); ścisłe F1 na spanach (granice dokładnie równe wartości wzorcowej, bez względu na etykietę); charakterystyki pokrycia znakowego i fałszywych wykryć.
**Identyfikacja pośrednia** to osobna miara opisowa: osoba nienazwana w dokumencie, wskazywalna z połączenia informacji (funkcja i firma, rzadka choroba i pracodawca, wiek i mała miejscowość, numer działki i współrzędne).
Dla każdej kombinacji liczy się, czy została przerwana, czyli czy co najmniej jeden jej składnik został zamaskowany; wynik to odsetek przerwanych kombinacji z przedziałem ufności. Miara nie wchodzi do sum.

## Kontrole dodatkowe

Poza punktacją wykonano dwie kontrole symetrycznie dla wszystkich uczestników: kontrolę nakładania się korpusu z danymi treningowymi mierzonego modelu (8-gramy) oraz kontrolę domen zarezerwowanych w adresach e-mail i URL.
Wyniki i ograniczenia obu kontroli są w aneksie ujawnień, a wynik drugiej – także w rozdziale „Wyniki”.
