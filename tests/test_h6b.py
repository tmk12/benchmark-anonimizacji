"""Testy złożenia warstwy trudnych przypadków (H6b): rozkład (jedno źródło, warunki, zgodność z `metodyka/przypadki.md`), plan
i split pełnej warstwy, przypadki T3/P3, sumy kontrolne do prerejestracji (bieżąca budowa = `metodyka/SHA256SUMS-trudne`),
determinizm budowy wieloprocesowej oraz poprawki z przeglądu językowego."""
from __future__ import annotations

import hashlib
import json
import random
import re
import shutil
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path

import pytest

from pbench import korpus, przypadki as P, trudne, trudne_warstwa as W
from pbench.budowa import zbuduj_z_kontekstem
from pbench.dane import Generator, zgodna_plec
from pbench.odmiana_pl import przyimek_pl, przyimek_przed
from pbench.skladacz import G, Skladacz
from pbench.szablony import SZABLONY, SZABLONY_TRUDNE
from pbench.szablony.trudne import SZABLONY_WSTAWKI

KORZEN = Path(__file__).resolve().parent.parent
BAZA = json.loads((Path(__file__).parent / "dane_testowe" / "trudne_baseline.json").read_text(encoding="utf-8"))
ZNACZNIK = re.compile(r"<!-- rozklad:poczatek -->\n(.*?)<!-- rozklad:koniec -->", re.S)


