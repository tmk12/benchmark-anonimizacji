# Dlaczego to ważne

Wysłanie dokumentu do zewnętrznej usługi modelu językowego (LLM) to przekazanie jego treści innemu podmiotowi. Rozdział zbiera przepisy, które kancelaria albo dział prawny ma przed oczami przy takiej decyzji:
ochronę danych osobowych, tajemnicę zawodową i tajemnicę przedsiębiorstwa, wymogi wobec dostawców usług ICT w sektorze finansowym i w cyberbezpieczeństwie oraz regulacje samych narzędzi – akt o cyberodporności
i akt w sprawie sztucznej inteligencji. To przegląd, a nie opinia prawna: nie rozstrzyga, czy konkretne użycie konkretnej usługi jest dopuszczalne. Benchmark też tego nie mierzy – pokazuje, co zostaje w dokumencie po anonimizacji (rozdział „Ograniczenia”).

Stan prawny na 13 listopada 2026 r. Brzmienie aktów UE pochodzi z EUR-Lex (wersje polskie, teksty skonsolidowane tam, gdzie istnieją), a aktów polskich – z ISAP (teksty jednolite i ogłoszone po nich ustawy zmieniające).
Każdy powołany akt ma wiersz w aneksie „Źródła prawne” z publikatorem i statusem weryfikacji.

## Ochrona danych osobowych

**Minimalizacja.** Dane osobowe mają być „adekwatne, stosowne oraz ograniczone do tego, co niezbędne do celów, w których są przetwarzane” (art. 5 ust. 1 lit. c rozporządzenia (UE) 2016/679, dalej RODO).
Jeżeli zadanie powierzane modelowi – streszczenie umowy, sprawdzenie klauzuli, szkic pisma – nie wymaga imion, numerów i adresów, przesłanie ich trudno pogodzić z tą zasadą. RODO wskazuje pseudonimizację wprost:
jako środek, który administrator wdraża, uwzględniając ochronę danych w fazie projektowania (art. 25 ust. 1), i jako przykład środka bezpieczeństwa przetwarzania (art. 32 ust. 1 lit. a).

**Powierzenie.** Usługa, która przetwarza dokumenty na zlecenie kancelarii, działa co do zasady jako podmiot przetwarzający, czyli przetwarza dane „w imieniu administratora” (art. 4 pkt 8). Administrator korzysta wyłącznie
z podmiotów przetwarzających, które zapewniają wystarczające gwarancje wdrożenia odpowiednich środków technicznych i organizacyjnych (art. 28 ust. 1), a przetwarzanie odbywa się na podstawie umowy o treści określonej w art. 28 ust. 3.
Kto sam ustala cele i sposoby przetwarzania, jest administratorem (art. 4 pkt 7); dostawca, który np. wykorzystuje przesłane treści do trenowania własnych modeli, nie działa więc wyłącznie w imieniu kancelarii.
O kwalifikacji przesądzają warunki usługi i faktyczny sposób przetwarzania.

**Przekazanie poza Europejski Obszar Gospodarczy.** Jeżeli dostawca albo jego podwykonawcy przetwarzają dane w państwie trzecim, stosuje się rozdział V RODO. Przekazanie jest dopuszczalne tylko na warunkach tego rozdziału (art. 44):
na podstawie decyzji stwierdzającej odpowiedni stopień ochrony, z zastrzeżeniem odpowiednich zabezpieczeń albo na podstawie wiążących reguł korporacyjnych (art. 45–47), a w szczególnych sytuacjach
także na podstawie wyjątków z art. 49.
Umowa powierzenia stanowi, że podmiot przetwarzający przetwarza dane wyłącznie na udokumentowane polecenie administratora, także co do przekazywania ich do państwa trzeciego (art. 28 ust. 3 lit. a).

**Naruszenie.** Incydent u dostawcy, który prowadzi do nieuprawnionego ujawnienia danych albo nieuprawnionego dostępu do nich, jest naruszeniem ochrony danych osobowych (art. 4 pkt 12). Administrator zgłasza je organowi nadzorczemu
bez zbędnej zwłoki, w miarę możliwości nie później niż w ciągu siedemdziesięciu dwóch godzin po stwierdzeniu, chyba że jest mało prawdopodobne, by skutkowało ono ryzykiem naruszenia praw lub wolności osób fizycznych (art. 33 ust. 1).

