"""Odczyt RTF dla sędziego plikowego – własny parser (bez LibreOffice'a i bez bibliotek zewnętrznych).

RTF to tekst z grupami `{…}` i słowami kontrolnymi; sędzia potrzebuje KAŻDEGO tekstu, który plik niesie, z podziałem na miejsca:
ciało dokumentu (akapity `\\par`, komórki `\\cell`, wynik pól `\\fldrslt`), nagłówki i stopki (`\\header…`, `\\footer…`), przypisy
(`\\footnote`), komentarze (`\\annotation`, autor `\\atnauthor`, inicjały `\\atnid`), metadane (`\\info`: `\\title`, `\\author`…;
`\\userprops`), instrukcje pól (`\\fldinst`), nazwy zakładek (`\\bkmkstart`), autorów zmian (`\\revtbl`) i każdą inną grupę – także
„ignorowalną” `{\\*\\nazwa …}`, której czytnik nie zna (dane bywają ukryte właśnie tam). Tekst ukryty (`\\v`) i usunięty
(`\\deleted`) jest czytany jak każdy inny. Tablice formatu (`\\fonttbl`, `\\colortbl`, `\\stylesheet`, listy, `\\rsidtbl`…) to szablon
formatu – części strukturalne. Kształty to treść, jak w DOCX i ODT (pole tekstowe `w:txbxContent`, `draw:frame`, atrybut `descr`): tekst
pola tekstowego (`\\shptxt`) należy do miejsca, w którym kształt leży (treść, nagłówek…), a wartości właściwości kształtu i obrazu
(`{\\sp{\\sn wzDescription}{\\sv …}}` – tekst alternatywny, `gtextUNICODE` – tekst WordArt) – do części `ksztalt`; strukturalne
zostają tylko nazwy właściwości (`\\sn`). Obrazy `\\pict` (dane szesnastkowe albo `\\binN` – dokładnie N bajtów, potem rozbiór od
następnego bajtu) trafiają do OCR, obiekty `\\objdata` – do rozbioru rekurencyjnego (kontener OLE w środku).

Dekodowanie: `\\'xx` – bajt w stronie kodowej czcionki (`\\fcharsetN` z `\\fonttbl`) albo dokumentu (`\\ansicpgN`; domyślnie
cp1252), kolejne bajty dekodowane razem (strony wielobajtowe); `\\uN` – znak Unicode (16 bitów ze znakiem: ujemne + 65536; para
surogatów – jeden znak; liczba spoza zakresu Unicode i surogat bez pary – znak zastępczy U+FFFD), po nim pomijane `\\ucN` znaków
zastępczych (domyślnie 1); symbole (`\\emdash`, `\\lquote`, `\\~`, `\\_`…) – ich znaki; `\\-` (miękki łącznik) – nic.
"""
from __future__ import annotations

import binascii
import re
from dataclasses import dataclass, field

#: Strona kodowa wg `\\fcharsetN` (Windows).
STRONY_KODOWE: dict[int, str] = {0: "cp1252", 1: "cp1252", 77: "mac_roman", 128: "cp932", 129: "cp949", 134: "cp936",
                                  136: "cp950", 161: "cp1253", 162: "cp1254", 163: "cp1258", 177: "cp1255", 178: "cp1256",
                                  186: "cp1257", 204: "cp1251", 222: "cp874", 238: "cp1250", 255: "cp437"}
#: Grupy, których tekst to szablon formatu (nie dane dokumentu).
STRUKTURALNE: frozenset[str] = frozenset({
    "fonttbl", "colortbl", "stylesheet", "listtable", "listoverridetable", "rsidtbl", "generator", "xmlnstbl", "pgdsctbl",
    "themedata", "colorschememapping", "latentstyles", "datastore", "mmathPr", "defchp", "defpap", "wgrffmtfilter",
    "pnseclvl", "listpicture", "fchars", "lchars", "panose", "falt", "fontemb", "fontfile", "ftnsep", "ftnsepc", "aftnsep",
    "aftnsepc", "ftncn", "aftncn", "pgptbl", "protusertbl", "filetbl", "sn"})
