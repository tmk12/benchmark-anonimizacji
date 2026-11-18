"""Wykresy raportu (matplotlib → SVG, tekst jako tekst, czcionka IBM Plex Sans z osadzonego fontu strony).

Każdy wykres: `(r: Raport, …) -> str` (SVG do wstawienia inline); rejestr `WYKRESY_FUNKCJE` zasila `buduj.WYKRESY`.
SVG deterministyczny (`svg.hashsalt` = nazwa wykresu, bez daty). Serie różnią się wzorem (hatch), nie tylko kolorem – czytelne w druku cz.-b.
Wartość nieliczona (None) nie ma słupka/kafelka koloru, tylko adnotację „n/d”."""
from __future__ import annotations

import io
import math
import re
from typing import Callable

import matplotlib
from matplotlib.figure import Figure
from matplotlib.patches import Patch, Rectangle
from matplotlib.ticker import FuncFormatter, LogLocator

from raport.dane import ND, TESTY, TRYBY, Raport, Wiersz, etykieta_miejsca, kategorie_trybow, liczba, maks_punktow, prywatizer as _prywatizer, procent, sekundy, wiersze_podsumowania

matplotlib.rcParams["svg.fonttype"] = "none"  # tekst zostaje tekstem (font strony), nie obrysami

# Paleta: tokeny z `:root` aplikacji (lgprivatizer/static/style.css), wartości przepisane.
INK = "#16223D"        # --ink: granat (Privatizer)
INK_2 = "#223157"      # --ink-2
INK_SOFT = "#8FA3C8"   # --ink-soft (pozostali uczestnicy)
LINE = "#DCE1EA"       # --line
CONTROL = "#76819A"    # --control
TEXT = "#1B2336"       # --text
MUTED = "#5E6A82"      # --muted
MARKER = "#FFD24A"     # --marker
OK = "#17724B"         # --ok
DANGER = "#B3382F"     # --danger
FOCUS = "#3D6FE0"      # --focus
PAPER = "#FFFFFF"      # --paper

KATEGORIE_N = 5  # ilu najlepszych uczestników pokazuje mapa kategorii (też do prozy rozdziału)
FONT = "IBM Plex Sans"
SZEROKOSC = 6.5  # cale; szerokość bloku tekstu A4

# Wzory serii (kolejno dla kolejnych serii; wszystkie różne). Kolory i wzory razem rozróżniają serie w druku cz.-b.
WZORY = ["//", "\\\\", "xx", "..", "++", "--", "oo", "||", "**", "///", "\\\\\\", "xxx", "OO"]
KOLORY_SERII = [INK, FOCUS, OK, MARKER, DANGER, INK_SOFT, CONTROL, INK_2, MUTED, "#6FA98A", "#E39A92", "#9DB6F0", LINE]
_CIEMNE = {INK, FOCUS, OK, DANGER, INK_2, MUTED, CONTROL}


def _liczba_krotka(v: float) -> str:
    return f"{v:g}".replace(".", ",")


def _nowa(wysokosc: float):
    fig = Figure(figsize=(SZEROKOSC, max(wysokosc, 1.6)), dpi=100)
    fig.patch.set_facecolor(PAPER)
    return fig


def _osie(fig, **kw):
    ax = fig.add_subplot(1, 1, 1, **kw)
    ax.set_facecolor(PAPER)
    for bok in ("top", "right"):
        ax.spines[bok].set_visible(False)
    for bok in ("left", "bottom"):
        ax.spines[bok].set_color(CONTROL)
    ax.tick_params(colors=TEXT, labelsize=8, length=3)
    ax.xaxis.label.set_color(TEXT)
    return ax


def _svg(fig, nazwa: str) -> str:
    """Figura → SVG inline: deterministycznie, bez deklaracji XML, skalowalne do szerokości bloku."""
    bufor = io.BytesIO()
    with matplotlib.rc_context({"svg.hashsalt": f"raport-{nazwa}", "font.family": [FONT, "DejaVu Sans"], "svg.fonttype": "none",
                                "hatch.linewidth": 0.6}):
        fig.savefig(bufor, format="svg", metadata={"Date": None, "Creator": "raport"})
    svg = bufor.getvalue().decode("utf-8")
    svg = svg[svg.index("<svg"):]
    # Układ liczy się na metrykach zapasowej czcionki (Plex nie jest zainstalowany jako ttf); w SVG ma być font strony.
    svg = re.sub(r"font-family: [^;\"]*", "font-family: 'IBM Plex Sans', sans-serif", svg)
    svg = re.sub(r'(<svg\b[^>]*?)\swidth="[^"]*"\s+height="[^"]*"', r'\1 style="width:100%;height:auto"', svg, count=1)
    return svg


