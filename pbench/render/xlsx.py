"""Renderer XLSX: lista płac/rejestr jako arkusz, komentarze komórek, nagłówek i stopka wydruku, ukryty arkusz,
właściwości dokumentu i nazwy arkuszy z danymi.

Wejście to `Dokument` przycięty przez `przytnij_dla("xlsx", …)`; renderer rysuje WSZYSTKIE jego elementy, a
`utrudnienia` steruje wyłącznie formą. Zwracana lista `Wartosc` jest autorytatywna (`miejsce` = gdzie wartość leży).

Układ: komórki tabel szablonu to komórki arkusza (kolumna = kolumna tabeli, kolejne tabele jedna pod drugą);
akapity spoza tabel to komórki kolumny A NAD tabelą, podpis i stopka (bez `naglowek_wydruku`) – pod nią. Wszystkie
teksty są łańcuchami (także PESEL i kwoty), żeby wartość w pliku była dokładnie wartością wzorcową.

Gdzie co leży: komórki – `xl/sharedStrings.xml` (miejsce „tresc”/„tabela”; ukryty arkusz to ta sama część, tylko
inny `sheetN.xml`); komentarze – `xl/comments/comment*.xml` (autor w `<authors>`, miejsce „komentarz”); nagłówek i
stopka wydruku – `<headerFooter>` w `xl/worksheets/sheet*.xml` („naglowek”/„stopka”; `&` zapisane jako `&&`, jak w
Excelu); właściwości – `docProps/core.xml` (creator, lastModifiedBy, title, subject), `docProps/custom.xml` (pozostałe
klucze), `docProps/app.xml` (`<Company>` – kopia nazwy firmy z nagłówka, miejsce „metadane”) i nazwy arkuszy w
`xl/workbook.xml` (miejsce „metadane”, kopia osoby albo firmy z dokumentu).

Ukryty arkusz (`arkusz_ukryty`): ok. 30% ostatnich wierszy największej tabeli (z powtórzonym nagłówkiem kolumn, jeśli
nie zawiera wartości) albo ostatnie akapity, gdy tabeli nie ma. Dla dokumentu zbyt małego, by cokolwiek przenieść,
arkusz nie powstaje. Arkusz ukryty zachowuje „tabela”/„tresc” – format nie ma osobnego miejsca dla ukrytych danych.
"""
from __future__ import annotations

import io
import re
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.packaging.custom import StringProperty
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from ..model import Dokument, Element, Wartosc
from ..utrudnienia import UTRUDNIENIA_POMINIETE, UTRUDNIENIA_XLSX
from . import wspolne

NAZWA_ARKUSZA = {"pl": "Arkusz", "en": "Sheet", "es": "Hoja", "de": "Tabelle", "fr": "Feuil", "uk": "Аркуш"}
PREFIKS_WYCIAG = {"pl": "Wyciąg", "en": "Extract", "es": "Extracto", "de": "Auszug", "fr": "Extrait", "uk": "Витяг"}
STRONA = {"pl": "Strona", "en": "Page", "es": "Página", "de": "Seite", "fr": "Page", "uk": "Сторінка"}
NIEDOZWOLONE_W_NAZWIE = re.compile(r"[\\/?*\[\]:]")
UDZIAL_UKRYTYCH = 0.3
SZEROKOSC_MAX = 60
_NAGLOWEK = Font(bold=True)
_TLO_NAGLOWKA = PatternFill("solid", fgColor="E7E6E6")


class _Ctx:
    def __init__(self, d: Dokument) -> None:
        self.d = d
        self.rng = wspolne.rng_dokumentu(d)
        self.wartosci: list[Wartosc] = []

    def zapisz(self, w: Wartosc, miejsce: str) -> Wartosc:
        z = wspolne.zapisz_jako(w, miejsce)
        self.wartosci.append(z)
        return z

    def tekst(self, fragmenty: list[str | Wartosc], miejsce: str) -> str:
        """Skleja fragmenty w tekst komórki i zapisuje wartości wzorcowe."""
        return "".join(f if isinstance(f, str) else self.zapisz(f, miejsce).tekst for f in fragmenty)