#: Grupy z danymi dokumentu, które dostają osobną część (reszta grup z tekstem – część `rtf:*<nazwa>`).
MIEJSCA: dict[str, str] = {
    "header": "naglowek", "headerl": "naglowek", "headerr": "naglowek", "headerf": "naglowek",
    "footer": "stopka", "footerl": "stopka", "footerr": "stopka", "footerf": "stopka",
    "footnote": "przypis", "annotation": "komentarz", "atnauthor": "komentarz", "atnid": "komentarz",
    "info": "metadane", "userprops": "metadane", "fldinst": "pole", "bkmkstart": "zakladki", "bkmkend": "zakladki",
    "revtbl": "zmiany", "sv": "ksztalt",
}
#: Miejsca z treścią dokumentu: tekst pola tekstowego kształtu (`\\shptxt`) w takim miejscu należy do niego.
_MIEJSCA_TRESCI = frozenset({"naglowek", "stopka", "przypis", "komentarz"})
#: Grupy, w których tekście czytelnik nie widzi treści dokumentu, a mogą nieść dane (wynik `rtf:*<nazwa>`): wszystko, co nie jest
#: strukturalne, ciałem (`fldrslt` i grupy formatowania) ani miejscem z `MIEJSCA`.
#: Pola `\info` i właściwości użytkownika: osobne wartości (rozdzielone końcem wiersza, nie sklejone z sąsiednimi polami).
_POLA = frozenset({"title", "subject", "author", "operator", "keywords", "comment", "doccomm", "company", "manager", "category",
                   "hlinkbase", "propname", "staticval", "linkval"})
_CIALO = frozenset({"fldrslt", "field", "shptxt", "txbxcontent", "nesttableprops", "nonesttables"})
_SYMBOLE: dict[str, str] = {"emdash": "—", "endash": "–", "lquote": "‘", "rquote": "’", "ldblquote": "“", "rdblquote": "”",
                            "bullet": "•", "emspace": " ", "enspace": " ", "qmspace": " ", "tab": "\t", "line": "\n",
                            "par": "\n", "sect": "\n", "page": "\n", "row": "\n", "cell": "\n", "nestcell": "\n",
                            "nestrow": "\n", "lbr": "\n", "zwj": "\u200d", "zwnj": "\u200c", "ltrmark": "\u200e", "rtlmark": "\u200f"}
_TOKEN = re.compile(rb"\\([a-zA-Z]{1,32})(-?\d{1,10})? ?|\\'([0-9a-fA-F]{2})|\\(.)|([{}])|([\r\n]+)|([^\\{}\r\n]+)", re.DOTALL)


@dataclass
class _Grupa:
    cel: str                     # klucz części, do której idzie tekst grupy
    kodowanie: str
    uc: int = 1
    czcionka: int | None = None
    strukturalna: bool = False
    pierwsza: bool = True        # czekamy na pierwsze słowo grupy (nazwa grupy-celu)
    gwiazdka: bool = False       # grupa `{\*…}`
    obraz: bool = False          # grupa `\pict`: jej tekst to dane obrazu
    obiekt: bool = False         # grupa `\objdata`: dane obiektu osadzonego
    oddziel: bool = False        # grupa-wartość (miejsce, pole `\info`…): po jej końcu nowy wiersz w części
    cel_tresci: str = "tresc"    # miejsce treści, w którym leży grupa (dla pola tekstowego kształtu w środku)


@dataclass
class OdczytRtf:
    """Tekst wg części (`tresc`, `naglowek`, `stopka`, `przypis`, `komentarz`, `metadane`, `pole`, `*<grupa>`…), części
    strukturalne, obrazy i obiekty (bajty) oraz liczniki struktury (`akapity` ciała, `wiersze_tabel`)."""

    teksty: dict[str, list[str]] = field(default_factory=dict)
    strukturalne: dict[str, list[str]] = field(default_factory=dict)
    obrazy: list[bytes] = field(default_factory=list)
    obiekty: list[bytes] = field(default_factory=list)
    struktura: dict[str, int] = field(default_factory=lambda: {"akapity": 0, "wiersze_tabel": 0})


