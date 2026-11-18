"""Dopisywanie załączników do gotowej wiadomości EML i MSG (warstwa trudnych przypadków H4b, `pbench.trudne_poczta`).

Zwykły renderer poczty (`pbench.render.eml`, `pbench.render.msg`) zapisuje wiadomość trzonu; tu dochodzą załączniki przypadku:
plik (PDF, vCard) albo wiadomość zagnieżdżona z własnymi nagłówkami, treścią i załącznikami. Trzon korpusu tego modułu nie używa.

* **EML**: wiadomość jest wczytywana (`email`, ta sama polityka co renderer), załącznik pliku to część `maintype/subtype` w base64
  z `Content-Disposition: attachment; filename=…`, wiadomość zagnieżdżona – część `message/rfc822` (nagłówki From/To/Subject/Date/
  Message-ID, treść `text/plain` w quoted-printable, własne załączniki). Granice części są przenumerowane jak w rendererze.
* **MSG**: kontener CFB jest wczytywany (`olefile`) i zapisywany ponownie (`render.cfb.zapisz_cfb`); każdy załącznik to storage
  `__attach_version1.0_#N` za załącznikami renderera: plik – `PR_ATTACH_DATA_BIN` (3701, binarne), metoda 1 (`ATTACH_BY_VALUE`);
  wiadomość zagnieżdżona – obiekt osadzony, nie plik: metoda 5 (`ATTACH_EMBEDDED_MSG`), storage `__substg1.0_3701000D`
  (`PR_ATTACH_DATA_OBJ`) z własnymi właściwościami (nagłówek 24 B – MS-OXMSG 2.4.1.2), odbiorcą i załącznikami. Liczniki załączników
  w nagłówku właściwości wiadomości są aktualizowane.

Daty i identyfikatory wiadomości podaje wywołujący (z ziarna dokumentu) – zapis jest deterministyczny.
"""
from __future__ import annotations

import datetime as dt
import email.utils
import struct
from dataclasses import dataclass, field
from email import message_from_bytes
from email.message import EmailMessage
from pathlib import Path

import olefile

from .render.cfb import Drzewo, zapisz_cfb
from .render.eml import _POLITYKA
from .render.msg import MAPI_TO, PROPS, PT_SYSTIME, _filetime, _Magazyn, _wlasciwosci

#: Typ obiektu MAPI (PtypObject) – `PR_ATTACH_DATA_OBJ` wiadomości osadzonej.
PT_OBJECT = 0x000D
ATTACH_BY_VALUE, ATTACH_EMBEDDED_MSG = 1, 5


@dataclass
class Plik:
    """Załącznik-plik: nazwa (bez danych osobowych), typ MIME i bajty."""

    nazwa: str
    typ: tuple[str, str]
    dane: bytes


@dataclass
class Wiadomosc:
    """Wiadomość zagnieżdżona: nadawca i adresat (nazwa, adres), temat, treść, data, Message-ID i jej własne załączniki."""

    nazwa: str
    od: tuple[str, str]
    do: tuple[str, str]
    temat: str
    tresc: str
    data: dt.datetime
    id_wiadomosci: str
    zalaczniki: list[Plik] = field(default_factory=list)


Zalacznik = Plik | Wiadomosc


# ----------------------------------------------------------------------------- EML
def _eml_wiadomosci(w: Wiadomosc) -> EmailMessage:
    m = EmailMessage(policy=_POLITYKA)
    # `formataddr`, nie `Address`: adres zamaskowany przez uczestnika idealnego („[EMAIL_3]___”) nie jest poprawnym addr-spec
    m["From"] = email.utils.formataddr(w.od, charset="utf-8")
    m["To"] = email.utils.formataddr(w.do, charset="utf-8")
    m["Subject"] = w.temat
    m["Date"] = email.utils.format_datetime(w.data)
    m["Message-ID"] = w.id_wiadomosci
    m["MIME-Version"] = "1.0"
    m.set_content(w.tresc, subtype="plain", charset="utf-8", cte="quoted-printable")
    for z in w.zalaczniki:
        m.add_attachment(z.dane, maintype=z.typ[0], subtype=z.typ[1], filename=z.nazwa)
    return m


def dolacz_eml(plik: Path, zalaczniki: list[Zalacznik], znacznik: str) -> None:
    """Dopisuje `zalaczniki` do wiadomości EML `plik`; `znacznik` (stały dla dokumentu) wchodzi do granic części."""
    plik = Path(plik)
    msg = message_from_bytes(plik.read_bytes(), policy=_POLITYKA)
    for z in zalaczniki:
        if isinstance(z, Wiadomosc):
            msg.add_attachment(_eml_wiadomosci(z), disposition="attachment", filename=z.nazwa)
        else:
            msg.add_attachment(z.dane, maintype=z.typ[0], subtype=z.typ[1], filename=z.nazwa)
    wielo = [p for p in msg.walk() if p.is_multipart() and p.get_content_maintype() == "multipart"]
    for i, czesc in enumerate(wielo):
        czesc.set_boundary(f"=_pbench_{i}_{znacznik}")
    plik.write_bytes(msg.as_bytes())


