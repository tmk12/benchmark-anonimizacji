"""Testy renderera PDF z tekstem i skanów: wartości w tekście stron, /Annots, AcroForm, /Info, XMP; skan bez warstwy
tekstu, ramki obrazów i kontrola jakości OCR (Tesseract)."""
from __future__ import annotations

import difflib
import io
import math
import random
import re
from collections import Counter
from pathlib import Path

import pikepdf
import pypdfium2 as pdfium
import pytest
from PIL import Image
from test_render_docx import _bogaty, _szablonowy

from pbench import ocr
from pbench.linearyzacja import linearyzuj_z_wartosciami
from pbench.model import Dokument, Element, Obraz, Wartosc
from pbench.render.pdf import render_pdf, renderuj_pdf, zbuduj_pdf
from pbench.render.skan import UTRUDNIENIA_SKAN, render_skan, renderuj_skan
from pbench.utrudnienia import UTRUDNIENIA_PDF, przytnij, przytnij_pdf

WSZYSTKIE = set(UTRUDNIENIA_PDF)


def _norm(s: str) -> str:
    return " ".join(s.split())


def _bez_spacji(s: str) -> str:
    return "".join(s.split())


def _tekst_stron(plik: Path) -> list[str]:
    pdf = pdfium.PdfDocument(str(plik))
    try:
        return [pdf[i].get_textpage().get_text_range() for i in range(len(pdf))]
    finally:
        pdf.close()


def _tekst(plik: Path) -> str:
    return _norm("\n".join(_tekst_stron(plik)))


def _adnotacje(plik: Path) -> list[pikepdf.Dictionary]:
    with pikepdf.open(plik) as pdf:
        return [pikepdf.Dictionary(a) for p in pdf.pages for a in p.get("/Annots", [])
                if a.get("/Subtype") == "/Text"]


def _pola(plik: Path) -> list[tuple[str, str]]:
    with pikepdf.open(plik) as pdf:
        if "/AcroForm" not in pdf.Root:
            return []
        return [(str(f.get("/T")), str(f.get("/V"))) for f in pdf.Root.AcroForm.Fields]


def _info_xmp(plik: Path) -> tuple[dict[str, str], str]:
    with pikepdf.open(plik) as pdf:
        info = {str(k): str(v) for k, v in pdf.docinfo.items()}
        xmp = bytes(pdf.Root.Metadata.read_bytes()).decode("utf-8") if "/Metadata" in pdf.Root else ""
    return info, xmp


def _dlugi() -> Dokument:
    """Dokument kilkustronicowy (nagłówek/stopka na każdej stronie) z przypisami na różnych stronach."""
    d = _bogaty()
    d.id = "test-dlugi"
    akapity = [Element("akapit", [f"Akapit {i}. " + "Lorem ipsum dolor sit amet consectetur adipiscing elit. " * 12])
               for i in range(14)]
    przyp = [Element("przypis", [f"Przypis {i}: ", Wartosc(f"s.sygn#{i}", "SYGNATURA", f"II K {i}00/2{i}", "pl",
                                                              "przypis", "SYGNATURA")]) for i in range(1, 5)]
    pierwsze = [e for e in d.elementy if e.rodzaj in ("naglowek",)]
    reszta = [e for e in d.elementy if e.rodzaj not in ("naglowek", "przypis")]
    d.elementy = pierwsze + akapity + reszta + przyp
    return d


# ----------------------------------------------------------------------------- brief
def test_pdf_tekst_wyciagalny(tmp_path):
    plik = tmp_path / "a.pdf"
    d = przytnij(_bogaty(), WSZYSTKIE)
    wartosci = render_pdf(d, plik, WSZYSTKIE)
    tekst = _tekst(plik)
    treść = [w for w in wartosci if w.miejsce in ("tresc", "tabela")]
    assert treść
    for w in treść:
        assert _norm(w.tekst) in tekst, w.tekst


def _sprawdz_miejsca(plik: Path, wartosci: list[Wartosc]) -> None:
    tekst = _tekst(plik)
    adn = _adnotacje(plik)
    pola = [v for _, v in _pola(plik)]
    info, xmp = _info_xmp(plik)
    adn_teksty = [str(a.get("/T", "")) for a in adn] + [str(a.get("/Contents", "")) for a in adn]
    for w in wartosci:
        if w.miejsce in ("tresc", "tabela", "naglowek", "stopka", "przypis"):
            assert _norm(w.tekst) in tekst, (w.id, w.tekst, w.miejsce)
        elif w.miejsce == "komentarz":
            assert any(w.tekst in t for t in adn_teksty), (w.id, w.tekst)
        elif w.miejsce == "pole":
            assert w.tekst in pola, (w.id, w.tekst)
        elif w.miejsce == "metadane":
            assert w.tekst in info.values() or w.tekst in xmp, (w.id, w.tekst)
        else:
            assert w.miejsce == "obraz", w.miejsce


