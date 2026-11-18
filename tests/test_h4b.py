"""Warstwa trudnych przypadków, zadanie H4b (spec §11 pkt 1 – poczta, pkt 6 – wątki cytowane, RTF i ODT): `ukryta_poczta`,
`cytowane_watki_vcard`, `formaty_rtf_odt`. Rejestr, plan, manifest, determinizm, obecność każdej wartości w pliku (niezależne
czytniki: `email`, `olefile`, pypdfium2, zipfile + lxml, prosty dekoder RTF – bez kodu sędziego), rozszerzenia sędziego (RTF, ODT,
vCard, rozpoznanie formatu po treści, OCR stron PDF w załączniku poczty) i sanity: oryginał wycieka, idealny uczestnik nie,
„naiwny” uczestnik (czyści tylko treść główną) zostawia wyciek w załącznikach, cytatach i wizytówce."""
from __future__ import annotations

import dataclasses
import email
import io
import json
import re
import shutil
import struct
import zipfile
from email import policy
from pathlib import Path

import olefile
import pikepdf
import pypdfium2 as pdfium
import pytest
from lxml import etree

from pbench import korpus, pliki_pdf, pliki_poczta, przypadki as P, trudne, trudne_poczta as TP, trudne_ukryta as U
from pbench.model import Wartosc
from pbench.render import odt as R_odt, rtf as R_rtf
from pbench.render.cfb import zapisz_cfb
from pbench.sedzia import ekstrakcja, obrazy, plik as sedzia_plik, rtf as S_rtf
from pbench.sedzia.normalizacja import normalizuj, same_alnum
from pbench.sedzia.plik import ocen_plik
from pbench.sedzia.sanity import Maskowanie, wartosci_wpisu

N_DOKUMENTOW = 4
POCZTA = (P.UKRYTA_POCZTA, P.CYTOWANE_WATKI_VCARD)
ODF = {"text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0", "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
       "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0", "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
       "dc": "http://purl.org/dc/elements/1.1/", "meta": "urn:oasis:names:tc:opendocument:xmlns:meta:1.0"}
LO = pytest.mark.skipif(shutil.which("soffice") is None, reason="brak LibreOffice")


# ============================================================================= rejestr, plan
def test_rejestr_h4b():
    assert P.H4B == (P.UKRYTA_POCZTA, P.CYTOWANE_WATKI_VCARD, P.FORMATY_RTF_ODT) and set(P.H4B) <= set(P.PRZYPADKI)
    assert {P.SKROTY[p] for p in P.H4B} == {"um", "cv", "ro"} and len(set(P.SKROTY.values())) == len(P.SKROTY)
    assert P.FORMATY_PRZYPADKU[P.UKRYTA_POCZTA] == P.FORMATY_PRZYPADKU[P.CYTOWANE_WATKI_VCARD] == ("eml", "msg")
    assert P.FORMATY_PRZYPADKU[P.FORMATY_RTF_ODT] == ("rtf", "odt")
    assert not set(P.H4B) & (set(P.H1) | set(P.H2) | set(P.H3) | set(P.H4A))
    for przypadek in P.H4B:
        assert przypadek in trudne.GENERATORY_H4B and trudne._pary(przypadek)
    assert {t for _, t in trudne._pary(P.UKRYTA_POCZTA)} == {"email"} and len(trudne._pary(P.UKRYTA_POCZTA)) == 5


def test_mapowanie_miejsc_h4b_istniejace_miejsca_i_wagi():
    wagi = json.loads(Path("metodyka/wagi_punktow.json").read_text(encoding="utf-8"))["wagi_miejsc"]
    nowe = {k: v for k, v in U.MIEJSCA.items() if k.startswith("poczta.")}
    assert nowe == {"poczta.wiadomosc": "zalacznik", "poczta.zalacznik_pdf": "zalacznik", "poczta.vcard": "zalacznik",
                    "poczta.cytat": "tresc"}
    assert set(nowe.values()) <= set(wagi)                      # tylko istniejące miejsca; wagi zamrożone
    md = Path("metodyka/miejsca-ukryte.md").read_text(encoding="utf-8")
    assert all(f"| `{k}` | `{v}` |" in md for k, v in nowe.items())


@pytest.mark.parametrize("przypadek", P.H4B)
def test_plan_h4b(przypadek):
    plan = trudne.zaplanuj_przypadek(przypadek, 30)
    assert len(plan) == 30 and plan == trudne.zaplanuj_przypadek(przypadek, 30) and plan == sorted(plan, key=lambda p: p.id)
    assert {p.format for p in plan} == set(P.FORMATY_PRZYPADKU[przypadek])
    for p in plan:
        assert re.fullmatch(rf"h-{P.SKROTY[przypadek]}-{p.jezyk}-{p.typ}-\d{{4}}", p.id)
        assert p.format in trudne.formaty_dla(p.jezyk, p.typ) and p.format in korpus.ROZSZERZENIA
    assert len({p.jezyk for p in plan}) == 5


@pytest.mark.parametrize("przypadek", [p for p in (*P.H1, *P.H2, *P.H3, *P.H4A)])
def test_rtf_odt_tylko_w_swoim_przypadku(przypadek):
    """Formaty spoza trzonu nie trafiają do planów innych przypadków (plany H1–H4a bez zmian)."""
    assert not {p.format for p in trudne.zaplanuj_przypadek(przypadek, 40)} & {"rtf", "odt"}


def test_wymuszone_utrudnienia_tylko_rtf_odt():
    assert set(korpus.WYMUSZONE_UTRUDNIENIA) == {"rtf", "odt"}
    for fmt in ("docx", "pdf", "eml", "msg", "doc"):
        poz = korpus.Pozycja(f"x-{fmt}", "pl", "umowa", fmt)
        assert korpus.losuj_utrudnienia(poz, 1, True) <= korpus._UTRUDNIENIA_FORMATU[fmt]
    poz = korpus.Pozycja("x-odt", "pl", "umowa", "odt")
    assert {"papier_firmowy", "tabele", "komentarze", "metadane"} <= korpus.losuj_utrudnienia(poz, 1, True)


# ============================================================================= generacja
@pytest.fixture(scope="module")
def warstwa(tmp_path_factory) -> dict[str, tuple[Path, list[dict]]]:
    wynik = {}
    for przypadek in P.H4B:
        cel = tmp_path_factory.mktemp(przypadek)
        wynik[przypadek] = (cel, trudne.zbuduj_przypadek(cel, przypadek, N_DOKUMENTOW, procesy=1))
    return wynik


def _dok(warstwa, przypadek: str, i: int) -> tuple[Path, dict, Path]:
    cel, wpisy = warstwa[przypadek]
    return cel, wpisy[i], cel / wpisy[i]["plik"]


def test_manifest_h4b(warstwa):
    for przypadek, (cel, wpisy) in warstwa.items():
        assert [json.loads(l) for l in (cel / "manifest.jsonl").read_text(encoding="utf-8").splitlines()] == wpisy
        assert {w["format"] for w in wpisy} == set(P.FORMATY_PRZYPADKU[przypadek])   # oba formaty w próbce
        for w in wpisy:
            assert w["warstwa"] == "trudne" and w["przypadki"] == [przypadek] and w["posrednie"] == []
            assert w["id"].startswith(f"h-{P.SKROTY[przypadek]}-") and (cel / w["plik"]).is_file()
            if przypadek in POCZTA:
                assert w["ostrzezenia"] == [] and w["typ"] == "email"
            else:
                assert {"papier_firmowy", "tabele", "komentarze", "metadane"} <= set(w["utrudnienia"])
                assert all("konwersja" in o for o in w["ostrzezenia"])
    assert all(w["ukryte"] == ["poczta.wiadomosc", "poczta.zalacznik_pdf"] for w in warstwa[P.UKRYTA_POCZTA][1])
    assert all(w["ukryte"] == ["poczta.vcard"] for w in warstwa[P.CYTOWANE_WATKI_VCARD][1])
    assert all("ukryte" not in w for w in warstwa[P.FORMATY_RTF_ODT][1])


def test_determinizm_h4b(tmp_path, warstwa):
    """Dwie budowy dają te same bajty (RTF/ODT: po normalizacji tablic, identyfikatorów i czasów ZIP – `normalizuj_*`)."""
    for przypadek in P.H4B:
        cel, wpisy = warstwa[przypadek]
        drugi = tmp_path / przypadek
        w2 = trudne.zbuduj_przypadek(drugi, przypadek, len(wpisy), procesy=1)
        assert [w["sha256"] for w in w2] == [w["sha256"] for w in wpisy], przypadek
        assert (drugi / "manifest.jsonl").read_bytes() == (cel / "manifest.jsonl").read_bytes()
        shutil.rmtree(drugi)


# ============================================================================= czytniki niezależne od sędziego
def _gold(w: dict, rodzaj: str | None = None, cecha: str | None = None) -> list[Wartosc]:
    ws = [Wartosc.from_dict(x) for x in w["gold_plik"]]
    if rodzaj is not None:
        ws = [x for x in ws if x.id.startswith(f"h.{rodzaj}.")]
    if cecha is not None:
        ws = [x for x in ws if cecha in x.cechy]
    return ws


def _tekst_pdf(dane: bytes) -> str:
    d = pdfium.PdfDocument(dane)
    try:
        return "\n".join(d[i].get_textpage().get_text_range() for i in range(len(d)))
    finally:
        d.close()


def _bez_bialych(t: str) -> str:
    return re.sub(r"\s+", " ", t)


def _w_tekscie(wartosc: str, tekst: str) -> bool:
    return _bez_bialych(wartosc) in _bez_bialych(tekst)


def _eml(plik: Path) -> email.message.EmailMessage:
    return email.message_from_bytes(plik.read_bytes(), policy=policy.default)


def _wlasciwosci(dane: bytes, naglowek: int) -> dict[int, int]:
    """Tablica właściwości MAPI: tag -> wartość/rozmiar (4 bajty)."""
    return {struct.unpack_from("<I", dane, i)[0]: struct.unpack_from("<I", dane, i + 8)[0]
            for i in range(naglowek, len(dane) - 15, 16)}


def _msg_tekst(ole: olefile.OleFileIO, *sciezka: str) -> str:
    return ole.openstream("/".join(sciezka)).read().decode("utf-16-le")


def test_ukryta_poczta_msg_wiadomosc_osadzona_olefile(warstwa):
    """MSG: załącznik-wiadomość jest obiektem osadzonym (metoda 5, storage `__substg1.0_3701000D`) z własnymi nagłówkami,
    treścią i załącznikiem PDF; obok – karta klienta PDF. Każda wartość gold leży we właściwym strumieniu."""
    cel, wpisy = warstwa[P.UKRYTA_POCZTA]
    msg = [w for w in wpisy if w["format"] == "msg"]
    assert msg
    for w in msg:
        ole = olefile.OleFileIO(str(cel / w["plik"]))
        try:
            n_zal = struct.unpack_from("<I", ole.openstream("__properties_version1.0").read(), 20)[0]
            zal = [f"__attach_version1.0_#{i:08X}" for i in range(n_zal)]
            assert all(ole.exists(z) for z in zal) and not ole.exists(f"__attach_version1.0_#{n_zal:08X}")
            osadzone = [z for z in zal if ole.exists(f"{z}/__substg1.0_3701000D")]
            assert len(osadzone) == 1
            z = osadzone[0]
            assert _wlasciwosci(ole.openstream(f"{z}/__properties_version1.0").read(), 8)[0x37050003] == 5
            wn = f"{z}/__substg1.0_3701000D"
            assert ole.get_type(wn) == olefile.STGTY_STORAGE
            n = struct.unpack_from("<IIII", ole.openstream(f"{wn}/__properties_version1.0").read(), 8)
            assert n == (1, 1, 1, 1)                                   # nagłówek wiadomości osadzonej: 24 B
            naglowki = "\n".join(_msg_tekst(ole, wn, f"__substg1.0_{t}001F") for t in ("0C1A", "0C1F", "0E04", "0037"))
            naglowki += _msg_tekst(ole, wn, "__recip_version1.0_#00000000", "__substg1.0_3003001F")
            tresc = _msg_tekst(ole, wn, "__substg1.0_1000001F")
            for v in _gold(w):
                if v.id.split(".")[1] in ("nadawca", "adresat"):
                    assert v.tekst in naglowki or _w_tekscie(v.tekst, tresc), v
            pdf_zagn = ole.openstream(f"{wn}/__attach_version1.0_#00000000/__substg1.0_37010102").read()
            assert pdf_zagn[:5] == b"%PDF-"
            tekst_zagn = _tekst_pdf(pdf_zagn)
            pdfy_glowne = [ole.openstream(f"{x}/__substg1.0_37010102").read() for x in zal
                           if ole.exists(f"{x}/__substg1.0_37010102")]
            tekst_glowny = "\n".join(_tekst_pdf(b) for b in pdfy_glowne if b[:5] == b"%PDF-")
            for v in _gold(w, "klient"):
                assert _w_tekscie(v.tekst, tresc) or _w_tekscie(v.tekst, tekst_zagn), v
            for v in _gold(w, "karta"):
                assert _w_tekscie(v.tekst, tekst_glowny), v
        finally:
            ole.close()