## Pseudonimizacja to nie anonimizacja

Pseudonimizacja to „przetworzenie danych osobowych w taki sposób, by nie można ich było już przypisać konkretnej osobie, której dane dotyczą, bez użycia dodatkowych informacji, pod warunkiem że takie dodatkowe informacje
są przechowywane osobno i są objęte środkami technicznymi i organizacyjnymi uniemożliwiającymi ich przypisanie zidentyfikowanej lub możliwej do zidentyfikowania osobie fizycznej” (art. 4 pkt 5 RODO).
Według motywu 26 dane spseudonimizowane, które przy użyciu dodatkowych informacji można przypisać osobie, są informacjami o możliwej do zidentyfikowania osobie fizycznej. RODO nie dotyczy natomiast informacji anonimowych,
czyli takich, przy których osoby w ogóle nie można albo już nie można zidentyfikować. O możliwości identyfikacji decydują wszelkie rozsądnie prawdopodobne sposoby, z uwzględnieniem kosztu i czasu identyfikacji
oraz technologii dostępnej w chwili przetwarzania.

Narzędzia, które zastępują dane spójnymi oznaczeniami w obrębie sprawy (tokenami, np. „[OSOBA_1]”) i przechowują tabelę powiązań, żeby przywrócić dane w odpowiedzi modelu, **pseudonimizują, a nie anonimizują**.
Dla tego, kto ma tabelę powiązań, dokument z tokenami nadal zawiera dane osobowe, a całe przetwarzanie po jego stronie podlega RODO. Anonimizacja oznacza nieodwracalność: z wyniku nie da się odtworzyć osoby
ani kluczem, ani rozsądnie prawdopodobnymi sposobami, np. zestawiając treść z innymi danymi.

Czy dane spseudonimizowane są danymi osobowymi dla odbiorcy, który nie ma klucza, jest kwestią sporną. Dotyczy jej wyrok Trybunału Sprawiedliwości UE z dnia 4 września 2025 r. w sprawie C-413/23 P (EIOD przeciwko SRB).
Wyrok wykłada rozporządzenie (UE) 2018/1725, ale jego definicja pseudonimizacji (art. 3 pkt 6) brzmi tak samo jak w RODO. Trybunał uznał, że dane spseudonimizowane nie są „w każdym wypadku i w odniesieniu do każdej osoby”
danymi osobowymi (pkt 86). Dla administratora, który ma dodatkowe informacje, zachowują ten charakter (pkt 76). Dla odbiorcy mogą go nie mieć, ale tylko gdy odbiorca nie jest w stanie znieść zastosowanych środków
i gdy środki te uniemożliwiają mu przypisanie danych osobie także innymi sposobami, takimi jak porównanie z innymi danymi (pkt 77). Obowiązki informacyjne administratora ocenia się z jego perspektywy,
w chwili zbierania danych, a więc przed jakimkolwiek przekazaniem (pkt 110–111).

Dla przesyłania dokumentów do usługi LLM wynika z tego, że brak tabeli powiązań u dostawcy sam nie czyni danych anonimowymi. Decyduje to, co zostało w treści – niezamaskowane wartości, rzadkie fakty, zestawienie ról,
miejsc i dat, które pozwala rozpoznać osobę pośrednio – oraz to, jakimi innymi danymi dysponuje odbiorca. Po stronie kancelarii dane pozostają osobowe i obowiązki z RODO dotyczą jej w pełnym zakresie.
Ostrożne podejście to traktować przesłanie dokumentu spseudonimizowanego jak przekazanie danych osobowych, dopóki analiza po stronie odbiorcy nie wykaże czegoś innego. Benchmark mierzy pierwszy z tych czynników:
ile wartości pozostaje w wyniku odczytywalnych, a identyfikację pośrednią pokazuje jako miarę opisową (rozdział „Wyniki”).

## Tajemnica zawodowa

