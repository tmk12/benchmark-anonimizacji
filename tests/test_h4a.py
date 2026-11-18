"""Warstwa trudnych przypadków, zadanie H4a (spec §11 pkt 1 – część PDF, pkt 6): `ukryta_pdf`, `znaki_zerowej_szerokosci`,
`rtl`, `zepsuty_tounicode`, `przeniesienia`, `dwie_kolumny`, `obrocone_strony`, `skan_pieczatki`, `zrzut_ekranu`, `znak_wodny`.
Rejestr, plan, manifest, determinizm, obecność każdej wartości w pliku (niezależne czytniki: pypdfium2, pikepdf, zipfile + lxml,
Tesseract – bez kodu sędziego), rozszerzenia sędziego (sklejanie przeniesień, widok RTL, OCR stron każdego PDF-u, zbiory
dokumentu z samego oryginału, krotność w OCR, obrót stron w OCR, obrazy w formularzach nakładek) i sanity: oryginał wycieka,
idealny uczestnik nie, „naiwny” uczestnik (zmienia tylko to, co widzi) zostawia wyciek dokładnie w elementach przypadku."""
from __future__ import annotations

import dataclasses
import hashlib
import io
import json
import re
import shutil
import subprocess
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path

import pikepdf
import pypdfium2 as pdfium
import pytest
from lxml import etree
from PIL import Image

from pbench import korpus, ocr as ocr_modul, przypadki as P, trudne, trudne_pliki as TP, trudne_ukryta as U
from pbench.model import Dokument, Wartosc
from pbench.sedzia import ekstrakcja, normalizacja, obrazy, plik as sedzia_plik
from pbench.sedzia.ekstrakcja import wydobadz
from pbench.sedzia.normalizacja import normalizuj, polacz_przeniesienia
from pbench.render.pdf import FONTY
from pbench.sedzia.plik import ocen_plik, warstwa_tekstowa_zepsuta
from pbench.sedzia.sanity import Maskowanie, wartosci_wpisu

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
V = "{urn:schemas-microsoft-com:vml}"
N_DOKUMENTOW = 6
#: Środek między kolumnami strony A4 w układzie `dwie_kolumny` (pt): kolumny 71–288 i 306–523.
SRODEK_KOLUMN = 297.0
#: Przypadki, których wartości w pliku są dopiskami obrazowymi / elementami `Dokument.ukryte` (a nie samym tekstem).
Z_UKRYTYMI = (P.UKRYTA_PDF, P.SKAN_PIECZATKI, P.ZRZUT_EKRANU, P.ZNAK_WODNY)


# ============================================================================= rejestr, plan
def test_rejestr_h4a():
    assert len(P.H4A) == 10 and set(P.H4A) <= set(P.PRZYPADKI) and P.UKRYTA_PDF in P.H4A
    assert set(P.FORMATY_PRZYPADKU) == set(P.H4A) | set(P.H4B)
    assert all(set(P.FORMATY_PRZYPADKU[p]) <= {"docx", "pdf", "skan"} for p in P.H4A)
    assert {P.SKROTY[p] for p in P.H4A} == {"uf", "zw", "rt", "zt", "pr", "dk", "os", "sp", "ze", "zn"}
    assert len(set(P.SKROTY.values())) == len(P.SKROTY)
    assert not set(P.H4A) & (set(P.H1) | set(P.H2) | set(P.H3) - {P.UKRYTA_PDF})
    for przypadek in P.H4A:
        assert przypadek in trudne.GENERATORY_H4A or przypadek in trudne.GENERATORY_H3
        assert trudne._pary(przypadek)


def test_mapowanie_miejsc_h4a_istniejace_miejsca_i_wagi():
    wagi = json.loads(Path("metodyka/wagi_punktow.json").read_text(encoding="utf-8"))["wagi_miejsc"]
    nowe = {k: v for k, v in U.MIEJSCA.items() if k.startswith(("pdf.", "obraz.", "znak_wodny."))}
    assert set(nowe) == {"pdf.zaczernienie", "pdf.warstwa_ocr", "obraz.pieczatka", "obraz.zrzut_ekranu", "znak_wodny.pdf",
                         "znak_wodny.docx"}
    assert set(nowe.values()) <= set(wagi)                      # tylko istniejące miejsca; wagi zamrożone
    assert nowe["znak_wodny.docx"] == "naglowek" and nowe["znak_wodny.pdf"] == "obraz"      # wg briefu
    assert nowe["pdf.zaczernienie"] == nowe["pdf.warstwa_ocr"] == "metadane"


@pytest.mark.parametrize("przypadek", P.H4A)
def test_plan_h4a(przypadek):
    plan = trudne.zaplanuj_przypadek(przypadek, 30)
    assert len(plan) == 30 and plan == trudne.zaplanuj_przypadek(przypadek, 30) and plan == sorted(plan, key=lambda p: p.id)
    dozwolone = set(P.FORMATY_PRZYPADKU[przypadek])
    assert {p.format for p in plan} == dozwolone              # każdy dozwolony format występuje
    for p in plan:
        assert re.fullmatch(rf"h-{P.SKROTY[przypadek]}-{p.jezyk}-{p.typ}-\d{{4}}", p.id) and p.format in trudne.formaty_dla(p.jezyk, p.typ)
    assert len({p.id for p in plan}) == 30 and {p.jezyk for p in plan} >= {"pl", "en"}


# ============================================================================= generacja
@pytest.fixture(scope="module")
def warstwa(tmp_path_factory) -> dict[str, tuple[Path, list[dict]]]:
    wynik = {}
    for przypadek in P.H4A:
        cel = tmp_path_factory.mktemp(przypadek)
        wynik[przypadek] = (cel, trudne.zbuduj_przypadek(cel, przypadek, 4 if przypadek == P.ZRZUT_EKRANU else N_DOKUMENTOW, procesy=1))
    return wynik


def _dok(warstwa, przypadek: str, i: int) -> tuple[Path, dict, Path]:
    cel, wpisy = warstwa[przypadek]
    return cel, wpisy[i], cel / wpisy[i]["plik"]


def test_manifest_h4a(warstwa):
    for przypadek, (cel, wpisy) in warstwa.items():
        assert [json.loads(l) for l in (cel / "manifest.jsonl").read_text(encoding="utf-8").splitlines()] == wpisy
        for w in wpisy:
            assert w["warstwa"] == "trudne" and w["przypadki"] == [przypadek] and w["posrednie"] == []
            assert w["format"] in P.FORMATY_PRZYPADKU[przypadek] and w["id"].startswith(f"h-{P.SKROTY[przypadek]}-")
            assert w["ostrzezenia"] == [] and (cel / w["plik"]).is_file()
            assert hashlib.sha256((cel / w["plik"]).read_bytes()).hexdigest() == w["sha256"]
            assert ("ukryte" in w) == (przypadek in Z_UKRYTYMI)
    assert {w["format"] for w in warstwa[P.OBROCONE_STRONY][1]} <= {"pdf", "skan"}
    assert {w["tounicode"] for w in warstwa[P.ZEPSUTY_TOUNICODE][1]} <= set(TP.pliki_pdf.TRYBY_TOUNICODE)


def test_determinizm_i_trzon_nietkniety(tmp_path, warstwa):
    for przypadek in P.H4A:
        cel, wpisy = warstwa[przypadek]
        drugi = tmp_path / przypadek
        w2 = trudne.zbuduj_przypadek(drugi, przypadek, len(wpisy), procesy=1)
        assert [w["sha256"] for w in w2] == [w["sha256"] for w in wpisy], przypadek
        assert (drugi / "manifest.jsonl").read_bytes() == (cel / "manifest.jsonl").read_bytes()
        shutil.rmtree(drugi)


# ============================================================================= czytniki niezależne od sędziego
def tekst_pdf(plik: Path) -> list[str]:
    """Tekst stron wg PDFium (bez zmian: z kodem znaków, jakie PDFium oddaje)."""
    d = pdfium.PdfDocument(str(plik))
    try:
        return [d[i].get_textpage().get_text_range() for i in range(len(d))]
    finally:
        d.close()


def tekst_docx(plik: Path) -> str:
    with zipfile.ZipFile(plik) as z:
        return "".join("".join(etree.fromstring(z.read(n)).itertext()) for n in z.namelist() if n.startswith("word/") and n.endswith(".xml"))


# ----------------------------------------------------------------------------- znaki zerowej szerokości
ZW = ("\u200b", "\u200c", "\u200d", "\u2060", "\u00ad")


def test_zw_kazdy_znak_wewnatrz_wartosci_gold_i_w_pliku(warstwa):
    cel, wpisy = warstwa[P.ZNAKI_ZEROWEJ_SZEROKOSCI]
    assert {w["format"] for w in wpisy} == {"docx", "pdf"}
    for w in wpisy:
        zw = [g for g in w["gold_tekst"] if "zero_width" in g.get("cechy", ())]
        tekst = (cel / w["plik_txt"]).read_text(encoding="utf-8")
        oczekiwane = set(ZW) - ({"\u00ad"} if w["format"] == "pdf" else set())   # w PDF miękki łącznik byłby widoczny (DejaVu)
        assert {z for g in zw for z in ZW if z in g["tekst"]} == oczekiwane, w["id"]
        for g in zw:
            assert tekst[g["start"]:g["end"]] == g["tekst"]
            assert any(z in g["tekst"][1:-1] for z in ZW) and g["kategoria"] in TP.KATEGORIE_ZW   # wewnątrz wartości PII
            assert all(g["tekst"][i - 1].isalnum() and g["tekst"][i + 1].isalnum() for i, c in enumerate(g["tekst"]) if c in ZW and 0 < i < len(g["tekst"]) - 1)
        plik = cel / w["plik"]
        calosc = tekst_docx(plik) if w["format"] == "docx" else "\n".join(tekst_pdf(plik))
        bialy = lambda t: re.sub(r"\s+", " ", t)           # PDF łamie wiersze (PDFium oddaje \r\n zamiast spacji)
        for g in zw:
            surowy = g["tekst"] if w["format"] == "docx" else g["tekst"].replace("\u00ad", "")   # PDFium pomija miękki łącznik
            assert bialy(surowy) in bialy(calosc), (w["id"], g["tekst"])                  # tekst dokładnie z dokumentu


def test_zw_normalizacja_sedziego_usuwa_znaki():
    assert normalizuj("Kow\u200balski \u200cJan Ko\u200dw\u2060a\u00adlski") == "kowalski jan kowalski"
    assert normalizacja.same_alnum("8501\u200b0112\u200c345") == "85010112345"


# ----------------------------------------------------------------------------- RTL
def test_rtl_wartosci_i_znaki_sterujace(warstwa):
    cel, wpisy = warstwa[P.RTL]
    assert {w["format"] for w in wpisy} == {"docx", "pdf"}
    for w in wpisy:
        rtl = [g for g in w["gold_tekst"] if "rtl" in g.get("cechy", ())]
        assert {g["kategoria"] for g in rtl} == {"ORGANIZACJA", "ADRES", "OSOBA", "EMAIL"}
        tekst = (cel / w["plik_txt"]).read_text(encoding="utf-8")
        for g in rtl:
            assert tekst[g["start"]:g["end"]] == g["tekst"]                          # gold = zapis jak w strumieniu znaków
        he_ar = [g["tekst"] for g in rtl if g["kategoria"] in ("ORGANIZACJA", "ADRES")]
        assert all(re.search("[֐-ۿ]", t) for t in he_ar)
        email = next(g["tekst"] for g in rtl if g["kategoria"] == "EMAIL")
        domena = U.DOMENY_UKRYTYCH[w["jezyk"]]
        assert email.startswith(domena[::-1]) and email[::-1].endswith("@" + domena)               # zapis odwrócony
        otwarcie, zamkniecie = TP.IZOLACJA_RTL[w["format"]]
        assert f"{otwarcie}{next(g['tekst'] for g in rtl if g['kategoria'] == 'OSOBA')}{zamkniecie}" in tekst
        assert f"{TP.RLO}{email}{TP.PDF_RLO}" in tekst
        plik = cel / w["plik"]
        if w["format"] == "docx":
            calosc = tekst_docx(plik)
            assert email in calosc and otwarcie in calosc and all(t in calosc for t in he_ar)      # XML: porządek logiczny
            continue
        # PDF: glify w kolejności wizualnej (jak w Wordzie/LibreOffice); gold z pliku = to, co widać (e-mail pod RLO: prosto)
        gold_pdf = {g["kategoria"]: g["tekst"] for g in w["gold_plik"] if "rtl" in g.get("cechy", ())}
        assert gold_pdf["EMAIL"] == email[::-1] and gold_pdf["EMAIL"].endswith("@" + domena)
        assert gold_pdf["ORGANIZACJA"] == next(g["tekst"] for g in rtl if g["kategoria"] == "ORGANIZACJA")
        widok = "\n".join(tekst_pdf(plik))
        assert gold_pdf["EMAIL"] in widok and gold_pdf["OSOBA"] in widok
        assert TP.RLO not in widok and zamkniecie not in widok and otwarcie not in widok     # sterowanie nie trafia do strumienia
        assert _wyrazy_rtl(he_ar) <= _wyrazy_rtl_z_tekstu(widok)


def _wyrazy_rtl(wartosci: list[str]) -> set[str]:
    return {unicodedata.normalize("NFKC", x) for t in wartosci for x in re.findall(r"[\u0590-\u08ff\ufb1d-\ufdff\ufe70-\ufefc]+", t)}


def _wyrazy_rtl_z_tekstu(tekst: str) -> set[str]:
    """Wyrazy RTL tekstu w obu zapisach: logicznym (PDFium porządkuje bidi) i z literami odwróconymi (pdfminer: porządek wizualny)."""
    wyrazy = _wyrazy_rtl([tekst])
    return wyrazy | {x[::-1] for x in wyrazy}


def test_rtl_pdf_pierwsza_litera_logiczna_wyrazu_ma_najwieksze_x(warstwa):
    """Niezależny odczyt pozycji znaków (PDFium): w wyrazie RTL pierwsza litera logiczna stoi najbardziej na prawo (nie jest to
    pismo lustrzane – zapis w kolejności wizualnej z kształtowaniem liter)."""
    cel, wpisy = warstwa[P.RTL]
    sprawdzone = 0
    for w in (w for w in wpisy if w["format"] == "pdf"):
        d = pdfium.PdfDocument(str(cel / w["plik"]))
        try:
            strony = [d[i].get_textpage() for i in range(len(d))]
            for g in (g for g in w["gold_plik"] if g["kategoria"] in ("ORGANIZACJA", "ADRES") and "rtl" in g.get("cechy", ())):
                for wyraz in re.findall(r"[\u0590-\u08ff]{4,}", g["tekst"]):
                    for tp in strony:
                        i = tp.get_text_range().find(wyraz)
                        if i >= 0:
                            x = [tp.get_charbox(j)[0] for j in range(i, i + len(wyraz))]
                            assert x[0] > x[-1], (w["id"], wyraz, x)
                            sprawdzone += 1
                            break
                    else:
                        raise AssertionError((w["id"], wyraz))
        finally:
            d.close()
    assert sprawdzone >= 4


