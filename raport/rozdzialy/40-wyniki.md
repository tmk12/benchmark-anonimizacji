# Wyniki

Rankingi mierzą **tryb domyślny** Privatizera (świeża instalacja, czułość „zrównoważona”, kategoria `KWOTA` wyłączona). Tryb „Maksymalna ochrona” i warianty
z aneksu liczbowego (osobny dokument; potok z obcym modelem, same reguły, Presidio z modelem Legal Geek Privatizer (RC)) są pokazane osobno i nie mają miejsc w rankingach.
Ranking tekstu liczy {{ liczba(r.rankingi['tekst']|length, 0) }} uczestników i {{ liczba(maks_punktow('tekst'), 0) }} punktów możliwych do zdobycia,
ranking plików – {{ liczba(r.rankingi['pliki']|length, 0) }} uczestników i {{ liczba(maks_punktow('pliki'), 0) }} punktów. Przy sumach podano przedział
ufności (bootstrap); uczestnicy, których przedziały się nie rozdzielają, mają wspólną etykietę miejsca z dopiskiem „remis”. Wartość nieliczona jest zapisana jako „n/d”.

## Ranking tekstu

{% set t = r.rankingi['tekst'] | sort(attribute='miejsce') %}{% set p1 = t[0] %}{% set p2 = t[1] %}{% set p3 = t[2] %}
Pierwsze miejsce zajmuje `{{ p1.uczestnik }}` z sumą {{ liczba(p1.suma) }} pkt {{ przedzial(p1.suma_ci) }}, drugie – `{{ p2.uczestnik }}`
({{ liczba(p2.suma) }} pkt {{ przedzial(p2.suma_ci) }}), trzecie – `{{ p3.uczestnik }}` ({{ liczba(p3.suma) }} pkt {{ przedzial(p3.suma_ci) }}).
Różnica między pierwszym a drugim miejscem to {{ liczba(p1.suma - p2.suma) }} pkt; przedziały ufności
{% if p1.suma_ci[0] > p2.suma_ci[1] %}nie nachodzą na siebie{% else %}nachodzą na siebie{% endif %}.
{% set remisy = t | selectattr('remis_z') | list %}{% if remisy %}Remis statystyczny z co najmniej jednym innym uczestnikiem ma {{ liczba(remisy|length, 0) }} z {{ liczba(t|length, 0) }} uczestników rankingu.{% else %}Żaden uczestnik rankingu nie ma remisu statystycznego.{% endif %}

{{ wykres('ranking_tekst') }}

{{ tabela('ranking', 'tekst') }}

Składniki sum – punkty za poszczególne testy – pokazuje poniższy wykres; test bez pomiaru nie ma odcinka, tylko adnotację „n/d”.

{{ wykres('skladniki_tekst') }}

## Ranking plików

{% set tp = r.rankingi['pliki'] | sort(attribute='miejsce') %}{% set f1 = tp[0] %}{% set f2 = tp[1] %}{% set f3 = tp[2] %}{% set f4 = tp[3] %}
Pierwsze miejsce zajmuje `{{ f1.uczestnik }}` ({{ liczba(f1.suma) }} pkt {{ przedzial(f1.suma_ci) }}), drugie – `{{ f2.uczestnik }}` ({{ liczba(f2.suma) }} pkt),
trzecie – `{{ f3.uczestnik }}` ({{ liczba(f3.suma) }} pkt), czwarte – `{{ f4.uczestnik }}` ({{ liczba(f4.suma) }} pkt).
{% set nd5 = [] %}{% for w in tp %}{% if w.testy['P5'].pkt is none %}{% set _ = nd5.append(w.uczestnik) %}{% endif %}{% endfor %}
{% if nd5 %}Test P5 (brak nadmiarowego maskowania) jest nieliczony dla: {% for u in nd5 %}`{{ u }}`{% if not loop.last %}, {% endif %}{% endfor %} – według prerejestracji nie dotyczy.
{% if f3.uczestnik in nd5 or f4.uczestnik in nd5 %}Maksymalna wartość P5 to {{ liczba(wagi_testow()['P5'], 0) }} pkt, a różnica sum miejsc trzeciego i czwartego wynosi {{ liczba(f3.suma - f4.suma) }} pkt,
więc {% if f3.suma - f4.suma > wagi_testow()['P5'] %}kolejność tych miejsc nie zależy od brakującego P5{% else %}brak P5 mógłby zmienić kolejność tych miejsc{% endif %}.{% endif %}{% endif %}