@pytest.mark.parametrize("utrudnienia", [set(), WSZYSTKIE, {"papier_firmowy", "tabele"},
                                         {"komentarze", "pola", "metadane"}, {"przypisy", "podpis"}])
def test_wartosci_w_pdf_bogaty(tmp_path, utrudnienia):
    d = przytnij(_bogaty(), utrudnienia)
    plik = tmp_path / "a.pdf"
    wartosci = render_pdf(d, plik, utrudnienia)
    assert wartosci
    _sprawdz_miejsca(plik, wartosci)


@pytest.mark.parametrize("jezyk,typ", [("pl", "umowa"), ("pl", "notatka"), ("pl", "lista_plac"), ("en", "faktura"),
                                       ("de", "cv"), ("fr", "email"), ("es", "odpis_rejestru"),
                                       ("pl", "pelnomocnictwo"), ("en", "pelnomocnictwo")])
def test_wartosci_w_pdf_szablony(tmp_path, jezyk, typ):
    d = przytnij(_szablonowy(jezyk, typ, 1), WSZYSTKIE)
    plik = tmp_path / "a.pdf"
    _sprawdz_miejsca(plik, render_pdf(d, plik, WSZYSTKIE))


@pytest.mark.parametrize("jezyk,typ", [("pl", "umowa"), ("en", "faktura"), ("de", "cv"), ("fr", "email"),
                                       ("pl", "pelnomocnictwo")])
@pytest.mark.parametrize("utrudnienia", [set(), {"papier_firmowy"}, {"tabele", "metadane"}, WSZYSTKIE])
def test_linearyzacja_przycietego_zgodna_ze_zwroconymi(tmp_path, jezyk, typ, utrudnienia):
    d = przytnij(_szablonowy(jezyk, typ, 2), utrudnienia)
    wartosci = render_pdf(d, tmp_path / "a.pdf", utrudnienia)
    _, _, lin = linearyzuj_z_wartosciami(d)
    zwrocone = Counter((w.id, w.tekst, w.miejsce) for w in wartosci if w.miejsce != "obraz")
    oczekiwane = Counter((w.id, w.tekst, w.miejsce) for w in lin)
    if typ == "email":  # nagłówki e-maila z `metadane`: druga, widoczna kopia w treści
        oczekiwane.update((v.id, v.tekst, "tresc") for k, v in d.metadane.items()
                          if k in ("from", "to", "cc") and isinstance(v, Wartosc) and v.miejsce == "metadane")
    assert zwrocone == oczekiwane


def test_linearyzacja_bogatego_zgodna(tmp_path):
    for utr in (set(), WSZYSTKIE, WSZYSTKIE - {"papier_firmowy", "pola", "tabele"}):
        d = przytnij(_bogaty(), utr)
        wartosci = render_pdf(d, tmp_path / "a.pdf", utr)
        _, _, lin = linearyzuj_z_wartosciami(d)
        assert Counter((w.id, w.tekst, w.miejsce) for w in wartosci if w.miejsce != "obraz") == \
            Counter((w.id, w.tekst, w.miejsce) for w in lin)


# ----------------------------------------------------------------------------- utrudnienia
def test_komentarz_adnotacja_text(tmp_path):
    plik = tmp_path / "a.pdf"
    render_pdf(przytnij(_bogaty(), {"komentarze"}), plik, {"komentarze"})
    adn = _adnotacje(plik)
    assert len(adn) == 1
    assert str(adn[0].T) == "Piotr Nowak" and "Do sprawdzenia." in str(adn[0].Contents)
    assert "Piotr Nowak" not in str(adn[0].Contents)  # autor tylko w /T


def test_pole_acroform_z_wygladem(tmp_path):
    plik = tmp_path / "a.pdf"
    render_pdf(przytnij(_bogaty(), {"pola"}), plik, {"pola"})
    with pikepdf.open(plik) as pdf:
        pola = list(pdf.Root.AcroForm.Fields)
        assert len(pola) == 1
        f = pola[0]
        assert str(f.V) == "anna@example.com" and f.FT == "/Tx"
        assert "anna" not in str(f.T) and "/AP" in f and "/N" in f.AP
        assert f.get("/Subtype") == "/Widget"
        assert pdf.pages[0].Annots[0].objgen == f.objgen or any(a.objgen == f.objgen for a in pdf.pages[0].Annots)


