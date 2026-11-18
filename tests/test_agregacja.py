"""Testy `pbench-agreguj`: wzory punktacji (T1–T6, P1–P7) na syntetycznych rekordach ocen, fail-closed (błąd, timeout,
nieobsługiwany, odmowa), mianownik P2, aneks poza rankingiem, bootstrap i remis statystyczny."""
from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from pbench import agregacja as ag
from pbench.przypadki import przypadki_punktowane

pytestmark = pytest.mark.filterwarnings("ignore")

SPLIT = "dev"
#: Odcisk sędziego wspólny dla rekordów fikstur (W3; `pbench.srodowisko.odcisk_sedziego`).
ODCISK = {"kod": "a" * 64, "reguly": "b" * 64, "commit": "c0ffee"}


# ----------------------------------------------------------------------------- fikstury: korpus i rekordy ocen
def _wpis(i: str, jezyk: str = "pl", *, typ: str = "pozew", format: str = "docx", tekst: str = "",
          gold: list[tuple[int, int, str, str, str]] = (), gold_plik: list[dict] = (), gold_obrazy: list[dict] = (),
          przypadki: list[str] | None = None) -> tuple[dict, str]:
    """Wpis manifestu i tekst `.txt`; `gold` – (start, end, wartosc_id, kategoria, miejsce)."""
    w = {"id": i, "jezyk": jezyk, "typ": typ, "format": format, "split": SPLIT, "plik": f"{i}.{format}",
         "plik_txt": f"{i}.txt",
         "gold_tekst": [{"start": s, "end": e, "wartosc_id": wid, "kategoria": k, "miejsce": m, "tekst": tekst[s:e]}
                        for s, e, wid, k, m in gold],
         "gold_plik": list(gold_plik), "gold_obrazy": list(gold_obrazy)}
    if przypadki is not None:
        w["przypadki"] = przypadki
    return w, tekst


def _korpus(katalog: Path, wpisy: list[tuple[dict, str]]) -> Path:
    katalog.mkdir(parents=True, exist_ok=True)
    for w, t in wpisy:
        (katalog / w["plik_txt"]).write_text(t, encoding="utf-8")
    (katalog / "manifest.jsonl").write_text("".join(json.dumps(w, ensure_ascii=False) + "\n" for w, _ in wpisy),
                                            encoding="utf-8")
    return katalog


def _oceny(wyniki: Path, uczestnik: str, poziom: str, rekordy: list[dict]) -> None:
    p = wyniki / "oceny" / uczestnik / SPLIT / f"{poziom}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rekordy), encoding="utf-8")


def _rek(i: str, jezyk: str = "pl", *, wycieki=(), fp: int = 0, brak: bool = False, nieobs: bool = False,
         blad: str | None = None, **inne) -> dict:
    r = {"id": i, "jezyk": jezyk, "typ": "pozew", "format": "docx", "nieobslugiwany": nieobs, "brak_wyniku": brak,
         "blad": blad, "wycieki": [list(w) for w in wycieki], "wartosci_ocenione": 1, "czas_s": 1.0,
         "w_zakresie_oficjalnym": True, "fp_znaki": fp, "fp_spany": 0, "pokrycie_znakowe": 1.0, "char_f2": 1.0,
         "odcisk_sedziego": ODCISK}
    r.update(inne)
    return r


def _surowe(wyniki: Path, uczestnik: str, rekordy: list[dict]) -> None:
    p = wyniki / "surowe" / uczestnik / SPLIT / "tekst.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rekordy), encoding="utf-8")


def _uczestnik(uczestnicy: Path, nazwa: str, *, aneks: bool = False, odmowy: list[str] | None = None) -> None:
    k = uczestnicy / nazwa
    k.mkdir(parents=True, exist_ok=True)
    (k / "uczestnik.toml").write_text(
        'poziomy = ["tekst"]\njezyki = ["pl"]\nformaty = ["docx"]\n' + ("aneks = true\n" if aneks else ""), encoding="utf-8")
    if odmowy is not None:
        (k / "odmowy.json").write_text(json.dumps({"komunikaty": odmowy}, ensure_ascii=False), encoding="utf-8")


TEKST = "Jan Kowalski mieszka w Krakowie. PESEL 44051401359. Umowa najmu lokalu."
GOLD = [(0, 12, "osoba#1", "OSOBA", "tresc"), (23, 31, "miasto#1", "MIEJSCOWOSC", "tresc"),
        (39, 50, "pesel#1", "PESEL", "tresc")]


def _cztery_dokumenty(tmp_path: Path, jezyki=("pl", "pl", "en", "de")) -> Path:
    return _korpus(tmp_path / "korpus", [_wpis(f"d{k}", j, tekst=TEKST, gold=GOLD) for k, j in enumerate(jezyki)])


def _agreguj(tmp_path: Path, **k) -> dict:
    k.setdefault("korpus", tmp_path / "korpus")
    k.setdefault("wyniki", tmp_path / "wyniki")
    k.setdefault("uczestnicy", tmp_path / "uczestnicy")
    k.setdefault("powtorzenia", 200)
    return ag.agreguj(split=SPLIT, **k)


def _wiersz(wynik: dict, uczestnik: str, ranking: str = "tekst") -> dict:
    return next(r for r in wynik["glowne"] if r["uczestnik"] == uczestnik and r["ranking"] == ranking)


def _poza_gold(tekst: str, gold) -> int:
    maska = [False] * len(tekst)
    for s, e, *_ in gold:
        for x in range(s, e):
            maska[x] = True
    return sum(1 for x, c in enumerate(tekst) if not maska[x] and not c.isspace())