{{ wykres('ranking_pliki') }}

{{ tabela('ranking', 'pliki') }}

{{ wykres('skladniki_pliki') }}

## Identyfikacja pośrednia

Identyfikacja pośrednia jest osobną miarą opisową, poza punktami: nie wpływa na T1–T6 ani na P1–P7 i nie zmienia miejsc w rankingach. Mierzy, czy narzędzie w ogóle rusza informacje, które pośrednio wskazują osobę, choć nie jest ona nigdzie nazwana; w warstwie trudnej jest na to
{{ ile(m.korpus.przypadki_posrednie, 'przypadek', 'przypadki', 'przypadków') }}. Wynik to odsetek przerwanych kombinacji informacji z przedziałem ufności (bootstrap po dokumentach).
„Przerwana” to warunek konieczny ochrony, nie wystarczający: zamaskowanie samej funkcji przy nazwie firmy przerywa kombinację, choć czytelnik może domyślić się reszty z kontekstu.

### Ranking tekstu

{{ tabela('posrednie', 'tekst') }}

### Ranking plików

{{ tabela('posrednie', 'pliki') }}

## Rozbicia

Odsetki w tabelach to udział dokumentów bez wycieku (ważony kategorią, jak T1 i P1) albo – dla kategorii i miejsc w dokumencie – odsetek wyciekłych wartości.
Kolumny są ułożone w kolejności miejsc w rankingu; kolumna „Dok.” podaje liczność wycinka.

### Języki

{{ wykres('jezyki') }}

{{ tabela('per', 'jezyk', 'tekst') }}

{{ tabela('per', 'jezyk', 'pliki') }}

### Formaty

{{ tabela('per', 'format', 'tekst') }}

{{ tabela('per', 'format', 'pliki') }}

### Typy dokumentów

{{ tabela('per', 'typ', 'tekst') }}

### Kategorie danych

Mapa pokazuje odsetek wyciekłych wartości w kategoriach, w których {{ ile(n_kategorie, 'najlepszy uczestnik', 'najlepszych uczestników', 'najlepszych uczestników') }} rankingu tekstu wyciekło najwięcej; pełna tabela jest w osobnym dokumencie „Aneks liczbowy”, publikowanym razem z raportem.

{{ wykres('kategorie') }}

### Miejsca w dokumencie

{{ tabela('per', 'miejsce', 'tekst') }}

## Trudne przypadki

Trudne przypadki to osobna warstwa korpusu (T3 w rankingu tekstu, P3 w rankingu plików). Tabele zestawiają Privatizera z najlepszym z pozostałych uczestników rankingu
w każdym przypadku; przypadki oznaczone „poza punktacją” nie wchodzą do sum.

{{ tabela('trudne_przypadki', 'tekst') }}

{{ tabela('trudne_przypadki', 'pliki') }}

## Szybkość

Szybkość to mediana czasu na stronę obliczeniową na maszynie referencyjnej (Apple M1); punkty T6 i P7 wynikają ze stałej wartości odniesienia `t_ref`, niezależnej
od pozostałych uczestników. Warianty z aneksu liczbowego nie mają pomiaru czasu, więc nie mają też punktów szybkości. Kolumny z innymi wartościami `t_ref` to analiza wrażliwości, bez wpływu na sumy.

{{ wykres('szybkosc') }}

{{ tabela('szybkosc', 'tekst') }}

{{ tabela('szybkosc', 'pliki') }}

## Wrażliwość na wagi

