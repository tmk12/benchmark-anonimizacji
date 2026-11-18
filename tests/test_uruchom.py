"""Testy orkiestratora `pbench-uruchom` z uczestnikiem-atrapą (`uczestnicy/_atrapa`, bez zależności zewnętrznych)."""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from pbench import uruchom

KORZEN = Path(__file__).resolve().parent.parent

TEKSTY = {
    "pl-a-0001": ("pl", "Jan Kowalski mieszka w Warszawie.", [(0, 12, "OSOBA")]),
    "pl-a-0002": ("pl", "PESEL 44051401359 podano w pozwie.", [(6, 17, "PESEL")]),
    "pl-a-0003": ("pl", "Adres: ul. Długa 5, Gdańsk.", [(7, 27, "ADRES")]),
    "pl-a-0004": ("pl", "Anna Nowak i Piotr Zieliński.", [(0, 10, "OSOBA"), (13, 28, "OSOBA")]),
    "en-a-0001": ("en", "John Smith lives in London.", [(0, 10, "OSOBA")]),
    "de-a-0001": ("de", "Tobias Brenner wohnt in Bremen.", [(0, 14, "OSOBA")]),
}


def zrob_srodowisko(tmp: Path, toml: str | None = None) -> dict[str, Path]:
    """Mały korpus syntetyczny (tylko .txt) + kopia atrapy z własną deklaracją."""
    korpus = tmp / "korpus"
    korpus.mkdir()
    wpisy = []
    for id_dok, (jez, tekst, spany) in TEKSTY.items():
        (korpus / f"{id_dok}.txt").write_text(tekst, encoding="utf-8")
        wpisy.append({
            "id": id_dok, "jezyk": jez, "typ": "pozew", "format": "docx", "split": "dev",
            "plik": f"{id_dok}.docx", "plik_txt": f"{id_dok}.txt",
            "gold_tekst": [{"start": s, "end": e, "wartosc_id": f"w{i}#1", "kategoria": k, "miejsce": "tresc",
                            "tekst": tekst[s:e]} for i, (s, e, k) in enumerate(spany)],
            "gold_plik": [], "gold_obrazy": [], "ostrzezenia": []})
    (korpus / "manifest.jsonl").write_text("\n".join(json.dumps(w, ensure_ascii=False) for w in wpisy) + "\n",
                                           encoding="utf-8")
    ucz = tmp / "uczestnicy"
    shutil.copytree(KORZEN / "uczestnicy" / "_atrapa", ucz / "_atrapa",
                    ignore=shutil.ignore_patterns(".venv", "uv.lock", "__pycache__"))
    if toml is not None:
        (ucz / "_atrapa" / "uczestnik.toml").write_text(toml, encoding="utf-8")
    return {"korpus": korpus, "uczestnicy": ucz, "wyniki": tmp / "wyniki", "manifest": korpus / "manifest.jsonl"}


TOML = 'poziomy = ["tekst", "plik"]\njezyki = ["pl", "en", "de"]\nformaty = ["docx"]\nprocesy = {procesy}\ntimeout_s = {timeout}\n'


def uruchom_atrape(sr, monkeypatch, tryb="idealny", *, procesy=1, timeout=60, toml=None, argv=(), env=None,
                   poziom="tekst"):
    if toml is None:
        (sr["uczestnicy"] / "_atrapa" / "uczestnik.toml").write_text(
            TOML.format(procesy=procesy, timeout=timeout), encoding="utf-8")
    else:
        (sr["uczestnicy"] / "_atrapa" / "uczestnik.toml").write_text(toml, encoding="utf-8")
    monkeypatch.setenv("ATRAPA_TRYB", tryb)
    monkeypatch.setenv("ATRAPA_MANIFEST", str(sr["manifest"]))
    for k, v in (env or {}).items():
        monkeypatch.setenv(k, v)
    return uruchom.main(["--uczestnik", "_atrapa", "--split", "dev", "--poziom", poziom,
                         "--korpus", str(sr["korpus"]), "--wyniki", str(sr["wyniki"]),
                         "--uczestnicy", str(sr["uczestnicy"]), *argv])