def test_ukryta_poczta_eml_rfc822_i_pdf(warstwa):
    cel, wpisy = warstwa[P.UKRYTA_POCZTA]
    eml = [w for w in wpisy if w["format"] == "eml"]
    assert eml
    for w in eml:
        m = _eml(cel / w["plik"])
        zagn = [p for p in m.walk() if p.get_content_type() == "message/rfc822"]
        assert len(zagn) == 1
        wn = zagn[0].get_payload()[0]
        assert wn["From"] and wn["To"] and wn["Subject"] and wn["Message-ID"]
        tresc = wn.get_body(("plain",)).get_content()
        pdf_zagn = [p.get_payload(decode=True) for p in wn.walk() if p.get_content_type() == "application/pdf"]
        pdf_glowne = [p.get_payload(decode=True) for p in m.iter_attachments() if p.get_content_type() == "application/pdf"]
        assert len(pdf_zagn) == 1 and len(pdf_glowne) == 1
        assert {p.get_filename() for p in m.iter_attachments()} >= {TP.TEKSTY[w["jezyk"]]["plik_karty"]}
        naglowki = f"{wn['From']}\n{wn['To']}"
        for v in _gold(w, "nadawca") + _gold(w, "adresat"):
            assert v.tekst in naglowki or _w_tekscie(v.tekst, tresc), v
        for v in _gold(w, "klient"):
            assert _w_tekscie(v.tekst, tresc) or _w_tekscie(v.tekst, _tekst_pdf(pdf_zagn[0])), v
        for v in _gold(w, "karta"):
            assert _w_tekscie(v.tekst, _tekst_pdf(pdf_glowne[0])), v


def _tresc_poczty(plik: Path) -> tuple[str, list[tuple[str, bytes]]]:
    """(treść tekstowa, załączniki (nazwa, bajty)) wiadomości EML albo MSG – czytnikiem niezależnym od sędziego."""
    if plik.suffix == ".eml":
        m = _eml(plik)
        return (m.get_body(("plain",)).get_content().replace("\r\n", "\n"),
                [(p.get_filename(), p.get_payload(decode=True)) for p in m.iter_attachments()])
    ole = olefile.OleFileIO(str(plik))
    try:
        zal = [(_msg_tekst(ole, s[0], "__substg1.0_3707001F"), ole.openstream([s[0], "__substg1.0_37010102"]).read())
               for s in ole.listdir() if len(s) == 2 and s[1] == "__substg1.0_37010102"]
        return _msg_tekst(ole, "__substg1.0_1000001F").replace("\r\n", "\n"), zal
    finally:
        ole.close()


def test_cytowane_watki_i_vcard(warstwa):
    cel, wpisy = warstwa[P.CYTOWANE_WATKI_VCARD]
    style = set()
    for w in wpisy:
        tresc, zal = _tresc_poczty(cel / w["plik"])
        outlook = tresc.count(TP.KRESKA_OUTLOOKA)
        wiadomosci = len(re.findall(r"^(?:>+ )?--$", tresc, re.M))     # każda cytowana wiadomość ma stopkę po „--”
        assert 3 <= wiadomosci <= 5 and outlook >= 1, (outlook, wiadomosci)
        style.add("outlook")
        if re.search(r"^>+ ", tresc, re.M):
            style.add("gmail")
        assert re.search(r"^>> ", tresc, re.M) or re.search(r"^> ", tresc, re.M)
        cytat = _gold(w, cecha=TP.CECHA_CYTAT)
        assert len(cytat) >= 12 and all(v.miejsce == "tresc" for v in cytat)
        # cytaty leżą pod podpisem (za separatorem stopki) i są w tekście poziomu 1
        reszta = tresc.split("\n-- \n", 1)[1]
        txt = (cel / w["plik_txt"]).read_text(encoding="utf-8")
        for v in cytat:
            assert v.tekst in reszta and v.tekst in txt, v
        assert {s["wartosc_id"] for s in w["gold_tekst"]} >= {v.id for v in cytat}
        # vCard: niezależny odczyt wierszy
        vcf = [b for n, b in zal if n and n.endswith(".vcf")]
        assert len(vcf) == 1
        wiersze = vcf[0].decode("utf-8").split("\r\n")
        assert wiersze[0] == "BEGIN:VCARD" and wiersze[1] in ("VERSION:3.0", "VERSION:4.0") and wiersze[-2] == "END:VCARD"
        wlasciwosci = {l.split(":", 1)[0].split(";", 1)[0] for l in wiersze if ":" in l}
        assert {"FN", "N", "TEL", "EMAIL", "ADR", "ORG"} <= wlasciwosci
        vcard = _gold(w, "vcard")
        assert {v.kategoria for v in vcard} >= {"OSOBA", "TELEFON", "EMAIL", "ADRES", "ORGANIZACJA"}
        assert all(v.miejsce == "zalacznik" and v.tekst in vcf[0].decode("utf-8") for v in vcard)
    assert style == {"outlook", "gmail"}


def _rtf_na_tekst(rtf: bytes) -> str:
    """Prosty dekoder RTF (test – niezależny od parsera sędziego): `\\uN` i `\\'xx` (cp1252) jako znaki, słowa kontrolne usunięte."""
    t = rtf.decode("latin-1")
    t = re.sub(r"\\u(-?\d+) ?(\\'[0-9a-fA-F]{2}|\?)?", lambda m: chr(int(m.group(1)) % 65536), t)
    t = re.sub(r"\\'([0-9a-fA-F]{2})", lambda m: bytes([int(m.group(1), 16)]).decode("cp1252", "replace"), t)
    t = re.sub(r"\\(?:par|line|cell|row|tab)\b ?", " ", t)
    t = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", t)
    return re.sub(r"[{}\r\n]", "", t)


def test_rtf_odt_niezalezny_czytnik(warstwa):
    """ODT: każda wartość w swojej części (lxml: `content.xml` – treść, tabela, komentarz `office:annotation`; `styles.xml` –
    nagłówek/stopka; `meta.xml` – metadane). RTF: każda wartość w tekście zdekodowanym prostym dekoderem."""
    cel, wpisy = warstwa[P.FORMATY_RTF_ODT]
    czesci = {"tresc": "content.xml", "tabela": "content.xml", "komentarz": "content.xml", "przypis": "content.xml",
              "zmiany": "content.xml", "pole": "content.xml", "naglowek": "styles.xml", "stopka": "styles.xml",
              "metadane": "meta.xml"}
    for w in wpisy:
        plik = cel / w["plik"]
        ws = [x for x in _gold(w) if x.miejsce != "obraz"]
        if w["format"] == "odt":
            with zipfile.ZipFile(plik) as z:
                assert z.infolist()[0].filename == "mimetype" and z.infolist()[0].compress_type == zipfile.ZIP_STORED
                assert z.read("mimetype") == b"application/vnd.oasis.opendocument.text"
                xml = {n: etree.fromstring(z.read(n)) for n in ("content.xml", "styles.xml", "meta.xml")}
            teksty = {n: _bez_bialych(" ".join(r.itertext())) for n, r in xml.items()}
            assert xml["content.xml"].find(".//office:annotation", ODF) is not None
            assert xml["content.xml"].find(".//table:table", ODF) is not None
            assert xml["styles.xml"].find(".//style:header", ODF) is not None
            assert xml["styles.xml"].find(".//style:footer", ODF) is not None
            assert xml["meta.xml"].find(".//meta:initial-creator", ODF) is not None
            for v in ws:
                assert _w_tekscie(v.tekst, teksty[czesci[v.miejsce]]), v
        else:
            tekst = _rtf_na_tekst(plik.read_bytes())
            assert b"\\annotation" in plik.read_bytes() and b"\\header" in plik.read_bytes() and b"\\trowd" in plik.read_bytes()
            for v in ws:
                assert _w_tekscie(v.tekst, tekst), v
        assert {x.miejsce for x in ws} >= {"tresc", "tabela", "komentarz", "naglowek", "stopka", "metadane"}


@LO
def test_rtf_odt_libreoffice_otwiera(warstwa, tmp_path):
    """Pliki RTF/ODT otwiera LibreOffice (konwersja do PDF daje strony)."""
    from pbench.render.doc import konwertuj
    cel, wpisy = warstwa[P.FORMATY_RTF_ODT]
    for w in wpisy[:2]:
        wy = tmp_path / f"{w['id']}.pdf"
        konwertuj(cel / w["plik"], wy, "pdf")
        assert len(pdfium.PdfDocument(str(wy))) >= 1


def test_normalizuj_rtf_porzadek_tablic():
    a = (b"{\\rtf1\\ansi\\deff1{\\fonttbl{\\f0\\fswiss\\fcharset0 Arial;}{\\f1\\froman\\fcharset238 Times;}}"
         b"{\\colortbl;\\red255\\green0\\blue0;\\red0\\green0\\blue255;}{\\f1\\cf1 A}{\\f0\\cf2\\af0 B}\\fs20\\fi-360 C}")
    b = (b"{\\rtf1\\ansi\\deff0{\\fonttbl{\\f0\\froman\\fcharset238 Times;}{\\f1\\fswiss\\fcharset0 Arial;}}"
         b"{\\colortbl;\\red0\\green0\\blue255;\\red255\\green0\\blue0;}{\\f0\\cf2 A}{\\f1\\cf1\\af1 B}\\fs20\\fi-360 C}")
    assert R_rtf.normalizuj_rtf(a) == R_rtf.normalizuj_rtf(b)
    n = R_rtf.normalizuj_rtf(a)
    assert b"\\fs20\\fi-360" in n and b"\\deff" in n
    o = S_rtf.czytaj(n)
    assert "".join(o.teksty["tresc"]).strip() == "ABC"           # spacja po słowie kontrolnym to ogranicznik


def test_normalizuj_odt_identyfikatory_i_czas(tmp_path):
    def odt(ct: str, nazwa: str, rsid: str) -> bytes:
        bufor = io.BytesIO()
        with zipfile.ZipFile(bufor, "w") as z:
            z.writestr(zipfile.ZipInfo("mimetype", (2025, 5, 5, 1, 2, 3)), b"application/vnd.oasis.opendocument.text")
            zi = zipfile.ZipInfo("content.xml", (2025, 5, 5, 1, 2, 3))
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, f'<a xml:id="{ct}" text:id="{ct}"><b office:name="__Annotation__4_{nazwa}"/>'
                           f'<c office:name="__Annotation__4_{nazwa}"/><d text:change-id="{ct}"/></a>'.encode())
            z.writestr(zipfile.ZipInfo("settings.xml", (2025, 5, 5, 1, 2, 3)),
                       f'<s config:name="RsidRoot" config:type="int">{rsid}</s>'.encode())
        return bufor.getvalue()
    a, b = R_odt.normalizuj_odt(odt("ct1234", "998877", "5555")), R_odt.normalizuj_odt(odt("ct99", "1", "7"))
    assert a == b
    with zipfile.ZipFile(io.BytesIO(a)) as z:
        assert [i.compress_type for i in z.infolist()][:2] == [zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED]
        assert b'xml:id="ct1"' in z.read("content.xml") and b"__Annotation__4_1" in z.read("content.xml")


# ============================================================================= sędzia: RTF, ODT, vCard, format po treści
_RTF_TEST = (b"{\\rtf1\\ansi\\ansicpg1250\\deff0{\\fonttbl{\\f0\\froman\\fcharset238 Times;}{\\f1\\fswiss\\fcharset0 Arial;}}"
             b"{\\info{\\title Sprawa Pawlak}{\\author Teresa Pawlak}{\\*\\company Kancelaria Wrona}}"
             b"{\\*\\userprops{\\propname Klient}\\proptype30{\\staticval Adam Wrona}}"
             b"{\\header \\pard Nag\\'b3\\'f3wek: Zofia Je\\u380\\'bfyk\\par}"
             b"{\\footer \\pard tel. 600 100 200\\par}"
             b"\\pard\\f0 Klient Bo\\u380?ena Kowal{\\v ska ukryta}\\par"
             b"\\pard Komentarz{\\*\\atnid TP}{\\*\\atnauthor Tomasz Pietrzak}\\chatn{\\*\\annotation \\pard Uwaga: Marek Sowa\\par}\\par"
             b"{\\*\\mojagrupa Ewelina Kruk}"
             b"\\trowd\\cellx1000\\cellx2000 Jan\\cell Lis\\cell\\row"
             b"}")


