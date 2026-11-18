# Aneks odtworzenia

Aneks opisuje, jak odtworzyć pomiar, i wymienia narzędzia, które rozważono i odrzucono. Kod, metodyka, konfiguracje uczestników i korpus są w repozytorium benchmarku ({{ repozytorium }}); zamrożoną wersję metodyki wskazuje znacznik git `prerejestracja-1`.
{% set op = r.odcisk | selectattr('poziom', 'equalto', 'plik') | list %}{% set c = m.czas %}
## Wymagania

- Python w wersji {{ m.srodowisko.python }} lub nowszej i narzędzie `uv`; każdy uczestnik jest osobnym projektem `uv` w katalogu `uczestnicy/<id>/` z plikiem blokady `uv.lock` (te same wersje bibliotek co w pomiarze).
- Linux na procesorze, bez GPU (`CUDA_VISIBLE_DEVICES=""`). Ocena trafności jest deterministyczna: sędziowie dają ten sam wynik niezależnie od maszyny przy tym samym środowisku.
- Środowisko oceny plikowej jest zamrożone: {% if op %}Tesseract {{ op[0].tesseract }} z biblioteką leptonica {{ op[0].leptonica }}, LibreOffice {{ op[0].libreoffice }}{% else %}Tesseract, leptonica i LibreOffice w wersjach z prerejestracji{% endif %},
  dane językowe Tesseracta z kontrolą sum SHA-256 w katalogu `vendor/tessdata` oraz czcionki Liberation (potrzebne do odtworzenia DOC, RTF i ODT w warstwie trudnej). Ocena plikowa sprawdza to środowisko i przy niezgodności przerywa bez oceny.
  Odciski kodu i reguł sędziów oraz wersje narzędzi są w tabeli „Mierzone wydanie” w osobnym dokumencie „Aneks liczbowy”, publikowanym razem z raportem.
- Pomiar Privatizera wymaga zainstalowanego wydania z rozdziału „Metodyka” (plan licencji „pro”) i dostępu do modelu, które udostępnia producent. Pomiar szybkości wymaga maszyny referencyjnej opisanej w rozdziale „Metodyka”.

## Kroki

Wszystkie polecenia wykonuje się w katalogu głównym repozytorium.

```
uv sync

# korpus z repozytorium: kontrola sum SHA-256
(cd korpus && sha256sum -c ../metodyka/SHA256SUMS-trzon)
(cd korpus-trudne && sha256sum -c ../metodyka/SHA256SUMS-trudne)

# odtworzenie korpusu z kodu (trzon i warstwa trudna) do osobnych katalogów i porównanie sum
uv run pbench-korpus --ziarno {{ m.korpus.ziarno_trzonu }} --cel odtworzony/korpus/
uv run pbench-trudne --ziarno {{ m.korpus.ziarno_trudne }} --cel odtworzony/korpus-trudne --pelna
(cd odtworzony/korpus && sha256sum -c ../../metodyka/SHA256SUMS-trzon)
(cd odtworzony/korpus-trudne && sha256sum -c ../../metodyka/SHA256SUMS-trudne)

# uczestnik: środowisko, przebieg na splicie testowym, ocena
uv sync --frozen --project uczestnicy/<id>
uv run pbench-uruchom --uczestnik <id> --split test --poziom tekst
uv run pbench-ocen    --uczestnik <id> --split test --poziom tekst

# agregacja: oba rankingi, bootstrap, wrażliwość, rozbicia
uv run pbench-agreguj --split test --wyniki wyniki --wyniki-trudne wyniki/trudne --czasy wyniki/czas/czasy.jsonl

# szybkość (maszyna referencyjna)
uv run pbench-czas --uczestnik <id> --poziom tekst --korpus korpus --cel wyniki/czas

# kontrole dodatkowe
uv run pbench-kontaminacja --korpus korpus/ --korpus-trudne korpus-trudne/ --legal-texts <dane treningowe> --linia <opis linii modelu>
PYTHONPATH=. uv run python narzedzia/kontrola_domen.py --cel kontrola-domen --commit <skrót commitu>

# raport
uv run --group raport playwright install chromium
uv run --group raport python -m raport.buduj --wyniki <katalog zbiorczy> --cel raport.pdf --cel-aneks aneks.pdf
```

Parametry pomiaru zapisano w metodyce: ziarno korpusu trzonu {{ m.korpus.ziarno_trzonu }}, ziarno warstwy trudnej {{ m.korpus.ziarno_trudne }}, ziarno bootstrapu {{ m.ziarna.bootstrap }}
({{ liczba(wagi_punktow.progi.bootstrap_powtorzen, 0) }} losowań), ziarno losowania próbki czasu {{ m.ziarna.proba_czasu }} ({{ liczba(c.proba_dokumentow, 0) }} dokumentów, {{ liczba(c.rozgrzewka, 0) }} przejście rozgrzewkowe i {{ liczba(c.przejscia, 0) }} mierzone,
{{ liczba(c.watki, 0) }} wątki). Uczestnicy używają dokładnie tych rewizji modeli i narzędzi, które zapisano w konfiguracjach (`uczestnicy/<id>/KONFIG.md`) i w plikach wersji przebiegów.

Wyniki czasu zależą od sprzętu: ten sam kod na innej maszynie da inne czasy, więc punkty szybkości (T6, P7) z innego sprzętu nie są porównywalne z raportem. Dokumenty korpusu są w repozytorium (katalogi `korpus/` i `korpus-trudne/`, licencja z zakazem trenowania modeli) i można je odtworzyć z kodu; zgodność z pomiarem sprawdzają opublikowane sumy kontrolne. Kontrola kontaminacji wymaga zbioru referencyjnego, czyli danych treningowych mierzonego modelu, i opisu jego linii treningowej; nie są one publiczne,
a wynik kontroli zawiera wyłącznie liczby.

## Narzędzia rozważone i odrzucone

| Kandydat | Powód |
|---|---|
| Piiranha (model mDeBERTa organizacji `iiiorg`) | licencja CC-BY-NC-ND 4.0 jest niekomercyjna, a opublikowane porównanie firmy mogłoby uchodzić za użycie komercyjne; model nie został pobrany ani uruchomiony |
| anonimizator CLARIN-PL | repozytorium nie ma pliku licencji, a rozpoznawanie nazw własnych pochodzi wyłącznie z usług sieciowych CLARIN-PL; lokalnie na procesorze, bez usług sieciowych, narzędzia nie da się uruchomić |
| Liner2 (CLARIN-PL) | ogólny NER, a nie anonimizator; wymaga osobnego łańcucha narzędzi i modeli (Java 8, CRF++, tager morfologiczny); ostatnia zmiana 2023-06-05 |
| pakiet `ai4privacy` z PyPI | plik licencji pakietu to „All rights reserved.”, więc nie ma licencji otwartej; w benchmarku uczestniczy sam model (licencja MIT), uruchamiany standardowym potokiem biblioteki transformers |
| pakiet `pdf-redactor` z PyPI | opublikowany z forka, nie przez autorów; zastąpiony kodem z repozytorium autorów w przypiętym commicie |
| usługi chmurowe (Google Cloud Sensitive Data Protection, usługi analogiczne u innych dostawców) | decyzja o opisaniu bez pomiaru; opis w rozdziale „Wdrożenie” |