def surowe(sr, poziom="tekst") -> list[dict]:
    p = sr["wyniki"] / "surowe" / "_atrapa" / "dev" / f"{poziom}.jsonl"
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def wg_id(rekordy) -> dict[str, dict]:
    return {r["id"]: r for r in rekordy}


@pytest.fixture
def sr(tmp_path):
    return zrob_srodowisko(tmp_path)


def test_seria_zapisuje_wszystkie_dokumenty(sr, monkeypatch):
    assert uruchom_atrape(sr, monkeypatch) == 0
    rek = wg_id(surowe(sr))
    assert set(rek) == set(TEKSTY)
    for id_dok, (_, _, spany) in TEKSTY.items():
        assert [w[:3] for w in rek[id_dok]["wykrycia"]] == [[s, e, k] for s, e, k in spany]
        assert rek[id_dok]["czas_s"] >= 0 and rek[id_dok]["proby"] == 1
    wersje = json.loads((sr["wyniki"] / "surowe" / "_atrapa" / "wersje.json").read_text(encoding="utf-8"))
    assert wersje["wersje"]["atrapa"] == "0.1"
    starty = (sr["wyniki"] / "surowe" / "_atrapa" / "dev" / "tekst.starty.jsonl").read_text().splitlines()
    assert len(starty) == 1 and json.loads(starty[0])["start_s"] > 0


def test_timeout_zapisuje_blad_i_kontynuuje(sr, monkeypatch):
    assert uruchom_atrape(sr, monkeypatch, "wolny", timeout=2, env={"ATRAPA_ID": "pl-a-0002"}) == 0
    rek = wg_id(surowe(sr))
    assert set(rek) == set(TEKSTY)
    assert "timeout" in rek["pl-a-0002"]["blad"] and "wykrycia" not in rek["pl-a-0002"]
    assert rek["pl-a-0002"]["czas_s"] >= 2 and rek["pl-a-0002"]["proby"] == 3     # 1 + 2 ponowienia
    for id_dok in TEKSTY.keys() - {"pl-a-0002"}:
        assert "wykrycia" in rek[id_dok] and "blad" not in rek[id_dok]
    # po timeoucie proces startuje od nowa
    assert len((sr["wyniki"] / "surowe" / "_atrapa" / "dev" / "tekst.starty.jsonl").read_text().splitlines()) >= 2


def test_pad_procesu_zapisuje_blad_i_restartuje(sr, monkeypatch):
    uruchom_atrape(sr, monkeypatch, "pada", env={"ATRAPA_ID": "pl-a-0003"})
    rek = wg_id(surowe(sr))
    assert set(rek) == set(TEKSTY)
    assert "blad" in rek["pl-a-0003"] and "zakończył" in rek["pl-a-0003"]["blad"]
    assert all("wykrycia" in rek[i] for i in TEKSTY.keys() - {"pl-a-0003"})


def test_offset_poza_tekstem_to_blad_dokumentu(sr, monkeypatch):
    uruchom_atrape(sr, monkeypatch, "zle_offsety", env={"ATRAPA_ID": "en-a-0001"})
    rek = wg_id(surowe(sr))
    assert "offset" in rek["en-a-0001"]["blad"] and "wykrycia" not in rek["en-a-0001"]
    assert "wykrycia" in rek["pl-a-0001"]


def test_wznowienie_pomija_gotowe(sr, monkeypatch):
    uruchom_atrape(sr, monkeypatch, argv=["--limit", "2"])
    pierwsze = surowe(sr)
    assert len(pierwsze) == 2
    uruchom_atrape(sr, monkeypatch)
    rek = surowe(sr)
    assert len(rek) == len(TEKSTY) and len({r["id"] for r in rek}) == len(TEKSTY)
    assert rek[:2] == pierwsze                      # gotowych nie ruszono (dopisywanie)