def test_sedzia_rtf_czesci_i_dekodowanie():
    o = S_rtf.czytaj(_RTF_TEST)
    t = {k: "".join(v) for k, v in o.teksty.items()}
    assert "Nagłówek: Zofia Jeżyk" in t["naglowek"] and "600 100 200" in t["stopka"]
    assert "Bożena Kowalska ukryta" in t["tresc"] and "Jan\nLis\n" in t["tresc"]
    assert "Teresa Pawlak" in t["metadane"] and "Adam Wrona" in t["metadane"] and "Kancelaria Wrona" in t["metadane"]
    assert "Tomasz Pietrzak" in t["komentarz"] and "Marek Sowa" in t["komentarz"] and "Ewelina Kruk" in t["*mojagrupa"]
    assert "Times" in "".join(o.strukturalne["fonttbl"]) and o.struktura == {"akapity": 2, "wiersze_tabel": 1}
    # metadane nie sklejone z sąsiednim polem
    assert "Sprawa Pawlak\nTeresa Pawlak" in t["metadane"]


def test_sedzia_rtf_wyciek_w_kazdej_grupie(tmp_path):
    org = tmp_path / "o.rtf"
    org.write_bytes(_RTF_TEST)
    ws = [Wartosc(f"x.{i}#1", k, t, "pl", m, f"x.{i}") for i, (k, t, m) in enumerate((
        ("OSOBA", "Zofia Jeżyk", "naglowek"), ("OSOBA", "Teresa Pawlak", "metadane"), ("OSOBA", "Adam Wrona", "metadane"),
        ("OSOBA", "Tomasz Pietrzak", "komentarz"), ("OSOBA", "Marek Sowa", "komentarz"), ("OSOBA", "Ewelina Kruk", "metadane"),
        ("TELEFON", "600 100 200", "stopka")))]
    a = ocen_plik(org, org, ws, leksykon={})
    assert a.status == "OK" and a.integralnosc["format"] == "rtf" and {x[0] for x in a.wycieki} == {w.id for w in ws}
    czysty = tmp_path / "w.rtf"
    czysty.write_bytes(re.sub(rb"(Zofia|Teresa|Adam|Tomasz|Marek|Ewelina|600 100 200|Pawlak|Wrona|Pietrzak|Sowa|Kruk|Je\\u380\\'bfyk)",
                              b"X", _RTF_TEST))
    b = ocen_plik(org, czysty, ws, leksykon={})
    assert b.status == "OK" and b.wycieki == [] and b.integralnosc["format_zgodny"]


def test_sedzia_rtf_obraz_pict_do_ocr():
    from PIL import Image
    bufor = io.BytesIO()
    Image.new("RGB", (40, 30), "white").save(bufor, format="PNG")
    png = bufor.getvalue()
    rtf = (b"{\\rtf1\\ansi{\\*\\shppict{\\pict{\\*\\picprop{\\sp{\\sn wzPictureDescription}{\\sv Opis Kazimierz Wilk}}}"
           b"\\pngblip " + png.hex().encode() + b"}}\\par Tekst\\par}")
    w = ekstrakcja.Wydobycie()
    ekstrakcja._rtf(rtf, "", w, True, 0)
    assert [b for _, b in w.obrazy] == [png]
    assert any("Kazimierz Wilk" in c.caly_tekst() for c in w.czesci)


def test_sedzia_odt_komentarz_i_spacje_nie_sklejaja_akapitu():
    xml = ('<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
           'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" xmlns:dc="http://purl.org/dc/elements/1.1/">'
           '<office:body><office:text><text:p>Klient Jan<text:s/>Nowak<office:annotation><dc:creator>Ewa Lis</dc:creator>'
           '<text:p>Sprawdzić</text:p></office:annotation> mieszka<text:line-break/>w Gdyni<text:tab/>tel.<text:s text:c="2"/>600'
           '<text:note><text:note-citation>1</text:note-citation><text:note-body><text:p>Przypis Olga Kos</text:p></text:note-body>'
           '</text:note></text:p><text:h>Rozdział Piotr Mak</text:h></office:text></office:body></office:document-content>')
    c = ekstrakcja.czesc_xml("content.xml", xml.encode(), odf=True)
    assert c.tresc and "Klient Jan Nowak mieszka\nw Gdyni\ttel.  600" in c.linie
    assert {"Ewa Lis", "Sprawdzić", "Przypis Olga Kos", "Rozdział Piotr Mak"} <= set(c.linie)


def test_sedzia_r42_format_po_tresci_rtf_odt_vcard(warstwa, tmp_path):
    """R42: format wyniku rozpoznawany po treści – RTF i ODT (także pod obcym rozszerzeniem) są czytelne; zmiana formatu widoczna."""
    cel, wpisy = warstwa[P.FORMATY_RTF_ODT]
    for w in wpisy:
        plik = cel / w["plik"]
        wyd = ekstrakcja.wydobadz(plik)
        assert wyd.rodzaj == w["format"] and wyd.status == "OK"
        assert wyd.struktura["akapity"] > 5
        inna = tmp_path / f"{w['id']}.txt"
        inna.write_bytes(plik.read_bytes())
        assert ekstrakcja.wydobadz(inna).rodzaj == w["format"] and ekstrakcja.wydobadz(inna).status == "OK"
    rtf = next(w for w in wpisy if w["format"] == "rtf")
    odt = next(w for w in wpisy if w["format"] == "odt")
    o = ocen_plik(cel / odt["plik"], cel / rtf["plik"], wartosci_wpisu(odt), leksykon={})
    assert o.status == "OK" and o.integralnosc["format"] == "odt" and o.integralnosc["format_zgodny"] is False
    assert o.integralnosc["zachowanie_struktury"] is None
    vcf = tmp_path / "k.vcf"
    vcf.write_bytes(b"BEGIN:VCARD\r\nVERSION:3.0\r\nFN:Jan Nowak\r\nEND:VCARD\r\n")
    assert ekstrakcja.wydobadz(vcf).rodzaj == "vcard" and ekstrakcja.wydobadz(vcf).status == "OK"


def test_sedzia_vcard_rozwiniecie_ucieczki_qp(tmp_path):
    vcf = ("BEGIN:VCARD\r\nVERSION:2.1\r\nN;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:=C5=81ukasiewicz;Bo=C5=BCena;;;\r\n"
           "FN:Bożena Łukasie\r\n wicz\r\nORG:Kowal\\, Nowak i Wsp\\;\r\nADR;WORK:;;ul. Długa 5;Gdańsk;;80-001;\r\n"
           "TEL:+48 600 700 800\r\nEND:VCARD\r\n").encode()
    w = ekstrakcja.Wydobycie()
    ekstrakcja._vcard(vcf, "zal:", w)
    linie = w.czesci[0].linie
    assert "Łukasiewicz Bożena" in linie and "Bożena Łukasiewicz" in linie and "Kowal, Nowak i Wsp;" in linie
    assert "ul. Długa 5 Gdańsk 80-001" in linie and w.czesci[0].tresc
    # vCard w załączniku EML: wyciek znaleziony, wizytówka zamaskowana – brak wycieku
    m = email.message.EmailMessage()
    m["Subject"], m["From"], m["To"] = "Kontakt", "a@x.test", "b@x.test"
    m.set_content("W załączeniu wizytówka.")
    m.add_attachment(vcf, maintype="text", subtype="vcard", filename="kontakt.vcf")
    org = tmp_path / "o.eml"
    org.write_bytes(m.as_bytes())
    ws = [Wartosc("v.pelne#1", "OSOBA", "Bożena Łukasiewicz", "pl", "zalacznik", "v"),
          Wartosc("v.tel#1", "TELEFON", "+48 600 700 800", "pl", "zalacznik", "v")]
    assert {x[0] for x in ocen_plik(org, org, ws, leksykon={}).wycieki} == {"v.pelne#1", "v.tel#1"}
    m2 = email.message.EmailMessage()
    m2["Subject"], m2["From"], m2["To"] = "Kontakt", "a@x.test", "b@x.test"
    m2.set_content("W załączeniu wizytówka.")
    m2.add_attachment(b"BEGIN:VCARD\r\nVERSION:3.0\r\nFN:[OSOBA_1]\r\nTEL:[TELEFON_1]\r\nEND:VCARD\r\n", maintype="text",
                      subtype="vcard", filename="kontakt.vcf")
    wyn = tmp_path / "w.eml"
    wyn.write_bytes(m2.as_bytes())
    assert ocen_plik(org, wyn, ws, leksykon={}).wycieki == []


# ============================================================================= sędzia: OCR stron PDF w załączniku poczty
def _raster_inline(pdf: bytes, dpi: int = 200) -> bytes:
    """Strony PDF jako obrazy inline (`BI … ID … EI`) – bez warstwy tekstowej i bez obrazów osadzonych (XObject)."""
    from reportlab.pdfgen import canvas
    doc = pdfium.PdfDocument(pdf)
    bufor = io.BytesIO()
    c = canvas.Canvas(bufor, invariant=1)
    for i in range(len(doc)):
        im = doc[i].render(scale=dpi / 72).to_pil().convert("RGB")
        w, h = doc[i].get_size()
        c.setPageSize((w, h))
        c.drawInlineImage(im, 0, 0, w, h)
        c.showPage()
    c.save()
    doc.close()
    return bufor.getvalue()


def _podmien_pdf_eml(plik: Path, cel: Path, nazwa: str, dane: bytes) -> Path:
    m = _eml(plik)
    for p in m.walk():
        if p.get_filename() == nazwa:
            p.set_content(dane, maintype="application", subtype="pdf", filename=nazwa)
    cel.write_bytes(m.as_bytes())
    return cel


def _pdf_eml(plik: Path, nazwa: str) -> bytes:
    return next(p.get_payload(decode=True) for p in _eml(plik).walk() if p.get_filename() == nazwa)


def _uczestnik(przypadek: str, w: dict, tmp: Path, maskuj) -> Path:
    tmp.mkdir(exist_ok=True)
    r = trudne.generuj_dokument_trudny(trudne.PozycjaTrudna(w["id"], w["jezyk"], w["typ"], w["format"], przypadek),
                                       trudne.ZIARNO_TRUDNE, w["split"], tmp, maskuj=maskuj)
    return tmp / r["plik"]


def _wyciek_z_rastra(oczekiwane: set[str], wyciekly: dict[str, str], ws) -> None:
    """Wartości widoczne na rastrze wyciekają (porównanie po tekstach – sędzia przypisuje wyciek wartości o kilku `id` kolejnym
    `id`); dopuszczalny brak jednego identyfikatora, którego OCR nie odczytał (DNI „…533Q” czytane jako „…5330” – identyfikator
    krótszy niż `plik.MIN_DL_ID_ROZMYTEGO` porównywany jest dokładnie po złożeniu znaków mylonych)."""
    teksty = _teksty(ws)
    kategorie = {x.id: x.kategoria for x in ws}
    brak = {teksty[i] for i in oczekiwane} - {teksty[i] for i in wyciekly}
    assert len(oczekiwane) >= 4 and len(brak) <= 1, sorted(brak)
    assert all(kategorie[i] not in ("OSOBA", "ADRES", "TELEFON", "RACHUNEK") for i in oczekiwane if teksty[i] in brak), sorted(brak)