def test_komentarz_i_pole_poza_tekstem_strony(tmp_path):
    plik = tmp_path / "a.pdf"
    render_pdf(przytnij(_bogaty(), {"komentarze", "pola"}), plik, {"komentarze", "pola"})
    tekst = _tekst(plik)
    assert "Piotr Nowak" not in tekst and "Do sprawdzenia." not in tekst and "anna@example.com" not in tekst


def test_pole_polskie_znaki_w_v(tmp_path):
    d = przytnij(_bogaty(), {"pola"})
    for e in d.elementy:
        if e.rodzaj == "pole":
            e.fragmenty = [Wartosc("klient.pelne#9", "OSOBA", "Zażółć Gęślą Jaźń", "pl", "pole", "OSOBA")]
    plik = tmp_path / "a.pdf"
    wart = render_pdf(d, plik, {"pola"})
    assert ("pole" in {w.miejsce for w in wart}) and "Zażółć Gęślą Jaźń" in [v for _, v in _pola(plik)]


def test_metadane_info_i_xmp(tmp_path):
    plik = tmp_path / "a.pdf"
    wartosci = render_pdf(przytnij(_bogaty(), {"metadane"}), plik, {"metadane"})
    info, xmp = _info_xmp(plik)
    assert info["/Author"] == "Marek Wójcik" and info["/Title"] == "Umowa testowa" and info["/Subject"] == "Test"
    assert "Marek Wójcik" in xmp and "Umowa testowa" in xmp and "dc:creator" in xmp and "dc:title" in xmp
    assert any(w.miejsce == "metadane" and w.tekst == "Marek Wójcik" for w in wartosci)


def test_metadane_neutralne_bez_utrudnienia(tmp_path):
    plik = tmp_path / "a.pdf"
    wartosci = render_pdf(przytnij(_bogaty(), set()), plik, set())
    info, xmp = _info_xmp(plik)
    assert info["/Author"] == "Użytkownik" and "Wójcik" not in xmp and "Wójcik" not in "".join(info.values())
    assert not any(w.miejsce == "metadane" for w in wartosci)


def test_metadane_dodatkowe_klucze(tmp_path):
    d = _szablonowy("pl", "umowa", 3)
    d.metadane["case"] = Wartosc("sprawa.sygnatura#9", "SYGNATURA", "XII C 777/23", "pl", "metadane", "SYGNATURA")
    plik = tmp_path / "a.pdf"
    wartosci = render_pdf(przytnij(d, {"metadane"}), plik, {"metadane"})
    info, xmp = _info_xmp(plik)
    assert "XII C 777/23" in info.values() and "XII C 777/23" in xmp
    assert any(w.tekst == "XII C 777/23" and w.miejsce == "metadane" for w in wartosci)


def test_papier_firmowy_na_kazdej_stronie(tmp_path):
    plik = tmp_path / "a.pdf"
    wartosci = render_pdf(przytnij(_dlugi(), {"papier_firmowy"}), plik, {"papier_firmowy"})
    strony = _tekst_stron(plik)
    assert len(strony) >= 3
    for i, t in enumerate(strony, 1):
        assert "Prusa 12" in _norm(t) and "KRS 0000123456" in _norm(t), i  # nagłówek i stopka na każdej
        assert f"Strona {i}" in _norm(t)
    with pikepdf.open(plik) as pdf:
        assert all(len(p.get_images()) >= 1 for p in pdf.pages)  # logo na każdej stronie
    assert any(w.miejsce == "obraz" and w.kategoria == "ORGANIZACJA" for w in wartosci)
    assert {w.miejsce for w in wartosci if w.kategoria == "NIP"} == {"naglowek"}


def test_bez_papieru_naglowek_w_tresci(tmp_path):
    plik = tmp_path / "a.pdf"
    wartosci = render_pdf(przytnij(_bogaty(), set()), plik, set())
    assert "Prusa 12" in _tekst(plik)
    assert {w.miejsce for w in wartosci if w.kategoria in ("NIP", "KRS")} == {"tresc"}
    assert not any(w.miejsce == "obraz" for w in wartosci)
    with pikepdf.open(plik) as pdf:
        assert not any(p.get_images() for p in pdf.pages)


def _operatory(plik: Path) -> Counter:
    with pikepdf.open(plik) as pdf:
        return Counter(str(op) for p in pdf.pages for _, op in pikepdf.parse_content_stream(p))


