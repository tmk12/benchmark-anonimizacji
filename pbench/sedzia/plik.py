"""Sędzia plikowy: które wartości wzorcowe (gold) zostały w pliku wynikowym uczestnika, czy plik jest nienaruszony
i czy zamiennik jest spójny. To sędzia poziomu 3 („plik → plik”): porównuje obsługę plików Privatizera i konkurentów
(zob. `ekstrakcja.py` – co jest skanowane w każdym formacie; `obrazy.py` – OCR obrazów).

Wejście `ocen_plik(oryginal, wynik, wartosci)`: plik oryginalny, plik uczestnika i lista `Wartosc` (`gold_plik` +
`gold_obrazy` z manifestu). Wynik jest kluczowany po `Wartosc.id`: wartość wycieka, jeśli wycieka w którymkolwiek miejscu
wyniku (ta sama wartość bywa w pliku kilka razy – nagłówki e-maila w treści i w `custom.xml`, stopka na każdym slajdzie).

Reguły wycieku (brak offsetów, więc szukanie; wspólna normalizacja `normalizacja.py`: NFKC, NBSP/białe znaki →
spacja, myślniki → „-”, casefold):

1. **Każda wartość w każdym tekście.** Wartość (tekstowa i obrazowa) jest szukana w tekście wszystkich części pliku
   (treść, nagłówki, stopki, komentarze, zmiany, metadane, pola, załączniki rekurencyjnie…) ORAZ w OCR każdego obrazu
   osadzonego w wyniku (OCR – z tolerancją, zob. pkt 5); obrazy wyniku są zawsze czytane (np. PDF zrasteryzowany,
   nazwisko narysowane w `word/media`); trafienie częściowe z OCR obrazu osadzonego (i pełne złożone wyłącznie z trafień
   rozmytych) liczy się, jak na stronach PDF, tylko z potwierdzeniem w innym odczycie tego obrazu – odczycie INNYM TRYBEM
   Tesseracta albo tym samym trybem w innej skali, gdy wspólny token jest w którymś z dwóch odczytów słowem DOKŁADNIE
   (`_trafienia_ocr`, `_Ocr.tryby`; obraz bez potwierdzenia dostaje drugi odczyt – `obrazy.ocr_tekst(drugi=True)`); token
   identyfikujący ≥ `MIN_DL_TOKENU_BEZ_POTWIERDZENIA` znaków trafiony dokładnie wystarcza z jednego odczytu obrazu.
   Wartości obrazowe, których sędzia nie znajduje w OCR ORYGINAŁU (`obrazy.wykrywalne_obrazy`), są `niewykrywalne`
   i wyłączone z oceny dla wszystkich uczestników. Przed porównaniem usuwane są znaki formatujące (zero-width, miękki
   łącznik, BOM), a gdy wartość ma znaki diakrytyczne, próbowana jest też wersja bez diakrytyków („Dabrowski” trafia
   „Dąbrowski”). Gdy kilka `id` ma ten sam tekst (k), wyciekają `min(k, liczba wystąpień w wyniku)` z nich, w kolejności
   `id` (liczba wystąpień w tekstach OCR – regułą OCR, zob. niżej „Strony PDF czytane OCR”).
2. **Identyfikatory** (kategorie `KATEGORIE_ID` o długości alfanumerycznej ≥ 6; kod pocztowy – ≥ `MIN_DL_KODU` = 5, J3,
   jednakowo w każdym języku: „28-333”, „28333”, „28 333”): wyciek, gdy znormalizowana wartość
   (same litery i cyfry) występuje w tekście części zredukowanym tak samo – przy czym trafienie musi mieć granice
   (nie może wchodzić w dłuższy ciąg liter/cyfr), żeby 6–8 cyfr nie „trafiało” przypadkiem w długich ciągach liczb
   (arkusze, XML). Rozszerzenia: (a) dla numeru zaczynającego się od „+kod” sprawdzana jest też część krajowa (≥ 6
   znaków); (b) `DATA`, `DATA_UR`, `KWOTA` (słabe tokeny: sam rok z dat utworzenia pliku nie jest wyciekiem daty)
   są liczone jak identyfikatory (≥ 6 znaków, kwota ≥ 5; krótsze nie mogą wyciec); (c) `KWOTA` ma też wariant liczby
   kanonicznej (≥ 5 cyfr), bo komórka XLSX przechowuje 753,46 € jako liczbę 753.46. Separatory między znakami:
   dowolne znaki niealfanumeryczne poza `< > = " &` (spacja, kropka, myślnik, ukośnik, „°”, nawias…) i podkreślnik.
   (d) Identyfikator z etykietą (`tekst.ETYKIETY_ID`, J1 – „Routing No. …, Account No. …”, „Claim No. …”): słowa etykiety nie
   identyfikują wartości, więc obok pełnej wartości szukane są jej **części** – ciągi alfanumeryczne między etykietami
   (`Regula.id_czesci`, łącznie ≥ 6 znaków; bez części wspólnych z inną wartością gold – cała część w tekście innej wartości,
   wzorcem z granicami, nie podciąg (J1-fix3, m2) – tej samej liczby nie da się przypisać): wszystkie części = „pelny” (także gdy
   etykiety zamieniono), część ≥ `Regula.id_prog_czesci` znaków = „czesciowy”; w OCR także po złożeniu znaków mylonych,
   a częściowy – z potwierdzeniem jak token (`_trafienia_ocr`). Część pominięta jako wspólna nie wchodzi do „wszystkich części”:
   odsłonięte pozostałe przy zamaskowanej części wspólnej = „pelny” (wyłącznie zaostrza). Wyciek częściowy identyfikatora jest
   tu tylko całą częścią (sędzia plikowy nie ma offsetów): IBAN bez etykiety wycieka wyłącznie „pelny”, a część zamaskowana
   w połowie nie jest wyciekiem (w sędzi tekstowym – jest, gdy zostaje ≥ `min_cyfr_id` kolejnych znaków).
   **Sygnatura – części opisowe (J1-fix2, J1-fix3):** ciąg między etykietami dzieli się na części opisowe (wydział, repertorium,
   rodzaj postępowania: „VII Ca”, „12 C”, „Juicio Verbal”; litery sklejone separatorem z cyframi na początku tokenu numeru –
   „NS-REJ.KRS/”, „QB-”) i numer (od ostatniego tokenu z cyfrą; `_opis_i_numer`) – także gdy etykiety w wartości nie ma. Każda
   część sygnatury (opisowa i numer) wycieka częściowo od `min_cyfr_id` znaków, jak w sędzi tekstowym (J1-fix3, m1: „12 C” –
   3 znaki – nie wycieka, numer „345/24” – 5 znaków – tak); części rachunku – od `MIN_DL_ID`. Reguła taka sama w każdym języku,
   nie zależy od etykiety.
   **Cytat innej sprawy (J1-fix3, I1):** część, którą oryginał ma także poza wystąpieniami wartości gold („VII Ca” w cytacie
   „VII Ca 6470/18” obok własnej „VII Ca 1554/21” – cytaty nie są gold), jest trafieniem tylko wtedy, gdy wynik ma ją częściej
   niż oryginał poza gold – reguła krotności jak dla wartości niejednoznacznych (`_z_czesciami_spoza_gold`,
   `_bez_czesci_spoza_gold`); pominięta zostaje w „wszystkich częściach” (odsłonięty numer przy cytacie = „czesciowy”).
   Krótsze identyfikatory – jak tokeny.
3. **Pozostałe wartości**: wyciek, gdy w tekście części występuje (granice słów, bez wielkości liter, dowolne znaki
   niesłowne między tokenami) pełna wartość ALBO którykolwiek jej **token identyfikujący**. Token (`\\w+`) jest
   identyfikujący, gdy ma ≥ `min_dl_tokenu` znaków, nie jest ignorowany dla EMAIL/URL (schemat, `www`, `mailto`, TLD –
   jak w sędzi tekstowym) i NIE występuje w tekście oryginalnego dokumentu poza wystąpieniami wartości gold (słowa
   generyczne – „Kancelaria”, „Prawna”, „sp”, „ul” – nie liczą się; oryginał skanowany tak samo jak wynik, dla wartości
   obrazowych także jego OCR; token złożony z samych cyfr liczy się od `min_cyfr_id` cyfr, a w wartości spoza
   `KATEGORIE_ID` nie jest identyfikujący – dawka „1000 mg” trafia w `/Widths` czcionki; części strukturalne – style, czcionki, motyw – są szablonem formatu: ich słowa są
   generyczne; w wyniku skanowane są tylko pełną wartością/identyfikatorem i tylko gdy oryginał jej w tej części nie
   miał). Zbiór słów generycznych powstaje wyłącznie z tekstów pojedynczych węzłów oryginału (akapity, komórki,
   atrybuty, stringi) – nie z widoków sklejonych ani surowych. **Leksykon korpusu** (`zbuduj_leksykon`,
   `RegulyWycieku.prog_leksykonu`, domyślnie 0,05): token obecny w gold ≥ 5% dokumentów danego języka oraz słowa
   zastrzeżone (`example`, `test`, formy prawne…) nie liczą się jako pojedynczy token wycieku (pełna wartość i
   identyfikatory bez zmian) – dane fikcyjne się powtarzają, więc wspólny token nie dowodzi wycieku. Wartość bez żadnego liczącego
   się tokenu (np. „ul.”, numer domu) nie może wyciec – z wyjątkiem inicjałów (pkt 7).
   **Wartość niejednoznaczna**: gdy jej tekst występuje w oryginale CZĘŚCIEJ niż jest wystąpień gold (np. miasto z nazwy
   sądu, które nie jest gold, równe miastu adresu), wystąpienia nie da się odróżnić od wycieku – wartość jest wyłączona
   z oceny wszystkich uczestników (`OcenaPliku.niejednoznaczne`), podobnie jak `niewykrywalne` (zob. `niejednoznaczne`).
   Formy odmienione: gold zawiera formę wstawioną, szukamy jej i jej tokenów; dodatkowo token alfabetyczny o długości
   ≥ 6 ma **rdzeń** (pierwsze max(5, ⌈0,75·długość⌉) znaków), który pasuje prefiksowo do słowa wyniku o długości
   ≤ długość tokenu + 4 (np. „Kowalski” → rdzeń „kowals” trafia „Kowalskiemu”); rdzeń nie liczy się, gdy jest
   prefiksem słowa generycznego oryginału.
4. **Rodzaj**: „pelny” – znaleziona pełna wartość (identyfikator) albo wszystkie liczące się tokeny; „czesciowy” –
   tylko część tokenów. `miejsce` w krotce wycieku = nazwa części wyniku, w której wartość znaleziono (pełny przed
   częściowym, potem kolejność w pliku).
5. **OCR**: te same reguły, ale tokeny i ciągi alfanumeryczne dopasowywane z tolerancją, bo OCR myli znaki: token rozmyto
   (podobieństwo ≥ 0,85, difflib; token ≥ `MIN_DL_SLOWA_ROZMYTEGO` = 4 znaki, słowo OCR ≥ `MIN_DL_SLOWA_OCR_ROZMYTEGO` = 5 – śmieci
   „ana”, „EICH” nie trafiają „anna”, „Erich”), token z cyfrą po złożeniu znaków mylonych (`ZNAKI_MYLONE_OCR`: „I48” = „148”);
   identyfikator po złożeniu znaków mylonych wzorcem z granicami, a rozmyto (z granicami) tylko identyfikator `KATEGORIE_ID`
   o ≥ `MIN_DL_ID_ROZMYTEGO` znakach; data i kwota (`_wzor_daty_ocr`) – cyfry dokładnie (albo litera czytana w miejscu cyfry,
   `LITERY_ZA_CYFRY_OCR`: „1b.0b.202b” = „16.06.2026”) z granicami, bo inna cyfra to inna data („29.11.2022” ≠ „28.11.2022”), a ciągi
   liter (miesiąc, waluta) rozmyto (`_litery_pasuja`: „sierpma” = „sierpnia”, „Jume” = „June”, ale inna nazwa miesiąca – „Juli” ≠
   „Juni” – nie), „r.” i waluta opcjonalne; pełna wartość także frazą z tolerancją (`_fraza_ocr`: tokeny w kolejności, krótkie słowa
   między nimi pominięte – „sp. z 0.0.”). Słowo OCR równe innemu słowu dokumentu (słowo generyczne albo token innej wartości gold)
   nie trafia rozmyto tokenu wartości („Schmidt” innej osoby ≠ „lschmidt” z e-maila) – jest tamtym słowem (`Regula.obce`); z tekstu
   OCR identyfikatora wycinane są wystąpienia innych wartości gold z granicami („28. Juli 2025” ≠ „1. Juli 2025”, ale „Z1. Juli 2025” =
   „21. Juli 2025”, `Regula.obce_alnum`); e-mail i URL są szukane w OCR także jako ciąg alfanumeryczny (`KATEGORIE_ALNUM_OCR`: „@”
   czytane jako litera skleja tokeny). Słowo zamiennika (`SLOWA_ZAMIENNIKOW` – etykiety wszystkich uczestników) w kontekście
   zamiennika (nawias, numer: „[ADRES 21]”, „OSOBA 1”, „<PERSON>”) jest w tekście OCR maskowane (`maskuj_zamienniki`) – nie jest
   tokenem wycieku („login” z „[LOGIN_7]”) i nie trafia rozmyto („ADRES” ≠ „Andrés”); poza tym kontekstem jest zwykłym słowem
   („Alter” obok „[PERSON]” to wyciek nazwiska „Hans Alter”).

6. **Homoglify – szkielet** (H6a): obok porównania dokładnego wartość jest porównywana w postaci złożonej – szkielet
   (`normalizacja.szkielet`: litery cyrylicy i greki o kształcie liter łacińskich, wg Unicode `confusables.txt`, sprowadzone do łaciny)
   bez znaków diakrytycznych (`normalizacja.zloz_szkielet`), na tekstach wyniku w tej samej postaci (`Tekst.zlozony`). Wartość gold
   zapisana homoglifami („Kоwalski” z cyrylicznym „о”) wycieka więc, gdy wynik zawiera ją w zapisie oryginalnym ALBO po „naprawie”
   homoglifów na łacinę; wartość cyrylicka z wmieszaną łaciną – także po „naprawie” na cyrylicę. Kierunek odwrotny – wartość
   łacińska ASCII (albo identyfikator), której litery wynik zastąpił homoglifami – sprawdza wariant `Regula.tylko_cyrylica`: sam
   szkielet, tylko na tekstach z cyrylicą albo greką mylącą (na tekście bez nich szkielet niczego nie zmienia, więc trzon korpusu
   ocenia się jak dotąd). Zbiory dokumentu liczone są tą samą regułą z oryginału: słowa generyczne, leksykon, słownik OCR i ciągi obcych
   wartości wariantu – w postaci złożonej; wartość, której postać złożona występuje w oryginale częściej niż wystąpień gold
   (`niejednoznaczne(zloz=zloz_szkielet)`), traci wariant w szkielecie (ocena dokładna bez zmian); krotność wartości z homoglifami
   liczona jest też w postaci złożonej. Wartość z samymi diakrytykami (bez homoglifów) ma wariant złożony jak przed H6a – bez
   warunku niejednoznaczności. Przejścia szkieletu, które zmieniają ocenę wyłącznie tekstu z literami szkieletu (niejednoznaczność
   w szkielecie i wariant `tylko_cyrylica` wartości ASCII), są pomijane, gdy liter szkieletu nie ma ani w wartościach, ani
   w oryginale (części i OCR), ani w wyniku (`ZbioryDokumentu.pelne`; poprawka H6a M8 – wynik bez zmian).
7. **Inicjały** (`INICJALY`, H6a): dokładny wzorzec inicjałów z granicami (`normalizacja.wzor_inicjalow`: litery i kropki jak
   w wartości, dowolne spacje po kropce, przed i po wzorcu brak litery/cyfry – „J.K.” trafia „J. K.”, nie trafia „J.K.M.”, „JK” nie
   trafia „JKL”), także na tekście OCR (bez wariantów rozmytych); trafienie = „pelny”. W OCR (strony PDF, obrazy osadzone)
   trafienie inicjałów liczy się tylko z potwierdzeniem w innym odczycie tej samej strony/obrazu i w odczycie tego obrazu
   z wybielonymi polami zamalowanymi (`_trafienia_ocr`, `_po_wybieleniu`, `obrazy.bez_pol`: czarne prostokąty redakcji rastrowej
   czytane jako „rs” w każdym odczycie). W odczytach obrazów osadzonych (także bez pól) pomijane są wiersze szumu
   (`_bez_szumu`: ≥ `MIN_SLOW_SZUMU` tokenów ≥ `MIN_DL_SLOWA_SZUMU` liter samymi wielkimi literami, nie z jednej powtórzonej
   litery, łącznie z ≤ `MAKS_LITER_SZUMU` różnych liter, i żadnego słowa dokumentu – słowa oryginału albo tokenu wartości gold, porównanie bez znaków diakrytycznych): znak
   maskujący powtórzony w obrazie osadzonym (wiersz gwiazdek w miejscu logo) OCR czyta w każdym odczycie, także po wybieleniu,
   jako ten sam ciąg wielkich liter, w którym wzorzec trafia przypadkowo; wiersz prawdziwej parafy ma etykietę z tekstu
   dokumentu, jest krótki albo ma słowa pisane zwykle (zamienniki) czy maskę z jednej litery („XXXX”). Na stronach z warstwą tekstową pokazującą treść (`_strony_z_warstwa`) OCR
   czyta render strony bez obiektów tekstowych (`_Ocr.bez_tekstu`): szum zamaskowanego tekstu (gwiazdki czytane jako „ar”
   w każdym odczycie) znika, piksele spoza warstwy (parafa jako obraz inline albo XObject, ścieżki) zostają; strona bez warstwy
   (raster, tekst jako ścieżki, znaki bez mapy ToUnicode) – render pełny. Niejednoznaczność inicjałów –
   tym samym wzorcem (`niejednoznaczne`, `normalizacja.ile_inicjalow`). Generatory przypadków `parafy` i `skroty_po_pelnym`
   gwarantują, że wzorzec nie występuje w dokumencie poza spanami gold inicjałów, a w całym tekście trafia nie częściej niż
   w tekstach gold – ta sama miara (`trudne_wspolne.inicjaly_jednoznaczne`, losowanie od nowa).
8. **Widoki binarne OLE** (J3): inicjały i wartości krótkie (≤ `MAKS_ALNUM_KROTKIEJ` = 3 znaki alfanumeryczne) nie są szukane
   w zdekodowanych widokach binarnych strumieni pliku DOC (`ekstrakcja.Czesc.binarna`: `Data`, `WordDocument`, tabele, obiekty
   osadzone – wszystko poza strumieniami właściwości) – dwie litery trafiają tam przypadkowo w bajty zdekodowane jako tekst, zależnie
   od bajtów wyniku (uczestnik zamieniający DOC na DOCX nie ma takich widoków). Szukane są w tekście dokumentu (konwersja
   LibreOffice, części `doc->docx:`), właściwościach i pozostałych częściach. Dłuższe wartości – bez zmian.

Integralność (`OcenaPliku.integralnosc`): `otwiera_sie`, `blad`, `format`/`format_zgodny`, `struktura` (liczby w
oryginale i wyniku: akapity/tabele – DOCX, DOC i ODT, akapity/wiersze tabel – RTF, strony – PDF, arkusze/wiersze – XLSX,
slajdy – PPTX, części MIME – EML i MSG, wizytówki – vCard), `zachowanie_struktury` (0–1: średnia z min/max po licznikach oryginału; 0, gdy plik nieczytelny/pusty; `None` = nie
dotyczy, gdy format zamieniony na odpowiednik – punktacja pomija taki składnik) i `spojnosc`. **Spójność**: encja = rola wartości (`encja(id)`: id bez `#n`, `@obraz`); bierzemy encje z ≥ 2
wystąpieniami w tekście oryginału; tekst wyniku jest dopasowywany do oryginału (difflib na słowach, część po części,
części o tej samej nazwie) i dla każdego wystąpienia odczytywany jest zamiennik. Encja jest spójna, gdy WSZYSTKIE jej
wystąpienia są zamaskowane i mają ten sam niepusty zamiennik (porównanie po znakach alfanumerycznych, więc `[OSOBA_1]`
= `OSOBA 1`). `spojnosc` = spójne / ocenione (None, gdy brak ocenianych encji); encje z nietkniętym wystąpieniem
(`niezamaskowane`) nie są oceniane, a z niejednoznacznym dopasowaniem (zamiennik zlany z sąsiednią zmianą,
wystąpienie tylko częściowo zamienione) są pomijane i liczone w `pominiete`. Wystąpienie w części, której wynik nie ma,
liczy się jako zamaskowane pustym zamiennikiem (niespójne).

**Przeniesienia wyrazów**: wyraz złamany łącznikiem na końcu wiersza („Kowal-\\nski”; w PDF PDFium zapisuje taki łącznik jako
U+FFFE) ma w każdej części tekstowej (strona PDF, plik `.txt`) dodatkowy widok ze sklejonymi przeniesieniami
(`normalizacja.polacz_przeniesienia`), a wartość gold z przeniesieniem jest szukana w postaci sklejonej – zwykłe myślniki w
wierszu („Nowak-Kowalski”) nie są sklejane; wyraz złożony złamany po łączniku ma też zapis niesklejony w tekście.

**Strony PDF czytane OCR** (`obrazy.ocr_stron_pdf`): KAŻDA strona każdego PDF-u – wyniku zawsze, oryginału zawsze (raz na
dokument, pamięć podręczna po sumie pliku) – jest renderowana (PDFium, `ekstrakcja.RENDER_DPI` = 300 dpi; strona większa niż
`ekstrakcja.MAKS_BOK_RENDERU_PX` – kafelkami obszaru z treścią w pełnym dpi) i czytana OCR jak obraz osadzony – dla każdej wartości,
także obrazowej niewykrywalnej w OCR obrazu osadzonego (render pokazuje to samo co warstwa tekstowa). Wartość wycieka, gdy jest
widoczna w KTÓRYMKOLWIEK widoku: warstwa tekstowa, strumienie i bajty surowe (bez danych obrazów inline), obrazy osadzone, OCR
stron – więc to, co widać na stronie (raster strony, także obraz inline, tekst przykryty obrazem, tekst jako ścieżki, czcionka
z zepsutą mapą ToUnicode), liczy się niezależnie od tego, co zwraca kopiowanie. Trafienie częściowe z samego OCR stron – i pełne
złożone wyłącznie z trafień rozmytych („MARA” ≈ „Maria”) – liczy się tylko z potwierdzeniem: ten sam token trafia w innym odczycie
tej samej strony (`_trafienia_ocr`); pozostałe pełne – z jednego odczytu. Wartości z linii bazowej, których odczyt 300 dpi nie
znalazł na stronach (oryginału – w linii bazowej; wyniku – wśród wycieków), i wartości z trafieniem bez potwierdzenia są szukane w
drugim odczycie stron (`ekstrakcja.DRUGI_ODCZYT_DPI` = 400 dpi, tryby Tesseracta `obrazy.PSM_DRUGIEGO_ODCZYTU`: psm 3 bywa ślepy na
blok w układzie wielokolumnowym, psm 6 go czyta). Gdy po nim potwierdzenia nadal brak, strony dostają trzeci odczyt (300 dpi,
`obrazy.PSM_TRZECIEGO_ODCZYTU` = psm 6), więc i blok czytany tylko przez psm 6 ma odczyty w dwóch rozdzielczościach.
**PDF w załączniku poczty** (EML, MSG – także w wiadomości zagnieżdżonej) jest oceniany tą samą ścieżką co samodzielny PDF:
warstwa tekstowa, strumienie i bajty surowe, obrazy osadzone (ekstrakcja rekurencyjna) ORAZ OCR każdej jego strony
(`ocr_stron_pliku`, `obrazy.ocr_stron_osadzonych`: te same odczyty i potwierdzenia, pamięć podręczna po sumie pliku PDF).
Krotność wartości o kilku `id` liczona jest w tekstach OCR regułą OCR, tylko z trafień pełnych (`_ile_w_ocr`: samo nazwisko w innym
wierszu nie jest drugim wystąpieniem pełnej wartości, wartość złamana między wiersze liczy się raz), a nie dokładną frazą; różne
odczyty tych samych stron (300 i 400 dpi, psm 3 i 6) i widoki tej samej treści (warstwa tekstowa + obrazy osadzone albo render strony) nie
sumują się – brana jest większa liczba. W poczcie render stron pokazuje tylko PDF-y załączników, więc „albo” dotyczy każdego PDF-u
osobno (także w wiadomości zagnieżdżonej): krotność = wystąpienia w częściach spoza PDF-ów (treść, nagłówki, inne załączniki) +
Σ po PDF-ach max(wystąpienia w jego częściach, OCR jego stron) – `_ile_poczty`.

**Zbiory dokumentu** (`zbiory_dokumentu`): wartości niejednoznaczne, słowa generyczne, wartości niewykrywalne i linia bazowa
(mianownik, `OcenaPliku.bazowe`) zależą WYŁĄCZNIE od oryginału i gold – są liczone raz i wspólne dla wszystkich uczestników
(funkcja nie dostaje pliku wyniku). OCR stron oryginału wchodzi do niejednoznacznych i generycznych tylko wtedy, gdy oryginał sam
ma zepsutą warstwę tekstową (`warstwa_tekstowa_zepsuta`: poniżej `PROG_POKRYCIA_TEKSTU` wartości tekstowych gold w tekście stron
albo ≥ `MIN_ZNAKOW_STERUJACYCH` znaków sterujących – tak PDFium oddaje znaki bez mapy ToUnicode) – render zwykłego oryginału to
gorszy odczyt tej samej treści, a słowa gold zniekształcone przez OCR nie mogą stać się „generyczne”. Tak samo PDF w załączniku poczty
(`zepsute_pdfy_poczty`): OCR stron PDF-u załącznika ze zepsutą warstwą tekstową wchodzi do zbiorów dokumentu, OCR zdrowego – nie.
Linia bazowa korzysta ze wszystkich widoków oryginału, także OCR stron. Wykrywalność wartości obrazowej w OCR oryginału (J3)
wymaga tych samych potwierdzeń co wyciek: grupa wartości obrazowych przyjęta przez `obrazy.wykrywalne_obrazy` (jeden odczyt), której
linia bazowa w oryginale nie odnajduje, jest `niewykrywalna` dla wszystkich uczestników (bez OCR obrazów wyniku) – inaczej byłaby
oceniana, choć nie może wyciec nawet z kopii oryginału.

**Identyfikacja pośrednia** (H5, `ocen_plik(posrednie=…)` – pole manifestu, `pbench.posrednie`; osobna miara poza punktami):
kombinacja jest przerwana, gdy któryś jej składnik NIE jest widoczny w wyniku. Składnik to wartość (`wartosci_skladnikow`: składnik
gold – z kategorią swojej wartości, składnik spoza gold – z kategorią reguły `posrednie.kategoria_reguly(rola)`) oceniana tymi samymi
regułami i widokami co gold (części, obrazy osadzone i OCR stron z drugim/trzecim odczytem – `_ocen_z_odczytami`), osobną grupą
(jedna wartość), z wynikiem poza `wycieki`; widoczny = trafienie „pelny” całego tekstu składnika ALBO jego rdzenia (pole `rdzen`,
`posrednie.odcinki_rdzenia`: kolejne fragmenty rdzenia rozdzielone tylko znakami niealfanumerycznymi tworzą odcinek – „50°10′32.3” –
i każdy odcinek jest osobną wartością; rdzeń widoczny = wszystkie odcinki „pelny”). Bez offsetów odcinek da się szukać tylko wtedy,
gdy sam może wyciec (reguły pkt 2–3: liczba ≥ `min_cyfr_id` cyfr, identyfikator ≥ 6 znaków, słowo ≥ `min_dl_tokenu`) i jego
pełna wartość występuje w tekście oryginału dokładnie raz, i gdy jest widoczny w oryginale (`ZbioryDokumentu.rdzenie` – wspólne
dla uczestników); inaczej składnik jest szukany tylko całym tekstem (wiek „47-letni”, numer szkoły, krótkie numery działki – tu
zamaskowanie samej etykiety przerywa kombinację; sędzia tekstowy ocenia rdzeń zawsze). Słowa generyczne dla składników liczone są
bez wystąpień gold i składników (tekst składnika spoza gold nie jest gold, ale nie może być „słowem generycznym” samego siebie);
grupy, zbiory i wynik miary głównej się nie zmieniają. Kombinacja jest oceniana tylko wtedy, gdy WSZYSTKIE jej składniki są
widoczne (całym tekstem) w ORYGINALE (linia bazowa składników, wspólna dla uczestników – `ZbioryDokumentu.skladniki_bazowe`);
inaczej `przerwana` = None (nieoceniona).

Status pliku nieczytelnego/pustego: `wycieki` puste (nie ma czego ocenić), `integralnosc.otwiera_sie` False – to dane
dla agregatora (nieczytelny wynik to porażka uczestnika, nie brak wycieków). PDF bez warstwy tekstowej i bez obrazów osadzonych
(strona jako obraz inline, tekst jako ścieżki), na którego stronach OCR czyta tekst, nie jest pusty – jest oceniany.
"""
from __future__ import annotations