def test_wznowienie_toleruje_uciety_ostatni_wiersz(sr, monkeypatch):
    uruchom_atrape(sr, monkeypatch, argv=["--limit", "1"])
    p = sr["wyniki"] / "surowe" / "_atrapa" / "dev" / "tekst.jsonl"
    p.write_text(p.read_text(encoding="utf-8") + '{"id": "pl-a-00', encoding="utf-8")
    uruchom_atrape(sr, monkeypatch)
    assert set(wg_id(surowe_z_pliku(p))) == set(TEKSTY)


def surowe_z_pliku(p):
    wynik = []
    for l in p.read_text(encoding="utf-8").splitlines():
        try:
            wynik.append(json.loads(l))
        except json.JSONDecodeError:
            pass
    return wynik


def test_dokumenty_spoza_deklaracji_to_pominiety(sr, monkeypatch):
    toml = 'poziomy = ["tekst"]\njezyki = ["pl"]\nformaty = ["docx"]\nprocesy = 1\ntimeout_s = 60\n'
    uruchom_atrape(sr, monkeypatch, toml=toml)
    rek = wg_id(surowe(sr))
    assert rek["en-a-0001"] == {"id": "en-a-0001", "pominiety": "jezyk"}
    assert rek["de-a-0001"] == {"id": "de-a-0001", "pominiety": "jezyk"}
    assert "wykrycia" in rek["pl-a-0001"]


def test_wynik_niezalezny_od_liczby_procesow(sr, monkeypatch, tmp_path):
    uruchom_atrape(sr, monkeypatch, procesy=1)
    jeden = {i: {k: v for k, v in r.items() if k != "czas_s"} for i, r in wg_id(surowe(sr)).items()}
    shutil.rmtree(sr["wyniki"])
    uruchom_atrape(sr, monkeypatch, procesy=3)
    trzy = {i: {k: v for k, v in r.items() if k != "czas_s"} for i, r in wg_id(surowe(sr)).items()}
    assert jeden == trzy and len(trzy) == len(TEKSTY)
    starty = (sr["wyniki"] / "surowe" / "_atrapa" / "dev" / "tekst.starty.jsonl").read_text().splitlines()
    assert len(starty) == 3


def test_filtr_jezykow_i_limit(sr, monkeypatch):
    uruchom_atrape(sr, monkeypatch, argv=["--jezyki", "pl", "--limit", "3"])
    assert [r["id"] for r in surowe(sr)] == ["pl-a-0001", "pl-a-0002", "pl-a-0003"]


def test_poziom_spoza_deklaracji_to_blad_uzycia(sr, monkeypatch):
    toml = 'poziomy = ["tekst"]\njezyki = ["pl"]\nformaty = ["docx"]\nprocesy = 1\ntimeout_s = 60\n'
    with pytest.raises(SystemExit) as e:
        uruchom_atrape(sr, monkeypatch, toml=toml, poziom="plik")
    assert e.value.code != 0


def test_wadliwa_deklaracja_to_blad(sr, monkeypatch):
    with pytest.raises(SystemExit):
        uruchom_atrape(sr, monkeypatch, toml='poziomy = ["tekst"]\n')       # brak wymaganych pól


def test_uczestnik_zwraca_blad_w_protokole(sr, monkeypatch):
    # tryb nieznany → atrapa potraktuje jak idealny; blad protokołu sprawdzamy odpowiedzią {"id","blad"}
    assert uruchom._normalizuj_odpowiedz_tekst({"id": "x", "blad": "model padł"}, "abc") == {"blad": "model padł"}
    assert uruchom._normalizuj_odpowiedz_tekst({"id": "x"}, "abc")["blad"]
    assert uruchom._normalizuj_odpowiedz_tekst({"id": "x", "wykrycia": [[0, 0, "A", 1]]}, "abc")["blad"]
    assert uruchom._normalizuj_odpowiedz_tekst({"id": "x", "wykrycia": [[0, 4, "A"]]}, "abc")["blad"]
    assert uruchom._normalizuj_odpowiedz_tekst({"id": "x", "wykrycia": [[0, 3, "A"]]}, "abc") == {
        "wykrycia": [[0, 3, "A", None]]}