def test_tabele_z_obramowaniem(tmp_path):
    z, bez = tmp_path / "z.pdf", tmp_path / "b.pdf"
    render_pdf(przytnij(_bogaty(), {"tabele"}), z, {"tabele"})
    render_pdf(przytnij(_bogaty(), set()), bez, set())
    kreski = lambda c: c["l"] + c["re"]  # noqa: E731
    assert kreski(_operatory(z)) >= 4 and kreski(_operatory(bez)) == 0
    assert "44051401359" in _tekst(z)


def test_przypis_u_dolu_strony(tmp_path):
    plik = tmp_path / "a.pdf"
    wartosci = render_pdf(przytnij(_dlugi(), {"przypisy"}), plik, {"przypisy"})
    pdf = pdfium.PdfDocument(str(plik))
    try:
        znalezione = 0
        for w in (w for w in wartosci if w.miejsce == "przypis"):
            for i in range(len(pdf)):
                tp = pdf[i].get_textpage()
                tekst = tp.get_text_range()
                p = tekst.replace("\r\n", " ").find(w.tekst)
                if p < 0:
                    continue
                znalezione += 1
                l, b, r, t = tp.get_charbox(tekst.find(w.tekst.split()[0]))
                wys = pdf[i].get_height()
                assert t < wys * 0.25, (w.tekst, t, wys)  # w dolnej ćwiartce strony (nad stopką)
        assert znalezione == len([w for w in wartosci if w.miejsce == "przypis"]) == 4
    finally:
        pdf.close()


def test_przypis_nie_zachodzi_na_tresc(tmp_path):
    """Na każdej stronie tekst przypisów leży pod całą treścią (rezerwa miejsca na przypisy)."""
    plik = tmp_path / "a.pdf"
    wartosci = render_pdf(przytnij(_dlugi(), {"przypisy"}), plik, {"przypisy"})
    pdf = pdfium.PdfDocument(str(plik))
    try:
        for i in range(len(pdf)):
            tp = pdf[i].get_textpage()
            tekst = tp.get_text_range()
            dol_przypisu = [tp.get_charbox(j)[3] for j in range(len(tekst)) if tekst.startswith("Przypis ", j)]
            if not dol_przypisu:
                continue
            gora_przypisow = max(dol_przypisu)
            tresc = [tp.get_charbox(j)[1] for j in range(len(tekst)) if tekst.startswith("Akapit ", j)]
            assert all(y > gora_przypisow for y in tresc), (i, min(tresc), gora_przypisow)
    finally:
        pdf.close()
    assert sum(w.miejsce == "przypis" for w in wartosci) == 4


def test_podpis_obraz_i_gold(tmp_path):
    plik = tmp_path / "a.pdf"
    w = renderuj_pdf(przytnij(_bogaty(), {"podpis"}), plik, {"podpis"})
    assert len(w.obrazy) == 1
    ob = w.obrazy[0]
    assert isinstance(ob, Obraz) and ob.png and len(ob.wartosci) == 1 and len(ob.ramki) == 1
    wart = ob.wartosci[0]
    assert (wart.kategoria, wart.tekst, wart.miejsce) == ("OSOBA", "Anna Kowalska", "obraz")
    img = Image.open(io.BytesIO(ob.png))
    x0, y0, x1, y1 = ob.ramki[0][1]
    assert 0 <= x0 < x1 <= img.width and 0 <= y0 < y1 <= img.height
    with pikepdf.open(plik) as pdf:
        assert sum(len(p.get_images()) for p in pdf.pages) == 1
    assert "Anna Kowalska" in _tekst(plik) and wart in w.wartosci


def test_logo_gold_obrazu(tmp_path):
    plik = tmp_path / "a.pdf"
    w = renderuj_pdf(przytnij(_bogaty(), {"papier_firmowy"}), plik, {"papier_firmowy"})
    assert len(w.obrazy) == 1 and w.obrazy[0].wartosci[0].tekst == "Zielińscy i Wspólnicy Kancelaria Prawna"
    assert w.obrazy[0].wartosci[0].miejsce == "obraz"


def test_deterministyczny(tmp_path):
    a, b = tmp_path / "a.pdf", tmp_path / "b.pdf"
    wa = render_pdf(przytnij(_dlugi(), WSZYSTKIE), a, WSZYSTKIE)
    wb = render_pdf(przytnij(_dlugi(), WSZYSTKIE), b, WSZYSTKIE)
    assert wa == wb and a.read_bytes() == b.read_bytes()
    with pikepdf.open(a) as pdf:
        assert "/ID" in pdf.trailer
        data = str(pdf.docinfo["/CreationDate"])
    assert re.match(r"D:20(2[2-5])\d{10}", data)