# ----------------------------------------------------------------------------- T1, T2, T4, T5
def test_odsetek_dokumentow_z_wyciekiem(tmp_path):
    _cztery_dokumenty(tmp_path)
    _oceny(tmp_path / "wyniki", "u", "tekst", [
        _rek("d0"), _rek("d1", wycieki=[("pesel#1", "PESEL", "tresc", "pelny")]), _rek("d2", "en"), _rek("d3", "de")])
    r = _wiersz(_agreguj(tmp_path), "u")
    assert r["T1"] == pytest.approx(0.75)
    assert r["T1_pkt"] == pytest.approx(350 * 0.75)
    assert r["dokumenty"] == 4 and r["z_wyciekiem"] == 1
    # T2: wagi PESEL 3, OSOBA 2, MIEJSCOWOSC 1 → mianownik 6 na dokument; wyciekł PESEL w jednym
    assert r["T2"] == pytest.approx(1 - 3 / 24)
    # T4: min po językach (pl: 1/2 bez wycieku)
    assert r["T4"] == pytest.approx(0.5)


def test_t4_bez_ukrainskiego_i_t5_z_tekstu(tmp_path):
    _cztery_dokumenty(tmp_path, jezyki=("pl", "en", "es", "uk"))
    _oceny(tmp_path / "wyniki", "u", "tekst", [_rek("d0", fp=5), _rek("d1", "en"), _rek("d2", "es"),
                                              _rek("d3", "uk", wycieki=[("osoba#1", "OSOBA", "tresc", "pelny")])])
    r = _wiersz(_agreguj(tmp_path), "u")
    assert r["T4"] == 1.0                                       # dokument `uk` poza T4
    u = 5 / (4 * _poza_gold(TEKST, GOLD))
    assert r["T5"] == pytest.approx(max(0.0, 1 - u / 0.20))
    assert r["T5_u"] == pytest.approx(u)


def test_brak_wyniku_liczony_jako_wyciek_i_osobno_raportowany(tmp_path):
    _cztery_dokumenty(tmp_path)
    _oceny(tmp_path / "wyniki", "u", "tekst", [
        _rek("d0", brak=True, blad="RuntimeError: coś"),
        _rek("d1", brak=True, blad="timeout 300 s (dokument)"),
        _rek("d2", "en", nieobs=True),
        {**_rek("d3", "de", fp=1000), "blad_sedziego": "ValueError: oryginał"}])
    r = _wiersz(_agreguj(tmp_path), "u")
    assert r["T1"] == 0.0 and r["T2"] == 0.0                    # licznik T2 dokumentu bez wyniku = jego mianownik
    assert (r["bledy"], r["timeouty"], r["nieobslugiwane"], r["bledy_sedziego"], r["odmowy"]) == (1, 1, 1, 1, 0)
    assert r["T5"] is None                                      # żaden dokument z wynikiem – T5 nie z „zera FP”
    assert "T5" in r["uwagi"]


def test_brak_rekordu_oceny_to_wyciek(tmp_path):
    _cztery_dokumenty(tmp_path)
    _oceny(tmp_path / "wyniki", "u", "tekst", [_rek("d0"), _rek("d1"), _rek("d2", "en")])
    r = _wiersz(_agreguj(tmp_path), "u")
    assert r["T1"] == pytest.approx(0.75) and r["brak_oceny"] == 1


def test_odmowa_z_listy_komunikatow_liczona_jak_brak_wyniku_i_osobno(tmp_path):
    _cztery_dokumenty(tmp_path)
    komunikat = "Wiadomość zawiera załączniki – Privatizer nie anonimizuje załączników w plikach EML."
    _uczestnik(tmp_path / "uczestnicy", "u", odmowy=[komunikat])
    _oceny(tmp_path / "wyniki", "u", "tekst", [
        _rek("d0", brak=True, blad=f"RuntimeError: analiza: zadanie review, plik error: {komunikat} Zapisz załączniki osobno."),
        _rek("d1"), _rek("d2", "en"), _rek("d3", "de")])
    r = _wiersz(_agreguj(tmp_path), "u")
    assert r["T1"] == pytest.approx(0.75)
    assert (r["odmowy"], r["bledy"]) == (1, 0)


def test_odmowy_privatizera_plikowego_zapisane():
    komunikaty = ag.komunikaty_odmowy(ag.KORZEN / "uczestnicy" / "privatizer-plik")
    blad = ("RuntimeError: analiza: zadanie review, plik error: Wiadomość zawiera załączniki – Privatizer nie anonimizuje "
            "załączników w plikach EML. Zapisz załączniki osobno i zanonimizuj je jako oddzielne pliki.")
    assert ag.stan_dokumentu({"id": "x", "brak_wyniku": True, "blad": blad}, komunikaty) == "odmowa"
    assert ag.stan_dokumentu({"id": "x", "brak_wyniku": True, "blad": "RuntimeError: inny"}, komunikaty) == "blad"


# ----------------------------------------------------------------------------- aneks, remis, wrażliwość, bootstrap
def test_aneks_poza_rankingiem_pokazany_osobno(tmp_path):
    _cztery_dokumenty(tmp_path)
    _uczestnik(tmp_path / "uczestnicy", "wariant", aneks=True)
    _uczestnik(tmp_path / "uczestnicy", "a")
    for u in ("a", "wariant"):
        _oceny(tmp_path / "wyniki", u, "tekst", [_rek("d0"), _rek("d1"), _rek("d2", "en"), _rek("d3", "de")])
    w = _agreguj(tmp_path)
    a, x = _wiersz(w, "a"), _wiersz(w, "wariant")
    assert a["miejsce"] == 1 and not a["aneks"]
    assert x["aneks"] and x["miejsce"] is None and x["suma"] == pytest.approx(a["suma"])
    assert "wariant" not in a["remis_z"]
    assert all(r["uczestnik"] != "wariant" for r in w["wrazliwosc"])


