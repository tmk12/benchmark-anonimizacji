"""Testy sędziego plikowego i obrazowego: wyciek wartości w dowolnym miejscu pliku, integralność, spójność."""
from __future__ import annotations

import io
import json
import os
import re
import zipfile
from email.message import EmailMessage
from pathlib import Path

import pikepdf
import pytest
from docx import Document
from openpyxl import Workbook
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas

from pbench import ocr
from pbench.model import Wartosc
from pbench.sedzia import obrazy
from pbench.sedzia.plik import ocen_plik as _ocen_plik

pytestmark = pytest.mark.filterwarnings("ignore")


def ocen_plik(*a, **k):
    """`leksykon` jest wymagany w API; testy domyślnie świadomie bez leksykonu korpusu (`{}`)."""
    k.setdefault("leksykon", {})
    return _ocen_plik(*a, **k)
CZCIONKA = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


@pytest.fixture(scope="session")
def _katalog_cache_ocr(tmp_path_factory):
    return tmp_path_factory.mktemp("ocr-cache")


@pytest.fixture(autouse=True)
def _cache_ocr(_katalog_cache_ocr, monkeypatch):
    monkeypatch.setenv("PBENCH_OCR_CACHE", str(_katalog_cache_ocr))   # wspólny dla testów procesu: miniatury docx


def W(wid: str, tekst: str, kat: str = "OSOBA", miejsce: str = "tresc", jezyk: str = "pl") -> Wartosc:
    return Wartosc(wid, kat, tekst, jezyk, miejsce, kat)


def _docx(sciezka: Path, akapity=("Umowa zawarta w Warszawie.",), stopka=None, autor=None, runy=None) -> Path:
    d = Document()
    for a in akapity:
        d.add_paragraph(a)
    if runy:
        p = d.add_paragraph()
        for r in runy:
            p.add_run(r)
    if stopka:
        d.sections[0].footer.paragraphs[0].text = stopka
    if autor:
        d.core_properties.author = autor
    d.save(sciezka)
    return sciezka


def _obraz_z_tekstem(tekst: str, rozmiar: int = 48) -> bytes:
    f = ImageFont.truetype(CZCIONKA, rozmiar)
    szer = int(ImageDraw.Draw(Image.new("L", (1, 1))).textlength(tekst, font=f)) + 80
    im = Image.new("RGB", (szer, rozmiar * 2 + 40), "white")
    ImageDraw.Draw(im).text((40, 30), tekst, font=f, fill="black")
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


# ----------------------------------------------------------------------------- wyciek: miejsca w pliku
def test_wartosc_w_stopce_wykryta(tmp_path):
    org = _docx(tmp_path / "o.docx", ("Zwykły tekst.",), stopka="Kancelaria Adam Zielinski i Wspolnicy")
    o = ocen_plik(org, org, [W("os#1", "Adam Zielinski")])
    assert [w[0] for w in o.wycieki] == ["os#1"]
    assert "footer" in o.wycieki[0][2]


def test_wartosc_w_metadanych_wykryta(tmp_path):
    org = _docx(tmp_path / "o.docx", autor="Barbara Wieczorek")
    wyn = _docx(tmp_path / "w.docx", ("Umowa zawarta w Warszawie.",), autor="Barbara Wieczorek")
    o = ocen_plik(org, wyn, [W("os#1", "Barbara Wieczorek", miejsce="metadane")])
    assert [w[0] for w in o.wycieki] == ["os#1"]
    assert "core.xml" in o.wycieki[0][2]


def test_wartosc_rozbita_na_runy_wykryta(tmp_path):
    wyn = _docx(tmp_path / "w.docx", runy=["Pozwany Jan Kowa", "lski", " zamieszkały"])
    org = _docx(tmp_path / "o.docx", runy=["Pozwany Jan Kowalski zamieszkały"])
    o = ocen_plik(org, wyn, [W("os#1", "Jan Kowalski")])
    assert [w[0] for w in o.wycieki] == ["os#1"] and o.wycieki[0][3] == "pelny"


def test_pdf_strumien_skompresowany_wykryty(tmp_path):
    p = tmp_path / "w.pdf"
    c = canvas.Canvas(str(p), pageCompression=1)
    c.setTitle("Pismo")
    c.setAuthor("Zofia Kaminska")
    c.drawString(72, 700, "Tresc bez danych.")
    c.save()
    org = tmp_path / "o.pdf"
    c = canvas.Canvas(str(org), pageCompression=1)
    c.drawString(72, 700, "Tresc bez danych. Zofia Kaminska podpisala.")
    c.save()
    o = ocen_plik(org, p, [W("os#1", "Zofia Kaminska", miejsce="metadane")])
    assert [w[0] for w in o.wycieki] == ["os#1"] and "Info" in o.wycieki[0][2]
    p2 = tmp_path / "w2.pdf"
    c = canvas.Canvas(str(p2), pageCompression=1)
    c.drawString(72, 700, "Podpisala Zofia Kaminska.")
    c.save()
    assert b"Podpisala" not in p2.read_bytes()  # tekst strony leży w skompresowanym strumieniu
    o2 = ocen_plik(org, p2, [W("os#1", "Zofia Kaminska")])
    assert [w[0] for w in o2.wycieki] == ["os#1"] and "strona" in o2.wycieki[0][2]


@pytest.mark.skipif(not ocr.dostepny("pl"), reason="brak Tesseracta")
def test_wartosc_na_obrazie_wykryta_ocr(tmp_path):
    def z_obrazem(sciezka: Path, tekst: str) -> Path:
        d = Document()
        d.add_paragraph("Logo poniżej.")
        d.add_picture(io.BytesIO(_obraz_z_tekstem(tekst)))
        d.save(sciezka)
        return sciezka
    org = z_obrazem(tmp_path / "o.docx", "Marcin Wisniewski")
    w = W("os#1@obraz", "Marcin Wisniewski", miejsce="obraz")
    assert obrazy.wykrywalne_obrazy(org, [w]) == {"os#1@obraz"}
    o = ocen_plik(org, org, [w])
    assert [x[0] for x in o.wycieki] == ["os#1@obraz"] and "media" in o.wycieki[0][2]
    czysty = z_obrazem(tmp_path / "c.docx", "[OSOBA_1]")
    assert ocen_plik(org, czysty, [w]).wycieki == []


def test_wartosc_niewykrywalna_na_obrazie_wylaczona(tmp_path, monkeypatch):
    org = _docx(tmp_path / "o.docx")
    monkeypatch.setattr(obrazy, "wykrywalne_obrazy", lambda *a, **k: set())
    o = ocen_plik(org, org, [W("os#1@obraz", "Marcin Wisniewski", miejsce="obraz")])
    assert o.wycieki == [] and o.niewykrywalne == ["os#1@obraz"]


def test_plik_uszkodzony_to_nieczytelny(tmp_path):
    org = _docx(tmp_path / "o.docx")
    zly = tmp_path / "w.docx"
    zly.write_bytes(b"to nie jest zip" * 20)
    o = ocen_plik(org, zly, [W("os#1", "Jan Kowalski")])
    assert o.status == "NIECZYTELNY" and o.wycieki == [] and o.integralnosc["otwiera_sie"] is False
    obciety = tmp_path / "o2.docx"
    obciety.write_bytes(org.read_bytes()[:200])
    assert ocen_plik(org, obciety, []).status == "NIECZYTELNY"


def test_plik_pusty_to_pusty(tmp_path):
    org = _docx(tmp_path / "o.docx")
    pusty = tmp_path / "w.docx"
    pusty.write_bytes(b"")
    assert ocen_plik(org, pusty, []).status == "PUSTY"
    assert ocen_plik(org, tmp_path / "brak.docx", []).status == "PUSTY"
    bez_tresci = tmp_path / "b.docx"
    Document().save(bez_tresci)
    assert ocen_plik(org, bez_tresci, []).status == "PUSTY"


