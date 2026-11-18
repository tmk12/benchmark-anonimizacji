"""H6a – sędziowie warstwy trudnych przypadków: homoglify w szkielecie, poziom encji (transliteracje), inicjały (parafy, „Pan K.”),
ukraiński w uruchamianiu (`jezyk_uzyty`), poprawki H5 m1/m2 (agregacja identyfikacji pośredniej) i gramatyka wariantów H2."""
from __future__ import annotations

import dataclasses
import json
import os
import re
from pathlib import Path

import pytest
from docx import Document

from pbench import ocen, posrednie, przypadki as P, trudne, trudne_dlugie, trudne_jezyk, uruchom
from pbench.homoglify import CYR_NA_LAC, homoglify
from pbench.model import Dokument, Element, Wartosc, Wykrycie
from pbench.sedzia.normalizacja import normalizuj, szkielet, wzor_inicjalow, zloz_szkielet
from pbench.sedzia.plik import ocen_plik
from pbench.sedzia.sanity import Maskowanie, wartosci_wpisu
from pbench.sedzia.tekst import KATEGORIE_ID, RegulyWycieku, gold_z_wpisu, ocen_tekst
from pbench.linearyzacja import GoldSpan
from pbench.trudne_wspolne import inicjaly_jednoznaczne

os.environ.setdefault("PBENCH_OCR_WATKI", "2")
R = RegulyWycieku()


def W(wid: str, tekst: str, kat: str = "OSOBA", miejsce: str = "tresc", jezyk: str = "pl") -> Wartosc:
    return Wartosc(wid, kat, tekst, jezyk, miejsce, kat)


def _docx(sciezka: Path, *akapity: str) -> Path:
    d = Document()
    for a in akapity:
        d.add_paragraph(a)
    d.save(sciezka)
    return sciezka


def _wycieki(oryginal: Path, wynik: Path, wartosci: list[Wartosc]) -> dict[str, str]:
    o = ocen_plik(oryginal, wynik, wartosci, leksykon={})
    assert o.status == "OK"
    return {x[0]: x[3] for x in o.wycieki}


# ============================================================================= 1. homoglify – szkielet
def test_szkielet_cyrylicy_mylacej():
    assert szkielet(normalizuj("Kоwalski")) == szkielet(normalizuj("Kowalski")) == "kowalski"       # „о” cyrylickie
    assert szkielet(normalizuj("КОВАЛЬ")) == szkielet(normalizuj("KOBAЛЬ"))                          # В/B, К/K wielkie
    assert szkielet(normalizuj("Коваленко")) == szkielet(normalizuj("Koвaлeнko"))                    # łacina wmieszana w cyrylicę
    assert szkielet(normalizuj("Шевченко")) != szkielet(normalizuj("Shevchenko"))                   # transliteracja to nie homoglif
    assert szkielet("dąbrowski") == "dąbrowski" and zloz_szkielet(normalizuj("Wójсik")) == "wojcik"
    for lac, cyr in CYR_NA_LAC.items():                                                              # tablica generatora ⊂ szkielet
        assert szkielet(normalizuj(lac)) == normalizuj(cyr)


def test_plik_homoglify_naprawione_na_lacine_to_wyciek(tmp_path):
    gold = "Kоwalski Jаn"                                       # cyrylickie „о” i „а”
    ws = [W("p.pelne#1", gold)]
    orig = _docx(tmp_path / "o.docx", f"Umowę podpisał {gold} w imieniu spółki.")
    assert _wycieki(orig, orig, ws) == {"p.pelne#1": "pelny"}
    naprawiony = _docx(tmp_path / "n.docx", "Umowę podpisał Kowalski Jan w imieniu spółki.")
    assert _wycieki(orig, naprawiony, ws) == {"p.pelne#1": "pelny"}
    czesc = _docx(tmp_path / "c.docx", "Umowę podpisał [OSOBA_1] Jan w imieniu spółki.")
    assert _wycieki(orig, czesc, ws) == {"p.pelne#1": "czesciowy"}       # „Jan” (z „Jаn”) – token identyfikujący
    bez_diakr = _docx(tmp_path / "d.docx", "Umowę podpisał KOWALSKI JAN w imieniu spółki.")
    assert _wycieki(orig, bez_diakr, ws) == {"p.pelne#1": "pelny"}
    idealny = _docx(tmp_path / "i.docx", "Umowę podpisał [OSOBA_1] w imieniu spółki.")
    assert _wycieki(orig, idealny, ws) == {}


def test_plik_cyrylica_z_lacina_i_kierunek_odwrotny(tmp_path):
    # wartość cyrylicka z wmieszaną łaciną „naprawiona” na cyrylicę
    gold = homoglify("Олена Коваленко")
    assert gold != "Олена Коваленко"
    ws = [W("p.pelne#1", gold, jezyk="uk")]
    orig = _docx(tmp_path / "o.docx", f"Довіритель: {gold}, м. Київ.")
    assert _wycieki(orig, _docx(tmp_path / "n.docx", "Довіритель: Олена Коваленко, м. Київ."), ws) == {"p.pelne#1": "pelny"}
    # wartość łacińska ASCII, której litery wynik zastąpił cyrylicą o tym samym kształcie
    ws = [W("p.pelne#1", "Jan Kowalski")]
    orig = _docx(tmp_path / "o2.docx", "Umowę podpisał Jan Kowalski osobiście.")
    w = _docx(tmp_path / "w2.docx", "Umowę podpisał Jаn Kоwаlski osobiście.")
    assert _wycieki(orig, w, ws) == {"p.pelne#1": "pelny"}


def test_plik_szkielet_niejednoznaczny_w_oryginale_bez_wariantu(tmp_path):
    """Postać złożona wartości występuje w oryginale częściej niż gold (cytat spraw „Kowalski” – nie gold): wariant w szkielecie
    jest wyłączony z oryginału (wspólnie dla uczestników), ocena dokładna zostaje."""
    gold = "Kоwalski"
    ws = [W("p.nazwisko#1", gold)]
    orig = _docx(tmp_path / "o.docx", f"Pozwany {gold} powołał wyrok w sprawie Kowalski przeciwko Polsce.")
    idealny = _docx(tmp_path / "i.docx", "Pozwany [OSOBA_1] powołał wyrok w sprawie Kowalski przeciwko Polsce.")
    assert _wycieki(orig, idealny, ws) == {}
    zostawiony = _docx(tmp_path / "z.docx", f"Pozwany {gold} powołał wyrok w sprawie [X] przeciwko Polsce.")
    assert _wycieki(orig, zostawiony, ws) == {"p.nazwisko#1": "pelny"}


def test_plik_trzon_bez_cyrylicy_bez_zmian(tmp_path):
    """Bez cyrylicy szkielet jest tożsamością: wartość ASCII nie trafia formy z diakrytykami (jak przed H6a)."""
    ws = [W("p.nazwisko#1", "Dabrowski")]
    orig = _docx(tmp_path / "o.docx", "Pozwany Dabrowski stawił się.")
    assert _wycieki(orig, _docx(tmp_path / "w.docx", "Pozwany Dąbrowski stawił się."), ws) == {}


def test_tekst_homoglify_offsety():
    t = "Umowę podpisał Kоwalski Jаn osobiście."
    s = t.index("K")
    g = [GoldSpan(s, s + len("Kоwalski Jаn"), "p.pelne#1", "OSOBA", "tresc")]
    assert [w[0] for w in ocen_tekst(g, [], t, R).wycieki] == ["p.pelne#1"]       # „normalizujący” bez oznaczenia: wyciek
    assert ocen_tekst(g, [Wykrycie(g[0].start, g[0].end, "OSOBA")], t, R).wycieki == []


class NaprawaHomoglifow(Maskowanie):
    """Uczestnik „normalizujący”: zamienia homoglify cyrylicy na łacinę, niczego nie maskuje."""

    def _zamien(self, w: Wartosc) -> Wartosc:
        return dataclasses.replace(w, tekst="".join(CYR_NA_LAC.get(c, c) for c in w.tekst))


@pytest.fixture(scope="module")
def homoglify_docx(tmp_path_factory):
    cel = tmp_path_factory.mktemp("homoglify")
    return cel, trudne.zbuduj_przypadek(cel, P.HOMOGLIFY, 10, formaty=("docx",))


def test_homoglify_normalizujacy_wycieka_idealny_nie(homoglify_docx, tmp_path):
    cel, wpisy = homoglify_docx
    assert wpisy
    sprawdzone = 0
    for w in wpisy:
        ws = wartosci_wpisu(w)
        z_homoglifami = {x.id for x in ws if "homoglify" in x.cechy}
        orig = cel / w["plik"]
        poz = trudne.PozycjaTrudna(w["id"], w["jezyk"], w["typ"], w["format"], P.HOMOGLIFY)
        for nazwa, uczestnik in (("n", NaprawaHomoglifow()), ("i", Maskowanie())):
            wyj = tmp_path / f"{w['id']}-{nazwa}"
            wyj.mkdir()
            r = trudne.generuj_dokument_trudny(poz, trudne.ZIARNO_TRUDNE, w["split"], wyj, maskuj=uczestnik)
            o = ocen_plik(orig, wyj / r["plik"], ws, leksykon={})
            wyciekle = {x[0] for x in o.wycieki}
            if nazwa == "n":
                pominiete = set(o.niejednoznaczne) | set(o.niewykrywalne)
                assert z_homoglifami - pominiete <= wyciekle, (w["id"], sorted(z_homoglifami - pominiete - wyciekle))
                sprawdzone += len(z_homoglifami - pominiete)
            else:
                assert not o.wycieki, (w["id"], o.wycieki[:3])
    assert sprawdzone >= 10