def test_nieznane_utrudnienie(tmp_path):
    with pytest.raises(ValueError, match="nieznane"):
        render_pdf(_bogaty(), tmp_path / "a.pdf", {"xyz"})


def test_zmiany_sledzone_nie_wystepuja_w_pdf(tmp_path):
    with pytest.raises(ValueError, match="zmiany"):
        render_pdf(przytnij(_bogaty(), {"zmiany"}), tmp_path / "a.pdf", set())  # zmiany w dokumencie
    with pytest.raises(ValueError, match="nieznane"):
        render_pdf(_bogaty(), tmp_path / "a.pdf", {"zmiany"})


def test_przytnij_pdf_usuwa_zmiany():
    d = przytnij_pdf(_bogaty(), WSZYSTKIE)
    assert not any(e.rodzaj == "zmiany" for e in d.elementy)
    assert any(e.rodzaj == "komentarz" for e in d.elementy)
    with pytest.raises(ValueError, match="nieznane"):
        przytnij_pdf(_bogaty(), {"zmiany"})


def test_zdjecie_pominiete_bez_bledu(tmp_path):
    render_pdf(przytnij(_bogaty(), set()), tmp_path / "a.pdf", {"zdjecie"})


def test_pdf_otwiera_sie_w_pikepdf_i_pdfium(tmp_path):
    plik = tmp_path / "a.pdf"
    render_pdf(przytnij(_dlugi(), WSZYSTKIE), plik, WSZYSTKIE)
    with pikepdf.open(plik) as pdf:
        assert len(pdf.pages) >= 3
    assert len(pdfium.PdfDocument(str(plik))) >= 3


def test_czcionki_osadzone_i_znaki_diakrytyczne(tmp_path):
    d = przytnij(_bogaty(), set())
    d.elementy.append(Element("akapit", ["Zażółć gęślą jaźń ÄÖÜ ß ñ ¿ é à ç œ"]))
    plik = tmp_path / "a.pdf"
    render_pdf(d, plik, set())
    assert "Zażółć gęślą jaźń ÄÖÜ ß ñ ¿ é à ç œ" in _tekst(plik)
    with pikepdf.open(plik) as pdf:
        for p in pdf.pages:
            for f in p.Resources.Font.values():
                assert "/FontFile2" in f.DescendantFonts[0].FontDescriptor or "/FontFile2" in f.FontDescriptor \
                    if "/DescendantFonts" in f else True


# ----------------------------------------------------------------------------- skan
def _skan(tmp_path, d=None, ziarno=1, nazwa="s.pdf", utr=None):
    plik = tmp_path / nazwa
    wynik = renderuj_skan(d if d is not None else przytnij(_dlugi(), UTRUDNIENIA_SKAN), plik, random.Random(ziarno),
                          utr)
    return plik, wynik


def test_skan_bez_warstwy_tekstu(tmp_path):
    plik, _ = _skan(tmp_path)
    assert all(not t.strip() for t in _tekst_stron(plik))
    with pikepdf.open(plik) as pdf:
        assert len(pdf.pages) >= 3
        for p in pdf.pages:
            assert "/Font" not in p.Resources
            assert len(p.get_images()) == 1
            assert "DCTDecode" in str(list(p.get_images().values())[0].Filter)
            assert "/Annots" not in p
        assert "/AcroForm" not in pdf.Root


def test_skan_wartosci_obraz_i_ramki(tmp_path):
    plik, wynik = _skan(tmp_path)
    assert wynik.wartosci and all(w.miejsce == "obraz" for w in wynik.wartosci)
    ids = {w.id for w in wynik.wartosci}
    pdf = pdfium.PdfDocument(str(plik))
    try:
        assert len(wynik.obrazy) == len(pdf)
        for ob, strona in zip(wynik.obrazy, [pdf[i] for i in range(len(pdf))]):
            bm = strona.render(scale=200 / 72)
            for wid, (x0, y0, x1, y1) in ob.ramki:
                assert wid in ids and 0 <= x0 < x1 <= bm.width and 0 <= y0 < y1 <= bm.height
            assert {w.id for w in ob.wartosci} <= ids and {i for i, _ in ob.ramki} <= {w.id for w in ob.wartosci}
    finally:
        pdf.close()
    zrodlo = przytnij(_dlugi(), UTRUDNIENIA_SKAN)
    # każda wartość tekstowa dokumentu ma co najmniej jedną ramkę
    ramkowane = {wid for ob in wynik.obrazy for wid, _ in ob.ramki}
    assert {w.id for w in wynik.wartosci} <= ramkowane
    assert {w.id for e in zrodlo.elementy for w in e.fragmenty if isinstance(w, Wartosc)} <= ids


