"""Rejestr przypadków warstwy trudnych przypadków (spec §11): nazwa przypadku -> krótki opis.

Nazwy trafiają do `przypadki` we wpisie manifestu dokumentu warstwy `trudne` i do raportu (wyniki per przypadek).
Rejestr obejmuje WSZYSTKIE punkty §11 (1–6); generatory piszą kolejne zadania (H1: cyrylica ukraińska, transliteracje,
homoglify i pisownia rosyjska imion osób ukraińskich; H2: pułapki językowe i długie dokumenty; H3: treść ukryta w
DOCX/XLSX/PPTX; H4–H5: pozostałe). `POSREDNIE` – osobna miara (punkt 4), poza miarą główną.
Podtypy treści ukrytej (punkt 1: `w:vanish`, kody pól, pivotCache, nazwy zakresów…) nie mają osobnych kluczy; H3 zapisuje
je w polu `ukryte` wpisu manifestu (lista rodzajów `<format>.<rodzaj>`, np. `docx.zakladka`; przypadek to tylko format:
docx, xlsx, pptx, pdf, poczta). Mapowanie element -> miejsce gold: `metodyka/miejsca-ukryte.md`.
H4a (PDF, układ i kodowanie): `ukryta_pdf` oraz dziewięć przypadków punktu 6 (znaki zerowej szerokości, RTL, zepsuty
ToUnicode, przeniesienia, dwie kolumny, obrócone strony, pieczątki, zrzuty ekranu, znak wodny); dopisek obrazowy
(pieczątka, zrzut, znak wodny) to też element `Dokument.ukryte` (rodzaje `obraz.*`, `znak_wodny.*`).
H4b (poczta, RTF i ODT): `ukryta_poczta` (wiadomość w wiadomości, załącznik PDF), `cytowane_watki_vcard` (wątek cytowany pod
podpisem, wizytówka `.vcf`) i `formaty_rtf_odt` (formaty spoza trzonu: RTF i ODT z konwersji LibreOffice'em); elementy poczty
to rodzaje `poczta.*` w `Dokument.ukryte`.
H5 (identyfikacja pośrednia, punkt 4): cztery przypadki `posrednie_*` – osoba nienazwana, wskazywalna z połączenia informacji;
kombinacje w polu manifestu `posrednie` (`pbench.posrednie`), miara osobna, poza punktami (`przypadki_punktowane` – przypadki
średniej T3/P3, bez nich).
"""
from __future__ import annotations

#: Parametry przypadku `granica_okna` (punkt 5): okno modelu w znakach, zakładka okien i tolerancja położenia wartości.
GRANICA_OKNA_ZNAKI = 2560
ZAKLADKA_ZNAKI = 448
TOLERANCJA_ZNAKI = 50

# ----- 1. treść ukryta
UKRYTA_DOCX = "ukryta_docx"
UKRYTA_XLSX = "ukryta_xlsx"
UKRYTA_PPTX = "ukryta_pptx"
UKRYTA_PDF = "ukryta_pdf"
UKRYTA_POCZTA = "ukryta_poczta"
# ----- 2. pułapki językowe
ODMIANA_NAZWISK = "odmiana_nazwisk"
NAZWISKA_ZWYKLE_SLOWA = "nazwiska_zwykle_slowa"
ZDROBNIENIA = "zdrobnienia"
NAZWISKO_IMIE = "nazwisko_imie"
PARAFY = "parafy"
LICZBY_SLOWNIE = "liczby_slownie"
# ----- 3. cyrylica – wyłącznie ukraińska
CYRYLICA_DOKUMENT_UK = "cyrylica_dokument_uk"
CYRYLICA_WSTAWKA = "cyrylica_wstawka"
TRANSLITERACJA = "transliteracja"
HOMOGLIFY = "homoglify"
PISOWNIA_ROSYJSKA_IMION = "pisownia_rosyjska_imion"
# ----- 4. identyfikacja pośrednia (osobna miara)
POSREDNIE_FUNKCJA_FIRMA = "posrednie_funkcja_firma"
POSREDNIE_RZADKA_CHOROBA = "posrednie_rzadka_choroba"
POSREDNIE_WIEK_MIEJSCOWOSC = "posrednie_wiek_miejscowosc"
POSREDNIE_DZIALKA_GPS = "posrednie_dzialka_gps"
# ----- 5. długie dokumenty
SKROTY_PO_PELNYM = "skroty_po_pelnym"
GRANICA_OKNA = "granica_okna"
DLUGIE_LISTY_OSOB = "dlugie_listy_osob"
# ----- 6. kodowanie i układ
ZNAKI_ZEROWEJ_SZEROKOSCI = "znaki_zerowej_szerokosci"
RTL = "rtl"
ZEPSUTY_TOUNICODE = "zepsuty_tounicode"
PRZENIESIENIA = "przeniesienia"
DWIE_KOLUMNY = "dwie_kolumny"
OBROCONE_STRONY = "obrocone_strony"
SKAN_PIECZATKI = "skan_pieczatki"
ZRZUT_EKRANU = "zrzut_ekranu"
ZNAK_WODNY = "znak_wodny"
CYTOWANE_WATKI_VCARD = "cytowane_watki_vcard"
FORMATY_RTF_ODT = "formaty_rtf_odt"

