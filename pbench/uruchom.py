"""Orkiestrator: uruchamia uczestnika benchmarku na dokumentach korpusu i zapisuje surowe wyniki z czasami.

    uv run pbench-uruchom --uczestnik <id> --split dev|test --poziom tekst|plik [--jezyki pl,en] [--limit N]
                          [--procesy N] [--watki N] [--timeout S] [--offline]

Każdy uczestnik ma własny projekt uv w `uczestnicy/<id>/` (`run.py`, `pyproject.toml`, `uczestnik.toml`, `KONFIG.md`).
Orkiestrator startuje go jako `uv run --project uczestnicy/<id> python run.py` (środowisko: `CUDA_VISIBLE_DEVICES=""`,
`OMP_NUM_THREADS`=`--watki`, `HF_HOME`=`vendor/hf`, z `--offline` także `HF_HUB_OFFLINE=1`; katalog roboczy – tymczasowy
per proces) i rozmawia z nim protokołem JSONL (`pbench.protokol`): linia `gotowy` z wersjami, potem
zapytanie → odpowiedź na każdy dokument.

Deklaracja `uczestnicy/<id>/uczestnik.toml` (wszystkie pola obowiązkowe poza `procesy`, `timeout_s`, `start_timeout_s`):

    poziomy = ["tekst", "plik"]         # obsługiwane poziomy
    jezyki  = ["pl", "en", "es", "de", "fr"]
    jezyki_oficjalne = ["en"]           # opcjonalne (domyślnie = jezyki): języki oficjalnie obsługiwane wg karty/dokumentacji
    formaty = ["docx", "pdf"]           # tylko dla poziomu plik
    procesy = 1                         # ile instancji wolno uruchomić równolegle (domyślnie 1)
    timeout_s = 300                     # limit na jeden dokument (domyślnie 300)
    start_timeout_s = 600               # limit na start procesu (ładowanie modeli; domyślnie 600)
    aneks = true                        # opcjonalne (domyślnie false): wariant ablacyjny/krzyżowy – aneks, poza rankingami

Dokument spoza deklaracji (język albo – na poziomie plik – format) dostaje wpis `{"id", "pominiety": "jezyk"|"format"}`:
sędzia liczy go jako „nie obsługuje”, osobno od błędu. Wyjątek – język z `JEZYKI_ZASTEPCZE` (ukraiński, warstwa trudnych
przypadków): uczestnik, który go nie deklaruje, przetwarza dokument w języku zastępczym (`jezyk_uzyty`: pierwszy zadeklarowany
z listy zastępczej – jedna reguła dla wszystkich uczestników, `metodyka/uczestnicy.md`); zapytanie protokołu niesie język
użyty, a wynik surowy – oba (`jezyk` dokumentu i `jezyk_uzyty`).

Wyniki (`--wyniki`, domyślnie `wyniki/`):

* `surowe/<id>/wersje.json` – `{"wersje": {pakiet: wersja}, "jezyki", "jezyki_oficjalne", "aneks", "zapisano": ISO}` z linii `gotowy`
  (ostatni przebieg; `aneks` z deklaracji – agregacja wyłącza takiego uczestnika z rankingów);
* `surowe/<id>/<split>/<poziom>.jsonl` – po jednej linii na dokument (kolejność dowolna, zapis atomowy per linia):
  `{"id","jezyk","jezyk_uzyty","wykrycia":[[start,end,etykieta,wynik],...],"czas_s"}` (tekst) albo `{"id","jezyk",
  "jezyk_uzyty","plik_wyj":"pliki/<id>.<ext>","czas_s"}` (plik; ścieżka względem `surowe/<id>/<split>/`) albo `{"id","jezyk",
  "jezyk_uzyty","blad":str,"czas_s"}` albo `{"id","pominiety"}`. `czas_s` = od wysłania zapytania do odebrania odpowiedzi
  (albo do timeoutu/padu);
* `surowe/<id>/<split>/<poziom>.starty.jsonl` – start każdej instancji osobno: `{"proces","start_s","przyczyna"}`
  (`start_s` = od uruchomienia do linii `gotowy`; `przyczyna` = `start` albo `restart` po timeoucie/padzie);
* `surowe/<id>/<split>/<poziom>.stderr-<n>.log` – stderr instancji nr n (dopisywany);
* `surowe/<id>/<split>/pliki/` – pliki wynikowe uczestnika (poziom plik).

Wznawianie i ponawianie (jedna polityka dla wszystkich uczestników): dokumenty, których ostatni wpis w `<poziom>.jsonl`
jest wynikiem (`wykrycia`/`plik_wyj`) albo `pominiety`, są pomijane. Dokumenty zakończone `blad` (błąd, timeout, pad) są
powtarzane: w jednym przebiegu co najwyżej 2 razy (3 próby; `proby` w rekordzie = liczba prób), a przy wznowieniu
przebiegu także te z poprzednich przebiegów (`--bez-ponawiania` wyłącza oba). Plik jest dopisywany, więc ponowiony
dokument ma kilka linii; liczy się ostatnia (`pbench-ocen` czyta ostatnią). `pominiety` nie jest ponawiany – poza
`pominiety: jezyk`, którego język uczestnik dziś przetwarza (`jezyk_uzyty`; wpis nieaktualny, np. dokument `uk` z przebiegu
sprzed języka zastępczego): taki dokument jest przetwarzany przy wznowieniu, niezależnie od `--bez-ponawiania`.
Timeout dokumentu zabija całą grupę procesów uczestnika (`uv run` i potomne, np. serwery modeli) i zapisuje `blad`;
seria leci dalej na świeżej instancji. Przy wyjściu, Ctrl-C i SIGTERM wszystkie żywe instancje są zabijane (grupami), a
niedokończone dokumenty nie dostają wpisów. Trzy kolejne nieudane starty instancji kończą jej wątek (zadania przejmują
pozostałe); gdy żaden wątek nie przetworzy całej kolejki, polecenie kończy się kodem 2, a przebieg można wznowić.
Przed startem runner sprawdza wersję Pythona projektu uczestnika (`OCZEKIWANY_PYTHON` = 3.12) i ostrzega o innej.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import queue
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from . import protokol

KORZEN = Path(__file__).resolve().parent.parent
#: Języki dokumentów korpusu: pięć języków trzonu i ukraiński (warstwa trudnych przypadków, poza T4 – `metodyka/punktacja.md`).
JEZYKI = ("pl", "en", "es", "de", "fr", "uk")
#: Język dokumentu -> języki zastępcze (w kolejności), gdy uczestnik go nie deklaruje. Ukraiński: polski (najbliższy z pięciu –
#: język słowiański; transliteracje osób z Ukrainy w korpusie są też w zapisie polskim), potem angielski (domyślny język
#: większości narzędzi), niemiecki, hiszpański, francuski. Ta sama reguła dla wszystkich uczestników (`metodyka/uczestnicy.md`).
JEZYKI_ZASTEPCZE: dict[str, tuple[str, ...]] = {"uk": ("pl", "en", "de", "es", "fr")}
POZIOMY = ("tekst", "plik")
LIMIT_BLEDU = 1000          # znaków komunikatu błędu zapisywanych w wyniku
MAKS_PORAZEK_STARTU = 3
MAKS_PONOWIEN = 2           # ile razy w jednym przebiegu powtarzamy dokument zakończony błędem/timeoutem
OCZEKIWANY_PYTHON = "3.12"  # uczestnicy mają przypiętą wersję Pythona (requires-python); inna → ostrzeżenie


def jezyk_uzyty(jezyk: str, deklarowane: tuple[str, ...] | list[str]) -> str | None:
    """Język, w którym uczestnik deklarujący `deklarowane` przetwarza dokument w języku `jezyk`: ten sam, gdy go deklaruje,
    inaczej pierwszy zadeklarowany z `JEZYKI_ZASTEPCZE[jezyk]`; None – brak (dokument „pominiety: jezyk”)."""
    if jezyk in deklarowane:
        return jezyk
    return next((j for j in JEZYKI_ZASTEPCZE.get(jezyk, ()) if j in deklarowane), None)


class BladDeklaracji(ValueError):
    """Niepoprawny `uczestnik.toml`."""


class BladProcesu(Exception):
    """Instancja uczestnika nie odpowiedziała (timeout, pad, śmieci w protokole)."""


@dataclass(frozen=True)
class Deklaracja:
    poziomy: tuple[str, ...]
    jezyki: tuple[str, ...]
    formaty: tuple[str, ...]
    procesy: int = 1
    timeout_s: float = 300.0
    start_timeout_s: float = 600.0
    #: języki, które narzędzie/model oficjalnie obsługuje (karta/dokumentacja); `jezyki` = na jakich uruchamiamy.
    #: Brak pola w tomlu = `jezyki`. Sędzia oznacza dokumenty flagą `w_zakresie_oficjalnym` (miara „w zakresie oficjalnym”).
    jezyki_oficjalne: tuple[str, ...] | None = None
    #: Wariant ablacyjny albo krzyżowy (`privatizer-reguly`, `presidio-lgp`, `privatizer-tekst-gliner`…): wyniki w aneksie,
    #: poza rankingami (`metodyka/punktacja.md`, `metodyka/uczestnicy.md`). Brak pola w tomlu = False.
    aneks: bool = False


def wczytaj_deklaracje(katalog: Path) -> Deklaracja:
    """Czyta `uczestnik.toml` z katalogu uczestnika; brak pliku/pola albo zła wartość → `BladDeklaracji`."""
    p = Path(katalog) / "uczestnik.toml"
    if not p.exists():
        raise BladDeklaracji(f"brak {p}")
    try:
        d = tomllib.loads(p.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise BladDeklaracji(f"{p}: {e}") from e
    nieznane = set(d) - {"poziomy", "jezyki", "jezyki_oficjalne", "formaty", "procesy", "timeout_s",
                          "start_timeout_s", "aneks"}
    if nieznane:
        raise BladDeklaracji(f"{p}: nieznane pola {sorted(nieznane)}")
    for pole in ("poziomy", "jezyki", "formaty"):
        if not isinstance(d.get(pole), list) or not all(isinstance(x, str) for x in d[pole]):
            raise BladDeklaracji(f"{p}: pole '{pole}' jest obowiązkowe i musi być listą napisów")
    if not set(d["poziomy"]) <= set(POZIOMY) or not set(d["jezyki"]) <= set(JEZYKI):
        raise BladDeklaracji(f"{p}: nieznany poziom lub język")
    oficjalne = d.get("jezyki_oficjalne", d["jezyki"])
    if not isinstance(oficjalne, list) or not all(isinstance(x, str) for x in oficjalne) or not set(oficjalne) <= set(JEZYKI):
        raise BladDeklaracji(f"{p}: 'jezyki_oficjalne' musi być listą znanych języków")
    aneks = d.get("aneks", False)
    if not isinstance(aneks, bool):
        raise BladDeklaracji(f"{p}: 'aneks' musi być wartością logiczną (true/false)")
    procesy = d.get("procesy", 1)
    if not isinstance(procesy, int) or isinstance(procesy, bool) or procesy < 1:
        raise BladDeklaracji(f"{p}: 'procesy' musi być liczbą całkowitą >= 1")
    liczby = {}
    for pole, domyslnie in (("timeout_s", 300.0), ("start_timeout_s", 600.0)):
        v = d.get(pole, domyslnie)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0:
            raise BladDeklaracji(f"{p}: '{pole}' musi być liczbą > 0")
        liczby[pole] = float(v)
    return Deklaracja(tuple(d["poziomy"]), tuple(d["jezyki"]), tuple(d["formaty"]), procesy,
                      jezyki_oficjalne=tuple(oficjalne), aneks=aneks, **liczby)


def sprawdz_python(katalog: Path, env: dict[str, str], oczekiwany: str = OCZEKIWANY_PYTHON) -> str | None:
    """Wersja Pythona, na której `uv run --project <katalog>` uruchomi uczestnika; ostrzega (stderr), gdy nie zaczyna się od
    `oczekiwany`. Zwraca wersję albo None, gdy nie udało się jej ustalić (to też ostrzeżenie – środowisko się nie buduje)."""
    try:
        r = subprocess.run(["uv", "run", "--project", str(Path(katalog).resolve()), "python", "-c",
                            "import platform; print(platform.python_version())"],
                           capture_output=True, text=True, env=env, timeout=1800)
        wersja = r.stdout.strip().splitlines()[-1] if r.returncode == 0 and r.stdout.strip() else None
    except (OSError, subprocess.TimeoutExpired):
        wersja = None
    if wersja is None:
        print(f"OSTRZEŻENIE: nie udało się ustalić wersji Pythona uczestnika {Path(katalog).name}", file=sys.stderr)
    elif not (wersja == oczekiwany or wersja.startswith(oczekiwany + ".")):
        print(f"OSTRZEŻENIE: uczestnik {Path(katalog).name} działa na Pythonie {wersja}, oczekiwano {oczekiwany}.x "
              f"(przypnij `requires-python` w jego pyproject.toml)", file=sys.stderr)
    return wersja


# ----------------------------------------------------------------------------- walidacja odpowiedzi
def _obetnij(tekst: object) -> str:
    return str(tekst)[:LIMIT_BLEDU]


def _normalizuj_odpowiedz_tekst(odp: dict[str, Any], tekst: str) -> dict[str, Any]:
    """Odpowiedź poziomu tekst → `{"wykrycia": [[s,e,etykieta,wynik],...]}` albo `{"blad": str}`.

    Offsety muszą mieścić się w tekście wejściowym (0 <= start < end <= len(tekst), w znakach): wykrycie poza tekstem
    unieważnia cały dokument (błąd uczestnika, nie cichy zwrot przycięty przez sędziego)."""
    if "blad" in odp:
        return {"blad": _obetnij(odp["blad"])}
    wyk = odp.get("wykrycia")
    if not isinstance(wyk, list):
        return {"blad": "odpowiedź bez pola 'wykrycia' (lista)"}
    wynik = []
    for i, w in enumerate(wyk):
        if not isinstance(w, (list, tuple)) or len(w) not in (3, 4):
            return {"blad": f"wykrycie {i}: oczekiwano [start, end, etykieta(, wynik)]"}
        s, e, et = w[0], w[1], w[2]
        sc = w[3] if len(w) == 4 else None
        if any(isinstance(x, bool) or not isinstance(x, int) for x in (s, e)) or not isinstance(et, str):
            return {"blad": f"wykrycie {i}: start/end muszą być liczbami całkowitymi, etykieta napisem"}
        if sc is not None and (isinstance(sc, bool) or not isinstance(sc, (int, float))):
            return {"blad": f"wykrycie {i}: wynik musi być liczbą albo null"}
        if not 0 <= s < e <= len(tekst):
            return {"blad": f"offset poza tekstem: wykrycie {i} [{s}, {e}) przy długości tekstu {len(tekst)}"}
        wynik.append([s, e, et, sc])
    return {"wykrycia": wynik}


# ----------------------------------------------------------------------------- proces uczestnika
def _zabij(proc: subprocess.Popen) -> None:
    """Zabija całą grupę procesów uczestnika, także gdy lider już zakończył działanie (`uv run` i jego potomne – np.
    serwery modeli – nie mogą zostać osierocone)."""
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
        else:
            os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        pass
    if proc.poll() is None:
        try:
            proc.kill()
        except OSError:
            pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass


#: Żywe instancje (zamykane przy wyjściu, Ctrl-C i SIGTERM – żadna grupa procesów nie zostaje osierocona).
_ZYWE: set["Proces"] = set()
_ZYWE_BLOKADA = threading.Lock()


def zamknij_wszystkie() -> None:
    with _ZYWE_BLOKADA:
        zywe = list(_ZYWE)
    for p in zywe:
        p.zamknij()


class Proces:
    """Jedna instancja uczestnika: własny stdin/stdout, tymczasowy katalog roboczy, wątek czytający wyjście."""

    def __init__(self, katalog: Path, env: dict[str, str], log_stderr: Path) -> None:
        self.katalog = Path(katalog).resolve()
        self.env = env
        self.log_stderr = log_stderr
        self.proc: subprocess.Popen | None = None
        self.wyjscie: queue.Queue = queue.Queue()
        self.praca: str | None = None
        self.wersje: dict[str, str] = {}
        self._blad_czytnika = 0

    def start(self, timeout: float) -> tuple[dict[str, str], float]:
        """Uruchamia proces i czeka na linię `gotowy`. Zwraca (wersje, czas startu w s); błąd → `BladProcesu`."""
        self.praca = tempfile.mkdtemp(prefix="pbench-uczestnik-")
        self.wyjscie = queue.Queue()            # świeża kolejka: EOF zabitej poprzedniej instancji nie może jej zatruć
        komenda = ["uv", "run", "--project", str(self.katalog), "python", str(self.katalog / "run.py")]
        opcje: dict[str, Any] = {}
        if sys.platform == "win32":
            opcje["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            opcje["start_new_session"] = True
        t0 = time.perf_counter()
        self.log_stderr.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_stderr, "ab") as log:
            self.proc = subprocess.Popen(komenda, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log,
                                         cwd=self.praca, env=self.env, encoding="utf-8", errors="replace",
                                         bufsize=1, **opcje)
        with _ZYWE_BLOKADA:
            _ZYWE.add(self)
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

    @staticmethod
    def _czytaj(proc: subprocess.Popen, wyj: queue.Queue) -> None:
        """Wątek: linie wyjścia → kolejka; linie niebędące protokołem (np. print biblioteki) są pomijane."""
        for linia in proc.stdout:
            if not linia.strip():
                continue
            try:
                wyj.put(protokol.parsuj_wyjscie(linia))
            except ValueError:
                continue
        wyj.put(None)

    def _czekaj(self, timeout: float, co: str) -> dict[str, Any]:
        try:
            odp = self.wyjscie.get(timeout=timeout)
        except queue.Empty:
            raise BladProcesu(f"timeout {timeout:g} s ({co})") from None
        if odp is None:
            try:
                kod = self.proc.wait(timeout=10) if self.proc else None
            except subprocess.TimeoutExpired:
                kod = "nieznany"
            raise BladProcesu(f"proces uczestnika zakończył działanie (kod {kod}) podczas: {co}")
        return odp

    def zapytaj(self, zapytanie: dict[str, Any], timeout: float) -> dict[str, Any]:
        """Wysyła zapytanie i czeka na odpowiedź o tym samym `id`; timeout/pad → `BladProcesu` (proces do zamknięcia)."""
        try:
            protokol.wyslij(self.proc.stdin, zapytanie)
        except (BrokenPipeError, OSError):
            raise BladProcesu("proces uczestnika zakończył działanie (zapis do stdin)") from None
        koniec = time.monotonic() + timeout
        while True:
            odp = self._czekaj(max(0.0, koniec - time.monotonic()), f"dokument {zapytanie['id']}")
            if odp.get("id") == zapytanie["id"]:
                return odp
            if "id" in odp:
                raise BladProcesu(f"odpowiedź o niezgodnym id {_obetnij(odp['id'])!r}")

    def zamknij(self) -> None:
        if self.proc is not None:
            try:
                if self.proc.stdin:
                    self.proc.stdin.close()
            except OSError:
                pass
            if self.proc.poll() is None:
                try:
                    self.proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass
            _zabij(self.proc)
            self.proc = None
        with _ZYWE_BLOKADA:
            _ZYWE.discard(self)
        if self.praca:
            shutil.rmtree(self.praca, ignore_errors=True)
            self.praca = None


# ----------------------------------------------------------------------------- zapis wyników
class Zapis:
    """Dopisywanie linii JSON do pliku: jeden `write` na linię pod blokadą, po każdej linii flush + fsync."""

    def __init__(self, sciezka: Path) -> None:
        sciezka.parent.mkdir(parents=True, exist_ok=True)
        self._f = open(sciezka, "ab")
        self._blokada = threading.Lock()

    def dodaj(self, obj: dict[str, Any]) -> None:
        dane = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
        with self._blokada:
            self._f.write(dane)
            self._f.flush()
            os.fsync(self._f.fileno())

    def zamknij(self) -> None:
        self._f.close()


def gotowe_id(sciezka: Path, ponawiaj_bledy: bool = False,
              obslugiwany: Callable[[str], bool] | None = None) -> set[str]:
    """`id` dokumentów już zapisanych w JSONL (uszkodzony – ucięty – wiersz jest pomijany, a plik wyrównywany do nowej
    linii, żeby kolejny zapis nie skleił się z resztką). Przy kilku liniach tego samego `id` liczy się ostatnia; z
    `ponawiaj_bledy` dokument, którego ostatni wpis to `blad`, nie jest „gotowy” (zostanie powtórzony). Dokument, którego
    ostatni wpis to `pominiety: jezyk`, a `obslugiwany(id)` jest prawdą (uczestnik przetwarza dziś jego język – np. w języku
    zastępczym `JEZYKI_ZASTEPCZE`, którego wpis sprzed H6a nie znał), też nie jest „gotowy” (wpis nieaktualny)."""
    if not sciezka.exists():
        return set()
    dane = sciezka.read_bytes()
    if dane and not dane.endswith(b"\n"):
        with open(sciezka, "ab") as f:
            f.write(b"\n")
    ostatnie: dict[str, dict] = {}
    for linia in dane.decode("utf-8", errors="replace").splitlines():
        try:
            obj = json.loads(linia)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "id" in obj:
            ostatnie[obj["id"]] = obj
    return {i for i, o in ostatnie.items() if not (ponawiaj_bledy and "blad" in o)
            and not (obslugiwany is not None and o.get("pominiety") == "jezyk" and obslugiwany(i))}


def wczytaj_manifest(korpus: Path) -> list[dict[str, Any]]:
    p = Path(korpus) / "manifest.jsonl"
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


# ----------------------------------------------------------------------------- przebieg
def zbuduj_srodowisko(watki: int, offline: bool) -> dict[str, str]:
    env = dict(os.environ)
    env.pop("VIRTUAL_ENV", None)            # uv uruchamiany z venva harnessu ostrzegałby o niezgodnym środowisku
    env.update({"CUDA_VISIBLE_DEVICES": "", "OMP_NUM_THREADS": str(watki), "PYTHONUTF8": "1",
                "PYTHONIOENCODING": "utf-8", "HF_HOME": str(KORZEN / "vendor" / "hf")})
    if offline:
        env["HF_HUB_OFFLINE"] = "1"
    return env


def _zadanie(wpis: dict[str, Any], poziom: str, korpus: Path, katalog_pliki: Path, jezyk: str | None = None) -> dict[str, Any]:
    """Zapytanie protokołu dla dokumentu + dane pomocnicze (klucze zaczynające się od `_` nie idą do uczestnika). `jezyk` – język
    użyty (`jezyk_uzyty`; domyślnie język dokumentu)."""
    jezyk = jezyk or wpis["jezyk"]
    if poziom == "tekst":
        # bajty → napis bez tłumaczenia końców linii: offsety gold odnoszą się do dokładnej treści pliku .txt
        tekst = (korpus / wpis["plik_txt"]).read_bytes().decode("utf-8")
        return {"id": wpis["id"], "jezyk": jezyk, "tekst": tekst}
    wyj = katalog_pliki / f"{wpis['id']}{Path(wpis['plik']).suffix}"
    return {"id": wpis["id"], "jezyk": jezyk, "plik_wej": str((korpus / wpis["plik"]).resolve()),
            "plik_wyj": str(wyj.resolve())}


def _obsluz(proces: Proces, zap: dict[str, Any], poziom: str, timeout: float) -> tuple[dict[str, Any], bool]:
    """Wysyła zapytanie. Zwraca (rekord bez id/jezyk/czas_s, czy proces trzeba zamknąć)."""
    t0 = time.perf_counter()
    try:
        odp = proces.zapytaj(zap, timeout)
    except BladProcesu as e:
        return {"blad": str(e), "czas_s": time.perf_counter() - t0}, True
    czas = time.perf_counter() - t0
    if poziom == "tekst":
        rek = _normalizuj_odpowiedz_tekst(odp, zap["tekst"])
    elif "blad" in odp:
        rek = {"blad": _obetnij(odp["blad"])}
    else:
        # R38: wynikiem jest plik, który narzędzie faktycznie zapisało – uczestnik może zwrócić ścieżkę z innym rozszerzeniem
        # niż oryginał (`.doc` → `.docx`, `.msg` → `.txt`), byle w katalogu wyników; format rozpoznaje sędzia po treści
        zadane = Path(zap["plik_wyj"])
        wyj = Path(odp["plik_wyj"]) if isinstance(odp.get("plik_wyj"), str) else zadane
        if wyj.parent.resolve() != zadane.parent.resolve() or wyj.stem != zadane.stem:
            wyj = zadane
        if not wyj.is_file() or wyj.stat().st_size == 0:
            rek = {"blad": "brak (albo pusty) plik wynikowy"}
        else:
            rek = {"plik_wyj": f"pliki/{wyj.name}", "format_wyj": wyj.suffix.lower().lstrip(".")}
    if "blad" not in rek and isinstance(odp.get("ostrzezenie"), str):
        rek["ostrzezenie"] = _obetnij(odp["ostrzezenie"])      # np. nieudane sprzątanie po udanym wyniku (bez treści dokumentu)
    rek["czas_s"] = czas
    return rek, False


def wykonaj(*, uczestnik: str, split: str, poziom: str, korpus: Path, wyniki: Path, uczestnicy: Path,
            jezyki: tuple[str, ...] | None = None, limit: int | None = None, procesy: int | None = None,
            watki: int = 1, timeout: float | None = None, offline: bool = False, ponawiaj_bledy: bool = True,
            oczekiwany_python: str = OCZEKIWANY_PYTHON) -> dict[str, int]:
    """Przebieg dla jednego uczestnika/splitu/poziomu. Zwraca liczniki
    `{"ok","blad","pominiety","wczesniej","nieprzetworzone"}`; `nieprzetworzone` > 0 = przebieg przerwany."""
    katalog = Path(uczestnicy) / uczestnik
    decl = wczytaj_deklaracje(katalog)
    if poziom not in decl.poziomy:
        raise BladDeklaracji(f"uczestnik {uczestnik} nie deklaruje poziomu '{poziom}' (deklaruje: {list(decl.poziomy)})")
    timeout = timeout or decl.timeout_s
    korpus = Path(korpus)
    wyjscie = Path(wyniki) / "surowe" / uczestnik
    dir_split = wyjscie / split
    plik_jsonl = dir_split / f"{poziom}.jsonl"
    pliki = dir_split / "pliki"
    if poziom == "plik":
        pliki.mkdir(parents=True, exist_ok=True)

    wpisy = [w for w in wczytaj_manifest(korpus) if w["split"] == split and (not jezyki or w["jezyk"] in jezyki)]
    if limit is not None:
        wpisy = wpisy[:limit]
    jezyk_wpisu = {w["id"]: w["jezyk"] for w in wpisy}
    zrobione = gotowe_id(plik_jsonl, ponawiaj_bledy,
                         lambda i: i in jezyk_wpisu and jezyk_uzyty(jezyk_wpisu[i], decl.jezyki) is not None)
    licz = {"ok": 0, "blad": 0, "pominiety": 0, "wczesniej": 0, "nieprzetworzone": 0}
    zapis = Zapis(plik_jsonl)
    kolejka: queue.Queue = queue.Queue()
    for w in wpisy:
        if w["id"] in zrobione:
            licz["wczesniej"] += 1
        elif jezyk_uzyty(w["jezyk"], decl.jezyki) is None:
            zapis.dodaj({"id": w["id"], "pominiety": "jezyk"})
            licz["pominiety"] += 1
        elif poziom == "plik" and w["format"] not in decl.formaty:
            zapis.dodaj({"id": w["id"], "pominiety": "format"})
            licz["pominiety"] += 1
        else:
            kolejka.put((w, 1))
    do_zrobienia = kolejka.qsize()
    przerwano = threading.Event()
    blokada = threading.Lock()
    starty = Zapis(dir_split / f"{poziom}.starty.jsonl")
    zapisano_wersje = threading.Event()
    env = zbuduj_srodowisko(watki, offline)

    def zapisz_wersje(wersje: dict[str, str]) -> None:
        if not zapisano_wersje.is_set():
            zapisano_wersje.set()
            wyjscie.mkdir(parents=True, exist_ok=True)
            (wyjscie / "wersje.json").write_text(json.dumps(
                {"wersje": wersje, "jezyki": list(decl.jezyki), "jezyki_oficjalne": list(decl.jezyki_oficjalne or decl.jezyki),
                 "aneks": decl.aneks, "zapisano": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")},
                ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def watek(nr: int) -> None:
        proces = Proces(katalog, env, dir_split / f"{poziom}.stderr-{nr}.log")
        zywy = False
        porazki = 0
        przyczyna = "start"
        try:
            while True:
                try:
                    wpis, proba = kolejka.get_nowait()
                except queue.Empty:
                    return
                if przerwano.is_set():
                    return
                if not zywy:
                    try:
                        wersje, start_s = proces.start(decl.start_timeout_s)
                    except BladProcesu as e:
                        kolejka.put((wpis, proba))           # zadanie przejmie inny wątek (albo przebieg się przerwie)
                        porazki += 1
                        print(f"[proces {nr}] start nieudany ({porazki}/{MAKS_PORAZEK_STARTU}): {e}", file=sys.stderr)
                        if porazki >= MAKS_PORAZEK_STARTU:
                            return
                        continue
                    porazki, zywy = 0, True
                    zapisz_wersje(wersje)
                    starty.dodaj({"proces": nr, "start_s": round(start_s, 3), "przyczyna": przyczyna})
                uzyty = jezyk_uzyty(wpis["jezyk"], decl.jezyki)
                zap = _zadanie(wpis, poziom, korpus, pliki, uzyty)
                if poziom == "plik":
                    for stary in Path(zap["plik_wyj"]).parent.glob(Path(zap["plik_wyj"]).stem + ".*"):
                        stary.unlink(missing_ok=True)       # także wynik z innym rozszerzeniem (R38)
                rek, zamknac = _obsluz(proces, zap, poziom, timeout)
                if przerwano.is_set():
                    return                                    # przerwanie (Ctrl-C/SIGTERM): nie zapisuj śmieciowych błędów
                if "blad" in rek and ponawiaj_bledy and proba <= MAKS_PONOWIEN:
                    kolejka.put((wpis, proba + 1))            # ponowienie (do MAKS_PONOWIEN razy na dokument w przebiegu)
                else:
                    zapis.dodaj({"id": wpis["id"], "jezyk": wpis["jezyk"], "jezyk_uzyty": uzyty, **rek, "proby": proba})
                    with blokada:
                        licz["blad" if "blad" in rek else "ok"] += 1
                if zamknac:
                    proces.zamknij()
                    zywy, przyczyna = False, "restart"
        finally:
            proces.zamknij()

    n = max(1, min(procesy or decl.procesy, decl.procesy, do_zrobienia or 1))
    watki_ = [threading.Thread(target=watek, args=(i + 1,), name=f"uczestnik-{i + 1}", daemon=True) for i in range(n)]
    try:
        if do_zrobienia:
            sprawdz_python(katalog, env, oczekiwany_python)
        for t in watki_:
            t.start()
        while any(t.is_alive() for t in watki_):
            for t in watki_:
                t.join(0.2)
    except BaseException:                                     # Ctrl-C, SIGTERM (→ KeyboardInterrupt), błąd orkiestratora
        przerwano.set()
        raise
    finally:
        zamknij_wszystkie()
        zapis.zamknij()
        starty.zamknij()
    licz["nieprzetworzone"] = kolejka.qsize()
    return licz


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pbench-uruchom", description="Uruchamia uczestnika benchmarku na korpusie.")
    ap.add_argument("--uczestnik", required=True, help="nazwa katalogu w uczestnicy/")
    ap.add_argument("--split", required=True, choices=("dev", "test"))
    ap.add_argument("--poziom", required=True, choices=POZIOMY)
    ap.add_argument("--jezyki", help="tylko te języki, np. pl,en")
    ap.add_argument("--limit", type=int, help="pierwsze N dokumentów po filtrze języków (kolejność manifestu)")
    ap.add_argument("--procesy", type=int, help="mniej instancji niż w uczestnik.toml (nie więcej)")
    ap.add_argument("--watki", type=int, default=1, help="OMP_NUM_THREADS na instancję (domyślnie 1)")
    ap.add_argument("--timeout", type=float, help="limit na dokument w s (domyślnie z uczestnik.toml, 300)")
    ap.add_argument("--offline", action="store_true", help="HF_HUB_OFFLINE=1 (po pierwszym pobraniu modeli)")
    ap.add_argument("--bez-ponawiania", action="store_true",
                    help="nie powtarzaj dokumentów zakończonych błędem (domyślnie: do 2 powtórzeń w przebiegu i ponowienie "
                         "błędów z poprzednich przebiegów przy wznowieniu; `pominiety` nigdy – poza nieaktualnym "
                         "`pominiety: jezyk`)")
    ap.add_argument("--korpus", type=Path, default=KORZEN / "korpus")
    ap.add_argument("--wyniki", type=Path, default=KORZEN / "wyniki")
    ap.add_argument("--uczestnicy", type=Path, default=KORZEN / "uczestnicy")
    a = ap.parse_args(argv)
    poprzedni = None
    if threading.current_thread() is threading.main_thread():
        def _sigterm(signum, frame):
            raise KeyboardInterrupt
        poprzedni = signal.signal(signal.SIGTERM, _sigterm)
    jezyki = tuple(j for j in (a.jezyki or "").split(",") if j) or None
    if jezyki and not set(jezyki) <= set(JEZYKI):
        ap.error(f"nieznany język w --jezyki (dozwolone: {', '.join(JEZYKI)})")
    try:
        licz = wykonaj(uczestnik=a.uczestnik, split=a.split, poziom=a.poziom, korpus=a.korpus, wyniki=a.wyniki,
                       uczestnicy=a.uczestnicy, jezyki=jezyki, limit=a.limit, procesy=a.procesy, watki=a.watki,
                       timeout=a.timeout, offline=a.offline, ponawiaj_bledy=not a.bez_ponawiania)
    except BladDeklaracji as e:
        ap.error(str(e))
    finally:
        if poprzedni is not None:
            signal.signal(signal.SIGTERM, poprzedni)
    print(f"{a.uczestnik}/{a.split}/{a.poziom}: ok {licz['ok']}, błędy {licz['blad']}, pominięte {licz['pominiety']}, "
          f"wcześniej gotowe {licz['wczesniej']}, nieprzetworzone {licz['nieprzetworzone']}")
    return 2 if licz["nieprzetworzone"] else 0


if __name__ == "__main__":
    sys.exit(main())