def _ustaw(ws: Worksheet, wiersz: int, kolumna: int, tekst: str) -> None:
    c = ws.cell(row=wiersz, column=kolumna)
    c.value = tekst
    if tekst.startswith("="):  # tekst, nie formuła
        c.data_type = "s"


def _tabele(d: Dokument) -> dict[int, dict[int, dict[int, list[Element]]]]:
    wynik: dict[int, dict[int, dict[int, list[Element]]]] = {}
    for e in d.elementy:
        if e.rodzaj == "komorka":
            a = e.atrybuty
            wynik.setdefault(a["tabela"], {}).setdefault(a["wiersz"], {}).setdefault(a["kolumna"], []).append(e)
    return wynik


def _komorka(ctx: _Ctx, elementy: list[Element]) -> str:
    return "\n".join(ctx.tekst(e.fragmenty, "tabela") for e in elementy)


def _naglowek_wydruku(ctx: _Ctx, arkusze: list[Worksheet], naglowki: list[Element], stopki: list[Element]) -> None:
    """Ten sam nagłówek i stopka na każdym arkuszu; wartości zapisane raz (to samo wystąpienie w pliku)."""
    def sklej(elementy: list[Element], miejsce: str) -> str:
        return "\n".join(ctx.tekst(e.fragmenty, miejsce).replace("&", "&&") for e in elementy)
    naglowek = sklej(naglowki, "naglowek")
    stopka = sklej(stopki, "stopka")
    for ws in arkusze:
        if naglowek:
            ws.oddHeader.center.text = naglowek
            ws.oddHeader.center.size = 10
        ws.oddFooter.center.text = (stopka + "\n" if stopka else "") + f"{STRONA.get(ctx.d.jezyk, 'Page')} &P"
        ws.oddFooter.center.size = 9


def _sformatuj_tabele(ws: Worksheet, pierwszy: int, ostatni: int, szerokosci: dict[int, int], z_naglowkiem: bool) -> None:
    for kol, szer in szerokosci.items():
        lit = get_column_letter(kol)
        ws.column_dimensions[lit].width = max(ws.column_dimensions[lit].width or 0, min(szer + 2, SZEROKOSC_MAX))
    if z_naglowkiem:
        for c in ws[pierwszy]:
            if c.value is not None:
                c.font, c.fill = _NAGLOWEK, _TLO_NAGLOWKA
                c.alignment = Alignment(horizontal="center")


def _nazwa_arkusza(ctx: _Ctx, uzyte: set[str]) -> tuple[str, Wartosc | None]:
    """Nazwa arkusza z osobą albo firmą z dokumentu (kopia wartości, miejsce „metadane”); None, gdy nic nie pasuje."""
    kandydaci = [f for e in ctx.d.elementy for f in e.fragmenty
                 if isinstance(f, Wartosc) and f.kategoria in ("OSOBA", "ORGANIZACJA") and f.tekst
                 and len(f.tekst) <= 31 and not NIEDOZWOLONE_W_NAZWIE.search(f.tekst)]
    for w in ctx.rng.sample(kandydaci, len(kandydaci)):
        prefiks = PREFIKS_WYCIAG.get(ctx.d.jezyk, "Extract")
        for nazwa in (f"{prefiks} {w.tekst}", w.tekst):
            if len(nazwa) <= 31 and nazwa not in uzyte:
                return nazwa, w
    return "", None


