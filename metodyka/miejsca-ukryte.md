# Miejsca gold dla treści ukrytej w DOCX / XLSX / PPTX / PDF i dopisków obrazowych (warstwa trudnych przypadków, spec §11 pkt 1 i 6)

Wagi miejsc są zamrożone (`wagi_punktow.json`, `wagi_miejsc`) – nowe elementy ukryte NIE dostają własnych miejsc, tylko
istniejące. Zasada z `punktacja.md`: miejsca, których użytkownik zwykle nie ogląda przed wysłaniem, ważą więcej.
Element zapisany w manifeście w polu `ukryte` jako `<format>.<rodzaj>`; wszystkie wartości jednego elementu mają to samo
miejsce. Tabela jest sprawdzana testem (`tests/test_h3.py`) względem `pbench.trudne_ukryta.MIEJSCA`.

| Element | Miejsce | Waga | Gdzie leży w pliku | Uzasadnienie |
|---|---|---|---|---|
| `docx.vanish` | `metadane` | 2,0 | `w:vanish` w `word/document.xml` | tekst niewidoczny w normalnym widoku |
| `docx.zakladka` | `metadane` | 2,0 | `w:bookmarkStart/@w:name` | nazwa niewidoczna w tekście, widać ją tylko w oknie zakładek |
| `docx.custom_xml` | `metadane` | 2,0 | `customXml/itemN.xml` | część pakietu bez żadnego widoku w edytorze |
| `xlsx.wiersz_ukryty` | `metadane` | 2,0 | wiersz `hidden="1"` | niewidoczny w arkuszu |
| `xlsx.kolumna_ukryta` | `metadane` | 2,0 | kolumna `hidden="1"` | niewidoczna w arkuszu |
| `xlsx.arkusz_hidden` | `metadane` | 2,0 | arkusz `state="hidden"` | zakładka ukryta; odkrywa się poleceniem „Odkryj” |
| `xlsx.arkusz_veryhidden` | `metadane` | 2,0 | arkusz `state="veryHidden"` | nie da się go odkryć z interfejsu |
| `xlsx.pivot` | `metadane` | 2,0 | `xl/pivotCache/*` (definicja i rekordy) | pamięć podręczna tabeli przestawnej, bez widoku |
| `xlsx.nazwa` | `metadane` | 2,0 | `definedName` ze stałą | widoczna tylko w Menedżerze nazw |
| `xlsx.walidacja` | `metadane` | 2,0 | `dataValidation/formula1` z listą nazwisk | widoczna dopiero po rozwinięciu listy w komórce |
| `pptx.slajd_ukryty` | `metadane` | 2,0 | slajd `show="0"` | pomijany w pokazie i w druku |
| `pptx.poza_slajdem` | `metadane` | 2,0 | kształt z `a:off` poza `sldSz` | poza obszarem slajdu; widać go tylko w edytorze |
| `docx.pole_author`, `docx.pole_mergefield`, `docx.pole_docproperty` | `pole` | 1,5 | `w:instrText` i wynik pola | instrukcja pola jest niewidoczna, wynik widoczny |
| `docx.alt_text` | `obraz` | 1,5 | `wp:docPr/@descr`, `@title` | opis obrazu, który czytają czytniki ekranu |
| `docx.wykres` | `obraz` | 1,5 | `word/charts/chartN.xml` (nazwy serii, kategorie) | wykres to obiekt graficzny |
| `docx.obiekt` | `obraz` | 1,5 | `word/embeddings/*.xlsx` | obiekt osadzony, w dokumencie widać tylko ikonę |
| `pptx.alt_text` | `obraz` | 1,5 | `p:cNvPr/@descr` obrazu | jak w DOCX |
| `docx.naglowek_pierwszej_strony` | `naglowek` | 1,5 | `w:titlePg` + nagłówek `first` | nagłówek innej strony niż pozostałe, łatwo go przeoczyć |
| `docx.przypis_koncowy` | `przypis` | 1,0 | `word/endnotes.xml` | przypis jest widoczny na końcu dokumentu |
| `xlsx.komentarz` | `komentarz` | 2,0 | `xl/commentsN.xml` | komentarz widać dopiero po najechaniu na komórkę |
| `pptx.notatki` | `komentarz` | 2,0 | `ppt/notesSlides/*` | notatki prelegenta nie są na slajdzie |
| `pptx.komentarz` | `komentarz` | 2,0 | `ppt/comments/*` | komentarze recenzenta |
| `docx.pole_tekstowe` | `tresc` | 1,0 | `w:txbxContent` (`wps` i wersja VML) | pole tekstowe jest widoczne na stronie |
| `xlsx.formula` | `tabela` | 1,0 | `<f>` ze stałymi + wartość w `<v>` | wartość wyliczona jest widoczna w komórce |
| `pdf.zaczernienie` | `metadane` | 2,0 | tekst w strumieniu treści strony aneksu, nad nim czarny prostokąt | czytelnik widzi zaczernienie, a tekst pod spodem da się zaznaczyć i skopiować |
| `pdf.warstwa_ocr` | `metadane` | 2,0 | niewidoczny tekst (tryb renderowania 3) na stronie ze skanem | dane, których nie ma na obrazie; widać je dopiero po zaznaczeniu tekstu |
| `obraz.pieczatka`, `obraz.zrzut_ekranu` | `obraz` | 1,5 | obraz osadzony w PDF (strona załącznika) albo DOCX (`word/media`) | dane narysowane w pikselach; czyta je tylko OCR |
| `znak_wodny.pdf` | `obraz` | 1,5 | obraz osadzony raz, nakładany ukośnie na każdą stronę (półprzezroczysty) | element graficzny strony, nie tekst |
| `znak_wodny.docx` | `naglowek` | 1,5 | WordArt (`v:textpath/@string`) w nagłówku | znak wodny Worda leży w nagłówku sekcji |
| `poczta.wiadomosc` | `zalacznik` | 1,5 | MSG: obiekt osadzony (`ATTACH_EMBEDDED_MSG`, storage `__substg1.0_3701000D` z nagłówkami, treścią i własnym załącznikiem); EML: część `message/rfc822` | wiadomość w wiadomości – jej nagłówki i treść czyta się dopiero po otwarciu załącznika |
| `poczta.zalacznik_pdf` | `zalacznik` | 1,5 | załącznik PDF wiadomości głównej albo zagnieżdżonej (MSG: `PR_ATTACH_DATA_BIN`, EML: część `application/pdf`) | jak każdy załącznik poczty (trzon: DOCX) |
| `poczta.vcard` | `zalacznik` | 1,5 | załącznik `.vcf` (`text/vcard`, VERSION 3.0 albo 4.0: FN, N, ORG, TEL, EMAIL, ADR) | wizytówka to załącznik |
| `poczta.cytat` | `tresc` | 1,0 | treść wiadomości pod podpisem (`text/plain`, `text/html`, `PR_BODY`): akapity z atrybutem `cytat`, nie element `ukryte` | wątek cytowany jest widoczny w treści, choć łatwo go przeoczyć pod podpisem |