def test_rtl_pdfium_i_pdfminer_ten_sam_wynik_idealny_i_naiwny(warstwa, tmp_path):
    """Wynik przypadku nie zależy od parsera PDF: PDFium (porządkuje bidi) i pdfminer (porządek wizualny, formy prezentacyjne)
    odnajdują w pliku te same wartości (wyrazy RTL jako zbiór, e-mail i osoba tekstem): w oryginale i u naiwnego uczestnika
    (zostawia wartości z cechą `rtl`) wszystkie cztery, u idealnego (`Maskowanie`) żadnej."""
    pdfminer = pytest.importorskip("pdfminer.high_level")

    def znalezione(plik: Path, gold: list[dict], czytnik: str) -> frozenset[str]:
        tekst = "\n".join(tekst_pdf(plik)) if czytnik == "pdfium" else pdfminer.extract_text(str(plik))
        wynik = set()
        for g in gold:
            t = g["tekst"]
            if re.search("[֐-ۿ]", t):
                if _wyrazy_rtl([t]) <= _wyrazy_rtl_z_tekstu(tekst):
                    wynik.add(g["kategoria"])
            elif t in tekst:
                wynik.add(g["kategoria"])
        return frozenset(wynik)

    cel, wpisy = warstwa[P.RTL]
    for w in (w for w in wpisy if w["format"] == "pdf"):
        gold = [g for g in w["gold_plik"] if "rtl" in g.get("cechy", ())]
        wszystkie = frozenset({"ORGANIZACJA", "ADRES", "OSOBA", "EMAIL"})
        ideal = _uczestnik(P.RTL, w, tmp_path / f"i{w['id']}", Maskowanie())
        naiwny = _uczestnik(P.RTL, w, tmp_path / f"n{w['id']}", BezCechy("rtl"))
        for czytnik in ("pdfium", "pdfminer"):
            assert znalezione(cel / w["plik"], gold, czytnik) == wszystkie, (w["id"], czytnik)
            assert znalezione(naiwny, gold, czytnik) == wszystkie, (w["id"], czytnik)
            assert znalezione(ideal, gold, czytnik) == frozenset(), (w["id"], czytnik)


def test_rtl_widok_rtl_pomaga_dla_pdf_z_porzadkiem_logicznym(tmp_path):
    """`widok_rtl` zostaje: PDF zapisany przez narzędzie bez bidi (glify w porządku logicznym, jak w starym rendererze) PDFium
    oddaje z odwróconymi wyrazami – wartość RTL jest wtedy w tekście dopiero w widoku `widok_rtl`."""
    from reportlab.pdfgen import canvas
    from pbench.render import pdf as render_pdf
    wartosc = "שחר יזמות בע״מ"
    plik = tmp_path / "logiczny.pdf"
    c = canvas.Canvas(str(plik), invariant=1)
    c.setFont("DejaVuSans", 12)
    c.drawString(72, 700, "Kontrahent: " + wartosc)             # kolejność logiczna, od lewej do prawej, bez bidi
    c.save()
    [tekst] = tekst_pdf(plik)
    assert wartosc not in tekst
    widok = "\n".join(ekstrakcja.widok_rtl(tekst.splitlines()))
    assert all(wyraz in widok.split() for wyraz in wartosc.split())      # wyrazy rozpoznawalne (kolejność wyrazów zostaje odwrócona)
    assert render_pdf is not None      # import rejestruje czcionki DejaVu użyte wyżej


def test_rtl_widok_odwraca_wyrazy_z_litera_rtl_zostawia_cyfry_i_lacine():
    assert ekstrakcja.widok_rtl(["Anschrift: ةرانملا 52، ربونصلا"]) == ["Anschrift: المنارة 52، الصنوبر"]
    assert ekstrakcja.widok_rtl(["Nowak-Kowalski 2020 – 2021"]) == []


# ----------------------------------------------------------------------------- przeniesienia
def test_polacz_przeniesienia_nie_skleja_zwyklych_myslnikow():
    assert polacz_przeniesienia("Kowal-\nski") == "Kowalski"
    assert polacz_przeniesienia("Kowal-  \r\n  ski") == "Kowalski"
    assert polacz_przeniesienia("Kowal\ufffeski") == "Kowalski"                       # łącznik końca wiersza w PDFium
    assert polacz_przeniesienia("Nowak-Kowalski, 2020 - 2021, e-mail, PL61-1090") == "Nowak-Kowalski, 2020 - 2021, e-mail, PL61-1090"
    assert polacz_przeniesienia("Nowak -\nKowalski") == "Nowak -\nKowalski"          # myślnik oddzielony spacją to nie przeniesienie
    assert polacz_przeniesienia("rok\n2020") == "rok\n2020"


def test_przeniesienia_gold_z_dokumentu_w_txt_i_pdf(warstwa):
    cel, wpisy = warstwa[P.PRZENIESIENIA]
    for w in wpisy:
        zlamane = [g for g in w["gold_tekst"] if "przeniesienie" in g.get("cechy", ())]
        assert len(zlamane) >= 2 and w["format"] == "pdf"
        tekst = (cel / w["plik_txt"]).read_text(encoding="utf-8")
        strony = tekst_pdf(cel / w["plik"])
        calosc = "\n".join(strony)
        for g in zlamane:
            assert "\n" in g["tekst"] and tekst[g["start"]:g["end"]] == g["tekst"]
            # w PDF wartość jest naprawdę złamana: wyraz rozdzielony łącznikiem (PDFium: U+FFFE) albo nowy wiersz w rachunku
            if g["kategoria"] == "OSOBA":
                przed, po = g["tekst"].split("-\n")
                # ostatnie znaki części wyrazu przed łącznikiem (H6b: podział sylabiczny bywa po 2 literach – „Za-\npata” – a renderer
                # może zawinąć wiersz przed „Za”, więc spacja przed nią nie musi być w tym samym wierszu)
                assert re.search(re.escape(przed.split()[-1][-3:]) + r"[\ufffe\-]\s*" + re.escape(po[:3]), calosc), g["tekst"]
            else:
                assert normalizacja.same_alnum(g["tekst"]) in normalizacja.same_alnum(calosc)


# ----------------------------------------------------------------------------- dwie kolumny
def _kolumny_pdf(plik: Path) -> list[list[float]]:
    """Lewe krawędzie początków wierszy tekstu strony (pt) – po jednej liście na stronę."""
    d = pdfium.PdfDocument(str(plik))
    wynik = []
    try:
        for i in range(len(d)):
            tp = d[i].get_textpage()
            n = tp.count_chars()
            tekst = tp.get_text_range()
            x0s, poczatek = [], True
            for k in range(n):
                if tekst[k] in "\r\n":
                    poczatek = True
                    continue
                if poczatek and not tekst[k].isspace():
                    x0s.append(tp.get_charbox(k)[0])
                    poczatek = False
            wynik.append(x0s)
    finally:
        d.close()
    return wynik


def test_dwie_kolumny_pdf_i_docx(warstwa):
    cel, wpisy = warstwa[P.DWIE_KOLUMNY]
    assert {w["format"] for w in wpisy} == {"pdf", "docx"}
    for w in wpisy:
        plik = cel / w["plik"]
        assert w["kolumny"] == 2
        if w["format"] == "docx":
            with zipfile.ZipFile(plik) as z:
                sect = etree.fromstring(z.read("word/document.xml")).find(f"{W}body").find(f"{W}sectPr")
            cols = sect.find(f"{W}cols")
            assert cols is not None and cols.get(f"{W}num") == "2"
            potomki = [e.tag.split("}")[1] for e in sect]
            assert potomki.index("cols") > potomki.index("pgMar") and ("docGrid" not in potomki or potomki.index("cols") < potomki.index("docGrid"))
            assert not any(e.tag == f"{W}tbl" for e in etree.fromstring(zipfile.ZipFile(plik).read("word/document.xml")).iter())
            continue
        krawedzie = _kolumny_pdf(plik)
        # dwie kolumny: początki wierszy skupiają się wokół dwóch wartości x w obrębie kolumn tekstu
        for x0s in krawedzie[:1]:
            lewa = [x for x in x0s if x < SRODEK_KOLUMN]
            prawa = [x for x in x0s if x >= SRODEK_KOLUMN]
            assert len(lewa) >= 5 and len(prawa) >= 3, (w["id"], len(lewa), len(prawa))
        # wartości nie przechodzą między kolumnami: początek i koniec każdej wartości w tej samej kolumnie
        d = pdfium.PdfDocument(str(plik))
        try:
            strony = [d[i].get_textpage() for i in range(len(d))]
            for g in w["gold_plik"]:
                if g["miejsce"] not in ("tresc", "tabela") or len(g["tekst"]) < 6:
                    continue
                szukane = re.sub(r"\s+", " ", g["tekst"])
                for tp in strony:
                    szukacz = tp.search(szukane)
                    while (trafienie := szukacz.get_next()) is not None:
                        idx, ile = trafienie
                        if not 120 < tp.get_charbox(idx)[1] < 730:         # nagłówek i stopka papieru firmowego są na całą szerokość
                            continue
                        assert (tp.get_charbox(idx)[0] < SRODEK_KOLUMN) == (tp.get_charbox(idx + ile - 1)[2] < SRODEK_KOLUMN), (w["id"], g["tekst"])
        finally:
            d.close()


@pytest.mark.skipif(shutil.which("soffice") is None, reason="brak LibreOffice")
def test_dwie_kolumny_docx_libreoffice_konwertuje_do_pdf(warstwa, tmp_path):
    cel, wpisy = warstwa[P.DWIE_KOLUMNY]
    w = next(w for w in wpisy if w["format"] == "docx")
    r = subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(tmp_path), str(cel / w["plik"])],
                       capture_output=True, timeout=180, env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"})
    pdf = tmp_path / (Path(w["plik"]).stem + ".pdf")
    assert pdf.is_file(), r.stderr[:300]
    lewa_prawa = [x for x0s in _kolumny_pdf(pdf)[:1] for x in x0s]
    assert any(x < SRODEK_KOLUMN for x in lewa_prawa) and any(x >= SRODEK_KOLUMN for x in lewa_prawa)


# ----------------------------------------------------------------------------- obrócone strony
def test_obrocone_strony_pdf_i_skan(warstwa):
    cel, wpisy = warstwa[P.OBROCONE_STRONY]
    assert {w["format"] for w in wpisy} == {"pdf", "skan"}
    for w in wpisy:
        katy = w["obroty"]
        assert set(katy) <= {0, 90, 180, 270} and any(katy)
        with pikepdf.open(cel / w["plik"]) as pdf:
            assert len(pdf.pages) == len(katy)
            for strona, kat in zip(pdf.pages, katy):
                if w["format"] == "pdf":
                    assert int(strona.get("/Rotate", 0)) == kat
                else:
                    assert int(strona.get("/Rotate", 0)) == 0                 # skan obrócony fizycznie
                    szer, wys = float(strona.MediaBox[2]), float(strona.MediaBox[3])
                    assert (szer > wys) == (kat in (90, 270))
                    im = pikepdf.PdfImage(next(iter(strona.Resources.XObject.values())))
                    assert (im.width > im.height) == (kat in (90, 270))
        if w["format"] == "skan":
            for o in w["gold_obrazy"]:
                for wid, (x0, y0, x1, y1) in o["ramki"]:
                    assert 0 <= x0 < x1 and 0 <= y0 < y1                          # ramki przeliczone na obrócone piksele


def test_ocr_czyta_strony_obrocone_o_90_180_270(tmp_path):
    cel = tmp_path / "k"
    cel.mkdir()
    wpis = korpus.generuj_dokument(korpus.Pozycja("x-pdf", "pl", "umowa", "pdf"), 1, "dev", cel)
    strona = pdfium.PdfDocument(str(cel / wpis["plik"]))[0].render(scale=200 / 72).to_pil().convert("RGB")
    wzorzec = normalizuj(next(g["tekst"] for g in wpis["gold_plik"] if g["kategoria"] == "OSOBA"))
    for kat in (0, 90, 180, 270):
        bufor = io.BytesIO()
        strona.rotate(kat, expand=True, fillcolor="white").save(bufor, format="PNG")
        assert wzorzec in normalizuj(obrazy.ocr_tekst(bufor.getvalue(), "pl").replace("\x0c", " ")), kat
    assert obrazy.kat_obrotu(strona) == 0
    assert obrazy.kat_obrotu(strona.rotate(90, expand=True, fillcolor="white")) == 90      # obrót zgodnie z ruchem wskazówek, by wyprostować


# ----------------------------------------------------------------------------- obrazy: pieczątka, zrzut, znak wodny
def _obrazy_pliku(plik: Path, format_: str) -> list[bytes]:
    """Obrazy osadzone (niezależny czytnik: pikepdf / zipfile), bez obrazów podpisu i loga z trzonu – po rozmiarze."""
    if format_ == "docx":
        with zipfile.ZipFile(plik) as z:
            return [z.read(n) for n in z.namelist() if n.startswith("word/media/h4_obraz")]
    wynik = []
    with pikepdf.open(plik) as pdf:       # dopisek leży na ostatniej stronie (strona załącznika)
        for obiekt in pdf.pages[-1].Resources.XObject.values():
            bufor = io.BytesIO()
            pikepdf.PdfImage(obiekt).as_pil_image().save(bufor, format="PNG")
            wynik.append(bufor.getvalue())
    return wynik


def _zbliz(a: str, b: str) -> bool:
    return obrazy.podobienstwo(normalizacja.same_alnum(a), normalizacja.same_alnum(b)) >= 0.8