def test_bootstrap_deterministyczny(tmp_path):
    _korpus(tmp_path / "korpus", [_wpis(f"d{k:02d}", ["pl", "en", "de"][k % 3], tekst=TEKST, gold=GOLD)
                                  for k in range(30)])
    for u, co in (("a", 3), ("b", 3), ("c", 7)):
        _oceny(tmp_path / "wyniki", u, "tekst",
               [_rek(f"d{k:02d}", ["pl", "en", "de"][k % 3],
                     wycieki=[("osoba#1", "OSOBA", "tresc", "pelny")] if k % co == 0 else ()) for k in range(30)])
    w1, w2 = _agreguj(tmp_path), _agreguj(tmp_path)
    assert w1["glowne"] == w2["glowne"]
    a, b = _wiersz(w1, "a"), _wiersz(w1, "b")
    # losowanie sparowane: identyczni uczestnicy mają identyczne przedziały
    assert (a["suma_ci_dol"], a["suma_ci_gora"]) == (b["suma_ci_dol"], b["suma_ci_gora"])
    assert a["suma_ci_dol"] < a["suma"] < a["suma_ci_gora"]
    assert "b" in a["remis_z"]                                  # nakładające się przedziały = remis statystyczny


def test_macierz_bootstrapu_sparowana_i_warstwowana():
    rng = np.random.default_rng(ag.ZIARNO)
    w = ag.macierz_losowan(np.random.default_rng(ag.ZIARNO), 7, 50)
    assert w.shape == (50, 7) and (w.sum(axis=1) == 7).all()
    assert np.array_equal(w, ag.macierz_losowan(rng, 7, 50))
    warstwy = ["a", "a", "b", "b", "b", "c"]
    wt = ag.macierz_losowan(np.random.default_rng(1), 6, 40, warstwy=warstwy)
    assert (wt[:, :2].sum(axis=1) == 2).all() and (wt[:, 2:5].sum(axis=1) == 3).all() and (wt[:, 5] == 1).all()


def test_warstwy_bootstrapu_staly_rozmiar_kazdego_przypadku(tmp_path, monkeypatch):
    """W2: `pisownia_rosyjska_imion` występuje tylko jako przypadek drugi – warstwa po pełnym zestawie przypadków daje
    w każdym losowaniu tyle dokumentów każdego przypadku co w próbie (prerejestracja pkt 3.5)."""
    przypadki = ([["transliteracja", "pisownia_rosyjska_imion"]] * 3 + [["transliteracja"]] * 2
                 + [["homoglify", "pisownia_rosyjska_imion"]] + [["homoglify"]] * 2 + [[]])
    warstwy = ag.warstwy_przypadkow(przypadki)
    assert warstwy[0] == warstwy[1] != warstwy[3] and warstwy[-1] == "-"
    W = ag.macierz_losowan(np.random.default_rng(ag.ZIARNO), len(przypadki), 300, warstwy=warstwy)
    for p in ("transliteracja", "pisownia_rosyjska_imion", "homoglify"):
        maska = np.array([p in pp for pp in przypadki], dtype=float)
        assert (W @ maska == maska.sum()).all(), p
    # warstwy po pierwszym przypadku (przed poprawką) tego nie gwarantują
    stare = ag.macierz_losowan(np.random.default_rng(ag.ZIARNO), len(przypadki), 300,
                               warstwy=[(p or ["-"])[0] for p in przypadki])
    maska = np.array([("pisownia_rosyjska_imion" in pp) for pp in przypadki], dtype=float)
    assert not (stare @ maska == maska.sum()).all()
    # agregacja korzysta z tych warstw
    uzyte = []
    monkeypatch.setattr(ag, "warstwy_przypadkow", lambda pp: uzyte.append(pp) or ["-"] * len(pp))
    _cztery_dokumenty(tmp_path)
    _korpus(tmp_path / "korpus-trudne", [_wpis("h1", tekst=TEKST, gold=GOLD, przypadki=["transliteracja"])])
    _oceny(tmp_path / "wyniki", "u", "tekst", [_rek("d0"), _rek("d1"), _rek("d2", "en"), _rek("d3", "de")])
    _agreguj(tmp_path, wyniki_trudne=tmp_path / "trudne", korpus_trudne=tmp_path / "korpus-trudne")
    assert uzyte == [[["transliteracja"]]]


def test_wrazliwosc_trzy_zestawy_wag(tmp_path):
    _cztery_dokumenty(tmp_path)
    _oceny(tmp_path / "wyniki", "u", "tekst", [_rek("d0"), _rek("d1"), _rek("d2", "en"), _rek("d3", "de")])
    w = _agreguj(tmp_path)
    zestawy = {r["zestaw"] for r in w["wrazliwosc"]}
    assert {"rowne", "prywatnosc", "uzytecznosc"} <= zestawy
    p = next(r for r in w["wrazliwosc"] if r["zestaw"] == "prywatnosc" and r["uczestnik"] == "u")
    assert p["suma"] == pytest.approx(450 + 300 + 50)          # T3 brak (bez warstwy trudnej), T5/T6 waga 0


# ----------------------------------------------------------------------------- T3, P3 (warstwa trudna)
def test_t3_srednia_po_przypadkach_punktowanych(tmp_path):
    _cztery_dokumenty(tmp_path)
    p1, p2 = przypadki_punktowane("tekst")[:2]
    tylko_plik = next(p for p in przypadki_punktowane("plik") if p not in przypadki_punktowane("tekst"))
    trudne = [_wpis("h1", tekst=TEKST, gold=GOLD, przypadki=[p1]), _wpis("h2", tekst=TEKST, gold=GOLD, przypadki=[p1]),
              _wpis("h3", tekst=TEKST, gold=GOLD, przypadki=[p2, p1]),
              _wpis("h4", tekst=TEKST, gold=GOLD, przypadki=[tylko_plik]),
              _wpis("h5", tekst=TEKST, gold=GOLD, przypadki=["posrednie_funkcja_firma"])]
    _korpus(tmp_path / "korpus-trudne", trudne)
    _oceny(tmp_path / "wyniki", "u", "tekst", [_rek("d0"), _rek("d1"), _rek("d2", "en"), _rek("d3", "de")])
    wyc = [("osoba#1", "OSOBA", "tresc", "pelny")]
    _oceny(tmp_path / "trudne", "u", "tekst", [_rek("h1", wycieki=wyc), _rek("h2"), _rek("h3", wycieki=wyc),
                                              _rek("h4", wycieki=wyc), _rek("h5", wycieki=wyc)])
    r = _wiersz(_agreguj(tmp_path, wyniki_trudne=tmp_path / "trudne", korpus_trudne=tmp_path / "korpus-trudne"), "u")
    # OSOBA: s = 2/3. p1: h1 (2/3), h2, h3 (2/3) → 1 − (4/3)/3 = 5/9; p2: h3 → 1/3; T3 = średnia (bez TYLKO_PLIK i bez pośrednich)
    assert r["T3"] == pytest.approx((5 / 9 + 1 / 3) / 2)
    assert r["T3_przypadki"] == 2


