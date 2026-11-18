"""Testy T17a poza agregacją: kontrola środowiska oceny (sumy `tessdata`, wersje Tesseracta i LibreOffice'a) przed
`pbench-ocen`, suma `tessdata` w kluczu pamięci podręcznej OCR i miara P5 sędziego plikowego (`nadmiarowe`)."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path

import pytest
from PIL import Image

from pbench import ocen, ocr, srodowisko
from pbench.model import Wartosc
from pbench.sedzia import obrazy
from pbench.sedzia.ekstrakcja import Czesc, Wydobycie
from pbench.sedzia.plik import nadmiarowe

pytestmark = pytest.mark.filterwarnings("ignore")


# ----------------------------------------------------------------------------- kontrola środowiska
def _tessdata(katalog: Path, pliki: dict[str, bytes]) -> dict[str, str]:
    katalog.mkdir(parents=True, exist_ok=True)
    for nazwa, dane in pliki.items():
        (katalog / nazwa).write_bytes(dane)
    return {n: hashlib.sha256(d).hexdigest() for n, d in pliki.items()}


def test_sumy_tessdata_z_prerejestracji():
    sumy = srodowisko.sumy_tessdata()
    assert set(sumy) == {f"{k}.traineddata" for k in ("deu", "eng", "fra", "osd", "pol", "spa", "ukr")}
    assert sumy["pol.traineddata"].startswith("c4476cdb")
    assert srodowisko.wersje_oczekiwane() == {"tesseract": "5.3.4", "leptonica": "1.82.0", "libreoffice": "24.2.7.2"}


def test_kontrola_tessdata_brak_i_inna_suma(tmp_path):
    oczekiwane = _tessdata(tmp_path / "td", {"pol.traineddata": b"pol", "eng.traineddata": b"eng"})
    assert srodowisko.sprawdz_tessdata(tmp_path / "td", oczekiwane) == []
    (tmp_path / "td" / "eng.traineddata").write_bytes(b"inne")
    (tmp_path / "td" / "pol.traineddata").unlink()
    problemy = srodowisko.sprawdz_tessdata(tmp_path / "td", oczekiwane)
    assert len(problemy) == 2
    assert any("pol.traineddata" in p and "brak" in p for p in problemy)
    assert any("eng.traineddata" in p and "suma" in p for p in problemy)


def test_ocen_plik_przerywa_przy_niezgodnym_tessdata(tmp_path, monkeypatch, capsys):
    _tessdata(tmp_path / "td", {"pol.traineddata": b"to nie sa dane tesseracta"})
    monkeypatch.setenv("PBENCH_TESSDATA", str(tmp_path / "td"))
    kod = ocen.main(["--uczestnik", "_atrapa", "--split", "dev", "--poziom", "plik", "--korpus", str(tmp_path / "brak"),
                     "--wyniki", str(tmp_path / "wyniki")])
    assert kod == 2
    assert "tessdata" in capsys.readouterr().err
    assert not (tmp_path / "wyniki").exists()                 # nic nie oceniono


def test_kontrola_srodowiska_zgodnego(monkeypatch):
    monkeypatch.delenv("PBENCH_TESSDATA", raising=False)
    if not (ocr.KORZEN / "vendor" / "tessdata").exists():
        pytest.skip("brak vendor/tessdata")
    assert srodowisko.kontrola_srodowiska() == []


def test_kontrola_srodowiska_inna_leptonika(monkeypatch):
    monkeypatch.delenv("PBENCH_TESSDATA", raising=False)
    if not (ocr.KORZEN / "vendor" / "tessdata").exists():
        pytest.skip("brak vendor/tessdata")
    monkeypatch.setattr(srodowisko, "wersja_leptoniki", lambda: "1.79.0")
    assert srodowisko.kontrola_srodowiska() == ["leptonica: wersja 1.79.0, oczekiwana 1.82.0"]


# ----------------------------------------------------------------------------- odcisk sędziego (W3)
def test_odcisk_sedziego_kod_reguly_i_srodowisko(tmp_path, monkeypatch):
    monkeypatch.delenv("PBENCH_TESSDATA", raising=False)
    tekst = srodowisko.odcisk_sedziego("tekst", srodowisko.PREREJESTRACJA)
    assert set(tekst) == {"kod", "reguly", "commit"} and len(tekst["kod"]) == len(tekst["reguly"]) == 64
    plik = srodowisko.odcisk_sedziego("plik", srodowisko.PREREJESTRACJA)
    assert {"tessdata", "tesseract", "leptonica", "libreoffice"} <= set(plik)
    assert (plik["kod"], plik["reguly"]) == (tekst["kod"], tekst["reguly"])
    # inne reguły – inny odcisk; commit nie wchodzi do porównania
    inne = tmp_path / "reguly.md"
    inne.write_text("```yaml\nreguly_wycieku:\n  min_dl_tokenu: 4\n```\n", encoding="utf-8")
    assert srodowisko.suma_regul(inne) != tekst["reguly"]
    assert srodowisko.klucz_odcisku({**tekst, "commit": "x"}) == srodowisko.klucz_odcisku(tekst)
    assert srodowisko.klucz_odcisku({**tekst, "kod": "0" * 64}) != srodowisko.klucz_odcisku(tekst)


def test_odcisk_kodu_zmienia_sie_ze_zmiana_pliku_sedziego(tmp_path):
    (tmp_path / "pbench" / "sedzia").mkdir(parents=True)
    (tmp_path / "pbench" / "sedzia" / "tekst.py").write_text("A = 1\n", encoding="utf-8")
    (tmp_path / "pbench" / "ocen.py").write_text("", encoding="utf-8")
    przed = srodowisko.suma_kodu_sedziego(tmp_path)
    (tmp_path / "pbench" / "sedzia" / "tekst.py").write_text("A = 2\n", encoding="utf-8")
    assert srodowisko.suma_kodu_sedziego(tmp_path) != przed


# ----------------------------------------------------------------------------- klucz pamięci podręcznej OCR
def test_klucz_pamieci_ocr_zawiera_sume_tessdata(tmp_path, monkeypatch):
    _tessdata(tmp_path / "td", {"pol.traineddata": b"a"})
    monkeypatch.setenv("PBENCH_TESSDATA", str(tmp_path / "td"))
    k1 = ocr.skrot_tessdata()
    (tmp_path / "td" / "pol.traineddata").write_bytes(b"b")
    k2 = ocr.skrot_tessdata()
    assert k1 != k2 and len(k1) == 12
    monkeypatch.setenv("PBENCH_OCR_CACHE", str(tmp_path / "ocr"))
    bufor = io.BytesIO()
    Image.new("RGB", (4, 4), "white").save(bufor, "PNG")
    obrazy.ocr_tekst(bufor.getvalue(), "pl")
    assert [p.name for p in (tmp_path / "ocr").iterdir() if k2 in p.name]


# ----------------------------------------------------------------------------- P5: nadmiarowe maskowanie w pliku
def _w(*czesci: Czesc, rodzaj: str = "docx") -> Wydobycie:
    return Wydobycie(rodzaj=rodzaj, czesci=list(czesci))


def _gold(tekst: str, miejsce: str = "tresc", wid: str = "osoba#1", kat: str = "OSOBA") -> Wartosc:
    return Wartosc(wid, kat, tekst, "pl", miejsce, kat)


ORYG = "Jan Kowalski podpisał umowę najmu."      # poza gold: „podpisał” 8 + „umowę” 5 + „najmu” 5 + „.” 1


def test_nadmiarowe_zero_gdy_maskowane_tylko_gold():
    o = _w(Czesc("word/document.xml", [ORYG], tresc=True))
    w = _w(Czesc("word/document.xml", ["[OSOBA_1] podpisał umowę najmu."], tresc=True))
    assert nadmiarowe(o, w, [_gold("Jan Kowalski")]) == {"znaki": 0, "poza_gold": 19}


def test_nadmiarowe_liczy_zamienione_i_usuniete_slowa_poza_gold():
    o = _w(Czesc("word/document.xml", [ORYG], tresc=True))
    w = _w(Czesc("word/document.xml", ["[OSOBA_1] podpisał [X] ."], tresc=True))
    assert nadmiarowe(o, w, [_gold("Jan Kowalski")]) == {"znaki": 10, "poza_gold": 19}


def test_nadmiarowe_tylko_tekst_widoczny():
    """Metadane, komentarze i druga reprezentacja treści (HTML obok text/plain) nie wchodzą do P5."""
    o = _w(Czesc("word/document.xml", [ORYG], tresc=True), Czesc("word/comments.xml", ["uwaga recenzenta"], tresc=True),
           Czesc("docProps/core.xml", ["autor Anna Nowak"]), Czesc("eml:czesc 2 text/html", ["kopia"], tresc=True, wariant=True))
    w = _w(Czesc("word/document.xml", ["[OSOBA_1] podpisał umowę najmu."], tresc=True))
    assert nadmiarowe(o, w, [_gold("Jan Kowalski")]) == {"znaki": 0, "poza_gold": 19}


def test_nadmiarowe_brak_czesci_w_wyniku_to_usuniecie():
    o = _w(Czesc("word/document.xml", [ORYG], tresc=True), Czesc("word/footer1.xml", ["Strona"], tresc=True))
    w = _w(Czesc("word/document.xml", ["[OSOBA_1] podpisał umowę najmu."], tresc=True))
    assert nadmiarowe(o, w, [_gold("Jan Kowalski")]) == {"znaki": 6, "poza_gold": 25}


def test_nadmiarowe_format_zamieniony_wyrownanie_calosci():
    o = _w(Czesc("doc->docx:word/document.xml", [ORYG], tresc=True), rodzaj="doc")
    w = _w(Czesc("word/document.xml", ["[OSOBA_1] podpisał umowę najmu."], tresc=True))
    assert nadmiarowe(o, w, [_gold("Jan Kowalski")]) == {"znaki": 0, "poza_gold": 19}


def test_nadmiarowe_gold_kazde_wystapienie_takze_obrazowe_pominiete():
    o = _w(Czesc("word/document.xml", ["Jan Kowalski i Jan Kowalski."], tresc=True))
    w = _w(Czesc("word/document.xml", ["[A] i [A]."], tresc=True))
    obrazowa = Wartosc("logo#1", "ORGANIZACJA", "i", "pl", "obraz", "ORGANIZACJA")   # w pikselach – nie jest tekstem
    assert nadmiarowe(o, w, [_gold("Jan Kowalski"), obrazowa]) == {"znaki": 0, "poza_gold": 2}


def test_nadmiarowe_strona_pdf_bez_warstwy_tekstowej_z_ocr():
    o = _w(Czesc("pdf:strona 1", [ORYG], tresc=True), rodzaj="pdf")
    w = _w(rodzaj="pdf")
    ocr_stron = [("pdf:render strona 1", "[OSOBA] podpisał umowę najmu.")]
    assert nadmiarowe(o, w, [_gold("Jan Kowalski")], ocr_stron) == {"znaki": 0, "poza_gold": 19}