# ============================================================================= 2. poziom encji
def _wpis_tekstowy(tmp_path: Path, tekst: str, gold: list[tuple[str, str, str, str | None]]) -> dict:
    (tmp_path / "d.txt").write_text(tekst, encoding="utf-8")
    gt = []
    for wid, kat, frag, enc in gold:
        s = tekst.index(frag)
        g = {"start": s, "end": s + len(frag), "wartosc_id": wid, "kategoria": kat, "miejsce": "tresc", "tekst": frag}
        if enc:
            g["encja"] = enc
        gt.append(g)
    return {"id": "d", "jezyk": "pl", "typ": "t", "format": "docx", "plik_txt": "d.txt", "gold_tekst": gt}


def test_encja_wycieka_gdy_wycieka_ktorykolwiek_zapis(tmp_path):
    tekst = "Wykonawca Олена Коваленко (Ołena Kowałenko, Olena Kovalenko) oraz Jan Nowak."
    w = _wpis_tekstowy(tmp_path, tekst, [("p.cyr#1", "OSOBA", "Олена Коваленко", "p"),
                                         ("p.pl#1", "OSOBA", "Ołena Kowałenko", "p"),
                                         ("p.kmu#1", "OSOBA", "Olena Kovalenko", "p"),
                                         ("n.pelne#1", "OSOBA", "Jan Nowak", None)])
    gt = w["gold_tekst"]
    wszystko = [[g["start"], g["end"], "X", 1.0] for g in gt]
    bez_kmu = [x for x, g in zip(wszystko, gt) if g["wartosc_id"] != "p.kmu#1"]
    r = ocen._ocen_tekstowo(w, {"wykrycia": bez_kmu}, tmp_path, Path("brak.md"))
    assert [x[0] for x in r["wycieki"]] == ["p.kmu#1"]
    assert r["wycieki_encji"] == ["p"] and r["encje_ocenione"] == 2           # trzy zapisy = jedna encja; Nowak – własna
    r = ocen._ocen_tekstowo(w, {"wykrycia": wszystko}, tmp_path, Path("brak.md"))
    assert r["wycieki_encji"] == [] and r["encje_ocenione"] == 2
    r = ocen._ocen_tekstowo(w, {"wykrycia": []}, tmp_path, Path("brak.md"))
    assert r["wycieki_encji"] == ["n.pelne#1", "p"]
    trzon = {**w, "gold_tekst": [{k: v for k, v in g.items() if k != "encja"} for g in gt]}
    assert "wycieki_encji" not in ocen._ocen_tekstowo(trzon, {"wykrycia": []}, tmp_path, Path("brak.md"))


def test_encja_poziom_plik(tmp_path):
    orig = _docx(tmp_path / "o.docx", "Wykonawca Олена Коваленко (Olena Kovalenko) podpisał umowę.")
    wyn = _docx(tmp_path / "w.docx", "Wykonawca [OSOBA_1] (Olena Kovalenko) podpisał umowę.")
    gp = [{"id": "p.cyr#1", "kategoria": "OSOBA", "tekst": "Олена Коваленко", "jezyk": "pl", "miejsce": "tresc",
           "waga_klucz": "OSOBA", "encja": "p"},
          {"id": "p.kmu#1", "kategoria": "OSOBA", "tekst": "Olena Kovalenko", "jezyk": "pl", "miejsce": "tresc",
           "waga_klucz": "OSOBA", "encja": "p", "translit": "kmu2010"}]
    w = {"id": "d", "jezyk": "pl", "typ": "t", "format": "docx", "plik": "o.docx", "gold_plik": gp, "gold_obrazy": [],
         "gold_tekst": []}
    (tmp_path / "manifest.jsonl").write_text(json.dumps(w, ensure_ascii=False) + "\n", encoding="utf-8")
    r = ocen._ocen_plikowo(w, {"plik_wyj": "w.docx"}, tmp_path, tmp_path, Path("brak.md"), tmp_path / "manifest.jsonl")
    assert [x[0] for x in r["wycieki"]] == ["p.kmu#1"] and r["wycieki_encji"] == ["p"] and r["encje_ocenione"] == 1


# ============================================================================= 3. inicjały
def test_wzor_inicjalow_granice():
    n = normalizuj
    assert wzor_inicjalow("J.K.").search(n("Opracował: J.K.; zatwierdził: A.B."))
    assert wzor_inicjalow("J.K.").search(n("J. K."))
    assert not wzor_inicjalow("J.K.").search(n("J.K.M."))
    assert not wzor_inicjalow("JK").search(n("AJK, JKL, MJKA"))
    assert wzor_inicjalow("jk").search(n("Oznaczenie: jk/ak")) and wzor_inicjalow("AB").search(n("/AB/"))
    assert not wzor_inicjalow("K.").search(n("art. 415 k.c.")) and wzor_inicjalow("K.").search(n("Pan K. wyszedł."))


def test_tekst_inicjaly_jak_identyfikator_prog_dlugosc():
    assert "INICJALY" not in KATEGORIE_ID
    t = "Opracował: J.K.; Pan K. przyszedł."
    jk, k = t.index("J.K."), t.index("K. p")
    g = [GoldSpan(jk, jk + 4, "a.ini#1", "INICJALY", "stopka"), GoldSpan(k, k + 2, "a.inicjal#1", "INICJALY", "tresc")]
    o = ocen_tekst(g, [], t, R)
    assert [(x[0], x[3]) for x in o.wycieki] == [("a.ini#1", "pelny"), ("a.inicjal#1", "pelny")] and o.wartosci_ocenione == 2
    pokryte = [Wykrycie(jk, jk + 4, "X"), Wykrycie(k, k + 2, "X")]
    assert ocen_tekst(g, pokryte, t, R).wycieki == []
    tylko_j = [Wykrycie(jk, jk + 1, "X"), Wykrycie(k, k + 1, "X")]
    assert ocen_tekst(g, tylko_j, t, R).wycieki == []            # „K” odsłonięte samo: 1 < 2 znaków progu


def test_plik_parafa_zostawiona_wycieka_zamaskowana_nie(tmp_path):
    ws = [W("a.inicjaly#1", "J.K.", "INICJALY"), W("b.inicjaly#1", "AB", "INICJALY"), W("c.inicjal#1", "N.", "INICJALY")]
    tlo = "Spółka AJK i JKL; art. 415 k.c.; ABC-1; ABN."
    orig = _docx(tmp_path / "o.docx", "Opracował: J.K.", "Paraf: /AB/", "Pan N. się nie stawił.", tlo)
    assert _wycieki(orig, orig, ws) == {"a.inicjaly#1": "pelny", "b.inicjaly#1": "pelny", "c.inicjal#1": "pelny"}
    zam = _docx(tmp_path / "z.docx", "Opracował: [INICJALY_1]", "Paraf: /[INICJALY_2]/", "Pan [INICJALY_3] się nie stawił.", tlo)
    assert _wycieki(orig, zam, ws) == {}                          # brak fałszywych trafień z „AJK”, „JKL”, „k.c.”, „ABC”
    czesc = _docx(tmp_path / "c.docx", "Opracował: J. K.", "Paraf: /[X]/", "Pan [X] się nie stawił.", tlo)
    assert _wycieki(orig, czesc, ws) == {"a.inicjaly#1": "pelny"}


def test_plik_inicjaly_niejednoznaczne_wzorcem(tmp_path):
    """Wzorzec inicjałów poza gold w oryginale („Pan N.” i „N.” poza gold) – wartość wyłączona dla wszystkich; „K.” w „J.K.”
    tej samej osoby (gold) nie czyni „Pan K.” niejednoznacznym."""
    ws = [W("c.inicjal#1", "N.", "INICJALY"), W("a.ini#1", "J.K.", "INICJALY"), W("a.inicjal#1", "K.", "INICJALY")]
    orig = _docx(tmp_path / "o.docx", "Pan N. się nie stawił, bo N. wyjechał.", "Opracował: J.K.", "Pan K. przyszedł.")
    o = ocen_plik(orig, orig, ws, leksykon={})
    assert o.niejednoznaczne == ["c.inicjal#1"] and {x[0] for x in o.wycieki} == {"a.ini#1", "a.inicjal#1"}


def _dok(*fragmenty) -> Dokument:
    d = Dokument("x", "pl", "t", "txt")
    d.elementy = [Element("akapit", list(fragmenty))]
    return d


def test_inicjaly_jednoznaczne_generatora():
    ini = lambda t, e="a": Wartosc(f"{e}.inicjaly#1", "INICJALY", t, "pl", "tresc", "INICJALY", encja=e)
    assert inicjaly_jednoznaczne(_dok("Paraf: ", ini("JK"), "."))
    assert not inicjaly_jednoznaczne(_dok("Paraf: ", ini("JK"), ", a także jk w tekście."))
    assert not inicjaly_jednoznaczne(_dok("art. 415 k.c.; Pan ", ini("C."), " przyszedł."))
    assert inicjaly_jednoznaczne(_dok("Opracował ", ini("J.K."), "; Pan ", ini("K."), "."))          # ta sama osoba
    assert not inicjaly_jednoznaczne(_dok("Opracował ", ini("J.K."), "; Pani ", ini("K.", "b"), "."))  # różne osoby


