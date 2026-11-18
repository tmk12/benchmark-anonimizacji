"""Testy kontroli kontaminacji na sztucznym katalogu danych treningowych (te same ścieżki względne, kilka wierszy)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from pbench import kontaminacja, korpus
from pbench.kontaminacja import okna_z_cyfra, osmiogramy

LINIA = {
    "model": "m", "paczka": "p", "wagi": "w", "zupa_plik": "brak/soup.json",
    "baza": {"przebieg": "b", "krok": 1, "prep_from": "x", "mieszanka_train": "mix-train", "config": "runs/b/config.json"},
    "skladniki": [{"przebieg": "s", "krok": 2, "waga": 1.0, "prep_from": "y", "mieszanka_train": "mix2-train",
                   "configi": "runs/s/from-*/config.json"}],
    "pliki_referencyjne": [
        {"id": "mix-train", "sciezka": "d/mix/train.jsonl"},
        {"id": "mix2-train", "sciezka": "d/mix2/train.jsonl"},
        {"id": "dev", "sciezka": "d/dev/*.jsonl"},
    ],
}


def _wiersz(t: str, dev: bool = False) -> str:
    return json.dumps({"row": {"input": t, "output": {}}} if dev else {"input": t, "output": {}}, ensure_ascii=False)


def _zrodlo(katalog: Path, teksty: list[str], rows_config: int | None = None, pomin: tuple[str, ...] = ()) -> Path:
    pliki = {"d/mix/train.jsonl": False, "d/mix2/train.jsonl": False, "d/dev/a.jsonl": True, "d/dev/b.jsonl": True}
    for rel, dev in pliki.items():
        if rel in pomin:
            continue
        sciezka = katalog / rel
        sciezka.parent.mkdir(parents=True, exist_ok=True)
        sciezka.write_text("\n".join(_wiersz(t, dev) for t in teksty) + "\n", encoding="utf-8")
    if rows_config is not None:
        for rel in ("runs/b/config.json", "runs/s/from-1/config.json"):
            (katalog / rel).parent.mkdir(parents=True, exist_ok=True)
            (katalog / rel).write_text(json.dumps({"rows": rows_config}), encoding="utf-8")
    return katalog


def test_osmiogramy_normalizacja_i_przesuwanie():
    a = osmiogramy("Ala, ma kota; a KOT ma Alę — i psa też.")
    b = osmiogramy("ala ma kota a kot ma alę i psa też")
    assert np.array_equal(a, b) and len(a) == 3
    assert len(osmiogramy("za krótki tekst")) == 0
    assert len(set(osmiogramy("a b c d e f g h i").tolist())) == 2


def test_zbior_referencyjny_kroi_pliki_bez_utraty_wierszy(tmp_path, monkeypatch):
    monkeypatch.setattr(kontaminacja, "ROZMIAR_KAWALKA", 300)   # wiele zakresów na plik
    teksty = [f"w{i} " + " ".join(f"s{i}x{j}" for j in range(30)) for i in range(40)]
    katalog = _zrodlo(tmp_path / "lt", teksty)
    zrodla, stan = kontaminacja.zbior_referencyjny(katalog, LINIA, procesy=2)
    assert [o["wierszy"] for o, _ in zrodla] == [40] * 4          # train, train, dev a, dev b (glob)
    assert [o["id"] for o, _ in zrodla] == ["mix-train", "mix2-train", "dev", "dev"]
    assert stan == {"kompletny": True, "braki": []}
    oczekiwane = np.unique(np.concatenate([osmiogramy(t) for t in teksty]))
    assert np.array_equal(kontaminacja.polacz(zrodla), oczekiwane)
    assert all(o["osmiogramow_unikalnych"] == len(oczekiwane) and not o["z_pliku_npy"] for o, _ in zrodla)


def test_brak_pliku_oznacza_niekompletny_a_skroty_zewnetrzne_go_uzupelniaja(tmp_path):
    katalog = _zrodlo(tmp_path / "lt", ["a b c d e f g h i j"], pomin=("d/mix2/train.jsonl",))
    zrodla, stan = kontaminacja.zbior_referencyjny(katalog, LINIA, procesy=1)
    assert stan == {"kompletny": False, "braki": ["d/mix2/train.jsonl"]}
    npy = tmp_path / "mix2-train.npy"
    np.save(npy, osmiogramy("zupelnie inny tekst ktory ma wiecej niz osiem slow tutaj"))
    zrodla, stan = kontaminacja.zbior_referencyjny(katalog, LINIA, procesy=1, skroty_zewnetrzne=[str(npy)])
    assert stan["kompletny"] is True
    zew = [o for o, _ in zrodla if o["z_pliku_npy"]]
    assert len(zew) == 1 and zew[0]["id"] == "mix2-train" and zew[0]["osmiogramow_unikalnych"] == 3
    # zapis ID=PLIK
    inny = tmp_path / "x.npy"
    np.save(inny, osmiogramy("zupelnie inny tekst ktory ma wiecej niz osiem slow tutaj"))
    _, stan = kontaminacja.zbior_referencyjny(katalog, LINIA, procesy=1, skroty_zewnetrzne=[f"mix2-train={inny}"])
    assert stan["kompletny"]


def test_tylko_skroty_zapisuje_unikalne_skroty_bez_tresci(tmp_path):
    t1, t2 = "a b c d e f g h i j", "k l m n o p q r s t"
    (tmp_path / "x.jsonl").write_text(_wiersz(t1) + "\n" + _wiersz(t1) + "\n", encoding="utf-8")
    (tmp_path / "y.jsonl").write_text(_wiersz(t2, dev=True) + "\n", encoding="utf-8")
    wyj = tmp_path / "out" / "z.npy"
    assert kontaminacja.main(["--tylko-skroty", "--wejscie", str(tmp_path / "x.jsonl"), str(tmp_path / "y.jsonl"),
                              "--wyjscie", str(wyj), "--procesy", "1"]) == 0
    h = np.load(wyj)
    assert h.dtype == np.uint64 and np.array_equal(h, np.unique(np.concatenate([osmiogramy(t1), osmiogramy(t2)])))
    assert b"a b c" not in wyj.read_bytes()


def test_modul_samodzielny_importuje_tylko_numpy_i_stdlib():
    kod = ("import sys, importlib.util as u\n"
           "przed = set(sys.modules)\n"
           f"s = u.spec_from_file_location('kont', {str(Path(kontaminacja.__file__))!r}); m = u.module_from_spec(s)\n"
           "sys.modules['kont'] = m; s.loader.exec_module(m)\n"
           "nowe = {n.split('.')[0] for n in set(sys.modules) - przed} - {'kont'}\n"
           "obce = sorted(n for n in nowe if n not in sys.stdlib_module_names and n != 'numpy' and not n.startswith('_'))\n"
           "print(obce)\n")
    wynik = subprocess.run([sys.executable, "-c", kod], capture_output=True, text=True, check=True)
    assert wynik.stdout.strip() == "[]"


def test_sprawdz_linie_zgodnosc_configow(tmp_path):
    katalog = _zrodlo(tmp_path / "lt", ["a b c d e f g h i j", "k l m n o p q r s t"], rows_config=2)
    zrodla, _ = kontaminacja.zbior_referencyjny(katalog, LINIA, procesy=1)
    info = kontaminacja.sprawdz_linie(katalog, LINIA, zrodla, modele=tmp_path / "brak")
    assert [s["zgodne"] for s in info["skladniki"]] == [True, True] and info["zupa"]["zgodne"] is None
    _zrodlo(tmp_path / "lt", [], rows_config=7)
    info = kontaminacja.sprawdz_linie(katalog, LINIA, zrodla, modele=tmp_path / "brak")
    assert [s["zgodne"] for s in info["skladniki"]] == [False, False]


def test_zupa_zgodna_z_plikiem_linii(tmp_path):
    zupa = tmp_path / "m" / "brak"
    zupa.mkdir(parents=True)
    (zupa / "soup.json").write_text(json.dumps({"sources": [{"path": "/x/runs/s/from-1/checkpoints/best", "weight": 1.0}]}))
    info = kontaminacja.sprawdz_linie(tmp_path, LINIA, [], modele=tmp_path / "m")
    assert info["zupa"]["zgodne"] is True and info["zupa"]["skladniki"] == ["s"]


def test_raport_liczy_wspolne_osmiogramy(tmp_path):
    generuj_cel = tmp_path / "k"
    korpus.generuj(generuj_cel, korpus.ZIARNO, procesy=1, limit=4, jezyki=("pl",), formaty=("docx",), postep=False)
    # trening = teksty korpusu → kontaminacja 100%
    teksty = [(generuj_cel / w["plik_txt"]).read_text(encoding="utf-8")
              for w in map(json.loads, (generuj_cel / "manifest.jsonl").read_text(encoding="utf-8").splitlines())]
    katalog = _zrodlo(tmp_path / "lt", teksty)
    zrodla, stan = kontaminacja.zbior_referencyjny(katalog, LINIA, procesy=1)
    r = kontaminacja.raport(generuj_cel, kontaminacja.polacz(zrodla), kontaminacja.opis_zbioru(zrodla, stan))
    assert r["korpus"]["ogolem"]["odsetek"] == 1.0
    assert r["korpus"]["dokumentow"] == 4
    assert r["szablony"]["ogolem"]["odsetek"] < 1.0
    assert r["frazy_formulowe"]["liczba"] > 0
    assert r["zbior_referencyjny"]["kompletny"] is True and len(r["zbior_referencyjny"]["zrodla"]) == 4
    assert set(r["szablony"]["po_jezykach"]) == {"pl", "en", "es", "de", "fr"}
    # pusty trening → zero
    pusty = _zrodlo(tmp_path / "lt2", ["x y"])
    z0, s0 = kontaminacja.zbior_referencyjny(pusty, LINIA, procesy=1)
    r0 = kontaminacja.raport(generuj_cel, kontaminacja.polacz(z0), kontaminacja.opis_zbioru(z0, s0))
    assert r0["korpus"]["ogolem"]["odsetek"] == 0.0 and r0["szablony"]["ogolem"]["wspolnych"] == 0
    assert "tekst" not in json.dumps(r0).lower().replace("teksty", "")  # tylko liczby i ścieżki


def test_okna_z_cyfra_rownolegle_do_osmiogramow():
    t = "a b c d e f g h i art 233 j k l m n o p q"
    assert len(okna_z_cyfra(t)) == len(osmiogramy(t))
    assert okna_z_cyfra(t).any() and not okna_z_cyfra("a b c d e f g h i").any()