def test_wynik_czysty_zero_wyciekow(tmp_path):
    org = _docx(tmp_path / "o.docx", ("Strona: Jan Kowalski, PESEL 44051401359.", "Adres: ul. Długa 5, Łódź."),
                stopka="Jan Kowalski", autor="Jan Kowalski")
    czysty = _docx(tmp_path / "c.docx", ("Strona: [OSOBA_1], PESEL [PESEL_1].", "Adres: ul. Długa 5, Łódź."),
                   stopka="[OSOBA_1]", autor="Użytkownik")
    ws = [W("os#1", "Jan Kowalski"), W("pesel#1", "44051401359", "PESEL"), W("os#2", "Jan Kowalski", miejsce="stopka")]
    assert [x[0] for x in ocen_plik(org, org, ws).wycieki] == ["os#1", "pesel#1", "os#2"]
    o = ocen_plik(org, czysty, ws)
    assert o.status == "OK" and o.wycieki == [] and o.integralnosc["otwiera_sie"] is True


# ----------------------------------------------------------------------------- reguły wycieku
def test_identyfikator_normalizowany_i_token_generyczny(tmp_path):
    org = _docx(tmp_path / "o.docx", ("Kancelaria Prawna Nowak wystąpiła; Kancelaria Prawna działa; PESEL 44-05-14 01359",))
    ws = [W("o#1", "Kancelaria Prawna Nowak", "ORGANIZACJA"), W("p#1", "44051401359", "PESEL")]
    # w wyniku zostało tylko generyczne „Kancelaria Prawna” → bez wycieku; PESEL z separatorami → wyciek
    wyn = _docx(tmp_path / "w.docx", ("Kancelaria Prawna [ORG]; PESEL 44-05-14 01359",))
    assert [x[0] for x in ocen_plik(org, wyn, ws).wycieki] == ["p#1"]
    wyn2 = _docx(tmp_path / "w2.docx", ("Pan Nowak, Kancelaria",))
    o = ocen_plik(org, wyn2, ws)
    assert [(x[0], x[3]) for x in o.wycieki] == [("o#1", "czesciowy")]


def test_forma_odmieniona_trafia_prefiksowo(tmp_path):
    org = _docx(tmp_path / "o.docx", ("Powód Jan Kowalski wnosi.",))
    wyn = _docx(tmp_path / "w.docx", ("Przeciwko Kowalskiemu wniesiono.",))
    assert [x[0] for x in ocen_plik(org, wyn, [W("os#1", "Jan Kowalski")]).wycieki] == ["os#1"]


def test_xlsx_naglowek_wydruku_z_ampersandami(tmp_path):
    def xl(p: Path, naglowek: str) -> Path:
        wb = Workbook()
        ws = wb.active
        ws["A1"] = "Lista"
        ws.oddHeader.center.text = naglowek
        wb.save(p)
        return p
    org = xl(tmp_path / "o.xlsx", "Kancelaria Nowak && Wspólnicy")
    o = ocen_plik(org, org, [W("o#1", "Nowak & Wspólnicy", "ORGANIZACJA")])
    assert [x[0] for x in o.wycieki] == ["o#1"]
    assert ocen_plik(org, xl(tmp_path / "w.xlsx", "Kancelaria [ORG]"), [W("o#1", "Nowak & Wspólnicy", "ORGANIZACJA")]).wycieki == []


def test_eml_naglowek_rfc2047_i_zalacznik(tmp_path):
    def eml(p: Path, od: str, zal: bytes | None) -> Path:
        m = EmailMessage()
        m["From"] = od
        m["Subject"] = "Sprawa"
        m.set_content("Treść wiadomości.", charset="utf-8", cte="quoted-printable")
        if zal:
            m.add_attachment(zal, maintype="application", subtype="octet-stream", filename="notatka.docx")
        p.write_bytes(m.as_bytes())
        return p
    _docx(tmp_path / "z.docx", ("Klient Piotr Zawadzki",))
    org = eml(tmp_path / "o.eml", "Łukasz Żółkiewski <lz@mail.test>", (tmp_path / "z.docx").read_bytes())
    ws = [W("nad#1", "Łukasz Żółkiewski", miejsce="metadane"), W("zal:os#1", "Piotr Zawadzki", miejsce="zalacznik")]
    o = ocen_plik(org, org, ws)
    assert {x[0] for x in o.wycieki} == {"nad#1", "zal:os#1"}
    miejsca = {x[0]: x[2] for x in o.wycieki}
    assert "notatka.docx" in miejsca["zal:os#1"] and "word/document.xml" in miejsca["zal:os#1"]
    assert miejsca["nad#1"] == "eml:naglowki"
    _docx(tmp_path / "z2.docx", ("Klient [OSOBA_2]",))
    czysty = eml(tmp_path / "c.eml", "[OSOBA_1] <x@mail.test>", (tmp_path / "z2.docx").read_bytes())
    assert ocen_plik(org, czysty, ws).wycieki == []


# ----------------------------------------------------------------------------- integralność i spójność
def test_struktura_i_spojnosc(tmp_path):
    org = _docx(tmp_path / "o.docx", ("Powód Jan Kowalski.", "Pozwany Piotr Nowak.", "Jan Kowalski podpisał.",
                                      "Piotr Nowak również."))
    ws = [W("p.pelne#1", "Jan Kowalski"), W("p.pelne#2", "Jan Kowalski"), W("r.pelne#1", "Piotr Nowak"),
          W("r.pelne#2", "Piotr Nowak")]
    dobry = _docx(tmp_path / "d.docx", ("Powód [OSOBA_1].", "Pozwany [OSOBA_2].", "[OSOBA_1] podpisał.",
                                        "[OSOBA_2] również."))
    o = ocen_plik(org, dobry, ws)
    assert o.wycieki == [] and o.integralnosc["spojnosc"] == 1.0 and o.integralnosc["zachowanie_struktury"] == 1.0
    zly = _docx(tmp_path / "z.docx", ("Powód [OSOBA_1].", "Pozwany [OSOBA_2].", "[OSOBA_3] podpisał.",
                                      "[OSOBA_2] również."))
    assert ocen_plik(org, zly, ws).integralnosc["spojnosc"] == 0.5
    mniej = _docx(tmp_path / "m.docx", ("Powód [OSOBA_1].", "[OSOBA_1] podpisał."))
    assert ocen_plik(org, mniej, ws).integralnosc["zachowanie_struktury"] < 1.0
    # wartość niezamaskowana w jednym wystąpieniu: encja nie liczy się do spójności
    czesc = _docx(tmp_path / "cz.docx", ("Powód Jan Kowalski.", "Pozwany [OSOBA_2].", "[OSOBA_1] podpisał.",
                                         "[OSOBA_2] również."))
    assert ocen_plik(org, czesc, ws).integralnosc["spojnosc"] == 1.0


def test_oryginal_jako_wynik_znajduje_wszystko_w_zip_i_surowych_bajtach(tmp_path):
    org = tmp_path / "o.docx"
    _docx(org, ("Tekst.",))
    with zipfile.ZipFile(org, "a") as z:
        z.writestr("customXml/item1.xml", "<r><x>Henryk Sienkiewicz</x></r>")
    o = ocen_plik(org, org, [W("os#1", "Henryk Sienkiewicz", miejsce="metadane")])
    assert [x[0] for x in o.wycieki] == ["os#1"]


# ----------------------------------------------------------------------------- dalsze reguły i formaty
def test_data_nie_wycieka_samym_rokiem_z_metadanych(tmp_path):
    org = _docx(tmp_path / "o.docx", ("Rozprawa odbędzie się 08/07/2025 w sali nr 5.",))
    wyn = _docx(tmp_path / "w.docx", ("Rozprawa odbędzie się [DATA_1] w sali nr 5. Wydruk z 2025 roku.",))
    d = W("d#1", "08/07/2025", "DATA")
    assert ocen_plik(org, wyn, [d]).wycieki == []
    assert [x[0] for x in ocen_plik(org, _docx(tmp_path / "w2.docx", ("Termin 08.07.2025",)), [d]).wycieki] == ["d#1"]


