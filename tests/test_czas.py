"""Testy `pbench-czas` (T6/P7): próbka, orkiestracja pomiaru na uczestniku-atrapie (rozgrzewka, błąd/timeout/odmowa, wznawianie,
format zgodny z `agregacja.wczytaj_czasy`) oraz adapter zainstalowanej aplikacji na atrapie serwera HTTP (ciasteczko z adresu startowego)."""
from __future__ import annotations

import http.server
import json
import math
import os
import random
import secrets
import statistics
import shutil
import subprocess
import sys
import threading
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from pbench import agregacja, czas, uruchom

KORZEN = Path(__file__).resolve().parent.parent

# ----------------------------------------------------------------------------- korpus i uczestnik-atrapa
LICZBY_KORPUSU = {"pl": 45, "en": 12, "de": 12, "es": 12, "fr": 12}


def zrob_manifest(korpus: Path, liczby: dict[str, int] = LICZBY_KORPUSU, split_dev: int = 5) -> list[dict]:
    korpus.mkdir(parents=True, exist_ok=True)
    wpisy = []
    for jez, n in liczby.items():
        for split, ile in (("test", n), ("dev", split_dev)):
            for i in range(ile):
                id_dok = f"{jez}-{split}-{i:04d}"
                tekst = ("Jan Kowalski " * (i + 1))[: 400 + 40 * i]
                (korpus / f"{id_dok}.txt").write_text(tekst, encoding="utf-8")
                (korpus / f"{id_dok}.docx").write_bytes(b"PK-" + id_dok.encode())
                wpisy.append({"id": id_dok, "jezyk": jez, "typ": "pozew", "format": "docx", "split": split,
                              "plik": f"{id_dok}.docx", "plik_txt": f"{id_dok}.txt", "gold_tekst": [], "gold_plik": [],
                              "gold_obrazy": []})
    (korpus / "manifest.jsonl").write_text("".join(json.dumps(w) + "\n" for w in wpisy), encoding="utf-8")
    return wpisy


RUN_PY = '''
import json, os, sys, time, shutil
LOG = os.environ.get("CZAS_LOG")
def lista(nazwa): return {i for i in os.environ.get(nazwa, "").split(",") if i}
def wyslij(o):
    sys.stdout.write(json.dumps(o) + "\\n"); sys.stdout.flush()
wyslij({"gotowy": True, "wersje": {"atrapa": "1"}})
for linia in sys.stdin:
    if not linia.strip(): continue
    z = json.loads(linia); i = z["id"]
    if LOG:
        with open(LOG, "a") as f: f.write(i + "\\n")
    if i in lista("CZAS_PADA"): os._exit(3)
    if i in lista("CZAS_WOLNY"): time.sleep(60)
    if i in lista("CZAS_ODMOWA"):
        wyslij({"id": i, "blad": "Odmowa produktu: nie obsluguje"}); continue
    time.sleep(float(os.environ.get("CZAS_SEN", "0.01")))
    if "tekst" in z: wyslij({"id": i, "wykrycia": []})
    else:
        shutil.copyfile(z["plik_wej"], z["plik_wyj"]); wyslij({"id": i, "plik_wyj": z["plik_wyj"]})
'''


@pytest.fixture
def sr(tmp_path, monkeypatch):
    korpus = tmp_path / "korpus"
    manifest = zrob_manifest(korpus)
    ucz = tmp_path / "uczestnicy"
    for nazwa in ("atrapa-czas", "privatizer-tekst"):
        d = ucz / nazwa
        d.mkdir(parents=True)
        shutil.copy(KORZEN / "uczestnicy" / "_atrapa" / "pyproject.toml", d / "pyproject.toml")
        (d / "run.py").write_text(RUN_PY, encoding="utf-8")
        (d / "uczestnik.toml").write_text(
            'poziomy = ["tekst", "plik"]\njezyki = ["pl", "en", "es", "de", "fr"]\nformaty = ["docx"]\ntimeout_s = 5\n',
            encoding="utf-8")
    log = tmp_path / "wywolania.log"
    monkeypatch.setenv("CZAS_LOG", str(log))
    return {"korpus": korpus, "uczestnicy": ucz, "cel": tmp_path / "cel", "log": log, "manifest": manifest, "tmp": tmp_path}


def wywolania(sr) -> list[str]:
    return sr["log"].read_text().split() if sr["log"].exists() else []