# ----------------------------------------------------------------------------- poziom plik: P1, P2, P4, P5, P6
def _plik(i: str, *, wycieki=(), bazowe=(), integralnosc=None, nadmiarowe=None, status="OK", brak=False, nieobs=False,
          blad=None, format_wyj="docx", **inne) -> dict:
    r = {"id": i, "jezyk": "pl", "typ": "pozew", "format": "docx", "nieobslugiwany": nieobs, "brak_wyniku": brak,
         "blad": blad, "czas_s": 1.0, "w_zakresie_oficjalnym": True, "status_pliku": None if nieobs else status,
         "wycieki": [list(w) for w in wycieki], "wartosci_ocenione": len(set(bazowe) | {w[0] for w in wycieki}),
         "niewykrywalne": [], "niejednoznaczne": [], "bazowe": list(bazowe),
         "integralnosc": integralnosc if not brak else None, "format_wyj": format_wyj, "nadmiarowe": nadmiarowe,
         "odcisk_sedziego": {**ODCISK, "tessdata": "d" * 12, "tesseract": "5.3.4", "leptonica": "1.82.0",
                             "libreoffice": "24.2.7.2"}}
    r.update(inne)
    return r


def _integr(otwiera=True, struktura=1.0, spojnosc=1.0, zgodny=True) -> dict:
    return {"otwiera_sie": otwiera, "format_zgodny": zgodny, "zachowanie_struktury": struktura, "spojnosc": spojnosc}


GP = [{"id": "osoba#1", "kategoria": "OSOBA", "tekst": "Jan Kowalski", "jezyk": "pl", "miejsce": "tresc", "waga_klucz": "OSOBA"},
      {"id": "pesel#1", "kategoria": "PESEL", "tekst": "44051401359", "jezyk": "pl", "miejsce": "tresc", "waga_klucz": "PESEL"},
      {"id": "pesel#1", "kategoria": "PESEL", "tekst": "44051401359", "jezyk": "pl", "miejsce": "metadane", "waga_klucz": "PESEL"},
      {"id": "zal:osoba#1", "kategoria": "OSOBA", "tekst": "Jan Kowalski", "jezyk": "pl", "miejsce": "zalacznik",
       "waga_klucz": "OSOBA"}]


def _korpus_plikowy(tmp_path: Path, n: int = 2) -> None:
    _korpus(tmp_path / "korpus", [_wpis(f"d{k}", tekst=TEKST, gold=GOLD, gold_plik=GP) for k in range(n)])


def test_p2_licznik_i_mianownik_z_tych_samych_id(tmp_path):
    """Waga wartości = w(kat)·maks. w(miejsce) jej wpisów gold; mianownik = linia bazowa ∪ wycieki uczestnika."""
    _korpus_plikowy(tmp_path)
    _oceny(tmp_path / "wyniki", "p", "plik", [
        _plik("d0", wycieki=[("pesel#1", "PESEL", "docProps/core.xml", "pelny")],
              bazowe=["osoba#1", "pesel#1"], integralnosc=_integr(), nadmiarowe={"znaki": 0, "poza_gold": 100}),
        _plik("d1", wycieki=[("zal:osoba#1", "OSOBA", "eml:zal", "pelny")], bazowe=["osoba#1"],
              integralnosc=_integr(), nadmiarowe={"znaki": 0, "poza_gold": 100})])
    r = _wiersz(_agreguj(tmp_path), "p", "pliki")
    w_pesel, w_osoba, w_zal = 3 * 2.0, 2 * 1.0, 2 * 1.5            # PESEL: treść + metadane → maks. 2,0
    assert r["P2"] == pytest.approx(1 - (w_pesel + w_zal) / (w_osoba + w_pesel + w_osoba + w_zal))
    assert r["P2_kat"] == pytest.approx(1 - (3 + 2) / (2 + 3 + 2 + 2))
    assert r["P1"] == pytest.approx(1 - (1 + 2 / 3) / 2)             # PESEL s = 1, OSOBA s = 2/3


