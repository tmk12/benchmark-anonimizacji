"""Testy rendererów XLSX, PPTX, EML, MSG i DOC: wartości odczytane niezależną biblioteką, przycinanie `przytnij_dla`,
zgodność z linearyzacją, brak danych poza gold (skan wszystkich części pliku), determinizm."""
from __future__ import annotations

import html
import io
import re
import zipfile
from collections import Counter
from pathlib import Path

import pytest
from test_render_docx import _bogaty, _szablonowy, _w

from pbench.linearyzacja import linearyzuj_z_wartosciami
from pbench.model import Dokument, Element, Wartosc
from pbench.utrudnienia import (UTRUDNIENIA_DOC, UTRUDNIENIA_EML, UTRUDNIENIA_MSG, UTRUDNIENIA_PPTX,
                                UTRUDNIENIA_XLSX, przytnij_dla)

SZABLONY_PRZEKROJOWE = [("pl", "umowa"), ("pl", "notatka"), ("pl", "lista_plac"), ("en", "faktura"), ("de", "cv"),
                        ("fr", "email"), ("es", "odpis_rejestru"), ("pl", "prezentacja"), ("pl", "email")]


def _licz(wartosci, bez_obrazow: bool = True) -> Counter:
    return Counter((w.id, w.tekst, w.miejsce) for w in wartosci if not (bez_obrazow and w.miejsce == "obraz"))


def _oczekiwane(d: Dokument) -> Counter:
    """Wartości linearyzacji przyciętego dokumentu (to, co renderer ma umieścić w pliku)."""
    return _licz(linearyzuj_z_wartosciami(d)[2])


# ----------------------------------------------------------------------------- przytnij_dla
def test_przytnij_dla_nieznany_format_i_utrudnienie():
    with pytest.raises(ValueError):
        przytnij_dla("txt", _bogaty(), set())
    with pytest.raises(ValueError):
        przytnij_dla("xlsx", _bogaty(), {"zmiany"})
    with pytest.raises(ValueError):
        przytnij_dla("eml", _bogaty(), {"tabele"})
    przytnij_dla("xlsx", _bogaty(), {"zdjecie"})  # pominięte utrudnienie nie jest błędem


def test_przytnij_dla_docx_i_pdf_jak_przytnij():
    from pbench.utrudnienia import UTRUDNIENIA_DOCX, UTRUDNIENIA_PDF, przytnij, przytnij_pdf
    d = _bogaty()
    assert przytnij_dla("docx", d, {"tabele", "metadane"}).to_json() == przytnij(d, {"tabele", "metadane"}).to_json()
    assert przytnij_dla("pdf", d, set(UTRUDNIENIA_PDF)).to_json() == przytnij_pdf(d, set(UTRUDNIENIA_PDF)).to_json()
    assert przytnij_dla("doc", d, set(UTRUDNIENIA_DOCX)).to_json() == przytnij(d, set(UTRUDNIENIA_DOCX)).to_json()


def _rodzaje(d: Dokument) -> Counter:
    return Counter(e.rodzaj for e in d.elementy)


def test_przytnij_dla_xlsx_usuwa_przypisy_zmiany_i_splaszcza_pola():
    d = przytnij_dla("xlsx", _bogaty(), set(UTRUDNIENIA_XLSX))
    r = _rodzaje(d)
    assert r["przypis"] == r["zmiany"] == r["pole"] == 0
    assert r["komorka"] == 4 and r["komentarz"] == 1  # tabele wymuszone, komentarze zostają
    assert _rodzaje(przytnij_dla("xlsx", _bogaty(), set()))["komentarz"] == 0


def test_przytnij_dla_xlsx_naglowek_wydruku_i_metadane():
    bez = przytnij_dla("xlsx", _bogaty(), set())
    assert all(f.miejsce == "tresc" for e in bez.elementy if e.rodzaj in ("naglowek", "stopka")
               for f in e.fragmenty if isinstance(f, Wartosc))
    assert bez.metadane["author"] == "Użytkownik"
    z = przytnij_dla("xlsx", _bogaty(), {"naglowek_wydruku", "metadane"})
    assert z.metadane["author"].miejsce == "metadane"
    assert any(f.miejsce == "naglowek" for e in z.elementy if e.rodzaj == "naglowek"
               for f in e.fragmenty if isinstance(f, Wartosc))


def test_przytnij_dla_pptx_mapa():
    d = przytnij_dla("pptx", _bogaty(), {"notatki"})
    assert _rodzaje(d)["przypis"] == 1 and _rodzaje(d)["komentarz"] == 0 and _rodzaje(d)["komorka"] == 0
    d2 = przytnij_dla("pptx", _bogaty(), {"komentarze", "tabele"})
    assert _rodzaje(d2)["przypis"] == 0 and _rodzaje(d2)["komentarz"] == 1 and _rodzaje(d2)["komorka"] == 4


def _email_z_osobami() -> Dokument:
    """E-mail ręczny: nagłówki z osobami (nazwy z diakrytykami), stopka z telefonem."""
    meta = {"from": _w("nadawca.pelne#1", "Żaneta Ćwikła", "OSOBA", "metadane"),
            "to": _w("klient.email#1", "p.dudek@poczta.test", "EMAIL", "metadane"),
            "cc": _w("kolega.pelne#1", "Łukasz Śliwiński", "OSOBA", "metadane"),
            "subject": "Projekt pisma – prośba o uwagi",
            "author": _w("autor.pelne#1", "Marek Wójcik", "OSOBA", "metadane"),
            "case": _w("sprawa.sygnatura#1", "I C 123/21", "SYGNATURA", "metadane")}
    el = [Element("akapit", ["Dzień dobry,"]),
          Element("akapit", ["w sprawie ", _w("sprawa.sygnatura#2", "I C 123/21", "SYGNATURA"), " informuję, że ",
                             _w("klient.pelne#1", "Piotr Żółć", "OSOBA"), " potwierdził termin & miejsce <ok>."]),
          Element("komentarz", [_w("k.pelne#1", "Ewa Lis", "OSOBA", "komentarz"), ": ", "uwaga"],
                  {"autor_fragment": 0}),
          Element("komorka", ["Lp."], {"tabela": 0, "wiersz": 0, "kolumna": 0}),
          Element("komorka", [_w("klient.pesel#1", "44051401359", "PESEL", "tabela")],
                  {"tabela": 0, "wiersz": 1, "kolumna": 0}),
          Element("stopka", [_w("nadawca.pelne#2", "Żaneta Ćwikła", "OSOBA", "stopka"), ", tel. ",
                             _w("nadawca.telefon#1", "+48 600 100 200", "TELEFON", "stopka")]),
          Element("stopka", [_w("kancelaria.nazwa#1", "Kancelaria Ćwikła i Wspólnicy", "ORGANIZACJA", "stopka")])]
    return Dokument("test-email", "pl", "email", "eml", el, meta)


def test_przytnij_dla_eml_zachowuje_naglowki_i_stopke():
    d = przytnij_dla("eml", _email_z_osobami(), set())
    assert d.metadane["from"].miejsce == "metadane" and d.metadane["cc"].miejsce == "metadane"
    assert d.metadane["author"] == "Użytkownik" and "case" not in d.metadane
    assert d.metadane["subject"].startswith("Projekt")
    r = _rodzaje(d)
    assert r["komentarz"] == 0 and r["komorka"] == 0 and r["stopka"] == 2
    assert all(f.miejsce == "stopka" for e in d.elementy if e.rodzaj == "stopka"
               for f in e.fragmenty if isinstance(f, Wartosc))
    z = przytnij_dla("eml", _email_z_osobami(), {"metadane"})
    assert z.metadane["author"].miejsce == "metadane" and z.metadane["case"].miejsce == "metadane"
    assert przytnij_dla("msg", _email_z_osobami(), set()).to_json() == d.to_json()


def test_przytnij_dla_czysty_i_deterministyczny():
    d = _bogaty()
    przed = d.to_json()
    for fmt in ("xlsx", "pptx", "eml", "msg", "doc"):
        a, b = przytnij_dla(fmt, d, set()), przytnij_dla(fmt, d, set())
        assert a.to_json() == b.to_json() and a is not d
    assert d.to_json() == przed


# ----------------------------------------------------------------------------- wspólne asercje
def _czesci_zip(plik: Path) -> dict[str, str]:
    """Wszystkie części ZIP jako tekst (XML po `html.unescape`, by encje nie ukrywały wartości)."""
    with zipfile.ZipFile(plik) as zf:
        return {n: html.unescape(zf.read(n).decode("utf-8", errors="ignore")) for n in zf.namelist()}