def mierz(sr, uczestnik="atrapa-czas", poziom="tekst", proba=None, **kw):
    proba = proba or czas.losuj_probe(uruchom.wczytaj_manifest(sr["korpus"]))
    kw.setdefault("okres_rss", 0.05)
    return czas.zmierz(uczestnik=uczestnik, poziom=poziom, proba=proba, korpus=sr["korpus"], cel=sr["cel"],
                       uczestnicy=sr["uczestnicy"], **kw)


def czasy(sr) -> dict[str, dict]:
    p = sr["cel"] / "czasy.jsonl"
    wynik = {}
    for l in p.read_text(encoding="utf-8").splitlines():
        try:
            wynik[json.loads(l)["id"]] = json.loads(l)
        except (ValueError, KeyError):
            continue                                                        # ucięta linia po przerwaniu – pomijana jak w agregacji
    return wynik


# ----------------------------------------------------------------------------- próbka
def test_proba_ma_60_dokumentow_i_rozklad_jezykow(sr):
    proba = czas.losuj_probe(sr["manifest"])
    assert len(proba) == 60 and len({w["id"] for w in proba}) == 60
    assert Counter(w["jezyk"] for w in proba) == {"pl": 30, "en": 8, "de": 8, "es": 7, "fr": 7}
    assert all(w["split"] == "test" for w in proba)                       # dev nie wchodzi do próbki


def test_proba_deterministyczna_i_zgodna_z_procedura(sr):
    a = czas.losuj_probe(sr["manifest"])
    b = czas.losuj_probe(list(reversed(sr["manifest"])))                  # kolejność manifestu nie ma znaczenia
    assert [w["id"] for w in a] == [w["id"] for w in b]
    for jez, n in czas.ROZKLAD.items():                                   # niezależna reimplementacja procedury z docstringu
        ids = sorted(w["id"] for w in sr["manifest"] if w["split"] == "test" and w["jezyk"] == jez)
        oczekiwane = sorted(random.Random(20261102).sample(ids, n))
        assert [w["id"] for w in a if w["jezyk"] == jez] == oczekiwane
    assert [w["jezyk"] for w in a][:30] == ["pl"] * 30                    # kolejność języków: pl, en, de, es, fr
    assert [w["jezyk"] for w in a][30:38] == ["en"] * 8 and [w["jezyk"] for w in a][-7:] == ["fr"] * 7


def test_proba_jezyk_nie_zalezy_od_pozostalych(sr):
    pelna = czas.losuj_probe(sr["manifest"])
    tylko_en = czas.losuj_probe([w for w in sr["manifest"] if w["jezyk"] == "en"], {"en": 8})
    assert [w["id"] for w in tylko_en] == [w["id"] for w in pelna if w["jezyk"] == "en"]


def test_proba_za_malo_dokumentow_to_blad(sr):
    with pytest.raises(czas.BladProby):
        czas.losuj_probe([w for w in sr["manifest"] if w["jezyk"] != "fr"])


def test_proba_json_zapis_i_niezgodnosc(sr):
    proba = czas.losuj_probe(sr["manifest"])
    p = sr["cel"] / "proba.json"
    czas.zapisz_probe(p, proba)
    d = json.loads(p.read_text())
    assert d["ziarno"] == 20261102 and d["liczba"] == 60 and d["id"] == [w["id"] for w in proba]
    czas.zapisz_probe(p, proba)                                           # ponowny zapis tej samej próbki jest dozwolony
    with pytest.raises(czas.BladProby):
        czas.zapisz_probe(p, proba[1:])


# ----------------------------------------------------------------------------- pomiar: protokół, rozgrzewka, format
def test_kolejnosc_przejsc_rozgrzewka_potem_trzy_pelne_przejscia(sr):
    proba = czas.losuj_probe(uruchom.wczytaj_manifest(sr["korpus"]))
    ids = [w["id"] for w in proba]
    licz = mierz(sr, proba=proba)
    assert licz["ok"] == 60 and licz["nieprzetworzone"] == 0
    rek = czasy(sr)
    for r in rek.values():
        assert r["status"] == "ok" and len(r["pomiary_s"]) == 3 and all(x > 0 for x in r["pomiary_s"])
        assert r["uczestnik"] == "atrapa-czas" and r["poziom"] == "tekst"
    # 1 pełna rozgrzewka po próbce, potem 3 pełne przejścia w tej samej kolejności id (nie 3 pomiary z rzędu)
    assert wywolania(sr) == ids * 4
    # pomiary_s w kolejności przejść = czasy z pomiary.jsonl (rozgrzewka nie trafia do pomiarów)
    pom = [json.loads(l) for l in (sr["cel"] / "pomiary.jsonl").read_text().splitlines()]
    assert [(d["przejscie"], d["id"]) for d in pom] == [(k, i) for k in (1, 2, 3) for i in ids]
    for i in ids:
        assert rek[i]["pomiary_s"] == [round(d["czas_s"], 6) for d in pom if d["id"] == i]
    assert (sr["cel"] / "start.jsonl").read_text().count("\n") == 1


