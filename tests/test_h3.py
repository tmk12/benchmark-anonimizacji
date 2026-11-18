"""Warstwa trudnych przypadków, zadanie H3 (spec §11 pkt 1): treść ukryta w DOCX, XLSX i PPTX. Rejestr, plan, manifest,
obecność każdej wartości w pliku (niezależny czytnik: zipfile + lxml, bez kodu sędziego), poprawność pakietu OOXML
(ZIP, części XML, typy zawartości, relacje; konwersja LibreOffice, gdy jest), widoczność w sędzi plikowym i sanity:
oryginał wycieka, idealny uczestnik nie, uczestnik czyszczący tylko widoczną treść zostawia wyciek w elementach ukrytych."""
from __future__ import annotations

import io
import json
import posixpath
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest
from lxml import etree
from openpyxl import load_workbook

from pbench import przypadki as P, trudne, trudne_ukryta as U
from pbench.model import Dokument, Wartosc
from pbench.sedzia.ekstrakcja import wydobadz
from pbench.sedzia.plik import ocen_plik
from pbench.sedzia.sanity import Maskowanie, wartosci_wpisu

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
      "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
      "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
      "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
      "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
      "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
      "v": "urn:schemas-microsoft-com:vml"}
RODZAJE = {"docx": sorted(r for r in U.MIEJSCA if r.startswith("docx.")),
           "xlsx": sorted(r for r in U.MIEJSCA if r.startswith("xlsx.")),
           "pptx": sorted(r for r in U.MIEJSCA if r.startswith("pptx."))}
PRZYPADEK_FORMATU = {"docx": P.UKRYTA_DOCX, "xlsx": P.UKRYTA_XLSX, "pptx": P.UKRYTA_PPTX}


# ============================================================================= rejestr, model
def test_rejestr_h3():
    assert P.H3 == (P.UKRYTA_DOCX, P.UKRYTA_XLSX, P.UKRYTA_PPTX) and P.UKRYTA_PPTX == "ukryta_pptx"
    assert set(P.H3) <= set(P.PRZYPADKI) and "pptx" in P.PRZYPADKI[P.UKRYTA_PPTX].lower()
    assert {P.SKROTY[p] for p in P.H3} == {"ud", "ux", "up"}
    assert len(set(P.SKROTY.values())) == len(P.SKROTY)
    assert P.FORMAT_PRZYPADKU == {P.UKRYTA_DOCX: "docx", P.UKRYTA_XLSX: "xlsx", P.UKRYTA_PPTX: "pptx"}


def test_dokument_ukryte_serializacja_tylko_gdy_ustawione():
    d = Dokument("x", "pl", "umowa", "docx")
    assert "ukryte" not in d.to_dict()                      # JSON dokumentów trzonu bez zmian
    w = Wartosc("u.vanish.pelne#1", "OSOBA", "Jan Zielony", "pl", "metadane", "OSOBA")
    from pbench.model import Element
    d.ukryte = [Element("docx.vanish", ["Uwaga: ", w])]
    assert Dokument.from_json(d.to_json()) == d and d.to_dict()["ukryte"][0]["rodzaj"] == "docx.vanish"


def test_w_pikselach_cecha_tekst_xml():
    a = Wartosc("a#1", "OSOBA", "Jan Zielony", "pl", "obraz", "OSOBA")
    b = Wartosc("b#1", "OSOBA", "Jan Zielony", "pl", "obraz", "OSOBA", cechy=["tekst_xml"])
    assert a.w_pikselach and not b.w_pikselach and not Wartosc("c#1", "OSOBA", "Jan", "pl", "tresc", "OSOBA").w_pikselach


def test_mapowanie_miejsc_zgodne_z_dokumentem_i_wagami():
    wagi = json.loads(Path("metodyka/wagi_punktow.json").read_text(encoding="utf-8"))["wagi_miejsc"]
    assert set(U.MIEJSCA.values()) <= set(wagi)             # tylko istniejące miejsca, wagi bez zmian
    md = Path("metodyka/miejsca-ukryte.md").read_text(encoding="utf-8")
    wiersze = {}
    for linia in md.splitlines():
        m = re.match(r"\| (`[^|]+`) \| `(\w+)` \| ([\d,]+) \|", linia)
        if m:
            for rodzaj in re.findall(r"`([a-z_.]+)`", m.group(1)):
                wiersze[rodzaj] = (m.group(2), float(m.group(3).replace(",", ".")))
    assert {k: v[0] for k, v in wiersze.items()} == U.MIEJSCA
    assert all(wagi[miejsce] == waga for miejsce, waga in wiersze.values())
    # zasada: widoczne w normalnym widoku -> niższa waga niż niewidoczne
    assert wagi[U.MIEJSCA["docx.vanish"]] > wagi[U.MIEJSCA["docx.pole_tekstowe"]]


