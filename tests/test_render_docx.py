"""Testy renderera DOCX: wartości w częściach ZIP, rozbite runy, przycinanie utrudnień, gold obrazów."""
from __future__ import annotations

import io
import random
import zipfile
from collections import Counter
from pathlib import Path

import pytest
from docx import Document as DocxDocument
from lxml import etree
from PIL import Image

from pbench.budowa import zbuduj
from pbench.dane import Generator
from pbench.linearyzacja import linearyzuj_z_wartosciami
from pbench.model import Dokument, Element, Obraz, Wartosc
from pbench.render import logo
from pbench.render.docx import render_docx, renderuj_docx
from pbench.szablony import SZABLONY
from pbench.utrudnienia import UTRUDNIENIA_DOCX, przytnij

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
WSZYSTKIE = set(UTRUDNIENIA_DOCX)


def _w(i: str, tekst: str, kat: str = "OSOBA", miejsce: str = "tresc") -> Wartosc:
    return Wartosc(i, kat, tekst, "pl", miejsce, kat)


def _bogaty() -> Dokument:
    """Dokument ręczny ze wszystkimi rodzajami elementów (szablony produkują komentarze/pola tylko częściowo)."""
    firma = _w("kancelaria.nazwa#1", "Zielińscy i Wspólnicy Kancelaria Prawna", "ORGANIZACJA", "naglowek")
    el = [
        Element("naglowek", [firma]),
        Element("naglowek", [_w("kancelaria.adres#1", "ul. Prusa 12, 00-950 Warszawa", "ADRES", "naglowek"),
                             " | NIP ", _w("kancelaria.nip#1", "5252525252", "NIP", "naglowek")]),
        Element("akapit", ["UMOWA TESTOWA"]),
        Element("akapit", ["Zawarta w dniu ", _w("ctx.data#1", "15 grudnia 2022 r.", "DATA"), " pomiędzy ",
                           _w("klient.pelne#1", "Anna Kowalska", "OSOBA"), " a firmą."]),
        Element("komorka", ["Lp."], {"tabela": 0, "wiersz": 0, "kolumna": 0}),
        Element("komorka", ["PESEL"], {"tabela": 0, "wiersz": 0, "kolumna": 1}),
        Element("komorka", ["1"], {"tabela": 0, "wiersz": 1, "kolumna": 0}),
        Element("komorka", [_w("klient.pesel#1", "44051401359", "PESEL", "tabela")],
                {"tabela": 0, "wiersz": 1, "kolumna": 1}),
        Element("akapit", ["Drugi akapit z telefonem ", _w("klient.telefon#1", "600 100 200", "TELEFON"), "."]),
        Element("pole", [_w("klient.email#1", "anna@example.com", "EMAIL", "pole")], {"etykieta": "E-mail klienta"}),
        Element("przypis", ["Zob. ", _w("sprawa.sygnatura#1", "I C 123/21", "SYGNATURA", "przypis"), "."]),
        Element("komentarz", [_w("kolega.pelne#1", "Piotr Nowak", "OSOBA", "komentarz"), ": ", "Do sprawdzenia."],
                {"autor_fragment": 0}),
        Element("zmiany", [_w("kolega.pelne#2", "Ewa Lis", "OSOBA", "zmiany"), ": ", "Dodano zdanie."],
                {"autor_fragment": 0, "typ": "ins"}),
        Element("zmiany", [_w("kolega.pelne#3", "Jan Mazur", "OSOBA", "zmiany"), ": ", "Usunięto zapis."],
                {"autor_fragment": 0, "typ": "del"}),
        Element("podpis", [_w("klient.pelne#2", "Anna Kowalska", "OSOBA", "tresc")]),
        Element("stopka", [_w("kancelaria.nazwa#2", "Zielińscy i Wspólnicy Kancelaria Prawna", "ORGANIZACJA",
                              "stopka"), ", KRS ", _w("kancelaria.krs#1", "0000123456", "KRS", "stopka")]),
    ]
    meta = {"author": _w("autor.pelne#1", "Marek Wójcik", "OSOBA", "metadane"), "title": "Umowa testowa",
            "subject": "Test"}
    return Dokument("test-bogaty", "pl", "umowa", "docx", el, meta)


def _szablonowy(jezyk: str, typ: str, ziarno: int = 1) -> Dokument:
    return zbuduj(SZABLONY[(jezyk, typ)], Generator(jezyk, ziarno), random.Random(ziarno))


