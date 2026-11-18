"""Pomocniki wspólne rendererów XLSX, PPTX, EML, MSG i DOC: deterministyczny ZIP, metadane pliku, losowanie."""
from __future__ import annotations

import dataclasses
import datetime as dt
import io
import random
import re
import zipfile
import zlib
from collections.abc import Callable
from xml.sax.saxutils import escape

from ..linearyzacja import ETYKIETY, NAGLOWKI_EMAIL
from ..model import Dokument, Element, Wartosc
from ..utrudnienia import NEUTRALNY_AUTOR

STALA_DATA_ZIP = (2024, 1, 1, 0, 0, 0)
#: Klucze metadanych idące do właściwości podstawowych pliku (reszta – do właściwości własnych).
KLUCZE_CORE = ("author", "title", "subject")


def rng_dokumentu(d: Dokument) -> random.Random:
    return random.Random(zlib.crc32(d.id.encode("utf-8")))


def tekst_fragmentow(fragmenty: list[str | Wartosc]) -> str:
    return "".join(f if isinstance(f, str) else f.tekst for f in fragmenty)


def data_pliku(rng: random.Random) -> tuple[dt.datetime, dt.datetime]:
    """Data utworzenia i modyfikacji pliku (deterministyczne dla ziarna `rng`)."""
    utworzony = dt.datetime(rng.randint(2022, 2025), rng.randint(1, 12), rng.randint(1, 28),
                            rng.randint(8, 17), rng.randint(0, 59))
    return utworzony, utworzony + dt.timedelta(days=rng.randint(0, 40), minutes=rng.randint(1, 600))


def rozdziel_metadane(d: Dokument, zapisz: Callable[[Wartosc, str], Wartosc]) -> tuple[dict[str, str], dict[str, str]]:
    """Metadane dokumentu -> (właściwości podstawowe: author/title/subject, właściwości własne: reszta).

    Wartości wzorcowe z miejscem „metadane” zapisuje przez `zapisz` (inne pomija – leżą w treści); autor bez wartości to autor neutralny.
    """
    core: dict[str, str] = {}
    wlasne: dict[str, str] = {}
    for k, v in d.metadane.items():
        if isinstance(v, Wartosc) and v.miejsce != "metadane":
            continue  # wartość przycięta do treści (np. nagłówek e-maila) – nie trafia do właściwości pliku
        tekst = zapisz(v, "metadane").tekst if isinstance(v, Wartosc) else v
        (core if k in KLUCZE_CORE else wlasne)[k] = tekst
    core.setdefault("author", NEUTRALNY_AUTOR.get(d.jezyk, "User"))
    return core, wlasne


def przepakuj(bajty: bytes, podmiany: dict[str, Callable[[bytes], bytes]] | None = None) -> bytes:
    """ZIP ze stałymi znacznikami czasu (biblioteki zapisują bieżący czas); `podmiany` przetwarzają wskazane części."""
    podmiany = podmiany or {}
    wyjscie = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(bajty)) as zin, zipfile.ZipFile(wyjscie, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            zi = zipfile.ZipInfo(info.filename, STALA_DATA_ZIP)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o600 << 16
            dane = zin.read(info.filename)
            if info.filename in podmiany:
                dane = podmiany[info.filename](dane)
            zout.writestr(zi, dane)
    return wyjscie.getvalue()


def wstaw_firme(xml: bytes, firma: str) -> bytes:
    """Ustawia `<Company>` w docProps/app.xml (dopisuje element albo podmienia istniejący)."""
    tekst = xml.decode("utf-8")
    wpis = f"<Company>{escape(firma)}</Company>"
    if "<Company>" in tekst or "<Company/>" in tekst:
        tekst = re.sub(r"<Company>.*?</Company>|<Company/>", lambda _m: wpis, tekst, flags=re.S)
    else:
        tekst = tekst.replace("</Properties>", wpis + "</Properties>")
    return tekst.encode("utf-8")


def zapisz_jako(w: Wartosc, miejsce: str) -> Wartosc:
    return dataclasses.replace(w, miejsce=miejsce)


def metadane_w_tresci(d: Dokument) -> tuple[list[Element], list[Element]]:
    """Metadane widoczne w treści (poza właściwościami pliku): (blok na początku, linie na końcu).

    Na początku: nagłówki e-maila (typ „email”: from/to/cc/subject) – także druga kopia wartości, które leżą też we
    właściwościach pliku (miejsce „metadane”). Na końcu: pozostałe wartości, których przycięcie zostawiło w treści
    (miejsce inne niż „metadane”). Ciągi znaków bez wartości wzorcowych poza nagłówkami e-maila – tylko we właściwościach.
    """
    etykiety = ETYKIETY.get(d.jezyk, {})
    naglowki = [k for k in NAGLOWKI_EMAIL if k in d.metadane] if d.typ == "email" else []
    kolejnosc = naglowki + sorted((k for k in d.metadane if k not in naglowki), key=lambda x: (etykiety.get(x, x), x))
    poczatek: list[Element] = []
    koniec: list[Element] = []
    for k in kolejnosc:
        v = d.metadane[k]
        if isinstance(v, Wartosc) and v.miejsce == "metadane":
            if k in naglowki:
                poczatek.append(Element("akapit", [f"{etykiety.get(k, k)}: ", dataclasses.replace(v, miejsce="tresc")]))
        elif isinstance(v, Wartosc) or k in naglowki:
            (poczatek if k in naglowki else koniec).append(Element("akapit", [f"{etykiety.get(k, k)}: ", v]))
    return poczatek, koniec


CT_CUSTOM = "application/vnd.openxmlformats-officedocument.custom-properties+xml"


def custom_xml(wlasciwosci: dict[str, str]) -> bytes:
    """`docProps/custom.xml` z właściwościami własnymi (pozostałe klucze metadanych dokumentu)."""
    pozycje = "".join(
        f'<property fmtid="{{D5CDD505-2E9C-101B-9397-08002B2CF9AE}}" pid="{i}" name="{escape(k)}">'
        f"<vt:lpwstr>{escape(v)}</vt:lpwstr></property>" for i, (k, v) in enumerate(sorted(wlasciwosci.items()), 2))
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" '
            'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
            f"{pozycje}</Properties>").encode("utf-8")


def ustaw_modified(xml: bytes, kiedy: dt.datetime) -> bytes:
    """Podmienia `dcterms:modified` w docProps/core.xml (openpyxl nadpisuje je bieżącym czasem przy zapisie)."""
    znacznik = kiedy.strftime("%Y-%m-%dT%H:%M:%SZ")
    return re.sub(rb"(<dcterms:modified[^>]*>)[^<]*(</dcterms:modified>)",
                  lambda m: m.group(1) + znacznik.encode() + m.group(2), xml)