{% set zestawy = r.wrazliwosc | map(attribute='zestaw') | unique | list %}Kolejność uczestników sprawdzono przy {{ liczba(zestawy|length, 0) }} alternatywnych zestawach wag testów: {% for z in zestawy %}{{ zestawy_wag[z] }}{% if not loop.last %}, {% endif %}{% endfor %}.
{% for rk, nazwa in (('tekst', 'tekstu'), ('pliki', 'plików')) %}{% set liderzy = r.wrazliwosc | selectattr('ranking', 'equalto', rk) | selectattr('miejsce', 'equalto', 1) | map(attribute='uczestnik') | list %}
W rankingu {{ nazwa }} pierwsze miejsce {% if liderzy | unique | list | length == 1 %}we wszystkich {{ liczba(liderzy|length, 0) }} zestawach wag zajmuje `{{ liderzy[0] }}`{% else %}zależy od wag: zajmują je {% for u in liderzy | unique %}`{{ u }}`{% if not loop.last %}, {% endif %}{% endfor %}{% endif %}.
{% endfor %}
{% set zmiany = r.wrazliwosc | selectattr('ranking', 'equalto', 'tekst') | rejectattr('miejsce', 'equalto', none) | list %}
{% set rozne = zmiany | selectattr('miejsce_domyslne') | list %}
{% set przesuniete = [] %}{% for x in rozne %}{% if x.miejsce != x.miejsce_domyslne %}{% set _ = przesuniete.append(x.uczestnik) %}{% endif %}{% endfor %}
Porównanie numerów miejsc (bez etykiet remisu): w którymś zestawie wag inny numer miejsca niż w rankingu głównym ma {{ liczba(przesuniete | unique | list | length, 0) }} z {{ liczba(t|length, 0) }} uczestników rankingu tekstu.

{{ tabela('wrazliwosc', 'tekst') }}

{{ tabela('wrazliwosc', 'pliki') }}

## Porównanie trybów

Tryb „Maksymalna ochrona” (czułość modelu, kwoty pieniężne) mierzono osobno; wyniki są w aneksie liczbowym. Układ porównania: kolumny – tryb domyślny i „Maksymalna ochrona”, wiersze – wyciek ogółem,
w tym kwoty, wyciek bez kwot i dokumenty z wyciekiem.
{% set tryb_t = wiersz(r, 'tekst', 'privatizer-tekst') %}{% set maks_t = wiersz(r, 'tekst', 'privatizer-tekst-maks') %}
W rankingu tekstu dokumentów z wyciekiem jest {{ liczba(tryb_t.z_wyciekiem, 0) }} w trybie domyślnym i {{ liczba(maks_t.z_wyciekiem, 0) }} w trybie „Maksymalna ochrona”
(na {{ liczba(tryb_t.dokumenty, 0) }} dokumentów); suma punktów bez testu szybkości (którego tryb „Maksymalna ochrona” nie ma) wynosi odpowiednio {{ liczba(suma_bez_szybkosci(tryb_t, 'tekst')) }} i {{ liczba(suma_bez_szybkosci(maks_t, 'tekst')) }}.
Zakres gold jest ten sam w obu trybach i obejmuje kategorię `KWOTA`; tryb domyślny jej nie maskuje, a „Maksymalna ochrona” tak, dlatego wiersz „w tym kwoty” pokazuje ją osobno.
{% set tryb_p = wiersz(r, 'pliki', 'privatizer-plik') %}{% set maks_p = wiersz(r, 'pliki', 'privatizer-plik-maks') %}{% set bk = porownanie_trybow(r) | selectattr('ranking', 'equalto', 'pliki') | selectattr('wiersz', 'equalto', 'Wyciek bez kwot') | list %}
{% if bk and tryb_p and maks_p and bk[0].maks is not none and bk[0].domyslny is not none and bk[0].maks > bk[0].domyslny %}W rankingu plików wyciek wartości innych niż kwoty jest w trybie „Maksymalna ochrona” większy ({{ liczba(bk[0].maks, 0) }}) niż w trybie domyślnym ({{ liczba(bk[0].domyslny, 0) }}),
mimo że tryb ten maskuje więcej. W trybie „Maksymalna ochrona” błędów przetwarzania jest {{ liczba(maks_p.bledy, 0) }}, w trybie domyślnym {{ liczba(tryb_p.bledy, 0) }}; dokument z błędem liczy się jako wyciek wszystkich jego wartości (fail-closed),
więc różnica błędów jest możliwą przyczyną tego wyniku. Zagregowane dane nie rozdzielają wycieku według dokumentów z błędem, więc udziału tej przyczyny nie wyznaczono.{% endif %}

