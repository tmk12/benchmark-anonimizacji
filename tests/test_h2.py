"""Warstwa trudnych przypadków, zadanie H2 (spec §11 pkt 2 i 5): liczebniki słownie, odmiana rodzin, plan i generacja
dziewięciu przypadków (odmiana_nazwisk, nazwiska_zwykle_slowa, zdrobnienia, nazwisko_imie, parafy, liczby_slownie,
skroty_po_pelnym, granica_okna, dlugie_listy_osob), gold w pliku (niezależne czytniki), granice okien modelu,
pułapki pospolite, sanity (oryginał wycieka, idealny uczestnik nie)."""
from __future__ import annotations

import datetime as dt
import json
import random
import re
import zipfile
from collections import Counter
from pathlib import Path

import pytest
from test_render_docx import _teksty_miejsc
from test_render_inne import _blob_doc, _teksty_xlsx, _w_blobie
from test_render_pdf import _sprawdz_miejsca

from pbench import liczebniki as L, przypadki as P, trudne, trudne_dlugie, trudne_jezyk, trudne_wypelniacz
from pbench.model import Wartosc
from pbench.trudne_wspolne import ZABLOKOWANE
from pbench.sedzia.plik import ocen_plik, zbuduj_regule
from pbench.sedzia.tekst import RegulyWycieku
from pbench.sedzia.sanity import Maskowanie, wartosci_wpisu

H2 = P.H2
POLE_ROL = ("Powód", "Pozwana")