def _tekst_czesci(zf: zipfile.ZipFile, nazwa: str) -> str:
    """Tekst części: akapity ze sklejonych w:t/w:delText + wartości wszystkich atrybutów + tekst innych elementów."""
    root = etree.fromstring(zf.read(nazwa))
    akapity = ["".join(t.text or "" for t in p.iter(f"{{{W}}}t", f"{{{W}}}delText")) for p in root.iter(f"{{{W}}}p")]
    atrybuty = [v for e in root.iter() for v in e.attrib.values()]
    inne = [t for t in root.itertext()]
    return "\n".join(akapity + atrybuty + inne)


CZESCI = {"tresc": ["word/document.xml"], "tabela": ["word/document.xml"], "pole": ["word/document.xml"],
          "zmiany": ["word/document.xml"], "naglowek": ["word/header"], "stopka": ["word/footer"],
          "przypis": ["word/footnotes.xml"], "komentarz": ["word/comments.xml"],
          "metadane": ["docProps/core.xml", "docProps/custom.xml"]}


def _teksty_miejsc(zf: zipfile.ZipFile) -> dict[str, str]:
    """Złączony tekst części ZIP dla każdego miejsca (liczony raz – listy płac mają tysiące wartości)."""
    return {m: "\n".join(_tekst_czesci(zf, n) for n in _czesci(zf, m)) for m in CZESCI}


def _czesci(zf: zipfile.ZipFile, miejsce: str) -> list[str]:
    return [n for n in zf.namelist() for p in CZESCI[miejsce] if n.startswith(p) and n.endswith(".xml")]


# ----------------------------------------------------------------------------- brief
@pytest.mark.parametrize("utrudnienia", [set(), WSZYSTKIE, {"papier_firmowy", "tabele"}, {"rozbite_runy", "metadane"}])
def test_wartosci_w_xml_bogaty(tmp_path, utrudnienia):
    d = przytnij(_bogaty(), utrudnienia)
    plik = tmp_path / "a.docx"
    wartosci = render_docx(d, plik, utrudnienia)
    assert wartosci
    with zipfile.ZipFile(plik) as zf:
        teksty = _teksty_miejsc(zf)
        for w in wartosci:
            if w.miejsce == "obraz":
                continue
            assert w.tekst in teksty[w.miejsce], (w.id, w.tekst, w.miejsce)


@pytest.mark.parametrize("jezyk,typ", [("pl", "umowa"), ("pl", "notatka"), ("pl", "lista_plac"), ("en", "faktura"),
                                       ("de", "cv"), ("fr", "email"), ("es", "odpis_rejestru"),
                                       ("pl", "pelnomocnictwo"), ("en", "pelnomocnictwo")])
@pytest.mark.parametrize("ziarno", [1, 2])
def test_wartosci_w_xml_szablony(tmp_path, jezyk, typ, ziarno):
    d = przytnij(_szablonowy(jezyk, typ, ziarno), WSZYSTKIE)
    plik = tmp_path / "a.docx"
    wartosci = render_docx(d, plik, WSZYSTKIE)
    with zipfile.ZipFile(plik) as zf:
        teksty = _teksty_miejsc(zf)
        for w in wartosci:
            if w.miejsce == "obraz":
                continue
            assert w.tekst in teksty[w.miejsce], (w.id, w.tekst, w.miejsce)


def _rozbite(plik: Path, wartosci: list[Wartosc]) -> tuple[int, int, list[etree._Element], etree._Element]:
    """(wartości w treści, ile rozbitych, akapity z rozbitą wartością, korzeń document.xml)."""
    with zipfile.ZipFile(plik) as zf:
        root = etree.fromstring(zf.read("word/document.xml"))
    akapity = [[t.text or "" for t in p.iter(f"{{{W}}}t")] for p in root.iter(f"{{{W}}}p")]
    razem = rozbite = 0
    for w in wartosci:
        if w.miejsce not in ("tresc", "tabela", "pole") or len(w.tekst) < 2:
            continue
        razem += 1
        for ts in akapity:
            if w.tekst in "".join(ts):
                if not any(w.tekst in t for t in ts):
                    rozbite += 1
                break
        else:
            pytest.fail(f"brak wartości {w.tekst!r}")
    return razem, rozbite, akapity, root


