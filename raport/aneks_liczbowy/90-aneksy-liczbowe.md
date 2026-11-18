# Aneks liczbowy

Aneks zbiera tabele pełne, które w rozdziale z wynikami zajęłyby zbyt wiele miejsca, oraz dane identyfikujące mierzone wydanie.

## Uczestnicy aneksu

Uczestnicy aneksu nie mają miejsc w rankingach. „Maksymalna ochrona” to tryb aplikacji, pozostałe warianty to potok z obcym modelem, Presidio z modelem Legal Geek Privatizer (RC) i same reguły.
Test bez pomiaru czasu (T6, P7) ma w uwagach „nie mierzono”, a w kolumnie punktów „n/d”.

### Tekst

{{ tabela('aneks_x1', 'tekst') }}

### Pliki

{{ tabela('aneks_x1', 'pliki') }}

## Kategorie danych

Odsetek wyciekłych wartości w każdej kategorii (mniej = lepiej); „n/d” – uczestnik nie ma wartości w tej kategorii.

### Ranking tekstu

{{ tabela('per', 'kategoria', 'tekst') }}

### Ranking plików

{{ tabela('per', 'kategoria', 'pliki') }}

## Przypadki trudne – pełne zestawienie

### Ranking tekstu

{{ tabela('per', 'przypadek', 'tekst') }}

### Ranking plików

{{ tabela('per', 'przypadek', 'pliki') }}

{% if r.ranking_bez_example %}
## Ranking bez wartości example.*

Analiza dodatkowa kontroli domen zarezerwowanych (rozdział „Wyniki”): rankingi przeliczone bez wartości EMAIL i URL w domenach `example.*`, z tymi samymi wagami testów i tym samym bootstrapem;
obok miejsca i sumy rankingu głównego. Wariant nie zmienia punktacji, jest analizą dodatkową obok analizy wrażliwości na wagi.
{% for rk, nazwa in (('tekst', 'tekstu'), ('pliki', 'plików')) %}{% set z = zmiana_rankingu(r, rk) %}{% if z is not none %}
W rankingu {{ nazwa }} numer miejsca zmienia się u {{ liczba(z.zmienione_miejsca, 0) }} z {{ liczba(z.uczestnikow, 0) }} uczestników, a etykieta miejsca (numer albo remis) u {{ liczba(z.zmienione_etykiety, 0) }}{% if z.zmiany_etykiet %}: {% for e in z.zmiany_etykiet %}`{{ e.uczestnik }}` – z „{{ e.glowny }}” na „{{ e.wariant }}”{% if not loop.last %}, {% endif %}{% endfor %}{% endif %}; największa zmiana sumy to {{ liczba(z.najwieksza_zmiana) }} pkt (`{{ z.uczestnik_najwiekszej_zmiany }}`).{% endif %}{% endfor %}

### Ranking tekstu

{{ tabela('ranking_bez_example', 'tekst') }}

### Ranking plików

{{ tabela('ranking_bez_example', 'pliki') }}
{% endif %}

## Rankingi niekompletne

{% if r.niekompletne %}Uczestnicy, u których któryś test jest nieliczony:
{% for x in r.niekompletne %}
- `{{ x.uczestnik }}` (ranking {{ x.ranking }}): {{ x.powod }}.
{% endfor %}{% else %}Wszystkie testy wszystkich uczestników rankingów są policzone.{% endif %}

## Mierzone wydanie

{{ tabela('wersje') }}

Odciski kodu i reguł (SHA-256) pozwalają sprawdzić, że mierzono dokładnie to wydanie:

{{ tabela('odcisk') }}