def render_xlsx(d: Dokument, plik: Path, utrudnienia: set[str]) -> list[Wartosc]:
    """Zapisuje `d` jako XLSX w `plik`; zwraca wartości faktycznie umieszczone w pliku (zob. docstring modułu)."""
    nieznane = set(utrudnienia) - UTRUDNIENIA_XLSX - UTRUDNIENIA_POMINIETE
    if nieznane:
        raise ValueError(f"nieznane utrudnienia XLSX: {sorted(nieznane)}")
    plik = Path(plik)
    ctx = _Ctx(d)
    papier = "naglowek_wydruku" in utrudnienia
    wb = Workbook()
    ws = wb.active
    baza = NAZWA_ARKUSZA.get(d.jezyk, "Sheet")
    ws.title = f"{baza}1"

    naglowki = [e for e in d.elementy if e.rodzaj == "naglowek"]
    stopki = [e for e in d.elementy if e.rodzaj == "stopka"]
    akapity = [e for e in d.elementy if e.rodzaj in ("akapit",)]
    podpisy = [e for e in d.elementy if e.rodzaj == "podpis"]
    tabele = _tabele(d)

    # --- plan wierszy: ("a", tekst) -> kolumna A; ("t", {kolumna: tekst}, naglowek?); ("p",) pusty
    meta_poczatek, meta_koniec = wspolne.metadane_w_tresci(d)
    gora: list[str] = [ctx.tekst(e.fragmenty, "tresc") for e in meta_poczatek]
    if not papier:
        gora += [ctx.tekst(e.fragmenty, "tresc") for e in naglowki]
    gora += [ctx.tekst(e.fragmenty, "tresc") for e in akapity]
    dol = [ctx.tekst(e.fragmenty, "tresc") for e in podpisy + meta_koniec]
    if not papier:
        dol += [ctx.tekst(e.fragmenty, "tresc") for e in stopki]
    bloki: list[list[dict[int, str]]] = []
    for nr in sorted(tabele):
        wiersze = tabele[nr]
        bloki.append([{k: _komorka(ctx, es) for k, es in sorted(wiersze[w].items())} for w in sorted(wiersze)])

    # --- ukryty arkusz: końcówka największej tabeli albo ostatnie akapity
    ukryte_wiersze: list[dict[int, str]] = []
    ukryte_akapity: list[str] = []
    naglowek_ukrytego: dict[int, str] | None = None
    if "arkusz_ukryty" in utrudnienia:
        if bloki and max(len(b) for b in bloki) >= 4:
            b = max(bloki, key=len)
            ciecie = max(2, len(b) - max(2, int((len(b) - 1) * UDZIAL_UKRYTYCH)))
            ukryte_wiersze = b[ciecie:]
            del b[ciecie:]
            wiersz0 = tabele[sorted(tabele)[bloki.index(b)]][0] if 0 in tabele[sorted(tabele)[bloki.index(b)]] else {}
            if wiersz0 and all(isinstance(f, str) for es in wiersz0.values() for e in es for f in e.fragmenty):
                naglowek_ukrytego = {k: " ".join(wspolne.tekst_fragmentow(e.fragmenty) for e in es)
                                     for k, es in wiersz0.items()}
        elif not bloki and len(gora) >= 3:
            ile = max(1, int(len(gora) * UDZIAL_UKRYTYCH))
            ukryte_akapity, gora = gora[-ile:], gora[:-ile]

    # --- zapis arkusza głównego
    wiersz = 1
    szerokosci: dict[int, int] = {}
    anchory: list[tuple[Worksheet, int]] = []
    for t in gora:
        _ustaw(ws, wiersz, 1, t)
        anchory.append((ws, wiersz))
        wiersz += 1
    if gora and bloki:
        wiersz += 1
    pierwszy_naglowek = None
    for b in bloki:
        poczatek = wiersz
        for rzad in b:
            for k, t in rzad.items():
                _ustaw(ws, wiersz, k + 1, t)
                szerokosci[k + 1] = max(szerokosci.get(k + 1, 0), max((len(x) for x in t.split("\n")), default=0))
            wiersz += 1
        _sformatuj_tabele(ws, poczatek, wiersz - 1, szerokosci, len(b) > 2)
        pierwszy_naglowek = pierwszy_naglowek or poczatek
        if poczatek + 1 <= wiersz - 1:
            anchory.append((ws, min(poczatek + 1, wiersz - 1)))
        wiersz += 1
    if len(bloki) == 1 and pierwszy_naglowek and len(bloki[0]) > 2:
        ws.freeze_panes = f"A{pierwszy_naglowek + 1}"
    for t in dol:
        _ustaw(ws, wiersz, 1, t)
        wiersz += 1

    # --- ukryty arkusz
    if ukryte_wiersze or ukryte_akapity:
        wu = wb.create_sheet(f"{baza}2")
        wu.sheet_state = "hidden"
        r = 1
        if naglowek_ukrytego:
            for k, t in naglowek_ukrytego.items():
                _ustaw(wu, r, k + 1, t)
            r += 1
        for rzad in ukryte_wiersze:
            for k, t in rzad.items():
                _ustaw(wu, r, k + 1, t)
            r += 1
        for t in ukryte_akapity:
            _ustaw(wu, r, 1, t)
            r += 1
        for kol, szer in szerokosci.items():
            wu.column_dimensions[get_column_letter(kol)].width = min(szer + 2, SZEROKOSC_MAX)

    # --- nagłówek i stopka wydruku
    if papier and (naglowki or stopki):
        _naglowek_wydruku(ctx, wb.worksheets, naglowki, stopki)

    # --- komentarze komórek
    komentarze = [e for e in d.elementy if e.rodzaj == "komentarz"]
    if komentarze:
        _komentarze(ctx, ws, komentarze, anchory, wiersz)

    # --- metadane
    core, wlasne = wspolne.rozdziel_metadane(d, ctx.zapisz)
    firma_meta = None
    if "metadane" in utrudnienia:
        firma = next((f for e in naglowki for f in e.fragmenty if isinstance(f, Wartosc) and f.kategoria == "ORGANIZACJA"),
                     None)
        firma_meta = ctx.zapisz(firma, "metadane").tekst if firma else None
    if "nazwy_arkuszy" in utrudnienia:
        nazwa, wartosc = _nazwa_arkusza(ctx, {s.title for s in wb.worksheets})
        if wartosc is not None:
            ctx.zapisz(wartosc, "metadane")
            ws.title = nazwa
    p = wb.properties
    p.creator = p.lastModifiedBy = core["author"]
    p.title = core.get("title", "")
    p.subject = core.get("subject", "")
    p.keywords = p.description = p.category = ""
    p.language = d.jezyk
    utworzony, zmodyfikowany = wspolne.data_pliku(ctx.rng)
    p.created, p.modified = utworzony, zmodyfikowany
    for k, v in sorted(wlasne.items()):
        wb.custom_doc_props.append(StringProperty(name=k, value=v))

    plik.parent.mkdir(parents=True, exist_ok=True)
    bufor = io.BytesIO()
    wb.save(bufor)
    podmiany = {"docProps/core.xml": lambda x: wspolne.ustaw_modified(x, zmodyfikowany)}  # openpyxl wpisuje „teraz”
    if firma_meta:
        podmiany["docProps/app.xml"] = lambda x: wspolne.wstaw_firme(x, firma_meta)
    plik.write_bytes(wspolne.przepakuj(bufor.getvalue(), podmiany))
    return ctx.wartosci