def test_p2_w_przedziale_dla_przypadku_pilota_ponad_100(tmp_path):
    """Pilot dev (de-email-0008, odmowa EML z załącznikami): sędzia plikowy ocenia wartości `zal:` spoza `gold_tekst`,
    więc stary mianownik z `gold_tekst` dawał wyciek ważony 91/38 > 100%. Mianownik z linii bazowej – dokładnie 100%."""
    gold_tekst = [(0, 12, "osoba#1", "OSOBA", "tresc"), (39, 50, "pesel#1", "PESEL", "tresc")]
    zal = [{"id": f"zal:osoba#{k}", "kategoria": "OSOBA", "tekst": "Jan Kowalski", "jezyk": "de", "miejsce": "zalacznik",
            "waga_klucz": "OSOBA"} for k in range(1, 9)]
    gp = GP[:2] + zal
    _korpus(tmp_path / "korpus", [_wpis("d0", "de", format="eml", tekst=TEKST, gold=gold_tekst, gold_plik=gp)])
    wycieki = [(g["id"], g["kategoria"], "eml:czesc", "pelny") for g in gp]
    blad = ("RuntimeError: analiza: zadanie review, plik error: Wiadomość zawiera załączniki – Privatizer nie anonimizuje "
            "załączników w plikach EML. Zapisz załączniki osobno i zanonimizuj je jako oddzielne pliki.")
    rek = _plik("d0", wycieki=wycieki, brak=True, blad=blad, bazowe=[])
    del rek["bazowe"]                                          # rekord sprzed T17a: linia bazowa = wycieki kopii oryginału
    _oceny(tmp_path / "wyniki", "privatizer-plik", "plik", [rek])
    stary = sum(ag.waga_kategorii(ag.wczytaj_wagi(), w[1]) for w in wycieki) / (2 + 3)
    assert stary > 1
    r = _wiersz(_agreguj(tmp_path, uczestnicy=ag.KORZEN / "uczestnicy"), "privatizer-plik", "pliki")
    assert 0.0 <= r["P2"] <= 1.0 and r["P2"] == 0.0
    assert r["odmowy"] == 1 and r["P6"] == 0.0


def test_p2_nieliczone_bez_linii_bazowej(tmp_path):
    _korpus_plikowy(tmp_path, 1)
    rek = _plik("d0", integralnosc=_integr(), nadmiarowe={"znaki": 0, "poza_gold": 10})
    del rek["bazowe"]
    _oceny(tmp_path / "wyniki", "p", "plik", [rek])
    r = _wiersz(_agreguj(tmp_path), "p", "pliki")
    assert r["P2"] is None and "P2" in r["uwagi"]


def test_nieczytelny_plik_osobno_w_integralnosci(tmp_path):
    _korpus_plikowy(tmp_path, 4)
    _oceny(tmp_path / "wyniki", "p", "plik", [
        _plik("d0", bazowe=["osoba#1"], integralnosc=_integr(struktura=0.5, spojnosc=None),
              nadmiarowe={"znaki": 10, "poza_gold": 100}),
        _plik("d1", bazowe=["osoba#1"], wycieki=[("osoba#1", "OSOBA", "x", "pelny")], status="NIECZYTELNY", brak=True,
              blad="plik wynikowy: NIECZYTELNY"),
        _plik("d2", bazowe=["osoba#1"], integralnosc=_integr(struktura=0.0, zgodny=False, spojnosc=0.5),
              nadmiarowe={"znaki": 0, "poza_gold": 100}, format_wyj="txt"),
        _plik("d3", nieobs=True, wycieki=[("osoba#1", "OSOBA", "x", "pelny")], bazowe=["osoba#1"])])
    r = _wiersz(_agreguj(tmp_path), "p", "pliki")
    # d0: (1 + 0,5)/2; d1 nieczytelny: 0; d2: format zamieniony – struktura pominięta: (1 + 0,5)/2; d3 nieobsługiwany – poza P4
    assert r["P4"] == pytest.approx((0.75 + 0 + 0.75) / 3)
    assert (r["nieczytelne"], r["puste"], r["bledy"], r["nieobslugiwane"]) == (1, 0, 0, 1)
    assert r["format_zmieniony"] == 1
    assert r["P6"] == pytest.approx(2 / 4)
    assert r["P5"] == pytest.approx(max(0.0, 1 - (10 / 200) / 0.20))   # tylko dokumenty z wynikiem
    assert r["P1"] == pytest.approx(2 / 4)


# ----------------------------------------------------------------------------- T6, P7 (czas)
def test_szybkosc_z_pliku_pomiaru_i_bez_pomiaru(tmp_path):
    _cztery_dokumenty(tmp_path)
    _oceny(tmp_path / "wyniki", "u", "tekst", [_rek("d0"), _rek("d1"), _rek("d2", "en"), _rek("d3", "de")])
    bez = _wiersz(_agreguj(tmp_path), "u")
    assert bez["T6"] is None and "T6" in bez["uwagi"]
    czasy = tmp_path / "czasy.jsonl"
    linie = [{"uczestnik": "u", "poziom": "tekst", "id": "d0", "znaki": 3600, "pomiary_s": [4.0, 3.0, 5.0], "status": "ok"},
             {"uczestnik": "u", "poziom": "tekst", "id": "d1", "znaki": 900, "pomiary_s": [0.5, 0.6, 0.4], "status": "ok"},
             {"uczestnik": "u", "poziom": "tekst", "id": "d2", "znaki": 1800, "pomiary_s": [], "status": "timeout"},
             {"uczestnik": "u", "poziom": "tekst", "id": "d3", "znaki": 1800, "pomiary_s": [], "status": "pominiety"}]
    czasy.write_text("".join(json.dumps(l) + "\n" for l in linie), encoding="utf-8")
    r = _wiersz(_agreguj(tmp_path, czasy=czasy), "u")
    # s/stronę: d0 4/2 = 2,0; d1 0,5/1 (min. 1 strona) = 0,5; d2 ∞; d3 poza próbą → mediana 2,0
    assert r["T6_t"] == pytest.approx(2.0)
    assert r["T6"] == pytest.approx(ag.T_REF / 2.0)
    assert r["suma"] == pytest.approx(r["T1_pkt"] + r["T2_pkt"] + r["T4_pkt"] + r["T5_pkt"] + 50 * r["T6"])


def test_szybkosc_co_najmniej_polowa_awarii_to_zero():
    assert ag.wynik_czasu([math.inf, math.inf, 1.0]) == (math.inf, 0.0)
    assert ag.wynik_czasu([math.inf, math.inf, 1.0, 1.0]) == (math.inf, 0.0)    # dokładnie połowa (D5)
    assert ag.wynik_czasu([0.4, 0.8, 3.0]) == (0.8, 1.0)