def test_ocr_stron_pdf_w_zalaczniku_eml_raster_wycieka_idealny_zero(warstwa, tmp_path):
    """Orzeczenie po H4a: PDF w załączniku poczty – ta sama ścieżka co samodzielny PDF, z OCR stron. Wynik: wiadomość idealnego
    uczestnika z kartą klienta zastąpioną rastrem (obraz inline) karty ORYGINAŁU – wartości karty wyciekają z OCR stron."""
    cel, wpisy = warstwa[P.UKRYTA_POCZTA]
    w = next(x for x in wpisy if x["format"] == "eml")
    orig, ws = cel / w["plik"], wartosci_wpisu(w)
    ideal = _uczestnik(P.UKRYTA_POCZTA, w, tmp_path / "ideal", Maskowanie())
    nazwa = TP.TEKSTY[w["jezyk"]]["plik_karty"]
    raster = _raster_inline(_pdf_eml(orig, nazwa))
    assert not pdfium.PdfDocument(raster)[0].get_textpage().get_text_range().strip()
    with pikepdf.open(io.BytesIO(raster)) as p:
        assert not list(p.pages[0].images)                       # brak obrazów osadzonych – tylko inline
    wynik = _podmien_pdf_eml(ideal, tmp_path / "wynik.eml", nazwa, raster)
    a = ocen_plik(orig, wynik, ws, leksykon={})
    karta = {x.id for x in ws if x.id.startswith("h.karta.")} & set(a.bazowe)
    wyciekly = {x[0]: x[2] for x in a.wycieki}
    _wyciek_z_rastra(karta, wyciekly, ws)
    assert all("pdf:render strona" in wyciekly[i] for i in karta if i in wyciekly)
    teksty = _teksty(ws)
    assert {teksty[i] for i in wyciekly} <= {teksty[i] for i in karta}                # nic poza kartą
    assert ocen_plik(orig, ideal, ws, leksykon={}).wycieki == []


def test_ocr_stron_pdf_w_wiadomosci_osadzonej_msg(warstwa, tmp_path, monkeypatch):
    """MSG: PDF załącznika wiadomości osadzonej też jest czytany OCR stron (raster karty klienta z oryginału wycieka)."""
    cel, wpisy = warstwa[P.UKRYTA_POCZTA]
    w = next(x for x in wpisy if x["format"] == "msg")
    orig, ws = cel / w["plik"], wartosci_wpisu(w)
    ideal = _uczestnik(P.UKRYTA_POCZTA, w, tmp_path / "ideal", Maskowanie())
    drzewo_o, drzewo_i = pliki_poczta.wczytaj_cfb(orig), pliki_poczta.wczytaj_cfb(ideal)
    zal = next(k for k, v in drzewo_i.items() if isinstance(v, dict) and "__substg1.0_3701000D" in v)
    sciezka = [zal, "__substg1.0_3701000D", "__attach_version1.0_#00000000", "__substg1.0_37010102"]

    def wezel(d, s):
        for k in s[:-1]:
            d = d[k]
        return d
    wezel(drzewo_i, sciezka)[sciezka[-1]] = _raster_inline(wezel(drzewo_o, sciezka)[sciezka[-1]])
    wynik = tmp_path / "wynik.msg"
    zapisz_cfb(wynik, drzewo_i)
    odczyty = []
    prawdziwa = obrazy.ocr_stron_osadzonych
    monkeypatch.setattr(obrazy, "ocr_stron_osadzonych", lambda pdfy, j, drugi=False, trzeci=False:
                        odczyty.append(len(pdfy)) or prawdziwa(pdfy, j, drugi=drugi, trzeci=trzeci))
    a = ocen_plik(orig, wynik, ws, leksykon={})
    assert odczyty and min(odczyty) == 2                          # oba PDF-y: załącznik główny i wiadomości osadzonej
    # wartości karty w PDF wiadomości osadzonej (imię i nazwisko, telefon są też w jej treści – tam zamaskowane)
    wyciekly = {x[0]: x[2] for x in a.wycieki}
    _wyciek_z_rastra({x.id for x in ws if x.id.startswith("h.klient.")} & set(a.bazowe), wyciekly, ws)
    assert all("3701000D" in m and "pdf:render strona" in m for i, m in wyciekly.items() if i.startswith("h.klient."))


def test_ocr_stron_osadzonych_pamiec_podreczna_po_sumie_pliku(warstwa, monkeypatch, tmp_path):
    cel, wpisy = warstwa[P.UKRYTA_POCZTA]
    w = next(x for x in wpisy if x["format"] == "eml")
    wyd = ekstrakcja.wydobadz(cel / w["plik"])
    assert len(wyd.pdfy) == 2
    monkeypatch.setenv("PBENCH_OCR_CACHE", str(tmp_path / "ocr"))
    renderowane = []
    prawdziwy = ekstrakcja.renderuj_strony
    monkeypatch.setattr(ekstrakcja, "renderuj_strony", lambda p, dpi=300: renderowane.append(dpi) or prawdziwy(p, dpi))
    a = obrazy.ocr_stron_osadzonych(wyd.pdfy, "pl")
    assert len(renderowane) == 2 and all(n.startswith("zal(") and "pdf:render strona 1" in n for n, _ in a)
    assert obrazy.ocr_stron_osadzonych(wyd.pdfy, "pl") == a and len(renderowane) == 2      # drugi raz z pamięci podręcznej
    assert len(list((tmp_path / "ocr").glob("strony-*.json"))) == 2             # klucz: suma pliku PDF (dwa różne PDF-y)


# ============================================================================= sanity: oryginał / idealny / naiwny
class TrescGlowna(Maskowanie):
    """Uczestnik „naiwny”: czyści tylko główną treść wiadomości (i nagłówki) – nie widzi załączników przypadku (`Dokument.ukryte`)
    ani wątku cytowanego (wartości z cechą `cytat`)."""

    def _zamien(self, w: Wartosc) -> Wartosc:
        return w if TP.CECHA_CYTAT in w.cechy else super()._zamien(w)

    def __call__(self, d):
        n = super().__call__(d)
        n.ukryte = type(d).from_dict(d.to_dict()).ukryte
        return n


class BezMiejsc(Maskowanie):
    """Uczestnik czyszczący tylko treść i tabele (RTF/ODT): nagłówek, stopka, komentarze, przypisy i metadane zostają."""

    def _zamien(self, w: Wartosc) -> Wartosc:
        return super()._zamien(w) if w.miejsce in ("tresc", "tabela") else w


def _teksty(ws) -> dict[str, str]:
    return {x.id: normalizuj(x.tekst) for x in ws}


def _slowa(tekst: str) -> set[str]:
    """Słowa i ich pięcioliterowe początki (rdzeń sędziego łączy formę odmienioną z mianownikiem: „Nowaka” – „Nowak”)."""
    slowa = set(re.findall(r"\w+", tekst))
    return slowa | {f"{s[:5]}…" for s in slowa if len(s) >= 5}


@pytest.mark.parametrize("przypadek,i", [(p, i) for p in P.H4B for i in range(N_DOKUMENTOW)])
def test_sanity_oryginal_i_idealny(warstwa, tmp_path, przypadek, i):
    cel, w, orig = _dok(warstwa, przypadek, i)
    ws = wartosci_wpisu(w)
    a = ocen_plik(orig, orig, ws, leksykon={})
    assert a.status == "OK"
    wyciekly = {x[0] for x in a.wycieki}
    teksty = _teksty(ws)
    oceniane = {x.id for x in ws} - set(a.niejednoznaczne) - set(a.niewykrywalne)
    # kopia oryginału wycieka wszystko, co sędzia ocenia; poza oceną tylko wartości, które w ogóle nie mogą wyciec
    # (`Regula.moze_wyciec` False – reguła istniejąca, symetryczna dla wszystkich uczestników: np. kod pocztowy w wizytówce, którego
    # tokeny są cyframi spoza identyfikatorów, także „08-980”; poza mianownikiem, adres ocenia ulica i miejscowość)
    zb = sedzia_plik.zbiory_dokumentu(orig, ws, leksykon={})
    niemozliwe = oceniane - {x.id for g in zb.grupy for x in g.wartosci}
    assert {teksty[i] for i in oceniane - niemozliwe} <= {teksty[i] for i in wyciekly}, sorted(oceniane - wyciekly - niemozliwe)
    specjalne = {x.id for x in ws if x.id.startswith("h.")} - set(a.niejednoznaczne) - set(a.niewykrywalne) - niemozliwe
    assert specjalne and specjalne <= wyciekly, sorted(specjalne - wyciekly)
    ideal = _uczestnik(przypadek, w, tmp_path / "ideal", Maskowanie())
    b = ocen_plik(orig, ideal, ws, leksykon={})
    assert b.status == "OK" and b.integralnosc["otwiera_sie"] and b.integralnosc["format_zgodny"]
    assert not b.wycieki, b.wycieki[:4]


@pytest.mark.parametrize("przypadek", POCZTA)
def test_sanity_naiwny_tresc_glowna_zostawia_wyciek_w_zalacznikach_i_cytatach(warstwa, tmp_path, przypadek):
    """Naiwny uczestnik czyści główną treść wiadomości: wyciekają wartości załączników, wiadomości osadzonej, wątku cytowanego
    i wizytówki; inne wartości – tylko przez słowa wspólne z nimi (to samo miasto albo słowo „Calle” w adresie)."""
    for i in range(N_DOKUMENTOW):
        cel, w, orig = _dok(warstwa, przypadek, i)
        ws = wartosci_wpisu(w)
        a = ocen_plik(orig, orig, ws, leksykon={})
        naiwny = _uczestnik(przypadek, w, tmp_path / f"n{i}", TrescGlowna())
        c = ocen_plik(orig, naiwny, ws, leksykon={})
        dopisek = {x.id for x in ws if x.id.startswith("h.")}
        mozliwe = dopisek & set(a.bazowe)
        wyciekly = {x[0] for x in c.wycieki}
        assert mozliwe and mozliwe <= wyciekly, sorted(mozliwe - wyciekly)
        teksty = _teksty(ws)
        tokeny = {t for x in dopisek for t in _slowa(teksty[x])}
        assert all(_slowa(teksty[x]) & tokeny for x in wyciekly - dopisek), sorted(wyciekly - dopisek)


def test_sanity_naiwny_rtf_odt_czysci_tylko_tresc(warstwa, tmp_path):
    """RTF/ODT: uczestnik czyszczący tylko treść i tabele zostawia wyciek w nagłówku, stopce, komentarzach i metadanych."""
    for i in range(N_DOKUMENTOW):
        cel, w, orig = _dok(warstwa, P.FORMATY_RTF_ODT, i)
        ws = wartosci_wpisu(w)
        a = ocen_plik(orig, orig, ws, leksykon={})
        c = ocen_plik(orig, _uczestnik(P.FORMATY_RTF_ODT, w, tmp_path / f"n{i}", BezMiejsc()), ws, leksykon={})
        poza = {x.id for x in ws if x.miejsce in ("naglowek", "stopka", "komentarz", "metadane", "przypis")} & set(a.bazowe)
        wyciekly = {x[0] for x in c.wycieki}
        teksty = _teksty(ws)
        # porównanie po tekstach: ta sama wartość jest też w treści (zamaskowana), a sędzia przypisuje wyciek kolejnym `id`
        assert poza and {teksty[i] for i in poza} <= {teksty[i] for i in wyciekly}, (w["id"], sorted(poza - wyciekly))
        # wartość treści wycieka tylko przez słowa wspólne z wartością spoza treści (nagłówek, stopka, komentarz, metadane, pola,
        # zmiany, obrazy – tych uczestnik nie czyści) albo przez tę samą wartość zapisaną inaczej (ten sam ciąg znaków
        # alfanumerycznych: telefon „+49 172 …” w treści i „+49172…” w stopce)
        zostawione = {x.id for x in ws if x.miejsce not in ("tresc", "tabela")}
        tokeny = {t for x in zostawione for t in _slowa(teksty[x])}
        alnum = {same_alnum(teksty[x]) for x in zostawione}
        assert all(_slowa(teksty[x]) & tokeny or same_alnum(teksty[x]) in alnum for x in wyciekly - zostawione), \
            sorted(wyciekly - zostawione)


# ============================================================================= poprawki 1 (przegląd H4b)
def test_w1_krotnosc_poczty_pdf_wiadomosci_osadzonej_liczony_osobno(warstwa, tmp_path):
    """W1: render stron w poczcie pokazuje tylko PDF-y załączników – „warstwa tekstowa ALBO render” dotyczy każdego PDF-u osobno.
    Oryginał MSG, w którym PDF wiadomości zagnieżdżonej zastąpiono rastrem (treść bez zmian): klient jest w treści wiadomości
    zagnieżdżonej (#1) i na karcie PDF (#2) – oba wystąpienia wyciekają (wcześniej `max` zlewał treść i stronę PDF-u)."""
    cel, wpisy = warstwa[P.UKRYTA_POCZTA]
    w = next(x for x in wpisy if x["format"] == "msg")
    orig, ws = cel / w["plik"], wartosci_wpisu(w)
    drzewo = pliki_poczta.wczytaj_cfb(orig)
    zal = next(k for k, v in drzewo.items() if isinstance(v, dict) and "__substg1.0_3701000D" in v)
    wezel = drzewo[zal]["__substg1.0_3701000D"]["__attach_version1.0_#00000000"]
    wezel["__substg1.0_37010102"] = _raster_inline(wezel["__substg1.0_37010102"])
    wynik = tmp_path / "raster.msg"
    zapisz_cfb(wynik, drzewo)
    a = ocen_plik(orig, orig, ws, leksykon={})
    oczekiwane = {"h.klient.pelne#2", "h.klient.telefon#2"}
    assert oczekiwane <= set(a.bazowe)
    b = ocen_plik(orig, wynik, ws, leksykon={})
    wyciekly = {x[0]: x[2] for x in b.wycieki}
    assert oczekiwane <= set(wyciekly), sorted(oczekiwane - set(wyciekly))
    assert {"h.klient.pelne#1", "h.klient.telefon#1"} <= set(wyciekly)