Pola z krotnością 2 (`KROTNOSC` w `trudne_ukryta.py`): pole (instrukcja i wynik), pole tekstowe (`wps` i VML), formuła
(`<f>` i `<v>`) – gold listuje wartość tyle razy, ile razy ją zapisano, bo tyle wystąpień liczy sędzia plikowy.

Wartości `obraz` z tekstem w XML (alt text, wykres, obiekt osadzony) mają cechę `tekst_xml`: sędzia plikowy szuka ich w
tekście części pakietu, nie w OCR (bez tej cechy trafiałyby do `niewykrywalne`, bo na obrazie nie ma żadnych pikseli z
tekstem). Każdy element niesie własne osoby (nie występują w widocznej treści), więc uczestnik czyszczący tylko widoczną
treść zostawia wyciek dokładnie w elementach ukrytych.

Sędzia plikowy pomija części `printerSettings/*.bin` (binarne ustawienia drukarki z szablonu OOXML, nigdy miejsce danych –
bajty dawały fałszywe wycieki częściowe u każdego uczestnika); inne części `.bin` (np. `oleObject*.bin`, `vbaProject.bin`)
są przeszukiwane, bo mogą nieść dane.

## Rozszerzenia sędziego plikowego (H4a)

* **Przeniesienia**: wyraz złamany łącznikiem na końcu wiersza („Kowal-\nski”; PDFium zapisuje taki łącznik jako U+FFFE) ma
  w stronie PDF i w pliku `.txt` dodatkowy widok ze sklejonym zapisem, a wartość gold z przeniesieniem jest szukana w postaci
  sklejonej. Zwykłe myślniki w wierszu („Nowak-Kowalski”) nie są sklejane; wyraz złożony złamany po łączniku ma też zapis
  niesklejony.
