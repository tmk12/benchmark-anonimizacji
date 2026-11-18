"""Renderer MSG (Outlook, format CFB/OLE z właściwościami MAPI) – zapis własny (`pbench.render.cfb`), bez bibliotek zapisu.

Treść wspólna z EML (`pbench.render.poczta`): te same nagłówki, treść, stopka i załącznik. Gdzie co leży (strumienie
`__substg1.0_<tag><typ>`, tekst UTF-16LE `001F`): PR_SUBJECT 0037; PR_SENDER_NAME 0C1A, PR_SENDER_EMAIL_ADDRESS 0C1F i
PR_SENDER_SMTP_ADDRESS 5D01 (From); PR_DISPLAY_TO 0E04 i PR_DISPLAY_CC 0E03 oraz storage'e `__recip_version1.0_#n`
(PR_DISPLAY_NAME 3001, adres 3003/39FE) – wartości „metadane”; PR_BODY 1000 (treść i stopka po „-- ”, CRLF) i PR_HTML 1013
(`html`, UTF-8; wartość w treści i HTML zapisana w gold raz); PR_TRANSPORT_MESSAGE_HEADERS 007D z liniami `X-…`
(`metadane`); załącznik – storage `__attach_version1.0_#0` z PR_ATTACH_DATA_BIN 3701 (bajty DOCX), PR_ATTACH_LONG_FILENAME
3707 `<typ>.docx` (bez danych osobowych) („zalacznik”). Rozmiary tekstów w tablicy właściwości zawierają terminator UTF-16 (+2 B), jak zapisuje Outlook. Czas wysłania PR_CLIENT_SUBMIT_TIME wyliczony z id dokumentu (plik jest deterministyczny).
Weryfikacja w testach: `olefile` (strumienie) i `extract_msg` (tylko odczyt).
"""
from __future__ import annotations

import datetime as dt
import struct
from pathlib import Path

from ..model import Dokument, Wartosc
from .cfb import Drzewo, zapisz_cfb
from .poczta import Naglowek, WynikPoczty, Wiadomosc, zbuduj_wiadomosc

PROPS = "__properties_version1.0"
_EPOKA_FILETIME = 116444736000000000
PT_LONG, PT_SYSTIME, PT_STRING, PT_BINARY = 0x0003, 0x0040, 0x001F, 0x0102
MAPI_TO, MAPI_CC = 1, 2


def _filetime(kiedy: dt.datetime) -> bytes:
    return struct.pack("<Q", int(round(kiedy.timestamp() * 10_000_000)) + _EPOKA_FILETIME)


def _wlasciwosci(stale: dict[int, bytes], zmienne: dict[int, int], naglowek: bytes) -> bytes:
    """`__properties_version1.0`: nagłówek, potem wpisy po 16 bajtów (tag, flagi, wartość albo rozmiar)."""
    wyjscie = bytearray(naglowek)
    for tag, wartosc in stale.items():
        wyjscie += struct.pack("<II", tag, 0x06) + wartosc.ljust(8, b"\0")
    for tag, dlugosc in zmienne.items():
        wyjscie += struct.pack("<III", tag, 0x06, dlugosc) + b"\0" * 4
    return bytes(wyjscie)


class _Magazyn:
    """Strumienie jednego storage'u (wiadomość, odbiorca, załącznik) i ich wpisy w tablicy właściwości."""

    def __init__(self) -> None:
        self.drzewo: Drzewo = {}
        self.zmienne: dict[int, int] = {}
        self.stale: dict[int, bytes] = {}

    def tekst(self, tag: int, wartosc: str) -> None:
        if wartosc:
            surowe = wartosc.encode("utf-16-le")
            self.drzewo[f"__substg1.0_{tag:04X}{PT_STRING:04X}"] = surowe
            self.zmienne[tag << 16 | PT_STRING] = len(surowe) + 2  # rozmiar z terminatorem UTF-16, jak zapisuje Outlook

    def binarne(self, tag: int, dane: bytes) -> None:
        self.drzewo[f"__substg1.0_{tag:04X}{PT_BINARY:04X}"] = dane
        self.zmienne[tag << 16 | PT_BINARY] = len(dane)

    def liczba(self, tag: int, wartosc: int) -> None:
        self.stale[tag << 16 | PT_LONG] = struct.pack("<I", wartosc)

    def zapisz(self, naglowek: bytes = b"\0" * 8) -> Drzewo:
        self.drzewo[PROPS] = _wlasciwosci(self.stale, self.zmienne, naglowek)
        return self.drzewo


def _adres(n: Naglowek) -> str:
    """Adres SMTP nagłówka: adres osoby z dokumentu, sam tekst gdy to adres (kategoria EMAIL / „@”); inaczej pusty."""
    if n.adres:
        return n.adres
    return n.tekst if n.kategoria == "EMAIL" or (n.kategoria is None and "@" in n.tekst) else ""


