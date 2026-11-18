"""Testy warstwy trudnych przypadków (H1): rejestr przypadków, plan, split, determinizm, TRZON BEZ ZMIAN BAJTOWYCH
(sumy sha256 sprzed warstwy), manifest, gold z oznaczeniami (transliteracja, encja, cechy), przykładowa budowa 30 dokumentów."""
from __future__ import annotations

import hashlib
import json
import random
import re
from collections import Counter
from pathlib import Path

import pytest

from pbench import korpus, przypadki as P, trudne
from pbench.budowa import zbuduj_z_kontekstem
from pbench.dane import Generator
from pbench.model import Dokument, Wartosc
from pbench.szablony import SZABLONY

BAZA = json.loads((Path(__file__).parent / "dane_testowe" / "trzon_baseline.json").read_text(encoding="utf-8"))
FORMATY_PLAN = {"docx", "pdf", "skan", "doc", "eml", "msg"}


def _manifest(cel: Path) -> list[dict]:
    return [json.loads(w) for w in (cel / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]


# ----------------------------------------------------------------------------- TRZON BEZ ZMIAN
def test_trzon_drzewa_wszystkich_1000_dokumentow_bez_zmian():
    plan = korpus.zaplanuj(korpus.ZIARNO)
    assert len(plan) == 1000 and len(BAZA["drzewa"]) == 1000
    for p in plan:
        seed = korpus.ziarno_dokumentu(korpus.ZIARNO, p.id)
        w = zbuduj_z_kontekstem(SZABLONY[(p.jezyk, p.typ)], Generator(p.jezyk, seed), random.Random(f"pbench-korpus:{seed}"))
        d = w.dokument
        d.id, d.format = p.id, p.format
        assert hashlib.sha256(d.to_json().encode()).hexdigest() == BAZA["drzewa"][p.id], p.id
    suma = hashlib.sha256("\n".join(f"{k}:{v}" for k, v in sorted(BAZA["drzewa"].items())).encode()).hexdigest()
    assert suma == BAZA["suma_drzew"]


def test_trzon_pliki_teksty_i_manifest_bez_zmian_bajtowych(tmp_path):
    wpisy = korpus.generuj(tmp_path, korpus.ZIARNO, procesy=1, limit=BAZA["limit_plikow"], postep=False)
    assert hashlib.sha256((tmp_path / "manifest.jsonl").read_bytes()).hexdigest() == BAZA["manifest_sha256"]
    assert {w["format"] for w in wpisy} == {"doc", "docx", "eml", "msg", "pdf", "pptx", "skan", "xlsx"}
    for w in wpisy:
        assert [hashlib.sha256((tmp_path / w["plik"]).read_bytes()).hexdigest(),
                hashlib.sha256((tmp_path / w["plik_txt"]).read_bytes()).hexdigest()] == BAZA["pliki"][w["id"]], w["id"]
        assert not {"warstwa", "przypadki", "posrednie", "translit", "encja", "cechy"} & set(w)
        assert all(not {"translit", "encja", "cechy"} & set(g) for g in w["gold_tekst"] + w["gold_plik"])


def test_plan_trzonu_nie_zawiera_warstwy_trudnej():
    plan = korpus.zaplanuj(korpus.ZIARNO)
    assert len(plan) == 1000 and not any(p.jezyk == "uk" or p.id.startswith("h-") for p in plan)


def test_wartosc_serializacja_zachowuje_stary_format():
    w = Wartosc("a.pelne#1", "OSOBA", "Jan", "pl", "tresc", "OSOBA")
    assert w.to_dict() == {"id": "a.pelne#1", "kategoria": "OSOBA", "tekst": "Jan", "jezyk": "pl", "miejsce": "tresc",
                           "waga_klucz": "OSOBA"}
    z = Wartosc("a.pelne#1", "OSOBA", "Ołeksandr", "pl", "tresc", "OSOBA", "polski", "a", ["pisownia_rosyjska"])
    assert Wartosc.from_dict(z.to_dict()) == z and z.to_dict()["translit"] == "polski"
    assert Wartosc.from_dict(w.to_dict()) == w
    d = Dokument("x", "pl", "umowa", "docx")
    assert Dokument.from_json(d.to_json()).to_json() == d.to_json()


# ----------------------------------------------------------------------------- rejestr przypadków
def test_rejestr_przypadkow_obejmuje_wszystkie_punkty_spec_11():
    assert len(P.PRZYPADKI) >= 30 and all(isinstance(v, str) and v for v in P.PRZYPADKI.values())
    for nazwa in ("granica_okna", "cyrylica_dokument_uk", "cyrylica_wstawka", "transliteracja", "homoglify",
                  "pisownia_rosyjska_imion", "ukryta_docx", "ukryta_xlsx", "ukryta_pptx", "ukryta_pdf", "ukryta_poczta",
                  "odmiana_nazwisk", "parafy", "liczby_slownie", "posrednie_funkcja_firma", "skroty_po_pelnym",
                  "dlugie_listy_osob", "znaki_zerowej_szerokosci", "rtl", "zepsuty_tounicode", "przenies" "ienia",
                  "dwie_kolumny", "obrocone_strony", "skan_pieczatki", "zrzut_ekranu", "znak_wodny",
                  "cytowane_watki_vcard", "formaty_rtf_odt"):
        assert nazwa in P.PRZYPADKI, nazwa
    assert P.POSREDNIE <= set(P.PRZYPADKI) and len(P.POSREDNIE) == 4
    assert P.CYRYLICA_UKRAINSKA == set(P.H1) and set(P.SKROTY) == (set(P.H1) | set(P.H2) | set(P.H3) | set(P.H4A) | set(P.H4B)
                                                                   | set(P.H5))
    assert len(set(P.SKROTY.values())) == len(P.SKROTY) == 34
    with pytest.raises(ValueError):
        P.sprawdz(["nie_ma_takiego"])
    P.sprawdz(list(P.H1))


# ----------------------------------------------------------------------------- plan
@pytest.mark.parametrize("przypadek", P.H1)
def test_plan_przypadku_ids_formaty_split_determinizm(przypadek):
    plan = trudne.zaplanuj_przypadek(przypadek, 30)
    assert len(plan) == 30 and plan == trudne.zaplanuj_przypadek(przypadek, 30) and plan == sorted(plan, key=lambda p: p.id)
    ids = [p.id for p in plan]
    assert len(set(ids)) == 30
    for p in plan:
        assert re.fullmatch(rf"h-{P.SKROTY[przypadek]}-{p.jezyk}-{p.typ}-\d{{4}}", p.id) and p.przypadek == przypadek
        assert p.format in korpus.ROZSZERZENIA and p.format in trudne.formaty_dla(p.jezyk, p.typ)
    split = trudne.przydziel_split(plan)
    assert set(split) == set(ids) and set(split.values()) <= {"dev", "test"}
    assert sum(1 for s in split.values() if s == "dev") in range(4, 9)             # ~20% ± zaokrąglenia warstw
    assert plan != trudne.zaplanuj_przypadek(przypadek, 30, ziarno=1)


def test_plan_osobne_ziarno_i_katalog_id_nie_koliduje_z_trzonem():
    wszystkie = [p.id for pr in P.H1 for p in trudne.zaplanuj_przypadek(pr, 60)]
    assert len(set(wszystkie)) == len(wszystkie)
    trzon = {p.id for p in korpus.zaplanuj(korpus.ZIARNO)}
    assert not set(wszystkie) & trzon and trudne.ZIARNO_TRUDNE != korpus.ZIARNO


def test_plan_pokrywa_jezyki_typy_i_formaty():
    cu = trudne.zaplanuj_przypadek(P.CYRYLICA_DOKUMENT_UK, 60)
    assert {p.jezyk for p in cu} == {"uk"} and {p.typ for p in cu} == {"cv", "email", "med_zaswiadczenie", "notatka",
                                                                       "pelnomocnictwo", "umowa"}
    assert {p.format for p in cu} == FORMATY_PLAN
    assert all((p.typ == "email") == (p.format in ("eml", "msg")) for p in cu)
    cw = trudne.zaplanuj_przypadek(P.CYRYLICA_WSTAWKA, 60)
    assert {p.jezyk for p in cw} == {"pl", "en", "de"} and {p.format for p in cw} == {"docx", "pdf", "skan", "doc"}
    hg = trudne.zaplanuj_przypadek(P.HOMOGLIFY, 80)
    assert {p.jezyk for p in hg} == {"pl", "en", "es", "de", "fr"}
    assert Counter(p.jezyk for p in hg)["pl"] >= 30 and {"xlsx", "pptx", "eml", "msg"} <= {p.format for p in hg}


def test_przypadek_bez_generatora_jest_bledem():
    with pytest.raises(ValueError):            # od H5 każdy przypadek rejestru ma generator – nazwa spoza rejestru
        trudne.zaplanuj_przypadek("nie_ma_takiego", 10)


# ----------------------------------------------------------------------------- przykładowa budowa (30 dokumentów)
def _sprawdz_wpis(cel: Path, w: dict, przypadek: str) -> None:
    assert (cel / w["plik"]).is_file() and (cel / w["plik_txt"]).is_file()
    assert w["warstwa"] == "trudne" and w["posrednie"] == [] and przypadek in w["przypadki"]
    assert w["przypadki"] == sorted(set(w["przypadki"])) and set(w["przypadki"]) <= set(P.PRZYPADKI)
    assert w["split"] in ("dev", "test") and w["id"].startswith("h-")
    tekst = (cel / w["plik_txt"]).read_text(encoding="utf-8")
    ostatni = 0
    for g in w["gold_tekst"]:
        assert g["start"] >= ostatni and tekst[g["start"]:g["end"]] == g["tekst"]
        ostatni = g["end"]
    assert all({"id", "kategoria", "tekst", "miejsce"} <= set(v) for v in w["gold_plik"])
    assert w["ostrzezenia"] == []


@pytest.fixture(scope="module")
def warstwa(tmp_path_factory) -> dict[str, tuple[Path, list[dict]]]:
    wynik = {}
    for przypadek in P.H1:
        cel = tmp_path_factory.mktemp(przypadek)
        wynik[przypadek] = (cel, trudne.zbuduj_przypadek(cel, przypadek, 30, procesy=1))
    return wynik


@pytest.mark.parametrize("przypadek", P.H1)
def test_przykladowa_budowa_30_dokumentow(warstwa, przypadek):
    cel, wpisy = warstwa[przypadek]
    assert len(wpisy) == 30 and wpisy == _manifest(cel) and [w["id"] for w in wpisy] == sorted(w["id"] for w in wpisy)
    for w in wpisy:
        _sprawdz_wpis(cel, w, przypadek if przypadek != P.PISOWNIA_ROSYJSKA_IMION else P.PISOWNIA_ROSYJSKA_IMION)
    assert {w["split"] for w in wpisy} == {"dev", "test"}
    assert len({w["format"] for w in wpisy}) >= 4


def test_cyrylica_dokument_uk_gold_i_jezyk(warstwa):
    cel, wpisy = warstwa[P.CYRYLICA_DOKUMENT_UK]
    for w in wpisy:
        assert w["jezyk"] == "uk" and w["przypadki"] == [P.CYRYLICA_DOKUMENT_UK]
        kat = {g["kategoria"] for g in w["gold_tekst"]}
        assert "OSOBA" in kat and "ADRES" in kat
        assert any(g["kategoria"] == "NR_PODATKOWY" for g in w["gold_tekst"]) or w["typ"] in ("cv", "email", "notatka", "umowa")
        assert all(g["encja"] for g in w["gold_tekst"] if g["wartosc_id"].split(".")[0] != "ctx")
        assert any(re.search("[А-Яа-яІіЇїЄє]", g["tekst"]) for g in w["gold_tekst"])


def test_transliteracja_gold_ma_systemy_i_wspolna_encje(warstwa):
    cel, wpisy = warstwa[P.TRANSLITERACJA]
    systemy_w_korpusie: set[str] = set()
    bez_cyrylicy = 0
    for w in wpisy:
        assert P.TRANSLITERACJA in w["przypadki"] and set(w["uklad_zapisow"]) == {"s1", "s2", "s3", "s4"}
        osoba = [g for g in w["gold_tekst"] if g["wartosc_id"].split(".")[1].startswith("pelne_im")]
        assert osoba
        encje = {g["encja"] for g in osoba}
        assert len(encje) == 1                                           # jedna encja: wszystkie zapisy tej osoby
        sys_dok = {g.get("translit") for g in osoba}
        systemy_w_korpusie |= {s for s in sys_dok if s}
        if None not in sys_dok:
            bez_cyrylicy += 1
            assert P.CYRYLICA_WSTAWKA not in w["przypadki"]
        else:
            assert P.CYRYLICA_WSTAWKA in w["przypadki"]
        assert len({g["tekst"] for g in osoba}) >= 2
    assert len(systemy_w_korpusie) >= 4 and bez_cyrylicy >= 3


def test_pisownia_rosyjska_oznaczona_w_kazdym_dokumencie(warstwa):
    cel, wpisy = warstwa[P.PISOWNIA_ROSYJSKA_IMION]
    for w in wpisy:
        assert w["jezyk"] in ("pl", "en", "de") and P.PISOWNIA_ROSYJSKA_IMION in w["przypadki"]
        ru = [g for g in w["gold_tekst"] if "pisownia_rosyjska" in g.get("cechy", ())]
        assert ru and all(g["kategoria"] == "OSOBA" for g in ru)
        assert any(re.search("[ыэёъИи]|[Ии]", g["tekst"]) or g["translit"] for g in ru)


def test_homoglify_gold_dokladnie_z_dokumentu(warstwa):
    cel, wpisy = warstwa[P.HOMOGLIFY]
    from pbench.homoglify import mieszane
    for w in wpisy:
        assert w["przypadki"] == [P.HOMOGLIFY]
        h = [g for g in w["gold_tekst"] if "homoglify" in g.get("cechy", ())]
        assert h and all(mieszane(g["tekst"]) and g["encja"] for g in h)
        assert not any("pisownia_rosyjska" in g.get("cechy", ()) for g in w["gold_tekst"])


def test_generacja_deterministyczna_i_niezalezna_od_procesow(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    trudne.zbuduj_przypadek(a, P.TRANSLITERACJA, 6, procesy=1, formaty=("docx", "pdf"))
    trudne.zbuduj_przypadek(b, P.TRANSLITERACJA, 6, procesy=2, formaty=("docx", "pdf"))
    assert (a / "manifest.jsonl").read_bytes() == (b / "manifest.jsonl").read_bytes()
    for w in _manifest(a):
        assert (a / w["plik"]).read_bytes() == (b / w["plik"]).read_bytes()


def test_formaty_wybor_nie_zmienia_identyfikatorow(tmp_path):
    pelny = {p.id for p in trudne.zaplanuj_przypadek(P.CYRYLICA_WSTAWKA, 20)}
    wpisy = trudne.zbuduj_przypadek(tmp_path, P.CYRYLICA_WSTAWKA, 20, formaty=("docx",))
    assert wpisy and {w["id"] for w in wpisy} <= pelny and {w["format"] for w in wpisy} == {"docx"}


def test_cli(tmp_path, capsys):
    assert trudne.main(["--cel", str(tmp_path), "--przypadek", "homoglify", "--n", "4", "--formaty", "docx,pdf"]) == 0
    assert "homoglify dokumentów: 4" in capsys.readouterr().out or len(_manifest(tmp_path)) >= 1
    assert _manifest(tmp_path)