def test_rozgrzewka_zero_i_inne_powtorzenia(sr):
    mierz(sr, rozgrzewka=0, powtorzenia=2)
    assert len(wywolania(sr)) == 120 and len(czasy(sr)) == 60
    assert all(len(r["pomiary_s"]) == 2 for r in czasy(sr).values())


def test_format_zgodny_z_wczytaj_czasy_i_wynik_czasu(sr):
    mierz(sr, rozgrzewka=0)
    znaki = {w["id"]: len((sr["korpus"] / w["plik_txt"]).read_text(encoding="utf-8")) for w in sr["manifest"]}
    for r in czasy(sr).values():
        assert r["znaki"] == znaki[r["id"]]
    wyn = agregacja.wczytaj_czasy(sr["cel"] / "czasy.jsonl", znaki)
    s_na_strone = wyn[("atrapa-czas", "tekst")]
    assert len(s_na_strone) == 60 and all(math.isfinite(x) for x in s_na_strone)
    t, wynik = agregacja.wynik_czasu(s_na_strone)
    assert 0 < t < math.inf and 0 < wynik <= 1.0


def test_poziom_plik_mierzy_pliki_oryginalne(sr):
    licz = mierz(sr, poziom="plik", rozgrzewka=0, powtorzenia=1)
    assert licz["ok"] == 60 and all(r["poziom"] == "plik" for r in czasy(sr).values())
    assert not any((sr["cel"] / "praca").rglob("*.docx"))                  # wyniki plikowe nie zostają na dysku


def test_rss_i_wersje_zapisane(sr):
    mierz(sr, rozgrzewka=0, powtorzenia=1)
    rss = [json.loads(l) for l in (sr["cel"] / "rss.jsonl").read_text().splitlines()]
    assert rss[0]["uczestnik"] == "atrapa-czas" and rss[0]["szczyt_pamieci_mb"] > 0 and rss[0]["probek"] >= 1
    assert rss[0]["metoda_pamieci"] in (czas.METODA_PSS, czas.METODA_FOOTPRINT, czas.METODA_PS)
    assert json.loads((sr["cel"] / "wersje.json").read_text())["atrapa-czas/tekst"]["wersje"]["atrapa"] == "1"


# ----------------------------------------------------------------------------- błędy: brak „szybkiego” wyniku
def test_pad_procesu_to_blad_bez_pomiarow_i_restart(sr, monkeypatch):
    proba = czas.losuj_probe(sr["manifest"])
    zly = proba[3]["id"]
    monkeypatch.setenv("CZAS_PADA", zly)
    licz = mierz(sr, proba=proba)
    r = czasy(sr)[zly]
    assert r["status"] == "blad" and r["pomiary_s"] == [] and "zakończył" in r["blad"]
    assert licz["blad"] == 1 and licz["ok"] == 59
    assert (sr["cel"] / "start.jsonl").read_text().count("restart") >= 1
    wyn = agregacja.wczytaj_czasy(sr["cel"] / "czasy.jsonl", {})
    assert math.isinf(wyn[("atrapa-czas", "tekst")][3])                     # awaria = +∞, nie „szybki” wynik


def test_timeout_to_status_timeout(sr, monkeypatch):
    proba = czas.losuj_probe(sr["manifest"])[:6]
    zly = proba[2]["id"]
    monkeypatch.setenv("CZAS_WOLNY", zly)
    licz = mierz(sr, proba=proba, rozgrzewka=0, timeout=1.0)
    assert czasy(sr)[zly]["status"] == "timeout" and czasy(sr)[zly]["pomiary_s"] == []
    assert licz["timeout"] == 1 and licz["ok"] == 5
    assert wywolania(sr).count(zly) == 3                                    # raz na przejście, bez ponawiania


