# Atrapa (uczestnik testowy)

Nie jest narzędziem do anonimizacji i nie występuje w wynikach. Służy do testów orkiestratora i sędziów.

- Wersje: brak zależności zewnętrznych (tylko biblioteka standardowa).
- Model, recognizery, progi: brak.
- Źródło konfiguracji: n/d.

Tryby (zmienna `ATRAPA_TRYB`):

| Tryb | Zachowanie |
|---|---|
| `idealny` (domyślny) | tekst: zwraca gold z manifestu (`ATRAPA_MANIFEST`); plik: kopia z zamazanymi wartościami gold (best effort: pliki ZIP – DOCX/PPTX/XLSX – i surowe bajty) |
| `pusty` | tekst: brak wykryć; plik: kopia bez zmian |
| `wolny` | (z `ATRAPA_PID_PLIK` startuje proces potomny i zapisuje jego pid) śpi `ATRAPA_SEN` s (domyślnie 3600) na dokumentach z `ATRAPA_ID` (lista po przecinku; puste = wszystkie), reszta jak `idealny` |
| `pada` | kończy proces bez odpowiedzi na dokumentach z `ATRAPA_ID`, reszta jak `idealny` |
| `zle_offsety` | zwraca wykrycie poza tekstem na dokumentach z `ATRAPA_ID`, reszta jak `idealny` |
| `inne_rozszerzenie` | plik: zapisuje wynik `.txt` (inne rozszerzenie niż oryginał) i zwraca jego ścieżkę (R38) |
| `plik_kopia` | plik: kopia bez zmian; tekst: brak wykryć |