PRZYPADKI: dict[str, str] = {
    UKRYTA_DOCX: "treść ukryta w DOCX (w:vanish, kody pól, pola tekstowe, alt text, zakładki, customXml, wykresy, nagłówki pierwszej strony, przypisy końcowe)",
    UKRYTA_XLSX: "treść ukryta w XLSX (ukryte wiersze/kolumny, pivotCache, nazwy zakresów, walidacja z listą nazwisk, formuły ze stałymi)",
    UKRYTA_PPTX: "treść ukryta w PPTX (notatki prelegenta, slajd ukryty, kształt poza obszarem slajdu, alt text, komentarze)",
    UKRYTA_PDF: "treść ukryta w PDF (zaczernienie prostokątem z tekstem pod spodem, warstwa OCR niezgodna z obrazem)",
    UKRYTA_POCZTA: "treść ukryta w poczcie (.msg w .msg, załączniki w PDF)",
    ODMIANA_NAZWISK: "odmiana i liczba mnoga nazwisk",
    NAZWISKA_ZWYKLE_SLOWA: "nazwiska będące zwykłymi słowami",
    ZDROBNIENIA: "zdrobnienia imion",
    NAZWISKO_IMIE: "zapis NAZWISKO Imię",
    PARAFY: "parafy i inicjały",
    LICZBY_SLOWNIE: "PESEL, daty i kwoty zapisane słownie",
    CYRYLICA_DOKUMENT_UK: "cały dokument po ukraińsku (cyrylica, dane ukraińskie: РНОКПП, ЄДРПОУ, IBAN UA, adresy)",
    CYRYLICA_WSTAWKA: "osoba, adres albo identyfikator z Ukrainy cyrylicą w dokumencie PL/EN/DE",
    TRANSLITERACJA: "ta sama osoba ukraińska zapisana cyrylicą i w kilku transliteracjach (każdy zapis = osobna wartość gold)",
    HOMOGLIFY: "nazwisko z wmieszanymi znakami cyrylicy i łaciny o podobnym kształcie (gold = zapis dokładnie z dokumentu)",
    PISOWNIA_ROSYJSKA_IMION: "rosyjska pisownia imion i nazwisk osób ukraińskich (Александр, Ковалёв); dokumenty i dane nadal wyłącznie ukraińskie",
    POSREDNIE_FUNKCJA_FIRMA: "identyfikacja pośrednia: funkcja + firma",
    POSREDNIE_RZADKA_CHOROBA: "identyfikacja pośrednia: rzadka choroba",
    POSREDNIE_WIEK_MIEJSCOWOSC: "identyfikacja pośrednia: wiek + mała miejscowość",
    POSREDNIE_DZIALKA_GPS: "identyfikacja pośrednia: numer działki, współrzędne GPS",
    SKROTY_PO_PELNYM: "długi dokument: pełne nazwisko raz, potem „Pan K.” / inicjały",
    GRANICA_OKNA: f"wartość na granicy okna modelu ({GRANICA_OKNA_ZNAKI} znaków, zakładka {ZAKLADKA_ZNAKI}, ±{TOLERANCJA_ZNAKI})",
    DLUGIE_LISTY_OSOB: "długie listy osób",
    ZNAKI_ZEROWEJ_SZEROKOSCI: "znaki zerowej szerokości w wartościach",
    RTL: "tekst RTL",
    ZEPSUTY_TOUNICODE: "PDF z zepsutym ToUnicode",
    PRZENIESIENIA: "przeniesienia wyrazów („Kowal-\\nski”)",
    DWIE_KOLUMNY: "układ w dwóch kolumnach",
    OBROCONE_STRONY: "obrócone strony",
    SKAN_PIECZATKI: "skan pieczątki z NIP",
    ZRZUT_EKRANU: "zrzut ekranu",
    ZNAK_WODNY: "znak wodny z nazwą klienta",
    CYTOWANE_WATKI_VCARD: "cytowane wątki e-mail z vCard",
    FORMATY_RTF_ODT: "formaty RTF i ODT",
}

