"""Kontrola domen zarezerwowanych (analiza dodatkowa z `metodyka/kontrola-domen.md`, pkt 1–4).

    PYTHONPATH=<korzeń z pakietem pbench> python narzedzia/kontrola_domen.py --cel kontrola-domen --commit <sha>
        [--wyniki wyniki] [--korpus korpus] [--wyniki-trudne wyniki/trudne] [--korpus-trudne korpus-trudne]
        [--uczestnicy uczestnicy] [--czasy wyniki/czas-m1/czasy.jsonl] [--glowne wyniki/zbiorcze/glowne.csv]

Skrypt nie zmienia punktacji ani kodu agregacji: liczy na oceny sędziego (`pbench.agregacja.wektory`, `macierz_losowan`,
`agreguj`) i niczego z nich nie kopiuje. Metoda (zamrożona w metodyce przed pomiarem; skrypt napisany po pomiarze):

1. **Odsetek wycieku wg domeny.** Dla kategorii EMAIL i URL osobno dla wartości z domeną `example.com|org|net` („example”)
   i z domeną `*.test` („test”); wartości z inną domeną („inna”) są pomijane i tylko zliczane. Warstwa: trzon, split `test`;
   uczestnik rankingu tekst – wartości `gold_tekst`, rankingu pliki – wartości ocenianych plików (linia bazowa sędziego
   plikowego ∪ wycieki, jak w P2). Dokument fail-closed (każdy stan ≠ `ok`) ma wszystkie wartości wyciekłe. Przedział 95%:
   bootstrap po dokumentach, **ta sama** macierz losowań co w agregacji (`macierz_losowan`, ziarno `ZIARNO`, `POWTORZENIA`
   losowań, percentyle 2,5 i 97,5).
2. **Sygnał przewagi** (test zdefiniowany tu, przed policzeniem wyniku). Różnica `D = wyciek(test) − wyciek(example)` per
   uczestnik i kategoria, z przedziałem bootstrap. Odniesienie: mediana różnic D pozostałych uczestników rankingu tego
   samego poziomu (bez wariantów z aneksu i bez samego uczestnika), liczona w każdym losowaniu osobno – stąd jej przedział.
   `kierunek` = „większa”, gdy dolny kraniec przedziału D uczestnika leży powyżej górnego krańca przedziału mediany pozostałych
   (przedziały rozłączne), „mniejsza” – gdy górny kraniec leży poniżej dolnego, w pozostałych przypadkach „nierozróżnialna”.
   **Sygnał przewagi = kierunek „większa”.** Wynik jest podawany niezależnie od kierunku. Wymagane co najmniej
   `MIN_POZOSTALYCH` pozostałych uczestników z policzoną różnicą (inaczej brak oceny sygnału).
3. **Ranking bez wartości `example.*`.** `pbench.agregacja.agreguj` uruchomione na manifestach i ocenach bez wartości EMAIL/URL
   w domenach `example.*` (obie warstwy; wartości usunięte z gold, z wycieków i z linii bazowej; dokumenty zostają w próbie).
   Mianownik T5/P5 (znaki poza gold) liczony z pełnego gold – sędzia policzył nadmiarowe maskowanie względem pełnego gold.
   Wagi, bootstrap i czasy bez zmian; obok wynik tego samego przebiegu bez filtra (kontrola zgodności z rankingiem głównym).

Wyjście (`--cel`): `kontrola_domen.csv`, `ranking_bez_example.csv`, `meta.json` (commit skryptu, ziarno, liczba powtórzeń,
data, liczności; bez nazw hostów i ścieżek)."""
from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import json
import re
import sys
import warnings
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

import numpy as np

from pbench import agregacja as ag

KATEGORIE = ("EMAIL", "URL")
#: Klasy domen z pkt 1 metodyki; wszystko inne to „inna” (pomijana, zliczana).
KLASY = ("example", "test")
TLD_EXAMPLE = ("com", "org", "net")
#: Najmniejsza liczba pozostałych uczestników z policzoną różnicą, przy której oceniamy sygnał (pkt 2).
MIN_POZOSTALYCH = 2
OPIS_TESTU = ("Sygnał przewagi: przedział bootstrap 95% różnicy (wyciek .test − wyciek example.*) uczestnika leży w całości powyżej "
              "przedziału bootstrap 95% mediany różnic pozostałych uczestników rankingu (rozłączne przedziały).")


