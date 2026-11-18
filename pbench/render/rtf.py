"""Renderer RTF (Rich Text Format): DOCX z `renderuj_docx` przekonwertowany LibreOffice'em (`soffice --headless
--convert-to rtf`) – ten sam wzorzec co DOC (`pbench.render.doc`). Warstwa trudnych przypadków (H4b, `formaty_rtf_odt`);
trzon korpusu nie ma tego formatu. Utrudnienia i wejście jak w DOCX (`UTRUDNIENIA_RTF` = `UTRUDNIENIA_DOCX`).

Gdzie co leży (grupy RTF): treść i tabele (`\\trowd … \\cell … \\row`) – ciało dokumentu; nagłówek i stopka – grupy `\\header…`,
`\\footer…`; przypisy – `\\footnote`; komentarze – `\\annotation` z autorem w `\\atnauthor` (i inicjałami `\\atnid`); zmiany
śledzone – autorzy w `\\revtbl`, tekst usunięty z `\\deleted`; metadane – `\\info` (`\\title`, `\\subject`, `\\author`…) i
`\\userprops`; obrazy – `\\pict` (PNG zapisany szesnastkowo). Tekst spoza ASCII LibreOffice zapisuje jako `\\uN` z zamiennikiem
`\\'xx` w stronie kodowej `\\ansicpg`, więc surowe bajty pliku nie zawierają polskich liter.

Gold = wartości DOCX po sprawdzeniu pliku RTF tak jak w DOC: RTF jest odczytywany z powrotem (LibreOffice RTF -> DOCX), każda
wartość musi występować w tekście swojego miejsca (`doc.teksty_miejsc_docx`, granice słów), obraz – jako bajty PNG wśród danych
szesnastkowych pliku. Czego konwersja nie zachowała, usuwamy z gold z ostrzeżeniem (`WynikDoc.ostrzezenia`).

Determinizm (zbadane, LibreOffice 24.2): kolejne konwersje tego samego DOCX różnią się wyłącznie numeracją wpisów tablicy
czcionek `\\fonttbl` i tablicy kolorów `\\colortbl` (kolejność wpisów i numery w odwołaniach `\\fN`, `\\afN`, `\\cfN`, `\\cbN`…).
`normalizuj_rtf` układa obie tablice w stałym porządku – kolory: wpis 0 („auto”) zostaje, pozostałe posortowane i bez powtórzeń;
czcionki: wpisy posortowane po opisie (bez numeru) i ponumerowane od 0 – i przenumerowuje odwołania (`SLOWA_KOLOROW`,
`SLOWA_CZCIONEK`) w całym pliku (tylko słowa kontrolne – „\\f1” poprzedzone parzystą liczbą ukośników to tekst, np. ścieżka).

Pola zapisane 8-bitowo: LibreOffice (24.2) zapisuje autora komentarza (`\\atnauthor`, także inicjały `\\atnid`) bajtami strony
kodowej dokumentu, a znak spoza niej – jako „?” („Michał Kozłowski” → „Micha? Koz?owski”), więc odczyt zwrotny gubił taką wartość
(inne pola – tekst, `\\info`, autorzy zmian w `\\revtbl` – zapisuje jako `\\uN`). `zapisz_pola_unicode` przepisuje tekst takiego pola na ucieczki `\\uN\\'3f` (znak zastępczy „?”), gdy
dokładnie jedna wartość dokumentu daje w stronie kodowej te same bajty (podmiana jest funkcją wartości – bajty pozostają
deterministyczne); LibreOffice i Word czytają `\\uN` w tych grupach. Podmiana jest przed odczytem zwrotnym, więc gold nadal
sprawdza odczyt LibreOffice'a.
"""
from __future__ import annotations

import binascii
import re
import struct
import tempfile
from pathlib import Path

from ..model import Dokument, Wartosc
from ..utrudnienia import UTRUDNIENIA_DOCX, UTRUDNIENIA_POMINIETE
from .doc import WynikDoc, konwertuj, odfiltruj_zachowane, teksty_miejsc_docx
from .docx import renderuj_docx

UTRUDNIENIA_RTF: frozenset[str] = UTRUDNIENIA_DOCX
#: Słowa kontrolne RTF, których parametr to numer wpisu tablicy kolorów.
SLOWA_KOLOROW: tuple[str, ...] = ("cf", "cb", "highlight", "chcbpat", "chcfpat", "cbpat", "cfpat", "clcbpat", "clcfpat",
                                  "clcbpatraw", "clcfpatraw", "brdrcf", "trcbpat", "trcfpat", "ulc", "tscellcbpat",
                                  "tscellcfpat")
