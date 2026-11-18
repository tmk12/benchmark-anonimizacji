"""Warstwa trudnych przypadków, zadanie H5 (spec §11 pkt 4): identyfikacja pośrednia – `posrednie_funkcja_firma`,
`posrednie_rzadka_choroba`, `posrednie_wiek_miejscowosc`, `posrednie_dzialka_gps`. Rejestr, plan, generatory (osoba-cel
nienazwana, składnik raz w dokumencie, bez nowych kategorii), pole manifestu `posrednie` i jego walidacja, obecność gold
i składników w pliku (niezależne czytniki: zipfile, pypdfium2, olefile), miara w sędziach tekstowym i plikowym (oryginał – 0%
przerwanych, idealny – 100% i 0 wycieków, „tylko kategorie” – przerwane dokładnie kombinacje ze składnikiem gold), wyłączenie
składników spoza gold z nadmiarowego maskowania, rekordy `pbench.ocen` i agregacja z przedziałem ufności. Runda poprawek 1
przeglądu H5: działka i GPS – osobne kombinacje jednoskładnikowe (I1), widoczność liczona na rdzeniu składnika (M1), GPS
w obszarach lądowych (M3), pary funkcja – forma prawna, elizja FR, biernik PL, numer tytułu EN (M4, M5), przypadki punktowane
(M6), błąd sędziego = kombinacje nieprzerwane (M7)."""
from __future__ import annotations

import json
import os
import re
import zipfile
from collections import Counter
from pathlib import Path

import pytest
from test_render_docx import _teksty_miejsc
from test_render_inne import _blob_doc, _w_blobie
from test_render_pdf import _sprawdz_miejsca

from pbench import ocen, posrednie, przypadki as P, trudne, trudne_posrednie as TP
from pbench.dane.wspolne import slownik
from pbench.model import Element, KATEGORIE, Wartosc, Wykrycie
from pbench.odmiana_pl import odmien
from pbench.sedzia.plik import ocen_plik
from pbench.sedzia.sanity import Maskowanie, wartosci_wpisu
from pbench.sedzia.tekst import RegulyWycieku, gold_z_wpisu, ocen_tekst, zakresy_skladnikow
from pbench.trudne_wspolne import JEZYKI

H5 = P.H5
#: Kategorie gold, którymi mogą być składniki kombinacji (kategorie trzonu – bez nowych kategorii).
KATEGORIE_SKLADNIKOW_GOLD = {"ORGANIZACJA", "MIEJSCOWOSC", "ZDROWIE", "ADRES", "KSIEGA_WIECZYSTA"}
ROLE_SPOZA_GOLD = {"funkcja", "choroba", "wiek", "rok_urodzenia", "szkola", "dzialka", "gps"}
FORMATY = ("docx", "pdf", "doc")
NASIONA = range(12)