# ----------------------------------------------------------------------------- klasyfikacja domeny
def host(tekst: str, kategoria: str) -> str:
    """Nazwa hosta wartości EMAIL (po ostatnim „@”) albo URL (bez schematu, danych logowania, portu i ścieżki), małymi literami."""
    t = tekst.strip().lower()
    if kategoria == "EMAIL":
        h = t.rsplit("@", 1)[1] if "@" in t else ""
    else:
        t = re.sub(r"^[a-z][a-z0-9+.-]*://", "", t)
        h = re.split(r"[/?#]", t, maxsplit=1)[0].rsplit("@", 1)[-1]
    return re.sub(r":\d+$", "", h).strip(".,;:)>]\"'")


def klasa_domeny(tekst: str, kategoria: str) -> str:
    """`example` (example.com|org|net, także poddomeny), `test` (domena *.test) albo `inna`."""
    etykiety = host(tekst, kategoria).split(".")
    if len(etykiety) >= 2 and etykiety[-2] == "example" and etykiety[-1] in TLD_EXAMPLE:
        return "example"
    if len(etykiety) >= 2 and etykiety[-1] == "test":
        return "test"
    return "inna"


def klasy_wartosci(wpis: dict) -> dict[str, tuple[str, str]]:
    """Identyfikator wartości gold (tekst, plik i obrazy) -> (kategoria, klasa domeny); tylko EMAIL i URL."""
    wynik: dict[str, tuple[str, str]] = {}
    for g in wpis.get("gold_tekst", ()):
        if g["kategoria"] in KATEGORIE:
            wynik.setdefault(g["wartosc_id"], (g["kategoria"], klasa_domeny(g["tekst"], g["kategoria"])))
    for g in [*wpis.get("gold_plik", ()), *(w for o in wpis.get("gold_obrazy", ()) for w in o["wartosci"])]:
        if g["kategoria"] in KATEGORIE:
            wynik.setdefault(g["id"], (g["kategoria"], klasa_domeny(g["tekst"], g["kategoria"])))
    return wynik


# ----------------------------------------------------------------------------- zawężanie wpisów i rekordów ocen
class ZawezonaLista(list):
    """`gold_tekst` po zawężeniu; `pelny` – lista przed zawężeniem (mianownik T5 liczony z pełnego gold)."""
    pelny: list


def zawez_wpis(wpis: dict, zachowaj: Callable[[str], bool]) -> dict:
    """Kopia wpisu manifestu z wartościami gold, których identyfikator spełnia `zachowaj` (pozostałe pola bez zmian)."""
    gold = ZawezonaLista(g for g in wpis.get("gold_tekst", ()) if zachowaj(g["wartosc_id"]))
    gold.pelny = wpis.get("gold_tekst", [])
    kopia = {**wpis, "gold_tekst": gold,
             "gold_plik": [g for g in wpis.get("gold_plik", ()) if zachowaj(g["id"])],
             "gold_obrazy": [{**o, "wartosci": [w for w in o["wartosci"] if zachowaj(w["id"])]} for o in wpis.get("gold_obrazy", ())]}
    return kopia


def zawez_rekord(rek: dict, zachowaj: Callable[[str], bool]) -> dict:
    """Kopia rekordu oceny z wyciekami i linią bazową zawężonymi do `zachowaj` (pola, których `wektory` nie czyta, bez zmian)."""
    kopia = dict(rek)
    if "wycieki" in kopia:
        kopia["wycieki"] = [w for w in kopia["wycieki"] if zachowaj(w[0])]
    if isinstance(kopia.get("bazowe"), list):
        kopia["bazowe"] = [b for b in kopia["bazowe"] if zachowaj(b)]
    return kopia