# ----------------------------------------------------------------------------- przykłady (W1)
def test_przyklady_dla_kazdego_uczestnika_rankingu(tmp_path):
    _korpus(tmp_path / "korpus", [_wpis(f"d{k}", tekst=TEKST, gold=GOLD) for k in range(3)])
    wyc = [("osoba#1", "OSOBA", "tresc", "pelny")]
    nazwy = [f"u{k:02d}" for k in range(13)]                   # więcej uczestników niż dawny limit 20 / 2
    for u in nazwy:
        _oceny(tmp_path / "wyniki", u, "tekst", [_rek(f"d{k}", wycieki=wyc) for k in range(3)])
        _surowe(tmp_path / "wyniki", u, [{"id": f"d{k}", "wykrycia": [[23, 31, "MIASTO", 0.9]]} for k in range(3)])
    _oceny(tmp_path / "wyniki", "zero", "tekst", [_rek(f"d{k}") for k in range(3)])
    _surowe(tmp_path / "wyniki", "zero", [{"id": f"d{k}", "wykrycia": []} for k in range(3)])
    w = _agreguj(tmp_path, powtorzenia=20)
    assert Counter(p["uczestnik"] for p in w["przyklady"]) == {u: ag.PRZYKLADOW_NA_UCZESTNIKA for u in nazwy}
    # deterministycznie: pierwsze dokumenty z wyciekiem w kolejności manifestu, u każdego te same
    assert all([p["id"] for p in w["przyklady"] if p["uczestnik"] == u] == ["d0", "d1"] for u in nazwy)
    assert "[MIASTO]" in w["przyklady"][0]["po"]


# ----------------------------------------------------------------------------- odcisk sędziego (W3)
def test_rozne_odciski_sedziego_przerywaja_agregacje(tmp_path):
    _cztery_dokumenty(tmp_path)
    rek = lambda **k: [_rek("d0", **k), _rek("d1", **k), _rek("d2", "en", **k), _rek("d3", "de", **k)]
    _oceny(tmp_path / "wyniki", "a", "tekst", rek())
    _oceny(tmp_path / "wyniki", "b", "tekst", rek(odcisk_sedziego={**ODCISK, "commit": "inny"}))   # commit – informacyjny
    w = _agreguj(tmp_path, powtorzenia=20)
    assert w["odcisk"] == [{"poziom": "tekst", "kod": ODCISK["kod"], "reguly": ODCISK["reguly"], "commit": "c0ffee;inny"}]
    _oceny(tmp_path / "wyniki", "c", "tekst", rek(odcisk_sedziego={**ODCISK, "kod": "e" * 64}))
    with pytest.raises(ag.NiezgodnyOdcisk, match=r"(?s)różnych sędziów.*a, b.*\bc\b"):
        _agreguj(tmp_path, powtorzenia=20)


def test_rozne_odciski_trzonu_i_warstwy_trudnej_przerywaja(tmp_path):
    _cztery_dokumenty(tmp_path)
    _korpus(tmp_path / "korpus-trudne", [_wpis("h1", tekst=TEKST, gold=GOLD, przypadki=["transliteracja"])])
    _oceny(tmp_path / "wyniki", "u", "tekst", [_rek("d0"), _rek("d1"), _rek("d2", "en"), _rek("d3", "de")])
    _oceny(tmp_path / "trudne", "u", "tekst", [_rek("h1", odcisk_sedziego={**ODCISK, "reguly": "f" * 64})])
    with pytest.raises(ag.NiezgodnyOdcisk, match="u .trudne."):
        _agreguj(tmp_path, wyniki_trudne=tmp_path / "trudne", korpus_trudne=tmp_path / "korpus-trudne")


def test_rekordy_bez_odcisku_tylko_w_pilocie_dev(tmp_path, capsys):
    _cztery_dokumenty(tmp_path)
    rekordy = [_rek("d0"), _rek("d1"), _rek("d2", "en"), _rek("d3", "de")]
    for r in rekordy:
        del r["odcisk_sedziego"]
    _oceny(tmp_path / "wyniki", "u", "tekst", rekordy)
    with pytest.raises(ag.NiezgodnyOdcisk, match="--dopusc-bez-odcisku"):
        _agreguj(tmp_path)
    w = _agreguj(tmp_path, dopusc_bez_odcisku=True)
    assert _wiersz(w, "u")["T1"] == 1.0 and w["odcisk"] == []
    with pytest.raises(ValueError, match="split dev"):
        ag.agreguj(split="test", korpus=tmp_path / "korpus", wyniki=tmp_path / "wyniki", dopusc_bez_odcisku=True)
    argv = ["--split", SPLIT, "--korpus", str(tmp_path / "korpus"), "--wyniki", str(tmp_path / "wyniki"),
            "--uczestnicy", str(tmp_path / "uczestnicy"), "--cel", str(tmp_path / "zb"), "--powtorzenia", "20"]
    assert ag.main(argv) == 2 and "--dopusc-bez-odcisku" in capsys.readouterr().err
    assert not (tmp_path / "zb").exists()
    assert ag.main(argv + ["--dopusc-bez-odcisku"]) == 3          # pilot: liczy, ale ranking niekompletny (T3, T6)
    assert "bez odcisku sędziego" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        ag.main(["--split", "test", "--dopusc-bez-odcisku"])


# ----------------------------------------------------------------------------- bramka publikacji (D1, D2, D8)
def _czasy(tmp_path: Path, uczestnicy: list[str]) -> Path:
    czasy = tmp_path / "czasy.jsonl"
    czasy.write_text("".join(json.dumps({"uczestnik": u, "poziom": "tekst", "id": f"d{k}", "znaki": 1800,
                                         "pomiary_s": [0.5, 0.5, 0.5], "status": "ok"}) + "\n"
                             for u in uczestnicy for k in range(4)), encoding="utf-8")
    return czasy


