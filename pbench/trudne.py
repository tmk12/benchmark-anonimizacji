"""Warstwa trudnych przypadków (spec §11): plan, budowa i generacja dokumentów z oznaczeniem przypadku.

Zadanie H1 – punkt 3 specyfikacji (cyrylica wyłącznie ukraińska). Generatory przypadków:

* `cyrylica_dokument_uk` – cały dokument po ukraińsku (`pbench/szablony/uk`: umowa, pełnomocnictwo, zaświadczenie
  lekarskie, notatka, CV, e-mail) z danymi ukraińskimi (РНОКПП, ЄДРПОУ, IBAN UA, adresy) i odmianą nazwisk;
* `cyrylica_wstawka` – dokument PL/EN/DE (`pbench/szablony/wstawki`) z osobą, adresem i identyfikatorami z Ukrainy:
  zapis łaciński i cyrylica w nawiasie;
* `transliteracja` – jak wyżej, ale ta sama osoba w kilku zapisach: cyrylica + 2–3 transliteracje albo same
  transliteracje (systemy z `pbench.translit`); KAŻDY zapis to osobna wartość gold (`translit`, wspólna `encja`);
* `homoglify` – szablony trzonu (PL/EN/ES/DE/FR) z nazwiskami, w których część liter to cyrylica o podobnym kształcie
  (`pbench.homoglify`); gold = zapis dokładnie z dokumentu;
* `pisownia_rosyjska_imion` – wstawki z osobami o rosyjskiej pisowni imion/nazwisk (Александр, Ковалёв); dokumenty i dane
  nadal ukraińskie. Przypadek dopisywany jest każdemu dokumentowi z taką pisownią.

Warstwa ma własne ziarno (`ZIARNO_TRUDNE`), własny katalog i identyfikatory `h-<skrót>-<język>-<typ>-<nr>`; trzon korpusu
(`pbench.korpus`) pozostaje bez zmian bajtowych. Wpis manifestu = wpis trzonu + `warstwa` (`"trudne"`; brak pola = trzon),
`przypadki` i `posrednie` (puste poza H5). Split dev/test 20/80 stratyfikowany osobno w każdym przypadku.

Zadanie H2 – punkty 2 i 5 specyfikacji (pułapki językowe i długie dokumenty): `odmiana_nazwisk`, `nazwiska_zwykle_slowa`,
`zdrobnienia`, `nazwisko_imie`, `parafy`, `liczby_slownie` (`pbench.trudne_jezyk`) oraz `skroty_po_pelnym`, `granica_okna`,
`dlugie_listy_osob` (`pbench.trudne_dlugie`). Dokumenty składa kod (`pbench.skladacz`), nie szablony; generator przypadku to
funkcja `(język, typ, ziarno) -> (Wynik, Generator, dodatki)`, zarejestrowana w `GENERATORY` obu modułów. Wpis manifestu
`nazwiska_zwykle_slowa` ma pole `pulapki_pospolite` (offsety słów pospolitych o brzmieniu nazwiska w tekście poziomu 1 –
NIE gold); wartości `granica_okna` niosą w `cechy` offset względem granicy okna modelu.

Zadanie H3 – punkt 1 specyfikacji (treść ukryta w DOCX/XLSX/PPTX): `ukryta_docx`, `ukryta_xlsx`, `ukryta_pptx`
(`pbench.trudne_ukryta`). Dokument to zwykły dokument trzonu (szablon) + `Dokument.ukryte`; po renderowaniu
`BudowaTrudna.po_renderze` dopisuje elementy ukryte do pliku, a ich gold trafia do `gold_plik`. Wpis manifestu ma pole
`ukryte` (lista rodzajów `<format>.<rodzaj>`). Mapowanie element -> miejsce: `metodyka/miejsca-ukryte.md`.

Zadanie H4b – poczta (punkt 1) i punkt 6 (wątki cytowane z vCard, RTF i ODT): `ukryta_poczta`, `cytowane_watki_vcard`
(`pbench.trudne_poczta`; załączniki dopisuje do gotowej wiadomości `po_renderze`) i `formaty_rtf_odt` (`pbench.trudne_formaty`;
formaty RTF i ODT spoza trzonu, udziały w planie `UDZIALY_DODATKOWE`, renderery `pbench.render.rtf`/`odt`).

Zadanie H5 – punkt 4 specyfikacji (identyfikacja pośrednia): `posrednie_funkcja_firma`, `posrednie_rzadka_choroba`,
`posrednie_wiek_miejscowosc`, `posrednie_dzialka_gps` (`pbench.trudne_posrednie`, generatory jak w H2). Osoba-cel nie jest
nazwana nigdzie w dokumencie; pole manifestu `posrednie` to lista kombinacji `{id, rodzaj, skladniki: [{id, rola, tekst,
miejsce, wartosc_id}]}` (`wartosc_id` – wartość `gold_tekst` składnika będącego zwykłą kategorią gold, null – składnik spoza
kategorii: funkcja, wiek, rocznik, szkoła, numer działki, GPS; NIE gold miary głównej). Struktura, walidacja i agregacja miary
(odsetek kombinacji przerwanych, poza punktami): `pbench.posrednie`, `metodyka/posrednie.md`. W pozostałych przypadkach pole jest
puste, w trzonie – nieobecne.

CLI: `uv run pbench-trudne --cel korpus-trudne --przypadek transliteracja --n 30`. Pełna warstwa (~300 dokumentów, rozkład per
przypadek, split i sumy kontrolne – zadanie H6b, `pbench.trudne_warstwa`): `uv run pbench-trudne --cel korpus-trudne --pelna
--sumy metodyka/SHA256SUMS-trudne`.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import random
import re
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import (korpus, posrednie, przypadki as P, trudne_dlugie, trudne_formaty, trudne_jezyk, trudne_pliki, trudne_poczta,
               trudne_posrednie, trudne_ukryta)
from .budowa import Blok, Sekcja, Szablon, Wynik, zbuduj_z_kontekstem
from .dane import Generator, zgodna_plec
from .dane.wspolne import BazowyGenerator
from .korpus import TYPY_SKANU, Pozycja
from .odmiana_pl import odmiana_trudna
from .szablony import SZABLONY_TRUDNE as SZABLONY       # wariant warstwy trudnej (J1, S5)
from .szablony.trudne import SZABLONY_UK, SZABLONY_WSTAWKI
from .translit import SYSTEMY, ma_cyrylice

ZIARNO_TRUDNE = 20261104
#: Generatory przypadków H2: przypadek -> {(język, typ): funkcja `(język, typ, ziarno) -> (Wynik, Generator, dodatki)`}.
GENERATORY_H2: dict[str, dict] = {**trudne_jezyk.GENERATORY, **trudne_dlugie.GENERATORY}
#: Generatory przypadków H3 (treść ukryta w DOCX/XLSX/PPTX): przypadek -> {(język, typ): funkcja jak w H2}.
GENERATORY_H3: dict[str, dict] = trudne_ukryta.GENERATORY
#: Generatory przypadków H4a (kodowanie i układ; `ukryta_pdf` jest w `GENERATORY_H3`): funkcja `(język, typ, ziarno, format)`.
GENERATORY_H4A: dict[str, dict] = trudne_pliki.GENERATORY
#: Generatory przypadków H4b (poczta, wątki cytowane z vCard, RTF i ODT): funkcja `(język, typ, ziarno, format)` jak w H4a.
GENERATORY_H4B: dict[str, dict] = {**trudne_poczta.GENERATORY, **trudne_formaty.GENERATORY}
#: Generatory przypadków H5 (identyfikacja pośrednia): funkcja `(język, typ, ziarno) -> (Wynik, Generator, dodatki)` jak w H2;
#: dodatki: `posrednie` – kombinacje (pole manifestu), `cele` – osoby-cele (nienazwane; tylko do testów).
GENERATORY_H5: dict[str, dict] = trudne_posrednie.GENERATORY
#: Udziały formatów spoza trzonu (tylko przypadki, które je dopuszczają w `P.FORMATY_PRZYPADKU`): jak DOC w trzonie.
UDZIALY_DODATKOWE: tuple[tuple[str, int], ...] = (("rtf", 7), ("odt", 7))
#: Typy H2 będące tabelą osób (arkusz XLSX ma sens).
_TYPY_ARKUSZA_H2 = ("lista_obecnosci", "wykaz_wspolnikow", "zalacznik_pracownicy")
PREFIKS_ID = "h-"
#: Rozkład języków homoglifów (jak w trzonie: PL połowa, reszta po ósmej części).
_JEZYKI_HOMOGLIFOW = ("pl", "pl", "pl", "pl", "en", "es", "de", "fr")
#: Zapis łaciński „naturalny” dla języka dokumentu (pierwsza transliteracja `t_s1`).
NATURALNY: dict[str, str] = {"pl": "polski", "de": "niemiecki", "en": "kmu2010"}
_ROLE_OSOBOWE = frozenset({"osoba", "lekarz", "pacjent"})
_RODZAJE_BEZ_HOMOGLIFOW = frozenset({"podpis", "komentarz", "zmiany", "pole", "komorka"})
_SLOT_NAZWA = re.compile(r"\{([a-z_][a-z0-9_]*)\.(pelne|imie|nazwisko)(:[a-z0-9_+]+)?\}")
#: Formaty możliwe w warstwie (xlsx/pptx/eml/msg wymagają typów, których szablony H1 nie mają – zob. `formaty_dla`).
_FORMATY_TEKSTOWE = ("docx", "pdf", "skan", "doc")


@dataclass(frozen=True)
class PozycjaTrudna(Pozycja):
    """Pozycja planu warstwy: dokument do wygenerowania + przypadek, który ilustruje."""

    przypadek: str = ""


# ----------------------------------------------------------------------------- homoglify: przeróbka szablonu trzonu
def z_homoglifami(szablon: Szablon, udzial: float = 0.5) -> Szablon:
    """Kopia szablonu, w której ok. `udzial` gniazd imienia/nazwiska osób ma modyfikator `homoglif` (reszta zostaje
    bez zmian – ta sama osoba występuje i w zapisie poprawnym, i z wmieszanymi znakami). Wybór gniazd jest stały
    (skrót nazwy szablonu, sekcji i pozycji). Podpisy, tabele, komentarze, zmiany i pola formularzy bez zmian."""
    sekcje = []
    for sek in szablon.sekcje:
        if sek.rodzaj_elementu in _RODZAJE_BEZ_HOMOGLIFOW:
            sekcje.append(sek)
            continue
        bloki = []
        for i, b in enumerate(sek.bloki):
            def zamien(m: re.Match[str]) -> str:
                if szablon.role.get(m.group(1)) not in _ROLE_OSOBOWE:
                    return m.group(0)
                h = int.from_bytes(hashlib.sha256(
                    f"{szablon.jezyk}:{szablon.typ}:{sek.nazwa}:{i}:{m.start()}".encode()).digest()[:4], "big")
                if h / 2 ** 32 >= udzial:
                    return m.group(0)
                mod = m.group(3)
                return "{%s.%s:%s}" % (m.group(1), m.group(2), mod[1:] + "+homoglif" if mod else "homoglif")
            bloki.append(Blok(_SLOT_NAZWA.sub(zamien, b.tekst_z_gniazdami), set(b.wymagane_role), b.wariant))
        sekcje.append(Sekcja(sek.nazwa, sek.rodzaj_elementu, bloki, sek.min, sek.max))
    return dataclasses.replace(szablon, sekcje=sekcje, znacz_encje=True)


# ----------------------------------------------------------------------------- plan
def formaty_dla(jezyk: str, typ: str) -> tuple[str, ...]:
    """Formaty, w których dokument tego typu ma sens w warstwie trudnej (kolejność: `korpus.UDZIALY_FORMATOW`)."""
    wynik = []
    for fmt, _ in (*korpus.UDZIALY_FORMATOW, *UDZIALY_DODATKOWE):
        if fmt in ("eml", "msg"):
            ok = typ == "email"
        elif fmt == "xlsx":
            ok = typ in ("lista_plac", "faktura", *_TYPY_ARKUSZA_H2)
        elif fmt == "pptx":
            ok = typ == "prezentacja"
        elif fmt == "skan":
            ok = typ in TYPY_SKANU
        else:
            ok = typ not in ("email", "lista_plac", "prezentacja")
        if ok:
            wynik.append(fmt)
    return tuple(wynik)


def _pary(przypadek: str) -> list[tuple[str, str]]:
    """Dozwolone pary (język, typ) dla przypadku."""
    if przypadek in GENERATORY_H2:
        return sorted(GENERATORY_H2[przypadek])
    if przypadek in GENERATORY_H3:
        return sorted(GENERATORY_H3[przypadek])
    if przypadek in GENERATORY_H4A:
        return sorted(GENERATORY_H4A[przypadek])
    if przypadek in GENERATORY_H4B:
        return sorted(GENERATORY_H4B[przypadek])
    if przypadek in GENERATORY_H5:
        return sorted(GENERATORY_H5[przypadek])
    if przypadek == P.CYRYLICA_DOKUMENT_UK:
        return [("uk", t) for t in sorted(SZABLONY_UK)]
    if przypadek in (P.CYRYLICA_WSTAWKA, P.TRANSLITERACJA, P.PISOWNIA_ROSYJSKA_IMION):
        return sorted(SZABLONY_WSTAWKI)
    if przypadek == P.HOMOGLIFY:    # tylko szablony z imieniem/nazwiskiem osoby w treści (odpisy rejestrów go nie mają)
        return sorted(k for k, sz in SZABLONY.items() if formaty_dla(*k) and any(
            "homoglif" in b.tekst_z_gniazdami for sek in z_homoglifami(sz, 1.0).sekcje for b in sek.bloki))
    raise ValueError(f"przypadek {przypadek!r} nie ma generatora w H1–H5 "
                     f"(dostępne: {', '.join(P.H1 + P.H2 + P.H3 + P.H4A + P.H4B + P.H5)})")


def zaplanuj_przypadek(przypadek: str, n: int, ziarno: int = ZIARNO_TRUDNE) -> list[PozycjaTrudna]:
    """`n` pozycji przypadku, posortowanych po `id`: formaty wg udziałów trzonu (przeskalowanych do możliwych dla
    przypadku), pary (język, typ) po kolei w przetasowanej kolejności. Identyfikatory zależą tylko od `(przypadek, ziarno)`."""
    pary = _pary(przypadek)
    udzialy = (*korpus.UDZIALY_FORMATOW, *((f, u) for f, u in UDZIALY_DODATKOWE if f in P.FORMATY_PRZYPADKU.get(przypadek, ())))
    mozliwe = [(fmt, u) for fmt, u in udzialy if any(fmt in formaty_dla(*p) for p in pary)
               and P.FORMAT_PRZYPADKU.get(przypadek, fmt) == fmt             # przypadki H3 mają jeden format pliku,
               and fmt in P.FORMATY_PRZYPADKU.get(przypadek, (fmt,))]        # przypadki H4a – kilka dozwolonych
    ile = korpus._najwiekszych_reszt([n * u / sum(w for _, w in mozliwe) for _, u in mozliwe], n)
    formaty = [fmt for (fmt, _), k in zip(mozliwe, ile) for _ in range(k)]
    random.Random(korpus._klucz(ziarno, "trudne-formaty", przypadek)).shuffle(formaty)
    kolejnosc: dict[str, list[tuple[str, str]]] = {}
    for fmt, _ in mozliwe:
        kandydaci = sorted(p for p in pary if fmt in formaty_dla(*p))
        random.Random(korpus._klucz(ziarno, "trudne-pary", przypadek, fmt)).shuffle(kandydaci)
        kolejnosc[fmt] = kandydaci
    licznik_fmt: Counter = Counter()
    numery: Counter = Counter()
    wynik = []
    for i, fmt in enumerate(formaty):
        kand = kolejnosc[fmt]
        if przypadek == P.HOMOGLIFY:     # język wg rozkładu trzonu, typ po kolei w obrębie języka i formatu
            jezyk = _JEZYKI_HOMOGLIFOW[i % len(_JEZYKI_HOMOGLIFOW)]
            kand = [p for p in kand if p[0] == jezyk] or kand
            para = kand[licznik_fmt[(fmt, jezyk)] % len(kand)]
            licznik_fmt[(fmt, jezyk)] += 1
        else:
            para = kand[licznik_fmt[fmt] % len(kand)]
            licznik_fmt[fmt] += 1
        jezyk, typ = para
        numery[(jezyk, typ)] += 1
        wynik.append(PozycjaTrudna(f"{PREFIKS_ID}{P.SKROTY[przypadek]}-{jezyk}-{typ}-{numery[(jezyk, typ)]:04d}",
                                   jezyk, typ, fmt, przypadek))
    return sorted(wynik, key=lambda p: p.id)


def przydziel_split(plan: list[PozycjaTrudna], ziarno: int = ZIARNO_TRUDNE) -> dict[str, str]:
    """Split dev/test (~20/80) stratyfikowany osobno w każdym przypadku (jak `korpus.przydziel_split`)."""
    wynik: dict[str, str] = {}
    for przypadek in sorted({p.przypadek for p in plan}):
        wynik |= korpus.przydziel_split([p for p in plan if p.przypadek == przypadek], ziarno)
    return wynik


# ----------------------------------------------------------------------------- budowa
def _uklad_zapisow(seed: int, jezyk: str, przypadek: str) -> dict[str, str]:
    """Przypisanie zapisów gniazd `:t_s1…t_s4`: `cyr` = cyrylica. Wstawka: łaciński naturalny + cyrylica; transliteracja:
    cyrylica + 2 inne zapisy łacińskie (2/3 dokumentów) albo cztery różne zapisy łacińskie bez cyrylicy."""
    nat = NATURALNY.get(jezyk, "kmu2010")
    if przypadek != P.TRANSLITERACJA:
        return {"s1": nat, "s2": "cyr", "s3": "cyr", "s4": "cyr"}
    rng = random.Random(f"translit-uklad:{seed}")
    inne = [s for s in SYSTEMY if s != nat]
    rng.shuffle(inne)
    if rng.random() < 2 / 3:
        return {"s1": nat, "s2": "cyr", "s3": inne[0], "s4": inne[1]}
    return {"s1": nat, "s2": inne[0], "s3": inne[1], "s4": inne[2]}


def _ma_homoglify(d) -> bool:
    return any(not isinstance(f, str) and "homoglify" in f.cechy for e in d.elementy for f in e.fragmenty)


class BudowaTrudna:
    """Budowa dokumentu warstwy (protokół `korpus.Budowa`); zapamiętuje wynik do oznaczenia `przypadki`."""

    def __init__(self) -> None:
        self.wynik: Wynik | None = None
        self.uklad: dict[str, str] | None = None
        #: dodatki generatora H2 do manifestu (np. `pulapki` – słowa pospolite o brzmieniu nazwiska)
        self.dodatki: dict[str, Any] = {}
        self.przypadek = ""
        self.seed = 0
        #: pola dopisywane do wpisu manifestu przez obróbkę pliku H4a (np. `tounicode`, `obroty`, `kolumny`)
        self.manifest: dict[str, Any] = {}

    def dokument(self, p: Pozycja, seed: int) -> tuple[Wynik, BazowyGenerator]:
        assert isinstance(p, PozycjaTrudna)
        self.przypadek, self.seed = p.przypadek, seed
        if p.przypadek in GENERATORY_H2:
            wynik, gen, self.dodatki = GENERATORY_H2[p.przypadek][(p.jezyk, p.typ)](p.jezyk, p.typ, seed)
        elif p.przypadek in GENERATORY_H3:
            wynik, gen, self.dodatki = GENERATORY_H3[p.przypadek][(p.jezyk, p.typ)](p.jezyk, p.typ, seed)
        elif p.przypadek in GENERATORY_H4A:
            wynik, gen, self.dodatki = GENERATORY_H4A[p.przypadek][(p.jezyk, p.typ)](p.jezyk, p.typ, seed, p.format)
        elif p.przypadek in GENERATORY_H4B:
            wynik, gen, self.dodatki = GENERATORY_H4B[p.przypadek][(p.jezyk, p.typ)](p.jezyk, p.typ, seed, p.format)
        elif p.przypadek in GENERATORY_H5:
            wynik, gen, self.dodatki = GENERATORY_H5[p.przypadek][(p.jezyk, p.typ)](p.jezyk, p.typ, seed)
        elif p.przypadek == P.CYRYLICA_DOKUMENT_UK:
            gen = Generator("uk", seed)
            wynik = zbuduj_z_kontekstem(SZABLONY_UK[p.typ], gen, random.Random(f"pbench-trudne:{seed}"))
        elif p.przypadek == P.HOMOGLIFY:
            for udzial, proba in [(0.5, i) for i in range(8)] + [(1.0, i) for i in range(30)]:
                wynik, gen = self._homoglify(p, seed, udzial, proba)
                if _ma_homoglify(wynik.dokument):       # bloki opcjonalne mogą pominąć nazwisko: kolejna próba, potem wszystkie gniazda
                    break
            else:  # pragma: no cover
                raise RuntimeError(f"nie udało się uzyskać homoglifów ({p.id})")
        else:
            wynik, gen = self._wstawka(p, seed)
        self.wynik = wynik
        return wynik, gen

    def zalacznik(self, p: Pozycja, seed: int, gen: BazowyGenerator, wynik: Wynik) -> Wynik:
        assert isinstance(p, PozycjaTrudna)
        if p.przypadek in trudne_poczta.GENERATORY:      # e-mail H4b: zwykły załącznik DOCX jak w trzonie (notatka)
            return zbuduj_z_kontekstem(SZABLONY[(p.jezyk, "notatka")], gen, random.Random(f"pbench-zal:{seed}"), wspolne=wynik)
        if p.przypadek in GENERATORY_H2 or p.przypadek in GENERATORY_H3 or p.przypadek in GENERATORY_H4A \
                or p.przypadek in GENERATORY_H4B or p.przypadek in GENERATORY_H5:   # żaden typ H2–H5 (poza pocztą H4b) nie jest e-mailem
            raise ValueError(f"przypadek {p.przypadek!r} nie ma załączników")
        if p.jezyk == "uk":
            szablon = SZABLONY_UK["notatka"]
        elif p.przypadek == P.HOMOGLIFY:
            szablon = z_homoglifami(SZABLONY[(p.jezyk, "notatka")])
        else:
            szablon = SZABLONY_WSTAWKI[(p.jezyk, "notatka")]
        return zbuduj_z_kontekstem(szablon, gen, random.Random(f"pbench-zal:{seed}"), wspolne=wynik)

    @property
    def kolumny(self) -> int:
        """Liczba kolumn renderera PDF (`dwie_kolumny` = 2)."""
        return trudne_pliki.kolumny_pdf(self.przypadek)

    def po_renderze(self, plik: Path, d, gold_obrazy: list[dict]) -> tuple[list, list[dict]]:
        """Obróbka wyrenderowanego pliku: treść ukryta H3/`ukryta_pdf` (`Dokument.ukryte`), dodatek przypadku H4a
        (`trudne_pliki.obrob`) albo załączniki poczty H4b (`trudne_poczta.obrob`). Zwraca (gold dopisany do `gold_plik`,
        `gold_obrazy`)."""
        if self.przypadek in GENERATORY_H4A:
            return trudne_pliki.obrob(self, plik, d, gold_obrazy)
        if self.przypadek in trudne_poczta.GENERATORY:
            return trudne_poczta.obrob(self, plik, d, gold_obrazy)
        if d.ukryte:
            return trudne_ukryta.wstrzyknij(plik, d), gold_obrazy
        return [], gold_obrazy

    @staticmethod
    def _homoglify(p: PozycjaTrudna, seed: int, udzial: float, proba: int = 0) -> tuple[Wynik, BazowyGenerator]:
        gen = Generator(p.jezyk, seed + 7919 * proba)
        szablon = z_homoglifami(SZABLONY[(p.jezyk, p.typ)], udzial)
        return zbuduj_z_kontekstem(szablon, gen, random.Random(f"pbench-trudne:{seed}:{proba}")), gen

    def _wstawka(self, p: PozycjaTrudna, seed: int) -> tuple[Wynik, BazowyGenerator]:
        szablon = SZABLONY_WSTAWKI[(p.jezyk, p.typ)]
        wariant = "tr" if p.przypadek == P.TRANSLITERACJA else "cw"
        self.uklad = _uklad_zapisow(seed, p.jezyk, p.przypadek)
        for proba in range(30):
            gen = Generator(p.jezyk, seed + 7919 * proba)       # kolejna próba = inna osoba (ziarno generatora Ukrainy z jego ziarna)
            gen.systemy_translit = self.uklad
            gen.p_ru_ua = 0.9 if p.przypadek == P.PISOWNIA_ROSYJSKA_IMION else 0.0
            if p.jezyk == "en":      # szablony wstawek EN to dokumenty kancelarii brytyjskiej (fee earner, letter before claim)
                gen.kraj_dok = "GB"
            wynik = zbuduj_z_kontekstem(szablon, gen, random.Random(f"pbench-trudne:{seed}:{proba}"), wariant)
            if p.przypadek != P.PISOWNIA_ROSYJSKA_IMION or ma_pisownie_ru(wynik):
                return wynik, gen
        raise RuntimeError(f"nie udało się wylosować osoby z rosyjską pisownią ({p.id})")  # pragma: no cover


def ma_pisownie_ru(wynik: Wynik) -> bool:
    """Czy dokument zawiera wartość gold w rosyjskiej pisowni imienia/nazwiska (cecha `pisownia_rosyjska`)."""
    return any(not isinstance(f, str) and "pisownia_rosyjska" in f.cechy
               for e in wynik.dokument.elementy for f in e.fragmenty)


def przypadki_dokumentu(p: PozycjaTrudna, wynik: Wynik) -> list[str]:
    """Przypadki dokumentu: główny + `pisownia_rosyjska_imion` (gdy jest taka osoba) + `cyrylica_wstawka` (dokument spoza
    `uk` zawierający cyrylicę w gold)."""
    wynik_p = {p.przypadek}
    if (p.przypadek in GENERATORY_H2 or p.przypadek in GENERATORY_H3 or p.przypadek in GENERATORY_H4A
            or p.przypadek in GENERATORY_H4B or p.przypadek in GENERATORY_H5):
        return sorted(wynik_p)
    if ma_pisownie_ru(wynik):
        wynik_p.add(P.PISOWNIA_ROSYJSKA_IMION)
    if p.jezyk != "uk" and p.przypadek != P.HOMOGLIFY and any(
            not isinstance(f, str) and ma_cyrylice(f.tekst) for e in wynik.dokument.elementy for f in e.fragmenty):
        wynik_p.add(P.CYRYLICA_WSTAWKA)
    return sorted(wynik_p)


# ----------------------------------------------------------------------------- generacja
def generuj_dokument_trudny(p: PozycjaTrudna, ziarno: int, split: str, cel: Path,
                            maskuj=None) -> dict[str, Any]:
    """Jak `korpus.generuj_dokument`, ale warstwa trudna: wpis ma też `warstwa`, `przypadki`, `posrednie` (kombinacje
    identyfikacji pośredniej H5 – `pbench.posrednie`; w innych przypadkach pusta lista) i `uklad_zapisow` (przypisanie `t_s1…t_s4`
    w transliteracjach)."""
    b = BudowaTrudna()
    # imię zgodne z płcią formy nazwiska (J1, S5) i odmiana -szka/-czka (H6b-fix1); trzon bez zmian
    with zgodna_plec(), odmiana_trudna():
        wpis = korpus.generuj_dokument(p, ziarno, split, cel, maskuj, budowa=b)
    assert b.wynik is not None
    P.sprawdz(przypadki_dokumentu(p, b.wynik))
    wpis["warstwa"] = "trudne"
    wpis["przypadki"] = przypadki_dokumentu(p, b.wynik)
    wpis["posrednie"] = (posrednie.do_manifestu(b.dodatki["posrednie"], wpis,
                                                (cel / wpis["plik_txt"]).read_text(encoding="utf-8"))
                         if b.dodatki.get("posrednie") else [])
    if b.uklad is not None:
        wpis["uklad_zapisow"] = b.uklad
    if b.wynik.dokument.ukryte:
        wpis["ukryte"] = sorted({e.rodzaj for e in b.wynik.dokument.ukryte})
    wpis.update(b.manifest)
    posrednie.sprawdz(wpis)
    if p.przypadek == P.NAZWISKA_ZWYKLE_SLOWA:
        wpis["pulapki_pospolite"] = offsety_pulapek(b.dodatki.get("pulapki", []),
                                                    (cel / wpis["plik_txt"]).read_text(encoding="utf-8"))
    return wpis


def offsety_pulapek(pulapki: list, tekst: str) -> list[dict[str, Any]]:
    """Offsety słów pospolitych (pułapek) w tekście poziomu 1: akapit pułapki to jedna linia tekstu, więc położenie =
    początek linii + przesunięcie w akapicie. Zwraca `{start, end, tekst, encja}` rosnąco po `start`; niezgodność z
    tekstem to błąd (pułapki muszą wskazywać dokładnie słowo)."""
    poczatki: dict[str, int] = {}
    poz = 0
    for linia in tekst.split("\n"):
        poczatki.setdefault(linia, poz)
        poz += len(linia) + 1
    wynik = []
    for pl in pulapki:
        start = poczatki[pl.akapit] + pl.przesuniecie
        if tekst[start:start + len(pl.tekst)] != pl.tekst:
            raise ValueError(f"pułapka {pl.tekst!r} nie leży w tekście na pozycji {start}")
        wynik.append({"start": start, "end": start + len(pl.tekst), "tekst": pl.tekst, "encja": pl.encja})
    return sorted(wynik, key=lambda w: w["start"])


def _zadanie(arg: tuple[PozycjaTrudna, int, str, str]) -> dict[str, Any]:
    p, ziarno, split, cel = arg
    try:
        return generuj_dokument_trudny(p, ziarno, split, Path(cel))
    except Exception as e:  # noqa: BLE001 - błąd jednego dokumentu nie zatrzymuje reszty
        return {"id": p.id, "blad": f"{type(e).__name__}: {e}"}


def zbuduj_przypadek(cel: Path, przypadek: str, n: int, ziarno: int = ZIARNO_TRUDNE, procesy: int = 1,
                     formaty: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    """Buduje `n` dokumentów przypadku w `cel` (pliki, teksty i `manifest.jsonl` posortowany po `id`); zwraca wpisy.
    `formaty` zawęża plan (po wyborze pozycji, identyfikatory bez zmian)."""
    cel = Path(cel)
    cel.mkdir(parents=True, exist_ok=True)
    plan = [p for p in zaplanuj_przypadek(przypadek, n, ziarno) if formaty is None or p.format in formaty]
    split = przydziel_split(plan, ziarno)
    zadania = [(p, ziarno, split[p.id], str(cel)) for p in plan]
    if procesy <= 1:
        wyniki = list(map(_zadanie, zadania))
    else:
        with ProcessPoolExecutor(max_workers=procesy) as pula:
            wyniki = list(pula.map(_zadanie, zadania, chunksize=1))
    bledy = [w for w in wyniki if "blad" in w]
    dobre = sorted((w for w in wyniki if "blad" not in w), key=lambda w: w["id"])
    with (cel / "manifest.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for w in dobre:
            f.write(json.dumps(w, ensure_ascii=False) + "\n")
    if bledy:
        raise RuntimeError("błędy generacji: " + "; ".join(f"{b['id']}: {b['blad']}" for b in bledy[:10]))
    return dobre


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pbench-trudne", description="Generuje dokumenty warstwy trudnych przypadków (H1–H6).")
    ap.add_argument("--cel", type=Path, default=Path("korpus-trudne"))
    tryb = ap.add_mutually_exclusive_group(required=True)
    tryb.add_argument("--przypadek", choices=P.H1 + P.H2 + P.H3 + P.H4A + P.H4B + P.H5)
    tryb.add_argument("--pelna", action="store_true",
                      help="cała warstwa wg rozkładu `trudne_warstwa.ROZKLAD` (H6b; split pełnej warstwy)")
    tryb.add_argument("--rozklad", action="store_true", help="tylko wypisz tabelę rozkładu (do metodyka/przypadki.md)")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--ziarno", type=int, default=ZIARNO_TRUDNE)
    ap.add_argument("--procesy", type=int, default=None, help="liczba procesów (domyślnie 1; --pelna: nproc-2)")
    ap.add_argument("--formaty", default=None, help="lista oddzielona przecinkami, np. docx,pdf")
    ap.add_argument("--sumy", type=Path, default=None, help="--pelna: zapisz sumy kontrolne (format sha256sum) do pliku")
    a = ap.parse_args(argv)
    if a.pelna or a.rozklad:
        from . import trudne_warstwa                   # moduł importuje ten – import leniwy
        if a.rozklad:
            print(trudne_warstwa.tabela_rozkladu(a.ziarno), end="")
            return 0
        return trudne_warstwa.main_pelna(a.cel, a.ziarno, a.procesy, a.sumy)
    wpisy = zbuduj_przypadek(a.cel, a.przypadek, a.n, a.ziarno, a.procesy or 1,
                             tuple(a.formaty.split(",")) if a.formaty else None)
    print(a.przypadek, "dokumentów:", len(wpisy), dict(Counter(w["split"] for w in wpisy)), file=sys.stdout)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