def _komentarze(ctx: _Ctx, ws: Worksheet, komentarze: list[Element], anchory: list[tuple[Worksheet, int]],
                ostatni_wiersz: int) -> None:
    """Komentarze komórek: autor w polu `author`, treść bez autora; kotwice rozłożone równomiernie."""
    n = len(komentarze)
    if len(anchory) < n:  # za mało komórek – puste wiersze na końcu jako kotwice
        for i in range(n - len(anchory)):
            anchory.append((ws, ostatni_wiersz + 1 + i))
            _ustaw(ws, ostatni_wiersz + 1 + i, 1, " ")
    for i, e in enumerate(komentarze):
        poz = min(len(anchory) - 1, int((i + 0.5) * len(anchory) / n))
        arkusz, w = anchory[poz]
        indeks = e.atrybuty.get("autor_fragment", 0)
        autor = ctx.zapisz(e.fragmenty[indeks], "komentarz")
        reszta = list(e.fragmenty[indeks + 1:])
        if reszta and isinstance(reszta[0], str) and reszta[0].startswith(": "):
            reszta[0] = reszta[0][2:]
        k = Comment(ctx.tekst(reszta, "komentarz"), autor.tekst)
        k.width, k.height = 260, 90
        arkusz.cell(row=w, column=1).comment = k
