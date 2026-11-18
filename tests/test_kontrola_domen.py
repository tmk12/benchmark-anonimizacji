"""Testy `narzedzia/kontrola_domen.py`: klasyfikacja domeny, odsetek wycieku i przedział na znanych danych, sygnał przewagi
(różnica z przedziałem vs mediana pozostałych), wariant rankingu bez wartości `example.*` = agregacja z odfiltrowanymi wartościami."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from pbench import agregacja as ag

pytestmark = pytest.mark.filterwarnings("ignore")

_spec = importlib.util.spec_from_file_location("kontrola_domen", Path(__file__).parent.parent / "narzedzia" / "kontrola_domen.py")
kd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kd)

SPLIT = "test"
ODCISK = {"kod": "a" * 64, "reguly": "b" * 64, "commit": "c0ffee"}
TEKST = "Kontakt: ala@example.org lub ola@kancelaria.test oraz https://example.com/a i www.firma.test/x. Jan Kowalski."


def _gold(tekst: str) -> list[dict]:
    wartosci = [("mail.example#1", "EMAIL", "ala@example.org"), ("mail.test#1", "EMAIL", "ola@kancelaria.test"),
                ("url.example#1", "URL", "https://example.com/a"), ("url.test#1", "URL", "www.firma.test/x"),
                ("mail.inna#1", "EMAIL", "x@firma.pl"), ("osoba#1", "OSOBA", "Jan Kowalski")]
    return [{"wartosc_id": i, "kategoria": k, "miejsce": "tresc", "tekst": t,
             "start": tekst.find(t), "end": tekst.find(t) + len(t)} for i, k, t in wartosci if t in tekst or k == "EMAIL" and i == "mail.inna#1"]


def _korpus(katalog: Path, n: int) -> list[dict]:
    katalog.mkdir(parents=True, exist_ok=True)
    wpisy = []
    for k in range(n):
        tekst = TEKST + " Poza tym x@firma.pl."
        gold = _gold(tekst)
        for g in gold:                       # wartość „inna” leży na końcu tekstu
            if g["wartosc_id"] == "mail.inna#1":
                g["start"] = tekst.rfind("x@firma.pl")
                g["end"] = g["start"] + len("x@firma.pl")
        w = {"id": f"d{k}", "jezyk": "pl", "typ": "pozew", "format": "docx", "split": SPLIT, "plik": f"d{k}.docx",
             "plik_txt": f"d{k}.txt", "gold_tekst": gold, "gold_plik": [], "gold_obrazy": []}
        (katalog / w["plik_txt"]).write_text(tekst, encoding="utf-8")
        wpisy.append(w)
    (katalog / "manifest.jsonl").write_text("".join(json.dumps(w, ensure_ascii=False) + "\n" for w in wpisy), encoding="utf-8")
    return wpisy


def _rek(i: str, wycieki=()) -> dict:
    return {"id": i, "jezyk": "pl", "typ": "pozew", "format": "docx", "nieobslugiwany": False, "brak_wyniku": False, "blad": None,
            "wycieki": [[w, "X", "tresc", "pelny"] for w in wycieki], "wartosci_ocenione": 1, "czas_s": 1.0,
            "w_zakresie_oficjalnym": True, "fp_znaki": 0, "fp_spany": 0, "pokrycie_znakowe": 1.0, "char_f2": 1.0,
            "odcisk_sedziego": ODCISK}


def _oceny(wyniki: Path, u: str, rekordy: list[dict]) -> None:
    p = wyniki / "oceny" / u / SPLIT / "tekst.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r) + "\n" for r in rekordy), encoding="utf-8")


def _uczestnik(uczestnicy: Path, u: str, aneks: bool = False) -> None:
    (uczestnicy / u).mkdir(parents=True, exist_ok=True)
    (uczestnicy / u / "uczestnik.toml").write_text('poziomy = ["tekst"]\njezyki = ["pl"]\nformaty = ["docx"]\n' + ("aneks = true\n" if aneks else ""),
                                                   encoding="utf-8")


# ----------------------------------------------------------------------------- klasyfikacja domeny
@pytest.mark.parametrize("tekst,kategoria,oczekiwana", [
    ("a@example.org", "EMAIL", "example"), ("a@example.net", "EMAIL", "example"), ("a@Mail.Example.com", "EMAIL", "example"),
    ("x@kancelaria.test", "EMAIL", "test"), ("x@firma.pl", "EMAIL", "inna"), ("bez-malpy", "EMAIL", "inna"),
    ("https://example.com/a", "URL", "example"), ("http://user@www.example.org:8080/x?y=1", "URL", "example"),
    ("https://extranet.textilfranken.test", "URL", "test"), ("www.firma.test/x", "URL", "test"),
    ("https://firma.pl/example.com", "URL", "inna"), ("https://example.pl/a", "URL", "inna"),
])
def test_klasyfikacja_domeny(tekst, kategoria, oczekiwana):
    assert kd.klasa_domeny(tekst, kategoria) == oczekiwana


def test_klasy_wartosci_tylko_email_i_url_z_gold_tekstu_i_pliku():
    wpis = {"gold_tekst": [{"wartosc_id": "a#1", "kategoria": "EMAIL", "tekst": "a@example.org"},
                           {"wartosc_id": "o#1", "kategoria": "OSOBA", "tekst": "Jan"}],
            "gold_plik": [{"id": "u#1", "kategoria": "URL", "tekst": "https://x.test"}],
            "gold_obrazy": [{"id": "i", "ramki": [], "wartosci": [{"id": "b#1", "kategoria": "EMAIL", "tekst": "b@firma.pl"}]}]}
    assert kd.klasy_wartosci(wpis) == {"a#1": ("EMAIL", "example"), "u#1": ("URL", "test"), "b#1": ("EMAIL", "inna")}


# ----------------------------------------------------------------------------- odsetek wycieku, przedział, sygnał
def _wyniki(tmp_path: Path, n: int = 40) -> tuple[list[dict], dict, dict, dict]:
    """40 dokumentów; `maskuje-example` nie ujawnia example.*, ale ujawnia .test w co drugim dokumencie (sygnał), reszta – bez różnic."""
    wpisy = _korpus(tmp_path / "korpus", n)
    wyniki, uczestnicy = tmp_path / "wyniki", tmp_path / "uczestnicy"
    profile = {"przewaga": lambda k: ["mail.test#1", "url.test#1"] if k % 2 == 0 else [],
               "rowny-a": lambda k: ["mail.example#1", "mail.test#1"] if k % 4 == 0 else [],
               "rowny-b": lambda k: ["url.example#1", "url.test#1"] if k % 4 == 1 else [],
               "rowny-c": lambda k: [],
               "wariant": lambda k: ["mail.test#1", "url.test#1"] if k % 2 == 0 else []}
    for u, f in profile.items():
        _uczestnik(uczestnicy, u, aneks=(u == "wariant"))
        _oceny(wyniki, u, [_rek(f"d{k}", f(k)) for k in range(n)])
    rekordy = {("tekst", u): ag._jsonl(wyniki / "oceny" / u / SPLIT / "tekst.jsonl") for u in profile}
    aneksy = {("tekst", u): u == "wariant" for u in profile}
    klasy = {w["id"]: kd.klasy_wartosci(w) for w in wpisy}
    return wpisy, rekordy, aneksy, klasy


def test_odsetek_wycieku_wg_domeny_i_przedzial(tmp_path):
    wpisy, rekordy, aneksy, klasy = _wyniki(tmp_path)
    W = ag.macierz_losowan(np.random.default_rng(ag.ZIARNO), len(wpisy), 300)
    wiersze = kd.analiza(wpisy, rekordy, aneksy, {}, ag.wczytaj_wagi(), klasy, W)
    r = next(x for x in wiersze if x["uczestnik"] == "przewaga" and x["kategoria"] == "EMAIL")
    assert (r["example_n"], r["example_wyciek_n"], r["example_odsetek"]) == (40, 0, 0.0)
    assert (r["test_n"], r["test_wyciek_n"], r["test_odsetek"]) == (40, 20, 0.5)
    assert r["inna_n"] == 40                                          # „inna” zliczona, poza odsetkami
    assert r["roznica"] == pytest.approx(0.5)
    assert r["test_ci_dol"] < 0.5 < r["test_ci_gora"] and 0.3 < r["test_ci_dol"] and r["test_ci_gora"] < 0.7
    assert r["example_ci_dol"] == r["example_ci_gora"] == 0.0         # zero wycieków w każdym losowaniu


def test_sygnal_przewagi_na_znanych_danych(tmp_path):
    wpisy, rekordy, aneksy, klasy = _wyniki(tmp_path)
    W = ag.macierz_losowan(np.random.default_rng(ag.ZIARNO), len(wpisy), 300)
    wiersze = kd.analiza(wpisy, rekordy, aneksy, {}, ag.wczytaj_wagi(), klasy, W)
    po = {(x["uczestnik"], x["kategoria"]): x for x in wiersze}
    assert po[("przewaga", "EMAIL")]["sygnal"] == "tak" and po[("przewaga", "EMAIL")]["kierunek"] == "większa"
    assert po[("rowny-c", "EMAIL")]["sygnal"] == "nie"
    assert po[("rowny-a", "EMAIL")]["sygnal"] == "nie"                # różnica 0 (example i test wyciekają razem)
    # odniesienie: bez wariantów aneksu i bez samego uczestnika (3 pozostałych), wariant aneksu jest oceniany, ale nie wchodzi do mediany
    assert po[("przewaga", "EMAIL")]["pozostalych"] == 3
    assert po[("wariant", "EMAIL")]["pozostalych"] == 4 and po[("wariant", "EMAIL")]["sygnal"] == "tak"


def test_kierunek_mniejsza_i_za_malo_pozostalych(tmp_path):
    wpisy, rekordy, aneksy, klasy = _wyniki(tmp_path)
    W = ag.macierz_losowan(np.random.default_rng(ag.ZIARNO), len(wpisy), 300)
    odwrocony = {d: {**r, "wycieki": [["mail.example#1", "X", "tresc", "pelny"]] if int(d[1:]) % 2 == 0 else []} for d, r in rekordy[("tekst", "rowny-c")].items()}
    rekordy[("tekst", "rowny-c")] = odwrocony
    wiersze = kd.analiza(wpisy, rekordy, aneksy, {}, ag.wczytaj_wagi(), klasy, W)
    r = next(x for x in wiersze if x["uczestnik"] == "rowny-c" and x["kategoria"] == "EMAIL")
    assert r["roznica"] == pytest.approx(-0.5) and r["kierunek"] == "mniejsza" and r["sygnal"] == "nie"
    tylko_dwoch = {k: v for k, v in rekordy.items() if k[1] in ("przewaga", "rowny-a")}
    wiersze = kd.analiza(wpisy, tylko_dwoch, aneksy, {}, ag.wczytaj_wagi(), klasy, W)
    assert all(x["sygnal"] is None and x["kierunek"] is None for x in wiersze)    # 1 pozostały < MIN_POZOSTALYCH


def test_dokument_fail_closed_ma_wszystkie_wartosci_wyciekle(tmp_path):
    wpisy, rekordy, aneksy, klasy = _wyniki(tmp_path, 8)
    rekordy[("tekst", "rowny-c")] = {d: ({**r, "brak_wyniku": True, "blad": "RuntimeError"} if d == "d0" else r)
                                     for d, r in rekordy[("tekst", "rowny-c")].items()}
    W = ag.macierz_losowan(np.random.default_rng(ag.ZIARNO), len(wpisy), 50)
    r = next(x for x in kd.analiza(wpisy, rekordy, aneksy, {}, ag.wczytaj_wagi(), klasy, W)
             if x["uczestnik"] == "rowny-c" and x["kategoria"] == "URL")
    assert r["example_wyciek_n"] == 1 and r["test_wyciek_n"] == 1


# ----------------------------------------------------------------------------- ranking bez example.*
def _agreguj(tmp_path: Path) -> list[dict]:
    return ag.agreguj(split=SPLIT, wyniki=tmp_path / "wyniki", korpus=tmp_path / "korpus", uczestnicy=tmp_path / "uczestnicy", powtorzenia=100)["glowne"]


def test_ranking_bez_example_to_agregacja_z_odfiltrowanymi_wartosciami(tmp_path):
    wpisy, _, _, klasy = _wyniki(tmp_path)
    pelne = _agreguj(tmp_path)
    with kd.bez_example(klasy):
        bez = _agreguj(tmp_path)
    # wzorzec: ręcznie odfiltrowany korpus i oceny w drugim katalogu, zwykła agregacja
    wzor = tmp_path / "wzor"
    nowe = []
    for w in wpisy:
        nowe.append({**w, "gold_tekst": [g for g in w["gold_tekst"] if klasy[w["id"]].get(g["wartosc_id"], ("", ""))[1] != "example"]})
    (wzor / "korpus").mkdir(parents=True)
    (wzor / "korpus" / "manifest.jsonl").write_text("".join(json.dumps(w) + "\n" for w in nowe), encoding="utf-8")
    for w in wpisy:
        (wzor / "korpus" / w["plik_txt"]).write_text((tmp_path / "korpus" / w["plik_txt"]).read_text(encoding="utf-8"), encoding="utf-8")
    for u in ("przewaga", "rowny-a", "rowny-b", "rowny-c", "wariant"):
        rek = ag._jsonl(tmp_path / "wyniki" / "oceny" / u / SPLIT / "tekst.jsonl")
        _oceny(wzor / "wyniki", u, [{**r, "wycieki": [x for x in r["wycieki"] if "example" not in x[0]]} for r in rek.values()])
    (wzor / "uczestnicy").mkdir()
    for u in ("przewaga", "rowny-a", "rowny-b", "rowny-c", "wariant"):
        _uczestnik(wzor / "uczestnicy", u, aneks=(u == "wariant"))
    oczekiwane = ag.agreguj(split=SPLIT, wyniki=wzor / "wyniki", korpus=wzor / "korpus", uczestnicy=wzor / "uczestnicy", powtorzenia=100)["glowne"]
    po = lambda g: {(r["ranking"], r["uczestnik"]): r for r in g}
    for k, r in po(bez).items():
        e = po(oczekiwane)[k]
        assert r["T1"] == pytest.approx(e["T1"]) and r["T2"] == pytest.approx(e["T2"]) and r["suma"] == pytest.approx(e["suma"])
        assert r["T5"] == pytest.approx(e["T5"]) or e["T5"] is None
    # filtr coś zmienia (rowny-a miał wycieki example), a przywrócone funkcje agregacji działają jak przed filtrem
    assert po(bez)[("tekst", "rowny-a")]["T2"] > po(pelne)[("tekst", "rowny-a")]["T2"]
    assert _agreguj(tmp_path) == pelne


def test_ranking_bez_example_dla_korpusu_bez_wartosci_example_jest_identyczny(tmp_path):
    wpisy = _korpus(tmp_path / "korpus", 6)
    nowe = []
    for w in wpisy:
        nowe.append({**w, "gold_tekst": [g for g in w["gold_tekst"] if "example" not in g["wartosc_id"]]})
    (tmp_path / "korpus" / "manifest.jsonl").write_text("".join(json.dumps(w) + "\n" for w in nowe), encoding="utf-8")
    for u, wyc in (("a", ["mail.test#1"]), ("b", [])):
        _uczestnik(tmp_path / "uczestnicy", u)
        _oceny(tmp_path / "wyniki", u, [_rek(f"d{k}", wyc if k % 2 else []) for k in range(6)])
    klasy = {w["id"]: kd.klasy_wartosci(w) for w in nowe}
    pelne = _agreguj(tmp_path)
    with kd.bez_example(klasy):
        bez = _agreguj(tmp_path)
    assert bez == pelne


def test_wiersze_rankingu_i_meta_bez_sciezek(tmp_path):
    wpisy, _, _, klasy = _wyniki(tmp_path, 8)
    pelne = _agreguj(tmp_path)
    with kd.bez_example(klasy):
        bez = _agreguj(tmp_path)
    wiersze = kd.wiersze_rankingu(bez, pelne)
    assert {w["uczestnik"] for w in wiersze} == {r["uczestnik"] for r in pelne}
    assert all(w["suma_glowna"] is not None and "miejsce_glowne" in w for w in wiersze)
    ag.zapisz({"glowne": pelne}, tmp_path / "zbiorcze")
    assert kd.zgodnosc(pelne, tmp_path / "zbiorcze" / "glowne.csv") == "tak"
    assert kd.zgodnosc(bez, None) == "nie sprawdzono"