def _pusty(nazwa: str, napis: str) -> str:
    fig = _nowa(1.6)
    fig.text(0.5, 0.5, napis, ha="center", va="center", fontsize=10, color=MUTED, family=FONT)
    return _svg(fig, nazwa)


def _nd(ax, x, y, **kw):
    ax.text(x, y, ND, ha=kw.pop("ha", "left"), va="center", fontsize=8, color=MUTED, style="italic", **kw)


def _kolor_tekstu(tlo: str) -> str:
    r, g, b = (int(tlo[i:i + 2], 16) for i in (1, 3, 5))
    return PAPER if 0.299 * r + 0.587 * g + 0.114 * b < 140 else TEXT


def _wiersze(r: Raport, ranking: str) -> list[Wiersz]:
    return sorted(r.rankingi.get(ranking, []), key=lambda w: (w.miejsce is None, w.miejsce or 0, w.uczestnik))


def _etykieta(w: Wiersz, wiersze: list[Wiersz]) -> str:
    miejsce = etykieta_miejsca(w, wiersze).replace(" (remis)", "")
    return f"{miejsce}. {w.uczestnik}"


def _legenda_privatizer(ax, pod_osia: bool = False):
    uchwyty = [Patch(facecolor=INK, edgecolor=INK, label="Privatizer"),
               Patch(facecolor=INK_SOFT, edgecolor=TEXT, hatch="//", label="pozostali uczestnicy")]
    if pod_osia:
        ax.legend(handles=uchwyty, loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=2, fontsize=8, frameon=False)
    else:
        ax.legend(handles=uchwyty, loc="lower right", fontsize=8, frameon=False)


# ---------------------------------------------------------------- rankingi

