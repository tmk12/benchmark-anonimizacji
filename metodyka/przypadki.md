# Rozkład warstwy trudnych przypadków (spec §11; zadanie H6b)

Warstwa `trudne` to osobny zbiór dokumentów (ziarno `ZIARNO_TRUDNE` = 20261104, identyfikatory `h-<skrót>-<język>-<typ>-<nr>`),
oceniany per przypadek (T3, P3 – `punktacja.md`; identyfikacja pośrednia – osobna miara, `posrednie.md`). Trzon korpusu
(1000 dokumentów) się nie zmienia.

**Jedno źródło:** rozkład jest stałą `pbench.trudne_warstwa.ROZKLAD` (przypadek → dokumenty per język + uzasadnienie); plan,
split i ta tabela powstają z niej kodem. Tabelę między znacznikami wypisuje `uv run pbench-trudne --rozklad`, a test
`tests/test_h6b.py::test_tabela_rozkladu_w_metodyce_zgodna_z_kodem` pilnuje, że jest aktualna.

**Budowa:** `uv run pbench-trudne --cel korpus-trudne --pelna [--procesy N] [--sumy metodyka/SHA256SUMS-trudne]` – cała
warstwa deterministycznie (te same bajty niezależnie od liczby procesów; formaty z LibreOffice'em – DOC, RTF, ODT – wymagają tej
samej wersji LibreOffice'a, `srodowiska.md`). Manifest `korpus-trudne/manifest.jsonl` ma we wpisie pola trzonu oraz `warstwa`
(`"trudne"`), `przypadki`, `posrednie`, `ukryte` (gdy dokument ma treść ukrytą) i `split`.

## Warunki rozkładu

- łącznie 300 ± 40 dokumentów; każdy przypadek ≥ 8 dokumentów, w tym ≥ 2 w dev;
- każdy przypadek we wszystkich językach, w których ma generator (H1–H5), z PL zawsze – wyjątek: `cyrylica_dokument_uk` (dokument
  w całości po ukraińsku); wstawki cyrylicy, transliteracje i pisownia rosyjska imion – PL, EN, DE (spec §11 pkt 3: dokumenty
  PL/EN/DE); `odmiana_nazwisk` – tylko PL;
- formaty z `trudne.formaty_dla` i ograniczeń przypadku (`przypadki.FORMAT_PRZYPADKU`, `FORMATY_PRZYPADKU`), udziały jak w trzonie
  przeliczone na formaty możliwe dla przypadku; języki przydzielane pozycjom formatu tak, żeby język miał możliwie różne formaty
  i typy (`trudne_warstwa.zaplanuj_rozklad`);
- split per przypadek: dev = max(2, round(0,2·n)), rozdzielony na języki, a w języku na formaty metodą największych reszt
  z limitem: dev nigdy nie zabiera ostatniego dokumentu danego języka ani formatu przypadku – split test (punktowany) ma każdy
  język i każdy format przypadku (`trudne_warstwa.przydziel_split_warstwy`; w przypadkach 8-dokumentowych PL 4 + po 1 EN/ES/
  DE/FR dev = 2 dokumenty PL). Split budowy pojedynczego przypadku (`trudne.przydziel_split`) zaokrągla po językach i przy
  1–2 dokumentach na język nie dawałby dev – pełna warstwa ma więc własny podział.

Domyślny kontyngent przypadku w pięciu językach to 8 dokumentów: PL 4 (połowa, jak w trzonie) i po jednym w EN, ES, DE, FR.
Przypadki z dwoma formatami albo typami, które trzeba pokazać w każdym języku (poczta EML/MSG, RTF/ODT, dwa typy arkusza), mają
po 2 dokumenty na język; przypadki o szerszym zakresie (homoglify – osiem formatów, dokument ukraiński – sześć typów
i formatów, transliteracja – dwa układy zapisów) – więcej.

## T3 i P3 – przypadki tekstowe i plikowe

T3 to „średnia po przypadkach tekstowych”, P3 – to samo sędzią plikowym (`punktacja.md`). Przypadek jest **tekstowy** (✓ w
kolumnie T3), gdy jego trudność jest w tekście poziomu 1 (`.txt`, wejście poziomu tekst): pułapki językowe, długie dokumenty,
cyrylica i transliteracje, znaki zerowej szerokości, RTL, przeniesienia, cytowany wątek e-maila. Przypadki
`przypadki.TYLKO_PLIK` (treść ukryta DOCX/XLSX/PPTX/PDF/poczta, zepsuty ToUnicode, dwie kolumny, obrócone strony, pieczątka,
zrzut ekranu, znak wodny, RTF/ODT) mają trudność wyłącznie w pliku – wartości przypadku są tylko w `gold_plik`/`gold_obrazy`,
a tekst poziomu 1 jest zwykłym tekstem dokumentu – więc wchodzą tylko do P3. Agregacja wybiera przypadki funkcją
`przypadki.przypadki_punktowane(poziom)` (`"tekst"` – 18 przypadków, `"plik"` – 30); `posrednie_*` są poza obiema średnimi.

## Rozkład

Kolumny: dokumenty i dev (split), języki i formaty planu (przypadek główny). Dokument może nieść też przypadek dodatkowy w polu
`przypadki` (`trudne.przypadki_dokumentu`): dokumenty transliteracji i pisowni rosyjskiej z cyrylicą w gold mają także
`cyrylica_wstawka` – wyniki per przypadek liczy się po polu `przypadki`, więc `cyrylica_wstawka` ma w nich więcej dokumentów
niż w tabeli (w budowie 2026-11-01: 20).

<!-- rozklad:poczatek -->
| Przypadek | Skrót | T3 | P3 | Dok. | Dev | Języki | Formaty | Uzasadnienie |
|---|---|---|---|---|---|---|---|---|
| `ukryta_docx` | `ud` | – | ✓ | 8 | 2 | pl 4, en 1, es 1, de 1, fr 1 | docx 8 | jeden format; minimum, bo każdy dokument niesie kilka rodzajów elementów ukrytych |
| `ukryta_xlsx` | `ux` | – | ✓ | 10 | 2 | pl 2, en 2, es 2, de 2, fr 2 | xlsx 10 | oba typy arkusza (lista płac, faktura) w każdym języku |
| `ukryta_pptx` | `up` | – | ✓ | 8 | 2 | pl 4, en 1, es 1, de 1, fr 1 | pptx 8 | jeden typ (prezentacja) i jeden format; minimum |
| `ukryta_pdf` | `uf` | – | ✓ | 8 | 2 | pl 4, en 1, es 1, de 1, fr 1 | pdf 8 | jeden format; zaczernienie i niezgodna warstwa OCR w każdym języku |
| `ukryta_poczta` | `um` | – | ✓ | 10 | 2 | pl 2, en 2, es 2, de 2, fr 2 | eml 5, msg 5 | oba formaty poczty (EML, MSG) w każdym języku |
| `odmiana_nazwisk` | `on` | ✓ | ✓ | 8 | 2 | pl 8 | docx 4, pdf 3, doc 1 | tylko polski (odmiana nazwisk i formy rodzinne to zjawisko polszczyzny) |
| `nazwiska_zwykle_slowa` | `nz` | ✓ | ✓ | 8 | 2 | pl 4, en 1, es 1, de 1, fr 1 | docx 4, pdf 3, doc 1 | minimum; pułapki pospolite w każdym języku |
| `zdrobnienia` | `zd` | ✓ | ✓ | 8 | 2 | pl 4, en 1, es 1, de 1, fr 1 | docx 4, pdf 3, doc 1 | minimum; zdrobnienia w każdym języku |
| `nazwisko_imie` | `ni` | ✓ | ✓ | 8 | 2 | pl 4, en 1, es 1, de 1, fr 1 | docx 4, pdf 3, doc 1 | minimum; zapis NAZWISKO Imię w każdym języku |
| `parafy` | `pf` | ✓ | ✓ | 8 | 2 | pl 4, en 1, es 1, de 1, fr 1 | docx 4, pdf 3, doc 1 | minimum; parafy w każdym języku |
| `liczby_slownie` | `ls` | ✓ | ✓ | 8 | 2 | pl 4, en 1, es 1, de 1, fr 1 | docx 4, pdf 3, doc 1 | minimum; liczebniki słowne w każdym języku |
| `cyrylica_dokument_uk` | `cu` | ✓ | ✓ | 12 | 2 | uk 12 | docx 4, pdf 3, skan 2, eml 1, msg 1, doc 1 | tylko ukraiński; więcej, bo sześć typów i sześć formatów (także skan i poczta) |
| `cyrylica_wstawka` | `cw` | ✓ | ✓ | 8 | 2 | pl 4, en 2, de 2 | docx 4, pdf 2, skan 1, doc 1 | szablony wstawek są tylko w PL, EN i DE (spec §11 pkt 3: dokument PL/EN/DE) |
| `transliteracja` | `tr` | ✓ | ✓ | 10 | 2 | pl 4, en 3, de 3 | docx 4, pdf 3, skan 2, doc 1 | PL, EN, DE jak wstawki; więcej, bo dwa układy zapisów (z cyrylicą i same transliteracje) |
| `homoglify` | `hg` | ✓ | ✓ | 12 | 2 | pl 4, en 2, es 2, de 2, fr 2 | docx 4, pdf 2, skan 1, xlsx 1, pptx 1, eml 1, msg 1, doc 1 | szablony trzonu w pięciu językach; więcej, bo osiem formatów (także XLSX, PPTX, poczta, skan) |
| `pisownia_rosyjska_imion` | `ru` | ✓ | ✓ | 8 | 2 | pl 4, en 2, de 2 | docx 4, pdf 2, skan 1, doc 1 | PL, EN, DE jak wstawki (osoby ukraińskie w dokumentach tych języków) |
| `posrednie_funkcja_firma` | `ff` | – | – | 8 | 2 | pl 4, en 1, es 1, de 1, fr 1 | docx 4, pdf 3, doc 1 | minimum; miara opisowa poza punktami |
| `posrednie_rzadka_choroba` | `rc` | – | – | 8 | 2 | pl 4, en 1, es 1, de 1, fr 1 | docx 4, pdf 3, doc 1 | minimum; miara opisowa poza punktami |
| `posrednie_wiek_miejscowosc` | `wm` | – | – | 8 | 2 | pl 4, en 1, es 1, de 1, fr 1 | docx 4, pdf 3, doc 1 | minimum; miara opisowa poza punktami |
| `posrednie_dzialka_gps` | `dg` | – | – | 8 | 2 | pl 4, en 1, es 1, de 1, fr 1 | docx 4, pdf 3, doc 1 | minimum; miara opisowa poza punktami |
| `skroty_po_pelnym` | `sk` | ✓ | ✓ | 8 | 2 | pl 4, en 1, es 1, de 1, fr 1 | docx 4, pdf 3, doc 1 | minimum; dokumenty długie (> 3 okna modelu) |
| `granica_okna` | `go` | ✓ | ✓ | 8 | 2 | pl 4, en 1, es 1, de 1, fr 1 | docx 4, pdf 3, doc 1 | minimum; kilka wartości na granicach okien w każdym dokumencie |
| `dlugie_listy_osob` | `dl` | ✓ | ✓ | 8 | 2 | pl 4, en 1, es 1, de 1, fr 1 | docx 4, pdf 2, xlsx 1, doc 1 | minimum; listy ≥ 100 osób (także XLSX) |
| `znaki_zerowej_szerokosci` | `zw` | ✓ | ✓ | 8 | 2 | pl 4, en 1, es 1, de 1, fr 1 | docx 5, pdf 3 | minimum; DOCX i PDF |
| `rtl` | `rt` | ✓ | ✓ | 8 | 2 | pl 4, en 1, es 1, de 1, fr 1 | docx 5, pdf 3 | minimum; DOCX i PDF |
| `zepsuty_tounicode` | `zt` | – | ✓ | 8 | 2 | pl 4, en 1, es 1, de 1, fr 1 | pdf 8 | minimum; tylko PDF |
| `przeniesienia` | `pr` | ✓ | ✓ | 8 | 2 | pl 4, en 1, es 1, de 1, fr 1 | pdf 8 | minimum; tylko PDF |
| `dwie_kolumny` | `dk` | – | ✓ | 8 | 2 | pl 4, en 1, es 1, de 1, fr 1 | docx 5, pdf 3 | minimum; DOCX i PDF |
| `obrocone_strony` | `os` | – | ✓ | 8 | 2 | pl 4, en 1, es 1, de 1, fr 1 | pdf 5, skan 3 | minimum; PDF i skan |
| `skan_pieczatki` | `sp` | – | ✓ | 8 | 2 | pl 4, en 1, es 1, de 1, fr 1 | docx 5, pdf 3 | minimum; DOCX i PDF |
| `zrzut_ekranu` | `ze` | – | ✓ | 8 | 2 | pl 4, en 1, es 1, de 1, fr 1 | docx 5, pdf 3 | minimum; DOCX i PDF |
| `znak_wodny` | `zn` | – | ✓ | 8 | 2 | pl 4, en 1, es 1, de 1, fr 1 | docx 5, pdf 3 | minimum; DOCX i PDF |
| `cytowane_watki_vcard` | `cv` | ✓ | ✓ | 10 | 2 | pl 2, en 2, es 2, de 2, fr 2 | eml 5, msg 5 | oba formaty poczty (EML, MSG) w każdym języku |
| `formaty_rtf_odt` | `ro` | – | ✓ | 10 | 2 | pl 2, en 2, es 2, de 2, fr 2 | rtf 5, odt 5 | oba formaty (RTF, ODT) w każdym języku |
| **razem** | | 18 | 30 | **290** | 68 | pl 128, en 41, es 34, de 41, fr 34, uk 12 | docx 110, pdf 97, skan 10, xlsx 12, pptx 9, eml 12, msg 12, doc 18, rtf 5, odt 5 | |
<!-- rozklad:koniec -->

## Sumy kontrolne (prerejestracja)

`metodyka/SHA256SUMS-trudne` – suma SHA-256 każdego pliku dokumentu, każdego `.txt`, `manifest.jsonl` i `statystyki.json`
warstwy, w formacie `sha256sum` (GNU coreutils: `<64 znaki hex>  <ścieżka względem katalogu warstwy>`, posortowane po ścieżce) –
ten sam format i te same rodzaje plików co opublikowany `korpus/SHA256SUMS-trzon` prerejestracji trzonu (`statystyki.json`
warstwy jest deterministyczny: liczby dokumentów, bez czasu budowy). Sprawdzenie:
`cd korpus-trudne && sha256sum -c ../metodyka/SHA256SUMS-trudne`. Test `tests/test_h6b.py::test_pelna_warstwa_daje_opublikowane_sumy`
buduje całą warstwę i porównuje ją z tym plikiem, a skrót pliku – z linią bazową `tests/dane_testowe/trudne_baseline.json`. Dokumenty nie są w repozytorium (`.gitignore`) – odtwarza je budowa.