# ============================================================================= generacja
@pytest.fixture(scope="module")
def warstwa(tmp_path_factory) -> dict[str, tuple[Path, list[dict]]]:
    wynik = {}
    for przypadek in P.H3:
        cel = tmp_path_factory.mktemp(przypadek)
        wynik[przypadek] = (cel, trudne.zbuduj_przypadek(cel, przypadek, 10, procesy=1))
    return wynik


def _wpisy():
    return [(przypadek, i) for przypadek in P.H3 for i in range(10)]


def test_manifest_h3(warstwa):
    for przypadek, (cel, wpisy) in warstwa.items():
        fmt = P.FORMAT_PRZYPADKU[przypadek]
        assert len(wpisy) == 10 and [json.loads(l) for l in (cel / "manifest.jsonl").read_text(encoding="utf-8").splitlines()] == wpisy
        assert {w["jezyk"] for w in wpisy} >= {"pl", "en"} or fmt != "docx"
        for w in wpisy:
            assert w["warstwa"] == "trudne" and w["przypadki"] == [przypadek] and w["posrednie"] == []
            assert w["format"] == fmt and w["id"].startswith(f"h-{P.SKROTY[przypadek]}-") and w["ostrzezenia"] == []
            assert w["ukryte"] == RODZAJE[fmt] and (cel / w["plik"]).is_file()
            ukryte = [g for g in w["gold_plik"] if g["id"].startswith("u.")]
            assert ukryte and all(g["miejsce"] == U.MIEJSCA[_rodzaj_wartosci(w, g)] for g in ukryte)
            # tekst poziomu 1 bez zmian: wartości ukrytych nie ma w gold_tekst ani w .txt
            tekst = (cel / w["plik_txt"]).read_text(encoding="utf-8")
            assert not any(g["wartosc_id"].startswith("u.") for g in w["gold_tekst"])
            assert not any(g["tekst"] in tekst for g in ukryte if g["kategoria"] == "OSOBA" and len(g["tekst"]) > 8)


def _rodzaj_wartosci(w: dict, g: dict) -> str:
    """Rodzaj elementu (`<format>.<rodzaj>`) z identyfikatora `u.<rodzaj>.<pole>#n`."""
    krotki = g["id"].split(".")[1]
    kandydaci = [r for r in RODZAJE[w["format"]] if r.split(".", 1)[1] == krotki]
    assert len(kandydaci) == 1, (g["id"], kandydaci)
    return kandydaci[0]


def test_wartosci_ukryte_nie_dziela_tokenow_z_trescia(warstwa):
    for przypadek, (cel, wpisy) in warstwa.items():
        for w in wpisy:
            widoczne = {t for g in w["gold_plik"] if not g["id"].startswith("u.") and g["kategoria"] == "OSOBA"
                        for t in U.tokeny(g["tekst"])}
            osoby = {g["id"]: U.tokeny(g["tekst"]) for g in w["gold_plik"] if g["id"].startswith("u.") and g["kategoria"] == "OSOBA"
                     and not g["id"].startswith("u.zakladka")}
            for tokeny in osoby.values():
                assert not (tokeny & widoczne), (w["id"], tokeny & widoczne)


def test_determinizm_i_trzon_nietkniety(tmp_path, warstwa):
    cel, wpisy = warstwa[P.UKRYTA_XLSX]
    drugi = trudne.zbuduj_przypadek(tmp_path, P.UKRYTA_XLSX, 10, procesy=1)
    assert drugi == wpisy and [w["sha256"] for w in drugi] == [w["sha256"] for w in wpisy]
    assert {w["sha256"] for w in wpisy} and len({w["sha256"] for w in wpisy}) == 10


