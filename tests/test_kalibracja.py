"""Testy kalibracji progu (`pbench.kalibracja`) na syntetycznym dev o znanym optimum."""
from __future__ import annotations

import json
from pathlib import Path

from pbench import kalibracja

KORZEN = Path(__file__).resolve().parent.parent

# dokument: „Jan Kowalski” (0–12) i „Anna Nowak” (28–38) w gold; reszta tekstu to nie-PII
TEKST = "Jan Kowalski mieszka w Gdańsku, Anna Nowak też. Sprawa toczy się od roku."
GOLD = [(0, 12), (29, 39)]
POZA_GOLD = (47, 58)                                  # „toczy się od” – fałszywe trafienie


def korpus(tmp: Path, n: int = 3) -> Path:
    k = tmp / "korpus"
    k.mkdir()
    wpisy = []
    for i in range(n):
        id_dok = f"pl-a-{i:04d}"
        (k / f"{id_dok}.txt").write_text(TEKST, encoding="utf-8")
        wpisy.append({"id": id_dok, "jezyk": "pl", "typ": "pozew", "format": "docx", "split": "dev",
                      "plik": f"{id_dok}.docx", "plik_txt": f"{id_dok}.txt",
                      "gold_tekst": [{"start": s, "end": e, "wartosc_id": f"w{j}#1", "kategoria": "OSOBA",
                                      "miejsce": "tresc", "tekst": TEKST[s:e]} for j, (s, e) in enumerate(GOLD)],
                      "gold_plik": [], "gold_obrazy": [], "ostrzezenia": []})
    (k / "manifest.jsonl").write_text("\n".join(json.dumps(w, ensure_ascii=False) for w in wpisy) + "\n", encoding="utf-8")
    return k


def surowe(tmp: Path, wykrycia: list, n: int = 3, uczestnik: str = "x") -> Path:
    """`wyniki/surowe/x/dev` z tym samym zestawem wykryć dla każdego z `n` dokumentów."""
    d = tmp / "wyniki" / "surowe" / uczestnik / "dev"
    d.mkdir(parents=True)
    (d / "tekst.jsonl").write_text(
        "\n".join(json.dumps({"id": f"pl-a-{i:04d}", "jezyk": "pl", "wykrycia": wykrycia}) for i in range(n)) + "\n",
        encoding="utf-8")
    return d


def test_kalibracja_wybiera_prog_maks_f2(tmp_path):
    # 0,9 – trafienie pewne, 0,6 – trafienie mniej pewne, 0,3 – fałszywe: przy 0,5 zostają oba trafienia i znika fałszywe
    wyk = [[GOLD[0][0], GOLD[0][1], "PER", 0.9], [GOLD[1][0], GOLD[1][1], "PER", 0.6], [*POZA_GOLD, "PER", 0.3]]
    siatka = [0.1, 0.3, 0.5, 0.7, 0.95]
    k = korpus(tmp_path)
    d = surowe(tmp_path, wyk)
    assert kalibracja.kalibruj("x", d, siatka, korpus=k) == 0.5
    f2, n = kalibracja.krzywa(d, siatka, korpus=k)
    assert n == 3 and f2[0.5] > f2[0.7] > f2[0.95] and f2[0.5] > f2[0.3] and f2[0.1] == f2[0.3]


def test_kalibracja_remis_wybiera_wyzszy_prog(tmp_path):
    # oba trafienia mają wynik 0,9 – progi 0,5 i 0,7 dają to samo F2 → wyższy
    wyk = [[GOLD[0][0], GOLD[0][1], "PER", 0.9], [GOLD[1][0], GOLD[1][1], "PER", 0.8], [*POZA_GOLD, "PER", 0.3]]
    k = korpus(tmp_path)
    assert kalibracja.kalibruj("x", surowe(tmp_path, wyk), [0.5, 0.7], korpus=k) == 0.7
    assert kalibracja.wybierz_prog({0.1: 0.5, 0.2: 0.9, 0.3: 0.9, 0.4: 0.2}) == 0.3


def test_uczestnik_bez_wyniku_pewnosci_nie_jest_kalibrowany(tmp_path):
    wyk = [[GOLD[0][0], GOLD[0][1], "PER", 1.0], [*POZA_GOLD, "PER", 1.0]]          # jak stanza/scrubadub: wynik stały
    k = korpus(tmp_path)
    assert kalibracja.kalibruj("x", surowe(tmp_path, wyk), korpus=k) is None
    # brak wykryć też nie niesie wyniku
    assert kalibracja.kalibruj("x", surowe(tmp_path / "pusty", []), korpus=k) is None


def test_cli_zapisuje_prog_json_z_metadanymi(tmp_path):
    wyk = [[GOLD[0][0], GOLD[0][1], "PER", 0.9], [GOLD[1][0], GOLD[1][1], "PER", 0.6], [*POZA_GOLD, "PER", 0.3]]
    k = korpus(tmp_path)
    surowe(tmp_path, wyk)
    ucz = tmp_path / "uczestnicy"
    (ucz / "x").mkdir(parents=True)
    assert kalibracja.main(["--uczestnik", "x", "--wyniki", str(tmp_path / "wyniki"), "--korpus", str(k),
                            "--uczestnicy", str(ucz), "--zapisz", "--procesy", "1"]) == 0
    d = json.loads((ucz / "x" / "prog.json").read_text(encoding="utf-8"))
    assert d["prog"] == 0.6 and d["liczba_dokumentow"] == 3 and d["siatka"] == kalibracja.SIATKA
    assert set(d["f2"]) == {f"{p:.2f}" for p in kalibracja.SIATKA} and "data" in d and "commit_sedziego" in d
    # uczestnik bez wyniku pewności – brak pliku
    surowe(tmp_path, [[0, 12, "PER", 1.0]], uczestnik="y")
    (ucz / "y").mkdir()
    assert kalibracja.main(["--uczestnik", "y", "--wyniki", str(tmp_path / "wyniki"), "--korpus", str(k),
                            "--uczestnicy", str(ucz), "--zapisz"]) == 0
    assert not (ucz / "y" / "prog.json").exists()


def test_siatka_zaczyna_sie_od_001_i_ma_dotychczasowa_reszte():
    assert kalibracja.SIATKA[:5] == [0.01, 0.02, 0.03, 0.04, 0.05] and kalibracja.SIATKA[-1] == 0.95
    assert len(kalibracja.SIATKA) == 23


def test_wczytaj_prog_surowy_001_prog_json_nizej_niz_005_i_domyslny(tmp_path, monkeypatch):
    import sys
    sys.path.insert(0, str(kalibracja.KORZEN / "uczestnicy" / "_wspolne"))
    import protokol_uczestnika as pu
    monkeypatch.delenv("PBENCH_SUROWE", raising=False)
    assert pu.wczytaj_prog(tmp_path, 0.0) == 0.05 and pu.wczytaj_prog(tmp_path, 0.3) == 0.3   # bez zmian
    (tmp_path / "prog.json").write_text('{"prog": 0.02}', encoding="utf-8")
    assert pu.wczytaj_prog(tmp_path, 0.3) == 0.02
    monkeypatch.setenv("PBENCH_SUROWE", "1")
    assert pu.wczytaj_prog(tmp_path, 0.3) == 0.01