def test_odmowa_z_odmowy_json(sr, monkeypatch):
    (sr["uczestnicy"] / "atrapa-czas" / "odmowy.json").write_text(
        json.dumps({"komunikaty": ["Odmowa produktu"]}), encoding="utf-8")
    proba = czas.losuj_probe(sr["manifest"])[:4]
    monkeypatch.setenv("CZAS_ODMOWA", proba[1]["id"])
    licz = mierz(sr, proba=proba, rozgrzewka=0)
    assert czasy(sr)[proba[1]["id"]]["status"] == "odmowa" and licz["odmowa"] == 1
    assert math.isinf(agregacja.wczytaj_czasy(sr["cel"] / "czasy.jsonl", {})[("atrapa-czas", "tekst")][1])


def test_blad_uczestnika_bez_odmowy_json_to_blad(sr, monkeypatch):
    proba = czas.losuj_probe(sr["manifest"])[:4]
    monkeypatch.setenv("CZAS_ODMOWA", proba[0]["id"])
    mierz(sr, proba=proba, rozgrzewka=0)
    assert czasy(sr)[proba[0]["id"]]["status"] == "blad"


def test_pominiety_jezyk_i_format_poza_proba(sr):
    (sr["uczestnicy"] / "atrapa-czas" / "uczestnik.toml").write_text(
        'poziomy = ["tekst", "plik"]\njezyki = ["pl"]\nformaty = ["pdf"]\ntimeout_s = 5\n', encoding="utf-8")
    licz = mierz(sr, rozgrzewka=0, powtorzenia=1)
    assert licz["pominiety"] == 30 and licz["ok"] == 30
    rek = czasy(sr)
    assert Counter(r["status"] for r in rek.values()) == {"ok": 30, "pominiety": 30}
    assert len(agregacja.wczytaj_czasy(sr["cel"] / "czasy.jsonl", {})[("atrapa-czas", "tekst")]) == 30   # pominięte poza próbą
    licz = mierz(sr, poziom="plik", rozgrzewka=0, powtorzenia=1)                                          # format docx poza deklaracją
    assert licz["pominiety"] == 60 and licz["ok"] == 0


def test_wznawianie_z_nowa_rozgrzewka_i_brakujacymi_przejsciami(sr):
    proba = czas.losuj_probe(sr["manifest"])
    ids = [w["id"] for w in proba]
    mierz(sr, proba=proba, rozgrzewka=0)
    pom = sr["cel"] / "pomiary.jsonl"
    wiersze = pom.read_text().splitlines()
    pom.write_text("\n".join(wiersze[:150]) + "\n")                        # przerwa: przejścia 1-2 pełne, 3. do połowy
    (sr["cel"] / "czasy.jsonl").unlink()
    sr["log"].unlink()
    licz = mierz(sr, proba=proba)
    assert licz["wczesniej"] == 150 and len(czasy(sr)) == 60
    assert wywolania(sr) == ids + ids[30:]                                  # nowa pełna rozgrzewka, potem tylko brakujące (3, id)
    assert all(len(r["pomiary_s"]) == 3 for r in czasy(sr).values())


def test_wznawianie_naprawia_ucieta_linie(sr):
    proba = czas.losuj_probe(sr["manifest"])[:3]
    mierz(sr, proba=proba, rozgrzewka=0)
    with open(sr["cel"] / "pomiary.jsonl", "ab") as f:
        f.write(b'{"uczestnik": "atrapa-czas", "poz')                       # przerwany zapis
    (sr["cel"] / "czasy.jsonl").unlink()
    licz = mierz(sr, proba=proba, rozgrzewka=0)
    assert licz["wczesniej"] == 9 and licz["nieprzetworzone"] == 0 and len(czasy(sr)) == 3


def test_zloz_pomija_dokumenty_z_niepelnym_kompletem(sr):
    proba = czas.losuj_probe(sr["manifest"])[:4]
    mierz(sr, proba=proba, rozgrzewka=0)
    pom = sr["cel"] / "pomiary.jsonl"
    pom.write_text("\n".join(pom.read_text().splitlines()[:-1]) + "\n")     # brak (3, ostatni id)
    czas.zloz(uczestnik="atrapa-czas", poziom="tekst", proba=proba, korpus=sr["korpus"], cel=sr["cel"], uczestnicy=sr["uczestnicy"])
    assert set(czasy(sr)) == {w["id"] for w in proba[:3]}
    kod = czas.main(["--uczestnik", "atrapa-czas", "--poziom", "tekst", "--korpus", str(sr["korpus"]), "--cel", str(sr["cel"]),
                     "--uczestnicy", str(sr["uczestnicy"]), "--zloz", "--dopusc-niepelne"])
    assert kod == 0 and len(czasy(sr)) == 3