def test_rozbite_runy_w_osobnych_w_t(tmp_path):
    """Rozbita wartość nie leży w żadnym pojedynczym w:t, a sklejone w:t akapitu ją zawierają."""
    razem = rozbite = 0
    for i in range(20):
        d = _bogaty()
        d.id = f"doc-{i}"
        plik = tmp_path / "a.docx"
        r, b, _, _ = _rozbite(plik, render_docx(d, plik, {"rozbite_runy"}))
        razem, rozbite = razem + r, rozbite + b
    assert rozbite >= 5


def test_rozbite_runy_mniejszosc(tmp_path):
    """Rozbite wartości to mniejszość (15–40%) – podział nie jest znacznikiem danych osobowych."""
    razem = rozbite = 0
    for i in range(20):
        d = _bogaty()
        d.id = f"doc-{i}"
        plik = tmp_path / "a.docx"
        r, b, _, _ = _rozbite(plik, render_docx(d, plik, {"rozbite_runy"}))
        razem, rozbite = razem + r, rozbite + b
    assert 0.15 <= rozbite / razem <= 0.40, (rozbite, razem)


def test_rozbite_runy_dzielone_tez_zwykle_slowa(tmp_path):
    """Część zwykłych słów (nie wartości) też jest rozbita na runy."""
    pociete = 0
    for i in range(20):
        d = _bogaty()
        d.id = f"doc-{i}"
        plik = tmp_path / "a.docx"
        wartosci = render_docx(d, plik, {"rozbite_runy"})
        _, _, akapity, _ = _rozbite(plik, wartosci)
        slowa = {"Zawarta", "pomiędzy", "Drugi", "akapit", "telefonem", "firmą"}
        for ts in akapity:
            razem = "".join(ts)
            for sl in slowa:
                if sl in razem and not any(sl in t for t in ts):
                    pociete += 1
    assert pociete >= 3


def test_rozbite_runy_niewidoczne(tmp_path):
    """Kawałki rozbitej wartości mają identyczne rPr (nie widać ich w dokumencie); różni je tylko rsid."""
    sprawdzone = 0
    for i in range(10):
        d = _bogaty()
        d.id = f"doc-{i}"
        plik = tmp_path / "a.docx"
        wartosci = render_docx(d, plik, {"rozbite_runy"})
        with zipfile.ZipFile(plik) as zf:
            root = etree.fromstring(zf.read("word/document.xml"))
            settings = etree.fromstring(zf.read("word/settings.xml"))
        rsids_ustawien = {e.get(f"{{{W}}}val") for e in settings.iter(f"{{{W}}}rsid")}
        for p in root.iter(f"{{{W}}}p"):
            runy = [r for r in p.findall("w:r", NS) if r.find("w:t", NS) is not None]
            ts = [r.find("w:t", NS).text or "" for r in runy]
            sklejone = "".join(ts)
            for w in wartosci:
                if w.miejsce != "tresc" or len(w.tekst) < 2 or w.tekst not in sklejone or any(w.tekst in t for t in ts):
                    continue
                start, pos, kawalki = sklejone.index(w.tekst), 0, []
                for r, t in zip(runy, ts):
                    if pos < start + len(w.tekst) and pos + len(t) > start:
                        kawalki.append(r)
                    pos += len(t)
                rpry = {etree.tostring(r.find("w:rPr", NS)) if r.find("w:rPr", NS) is not None else b"" for r in kawalki}
                assert len(rpry) == 1, w.tekst
                rs = [r.get(f"{{{W}}}rsidR") for r in kawalki]
                assert all(rs) and len(set(rs)) >= 2 and set(rs) <= rsids_ustawien
                sprawdzone += 1
    assert sprawdzone >= 3


def test_rozbite_runy_brak_bez_utrudnienia(tmp_path):
    plik = tmp_path / "a.docx"
    render_docx(_bogaty(), plik, set())
    with zipfile.ZipFile(plik) as zf:
        root = etree.fromstring(zf.read("word/document.xml"))
    assert any("Anna Kowalska" in (t.text or "") for t in root.iter(f"{{{W}}}t"))


def test_docx_otwiera_python_docx(tmp_path):
    plik = tmp_path / "a.docx"
    render_docx(przytnij(_bogaty(), WSZYSTKIE), plik, WSZYSTKIE)
    doc = DocxDocument(str(plik))
    tekst = "\n".join(p.text for p in doc.paragraphs)
    assert "UMOWA TESTOWA" in tekst
    assert len(doc.tables) == 1 and doc.tables[0].cell(1, 1).text == "44051401359"
    assert doc.core_properties.author == "Marek Wójcik"
    assert len(list(doc.comments)) == 1


