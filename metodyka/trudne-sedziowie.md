# Sędziowie warstwy trudnych przypadków – reguły dodane w H6a

Reguły poniżej dotyczą WSZYSTKICH uczestników tak samo (sędziowie nie wiedzą, kto jest oceniany). Na trzonie korpusu (dokumenty
bez cyrylicy, greki i inicjałów) nie zmieniają żadnego wyniku: szkielet jest tam tożsamością, a trzon nie ma wartości `INICJALY`
(test regresji `tests/test_h6a.py::test_trzon_wyniki_sedziego_bez_zmian` – stała próbka trzonu: migawka bez OCR zapisana sędzią
bez tych reguł, migawka z OCR – z nimi; `tests/dane_testowe/sedzia_trzon_*.json`). Wagi i wzory
punktów (`punktacja.md`) się nie zmieniają.

## Homoglify – porównanie po szkielecie

Wartość zapisana homoglifami (łacińskie „Kowalski” z cyrylicznymi „К”, „о” – `pbench.homoglify`) wygląda dla czytelnika tak samo
jak zapis łaciński. Uczestnik, który „naprawi” homoglify (zamieni cyrylicę na łacinę), ale wartości nie zamaskuje, zostawia ją
w wyniku – to wyciek.

* **Szkielet** (`pbench/sedzia/normalizacja.py`, `SZKIELET_CYR_LAC`, `SZKIELET_GR_LAC`): litery cyrylicy i greki o kształcie liter
  łacińskich sprowadzone do łaciny. Źródło tablic: Unicode Technical Standard #39, plik `confusables.txt` (pary Cyrillic → Latin
  i Greek → Latin, tylko litera ↔ litera) – litery alfabetu ukraińskiego, litery, które wstawia generator homoglifów, i litery
  alfabetu greckiego („Κοwalski” z greckimi „Κ”, „ο” = „Kowalski”). Sędziowie nie rozróżniają wielkości liter (porównanie po
  casefold), więc pary mylone tylko jako wielkie litery (В/B, Н/H, К/K, М/M, Т/T; Β/B, Η/H, Κ/K, Μ/M, Τ/T…) są w tablicy zapisane
  małymi. Gdy mała i wielka litera grecka wyglądają jak dwie różne litery łacińskie, obowiązuje odpowiednik małej litery z UTS #39
  („ν” = „v”, więc wielkie „Ν” udające „N” nie jest wykrywane); sigma księżycowa „ϲ” (NFKC: „σ” = „o”) – też poza zakresem.
  Generator warstwy trudnej wstawia wyłącznie cyrylicę; inne pisma (np. ormiańskie, Cherokee) – poza zakresem.
* **Sędzia plikowy**: obok porównania dokładnego wartość jest porównywana w postaci złożonej – szkielet bez znaków diakrytycznych –
  z tekstem wyniku w tej samej postaci. Wartość gold z homoglifami wycieka, gdy wynik zawiera ją w zapisie oryginalnym ALBO po
  „naprawie” na łacinę (także po zdjęciu diakrytyków); wartość cyrylicka z wmieszaną łaciną – także po „naprawie” na cyrylicę.
  Kierunek odwrotny – wartość łacińska, której litery wynik zastąpił cyrylicą o tym samym kształcie – też jest wyciekiem
  (porównanie w szkielecie, tylko na tekstach wyniku z cyrylicą albo greką mylącą). Gdy liter szkieletu nie ma ani w wartościach,
  ani w oryginale, ani w wyniku, przejścia szkieletu są pomijane – wynik jest ten sam, sędzia szybszy (trzon). Na tekście
  z literami szkieletu trafienie pełne w szkielecie ma pierwszeństwo przed częściowym dokładnym („Jan Κοwalski”: „Jan” dokładnie,
  nazwisko w szkielecie – wyciek pełny, nie częściowy); na tekście bez nich – jak bez szkieletu.