@pytest.mark.parametrize("przypadek,generatory", [(P.PARAFY, trudne_jezyk.GENERATORY), (P.SKROTY_PO_PELNYM,
                                                                                      trudne_dlugie.GENERATORY)])
def test_generatory_inicjalow_jednoznaczne(przypadek, generatory):
    for (jezyk, typ), gen in sorted(generatory[przypadek].items()):
        for seed in range(6):
            wynik = gen(jezyk, typ, 1000 + seed)
            assert inicjaly_jednoznaczne(wynik[0].dokument), (jezyk, seed)
            assert any(not isinstance(f, str) and f.kategoria == "INICJALY"
                       for e in wynik[0].dokument.elementy for f in e.fragmenty)


# ============================================================================= 4. ukraiński w uruchamianiu
def test_jezyk_uzyty_regula_zastepcza():
    assert "uk" in uruchom.JEZYKI
    assert uruchom.jezyk_uzyty("pl", ("pl", "en")) == "pl"
    assert uruchom.jezyk_uzyty("uk", ("pl", "en", "es", "de", "fr")) == "pl"
    assert uruchom.jezyk_uzyty("uk", ("en", "fr")) == "en" and uruchom.jezyk_uzyty("uk", ("fr",)) == "fr"
    assert uruchom.jezyk_uzyty("uk", ("uk", "pl")) == "uk"
    assert uruchom.jezyk_uzyty("de", ("pl",)) is None


def test_uruchom_dokument_uk_z_jezykiem_zastepczym(tmp_path, monkeypatch):
    from test_uruchom import surowe, uruchom_atrape, wg_id, zrob_srodowisko
    sr = zrob_srodowisko(tmp_path)
    wpisy = [json.loads(l) for l in sr["manifest"].read_text(encoding="utf-8").splitlines()]
    tekst = "Олена Коваленко мешкає у Києві."
    (sr["korpus"] / "uk-a-0001.txt").write_text(tekst, encoding="utf-8")
    wpisy.append({"id": "uk-a-0001", "jezyk": "uk", "typ": "pozew", "format": "docx", "split": "dev", "plik": "uk-a-0001.docx",
                  "plik_txt": "uk-a-0001.txt", "gold_tekst": [{"start": 0, "end": 15, "wartosc_id": "w0#1", "kategoria": "OSOBA",
                                                               "miejsce": "tresc", "tekst": tekst[:15]}],
                  "gold_plik": [], "gold_obrazy": [], "ostrzezenia": []})
    sr["manifest"].write_text("\n".join(json.dumps(w, ensure_ascii=False) for w in wpisy) + "\n", encoding="utf-8")
    toml = 'poziomy = ["tekst"]\njezyki = ["en", "pl"]\nformaty = ["docx"]\nprocesy = 1\ntimeout_s = 60\n'
    assert uruchom_atrape(sr, monkeypatch, toml=toml, argv=("--jezyki", "uk,de")) == 0
    rek = wg_id(surowe(sr))
    assert rek["uk-a-0001"]["jezyk"] == "uk" and rek["uk-a-0001"]["jezyk_uzyty"] == "pl" and "wykrycia" in rek["uk-a-0001"]
    assert rek["de-a-0001"] == {"id": "de-a-0001", "pominiety": "jezyk"}
    o = ocen._ocen_dokument(("tekst", wpisy[-1], rek["uk-a-0001"], str(sr["korpus"]), str(tmp_path), str(tmp_path / "brak.md"),
                             str(sr["manifest"]), None, None))
    assert o["jezyk_uzyty"] == "pl" and o["w_zakresie_oficjalnym"] is True


# ============================================================================= 5. H5 m1/m2
def test_nieprzerwane_zachowuje_nieocenione_z_oryginalu():
    k = [{"id": "k1", "rodzaj": P.POSREDNIE_FUNKCJA_FIRMA, "skladniki": [{"id": "k1.a", "rola": "funkcja"}, {"id": "k1.b", "rola": "firma"}]},
         {"id": "k2", "rodzaj": P.POSREDNIE_DZIALKA_GPS, "skladniki": [{"id": "k2.gps", "rola": "gps"}]}]
    assert [x["przerwana"] for x in posrednie.nieprzerwane(k)] == [False, False]
    oryg = [{"id": "k1", "przerwana": None}, {"id": "k2", "przerwana": False}]
    n = posrednie.nieprzerwane(k, oryg)
    assert [x["przerwana"] for x in n] == [None, False] and n[1]["rola"] == "gps" and "rola" not in n[0]
    a = posrednie.agreguj([{"jezyk": "pl", "blad_sedziego": "x", "posrednie": n}])
    assert a["ogolem"]["kombinacje"] == 1 and a["nieocenione"] == 1


def test_blad_sedziego_nieocenione_poza_mianownikiem(tmp_path, monkeypatch):
    """m1: kombinacja nieoceniona z oryginału (składnik bez liczącej się jednostki) nie wchodzi do mianownika u uczestnika
    z błędem sędziego – tak jak u pozostałych."""
    tekst = "Kierownik zm. firmy Delta sp. z o.o. przyszedł."
    w = _wpis_tekstowy(tmp_path, tekst, [("f.nazwa#1", "ORGANIZACJA", "Delta sp. z o.o.", None)])
    w["posrednie"] = [{"id": "k1", "rodzaj": P.POSREDNIE_FUNKCJA_FIRMA, "skladniki": [
        {"id": "k1.funkcja", "rola": "funkcja", "tekst": "zm.", "miejsce": "tresc", "wartosc_id": None, "rdzen": ["zm."]},
        {"id": "k1.firma", "rola": "firma", "tekst": "Delta sp. z o.o.", "miejsce": "tresc", "wartosc_id": "f.nazwa#1",
         "rdzen": ["Delta sp. z o.o."]}]}]
    arg = ("tekst", w, {"wykrycia": [[0, 5, "X", 1.0]]}, str(tmp_path), str(tmp_path), str(tmp_path / "brak.md"),
           str(tmp_path / "m.jsonl"), None, None)
    zwykly = ocen._ocen_dokument(arg)
    assert zwykly["posrednie"][0]["przerwana"] is None
    prawdziwa = ocen.ocen_tekst
    monkeypatch.setattr(ocen, "ocen_tekst", lambda gold, wykr, *a, **k: (_ for _ in ()).throw(RuntimeError("x")) if wykr
                        else prawdziwa(gold, wykr, *a, **k))
    blad = ocen._ocen_dokument(arg)
    assert "blad_sedziego" in blad and blad["posrednie"][0]["przerwana"] is None
    a = posrednie.agreguj([blad, zwykly])
    assert a["ogolem"]["kombinacje"] == 0 and a["nieocenione"] == 2


def test_agreguj_dzialka_i_gps_osobno():
    dg = P.POSREDNIE_DZIALKA_GPS
    rek = [{"jezyk": "pl", "posrednie": [{"id": "k1", "rodzaj": dg, "przerwana": True, "widoczne": [], "rola": "dzialka"},
                                         {"id": "k2", "rodzaj": dg, "przerwana": False, "widoczne": ["k2.gps"], "rola": "gps"}]}
           for _ in range(4)]
    a = posrednie.agreguj(rek)
    assert a["rodzaje"][dg]["odsetek"] == 0.5
    assert a["podrodzaje"][dg]["dzialka"]["odsetek"] == 1.0 and a["podrodzaje"][dg]["gps"]["odsetek"] == 0.0
    assert a["podrodzaje"][dg]["gps"]["kombinacje"] == 4
    bez = posrednie.agreguj([{"jezyk": "pl", "posrednie": [{**k, "rola": None} for k in rek[0]["posrednie"]]}])
    assert bez["podrodzaje"] == {}
    stare = posrednie.agreguj(rek)                                 # przedziały pozostałych miar bez zmian (kolejność losowań)
    assert {k: v for k, v in stare.items() if k != "podrodzaje"} == {k: v for k, v in a.items() if k != "podrodzaje"}


def test_rekord_kombinacji_jednoskladnikowej_ma_role():
    k = {"id": "k2", "rodzaj": P.POSREDNIE_DZIALKA_GPS, "skladniki": [{"id": "k2.gps", "rola": "gps"}]}
    assert posrednie.ocena_kombinacji(k, True, []) == {"id": "k2", "rodzaj": P.POSREDNIE_DZIALKA_GPS, "przerwana": True,
                                                       "widoczne": [], "rola": "gps"}


# ============================================================================= 6. gramatyka wariantów H2
def test_formy_rodzinne_pl():
    f = trudne_jezyk.forma_rodzinna
    assert [f("Kowalski", p) for p in ("mian", "dop", "cel", "bier", "narz", "msc")] == \
        ["Kowalscy", "Kowalskich", "Kowalskim", "Kowalskich", "Kowalskimi", "Kowalskich"]
    assert [f("Wysocki", p) for p in ("mian", "dop", "narz")] == ["Wysoccy", "Wysockich", "Wysockimi"]
    assert [f("Nowak", p) for p in ("mian", "dop", "cel", "bier", "narz", "msc")] == \
        ["Nowakowie", "Nowaków", "Nowakom", "Nowaków", "Nowakami", "Nowakach"]
    assert f("Król", "mian") == "Królowie" and trudne_jezyk.nazwisko_zenskie("Wysocki") == "Wysocka"