def test_identyfikator_nie_trafia_w_dlugi_ciag_cyfr(tmp_path):
    org = _docx(tmp_path / "o.docx", ("Rachunek 12345678901234.",))
    wyn = _docx(tmp_path / "w.docx", ("Numer 9912345678901234567 i [IBAN_1].",))
    assert ocen_plik(org, wyn, [W("r#1", "12345678901234", "RACHUNEK")]).wycieki == []


def test_kwota_jako_liczba_w_komorce_xlsx(tmp_path):
    def xl(p: Path, v) -> Path:
        wb = Workbook()
        wb.active["A1"] = v
        wb.save(p)
        return p
    org = xl(tmp_path / "o.xlsx", 753.46)
    k = W("k#1", "753,46 €", "KWOTA", miejsce="tabela")
    assert [x[0] for x in ocen_plik(org, org, [k]).wycieki] == ["k#1"]
    assert ocen_plik(org, xl(tmp_path / "w.xlsx", "[KWOTA_1]"), [k]).wycieki == []
    assert ocen_plik(org, xl(tmp_path / "w2.xlsx", 9753.46), [k]).wycieki == []


def test_wartosc_niejednoznaczna_jest_wylaczona(tmp_path):
    # „Hamburg” jest gold (adres), ale także w nazwie sądu (nie-gold): pozostałe wystąpienie nie jest wyciekiem
    org = _docx(tmp_path / "o.docx", ("Amtsgericht Hamburg orzekł. Spółka ma siedzibę: Hamburg.",))
    wyn = _docx(tmp_path / "w.docx", ("Amtsgericht Hamburg orzekł. Spółka ma siedzibę: [MIEJSCOWOSC_1].",))
    m = W("m#1", "Hamburg", "MIEJSCOWOSC")
    o = ocen_plik(org, wyn, [m])
    assert o.wycieki == [] and o.niejednoznaczne == ["m#1"] and o.wartosci_ocenione == 0


def test_czesci_strukturalne_nie_sa_skanowane(tmp_path):
    org = _docx(tmp_path / "o.docx", ("Pozwany Roman Nowak.",))
    wyn = _docx(tmp_path / "w.docx", ("Pozwany [OSOBA_1].",))  # styles/fontTable zawierają „Times New Roman”
    assert ocen_plik(org, wyn, [W("o#1", "Roman"), W("o#2", "Roman Nowak")]).wycieki == []


def test_msg_wlasciwosci_i_zalacznik(tmp_path):
    from pbench.render.cfb import zapisz_cfb
    from pbench.render.msg import PROPS
    def msg(p: Path, temat: str, od: str, zal: bytes) -> Path:
        a = {PROPS: b"\0" * 32, "__substg1.0_3701" + "0102": zal, "__substg1.0_3707001F": "n.docx".encode("utf-16-le")}
        korzen = {PROPS: b"\0" * 32, "__substg1.0_0037001F": temat.encode("utf-16-le"),
                  "__substg1.0_0C1A001E": od.encode("cp1252"), "__substg1.0_1000001F": "Treść".encode("utf-16-le"),
                  "__attach_version1.0_#00000000": a}
        zapisz_cfb(p, korzen)
        return p
    _docx(tmp_path / "z.docx", ("Klient Teresa Pawlak",))
    org = msg(tmp_path / "o.msg", "Sprawa Pawlak Teresa", "Adam Wrona", (tmp_path / "z.docx").read_bytes())
    ws = [W("t#1", "Teresa Pawlak", miejsce="zalacznik"), W("a#1", "Adam Wrona", miejsce="metadane")]
    o = ocen_plik(org, org, ws)
    assert {x[0] for x in o.wycieki} == {"t#1", "a#1"}
    _docx(tmp_path / "z2.docx", ("Klient [OSOBA_1]",))
    czysty = msg(tmp_path / "c.msg", "Sprawa [OSOBA_1]", "[OSOBA_2]", (tmp_path / "z2.docx").read_bytes())
    assert ocen_plik(org, czysty, ws).wycieki == []
    assert ocen_plik(org, tmp_path / "z.docx", ws).status == "OK"  # inny format: czytelny…
    assert ocen_plik(org, tmp_path / "z.docx", ws).integralnosc["format_zgodny"] is False
    # P12-1: format zamieniony na odpowiednik → zachowanie struktury „nie dotyczy” (None), nie 0.0; serializuje się jako null
    zam = ocen_plik(org, tmp_path / "z.docx", ws).integralnosc
    assert zam["zachowanie_struktury"] is None
    assert json.loads(json.dumps(zam))["zachowanie_struktury"] is None


def test_pdf_adnotacja_pole_i_xmp(tmp_path):
    def pdf(p: Path, komentarz: str, pole: str, xmp_autor: str) -> Path:
        c = canvas.Canvas(str(p), pageCompression=1)
        c.drawString(72, 700, "Pismo procesowe.")
        c.save()
        with pikepdf.open(p, allow_overwriting_input=True) as d:
            d.pages[0].Annots = d.make_indirect(pikepdf.Array([d.make_indirect(pikepdf.Dictionary(
                Type=pikepdf.Name.Annot, Subtype=pikepdf.Name.Text, Rect=[0, 0, 10, 10], Contents=pikepdf.String(komentarz),
                T=pikepdf.String("Recenzent")))]))
            d.Root.AcroForm = d.make_indirect(pikepdf.Dictionary(Fields=pikepdf.Array([d.make_indirect(pikepdf.Dictionary(
                FT=pikepdf.Name.Tx, T=pikepdf.String("pole1"), V=pikepdf.String(pole)))])))
            with d.open_metadata() as m:
                m["dc:creator"] = [xmp_autor]
            d.save(p)
        return p
    org = pdf(tmp_path / "o.pdf", "Do sprawdzenia: Ewa Mazur", "Ewa Mazur", "Ewa Mazur")
    for gdzie, ws in (("pdf:słowniki", W("w#1", "Ewa Mazur")),):
        o = ocen_plik(org, org, [ws])
        assert [x[0] for x in o.wycieki] == ["w#1"]
    czysty = pdf(tmp_path / "c.pdf", "Do sprawdzenia: [OSOBA_1]", "[OSOBA_1]", "[OSOBA_1]")
    assert ocen_plik(org, czysty, [W("w#1", "Ewa Mazur")]).wycieki == []
    tylko_xmp = pdf(tmp_path / "x.pdf", "ok", "ok", "Ewa Mazur")
    o = ocen_plik(org, tylko_xmp, [W("w#1", "Ewa Mazur")])
    assert [x[0] for x in o.wycieki] == ["w#1"] and o.wycieki[0][3] == "pelny"


def test_pptx_slajdy_i_stopka_na_kazdym_slajdzie(tmp_path):
    from pptx import Presentation
    def pptx(p: Path, stopka: str, slajdow: int = 2) -> Path:
        pr = Presentation()
        for _ in range(slajdow):
            s = pr.slides.add_slide(pr.slide_layouts[5])
            s.shapes.title.text = "Temat"
            tb = s.shapes.add_textbox(0, 0, 100, 100)
            tb.text_frame.text = stopka
        pr.save(p)
        return p
    org = pptx(tmp_path / "o.pptx", "Kancelaria Gołębiowski")
    w = [W(f"f#{i}", "Gołębiowski", "ORGANIZACJA", miejsce="stopka") for i in (1, 2)]   # po jednej na slajd
    assert [x[0] for x in ocen_plik(org, org, w).wycieki] == ["f#1", "f#2"]
    mniej = ocen_plik(org, pptx(tmp_path / "w.pptx", "[ORG]", 1), w)
    assert mniej.wycieki == [] and mniej.integralnosc["struktura"]["wynik"] == {"slajdy": 1}
    assert mniej.integralnosc["zachowanie_struktury"] == 0.5