Adwokat „obowiązany jest zachować w tajemnicy wszystko, o czym dowiedział się w związku z udzielaniem pomocy prawnej” (art. 6 ust. 1 ustawy z dnia 26 maja 1982 r. – Prawo o adwokaturze, Dz.U. z 2024 r. poz. 1564 ze zm.).
Obowiązek nie może być ograniczony w czasie, a adwokata nie można z niego zwolnić co do faktów, o których dowiedział się, udzielając pomocy prawnej lub prowadząc sprawę (art. 6 ust. 2 i 3). Analogicznie brzmi
art. 3 ust. 3–5 ustawy z dnia 6 lipca 1982 r. o radcach prawnych (Dz.U. z 2024 r. poz. 499 ze zm.).

Tajemnica obejmuje więcej niż dane osobowe: fakty sprawy, stanowisko i strategię klienta, informacje handlowe, treść korespondencji – także wtedy, gdy z dokumentu usunięto wszystko, co pozwala zidentyfikować osoby.
Anonimizacja danych osobowych zmniejsza zakres informacji, które trafiają do dostawcy, ale nie wyłącza tajemnicy w odniesieniu do pozostałej treści.

Raport nie rozstrzyga, czy przesłanie dokumentu do zewnętrznej usługi narusza tajemnicę. Ryzyko zależy od tego, kto u dostawcy ma dostęp do treści (personel, podwykonawcy), jak długo treść jest przechowywana,
czy służy do trenowania modeli, w jakiej jurysdykcji jest przetwarzana i jakie organy mogą żądać do niej dostępu, a także od zobowiązań do poufności, które przyjmuje dostawca. Ryzyko ograniczają m.in.:
umowa z zobowiązaniem do poufności i wyłączeniem trenowania na przesłanych treściach, przesyłanie tylko tego, co potrzebne do zadania, usunięcie danych identyfikujących i zbędnych faktów przed wysłaniem,
przetwarzanie najbardziej wrażliwych spraw lokalnie oraz wewnętrzne zasady korzystania z narzędzi AI. Ocena w konkretnej sprawie należy do prawnika, który ją prowadzi, z uwzględnieniem zasad etyki jego samorządu zawodowego.

## Tajemnica przedsiębiorstwa

Przez tajemnicę przedsiębiorstwa rozumie się „informacje techniczne, technologiczne, organizacyjne przedsiębiorstwa lub inne informacje posiadające wartość gospodarczą, które jako całość lub w szczególnym zestawieniu i zbiorze ich elementów nie są powszechnie znane osobom zwykle zajmującym się tym rodzajem informacji albo nie są łatwo dostępne dla takich osób, o ile uprawniony do korzystania z informacji lub rozporządzania nimi podjął, przy zachowaniu należytej staranności, działania w celu utrzymania ich w poufności”
(art. 11 ust. 2 ustawy z dnia 16 kwietnia 1993 r. o zwalczaniu nieuczciwej konkurencji, Dz.U. z 2026 r. poz. 85). Ujawnienie lub wykorzystanie takich informacji jest czynem nieuczciwej konkurencji w szczególności wtedy, gdy następuje bez zgody uprawnionego i z naruszeniem obowiązku
wynikającego z ustawy, czynności prawnej lub innego aktu (art. 11 ust. 1 i 4).

Wynikają z tego dwie rzeczy. Po pierwsze, dokumenty klientów zawierają informacje tego rodzaju – ceny, warunki handlowe, dane techniczne, plany – a narzędzia anonimizujące wykrywają przede wszystkim dane osobowe
i identyfikatory, nie tajemnicę handlową; o tym, które z takich informacji mogą trafić do zewnętrznej usługi, trzeba zdecydować osobno. Po drugie, ochrona zależy od tego, czy uprawniony z należytą starannością
dba o poufność, więc sposób korzystania z zewnętrznych usług przez niego i jego doradców może mieć znaczenie przy tej ocenie. Krąg osób, którym wolno udostępnić informacje, często określają też umowy o zachowaniu poufności.

## DORA: ryzyko ze strony dostawców usług ICT

Rozporządzenie (UE) 2022/2554 (DORA) stosuje się od 17 stycznia 2025 r. (art. 64) do podmiotów finansowych wymienionych w art. 2 ust. 1 lit. a–t, m.in. instytucji kredytowych, instytucji płatniczych, firm inwestycyjnych,
zakładów ubezpieczeń i pośredników ubezpieczeniowych. Kancelarii w tym katalogu nie ma.