#: Przyimek przed gniazdem nazwiska -> przypadek, którego wymaga (PL). „o” + miejscownik (mowa o…, wspominać o…); czasowniki
#: z „o” + biernikiem („pytać o”, „prosić o”) nie mogą stać w ramie miejscownika.
_RZAD_PL = {"u": {"dop"}, "z": {"narz"}, "o": {"msc"}, "do": {"dop"}}
_O_Z_BIERNIKIEM = re.compile(r"\b(pyta\w*|prosi\w*|dba\w*|walczy\w*)\s+o\s+\{", re.IGNORECASE)


@pytest.mark.parametrize("ramki", ["rodzina", "pojedyncze"])
def test_ramki_przypadkow_pl_rzad_przyimkow(ramki):
    if ramki == "rodzina":
        pary = [(p, r) for p, rr in trudne_jezyk._RAMKI_RODZINY.items() for r in rr]
    else:
        pary = [(p, r) for plec in trudne_jezyk._RAMKI_POJEDYNCZE.values() for p, rr in plec.items() for r in rr]
    for przyp, rama in pary:
        assert not _O_Z_BIERNIKIEM.search(rama), rama
        for m in re.finditer(r"\b(\w+)\s+(?:\{P\}\s+)?\{[FX]\}", rama):
            przyimek = m.group(1).lower()
            if przyimek in _RZAD_PL:
                assert przyp in _RZAD_PL[przyimek], (przyp, rama)


def test_odmiana_nazwisk_dokument_pl_bez_bledow_rzadu():
    for seed in range(8):
        for typ in ("notatka_rodzina", "protokol_spotkania"):
            wynik = trudne_jezyk.GENERATORY[P.ODMIANA_NAZWISK][("pl", typ)]("pl", typ, seed)[0]
            tekst = "\n".join("".join(f if isinstance(f, str) else f.tekst for f in e.fragmenty) for e in wynik.dokument.elementy)
            assert not re.search(r"pytali o \w+ach\b", tekst) and "Państw" in tekst


@pytest.mark.parametrize("jezyk,etykieta,forma_k", [("pl", "rozmówczyni", "zgodziła się"), ("de", "Anruferin", None),
                                                     ("es", "interlocutora", "La señora"), ("fr", "interlocutrice", None)])
def test_zdrobnienia_rodzaj_gramatyczny(jezyk, etykieta, forma_k):
    """Pierwsza osoba notatki to kobieta (pula żeńska), druga – mężczyzna: etykieta rozmówcy i formy czasowników zgodne z płcią;
    zdrobnienie z tej samej puli co imię pełne."""
    gen = trudne_jezyk.GENERATORY[P.ZDROBNIENIA][(jezyk, "notatka_rozmowy")]
    pule = {pelne: dims for pelne, _, dims in trudne_jezyk.ZDROBNIENIA_IMION[jezyk]}
    for seed in range(5):
        wynik = gen(jezyk, "notatka_rozmowy", seed)[0]
        tekst = "\n".join("".join(f if isinstance(f, str) else f.tekst for f in e.fragmenty) for e in wynik.dokument.elementy)
        assert f"{etykieta} – " in tekst, tekst[:200]
        if forma_k:
            assert forma_k in tekst
        wartosci = [f for e in wynik.dokument.elementy for f in e.fragmenty if not isinstance(f, str) and f.kategoria == "OSOBA"]
        pelne = {f.encja: f.tekst.split()[0] for f in wartosci if f.id.endswith(".pelne#1")}
        zdrob = [f for f in wartosci if "zdrobnienie" in f.cechy]
        assert zdrob and all(f.tekst.split()[0] in pule[pelne[f.encja]] for f in zdrob)


def test_skroty_de_honoryfikat_w_przypadku_zaleznym():
    """DE: „Herrn” w dopełniaczu/celowniku/bierniku mężczyzny, „Frau” u kobiety; PL: „Pana”/„Panu” zgodnie z przypadkiem."""
    gen, ctx = trudne_dlugie.nowy_kontekst("de", 3)
    a, b = trudne_dlugie._para_stron(gen, ctx, "de")
    for przyp in ("dat", "akk"):
        przed, g = trudne_dlugie._odniesienie("de", a, "RA", "pan_inicjal", przyp, "")
        assert przed == "Herrn " and g.kategoria == "INICJALY" and re.fullmatch(r"\w\.", g.tekst)
    przed, _ = trudne_dlugie._odniesienie("de", b, "RB", "pan_inicjal", "akk", "")
    assert przed == "Frau "
    gen, ctx = trudne_dlugie.nowy_kontekst("pl", 3)
    a, _ = trudne_dlugie._para_stron(gen, ctx, "pl")
    assert trudne_dlugie._odniesienie("pl", a, "RA", "pan_inicjal", "cel", "")[0] == "Panu "
    assert trudne_dlugie._odniesienie("pl", a, "RA", "pan_inicjal", "dop", "")[0] == "Pana "


# ============================================================================= poprawki H6a – runda 1
def test_inicjaly_jednoznaczne_licza_jak_sedzia_przez_honoryfikat():
    """I1: honoryfikat spoza gold („M.”) i inicjał gold („L.”) dają „M. L.” – wzorzec inicjałów „M.L.” tej samej osoby trafia
    w całym tekście częściej niż w tekstach gold (tak liczy sędzia `niejednoznaczne`), więc dokument jest losowany od nowa."""
    ini = lambda t, e="a", i=1: Wartosc(f"{e}.inicjaly#{i}", "INICJALY", t, "fr", "tresc", "INICJALY", encja=e)
    assert not inicjaly_jednoznaczne(_dok("Selon ", ini("M.L."), ", M. ", ini("L.", i=2), " était présent."))
    assert not inicjaly_jednoznaczne(_dok("D. ", ini("G.", i=2), " y ", ini("D.G."), " firmaron."))
    assert inicjaly_jednoznaczne(_dok("Selon ", ini("M.L."), ", Mme ", ini("L.", i=2), " était présente."))


@pytest.fixture(scope="module")
def skroty_docx(tmp_path_factory):
    cel = tmp_path_factory.mktemp("skroty")
    return cel, trudne.zbuduj_przypadek(cel, P.SKROTY_PO_PELNYM, 60, formaty=("docx",))


def test_skroty_es_fr_bez_inicjalow_niejednoznacznych(skroty_docx):
    """I1: próbka recenzenta (`skroty_po_pelnym` docx, 60 pozycji, ES/FR) – przed poprawką 19/568 wartości INICJALY wyłączonych
    jako niejednoznaczne (honoryfikaty FR „M.”, ES „D.”); po – żadnej, a wszystkie inicjały kopii oryginału wyciekają."""
    cel, wpisy = skroty_docx
    sprawdzone = 0
    for w in wpisy:
        if w["jezyk"] not in ("es", "fr"):
            continue
        ws = wartosci_wpisu(w)
        ini = {x.id for x in ws if x.kategoria == "INICJALY"}
        o = ocen_plik(cel / w["plik"], cel / w["plik"], ws, leksykon={})
        assert not ini & set(o.niejednoznaczne), w["id"]
        assert ini <= {x[0] for x in o.wycieki}, w["id"]
        sprawdzone += len(ini)
    assert sprawdzone > 300


def test_ocr_inicjaly_wymagaja_potwierdzenia_innym_odczytem():
    """I2: trafienie wzorca inicjałów w JEDNYM odczycie strony (szum OCR: gwiazdki czytane jako „ar”) nie jest wyciekiem –
    strona trafia do niepotwierdzonych (wywołujący dokłada odczyt); wzorzec w dwóch odczytach (inna rozdzielczość, inny tryb)
    – jest. Nazwisko (pełne, token dokładny) – jak dotąd z jednego odczytu."""
    from pbench.sedzia import plik as sedzia_plik
    w = W("c.inicjaly_male#1", "ar", "INICJALY", jezyk="es")
    reg = sedzia_plik.zbuduj_regule(w, R, set(), [])
    reg_ocr = sedzia_plik.zbuduj_regule(w, R, set(), [], ocr=True)
    g = sedzia_plik._Grupa([w], reg, None, reg_ocr, None, True)
    Ocr = sedzia_plik._Ocr
    assert sedzia_plik._trafienia_ocr(g, [[Ocr("strona 1", "ns an 1 aaa ar aro oroor")]]) == ([], {0})
    assert sedzia_plik._trafienia_ocr(g, [[Ocr("strona 1", "ns an ar")], [Ocr("strona 1 (400)", "oo ar")]])[0]
    assert sedzia_plik._trafienia_ocr(g, [[Ocr("strona 1", "ns an ar\foo ar")]])[0]               # dwa odczyty jednej strony
    assert sedzia_plik._trafienia_ocr(g, [[Ocr("strona 1", "ns an\for")]]) == ([], set())
    n = W("p.nazwisko#1", "Kowalski")
    gn = sedzia_plik._Grupa([n], sedzia_plik.zbuduj_regule(n, R, set(), []), None,
                            sedzia_plik.zbuduj_regule(n, R, set(), [], ocr=True), None, True)
    assert sedzia_plik._trafienia_ocr(gn, [[Ocr("strona 1", "pan kowalski")]])[0]