def test_plan_h3_jeden_format():
    for przypadek, fmt in P.FORMAT_PRZYPADKU.items():
        plan = trudne.zaplanuj_przypadek(przypadek, 30)
        assert len(plan) == 30 and {p.format for p in plan} == {fmt}
        assert all(p.id.startswith(f"h-{P.SKROTY[przypadek]}-") for p in plan)
        assert plan == trudne.zaplanuj_przypadek(przypadek, 30)


# ============================================================================= pakiet OOXML poprawny
def sprawdz_pakiet(plik: Path) -> None:
    """ZIP bez błędów, każda część XML parsuje się, każda część ma typ zawartości, każda relacja wewnętrzna ma cel."""
    with zipfile.ZipFile(plik) as z:
        assert z.testzip() is None
        nazwy = z.namelist()
        assert len(nazwy) == len(set(nazwy))
        for n in nazwy:
            if n.endswith((".xml", ".rels", ".vml")):
                etree.fromstring(z.read(n))
        ct = etree.fromstring(z.read("[Content_Types].xml"))
        domyslne = {e.get("Extension").lower() for e in ct.findall("ct:Default", NS)}
        nadpisane = {e.get("PartName") for e in ct.findall("ct:Override", NS)}
        assert not [n for n in nazwy if n != "[Content_Types].xml" and "/" + n not in nadpisane
                    and n.rsplit(".", 1)[-1].lower() not in domyslne], "część bez typu zawartości"
        assert not [p for p in nadpisane if p[1:] not in nazwy], "typ zawartości nieistniejącej części"
        for n in nazwy:
            if not n.endswith(".rels"):
                continue
            zrodlo = posixpath.dirname(posixpath.dirname(n))
            rels = etree.fromstring(z.read(n))
            ids = [e.get("Id") for e in rels]
            assert len(ids) == len(set(ids)), n
            for e in rels:
                if e.get("TargetMode") == "External":
                    continue
                cel = e.get("Target").lstrip("/") if e.get("Target").startswith("/") else posixpath.normpath(posixpath.join(zrodlo, e.get("Target")))
                assert cel in nazwy, (n, e.get("Target"))


@pytest.mark.parametrize("przypadek,i", _wpisy())
def test_pakiet_poprawny(warstwa, przypadek, i):
    cel, wpisy = warstwa[przypadek]
    sprawdz_pakiet(cel / wpisy[i]["plik"])


@pytest.mark.skipif(shutil.which("soffice") is None, reason="brak LibreOffice")
@pytest.mark.parametrize("przypadek", P.H3)
def test_libreoffice_konwertuje_do_pdf(warstwa, przypadek, tmp_path):
    cel, wpisy = warstwa[przypadek]
    for w in wpisy[:2]:
        wynik = subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(tmp_path), str(cel / w["plik"])],
                               capture_output=True, timeout=180, env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"})
        pdf = tmp_path / (Path(w["plik"]).stem + ".pdf")
        assert wynik.returncode == 0 and pdf.is_file() and pdf.stat().st_size > 1000, wynik.stderr[-300:]


# ============================================================================= niezależny czytnik: wartość jest tam, gdzie ma być
def _wartosci(w: dict, krotki: str, pole: str | None = None) -> list[str]:
    """Teksty wartości gold elementu `u.<krotki>.*` (unikalne id, w kolejności), opcjonalnie tylko pole `pole`."""
    wynik, widziane = [], set()
    for g in w["gold_plik"]:
        m = re.fullmatch(rf"u\.{krotki}\.(\w+)#\d+", g["id"])
        if m and g["id"] not in widziane and (pole is None or m.group(1) == pole):
            widziane.add(g["id"])
            wynik.append(g["tekst"])
    assert wynik, (w["id"], krotki)
    return wynik


def _xml(z: zipfile.ZipFile, nazwa: str) -> etree._Element:
    return etree.fromstring(z.read(nazwa))


def _tekst(el) -> str:
    return "".join(el.itertext())


def _rels(z: zipfile.ZipFile, zrodlo: str) -> dict[str, str]:
    """Typ relacji (końcówka) -> lista celów po spłaszczeniu: {Id: (typ, cel w pakiecie)}."""
    nazwa = posixpath.join(posixpath.dirname(zrodlo), "_rels", posixpath.basename(zrodlo) + ".rels")
    return {e.get("Id"): (e.get("Type").rsplit("/", 1)[-1],
                          e.get("Target").lstrip("/") if e.get("Target").startswith("/")
                          else posixpath.normpath(posixpath.join(posixpath.dirname(zrodlo), e.get("Target"))))
            for e in _xml(z, nazwa)}