def _manifest(cel: Path) -> list[dict]:
    return [json.loads(w) for w in (cel / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]


# ----------------------------------------------------------------------------- rozkład
def test_rozklad_spelnia_warunki():
    W.sprawdz_rozklad()
    suma = sum(r.n for r in W.ROZKLAD.values())
    assert abs(suma - 300) <= 40 and list(W.ROZKLAD) == list(P.PRZYPADKI)
    for przypadek, r in W.ROZKLAD.items():
        assert r.n >= 8 and r.uzasadnienie, przypadek
        mozliwe = W.jezyki_przypadku(przypadek)
        assert set(r.jezyki) == set(mozliwe), przypadek          # wszystkie języki, w których przypadek ma generator
        assert "pl" in r.jezyki or mozliwe == ["uk"], przypadek    # PL zawsze (poza dokumentem w całości ukraińskim)


@pytest.mark.parametrize("zmiana", ["za_malo", "brak_jezyka", "obcy_jezyk", "suma"])
def test_sprawdz_rozklad_odrzuca_zly_rozklad(zmiana):
    r = dict(W.ROZKLAD)
    if zmiana == "za_malo":
        r[P.RTL] = W.Rozklad({"pl": 3, "en": 1, "es": 1, "de": 1, "fr": 1}, "x")
    elif zmiana == "brak_jezyka":
        r[P.RTL] = W.Rozklad({"pl": 8}, "x")
    elif zmiana == "obcy_jezyk":
        r[P.ODMIANA_NAZWISK] = W.Rozklad({"pl": 7, "en": 1}, "x")
    else:
        r[P.HOMOGLIFY] = W.Rozklad({"pl": 60, "en": 2, "es": 2, "de": 2, "fr": 2}, "x")
    with pytest.raises(ValueError):
        W.sprawdz_rozklad(r)


def test_tabela_rozkladu_w_metodyce_zgodna_z_kodem():
    md = (KORZEN / "metodyka" / "przypadki.md").read_text(encoding="utf-8")
    m = ZNACZNIK.search(md)
    assert m, "brak znaczników tabeli rozkładu w metodyka/przypadki.md"
    assert m.group(1) == W.tabela_rozkladu(), "tabela nieaktualna: uv run pbench-trudne --rozklad"


def test_cli_rozklad(capsys):
    assert trudne.main(["--rozklad"]) == 0
    assert capsys.readouterr().out == W.tabela_rozkladu()


# ----------------------------------------------------------------------------- plan i split
def test_plan_warstwy_kontyngenty_formaty_identyfikatory():
    plan = W.zaplanuj_warstwe()
    assert plan == W.zaplanuj_warstwe() and plan == sorted(plan, key=lambda p: p.id)
    assert len(plan) == sum(r.n for r in W.ROZKLAD.values()) == len({p.id for p in plan})
    assert not {p.id for p in plan} & {p.id for p in korpus.zaplanuj(korpus.ZIARNO)}
    for przypadek, r in W.ROZKLAD.items():
        pozycje = [p for p in plan if p.przypadek == przypadek]
        assert Counter(p.jezyk for p in pozycje) == Counter(r.jezyki), przypadek
        dozwolone = {f for f, _ in W._formaty_przypadku(przypadek)}
        for p in pozycje:
            assert re.fullmatch(rf"h-{P.SKROTY[przypadek]}-{p.jezyk}-{p.typ}-\d{{4}}", p.id)
            assert (p.jezyk, p.typ) in trudne._pary(przypadek) and p.format in trudne.formaty_dla(p.jezyk, p.typ)
            assert p.format in dozwolone, (p.id, p.format)
        # formaty przypadku z udziałów trzonu: każdy możliwy format, gdy dokumentów wystarcza
        if len(dozwolone) <= r.n // 2:
            assert {p.format for p in pozycje} == dozwolone, przypadek
    # wybór przypadków nie zmienia identyfikatorów
    assert W.zaplanuj_warstwe(przypadki=(P.RTL,)) == [p for p in plan if p.przypadek == P.RTL]
    assert plan != W.zaplanuj_warstwe(ziarno=1)


def test_plan_dwa_formaty_w_kazdym_jezyku():
    """Przypadki z rozkładem 2 dokumenty na język i dwoma formatami (poczta, RTF/ODT): każdy język w obu formatach."""
    plan = W.zaplanuj_warstwe()
    for przypadek in (P.UKRYTA_POCZTA, P.CYTOWANE_WATKI_VCARD, P.FORMATY_RTF_ODT):
        for jezyk in W.ROZKLAD[przypadek].jezyki:
            assert len({p.format for p in plan if p.przypadek == przypadek and p.jezyk == jezyk}) == 2, (przypadek, jezyk)


def test_split_warstwy_co_najmniej_dwa_dev_w_przypadku():
    plan = W.zaplanuj_warstwe()
    split = W.przydziel_split_warstwy(plan)
    assert set(split) == {p.id for p in plan} and set(split.values()) == {"dev", "test"}
    for przypadek, r in W.ROZKLAD.items():
        pozycje = [p for p in plan if p.przypadek == przypadek]
        dev = [p for p in pozycje if split[p.id] == "dev"]
        test = [p for p in pozycje if split[p.id] == "test"]
        assert len(dev) == W.liczba_dev(r.n) >= 2, przypadek
        # split test (punktowany) ma każdy język i każdy format przypadku – dev nie zabiera ostatniego dokumentu (I1)
        assert {p.jezyk for p in test} == {p.jezyk for p in pozycje}, przypadek
        assert {p.format for p in test} == {p.format for p in pozycje}, przypadek
        if r.jezyki == W._PIEC_8:
            assert [p.jezyk for p in dev] == ["pl", "pl"], przypadek
    for przypadek, r in W.ROZKLAD.items():
        assert W.przydziel_split_warstwy([p for p in plan if p.przypadek == przypadek]) == \
            {p.id: split[p.id] for p in plan if p.przypadek == przypadek}, przypadek
    pomieszany = list(reversed(plan))
    assert W.przydziel_split_warstwy(pomieszany) == split
    dev = sum(1 for s in split.values() if s == "dev")
    assert 0.18 <= dev / len(plan) <= 0.26


def test_split_warstwy_limit_warstw_i_brak_miejsca():
    """`_rozdziel` z limitem: nadwyżka przechodzi do warstw z zapasem; gdy zapasu brak – ValueError, nie cichy split bez
    języka w test."""
    assert W._rozdziel(Counter({"pl": 4, "en": 1, "es": 1}), 2, 1, "x",
                       limity={"pl": 3, "en": 0, "es": 0}) == {"pl": 2, "en": 0, "es": 0}
    plan = [trudne.PozycjaTrudna(f"h-rt-{j}-umowa-0001", j, "umowa", "docx", P.RTL) for j in ("pl", "en", "es")]
    with pytest.raises(ValueError):
        W.przydziel_split_warstwy(plan)


# ----------------------------------------------------------------------------- T3 / P3
def test_przypadki_punktowane_tekst_bez_przypadkow_tylko_plikowych():
    tekst, plik = set(P.przypadki_punktowane("tekst")), set(P.przypadki_punktowane("plik"))
    assert plik == set(P.PRZYPADKI) - P.POSREDNIE
    assert tekst == plik - P.TYLKO_PLIK and P.TYLKO_PLIK <= plik and not P.TYLKO_PLIK & P.POSREDNIE
    assert len(tekst) == 18 and len(plik) == 30
    assert P.CYTOWANE_WATKI_VCARD in tekst and P.UKRYTA_DOCX not in tekst
    for zly in ("obraz", None):
        with pytest.raises(ValueError):
            P.przypadki_punktowane(zly)
    with pytest.raises(TypeError):                                # poziom jawny – bez wartości domyślnej (M5)
        P.przypadki_punktowane()


@pytest.mark.parametrize("przypadek", sorted(P.TYLKO_PLIK))
def test_przypadek_tylko_plikowy_tekst_poziomu_1_bez_wartosci_przypadku(tmp_path, przypadek):
    """Wartości dopisane przez przypadek (prefiksy `u.`/`h.`) są tylko w `gold_plik`; tekst poziomu 1 – zwykły dokument.
    Wyjątek: RTF/ODT dopisuje zwykłą (widoczną) tabelę kontaktów i komentarz – trudnością jest sam format pliku."""
    for w in W.zbuduj_warstwe(tmp_path, przypadki=(przypadek,))[:2]:
        if przypadek != P.FORMATY_RTF_ODT:
            assert not any(g["wartosc_id"].startswith(("u.", "h.")) for g in w["gold_tekst"]), w["id"]
        assert not any("rtl" in g.get("cechy", ()) or "przeniesienie" in g.get("cechy", ()) for g in w["gold_tekst"])


# ----------------------------------------------------------------------------- budowa i sumy kontrolne
def test_sumy_kontrolne_format_sha256sum(tmp_path):
    wpisy = W.zbuduj_warstwe(tmp_path, przypadki=(P.PARAFY,))
    tekst = W.sumy_kontrolne(tmp_path)
    linie = tekst.splitlines()
    assert tekst.endswith("\n") and linie == sorted(linie, key=lambda l: l.split("  ", 1)[1])
    assert all(re.fullmatch(r"[0-9a-f]{64}  [^ ].*", l) for l in linie)
    sumy = W.wczytaj_sumy(tekst)
    # te same rodzaje plików co opublikowany `SHA256SUMS-trzon`: dokumenty, `.txt`, manifest i statystyki (I3)
    assert set(sumy) == {"manifest.jsonl", "statystyki.json", *(w["plik"] for w in wpisy), *(w["plik_txt"] for w in wpisy)}
    assert json.loads((tmp_path / "statystyki.json").read_text(encoding="utf-8")) == W.statystyki(wpisy)
    assert all(sumy[w["plik"]] == w["sha256"] for w in wpisy)
    if shutil.which("sha256sum"):
        (tmp_path / "SUMY").write_text(tekst, encoding="utf-8")
        assert subprocess.run(["sha256sum", "--quiet", "-c", "SUMY"], cwd=tmp_path).returncode == 0


def test_budowa_wieloprocesowa_te_same_bajty_i_opublikowane_sumy(tmp_path):
    """Dwie budowy (1 i 3 procesy) – te same bajty; pliki zgodne z opublikowanymi sumami (formaty z LibreOffice'em i skan)."""
    przypadki = (P.FORMATY_RTF_ODT, P.CYRYLICA_DOKUMENT_UK, P.UKRYTA_XLSX)
    a = W.zbuduj_warstwe(tmp_path / "a", przypadki=przypadki, procesy=1)
    b = W.zbuduj_warstwe(tmp_path / "b", przypadki=przypadki, procesy=3)
    assert a == b and (tmp_path / "a" / "manifest.jsonl").read_bytes() == (tmp_path / "b" / "manifest.jsonl").read_bytes()
    sa, sb = W.wczytaj_sumy(W.sumy_kontrolne(tmp_path / "a")), W.wczytaj_sumy(W.sumy_kontrolne(tmp_path / "b"))
    assert sa == sb
    opublikowane = W.wczytaj_sumy(W.PLIK_SUM.read_text(encoding="utf-8"))
    calosc = ("manifest.jsonl", "statystyki.json")            # pliki całej warstwy – w budowie części inne
    assert {k: v for k, v in sa.items() if k not in calosc} == {k: opublikowane[k] for k in sa if k not in calosc}
    linie = dict(zip((w["id"] for w in a), (tmp_path / "a" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()))
    for i, linia in linie.items():           # wpisy manifestu tych przypadków = wpisy pełnej warstwy
        assert hashlib.sha256(linia.encode()).hexdigest() == BAZA["linie_manifestu"][i], i


def test_pelna_warstwa_daje_opublikowane_sumy(tmp_path):
    """Bieżąca budowa całej warstwy = `metodyka/SHA256SUMS-trudne` (do prerejestracji), a ten plik = linia bazowa."""
    assert hashlib.sha256(W.PLIK_SUM.read_bytes()).hexdigest() == BAZA["sumy_sha256"]
    wpisy = W.zbuduj_warstwe(tmp_path, procesy=4)
    assert len(wpisy) == BAZA["dokumentow"] == sum(r.n for r in W.ROZKLAD.values())
    assert W.sumy_kontrolne(tmp_path, wpisy) == W.PLIK_SUM.read_text(encoding="utf-8")
    plan = {p.id: p for p in W.zaplanuj_warstwe()}
    for w in wpisy:
        assert w["warstwa"] == "trudne" and plan[w["id"]].przypadek in w["przypadki"] and isinstance(w["posrednie"], list)
        assert bool(w["posrednie"]) == (plan[w["id"]].przypadek in P.POSREDNIE)
        assert ("ukryte" in w) == bool(w.get("ukryte")) and w["ostrzezenia"] == []
    assert W.statystyki(wpisy)["po_przypadku_splicie"] == BAZA["po_przypadku_splicie"]


# ----------------------------------------------------------------------------- przegląd językowy (H6b)
@pytest.mark.parametrize("przyimek,wyraz,forma", [
    ("z", "Zbigniewem", "ze"), ("z", "Stępniem", "ze"), ("z", "Szczepańskimi", "ze"), ("z", "Świątkiem", "ze"),
    ("z", "Żmudą", "ze"), ("z", "Zofią", "z"), ("z", "Szymonem", "z"), ("z", "Adamem", "z"), ("Z", "Zdzisławem", "Ze"),
    ("w", "Wrocławiu", "we"), ("w", "Włoszczowie", "we"), ("w", "Warszawie", "w"), ("w", "2021", "w")])
def test_przyimek_z_ze_w_we(przyimek, wyraz, forma):
    assert przyimek_pl(przyimek, wyraz) == forma


def test_przyimek_w_skladaczu_i_szablonach_warstwy_trudnej():
    assert przyimek_przed("Rozmowa z ", "Zbigniewem Nowakiem") == "Rozmowa ze "
    assert przyimek_przed("raz ", "Zbigniewem") is None and przyimek_przed("Rozmowa z ", "Anną") is None
    s = Skladacz("pl")
    e = s.akapit("W nawiązaniu do rozmowy z {b} przypominamy.", b=G("Stanisławem Kowalem", "OSOBA", "b.pelne", "b"))
    assert "".join(f if isinstance(f, str) else f.tekst for f in e.fragmenty) == \
        "W nawiązaniu do rozmowy ze Stanisławem Kowalem przypominamy."
    assert all(not sz.przyimki for sz in SZABLONY.values())                  # trzon bez zmian
    assert all(sz.przyimki == (k[0] == "pl") for k, sz in SZABLONY_TRUDNE.items())
    assert SZABLONY_WSTAWKI[("pl", "protokol")].przyimki and not SZABLONY_WSTAWKI[("de", "notatka")].przyimki


def _teksty(szablon, jezyk: str, ile: int, wariant: str = "cw"):
    for seed in range(ile):
        with zgodna_plec():
            w = zbuduj_z_kontekstem(szablon, Generator(jezyk, seed), random.Random(f"t:{seed}"), wariant)
        yield w, "\n".join("".join(f if isinstance(f, str) else f.tekst for f in e.fragmenty) for e in w.dokument.elementy)


def test_wstawki_formy_zgodne_z_plcia():
    kobiety = 0
    for w, tekst in _teksty(SZABLONY_WSTAWKI[("pl", "protokol")], "pl", 12):
        for rola, m, k in (("powod", "powód", "powódka"), ("pozwany", "pozwany", "pozwana")):
            o = w.osoby[rola]
            forma = k if o.plec == "K" else m
            kobiety += o.plec == "K"
            assert f"{forma} {o.pelne_imie}" in tekst, (rola, o.pelne_imie)
    assert kobiety
    for w, tekst in _teksty(SZABLONY_WSTAWKI[("de", "notatka")], "de", 8):
        o = w.osoby["dolmetscher"]
        assert ("der Dolmetscherin " if o.plec == "K" else "des Dolmetschers ") + o.pelne_imie in tekst


def test_szablony_warstwy_trudnej_formy_zgodne_z_plcia():
    for w, tekst in _teksty(SZABLONY_TRUDNE[("pl", "notatka")], "pl", 6, None):
        assert ("Sporządziła: " if w.osoby["autor"].plec == "K" else "Sporządził: ") + w.osoby["autor"].pelne_imie in tekst
    for w, tekst in _teksty(SZABLONY_TRUDNE[("pl", "prezentacja")], "pl", 6, None):
        assert ("z Prezes Zarządu, " if w.osoby["prezes"].plec == "K" else "z Prezesem Zarządu, ") in tekst
    _, tekst = next(_teksty(SZABLONY[("pl", "prezentacja")], "pl", 1, None))     # trzon: forma stała
    assert "z Prezesem Zarządu, " in tekst


def test_protokol_formy_zgodne_z_plcia_fix1():
    """H6b-fix1 (M1): Prezes Zarządu „która stwierdza”, tłumaczka „została pouczona”, protokolantka – tylko warstwa trudna."""
    kobiety = 0
    for w, tekst in _teksty(SZABLONY_TRUDNE[("pl", "protokol")], "pl", 8, None):
        o = w.osoby["prezes"]
        kobiety += o.plec == "K"
        assert f"{o.pelne_imie}, Prezes Zarządu, {'która' if o.plec == 'K' else 'który'} stwierdza" in tekst
    assert kobiety
    _, tekst = next(_teksty(SZABLONY[("pl", "protokol")], "pl", 1, None))     # trzon: forma stała
    assert "Prezes Zarządu, który stwierdza" in tekst
    kobiety = 0
    for w, tekst in _teksty(SZABLONY_WSTAWKI[("pl", "protokol")], "pl", 12):
        t, p = w.osoby["tlumacz"], w.osoby["protokolant"]
        kobiety += t.plec == "K"
        assert ("Tłumaczka została pouczona" if t.plec == "K" else "Tłumacz został pouczony") in tekst
        assert ("tłumaczka przysięgła" if t.plec == "K" else "tłumacz przysięgły") in tekst
        assert ("protokolantka: " if p.plec == "K" else "protokolant: ") + p.pelne_imie in tekst
    assert kobiety


def test_pieczatka_etykiety_w_jezyku_dokumentu():
    """H6b-fix1 (M2): etykiety identyfikatorów na pieczątce z kraju firmy (nie nazwy kategorii, np. „NR REJESTRU”)."""
    from pbench import trudne_pliki as TPl
    for jezyk, kraje in (("pl", ("PL",)), ("en", ("GB", "US")), ("es", ("ES",)), ("de", ("DE",)), ("fr", ("FR",))):
        g = Generator(jezyk, 3)
        for kraj in kraje:
            for _ in range(5):
                assert set(g.firma(kraj=kraj).rejestry) <= set(TPl.ETYKIETY_PIECZATKI[kraj]), kraj
    pary = sorted(TPl.GENERATORY[P.SKAN_PIECZATKI])
    for jezyk in ("en", "es", "de", "fr"):
        typ = next(t for j, t in pary if j == jezyk)
        for seed in range(6):
            wynik, _, _ = TPl._pieczatka(jezyk, typ, seed, "pdf")
            e = wynik.dokument.ukryte[0]
            etykiety = e.atrybuty["etykiety"]
            assert len(etykiety) == len(e.fragmenty) and not any("REJESTRU" in x or "_" in x for x in etykiety)
            for w, x in zip(e.fragmenty, etykiety):
                if w.id.startswith("h.pieczatka.siret"):
                    assert x == "SIRET"
                if w.id.startswith(("h.pieczatka.hrb", "h.pieczatka.hra")):
                    assert x == "" and w.tekst.startswith(("HRB ", "HRA "))


def test_przeniesienie_bez_podzialu_awaryjnego():
    """H6b-fix1 (M3): wyraz bez miejsca podziału na sylaby („Chloé”) nie jest łamany – łamany jest inny wyraz albo nic."""
    from pbench.trudne_pliki import _przenies_wyraz
    assert _przenies_wyraz("Chloé Roy", random.Random(1)) is None
    assert _przenies_wyraz("Chloé Martin", random.Random(1)) == "Chloé Mar-\ntin"


def test_domena_ukrytych_wg_jezyka():
    """H6b-fix1 (M4): domena e-maili treści ukrytej zależy od języka i nie występuje w tekstach szablonów."""
    from pbench.trudne_ukryta import DOMENY_UKRYTYCH
    assert len(set(DOMENY_UKRYTYCH.values())) == len(DOMENY_UKRYTYCH) and "poufne.example" not in DOMENY_UKRYTYCH.values()
    zrodla = " ".join(p.read_text(encoding="utf-8").lower() for p in (KORZEN / "pbench" / "szablony").rglob("*.py"))
    assert not any(d.split(".")[0] in zrodla for d in DOMENY_UKRYTYCH.values())


def test_poczta_funkcje_zgodne_z_plcia_i_daty_kraju():
    from pbench import trudne_poczta as TP
    for jezyk, pary in ((j, TP.TEKSTY[j]["funkcje"]) for j in TP.TEKSTY):
        assert all(isinstance(p, tuple) and len(p) == 2 for p in pary), jezyk
    rng = random.Random(1)
    teraz = datetime(2024, 5, 14, 10, 30)
    assert re.fullmatch(r"\d\d/\d\d/\d{4} \d\d:\d\d", TP._daty(rng, "fr", 1, teraz)[0])
    assert re.fullmatch(r"\d\d\.\d\d\.\d{4} \d\d:\d\d", TP._daty(rng, "de", 1, teraz)[0])
    assert re.fullmatch(r"\d\d/\d\d/\d{4} \d\d:\d\d [AP]M", TP._daty(rng, "en", 1, teraz, "US")[0])


def test_poczta_chronologia_watku_i_strefa():
    """H6b-fix1 (M4): wątek cytowany od najnowszej, cały przed wiadomością główną, w godzinach 8–19; data wysłania między pozwem
    a terminem z treści; strefa wg kraju i czasu letniego."""
    from pbench import trudne_poczta as TP
    for seed in range(30):
        teraz = datetime(2024, 3, 1 + seed % 28, 9 + seed % 9, seed)
        daty = [datetime.strptime(d, "%d.%m.%Y %H:%M") for d in TP._daty(random.Random(seed), "pl", 5, teraz)]
        assert daty == sorted(daty, reverse=True) and daty[0] < teraz and all(8 <= d.hour < 20 for d in daty), seed
    assert TP.strefa("PL", datetime(2024, 1, 10)).utcoffset(None).total_seconds() == 3600
    assert TP.strefa("DE", datetime(2024, 7, 10)).utcoffset(None).total_seconds() == 7200
    assert TP.strefa("GB", datetime(2024, 7, 10)).utcoffset(None).total_seconds() == 3600
    assert TP.strefa("FR", datetime(2024, 10, 27)).utcoffset(None).total_seconds() == 3600     # ostatnia niedziela października
    assert TP.strefa("US", datetime(2024, 3, 10)).utcoffset(None).total_seconds() == -4 * 3600
    for seed in range(20):
        wynik, _ = TP._baza("pl", "email", seed, "cv")
        chwila = TP.wyslano(wynik, seed)
        assert wynik.kontekst.daty["pozew"] <= chwila.date() < wynik.kontekst.daty["odp_termin"] and chwila.weekday() < 5


def test_poprawki_tekstow_generatorow():
    from pbench import trudne_jezyk as TJ, trudne_posrednie as TPo, trudne_ukryta as TU
    assert "se présenteraient" in TJ._TRESC_ZDROBNIENIA["fr"]["p5"]                       # zgodność czasów po „a été convenu”
    assert TPo._TRESC_FUNKCJI["pl"]["przedstawiciel"] == "przedstawicielem|przedstawicielką"
    assert TPo._TRESC_OGLEDZIN["pl"]["dz"] == "Nieruchomość stanowi działkę ewidencyjną nr {dzialka}."
    assert TU.opis("fr", "Amandine Roger") == "Photo d'" and TU.opis("fr", "Jean Roy") == "Photo de "
    assert TU.opis("pl", "Anna Nowak") == "Zdjęcie: "
    assert TU.dwukropek("fr") == " : " and TU.dwukropek("pl") == ": "


def test_skoroszyt_osadzony_bez_czasu_zapisu():
    """Obiekt osadzony DOCX (`ukryta_docx`): `dcterms:modified` stałe, nie czas zapisu (bajty niezależne od chwili budowy)."""
    import io
    import zipfile
    from pbench.ukryta_docx import skoroszyt_osadzony
    bajty = skoroszyt_osadzony([("Klient", "Jan Nowak")])
    core = zipfile.ZipFile(io.BytesIO(bajty)).read("docProps/core.xml").decode()
    assert "2024-01-01T00:00:00Z</dcterms:modified>" in core