def test_ocr_inicjaly_bez_wierszy_szumu():
    """Inicjały w OCR obrazu osadzonego: wiersz z ≥ `MIN_SLOW_SZUMU` tokenami szumu (≥ 3 liter, same wielkie litery, nie z jednej
    powtórzonej litery) i bez słowa dokumentu (gwiazdki czytane w każdym odczycie jako „… ERRE ERE ARRE RR AR”) nie potwierdza
    inicjałów; wiersz z etykietą z tekstu dokumentu (także odczytaną bez znaków diakrytycznych), krótki, z zamiennikami pisanymi
    zwykle albo z maską z jednej litery – potwierdza. Usunięty wiersz szumu nie skleja „J.” i „K.” w „J.K.”. Strony PDF i grupa bez
    słownika (`slownik=None`) – bez tego warunku."""
    from pbench.sedzia import plik as sedzia_plik
    Ocr = sedzia_plik._Ocr

    def grupa(tekst: str, slownik) -> "sedzia_plik._Grupa":
        w = W("a.inicjaly#1", tekst, "INICJALY", jezyk="es")
        return sedzia_plik._Grupa([w], sedzia_plik.zbuduj_regule(w, R, set(), []), None,
                                  sedzia_plik.zbuduj_regule(w, R, set(), [], ocr=True), None, True, slownik=slownik)
    slownik = frozenset({"referencia", "elaborado", "por", "rubrica", "ar", "j", "k"})
    g = grupa("ar", slownik)

    def traf(g, *odczyty: str, osadzone: bool = True):
        return sedzia_plik._trafienia_ocr(g, [[Ocr("logo", "\f".join(odczyty), (6, 11) if osadzone else ())]], osadzone)[0]
    szum = "A ARAHAL AC AE AA AE AE AE AEREA AE ERRE ERE ARRE RR AR"
    assert not traf(g, szum, szum)
    assert traf(g, szum, szum, osadzone=False)                                              # strony PDF – bez warunku
    assert traf(g, f"{szum}\nReferencia: ar/jc", f"{szum}\nReferencia: ar/jc")
    assert traf(g, "ar", "AR")                                                              # sama parafa
    assert traf(g, "RUBRICA AEREA ERRE ARRE AR", "RUBRICA AEREA ERRE ARRE AR")              # „Rúbrica” bez diakrytyków
    assert traf(g, "XXXX XXXXX XXXXX XXXX AR", "XXXX XXXXX XXXXX XXXX AR")                  # maska z jednej litery
    for zamienniki in ("Martínez Herrera Abogados Asociados ar", "MARTÍNEZ HERRERA ABOGADOS ASOCIADOS ar"):
        assert traf(g, zamienniki, zamienniki)                                              # wielkimi: 15 różnych liter
    assert traf(grupa("ar", None), szum, szum)
    gjk = grupa("J.K.", slownik)
    assert not traf(gjk, f"J.\n{szum}\nK.", f"J.\n{szum}\nK.")                              # bez sklejenia przez usunięty wiersz
    assert traf(gjk, "J.\nK.", "J.\nK.")
    assert traf(gjk, f"J.\nK.\n{szum}", f"J.\nK.\n{szum}")                                  # szum w innym miejscu odczytu