import dataclasses
import difflib
import functools
import math
import re
from bisect import bisect_left
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from .. import posrednie as _posrednie
from ..model import KATEGORIE, Wartosc
from ..translit import ma_cyrylice
from . import ekstrakcja, obrazy
from .ekstrakcja import Czesc, Wydobycie, wydobadz
from .normalizacja import (ile_inicjalow, ma_znaki_szkieletu, normalizuj, polacz_przeniesienia, same_alnum, szkielet,
                           wzor_inicjalow, zloz_diakrytyki, zloz_szkielet)
from .tekst import ETYKIETY_ID, KATEGORIE_INICJALOW, SLOWA_OPISOWE, RegulyWycieku, _ignorowane, zakresy_etykiet

_SLOWO = re.compile(r"\w+")
_SLOWO_LUB_ZNAK = re.compile(r"\w+|[^\w\s]")
#: Rdzeń odmienionego tokenu: ułamek długości i minimum; słowo wyniku nie może być dłuższe niż token + tyle znaków.
MIN_BAZA_ODMIANY = 4
#: Końcówki fleksyjne (PL): rzeczowniki/nazwiska oraz rodzina przymiotnikowa (-ski/-cki/-dzki). Tylko dla języka „pl”;
#: EN/ES/DE/FR bez reguły rdzenia (Richards ≠ Richardson), DE: tylko dopełniacz -s.
KONCOWKI_PL: tuple[str, ...] = ("", "a", "owi", "em", "iem", "u", "ie", "ego", "emu", "im", "ą", "ej", "y", "ów", "om",
                                "ami", "ach", "owie", "ę", "e", "i")
KONCOWKI_PRZYM_PL: tuple[str, ...] = ("ki", "kiego", "kiemu", "kim", "kiej", "ką", "ka", "kie", "cy", "kich", "kimi")
_PRZYM = re.compile(r"^(.*?[sc]|.*?dz)(ki|ka|kie)$")
MIN_DL_ID = 6
MIN_CYFR_KWOTY = 5
#: (J3) Wartość krótka: najwyżej tyle znaków alfanumerycznych – razem z inicjałami nie jest szukana w widokach binarnych
#: strumieni OLE (`ekstrakcja.Czesc.binarna`): dwa–trzy znaki trafiają przypadkowo w bajty zdekodowane jako tekst.
MAKS_ALNUM_KROTKIEJ = 3
#: (J3) Kod pocztowy (`KOD_POCZTOWY` w `tekst.KATEGORIE_ID`) – identyfikator już od tylu znaków alfanumerycznych (kody PL, DE, ES,
#: FR, US, UA – 5 cyfr, GB – 5–7 znaków): wyciek, gdy cały ciąg występuje z granicami, z separatorami albo bez.
MIN_DL_KODU = 5
#: Kategorie ze słabymi tokenami (rok, kwota bez waluty): sędzia plikowy traktuje je jak identyfikatory – wyciek, gdy
#: cała wartość (same litery i cyfry, ≥ 6 znaków) występuje w tekście. Sam rok „2025” z metadanych pliku
#: (daty utworzenia) nie jest wyciekiem daty „08/07/2025”. Krótsze (np. „50 zł”) – nie mogą wyciec.
KATEGORIE_JAK_ID: frozenset[str] = frozenset({"DATA", "DATA_UR", "KWOTA"})
#: Etykiety, z których uczestnicy budują zamienniki – wspólne dla WSZYSTKICH uczestników (ochrona reguł OCR nie może dotyczyć
#: słownictwa jednego z nich). Źródła (kod i konfiguracja uczestników w repozytorium – nie słowa wyniku):
#: * benchmark (`sanity.Maskowanie`, `Czesciowe`: „[KATEGORIA_n]”) – `model.KATEGORIE` (dokładane w `SLOWA_ZAMIENNIKOW`);
#: * Privatizer (`uczestnicy/privatizer-plik`, token „[{KAT}_{NR}]”, `vendor/privatizer/v1.3.0b9`): klucze kategorii
#:   (`lgprivatizer/categories.py`, profil PL) i `ETYKIETY_TOKENOW` profili EN/ES/DE/FR (`lgprivatizer/jezyki/*.py`);
#: * etykiety natywne narzędzi – klucze `uczestnicy/*/etykiety.json` i `uczestnicy/_wspolne/etykiety_presidio.json` (Presidio:
#:   operator „replace” anonimizatora wstawia „<ETYKIETA>”, np. „<PERSON>”; GLiNER: „name”, „email address”…; OpenAI Privacy
#:   Filter: „private_person”…; Stanza: „PER”, „ORG”). Pilnuje tego `tests/test_h4a.py` (klucze plików `etykiety.json`
#:   uczestników z poziomem „plik”; uczestnicy wyłącznie tekstowi, np. `ai4privacy`, nie oddają plików).
#: Zamazanie znakami („xxxx”, `uczestnicy/_atrapa`) nie potrzebuje wpisu: żaden token gold nie jest do niego podobny.
#: Słów z warstwy tekstowej wyniku celowo nie dokładamy – uczestnik mógłby dopisać niewidoczne warianty tokenów gold.
ETYKIETY_ZAMIENNIKOW: tuple[str, ...] = (
    # Privatizer, profil PL (klucze kategorii spoza `model.KATEGORIE`)
    "GPS", "WIEK", "KOD_KRESKOWY",
    # Privatizer, EN
    "PERSON", "INITIALS", "ORGANIZATION", "USERNAME", "ADDRESS", "POSTCODE", "CITY", "COUNTRY", "PHONE", "ID_CARD", "PASSPORT",
    "DRIVING_LICENCE", "ID_NUMBER", "VEHICLE_REG", "LAND_REGISTER", "CASE_NO", "REGISTER_NO", "REFERENCE_NO", "RNOKPP", "UNZR",
    "TAX_ID", "VAT_NO", "BANK_ACCOUNT", "CRYPTO", "CARD", "AMOUNT", "HEALTH", "DOB", "BIRTHPLACE", "DATE", "AGE", "SECRET",
    "FACE", "BARCODE", "CUSTOM",
    # Privatizer, ES
    "PERSONA", "INICIALES", "ORGANIZACION", "USUARIO", "DIRECCION", "CODIGO_POSTAL", "CIUDAD", "PAIS", "TELEFONO",
    "DOC_IDENTIDAD", "PASAPORTE", "PERMISO_CONDUCIR", "NUM_IDENTIFICACION", "MATRICULA", "REGISTRO_PROPIEDAD", "NUM_AUTOS",
    "NUM_REGISTRO", "NUM_REFERENCIA", "NUM_FISCAL", "NUM_IVA", "CUENTA_BANCARIA", "CRIPTO", "TARJETA", "IMPORTE", "SALUD",
    "FECHA_NAC", "LUGAR_NAC", "FECHA", "EDAD", "SECRETO", "CARA", "CODIGO_BARRAS", "PERSONALIZADO",
    # Privatizer, DE
    "INITIALEN", "ORGANISATION", "BENUTZERNAME", "ADRESSE", "PLZ", "ORT", "LAND", "AUSWEIS", "PASS", "FUEHRERSCHEIN",
    "ID_NUMMER", "KENNZEICHEN", "GRUNDBUCH", "AKTENZEICHEN", "REGISTERNUMMER", "REFERENZNUMMER", "STEUERNUMMER", "USTIDNR",
    "BANKKONTO", "KARTE", "BETRAG", "GESUNDHEIT", "GEBURTSDATUM", "GEBURTSORT", "DATUM", "ALTER", "GEHEIMNIS", "GESICHT",
    "STRICHCODE", "EIGENE",
    # Privatizer, FR
    "PERSONNE", "INITIALES", "IDENTIFIANT", "CODE_POSTAL", "VILLE", "PAYS", "TELEPHONE", "CNI", "PASSEPORT", "PERMIS_CONDUIRE",
    "NUM_IDENTIFICATION", "IMMATRICULATION", "CADASTRE", "NUM_RG", "NUM_RCS", "NUM_REFERENCE", "NUM_TVA", "COMPTE_BANCAIRE",
    "CARTE", "MONTANT", "SANTE", "DATE_NAISSANCE", "LIEU_NAISSANCE", "VISAGE", "CODE_BARRES", "PERSONNALISE",
    # Presidio (`_wspolne/etykiety_presidio.json`, `presidio-*/etykiety.json`)
    "LOCATION", "DATE_TIME", "EMAIL_ADDRESS", "PHONE_NUMBER", "IP_ADDRESS", "MAC_ADDRESS", "IBAN_CODE", "CREDIT_CARD",
    "MEDICAL_LICENSE", "MEDICAL_CONDITION", "NRP", "MONEY", "DRIVER_LICENSE", "HEALTH_INSURANCE", "LICENSE_PLATE",
    "NATIONAL_ID", "POSTAL_CODE", "REGISTRATION_NUMBER", "US_SSN", "US_ITIN", "US_PASSPORT", "US_DRIVER_LICENSE",
    "US_BANK_NUMBER", "US_MBI", "US_NPI", "UK_NHS", "UK_NINO", "UK_PASSPORT", "UK_POSTCODE", "UK_DRIVING_LICENCE",
    "UK_VEHICLE_REGISTRATION", "PL_PESEL", "PL_NIP", "PL_REGON", "PL_KRS", "PL_ID_CARD", "ES_NIF", "ES_NIE", "ES_PASSPORT",
    "DE_TAX_ID", "DE_TAX_NUMBER", "DE_VAT_ID", "DE_ID_CARD", "DE_PASSPORT", "DE_SOCIAL_SECURITY", "DE_HEALTH_INSURANCE",
    "DE_KFZ", "DE_FUEHRERSCHEIN", "DE_HANDELSREGISTER", "DE_PLZ", "DE_LANR", "DE_BSNR", "ID",
    # Stanza (`stanza/etykiety.json`)
    "PER", "ORG", "LOC",
    # GLiNER (`gliner-*/etykiety.json`) i OpenAI Privacy Filter (`openai-privacy-filter/etykiety.json`)
    "name", "first_name", "last_name", "person", "organization", "company_name", "address", "street_address", "city", "county",
    "state", "country", "postcode", "postal code", "email", "email address", "phone number", "phone_number", "fax_number",
    "date", "date of birth", "date_of_birth", "dob", "url", "ip address", "ipv4", "ipv6", "mac_address", "iban", "bank account",
    "bank account number", "account_number", "bank_routing_number", "swift_bic", "credit card", "credit card number",
    "credit_debit_card", "location address", "location street", "location city", "location state", "location country",
    "location zip", "passport number", "driver license", "driver's license number", "identity card number",
    "national id number", "social security number", "ssn", "tax identification number", "tax_id", "registration number",
    "license plate number", "license_plate", "vehicle id", "vehicle_identifier", "health insurance number", "healthcare number",
    "health_plan_beneficiary_number", "medical condition", "medical_record_number", "condition", "blood_type", "money",
    "username", "user_name", "password", "pin", "secret", "api_key", "unique_id", "customer_id", "employee_id",
    "certificate_license_number", "device_identifier",
    "private_person", "private_address", "private_email", "private_phone", "private_url", "private_date",
)
#: Słowa zamienników (`model.KATEGORIE` i `ETYKIETY_ZAMIENNIKOW`, małymi literami: cała etykieta oraz jej części po „_”, spacji
#: i apostrofie). Chronią tylko w KONTEKŚCIE ZAMIENNIKA (`maskuj_zamienniki`): takie słowo w tekście OCR jest zastępowane
#: neutralnym znakiem, więc nie jest pojedynczym tokenem wycieku i nie trafia rozmyto tokenu wartości – tak samo dla każdego
#: uczestnika. Poza kontekstem zamiennika (nazwisko „Alter” obok „[PERSON]”) to zwykłe słowo.
SLOWA_ZAMIENNIKOW: frozenset[str] = frozenset(
    s for e in (*KATEGORIE, *ETYKIETY_ZAMIENNIKOW) for s in (e.casefold(), *re.split(r"[\s_']+", e.casefold())) if s)
#: Kontekst zamiennika w surowym tekście OCR (`maskuj_zamienniki`). Słowo (same litery) z `SLOWA_ZAMIENNIKOW` jest częścią
#: zamiennika, gdy:
#: 1. stoi w nawiasie zamiennika razem z innymi słowami zamienników, ewentualnie z numerem (`_ZAMIENNIK_W_NAWIASIE`: „[PERSON]”,
#:    „<PERSON>”, „{NAME}”, „(OSOBA 1)” – OCR czyta „[” też jako „(” –, „[credit card number]”, „[CODIGO POSTAL 3]”);
#: 2. dotyka – bez spacji – nawiasu: z lewej `OTWIERAJACE_ZAMIENNIK`, z prawej `ZAMYKAJACE_ZAMIENNIK` („[ADRES 21” – OCR zgubił
#:    „]”, „PERSON)”);
#: 3. po nim stoi numer (oddzielony co najwyżej spacjami i podkreślnikami: „OSOBA_1”, „OSOBA 1”, „PERSON 001” – OCR zgubił nawiasy).
#: Reguły 2 i 3 dotyczą tylko słów pisanych wersalikami (tak piszą zamienniki uczestnicy): zwykłe słowo wartości przy nawiasie albo
#: przed liczbą („account (Routing No. 281524457”, „de type 2”) zostaje słowem. Wersaliki bez nawiasu i numeru – jak niżej.
#: Sam podkreślnik nie jest ogranicznikiem: adres e-mail „jan_name@…” nie traci tokenu. Słowa krótsze niż `MIN_DL_SLOWA_ZAMIENNIKA`
#: nie są maskowane: to kody krajów („DE” z „DE_TAX_ID”) w numerach VAT i IBAN („DE893909084”), a same nie są tokenami wycieku.
#: Wielkie litery same w sobie NIE są kontekstem: nazwiska w pismach bywają pisane wersalikami („Pierre DUPONT”, „Hans ALTER”).
#: „[PERSON] Alter” – „Alter” nie dotyka nawiasu (spacja) i nie ma po nim numeru, więc jest zwykłym słowem (wyciek częściowy).
OTWIERAJACE_ZAMIENNIK = "[<{("
ZAMYKAJACE_ZAMIENNIK = "]>})"
_ZAMIENNIK_W_NAWIASIE = re.compile(r"[\[<{(]\s*([^\W\d_]+(?:[ _]+[^\W\d_]+)*)(?:[ _]*\d+)?\s*[\]>})]")
_LITERY = re.compile(r"[^\W\d_]+")
_NUMER_PO = re.compile(r"[ _]*\d")
MIN_DL_SLOWA_ZAMIENNIKA = 3
#: Znak, którym `maskuj_zamienniki` zastępuje każdą literę słowa zamiennika: litera (słowo zostaje słowem, rozdziela tokeny i ciągi
#: identyfikatorów jak przedtem), niezmieniana przez NFKC ani casefold i niepodobna do żadnego tokenu gold.
ZNAK_ZAMIENNIKA = "ǂ"


def maskuj_zamienniki(surowy: str) -> str:
    """(OCR) Surowy tekst OCR ze słowami zamienników w kontekście zamiennika (zob. `OTWIERAJACE_ZAMIENNIK`) zastąpionymi znakiem
    `ZNAK_ZAMIENNIKA` (ta sama długość)."""
    miejsca: list[tuple[int, int]] = []
    for m in _ZAMIENNIK_W_NAWIASIE.finditer(surowy):
        slowa = list(_LITERY.finditer(m.group(1)))
        if all(normalizuj(s.group()) in SLOWA_ZAMIENNIKOW for s in slowa):
            miejsca += [(m.start(1) + s.start(), m.start(1) + s.end()) for s in slowa
                        if len(s.group()) >= MIN_DL_SLOWA_ZAMIENNIKA]
    for m in _LITERY.finditer(surowy):
        if len(m.group()) < MIN_DL_SLOWA_ZAMIENNIKA or normalizuj(m.group()) not in SLOWA_ZAMIENNIKOW:
            continue
        a, b = m.span()
        if not m.group().isupper():
            continue
        if (a and surowy[a - 1] in OTWIERAJACE_ZAMIENNIK) or surowy[b:b + 1] in tuple(ZAMYKAJACE_ZAMIENNIK) \
                or _NUMER_PO.match(surowy, b):
            miejsca.append((a, b))
    if not miejsca:
        return surowy
    znaki = list(surowy)
    for a, b in miejsca:
        znaki[a:b] = ZNAK_ZAMIENNIKA * (b - a)
    return "".join(znaki)
#: Znaki mylone przez OCR (litera ↔ cyfra o podobnym kształcie; Tesseract myli je w obie strony): przed porównaniem
#: identyfikatorów, dat, kwot i tokenów z cyfrą w OCR obie strony są składane („2O25” = „2025”, „l. Juli” = „1. Juli”,
#: „Z1.” = „21.”, „I48” = „148”). Różne cyfry („29.11.” i „28.11.”, „17” i „7”) pozostają różne.
ZNAKI_MYLONE_OCR: dict[str, str] = {"o": "0", "i": "1", "l": "1", "z": "2", "s": "5", "b": "8"}
_MYLONE = str.maketrans(ZNAKI_MYLONE_OCR)
#: Dopasowanie rozmyte (difflib) identyfikatora w OCR – tylko kategorie `KATEGORIE_ID` z co najmniej tyloma znakami
#: alfanumerycznymi (IBAN, PESEL, NIP) i z granicami. Krótszy identyfikator, data i kwota – tylko dokładnie (po złożeniu znaków
#: mylonych): w krótkim ciągu jedna inna cyfra to inna wartość („29.11.2022” ≠ „28.11.2022”, „912345678” ≠ „12345678”).
MIN_DL_ID_ROZMYTEGO = 10
#: (OCR) Token dopasowywany rozmyto ma co najmniej `MIN_DL_SLOWA_ROZMYTEGO` znaków, a słowo OCR – `MIN_DL_SLOWA_OCR_ROZMYTEGO`: krótkie
#: śmieci OCR („ana”, „ema”, z linii tabel „EICH”, „MARA”) mają podobieństwo ≥ 0,85 do tokenów dłuższych o jedną literę („anna”,
#: „Erich”, „Maria”) i powtarzają się w odczytach psm 6 w obu rozdzielczościach. Słowo 4-literowe i tak nie trafia rozmyto tokenu
#: 4-literowego (jedna zamiana = 0,75), więc próg 5 odrzuca tylko token 5-literowy przeczytany o literę za krótko.
MIN_DL_SLOWA_ROZMYTEGO = 4
MIN_DL_SLOWA_OCR_ROZMYTEGO = 5
#: (OCR, data i kwota – `_wzor_daty_ocr`) Litery, które OCR czyta w miejscu cyfry: `ZNAKI_MYLONE_OCR` oraz „b” także w miejscu 6
#: (kształt pośredni między 6 a 8), „g” w miejscu 6 i „t” w miejscu 7. Cyfra wartości trafia siebie albo jedną z tych liter;
#: inna CYFRA nigdy („29.11.” ≠ „28.11.”), więc „b” pasuje do 6 i do 8 bez łączenia cyfr odczytanych poprawnie.
LITERY_ZA_CYFRY_OCR: dict[str, str] = {**{c: "" for c in "0123456789"}, "0": "o", "1": "il", "2": "z", "5": "s", "6": "bg",
                                       "7": "t", "8": "b"}
#: (OCR, data i kwota) Ciąg liter wartości (nazwa miesiąca, waluta, „r.”) w OCR: trafia, gdy podobieństwo ≥ tyle (difflib, po
#: złożeniu diakrytyków i znaków mylonych) albo różni się jedną zmianą (od 4 liter: „Jume” = „June”, „Mürz” = „März”).
PROG_LITER_DATY = 0.8
MIN_DL_JEDNEJ_ZMIANY = 4
#: (OCR, data) Ciąg liter na brzegu daty (przed pierwszą / po ostatniej liczbie) najwyżej tak długi jest opcjonalny („r.” – OCR
#: gubi go albo czyta „1.”, „т.”); dłuższy (nazwa miesiąca: „June 3, 2024”) jest wymagany. W kwocie każdy ciąg liter na brzegu
#: (waluta: „zł”, „EUR”) jest opcjonalny. Krótki ciąg liter między liczbami („3 de junio de 2024”) – dowolne ≤ 3 litery.
MAKS_LITER_OPCJONALNYCH = 2
#: Nazwy miesięcy (pl, en, de, es, fr, uk; mianownik i dopełniacz, skróty): ciąg liter OCR równy INNEJ nazwie miesiąca to inna data,
#: choć różni się jedną literą („Juli” ≠ „Juni”, „julio” ≠ „junio” – np. przesunięcie daty o miesiąc przez uczestnika).
NAZWY_MIESIECY: tuple[str, ...] = (
    "styczeń", "stycznia", "luty", "lutego", "marzec", "marca", "kwiecień", "kwietnia", "maj", "maja", "czerwiec", "czerwca",
    "lipiec", "lipca", "sierpień", "sierpnia", "wrzesień", "września", "październik", "października", "listopad", "listopada",
    "grudzień", "grudnia",
    "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
    "januar", "jänner", "februar", "märz", "mai", "juni", "juli", "oktober", "dezember", "mrz", "okt", "dez",
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "setiembre", "octubre", "noviembre",
    "diciembre",
    "janvier", "février", "mars", "avril", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre", "janv",
    "févr", "avr", "juil",
    "січень", "лютий", "березень", "квітень", "травень", "червень", "липень", "серпень", "вересень", "жовтень", "листопад",
    "грудень", "січня", "лютого", "березня", "квітня", "травня", "червня", "липня", "серпня", "вересня", "жовтня", "листопада",
    "грудня",
)


