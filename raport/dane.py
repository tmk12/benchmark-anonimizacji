"""Model danych raportu: wczytanie CSV agregacji (`zbiorcze`) i czasów, formatery liczb po polsku, etykiety miejsc, porównanie trybów.

Tylko stdlib. Pusta komórka = wartość nieliczona = `None` (w tabelach „n/d”, nigdy `nan`/`0`). Ścieżka wyników zawsze z argumentu."""
from __future__ import annotations

import csv
import json
import math
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

METODYKA = Path(__file__).resolve().parent.parent / "metodyka"  # wersjonowane pliki metodyki (tag prerejestracja-1)
REPOZYTORIUM = "https://github.com/tmk12/benchmark-anonimizacji"  # repozytorium benchmarku (aneks odtworzenia)
LICZBY_OPISOWE = Path(__file__).resolve().parent / "liczby_opisowe.toml"  # stałe metodyki i opisu korpusu spoza agregacji
ZAKRESY_PRZYKLADOW = Path(__file__).resolve().parent / "dane" / "przyklady_zakresy.json"  # offsety wycieku w przykładach (narzedzia/zakresy_przykladow.py)
TESTY = ["T1", "T2", "T3", "T4", "T5", "T6", "P1", "P2", "P3", "P4", "P5", "P6", "P7"]
PER = ["format", "jezyk", "typ", "kategoria", "miejsce", "przypadek"]
ND = "n/d"
NBSP = " "

# Tryb domyślny vs „Maksymalna ochrona” (uczestnik rankingu → wariant w aneksie).
TRYBY = {"tekst": ("privatizer-tekst", "privatizer-tekst-maks"), "pliki": ("privatizer-plik", "privatizer-plik-maks")}


@dataclass
class Test:
    __test__ = False  # nie jest klasą testową pytesta
    wartosc: float | None
    pkt: float | None
    ci: tuple[float, float] | None


@dataclass
class Wiersz:
    uczestnik: str
    miejsce: int | None
    remis_z: list[str]
    suma: float
    suma_ci: tuple[float, float]
    testy: dict[str, Test]
    dokumenty: int | None = None
    z_wyciekiem: int | None = None
    bledy: int | None = None
    odmowy: int | None = None
    nieobslugiwane: int | None = None
    uwagi: str = ""
    format_zmieniony: int | None = None  # dokumenty, których format wyjścia różni się od wejściowego (np. DOC → DOCX, MSG → TXT)


@dataclass
class Raport:
    rankingi: dict[str, list[Wiersz]] = field(default_factory=dict)
    aneks: dict[str, list[Wiersz]] = field(default_factory=dict)
    per: dict[str, list[dict]] = field(default_factory=dict)
    czas: list[dict] = field(default_factory=list)
    wrazliwosc: list[dict] = field(default_factory=list)
    pomocnicze: list[dict] = field(default_factory=list)
    w_zakresie: list[dict] = field(default_factory=list)
    odcisk: list[dict] = field(default_factory=list)
    wersje: dict = field(default_factory=dict)
    przyklady: list[dict] = field(default_factory=list)
    czas_podsumowanie: list[dict] = field(default_factory=list)  # czas-m1/podsumowanie.txt: start i szczyt pamięci (poza agregacją)
    niekompletne: list[dict] = field(default_factory=list)
    # kontrola domen zarezerwowanych (`kontrola-domen/` obok zbiorczych; brak plików = sekcje raportu pomijane)
    kontrola_domen: list[dict] = field(default_factory=list)
    ranking_bez_example: dict[str, list[Wiersz]] = field(default_factory=dict)
    kontrola_domen_meta: dict = field(default_factory=dict)


# ---------------------------------------------------------------- formatery PL

def liczba(x: float | None, miejsca: int = 1) -> str:
    """Liczba po polsku: przecinek dziesiętny, niełamliwa spacja tysięcy, „n/d” dla nieliczonej."""
    if x is None:
        return ND
    return f"{x:,.{miejsca}f}".replace(",", NBSP).replace(".", ",")