#: Punkt 4 specyfikacji – osobna miara, poza miarą główną.
POSREDNIE: frozenset[str] = frozenset({
    POSREDNIE_FUNKCJA_FIRMA, POSREDNIE_RZADKA_CHOROBA, POSREDNIE_WIEK_MIEJSCOWOSC, POSREDNIE_DZIALKA_GPS})

#: Przypadki z punktu 3 (cyrylica ukraińska) – raportowane osobno, poza pięcioma językami Privatizera.
CYRYLICA_UKRAINSKA: frozenset[str] = frozenset({
    CYRYLICA_DOKUMENT_UK, CYRYLICA_WSTAWKA, TRANSLITERACJA, HOMOGLIFY, PISOWNIA_ROSYJSKA_IMION})

#: Przypadki, których generatory są w H1.
H1: tuple[str, ...] = (CYRYLICA_DOKUMENT_UK, CYRYLICA_WSTAWKA, TRANSLITERACJA, HOMOGLIFY, PISOWNIA_ROSYJSKA_IMION)

#: Przypadki, których generatory są w H2 (pułapki językowe i długie dokumenty – punkty 2 i 5 specyfikacji).
H2: tuple[str, ...] = (ODMIANA_NAZWISK, NAZWISKA_ZWYKLE_SLOWA, ZDROBNIENIA, NAZWISKO_IMIE, PARAFY, LICZBY_SLOWNIE,
                       SKROTY_PO_PELNYM, GRANICA_OKNA, DLUGIE_LISTY_OSOB)

#: Przypadki, których generatory są w H3 (treść ukryta w pakiecie DOCX/XLSX/PPTX – punkt 1 specyfikacji).
H3: tuple[str, ...] = (UKRYTA_DOCX, UKRYTA_XLSX, UKRYTA_PPTX)

#: Format pliku przypadków wiążących się z jednym formatem (plan nie losuje innych).
FORMAT_PRZYPADKU: dict[str, str] = {UKRYTA_DOCX: "docx", UKRYTA_XLSX: "xlsx", UKRYTA_PPTX: "pptx"}

#: Przypadki, których generatory są w H4a (PDF, układ i kodowanie – punkt 1 część PDF i punkt 6 specyfikacji).
H4A: tuple[str, ...] = (UKRYTA_PDF, ZNAKI_ZEROWEJ_SZEROKOSCI, RTL, ZEPSUTY_TOUNICODE, PRZENIESIENIA, DWIE_KOLUMNY,
                        OBROCONE_STRONY, SKAN_PIECZATKI, ZRZUT_EKRANU, ZNAK_WODNY)

#: Dozwolone formaty plików przypadków H4a i H4b (plan losuje tylko spośród nich, wg udziałów formatów trzonu; RTF i ODT – formaty
#: spoza trzonu – wg `trudne.UDZIALY_DODATKOWE`).
FORMATY_PRZYPADKU: dict[str, tuple[str, ...]] = {
    UKRYTA_PDF: ("pdf",), ZNAKI_ZEROWEJ_SZEROKOSCI: ("docx", "pdf"), RTL: ("docx", "pdf"), ZEPSUTY_TOUNICODE: ("pdf",),
    PRZENIESIENIA: ("pdf",), DWIE_KOLUMNY: ("docx", "pdf"), OBROCONE_STRONY: ("pdf", "skan"),
    SKAN_PIECZATKI: ("docx", "pdf"), ZRZUT_EKRANU: ("docx", "pdf"), ZNAK_WODNY: ("docx", "pdf")}

#: Przypadki, których generatory są w H4b (poczta – punkt 1; wątki cytowane z vCard, RTF i ODT – punkt 6 specyfikacji).
H4B: tuple[str, ...] = (UKRYTA_POCZTA, CYTOWANE_WATKI_VCARD, FORMATY_RTF_ODT)
FORMATY_PRZYPADKU.update({UKRYTA_POCZTA: ("eml", "msg"), CYTOWANE_WATKI_VCARD: ("eml", "msg"), FORMATY_RTF_ODT: ("rtf", "odt")})