def _porownaj_z_linearyzacja(zwrocone, d: Dokument, kopie_metadane: bool = True) -> None:
    """Zwrócone wartości = wartości linearyzacji przyciętego dokumentu (+ kopie „metadane” tej samej wartości)."""
    oczekiwane = _oczekiwane(d)
    z = _licz(zwrocone)
    assert not (oczekiwane - z), oczekiwane - z
    nadmiar = z - oczekiwane
    znane = {(i, t) for (i, t, _m) in oczekiwane}
    for (i, t, m), n in nadmiar.items():
        assert kopie_metadane and m in ("metadane", "tresc", "stopka") and (i, t) in znane, (i, t, m)


def _nie_wyciekaja(pelny: Dokument, zwrocone, czesci: dict[str, str]) -> None:
    """Wartości dokumentu pełnego, których plik NIE ma w gold (przycięte), nie występują w żadnej części pliku."""
    w_gold = {w.tekst for w in zwrocone}
    reszta = {f.tekst for e in pelny.elementy for f in e.fragmenty if isinstance(f, Wartosc)}
    reszta |= {v.tekst for v in pelny.metadane.values() if isinstance(v, Wartosc)}
    for tekst in reszta - w_gold:
        if len(tekst) < 6 or any(tekst in g for g in w_gold):
            continue
        for nazwa, zawartosc in czesci.items():
            assert tekst not in zawartosc, (tekst, nazwa)


# ----------------------------------------------------------------------------- XLSX
from openpyxl import load_workbook  # noqa: E402

from pbench.render.xlsx import render_xlsx  # noqa: E402

WSZYSTKIE_XLSX = set(UTRUDNIENIA_XLSX)
PUSTE_I_PELNE_XLSX = [set(), WSZYSTKIE_XLSX, {"komentarze", "arkusz_ukryty"}, {"naglowek_wydruku", "metadane"},
                      {"nazwy_arkuszy"}]


def _stopka_wydruku(ws, strona: str) -> str:
    hf = ws.oddHeader if strona == "naglowek" else ws.oddFooter
    return "\n".join(x.text.replace("&&", "&") for x in (hf.left, hf.center, hf.right) if x.text)


def _teksty_xlsx(plik: Path) -> dict[str, str]:
    """Złączony tekst skoroszytu wg miejsca (openpyxl, niezależnie od renderera)."""
    wb = load_workbook(plik)
    t: dict[str, list[str]] = {m: [] for m in ("tresc", "tabela", "komentarz", "naglowek", "stopka", "metadane")}
    for ws in wb.worksheets:
        for rzad in ws.iter_rows():
            for c in rzad:
                if isinstance(c.value, str):
                    t["tresc"].append(c.value)
                    t["tabela"].append(c.value)
                if c.comment:
                    t["komentarz"] += [c.comment.author or "", c.comment.text]
        t["naglowek"].append(_stopka_wydruku(ws, "naglowek"))
        t["stopka"].append(_stopka_wydruku(ws, "stopka"))
        t["metadane"].append(ws.title)
    p = wb.properties
    t["metadane"] += [p.creator or "", p.lastModifiedBy or "", p.title or "", p.subject or ""]
    t["metadane"] += [f"{c.name}={c.value}" for c in wb.custom_doc_props.props]
    with zipfile.ZipFile(plik) as zf:
        t["metadane"].append(html.unescape(zf.read("docProps/app.xml").decode("utf-8")))
    return {m: "\n".join(v) for m, v in t.items()}


@pytest.mark.parametrize("utrudnienia", PUSTE_I_PELNE_XLSX)
def test_xlsx_wartosci_obecne_bogaty(tmp_path, utrudnienia):
    d = przytnij_dla("xlsx", _bogaty(), utrudnienia)
    plik = tmp_path / "a.xlsx"
    wartosci = render_xlsx(d, plik, utrudnienia)
    assert wartosci
    teksty = _teksty_xlsx(plik)
    for w in wartosci:
        assert w.tekst in teksty[w.miejsce], (w.id, w.tekst, w.miejsce)


@pytest.mark.parametrize("jezyk,typ", SZABLONY_PRZEKROJOWE)
@pytest.mark.parametrize("utrudnienia", [set(), WSZYSTKIE_XLSX])
def test_xlsx_wartosci_obecne_szablony(tmp_path, jezyk, typ, utrudnienia):
    pelny = _szablonowy(jezyk, typ, 2)
    d = przytnij_dla("xlsx", pelny, utrudnienia)
    plik = tmp_path / "a.xlsx"
    wartosci = render_xlsx(d, plik, utrudnienia)
    teksty = _teksty_xlsx(plik)
    for w in wartosci:
        assert w.tekst in teksty[w.miejsce], (w.id, w.tekst, w.miejsce)
    _porownaj_z_linearyzacja(wartosci, d)
    _nie_wyciekaja(pelny, wartosci, _czesci_zip(plik))


def test_xlsx_otwiera_sie(tmp_path):
    d = przytnij_dla("xlsx", _szablonowy("pl", "faktura", 1), WSZYSTKIE_XLSX)
    plik = tmp_path / "a.xlsx"
    render_xlsx(d, plik, WSZYSTKIE_XLSX)
    with zipfile.ZipFile(plik) as zf:
        assert zf.testzip() is None
    wb = load_workbook(plik)
    assert wb.worksheets and all(ws.max_row >= 1 for ws in wb.worksheets)


def test_xlsx_lista_plac_co_najmniej_200_wierszy(tmp_path):
    d = przytnij_dla("xlsx", _szablonowy("pl", "lista_plac", 1), set())
    plik = tmp_path / "a.xlsx"
    render_xlsx(d, plik, set())
    ws = load_workbook(plik).worksheets[0]
    assert ws.max_row >= 200
    kolumny = {c.column for r in ws.iter_rows() for c in r if c.value is not None}
    assert len(kolumny) >= 5


def test_xlsx_ukryty_arkusz_ma_czesc_danych(tmp_path):
    d = przytnij_dla("xlsx", _szablonowy("pl", "lista_plac", 1), {"arkusz_ukryty"})
    plik = tmp_path / "a.xlsx"
    wartosci = render_xlsx(d, plik, {"arkusz_ukryty"})
    wb = load_workbook(plik)
    ukryte = [ws for ws in wb.worksheets if ws.sheet_state != "visible"]
    assert len(ukryte) == 1 and ukryte[0].max_row >= 5
    assert any(ws.sheet_state == "visible" for ws in wb.worksheets)
    w_ukrytym = {c.value for r in ukryte[0].iter_rows() for c in r if isinstance(c.value, str)}
    assert any(w.tekst in w_ukrytym for w in wartosci if w.miejsce == "tabela")
    bez = tmp_path / "b.xlsx"
    render_xlsx(przytnij_dla("xlsx", _szablonowy("pl", "lista_plac", 1), set()), bez, set())
    assert all(ws.sheet_state == "visible" for ws in load_workbook(bez).worksheets)


def test_xlsx_komentarze_komorek_z_autorem(tmp_path):
    d = przytnij_dla("xlsx", _bogaty(), {"komentarze"})
    plik = tmp_path / "a.xlsx"
    wartosci = render_xlsx(d, plik, {"komentarze"})
    ws = load_workbook(plik).worksheets[0]
    komentarze = [c.comment for r in ws.iter_rows() for c in r if c.comment]
    assert [(k.author, "Do sprawdzenia" in k.text) for k in komentarze] == [("Piotr Nowak", True)]
    assert {w.miejsce for w in wartosci if w.id == "kolega.pelne#1"} == {"komentarz"}
    bez = tmp_path / "b.xlsx"
    render_xlsx(przytnij_dla("xlsx", _bogaty(), set()), bez, set())
    assert not [c for r in load_workbook(bez).worksheets[0].iter_rows() for c in r if c.comment]


def test_xlsx_naglowek_i_stopka_wydruku(tmp_path):
    d = przytnij_dla("xlsx", _bogaty(), {"naglowek_wydruku"})
    plik = tmp_path / "a.xlsx"
    wartosci = render_xlsx(d, plik, {"naglowek_wydruku"})
    ws = load_workbook(plik).worksheets[0]
    assert "Zielińscy i Wspólnicy Kancelaria Prawna" in _stopka_wydruku(ws, "naglowek")
    assert "KRS 0000123456" in _stopka_wydruku(ws, "stopka")
    assert {w.miejsce for w in wartosci if w.id.startswith("kancelaria.krs")} == {"stopka"}
    # bez utrudnienia dane firmy są w komórkach arkusza
    bez = tmp_path / "b.xlsx"
    wb = render_xlsx(przytnij_dla("xlsx", _bogaty(), set()), bez, set())
    ws2 = load_workbook(bez).worksheets[0]
    assert not _stopka_wydruku(ws2, "naglowek") and {w.miejsce for w in wb if w.id.startswith("kancelaria")} == {"tresc"}