{{ wykres('tryby') }}

{{ tabela('tryby', 'tekst') }}

{{ tabela('tryby', 'pliki') }}

## Aplikacja a gołe modele

Warianty z aneksu liczbowego rozdzielają wkład modelu i potoku aplikacji: ten sam model uruchomiony samodzielnie, w Presidio i w potoku Privatizera. Warianty nie mają pomiaru czasu,
więc suma w tej tabeli jest liczona bez T6 u wszystkich uczestników.

{{ tabela('aplikacja_vs_modele', 'tekst') }}

{% macro porownanie(potok, solo) -%}
{% set a = wiersz(r, 'tekst', potok) %}{% set b = wiersz(r, 'tekst', solo) %}{% set d = suma_bez_szybkosci(a) - suma_bez_szybkosci(b) %}{% set d5 = a.testy['T5'].pkt - b.testy['T5'].pkt %}{% set d1 = a.testy['T1'].pkt - b.testy['T1'].pkt -%}
Potok `{{ potok }}` zdobywa {% if d > 0 %}więcej{% elif d < 0 %}mniej{% else %}tyle samo{% endif %} punktów niż `{{ solo }}` (suma bez T6: {{ liczba(suma_bez_szybkosci(a)) }} wobec {{ liczba(suma_bez_szybkosci(b)) }}, różnica {{ liczba(d | abs) }} pkt).
W T1 różnica wynosi {{ liczba(d1 | abs) }} pkt {% if d1 > 0 %}na korzyść potoku{% elif d1 < 0 %}na korzyść modelu samodzielnego{% else %}(wynik równy){% endif %}, a w T5 (brak nadmiarowego maskowania) {{ liczba(d5 | abs) }} pkt {% if d5 > 0 %}na korzyść potoku{% elif d5 < 0 %}na korzyść modelu samodzielnego{% else %}(wynik równy){% endif %}.
{%- endmacro %}

{% set lgp = wiersz(r, 'tekst', 'privatizer-tekst') %}{% set gola = wiersz(r, 'tekst', 'privatizer-model') %}{% set presidio = wiersz(r, 'tekst', 'presidio-lgp') %}{% set reguly = wiersz(r, 'tekst', 'privatizer-reguly') %}
Model Legal Geek Privatizer (RC) bez potoku (`privatizer-model`) ma sumę bez T6 równą {{ liczba(suma_bez_szybkosci(gola)) }} pkt, ten sam model w Presidio (`presidio-lgp`) – {{ liczba(suma_bez_szybkosci(presidio)) }} pkt,
same reguły bez modelu (`privatizer-reguly`) – {{ liczba(suma_bez_szybkosci(reguly)) }} pkt, a pełny potok aplikacji (`privatizer-tekst`) – {{ liczba(suma_bez_szybkosci(lgp)) }} pkt.

{{ porownanie('privatizer-tekst-gliner', 'gliner-nvidia-pii') }}

{{ porownanie('privatizer-tekst-opf', 'openai-privacy-filter') }}

Obcy model w potoku Privatizera nie ma kalibracji Privatizera (progi kategorii, tryby czułości, taksonomia etykiet prawniczych), a potok był strojony pod model Legal Geek Privatizer (RC):
różnice między potokiem a modelem samodzielnym opisują wkład potoku, a nie ogólną jakość żadnego z modeli.

## Miary pomocnicze

