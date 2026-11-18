"""Ocena surowych wyników uczestnika sędziami (tekstowym i plikowym).

    uv run pbench-ocen --uczestnik <id> --split dev|test --poziom tekst|plik [--procesy N]

Czyta `wyniki/surowe/<id>/<split>/<poziom>.jsonl` (zob. `pbench.uruchom`) i zapisuje
`wyniki/oceny/<id>/<split>/<poziom>.jsonl` – po jednej linii na dokument, w kolejności manifestu. Oceniane są dokumenty,
które mają wpis w wynikach surowych (dokumenty bez wpisu = przebieg niedokończony; polecenie ostrzega, ale ich nie
ocenia). Ocena równoległa (ProcessPool); OCR sędziego plikowego korzysta z pamięci podręcznej (`PBENCH_OCR_CACHE`).

Sędzia tekstowy: `ocen_tekst` z regułami z `metodyka/prerejestracja.md` (brak pliku = domyślne progi). Sędzia plikowy:
`ocen_plik` z leksykonem z `korpus/manifest.jsonl` (`leksykon_z_manifestu`, obowiązkowy).

Reguły dla dokumentów bez użytecznego wyniku (fail-closed – uczestnik nie zyskuje na awarii):

* **brak wyniku** (wpis `blad`: błąd uczestnika, timeout, pad procesu, offset poza tekstem, brak pliku wynikowego;
  a na poziomie plik także plik wynikowy nieczytelny lub pusty) → ocena „wszystko wycieka”: tekst – wykrycia puste;
  plik – ocena kopii oryginału (wyciekają wszystkie wartości, które sędzia w ogóle uznaje za wykrywalne);
  flaga `brak_wyniku: true`, w `blad` powód;
* **nieobsługiwany** (wpis `pominiety`: język/format spoza deklaracji) → ta sama ocena „wszystko wycieka”, flaga
  `nieobslugiwany: true`, `brak_wyniku: false`. Agregacja (zadanie późniejsze) wlicza go w miarę główną jako pełny wyciek,
  ale wyłącza z mianownika miar „w zakresie obsługiwanym”; od błędu odróżnia go właśnie ta flaga.

Rekord oceny (wspólne pola): `id, jezyk, typ, format, nieobslugiwany, brak_wyniku, blad, wycieki
[[wartosc_id, kategoria, miejsce, rodzaj],...], wartosci_ocenione, czas_s`. Poziom tekst dodatkowo: `fp_znaki,
fp_spany, pokrycie_znakowe, char_f2`. Poziom plik dodatkowo: `status_pliku` (OK|NIECZYTELNY|PUSTY), `niewykrywalne`,
`niejednoznaczne`, `bazowe` (linia bazowa sędziego – identyfikatory wartości odnajdywanych w ORYGINALE, wspólne dla uczestników;
mianownik P2 = `bazowe` ∪ identyfikatory `wycieki`, prerejestracja pkt 3.3), `integralnosc` (null przy braku wyniku),
`nadmiarowe` (P5: `{znaki, poza_gold}` – `pbench.sedzia.plik.nadmiarowe`; null przy braku wyniku), `format_wyj` (rozszerzenie
zapisanego pliku; może różnić się od oryginału – R38). Błąd samego sędziego (np. uszkodzony oryginał) trafia do
`blad_sedziego`, a polecenie kończy się kodem 1. Każdy rekord niesie `odcisk_sedziego` (`pbench.srodowisko.odcisk_sedziego`:
suma kodu sędziego i reguł wycieku, na poziomie plik także skrót `tessdata` i wersje Tesseracta, leptoniki i LibreOffice'a,
informacyjnie commit) – `pbench-agreguj` nie łączy rekordów o różnych odciskach.

Kontrola środowiska (poziom plik, `pbench.srodowisko`): przed oceną sprawdzane są sumy `vendor/tessdata` i wersje Tesseracta
(z leptoniką) i LibreOffice'a względem prerejestracji (`--reguly`); niezgodność – komunikat i kod 2, bez oceny.

Identyfikacja pośrednia (H5): dokument z niepustym polem manifestu `posrednie` ma w rekordzie (obu poziomów) pole `posrednie` –
po kombinacji `{id, rodzaj, przerwana: bool|null, widoczne: [id składników]}` (sędzia tekstowy: `ocen_tekst(posrednie=…)`,
plikowy: `ocen_plik(posrednie=…)`; przy braku wyniku i dokumencie nieobsługiwanym – ocena kopii oryginału, więc nic nie jest
przerwane; przy błędzie sędziego – `posrednie.nieprzerwane`: kombinacje nieprzerwane, w mianowniku, poza nieocenionymi na kopii
oryginału – te są `None` jak u pozostałych uczestników). Agregacja: odsetek kombinacji przerwanych `pbench.posrednie.agreguj`
(poza punktami, `metodyka/posrednie.md`). Poziom tekst wyłącza wtedy składniki spoza gold z `fp_znaki`/`fp_spany`.

Poziom encji (H6a, miara opisowa poza wzorami T/P): dokument, którego gold ma pole `encja` (warstwa trudna – ta sama osoba
w kilku zapisach: cyrylica, transliteracje, homoglify, inicjały, formy odmienione), ma w rekordzie (obu poziomów) pola
`wycieki_encji` (posortowane encje z co najmniej jednym wyciekłym zapisem – encja wycieka, gdy wycieka KTÓRYKOLWIEK jej zapis)
i `encje_ocenione` (liczba encji z co najmniej jedną ocenioną wartością); wartość bez `encja` jest encją samą dla siebie. Wzory
punktów liczą się jak dotąd (T3/P3 – odsetek DOKUMENTÓW z wyciekiem, więc poziom wartość/encja ich nie zmienia).
Miara „w deklarowanym zakresie” (J1, pomocnicza, poza punktami): kategorie gold, które uczestnik deklaruje w
`uczestnicy/<id>/etykiety.json` dla JĘZYKA DOKUMENTU (`wpis["jezyk"]`; J1-fix3, I2 – etykieta z listą kategorii działa w każdym
języku, ze słownikiem język → kategorie tylko w wymienionych; `zakres_deklarowany`, `kategorie_w_jezyku`). Rekord (obu
poziomów) ma wtedy pole `w_zakresie_deklarowanym`: `{wycieki, wartosci_ocenione}` tylko z wartości tych kategorii (wartość = kategoria pierwszego spanu,
jak w `wycieki`), a poziom tekst także `pokrycie_znakowe` i `char_f2` (`ocen_tekst(kategorie=…)`; FP – bez zmian, względem
całego gold). Brak `etykiety.json` – pola nie ma. Agregacja (`w_zakresie.csv`) liczy z niego te same wzory co miara główna.
`jezyk_uzyty` z wyniku surowego (język, z którym uczestnik przetwarzał dokument – `pbench.uruchom.jezyk_uzyty`) przechodzi do
rekordu oceny, gdy jest.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Iterable

from . import posrednie as _posrednie
from . import srodowisko
from .model import Wykrycie
from .sedzia.plik import leksykon_z_manifestu, ocen_plik
from .sedzia.sanity import wartosci_wpisu
from .sedzia.tekst import RegulyWycieku, gold_z_wpisu, ocen_tekst
from .uruchom import KORZEN, POZIOMY, wczytaj_manifest

REGULY_DOMYSLNE = KORZEN / "metodyka" / "prerejestracja.md"


def _wczytaj_surowe(sciezka: Path) -> dict[str, dict[str, Any]]:
    wynik: dict[str, dict[str, Any]] = {}
    if sciezka.exists():
        for linia in sciezka.read_text(encoding="utf-8").splitlines():
            try:
                obj = json.loads(linia)
            except json.JSONDecodeError:
                continue                                  # ucięty ostatni wiersz przerwanego przebiegu
            if isinstance(obj, dict) and "id" in obj:
                wynik[obj["id"]] = obj
    return wynik


def _jezyki_oficjalne(katalog_uczestnika: Path) -> list[str] | None:
    """Języki oficjalne z `surowe/<id>/wersje.json` (zapisuje je `pbench-uruchom`); brak pliku/pola → None (= wszystkie w zakresie)."""
    try:
        d = json.loads((katalog_uczestnika / "wersje.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    j = d.get("jezyki_oficjalne")
    return list(j) if isinstance(j, list) else None


#: Klucz deklaracji języka w `etykiety.json`: kategorie etykiety w każdym języku dokumentu.
KAZDY_JEZYK = "*"


def zakres_deklarowany(katalog_uczestnika: Path) -> dict[str, list[str]] | None:
    """Zakres deklarowany przez uczestnika (miara pomocnicza, J1; per język – J1-fix3, I2) z `etykiety.json`: język dokumentu
    (`KAZDY_JEZYK` – każdy) → kategorie gold. Wartość etykiety to lista kategorii (etykieta zwracana w każdym języku; lista pusta
    = brak odpowiednika w gold) albo słownik język → lista kategorii (etykieta zwracana tylko w tych językach – rozpoznawacz
    zarejestrowany dla jednego języka, model NER jednego języka; klucz `KAZDY_JEZYK` – w każdym). Brak albo zły plik → None
    (miara nieliczona)."""
    try:
        d = json.loads((katalog_uczestnika / "etykiety.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(d, dict):
        return None
    zakres: dict[str, set[str]] = {}
    for v in d.values():
        for jezyk, kategorie in (v.items() if isinstance(v, dict) else [(KAZDY_JEZYK, v)]):
            if isinstance(jezyk, str) and isinstance(kategorie, list):
                zakres.setdefault(jezyk, set()).update(k for k in kategorie if isinstance(k, str))
    return {j: sorted(k) for j, k in sorted(zakres.items())}


def kategorie_w_jezyku(zakres: dict[str, list[str]], jezyk: str | None) -> list[str]:
    """Kategorie zakresu (`zakres_deklarowany`) dla dokumentu w języku `jezyk`: deklarowane w każdym języku i w tym języku;
    `jezyk` None – suma po wszystkich językach (opis deklaracji, nie miara)."""
    if jezyk is None:
        return sorted({k for v in zakres.values() for k in v})
    return sorted({*zakres.get(KAZDY_JEZYK, ()), *zakres.get(jezyk, ())})


def kategorie_deklarowane(katalog_uczestnika: Path, jezyk: str | None = None) -> list[str] | None:
    """Kategorie gold w zakresie deklarowanym przez uczestnika dla dokumentu w języku `jezyk` (`kategorie_w_jezyku`; None – suma
    po językach); brak albo zły `etykiety.json` → None (miara nieliczona)."""
    zakres = zakres_deklarowany(katalog_uczestnika)
    return None if zakres is None else kategorie_w_jezyku(zakres, jezyk)


def w_zakresie(wycieki: Iterable, ocenione: Iterable[str], kategoria: dict[str, str], kategorie: Iterable[str]) -> dict[str, Any]:
    """Pole `w_zakresie_deklarowanym`: wycieki (krotki z kategorią na pozycji 1) i liczba ocenionych wartości tylko z `kategorie`
    (`kategoria`: identyfikator wartości -> kategoria)."""
    kat = set(kategorie)
    return {"wycieki": [list(w) for w in wycieki if w[1] in kat],
            "wartosci_ocenione": sum(1 for i in set(ocenione) if kategoria.get(i) in kat)}


def _flagi(rek: dict[str, Any]) -> dict[str, Any]:
    wynik = {"nieobslugiwany": "pominiety" in rek, "brak_wyniku": "blad" in rek, "blad": rek.get("blad")}
    if "jezyk_uzyty" in rek:
        wynik["jezyk_uzyty"] = rek["jezyk_uzyty"]
    return wynik


def encje_wartosci(wpis: dict[str, Any]) -> dict[str, str]:
    """Identyfikator wartości -> encja (`encja` z `gold_tekst`, `gold_plik` i `gold_obrazy` wpisu); pusty – dokument bez encji."""
    wpisy = [*wpis.get("gold_tekst", ()), *wpis.get("gold_plik", ()),
             *(w for o in wpis.get("gold_obrazy", ()) for w in o["wartosci"])]
    return {g.get("wartosc_id", g.get("id")): g["encja"] for g in wpisy if g.get("encja")}


def poziom_encji(encje: dict[str, str], wycieki: list, ocenione: Iterable[str]) -> dict[str, Any]:
    """Miara opisowa poziomu encji: `wycieki_encji` – encje z co najmniej jednym wyciekłym zapisem (krotki wycieków: id na
    pozycji 0), `encje_ocenione` – encje z oceniona wartością albo z wyciekiem; wartość bez encji = encja sama dla siebie."""
    def e(wid: str) -> str:
        return encje.get(wid, wid)
    wyc = {e(x[0]) for x in wycieki}
    return {"wycieki_encji": sorted(wyc), "encje_ocenione": len({e(i) for i in ocenione} | wyc)}


def _ocen_dokument(arg: tuple) -> dict[str, Any]:
    """Zadanie puli procesów: ocena jednego dokumentu (funkcja modułu – musi dać się zapisać przez pickle)."""
    # `kategorie` – zakres deklarowany w języku dokumentu (J1, `kategorie_w_jezyku`); None – bez tej miary
    poziom, wpis, rek, korpus, katalog_split, reguly_sciezka, manifest, oficjalne, kategorie = arg
    korpus, katalog_split = Path(korpus), Path(katalog_split)
    wynik = {"id": wpis["id"], "jezyk": wpis["jezyk"], "typ": wpis["typ"], "format": wpis["format"],
             **_flagi(rek), "czas_s": rek.get("czas_s"),
             "w_zakresie_oficjalnym": oficjalne is None or wpis["jezyk"] in oficjalne}
    try:
        if poziom == "tekst":
            wynik.update(_ocen_tekstowo(wpis, rek, korpus, Path(reguly_sciezka), kategorie))
        else:
            wynik.update(_ocen_plikowo(wpis, rek, korpus, katalog_split, Path(reguly_sciezka), Path(manifest), kategorie))
    except Exception as e:                                # błąd sędziego/korpusu, nie uczestnika
        wynik["blad_sedziego"] = f"{type(e).__name__}: {e}"[:1000]
        if wpis.get("posrednie"):                         # fail-closed: kombinacje nieprzerwane, w mianowniku
            wynik["posrednie"] = _posrednie.nieprzerwane(
                wpis["posrednie"], _posrednie_kopii(poziom, wpis, korpus, Path(reguly_sciezka), Path(manifest)))
    return wynik


def _posrednie_kopii(poziom: str, wpis: dict, korpus: Path, reguly_sciezka: Path, manifest: Path) -> list[dict] | None:
    """Kombinacje oceny KOPII ORYGINAŁU (bez wyniku uczestnika – ta sama dla wszystkich): wskazują kombinacje nieoceniane
    (`None`), które przy błędzie sędziego zostają poza mianownikiem. None – i ta ocena się nie udała (wtedy wszystkie
    w mianowniku)."""
    try:
        if poziom == "tekst":
            return _ocen_tekstowo(wpis, {"wykrycia": []}, korpus, reguly_sciezka).get("posrednie")
        return _ocen_plikowo(wpis, {"blad": "kopia oryginału"}, korpus, korpus, reguly_sciezka, manifest).get("posrednie")
    except Exception:
        return None


def _ocen_tekstowo(wpis: dict, rek: dict, korpus: Path, reguly_sciezka: Path,
                   kategorie: list[str] | None = None) -> dict[str, Any]:
    tekst = (korpus / wpis["plik_txt"]).read_bytes().decode("utf-8")
    wykrycia = [Wykrycie(s, e, et, sc) for s, e, et, sc in rek.get("wykrycia", [])]
    gold, reguly = gold_z_wpisu(wpis), RegulyWycieku.wczytaj(reguly_sciezka)
    o = ocen_tekst(gold, wykrycia, tekst, reguly, posrednie=wpis.get("posrednie") or None)
    wynik = {"wycieki": [list(w) for w in o.wycieki], "wartosci_ocenione": o.wartosci_ocenione,
             "fp_znaki": o.fp_znaki, "fp_spany": o.fp_spany, "pokrycie_znakowe": o.pokrycie_znakowe,
             "char_f2": o.char_f2}
    if kategorie is not None:                             # miara pomocnicza „w deklarowanym zakresie” (J1)
        oz = ocen_tekst(gold, wykrycia, tekst, reguly, kategorie=set(kategorie))
        wynik["w_zakresie_deklarowanym"] = {"wycieki": [list(w) for w in oz.wycieki],
                                            "wartosci_ocenione": oz.wartosci_ocenione,
                                            "pokrycie_znakowe": oz.pokrycie_znakowe, "char_f2": oz.char_f2}
    if encje := encje_wartosci(wpis):
        wynik.update(poziom_encji(encje, o.wycieki, o.ocenione_id))
    if o.posrednie is not None:
        wynik["posrednie"] = o.posrednie
    return wynik


def _ocen_plikowo(wpis: dict, rek: dict, korpus: Path, katalog_split: Path, reguly_sciezka: Path,
                  manifest: Path, kategorie: list[str] | None = None) -> dict[str, Any]:
    oryginal = korpus / wpis["plik"]
    reguly = RegulyWycieku.wczytaj(reguly_sciezka)
    leksykon = leksykon_z_manifestu(manifest)
    wartosci = wartosci_wpisu(wpis)
    posrednie = wpis.get("posrednie") or None
    status, blad = None, None
    brak = "plik_wyj" not in rek
    if not brak:
        o = ocen_plik(oryginal, katalog_split / rek["plik_wyj"], wartosci, reguly, leksykon=leksykon, posrednie=posrednie)
        status = o.status
        if status != "OK":
            brak, blad = True, f"plik wynikowy: {status}"
    if brak:                                              # fail-closed: oceniamy kopię oryginału (wszystko wycieka)
        o = ocen_plik(oryginal, oryginal, wartosci, reguly, leksykon=leksykon, posrednie=posrednie)
    wynik = {"status_pliku": status, "wycieki": [list(w) for w in o.wycieki], "wartosci_ocenione": o.wartosci_ocenione,
             "niewykrywalne": o.niewykrywalne, "niejednoznaczne": o.niejednoznaczne,
             "bazowe": list(o.bazowe),                     # linia bazowa: mianownik P2 (prerejestracja, pkt 3.3)
             "integralnosc": None if brak else o.integralnosc,
             "nadmiarowe": None if brak else o.nadmiarowe,  # P5 (pkt 3.2); bez wyniku – poza P5
             "format_wyj": rek.get("format_wyj")}          # R38: rozszerzenie pliku zapisanego przez narzędzie
    if encje := encje_wartosci(wpis):
        wynik.update(poziom_encji(encje, o.wycieki, o.bazowe))
    if kategorie is not None:                             # miara pomocnicza „w deklarowanym zakresie” (J1)
        wynik["w_zakresie_deklarowanym"] = w_zakresie(o.wycieki, [*o.bazowe, *(w[0] for w in o.wycieki)],
                                                      {w.id: w.kategoria for w in wartosci}, kategorie)
    if o.posrednie is not None:
        wynik["posrednie"] = o.posrednie
    if blad:
        wynik.update(brak_wyniku=True, blad=blad)
    return wynik


def ocen_uczestnika(*, uczestnik: str, split: str, poziom: str, korpus: Path, wyniki: Path,
                    reguly: Path = REGULY_DOMYSLNE, procesy: int | None = None,
                    uczestnicy: Path = KORZEN / "uczestnicy") -> dict[str, int]:
    """Ocenia wyniki surowe i zapisuje `wyniki/oceny/<uczestnik>/<split>/<poziom>.jsonl`.
    Zwraca liczniki `{"ocenione","bez_wyniku_surowego","blad_sedziego"}`."""
    korpus, wyniki = Path(korpus), Path(wyniki)
    katalog_split = wyniki / "surowe" / uczestnik / split
    surowe = _wczytaj_surowe(katalog_split / f"{poziom}.jsonl")
    wpisy = [w for w in wczytaj_manifest(korpus) if w["split"] == split]
    manifest = korpus / "manifest.jsonl"
    oficjalne = _jezyki_oficjalne(katalog_split.parent)
    zakres = zakres_deklarowany(Path(uczestnicy) / uczestnik)
    zadania = [(poziom, w, surowe[w["id"]], str(korpus), str(katalog_split), str(reguly), str(manifest), oficjalne,
                None if zakres is None else kategorie_w_jezyku(zakres, w["jezyk"]))
               for w in wpisy if w["id"] in surowe]
    liczniki = {"ocenione": len(zadania), "bez_wyniku_surowego": len(wpisy) - len(zadania), "blad_sedziego": 0}
    n = procesy or min(8, os.cpu_count() or 1)
    if n <= 1 or len(zadania) <= 1:
        oceny = [_ocen_dokument(z) for z in zadania]
    else:
        with ProcessPoolExecutor(max_workers=n) as pula:
            oceny = list(pula.map(_ocen_dokument, zadania, chunksize=4))
    liczniki["blad_sedziego"] = sum(1 for o in oceny if "blad_sedziego" in o)
    odcisk = srodowisko.odcisk_sedziego(poziom, Path(reguly))
    for o in oceny:
        o["odcisk_sedziego"] = odcisk
    cel = wyniki / "oceny" / uczestnik / split / f"{poziom}.jsonl"
    cel.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=cel.parent, suffix=".tmp", delete=False) as f:
        for o in oceny:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    os.replace(f.name, cel)
    return liczniki


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pbench-ocen", description="Ocenia surowe wyniki uczestnika sędziami benchmarku.")
    ap.add_argument("--uczestnik", required=True)
    ap.add_argument("--split", required=True, choices=("dev", "test"))
    ap.add_argument("--poziom", required=True, choices=POZIOMY)
    ap.add_argument("--procesy", type=int, help="liczba procesów oceny (domyślnie min(8, CPU))")
    ap.add_argument("--korpus", type=Path, default=KORZEN / "korpus")
    ap.add_argument("--wyniki", type=Path, default=KORZEN / "wyniki")
    ap.add_argument("--reguly", type=Path, default=REGULY_DOMYSLNE, help="plik z blokiem reguly_wycieku (prerejestracja)")
    ap.add_argument("--uczestnicy", type=Path, default=KORZEN / "uczestnicy",
                    help="katalog uczestników (etykiety.json – miara „w deklarowanym zakresie”)")
    a = ap.parse_args(argv)
    if a.poziom == "plik" and (problemy := srodowisko.kontrola_srodowiska(a.reguly)):
        print("pbench-ocen: środowisko oceny niezgodne z prerejestracją – ocena przerwana:\n  " + "\n  ".join(problemy),
              file=sys.stderr)
        return 2
    l = ocen_uczestnika(uczestnik=a.uczestnik, split=a.split, poziom=a.poziom, korpus=a.korpus, wyniki=a.wyniki,
                        reguly=a.reguly, procesy=a.procesy, uczestnicy=a.uczestnicy)
    print(f"{a.uczestnik}/{a.split}/{a.poziom}: ocenione {l['ocenione']}, bez wyniku surowego {l['bez_wyniku_surowego']}, "
          f"błędy sędziego {l['blad_sedziego']}")
    if l["bez_wyniku_surowego"]:
        print("UWAGA: przebieg niedokończony – część dokumentów splitu nie ma wyniku surowego i nie została oceniona.",
              file=sys.stderr)
    return 1 if l["blad_sedziego"] else 0


if __name__ == "__main__":
    sys.exit(main())