def _manifest(cel: Path) -> list[dict]:
    return [json.loads(w) for w in (cel / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]


def _tekst_dok(wynik) -> str:
    return "\n".join("".join(f if isinstance(f, str) else f.tekst for f in e.fragmenty) for e in wynik.dokument.elementy)


@pytest.fixture(scope="module", autouse=True)
def _cache_ocr(tmp_path_factory):
    """Wspólny katalog pamięci OCR modułu (oryginał PDF czytany raz dla kilku uczestników)."""
    stary = os.environ.get("PBENCH_OCR_CACHE")
    os.environ["PBENCH_OCR_CACHE"] = str(tmp_path_factory.mktemp("ocr"))
    yield
    if stary is None:
        os.environ.pop("PBENCH_OCR_CACHE", None)
    else:
        os.environ["PBENCH_OCR_CACHE"] = stary


# ============================================================================= rejestr i plan
def test_rejestr_h5():
    assert H5 == (P.POSREDNIE_FUNKCJA_FIRMA, P.POSREDNIE_RZADKA_CHOROBA, P.POSREDNIE_WIEK_MIEJSCOWOSC, P.POSREDNIE_DZIALKA_GPS)
    assert set(H5) == P.POSREDNIE and {P.SKROTY[p] for p in H5} == {"ff", "rc", "wm", "dg"}
    assert len(set(P.SKROTY.values())) == len(P.SKROTY) == len(P.PRZYPADKI)       # każdy przypadek ma generator i skrót
    assert not set(H5) & (set(P.H1) | set(P.H2) | set(P.H3) | set(P.H4A) | set(P.H4B))
    for przypadek in H5:
        assert przypadek in trudne.GENERATORY_H5 and {j for j, _ in trudne._pary(przypadek)} == set(JEZYKI)


@pytest.mark.parametrize("przypadek", H5)
def test_plan_h5(przypadek):
    plan = trudne.zaplanuj_przypadek(przypadek, 40)
    assert len(plan) == 40 and plan == trudne.zaplanuj_przypadek(przypadek, 40)
    assert {p.jezyk for p in plan} == set(JEZYKI)
    assert {p.format for p in plan} == {"docx", "pdf", "doc"}                    # bez rtf/odt (tylko `formaty_rtf_odt`)
    assert all(re.fullmatch(rf"h-{P.SKROTY[przypadek]}-{p.jezyk}-{p.typ}-\d{{4}}", p.id) for p in plan)
    split = trudne.przydziel_split(plan)
    assert sum(1 for s in split.values() if s == "dev") in range(6, 11)
    inne = {p.id for pr in (*P.H1, *P.H2) for p in trudne.zaplanuj_przypadek(pr, 40)}
    assert not inne & {p.id for p in plan}


# ============================================================================= generatory (bez renderowania)
def _wszystkie():
    for przypadek in H5:
        for (jezyk, typ), f in sorted(trudne.GENERATORY_H5[przypadek].items()):
            for seed in NASIONA:
                yield przypadek, jezyk, typ, seed, f(jezyk, typ, seed * 7919 + 11)


@pytest.fixture(scope="module")
def generowane() -> list[tuple]:
    return list(_wszystkie())


def test_osoba_cel_nienazwana(generowane):
    for przypadek, jezyk, typ, seed, (wynik, _, dod) in generowane:
        tekst = _tekst_dok(wynik)
        slowa = set(re.findall(r"\w+", tekst))
        osoby = [f.tekst for e in wynik.dokument.elementy for f in e.fragmenty if not isinstance(f, str) and f.kategoria == "OSOBA"]
        assert dod["cele"] and osoby, (przypadek, jezyk, seed)          # inne osoby są nazwane (zwykłe gold)
        for o in dod["cele"]:
            for czlon in re.findall(r"\w+", f"{o.imie} {o.nazwisko}"):
                if len(czlon) >= 3 and czlon[0].isupper():
                    assert czlon not in slowa, (przypadek, jezyk, seed, czlon)
            i, n = o.imie[0], o.nazwisko.split()[0][0]
            assert not re.search(rf"(?<!\w)(?:{i}{n}|{i}\.\s?{n}\.)(?!\w)", tekst), (przypadek, jezyk, seed)
            assert o.pelne_imie not in tekst and all(o.pelne_imie not in x for x in osoby)


def test_skladniki_raz_w_dokumencie_i_bez_nowych_kategorii(generowane):
    for przypadek, jezyk, typ, seed, (wynik, _, dod) in generowane:
        tekst = _tekst_dok(wynik).casefold()
        kategorie = {f.id: f.kategoria for e in wynik.dokument.elementy for f in e.fragmenty if not isinstance(f, str)}
        assert set(kategorie.values()) <= KATEGORIE
        assert dod["posrednie"] and all(k["rodzaj"] == przypadek for k in dod["posrednie"])
        for k in dod["posrednie"]:
            assert len(k["skladniki"]) >= 2 or k["skladniki"][0]["rola"] in posrednie.ROLE_JEDNOSKLADNIKOWE
            assert len({s["rola"] for s in k["skladniki"]}) == len(k["skladniki"])
            for s in k["skladniki"]:
                assert tekst.count(s["tekst"].casefold()) == 1, (przypadek, jezyk, seed, s)
                assert s["rdzen"] and posrednie.zakresy_rdzenia(s["tekst"], s["rdzen"]) is not None, s
                if s["wartosc_id"] is None:
                    assert s["rola"] in ROLE_SPOZA_GOLD and s["miejsce"] == "tresc"
                else:
                    assert kategorie[s["wartosc_id"]] in KATEGORIE_SKLADNIKOW_GOLD, s


def test_generatory_deterministyczne():
    for przypadek in H5:
        for (jezyk, typ), f in sorted(trudne.GENERATORY_H5[przypadek].items()):
            a, b = f(jezyk, typ, 5), f(jezyk, typ, 5)
            assert a[0].dokument.to_json() == b[0].dokument.to_json() and a[2]["posrednie"] == b[2]["posrednie"]


def _nieruchomosc_w_gold(wynik) -> bool:
    """Dokument `posrednie_dzialka_gps` wskazuje nieruchomość także zwykłym gold (księga wieczysta albo adres)."""
    return any(not isinstance(f, str) and f.id.startswith("nieruchomosc.") and f.kategoria in ("ADRES", "KSIEGA_WIECZYSTA")
               for e in wynik.dokument.elementy for f in e.fragmenty)


def test_rozklad_skladnikow(generowane):
    licz: Counter = Counter()
    for przypadek, jezyk, typ, seed, (wynik, _, dod) in generowane:
        for k in dod["posrednie"]:
            role = {s["rola"] for s in k["skladniki"]}
            licz[(przypadek, frozenset(role))] += 1
            licz[(przypadek, "bez_gold" if all(s["wartosc_id"] is None for s in k["skladniki"]) else "z_gold")] += 1
            if przypadek == P.POSREDNIE_DZIALKA_GPS and role == {"gps"}:
                licz[("gps", "dms" if "°" in k["skladniki"][0]["tekst"] else "dziesietne")] += 1
        if przypadek == P.POSREDNIE_DZIALKA_GPS:
            licz[("dg", _nieruchomosc_w_gold(wynik))] += 1
            assert [(k["id"], [s["rola"] for s in k["skladniki"]]) for k in dod["posrednie"]] == [("k1", ["dzialka"]),
                                                                                                 ("k2", ["gps"])]
    # działka i GPS: dwie kombinacje jednoskładnikowe spoza gold (I1); nieruchomość wskazana też zwykłym gold (KW/adres) w części
    # dokumentów; GPS w obu zapisach
    n_dg = 5 * len(NASIONA)
    assert licz[(P.POSREDNIE_DZIALKA_GPS, frozenset({"dzialka"}))] == licz[(P.POSREDNIE_DZIALKA_GPS, frozenset({"gps"}))] == n_dg
    assert licz[(P.POSREDNIE_DZIALKA_GPS, "bez_gold")] == 2 * n_dg and licz[(P.POSREDNIE_DZIALKA_GPS, "z_gold")] == 0
    assert licz[("dg", True)] >= 20 and licz[("dg", False)] >= 20
    assert licz[("gps", "dms")] >= 20 and licz[("gps", "dziesietne")] >= 20
    # pozostałe przypadki: zawsze ze składnikiem gold; warianty kontekstu choroby i funkcji z adresem budowy
    for przypadek in (P.POSREDNIE_FUNKCJA_FIRMA, P.POSREDNIE_RZADKA_CHOROBA, P.POSREDNIE_WIEK_MIEJSCOWOSC):
        assert licz[(przypadek, "bez_gold")] == 0
    assert licz[(P.POSREDNIE_RZADKA_CHOROBA, frozenset({"choroba", "firma", "miejscowosc"}))] >= 10
    assert licz[(P.POSREDNIE_RZADKA_CHOROBA, frozenset({"choroba", "firma", "rok_urodzenia"}))] >= 10
    assert licz[(P.POSREDNIE_RZADKA_CHOROBA, frozenset({"choroba", "szkola", "miejscowosc"}))] >= 20
    assert licz[(P.POSREDNIE_FUNKCJA_FIRMA, frozenset({"funkcja", "adres"}))] >= 5
    assert licz[(P.POSREDNIE_WIEK_MIEJSCOWOSC, frozenset({"wiek", "miejscowosc"}))] == 5 * len(NASIONA)


def test_wiek_i_rocznik_zgodne_z_osoba_cel(generowane):
    for przypadek, jezyk, typ, seed, (wynik, _, dod) in generowane:
        for k in dod["posrednie"]:
            for s in k["skladniki"]:
                if s["rola"] == "wiek":
                    lata = TP._wiek(dod["cele"][0], wynik.kontekst.daty["dok"])
                    assert re.search(rf"(?<!\d){lata}(?!\d)", s["tekst"]) and lata >= 18
                if s["rola"] == "rok_urodzenia":
                    assert str(dod["cele"][0].data_ur.year) in s["tekst"]
                    assert TP._wiek(dod["cele"][0], wynik.kontekst.daty["dok"]) <= TP.WIEK_PRACY


@pytest.mark.parametrize("jezyk", JEZYKI)
def test_male_miejscowosci_spoza_slownika_miast(jezyk):
    miasta = {m.split("|")[0] for m in slownik(jezyk, "miejscowosci")}
    pary = TP.MALE_MIEJSCOWOSCI[jezyk]
    assert len(pary) >= 15 and len({w for w, _ in pary}) == len(pary)
    assert not {w for w, _ in pary} & miasta and not {w for w, _ in pary} & {g for _, g in pary}
    if jezyk == "fr":
        assert all(w[0].lower() not in "aeiouéèêh" for w, _ in pary)     # „du hameau de …” bez elizji


#: Zakresy (szerokość, długość) obejmujące cały kraj dokumentu (EN – Wielka Brytania) – prostokąty lądowe muszą w nich leżeć.
_KRAJ = {"pl": ((49.0, 54.9), (14.1, 24.2)), "en": ((49.9, 55.8), (-5.8, 1.8)), "de": ((47.2, 55.1), (5.8, 15.1)),
         "es": ((36.0, 43.8), (-9.3, 3.4)), "fr": ((42.3, 51.1), (-4.8, 8.3))}


def _w_obszarach(szer: float, dl: float, jezyk: str) -> bool:
    return any(s0 <= szer <= s1 and d0 <= dl <= d1 for (s0, s1), (d0, d1) in TP.OBSZARY_LADOWE[jezyk])


def _dms_na_stopnie(zapis: str) -> tuple[float, float]:
    def jedna(x: str) -> float:
        m = re.fullmatch(r"(\d+)°(\d+)′([\d.]+)″([NSEW])", x)
        v = int(m[1]) + int(m[2]) / 60 + float(m[3]) / 3600
        return -v if m[4] in "SW" else v
    a, b = zapis.split(" ")
    return jedna(a), jedna(b)


@pytest.mark.parametrize("jezyk", JEZYKI)
def test_gps_w_obszarach_ladowych_kraju(jezyk):
    import random
    obszary = TP.OBSZARY_LADOWE[jezyk]
    (k0, k1), (l0, l1) = _KRAJ[jezyk]
    assert len(obszary) >= 3 and all(k0 <= s0 < s1 <= k1 and l0 <= d0 < d1 <= l1 for (s0, s1), (d0, d1) in obszary)
    rng = random.Random(1)
    for _ in range(50):
        tekst, rdzen = TP.gps(rng, jezyk, dms=False)
        szer, dl = map(float, tekst.split(", "))
        assert _w_obszarach(szer, dl, jezyk) and list(rdzen) == tekst.split(", ")
        dms, rdzen = TP.gps(rng, jezyk, dms=True)
        assert re.fullmatch(r"\d{1,2}°\d{2}′\d{2}\.\d″[NS] \d{1,3}°\d{2}′\d{2}\.\d″[EW]", dms), dms
        assert _w_obszarach(*_dms_na_stopnie(dms), jezyk) and len(rdzen) == 6
        assert all(re.fullmatch(r"\d+(?:\.\d)?", x) for x in rdzen)       # same liczby – bez liter półkul i symboli


def test_gps_w_dokumentach_w_obszarach_ladowych(generowane):
    for przypadek, jezyk, typ, seed, (wynik, _, dod) in generowane:
        for k in dod["posrednie"]:
            for s in k["skladniki"]:
                if s["rola"] == "gps":
                    t = s["tekst"]
                    punkt = _dms_na_stopnie(t) if "°" in t else tuple(map(float, t.split(", ")))
                    assert _w_obszarach(*punkt, jezyk), (jezyk, t)


def test_kombinacje_ze_skladacza():
    from pbench.skladacz import G, Skladacz, Skladnik
    s = Skladacz("pl")
    s.akapit("Opis: {a} {b}.", a=Skladnik("k1", "funkcja", "Prezes Zarządu"),
             b=Skladnik("k1", "firma", G("Delta sp. z o.o.", "ORGANIZACJA", "f.nazwa", "f")))
    assert TP.kombinacje(s, P.POSREDNIE_FUNKCJA_FIRMA) == [{"id": "k1", "rodzaj": P.POSREDNIE_FUNKCJA_FIRMA, "skladniki": [
        {"id": "k1.funkcja", "rola": "funkcja", "tekst": "Prezes Zarządu", "miejsce": "tresc", "wartosc_id": None,
         "rdzen": ["Prezes Zarządu"]},
        {"id": "k1.firma", "rola": "firma", "tekst": "Delta sp. z o.o.", "miejsce": "tresc", "wartosc_id": "f.nazwa#1",
         "rdzen": ["Delta sp. z o.o."]}]}]
    assert [f if isinstance(f, str) else f.kategoria for f in s.elementy[0].fragmenty] == \
        ["Opis: Prezes Zarządu ", "ORGANIZACJA", "."]                     # składnik spoza gold to zwykły tekst
    with pytest.raises(ValueError):                                        # składnik spoza gold tylko w treści
        s.naglowek("{a}", a=Skladnik("k2", "wiek", "47-letni"))


# ============================================================================= manifest i walidacja
@pytest.fixture(scope="module")
def warstwa(tmp_path_factory) -> dict[str, tuple[Path, list[dict]]]:
    wynik = {}
    for przypadek in H5:
        cel = tmp_path_factory.mktemp(przypadek)
        wynik[przypadek] = (cel, trudne.zbuduj_przypadek(cel, przypadek, 24 if przypadek == P.POSREDNIE_RZADKA_CHOROBA else 12, procesy=1,
                                                    formaty=("docx", "pdf")))   # rocznik w ok. 1/4 próbki: 24 dokumenty
    return wynik


@pytest.mark.parametrize("przypadek", H5)
def test_manifest_h5(warstwa, przypadek):
    cel, wpisy = warstwa[przypadek]
    assert len(wpisy) >= 8 and wpisy == _manifest(cel)
    for w in wpisy:
        assert w["warstwa"] == "trudne" and w["przypadki"] == [przypadek] and w["ostrzezenia"] == []
        posrednie.sprawdz(w)
        tekst = (cel / w["plik_txt"]).read_text(encoding="utf-8")
        miejsca = {g["wartosc_id"]: (g["miejsce"], g["tekst"]) for g in w["gold_tekst"]}
        assert w["posrednie"]
        for k in w["posrednie"]:
            assert list(k) == list(posrednie.KLUCZE_KOMBINACJI) and k["rodzaj"] == przypadek
            for s in k["skladniki"]:
                assert list(s) == list(posrednie.KLUCZE_SKLADNIKA) and s["id"] == f"{k['id']}.{s['rola']}"
                assert posrednie.zakresy_rdzenia(s["tekst"], s["rdzen"]) is not None
                if s["wartosc_id"] is None:
                    assert len(posrednie.wystapienia(tekst, s["tekst"])) == 1 and s["miejsce"] == "tresc"
                    assert not any(g["start"] < e and s0 < g["end"] for g in w["gold_tekst"]
                                   for s0, e in posrednie.wystapienia(tekst, s["tekst"]))      # spoza gold: nie nachodzi na gold
                else:
                    assert miejsca[s["wartosc_id"]] == (s["miejsce"], s["tekst"])


def test_inne_przypadki_maja_puste_posrednie_a_trzon_brak_pola(tmp_path):
    w = trudne.zbuduj_przypadek(tmp_path, P.PARAFY, 2, formaty=("docx",))
    assert all(x["posrednie"] == [] for x in w)
    posrednie.sprawdz({"id": "trzon"})                                    # trzon: pole nieobecne – poprawne


def test_walidacja_posrednich():
    gold = [{"wartosc_id": "f.nazwa#1", "tekst": "Delta sp. z o.o."}]
    dobra = {"id": "k1", "rodzaj": P.POSREDNIE_FUNKCJA_FIRMA, "skladniki": [
        {"id": "k1.funkcja", "rola": "funkcja", "tekst": "Prezes", "miejsce": "tresc", "wartosc_id": None, "rdzen": ["Prezes"]},
        {"id": "k1.firma", "rola": "firma", "tekst": "Delta sp. z o.o.", "miejsce": "tresc", "wartosc_id": "f.nazwa#1",
         "rdzen": ["Delta sp. z o.o."]}]}
    posrednie.sprawdz({"gold_tekst": gold, "posrednie": [dobra]})
    # działka i GPS: kombinacje jednoskładnikowe (I1); inne role – nadal co najmniej dwa składniki
    dzialka = {"id": "k2", "rodzaj": P.POSREDNIE_DZIALKA_GPS, "skladniki": [
        {"id": "k2.dzialka", "rola": "dzialka", "tekst": "82/26, obręb 0021", "miejsce": "tresc", "wartosc_id": None,
         "rdzen": ["82/26", "0021"]}]}
    gps = {"id": "k3", "rodzaj": P.POSREDNIE_DZIALKA_GPS, "skladniki": [
        {"id": "k3.gps", "rola": "gps", "tekst": "52°13′47.3″N 21°00′44.4″E", "miejsce": "tresc", "wartosc_id": None,
         "rdzen": ["52", "13", "47.3", "21", "00", "44.4"]}]}
    posrednie.sprawdz({"gold_tekst": gold, "posrednie": [dobra, dzialka, gps]})
    zle = [
        {**dobra, "rodzaj": "odmiana_nazwisk"},
        {**dobra, "skladniki": dobra["skladniki"][:1]},
        {**dobra, "dodatkowe": 1},
        {**dobra, "skladniki": [dobra["skladniki"][0], {**dobra["skladniki"][1], "wartosc_id": "inna#1"}]},
        {**dobra, "skladniki": [dobra["skladniki"][0], {**dobra["skladniki"][1], "tekst": "Delta"}]},
        {**dobra, "skladniki": [dobra["skladniki"][0], {**dobra["skladniki"][0]}]},
        {**dobra, "skladniki": [dobra["skladniki"][0], {k: v for k, v in dobra["skladniki"][1].items() if k != "miejsce"}]},
        {**dobra, "skladniki": [dobra["skladniki"][0], {**dobra["skladniki"][1], "tekst": " "}]},
        {**dobra, "skladniki": []},
        {**dobra, "skladniki": [{**dobra["skladniki"][0], "rola": "wiek"}]},             # jeden składnik – nie działka/GPS
        {**dobra, "skladniki": [dobra["skladniki"][0], {k: v for k, v in dobra["skladniki"][1].items() if k != "rdzen"}]},
        {**dobra, "skladniki": [dobra["skladniki"][0], {**dobra["skladniki"][1], "rdzen": []}]},
        {**dobra, "skladniki": [dobra["skladniki"][0], {**dobra["skladniki"][1], "rdzen": ["Gamma"]}]},   # spoza tekstu
        {**dobra, "skladniki": [dobra["skladniki"][0], {**dobra["skladniki"][1], "rdzen": ["o.o.", "Delta"]}]},  # kolejność
        {**dobra, "skladniki": [dobra["skladniki"][0], {**dobra["skladniki"][1], "rdzen": ["Delta", " "]}]},    # bez liter
        {**dobra, "skladniki": [dobra["skladniki"][0], {**dobra["skladniki"][1], "rdzen": "Delta"}]},
    ]
    for z in zle:
        with pytest.raises(ValueError):
            posrednie.sprawdz({"gold_tekst": gold, "posrednie": [z]})
    with pytest.raises(ValueError):
        posrednie.sprawdz({"gold_tekst": gold, "posrednie": [dobra, dobra]})      # powtórzony identyfikator


def test_generacja_h5_deterministyczna(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    for pr in (P.POSREDNIE_DZIALKA_GPS, P.POSREDNIE_FUNKCJA_FIRMA):
        trudne.zbuduj_przypadek(a / pr, pr, 4, procesy=1, formaty=("docx", "pdf"))
        trudne.zbuduj_przypadek(b / pr, pr, 4, procesy=2, formaty=("docx", "pdf"))
        assert (a / pr / "manifest.jsonl").read_bytes() == (b / pr / "manifest.jsonl").read_bytes()
        for w in _manifest(a / pr):
            assert (a / pr / w["plik"]).read_bytes() == (b / pr / w["plik"]).read_bytes()
            assert (a / pr / w["plik_txt"]).read_bytes() == (b / pr / w["plik_txt"]).read_bytes()


def test_cli_h5(tmp_path, capsys):
    assert trudne.main(["--cel", str(tmp_path), "--przypadek", P.POSREDNIE_WIEK_MIEJSCOWOSC, "--n", "4", "--formaty", "docx"]) == 0
    wpisy = _manifest(tmp_path)
    assert f"{P.POSREDNIE_WIEK_MIEJSCOWOSC} dokumentów: {len(wpisy)} " in capsys.readouterr().out and wpisy


# ============================================================================= sędzia tekstowy
def _wykrycia(spany) -> list[Wykrycie]:
    return [Wykrycie(s, e, "X", 1.0) for s, e in spany]


def _ma_gold(k: dict) -> bool:
    return any(s["wartosc_id"] is not None for s in k["skladniki"])


def test_sedzia_tekstowy_sanity(warstwa):
    r = RegulyWycieku()
    rozroznia: Counter = Counter()
    for przypadek in H5:
        cel, wpisy = warstwa[przypadek]
        for w in wpisy:
            tekst = (cel / w["plik_txt"]).read_text(encoding="utf-8")
            gold = gold_z_wpisu(w)
            kat = _wykrycia((g.start, g.end) for g in gold)
            idealne = kat + _wykrycia(zakresy_skladnikow(w["posrednie"], tekst))
            o = ocen_tekst(gold, [], tekst, r, posrednie=w["posrednie"])
            assert [k["przerwana"] for k in o.posrednie] == [False] * len(w["posrednie"])     # oryginał: nic nie przerwane
            assert all(k["widoczne"] == [s["id"] for s in kk["skladniki"]] for k, kk in zip(o.posrednie, w["posrednie"]))
            i = ocen_tekst(gold, idealne, tekst, r, posrednie=w["posrednie"])
            assert [k["przerwana"] for k in i.posrednie] == [True] * len(w["posrednie"]) and not i.wycieki
            assert i.fp_znaki == 0 and i.fp_spany == 0         # składniki spoza gold – poza nadmiarowym maskowaniem
            bez = ocen_tekst(gold, idealne, tekst, r)
            assert bez.posrednie is None and (bez.fp_znaki > 0) == bool(zakresy_skladnikow(w["posrednie"], tekst))
            rozroznia["fp"] += bez.fp_znaki > 0                # bez pola `posrednie` składniki byłyby nadmiarowe
            c = ocen_tekst(gold, kat, tekst, r, posrednie=w["posrednie"])
            assert not c.wycieki
            for k, kk in zip(c.posrednie, w["posrednie"]):
                assert k["przerwana"] == _ma_gold(kk), (w["id"], k)
                rozroznia[k["przerwana"]] += 1
    assert rozroznia[True] and rozroznia[False] and rozroznia["fp"]   # „tylko kategorie” przerywa część kombinacji, nie wszystkie


def test_sedzia_tekstowy_czesciowe_maskowanie_i_regula_liczb():
    tekst = "Drugim uczestnikiem był 47-letni mieszkaniec wsi Zawady, a obok Prezes Zarządu firmy."
    k = [{"id": "k1", "rodzaj": P.POSREDNIE_WIEK_MIEJSCOWOSC, "skladniki": [
        {"id": "k1.wiek", "rola": "wiek", "tekst": "47-letni", "miejsce": "tresc", "wartosc_id": None, "rdzen": ["47"]},
        {"id": "k1.funkcja", "rola": "funkcja", "tekst": "Prezes Zarządu", "miejsce": "tresc", "wartosc_id": None,
         "rdzen": ["Prezes Zarządu"]}]}]
    r = RegulyWycieku()
    a = tekst.index("47")
    # zamaskowana sama liczba („47”) przerywa wiek (reguła identyfikatora – token „47” byłby za krótki)
    assert ocen_tekst([], _wykrycia([(a, a + 2)]), tekst, r, posrednie=k).posrednie[0]["przerwana"] is True
    # jedna litera nazwy funkcji pokryta: token „Zarządu” nadal odsłonięty (reguła tokenów) – kombinacja nieprzerwana
    z = tekst.index("Zarządu")
    o = ocen_tekst([], _wykrycia([(z, z + 1)]), tekst, r, posrednie=k).posrednie[0]
    assert o["przerwana"] is False and o["widoczne"] == ["k1.wiek", "k1.funkcja"]
    # cały token „Zarządu” – funkcja niewidoczna
    assert ocen_tekst([], _wykrycia([(z, z + 7)]), tekst, r, posrednie=k).posrednie[0]["przerwana"] is True
    assert ocen_tekst([], [], tekst, r, posrednie=[]).posrednie == []


# ============================================================================= pliki: niezależne czytniki i sędzia plikowy
class _Idealny(Maskowanie):
    """Uczestnik idealny: maskuje gold (`Maskowanie`) i teksty składników spoza gold (tej samej długości)."""

    def __init__(self, teksty: list[str]) -> None:
        super().__init__()
        self.teksty = teksty

    def _napis(self, f: str) -> str:
        for t in self.teksty:
            f = f.replace(t, ("[SKLADNIK]" + "_" * len(t))[:len(t)] if len(t) >= 10 else "[S]")
        return f

    def __call__(self, d):
        n = super().__call__(d)
        n.elementy = [Element(e.rodzaj, [self._napis(f) if isinstance(f, str) else f for f in e.fragmenty], e.atrybuty)
                      for e in n.elementy]
        return n


@pytest.fixture(scope="module")
def formaty(tmp_path_factory) -> dict[tuple[str, str], list[tuple[Path, dict, trudne.PozycjaTrudna]]]:
    """Każdy przypadek w każdym formacie (języki po kolei); działka – dokument z nieruchomością wskazaną zwykłym gold (KW/adres)
    i bez niej w każdym formacie."""
    cel = tmp_path_factory.mktemp("formaty")
    wynik: dict = {}
    for nr_p, przypadek in enumerate(H5):
        pary = sorted(trudne.GENERATORY_H5[przypadek])
        for i, fmt in enumerate(FORMATY):
            potrzebne = {True, False} if przypadek == P.POSREDNIE_DZIALKA_GPS else {None}
            for proba in range(40):
                jezyk, typ = pary[(3 * i + nr_p + proba) % len(pary)]
                poz = trudne.PozycjaTrudna(f"h-{P.SKROTY[przypadek]}-{jezyk}-{typ}-9{i}{proba:02d}", jezyk, typ, fmt, przypadek)
                w = trudne.generuj_dokument_trudny(poz, trudne.ZIARNO_TRUDNE, "test", cel)
                klucz = (any(g["wartosc_id"].startswith(("nieruchomosc.adres", "nieruchomosc.kw")) for g in w["gold_tekst"])
                         if przypadek == P.POSREDNIE_DZIALKA_GPS else None)
                if klucz in potrzebne:
                    potrzebne.discard(klucz)
                    wynik.setdefault((przypadek, fmt), []).append((cel, w, poz))
                if not potrzebne:
                    break
            assert not potrzebne, (przypadek, fmt)
    return wynik


def _skladniki_spoza_gold(w: dict) -> list[Wartosc]:
    return [Wartosc(s["id"], "WLASNE", s["tekst"], w["jezyk"], s["miejsce"], "WLASNE")
            for k in w["posrednie"] for s in k["skladniki"] if s["wartosc_id"] is None]


@pytest.mark.parametrize("klucz", [(p, f) for p in H5 for f in FORMATY])
def test_gold_i_skladniki_w_pliku_niezaleznym_czytnikiem(formaty, klucz):
    for cel, w, _ in formaty[klucz]:
        plik = cel / w["plik"]
        wartosci = [Wartosc.from_dict(x) for x in w["gold_plik"]] + _skladniki_spoza_gold(w)
        assert w["ostrzezenia"] == [] and _skladniki_spoza_gold(w)
        ids = {x["id"] for x in w["gold_plik"]}
        assert all(s["wartosc_id"] in ids for k in w["posrednie"] for s in k["skladniki"] if s["wartosc_id"])
        if klucz[1] == "docx":
            with zipfile.ZipFile(plik) as zf:
                teksty = _teksty_miejsc(zf)
            for v in wartosci:
                assert v.tekst in teksty[v.miejsce], (v.id, v.tekst, v.miejsce)
        elif klucz[1] == "pdf":
            _sprawdz_miejsca(plik, wartosci)
        else:
            blob = _blob_doc(plik)
            assert all(_w_blobie(v.tekst, blob) for v in wartosci), [v.tekst for v in wartosci if not _w_blobie(v.tekst, blob)]


@pytest.mark.parametrize("klucz", [(p, f) for p in H5 for f in FORMATY])
def test_sedzia_plikowy_sanity(formaty, tmp_path, klucz):
    for cel, w, poz in formaty[klucz]:
        ws = wartosci_wpisu(w)
        orig = cel / w["plik"]
        o = ocen_plik(orig, orig, ws, leksykon={}, posrednie=w["posrednie"])
        assert [k["przerwana"] for k in o.posrednie] == [False] * len(w["posrednie"]), (w["id"], o.posrednie)
        teksty = [x.tekst for x in _skladniki_spoza_gold(w)]
        for nazwa, maska, oczek in (("idealny", _Idealny(teksty), lambda k: True), ("kategorie", Maskowanie(), _ma_gold)):
            wyj = tmp_path / f"{w['id']}-{nazwa}"
            wyj.mkdir()
            r = trudne.generuj_dokument_trudny(poz, trudne.ZIARNO_TRUDNE, w["split"], wyj, maskuj=maska)
            b = ocen_plik(orig, wyj / r["plik"], ws, leksykon={}, posrednie=w["posrednie"])
            assert b.status == "OK" and not b.wycieki, (w["id"], nazwa, b.wycieki[:3])
            assert [k["przerwana"] for k in b.posrednie] == [oczek(k) for k in w["posrednie"]], (w["id"], nazwa, b.posrednie)
        bez = ocen_plik(orig, orig, ws, leksykon={})
        assert bez.posrednie is None and sorted(bez.wycieki) == sorted(o.wycieki)       # miara główna bez zmian


# ============================================================================= rekordy oceny i agregacja
def test_rekordy_ocen_maja_pole_posrednie(warstwa):
    cel, wpisy = warstwa[P.POSREDNIE_DZIALKA_GPS]
    w = next(x for x in wpisy if x["format"] == "docx")
    reguly = cel / "brak-prerejestracji.md"
    t = ocen._ocen_tekstowo(w, {"wykrycia": []}, cel, reguly)
    assert [k["przerwana"] for k in t["posrednie"]] == [False, False]
    n = ocen._ocen_tekstowo(w, {"pominiety": "język spoza deklaracji"}, cel, reguly)      # nieobsługiwany: nic nie przerwane
    assert [k["przerwana"] for k in n["posrednie"]] == [False, False]
    tekst = (cel / w["plik_txt"]).read_text(encoding="utf-8")
    wszystko = [[s, e, "X", 1.0] for s, e in zakresy_skladnikow(w["posrednie"], tekst)] + \
        [[g["start"], g["end"], "X", 1.0] for g in w["gold_tekst"]]
    t2 = ocen._ocen_tekstowo(w, {"wykrycia": wszystko}, cel, reguly)
    assert [k["przerwana"] for k in t2["posrednie"]] == [True, True] and t2["fp_znaki"] == 0
    p = ocen._ocen_plikowo(w, {"blad": "timeout"}, cel, cel, reguly, cel / "manifest.jsonl")   # fail-closed: kopia oryginału
    assert p["integralnosc"] is None and [k["przerwana"] for k in p["posrednie"]] == [False, False]
    trzon = {**w, "posrednie": []}
    assert "posrednie" not in ocen._ocen_tekstowo(trzon, {"wykrycia": []}, cel, reguly)


def _rek(jezyk: str, *kombinacje: tuple[str, bool | None]) -> dict:
    return {"jezyk": jezyk, "posrednie": [{"id": f"k{i}", "rodzaj": r, "przerwana": p, "widoczne": []}
                                          for i, (r, p) in enumerate(kombinacje, 1)]}


def test_agregacja_odsetek_i_przedzial():
    ff, dg = P.POSREDNIE_FUNKCJA_FIRMA, P.POSREDNIE_DZIALKA_GPS
    rek = [_rek("pl", (ff, True), (ff, False)), _rek("pl", (dg, True)), _rek("en", (dg, False)), _rek("en", (dg, None)),
           {"jezyk": "pl", "wycieki": []}, {"jezyk": "de", "posrednie": []}]
    a = posrednie.agreguj(rek)
    assert a["ogolem"]["kombinacje"] == 4 and a["ogolem"]["przerwane"] == 2 and a["ogolem"]["odsetek"] == 0.5
    assert a["ogolem"]["dokumenty"] == 3 and a["nieocenione"] == 1
    assert a["rodzaje"][ff]["odsetek"] == 0.5 and a["rodzaje"][dg]["odsetek"] == 0.5 and a["rodzaje"][dg]["kombinacje"] == 2
    assert a["jezyki"]["pl"]["odsetek"] == 2 / 3 and a["jezyki"]["en"]["odsetek"] == 0.0 and set(a["jezyki"]) == {"pl", "en"}
    for m in (a["ogolem"], *a["rodzaje"].values(), *a["jezyki"].values()):
        lo, hi = m["przedzial"]
        assert 0.0 <= lo <= m["odsetek"] <= hi <= 1.0
    assert a == posrednie.agreguj(rek)                                    # deterministycznie (stałe ziarno bootstrapu)
    pelne = posrednie.agreguj([_rek("fr", (ff, True)) for _ in range(5)])
    assert pelne["ogolem"]["odsetek"] == 1.0 and pelne["ogolem"]["przedzial"] == [1.0, 1.0]
    puste = posrednie.agreguj([])
    assert puste["ogolem"] == {"dokumenty": 0, "kombinacje": 0, "przerwane": 0, "odsetek": None, "przedzial": None}
    szeroki = posrednie.agreguj([_rek("pl", (ff, i % 2 == 0)) for i in range(40)])["ogolem"]
    assert szeroki["przedzial"][0] < 0.5 < szeroki["przedzial"][1] and szeroki["przedzial"][1] - szeroki["przedzial"][0] < 0.5


# ============================================================================= runda poprawek 1 (przegląd H5)
def test_dzialka_i_gps_przerywane_osobno(warstwa):
    """I1: numer działki i GPS domu to dwie kombinacje jednoskładnikowe – zamaskowanie jednego nie przerywa drugiego."""
    r = RegulyWycieku()
    cel, wpisy = warstwa[P.POSREDNIE_DZIALKA_GPS]
    for w in wpisy:
        tekst = (cel / w["plik_txt"]).read_text(encoding="utf-8")
        gold = gold_z_wpisu(w)
        kat = [(g.start, g.end) for g in gold]
        zakresy = {k["skladniki"][0]["rola"]: posrednie.wystapienia(tekst, k["skladniki"][0]["tekst"]) for k in w["posrednie"]}
        assert set(zakresy) == {"dzialka", "gps"}
        for rola, inna in (("dzialka", "gps"), ("gps", "dzialka")):
            o = ocen_tekst(gold, _wykrycia(kat + zakresy[rola]), tekst, r, posrednie=w["posrednie"])
            stan = {kk["skladniki"][0]["rola"]: k["przerwana"] for k, kk in zip(o.posrednie, w["posrednie"])}
            assert stan == {rola: True, inna: False}, (w["id"], rola)


@pytest.mark.parametrize("fmt", ["docx", "pdf"])
def test_dzialka_i_gps_przerywane_osobno_w_pliku(formaty, tmp_path, fmt):
    for cel, w, poz in formaty[(P.POSREDNIE_DZIALKA_GPS, fmt)][:1]:
        ws, orig = wartosci_wpisu(w), cel / w["plik"]
        teksty = {k["skladniki"][0]["rola"]: k["skladniki"][0]["tekst"] for k in w["posrednie"]}
        for rola, inna in (("dzialka", "gps"), ("gps", "dzialka")):
            wyj = tmp_path / rola
            wyj.mkdir()
            r = trudne.generuj_dokument_trudny(poz, trudne.ZIARNO_TRUDNE, w["split"], wyj, maskuj=_Idealny([teksty[rola]]))
            b = ocen_plik(orig, wyj / r["plik"], ws, leksykon={}, posrednie=w["posrednie"])
            stan = {kk["skladniki"][0]["rola"]: k["przerwana"] for k, kk in zip(b.posrednie, w["posrednie"])}
            assert stan == {rola: True, inna: False}, (w["id"], rola, b.posrednie)


def _poza_rdzeniem(s: dict, od: int) -> list[tuple[int, int]]:
    """Przedziały tekstu składnika (wystąpienie od `od`) poza fragmentami rdzenia, ze znakiem alfanumerycznym."""
    wynik, poz = [], 0
    for a, b in [*posrednie.zakresy_rdzenia(s["tekst"], s["rdzen"]), (len(s["tekst"]), len(s["tekst"]))]:
        if any(c.isalnum() for c in s["tekst"][poz:a]):
            wynik.append((od + poz, od + a))
        poz = b
    return wynik


def test_rdzen_skladnika_w_sedzi_tekstowym(warstwa):
    """M1: widoczność liczona na rdzeniu – zamaskowanie samej etykiety („-letni”, „obręb”, „title number”, „N”/„E”, „choroba”)
    nie przerywa kombinacji, zamaskowanie fragmentu rdzenia (albo jednej cyfry liczby) – przerywa; dla każdej roli."""
    r = RegulyWycieku()
    sprawdzone: Counter = Counter()
    for przypadek in H5:
        cel, wpisy = warstwa[przypadek]
        for w in wpisy:
            tekst = (cel / w["plik_txt"]).read_text(encoding="utf-8")
            gold = gold_z_wpisu(w)

            def stan(spany, kid):
                o = ocen_tekst(gold, _wykrycia(spany), tekst, r, posrednie=w["posrednie"])
                return next(x for x in o.posrednie if x["id"] == kid)
            for k in w["posrednie"]:
                for s in k["skladniki"]:
                    od = tekst.index(s["tekst"])
                    rdz = [(od + a, od + b) for a, b in posrednie.zakresy_rdzenia(s["tekst"], s["rdzen"])]
                    if poza := _poza_rdzeniem(s, od):
                        o = stan(poza, k["id"])
                        assert o["przerwana"] is False and s["id"] in o["widoczne"], (w["id"], s, poza)
                        sprawdzone[(s["rola"], "etykieta")] += 1
                    assert stan(rdz[:1], k["id"])["przerwana"] is True, (w["id"], s)
                    sprawdzone[(s["rola"], "rdzen")] += 1
                    if posrednie.kategoria_reguly(s["rola"]) == posrednie.KATEGORIA_ID and s["wartosc_id"] is None:
                        a, b = rdz[-1]
                        ost = max(i for i in range(a, b) if tekst[i].isalnum())
                        assert stan([(ost, ost + 1)], k["id"])["przerwana"] is True, (w["id"], s)      # jedna cyfra liczby
    assert {rola for rola, x in sprawdzone if x == "etykieta"} >= {"wiek", "rok_urodzenia", "szkola", "dzialka", "gps", "choroba"}
    assert {rola for rola, x in sprawdzone if x == "rdzen"} >= {"wiek", "rok_urodzenia", "szkola", "dzialka", "gps", "choroba",
                                                                  "funkcja", "firma", "miejscowosc"}


def test_rdzen_etykiety_i_liczby():
    """M1 na przykładach z orzeczenia: „letni”, „obręb”, litera „E” – kombinacja nieprzerwana; liczba – przerwana."""
    tekst = "Szedł 47-letni mieszkaniec. Działka nr 82/26, obręb 0021. Wejście: 50°10′32.3″N 11°21′27.1″E."
    sk = [("k1", "wiek", "47-letni", ["47"]), ("k2", "dzialka", "82/26, obręb 0021", ["82/26", "0021"]),
          ("k3", "gps", "50°10′32.3″N 11°21′27.1″E", ["50", "10", "32.3", "11", "21", "27.1"])]
    k = [{"id": i, "rodzaj": P.POSREDNIE_DZIALKA_GPS if rola != "wiek" else P.POSREDNIE_WIEK_MIEJSCOWOSC,
          "skladniki": [{"id": f"{i}.{rola}", "rola": rola, "tekst": t, "miejsce": "tresc", "wartosc_id": None, "rdzen": rdz}]}
         for i, rola, t, rdz in sk]
    r = RegulyWycieku()

    def przerwane(*frazy):
        spany = []
        for f in frazy:
            a = tekst.index(f)
            spany.append((a, a + len(f)))
        return [x["przerwana"] for x in ocen_tekst([], _wykrycia(spany), tekst, r, posrednie=k).posrednie]
    assert przerwane() == [False, False, False]
    assert przerwane("letni", "obręb", "″E") == [False, False, False]
    assert przerwane("N 11") == [False, False, True]
    assert przerwane("47") == [True, False, False]
    assert przerwane("0021") == [False, True, False]
    assert przerwane("27.1″E") == [False, False, True]


def _podmien_docx(src: Path, dst: Path, zamiany: list[tuple[str, str]]) -> None:
    """Kopia DOCX z podmienionym tekstem w `word/document.xml` (każda zamiana musi trafić)."""
    with zipfile.ZipFile(src) as zi, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zo:
        for it in zi.infolist():
            b = zi.read(it.filename)
            if it.filename == "word/document.xml":
                x = b.decode("utf-8")
                for a, c in zamiany:
                    assert a in x, (src.name, a)
                    x = x.replace(a, c)
                b = x.encode("utf-8")
            zo.writestr(it, b)


def _dokument_docx(cel: Path, przypadek: str, jezyk: str, typ: str, warunek) -> dict:
    for proba in range(60):
        poz = trudne.PozycjaTrudna(f"h-{P.SKROTY[przypadek]}-{jezyk}-{typ}-8{proba:03d}", jezyk, typ, "docx", przypadek)
        w = trudne.generuj_dokument_trudny(poz, trudne.ZIARNO_TRUDNE, "test", cel)
        if warunek({s["rola"]: s for k in w["posrednie"] for s in k["skladniki"]}):
            return w
    raise AssertionError((przypadek, jezyk))                              # pragma: no cover


def test_rdzen_skladnika_w_sedzi_plikowym(tmp_path):
    """M1 w sędzi plikowym: rdzeń szukany odcinkami (`posrednie.odcinki_rdzenia`) – usunięte litery półkul, etykieta numeru
    tytułu, człon rodzajowy choroby i słowo „born in” nie przerywają kombinacji; podmieniona liczba – przerywa."""
    dg = _dokument_docx(tmp_path, P.POSREDNIE_DZIALKA_GPS, "en", "protokol_ogledzin", lambda s: "°" in s["gps"]["tekst"])
    rc = _dokument_docx(tmp_path, P.POSREDNIE_RZADKA_CHOROBA, "en", "wniosek_kadrowy",
                        lambda s: "rok_urodzenia" in s and s["choroba"]["rdzen"] != [s["choroba"]["tekst"]])
    s_dg = {k["skladniki"][0]["rola"]: k["skladniki"][0] for k in dg["posrednie"]}
    s_rc = {s["rola"]: s for s in rc["posrednie"][0]["skladniki"]}
    g, tytul = s_dg["gps"], s_dg["dzialka"]["rdzen"][0]
    bez_liter = g["tekst"].replace("″N", "″").replace("″S", "″").replace("″E", "″").replace("″W", "″")
    ch = s_rc["choroba"]
    etykieta_choroby = ch["tekst"].replace(ch["rdzen"][0], "").strip()
    rok = s_rc["rok_urodzenia"]["rdzen"][0]
    scenariusze = [
        (dg, [(g["tekst"], bez_liter)], [False, False]),
        (dg, [(f"title number {tytul}", tytul)], [False, False]),
        (dg, [(tytul, "[TYTUŁ]")], [True, False]),
        (dg, [(g["tekst"], g["tekst"].replace(g["rdzen"][-1] + "″", "[X]″"))], [False, True]),
        (rc, [(etykieta_choroby, "[X]"), (f"born in {rok}", rok)], [False]),
        (rc, [(rok, "[ROK]")], [True]),
        (rc, [(ch["rdzen"][0], "[CHOROBA]")], [True]),
    ]
    for nr, (w, zamiany, oczek) in enumerate(scenariusze):
        orig = tmp_path / w["plik"]
        dst = tmp_path / f"wynik-{nr}.docx"
        _podmien_docx(orig, dst, zamiany)
        b = ocen_plik(orig, dst, wartosci_wpisu(w), leksykon={}, posrednie=w["posrednie"])
        assert [k["przerwana"] for k in b.posrednie] == oczek, (nr, zamiany, b.posrednie)


def test_rdzen_choroby():
    assert TP.rdzen_choroby("choroba Fabry'ego") == "Fabry'ego"
    assert TP.rdzen_choroby("zespół Marfana") == "Marfana" and TP.rdzen_choroby("Marfan syndrome") == "Marfan"
    assert TP.rdzen_choroby("vaskuläres Ehlers-Danlos-Syndrom") == "vaskuläres Ehlers-Danlos"
    assert TP.rdzen_choroby("syndrome d'Ehlers-Danlos vasculaire") == "Ehlers-Danlos vasculaire"
    assert TP.rdzen_choroby("enfermedad de Pompe de inicio tardío") == "Pompe de inicio tardío"
    assert TP.rdzen_choroby("akromegalia") == "akromegalia" and TP.rdzen_choroby("hemofilia A") == "hemofilia A"
    for jezyk, choroby in TP._CHOROBY.items():
        assert all(TP.rdzen_choroby(c) and TP.rdzen_choroby(c) in c for c, _ in choroby)


#: Pary funkcja – forma prawna z orzeczenia (M4): funkcja (forma męska) -> formy dopuszczalne (nadzbiór tabeli generatora).
_FORMY_DOPUSZCZALNE = {
    "pl": {"Prezes Zarządu": {"sp. z o.o.", "S.A.", "P.S.A."}, "jedyny wspólnik": {"sp. z o.o."},
           "komplementariusz": {"sp.k.", "S.K.A."}},
    "de": {"Geschäftsführer": {"GmbH", "UG (haftungsbeschränkt)"}, "Finanzvorstand": {"AG"},
           "Alleingesellschafter": {"GmbH", "UG (haftungsbeschränkt)"}},
    "fr": {"gérant": {"SARL", "EURL"}, "président": {"SAS", "SASU"}, "associé unique": {"EURL", "SASU"}},
    "es": {"administrador único": {"S.L.", "S.A.", "S.L.U."}, "socio único": {"S.L.U."}},
    "en": {"Managing Director": {"Ltd", "Limited", "PLC"}, "Chief Financial Officer": {"Ltd", "Limited", "PLC"},
           "sole shareholder": {"Ltd", "Limited"}},
}


def test_funkcja_tylko_z_dopuszczalna_forma_prawna(generowane):
    for jezyk, tabela in _FORMY_DOPUSZCZALNE.items():
        funkcje = {f[0]: f[3] for f in TP._FUNKCJE[jezyk]}
        for funkcja, formy in tabela.items():
            assert funkcje[funkcja] and set(funkcje[funkcja]) <= formy, (jezyk, funkcja)
    licz: Counter = Counter()
    for przypadek, jezyk, typ, seed, (wynik, _, dod) in generowane:
        if przypadek != P.POSREDNIE_FUNKCJA_FIRMA:
            continue
        for k in dod["posrednie"]:
            sk = {s["rola"]: s["tekst"] for s in k["skladniki"]}
            wpis = next(f for f in TP._FUNKCJE[jezyk] if sk["funkcja"] in f[:2])
            if "firma" in sk:
                forma = max((f for f in wpis[3] if sk["firma"].endswith((" " + f, ", " + f))), key=len, default=None)
                assert forma is not None, (jezyk, sk)
                assert not sk["firma"].endswith(" sp. z o.o. sp.k.") or forma == "sp. z o.o. sp.k."
                licz[jezyk] += 1
    assert set(licz) == set(JEZYKI)


def test_elizja_fr():
    assert TP._elizja("fr", "{f} de {firma}", "Étoile SARL") == "{f} d'{firma}"
    assert TP._elizja("fr", "{f} de {firma}", "Atlas SAS") == "{f} d'{firma}"
    assert TP._elizja("fr", "{f} de {firma}", "Normandie SAS") == "{f} de {firma}"
    assert TP._elizja("es", "{f} de {firma}", "Alfa, S.L.") == "{f} de {firma}"


def test_elizja_fr_w_dokumentach():
    for seed in range(40):
        wynik, _, dod = TP.GENERATORY[P.POSREDNIE_FUNKCJA_FIRMA][("fr", "notatka_kontrahent")]("fr", "notatka_kontrahent", seed)
        tekst = _tekst_dok(wynik)
        assert not re.search(r"\bde [AEIOUYÉÈÊÀÂÎÔÛaeiouyéèêàâîôû]", tekst), (seed, tekst)


def test_pl_kierowca_w_bierniku():
    """M5: „kierowanego przez Tadeusza Kwiatkowskiego” – kierowca w bierniku (odmiana z `odmiana_pl`)."""
    from pbench.trudne_wspolne import bez_blokady, osoba
    for seed in range(8):
        proba = next(p for p in range(TP.PROBY) if TP._buduj_wiek("pl", "notatka_zdarzenie", seed, p) is not None)
        wynik, _, _ = TP._buduj_wiek("pl", "notatka_zdarzenie", seed, proba)
        gen, ctx = TP._kontekst("pl", seed, proba)
        osoba(gen, ctx)                                                    # osoba-cel – jak w generatorze
        k = osoba(gen, ctx, None, bez_blokady)
        biernik = odmien(k.imie, k.nazwisko, k.plec, "bier")
        assert f"kierowanego przez {biernik}, zam." in _tekst_dok(wynik), (seed, biernik)


def test_en_dzialka_numer_tytulu(generowane):
    licz = 0
    for przypadek, jezyk, typ, seed, (wynik, _, dod) in generowane:
        if przypadek == P.POSREDNIE_DZIALKA_GPS and jezyk == "en":
            s = dod["posrednie"][0]["skladniki"][0]
            assert re.fullmatch(r"title number [A-Z]{2}\d{6}", s["tekst"]) and s["rdzen"] == [s["tekst"].split()[-1]]
            assert "registered under title number" in _tekst_dok(wynik)
            licz += 1
    assert licz == len(NASIONA)


def test_przypadki_punktowane_bez_posrednich():
    """M6: średnia T3/P3 wybiera przypadki wyłącznie `przypadki_punktowane(poziom)` – rejestr bez `posrednie_*`."""
    pk = P.przypadki_punktowane("plik")
    assert pk == tuple(p for p in P.PRZYPADKI if p not in P.POSREDNIE) and len(pk) == len(P.PRZYPADKI) - len(P.POSREDNIE)
    assert not set(pk) & P.POSREDNIE and not any(p.startswith("posrednie_") for p in pk)


def test_blad_sedziego_kombinacje_nieprzerwane(warstwa):
    """M7: błąd sędziego na dokumencie z kombinacjami – wszystkie nieprzerwane i w mianowniku (fail-closed), licznik błędów."""
    cel, wpisy = warstwa[P.POSREDNIE_FUNKCJA_FIRMA]
    w = wpisy[0]
    zly = {**w, "plik": "brak/pliku.docx", "plik_txt": "brak/pliku.txt"}
    rekordy = []
    for poziom in ("tekst", "plik"):
        rek = ocen._ocen_dokument((poziom, zly, {"wykrycia": []}, str(cel), str(cel), str(cel / "brak-prerejestracji.md"),
                                   str(cel / "manifest.jsonl"), None, None))
        assert "blad_sedziego" in rek and rek["posrednie"] == posrednie.nieprzerwane(w["posrednie"]), (poziom, rek)
        assert [k["przerwana"] for k in rek["posrednie"]] == [False] * len(w["posrednie"])
        assert all(k["widoczne"] == [s["id"] for s in kk["skladniki"]] for k, kk in zip(rek["posrednie"], w["posrednie"]))
        rekordy.append(rek)
    bez = ocen._ocen_dokument(("tekst", {**zly, "posrednie": []}, {"wykrycia": []}, str(cel), str(cel),
                               str(cel / "brak-prerejestracji.md"), str(cel / "manifest.jsonl"), None, None))
    assert "blad_sedziego" in bez and "posrednie" not in bez
    a = posrednie.agreguj([rekordy[0], bez, _rek("pl", (P.POSREDNIE_FUNKCJA_FIRMA, True))])
    assert a["bledy_sedziego"] == 2 and a["ogolem"]["kombinacje"] == len(w["posrednie"]) + 1
    assert a["ogolem"]["przerwane"] == 1 and a["ogolem"]["dokumenty"] == 2