#: Słowa kontrolne RTF, których parametr to numer czcionki w `\\fonttbl`.
SLOWA_CZCIONEK: tuple[str, ...] = ("f", "af", "deff", "adeff", "stshfdbch", "stshfloch", "stshfhich", "stshfbi")
_KOLORY = re.compile(rb"\{\\colortbl([^{}]*)\}")
_POCZATEK_CZCIONEK = re.compile(rb"\{\\fonttbl")
_NUMER_CZCIONKI = re.compile(rb"^\{\\f(\d+)(?![0-9a-zA-Z])")


def _odwolania(slowa: tuple[str, ...]) -> re.Pattern:
    """Słowo kontrolne z numerem: nieparzysta liczba ukośników przed nazwą (parzysta – dosłowne ukośniki tekstu, „C:\\\\f1”)."""
    return re.compile(rb"(?<!\\)((?:\\\\)*)\\(" + b"|".join(s.encode() for s in sorted(slowa, key=len, reverse=True))
                      + rb")(\d+)(?![0-9a-zA-Z])")


_ODWOLANIE_KOLORU = _odwolania(SLOWA_KOLOROW)
_ODWOLANIE_CZCIONKI = _odwolania(SLOWA_CZCIONEK)
_SZESNASTKOWE = re.compile(rb"[0-9a-fA-F\r\n]{256,}")
_ZNACZNIK = b"\x00%d\x00"


def _koniec_grupy(bajty: bytes, start: int) -> int:
    """Indeks za nawiasem zamykającym grupę zaczynającą się `{` na pozycji `start` (z pominięciem `\\{`, `\\}`, `\\\\`)."""
    glebokosc, i = 0, start
    while i < len(bajty):
        c = bajty[i:i + 1]
        if c == b"\\":
            i += 2
            continue
        if c == b"{":
            glebokosc += 1
        elif c == b"}":
            glebokosc -= 1
            if glebokosc == 0:
                return i + 1
        i += 1
    return -1


def _tablica_czcionek(bajty: bytes) -> tuple[int, int, bytes, dict[int, int]] | None:
    """(początek, koniec, nowa tablica, mapa numerów) dla `\\fonttbl`; None, gdy jej nie ma albo ma wpisy bez nawiasów."""
    m = _POCZATEK_CZCIONEK.search(bajty)
    if m is None:
        return None
    koniec = _koniec_grupy(bajty, m.start())
    if koniec < 0:
        return None
    wpisy: list[tuple[int, bytes]] = []
    i = m.end()
    while i < koniec - 1:
        if bajty[i:i + 1] in (b" ", b"\r", b"\n"):
            i += 1
            continue
        if bajty[i:i + 1] != b"{":
            return None
        k = _koniec_grupy(bajty, i)
        grupa = bajty[i:k]
        n = _NUMER_CZCIONKI.match(grupa)
        if n is None:
            return None
        wpisy.append((int(n.group(1)), b"{" + grupa[n.end():]))      # opis wpisu bez numeru
        i = k
    opisy = sorted({o for _, o in wpisy})
    mapa = {nr: opisy.index(o) for nr, o in wpisy}
    tablica = b"{\\fonttbl" + b"".join(b"{\\f%d" % k + o[1:] for k, o in enumerate(opisy)) + b"}"
    return m.start(), koniec, tablica, mapa


def normalizuj_rtf(bajty: bytes) -> bytes:
    """RTF z LibreOffice'a w postaci powtarzalnej: tablice czcionek i kolorów w stałym porządku (zob. docstring modułu)."""
    tablice: list[bytes] = []
    mapa_czcionek: dict[int, int] = {}
    czcionki = _tablica_czcionek(bajty)
    if czcionki is not None:
        start, koniec, tablica, mapa_czcionek = czcionki
        bajty = bajty[:start] + _ZNACZNIK % len(tablice) + bajty[koniec:]
        tablice.append(tablica)
    mapa_kolorow: dict[int, int] = {}
    m = _KOLORY.search(bajty)
    if m is not None:
        wpisy = m.group(1).split(b";")
        if wpisy and not wpisy[-1].strip():
            wpisy = wpisy[:-1]
        # wpis 0 to „auto” (pusty przed pierwszym średnikiem) – zostaje na miejscu; reszta posortowana, bez powtórzeń
        uporzadkowane = sorted(set(wpisy[1:]))
        mapa_kolorow = {i: (0 if i == 0 else uporzadkowane.index(w) + 1) for i, w in enumerate(wpisy)}
        bajty = bajty[:m.start()] + _ZNACZNIK % len(tablice) + bajty[m.end():]
        tablice.append(b"{\\colortbl;" + b"".join(w + b";" for w in uporzadkowane) + b"}")

    def podmien(mapa: dict[int, int]):
        return lambda r: r.group(1) + b"\\" + r.group(2) + str(mapa.get(int(r.group(3)), int(r.group(3)))).encode()
    bajty = _ODWOLANIE_CZCIONKI.sub(podmien(mapa_czcionek), bajty) if mapa_czcionek else bajty
    bajty = _ODWOLANIE_KOLORU.sub(podmien(mapa_kolorow), bajty) if mapa_kolorow else bajty
    for i, t in enumerate(tablice):
        bajty = bajty.replace(_ZNACZNIK % i, t, 1)
    return bajty