def test_xlsx_ampersand_w_naglowku_wydruku_zmienia_sie_na_dwa(tmp_path):
    firma = _w("kancelaria.nazwa#1", "Stachowiak & Stasiak sp.k.", "ORGANIZACJA", "naglowek")
    d = Dokument("amp", "pl", "umowa", "xlsx", [Element("naglowek", [firma]), Element("akapit", ["x"])])
    plik = tmp_path / "a.xlsx"
    render_xlsx(przytnij_dla("xlsx", d, {"naglowek_wydruku"}), plik, {"naglowek_wydruku"})
    ws = load_workbook(plik).worksheets[0]
    assert "Stachowiak && Stasiak" in (ws.oddHeader.center.text or "")
    assert "Stachowiak & Stasiak sp.k." in _stopka_wydruku(ws, "naglowek")


def test_xlsx_metadane_pliku(tmp_path):
    d = przytnij_dla("xlsx", _bogaty(), {"metadane"})
    plik = tmp_path / "a.xlsx"
    wartosci = render_xlsx(d, plik, {"metadane"})
    wb = load_workbook(plik)
    assert wb.properties.creator == wb.properties.lastModifiedBy == "Marek Wójcik"
    assert wb.properties.title == "Umowa testowa"
    with zipfile.ZipFile(plik) as zf:
        assert "<Company>Zielińscy i Wspólnicy Kancelaria Prawna</Company>" in zf.read("docProps/app.xml").decode()
    assert any(w.miejsce == "metadane" and w.kategoria == "ORGANIZACJA" for w in wartosci)
    neutralny = tmp_path / "b.xlsx"
    render_xlsx(przytnij_dla("xlsx", _bogaty(), set()), neutralny, set())
    w2 = load_workbook(neutralny)
    assert w2.properties.creator == w2.properties.lastModifiedBy == "Użytkownik"
    assert w2.properties.creator != "openpyxl"


def test_xlsx_nazwa_arkusza_z_nazwiskiem_lub_firma(tmp_path):
    d = przytnij_dla("xlsx", _bogaty(), {"nazwy_arkuszy"})
    plik = tmp_path / "a.xlsx"
    wartosci = render_xlsx(d, plik, {"nazwy_arkuszy"})
    tytuly = [ws.title for ws in load_workbook(plik).worksheets]
    kopie = [w for w in wartosci if w.miejsce == "metadane"]
    assert kopie and all(any(w.tekst in t for t in tytuly) for w in kopie)
    assert all(len(t) <= 31 for t in tytuly)
    neutralny = tmp_path / "b.xlsx"
    render_xlsx(przytnij_dla("xlsx", _bogaty(), set()), neutralny, set())
    assert not any(w.tekst in ws.title for ws in load_workbook(neutralny).worksheets for w in wartosci if len(w.tekst) > 5)


def test_xlsx_komorka_z_rownoscia_nie_jest_formula(tmp_path):
    d = Dokument("f", "pl", "umowa", "xlsx", [Element("komorka", ["=1+1"], {"tabela": 0, "wiersz": 0, "kolumna": 0}),
                                              Element("komorka", [_w("a.pelne#1", "Anna Nowak")],
                                                      {"tabela": 0, "wiersz": 1, "kolumna": 0})])
    plik = tmp_path / "a.xlsx"
    render_xlsx(przytnij_dla("xlsx", d, set()), plik, set())
    ws = load_workbook(plik).worksheets[0]
    assert ws["A1"].value == "=1+1" and ws["A1"].data_type == "s"


def test_xlsx_deterministyczny_i_nieznane_utrudnienie(tmp_path):
    d = przytnij_dla("xlsx", _szablonowy("pl", "lista_plac", 3), WSZYSTKIE_XLSX)
    a, b = tmp_path / "a.xlsx", tmp_path / "b.xlsx"
    wa, wb_ = render_xlsx(d, a, WSZYSTKIE_XLSX), render_xlsx(d, b, WSZYSTKIE_XLSX)
    assert a.read_bytes() == b.read_bytes() and wa == wb_
    with pytest.raises(ValueError):
        render_xlsx(d, tmp_path / "c.xlsx", {"zmiany"})
    render_xlsx(d, tmp_path / "d.xlsx", {"zdjecie"})


# ----------------------------------------------------------------------------- PPTX
from lxml import etree  # noqa: E402
from pptx import Presentation  # noqa: E402
from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER  # noqa: E402

from pbench.render.pptx import render_pptx, renderuj_pptx  # noqa: E402

WSZYSTKIE_PPTX = set(UTRUDNIENIA_PPTX)
NS_P = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main"}


def _teksty_pptx(plik: Path) -> dict[str, str]:
    """Tekst prezentacji wg miejsca (python-pptx; komentarze i właściwości własne z surowych części)."""
    prs = Presentation(str(plik))
    t: dict[str, list[str]] = {m: [] for m in ("tresc", "naglowek", "tabela", "przypis", "stopka", "komentarz",
                                               "metadane")}
    for nr, slajd in enumerate(prs.slides):
        for sh in slajd.shapes:
            if sh.has_text_frame:
                tekst = sh.text_frame.text
                if sh.is_placeholder and sh.placeholder_format.type == PP_PLACEHOLDER.FOOTER:
                    t["stopka"].append(tekst)
                else:
                    t["tresc"].append(tekst)
                    if nr == 0:
                        t["naglowek"].append(tekst)
            if sh.has_table:
                t["tabela"] += [c.text for r in sh.table.rows for c in r.cells]
        if slajd.has_notes_slide:
            t["przypis"].append(slajd.notes_slide.notes_text_frame.text)
    p = prs.core_properties
    t["metadane"] += [p.author, p.last_modified_by, p.title, p.subject, p.comments, p.keywords]
    with zipfile.ZipFile(plik) as zf:
        for n in zf.namelist():
            tekst = html.unescape(zf.read(n).decode("utf-8", errors="ignore"))
            if n.startswith("ppt/comments/") or n == "ppt/commentAuthors.xml":
                t["komentarz"].append(tekst)
            if n in ("docProps/custom.xml", "docProps/app.xml"):
                t["metadane"].append(tekst)
    return {m: "\n".join(v) for m, v in t.items()}


@pytest.mark.parametrize("utrudnienia", [set(), WSZYSTKIE_PPTX, {"logo", "tabele"}, {"notatki", "komentarze"},
                                         {"metadane"}])
def test_pptx_wartosci_obecne_bogaty(tmp_path, utrudnienia):
    d = przytnij_dla("pptx", _bogaty(), utrudnienia)
    plik = tmp_path / "a.pptx"
    wartosci = render_pptx(d, plik, utrudnienia)
    assert wartosci
    teksty = _teksty_pptx(plik)
    for w in wartosci:
        if w.miejsce == "obraz":
            continue
        zbior = teksty["tresc"] + teksty["naglowek"] if w.miejsce == "naglowek" else teksty[w.miejsce]
        assert w.tekst in zbior, (w.id, w.tekst, w.miejsce)


@pytest.mark.parametrize("jezyk,typ", SZABLONY_PRZEKROJOWE)
@pytest.mark.parametrize("utrudnienia", [set(), WSZYSTKIE_PPTX])
def test_pptx_wartosci_obecne_szablony(tmp_path, jezyk, typ, utrudnienia):
    pelny = _szablonowy(jezyk, typ, 2)
    d = przytnij_dla("pptx", pelny, utrudnienia)
    plik = tmp_path / "a.pptx"
    wartosci = render_pptx(d, plik, utrudnienia)
    teksty = _teksty_pptx(plik)
    for w in wartosci:
        if w.miejsce == "obraz":
            continue
        zbior = teksty["tresc"] if w.miejsce == "naglowek" else teksty[w.miejsce]
        assert w.tekst in zbior, (w.id, w.tekst, w.miejsce)
    _porownaj_z_linearyzacja(wartosci, d)
    _nie_wyciekaja(pelny, wartosci, _czesci_zip(plik))


def test_pptx_otwiera_sie_i_ma_slajdy(tmp_path):
    d = przytnij_dla("pptx", _szablonowy("pl", "prezentacja", 1), WSZYSTKIE_PPTX)
    plik = tmp_path / "a.pptx"
    render_pptx(d, plik, WSZYSTKIE_PPTX)
    with zipfile.ZipFile(plik) as zf:
        assert zf.testzip() is None
    prs = Presentation(str(plik))
    assert len(prs.slides) >= 4
    assert any(sh.has_table for s in prs.slides for sh in s.shapes)