def ranking(r: Raport, ranking: str = "tekst") -> str:
    """Suma punktów z przedziałem ufności; Privatizer – pełny granat, reszta – jasny z kreskowaniem."""
    nazwa = f"ranking_{ranking}"
    wiersze = _wiersze(r, ranking)
    if not wiersze:
        return _pusty(nazwa, f"Ranking „{ranking}”: {ND}")
    fig = _nowa(0.34 * len(wiersze) + 0.9)
    ax = _osie(fig)
    gora = max([w.suma_ci[1] for w in wiersze if w.suma_ci[1] is not None] + [w.suma for w in wiersze if w.suma is not None] + [1])
    for i, w in enumerate(wiersze):
        if w.suma is None:
            _nd(ax, gora * 0.01, i)
            continue
        pr = _prywatizer(w.uczestnik)
        ax.barh(i, w.suma, height=0.62, color=INK if pr else INK_SOFT, edgecolor=INK if pr else TEXT,
                hatch=None if pr else "//", linewidth=0.5, zorder=2)
        ci = w.suma_ci
        if ci[0] is not None and ci[1] is not None:
            ax.errorbar(w.suma, i, xerr=[[max(w.suma - ci[0], 0)], [max(ci[1] - w.suma, 0)]], fmt="none", ecolor=TEXT,
                        elinewidth=1, capsize=2.5, zorder=3)
        ax.text(max(ci[1] or w.suma, w.suma) + gora * 0.012, i, liczba(w.suma, 1), va="center", fontsize=8, color=TEXT)
    ax.set_yticks(range(len(wiersze)), [_etykieta(w, wiersze) for w in wiersze])
    ax.invert_yaxis()
    ax.set_xlim(0, gora * 1.12)
    ax.set_xlabel("Suma punktów (z 95% przedziałem ufności)", fontsize=8)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: liczba(v, 0)))
    ax.grid(axis="x", color=LINE, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    _legenda_privatizer(ax)
    fig.tight_layout()
    return _svg(fig, nazwa)


def podsumowanie(r: Raport) -> str:
    """Oba rankingi w skrócie (te same wiersze co tabela podsumowania): sumy z przedziałem ufności, Privatizer – pełny granat, reszta – kreskowana."""
    grupy = [(ranking, wiersze_podsumowania(r, ranking)) for ranking in ("tekst", "pliki")]
    grupy = [(ranking, w) for ranking, w in grupy if w]
    if not grupy:
        return _pusty("podsumowanie", f"Podsumowanie: {ND}")
    # pozycje y: nagłówek grupy, jej wiersze, odstęp
    pozycje, naglowki, y = [], [], 0.0
    for ranking, wiersze in grupy:
        naglowki.append((y, f"Ranking {ranking} (maks. {liczba(maks_punktow(ranking), 0)} pkt)"))
        y += 1.0
        for w in wiersze:
            pozycje.append((y, w, _etykieta(w, r.rankingi[ranking])))
            y += 1.0
        y += 0.5
    fig = _nowa(0.22 * y + 0.7)
    ax = _osie(fig)
    gora = max([w.suma_ci[1] for _, w, _ in pozycje if w.suma_ci[1] is not None] + [w.suma for _, w, _ in pozycje if w.suma is not None] + [1])
    for yy, w, _ in pozycje:
        if w.suma is None:
            _nd(ax, gora * 0.01, yy)
            continue
        pr = _prywatizer(w.uczestnik)
        ax.barh(yy, w.suma, height=0.62, color=INK if pr else INK_SOFT, edgecolor=INK if pr else TEXT, hatch=None if pr else "//", linewidth=0.5, zorder=2)
        ci = w.suma_ci
        if ci[0] is not None and ci[1] is not None:
            ax.errorbar(w.suma, yy, xerr=[[max(w.suma - ci[0], 0)], [max(ci[1] - w.suma, 0)]], fmt="none", ecolor=TEXT, elinewidth=1, capsize=2.5, zorder=3)
        ax.text(max(ci[1] or w.suma, w.suma) + gora * 0.012, yy, liczba(w.suma, 1), va="center", fontsize=8, color=TEXT)
    for yy, napis in naglowki:
        ax.text(0, yy, napis, va="center", ha="left", fontsize=8, fontweight="bold", color=TEXT)
    ax.set_yticks([p[0] for p in pozycje], [p[2] for p in pozycje])
    ax.set_ylim(y - 0.5, -0.6)
    ax.set_xlim(0, gora * 1.12)
    ax.set_xlabel("Suma punktów (z 95% przedziałem ufności)", fontsize=8)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: liczba(v, 0)))
    ax.grid(axis="x", color=LINE, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    _legenda_privatizer(ax)
    fig.tight_layout()
    return _svg(fig, "podsumowanie")


def skladniki(r: Raport, ranking: str = "tekst") -> str:
    """Skumulowane punkty poszczególnych testów (T1…, P1…); każdy test ma własny wzór i kolor."""
    nazwa = f"skladniki_{ranking}"
    wiersze = _wiersze(r, ranking)
    testy = [t for t in TESTY if any(w.testy[t].pkt is not None for w in wiersze)]
    if not wiersze or not testy:
        return _pusty(nazwa, f"Składniki rankingu „{ranking}”: {ND}")
    fig = _nowa(0.34 * len(wiersze) + 1.35)
    ax = _osie(fig)
    lewo = [0.0] * len(wiersze)
    for k, t in enumerate(testy):
        kolor = KOLORY_SERII[k % len(KOLORY_SERII)]
        dlugosci = [w.testy[t].pkt or 0.0 for w in wiersze]  # None = n/d → brak odcinka (adnotacja poniżej)
        ax.barh(range(len(wiersze)), dlugosci, left=lewo, height=0.62, color=kolor, edgecolor=PAPER if kolor in _CIEMNE else TEXT,
                hatch=WZORY[k], linewidth=0.4, zorder=2)
        lewo = [a + b for a, b in zip(lewo, dlugosci)]
    gora = max(lewo + [1])
    for i, w in enumerate(wiersze):
        brak = [t for t in testy if w.testy[t].pkt is None]
        napis = liczba(w.suma, 1) if w.suma is not None else ND
        if brak:
            napis += f"  (n/d: {', '.join(brak)})"
        ax.text(lewo[i] + gora * 0.012, i, napis, va="center", fontsize=7.5, color=TEXT)
    ax.set_yticks(range(len(wiersze)), [_etykieta(w, wiersze) for w in wiersze])
    ax.invert_yaxis()
    ax.set_xlim(0, gora * 1.28)
    ax.set_xlabel("Punkty (suma składników)", fontsize=8)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: liczba(v, 0)))
    ax.grid(axis="x", color=LINE, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    uchwyty = [Patch(facecolor=KOLORY_SERII[k % len(KOLORY_SERII)], edgecolor=PAPER if KOLORY_SERII[k % len(KOLORY_SERII)] in _CIEMNE else TEXT,
                     hatch=WZORY[k], label=t) for k, t in enumerate(testy)]
    ax.legend(handles=uchwyty, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=min(len(testy), 7), fontsize=8, frameon=False)
    fig.tight_layout()
    return _svg(fig, nazwa)


# ---------------------------------------------------------------- mapy cieplne

def _mapa(nazwa: str, wiersze_etykiety: list[str], kolumny: list[str], wartosci: dict, jasny: str, ciemny: str, kolumny_pogrubione: set[str] | None = None,
          wiersze_pogrubione: set[str] | None = None, tytul_osi: str = "", przypis: str = "", obrot: int = 0) -> str:
    """Siatka kafelków: kolor rośnie z wartością (jasny→ciemny), liczba w środku; None = kafelek ze wzorem i „n/d”."""
    lj = [int(jasny[i:i + 2], 16) for i in (1, 3, 5)]
    lc = [int(ciemny[i:i + 2], 16) for i in (1, 3, 5)]
    fig = _nowa(0.32 * len(wiersze_etykiety) + (1.1 if not obrot else 1.6) + (0.3 if przypis else 0))
    ax = _osie(fig)
    for i, w in enumerate(wiersze_etykiety):
        for j, k in enumerate(kolumny):
            v = wartosci.get((w, k))
            if v is None:
                ax.add_patch(Rectangle((j, i), 1, 1, facecolor=LINE, edgecolor=PAPER, hatch="xx", linewidth=1.2))
                ax.text(j + 0.5, i + 0.5, ND, ha="center", va="center", fontsize=8, color=TEXT, style="italic")
                continue
            t = min(max(v, 0.0), 1.0)
            tlo = "#" + "".join(f"{round(a + (b - a) * t):02X}" for a, b in zip(lj, lc))
            ax.add_patch(Rectangle((j, i), 1, 1, facecolor=tlo, edgecolor=PAPER, linewidth=1.2))
            ax.text(j + 0.5, i + 0.5, procent(v, 0), ha="center", va="center", fontsize=8, color=_kolor_tekstu(tlo))
    ax.set_xlim(0, len(kolumny))
    ax.set_ylim(len(wiersze_etykiety), 0)
    ax.set_xticks([j + 0.5 for j in range(len(kolumny))], kolumny, rotation=obrot, ha="left" if obrot else "center",
                  rotation_mode="anchor" if obrot else "default")
    ax.set_yticks([i + 0.5 for i in range(len(wiersze_etykiety))], wiersze_etykiety)
    ax.xaxis.tick_top()
    ax.tick_params(length=0)
    for etykieta in ax.get_xticklabels():
        if kolumny_pogrubione and etykieta.get_text() in kolumny_pogrubione:
            etykieta.set_fontweight("bold")
    for etykieta in ax.get_yticklabels():
        if wiersze_pogrubione and etykieta.get_text() in wiersze_pogrubione:
            etykieta.set_fontweight("bold")
    for bok in ax.spines.values():
        bok.set_visible(False)
    if tytul_osi:
        ax.set_xlabel(tytul_osi, fontsize=8)
    if przypis:
        fig.text(0.01, 0.01, przypis, fontsize=7.5, color=MUTED, va="bottom", ha="left")
    fig.tight_layout(rect=(0, 0.05 if przypis else 0, 1, 1))
    return _svg(fig, nazwa)


def jezyki(r: Raport, ranking: str = "tekst") -> str:
    """Mapa uczestnicy × język (pl, en, es, de, fr): odsetek dokumentów bez wycieku (ważony) – jak T1 per język."""
    wiersze = _wiersze(r, ranking)
    jezyki_ = ["pl", "en", "es", "de", "fr"]
    if not wiersze:
        return _pusty("jezyki", f"Języki, ranking „{ranking}”: {ND}")
    wart = {}
    for k in r.per.get("jezyk", []):
        if k["ranking"] == ranking:
            wart[(k["uczestnik"], k["jezyk"])] = k.get("bez_wycieku_wazone")
    nazwy = [w.uczestnik for w in wiersze]
    return _mapa("jezyki", nazwy, jezyki_, wart, "#EEF1F6", INK, wiersze_pogrubione={u for u in nazwy if _prywatizer(u)})


def kategorie(r: Raport, ranking: str = "tekst", n: int = KATEGORIE_N, wiersze_max: int = 16) -> str:
    """Mapa kategorie wycieków × `n` najlepszych uczestników rankingu: odsetek wyciekłych wartości (ciemniej = gorzej);
    `wiersze_max` kategorii o najwyższym średnim odsetku, resztę zlicza przypis."""
    wiersze = _wiersze(r, ranking)[:n]
    kat = {}
    for k in r.per.get("kategoria", []):
        if k["ranking"] == ranking:
            kat[(k["kategoria"], k["uczestnik"])] = k.get("odsetek_wyciekow")
    nazwy = [w.uczestnik for w in wiersze]
    kategorie_ = sorted({k for k, _ in kat}, key=lambda c: (-(sum(kat.get((c, u)) or 0 for u in nazwy) / max(len(nazwy), 1)), c))
    if not nazwy or not kategorie_:
        return _pusty("kategorie", f"Kategorie wycieków, ranking „{ranking}”: {ND}")
    pominiete = max(len(kategorie_) - wiersze_max, 0)
    return _mapa("kategorie", kategorie_[:wiersze_max], nazwy, kat, "#FFF3C4", DANGER, kolumny_pogrubione={u for u in nazwy if _prywatizer(u)},
                 przypis=f"Pominięto {pominiete} kat. o niższym średnim odsetku wycieków." if pominiete else "", obrot=25)


# ---------------------------------------------------------------- szybkość i tryby

def szybkosc(r: Raport, ranking: str = "tekst") -> str:
    """Sekundy na stronę (skala logarytmiczna), linia odniesienia t_ref = 1,0 s/stronę; brak pomiaru = „n/d” bez słupka."""
    nazwa = "szybkosc"
    w_rankingu = {w.uczestnik for w in r.rankingi.get(ranking, [])}
    czasy = {c["uczestnik"]: c.get("s_na_strone") for c in r.czas if c["ranking"] == ranking and (not w_rankingu or c["uczestnik"] in w_rankingu)}
    if not czasy:
        return _pusty(nazwa, f"Szybkość, ranking „{ranking}”: {ND}")
    kolejnosc = sorted(czasy, key=lambda u: (czasy[u] is None, czasy[u] or 0, u))
    liczone = [v for v in czasy.values() if v is not None and v > 0]
    dol = 10 ** math.floor(math.log10(min(liczone + [1.0]))) / 2
    gora = 10 ** math.ceil(math.log10(max(liczone + [1.0]) * 1.5))
    fig = _nowa(0.34 * len(kolejnosc) + 1.4)
    ax = _osie(fig)
    ax.set_xscale("log")
    ax.set_xlim(dol, gora)
    for i, u in enumerate(kolejnosc):
        v = czasy[u]
        if v is None or v <= 0:
            _nd(ax, dol * 1.15, i)
            continue
        pr = _prywatizer(u)
        ax.barh(i, v - dol, left=dol, height=0.62, color=INK if pr else INK_SOFT, edgecolor=INK if pr else TEXT,
                hatch=None if pr else "//", linewidth=0.5, zorder=2)
        ax.text(v * 1.12, i, sekundy(v), va="center", fontsize=8, color=TEXT)
    ax.axvline(1.0, color=DANGER, linewidth=1.2, linestyle=(0, (4, 2)), zorder=3)
    ax.text(1.0 * 1.08, 0, "t_ref = 1,0 s/stronę", color=DANGER, fontsize=8, va="center")
    ax.set_yticks(range(len(kolejnosc)), kolejnosc)
    ax.set_ylim(len(kolejnosc) - 0.4 + 0.5, -0.6)
    ax.xaxis.set_major_locator(LogLocator(base=10, subs=(1.0,), numticks=12))  # tylko dekady – bez powtórzonych etykiet
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: liczba(v, max(0, -math.floor(math.log10(v)))) if v > 0 else ""))
    ax.xaxis.set_minor_formatter(FuncFormatter(lambda v, _: ""))
    ax.set_xlabel("Sekundy na stronę (skala logarytmiczna)", fontsize=8)
    ax.grid(axis="x", color=LINE, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    _legenda_privatizer(ax, pod_osia=True)
    fig.tight_layout()
    return _svg(fig, nazwa)


def tryby(r: Raport, ranking: str = "tekst") -> str:
    """Odsetek wyciekłych wartości per kategoria: tryb domyślny (pełny) vs „Maksymalna ochrona” (kreskowany); brak wartości = „n/d”."""
    nazwa = "tryby"
    if ranking not in TRYBY:
        return _pusty(nazwa, f"Tryby, ranking „{ranking}”: {ND}")
    domyslny, maks = TRYBY[ranking]
    kat = {u: {c: k.get("odsetek_wyciekow") for c, k in kk.items()} for u, kk in kategorie_trybow(r, ranking).items()}
    kategorie_ = sorted(set(kat[domyslny]) | set(kat[maks]), key=lambda c: (kat[domyslny].get(c) is None, -(kat[domyslny].get(c) or 0), c))
    if not kategorie_:
        return _pusty(nazwa, f"Tryby, ranking „{ranking}”: {ND}")
    # kategorie bez wycieku w obu trybach nie wnoszą nic do wykresu – zlicza je przypis (n/d zostaje widoczne)
    puste = [c for c in kategorie_ if kat[domyslny].get(c) == 0 and kat[maks].get(c) == 0]
    kategorie_ = [c for c in kategorie_ if c not in puste]
    if not kategorie_:
        return _pusty(nazwa, f"Tryby, ranking „{ranking}”: brak wycieków w obu trybach")
    fig = _nowa(0.42 * len(kategorie_) + 1.4)
    ax = _osie(fig)
    wys = 0.36
    gora = max([v for d in kat.values() for v in d.values() if v is not None] + [0.01])
    for i, c in enumerate(kategorie_):
        for przesuniecie, u, kolor, wzor, kr in ((-wys / 2, domyslny, INK, None, INK), (wys / 2, maks, INK_SOFT, "//", TEXT)):
            v = kat[u].get(c)
            y = i + przesuniecie
            if v is None:
                _nd(ax, gora * 0.01, y)
                continue
            ax.barh(y, v, height=wys * 0.94, color=kolor, edgecolor=kr, hatch=wzor, linewidth=0.5, zorder=2)
            ax.text(v + gora * 0.012, y, procent(v, 1), va="center", fontsize=7.5, color=TEXT)
    ax.set_yticks(range(len(kategorie_)), kategorie_)
    ax.set_ylim(len(kategorie_) - 0.5, -0.5)
    ax.set_xlim(0, gora * 1.15)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: procent(v, 0)))
    ax.set_xlabel("Odsetek wyciekłych wartości w kategorii", fontsize=8)
    ax.grid(axis="x", color=LINE, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(handles=[Patch(facecolor=INK, edgecolor=INK, label="tryb domyślny"),
                       Patch(facecolor=INK_SOFT, edgecolor=TEXT, hatch="//", label="Maksymalna ochrona")],
              loc="lower right", fontsize=8, frameon=False)
    if puste:
        fig.text(0.01, 0.01, f"Pominięto {len(puste)} kat. bez wycieku w obu trybach.", fontsize=7.5, color=MUTED, va="bottom", ha="left")
    fig.tight_layout(rect=(0, 0.05 if puste else 0, 1, 1))
    return _svg(fig, nazwa)


# Rejestr dla `buduj.WYKRESY`: nazwa → `(r, *args, **kw) -> str`.
WYKRESY_FUNKCJE: dict[str, Callable[..., str]] = {
    "ranking_tekst": lambda r, *a, **kw: ranking(r, "tekst", *a, **kw),
    "ranking_pliki": lambda r, *a, **kw: ranking(r, "pliki", *a, **kw),
    "podsumowanie": podsumowanie,
    "skladniki_tekst": lambda r, *a, **kw: skladniki(r, "tekst", *a, **kw),
    "skladniki_pliki": lambda r, *a, **kw: skladniki(r, "pliki", *a, **kw),
    "jezyki": jezyki,
    "szybkosc": szybkosc,
    "tryby": tryby,
    "kategorie": kategorie,
}