* **Ten sam człowiek w zapisie zwykłym i z homoglifami** – dwie wartości gold o tym samym szkielecie trafiają się nawzajem:
  uczestnik, który zamaskuje tylko „Jan Kowalski”, a zostawi „Jаn Kоwalski” (albo odwrotnie), ma wyciek OBU wartości. To zawyża
  liczbę wycieków na poziomie wartości (miara opisowa), nie na poziomie dokumentu ani encji – dokument i tak ma wyciek tej osoby.
* **Transliteracja zrobiona przez uczestnika nie jest wyciekiem** (sędzia plikowy): wynik „Olena Kovalenko” w miejscu gold
  „Олена Коваленко” nie trafia ani dokładnie, ani w szkielecie (szkielet sprowadza tylko litery o tym samym kształcie, nie
  transliteruje). To ta sama konwencja „liczy się zapis z dokumentu” co przy identyfikacji pośredniej („przeformatowanie ≠
  wyciek”, `posrednie.md`) – i symetryczna: żaden uczestnik nie jest karany ani nagradzany za przepisanie wartości na inne
  pismo. Zapis transliterowany obecny w ORYGINALE jest osobną wartością gold i wycieka normalnie.
* **Zbiory dokumentu tą samą regułą z oryginału** (wspólne dla wszystkich uczestników): słowa generyczne, leksykon i słownik OCR
  wariantu – w postaci złożonej; wartość, której postać złożona występuje w oryginale częściej niż wystąpień gold (np. wartość
  „Kоwalski” z homoglifem i nazwa sprawy „Kowalski” w cytacie orzeczenia – nie gold), traci porównanie po szkielecie (porównanie
  dokładne zostaje) – inaczej pozostawione przez KAŻDEGO uczestnika słowo spoza gold liczyłoby się jako wyciek; krotność wartości
  z homoglifami (kilka `id`) liczona jest także w postaci złożonej. Mianownik (linia bazowa) – te same reguły na kopii oryginału.
* **Sędzia tekstowy** ocenia pokrycie offsetów tekstu oryginalnego: zapis wartości (homoglify, transliteracja) nie wymaga porównania
  napisów. Uczestnik „normalizujący” homoglify u siebie, który nie oznaczy znaków wartości, ma wyciek; uczestnik, który je oznaczy,
  nie ma – niezależnie od tego, jak je wewnętrznie zapisał.

## Transliteracje – poziom encji (miara opisowa)

Każdy zapis osoby (cyrylica, każda transliteracja, homoglify, inicjały, formy odmienione) pozostaje **osobną wartością gold** – tak
liczą się wycieki wartości i wszystkie wzory punktów. `punktacja.md` przesądza o tym jednoznacznie: T3 i P3 to średnia po
przypadkach z odsetka **dokumentów** z wyciekiem (dokument z jakimkolwiek wyciekiem – niezależnie od tego, czy liczyć wartości, czy
encje – jest dokumentem z wyciekiem), a T2/P2 (ważenie po wartościach) liczy się na trzonie. Poziom encji jest więc wyłącznie
**miarą opisową**:

* rekord oceny (`pbench.ocen`, oba poziomy) dokumentu, którego gold ma pole `encja`, ma pola `wycieki_encji` (encje z co najmniej
  jednym wyciekłym zapisem – **encja wycieka, gdy wycieka którykolwiek jej zapis**) i `encje_ocenione` (encje z co najmniej jedną
  ocenianą wartością); wartość bez `encja` jest encją samą dla siebie;
* raport może pokazać odsetek encji z wyciekiem obok odsetka wartości – np. uczestnik, który maskuje zapis cyrylicki, a zostawia
  transliterację, ma wyciek encji, choć „większość wartości” jest zamaskowana.

## Inicjały (parafy, „Pan K.”)

Orzeczenie kontrolera do H2 – inicjały muszą móc wyciec, inaczej przypadki `parafy` i `skroty_po_pelnym` byłyby puste dla T3/P3:

* **Sędzia tekstowy**: `INICJALY` jak identyfikator – ciąg znaków alfanumerycznych spanu (kropki i spacje pomijane), próg =
  długość, czyli wyciek, gdy wszystkie litery inicjałów są odsłonięte („J.K.” z pokrytym „K” nie wycieka; „K.” po „Pan” bez
  pokrycia – wycieka).
