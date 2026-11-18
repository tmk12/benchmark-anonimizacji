"""Ekstrakcja tekstu i obrazów z pliku wynikowego (i oryginalnego) dla sędziego plikowego.

`wydobadz(plik)` zwraca `Wydobycie`: listę `Czesc` (nazwany kawałek pliku z tekstem), obrazy osadzone (do OCR),
liczby struktur i status odczytu. Nazwa części jest „miejscem” wycieku w wyniku. Wszystko, co niesie tekst, jest
skanowane – nic nie zależy od rodzaju wartości:

* **DOCX/XLSX/PPTX (ZIP):** każda część XML → `linie` (tekst sklejony per akapit/komórkę/kształt: `p`, `si`, `is`, liść),
  `dodatkowe` (wartości atrybutów, np. `w:author`; tekst komentarzy XML; tekst bez znaczników ze zdekodowanymi encjami
  i drugi raz surowy XML ze zdekodowanymi encjami – łapie podział między elementami i wartości w CDATA/komentarzach;
  nagłówki wydruku XLSX bez kodów `&L &C &R &"font"` z `&&` → `&`). Obrazy (`*/media/*`) → OCR; osadzone pliki
  (docx/pdf/ole/zip) → rekurencja; inne części binarne → surowy tekst (UTF-8 / UTF-16LE / cp1250). Nazwy części ZIP
  też są skanowane.
* **PDF:** tekst stron (pypdfium2), strumienie po dekompresji (surowe i sklejone ciągi `Tj/TJ`; bez danych obrazów inline
  `BI … ID … EI`), `/Info`, XMP, wszystkie
  teksty ze słowników (adnotacje `/T /Contents /Subj`, pola AcroForm `/V /DV /TU`, nazwy plików osadzonych),
  pliki osadzone (rekurencja), obrazy stron i XObject-y → OCR (skan = jedna strona-obraz). Niezależnie od tego każda
  strona jest renderowana (`renderuj_strony`; strona większa niż `MAKS_BOK_RENDERU_PX` – kafelkami w pełnym dpi) i czytana
  OCR przez sędziego (`obrazy.ocr_stron_pdf`, `plik.ocen_plik`).
* **EML:** wszystkie nagłówki (RFC 2047 zdekodowane), części tekstowe (QP/base64; HTML także bez znaczników), nazwy
  załączników, załączniki rekurencyjnie, obrazy → OCR.
* **MSG (OLE/MAPI):** wszystkie strumienie `__substg1.0_<tag><typ>` (001F UTF-16LE, 001E 8-bitowe cp1252/cp1250,
  binarne: HTML, załączniki rekurencyjnie) oraz pozostałe strumienie jako surowy tekst.
* **DOC:** tekst z konwersji LibreOffice (jak w `render/doc.py`; wynik jak DOCX: części `doc->docx:…`) oraz surowe
  strumienie OLE (SummaryInformation, WordDocument…) zdekodowane cp1250/cp1252/UTF-16LE (także z przesunięciem o bajt);
  strumienie poza właściwościami są `Czesc.binarna` (J3: bez wartości krótkich i inicjałów).
* **RTF:** własny parser (`sedzia/rtf.py`, bez LibreOffice'a – RTF to tekst, rozbiór jest pełniejszy niż konwersja, która gubi
  nieznane grupy): część na miejsce (`rtf:tresc`, `rtf:naglowek`, `rtf:stopka`, `rtf:przypis`, `rtf:komentarz`, `rtf:metadane`,
  `rtf:pole`…, `rtf:*<grupa>` dla każdej innej grupy `{\\*…}` z tekstem), tablice formatu jako części strukturalne, obrazy `\\pict`
  → OCR, obiekty `\\objdata` → rekurencja, surowe bajty (bez długich ciągów szesnastkowych danych obrazów).
* **ODT:** ZIP jak OOXML (każda część XML, nazwy części, obrazy, miniatura); w częściach OpenDocument (`content.xml`, `styles.xml`
  z nagłówkiem i stopką, `meta.xml`) akapitem jest `text:p` i `text:h`, `text:s`/`text:tab`/`text:line-break` dają spacje,
  tabulator i koniec wiersza, a komentarze (`office:annotation` z `dc:creator`), przypisy (`text:note`) i ramki (`draw:frame`)
  zakotwiczone w akapicie są czytane jako osobne linie (nie sklejają się z tekstem akapitu).
* **vCard** (`.vcf`, zwykle załącznik poczty; UTF-8 z BOM-em albo bez, UTF-16): wiersze rozwinięte (RFC 6350 3.2), wartość każdej właściwości (składowe `N`/`ADR`
  rozdzielone, znaki ucieczki zdjęte, QUOTED-PRINTABLE z vCard 2.1 zdekodowane), zdjęcie `PHOTO` → OCR.

Wydobycie pamięta też PDF-y zagnieżdżone (`Wydobycie.pdfy`: przedrostek części i bajty): sędzia czyta OCR ich stron, gdy plik
jest wiadomością (`plik.RODZAJE_POCZTY`) – PDF w załączniku poczty ocenia się tą samą ścieżką co samodzielny PDF.

Rodzaj pliku wynika z bajtów (sygnatury), nie z rozszerzenia; rozszerzenie niezgodne z zawartością = plik nieczytelny.
Status: `PUSTY` (brak pliku / 0 bajtów / poprawny, ale bez żadnego tekstu treści i bez obrazów), `NIECZYTELNY` (nie da się
otworzyć jako swój format), inaczej `OK`.
"""
from __future__ import annotations

import base64
import codecs
import email
import email.header
import email.policy
import hashlib
import html
import io
import quopri
import re
import struct
import tempfile
import unicodedata
import zipfile
from collections import Counter, OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

import olefile
from lxml import etree
from PIL import Image

from . import rtf as _rtf_czytnik
from .normalizacja import polacz_przeniesienia

MAKS_CZESC = 64 * 1024 * 1024
MAKS_GLEBOKOSC = 3
_OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_OBRAZ_ROZSZ = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp")
_AKAPIT = frozenset({"p", "si", "is"})
#: Akapit w częściach OpenDocument (`text:p`, nagłówek `text:h`).
_AKAPIT_ODF = frozenset({"p", "h"})
_ODF_TEXT = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
_ODF_OFFICE = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"
_ODF_DRAW = "{urn:oasis:names:tc:opendocument:xmlns:drawing:1.0}"
_MIMETYP_ODT = b"application/vnd.oasis.opendocument.text"
#: Części ODT z treścią dokumentu (także obiektów osadzonych `Object N/content.xml`) i części-szablony formatu.
_TRESC_ODF = re.compile(r"^(?:[^/]+/)*(?:content|styles)\.xml$")
_STRUKTURALNA_ODF = re.compile(r"^(?:settings\.xml|manifest\.rdf|META-INF/manifest\.xml)$")
_NAGLOWKI_WYDRUKU = frozenset({"oddHeader", "oddFooter", "evenHeader", "evenFooter", "firstHeader", "firstFooter"})
_KODY_NAGLOWKA = re.compile(r'&(?:K[0-9A-Fa-f]{6}|"[^"]*"|\d+|[A-Za-z])')
_ZNACZNIK = re.compile(r"<[^>]*>", re.DOTALL)
_TRESC = re.compile(r"^(?:word/(?:document|header\d*|footer\d*|comments\w*|footnotes|endnotes)\.xml"
                    r"|xl/(?:sharedStrings\.xml|worksheets/[^/]+\.xml|comments[^/]*\.xml|threadedComments/[^/]+\.xml)"
                    r"|ppt/(?:slides|notesSlides|comments)/[^/]+\.xml)$")
_STRUKTURALNA = re.compile(r"^(?:word/(?:styles|stylesWithEffects|fontTable|settings|webSettings|numbering)\.xml"
                           r"|word/theme/[^/]+\.xml|\[Content_Types\]\.xml|xl/styles\.xml|xl/theme/[^/]+\.xml"
                           r"|ppt/(?:presProps|viewProps|tableStyles)\.xml|ppt/theme/[^/]+\.xml)$")
_ESC_X = re.compile(r"_x([0-9A-Fa-f]{4})_")


@dataclass
class Czesc:
    """Nazwany kawałek pliku z tekstem. `linie` = czysty tekst (jednostki: akapit/komórka/wiersz), `dodatkowe` = widoki
    uzupełniające (atrybuty, tekst bez znaczników, surowe bajty zdekodowane) używane tylko do wyszukiwania wycieków."""

    nazwa: str
    linie: list[str] = field(default_factory=list)
    dodatkowe: list[str] = field(default_factory=list)
    #: wartości pojedynczych węzłów (atrybuty XML, stringi słowników PDF, nazwy plików, komentarze XML): osobne teksty,
    #: używane do wyszukiwania ORAZ do słów generycznych oryginału (w przeciwieństwie do `dodatkowe`).
    wezly: list[str] = field(default_factory=list)
    #: część niesie treść dokumentu (korpus, nagłówki/stopki, komentarze, strony PDF, treść wiadomości) – nie metadane.
    tresc: bool = False
    #: część szablonowa formatu (style, czcionki, motyw, ustawienia): nie zawiera danych dokumentu; sędzia jej nie
    #: skanuje (słowo „Roman” w „Times New Roman” nie jest wyciekiem imienia), a jej słowa są generyczne.
    strukturalna: bool = False
    #: druga reprezentacja treści już obecnej w innej części (HTML obok text/plain): nie liczy się do wystąpień.
    wariant: bool = False
    #: (J3) zdekodowane widoki binarnego strumienia OLE pliku DOC (`Data`, `WordDocument`, tabele, obiekty osadzone – wszystko
    #: poza strumieniami właściwości): wartości krótkie (≤ `plik.MAKS_ALNUM_KROTKIEJ` znaków alfanumerycznych) i inicjały nie są
    #: w nich szukane – dwie litery trafiają przypadkowo w bajty binarne zdekodowane jako tekst; tekst dokumentu daje konwersja
    #: LibreOffice (części `doc->docx:`), a właściwości – strumienie `SummaryInformation`. Dłuższe wartości – bez zmian.
    binarna: bool = False

    def caly_tekst(self) -> str:
        """Wszystkie widoki do wyszukiwania w wyniku (linie, węzły i widoki sklejone/surowe)."""
        return "\n".join([*self.linie, *self.wezly, *self.dodatkowe])

    def tekst_wezlowy(self) -> str:
        """Tylko teksty pojedynczych węzłów (linie + węzły): podstawa słów generycznych i liczenia wystąpień."""
        return "\n".join([*self.linie, *self.wezly])


@dataclass
class Wydobycie:
    """Wynik ekstrakcji pliku: części tekstowe, obrazy do OCR (nazwa, bajty), struktura i status."""

    rodzaj: str = ""
    status: str = "OK"            # OK | NIECZYTELNY | PUSTY
    blad: str | None = None
    czesci: list[Czesc] = field(default_factory=list)
    obrazy: list[tuple[str, bytes]] = field(default_factory=list)
    struktura: dict[str, int] = field(default_factory=dict)
    #: PDF-y zagnieżdżone (przedrostek części, bajty) – OCR ich stron dla poczty (`plik.ocr_stron`)
    pdfy: list[tuple[str, bytes]] = field(default_factory=list)

    def ma_tresc(self) -> bool:
        return any("docProps/" not in n for n, _ in self.obrazy) or any(c.tresc and any(l.strip() for l in c.linie) for c in self.czesci)


def widok_bez_przeniesien(linie: list[str]) -> list[str]:
    """Widok uzupełniający z wyrazami sklejonymi po przeniesieniu („Kowal-\\nski”, znacznik U+FFFE z PDFium): `[tekst]`, gdy
    w liniach jest co sklejać, inaczej pusta lista. Służy tylko do wyszukiwania (`Czesc.dodatkowe`)."""
    tekst = "\n".join(linie)
    sklejony = polacz_przeniesienia(tekst)
    return [sklejony] if sklejony != tekst else []