def test_ranking_kompletny_i_niekompletny(tmp_path):
    _cztery_dokumenty(tmp_path)
    p1 = przypadki_punktowane("tekst")[0]
    _korpus(tmp_path / "korpus-trudne", [_wpis("h1", tekst=TEKST, gold=GOLD, przypadki=[p1])])
    _uczestnik(tmp_path / "uczestnicy", "a")
    _uczestnik(tmp_path / "uczestnicy", "bez_ocen")                    # zadeklarowany, bez pliku ocen (D2)
    _uczestnik(tmp_path / "uczestnicy", "wariant_bez_ocen", aneks=True)
    for u in ("a", "b"):
        _oceny(tmp_path / "wyniki", u, "tekst", [_rek("d0"), _rek("d1"), _rek("d2", "en"), _rek("d3", "de")])
    _oceny(tmp_path / "trudne", "a", "tekst", [_rek("h1")])           # „b” – bez ocen warstwy trudnej (D8)
    w = _agreguj(tmp_path, wyniki_trudne=tmp_path / "trudne", korpus_trudne=tmp_path / "korpus-trudne",
                 czasy=_czasy(tmp_path, ["a", "b"]))
    a, b = _wiersz(w, "a"), _wiersz(w, "b")
    assert a["kompletny"] and not b["kompletny"]
    assert b["T3"] == 0.0 and b["T3_pkt"] == 0.0                     # fail-closed, nie „nieliczony”
    powody = {(r["uczestnik"], r["powod"]) for r in w["niekompletne"]}
    assert powody == {("b", "trudne: brak_oceny 1"), ("bez_ocen", "brak pliku ocen (zadeklarowany poziom tekst)")}


# ----------------------------------------------------------------------------- CLI i pliki CSV
def test_cli_zapisuje_pliki_csv(tmp_path, capsys):
    _cztery_dokumenty(tmp_path)
    _oceny(tmp_path / "wyniki", "u", "tekst", [_rek("d0"), _rek("d1", wycieki=[("pesel#1", "PESEL", "tresc", "pelny")]),
                                              _rek("d2", "en"), _rek("d3", "de")])
    cel = tmp_path / "zbiorcze"
    # bez warstwy trudnej i pomiaru czasu ranking jest niekompletny: tabele zapisane, kod 3, nagłówek NIEKOMPLETNE
    assert ag.main(["--split", SPLIT, "--korpus", str(tmp_path / "korpus"), "--wyniki", str(tmp_path / "wyniki"),
                    "--uczestnicy", str(tmp_path / "uczestnicy"), "--cel", str(cel), "--powtorzenia", "50"]) == 3
    assert "NIEKOMPLETNE" in capsys.readouterr().out
    for nazwa in ("glowne.csv", "per_jezyk.csv", "per_format.csv", "per_typ.csv", "per_kategoria.csv", "per_miejsce.csv",
                  "w_zakresie.csv", "pomocnicze.csv", "wrazliwosc.csv", "czas.csv", "odcisk.csv", "niekompletne.csv",
                  "przyklady.jsonl"):
        assert (cel / nazwa).exists(), nazwa
    with (cel / "glowne.csv").open(encoding="utf-8") as f:
        wiersze = list(csv.DictReader(f))
    assert wiersze[0]["uczestnik"] == "u" and float(wiersze[0]["T1"]) == pytest.approx(0.75)
    kat = list(csv.DictReader((cel / "per_kategoria.csv").open(encoding="utf-8")))
    pesel = next(k for k in kat if k["kategoria"] == "PESEL")
    assert (int(pesel["wartosci"]), int(pesel["wyciekle"])) == (4, 1)


# ----------------------------------------------------------------------------- T1/P1/T3/T4 ważone kategorią
def _dokumenty_wazone(tmp_path: Path) -> None:
    """d0 bez wycieku, d1 tylko miejscowość (w=1), d2 tylko osoba (w=2), d3 osoba i PESEL (w=3); języki pl,pl,en,en."""
    _cztery_dokumenty(tmp_path, ("pl", "pl", "en", "en"))
    _oceny(tmp_path / "wyniki", "u", "tekst", [
        _rek("d0"),
        _rek("d1", wycieki=[("miasto#1", "MIEJSCOWOSC", "tresc", "pelny")]),
        _rek("d2", "en", wycieki=[("osoba#1", "OSOBA", "tresc", "czesciowy")]),
        _rek("d3", "en", wycieki=[("osoba#1", "OSOBA", "tresc", "pelny"), ("pesel#1", "PESEL", "tresc", "pelny")])])