def procent(x: float | None, miejsca: int = 1) -> str:
    """Ułamek (0–1) jako procent, np. 0,1234 → „12,3%”."""
    if x is None:
        return ND
    return liczba(x * 100, miejsca) + "%"


def _przedzial_tekst(dol: str, gora: str) -> str:
    """Przedział „[a–b]”; gdy któryś kraniec jest ujemny, średnik zamiast półpauzy („[−18,3; −12,2]”), żeby minus nie myli się z separatorem."""
    return f"[{dol}; {gora}]" if "−" in dol + gora else f"[{dol}–{gora}]"


def przedzial(ci: tuple[float, float] | None, miejsca: int = 0) -> str:
    """Przedział ufności „[766–778]”, z ujemnym krańcem „[−18,3; −12,2]”."""
    if ci is None or ci[0] is None or ci[1] is None:
        return ND
    return _przedzial_tekst(_minus(liczba(ci[0], miejsca)), _minus(liczba(ci[1], miejsca)))


def przedzial_procent(dol: float | None, gora: float | None, miejsca: int = 1) -> str:
    """Przedział ufności odsetków (ułamki 0–1) w procentach, np. „[9,9–14,0]”; brak krańca → „n/d”."""
    if dol is None or gora is None:
        return ND
    return _przedzial_tekst(_minus(liczba(dol * 100, miejsca)), _minus(liczba(gora * 100, miejsca)))


def _minus(tekst: str) -> str:
    """Znak minus typograficzny (U+2212) i brak „-0,0” dla ujemnych wartości zaokrąglonych do zera."""
    if tekst.startswith("-"):
        return tekst[1:] if not any(c in "123456789" for c in tekst) else "−" + tekst[1:]
    return tekst


def roznica(x: float | None, miejsca: int = 1) -> str:
    """Różnica punktów (ze znakiem minus U+2212, bez „-0,0”); brak → „n/d”."""
    return ND if x is None else _minus(liczba(x, miejsca))


def sekundy(x: float | None) -> str:
    """Sekundy na stronę: 2 miejsca, 3 od 0,01 s; poniżej – dwie cyfry znaczące (np. 0,00055), żeby nie zaokrąglić do 0,00;
    jedna funkcja dla tabel i wykresów, więc ta sama wartość wygląda wszędzie tak samo."""
    if x is None:
        return ND
    if x >= 0.1:
        return liczba(x, 2)
    if x >= 0.01:
        return liczba(x, 3)
    if x <= 0:
        return liczba(x, 2)
    return liczba(x, max(4, 1 - math.floor(math.log10(x))))


def prywatizer(nazwa: str) -> bool:
    """Czy uczestnik należy do rodziny Privatizera (nazwa zaczyna się od „privatizer”)."""
    return nazwa.startswith("privatizer")


def roznica_pp(x: float | None, miejsca: int = 1) -> str:
    """Różnica odsetków (ułamek 0–1) w punktach procentowych, np. „−15,1 p.p.” (niełamliwa spacja); brak → „n/d”."""
    return ND if x is None else f"{_minus(liczba(x * 100, miejsca))}{NBSP}p.p."


def etykieta_miejsca(w: Wiersz, wiersze: list[Wiersz]) -> str:
    """„N” albo „min–max (remis)”; grupa remisu = domknięcie przechodnie `remis_z` (może łączyć trzech i więcej)."""
    if w.miejsce is None:
        return "–"
    po_nazwie = {x.uczestnik: x for x in wiersze}
    grupa, kolejka = {w.uczestnik}, [w.uczestnik]
    while kolejka:
        x = po_nazwie.get(kolejka.pop())
        for inny in (x.remis_z if x else []):
            if inny not in grupa:
                grupa.add(inny)
                kolejka.append(inny)
    miejsca = [po_nazwie[u].miejsce for u in grupa if u in po_nazwie and po_nazwie[u].miejsce is not None]
    if len(grupa) < 2 or not miejsca:
        return str(w.miejsce)
    return f"{min(miejsca)}–{max(miejsca)} (remis)"


