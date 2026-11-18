# Podsumowanie

{% set wp = r.wersje['privatizer-tekst/tekst']['wersje'] %}{% set t = r.rankingi['tekst'] | sort(attribute='miejsce') %}{% set f = r.rankingi['pliki'] | sort(attribute='miejsce') %}
{% set pt = wiersz(r, 'tekst', 'privatizer-tekst') %}{% set pm = wiersz(r, 'tekst', 'privatizer-model') %}{% set pf = wiersz(r, 'pliki', 'privatizer-plik') %}
{% set t2 = (t | rejectattr('uczestnik', 'equalto', 'privatizer-tekst') | list)[0] %}{% set f2 = (f | rejectattr('uczestnik', 'equalto', 'privatizer-plik') | list)[0] %}
{% set porz = {1: 'pierwszy', 2: 'drugi', 3: 'trzeci', 4: 'czwarty', 5: 'piąty'} %}
Raport porównuje narzędzia do anonimizacji dokumentów na wspólnym korpusie dokumentów, w jednej metodyce zamrożonej <span style="white-space:nowrap">{{ m.daty.zamrozenie }}</span>.
Mierzono Privatizera by Legal Geek w wersji {{ wp.aplikacja }} z modelem Legal Geek Privatizer (RC) {{ wp.model_wersja }}, w trybie domyślnym. Pomiar szybkości `privatizer-tekst` pochodzi z dwóch sesji
(<span style="white-space:nowrap">{{ m.daty.czas_sesja_1 }}</span> i <span style="white-space:nowrap">{{ m.daty.czas_sesja_2 }}</span>); dwie sesje dotyczą tylko tego uczestnika. Autor raportu jest producentem jednego z porównywanych narzędzi (rozdział „Ograniczenia”).

{{ tabela('podsumowanie') }}

{{ wykres('podsumowanie') }}

1. **Ranking tekstu.** `privatizer-tekst` ma {{ liczba(pt.suma) }} pkt {{ przedzial(pt.suma_ci) }} z {{ liczba(maks_punktow('tekst'), 0) }} możliwych i zajmuje miejsce {{ pt.miejsce }}; z pozostałych uczestników najwyższą sumę ma `{{ t2.uczestnik }}` ({{ porz.get(t2.miejsce, 'miejsce ' ~ t2.miejsce) }} w kolejności):
   {{ liczba(t2.suma) }} pkt {{ przedzial(t2.suma_ci) }}. Privatizer ma o {{ liczba((pt.suma - t2.suma) | abs) }} pkt {% if pt.suma >= t2.suma %}więcej{% else %}mniej{% endif %}, a przedziały ufności {% if pt.suma_ci[0] > t2.suma_ci[1] or t2.suma_ci[0] > pt.suma_ci[1] %}nie nachodzą na siebie{% else %}nachodzą na siebie{% endif %}.
   {% if pt.remis_z %}Remis statystyczny ma z: {{ pt.remis_z | join(', ') }}.{% else %}Privatizer nie ma remisu statystycznego z żadnym innym uczestnikiem rankingu.{% endif %}
2. **Ranking plików i wycieki w dokumentach.** `privatizer-plik` ma {{ liczba(pf.suma) }} pkt {{ przedzial(pf.suma_ci) }} z {{ liczba(maks_punktow('pliki'), 0) }} możliwych i zajmuje miejsce {{ pf.miejsce }}; z pozostałych uczestników najwyższą sumę ma `{{ f2.uczestnik }}` ({{ porz.get(f2.miejsce, 'miejsce ' ~ f2.miejsce) }} w kolejności):
   {{ liczba(f2.suma) }} pkt {{ przedzial(f2.suma_ci) }}. Privatizer ma o {{ liczba((pf.suma - f2.suma) | abs) }} pkt {% if pf.suma >= f2.suma %}więcej{% else %}mniej{% endif %}, a przedziały {% if pf.suma_ci[0] > f2.suma_ci[1] or f2.suma_ci[0] > pf.suma_ci[1] %}nie nachodzą na siebie{% else %}nachodzą na siebie{% endif %}.
   Ranking plików obejmuje {{ liczba(f | length, 0) }} uczestników.
   Ścieżka plikowa Privatizera ma wyciek w {{ liczba(pf.z_wyciekiem, 0) }} z {{ liczba(pf.dokumenty, 0) }} dokumentów ({{ procent(pf.z_wyciekiem / pf.dokumenty, 0) }}; wyciek to choć jedna wartość, także kwota, której tryb domyślny nie maskuje), a uczestnik o najwyższej sumie spośród pozostałych w rankingu plików, `{{ f2.uczestnik }}`
   – w {{ liczba(f2.z_wyciekiem, 0) }} z {{ liczba(f2.dokumenty, 0) }} ({{ procent(f2.z_wyciekiem / f2.dokumenty, 0) }}).
   Dokument nieprzetworzony, z błędem albo z odmową liczy się jako wyciek (fail-closed), więc te wartości obejmują także dokumenty, których narzędzie nie obsłużyło.
   Formaty spoza zakresu deklarowanego przez narzędzie: {% for w in f | rejectattr('uczestnik', 'equalto', 'privatizer-plik') | list %}`{{ w.uczestnik }}` – {{ liczba(w.nieobslugiwane, 0) }} z {{ liczba(w.dokumenty, 0) }} dokumentów{% if not loop.last %}, {% else %}; {% endif %}{% endfor %}`privatizer-plik` – {{ liczba(pf.nieobslugiwane, 0) }}.
   W `privatizer-plik` odmów jest {{ liczba(pf.odmowy, 0) }}, a błędów {{ liczba(pf.bledy, 0) }}; wszystkie są policzone jako wyciek.