def zloz_mylone(tekst: str) -> str:
    """Tekst (znormalizowany, małymi literami) ze złożonymi znakami mylonymi przez OCR (`ZNAKI_MYLONE_OCR`); długość bez zmian."""
    return tekst.translate(_MYLONE)


def _klucz_liter(s: str) -> str:
    """(OCR, data i kwota) Ciąg liter do porównania: bez diakrytyków, ze złożonymi znakami mylonymi."""
    return zloz_mylone(zloz_diakrytyki(s))


_MIESIACE: frozenset[str] = frozenset(_klucz_liter(normalizuj(m)) for m in NAZWY_MIESIECY)
#: Adres e-mail / URL w OCR: znak „@” bywa czytany jako litera („rsorianofpoufne.example”), co skleja tokeny w jedno słowo.
#: Taka wartość (≥ `MIN_DL_ALNUM_OCR` znaków alfanumerycznych) jest szukana także jako ciąg alfanumeryczny, rozmyto z progiem
#: `PROG_ALNUM_OCR` (wyższym niż dla tokenów: dwa adresy w tej samej domenie różnią się często tylko częścią lokalną).
KATEGORIE_ALNUM_OCR: frozenset[str] = frozenset({"EMAIL", "URL"})
MIN_DL_ALNUM_OCR = 12
PROG_ALNUM_OCR = 0.93
#: (OCR obrazu osadzonego) Token identyfikujący co najmniej tej długości, który jest słowem odczytu DOKŁADNIE, liczy się jako
#: trafienie częściowe z jednego odczytu obrazu – bez potwierdzenia (`_trafienia_ocr`). Szum OCR, przed którym chroni
#: potwierdzenie, to trafienia rozmyte („Osowa” z miniatury ODT ≈ „Sowa”) albo krótkie słowa („EMA” z okaleczonego zamiennika,
#: „ray” z linii tabeli); dokładne słowo ≥ 7 znaków równe tokenowi wartości szumem nie jest, a mały obraz (pieczątka 348×168,
#: zrzut 360×156) bywa czytany dokładnie tylko w jednym odczycie. Dotyczy tylko obrazów osadzonych – na stronach PDF (H4a R1)
#: trafienie częściowe zawsze wymaga potwierdzenia.
MIN_DL_TOKENU_BEZ_POTWIERDZENIA = 7
#: (Inicjały w OCR obrazów osadzonych, `_bez_szumu`) Wiersz odczytu jest szumem, gdy ma co najmniej `MIN_SLOW_SZUMU` tokenów
#: szumu – ≥ `MIN_DL_SLOWA_SZUMU` liter, samymi wielkimi literami, nie z jednej powtórzonej litery, łącznie z najwyżej
#: `MAKS_LITER_SZUMU` różnych liter – i żaden jego token literowy
#: ≥ `MIN_DL_SLOWA_SZUMU` liter nie jest słowem dokumentu (`_Grupa.slownik`, bez znaków diakrytycznych). Znak maskujący powtórzony
#: w obrazie (logo zastąpione wierszem gwiazdek) OCR czyta w każdym odczycie jako ten sam ciąg wielkich liter („ARAHAL AC AE …
#: ERRE ARRE RR AR”), w którym krótki wzorzec inicjałów trafia przypadkowo. Wiersz z prawdziwą parafą ma etykietę z tekstu dokumentu
#: („Referencia: ar/jc”), jest krótki (sama parafa we wycinku) albo obok parafy stoją słowa pisane zwykle (zamienniki uczestnika
#: „Martínez Herrera Abogados Asociados A.R.”, także wielkimi literami – 15 różnych liter) czy maska z jednej litery („XXXX XXXXX
#: A.R.”) – żaden z nich nie jest szumem.
MIN_SLOW_SZUMU = 4
MIN_DL_SLOWA_SZUMU = 3
#: (`_bez_szumu`) Tokeny szumu wiersza mają łącznie najwyżej tyle różnych liter (bez diakrytyków). Szum gwiazdek w każdym odczycie
#: obrazu osadzonego (pierwszy, bez pól, drugi w skali ×2): 5–6 liter (A, R, E, H/L/C/S/N); cztery prawdziwe słowa wielkimi
#: literami – nagłówek z zamiennikami „MARTÍNEZ HERRERA ABOGADOS ASOCIADOS A.R.” – 15. Próg 8 zostawia margines po obu stronach.
MAKS_LITER_SZUMU = 8
#: Łączy wiersze odczytu po usunięciu wierszy szumu: nie jest białym znakiem ani literą, więc wzorzec inicjałów (`\\s*` po kropce)
#: nie przechodzi przez miejsce usuniętego wiersza.
_ODDZIELACZ_WIERSZY = "\n|\n"


#: Miejsca gold, których wartości muszą stać w tekście stron PDF (rysowane jako tekst, nie obraz).
MIEJSCA_TEKSTU_STRONY = ("tresc", "tabela", "naglowek", "stopka", "przypis")
#: Poniżej tego udziału odnalezionych wartości tekstowych gold warstwa tekstowa PDF jest uznana za zepsutą (od 3 wartości).
PROG_POKRYCIA_TEKSTU = 0.9
MIN_WARTOSCI_POKRYCIA = 3
#: Tyle znaków sterujących (poza \\t \\n \\r) w tekście stron wystarcza: PDFium oddaje nimi znaki bez mapy ToUnicode.
MIN_ZNAKOW_STERUJACYCH = 3
def _tekst_stron(w: Wydobycie) -> str:
    return "\n".join(c.caly_tekst() for c in w.czesci if c.tresc and c.nazwa.startswith("pdf:strona"))


def _ma_znaki_sterujace(tekst: str) -> bool:
    return sum(1 for ch in tekst if ord(ch) < 32 and ch not in "\t\n\r") >= MIN_ZNAKOW_STERUJACYCH


def warstwa_tekstowa_zepsuta(w: Wydobycie, wartosci: Iterable[Wartosc]) -> bool:
    """Czy warstwa tekstowa PDF-a nie zawiera spodziewanych znaków: mniej niż `PROG_POKRYCIA_TEKSTU` wartości tekstowych gold
    (miejsca `MIEJSCA_TEKSTU_STRONY`, ≥ 4 znaki alfanumeryczne; od `MIN_WARTOSCI_POKRYCIA` wartości) występuje w tekście stron
    (porównanie alfanumeryczne) albo tekst stron ma ≥ `MIN_ZNAKOW_STERUJACYCH` znaków sterujących."""
    if w.rodzaj != "pdf" or w.status != "OK":
        return False
    tekst = _tekst_stron(w)
    if _ma_znaki_sterujace(tekst):
        return True
    oczekiwane = {same_alnum(x.tekst) for x in wartosci if not x.w_pikselach and x.miejsce in MIEJSCA_TEKSTU_STRONY}
    oczekiwane = {t for t in oczekiwane if len(t) >= 4}
    if len(oczekiwane) < MIN_WARTOSCI_POKRYCIA:
        return False
    calosc = same_alnum(tekst)
    return sum(1 for t in oczekiwane if t in calosc) / len(oczekiwane) < PROG_POKRYCIA_TEKSTU


def zepsute_pdfy_poczty(w: Wydobycie, wartosci: Iterable[Wartosc], ocr_stron: list[tuple[str, str]]) -> set[str]:
    """Przedrostki PDF-ów w załącznikach wiadomości (`Wydobycie.pdfy`), których warstwa tekstowa jest zepsuta – kryterium jak
    `warstwa_tekstowa_zepsuta` dla samodzielnego PDF-u: ≥ `MIN_ZNAKOW_STERUJACYCH` znaków sterujących w tekście jego stron albo
    poniżej `PROG_POKRYCIA_TEKSTU` oczekiwanych wartości w tekście jego stron (od `MIN_WARTOSCI_POKRYCIA`). Gold nie mówi, w którym
    załączniku leży wartość (miejsce `zalacznik` mają wszystkie), więc oczekiwane są wartości tekstowe gold (≥ 4 znaki
    alfanumeryczne), które OCR stron tego PDF-u (`ocr_stron`, nazwy z przedrostkiem PDF-u) czyta dokładnie – widoczne na stronie."""
    if w.rodzaj not in RODZAJE_POCZTY or w.status != "OK":
        return set()
    przedrostki = list(dict.fromkeys(p for p, _ in w.pdfy))
    kandydaci = {same_alnum(x.tekst) for x in wartosci if not x.w_pikselach}
    kandydaci = {t for t in kandydaci if len(t) >= 4}
    zepsute: set[str] = set()
    for p in przedrostki:
        tekst = "\n".join(c.caly_tekst() for c in w.czesci if c.tresc and _pdf_nazwy(c.nazwa, przedrostki) == p
                          and c.nazwa[len(p):].startswith("pdf:strona"))
        if _ma_znaki_sterujace(tekst):
            zepsute.add(p)
            continue
        render = same_alnum("\n".join(t for n, t in ocr_stron if _pdf_nazwy(n, przedrostki) == p))
        oczekiwane = {t for t in kandydaci if t in render}
        if len(oczekiwane) < MIN_WARTOSCI_POKRYCIA:
            continue
        calosc = same_alnum(tekst)
        if sum(1 for t in oczekiwane if t in calosc) / len(oczekiwane) < PROG_POKRYCIA_TEKSTU:
            zepsute.add(p)
    return zepsute


@dataclass
class OcenaPliku:
    """Wynik oceny pliku wynikowego uczestnika względem oryginału i gold."""

    status: str                                      # "OK" | "NIECZYTELNY" | "PUSTY"
    #: (wartosc_id, kategoria, miejsce w wyniku – nazwa części / obraz-OCR, rodzaj "pelny"|"czesciowy").
    wycieki: list[tuple[str, str, str, str]]
    integralnosc: dict
    #: identyfikatory wartości obrazowych wyłączonych z oceny (OCR nie znajduje ich w oryginale).
    niewykrywalne: list[str] = field(default_factory=list)
    #: identyfikatory wartości wyłączonych jako niejednoznaczne (tekst występuje w oryginale poza wystąpieniami gold).
    niejednoznaczne: list[str] = field(default_factory=list)
    #: liczba ocenianych wartości, które mogły wyciec (miały liczący się fragment), bez niewykrywalnych.
    wartosci_ocenione: int = 0
    #: linia bazowa: identyfikatory wartości, które sędzia odnajduje w ORYGINALE (wspólne dla wszystkich uczestników);
    #: `wartosci_ocenione` = |bazowe ∪ wycieki|.
    bazowe: list[str] = field(default_factory=list)
    #: identyfikacja pośrednia: po kombinacji `{id, rodzaj, przerwana: bool|None, widoczne: [id składników]}`; None – ocena bez
    #: pola `posrednie` albo wynik nieczytelny/pusty.
    posrednie: list[dict] | None = None
    #: nadmiarowe maskowanie tekstu widocznego (P5, `nadmiarowe`): `{"znaki", "poza_gold"}`; None – wynik nieczytelny/pusty.
    nadmiarowe: dict | None = None


def encja(wid: str) -> str:
    """Rola wartości: identyfikator bez numeru wystąpienia (`#n`) i bez przyrostka `@obraz`."""
    return wid.removesuffix("@obraz").rsplit("#", 1)[0]


def jezyk_wartosci(wartosci: Iterable[Wartosc]) -> str:
    """Język dokumentu = najczęstszy `Wartosc.jezyk` (języki OCR: pl, en, es, de, fr, uk)."""
    licz = Counter(w.jezyk for w in wartosci)
    return licz.most_common(1)[0][0] if licz else "pl"


def jezyk_ocr(wartosci: Iterable[Wartosc], jezyk: str) -> str:
    """Język OCR: dokument z wartościami w cyrylicy (poza dokumentem `uk`) czytamy też danymi `ukr` (`pl` → `pl+uk`)."""
    if jezyk != "uk" and "+" not in jezyk and any(ma_cyrylice(w.tekst) for w in wartosci):
        return f"{jezyk}+uk"
    return jezyk


# ----------------------------------------------------------------------------- tekst przygotowany do szukania
class Tekst:
    """Tekst części (linie + widoki dodatkowe) znormalizowany raz: do wyszukiwania pełnych fraz, słów i identyfikatorów."""

    __slots__ = ("norm", "alnum", "slowa", "posortowane", "_zlozony", "_mylone", "_slowa_mylone", "_ciag", "_dlugie",
                 "_cyrylica", "_szkielet")

    def __init__(self, surowy: str, norm: str | None = None) -> None:
        self.norm = normalizuj(surowy) if norm is None else norm
        self.alnum = same_alnum(surowy) if norm is None else "".join(c for c in norm if c.isalnum())
        self.slowa = set(_SLOWO.findall(self.norm))
        self.posortowane = sorted(self.slowa)
        self._zlozony: Tekst | None = None
        self._mylone: Tekst | None = None
        self._slowa_mylone: dict[str, set[str]] | None = None
        self._ciag: list[str] | None = None
        self._dlugie: set[str] | None = None
        self._cyrylica: bool | None = None
        self._szkielet: Tekst | None = None

    def dlugie(self) -> set[str]:
        """(OCR) Słowa tekstu, które mogą trafić rozmyto (≥ `MIN_DL_SLOWA_OCR_ROZMYTEGO` znaków)."""
        if self._dlugie is None:
            self._dlugie = {s for s in self.slowa if len(s) >= MIN_DL_SLOWA_OCR_ROZMYTEGO}
        return self._dlugie

    def zlozony(self) -> "Tekst":
        """Ten sam tekst bez znaków diakrytycznych („Dabrowski” trafia „Dąbrowski”), w szkielecie (`normalizacja.szkielet`:
        homoglify cyrylicy i greki jako łacina – „Kоwalski” = „Kowalski”); bez nich szkielet niczego nie zmienia."""
        if self._zlozony is None:
            self._zlozony = Tekst("", norm=zloz_szkielet(self.norm))
        return self._zlozony

    def szkielet(self) -> "Tekst":
        """Ten sam tekst w szkielecie (`normalizacja.szkielet`), ze znakami diakrytycznymi."""
        if self._szkielet is None:
            self._szkielet = Tekst("", norm=szkielet(self.norm))
        return self._szkielet

    def ma_cyrylice(self) -> bool:
        """Czy tekst ma literę cyrylicy albo greki mylącą z łacińską (szkielet go zmienia) – warunek wariantu
        `Regula.tylko_cyrylica`."""
        if self._cyrylica is None:
            self._cyrylica = ma_znaki_szkieletu(self.norm)
        return self._cyrylica

    def mylone(self) -> "Tekst":
        """(OCR) Ten sam tekst ze złożonymi znakami mylonymi przez OCR (`zloz_mylone`)."""
        if self._mylone is None:
            self._mylone = Tekst("", norm=zloz_mylone(self.norm))
        return self._mylone

    def slowa_mylone(self) -> dict[str, set[str]]:
        """(OCR) Słowa tekstu po złożeniu znaków mylonych → słowa tekstu („148” → {„i48”, „148”})."""
        if self._slowa_mylone is None:
            self._slowa_mylone = {}
            for s in self.slowa:
                self._slowa_mylone.setdefault(zloz_mylone(s), set()).add(s)
        return self._slowa_mylone

    def ciag(self) -> list[str]:
        """Słowa tekstu w kolejności (fraza OCR, `_fraza_ocr`)."""
        if self._ciag is None:
            self._ciag = _SLOWO.findall(self.norm)
        return self._ciag


def _tekst_czesci(c: Czesc, cache: dict[int, Tekst]) -> Tekst:
    t = cache.get(id(c))
    if t is None:
        t = cache[id(c)] = Tekst(c.caly_tekst())
    return t


def _tokeny(tekst: str) -> list[str]:
    return _SLOWO.findall(normalizuj(tekst))


# ----------------------------------------------------------------------------- słowa generyczne oryginału
def _indeks_gold(wartosci: Iterable[Wartosc], tokeny: Callable[[str], list[str]] = _tokeny) -> dict[str, list[tuple[str, ...]]]:
    """Indeks tekstów wartości (znormalizowane tokeny) po pierwszym tokenie; kandydaci od najdłuższych."""
    indeks: dict[str, list[tuple[str, ...]]] = {}
    for tok in {tuple(tokeny(w.tekst)) for w in wartosci}:
        if tok:
            indeks.setdefault(tok[0], []).append(tok)
    for lista in indeks.values():
        lista.sort(key=len, reverse=True)
    return indeks


def _przejdz(tokeny: list[str], indeks: dict[str, list[tuple[str, ...]]], generyczne: set[str] | None,
             licznik: Counter | None) -> None:
    """Przechodzi po tokenach: wystąpienia tekstów gold (greedy, najdłuższy kandydat) są liczone w `licznik`,
    pozostałe słowa trafiają do `generyczne`."""
    i, n = 0, len(tokeny)
    while i < n:
        for kandydat in indeks.get(tokeny[i], ()):
            k = len(kandydat)
            if tuple(tokeny[i:i + k]) == kandydat:
                if licznik is not None:
                    licznik[kandydat] += 1
                i += k
                break
        else:
            if generyczne is not None:
                generyczne.add(tokeny[i])
            i += 1


def slowa_generyczne(czesci: Iterable[Czesc], teksty_ocr: Iterable[str], wartosci: Iterable[Wartosc]) -> set[str]:
    """Słowa oryginału poza wystąpieniami wartości gold (znormalizowane tokeny z linii i węzłów części – nie z widoków
    sklejonych/surowych – oraz OCR obrazów). Części strukturalne (style, czcionki…) są szablonem formatu: ich słowa są generyczne w całości."""
    indeks = _indeks_gold(list(wartosci))
    generyczne: set[str] = set()
    for c in czesci:
        # TYLKO teksty pojedynczych węzłów (linie, atrybuty, stringi): widoki sklejone/surowe zatruwałyby zbiór
        # sklejonymi „słowami” i słownictwem formatu
        for kawalek in (*c.linie, *c.wezly):
            _przejdz(_tokeny(kawalek), {} if c.strukturalna else indeks, generyczne, None)
    for t in teksty_ocr:
        _przejdz(_tokeny(t), indeks, generyczne, None)
    return generyczne


def niejednoznaczne(czesci: Iterable[Czesc], teksty_ocr: Iterable[str], wartosci: list[Wartosc],
                    strony: int = 1, ocr_stron: Iterable[str] = (), zloz: Callable[[str], str] | None = None) -> set[str]:
    """Identyfikatory wartości, których tekst występuje w oryginale CZĘŚCIEJ, niż jest wystąpień gold (np. miasto
    z nazwy sądu – nie jest gold – równe miastu adresu): wystąpienia nie da się odróżnić od wycieku, więc wartość jest
    wyłączona z oceny wszystkich uczestników (symetrycznie). Wartości tekstowe liczone są w częściach treści
    (`Czesc.tresc`, bez metadanych), obrazowe – w OCR obrazów oryginału; wystąpienia objęte dłuższą wartością gold
    (np. imię w „Jan Kowalski”) liczą się do niej. `strony` > 1 (PDF): nagłówek/stopka (`miejsce` naglowek/stopka) ma
    w gold jeden wpis, a w tekście jedno wystąpienie na stronę – oczekiwana krotność to liczba stron oryginału.
    `ocr_stron`: OCR stron PDF oryginału – podawany tylko wtedy, gdy jego warstwa tekstowa jest zepsuta (zob. docstring
    modułu, „Zbiory dokumentu”); wystąpienia wartości tekstowych liczone są wtedy także w nim; render pokazuje obok tekstu obrazy osadzone (logo, podpis), więc liczba z renderu jest
    porównywana z `gold_tekst + gold_obraz` (wartość niejednoznaczna, gdy przekracza którąkolwiek z dwóch miar); obraz
    z logo bywa narysowany na każdej stronie (jeden wpis gold, osadzony raz), więc wpisy obrazowe liczą się razy `strony`.
    `zloz` – tokeny porównywane w postaci złożonej (`normalizacja.zloz_szkielet`: wariant złożony `_Grupa.reg_z` – wartość
    niejednoznaczna w szkielecie traci tylko ten wariant, zob. `zbiory_dokumentu`). Inicjały (`KATEGORIE_INICJALOW`, wartości
    tekstowe) liczone są wzorcem sędziego (`normalizacja.wzor_inicjalow`), nie tokenami: niejednoznaczne, gdy wzorzec występuje
    w treści (albo w OCR stron) częściej niż wartości gold o tym samym zapisie."""
    czesci, ocr_stron = list(czesci), list(ocr_stron)
    tokeny = (lambda s: [zloz(t) for t in _tokeny(s)]) if zloz else _tokeny
    indeks = _indeks_gold(wartosci, tokeny)
    licznik_tekst: Counter = Counter()
    for c in czesci:
        if c.tresc and not c.strukturalna and not c.wariant:
            _przejdz(tokeny("\n".join(c.linie)), indeks, None, licznik_tekst)
    licznik_stron: Counter = Counter()      # render strony pokazuje też obrazy osadzone (logo, podpis)
    for t in ocr_stron:
        najwiecej_strony: Counter = Counter()
        for odczyt in t.split(obrazy.ODDZIELACZ):
            l: Counter = Counter()
            _przejdz(tokeny(odczyt), indeks, None, l)
            najwiecej_strony |= l
        licznik_stron.update(najwiecej_strony)
    licznik_ocr: Counter = Counter()
    for t in teksty_ocr:
        najwiecej: Counter = Counter()
        for odczyt in t.split(obrazy.ODDZIELACZ):
            l: Counter = Counter()
            _przejdz(tokeny(odczyt), indeks, None, l)
            najwiecej |= l
        licznik_ocr.update(najwiecej)
    gold_tekst: Counter = Counter()
    gold_obraz: Counter = Counter()
    for w in wartosci:
        if w.w_pikselach:
            gold_obraz[tuple(tokeny(w.tekst))] += 1
        elif w.miejsce != "metadane":
            gold_tekst[tuple(tokeny(w.tekst))] += strony if w.miejsce in ("naglowek", "stopka") else 1
    wynik = set()
    for w in wartosci:
        t = tuple(tokeny(w.tekst))
        if w.w_pikselach:
            if licznik_ocr[t] > gold_obraz[t]:
                wynik.add(w.id)
        elif w.miejsce != "metadane" and (licznik_tekst[t] > gold_tekst[t]
                                          or licznik_stron[t] > gold_tekst[t] + gold_obraz[t] * strony):
            wynik.add(w.id)
    # inicjały: wzorcem sędziego (granice, kropki), nie sekwencją tokenów („K.” ≠ każde „k” tekstu)
    inicjaly = [w for w in wartosci if w.kategoria in KATEGORIE_INICJALOW and not w.w_pikselach and w.miejsce != "metadane"]
    if inicjaly:
        tresc = [normalizuj("\n".join(c.linie)) for c in czesci if c.tresc and not c.strukturalna and not c.wariant]
        tekstowe = [v for v in wartosci if not v.w_pikselach and v.miejsce != "metadane"]
        strony_n = [[normalizuj(o) for o in t.split(obrazy.ODDZIELACZ)] for t in ocr_stron]
        for w in inicjaly:
            wynik.discard(w.id)
            wzor = wzor_inicjalow(w.tekst)
            # wystąpienia gold: trafienia wzorca w tekstach wartości gold („J.K.” i „J. K.”; „K.” także w „J.K.” tej samej osoby),
            # nagłówek/stopka – raz na stronę
            # (`normalizacja.ile_inicjalow` – ta sama miara w generatorach warstwy trudnej, `trudne_wspolne.inicjaly_jednoznaczne`)
            gold = sum((strony if v.miejsce in ("naglowek", "stopka") else 1) * ile_inicjalow(wzor, [normalizuj(v.tekst)])
                       for v in tekstowe)
            ile = ile_inicjalow(wzor, tresc)
            ile_stron = sum(max((ile_inicjalow(wzor, [o]) for o in odczyty), default=0) for odczyty in strony_n)
            if ile > gold or ile_stron > gold:
                wynik.add(w.id)
    return wynik


def _tokeny_wartosci(wartosci: Iterable[Wartosc], ids: set[str]) -> set[str]:
    """Tokeny wartości o podanych identyfikatorach (wartości niejednoznaczne: ich słowa występują też poza gold)."""
    return {t for w in wartosci if w.id in ids for t in _tokeny(w.tekst)}


