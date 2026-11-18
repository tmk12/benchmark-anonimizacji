"""Testy dymne uczestników grupy B (zadanie 14): tekstowi (scrubadub, flair, ai4privacy) i plikowi (presidio-wrapper-plikowy,
pdf-redactor, presidio-image-redactor).

Jak w zadaniu 13: każdy uczestnik działa we własnym środowisku uv i jest uruchamiany jako podproces (orkiestrator
`pbench.uruchom.wykonaj`, offline – modele w `vendor/hf`). Tekstowi: zdanie dymne + 2 dokumenty polskie splitu dev; plikowi:
2 pliki polskie splitu dev, a sędzia plikowy (`ocen_plik`) musi je otworzyć (`status == "OK"`). Testy puszczać szeregowo
(`-p no:xdist`): procesy plikowe trzymają pięć modeli NER `presidio-pl-ner`."""
from __future__ import annotations

import json
import re
import subprocess
import tomllib
from pathlib import Path

import pytest

from pbench import uruchom
from pbench.sedzia.plik import leksykon_z_manifestu, ocen_plik
from pbench.sedzia.sanity import wartosci_wpisu
from pbench.sedzia.tekst import RegulyWycieku

KORZEN = Path(__file__).resolve().parent.parent
UCZESTNICY = KORZEN / "uczestnicy"
KORPUS = KORZEN / "korpus"
TEKSTOWI = ("scrubadub", "flair", "ai4privacy")
PLIKOWI = {"presidio-wrapper-plikowy": ("docx", "xlsx", "pptx"), "pdf-redactor": ("pdf", "pdf"),
           "presidio-image-redactor": ("skan", "skan")}
GRUPA = pytest.mark.xdist_group("uczestnicy-oss")


def _wymagania(id_uczestnika: str) -> None:
    if not (KORPUS / "manifest.jsonl").exists():
        pytest.skip("brak korpusu (korpus/manifest.jsonl)")
    if not (UCZESTNICY / id_uczestnika / ".venv").exists():
        pytest.skip(f"brak środowiska uczestnika (uv sync --project uczestnicy/{id_uczestnika})")


# ----------------------------------------------------------------------------- bez procesów
def _zaleznosci(id_uczestnika: str) -> dict[str, str]:
    d = tomllib.loads((UCZESTNICY / id_uczestnika / "pyproject.toml").read_text(encoding="utf-8"))
    return {re.split(r"[=<>!~ ]", z, maxsplit=1)[0].lower(): z for z in d["project"]["dependencies"]}


@pytest.mark.parametrize("id_uczestnika", sorted(PLIKOWI))
def test_plikowi_maja_wersje_presidio_pl_ner(id_uczestnika):
    """Plikowi ładują kod konfiguracji `presidio-pl-ner` (`_wspolne/presidio_plikowe.py`), więc muszą mieć jego wersje."""
    wzor = _zaleznosci("presidio-pl-ner")
    wlasne = _zaleznosci(id_uczestnika)
    assert {k: wlasne.get(k) for k in wzor} == wzor


@pytest.mark.parametrize("id_uczestnika", [*TEKSTOWI, *PLIKOWI])
def test_deklaracja_i_etykiety(id_uczestnika):
    decl = uruchom.wczytaj_deklaracje(UCZESTNICY / id_uczestnika)
    assert decl.jezyki == ("pl", "en", "es", "de", "fr")                 # R37
    assert decl.poziomy == (("plik",) if id_uczestnika in PLIKOWI else ("tekst",))
    from pbench.ocen import zakres_deklarowany
    assert zakres_deklarowany(UCZESTNICY / id_uczestnika)                # miara „w deklarowanym zakresie”
    assert (UCZESTNICY / id_uczestnika / "KONFIG.md").is_file()


# ----------------------------------------------------------------------------- tekstowi (procesy)
# „by email”, nie „at”: wzorzec e-maila scrubadub przyjmuje zapis „x at y” i z „Smith at john.smith@…” bierze „Smith at john.smith”
# (zachowanie narzędzia – KONFIG.md); zdanie sprawdza tylko, że uczestnik działa.
ZDANIE = "Please contact John Smith by email john.smith@example.com about the contract."


def _zapytaj(id_uczestnika: str, tekst: str, jezyk: str) -> tuple[dict, list]:
    env = uruchom.zbuduj_srodowisko(2, offline=True)
    proc = subprocess.run(
        ["uv", "run", "--project", str(UCZESTNICY / id_uczestnika), "python", str(UCZESTNICY / id_uczestnika / "run.py")],
        input=json.dumps({"id": "t-1", "jezyk": jezyk, "tekst": tekst}) + "\n", capture_output=True, text=True,
        encoding="utf-8", env=env, cwd=KORZEN, timeout=900)
    linie = [json.loads(l) for l in proc.stdout.splitlines() if l.strip()]
    assert linie and linie[0].get("gotowy") is True, proc.stderr[-2000:]
    assert len(linie) == 2 and "blad" not in linie[1], (linie, proc.stderr[-2000:])
    return linie[0], linie[1]["wykrycia"]


def _pokryte(wykrycia, tekst, fragment) -> bool:
    s = tekst.index(fragment)
    return all(any(w[0] <= i < w[1] for w in wykrycia) for i in range(s, s + len(fragment)) if not tekst[i].isspace())