* **RTL**: PDF-y przypadku `rtl` mają glify w kolejności wizualnej, z kształtowaniem liter arabskich (`arabic-reshaper`, `python-bidi`),
  jak w pliku zapisanym przez Worda/LibreOffice; e-mail pod U+202E leży w strumieniu prosto (gold z pliku = to, co widać).
  PDFium porządkuje taki tekst bidi (wyrazy RTL w zapisie logicznym), pdfminer oddaje porządek wizualny z formami prezentacyjnymi
  – wartości RTL są rozpoznawalne w obu. Widok `widok_rtl` (wyrazy z literą RTL odwrócone) zostaje dla wyników uczestników, którzy
  zapisali glify w porządku logicznym bez bidi (PDFium oddaje je wtedy odwrócone).
* **Strony PDF czytane OCR** (`obrazy.ocr_stron_pdf`): każda strona KAŻDEGO pliku PDF zwróconego przez uczestnika jest
  renderowana (PDFium, 300 dpi) i czytana OCR – bez warunku wstępnego. Wartość wycieka, gdy widać ją w którymkolwiek widoku:
  warstwa tekstowa, strumienie i bajty surowe, obrazy osadzone, OCR stron. Dzięki temu liczy się to, co widzi czytelnik, także gdy
  kopiowanie tekstu daje coś innego: strona jako obraz (XObject albo inline) z niewidoczną warstwą tekstową (Tr 3), tekst przykryty
  obrazem, zepsuta mapa ToUnicode, tekst jako ścieżki. Strony oryginału PDF są czytane tak samo, raz na dokument (pamięć podręczna
  po sumie pliku, dpi, trybie, języku i wersji OCR). Wartości z linii bazowej, których odczyt 300 dpi nie odnalazł na stronach, mają
  drugi odczyt: 400 dpi, Tesseract w trybach psm 3 i psm 6 (drobny druk, raster strony o niskiej rozdzielczości, blok tekstu w
  układzie wielokolumnowym, który automatyczny podział strony – psm 3 – potrafi pominąć). Ograniczenie: OCR bywa zawodny, a
  wartość, której nie przeczyta żaden odczyt i której nie ma w warstwie tekstowej, nie zostanie wykryta. Na konstrukcjach z
  przeglądu (strona-raster inline lub XObject z warstwą tekstową uczestnika idealnego, tekst pod rastrem, raster nad widocznym tekstem, zepsuty ToUnicode z nakładką
  Tr 3, skan zwrócony jako strony-obrazy inline) sędzia odnajduje ≥ 95% wartości widocznych na stronie (`tests/test_h4a.py`).
  OCR całej strony widzi też słowa innych wartości i zamienniki uczestnika, więc dopasowanie ma zastrzeżenia:
  * **Potwierdzenie trafień częściowych**: trafienie częściowe (część tokenów wartości) znalezione wyłącznie w OCR stron liczy się
    tylko wtedy, gdy ten sam token trafia też w innym odczycie tej samej strony (inna rozdzielczość albo inny tryb Tesseracta:
    300 dpi psm 3, 400 dpi psm 3 i psm 6, odczyty po wyprostowaniu). Śmieci OCR z tabel i zamienników („EMA” z okaleczonego
    „[EMAIL_10]”, linia tabeli czytana jako „ray”) zwykle stoją w jednym odczycie. Widoczny tekst nie zawsze jest we wszystkich:
    blok w układzie dwukolumnowym (dane kupującego na fakturze) czyta tylko psm 6, więc po drugim odczycie ma tylko jeden. Dlatego
    strona, na której po drugim odczycie zostaje trafienie bez potwierdzenia, dostaje trzeci odczyt – psm 6 w 300 dpi: każdy blok
    ma wtedy odczyty w dwóch rozdzielczościach (`de-faktura-0007` z zamazanym tylko „GmbH” kupującego: „Jäger Logistik” jest
    wyciekiem częściowym). Trafienie pełne wystarcza z jednego odczytu, chyba że składa się wyłącznie z trafień rozmytych (śmieć
    „MARA” ≈ „Maria”) – wtedy także potrzebuje potwierdzenia, a potwierdzone jest pełne. Trafienia częściowe z warstwy tekstowej
    i strumieni liczą się bez potwierdzenia; z OCR obrazu osadzonego (każdy format: miniatura ODT, obrazy DOCX/XLSX/PPTX i PDF,
    obrazy-załączniki poczty) – jak ze stron, z potwierdzeniem w innym odczycie tego obrazu, a obraz bez potwierdzenia dostaje
    drugi odczyt (mały – psm 6 i 11 w dwukrotnie większej skali, duży – psm 6 i 11 obok psm 3). Reguły potwierdzenia dla
    obrazów osadzonych: (a) odczyt innym trybem Tesseracta potwierdza wspólny token; (b) odczyt tym samym trybem w innej skali
    potwierdza tylko wtedy, gdy wspólny token jest w co najmniej jednym z dwóch odczytów słowem DOKŁADNIE – powiększenie tych
    samych pikseli powtarza szum rozmyty („Osoba” z miniatury ODT czytane w każdej skali jako „Osowa” ≈ „Sowa”), ale nie
    wymyśla dokładnego nazwiska (pieczątka 741×131, w której tylko psm 11 czyta „[OSOBA_7] Bernal” w obu skalach, jest
    wyciekiem częściowym); (c) token identyfikujący o długości co najmniej 7 znaków (`plik.MIN_DL_TOKENU_BEZ_POTWIERDZENIA`)
    trafiony dokładnie w jednym odczycie wystarcza bez potwierdzenia – tylko na obrazach osadzonych, strony PDF zawsze
    wymagają potwierdzenia. Koszt reguły: krótki token przeczytany dokładnie tylko w jednym odczycie małego obrazu nie liczy
    się – na próbce przeglądu (135 dokumentów, 108 prawdziwych trafień częściowych z obrazów osadzonych) to jeden wyciek:
    „Díez” w pieczątce DOCX, czytane dokładnie tylko przez psm 11 w skali ×1 (psm 6 skleja je z podkreślnikami dopełnienia
    zamiennika, psm 11 ×2 czyta „Diez”, słowo generyczne hiszpańskiego dokumentu).
    Słowo OCR krótsze niż 5 znaków nie trafia rozmyto („ana”, „EICH” – śmieci OCR z linii tabeli – nie są
    „Anna”, „Erich”, nawet gdy ten sam śmieć stoi w kilku odczytach psm 3 i psm 6), token krótszy niż 4 znaki trafia tylko
    dokładnie. Gdy potwierdzenia brak po odczycie 300 dpi, strona dostaje drugi odczyt (400 dpi), a potem ewentualnie trzeci (300 dpi psm 6). Na 12
    rastrach wyników uczestnika częściowego (prawda: ten sam wynik z warstwą tekstową) reguła nie zgubiła żadnego
    prawdziwego wycieku.
  * **Wspólna lista słów-zamienników** (`plik.SLOWA_ZAMIENNIKOW`): słowo OCR równe innemu słowu dokumentu (słowo szablonu, token
    innej wartości gold) nie trafia rozmyto tokenu wartości („Schmidt” innej osoby nie jest wyciekiem adresu „lschmidt@…”). Słowo
    zamiennika w kontekście zamiennika – w nawiasie (`[ ] < > { } ( )`) razem z innymi słowami zamienników, dotykające nawiasu albo
    z numerem po nim („[ADRES 21]”, „<PERSON>”, „OSOBA 1”) – jest w tekście OCR maskowane: nie jest pojedynczym tokenem wycieku
    („login” z „[LOGIN 7]”) i nie trafia rozmyto („[ADRES 21]” – zamiennik bez podkreślnika – nie jest „Andrés”). Poza tym
    kontekstem to zwykłe słowo: nazwisko „Alter” obok „[PERSON]” jest wyciekiem częściowym „Hans Alter”. Same wielkie litery
    kontekstem nie są (nazwiska bywają pisane wersalikami). Słowa zamienników pochodzą z etykiet WSZYSTKICH uczestników w
    repozytorium (kategorie benchmarku, tokeny Privatizera we wszystkich profilach językowych, etykiety natywne Presidio, GLiNER,
    OpenAI Privacy Filter, Stanza – „<PERSON>”, „[NAME]”, „[OSOBA_1]” są chronione tak samo), nie z warstwy tekstowej wyniku
    (uczestnik mógłby dopisać niewidoczne warianty tokenów).
  * **Znaki mylone i granice dla identyfikatorów i dat**: identyfikatory, daty i kwoty są w OCR porównywane po złożeniu znaków,
    które OCR myli (`plik.ZNAKI_MYLONE_OCR`: O→0, I/l→1, Z→2, S→5, B→8, po obu stronach: „2O25” = „2025”, „Z1.” = „21.”) wzorcem
    z granicami – trafienie nie może wchodzić w dłuższy ciąg liter i cyfr („912345678” nie zawiera „12345678”). Dopasowanie rozmyte
    (difflib) zostaje tylko dla identyfikatorów kategorii identyfikacyjnych o co najmniej 10 znakach (IBAN, PESEL, NIP), też z
    granicami. W dacie i kwocie cyfry porównywane są dokładnie (cyfra albo litera, którą OCR czyta w jej miejscu: „b” jako 6 lub 8,
    „G” jako 6, „T” jako 7), z granicami, bo inna cyfra dnia, miesiąca albo roku to inna data (cytat orzeczenia „29.11.2022 r.” nie
    jest wyciekiem daty „28.11.2022 r.”, „17 sierpnia” nie jest „7 sierpnia”); nazwa miesiąca i waluta – rozmyto (podobieństwo
    ≥ 0,8 albo jedna zmiana: „sierpma”, „Jume”, „Mürz”), ale inna nazwa miesiąca to inna data („Juli” ≠ „Juni”); „r.” i waluta są
    opcjonalne (OCR je gubi albo psuje). Wystąpienie innej wartości gold jest wycinane
    z tekstu OCR tylko z granicami („1. Juli 2025” nie jest wycinane ze środka „21. Juli 2025”). Token z cyfrą trafia też po
    złożeniu („I48” odczytane jako „148”). Token złożony z samych cyfr w wartości spoza kategorii identyfikacyjnych (dawka
    „1000 mg”, numer domu) nie identyfikuje wartości sam w sobie w żadnym widoku (trafia w cyfry tabel i metryk czcionek
    `/Widths`); liczy się do wycieku pełnego.
  * **Fraza OCR**: pełna wartość jest w OCR szukana także jako fraza z tolerancją – tokeny liczące się w kolejności, między nimi
    co najwyżej trzy słowa krótsze niż `min_dl_tokenu`, każdy token dokładnie, rozmyto albo po złożeniu znaków
    mylonych. Nazwa złożona z samych słów generycznych („Eko-Serwis Centrum Medyczne sp. z o.o.”, OCR: „sp. z 0.0.”) wycieka więc
    z rastra tak samo jak z warstwy tekstowej.
  E-mail i URL są w OCR szukane także jako ciąg alfanumeryczny (próg 0,93, z granicami), bo „@” bywa czytane jako litera i skleja
  tokeny.
  **Krotność** wartości o kilku `id` (e-mail w treści i w stopce) liczona jest w tekstach OCR regułą OCR, a nie dokładną frazą,
  której OCR prawie nigdy nie odtwarza – i tylko z trafień PEŁNYCH: wiersz z pełną wartością liczy się tyle razy, ile razy ma ją
  dokładnie (co najmniej raz); ciąg wierszy z samymi trafieniami częściowymi liczy się raz tylko wtedy, gdy ich złączenie (także z
  sąsiednim wierszem) trafia pełnie – wartość złamana między wiersze; identyfikator złamany na dwa wiersze, z których żaden nie
  trafia sam („… rejestracyjnym SZ” / „22924. …”), też raz. Samo nazwisko w innym wierszu nie jest drugim wystąpieniem imienia
  i nazwiska. Odczyty tej samej strony (300 i 400 dpi) i widoki tej samej treści (warstwa tekstowa i render strony) nie sumują się.
  Wartości z komentarzy (adnotacji) i metadanych nie są rysowane na stronie, więc w rastrze strony nie wyciekają.
  **Duża strona**: strona, której bok w docelowym dpi przekracza `ekstrakcja.MAKS_BOK_RENDERU_PX` (12 000 px), jest renderowana
  w pełnym dpi kafelkami obszaru z treścią (podgląd wskazuje obszar z niebiałymi pikselami; kafelki z zakładką 300 px, puste
  pomijane) – powiększenie `/MediaBox` nie obniża rozdzielczości treści. OCR wartości obrazowych niewykrywalnych w OCR obrazu
  osadzonego (logo czytane jako tekst nazwy) obejmuje też render stron – uczestnik zwracający raster może je ujawnić tak samo jak
  uczestnik z warstwą tekstową. Z widoków strumieni i surowego wycinane są dane obrazów inline (`BI … ID … EI`), które w
  kodowaniu ASCII85 wyglądają jak tekst.