def test_ocr_tolerancja_bledu_znaku(tmp_path):
    from pbench.sedzia import plik
    assert obrazy.zawiera_rozmyto("pl61109010140000071219812874", "xx pl6l109010140000071219812874 yy")
    assert not obrazy.zawiera_rozmyto("pl61109010140000071219812874", "zupelnie inny tekst 1234567890")
    assert obrazy.slowo_rozmyte("wisniewski", {"wisniewskl", "inne"})
    assert not obrazy.slowo_rozmyte("wisniewski", {"kowalski", "inne"})


def test_spojnosc_pomija_niejednoznaczne_dopasowanie(tmp_path):
    org = _docx(tmp_path / "o.docx", ("Strony: Jan Kowalski Piotr Nowak.", "Jan Kowalski i Piotr Nowak."))
    ws = [W("p.pelne#1", "Jan Kowalski"), W("p.pelne#2", "Jan Kowalski"), W("r.pelne#1", "Piotr Nowak"),
          W("r.pelne#2", "Piotr Nowak")]
    wyn = _docx(tmp_path / "w.docx", ("Strony: [A] [B].", "[A] i [B]."))
    o = ocen_plik(org, wyn, ws)
    assert o.integralnosc["spojnosc"] is None and o.integralnosc["encje"]["pominiete"] == 2


# ----------------------------------------------------------------------------- runda poprawek 1 (testy kontradyktoryjne)
def _zip_mod(src: Path, dst: Path, mods=None, add=None) -> Path:
    mods, add = mods or {}, add or {}
    with zipfile.ZipFile(src) as z, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as o:
        for inf in z.infolist():
            d = z.read(inf)
            o.writestr(inf.filename, mods[inf.filename](d) if inf.filename in mods else d)
        for n, d in add.items():
            o.writestr(n, d)
    return dst


def _pdf_tekst(p: Path, linie=("Pismo procesowe.",), autor=None) -> Path:
    c = canvas.Canvas(str(p), pageCompression=1)
    if autor:
        c.setAuthor(autor)
    for i, l in enumerate(linie):
        c.drawString(72, 700 - 20 * i, l)
    c.save()
    return p


def _pdf_obraz(p: Path, png: bytes) -> Path:
    from reportlab.lib.utils import ImageReader
    c = canvas.Canvas(str(p), pageCompression=1)
    c.drawImage(ImageReader(io.BytesIO(png)), 40, 600, 500, 120)
    c.save()
    return p


def _pdf_modyfikuj(src: Path, dst: Path, fn) -> Path:
    with pikepdf.open(src) as pdf:
        fn(pdf)
        pdf.save(dst)
    return dst


@pytest.mark.skipif(not ocr.dostepny("pl"), reason="brak Tesseracta")
def test_c1_tekst_rasteryzowany_do_pdf_obrazowego_wykryty(tmp_path):
    org = _pdf_tekst(tmp_path / "o.pdf", ("Strony: Marcin Wisniewski i inni.",))
    import pypdfium2 as pdfium
    obraz = pdfium.PdfDocument(str(org))[0].render(scale=3).to_pil().convert("RGB")
    b = io.BytesIO()
    obraz.save(b, "PNG")
    raster = _pdf_obraz(tmp_path / "r.pdf", b.getvalue())
    o = ocen_plik(org, raster, [W("os#1", "Marcin Wisniewski")])
    assert [x[0] for x in o.wycieki] == ["os#1"] and o.wycieki[0][2].startswith("obraz:")


@pytest.mark.skipif(not ocr.dostepny("pl"), reason="brak Tesseracta")
def test_c1_wartosc_tekstowa_narysowana_w_obrazie_docx(tmp_path):
    org = _docx(tmp_path / "o.docx", ("Pozwany Henryk Lesniak.",))
    wyn = _zip_mod(_docx(tmp_path / "c.docx", ("Pozwany [OSOBA_1].",)), tmp_path / "w.docx",
                   add={"word/media/x.png": _obraz_z_tekstem("Henryk Lesniak")})
    o = ocen_plik(org, wyn, [W("os#1", "Henryk Lesniak")])
    assert [x[0] for x in o.wycieki] == ["os#1"] and "media" in o.wycieki[0][2]


@pytest.mark.skipif(not ocr.dostepny("pl"), reason="brak Tesseracta")
def test_c1_skan_z_ukrytym_tekstem_i_info(tmp_path):
    org = _pdf_obraz(tmp_path / "o.pdf", _obraz_z_tekstem("Kontakt: Marcin Wisniewski"))
    ukryty = _pdf_modyfikuj(org, tmp_path / "u.pdf", lambda pdf: _ukryty_tekst(pdf, "renata@poczta.test"))
    w = [W("em#1", "renata@poczta.test", "EMAIL"), W("os#1", "Marcin Wisniewski", miejsce="obraz")]
    assert [x[0] for x in ocen_plik(org, ukryty, w[:1]).wycieki] == ["em#1"]
    info = _pdf_modyfikuj(org, tmp_path / "i.pdf", lambda pdf: pdf.docinfo.__setitem__("/Author", "Marcin Wisniewski"))
    assert "pdf:/Info" in {x[2] for x in ocen_plik(org, info, [W("os#2", "Marcin Wisniewski")]).wycieki}


def _ukryty_tekst(pdf, tekst: str) -> None:
    pg = pdf.pages[0]
    res = pg.obj.Resources
    if "/Font" not in res:
        res.Font = pikepdf.Dictionary()
    res.Font.FZZ = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica)
    pg.contents_add(pdf.make_stream(b"BT /FZZ 8 Tf 3 Tr 10 10 Td (" + tekst.encode("latin-1") + b") Tj ET"), prepend=False)


def test_c2_widoki_sklejone_nie_zatruwaja_slow_generycznych(tmp_path):
    # koniec poprzedniego akapitu skleja się z początkiem wartości w widoku bez znaczników („PowódHenryk”)
    org = _docx(tmp_path / "o.docx", ("Strona pozwana to Powód", "Henryk Leśniak", "mieszka w Łodzi."))
    wyn = _docx(tmp_path / "w.docx", ("Strona pozwana to Powód", "Henryk [OSOBA_1]", "mieszka w Łodzi."))
    o = ocen_plik(org, wyn, [W("os#1", "Henryk Leśniak")])
    assert [(x[0], x[3]) for x in o.wycieki] == [("os#1", "czesciowy")]


def test_c3_krotnosc_gold_zapobiega_falszywej_niejednoznacznosci(tmp_path):
    org = _docx(tmp_path / "o.docx", ("Kancelaria Zbigniew Orłowski", "treść", "Kancelaria Zbigniew Orłowski"))
    jedna = [W("n#1", "Zbigniew Orłowski", miejsce="naglowek")]
    assert ocen_plik(org, org, jedna).niejednoznaczne == ["n#1"]
    dwie = [W("n#1", "Zbigniew Orłowski", miejsce="naglowek")] * 2
    o = ocen_plik(org, org, dwie)
    assert o.niejednoznaczne == [] and [x[0] for x in o.wycieki] == ["n#1"]


def test_i1_leksykon_wyklucza_pojedynczy_token_ale_nie_pelna_wartosc(tmp_path):
    org = _docx(tmp_path / "o.docx", ("Powód Anna Zielińska wnosi.",))
    wyn = _docx(tmp_path / "w.docx", ("Anna [OSOBA_1] wnosi.",))
    w = [W("os#1", "Anna Zielińska")]
    assert [x[3] for x in ocen_plik(org, wyn, w).wycieki] == ["czesciowy"]
    assert ocen_plik(org, wyn, w, leksykon={"pl": frozenset({"anna"})}).wycieki == []
    assert [x[3] for x in ocen_plik(org, org, w, leksykon={"pl": frozenset({"anna"})}).wycieki] == ["pelny"]


def test_i1_zbuduj_leksykon_progiem_dokumentow():
    from pbench.sedzia.plik import zbuduj_leksykon
    wpisy = [{"jezyk": "pl", "gold_obrazy": [], "gold_plik": [{"tekst": f"Anna Nazwisko{i}"}]} for i in range(40)]
    lek = zbuduj_leksykon(wpisy, 0.05)
    assert "anna" in lek["pl"] and "nazwisko3" not in lek["pl"]