@pytest.mark.parametrize("przypadek", [P.SKAN_PIECZATKI, P.ZRZUT_EKRANU])
def test_obrazy_gold_ramki_czytane_tesseractem(warstwa, przypadek):
    cel, wpisy = warstwa[przypadek]
    for w in wpisy[:4]:
        gold = [g for g in w["gold_plik"] if g["id"].startswith("h.")]
        assert gold and all(g["miejsce"] == "obraz" and "tekst_xml" not in g.get("cechy", ()) for g in gold)
        o = next(o for o in w["gold_obrazy"] if o["id"].endswith("-h4a1"))
        assert [x["id"] for x in o["wartosci"]] == [g["id"] for g in gold]
        png = _obrazy_pliku(cel / w["plik"], w["format"])
        assert len(png) == 1, (w["id"], len(png))
        obraz = Image.open(io.BytesIO(png[0])).convert("RGB")
        przeczytane = 0
        for wid, (x0, y0, x1, y1) in o["ramki"]:
            assert 0 <= x0 < x1 <= obraz.width and 0 <= y0 < y1 <= obraz.height
            g = next(g for g in gold if g["id"] == wid)
            wycinek = obraz.crop((max(0, x0 - 6), max(0, y0 - 6), x1 + 6, y1 + 6))
            wycinek = wycinek.resize((wycinek.width * 2, wycinek.height * 2), Image.LANCZOS)
            odczyt = ocr_modul.ocr_obraz(wycinek, w["jezyk"], psm=6)
            przeczytane += _zbliz(odczyt, g["tekst"]) or normalizacja.same_alnum(g["tekst"]) in normalizacja.same_alnum(odczyt)
        # pieczątka jest zaszumiona i obrócona (OCR myli się częściej): co najmniej połowa wartości; zrzut: prawie wszystkie
        assert przeczytane >= (len(o["ramki"]) // 2 if przypadek == P.SKAN_PIECZATKI else len(o["ramki"]) - 1), (w["id"], przeczytane, len(o["ramki"]))
        if w["format"] == "pdf":
            assert [p[0] for p in o["polozenia"]] == [g["id"] for g in gold]


def _png(im: Image.Image) -> bytes:
    b = io.BytesIO()
    im.save(b, format="PNG")
    return b.getvalue()


def test_znak_wodny_pdf_i_docx(warstwa):
    cel, wpisy = warstwa[P.ZNAK_WODNY]
    assert {w["format"] for w in wpisy} == {"pdf", "docx"}
    for w in wpisy:
        gold = next(g for g in w["gold_plik"] if g["id"].startswith("h.znak_wodny"))
        plik = cel / w["plik"]
        if w["format"] == "docx":
            assert gold["miejsce"] == "naglowek"
            with zipfile.ZipFile(plik) as z:
                nazwy = [n for n in z.namelist() if re.fullmatch(r"word/header\d+\.xml", n)]
                napisy = [e.get("string") for n in nazwy for e in etree.fromstring(z.read(n)).iter(f"{V}textpath") if e.get("string")]
                rels = z.read("word/_rels/document.xml.rels").decode()
            assert napisy == [gold["tekst"]] and "header" in rels
            continue
        assert gold["miejsce"] == "obraz"
        with pikepdf.open(plik) as pdf:
            for strona in pdf.pages:                                         # na każdej stronie, półprzezroczysty, ukośnie
                tresc = b"".join(s.read_bytes() for s in (strona.Contents if isinstance(strona.Contents, pikepdf.Array) else [strona.Contents]))
                assert b"/PbZnak Do" in tresc and "/PbZnakGs" in strona.Resources.ExtGState
                assert float(strona.Resources.ExtGState.PbZnakGs.ca) < 0.5
            obrazy_znaku = {strona.Resources.XObject.PbZnak.objgen for strona in pdf.pages}
            assert len(obrazy_znaku) == 1                                      # jeden obraz osadzony na cały plik
            znak = pikepdf.PdfImage(pdf.pages[0].Resources.XObject.PbZnak).as_pil_image()
        odczyt = ocr_modul.ocr_obraz(znak.convert("RGB"), w["jezyk"], psm=7)
        assert _zbliz(odczyt, gold["tekst"]), (odczyt, gold["tekst"])
        assert len(next(o for o in w["gold_obrazy"] if o["id"].endswith("-h4a1"))["polozenia"]) == len(tekst_pdf(plik))


# ----------------------------------------------------------------------------- ukryta_pdf
def test_ukryta_pdf_zaczernienie_nad_tekstem_i_warstwa_ocr(warstwa):
    cel, wpisy = warstwa[P.UKRYTA_PDF]
    for w in wpisy:
        assert w["ukryte"] == ["pdf.warstwa_ocr", "pdf.zaczernienie"] and w["format"] == "pdf"
        gold = [g for g in w["gold_plik"] if g["id"].startswith("u.")]
        assert gold and all(g["miejsce"] == "metadane" for g in gold)
        zacz = [g["tekst"] for g in gold if "zaczernienie" in g["id"]]
        ocr = [g["tekst"] for g in gold if "warstwa_ocr" in g["id"]]
        plik = cel / w["plik"]
        strony = tekst_pdf(plik)
        with pikepdf.open(plik) as pdf:
            assert len(pdf.pages) == len(strony) >= 3
            aneks, skan = pdf.pages[-2], pdf.pages[-1]
            # (a) tekst wartości stoi w strumieniu treści (do skopiowania), a czarny prostokąt jest rysowany PÓŹNIEJ niż tekst
            assert all(t in strony[-2] for t in zacz)
            operacje = [(str(op), [o for o in ops]) for ops, op in pikepdf.parse_content_stream(aneks)]
            nazwy = [o for o, _ in operacje]
            ostatni_tekst = max(i for i, o in enumerate(nazwy) if o in ("Tj", "TJ"))
            prostokaty = [i for i, o in enumerate(nazwy) if o == "re"]
            assert len(prostokaty) == len(zacz) and ({"f", "f*"} & set(nazwy))       # po jednym prostokącie na wartość
            assert all(i > min(j for j, o in enumerate(nazwy) if o in ("Tj", "TJ")) for i in prostokaty) and max(prostokaty) > ostatni_tekst
            # (b) skan z niewidoczną warstwą tekstową: obraz + tryb renderowania 3; dane tylko w warstwie tekstowej
            tryby = [ops for ops, op in pikepdf.parse_content_stream(skan) if str(op) == "Tr"]
            assert tryby and all(int(t[0]) == 3 for t in tryby) and len(list(skan.Resources.XObject)) == 1
            assert all(t in strony[-1] for t in ocr)
            obraz = pikepdf.PdfImage(next(iter(skan.Resources.XObject.values()))).as_pil_image().convert("RGB")
        odczyt = ocr_modul.ocr_obraz(obraz, w["jezyk"], psm=6)
        assert not any(normalizacja.same_alnum(t) in normalizacja.same_alnum(odczyt) for t in ocr if len(t) > 5)    # na obrazie ich nie ma


# ----------------------------------------------------------------------------- zepsuty ToUnicode
@pytest.fixture(scope="module")
def zwykly_pdf(tmp_path_factory):
    cel = tmp_path_factory.mktemp("zwykly")
    wpis = korpus.generuj_dokument(korpus.Pozycja("z-pl-umowa", "pl", "umowa", "pdf"), 7, "dev", cel)
    return cel, wpis


@pytest.mark.parametrize("tryb", TP.pliki_pdf.TRYBY_TOUNICODE)
def test_zepsuty_tounicode_tekst_smieci_obraz_poprawny_a_sedzia_wykrywa_wyciek(zwykly_pdf, tmp_path, tryb):
    cel, wpis = zwykly_pdf
    zepsuty = tmp_path / "zepsuty.pdf"
    shutil.copy(cel / wpis["plik"], zepsuty)
    assert TP.pliki_pdf.zepsuj_tounicode(zepsuty, tryb) >= 2
    ws = wartosci_wpisu(wpis)
    osoby = [w.tekst for w in ws if w.kategoria == "OSOBA" and w.miejsce == "tresc"]
    surowy = "\n".join(tekst_pdf(zepsuty))
    if tryb == "usuniete":                                              # znaki spoza ASCII stają się kodami sterującymi
        assert sum(1 for c in surowy if ord(c) < 32 and c not in "\t\r\n") >= 3
    else:                                                               # śmieci zamiast tekstu
        assert not any(o in surowy for o in osoby)
        assert not any(o.split()[-1] in surowy for o in osoby if len(o.split()[-1]) > 5)
    # tekst na stronie wygląda poprawnie: niezależny OCR renderu strony czyta nazwisko
    strona = pdfium.PdfDocument(str(zepsuty))[0].render(scale=200 / 72).to_pil().convert("RGB")
    odczyt = normalizuj(obrazy._tesseract(strona, "pl", 3))
    assert sum(normalizuj(o) in odczyt for o in set(osoby)) >= len(set(osoby)) // 2
    # sędzia: oryginał → wyciek wykryty mimo śmieci w warstwie tekstowej (ścieżka OCR stron)
    assert warstwa_tekstowa_zepsuta(wydobadz(zepsuty), ws)
    a = ocen_plik(zepsuty, zepsuty, ws, leksykon={})
    tekstowe = {w.id for w in ws if not w.w_pikselach and w.miejsce in sedzia_plik.MIEJSCA_TEKSTU_STRONY} - set(a.niejednoznaczne)
    wyciekly = {x[0] for x in a.wycieki}
    assert len(tekstowe & wyciekly) >= 0.9 * len(tekstowe), sorted(tekstowe - wyciekly)
    assert {w.id for w in ws if w.kategoria == "OSOBA" and w.miejsce == "tresc"} - set(a.niejednoznaczne) <= wyciekly
    # zwykły oryginał ma zdrową warstwę tekstową (OCR jego stron nie wchodzi do zbiorów dokumentu), a `wydobadz` stron nie renderuje
    assert not warstwa_tekstowa_zepsuta(wydobadz(cel / wpis["plik"]), ws)
    assert not any(n.startswith(ekstrakcja.PREFIKS_RENDERU) for n, _ in wydobadz(cel / wpis["plik"]).obrazy)


def test_zepsuty_tounicode_naiwny_na_warstwie_tekstowej_zostawia_wyciek(warstwa, tmp_path):
    """Uczestnik pracujący na warstwie tekstowej PDF nie znajduje wartości (śmieci) i zwraca plik bez zmian: wycieka wszystko."""
    cel, wpisy = warstwa[P.ZEPSUTY_TOUNICODE]
    w = next(w for w in wpisy if w["tounicode"] != "usuniete")        # w trybie `usuniete` ASCII zostaje czytelne
    orig = cel / w["plik"]
    ws = wartosci_wpisu(w)
    zepsuty = "\n".join(tekst_pdf(orig))
    assert not any(g.tekst in zepsuty for g in ws if g.kategoria == "OSOBA" and len(g.tekst) > 8)
    a = ocen_plik(orig, orig, ws, leksykon={})
    assert len({x[0] for x in a.wycieki}) >= 0.8 * (len({g.id for g in ws}) - len(a.niejednoznaczne) - len(a.niewykrywalne))


# ============================================================================= sanity: oryginał / idealny / naiwny
class WidocznaTresc(Maskowanie):
    """Idealny uczestnik, który nie widzi dopisków ukrytych (`Dokument.ukryte`): maskuje treść i metadane."""

    def __call__(self, d):
        n = super().__call__(d)
        n.ukryte = Dokument.from_dict(d.to_dict()).ukryte
        return n


class BezCechy(Maskowanie):
    """Uczestnik, który nie rozpoznaje wartości z daną cechą (np. `zero_width`): maskuje resztę."""

    def __init__(self, cecha: str) -> None:
        super().__init__()
        self.cecha = cecha

    def _zamien(self, w: Wartosc) -> Wartosc:
        return w if self.cecha in w.cechy else super()._zamien(w)


def _pozycja(w: dict, przypadek: str) -> trudne.PozycjaTrudna:
    return trudne.PozycjaTrudna(w["id"], w["jezyk"], w["typ"], w["format"], przypadek)


def _uczestnik(przypadek: str, w: dict, tmp: Path, maskuj) -> Path:
    tmp.mkdir(exist_ok=True)
    r = trudne.generuj_dokument_trudny(_pozycja(w, przypadek), trudne.ZIARNO_TRUDNE, w["split"], tmp, maskuj=maskuj)
    return tmp / r["plik"]


def _normy(ids, ws) -> Counter:
    teksty = {w.id: normalizuj(w.tekst) for w in ws}
    return Counter(teksty[i] for i in ids)


@pytest.mark.parametrize("przypadek,i", [(p, i) for p in P.H4A for i in (0, 1, 3)])
def test_sanity_oryginal_i_idealny(warstwa, tmp_path, przypadek, i):
    cel, w, orig = _dok(warstwa, przypadek, i)
    ws = wartosci_wpisu(w)
    a = ocen_plik(orig, orig, ws, leksykon={})
    assert a.status == "OK"
    oceniane = {x.id for x in ws} - set(a.niejednoznaczne) - set(a.niewykrywalne)
    # poza oceną także wartości, które w sędzi plikowym nie mogą wyciec (`Regula.moze_wyciec` False, np. kwota krótsza niż
    # `MIN_CYFR_KWOTY` – „10,00 €”; `metodyka/zakres-gold.md`, „Bez zmian (reguła oczekiwana)”): sanity raportuje je jako
    # niewyciekające z kopii oryginału, jednakowo dla wszystkich uczestników
    zb = sedzia_plik.zbiory_dokumentu(orig, ws, leksykon={})
    niemozliwe = oceniane - {x.id for g in zb.grupy for x in g.wartosci}
    wyciekly = {x[0] for x in a.wycieki}
    if przypadek == P.ZEPSUTY_TOUNICODE:              # tekst z OCR renderu strony: drobny druk (stopka) bywa nieczytelny
        assert len(oceniane & wyciekly) >= 0.9 * len(oceniane - niemozliwe), sorted(oceniane - wyciekly - niemozliwe)
    else:
        # kopia oryginału wycieka wszystko, co ocenia sędzia (porównanie po tekstach: sędzia numeruje identyczne wartości kolejno)
        teksty = {x.id: normalizuj(x.tekst) for x in ws}
        assert {teksty[i] for i in oceniane - niemozliwe} <= {teksty[i] for i in wyciekly}, sorted(oceniane - wyciekly - niemozliwe)
    specjalne = ({x.id for x in ws if x.id.startswith(("h.", "u."))} - set(a.niejednoznaczne) - set(a.niewykrywalne)
                 - niemozliwe)
    assert specjalne <= wyciekly, sorted(specjalne - wyciekly)                 # oryginał: wszystkie wartości przypadku wyciekają
    ideal = _uczestnik(przypadek, w, tmp_path / "ideal", Maskowanie())
    b = ocen_plik(orig, ideal, ws, leksykon={})
    assert b.status == "OK" and b.integralnosc["otwiera_sie"]
    assert not b.wycieki, b.wycieki[:4]                                          # idealny uczestnik: 0 wycieków


@pytest.mark.parametrize("przypadek,cecha", [(P.ZNAKI_ZEROWEJ_SZEROKOSCI, "zero_width"), (P.RTL, "rtl"),
                                             (P.PRZENIESIENIA, "przeniesienie")])
def test_sanity_naiwny_nie_rozpoznaje_wartosci_z_cecha_przypadku(warstwa, tmp_path, przypadek, cecha):
    """Naiwny uczestnik (szuka wartości jako gołego napisu): nie znajduje wartości ze znakami zerowej szerokości / RTL / złamanych
    przeniesieniem – wyciek dokładnie w elementach przypadku (liczone po tekstach: sędzia numeruje identyczne wartości kolejno)."""
    for i in (0, 1, 2):
        cel, w, orig = _dok(warstwa, przypadek, i)
        ws = wartosci_wpisu(w)
        naiwny = _uczestnik(przypadek, w, tmp_path / f"n{i}", BezCechy(cecha))
        c = ocen_plik(orig, naiwny, ws, leksykon={})
        przypadkowe = [x.id for x in ws if cecha in x.cechy]
        wyciekly = [x[0] for x in c.wycieki]
        assert przypadkowe
        teksty = {x.id: normalizuj(polacz_przeniesienia(x.tekst)) for x in ws}
        oczekiwane = {teksty[x] for x in przypadkowe}
        # wartości przypadku wyciekają (identyczne teksty sędzia numeruje kolejno, więc porównujemy teksty)
        assert oczekiwane <= {teksty[x] for x in wyciekly} | {teksty[x] for x in c.niejednoznaczne}, c.wycieki[:6]
        # a wyciek innych wartości to tylko wspólne tokeny z wartościami przypadku (to samo nazwisko w zapisie zwykłym i z cechą)
        tokeny = {t for x in przypadkowe for t in re.findall(r"\w+", teksty[x])}
        assert all(set(re.findall(r"\w+", teksty[x])) & tokeny for x in wyciekly), c.wycieki[:6]
        ideal = ocen_plik(orig, _uczestnik(przypadek, w, tmp_path / f"i{i}", Maskowanie()), ws, leksykon={})
        assert not ideal.wycieki


@pytest.mark.parametrize("przypadek", [P.UKRYTA_PDF, P.SKAN_PIECZATKI, P.ZNAK_WODNY, P.ZRZUT_EKRANU])
def test_sanity_naiwny_widoczna_tresc_zostawia_wyciek_w_dopisku(warstwa, tmp_path, przypadek):
    for i in (0, 1):
        cel, w, orig = _dok(warstwa, przypadek, i)
        ws = wartosci_wpisu(w)
        dopisek = {x.id for x in ws if x.id.startswith(("h.", "u."))}
        naiwny = _uczestnik(przypadek, w, tmp_path / f"n{i}", WidocznaTresc())
        c = ocen_plik(orig, naiwny, ws, leksykon={})
        a = ocen_plik(orig, orig, ws, leksykon={})
        mozliwe = dopisek - set(a.niewykrywalne) - set(a.niejednoznaczne)
        wyciekly = {x[0] for x in c.wycieki}
        assert mozliwe <= wyciekly and not (wyciekly - dopisek), (c.wycieki[:5], sorted(mozliwe - wyciekly))


# ============================================================================= rozszerzenia sędziego (jednostkowo)
def test_ekstrakcja_czyta_znak_wodny_raz_i_nie_czyta_jego_maski_alfa(warstwa):
    """Znak wodny jest obrazem w zasobach strony po nałożeniu przez PbZnak; obraz w formularzu nakładki (XObject Form) też ma być
    czytany, a maska /SMask nie jest osobnym obrazem."""
    cel, wpisy = warstwa[P.ZNAK_WODNY]
    w = next(w for w in wpisy if w["format"] == "pdf")
    e = wydobadz(cel / w["plik"])
    nazwy = [n for n, _ in e.obrazy]
    assert sum("PbZnak" in n for n in nazwy) == 1 and not any(n.startswith(ekstrakcja.PREFIKS_RENDERU) for n in nazwy)


def test_ekstrakcja_obrazy_poza_zasobami_strony(tmp_path):
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    obraz = Image.new("RGB", (400, 120), "white")
    from PIL import ImageDraw
    ImageDraw.Draw(obraz).text((10, 40), "Znak Wodny 42", fill="black")
    bufor = io.BytesIO()
    c = canvas.Canvas(bufor, invariant=1)
    c.drawImage(ImageReader(io.BytesIO(_png(obraz))), 50, 600, 300, 90)
    c.showPage()
    c.save()
    # nakładka jako formularz: obraz leży w zasobach formularza, nie strony
    bazowy = io.BytesIO()
    c2 = canvas.Canvas(bazowy, invariant=1)
    c2.drawString(60, 700, "Tekst strony")
    c2.showPage()
    c2.save()
    plik = tmp_path / "formularz.pdf"
    with pikepdf.open(io.BytesIO(bazowy.getvalue())) as pdf, pikepdf.open(io.BytesIO(bufor.getvalue())) as nakladka:
        pikepdf.Page(pdf.pages[0]).add_overlay(nakladka.pages[0])
        pdf.save(plik)
    e = wydobadz(plik)
    assert e.obrazy and any("Znak Wodny" in obrazy.ocr_tekst(b, "pl") for _, b in e.obrazy)


def test_sedzia_plik_zwykly_pdf_trzonu_ma_zdrowa_warstwe_tekstowa(zwykly_pdf):
    cel, wpis = zwykly_pdf
    assert not warstwa_tekstowa_zepsuta(wydobadz(cel / wpis["plik"]), wartosci_wpisu(wpis))


# ----------------------------------------------------------------------------- poprawki 1–2: wynik, w którym to, co widać, różni się od tekstu
@pytest.fixture(scope="module")
def adwers(tmp_path_factory):
    """Zwykły dokument trzonu (PDF) i wynik idealnego uczestnika: baza dla wyników, w których to, co widać, różni się od tekstu."""
    cel = tmp_path_factory.mktemp("adwers")
    poz = korpus.Pozycja("z-pl-umowa", "pl", "umowa", "pdf")
    wpis = korpus.generuj_dokument(poz, 7, "dev", cel / "o")
    ideal = korpus.generuj_dokument(poz, 7, "dev", cel / "i", maskuj=Maskowanie())
    return cel, cel / "o" / wpis["plik"], wartosci_wpisu(wpis), cel / "i" / ideal["plik"]


def _ocen_adw(orig: Path, wynik: Path, ws) -> tuple[set[str], set[str], ocen_plik.__class__]:
    a = ocen_plik(orig, wynik, ws, leksykon={})
    oceniane = {w.id for w in ws} - set(a.niejednoznaczne) - set(a.niewykrywalne)
    return oceniane, {x[0] for x in a.wycieki}, a


def _widoczne(a, ws) -> set[str]:
    """Wartości linii bazowej widoczne na stronie (bez metadanych – tych w rastrze strony słusznie nie ma)."""
    return set(a.bazowe) - {w.id for w in ws if w.miejsce == "metadane"}


def _raster(orig: Path, cel: Path, inline: bool, slowo: str | None = None, dpi: int = 150) -> Path:
    """Strony oryginału jako obrazy (XObject albo inline `BI…ID…EI`), opcjonalnie z niewidocznym tekstem (Tr 3) `slowo`."""
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    doc = pdfium.PdfDocument(str(orig))
    bufor = io.BytesIO()
    c = canvas.Canvas(bufor, invariant=1)
    for i in range(len(doc)):
        im = doc[i].render(scale=dpi / 72).to_pil().convert("RGB")
        w, h = doc[i].get_size()
        c.setPageSize((w, h))
        c.drawInlineImage(im, 0, 0, w, h) if inline else c.drawImage(ImageReader(im), 0, 0, w, h)
        if slowo:
            t = c.beginText(72, h - 72)
            t.setTextRenderMode(3)
            t.setFont("Helvetica", 10)
            t.textLine(slowo)
            c.drawText(t)
        c.showPage()
    c.save()
    doc.close()
    plik = cel / f"raster_{'inline' if inline else 'xobj'}_{int(bool(slowo))}.pdf"
    plik.write_bytes(bufor.getvalue())
    return plik


def _niewidoczny(src: Path, dst: Path) -> Path:
    """Kopia PDF z całym tekstem w trybie renderowania 3 (niewidoczny) – warstwa tekstowa bez zmian."""
    with pikepdf.open(src) as pdf:
        for s in pdf.pages:
            dane = s.Contents.read_bytes() if isinstance(s.Contents, pikepdf.Stream) else b"\n".join(
                c.read_bytes() for c in s.Contents)
            s.Contents = pdf.make_stream(re.sub(rb"\b[0-7] Tr\b", b"3 Tr", re.sub(rb"\bBT\b", b"BT 3 Tr", dane)))
        pdf.save(dst)
    return dst


def _nakladka(spod: Path, wierzch: Path, dst: Path) -> Path:
    """Strony `wierzch` narysowane na stronach `spod` (kolejność rysowania = kolejność nakładania)."""
    with pikepdf.open(spod) as a, pikepdf.open(wierzch) as b:
        for i, s in enumerate(a.pages):
            s.add_overlay(b.pages[i])
        a.save(dst)
    return dst


def _ze_znakami_sterujacymi(src: Path, dst: Path) -> Path:
    """Kopia PDF z niewidocznym tekstem ze znakami sterującymi (dawny wyzwalacz OCR stron oryginału)."""
    with pikepdf.open(src) as pdf:
        strona = pdf.pages[0]
        # własna czcionka Type1 (WinAnsi): kod 1 daje znak sterujący; podzbiory TrueType z zasobów mapują go na glif, a kolejność
        # kluczy słownika zasobów zależy od PYTHONHASHSEED
        strona.Resources.Font[pikepdf.Name("/FSter")] = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica,
            Encoding=pikepdf.Name.WinAnsiEncoding))
        strona.contents_add(pdf.make_stream(b"BT 3 Tr /FSter 10 Tf 72 72 Td (A\\001B\\001C\\001D\\001E) Tj ET"))
        pdf.save(dst)
    return dst