#: Przypadki, których generatory są w H5 (identyfikacja pośrednia – punkt 4 specyfikacji; osobna miara, `POSREDNIE`).
H5: tuple[str, ...] = (POSREDNIE_FUNKCJA_FIRMA, POSREDNIE_RZADKA_CHOROBA, POSREDNIE_WIEK_MIEJSCOWOSC, POSREDNIE_DZIALKA_GPS)

#: Krótkie skróty do identyfikatorów dokumentów warstwy (`h-<skrót>-<język>-<typ>-<nr>`).
SKROTY: dict[str, str] = {CYRYLICA_DOKUMENT_UK: "cu", CYRYLICA_WSTAWKA: "cw", TRANSLITERACJA: "tr", HOMOGLIFY: "hg",
                          PISOWNIA_ROSYJSKA_IMION: "ru",
                          ODMIANA_NAZWISK: "on", NAZWISKA_ZWYKLE_SLOWA: "nz", ZDROBNIENIA: "zd", NAZWISKO_IMIE: "ni",
                          PARAFY: "pf", LICZBY_SLOWNIE: "ls", SKROTY_PO_PELNYM: "sk", GRANICA_OKNA: "go",
                          DLUGIE_LISTY_OSOB: "dl", UKRYTA_DOCX: "ud", UKRYTA_XLSX: "ux", UKRYTA_PPTX: "up",
                          UKRYTA_PDF: "uf", ZNAKI_ZEROWEJ_SZEROKOSCI: "zw", RTL: "rt", ZEPSUTY_TOUNICODE: "zt",
                          PRZENIESIENIA: "pr", DWIE_KOLUMNY: "dk", OBROCONE_STRONY: "os", SKAN_PIECZATKI: "sp",
                          ZRZUT_EKRANU: "ze", ZNAK_WODNY: "zn", UKRYTA_POCZTA: "um", CYTOWANE_WATKI_VCARD: "cv",
                          FORMATY_RTF_ODT: "ro", POSREDNIE_FUNKCJA_FIRMA: "ff", POSREDNIE_RZADKA_CHOROBA: "rc",
                          POSREDNIE_WIEK_MIEJSCOWOSC: "wm", POSREDNIE_DZIALKA_GPS: "dg"}


#: Przypadki, których trudność istnieje tylko w pliku (H6b): tekst poziomu 1 (`.txt`, wejście poziomu tekst) jest w nich zwykłym
#: tekstem dokumentu – treść ukryta, dopiski obrazowe i znak wodny są tylko w `gold_plik`/`gold_obrazy`, a kodowanie, układ
#: stron i format pliku nie przechodzą do linearyzacji. Nie są „przypadkami tekstowymi” T3 (`punktacja.md`: „średnia po
#: przypadkach tekstowych”), wchodzą do P3. `cytowane_watki_vcard` jest tekstowy: cytowany wątek jest w treści wiadomości.
TYLKO_PLIK: frozenset[str] = frozenset({
    UKRYTA_DOCX, UKRYTA_XLSX, UKRYTA_PPTX, UKRYTA_PDF, UKRYTA_POCZTA, ZEPSUTY_TOUNICODE, DWIE_KOLUMNY, OBROCONE_STRONY,
    SKAN_PIECZATKI, ZRZUT_EKRANU, ZNAK_WODNY, FORMATY_RTF_ODT})


def przypadki_punktowane(poziom: str) -> tuple[str, ...]:
    """Przypadki warstwy trudnej wchodzące do punktów (średnia po przypadkach T3/P3, `metodyka/punktacja.md`): rejestr bez
    `POSREDNIE` – identyfikacja pośrednia jest osobną miarą opisową (`metodyka/posrednie.md`). `poziom="tekst"` (T3) – także
    bez `TYLKO_PLIK`; `"plik"` (P3) – wszystkie punktowane. Poziom jest wymagany (bez wartości domyślnej): agregacja T3
    wywołana bez niego nie może po cichu dostać zbioru P3. Agregacja punktów wybiera przypadki wyłącznie tą funkcją."""
    if poziom not in ("tekst", "plik"):
        raise ValueError(f"nieznany poziom: {poziom!r}")
    return tuple(p for p in PRZYPADKI if p not in POSREDNIE and not (poziom == "tekst" and p in TYLKO_PLIK))


def sprawdz(przypadki: list[str] | tuple[str, ...]) -> None:
    """ValueError dla nazwy spoza rejestru."""
    for p in przypadki:
        if p not in PRZYPADKI:
            raise ValueError(f"nieznany przypadek: {p!r}")