def test_i2_zamiennik_z_przypadkowo_zgodnym_slowem(tmp_path):
    org = _docx(tmp_path / "o.docx", ("Powód Jan Maria Kowalski wnosi.", "Jan Maria Kowalski podpisał."))
    wyn = _docx(tmp_path / "w.docx", ("Powód Piotr Maria Nowak wnosi.", "Piotr Maria Nowak podpisał."))
    ws = [W("p#1", "Jan Maria Kowalski"), W("p#2", "Jan Maria Kowalski")]
    o = ocen_plik(org, wyn, ws)
    assert o.integralnosc["spojnosc"] == 1.0


def test_i3_pdf_slowniki_zagniezdzone_i_stare_rewizje(tmp_path):
    base = _pdf_tekst(tmp_path / "b.pdf")
    def link(pdf):
        a = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Annot, Subtype=pikepdf.Name.Link, Rect=[0, 0, 5, 5],
                                                 A=pikepdf.Dictionary(S=pikepdf.Name.URI, URI=pikepdf.String("mailto:ewa.mazur@poczta.test"))))
        pdf.pages[0].obj.Annots = pdf.make_indirect(pikepdf.Array([a]))
    def mk(pdf):
        a = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Annot, Subtype=pikepdf.Name.Widget, Rect=[0, 0, 5, 5],
                                                 MK=pikepdf.Dictionary(CA=pikepdf.String("Ewa Mazur"))))
        pdf.pages[0].obj.Annots = pdf.make_indirect(pikepdf.Array([a]))
    def js(pdf):
        pdf.Root.OpenAction = pikepdf.Dictionary(S=pikepdf.Name.JavaScript, JS=pikepdf.String('var k="Ewa Mazur";'))
    for nazwa, fn in (("link", link), ("mk", mk), ("js", js)):
        p = _pdf_modyfikuj(base, tmp_path / f"{nazwa}.pdf", fn)
        ws = [W("e#1", "ewa.mazur@poczta.test", "EMAIL")] if nazwa == "link" else [W("o#1", "Ewa Mazur")]
        assert ocen_plik(base, p, ws).wycieki, nazwa
    # osierocony obiekt ze strumieniem (jak stara rewizja po aktualizacji przyrostowej): poza tablicą xref
    import zlib
    surowy = base.read_bytes()
    strumien = zlib.compress("Strona: Ewa Mazur.".encode())
    obiekt = b"99 0 obj\n<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(strumien) + strumien + b"\nendstream\nendobj\n"
    i = surowy.rindex(b"xref\n", 0, surowy.rindex(b"trailer"))
    polaczony = tmp_path / "p.pdf"
    polaczony.write_bytes(surowy[:i] + obiekt + surowy[i:])
    o = ocen_plik(base, polaczony, [W("o#1", "Ewa Mazur")])
    assert o.status == "OK" and [x[0] for x in o.wycieki] == ["o#1"]


def test_i4_czesci_strukturalne_fraza_ale_nie_token(tmp_path):
    org = _docx(tmp_path / "o.docx", ("Pozwany Roman Nowak.",))
    wyn = _zip_mod(_docx(tmp_path / "c.docx", ("Pozwany [OSOBA_1].",)), tmp_path / "w.docx", mods={
        "word/settings.xml": lambda d: d.replace(b"<w:zoom", b'<w:docVars><w:docVar w:name="k" w:val="Roman Nowak"/></w:docVars><w:zoom', 1)})
    o = ocen_plik(org, wyn, [W("o#1", "Roman Nowak"), W("o#2", "Roman")])
    assert {(x[0], x[2]) for x in o.wycieki} == {("o#1", "word/settings.xml"), ("o#2", "word/settings.xml")}
    assert ocen_plik(org, _docx(tmp_path / "c2.docx", ("Pozwany [OSOBA_1].",)), [W("o#2", "Roman")]).wycieki == []


def test_i5_eml_naglowki_czesci_preambula_epilog(tmp_path):
    def surowy(wstaw: str) -> bytes:
        m = EmailMessage()
        m["From"] = "x@poczta.test"
        m["Subject"] = "Sprawa"
        m.set_content("Treść.")
        m.add_attachment(b"%", maintype="application", subtype="octet-stream", filename="a.bin")
        return m.as_bytes().replace(b"\n--", ("\n" + wstaw + "\n--").encode(), 1) if wstaw else m.as_bytes()
    org = tmp_path / "o.eml"
    org.write_bytes(surowy(""))
    ws = [W("e#1", "renata@poczta.test", "EMAIL")]
    wew = EmailMessage()
    wew["From"] = "renata@poczta.test"
    wew.set_content("bez danych")
    m = email_msg(surowy(""))
    from email.mime.message import MIMEMessage
    m.attach(MIMEMessage(wew))
    a = tmp_path / "a.eml"
    a.write_bytes(m.as_bytes())
    assert [x[0] for x in ocen_plik(org, a, ws).wycieki] == ["e#1"]
    m = email_msg(surowy(""))
    m.preamble = "Notatka renata@poczta.test"
    p = tmp_path / "p.eml"
    p.write_bytes(m.as_bytes())
    assert [x[0] for x in ocen_plik(org, p, ws).wycieki] == ["e#1"]
    m = email_msg(surowy(""))
    m.epilogue = "Notatka renata@poczta.test"
    e = tmp_path / "e.eml"
    e.write_bytes(m.as_bytes())
    assert [x[0] for x in ocen_plik(org, e, ws).wycieki] == ["e#1"]


def email_msg(surowe: bytes):
    import email
    import email.policy
    return email.message_from_bytes(surowe, policy=email.policy.compat32)


def test_drobne_znaki_formatujace_diakrytyki_i_kody_naglowka(tmp_path):
    org = _docx(tmp_path / "o.docx", ("Pan Michał Dąbrowski.",))
    ws = [W("o#1", "Michał Dąbrowski")]
    for tekst in ("Pan Michał Dą​browski.", "Pan Mi­chał Dąbrowski.", "Pan Michal Dabrowski."):
        assert [x[0] for x in ocen_plik(org, _docx(tmp_path / "w.docx", (tekst,)), ws).wycieki] == ["o#1"], tekst
    def xl(p: Path, naglowek: str) -> Path:
        wb = Workbook()
        wb.active["A1"] = "Lista"
        wb.active.oddHeader.center.text = naglowek
        wb.save(p)
        return p
    o = xl(tmp_path / "o.xlsx", "&KFF0000&\"Arial,Bold\"Kancelaria Nowak")
    assert [x[0] for x in ocen_plik(o, o, [W("k#1", "Kancelaria Nowak", "ORGANIZACJA")]).wycieki] == ["k#1"]


def test_krotnosc_wyciekow_wg_wystapien_w_wyniku(tmp_path):
    org = _docx(tmp_path / "o.docx", ("Anna Wrona.", "Dalej Anna Wrona.", "Inna część."))
    wyn = _docx(tmp_path / "w.docx", ("[OSOBA_1].", "Dalej Anna Wrona.", "Inna część."))
    ws = [W("a#1", "Anna Wrona"), W("a#2", "Anna Wrona")]
    assert [x[0] for x in ocen_plik(org, wyn, ws).wycieki] == ["a#1"]
    assert [x[0] for x in ocen_plik(org, org, ws).wycieki] == ["a#1", "a#2"]


def test_strony_pdf_plus_minus_jedna_bez_kary(tmp_path):
    org = _pdf_tekst(tmp_path / "o.pdf", ("a",))
    c = canvas.Canvas(str(tmp_path / "w.pdf"))
    c.drawString(72, 700, "a")
    c.showPage()
    c.drawString(72, 700, "b")
    c.save()
    o = ocen_plik(org, tmp_path / "w.pdf", [])
    assert o.integralnosc["struktura"] == {"oryginal": {"strony": 1}, "wynik": {"strony": 2}}
    assert o.integralnosc["zachowanie_struktury"] == 1.0