* **Sędzia plikowy**: dokładny wzorzec inicjałów z granicami (`normalizacja.wzor_inicjalow`): litery i kropki jak w wartości,
  dowolne spacje po kropce, przed i po wzorcu nie ma litery ani cyfry – „J.K.” trafia „J. K.”, nie trafia „J.K.M.”; „JK” nie trafia
  „AJK” ani „JKL”; „K.” nie trafia „k.c.”. Także na tekście OCR – bez dopasowań rozmytych (pojedyncze litery czytane rozmyto
  trafiałyby wszędzie). Wartość niejednoznaczna (wzorzec występuje w treści oryginału częściej niż w tekstach wartości gold) jest
  wyłączona z oceny wszystkich uczestników; trafienia wzorca wewnątrz innych wartości gold (np. „K.” w „J.K.” tej samej osoby)
  liczą się jako wystąpienia gold.
* **OCR (strony PDF, obrazy osadzone)**: wzorzec 1–3 liter trafia szum OCR – gwiazdki maskowania („**”) czytane jako „… ar …”
  dałyby wyciek parafy „ar” uczestnikowi, który zamaskował wszystko (`h-pf-es-pismo_z_parafami-0003`), zależnie od stylu
  maskowania, nie od wycieku. Dlatego:
  * trafienie wzorca inicjałów w OCR liczy się tylko z potwierdzeniem – wzorzec trafia w co najmniej dwóch odczytach tej samej
    strony albo obrazu (inna rozdzielczość albo inny tryb Tesseracta); bez potwierdzenia strona/obraz dostaje kolejne odczyty
    (400 dpi psm 3 i 6, 300 dpi psm 6), jak dla innych wartości;
  * samo potwierdzenie nie wystarcza: szum z tych samych pikseli powtarza się w KAŻDYM odczycie (gwiazdki czytane jako „ar” w 300
    i 400 dpi, psm 3 i 6; czarne pole redakcji rastrowej na miejscu „R.S.” czytane jako „rs”, pola na każdy znak „J.E.” – jako „jm”).
    Dlatego trzy reguły dodatkowe:
    * **strony z warstwą tekstową** (`plik._strony_z_warstwa`: część `pdf:strona N` ma litery albo cyfry i nie ma znaków
      sterujących) – inicjały czyta OCR renderu strony **bez obiektów tekstowych** (PDFium: tekst w trybie niewidocznym, także
      w XObject-ach formularzy; `ekstrakcja.renderuj_strony(bez_tekstu=True)`). Tekst strony ocenia warstwa (dokładna), a w renderze
      zostają tylko piksele spoza niej – parafa wklejona jako obraz inline `BI … EI` albo XObject, ścieżki; szum z zamaskowanego
      tekstu (gwiazdki) znika. Strona bez warstwy (raster, tekst jako ścieżki, znaki bez mapy ToUnicode) – render pełny;
    * **odczyt bez pól zamalowanych** – trafienie inicjałów w pikselach (strona albo obraz osadzony) liczy się tylko, gdy wzorzec
      jest też w odczycie tego samego obrazu z wybielonymi polami zamalowanymi (`obrazy.bez_pol`, `plik._po_wybieleniu`). Pole
      zamalowane = piksele ciemniejsze niż `PROG_CIEMNEGO_POLA` = 100 (jasność 0–255), w które mieści się kwadrat
      `BOK_POLA_PX` = 15 px obrazu czytanego przez OCR (≈ 1,3 mm w 300 dpi; otwarcie morfologiczne), razem z krawędzią
      `MARGINES_POLA_PX` = 3 px; w małym obrazie osadzonym pole liczy się w pikselach obrazu źródłowego, **przed** powiększeniem do OCR.
      Pociągnięcia pisma do ok. 14 pt przy ≤ 400 dpi – także pogrubionego i kolorowego – są cieńsze i zostają. Ryzyko resztkowe:
      pismo pogrubione od 24 pt przy 300 dpi (18 pt przy 400 dpi, 12 pt przy 600 dpi; zwykłe 36 pt przy 300 dpi) i grube pismo
      markerem bywa wybielane, więc takie trafienie nie zostaje potwierdzone; podobnie jasne pismo na ciemnym tle albo strona
      ciemna w całości (odczyt po wybieleniu pusty). Żaden generator ani uczestnik tak nie rysuje. Odczyty bez pól są
      leniwe (tylko dla trafień inicjałów, kolejny tylko, gdy poprzedni nie trafia) i mają osobne klucze pamięci podręcznej OCR;
    * **wiersze szumu w obrazach osadzonych** – w odczytach OCR obrazów osadzonych (także bez pól; strony PDF – bez tego warunku)
      pomijany jest wiersz, który ma co najmniej `MIN_SLOW_SZUMU` = 4 tokeny szumu – ≥ `MIN_DL_SLOWA_SZUMU` = 3 liter, zapisane
      samymi wielkimi literami, nie z jednej powtórzonej litery – złożone łącznie z najwyżej `MAKS_LITER_SZUMU` = 8 różnych liter,
      a żaden token literowy wiersza ≥ 3 liter nie jest słowem dokumentu
      (słowem oryginału – części i OCR jego obrazów – albo tokenem wartości gold; porównanie bez znaków diakrytycznych po obu
      stronach, bo OCR je gubi: „RUBRICA” = „Rúbrica”; `plik._bez_szumu`). Znak maskujący powtórzony w obrazie osadzonym (logo
      zastąpione wierszem gwiazdek – obraz nie ma warstwy tekstowej, więc render bez tekstu go nie usuwa) OCR czyta w każdym
      odczycie, w każdej skali i po wybieleniu jako ten sam ciąg wielkich liter (`A ARAHAL AC AE … ERRE ERE ARRE RR AR`), w którym
      wzorzec „ar” trafia przypadkowo; jego tokeny szumu mają w każdym odczycie (pierwszym, bez pól, drugim w skali ×2) 5–6
      różnych liter. Wiersz z prawdziwą parafą szumem nie jest: ma etykietę z tekstu dokumentu („Referencia: ar/jc”, „Elaborado
      por: A.R.”), jest krótki (sama parafa we wycinku), ma słowa pisane zwykle (zamienniki uczestnika „Martínez Herrera Abogados
      Asociados A.R.”), słowa wielkimi literami o wielu różnych literach („MARTÍNEZ HERRERA ABOGADOS ASOCIADOS A.R.” – 15 liter
      w każdym odczycie) albo maskę z jednej litery („XXXX XXXXX XXXXX XXXX A.R.”) – trzy ostatnie przypadki sprawdza `test_parafa_w_pikselach_obok_maski_i_zamiennikow_wycieka` (obraz osadzony DOCX i strona zrasteryzowana
      PDF). Na stronach PDF reguła nie działa: szum zamaskowanego tekstu usuwa tam render bez tekstu, a na stronie
      zrasteryzowanej parafę czyta OCR strony bez dodatkowego warunku (to samo trafienie w obrazie strony liczy się wtedy
      z odczytu strony). Pozostałe wiersze odczytu łączy separator niebędący białym znakiem ani literą, więc usunięty wiersz
      między „J.” a „K.” nie tworzy wzorca „J.K.” (sąsiednie wiersze zostawione łączy zwykły koniec wiersza, jak w odczycie). Pewność słowa Tesseracta (`conf`) szumu nie rozróżnia: „AR” w szumie gwiazdek
      ma 57, a prawdziwe parafy w kolorowej pieczątce albo we wycinku – 6–51. Ryzyko resztkowe (jednakowo dla wszystkich):
      parafa w obrazie osadzonym (nie na stronie PDF) w wierszu z co najmniej czterema słowami WIELKIMI LITERAMI spoza oryginału,
      złożonymi łącznie z najwyżej ośmiu różnych liter (np. „ANNA ANA ARENA SARA A.R.”), nie jest liczona; w generatorze `parafy` każda
      parafa stoi przy etykiecie szablonu (oznaczenie pisma, margines, stopka). Słowo dokumentu przeczytane przypadkiem w szumie
      wyłącza regułę dla tego wiersza (sędzia liczy wtedy trafienie jak bez niej). Krotność (`_ile_w_ocr`) liczona jest
      z odczytów bez tego warunku, jak przy odczycie bez pól.
  * Pomiar walidacyjny reguł na dokumentach generatora `parafy` (PDF, 14 dokumentów × 6 wartości `INICJALY`; każdy wynik
    zamaskowany w całości, redakcja rastrowa 200 dpi). Kolumny: „bez reguł dodatkowych” – samo potwierdzenie innym odczytem,
    a OCR inicjałów tylko na stronach bez warstwy tekstowej; „render bez tekstu + odczyt bez pól” – dwie pierwsze reguły
    dodatkowe (pomiar bez reguły wierszy szumu; ją sprawdzają testy niżej):
    | styl wyniku | bez reguł dodatkowych | render bez tekstu + odczyt bez pól |
    |---|---|---|
    | czarne pole na wystąpienie (raster) | 1/14 dokumentów | 0/14 |
    | to samo + niewidoczna warstwa wyniku nawiasowego | 0/14 | 0/14 |
    | czarne pole na każdy znak (raster) | 1/14 | 0/14 |
    | to samo + niewidoczna warstwa | 1/14 | 0/14 |
    | gwiazdki / nawiasy „[INICJALY_n]” / „XXX” (raster) | 0/14 / 0/14 / 0/14 | 0/14 / 0/14 / 0/14 |
    Fałszywe wycieki inicjałów: 3/56 wyników z czarnymi polami → 0/56 (0 z 336 wartości). Prawdziwe parafy w kopii
    zrasteryzowanej tych samych 14 dokumentów – 82/84 wartości w obu kolumnach (te same dwie straty, błędy odczytu OCR „I.T.” → „1.t.”,
    „/CK/” → „ick/” – ograniczenie niżej). Parafy w kolorowych pieczątkach (niebieski tusz, ramka i jasne wypełnienie albo
    czerwona ramka na białym tle; `test_pdf_parafa_w_kolorowej_pieczatce_wycieka`, `h-pf-en-pismo_z_parafami-0002`): wyciekają
    te same z warunkiem odczytu bez pól i bez niego – 5/6, w tym obie parafy z kropkami („E.L.”, „D.R.”); „bb” w pieczątce nie
    czyta żaden odczyt (ramka tuż przy znakach utrudnia sam OCR), w żadnym odczycie wybielanie nie zabrało trafienia. Parafa
    zostawiona tylko w pikselach strony z warstwą tekstową (`test_pdf_parafa_tylko_w_pikselach_strony_z_warstwa_wycieka`,
    `h-pf-es-pismo_z_parafami-0003`: „A.R.”, „ar”, „jc”, „II” ×2, „I.I.”; wynik nawiasowy z wklejonym wycinkiem rastra oryginału):
    obraz inline i mały XObject – wyciekają wszystkie trzy czytelne parafy i jedna z dwóch „II” (4/6; „I.I.” i druga „II” – niżej,
    ograniczenie parafy z samych „I”); bez OCR stron (sam OCR obrazów osadzonych) – obraz inline 0/6 (nie jest obrazem osadzonym),
    mały XObject 2/6 („A.R.”, „ar”: małe wycinki OCR obrazów osadzonych czyta gorzej niż OCR strony); render oryginału bez tekstu
    – 0 trafień wzorca. Uczestnik maskujący gwiazdkami w tym dokumencie (tekst i logo – obraz osadzony – zamaskowane;
    `test_pdf_parafy_gwiazdki_bez_falszywych_wyciekow_raster_wycieka`) – 0 wycieków z regułą wierszy szumu (bez niej – fałszywy
    wyciek „ar” z OCR logo), a kopia zrasteryzowana – wszystkie czytelne parafy; testy parafy tylko w pikselach, kolorowej
    pieczątki, czarnych pól i małego obrazu osadzonego dają z regułą wierszy szumu te same wyniki.
  * Ograniczenia i ryzyko resztkowe (jednakowo dla wszystkich uczestników):
    * **parafy złożone z samych „I”** („II”, „I.I.”) to same pionowe kreski – OCR myli je z „l”, „1”, „|” i w pikselach czyta je
      przypadkowo albo wcale (w `h-pf-es-pismo_z_parafami-0003` jedna z dwóch „II” wycieka z wycinka, druga i „I.I.” – nie), a dwie
      identyczne wartości sędzia numeruje kolejno, więc drugiej nie potwierdza; w pikselach takie parafy praktycznie nie są
      wykrywane (testy liczą parafy czytelne – z literą inną niż „I”, `_czytelne_parafy`). W warstwie tekstowej – bez ograniczeń;
    * obrazy osadzone (`XObject`) są czytane przez OCR obrazów osadzonych zawsze, ale **małe wycinki** czyta on gorzej niż OCR
      strony – parafę w małym XObject-cie na stronie z warstwą wykrywa dopiero OCR renderu bez tekstu (wyżej: 2/6 z samego OCR
      obrazów osadzonych, 4/6 z renderem bez tekstu). Wartości
      `niewykrywalne` (OCR oryginału ich nie czyta albo – J3 – linia bazowa nie odnajduje ich z potwierdzeniem;
      `_Grupa.ocr = False`) **nie są szukane w OCR obrazów osadzonych** – dla nich jedyną drogą w pikselach jest OCR stron
      (pełny render albo render bez tekstu);
    * warstwa tekstowa „użyteczna” (`_strony_z_warstwa`) to każda z literą albo cyfrą i bez znaków sterujących – także warstwa
      **wiarygodnie zepsuta** (ToUnicode przesunięte o jeden znak: tekst wygląda poprawnie, kopiowanie daje „Sbnpt!…”) i warstwa
      z **samym numerem strony** na stronie-obrazie. Pomiar (4 dokumenty `parafy`, 24 wartości): strona-obraz inline z numerem
      strony jako tekstem – 0/24 bez reguł dodatkowych, 23/24 z renderem bez tekstu (render bez tekstu zostawia obraz; jedna strata – „R.S.” w stopce nieczytane
      przez OCR w żadnym odczycie, także pełnego renderu); ToUnicode przesunięte – 20/24 w obu stanach (inicjały trafiają w surowych
      strumieniach PDF, gdzie kody znaków są nietknięte; drugie wystąpienie tych samych inicjałów nie jest liczone, bo krotność
      liczą warstwa tekstowa i OCR, a glifów tej strony OCR inicjałów nie widzi – zaniżenie krotności, nie wycieku dokumentu:
      4/4 dokumenty wyciekają); ToUnicode w obszarze prywatnym albo usunięte – 24/24 w obu stanach. Bez ekspozycji w korpusie: generatory
      rysują inicjały tylko zwykłym tekstem (`parafy`, `skroty_po_pelnym`), bez przypadków H4a;
    * pole wybielane jest wyłącznie po ciemności i rozmiarze: **jasny tekst na ciemnym wypełnieniu** (biała parafa w granatowej
      pieczątce) po wybieleniu znika, więc takiej parafy w pikselach sędzia nie liczy; pole węższe niż 15 px w odczycie (np. pole
      na kropkę) zostaje – w pomiarze nie dało trafień. Krotność (`_ile_w_ocr`) liczona jest z odczytów bez wybielania (szum pól
      może zawyżyć liczbę wycieków wartości o tym samym tekście, gdy dokument już wycieka), a nie z trafień potwierdzonych.