# ----------------------------------------------------------------------------- reguła pojedynczej wartości
@dataclass
class Regula:
    """Przygotowana reguła wycieku jednej wartości."""

    id_alnum: tuple[str, ...] = ()           # identyfikator: ciągi alfanumeryczne (warianty zapisu)
    #: (ciąg alfanumeryczny do szybkiego filtra, wzorzec z granicami) – formatowanie wartości bywa różne.
    id_wzorce: tuple[tuple[str, re.Pattern], ...] = ()
    #: (OCR, identyfikator) warianty `id_alnum` ze złożonymi znakami mylonymi (`zloz_mylone`), szukane wzorcem z granicami
    id_mylone: tuple[str, ...] = ()
    #: (OCR, identyfikator) dopuszczone dopasowanie rozmyte z granicami (`KATEGORIE_ID`, ≥ `MIN_DL_ID_ROZMYTEGO` znaków)
    id_rozmyte: bool = False
    #: (identyfikator z etykietą, J1) części – ciągi alfanumeryczne między etykietami `tekst.ETYKIETY_ID` z wzorcem z granicami
    #: (zob. docstring modułu, pkt 2d); puste – wartość bez etykiet
    id_czesci: tuple[tuple[str, re.Pattern], ...] = ()
    #: (sygnatura, J1-fix2) części opisowe spośród `id_czesci` (wydział, repertorium, rodzaj postępowania)
    id_opisowe: frozenset[str] = frozenset()
    #: próg wycieku częściowego jedną częścią: `MIN_DL_ID`; sygnatura (J1-fix3, m1) – `min_cyfr_id` dla każdej części (opisowej
    #: i numeru), jak w sędzi tekstowym
    id_prog_czesci: int = MIN_DL_ID
    #: (J1-fix3, I1) części, których w ocenianym pliku nie ma więcej niż w oryginale poza wystąpieniami gold (cytat innej sprawy
    #: z tym samym wydziałem) – nie liczą się jako trafienie (`_bez_czesci_spoza_gold`)
    id_pominiete: frozenset[str] = frozenset()
    #: (OCR, data i kwota) wzorzec z granicami na tekście OCR bez złożenia: cyfry dokładnie (albo litera z `LITERY_ZA_CYFRY_OCR`),
    #: ciągi liter jako grupy porównywane z `litery_daty` rozmyto (`_litery_pasuja`), brzegowe „r.”/waluta opcjonalne
    wzor_daty: re.Pattern | None = None
    litery_daty: tuple[str, ...] = ()
    tokeny: tuple[str, ...] = ()             # wszystkie tokeny wartości (do pełnej frazy)
    liczace: tuple[str, ...] = ()            # tokeny liczące się (≥ min_dl, nie ignorowane EMAIL/URL)
    identyfikujace: tuple[str, ...] = ()     # liczące się i niegeneryczne
    #: token -> odmienione formy do dopasowania (tylko PL/DE; trafienie = co najwyżej „czesciowy”)
    rdzenie: dict[str, frozenset[str]] = field(default_factory=dict)
    fraza: re.Pattern | None = None
    #: (OCR) fraza z tolerancją: tokeny liczące się w kolejności (co najmniej dwa), między nimi tylko słowa krótsze niż
    #: `min_dl_tokenu` („sp. z 0.0.”), każdy token dokładnie, rozmyto (`_pasujace_slowa`) albo po złożeniu znaków mylonych – zob. `_fraza_ocr`
    fraza_ocr: tuple[str, ...] = ()
    min_dl_tokenu: int = 3
    #: (OCR) słowa dokumentu inne niż tokeny wartości – słowa generyczne i tokeny pozostałych wartości gold: słowo OCR równe
    #: jednemu z nich JEST tamtym słowem, więc nie trafia rozmyto tokenu tej wartości („Schmidt” innej osoby ≠ „lschmidt@…”).
    #: Słowa zamienników w kontekście zamiennika („[ADRES 21]” ≠ „Andrés”, „<PERSON>” ≠ „Persson”) usuwa z tekstu OCR
    #: `maskuj_zamienniki`.
    obce: frozenset[str] = frozenset()
    #: (OCR, identyfikator, e-mail/URL) ciągi alfanumeryczne innych wartości gold po złożeniu znaków mylonych (bez tych, które
    #: zawierają ten identyfikator): ich wystąpienia z granicami są wycinane z tekstu OCR przed dopasowaniem („28. Juli 2025”
    #: nie trafia „1. Juli 2025”), a wystąpienie wewnątrz dłuższego ciągu („Z1. Juli 2025” = „21. Juli 2025”) zostaje.
    obce_alnum: tuple[str, ...] = ()
    #: (OCR, e-mail/URL) cała wartość jako ciąg alfanumeryczny po złożeniu znaków mylonych (zob. `KATEGORIE_ALNUM_OCR`)
    ocr_alnum: str = ""
    #: (wariant złożony `_Grupa.reg_z` wartości bez liter mylących i bez diakrytyków – zapis łaciński ASCII) wariant stosowany
    #: wyłącznie do tekstów z cyrylicą mylącą (`Tekst.ma_cyrylice`) i tylko w szkielecie (bez składania diakrytyków): wynik,
    #: w którym litery wartości zastąpiono homoglifami cyrylicy, nadal ją pokazuje (zob. docstring modułu, pkt 6)
    tylko_cyrylica: bool = False

    @property
    def moze_wyciec(self) -> bool:
        return bool(self.id_alnum or self.liczace)


def _alnum_bez_prefiksu(tekst: str) -> str | None:
    if tekst.lstrip().startswith("+"):
        reszta = tekst.strip().split(None, 1)
        if len(reszta) == 2:
            return same_alnum(reszta[1])
    return None


_SEPARATORY = r"(?:[^\w<>=\"&]|_)*"


@functools.lru_cache(maxsize=4096)
def _wzor_id(alnum: str) -> re.Pattern:
    """Ciąg alfanumeryczny z separatorami (spacje, kropki, myślniki, ukośniki…) dozwolonymi między znakami; trafienie
    nie może wchodzić w dłuższy ciąg liter/cyfr."""
    return re.compile(r"(?<![^\W_])" + _SEPARATORY.join(re.escape(c) for c in alnum) + r"(?![^\W_])")


def _wzor_liczby(kanon: str, ulamek: int) -> re.Pattern:
    """Liczba w komórce arkusza (`753.46`, `1200`): kanoniczne cyfry z opcjonalnym separatorem dziesiętnym."""
    calk, czesc = (kanon[:-ulamek], kanon[-ulamek:]) if ulamek else (kanon, "")
    return re.compile(r"(?<![\d.,])" + re.escape(calk) + (r"[.,]" + re.escape(czesc) if czesc else r"(?![.,]?\d)")
                      + r"(?!\d)")


def _warianty_kwoty(tekst: str) -> list[tuple[str, re.Pattern]]:
    """Kwota w komórce numerycznej XLSX nie ma waluty ani przecinka (753,46 € leży jako liczba 753.46): wariant z
    liczbą kanoniczną (≥ 5 cyfr)."""
    m = re.search(r"\d[\d \u00a0\u202f'.,]*\d|\d", tekst)
    if not m:
        return []
    liczba = re.sub(r"[ \u00a0\u202f']", "", m.group())
    ostatni = max(liczba.rfind(","), liczba.rfind("."))
    if ostatni != -1 and len(liczba) - ostatni - 1 in (1, 2):
        calk, ulamek = re.sub(r"[.,]", "", liczba[:ostatni]), liczba[ostatni + 1:].rstrip("0")
    else:
        calk, ulamek = re.sub(r"[.,]", "", liczba), ""
    kanon = (calk.lstrip("0") or "0") + ulamek
    return [(kanon, _wzor_liczby(kanon, len(ulamek)))] if len(kanon) >= MIN_CYFR_KWOTY else []


def zbuduj_regule(w: Wartosc, r: RegulyWycieku, generyczne: set[str], gen_posortowane: list[str],
                  ocr: bool = False, leksykon: frozenset[str] = frozenset(), jezyk: str = "",
                  slownik: frozenset[str] = frozenset(), inne_alnum: frozenset[str] = frozenset(),
                  inne_teksty: frozenset[str] = frozenset()) -> Regula:
    """Reguła wycieku wartości `w` (zob. docstring modułu, pkt 2–3). `slownik` (OCR): słowa dokumentu (generyczne i tokeny
    wartości gold) – zob. `Regula.obce`; `inne_alnum` (OCR): ciągi alfanumeryczne wartości gold – zob. `Regula.obce_alnum`;
    `inne_teksty`: znormalizowane teksty wartości gold dokumentu – części wspólne identyfikatora z etykietą (`_czesci_id`)."""
    if w.kategoria in KATEGORIE_INICJALOW:
        # inicjały: dokładny wzorzec z granicami (`normalizacja.wzor_inicjalow`), także w OCR – bez wariantów rozmytych
        alnum = same_alnum(w.tekst)
        return Regula(id_alnum=(alnum,), id_wzorce=((alnum, wzor_inicjalow(w.tekst)),)) if alnum else Regula()
    if w.kategoria in r.kategorie_id or w.kategoria in KATEGORIE_JAK_ID:
        alnum = same_alnum(w.tekst)
        prog = MIN_CYFR_KWOTY if w.kategoria == "KWOTA" else MIN_DL_KODU if w.kategoria == "KOD_POCZTOWY" else MIN_DL_ID
        if len(alnum) >= prog:
            warianty = [alnum]
            kraj = _alnum_bez_prefiksu(w.tekst) if w.kategoria == "TELEFON" else None
            if kraj and len(kraj) >= MIN_DL_ID:
                warianty.append(kraj)
            wzorce = [(a, _wzor_id(a)) for a in warianty]
            if w.kategoria == "KWOTA":
                wzorce += _warianty_kwoty(w.tekst)
            mylone = tuple(dict.fromkeys(zloz_mylone(a) for a in warianty)) if ocr else ()
            wzor_daty, litery_daty = (_wzor_daty_ocr(w.tekst, w.kategoria) if ocr and w.kategoria in KATEGORIE_JAK_ID
                                      else (None, ()))
            return Regula(id_alnum=tuple(warianty), id_wzorce=tuple(wzorce), id_mylone=mylone,
                          id_rozmyte=ocr and w.kategoria in r.kategorie_id and len(alnum) >= MIN_DL_ID_ROZMYTEGO,
                          id_czesci=_czesci_id(w, alnum, inne_teksty), id_opisowe=_czesci_opisowe(w),
                          id_prog_czesci=r.min_cyfr_id if w.kategoria == "SYGNATURA" else MIN_DL_ID,
                          wzor_daty=wzor_daty, litery_daty=litery_daty, obce_alnum=_obce_alnum(mylone, inne_alnum, ocr))
        if w.kategoria in KATEGORIE_JAK_ID:
            return Regula()
    tokeny = tuple(_tokeny(w.tekst))
    ign = _ignorowane(w.tekst, w.kategoria)
    ignorowane = {normalizuj(m.group()) for m in _SLOWO.finditer(w.tekst)
                  if any(a <= m.start() and m.end() <= b for a, b in ign)}
    # liczba krótsza niż `min_cyfr_id` cyfr (numer domu, kod pocztowy w pół) nie dowodzi wycieku i trafia w liczby z metadanych
    liczace = tuple(t for t in tokeny if len(t) >= r.min_dl_tokenu and t not in ignorowane
                    and not (t.isdigit() and len(t) < r.min_cyfr_id))
    # w OCR token „podobny” do słowa generycznego (ten sam wyraz przeczytany inaczej) też jest generyczny; token złożony z samych
    # cyfr w wartości spoza identyfikatorów (dawka „1000 mg”, numer domu, liczba w nazwie) nie identyfikuje wartości sam w sobie
    # – trafia w cyfry z tabel i metryk czcionek (`/Widths`); liczy się do „pelny”
    ident = tuple(dict.fromkeys(t for t in liczace if t not in generyczne and t not in leksykon
                                and not (t.isdigit() and w.kategoria not in r.kategorie_id)
                                and not (ocr and obrazy.slowo_rozmyte(t, generyczne))))
    rdzenie = {}
    for t in ident:
        if t.isalpha():
            formy = _odmiany(t, jezyk) - {t} - generyczne
            if formy:
                rdzenie[t] = frozenset(formy)
    fraza = re.compile(r"(?<!\w)" + r"\W+".join(re.escape(t) for t in tokeny) + r"(?!\w)") if tokeny else None
    alnum = same_alnum(w.tekst) if ocr and w.kategoria in KATEGORIE_ALNUM_OCR else ""
    alnum = zloz_mylone(alnum) if len(alnum) >= MIN_DL_ALNUM_OCR else ""
    return Regula(tokeny=tokeny, liczace=liczace, identyfikujace=ident, rdzenie=rdzenie, fraza=fraza,
                  fraza_ocr=liczace if ocr and len(liczace) >= 2 else (), min_dl_tokenu=r.min_dl_tokenu,
                  obce=slownik - set(tokeny) if ocr else frozenset(), ocr_alnum=alnum,
                  obce_alnum=_obce_alnum([alnum], inne_alnum, ocr) if alnum else ())


#: Litery na początku tokenu numeru sygnatury, oddzielone od cyfr separatorem („NS-REJ.KRS/033655/20”, „QB-2020-014548”): osobna
#: część opisowa (J1-fix3, m1) – sędzia tekstowy liczy je jak każdy ciąg znaków spanu spoza etykiet.
_PRZEDROSTEK_NUMERU = re.compile(r"([^\d]*[^\W\d_])[\W_]+(?=\d)")


def _opis_i_numer(segment: str) -> tuple[tuple[str, ...], str]:
    """Podział ciągu sygnatury (między etykietami) na części opisowe (wydział, repertorium, rodzaj postępowania – „VII Ca”,
    „12 C”, „Juicio Verbal”, „NS-REJ.KRS”) i numer: numer zaczyna się od ostatniego tokenu (słowa rozdzielone białymi znakami)
    z cyfrą; litery na początku tego tokenu oddzielone od cyfr separatorem (`_PRZEDROSTEK_NUMERU`: „NS-REJ.KRS/”, „QB-”) są drugą
    częścią opisową; ciąg bez cyfry jest w całości opisowy. Reguła taka sama w każdym języku."""
    tokeny = segment.split()
    cyfrowe = [i for i, t in enumerate(tokeny) if any(c.isdigit() for c in t)]
    if not cyfrowe:
        return tuple(x for x in (" ".join(tokeny),) if x), ""
    i = cyfrowe[-1]
    opisy, numer = [" ".join(tokeny[:i])], tokeny[i]
    if m := _PRZEDROSTEK_NUMERU.match(numer):
        opisy.append(m.group(1))
        numer = numer[m.end():]
    return tuple(o for o in opisy if o), " ".join([numer, *tokeny[i + 1:]])


def _segmenty_miedzy_etykietami(w: Wartosc) -> list[str]:
    """Ciągi wartości między etykietami (`tekst.ETYKIETY_ID`; cała wartość, gdy etykiety nie ma)."""
    granice = [0, *(x for e in zakresy_etykiet(w.tekst, w.kategoria) for x in e), len(w.tekst)]
    return [w.tekst[granice[i]:granice[i + 1]] for i in range(0, len(granice), 2)]


def _czesci_id(w: Wartosc, alnum: str, inne_teksty: Iterable[str]) -> tuple[tuple[str, re.Pattern], ...]:
    """`Regula.id_czesci` identyfikatora z etykietami (`tekst.ETYKIETY_ID`, docstring modułu pkt 2d): ciągi alfanumeryczne
    między etykietami, bez części wspólnych z inną wartością gold (`inne_teksty` poza wartościami o tym samym ciągu
    alfanumerycznym; część wspólna = cała część występuje w tekście innej wartości wzorcem z granicami – J1-fix3, m2: nie
    podciąg, więc „32 O” nie jest wspólne z „Bahnhofstraße 32 Ost”); puste, gdy wartość nie ma etykiety albo części mają łącznie
    mniej niż `MIN_DL_ID` znaków. Sygnatura (J1-fix2): ciąg między etykietami dzieli się dodatkowo na części opisowe i numer
    (`_opis_i_numer`) – także gdy etykiety nie ma („VII Ca 1234/21”), żeby zapis z etykietą („Juicio Verbal n.º …”) i bez niej
    oceniać tak samo; części opisowe zwraca `_czesci_opisowe`."""
    if w.kategoria not in ETYKIETY_ID:
        return ()
    etykiety = zakresy_etykiet(w.tekst, w.kategoria)
    sygnatura = w.kategoria == "SYGNATURA"
    if not etykiety and not sygnatura:
        return ()
    czesci = []
    for segment in _segmenty_miedzy_etykietami(w):
        if sygnatura:
            opisy, numer = _opis_i_numer(segment)
            czesci += [same_alnum(x) for x in (*opisy, numer)]
        else:
            czesci.append(same_alnum(segment))
    czesci = [a for a in czesci if a]
    if sum(map(len, czesci)) < MIN_DL_ID or (not etykiety and len(set(czesci)) < 2):
        return ()
    inne = [o for o in inne_teksty if same_alnum(o) != alnum]
    return tuple((a, wzor) for a in dict.fromkeys(czesci) for wzor in (_wzor_id(a),)
                 if not any(wzor.search(o) for o in inne if a in same_alnum(o)))


def _teksty_czesci(w: Wartosc) -> dict[str, str]:
    """Część identyfikatora (`_czesci_id`, ciąg alfanumeryczny) -> jej tekst w wartości (krotność części – tokenami,
    `_z_czesciami_spoza_gold`)."""
    wynik: dict[str, str] = {}
    for segment in _segmenty_miedzy_etykietami(w):
        if w.kategoria == "SYGNATURA":
            opisy, numer = _opis_i_numer(segment)
            teksty = (*opisy, numer)
        else:
            teksty = (segment,)
        for x in teksty:
            if a := same_alnum(x):
                wynik.setdefault(a, x)
    return wynik


def _czesci_opisowe(w: Wartosc) -> frozenset[str]:
    """Części opisowe sygnatury (`_opis_i_numer`) jako ciągi alfanumeryczne."""
    if w.kategoria != "SYGNATURA":
        return frozenset()
    return frozenset(a for segment in _segmenty_miedzy_etykietami(w) for x in _opis_i_numer(segment)[0]
                     if (a := same_alnum(x)))


def _trafione_czesci(reg: Regula, t: Tekst, ocr: bool) -> set[str]:
    """Części identyfikatora z etykietą (`Regula.id_czesci`) obecne w tekście: wzorcem z granicami, w OCR także po złożeniu
    znaków mylonych (`zloz_mylone`, jak `Regula.id_mylone`); bez części `Regula.id_pominiete` (cytat innej sprawy)."""
    if not reg.id_czesci:
        return set()
    wynik = {a for a, wzor in reg.id_czesci if a in t.alnum and wzor.search(t.norm)}
    if ocr:
        m = t.mylone()
        wynik |= {a for a, _ in reg.id_czesci if (am := zloz_mylone(a)) in m.alnum and _wzor_id(am).search(m.norm)}
    return wynik - reg.id_pominiete


def _rodzaj_czesci(reg: Regula, t: Tekst, ocr: bool) -> str | None:
    """Rodzaj wycieku identyfikatora z etykietą z jego części: wszystkie = „pelny”, część ≥ `Regula.id_prog_czesci` znaków
    (`MIN_DL_ID`; sygnatura – `min_cyfr_id`) = „czesciowy”.
    „Wszystkie” – bez części pominiętych jako wspólne z inną wartością (`_czesci_id`), więc odsłonięcie reszty przy zamaskowanej
    części wspólnej daje „pelny” (zaostrzenie; w trzonie numery routingu są losowe – praktycznie nie występuje). Część pominięta
    w tym pliku jako cytat innej sprawy (`Regula.id_pominiete`) nie jest trafieniem, ale zostaje w „wszystkich” – odsłonięty
    numer przy zamaskowanej własnej części opisowej i zostawionym cytacie to „czesciowy”."""
    traf = _trafione_czesci(reg, t, ocr)
    if traf and len(traf) == len(reg.id_czesci):
        return "pelny"
    return "czesciowy" if any(len(a) >= reg.id_prog_czesci for a in traf) else None


def _obce_alnum(warianty: Iterable[str], inne_alnum: Iterable[str], ocr: bool) -> tuple[str, ...]:
    """`Regula.obce_alnum`: ciągi innych wartości po złożeniu znaków mylonych (bez zawierających którykolwiek wariant), od
    najdłuższych."""
    if not ocr:
        return ()
    warianty = list(warianty)
    inne = {zloz_mylone(o) for o in inne_alnum}
    return tuple(sorted((o for o in inne if not any(a in o for a in warianty)), key=lambda o: (-len(o), o)))


#: Znak wstawiany w miejsce wyciętej innej wartości: spoza separatorów `_wzor_id` i niealfanumeryczny, więc wycięte miejsce nie
#: skleja sąsiednich znaków w jedno trafienie i stanowi granicę.
_WYCIETE = "<"


def _bez_obcych(reg: Regula, m: Tekst) -> str:
    """(OCR) Tekst `m` (po złożeniu znaków mylonych, `Tekst.mylone`) bez wystąpień innych wartości gold (`Regula.obce_alnum`) –
    tylko wystąpień z granicami (nie wewnątrz dłuższego ciągu liter i cyfr)."""
    norm = m.norm
    for o in reg.obce_alnum:
        if o in m.alnum:
            norm = _wzor_id(o).sub(_WYCIETE, norm)
    return norm


def _id_w_ocr(reg: Regula, t: Tekst) -> bool:
    """(OCR) Identyfikator po złożeniu znaków mylonych: wzorcem z granicami, a dla `Regula.id_rozmyte` także rozmyto z granicami."""
    m = t.mylone()
    if not reg.id_rozmyte and not any(a in m.alnum for a in reg.id_mylone):
        return False
    norm = _bez_obcych(reg, m)
    if any(a in m.alnum and _wzor_id(a).search(norm) for a in reg.id_mylone):
        return True
    return reg.id_rozmyte and any(len(a) >= MIN_DL_ID_ROZMYTEGO and obrazy.zawiera_rozmyto(a, norm, granice=True)
                                  for a in reg.id_mylone)


_CIAGI_DATY = re.compile(r"\d+|[^\W\d_]+")


def _wzor_daty_ocr(tekst: str, kategoria: str) -> tuple[re.Pattern | None, tuple[str, ...]]:
    """(OCR) `Regula.wzor_daty` i `Regula.litery_daty` daty albo kwoty: liczby cyfra po cyfrze (cyfra albo litera, którą OCR czyta
    w jej miejscu – `LITERY_ZA_CYFRY_OCR`), separatory jak w `_wzor_id`, z granicami; ciąg liter między liczbami (i wymagany na
    brzegu) – grupa porównywana rozmyto; ciąg opcjonalny (`MAKS_LITER_OPCJONALNYCH`, waluta) pominięty, a granica po jego stronie
    dopuszcza literę (nie cyfrę: „17 sierpnia” ≠ „7 sierpnia”)."""
    ciagi = _CIAGI_DATY.findall(normalizuj(tekst))
    liczby = [i for i, c in enumerate(ciagi) if c[0].isdigit()]
    if not liczby:
        return None, ()
    czesci: list[str] = []
    litery: list[str] = []
    lewa, prawa = r"(?<![^\W_])", r"(?![^\W_])"
    for i, c in enumerate(ciagi):
        if c[0].isdigit():
            czesci.append(_SEPARATORY.join(f"[{d}{LITERY_ZA_CYFRY_OCR[d]}]" for d in c))
        elif i < liczby[0] or i > liczby[-1]:
            if kategoria == "KWOTA" or len(c) <= MAKS_LITER_OPCJONALNYCH:
                if i < liczby[0]:
                    lewa = r"(?<!\d)"
                else:
                    prawa = r"(?!\d)"
                continue
            czesci.append(rf"([^\W_]{{1,{len(c) + 3}}})")
            litery.append(c)
        elif len(c) <= MAKS_LITER_OPCJONALNYCH:
            czesci.append(r"[^\W\d_]{0,3}")
        else:
            czesci.append(rf"([^\W_]{{1,{len(c) + 3}}})")
            litery.append(c)
    return re.compile(lewa + _SEPARATORY.join(czesci) + prawa), tuple(litery)


def _jedna_zmiana(a: str, b: str) -> bool:
    """Czy `a` i `b` różnią się co najwyżej jedną zmianą (zamiana, wstawienie albo usunięcie znaku)."""
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    krotszy, dluzszy = sorted((a, b), key=len)
    i = next((k for k, (x, y) in enumerate(zip(krotszy, dluzszy)) if x != y), len(krotszy))
    return krotszy[i:] == dluzszy[i + 1:]


def _litery_pasuja(odczyt: str, wzor: str) -> bool:
    """(OCR, data i kwota) Ciąg liter OCR `odczyt` jest ciągiem liter wartości `wzor` (nazwa miesiąca, waluta): równy po złożeniu
    diakrytyków i znaków mylonych, podobny (≥ `PROG_LITER_DATY`) albo o jedną zmianę (od `MIN_DL_JEDNEJ_ZMIANY` liter) – chyba że
    jest INNĄ nazwą miesiąca (`NAZWY_MIESIECY`)."""
    a, b = _klucz_liter(odczyt), _klucz_liter(wzor)
    if a == b:
        return True
    if a in _MIESIACE:
        return False
    return obrazy.podobienstwo(a, b) >= PROG_LITER_DATY or (len(b) >= MIN_DL_JEDNEJ_ZMIANY and _jedna_zmiana(a, b))