def test_blad_w_trakcie_przejscia_nie_powtarza_rozgrzewki(sr, monkeypatch):
    proba = czas.losuj_probe(sr["manifest"])[:5]
    ids = [w["id"] for w in proba]
    monkeypatch.setenv("CZAS_PADA", ids[2])
    mierz(sr, proba=proba, rozgrzewka=0)
    log = wywolania(sr)
    assert log == ids * 3                                                   # restart po padzie, bez wstawionej rozgrzewki
    assert (sr["cel"] / "start.jsonl").read_text().count("restart") == 3


def test_uczestnik_aplikacji_startuje_polecenie_adaptera(sr, monkeypatch):
    """`ProcesCzas` z `polecenie` (adapter aplikacji) zamiast `run.py` projektu; RSS dla aplikacji z procesu na porcie."""
    monkeypatch.setattr(czas, "APLIKACJA", ("atrapa-czas",))
    monkeypatch.setattr(czas, "polecenie_aplikacji",
                        lambda kat, poziom, port, dane, info, rejestr=None: [sys.executable, str(kat / "run.py")])
    monkeypatch.setattr(czas, "pid_nasluchu", lambda port: os.getpid())
    licz = mierz(sr, rozgrzewka=0, powtorzenia=1, aplikacja_port=8765)
    assert licz["ok"] == 60
    assert json.loads((sr["cel"] / "rss.jsonl").read_text().splitlines()[0])["szczyt_pamieci_mb"] > 0   # pamięć testu (pid z lsof), nie atrapy


def test_aplikacja_wymaga_portu(sr):
    with pytest.raises(uruchom.BladDeklaracji):
        mierz(sr, uczestnik="privatizer-tekst", rozgrzewka=0)


def test_cli_sprawdz_nie_mierzy(sr, capsys):
    kod = czas.main(["--uczestnik", "atrapa-czas", "--poziom", "tekst", "--korpus", str(sr["korpus"]),
                     "--cel", str(sr["cel"]), "--uczestnicy", str(sr["uczestnicy"]), "--sprawdz"])
    wyj = capsys.readouterr().out
    assert "próbka: 60 dokumentów" in wyj and "atrapa-czas/tekst" in wyj
    assert not (sr["cel"] / "czasy.jsonl").exists() and not wywolania(sr)
    assert kod in (0, 2)                                                    # 2 tylko gdy maszyna testowa jest na baterii


def test_cli_pomiar_end_to_end(sr, monkeypatch, capsys):
    monkeypatch.setattr(czas, "srodowisko", lambda: {"host": "t", "na_zasilaczu": True, "tryb_niskiego_zuzycia": 0})
    kod = czas.main(["--uczestnik", "atrapa-czas", "--poziom", "tekst", "--korpus", str(sr["korpus"]), "--cel", str(sr["cel"]),
                     "--uczestnicy", str(sr["uczestnicy"]), "--rozgrzewka", "0", "--powtorzenia", "1"])
    assert kod == 0 and "ok 60" in capsys.readouterr().out
    assert (sr["cel"] / "proba.json").exists() and (sr["cel"] / "srodowisko.json").exists()


def test_cli_odmawia_bez_zasilacza(sr, monkeypatch):
    monkeypatch.setattr(czas, "srodowisko", lambda: {"host": "t", "na_zasilaczu": False, "tryb_niskiego_zuzycia": 1})
    with pytest.raises(SystemExit):
        czas.main(["--uczestnik", "atrapa-czas", "--poziom", "tekst", "--korpus", str(sr["korpus"]), "--cel", str(sr["cel"]),
                   "--uczestnicy", str(sr["uczestnicy"])])
    assert czas.naruszenia_warunkow({"na_zasilaczu": False, "tryb_niskiego_zuzycia": 1}) and \
        not czas.naruszenia_warunkow({"na_zasilaczu": None, "tryb_niskiego_zuzycia": None})


def test_rss_drzewa_liczy_potomkow():
    p = subprocess.Popen([sys.executable, "-c", "import subprocess,sys,time;"
                          "subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);time.sleep(30)"])
    try:
        import time
        time.sleep(0.8)
        assert czas.rss_drzewa_kb([p.pid]) > czas.rss_drzewa_kb([]) == 0
    finally:
        p.kill()