def test_waga_dokumentu_to_maks_waga_kategorii_przez_trzy(tmp_path):
    _dokumenty_wazone(tmp_path)
    wpisy = [json.loads(l) for l in (tmp_path / "korpus" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    rek = ag._jsonl(tmp_path / "wyniki" / "oceny" / "u" / SPLIT / "tekst.jsonl")
    v = ag.wektory(wpisy, rek, "tekst", ag.wczytaj_wagi())
    assert list(v.wyciek_w) == pytest.approx([0, 1 / 3, 2 / 3, 1])      # KWOTA/miejscowość 1/3, OSOBA 2/3, OSOBA+PESEL 1
    assert list(v.wyciek) == [0, 1, 1, 1]                               # wektor 0/1 (liczniki opisowe)


def test_t1_t4_wazone_kategoria_a_reszta_bez_wplywu(tmp_path):
    _dokumenty_wazone(tmp_path)
    r = _wiersz(_agreguj(tmp_path), "u")
    assert r["T1"] == pytest.approx(1 - (1 / 3 + 2 / 3 + 1) / 4)        # 0,5
    # T4: pl = 1 − (1/3)/2, en = 1 − (2/3 + 1)/2 → min = en
    assert r["T4"] == pytest.approx(1 - (2 / 3 + 1) / 2)
    assert r["T1_pkt"] == pytest.approx(350 * r["T1"]) and r["T4_pkt"] == pytest.approx(50 * r["T4"])
    assert r["z_wyciekiem"] == 3 and r["dokumenty"] == 4
    assert "punktacja" not in r


def test_fail_closed_to_waga_jeden(tmp_path):
    _cztery_dokumenty(tmp_path, ("pl", "pl", "en", "de"))
    _oceny(tmp_path / "wyniki", "u", "tekst", [
        _rek("d0", brak=True, blad="RuntimeError: coś"), _rek("d1", brak=True, blad="timeout 300 s (dokument)"),
        _rek("d2", "en", nieobs=True), _rek("d3", "de")])
    r = _wiersz(_agreguj(tmp_path), "u")
    assert r["T1"] == pytest.approx(0.25)                               # trzy dokumenty fail-closed po s = 1
    assert r["T4"] == pytest.approx(0.0)


def test_p1_wazone_kategoria_nie_miejscem(tmp_path):
    _korpus_plikowy(tmp_path, 3)
    _oceny(tmp_path / "wyniki", "p", "plik", [
        _plik("d0", bazowe=["osoba#1", "pesel#1"], integralnosc=_integr(), nadmiarowe={"znaki": 0, "poza_gold": 100}),
        # wyciek OSOBA w załączniku (miejsce 1,5) – waga dokumentu to 2/3, bez wagi miejsca
        _plik("d1", wycieki=[("zal:osoba#1", "OSOBA", "eml:zal", "pelny")], bazowe=["osoba#1"],
              integralnosc=_integr(), nadmiarowe={"znaki": 0, "poza_gold": 100}),
        # wyciek PESEL w metadanych (miejsce 2,0) – 1
        _plik("d2", wycieki=[("pesel#1", "PESEL", "docProps/core.xml", "pelny")], bazowe=["pesel#1"],
              integralnosc=_integr(), nadmiarowe={"znaki": 0, "poza_gold": 100})])
    r = _wiersz(_agreguj(tmp_path), "p", "pliki")
    assert r["P1"] == pytest.approx(1 - (2 / 3 + 1) / 3)


def test_bootstrap_i_wrazliwosc_z_wagami(tmp_path):
    _dokumenty_wazone(tmp_path)
    w = _agreguj(tmp_path)
    r = _wiersz(w, "u")
    assert r["T1_ci_dol"] <= r["T1"] <= r["T1_ci_gora"]
    assert w["wrazliwosc"] and not any("punktacja" in x for x in w["wrazliwosc"] + w["odcisk"])


def test_jeden_plik_wag_bez_numeru_wersji():
    """Jedna punktacja: `metodyka/wagi_punktow.json`, bez pola wersji; test 1 rankingu to T1/P1 ważone kategorią."""
    assert ag.WAGI.name == "wagi_punktow.json" and not hasattr(ag, "WAGI_WERSJI")
    assert not (ag.WAGI.parent / "wagi_punktow-2.json").exists()
    w = ag.wczytaj_wagi()
    assert "wersja" not in w
    assert sum(w["ranking_tekst"].values()) == 1000 and sum(w["ranking_pliki"].values()) == 1000
    assert ag.wagi_testow(w, "tekst")["T1"] == 350 and ag.wagi_testow(w, "pliki")["P1"] == 350


def test_cli_bez_opcji_punktacja(tmp_path, capsys):
    _dokumenty_wazone(tmp_path)
    baza = ["--split", SPLIT, "--korpus", str(tmp_path / "korpus"), "--wyniki", str(tmp_path / "wyniki"),
            "--uczestnicy", str(tmp_path / "uczestnicy"), "--powtorzenia", "30"]
    with pytest.raises(SystemExit) as e:
        ag.main([*baza, "--punktacja", "2", "--cel", str(tmp_path / "bez")])
    assert e.value.code == 2 and "--punktacja" in capsys.readouterr().err
    assert ag.main([*baza, "--cel", str(tmp_path / "z")]) == 3
    for nazwa in ("glowne", "wrazliwosc", "odcisk"):
        wiersze = list(csv.DictReader((tmp_path / "z" / f"{nazwa}.csv").open(encoding="utf-8")))
        assert wiersze and "punktacja" not in wiersze[0]


def test_t3_wazone_kategoria(tmp_path):
    """T3: średnia po przypadkach z 1 − Σ s(d) / n; wyciek samej miejscowości/kwoty (w = 1) wnosi 1/3."""
    _cztery_dokumenty(tmp_path)
    p1, p2 = przypadki_punktowane("tekst")[:2]
    trudne = [_wpis(f"h{k}", tekst=TEKST, gold=GOLD, przypadki=pp) for k, pp in enumerate([[p1], [p1], [p1, p2], [p2]], 1)]
    _korpus(tmp_path / "korpus-trudne", trudne)
    _oceny(tmp_path / "wyniki", "u", "tekst", [_rek("d0"), _rek("d1"), _rek("d2", "en"), _rek("d3", "de")])
    kwota = [("miasto#1", "MIEJSCOWOSC", "tresc", "pelny")]
    osoba_pesel = [("osoba#1", "OSOBA", "tresc", "pelny"), ("pesel#1", "PESEL", "tresc", "pelny")]
    _oceny(tmp_path / "trudne", "u", "tekst", [_rek("h1", wycieki=kwota), _rek("h2"), _rek("h3", wycieki=osoba_pesel),
                                              _rek("h4", brak=True, blad="boom")])
    k = dict(wyniki_trudne=tmp_path / "trudne", korpus_trudne=tmp_path / "korpus-trudne")
    r = _wiersz(_agreguj(tmp_path, **k), "u")
    # p1: h1 (1/3), h2 (0), h3 (1) → 1 − (4/3)/3; p2: h3 (1), h4 (fail-closed, 1) → 1 − 2/2 = 0
    assert r["T3"] == pytest.approx((1 - (1 / 3 + 1) / 3 + 0) / 2)