#: Przypadki C1 z ponownego przeglądu: strona pokazuje dane, a warstwa tekstowa jest czysta (tekst uczestnika idealnego).
PRZYPADKI_C1 = ["raster_inline_tr3", "raster_xobject_tr3", "tekst_pod_rastrem", "raster_nad_tekstem",
                *(f"tounicode_{t}_tr3" for t in TP.pliki_pdf.TRYBY_TOUNICODE)]


def _wynik_c1(przypadek: str, orig: Path, ideal: Path, cel: Path) -> Path:
    niewidoczny = _niewidoczny(ideal, cel / "idealny_tr3.pdf")
    if przypadek == "raster_inline_tr3":            # raster strony inline + tekst idealnego Tr 3 nad nim
        return _nakladka(_raster(orig, cel, True), niewidoczny, cel / "wynik.pdf")
    if przypadek == "raster_xobject_tr3":
        return _nakladka(_raster(orig, cel, False), niewidoczny, cel / "wynik.pdf")
    if przypadek == "tekst_pod_rastrem":            # tekst idealnego (Tr 3) narysowany POD rastrem inline
        return _nakladka(niewidoczny, _raster(orig, cel, True), cel / "wynik.pdf")
    if przypadek == "raster_nad_tekstem":           # tekst idealnego WIDOCZNY, przykryty nieprzezroczystym rastrem inline
        return _nakladka(ideal, _raster(orig, cel, True), cel / "wynik.pdf")
    tu = cel / "tu.pdf"                             # oryginał z zepsutym ToUnicode + nakładka idealnego Tr 3
    shutil.copy(orig, tu)
    TP.pliki_pdf.zepsuj_tounicode(tu, przypadek.removeprefix("tounicode_").removesuffix("_tr3"))
    return _nakladka(tu, niewidoczny, cel / "wynik.pdf")


@pytest.mark.parametrize("przypadek", PRZYPADKI_C1)
def test_c1_widoczna_strona_wycieka_mimo_czystej_warstwy_tekstowej(adwers, tmp_path, przypadek):
    """OCR stron każdego wyniku PDF, bez wyzwalacza: wartość widoczna na stronie wycieka, choćby warstwa tekstowa (kopiowanie)
    była tekstem uczestnika idealnego – ≥ 95 % wartości widocznych."""
    cel, orig, ws, ideal = adwers
    wynik = _wynik_c1(przypadek, orig, ideal, tmp_path)
    assert not {x[0] for x in ocen_plik(orig, _niewidoczny(ideal, tmp_path / "kontrola.pdf"), ws, leksykon={}).wycieki}
    _, wyciekly, a = _ocen_adw(orig, wynik, ws)
    widoczne = _widoczne(a, ws)
    assert len(widoczne) >= 40 and len(widoczne & wyciekly) >= 0.95 * len(widoczne), sorted(widoczne - wyciekly)


@pytest.fixture(scope="module")
def skan_adw(tmp_path_factory):
    cel = tmp_path_factory.mktemp("skan_adw")
    wpis = korpus.generuj_dokument(korpus.Pozycja("z-pl-umowa", "pl", "umowa", "skan"), 7, "dev", cel)
    return cel / wpis["plik"], wartosci_wpisu(wpis)


@pytest.mark.parametrize("slowo", ["[OSOBA_1] dokument", None])
def test_c1_skan_strony_jako_obrazy_inline_z_niewidocznym_slowem_wyciekaja(skan_adw, tmp_path, slowo):
    """Oryginał-skan, wynik: strony jako obrazy inline (+ jedno niewidoczne słowo). Bez słowa plik nie ma warstwy tekstowej ani
    obrazów osadzonych – to nie jest plik pusty, bo strony pokazują tekst."""
    orig, ws = skan_adw
    a = ocen_plik(orig, _raster(orig, tmp_path, True, slowo, dpi=200), ws, leksykon={})
    widoczne, wyciekly = _widoczne(a, ws), {x[0] for x in a.wycieki}
    assert a.status == "OK" and a.integralnosc["otwiera_sie"]
    assert len(widoczne) >= 15 and len(widoczne & wyciekly) >= 0.95 * len(widoczne), sorted(widoczne - wyciekly)


def test_c1_strony_kazdego_wyniku_pdf_czytane_ocr_idealny_zero_kopia_wszystko(adwers, monkeypatch):
    cel, orig, ws, ideal = adwers
    odczyty = []
    prawdziwa = obrazy.ocr_stron_pdf
    monkeypatch.setattr(obrazy, "ocr_stron_pdf", lambda p, j, drugi=False, trzeci=False:
                        odczyty.append((Path(p).name, drugi)) or prawdziwa(p, j, drugi, trzeci))
    _, wyciekly, a = _ocen_adw(orig, ideal, ws)
    assert not wyciekly and not a.niejednoznaczne
    # strony wyniku zawsze (300 dpi) i drugi odczyt (400 dpi), bo idealny nie zostawił żadnej wartości linii bazowej
    assert (ideal.name, False) in odczyty and (ideal.name, True) in odczyty and (orig.name, False) in odczyty
    oceniane, wyciekly, b = _ocen_adw(orig, orig, ws)
    assert oceniane <= wyciekly and len(wyciekly) == b.wartosci_ocenione and b.bazowe == a.bazowe
    assert (ekstrakcja.RENDER_DPI, ekstrakcja.DRUGI_ODCZYT_DPI, obrazy.PSM_STRON, obrazy.PSM_DRUGIEGO_ODCZYTU,
            obrazy.PSM_TRZECIEGO_ODCZYTU) == (300, 400, (3,), (3, 6), (6,))


def test_c1_ocr_stron_z_pamieci_podrecznej_po_sumie_pliku(adwers, monkeypatch, tmp_path):
    """OCR stron: klucz z sumą pliku, dpi, językiem i wersją OCR – trafienie w pamięć podręczną nie renderuje strony."""
    cel, orig, ws, _ = adwers
    monkeypatch.setenv("PBENCH_OCR_CACHE", str(tmp_path / "ocr"))
    pierwszy = obrazy.ocr_stron_pdf(orig, "pl")
    assert [n for n, _ in pierwszy] == [f"{ekstrakcja.PREFIKS_RENDERU} {i + 1}" for i in range(len(pierwszy))]
    plik_cache, = (tmp_path / "ocr").glob("strony-*.json")
    assert ekstrakcja.skrot_pliku(orig) in plik_cache.name and obrazy.WERSJA_OCR in plik_cache.name
    monkeypatch.setattr(ekstrakcja, "renderuj_strony", lambda *a: pytest.fail("render mimo pamięci podręcznej"))
    assert obrazy.ocr_stron_pdf(orig, "pl") == pierwszy