def test_rss_probkowanie_ps_p_i_rzadkie_drzewo(monkeypatch):
    assert czas.OKRES_RSS_S == 1.0 and czas.ODSWIEZANIE_DRZEWA_S == 5.0
    polecenia = []
    prawdziwe = subprocess.run

    def sledz(cmd, *a, **kw):
        polecenia.append(cmd)
        return prawdziwe(cmd, *a, **kw)

    monkeypatch.setattr(czas.subprocess, "run", sledz)
    p = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(30)"])
    try:
        pr = czas.ProbnikRss(lambda: [p.pid], okres=0.05, metoda=czas.METODA_PS).start()
        import time
        koniec = time.monotonic() + 15
        while pr.probek < 3 and time.monotonic() < koniec:
            time.sleep(0.05)
        pr.stop()
    finally:
        p.kill()
    assert pr.szczyt_kb > 0
    drzewa = [c for c in polecenia if c[:2] == ["ps", "-A"]]
    rss = [c for c in polecenia if c[:3] == ["ps", "-o", "rss="] and "-p" in c]
    assert len(drzewa) == 1 and len(rss) >= 3                      # drzewo raz (odświeżane co 5 s), RSS tanim `ps -p`
    assert all(c[:3] != ["ps", "-A", "-o"] or c[-1] == "pid=,ppid=" for c in drzewa)


def test_zloz_z_niepelnymi_kompletami_konczy_sie_bledem(sr, capsys):
    proba = czas.losuj_probe(sr["manifest"])[:4]
    mierz(sr, proba=proba, rozgrzewka=0)
    pom = sr["cel"] / "pomiary.jsonl"
    pom.write_text("\n".join(pom.read_text().splitlines()[:-1]) + "\n")
    argv = ["--uczestnik", "atrapa-czas", "--poziom", "tekst", "--korpus", str(sr["korpus"]), "--cel", str(sr["cel"]),
            "--uczestnicy", str(sr["uczestnicy"]), "--zloz"]
    # próbka CLI to pełne 60 dok. z korpusu, a pomiary dotyczą 4 – reszta to dokumenty bez kompletu
    assert czas.main(argv) == 3
    assert "bez kompletu" in capsys.readouterr().err
    assert czas.main(argv + ["--dopusc-niepelne"]) == 0


def test_srodowisko_oznacza_domniemany_lowpowermode(monkeypatch):
    wyj = {("pmset", "-g", "batt"): "Now drawing from 'AC Power'\n", ("pmset", "-g"): "System-wide power settings:\n sleep 1\n"}
    monkeypatch.setattr(czas, "_polecenie", lambda *a: wyj.get(a))
    sr_ = czas.srodowisko()
    assert sr_["tryb_niskiego_zuzycia"] == 0 and sr_["lowpowermode_domniemane"] is True
    wyj[("pmset", "-g")] = " lowpowermode         0\n"
    assert czas.srodowisko()["lowpowermode_domniemane"] is False




# ----------------------------------------------------------------------------- start bez sieci, pamięć, --limit, --podsumuj
def test_polecenie_uczestnika_ma_frozen_i_no_sync(tmp_path):
    pol = czas.polecenie_uczestnika(tmp_path / "u")
    assert pol[:5] == ["uv", "run", "--frozen", "--no-sync", "--project"] and pol[-1].endswith("run.py")


def test_zmierz_startuje_uczestnika_z_no_sync(sr, monkeypatch):
    polecenia = []
    prawdziwe = subprocess.Popen

    def sledz(cmd, *a, **kw):
        polecenia.append(cmd)
        return prawdziwe(cmd, *a, **kw)

    monkeypatch.setattr(czas.subprocess, "Popen", sledz)
    mierz(sr, rozgrzewka=0, powtorzenia=1, proba=czas.losuj_probe(sr["manifest"])[:2])
    uv = [c for c in polecenia if c[:2] == ["uv", "run"]]
    assert uv and all("--no-sync" in c and "--frozen" in c for c in uv)


def test_sprawdz_wykrywa_brak_zsynchronizowanego_srodowiska(sr, monkeypatch, capsys):
    monkeypatch.delenv("UV_PROJECT_ENVIRONMENT", raising=False)
    proba = czas.losuj_probe(sr["manifest"])
    arg = dict(uczestnicy_ids=["atrapa-czas"], poziom="tekst", proba=proba, korpus=sr["korpus"], cel=sr["cel"],
               uczestnicy=sr["uczestnicy"], aplikacja_port=None, aplikacja_dane=None)
    problemy = czas.sprawdz(**arg)
    assert any("brak zsynchronizowanego środowiska" in p and "uv sync --frozen --project" in p for p in problemy)
    kat = sr["uczestnicy"] / "atrapa-czas" / ".venv"
    kat.mkdir()
    (kat / "pyvenv.cfg").write_text("home = /usr/bin\n")
    assert not any("zsynchronizowanego" in p for p in czas.sprawdz(**arg))


