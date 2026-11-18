# Ograniczenia

Rozdział zbiera ograniczenia, które trzeba uwzględnić przy czytaniu wyników. Ujawnienia dotyczące przebiegu pomiaru są w aneksie ujawnień.
{% set rz = m.realizm %}{% set k = m.korpus %}
## Pozycja autora raportu

Raport publikuje autor mierzonego produktu. Dlatego metodykę, punktację, uczestników, korpus i środowisko oceny zapisano i zamrożono przed uruchomieniem jakiegokolwiek uczestnika na splicie testowym,
reguły sędziów są jednakowe dla wszystkich uczestników, a kod, metodyka i korpus są w repozytorium benchmarku, a wyniki – w raporcie i aneksie liczbowym. Rozdział „Wyniki” wylicza z danych wycinki, w których Privatizer przegrywa.
Nie usuwa to ryzyka, że wybór miar, wag lub zakresu danych sprzyja któremuś uczestnikowi; analiza wrażliwości na wagi sprawdza tylko jedną z tych decyzji.

## Korpus

- **Dane są syntetyczne.** Dokumenty powstają z szablonów i słowników, a nie z rzeczywistych pism. Rozkład typów, formatów, języków i trudności nie odzwierciedla żadnej kancelarii, a wynik na korpusie
  syntetycznym nie jest przewidywaniem wyniku na rzeczywistych dokumentach. Realizm językowy jest ograniczony, a część błędów trzonu zachowano świadomie, bo sumy kontrolne trzonu są opublikowane.
- **Błędy odmiany w trzonie.** Żeńskie nazwiska przymiotnikowe dostają błędną końcówkę (np. „Górniej” zamiast „Górnej”: {{ ile(rz.gorniej_wystapien, 'wystąpienie', 'wystąpienia', 'wystąpień') }} w {{ ile(rz.gorniej_dokumentow, 'dokumencie', 'dokumentach', 'dokumentach') }}),
  a żeńskie imiona i nazwiska na „-szka” i „-czka” odmieniają się jak przymiotniki (np. „Agnieszkiej”: {{ ile(rz.agnieszkiej_wystapien, 'wystąpienie', 'wystąpienia', 'wystąpień') }} w {{ ile(rz.agnieszkiej_dokumentow, 'dokumencie', 'dokumentach', 'dokumentach') }}).
  Wartość wzorcowa ma tę samą (błędną) formę co tekst, więc ocena wycieku jest poprawna; zaniżony jest tylko realizm. Warstwa trudnych przypadków tych błędów nie powtarza.
- **Płeć nazwisk i stanowisk.** Polski słownik zawiera żeńską formę nazwiska, którą generator dał też mężczyznom ({{ ile(rz.plec_nazwisko_wystapien, 'wystąpienie', 'wystąpienia', 'wystąpień') }}),
  a polska lista płac ma stanowisko „Księgowa” przypisane osobom o imionach męskich ({{ ile(rz.plec_ksiegowa_wierszy, 'wiersz', 'wiersze', 'wierszy') }} w {{ ile(rz.plec_ksiegowa_list, 'liście płac', 'listach płac', 'listach płac') }}).
  Wpływ na pomiar jak wyżej. W języku angielskim szablon pozwu dubluje etykietę „Claim No.” ({{ ile(rz.podwojna_etykieta_dokumentow, 'dokument', 'dokumenty', 'dokumentów') }}); druga etykieta jest poza gold.
- **Nazwy firm.** Polski słownik rdzeni nazw firm zawiera rdzeń podobny do nazwy istniejącej marki ({{ ile(rz.firma_dokumentow, 'dokument', 'dokumenty', 'dokumentów') }}, {{ ile(rz.firma_wartosci_gold, 'wartość wzorcowa', 'wartości wzorcowe', 'wartości wzorcowych') }}).
  Wszystkie nazwy firm w korpusie są fikcyjne, a podobieństwo jest przypadkowe; nazwa nie odnosi się do żadnej rzeczywistej spółki ani jej danych.