* **Zbiory dokumentu** (`plik.zbiory_dokumentu`): wartości niejednoznaczne, słowa generyczne, wartości niewykrywalne i linia bazowa
  (mianownik) są liczone raz, z samego oryginału, i są wspólne dla wszystkich uczestników – nic w pliku uczestnika ich nie zmienia.
  OCR stron oryginału wchodzi do niejednoznacznych i słów generycznych tylko wtedy, gdy oryginał sam ma zepsutą warstwę tekstową
  (`plik.warstwa_tekstowa_zepsuta`: w tekście stron odnajduje się mniej niż 90% wartości tekstowych gold – od 3 wartości – albo
  są ≥ 3 znaki sterujące, tak PDFium oddaje znaki bez mapy ToUnicode; w trzonie, 298 PDF-ów i skanów, najniższe pokrycie to 0,963).
  Render zwykłego oryginału to gorszy odczyt tej samej treści: słowa wartości gold zniekształcone przez OCR stałyby się
  „generyczne” i wyciek częściowy tych słów przestałby się liczyć. Linia bazowa korzysta ze wszystkich widoków oryginału, także
  OCR stron; niejednoznaczne z OCR stron (oryginał zepsuty) porównują się z `gold_tekst + gold_obraz` (render pokazuje obok tekstu
  logo i podpis).
