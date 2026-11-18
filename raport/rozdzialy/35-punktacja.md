# Punktacja

Punkty wynikają ze stałych wzorów zapisanych w prerejestracji przed pomiarem. Punkty testu to jego waga razy wynik z przedziału od zera do jednego. Wynik nie zależy od innych uczestników:
dodanie lub usunięcie narzędzia nie zmienia cudzych punktów. Sumy są liczone bez zaokrągleń, a zaokrąglenie dotyczy tylko prezentacji.
{% set w = wagi_testow() %}{% set pr = wagi_punktow.progi %}{% set kw = namespace(waga='n/d') %}{% set os = namespace(waga='n/d') %}{% for ww, kategorie in wagi_punktow.wagi_kategorii.items() %}{% if 'OSOBA' in kategorie %}{% set os.waga = ww %}{% endif %}{% endfor %}{% for ww, kategorie in wagi_punktow.wagi_kategorii.items() %}{% if 'KWOTA' in kategorie %}{% set kw.waga = ww %}{% endif %}{% endfor %}
Każdy z dwóch rankingów ma {{ liczba(maks_punktow('tekst'), 0) }} punktów możliwych do zdobycia (tekst) i {{ liczba(maks_punktow('pliki'), 0) }} (pliki). Testy „T” dotyczą rankingu tekstu, testy „P” – rankingu plików.

## Testy rankingu tekstu

| Test | Co mierzy | Punkty | Wynik z przedziału od zera do jednego |
|---|---|---|---|
| T1 | dokumenty bez wycieku (ważone kategorią) | {{ liczba(w['T1'], 0) }} | jeden minus średnia waga wycieku dokumentu (niżej) po dokumentach trzonu |
| T2 | wyciek ważony kategorią | {{ liczba(w['T2'], 0) }} | jeden minus udział wagi wyciekłych wartości wzorcowych w wadze wszystkich wartości |
| T3 | trudne przypadki | {{ liczba(w['T3'], 0) }} | średnia po przypadkach tekstowych warstwy trudnej z (jeden minus średnia waga wycieku dokumentów przypadku) |
| T4 | najsłabszy język | {{ liczba(w['T4'], 0) }} | najniższy wynik T1 liczonego osobno dla polskiego, angielskiego, hiszpańskiego, niemieckiego i francuskiego |
| T5 | brak nadmiarowego maskowania | {{ liczba(w['T5'], 0) }} | jeden minus udział zamaskowanych znaków spoza gold w znakach spoza gold, podzielony przez próg {{ procent(pr.nadmiarowe_maskowanie_zero_pkt_przy_udziale, 0) }}; nie mniej niż zero |
| T6 | szybkość | {{ liczba(w['T6'], 0) }} | wartość odniesienia `t_ref` podzielona przez medianę czasu na stronę, nie więcej niż jeden |

## Testy rankingu plików

| Test | Co mierzy | Punkty | Wynik z przedziału od zera do jednego |
|---|---|---|---|
| P1 | pliki bez wycieku (ważone kategorią) | {{ liczba(w['P1'], 0) }} | jak T1, wyciek w dowolnej części pliku wynikowego (sędzia plikowy) |
| P2 | wyciek ważony miejscem | {{ liczba(w['P2'], 0) }} | jak T2, z wagą wartości równą wadze kategorii razy wadze miejsca w pliku |
| P3 | trudne przypadki plikowe | {{ liczba(w['P3'], 0) }} | jak T3, sędzia plikowy, z przypadkami o trudności wyłącznie w pliku |
| P4 | integralność | {{ liczba(w['P4'], 0) }} | średnia z: plik się otwiera, zachowanie struktury, spójność tokenów tej samej wartości; składnik „nie dotyczy” jest pomijany w średniej |
| P5 | brak nadmiarowego maskowania | {{ liczba(w['P5'], 0) }} | jak T5, na tekście wyekstrahowanym z pliku wynikowego |
| P6 | pokrycie formatów | {{ liczba(w['P6'], 0) }} | udział dokumentów przetworzonych bez błędu i bez „nieobsługiwane” we wszystkich dokumentach trzonu (odmowa liczy się jako nieprzetworzony) |
| P7 | szybkość | {{ liczba(w['P7'], 0) }} | jak T6, dla przetwarzania pliku |