def _data_w_ocr(reg: Regula, t: Tekst) -> bool:
    """(OCR) Data albo kwota wzorcem `Regula.wzor_daty` w tekście bez złożenia znaków mylonych, z którego wycięto wystąpienia innych
    wartości gold (`Regula.obce_alnum`, miejsca wyznaczone na tekście po złożeniu – ta sama długość)."""
    m = t.mylone()
    znaki = list(t.norm)
    for o in reg.obce_alnum:
        if o in m.alnum:
            for x in _wzor_id(o).finditer(m.norm):
                znaki[x.start():x.end()] = _WYCIETE * (x.end() - x.start())
    for x in reg.wzor_daty.finditer("".join(znaki)):
        if all(_litery_pasuja(g, w) for g, w in zip(x.groups(), reg.litery_daty)):
            return True
    return False


def _odmiany(t: str, jezyk: str) -> set[str]:
    """Odmienione formy tokenu (PL: końcówki przypadków i rodzina -ski/-cki; DE: dopełniacz -s). Inne języki: brak."""
    if jezyk == "de":
        return {t + "s"} | ({t[:-1]} if t.endswith("s") and len(t) > MIN_BAZA_ODMIANY else set())
    if jezyk != "pl" or len(t) < MIN_BAZA_ODMIANY + 1:
        return set()
    wynik = set()
    m = _PRZYM.match(t)
    if m and len(m.group(1)) >= MIN_BAZA_ODMIANY:
        wynik |= {m.group(1) + k for k in KONCOWKI_PRZYM_PL}
    for k in sorted(KONCOWKI_PL, key=len, reverse=True):
        if k and t.endswith(k) and len(t) - len(k) >= MIN_BAZA_ODMIANY:
            baza = t[:-len(k)]
            wynik |= {baza + e for e in KONCOWKI_PL}
    wynik |= {t + e for e in KONCOWKI_PL}
    return wynik


def _slowo_dokladnie(tok: str, t: Tekst, ocr: bool, obce: frozenset[str] = frozenset()) -> bool:
    """Token jest słowem tekstu; w OCR także rozmyto (token ≥ `MIN_DL_SLOWA_ROZMYTEGO`, słowo OCR ≥ `MIN_DL_SLOWA_OCR_ROZMYTEGO` znaków) albo – token z cyfrą – po złożeniu znaków mylonych („I48” =
    „148”), w obu przypadkach z pominięciem słów `obce`."""
    if tok in t.slowa:
        return True
    if not ocr:
        return False
    if len(tok) >= MIN_DL_SLOWA_ROZMYTEGO and obrazy.slowo_rozmyte(tok, t.dlugie() - obce if obce else t.dlugie()):
        return True
    return any(c.isdigit() for c in tok) and any(s not in obce for s in t.slowa_mylone().get(zloz_mylone(tok), ()))


def _pasujace_slowa(tok: str, t: Tekst, obce: frozenset[str]) -> set[str]:
    """(OCR) Słowa tekstu, którymi może być token: ono samo, podobne (`Tekst.dlugie`, poza `obce`) i równe po złożeniu znaków mylonych."""
    wynik = {tok} & t.slowa
    if len(tok) >= MIN_DL_SLOWA_ROZMYTEGO:
        wynik |= obrazy.slowa_rozmyte(tok, t.dlugie() - obce)
    wynik |= {s for s in t.slowa_mylone().get(zloz_mylone(tok), ()) if s not in obce}
    return wynik


#: Fraza OCR: najwyżej tyle słów krótszych niż `min_dl_tokenu` między kolejnymi tokenami wartości.
MAKS_KROTKICH_W_FRAZIE = 3


def _fraza_ocr(reg: Regula, t: Tekst) -> bool:
    """(OCR) Pełna wartość jako fraza z tolerancją (`Regula.fraza_ocr`): „Eko-Serwis Centrum Medyczne sp. z 0.0.” trafia
    „Eko-Serwis Centrum Medyczne sp. z o.o.”, choć OCR zepsuł krótkie tokeny i żaden token nie jest identyfikujący."""
    kandydaci = []
    for tok in reg.fraza_ocr:
        k = _pasujace_slowa(tok, t, reg.obce)
        if not k:
            return False
        kandydaci.append(k)
    slowa = t.ciag()
    for i, s in enumerate(slowa):
        if s not in kandydaci[0]:
            continue
        j, k, krotkie = i + 1, 1, 0
        while k < len(kandydaci) and j < len(slowa):
            if slowa[j] in kandydaci[k]:
                k, krotkie = k + 1, 0
            elif len(slowa[j]) < reg.min_dl_tokenu and krotkie < MAKS_KROTKICH_W_FRAZIE:
                krotkie += 1
            else:
                break
            j += 1
        if k == len(kandydaci):
            return True
    return False


def dopasuj(reg: Regula, t: Tekst, ocr: bool = False, tylko_fraza: bool = False) -> str | None:
    """Rodzaj wycieku wartości w jednym tekście: "pelny", "czesciowy" albo None (zob. docstring modułu).
    `tylko_fraza`: tylko pełna wartość / identyfikator (części strukturalne – bez reguły pojedynczego tokenu)."""
    if reg.id_wzorce:
        for a, wzor in reg.id_wzorce:
            if a in t.alnum and wzor.search(t.norm):
                return "pelny"
        if ocr and (_id_w_ocr(reg, t) or (reg.wzor_daty is not None and _data_w_ocr(reg, t))):
            return "pelny"
        return _rodzaj_czesci(reg, t, ocr) if reg.id_czesci else None
    if not reg.liczace:
        return None
    if reg.fraza is not None and all(tok in t.slowa for tok in reg.tokeny) and reg.fraza.search(t.norm):
        return "pelny"
    if tylko_fraza:
        return None
    if ocr and reg.ocr_alnum and obrazy.zawiera_rozmyto(reg.ocr_alnum, _bez_obcych(reg, t.mylone()), PROG_ALNUM_OCR,
                                                        granice=True):
        return "pelny"
    if ocr and reg.fraza_ocr and _fraza_ocr(reg, t):
        return "pelny"
    dokladne = {tok for tok in reg.liczace if _slowo_dokladnie(tok, t, ocr, reg.obce)}
    odmiana = {tok for tok in reg.identyfikujace if tok not in dokladne and reg.rdzenie.get(tok)
               and not reg.rdzenie[tok].isdisjoint(t.slowa)}
    if not (dokladne & set(reg.identyfikujace)) and not odmiana:
        return None
    return "pelny" if len(dokladne) == len(reg.liczace) else "czesciowy"


def _najlepsze(trafienia: list[tuple[str, str]]) -> tuple[str, str] | None:
    """(miejsce, rodzaj): pierwsze „pelny”, inaczej pierwsze „czesciowy”."""
    for miejsce, rodzaj in trafienia:
        if rodzaj == "pelny":
            return miejsce, rodzaj
    return trafienia[0] if trafienia else None


# ----------------------------------------------------------------------------- kalibracja OCR oryginału
def wykrywalne_w_ocr(oryginal: Path, gold: Iterable[Wartosc], ob: list[Wartosc], teksty_ocr: list[str],
                     reguly: RegulyWycieku, leksykon: frozenset[str] = frozenset()) -> set[str]:
    """Wartości obrazowe `ob`, które reguły wycieku znajdują w OCR oryginału (`teksty_ocr`) – używane przez
    `obrazy.wykrywalne_obrazy`."""
    wyd = wydobadz(oryginal)
    wszystkie = list(gold)
    gen = slowa_generyczne(wyd.czesci, teksty_ocr, wszystkie)
    gen |= _tokeny_wartosci(wszystkie, niejednoznaczne(wyd.czesci, teksty_ocr, wszystkie))
    gen_s = sorted(gen)
    teksty = [Tekst(maskuj_zamienniki(t)) for t in teksty_ocr]
    wynik = set()
    for w in ob:
        reg = zbuduj_regule(w, reguly, gen, gen_s, ocr=True, leksykon=leksykon, jezyk=w.jezyk)
        if any(dopasuj(reg, t, ocr=True) for t in teksty):
            wynik.add(w.id)
    return wynik


# ----------------------------------------------------------------------------- integralność
def _zachowanie(o: dict[str, int], w: dict[str, int]) -> float:
    if not o:
        return 1.0
    stosunki = []
    for k, a in o.items():
        b = w.get(k, 0)
        if k == "strony" and abs(a - b) <= 1:   # układ stron zależy od długości zamienników: ±1 strona bez kary
            stosunki.append(1.0)
            continue
        stosunki.append(1.0 if a == b else (min(a, b) / max(a, b) if max(a, b) else 1.0))
    return sum(stosunki) / len(stosunki)


def _tokeny_czesci(c: Czesc) -> list[str]:
    return _SLOWO_LUB_ZNAK.findall(normalizuj(" \n ".join(c.linie)))


def _alnum_tokenow(tokeny: list[str]) -> str:
    return "".join(ch for t in tokeny for ch in t if ch.isalnum())


def spojnosc(orig: Wydobycie, wyn: Wydobycie, wartosci: list[Wartosc], szczegoly: dict | None = None) -> dict:
    """Spójność zamienników encji (zob. docstring modułu). Zwraca słownik `spojnosc` + liczniki."""
    wynik = {"spojnosc": None, "ocenione": 0, "spojne": 0, "pominiete": 0, "niezamaskowane": 0}
    teksty = [w for w in wartosci if not w.w_pikselach and _tokeny(w.tekst)]
    if not teksty or orig.rodzaj != wyn.rodzaj:
        return wynik
    # tekst wartości -> rola (przy remisie ról pierwsza alfabetycznie)
    rola_tekstu: dict[tuple[str, ...], str] = {}
    for w in sorted(teksty, key=lambda w: encja(w.id)):
        rola_tekstu.setdefault(tuple(_SLOWO_LUB_ZNAK.findall(normalizuj(w.tekst))), encja(w.id))
    indeks: dict[str, list[tuple[str, ...]]] = {}
    for tok in rola_tekstu:
        indeks.setdefault(tok[0], []).append(tok)
    for lista in indeks.values():
        lista.sort(key=len, reverse=True)
    wyn_czesci = {c.nazwa: c for c in wyn.czesci}
    wystapienia: dict[str, list[str | None]] = {}   # rola -> zamienniki (alnum), None = nietknięte, "!" = niejednoznaczne
    for c in orig.czesci:
        if not c.linie:
            continue
        a = _tokeny_czesci(c)
        miejsca: list[tuple[int, int, str]] = []
        i = 0
        while i < len(a):
            for kandydat in indeks.get(a[i], ()):
                k = len(kandydat)
                if tuple(a[i:i + k]) == kandydat:
                    miejsca.append((i, i + k, rola_tekstu[kandydat]))
                    i += k
                    break
            else:
                i += 1
        if not miejsca:
            continue
        cw = wyn_czesci.get(c.nazwa)
        b = _tokeny_czesci(cw) if cw is not None else []
        ops = difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if b else [("delete", 0, len(a), 0, 0)]
        for od, do, rola in miejsca:
            nak = [op for op in ops if op[2] > od and op[1] < do]
            if all(op[0] == "equal" for op in nak):
                zam: str | None = None
            elif nak[0][0] != "equal" and nak[-1][0] != "equal" and nak[0][1] == od and nak[-1][2] == do:
                # zamiennik zaczyna się i kończy razem z wartością (może zawierać przypadkowo zgodne słowa w środku)
                zam = _alnum_tokenow(b[nak[0][3]:nak[-1][4]])
            else:
                zam = "!"
            wystapienia.setdefault(rola, []).append(zam)
    if szczegoly is not None:
        szczegoly.update(wystapienia)
    for rola, zam in wystapienia.items():
        if len(zam) < 2:
            continue
        if any(z is None for z in zam):
            wynik["niezamaskowane"] += 1
        elif any(z == "!" for z in zam):
            wynik["pominiete"] += 1
        else:
            wynik["ocenione"] += 1
            if zam[0] and len(set(zam)) == 1:
                wynik["spojne"] += 1
    if wynik["ocenione"]:
        wynik["spojnosc"] = wynik["spojne"] / wynik["ocenione"]
    return wynik


# ----------------------------------------------------------------------------- nadmiarowe maskowanie (P5)
#: Części z treścią, której czytelnik nie widzi w dokumencie (komentarze recenzentów): poza P5 jak metadane i śledzenie zmian –
#: ich usunięcie jest krokiem anonimizacji, nie nadmiarowym maskowaniem.
_KOMENTARZE = re.compile(r"(?:^|[/:])(?:comments\w*\.xml|threadedComments/|comments/|komentarz$)")


def _widoczne(w: Wydobycie) -> list[Czesc]:
    """Części tekstu widocznego (P5): treść (`Czesc.tresc` – akapity, tabele, nagłówki, stopki, przypisy, slajdy, komórki,
    strony PDF, treść poczty), bez komentarzy i bez drugiej reprezentacji tej samej treści (`wariant`, HTML obok text/plain)."""
    return [c for c in w.czesci if c.tresc and not c.wariant and not _KOMENTARZE.search(c.nazwa) and c.linie]


def _zlicz_nadmiarowe(a: list[str], b: list[str], gold: list[bool]) -> tuple[int, int]:
    """(znaki słów spoza gold zamienionych albo usuniętych w `b`, znaki wszystkich słów spoza gold) – wyrównanie difflib na
    słowach jak w `spojnosc`; brak słów wyniku = wszystko usunięte."""
    poza = sum(len(t) for t, g in zip(a, gold) if not g)
    if not poza:
        return 0, 0
    ops = difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if b else [("delete", 0, len(a), 0, 0)]
    zmienione = sum(len(a[i]) for op, i1, i2, _, _ in ops if op != "equal" for i in range(i1, i2) if not gold[i])
    return zmienione, poza


def nadmiarowe(orig: Wydobycie, wyn: Wydobycie, wartosci: Iterable[Wartosc],
               ocr_stron: Iterable[tuple[str, str]] = ()) -> dict[str, int]:
    """P5 (`metodyka/prerejestracja.md`, pkt 3.2): znaki słów oryginału spoza wystąpień gold, które w wyniku zostały zamienione
    albo usunięte (`znaki`), i znaki wszystkich słów oryginału spoza gold (`poza_gold`) – w tekście widocznym (`_widoczne`).
    Słowa = `_SLOWO_LUB_ZNAK` po `normalizuj` (znaki niebiałe). Wystąpienie gold = każde wystąpienie ciągu słów tekstu wartości
    gold w słowach oryginału (dłuższy ciąg pierwszy, jak w `spojnosc`) – wszystkich wartości tekstowych (bez narysowanych na
    obrazach), także tych, których sędzia nie ocenia jako wycieku (niejednoznaczne, bez liczącego się tokenu): maskowanie wartości
    gold nie jest nadmiarowe. Wyrównanie słów oryginału i wyniku – difflib, część z częścią o tej samej nazwie; przy formacie
    zamienionym na odpowiednik (`rodzaj` różny: DOC → DOCX, MSG → TXT) – sklejony tekst widoczny całego pliku. Strona PDF wyniku bez
    warstwy tekstowej (np. zrasteryzowana) – słowa z OCR tej strony (`ocr_stron`, nazwy `ekstrakcja.nazwa_renderu`). Skan bez
    warstwy tekstowej w oryginale nie wnosi znaków (mianownik 0)."""
    indeks: dict[str, list[tuple[str, ...]]] = {}
    for w in wartosci:
        if not w.w_pikselach and (tok := tuple(_SLOWO_LUB_ZNAK.findall(normalizuj(w.tekst)))):
            if tok not in indeks.setdefault(tok[0], []):
                indeks[tok[0]].append(tok)
    for lista in indeks.values():
        lista.sort(key=len, reverse=True)

    def slowa(c: Czesc) -> list[str]:
        return _tokeny_czesci(c)

    def oznacz(a: list[str]) -> list[bool]:
        gold = [False] * len(a)
        i = 0
        while i < len(a):
            for kandydat in indeks.get(a[i], ()):
                k = len(kandydat)
                if tuple(a[i:i + k]) == kandydat:
                    gold[i:i + k] = [True] * k
                    i += k
                    break
            else:
                i += 1
        return gold

    ocr = dict(ocr_stron)
    wyn_czesci = {c.nazwa: c for c in _widoczne(wyn)}

    def slowa_wyniku(nazwa: str) -> list[str]:
        if (c := wyn_czesci.get(nazwa)) is not None and (b := slowa(c)):
            return b
        if wyn.rodzaj == "pdf" and nazwa.startswith("pdf:strona "):
            t = ocr.get(ekstrakcja.nazwa_renderu(int(nazwa.removeprefix("pdf:strona "))), "")
            return _SLOWO_LUB_ZNAK.findall(normalizuj(t))
        return []

    pary: list[tuple[list[str], list[str]]]
    if orig.rodzaj == wyn.rodzaj:
        pary = [(slowa(c), slowa_wyniku(c.nazwa)) for c in _widoczne(orig)]
    else:
        pary = [([t for c in _widoczne(orig) for t in slowa(c)], [t for c in _widoczne(wyn) for t in slowa(c)])]
    znaki = poza = 0
    for a, b in pary:
        z, p = _zlicz_nadmiarowe(a, b, oznacz(a))
        znaki, poza = znaki + z, poza + p
    return {"znaki": znaki, "poza_gold": poza}


# ----------------------------------------------------------------------------- leksykon korpusu
#: Zastrzeżone domeny/etykiety przykładowe i słowa form prawnych – wspólne dla wszystkich korpusów danych fikcyjnych – oraz słowa
#: opisowe nazw organizacji (`tekst.SLOWA_OPISOWE_ORGANIZACJI`, J1: rodzaj kancelarii, forma prawna).
SLOWA_ZASTRZEZONE: frozenset[str] = frozenset({
    "example", "test", "invalid", "localhost", "com", "org", "net", "pl", "de", "fr", "es", "eu",
    "gmbh", "ag", "kg", "ug", "sp", "zoo", "spółka", "sa", "sl", "slu", "sarl", "sas", "sasu", "ltd", "llp", "llc",
    "plc", "inc", "kancelaria", "kanzlei", "cabinet", "despacho", "law", "group", "partners", "wspólnicy",
}) | frozenset(normalizuj(s) for s in SLOWA_OPISOWE)


def zbuduj_leksykon(manifest: Iterable[dict], prog: float = RegulyWycieku().prog_leksykonu) -> dict[str, frozenset[str]]:
    """Leksykon korpusu per język: tokeny (≥ 3 znaki) obecne w gold (`gold_plik` i `gold_obrazy`) co najmniej `prog`
    dokumentów danego języka. Dane fikcyjne powtarzają imiona, miasta i formy prawne; ich pojedynczy token nie dowodzi
    wycieku konkretnej wartości (pełna wartość i identyfikatory – bez zmian). Zob. `ocen_plik(leksykon=…)`."""
    df: dict[str, Counter] = {}
    n: Counter = Counter()
    for wpis in manifest:
        tokeny = {t for g in wpis["gold_plik"] for t in _tokeny(g["tekst"])}
        tokeny |= {t for o in wpis["gold_obrazy"] for g in o["wartosci"] for t in _tokeny(g["tekst"])}
        n[wpis["jezyk"]] += 1
        df.setdefault(wpis["jezyk"], Counter()).update(t for t in tokeny if len(t) >= 3)
    return {j: frozenset(t for t, c in df[j].items() if c >= prog * n[j]) for j in df}


_LEKSYKONY: dict[tuple, dict[str, frozenset[str]]] = {}


def leksykon_z_manifestu(sciezka: Path, prog: float = RegulyWycieku().prog_leksykonu) -> dict[str, frozenset[str]]:
    """`zbuduj_leksykon` z pliku `manifest.jsonl`, zapamiętany w procesie (klucz: ścieżka, rozmiar, mtime, próg)."""
    import json
    p = Path(sciezka)
    st = p.stat()
    klucz = (str(p.resolve()), st.st_size, st.st_mtime_ns, prog)
    if klucz not in _LEKSYKONY:
        _LEKSYKONY[klucz] = zbuduj_leksykon((json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()), prog)
    return _LEKSYKONY[klucz]


def _leksykon_dla(leksykon, jezyk: str) -> frozenset[str]:
    if leksykon is None:
        wynik: frozenset[str] = frozenset()
    elif isinstance(leksykon, dict):
        wynik = leksykon.get(jezyk, frozenset())
    else:
        wynik = frozenset(leksykon)
    return wynik | SLOWA_ZASTRZEZONE


# ----------------------------------------------------------------------------- ocena pliku
def _ile_wystapien(reg: Regula, teksty: Iterable[Tekst]) -> int:
    """Liczba wystąpień pełnej wartości (fraza / wzorzec identyfikatora) w tekstach (warstwa tekstowa – dokładnie)."""
    suma = 0
    for t in teksty:
        if reg.id_wzorce:
            suma += max((len(w.findall(t.norm)) for _, w in reg.id_wzorce), default=0)
        elif reg.fraza is not None:
            suma += len(reg.fraza.findall(t.norm))
    return suma


def _wariant(reg_z: Regula | None, t: Tekst) -> Tekst | None:
    """Widok tekstu dla wariantu złożonego `reg_z`: `Tekst.zlozony` (szkielet bez diakrytyków); wariant `tylko_cyrylica` –
    sam szkielet i tylko tekst z cyrylicą mylącą; None – wariant nie dotyczy tekstu."""
    if reg_z is None:
        return None
    if reg_z.tylko_cyrylica:
        return t.szkielet() if t.ma_cyrylice() else None
    return t.zlozony()


def _dopasuj_z_wariantami(reg: Regula, reg_z: Regula | None, t: Tekst, ocr: bool, tylko_fraza: bool = False) -> str | None:
    """`dopasuj` z wariantem złożonym `reg_z`, gdy dokładne nie trafia; na tekście z literami szkieletu – także gdy dokładne
    trafia tylko częściowo („Jan Κοwalski”: „Jan” dokładnie, nazwisko w szkielecie – trafienie pełne; poprawka H6a M2). Tekst bez
    liter szkieletu – jak przed H6a (wariant tylko przy braku trafienia dokładnego)."""
    r = dopasuj(reg, t, ocr=ocr, tylko_fraza=tylko_fraza)
    if (r is None or (r == "czesciowy" and t.ma_cyrylice())) and (tz := _wariant(reg_z, t)) is not None:
        rz = dopasuj(reg_z, tz, ocr=ocr, tylko_fraza=tylko_fraza)
        r = rz if r is None or rz == "pelny" else r
    return r


class _Ocr:
    """Tekst OCR jednego obrazu albo jednej strony: całość (dopasowanie) i odczyty podzielone na wiersze (krotność). `tryby` –
    (obraz osadzony) tryb Tesseracta każdego odczytu (`obrazy.tryby_odczytow`): potwierdza odczyt innym trybem, a odczyt tym
    samym trybem w innej skali – tylko tokenem dokładnym (`_trafienia_ocr`); puste (strona PDF) – każdy odczyt jest niezależny
    (inne dpi albo tryb). Dla inicjałów w pikselach (poprawka H6a I-R1, `_trafienia_ocr`, `_ocen_grupe`): `wybielone` – funkcje
    zwracające (leniwie, OCR z pamięci podręcznej) te same odczyty obrazu z wybielonymi polami zamalowanymi (`obrazy.bez_pol`),
    `bez_tekstu` – (strona PDF) funkcja zwracająca `_Ocr` tego samego odczytu renderu strony bez obiektów tekstowych. Puste/None –
    odczyt bez obrazu źródłowego (testy jednostkowe)."""

    __slots__ = ("nazwa", "surowy", "tekst", "tryby", "wybielone", "bez_tekstu", "_odczyty")

    def __init__(self, nazwa: str, surowy: str, tryby: tuple[int, ...] = (), wybielone: tuple[Callable[[], str], ...] = (),
                 bez_tekstu: Callable[[], "_Ocr"] | None = None) -> None:
        self.nazwa = f"obraz:{nazwa}"
        self.surowy = surowy = maskuj_zamienniki(surowy)
        self.tekst = Tekst(surowy)
        self.tryby = tryby
        self.wybielone = wybielone
        self.bez_tekstu = bez_tekstu
        self._odczyty: list[tuple[Tekst, list[Tekst]]] | None = None

    def odczyty(self) -> list[tuple[Tekst, list[Tekst]]]:
        if self._odczyty is None:
            self._odczyty = [(Tekst(o), [Tekst(l) for l in o.splitlines() if l.strip()])
                             for o in self.surowy.split(obrazy.ODDZIELACZ)]
        return self._odczyty