# ----------------------------------------------------------------------------- utrudnienia
def _zip(tmp_path, d, utrudnienia):
    plik = tmp_path / "a.docx"
    wartosci = render_docx(d, plik, utrudnienia)
    return zipfile.ZipFile(plik), wartosci


def test_papier_firmowy_naglowek_stopka_i_logo(tmp_path):
    zf, wartosci = _zip(tmp_path, _bogaty(), {"papier_firmowy"})
    assert any(n.startswith("word/header") for n in zf.namelist())
    assert any(n.startswith("word/footer") for n in zf.namelist())
    assert any(n.startswith("word/media/") for n in zf.namelist())
    assert "Prusa 12" in "".join(_tekst_czesci(zf, n) for n in _czesci(zf, "naglowek"))
    assert "Prusa 12" not in _tekst_czesci(zf, "word/document.xml")
    assert {w.miejsce for w in wartosci if w.kategoria == "NIP"} == {"naglowek"}
    assert any(w.miejsce == "obraz" and w.kategoria == "ORGANIZACJA" for w in wartosci)
    assert "PAGE" in "".join(_tekst_czesci(zf, n) for n in _czesci(zf, "stopka")) or \
        b"PAGE" in b"".join(zf.read(n) for n in _czesci(zf, "stopka"))


def test_bez_papieru_naglowek_idzie_do_tresci(tmp_path):
    zf, wartosci = _zip(tmp_path, _bogaty(), set())
    assert not any(n.startswith("word/header") for n in zf.namelist())
    assert "Prusa 12" in _tekst_czesci(zf, "word/document.xml")
    assert {w.miejsce for w in wartosci if w.kategoria in ("NIP", "KRS")} == {"tresc"}
    assert not any(w.miejsce == "obraz" for w in wartosci)


def test_tabele_obramowanie(tmp_path):
    zf, _ = _zip(tmp_path, _bogaty(), {"tabele"})
    root = etree.fromstring(zf.read("word/document.xml"))
    assert len(root.findall(".//w:tbl", NS)) == 1
    assert root.find(".//w:tbl/w:tblPr/w:tblBorders", NS) is not None or \
        root.find(".//w:tbl/w:tblPr/w:tblStyle", NS) is not None


def test_przypisy_footnotes_xml(tmp_path):
    zf, wartosci = _zip(tmp_path, _bogaty(), {"przypisy"})
    root = etree.fromstring(zf.read("word/footnotes.xml"))
    ids = [f.get(f"{{{W}}}id") for f in root.findall("w:footnote", NS)]
    assert "1" in ids
    doc = etree.fromstring(zf.read("word/document.xml"))
    assert doc.find(".//w:footnoteReference", NS).get(f"{{{W}}}id") == "1"
    assert "I C 123/21" in _tekst_czesci(zf, "word/footnotes.xml")


def test_komentarze_autor_i_data(tmp_path):
    zf, _ = _zip(tmp_path, _bogaty(), {"komentarze"})
    root = etree.fromstring(zf.read("word/comments.xml"))
    c = root.find("w:comment", NS)
    assert c.get(f"{{{W}}}author") == "Piotr Nowak" and c.get(f"{{{W}}}date")
    doc = etree.fromstring(zf.read("word/document.xml"))
    assert doc.find(".//w:commentRangeStart", NS) is not None and doc.find(".//w:commentReference", NS) is not None


def test_zmiany_ins_del(tmp_path):
    zf, _ = _zip(tmp_path, _bogaty(), {"zmiany"})
    doc = etree.fromstring(zf.read("word/document.xml"))
    ins, dele = doc.find(".//w:ins", NS), doc.find(".//w:del", NS)
    assert ins.get(f"{{{W}}}author") == "Ewa Lis" and ins.get(f"{{{W}}}date")
    assert dele.get(f"{{{W}}}author") == "Jan Mazur"
    assert "Usunięto zapis." in "".join(t.text for t in dele.iter(f"{{{W}}}delText"))
    assert "Dodano zdanie." in "".join(t.text for t in ins.iter(f"{{{W}}}t"))
    assert doc.find(".//w:ins//w:delText", NS) is None


def test_pola_content_control(tmp_path):
    zf, _ = _zip(tmp_path, _bogaty(), {"pola"})
    doc = etree.fromstring(zf.read("word/document.xml"))
    sdt = doc.find(".//w:sdt", NS)
    assert sdt is not None
    assert sdt.find("w:sdtPr/w:alias", NS).get(f"{{{W}}}val") == "E-mail klienta"
    assert "anna@example.com" in "".join(t.text for t in sdt.find("w:sdtContent", NS).iter(f"{{{W}}}t"))