# ---------------------------------------------------------------- wczytywanie

def _liczba(s: str | None) -> float | None:
    if s is None or s.strip() == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _wartosc(s: str):
    """Komórka CSV → None (pusta) / int / float / napis."""
    if s is None or s.strip() == "":
        return None
    for typ in (int, float):
        try:
            return typ(s)
        except ValueError:
            pass
    return s


def _csv(plik: Path) -> list[dict]:
    if not plik.is_file():
        return []
    with open(plik, encoding="utf-8", newline="") as f:
        return [{k: _wartosc(v) for k, v in rzad.items()} for rzad in csv.DictReader(f)]


def _csv_surowy(plik: Path) -> list[dict]:
    if not plik.is_file():
        return []
    with open(plik, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _wiersz(r: dict) -> Wiersz:
    testy = {}
    for t in TESTY:
        dol, gora = _liczba(r.get(t + "_ci_dol")), _liczba(r.get(t + "_ci_gora"))
        testy[t] = Test(_liczba(r.get(t)), _liczba(r.get(t + "_pkt")), (dol, gora) if dol is not None and gora is not None else None)
    miejsce = _liczba(r.get("miejsce"))
    dok, wyc = _liczba(r.get("dokumenty")), _liczba(r.get("z_wyciekiem"))
    calk = lambda pole: int(x) if (x := _liczba(r.get(pole))) is not None else None
    return Wiersz(
        uczestnik=r["uczestnik"],
        miejsce=int(miejsce) if miejsce is not None else None,
        remis_z=[x for x in re.split(r"[;,|]\s*", r.get("remis_z") or "") if x],
        suma=_liczba(r.get("suma")),
        suma_ci=(_liczba(r.get("suma_ci_dol")), _liczba(r.get("suma_ci_gora"))),
        testy=testy,
        dokumenty=int(dok) if dok is not None else None,
        z_wyciekiem=int(wyc) if wyc is not None else None,
        bledy=calk("bledy"), odmowy=calk("odmowy"), nieobslugiwane=calk("nieobslugiwane"),
        uwagi=(r.get("uwagi") or "").strip(), format_zmieniony=calk("format_zmieniony"),
    )


def _kontrola_domen(katalog: Path) -> tuple[list[dict], dict[str, list[Wiersz]], dict]:
    """Wynik kontroli domen (`kontrola_domen.csv`, `ranking_bez_example.csv`, `meta.json`); brak katalogu/plików → puste."""
    wiersze = _csv(katalog / "kontrola_domen.csv")
    for w in wiersze:
        w["aneks"] = w.get("aneks") == "True"
    ranking: dict[str, list[Wiersz]] = {}
    for rzad in _csv_surowy(katalog / "ranking_bez_example.csv"):
        if rzad.get("aneks") != "True":
            ranking.setdefault(rzad["ranking"], []).append(_wiersz(rzad))
    meta = katalog / "meta.json"
    return wiersze, ranking, json.loads(meta.read_text(encoding="utf-8")) if meta.is_file() else {}


def _podsumowanie_czasu(plik: Path) -> list[dict]:
    """Tabela Markdown `pbench-czas --podsumuj` → wiersze `{uczestnik, poziom, dokumenty, s_na_strone, awarie, start_s, szczyt_mb, metoda}`."""
    wiersze = []
    for linia in plik.read_text(encoding="utf-8").splitlines():
        komorki = [k.strip() for k in linia.strip().strip("|").split("|")]
        if len(komorki) < 8 or komorki[0] in ("uczestnik", "") or set(komorki[0]) <= {"-", ":"}:
            continue
        try:
            wiersze.append({"uczestnik": komorki[0], "poziom": komorki[1], "dokumenty": int(komorki[2]), "s_na_strone": float(komorki[3]),
                            "awarie": int(komorki[4]), "start_s": float(komorki[5]), "szczyt_mb": int(komorki[6]), "metoda": komorki[7]})
        except ValueError:  # nie gubimy wiersza po cichu: brak wartości = jawne n/d (None), nie 0
            liczby = []
            for k, typ in zip(komorki[2:7], (int, float, int, float, int)):
                try:
                    liczby.append(typ(k))
                except ValueError:
                    liczby.append(None)
            wiersze.append({"uczestnik": komorki[0], "poziom": komorki[1], "dokumenty": liczby[0], "s_na_strone": liczby[1],
                            "awarie": liczby[2], "start_s": liczby[3], "szczyt_mb": liczby[4], "metoda": komorki[7]})
    return wiersze


def wczytaj(wyniki: Path, czas: Path | None = None) -> Raport:
    """Wczytuje katalog zbiorczy `wyniki`; `czas` = katalog `czas-m1` z `wersje.json` (domyślnie sąsiedni `czas-m1`, jeśli istnieje)."""
    wyniki = Path(wyniki)
    if czas is None and (wyniki.parent / "czas-m1").is_dir():
        czas = wyniki.parent / "czas-m1"
    r = Raport()
    for rzad in _csv_surowy(wyniki / "glowne.csv"):
        cel = r.aneks if rzad.get("aneks") == "True" else r.rankingi
        cel.setdefault(rzad["ranking"], []).append(_wiersz(rzad))
    for kolumna in PER:
        r.per[kolumna] = _csv(wyniki / f"per_{kolumna}.csv")
    r.czas = _csv(wyniki / "czas.csv")
    r.wrazliwosc = _csv(wyniki / "wrazliwosc.csv")
    r.pomocnicze = _csv(wyniki / "pomocnicze.csv")
    r.w_zakresie = _csv(wyniki / "w_zakresie.csv")
    r.niekompletne = _csv(wyniki / "niekompletne.csv")
    r.odcisk = _csv_surowy(wyniki / "odcisk.csv")
    r.kontrola_domen, r.ranking_bez_example, r.kontrola_domen_meta = _kontrola_domen(wyniki / "kontrola-domen")
    wersje = czas / "wersje.json" if czas else None
    if wersje and wersje.is_file():
        r.wersje = json.loads(wersje.read_text(encoding="utf-8"))
    if czas and (czas / "podsumowanie.txt").is_file():
        r.czas_podsumowanie = _podsumowanie_czasu(czas / "podsumowanie.txt")
    przyklady = wyniki / "przyklady.jsonl"
    if przyklady.is_file():
        r.przyklady = [json.loads(l) for l in przyklady.read_text(encoding="utf-8").splitlines() if l.strip()]
    return r


# ---------------------------------------------------------------- metodyka (pliki z repo)

def wagi_testow() -> dict[str, int]:
    """Maksymalne punkty testów (`T1`…`T6`, `P1`…`P7`) z `metodyka/wagi_punktow.json`."""
    dane = json.loads((METODYKA / "wagi_punktow.json").read_text(encoding="utf-8"))
    return {klucz.split("_")[0]: pkt for ranking in ("ranking_tekst", "ranking_pliki") for klucz, pkt in dane[ranking].items()}


def wagi_punktow() -> dict:
    """Cały `metodyka/wagi_punktow.json` (wagi kategorii, miejsc, progi, zestawy analizy wrażliwości)."""
    return json.loads((METODYKA / "wagi_punktow.json").read_text(encoding="utf-8"))


def liczby_opisowe() -> dict:
    """Stałe metodyki i opisu korpusu z `raport/liczby_opisowe.toml` (źródło każdej sekcji w komentarzu pliku); rozdziały: `{{ m.sekcja.klucz }}`."""
    return tomllib.loads(LICZBY_OPISOWE.read_text(encoding="utf-8"))


def kontaminacja() -> dict[str, dict]:
    """Wyniki kontroli kontaminacji (8-gramy) z `metodyka/kontaminacja.json` (trzon) i `kontaminacja-trudne.json` (warstwa trudna)."""
    return {k: json.loads((METODYKA / f"kontaminacja{s}.json").read_text(encoding="utf-8")) for k, s in (("trzon", ""), ("trudne", "-trudne"))}


def zakresy_przykladow() -> dict[str, dict]:
    """Offsety wartości wzorcowej w oknie `przed` przykładów: `{"<id>|<wartosc_id>": {"od", "do", "tekst"}}`; brak pliku → `{}` (bez podświetlenia)."""
    if not ZAKRESY_PRZYKLADOW.is_file():
        return {}
    return json.loads(ZAKRESY_PRZYKLADOW.read_text(encoding="utf-8"))


def pamiec_wysoka(r: "Raport") -> list[dict]:
    """Wiersze podsumowania czasu ze szczytem pamięci powyżej `czas.prog_pamieci` · `czas.ram_mb` (malejąco); brak podsumowania → `[]`."""
    c = liczby_opisowe()["czas"]
    prog = c["prog_pamieci"] * c["ram_mb"]
    return sorted((x for x in r.czas_podsumowanie if x["szczyt_mb"] is not None and x["szczyt_mb"] > prog), key=lambda x: -x["szczyt_mb"])


def czas_podsumowanie_wg_pamieci(r: "Raport") -> list[dict]:
    """Wiersze podsumowania czasu od największego szczytu pamięci; wiersz bez pomiaru (`None`, „n/d”) na końcu."""
    return sorted(r.czas_podsumowanie, key=lambda x: (x["szczyt_mb"] is None, -(x["szczyt_mb"] if x["szczyt_mb"] is not None else 0), x["uczestnik"]))


def suma_bez_szybkosci(w: Wiersz | None, ranking: str = "tekst") -> float | None:
    """Suma punktów bez testu szybkości (T6 w tekście, P7 w plikach): warianty aneksu (np. „Maksymalna ochrona”) nie mają pomiaru czasu."""
    if w is None or w.suma is None:
        return None
    return w.suma - (w.testy["T6" if ranking == "tekst" else "P7"].pkt or 0.0)


def maks_punktow(ranking: str) -> int:
    """Maksymalna suma punktów rankingu (suma wag jego testów)."""
    wagi = wagi_testow()
    return sum(wagi[t] for t in wagi if t.startswith("T" if ranking == "tekst" else "P"))


# ---------------------------------------------------------------- porównanie trybów

def kategorie_trybow(r: Raport, ranking: str) -> dict[str, dict[str, dict]]:
    """Wiersze `per_kategoria` obu trybów rankingu: `{uczestnik: {kategoria: wiersz}}`; nieznany ranking → `{}`."""
    if ranking not in TRYBY:
        return {}
    kat: dict[str, dict[str, dict]] = {u: {} for u in TRYBY[ranking]}
    for k in r.per.get("kategoria", []):
        if k["ranking"] == ranking and k["uczestnik"] in kat:
            kat[k["uczestnik"]][k["kategoria"]] = k
    return kat


def porownanie_trybow(r: Raport) -> list[dict]:
    """Tryb domyślny vs „Maksymalna ochrona”: wiersze `{ranking, wiersz, domyslny, maks}`; `None` = brak pomiaru (n/d), nigdy 0."""
    wynik = []
    for ranking, (domyslny, maks) in TRYBY.items():
        kat = kategorie_trybow(r, ranking)
        wiersze = {w.uczestnik: w for w in r.rankingi.get(ranking, []) + r.aneks.get(ranking, [])}
        if not any(kat[u] or u in wiersze for u in kat):
            continue

        def suma(u, tylko=None, bez=None):
            """Suma wyciekłych wartości; brak kategorii albo choć jednej wartości w sumie → None (nie 0)."""
            if not kat[u]:
                return None
            if tylko is not None:
                k = kat[u].get(tylko)
                return None if k is None else k["wyciekle"]
            wartosci = [k["wyciekle"] for n, k in kat[u].items() if n != bez]
            return None if not wartosci or any(v is None for v in wartosci) else sum(wartosci)

        def pokaz(etykieta, f):
            wynik.append({"ranking": ranking, "wiersz": etykieta, "domyslny": f(domyslny), "maks": f(maks)})

        pokaz("Wyciekłe wartości", lambda u: suma(u))
        pokaz("w tym kwoty", lambda u: suma(u, tylko="KWOTA"))
        pokaz("Wyciek bez kwot", lambda u: suma(u, bez="KWOTA"))
        pokaz("Dokumenty z wyciekiem", lambda u: wiersze[u].z_wyciekiem if u in wiersze else None)
    return wynik


# ---------------------------------------------------------------- pomocnicy do prozy i tabel

def wiersz(r: Raport, ranking: str, uczestnik: str) -> Wiersz | None:
    """Wiersz uczestnika z rankingu albo aneksu (None, gdy go nie ma)."""
    for w in r.rankingi.get(ranking, []) + r.aneks.get(ranking, []):
        if w.uczestnik == uczestnik:
            return w
    return None


def wiersze_podsumowania(r: Raport, ranking: str, n: int = 5) -> list[Wiersz]:
    """Wiersze podsumowania: `n` pierwszych miejsc rankingu i każdy wiersz Privatizera spoza nich (w kolejności miejsc)."""
    wszystkie = sorted(r.rankingi.get(ranking, []), key=lambda w: (w.miejsce is None, w.miejsce or 0, w.uczestnik))
    return wszystkie[:n] + [w for w in wszystkie[n:] if w.uczestnik.startswith("privatizer")]


def odmiana(n: int, forma1: str, forma24: str, forma5: str) -> str:
    """Forma rzeczownika po liczebniku: 1 → forma1, 2–4 (poza 12–14) → forma24, reszta (w tym 0) → forma5."""
    n = abs(int(n))
    if n == 1:
        return forma1
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return forma24
    return forma5


def ile(n: int | None, forma1: str, forma24: str, forma5: str) -> str:
    """„N forma” z poprawną odmianą; brak danych (None) → „n/d”."""
    if n is None:
        return ND
    return f"{liczba(n, 0)} {odmiana(n, forma1, forma24, forma5)}"


def pozycja_szybkosci(r: Raport, ranking: str, uczestnik: str) -> dict | None:
    """Szybkość uczestnika wśród uczestników rankingu z pomiarem czasu: `{miejsce (1 = najszybszy), z, s_na_strone, pkt, maks}`; brak pomiaru → `None`."""
    w_rankingu = {w.uczestnik for w in r.rankingi.get(ranking, [])}
    czasy = {c["uczestnik"]: c["s_na_strone"] for c in r.czas if c["ranking"] == ranking and c["uczestnik"] in w_rankingu and c.get("s_na_strone") is not None}
    w = wiersz(r, ranking, uczestnik)
    if uczestnik not in czasy or w is None:
        return None
    test = "T6" if ranking == "tekst" else "P7"
    return {"miejsce": 1 + sum(1 for v in czasy.values() if v < czasy[uczestnik]), "z": len(czasy), "s_na_strone": czasy[uczestnik],
            "pkt": w.testy[test].pkt, "maks": wagi_testow()[test]}


# ---------------------------------------------------------------- kontrola domen zarezerwowanych


def liczebnosc_domen(r: Raport, ranking: str, kategoria: str) -> dict | None:
    """Liczba wartości EMAIL/URL w trzonie rankingu: `{example, test}` (z `kontrola-domen`, wspólne dla uczestników rankingu); brak danych → `None`."""
    wiersze = kontrola_domen_wiersze(r, ranking, kategoria)
    return {"example": wiersze[0]["example_n"], "test": wiersze[0]["test_n"]} if wiersze else None

def kontrola_domen_wiersze(r: Raport, ranking: str, kategoria: str) -> list[dict]:
    """Wiersze kontroli domen uczestników rankingu (bez aneksu) dla kategorii, w kolejności miejsc rankingu głównego; brak danych → `[]`."""
    miejsca = {w.uczestnik: (w.miejsce is None, w.miejsce or 0) for w in r.rankingi.get(ranking, [])}
    wiersze = [x for x in r.kontrola_domen if x["ranking"] == ranking and x["kategoria"] == kategoria and not x["aneks"]]
    return sorted(wiersze, key=lambda x: (miejsca.get(x["uczestnik"], (True, 0)), x["uczestnik"]))


def sygnaly_domen(r: Raport, ranking: str) -> list[dict]:
    """Uczestnicy rankingu (bez aneksu) z sygnałem przewagi w którejkolwiek kategorii (`sygnal == "tak"`)."""
    return [x for k in ("EMAIL", "URL") for x in kontrola_domen_wiersze(r, ranking, k) if x.get("sygnal") == "tak"]


def przewaga_domen(r: Raport) -> bool | None:
    """Czy któryś uczestnik rankingu z rodziny Privatizera (bez aneksu) ma sygnał przewagi; `None` – brak wyniku kontroli (sekcja pomijana)."""
    if not r.kontrola_domen:
        return None
    return any(x["uczestnik"].startswith("privatizer") for rk in r.rankingi for x in sygnaly_domen(r, rk))


def domeny_wiersz(r: Raport, ranking: str, uczestnik: str, kategoria: str) -> dict | None:
    """Wiersz kontroli domen uczestnika (rankingu albo aneksu) w kategorii; `None` – brak."""
    return next((x for x in r.kontrola_domen if x["ranking"] == ranking and x["uczestnik"] == uczestnik and x["kategoria"] == kategoria), None)


def zmiana_rankingu(r: Raport, ranking: str) -> dict | None:
    """Ranking bez wartości `example.*` względem głównego: liderzy, największa zmiana sumy (wartość bezwzględna, pkt), liczba uczestników
    z innym numerem miejsca, lista zmian etykiety miejsca (numer albo remis, np. „3” → „3–4 (remis)”) i to, czy trzy pierwsze miejsca mają tych samych uczestników w tej samej kolejności; `None` – brak wariantu."""
    wariant = {w.uczestnik: w for w in r.ranking_bez_example.get(ranking, [])}
    glowny = [w for w in r.rankingi.get(ranking, []) if w.uczestnik in wariant and w.miejsce is not None and wariant[w.uczestnik].miejsce is not None]
    if not glowny:
        return None
    zmiany = {w.uczestnik: wariant[w.uczestnik].suma - w.suma for w in glowny}
    najwieksza = max(zmiany, key=lambda u: (abs(zmiany[u]), u))
    pierwsi = lambda ws: [w.uczestnik for w in sorted(ws, key=lambda w: (w.miejsce, w.uczestnik))][:3]
    wszyscy_glowny, wszyscy_wariant = r.rankingi.get(ranking, []), list(wariant.values())
    etykiety = [{"uczestnik": w.uczestnik, "glowny": etykieta_miejsca(w, wszyscy_glowny), "wariant": etykieta_miejsca(wariant[w.uczestnik], wszyscy_wariant)} for w in
                sorted(glowny, key=lambda w: (w.miejsce, w.uczestnik))]
    etykiety = [e for e in etykiety if e["glowny"] != e["wariant"]]
    return {"zmiany_etykiet": etykiety, "zmienione_etykiety": len(etykiety), "lider_glowny": pierwsi(glowny)[0], "lider_wariant": pierwsi(list(wariant.values()))[0],
            "suma_lidera_wariant": wariant[pierwsi(list(wariant.values()))[0]].suma,
            "najwieksza_zmiana": abs(zmiany[najwieksza]), "uczestnik_najwiekszej_zmiany": najwieksza,
            "zmienione_miejsca": sum(1 for w in glowny if w.miejsce != wariant[w.uczestnik].miejsce), "uczestnikow": len(glowny),
            "to_samo_top3": pierwsi(glowny) == pierwsi(list(wariant.values()))}