# ----------------------------------------------------------------------------- MSG
def wczytaj_cfb(plik: Path) -> Drzewo:
    """Kontener CFB jako `Drzewo` (storage -> słownik, strumień -> bajty), w kolejności katalogu."""
    ole = olefile.OleFileIO(str(plik))
    try:
        drzewo: Drzewo = {}
        for sciezka in ole.listdir(streams=True, storages=True):
            wezel = drzewo
            for nazwa in sciezka[:-1]:
                wezel = wezel.setdefault(nazwa, {})  # type: ignore[assignment]
            if ole.get_type(sciezka) == olefile.STGTY_STORAGE:
                wezel.setdefault(sciezka[-1], {})
            else:
                wezel[sciezka[-1]] = ole.openstream(sciezka).read()
        return drzewo
    finally:
        ole.close()


def _zalacznik_pliku(z: Plik) -> Drzewo:
    a = _Magazyn()
    a.binarne(0x3701, z.dane)  # PR_ATTACH_DATA_BIN
    a.tekst(0x3707, z.nazwa)  # PR_ATTACH_LONG_FILENAME
    a.tekst(0x3704, z.nazwa)  # PR_ATTACH_FILENAME
    a.tekst(0x3703, "." + z.nazwa.rsplit(".", 1)[-1])
    a.tekst(0x370E, "/".join(z.typ))
    a.tekst(0x3001, z.nazwa)
    a.liczba(0x3705, ATTACH_BY_VALUE)
    return a.zapisz()


def _msg_wiadomosci(w: Wiadomosc) -> Drzewo:
    """Wiadomość osadzona (zawartość storage'u `__substg1.0_3701000D`)."""
    m = _Magazyn()
    m.tekst(0x001A, "IPM.Note")
    m.tekst(0x0037, w.temat)
    m.tekst(0x0C1A, w.od[0])
    m.tekst(0x0C1E, "SMTP")
    m.tekst(0x0C1F, w.od[1])
    m.tekst(0x5D01, w.od[1])
    m.tekst(0x0E04, w.do[0])
    m.tekst(0x1000, w.tresc.replace("\n", "\r\n"))
    m.tekst(0x1035, w.id_wiadomosci)
    m.liczba(0x0E07, 0x01)
    m.liczba(0x340D, 0x00040000)
    m.stale[0x0039 << 16 | PT_SYSTIME] = _filetime(w.data)
    r = _Magazyn()
    r.tekst(0x3001, w.do[0])
    r.tekst(0x3002, "SMTP")
    r.tekst(0x3003, w.do[1])
    r.tekst(0x39FE, w.do[1])
    r.liczba(0x0C15, MAPI_TO)
    drzewo: Drzewo = {"__recip_version1.0_#00000000": r.zapisz()}
    for i, z in enumerate(w.zalaczniki):
        drzewo[f"__attach_version1.0_#{i:08X}"] = _zalacznik_pliku(z)
    drzewo.update(m.drzewo)
    n = len(w.zalaczniki)
    drzewo[PROPS] = _wlasciwosci(m.stale, m.zmienne, struct.pack("<8xIIII", 1, n, 1, n))   # nagłówek wiadomości osadzonej: 24 B
    return drzewo


def _zalacznik_wiadomosci(w: Wiadomosc) -> Drzewo:
    a = _Magazyn()
    a.tekst(0x3001, w.temat)            # PR_DISPLAY_NAME
    a.tekst(0x3707, w.nazwa)
    a.liczba(0x3705, ATTACH_EMBEDDED_MSG)
    a.zmienne[0x3701 << 16 | PT_OBJECT] = 0xFFFFFFFF     # PR_ATTACH_DATA_OBJ: rozmiar obiektu nieokreślony (MS-OXMSG 2.4.2.2)
    drzewo = a.zapisz()
    drzewo[f"__substg1.0_3701{PT_OBJECT:04X}"] = _msg_wiadomosci(w)
    return drzewo


def dolacz_msg(plik: Path, zalaczniki: list[Zalacznik]) -> None:
    """Dopisuje `zalaczniki` do wiadomości MSG `plik` (za załącznikami renderera)."""
    plik = Path(plik)
    drzewo = wczytaj_cfb(plik)
    wlasciwosci = drzewo[PROPS]
    assert isinstance(wlasciwosci, bytes)
    nast_odb, nast_zal, n_odb, n_zal = struct.unpack_from("<IIII", wlasciwosci, 8)
    for i, z in enumerate(zalaczniki, start=n_zal):
        drzewo[f"__attach_version1.0_#{i:08X}"] = _zalacznik_wiadomosci(z) if isinstance(z, Wiadomosc) else _zalacznik_pliku(z)
    k = len(zalaczniki)
    drzewo[PROPS] = wlasciwosci[:8] + struct.pack("<IIII", nast_odb, nast_zal + k, n_odb, n_zal + k) + wlasciwosci[24:]
    zapisz_cfb(plik, drzewo)


def dolacz(plik: Path, format_: str, zalaczniki: list[Zalacznik], znacznik: str) -> None:
    """Dopisuje `zalaczniki` do wiadomości `plik` w formacie `format_` (`eml` albo `msg`)."""
    if format_ == "eml":
        dolacz_eml(plik, zalaczniki, znacznik)
    elif format_ == "msg":
        dolacz_msg(plik, zalaczniki)
    else:
        raise ValueError(f"załączniki poczty: nieobsługiwany format {format_!r}")
