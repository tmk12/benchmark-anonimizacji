# Kontrola domen zarezerwowanych (analiza dodatkowa, ustalona 2026-10-30 przed przebiegami punktowanymi)

## Fakt
Korpus używa w e-mailach i adresach URL wyłącznie domen zarezerwowanych (RFC 2606/6761): `example.com|org|net`
oraz `*.test` (`pbench/dane/wspolne.py`). Zespół trenujący model Privatizera zgłosił 2026-10-30, że dane
treningowe modelu zawierają domeny `example.*` jako e-maile/URL z własnych generatorów syntetycznych, powstałych przed
benchmarkiem (w największej mieszance treningowej ok. 2,1% wierszy). Domen `.test` w treningu praktycznie nie ma (5 wystąpień). Zespół nie miał dostępu do korpusu.

## Ryzyko
Model mógł nauczyć się rozpoznawać `example.*` jako dane do maskowania łatwiej niż domeny spoza treningu – przewaga
w kategoriach EMAIL i URL, której nie mają narzędzia OSS.

## Analiza (wszyscy uczestnicy, symetrycznie)
1. Dla kategorii EMAIL i URL odsetek wycieku liczony osobno dla wartości z domeną `example.*` i z domeną `.test`
   (ten sam generator, losowy wybór domeny – grupy porównywalne), z przedziałami bootstrap 95%.
2. Sygnał przewagi: u uczestnika różnica „wyciek .test − wyciek example.*” istotnie większa niż u pozostałych.
3. Rankingi przeliczone wariantowo bez wartości EMAIL/URL w domenach `example.*` (aneks, obok analizy wrażliwości
   wag). Wagi bez zmian – to analiza dodatkowa, nie zmiana punktacji.
4. Raport przedstawia wynik niezależnie od kierunku; jeżeli przewaga wystąpi, ranking główny pokazuje się razem
   z wariantem z pkt 3.
