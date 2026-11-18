"""Skład raportu: rozdziały `rozdzialy/NN-nazwa.md` → Jinja2 (dane) → Markdown → HTML (szablon + druk.css) → PDF (Chromium przez Playwright).

CLI: `uv run --group raport python -m raport.buduj --wyniki DIR --cel PLIK.pdf [--html PLIK.html] [--cel-aneks PLIK.pdf [--html-aneks PLIK.html]] [--publikacja]`.
Aneks liczbowy (`aneks_liczbowy/*.md`) to osobny dokument towarzyszący, budowany tym samym potokiem i z tą samą kontrolą.
Przed składem i po nim działa kontrola treści (`raport.kontrola`); w trybie `--publikacja` znaczniki weryfikacji też są błędem."""
from __future__ import annotations

import argparse
import base64
import html as _html
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Callable

import jinja2
import markdown
from markupsafe import Markup

from raport.dane import REPOZYTORIUM, Raport, domeny_wiersz, kontaminacja, liczba, liczby_opisowe, ile, maks_punktow, pamiec_wysoka, czas_podsumowanie_wg_pamieci, liczebnosc_domen, pozycja_szybkosci, porownanie_trybow, prywatizer, wagi_punktow, procent, przedzial, przedzial_procent, roznica, roznica_pp, przewaga_domen, sygnaly_domen, zmiana_rankingu, suma_bez_szybkosci, wagi_testow, wczytaj, wiersz
from raport.tabele import ZESTAWY_WAG, TABELE_FUNKCJE, liczba_przewag, przewagi
from raport.wykresy import KATEGORIE_N, WYKRESY_FUNKCJE
from raport.kontrola import kontroluj_pdf, kontroluj_zrodla, znaczniki_zrodel

KATALOG = Path(__file__).parent
ROZDZIALY = KATALOG / "rozdzialy"
ANEKS = KATALOG / "aneks_liczbowy"
TYTUL_RAPORTU = "Raport porównawczy anonimizacji"
TYTUL_ANEKSU = "Aneks liczbowy"
SZABLON = KATALOG / "szablon"
CZCIONKI = KATALOG / "czcionki"
LOGO = KATALOG / "grafika" / "privatizer-logo-pelne-jasne-tlo.svg"

# Rejestry bloków wstawianych z rozdziałów przez `{{ tabela('nazwa', …) }}` / `{{ wykres('nazwa', …) }}`; funkcja: `(r, *args, **kw) -> str` (HTML/SVG).
TABELE: dict[str, Callable[..., str]] = dict(TABELE_FUNKCJE)
WYKRESY: dict[str, Callable[..., str]] = dict(WYKRESY_FUNKCJE)

_ZAKRESY = {
    "latin": "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD",
    "latin-ext": "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF",
}
_RODZINY = {"sans": "IBM Plex Sans", "serif": "IBM Plex Serif", "mono": "IBM Plex Mono"}
_BLOK = re.compile(r"(?:<p>)?@@BLOK(\d+)@@(?:</p>)?")


class BladKontroli(Exception):
    """Kontrola treści nie przeszła; `bledy` = lista komunikatów „plik:wiersz: opis”."""

    def __init__(self, bledy: list[str]):
        super().__init__("Kontrola treści nie przeszła:\n" + "\n".join(bledy))
        self.bledy = bledy


def _fonty_css() -> str:
    """@font-face z wbudowanych woff2 (base64) – HTML jest samodzielny, bez zależności od ścieżek."""
    bloki = []
    for plik in sorted(CZCIONKI.glob("ibm-plex-*.woff2")):
        m = re.fullmatch(r"ibm-plex-(sans|serif|mono)-(latin-ext|latin)-(\d+)\.woff2", plik.name)
        if not m:
            continue
        rodzina, zestaw, waga = m.groups()
        b64 = base64.b64encode(plik.read_bytes()).decode("ascii")
        bloki.append(
            f'@font-face {{ font-family: "{_RODZINY[rodzina]}"; font-weight: {waga}; font-style: normal; font-display: block; '
            f'src: url(data:font/woff2;base64,{b64}) format("woff2"); unicode-range: {_ZAKRESY[zestaw]}; }}')
    return "\n".join(bloki)


def _slug(tekst: str, sep: str) -> str:
    """Identyfikator z nagłówka z polskimi znakami (domyślny slugify markdown gubi ą/ę/ł…)."""
    t = tekst.replace("ł", "l").replace("Ł", "L")
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[\s-]+", sep, re.sub(r"[^\w\s-]", "", t).strip().lower()) or "sekcja"