def _ile_w_ocr(reg: Regula, reg_z: Regula | None, teksty: Iterable[_Ocr], reg_dokl: Regula | None = None) -> int:
    """Krotność wartości w tekstach OCR regułą OCR (dokładna fraza w OCR prawie nigdy nie pasuje: „officeQ darex.example.org”).
    Liczą się tylko trafienia PEŁNE: każdy obraz/strona – najwięcej z odczytów (`obrazy.ODDZIELACZ`); w odczycie trafionym regułą
    wiersz z trafieniem pełnym liczy się tyle razy, ile razy ma wartość dokładnie (`reg_dokl`: kwota netto i brutto w jednym
    wierszu tabeli), co najmniej raz – dwie pełne w sąsiednich wierszach to dwa wystąpienia. Ciąg kolejnych wierszy z samymi
    trafieniami częściowymi liczy się raz, gdy ich złączenie (ewentualnie z wierszem przed albo po ciągu) trafia pełnie – wartość
    złamana między wiersze; inaczej wcale (samo nazwisko „Kowalski” obok zamaskowanego „[OSOBA_1]” nie jest drugim wystąpieniem
    „Jan Kowalski”). Identyfikator (i fraza bez tokenu identyfikującego) złamany na dwa wiersze, z których żaden nie trafia sam,
    też liczy się raz. Odczyt liczy się co najmniej tyle razy, ile razy ma wartość dokładnie. Minimum 1 dla trafionej wartości
    daje `_ocen_grupe`."""
    def dokladnie(t: Tekst) -> int:
        return _ile_wystapien(reg_dokl, [t]) if reg_dokl is not None else 0

    def pelny(wiersze: list[Tekst]) -> bool:
        return _dopasuj_z_wariantami(reg, reg_z, Tekst("", norm=" ".join(w.norm for w in wiersze)), True) == "pelny"

    # tylko taka wartość może trafić pełnie w dwóch wierszach, z których żaden nie trafia sam
    lamane = bool(reg.id_mylone or (reg.fraza_ocr and not reg.identyfikujace))
    suma = 0
    for o in teksty:
        najwiecej = 0
        for caly, wiersze in o.odczyty():
            if not _dopasuj_z_wariantami(reg, reg_z, caly, True):
                continue
            wyniki = [_dopasuj_z_wariantami(reg, reg_z, w, True) for w in wiersze]
            ile, i, uzyty = 0, 0, -1          # `uzyty`: wiersz bez trafienia doklejony już do poprzedniego ciągu
            while i < len(wiersze):
                if not wyniki[i]:
                    # identyfikator / fraza bez tokenu identyfikującego złamane na dwa wiersze bez trafień („… rejestracyjnym SZ”,
                    # „22924. Sprawcą …”)
                    if (lamane and i + 1 < len(wiersze) and not wyniki[i + 1] and i != uzyty
                            and (not reg.id_mylone or any(a in zloz_mylone(wiersze[i].alnum + wiersze[i + 1].alnum)
                                                          for a in reg.id_mylone))
                            and pelny(wiersze[i:i + 2])):
                        ile, i = ile + 1, i + 2
                        continue
                    i += 1
                    continue
                j = i
                while j < len(wiersze) and wyniki[j]:
                    j += 1
                pelne = sum(max(1, dokladnie(wiersze[k])) for k in range(i, j) if wyniki[k] == "pelny")
                if pelne:
                    ile += pelne
                elif pelny(wiersze[i:j]):
                    ile += 1
                elif i > 0 and i - 1 != uzyty and pelny(wiersze[i - 1:j]):
                    ile += 1
                elif j < len(wiersze) and pelny(wiersze[i:j + 1]):
                    ile, uzyty = ile + 1, j
                i = j
            najwiecej = max(najwiecej, ile, dokladnie(caly))
        suma += najwiecej
    return suma


@dataclass(frozen=True)
class _CzescSpozaGold:
    """(J1-fix3, I1) Część identyfikatora (`Regula.id_czesci`), która występuje w oryginale także poza wystąpieniami wartości gold
    – np. wydział i repertorium sygnatury w cytacie innej sprawy („VII Ca 6470/18” obok własnej „VII Ca 1554/21”)."""

    alnum: str                       # część (ciąg alfanumeryczny, jak w `Regula.id_czesci`)
    tokeny: tuple[str, ...]          # jej tokeny (`_tokeny`) – krotność liczona przejściem jak w `niejednoznaczne`
    poza: int                        # wystąpienia w oryginale poza wystąpieniami gold (`_z_czesciami_spoza_gold`)


@dataclass
class _Grupa:
    """Wartości o tym samym tekście (osobno tekstowe i obrazowe): jedna reguła, krotność przypisywana po `id`."""

    wartosci: list[Wartosc]          # unikalne po `id`, w kolejności `id`
    reg: Regula
    #: wariant złożony (szkielet bez diakrytyków, `zbiory_dokumentu`): wartość z literami spoza ASCII albo z literami mylącymi;
    #: wartość ASCII – wariant `Regula.tylko_cyrylica`; None – wariant wyłączony (wartość niejednoznaczna w szkielecie)
    reg_z: Regula | None
    reg_ocr: Regula
    reg_ocr_z: Regula | None
    ocr: bool                        # szukana w OCR (nie wszystkie jej wartości są niewykrywalne)
    #: wartość ma litery cyrylicy mylące (szkielet ją zmienia): krotność liczona też w wariancie złożonym (`_ocen_grupe`)
    szkielet: bool = False
    #: (J1-fix3, I1) części obecne w oryginale także poza gold i indeks tekstów gold dokumentu razem z tymi częściami (krotność
    #: w ocenianym pliku, `_bez_czesci_spoza_gold`)
    czesci_poza: tuple[_CzescSpozaGold, ...] = ()
    indeks_poza: dict[str, list[tuple[str, ...]]] = field(default_factory=dict)
    #: (inicjały w OCR) słowa dokumentu – słowa oryginału (`slowa_generyczne`: części i OCR obrazów) i tokeny wartości gold;
    #: wiersze odczytu bez żadnego z nich są szumem (`_bez_szumu`). None – bez tego warunku (testy jednostkowe bez dokumentu)
    slownik: frozenset[str] | None = None


@dataclass
class _Widoki:
    """Teksty jednego pliku (oryginału albo wyniku), w których szukamy wartości."""

    zwykle: list[tuple[str, Tekst]]
    strukt: list[tuple[str, Tekst]]
    do_liczenia: list[Tekst]         # teksty węzłowe części (krotność w warstwie tekstowej – dokładnie)
    osadzone: list[_Ocr]             # OCR obrazów osadzonych
    #: OCR stron PDF: jedna lista na odczyt (`RENDER_DPI`, ewentualnie `DRUGI_ODCZYT_DPI`)
    strony: list[list[_Ocr]] = field(default_factory=list)
    #: (poczta) przedrostki PDF-ów załączników (`Wydobycie.pdfy`) i nazwy części `do_liczenia` – krotność `_ile_poczty`
    pdfy: list[str] = field(default_factory=list)
    nazwy_liczenia: list[str] = field(default_factory=list)
    #: pozycje stron (kolejność odczytów w `strony`), których warstwa tekstowa pokazuje treść strony (`_strony_z_warstwa`):
    #: inicjały czytane są tam z renderu bez obiektów tekstowych (`_Ocr.bez_tekstu`, `_ocen_grupe`)
    strony_z_warstwa: frozenset[int] = frozenset()
    #: (J3) nazwy części `zwykle` z widokami binarnych strumieni OLE (`ekstrakcja.Czesc.binarna`) – bez wartości krótkich
    #: i inicjałów (`_krotka`)
    binarne: frozenset[str] = frozenset()


@dataclass(frozen=True)
class _Zrodlo:
    """Plik, którego obrazy i strony czyta OCR (oryginał albo wynik), jego wydobycie i język OCR – źródło leniwych odczytów
    dodatkowych inicjałów (`_Ocr.wybielone`, `_Ocr.bez_tekstu`)."""

    sciezka: Path
    w: Wydobycie
    jezyk: str


def _ocr_obrazu(nazwa: str, dane: bytes, tekst: str, drugi: str | None = None, jezyk: str | None = None) -> _Ocr:
    """`_Ocr` obrazu osadzonego z trybami odczytów (`obrazy.tryby_odczytow`); `drugi` – tekst drugiego odczytu, dopisany po
    `obrazy.ODDZIELACZ` jako kolejne odczyty. `jezyk` – odczyty bez pól zamalowanych (`_Ocr.wybielone`: pierwszy, a z `drugi`
    także drugi odczyt obrazu bez pól)."""
    tryby = obrazy.tryby_odczytow(dane, len(tekst.split(obrazy.ODDZIELACZ)))
    wybielone: tuple[Callable[[], str], ...] = ()
    if jezyk is not None:
        wybielone = (lambda: obrazy.ocr_tekst(dane, jezyk, wybiel=True),)
        if drugi is not None:
            wybielone += (lambda: obrazy.ocr_tekst(dane, jezyk, drugi=True, wybiel=True),)
    if drugi is None:
        return _Ocr(nazwa, tekst, tryby, wybielone)
    return _Ocr(nazwa, tekst + obrazy.ODDZIELACZ + drugi,
                tryby + obrazy.tryby_odczytow(dane, len(drugi.split(obrazy.ODDZIELACZ)), drugi=True), wybielone)


def _ocr_stron(ocr_stron: list[tuple[str, str]], zrodlo: _Zrodlo | None, **odczyt: bool) -> list[_Ocr]:
    """`_Ocr` stron jednego odczytu (`ocr_stron` – wynik `ocr_stron_pliku(..., **odczyt)`); ze `zrodlo` – z leniwymi odczytami
    dodatkowymi inicjałów tego samego odczytu (`_Ocr.wybielone`: render bez pól zamalowanych, `_Ocr.bez_tekstu`: render bez
    obiektów tekstowych, a w nim – bez pól). Każdy wariant to jeden OCR wszystkich stron pliku, wykonywany przy pierwszym
    użyciu (tylko dla grup inicjałów)."""
    if zrodlo is None:
        return [_Ocr(n, t) for n, t in ocr_stron]

    def wariant(**opcje: bool) -> Callable[[], list[tuple[str, str]]]:
        return functools.cache(lambda: ocr_stron_pliku(zrodlo.sciezka, zrodlo.w, zrodlo.jezyk, **odczyt, **opcje))

    wybielone, bez_tekstu = wariant(wybiel=True), wariant(bez_tekstu=True)
    bez_tekstu_wybielone = wariant(bez_tekstu=True, wybiel=True)

    def tekst(f: Callable[[], list[tuple[str, str]]], k: int) -> str:
        strony = f()
        return strony[k][1] if k < len(strony) else ""

    def strona(k: int, n: str, t: str) -> _Ocr:
        def bez() -> _Ocr:
            strony = bez_tekstu()
            return _Ocr(strony[k][0] if k < len(strony) else n, tekst(bez_tekstu, k),
                        wybielone=(lambda: tekst(bez_tekstu_wybielone, k),))
        return _Ocr(n, t, wybielone=(lambda: tekst(wybielone, k),), bez_tekstu=functools.cache(bez))
    return [strona(k, n, t) for k, (n, t) in enumerate(ocr_stron)]


def _odczyt_stron(zrodlo: _Zrodlo, **odczyt: bool) -> list[_Ocr]:
    """Kolejny odczyt stron pliku `zrodlo` (`ocr_stron_pliku(..., **odczyt)`: drugi albo trzeci) jako `_Ocr` z odczytami
    dodatkowymi inicjałów (`_ocr_stron`)."""
    return _ocr_stron(ocr_stron_pliku(zrodlo.sciezka, zrodlo.w, zrodlo.jezyk, **odczyt), zrodlo, **odczyt)


def _widoki(w: Wydobycie, ocr_osadzone: list[tuple[str, str]], ocr_stron: list[tuple[str, str]],
            cache: dict[int, Tekst], zrodlo: _Zrodlo | None = None) -> _Widoki:
    """Widoki pliku `w`; `zrodlo` – plik i język OCR do odczytów dodatkowych inicjałów (`_Ocr.wybielone`, `_Ocr.bez_tekstu`);
    bez niego (testy jednostkowe) inicjały w pikselach nie mają odczytu bez pól, a strony z warstwą – renderu bez tekstu."""
    liczone = [c for c in w.czesci if not c.strukturalna and not c.wariant]
    jezyk = zrodlo.jezyk if zrodlo is not None else None
    return _Widoki(zwykle=[(c.nazwa, _tekst_czesci(c, cache)) for c in w.czesci if not c.strukturalna],
                   strukt=[(c.nazwa, _tekst_czesci(c, cache)) for c in w.czesci if c.strukturalna],
                   do_liczenia=[Tekst(polacz_przeniesienia(c.tekst_wezlowy())) for c in liczone],
                   osadzone=[_ocr_obrazu(n, b, t, jezyk=jezyk) for (n, t), (_, b) in zip(ocr_osadzone, w.obrazy)],
                   strony=[_ocr_stron(ocr_stron, zrodlo)] if ocr_stron else [],
                   pdfy=list(dict.fromkeys(p for p, _ in w.pdfy)) if w.rodzaj in RODZAJE_POCZTY else [],
                   nazwy_liczenia=[c.nazwa for c in liczone], strony_z_warstwa=_strony_z_warstwa(w, ocr_stron),
                   binarne=frozenset(c.nazwa for c in w.czesci if c.binarna))


def _krotka(g: _Grupa) -> bool:
    """(J3) Inicjały albo wartość krótka (≤ `MAKS_ALNUM_KROTKIEJ` znaków alfanumerycznych) – nie szukana w widokach binarnych
    strumieni OLE (`_Widoki.binarne`)."""
    w = g.wartosci[0]
    return w.kategoria in KATEGORIE_INICJALOW or len(same_alnum(w.tekst)) <= MAKS_ALNUM_KROTKIEJ


def _strony_z_warstwa(w: Wydobycie, ocr_stron: list[tuple[str, str]]) -> frozenset[int]:
    """Pozycje stron (kolejność `ocr_stron`), których warstwa tekstowa pokazuje treść strony: część `pdf:strona N` (w poczcie –
    z przedrostkiem PDF-u załącznika) ma litery albo cyfry i nie ma znaków sterujących (`_ma_znaki_sterujace`: znaki bez mapy
    ToUnicode). Strona bez warstwy tekstowej (raster, tekst jako ścieżki) albo z warstwą zepsutą – poza zbiorem."""
    teksty = {c.nazwa: c.caly_tekst() for c in w.czesci if c.tresc}
    wynik = set()
    for k, (n, _) in enumerate(ocr_stron):
        t = teksty.get(n.replace(ekstrakcja.PREFIKS_RENDERU, "pdf:strona", 1))
        if t and any(ch.isalnum() for ch in t) and not _ma_znaki_sterujace(t):
            wynik.add(k)
    return frozenset(wynik)


def _pdf_nazwy(nazwa: str, przedrostki: Iterable[str]) -> str | None:
    """Przedrostek PDF-u (najdłuższy pasujący – PDF w PDF-ie), do którego należy część, obraz albo strona o nazwie `nazwa`
    (`obraz:`/`metadane obrazu:` pominięte); None – poza PDF-ami."""
    for pocz in ("obraz:", "metadane obrazu:"):
        nazwa = nazwa.removeprefix(pocz)
    return max((p for p in przedrostki if nazwa.startswith(p)), key=len, default=None)


def _ile_poczty(g: _Grupa, wid: _Widoki) -> int:
    """Krotność grupy w wiadomości z PDF-ami w załącznikach: render stron pokazuje tylko PDF-y, więc reguła „warstwa tekstowa +
    obrazy osadzone ALBO render stron” dotyczy każdego PDF-u osobno – wystąpienia w częściach i obrazach spoza PDF-ów (treść,
    nagłówki, inne załączniki) + Σ po PDF-ach max(wystąpienia w jego częściach i obrazach, OCR jego stron – każdy odczyt osobno).
    PDF w wiadomości zagnieżdżonej to osobny PDF."""
    def tekst(p: str | None) -> int:
        ile = _ile_wystapien(g.reg, [t for n, t in zip(wid.nazwy_liczenia, wid.do_liczenia) if _pdf_nazwy(n, wid.pdfy) == p])
        if g.ocr:
            ile += _ile_w_ocr(g.reg_ocr, g.reg_ocr_z, [o for o in wid.osadzone if _pdf_nazwy(o.nazwa, wid.pdfy) == p], g.reg)
        return ile

    ile = tekst(None)
    for p in wid.pdfy:
        ile += max([tekst(p), *(_ile_w_ocr(g.reg_ocr, g.reg_ocr_z, [o for o in odczyt if _pdf_nazwy(o.nazwa, wid.pdfy) == p],
                                           g.reg) for odczyt in wid.strony)])
    return ile


def _trafione_tokeny(reg: Regula, reg_z: Regula | None, t: Tekst, liczace: bool = False) -> set[str]:
    """(OCR) Tokeny identyfikujące (`liczace`: wszystkie liczące się – trafienie pełne wartości ze słów generycznych), którymi
    wartość trafia tekst (dokładnie, rozmyto, po złożeniu znaków mylonych albo formą odmienioną), bez znaków diakrytycznych – klucz
    porównania odczytów (`_trafienia_ocr`) – w postaci złożonej (`normalizacja.zloz_szkielet`), wspólnej dla obu wariantów."""
    wynik: set[str] = set()
    for r, tt in ((reg, t), (reg_z, _wariant(reg_z, t))):
        if r is None or tt is None:
            continue
        ident = set(r.liczace if liczace else r.identyfikujace)
        wynik |= _trafione_czesci(r, tt, True)          # identyfikator z etykietą: części jak tokeny (J1)
        wynik |= {zloz_szkielet(tok) for tok in r.liczace if tok in ident and _slowo_dokladnie(tok, tt, True, r.obce)}
        wynik |= {zloz_szkielet(tok) for tok in r.identyfikujace
                  if r.rdzenie.get(tok) and not r.rdzenie[tok].isdisjoint(tt.slowa)}
    return wynik


def _dokladne_tokeny(reg: Regula, reg_z: Regula | None, t: Tekst) -> set[str]:
    """(OCR) Liczące się tokeny wartości, które są słowem tekstu DOKŁADNIE (nie rozmyto, nie formą odmienioną, nie po złożeniu
    znaków mylonych), w postaci złożonej – w kluczu `_trafione_tokeny` (`_trafienia_ocr`)."""
    wynik: set[str] = set()
    for r, tt in ((reg, t), (reg_z, _wariant(reg_z, t))):
        if r is not None and tt is not None:
            wynik |= {zloz_szkielet(tok) for tok in r.liczace if tok in tt.slowa}
            wynik |= _trafione_czesci(r, tt, False)
    return wynik


def _pewny_token(reg: Regula, reg_z: Regula | None, t: Tekst) -> bool:
    """(OCR) Czy trafienie opiera się nie tylko na dopasowaniu rozmytym tokenów: wartość jest identyfikatorem/datą/kwotą
    (`id_wzorce`), e-mail/URL trafia jako ciąg alfanumeryczny (`Regula.ocr_alnum`, próg `PROG_ALNUM_OCR`: „@” czytane jako „o”) albo
    któryś liczący się token jest słowem tekstu dokładnie lub – token z cyfrą – po złożeniu znaków mylonych („I48” = „148”)."""
    for r, tt in ((reg, t), (reg_z, _wariant(reg_z, t))):
        if r is None or tt is None:
            continue
        if r.id_wzorce or (r.ocr_alnum and obrazy.zawiera_rozmyto(r.ocr_alnum, _bez_obcych(r, tt.mylone()), PROG_ALNUM_OCR,
                                                                   granice=True)):
            return True
        mylone = tt.slowa_mylone()
        if any(tok in tt.slowa or (any(c.isdigit() for c in tok) and any(s not in r.obce for s in mylone.get(zloz_mylone(tok), ())))
               for tok in r.liczace):
            return True
    return False


def _trafienia_ocr(g: _Grupa, strony: list[list[_Ocr]], osadzone: bool = False) -> tuple[list[tuple[str, str]], set[int]]:
    """(OCR stron i obrazów osadzonych) Trafienia grupy w odczytach stron albo obrazów (`strony`: lista odczytów, w każdym `_Ocr`
    na stronę/obraz – ten sam numer to ten sam obraz) i numery stron/obrazów z trafieniem bez potwierdzenia. Odczyty jednej strony
    (części `_Ocr.surowy` rozdzielone `obrazy.ODDZIELACZ` ze wszystkich rozdzielczości i trybów: 300 dpi psm 3, 400 dpi psm 3
    i psm 6, ewentualnie 300 dpi psm 6, odczyty po wyprostowaniu) traktujemy jako niezależne; odczyty obrazu osadzonego – gdy
    różnią się trybem Tesseracta (`_Ocr.tryby`: psm 6 i 11 małego obrazu w dwóch skalach, psm 3 oraz 6 i 11 dużego), a odczyty
    tym samym trybem w innej skali – gdy wspólny token jest w którymś z nich słowem DOKŁADNIE (powiększenie tych samych pikseli
    powtarza szum rozmyty – „Osoba” z miniatury ODT czytane w każdej skali jako „Osowa” ≈ „Sowa” – ale dokładne nazwisko
    przeczytane w dwóch skalach to dwa odczyty prawdziwego tekstu). Na obrazie osadzonym token identyfikujący
    ≥ `MIN_DL_TOKENU_BEZ_POTWIERDZENIA` znaków, który jest słowem odczytu dokładnie, wystarcza bez potwierdzenia. Trafienie
    pełne wystarcza z jednego odczytu, chyba że składa się wyłącznie z trafień rozmytych (`_pewny_token`: „MARA” ≈ „Maria”) –
    wtedy, jak częściowe, liczy się tylko, gdy ten sam token wartości trafia też w innym (niezależnym) odczycie tej samej strony
    (potwierdzone – pełne). Inicjały (`KATEGORIE_INICJALOW`) – trafienie (pełne) zawsze z potwierdzeniem: wzorzec trafia w co
    najmniej dwóch odczytach tej samej strony/obrazu i w odczycie tego obrazu z wybielonymi polami zamalowanymi
    (`_po_wybieleniu`; na stronach z warstwą tekstową – w renderze bez obiektów tekstowych, `_ocen_grupe`); w odczytach obrazów
    osadzonych (`osadzone`) – poza wierszami szumu (`_bez_szumu`).
    Śmieci OCR (okaleczony zamiennik „EMA” z „[EMAIL_10]”, linia tabeli czytana jako „ray”, szum miniatury ODT) rzadko powtarzają
    się w innym odczycie. Blok, który czyta tylko jeden tryb (psm 3 bywa ślepy na blok w układzie wielokolumnowym), ma odczyt potwierdzający dopiero z tego trybu
    w drugiej rozdzielczości – dokłada go wywołujący (`obrazy.ocr_stron_pdf(trzeci=True)`, `obrazy.ocr_tekst(drugi=True)`), gdy
    zwracamy brak potwierdzenia."""
    inicjaly = g.wartosci[0].kategoria in KATEGORIE_INICJALOW
    # (nazwa, tekst odczytu, klucz niezależności: tryb obrazu osadzonego albo sam odczyt strony); inicjały w obrazach osadzonych
    # (`osadzone`) – odczyt bez wierszy szumu (`_bez_szumu`)
    szum = inicjaly and osadzone
    odczyty: dict[int, list[tuple[str, Tekst, tuple]]] = {}
    obiekty: dict[int, list[_Ocr]] = {}
    for nr_odczytu, odczyt in enumerate(strony):
        for nr, o in enumerate(odczyt):
            obiekty.setdefault(nr, []).append(o)
            odczyty.setdefault(nr, []).extend(
                (o.nazwa, _bez_szumu(g, surowy, caly) if szum else caly,
                 ("psm", o.tryby[k]) if k < len(o.tryby) else ("odczyt", nr_odczytu, k))
                for k, ((caly, _), surowy) in enumerate(zip(o.odczyty(), o.surowy.split(obrazy.ODDZIELACZ))))
    traf: list[tuple[str, str]] = []
    niepotwierdzone: set[int] = set()
    for nr in sorted(odczyty):
        wyniki = [(n, r, t, z) for n, t, z in odczyty[nr] if (r := _dopasuj_z_wariantami(g.reg_ocr, g.reg_ocr_z, t, True))]
        if inicjaly:
            # inicjały (1–3 litery, poprawka H6a I2): szum OCR trafia krótki wzorzec – trafienie (zawsze pełne) liczy się tylko,
            # gdy wzorzec trafia też w innym odczycie tej samej strony/obrazu (inna rozdzielczość albo inny tryb) i zostaje po
            # wybieleniu pól zamalowanych (I-R1: czarne pole czytane jako „rs” w każdym odczycie); bez potwierdzenia wywołujący
            # dokłada kolejny odczyt (a z nim – jego odczyt bez pól)
            if len(wyniki) >= 2 and _po_wybieleniu(g, obiekty[nr], osadzone):
                traf += [(n, r) for n, r, _, _ in wyniki]
            elif wyniki:
                niepotwierdzone.add(nr)
            continue
        pelne = [(n, r) for n, r, t, _ in wyniki if r == "pelny" and _pewny_token(g.reg_ocr, g.reg_ocr_z, t)]
        if pelne:
            traf += pelne
            continue
        # trafienie pełne (same rozmyte) potwierdza wspólny token liczący się, częściowe – wspólny token identyfikujący
        tokeny = [_trafione_tokeny(g.reg_ocr, g.reg_ocr_z, t, liczace=r == "pelny") for _, r, t, _ in wyniki]
        dokladne = [_dokladne_tokeny(g.reg_ocr, g.reg_ocr_z, t) for _, _, t, _ in wyniki]

        def potwierdza(i: int, j: int) -> bool:
            wspolne = tokeny[i] & tokeny[j]
            # inny tryb obrazu albo inny odczyt strony – niezależny; ten sam tryb obrazu (inna skala) – token dokładny
            return bool(wspolne) and (wyniki[i][3] != wyniki[j][3] or bool(wspolne & (dokladne[i] | dokladne[j])))

        def dlugi_dokladny(i: int) -> bool:
            # obraz osadzony: token identyfikujący trafiony dokładnie, ≥ MIN_DL_TOKENU_BEZ_POTWIERDZENIA znaków (odczyt z tokenem
            # dokładnym, który tu dotarł, jest częściowy – pełny z tokenem dokładnym liczy się wyżej – więc `tokeny[i]` to tokeny
            # identyfikujące)
            return wyniki[i][3][0] == "psm" and any(len(tok) >= MIN_DL_TOKENU_BEZ_POTWIERDZENIA
                                                    for tok in tokeny[i] & dokladne[i])

        potw = [i for i in range(len(wyniki))
                if any(potwierdza(i, j) for j in range(len(wyniki)) if j != i) or dlugi_dokladny(i)]
        if potw:
            i = next((i for i in potw if wyniki[i][1] == "pelny"), potw[0])
            traf.append((wyniki[i][0], wyniki[i][1]))
        elif wyniki:
            niepotwierdzone.add(nr)
    return traf, niepotwierdzone