def _silne_rtl(c: str) -> bool:
    return unicodedata.bidirectional(c) in ("R", "AL")


def widok_rtl(linie: list[str]) -> list[str]:
    """Widok uzupełniający dla wierszy z pismem RTL (hebrajski, arabski): PDFium podaje tekst w kolejności wizualnej (litery
    RTL odwrócone w obrębie wyrazu, wyrazy w odwrotnej kolejności), więc wartość w zapisie logicznym („المنارة للتجارة”) nie
    występuje w tekście strony wprost. Widok: każdy wyraz z literą RTL odwrócony (ciągi cyfr w nim zostają), kolejność wyrazów
    bez zmian – wyrazy wartości są wtedy rozpoznawalne (`[tekst]`; pusta lista, gdy nie ma wierszy RTL). Tylko do wyszukiwania."""
    wynik = []
    for linia in linie:
        if not any(_silne_rtl(c) for c in linia):
            continue
        wyrazy = []
        for w in linia.split(" "):
            if any(_silne_rtl(c) for c in w):
                w = re.sub(r"\d+", lambda m: m.group(0)[::-1], w[::-1])
            wyrazy.append(w)
        wynik.append(" ".join(wyrazy))
    return ["\n".join(wynik)] if wynik else []


class BladOdczytu(Exception):
    """Plik nie otwiera się jako swój format."""


def skrot_pliku(sciezka: Path) -> str:
    """sha256 zawartości pliku (klucz pamięci podręcznych)."""
    return hashlib.sha256(Path(sciezka).read_bytes()).hexdigest()


# ----------------------------------------------------------------------------- rozpoznanie rodzaju
def _rodzaj(dane: bytes, nazwa: str = "") -> str:
    if b"%PDF-" in dane[:1024]:
        return "pdf"
    if _rtf_czytnik.jest_rtf(dane):
        return "rtf"
    if _tekst_vcard(dane[:64]).lstrip()[:11].upper() == "BEGIN:VCARD":
        return "vcard"
    if dane[:2] == b"PK":
        try:
            with zipfile.ZipFile(io.BytesIO(dane)) as z:
                n = set(z.namelist())
                mimetyp = z.read("mimetype").strip() if "mimetype" in n else b""
        except zipfile.BadZipFile:
            return "zip_uszkodzony"
        for rodzaj, glowna in (("docx", "word/document.xml"), ("xlsx", "xl/workbook.xml"),
                               ("pptx", "ppt/presentation.xml")):
            if glowna in n:
                return rodzaj
        if mimetyp == _MIMETYP_ODT and "content.xml" in n:
            return "odt"
        return "zip"
    if dane[:8] == _OLE:
        try:
            ole = olefile.OleFileIO(io.BytesIO(dane))
        except Exception:  # noqa: BLE001
            return "ole_uszkodzony"
        try:
            if ole.exists("__properties_version1.0"):
                return "msg"
            return "doc" if ole.exists("WordDocument") else "ole"
        finally:
            ole.close()
    if dane[:8] == b"\x89PNG\r\n\x1a\n" or dane[:3] == b"\xff\xd8\xff" or dane[:4] in (b"GIF8", b"II*\x00", b"MM\x00*") \
            or dane[:2] == b"BM" or (dane[:4] == b"RIFF" and dane[8:12] == b"WEBP"):
        return "obraz"
    glowka = dane[:8192].decode("latin-1", errors="replace")
    if re.search(r"(?im)^(?:from|to|subject|date|message-id|mime-version|received|content-type):", glowka):
        return "eml"
    if nazwa.lower().endswith(_OBRAZ_ROZSZ):
        return "obraz"
    return "txt" if _tekst_jawny(dane) else "inne"


def _tekst_jawny(dane: bytes) -> bool:
    """Zwykły tekst (UTF-8, bez znaków sterujących poza tabulacją i końcami wierszy) – np. `.msg` zapisany przez narzędzie jako `.txt`."""
    if not dane.strip():
        return False
    try:
        tekst = dane[:MAKS_CZESC].decode("utf-8")
    except UnicodeDecodeError:
        return False
    return not re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", tekst)


# ----------------------------------------------------------------------------- pomocnicze dekodowanie
#: Przeplot UTF-16 w bajtach: ≥ 3 kolejne pary „bajt niezerowy + NUL” (tekst ASCII zapisany w UTF-16LE; w UTF-16BE ten sam
#: ciąg przesunięty o bajt).
_PRZEPLOT_UTF16 = re.compile(rb"(?:[^\x00]\x00){3,}")


def _alnum_8bit(bajt: int) -> bool:
    """Bajt jest literą albo cyfrą w odczycie 8-bitowym (cp1250) – znakiem napisu 8-bitowego, nie bajtem przeplotu."""
    return bytes([bajt]).decode("cp1250", errors="replace").isalnum()


def _bez_przeplotu_utf16(dane: bytes) -> bytes:
    """(widoki 8-bitowe: UTF-8, cp1250, latin-1) Bajty przed dekodowaniem 8-bitowym bez NUL-i wewnątrz przeplotu UTF-16
    (`_PRZEPLOT_UTF16`). Bez tego NUL zamieniony na spację (albo zostawiony jako granica) rozstrzela tekst UTF-16
    (`2 4 . 0 8 . 2 0 1 9`), a w tekście rozstrzelonym granica `plik._wzor_id` wypada w środku liczby: koniec daty
    „24.08.2019” trafia w część „82019” sygnatury „XI U 820/19”, której w tekście nie ma.

    Granice przeplotu zostają granicami: przeplot zaczynający się tuż po literze albo cyfrze (`_alnum_8bit`) zaczyna się w istocie
    od ostatniego znaku napisu 8-bitowego z NUL-em kończącym (`Kowalski\x00` + „Tytul” w UTF-16LE: para „i\x00” należy do
    „Kowalski”) – ten NUL zostaje; przeplot, po którym stoi litera albo cyfra, kończy się NUL-em kończącym napis UTF-16 przed
    napisem 8-bitowym (`A\x00B\x00C\x00Kowalski`) – ostatni NUL zostaje. NUL-e poza przeplotem (pojedyncze, podwójne
    terminatory) zostają jak w bajtach. Napis 8-bitowy obok napisu UTF-16 jest więc w widoku 8-bitowym tym samym słowem co bez
    przeplotu, a tekst UTF-16 – zwarty. Widoki UTF-16 (`_surowe_widoki` – UTF-16LE w obu wyrównaniach, PDF – UTF-16BE) liczone
    są z bajtów nietkniętych. Ryzyko resztkowe: napis UTF-16 poprzedzony literą albo cyfrą traci w widoku 8-bitowym pierwszy znak
    (oddzielony NUL-em; ten znak i resztę napisu nadal pokazuje widok UTF-16)."""
    if b"\x00" not in dane:
        return dane

    def zwarty(m: re.Match) -> bytes:
        ciag, pocz, kon = m.group(0), m.start(), m.end()
        glowa = ciag[:2] if pocz > 0 and _alnum_8bit(dane[pocz - 1]) else b""
        reszta = ciag[len(glowa):].replace(b"\x00", b"")
        return glowa + reszta + (b"\x00" if kon < len(dane) and _alnum_8bit(dane[kon]) else b"")
    return _PRZEPLOT_UTF16.sub(zwarty, dane)


def _surowe_widoki(dane: bytes) -> list[str]:
    """Surowe bajty jako tekst: UTF-8, cp1250 (8-bit, bez przeplotu UTF-16 – `_bez_przeplotu_utf16`), UTF-16LE (oba
    wyrównania); wspólne dla części binarnych/OLE."""
    dane = dane[:MAKS_CZESC]
    osem = _bez_przeplotu_utf16(dane)
    widoki = [osem.decode("utf-8", errors="replace"), osem.decode("cp1250", errors="replace"),
              dane.decode("utf-16-le", errors="replace")]
    if len(dane) > 1:
        widoki.append(dane[1:].decode("utf-16-le", errors="replace"))
    return [re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f�]+", " ", w) for w in widoki]


def _widok_utf8(dane: bytes) -> list[str]:
    """Bajty w całości UTF-8 (`_znaki_rtf`) jako jeden widok tekstowy, bez znaków sterujących – jak `_surowe_widoki`, ale bez
    drugiej interpretacji (cp1250, UTF-16) tych samych bajtów."""
    return [re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f�]+", " ",
                   _bez_przeplotu_utf16(dane[:MAKS_CZESC]).decode("utf-8", errors="replace"))]


def _lokalna(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _bez_kodow_naglowka(tekst: str) -> str:
    return _KODY_NAGLOWKA.sub("", tekst.replace("&&", "\0")).replace("\0", "&")


def _zbierz_xml(el: etree._Element, linie: list[str], attr: list[str], dod: list[str],
                akapity: frozenset[str] = _AKAPIT) -> None:
    if not isinstance(el.tag, str):  # komentarz / instrukcja przetwarzania
        if el.text and el.text.strip():
            dod.append(el.text)
        return
    nazwa = _lokalna(el.tag)
    for v in el.attrib.values():
        if v.strip():
            attr.append(v)
    if nazwa in akapity:
        for d in el.iterdescendants():
            if isinstance(d.tag, str):
                attr.extend(v for v in d.attrib.values() if v.strip())
        tekst = "".join(t for t in el.itertext())
        if tekst.strip():
            linie.append(tekst)
        return
    if len(el) == 0:
        if el.text and el.text.strip():
            linie.append(el.text)
            if nazwa in _NAGLOWKI_WYDRUKU:
                dod.append(_bez_kodow_naglowka(el.text))
        return
    if el.text and el.text.strip():
        linie.append(el.text)
    for ch in el:
        _zbierz_xml(ch, linie, attr, dod, akapity)
        if ch.tail and ch.tail.strip():
            linie.append(ch.tail)


def _odkoduj_x(tekst: str) -> str:
    """OOXML zapisuje znaki sterujące jako `_xHHHH_` (np. nowa linia w nagłówku wydruku `_x000a_`)."""
    return _ESC_X.sub(lambda m: chr(int(m.group(1), 16)), tekst) if "_x" in tekst else tekst


def _odf_przygotuj(root: etree._Element) -> None:
    """Część OpenDocument: `text:s`/`text:tab`/`text:line-break` jako znaki, a komentarz, przypis i ramka zakotwiczone w akapicie
    przeniesione za akapit (osobne linie zamiast sklejenia z tekstem akapitu; ogon elementu zostaje w akapicie)."""
    for el in list(root.iter(f"{_ODF_TEXT}s", f"{_ODF_TEXT}tab", f"{_ODF_TEXT}line-break")):
        nazwa = _lokalna(el.tag)
        znak = " " * int(el.get(f"{_ODF_TEXT}c", "1") or 1) if nazwa == "s" else "\t" if nazwa == "tab" else "\n"
        el.tail = znak + (el.tail or "")
    for el in list(root.iter(f"{_ODF_OFFICE}annotation", f"{_ODF_TEXT}note", f"{_ODF_DRAW}frame", f"{_ODF_DRAW}custom-shape")):
        akapit = next((a for a in el.iterancestors() if isinstance(a.tag, str) and a.tag.startswith(_ODF_TEXT)
                       and _lokalna(a.tag) in _AKAPIT_ODF), None)
        if akapit is None:
            continue
        rodzic, poprzedni = el.getparent(), el.getprevious()
        if el.tail:
            if poprzedni is not None:
                poprzedni.tail = (poprzedni.tail or "") + el.tail
            else:
                rodzic.text = (rodzic.text or "") + el.tail
        el.tail = None
        akapit.addnext(el)


def czesc_xml(nazwa: str, dane: bytes, scisle: bool = False, plain: str | None = None, odf: bool = False) -> Czesc:
    """Część XML jako `Czesc` (patrz docstring modułu). `scisle`: błąd parsowania = `BladOdczytu`; `plain` – nazwa
    części w pakiecie (bez przedrostka załącznika), wg której ustalane są flagi `tresc`/`strukturalna`; `odf` – część
    pakietu OpenDocument (akapity `text:p`/`text:h`, `_odf_przygotuj`)."""
    plain = nazwa if plain is None else plain
    surowy = dane.decode("utf-8", errors="replace")
    if odf:
        c = Czesc(nazwa, tresc=bool(_TRESC_ODF.match(plain)), strukturalna=bool(_STRUKTURALNA_ODF.match(plain)))
    else:
        c = Czesc(nazwa, tresc=bool(_TRESC.match(plain)), strukturalna=bool(_STRUKTURALNA.match(plain)))
    try:
        root = etree.fromstring(dane, etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True))
    except etree.XMLSyntaxError as e:
        if scisle:
            raise BladOdczytu(f"{nazwa}: niepoprawny XML ({e})") from e
        c.dodatkowe += [html.unescape(surowy), html.unescape(_ZNACZNIK.sub(" ", surowy))]
        return c
    attr: list[str] = []
    dod: list[str] = []
    if odf:
        _odf_przygotuj(root)
    _zbierz_xml(root, c.linie, attr, dod, _AKAPIT_ODF if odf else _AKAPIT)
    c.linie = [_odkoduj_x(l) for l in c.linie]
    c.wezly = [_odkoduj_x(l) for l in [*attr, *dod]]
    # widok sklejony (tekst bez znaczników; wartość rozbita między elementami) – tylko do szukania w wyniku; surowego
    # XML (nazwy znaczników i atrybutów) NIE dodajemy, żeby słownik formatu nie udawał treści
    bez_znacznikow = html.unescape(_ZNACZNIK.sub("", surowy))
    c.dodatkowe.append(_odkoduj_x(bez_znacznikow))
    if "&#" in bez_znacznikow or "&amp;" in bez_znacznikow:  # podwójnie zakodowane encje
        c.dodatkowe.append(html.unescape(bez_znacznikow))
    return c