def zloz_html(r: Raport, rozdzialy: Path = ROZDZIALY, tytul: str = TYTUL_RAPORTU, towarzyszy: str | None = None) -> str:
    """Samodzielny HTML dokumentu z rozdziałów `rozdzialy/*.md` (kolejność nazw); `tytul` – okładka, tytuł i stopka,
    `towarzyszy` – tytuł raportu, do którego dokument jest dodatkiem (linia na okładce)."""
    bloki: list[str] = []

    def wstaw(rejestr: dict, rodzaj: str, nazwa: str, *args, **kw) -> Markup:
        if nazwa not in rejestr:
            raise KeyError(f"Nieznany {rodzaj} „{nazwa}” (zarejestrowane: {', '.join(sorted(rejestr)) or 'brak'})")
        bloki.append(rejestr[nazwa](r, *args, **kw))
        return Markup(f"\n\n@@BLOK{len(bloki) - 1}@@\n\n")

    env = jinja2.Environment(undefined=jinja2.StrictUndefined, autoescape=False, keep_trailing_newline=True)
    kontekst = {
        "r": r, "liczba": liczba, "procent": procent, "przedzial": przedzial,
        # fakty z danych do prozy: wiersz uczestnika, suma bez T6, wycinki przewagi innych uczestników nad Privatizerem
        "wiersz": wiersz, "suma_bez_szybkosci": suma_bez_szybkosci, "przewagi": przewagi, "wagi_testow": wagi_testow, "ile": ile, "liczba_przewag": liczba_przewag, "zestawy_wag": ZESTAWY_WAG, "n_kategorie": KATEGORIE_N, "maks_punktow": maks_punktow,
        # kontrola domen zarezerwowanych: wstawki liczbowe i decyzje szablonu z danych (brak wyniku → sekcja pomijana)
        "przedzial_procent": przedzial_procent, "roznica_pp": roznica_pp, "roznica": roznica, "porownanie_trybow": porownanie_trybow, "liczebnosc_domen": liczebnosc_domen, "pozycja_szybkosci": pozycja_szybkosci, "prywatizer": prywatizer, "przewaga_domen": przewaga_domen, "sygnaly_domen": sygnaly_domen, "domeny_wiersz": domeny_wiersz, "zmiana_rankingu": zmiana_rankingu,
        # stałe metodyki i opisu korpusu (`liczby_opisowe.toml`), kontaminacja 8-gramów, wagi z `wagi_punktow.json`, uczestnicy z pamięcią bliską limitu RAM-u
        "m": liczby_opisowe(), "kont": kontaminacja(), "wagi_punktow": wagi_punktow(), "pamiec_wysoka": pamiec_wysoka, "czas_podsumowanie_wg_pamieci": czas_podsumowanie_wg_pamieci, "repozytorium": REPOZYTORIUM,
        "tabela": lambda nazwa, *a, **kw: wstaw(TABELE, "tabela", nazwa, *a, **kw),
        "wykres": lambda nazwa, *a, **kw: wstaw(WYKRESY, "wykres", nazwa, *a, **kw),
    }
    pliki = sorted(Path(rozdzialy).glob("*.md"))
    zrodlo = "\n\n".join(env.from_string(p.read_text(encoding="utf-8")).render(**kontekst) for p in pliki)
    md = markdown.Markdown(extensions=["tables", "toc", "attr_list", "sane_lists", "fenced_code"],
                           extension_configs={"toc": {"slugify": _slug}})
    tresc = _BLOK.sub(lambda m: bloki[int(m.group(1))], md.convert(zrodlo))
    spis = [{"poziom": 1 if t["level"] == 1 else 2, "id": t["id"], "tytul": _html.unescape(re.sub(r"<[^>]+>", "", t["name"]))}
            for glowny in md.toc_tokens for t in [glowny, *glowny.get("children", [])] if t["level"] <= 2]
    logo = Markup(LOGO.read_text(encoding="utf-8"))
    okladka = env.from_string((SZABLON / "okladka.html.j2").read_text(encoding="utf-8")).render(logo=logo, daty=liczby_opisowe()["daty"], tytul=tytul, towarzyszy=towarzyszy)
    szablon = env.from_string((SZABLON / "raport.html.j2").read_text(encoding="utf-8"))
    # stopka strony jest w `@page` (CSS), więc tytuł dokumentu podstawiamy w jej treści
    druk = (SZABLON / "druk.css").read_text(encoding="utf-8")
    if f"– {TYTUL_RAPORTU} · s." not in druk:
        raise ValueError("druk.css: brak tytułu raportu w stopce `@page` – podmiana tytułu dokumentu by nie zadziałała")
    druk = druk.replace(f"– {TYTUL_RAPORTU} · s.", f"– {tytul} · s.")
    return szablon.render(css=_fonty_css() + "\n" + druk, tytul=tytul,
                          okladka=Markup(okladka), tresc=Markup(tresc), spis=spis)