def test_wartosc_wieloczesciowa_ten_sam_id_rozne_teksty(tmp_path):
    # imię i nazwisko w osobnych komórkach to jedna wartość (id) o dwóch częściach: wyciek którejkolwiek = wyciek id
    org = _docx(tmp_path / "o.docx", ("Imię: Zygmunt", "Nazwisko: Przybylski"))
    czesci = [W("p#1", "Zygmunt", "OSOBA"), W("p#1", "Przybylski", "OSOBA")]
    wyn = _docx(tmp_path / "w.docx", ("Imię: [OSOBA_1]", "Nazwisko: Przybylski"))
    o = ocen_plik(org, wyn, czesci)
    assert [x[0] for x in o.wycieki] == ["p#1"] and o.wartosci_ocenione == 1
    assert ocen_plik(org, _docx(tmp_path / "c.docx", ("Imię: [A]", "Nazwisko: [B]")), czesci).wycieki == []


# ----------------------------------------------------------------------------- runda poprawek 2
def test_leksykon_jest_wymagany():
    with pytest.raises(TypeError):
        _ocen_plik(Path("a"), Path("b"), [])


@pytest.mark.skipif(not ocr.dostepny("pl"), reason="brak Tesseracta")
def test_niewykrywalna_wartosc_obrazowa_szukana_dokladnie_w_warstwie_tekstowej(tmp_path, monkeypatch):
    org = _pdf_obraz(tmp_path / "o.pdf", _obraz_z_tekstem("Kontakt"))
    monkeypatch.setattr(obrazy, "wykrywalne_obrazy", lambda *a, **k: set())   # OCR oryginału nie czyta tego e-maila
    w = W("em#1@obraz", "renata@poczta.test", "EMAIL", miejsce="obraz")
    ukryty = _pdf_modyfikuj(org, tmp_path / "u.pdf", lambda pdf: _ukryty_tekst(pdf, "renata@poczta.test"))
    o = ocen_plik(org, ukryty, [w])
    assert o.niewykrywalne == ["em#1@obraz"] and [x[0] for x in o.wycieki] == ["em#1@obraz"]
    assert ocen_plik(org, org, [w]).wycieki == []


def test_naglowek_pdf_na_kazdej_stronie_nie_jest_niejednoznaczny(tmp_path):
    def pdf(p: Path) -> Path:
        c = canvas.Canvas(str(p))
        for i in range(3):
            c.drawString(72, 800, "Kancelaria Zbigniew Orlowski")
            c.drawString(72, 700, f"Treść strony {i}")
            c.showPage()
        c.save()
        return p
    org = pdf(tmp_path / "o.pdf")
    n = W("n#1", "Zbigniew Orlowski", miejsce="naglowek")
    o = ocen_plik(org, org, [n])
    assert o.niejednoznaczne == [] and [x[0] for x in o.wycieki] == ["n#1"]
    # nagłówek 4 razy na 3 stronach = jedno wystąpienie nadmiarowe → niejednoznaczne
    org2 = tmp_path / "o2.pdf"
    c = canvas.Canvas(str(org2))
    for i in range(3):
        c.drawString(72, 800, "Kancelaria Zbigniew Orlowski")
        c.drawString(72, 780, "Zbigniew Orlowski" if i == 0 else "x")
        c.showPage()
    c.save()
    assert ocen_plik(org2, org2, [n]).niejednoznaczne == ["n#1"]


def test_pdf_stary_string_utf16_hex_i_literalny_z_escape(tmp_path):
    base = _pdf_tekst(tmp_path / "b.pdf")
    surowy = base.read_bytes()
    i = surowy.rindex(b"xref\n", 0, surowy.rindex(b"trailer"))
    hexstr = ("feff" + "Marcin Dąbrowski".encode("utf-16-be").hex()).encode()
    obiekt = b"98 0 obj\n<< /Author <" + hexstr + b"> /Title (Ewa Maz\\165r \\(stara\\)) >>\nendobj\n"
    p = tmp_path / "p.pdf"
    p.write_bytes(surowy[:i] + obiekt + surowy[i:])
    o = ocen_plik(base, p, [W("a#1", "Marcin Dąbrowski"), W("b#1", "Ewa Mazur")])
    assert o.status == "OK" and {x[0] for x in o.wycieki} == {"a#1", "b#1"}


@pytest.mark.parametrize("a,b", [("Richards", "Richardson"), ("Peters", "Peterson"), ("Roberts", "Robertson")])
def test_en_bez_reguly_rdzenia_dla_nazwisk_o_wspolnym_prefiksie(tmp_path, a, b):
    org = _docx(tmp_path / "o.docx", (f"Defendant {a} appears.",))
    wyn = _docx(tmp_path / "w.docx", (f"Defendant {b} appears.",))
    assert ocen_plik(org, wyn, [W("o#1", a, jezyk="en")], jezyk="en").wycieki == []


def test_pl_odmiana_tylko_z_listy_koncowek_i_czesciowy(tmp_path):
    org = _docx(tmp_path / "o.docx", ("Powód Jan Kowalski wnosi.",))
    w = [W("o#1", "Jan Kowalski")]
    for forma in ("Kowalskiemu", "Kowalskiego", "Kowalską", "Kowalscy"):
        o = ocen_plik(org, _docx(tmp_path / "w.docx", (f"Przeciw {forma}.",)), w)
        assert [(x[0], x[3]) for x in o.wycieki] == [("o#1", "czesciowy")], forma
    # inne nazwisko o wspólnym początku nie jest odmianą
    assert ocen_plik(org, _docx(tmp_path / "x.docx", ("Przeciw Kowalczykowi.",)), w).wycieki == []
    # de: tylko dopełniacz -s
    org_de = _docx(tmp_path / "d.docx", ("Herr Müller klagt.",))
    wd = [W("m#1", "Müller", jezyk="de")]
    assert ocen_plik(org_de, _docx(tmp_path / "d2.docx", ("Müllers Haus.",)), wd, jezyk="de").wycieki
    assert ocen_plik(org_de, _docx(tmp_path / "d3.docx", ("Müllerberg Haus.",)), wd, jezyk="de").wycieki == []


def test_leksykon_z_manifestu_zapamietany(tmp_path):
    from pbench.sedzia.plik import leksykon_z_manifestu
    m = tmp_path / "manifest.jsonl"
    m.write_text("\n".join(json.dumps({"jezyk": "pl", "gold_obrazy": [], "gold_plik": [{"tekst": "Anna X"}]}) for _ in range(30)))
    a = leksykon_z_manifestu(m)
    assert "anna" in a["pl"] and leksykon_z_manifestu(m) is a


# ----------------------------------------------------------------------------- R38: format wyniku po treści, nie po rozszerzeniu
def test_r38_doc_oryginalu_wynik_docx_jest_ok(tmp_path):
    """Narzędzie zapisało `.doc` jako `.docx` (Privatizer): wynik czytelny, bez NIECZYTELNY, zmiana formatu widoczna."""
    shutil = pytest.importorskip("shutil")
    if not shutil.which("soffice"):
        pytest.skip("brak LibreOffice")
    from pbench.render.doc import konwertuj_do_doc
    _docx(tmp_path / "zrodlo.docx", ("Klient Teresa Pawlak mieszka w Gdańsku.",))
    org = tmp_path / "o.doc"
    konwertuj_do_doc(tmp_path / "zrodlo.docx", org)
    w = W("t#1", "Teresa Pawlak")
    czysty = _docx(tmp_path / "w.docx", ("Klient [OSOBA_1] mieszka w Gdańsku.",))
    o = ocen_plik(org, czysty, [w])
    assert o.status == "OK" and o.wycieki == []
    assert o.integralnosc["format"] == "doc" and o.integralnosc["format_zgodny"] is False
    assert [x[0] for x in ocen_plik(org, tmp_path / "zrodlo.docx", [w]).wycieki] == ["t#1"]    # wyciek nadal widoczny