def _tekst_html(surowy: str) -> tuple[str, str]:
    """(tekst bez znaczników, ten sam ze zdekodowanymi encjami z surowego HTML)."""
    return html.unescape(_ZNACZNIK.sub(" ", surowy)), html.unescape(surowy)


def _dodaj_obraz(w: Wydobycie, nazwa: str, dane: bytes) -> None:
    w.obrazy.append((nazwa, dane))
    try:  # metadane obrazu (PNG tEXt, EXIF) mogą nieść tekst
        with Image.open(io.BytesIO(dane)) as im:
            info = [str(v) for v in im.info.values() if isinstance(v, (str, bytes))]
            try:
                info += [str(v) for v in im.getexif().values() if isinstance(v, (str, bytes))]
            except Exception:  # noqa: BLE001
                pass
        if info:
            w.czesci.append(Czesc(f"metadane obrazu:{nazwa}", wezly=info))
    except Exception:  # noqa: BLE001
        pass


# ----------------------------------------------------------------------------- rodzaje
#: Binarne ustawienia drukarki z szablonu OOXML (`printerSettings*.bin`) – nigdy miejsce danych; ich bajty dawały
#: fałszywe wycieki (token częściowy w binarium). Inne `.bin` (`oleObject*.bin`, `vbaProject.bin`) zostają przeszukiwane.
_USTAWIENIA_DRUKARKI = re.compile(r"(^|/)printerSettings/[^/]+\.bin$")
#: Rodzaje plików osadzonych/załączonych rozbierane rekurencyjnie (reszta – surowe widoki).
_ZAGNIEZDZANE = frozenset({"pdf", "docx", "xlsx", "pptx", "odt", "msg", "doc", "zip", "eml", "rtf", "vcard"})


def _zip(dane: bytes, pref: str, w: Wydobycie, rodzaj: str, scisle: bool, gl: int) -> None:
    try:
        z = zipfile.ZipFile(io.BytesIO(dane))
    except zipfile.BadZipFile as e:
        raise BladOdczytu(f"{pref}ZIP uszkodzony") from e
    with z:
        if scisle and z.testzip() is not None:
            raise BladOdczytu(f"{pref}ZIP: błędna suma kontrolna części")
        w.czesci.append(Czesc(f"{pref}zip:nazwy", wezly=[*z.namelist(), z.comment.decode("utf-8", "replace")]))
        for info in z.infolist():
            nazwa = info.filename
            if nazwa.endswith("/") or info.file_size > MAKS_CZESC:
                continue
            if _USTAWIENIA_DRUKARKI.search(nazwa):
                continue
            surowe = z.read(info)
            niskie = nazwa.lower()
            if niskie.endswith(_OBRAZ_ROZSZ):
                _dodaj_obraz(w, f"{pref}{nazwa}", surowe)
            elif niskie.endswith((".xml", ".rels", ".vml", ".xsl", ".rdf")) or surowe[:5] == b"<?xml":
                glowna = scisle and nazwa in ("word/document.xml", "xl/workbook.xml", "ppt/presentation.xml", "content.xml")
                w.czesci.append(czesc_xml(f"{pref}{nazwa}", surowe, glowna, plain=nazwa, odf=rodzaj == "odt"))
            else:
                podrodzaj = _rodzaj(surowe, nazwa)
                if podrodzaj in _ZAGNIEZDZANE and gl < MAKS_GLEBOKOSC:
                    _bajty(surowe, nazwa, f"{pref}{nazwa}/", w, gl + 1)
                else:
                    w.czesci.append(Czesc(f"{pref}{nazwa}", dodatkowe=_surowe_widoki(surowe)))
    if rodzaj == "xlsx":
        _powtorz_wspoldzielone(dane, pref, w)
    if rodzaj == "docx" and not pref:
        w.struktura.update(_struktura_docx(dane))
    elif rodzaj == "xlsx" and not pref:
        w.struktura.update(_struktura_xlsx(dane))
    elif rodzaj == "pptx" and not pref:
        w.struktura.update(_struktura_pptx(dane))
    elif rodzaj == "odt" and not pref:
        w.struktura.update(_struktura_odt(dane))


def _powtorz_wspoldzielone(dane: bytes, pref: str, w: Wydobycie) -> None:
    """XLSX trzyma powtarzający się tekst raz (`sharedStrings`), a komórki tylko go wskazują. Linie `sharedStrings`
    powtarzamy tyle razy, ile komórek je wskazuje, żeby liczba wystąpień odpowiadała komórkom (gold ma `Wartosc` na komórkę)."""
    with zipfile.ZipFile(io.BytesIO(dane)) as z:
        uzycia: Counter = Counter()
        sst = [_odkoduj_x("".join(si.itertext())) for si in etree.fromstring(z.read("xl/sharedStrings.xml")).iter(f"{_S}si")] \
            if "xl/sharedStrings.xml" in z.namelist() else []
        for n in z.namelist():
            if re.match(r"xl/worksheets/[^/]+\.xml$", n):
                for c in etree.fromstring(z.read(n)).iter(f"{_S}c"):
                    if c.get("t") == "s":
                        v = c.find(f"{_S}v")
                        if v is not None and v.text and v.text.strip().isdigit():
                            uzycia[int(v.text)] += 1
    for c in w.czesci:
        if c.nazwa == f"{pref}xl/sharedStrings.xml":
            c.linie = [l for i, l in enumerate(sst) if l.strip() for _ in range(max(1, uzycia.get(i, 1)))]


def _licz(dane: bytes, nazwa: str, tag: str) -> int:
    with zipfile.ZipFile(io.BytesIO(dane)) as z:
        return sum(1 for _ in etree.fromstring(z.read(nazwa)).iter(tag)) if nazwa in z.namelist() else 0


_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _struktura_docx(dane: bytes) -> dict[str, int]:
    return {"akapity": _licz(dane, "word/document.xml", f"{_W}p"), "tabele": _licz(dane, "word/document.xml", f"{_W}tbl")}


def _struktura_xlsx(dane: bytes) -> dict[str, int]:
    with zipfile.ZipFile(io.BytesIO(dane)) as z:
        arkusze = _licz(dane, "xl/workbook.xml", f"{_S}sheet")
        wiersze = sum(1 for n in z.namelist() if re.match(r"xl/worksheets/[^/]+\.xml$", n)
                      for _ in etree.fromstring(z.read(n)).iter(f"{_S}row"))
    return {"arkusze": arkusze, "wiersze": wiersze}


def _struktura_odt(dane: bytes) -> dict[str, int]:
    akapity = _licz(dane, "content.xml", f"{_ODF_TEXT}p") + _licz(dane, "content.xml", f"{_ODF_TEXT}h")
    return {"akapity": akapity, "tabele": _licz(dane, "content.xml", "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}table")}


def _struktura_pptx(dane: bytes) -> dict[str, int]:
    with zipfile.ZipFile(io.BytesIO(dane)) as z:
        return {"slajdy": sum(1 for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n))}