def _po_wybieleniu(g: _Grupa, obiekty: list[_Ocr], osadzone: bool = False) -> bool:
    """(Inicjały w pikselach, poprawka H6a I-R1) Czy wzorzec trafia także w którymś odczycie tej strony/obrazu z wybielonymi
    polami zamalowanymi (`_Ocr.wybielone` każdego odczytu – po kolei i leniwie: kolejny OCR tylko, gdy poprzedni nie trafia).
    Czarne prostokąty redakcji rastrowej OCR czyta w każdym odczycie jako to samo krótkie „słowo”, więc samo potwierdzenie
    innym odczytem ich nie odsiewa; parafa pisana tekstem (cienkie pociągnięcia) po wybieleniu zostaje. Odczyt bez obrazu
    źródłowego (`_Ocr` bez `wybielone` – testy jednostkowe) – bez tego warunku. Obraz osadzony (`osadzone`) – odczyty bez wierszy
    szumu (`_bez_szumu`), jak w `_trafienia_ocr`."""
    funkcje = [f for o in obiekty for f in o.wybielone]
    if not funkcje:
        return True
    for f in funkcje:
        o = _Ocr("", f())
        for (caly, _), surowy in zip(o.odczyty(), o.surowy.split(obrazy.ODDZIELACZ)):
            if _dopasuj_z_wariantami(g.reg_ocr, g.reg_ocr_z, _bez_szumu(g, surowy, caly) if osadzone else caly, True):
                return True
    return False


def _bez_szumu(g: _Grupa, surowy: str, caly: Tekst) -> Tekst:
    """(Inicjały w OCR obrazów osadzonych) Odczyt (`surowy` – tekst OCR odczytu, `caly` – ten sam jako `Tekst`) bez wierszy szumu.
    Wiersz szumu ma co najmniej `MIN_SLOW_SZUMU` tokenów szumu – tokenów ≥ `MIN_DL_SLOWA_SZUMU` liter zapisanych samymi wielkimi
    literami, nie z jednej powtórzonej litery („XXXX” maski czyta OCR wiernie) – a żaden jego token literowy ≥ `MIN_DL_SLOWA_SZUMU`
    liter nie jest słowem dokumentu (`_Grupa.slownik`; porównanie bez znaków diakrytycznych po obu stronach – OCR je gubi). Znak
    maskujący powtórzony w obrazie (wiersz gwiazdek w miejscu logo) OCR czyta w każdym odczycie jako ten sam ciąg wielkich liter
    („A ARAHAL AC AE … ERRE ERE ARRE RR AR”), a krótki wzorzec inicjałów trafia w nim przypadkowo, więc potwierdzenie innym
    odczytem go nie odsiewa; litery jego tokenów szumu (bez diakrytyków) to najwyżej `MAKS_LITER_SZUMU` różnych liter – szum
    powtórzonego znaku ma ich kilka, cztery prawdziwe słowa wielkimi literami (nagłówek z zamiennikami) – kilkanaście. W miejscu
    usuniętego wiersza stoi `_ODDZIELACZ_WIERSZY` (usunięty wiersz między „J.” a „K.” nie tworzy „J.K.”), sąsiednie wiersze
    zostawione łączy „\\n” jak w odczycie.
    Ta sama reguła dla oryginału i wyniku; grupa bez słownika – odczyt bez zmian."""
    if g.slownik is None:
        return caly

    def szum(wiersz: str) -> bool:
        slowa = [s for s in _SLOWO.findall(wiersz) if len(s) >= MIN_DL_SLOWA_SZUMU and s.isalpha()]
        if any(zloz_diakrytyki(normalizuj(s)) in g.slownik for s in slowa):
            return False
        szumowe = [s for s in slowa if s.isupper() and len(set(s)) > 1]
        litery = {c for s in szumowe for c in zloz_diakrytyki(normalizuj(s))}
        return len(szumowe) >= MIN_SLOW_SZUMU and len(litery) <= MAKS_LITER_SZUMU
    czesci: list[str] = []
    usuniety = zmiana = False
    for w in surowy.splitlines():
        if not w.strip():
            continue
        if szum(w):
            usuniety = zmiana = True
            continue
        if czesci:          # „\n” między sąsiednimi wierszami zostawionymi, oddzielacz – w miejscu usuniętych
            czesci.append(_ODDZIELACZ_WIERSZY if usuniety else "\n")
        czesci.append(w)
        usuniety = False
    return Tekst("".join(czesci)) if zmiana else caly


def _indeks_fraz(frazy: Iterable[tuple[str, ...]]) -> dict[str, list[tuple[str, ...]]]:
    """Indeks krotek tokenów po pierwszym tokenie, kandydaci od najdłuższych (jak `_indeks_gold`)."""
    indeks: dict[str, list[tuple[str, ...]]] = {}
    for tok in set(frazy):
        if tok:
            indeks.setdefault(tok[0], []).append(tok)
    for lista in indeks.values():
        lista.sort(key=len, reverse=True)
    return indeks


def _krotnosc_fraz(wid: _Widoki, indeks: dict[str, list[tuple[str, ...]]], frazy: Iterable[tuple[str, ...]]) -> Counter:
    """Wystąpienia `frazy` (krotki tokenów) w pliku przejściem `_przejdz` po indeksie `indeks` (najdłuższy kandydat wygrywa: z
    tekstami gold w indeksie fraza wewnątrz wystąpienia całej wartości liczy się do wartości). Widoki jak krotność grupy
    (`_ocen_grupe`): warstwa tekstowa (`_Widoki.do_liczenia`) + obrazy osadzone (każdy – najwięcej z odczytów) ALBO render stron
    (każdy odczyt osobno, strona – najwięcej z odczytów) – większa liczba."""
    frazy = set(frazy)

    def w_tekscie(tokeny: list[str]) -> Counter:
        licznik: Counter = Counter()
        _przejdz(tokeny, indeks, None, licznik)
        return Counter({f: licznik[f] for f in frazy if licznik[f]})

    def w_ocr(o: _Ocr) -> Counter:
        najwiecej: Counter = Counter()
        for caly, _ in o.odczyty():
            najwiecej |= w_tekscie(caly.ciag())
        return najwiecej

    wynik: Counter = Counter()
    for t in wid.do_liczenia:
        wynik += w_tekscie(t.ciag())
    for o in wid.osadzone:
        wynik += w_ocr(o)
    for odczyt in wid.strony:
        strony: Counter = Counter()
        for o in odczyt:
            strony += w_ocr(o)
        wynik |= strony
    return wynik


def _z_czesciami_spoza_gold(grupy: list[_Grupa], wid: _Widoki, wartosci: list[Wartosc], strony: int) -> list[_Grupa]:
    """(J1-fix3, I1 – orzeczenie kontrolera) Części identyfikatorów (`Regula.id_czesci`), które oryginał ma także poza
    wystąpieniami wartości gold – reguła krotności jak dla wartości niejednoznacznych (`niejednoznaczne`): cytat innej sprawy
    z tym samym wydziałem i repertorium („VII Ca 6470/18” obok własnej „VII Ca 1554/21”) nie jest gold, więc trafienie części
    w wyniku liczy się tylko wtedy, gdy wynik ma ją częściej niż oryginał poza gold (`_bez_czesci_spoza_gold`). Liczba wystąpień
    poza gold (`wid` – widoki ORYGINAŁU, `wartosci` – wpisy gold z powtórzeniami, `strony` – liczba stron PDF) to mniejsza z dwóch
    miar: przejście z tekstami gold w indeksie (`_krotnosc_fraz`) i wszystkie wystąpienia części minus jej wystąpienia w wpisach
    gold (nagłówek/stopka PDF – raz na stronę); OCR, który przeczyta wartość gold z błędem, a jej część poprawnie, nie zawyża więc
    liczby (nie ukrywa wycieku). Dotyczy wyłącznie części opisowych sygnatury (`Regula.id_opisowe`, J1-fix4, m1) – numeru i części
    rachunku nie, więc własny numer odsłonięty jest wyciekiem także przy zamaskowanym cytacie z tym samym numerem. Grupy bez
    takich części – bez zmian."""
    kandydaci: dict[int, list[tuple[str, tuple[str, ...]]]] = {}
    for i, g in enumerate(grupy):
        if g.reg.id_czesci:
            teksty = _teksty_czesci(g.wartosci[0])
            # (J1-fix4, m1) tylko części opisowe (wydział, repertorium, rodzaj): numer i części rachunku nie są krotnościowe –
            # własny numer odsłonięty przy zamaskowanym cytacie z tym samym numerem to wyciek (jak w sędzi tekstowym)
            kandydaci[i] = [(a, k) for a, _ in g.reg.id_czesci if a in g.reg.id_opisowe
                            and (k := tuple(_tokeny(teksty.get(a, ""))))]
    frazy = {k for lista in kandydaci.values() for _, k in lista}
    if not frazy:
        return grupy
    indeks = _indeks_fraz({tuple(_tokeny(w.tekst)) for w in wartosci} | frazy)
    poza_gold = _krotnosc_fraz(wid, indeks, frazy)
    if not poza_gold:
        return grupy
    same_frazy = _indeks_fraz(frazy)
    wszystkie = _krotnosc_fraz(wid, same_frazy, frazy)
    w_gold: Counter = Counter()
    for w in wartosci:
        licznik: Counter = Counter()
        _przejdz(_tokeny(w.tekst), same_frazy, None, licznik)
        for f, n in licznik.items():
            w_gold[f] += n * (strony if w.miejsce in ("naglowek", "stopka") else 1)
    wynik = list(grupy)
    for i, lista in kandydaci.items():
        czesci = tuple(_CzescSpozaGold(a, k, n) for a, k in lista
                       if (n := min(poza_gold[k], max(0, wszystkie[k] - w_gold[k]))))
        if czesci:
            wynik[i] = dataclasses.replace(grupy[i], czesci_poza=czesci, indeks_poza=indeks)
    return wynik


def _bez_czesci_spoza_gold(g: _Grupa, wid: _Widoki) -> _Grupa:
    """Grupa, której części obecne w oryginale poza gold (`_Grupa.czesci_poza`) występują w pliku `wid` nie częściej niż tam,
    ma je w regułach jako pominięte (`Regula.id_pominiete`: nie są trafieniem – zostawiony cytat innej sprawy nie jest wyciekiem
    własnej sygnatury). Krotność w pliku – `_krotnosc_fraz` z tym samym indeksem co w oryginale."""
    ile = _krotnosc_fraz(wid, g.indeks_poza, [c.tokeny for c in g.czesci_poza])
    pominiete = frozenset(c.alnum for c in g.czesci_poza if ile[c.tokeny] <= c.poza)
    if not pominiete:
        return g
    # wariant złożony (`_Grupa.reg_z`, `reg_ocr_z`) ma części w szkielecie
    pominiete |= {zloz_szkielet(a) for a in pominiete}

    def bez(r: Regula | None) -> Regula | None:
        return None if r is None else dataclasses.replace(r, id_pominiete=pominiete)
    return dataclasses.replace(g, reg=bez(g.reg), reg_z=bez(g.reg_z), reg_ocr=bez(g.reg_ocr), reg_ocr_z=bez(g.reg_ocr_z))


def _ocen_grupe(g: _Grupa, wid: _Widoki, orig_strukt: dict[str, Tekst]) -> tuple[tuple[str, str] | None, int, bool,
                                                                                 frozenset[int]]:
    """(miejsce, rodzaj) najlepszego trafienia grupy w widokach pliku (None – brak), liczba jej wystąpień (≤ krotność grupy
    przycina wywołujący), czy w OCR stron było trafienie bez potwierdzenia i numery obrazów osadzonych (`_Widoki.osadzone`)
    z trafieniem bez potwierdzenia (`_trafienia_ocr` – wywołujący dokłada wtedy drugi odczyt stron / tych obrazów). Te same
    reguły dla oryginału (linia bazowa) i wyniku. OCR stron dotyczy każdej grupy, także wartości obrazowych niewykrywalnych
    w OCR obrazu osadzonego (`_Grupa.ocr` False): render pokazuje to samo, co warstwa tekstowa. Inicjały – na stronach, których
    warstwa tekstowa pokazuje treść (`_Widoki.strony_z_warstwa`), OCR renderu strony bez obiektów tekstowych
    (`_Ocr.bez_tekstu`). Części identyfikatora obecne w oryginale poza gold – `_bez_czesci_spoza_gold`."""
    if g.czesci_poza:
        g = _bez_czesci_spoza_gold(g, wid)
    if g.wartosci[0].kategoria in KATEGORIE_INICJALOW and wid.strony_z_warstwa:
        # inicjały (wzorzec 1–3 liter, poprawki H6a I2 i I-R1): szum OCR z zamaskowanego tekstu powtarza się w każdym
        # odczycie strony (gwiazdki czytane jako „ar” w 300 i 400 dpi, psm 3 i 6), a tekst strony ma dokładną warstwę – OCR
        # czyta więc render bez obiektów tekstowych: zostają piksele spoza warstwy (parafa jako obraz inline albo XObject,
        # ścieżki), gwiazdki znikają; strona bez renderu bez tekstu (testy jednostkowe) – pusty odczyt
        def strona(k: int, o: _Ocr) -> _Ocr:
            if k not in wid.strony_z_warstwa:
                return o
            return o.bez_tekstu() if o.bez_tekstu is not None else _Ocr(o.nazwa.removeprefix("obraz:"), "")
        wid = dataclasses.replace(wid, strony=[[strona(k, o) for k, o in enumerate(odczyt)] for odczyt in wid.strony])
    # widoki binarnych strumieni OLE (DOC: `Data`, obiekty osadzone…) – bez wartości krótkich i inicjałów (J3, `_krotka`)
    zwykle = [(n, t) for n, t in wid.zwykle if n not in wid.binarne] if wid.binarne and _krotka(g) else wid.zwykle
    traf = [(n, r) for n, t in zwykle if (r := _dopasuj_z_wariantami(g.reg, g.reg_z, t, False))]
    # części strukturalne: tylko pełna wartość/identyfikator, i tylko jeśli oryginał jej tam nie miał
    for n, t in wid.strukt:
        r = _dopasuj_z_wariantami(g.reg, g.reg_z, t, False, tylko_fraza=True)
        if r and not (n in orig_strukt and _dopasuj_z_wariantami(g.reg, g.reg_z, orig_strukt[n], False, tylko_fraza=True)):
            traf.append((n, r))
    # obrazy osadzone – jak strony: trafienie częściowe (i pełne z samych trafień rozmytych) z potwierdzeniem innym odczytem
    # (`_trafienia_ocr`: inny tryb albo ten sam tryb w innej skali z tokenem dokładnym; długi token dokładny – bez potwierdzenia)
    traf_obrazow, obrazy_bez = _trafienia_ocr(g, [wid.osadzone], osadzone=True) if g.ocr and wid.osadzone else ([], set())
    traf_stron, strony_bez = _trafienia_ocr(g, wid.strony) if wid.strony else ([], set())
    najl = _najlepsze(traf + traf_obrazow + traf_stron)
    niepotwierdzone = bool(strony_bez), frozenset(obrazy_bez)
    if najl is None or len(g.wartosci) == 1:
        return najl, 1 if najl else 0, *niepotwierdzone
    if wid.pdfy:
        return najl, max(1, _ile_poczty(g, wid)), *niepotwierdzone
    # widoki tej samej treści się nie sumują: warstwa tekstowa + obrazy osadzone ALBO render stron (każdy odczyt osobno)
    ile = _ile_wystapien(g.reg, wid.do_liczenia)
    if g.szkielet and g.reg_z is not None:
        # homoglify: zapis „naprawiony” na łacinę też jest wystąpieniem wartości
        ile = max(ile, _ile_wystapien(g.reg_z, [t.zlozony() for t in wid.do_liczenia]))
    if g.ocr:
        ile += _ile_w_ocr(g.reg_ocr, g.reg_ocr_z, wid.osadzone, g.reg)
    ile = max([ile, *(_ile_w_ocr(g.reg_ocr, g.reg_ocr_z, odczyt, g.reg) for odczyt in wid.strony)])
    return najl, max(1, ile), *niepotwierdzone


def _drugi_odczyt_obrazow(wid: _Widoki, ocr_osadzone: list[tuple[str, str]], obrazy_pliku: list[tuple[str, bytes]],
                          jezyk: str, oceny: dict[int, tuple], ocen) -> _Widoki:
    """Obrazy osadzone z trafieniem bez potwierdzenia (czwarty element `_ocen_grupe`) dostają drugi odczyt
    (`obrazy.ocr_wiele(drugi=True)`), dopisany do ich `_Ocr` jako kolejne odczyty; grupy z takim trafieniem są oceniane ponownie
    (`ocen(i, widoki)`, wynik w `oceny`). Zwraca widoki z drugimi odczytami (bez zmian, gdy żaden obraz ich nie potrzebuje)."""
    nr = sorted(set().union(*(o[3] for o in oceny.values())))
    if not nr:
        return wid
    drugie = dict(zip(nr, (t for _, t in obrazy.ocr_wiele([obrazy_pliku[k] for k in nr], jezyk, drugi=True))))
    wid = dataclasses.replace(wid, osadzone=[_ocr_obrazu(n, obrazy_pliku[k][1], t, drugie[k], jezyk) if k in drugie
                                             else wid.osadzone[k] for k, (n, t) in enumerate(ocr_osadzone)])
    oceny.update({i: ocen(i, wid) for i in [i for i, o in oceny.items() if o[3]]})
    return wid


#: Rodzaje plików-wiadomości: strony PDF-ów w ich załącznikach (także w wiadomości zagnieżdżonej) są czytane OCR jak strony
#: samodzielnego PDF-u.
RODZAJE_POCZTY: frozenset[str] = frozenset({"eml", "msg"})


def ocr_stron_pliku(sciezka: Path, w: Wydobycie, jezyk: str, drugi: bool = False, trzeci: bool = False,
                    bez_tekstu: bool = False, wybiel: bool = False) -> list[tuple[str, str]]:
    """OCR stron, które widzi czytelnik pliku `sciezka` (wydobycie `w`): strony samego PDF-u (`obrazy.ocr_stron_pdf`) albo – dla
    poczty (`RODZAJE_POCZTY`) – strony PDF-ów w załącznikach (`obrazy.ocr_stron_osadzonych`); inne formaty – pusta lista.
    `drugi`/`trzeci` – kolejne odczyty (zob. docstring modułu); `bez_tekstu`/`wybiel` – warianty odczytu dla inicjałów
    (`_ocr_stron`)."""
    # warianty tylko, gdy włączone – wywołanie odczytu zwykłego bez zmian
    warianty = {k: True for k, v in (("bez_tekstu", bez_tekstu), ("wybiel", wybiel)) if v}
    if w.rodzaj == "pdf":
        return obrazy.ocr_stron_pdf(sciezka, jezyk, drugi=drugi, trzeci=trzeci, **warianty)
    if w.rodzaj in RODZAJE_POCZTY:
        return obrazy.ocr_stron_osadzonych(w.pdfy, jezyk, drugi=drugi, trzeci=trzeci, **warianty)
    return []


@dataclass
class ZbioryDokumentu:
    """Wszystko, co zależy WYŁĄCZNIE od oryginału i gold (zob. docstring modułu, „Zbiory dokumentu”): liczone raz, wspólne dla
    wszystkich uczestników – `zbiory_dokumentu` nie dostaje pliku wyniku."""

    orig: Wydobycie
    #: warstwa tekstowa oryginału PDF zepsuta (`warstwa_tekstowa_zepsuta`) – wtedy OCR jego stron wchodzi do zbiorów; poczta – zepsuta
    #: warstwa któregoś PDF-u załącznika (`zepsute_pdfy_poczty`; do zbiorów wchodzi OCR stron tylko takich PDF-ów)
    zepsuty: bool
    jezyk_ocr: str
    #: wartości ocenione (bez niejednoznacznych), unikalne pary (id, tekst)
    oceniane: list[Wartosc]
    uniq: list[Wartosc]
    niewykrywalne: list[str]
    niejednoznaczne: set[str]
    generyczne: frozenset[str]
    #: linia bazowa: identyfikatory wartości odnajdywanych w oryginale (mianownik)
    bazowe: frozenset[str]
    grupy: list[_Grupa]
    orig_strukt: dict[str, Tekst]
    #: identyfikacja pośrednia: kombinacje (pole manifestu), grupy składników (po jednej wartości – `wartosci_skladnikow`) i linia
    #: bazowa składników – identyfikatory składników widocznych („pelny”) w oryginale
    kombinacje: list[dict] = field(default_factory=list)
    skladniki: list[_Grupa] = field(default_factory=list)
    skladniki_bazowe: frozenset[str] = frozenset()
    #: id składnika -> id odcinków jego rdzenia (grupy w `skladniki`), gdy rdzeń da się szukać bez offsetów (docstring modułu)
    rdzenie: dict[str, tuple[str, ...]] = field(default_factory=dict)
    #: zbiory policzone bez przejść szkieletu (ani wartości, ani oryginał nie mają liter szkieletu – docstring modułu, pkt 6):
    #: funkcja liczy pełne zbiory (z przejściami szkieletu – grupy z wariantem `tylko_cyrylica`) z tego samego oryginału, gdy
    #: litery szkieletu ma wynik (`ocen_plik`); None – zbiory pełne
    pelne: Callable[[], "ZbioryDokumentu"] | None = None


def wartosci_skladnikow(posrednie: list[dict], wartosci: Iterable[Wartosc], jezyk: str) -> list[Wartosc]:
    """Składniki kombinacji jako wartości do oceny (id = id składnika): składnik gold z kategorią swojej wartości (`wartosci`),
    spoza gold (albo gold nieobecny w `wartosci`) – z kategorią reguły `posrednie.kategoria_reguly(rola)`."""
    kategorie = {w.id: w.kategoria for w in wartosci}
    return [Wartosc(s["id"], kategorie.get(s["wartosc_id"]) or _posrednie.kategoria_reguly(s["rola"]),
                    polacz_przeniesienia(s["tekst"]), jezyk, s["miejsce"], "SKLADNIK")
            for k in posrednie for s in k["skladniki"]]


def wartosci_rdzeni(posrednie: list[dict], wartosci: Iterable[Wartosc], jezyk: str) -> tuple[list[Wartosc],
                                                                                            dict[str, tuple[str, ...]]]:
    """Odcinki rdzeni składników (`posrednie.odcinki_rdzenia`) jako wartości do oceny (id `<id składnika>~<n>`, kategoria jak
    składnik – `wartosci_skladnikow`) i id składnika -> id jego odcinków; składnik, którego rdzeń to cały tekst, nie ma odcinków."""
    kategorie = {w.id: w.kategoria for w in wartosci}
    wynik: list[Wartosc] = []
    odcinki: dict[str, tuple[str, ...]] = {}
    for k in posrednie:
        for s in k["skladniki"]:
            teksty = _posrednie.odcinki_rdzenia(s["tekst"], s.get("rdzen") or [s["tekst"]])
            if teksty == [s["tekst"]]:
                continue
            kat = kategorie.get(s["wartosc_id"]) or _posrednie.kategoria_reguly(s["rola"])
            ids = tuple(f"{s['id']}~{n}" for n in range(1, len(teksty) + 1))
            wynik += [Wartosc(i, kat, polacz_przeniesienia(t), jezyk, s["miejsce"], "SKLADNIK") for i, t in zip(ids, teksty)]
            odcinki[s["id"]] = ids
    return wynik, odcinki


def _pelny(ocena: tuple) -> bool:
    return bool(ocena[0]) and ocena[0][1] == "pelny"


def _ocen_z_odczytami(grupy: list[_Grupa], wid: _Widoki, sciezka: Path, w: Wydobycie, ocr_osadzone: list[tuple[str, str]],
                      jezyk: str, orig_strukt: dict[str, Tekst], potrzebny) -> dict[int, tuple]:
    """Ocena grup (`_ocen_grupe`) z drugim odczytem obrazów osadzonych i drugim/trzecim odczytem stron – ta sama kolejność
    co dla gold w `zbiory_dokumentu`/`ocen_plik`. `wid` – widoki pierwszego odczytu; strony czytane ponownie dla grup
    z trafieniem bez potwierdzenia albo `potrzebny(i, ocena)`. Używane dla składników identyfikacji pośredniej."""
    def ocen(i: int, widoki: _Widoki) -> tuple:
        return _ocen_grupe(grupy[i], widoki, orig_strukt)
    oceny = {i: ocen(i, wid) for i in range(len(grupy))}
    wid = _drugi_odczyt_obrazow(wid, ocr_osadzone, w.obrazy, jezyk, oceny, ocen)
    drugi = [i for i, o in oceny.items() if wid.strony and (o[2] or potrzebny(i, o))]
    if drugi:
        wid_2 = dataclasses.replace(wid, strony=[*wid.strony, _odczyt_stron(_Zrodlo(sciezka, w, jezyk), drugi=True)])
        oceny.update({i: ocen(i, wid_2) for i in drugi})
        trzeci = [i for i in drugi if oceny[i][2]]
        if trzeci:
            wid_3 = dataclasses.replace(wid_2, strony=[*wid_2.strony, _odczyt_stron(_Zrodlo(sciezka, w, jezyk), trzeci=True)])
            oceny.update({i: ocen(i, wid_3) for i in trzeci})
    return oceny