def _manifest(cel: Path) -> list[dict]:
    return [json.loads(w) for w in (cel / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]


# ============================================================================= liczebniki
@pytest.mark.parametrize("n,oczek", [
    (0, "zero"), (1, "jeden"), (12, "dwanaście"), (21, "dwadzieścia jeden"), (100, "sto"), (112, "sto dwanaście"),
    (999, "dziewięćset dziewięćdziesiąt dziewięć"), (1000, "tysiąc"), (2000, "dwa tysiące"), (5000, "pięć tysięcy"),
    (12_000, "dwanaście tysięcy"), (22_000, "dwadzieścia dwa tysiące"), (2005, "dwa tysiące pięć"),
    (1_000_000, "milion"), (2_000_000, "dwa miliony"), (5_000_000, "pięć milionów"),
    (22_222_222, "dwadzieścia dwa miliony dwieście dwadzieścia dwa tysiące dwieście dwadzieścia dwa")])
def test_liczba_pl(n, oczek):
    assert L.liczba(n, "pl") == oczek


@pytest.mark.parametrize("gr,oczek", [
    (100, "jeden złoty"), (200, "dwa złote"), (2200, "dwadzieścia dwa złote"), (2500, "dwadzieścia pięć złotych"),
    (1200, "dwanaście złotych"), (101, "jeden złoty i jeden grosz"), (202, "dwa złote i dwa grosze"),
    (525, "pięć złotych i dwadzieścia pięć groszy"), (250_050, "dwa tysiące pięćset złotych i pięćdziesiąt groszy"),
    (0, "zero złotych")])
def test_kwota_pl_odmiana_zlotego_i_grosza(gr, oczek):
    assert L.kwota(gr, "pl") == oczek


@pytest.mark.parametrize("n,oczek", [
    (1, "pierwszego"), (3, "trzeciego"), (11, "jedenastego"), (20, "dwudziestego"), (23, "dwudziestego trzeciego"),
    (30, "trzydziestego"), (31, "trzydziestego pierwszego"), (1985, "tysiąc dziewięćset osiemdziesiątego piątego"),
    (1999, "tysiąc dziewięćset dziewięćdziesiątego dziewiątego"), (1900, "tysiąc dziewięćsetnego"),
    (2000, "dwutysięcznego"), (2005, "dwa tysiące piątego"), (2020, "dwa tysiące dwudziestego"),
    (2026, "dwa tysiące dwudziestego szóstego")])
def test_porzadkowa_pl_dopelniacz(n, oczek):
    assert L.porzadkowa_pl_dop(n) == oczek


def test_data_slownie_zdanie_z_briefu_i_inne_jezyki():
    assert L.data(dt.date(1985, 3, 23), "pl") == "dwudziestego trzeciego marca tysiąc dziewięćset osiemdziesiątego piątego roku"
    assert L.data(dt.date(1985, 3, 23), "en") == "the twenty-third of March nineteen eighty-five"
    assert L.data(dt.date(1985, 3, 23), "de") == "am dreiundzwanzigsten März neunzehnhundertfünfundachtzig"
    assert L.data(dt.date(1985, 3, 23), "es") == "veintitrés de marzo de mil novecientos ochenta y cinco"
    assert L.data(dt.date(1985, 3, 23), "fr") == "le vingt-trois mars mille neuf cent quatre-vingt-cinq"
    assert L.data(dt.date(2021, 1, 1), "de") == "am ersten Januar zweitausendeinundzwanzig"
    assert L.data(dt.date(2001, 10, 4), "de") == "am vierten Oktober zweitausendeins"
    assert L.data(dt.date(2021, 1, 1), "fr") == "le premier janvier deux mille vingt et un"
    assert L.data(dt.date(2021, 1, 1), "es") == "primero de enero de dos mil veintiuno"
    assert L.data(dt.date(2005, 12, 31), "en") == "the thirty-first of December two thousand and five"
    assert L.data(dt.date(2026, 6, 15), "en") == "the fifteenth of June twenty twenty-six"


@pytest.mark.parametrize("jezyk,n,oczek", [
    ("en", 2500, "two thousand five hundred"), ("en", 12_345, "twelve thousand three hundred and forty-five"),
    ("en", 101, "one hundred and one"), ("de", 2500, "zweitausendfünfhundert"), ("de", 21, "einundzwanzig"),
    ("de", 1, "eins"), ("de", 1_000_000, "eine Million"), ("es", 2500, "dos mil quinientos"), ("es", 21, "veintiuno"),
    ("es", 100, "cien"), ("es", 101, "ciento uno"), ("es", 1_000_000, "un millón"), ("fr", 2500, "deux mille cinq cents"),
    ("fr", 80, "quatre-vingts"), ("fr", 71, "soixante et onze"), ("fr", 99, "quatre-vingt-dix-neuf"),
    ("fr", 80_000, "quatre-vingt mille"), ("fr", 200, "deux cents"), ("fr", 201, "deux cent un")])
def test_liczba_inne_jezyki(jezyk, n, oczek):
    assert L.liczba(n, jezyk) == oczek


def test_kwota_inne_jezyki():
    assert L.kwota(250_050, "en") == "two thousand five hundred pounds and fifty pence"
    assert L.kwota(100, "en") == "one pound" and L.kwota(101, "en") == "one pound and one penny"
    assert L.kwota(100, "en", "USD") == "one dollar" and L.kwota(250_025, "en", "USD").endswith("and twenty-five cents")
    assert L.kwota(250_050, "de") == "zweitausendfünfhundert Euro und fünfzig Cent" and L.kwota(100, "de") == "ein Euro"
    assert L.kwota(250_050, "es") == "dos mil quinientos euros con cincuenta céntimos" and L.kwota(100, "es") == "un euro"
    assert L.kwota(250_050, "fr") == "deux mille cinq cents euros et cinquante centimes" and L.kwota(100, "fr") == "un euro"


def test_cyfry_slownie_i_zakres():
    assert L.cyfry_slownie("85032312345", "pl") == "osiem pięć zero trzy dwa trzy jeden dwa trzy cztery pięć"
    with pytest.raises(ValueError):
        L.liczba(-1, "pl")
    with pytest.raises(ValueError):
        L.liczba(1_000_000_000, "en")
    with pytest.raises(ValueError):
        L.liczba(1, "uk")
    with pytest.raises(ValueError):
        L.porzadkowa_pl_dop(0)


@pytest.mark.parametrize("jezyk", L.JEZYKI)
def test_liczebniki_losowe_bez_cyfr_i_znaczkow(jezyk):
    rng = random.Random(3)
    for _ in range(300):
        n = rng.choice((rng.randint(0, 999), rng.randint(0, 999_999), rng.randint(0, 999_999_999)))
        t = L.liczba(n, jezyk)
        assert t and not re.search(r"\d", t) and t == t.strip() and "  " not in t, (n, t)
    for d in (dt.date(1940, 1, 1), dt.date(2005, 12, 31), dt.date(2026, 10, 29), dt.date(1999, 2, 28)):
        assert not re.search(r"\d", L.data(d, jezyk))


# ============================================================================= odmiana rodzin
@pytest.mark.parametrize("nazwisko,wyniki", [
    ("Kowalski", ["Kowalscy", "Kowalskich", "Kowalskim", "Kowalskich", "Kowalskimi", "Kowalskich"]),
    ("Zieliński", ["Zielińscy", "Zielińskich", "Zielińskim", "Zielińskich", "Zielińskimi", "Zielińskich"]),
    ("Nowacki", ["Nowaccy", "Nowackich", "Nowackim", "Nowackich", "Nowackimi", "Nowackich"]),
    ("Nowak", ["Nowakowie", "Nowaków", "Nowakom", "Nowaków", "Nowakami", "Nowakach"]),
    ("Król", ["Królowie", "Królów", "Królom", "Królów", "Królami", "Królach"])])
def test_forma_rodzinna(nazwisko, wyniki):
    assert [trudne_jezyk.forma_rodzinna(nazwisko, p) for p in ("mian", "dop", "cel", "bier", "narz", "msc")] == wyniki


def test_forma_rodzinna_bledy_i_zenskie():
    with pytest.raises(ValueError):
        trudne_jezyk.forma_rodzinna("Kowalski", "woł")
    with pytest.raises(ValueError):
        trudne_jezyk.forma_rodzinna("Wróbel", "mian")          # alternacja tematu – poza obsługiwanym zakresem
    assert trudne_jezyk.nazwisko_zenskie("Kowalski") == "Kowalska" and trudne_jezyk.nazwisko_zenskie("Nowak") == "Nowak"
    assert trudne_jezyk.zapis_nazwisko_imie(type("O", (), {"imie": "Jan", "nazwisko": "Kowalski"})(), "pl", True) == "KOWALSKI Jan"
    assert trudne_jezyk.zapis_nazwisko_imie(type("O", (), {"imie": "John", "nazwisko": "Smith"})(), "en", False) == "Smith, John"


# ============================================================================= zdanie o dokładnej długości i granice okien
def test_granice_okien_definicja():
    assert P.GRANICA_OKNA_ZNAKI == 2560 and P.ZAKLADKA_ZNAKI == 448 and P.TOLERANCJA_ZNAKI == 50
    g = trudne_dlugie.granice_okien(9000)
    assert g[:6] == [(2112, "poczatek_okna"), (2560, "koniec_okna"), (4224, "poczatek_okna"), (4672, "koniec_okna"),
                     (6336, "poczatek_okna"), (6784, "koniec_okna")]
    assert (0, "poczatek_okna") not in g and all(0 < x < 9000 for x, _ in g)
    assert trudne_dlugie.najblizsza_granica(2100, 9000) == (2112, "poczatek_okna")
    assert trudne_dlugie.najblizsza_granica(2540, 9000) == (2560, "koniec_okna")
    assert trudne_dlugie.pozycja_przy_granicy(2100, 2130, 9000) == (2112, "poczatek_okna", -12, True)
    assert trudne_dlugie.pozycja_przy_granicy(2120, 2140, 9000) == (2112, "poczatek_okna", 8, False)


# ============================================================================= rejestr i plan
def test_rejestr_h2():
    assert set(H2) <= set(P.PRZYPADKI) and not set(H2) & set(P.H1) and len(H2) == 9
    assert set(P.SKROTY) == set(P.H1) | set(H2) | set(P.H3) | set(P.H4A) | set(P.H4B) | set(P.H5) \
        and len(set(P.SKROTY.values())) == len(P.SKROTY)
    assert set(trudne.GENERATORY_H2) == set(H2)
    P.sprawdz(list(H2))


@pytest.mark.parametrize("przypadek", H2)
def test_plan_h2(przypadek):
    plan = trudne.zaplanuj_przypadek(przypadek, 30)
    assert len(plan) == 30 and plan == trudne.zaplanuj_przypadek(przypadek, 30) and plan == sorted(plan, key=lambda p: p.id)
    assert len({p.id for p in plan}) == 30
    for p in plan:
        assert re.fullmatch(rf"h-{P.SKROTY[przypadek]}-{p.jezyk}-{p.typ}-\d{{4}}", p.id) and (p.jezyk, p.typ) in trudne.GENERATORY_H2[przypadek]
        assert p.format in trudne.formaty_dla(p.jezyk, p.typ) and p.format in ("docx", "pdf", "doc", "xlsx")
    jezyki = {p.jezyk for p in trudne.zaplanuj_przypadek(przypadek, 60)}
    assert jezyki == ({"pl"} if przypadek == P.ODMIANA_NAZWISK else {"pl", "en", "es", "de", "fr"})
    formaty = {p.format for p in trudne.zaplanuj_przypadek(przypadek, 60)}
    assert {"docx", "pdf"} <= formaty and ("xlsx" in formaty) == (przypadek == P.DLUGIE_LISTY_OSOB)
    split = trudne.przydziel_split(plan)
    assert set(split.values()) == {"dev", "test"}


def test_plany_h2_nie_koliduja_z_trzonem_i_h1():
    wszystkie = [p.id for pr in (*P.H1, *H2) for p in trudne.zaplanuj_przypadek(pr, 40)]
    assert len(set(wszystkie)) == len(wszystkie)


def test_przypadek_bez_generatora_jest_bledem():
    with pytest.raises(ValueError):            # od H5 każdy przypadek rejestru ma generator – nazwa spoza rejestru
        trudne.zaplanuj_przypadek("nie_ma_takiego", 10)


# ============================================================================= generacja: dokumenty i manifest
@pytest.fixture(scope="module")
def warstwa(tmp_path_factory) -> dict[str, tuple[Path, list[dict]]]:
    wynik = {}
    for przypadek in H2:
        cel = tmp_path_factory.mktemp(przypadek)
        wynik[przypadek] = (cel, trudne.zbuduj_przypadek(cel, przypadek, 10, procesy=1, formaty=("docx", "pdf")))
    return wynik


def _tekst(cel: Path, w: dict) -> str:
    return (cel / w["plik_txt"]).read_text(encoding="utf-8")


@pytest.mark.parametrize("przypadek", H2)
def test_manifest_h2(warstwa, przypadek):
    cel, wpisy = warstwa[przypadek]
    assert len(wpisy) >= 6 and wpisy == _manifest(cel) and [w["id"] for w in wpisy] == sorted(w["id"] for w in wpisy)
    assert {w["split"] for w in wpisy} <= {"dev", "test"}
    for w in wpisy:
        assert w["warstwa"] == "trudne" and w["przypadki"] == [przypadek] and w["posrednie"] == [] and w["ostrzezenia"] == []
        assert (cel / w["plik"]).is_file() and w["id"].startswith(f"h-{P.SKROTY[przypadek]}-")
        tekst = _tekst(cel, w)
        ostatni = 0
        for g in w["gold_tekst"]:
            assert g["start"] >= ostatni and tekst[g["start"]:g["end"]] == g["tekst"]
            ostatni = g["end"]
        assert ("pulapki_pospolite" in w) == (przypadek == P.NAZWISKA_ZWYKLE_SLOWA)


def test_generacja_h2_deterministyczna_i_niezalezna_od_procesow(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    for pr in (P.GRANICA_OKNA, P.NAZWISKA_ZWYKLE_SLOWA):
        trudne.zbuduj_przypadek(a / pr, pr, 4, procesy=1, formaty=("docx", "pdf"))
        trudne.zbuduj_przypadek(b / pr, pr, 4, procesy=2, formaty=("docx", "pdf"))
        assert (a / pr / "manifest.jsonl").read_bytes() == (b / pr / "manifest.jsonl").read_bytes()
        for w in _manifest(a / pr):
            assert (a / pr / w["plik"]).read_bytes() == (b / pr / w["plik"]).read_bytes()
            assert (a / pr / w["plik_txt"]).read_bytes() == (b / pr / w["plik_txt"]).read_bytes()


def test_cli_h2(tmp_path, capsys):
    assert trudne.main(["--cel", str(tmp_path), "--przypadek", "parafy", "--n", "6", "--formaty", "docx"]) == 0
    wpisy = _manifest(tmp_path)
    assert f"parafy dokumentów: {len(wpisy)} " in capsys.readouterr().out and wpisy and {w["format"] for w in wpisy} == {"docx"}


# ----------------------------------------------------------------------------- własności przypadków
def _gold(w: dict, **warunki) -> list[dict]:
    return [g for g in w["gold_tekst"] if all(g.get(k) == v for k, v in warunki.items())]


def test_odmiana_nazwisk_formy_rodzinne_i_przypadki_zalezne(warstwa):
    cel, wpisy = warstwa[P.ODMIANA_NAZWISK]
    for w in wpisy:
        assert w["jezyk"] == "pl"
        osoby = {g["encja"]: g for g in w["gold_tekst"] if g["wartosc_id"].endswith(".pelne#1")}
        assert {"m1", "k1"} <= set(osoby)                                    # głowa rodziny i żona występują imiennie
        rodzinne = [g for g in w["gold_tekst"] if "forma_rodzinna" in g.get("cechy", ())]
        przyp = {r["tekst"] for r in rodzinne}
        assert len(rodzinne) >= 8 and {"liczba_mnoga", "forma_rodzinna"} <= set(rodzinne[0]["cechy"])
        assert all(g["kategoria"] == "OSOBA" for g in rodzinne)
        # encja formy rodzinnej = encja osoby występującej imiennie
        assert {g["encja"] for g in rodzinne} <= set(osoby)
        nazwisko_m1 = osoby["m1"]["tekst"].split()[-1]
        assert {trudne_jezyk.forma_rodzinna(nazwisko_m1, p) for p in ("mian", "dop", "cel", "bier", "narz", "msc")} & przyp
        zalezne = [g for g in w["gold_tekst"] if "przypadek_zalezny" in g.get("cechy", ())]
        assert zalezne and all(g["tekst"] != osoby[g["encja"]]["tekst"] for g in zalezne)
        assert "Państw" in _tekst(cel, w) or any(g["tekst"].endswith(("ich", "ów")) for g in rodzinne)


def test_nazwiska_zwykle_slowa_pulapki_nie_sa_gold(warstwa):
    cel, wpisy = warstwa[P.NAZWISKA_ZWYKLE_SLOWA]
    assert {w["jezyk"] for w in wpisy} >= {"pl", "en", "de"}
    for w in wpisy:
        tekst = _tekst(cel, w)
        pulapki = w["pulapki_pospolite"]
        assert pulapki and pulapki == sorted(pulapki, key=lambda x: x["start"])
        nazwisko = _gold(w, wartosc_id="os.nazwisko#1")[0]["tekst"]
        for p in pulapki:
            assert tekst[p["start"]:p["end"]] == p["tekst"] and p["tekst"].lower() == nazwisko.lower() and p["encja"] == "os"
            assert not any(g["start"] < p["end"] and p["start"] < g["end"] for g in w["gold_tekst"]), p       # nie jest gold
        assert len(_gold(w, kategoria="OSOBA")) >= 3                                                           # imię i nazwisko oraz same nazwisko


def test_zdrobnienia_wspolna_encja_i_slownik(warstwa):
    cel, wpisy = warstwa[P.ZDROBNIENIA]
    for w in wpisy:
        dozwolone = {d for _, _, ds in trudne_jezyk.ZDROBNIENIA_IMION[w["jezyk"]] for d in ds}
        zdrobnienia = [g for g in w["gold_tekst"] if "zdrobnienie" in g.get("cechy", ())]
        assert len(zdrobnienia) >= 5
        for g in zdrobnienia:
            assert g["tekst"].split()[0] in dozwolone and g["encja"] in ("p1", "p2")
            pelne = _gold(w, wartosc_id=f"{g['encja']}.pelne#1")[0]
            assert pelne["start"] < g["start"] and pelne["tekst"].split()[0] not in dozwolone      # wcześniej pełnym imieniem
            if " " in g["tekst"]:
                assert g["tekst"].split()[-1] == pelne["tekst"].split()[-1]                         # to samo nazwisko


def test_nazwisko_imie_zapis_calosci_jako_osoba(warstwa):
    cel, wpisy = warstwa[P.NAZWISKO_IMIE]
    wielkie = 0
    for w in wpisy:
        zapisy = [g for g in w["gold_tekst"] if "nazwisko_imie" in g.get("cechy", ())]
        assert 8 <= len(zapisy) <= 14 and all(g["kategoria"] == "OSOBA" for g in zapisy)
        for g in zapisy:
            if w["jezyk"] in ("pl", "fr"):
                assert re.fullmatch(r"\S+( \S+)? \S+", g["tekst"]), g["tekst"]
            else:
                assert ", " in g["tekst"], g["tekst"]
            wielkie += "wielkie_litery" in g["cechy"]
            assert (g["tekst"].split(",")[0].split()[0].isupper()) == ("wielkie_litery" in g["cechy"])
        zatw = [g for g in w["gold_tekst"] if g["wartosc_id"].endswith(".pelne#1")]
        assert len(zatw) == 1 and zatw[0]["encja"].startswith("w")
    assert wielkie > 0


def test_parafy_inicjaly_osob_z_pelnym_nazwiskiem(warstwa):
    cel, wpisy = warstwa[P.PARAFY]
    for w in wpisy:
        ini = [g for g in w["gold_tekst"] if g["kategoria"] == "INICJALY"]
        assert len(ini) == 6                       # jk/ak, dwa paraf-y (Paraf: i /…/), dwa w stopce
        osoby = {g["encja"]: g["tekst"] for g in w["gold_tekst"] if g["kategoria"] == "OSOBA"}
        assert set(osoby) == {"a", "b"}
        for g in ini:
            if g["encja"] in osoby:                # inicjały osoby występującej z pełnym nazwiskiem – wspólna encja
                czlony = osoby[g["encja"]].split()
                litery = re.sub(r"[./]", "", g["tekst"]).lower()
                assert len(litery) == 2 and litery[0] == czlony[0][0].lower() and litery[1] in {c[0].lower() for c in czlony[1:]}
        assert {g["encja"] for g in ini} == {"a", "b", "c"}                   # c: maszynistka, nie występuje imiennie
        formy = {g["tekst"] for g in ini}
        assert any(re.fullmatch(r"[A-ZĄĆĘŁŃÓŚŹŻ]\.[A-ZĄĆĘŁŃÓŚŹŻ]\.", f) for f in formy) and any(f.islower() for f in formy)
        tekst = _tekst(cel, w)
        assert "/" in tekst


def test_liczby_slownie_osobne_wartosci_cyframi_i_slownie(warstwa):
    cel, wpisy = warstwa[P.LICZBY_SLOWNIE]
    for w in wpisy:
        slownie = [g for g in w["gold_tekst"] if "slownie" in g.get("cechy", ())]
        cyframi = [g for g in w["gold_tekst"] if "cyframi" in g.get("cechy", ())]
        assert {g["kategoria"] for g in slownie} == ({"DATA", "DATA_UR", "KWOTA", "PESEL"} if w["jezyk"] == "pl" else {"DATA", "DATA_UR", "KWOTA"})
        assert {g["kategoria"] for g in cyframi} == {"DATA", "DATA_UR", "KWOTA"}
        assert all(not re.search(r"\d", g["tekst"]) for g in slownie)
        if w["jezyk"] == "pl":
            pesel = _gold(w, kategoria="PESEL", wartosc_id="pb.pesel#1")[0]["tekst"]
            assert _gold(w, wartosc_id="pb.pesel_slownie#1")[0]["tekst"] == L.cyfry_slownie(pesel, "pl")
        waluta = "GBP" if w["jezyk"] == "en" else None
        for klucz in ("kwota", "odsetki"):          # kwota słownie = liczebnik od kwoty zapisanej cyframi
            c = _gold(w, wartosc_id=f"ctx.{klucz}#1")[0]["tekst"]
            assert _gold(w, wartosc_id=f"ctx.{klucz}_slownie#1")[0]["tekst"] == L.kwota(int(re.sub(r"\D", "", c)), w["jezyk"], waluta)


def test_skroty_po_pelnym_dlugi_dokument_role_nie_sa_gold(warstwa):
    cel, wpisy = warstwa[P.SKROTY_PO_PELNYM]
    for w in wpisy:
        tekst = _tekst(cel, w)
        assert len(tekst) > 3 * P.GRANICA_OKNA_ZNAKI and 10_000 <= len(tekst) <= 27_000
        assert {g["kategoria"] for g in w["gold_tekst"]} == {"OSOBA", "INICJALY"}
        assert {g["encja"] for g in w["gold_tekst"]} == {"a", "b"}
        pelne = [g for g in w["gold_tekst"] if g["wartosc_id"].startswith(("a.pelne#", "b.pelne#"))]
        assert len(pelne) == 2                                                  # pełne imię i nazwisko tylko raz na stronę
        skroty = [g for g in w["gold_tekst"] if "skrot" in g.get("cechy", ())]
        assert len(skroty) >= 25 and {g["kategoria"] for g in skroty} == {"OSOBA", "INICJALY"}
        for g in w["gold_tekst"]:
            assert g["tekst"] not in ("Powód", "Pozwana", "Powoda", "Pozwanej", "the Claimant", "the Defendant")
        rola = {"pl": "Powód", "en": "Claimant", "de": "Kläger", "es": "demandante", "fr": "demandeur"}[w["jezyk"]]
        assert tekst.count(rola) >= 5                                           # rola występuje w tekście, ale nie jest gold


def test_granica_okna_wartosci_przy_granicach_okien(warstwa):
    cel, wpisy = warstwa[P.GRANICA_OKNA]
    for w in wpisy:
        tekst = _tekst(cel, w)
        przy = [g for g in w["gold_tekst"] if "granica_okna" in g.get("cechy", ())]
        assert 4 <= len(przy) <= 6
        przecina = 0
        for g in przy:
            gr, typ, offset, cross = trudne_dlugie.pozycja_przy_granicy(g["start"], g["end"], len(tekst))
            assert abs(offset) <= P.TOLERANCJA_ZNAKI
            assert f"granica_offset:{offset:+d}" in g["cechy"] and f"granica_typ:{typ}" in g["cechy"]
            assert ("przecina_granice" in g["cechy"]) == cross
            przecina += cross
        assert przecina >= 2                        # co najmniej dwie wartości zaczynają się przed granicą i ją przecinają
        assert len(tekst) > max(g["end"] for g in przy)
        assert {g["kategoria"] for g in przy} <= {"OSOBA", "PESEL", "NR_PODATKOWY", "NINO", "DNI", "NIR", "RACHUNEK", "ADRES",
                                                  "EMAIL", "TELEFON"}


def test_dlugie_listy_osob_sto_plus_wartosci(warstwa):
    cel, wpisy = warstwa[P.DLUGIE_LISTY_OSOB]
    assert len({w["typ"] for w in wpisy}) >= 2
    for w in wpisy:
        osoby = {g["encja"] for g in w["gold_tekst"] if g["kategoria"] == "OSOBA" and g["wartosc_id"].endswith(".pelne#1")}
        assert len(osoby) >= 100
        n_adres = sum(1 for g in w["gold_tekst"] if g["kategoria"] == "ADRES")
        n_id = sum(1 for g in w["gold_tekst"] if g["kategoria"] not in ("OSOBA", "ADRES", "EMAIL", "ORGANIZACJA", "DATA"))
        assert (n_adres or n_id or any(g["kategoria"] == "EMAIL" for g in w["gold_tekst"]))
        assert max(n_adres, n_id) < len(osoby)     # adresy / identyfikatory tylko dla części osób


# ============================================================================= gold w pliku (niezależne czytniki) i sanity
_FORMATY_PLIKOW = {"docx": "docx", "pdf": "pdf", "doc": "doc", "xlsx": "xlsx"}


@pytest.fixture(scope="module")
def formaty(tmp_path_factory) -> dict[tuple[str, str], tuple[Path, dict]]:
    """Po jednym dokumencie każdego przypadku w każdym formacie możliwym dla jego typu (języki i typy po kolei)."""
    wynik = {}
    cel = tmp_path_factory.mktemp("formaty")
    for przypadek in H2:
        pary = sorted(trudne.GENERATORY_H2[przypadek])
        fmts = [f for f in ("docx", "pdf", "doc", "xlsx") if any(f in trudne.formaty_dla(*p) for p in pary)]
        for i, fmt in enumerate(fmts):
            kand = [p for p in pary if fmt in trudne.formaty_dla(*p)]
            jezyk, typ = kand[(2 * i + 1) % len(kand)]
            poz = trudne.PozycjaTrudna(f"h-{P.SKROTY[przypadek]}-{jezyk}-{typ}-9{i:03d}", jezyk, typ, fmt, przypadek)
            wynik[(przypadek, fmt)] = (cel, trudne.generuj_dokument_trudny(poz, trudne.ZIARNO_TRUDNE, "test", cel), poz)
    return wynik


def test_formaty_h2_pokrycie(formaty):
    for przypadek in H2:
        assert {f for (p, f) in formaty if p == przypadek} >= {"docx", "pdf", "doc"}
    assert {f for (p, f) in formaty if p == P.DLUGIE_LISTY_OSOB} == {"docx", "pdf", "doc", "xlsx"}


@pytest.mark.parametrize("klucz", [(p, f) for p in H2 for f in ("docx", "pdf", "doc", "xlsx")
                                   if f != "xlsx" or p == P.DLUGIE_LISTY_OSOB])
def test_gold_obecny_w_pliku_niezaleznym_czytnikiem(formaty, klucz):
    cel, w, _ = formaty[klucz]
    plik = cel / w["plik"]
    wartosci = [Wartosc.from_dict(x) for x in w["gold_plik"]]
    assert wartosci and w["ostrzezenia"] == []
    fmt = klucz[1]
    if fmt == "docx":
        with zipfile.ZipFile(plik) as zf:
            teksty = _teksty_miejsc(zf)
            for v in wartosci:
                if v.miejsce == "obraz":        # wartość tylko w obrazie (podpis, logo) – nie ma jej w XML (zależy od ziarna)
                    continue
                assert v.tekst in teksty[v.miejsce], (v.id, v.tekst, v.miejsce)
    elif fmt == "pdf":
        _sprawdz_miejsca(plik, wartosci)
    elif fmt == "xlsx":
        teksty = _teksty_xlsx(plik)
        for v in wartosci:
            assert v.tekst in teksty[v.miejsce], (v.id, v.tekst, v.miejsce)
    else:
        blob = _blob_doc(plik)
        assert all(_w_blobie(v.tekst, blob) for v in wartosci)


@pytest.mark.parametrize("klucz", [(p, f) for p in H2 for f in ("docx", "pdf", "doc", "xlsx")
                                   if f != "xlsx" or p == P.DLUGIE_LISTY_OSOB])
def test_sanity_oryginal_wycieka_idealny_nie(formaty, tmp_path, klucz):
    cel, w, poz = formaty[klucz]
    ws = wartosci_wpisu(w)
    orig = cel / w["plik"]
    a = ocen_plik(orig, orig, ws, leksykon={})
    assert a.status == "OK"
    wyciekly = {x[0] for x in a.wycieki}
    pominiete = set(a.niewykrywalne) | set(a.niejednoznaczne)
    # Inicjały („J.K.”, „K.”) – od H6a dokładny wzorzec z granicami (`normalizacja.wzor_inicjalow`): każda wartość ma regułę.
    bez_reguly = {x.id for x in ws if not zbuduj_regule(x, RegulyWycieku(), set(), [], jezyk=w["jezyk"]).moze_wyciec}
    assert not bez_reguly
    brak = [x.id for x in ws if x.id not in wyciekly and x.id not in pominiete and x.id not in bez_reguly]
    assert not brak, (w["id"], brak[:5])               # oryginał: wyciekają wszystkie wartości możliwe do wycieku
    assert a.wartosci_ocenione >= (len(ws) - len(bez_reguly)) * 0.6
    wyjscie = tmp_path / w["id"]
    wyjscie.mkdir()
    r = trudne.generuj_dokument_trudny(poz, trudne.ZIARNO_TRUDNE, w["split"], wyjscie, maskuj=Maskowanie())
    b = ocen_plik(orig, wyjscie / r["plik"], ws, leksykon={})
    assert b.status == "OK" and b.integralnosc["otwiera_sie"]
    assert not b.wycieki, (w["id"], b.wycieki[:3])     # idealny uczestnik: 0 wycieków


# ============================================================================= poprawki po przeglądzie (fix1)
def _narrator(jezyk: str, seed: int = 1):
    gen, ctx = trudne_dlugie.nowy_kontekst(jezyk, seed)
    a, b = trudne_dlugie._para_stron(gen, ctx, jezyk)
    return trudne_dlugie._Narrator(None, jezyk, a, b, random.Random(seed))


#: wzorce niegramatyczne po przyimku/rodzajniku (role procesowe wstawiane w mianowniku zamiast w przypadku frazy)
ZAKAZANE_ROLE = {
    "de": r"\b(von|mit|wodurch|für|an) (der Kläger|die Beklagte|den Kläger)\b|\b(Auffassung|Ansicht|Vortrag) von\b"
          r"|\bBevollmächtigte von\b",
    "fr": r"\b(à|de) (le|les) |\bde [AEIOUYÀÂÉÈÊÎÔÛ]|\bd'[BCDFGJKLMNPQRSTVWXZ]|\bà la défenderesse la|\bde (la )?le ",
    "es": r"\b(a|de) el\b",
}


@pytest.mark.parametrize("jezyk", ["de", "fr", "es"])
@pytest.mark.parametrize("styl", [x for x, _ in trudne_dlugie._WAGI_STYLI])
def test_role_procesowe_w_poprawnym_przypadku_kazda_kombinacja(jezyk, styl, monkeypatch):
    """Każdy szablon narracji × każdy styl odniesienia: bez „von der Kläger”, „à le demandeur”, „de el demandante”…"""
    monkeypatch.setattr(trudne_dlugie, "_WAGI_STYLI", ((styl, 1),))
    zakaz = re.compile(ZAKAZANE_ROLE[jezyk])
    for seed in range(40):
        n = _narrator(jezyk, seed)
        for szablon in trudne_dlugie._NARRACJA[jezyk]:
            tekst, sloty = n.zdanie(szablon)
            plaski = tekst.format(**{k: g.tekst for k, g in sloty.items()})
            assert not zakaz.search(plaski), plaski
            assert not re.search(r"\{|\}|_(?:de|a|gen|dat|akk)\b", plaski), plaski


@pytest.mark.parametrize("jezyk,szablon_zawiera,oczekiwane", [
    ("de", "Nach Auffassung {RA_gen}", "Nach Auffassung des Klägers hat"),
    ("de", "Nach Ansicht {RB_gen}", "Nach Ansicht der Beklagten gibt"),
    ("de", "mit {A_dat} und {B_dat}", "mit dem Kläger und der Beklagten führten"),
    ("de", "er habe {B_akk}", "er habe die Beklagte mehrfach"),
    ("de", "wodurch {A_dat}", "wodurch dem Kläger ein Schaden"),
    ("de", "dass {A_akk} und {B_akk}", "dass den Kläger und die Beklagte ein Vertrag"),
    ("fr", "préjudice {A_a}", "préjudice au demandeur."),
    ("fr", "la demande {A_de}", "la demande du demandeur et"),
    ("fr", "L'avocat {RB_de}", "L'avocat de la défenderesse a"),
    ("fr", "reçu {A_de}", "a reçu du demandeur un acompte"),
    ("es", "perjuicio {A_a}", "perjuicio al demandante."),
    ("es", "pretensión {A_de}", "pretensión del demandante y"),
    ("es", "En opinión {RA_de}", "En opinión del demandante,"),
    ("es", "requirió en varias ocasiones {B_a}", "requirió en varias ocasiones a la demandada el"),
])
def test_role_procesowe_frazy_z_tabeli(jezyk, szablon_zawiera, oczekiwane, monkeypatch):
    monkeypatch.setattr(trudne_dlugie, "_WAGI_STYLI", (("rola", 1),))
    n = _narrator(jezyk)
    szablon = next(z for z in trudne_dlugie._NARRACJA[jezyk] if szablon_zawiera in z)
    tekst, sloty = n.zdanie(szablon)
    assert not sloty and oczekiwane in tekst, tekst


def test_role_procesowe_w_dokumentach_bez_bledow_gramatycznych(warstwa):
    for przypadek in (P.SKROTY_PO_PELNYM, P.GRANICA_OKNA):
        cel, wpisy = warstwa[przypadek]
        for w in wpisy:
            if w["jezyk"] in ZAKAZANE_ROLE:
                assert not re.search(ZAKAZANE_ROLE[w["jezyk"]], _tekst(cel, w)), (w["id"])


def test_kropka_po_skrocie_nie_jest_podwojona(warstwa):
    for przypadek in (P.SKROTY_PO_PELNYM, P.GRANICA_OKNA, P.DLUGIE_LISTY_OSOB):
        cel, wpisy = warstwa[przypadek]
        for w in wpisy:
            assert not re.search(r"(?<!\.)\.\.(?!\.)", _tekst(cel, w)), w["id"]


def test_naglowek_listy_zawiera_firme_raz_bez_podwojnej_kropki(warstwa):
    cel, wpisy = warstwa[P.DLUGIE_LISTY_OSOB]
    for w in wpisy:
        firmy = [g for g in w["gold_tekst"] if g["kategoria"] == "ORGANIZACJA"]
        assert len(firmy) == 1
        wiersz = next(l for l in _tekst(cel, w).splitlines() if firmy[0]["tekst"] in l)
        assert wiersz.count(firmy[0]["tekst"]) == 1 and not wiersz.endswith("..") and "–" not in wiersz.split(firmy[0]["tekst"])[0][-3:]


def test_zdrobnienia_bez_form_grzecznosciowych_w_de_en_fr(warstwa):
    cel, wpisy = warstwa[P.ZDROBNIENIA]
    for w in wpisy:
        tekst = _tekst(cel, w)
        if w["jezyk"] in ("de", "en", "fr"):
            for g in w["gold_tekst"]:
                if "zdrobnienie" in g.get("cechy", ()) and " " not in g["tekst"]:
                    przed = tekst[max(0, g["start"] - 8):g["start"]]
                    assert not re.search(r"(Frau|Herr|Ms|Mr|Madame|Monsieur) $", przed), (w["id"], przed)


def test_pozyczka_en_plec_i_pl_role_zenskie(warstwa):
    cel, wpisy = warstwa[P.LICZBY_SLOWNIE]
    for w in wpisy:
        tekst = _tekst(cel, w)
        if w["jezyk"] == "en":
            assert "he or she" not in tekst and re.search(r"declares that (he|she) was born", tekst)
        if w["jezyk"] == "pl":
            if "urodziła się" in tekst:
                assert "Pożyczkobiorczyni oświadcza" in tekst and "Pożyczkobiorca" not in tekst
            else:
                assert "Pożyczkobiorca oświadcza" in tekst and "Pożyczkobiorczyni" not in tekst


@pytest.mark.parametrize("jezyk", L.JEZYKI)
def test_stanowiska_w_listach_maja_feminatywy(jezyk):
    for pary in (trudne_dlugie._LISTY[jezyk]["stanowiska"], trudne_jezyk._ROLE_TABELI[jezyk]):
        assert len(pary) == 6 and all(len(p) == 2 for p in pary)
        if jezyk != "en":
            assert sum(m != k for m, k in pary) >= 3


def test_stanowiska_pl_dobrane_wg_plci():
    pary = dict(trudne_dlugie._LISTY["pl"]["stanowiska"])
    assert pary["księgowy"] == "księgowa" and pary["kierownik zmiany"] == "kierowniczka zmiany"


def test_blokada_osob_publicznych_rozszerzona_i_stosowana(warstwa):
    assert ("tomasz", "lis") in ZABLOKOWANE
    for para in [("remigiusz", "mróz"), ("peter", "cook"), ("elijah", "wood"), ("maurice", "chevalier")]:
        assert para in ZABLOKOWANE
    zablokowane_pelne = {f"{i} {n}" for i, n in ZABLOKOWANE}
    for przypadek in H2:
        cel, wpisy = warstwa[przypadek]
        for w in wpisy:
            for g in w["gold_tekst"]:
                assert g["tekst"].lower() not in zablokowane_pelne, (w["id"], g["tekst"])
    assert trudne_jezyk.bez_blokady is not None


def test_es_identyfikator_dni_ma_format_dni(warstwa):
    for przypadek in H2:
        cel, wpisy = warstwa[przypadek]
        for w in wpisy:
            if w["jezyk"] != "es":
                continue
            for g in w["gold_tekst"]:
                if g["kategoria"] == "DNI":
                    assert re.fullmatch(r"\d{8}[A-Z]", g["tekst"]), (w["id"], g["tekst"])


# ----------------------------------------------------------------------------- wypełniacz granicy okna
@pytest.mark.parametrize("jezyk", L.JEZYKI)
def test_pula_formulek_wypelniacza(jezyk):
    wszystkie = trudne_wypelniacz.wszystkie_zdania(jezyk)
    assert len(trudne_wypelniacz.FORMULKI[jezyk]) >= 16 and len(wszystkie) >= 30
    for z in wszystkie:
        assert z[0].isupper() and z.endswith(".") and not re.search(r"\d|[<>|{}]|  ", z), z
        if jezyk != "de":                                    # nazwy własne: brak wielkich liter poza początkiem (DE: rzeczowniki)
            assert not re.search(r"\s[A-ZĄĆĘŁŃÓŚŹŻÀÂÉÈÊÎÔÛ]", z), z


def _rozloz_na_zdania(akapit: str, zdania: frozenset[str]) -> list[str] | None:
    if not akapit:
        return []
    for z in zdania:
        if akapit == z:
            return [z]
        if akapit.startswith(z + " "):
            reszta = _rozloz_na_zdania(akapit[len(z) + 1:], zdania)
            if reszta is not None:
                return [z] + reszta
    return None


@pytest.mark.parametrize("jezyk", L.JEZYKI)
def test_wypelniacz_zdania_z_puli_bez_powtorzen_w_pasmie(jezyk):
    zdania = trudne_wypelniacz.wszystkie_zdania(jezyk)
    rng = random.Random(7)
    for dl_min, szerokosc in [(60, 40), (100, 6), (220, 12), (400, 8), (650, 50), (130, 100)]:
        for _ in range(15):
            akapit = trudne_wypelniacz.akapit_w_pasie(rng, jezyk, dl_min, dl_min + szerokosc)
            assert dl_min <= len(akapit) <= dl_min + szerokosc
            czesci = _rozloz_na_zdania(akapit, zdania)
            assert czesci is not None, akapit                              # każde zdanie pochodzi z puli
            assert len(czesci) == len(set(czesci)), akapit                 # w akapicie żadne zdanie się nie powtarza
            assert not re.search(r"\d", akapit)                            # wypełniacz bez cyfr


@pytest.mark.parametrize("jezyk", L.JEZYKI)
def test_granica_okna_akapity_bez_wartosci_to_zdania_z_pul(jezyk):
    """Akapity bez wartości gold (wypełniacz, zdania neutralne) składają się wyłącznie ze zdań z puli – bez „sałatki słów”."""
    dozwolone = trudne_wypelniacz.wszystkie_zdania(jezyk) | frozenset(trudne_dlugie._NEUTRALNE[jezyk])
    role = [r.lower() for para in trudne_dlugie._ROLE[jezyk] for r in (para.values() if isinstance(para, dict) else [para])]
    for seed in range(12):
        wynik, _, _ = trudne_dlugie._buduj_granica(jezyk, "pismo_dlugie", seed)
        for e in wynik.dokument.elementy:
            if e.rodzaj == "akapit" and all(isinstance(f, str) for f in e.fragmenty):
                akapit = "".join(e.fragmenty)
                if any(r in akapit.lower() for r in role):         # narracja, w której strony występują tylko jako role
                    continue
                assert _rozloz_na_zdania(akapit, dozwolone) is not None, akapit


@pytest.mark.parametrize("jezyk", L.JEZYKI)
def test_granica_okna_wiele_ziaren_trafia_w_pasmo(jezyk):
    for seed in range(40):
        wynik, _, _ = trudne_dlugie._buduj_granica(jezyk, "pismo_dlugie", seed)
        assert wynik.dokument.elementy