def _pdf(dane: bytes, pref: str, w: Wydobycie, scisle: bool, gl: int) -> None:
    import pikepdf
    import pypdfium2 as pdfium
    try:
        pdf = pikepdf.open(io.BytesIO(dane))
    except Exception as e:  # noqa: BLE001 - pikepdf.PdfError i pokrewne
        raise BladOdczytu(f"{pref}PDF nie otwiera się: {type(e).__name__}") from e
    with pdf:
        n = len(pdf.pages)
        if scisle and n == 0:
            raise BladOdczytu("PDF bez stron")
        if not pref:
            w.struktura["strony"] = n
        else:
            w.pdfy.append((pref, dane))
        try:
            doc = pdfium.PdfDocument(dane)
        except Exception:  # noqa: BLE001 - pikepdf otworzył; tekst stron pominięty
            doc = None
        if doc is not None:
            try:
                for i in range(len(doc)):
                    strona_pdfium = doc[i]
                    if strona_pdfium.get_rotation():     # strona obrócona (`/Rotate`): PDFium przestawia kolejność wierszy
                        strona_pdfium.set_rotation(0)    # wg układu na ekranie, a nas obchodzi tekst w kolejności treści
                    tp = strona_pdfium.get_textpage()
                    tekst = tp.get_text_range()
                    tp.close()
                    linie = [l for l in tekst.splitlines() if l.strip()]
                    w.czesci.append(Czesc(f"{pref}pdf:strona {i + 1}", linie=linie, tresc=True,
                                          dodatkowe=[*widok_bez_przeniesien(linie), *widok_rtl(linie)]))
            finally:
                doc.close()
        info = []
        for k, v in pdf.docinfo.items():
            try:
                info.append(f"{str(k).lstrip('/')}: {v}")
            except Exception:  # noqa: BLE001
                pass
        w.czesci.append(Czesc(f"{pref}pdf:/Info", linie=info))
        slowniki: list[str] = []
        strumienie: list[str] = []
        widziane_obrazy: set[tuple[int, int]] = set()
        for obj in pdf.objects:
            _stringi_pdf(obj, slowniki, 0)
            if isinstance(obj, pikepdf.Stream):
                podtyp = str(obj.get("/Subtype", ""))
                if podtyp == "/Image" or "/Length1" in obj or "/Length2" in obj:
                    continue
                try:
                    surowe = obj.read_bytes()
                except Exception:  # noqa: BLE001 - nieobsługiwany filtr
                    continue
                if len(surowe) > 8 * 1024 * 1024:
                    continue
                surowe = _bez_obrazow_inline(surowe)
                if str(obj.get("/Type", "")) == "/Metadata":
                    w.czesci.append(czesc_xml(f"{pref}pdf:XMP", surowe))
                else:
                    strumienie += [*_widoki_strumienia(surowe), *(_sklejone_ciagi(surowe) if _tekstowy(surowe) else [])]
        w.czesci.append(Czesc(f"{pref}pdf:słowniki", wezly=slowniki))
        w.czesci.append(Czesc(f"{pref}pdf:strumienie", dodatkowe=strumienie))
        w.czesci.append(Czesc(f"{pref}pdf:surowe", dodatkowe=_surowe_pdf(dane)))
        for i, strona in enumerate(pdf.pages):
            try:
                obrazy = list(strona.images.items())
            except Exception:  # noqa: BLE001
                obrazy = []
            for nazwa, im in obrazy:
                klucz = im.objgen
                if klucz in widziane_obrazy:
                    continue
                widziane_obrazy.add(klucz)
                bajty = _bajty_obrazu_pdf(im)
                if bajty is not None:
                    _dodaj_obraz(w, f"{pref}pdf:strona {i + 1}/{str(nazwa).lstrip('/')}", bajty)
        # obrazy poza zasobami strony (formularze nakładek: znak wodny, adnotacje, wzorce); maski przezroczystości (/SMask,
        # /Mask) są kanałem alfa obrazu-rodzica (pikepdf składa je przy odczycie rodzica), więc samodzielnie czytamy je dopiero
        # wtedy, gdy rodzic nie został przeczytany (np. atrapa nieużywana, a maska rysowana gdzie indziej)
        rodzice_masek: dict[tuple, list[tuple]] = {}
        for o in pdf.objects:
            if isinstance(o, pikepdf.Stream):
                for k in ("/SMask", "/Mask"):
                    m = o.get(k)
                    if isinstance(m, pikepdf.Stream):
                        rodzice_masek.setdefault(m.objgen, []).append(o.objgen)
        rysowane = _obrazy_w_zasobach(pdf)       # maska rysowana też sama (Do) jest widocznym obrazem, nie tylko alfą rodzica
        obrazy_pdf = [o for o in pdf.objects if isinstance(o, pikepdf.Stream) and str(o.get("/Subtype", "")) == "/Image"]
        for maski_w_tej_turze in (False, True):
            for obj in obrazy_pdf:
                if (obj.objgen in rodzice_masek) != maski_w_tej_turze or obj.objgen in widziane_obrazy:
                    continue
                if (maski_w_tej_turze and obj.objgen not in rysowane
                        and any(r in widziane_obrazy for r in rodzice_masek[obj.objgen])):
                    continue
                widziane_obrazy.add(obj.objgen)
                bajty = _bajty_obrazu_pdf(obj)
                if bajty is not None:
                    _dodaj_obraz(w, f"{pref}pdf:obiekt {obj.objgen[0]}", bajty)
        try:
            zalaczniki = list(pdf.attachments.items())
        except Exception:  # noqa: BLE001
            zalaczniki = []
        for nazwa, zal in zalaczniki:
            w.czesci.append(Czesc(f"{pref}pdf:załączniki", dodatkowe=[nazwa]))
            if gl < MAKS_GLEBOKOSC:
                try:
                    _bajty(zal.get_file().read_bytes(), nazwa, f"{pref}pdf:zal({nazwa})/", w, gl + 1)
                except Exception:  # noqa: BLE001
                    pass


def _bajty_obrazu_pdf(im) -> bytes | None:
    """Obraz PDF jako bajty PNG/JPEG do OCR; None, gdy filtr nie jest wspierany (JBIG2, JPX…)."""
    import pikepdf
    try:
        pi = pikepdf.PdfImage(im)
        if pi.filters == ["/DCTDecode"]:
            return im.read_raw_bytes()
        bufor = io.BytesIO()
        pi.as_pil_image().save(bufor, format="PNG")
        return bufor.getvalue()
    except Exception:  # noqa: BLE001 - niewspierany filtr: brak OCR tego obrazu
        return None


def _stringi_pdf(obj, wynik: list[str], glebokosc: int) -> None:
    """Wszystkie stringi obiektu PDF, rekurencyjnie po słownikach i tablicach (np. `/A << /URI … >>`, `/MK << /CA … >>`,
    `/OpenAction`, drzewa nazw, struktury w nieindeksowanych obiektach)."""
    import pikepdf
    if glebokosc > 12:
        return
    try:
        if isinstance(obj, pikepdf.String):
            wynik.append(str(obj))
        elif isinstance(obj, pikepdf.Name):
            wynik.append(str(obj).lstrip("/"))
        elif isinstance(obj, (pikepdf.Dictionary, pikepdf.Stream)):
            for k, v in obj.items():
                wynik.append(str(k).lstrip("/"))
                if not getattr(v, "is_indirect", False):
                    _stringi_pdf(v, wynik, glebokosc + 1)
        elif isinstance(obj, pikepdf.Array):
            for v in obj:
                if not getattr(v, "is_indirect", False):
                    _stringi_pdf(v, wynik, glebokosc + 1)
    except Exception:  # noqa: BLE001
        pass


def _tekstowy(surowe: bytes) -> bool:
    """Heurystyka: strumień z tekstem/operatorami, nie dane binarne (piksele, fonty) – te są pomijane w widokach."""
    probka = surowe[:4096]
    return bool(probka) and sum(32 <= b < 127 or b in (9, 10, 13) for b in probka) / len(probka) >= 0.7


def _bez_obrazow_inline(dane: bytes) -> bytes:
    """Treść strony bez danych obrazów inline (`BI … ID <dane> EI`): dane obrazu (zwykle ASCII85 – wygląda jak tekst) nie są
    tekstem, a w widokach latin-1/cp1250 krótkie tokeny („rue”, „mai”) trafiałyby w nie przypadkiem. Obraz strony i tak czyta
    OCR stron. Dane obrazów lokalizuje parser treści pikepdf; strumień bez obrazów inline albo nieparsowalny – bez zmian."""
    if b"BI" not in dane or b"ID" not in dane or b"EI" not in dane:
        return dane
    import warnings

    import pikepdf
    try:
        with pikepdf.new() as p, warnings.catch_warnings():
            warnings.simplefilter("ignore")              # strumień, który nie jest treścią strony („Unexpected end of stream”)
            obrazy = [op.iimage.read_raw_bytes() for op in pikepdf.parse_content_stream(pikepdf.Stream(p, dane))
                      if isinstance(op, pikepdf.ContentStreamInlineImage)]
    except Exception:  # noqa: BLE001 - nie jest treścią strony
        return dane
    czesci, poz = [], 0
    for surowe in obrazy:
        i = dane.find(surowe, poz) if surowe else -1
        bi = dane.rfind(b"BI", poz, i) if i >= 0 else -1
        ei = dane.find(b"EI", i + len(surowe)) if bi >= 0 else -1
        if ei < 0:
            continue
        czesci += [dane[poz:bi], b" "]
        poz = ei + 2
    return b"".join(czesci) + dane[poz:] if czesci else dane


#: (widoki surowe PDF) Litera, którą zastępujemy znak stringu PDF niebędący ani tekstem ASCII, ani białym znakiem: kod glifu
#: podzbioru czcionki („Umowa o stałą obsługę prawną” – w strumieniu `(… prawn\\002)`), bajt spoza ASCII, znak sterujący. Jest
#: częścią słowa, nie jego granicą (jak `\\uN`/`\\'xx` w `_znaki_rtf`): ucięte „prawn” nie jest formą „Prawna” z wartości
#: „Kancelaria Prawna Mazovia”. Litera niepodobna do żadnego tokenu gold (jak `plik.ZNAK_ZAMIENNIKA`).
_ZNAK_W_SLOWIE_PDF = "ǂ"
#: Ucieczka ósemkowa stringu literalnego (`\\002`, `\\350`); `\\\\` – ukośnik w tekście (nie ucieczka).
_OSEMKOWA_PDF = re.compile(r"\\\\|\\([0-7]{1,3})")
#: Znaki sterujące w zdekodowanym stringu (C0 bez białych znaków `\\t \\n \\v \\f \\r`, DEL, C1); NUL zostaje granicą
#: (pojedynczy NUL; NUL-e przeplotu UTF-16 usuwa przed dekodowaniem `_bez_przeplotu_utf16`).
_STERUJACE_PDF = re.compile(r"[\x01-\x08\x0e-\x1f\x7f-\x9f]")


def _osemkowe_w_slowie(tekst: str) -> str:
    """(widoki surowe PDF: bajty pliku i strumienie) Ucieczka ósemkowa: znak ASCII drukowalny albo biały – ten znak; inny bajt
    (kod glifu, znak sterujący, bajt spoza ASCII, którego znaczenie zależy od kodowania czcionki) – `_ZNAK_W_SLOWIE_PDF`."""
    def znak(m: re.Match) -> str:
        if m.group(1) is None:
            return m.group(0)
        c = int(m.group(1), 8) & 0xFF
        return chr(c) if 0x20 <= c < 0x7F or 0x09 <= c <= 0x0D else _ZNAK_W_SLOWIE_PDF
    return _OSEMKOWA_PDF.sub(znak, tekst)


def _widoki_strumienia(surowe: bytes) -> list[str]:
    """Strumień po dekompresji jako tekst: latin-1, cp1250, UTF-8 (bez przeplotu UTF-16 – `_bez_przeplotu_utf16`) i UTF-16BE
    (stringi Unicode w PDF); ucieczki ósemkowe – `_osemkowe_w_slowie`."""
    if not _tekstowy(surowe):
        return []
    surowe = surowe[:4 * 1024 * 1024]
    osem = _bez_przeplotu_utf16(surowe)
    return [_osemkowe_w_slowie(t) for t in (osem.decode("latin-1"), osem.decode("cp1250", errors="replace"),
                                             osem.decode("utf-8", errors="replace"),
                                             surowe.decode("utf-16-be", errors="replace"))]


_HEX_PDF = re.compile(rb"(?<!<)<([0-9A-Fa-f\s]{4,})>(?!>)")
_ESC_PDF = {ord("n"): 10, ord("r"): 13, ord("t"): 9, ord("b"): 8, ord("f"): 12}


def _tekst_z_bajtow_pdf(b: bytes) -> list[str]:
    """Bajty stringa PDF jako tekst: z BOM-em – UTF-16BE/LE albo UTF-8; bez BOM-u – PDFDocEncoding (~latin-1) i cp1250 (bez
    przeplotu UTF-16 – `_bez_przeplotu_utf16`) oraz UTF-16BE."""
    if b[:2] == b"\xfe\xff":
        return [b[2:].decode("utf-16-be", errors="replace")]
    if b[:2] == b"\xff\xfe":
        return [b[2:].decode("utf-16-le", errors="replace")]
    if b[:3] == b"\xef\xbb\xbf":
        return [b[3:].decode("utf-8", errors="replace")]
    osem = _bez_przeplotu_utf16(b)
    return [osem.decode("latin-1"), osem.decode("cp1250", errors="replace"), b.decode("utf-16-be", errors="replace")]