3. **Silnik na tekście, nie sam model.** Silnik na tekście zdobywa o {{ liczba((pt.suma - pm.suma) | abs) }} pkt {% if pt.suma >= pm.suma %}więcej{% else %}mniej{% endif %} niż sam model Legal Geek Privatizer (RC)
   (`privatizer-model`: {{ liczba(pm.suma) }} pkt {{ przedzial(pm.suma_ci) }}), a przedziały {% if pt.suma_ci[0] > pm.suma_ci[1] or pm.suma_ci[0] > pt.suma_ci[1] %}nie nachodzą na siebie{% else %}nachodzą na siebie{% endif %}.

{% set sz = pozycja_szybkosci(r, 'pliki', 'privatizer-plik') %}{% set kwoty = porownanie_trybow(r) | selectattr('ranking', 'equalto', 'tekst') | list %}
{% set wk = kwoty | selectattr('wiersz', 'equalto', 'Wyciekłe wartości') | list %}{% set kw = kwoty | selectattr('wiersz', 'equalto', 'w tym kwoty') | list %}{% set dk = kwoty | selectattr('wiersz', 'equalto', 'Dokumenty z wyciekiem') | list %}
{% set mniej_wyciekow = t | rejectattr('uczestnik', 'equalto', 'privatizer-tekst') | selectattr('z_wyciekiem', 'lt', pt.z_wyciekiem) | list %}
{% if sz %}**Szybkość i przegrane.** Ścieżka plikowa Privatizera przetwarza {{ liczba(sz.s_na_strone, 2) }} s na stronę, czyli zajmuje {{ sz.miejsce }}. miejsce pod względem szybkości wśród {{ liczba(sz.z, 0) }} uczestników rankingu plików z pomiarem czasu,
i zdobywa {{ liczba(sz.pkt) }} z {{ liczba(sz.maks, 0) }} pkt w teście szybkości (P7). {% endif %}Wycinki, w których inny uczestnik ma lepszy wynik niż Privatizer, wylicza sekcja „Gdzie Privatizer przegrywa” w rozdziale „Wyniki”: w rankingu tekstu {{ ile(liczba_przewag(r, 'test', 'tekst'), 'test', 'testy', 'testów') }}, w rankingu plików {{ ile(liczba_przewag(r, 'test', 'pliki'), 'test', 'testy', 'testów') }}, a ponadto języki, formaty, typy dokumentów, kategorie i miejsca w dokumencie.
{% if mniej_wyciekow and wk and kw and dk and wk[0].domyslny is not none and kw[0].domyslny is not none %}Udział dokumentów z wyciekiem w rankingu tekstu jest u `privatizer-tekst` wyższy niż u {% for w in mniej_wyciekow %}`{{ w.uczestnik }}`{% if not loop.last %}, {% endif %}{% endfor %} ({{ procent(pt.z_wyciekiem / pt.dokumenty, 0) }} wobec {% for w in mniej_wyciekow %}{{ procent(w.z_wyciekiem / w.dokumenty, 0) }}{% if not loop.last %}, {% endif %}{% endfor %}),
głównie dlatego, że tryb domyślny nie maskuje kwot, a kwoty są w zakresie gold: wyciekłych wartości jest {{ liczba(wk[0].domyslny, 0) }}, z czego kwot {{ liczba(kw[0].domyslny, 0) }}{% if dk and dk[0].maks is not none %}; w trybie „Maksymalna ochrona” dokumentów z wyciekiem jest {{ liczba(dk[0].maks, 0) }} z {{ liczba(pt.dokumenty, 0) }}{% endif %}.{% endif %}

Wyniki dotyczą trybu domyślnego, korpusu i metodyki opisanych w raporcie; Privatizera mierzono bez kalibracji progów na części dev, a „Maksymalna ochrona” i warianty z aneksu liczbowego (osobny dokument) nie mają miejsc w rankingach.
Ograniczenia wyników – w tym pozycję autora, dobór korpusu i konfiguracje uczestników – opisuje rozdział „Ograniczenia”.