def _wiersz_z_parafa_png(tekst: str, px: int = 40) -> "Image.Image":
    """Obraz wiersza tekstu (DejaVu Sans, `px` pikseli) na białym tle."""
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", px)
    szer = int(ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(tekst, font=font)) + 2 * px
    im = Image.new("RGB", (szer, 2 * px), "white")
    ImageDraw.Draw(im).text((px, px // 3), tekst, font=font, fill=(0, 0, 0))
    return im


@pytest.mark.parametrize("wiersz", ["XXXX XXXXX XXXXX XXXX A.R.", "Martínez Herrera Abogados Asociados A.R.",
                                    "MARTÍNEZ HERRERA ABOGADOS ASOCIADOS A.R."],
                         ids=["maska_x", "zamienniki", "zamienniki_wielkie"])
def test_parafa_w_pikselach_obok_maski_i_zamiennikow_wycieka(wiersz, tmp_path):
    """Reguła wierszy szumu (`plik._bez_szumu`) nie zabiera prawdziwej parafy: parafa „A.R.” w jednym wierszu OCR z maską z X-ów
    albo z czterema zamiennikami spoza oryginału (wielkość liter mieszana albo same wielkie litery) wycieka – z obrazu osadzonego DOCX (jedyna droga
    w pikselach) i ze strony zrasteryzowanej PDF (OCR strony i obrazu strony)."""
    import io
    from reportlab.pdfgen import canvas
    ws = [W("a.inicjaly_kropki#1", "A.R.", "INICJALY", jezyk="es")]
    org = _docx(tmp_path / "o.docx", "Escrito elaborado por Lucía Gómez Ortega A.R.", "Madrid, a 3 de marzo.")
    d = Document()
    d.add_paragraph("Escrito elaborado por [OSOBA_1] [INICJALY_1].")
    b = io.BytesIO()
    _wiersz_z_parafa_png(wiersz).save(b, "PNG")
    d.add_picture(io.BytesIO(b.getvalue()))
    d.save(tmp_path / "w.docx")
    assert [x[0] for x in ocen_plik(org, tmp_path / "w.docx", ws, leksykon={}).wycieki] == ["a.inicjaly_kropki#1"]
    c = canvas.Canvas(str(tmp_path / "o.pdf"))
    c.drawString(72, 760, "Escrito elaborado por Lucía Gómez Ortega A.R.")
    c.drawString(72, 740, "Madrid, a 3 de marzo.")
    c.save()
    strona = _raster(tmp_path / "o.pdf", dpi=200)[0]
    d2 = __import__("PIL.ImageDraw", fromlist=["ImageDraw"]).Draw(strona)
    d2.rectangle([150, 160, 1600, 240], fill="white")                                     # tekst oryginału zakryty
    strona.paste(_wiersz_z_parafa_png(wiersz, 36), (190, 160))
    wynik = _pdf_z_obrazow([strona], tmp_path / "w.pdf")
    assert [x[0] for x in ocen_plik(tmp_path / "o.pdf", wynik, ws, leksykon={}).wycieki] == ["a.inicjaly_kropki#1"]


def _czytelne_parafy(ws) -> set[str]:
    """Id parafek, które OCR odróżnia od kresek: z liter innych niż „i” (parafa „II”, „I.I.” to same pionowe kreski – odczyt
    myli je z „l”, „1”, „|”, a identyczne wartości sędzia numeruje kolejno, więc drugiej „II” nie potwierdza)."""
    return {x.id for x in ws if x.kategoria == "INICJALY" and set(re.sub(r"\W", "", x.tekst.lower())) - {"i"}}


@pytest.fixture(scope="module")
def parafa_es_pdf(tmp_path_factory):
    """`h-pf-es-pismo_z_parafami-0003` (PDF, parafa „ar”): oryginał, uczestnik maskujący gwiazdkami i kopia zrasteryzowana."""
    from pbench.sedzia.sanity import zrasteryzuj
    cel = tmp_path_factory.mktemp("parafy_pdf")
    poz = trudne.PozycjaTrudna("h-pf-es-pismo_z_parafami-0003", "es", "pismo_z_parafami", "pdf", P.PARAFY)
    wpis = trudne.generuj_dokument_trudny(poz, trudne.ZIARNO_TRUDNE, "test", cel / "o")
    gw = trudne.generuj_dokument_trudny(poz, trudne.ZIARNO_TRUDNE, "test", cel / "g", maskuj=Gwiazdki())
    orig = cel / "o" / wpis["plik"]
    zrasteryzuj(orig, cel / "raster.pdf")
    return orig, cel / "g" / gw["plik"], cel / "raster.pdf", wartosci_wpisu(wpis)


class Gwiazdki(Maskowanie):
    """Uczestnik zamieniający każdą wartość na gwiazdki tej samej długości (częsty styl redakcji)."""

    def _zamien(self, w: Wartosc) -> Wartosc:
        return dataclasses.replace(w, tekst="*" * max(1, len(w.tekst)))


def test_pdf_parafy_gwiazdki_bez_falszywych_wyciekow_raster_wycieka(parafa_es_pdf):
    """I2 (odtworzenie recenzenta): gwiazdki w PDF czytane przez OCR strony jako „… ar …” (w każdym odczycie: 300 i 400 dpi,
    psm 3 i 6) i logo zastąpione wierszem gwiazdek (obraz osadzony, w każdym odczycie „… ERRE ERE ARRE RR AR”) – 0 wycieków: strona
    ma warstwę tekstową, więc inicjały czyta OCR renderu bez obiektów tekstowych (gwiazdek tekstu w nim nie ma), a wiersz gwiazdek
    logo jest wierszem szumu (`plik._bez_szumu`); prawdziwe parafy w rastrze (kopia zrasteryzowana – tekst tylko w pikselach,
    czytany w dwóch odczytach i po wybieleniu pól) wyciekają wszystkie czytelne (`_czytelne_parafy`)."""
    orig, gw, raster, ws = parafa_es_pdf
    ini = _czytelne_parafy(ws)
    assert ini and any(x.tekst == "ar" for x in ws if x.kategoria == "INICJALY")
    assert ocen_plik(orig, gw, ws, leksykon={}).wycieki == []
    r = ocen_plik(orig, raster, ws, leksykon={})
    assert ini <= {x[0] for x in r.wycieki}


def _parafy_pdf(cel: Path, id_: str) -> tuple[Path, Path, list[Wartosc]]:
    """Dokument `parafy` (PDF) `id_`: oryginał, wynik uczestnika nawiasowego (warstwa tekstowa z „[INICJALY_n]” zamiast wartości)
    i gold."""
    poz = trudne.PozycjaTrudna(id_, id_.split("-")[2], "pismo_z_parafami", "pdf", P.PARAFY)
    wpis = trudne.generuj_dokument_trudny(poz, trudne.ZIARNO_TRUDNE, "test", cel / "o")
    naw = trudne.generuj_dokument_trudny(poz, trudne.ZIARNO_TRUDNE, "test", cel / "n", maskuj=Maskowanie())
    return cel / "o" / wpis["plik"], cel / "n" / naw["plik"], wartosci_wpisu(wpis)


def _pola_wartosci(pdf: Path, teksty: set[str], na_znak: bool) -> list[list[tuple[float, float, float, float]]]:
    """Pola (punkty PDF: lewo, dół, prawo, góra) każdego wystąpienia każdego z `teksty` na kolejnych stronach – jedno na znak
    (`na_znak`) albo jedno na wystąpienie (suma pól znaków w pełnej wysokości wiersza)."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(pdf))
    wynik = []
    for i in range(len(doc)):
        tp = doc[i].get_textpage()
        pola = []
        for t in sorted(teksty):
            s = tp.search(t, match_case=True, match_whole_word=False)
            while (r := s.get_next()) is not None:
                znaki = [b for c in range(r[0], r[0] + r[1]) if (b := tp.get_charbox(c, loose=not na_znak))[2] > b[0]]
                if na_znak:
                    pola += znaki
                elif znaki:
                    pola.append((min(b[0] for b in znaki), min(b[1] for b in znaki), max(b[2] for b in znaki),
                                 max(b[3] for b in znaki)))
            s.close()
        tp.close()
        wynik.append(pola)
    doc.close()
    return wynik


def _raster(pdf: Path, rysuj=None, dpi: int = 200) -> list:
    """Strony `pdf` jako obrazy RGB (`dpi`); `rysuj(strona, obraz, skala, wysokosc_pt)` dorysowuje na nich (redakcja rastrowa)."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(pdf))
    obrazy_stron = []
    for i in range(len(doc)):
        im = doc[i].render(scale=dpi / 72).to_pil().convert("RGB")
        if rysuj is not None:
            rysuj(i, im, dpi / 72, doc[i].get_height())
        obrazy_stron.append(im)
    doc.close()
    return obrazy_stron


def _pdf_z_obrazow(obrazy_stron: list, cel: Path, warstwa: Path | None = None) -> Path:
    """PDF ze stron-obrazów (200 dpi); z `warstwa` – obraz strony (XObject, JPEG) pod niewidoczną (tryb 3) warstwą tekstową PDF-u
    `warstwa` (jak redakcja rastrowa, która zostawia tekst wyniku do kopiowania). Plik powtarzalny bajtowo (stałe daty
    i identyfikator) – OCR stron trafia w pamięć podręczną przy kolejnym uruchomieniu."""
    import io
    import time
    import pikepdf
    if warstwa is None:
        obrazy_stron[0].save(cel, save_all=True, append_images=obrazy_stron[1:], resolution=200, creationDate=time.gmtime(0),
                             modDate=time.gmtime(0))
        return cel
    pdf = pikepdf.open(warstwa)
    for im, strona in zip(obrazy_stron, pdf.pages):
        bufor = io.BytesIO()
        im.save(bufor, "JPEG", quality=85)
        obraz = pikepdf.Stream(pdf, bufor.getvalue(), Type=pikepdf.Name.XObject, Subtype=pikepdf.Name.Image, Width=im.width,
                               Height=im.height, ColorSpace=pikepdf.Name.DeviceRGB, BitsPerComponent=8,
                               Filter=pikepdf.Name.DCTDecode)
        strona.add_resource(obraz, pikepdf.Name.XObject, pikepdf.Name("/Strona"))
        x0, y0, x1, y1 = (float(v) for v in strona.mediabox)
        strona.contents_add(pdf.make_stream(f"q {x1 - x0:.2f} 0 0 {y1 - y0:.2f} {x0:.2f} {y0:.2f} cm /Strona Do Q 3 Tr\n"
                                            .encode()), prepend=True)
    pdf.save(cel, deterministic_id=True)
    pdf.close()
    return cel


def _czarne_pola(pola: list[list[tuple]], margines: float):
    from PIL import ImageDraw

    def rysuj(i, im, k, h):
        d = ImageDraw.Draw(im)
        for x0, y0, x1, y1 in pola[i]:
            d.rectangle([x0 * k - margines, (h - y1) * k - margines, x1 * k + margines, (h - y0) * k + margines], fill=(0, 0, 0))
    return rysuj


def test_bez_pol_wybiela_pola_zostawia_pismo_i_ramke():
    """I-R1 (`obrazy.bez_pol`): czarne pole (redakcja) staje się białe razem z wygładzoną krawędzią; pismo (także pogrubione,
    kolorowe), cienka kolorowa ramka pieczątki i jasne tło pieczątki zostają bez zmian."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    from pbench.sedzia import obrazy
    im = Image.new("RGB", (900, 300), "white")
    d = ImageDraw.Draw(im)
    d.rectangle([40, 40, 200, 90], fill=(0, 0, 0))                              # pole redakcji
    d.rectangle([40, 120, 52, 170], fill=(0, 0, 0))                             # pole na kropkę (≈ 13 px – za wąskie)
    font = ImageFont.load_default(size=48)
    d.text((260, 40), "J.K. ar", fill=(0, 0, 0), font=font, stroke_width=1)     # pismo pogrubione
    d.rectangle([520, 30, 860, 110], outline=(200, 20, 20), width=4)            # ramka pieczątki
    d.text((540, 40), "V.G.", fill=(200, 20, 20), font=font)
    d.rectangle([520, 150, 860, 260], fill=(225, 235, 255), outline=(20, 40, 200), width=3)
    d.text((540, 170), "E.M.", fill=(20, 40, 200), font=font)
    po = np.asarray(obrazy.bez_pol(im))
    przed = np.asarray(im)
    assert (po[35:96, 35:206] == 255).all()                                     # pole z krawędzią – białe
    assert (po[:, 230:] == przed[:, 230:]).all()                                # pismo, ramka i pieczątka bez zmian
    assert (po[115:175, 35:60] == przed[115:175, 35:60]).all()
    czysty = Image.new("RGB", (100, 100), "white")
    assert obrazy.bez_pol(czysty) is czysty


def test_ocr_inicjaly_potwierdzenie_po_wybieleniu_pol():
    """I-R1: wzorzec inicjałów w dwóch odczytach strony (czarne pole czytane jako „rs” w każdym odczycie) liczy się tylko, gdy
    zostaje w odczycie bez pól zamalowanych (`_Ocr.wybielone`) – inaczej brak trafienia i strona do kolejnego odczytu. Odczyty
    bez pól są leniwe: kolejny tylko, gdy poprzedni nie trafia."""
    from pbench.sedzia import plik as sedzia_plik
    w = W("b.inicjaly#1", "RS", "INICJALY", jezyk="fr")
    g = sedzia_plik._Grupa([w], sedzia_plik.zbuduj_regule(w, R, set(), []), None,
                           sedzia_plik.zbuduj_regule(w, R, set(), [], ocr=True), None, True)
    wywolane: list[str] = []

    def odczyt(tekst: str):
        return lambda: wywolane.append(tekst) or tekst

    Ocr = sedzia_plik._Ocr
    szum = [[Ocr("strona 1", "le rs 12", wybielone=(odczyt("le 12"),))],
            [Ocr("strona 1 (400)", "le rs\fle rs", wybielone=(odczyt("le\fle"),))]]
    assert sedzia_plik._trafienia_ocr(g, szum) == ([], {0})
    assert wywolane == ["le 12", "le\fle"]
    wywolane.clear()
    parafa = [[Ocr("strona 1", "le RS 12", wybielone=(odczyt("le RS"),))],
              [Ocr("strona 1 (400)", "le RS", wybielone=(odczyt("le RS"),))]]
    assert sedzia_plik._trafienia_ocr(g, parafa)[0]
    assert wywolane == ["le RS"]


def test_pdf_parafa_tylko_w_pikselach_strony_z_warstwa_wycieka(tmp_path):
    """I-R1 (odtworzenie recenzenta, `h-pf-es-pismo_z_parafami-0003`): wynik nawiasowy (warstwa tekstowa bez parafy)
    z wklejonym w miejsce każdej parafy wycinkiem rastra oryginału – jako obraz inline `BI … EI` albo jako mały XObject. Strona
    ma warstwę tekstową, więc inicjały czyta OCR renderu bez obiektów tekstowych: wyciekają wszystkie czytelne
    (`_czytelne_parafy`); sam wynik nawiasowy – 0 wycieków; render oryginału bez tekstu nie ma wzorca żadnych inicjałów."""
    import zlib
    import pikepdf
    from pbench.sedzia import obrazy
    from pbench.sedzia.normalizacja import wzor_inicjalow
    orig, naw, ws = _parafy_pdf(tmp_path, "h-pf-es-pismo_z_parafami-0003")
    ini = [x for x in ws if x.kategoria == "INICJALY"]
    assert len({x.id for x in ini}) == 6
    czytelne = _czytelne_parafy(ws)
    assert czytelne
    pola = _pola_wartosci(orig, {x.tekst for x in ini}, na_znak=False)
    strony = _raster(orig, dpi=300)
    k = 300 / 72
    assert ocen_plik(orig, naw, ws, leksykon={}).wycieki == []
    bez_tekstu = [normalizuj(o) for _, t in obrazy.ocr_stron_pdf(orig, "es", bez_tekstu=True) for o in t.split("\f")]
    assert not any(wzor_inicjalow(x.tekst).search(o) for x in ini for o in bez_tekstu)
    for tryb in ("inline", "xobject"):
        pdf = pikepdf.open(naw)
        for i, strona in enumerate(pdf.pages):
            h = float(strona.mediabox[3])
            for n, (x0, y0, x1, y1) in enumerate(pola[i]):
                x0, y0, x1, y1 = x0 - 3, y0 - 3, x1 + 3, y1 + 3
                wycinek = strony[i].crop((int(x0 * k), int((h - y1) * k), int(x1 * k), int((h - y0) * k)))
                macierz = f"q {x1 - x0:.2f} 0 0 {y1 - y0:.2f} {x0:.2f} {y0:.2f} cm "
                if tryb == "inline":
                    op = (macierz + f"BI /W {wycinek.width} /H {wycinek.height} /CS /RGB /BPC 8 /F /Fl ID ").encode() \
                        + zlib.compress(wycinek.tobytes()) + b"\nEI Q\n"
                else:
                    obraz = pikepdf.Stream(pdf, wycinek.tobytes(), Type=pikepdf.Name.XObject, Subtype=pikepdf.Name.Image,
                                           Width=wycinek.width, Height=wycinek.height, ColorSpace=pikepdf.Name.DeviceRGB,
                                           BitsPerComponent=8)
                    strona.add_resource(obraz, pikepdf.Name.XObject, pikepdf.Name(f"/Parafa{n}"))
                    op = (macierz + f"/Parafa{n} Do Q\n").encode()
                strona.contents_add(pdf.make_stream(op))
        wynik = tmp_path / f"wynik-{tryb}.pdf"
        pdf.save(wynik, deterministic_id=True)
        pdf.close()
        o = ocen_plik(orig, wynik, ws, leksykon={})
        assert czytelne <= {x[0] for x in o.wycieki}, tryb
        assert all(x[1] == "INICJALY" for x in o.wycieki), tryb


@pytest.mark.parametrize("id_, style", [
    ("h-pf-fr-pismo_z_parafami-0002", ("na_znak", "pole", "pole_warstwa", "na_znak_warstwa")),
    ("h-pf-en-pismo_z_parafami-0002", ("na_znak_warstwa",)),
])
def test_pdf_parafy_czarne_pola_bez_falszywych_wyciekow(id_, style, tmp_path):
    """I-R1 (odtworzenie recenzenta): uczestnik redagujący rastrowo czarnymi polami (każda wartość gold zamalowana: pole na znak
    albo na wystąpienie; raster 200 dpi, sam albo jako obraz strony pod niewidoczną warstwą wyniku nawiasowego). Bez odczytu bez
    pól: fr-0002 – pole „R.S.” czytane jako „rs” (pole na wystąpienie i na znak), en-0002 – „jm” (na znak + warstwa) = fałszywy
    wyciek inicjałów. Po wybieleniu pól zamalowanych wzorca nie ma – 0 wycieków `INICJALY`; prawdziwe parafy w kopii zrasteryzowanej tego samego
    dokumentu wyciekają wszystkie."""
    orig, naw, ws = _parafy_pdf(tmp_path, id_)
    ini = {x.id for x in ws if x.kategoria == "INICJALY"}
    teksty = {x.tekst for x in ws if x.tekst.strip()}
    for styl in style:
        na_znak = styl.startswith("na_znak")
        rysuj = _czarne_pola(_pola_wartosci(orig, teksty, na_znak), 2 if na_znak else 1)
        wynik = _pdf_z_obrazow(_raster(orig, rysuj), tmp_path / f"{styl}.pdf", naw if styl.endswith("warstwa") else None)
        o = ocen_plik(orig, wynik, ws, leksykon={})
        assert [x for x in o.wycieki if x[1] == "INICJALY"] == [], styl
    kopia = _pdf_z_obrazow(_raster(orig), tmp_path / "kopia-raster.pdf")
    assert ini <= {x[0] for x in ocen_plik(orig, kopia, ws, leksykon={}).wycieki}


def test_pdf_parafa_w_kolorowej_pieczatce_wycieka(tmp_path, monkeypatch):
    """I-R1: wybielanie pól nie zabiera parafy w kolorowej pieczątce – kopia zrasteryzowana, w której każda parafa ma kolorowy tusz
    i ramkę (niebieska pieczątka z jasnym wypełnieniem albo czerwona ramka na białym tle): wycieka to samo co bez warunku odczytu
    bez pól (`_po_wybieleniu`). Ramka tuż przy znakach utrudnia OCR (część parafek nie jest czytana w żadnym odczycie – to samo
    z warunkiem i bez), ale nie odczyt po wybieleniu. Dokument `h-pf-en-pismo_z_parafami-0002`: co najmniej dwie czytelne parafy
    z kropkami (wyprowadzone z gold)."""
    from PIL import ImageDraw
    from pbench.sedzia import plik as sedzia_plik
    orig, _, ws = _parafy_pdf(tmp_path, "h-pf-en-pismo_z_parafami-0002")
    ini = [x for x in ws if x.kategoria == "INICJALY"]
    pola = _pola_wartosci(orig, {x.tekst for x in ini}, na_znak=False)

    def rysuj(i, im, k, h):
        d = ImageDraw.Draw(im)
        for n, (x0, y0, x1, y1) in enumerate(pola[i]):
            ramka = (int(x0 * k) - 8, int((h - y1) * k) - 8, int(x1 * k) + 8, int((h - y0) * k) + 8)
            tusz, tlo = ((200, 20, 20), None) if n % 2 else ((20, 40, 200), (225, 235, 255))
            kolor = im.crop(ramka).convert("L").point(lambda v: 255 if v < 160 else 0)
            if tlo is not None:
                d.rectangle(ramka, fill=tlo)
            im.paste(tusz, ramka, kolor)
            d.rectangle(ramka, outline=tusz, width=3)
    pieczatki = _pdf_z_obrazow(_raster(orig, rysuj), tmp_path / "pieczatki.pdf")
    z_warunkiem = {x[0] for x in ocen_plik(orig, pieczatki, ws, leksykon={}).wycieki if x[1] == "INICJALY"}
    monkeypatch.setattr(sedzia_plik, "_po_wybieleniu", lambda g, obiekty, osadzone=False: True)
    bez_warunku = {x[0] for x in ocen_plik(orig, pieczatki, ws, leksykon={}).wycieki if x[1] == "INICJALY"}
    assert z_warunkiem == bez_warunku
    kropki = {x.id for x in ini if x.tekst.endswith(".")} & _czytelne_parafy(ws)               # parafy z kropkami („A.R.”)
    assert len(kropki) >= 2 and kropki <= z_warunkiem


def test_szkielet_greki():
    """M2: litery greckie mylone z łacińskimi (UTS #39, pary litera ↔ litera) – „Κοwalski” (greckie Κ, ο) = „Kowalski”."""
    assert szkielet(normalizuj("Κοwalski")) == szkielet(normalizuj("ΚΟWALSKI")) == "kowalski"
    assert szkielet(normalizuj("Ραvel")) == szkielet(normalizuj("Paνel")) == "pavel"                     # Ρ/P wielkie, ν/v małe
    assert szkielet(normalizuj("Jan Kowalski")) == "jan kowalski"


def test_plik_greckie_homoglify_w_wyniku_to_wyciek(tmp_path):
    ws = [W("p.pelne#1", "Jan Kowalski")]
    orig = _docx(tmp_path / "o.docx", "Umowę podpisał Jan Kowalski osobiście.")
    assert _wycieki(orig, _docx(tmp_path / "g.docx", "Umowę podpisał Jan Κοwalski osobiście."), ws) == {"p.pelne#1": "pelny"}
    assert _wycieki(orig, _docx(tmp_path / "i.docx", "Umowę podpisał [OSOBA_1] osobiście."), ws) == {}


def test_plik_bez_liter_szkieletu_bez_przejsc_szkieletu(tmp_path, monkeypatch):
    """M8: bez liter szkieletu w wartościach, oryginale i wyniku sędzia nie liczy niejednoznaczności w szkielecie ani wariantów
    `tylko_cyrylica` – wynik taki sam jak z przejściami szkieletu (`_zbiory_dokumentu(z_szkieletem=True)`); wynik z cyrylicą
    mylącą dostaje zbiory pełne (kierunek odwrotny nadal wycieka)."""
    from pbench.sedzia import plik as sedzia_plik
    ws = [W("p.pelne#1", "Jan Kowalski"), W("p.pelne#2", "Anna Dąbrowska"), W("a.ini#1", "J.K.", "INICJALY")]
    orig = _docx(tmp_path / "o.docx", "Umowę podpisał Jan Kowalski, a Anna Dąbrowska była świadkiem. Paraf: J.K.")
    czes = _docx(tmp_path / "c.docx", "Umowę podpisał Jan [X], a Anna Dabrowska była świadkiem. Paraf: [X]")
    zb = sedzia_plik.zbiory_dokumentu(orig, ws, leksykon={})
    assert zb.pelne is not None and all(g.reg_z is None or not g.reg_z.tylko_cyrylica for g in zb.grupy)
    pelne = zb.pelne()
    assert pelne.pelne is None and any(g.reg_z is not None and g.reg_z.tylko_cyrylica for g in pelne.grupy)
    lekko = [ocen_plik(orig, w, ws, leksykon={}) for w in (orig, czes)]
    prawdziwe = sedzia_plik._zbiory_dokumentu
    monkeypatch.setattr(sedzia_plik, "_zbiory_dokumentu", lambda *a, **k: prawdziwe(*a, **{**k, "z_szkieletem": True}))
    assert [ocen_plik(orig, w, ws, leksykon={}) for w in (orig, czes)] == lekko
    monkeypatch.undo()
    cyr = _docx(tmp_path / "k.docx", "Umowę podpisał Jаn Kоwalski, a [X] była świadkiem. Paraf: [X]")
    assert _wycieki(orig, cyr, ws) == {"p.pelne#1": "pelny"}


def test_wznowienie_przelicza_nieaktualny_pominiety_jezyk(tmp_path, monkeypatch):
    """M3: wpis `pominiety: jezyk` dokumentu `uk` z przebiegu sprzed języka zastępczego jest przy wznowieniu przeliczany;
    `pominiety` języka, którego uczestnik nadal nie przetwarza, i `pominiety: format` – nie."""
    from test_uruchom import surowe, uruchom_atrape, wg_id, zrob_srodowisko
    sr = zrob_srodowisko(tmp_path)
    wpisy = [json.loads(l) for l in sr["manifest"].read_text(encoding="utf-8").splitlines()]
    tekst = "Олена Коваленко мешкає у Києві."
    (sr["korpus"] / "uk-a-0001.txt").write_text(tekst, encoding="utf-8")
    wpisy.append({"id": "uk-a-0001", "jezyk": "uk", "typ": "pozew", "format": "docx", "split": "dev", "plik": "uk-a-0001.docx",
                  "plik_txt": "uk-a-0001.txt", "gold_tekst": [{"start": 0, "end": 15, "wartosc_id": "w0#1", "kategoria": "OSOBA",
                                                               "miejsce": "tresc", "tekst": tekst[:15]}],
                  "gold_plik": [], "gold_obrazy": [], "ostrzezenia": []})
    sr["manifest"].write_text("\n".join(json.dumps(w, ensure_ascii=False) for w in wpisy) + "\n", encoding="utf-8")
    stary = sr["wyniki"] / "surowe" / "_atrapa" / "dev" / "tekst.jsonl"
    stary.parent.mkdir(parents=True)
    stary.write_text('{"id": "uk-a-0001", "pominiety": "jezyk"}\n{"id": "de-a-0001", "pominiety": "jezyk"}\n', encoding="utf-8")
    toml = 'poziomy = ["tekst"]\njezyki = ["en", "pl"]\nformaty = ["docx"]\nprocesy = 1\ntimeout_s = 60\n'
    assert uruchom_atrape(sr, monkeypatch, toml=toml, argv=("--jezyki", "uk,de", "--bez-ponawiania")) == 0
    rek = surowe(sr)
    assert wg_id(rek)["uk-a-0001"]["jezyk_uzyty"] == "pl" and "wykrycia" in wg_id(rek)["uk-a-0001"]
    assert [r for r in rek if r["id"] == "de-a-0001"] == [{"id": "de-a-0001", "pominiety": "jezyk"}]      # bez ponownego wpisu
    assert uruchom.gotowe_id(stary) == {"uk-a-0001", "de-a-0001"}
    assert uruchom.gotowe_id(stary, obslugiwany=lambda i: True) == {"uk-a-0001"}


#: Migawki sędziego plikowego dla stałej próbki trzonu: bez danych OCR (`PBENCH_TESSDATA` – pusty katalog) i z OCR
#: (`vendor/tessdata`); ta sama próbka dokumentów.
TRZON_MIGAWKI = {nazwa: json.loads((Path(__file__).parent / "dane_testowe" / f"{nazwa}.json").read_text(encoding="utf-8"))
                 for nazwa in ("sedzia_trzon_h6a", "sedzia_trzon_ocr")}


def _ocena_trzonu(o, czesciowy: bool) -> dict:
    if czesciowy:
        d = {"wycieki": o.wycieki, "ocenione": o.wartosci_ocenione, "spojnosc": o.integralnosc["spojnosc"],
             "encje": o.integralnosc["encje"]}
    else:
        d = {"wycieki": o.wycieki, "niejednoznaczne": o.niejednoznaczne, "niewykrywalne": list(o.niewykrywalne),
             "ocenione": o.wartosci_ocenione, "bazowe": o.bazowe}
    return json.loads(json.dumps(d, ensure_ascii=False))


@pytest.mark.parametrize("migawka, poz", [(m, p) for m in TRZON_MIGAWKI for p in TRZON_MIGAWKI[m]["probka"]],
                         ids=lambda x: x if isinstance(x, str) else x[0])
def test_trzon_wyniki_sedziego_bez_zmian(migawka, poz, tmp_path, monkeypatch):
    """M6: regresja trzonu – stała próbka (12 dokumentów: DOCX, PDF, skan, XLSX, PPTX, EML, MSG, DOC; pięć języków), wyniki
    sędziego plikowego zapisane w migawkach (`dane_testowe/sedzia_trzon_h6a.json`, `sedzia_trzon_ocr.json`, pole `zrodlo`): kopia
    oryginału (wycieki, niejednoznaczne, niewykrywalne, ocenione, linia bazowa) i uczestnik połowiczny (`sanity.Czesciowe`: wycieki,
    ocenione, spójność) – reguły warstwy trudnej (szkielet cyrylicy i greki, inicjały, pominięte przejścia szkieletu) niczego na
    trzonie nie zmieniają. Migawka `sedzia_trzon_h6a` – bez danych OCR (`PBENCH_TESSDATA` wskazuje pusty katalog: ścieżka bez
    odczytu obrazów osadzonych i skanów), `sedzia_trzon_ocr` – z OCR (`vendor/tessdata`: `niewykrywalne`, `bazowe` i `ocenione`
    z odczytem obrazów i stron)."""
    from pbench import korpus
    if migawka == "sedzia_trzon_h6a":
        monkeypatch.setenv("PBENCH_TESSDATA", str(tmp_path / "brak-tessdata"))
    else:
        monkeypatch.delenv("PBENCH_TESSDATA", raising=False)
    from pbench.sedzia.sanity import Czesciowe
    id_, jezyk, typ, fmt, split = poz
    p = korpus.Pozycja(id_, jezyk, typ, fmt)
    wpis = korpus.generuj_dokument(p, korpus.ZIARNO, split, tmp_path / "o")
    czes = korpus.generuj_dokument(p, korpus.ZIARNO, split, tmp_path / "c", maskuj=Czesciowe())
    ws = wartosci_wpisu(wpis)
    orig = tmp_path / "o" / wpis["plik"]
    oczekiwane = TRZON_MIGAWKI[migawka]["wyniki"][id_]
    assert _ocena_trzonu(ocen_plik(orig, orig, ws, leksykon={}), False) == oczekiwane["kopia"]
    assert _ocena_trzonu(ocen_plik(orig, tmp_path / "c" / czes["plik"], ws, leksykon={}), True) == oczekiwane["czesciowy"]


@pytest.mark.parametrize("dpi", [150, 300])
def test_maly_obraz_osadzony_wybielanie_przed_powiekszeniem(dpi):
    """I-R2: w małym obrazie osadzonym pola zamalowane liczone są w pikselach obrazu źródłowego (przed powiększeniem do OCR) –
    parafa „R.S.” 11 pt zostaje w odczycie po wybieleniu (jak w zwykłym), a ta sama parafa pod czarnym prostokątem znika."""
    import io
    import re
    from PIL import Image, ImageDraw, ImageFont
    from pbench.sedzia import obrazy
    px = round(11 * dpi / 72)
    font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf", px)

    def png(zamaluj: bool) -> bytes:
        im = Image.new("RGB", (int(px * 2.6) + 20, px + 16), "white")
        ImageDraw.Draw(im).text((10, 6), "R.S.", font=font, fill=(0, 0, 0))
        if zamaluj:
            ImageDraw.Draw(im).rectangle([4, 2, im.width - 4, im.height - 2], fill=(0, 0, 0))
        b = io.BytesIO()
        im.save(b, "PNG")
        return b.getvalue()

    wzor = re.compile(r"R\.?\s*S", re.IGNORECASE)
    assert max(Image.open(io.BytesIO(png(False))).size) < obrazy.MALY_OBRAZ_PX
    assert wzor.search(obrazy.ocr_tekst(png(False), "en"))
    assert wzor.search(obrazy.ocr_tekst(png(False), "en", wybiel=True))
    assert not wzor.search(obrazy.ocr_tekst(png(True), "en", wybiel=True))