def _stringi_pdf_z_bajtow(dane: bytes) -> list[str]:
    """Stringi PDF zapisane wprost w bajtach (poza strumieniami): szesnastkowe `<feff…>` i literalne `(…)` z
    escape'ami (`\\n`, `\\(`, `\\ddd`) i zagnieżdżonymi nawiasami. Znak sterujący zdekodowanego stringu (kod glifu podzbioru
    czcionki: `PRAWN\\x02`) jest częścią słowa – `_ZNAK_W_SLOWIE_PDF`."""
    dane = dane[:2 * 1024 * 1024]
    wynik: list[str] = []
    for m in _HEX_PDF.finditer(dane):
        h = re.sub(rb"\s", b"", m.group(1))
        if len(h) % 2:
            h += b"0"
        wynik += _tekst_z_bajtow_pdf(bytes.fromhex(h.decode()))
    i, n = 0, len(dane)
    while True:
        i = dane.find(b"(", i)
        if i == -1 or i >= n:
            break
        glebokosc, j, buf = 1, i + 1, bytearray()
        while j < n and glebokosc:
            c = dane[j]
            if c == 0x5C and j + 1 < n:          # backslash
                d = dane[j + 1]
                if 0x30 <= d <= 0x37:             # ósemkowo, do 3 cyfr
                    k = j + 1
                    while k < min(n, j + 4) and 0x30 <= dane[k] <= 0x37:
                        k += 1
                    buf.append(int(dane[j + 1:k], 8) & 0xFF)
                    j = k
                    continue
                if d in (10, 13):                 # kontynuacja wiersza
                    j += 2
                    continue
                buf.append(_ESC_PDF.get(d, d))
                j += 2
                continue
            if c == 0x28:
                glebokosc += 1
            elif c == 0x29:
                glebokosc -= 1
                if not glebokosc:
                    break
            buf.append(c)
            j += 1
        if len(buf) >= 2:
            wynik += _tekst_z_bajtow_pdf(bytes(buf))
        i = j + 1
    return [_STERUJACE_PDF.sub(_ZNAK_W_SLOWIE_PDF, t) for t in wynik]


def _a85(blok: bytes) -> bytes:
    try:
        return base64.a85decode(blok.strip().removesuffix(b"~>"), adobe=False, ignorechars=b" \t\n\r\v\f")
    except ValueError:
        return b""


def _obrazy_w_zasobach(pdf) -> set[tuple]:
    """Identyfikatory obiektów wskazanych w słownikach `/XObject` zasobów stron i formularzy (obrazy rysowane operatorem `Do`)."""
    import pikepdf
    wynik: set[tuple] = set()
    for o in pdf.objects:
        if not isinstance(o, (pikepdf.Dictionary, pikepdf.Stream)):
            continue
        zasoby = o.get("/Resources")
        for kandydat in (o, zasoby):
            xo = kandydat.get("/XObject") if isinstance(kandydat, (pikepdf.Dictionary, pikepdf.Stream)) else None
            if isinstance(xo, pikepdf.Dictionary):
                for _, wartosc in xo.items():
                    if isinstance(wartosc, pikepdf.Stream):
                        wynik.add(wartosc.objgen)
    return wynik


_STREAM = re.compile(rb"stream\r?\n(.*?)\r?\n?endstream", re.DOTALL)
_NAZWA_PDF = re.compile(rb"/([^\s/<>\[\]()%{}]+)")
_HEX_NAZWY = re.compile(rb"#([0-9A-Fa-f]{2})")
#: Słownictwo formatu PDF: nazwy kluczy i standardowych wartości (ISO 32000-1/-2). Tylko one są wycinane z widoku surowego
#: (`/Info` w trailerze nie może dawać częściowego wycieku „info” z adresu info@…); każda inna nazwa (np. `/Marka#20Filipka` –
#: dane w nazwie z niedbałego generatora, klucz `/Dests`, nazwa pola) zostaje w widoku jako tekst zdekodowany (`#xx`).
NAZWY_FORMATU_PDF: frozenset[str] = frozenset(
    "Info Root Size Prev ID Encrypt XRefStm Type Subtype Catalog Pages Page Kids Count Parent Font FontDescriptor FontFile "
    "FontFile2 FontFile3 FontName FontBBox FontMatrix Flags Ascent Descent CapHeight ItalicAngle StemV StemH XHeight "
    "Leading AvgWidth MissingWidth BaseFont Encoding Differences FirstChar LastChar Widths W W2 DW DW2 CIDSystemInfo "
    "CIDToGIDMap CIDFontType0 CIDFontType2 Type0 Type1 Type3 TrueType MMType1 Identity Identity-H Identity-V WinAnsiEncoding "
    "MacRomanEncoding MacExpertEncoding StandardEncoding PDFDocEncoding DescendantFonts ToUnicode Registry Ordering "
    "Supplement Contents Resources MediaBox CropBox BleedBox TrimBox ArtBox Rotate UserUnit Group Tabs Annots StructParents "
    "ProcSet ExtGState XObject ColorSpace Pattern Shading Properties Form Image PS Width Height BitsPerComponent "
    "ColorTransform Decode ImageMask Mask SMask SMaskInData Matte Interpolate Intent Alternates Mask Length Length1 Length2 "
    "Length3 Filter DecodeParms FlateDecode LZWDecode ASCII85Decode ASCIIHexDecode RunLengthDecode CCITTFaxDecode "
    "DCTDecode JBIG2Decode JPXDecode Crypt Predictor Colors Columns EarlyChange K Rows BlackIs1 EncodedByteAlign "
    "EndOfLine EndOfBlock Index N First Extends DeviceGray DeviceRGB DeviceCMYK CalGray CalRGB Lab ICCBased Indexed "
    "Separation DeviceN Alternate Range DeviceGray G RGB CMYK I Cs1 Cs2 Gs0 Gs1 F0 F1 F2 F3 F4 F5 F6 F7 Im0 Im1 Im2 Im3 "
    "Fm0 Fm1 Ca ca CA BM SA Normal Multiply Screen Overlay Darken Lighten Metadata XML Author Title Subject Keywords Creator "
    "Producer CreationDate ModDate Trapped Metadata ViewerPreferences PageLayout PageMode Outlines Names OpenAction "
    "Lang MarkInfo Marked StructTreeRoot AcroForm Fields NeedAppearances SigFlags XFA DA DR Q DV FT Ff T TU TM V AP AS "
    "MK Btn Tx Ch Sig Widget Link Text Popup Border BS H A S URI GoTo Launch Rect Dest FitH FitV Fit XYZ Opt Annot "
    "Print Subtype Embedded EmbeddedFile EmbeddedFiles EF UF Filespec Desc AFRelationship Params Size ModDate CheckSum "
    "Linearized Linearization O E L T Lin XRef ObjStm Extends Pages OC OCG OCGs OCProperties D ON OFF BaseState Order "
    "Layer View Print Export Usage Optional Name NumberOfPages PageLabels Nums Limits Kids Names Threads Beads "
    "Transparency Pattern PatternType PaintType TilingType XStep YStep BBox Shading ShadingType Coords Function "
    "FunctionType Domain Functions Bounds Encode Extend FormType Tr TR2 BG UCR HT TK Default Border C Contents "
    "ASCIIHex Reason Location ContactInfo Cert Prop_Build Perms DocMDP Reference TransformMethod TransformParams "
    "P V R U UE OE Perms CF StmF StrF StdCF AESV2 AESV3 V2 None Identity CFM AuthEvent EncryptMetadata Standard "
    "EFF Rotate Tabs S Pg K Obj Alt ActualText E Lang Placement BBox O RoleMap ClassMap ParentTree IDTree "
    "Artifact Span P Figure Table TR TD TH Document Sect Part Art Div L LI Lbl LBody H1 H2 H3 H4 H5 H6 NonStruct "
    "True False Null".split())


def _nazwa_pdf_na_tekst(m: re.Match) -> bytes:
    """Nazwa ze słownictwa PDF znika (spacja); każda inna wraca jako zdekodowany tekst (`#20` → spacja)."""
    zdekodowana = _HEX_NAZWY.sub(lambda h: bytes([int(h.group(1), 16)]), m.group(1))
    try:
        if zdekodowana.decode("ascii") in NAZWY_FORMATU_PDF:
            return b" "
    except UnicodeDecodeError:
        pass
    return b" " + zdekodowana + b" "


def _surowe_pdf(dane: bytes) -> list[str]:
    """Cały plik niezależnie od tablicy xref (stare rewizje aktualizacji przyrostowych, osierocone obiekty): bajty pliku
    jako tekst oraz każdy blok `stream…endstream` próbowany jako zlib."""
    import zlib
    bez_strumieni = _STREAM.sub(b"", dane)   # strumienie rozpakowujemy niżej; tu zwykłe bajty obiektów
    # nazwy ze słownictwa PDF (`/Info`, `/Root`, `/Type`…) nie są treścią: bez nich „info” z adresu info@… nie wyciekałoby
    # z każdego pliku (tablica trailera ma `/Info`); pozostałe nazwy (dane w nazwie, np. `/Marka#20Filipka`) zostają jako tekst
    bez_nazw = _bez_przeplotu_utf16(_NAZWA_PDF.sub(_nazwa_pdf_na_tekst, bez_strumieni))
    wynik = [_osemkowe_w_slowie(bez_nazw.decode("latin-1")), _osemkowe_w_slowie(bez_nazw.decode("utf-8", errors="replace")),
             *_stringi_pdf_z_bajtow(bez_strumieni)]
    for m in _STREAM.finditer(dane):
        blok = m.group(1)
        rozp = b""
        for kandydat in (blok, _a85(blok)):   # Flate albo ASCII85 + Flate (domyślne w reportlab)
            if not kandydat:
                continue
            try:
                rozp = zlib.decompressobj().decompress(kandydat, 8 * 1024 * 1024)
                break
            except zlib.error:
                continue
        if rozp:
            rozp = _bez_obrazow_inline(rozp)
            if _tekstowy(rozp):
                # nazwy wewnątrz strumienia (np. osierocony strumień obiektów `/ObjStm` z `/Author /Marka#20Filipka` albo
                # `/Info`) – jak poza strumieniami: słownictwo PDF wycięte, reszta zdekodowana; widok UTF-16BE (stringi
                # binarne) oraz stringi literalne i szesnastkowe – z bajtów nietkniętych
                widoki = _widoki_strumienia(_NAZWA_PDF.sub(_nazwa_pdf_na_tekst, rozp))[:3] + _widoki_strumienia(rozp)[3:]
                wynik += widoki + _sklejone_ciagi(rozp) + _stringi_pdf_z_bajtow(rozp)
    return wynik


_CIAG_PDF = re.compile(rb"\((?:\\.|[^\\()])*\)|<([0-9A-Fa-f\s]+)>|\[|\]|T[Jj]|ET")


def _sklejone_ciagi(strumien: bytes) -> list[str]:
    """Teksty z operatorów `Tj`/`TJ`: ciągi literalne `(...)` sklejone w obrębie jednego operatora (cp1250/latin-1, bez
    przeplotu UTF-16 – `_bez_przeplotu_utf16`)."""
    wynik: list[str] = []
    biezace: list[bytes] = []
    for m in _CIAG_PDF.finditer(strumien[:8 * 1024 * 1024]):
        t = m.group(0)
        if t.startswith(b"("):
            biezace.append(re.sub(rb"\\(.)", rb"\1", t[1:-1]))
        elif t in (b"Tj", b"TJ", b"ET"):
            if biezace:
                wynik.append(_bez_przeplotu_utf16(b"".join(biezace)).decode("cp1250", errors="replace"))
                biezace = []
    return wynik