def test_pptx_slajd_tytulowy_z_logo_i_gold_obrazu(tmp_path):
    d = przytnij_dla("pptx", _bogaty(), {"logo"})
    plik = tmp_path / "a.pptx"
    wynik = renderuj_pptx(d, plik, {"logo"})
    prs = Presentation(str(plik))
    obrazy = [sh for sh in prs.slides[0].shapes if sh.shape_type == MSO_SHAPE_TYPE.PICTURE]
    assert len(obrazy) == 1 and len(wynik.obrazy) == 1
    ob = wynik.obrazy[0]
    assert obrazy[0].image.blob == ob.png
    from PIL import Image
    szer, wys = Image.open(io.BytesIO(ob.png)).size
    for wid, (x0, y0, x1, y1) in ob.ramki:
        assert 0 <= x0 < x1 <= szer and 0 <= y0 < y1 <= wys
    assert {w.miejsce for w in wynik.wartosci if w.id.endswith("@obraz")} == {"obraz"}
    bez = renderuj_pptx(przytnij_dla("pptx", _bogaty(), set()), tmp_path / "b.pptx", set())
    assert not bez.obrazy


def test_pptx_slajd_z_tabela_naglowek_powtorzony(tmp_path):
    d = przytnij_dla("pptx", _szablonowy("pl", "lista_plac", 1), {"tabele"})
    plik = tmp_path / "a.pptx"
    wartosci = render_pptx(d, plik, {"tabele"})
    prs = Presentation(str(plik))
    tabele = [sh.table for s in prs.slides for sh in s.shapes if sh.has_table]
    assert len(tabele) > 3
    assert sum(t.cell(0, 0).text == "Lp." for t in tabele) > 3  # nagłówek powtórzony na każdym slajdzie tabeli
    assert sum(1 for w in wartosci if w.miejsce == "tabela") > 100
    # bez utrudnienia tabele są spłaszczone do tekstu
    bez = tmp_path / "b.pptx"
    render_pptx(przytnij_dla("pptx", _szablonowy("pl", "lista_plac", 1), set()), bez, set())
    assert not any(sh.has_table for s in Presentation(str(bez)).slides for sh in s.shapes)


def test_pptx_notatki_prelegenta(tmp_path):
    d = przytnij_dla("pptx", _bogaty(), {"notatki"})
    plik = tmp_path / "a.pptx"
    wartosci = render_pptx(d, plik, {"notatki"})
    notatki = [s.notes_slide.notes_text_frame.text for s in Presentation(str(plik)).slides if s.has_notes_slide]
    assert any("I C 123/21" in n for n in notatki)
    assert {w.miejsce for w in wartosci if w.id.startswith("sprawa.sygnatura")} >= {"przypis"}
    bez = tmp_path / "b.pptx"
    render_pptx(przytnij_dla("pptx", _bogaty(), set()), bez, set())
    assert not any(s.has_notes_slide for s in Presentation(str(bez)).slides)


def test_pptx_komentarze_z_autorem(tmp_path):
    d = przytnij_dla("pptx", _bogaty(), {"komentarze"})
    plik = tmp_path / "a.pptx"
    wartosci = render_pptx(d, plik, {"komentarze"})
    with zipfile.ZipFile(plik) as zf:
        autorzy = etree.fromstring(zf.read("ppt/commentAuthors.xml"))
        assert [a.get("name") for a in autorzy] == ["Piotr Nowak"]
        assert autorzy[0].get("initials") == ""
        komentarze = [n for n in zf.namelist() if n.startswith("ppt/comments/")]
        assert len(komentarze) == 1
        cm = etree.fromstring(zf.read(komentarze[0])).findall("p:cm", NS_P)
        assert [c.find("p:text", NS_P).text for c in cm] == ["Do sprawdzenia."]
        assert "Piotr Nowak" not in zf.read(komentarze[0]).decode()
        ct = zf.read("[Content_Types].xml").decode()
        assert "presentationml.comments+xml" in ct and "presentationml.commentAuthors+xml" in ct
    assert {w.miejsce for w in wartosci if w.id == "kolega.pelne#1"} == {"komentarz"}
    Presentation(str(plik))  # python-pptx otwiera plik z częściami komentarzy


def test_pptx_metadane_pliku(tmp_path):
    d = przytnij_dla("pptx", _bogaty(), {"metadane"})
    plik = tmp_path / "a.pptx"
    wartosci = render_pptx(d, plik, {"metadane"})
    p = Presentation(str(plik)).core_properties
    assert p.author == p.last_modified_by == "Marek Wójcik"
    assert p.title == "Umowa testowa" and p.subject == "Test"
    assert p.comments == "" and "Steve" not in p.last_modified_by
    with zipfile.ZipFile(plik) as zf:
        assert "<Company>Zielińscy i Wspólnicy Kancelaria Prawna</Company>" in zf.read("docProps/app.xml").decode()
    assert any(w.miejsce == "metadane" and w.kategoria == "ORGANIZACJA" for w in wartosci)
    neutralny = tmp_path / "b.pptx"
    render_pptx(przytnij_dla("pptx", _bogaty(), set()), neutralny, set())
    p2 = Presentation(str(neutralny)).core_properties
    assert p2.author == p2.last_modified_by == "Użytkownik" and p2.comments == ""
    assert "Steve Canny" not in "".join(_czesci_zip(neutralny).values())


def test_pptx_stopka_w_polu_stopki_slajdu(tmp_path):
    d = przytnij_dla("pptx", _bogaty(), {"logo"})
    plik = tmp_path / "a.pptx"
    wartosci = render_pptx(d, plik, {"logo"})
    prs = Presentation(str(plik))
    stopki = [sh.text_frame.text for s in prs.slides for sh in s.placeholders
              if sh.placeholder_format.type == PP_PLACEHOLDER.FOOTER]
    assert stopki and all("0000123456" in s for s in stopki)
    assert len([w for w in wartosci if w.id == "kancelaria.krs#1"]) == len(stopki)  # wystąpienie na każdym slajdzie
    assert {w.miejsce for w in wartosci if w.id == "kancelaria.krs#1"} == {"stopka"}


def test_pptx_deterministyczny_i_nieznane_utrudnienie(tmp_path):
    d = przytnij_dla("pptx", _szablonowy("pl", "prezentacja", 3), WSZYSTKIE_PPTX)
    a, b = tmp_path / "a.pptx", tmp_path / "b.pptx"
    wa, wb_ = render_pptx(d, a, WSZYSTKIE_PPTX), render_pptx(d, b, WSZYSTKIE_PPTX)
    assert a.read_bytes() == b.read_bytes() and wa == wb_
    with pytest.raises(ValueError):
        render_pptx(d, tmp_path / "c.pptx", {"zmiany"})
    render_pptx(d, tmp_path / "d.pptx", {"zdjecie"})


# ----------------------------------------------------------------------------- EML
import email  # noqa: E402
from email import policy  # noqa: E402

from docx import Document as DocxDocument  # noqa: E402

from pbench.render.eml import render_eml, renderuj_eml  # noqa: E402

WSZYSTKIE_EML = set(UTRUDNIENIA_EML)
DOCX_ZAL = {"papier_firmowy", "tabele", "przypisy", "komentarze", "metadane"}


def _zalacznik(ziarno: int = 5) -> tuple[Dokument, set[str]]:
    """Krótki powiązany dokument (notatka) przycięty do utrudnień DOCX załącznika."""
    return przytnij_dla("docx", _szablonowy("pl", "notatka", ziarno), DOCX_ZAL), DOCX_ZAL


def _tekst_zip_bajty(bajty: bytes) -> dict[str, str]:
    with zipfile.ZipFile(io.BytesIO(bajty)) as zf:
        return {n: html.unescape(zf.read(n).decode("utf-8", errors="ignore")) for n in zf.namelist()}