* **Obrót**: duże obrazy (strony) są sprawdzane OSD Tesseracta; obraz obrócony o 90/180/270 stopni ma dodatkowy odczyt po
  wyprostowaniu. Strony PDF z `/Rotate` są czytane w kolejności treści (rotacja ustawiona na 0 tylko w pamięci).
* **Obrazy**: ekstrakcja PDF czyta też obrazy poza zasobami strony (formularze nakładek, np. znak wodny); maska `/SMask` albo
  `/Mask` jest pomijana tylko wtedy, gdy jej rodzic został przeczytany (pikepdf składa alfę) i sama nie jest rysowana operatorem `Do`.
* **Widok surowy PDF** (`pdf:surowe`): z bajtów pliku wycinane są tylko nazwy ze słownictwa formatu (`ekstrakcja.NAZWY_FORMATU_PDF`:
  `/Info`, `/Type`, `/Font`…), żeby „info” z adresu e-mail nie dawało częściowego wycieku z każdego pliku; pozostałe nazwy zostają
  jako tekst z zdekodowanym `#xx` (`/Marka#20Filipka` → „Marka Filipka”) – tak samo w bajtach pliku i w strumieniach po dekompresji
  (np. osierocony strumień obiektów `/ObjStm`). W widokach surowych (bajty pliku, strumienie, stringi literalne) ucieczka
  ósemkowa `\ddd` i znak sterujący zdekodowanego stringu są częścią słowa, nie jego granicą: kod glifu podzbioru czcionki
  („…obsługę prawną” zapisane `prawn\002`) nie daje uciętego słowa „prawn”, które byłoby formą „Prawna” z wartości „Kancelaria
  Prawna Mazovia sp. z o.o.”; ucieczka znaku ASCII drukowalnego albo białego to ten znak (`Jan\040Kowalski` – dwa słowa).