def _eml(dane: bytes, pref: str, w: Wydobycie, scisle: bool, gl: int) -> None:
    try:
        msg = email.message_from_bytes(dane, policy=email.policy.default)
    except Exception as e:  # noqa: BLE001
        raise BladOdczytu(f"{pref}EML nie parsuje się: {type(e).__name__}") from e
    naglowki = []
    for nazwa, wartosc in msg.raw_items():
        surowa = str(wartosc)
        try:
            dekodowana = str(email.header.make_header(email.header.decode_header(surowa)))
        except Exception:  # noqa: BLE001
            dekodowana = surowa
        naglowki.append(f"{nazwa}: {dekodowana}")
    if scisle and not any(n.split(":", 1)[0].lower() in ("from", "to", "subject", "date", "message-id", "mime-version")
                           for n in naglowki):
        raise BladOdczytu("EML bez nagłówków")
    surowe_naglowki = dane.split(b"\r\n\r\n", 1)[0].split(b"\n\n", 1)[0].decode("latin-1")
    w.czesci.append(Czesc(f"{pref}eml:naglowki", linie=naglowki,
                          dodatkowe=[surowe_naglowki, *(l for n in naglowki for l in [n.split(": ", 1)[-1]])]))
    czesci = 0
    uzyto: dict[str, int] = {}   # ile razy użyto nazwy załącznika w tym wywołaniu (kolejne: `zal(nazwa#2):`)
    naglowki_czesci: list[str] = []
    for i, czesc in enumerate(msg.walk(), 1):
        if czesc is not msg:   # nagłówki części i zagnieżdżonych wiadomości (message/rfc822), preambuła, epilog
            for k, v in czesc.raw_items():
                try:
                    naglowki_czesci.append(f"{k}: {email.header.make_header(email.header.decode_header(str(v)))}")
                except Exception:  # noqa: BLE001
                    naglowki_czesci.append(f"{k}: {v}")
        for obca in (getattr(czesc, "preamble", None), getattr(czesc, "epilogue", None)):
            if obca and str(obca).strip():
                naglowki_czesci.append(str(obca))
        if czesc.is_multipart():
            continue
        czesci += 1
        typ = czesc.get_content_type()
        nazwa_pliku = czesc.get_filename()
        bajty = czesc.get_payload(decode=True) or b""
        if nazwa_pliku:
            w.czesci.append(Czesc(f"{pref}eml:nazwy zalacznikow", linie=[nazwa_pliku], tresc=False))
        if typ.startswith("text/") and not nazwa_pliku:
            kodowanie = czesc.get_content_charset() or "utf-8"
            try:
                tekst = bajty.decode(kodowanie, errors="replace")
            except LookupError:
                tekst = bajty.decode("utf-8", errors="replace")
            if typ == "text/html":
                bez, surowy = _tekst_html(tekst)
                w.czesci.append(Czesc(f"{pref}eml:czesc {i} {typ}", linie=[l for l in bez.splitlines() if l.strip()],
                                      dodatkowe=[surowy], tresc=True, wariant=True))
            else:
                w.czesci.append(Czesc(f"{pref}eml:czesc {i} {typ}", linie=[l for l in tekst.splitlines() if l.strip()],
                                      tresc=True))
        elif typ.startswith("image/"):
            _dodaj_obraz(w, f"{pref}eml:czesc {i}/{nazwa_pliku or typ}", bajty)
        elif gl < MAKS_GLEBOKOSC:
            # unikalny przedrostek części (powtórzona albo brakująca nazwa, zewnętrzny i zagnieżdżony message/rfc822 –
            # walk() je spłaszcza): inaczej _widoki scala dwa PDF-y pod jednym przedrostkiem i zaniża krotność
            nazwa_zal = nazwa_pliku or typ
            uzyto[nazwa_zal] = uzyto.get(nazwa_zal, 0) + 1
            if uzyto[nazwa_zal] > 1:
                nazwa_zal = f"{nazwa_zal}#{uzyto[nazwa_zal]}"
            _bajty(bajty, nazwa_pliku or typ, f"{pref}zal({nazwa_zal}):", w, gl + 1)
    w.czesci.append(Czesc(f"{pref}eml:naglowki czesci", wezly=naglowki_czesci))
    if not pref:
        w.struktura["czesci_mime"] = czesci


_SUBSTG = re.compile(r"^__substg1\.0_([0-9A-Fa-f]{4})([0-9A-Fa-f]{4})$")


def _msg(dane: bytes, pref: str, w: Wydobycie, scisle: bool, gl: int) -> None:
    try:
        ole = olefile.OleFileIO(io.BytesIO(dane))
    except Exception as e:  # noqa: BLE001
        raise BladOdczytu(f"{pref}MSG nie otwiera się: {type(e).__name__}") from e
    with ole:
        if not ole.exists("__properties_version1.0"):
            raise BladOdczytu("MSG bez __properties_version1.0")
        czesci_msg = 0
        for sciezka in ole.listdir(streams=True, storages=False):
            nazwa = sciezka[-1]
            katalog = "/".join(sciezka[:-1])
            etykieta = f"{pref}msg:{katalog + '/' if katalog else ''}{nazwa}"
            surowe = ole.openstream(sciezka).read()
            m = _SUBSTG.match(nazwa)
            if not m:
                if nazwa != "__properties_version1.0":
                    w.czesci.append(Czesc(etykieta, dodatkowe=_surowe_widoki(surowe)))
                continue
            tag, typ = m.group(1).upper(), m.group(2).upper()
            kod = f"{pref}msg:{katalog + '/' if katalog else ''}{tag}"
            if typ == "001F":
                tekst = surowe.decode("utf-16-le", errors="replace")
                w.czesci.append(Czesc(kod, linie=[l for l in tekst.splitlines() if l.strip()], tresc=tag == "1000",
                                      dodatkowe=[*_surowe_widoki(surowe)]))
            elif typ == "001E":
                w.czesci.append(Czesc(kod, linie=[l for l in surowe.decode("cp1252", errors="replace").splitlines()
                                                  if l.strip()], tresc=tag == "1000",
                                      dodatkowe=[surowe.decode("cp1250", errors="replace")]))
            elif typ == "0102" and tag == "3701" and gl < MAKS_GLEBOKOSC:
                czesci_msg += 1
                _bajty(surowe, f"zalacznik{czesci_msg}", f"{pref}msg:{katalog}/zal:", w, gl + 1)
            elif typ == "0102" and tag == "1013":
                bez, surowy = _tekst_html(surowe.decode("utf-8", errors="replace"))
                w.czesci.append(Czesc(kod, linie=[l for l in bez.splitlines() if l.strip()], dodatkowe=[surowy],
                                      tresc=True, wariant=True))
            else:
                w.czesci.append(Czesc(kod, dodatkowe=_surowe_widoki(surowe)))
        if not pref:
            tresc = sum(1 for c in w.czesci if c.nazwa.endswith(("msg:1000", "msg:1013")))
            w.struktura["czesci_mime"] = tresc + czesci_msg


#: Strumienie właściwości OLE (`\x05SummaryInformation`, `\x05DocumentSummaryInformation`) – metadane dokumentu DOC; pozostałe
#: strumienie to dane binarne (`Czesc.binarna`, J3).
_WLASCIWOSCI_OLE = frozenset({"\x05SummaryInformation", "\x05DocumentSummaryInformation"})


def _doc(dane: bytes, pref: str, w: Wydobycie, scisle: bool, gl: int) -> None:
    try:
        ole = olefile.OleFileIO(io.BytesIO(dane))
    except Exception as e:  # noqa: BLE001
        raise BladOdczytu(f"{pref}DOC nie otwiera się: {type(e).__name__}") from e
    with ole:
        for sciezka in ole.listdir(streams=True, storages=False):
            surowe = ole.openstream(sciezka).read()
            w.czesci.append(Czesc(f"{pref}doc:ole/{'/'.join(sciezka).strip(chr(1)).strip(chr(5))}",
                                  dodatkowe=_surowe_widoki(surowe), binarna=sciezka[-1] not in _WLASCIWOSCI_OLE))
    if gl > 0 and not scisle:
        return  # DOC osadzony: tylko strumienie (konwersja LibreOffice tylko dla pliku najwyższego poziomu)
    from ..render.doc import konwertuj
    with tempfile.TemporaryDirectory(prefix="pbench-sedzia-doc-") as tmp:
        we, wy = Path(tmp) / "plik.doc", Path(tmp) / "plik.docx"
        we.write_bytes(dane)
        try:
            konwertuj(we, wy, "docx")
            zdocx = wy.read_bytes()
        except Exception as e:  # noqa: BLE001
            raise BladOdczytu(f"{pref}DOC: konwersja LibreOffice nie powiodła się") from e
    sub = Wydobycie()
    _zip(zdocx, f"{pref}doc->docx:", sub, "docx", False, gl)
    w.czesci += sub.czesci
    w.obrazy += sub.obrazy
    w.pdfy += sub.pdfy
    if not pref:
        w.struktura.update(_struktura_docx(zdocx))