def test_w1_krotnosc_poczty_jednostkowo():
    """W1 (jednostkowo, bez OCR): części spoza PDF-ów się sumują, PDF – max(jego części, OCR jego stron), PDF w PDF-ie – osobno."""
    ws = [Wartosc(f"k.pelne#{i}", "OSOBA", "Halina Wierzbicka", "pl", "zalacznik", "k") for i in (1, 2, 3, 4)]
    reg = sedzia_plik.zbuduj_regule(ws[0], sedzia_plik.RegulyWycieku(), set(), [], ocr=False, leksykon=frozenset(), jezyk="pl")
    reg_ocr = sedzia_plik.zbuduj_regule(ws[0], sedzia_plik.RegulyWycieku(), set(), [], ocr=True, leksykon=frozenset(),
                                        jezyk="pl")
    g = sedzia_plik._Grupa(ws, reg, None, reg_ocr, None, True)
    T = sedzia_plik.Tekst
    nazwy = ["eml:czesc 1 text/plain", "zal(a.pdf):pdf:strona 1", "zal(b.pdf):pdf:strona 1", "zal(b.pdf):pdf:zal(c.pdf)/pdf:strona 1"]
    teksty = ["Klient Halina Wierzbicka", "Karta: Halina Wierzbicka", "", "Halina Wierzbicka"]
    strony = [sedzia_plik._Ocr("zal(b.pdf):pdf:render strona 1", "Karta: Halina Wierzbicka"),
              sedzia_plik._Ocr("zal(a.pdf):pdf:render strona 1", "Karta: Halina Wierzbicka")]
    wid = sedzia_plik._Widoki([(n, T(t)) for n, t in zip(nazwy, teksty)], [], [T(t) for t in teksty], [], [strony],
                              pdfy=["zal(a.pdf):", "zal(b.pdf):", "zal(b.pdf):pdf:zal(c.pdf)/"], nazwy_liczenia=nazwy)
    # treść 1 + a.pdf max(1, 1) + b.pdf max(0, 1) + c.pdf max(1, 0)
    assert sedzia_plik._ocen_grupe(g, wid, {})[1] == 4
    bez_pdf = dataclasses.replace(wid, pdfy=[])                       # samodzielny plik: max(tekst 3, render 2)
    assert sedzia_plik._ocen_grupe(g, bez_pdf, {})[1] == 3


_RTF_KSZTALT = (b"{\\rtf1\\ansi\\ansicpg1250\\deff0{\\fonttbl{\\f0\\froman\\fcharset238 Times;}}"
                b"\\pard\\f0 Opiekun: %s\\par %s}")


def _rtf_ksztalt(tmp_path: Path, nazwa: str, osoba: bytes, dopisek: bytes) -> Path:
    plik = tmp_path / f"{nazwa}.rtf"
    plik.write_bytes(_RTF_KSZTALT % (osoba, dopisek))
    return plik


def test_w2_rtf_pole_tekstowe_tekst_alternatywny_wordart_to_tresc(tmp_path):
    """W2: kształty RTF to treść (jak `w:txbxContent`/`descr` w DOCX i `draw:frame` w ODT): nazwisko z polską literą w polu
    tekstowym (`\\shptxt`), tekście alternatywnym (`wzDescription`) i WordArt (`gtextUNICODE`) wycieka; czysty wynik – 0."""
    dude = b"Dud\\u281?"
    org = _rtf_ksztalt(tmp_path, "o", b"Mateusz " + dude, b"")
    ws = [Wartosc("o.pelne#1", "OSOBA", "Mateusz Dudę", "pl", "tresc", "o")]
    assert {x[0] for x in ocen_plik(org, org, ws, leksykon={}).wycieki} == {"o.pelne#1"}
    czysty = _rtf_ksztalt(tmp_path, "c", b"[OSOBA_1]", b"{\\shp{\\*\\shpinst{\\sp{\\sn fFlipH}{\\sv 0}}{\\shptxt \\pard [OSOBA_1]\\par}}}")
    assert ocen_plik(org, czysty, ws, leksykon={}).wycieki == []
    warianty = {
        "pole_tekstowe": (b"{\\shp{\\*\\shpinst{\\sp{\\sn fFlipH}{\\sv 0}}{\\shptxt \\pard Opiekun " + dude + b"\\par}}}", "rtf:tresc"),
        "pole_tekstowe_w_naglowku": (b"{\\header \\pard{\\shp{\\*\\shpinst{\\shptxt \\pard Opiekun " + dude + b"\\par}}}\\par}",
                                     "rtf:naglowek"),
        "tekst_alternatywny": (b"{\\*\\shppict{\\pict{\\*\\picprop{\\sp{\\sn wzDescription}{\\sv Podpis " + dude + b"}}}"
                               b"\\pngblip 89504e47}}", "rtf:ksztalt"),
        "wordart": (b"{\\shp{\\*\\shpinst{\\sp{\\sn gtextUNICODE}{\\sv " + dude + b"}}}}", "rtf:ksztalt"),
    }
    for nazwa, (dopisek, czesc) in warianty.items():
        b = ocen_plik(org, _rtf_ksztalt(tmp_path, nazwa, b"[OSOBA_1]", dopisek), ws, leksykon={})
        assert [(x[0], x[2]) for x in b.wycieki] == [("o.pelne#1", czesc)], (nazwa, b.wycieki)
    # nazwy właściwości (`\sn`) zostają strukturalne, wartości (`\sv`) – część `ksztalt`, pole tekstowe – treść miejsca
    o = S_rtf.czytaj(b"{\\rtf1{\\shp{\\*\\shpinst{\\sp{\\sn wzDescription}{\\sv Opis}}{\\shptxt Tekst ramki\\par}}}}")
    assert "".join(o.strukturalne["sn"]) == "wzDescription\n" and "Opis" in "".join(o.teksty["ksztalt"])
    assert "Tekst ramki" in "".join(o.teksty["tresc"])


def test_w3_autor_komentarza_rtf_z_polska_litera_zostaje_w_gold(tmp_path):
    """W3: LibreOffice zapisuje `\\atnauthor` 8-bitowo („Micha? Koz?owski”) – generator przepisuje pole na `\\uN\\'3f`; odczyt
    zwrotny LibreOffice'em (gold) i parser sędziego widzą „Michał Kozłowski”. Autorzy zmian (`\\revtbl`) – już jako `\\uN`."""
    if shutil.which("soffice") is None:
        pytest.skip("brak LibreOffice")
    from pbench.model import Dokument, Element
    W = lambda i, t, m: Wartosc(i, "OSOBA", t, "pl", m, i)     # noqa: E731
    d = Dokument("t", "pl", "umowa", "rtf", [
        Element("akapit", ["Umowa zawarta z ", W("a#1", "Grażyna Wróbel", "tresc"), "."]),
        Element("komentarz", [W("k#1", "Michał Kozłowski", "komentarz"), ": proszę sprawdzić."], {"autor_fragment": 0}),
        Element("zmiany", [W("z#1", "Paweł Siemiński", "zmiany"), " dopisek"], {"autor_fragment": 0, "typ": "ins"})])
    plik = tmp_path / "t.rtf"
    wynik = R_rtf.renderuj_rtf(d, plik, {"komentarze", "zmiany"})
    assert [w.id for w in wynik.wartosci] == ["a#1", "k#1", "z#1"] and wynik.ostrzezenia == []
    dane = plik.read_bytes()
    assert b"{\\*\\atnauthor \\uc1 Micha\\u322\\'3f Koz\\u322\\'3fowski}" in dane and b"Micha?" not in dane
    assert "Michał Kozłowski" in "".join(S_rtf.czytaj(dane).teksty["komentarz"])
    assert "Michał Kozłowski" in _rtf_na_tekst(dane)
    assert R_rtf.renderuj_rtf(d, tmp_path / "t2.rtf", {"komentarze", "zmiany"}) and (tmp_path / "t2.rtf").read_bytes() == dane
    # podmiana tylko przy jednoznacznej wartości; pole ASCII bez „?” – bez zmian
    pole = b"{\\*\\atnauthor Igor Zieli?ski}{\\*\\atnauthor Jan Nowak}"
    assert R_rtf.zapisz_pola_unicode(pole, ["Igor Zieliński", "Jan Nowak"]) == (
        b"{\\*\\atnauthor \\uc1 Igor Zieli\\u324\\'3fski}{\\*\\atnauthor Jan Nowak}")
    assert R_rtf.zapisz_pola_unicode(pole, ["Igor Zieliński", "Igor Zieliński".replace("ń", "ś")]) == pole


def test_d1_miniatura_oryginalu_w_idealnym_odt_wycieka(warstwa, tmp_path):
    """D1: miniatura pierwszej strony ODT (`Thumbnails/thumbnail.png`) jest czytana OCR – idealny ODT z miniaturą ORYGINAŁU
    wycieka, idealny ze swoją miniaturą – 0."""
    cel, wpisy = warstwa[P.FORMATY_RTF_ODT]
    w = next(x for x in wpisy if x["format"] == "odt")
    orig, ws = cel / w["plik"], wartosci_wpisu(w)
    ideal = _uczestnik(P.FORMATY_RTF_ODT, w, tmp_path / "ideal", Maskowanie())
    with zipfile.ZipFile(orig) as z:
        miniatura = z.read("Thumbnails/thumbnail.png")
    wynik = tmp_path / "miniatura.odt"
    with zipfile.ZipFile(ideal) as zi, zipfile.ZipFile(wynik, "w") as zw:
        for it in zi.infolist():
            zw.writestr(it, miniatura if it.filename == "Thumbnails/thumbnail.png" else zi.read(it.filename))
    b = ocen_plik(orig, wynik, ws, leksykon={})
    assert len(b.wycieki) >= 3 and all(x[2] == "obraz:Thumbnails/thumbnail.png" for x in b.wycieki), b.wycieki


def test_d2_rtf_bin_dokladnie_n_bajtow():
    """D2: `\\binN` pomija dokładnie N bajtów, rozbiór idzie dalej od następnego bajtu (tekst za danymi w tej samej grupie, dane
    kończące się bajtem `\\` nie „zjadają” nawiasu zamykającego)."""
    o = S_rtf.czytaj(b"{\\rtf1{\\*\\dane\\bin3 abcMateusz Dud\\u281?}\\par Dalej}")
    assert "Mateusz Dudę" in "".join(o.teksty["*dane"]) and "Dalej" in "".join(o.teksty["tresc"])
    o = S_rtf.czytaj(b"{\\rtf1{\\*\\shppict{\\pict\\pngblip\\bin3 ab\\}}\\pard Mateusz Dudek\\par}")
    assert "Mateusz Dudek" in "".join(o.teksty["tresc"]) and o.obrazy == [b"ab\\"]
    assert S_rtf.czytaj(b"{\\rtf1 Tekst\\bin99 ab}").teksty["tresc"] == ["Tekst"]    # dane krótsze niż N – koniec pliku


def test_d3_rtf_u_spoza_zakresu_znak_zastepczy(tmp_path):
    """D3: `\\uN` spoza zakresu Unicode (i ujemne spoza 16 bitów) – znak zastępczy, plik czytelny; para surogatów – jeden znak."""
    o = S_rtf.czytaj(b"{\\rtf1 a\\u99999999?b\\u-99999?c\\u-10179?\\u-8704?d\\u-10179?e\\u-3?}")
    assert "".join(o.teksty["tresc"]) == "a\ufffdb\ufffdc\U0001f600d\ufffde\ufffd"
    org = tmp_path / "o.rtf"
    org.write_bytes(b"{\\rtf1\\ansi \\pard \\u99999999?Klient Mateusz Dud\\u281?\\par}")
    a = ocen_plik(org, org, [Wartosc("o.pelne#1", "OSOBA", "Mateusz Dudę", "pl", "tresc", "o")], leksykon={})
    assert a.status == "OK" and [x[0] for x in a.wycieki] == ["o.pelne#1"]