_POLE_8BIT = re.compile(rb"(\{\\\*\\(?:atnauthor|atnid) ?)([^{}\\]*)(\})")
_STRONA_KODOWA = re.compile(rb"\\ansicpg(\d+)")


def _ucieczki_unicode(tekst: str) -> bytes:
    """Tekst RTF: ASCII bez zmian, inne znaki jako `\\uN\\'3f` (16 bitów ze znakiem, znak zastępczy „?”)."""
    wynik = []
    for c in tekst:
        if c.isascii():
            wynik.append(c.encode("ascii"))
        else:
            for jednostka in struct.unpack(f"<{len(c.encode('utf-16-le')) // 2}H", c.encode("utf-16-le")):
                wynik.append(b"\\u%d\\'3f" % (jednostka - 65536 if jednostka >= 32768 else jednostka))
    return b"".join(wynik)


def zapisz_pola_unicode(rtf: bytes, wartosci: list[str]) -> bytes:
    """Pola zapisane przez LibreOffice'a 8-bitowo (zob. docstring modułu) przepisane na `\\uN\\'3f`, gdy ich bajty to zapis
    dokładnie jednej z `wartosci` w stronie kodowej dokumentu (`\\ansicpgN`, domyślnie cp1252) z „?” za znaki spoza niej. Pola
    czysto ASCII i pola bez jednoznacznej wartości zostają bez zmian."""
    m = _STRONA_KODOWA.search(rtf[:4096])
    kod = f"cp{int(m.group(1))}" if m else "cp1252"
    try:
        zapisy: dict[bytes, set[str]] = {}
        for w in set(wartosci):
            if not w.isascii():
                zapisy.setdefault(w.encode(kod, errors="replace"), set()).add(w)
    except LookupError:
        return rtf

    def podmien(r: re.Match) -> bytes:
        kandydaci = zapisy.get(r.group(2), set())
        if (r.group(2).isascii() and b"?" not in r.group(2)) or len(kandydaci) != 1:
            return r.group(0)
        # `\\uc1` w grupie: liczba znaków zastępczych nie zależy od `\\ucN` grupy otaczającej
        return r.group(1) + b"\\uc1 " + _ucieczki_unicode(next(iter(kandydaci))) + r.group(3)
    return _POLE_8BIT.sub(podmien, rtf)


def dane_szesnastkowe(rtf: bytes) -> bytes:
    """Długie ciągi szesnastkowe pliku RTF (dane obrazów `\\pict`, obiektów `\\objdata`) zdekodowane i sklejone."""
    wynik = []
    for m in _SZESNASTKOWE.finditer(rtf):
        cyfry = re.sub(rb"\s", b"", m.group(0))
        try:
            wynik.append(binascii.unhexlify(cyfry[:len(cyfry) // 2 * 2]))
        except binascii.Error:
            continue
    return b"\0".join(wynik)


def renderuj_rtf(d: Dokument, plik: Path, utrudnienia: set[str]) -> WynikDoc:
    """Zapisuje `d` jako RTF w `plik`; zwraca wartości i obrazy faktycznie obecne w pliku oraz ostrzeżenia."""
    nieznane = set(utrudnienia) - UTRUDNIENIA_RTF - UTRUDNIENIA_POMINIETE
    if nieznane:
        raise ValueError(f"nieznane utrudnienia RTF: {sorted(nieznane)}")
    plik = Path(plik)
    plik.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pbench-rtf-") as tmp:
        docx = Path(tmp) / "dokument.docx"
        wynik = renderuj_docx(d, docx, set(utrudnienia))
        surowy = Path(tmp) / "dokument.rtf"
        konwertuj(docx, surowy, "rtf")
        plik.write_bytes(zapisz_pola_unicode(normalizuj_rtf(surowy.read_bytes()), [w.tekst for w in wynik.wartosci]))
        zwrot = Path(tmp) / "zwrot" / "dokument.docx"  # odczyt RTF niezależny od zapisu: RTF -> DOCX
        zwrot.parent.mkdir()
        konwertuj(plik, zwrot, "docx")
        teksty = teksty_miejsc_docx(zwrot)
    wartosci, obrazy, ostrzezenia = odfiltruj_zachowane(wynik.wartosci, wynik.obrazy, teksty,
                                                        dane_szesnastkowe(plik.read_bytes()))
    return WynikDoc(wartosci, obrazy, [o.replace("konwersja DOC", "konwersja RTF") for o in ostrzezenia])


def render_rtf(d: Dokument, plik: Path, utrudnienia: set[str]) -> list[Wartosc]:
    """Jak `renderuj_rtf`, ale zwraca tylko listę umieszczonych wartości."""
    return renderuj_rtf(d, plik, utrudnienia).wartosci
