# Punktacja i rankingi

Wagi i wzory poniżej są zapisane w prerejestracji (`metodyka/prerejestracja.md`), **zanim** jakikolwiek uczestnik (także
Privatizer) przejdzie przebieg na splicie test, z którego liczy się punkty. Wartości liczbowe: `metodyka/wagi_punktow.json`.
Zmiana po zamrożeniu prerejestracji = nowa wersja prerejestracji z opisem i wynikami obu wersji w raporcie.

## Dwa rankingi zamiast jednego

1. **Ranking „tekst”** – wszyscy uczestnicy przetwarzający tekst (modele i narzędzia OSS, Privatizer – sam model
   i aplikacja na tekście). Mierzy wykrywanie i maskowanie danych w treści.
2. **Ranking „pliki”** – uczestnicy zwracający plik wynikowy (Privatizer – model + aplikacja, narzędzia plikowe,
   wzorcowy „naiwny wrapper”). Mierzy to, co faktycznie wychodzi z organizacji.

Narzędzie tylko tekstowe nie dostaje zera w rankingu plików – po prostu w nim nie występuje. Warianty ablacyjne
(np. `privatizer-reguly`) są w aneksie, poza rankingami.

## Zasady wspólne

- Punkty testu = waga × wynik, wynik ∈ [0, 1] ze **stałego wzoru**, niezależny od innych uczestników (dodanie lub
  usunięcie konkurenta nie zmienia cudzych punktów). Suma rankingu: maks. 1000 pkt. Zaokrąglenie do 1 pkt
  dopiero w prezentacji.
- Zakres danych: **split test**. Testy T1, T2, T4, T5, P1, P2, P4–P6 – warstwa `trzon`; T3, P3 – warstwa `trudne`.
  Identyfikacja pośrednia (`posrednie`) – poza punktami, osobna miara opisowa. Ukraiński (`uk`) – poza T4
  (spoza pięciu języków Privatizera), wchodzi do T3/P3 jako przypadek.
- Wyciek, fałszywe maskowanie, odczyt pliku – według sędziów opisanych w metodyce (`pbench/sedzia/*`,
  `metodyka/prerejestracja.md`); punktacja niczego w nich nie zmienia.
- Dokument z błędem, przekroczonym czasem lub nieobsłużony: w testach wycieku liczony jak **dokument z wyciekiem**
  (fail-closed – użytkownik wysłałby oryginał).
- Niepewność: bootstrap po dokumentach (1000 powtórzeń, 95%). Gdy przedziały ufności sumy dwóch uczestników się
  nakładają, raport pokazuje **remis statystyczny** zamiast rozstrzygnięcia miejsca.
- Analiza wrażliwości (aneks): rankingi przy trzech alternatywnych zestawach wag z `wagi_punktow.json`
  (`rowne`, `prywatnosc`, `uzytecznosc`). Jeżeli kolejność zależy od wag, raport mówi to wprost.
- Raport zawiera pełną macierz „uczestnik × test” (punkty i surowe miary) oraz przedziały ufności.

## Ranking „tekst” (1000 pkt)

| Test | Pkt | Wynik ∈ [0,1] |
|---|---|---|
| T1 Dokumenty bez wycieku (ważone kategorią) | 350 | 1 − Σ_d s(d) / N, s(d) – waga dokumentu (sekcja „Waga dokumentu z wyciekiem”) |
| T2 Wyciek ważony kategorią | 250 | 1 − Σ w(kat)·[wyciekła] / Σ w(kat) po wszystkich wartościach gold |
| T3 Trudne przypadki | 150 | średnia po przypadkach tekstowych z (1 − Σ_{d∈przypadek} s(d) / liczba dokumentów przypadku) |
| T4 Najsłabszy język | 50 | min po {pl, en, es, de, fr} wyniku T1 (ważonego) liczonego w obrębie języka |
| T5 Brak nadmiarowego maskowania | 150 | max(0, 1 − u / 0,20), u = znaki zamaskowane poza gold / znaki poza gold |
| T6 Szybkość | 50 | min(1, t_ref / t), t = mediana s/stronę na maszynie referencyjnej |

## Ranking „pliki” (1000 pkt)