def test_d5_msg_wiadomosc_osadzona_extract_msg(warstwa, monkeypatch):
    """D5: niezależne potwierdzenie struktury MSG (obok `olefile`): extract_msg czyta wiadomość zagnieżdżoną – temat, nadawcę,
    adresata, datę, treść i jej załącznik PDF. extract_msg 0.58 ma błąd: `EmbeddedMsgAttachment` odwołuje się do nieistniejącego
    `MSGFile.prefixList` (dotyczy każdego osadzonego MSG, także z Outlooka) – łatka jednej linii poniżej. Otwarcie w Outlooku –
    ręczna kontrola przed publikacją."""
    extract_msg = pytest.importorskip("extract_msg")
    from extract_msg import MSGFile
    monkeypatch.setattr(MSGFile, "prefixList", property(lambda s: list(s._MSGFile__prefix.parts)), raising=False)
    cel, wpisy = warstwa[P.UKRYTA_POCZTA]
    msg = [w for w in wpisy if w["format"] == "msg"]
    assert msg
    for w in msg:
        m = extract_msg.openMsg(str(cel / w["plik"]))
        try:
            osadzone = [a for a in m.attachments if type(a).__name__ == "EmbeddedMsgAttachment"]
            assert len(osadzone) == 1
            e = osadzone[0].data
            naglowki = f"{e.subject}\n{e.sender}\n{e.to}"
            assert e.subject == TP.TEKSTY[w["jezyk"]]["temat_zagn"] and e.date is not None
            for v in _gold(w):
                if v.id.split(".")[1] in ("nadawca", "adresat"):
                    assert v.tekst in naglowki or _w_tekscie(v.tekst, e.body), v
            pdfy = [a.data for a in e.attachments if isinstance(a.data, bytes) and a.data[:5] == b"%PDF-"]
            assert len(pdfy) == 1
            tekst = e.body + "\n" + _tekst_pdf(pdfy[0])
            assert all(_w_tekscie(v.tekst, tekst) for v in _gold(w, "klient"))
        finally:
            m.close()


def test_d6_miasto_wizytowki_spoza_dokumentu(warstwa):
    """D6: miasto wizytówki jest spoza miast dokumentu (treść, wątek) – nie wypada jako niejednoznaczne."""
    cel, wpisy = warstwa[P.CYTOWANE_WATKI_VCARD]
    for w in wpisy:
        ws = wartosci_wpisu(w)
        miasto = next(x for x in ws if x.id.startswith("h.vcard.miejscowosc"))
        zb = sedzia_plik.zbiory_dokumentu(cel / w["plik"], ws, leksykon={})
        assert miasto.id not in zb.niejednoznaczne, (w["id"], miasto.tekst)
        assert miasto.id in zb.bazowe


def test_d7_zepsuta_warstwa_pdf_w_zalaczniku_poczty(warstwa, tmp_path, monkeypatch):
    """D7: PDF w załączniku poczty ze zepsutą mapą ToUnicode – OCR jego stron wchodzi do zbiorów dokumentu (jak samodzielny PDF);
    zdrowy PDF załącznika – nie. Kopia oryginału nadal wycieka wartości karty (OCR stron)."""
    cel, wpisy = warstwa[P.UKRYTA_POCZTA]
    w = next(x for x in wpisy if x["format"] == "eml")
    orig, ws = cel / w["plik"], wartosci_wpisu(w)
    nazwa = TP.TEKSTY[w["jezyk"]]["plik_karty"]
    przekazane = []
    prawdziwa = sedzia_plik.niejednoznaczne
    monkeypatch.setattr(sedzia_plik, "niejednoznaczne", lambda c, o, ws_, s=1, ocr_stron=(), zloz=None:
                        przekazane.append(list(ocr_stron)) or prawdziwa(c, o, ws_, s, ocr_stron, zloz))   # zloz: H6a (szkielet)
    zb = sedzia_plik.zbiory_dokumentu(orig, ws, leksykon={})
    assert not zb.zepsuty and przekazane[-1] == []
    jezyk_ocr = zb.jezyk_ocr
    for tryb in ("pua", "usuniete"):
        pdf = tmp_path / f"{tryb}.pdf"
        pdf.write_bytes(_pdf_eml(orig, nazwa))
        assert pliki_pdf.zepsuj_tounicode(pdf, tryb) >= 1
        zepsuty = _podmien_pdf_eml(orig, tmp_path / f"{tryb}.eml", nazwa, pdf.read_bytes())
        wyd = ekstrakcja.wydobadz(zepsuty)
        ocr = sedzia_plik.ocr_stron_pliku(zepsuty, wyd, jezyk_ocr)
        assert sedzia_plik.zepsute_pdfy_poczty(wyd, ws, ocr) == {f"zal({nazwa}):"}, tryb
        zb = sedzia_plik.zbiory_dokumentu(zepsuty, ws, leksykon={})
        assert zb.zepsuty and przekazane[-1] and all(t in [x for _, x in ocr] for t in przekazane[-1])
        a = ocen_plik(zepsuty, zepsuty, ws, leksykon={})
        karta = {x.id for x in ws if x.id.startswith("h.karta.")} & set(a.bazowe)
        assert karta and karta <= {x[0] for x in a.wycieki}


@pytest.mark.parametrize("kodowanie", ["utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"])
def test_d8_vcard_bom_i_utf16(tmp_path, kodowanie):
    """D8: vCard z BOM-em UTF-8 i w UTF-16 (z BOM-em i bez) rozpoznawany po treści i czytany (wartości bez znaków ucieczki)."""
    vcf = "BEGIN:VCARD\r\nVERSION:3.0\r\nFN:Bożena Łukasiewicz\r\nORG:Kowal\\, Nowak\r\nTEL:+48 600 700 800\r\nEND:VCARD\r\n"
    plik = tmp_path / "k.vcf"
    plik.write_bytes(vcf.encode(kodowanie))
    wyd = ekstrakcja.wydobadz(plik)
    assert wyd.rodzaj == "vcard" and wyd.status == "OK"
    linie = next(c for c in wyd.czesci if c.nazwa == "vcard").linie
    assert "Bożena Łukasiewicz" in linie and "Kowal, Nowak" in linie and "+48 600 700 800" in linie


def test_d9_normalizuj_rtf_tylko_slowa_kontrolne():
    """D9: przenumerowanie czcionek dotyczy słów kontrolnych (nieparzysta liczba ukośników), nie tekstu „C:\\\\f1”."""
    rtf = b"{\\rtf1{\\fonttbl{\\f0 B;}{\\f1 A;}}\\f1 C:\\\\f1 \\\\\\f0 x\\\\\\\\f0}"
    assert R_rtf.normalizuj_rtf(rtf) == b"{\\rtf1{\\fonttbl{\\f0 A;}{\\f1 B;}}\\f0 C:\\\\f1 \\\\\\f1 x\\\\\\\\f0}"


# ============================================================================= poprawki 2: I1 (przedrostek załącznika), I2 (widok surowy RTF)
def _pdf_tekst_reportlab(linie: list[str], niewidoczny: bool = False) -> bytes:
    """PDF z jedną stroną tekstu; `niewidoczny` = tryb renderowania 3 (tekst w warstwie, bez rysunku – OCR go nie widzi)."""
    from reportlab.pdfgen import canvas
    bufor = io.BytesIO()
    c = canvas.Canvas(bufor, invariant=1)
    t = c.beginText(72, 700)
    t.setFont("Helvetica", 14)
    if niewidoczny:
        t.setTextRenderMode(3)
    for l in linie:
        t.textLine(l)
    c.drawText(t)
    c.showPage()
    c.save()
    return bufor.getvalue()


@pytest.mark.parametrize("nazwa_b", ["zalacznik.pdf", "inny.pdf"])
def test_i1_dwa_pdf_o_tej_samej_nazwie_w_eml_liczone_osobno(warstwa, tmp_path, nazwa_b):
    """I1: dwa załączniki PDF o tej samej nazwie (raster = tylko OCR strony, niewidoczny tekst = tylko warstwa) – każdy PDF ma
    własny przedrostek (`zal(nazwa#2):`), więc wartość o dwóch `id` wycieka dwa razy (wcześniej `#2` ginął przy wspólnej nazwie)."""
    cel, w, orig = _dok(warstwa, P.UKRYTA_POCZTA, next(i for i, x in enumerate(warstwa[P.UKRYTA_POCZTA][1]) if x["format"] == "eml"))
    ws = wartosci_wpisu(w)
    teksty = {x.id: x.tekst for x in ws}
    x = next(x.tekst for x in ws if x.id.startswith("h.klient.pelne"))
    ids = sorted(i for i, t in teksty.items() if t == x)
    assert len(ids) == 2
    ideal = _uczestnik(P.UKRYTA_POCZTA, w, tmp_path / "ideal", Maskowanie())
    m = _eml(ideal)
    if not m.is_multipart():
        m.make_mixed()
    m.add_attachment(_raster_inline(_pdf_tekst_reportlab(["Karta", x])), maintype="application", subtype="pdf", filename="zalacznik.pdf")
    m.add_attachment(_pdf_tekst_reportlab(["Notatka", x], niewidoczny=True), maintype="application", subtype="pdf", filename=nazwa_b)
    wynik = tmp_path / "dwa.eml"
    wynik.write_bytes(m.as_bytes())
    nazwy = {c.nazwa.split("pdf:")[0] for c in ekstrakcja.wydobadz(wynik).czesci
             if re.match(r"zal\((zalacznik|inny)\.pdf(#2)?\):pdf:", c.nazwa)}
    assert nazwy == {"zal(zalacznik.pdf):", "zal(zalacznik.pdf#2):" if nazwa_b == "zalacznik.pdf" else "zal(inny.pdf):"}, nazwy
    b = ocen_plik(orig, wynik, ws, leksykon={})
    assert set(ids) <= {x_[0] for x_ in b.wycieki}, [(x_[0], x_[2]) for x_ in b.wycieki if x_[0] in ids]


def test_i1_kolejne_zalaczniki_bez_nazwy_dostaja_numer(tmp_path):
    """I1: załączniki bez nazwy (przedrostek z typu MIME) też są rozróżniane; pierwsze wystąpienie bez zmian."""
    m = email.message.EmailMessage()
    m["From"], m["To"], m["Subject"] = "a@example.com", "b@example.com", "x"
    m.set_content("treść")
    for t in ("a", "b", "c"):
        m.add_attachment(_pdf_tekst_reportlab([f"Karta {t}"]), maintype="application", subtype="pdf")
    plik = tmp_path / "bez-nazw.eml"
    plik.write_bytes(m.as_bytes())
    nazwy = sorted({c.nazwa.split("pdf:")[0] for c in ekstrakcja.wydobadz(plik).czesci if c.nazwa.startswith("zal(")})
    assert nazwy == ["zal(application/pdf#2):", "zal(application/pdf#3):", "zal(application/pdf):"], nazwy


def test_i2_widok_surowy_rtf_slowa_z_bialej_listy_zastapione_spacja():
    """I2: słowo sterujące z białej listy (`\\info`, `\\author`, `\\u322` z parametrem) znika z widoku; spoza listy
    (`\\Kowalski`) zostaje tekstem; podwójny ukośnik to tekst (`\\\\info` nie jest słowem sterującym)."""
    rtf = b"{\\rtf1\\ansi{\\info{\\author X}}\\par info.a@example.com \\Kowalski \\u322?\\fs24 b \\\\info}"
    widok = ekstrakcja._bez_slow_rtf(rtf)
    assert b"\\info" not in widok.replace(b"\\\\info", b"") and b"\\author" not in widok and b"\\u322" not in widok
    assert b"info.a@example.com" in widok and b"\\Kowalski" in widok and b"\\\\info" in widok


def _rtf_info(tmp_path: Path, nazwa: str, tresc: bytes) -> Path:
    plik = tmp_path / nazwa
    plik.write_bytes(b"{\\rtf1\\ansi\\deff0{\\fonttbl{\\f0 Arial;}}{\\info{\\title T}}\\pard " + tresc + b"\\par}")
    return plik