Dla podmiotu finansowego zewnętrzna usługa LLM jest usługą ICT – usługą cyfrową lub usługą w zakresie danych świadczoną w sposób ciągły za pośrednictwem systemów ICT (art. 3 pkt 21) – a jej dostawca
zewnętrznym dostawcą usług ICT (art. 3 pkt 19). Podmiot finansowy zarządza ryzykiem ze strony takich dostawców jako elementem ryzyka związanego z ICT i przez cały czas ponosi pełną odpowiedzialność
za swoje obowiązki (art. 28 ust. 1 lit. a). Umowa z dostawcą wskazuje m.in. regiony lub kraje, w których świadczone są usługi i przetwarzane dane, oraz zawiera postanowienia o dostępności, autentyczności,
integralności i poufności danych, w tym osobowych (art. 30 ust. 2 lit. b i c). Bank czy zakład ubezpieczeń, którego dział prawny wysyła dokumenty do zewnętrznej usługi LLM, korzysta więc z usługi ICT objętej tymi wymogami.

## NIS2 i krajowy system cyberbezpieczeństwa

Dyrektywa (UE) 2022/2555 (NIS2) wymaga od podmiotów kluczowych i ważnych środków zarządzania ryzykiem, które obejmują m.in. „bezpieczeństwo łańcucha dostaw, w tym aspekty związane z bezpieczeństwem dotyczące stosunków
między każdym podmiotem a jego bezpośrednimi dostawcami lub usługodawcami” (art. 21 ust. 2 lit. d). Wymaga też zgłaszania poważnych incydentów: wczesne ostrzeżenie w ciągu dwudziestu czterech godzin, a zgłoszenie incydentu
w ciągu siedemdziesięciu dwóch godzin od powzięcia wiedzy o incydencie (art. 23 ust. 4 lit. a i b). Termin transpozycji upłynął 17 października 2024 r. (art. 41 ust. 1).

W Polsce dyrektywę wdraża ustawa z dnia 23 stycznia 2026 r. o zmianie ustawy o krajowym systemie cyberbezpieczeństwa oraz niektórych innych ustaw (Dz.U. z 2026 r. poz. 252), która weszła w życie 3 kwietnia 2026 r.
W nowym brzmieniu ustawy o krajowym systemie cyberbezpieczeństwa (KSC) podmiot kluczowy lub ważny zapewnia m.in. „bezpieczeństwo i ciągłość łańcucha dostaw produktów ICT, usług ICT i procesów ICT, od których zależy
świadczenie usługi” (art. 8 ust. 1 pkt 2 lit. e KSC) oraz zgłasza do właściwego CSIRT sektorowego wczesne ostrzeżenie o incydencie poważnym w ciągu dwudziestu czterech godzin, a sam incydent w ciągu siedemdziesięciu dwóch godzin
od jego wykrycia (art. 11 ust. 1 pkt 4 i 4a KSC). Ostatni tekst jednolity KSC (Dz.U. z 2026 r. poz. 20) ogłoszono przed tą nowelizacją.

Zewnętrzna usługa LLM, z której korzysta podmiot kluczowy lub ważny, należy do jego łańcucha dostaw usług ICT. Kancelaria zetknie się z tymi wymogami przede wszystkim wtedy, gdy sama jest takim podmiotem,
albo wtedy, gdy klient objęty KSC określa w umowie wymagania bezpieczeństwa wobec swoich dostawców.

## CRA: bezpieczeństwo samego narzędzia

Rozporządzenie (UE) 2024/2847 (akt o cyberodporności, CRA) nakłada wymagania na producentów produktów z elementami cyfrowymi, w tym oprogramowania instalowanego lokalnie. Producent projektuje i wytwarza produkt
zgodnie z zasadniczymi wymaganiami cyberbezpieczeństwa z załącznika I i przeprowadza ocenę ryzyka w cyberprzestrzeni (art. 13 ust. 1–2), a o aktywnie wykorzystywanych podatnościach zawiadamia CSIRT wyznaczony
na koordynatora i ENISA przez pojedynczą platformę sprawozdawczą (art. 14 ust. 1). Rozporządzenie stosuje się od 11 grudnia 2027 r., art. 14 – od 11 września 2026 r., a rozdział IV (jednostki notyfikowane) –
od 11 czerwca 2026 r. (art. 71 ust. 2). Kary za naruszenia określa prawo krajowe (art. 64 ust. 1).

