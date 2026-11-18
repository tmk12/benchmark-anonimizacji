# Wdrożenie

Rozdział opisuje, gdzie i jak działają narzędzia z benchmarku, ile zasobów zajmują na maszynie referencyjnej i co trzeba sprawdzić przy wyborze. Nie zawiera ocen jakości poza tym, co pokazują rankingi.
{% set c = m.czas %}
## Gdzie przetwarzany jest dokument

Narzędzia do anonimizacji dzielą się ze względu na to, gdzie trafia dokument.

- **Aplikacja lokalna.** Privatizer by Legal Geek jest programem na komputer (Windows i macOS z procesorem Apple Silicon), który przetwarza dokumenty lokalnie, na procesorze komputera użytkownika. Wewnętrznie ma lokalny serwer
  z interfejsem programistycznym (API); w benchmarku `privatizer-tekst` i `privatizer-plik` wołają to samo API co interfejs programu. Aplikacja czyta i zapisuje pliki wielu formatów i zwraca gotowy plik.
- **Biblioteki i modele otwarte.** Uczestnicy grup A i B to biblioteki i modele, które integrator uruchamia we własnym kodzie, na własnym komputerze lub serwerze. Dostarczają zwykle wykrywanie danych w tekście;
  obsługę plików (wyciągnięcie tekstu, podmiana, zapis, czyszczenie metadanych) trzeba dobudować. Ilustruje to naiwny wrapper z grupy B: pokazuje, co zostaje w pliku, gdy anonimizuje się tylko tekst akapitów i komórek
  (nagłówki, stopki, przypisy, komentarze, śledzone zmiany, notatki i metadane pozostają poza zasięgiem takiego kodu). Wrapper nie jest produktem ani oceną Presidio.
- **Usługi chmurowe.** Istnieją także usługi dostawców chmurowych (m.in. Google Cloud Sensitive Data Protection oraz usługi analogiczne u innych dostawców chmurowych). W tym benchmarku usługi chmurowe są tylko opisane:
  nie mierzono ich ani nie punktowano, a raport nie zawiera ani wyników, ani twierdzeń o ich jakości. Przesłanie dokumentu do zewnętrznej usługi jest samo w sobie przekazaniem danych dostawcy.
  Jego ocena zależy m.in. od tajemnicy zawodowej, od miejsca przetwarzania (przekazywanie danych poza Europejski Obszar Gospodarczy w rozumieniu RODO) i od wymogów wobec dostawców usług ICT (DORA, NIS2);
  przepisy opisuje rozdział „Dlaczego to ważne”.

## Zasoby: start i pamięć

Poniższa tabela podaje czas startu (uruchomienie procesu i załadowanie modelu, poza czasem przetwarzania) i szczytową pamięć uczestników zmierzone na maszynie referencyjnej (Apple M1, {{ liczba(c.ram_gb, 0) }} GB RAM).
Pamięć to suma pamięci procesów uczestnika (macOS: `phys_footprint`, strony brudne i skompresowane), próbkowana co sekundę. Kolumna „Dokumenty” podaje liczbę dokumentów próbki, które uczestnik obsługuje;
dla narzędzi plikowych reszta próbki jest poza ich deklaracją formatów. Czas przetwarzania i punkty szybkości są w rozdziale „Wyniki”.

| Uczestnik | Poziom | Dokumenty | Start [s] | Szczyt pamięci [MB] |
|---|---|---|---|---|
{% for x in czas_podsumowanie_wg_pamieci(r) %}| `{{ x.uczestnik }}` | {{ x.poziom }} | {{ liczba(x.dokumenty, 0) }} | {{ liczba(x.start_s, 1) }} | {{ liczba(x.szczyt_mb, 0) }} |
{% endfor %}
{% set wysoka = pamiec_wysoka(r) %}{% if wysoka %}Szczyt pamięci powyżej {{ procent(c.prog_pamieci, 0) }} pamięci RAM maszyny ({{ liczba(c.prog_pamieci * c.ram_mb, 0) }} MB) mają: {% for x in wysoka %}`{{ x.uczestnik }}`{% if not loop.last %}, {% endif %}{% endfor %}.
Przy takim zapotrzebowaniu pamięć maszyny jest bliska limitu, co mogło wpływać na czas; szczegóły i ograniczenia pomiaru opisuje aneks ujawnień.{% endif %}

## Pochodzenie narzędzi i modeli