def test_c1_trzon_idealny_bez_wyciekow_kopia_wycieka_wszystko(tmp_path):
    """Próbka trzonu (PDF i skan, różne języki i typy) przy OCR stron każdego wyniku: idealny – 0 wycieków, kopia – 100 %."""
    probka = [("pl", "pismo", "pdf"), ("en", "umowa", "pdf"), ("de", "faktura", "pdf"), ("es", "pozew", "pdf"),
              ("fr", "umowa", "pdf"), ("pl", "umowa", "skan")]
    for j, (jezyk, typ, fmt) in enumerate(probka):
        poz = korpus.Pozycja(f"z-{jezyk}-{typ}", jezyk, typ, fmt)
        try:
            wpis = korpus.generuj_dokument(poz, 3 + j, "dev", tmp_path / f"{j}")
        except KeyError:
            continue
        ideal = korpus.generuj_dokument(poz, 3 + j, "dev", tmp_path / f"{j}i", maskuj=Maskowanie())
        orig = tmp_path / f"{j}" / wpis["plik"]
        ws = wartosci_wpisu(wpis)
        a = ocen_plik(orig, tmp_path / f"{j}i" / ideal["plik"], ws, leksykon={})
        assert not a.wycieki, (jezyk, typ, fmt, a.wycieki)
        b = ocen_plik(orig, orig, ws, leksykon={})
        assert len(b.wycieki) == b.wartosci_ocenione == len(b.bazowe) > 0, (jezyk, typ, fmt)


# ----------------------------------------------------------------------------- poprawki 2: zbiory dokumentu z oryginału (N1)
@pytest.fixture(scope="module")
def wypis(tmp_path_factory):
    """Dokument trzonu `de-med_wypis-0004` (przypadek z przeglądu) i wynik uczestnika częściowego."""
    from pbench.sedzia.sanity import Czesciowe
    cel = tmp_path_factory.mktemp("wypis")
    poz = korpus.Pozycja("de-med_wypis-0004", "de", "med_wypis", "pdf")
    wpis = korpus.generuj_dokument(poz, korpus.ZIARNO, "test", cel / "o")
    czes = korpus.generuj_dokument(poz, korpus.ZIARNO, "test", cel / "c", maskuj=Czesciowe())
    return cel, cel / "o" / wpis["plik"], wartosci_wpisu(wpis), cel / "c" / czes["plik"]


def test_n1_zbiory_dokumentu_nie_zaleza_od_wyniku_uczestnika(wypis, monkeypatch):
    """Ten sam dokument, dwóch uczestników – drugi dopisuje niewidoczne znaki sterujące (wyzwalacz OCR stron oryginału):
    identyczne słowa generyczne, niejednoznaczne, niewykrywalne i linia bazowa; wycieki uczestnika częściowego nie znikają."""
    import inspect
    cel, orig, ws, czes = wypis
    wymuszony = _ze_znakami_sterujacymi(czes, cel / "wymuszony.pdf")
    assert sedzia_plik._ma_znaki_sterujace(sedzia_plik._tekst_stron(wydobadz(wymuszony)))
    assert not sedzia_plik._ma_znaki_sterujace(sedzia_plik._tekst_stron(wydobadz(czes)))
    # bez pliku wyniku (`posrednie` – kombinacje z manifestu, H5)
    assert list(inspect.signature(sedzia_plik.zbiory_dokumentu).parameters) == ["oryginal", "wartosci", "reguly", "jezyk",
                                                                                 "leksykon", "posrednie"]
    zbiory: list = []
    prawdziwa = sedzia_plik.zbiory_dokumentu
    monkeypatch.setattr(sedzia_plik, "zbiory_dokumentu", lambda *a, **k: zbiory.append(prawdziwa(*a, **k)) or zbiory[-1])
    a = ocen_plik(orig, czes, ws, leksykon={})
    b = ocen_plik(orig, wymuszony, ws, leksykon={})
    assert len(zbiory) == 2 and zbiory[0].generyczne == zbiory[1].generyczne and zbiory[0].bazowe == zbiory[1].bazowe
    assert (a.niejednoznaczne, a.niewykrywalne, a.bazowe) == (b.niejednoznaczne, b.niewykrywalne, b.bazowe)
    assert a.wartosci_ocenione == b.wartosci_ocenione and {x[0] for x in a.wycieki} == {x[0] for x in b.wycieki}
    assert a.wycieki and {x[0] for x in a.wycieki} <= {x[0] for x in b.wycieki}


def test_n1_ocr_stron_zwyklego_oryginalu_nie_wchodzi_do_slow_generycznych(wypis, monkeypatch):
    """Zwykły oryginał: słowa generyczne i niejednoznaczne bez OCR jego stron (gorszy odczyt tej samej treści); OCR stron wchodzi
    tylko przy zepsutej warstwie tekstowej oryginału."""
    cel, orig, ws, _ = wypis
    zb = sedzia_plik.zbiory_dokumentu(orig, ws, leksykon={})
    assert not zb.zepsuty
    wyd = wydobadz(orig)
    uniq = list({(w.id, w.tekst): w for w in ws}.values())
    osadzone = [t for _, t in obrazy.ocr_wiele(wyd.obrazy, zb.jezyk_ocr)]
    assert zb.generyczne == sedzia_plik.slowa_generyczne(wyd.czesci, osadzone, uniq) | sedzia_plik._tokeny_wartosci(
        uniq, zb.niejednoznaczne)


# ----------------------------------------------------------------------------- poprawki 2: krotność w OCR regułą OCR (N2)
def test_n2_krotnosc_wartosci_powtarzanej_liczona_w_ocr_regula_ocr(adwers, tmp_path):
    """E-mail kancelarii w treści i w stopce (`kancelaria.email#1/#2`): wynik z zepsutym ToUnicode pokazuje oba, a OCR czyta je
    jako „officeQ darex…” – krotność z reguły OCR, nie z dokładnej frazy."""
    cel, orig, ws, _ = adwers
    wynik = tmp_path / "tu_pua.pdf"
    shutil.copy(orig, wynik)
    TP.pliki_pdf.zepsuj_tounicode(wynik, "pua")
    _, wyciekly, a = _ocen_adw(orig, wynik, ws)
    assert {"kancelaria.email#1", "kancelaria.email#2"} <= set(a.bazowe) and {"kancelaria.email#1", "kancelaria.email#2"} <= wyciekly


def test_n2_ile_w_ocr_wiersze_ciagi_i_odczyty():
    from pbench.sedzia.tekst import RegulyWycieku

    def ile(tekst: str, wartosc: str, kategoria: str = "OSOBA") -> int:
        w = Wartosc("x#1", kategoria, wartosc, "pl", "tresc", kategoria)
        reg, dokl = (sedzia_plik.zbuduj_regule(w, RegulyWycieku(), set(), [], ocr=o) for o in (True, False))
        return sedzia_plik._ile_w_ocr(reg, None, [sedzia_plik._Ocr("strona", tekst)], dokl)

    assert ile("biuro officeQ darex.example.org\nTekst umowy\nofficeQ©darex.example.org", "office@darex.example.org", "EMAIL") == 2
    assert ile("Pan Jan\nKowalski mieszka", "Jan Kowalski") == 1                 # wartość złamana między wiersze – raz
    assert ile("Jan Kowalski\nJan Kowalski", "Jan Kowalski") == 2                # dwie pełne w sąsiednich wierszach
    assert ile("Jan Kowalski\fJan Kowalski", "Jan Kowalski") == 1                # dwa odczyty tej samej strony – maksimum
    assert ile("Nic tu nie ma", "Jan Kowalski") == 0
    assert ile("1 Pauschale 1 1.526,68 EUR 1.526,68 EUR 19%", "1.526,68 €", "KWOTA") == 2     # netto i brutto w jednym wierszu
    assert ile("Summe 1.526,68 EUR\nPosition 1.526.68 EUR", "1.526,68 €", "KWOTA") == 2        # OCR: kropka zamiast przecinka


def test_c1_ocr_stron_slowa_innych_wartosci_i_zamiennikow_nie_trafiaja_rozmyto():
    """OCR całej strony widzi też słowa innych wartości i zamienniki: słowo równe innemu słowu dokumentu nie trafia rozmyto tokenu
    wartości, identyfikator nie trafia w dokładne wystąpienie innej wartości, nazwa kategorii z zamiennika nie jest tokenem wycieku;
    e-mail z „@” przeczytanym jako litera wycieka (ciąg alfanumeryczny)."""
    from pbench.sedzia.plik import Tekst, dopasuj
    from pbench.sedzia.tekst import RegulyWycieku

    def regula(tekst: str, kategoria: str, inne: list[str]):
        w = Wartosc("x#1", kategoria, tekst, "es", "tresc", kategoria)
        slownik = frozenset(t for x in [tekst, *inne] for t in re.findall(r"\w+", normalizuj(x)))
        alnum = frozenset(normalizacja.same_alnum(x) for x in [tekst, *inne])
        return sedzia_plik.zbuduj_regule(w, RegulyWycieku(), set(), [], ocr=True, slownik=slownik, inne_alnum=alnum)

    email = regula("lschmidt@post.test", "EMAIL", ["Lars Schmidt"])
    assert dopasuj(email, Tekst("Bewerber: Lars Schmidt"), ocr=True) is None            # „Schmidt” to inna wartość
    assert dopasuj(email, Tekst("E-Mail: lschmldt@post.test"), ocr=True)                # błąd OCR w adresie – nadal wyciek
    osoba = regula("Andrés Lorenzo Rey", "OSOBA", [])
    ocr = lambda s: Tekst(sedzia_plik.maskuj_zamienniki(s))                              # tekst OCR jak w `_Ocr`
    assert dopasuj(osoba, ocr("[ADRES 21] , con efectos"), ocr=True) is None            # zamiennik [ADRES_21] bez podkreślnika
    assert dopasuj(regula("https://portal.granite.example.org/login", "URL", []), ocr("GitHub: [LOGIN 7]"), ocr=True) is None
    data = regula("1. Juli 2025", "DATA", ["28. Juli 2025"])
    assert dopasuj(data, Tekst("Zahlbar bis zum 28. Juli 2025"), ocr=True) is None     # inna data, różna o jedną cyfrę
    assert dopasuj(data, Tekst("Datum: 1. Juli 2O25"), ocr=True) == "pelny"
    adres = regula("rsoriano@poufne.example", "EMAIL", ["Raúl Soriano Cordero"])
    assert dopasuj(adres, Tekst("rsorianofpoufne.example"), ocr=True) == "pelny"       # „@” przeczytane jako „f”


# ----------------------------------------------------------------------------- poprawki 1: niejednoznaczne z OCR stron (I1)
def test_i1_zepsuty_tounicode_nie_wylacza_nazwy_kancelarii_i_pelnomocnika(adwers, tmp_path):
    cel, orig, ws, _ = adwers
    wynik = tmp_path / "tu.pdf"
    shutil.copy(orig, wynik)
    TP.pliki_pdf.zepsuj_tounicode(wynik, "pua")
    a = ocen_plik(wynik, wynik, ws, leksykon={})                          # zepsuty oryginał → render + OCR stron
    assert not a.niejednoznaczne, a.niejednoznaczne                      # zwykły oryginał też nie ma niejednoznacznych
    oceniane = {w.id for w in ws} - set(a.niewykrywalne)
    assert {"kancelaria.nazwa#1", "kancelaria.nazwa#2", "kancelaria.nazwa#3"} <= oceniane
    assert {x[0] for x in a.wycieki} >= {"kancelaria.nazwa#1", "kancelaria.nazwa#2", "kancelaria.nazwa#3", "partner.pelne#3"}


def test_i1_niejednoznaczne_z_renderu_porownuje_tekst_i_obraz():
    from pbench.sedzia.ekstrakcja import Czesc
    wartosci = [Wartosc("n#1", "ORGANIZACJA", "Kancelaria Adamczyk", "pl", "tresc", "ORGANIZACJA"),
                Wartosc("n#1@obraz", "ORGANIZACJA", "Kancelaria Adamczyk", "pl", "obraz", "ORGANIZACJA")]
    czesci = [Czesc("pdf:strona 1", linie=[]), ]
    render = "Kancelaria Adamczyk\nKancelaria Adamczyk"                    # raz w tekście i raz w logo
    assert sedzia_plik.niejednoznaczne(czesci, [], wartosci, 1, [render]) == set()
    assert sedzia_plik.niejednoznaczne(czesci, [], wartosci, 1, [render + "\nKancelaria Adamczyk"]) == {"n#1"}


# ----------------------------------------------------------------------------- poprawki 1–2: widok surowy PDF (I2, N4, N5)
def _z_dopiskiem(plik: Path, cel: Path, dopisek: bytes) -> Path:
    wynik = cel / "z_dopiskiem.pdf"
    wynik.write_bytes(plik.read_bytes() + dopisek)
    return wynik


def _objstm(tresc: bytes) -> bytes:
    """Osierocony strumień obiektów (poza xref) z jednym obiektem `tresc` (`1000 0 << … >>`)."""
    import zlib
    z = zlib.compress(tresc)
    return (b"\n999 0 obj\n<< /Type /ObjStm /N 1 /First %d /Filter /FlateDecode /Length %d >>\nstream\n" % (tresc.index(b"<<"), len(z))
            + z + b"\nendstream\nendobj\n")


def test_i2_osierocona_nazwa_z_danymi_osobowymi_wycieka(adwers, tmp_path):
    cel, orig, ws, ideal = adwers
    osoba = next(w.tekst for w in ws if w.kategoria == "OSOBA" and w.miejsce == "tresc")
    wynik = _z_dopiskiem(ideal, tmp_path, b"\n999 0 obj\n<< /Author /" + osoba.replace(" ", "#20").encode() + b" >>\nendobj\n")
    _, wyciekly, _ = _ocen_adw(orig, wynik, ws)
    assert wyciekly and any(w.tekst == osoba and w.id in wyciekly for w in ws)


def test_n4_nazwa_w_osieroconym_strumieniu_obiektow_dekodowana(adwers, tmp_path):
    """`/Author /Marka#20Filipka` w strumieniu obiektów daje ten sam (pełny) wyciek co w zwykłym obiekcie."""
    cel, orig, ws, ideal = adwers
    osoba = next(w for w in ws if w.kategoria == "OSOBA" and w.miejsce == "tresc")
    wynik = _z_dopiskiem(ideal, tmp_path, _objstm(b"1000 0 << /Author /" + osoba.tekst.replace(" ", "#20").encode() + b" >>"))
    _, _, a = _ocen_adw(orig, wynik, ws)
    assert (osoba.id, "pelny") in {(x[0], x[3]) for x in a.wycieki}


def test_i2_n5_nazwy_ze_slownictwa_pdf_nie_daja_wycieku_adresu_info(adwers, tmp_path):
    """Gold z adresem `info@…`: trailer `/Info` ani `/Info` w strumieniu obiektów nie dają częściowego wycieku „info”; ten sam
    adres zapisany jako string wycieka (test nie jest pusty)."""
    import dataclasses
    cel, orig, ws, ideal = adwers
    wyd = wydobadz(ideal)
    surowe = next(c for c in wyd.czesci if c.nazwa == "pdf:surowe")
    assert not any("/Info" in d or "/Root" in d for d in surowe.dodatkowe)
    em = next(w for w in ws if w.kategoria == "EMAIL")
    ws_info = [*ws, dataclasses.replace(em, id="x.email#1", tekst="info@adamczyk-kancelaria.pl")]
    for dopisek in (b"\ntrailer << /Info 3 0 R /Root 1 0 R /Type /Catalog /Size 9 >>\n",
                    _objstm(b"1000 0 << /Info 3 0 R /Root 1 0 R /Type /Catalog >>")):
        _, wyciekly, _ = _ocen_adw(orig, _z_dopiskiem(ideal, tmp_path, dopisek), ws_info)
        assert not wyciekly, dopisek
    _, wyciekly, _ = _ocen_adw(orig, _z_dopiskiem(ideal, tmp_path, b"\n999 0 obj\n<< /Author (info@adamczyk-kancelaria.pl) >>\nendobj\n"),
                               ws_info)
    assert wyciekly == {"x.email#1"}
    assert {"Info", "Type", "Page", "Pages", "Catalog", "Font", "Contents", "Resources", "XObject", "Image", "Filter",
            "FlateDecode", "Length"} <= ekstrakcja.NAZWY_FORMATU_PDF


