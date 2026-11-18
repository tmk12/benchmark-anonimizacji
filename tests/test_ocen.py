"""Testy `pbench-ocen`: atrapa idealna/pusta na obu poziomach, flagi braku wyniku i nieobsługiwania (fail-closed)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from docx import Document

from pbench import ocen, srodowisko
from test_uruchom import TEKSTY, uruchom_atrape, zrob_srodowisko

pytestmark = pytest.mark.filterwarnings("ignore")

PESEL = "44051401359"


@pytest.fixture(autouse=True)
def _cache_ocr(tmp_path, monkeypatch):
    monkeypatch.setenv("PBENCH_OCR_CACHE", str(tmp_path / "ocr"))


@pytest.fixture
def sr(tmp_path):
    """Korpus z plikami .docx (PESEL w treści) i gold_plik; teksty jak w test_uruchom."""
    sr = zrob_srodowisko(tmp_path)
    wpisy = [json.loads(l) for l in sr["manifest"].read_text(encoding="utf-8").splitlines()]
    for w in wpisy:
        d = Document()
        d.add_paragraph(f"Pozew. PESEL powoda: {PESEL}. Treść bez znaczenia.")
        d.save(sr["korpus"] / w["plik"])
        w["gold_plik"] = [{"id": "powod.pesel#1", "kategoria": "PESEL", "tekst": PESEL, "jezyk": w["jezyk"],
                           "miejsce": "tresc", "waga_klucz": "PESEL"}]
    sr["manifest"].write_text("\n".join(json.dumps(w, ensure_ascii=False) for w in wpisy) + "\n", encoding="utf-8")
    return sr


def oceny(sr, poziom) -> dict[str, dict]:
    p = sr["wyniki"] / "oceny" / "_atrapa" / "dev" / f"{poziom}.jsonl"
    return {o["id"]: o for o in (json.loads(l) for l in p.read_text(encoding="utf-8").splitlines())}


def ocen_atrape(sr, poziom="tekst", procesy=1):
    return ocen.main(["--uczestnik", "_atrapa", "--split", "dev", "--poziom", poziom, "--korpus", str(sr["korpus"]),
                      "--wyniki", str(sr["wyniki"]), "--procesy", str(procesy)])


def test_atrapa_idealna_tekst_zero_wyciekow(sr, monkeypatch):
    uruchom_atrape(sr, monkeypatch, "idealny")
    assert ocen_atrape(sr) == 0
    o = oceny(sr, "tekst")
    assert set(o) == set(TEKSTY)
    for r in o.values():
        assert r["wycieki"] == [] and not r["brak_wyniku"] and not r["nieobslugiwany"]
        assert r["char_f2"] == 1.0 and r["fp_znaki"] == 0 and r["pokrycie_znakowe"] == 1.0
        assert r["odcisk_sedziego"] == srodowisko.odcisk_sedziego("tekst", ocen.REGULY_DOMYSLNE)   # W3
    assert sum(r["wartosci_ocenione"] for r in o.values()) > 0


def test_atrapa_pusta_tekst_wszystko_wycieka(sr, monkeypatch):
    uruchom_atrape(sr, monkeypatch, "pusty")
    ocen_atrape(sr)
    o = oceny(sr, "tekst")
    for r in o.values():
        assert len(r["wycieki"]) == r["wartosci_ocenione"] > 0
        assert r["pokrycie_znakowe"] == 0.0 and not r["brak_wyniku"]


def test_blad_i_pominiety_to_wszystko_wycieka_z_flagami(sr, monkeypatch):
    toml = 'poziomy = ["tekst"]\njezyki = ["pl", "en"]\nformaty = ["docx"]\nprocesy = 1\ntimeout_s = 60\n'
    uruchom_atrape(sr, monkeypatch, "zle_offsety", toml=toml, env={"ATRAPA_ID": "pl-a-0001"})
    ocen_atrape(sr)
    o = oceny(sr, "tekst")
    assert o["pl-a-0001"]["brak_wyniku"] and "offset" in o["pl-a-0001"]["blad"]
    assert len(o["pl-a-0001"]["wycieki"]) == o["pl-a-0001"]["wartosci_ocenione"] > 0
    assert o["de-a-0001"]["nieobslugiwany"] and not o["de-a-0001"]["brak_wyniku"]
    assert len(o["de-a-0001"]["wycieki"]) == o["de-a-0001"]["wartosci_ocenione"] > 0
    assert not o["pl-a-0002"]["brak_wyniku"] and o["pl-a-0002"]["wycieki"] == []


def test_ocena_rowna_dla_jednego_i_wielu_procesow(sr, monkeypatch):
    uruchom_atrape(sr, monkeypatch, "pusty")
    ocen_atrape(sr, procesy=1)
    jeden = oceny(sr, "tekst")
    ocen_atrape(sr, procesy=3)
    assert oceny(sr, "tekst") == jeden


def test_atrapa_idealna_plik_zero_wyciekow_pusta_wszystko(sr, monkeypatch):
    uruchom_atrape(sr, monkeypatch, "idealny", poziom="plik")
    assert ocen_atrape(sr, "plik") == 0
    o = oceny(sr, "plik")
    zakres = [i for i, (j, _, _) in TEKSTY.items() if j in ("pl", "en", "de")]
    assert set(o) == set(zakres)
    for r in o.values():
        assert r["status_pliku"] == "OK" and r["wycieki"] == [] and r["wartosci_ocenione"] == 1
        assert r["integralnosc"]["otwiera_sie"] is True and not r["brak_wyniku"]
        # T17a: linia bazowa (mianownik P2) i nadmiarowe maskowanie tekstu widocznego (P5) w rekordzie
        assert r["bazowe"] == ["powod.pesel#1"]
        assert r["nadmiarowe"]["poza_gold"] > 0 and r["nadmiarowe"]["znaki"] == 0
        # W3: odcisk sędziego i środowiska w każdym rekordzie
        assert r["odcisk_sedziego"] == srodowisko.odcisk_sedziego("plik", ocen.REGULY_DOMYSLNE)
    shutil.rmtree(sr["wyniki"] / "surowe")
    uruchom_atrape(sr, monkeypatch, "plik_kopia", poziom="plik")
    ocen_atrape(sr, "plik")
    for r in oceny(sr, "plik").values():
        assert [w[0] for w in r["wycieki"]] == ["powod.pesel#1"] and r["wycieki"][0][3] == "pelny"


def test_plik_nieczytelny_i_brak_pliku_to_brak_wyniku(sr, monkeypatch):
    uruchom_atrape(sr, monkeypatch, "plik_kopia", poziom="plik")
    surowy = sr["wyniki"] / "surowe" / "_atrapa" / "dev"
    (surowy / "pliki" / "pl-a-0001.docx").write_bytes(b"to nie jest docx")
    rek = [json.loads(l) for l in (surowy / "plik.jsonl").read_text().splitlines()]
    rek.append({"id": "pl-a-0002", "jezyk": "pl", "blad": "timeout 300 s (dokument pl-a-0002)", "czas_s": 300.0})
    rek = [r for r in rek if r["id"] != "pl-a-0002" or "blad" in r]
    (surowy / "plik.jsonl").write_text("\n".join(json.dumps(r) for r in rek) + "\n", encoding="utf-8")
    ocen_atrape(sr, "plik")
    o = oceny(sr, "plik")
    assert o["pl-a-0001"]["brak_wyniku"] and o["pl-a-0001"]["status_pliku"] in ("NIECZYTELNY", "PUSTY")
    assert o["pl-a-0001"]["integralnosc"] is None and len(o["pl-a-0001"]["wycieki"]) == 1
    assert o["pl-a-0001"]["nadmiarowe"] is None and o["pl-a-0001"]["bazowe"] == ["powod.pesel#1"]
    assert o["pl-a-0002"]["brak_wyniku"] and "timeout" in o["pl-a-0002"]["blad"]
    assert len(o["pl-a-0002"]["wycieki"]) == 1


def test_dokumenty_bez_wyniku_surowego_nie_sa_oceniane(sr, monkeypatch, capsys):
    uruchom_atrape(sr, monkeypatch, argv=["--limit", "2"])
    ocen_atrape(sr)
    assert len(oceny(sr, "tekst")) == 2
    assert "niedokończony" in capsys.readouterr().err


def test_flaga_w_zakresie_oficjalnym(sr, monkeypatch):
    toml = ('poziomy = ["tekst"]\njezyki = ["pl", "en", "de"]\njezyki_oficjalne = ["en", "de"]\nformaty = []\n'
            'procesy = 1\ntimeout_s = 60\n')
    uruchom_atrape(sr, monkeypatch, "idealny", toml=toml)
    assert ocen_atrape(sr) == 0
    for r in oceny(sr, "tekst").values():
        assert r["w_zakresie_oficjalnym"] == (r["jezyk"] in ("en", "de"))
    assert any(not r["w_zakresie_oficjalnym"] for r in oceny(sr, "tekst").values())