Poza punktami raport podaje dwie miary pomocnicze: wynik liczony tylko w kategoriach, które uczestnik deklaruje, oraz tylko w jego językach oficjalnych.
{% set njez = r.per['jezyk'] | map(attribute='jezyk') | unique | list | length %}Nagłówek rankingu uwzględnia wszystkie {{ ile(njez, 'język', 'języki', 'języków') }} korpusu; zgodnie z protokołem każdy uczestnik dostaje każdy dokument.

{{ tabela('w_zakresie', 'tekst') }}

{{ tabela('w_zakresie', 'pliki') }}

## Gdzie Privatizer przegrywa

Poniższe tabele wyliczono z danych: wymieniają wycinki (testy, języki, formaty, typy dokumentów, kategorie, miejsca w dokumencie, szybkość), w których najlepszy z pozostałych uczestników rankingu
(bez wariantów Privatizera) ma lepszy wynik niż Privatizer w trybie domyślnym. Wycinek, w którym Privatizer jest najlepszy lub równy, w tabeli się nie pojawia.
{% for rk, nazwa in (('tekst', 'tekstu'), ('pliki', 'plików')) %}
W rankingu {{ nazwa }} Privatizer ma gorszy wynik niż najlepszy inny uczestnik w: {{ ile(liczba_przewag(r, 'test', rk), 'teście', 'testach', 'testach') }}, {{ ile(liczba_przewag(r, 'jezyk', rk), 'języku', 'językach', 'językach') }}, {{ ile(liczba_przewag(r, 'format', rk), 'formacie', 'formatach', 'formatach') }}, {{ ile(liczba_przewag(r, 'typ', rk), 'typie dokumentu', 'typach dokumentów', 'typach dokumentów') }}, {{ ile(liczba_przewag(r, 'kategoria', rk), 'kategorii', 'kategoriach', 'kategoriach') }}, {{ ile(liczba_przewag(r, 'miejsce', rk), 'miejscu w dokumencie', 'miejscach w dokumencie', 'miejscach w dokumencie') }}, {{ ile(liczba_przewag(r, 'szybkosc', rk), 'pomiarze szybkości', 'pomiarach szybkości', 'pomiarach szybkości') }} (n/d – brak danych tego wymiaru w rankingu).
{% endfor %}

### Ranking tekstu

{{ tabela('przegrywa', 'test', 'tekst') }}

{{ tabela('przegrywa', 'szybkosc', 'tekst') }}

{{ tabela('przegrywa', 'jezyk', 'tekst') }}

{{ tabela('przegrywa', 'format', 'tekst') }}

{{ tabela('przegrywa', 'typ', 'tekst') }}

{{ tabela('przegrywa', 'kategoria', 'tekst') }}

{{ tabela('przegrywa', 'miejsce', 'tekst') }}

### Ranking plików

{{ tabela('przegrywa', 'test', 'pliki') }}

{{ tabela('przegrywa', 'szybkosc', 'pliki') }}

{{ tabela('przegrywa', 'format', 'pliki') }}

{{ tabela('przegrywa', 'kategoria', 'pliki') }}

{{ tabela('przegrywa', 'miejsce', 'pliki') }}

{% if przewaga_domen(r) is not none %}
## Kontrola domen zarezerwowanych

{% set meta = r.kontrola_domen_meta %}{% set inne = meta.get('wartosci_inna_domena_trzon', {}) %}
Korpus używa w adresach e-mail i URL wyłącznie domen zarezerwowanych do dokumentacji i testów: `example.com`, `example.org`, `example.net` oraz domen `*.test`.
Dane treningowe modelu Legal Geek Privatizer (RC) zawierają domeny `example.*` z syntetycznych generatorów powstałych przed benchmarkiem, a domen `.test` praktycznie nie zawierają.
Model mógł więc łatwiej rozpoznawać `example.*` jako dane do zamaskowania niż domeny spoza treningu, co dałoby mu przewagę w kategoriach EMAIL i URL.
Analizę tego ryzyka zdefiniowano w metodyce i dotyczy ona wszystkich uczestników symetrycznie; wynik jest podany niezależnie od kierunku.
Metodę zamrożono przed pomiarem, skrypt analizy napisano po pomiarze, a jego kod jest w repozytorium benchmarku.