# ----------------------------------------------------------------------------- poprawki 2: flaga ASCII85 reportlaba (N6)
def test_n6_import_renderera_nie_zmienia_flagi_a85_a_obraz_inline_dziala(adwers):
    from reportlab import rl_config
    from reportlab.pdfgen import canvas
    from pbench import render
    assert rl_config.useA85 == 1                 # wartość domyślna reportlaba: import i użycie rendererów jej nie zmieniają
    c = canvas.Canvas(io.BytesIO())
    c.drawInlineImage(Image.new("RGB", (40, 40), "red"), 0, 0, 40, 40)
    c.showPage()
    c.save()
    with render.bez_a85():
        assert rl_config.useA85 == 0
    assert rl_config.useA85 == 1


def test_i2_nazwa_dekodowana_i_wycinane_tylko_slownictwo():
    surowe = ekstrakcja._surowe_pdf(b"<< /Info 3 0 R /Author /Marka#20Filipka /Title /Jan#C5#82 >>")
    assert "Marka Filipka" in surowe[0] and "/Info" not in surowe[0] and "Info" not in surowe[0].replace("Filipka", "")


# ----------------------------------------------------------------------------- poprawki 1: maski obrazów (M1)
def test_m1_maska_pomijana_tylko_gdy_rodzic_przeczytany_i_maska_nie_jest_rysowana(tmp_path):
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from PIL import ImageDraw

    def obraz(tekst: str) -> Image.Image:
        from PIL import ImageFont
        im = Image.new("L", (1000, 140), 255)
        ImageDraw.Draw(im).text((10, 40), tekst, fill=0, font=ImageFont.truetype(f"{FONTY}/DejaVuSans.ttf", 64))
        return im

    bufor = io.BytesIO()
    c = canvas.Canvas(bufor, invariant=1)
    c.drawString(60, 700, "Tekst strony")
    c.showPage()
    c.save()
    with pikepdf.open(io.BytesIO(bufor.getvalue())) as pdf:
        def strumien_obrazu(im: Image.Image, **dodatki):
            s = pikepdf.Stream(pdf, im.convert("L").tobytes())
            s.Type, s.Subtype, s.Width, s.Height = pikepdf.Name.XObject, pikepdf.Name.Image, im.width, im.height
            s.ColorSpace, s.BitsPerComponent = pikepdf.Name.DeviceGray, 8
            for k, v in dodatki.items():
                s["/" + k] = v
            return s
        maska_tylko_alfa = strumien_obrazu(obraz("Alfa 777"))
        rodzic_a = strumien_obrazu(obraz("Rodzic 222"), SMask=maska_tylko_alfa)         # maska tylko jako alfa rodzica
        maska_rysowana = strumien_obrazu(obraz("Rysowana 333"))
        rodzic_b = strumien_obrazu(obraz("Rodzic 555"), SMask=maska_rysowana)            # tę samą maskę rysuje też formularz
        formularz = pikepdf.Stream(pdf, b"q 300 0 0 90 50 500 cm /Imk Do Q")
        formularz.Type, formularz.Subtype = pikepdf.Name.XObject, pikepdf.Name.Form
        formularz.BBox = [0, 0, 600, 800]
        formularz.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Imk=maska_rysowana))
        strona = pdf.pages[0]
        strona.Resources = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Fm1=formularz))
        strona.Contents = pdf.make_stream(b"/Fm1 Do")
        pdf.Root.Dekoy = pikepdf.Array([rodzic_a, rodzic_b])            # rodzice osiągalni z katalogu, ale poza zasobami stron
        plik = tmp_path / "maski.pdf"
        pdf.save(plik)
    e = wydobadz(plik)
    odczyty = " ".join(obrazy.ocr_tekst(b, "pl") for _, b in e.obrazy)
    assert "222" in odczyty and "555" in odczyty         # rodzice
    assert "333" in odczyty                               # maska rysowana operatorem Do jest widocznym obrazem
    assert "777" not in odczyty                           # maska będąca tylko kanałem alfa przeczytanego rodzica – pomijana


def test_sedzia_przeniesienie_nie_skleja_zwyklego_myslnika(tmp_path):
    """Gold „Nowak-Kowalski” i tekst z innym nazwiskiem po zwykłym myślniku w wierszu: nic nie jest sklejane."""
    plik = tmp_path / "a.txt"
    plik.write_text("Pan Nowak-Kowalski i Anna Lis-\nkowska.\nKonto 12-34.", encoding="utf-8")
    ws = [Wartosc("a#1", "OSOBA", "Nowak-Kowalski", "pl", "tresc", "OSOBA"), Wartosc("b#1", "OSOBA", "Anna Lis-\nkowska", "pl", "tresc", "OSOBA")]
    a = ocen_plik(plik, plik, ws, leksykon={})
    assert {x[0] for x in a.wycieki} == {"a#1", "b#1"}
    wyd = wydobadz(plik)
    assert any("Anna Liskowska" in d for c in wyd.czesci for d in c.dodatkowe) and not any("NowakKowalski" in d for c in wyd.czesci for d in c.dodatkowe)


# ----------------------------------------------------------------------------- poprawki 3: fałszywe trafienia OCR stron i krotność
def _regula_ocr(tekst: str, kategoria: str, inne: list[str] = [], jezyk: str = "pl", generyczne: set[str] = set()):
    """Reguła OCR wartości jak w `zbiory_dokumentu`: słownik = słowa wartości (słowa zamienników – tylko w tekście OCR,
    `maskuj_zamienniki`), ciągi alfanumeryczne wartości."""
    from pbench.sedzia.tekst import RegulyWycieku
    w = Wartosc("x#1", kategoria, tekst, jezyk, "tresc", kategoria)
    slownik = frozenset(t for x in [tekst, *inne] for t in re.findall(r"\w+", normalizuj(x))) | generyczne
    alnum = frozenset(normalizacja.same_alnum(x) for x in [tekst, *inne])
    return sedzia_plik.zbuduj_regule(w, RegulyWycieku(), set(generyczne), sorted(generyczne), ocr=True, slownik=slownik,
                                     inne_alnum=alnum)


def _grupa(tekst: str, kategoria: str = "OSOBA"):
    from pbench.sedzia.tekst import RegulyWycieku
    w = Wartosc("x#1", kategoria, tekst, "en", "tresc", kategoria)
    return sedzia_plik._Grupa([w], sedzia_plik.zbuduj_regule(w, RegulyWycieku(), set(), []), None,
                              _regula_ocr(tekst, kategoria, jezyk="en"), None, True)


def _ocen_strony(g, *odczyty_stron: str):
    """`_ocen_grupe` na samych odczytach stron (jeden tekst na rozdzielczość, odczyty trybami rozdzielone `ODDZIELACZ`)."""
    wid = sedzia_plik._Widoki([], [], [], [], [[sedzia_plik._Ocr(ekstrakcja.nazwa_renderu(1), t)] for t in odczyty_stron])
    return sedzia_plik._ocen_grupe(g, wid, {})[:3]          # bez czwartego elementu – obrazów osadzonych tu nie ma


def test_r1_czesciowe_z_ocr_stron_liczy_sie_z_potwierdzeniem_drugiego_odczytu():
    """Trafienie częściowe wyłącznie z OCR stron liczy się, gdy ten sam token trafia też w innym odczycie tej samej strony
    (inna rozdzielczość albo tryb); trafienie pełne – z jednego odczytu. Bez potwierdzenia: brak wycieku i prośba o drugi odczyt."""
    g = _grupa("Emma Gomez")
    STRONA_1 = "obraz:" + ekstrakcja.nazwa_renderu(1)
    # krótkie śmieci („EMA” z okaleczonego zamiennika „[EMAIL_10]”, przypadek (b)) nie trafiają rozmyto 4-literowego tokenu
    assert sedzia_plik.dopasuj(g.reg_ocr, sedzia_plik.Tekst("7 [OSOBA 9] = =—<“C—s—— SY EMA 10) a eeee"), ocr=True) is None
    smieci = "ni frosomaan | EMMA ee"                               # dokładne śmieciowe słowo z jednego odczytu (psm 6)
    assert sedzia_plik.dopasuj(g.reg_ocr, sedzia_plik.Tekst(smieci), ocr=True) == "czesciowy"
    assert _ocen_strony(g, smieci) == (None, 0, True)
    assert _ocen_strony(g, smieci, "Lista obecnosci\f[OSOBA 9] [EMAIL 10]") == (None, 0, True)
    assert _ocen_strony(g, "Podpis: Emma [OSOBA 2]", "Podpis: Emma [OSOBA 2]\fPodpis: Emrna") == \
        ((STRONA_1, "czesciowy"), 1, False)
    assert _ocen_strony(g, "Podpis: Emma\fPodpis: Emma") == ((STRONA_1, "czesciowy"), 1, False)
    assert _ocen_strony(g, "Kontakt: Emma Gomez") == ((STRONA_1, "pelny"), 1, False)
    # inna strona nie potwierdza
    wid = sedzia_plik._Widoki([], [], [], [], [[sedzia_plik._Ocr(ekstrakcja.nazwa_renderu(1), "Emma tu"),
                                                 sedzia_plik._Ocr(ekstrakcja.nazwa_renderu(2), "i Emma tam")]])
    assert sedzia_plik._ocen_grupe(g, wid, {}) == (None, 0, True, frozenset())


#: Dokumenty warstwy trudnej, w których uczestnik idealny miał fałszywe wycieki z OCR stron (R1) i z `/Widths` (R4).
FALSZYWE_TRAFIENIA = [("h-dl-es-lista_obecnosci-8001", "es", "lista_obecnosci", P.DLUGIE_LISTY_OSOB),
                      ("h-ni-fr-wykaz_osob-8002", "fr", "wykaz_osob", P.NAZWISKO_IMIE),
                      ("h-os-en-umowa-8001", "en", "umowa", P.OBROCONE_STRONY),
                      ("h-cu-uk-med_zaswiadczenie-8000", "uk", "med_zaswiadczenie", P.CYRYLICA_DOKUMENT_UK)]


@pytest.mark.parametrize("id_,jezyk,typ,przypadek", FALSZYWE_TRAFIENIA, ids=[f[0] for f in FALSZYWE_TRAFIENIA])
def test_r1_r4_idealny_bez_falszywych_trafien_kopia_wszystko(tmp_path, id_, jezyk, typ, przypadek):
    poz = trudne.PozycjaTrudna(id_, jezyk, typ, "pdf", przypadek)
    w = trudne.generuj_dokument_trudny(poz, trudne.ZIARNO_TRUDNE, "test", tmp_path / "o")
    r = trudne.generuj_dokument_trudny(poz, trudne.ZIARNO_TRUDNE, "test", tmp_path / "i", maskuj=Maskowanie())
    orig, ws = tmp_path / "o" / w["plik"], wartosci_wpisu(w)
    a = ocen_plik(orig, tmp_path / "i" / r["plik"], ws, leksykon={})
    assert a.status == "OK" and not a.wycieki, a.wycieki
    b = ocen_plik(orig, orig, ws, leksykon={})
    assert len(b.wycieki) == b.wartosci_ocenione == len(b.bazowe) > 0


def test_r2_identyfikatory_i_daty_w_ocr_po_zlozeniu_znakow_mylonych_z_granicami():
    """OCR: identyfikator/data/kwota po złożeniu znaków mylonych (O/0, I/l/1, Z/2, S/5, B/8) wzorcem z granicami; difflib tylko dla
    identyfikatorów ≥ 10 znaków, z granicami. Inna cyfra dnia/miesiąca/roku to inna data."""
    from pbench.sedzia.plik import Tekst, dopasuj
    assert sedzia_plik.ZNAKI_MYLONE_OCR.keys() >= {"o", "i", "l", "z", "s", "b"}
    data = _regula_ocr("28.11.2022 r.", "DATA")
    assert dopasuj(data, Tekst("w wyroku z dnia 29.11.2022 r. Sąd"), ocr=True) is None           # cytat orzeczenia
    assert dopasuj(data, Tekst("termin: 28.11.2O22 r."), ocr=True) == "pelny"                    # prawdziwy wyciek w rastrze
    assert dopasuj(data, Tekst("termin: 28.1l.2022 r."), ocr=True) == "pelny"
    slownie = _regula_ocr("7 sierpnia 2023 r.", "DATA")
    assert dopasuj(slownie, Tekst("w dniu 17 sierpnia 2023 r."), ocr=True) is None
    assert dopasuj(slownie, Tekst("w dniu 7 sierpnia 2O23 r."), ocr=True) == "pelny"
    numer = _regula_ocr("12345678", "NR_ID")
    assert dopasuj(numer, Tekst("nr 912345678"), ocr=True) is None
    assert dopasuj(numer, Tekst("nr l2345678"), ocr=True) == "pelny"
    pesel = _regula_ocr("85010112345", "PESEL")                                                   # ≥ 10 znaków: rozmyto
    assert dopasuj(pesel, Tekst("PESEL: 85O1O112845"), ocr=True) == "pelny"
    assert dopasuj(pesel, Tekst("PESEL: 9985010112345"), ocr=True) is None                         # wewnątrz dłuższego ciągu
    # token z cyfrą w wartości nie-ID: „I48” odczytane jako „148”
    rozp = _regula_ocr("I48 Atrial fibrillation and flutter", "ZDROWIE", jezyk="en")
    assert dopasuj(rozp, Tekst("Diagnosis: 148 Atrial fibrillation and flutter"), ocr=True) == "pelny"


def test_r2_pl_wyrok_0018_idealny_bez_wyciekow(tmp_path):
    """Trzon: cytat orzeczenia z datą różniącą się jedną cyfrą od daty gold (tu „29 listopada 2022 r.” przy „28 listopada 2022 r.”)
    nie jest wyciekiem daty gold u uczestnika idealnego."""
    poz = korpus.Pozycja("pl-wyrok-0018", "pl", "wyrok", "pdf")
    w = korpus.generuj_dokument(poz, korpus.ZIARNO, "test", tmp_path / "o")
    r = korpus.generuj_dokument(poz, korpus.ZIARNO, "test", tmp_path / "i", maskuj=Maskowanie())
    orig, ws = tmp_path / "o" / w["plik"], wartosci_wpisu(w)
    daty = {x.tekst for x in ws if x.kategoria == "DATA"}
    tekst = " ".join(c.caly_tekst() for c in wydobadz(orig).czesci)
    wystapienia = set(re.findall(r"\d{1,2}(?:\.\d{1,2}\.| [^\W\d]+ )\d{4} r\.", tekst)) - daty
    # cytowana data: ten sam zapis i długość co data gold, inna dokładnie jedna cyfra
    assert any(len(c) == len(d) and sum(a != b for a, b in zip(c, d)) == 1 for c in wystapienia for d in daty), (daty, wystapienia)
    a = ocen_plik(orig, tmp_path / "i" / r["plik"], ws, leksykon={})
    assert not a.wycieki, a.wycieki