# ----------------------------------------------------------------------------- pkt 1–2: odsetki wycieku wg domeny
def komorki(wpisy: list[dict], rekordy: dict[str, dict], poziom: str, wagi: dict, odmowy: list[str],
            klasy: dict[str, dict[str, tuple[str, str]]]) -> dict[tuple[str, str], tuple[np.ndarray, np.ndarray]] | None:
    """(kategoria, klasa) -> (liczba wartości, liczba wyciekłych) per dokument manifestu; klasa ∈ KLASY + `inna`.
    None – uczestnik z dokumentami bez linii bazowej sędziego plikowego (mianownik nieznany, jak P2)."""
    wynik = {}
    for kat in KATEGORIE:
        for klasa in (*KLASY, "inna"):
            def zachowaj_dok(dok: str, kat=kat, klasa=klasa):
                m = klasy.get(dok, {})
                return lambda i: m.get(i) == (kat, klasa)
            wp = [zawez_wpis(w, zachowaj_dok(w["id"])) for w in wpisy]
            rk = {d: zawez_rekord(r, zachowaj_dok(d)) for d, r in rekordy.items()}
            v = ag.wektory(wp, rk, poziom, wagi, odmowy)
            if v.brak_bazowych:
                return None
            wynik[(kat, klasa)] = (np.array([len(x) for x in v.wartosci], dtype=float),
                                   np.array([sum(1 for y in x if y[2]) for x in v.wartosci], dtype=float))
    return wynik


def _odsetek(W: np.ndarray, wyc: np.ndarray, mian: np.ndarray) -> np.ndarray:
    m = W @ mian
    return np.divide(W @ wyc, m, out=np.full(W.shape[0], np.nan), where=m > 0)


def analiza(wpisy: list[dict], rekordy: dict[tuple[str, str], dict[str, dict]], aneksy: dict[tuple[str, str], bool],
            odmowy: dict[str, list[str]], wagi: dict, klasy: dict, W: np.ndarray) -> list[dict]:
    """Wiersze `kontrola_domen.csv`: uczestnik × kategoria (docstring modułu, pkt 1–2)."""
    jeden = np.ones((1, len(wpisy)))
    dane: dict[tuple[str, str], Any] = {}
    for (poziom, u), rek in rekordy.items():
        k = komorki(wpisy, rek, poziom, wagi, odmowy.get(u, []), klasy)
        if k is None:
            continue
        dane[(poziom, u)] = {
            c: {"n": float((jeden @ m)[0]), "wyc": float((jeden @ w)[0]), "punkt": _odsetek(jeden, w, m)[0], "boot": _odsetek(W, w, m)}
            for c, (m, w) in k.items()}
    roznice: dict[tuple[str, str, str], tuple[float, np.ndarray]] = {}
    for (poziom, u), d in dane.items():
        for kat in KATEGORIE:
            roznice[(poziom, kat, u)] = (d[(kat, "test")]["punkt"] - d[(kat, "example")]["punkt"],
                                         d[(kat, "test")]["boot"] - d[(kat, "example")]["boot"])
    wiersze = []
    for (poziom, u), d in sorted(dane.items()):
        for kat in KATEGORIE:
            r: dict[str, Any] = {"ranking": "tekst" if poziom == "tekst" else "pliki", "uczestnik": u, "aneks": aneksy[(poziom, u)],
                                 "kategoria": kat, "inna_n": int(d[(kat, "inna")]["n"])}
            for klasa in KLASY:
                c = d[(kat, klasa)]
                r[f"{klasa}_n"], r[f"{klasa}_wyciek_n"] = int(c["n"]), int(c["wyc"])
                r[f"{klasa}_odsetek"] = None if np.isnan(c["punkt"]) else float(c["punkt"])
                r[f"{klasa}_ci_dol"], r[f"{klasa}_ci_gora"] = ag._przedzial(c["boot"])
            punkt, boot = roznice[(poziom, kat, u)]
            r["roznica"] = None if np.isnan(punkt) else float(punkt)
            r["roznica_ci_dol"], r["roznica_ci_gora"] = ag._przedzial(boot)
            inne = [(p, b) for (pz, k, x), (p, b) in roznice.items()
                    if pz == poziom and k == kat and x != u and not aneksy[(pz, x)] and not np.isnan(p)]
            r["pozostalych"] = len(inne)
            r["mediana_pozostalych"] = r["mediana_ci_dol"] = r["mediana_ci_gora"] = None
            r["kierunek"] = r["sygnal"] = None
            if inne:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    mediana_b = np.nanmedian(np.vstack([b for _, b in inne]), axis=0)
                r["mediana_pozostalych"] = float(np.median([p for p, _ in inne]))
                r["mediana_ci_dol"], r["mediana_ci_gora"] = ag._przedzial(mediana_b)
            if (len(inne) >= MIN_POZOSTALYCH and None not in (r["roznica_ci_dol"], r["mediana_ci_dol"])):
                r["kierunek"] = ("większa" if r["roznica_ci_dol"] > r["mediana_ci_gora"]
                                 else "mniejsza" if r["roznica_ci_gora"] < r["mediana_ci_dol"] else "nierozróżnialna")
                r["sygnal"] = "tak" if r["kierunek"] == "większa" else "nie"
            wiersze.append(r)
    return wiersze