* **Generatory** (`trudne_wspolne.inicjaly_jednoznaczne`): w dokumentach `parafy` i `skroty_po_pelnym` wzorzec żadnych inicjałów
  nie występuje poza spanami gold („C.” w „k.c.”, honoryfikat „M.” przy osobie o nazwisku na M, francuskie „v.”, niemieckie „ab”),
  w CAŁYM tekście (razem z gold) trafia nie częściej niż w tekstach wartości gold – tą samą miarą co sędzia
  (`normalizacja.ile_inicjalow`; łapie dopasowanie przez granicę gold: honoryfikat FR „M.” / ES „D.” spoza gold i inicjał gold
  „L.” dają „M. L.”, czyli wzorzec inicjałów „M.L.” tej samej osoby) – a inicjały różnych osób nie trafiają się nawzajem;
  w przeciwnym razie dokument jest losowany od nowa (kolejne ziarno; próba 0 to ziarno dokumentu, więc dokumenty bez kolizji są
  takie same jak bez reguły). Bez tej reguły sędzia wyłączałby jako niejednoznaczne 19 z 568 wartości `INICJALY` próbki
  kontrolnej (`skroty_po_pelnym` docx ES/FR) – inicjały zostawione przez uczestnika nie byłyby oceniane; z nią – 0 z 585.