def test_m2_wyciecie_innej_wartosci_tylko_z_granicami():
    """„Z1. Juli 2025” (OCR „21. Juli 2025”) przy gold „21. Juli 2025” i „1. Juli 2025”: wycięcie „1. Juli 2025” ze środka
    dłuższego ciągu ukrywałoby wyciek; wartość „1. Juli 2025” w tym tekście nie wycieka."""
    from pbench.sedzia.plik import Tekst, dopasuj
    assert dopasuj(_regula_ocr("21. Juli 2025", "DATA", ["1. Juli 2025"]), Tekst("Datum: Z1. Juli 2025"), ocr=True) == "pelny"
    assert dopasuj(_regula_ocr("1. Juli 2025", "DATA", ["21. Juli 2025"]), Tekst("Datum: Z1. Juli 2025"), ocr=True) is None


def test_r3_krotnosc_w_ocr_tylko_trafienia_pelne(tmp_path):
    """Samo nazwisko w innym wierszu nie jest drugim wystąpieniem pełnej wartości; wartość złamana między wiersze liczy się raz."""
    from reportlab.pdfgen import canvas
    from pbench.sedzia.tekst import RegulyWycieku

    def ile(tekst: str, wartosc: str, generyczne: set[str] = set(), kategoria: str = "OSOBA") -> int:
        w = Wartosc("x#1", kategoria, wartosc, "pl", "tresc", kategoria)
        reg, dokl = (sedzia_plik.zbuduj_regule(w, RegulyWycieku(), set(generyczne), sorted(generyczne), ocr=o)
                     for o in (True, False))
        return sedzia_plik._ile_w_ocr(reg, None, [sedzia_plik._Ocr("strona", tekst)], dokl)

    assert ile("Jan Kowalski\nTekst umowy\nKowalski podpis", "Jan Kowalski") == 1
    assert ile("Kowalski podpis\nKowalski", "Jan Kowalski") == 0                   # same trafienia częściowe
    assert ile("Pan Jan\nKowalski mieszka", "Jan Kowalski", {"jan"}) == 1           # wiersz bez trafienia doklejony do ciągu
    # tablica złamana na dwa wiersze, z których żaden nie trafia sam, i drugie wystąpienie w jednym wierszu
    assert ile("rejestracyjnym SZ\n22924. Sprawca\nnumerem SZ 22924.", "SZ 22924", kategoria="NR_REJESTRACYJNY") == 2

    def pdf(p: Path, linie: list[str]) -> Path:
        c = canvas.Canvas(str(p), invariant=1)
        c.setFont("Helvetica", 12)
        for i, linia in enumerate(linie):
            c.drawString(72, 780 - 40 * i, linia)
        c.save()
        return p

    tresc = ["Umowa najmu lokalu mieszkalnego zawarta w dniu dzisiejszym.", "Wynajmujacy: Jan Wierzbicki, zwany dalej Wynajmujacym.",
             "Najemca zobowiazuje sie placic czynsz w terminie.", "Wierzbicki odpowiada za stan techniczny lokalu."]
    orig = pdf(tmp_path / "o.pdf", tresc + ["Podpis Wynajmujacego: Jan Wierzbicki"])
    wynik = pdf(tmp_path / "w.pdf", tresc + ["Podpis Wynajmujacego: [OSOBA_1]"])
    ws = [Wartosc("a.pelne#1", "OSOBA", "Jan Wierzbicki", "pl", "tresc", "OSOBA"),
          Wartosc("a.pelne#2", "OSOBA", "Jan Wierzbicki", "pl", "tresc", "OSOBA"),
          Wartosc("a.nazwisko#1", "OSOBA", "Wierzbicki", "pl", "tresc", "OSOBA")]
    a = ocen_plik(orig, wynik, ws, leksykon={})
    assert {"a.pelne#1", "a.pelne#2", "a.nazwisko#1"} <= set(a.bazowe)
    assert {x[0] for x in a.wycieki} == {"a.pelne#1", "a.nazwisko#1"}, a.wycieki


def test_r4_tokeny_z_samych_cyfr_spoza_identyfikatorow_nie_identyfikuja():
    """Dawka „1000 mg” trafia w `/Widths` czcionki – liczba w wartości spoza identyfikatorów nie wycieka sama; identyfikator z cyfr
    (także krótszy niż `MIN_DL_ID`, oceniany jak token) – tak."""
    from pbench.sedzia.plik import Tekst, dopasuj
    from pbench.sedzia.tekst import RegulyWycieku
    widths = Tekst("/Widths [ 580.0781 1000 773.9258 ]")
    for ocr in (False, True):
        lek = sedzia_plik.zbuduj_regule(Wartosc("x#1", "ZDROWIE", "Амоксицилін 1000 мг", "uk", "tresc", "ZDROWIE"),
                                        RegulyWycieku(), set(), [], ocr=ocr)
        assert "1000" in lek.liczace and "1000" not in lek.identyfikujace
        assert dopasuj(lek, widths, ocr=ocr) is None
        assert dopasuj(lek, Tekst("Амоксицилін 1000 мг"), ocr=ocr) == "pelny"
        nr = sedzia_plik.zbuduj_regule(Wartosc("x#1", "NR_ID", "48213", "pl", "tresc", "NR_ID"), RegulyWycieku(), set(), [], ocr=ocr)
        assert dopasuj(nr, Tekst("numer 48213"), ocr=ocr) == "pelny"


def test_m3_slowa_zamiennikow_wspolne_dla_wszystkich_uczestnikow():
    """Ochrona reguł OCR obejmuje zamienniki każdego uczestnika, którego wynik ocenia sędzia plikowy (etykiety z
    `uczestnicy/*/etykiety.json` uczestników z poziomem „plik”, Presidio, Privatizera, benchmarku): ten sam szum OCR wokół
    „<PERSON>” i wokół „[OSOBA_1]” daje ten sam wynik. Uczestnicy wyłącznie tekstowi (np. `ai4privacy`) nie oddają plików –
    ich etykiet sędzia plikowy nigdy nie widzi."""
    import tomllib
    from pbench.sedzia.plik import Tekst, dopasuj
    korzen = Path(__file__).resolve().parents[1]

    def plikowy(p: Path) -> bool:
        toml = p.parent / "uczestnik.toml"
        return toml.exists() and "plik" in tomllib.loads(toml.read_text(encoding="utf-8")).get("poziomy", [])

    pliki = [p for p in korzen.glob("uczestnicy/*/etykiety.json") if plikowy(p)]
    assert pliki
    etykiety = {k for p in [*pliki, korzen / "uczestnicy/_wspolne/etykiety_presidio.json"]
                for k in json.loads(p.read_text(encoding="utf-8"))}
    assert etykiety and all(normalizuj(k) in sedzia_plik.SLOWA_ZAMIENNIKOW for k in etykiety), \
        sorted(k for k in etykiety if normalizuj(k) not in sedzia_plik.SLOWA_ZAMIENNIKOW)
    assert {"osoba", "person", "persona", "personne", "name", "per"} <= sedzia_plik.SLOWA_ZAMIENNIKOW
    reg = _regula_ocr("Persson Osobal", "OSOBA")
    wyniki = {}
    for zamiennik in ("<PERSON>", "[OSOBA_1]", "[PERSON_001]", "[PERSONA_001]", "[NAME]"):
        for szum in (zamiennik, f"{zamiennik.strip('<>[]').replace('_', ' ')} 7"):     # OCR gubi nawiasy i podkreślnik
            tekst = Tekst(sedzia_plik.maskuj_zamienniki(f"Podpis: {szum} podpisal"))
            wyniki[szum] = dopasuj(reg, tekst, ocr=True)
    assert set(wyniki.values()) == {None}, wyniki
    # bez maskowania kontekstu zamiennika te same zamienniki „trafiają” rozmyto (test nie jest pusty)
    assert dopasuj(reg, Tekst("Podpis: PERSON 7"), ocr=True) and dopasuj(reg, Tekst("Podpis: [OSOBA 1]"), ocr=True)


def test_m4_duza_mediabox_render_kafelkami_w_pelnym_dpi(adwers, tmp_path):
    """Strona z `/MediaBox` 20× większym i rastrem oryginału w normalnym rozmiarze w rogu: render kafelkami obszaru z treścią w pełnym
    dpi – wartości widoczne wyciekają jak przy zwykłej stronie (≥ 95 %)."""
    from reportlab.pdfgen import canvas
    cel, orig, ws, _ = adwers
    doc = pdfium.PdfDocument(str(orig))
    bufor = io.BytesIO()
    c = canvas.Canvas(bufor, invariant=1)
    for i in range(len(doc)):
        im = doc[i].render(scale=200 / 72).to_pil().convert("RGB")
        w, h = doc[i].get_size()
        c.setPageSize((w * 20, h * 20))
        c.drawInlineImage(im, 0, h * 20 - h, w, h)
        c.showPage()
    c.save()
    doc.close()
    wynik = tmp_path / "duzy.pdf"
    wynik.write_bytes(bufor.getvalue())
    assert ekstrakcja.ma_duze_strony(wynik) and not ekstrakcja.ma_duze_strony(orig)
    _, wyciekly, a = _ocen_adw(orig, wynik, ws)
    widoczne = _widoczne(a, ws)
    assert len(widoczne) >= 40 and len(widoczne & wyciekly) >= 0.95 * len(widoczne), sorted(widoczne - wyciekly)


def test_m6_wartosc_obrazowa_niewykrywalna_w_obrazie_wycieka_z_renderu_strony(adwers, tmp_path, monkeypatch):
    """Wartość obrazowa niewykrywalna w OCR obrazu osadzonego (logo; oceniana przez warstwę tekstową kopii) wycieka u uczestnika
    zwracającego raster tak samo jak u uczestnika z warstwą tekstową – OCR stron dotyczy każdej grupy. Wszystkie wartości obrazowe
    są tu wymuszone jako niewykrywalne."""
    cel, orig, ws, _ = adwers
    monkeypatch.setattr(obrazy, "wykrywalne_obrazy", lambda *a, **k: set())
    a = ocen_plik(orig, orig, ws, leksykon={})
    obrazowe = set(a.bazowe) & set(a.niewykrywalne)
    assert obrazowe and obrazowe == {w.id for w in ws if w.w_pikselach} & set(a.bazowe), (a.bazowe, a.niewykrywalne)
    b = ocen_plik(orig, _raster(orig, tmp_path, True, dpi=200), ws, leksykon={})
    assert obrazowe <= {x[0] for x in b.wycieki}, sorted(obrazowe - {x[0] for x in b.wycieki})


def test_m7_dane_obrazow_inline_poza_widokami_strumieni(tmp_path):
    """Dane obrazu inline (`BI … ID <ASCII85> EI`) nie są tekstem: wycięte z widoków strumieni i surowego, tekst wokół zostaje."""
    from reportlab.pdfgen import canvas
    tresc = b"BT (Ala ma kota) Tj ET\nBI /W 2 /H 1 /BPC 8 /CS /G ID\nrue mai sin~>\nEI\nBT (Ola) Tj ET"
    wynik = ekstrakcja._bez_obrazow_inline(tresc)
    assert b"rue" not in wynik and b"(Ala ma kota)" in wynik and b"(Ola)" in wynik
    assert ekstrakcja._bez_obrazow_inline(b"BT (BIURO IDEA EI) Tj ET") == b"BT (BIURO IDEA EI) Tj ET"
    plik = tmp_path / "inline.pdf"
    c = canvas.Canvas(str(plik), invariant=1)
    c.drawString(72, 700, "Tekst strony")
    c.drawInlineImage(Image.effect_noise((300, 200), 90).convert("RGB"), 72, 300, 300, 200)
    c.save()
    with pikepdf.open(plik) as pdf:
        dane = pdf.pages[0].Contents.read_bytes()
    a85 = dane[dane.index(b" ID") + 4:][:200]
    e = wydobadz(plik)
    widoki = " ".join(d for c in e.czesci if c.nazwa in ("pdf:strumienie", "pdf:surowe") for d in c.dodatkowe)
    assert "Tekst strony" in widoki and a85.decode("latin-1") not in widoki


def test_m7_fraza_ocr_pomija_krotkie_tokeny_i_dopuszcza_rozmycie():
    """Wartość bez tokenu identyfikującego (same słowa generyczne) wycieka w OCR frazą: OCR psuje „o.o.” → „0.0.”."""
    from pbench.sedzia.plik import Tekst, dopasuj
    gen = {"eko", "serwis", "centrum", "medyczne", "sp", "z", "o"}
    reg = _regula_ocr("Eko-Serwis Centrum Medyczne sp. z o.o.", "ORGANIZACJA", generyczne=gen)
    assert not reg.identyfikujace
    assert dopasuj(reg, Tekst("Poradnia: Eko-Serwis Centrum Medyczne sp. z 0.0."), ocr=True) == "pelny"
    assert dopasuj(reg, Tekst("Poradnia: Eko-Serwis Centrun Medyczne sp. z 0.0."), ocr=True) == "pelny"
    assert dopasuj(reg, Tekst("Eko-Serwis oraz Centrum Medyczne"), ocr=True) is None            # słowo spoza wartości
    assert dopasuj(reg, Tekst("[ORGANIZACJA 3] sp. z 0.0."), ocr=True) is None


def test_m7_nazwa_z_samych_slow_generycznych_w_rastrze_wycieka_idealny_zero(tmp_path):
    """Trzon `pl-med_skierowanie-0016`: „Eko-Serwis Centrum Medyczne sp. z o.o.” i „… Jantar sp. z o.o.” w rastrze strony wyciekają;
    uczestnik idealny – 0 wycieków."""
    poz = korpus.Pozycja("pl-med_skierowanie-0016", "pl", "med_skierowanie", "pdf")
    w = korpus.generuj_dokument(poz, korpus.ZIARNO, "test", tmp_path / "o")
    r = korpus.generuj_dokument(poz, korpus.ZIARNO, "test", tmp_path / "i", maskuj=Maskowanie())
    orig, ws = tmp_path / "o" / w["plik"], wartosci_wpisu(w)
    a = ocen_plik(orig, _raster(orig, tmp_path, True, dpi=200), ws, leksykon={})
    assert {"poradnia.nazwa#2", "szpital.nazwa#1"} <= {x[0] for x in a.wycieki}, a.wycieki
    assert not ocen_plik(orig, tmp_path / "i" / r["plik"], ws, leksykon={}).wycieki