Dla kancelarii, która wybiera lokalne narzędzie do anonimizacji, zgodność z CRA może być kryterium wyboru dostawcy: program przetwarza poufne dokumenty na komputerach kancelarii, więc jego podatności są ryzykiem dla tych dokumentów.

**Zgodność programu Privatizer by Legal Geek.** Jego producentem jest Legal Geek Sp. z o.o. Według dokumentów producenta z 20 października 2026 r. Privatizer nie należy do produktów ważnych ani krytycznych
(zał. III i IV CRA), więc zgodność wykazuje się procedurą kontroli wewnętrznej (moduł A, art. 32 ust. 1 lit. a), bez jednostki notyfikowanej. Pierwszą ocenę tą procedurą przeprowadzono 20 października 2026 r.
dla wariantu Windows; nie wykazała niespełnionych wymagań, a część elementów jest w trakcie wdrażania. Deklarację zgodności UE i oznakowanie CE producent zapowiada w 2027 r., gdy rozporządzenie zacznie być stosowane.
Obowiązki z art. 14 realizuje procedurą zgłaszania aktywnie wykorzystywanych podatności i poważnych incydentów, z CSIRT NASK jako koordynatorem i kanałem zgłoszeń `security@privatizer.ai`.
Dokumenty CRA producenta są wersją roboczą do weryfikacji przez prawnika.

## AI Act: klasyfikacja narzędzia do anonimizacji

Rozporządzenie (UE) 2024/1689 (AI Act), zmienione rozporządzeniem (UE) 2026/1744, stosuje się co do zasady od 2 sierpnia 2026 r., a jego rozdziały I i II – od 2 lutego 2025 r. (art. 113).
Lokalne narzędzie, które modelem uczenia maszynowego wykrywa dane osobowe w tekście, najpewniej jest systemem AI w rozumieniu art. 3 pkt 1: na podstawie danych wejściowych wnioskuje, jak generować wyniki, takie jak predykcje.

Systemem wysokiego ryzyka takie narzędzie co do zasady nie jest. Nie jest związanym z bezpieczeństwem elementem produktu objętego unijnym prawodawstwem harmonizacyjnym (art. 6 ust. 1), a anonimizacja dokumentów
nie należy do obszarów z załącznika III (art. 6 ust. 2); w obszarze wymiaru sprawiedliwości załącznik wymienia systemy wspomagające organ wymiaru sprawiedliwości w badaniu i interpretacji stanu faktycznego
i przepisów prawa oraz w stosowaniu prawa. Obowiązki przejrzystości z art. 50 dotyczą systemów wchodzących w bezpośrednią interakcję z osobami fizycznymi, generujących syntetyczne treści, rozpoznających emocje
lub kategoryzujących biometrycznie oraz treści typu deepfake. Narzędzie, które oznacza i maskuje dane w dokumencie użytkownika, co do zasady się w nich nie mieści. Ocena zależy jednak od przeznaczenia
i funkcji konkretnego narzędzia; inaczej trzeba by ocenić np. generowanie treści zastępczych modelem generatywnym.

Niezależnie od klasyfikacji narzędzia kancelarię dotyczy art. 4: dostawcy i podmioty stosujące systemy AI podejmują środki, które wspierają rozwój kompetencji w zakresie AI wśród personelu
(brzmienie nadane rozporządzeniem (UE) 2026/1744). Kancelaria, która w działalności zawodowej korzysta z narzędzia do anonimizacji albo z zewnętrznego modelu językowego, jest podmiotem stosującym (art. 3 pkt 4).
Nadzór nad rynkiem systemów AI w Polsce i kary za naruszenia rozporządzenia określa ustawa z dnia 3 lipca 2026 r. o systemach sztucznej inteligencji (Dz.U. z 2026 r. poz. 1003).