@GRUPA
@pytest.mark.parametrize("id_uczestnika", TEKSTOWI)
def test_tekstowy_zdanie_dymne_en(id_uczestnika):
    gotowy, wyk = _zapytaj(id_uczestnika, ZDANIE, "en")
    assert gotowy["wersje"]
    for start, koniec, etykieta, wynik in wyk:
        assert 0 <= start < koniec <= len(ZDANIE) and etykieta and 0.0 <= wynik <= 1.0
    email = "john.smith@example.com"               # flair: ogólny NER (PER/LOC/ORG/MISC), bez e-maili
    if id_uczestnika == "scrubadub":
        assert _pokryte(wyk, ZDANIE, email), wyk
    elif id_uczestnika == "ai4privacy":             # potok HF bez dekodowania pakietu: e-mail wykryty częściowo (KONFIG.md)
        s = ZDANIE.index(email)
        assert any(w[2] == "EMAIL" and w[0] < s + len(email) and w[1] > s for w in wyk), wyk
    if id_uczestnika != "scrubadub":                # scrubadub: same wzorce (bez detektora nazwisk w konfiguracji domyślnej)
        assert _pokryte(wyk, ZDANIE, "John Smith"), wyk


@GRUPA
@pytest.mark.parametrize("id_uczestnika", TEKSTOWI)
def test_tekstowy_2_dokumenty_pl(id_uczestnika, tmp_path):
    _wymagania(id_uczestnika)
    licz = uruchom.wykonaj(uczestnik=id_uczestnika, split="dev", poziom="tekst", korpus=KORPUS, wyniki=tmp_path,
                           uczestnicy=UCZESTNICY, jezyki=("pl",), limit=2, procesy=1, watki=2, offline=True)
    rekordy = [json.loads(l) for l in (tmp_path / "surowe" / id_uczestnika / "dev" / "tekst.jsonl").read_text(
        encoding="utf-8").splitlines() if l.strip()]
    assert len(rekordy) == 2 and all("blad" not in r for r in rekordy), (licz, rekordy)
    manifest = {w["id"]: w for w in uruchom.wczytaj_manifest(KORPUS)}
    for r in rekordy:
        tekst = (KORPUS / manifest[r["id"]]["plik_txt"]).read_bytes().decode("utf-8")
        assert r["wykrycia"], r["id"]
        assert all(0 <= s < e <= len(tekst) for s, e, _, _ in r["wykrycia"]), r["id"]


# ----------------------------------------------------------------------------- plikowi (procesy)
def _mini_korpus(formaty: tuple[str, ...], cel: Path) -> list[dict]:
    """Pierwsze dokumenty polskie splitu dev w podanych formatach (bez list płac – ~1000 wartości, długie)."""
    wpisy, uzyte = [], set()
    for fmt in formaty:
        w = next(w for w in uruchom.wczytaj_manifest(KORPUS) if w["split"] == "dev" and w["jezyk"] == "pl"
                 and w["format"] == fmt and w["typ"] != "lista_plac" and w["id"] not in uzyte)
        uzyte.add(w["id"])
        wpisy.append(w)
    cel.mkdir()
    for w in wpisy:
        (cel / w["plik"]).symlink_to((KORPUS / w["plik"]).resolve())
    (cel / "manifest.jsonl").write_text("\n".join(json.dumps(w, ensure_ascii=False) for w in wpisy) + "\n", encoding="utf-8")
    return wpisy


@GRUPA
@pytest.mark.parametrize("id_uczestnika", sorted(PLIKOWI))
def test_plikowy_2_pliki_pl_ocena_ok(id_uczestnika, tmp_path):
    _wymagania(id_uczestnika)
    wpisy = _mini_korpus(PLIKOWI[id_uczestnika], tmp_path / "korpus")
    uruchom.wykonaj(uczestnik=id_uczestnika, split="dev", poziom="plik", korpus=tmp_path / "korpus", wyniki=tmp_path / "w",
                    uczestnicy=UCZESTNICY, jezyki=("pl",), procesy=1, watki=2, offline=True)
    surowe = tmp_path / "w" / "surowe" / id_uczestnika / "dev"
    rekordy = {r["id"]: r for r in (json.loads(l) for l in (surowe / "plik.jsonl").read_text(encoding="utf-8").splitlines()
                                    if l.strip())}
    reguly = RegulyWycieku.wczytaj(KORZEN / "metodyka" / "prerejestracja.md")
    leksykon = leksykon_z_manifestu(KORPUS / "manifest.jsonl")
    for w in wpisy:
        r = rekordy[w["id"]]
        assert "blad" not in r, r
        wyj = surowe / r["plik_wyj"]
        assert wyj.is_file() and wyj.stat().st_size > 0, r
        assert wyj.read_bytes() != (KORPUS / w["plik"]).read_bytes()                  # plik faktycznie zmieniony
        o = ocen_plik(KORPUS / w["plik"], wyj, wartosci_wpisu(w), reguly, leksykon=leksykon)
        assert o.status == "OK", (w["id"], o.status, o.integralnosc)
        assert len(o.wycieki) < len({x.id for x in wartosci_wpisu(w)}), (w["id"], len(o.wycieki))   # coś zamaskował