def _sprawdz_docx(plik: Path, w: dict) -> None:
    with zipfile.ZipFile(plik) as z:
        dok = _xml(z, "word/document.xml")
        rel = _rels(z, "word/document.xml")
        (osoba, email) = _wartosci(w, "vanish")
        ukryte = [r for r in dok.iterfind(".//w:r", NS) if r.find("w:rPr/w:vanish", NS) is not None]
        assert any(osoba in _tekst(r) and email in _tekst(r.getparent()) for r in ukryte)
        for kod, krotki in (("AUTHOR", "pole_author"), ("MERGEFIELD", "pole_mergefield"), ("DOCPROPERTY", "pole_docproperty")):
            (wartosc,) = _wartosci(w, krotki)
            instr = [i.text for i in dok.iterfind(".//w:instrText", NS) if kod in i.text and wartosc in i.text]
            wyniki = [t for t in dok.iterfind(".//w:t", NS) if t.text == wartosc]
            assert len(instr) == 1 and len(wyniki) == 1, (krotki, wartosc)
        pole = _wartosci(w, "pole_tekstowe")
        okna = dok.findall(".//w:txbxContent", NS)
        assert len(okna) == 2 and all(all(p in _tekst(o) for p in pole) for o in okna)    # wps + VML
        assert dok.find(".//mc:AlternateContent", NS) is not None
        (opis, tytul) = _wartosci(w, "alt_text")
        doc_pr = [e for e in dok.iterfind(".//wp:docPr", NS) if opis in (e.get("descr") or "")]
        assert len(doc_pr) == 1 and doc_pr[0].get("title") == tytul
        (zakladka,) = _wartosci(w, "zakladka")
        assert [e.get(f"{{{NS['w']}}}name") for e in dok.iterfind(".//w:bookmarkStart", NS)].count(zakladka) == 1
        assert re.fullmatch(r"\w+", zakladka) and len(zakladka) <= 40
        nazwa_xml = [c for t, c in rel.values() if t == "customXml" and "item" in c]
        tresc = "".join(_tekst(_xml(z, c)) for c in nazwa_xml)
        assert all(v in tresc for v in _wartosci(w, "custom_xml"))
        assert any(c.startswith("customXml/item") and c not in ("customXml/item1.xml",) for c in nazwa_xml)
        wykresy = [c for t, c in rel.values() if t == "chart"]
        assert len(wykresy) == 1
        wykres = _xml(z, wykresy[0])
        v = [e.text for e in wykres.iterfind(".//c:v", NS)]
        seria, *kategorie = _wartosci(w, "wykres")
        assert seria in v[0] and all(k in v for k in kategorie) and wykres.find(".//c:tx//c:v", NS).text == seria
        assert dok.find(".//c:chart", NS) is not None and dok.find(".//c:chart", NS).get(f"{{{NS['r']}}}id") in rel
        osadzone = [c for t, c in rel.values() if t == "package"]
        assert len(osadzone) == 1
        arkusz = load_workbook(io.BytesIO(z.read(osadzone[0]))).active
        komorki = {str(c.value) for r in arkusz.iter_rows() for c in r}
        assert set(_wartosci(w, "obiekt")) <= komorki
        assert dok.find(".//{urn:schemas-microsoft-com:office:office}OLEObject") is not None
        sect = dok.find("w:body/w:sectPr", NS)
        assert sect.find("w:titlePg", NS) is not None
        pierwszy = [e for e in sect.iterfind("w:headerReference", NS) if e.get(f"{{{NS['w']}}}type") == "first"]
        assert len(pierwszy) == 1
        naglowek = _tekst(_xml(z, rel[pierwszy[0].get(f"{{{NS['r']}}}id")][1]))
        assert all(v in naglowek for v in _wartosci(w, "naglowek_pierwszej_strony"))
        przypisy = _xml(z, "word/endnotes.xml")
        ref = dok.find(".//w:endnoteReference", NS).get(f"{{{NS['w']}}}id")
        notka = [n for n in przypisy.iterfind("w:endnote", NS) if n.get(f"{{{NS['w']}}}id") == ref]
        assert len(notka) == 1 and all(v in _tekst(notka[0]) for v in _wartosci(w, "przypis_koncowy"))
        assert dok.find("w:body/w:sectPr", NS) is dok.find("w:body", NS)[-1]