Dla wartości EMAIL i URL w trzonie (split testowy) liczono odsetek wartości, które wyciekły, osobno dla domen `example.*` i `*.test`
(ten sam generator losuje domenę, więc obie grupy są porównywalne); dla uczestnika z rankingu plików liczą się wartości ocenianych plików.
Przedziały ufności wyznaczono bootstrapem po dokumentach, tą samą macierzą losowań co w rankingach ({{ ile(meta.get('powtorzenia'), 'losowanie', 'losowania', 'losowań') }}).
Wartości z inną domeną byłyby pominięte i zliczone; w trzonie jest ich {{ ile(inne.get('EMAIL'), 'e-mail', 'e-maile', 'e-maili') }} i {{ ile(inne.get('URL'), 'adres URL', 'adresy URL', 'adresów URL') }}.
**Sygnał przewagi** występuje u uczestnika, gdy różnica „wyciek `.test` − wyciek `example.*`” jest istotnie większa niż u pozostałych: jej przedział ufności leży w całości
powyżej przedziału ufności mediany różnic pozostałych uczestników rankingu (rozłączne przedziały; warianty z aneksu liczbowego i sam uczestnik nie wchodzą do mediany).
Test zapisano w kodzie przed policzeniem wyniku. Ma on ograniczenia – mediana różnic pozostałych uczestników ma często przedział [0–0], nie zastosowano korekty na wielokrotne porównania, a liczby adresów URL są małe;
opisuje je aneks ujawnień (akapit o domenach `example.*`).

{% for rk, nazwa in (('tekst', 'tekstu'), ('pliki', 'plików')) %}{% set sy = sygnaly_domen(r, rk) %}{% set uczestnicy = sy | map(attribute='uczestnik') | unique | list %}
W rankingu {{ nazwa }} sygnał przewagi w co najmniej jednej z dwóch kategorii ma {{ liczba(uczestnicy | length, 0) }} z {{ liczba(r.rankingi[rk] | length, 0) }} uczestników{% if uczestnicy %}: {% for u in uczestnicy %}`{{ u }}`{% if not loop.last %}, {% endif %}{% endfor %}{% endif %}.
{% for u in (('privatizer-tekst',) if rk == 'tekst' else ('privatizer-plik',)) %}{% set e = domeny_wiersz(r, rk, u, 'EMAIL') %}{% set l = domeny_wiersz(r, rk, u, 'URL') %}{% if e is not none and l is not none %}Uczestnik mierzący tryb domyślny Privatizera (`{{ u }}`) ma różnicę `.test` − `example.*` równą {{ roznica_pp(e.roznica) }} {{ przedzial_procent(e.roznica_ci_dol, e.roznica_ci_gora) }} w e-mailach i {{ roznica_pp(l.roznica) }} {{ przedzial_procent(l.roznica_ci_dol, l.roznica_ci_gora) }} w adresach URL; sygnał przewagi: e-maile – {{ e.sygnal if e.sygnal is not none else 'n/d' }}, adresy URL – {{ l.sygnal if l.sygnal is not none else 'n/d' }}.{% endif %}{% endfor %}
{% endfor %}
{% set sygn_presidio = [] %}{% for rk in r.rankingi %}{% for x in sygnaly_domen(r, rk) %}{% if x.uczestnik.startswith('presidio') and x.uczestnik not in sygn_presidio %}{% set _ = sygn_presidio.append(x.uczestnik) %}{% endif %}{% endfor %}{% endfor %}
{% if sygn_presidio %}Sygnały przewagi uczestników `presidio-*` ({% for u in sygn_presidio %}`{{ u }}`{% if not loop.last %}, {% endif %}{% endfor %}) są co najmniej częściowo tłumaczone mechanizmem opisanym w rozdziale „Ograniczenia”: rozpoznawacze e-mail i URL w presidio-analyzer {{ m.presidio.analyzer }} nie obejmują domeny `.test` (e-mail odrzuca walidacja z publiczną listą sufiksów, adres URL – zamknięta lista końcówek),
więc nie są dowodem kontaminacji treningowej.
{% endif %}{% set u_rodziny = [] %}{% for rk in r.rankingi %}{% for x in sygnaly_domen(r, rk) %}{% if x.uczestnik.startswith('privatizer') %}{% set _ = u_rodziny.append((rk, x)) %}{% endif %}{% endfor %}{% endfor %}
{% if u_rodziny %}Sygnał przewagi wystąpił w rodzinie Privatizera: {% for rk, x in u_rodziny %}`{{ x.uczestnik }}` (kategoria {{ x.kategoria }}, różnica {{ roznica_pp(x.roznica) }} {{ przedzial_procent(x.roznica_ci_dol, x.roznica_ci_gora) }}, mediana pozostałych {{ roznica_pp(x.mediana_pozostalych) }} {{ przedzial_procent(x.mediana_ci_dol, x.mediana_ci_gora) }}){% if not loop.last %}, {% endif %}{% endfor %}.
Zgodnie z metodyką ranking główny pokazujemy razem z wariantem przeliczonym bez wartości `example.*` (poniżej oraz w aneksie liczbowym).
{% else %}Żaden uczestnik rankingu z rodziny Privatizera nie ma sygnału przewagi. Ranking przeliczony bez wartości `example.*` podajemy w aneksie liczbowym obok analizy wrażliwości wag.
{% endif %}
W tabelach: odsetek wyciekłych wartości z przedziałem ufności, różnica w punktach procentowych, mediana różnic pozostałych uczestników i sygnał przewagi; „nie, mniejsza” oznacza różnicę istotnie
mniejszą niż u pozostałych. Uczestnicy są w kolejności miejsc rankingu głównego.