* **Przesunięcie rozkładu przez losowanie od nowa**: odrzucane są dokumenty, w których inicjały pokrywają się ze słowem tekstu
  (ES „al”, DE „ab”, EN „at”) albo z honoryfikatem (FR „M.”, ES „D.” przy imieniu na tę literę) – takie warianty, realnie
  trudniejsze, w warstwie nie występują („inicjały równe słowu dokumentu” są poza zakresem). Skala (40 ziaren na język,
  odrzucenia pierwszej próby): `parafy` DE 4/40, ES 2/40, EN 1/40, FR 1/40, PL 0/40; `skroty_po_pelnym` FR 19/40, PL 9/40,
  ES 8/40, DE 1/40, EN 1/40. Wpływ na rozkład: w `skroty_po_pelnym` FR inicjały „X.Y.” zaczynające się literą honoryfikatu („M.”)
  to 5/80 wartości (bez reguły „cały tekst ≤ gold” – 11/80), ES („D.”) – 1/80 (bez niej 3/80); pozostałe przypadki i języki bez
  zmian.
* Ograniczenie: inicjał osoby trafiany wewnątrz innych inicjałów tej samej osoby („K.” w „J.K.”) jest raportowany jako wyciek obu
  wartości, gdy uczestnik zostawi tylko „J.K.” – na poziomie dokumentu i encji bez znaczenia (ta sama osoba, dokument i tak ma
  wyciek), na poziomie wartości zawyża liczbę wycieków.
