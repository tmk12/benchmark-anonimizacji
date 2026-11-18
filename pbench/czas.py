"""Pomiar szybkości T6/P7 (prerejestracja, pkt 1.2) – realizacja zamrożonego protokołu.

    uv run pbench-czas --uczestnik <id>[,<id>…] --poziom tekst|plik --korpus <trzon> --cel <katalog>
                       [--aplikacja-port N] [--aplikacja-dane <katalog>] [--rozgrzewka 1] [--powtorzenia 3]
                       [--watki 4] [--uczestnicy uczestnicy] [--sprawdz] [--limit N]
    uv run pbench-czas --podsumuj <cel>      # tabela: mediana s/stronę, awarie, start, szczyt pamięci

**Próbka** (`losuj_probe`): 60 dokumentów trzonu ze splitu `test` – PL 30, EN 8, DE 8, ES 7, FR 7. Procedura: w KAŻDYM języku
osobny, świeży `random.Random(20261102)` (ziarno zadane w prerejestracji „w każdym języku”, więc jeden obiekt na język, nie
wspólny – wynik języka nie zależy od liczby ani kolejności pozostałych); `rng.sample(sorted(id języka w splicie test), n)` – losowanie
bez zwracania z posortowanych identyfikatorów; w próbce id są posortowane w obrębie języka, języki w kolejności
PL, EN, DE, ES, FR. Lista trafia do `<cel>/proba.json` (przy wznowieniu musi zgadzać się z ponownym losowaniem – korpus nie mógł
się zmienić). T6 mierzy pliki `.txt`, P7 pliki oryginalne – ta sama próbka.

**Uczestnicy** (`uczestnicy/<id>`) startują jak w `pbench-uruchom` (klasa `Proces` i deklaracja z `uruchom.py`, to samo środowisko,
ale polecenie `uv run --frozen --no-sync --project …` – bez sprawdzania sieci; środowisko musi być wcześniej zbudowane
`uv sync --frozen --project uczestnicy/<id>`, `--sprawdz` to sprawdza:
`OMP_NUM_THREADS=4`, `HF_HUB_OFFLINE=1`, `HF_HOME=vendor/hf`, reszta środowiska przekazana dalej),
jedna instancja, jeden dokument naraz. `privatizer-tekst` i `privatizer-plik` NIE startują z tagu: wymagają `--aplikacja-port`
i mierzą zainstalowaną aplikację przez adapter `pbench.czas_aplikacja` (niepubliczny).

**Przebieg uczestnika** (zamrożony protokół): start procesu i linia `gotowy` (czas – `start.jsonl`, nie wchodzi do pomiarów); dla
zainstalowanej aplikacji adapter przed `gotowy` raz czyta ustawienia (`/api/bootstrap`) i ewentualnie ładuje model (`POST load`) –
poza mierzonym czasem, wynik (`load_potrzebny`) w `aplikacja-<id>.json`. Potem `--rozgrzewka` (1) PEŁNE przejście po CAŁEJ próbce
uczestnika (nieliczone), potem `--powtorzenia` (3) pełne przejścia mierzone po całej próbce, w tej samej kolejności id; *t_dok* =
mediana z 3 przejść. Pomiar cząstkowy (przejście, id) trafia od razu do `pomiary.jsonl` (plik roboczy); `czasy.jsonl` składa się po
komplecie (`zloz`, także `--zloz`). Wznawialność na poziomie (uczestnik, przejście, id): wznowienie po przerwie zaczyna od nowej
pełnej rozgrzewki po całej próbce i kontynuuje brakujące (przejście, id). Restart procesu po błędzie/timeoucie w trakcie przejścia
NIE powtarza rozgrzewki. Błąd/timeout/odmowa w DOWOLNYM z przejść daje dokumentowi *t_dok* = +∞ (protokół: „dokument z błędem ma
*t_dok* = +∞”; status pierwszego nieudanego przejścia, `pomiary_s` = `[]`) – mediana z dwóch dobrych pomiarów nie ratuje dokumentu.

Czas dokumentu = `time.perf_counter()` od wysłania zapytania do odebrania kompletnej odpowiedzi (`uruchom._obsluz`: poziom plik –
do odpowiedzi z `plik_wyj` i sprawdzenia, że plik istnieje). Status: `ok`; `blad`; `timeout` (`timeout_s` z `uczestnik.toml`);
`odmowa` (komunikat z `odmowy.json` uczestnika, ta sama reguła co `agregacja.stan_dokumentu`); `pominiety` (język/format poza deklaracją
– `uruchom.jezyk_uzyty`, jak `pbench-uruchom`). Błąd, timeout albo odmowa nie są ponawiane w pomiarze.

**Wyjście** (`--cel`): `pomiary.jsonl` (robocze: `uczestnik, poziom, przejscie, id, status, czas_s|blad`), `czasy.jsonl` (format `--czasy` agregacji: `uczestnik, poziom, id, znaki, pomiary_s, status` + `jezyk`, przy błędzie
`blad`), `proba.json`, `start.jsonl` (`uczestnik, poziom, start_s, przyczyna`), `rss.jsonl` (`szczyt_pamieci_mb` i `metoda_pamieci`: PSS drzewa
procesów (Linux) albo suma `phys_footprint` z `footprint` (macOS), zapas `ps`; próbkowanie co 1 s; dla aplikacji – drzewo procesu
nasłuchującego na porcie), `wersje.json` (linie `gotowy`), `aplikacja-<id>.json`
(opis aplikacji z adaptera), `srodowisko.json` (+ `srodowisko.jsonl` – po jednym wpisie na wywołanie), `stderr/` (logi uczestników)."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import platform
import random
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from . import agregacja, uruchom
from .uruchom import BladDeklaracji, BladProcesu, Deklaracja, Proces, Zapis


def _czas_aplikacja():
    """Adapter zainstalowanej aplikacji (`pbench.czas_aplikacja`): niepubliczny, importowany dopiero przy pomiarze aplikacji."""
    from . import czas_aplikacja
    return czas_aplikacja


KORZEN = uruchom.KORZEN
ZIARNO = 20261102
#: język -> liczba dokumentów próbki (kolejność = kolejność w `proba.json`)
ROZKLAD: dict[str, int] = {"pl": 30, "en": 8, "de": 8, "es": 7, "fr": 7}
SPLIT = "test"
WATKI = 4
ROZGRZEWKA = 1
POWTORZENIA = 3
OKRES_RSS_S = 1.0           # próbkowanie pamięci (PSS / footprint / `ps`); lista drzewa procesów odświeżana rzadziej
ODSWIEZANIE_DRZEWA_S = 5.0
#: uczestnicy mierzeni na zainstalowanej aplikacji (wymagają `--aplikacja-port`)
APLIKACJA = ("privatizer-tekst", "privatizer-plik")
STATUSY = ("ok", "blad", "timeout", "odmowa", "pominiety")
PROCEDURA = ("w każdym języku osobny random.Random(20261102).sample(sorted(id języka w splicie test), n); "
             "id posortowane w obrębie języka; kolejność języków pl, en, de, es, fr")


class BladProby(ValueError):
    """Korpus nie pozwala wylosować próbki (za mało dokumentów w języku) albo `proba.json` nie zgadza się z korpusem."""


# ----------------------------------------------------------------------------- próbka
def losuj_probe(manifest: list[dict[str, Any]], rozklad: dict[str, int] = ROZKLAD, ziarno: int = ZIARNO,
                split: str = SPLIT) -> list[dict[str, Any]]:
    """Próbka czasu: lista wpisów manifestu (kolejność: języki wg `rozklad`, w języku id rosnąco). Procedura w docstringu modułu."""
    wynik = []
    for jezyk, n in rozklad.items():
        wpisy = {w["id"]: w for w in manifest if w["split"] == split and w["jezyk"] == jezyk}
        if len(wpisy) < n:
            raise BladProby(f"język {jezyk}: w splicie {split} jest {len(wpisy)} dokumentów, potrzeba {n}")
        wybrane = random.Random(ziarno).sample(sorted(wpisy), n)
        wynik += [wpisy[i] for i in sorted(wybrane)]
    return wynik


def zapisz_probe(sciezka: Path, proba: list[dict[str, Any]]) -> None:
    """`proba.json`; istniejący plik musi wskazywać te same dokumenty (inaczej korpus albo ziarno się zmieniły → `BladProby`)."""
    ids = [w["id"] for w in proba]
    if sciezka.exists():
        try:
            stare = json.loads(sciezka.read_text(encoding="utf-8")).get("id")
        except (OSError, ValueError):
            stare = None
        if stare != ids:
            raise BladProby(f"{sciezka} wskazuje inną próbkę niż losowanie z podanego korpusu – wznawiaj na tym samym korpusie "
                            "albo wskaż pusty katalog --cel")
        return
    sciezka.parent.mkdir(parents=True, exist_ok=True)
    sciezka.write_text(json.dumps({
        "ziarno": ZIARNO, "split": SPLIT, "rozklad": ROZKLAD, "procedura": PROCEDURA, "liczba": len(ids), "id": ids,
        "jezyki": {w["id"]: w["jezyk"] for w in proba}}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ----------------------------------------------------------------------------- pamięć (PSS na Linuksie, phys_footprint na macOS)
def drzewo_pidow(korzenie: list[int]) -> list[int]:
    """PID-y `korzenie` i ich potomków wg `ps -A -o pid=,ppid=` (drogie – wołać rzadko); błąd `ps` → tylko korzenie."""
    try:
        wyj = subprocess.run(["ps", "-A", "-o", "pid=,ppid="], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return list(korzenie)
    dzieci: dict[int, list[int]] = {}
    zyje: set[int] = set()
    for linia in wyj.splitlines():
        c = linia.split()
        if len(c) == 2 and all(x.isdigit() for x in c):
            pid, ppid = map(int, c)
            zyje.add(pid)
            dzieci.setdefault(ppid, []).append(pid)
    widziane: set[int] = set()
    stos = [p for p in korzenie if p in zyje]
    while stos:
        p = stos.pop()
        if p not in widziane:
            widziane.add(p)
            stos += dzieci.get(p, [])
    return sorted(widziane)


def rss_wg_pidow(pidy: list[int]) -> dict[int, int]:
    """PID -> RSS (KiB) wg `ps -o rss= -o pid= -p <pid,…>` (tanie; zniknięte PID-y pomija); błąd → {}."""
    if not pidy:
        return {}
    try:
        wyj = subprocess.run(["ps", "-o", "rss=", "-o", "pid=", "-p", ",".join(map(str, pidy))], capture_output=True, text=True,
                             timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return {}
    wynik: dict[int, int] = {}
    for linia in wyj.splitlines():
        c = linia.split()
        if len(c) == 2 and all(x.isdigit() for x in c):
            wynik[int(c[1])] = int(c[0])
    return wynik


def rss_pidow_kb(pidy: list[int]) -> int:
    """Suma RSS (KiB) podanych procesów (`rss_wg_pidow`); NIE nadaje się do raportu pamięci drzewa – strony współdzielone
    (biblioteki, mmap modeli) liczą się wtedy wiele razy; raport używa `pamiec_pidow_kb`."""
    return sum(rss_wg_pidow(pidy).values())


def rss_drzewa_kb(korzenie: list[int]) -> int:
    """Suma RSS (KiB) drzewa procesów z `korzenie` (`drzewo_pidow` + `rss_pidow_kb`)."""
    return rss_pidow_kb(drzewo_pidow(korzenie))


# Metody pomiaru pamięci uczestnika (nazwa trafia do `rss.jsonl` i raportu)
METODA_PSS = "pss"                          # Linux: suma PSS procesów drzewa (/proc/<pid>/smaps_rollup) – strony współdzielone dzielone
METODA_FOOTPRINT = "phys_footprint"         # macOS: suma `footprint -p <pid>` (phys_footprint: strony brudne + skompresowane + IOKit)
METODA_PS = "rss_glowny+najwiekszy_potomek"  # zapas: `ps -o rss` procesu głównego uczestnika + osobno największego potomka
_JEDNOSTKI = {"B": 1, "KB": 1024, "MB": 1024 ** 2, "GB": 1024 ** 3}
_FOOTPRINT_RE = re.compile(r"\[(\d+)\].*?Footprint:\s*([\d.,]+)\s*([KMG]?B)", re.I)


def pss_pid_kb(pid: int) -> int | None:
    """PSS (KiB) procesu z `/proc/<pid>/smaps_rollup`; brak pliku/uprawnień → None."""
    try:
        for linia in Path(f"/proc/{pid}/smaps_rollup").read_text(encoding="utf-8").splitlines():
            if linia.startswith("Pss:"):
                return int(linia.split()[1])
    except (OSError, ValueError, IndexError):
        pass
    return None


def parsuj_footprint(wyj: str) -> dict[int, int]:
    """PID -> phys_footprint (KiB) z wyjścia `footprint -p …` (linie nagłówka `nazwa [pid]: 64-bit  Footprint: 12 MB (…)`)."""
    wynik: dict[int, int] = {}
    for linia in wyj.splitlines():
        m = _FOOTPRINT_RE.search(linia)
        if m:
            try:
                wynik[int(m.group(1))] = int(float(m.group(2).replace(",", ".")) * _JEDNOSTKI[m.group(3).upper()] / 1024)
            except (ValueError, KeyError):
                continue
    return wynik


def footprint_pidow_kb(pidy: list[int]) -> dict[int, int]:
    """PID -> phys_footprint (KiB) wg `footprint -p <pid> -p …` (macOS, bez sudo dla własnych procesów); błąd → {}."""
    if not pidy:
        return {}
    pol = ["footprint"]
    for p in pidy:
        pol += ["-p", str(p)]
    try:
        return parsuj_footprint(subprocess.run(pol, capture_output=True, text=True, timeout=30).stdout)
    except (OSError, subprocess.TimeoutExpired):
        return {}


def wybierz_metode_pamieci(pid_probny: int | None = None) -> str:
    """Najlepsza dostępna metoda: PSS (Linux) → phys_footprint (macOS, sprawdzone na własnym procesie) → zapas `ps`."""
    pid = pid_probny or os.getpid()
    if sys.platform.startswith("linux") and pss_pid_kb(pid) is not None:
        return METODA_PSS
    if sys.platform == "darwin" and shutil.which("footprint") and footprint_pidow_kb([pid]).get(pid):
        return METODA_FOOTPRINT
    return METODA_PS


def pamiec_pidow_kb(pidy: list[int], korzenie: list[int], metoda: str) -> int:
    """Pamięć (KiB) drzewa procesów `pidy` wg `metoda` bez podwójnego liczenia stron współdzielonych.

    PSS i phys_footprint liczone per proces i sumowane (strony współdzielone dzielone albo pomijane). Zapas (`ps`): RSS procesów
    głównych (`korzenie`) + osobno największy z pozostałych (potomków) – nie suma drzewa, bo ta liczy biblioteki wielokrotnie."""
    if not pidy:
        return 0
    if metoda == METODA_PSS:
        return sum(v for v in (pss_pid_kb(p) for p in pidy) if v)
    if metoda == METODA_FOOTPRINT:
        return sum(footprint_pidow_kb(pidy).values())
    rss = rss_wg_pidow(pidy)
    glowne = sum(v for p, v in rss.items() if p in set(korzenie))
    potomkowie = [v for p, v in rss.items() if p not in set(korzenie)]
    return glowne + (max(potomkowie) if potomkowie else 0)


def pid_nasluchu(port: int) -> int | None:
    """PID procesu nasłuchującego na 127.0.0.1:`port` (`lsof`); brak/błąd → None."""
    try:
        wyj = subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"], capture_output=True, text=True,
                             timeout=10).stdout.split()
    except (OSError, subprocess.TimeoutExpired):
        return None
    return int(wyj[0]) if wyj and wyj[0].isdigit() else None


class ProbnikRss:
    """Wątek próbkujący pamięć drzewa procesów (`pamiec_pidow_kb`) co `okres` s; `szczyt_kb` = maksimum z próbek."""

    def __init__(self, korzenie, okres: float = OKRES_RSS_S, metoda: str | None = None) -> None:
        self.korzenie = korzenie            # wywoływalne → lista PID-ów korzeni (proces może się zmieniać po restarcie)
        self.okres = okres
        self.metoda = metoda or wybierz_metode_pamieci()
        self.szczyt_kb = 0
        self.probek = 0
        self._stop = threading.Event()
        self._watek = threading.Thread(target=self._petla, daemon=True)

    def _petla(self) -> None:
        pidy: list[int] = []
        ostatnie_drzewo = -1e9
        while not self._stop.is_set():
            try:
                korzenie = [p for p in self.korzenie() if p]
                if time.monotonic() - ostatnie_drzewo >= ODSWIEZANIE_DRZEWA_S or not pidy:
                    pidy, ostatnie_drzewo = drzewo_pidow(korzenie), time.monotonic()
                kb = pamiec_pidow_kb(pidy, korzenie, self.metoda)
            except Exception:                                  # noqa: BLE001 – próbnik nie może przerwać pomiaru
                kb = 0
            if kb:
                self.szczyt_kb = max(self.szczyt_kb, kb)
                self.probek += 1
            self._stop.wait(self.okres)

    def start(self) -> "ProbnikRss":
        self._watek.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        self._watek.join(5)


# ----------------------------------------------------------------------------- proces uczestnika (także zainstalowana aplikacja)
class ProcesCzas(Proces):
    """`uruchom.Proces`; z `polecenie` (uczestnik-adapter aplikacji) startuje to polecenie zamiast `run.py` projektu."""

    def __init__(self, katalog: Path, env: dict[str, str], log_stderr: Path, polecenie: list[str] | None = None) -> None:
        super().__init__(katalog, env, log_stderr)
        self.polecenie = polecenie

    def start(self, timeout: float) -> tuple[dict[str, str], float]:
        if self.polecenie is None:
            return super().start(timeout)
        # jak Proces.start, tylko inna komenda (kod orkiestratora trafności nie jest zmieniany)
        import queue
        self.praca = tempfile.mkdtemp(prefix="pbench-uczestnik-")
        self.wyjscie = queue.Queue()
        opcje: dict[str, Any] = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if sys.platform == "win32" \
            else {"start_new_session": True}
        t0 = time.perf_counter()
        self.log_stderr.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_stderr, "ab") as log:
            self.proc = subprocess.Popen(self.polecenie, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log,
                                         cwd=self.praca, env=self.env, encoding="utf-8", errors="replace", bufsize=1, **opcje)
        with uruchom._ZYWE_BLOKADA:
            uruchom._ZYWE.add(self)
        threading.Thread(target=self._czytaj, args=(self.proc, self.wyjscie), daemon=True).start()
        try:
            odp = self._czekaj(timeout, "start")
        except BladProcesu:
            self.zamknij()
            raise
        if not odp.get("gotowy"):
            self.zamknij()
            raise BladProcesu("pierwsza linia wyjścia nie jest linią 'gotowy'")
        self.wersje = {str(k): str(v) for k, v in (odp.get("wersje") or {}).items()}
        return self.wersje, time.perf_counter() - t0


#: opcje `uv run` pomiaru: bez sieci i bez synchronizacji (środowisko budowane wcześniej: `uv sync --frozen --project …`)
UV_BEZ_SIECI = ["--frozen", "--no-sync"]


def polecenie_uczestnika(katalog: Path) -> list[str]:
    """Uczestnik OSS jako proces protokołu: `uv run --frozen --no-sync` w jego projekcie (start bez sprawdzania sieci)."""
    katalog = Path(katalog).resolve()
    return ["uv", "run", *UV_BEZ_SIECI, "--project", str(katalog), "python", str(katalog / "run.py")]


def katalog_srodowiska(katalog: Path) -> Path:
    """Katalog środowiska uv projektu uczestnika (`UV_PROJECT_ENVIRONMENT` albo `<projekt>/.venv`)."""
    zm = os.environ.get("UV_PROJECT_ENVIRONMENT")
    return (Path(zm) if zm else Path(katalog).resolve() / ".venv")


def srodowisko_zsynchronizowane(katalog: Path) -> bool:
    """Czy środowisko uv uczestnika istnieje (`uv run --no-sync` bez niego startuje w pustym venv i uczestnik pada na imporcie)."""
    return (katalog_srodowiska(katalog) / "pyvenv.cfg").is_file()


def polecenie_aplikacji(katalog: Path, poziom: str, port: int, dane: Path | None, info: Path,
                        rejestr: Path | None = None) -> list[str]:
    """Adapter zainstalowanej aplikacji jako uczestnik protokołu, w środowisku uv projektu `katalog` (źródła tagu)."""
    pol = ["uv", "run", *UV_BEZ_SIECI, "--project", str(Path(katalog).resolve()), "python", "-P", str(Path(_czas_aplikacja().__file__).resolve()),
           "--poziom", poziom, "--port", str(port), "--info", str(info)]
    if dane:
        pol += ["--dane", str(dane)]
    if rejestr:
        pol += ["--rejestr", str(rejestr)]
    return pol


# ----------------------------------------------------------------------------- pomiary.jsonl (robocze) i czasy.jsonl (wynik)
def _czytaj_jsonl(sciezka: Path) -> list[dict]:
    """Wiersze JSONL (ucięty/uszkodzony pomijany); plik bez końcowej nowej linii jest do niej wyrównywany."""
    if not sciezka.exists():
        return []
    dane = sciezka.read_bytes()
    if dane and not dane.endswith(b"\n"):
        with open(sciezka, "ab") as f:
            f.write(b"\n")
    wynik = []
    for linia in dane.decode("utf-8", errors="replace").splitlines():
        try:
            d = json.loads(linia)
        except ValueError:
            continue
        if isinstance(d, dict):
            wynik.append(d)
    return wynik


def wczytaj_pomiary(sciezka: Path, uczestnik: str, poziom: str) -> dict[tuple[int, str], dict]:
    """(przejście, id) -> ostatni wpis roboczy `pomiary.jsonl` `{uczestnik, poziom, przejscie, id, status, czas_s?, blad?}`."""
    wynik = {}
    for d in _czytaj_jsonl(sciezka):
        if d.get("uczestnik") == uczestnik and d.get("poziom") == poziom and d.get("status") in STATUSY \
                and isinstance(d.get("przejscie"), int) and "id" in d:
            wynik[(d["przejscie"], d["id"])] = d
    return wynik


def status_bledu(blad: str, odmowy: list[str]) -> str:
    """`odmowa` / `timeout` / `blad` – ta sama kolejność reguł co `agregacja.stan_dokumentu`."""
    if any(k in blad for k in odmowy):
        return "odmowa"
    if "timeout" in blad.lower():
        return "timeout"
    return "blad"


def liczba_znakow(korpus: Path, wpis: dict[str, Any]) -> int:
    """Długość `.txt` dokumentu w znakach (jak `agregacja`/`uruchom._zadanie`: bajty → UTF-8, bez zmiany końców linii)."""
    return len((korpus / wpis["plik_txt"]).read_bytes().decode("utf-8"))


def pominiecie(w: dict[str, Any], decl: Deklaracja, poziom: str) -> str | None:
    """`jezyk` / `format` – dokument poza deklaracją uczestnika (jak `pbench-uruchom`); None – do pomiaru."""
    if uruchom.jezyk_uzyty(w["jezyk"], decl.jezyki) is None:
        return "jezyk"
    if poziom == "plik" and w["format"] not in decl.formaty:
        return "format"
    return None


def zloz(*, uczestnik: str, poziom: str, proba: list[dict[str, Any]], korpus: Path, cel: Path, uczestnicy: Path,
         przejscia: int = POWTORZENIA) -> dict[str, int]:
    """Składa wpisy `czasy.jsonl` uczestnika/poziomu z `pomiary.jsonl` (reszta pliku zostaje; zapis atomowy).

    Dokument z kompletem `przejscia` przejść: wszystkie `ok` → `ok` i `pomiary_s` w kolejności przejść; inaczej status pierwszego
    nieudanego przejścia (`blad`/`timeout`/`odmowa`) i `pomiary_s` = `[]` (+∞ w agregacji). Dokument spoza deklaracji – `pominiety`.
    Dokument z niepełnym kompletem (przerwany pomiar) jest pomijany i liczony w `niepelne` (agregacja liczyłaby wtedy mniejszą próbę,
    nie +∞, więc `--zloz` kończy się wtedy błędem). Zwraca liczniki jak `zmierz`."""
    decl = uruchom.wczytaj_deklaracje(Path(uczestnicy) / uczestnik)
    pom = wczytaj_pomiary(Path(cel) / "pomiary.jsonl", uczestnik, poziom)
    nowe, licz = [], {**dict.fromkeys(STATUSY, 0), "niepelne": 0}
    for w in proba:
        baza = {"uczestnik": uczestnik, "poziom": poziom, "id": w["id"], "jezyk": w["jezyk"],
                "znaki": liczba_znakow(korpus, w)}
        powod = pominiecie(w, decl, poziom)
        if powod:
            nowe.append({**baza, "pomiary_s": [], "status": "pominiety", "powod": powod})
            licz["pominiety"] += 1
            continue
        wpisy = [pom.get((k, w["id"])) for k in range(1, przejscia + 1)]
        if any(x is None for x in wpisy):
            licz["niepelne"] += 1
            continue
        zle = next((x for x in wpisy if x["status"] != "ok"), None)
        if zle is None:
            nowe.append({**baza, "pomiary_s": [round(x["czas_s"], 6) for x in wpisy], "status": "ok"})
            licz["ok"] += 1
        else:
            nowe.append({**baza, "pomiary_s": [], "status": zle["status"], "blad": str(zle.get("blad", ""))[:300]})
            licz[zle["status"]] += 1
    sciezka = Path(cel) / "czasy.jsonl"
    inne = [d for d in _czytaj_jsonl(sciezka) if not (d.get("uczestnik") == uczestnik and d.get("poziom") == poziom)]
    tmp = sciezka.with_suffix(".jsonl.tmp")
    tmp.write_text("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in inne + nowe), encoding="utf-8")
    os.replace(tmp, sciezka)
    return licz


# ----------------------------------------------------------------------------- pomiar jednego uczestnika
def zmierz(*, uczestnik: str, poziom: str, proba: list[dict[str, Any]], korpus: Path, cel: Path, uczestnicy: Path,
           watki: int = WATKI, rozgrzewka: int = ROZGRZEWKA, powtorzenia: int = POWTORZENIA, timeout: float | None = None,
           aplikacja_port: int | None = None, aplikacja_dane: Path | None = None,
           okres_rss: float = OKRES_RSS_S) -> dict[str, int]:
    """Pomiar jednego uczestnika na jednym poziomie. Zwraca liczniki `{ok, blad, timeout, odmowa, pominiety, wczesniej, nieprzetworzone}`
    (`wczesniej` – wpisy (przejście, id) już w `pomiary.jsonl`; `nieprzetworzone` – brakujące; po komplecie składa `czasy.jsonl`)."""
    katalog = Path(uczestnicy) / uczestnik
    decl = uruchom.wczytaj_deklaracje(katalog)
    if poziom not in decl.poziomy:
        raise BladDeklaracji(f"uczestnik {uczestnik} nie deklaruje poziomu '{poziom}' (deklaruje: {list(decl.poziomy)})")
    if uczestnik in APLIKACJA and aplikacja_port is None:
        raise BladDeklaracji(f"uczestnik {uczestnik} jest mierzony na zainstalowanej aplikacji – podaj --aplikacja-port")
    timeout = timeout or decl.timeout_s
    korpus, cel = Path(korpus), Path(cel)
    odmowy = agregacja.komunikaty_odmowy(katalog)
    cel.mkdir(parents=True, exist_ok=True)
    sciezka_pomiarow = cel / "pomiary.jsonl"
    zrobione = wczytaj_pomiary(sciezka_pomiarow, uczestnik, poziom)
    docs = [w for w in proba if pominiecie(w, decl, poziom) is None]
    brakuje = [(k, w) for k in range(1, powtorzenia + 1) for w in docs if (k, w["id"]) not in zrobione]
    licz = dict.fromkeys(("ok", "blad", "timeout", "odmowa", "pominiety", "wczesniej", "nieprzetworzone"), 0)
    licz["wczesniej"] = len(docs) * powtorzenia - len(brakuje)
    licz["nieprzetworzone"] = len(brakuje)
    if not brakuje:
        licz.update(zloz(uczestnik=uczestnik, poziom=poziom, proba=proba, korpus=korpus, cel=cel, uczestnicy=uczestnicy,
                         przejscia=powtorzenia))
        return licz

    zapis = Zapis(sciezka_pomiarow)
    starty = Zapis(cel / "start.jsonl")
    pliki = cel / "praca" / uczestnik / "pliki"
    if poziom == "plik":
        pliki.mkdir(parents=True, exist_ok=True)
    env = uruchom.zbuduj_srodowisko(watki, offline=True)
    info = cel / f"aplikacja-{uczestnik}.json"
    polecenie = (polecenie_aplikacji(katalog, poziom, aplikacja_port, aplikacja_dane, info, cel / f"aplikacja-{uczestnik}-rejestr.jsonl")
                 if uczestnik in APLIKACJA else polecenie_uczestnika(katalog))
    proces = ProcesCzas(katalog, env, cel / "stderr" / f"{uczestnik}-{poziom}.log", polecenie)
    pid_app = [None]

    def korzenie() -> list[int]:
        if uczestnik in APLIKACJA:
            if pid_app[0] is None:
                pid_app[0] = pid_nasluchu(aplikacja_port)
            return [pid_app[0]] if pid_app[0] else []
        return [proces.proc.pid] if proces.proc is not None and proces.proc.poll() is None else []

    probnik = ProbnikRss(korzenie, okres_rss).start()
    przyczyna = ["start"]
    porazki = [0]

    def zapewnij_proces() -> bool:
        """Startuje proces, gdy nie żyje (do `MAKS_PORAZEK_STARTU` prób z rzędu); False – nie da się."""
        while proces.proc is None:
            try:
                wersje, start_s = proces.start(decl.start_timeout_s)
            except BladProcesu as e:
                porazki[0] += 1
                print(f"[{uczestnik}] start nieudany ({porazki[0]}/{uruchom.MAKS_PORAZEK_STARTU}): {e}", file=sys.stderr)
                if porazki[0] >= uruchom.MAKS_PORAZEK_STARTU:
                    return False
                continue
            porazki[0] = 0
            starty.dodaj({"uczestnik": uczestnik, "poziom": poziom, "start_s": round(start_s, 3), "przyczyna": przyczyna[0]})
            przyczyna[0] = "restart"
            wpis_wersji(cel, uczestnik, poziom, wersje)
            pid_app[0] = None
        return True

    def jedno(w) -> tuple[dict, bool]:
        uzyty = uruchom.jezyk_uzyty(w["jezyk"], decl.jezyki)
        zap = uruchom._zadanie(w, poziom, korpus, pliki, uzyty)
        if poziom == "plik":
            for stary in Path(zap["plik_wyj"]).parent.glob(Path(zap["plik_wyj"]).stem + ".*"):
                stary.unlink(missing_ok=True)
        rek, zamknac = uruchom._obsluz(proces, zap, poziom, timeout)
        if poziom == "plik":
            for stary in Path(zap["plik_wyj"]).parent.glob(Path(zap["plik_wyj"]).stem + ".*"):
                stary.unlink(missing_ok=True)          # pomiar nie trzyma wyników; ocena trafności to osobny przebieg
        return rek, zamknac

    kompletne = False
    try:
        # rozgrzewka: pełne przejście(a) po CAŁEJ próbce uczestnika (także przy wznowieniu); wyniki odrzucane,
        # błąd rozgrzewki tylko restartuje proces
        for _ in range(rozgrzewka):
            for w in docs:
                if not zapewnij_proces():
                    return licz
                rek, zamknac = jedno(w)
                if zamknac or "blad" in rek:
                    proces.zamknij()
        # pomiar: `powtorzenia` pełnych przejść po próbce, w tej samej kolejności id; restart po błędzie nie powtarza rozgrzewki
        for k in range(1, powtorzenia + 1):
            for w in docs:
                if (k, w["id"]) in zrobione:
                    continue
                if not zapewnij_proces():
                    return licz
                rek, zamknac = jedno(w)
                wpis = {"uczestnik": uczestnik, "poziom": poziom, "przejscie": k, "id": w["id"]}
                if "blad" in rek:
                    st = status_bledu(rek["blad"], odmowy)
                    zapis.dodaj({**wpis, "status": st, "blad": rek["blad"][:300]})
                    licz[st] += 1
                    proces.zamknij()
                else:
                    zapis.dodaj({**wpis, "status": "ok", "czas_s": rek["czas_s"]})
                    if zamknac:
                        proces.zamknij()
                licz["nieprzetworzone"] -= 1
        kompletne = True
    finally:
        probnik.stop()
        proces.zamknij()
        with open(cel / "rss.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"uczestnik": uczestnik, "poziom": poziom, "szczyt_pamieci_mb": round(probnik.szczyt_kb / 1024, 1),
                                "metoda_pamieci": probnik.metoda, "probek": probnik.probek, "okres_s": okres_rss,
                                "opis": "pamięć drzewa procesów co okres_s, drzewo odświeżane co 5 s (aplikacja: proces nasłuchujący na porcie)",
                                "zapisano": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}) + "\n")
        zapis.zamknij()
        starty.zamknij()
        if poziom == "plik":
            shutil.rmtree(cel / "praca" / uczestnik, ignore_errors=True)
    if kompletne:
        licz.update(zloz(uczestnik=uczestnik, poziom=poziom, proba=proba, korpus=korpus, cel=cel, uczestnicy=uczestnicy,
                         przejscia=powtorzenia))
    return licz


def wpis_wersji(cel: Path, uczestnik: str, poziom: str, wersje: dict[str, str]) -> None:
    """`wersje.json`: `{"<uczestnik>/<poziom>": {"wersje": …, "zapisano": …}}` (ostatni start)."""
    p = cel / "wersje.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    d[f"{uczestnik}/{poziom}"] = {"wersje": wersje, "zapisano": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ----------------------------------------------------------------------------- środowisko pomiaru
def _polecenie(*args: str) -> str | None:
    try:
        r = subprocess.run(list(args), capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def srodowisko() -> dict[str, Any]:
    """Opis maszyny i warunków pomiaru (macOS: `sysctl`, `sw_vers`, `pmset`; na innych systemach pola z `None`)."""
    pmset_batt = _polecenie("pmset", "-g", "batt")
    pmset = _polecenie("pmset", "-g")
    niskie, domniemane = None, None
    if pmset is not None:
        m = re.search(r"^\s*lowpowermode\s+(\d)", pmset, re.M)
        niskie = int(m.group(1)) if m else 0
        domniemane = m is None          # brak linii `lowpowermode` w `pmset -g` = tryb wyłączony (wartość domniemana, nie odczytana)
    zasilacz = None
    if pmset_batt:
        zasilacz = "AC Power" in pmset_batt.splitlines()[0]
    wersja_uv = _polecenie("uv", "--version")
    commit = _polecenie("git", "-C", str(KORZEN), "rev-parse", "HEAD")
    return {
        "zapisano": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "host": platform.node(), "system": platform.platform(), "python": platform.python_version(),
        "hw_model": _polecenie("sysctl", "-n", "hw.model"),
        "cpu": _polecenie("sysctl", "-n", "machdep.cpu.brand_string") or platform.processor() or None,
        "rdzenie_logiczne": os.cpu_count(),
        "rdzenie_wydajne": _polecenie("sysctl", "-n", "hw.perflevel0.logicalcpu"),
        "rdzenie_energooszczedne": _polecenie("sysctl", "-n", "hw.perflevel1.logicalcpu"),
        "ram_bajty": _polecenie("sysctl", "-n", "hw.memsize"),
        "macos": _polecenie("sw_vers", "-productVersion"),
        "pmset_batt": pmset_batt, "na_zasilaczu": zasilacz, "tryb_niskiego_zuzycia": niskie, "lowpowermode_domniemane": domniemane,
        "uv": wersja_uv, "commit_harnessu": commit, "ziarno": ZIARNO, "obciazenie_1min": os.getloadavg()[0]
        if hasattr(os, "getloadavg") else None,
    }


def naruszenia_warunkow(sr: dict[str, Any]) -> list[str]:
    """Warunki z prerejestracji znane z `srodowisko()`: zasilacz i tryb niskiego zużycia (brak danych – brak naruszenia)."""
    n = []
    if sr.get("na_zasilaczu") is False:
        n.append("maszyna nie jest na zasilaczu (pmset -g batt)")
    if sr.get("tryb_niskiego_zuzycia") == 1:
        n.append("włączony tryb niskiego zużycia energii (pmset -g: lowpowermode 1)")
    return n


def zapisz_srodowisko(cel: Path, sr: dict[str, Any], argv: list[str]) -> None:
    cel.mkdir(parents=True, exist_ok=True)
    wpis = {**sr, "argumenty": argv}
    (cel / "srodowisko.json").write_text(json.dumps(wpis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with open(cel / "srodowisko.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(wpis, ensure_ascii=False) + "\n")


# ----------------------------------------------------------------------------- kontrola sucha
def sprawdz(*, uczestnicy_ids: list[str], poziom: str, proba: list[dict], korpus: Path, cel: Path, uczestnicy: Path,
            aplikacja_port: int | None, aplikacja_dane: Path | None) -> list[str]:
    """Sucha kontrola bez pomiaru: wypisuje stan i zwraca listę problemów (pusta = gotowe do pomiaru)."""
    problemy: list[str] = []
    por = {j: sum(1 for w in proba if w["jezyk"] == j) for j in ROZKLAD}
    print(f"próbka: {len(proba)} dokumentów {por}, ziarno {ZIARNO}")
    for u in uczestnicy_ids:
        try:
            decl = uruchom.wczytaj_deklaracje(Path(uczestnicy) / u)
        except BladDeklaracji as e:
            problemy.append(f"{u}: {e}")
            continue
        if poziom not in decl.poziomy:
            problemy.append(f"{u}: nie deklaruje poziomu {poziom}")
            continue
        nieobsl = sum(1 for w in proba if uruchom.jezyk_uzyty(w["jezyk"], decl.jezyki) is None
                      or (poziom == "plik" and w["format"] not in decl.formaty))
        gotowe = len(wczytaj_pomiary(Path(cel) / "pomiary.jsonl", u, poziom))
        print(f"{u}/{poziom}: timeout {decl.timeout_s:g} s, pominięte {nieobsl}, zapisane pomiary (przejście, id): {gotowe}")
        if not srodowisko_zsynchronizowane(Path(uczestnicy) / u):
            problemy.append(f"{u}: brak zsynchronizowanego środowiska uv ({katalog_srodowiska(Path(uczestnicy) / u)}) – "
                            f"uruchom: uv sync --frozen --project {Path(uczestnicy) / u}")
        if u in APLIKACJA:
            if aplikacja_port is None:
                problemy.append(f"{u}: brak --aplikacja-port")
                continue
            czas_aplikacja = _czas_aplikacja()
            try:
                wersja = czas_aplikacja.ping(aplikacja_port).get("version")
                czas_aplikacja.wczytaj_sesje(aplikacja_dane or czas_aplikacja.katalog_danych_aplikacji(), aplikacja_port)
            except czas_aplikacja.BladAplikacji as e:
                problemy.append(f"{u}: {e}")
                continue
            print(f"  aplikacja na porcie {aplikacja_port}: wersja {wersja}, sesja.json czytelny")
            if wersja != czas_aplikacja.WERSJA_OCZEKIWANA:
                problemy.append(f"{u}: wersja aplikacji {wersja!r}, prerejestracja wymaga {czas_aplikacja.WERSJA_OCZEKIWANA!r}")
    if shutil.which("uv") is None:
        problemy.append("brak polecenia uv w PATH")
    sr = srodowisko()
    print(f"maszyna: {sr['hw_model'] or sr['host']}, zasilacz {sr['na_zasilaczu']}, niskie zużycie {sr['tryb_niskiego_zuzycia']}")
    problemy += naruszenia_warunkow(sr)
    return problemy


# ----------------------------------------------------------------------------- podsumowanie (s/stronę, awarie, start, pamięć)
def _mediana_lub_none(x: list[float]) -> float | None:
    return statistics.median(x) if x else None


def podsumuj(cel: Path) -> list[dict[str, Any]]:
    """Wiersze tabeli per (uczestnik, poziom) z `czasy.jsonl`, `start.jsonl`, `rss.jsonl` katalogu `cel`.

    s/stronę dokładnie jak agregacja: `agregacja.wczytaj_czasy` (strona = max(1, znaki/1800), awaria = +∞) i `agregacja.wynik_czasu`
    (mediana po próbie; połowa awarii = +∞)."""
    cel = Path(cel)
    pomiary = agregacja.wczytaj_czasy(cel / "czasy.jsonl", {})
    starty: dict[tuple[str, str], list[float]] = {}
    for d in _czytaj_jsonl(cel / "start.jsonl"):
        if d.get("przyczyna") == "start":
            starty.setdefault((d.get("uczestnik"), d.get("poziom")), []).append(float(d["start_s"]))
    pamiec: dict[tuple[str, str], dict[str, Any]] = {}
    for d in _czytaj_jsonl(cel / "rss.jsonl"):
        k = (d.get("uczestnik"), d.get("poziom"))
        mb = d.get("szczyt_pamieci_mb")
        if mb is not None and (k not in pamiec or mb >= pamiec[k]["mb"]):
            pamiec[k] = {"mb": mb, "metoda": d.get("metoda_pamieci")}
    wiersze = []
    for (u, poziom), s_na_strone in sorted(pomiary.items()):
        t, wynik = agregacja.wynik_czasu(s_na_strone)
        pam = pamiec.get((u, poziom))
        wiersze.append({"uczestnik": u, "poziom": poziom, "dokumenty": len(s_na_strone),
                        "awarie": sum(1 for x in s_na_strone if math.isinf(x)), "mediana_s_na_strone": t, "wynik": wynik,
                        "start_s": _mediana_lub_none(starty.get((u, poziom), [])),
                        "szczyt_pamieci_mb": pam["mb"] if pam else None, "metoda_pamieci": pam["metoda"] if pam else None})
    return wiersze


def tabela_podsumowania(wiersze: list[dict[str, Any]]) -> str:
    def liczba(x: float | None, miejsca: int) -> str:
        return "—" if x is None else ("∞" if math.isinf(x) else f"{x:.{miejsca}f}")
    linie = ["| uczestnik | poziom | dok. | mediana s/stronę | awarie | start [s] | szczyt pamięci [MB] | metoda pamięci |",
             "|---|---|---|---|---|---|---|---|"]
    for w in wiersze:
        linie.append(f"| {w['uczestnik']} | {w['poziom']} | {w['dokumenty']} | {liczba(w['mediana_s_na_strone'], 4)} | {w['awarie']} | "
                     f"{liczba(w['start_s'], 1)} | {liczba(w['szczyt_pamieci_mb'], 0)} | {w['metoda_pamieci'] or '—'} |")
    return "\n".join(linie)


def proba_niepelna_w(cel: Path) -> bool:
    """Czy `srodowisko.json` katalogu `cel` oznacza przebieg próbny (`--limit`)."""
    try:
        return bool(json.loads((Path(cel) / "srodowisko.json").read_text(encoding="utf-8")).get("proba_niepelna"))
    except (OSError, ValueError, AttributeError):
        return False


# ----------------------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pbench-czas", description="Pomiar szybkości T6/P7 (prerejestracja, pkt 1.2).")
    ap.add_argument("--uczestnik", help="id uczestnika (katalog w uczestnicy/) lub lista po przecinku")
    ap.add_argument("--poziom", choices=uruchom.POZIOMY)
    ap.add_argument("--korpus", type=Path, help="korpus trzonu (manifest.jsonl + pliki)")
    ap.add_argument("--cel", type=Path, help="katalog wyników (czasy.jsonl, proba.json, …)")
    ap.add_argument("--podsumuj", type=Path, metavar="CEL",
                    help="tylko tabela z katalogu wyników CEL: mediana s/stronę, awarie, start, szczyt pamięci (bez pomiaru)")
    ap.add_argument("--limit", type=int, help="tylko pierwsze N dokumentów próbki (próba narzędzia; wynik oznaczony proba_niepelna, "
                                              "--zloz odmawia bez --dopusc-niepelne)")
    ap.add_argument("--aplikacja-port", type=int, help="port działającej aplikacji Privatizer (privatizer-tekst/-plik)")
    ap.add_argument("--aplikacja-dane", type=Path, help="katalog danych aplikacji z sesja.json (domyślnie jak paths.py)")
    ap.add_argument("--rozgrzewka", type=int, default=ROZGRZEWKA, help="przejścia rozgrzewkowe (nieliczone)")
    ap.add_argument("--powtorzenia", type=int, default=POWTORZENIA, help="pomiary na dokument")
    ap.add_argument("--watki", type=int, default=WATKI, help="OMP_NUM_THREADS uczestnika (prerejestracja: 4)")
    ap.add_argument("--timeout", type=float, help="limit na dokument w s (domyślnie timeout_s z uczestnik.toml)")
    ap.add_argument("--uczestnicy", type=Path, default=KORZEN / "uczestnicy")
    ap.add_argument("--sprawdz", action="store_true", help="sucha kontrola (próbka, uczestnicy, aplikacja, warunki) bez pomiaru")
    ap.add_argument("--zloz", action="store_true", help="tylko złóż czasy.jsonl z pomiary.jsonl (bez pomiaru; niepełne dokumenty pominięte)")
    ap.add_argument("--dopusc-niepelne", action="store_true", help="--zloz: nie kończ błędem mimo niepełnych kompletów (tylko do wglądu)")
    ap.add_argument("--ignoruj-warunki", action="store_true", help="mierz mimo braku zasilacza/trybu niskiego zużycia (wynik nieważny)")
    a = ap.parse_args(argv)
    if a.podsumuj is not None:
        wiersze = podsumuj(a.podsumuj)
        if not wiersze:
            print(f"brak wyników w {a.podsumuj / 'czasy.jsonl'}", file=sys.stderr)
            return 2
        print(tabela_podsumowania(wiersze))
        if proba_niepelna_w(a.podsumuj):
            print("UWAGA: przebieg próbny (--limit) – próba niepełna, wynik nie jest wiążący", file=sys.stderr)
        return 0
    for brak in ("uczestnik", "poziom", "korpus", "cel"):
        if getattr(a, brak) is None:
            ap.error(f"wymagane --{brak} (poza --podsumuj)")
    if a.rozgrzewka < 0 or a.powtorzenia < 1:
        ap.error("--rozgrzewka >= 0, --powtorzenia >= 1")
    if a.limit is not None and a.limit < 1:
        ap.error("--limit >= 1")
    ids = [u for u in a.uczestnik.split(",") if u]
    try:
        pelna = losuj_probe(uruchom.wczytaj_manifest(a.korpus))
    except (BladProby, OSError) as e:
        ap.error(str(e))
    proba = pelna[:a.limit] if a.limit else pelna
    niepelna = len(proba) < len(pelna)
    if a.sprawdz:
        problemy = sprawdz(uczestnicy_ids=ids, poziom=a.poziom, proba=proba, korpus=a.korpus, cel=a.cel, uczestnicy=a.uczestnicy,
                           aplikacja_port=a.aplikacja_port, aplikacja_dane=a.aplikacja_dane)
        for p in problemy:
            print(f"PROBLEM: {p}")
        print("sprawdzenie: " + ("OK" if not problemy else f"{len(problemy)} problem(ów)"))
        return 0 if not problemy else 2
    if a.zloz:
        if proba_niepelna_w(a.cel) and not a.dopusc_niepelne:
            print(f"BŁĄD: {a.cel / 'srodowisko.json'} oznacza przebieg próbny (proba_niepelna: true, --limit) – odmowa złożenia "
                  "czasy.jsonl (--dopusc-niepelne tylko do wglądu)", file=sys.stderr)
            return 3
        niepelne = False
        for u in ids:
            licz = zloz(uczestnik=u, poziom=a.poziom, proba=proba, korpus=a.korpus, cel=a.cel, uczestnicy=a.uczestnicy,
                        przejscia=a.powtorzenia)
            if licz["niepelne"]:
                print(f"OSTRZEŻENIE: {u}/{a.poziom}: {licz['niepelne']} dokument(ów) bez kompletu {a.powtorzenia} przejść – "
                      "pominięte w czasy.jsonl (agregacja policzyłaby mniejszą próbę zamiast +∞)", file=sys.stderr)
                if not a.dopusc_niepelne:
                    niepelne = True
            print(f"{u}/{a.poziom}: złożono czasy.jsonl – ok {licz['ok']}, błąd {licz['blad']}, timeout {licz['timeout']}, "
                  f"odmowa {licz['odmowa']}, pominięte {licz['pominiety']}")
        return 3 if niepelne else 0
    sr = srodowisko()
    naruszenia = naruszenia_warunkow(sr)
    if naruszenia and not a.ignoruj_warunki:
        ap.error("warunki pomiaru niespełnione: " + "; ".join(naruszenia) + " (--ignoruj-warunki pomija)")
    if (a.cel / "pomiary.jsonl").exists() and proba_niepelna_w(a.cel) != niepelna:
        ap.error(f"{a.cel} zawiera pomiary z innego trybu (proba_niepelna={proba_niepelna_w(a.cel)}) – użyj czystego katalogu --cel "
                 "(przebieg próbny --limit i wiążący nie mogą dzielić pomiarów)")
    try:
        zapisz_probe(a.cel / "proba.json", pelna)
    except BladProby as e:
        ap.error(str(e))
    sr = {**sr, "proba_niepelna": niepelna, "limit": a.limit}
    zapisz_srodowisko(a.cel, sr, sys.argv[1:] if argv is None else list(argv))
    if threading.current_thread() is threading.main_thread():
        import signal

        def _sigterm(signum, frame):
            raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, _sigterm)
    kod = 0
    try:
        for u in ids:
            licz = zmierz(uczestnik=u, poziom=a.poziom, proba=proba, korpus=a.korpus, cel=a.cel, uczestnicy=a.uczestnicy,
                          watki=a.watki, rozgrzewka=a.rozgrzewka, powtorzenia=a.powtorzenia, timeout=a.timeout,
                          aplikacja_port=a.aplikacja_port, aplikacja_dane=a.aplikacja_dane)
            print(f"{u}/{a.poziom}: ok {licz['ok']}, błąd {licz['blad']}, timeout {licz['timeout']}, odmowa {licz['odmowa']}, "
                  f"pominięte {licz['pominiety']}, wcześniej {licz['wczesniej']}, nieprzetworzone {licz['nieprzetworzone']}")
            if licz["nieprzetworzone"]:
                kod = 2
    except BladDeklaracji as e:
        ap.error(str(e))
    finally:
        uruchom.zamknij_wszystkie()
    return kod


if __name__ == "__main__":
    sys.exit(main())