| Test | Pkt | Wynik ∈ [0,1] |
|---|---|---|
| P1 Pliki bez wycieku (ważone kategorią) | 350 | 1 − Σ_d s(d) / N, wycieki w dowolnej części pliku, sędzia plikowy |
| P2 Wyciek ważony miejscem | 200 | 1 − Σ w(kat)·w(miejsce)·[wyciekła] / Σ w(kat)·w(miejsce) |
| P3 Trudne przypadki plikowe | 150 | jak T3 (ważone s(d)), sędzia plikowy |
| P4 Integralność | 100 | średnia z: plik się otwiera (0/1), zachowanie struktury, spójność tokenów tej samej wartości; składnik „nie dotyczy” (np. format zamieniony na odpowiednik) pomijany w średniej, nie liczony jako 0 |
| P5 Brak nadmiarowego maskowania | 100 | jak T5, na tekście wyekstrahowanym z pliku wynikowego |
| P6 Pokrycie formatów | 50 | dokumenty przetworzone bez błędu i bez „nieobsługiwane” / wszystkie |
| P7 Szybkość | 50 | jak T6, dla przetwarzania pliku |

Zamiana formatu (np. `.doc` → `.docx`, `.msg` → `.txt`) nie jest wyciekiem ani błędem; raport pokazuje ją
w tabeli różnic funkcjonalnych.

## Waga dokumentu z wyciekiem

T1, P1, T3, P3 i T4 liczą dokument z wyciekiem według najwyższej wagi wyciekłej kategorii, a nie
jako 0/1 (wyciek kwoty o wadze 1 liczy się mniej niż wyciek PESEL o wadze 3, spójnie z T2 i P2, które też ważą kategorie).
Wagi punktów testów, bootstrap i remisy – jak w całym dokumencie. Wagi: `metodyka/wagi_punktow.json` (`pbench-agreguj`).

**Definicja (wiążąca).**
- **Waga dokumentu z wyciekiem** s(d) = max w(kat) po wartościach gold, które w dokumencie wyciekły (pełnie lub częściowo – tak jak
  w sędziach „wyciekła”), podzielone przez 3 (najwyższa waga kategorii); dokument bez wycieku s = 0; dokument fail-closed (błąd,
  timeout, odmowa, nieczytelny, brak wyniku – wszystkie stany ≠ `ok`) s = 1. Wagi kategorii: `wagi_kategorii` 3/2/1;
  wagi miejsc **nie** wchodzą.
- **T1** = 1 − Σ_d s(d) / N. **T4** = min po językach T1 (tej samej definicji, z definicji „T1 w obrębie
  języka”). **P1** = analogicznie na sędzim plikowym (wycieki w dowolnej części pliku, wagi kategorii; miejsca nie).
- **T3 i P3** = średnia po przypadkach punktowanych z
  (1 − Σ_{d∈przypadek} s(d) / liczba dokumentów przypadku), s(d) jak wyżej. Przypadki i stratyfikacja bootstrapu – jak w pozostałych testach.
- T2, T5, T6, P2, P4–P7 liczą się bez ważenia dokumentu s(d); wagi punktów testów (350/250/…), bootstrap, remisy i analiza wrażliwości – jak w opisie wyżej.
- Nazwy: „T1 Dokumenty bez wycieku (ważone kategorią)”, „P1 Pliki bez wycieku (ważone kategorią)”.

Przykłady s(d) (i wkładu dokumentu do T3/P3): dokument z wyciekiem kwoty i PESEL → 1; tylko kwota → 1/3; tylko osoba → 2/3.

## Wagi kategorii i miejsc

- Kategorie (`w(kat)`): **3** – dane szczególnej kategorii (zdrowie, wizerunek) i identyfikatory osobowe (PESEL,
  dowód, paszport, rachunek, karta, krajowe numery ID, ubezpieczeniowe i podatkowe osób, MRZ, sekrety);
  **2** – osoba, adres, e-mail, telefon, data i miejsce urodzenia, numer rejestracyjny, księga wieczysta,
  login, IP, portfel krypto; **1** – pozostałe (miejscowość, region, kraj, kod pocztowy, organizacja, data,
  kwota, URL, sygnatura, numery rejestrowe firm, UUID, MAC, inicjały, własne). Pełna lista: `wagi_punktow.json`.
- Miejsca (`w(miejsce)`): treść, tabela, przypis 1,0; nagłówek, stopka, pole, obraz, załącznik 1,5; metadane,
  komentarze, śledzenie zmian 2,0 – miejsca, których użytkownik zwykle nie ogląda przed wysłaniem, ważą więcej.

## Ustalane po pilocie na dev (dozwolone, bez zmiany wag)

`t_ref` (s/stronę) dla T6/P7 oraz maszyna i ustawienia pomiaru czasu. Zapis w `metodyka/prerejestracja.md`
przed przebiegiem na splicie test.
