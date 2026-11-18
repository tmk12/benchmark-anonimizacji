"""Renderer EML (RFC 5322/MIME, biblioteka `email`): nagłówki From/To/Cc/Subject z osobami, treść text/plain (+ text/html
przy `html`), stopka z telefonem po separatorze „-- ” i załącznik DOCX (`zalacznik`).

Treść wspólna z MSG (`pbench.render.poczta`; tam opis wejścia, załącznika i `przytnij_dla`). Gdzie co leży: nagłówki
From/To/Cc/Subject i `X-…` – nagłówki MIME (nazwy wyświetlane z diakrytykami zakodowane RFC 2047; wartości „metadane”);
treść – część `text/plain` (i `text/html`) zakodowana quoted-printable w UTF-8, więc surowe bajty NIE zawierają
polskich liter ani zawijanych wartości w postaci jawnej – sędzia pliku musi dekodować części MIME; stopka – ta sama
część po separatorze („stopka”); załącznik – część `application/…wordprocessingml.document` w base64 („zalacznik”).
Wartość występująca w `text/plain` i `text/html` jest zapisana w gold raz. Granice (boundary), Message-ID i data są
wyliczone z id dokumentu, więc plik jest deterministyczny.

Wartość nagłówka z kategorią OSOBA: gdy dokument ma e-mail tej samej osoby (ta sama rola), nagłówek to
`"Nazwa" <adres>` (adres wchodzi do gold jako wartość „metadane”); inaczej sama nazwa wyświetlana – w cudzysłowie (ASCII)
albo jako słowo RFC 2047 (diakrytyki).
"""
from __future__ import annotations

import email.utils
from email import policy
from email.header import Header
from email.headerregistry import Address
from email.message import EmailMessage
from pathlib import Path

from ..model import Dokument, Wartosc
from .poczta import TYP_DOCX, Naglowek, WynikPoczty, zbuduj_wiadomosc

_POLITYKA = policy.SMTP.clone(utf8=False)


def _ustaw_naglowek(msg: EmailMessage, n: Naglowek) -> None:
    if n.kategoria == "OSOBA" and n.adres:  # `"Nazwa" <adres>`; nazwa z diakrytykami zakodowana RFC 2047
        msg[n.nazwa] = Address(display_name=n.tekst, addr_spec=n.adres)
    elif n.kategoria == "OSOBA":  # sama nazwa wyświetlana, poprawnie ujęta w cudzysłów albo zakodowana RFC 2047
        if not n.tekst.isascii():
            msg[n.nazwa] = Header(n.tekst, "utf-8").encode()
        else:
            msg[n.nazwa] = '"' + n.tekst.replace("\\", "\\\\").replace('"', '\\"') + '"'
    else:
        msg[n.nazwa] = n.tekst


def renderuj_eml(d: Dokument, plik: Path, utrudnienia: set[str], zalacznik: Dokument | None = None,
                 utrudnienia_zalacznika: set[str] | None = None) -> WynikPoczty:
    """Zapisuje `d` jako EML w `plik`; zwraca wartości w pliku (z załącznikiem) i obrazy załącznika z gold."""
    w = zbuduj_wiadomosc(d, set(utrudnienia), zalacznik, utrudnienia_zalacznika or set())
    msg = EmailMessage(policy=_POLITYKA)
    for n in w.naglowki:
        _ustaw_naglowek(msg, n)
    msg["Date"] = email.utils.format_datetime(w.data)
    msg["Message-ID"] = w.id_wiadomosci
    msg["MIME-Version"] = "1.0"
    msg.set_content(w.tekst, subtype="plain", charset="utf-8", cte="quoted-printable")
    if w.html is not None:
        msg.add_alternative(w.html, subtype="html", charset="utf-8", cte="quoted-printable")
    if w.zalacznik is not None:
        nazwa, bajty = w.zalacznik
        msg.add_attachment(bajty, maintype=TYP_DOCX[0], subtype=TYP_DOCX[1], filename=nazwa)
    for i, czesc in enumerate(p for p in msg.walk() if p.is_multipart()):
        czesc.set_boundary(f"=_pbench_{i}_{w.id_wiadomosci[1:9]}")
    plik = Path(plik)
    plik.parent.mkdir(parents=True, exist_ok=True)
    plik.write_bytes(msg.as_bytes())
    return w.wynik


def render_eml(d: Dokument, plik: Path, utrudnienia: set[str], zalacznik: Dokument | None = None,
               utrudnienia_zalacznika: set[str] | None = None) -> list[Wartosc]:
    """Jak `renderuj_eml`, ale zwraca tylko listę umieszczonych wartości (z `miejsce`, w tym `zalacznik`)."""
    return renderuj_eml(d, plik, utrudnienia, zalacznik, utrudnienia_zalacznika).wartosci