def jest_rtf(dane: bytes) -> bool:
    return dane.lstrip()[:5] == b"{\\rtf"


def _zloz_surogaty(tekst: str) -> str:
    """Para surogatów z dwóch kolejnych `\\uN` (znak spoza BMP) – jeden znak; surogat bez pary – znak zastępczy U+FFFD."""
    if not any("\ud800" <= c <= "\udfff" for c in tekst):
        return tekst
    return tekst.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")


def _bajty_szesnastkowe(tekst: str) -> bytes:
    cyfry = re.sub(r"[^0-9a-fA-F]", "", tekst)
    try:
        return binascii.unhexlify(cyfry[:len(cyfry) // 2 * 2])
    except binascii.Error:
        return b""


def czytaj(dane: bytes) -> OdczytRtf:
    """Rozbiór RTF (zob. docstring modułu). Błędy składni (niedomknięte grupy, nadmiarowe `}`) nie przerywają odczytu."""
    wynik = OdczytRtf()
    czcionki: dict[int, str] = {}
    domyslne = "cp1252"
    stos: list[_Grupa] = [_Grupa("tresc", domyslne)]
    bufor = bytearray()            # bajty `\'xx` czekające na dekodowanie
    pomin = 0                      # znaki zastępcze po `\uN`
    surowe_obrazu: list[str] = []  # dane szesnastkowe bieżącej grupy `\pict`/`\objdata`

    def g() -> _Grupa:
        return stos[-1]

    def dopisz(tekst: str) -> None:
        cel = g()
        if cel.obraz or cel.obiekt:
            surowe_obrazu.append(tekst)
            return
        slownik = wynik.strukturalne if cel.strukturalna else wynik.teksty
        slownik.setdefault(cel.cel, []).append(tekst)

    def oproznij() -> None:
        if bufor:
            kod = czcionki.get(g().czcionka, g().kodowanie) if g().czcionka is not None else g().kodowanie
            try:
                dopisz(bytes(bufor).decode(kod, errors="replace"))
            except LookupError:
                dopisz(bytes(bufor).decode("cp1252", errors="replace"))
            bufor.clear()

    def ustaw_cel(nazwa: str, gwiazdka: bool) -> None:
        """Pierwsze słowo grupy wskazuje cel (grupy-miejsca, strukturalne, nieznane `{\\*…}`, obrazy, obiekty)."""
        cel = g()
        cel.oddziel = nazwa in STRUKTURALNE or nazwa in MIEJSCA or nazwa in _POLA or (gwiazdka and nazwa not in _CIALO)
        if nazwa in STRUKTURALNE:
            cel.strukturalna, cel.cel = True, nazwa
        elif nazwa in MIEJSCA:
            cel.cel = MIEJSCA[nazwa]
            if cel.cel in _MIEJSCA_TRESCI:
                cel.cel_tresci = cel.cel
        elif nazwa == "shptxt" or (nazwa in _CIALO and cel.strukturalna):
            # pole tekstowe kształtu (także w `\shpinst` i we właściwościach) to treść miejsca, w którym kształt leży
            cel.strukturalna, cel.cel = False, cel.cel_tresci
        elif nazwa == "pict":
            cel.obraz, cel.oddziel = True, False
        elif nazwa == "objdata":
            cel.obiekt, cel.oddziel = True, False
        elif gwiazdka and nazwa not in _CIALO and nazwa not in _POLA:     # `{\*\company …}` w `\info` zostaje w metadanych
            cel.cel = f"*{nazwa}"

    pos, dlugosc = 0, len(dane)
    while pos < dlugosc:
        m = _TOKEN.match(dane, pos)
        if m is None:                # samotny `\` na końcu danych
            pos += 1
            continue
        pos = m.end()
        slowo, param, hexa, znak, nawias, _koniec, tekst = m.groups()
        if hexa is not None:
            if pomin:
                pomin -= 1
                continue
            bufor.append(int(hexa, 16))
            continue
        oproznij()
        if nawias == b"{":
            r = g()
            # grupa w `\pict`/`\objdata` (`\picprop`, `\blipuid`…) nie jest danymi obrazu – jej tekst idzie do swojej części
            stos.append(_Grupa(r.cel, r.kodowanie, r.uc, r.czcionka, r.strukturalna, cel_tresci=r.cel_tresci))
            pomin = 0
            continue
        if nawias == b"}":
            zamykana = stos.pop() if len(stos) > 1 else g()
            if zamykana.oddziel:
                (wynik.strukturalne if zamykana.strukturalna else wynik.teksty).setdefault(zamykana.cel, []).append("\n")
            if zamykana.obraz or zamykana.obiekt:
                bajty = _bajty_szesnastkowe("".join(surowe_obrazu))
                if bajty:
                    (wynik.obrazy if zamykana.obraz else wynik.obiekty).append(bajty)
                surowe_obrazu.clear()
            pomin = 0
            continue
        if _koniec is not None:
            continue
        if tekst is not None:
            t = tekst.decode("latin-1")
            if pomin:
                ile = min(pomin, len(t))
                t, pomin = t[ile:], pomin - ile
            g().pierwsza = False
            if t:
                if g().obraz or g().obiekt:
                    surowe_obrazu.append(t)
                else:
                    bufor.extend(t.encode("latin-1"))
                    oproznij()
            continue
        if znak is not None:
            z = znak.decode("latin-1")
            if z == "*":
                g().gwiazdka = True
                continue
            g().pierwsza = False
            if pomin:
                pomin -= 1
                continue
            if z in "\\{}":
                dopisz(z)
            elif z == "~":
                dopisz("\u00a0")
            elif z == "_":
                dopisz("\u2011")
            elif z in "\r\n":
                dopisz("\n")
            continue
        # słowo kontrolne
        nazwa = slowo.decode("ascii")
        liczba = int(param) if param is not None else None
        if g().pierwsza:
            ustaw_cel(nazwa, g().gwiazdka)
            g().pierwsza = False
        if nazwa == "bin" and liczba is not None and liczba > 0:
            # dokładnie N bajtów danych binarnych (od bajtu po ograniczniku słowa), rozbiór dalej od następnego bajtu
            koniec = min(pos + liczba, dlugosc)
            if g().obraz or g().obiekt:
                surowe_obrazu.append(binascii.hexlify(dane[pos:koniec]).decode("ascii"))
            pos = koniec
            continue
        if nazwa == "u" and liczba is not None:
            kod = liczba + 65536 if -32768 <= liczba < 0 else liczba
            dopisz(chr(kod) if 0 <= kod <= 0x10FFFF else "\ufffd")
            pomin = g().uc
            continue
        if pomin:                   # słowo kontrolne w miejscu znaku zastępczego
            pomin -= 1
            continue
        if nazwa == "uc" and liczba is not None:
            g().uc = liczba
        elif nazwa == "ansicpg" and liczba:
            domyslne = f"cp{liczba}"
            for grupa in stos:
                grupa.kodowanie = domyslne
        elif nazwa == "f" and liczba is not None:
            g().czcionka = liczba
        elif nazwa == "fcharset" and liczba is not None and g().czcionka is not None and g().cel == "fonttbl":
            czcionki[g().czcionka] = STRONY_KODOWE.get(liczba, domyslne)
        elif nazwa in _SYMBOLE:
            dopisz(_SYMBOLE[nazwa])
            if g().cel == "tresc" and not g().strukturalna:
                if nazwa == "par":
                    wynik.struktura["akapity"] += 1
                elif nazwa == "row":
                    wynik.struktura["wiersze_tabel"] += 1
    oproznij()
    for slownik in (wynik.teksty, wynik.strukturalne):
        for klucz, kawalki in slownik.items():
            slownik[klucz] = [_zloz_surogaty("".join(kawalki))]
    return wynik