def _x_naglowki(w: Wiadomosc) -> str:
    return "".join(f"{n.nazwa}: {n.tekst}\r\n" for n in w.naglowki if n.nazwa.startswith("X-"))


def renderuj_msg(d: Dokument, plik: Path, utrudnienia: set[str], zalacznik: Dokument | None = None,
                 utrudnienia_zalacznika: set[str] | None = None) -> WynikPoczty:
    """Zapisuje `d` jako MSG w `plik`; zwraca wartości w pliku (z załącznikiem) i obrazy załącznika z gold."""
    w = zbuduj_wiadomosc(d, set(utrudnienia), zalacznik, utrudnienia_zalacznika or set())
    od, do, dw, temat = (w.naglowek(k) for k in ("From", "To", "Cc", "Subject"))
    msg = _Magazyn()
    msg.tekst(0x001A, "IPM.Note")
    msg.tekst(0x0037, temat.tekst if temat else "")
    if od:
        msg.tekst(0x0C1A, od.tekst)
        msg.tekst(0x0C1E, "SMTP" if _adres(od) else "")
        msg.tekst(0x0C1F, _adres(od))
        msg.tekst(0x5D01, _adres(od))
    msg.tekst(0x0E04, do.tekst if do else "")
    msg.tekst(0x0E03, dw.tekst if dw else "")
    msg.tekst(0x1000, w.tekst.replace("\n", "\r\n"))
    msg.tekst(0x1035, w.id_wiadomosci)
    if "X-" in "".join(n.nazwa for n in w.naglowki):
        msg.tekst(0x007D, _x_naglowki(w))
    if w.html is not None:
        msg.binarne(0x1013, w.html.encode("utf-8"))
        msg.liczba(0x3FDE, 65001)  # PR_INTERNET_CPID: UTF-8
    msg.liczba(0x0E07, 0x01)  # PR_MESSAGE_FLAGS: przeczytana
    msg.liczba(0x340D, 0x00040000)  # PR_STORE_SUPPORT_MASK: STORE_UNICODE_OK
    msg.stale[0x0039 << 16 | PT_SYSTIME] = _filetime(w.data)  # PR_CLIENT_SUBMIT_TIME

    korzen: Drzewo = {}
    odbiorcy = [(n, MAPI_TO) for n in (do,) if n] + [(n, MAPI_CC) for n in (dw,) if n]
    for i, (n, typ) in enumerate(odbiorcy):
        r = _Magazyn()
        r.tekst(0x3001, n.tekst)
        r.tekst(0x3002, "SMTP" if _adres(n) else "")
        r.tekst(0x3003, _adres(n))
        r.tekst(0x39FE, _adres(n))
        r.liczba(0x0C15, typ)  # PR_RECIPIENT_TYPE
        korzen[f"__recip_version1.0_#{i:08X}"] = r.zapisz()
    if w.zalacznik is not None:
        nazwa, dane = w.zalacznik
        a = _Magazyn()
        a.binarne(0x3701, dane)  # PR_ATTACH_DATA_BIN
        a.tekst(0x3707, nazwa)  # PR_ATTACH_LONG_FILENAME
        a.tekst(0x3704, nazwa)  # PR_ATTACH_FILENAME
        a.tekst(0x3703, ".docx")
        a.tekst(0x370E, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        a.tekst(0x3001, nazwa)
        a.liczba(0x3705, 1)  # PR_ATTACH_METHOD: ATTACH_BY_VALUE
        korzen["__attach_version1.0_#00000000"] = a.zapisz()
    n_zal = 1 if w.zalacznik is not None else 0
    korzen.update(msg.drzewo)
    korzen[PROPS] = _wlasciwosci(msg.stale, msg.zmienne,
                                 struct.pack("<8xIIII8x", len(odbiorcy), n_zal, len(odbiorcy), n_zal))
    korzen["__nameid_version1.0"] = {"__substg1.0_00020102": b"", "__substg1.0_00030102": b"",
                                     "__substg1.0_00040102": b""}
    plik = Path(plik)
    plik.parent.mkdir(parents=True, exist_ok=True)
    zapisz_cfb(plik, korzen)
    return w.wynik


def render_msg(d: Dokument, plik: Path, utrudnienia: set[str], zalacznik: Dokument | None = None,
               utrudnienia_zalacznika: set[str] | None = None) -> list[Wartosc]:
    """Jak `renderuj_msg`, ale zwraca tylko listę umieszczonych wartości (z `miejsce`, w tym `zalacznik`)."""
    return renderuj_msg(d, plik, utrudnienia, zalacznik, utrudnienia_zalacznika).wartosci