def zbiory_dokumentu(oryginal: Path, wartosci: list[Wartosc], reguly: RegulyWycieku | None = None,
                     jezyk: str | None = None, *, leksykon, posrednie: list[dict] | None = None) -> ZbioryDokumentu:
    """Zbiory dokumentu (niejednoznaczne, generyczne, niewykrywalne, linia bazowa) i reguły wartości – z samego oryginału
    (parametry jak w `ocen_plik`). `posrednie` – kombinacje identyfikacji pośredniej (grupy składników i ich linia bazowa).
    Błąd odczytu ORYGINAŁU to `ValueError`. Bez liter szkieletu w wartościach i w oryginale – bez przejść szkieletu
    (`ZbioryDokumentu.pelne`)."""
    return _zbiory_dokumentu(oryginal, wartosci, reguly, jezyk, leksykon, posrednie, z_szkieletem=False)


def _ma_znaki_szkieletu(teksty: Iterable[str]) -> bool:
    return any(ma_znaki_szkieletu(normalizuj(t)) for t in teksty)


def _zbiory_dokumentu(oryginal: Path, wartosci: list[Wartosc], reguly: RegulyWycieku | None, jezyk: str | None,
                      leksykon, posrednie: list[dict] | None, z_szkieletem: bool) -> ZbioryDokumentu:
    """`zbiory_dokumentu`; `z_szkieletem` – zawsze z przejściami szkieletu (`ZbioryDokumentu.pelne`)."""
    reguly = reguly or RegulyWycieku()
    orig = wydobadz(oryginal)
    if orig.status != "OK":
        raise ValueError(f"oryginał {Path(oryginal).name}: {orig.status} ({orig.blad})")
    # wartość z przeniesieniem („Kowal-\nski”) szukamy w postaci sklejonej (zob. docstring modułu)
    surowe = [w if polacz_przeniesienia(w.tekst) == w.tekst else dataclasses.replace(w, tekst=polacz_przeniesienia(w.tekst))
              for w in wartosci]
    zepsuty = warstwa_tekstowa_zepsuta(orig, surowe)
    # `Wartosc.id` może mieć kilka części (imię i nazwisko w osobnych komórkach, runy): unikalne są pary (id, tekst)
    uniq = list({(w.id, w.tekst): w for w in surowe}.values())
    jezyk = jezyk or jezyk_wartosci(uniq)
    jezyk_o = jezyk_ocr(uniq, jezyk)
    leks = _leksykon_dla(leksykon, jezyk)
    ob_all = [w for w in uniq if w.w_pikselach]
    ocr_osadzone = obrazy.ocr_wiele(orig.obrazy, jezyk_o)
    ocr_stron = ocr_stron_pliku(oryginal, orig, jezyk_o)
    wykr = obrazy.wykrywalne_obrazy(oryginal, surowe, jezyk_o, reguly, leks) if ob_all else set()
    niewykr = sorted(w.id for w in ob_all if w.id not in wykr)
    # OCR stron oryginału wchodzi do zbiorów tylko przy zepsutej warstwie tekstowej oryginału (własność dokumentu); w poczcie –
    # OCR stron tych PDF-ów załączników, których warstwa tekstowa jest zepsuta (jak samodzielny PDF)
    if orig.rodzaj in RODZAJE_POCZTY:
        zepsute = zepsute_pdfy_poczty(orig, surowe, ocr_stron)
        przedrostki = [p for p, _ in orig.pdfy]
        zepsuty = bool(zepsute)
        strony_zbiorow = [t for n, t in ocr_stron if _pdf_nazwy(n, przedrostki) in zepsute]
    else:
        strony_zbiorow = [t for _, t in ocr_stron] if zepsuty else []
    strony_pdf = orig.struktura.get("strony", 1) if orig.rodzaj == "pdf" else 1
    niejedn = niejednoznaczne(orig.czesci, [t for _, t in ocr_osadzone], surowe, strony_pdf, strony_zbiorow)
    # przejścia szkieletu (niejednoznaczność w szkielecie, wariant `tylko_cyrylica` wartości ASCII) zmieniają ocenę tylko tekstu
    # z literami szkieletu: bez nich w wartościach i w oryginale (części, OCR obrazów i stron; OCR bez danych `ukr` cyrylicy ani
    # greki nie zwraca) są pomijane, a `ocen_plik` dolicza je (`ZbioryDokumentu.pelne`), gdy litery szkieletu ma wynik
    lekko = not z_szkieletem and "uk" not in jezyk_o.split("+") and not (
        _ma_znaki_szkieletu(w.tekst for w in uniq) or _ma_znaki_szkieletu(c.caly_tekst() for c in orig.czesci)
        or _ma_znaki_szkieletu(t for _, t in ocr_osadzone + ocr_stron))
    # wariant złożony w szkielecie (homoglify): wartość, której postać złożona występuje w oryginale częściej niż gold, traci
    # ten wariant (ocena dokładna bez zmian) – ta sama reguła niejednoznaczności, liczona z oryginału
    niejedn_z = set() if lekko else niejednoznaczne(orig.czesci, [t for _, t in ocr_osadzone], surowe, strony_pdf,
                                                    strony_zbiorow, zloz=zloz_szkielet)
    oceniane = [w for w in uniq if w.id not in niejedn]
    gen = slowa_generyczne(orig.czesci, [t for _, t in ocr_osadzone] + strony_zbiorow, uniq) | _tokeny_wartosci(uniq, niejedn)
    leks_z = frozenset(zloz_szkielet(t) for t in leks)
    # niewykrywalne (OCR oryginału ich nie czyta) NIE są wyłączone z szukania w tekście: warstwa tekstowa, /Info itd.
    # szukamy ich dokładnie; pomijamy tylko wyszukiwanie w OCR wyniku
    bez_ocr = set(niewykr)

    def zbuduj_grupy(listy: Iterable[list[Wartosc]], gen: set[str], wszystkie: list[Wartosc]) -> list[_Grupa]:
        """Grupy (reguły wartości) przy słowach generycznych `gen`; `wszystkie` – wartości dokumentu (słownik OCR i ciągi
        alfanumeryczne innych wartości)."""
        gen_s = sorted(gen)
        gen_z = {zloz_szkielet(t) for t in gen}
        gen_zs = sorted(gen_z)
        # słowa zamienników – tylko w kontekście zamiennika, w samym tekście OCR (`maskuj_zamienniki`)
        slownik = frozenset(gen | {t for w in wszystkie for t in _tokeny(w.tekst)})
        slownik_z = frozenset(zloz_szkielet(t) for t in slownik)
        slownik_szumu = frozenset(zloz_diakrytyki(t) for t in slownik)       # `_bez_szumu`: bez znaków diakrytycznych
        inne_alnum = frozenset(a for w in wszystkie if len(a := same_alnum(w.tekst)) >= MIN_DL_ID)
        inne_alnum_z = frozenset(a for w in wszystkie if len(a := same_alnum(zloz_szkielet(normalizuj(w.tekst)))) >= MIN_DL_ID)
        # części wspólne identyfikatorów z etykietą (`_czesci_id`): teksty wartości o ≥ `MIN_DL_ID` znakach alfanumerycznych
        inne_teksty = frozenset(normalizuj(w.tekst) for w in wszystkie if len(same_alnum(w.tekst)) >= MIN_DL_ID)
        inne_teksty_z = frozenset(t for w in wszystkie if len(same_alnum(t := zloz_szkielet(normalizuj(w.tekst)))) >= MIN_DL_ID)
        grupy: list[_Grupa] = []
        for ws in listy:
            w0 = ws[0]
            reg = zbuduj_regule(w0, reguly, gen, gen_s, ocr=False, leksykon=leks, jezyk=jezyk, inne_alnum=inne_alnum,
                                inne_teksty=inne_teksty)
            if not reg.moze_wyciec:
                continue
            norm0 = normalizuj(w0.tekst)
            # homoglify: litery cyrylicy mylące z łacińskimi (szkielet zmienia zapis wartości)
            zmieniony = szkielet(norm0) != norm0
            nieascii = any(not t.isascii() for t in reg.tokeny) and not reg.id_wzorce
            # wariant złożony: wartość z diakrytykami (jak dotąd, bez warunku niejednoznaczności) albo z homoglifami – zawsze;
            # pozostałe – tylko na tekstach z cyrylicą mylącą (`Regula.tylko_cyrylica`); wariant w szkielecie jest wyłączony,
            # gdy postać złożona wartości jest niejednoznaczna w oryginale (`niejedn_z`)
            tylko_cyr = not (nieascii or zmieniony)
            wariant = (nieascii and not zmieniony) or not (lekko or any(w.id in niejedn_z for w in ws))

            def zl(r: bool) -> Regula | None:
                if not wariant:
                    return None
                reg_z = zbuduj_regule(dataclasses.replace(w0, tekst=zloz_szkielet(norm0)), reguly, gen_z, gen_zs, ocr=r,
                                      leksykon=leks_z, jezyk=jezyk, slownik=slownik_z, inne_alnum=inne_alnum_z,
                                      inne_teksty=inne_teksty_z)
                return dataclasses.replace(reg_z, tylko_cyrylica=tylko_cyr) if reg_z.moze_wyciec else None
            grupy.append(_Grupa(sorted({w.id: w for w in ws}.values(), key=lambda x: x.id), reg, zl(False),
                                zbuduj_regule(w0, reguly, gen, gen_s, ocr=True, leksykon=leks, jezyk=jezyk, slownik=slownik,
                                              inne_alnum=inne_alnum, inne_teksty=inne_teksty),
                                zl(True), any(w.id not in bez_ocr for w in ws), zmieniony, slownik=slownik_szumu))
        return grupy

    surowe_grupy: dict[tuple[str, bool], list[Wartosc]] = {}
    for w in oceniane:
        surowe_grupy.setdefault((normalizuj(w.tekst), w.w_pikselach), []).append(w)   # obraz i tekst: osobne krotności
    grupy = zbuduj_grupy(surowe_grupy.values(), gen, uniq)

    # Linia bazowa: te same reguły na ORYGINALE (kopia bez zmian). Ocenianym mianownikiem są wartości, które sędzia w ogóle
    # odnajduje w oryginale (albo wyciekły w wyniku) – więc kopia oryginału wycieka 100 % ocenianych, symetrycznie dla
    # wszystkich uczestników (niewykrywalne w OCR, niejednoznaczne i niedopasowywalne wartości nie zaniżają miary).
    zrodlo = _Zrodlo(oryginal, orig, jezyk_o)
    # szablon formatu (części strukturalne) – poza linią bazową
    wid = dataclasses.replace(_widoki(orig, ocr_osadzone, ocr_stron, {}, zrodlo), strukt=[])
    # części identyfikatorów obecne w oryginale także poza gold (cytat innej sprawy – J1-fix3, I1): krotność z oryginału
    grupy = _z_czesciami_spoza_gold(grupy, wid, surowe, strony_pdf)
    oceny = {i: _ocen_grupe(g, wid, {}) for i, g in enumerate(grupy)}
    # drugi odczyt obrazów osadzonych z trafieniem bez potwierdzenia
    wid = _drugi_odczyt_obrazow(wid, ocr_osadzone, orig.obrazy, jezyk_o, oceny, lambda i, w: _ocen_grupe(grupy[i], w, {}))
    # drugi odczyt stron oryginału: wartości, których odczyt `RENDER_DPI` nie znalazł na stronach (albo nie wszystkie wystąpienia)
    # i wartości z trafieniem częściowym bez potwierdzenia (potwierdza je drugi odczyt)
    drugi = {i for i, g in enumerate(grupy) if wid.strony
             and (oceny[i][2] or _ile_w_ocr(g.reg_ocr, g.reg_ocr_z, wid.strony[0], g.reg) < len(g.wartosci))}
    if drugi:
        wid_2 = dataclasses.replace(wid, strony=[*wid.strony, _odczyt_stron(zrodlo, drugi=True)])
        oceny.update({i: _ocen_grupe(grupy[i], wid_2, {}) for i in drugi})
        # trzeci odczyt (300 dpi psm 6): trafienie nadal bez potwierdzenia – blok czytany tylko przez psm 6 (`_trafienia_ocr`)
        trzeci = {i for i in drugi if oceny[i][2]}
        if trzeci:
            wid_3 = dataclasses.replace(wid_2, strony=[*wid_2.strony, _odczyt_stron(zrodlo, trzeci=True)])
            oceny.update({i: _ocen_grupe(grupy[i], wid_3, {}) for i in trzeci})
    bazowe: set[str] = set()
    for i, (najl, ile, *_) in oceny.items():
        if najl:
            bazowe.update(w.id for w in grupy[i].wartosci[:ile])
    # wykrywalność w OCR oryginału = te same warunki potwierdzenia co wyciek (J3): wartość obrazowa, którą `wykrywalne_obrazy`
    # przyjmuje z jednego odczytu (np. samo trafienie rozmyte), a linia bazowa – z potwierdzeniem jak w ocenie wyniku – w oryginale
    # nie odnajduje, jest niewykrywalna dla wszystkich (bez szukania w OCR wyniku; inaczej byłaby oceniana, ale nie mogłaby
    # wyciec nawet z kopii oryginału). Grupa częściowo odnaleziona (krotność) – bez zmian.
    dopisane = {w.id for g in grupy if g.ocr and g.wartosci[0].w_pikselach and not any(w.id in bazowe for w in g.wartosci)
                for w in g.wartosci if w.id not in bez_ocr}
    if dopisane:
        bez_ocr |= dopisane
        niewykr = sorted(bez_ocr)
        grupy = [dataclasses.replace(g, ocr=False) if any(w.id in dopisane for w in g.wartosci) else g for g in grupy]
    zb = ZbioryDokumentu(orig, zepsuty, jezyk_o, oceniane, uniq, niewykr, niejedn, frozenset(gen), frozenset(bazowe), grupy,
                         {c.nazwa: Tekst(c.caly_tekst()) for c in orig.czesci if c.strukturalna},
                         pelne=(lambda: _zbiory_dokumentu(oryginal, wartosci, reguly, jezyk, leksykon, posrednie,
                                                          z_szkieletem=True)) if lekko else None)
    if posrednie:
        # identyfikacja pośrednia: składniki – osobne grupy (po jednej wartości), słowa generyczne bez wystąpień gold i składników;
        # linia bazowa składników = widoczne („pelny”) w oryginale, tymi samymi odczytami co gold
        skl = wartosci_skladnikow(posrednie, uniq, jezyk)
        odc, rdzenie = wartosci_rdzeni(posrednie, uniq, jezyk)
        gen_skl = slowa_generyczne(orig.czesci, [t for _, t in ocr_osadzone] + strony_zbiorow, uniq + skl) \
            | _tokeny_wartosci(uniq, niejedn)
        grupy_skl = zbuduj_grupy([[w] for w in skl + odc], gen_skl, uniq + skl)
        wid_s = dataclasses.replace(_widoki(orig, ocr_osadzone, ocr_stron, {}, zrodlo), strukt=[])
        oceny_s = _ocen_z_odczytami(grupy_skl, wid_s, oryginal, orig, ocr_osadzone, jezyk_o, {},
                                    lambda i, o: not _pelny(o))
        widoczne = {grupy_skl[i].wartosci[0].id for i, o in oceny_s.items() if _pelny(o)}
        # odcinek rdzenia: może wyciec (ma grupę), widoczny w oryginale i jego pełna wartość jest w tekście oryginału raz
        pewne = {g.wartosci[0].id for g in grupy_skl if _ile_wystapien(g.reg, wid_s.do_liczenia) == 1}
        zb = dataclasses.replace(zb, kombinacje=list(posrednie), skladniki=grupy_skl, skladniki_bazowe=frozenset(widoczne),
                                 rdzenie={sid: ids for sid, ids in rdzenie.items()
                                          if all(i in widoczne and i in pewne for i in ids)})
    return zb


def ocen_plik(oryginal: Path, wynik: Path, wartosci: list[Wartosc], reguly: RegulyWycieku | None = None,
              jezyk: str | None = None, *, leksykon, posrednie: list[dict] | None = None) -> OcenaPliku:
    """Ocenia plik `wynik` względem `oryginal` i gold `wartosci` (zob. docstring modułu).

    `wartosci` może powtarzać `id` (jedno `Wartosc` na wystąpienie, np. nagłówek biegnący na każdej stronie skanu);
    krotność służy do wykrywania wartości niejednoznacznych, wynik jest po unikalnych `id`. Każda wartość jest
    szukana w KAŻDEJ części tekstowej wyniku, w OCR KAŻDEGO obrazu wyniku i – dla PDF – w OCR KAŻDEJ strony wyniku (OCR – z
    tolerancją). Zbiory dokumentu (`zbiory_dokumentu`) zależą tylko od oryginału. `jezyk` – język OCR (domyślnie najczęstszy
    w `wartosci`); `leksykon` (WYMAGANY, bez domyślnej wartości – żeby nikt nie zapomniał go podłączyć) –
    `zbuduj_leksykon(manifest)`/`leksykon_z_manifestu(ścieżka)` (słownik język → tokeny), zbiór tokenów albo `{}` świadomie
    bez leksykonu korpusu. `posrednie` – pole manifestu z kombinacjami identyfikacji pośredniej (wynik w `OcenaPliku.posrednie`,
    poza `wycieki`). Błąd odczytu ORYGINAŁU to `ValueError` (uszkodzony korpus, nie wynik uczestnika)."""
    zb = zbiory_dokumentu(oryginal, wartosci, reguly, jezyk, leksykon=leksykon, posrednie=posrednie)
    orig = zb.orig
    wyn = wydobadz(wynik)
    ocr_stron = ocr_stron_pliku(wynik, wyn, zb.jezyk_ocr) if wyn.status in ("OK", "PUSTY") else []
    if wyn.status == "PUSTY" and any(ch.isalnum() for _, t in ocr_stron for ch in t):
        # PDF bez warstwy tekstowej i bez obrazów osadzonych (strona jako obraz inline, tekst jako ścieżki), na którego
        # stronach widać tekst – to nie jest plik pusty
        wyn = dataclasses.replace(wyn, status="OK", blad=None)

    integralnosc: dict = {"otwiera_sie": wyn.status == "OK", "blad": wyn.blad, "format": orig.rodzaj,
                          "format_zgodny": wyn.rodzaj == orig.rodzaj,
                          "struktura": {"oryginal": dict(orig.struktura), "wynik": dict(wyn.struktura)},
                          "zachowanie_struktury": 0.0, "spojnosc": None,
                          "encje": {"ocenione": 0, "spojne": 0, "pominiete": 0, "niezamaskowane": 0}}
    if wyn.status != "OK":
        return OcenaPliku(wyn.status, [], integralnosc, zb.niewykrywalne, sorted(zb.niejednoznaczne), 0, sorted(zb.bazowe))

    ocr_osadzone = obrazy.ocr_wiele(wyn.obrazy, zb.jezyk_ocr)
    if zb.pelne is not None and (_ma_znaki_szkieletu(c.caly_tekst() for c in wyn.czesci)
                                 or _ma_znaki_szkieletu(t for _, t in ocr_osadzone + ocr_stron)):
        zb = zb.pelne()                     # wynik z literami szkieletu: zbiory z przejściami szkieletu (docstring modułu, pkt 6)
    zrodlo = _Zrodlo(wynik, wyn, zb.jezyk_ocr)
    wid = _widoki(wyn, ocr_osadzone, ocr_stron, {}, zrodlo)
    oceny = {i: _ocen_grupe(g, wid, zb.orig_strukt) for i, g in enumerate(zb.grupy)}
    # drugi odczyt obrazów osadzonych z trafieniem bez potwierdzenia – jak dla oryginału w `zbiory_dokumentu`
    wid = _drugi_odczyt_obrazow(wid, ocr_osadzone, wyn.obrazy, zb.jezyk_ocr, oceny,
                                lambda i, w: _ocen_grupe(zb.grupy[i], w, zb.orig_strukt))
    # drugi odczyt stron wyniku: grupy z wartościami linii bazowej, które nie wyciekły w odczycie `RENDER_DPI`, i grupy z trafieniem
    # częściowym bez potwierdzenia (potwierdza je drugi odczyt)
    wyciekle = {w.id for i, (najl, ile, *_) in oceny.items() if najl for w in zb.grupy[i].wartosci[:ile]}
    drugi = [i for i, g in enumerate(zb.grupy)
             if oceny[i][2] or any(w.id in zb.bazowe and w.id not in wyciekle for w in g.wartosci)]
    if drugi and ocr_stron:
        strony_2 = _odczyt_stron(zrodlo, drugi=True)
        wid_2 = dataclasses.replace(wid, strony=[*wid.strony, strony_2])
        oceny.update({i: _ocen_grupe(zb.grupy[i], wid_2, zb.orig_strukt) for i in drugi})
        # trzeci odczyt (300 dpi psm 6) – jak dla oryginału w `zbiory_dokumentu`
        trzeci = [i for i in drugi if oceny[i][2]]
        if trzeci:
            strony_3 = _odczyt_stron(zrodlo, trzeci=True)
            wid_3 = dataclasses.replace(wid_2, strony=[*wid_2.strony, strony_3])
            oceny.update({i: _ocen_grupe(zb.grupy[i], wid_3, zb.orig_strukt) for i in trzeci})

    wycieki: list[tuple[str, str, str, str]] = []
    for i, (najl, ile, *_) in oceny.items():
        if najl:
            wycieki += [(w.id, w.kategoria, najl[0], najl[1]) for w in zb.grupy[i].wartosci[:ile]]
    porzadek: dict[str, int] = {}
    for i, w in enumerate(zb.uniq):
        porzadek.setdefault(w.id, i)
    wycieki.sort(key=lambda x: (porzadek[x[0]], x[3] != "pelny"))
    unikalne: dict[str, tuple[str, str, str, str]] = {}
    for x in wycieki:                       # jedna pozycja na `id`, choćby wyciekło kilka jego części
        unikalne.setdefault(x[0], x)
    wycieki = list(unikalne.values())
    ocenione = len(zb.bazowe | {x[0] for x in wycieki})

    # format zamieniony na odpowiednik (.doc→.docx, .msg→.txt): liczniki nieporównywalne – „nie dotyczy” (None), nie 0
    integralnosc["zachowanie_struktury"] = _zachowanie(orig.struktura, wyn.struktura) if integralnosc["format_zgodny"] else None
    sp = spojnosc(orig, wyn, zb.oceniane)
    integralnosc["spojnosc"] = sp.pop("spojnosc")
    integralnosc["encje"] = sp
    return OcenaPliku("OK", wycieki, integralnosc, zb.niewykrywalne, sorted(zb.niejednoznaczne), ocenione, sorted(zb.bazowe),
                      _ocen_kombinacje(zb, wynik, wyn, ocr_osadzone, ocr_stron) if posrednie is not None else None,
                      nadmiarowe(orig, wyn, wartosci, ocr_stron))


def _ocen_kombinacje(zb: ZbioryDokumentu, wynik: Path, wyn: Wydobycie, ocr_osadzone: list[tuple[str, str]],
                     ocr_stron: list[tuple[str, str]]) -> list[dict]:
    """Kombinacje identyfikacji pośredniej w wyniku (docstring modułu): składnik widoczny = trafienie „pelny” jego grupy albo
    wszystkich odcinków jego rdzenia (`ZbioryDokumentu.rdzenie`); strony czytane ponownie dla składników i odcinków linii
    bazowej niewidocznych w pierwszym odczycie (jak gold)."""
    widoczne: set[str] = set()
    if zb.skladniki:
        wid = _widoki(wyn, ocr_osadzone, ocr_stron, {}, _Zrodlo(wynik, wyn, zb.jezyk_ocr))
        oceny = _ocen_z_odczytami(zb.skladniki, wid, wynik, wyn, ocr_osadzone, zb.jezyk_ocr, zb.orig_strukt,
                                  lambda i, o: zb.skladniki[i].wartosci[0].id in zb.skladniki_bazowe and not _pelny(o))
        widoczne = {zb.skladniki[i].wartosci[0].id for i, o in oceny.items() if _pelny(o)}
        widoczne |= {sid for sid, ids in zb.rdzenie.items() if all(i in widoczne for i in ids)}
    wynik_k = []
    for k in zb.kombinacje:
        ids = [s["id"] for s in k["skladniki"]]
        oceniona = all(i in zb.skladniki_bazowe for i in ids)
        wynik_k.append(_posrednie.ocena_kombinacji(k, (not all(i in widoczne for i in ids)) if oceniona else None,
                                                   [i for i in ids if i in widoczne]))
    return wynik_k