def test_i2_adres_info_w_wartosci_nie_trafia_w_slowo_info_rtf(tmp_path):
    """I2: idealny RTF z grupą `{\\info …}` i adresem `info.…@` w gold → 0 wycieków; ten sam adres w pliku wycieka."""
    ws = [Wartosc("e.email#1", "EMAIL", "info.kancelaria@example.com", "pl", "tresc", "e.email")]
    orig = _rtf_info(tmp_path, "o.rtf", b"Kontakt: info.kancelaria@example.com")
    ideal = _rtf_info(tmp_path, "i.rtf", b"Kontakt: [EMAIL_1]")
    assert {x[0] for x in ocen_plik(orig, orig, ws, leksykon={}).wycieki} == {"e.email#1"}
    b = ocen_plik(orig, ideal, ws, leksykon={})
    assert b.status == "OK" and b.wycieki == [], b.wycieki


def test_i2_nieznane_slowo_sterujace_z_nazwiskiem_wycieka(tmp_path):
    """I2: lista jest zamknięta – wartość ukryta pod wymyślonym słowem sterującym (`\\Kowalski`) nadal wycieka z widoku surowego;
    to samo dla słowa spoza listy w ASCII-owym adresie."""
    ws = [Wartosc("o.osoba#1", "OSOBA", "Jan Kowalski", "pl", "tresc", "o.osoba"),
          Wartosc("e.email#1", "EMAIL", "zbigniew.nowicki@example.com", "pl", "tresc", "e.email")]
    orig = _rtf_info(tmp_path, "o.rtf", b"Jan Kowalski, zbigniew.nowicki@example.com")
    ukryty = _rtf_info(tmp_path, "u.rtf", b"[OSOBA_1] {\\*\\Kowalski ukryte}\\Nowicki \\zbigniew.nowicki@example.com")
    b = ocen_plik(orig, ukryty, ws, leksykon={})
    assert b.status == "OK" and {"o.osoba#1", "e.email#1"} <= {x[0] for x in b.wycieki}, b.wycieki


@pytest.mark.parametrize("ziarno", [4242, 7, 20261101, 101, 31337, 424242])
def test_i2_idealny_rtf_i_odt_na_innych_ziarnach_zero(tmp_path, ziarno):
    """I2: sanity na świeżych ziarnach (stałe ziarno nie trafia na adres `info.…@`): idealny RTF i ODT → 0 wycieków. 12 dokumentów
    na ziarno; ziarna 101 i 31337 (N1): szum OCR miniatury ODT („Osowa” z „Osoba” ≈ „Sowa”, „ilogin”) – rozmyty, więc bez
    potwierdzenia innym trybem nie jest wyciekiem częściowym; 424242 (H4b fix4 I2): „ma\\u241\\'f1ana” w `rtf:surowe` nie daje
    słowa „ana” wartości „Ana Merino Sebastián”."""
    cel = tmp_path / "k"
    wpisy = trudne.zbuduj_przypadek(cel, P.FORMATY_RTF_ODT, 12, ziarno=ziarno, procesy=1)
    assert {w["format"] for w in wpisy} == {"rtf", "odt"}
    for w in wpisy:
        ws = wartosci_wpisu(w)
        ideal = _uczestnik_ziarno(P.FORMATY_RTF_ODT, w, tmp_path / "i" / w["id"], ziarno)
        b = ocen_plik(cel / w["plik"], ideal, ws, leksykon={})
        assert b.status == "OK" and b.wycieki == [], (w["id"], b.wycieki[:3])


def _uczestnik_ziarno(przypadek: str, w: dict, tmp: Path, ziarno: int) -> Path:
    tmp.mkdir(parents=True, exist_ok=True)
    r = trudne.generuj_dokument_trudny(trudne.PozycjaTrudna(w["id"], w["jezyk"], w["typ"], w["format"], przypadek),
                                       ziarno, w["split"], tmp, maskuj=Maskowanie())
    return tmp / r["plik"]


# ============================================================================= N1: trafienia częściowe z OCR obrazu osadzonego
def _grupa_obrazu(tekst: str, kategoria: str = "OSOBA") -> sedzia_plik._Grupa:
    w = Wartosc("x#1", kategoria, tekst, "pl", "tresc", kategoria)
    reg, reg_ocr = (sedzia_plik.zbuduj_regule(w, sedzia_plik.RegulyWycieku(), set(), [], ocr=ocr, leksykon=frozenset(),
                                              jezyk="pl") for ocr in (False, True))
    return sedzia_plik._Grupa([w], reg, None, reg_ocr, None, True)


def _ocen_obraz(g: sedzia_plik._Grupa, tekst: str, tryby: tuple[int, ...]):
    """`_ocen_grupe` na samym OCR jednego obrazu osadzonego (odczyty rozdzielone `ODDZIELACZ`, `tryby` – psm każdego odczytu)."""
    wid = sedzia_plik._Widoki([], [], [], [sedzia_plik._Ocr("Thumbnails/thumbnail.png", tekst, tryby)])
    return sedzia_plik._ocen_grupe(g, wid, {})


def test_n1_czesciowe_z_obrazu_osadzonego_liczy_sie_z_potwierdzeniem_innym_trybem():
    """N1: trafienie częściowe z OCR obrazu osadzonego (miniatura ODT, obrazy DOCX/XLSX/PPTX i PDF, załączniki-obrazy poczty)
    liczy się – jak na stronach PDF – tylko z potwierdzeniem w innym odczycie tego obrazu, i to odczycie INNYM trybem Tesseracta:
    psm 6 czyta „Osoba” z miniatury jako „Osowa” (≈ „Sowa”) w skali ×3, ×5 i ×10, psm 11 – nie. Brak potwierdzenia – brak wycieku
    i numer obrazu do drugiego odczytu. Pełne z jednego odczytu wystarcza, chyba że złożone wyłącznie z trafień rozmytych."""
    g = _grupa_obrazu("Robert Sowa")
    M = "obraz:Thumbnails/thumbnail.png"
    szum = "Osowa prowadząca sprawę"
    assert _ocen_obraz(g, f"{szum}\fOsoba prowadząca", (6, 11)) == (None, 0, False, frozenset({0}))
    # drugi odczyt (te same tryby, skala ×2): szum ROZMYTY w tym samym trybie w innej skali nie potwierdza (fix4 I1)
    assert _ocen_obraz(g, f"{szum}\fOsoba prowadząca\f{szum}\fOsoba", (6, 11, 6, 11)) == (None, 0, False, frozenset({0}))
    # samo nazwisko w dwóch trybach – wyciek częściowy; także między odczytami w różnych skalach
    assert _ocen_obraz(g, "Prowadzi: Sowa\fProwadzi: Sowa", (6, 11)) == ((M, "czesciowy"), 1, False, frozenset())
    assert _ocen_obraz(g, "Prowadzi: Sowa\fProwadzi\fProwadzi\fProwadzi: Sowa", (6, 11, 6, 11))[0] == (M, "czesciowy")
    # duży obraz: psm 3 potwierdza dopiero odczyt psm 6 albo 11 (drugi odczyt)
    assert _ocen_obraz(g, "Prowadzi: Sowa", (3,))[3] == frozenset({0})
    assert _ocen_obraz(g, "Prowadzi: Sowa\fProwadzi: Sowa\fProwadzi", (3, 6, 11))[0] == (M, "czesciowy")
    # pełne z jednego odczytu; złożone z samych trafień rozmytych – dopiero potwierdzone innym trybem
    assert _ocen_obraz(g, "Prowadzi: Robert Sowa\fProwadzi", (6, 11)) == ((M, "pelny"), 1, False, frozenset())
    assert _ocen_obraz(g, "Roberrt Sowva\fProwadzi", (6, 11)) == (None, 0, False, frozenset({0}))
    assert _ocen_obraz(g, "Roberrt Sowva\fProwadzi\fRoberrt Sowva", (6, 11, 6))[0] is None
    assert _ocen_obraz(g, "Roberrt Sowva\fRoberrt Sowva", (6, 11))[0] == (M, "pelny")
    # strona PDF (bez trybów): każdy odczyt niezależny – jak dotąd
    assert _ocen_obraz(g, f"{szum}\f{szum}", ())[0] == (M, "czesciowy")


def test_i1_ten_sam_tryb_w_innej_skali_potwierdza_token_dokladny(monkeypatch):
    """H4b fix4 I1 (b): odczyt tym samym trybem w innej skali potwierdza, gdy wspólny token jest DOKŁADNY w którymś z dwóch
    odczytów – pieczątka DOCX 741×131 („[OSOBA_7] Bernal”): psm 6 nie czyta nic, psm 11 czyta „Bernal” dokładnie w ×1 i ×2;
    pieczątka 348×168 („Szymański”) – odwrotnie, tylko psm 6. Rozmyty („Osowa” ≈ „Sowa”) w obu skalach – nadal nie."""
    M = "obraz:Thumbnails/thumbnail.png"
    g = _grupa_obrazu("Alfonso Bernal")
    assert _ocen_obraz(g, "\fPresidente: [OSOBA_7] Bernal\f\fPresidente: [OSOBA_7] Bernal", (6, 11, 6, 11)) == \
        ((M, "czesciowy"), 1, False, frozenset())
    # jeden dokładny odczyt krótkiego tokenu (6 znaków) – bez potwierdzenia
    assert _ocen_obraz(g, "\fPresidente: [OSOBA_7] Bernal", (6, 11)) == (None, 0, False, frozenset({0}))
    g = _grupa_obrazu("Robert Sowa")
    assert _ocen_obraz(g, "Sowa\f\fSowa\f", (6, 11, 6, 11))[0] == (M, "czesciowy")
    assert _ocen_obraz(g, "Osowa\f\fOsowa\f", (6, 11, 6, 11)) == (None, 0, False, frozenset({0}))
    # dokładny w jednej skali, rozmyty w drugiej – potwierdza; rozmyty w obu – nie (bez reguły długiego tokenu)
    monkeypatch.setattr(sedzia_plik, "MIN_DL_TOKENU_BEZ_POTWIERDZENIA", 99)
    g = _grupa_obrazu("Robert Kowalczyk")
    assert _ocen_obraz(g, "Kowalczyk\f\fKowalczyx\f", (6, 11, 6, 11))[0] == (M, "czesciowy")
    assert _ocen_obraz(g, "Kowalczyx\f\fKowalczyx\f", (6, 11, 6, 11)) == (None, 0, False, frozenset({0}))


def test_i1_dlugi_token_dokladny_z_jednego_odczytu_obrazu_osadzonego():
    """H4b fix4 I1 (c): token identyfikujący ≥ `MIN_DL_TOKENU_BEZ_POTWIERDZENIA` (7) znaków trafiony DOKŁADNIE w jednym odczycie
    obrazu osadzonego wystarcza („[OSOBA_1] Szymański” w zrzucie 360×156); rozmyty („Szymańsky”) albo krótszy („Díez”) – nie;
    strona PDF (odczyty bez trybów) – reguła nie dotyczy (H4a R1)."""
    M = "obraz:Thumbnails/thumbnail.png"
    assert sedzia_plik.MIN_DL_TOKENU_BEZ_POTWIERDZENIA == 7
    g = _grupa_obrazu("Bartosz Szymański")
    assert _ocen_obraz(g, "Klient: [OSOBA_1] Szymański\fKlient:", (6, 11)) == ((M, "czesciowy"), 1, False, frozenset())
    assert _ocen_obraz(g, "Klient: [OSOBA_1] Szymańsky\fKlient:", (6, 11)) == (None, 0, False, frozenset({0}))
    assert _ocen_obraz(g, "Klient: [OSOBA_1] Szymański", ()) == (None, 0, False, frozenset({0}))
    g = _grupa_obrazu("Álvaro Díez")
    assert _ocen_obraz(g, "Médico: [OSOBA_23] Díez\fMédico:", (6, 11)) == (None, 0, False, frozenset({0}))


#: Obrazy syntetyczne z przeglądu (rr3, `syn.py`): styl, skala, osoba, organizacja – małe obrazy, w których nazwisko czyta dokładnie
#: tylko jeden tryb (pieczątka) albo tylko jeden odczyt (zrzuty).
_SYNTETYCZNE = [("pieczatka", 0.6, ("Bartosz", "Szymański"), "Dąbrowska"), ("zrzut", 0.6, ("Bartosz", "Szymański"), "Dąbrowska"),
                ("zrzut_duzy", 0.6, ("Joanna", "Zielińska"), "Wróblewski")]