## Poczta, RTF i ODT (H4b)

* **Wiadomość zagnieżdżona i załącznik PDF** (`ukryta_poczta`): MSG zawiera załącznik będący wiadomością (obiekt osadzony
  `ATTACH_EMBEDDED_MSG`, nie plik `.msg`) z własnymi nagłówkami (nadawca, adresat), treścią i załącznikiem PDF; EML – część
  `message/rfc822` o tej samej budowie. Wiadomość główna ma też własny załącznik PDF (karta klienta). Załączniki dopisuje do
  gotowej wiadomości `pbench.pliki_poczta`. Każda osoba załączników to inna osoba niż w treści wiadomości.
* **Wątek cytowany z wizytówką** (`cytowane_watki_vcard`): pod podpisem 3–5 wcześniejszych wiadomości – nagłówek Outlooka
  („Od/Wysłano/Do/Temat” za kreską) albo przypis „W dniu … napisał(a):” z cytowaniem `>` (zagłębienie rośnie z każdą odpowiedzią);
  każda wiadomość ma stopkę z danymi nadawcy, a treść – dane klienta. Wartości wątku mają miejsce `tresc` i cechę `cytat` (są też
  w tekście poziomu 1). Załącznik vCard (`.vcf`) z danymi osoby trzeciej – miejsce `zalacznik`.