def test_r38_msg_oryginalu_wynik_txt_jest_ok(tmp_path):
    from pbench.render.cfb import zapisz_cfb
    from pbench.render.msg import PROPS
    korzen = {PROPS: b"\0" * 32, "__substg1.0_0037001F": "Sprawa Pawlak Teresa".encode("utf-16-le"),
              "__substg1.0_0C1A001E": "Adam Wrona".encode("cp1252"), "__substg1.0_1000001F": "Treść".encode("utf-16-le")}
    org = tmp_path / "o.msg"
    zapisz_cfb(org, korzen)
    ws = [W("t#1", "Teresa Pawlak", miejsce="metadane"), W("a#1", "Adam Wrona", miejsce="metadane")]
    czysty = tmp_path / "w.txt"
    czysty.write_text("Temat: Sprawa [OSOBA_1]\nOd: [OSOBA_2]\n\nTreść\n", encoding="utf-8")
    o = ocen_plik(org, czysty, ws)
    assert o.status == "OK" and o.integralnosc["format_zgodny"] is False
    brudny = tmp_path / "b.txt"
    brudny.write_text("Temat: Sprawa Pawlak Teresa\nOd: Adam Wrona\n", encoding="utf-8")
    assert {x[0] for x in ocen_plik(org, brudny, ws).wycieki} == {"a#1"}


def test_r38_wynik_naprawde_nieczytelny_nadal_nieczytelny(tmp_path):
    org = _docx(tmp_path / "o.docx")
    for nazwa, tresc in (("w.docx", os.urandom(300)), ("w.txt", b"\x00\x01\x02binarne\xff" * 40),
                         ("w.doc", b"PK\x03\x04uciety")):
        zly = tmp_path / nazwa
        zly.write_bytes(tresc)
        o = ocen_plik(org, zly, [W("os#1", "Jan Kowalski")])
        assert o.status == "NIECZYTELNY" and o.wycieki == [], nazwa


def test_r38_rozszerzenie_nie_decyduje_o_formacie(tmp_path):
    """Docx zapisany pod rozszerzeniem `.doc` i odwrotnie jest czytany po treści."""
    org = _docx(tmp_path / "o.docx", ("Klient Teresa Pawlak",))
    pod_inna_nazwa = tmp_path / "w.doc"
    pod_inna_nazwa.write_bytes(org.read_bytes())
    o = ocen_plik(org, pod_inna_nazwa, [W("t#1", "Teresa Pawlak")])
    assert o.status == "OK" and [x[0] for x in o.wycieki] == ["t#1"] and o.integralnosc["format_zgodny"] is True


def test_p12_4_zagniezdzony_txt_to_zalacznik_nie_tresc_glowna(tmp_path):
    from pbench.sedzia import ekstrakcja
    m = EmailMessage()
    m["Subject"], m["From"], m["To"] = "Sprawa", "a@x.test", "b@x.test"
    m.set_content("Dzień dobry, w załączniku notatka.")
    m.add_attachment("Klient Teresa Pawlak mieszka w Gdańsku.\n".encode(), maintype="application",
                     subtype="octet-stream", filename="notatka.txt")
    eml = tmp_path / "a.eml"
    eml.write_bytes(m.as_bytes())
    w = ekstrakcja.wydobadz(eml)
    zal = [c for c in w.czesci if c.nazwa.endswith("notatka.txt)/notatka.txt") or c.nazwa.endswith("notatka.txt")]
    zal = [c for c in zal if "nazwy zalacznikow" not in c.nazwa]
    assert zal and not any(c.tresc or c.linie for c in zal)                       # nie jest linią treści głównej…
    assert not any(c.tresc and "Pawlak" in c.caly_tekst() for c in w.czesci)
    ws = [W("t#1", "Teresa Pawlak", miejsce="zalacznik")]
    assert [x[0] for x in ocen_plik(eml, eml, ws).wycieki] == ["t#1"]           # …ale wyciek w nim nadal widać
    # sam plik wynikowy .txt (np. po .msg → .txt) jest treścią główną
    t = tmp_path / "w.txt"
    t.write_text("Klient Teresa Pawlak.\n", "utf-8")
    assert ekstrakcja.wydobadz(t).ma_tresc()


def _docx_z_binarium(sciezka: Path, czesc: str, zawartosc: bytes) -> Path:
    """DOCX z dopisaną binarną częścią `czesc`."""
    _docx(sciezka)
    with zipfile.ZipFile(sciezka, "a") as z:
        z.writestr(czesc, zawartosc)
    return sciezka


def test_printersettings_bin_pomijany_a_oleobject_bin_przeszukiwany(tmp_path):
    org = _docx(tmp_path / "o.docx")
    w = [W("os#1", "Barbara Wieczorek")]
    bin_dane = b"\x00\x01DRUKARKA\x00" + "Barbara Wieczorek".encode("utf-16-le") + b"\x00" + b"Barbara Wieczorek" + b"\x00"
    drukarka = _docx_z_binarium(tmp_path / "d.docx", "word/printerSettings/printerSettings1.bin", bin_dane)
    assert ocen_plik(org, drukarka, w).wycieki == []
    ole = _docx_z_binarium(tmp_path / "e.docx", "word/embeddings/oleObject1.bin", bin_dane)
    assert [x[0] for x in ocen_plik(org, ole, w).wycieki] == ["os#1"]


# ----------------------------------------------------------------------------- J3: poprawki po sanity warstwy trudnej
@pytest.mark.skipif(__import__("shutil").which("soffice") is None, reason="brak LibreOffice")
def test_j3_inicjaly_nie_trafiaja_w_binarne_strumienie_doc(tmp_path):
    """I2 (odchylenie sanity 1): `h-pf-en-pismo_z_parafami-0001` (DOC) – idealny bez wycieków (dwuliterowe „tb” trafiało w bajty
    strumienia `Data` wyniku), oryginał nadal wycieka inicjałami (tekst dokumentu z konwersji LibreOffice)."""
    from pbench import przypadki as P, trudne
    from pbench.sedzia import ekstrakcja
    from pbench.sedzia.sanity import Maskowanie, wartosci_wpisu
    poz = trudne.PozycjaTrudna("h-pf-en-pismo_z_parafami-0001", "en", "pismo_z_parafami", "doc", P.PARAFY)
    wpis = trudne.generuj_dokument_trudny(poz, trudne.ZIARNO_TRUDNE, "test", tmp_path / "o")
    ideal = trudne.generuj_dokument_trudny(poz, trudne.ZIARNO_TRUDNE, "test", tmp_path / "i", maskuj=Maskowanie())
    orig, wyn, ws = tmp_path / "o" / wpis["plik"], tmp_path / "i" / ideal["plik"], wartosci_wpisu(wpis)
    czesci = {c.nazwa: c for c in ekstrakcja.wydobadz(wyn).czesci}
    assert czesci["doc:ole/Data"].binarna and czesci["doc:ole/WordDocument"].binarna
    assert not czesci["doc:ole/SummaryInformation"].binarna and not any(n.startswith("doc->docx:") and c.binarna
                                                                       for n, c in czesci.items())
    assert ocen_plik(orig, wyn, ws).wycieki == []
    a = ocen_plik(orig, orig, ws)
    inicjaly = {w.id for w in ws if w.kategoria == "INICJALY"} - set(a.niejednoznaczne)
    assert inicjaly and inicjaly <= {x[0] for x in a.wycieki}