* Ograniczenie (OCR): wzorzec jest dokładny – kropka zgubiona przez OCR („J.K” zamiast „J.K.”) albo diakrytyk przeczytany bez
  znaku („L.” zamiast „Ł.”), litera czytana jako cyfra („1.T.” zamiast „I.T.”) albo sklejona z sąsiednim znakiem („ick/” zamiast
  „/CK/”) nie trafia. Dotyczy tylko wyników spłaszczonych do obrazu (warstwa tekstowa jest dokładna); tolerancja
  na takie błędy OCR przy wzorcu 1–3 liter trafiałaby szum, więc jej nie ma – możliwy przeoczony wyciek inicjałów w rastrze,
  jednakowo dla wszystkich uczestników.

## Ukraiński w uruchamianiu

`uk` należy do `pbench.uruchom.JEZYKI` (dokumenty warstwy trudnej `cyrylica_dokument_uk`; `--jezyki uk` filtruje je jak inne
języki). Reguła dla uczestnika, który ukraińskiego nie deklaruje – opisana w `metodyka/uczestnicy.md` („Język zastępczy”). Wynik
surowy i rekord oceny niosą `jezyk_uzyty`. Wznowienie przebiegu przelicza nieaktualne wpisy `pominiety: jezyk` (np. dokument
`uk` z przebiegu bez języka zastępczego), gdy uczestnik ten język przetwarza. Ukraiński jest poza T4 (`punktacja.md`), dokumenty `uk` wchodzą do T3/P3 jako przypadek;
flaga `w_zakresie_oficjalnym` liczy się po języku dokumentu (`uk` nie deklaruje oficjalnie żaden uczestnik).