# ----------------------------------------------------------------------------- pkt 3: ranking bez wartości example.*
@contextmanager
def bez_example(klasy: dict[str, dict[str, tuple[str, str]]]) -> Iterator[None]:
    """Podmienia wczytywanie manifestu i ocen w `pbench.agregacja`, tak aby `agreguj` liczyło bez wartości EMAIL/URL w domenach
    `example.*` (zawężenie wpisów, wycieków i linii bazowej; mianownik T5/P5 z pełnego gold)."""
    def zachowaj(dok: str) -> Callable[[str], bool]:
        m = klasy.get(dok, {})
        return lambda i: m.get(i, ("", ""))[1] != "example"

    manifest, jsonl, poza = ag.wczytaj_manifest, ag._jsonl, ag._poza_gold

    def manifest_z(korpus: Path) -> list[dict]:
        return [zawez_wpis(w, zachowaj(w["id"])) for w in manifest(korpus)]

    def jsonl_z(p: Path) -> dict[str, dict]:
        return {d: zawez_rekord(r, zachowaj(d)) for d, r in jsonl(p).items()}

    ag.wczytaj_manifest, ag._jsonl = manifest_z, jsonl_z
    ag._poza_gold = lambda tekst, gold: poza(tekst, getattr(gold, "pelny", gold))
    try:
        yield
    finally:
        ag.wczytaj_manifest, ag._jsonl, ag._poza_gold = manifest, jsonl, poza


def wiersze_rankingu(glowne: list[dict], glowne_pelne: list[dict]) -> list[dict]:
    """Wiersze `ranking_bez_example.csv`: wynik bez example.* z miejscem i sumą rankingu głównego (ten sam przebieg bez filtra)."""
    pelne = {(r["ranking"], r["uczestnik"]): r for r in glowne_pelne}
    testy = [t for _, ts in ag.RANKINGI.values() for t in ts]
    wynik = []
    for r in glowne:
        g = pelne[(r["ranking"], r["uczestnik"])]
        w = {k: r.get(k) for k in ("ranking", "uczestnik", "aneks", "miejsce", "remis_z", "suma", "suma_ci_dol", "suma_ci_gora")}
        for t in testy:
            if t in r:
                w[t], w[f"{t}_pkt"] = r[t], r.get(f"{t}_pkt")
        w.update(miejsce_glowne=g["miejsce"], suma_glowna=g["suma"], suma_glowna_ci_dol=g["suma_ci_dol"],
                 suma_glowna_ci_gora=g["suma_ci_gora"], remis_z_glowne=g["remis_z"])
        wynik.append(w)
    return wynik


def zgodnosc(glowne_pelne: list[dict], sciezka: Path | None) -> str:
    """Czy przebieg bez filtra odtwarza `glowne.csv` rankingu głównego (miejsca i sumy z dokładnością zapisu CSV)."""
    if sciezka is None:
        return "nie sprawdzono"
    with Path(sciezka).open(encoding="utf-8", newline="") as f:
        wzor = {(r["ranking"], r["uczestnik"]): r for r in csv.DictReader(f)}
    if set(wzor) != {(r["ranking"], r["uczestnik"]) for r in glowne_pelne}:
        return "nie"
    for r in glowne_pelne:
        w = wzor[(r["ranking"], r["uczestnik"])]
        if abs(float(w["suma"]) - r["suma"]) > 1e-4 or str(w["miejsce"] or "") != str(r["miejsce"] or ""):
            return "nie"
    return "tak"