def _sheet_xml(z: zipfile.ZipFile, nazwa_arkusza: str) -> tuple[etree._Element, etree._Element]:
    skoroszyt = _xml(z, "xl/workbook.xml")
    rel = _rels(z, "xl/workbook.xml")
    s = [e for e in skoroszyt.iterfind(".//s:sheet", NS) if e.get("name") == nazwa_arkusza][0]
    return s, _xml(z, rel[s.get(f"{{{NS['r']}}}id")][1])


def _sprawdz_xlsx(plik: Path, w: dict) -> None:
    with zipfile.ZipFile(plik) as z:
        skoroszyt = _xml(z, "xl/workbook.xml")
        rel = _rels(z, "xl/workbook.xml")
        pierwszy = skoroszyt.find(".//s:sheet", NS)
        arkusz1 = _xml(z, rel[pierwszy.get(f"{{{NS['r']}}}id")][1])
        wiersze = {int(r.get("r")): r for r in arkusz1.iterfind(".//s:row", NS)}
        # ukryty wiersz
        wartosci = _wartosci(w, "wiersz_ukryty")
        ukryty = [r for r in wiersze.values() if r.get("hidden") == "1"]
        assert len(ukryty) == 1 and [_tekst(c) for c in ukryty[0].iterfind("s:c", NS)] == wartosci
        # ukryta kolumna
        kolumna = [c for c in arkusz1.iterfind(".//s:col", NS) if c.get("hidden") == "1"]
        assert len(kolumna) == 1 and kolumna[0].get("min") == kolumna[0].get("max")
        lit = _kolumna_litera(int(kolumna[0].get("min")))
        w_kolumnie = [_tekst(c) for c in arkusz1.iterfind(".//s:c", NS) if re.fullmatch(lit + r"\d+", c.get("r"))]
        assert set(_wartosci(w, "kolumna_ukryta")) <= set(w_kolumnie)
        # arkusze hidden i veryHidden
        for stan, krotki in (("hidden", "arkusz_hidden"), ("veryHidden", "arkusz_veryhidden")):
            s = [e for e in skoroszyt.iterfind(".//s:sheet", NS) if e.get("state") == stan and e.get("name") in ("Dane_robocze", "Archiwum_systemowe")]
            assert len(s) == 1
            tresc = _tekst(_xml(z, rel[s[0].get(f"{{{NS['r']}}}id")][1]))
            assert all(v in tresc for v in _wartosci(w, krotki))
        # pivotCache: definicja i rekordy
        (rid,) = [e.get(f"{{{NS['r']}}}id") for e in skoroszyt.iterfind(".//s:pivotCache", NS)]
        definicja_nazwa = rel[rid][1]
        definicja = _xml(z, definicja_nazwa)
        rekordy = _xml(z, _rels(z, definicja_nazwa)[definicja.get(f"{{{NS['r']}}}id")][1])
        pelne = _wartosci(w, "pivot", "pelne")
        rach = _wartosci(w, "pivot", "rachunek")
        assert [e.get("v") for e in definicja.iterfind(".//s:sharedItems/s:s", NS)] == pelne
        assert [e.get("v") for e in rekordy.iterfind(".//s:r/s:s", NS)] == rach
        # nazwa zdefiniowana, walidacja, formuła
        (nazwa,) = [e for e in skoroszyt.iterfind(".//s:definedName", NS) if e.get("name") == "Klient_glowny"]
        assert nazwa.text == '"' + _wartosci(w, "nazwa")[0] + '"'
        (dv,) = arkusz1.iterfind(".//s:dataValidation", NS)
        assert dv.get("type") == "list" and dv.find("s:formula1", NS).text == '"' + ",".join(_wartosci(w, "walidacja")) + '"'
        (wartosc,) = _wartosci(w, "formula")
        komorki = [c for c in arkusz1.iterfind(".//s:c", NS) if c.find("s:f", NS) is not None]
        assert len(komorki) == 1 and komorki[0].find("s:v", NS).text == wartosc
        formula = komorki[0].find("s:f", NS).text
        assert "&" in formula and "".join(re.findall(r'"([^"]*)"', formula)) == wartosc
        # komentarz
        (komentarz,) = [n for n in z.namelist() if re.fullmatch(r"xl/comments\d+\.xml", n)]
        assert all(v in _tekst(_xml(z, komentarz)) for v in _wartosci(w, "komentarz"))
        assert any(n.endswith(".vml") for n in z.namelist())


