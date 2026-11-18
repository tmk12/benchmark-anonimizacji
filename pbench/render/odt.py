"""Renderer ODT (OpenDocument Text): DOCX z `renderuj_docx` przekonwertowany LibreOffice'em (`soffice --headless
--convert-to odt`) – ten sam wzorzec co DOC (`pbench.render.doc`). Warstwa trudnych przypadków (H4b, `formaty_rtf_odt`);
trzon korpusu nie ma tego formatu. Utrudnienia i wejście jak w DOCX (`UTRUDNIENIA_ODT` = `UTRUDNIENIA_DOCX`).

Gdzie co leży w pakiecie ODT (ZIP): treść, tabele, komentarze (`office:annotation` z `dc:creator`), przypisy (`text:note`)
i zmiany śledzone (`text:tracked-changes`) – `content.xml`; nagłówek i stopka – strony wzorcowe w `styles.xml`
(`style:header`, `style:footer`); metadane – `meta.xml` (`dc:title`, `dc:subject`, `meta:initial-creator`, `dc:creator`,
`meta:user-defined`); obrazy – `Pictures/`; miniatura pierwszej strony – `Thumbnails/thumbnail.png`.

Gold = wartości DOCX po sprawdzeniu pliku ODT tak jak w DOC: ODT jest odczytywany z powrotem (LibreOffice ODT -> DOCX), każda
wartość musi występować w tekście swojego miejsca (`doc.teksty_miejsc_docx`, granice słów), obraz – jako bajty PNG w którejś
części pakietu. Czego konwersja nie zachowała, usuwamy z gold z ostrzeżeniem (`WynikDoc.ostrzezenia`).

Determinizm (zbadane, LibreOffice 24.2): konwersja tego samego DOCX daje różne bajty – czasy w nagłówkach ZIP (bieżący czas),
identyfikatory zmian śledzonych (`xml:id`/`text:id`/`text:change-id` = `ct<adres w pamięci>`), losowy przyrostek nazw
komentarzy (`office:name="__Annotation__<n>_<losowa liczba>"`) i losowy `RsidRoot`/`Rsid` w `settings.xml`. `normalizuj_odt` przepakowuje ZIP ze stałym czasem (kolejność części i metoda kompresji bez zmian, `mimetype`
pierwszy i nieskompresowany – jak wymaga ODF), numeruje identyfikatory zmian i przyrostki nazw komentarzy kolejno (`ct1`, `ct2`…, `__Annotation__<n>_1`… w kolejności
pierwszego wystąpienia) i ustawia `Rsid`/`RsidRoot` na stałą. Poza tym treść jest powtarzalna (sprawdza to test determinizmu warstwy).
"""
from __future__ import annotations

import io
import re
import tempfile
import zipfile
from pathlib import Path

from ..model import Dokument, Wartosc
from ..utrudnienia import UTRUDNIENIA_DOCX, UTRUDNIENIA_POMINIETE
from .doc import WynikDoc, konwertuj, odfiltruj_zachowane, teksty_miejsc_docx
from .docx import renderuj_docx
from .wspolne import STALA_DATA_ZIP

UTRUDNIENIA_ODT: frozenset[str] = UTRUDNIENIA_DOCX
MIMETYP_ODT = b"application/vnd.oasis.opendocument.text"
#: Stała wartość `Rsid`/`RsidRoot` w `settings.xml` (LibreOffice losuje ją przy każdej konwersji).
STALY_RSID = "1000000"
_ID_ZMIANY = re.compile(rb'(xml:id|text:id|text:change-id)="(ct\d+)"')
_NAZWA_KOMENTARZA = re.compile(rb'(__Annotation__\d+_)(\d+)')
_RSID = re.compile(rb'(config:name="Rsid(?:Root)?" config:type="int">)\d+(<)')


def _numeruj(dane: bytes, mapa: dict[bytes, bytes], mapa_nazw: dict[bytes, bytes]) -> bytes:
    def zmiana(m: re.Match) -> bytes:
        nowy = mapa.setdefault(m.group(2), b"ct%d" % (len(mapa) + 1))
        return m.group(1) + b'="' + nowy + b'"'

    def nazwa(m: re.Match) -> bytes:
        return m.group(1) + mapa_nazw.setdefault(m.group(2), b"%d" % (len(mapa_nazw) + 1))
    return _NAZWA_KOMENTARZA.sub(nazwa, _ID_ZMIANY.sub(zmiana, dane))


def normalizuj_odt(bajty: bytes) -> bytes:
    """ODT z LibreOffice'a w postaci powtarzalnej (zob. docstring modułu)."""
    mapa: dict[bytes, bytes] = {}       # wspólne dla content.xml i styles.xml (odwołania między częściami)
    mapa_nazw: dict[bytes, bytes] = {}
    wyjscie = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(bajty)) as zin, zipfile.ZipFile(wyjscie, "w") as zout:
        for info in zin.infolist():
            dane = zin.read(info.filename)
            if info.filename.endswith(".xml"):
                dane = _numeruj(dane, mapa, mapa_nazw)
            if info.filename == "settings.xml":
                dane = _RSID.sub(lambda m: m.group(1) + STALY_RSID.encode() + m.group(2), dane)
            zi = zipfile.ZipInfo(info.filename, STALA_DATA_ZIP)
            zi.compress_type = info.compress_type
            zi.external_attr = 0o600 << 16
            zout.writestr(zi, dane)
    return wyjscie.getvalue()


def _bajty_pakietu(plik: Path) -> bytes:
    """Wszystkie części pakietu (do sprawdzenia, czy PNG obrazu przetrwał konwersję)."""
    with zipfile.ZipFile(plik) as z:
        return b"\0".join(z.read(n) for n in z.namelist())


def renderuj_odt(d: Dokument, plik: Path, utrudnienia: set[str]) -> WynikDoc:
    """Zapisuje `d` jako ODT w `plik`; zwraca wartości i obrazy faktycznie obecne w pliku oraz ostrzeżenia."""
    nieznane = set(utrudnienia) - UTRUDNIENIA_ODT - UTRUDNIENIA_POMINIETE
    if nieznane:
        raise ValueError(f"nieznane utrudnienia ODT: {sorted(nieznane)}")
    plik = Path(plik)
    plik.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pbench-odt-") as tmp:
        docx = Path(tmp) / "dokument.docx"
        wynik = renderuj_docx(d, docx, set(utrudnienia))
        surowy = Path(tmp) / "dokument.odt"
        konwertuj(docx, surowy, "odt")
        plik.write_bytes(normalizuj_odt(surowy.read_bytes()))
        zwrot = Path(tmp) / "zwrot" / "dokument.docx"  # odczyt ODT niezależny od zapisu: ODT -> DOCX
        zwrot.parent.mkdir()
        konwertuj(plik, zwrot, "docx")
        teksty = teksty_miejsc_docx(zwrot)
    wartosci, obrazy, ostrzezenia = odfiltruj_zachowane(wynik.wartosci, wynik.obrazy, teksty, _bajty_pakietu(plik))
    return WynikDoc(wartosci, obrazy, [o.replace("konwersja DOC", "konwersja ODT") for o in ostrzezenia])


def render_odt(d: Dokument, plik: Path, utrudnienia: set[str]) -> list[Wartosc]:
    """Jak `renderuj_odt`, ale zwraca tylko listę umieszczonych wartości."""
    return renderuj_odt(d, plik, utrudnienia).wartosci