def test_metadane_core_xml(tmp_path):
    zf, wartosci = _zip(tmp_path, _bogaty(), {"metadane"})
    core = etree.fromstring(zf.read("docProps/core.xml")).itertext()
    tekst = "|".join(core)
    assert "Marek Wójcik" in tekst and "Umowa testowa" in tekst
    root = etree.fromstring(zf.read("docProps/core.xml"))
    ln = [e for e in root.iter() if e.tag.endswith("lastModifiedBy")]
    assert ln and ln[0].text == "Marek Wójcik"
    assert any(w.miejsce == "metadane" and w.tekst == "Marek Wójcik" for w in wartosci)


def test_podpis_obraz_i_gold(tmp_path):
    plik = tmp_path / "a.docx"
    w = renderuj_docx(_bogaty(), plik, {"podpis"})
    assert len(w.obrazy) == 1
    ob = w.obrazy[0]
    assert isinstance(ob, Obraz) and ob.png and len(ob.wartosci) == 1 and len(ob.ramki) == 1
    wart = ob.wartosci[0]
    assert (wart.kategoria, wart.tekst, wart.miejsce) == ("OSOBA", "Anna Kowalska", "obraz")
    assert ob.ramki[0][0] == wart.id
    img = Image.open(io.BytesIO(ob.png))
    x0, y0, x1, y1 = ob.ramki[0][1]
    assert 0 <= x0 < x1 <= img.width and 0 <= y0 < y1 <= img.height
    with zipfile.ZipFile(plik) as zf:
        assert any(n.startswith("word/media/") for n in zf.namelist())
        assert "Anna Kowalska" in _tekst_czesci(zf, "word/document.xml")  # nazwisko tekstem pod linią
    assert wart in w.wartosci and wart.id in {x.id for x in w.wartosci if x.miejsce == "obraz"}


def test_bez_podpisu_tylko_tekst(tmp_path):
    zf, wartosci = _zip(tmp_path, _bogaty(), set())
    assert not any(n.startswith("word/media/") for n in zf.namelist())
    assert not any(w.miejsce == "obraz" for w in wartosci)


def test_logo_generuj_i_ramka():
    rng = random.Random(3)
    img = logo.generuj("Zielińscy i Wspólnicy Kancelaria Prawna", rng)
    assert isinstance(img, Image.Image) and img.width > 100
    img2, bbox = logo.generuj_z_ramka("Zielińscy i Wspólnicy Kancelaria Prawna", random.Random(3))
    assert img2.tobytes() == img.tobytes()  # deterministyczne dla ziarna
    assert 0 <= bbox[0] < bbox[2] <= img2.width and 0 <= bbox[1] < bbox[3] <= img2.height


def test_nieznane_utrudnienie(tmp_path):
    with pytest.raises(ValueError, match="nieznane"):
        render_docx(_bogaty(), tmp_path / "a.docx", {"zdjecie_xyz"})


def test_zdjecie_pominiete_bez_bledu(tmp_path):
    render_docx(_bogaty(), tmp_path / "a.docx", {"zdjecie"})


def test_deterministyczny(tmp_path):
    a, b = tmp_path / "a.docx", tmp_path / "b.docx"
    wa = render_docx(przytnij(_bogaty(), WSZYSTKIE), a, WSZYSTKIE)
    wb = render_docx(przytnij(_bogaty(), WSZYSTKIE), b, WSZYSTKIE)
    assert wa == wb
    with zipfile.ZipFile(a) as za, zipfile.ZipFile(b) as zb:
        assert sorted(za.namelist()) == sorted(zb.namelist())
        for n in za.namelist():
            assert za.read(n) == zb.read(n), n


# ----------------------------------------------------------------------------- przycinanie
def _rodzaje(d: Dokument) -> Counter:
    return Counter(e.rodzaj for e in d.elementy)


def test_przytnij_bez_komentarzy():
    d = przytnij(_bogaty(), WSZYSTKIE - {"komentarze"})
    assert _rodzaje(d)["komentarz"] == 0 and _rodzaje(d)["zmiany"] == 2 and _rodzaje(d)["przypis"] == 1