def _obraz_syntetyczny(styl: str, s: float, osoba: str, org: str, adres: str) -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    def font(plik: str, r: float):
        return ImageFont.truetype(f"/usr/share/fonts/truetype/{plik}", max(6, int(round(r))))
    sansb, lib = "dejavu/DejaVuSans-Bold.ttf", "liberation/LiberationSans-Regular.ttf"
    if styl == "pieczatka":
        im = Image.new("RGB", (int(560 * s), int(220 * s)), "white")
        d = ImageDraw.Draw(im)
        d.rectangle([int(8 * s), int(8 * s), int(552 * s), int(212 * s)], outline=(200, 20, 20), width=max(1, int(4 * s)))
        y = 24 * s
        for t in (org, osoba, adres, "NIP 527-104-55-83"):
            d.text((int(24 * s), int(y)), t, fill=(200, 20, 20), font=font(sansb, 22 * s))
            y += 44 * s
        im = im.rotate(6, expand=True, fillcolor="white")
    elif styl == "zrzut":
        im = Image.new("RGB", (int(600 * s), int(260 * s)), (245, 246, 248))
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, int(600 * s), int(30 * s)], fill=(60, 70, 90))
        d.text((int(10 * s), int(6 * s)), "CRM - karta klienta", fill="white", font=font(lib, 15 * s))
        y = 45 * s
        for k, v in (("Klient", osoba), ("Firma", org), ("Adres", adres), ("Status", "aktywny")):
            d.text((int(14 * s), int(y)), k + ":", fill=(110, 110, 110), font=font(lib, 14 * s))
            d.text((int(120 * s), int(y)), v, fill=(30, 30, 30), font=font(lib, 14 * s))
            y += 34 * s
    else:
        im = Image.new("RGB", (int(1280 * s), int(720 * s)), (250, 250, 250))
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, int(1280 * s), int(40 * s)], fill=(40, 90, 160))
        d.rectangle([0, int(40 * s), int(220 * s), int(720 * s)], fill=(230, 233, 238))
        for i, t in enumerate(("Pulpit", "Sprawy", "Klienci", "Faktury")):
            d.text((int(20 * s), int((70 + 40 * i) * s)), t, fill=(60, 60, 60), font=font(lib, 15 * s))
        y = 80 * s
        for k, v in (("Klient", osoba), ("Pełnomocnik", org), ("Adres do doręczeń", adres), ("Sygnatura", "I C 1234/25")):
            d.text((int(260 * s), int(y)), k, fill=(120, 120, 120), font=font(lib, 13 * s))
            d.text((int(460 * s), int(y)), v, fill=(20, 20, 20), font=font(lib, 13 * s))
            y += 36 * s
    bufor = io.BytesIO()
    im.save(bufor, "PNG")
    return bufor.getvalue()


def _eml_z_png(sciezka: Path, png: bytes) -> Path:
    m = email.message.EmailMessage(policy=policy.default)
    m["From"], m["To"], m["Subject"] = "biuro@example.com", "sad@example.com", "Dokumenty"
    m.set_content("W załączeniu dokument.")
    m.add_attachment(png, maintype="image", subtype="png", filename="obraz.png")
    sciezka.write_bytes(m.as_bytes())
    return sciezka


@pytest.mark.parametrize("styl,skala,osoba,nazwa", _SYNTETYCZNE)
def test_i1_male_obrazy_syntetyczne_czesciowy_wycieka_idealny_zero(tmp_path, styl, skala, osoba, nazwa):
    """H4b fix4 I1: prawdziwy wyciek częściowy (imię zamaskowane, nazwisko zostaje) na małym obrazie w skali 0,6 – zgubiony przez
    regułę „potwierdza tylko inny tryb” – liczy się: pieczątka (psm 6 czyta „Szymański” dokładnie w ×1 i ×2, psm 11
    nigdy), zrzuty (nazwisko dokładnie tylko w jednym odczycie, ≥ 7 znaków). Ten sam obraz z samymi zamiennikami – 0."""
    imie, nazwisko = osoba
    adres = "ul. Słoneczna 14, 30-120 Kraków"
    ws = [Wartosc(i, k, t, "pl", "zalacznik", k) for i, k, t in (
        ("x.osoba#1", "OSOBA", f"{imie} {nazwisko}"), ("x.org#1", "ORGANIZACJA", f"Biuro Rachunkowe {nazwa}"),
        ("x.adres#1", "ADRES", adres))]
    orig = _eml_z_png(tmp_path / "o.eml", _obraz_syntetyczny(styl, skala, f"{imie} {nazwisko}", f"Biuro Rachunkowe {nazwa}", adres))
    czes = _eml_z_png(tmp_path / "c.eml", _obraz_syntetyczny(styl, skala, f"[OSOBA_1] {nazwisko}", f"[ORGANIZACJA_2] {nazwa}",
                                                             "ul. [ADRES_3] 14, 30-120 Kraków"))
    ideal = _eml_z_png(tmp_path / "i.eml", _obraz_syntetyczny(styl, skala, "[OSOBA_1]", "[ORGANIZACJA_2]", "[ADRES_3]"))
    b = ocen_plik(orig, czes, ws, leksykon={})
    assert ("x.osoba#1", "obraz:eml:czesc 3/obraz.png", "czesciowy") in {(x[0], x[2], x[3]) for x in b.wycieki}, b.wycieki
    assert ocen_plik(orig, ideal, ws, leksykon={}).wycieki == []


def _eml_z_obrazem(sciezka: Path, wiersze: list[str]) -> Path:
    """EML z załącznikiem PNG (1400 × 500 px – duży obraz: pierwszy odczyt tylko psm 3) z wierszami tekstu."""
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGB", (1400, 500), "white")
    rys, czcionka = ImageDraw.Draw(im), ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 34)
    for i, wiersz in enumerate(wiersze):
        rys.text((20, 20 + 54 * i), wiersz, fill="black", font=czcionka)
    bufor = io.BytesIO()
    im.save(bufor, "PNG")
    m = email.message.EmailMessage(policy=policy.default)
    m["From"], m["To"], m["Subject"] = "biuro@example.com", "sad@example.com", "Skan karty"
    m.set_content("W załączeniu skan karty klienta.")
    m.add_attachment(bufor.getvalue(), maintype="image", subtype="png", filename="karta.png")
    sciezka.write_bytes(m.as_bytes())
    return sciezka


def test_n1_obraz_w_zalaczniku_poczty_czesciowy_potwierdzony_drugim_odczytem(tmp_path):
    """N1: załącznik-obraz poczty czytany tylko psm 3 – trafienie częściowe potwierdza dopiero drugi odczyt (psm 6 i 11),
    więc niezamaskowane nazwisko i nazwa firmy na obrazie nadal wyciekają; obraz z samymi zamiennikami – 0, oryginał – pełne."""
    ws = [Wartosc(i, k, t, "pl", "zalacznik", k) for i, k, t in (
        ("m.osoba#1", "OSOBA", "Halina Wierzbicka"), ("m.telefon#1", "TELEFON", "+48 512 334 871"),
        ("m.firma#1", "ORGANIZACJA", "Zakład Usług Ogrodniczych Wrzos"))]
    orig = _eml_z_obrazem(tmp_path / "orig.eml", ["Karta klienta", "Klient: Halina Wierzbicka", "Tel. +48 512 334 871",
                                                   "Pracodawca: Zakład Usług Ogrodniczych Wrzos"])
    czes = _eml_z_obrazem(tmp_path / "czes.eml", ["Karta klienta", "Klient: [OSOBA_1] Wierzbicka", "Tel. [TELEFON_2]",
                                                   "Pracodawca: Zakład Usług [ORGANIZACJA_3]"])
    ideal = _eml_z_obrazem(tmp_path / "ideal.eml", ["Karta klienta", "Klient: [OSOBA_1]", "Tel. [TELEFON_2]",
                                                     "Pracodawca: [ORGANIZACJA_3]"])
    MIEJSCE = "obraz:eml:czesc 3/karta.png"
    a = ocen_plik(orig, orig, ws, leksykon={})
    assert {(x[0], x[2], x[3]) for x in a.wycieki} == {(w.id, MIEJSCE, "pelny") for w in ws}
    b = ocen_plik(orig, czes, ws, leksykon={})
    assert {(x[0], x[2], x[3]) for x in b.wycieki} == {("m.osoba#1", MIEJSCE, "czesciowy"), ("m.firma#1", MIEJSCE, "czesciowy")}
    assert ocen_plik(orig, ideal, ws, leksykon={}).wycieki == []


def test_i2_widok_surowy_rtf_znaki_szesnastkowe_i_unicode_czescia_slowa(tmp_path):
    """I2 (12 dokumentów na ziarno, 20261101): w widoku `rtf:surowe` znak `\\uN` i `\\'xx` jest częścią słowa, nie granicą –
    „mayor\\u237\\'eda” (mayoría) nie trafia tokenu „Mayor” adresu „Calle Mayor”; wartość zapisana znakami szesnastkowymi
    pod nieznanym słowem sterującym („Gonz\\'e1lez”) wycieka w całości."""
    assert ekstrakcja._znaki_rtf(b"\\ansicpg1250 la mayor\\u237\\'eda Zieli\\'f1ski \\uc1").decode() == \
        "\\ansicpg1250 la mayoríía Zieliński \\uc1"
    ws = [Wartosc("a.adres#1", "ADRES", "Calle Mayor, 197, 20284 Eibar", "es", "tresc", "a.adres"),
          Wartosc("o.osoba#1", "OSOBA", "Lucía González", "es", "tresc", "o.osoba")]
    orig = _rtf_info(tmp_path, "o.rtf", b"Calle Mayor, 197, 20284 Eibar. Luc\\'eda Gonz\\'e1lez")
    ideal = _rtf_info(tmp_path, "i.rtf", b"[ADRES_1]. [OSOBA_2], con la mayor\\u237\\'eda exigida")
    assert ocen_plik(orig, ideal, ws, leksykon={}).wycieki == []
    ukryty = _rtf_info(tmp_path, "u.rtf", b"[ADRES_1]. [OSOBA_2] {\\*\\nieznane Luc\\'eda Gonz\\'e1lez}")
    b = ocen_plik(orig, ukryty, ws, leksykon={})
    assert ("o.osoba#1", "pelny") in {(x[0], x[3]) for x in b.wycieki}, b.wycieki


def test_i2_widok_surowy_rtf_jeden_widok_utf8(tmp_path):
    """H4b fix4 I2: po dekodowaniu `\\uN`/`\\'xx` widok `rtf:surowe` jest jeden (UTF-8) – drugi odczyt cp1250 robił z „ñ”
    (c3 b1) „ă±”, czyli granicę słowa: „ma\\u241\\'f1ana” dawało słowo „ana” wartości „Ana Merino Sebastián” (ziarno 424242,
    `h-ro-es-med_wypis-0001`). Bajty 8-bitowe wpisane wprost (nie UTF-8) są czytane stroną kodową dokumentu: nazwisko w tabeli
    czcionek (strefa czytana tylko surowo) nadal wycieka."""
    widok = ekstrakcja._widok_utf8(ekstrakcja._znaki_rtf(b"vendr\\'e1 ma\\u241\\'f1ana a las 9"))
    assert len(widok) == 1 and "ana" not in re.findall(r"\w+", normalizuj(widok[0])), widok
    assert ekstrakcja._znaki_rtf(b"\\ansicpg1250 {\\f1 D\xb9browski;} \\'e6") == "\\ansicpg1250 {\\f1 Dąbrowski;} ć".encode()
    ws = [Wartosc("f.osoba#1", "OSOBA", "Ana Merino Sebastián", "es", "tresc", "f.osoba")]
    orig = _rtf_info(tmp_path, "o.rtf", b"Familiar: Ana Merino Sebasti\\'e1n")
    ideal = _rtf_info(tmp_path, "i.rtf", b"Familiar: [OSOBA_1]. Alta prevista ma\\u241\\'f1ana, a las 9")
    assert ocen_plik(orig, ideal, ws, leksykon={}).wycieki == []
    ws = [Wartosc("o.osoba#1", "OSOBA", "Jan Dąbrowski", "pl", "tresc", "o.osoba")]
    orig = tmp_path / "o2.rtf"
    orig.write_bytes(b"{\\rtf1\\ansi\\ansicpg1250\\deff0{\\fonttbl{\\f0 Arial;}}\\pard Jan D\\'b9browski\\par}")
    ukryty = tmp_path / "u2.rtf"
    ukryty.write_bytes(b"{\\rtf1\\ansi\\ansicpg1250\\deff0{\\fonttbl{\\f0 Arial;}{\\f1 D\xb9browski;}}\\pard [OSOBA_1]\\par}")
    assert ("o.osoba#1", "rtf:surowe") in {(x[0], x[2]) for x in ocen_plik(orig, ukryty, ws, leksykon={}).wycieki}