- **Identyfikatory.** Generatory PESEL, KRS, rachunków, numerów rejestracyjnych, sygnatur i kodów pocztowych poprawiono na podstawie źródeł pierwotnych (m.in. numery rejestracyjne i kody wydziałów ksiąg wieczystych w Polsce,
  numery ubezpieczenia w Niemczech i Wielkiej Brytanii, tablice we Francji), ale część pozycji pozostaje niezweryfikowana: m.in. format KRS, zakres serii dowodu osobistego, prefiksy banków i sygnatury sądowe w Polsce i na Ukrainie,
  kody pocztowe w kilku krajach, tablice rejestracyjne w Niemczech i Hiszpanii, algorytmy kilku numerów podatkowych i ubezpieczeniowych potwierdzone tylko źródłami wtórnymi. Kody pocztowe brytyjskie zawężono heurystycznie,
  więc kod nie musi istnieć. Rachunki bankowe mają poprawne cyfry kontrolne, ale kody banków i numery kont są losowe i mogą przypadkiem odpowiadać istniejącym. Pełna lista jest w metodyce (`metodyka/znane-ograniczenia.md`).
- **Telefony** są w formatach fikcyjnych: oficjalne pule numerów fikcyjnych (Wielka Brytania, USA, Niemcy, Francja) albo, dla Polski, Hiszpanii i Ukrainy (gdzie takiej puli nie ma), numery krajowe zaczynające się od dwóch zer.
  Nie przechodzą one walidacji planów numeracji, więc narzędzia walidujące numery (np. biblioteką libphonenumber) mogą mieć niższą wykrywalność. Dotyczy to wszystkich uczestników jednakowo.
- **Domeny zarezerwowane a walidacja adresów.** {% set pe = liczebnosc_domen(r, 'tekst', 'EMAIL') %}{% set pu = liczebnosc_domen(r, 'tekst', 'URL') %}{% set fe = liczebnosc_domen(r, 'pliki', 'EMAIL') %}{% set fu = liczebnosc_domen(r, 'pliki', 'URL') %}Adresy e-mail i URL w korpusie używają wyłącznie domen zarezerwowanych na mocy RFC {{ m.presidio.rfc_domeny }} i RFC {{ m.presidio.rfc_nazwy }} (`example.com`, `example.org`, `example.net` i `*.test`),
  żeby żaden syntetyczny adres nie wskazywał istniejącej skrzynki ani strony; wybór zamrożono w metodyce. Skutkiem jest to, że walidatory sprawdzające domenę z publiczną listą sufiksów nie uznają `.test` za poprawną domenę, bo jej tam nie ma. W presidio-analyzer {{ m.presidio.analyzer }} (wersja uczestników `presidio-*`)
  `EmailRecognizer` odrzuca w `validate_result` adres, dla którego `tldextract` ({{ m.presidio.tldextract }}) zwraca pustą pełną domenę, więc `jan@kancelaria.test` nie jest rozpoznawany jako e-mail, a `jan@example.com` jest; `UrlRecognizer` dopasowuje domeny tylko z zamkniętej listy końcówek, na której nie ma `test`.
  {% if pe and pu %}W rankingu tekstu na `.test` kończy się {{ ile(pe.test, 'wartość', 'wartości', 'wartości') }} EMAIL i {{ ile(pu.test, 'wartość', 'wartości', 'wartości') }} URL (wobec {{ liczba(pe.example, 0) }} i {{ liczba(pu.example, 0) }} w domenach `example.*`){% if fe and fu %}, w rankingu plików – {{ liczba(fe.test, 0) }} i {{ liczba(fu.test, 0) }} (wobec {{ liczba(fe.example, 0) }} i {{ liczba(fu.example, 0) }}){% endif %}. {% endif %}Rozpoznawacze wzorców Presidio nie wykrywają więc w tej części korpusu adresów, które model NER uczestnika może jeszcze wychwycić;
  sygnały przewagi uczestników `presidio-*` w kontroli domen (rozdział „Wyniki”) należy czytać razem z tym mechanizmem. Metodyki, punktacji ani rankingów nie zmieniono. Mechanizm sprawdzono w kodzie źródłowym podanej wersji; w jakiej części obserwowane odsetki wycieków wynikają z niego, a w jakiej z innych detektorów uczestnika (np. modeli NER), zagregowane dane nie rozstrzygają.
