"""Testy generatora korpusu: plan (rozkład, typy, split), wspólny kontekst załącznika, manifest i determinizm."""
from __future__ import annotations

import json
import random
import re
from collections import Counter
from pathlib import Path

import pytest

from pbench import korpus
from pbench.dane import Generator
from pbench.budowa import zbuduj_z_kontekstem
from pbench.szablony import JEZYKI, SZABLONY

FORMATY = ("docx", "pdf", "skan", "xlsx", "pptx", "eml", "msg", "doc")


def _manifest(cel: Path) -> list[dict]:
    return [json.loads(w) for w in (cel / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]


# ----------------------------------------------------------------------------- plan
def test_rozklad_jezykow():
    plan = korpus.zaplanuj(korpus.ZIARNO)
    suma = len(plan)
    assert suma == 1000
    licz = Counter(p.jezyk for p in plan)
    assert licz["pl"] == 500
    for j in JEZYKI:
        oczekiwane = 500 if j == "pl" else 125
        assert abs(licz[j] - oczekiwane) / suma <= 0.02
    for j in JEZYKI:
        n = licz[j]
        for fmt, udzial in korpus.UDZIALY_FORMATOW:
            ile = sum(1 for p in plan if p.jezyk == j and p.format == fmt)
            assert abs(ile - n * udzial / 100) <= 1, (j, fmt, ile)
        assert sum(1 for p in plan if p.jezyk == j) == n


def test_typ_dobrany_do_formatu():
    dozwolone = {
        "xlsx": {"lista_plac", "faktura"}, "pptx": {"prezentacja"}, "eml": {"email"}, "msg": {"email"},
    }
    papierowe = set(korpus.TYPY_SKANU)
    tekstowe_wykluczone = {"lista_plac", "prezentacja", "email"}
    for p in korpus.zaplanuj(korpus.ZIARNO):
        assert (p.jezyk, p.typ) in SZABLONY
        if p.format in dozwolone:
            assert p.typ in dozwolone[p.format]
        elif p.format == "skan":
            assert p.typ in papierowe
        else:
            assert p.typ not in tekstowe_wykluczone
    assert not any(p.typ == "med_skierowanie" for p in korpus.zaplanuj(korpus.ZIARNO) if p.jezyk != "pl")


def test_typy_w_formacie_zrownowazone():
    """Zwykłe typy w formacie różnią się najwyżej o 1; typy prywatne też; medyczne mają osobny budżet."""
    plan = korpus.zaplanuj(korpus.ZIARNO)
    for j in JEZYKI:
        for fmt in ("docx", "pdf", "skan", "doc", "xlsx"):
            licz = Counter(p.typ for p in plan if p.jezyk == j and p.format == fmt)
            zwykle = [n for t, n in licz.items() if t not in korpus.TYPY_MEDYCZNE and t not in korpus.TYPY_PRYWATNE]
            assert max(zwykle) - min(zwykle) <= 2, (j, fmt, licz)
            prywatne = [licz.get(t, 0) for t in korpus.TYPY_PRYWATNE]
            if fmt != "xlsx":
                assert max(prywatne) - min(prywatne) <= 1, (j, fmt, licz)
            else:
                assert not any(prywatne) and not any(t in korpus.TYPY_MEDYCZNE for t in licz)


def test_rozklad_typow_67_medycznych_i_67_prywatnych_na_1000():
    """Dokumenty medyczne 67 z 1000, proporcje 27 : 28 : 12, a zwolnione 67 miejsc to
    dokumenty prywatne rozłożone 23 / 22 / 22 – także dla innych ziaren (liczba medycznych w planie wyjściowym zależy od ziarna)."""
    for ziarno in (korpus.ZIARNO, 20261029, 1, 2, 3, 77):
        plan = korpus.zaplanuj(ziarno)
        licz = Counter(p.typ for p in plan)
        assert len(plan) == 1000 and len({p.id for p in plan}) == 1000
        assert [licz[t] for t in korpus.TYPY_MEDYCZNE] == [27, 28, 12], ziarno
        assert sum(licz[t] for t in korpus.TYPY_MEDYCZNE) == korpus.LICZBA_MEDYCZNYCH == 67
        assert sorted(licz[t] for t in korpus.TYPY_PRYWATNE) == [22, 22, 23], ziarno
        assert sum(licz[t] for t in korpus.TYPY_PRYWATNE) == korpus.LICZBA_PRYWATNYCH == 67
        assert plan == korpus.zaplanuj(ziarno)
        assert all(p.jezyk == "pl" for p in plan if p.typ == "med_skierowanie")


def test_typy_prywatne_we_wszystkich_jezykach_i_formatach_dokumentowych():
    plan = korpus.zaplanuj(korpus.ZIARNO)
    prywatne = [p for p in plan if p.typ in korpus.TYPY_PRYWATNE]
    assert {p.jezyk for p in prywatne} == set(JEZYKI)
    assert {p.format for p in prywatne} == {"docx", "pdf", "skan", "doc"}
    assert set(korpus.TYPY_PRYWATNE) <= set(korpus.TYPY_SKANU)
    for j in JEZYKI:
        assert all((j, t) in SZABLONY for t in korpus.TYPY_PRYWATNE)
        assert {p.typ for p in prywatne if p.jezyk == j} == set(korpus.TYPY_PRYWATNE) or j != "pl"


def test_id_unikalne_i_bez_pii():
    plan = korpus.zaplanuj(korpus.ZIARNO)
    ids = [p.id for p in plan]
    assert len(set(ids)) == len(ids)
    for p in plan:
        assert re.fullmatch(rf"{p.jezyk}-{p.typ}-\d{{4}}", p.id), p.id


def test_plan_deterministyczny_i_limit():
    a = korpus.zaplanuj(korpus.ZIARNO, limit=30)
    b = korpus.zaplanuj(korpus.ZIARNO, limit=30)
    assert a == b and len(a) == 30
    assert a == sorted(a, key=lambda p: p.id)
    pelny = {p.id: p for p in korpus.zaplanuj(korpus.ZIARNO)}
    assert all(pelny[p.id] == p for p in a)  # --limit nie zmienia identyfikatorów


def test_split_rozlaczny_i_stratyfikowany():
    plan = korpus.zaplanuj(korpus.ZIARNO)
    split = korpus.przydziel_split(plan, korpus.ZIARNO)
    assert set(split) == {p.id for p in plan}
    assert set(split.values()) == {"dev", "test"}
    dev = sum(1 for s in split.values() if s == "dev")
    assert abs(dev - 0.2 * len(plan)) <= 1
    for j in JEZYKI:   # każdy język ma ~20% dev
        n_j = sum(1 for p in plan if p.jezyk == j)
        assert abs(sum(1 for p in plan if p.jezyk == j and split[p.id] == "dev") - 0.2 * n_j) <= 1, j
    warstwy: dict[tuple, list[str]] = {}
    for p in plan:
        warstwy.setdefault((p.jezyk, p.typ, p.format), []).append(split[p.id])
    for klucz, lista in warstwy.items():
        assert abs(lista.count("dev") - 0.2 * len(lista)) < 1, (klucz, lista)
    assert split == korpus.przydziel_split(plan, korpus.ZIARNO)


def test_split_niezalezny_od_kolejnosci_listy():
    plan = korpus.zaplanuj(korpus.ZIARNO, limit=200)
    odwrocony = list(reversed(plan))
    assert korpus.przydziel_split(plan, korpus.ZIARNO) == korpus.przydziel_split(odwrocony, korpus.ZIARNO)


def test_utrudnienia_zalezne_tylko_od_ziarna_dokumentu():
    plan = korpus.zaplanuj(korpus.ZIARNO)
    p = next(p for p in plan if p.format == "docx")
    wynik = korpus.losuj_utrudnienia(p, korpus.ZIARNO, ma_podpis=True)
    assert wynik == korpus.losuj_utrudnienia(p, korpus.ZIARNO, ma_podpis=True)
    assert "podpis" not in korpus.losuj_utrudnienia(p, korpus.ZIARNO, ma_podpis=False)
    wiele = Counter(u for q in plan if q.format == "docx" for u in korpus.losuj_utrudnienia(q, korpus.ZIARNO, True))
    n = sum(1 for q in plan if q.format == "docx")
    assert 0.5 < wiele["tabele"] / n < 0.7
    assert wiele["papier_firmowy"] / n > wiele["tabele"] / n


# ----------------------------------------------------------------------------- wspólny kontekst
def test_zalacznik_dzieli_osoby_z_emailem():
    import random as r
    gen = Generator("pl", 7)
    mail = zbuduj_z_kontekstem(SZABLONY[("pl", "email")], gen, r.Random(7))
    zal = zbuduj_z_kontekstem(SZABLONY[("pl", "notatka")], gen, r.Random(8), wspolne=mail)
    assert zal.kontekst is mail.kontekst
    wspolne = {"klient", "przeciwnik", "swiadek"} & set(zal.osoby)
    assert wspolne
    for rola in wspolne:
        assert zal.osoby[rola] is mail.osoby[rola]
    # ta sama osoba: te same wartości (PESEL) w obu dokumentach, jeśli występują
    teksty_m = {w.tekst for e in mail.dokument.elementy for w in e.fragmenty if not isinstance(w, str)}
    teksty_z = {w.tekst for e in zal.dokument.elementy for w in e.fragmenty if not isinstance(w, str)}
    assert teksty_m & teksty_z


def test_budowa_bez_wspolnego_kontekstu_bez_zmian():
    a = zbuduj_z_kontekstem(SZABLONY[("pl", "umowa")], Generator("pl", 3), random.Random(3)).dokument
    b = zbuduj_z_kontekstem(SZABLONY[("pl", "umowa")], Generator("pl", 3), random.Random(3), wspolne=None).dokument
    assert a.to_json() == b.to_json()


# ----------------------------------------------------------------------------- generacja
def _sprawdz_wpis(cel: Path, w: dict) -> None:
    assert (cel / w["plik"]).is_file() and (cel / w["plik_txt"]).is_file()
    assert w["split"] in ("dev", "test")
    assert w["utrudnienia"] == sorted(w["utrudnienia"])
    tekst = (cel / w["plik_txt"]).read_text(encoding="utf-8")
    ostatni = 0
    for g in w["gold_tekst"]:
        assert 0 <= g["start"] < g["end"] <= len(tekst)
        assert g["start"] >= ostatni
        ostatni = g["end"]
        assert tekst[g["start"]:g["end"]] == g["tekst"]
        assert {"wartosc_id", "kategoria", "miejsce"} <= set(g)
    assert all({"id", "kategoria", "tekst", "miejsce", "waga_klucz"} <= set(v) for v in w["gold_plik"])
    assert isinstance(w["gold_obrazy"], list) and isinstance(w["ostrzezenia"], list)


@pytest.mark.parametrize("fmt", FORMATY)
def test_format_powstaje_z_gold_zgodnym_z_txt(tmp_path, fmt):
    korpus.generuj(tmp_path, korpus.ZIARNO, procesy=1, limit=1, jezyki=("pl",), formaty=(fmt,), postep=False)
    wpisy = _manifest(tmp_path)
    assert len(wpisy) == 1
    w = wpisy[0]
    assert w["format"] == fmt and w["jezyk"] == "pl"
    _sprawdz_wpis(tmp_path, w)
    assert Path(w["plik"]).suffix == (".pdf" if fmt == "skan" else f".{fmt}")
    ids_pliku = {v["id"] for v in w["gold_plik"]}
    if fmt in ("docx", "pdf", "xlsx", "pptx"):  # wartości tekstu poziomu 1 leżą w pliku
        assert {g["wartosc_id"] for g in w["gold_tekst"]} <= ids_pliku
    if fmt == "skan":
        assert w["gold_plik"] and all(v["miejsce"] == "obraz" for v in w["gold_plik"])
        assert w["gold_obrazy"] and all(o["ramki"] for o in w["gold_obrazy"])
    if fmt in ("eml", "msg"):
        assert w["typ"] == "email"


def test_email_z_zalacznikiem_ma_gold_zalacznika(tmp_path):
    korpus.generuj(tmp_path, korpus.ZIARNO, procesy=1, limit=60, jezyki=("pl", "en"), formaty=("eml", "msg"),
                   postep=False)
    z_zal = [w for w in _manifest(tmp_path) if "zalacznik" in w["utrudnienia"]]
    assert z_zal
    for w in z_zal:
        assert any(v["id"].startswith("zal:") and v["miejsce"] == "zalacznik" for v in w["gold_plik"])
        assert "utrudnienia_zalacznika" in w


def test_generacja_deterministyczna_i_niezalezna_od_procesow(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    korpus.generuj(a, korpus.ZIARNO, procesy=1, limit=10, jezyki=("en", "de"), postep=False)
    korpus.generuj(b, korpus.ZIARNO, procesy=2, limit=10, jezyki=("en", "de"), postep=False)
    ma, mb = (a / "manifest.jsonl").read_bytes(), (b / "manifest.jsonl").read_bytes()
    assert ma == mb
    for w in _manifest(a):
        assert (a / w["plik"]).read_bytes() == (b / w["plik"]).read_bytes()
        assert (a / w["plik_txt"]).read_bytes() == (b / w["plik_txt"]).read_bytes()
        _sprawdz_wpis(a, w)
    ids = [w["id"] for w in _manifest(a)]
    assert ids == sorted(ids)


def test_cli_limit(tmp_path):
    korpus.main(["--cel", str(tmp_path), "--limit", "2", "--procesy", "1", "--jezyki", "fr", "--formaty", "docx"])
    assert len(_manifest(tmp_path)) == 2