def test_poziom_plik_kopiuje_pliki_do_pliki(sr, monkeypatch):
    for id_dok in TEKSTY:
        (sr["korpus"] / f"{id_dok}.docx").write_bytes(b"PK-nie-zip " + id_dok.encode())
    uruchom_atrape(sr, monkeypatch, "plik_kopia", poziom="plik")
    rek = wg_id(surowe(sr, "plik"))
    for id_dok in TEKSTY:
        if TEKSTY[id_dok][0] in ("pl", "en", "de"):
            wyj = sr["wyniki"] / "surowe" / "_atrapa" / "dev" / rek[id_dok]["plik_wyj"]
            assert rek[id_dok]["plik_wyj"] == f"pliki/{id_dok}.docx"
            assert wyj.read_bytes() == (sr["korpus"] / f"{id_dok}.docx").read_bytes()


def test_poziom_plik_brak_pliku_wynikowego_to_blad(sr, monkeypatch):
    # tryb „pada” nie odpowiada, a „pusty” na poziomie plik kopiuje – brak pliku symulujemy brakiem wejścia
    uruchom_atrape(sr, monkeypatch, "plik_kopia", poziom="plik")     # brak plików wejściowych .docx
    rek = surowe(sr, "plik")
    assert rek and all("blad" in r for r in rek)


def test_format_spoza_deklaracji_poziomu_plik_to_pominiety(sr, monkeypatch):
    toml = 'poziomy = ["plik"]\njezyki = ["pl", "en", "de"]\nformaty = ["pdf"]\nprocesy = 1\ntimeout_s = 60\n'
    uruchom_atrape(sr, monkeypatch, "plik_kopia", toml=toml, poziom="plik")
    assert all(r == {"id": r["id"], "pominiety": "format"} for r in surowe(sr, "plik"))