# ----------------------------------------------------------------------------- zapis
def zapisz_csv(wiersze: list[dict], sciezka: Path) -> None:
    kolumny: list[str] = []
    for w in wiersze:
        kolumny += [k for k in w if k not in kolumny]
    with sciezka.open("w", encoding="utf-8", newline="") as f:
        pis = csv.DictWriter(f, fieldnames=kolumny)
        pis.writeheader()
        for w in wiersze:
            pis.writerow({k: ag._komorka(w.get(k)) for k in kolumny})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Kontrola domen zarezerwowanych (metodyka/kontrola-domen.md).")
    ap.add_argument("--wyniki", type=Path, default=ag.KORZEN / "wyniki")
    ap.add_argument("--korpus", type=Path, default=ag.KORZEN / "korpus")
    ap.add_argument("--wyniki-trudne", type=Path, default=ag.KORZEN / "wyniki" / "trudne")
    ap.add_argument("--korpus-trudne", type=Path, default=ag.KORZEN / "korpus-trudne")
    ap.add_argument("--uczestnicy", type=Path, default=ag.KORZEN / "uczestnicy")
    ap.add_argument("--czasy", type=Path, default=ag.KORZEN / "wyniki" / "czas-m1" / "czasy.jsonl")
    ap.add_argument("--glowne", type=Path, default=None, help="glowne.csv rankingu głównego (kontrola zgodności przebiegu bez filtra)")
    ap.add_argument("--cel", type=Path, required=True)
    ap.add_argument("--commit", required=True, help="commit skryptu (zapisywany w meta.json)")
    ap.add_argument("--powtorzenia", type=int, default=ag.POWTORZENIA)
    a = ap.parse_args(argv)
    split = "test"

    wagi = ag.wczytaj_wagi()
    wpisy = [w for w in ag.wczytaj_manifest(a.korpus) if w["split"] == split]
    wpisy_t = [w for w in ag.wczytaj_manifest(a.korpus_trudne) if w["split"] == split]
    klasy = {w["id"]: klasy_wartosci(w) for w in [*wpisy, *wpisy_t]}

    rekordy, aneksy, odmowy = {}, {}, {}
    for ranking, (poziom, _) in ag.RANKINGI.items():
        for u in ag._uczestnicy_poziomu(a.wyniki, split, poziom):
            rekordy[(poziom, u)] = ag._jsonl(a.wyniki / "oceny" / u / split / f"{poziom}.jsonl")
            aneksy[(poziom, u)] = ag.czy_aneks(a.uczestnicy / u)
            odmowy[u] = ag.komunikaty_odmowy(a.uczestnicy / u)
    W = ag.macierz_losowan(np.random.default_rng(ag.ZIARNO), len(wpisy), a.powtorzenia)
    kontrola = analiza(wpisy, rekordy, aneksy, odmowy, wagi, klasy, W)

    wspolne = dict(split=split, wyniki=a.wyniki, korpus=a.korpus, uczestnicy=a.uczestnicy, wyniki_trudne=a.wyniki_trudne,
                   korpus_trudne=a.korpus_trudne, czasy=a.czasy, powtorzenia=a.powtorzenia)
    pelne = ag.agreguj(**wspolne)["glowne"]
    with bez_example(klasy):
        bez = ag.agreguj(**wspolne)["glowne"]
    ranking = wiersze_rankingu(bez, pelne)

    a.cel.mkdir(parents=True, exist_ok=True)
    zapisz_csv(kontrola, a.cel / "kontrola_domen.csv")
    zapisz_csv(ranking, a.cel / "ranking_bez_example.csv")
    wykluczone = {nazwa: len({(w["id"], i) for w in ws for i, (_, kl) in klasy[w["id"]].items() if kl == "example"})
                  for nazwa, ws in (("trzon", wpisy), ("trudne", wpisy_t))}
    inna = {kat: len({(w["id"], i) for w in wpisy for i, (k, kl) in klasy[w["id"]].items() if k == kat and kl == "inna"})
            for kat in KATEGORIE}
    meta = {"skrypt_commit": a.commit, "skrypt_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "ziarno": ag.ZIARNO, "powtorzenia": a.powtorzenia, "data": datetime.date.today().isoformat(), "split": split,
            "warstwa_analizy": "trzon", "test_istotnosci": OPIS_TESTU, "min_pozostalych": MIN_POZOSTALYCH,
            "wykluczone_wartosci_example": wykluczone, "wartosci_inna_domena_trzon": inna,
            "przebieg_bez_filtra_zgodny_z_rankingiem_glownym": zgodnosc(pelne, a.glowne)}
    (a.cel / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Zapisano: {a.cel} (zgodność przebiegu bez filtra z rankingiem głównym: {meta['przebieg_bez_filtra_zgodny_z_rankingiem_glownym']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