def test_parsowanie_footprint():
    wyj = ("======\npython3.12 [123]: 64-bit    Footprint: 1536 KB (16384 bytes per page)\n======\n"
           "  Dirty    Clean  Reclaimable\n"
           "node [456]: 64-bit    Footprint: 2.5 GB (16384 bytes per page)\nsmieci\n")
    assert czas.parsuj_footprint(wyj) == {123: 1536, 456: int(2.5 * 1024 * 1024)}


def test_pamiec_footprint_sumuje_per_proces(monkeypatch):
    wywolania_ = []

    def fałsz(cmd, *a, **kw):
        wywolania_.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="a [10]: 64-bit    Footprint: 100 MB (16384 bytes per page)\n"
                                                         "b [11]: 64-bit    Footprint: 50 MB (16384 bytes per page)\n")

    monkeypatch.setattr(czas.subprocess, "run", fałsz)
    assert czas.pamiec_pidow_kb([10, 11], [10], czas.METODA_FOOTPRINT) == 150 * 1024
    assert wywolania_[0] == ["footprint", "-p", "10", "-p", "11"]


def test_pamiec_zapas_ps_to_glowny_plus_najwiekszy_potomek(monkeypatch):
    monkeypatch.setattr(czas, "rss_wg_pidow", lambda pidy: {1: 1000, 2: 300, 3: 700, 4: 200})
    assert czas.pamiec_pidow_kb([1, 2, 3, 4], [1], czas.METODA_PS) == 1000 + 700            # nie 2200 (suma drzewa)


def test_wybor_metody_pamieci(monkeypatch):
    monkeypatch.setattr(czas.sys, "platform", "darwin")
    monkeypatch.setattr(czas.shutil, "which", lambda n: "/usr/bin/footprint")
    monkeypatch.setattr(czas, "footprint_pidow_kb", lambda pidy: {pidy[0]: 4096})
    assert czas.wybierz_metode_pamieci(7) == czas.METODA_FOOTPRINT
    monkeypatch.setattr(czas, "footprint_pidow_kb", lambda pidy: {})                         # footprint odmawia (uprawnienia)
    assert czas.wybierz_metode_pamieci(7) == czas.METODA_PS
    monkeypatch.setattr(czas.sys, "platform", "linux")
    monkeypatch.setattr(czas, "pss_pid_kb", lambda pid: 123)
    assert czas.wybierz_metode_pamieci(7) == czas.METODA_PSS


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="PSS z /proc – Linux")
def test_pss_nie_liczy_stron_wspoldzielonych_wielokrotnie():
    kod = ("import os,time;b=bytearray(b'x'*(80*1024*1024))\n"
           "[os.fork() or (time.sleep(30), os._exit(0)) for _ in range(2)]\ntime.sleep(30)")
    p = subprocess.Popen([sys.executable, "-c", kod])
    try:
        import time
        time.sleep(1.5)
        pidy = czas.drzewo_pidow([p.pid])
        assert len(pidy) == 3
        assert czas.wybierz_metode_pamieci() == czas.METODA_PSS
        pss = czas.pamiec_pidow_kb(pidy, [p.pid], czas.METODA_PSS)
        rss = czas.rss_pidow_kb(pidy)
        assert 70 * 1024 < pss < 0.6 * rss                                                  # ~80 MB raz, nie 3 × 80 MB
    finally:
        p.kill()


def argv_cli(sr, *dodatkowe, uczestnik="atrapa-czas"):
    return ["--uczestnik", uczestnik, "--poziom", "tekst", "--korpus", str(sr["korpus"]), "--cel", str(sr["cel"]),
            "--uczestnicy", str(sr["uczestnicy"]), *dodatkowe]


@pytest.fixture
def zasilacz(monkeypatch):
    monkeypatch.setattr(czas, "srodowisko", lambda: {"host": "t", "na_zasilaczu": True, "tryb_niskiego_zuzycia": 0})


def test_limit_mierzy_tylko_pierwsze_n_i_oznacza_probe_niepelna(sr, zasilacz, capsys):
    pelna = czas.losuj_probe(sr["manifest"])
    assert czas.main(argv_cli(sr, "--rozgrzewka", "0", "--powtorzenia", "1", "--limit", "5")) == 0
    assert "ok 5" in capsys.readouterr().out
    assert set(czasy(sr)) == {w["id"] for w in pelna[:5]}
    srod = json.loads((sr["cel"] / "srodowisko.json").read_text())
    assert srod["proba_niepelna"] is True and srod["limit"] == 5
    assert len(json.loads((sr["cel"] / "proba.json").read_text())["id"]) == 60               # proba.json zawsze pełna


