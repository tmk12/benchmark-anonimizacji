# Przykłady

Tabela pokazuje, jak wyglądają wycieki w wynikach uczestników rankingu tekstu.
{% set n_uczestnikow = r.przyklady | map(attribute='uczestnik') | unique | list | length %}{% set na_uczestnika = ((r.przyklady | length) // n_uczestnikow) if n_uczestnikow else 0 %}Dla każdego uczestnika wzięto
{{ ile(na_uczestnika, 'pierwszy dokument', 'pierwsze dokumenty', 'pierwszych dokumentów') }} ze splitu testowego (w kolejności manifestu korpusu), w których zostawił co najmniej jedną wartość wzorcową w odczytywalnej postaci.
Przykładów nie wybierano jako typowych ani jako szczególnie dobrych lub złych. Każdy z nich pokazuje wyciek, więc nie mówią nic o udziale dokumentów bez wycieku – ten udział podają rankingi.
Uczestnicy mogą mieć ten sam dokument, a wartość, która wyciekła, bywa u każdego inna.

Kolumna „Przed anonimizacją” to okno tekstu wokół pierwszej wartości, która wyciekła; kolumna „Po anonimizacji” to to samo okno z wykryciami zastąpionymi oznaczeniem uczestnika. Wartość wzorcowa, która pozostała w wyniku
w całości („pełny”) albo w części („częściowy”), jest w pierwszej kolumnie podkreślona i pogrubiona tam, gdzie znane jest jej położenie w oknie; w pozostałych wierszach okno pokazano bez wyróżnienia. Wszystkie dokumenty są syntetyczne, a osoby, firmy i adresy – fikcyjne.

{{ tabela('przyklady', 'tekst') }}