def _bez_znacznikow(h: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", h))


def _wczytaj_eml(plik: Path):
    return email.message_from_bytes(plik.read_bytes(), policy=policy.default)


def _teksty_eml(plik: Path) -> dict[str, str]:
    """Miejsca w wiadomości (biblioteka `email`): nagłówki, treść, części HTML, załącznik DOCX."""
    msg = _wczytaj_eml(plik)
    t: dict[str, list[str]] = {m: [] for m in ("metadane", "tresc", "naglowek", "stopka", "zalacznik")}
    t["metadane"] += [f"{k}: {v}" for k, v in msg.items()]
    plain, htm = msg.get_body(("plain",)), msg.get_body(("html",))
    tresc = plain.get_content().replace("\r\n", "\n") if plain else ""
    if htm:
        tresc += "\n" + _bez_znacznikow(htm.get_content())
    for m in ("tresc", "naglowek", "stopka"):
        t[m].append(tresc)
    for zal in msg.iter_attachments():
        czesci = _tekst_zip_bajty(zal.get_content())
        t["zalacznik"] += [_tekst_docx(czesci)]
    return {m: "\n".join(v) for m, v in t.items()}


def _tekst_docx(czesci: dict[str, str]) -> str:
    """Tekst wszystkich części XML DOCX (bez znaczników, atrybuty z autorami też)."""
    wyniki = []
    for nazwa, xml in czesci.items():
        if nazwa.endswith(".xml") or nazwa.endswith(".rels"):
            wyniki.append(xml)
            wyniki.append(re.sub(r"<[^>]+>", "", xml))
    return "\n".join(wyniki)


def _sprawdz_wartosci_eml(plik: Path, wartosci) -> None:
    teksty = _teksty_eml(plik)
    for w in wartosci:
        assert w.tekst in teksty[w.miejsce], (w.id, w.tekst, w.miejsce)


@pytest.mark.parametrize("utrudnienia", [set(), {"html"}, WSZYSTKIE_EML, {"zalacznik"}, {"metadane"}])
def test_eml_wartosci_obecne_bogaty(tmp_path, utrudnienia):
    d = przytnij_dla("eml", _email_z_osobami(), utrudnienia)
    zal, zal_utr = _zalacznik()
    plik = tmp_path / "a.eml"
    wartosci = render_eml(d, plik, utrudnienia, zal, zal_utr)
    assert wartosci
    _sprawdz_wartosci_eml(plik, wartosci)


@pytest.mark.parametrize("jezyk,typ", [("pl", "email"), ("fr", "email"), ("en", "email"), ("de", "email"),
                                       ("es", "email"), ("pl", "umowa"), ("en", "faktura")])
@pytest.mark.parametrize("utrudnienia", [set(), WSZYSTKIE_EML])
def test_eml_wartosci_obecne_szablony(tmp_path, jezyk, typ, utrudnienia):
    pelny = _szablonowy(jezyk, typ, 2)
    d = przytnij_dla("eml", pelny, utrudnienia)
    zal, zal_utr = _zalacznik()
    plik = tmp_path / "a.eml"
    wartosci = render_eml(d, plik, utrudnienia, zal, zal_utr)
    _sprawdz_wartosci_eml(plik, wartosci)
    wlasne = [w for w in wartosci if w.miejsce != "zalacznik"]
    _porownaj_z_linearyzacja(wlasne, d, kopie_metadane=False)
    _nie_wyciekaja(pelny, wlasne, {"eml": "\n".join(_teksty_eml(plik).values())})


def test_eml_otwiera_sie(tmp_path):
    d = przytnij_dla("eml", _email_z_osobami(), WSZYSTKIE_EML)
    zal, zal_utr = _zalacznik()
    plik = tmp_path / "a.eml"
    render_eml(d, plik, WSZYSTKIE_EML, zal, zal_utr)
    msg = _wczytaj_eml(plik)
    assert msg.is_multipart() and not msg.defects
    assert [p.get_content_type() for p in msg.walk()][0] == "multipart/mixed"
    assert msg["MIME-Version"] == "1.0" and msg["Date"] and msg["Message-ID"]
    [zal_msg] = list(msg.iter_attachments())
    DocxDocument(io.BytesIO(zal_msg.get_content()))  # załącznik jest poprawnym DOCX


def test_eml_naglowki_z_osobami_rfc2047(tmp_path):
    d = przytnij_dla("eml", _email_z_osobami(), set())
    plik = tmp_path / "a.eml"
    wartosci = render_eml(d, plik, set())
    surowe = plik.read_bytes()
    assert "Żaneta".encode() not in surowe and b"=?utf-8?" in surowe.lower()  # nazwa zakodowana RFC 2047
    msg = _wczytaj_eml(plik)
    assert "Żaneta Ćwikła" in str(msg["From"]) and "Łukasz Śliwiński" in str(msg["Cc"])
    assert "p.dudek@poczta.test" in str(msg["To"]) and msg["Subject"] == "Projekt pisma – prośba o uwagi"
    assert {w.miejsce for w in wartosci if w.id in ("nadawca.pelne#1", "klient.email#1", "kolega.pelne#1")} == {"metadane"}


def test_eml_stopka_z_telefonem_po_separatorze(tmp_path):
    d = przytnij_dla("eml", _email_z_osobami(), set())
    plik = tmp_path / "a.eml"
    wartosci = render_eml(d, plik, set())
    tresc = _wczytaj_eml(plik).get_body(("plain",)).get_content().replace("\r\n", "\n")
    przed, _, stopka = tresc.partition("\n-- \n")
    assert "+48 600 100 200" in stopka and "+48 600 100 200" not in przed
    assert {w.miejsce for w in wartosci if w.id in ("nadawca.telefon#1", "kancelaria.nazwa#1")} == {"stopka"}


def test_eml_html_jako_alternatywa_z_encjami(tmp_path):
    d = przytnij_dla("eml", _email_z_osobami(), {"html"})
    plik = tmp_path / "a.eml"
    wartosci = render_eml(d, plik, {"html"})
    msg = _wczytaj_eml(plik)
    assert msg.get_content_type() == "multipart/alternative"
    plain = msg.get_body(("plain",)).get_content().replace("\r\n", "\n")
    htm = msg.get_body(("html",)).get_content()
    assert "termin & miejsce <ok>" in plain and "termin &amp; miejsce &lt;ok&gt;" in htm
    assert "Piotr Żółć" in _bez_znacznikow(htm)
    assert len([w for w in wartosci if w.id == "klient.pelne#1"]) == 1  # jedno wystąpienie wzorcowe
    bez = tmp_path / "b.eml"
    render_eml(przytnij_dla("eml", _email_z_osobami(), set()), bez, set())
    assert _wczytaj_eml(bez).get_content_type() == "text/plain"


def test_eml_zalacznik_docx_gold_z_prefiksem(tmp_path):
    d = przytnij_dla("eml", _email_z_osobami(), {"zalacznik"})
    zal, zal_utr = _zalacznik()
    plik = tmp_path / "a.eml"
    wynik = renderuj_eml(d, plik, {"zalacznik"}, zal, zal_utr)
    wz = [w for w in wynik.wartosci if w.miejsce == "zalacznik"]
    assert wz and all(w.id.startswith("zal:") for w in wz)
    assert all(not w.id.startswith("zal:") for w in wynik.wartosci if w.miejsce != "zalacznik")
    # załącznik zawiera (co najmniej) wszystkie wartości linearyzacji przyciętej notatki
    oczekiwane = {(f"zal:{i}", t) for (i, t, m) in _oczekiwane(zal) if m != "obraz"}
    assert oczekiwane <= {(w.id, w.tekst) for w in wz}
    msg = _wczytaj_eml(plik)
    [zal_msg] = list(msg.iter_attachments())
    assert zal_msg.get_filename() == "notatka.docx"  # nazwa bez danych osobowych
    assert zal_msg.get_content_type().endswith("wordprocessingml.document")
    # DOCX załącznika = DOCX z renderera DOCX
    from pbench.render.docx import render_docx
    sam = tmp_path / "sam.docx"
    render_docx(zal, sam, zal_utr)
    assert zal_msg.get_content() == sam.read_bytes()
    # wartości obrazów załącznika to nie tekst pliku: są w obrazach, nie w liście wartości
    assert not any(w.miejsce == "obraz" for w in wynik.wartosci)
    assert all(o.id.startswith("zal:") for o in wynik.obrazy_zalacznika)


def test_eml_bez_utrudnienia_zalacznik_pomijany_i_brak_dokumentu_to_blad(tmp_path):
    d = przytnij_dla("eml", _email_z_osobami(), set())
    zal, zal_utr = _zalacznik()
    plik = tmp_path / "a.eml"
    render_eml(d, plik, set(), zal, zal_utr)
    assert not list(_wczytaj_eml(plik).iter_attachments())
    with pytest.raises(ValueError):
        render_eml(d, plik, {"zalacznik"})


def test_eml_dodatkowe_naglowki_z_metadanych(tmp_path):
    d = przytnij_dla("eml", _email_z_osobami(), {"metadane"})
    plik = tmp_path / "a.eml"
    wartosci = render_eml(d, plik, {"metadane"})
    msg = _wczytaj_eml(plik)
    assert msg["X-Author"] == "Marek Wójcik" and msg["X-Case"] == "I C 123/21"
    assert {w.miejsce for w in wartosci if w.id == "autor.pelne#1"} == {"metadane"}
    bez = tmp_path / "b.eml"
    render_eml(przytnij_dla("eml", _email_z_osobami(), set()), bez, set())
    assert "Marek" not in _wczytaj_eml(bez).as_string()


def test_eml_deterministyczny_i_nieznane_utrudnienie(tmp_path):
    d = przytnij_dla("eml", _szablonowy("pl", "email", 3), WSZYSTKIE_EML)
    zal, zal_utr = _zalacznik()
    a, b = tmp_path / "a.eml", tmp_path / "b.eml"
    wa, wb_ = render_eml(d, a, WSZYSTKIE_EML, zal, zal_utr), render_eml(d, b, WSZYSTKIE_EML, zal, zal_utr)
    assert a.read_bytes() == b.read_bytes() and wa == wb_
    with pytest.raises(ValueError):
        render_eml(d, tmp_path / "c.eml", {"tabele"})
    render_eml(d, tmp_path / "d.eml", {"zdjecie"})


# ----------------------------------------------------------------------------- MSG
import olefile  # noqa: E402
import struct  # noqa: E402

from pbench.render.cfb import zapisz_cfb  # noqa: E402
from pbench.render.msg import render_msg, renderuj_msg  # noqa: E402

WSZYSTKIE_MSG = set(UTRUDNIENIA_MSG)


def _strumienie(plik: Path) -> dict[str, bytes]:
    """Wszystkie strumienie OLE (olefile) jako nazwa -> bajty, nazwy ze ścieżką po `/`."""
    ole = olefile.OleFileIO(str(plik))
    try:
        return {"/".join(s): ole.openstream(s).read() for s in ole.listdir(streams=True, storages=False)}
    finally:
        ole.close()


def _napisy(strumienie: dict[str, bytes]) -> dict[str, str]:
    """Strumienie tekstowe MAPI (`…001F` UTF-16LE, `…001E` 8-bitowe) zdekodowane; reszta pominięta."""
    wynik = {}
    for nazwa, dane in strumienie.items():
        m = re.search(r"__substg1\.0_([0-9A-F]{4})([0-9A-F]{4})$", nazwa)
        if m and m.group(2) == "001F":
            wynik[nazwa] = dane.decode("utf-16-le")
        elif m and m.group(2) == "001E":
            wynik[nazwa] = dane.decode("cp1250")
    return wynik


def _teksty_msg(plik: Path) -> dict[str, str]:
    """Miejsca w MSG wg olefile: właściwości nagłówkowe, treść (PR_BODY, PR_HTML), załącznik (PR_ATTACH_DATA_BIN)."""
    s = _strumienie(plik)
    n = _napisy(s)
    t: dict[str, list[str]] = {m: [] for m in ("metadane", "tresc", "naglowek", "stopka", "zalacznik")}
    for nazwa, tekst in n.items():
        tag = nazwa.rsplit("_", 1)[1][:4]
        if "__recip_version1.0_" in nazwa or tag in ("0037", "0C1A", "0C1F", "5D01", "0E04", "0E03", "007D"):
            t["metadane"].append(tekst)
        elif tag == "1000":
            for m in ("tresc", "naglowek", "stopka"):
                t[m].append(tekst.replace("\r\n", "\n"))
    for nazwa, dane in s.items():
        if nazwa.endswith("__substg1.0_10130102"):
            for m in ("tresc", "naglowek", "stopka"):
                t[m].append(_bez_znacznikow(dane.decode("utf-8")))
        if "__attach_version1.0_" in nazwa and nazwa.endswith("__substg1.0_37010102"):
            t["zalacznik"].append(_tekst_docx(_tekst_zip_bajty(dane)))
    return {m: "\n".join(v) for m, v in t.items()}


def _sprawdz_wartosci_msg(plik: Path, wartosci) -> None:
    teksty = _teksty_msg(plik)
    for w in wartosci:
        assert w.tekst in teksty[w.miejsce], (w.id, w.tekst, w.miejsce)


@pytest.mark.parametrize("utrudnienia", [set(), {"html"}, WSZYSTKIE_MSG, {"zalacznik"}, {"metadane"}])
def test_msg_wartosci_obecne_bogaty(tmp_path, utrudnienia):
    d = przytnij_dla("msg", _email_z_osobami(), utrudnienia)
    zal, zal_utr = _zalacznik()
    plik = tmp_path / "a.msg"
    wartosci = render_msg(d, plik, utrudnienia, zal, zal_utr)
    assert wartosci
    _sprawdz_wartosci_msg(plik, wartosci)


@pytest.mark.parametrize("jezyk,typ", [("pl", "email"), ("fr", "email"), ("en", "email"), ("de", "email"),
                                       ("es", "email"), ("pl", "umowa"), ("en", "faktura")])
@pytest.mark.parametrize("utrudnienia", [set(), WSZYSTKIE_MSG])
def test_msg_wartosci_obecne_szablony(tmp_path, jezyk, typ, utrudnienia):
    pelny = _szablonowy(jezyk, typ, 2)
    d = przytnij_dla("msg", pelny, utrudnienia)
    zal, zal_utr = _zalacznik()
    plik = tmp_path / "a.msg"
    wartosci = render_msg(d, plik, utrudnienia, zal, zal_utr)
    _sprawdz_wartosci_msg(plik, wartosci)
    wlasne = [w for w in wartosci if w.miejsce != "zalacznik"]
    _porownaj_z_linearyzacja(wlasne, d, kopie_metadane=False)
    _nie_wyciekaja(pelny, wlasne, {"msg": "\n".join(_teksty_msg(plik).values()) + "\n".join(
        _napisy(_strumienie(plik)).values())})


def test_msg_otwiera_sie_olefile_i_extract_msg(tmp_path):
    import extract_msg
    d = przytnij_dla("msg", _email_z_osobami(), WSZYSTKIE_MSG)
    zal, zal_utr = _zalacznik()
    plik = tmp_path / "a.msg"
    render_msg(d, plik, WSZYSTKIE_MSG, zal, zal_utr)
    assert olefile.isOleFile(str(plik))
    msg = extract_msg.openMsg(str(plik))
    try:
        assert msg.subject == "Projekt pisma – prośba o uwagi"
        assert msg.sender == "Żaneta Ćwikła"
        assert "p.dudek@poczta.test" in msg.to and "Łukasz Śliwiński" in msg.cc
        assert "Piotr Żółć" in msg.body and "+48 600 100 200" in msg.body
        assert "termin &amp; miejsce &lt;ok&gt;" in msg.htmlBody.decode("utf-8")
        [zal_msg] = msg.attachments
        assert zal_msg.longFilename == "notatka.docx"
        DocxDocument(io.BytesIO(zal_msg.data))  # załącznik jest poprawnym DOCX
        assert msg.date is not None
    finally:
        msg.close()


def test_msg_nazwa_nadawcy_i_odbiorcy_we_wlasciwosciach_mapi(tmp_path):
    d = przytnij_dla("msg", _email_z_osobami(), set())
    plik = tmp_path / "a.msg"
    wartosci = render_msg(d, plik, set())
    n = _napisy(_strumienie(plik))
    assert n["__substg1.0_0C1A001F"] == "Żaneta Ćwikła"  # PR_SENDER_NAME
    assert n["__substg1.0_0E04001F"] == "p.dudek@poczta.test"  # PR_DISPLAY_TO
    assert n["__substg1.0_0E03001F"] == "Łukasz Śliwiński"  # PR_DISPLAY_CC
    assert n["__substg1.0_0037001F"].startswith("Projekt pisma")  # PR_SUBJECT
    assert "+48 600 100 200" in n["__substg1.0_1000001F"]  # PR_BODY
    odbiorcy = sorted(v for k, v in n.items() if "__recip_version1.0_" in k and k.endswith("3001001F"))
    assert odbiorcy == ["p.dudek@poczta.test", "Łukasz Śliwiński"]
    assert {w.miejsce for w in wartosci if w.id in ("nadawca.pelne#1", "klient.email#1", "kolega.pelne#1")} == {"metadane"}


def test_msg_zalacznik_pr_attach_data_bin(tmp_path):
    d = przytnij_dla("msg", _email_z_osobami(), {"zalacznik"})
    zal, zal_utr = _zalacznik()
    plik = tmp_path / "a.msg"
    wynik = renderuj_msg(d, plik, {"zalacznik"}, zal, zal_utr)
    s = _strumienie(plik)
    dane = [v for k, v in s.items() if k.endswith("__substg1.0_37010102")]
    assert len(dane) == 1
    from pbench.render.docx import render_docx
    sam = tmp_path / "sam.docx"
    render_docx(zal, sam, zal_utr)
    assert dane[0] == sam.read_bytes()
    nazwy = [v for k, v in _napisy(s).items() if k.endswith("3707001F") and "__attach_version1.0_" in k]
    assert nazwy == ["notatka.docx"]
    wz = [w for w in wynik.wartosci if w.miejsce == "zalacznik"]
    assert wz and all(w.id.startswith("zal:") for w in wz)
    assert all(o.id.startswith("zal:") for o in wynik.obrazy_zalacznika)


def test_msg_html_i_dodatkowe_naglowki(tmp_path):
    d = przytnij_dla("msg", _email_z_osobami(), {"html", "metadane"})
    plik = tmp_path / "a.msg"
    wartosci = render_msg(d, plik, {"html", "metadane"})
    s = _strumienie(plik)
    assert "__substg1.0_10130102" in s
    naglowki = _napisy(s)["__substg1.0_007D001F"]  # PR_TRANSPORT_MESSAGE_HEADERS
    assert "X-Author: Marek Wójcik" in naglowki and "X-Case: I C 123/21" in naglowki
    assert len([w for w in wartosci if w.id == "klient.pelne#1"]) == 1
    bez = tmp_path / "b.msg"
    render_msg(przytnij_dla("msg", _email_z_osobami(), set()), bez, set())
    s2 = _strumienie(bez)
    assert "__substg1.0_10130102" not in s2 and "__substg1.0_007D001F" not in s2


def test_msg_ta_sama_tresc_co_eml(tmp_path):
    for utr in (set(), {"html", "metadane"}):
        d = przytnij_dla("msg", _email_z_osobami(), utr)
        a = render_msg(d, tmp_path / "a.msg", utr)
        b = render_eml(przytnij_dla("eml", _email_z_osobami(), utr), tmp_path / "a.eml", utr)
        assert _licz(a) == _licz(b)


def test_cfb_duzy_strumien_i_mini_strumien_odczyt_olefile(tmp_path):
    duzy, maly = bytes(range(256)) * 80, b"abc"
    plik = tmp_path / "a.cfb"
    zapisz_cfb(plik, {"A": {"duzy": duzy, "maly": maly, "pusty": b""}, "zeta": b"z" * 4095, "z4096": b"q" * 4096})
    ole = olefile.OleFileIO(str(plik))
    assert ole.openstream("A/duzy").read() == duzy and ole.openstream("A/maly").read() == maly
    assert ole.openstream("A/pusty").read() == b"" and ole.openstream("zeta").read() == b"z" * 4095
    assert ole.openstream("z4096").read() == b"q" * 4096
    assert struct.unpack_from("<H", plik.read_bytes(), 28)[0] == 0xFFFE
    ole.close()
    with pytest.raises(ValueError):
        zapisz_cfb(tmp_path / "b.cfb", {"x": bytes(8_000_000)})


def test_msg_deterministyczny_i_nieznane_utrudnienie(tmp_path):
    d = przytnij_dla("msg", _szablonowy("pl", "email", 3), WSZYSTKIE_MSG)
    zal, zal_utr = _zalacznik()
    a, b = tmp_path / "a.msg", tmp_path / "b.msg"
    wa, wb_ = render_msg(d, a, WSZYSTKIE_MSG, zal, zal_utr), render_msg(d, b, WSZYSTKIE_MSG, zal, zal_utr)
    assert a.read_bytes() == b.read_bytes() and wa == wb_
    with pytest.raises(ValueError):
        render_msg(d, tmp_path / "c.msg", {"tabele"})
    render_msg(d, tmp_path / "d.msg", {"zdjecie"})
    with pytest.raises(ValueError):
        render_msg(d, tmp_path / "e.msg", {"zalacznik"})


# ----------------------------------------------------------------------------- DOC
import shutil  # noqa: E402
import subprocess  # noqa: E402

from lxml import etree as _etree  # noqa: E402

from pbench.render.doc import ZAKODOWANIA_TEKSTU, odfiltruj_zachowane, render_doc, renderuj_doc  # noqa: E402

WSZYSTKIE_DOC = set(UTRUDNIENIA_DOC)
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _blob_doc(plik: Path) -> bytes:
    """Wszystkie strumienie pliku DOC (olefile) sklejone – do wyszukiwania wartości w obu kodowaniach Worda."""
    ole = olefile.OleFileIO(str(plik))
    try:
        return b"\0".join(ole.openstream(s).read() for s in ole.listdir())
    finally:
        ole.close()


def _w_blobie(tekst: str, blob: bytes) -> bool:
    for k in ZAKODOWANIA_TEKSTU:
        try:
            if tekst.encode(k) in blob:
                return True
        except UnicodeEncodeError:
            continue
    return False


def _doc_na_docx(plik: Path, wyjscie: Path) -> Path:
    """Niezależny odczyt: LibreOffice DOC -> DOCX (osobny profil), do sprawdzenia miejsc wartości."""
    wyjscie.mkdir(parents=True, exist_ok=True)
    subprocess.run([shutil.which("soffice"), "--headless", "--norestore",
                    f"-env:UserInstallation=file://{wyjscie / 'profil'}", "--convert-to", "docx", "--outdir",
                    str(wyjscie), str(plik)], capture_output=True, timeout=180, check=True)
    return wyjscie / (plik.stem + ".docx")


def _tekst_xml(zf: zipfile.ZipFile, nazwa: str) -> str:
    root = _etree.fromstring(zf.read(nazwa))
    akapity = ["".join(t.text or "" for t in p.iter(f"{{{W_NS}}}t", f"{{{W_NS}}}delText"))
               for p in root.iter(f"{{{W_NS}}}p")]
    return "\n".join(akapity + [v for e in root.iter() for v in e.attrib.values()] + list(root.itertext()))


def _miejsca_docx(plik: Path) -> dict[str, str]:
    CZESCI_DOC = {"tresc": ["word/document.xml"], "tabela": ["word/document.xml"], "pole": ["word/document.xml"],
                  "zmiany": ["word/document.xml"], "naglowek": ["word/header"], "stopka": ["word/footer"],
                  "przypis": ["word/footnotes.xml"], "komentarz": ["word/comments.xml"],
                  "metadane": ["docProps/core.xml", "docProps/custom.xml", "docProps/app.xml"]}
    with zipfile.ZipFile(plik) as zf:
        return {m: "\n".join(_tekst_xml(zf, n) for n in zf.namelist()
                             if n.endswith(".xml") and any(n.startswith(p) for p in prefiksy))
                for m, prefiksy in CZESCI_DOC.items()}


@pytest.fixture(scope="module")
def doc_bogaty(tmp_path_factory):
    """Bogaty dokument wszystkimi utrudnieniami: DOC, wynik renderera i odczyt zwrotny (jedna konwersja na moduł)."""
    katalog = tmp_path_factory.mktemp("doc_bogaty")
    d = przytnij_dla("doc", _bogaty(), WSZYSTKIE_DOC)
    plik = katalog / "a.doc"
    wynik = renderuj_doc(d, plik, WSZYSTKIE_DOC)
    return d, plik, wynik, _doc_na_docx(plik, katalog / "zwrot")


def test_doc_wartosci_obecne_bogaty(doc_bogaty):
    _, plik, wynik, _ = doc_bogaty
    assert wynik.wartosci
    blob = _blob_doc(plik)
    for w in wynik.wartosci:
        if w.miejsce != "obraz":
            assert _w_blobie(w.tekst, blob), (w.id, w.tekst, w.miejsce)


def test_doc_otwiera_sie_i_wartosci_w_swoich_miejscach(doc_bogaty):
    d, plik, wynik, zwrot = doc_bogaty
    assert olefile.isOleFile(str(plik)) and plik.read_bytes()[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    DocxDocument(str(zwrot))  # LibreOffice otworzył DOC i odtworzył poprawny DOCX
    teksty = _miejsca_docx(zwrot)
    for w in wynik.wartosci:
        if w.miejsce == "obraz":
            continue
        assert w.tekst in teksty[w.miejsce], (w.id, w.tekst, w.miejsce)


def test_doc_zachowuje_komentarze_zmiany_przypisy_pola_i_obrazy(doc_bogaty):
    _, plik, wynik, zwrot = doc_bogaty
    miejsca = {w.miejsce for w in wynik.wartosci}
    assert {"komentarz", "zmiany", "przypis", "pole", "naglowek", "stopka", "tabela", "metadane"} <= miejsca
    assert not wynik.ostrzezenia
    assert len(wynik.obrazy) == 2  # logo i podpis przeżyły konwersję (PNG bez zmian w strumieniu Data)
    blob = _blob_doc(plik)
    assert all(o.png in blob for o in wynik.obrazy)
    with zipfile.ZipFile(zwrot) as zf:
        doc_xml = zf.read("word/document.xml").decode()
        assert "<w:ins " in doc_xml and "<w:del " in doc_xml and "Piotr Nowak" in zf.read("word/comments.xml").decode()


def test_doc_linearyzacja_zgodna_ze_zwroconymi(doc_bogaty):
    d, _, wynik, _ = doc_bogaty
    zwrocone = _licz(wynik.wartosci)
    oczekiwane = _oczekiwane(d)
    assert not (oczekiwane - zwrocone) and not (zwrocone - oczekiwane)


def test_doc_metadane_summary_information(doc_bogaty):
    _, plik, _, _ = doc_bogaty
    ole = olefile.OleFileIO(str(plik))
    try:
        p = ole.getproperties("\x05SummaryInformation")
    finally:
        ole.close()
    assert p[4] == "Marek Wójcik".encode() and p[2] == "Umowa testowa".encode()  # autor, tytuł (UTF-8)


def test_doc_obrazy_gold_jak_w_docx(doc_bogaty):
    _, _, wynik, _ = doc_bogaty
    assert {w.miejsce for w in wynik.wartosci if w.id.endswith("@obraz")} == {"obraz"}
    assert all(o.png and o.ramki for o in wynik.obrazy)


@pytest.mark.parametrize("jezyk,typ", [("pl", "umowa"), ("en", "faktura"), ("pl", "lista_plac")])
def test_doc_szablony_wartosci_i_brak_wyciekow(tmp_path, jezyk, typ):
    pelny = _szablonowy(jezyk, typ, 2)
    utr = {"papier_firmowy", "tabele", "przypisy", "komentarze", "zmiany", "metadane", "pola"}
    d = przytnij_dla("doc", pelny, utr)
    plik = tmp_path / "a.doc"
    wynik = renderuj_doc(d, plik, utr)
    blob = _blob_doc(plik)
    for w in wynik.wartosci:
        if w.miejsce != "obraz":
            assert _w_blobie(w.tekst, blob), (w.id, w.tekst, w.miejsce)
    zwrocone, oczekiwane = _licz(wynik.wartosci), _oczekiwane(d)
    assert not (zwrocone - oczekiwane)
    assert oczekiwane - zwrocone == Counter(
        {(i, t, m): 1 for (i, t, m) in oczekiwane - zwrocone})  # brakujące = tylko te z ostrzeżeń
    assert len(oczekiwane - zwrocone) == len(wynik.ostrzezenia)
    dekodowania = [blob[s:].decode(k, errors="ignore") for k in ("utf-16-le", "cp1252", "cp1250", "utf-8") for s in (0, 1)]
    _nie_wyciekaja(pelny, wynik.wartosci, {f"d{i}": t for i, t in enumerate(dekodowania)})


def test_odfiltruj_zachowane_usuwa_to_czego_nie_ma_w_pliku_z_ostrzezeniem():
    obecna, brak = _w("a.pelne#1", "Anna Nowak"), _w("b.pelne#1", "Jan Zażółć", miejsce="komentarz")
    fragment = _w("c.pelne#1", "Anna Nowa")  # tylko jako początek dłuższego słowa
    inne_miejsce = _w("d.pelne#1", "Piotr Lis", miejsce="komentarz")  # jest, ale w treści, nie w komentarzach
    teksty = {"tresc": "x Anna Nowak, Anna Nowakowska i Piotr Lis", "komentarz": "Jan"}
    z_png, bez_png = b"\x89PNG-obecny", b"\x89PNG-brak"
    from pbench.model import Obraz
    ob1 = Obraz("o1", z_png, [_w("a.pelne#1@obraz", "Anna Nowak", miejsce="obraz")], [("a.pelne#1@obraz", (0, 0, 5, 5))])
    ob2 = Obraz("o2", bez_png, [_w("b.pelne#1@obraz", "Jan", miejsce="obraz")], [("b.pelne#1@obraz", (0, 0, 5, 5))])
    wartosci = [obecna, brak, fragment, inne_miejsce, *ob1.wartosci, *ob2.wartosci]
    ok, obrazy, ostrzezenia = odfiltruj_zachowane(wartosci, [ob1, ob2], teksty, b"..." + z_png)
    assert [w.id for w in ok] == ["a.pelne#1", "a.pelne#1@obraz"] and obrazy == [ob1]
    assert len(ostrzezenia) == 4
    assert all(any(i in o for o in ostrzezenia) for i in ("b.pelne#1", "c.pelne#1", "d.pelne#1", "o2"))


def test_doc_deterministyczny_i_nieznane_utrudnienie(tmp_path):
    d = przytnij_dla("doc", _bogaty(), {"komentarze", "metadane"})
    a, b = tmp_path / "a.doc", tmp_path / "b.doc"
    wa, wb_ = render_doc(d, a, {"komentarze", "metadane"}), render_doc(d, b, {"komentarze", "metadane"})
    assert a.read_bytes() == b.read_bytes() and wa == wb_
    with pytest.raises(ValueError):
        render_doc(d, tmp_path / "c.doc", {"html"})


def test_xlsx_modified_z_dokumentu_nie_z_zegara(tmp_path):
    import time
    d = przytnij_dla("xlsx", _bogaty(), {"metadane"})
    a, b = tmp_path / "a.xlsx", tmp_path / "b.xlsx"
    render_xlsx(d, a, {"metadane"})
    time.sleep(1.1)
    render_xlsx(d, b, {"metadane"})
    assert a.read_bytes() == b.read_bytes()
    with zipfile.ZipFile(a) as zf:
        core = zf.read("docProps/core.xml").decode()
    zm = re.search(r"<dcterms:modified[^>]*>([^<]*)<", core).group(1)
    wb = load_workbook(a)
    assert wb.properties.modified.strftime("%Y-%m-%dT%H:%M:%SZ") == zm
    assert wb.properties.modified >= wb.properties.created
    assert wb.properties.modified.year <= 2026


def test_pptx_daty_komentarzy_w_zakresie_pliku(tmp_path):
    import datetime
    d = przytnij_dla("pptx", _bogaty(), {"komentarze"})
    plik = tmp_path / "a.pptx"
    render_pptx(d, plik, {"komentarze"})
    p = Presentation(str(plik)).core_properties
    with zipfile.ZipFile(plik) as zf:
        for n in zf.namelist():
            if n.startswith("ppt/comments/"):
                for cm in etree.fromstring(zf.read(n)).findall("p:cm", NS_P):
                    t = datetime.datetime.fromisoformat(cm.get("dt"))
                    assert p.created <= t <= p.modified


def _email_z_adresem_osoby() -> Dokument:
    d = _email_z_osobami()
    d.elementy.append(Element("stopka", ["e-mail: ", _w("nadawca.email#1", "z.cwikla@kancelaria.test", "EMAIL", "stopka")]))
    d.metadane["to"] = _w("klient.pelne#9", "Kowalski, Jan", "OSOBA", "metadane")
    return d


def test_eml_osoba_z_adresem_i_bez_poprawnie_zapisana(tmp_path):
    d = przytnij_dla("eml", _email_z_adresem_osoby(), set())
    plik = tmp_path / "a.eml"
    wartosci = render_eml(d, plik, set())
    msg = _wczytaj_eml(plik)
    adr = msg["From"].addresses[0]
    assert adr.display_name == "Żaneta Ćwikła" and adr.addr_spec == "z.cwikla@kancelaria.test"
    assert b"=?utf-8?" in plik.read_bytes().lower() and "Żaneta".encode() not in plik.read_bytes()
    assert {w.miejsce for w in wartosci if w.id == "nadawca.email#1"} == {"metadane", "stopka"}
    # osoba bez adresu w dokumencie: sama nazwa, w cudzysłowie (ASCII ze znakami specjalnymi)
    assert str(msg["To"]) == '"Kowalski, Jan"'
    assert '"Kowalski, Jan"' in plik.read_text()
    _sprawdz_wartosci_eml(plik, wartosci)


def test_msg_osoba_z_adresem_i_rozmiar_tekstu_z_terminatorem(tmp_path):
    d = przytnij_dla("msg", _email_z_adresem_osoby(), set())
    plik = tmp_path / "a.msg"
    render_msg(d, plik, set())
    n = _napisy(_strumienie(plik))
    assert n["__substg1.0_0C1A001F"] == "Żaneta Ćwikła" and n["__substg1.0_0C1F001F"] == "z.cwikla@kancelaria.test"
    s = _strumienie(plik)
    props = s["__properties_version1.0"]
    wpisy = {struct.unpack_from("<I", props, o)[0]: struct.unpack_from("<I", props, o + 8)[0]
             for o in range(32, len(props), 16)}
    tytul = s["__substg1.0_0037001F"]
    assert wpisy[0x0037001F] == len(tytul) + 2