## Waga dokumentu z wyciekiem

T1, P1, T3, P3 i T4 nie liczą dokumentu jako wyciek albo brak wycieku. Waga dokumentu to najwyższa waga kategorii wśród wartości wzorcowych, które w nim wyciekły (w całości lub w części), podzielona przez {{ liczba(m.sedzia.waga_kategorii_max, 0) }}.
Dokument bez wycieku ma wagę zero. Dokument, którego nie udało się ocenić jako wynik uczestnika (błąd, przekroczony czas, odmowa, pusty lub nieczytelny wynik, format poza deklaracją), ma wagę jeden.
Wyciek kwoty (waga kategorii {{ kw.waga }}) liczy się więc mniej niż wyciek PESEL. Przykłady: dokument z wyciekiem kwoty i PESEL ma wagę jeden, z samą kwotą – {{ kw.waga }}/{{ m.sedzia.waga_kategorii_max }}, z samą osobą (kategoria `OSOBA`, waga {{ os.waga }}) – {{ os.waga }}/{{ m.sedzia.waga_kategorii_max }}.

## Wagi kategorii i miejsc

{% for waga in ['3', '2', '1'] %}- **Kategorie z wagą {{ waga }}:** {{ wagi_punktow.wagi_kategorii[waga] | join(', ') }}.
{% endfor %}
Wagi miejsc dotyczą testu P2 i wyniku „wyciek ważony kategorią na poziomie pliku”. Miejsca, których użytkownik zwykle nie ogląda przed wysłaniem pliku, ważą więcej:
{% set wm = wagi_punktow.wagi_miejsc %}{% for g in (1.0, 1.5, 2.0) %}waga {{ liczba(g, 1) }} – {{ wm.items() | selectattr('1', 'equalto', g) | map(attribute='0') | join(', ') }}{% if not loop.last %}; {% endif %}{% endfor %}.
Wagi miejsc nie wchodzą do testów T1 i P1.

## Brak wyniku, odmowa i niekompletność

Dokument bez wyniku uczestnika jest liczony fail-closed: sędzia ocenia go jak tekst bez wykryć albo kopię oryginału. Odmowa, czyli komunikat produktu, że dokumentu nie przetworzy, liczy się tak samo, ale raport pokazuje ją w osobnej kolumnie.
Ranking niekompletny (test nieliczony, dokument bez oceny, błąd sędziego) nie jest publikowany; test, którego prerejestracja każe nie liczyć dla danego uczestnika, jest oznaczony „n/d” i nie wnosi punktów.

## Analiza wrażliwości na wagi

Kolejność uczestników sprawdzono przy trzech alternatywnych zestawach wag testów:

{% set aw = wagi_punktow.analiza_wrazliwosci %}- **równe wagi** – tekst: {{ aw.rowne.ranking_tekst }}, pliki: {{ aw.rowne.ranking_pliki }};
- **nacisk na prywatność** – tekst: {% for t, p in aw.prywatnosc.ranking_tekst.items() %}{{ t }} {{ liczba(p, 0) }}{% if not loop.last %}, {% endif %}{% endfor %}; pliki: {% for t, p in aw.prywatnosc.ranking_pliki.items() %}{{ t }} {{ liczba(p, 0) }}{% if not loop.last %}, {% endif %}{% endfor %} (pozostałe testy bez punktów);
- **nacisk na użyteczność** – tekst: {% for t, p in aw.uzytecznosc.ranking_tekst.items() %}{{ t }} {{ liczba(p, 0) }}{% if not loop.last %}, {% endif %}{% endfor %}; pliki: {% for t, p in aw.uzytecznosc.ranking_pliki.items() %}{{ t }} {{ liczba(p, 0) }}{% if not loop.last %}, {% endif %}{% endfor %}.

Wynik analizy jest w rozdziale „Wyniki”. Jeżeli kolejność zależy od wag, raport mówi to wprost.