def test_przytnij_bez_zmian():
    d = przytnij(_bogaty(), WSZYSTKIE - {"zmiany"})
    assert _rodzaje(d)["zmiany"] == 0 and _rodzaje(d)["komentarz"] == 1


def test_przytnij_bez_przypisow():
    assert _rodzaje(przytnij(_bogaty(), WSZYSTKIE - {"przypisy"}))["przypis"] == 0


def test_przytnij_bez_pol():
    d = przytnij(_bogaty(), WSZYSTKIE - {"pola"})
    assert _rodzaje(d)["pole"] == 0
    akapit = next(e for e in d.elementy if any(isinstance(f, Wartosc) and f.kategoria == "EMAIL" for f in e.fragmenty))
    assert akapit.rodzaj == "akapit"
    assert [f.miejsce for f in akapit.fragmenty if isinstance(f, Wartosc)] == ["tresc"]
    assert "E-mail klienta" in "".join(f for f in akapit.fragmenty if isinstance(f, str))


def test_przytnij_bez_tabel():
    d = przytnij(_bogaty(), WSZYSTKIE - {"tabele"})
    assert _rodzaje(d)["komorka"] == 0
    teksty = ["".join(f if isinstance(f, str) else f.tekst for f in e.fragmenty) for e in d.elementy]
    assert "PESEL: 44051401359" in teksty
    pesel = next(f for e in d.elementy for f in e.fragmenty if isinstance(f, Wartosc) and f.kategoria == "PESEL")
    assert pesel.miejsce == "tresc"


def test_przytnij_bez_metadanych():
    d = przytnij(_bogaty(), WSZYSTKIE - {"metadane"})
    assert d.metadane["author"] == "Użytkownik"
    assert not any(isinstance(v, Wartosc) for v in d.metadane.values())
    assert d.metadane["title"] == "Umowa testowa"


def test_przytnij_bez_papieru_zmienia_miejsce():
    d = przytnij(_bogaty(), WSZYSTKIE - {"papier_firmowy"})
    for e in d.elementy:
        if e.rodzaj in ("naglowek", "stopka"):
            assert all(f.miejsce == "tresc" for f in e.fragmenty if isinstance(f, Wartosc))


def test_przytnij_czysty_i_deterministyczny():
    d = _bogaty()
    json_przed = d.to_json()
    a, b = przytnij(d, set()), przytnij(d, set())
    assert d.to_json() == json_przed and a is not d and a.to_json() == b.to_json()
    assert przytnij(d, WSZYSTKIE).to_json() == json_przed  # wszystkie utrudnienia = bez zmian


@pytest.mark.parametrize("jezyk,typ", [("pl", "umowa"), ("pl", "notatka"), ("pl", "lista_plac"), ("en", "faktura"),
                                       ("de", "cv"), ("fr", "email"), ("pl", "pelnomocnictwo")])
@pytest.mark.parametrize("utrudnienia", [set(), {"papier_firmowy"}, {"tabele", "metadane"}, WSZYSTKIE])
def test_linearyzacja_przycietego_zgodna_ze_zwroconymi(tmp_path, jezyk, typ, utrudnienia):
    d = przytnij(_szablonowy(jezyk, typ, 2), utrudnienia)
    wartosci = render_docx(d, tmp_path / "a.docx", utrudnienia)
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
        wartosci = render_docx(d, tmp_path / "a.docx", utr)
        _, _, lin = linearyzuj_z_wartosciami(d)
        assert Counter((w.id, w.tekst, w.miejsce) for w in wartosci if w.miejsce != "obraz") == \
            Counter((w.id, w.tekst, w.miejsce) for w in lin)


def test_email_z_metadanymi_naglowek_widoczny_w_tresci(tmp_path):
    d = przytnij(_szablonowy("fr", "email", 2), WSZYSTKIE)
    plik = tmp_path / "a.docx"
    wartosci = render_docx(d, plik, WSZYSTKIE)
    od = d.metadane["from"]
    assert {w.miejsce for w in wartosci if w.id == od.id} == {"tresc", "metadane"}
    with zipfile.ZipFile(plik) as zf:
        assert od.tekst in _tekst_czesci(zf, "word/document.xml")
        assert od.tekst in _tekst_czesci(zf, "docProps/custom.xml")


def test_inicjaly_komentarza_neutralne(tmp_path):
    zf, _ = _zip(tmp_path, _bogaty(), {"komentarze"})
    c = etree.fromstring(zf.read("word/comments.xml")).find("w:comment", NS)
    assert not c.get(f"{{{W}}}initials")