def test_j3_krotka_wartosc_w_binarnym_widoku_tylko_dluzsze(tmp_path, monkeypatch):
    """Widoki binarne OLE (`Czesc.binarna`): inicjały i wartości ≤ 3 znaków alfanumerycznych nie są w nich szukane, dłuższe – tak;
    ta sama krótka wartość w części niebinarnej wycieka."""
    from pbench.sedzia import ekstrakcja, plik
    org = _docx(tmp_path / "o.docx", akapity=("Parafa: tb. Klient Barbara Wieczorek.",))
    wyn = _docx(tmp_path / "w.docx", akapity=("Parafa: [INICJALY_1]. Klient [OSOBA_1].",))
    oryginalne = ekstrakcja.wydobadz

    def z_binarium(sciezka, *a, **k):
        w = oryginalne(sciezka, *a, **k)
        if Path(sciezka).name == "w.docx":
            w.czesci.append(ekstrakcja.Czesc("doc:ole/Data", dodatkowe=["\x7ftb\x01 Barbara Wieczorek ab1"], binarna=True))
        return w
    monkeypatch.setattr(plik, "wydobadz", z_binarium)
    ws = [W("i#1", "tb", "INICJALY"), W("os#1", "Barbara Wieczorek"), W("k#1", "ab1", "NR_ID")]
    assert [x[0] for x in ocen_plik(org, wyn, ws).wycieki] == ["os#1"]


def test_j3_wartosc_obrazowa_bez_potwierdzenia_w_oryginale_niewykrywalna(tmp_path, monkeypatch):
    """Odchylenie 4: wartość obrazowa, którą `wykrywalne_obrazy` przyjmuje (jeden odczyt), a linia bazowa w oryginale nie odnajduje
    (tu: obraz pokazuje inny tekst), jest `niewykrywalna` – nie oceniana i nie szukana w OCR wyniku; wartość odnajdywana – bez zmian."""
    def z_obrazem(sciezka: Path, tekst: str) -> Path:
        d = Document()
        d.add_paragraph("Pieczątka poniżej.")
        d.add_picture(io.BytesIO(_obraz_z_tekstem(tekst)))
        d.save(sciezka)
        return sciezka
    org = z_obrazem(tmp_path / "o.docx", "Marcin Wisniewski")
    ws = [W("os#1@obraz", "Marcin Wisniewski", miejsce="obraz"), W("fi#1@obraz", "Ingenieurbuero Krause", "ORGANIZACJA",
                                                                    miejsce="obraz")]
    monkeypatch.setattr(obrazy, "wykrywalne_obrazy", lambda *a, **k: {"os#1@obraz", "fi#1@obraz"})
    o = ocen_plik(org, org, ws)
    assert o.niewykrywalne == ["fi#1@obraz"] and [x[0] for x in o.wycieki] == ["os#1@obraz"]
    assert o.bazowe == ["os#1@obraz"] and o.wartosci_ocenione == 1
    wyn = z_obrazem(tmp_path / "w.docx", "Ingenieurbuero Krause")      # wynik z nazwą w pikselach: nie oceniana (poza mianownikiem)
    assert ocen_plik(org, wyn, ws).wycieki == []


@pytest.mark.parametrize("zapis", ["28-333", "28333", "28 333"])
def test_j3_kod_pocztowy_jak_identyfikator(tmp_path, zapis):
    """Odchylenie 3: kod pocztowy wycieka, gdy jego ciąg cyfr występuje z granicami (z separatorem albo bez) – w każdym
    języku tak samo (polski „28-333” dotąd nie mógł wyciec, pięciocyfrowy niemiecki – tak)."""
    org = _docx(tmp_path / "o.docx", akapity=("Adres: ul. Polna 4, 28-333 Pińczów. Anschrift: 10115 Berlin.",))
    ws = [W("k#1", "28-333", "KOD_POCZTOWY"), W("k#2", "10115", "KOD_POCZTOWY", jezyk="de")]
    assert sorted(x[0] for x in ocen_plik(org, org, ws).wycieki) == ["k#1", "k#2"]
    wyn = _docx(tmp_path / "w.docx", akapity=(f"Adres: ul. Polna 4, {zapis} Pińczów. Anschrift: [KOD] Berlin.",))
    assert [x[0] for x in ocen_plik(org, wyn, ws).wycieki] == ["k#1"]
    for inny in ("128-3330", "28-33", "2833"):
        wyn = _docx(tmp_path / "x.docx", akapity=(f"Adres: ul. Polna 4, {inny} Pińczów. Anschrift: [KOD] Berlin.",))
        assert ocen_plik(org, wyn, ws).wycieki == [], inny



def test_widok_8bitowy_utf16_bez_przeplotu(tmp_path):
    """Widoki 8-bitowe (UTF-8, cp1250) bajtów UTF-16 nie są tekstem rozstrzelonym: NUL-e przeplotu znikają przed dekodowaniem,
    więc granica wzorca identyfikatora nie wypada w środku liczby (koniec daty „24.08.2019” nie jest częścią „82019”
    sygnatury „XI U 820/19”). Wartość zapisana w UTF-16 wycieka dalej – z widoku UTF-16 i z widoku 8-bitowego."""
    from pbench.sedzia import ekstrakcja
    data = "W dniu 24.08.2019 19:39 napisał:".encode("utf-16-le")
    widoki = ekstrakcja._surowe_widoki(data)
    assert all("2 4 . 0 8" not in v for v in widoki) and "24.08.2019" in widoki[0] and "24.08.2019" in widoki[1]
    assert ekstrakcja._bez_przeplotu_utf16(b"Adam\x00Wrona\x00") == b"Adam\x00Wrona\x00"   # pojedynczy NUL zostaje granicą
    sygn = "Sygnatura XI U 820/19".encode("utf-16-le")
    widoki = ekstrakcja._surowe_widoki(sygn)
    assert all("XI U 820/19" in v for v in widoki[:3])                  # utf-8, cp1250 (zwarte) i utf-16-le
    org = _docx(tmp_path / "o.docx", ("Sygnatura akt XI U 820/19.",))
    ws = [W("s#1", "XI U 820/19", "SYGNATURA")]
    czysty = _docx_z_binarium(tmp_path / "c.docx", "word/embeddings/oleObject1.bin", b"\x01\x00\x00\x00" + data)
    assert ocen_plik(org, czysty, ws).wycieki == []
    for nazwa, bajty in (("le.docx", b"\x01\x00\x00\x00" + sygn), ("le1.docx", b"\x01\x00\x00" + sygn)):
        brudny = _docx_z_binarium(tmp_path / nazwa, "word/embeddings/oleObject1.bin", bajty)
        assert [(x[0], x[3]) for x in ocen_plik(org, brudny, ws).wycieki] == [("s#1", "pelny")], nazwa


@pytest.mark.parametrize("bajty, wartosc, kat", [
    (b"\x01\x00Kowalski\x00" + "Tytul".encode("utf-16-le"), "Kowalski", "OSOBA"),
    (b"5213456789\x00" + "Tytul".encode("utf-16-le"), "5213456789", "NIP"),
    (b"XI U 820/19\x00" + "Tytul".encode("utf-16-le"), "XI U 820/19", "SYGNATURA"),
    (b"A\x00B\x00C\x00Kowalski", "Kowalski", "OSOBA"),
], ids=["przed_utf16", "nip_przed_utf16", "sygnatura_przed_utf16", "po_utf16"])
def test_widok_8bitowy_napis_8bitowy_obok_utf16(tmp_path, bajty, wartosc, kat):
    """Granice przeplotu UTF-16 zostają granicami (`ekstrakcja._bez_przeplotu_utf16`): napis 8-bitowy zakończony NUL-em tuż przed
    napisem UTF-16 albo tuż po nim nie skleja się z nim w widoku 8-bitowym – wartość 8-bitowa wycieka w całości."""
    from pbench.sedzia import ekstrakcja
    assert all(re.search(rf"(?<![^\W_]){re.escape(wartosc)}(?![^\W_])", v) for v in ekstrakcja._surowe_widoki(bajty)[:2])
    org = _docx(tmp_path / "o.docx", (f"Dane: {wartosc}.",))
    ws = [W("v#1", wartosc, kat)]
    wyn = _docx_z_binarium(tmp_path / "w.docx", "word/embeddings/oleObject1.bin", bajty)
    assert [(x[0], x[3]) for x in ocen_plik(org, wyn, ws).wycieki] == [("v#1", "pelny")]