def _zyje(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    # zombie (nieodebrany potomek) też liczy się jako martwy
    try:
        return Path(f"/proc/{pid}/stat").read_text().split()[2] != "Z"
    except OSError:
        return False


def _czekaj_az(warunek, limit=15.0):
    koniec = time.monotonic() + limit
    while time.monotonic() < koniec:
        if warunek():
            return True
        time.sleep(0.1)
    return warunek()


@pytest.mark.skipif(sys.platform == "win32", reason="sprawdzanie pid przez /proc i kill(0)")
def test_timeout_zabija_cale_drzewo_procesow(sr, monkeypatch, tmp_path):
    pid_plik = tmp_path / "dziecko.pid"
    uruchom_atrape(sr, monkeypatch, "wolny", timeout=2, argv=["--bez-ponawiania", "--limit", "1"],
                   env={"ATRAPA_ID": "pl-a-0001", "ATRAPA_PID_PLIK": str(pid_plik)})
    pid = int(pid_plik.read_text())
    assert _czekaj_az(lambda: not _zyje(pid)), "proces potomny uczestnika przeżył timeout"


@pytest.mark.skipif(sys.platform == "win32", reason="SIGTERM/killpg")
def test_sigterm_zamyka_instancje_i_nie_zapisuje_bledow(sr, tmp_path):
    pid_plik = tmp_path / "dziecko.pid"
    (sr["uczestnicy"] / "_atrapa" / "uczestnik.toml").write_text(TOML.format(procesy=1, timeout=600))
    env = {**os.environ, "ATRAPA_TRYB": "wolny", "ATRAPA_ID": "pl-a-0001", "ATRAPA_PID_PLIK": str(pid_plik),
           "ATRAPA_MANIFEST": str(sr["manifest"])}
    p = subprocess.Popen([sys.executable, "-m", "pbench.uruchom", "--uczestnik", "_atrapa", "--split", "dev",
                          "--poziom", "tekst", "--korpus", str(sr["korpus"]), "--wyniki", str(sr["wyniki"]),
                          "--uczestnicy", str(sr["uczestnicy"]), "--limit", "1"], env=env, cwd=KORZEN,
                         stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    assert _czekaj_az(pid_plik.exists, 60)
    pid = int(pid_plik.read_text())
    time.sleep(0.3)
    p.send_signal(signal.SIGTERM)
    p.wait(timeout=30)
    assert _czekaj_az(lambda: not _zyje(pid)), "potomek uczestnika przeżył SIGTERM orkiestratora"
    plik = sr["wyniki"] / "surowe" / "_atrapa" / "dev" / "tekst.jsonl"
    assert not plik.exists() or plik.read_text().strip() == ""


def test_wznowienie_ponawia_bledy_ale_nie_pominiete(sr, monkeypatch):
    toml = TOML.format(procesy=1, timeout=60).replace('["pl", "en", "de"]', '["pl", "en"]')
    uruchom_atrape(sr, monkeypatch, "zle_offsety", toml=toml, argv=["--bez-ponawiania"], env={"ATRAPA_ID": "pl-a-0001"})
    p = sr["wyniki"] / "surowe" / "_atrapa" / "dev" / "tekst.jsonl"
    assert "blad" in wg_id(surowe(sr))["pl-a-0001"] and wg_id(surowe(sr))["pl-a-0001"]["proby"] == 1
    uruchom_atrape(sr, monkeypatch, "idealny", toml=toml)                 # domyślnie ponawia błędy
    rek = surowe(sr)
    ostatni = wg_id(rek)
    assert "wykrycia" in ostatni["pl-a-0001"] and ostatni["pl-a-0001"]["proby"] == 1
    assert [r["id"] for r in rek].count("pl-a-0001") == 2                  # stary błąd zostaje, liczy się ostatni
    assert [r["id"] for r in rek].count("de-a-0001") == 1                  # pominiety nie jest ponawiany
    assert ostatni["de-a-0001"] == {"id": "de-a-0001", "pominiety": "jezyk"}
    assert p.exists()


def test_bez_ponawiania_nie_powtarza_bledow_przy_wznowieniu(sr, monkeypatch):
    uruchom_atrape(sr, monkeypatch, "zle_offsety", argv=["--bez-ponawiania"], env={"ATRAPA_ID": "pl-a-0001"})
    uruchom_atrape(sr, monkeypatch, "idealny", argv=["--bez-ponawiania"])
    rek = surowe(sr)
    assert [r["id"] for r in rek].count("pl-a-0001") == 1 and "blad" in wg_id(rek)["pl-a-0001"]


def test_gotowe_id_liczy_ostatni_wpis_i_ponawia_bledy(tmp_path):
    assert uruchom.MAKS_PONOWIEN == 2
    p = tmp_path / "x.jsonl"
    p.write_text('{"id": "a", "blad": "x"}\n{"id": "a", "wykrycia": []}\n{"id": "b", "blad": "y"}\n{"id": "c", "pominiety": "jezyk"}\n')
    assert uruchom.gotowe_id(p, ponawiaj_bledy=True) == {"a", "c"}
    assert uruchom.gotowe_id(p) == {"a", "b", "c"}


def test_sprawdz_python_ostrzega_o_innej_wersji(sr, capsys):
    env = uruchom.zbuduj_srodowisko(1, False)
    katalog = sr["uczestnicy"] / "_atrapa"
    wersja = uruchom.sprawdz_python(katalog, env)
    assert wersja.startswith("3.12.") and "OSTRZEŻENIE" not in capsys.readouterr().err
    uruchom.sprawdz_python(katalog, env, "3.11")
    assert "OSTRZEŻENIE" in capsys.readouterr().err


def test_jezyki_oficjalne_w_deklaracji_i_wersje_json(sr, monkeypatch):
    toml = ('poziomy = ["tekst"]\njezyki = ["pl", "en", "de"]\njezyki_oficjalne = ["en"]\nformaty = []\n'
            'procesy = 1\ntimeout_s = 60\n')
    uruchom_atrape(sr, monkeypatch, toml=toml)
    wersje = json.loads((sr["wyniki"] / "surowe" / "_atrapa" / "wersje.json").read_text(encoding="utf-8"))
    assert wersje["jezyki_oficjalne"] == ["en"] and wersje["jezyki"] == ["pl", "en", "de"]
    assert wg_id(surowe(sr))["pl-a-0001"].get("wykrycia") is not None        # uruchamiamy na wszystkich zadeklarowanych


def test_jezyki_oficjalne_domyslnie_rowne_jezykom(tmp_path):
    (tmp_path / "uczestnik.toml").write_text('poziomy = ["tekst"]\njezyki = ["pl", "en"]\nformaty = []\n', encoding="utf-8")
    d = uruchom.wczytaj_deklaracje(tmp_path)
    assert d.jezyki_oficjalne == ("pl", "en")


def test_jezyki_oficjalne_nieznany_jezyk_to_blad(tmp_path):
    (tmp_path / "uczestnik.toml").write_text(
        'poziomy = ["tekst"]\njezyki = ["pl"]\njezyki_oficjalne = ["xx"]\nformaty = []\n', encoding="utf-8")
    with pytest.raises(uruchom.BladDeklaracji):
        uruchom.wczytaj_deklaracje(tmp_path)


def test_aneks_domyslnie_false_i_zapisany_w_wersjach(sr, monkeypatch, tmp_path):
    """`aneks` (wariant ablacyjny/krzyżowy – poza rankingami): brak pola = False; wartość trafia do `wersje.json`."""
    (tmp_path / "uczestnik.toml").write_text('poziomy = ["tekst"]\njezyki = ["pl"]\nformaty = []\n', encoding="utf-8")
    assert uruchom.wczytaj_deklaracje(tmp_path).aneks is False
    uruchom_atrape(sr, monkeypatch, toml='poziomy = ["tekst"]\njezyki = ["pl", "en", "de"]\nformaty = []\naneks = true\n')
    wersje = json.loads((sr["wyniki"] / "surowe" / "_atrapa" / "wersje.json").read_text(encoding="utf-8"))
    assert wersje["aneks"] is True


def test_aneks_nie_logiczny_to_blad(tmp_path):
    (tmp_path / "uczestnik.toml").write_text('poziomy = ["tekst"]\njezyki = ["pl"]\nformaty = []\naneks = "tak"\n',
                                             encoding="utf-8")
    with pytest.raises(uruchom.BladDeklaracji):
        uruchom.wczytaj_deklaracje(tmp_path)


def test_r38_plik_wynikowy_z_innym_rozszerzeniem_jest_przyjety(sr, monkeypatch):
    """Wynikiem jest plik faktycznie zapisany przez narzędzie (np. .msg → .txt); w rekordzie `plik_wyj` i `format_wyj`."""
    for id_dok in TEKSTY:
        (sr["korpus"] / f"{id_dok}.docx").write_bytes(b"PK-nie-zip " + id_dok.encode())
    uruchom_atrape(sr, monkeypatch, "inne_rozszerzenie", poziom="plik")
    rek = wg_id(surowe(sr, "plik"))
    for id_dok in TEKSTY:
        if TEKSTY[id_dok][0] in ("pl", "en", "de"):
            assert "blad" not in rek[id_dok], rek[id_dok]
            assert rek[id_dok]["plik_wyj"] == f"pliki/{id_dok}.txt" and rek[id_dok]["format_wyj"] == "txt"
            assert (sr["wyniki"] / "surowe" / "_atrapa" / "dev" / rek[id_dok]["plik_wyj"]).is_file()