* **PDF w załączniku poczty** jest oceniany tą samą ścieżką co samodzielny PDF: warstwa tekstowa, strumienie, bajty surowe, obrazy
  osadzone i OCR każdej strony (`plik.ocr_stron_pliku`, `obrazy.ocr_stron_osadzonych`; pamięć podręczna OCR po sumie pliku PDF, te
  same odczyty 300/400 dpi i potwierdzenia). Strony osadzonych PDF-ów są renderowane, bo raster strony (obraz inline)
  w załączniku byłby niewidoczny dla sędziego. Krotność wartości: render pokazuje tylko PDF-y, więc zasada „warstwa tekstowa ALBO
  render – większa liczba” obowiązuje osobno dla każdego PDF-u (także w wiadomości zagnieżdżonej), a wystąpienia z treści, nagłówków
  i innych załączników się dodaje – uczestnik, który zamienia PDF załącznika na raster, nie ukrywa drugiego wystąpienia wartości
  obecnej też w treści. PDF załącznika ze zepsutą warstwą tekstową (mapa ToUnicode) – jak samodzielny PDF: OCR jego stron wchodzi do
  zbiorów dokumentu (oczekiwane wartości: te, które OCR jego stron czyta – gold nie mówi, w którym załączniku leży wartość). Kryterium „zepsuty” jest liczone wyłącznie z oryginału
  (`zbiory_dokumentu`), więc jest wspólne dla wszystkich uczestników; oczekiwane wartości (te, które OCR stron czyta dokładnie) są
  warunkiem koniecznym i bezpiecznym – słaby OCR (mniej niż 3 dokładne odczyty) tylko NIE dokłada OCR stron do niejednoznacznych, więc
  sędzia jest wtedy surowszy, nie łagodniejszy. Załączniki o tej samej nazwie (albo bez nazwy; także zewnętrzny i zagnieżdżony
  `message/rfc822`) dostają unikalny przedrostek części (`zal(nazwa#2):`), by każdy PDF był liczony osobno.
* **vCard**: sędzia czyta plik `.vcf` (załącznik albo plik wynikowy; UTF-8 z BOM-em albo bez, UTF-16): wiersze rozwinięte, wartości właściwości ze zdjętymi znakami
  ucieczki, składowe `N`/`ADR` rozdzielone, QUOTED-PRINTABLE (vCard 2.1) zdekodowane, `PHOTO` – OCR. Miasto wizytówki jest spoza
  miast dokumentu (to samo miasto w treści albo wątku czyniłoby je niejednoznacznym). Kod pocztowy wizytówki (tokeny – cyfry spoza
  identyfikatorów) jest, jak w całym korpusie, poza mianownikiem (`Regula.moze_wyciec`); adres oceniają ulica i miejscowość.