_SZESNASTKOWE_RTF = re.compile(rb"[0-9a-fA-F\r\n]{64,}")
#: Biała lista słów sterujących i grup docelowych RTF (słownictwo specyfikacji „Rich Text Format (RTF) Specification”, wersja 1.9.1,
#: Microsoft, 2008). Widok `rtf:surowe` zastępuje je spacją wraz z parametrem liczbowym – nazwa słowa sterującego (np. `\info`)
#: nie jest tekstem dokumentu i nie może „trafiać” tokenu wartości (adres `info.…@`). Słowo spoza listy (np. `\Kowalski`) zostaje
#: w widoku jako tekst – lista musi być zamknięta, inaczej uczestnik ukryłby wartość pod wymyślonym słowem sterującym.
_SLOWA_RTF = frozenset("""
rtf ansi mac pc pca ansicpg deff deflang deflangfe adeff adeflang stshfdbch stshfloch stshfhich stshfbi
fonttbl f fnil froman fswiss fmodern fscript fdecor ftech fbidi fcharset fprq falt panose fname fttruetype
colortbl red green blue cf cb cbpat highlight ctint cshade
stylesheet s cs ds ts sbasedon snext slink sqformat spriority styrsid additive ssemihidden sautoupd
info title subject author manager company operator category keywords comment doccomm hlinkbase version vern edmins
nofpages nofwords nofchars nofcharsws id creatim revtim printim buptim yr mo dy hr min sec
generator xmlns userprops propname proptype staticval
pard plain par line page sect sectd row cell nestcell nestrow lastrow trowd tab emdash endash emspace enspace
bullet lquote rquote ldblquote rdblquote ql qr qc qj qd qt sl slmult sb sa li ri fi lin rin
b i ul ulnone uld uldb ulw ulth ulc ulwave strike striked1 scaps caps v fs expnd expndtw kerning charscalex
super sub nosupersub up dn outl shad embo impr lang langfe langnp langfenp noproof cgrid
field fldinst fldrslt fldlock fldedit flddirty fldpriv datafield formfield ffdeftext ffl ffname ffhelptext ffstattext
ffentrymcr ffexitmcr ffownhelp ffownstat
shp shpinst shprslt shptxt shpgrp shpleft shptop shpright shpbottom shplid shpz shpfhdr shpbxcolumn shpbxmargin shpbxpage
shpbyline shpbymargin shpbypage shpwr shpwrk shpfblwtxt shplockanchor shpbasename
sp sn sv do dobxcolumn dobxmargin dobxpage dobymargin dobypage dobypara dodhgt dolock dpx dpy dpxsize dpysize dptxbx
dptxbxtext dpline dprect dpellipse dpcallout dpgroup dpcount dptxbxmar dpshadow dpshadx dpshady
pict emfblip pngblip jpegblip wmetafile macpict pmmetafile dibitmap wbitmap wbmbitspixel wbmplanes wbmwidthbytes
picw pich picwgoal pichgoal picscalex picscaley picscaled piccropl piccropr piccropt piccropb bliptag blipuid picprop
nonshppict defshp
bin objdata object objemb objlink objautlink objsub objpub objicemb objhtml objocx objclass objname objsetsize objalign
objtransy objw objh objscalex objscaley objcropl objcropr objcropt objcropb result rsltrtf rsltpict rsltbmp rslttxt rsltmerge
u uc ud upr ltrch rtlch loch hich dbch ltrdoc rtldoc ltrpar rtlpar ltrsect rtlsect ltrmark rtlmark zwj zwnj
atnauthor atnid atnref atndate atntime atnicn atnparent atrfstart atrfend annotation atnbookmark
header headerl headerr headerf footer footerl footerr footerf footnote ftnsep ftnsepc ftncn aftnsep aftnsepc aftncn
ftnbj ftnstart ftnrstpg ftnrestart ftnrstcont ftnnar ftnnalc ftnnauc ftnnrlc ftnnruc aenddoc aendnotes enddoc endnotes
bkmkstart bkmkend bkmkcolf bkmkcoll xe tc tcf tcl txe rxe bxe
listtable list listid listtemplateid listsimple listhybrid listname listlevel levelstartat levelnfc levelnfcn leveljc
leveljcn levelfollow levelindent levelspace levelnorestart levelnumbers leveltext levelpicture listoverridetable
listoverride listoverridecount ls ilvl listtext pntext pntxta pntxtb pn pnlvl pnlvlblt pnlvlbody pnlvlcont pnf pnfs
pnindent pnstart pnhang pndec pnucltr pnlcltr pnucrm pnlcrm pnord pnordt pncard pnqc pnql pnqr pnb pni pnul pncf
pgdsctbl pgdsc pgdscno pgdscnxt rsidtbl rsid insrsid delrsid charrsid pararsid tblrsid sectrsid latentstyles
lsdlockeddef lsdsemihiddendef lsdunhideuseddef lsdqformatdef lsdprioritydef lsdlockedexcept themedata
colorschememapping datastore nouicompat
paperw paperh margl margr margt margb gutter landscape psz pgwsxn pghsxn marglsxn margrsxn margtsxn margbsxn guttersxn
headery footery cols colsx colno colw colsr linex lndscpsxn sbknone sbkcol sbkpage sbkeven sbkodd pgnx pgny pgnstarts
pgnrestart pgncont pgndec pgnucrm pgnlcrm pgnucltr pgnlcltr titlepg facingp widowctrl hyphauto viewkind viewscale
viewzk viewbksp margmirror deftab formshade fet nolnhtadjtbl noxlattoyen splytwnine ftnlytwnine htmautsp useltbaln
alntblind lytcalctblwd lyttblrtgr lnbrkrule dntblnsbdb nospaceforul truncatefontheight allowfieldendsel nobrkwrptbl
wrppunct asianbrkrule dgmargin dghspace dgvspace dghorigin dgvorigin dghshow dgvshow dgsnap
keep keepn pagebb nowidctlpar widctlpar noline hyphpar outlinelevel intbl itap cpg lisa lisb
trleft trrh trhdr trkeep trgaph trql trqr trqc trbrdrt trbrdrl trbrdrb trbrdrr trbrdrh trbrdrv trpaddl trpaddr trpaddt
trpaddb trpaddfl trpaddfr trpaddft trpaddfb trautofit clvmgf clvmrg clmgf clmrg cellx clbrdrt clbrdrl clbrdrb clbrdrr
clvertalt clvertalc clvertalb clshdrawnil clshdng clcfpat clcbpat clpadl clpadr clpadt clpadb clpadfl clpadfr clpadft
clpadfb cltxlrtb cltxtbrl cltxbtlr cltxlrtbv cltxtbrlv
brdrt brdrb brdrl brdrr brdrbtw brdrbar box brdrs brdrth brdrsh brdrdb brdrdot brdrdash brdrhair brdrinset brdrnone
brdroutset brdrtriple brdrwavy brdrwavydb brdrdashsm brdrdashd brdrdashdd brdremboss brdrengrave brdrframe brdrw brdrcf brsp
shading cfpat bgbdiag bgcross bgdcross bgdkbdiag bgdkcross bgdkdcross bgdkfdiag bgdkhoriz bgdkvert bgfdiag bghoriz bgvert
tx tqr tqc tqdec tldot tlhyph tlul tlth tleq
fromtext fromhtml htmltag htmlrtf mhtmltag
revised revauth revdttm deleted revauthdel revdttmdel
""".split())
_SLOWO_RTF = re.compile(rb"\\\\|\\([a-zA-Z]{1,32})(-?\d{1,10})? ?")   # `\\` (podwójny ukośnik w tekście) przechodzi bez zmian


def _bez_slow_rtf(dane: bytes) -> bytes:
    """Zastępuje spacją słowa sterujące RTF z białej listy (`_SLOWA_RTF`) wraz z parametrem; inne słowa zostają tekstem."""
    return _SLOWO_RTF.sub(lambda m: b" " if m.group(1) and m.group(1).decode("ascii") in _SLOWA_RTF else m.group(0), dane)


#: Znak RTF: `\\uN` (z ogranicznikiem – spacją) albo ciąg `\\'xx`.
_ZNAKI_RTF = re.compile(rb"\\u(-?\d{1,6}) ?|(?:\\'[0-9a-fA-F]{2})+")
_ANSICPG_RTF = re.compile(rb"\\ansicpg(\d{3,5})")


def _znaki_rtf(dane: bytes) -> bytes:
    """(widok `rtf:surowe`) Bajty RTF w całości jako UTF-8. Znaki zapisane `\\uN` i `\\'xx` (strona kodowa dokumentu `\\ansicpgN`,
    domyślnie cp1252) są zdekodowane – znak jest częścią słowa, nie jego granicą („mayor\\u237\\'eda” – „mayoría”, nie słowo
    „mayor” adresu „Calle Mayor”; „Gonz\\'e1lez” – „González”); bajty poza nimi, które nie są poprawnym UTF-8 (tekst 8-bitowy
    wpisany wprost), są czytane stroną kodową dokumentu. Wynik ma jeden widok (`_widok_utf8`): odczyt zdekodowanych znaków
    jeszcze raz jako cp1250 robiłby z nich nowe granice słowa („ñ” = c3 b1 → „ă±”: „mañana” – słowo „ana” wartości „Ana Merino”).
    Znak zastępczy po `\\uN` zostaje: podwojona litera nie tworzy granicy słowa, ale zastępczy „?” albo „™” tworzy („ma\\u241?ana”
    – „mañ”, „ana”); zmierzone 0 fałszywych wycieków u uczestnika idealnego (8 ziaren × 12 RTF), pełne `\\ucN` – odłożone."""
    m = _ANSICPG_RTF.search(dane)
    try:
        strona = codecs.lookup(f"cp{int(m.group(1))}").name if m else "cp1252"
    except LookupError:
        strona = "cp1252"

    def znak(z: re.Match) -> bytes:
        if z.group(1) is not None:
            return chr(int(z.group(1)) % 65536).encode("utf-8", errors="replace")
        return bytes.fromhex(z.group(0).replace(b"\\'", b"").decode("ascii")).decode(strona, errors="replace").encode("utf-8")

    def poza(b: bytes) -> bytes:
        try:
            b.decode("utf-8")
            return b
        except UnicodeDecodeError:
            return b.decode(strona, errors="replace").encode("utf-8")
    czesci, poz = [], 0
    for z in _ZNAKI_RTF.finditer(dane):
        czesci += [poza(dane[poz:z.start()]), znak(z)]
        poz = z.end()
    return b"".join([*czesci, poza(dane[poz:])])


#: Części RTF z treścią dokumentu (reszta – metadane, pola, grupy nieznane – też jest przeszukiwana, ale nie liczy się do treści).
_TRESC_RTF = frozenset({"tresc", "naglowek", "stopka", "przypis", "komentarz"})


def _rtf(dane: bytes, pref: str, w: Wydobycie, scisle: bool, gl: int) -> None:
    o = _rtf_czytnik.czytaj(dane[:MAKS_CZESC])
    for klucz, kawalki in o.teksty.items():
        linie = [l for l in "".join(kawalki).splitlines() if l.strip()]
        if linie:
            w.czesci.append(Czesc(f"{pref}rtf:{klucz}", linie=linie, tresc=klucz in _TRESC_RTF,
                                  dodatkowe=[*widok_bez_przeniesien(linie), *widok_rtl(linie)]))
    for klucz, kawalki in o.strukturalne.items():
        w.czesci.append(Czesc(f"{pref}rtf:{klucz}", linie=[l for l in "".join(kawalki).splitlines() if l.strip()],
                              strukturalna=True))
    for i, b in enumerate(o.obrazy, 1):
        if _rodzaj(b) == "obraz":
            _dodaj_obraz(w, f"{pref}rtf:obraz {i}", b)
        else:                           # metaplik (WMF/EMF) – tekst rekordów w surowych bajtach
            w.czesci.append(Czesc(f"{pref}rtf:obraz {i}", dodatkowe=_surowe_widoki(b)))
    for i, b in enumerate(o.obiekty, 1):
        ole = b.find(_OLE)              # obiekt OLE1: nagłówek, potem kontener CFB
        if ole >= 0 and gl < MAKS_GLEBOKOSC:
            _bajty(b[ole:], f"obiekt{i}", f"{pref}rtf:obiekt {i}/", w, gl + 1)
        else:
            w.czesci.append(Czesc(f"{pref}rtf:obiekt {i}", dodatkowe=_surowe_widoki(b)))
    # surowe bajty bez danych szesnastkowych obrazów (ciąg cyfr w nich „trafiałby” identyfikatory)
    w.czesci.append(Czesc(f"{pref}rtf:surowe",
                          dodatkowe=_widok_utf8(_bez_slow_rtf(_znaki_rtf(_SZESNASTKOWE_RTF.sub(b" ", dane))))))
    if not pref:
        w.struktura.update(o.struktura)


_WIERSZ_VCARD = re.compile(r"^([^:]*):(.*)$")