- **Brak zdjęć twarzy.** Korpus nie zawiera zdjęć twarzy, więc kategoria `TWARZ` nie ma wartości wzorcowych i żaden uczestnik nie jest oceniany pod tym kątem.
{% set kt = kont.trzon %}{% set kh = kont.trudne %}{% set nad = [] %}{% if not kt.cel.korpus_poza_formulowymi %}{% set _ = nad.append('korpus trzonu') %}{% endif %}{% if not kh.cel.korpus_poza_formulowymi %}{% set _ = nad.append('warstwa trudnych przypadków') %}{% endif %}{% if not kt.cel.szablony_poza_formulowymi %}{% set _ = nad.append('szablony') %}{% endif %}
{% set jez = {'pl': 'polski', 'en': 'angielski', 'es': 'hiszpański', 'de': 'niemiecki', 'fr': 'francuski'} %}{% set powyzej = [] %}{% for j in ['pl', 'en', 'es', 'de', 'fr'] %}{% if kt.korpus.po_jezykach[j].poza_formulowymi.odsetek > kt.cel.odsetek_maks %}{% set _ = powyzej.append(jez[j]) %}{% endif %}{% endfor %}
- **Kontaminacja.** Nakładanie się korpusu z danymi treningowymi mierzonego modelu porównano z wewnętrznym celem. {% if nad %}Cel przekraczają: {{ nad | join(', ') }}.{% else %}Cel jest spełniony dla korpusu trzonu, warstwy trudnej i szablonów.{% endif %}
  {% if powyzej %}Korpus trzonu jako całość {% if kt.cel.korpus_poza_formulowymi %}spełnia cel{% else %}go przekracza{% endif %}, ale w podziale na języki cel przekraczają: {{ powyzej | join(', ') }}.{% else %}W podziale na języki żaden język trzonu nie przekracza celu.{% endif %} Liczby są w aneksie ujawnień.

## Zakres pomiaru

- **Zakres gold.** Rozpoznania, kody ICD i leki są poza gold, więc ocena ochrony samej diagnozy jest poza zakresem benchmarku. Cytowane orzeczenia są poza gold z konwencji (publikowane orzeczenia nie są danymi do anonimizacji).
  Kwoty są w gold z najniższą wagą; uczestnik, który z założenia ich nie maskuje (w tym Privatizer w trybie domyślnym), ma przez to więcej wycieków, co pokazują wiersze „w tym kwoty” i miara „w deklarowanym zakresie”.
- **Poziom tekstu w XLSX** traci etykiety kolumn arkusza, bo tekst arkusza jest linearyzowany do pliku `.txt`.
- **Języki i formaty:** pięć języków (ukraiński tylko w warstwie trudnej) i formaty z opisu korpusu. Wynik nie mówi nic o innych językach, układach dokumentów ani formatach.
- **Procesor.** Wszyscy uczestnicy pracowali na procesorze, bez GPU. Narzędzia projektowane z myślą o karcie graficznej są mierzone na procesorze, także pod względem szybkości.
- **Usługi chmurowe** nie były mierzone (rozdział „Wdrożenie”), więc raport nie porównuje z nimi żadnego uczestnika.
- **Identyfikacja pośrednia** jest miarą opisową poza punktami; wynik punktowy nie mówi, czy narzędzie przerywa kombinacje danych prowadzące do ponownej identyfikacji.