def test_zloz_odmawia_po_przebiegu_z_limitem(sr, zasilacz, capsys):
    czas.main(argv_cli(sr, "--rozgrzewka", "0", "--powtorzenia", "1", "--limit", "5"))
    capsys.readouterr()
    (sr["cel"] / "czasy.jsonl").unlink()
    assert czas.main(argv_cli(sr, "--limit", "5", "--powtorzenia", "1", "--zloz")) == 3
    assert "przebieg próbny" in capsys.readouterr().err and not (sr["cel"] / "czasy.jsonl").exists()
    assert czas.main(argv_cli(sr, "--limit", "5", "--powtorzenia", "1", "--zloz", "--dopusc-niepelne")) == 0
    assert (sr["cel"] / "czasy.jsonl").exists()


def test_limit_i_pelny_przebieg_nie_dziela_katalogu(sr, zasilacz):
    czas.main(argv_cli(sr, "--rozgrzewka", "0", "--powtorzenia", "1", "--limit", "3"))
    with pytest.raises(SystemExit):
        czas.main(argv_cli(sr, "--rozgrzewka", "0", "--powtorzenia", "1"))


def test_pelny_przebieg_nie_jest_proba_niepelna(sr, zasilacz):
    czas.main(argv_cli(sr, "--rozgrzewka", "0", "--powtorzenia", "1"))
    assert json.loads((sr["cel"] / "srodowisko.json").read_text())["proba_niepelna"] is False
    assert czas.main(argv_cli(sr, "--powtorzenia", "1", "--zloz")) == 0


def test_podsumuj_zgodne_z_agregacja(sr, zasilacz, capsys):
    czas.main(argv_cli(sr, "--rozgrzewka", "0", "--powtorzenia", "3", "--limit", "12"))
    capsys.readouterr()
    sciezka = sr["cel"] / "czasy.jsonl"
    oczekiwane, _ = agregacja.wynik_czasu(agregacja.wczytaj_czasy(sciezka, {})[("atrapa-czas", "tekst")])
    with open(sr["cel"] / "rss.jsonl", "a") as f:                      # próbnik (okres 1 s) nie musi zdążyć przy tak krótkim przebiegu
        f.write(json.dumps({"uczestnik": "atrapa-czas", "poziom": "tekst", "szczyt_pamieci_mb": 123.4, "metoda_pamieci": "pss"}) + "\n")
    wiersze = czas.podsumuj(sr["cel"])
    assert len(wiersze) == 1 and wiersze[0]["mediana_s_na_strone"] == oczekiwane and wiersze[0]["dokumenty"] == 12
    # niezależny wzór: mediana po dokumentach z (mediana 3 przejść) / max(1, znaki/1800)
    reczne = []
    for linia in sciezka.read_text().splitlines():
        d = json.loads(linia)
        reczne.append(statistics.median(d["pomiary_s"]) / max(1.0, d["znaki"] / agregacja.ZNAKI_STRONY))
    assert wiersze[0]["mediana_s_na_strone"] == pytest.approx(statistics.median(reczne))
    assert wiersze[0]["awarie"] == 0 and wiersze[0]["start_s"] > 0 and wiersze[0]["szczyt_pamieci_mb"] == 123.4 and wiersze[0]["metoda_pamieci"] == "pss"
    assert czas.main(["--podsumuj", str(sr["cel"])]) == 0
    wyj = capsys.readouterr()
    assert "| atrapa-czas | tekst | 12 |" in wyj.out and "przebieg próbny" in wyj.err


def test_podsumuj_liczy_awarie_jako_nieskonczonosc(sr, zasilacz, monkeypatch):
    monkeypatch.setenv("CZAS_ODMOWA", ",".join(w["id"] for w in czas.losuj_probe(sr["manifest"])[:7]))
    czas.main(argv_cli(sr, "--rozgrzewka", "0", "--powtorzenia", "1", "--limit", "10"))
    w = czas.podsumuj(sr["cel"])[0]
    assert w["awarie"] == 7 and math.isinf(w["mediana_s_na_strone"]) and w["wynik"] == 0.0
    assert "∞" in czas.tabela_podsumowania([w])


def test_podsumuj_pusty_katalog(tmp_path, capsys):
    assert czas.main(["--podsumuj", str(tmp_path)]) == 2