# ----------------------------------------------------------------------------- poprawki 4: trzeci odczyt, trafienia rozmyte, daty, zamienniki
def test_p1_blok_czytany_tylko_przez_psm6_potwierdza_trzeci_odczyt():
    """Blok, którego psm 3 nie czyta w żadnej rozdzielczości, ma po drugim odczycie jeden odczyt (400 dpi psm 6): brak potwierdzenia
    i prośba o trzeci odczyt (300 dpi psm 6) – ten potwierdza wyciek częściowy."""
    g = _grupa("Emma Gomez")
    STRONA_1 = "obraz:" + ekstrakcja.nazwa_renderu(1)
    assert _ocen_strony(g, "Rechnung", "Rechnung\fRechnung\n[PERSON] Gomez") == (None, 0, True)
    assert _ocen_strony(g, "Rechnung", "Rechnung\fRechnung\n[PERSON] Gomez", "Rechnung\n[PERSON] Gomez") == \
        ((STRONA_1, "czesciowy"), 1, False)
    assert obrazy.PSM_TRZECIEGO_ODCZYTU == (6,)


def _zamaz_slowa(png: bytes, jezyk: str, zamaz) -> Image.Image:
    """Obraz strony z zamazanymi słowami, które wskazuje `zamaz(slowo, poprzednie)` (pozycje z TSV Tesseracta, psm 6)."""
    im = Image.open(io.BytesIO(png)).convert("RGB")
    wejscie = io.BytesIO()
    im.save(wejscie, format="PNG")
    tsv = subprocess.run([ocr_modul._tesseract(), "stdin", "stdout", "-l", ocr_modul.KODY[jezyk], "--tessdata-dir",
                          str(ocr_modul.tessdata_dir()), "--psm", "6", "-c", "tessedit_create_tsv=1"],
                         input=wejscie.getvalue(), capture_output=True, check=True).stdout.decode("utf-8").splitlines()
    wiersze = [r.split("\t") for r in tsv[1:] if len(r.split("\t")) == 12]
    from PIL import ImageDraw
    rysuj = ImageDraw.Draw(im)
    for k, r in enumerate(wiersze):
        if zamaz(r[11].strip(",."), wiersze[k - 1][11] if k else ""):
            x, y, w, h = map(int, r[6:10])
            rysuj.rectangle([x - 3, y - 3, x + w + 3, y + h + 3], fill="white")
    return im


def test_p1_de_faktura_0007_wyciek_czesciowy_w_bloku_czytanym_tylko_przez_psm6(tmp_path):
    """Trzon `de-faktura-0007` (skan): dane kupującego stoją w bloku, który czyta tylko psm 6. Uczestnik zostawia nazwę kupującego
    bez formy prawnej (zamazuje „GmbH”, kod i miasto) – wyciek częściowy nazwy wykrywa trzeci odczyt; uczestnik idealny – 0 wycieków."""
    from reportlab.pdfgen import canvas
    poz = korpus.Pozycja("de-faktura-0007", "de", "faktura", "skan")
    w = korpus.generuj_dokument(poz, korpus.ZIARNO, "test", tmp_path / "o")
    r = korpus.generuj_dokument(poz, korpus.ZIARNO, "test", tmp_path / "i", maskuj=Maskowanie())
    orig, ws = tmp_path / "o" / w["plik"], wartosci_wpisu(w)
    (nazwa,) = {x.tekst for x in ws if x.id == "kaeufer.nazwa#1"}                 # „<człon> … GmbH”
    (adres,) = {x.tekst for x in ws if x.id == "kaeufer.adres#1"}                 # „<ulica> <numer>, <kod> <miasto>”
    *rdzen, forma = nazwa.split()
    ulica, kod_miasto = adres.rsplit(",", 1)
    kod, miasto = kod_miasto.split(maxsplit=1)
    assert forma == "GmbH" and rdzen
    zamaz = lambda t, prev: ((t == forma and rdzen[-1] in prev) or (t == kod and ulica.split()[-1] in prev)
                             or (t == miasto and prev.startswith(kod)))
    doc = pdfium.PdfDocument(str(orig))
    bufor = io.BytesIO()
    c = canvas.Canvas(bufor, invariant=1)
    for i in range(len(doc)):
        szer, wys = doc[i].get_size()
        im = doc[i].render(scale=400 / 72).to_pil().convert("RGB")
        if i == 0:
            png = io.BytesIO()
            im.save(png, format="PNG")
            im = _zamaz_slowa(png.getvalue(), "de", zamaz)
        c.setPageSize((szer, wys))
        c.drawInlineImage(im.resize((im.width * 3 // 4, im.height * 3 // 4)), 0, 0, szer, wys)
        c.showPage()
    c.save()
    doc.close()
    wynik = tmp_path / "wyciek.pdf"
    wynik.write_bytes(bufor.getvalue())
    a = ocen_plik(orig, wynik, ws, leksykon={})
    assert "kaeufer.nazwa#1" in a.bazowe
    assert ("kaeufer.nazwa#1", "czesciowy") in {(x[0], x[3]) for x in a.wycieki}, a.wycieki
    assert not ocen_plik(orig, tmp_path / "i" / r["plik"], ws, leksykon={}).wycieki


def test_n1_pelny_z_samych_trafien_rozmytych_wymaga_potwierdzenia():
    """Wartość jednotokenowa: słowo OCR rozmycie podobne do tokenu („Schustcr” ≈ „Schuster”) nie jest wyciekiem pełnym z jednego
    odczytu (jak trafienie częściowe – potrzebne potwierdzenie innym odczytem; potwierdzone – pełne); trafienie dokładne – jest.
    Słowo OCR krótsze niż 5 znaków nie trafia rozmyto wcale (śmieci „MARA” ≈ „Maria”, „EICH” ≈ „Erich” z linii tabeli)."""
    STRONA_1 = "obraz:" + ekstrakcja.nazwa_renderu(1)
    assert sedzia_plik.dopasuj(_grupa("Maria").reg_ocr, sedzia_plik.Tekst("1OSOBA 169] MARA O]"), ocr=True) is None
    assert sedzia_plik.dopasuj(_grupa("Hans Erich").reg_ocr, sedzia_plik.Tekst("EICH [E77 e 7 u ER"), ocr=True) is None
    g = _grupa("Schuster")
    assert sedzia_plik.dopasuj(g.reg_ocr, sedzia_plik.Tekst("Herr Schustcr"), ocr=True) == "pelny"
    assert _ocen_strony(g, "Herr Schustcr") == (None, 0, True)
    assert _ocen_strony(g, "Herr Schustcr", "Herr Schustcr\fHerr") == ((STRONA_1, "pelny"), 1, False)
    assert _ocen_strony(g, "Herr Schuster") == ((STRONA_1, "pelny"), 1, False)


def test_n2_daty_i_kwoty_cyfry_dokladnie_litery_rozmyto():
    """Data i kwota w OCR: cyfry dokładnie (albo litera czytana w miejscu cyfry: „b” = 6 lub 8, „G” = 6, „T” = 7), z granicami; nazwa
    miesiąca i waluta rozmyto, „r.” i waluta opcjonalne. Inna cyfra albo inna nazwa miesiąca to inna data."""
    from pbench.sedzia.plik import Tekst, dopasuj
    przypadki = {("28.11.2022 r.", "DATA", "pl"): ["28.11.2022", "28.11.2022 1.", "28.1l.2O22 r."],
                 ("16.06.2026 r.", "DATA", "pl"): ["1b.0b.202b r.", "1G.06.2026 r.", "16.06.2026 т."],
                 ("7 sierpnia 2023 r.", "DATA", "pl"): ["7 sierpma 2023 r.", "7 sicrpnia 2023 r.", "7 sierpuia 2023 r.",
                                                       "7 slerpnia 2023 r."],
                 ("3 June 2024", "DATA", "en"): ["3 Jume 2024", "3 Junc 2024", "3 Iune 2024"],
                 ("15. März 2024", "DATA", "de"): ["15. Mürz 2024", "15. Marz 2024"],
                 ("12 345,67 zł", "KWOTA", "pl"): ["12 345,67 zt", "12 345,67 z", "12 345,67", "12 345,6T zł", "l2 345,67 zł"]}
    for (tekst, kategoria, jezyk), odczyty in przypadki.items():
        reg = _regula_ocr(tekst, kategoria, jezyk=jezyk)
        for odczyt in odczyty:
            assert dopasuj(reg, Tekst(odczyt), ocr=True) == "pelny", (tekst, odczyt)
    data = _regula_ocr("28.11.2022 r.", "DATA")
    assert dopasuj(data, Tekst("w wyroku z dnia 29.11.2022 r. Sąd"), ocr=True) is None
    slownie = _regula_ocr("7 sierpnia 2023 r.", "DATA")
    assert dopasuj(slownie, Tekst("w dniu 17 sierpnia 2023 r."), ocr=True) is None
    assert dopasuj(_regula_ocr("3 June 2024", "DATA", jezyk="en"), Tekst("on 8 June 2024"), ocr=True) is None
    assert dopasuj(_regula_ocr("16.06.2026 r.", "DATA"), Tekst("18.08.2028 r."), ocr=True) is None
    assert dopasuj(_regula_ocr("12 345,67 zł", "KWOTA"), Tekst("12 345,671 zł"), ocr=True) is None
    # inna nazwa miesiąca (o jedną literę) – inna data, np. przesunięcie daty o miesiąc
    assert dopasuj(_regula_ocr("3. Juni 2024", "DATA", jezyk="de"), Tekst("am 3. Juli 2024"), ocr=True) is None
    assert dopasuj(_regula_ocr("3 de junio de 2024", "DATA", jezyk="es"), Tekst("el 3 de julio de 2024"), ocr=True) is None
    assert dopasuj(_regula_ocr("3 de junio de 2024", "DATA", jezyk="es"), Tekst("el 3 de jumio de 2024"), ocr=True) == "pelny"


def test_n3_slowo_zamiennika_chroni_tylko_w_kontekscie_zamiennika():
    """Słowo zamiennika („Alter” – DE „[ALTER_1]”) chroni tylko w kontekście zamiennika: nawias, numer. Nazwisko „Alter” obok
    „[PERSON]” to wyciek częściowy; szum wokół „<PERSON>” i „[OSOBA_1]” – bez wycieku (zob. test m3)."""
    maskuj = sedzia_plik.maskuj_zamienniki
    assert maskuj("[PERSON] Alter") == f"[{sedzia_plik.ZNAK_ZAMIENNIKA * 6}] Alter"
    assert maskuj("OSOBA_1 i PERSON 7 oraz <NAME> (PERSONA) [credit card number]").count("ǂ") == 5 + 6 + 4 + 7 + 16
    assert maskuj("Hans Alter, HANS ALTER, Alter: 45 Jahre") == "Hans Alter, HANS ALTER, Alter: 45 Jahre"
    assert maskuj("jan_name@post.test") == "jan_name@post.test"
    # n6: zwykłe słowa wartości przy „(” albo przed liczbą nie są zamiennikiem (reguły 2 i 3 tylko dla wersalików).
    for zwykly in ("account (Routing No. 281524457", "E11.9 Diabète sucré de type 2", "kontakt@example.org)"):
        assert maskuj(zwykly) == zwykly
    assert maskuj("(PERSON 3") == f"({sedzia_plik.ZNAK_ZAMIENNIKA * 6} 3"
    g = _grupa("Hans Alter")
    STRONA_1 = "obraz:" + ekstrakcja.nazwa_renderu(1)
    assert _ocen_strony(g, "Vertrag [PERSON] Alter", "Vertrag [PERSON] Alter") == ((STRONA_1, "czesciowy"), 1, False)
    assert _ocen_strony(g, "Vertrag [PERSON_1] [ALTER_2]", "Vertrag PERSON 1 ALTER 2") == (None, 0, False)


# ----------------------------------------------------------------------------- H4b fix4 I3: ucieczki w widokach surowych PDF
def _slowa_widokow(widoki: list[str]) -> set[str]:
    return {s for w in widoki for s in re.findall(r"\w+", normalizuj(w))}


def test_i3_ucieczka_osemkowa_i_znak_sterujacy_w_stringu_pdf_czescia_slowa():
    """H4b fix4 I3: w widokach surowych PDF (strumienie, bajty pliku, stringi literalne) ucieczka `\\ddd` z kodem glifu podzbioru
    czcionki („prawn\\002” – „prawną”) i znak sterujący zdekodowanego stringu („PRAWN\\x02”) są częścią słowa, nie granicą: brak
    słowa „prawn” (forma z pustą końcówką „Prawna” z wartości „Kancelaria Prawna Mazovia sp. z o.o.”). Ucieczka znaku ASCII
    drukowalnego albo białego to ten znak („Jan\\040Kowalski” – dwa słowa, wartość nadal trafia)."""
    strumien = b"BT /F1 12 Tf (Umowa o sta\\001\\002 obs\\003ug\\004 prawn\\002) Tj (Jan\\040Kowalski) Tj (\\050x\\051) Tj ET"
    widoki = ekstrakcja._widoki_strumienia(strumien)
    assert "prawn" not in _slowa_widokow(widoki) and {"jan", "kowalski"} <= _slowa_widokow(widoki)
    assert any("(x)" in w for w in widoki)
    stringi = ekstrakcja._stringi_pdf_z_bajtow(b"<< /Title (PRAWN\\002 MAZ\\001) /Author (Jan\\040Kowalski\\tA) >>")
    assert "prawn" not in _slowa_widokow(stringi) and {"jan", "kowalski"} <= _slowa_widokow(stringi)
    surowe = ekstrakcja._surowe_pdf(b"%PDF-1.4\n1 0 obj << /Title (PRAWN\\002) /Subject (prawn\\002) >> endobj\n")
    assert "prawn" not in _slowa_widokow(surowe)


def test_i3_idealny_pdf_kod_glifu_w_strumieniu_zero(tmp_path):
    """H4b fix4 I3: `h-uf-pl-wezwanie-0001` (ukryta_pdf) – w strumieniu stoi „kancelari\\003” („kancelarią” w podzbiorze czcionki:
    końcówka to kod glifu), a wartość `kancelaria.nazwa` („Kancelaria Prawna …”) zawiera to słowo. Kod glifu jest częścią słowa,
    nie jego granicą: idealny uczestnik ma 0 wycieków (także częściowych z `pdf:strumienie`/`pdf:surowe`), a oryginał nadal
    wycieka tę wartość."""
    poz = trudne.PozycjaTrudna("h-uf-pl-wezwanie-0001", "pl", "wezwanie", "pdf", P.UKRYTA_PDF)
    w = trudne.generuj_dokument_trudny(poz, trudne.ZIARNO_TRUDNE, "test", tmp_path / "o")
    orig = tmp_path / "o" / w["plik"]
    ws = wartosci_wpisu(w)
    slowo = next(x.tekst.split()[0].lower() for x in ws if x.id.startswith("kancelaria.nazwa"))      # „kancelaria”
    with pikepdf.open(orig) as pdf:
        strumienie = b"".join(s.read_bytes() for p in pdf.pages for s in (p.Contents if isinstance(p.Contents, pikepdf.Array)
                                                                          else [p.Contents]))
    assert re.search(rb"(?i)" + re.escape(slowo[:-1].encode()) + rb"\\\d{3}", strumienie)         # kod glifu w miejscu końcówki
    assert any(x[0].startswith("kancelaria.nazwa") for x in ocen_plik(orig, orig, ws, leksykon={}).wycieki)
    ideal = _uczestnik(P.UKRYTA_PDF, w, tmp_path / "ideal", Maskowanie())
    b = ocen_plik(orig, ideal, ws, leksykon={})
    assert b.status == "OK" and b.wycieki == [], b.wycieki