def test_skan_render_skan_zwraca_liste(tmp_path):
    w = render_skan(przytnij(_bogaty(), UTRUDNIENIA_SKAN), tmp_path / "s.pdf", random.Random(2))
    assert isinstance(w, list) and w and all(isinstance(x, Wartosc) and x.miejsce == "obraz" for x in w)


def test_skan_metadane_neutralne(tmp_path):
    d = _bogaty()  # z autorem w metadanych – skan ich nie niesie
    plik, wynik = _skan(tmp_path, d)
    info, xmp = _info_xmp(plik)
    wszystko = " ".join(info.values()) + xmp
    assert "Wójcik" not in wszystko and "/Author" not in info
    assert "Scanner" in wszystko
    assert not any(w.tekst == "Marek Wójcik" for w in wynik.wartosci)
    assert all(w.miejsce == "obraz" for w in wynik.wartosci)


def test_skan_ignoruje_komentarze_pola_i_metadane(tmp_path):
    plik, wynik = _skan(tmp_path, _bogaty())
    assert not any(w.tekst == "Piotr Nowak" for w in wynik.wartosci)  # komentarz bez odpowiednika w skanie
    assert any(w.tekst == "anna@example.com" for w in wynik.wartosci)  # pole spłaszczone do akapitu – widoczne
    assert not _adnotacje(plik) and not _pola(plik)


def test_skan_nieznane_utrudnienie(tmp_path):
    with pytest.raises(ValueError, match="nieznane"):
        renderuj_skan(_bogaty(), tmp_path / "s.pdf", random.Random(1), {"komentarze"})


def test_skan_deterministyczny(tmp_path):
    a, wa = _skan(tmp_path, ziarno=5, nazwa="a.pdf")
    b, wb = _skan(tmp_path, ziarno=5, nazwa="b.pdf")
    assert a.read_bytes() == b.read_bytes() and wa.wartosci == wb.wartosci and wa.obrazy == wb.obrazy
    c, _ = _skan(tmp_path, ziarno=6, nazwa="c.pdf")
    assert c.read_bytes() != a.read_bytes()


def test_skan_szum_i_obrot(tmp_path):
    plik, _ = _skan(tmp_path, ziarno=3)
    pdf = pdfium.PdfDocument(str(plik))
    try:
        obraz = pdf[0].render(scale=1).to_pil().convert("L")
    finally:
        pdf.close()
    px = list(obraz.getdata())
    biale = [p for p in px if p > 200]
    assert len(set(biale)) > 20  # tło nie jest jednolicie białe (szum, niejednorodność jasności)


def _pod_ramka(strona, ramka: tuple[float, float, float, float]) -> str:
    """Znaki niebiałe, których środek leży w ramce (pt), w kolejności od lewej – to, co ramka faktycznie obejmuje."""
    tp = strona.get_textpage()
    tekst = tp.get_text_range()
    znaki = []
    for i, c in enumerate(tekst):
        if c.isspace() or ord(c) < 32:
            continue
        l, b, r, t = tp.get_charbox(i)
        if ramka[0] <= (l + r) / 2 <= ramka[2] and ramka[1] <= (b + t) / 2 <= ramka[3]:
            znaki.append((l, c))
    return "".join(c for _, c in sorted(znaki))


def _dokument_zlosliwy() -> Dokument:
    def w(i, t, k="MIEJSCOWOSC"):
        return Wartosc(i, k, t, "pl", "tresc", k)
    return Dokument("zlosliwy", "pl", "umowa", "pdf", [
        Element("akapit", ["Sąd w Warszawa i jeszcze Warszawa oraz 12 oraz 1234 oraz ", w("a.miasto#1", "Warszawa"),
                           ". Numer 12: ", w("a.nr#1", "12", "NR_ID")]),
        Element("akapit", ["Początek ", w("a.dlugie#1", " ".join(f"Imię{i}ąęł" for i in range(30)), "OSOBA"), " koniec."]),
    ], {})