def _kolumna_litera(n: int) -> str:
    from openpyxl.utils import get_column_letter
    return get_column_letter(n)


def _sprawdz_pptx(plik: Path, w: dict) -> None:
    with zipfile.ZipFile(plik) as z:
        prez = _xml(z, "ppt/presentation.xml")
        szerokosc = int(prez.find(".//p:sldSz", NS).get("cx"))
        slajdy = sorted(n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n))
        tresci = {n: _xml(z, n) for n in slajdy}
        # notatki prelegenta
        notatki = [n for n in z.namelist() if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", n)]
        assert len(notatki) == 1 and all(v in _tekst(_xml(z, notatki[0])) for v in _wartosci(w, "notatki"))
        # slajd ukryty
        ukryte = [n for n, x in tresci.items() if x.get("show") == "0"]
        assert len(ukryte) == 1 and all(v in _tekst(tresci[ukryte[0]]) for v in _wartosci(w, "slajd_ukryty"))
        # kształt poza slajdem
        poza = [sp for x in tresci.values() for sp in x.iterfind(".//p:sp", NS)
                if sp.find(".//a:off", NS) is not None and int(sp.find(".//a:off", NS).get("x")) >= szerokosc]
        assert len(poza) == 1 and all(v in _tekst(poza[0]) for v in _wartosci(w, "poza_slajdem"))
        # alt text
        (opis,) = _wartosci(w, "alt_text")
        assert len([e for x in tresci.values() for e in x.iterfind(".//p:pic//p:cNvPr", NS) if opis in (e.get("descr") or "")]) == 1
        # komentarze
        komentarze = [n for n in z.namelist() if re.fullmatch(r"ppt/comments/comment\d+\.xml", n)]
        assert len(komentarze) == 1 and all(v in _tekst(_xml(z, komentarze[0])) for v in _wartosci(w, "komentarz"))
        assert z.read("ppt/commentAuthors.xml")


SPRAWDZ = {"docx": _sprawdz_docx, "xlsx": _sprawdz_xlsx, "pptx": _sprawdz_pptx}


@pytest.mark.parametrize("przypadek,i", _wpisy())
def test_gold_ukryty_obecny_w_pliku_niezaleznym_czytnikiem(warstwa, przypadek, i):
    cel, wpisy = warstwa[przypadek]
    w = wpisy[i]
    SPRAWDZ[w["format"]](cel / w["plik"], w)


def test_krotnosc_gold_odpowiada_zapisom_w_pliku(warstwa):
    for przypadek, (cel, wpisy) in warstwa.items():
        for w in wpisy:
            ids = [g["id"] for g in w["gold_plik"] if g["id"].startswith("u.")]
            ile = {i: ids.count(i) for i in set(ids)}
            for rodzaj, k in U.KROTNOSC.items():
                if rodzaj.startswith(w["format"]):
                    assert all(n == k for i, n in ile.items() if i.startswith(f"u.{rodzaj.split('.', 1)[1]}.")), (w["id"], rodzaj)


# ============================================================================= sędzia widzi treść ukrytą
CZESC_SEDZIEGO = {  # rodzaj -> fragment nazwy części, w której sędzia ma znaleźć wartość
    "docx.vanish": "word/document.xml", "docx.pole_author": "word/document.xml", "docx.pole_mergefield": "word/document.xml",
    "docx.pole_docproperty": "word/document.xml", "docx.pole_tekstowe": "word/document.xml", "docx.alt_text": "word/document.xml",
    "docx.zakladka": "word/document.xml", "docx.custom_xml": "customXml/item", "docx.wykres": "word/charts/chart",
    "docx.obiekt": "word/embeddings/", "docx.naglowek_pierwszej_strony": "word/header", "docx.przypis_koncowy": "word/endnotes.xml",
    "xlsx.wiersz_ukryty": "xl/worksheets/", "xlsx.kolumna_ukryta": "xl/worksheets/", "xlsx.arkusz_hidden": "xl/worksheets/",
    "xlsx.arkusz_veryhidden": "xl/worksheets/", "xlsx.pivot": "xl/pivotCache/", "xlsx.nazwa": "xl/workbook.xml",
    "xlsx.walidacja": "xl/worksheets/", "xlsx.formula": "xl/worksheets/", "xlsx.komentarz": "xl/comments",
    "pptx.notatki": "ppt/notesSlides/", "pptx.slajd_ukryty": "ppt/slides/", "pptx.poza_slajdem": "ppt/slides/",
    "pptx.alt_text": "ppt/slides/", "pptx.komentarz": "ppt/comments/",
}


@pytest.mark.parametrize("przypadek,i", _wpisy())
def test_sedzia_ekstrakcja_widzi_kazda_wartosc_ukryta(warstwa, przypadek, i):
    from pbench.sedzia.normalizacja import normalizuj
    cel, wpisy = warstwa[przypadek]
    w = wpisy[i]
    wyd = wydobadz(cel / w["plik"])
    assert wyd.status == "OK"
    for g in w["gold_plik"]:
        if not g["id"].startswith("u."):
            continue
        rodzaj = _rodzaj_wartosci(w, g)
        gdzie = [c.nazwa for c in wyd.czesci if CZESC_SEDZIEGO[rodzaj] in c.nazwa and normalizuj(g["tekst"]) in normalizuj(c.caly_tekst())]
        assert gdzie, (w["id"], g["id"], rodzaj)


# ============================================================================= sanity: oryginał / idealny / uczestnik widocznej treści
class WidocznaTresc(Maskowanie):
    """Idealny uczestnik, który nie widzi treści ukrytej: maskuje treść i metadane, elementy ukryte zostają."""

    def __call__(self, d):
        n = super().__call__(d)
        n.ukryte = Dokument.from_dict(d.to_dict()).ukryte
        return n


def _pozycja(w: dict, przypadek: str) -> trudne.PozycjaTrudna:
    return trudne.PozycjaTrudna(w["id"], w["jezyk"], w["typ"], w["format"], przypadek)


@pytest.mark.parametrize("przypadek,i", [(p, i) for p in P.H3 for i in (0, 1, 2, 5)])
def test_sanity_oryginal_idealny_i_widoczna_tresc(warstwa, tmp_path, przypadek, i):
    cel, wpisy = warstwa[przypadek]
    w = wpisy[i]
    ws = wartosci_wpisu(w)
    ukryte = {x.id for x in ws if x.id.startswith("u.")}
    orig = cel / w["plik"]
    a = ocen_plik(orig, orig, ws, leksykon={})
    assert a.status == "OK" and not a.niewykrywalne                  # tekst w XML nie jest „obrazowy” (cecha tekst_xml)
    assert ukryte <= {x[0] for x in a.wycieki} and not (ukryte & set(a.niejednoznaczne))     # oryginał: wszystko wycieka
    # idealny uczestnik (maskuje także treść ukrytą): 0 wycieków ukrytych
    ideal = tmp_path / "ideal"
    ideal.mkdir()
    r = trudne.generuj_dokument_trudny(_pozycja(w, przypadek), trudne.ZIARNO_TRUDNE, w["split"], ideal, maskuj=Maskowanie())
    b = ocen_plik(orig, ideal / r["plik"], ws, leksykon={})
    assert b.status == "OK" and b.integralnosc["otwiera_sie"]
    assert not [x for x in b.wycieki if x[0] in ukryte], b.wycieki[:3]
    assert not b.wycieki, b.wycieki[:3]
    sprawdz_pakiet(ideal / r["plik"])
    # uczestnik widocznej treści: wyciek dokładnie w elementach ukrytych
    naiwny = tmp_path / "naiwny"
    naiwny.mkdir()
    r = trudne.generuj_dokument_trudny(_pozycja(w, przypadek), trudne.ZIARNO_TRUDNE, w["split"], naiwny, maskuj=WidocznaTresc())
    c = ocen_plik(orig, naiwny / r["plik"], ws, leksykon={})
    wyciekly = {x[0] for x in c.wycieki}
    assert ukryte <= wyciekly
    # wartość jawna (zamaskowana w treści) może wyciec tylko częściowo i tylko w elemencie ukrytym, w którym wycieka wartość
    # ukryta o wspólnym słowie albo jego formie („Andreas” – „Andrea”, DE dopełniacz -s): uczestnik nie rusza elementów ukrytych,
    # a sędzia łączy formy tego samego słowa tą samą relacją co przy dopasowaniu (`plik._odmiany`)
    from pbench.sedzia.normalizacja import normalizuj
    from pbench.sedzia.plik import _odmiany
    teksty, jezyki = {}, {x.id: x.jezyk for x in ws}
    for x in ws:
        teksty.setdefault(x.id, []).extend(re.findall(r"\w+", normalizuj(x.tekst)))

    def wspolny_rdzen(i: str, j: str) -> bool:
        return any(s == t or t in _odmiany(s, jezyki[i]) or s in _odmiany(t, jezyki[j]) for s in teksty[i] for t in teksty[j])
    inne = [x for x in c.wycieki if x[0] not in ukryte]
    assert all(x[3] == "czesciowy" and any(y[2] == x[2] and wspolny_rdzen(x[0], y[0]) for y in c.wycieki if y[0] in ukryte)
               for x in inne), inne


def _naiwny_docx(zrodlo: Path, cel: Path, wartosci: list[str]) -> None:
    """Czyści tylko widoczny tekst `w:t` akapitów w `document.xml` (poza tekstem ukrytym i polami tekstowymi)."""
    with zipfile.ZipFile(zrodlo) as zin, zipfile.ZipFile(cel, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            dane = zin.read(info.filename)
            if info.filename == "word/document.xml":
                root = etree.fromstring(dane)
                for p in root.iterfind(".//w:p", NS):
                    if p.xpath("ancestor::w:txbxContent", namespaces=NS):
                        continue
                    ts = [t for t in p.iterfind(".//w:t", NS) if t.xpath("not(ancestor::w:r/w:rPr/w:vanish)", namespaces=NS)]
                    tekst = "".join(t.text or "" for t in ts)
                    nowy = tekst
                    for v in sorted(wartosci, key=len, reverse=True):
                        nowy = nowy.replace(v, "X" * len(v))
                    if ts and nowy != tekst:
                        ts[0].text = nowy
                        for t in ts[1:]:
                            t.text = ""
                dane = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            zout.writestr(info.filename, dane)


def test_naiwny_docx_czyszczacy_tylko_document_xml_zostawia_wyciek_w_ukrytych(warstwa, tmp_path):
    cel, wpisy = warstwa[P.UKRYTA_DOCX]
    for w in wpisy[:4]:
        ws = wartosci_wpisu(w)
        orig = cel / w["plik"]
        widoczne = [x.tekst for x in ws if not x.id.startswith("u.") and x.miejsce in ("tresc", "tabela")]
        wynik = tmp_path / w["plik"]
        _naiwny_docx(orig, wynik, widoczne)
        a = ocen_plik(orig, wynik, ws, leksykon={})
        wyciekly = {x[0] for x in a.wycieki}
        assert {x.id for x in ws if x.id.startswith("u.")} <= wyciekly
        # wartości widoczne zostały zamaskowane w document.xml (inne części – nagłówek, obraz podpisu – naiwny uczestnik zostawia)
        assert not [x for x in a.wycieki if not x[0].startswith("u.") and x[2] == "word/document.xml"], a.wycieki


def test_bez_cechy_tekst_xml_wartosc_obraz_bylaby_niewykrywalna(warstwa):
    """Powód rozszerzenia sędziego: alt text oznaczony `obraz` bez cechy `tekst_xml` trafia do `niewykrywalne` (OCR oryginału
    nie widzi pikseli z tekstem) – z cechą jest szukany w tekście części pakietu."""
    cel, wpisy = warstwa[P.UKRYTA_DOCX]
    w = wpisy[0]
    ws = wartosci_wpisu(w)
    bez = [Wartosc.from_dict({**g.to_dict(), "cechy": []}) if g.id.startswith("u.alt_text.pelne") else g for g in ws]
    orig = cel / w["plik"]
    assert ocen_plik(orig, orig, bez, leksykon={}).niewykrywalne == ["u.alt_text.pelne#1"]
    assert ocen_plik(orig, orig, ws, leksykon={}).niewykrywalne == []