## Konfiguracje uczestników

- **Różne stopnie strojenia.** Uczestnikom grupy A skalibrowano próg na splicie dev, uczestnicy grupy B pracują w ustawieniach domyślnych autorów, a Privatizera mierzono jako wydanie bez kalibracji.
  Porównanie między grupami łączy więc narzędzia o różnym stopniu dostrojenia do tego typu zadania.
- **Optimum na brzegu siatki.** Dla części uczestników grupy A najlepszy próg wypadł na najniższej wartości siatki ({{ liczba(m.kalibracja.siatka_min, 2) }}); siatki nie rozszerzano. Ustawienie progu bliskiego zera oznacza
  zwracanie niemal każdego kandydata modelu, co sprzyja pokryciu, a koszt nadmiarowego maskowania ocenia osobno test T5.
- **Warianty z aneksu liczbowego** (potok Privatizera z obcym modelem, model Legal Geek Privatizer (RC) w Presidio) analizują wkład składników i nie są porównaniem produktów. Wejście obcego modelu w potoku Privatizera różni się od wejścia modelu samodzielnego
  (silnik oddaje tekst ze spłaszczonymi białymi znakami), a dla modeli, których tokenizer uwzględnia nowe linie, to inne tokeny.
- **Naiwny wrapper** pokazuje, co zostaje, gdy anonimizuje się tylko tekst; nie jest oceną Presidio ani żadnego produktu.
- **Licencja modelu Flair.** Karta modelu `flair/ner-multi` w serwisie Hugging Face nie podaje licencji (biblioteka Flair jest na licencji MIT). Model pobrano z oficjalnego repozytorium w przypiętej rewizji; wagi nie są redystrybuowane,
  a benchmark publikuje tylko wyniki i kod uruchamiający.
- **Jedno wydanie.** Mierzono jedno wydanie Privatizera i jedne rewizje narzędzi otwartych. Raport opisuje ich stan w dniu pomiaru.

## Pomiar i sędziowie

- **Szybkość** zmierzono na jednej maszynie (Apple M1, {{ liczba(m.czas.ram_gb, 0) }} GB RAM) i jednej próbce {{ liczba(m.czas.proba_dokumentow, 0) }} dokumentów. Narzędzia plikowe obsługują część próbki (reszta jest poza ich deklaracją formatów),
  więc ich czas dotyczy mniejszej liczby dokumentów. Wynik zależy od sprzętu, budżetu wątków i pamięci maszyny (ujawnienie w aneksie ujawnień).
- **Sędziowie są regułami.** Progi sędziów (długość słowa, ułamek odsłoniętego ciągu, minimalna długość identyfikatora) zapisano z góry; mogą uznać za wyciek lub pominąć przypadki graniczne inaczej, niż zrobiłby człowiek.
  Reguły przejrzano ręcznie na splicie dev i poprawiono przed zamrożeniem. Odczyt OCR zależy od wersji Tesseracta i danych językowych, dlatego środowisko oceny plikowej jest zamrożone i sprawdzane przed oceną.
- **Niepewność.** Przedziały ufności obejmują zmienność doboru dokumentów w korpusie, nie zmienność generatora ani sędziego. Remis statystyczny oznacza, że korpus nie rozstrzyga kolejności, a nie że wyniki są równe.

## Interpretacja punktów

Punkty są sumą ważoną wielu miar. Kolejność uczestników zależy od wag testów (rozdział „Wyniki”, analiza wrażliwości), a suma punktów nie jest miarą „bezpieczeństwa” w sensie prawnym:
nie mówi, czy dokument po anonimizacji spełnia wymogi konkretnego przepisu ani umowy. Rankingi pokazują, ile wartości wzorcowych zostało w wynikach na zamrożonym korpusie i jak narzędzia radzą sobie z formatami, nadmiarowym maskowaniem i szybkością.