def _chromium(pw) -> str | None:
    """Ścieżka do Chromium z `~/.cache/ms-playwright` bez pobierania: domyślna dla wersji pakietu, a gdy jej nie ma – najnowszy zainstalowany
    build (PDF z Chromium działa między pobliskimi wersjami). Nadpisanie: `RAPORT_CHROMIUM`."""
    if os.environ.get("RAPORT_CHROMIUM"):
        return os.environ["RAPORT_CHROMIUM"]
    domyslna = Path(pw.chromium.executable_path)
    if domyslna.exists():
        return None
    cache = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or Path.home() / ".cache" / "ms-playwright")
    buildy = sorted(cache.glob("chromium-*/chrome-linux*/chrome"), key=lambda p: int(p.parts[-3].split("-")[1]), reverse=True)
    if not buildy:
        raise RuntimeError("Brak Chromium w ~/.cache/ms-playwright – uruchom `uv run --group raport playwright install chromium`")
    return str(buildy[0])


def drukuj_pdf(html: str, cel: Path) -> None:
    """HTML → PDF A4 w Chromium: marginesy i stopka z `@page` w druk.css (`prefer_css_page_size`), zakładki PDF z nagłówków."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        przegladarka = pw.chromium.launch(executable_path=_chromium(pw), args=["--no-sandbox"])
        try:
            strona = przegladarka.new_page()
            strona.set_content(html, wait_until="load")
            strona.evaluate("document.fonts.ready")
            strona.pdf(path=str(cel), format="A4", print_background=True, prefer_css_page_size=True, outline=True, tagged=True)
        finally:
            przegladarka.close()


def buduj(wyniki: Path, cel: Path, html: Path | None = None, czas: Path | None = None,
          rozdzialy: Path = ROZDZIALY, publikacja: bool = False, tytul: str = TYTUL_RAPORTU, towarzyszy: str | None = None) -> Path:
    """Kontrola źródeł → HTML → PDF → kontrola tekstu PDF. Błąd kontroli = `BladKontroli`."""
    bledy = kontroluj_zrodla(rozdzialy, publikacja)
    if bledy:
        raise BladKontroli(bledy)
    if not publikacja:
        for ostrzezenie in znaczniki_zrodel(rozdzialy):
            print(f"OSTRZEŻENIE {ostrzezenie}: znacznik weryfikacji (w publikacji = błąd)", file=sys.stderr)
    tresc = zloz_html(wczytaj(wyniki, czas), rozdzialy, tytul, towarzyszy)
    if html:
        Path(html).write_text(tresc, encoding="utf-8")
    cel = Path(cel)
    cel.parent.mkdir(parents=True, exist_ok=True)
    # Skład do pliku tymczasowego obok celu: kontrola PDF przed podmianą, więc nieudany build nie nadpisuje poprzedniego dobrego PDF-a.
    tymczasowy = cel.with_name(f".{cel.stem}.tmp{cel.suffix}")
    try:
        drukuj_pdf(tresc, tymczasowy)
        bledy = kontroluj_pdf(tymczasowy, publikacja)
        if bledy:
            raise BladKontroli([b.replace(tymczasowy.name, cel.name, 1) for b in bledy])
        os.replace(tymczasowy, cel)
    finally:
        tymczasowy.unlink(missing_ok=True)
    return cel


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="raport.buduj", description=__doc__.splitlines()[0])
    ap.add_argument("--wyniki", type=Path, required=True, help="katalog zbiorczy z wynikami (glowne.csv …)")
    ap.add_argument("--cel", type=Path, required=True, help="plik wynikowy PDF")
    ap.add_argument("--html", type=Path, help="zapisz też samodzielny HTML")
    ap.add_argument("--cel-aneks", type=Path, help="zbuduj też aneks liczbowy jako osobny PDF")
    ap.add_argument("--html-aneks", type=Path, help="zapisz też samodzielny HTML aneksu (wymaga --cel-aneks)")
    ap.add_argument("--czas", type=Path, help="katalog czas-m1 (domyślnie sąsiedni do --wyniki)")
    ap.add_argument("--publikacja", action="store_true", help="znaczniki [NIEZWERYFIKOWANE]/[HIPOTEZA] są błędem")
    a = ap.parse_args(argv)
    if a.html_aneks and not a.cel_aneks:
        ap.error("--html-aneks wymaga --cel-aneks")
    try:
        cel = buduj(a.wyniki, a.cel, a.html, a.czas, ROZDZIALY, a.publikacja)
        print(f"OK: {cel}")
        if a.cel_aneks:
            cel = buduj(a.wyniki, a.cel_aneks, a.html_aneks, a.czas, ANEKS, a.publikacja, TYTUL_ANEKSU, TYTUL_RAPORTU)
            print(f"OK: {cel}")
    except BladKontroli as e:
        print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