* **RTF i ODT** (`formaty_rtf_odt`): formaty spoza trzonu, DOCX przekonwertowany LibreOffice'em jak DOC – gold sprawdzony odczytem
  zwrotnym, co konwersja zgubiła, usunięte z gold z ostrzeżeniem. Autor komentarza z literą spoza strony kodowej: LibreOffice
  zapisuje `\atnauthor` 8-bitowo („Bąk” → „B?k”), więc generator przepisuje to pole na `\uN\'3f` znanej wartości przed odczytem
  zwrotnym (`render.rtf.zapisz_pola_unicode`) – autor zostaje w gold. Bajty powtarzalne po normalizacji (`render.rtf.normalizuj_rtf`: stały porządek
  tablic czcionek i kolorów; `render.odt.normalizuj_odt`: stały czas ZIP, numeracja identyfikatorów zmian i nazw komentarzy, stały
  `Rsid`). Utrudnienia `papier_firmowy`, `tabele`, `komentarze`, `metadane` są wymuszone, a dokument bez komentarza albo tabeli
  dostaje je z osobą dodatku. Sędzia czyta RTF własnym parserem (`sedzia/rtf.py`: część na miejsce – treść, nagłówek, stopka,
  przypis, komentarz, metadane `\info`/`\userprops`, pola, każda nieznana grupa `{\*…}` z tekstem; kształty to treść jak w DOCX
  i ODT: pole tekstowe `\shptxt` – treść miejsca kształtu, tekst alternatywny i WordArt (`{\sv …}`) – część `ksztalt`; `\binN` –
  dokładnie N bajtów; obrazy `\pict` → OCR; duplikat Worda `\shprslt` jest liczony jako osobny zapis wartości, jak `mc:Fallback`
  w DOCX – obie konwencje to „gold = zapisy w pliku”, a zmiana mogłaby zajść tylko jednocześnie dla obu formatów; w widoku
  surowym `rtf:surowe` słowa sterujące RTF ze stałej białej listy `ekstrakcja._SLOWA_RTF` (słownictwo specyfikacji RTF 1.9.1) są
  zastępowane spacją wraz z parametrem – nazwa `\info` nie może trafić tokenu adresu `info.…@`, a słowo spoza listy
  (np. `\Kowalski`) zostaje tekstem, więc nie da się pod nim ukryć wartości; znaki `\uN` i `\'xx` są w nim dekodowane (strona
  kodowa `\ansicpgN`) jako część słowa – „mayor\u237\'eda” to „mayoría”, nie słowo „mayor” adresu „Calle Mayor” – a bajty
  8-bitowe wpisane wprost stroną kodową dokumentu; widok jest jeden (UTF-8): drugi odczyt zdekodowanych znaków jako cp1250
  robiłby z „ñ” granicę słowa („mañana” → słowo „ana” wartości „Ana Merino”). Wartość sklejona z zakodowaną literą w strefie
  czytanej tylko surowo (tabela czcionek: „Wroblewski\'e9”) nie trafia jako to słowo – w treści i tak nie jest widoczna jako ta
  wartość. Znak zastępczy po `\uN` zostaje w widoku (podwojona litera: „Gonz\u225\'e1lez” → „Gonzáález”), więc wartość z `\uN`
  w strefie czytanej tylko surowo nie trafia – jak przed dekodowaniem; zastępczy „?” albo „™” po `\uN` dzieli jednak słowo –
  „ma\u241?ana” daje „mañ” i „ana”: zmierzone 0 fałszywych wycieków uczestnika idealnego na 8 ziarnach × 12 RTF, pełna obsługa
  `\ucN` z zakresem grup odłożona), ODT – jak
  pakiet OOXML (`zipfile` + `lxml`: `content.xml`, `styles.xml` z nagłówkiem i stopką, `meta.xml`), z akapitem `text:p`/`text:h`
  i komentarzem `office:annotation` czytanym jako osobne linie; miniatura `Thumbnails/thumbnail.png` (ok. 362×512 px) jest czytana
  OCR jak każdy obraz – uczestnik, który zostawi miniaturę oryginału, ma za nią wycieki (test regresyjny). Rozpoznanie formatu wyniku po treści (R42) obejmuje RTF (`{\rtf`),
  ODT (`mimetype` OpenDocument Text w ZIP) i vCard.