Narzędzie do ochrony danych pobrane z niezweryfikowanego źródła samo może stać się wektorem wycieku. W benchmarku modele i narzędzia pochodzą z oficjalnych repozytoriów i mają przypiętą rewizję;
w wariantach z obcym modelem suma kontrolna wag jest dodatkowo sprawdzana przy starcie. Przykładem jest OpenAI Privacy Filter. Oficjalne źródło to repozytorium `openai/privacy-filter` w serwisie Hugging Face (organizacja zweryfikowana, licencja Apache-2.0),
a kod – repozytorium `openai/privacy-filter` w serwisie GitHub (licencja Apache-2.0); w benchmarku użyto przypiętej rewizji i sumy pliku wag.

Według analizy firmy HiddenLayer (7 maja 2026), potwierdzonej przez BleepingComputer i The Hacker News, w serwisie Hugging Face pojawiło się złośliwe repozytorium `Open-OSS/privacy-filter`, podszywające się pod to wydanie
(karta modelu skopiowana niemal dosłownie). Zawierało skrypt uruchamiający, który udawał kod uczenia maszynowego, wyłączał weryfikację SSL i pobierał oprogramowanie kradnące dane: dane przeglądarek, hasła, sesje,
portfele kryptowalut i poświadczenia SSH i FTP. Celem był system Windows. Serwis Hugging Face potwierdził naruszenie regulaminu i usunął repozytorium. Autorzy analizy zalecają, by host, który uruchomił te pliki,
traktować jako w pełni przejęty. Wniosek dotyczy każdego narzędzia pobieranego z publicznych repozytoriów, nie konkretnego produktu: należy weryfikować wydawcę, przypinać rewizje i sprawdzać sumy kontrolne.

Źródła: HiddenLayer, 7 maja 2026 (aktualizacja 8 maja 2026) <https://www.hiddenlayer.com/research/malware-found-in-trending-hugging-face-repository-open-oss-privacy-filter>; BleepingComputer, 9 maja 2026 <https://www.bleepingcomputer.com/news/security/fake-openai-repository-on-hugging-face-pushes-infostealer-malware/>; The Hacker News, maj 2026 <https://thehackernews.com/2026/05/fake-openai-privacy-filter-repo-hits-1.html>.

Kontekst regulacyjny: CRA (łańcuch dostaw komponentów), NIS2 i KSC (bezpieczeństwo łańcucha dostaw), DORA (ryzyko ICT stron trzecich); przepisy opisuje rozdział „Dlaczego to ważne”.

## Format pliku wynikowego Privatizera

Privatizer czyta stare formaty binarne Office (DOC, XLS, PPT) i RTF własnymi czytnikami i zapisuje je jako DOCX, XLSX i PPTX. To świadoma decyzja projektowa o charakterze kompromisu. Producent uzasadnia ją tym, że bezpieczna edycja w miejscu binarnego pliku OLE, bez LibreOffice i Office, grozi pozostawieniem fragmentów oryginału w nieużywanych sektorach pliku, a format OOXML pozwala, by w wyniku była tylko zanonimizowana treść, i objąć kontrolą fail-closed całą paczkę. Wiadomości MSG program zapisuje jako TXT
(nagłówki i treść); załączniki MSG nie są przenoszone, a program ostrzega o tym użytkownika. Wiadomości EML z załącznikami program odrzuca z komunikatem, że nie anonimizuje załączników.
Są to ograniczenia funkcjonalne: format wyjścia różni się od wejściowego, a załączniki wymagają osobnego przetworzenia.

W benchmarku zamiana formatu nie jest błędem ani wyciekiem; składnik „zachowanie struktury” w teście integralności (P4) jest wtedy „nie dotyczy”.
{% set pp = wiersz(r, 'pliki', 'privatizer-plik') %}{% if pp %}W rankingu plików format wyjścia zmieniono w {{ ile(pp.format_zmieniony, 'dokumencie', 'dokumentach', 'dokumentach') }} z {{ liczba(pp.dokumenty, 0) }}, a odmowę przetworzenia zgłoszono dla {{ ile(pp.odmowy, 'dokumentu', 'dokumentów', 'dokumentów') }}.
Odmowa jest w rankingu liczona jak wyciek (fail-closed) i pokazana osobno.{% endif %}

## Pytania przy wyborze narzędzia

Wyniki rankingów odpowiadają na część pytań. Pozostałe warto zadać dostawcy lub sprawdzić samemu:

- gdzie i na jakim sprzęcie dokument jest przetwarzany i kto ma do niego dostęp w trakcie;
- jakie formaty narzędzie przyjmuje, co zwraca (format wyjścia, załączniki, metadane) i co robi z dokumentem, którego nie obsługuje;
- czy anonimizacja obejmuje całą zawartość pliku, a nie tylko tekst akapitów: nagłówki, stopki, przypisy, komentarze, śledzone zmiany, metadane (ranking plików);
- skąd pochodzi model, jak jest weryfikowany i jak są dostarczane aktualizacje;
- ile pamięci i czasu narzędzie potrzebuje na docelowym sprzęcie.