### Ranking tekstu

{{ tabela('kontrola_domen', 'tekst', 'EMAIL') }}

{{ tabela('kontrola_domen', 'tekst', 'URL') }}

### Ranking plików

{{ tabela('kontrola_domen', 'pliki', 'EMAIL') }}

{{ tabela('kontrola_domen', 'pliki', 'URL') }}

{% if przewaga_domen(r) %}
### Ranking główny i wariant bez wartości `example.*`

Wariant liczono tymi samymi funkcjami agregacji i tymi samymi wagami; z oceny usunięto wartości EMAIL i URL w domenach `example.*` (dokumenty zostają w próbie).
{% for rk, nazwa in (('tekst', 'tekstu'), ('pliki', 'plików')) %}{% set z = zmiana_rankingu(r, rk) %}{% if z is not none %}
W rankingu {{ nazwa }} pierwsze miejsce zajmuje w wariancie `{{ z.lider_wariant }}` (suma {{ liczba(z.suma_lidera_wariant) }} pkt), w rankingu głównym – `{{ z.lider_glowny }}`; trzy pierwsze miejsca {% if z.to_samo_top3 %}mają tych samych uczestników w tej samej kolejności{% else %}różnią się składem lub kolejnością{% endif %}.
Numer miejsca zmienia się u {{ liczba(z.zmienione_miejsca, 0) }} z {{ liczba(z.uczestnikow, 0) }} uczestników, a etykieta miejsca (numer albo remis) u {{ liczba(z.zmienione_etykiety, 0) }}{% if z.zmiany_etykiet %}: {% for e in z.zmiany_etykiet %}`{{ e.uczestnik }}` – z „{{ e.glowny }}” na „{{ e.wariant }}”{% if not loop.last %}, {% endif %}{% endfor %}{% endif %}.
Największa zmiana sumy to {{ liczba(z.najwieksza_zmiana) }} pkt (`{{ z.uczestnik_najwiekszej_zmiany }}`).
{% endif %}{% endfor %}

{{ tabela('ranking_bez_example', 'tekst') }}

{{ tabela('ranking_bez_example', 'pliki') }}
{% endif %}
{% endif %}