def _tekst_vcard(dane: bytes) -> str:
    """Bajty vCard jako tekst: UTF-8 (z BOM-em albo bez) albo UTF-16 (z BOM-em; bez BOM-u – po bajtach zerowych przy znakach ASCII)."""
    if dane[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return dane.decode("utf-16", errors="replace")
    if len(dane) > 1 and dane[1:2] == b"\x00" and dane[:1] != b"\x00":
        return dane[:len(dane) // 2 * 2].decode("utf-16-le", errors="replace")
    if dane[:1] == b"\x00" and len(dane) > 1 and dane[1:2] != b"\x00":
        return dane[:len(dane) // 2 * 2].decode("utf-16-be", errors="replace")
    return dane.decode("utf-8-sig", errors="replace")
_UCIECZKA_VCARD = re.compile(r"\\(.)")


def _wartosc_vcard(wartosc: str) -> str:
    """Wartość właściwości vCard: składowe (rozdzielone `;` bez ucieczki) oddzielone spacją, znaki ucieczki zdjęte."""
    skladowe = re.split(r"(?<!\\);", wartosc)
    return " ".join(s for s in (_UCIECZKA_VCARD.sub(lambda m: "\n" if m.group(1) in "nN" else m.group(1), x).strip()
                               for x in skladowe) if s)


def _vcard(dane: bytes, pref: str, w: Wydobycie) -> None:
    tekst = _tekst_vcard(dane[:MAKS_CZESC])
    tekst = re.sub(r"=\r?\n", "", tekst) if "QUOTED-PRINTABLE" in tekst.upper() else tekst   # miękkie łamania QP (vCard 2.1)
    tekst = re.sub(r"\r?\n[ \t]", "", tekst)                                                # rozwinięcie wierszy (RFC 6350 3.2)
    linie: list[str] = []
    for wiersz in tekst.splitlines():
        m = _WIERSZ_VCARD.match(wiersz)
        if m is None or not m.group(2).strip():
            continue
        nazwa, wartosc = m.group(1).upper(), m.group(2)
        if "QUOTED-PRINTABLE" in nazwa:
            kod = re.search(r"CHARSET=([\w-]+)", nazwa)
            wartosc = quopri.decodestring(wartosc.encode("latin-1", errors="replace")).decode(
                kod.group(1) if kod else "utf-8", errors="replace")
        if nazwa.startswith("PHOTO") and ("ENCODING=B" in nazwa or "BASE64" in nazwa or "base64," in wartosc):
            try:
                _dodaj_obraz(w, f"{pref}vcard:PHOTO", base64.b64decode(wartosc.split(",")[-1] + "==="))
            except Exception:  # noqa: BLE001
                pass
            continue
        linie.append(_wartosc_vcard(wartosc))
    w.czesci.append(Czesc(f"{pref}vcard", linie=[l for l in linie if l.strip()], tresc=True, dodatkowe=_surowe_widoki(dane)))
    if not pref:
        w.struktura["wizytowki"] = len(re.findall(r"(?im)^BEGIN:VCARD", tekst))


def _bajty(dane: bytes, nazwa: str, pref: str, w: Wydobycie, gl: int, scisle: bool = False,
           rodzaj: str | None = None) -> None:
    """Rozbiera bajty wg sygnatury (rekurencja załączników i osadzonych plików; błędy zagnieżdżonych są pomijane)."""
    rodzaj = rodzaj or _rodzaj(dane, nazwa)
    try:
        if rodzaj in ("docx", "xlsx", "pptx", "odt", "zip"):
            _zip(dane, pref, w, rodzaj, scisle, gl)
        elif rodzaj == "pdf":
            _pdf(dane, pref, w, scisle, gl)
        elif rodzaj == "eml":
            _eml(dane, pref, w, scisle, gl)
        elif rodzaj == "msg":
            _msg(dane, pref, w, scisle, gl)
        elif rodzaj == "doc":
            _doc(dane, pref, w, scisle, gl)
        elif rodzaj == "rtf":
            _rtf(dane, pref, w, scisle, gl)
        elif rodzaj == "vcard":
            _vcard(dane, pref, w)
        elif rodzaj == "obraz":
            _dodaj_obraz(w, f"{pref}{nazwa}", dane)
        elif rodzaj == "txt" and not pref:
            # tylko sam plik wynikowy (`.msg` → `.txt`); zagnieżdżony .txt (ZIP/EML) to załącznik – surowe widoki niżej
            tekst = dane[:MAKS_CZESC].decode("utf-8")
            linie = [l for l in tekst.splitlines() if l.strip()]
            w.czesci.append(Czesc(f"{pref}tekst", linie=linie, tresc=True, dodatkowe=widok_bez_przeniesien(linie)))
        else:
            w.czesci.append(Czesc(f"{pref}{nazwa}", dodatkowe=_surowe_widoki(dane)))
    except BladOdczytu:
        if scisle:
            raise
    except Exception as e:  # noqa: BLE001
        if scisle:
            raise BladOdczytu(f"{type(e).__name__}: {e}") from e


def _wydobadz(sciezka: Path) -> Wydobycie:
    p = Path(sciezka)
    w = Wydobycie()
    if not p.exists() or p.stat().st_size == 0:
        w.status = "PUSTY"
        w.blad = "brak pliku" if not p.exists() else "plik ma 0 bajtów"
        return w
    dane = p.read_bytes()
    rodzaj = _rodzaj(dane, p.name)
    # R38: format wyniku rozpoznajemy po TREŚCI (sygnatury, części ZIP, nagłówek OLE), nie po rozszerzeniu – narzędzie może
    # zapisać inny format niż oryginał (`.doc` → `.docx`, `.msg` → `.txt`); zmianę formatu widać w `integralnosc.format_zgodny`
    w.rodzaj = rodzaj
    if rodzaj == "txt" and p.suffix.lower() not in (".txt", ".text", ""):
        # zwykły tekst jest wynikiem tylko pod nazwą tekstową; pod nazwą formatu binarnego (.docx, .pdf…) to uszkodzony plik
        w.status, w.blad = "NIECZYTELNY", f"zwykły tekst pod rozszerzeniem formatu binarnego ({p.suffix})"
        return w
    if rodzaj in ("zip_uszkodzony", "ole_uszkodzony", "inne", "ole", "zip"):
        w.status, w.blad = "NIECZYTELNY", f"nierozpoznany format ({rodzaj})"
        return w
    try:
        _bajty(dane, p.name, "", w, 0, scisle=True, rodzaj=rodzaj)
    except BladOdczytu as e:
        w.status, w.blad = "NIECZYTELNY", str(e)
        return w
    if not w.ma_tresc():
        w.status, w.blad = "PUSTY", "plik otwiera się, ale nie ma tekstu ani obrazów"
    return w


#: Rozdzielczość renderowania stron PDF do OCR (strona A4 ≈ 2480 x 3508 px): sędzia czyta tak KAŻDĄ stronę oryginału i wyniku PDF.
RENDER_DPI = 300
#: Drugi odczyt stron (A4 ≈ 3307 x 4677 px) – tylko dla wartości, których odczyt `RENDER_DPI` nie znalazł (zob. `plik.ocen_plik`):
#: drobny druk i strony-rastry o niskiej rozdzielczości źródłowej.
DRUGI_ODCZYT_DPI = 400
#: Bok jednego obrazu renderu strony nie przekracza tylu pikseli (strona o absurdalnym `/MediaBox` nie może wyczerpać pamięci):
#: większa strona jest renderowana w pełnym dpi kafelkami (`renderuj_strony`), więc powiększenie `/MediaBox` nie zmniejsza
#: rozdzielczości treści.
MAKS_BOK_RENDERU_PX = 12000
#: Zakładka sąsiednich kafelków (piksele w docelowym dpi) – wiersz tekstu na styku kafelków jest cały w jednym z nich.
ZAKLADKA_KAFELKOW_PX = 300
#: Podgląd dużej strony (szukanie obszaru z treścią) – dłuższy bok w pikselach; jaśniejsze piksele to tło.
BOK_PODGLADU_PX = 3000
PROG_TLA = 250
#: Nazwa obrazu strony wyrenderowanej do OCR: `pdf:render strona N` (`RENDER_DPI`), `pdf:render strona N (400 dpi)` (inne dpi).
PREFIKS_RENDERU = "pdf:render strona"


def nazwa_renderu(strona: int, dpi: int = RENDER_DPI) -> str:
    """Nazwa obrazu strony `strona` (od 1) wyrenderowanej w `dpi` (zob. `PREFIKS_RENDERU`)."""
    return f"{PREFIKS_RENDERU} {strona}" + ("" if dpi == RENDER_DPI else f" ({dpi} dpi)")


def ma_duze_strony(sciezka: Path, dpi: int = RENDER_DPI) -> bool:
    """Czy któraś strona PDF w `dpi` ma bok większy niż `MAKS_BOK_RENDERU_PX` (render kafelkami; klucz pamięci podręcznej OCR)."""
    import pypdfium2 as pdfium
    try:
        doc = pdfium.PdfDocument(Path(sciezka).read_bytes())
    except Exception:  # noqa: BLE001
        return False
    try:
        return any(max(doc[i].get_size()) * dpi / 72 > MAKS_BOK_RENDERU_PX for i in range(len(doc)))
    finally:
        doc.close()


def _png(im: Image.Image) -> bytes:
    bufor = io.BytesIO()
    im.convert("RGB").save(bufor, format="PNG", compress_level=1)
    return bufor.getvalue()


def _kafelki(strona, dpi: int) -> list[bytes]:
    """Duża strona w pełnym `dpi`: podgląd wskazuje obszar z treścią (piksele ciemniejsze niż `PROG_TLA`), który jest renderowany
    kafelkami o boku ≤ `MAKS_BOK_RENDERU_PX` z zakładką `ZAKLADKA_KAFELKOW_PX`; kafelki bez treści są pomijane."""
    szer, wys = strona.get_size()
    s_podg = BOK_PODGLADU_PX / max(szer, wys)
    podglad = strona.render(scale=s_podg).to_pil().convert("L")
    ramka = podglad.point(lambda v: 255 if v < PROG_TLA else 0).getbbox()
    if ramka is None:
        return [_png(podglad)]
    margines = 2 / s_podg                                    # punkty: piksel podglądu zaokrąglony w obie strony
    x0, y0 = max(0.0, ramka[0] / s_podg - margines), max(0.0, ramka[1] / s_podg - margines)   # od góry strony
    x1, y1 = min(szer, ramka[2] / s_podg + margines), min(wys, ramka[3] / s_podg + margines)
    skala = dpi / 72
    bok, zakladka = MAKS_BOK_RENDERU_PX / skala, ZAKLADKA_KAFELKOW_PX / skala
    krok = bok - zakladka
    kafelki = []
    y = y0
    while y < y1:
        x = x0
        while x < x1:
            prawa, dol = min(x + bok, x1), min(y + bok, y1)
            # `crop` PDFium: (lewo, dół, prawo, góra) – ile punktów odciąć z każdej strony
            im = strona.render(scale=skala, crop=(x, wys - dol, szer - prawa, y)).to_pil()
            if im.convert("L").point(lambda v: 255 if v < PROG_TLA else 0).getbbox() is not None:
                kafelki.append(_png(im))
            if prawa >= x1:
                break
            x += krok
        if dol >= y1:
            break
        y += krok
    return kafelki or [_png(podglad)]


def renderuj_strony(sciezka: Path, dpi: int = RENDER_DPI, bez_tekstu: bool = False) -> list[list[bytes]]:
    """Każda strona PDF wyrenderowana (PDFium – to, co widzi czytelnik: tekst w każdym kodowaniu, obrazy osadzone i inline,
    ścieżki, przykrycia) jako PNG do OCR: lista obrazów na stronę – jeden, a dla strony większej niż `MAKS_BOK_RENDERU_PX`
    kafelki obszaru z treścią w pełnym dpi (`_kafelki`); pusta lista, gdy PDFium pliku nie otwiera. Strony obrócone (`/Rotate`)
    są renderowane w obróconej postaci; kąt prostuje OCR (OSD). `bez_tekstu` – render bez obiektów tekstowych (`_bez_tekstu`):
    zostają piksele spoza warstwy tekstowej (obrazy osadzone i inline, ścieżki)."""
    import pypdfium2 as pdfium
    try:
        doc = pdfium.PdfDocument(Path(sciezka).read_bytes())
    except Exception:  # noqa: BLE001 - PDFium nie otwiera pliku: nie ma czego zobaczyć
        return []
    strony: list[list[bytes]] = []
    try:
        for i in range(len(doc)):
            strona = doc[i]
            if bez_tekstu:
                _bez_tekstu(strona)
            if max(strona.get_size()) * dpi / 72 > MAKS_BOK_RENDERU_PX:
                strony.append(_kafelki(strona, dpi))
            else:
                strony.append([_png(strona.render(scale=dpi / 72).to_pil())])
    finally:
        doc.close()
    return strony


def _bez_tekstu(strona) -> None:
    """Obiekty tekstowe strony PDFium (także w XObject-ach formularzy) dostają tryb renderowania „niewidoczny” – render pokazuje
    wtedy tylko piksele spoza warstwy tekstowej (zmiana w pamięci, plik bez zmian)."""
    import pypdfium2.raw as pdfium_c
    for obiekt in strona.get_objects(filter=[pdfium_c.FPDF_PAGEOBJ_TEXT]):
        pdfium_c.FPDFTextObj_SetTextRenderMode(obiekt, pdfium_c.FPDF_TEXTRENDERMODE_INVISIBLE)


_CACHE: OrderedDict[tuple, Wydobycie] = OrderedDict()


def wydobadz(sciezka: Path) -> Wydobycie:
    """`_wydobadz` z krótką pamięcią podręczną (oryginał jest oceniany dla każdego uczestnika)."""
    p = Path(sciezka)
    try:
        st = p.stat()
        klucz = (str(p.resolve()), st.st_size, st.st_mtime_ns)
    except OSError:
        return _wydobadz(p)
    if klucz in _CACHE:
        _CACHE.move_to_end(klucz)
        return _CACHE[klucz]
    wynik = _wydobadz(p)
    _CACHE[klucz] = wynik
    while len(_CACHE) > 24:
        _CACHE.popitem(last=False)
    return wynik