def test_ramki_geometria_z_rysowania_a_nie_z_wyszukiwania():
    """Zwykły tekst o tym samym brzmieniu i podciąg dłuższego słowa nie zajmują ramki wartości."""
    bajty, wp = zbuduj_pdf(_dokument_zlosliwy(), set(), geometria=True)
    strona = pdfium.PdfDocument(bajty)[0]
    wys = strona.get_height()
    po_id = {}
    for w, nr, r in wp.ramki:
        po_id.setdefault(w.id, []).append(r)
    assert set(po_id) == {"a.miasto#1", "a.nr#1", "a.dlugie#1"}
    for wid, tekst in (("a.miasto#1", "Warszawa"), ("a.nr#1", "12")):
        assert len(po_id[wid]) == 1
        assert _pod_ramka(strona, po_id[wid][0]) == tekst, wid
    # ramka leży na OSTATNIM wystąpieniu w swoim wierszu (pozostałe są zwykłym tekstem po lewej)
    tp = strona.get_textpage()
    tekst = tp.get_text_range()
    for wid, tekst_w in (("a.miasto#1", "Warszawa"), ("a.nr#1", "12")):
        x0 = po_id[wid][0][0]
        wczesniejsze = [tp.get_charbox(i)[0] for i in range(len(tekst)) if tekst.startswith(tekst_w, i)]
        assert x0 >= max(wczesniejsze) - 2.0, (wid, x0, wczesniejsze)
    # wartość złamana na dwa wiersze: po jednej ramce na wiersz, razem obejmują całą wartość
    dlugie = po_id["a.dlugie#1"]
    assert len(dlugie) >= 2 and len({round(r[1]) for r in dlugie}) == len(dlugie)
    oczekiwane = "".join(f"Imię{i}ąęł" for i in range(30))
    assert "".join(_pod_ramka(strona, r) for r in sorted(dlugie, key=lambda r: -r[1])) == oczekiwane
    assert all(0 <= r[0] < r[2] <= strona.get_width() and 0 <= r[1] < r[3] <= wys for r in dlugie)


def test_skan_zlosliwy_ramki_w_pikselach(tmp_path):
    plik = tmp_path / "z.pdf"
    wynik = renderuj_skan(_dokument_zlosliwy(), plik, random.Random(4))
    assert not wynik.nieznalezione
    ramki = {wid: [b for wid2, b in wynik.obrazy[0].ramki if wid2 == wid] for wid in ("a.miasto#1", "a.nr#1")}
    assert all(len(v) == 1 for v in ramki.values())
    # „Warszawa” (wartość) leży na prawo od zwykłego „Warszawa” w tym samym wierszu
    assert ramki["a.miasto#1"][0][0] > 700 and ramki["a.nr#1"][0][0] > 300


def test_skan_strony_bez_zalegajacych_czcionek(tmp_path):
    plik, _ = _skan(tmp_path)
    with pikepdf.open(plik) as pdf:
        for p in pdf.pages:
            operatory = [str(op) for _, op in pikepdf.parse_content_stream(p)]
            assert "Tf" not in operatory and "BT" not in operatory
            assert "/Font" not in p.Resources


def test_pole_dv_rowne_v_i_wyglad_z_dejavu(tmp_path):
    d = przytnij(_bogaty(), {"pola"})
    for e in d.elementy:
        if e.rodzaj == "pole":
            e.fragmenty = [Wartosc("klient.pelne#9", "OSOBA", "Zażółć Gęślą Jaźń", "pl", "pole", "OSOBA")]
    plik = tmp_path / "a.pdf"
    render_pdf(d, plik, {"pola"})
    with pikepdf.open(plik) as pdf:
        f = pdf.Root.AcroForm.Fields[0]
        assert str(f.V) == str(f.DV) == "Zażółć Gęślą Jaźń"
        font = f.AP.N.Resources.Font.F0
        assert font.Subtype == "/Type0" and "/FontFile2" in font.DescendantFonts[0].FontDescriptor
        assert "Zazolc" not in f.AP.N.read_bytes().decode("latin-1")  # brak zdegradowanej kopii wartości
    # wygląd rastruje się z polskimi znakami (pdfium renderuje widgety)
    strona = pdfium.PdfDocument(str(plik))[0]
    assert strona.render(scale=1, may_draw_forms=True) is not None


def test_obrot_punktu_zgodny_z_pil():
    from pbench.render.skan import obroc_punkt
    for kat in (-1.5, -0.7, 0.9, 1.5):
        w, h = 400, 300
        img = Image.new("L", (w, h), 0)
        img.putpixel((300, 80), 255)
        obr = img.rotate(kat, resample=Image.BICUBIC, center=(w / 2, h / 2))
        px = [(i % w, i // w, v) for i, v in enumerate(obr.getdata())]
        suma = sum(v for *_, v in px)
        cx = sum(x * v for x, _, v in px) / suma
        cy = sum(y * v for _, y, v in px) / suma
        x, y = obroc_punkt(300, 80, kat, w, h)
        assert math.hypot(cx - x, cy - y) < 1.0, (kat, (cx, cy), (x, y))


OCR_JEZYKI = [("pl", "umowa"), ("en", "faktura"), ("de", "cv"), ("fr", "email"), ("es", "odpis_rejestru")]


def _wymagaj_ocr(jezyk: str) -> None:
    if not ocr.dostepny(jezyk):
        pytest.skip(f"brak danych tessdata dla języka {jezyk} (vendor/tessdata)")


def _ocr_strony(plik: Path, jezyk: str) -> list[tuple[Image.Image, str]]:
    pdf = pdfium.PdfDocument(str(plik))
    try:
        obrazy = [pdf[i].render(scale=200 / 72).to_pil().convert("RGB") for i in range(len(pdf))]
    finally:
        pdf.close()
    return [(im, ocr.ocr_obraz(im, jezyk)) for im in obrazy]


def _odzyskana(szukana: str, tekst: str, prog: float = 0.85) -> bool:
    """Wartość odzyskana z OCR: dokładnie albo z drobnymi błędami znaków (`&`->`6`, `@`->`©`) – podobieństwo okna."""
    if szukana in tekst:
        return True
    n = len(szukana)
    return any(difflib.SequenceMatcher(None, szukana, tekst[i:i + n], autojunk=False).ratio() >= prog
               for i in range(max(1, len(tekst) - n + 1)))


def test_skan_ocr_odzyskuje_wiekszosc(tmp_path):
    """Kontrola jakości skanu (nie miara): Tesseract na skanie PL odzyskuje co najmniej 90% wartości."""
    _wymagaj_ocr("pl")
    d = przytnij(_szablonowy("pl", "umowa", 1), UTRUDNIENIA_SKAN)
    plik, wynik = _skan(tmp_path, d, ziarno=1)
    tekst = _bez_spacji(" ".join(t for _, t in _ocr_strony(plik, "pl"))).casefold()
    wartosci = [w for w in wynik.wartosci if len(_bez_spacji(w.tekst)) >= 3]
    odzyskane = sum(_odzyskana(_bez_spacji(w.tekst).casefold(), tekst) for w in wartosci)
    assert wartosci and odzyskane / len(wartosci) >= 0.90, (odzyskane, len(wartosci))


@pytest.mark.parametrize("jezyk,typ", OCR_JEZYKI)
def test_skan_ramki_trafiaja_w_tekst(tmp_path, jezyk, typ):
    """OCR wycinka ramki zawiera wartość dla co najmniej 80% ramek (ramki liczone w pikselach strony)."""
    _wymagaj_ocr(jezyk)
    d = przytnij(_szablonowy(jezyk, typ, 1), UTRUDNIENIA_SKAN)
    plik, wynik = _skan(tmp_path, d, ziarno=2)
    teksty = {(w.id, w.tekst) for w in wynik.wartosci}
    pdf = pdfium.PdfDocument(str(plik))
    try:
        obrazy = [pdf[i].render(scale=200 / 72).to_pil().convert("RGB") for i in range(len(pdf))]
    finally:
        pdf.close()
    # tekst wartości wg id (części wartości mają ten sam id – porównujemy z dowolną częścią)
    po_id: dict[str, list[str]] = {}
    for wid, t in teksty:
        po_id.setdefault(wid, []).append(_bez_spacji(t).casefold())
    ok = razem = 0
    for ob, im in zip(wynik.obrazy, obrazy):
        for wid, (x0, y0, x1, y1) in list(ob.ramki)[:25]:
            if wid.endswith("@obraz"):
                continue  # logo i podpis – inne czcionki, osobny poziom
            if len(_bez_spacji(po_id[wid][0])) < 3:
                continue
            wycinek = im.crop((max(0, x0 - 1), max(0, y0 - 1), min(im.width, x1 + 1), min(im.height, y1 + 1)))
            tekst = _bez_spacji(ocr.ocr_obraz(wycinek, jezyk, psm=7)).casefold()
            razem += 1
            ok += len(tekst) >= 2 and any(_odzyskana(t, tekst) or t in tekst or tekst in t for t in po_id[wid])
    assert razem >= 5 and ok / razem >= 0.80, (ok, razem)


def test_tessdata_dir():
    p = ocr.tessdata_dir()
    assert isinstance(p, Path)
    assert ocr.dostepny("pl") or not (p / "pol.traineddata").exists()
