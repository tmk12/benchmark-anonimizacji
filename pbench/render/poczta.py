"""Wspólna treść wiadomości e-mail dla EML i MSG: nagłówki, treść tekstowa i HTML, załącznik DOCX i gold.

Wejście to `Dokument` przycięty przez `przytnij_dla("eml"|"msg", …)`: metadane `from`/`to`/`cc`/`subject` to nagłówki
(wartości wzorcowe mają miejsce „metadane”), a z `utrudnienia` `metadane` – także pozostałe klucze jako nagłówki
`X-<Klucz>` (EML) albo właściwości własne. Treść: nagłówki dokumentu (jeśli są), akapity, podpisy; stopka (podpis z
telefonem) po separatorze „-- ”, miejsce „stopka”; na końcu akapity z atrybutem `cytat` (wątek cytowany – warstwa trudna,
`cytowane_watki_vcard`; trzon ich nie ma). Obie formy pliku (EML i MSG) mają dokładnie te same treści.

Załącznik (`zalacznik`): wywołujący (zadanie 8) buduje krótki, powiązany dokument (np. `notatka` z tym samym
`Generator` i `Kontekst`, żeby osoby się powtarzały), przycina go `przytnij_dla("docx", …)` i przekazuje wraz z jego
utrudnieniami; renderer zapisuje go DOCX-em jako `<typ>.docx` (nazwa bez danych osobowych). Wartości załącznika w
gold mają id z prefiksem `zal:` i miejsce „zalacznik”; wartości z obrazów załącznika (logo, podpis) nie są tekstem
pliku – to `WynikPoczty.obrazy_zalacznika` (też z prefiksem `zal:`). Linearyzacja poziomu 1 obejmuje tylko sam e-mail,
nie załącznik: załącznik to poziom plikowy.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import html
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from ..budowa import encja
from ..model import Dokument, Obraz, Wartosc
from ..utrudnienia import NAGLOWKI_POCZTY, UTRUDNIENIA_EML, UTRUDNIENIA_POMINIETE
from . import wspolne
from .docx import renderuj_docx

SEPARATOR_STOPKI = "-- "
TYP_DOCX = ("application", "vnd.openxmlformats-officedocument.wordprocessingml.document")


@dataclass
class WynikPoczty:
    """Wynik renderowania wiadomości: wartości w pliku (z załącznikiem) i obrazy załącznika z gold."""

    wartosci: list[Wartosc] = field(default_factory=list)
    obrazy_zalacznika: list[Obraz] = field(default_factory=list)


@dataclass
class Naglowek:
    """Nagłówek wiadomości: nazwa, tekst (adres albo nazwa osoby) i kategoria wartości wzorcowej (None = zwykły tekst)."""

    nazwa: str
    tekst: str
    kategoria: str | None = None
    adres: str | None = None  # adres osoby (OSOBA), gdy dokument ma jej e-mail: nagłówek `"Nazwa" <adres>`


@dataclass
class Wiadomosc:
    naglowki: list[Naglowek]
    tekst: str
    html: str | None
    zalacznik: tuple[str, bytes] | None
    data: dt.datetime
    id_wiadomosci: str
    wynik: WynikPoczty = field(default_factory=WynikPoczty)

    def naglowek(self, nazwa: str) -> Naglowek | None:
        return next((n for n in self.naglowki if n.nazwa == nazwa), None)


def _nazwa_x(klucz: str) -> str:
    return "X-" + "-".join(c.capitalize() for c in re.sub(r"[^A-Za-z0-9]+", "-", klucz).strip("-").split("-"))


def zbuduj_wiadomosc(d: Dokument, utrudnienia: set[str], zalacznik: Dokument | None,
                     utrudnienia_zalacznika: set[str]) -> Wiadomosc:
    """Wspólny rdzeń renderowania EML i MSG (waliduje `utrudnienia`, składa nagłówki, treść i załącznik)."""
    nieznane = set(utrudnienia) - UTRUDNIENIA_EML - UTRUDNIENIA_POMINIETE
    if nieznane:
        raise ValueError(f"nieznane utrudnienia EML/MSG: {sorted(nieznane)}")
    if "zalacznik" in utrudnienia and zalacznik is None:
        raise ValueError("utrudnienie `zalacznik` wymaga dokumentu załącznika (parametr `zalacznik`)")
    rng = wspolne.rng_dokumentu(d)
    wynik = WynikPoczty()

    def zapisz(w: Wartosc, miejsce: str) -> str:
        wynik.wartosci.append(wspolne.zapisz_jako(w, miejsce))
        return w.tekst

    def tekst(fragmenty: list, miejsce: str) -> str:
        return "".join(f if isinstance(f, str) else zapisz(f, miejsce) for f in fragmenty)

    def adres_osoby(v: Wartosc) -> str | None:
        """E-mail tej samej encji (roli) z treści dokumentu; wchodzi do gold jako wartość „metadane”."""
        for e in d.elementy:
            for f in e.fragmenty:
                if isinstance(f, Wartosc) and f.kategoria == "EMAIL" and encja(f.id) == encja(v.id):
                    return zapisz(f, "metadane")
        return None

    naglowki: list[Naglowek] = []
    for klucz in NAGLOWKI_POCZTY:
        if klucz in d.metadane:
            v = d.metadane[klucz]
            osoba = isinstance(v, Wartosc) and v.kategoria == "OSOBA"
            naglowki.append(Naglowek(klucz.capitalize(), zapisz(v, "metadane") if isinstance(v, Wartosc) else v,
                                     v.kategoria if isinstance(v, Wartosc) else None,
                                     adres_osoby(v) if osoba and klucz != "subject" else None))
    if "metadane" in utrudnienia:
        for klucz, v in sorted(d.metadane.items()):
            if klucz not in NAGLOWKI_POCZTY:
                naglowki.append(Naglowek(_nazwa_x(klucz), zapisz(v, "metadane") if isinstance(v, Wartosc) else v,
                                         v.kategoria if isinstance(v, Wartosc) else None))

    # --- treść: nagłówki dokumentu, akapity, podpisy; stopka po separatorze
    gora = [tekst(e.fragmenty, "naglowek") for e in d.elementy if e.rodzaj == "naglowek"]
    akapity = [tekst(e.fragmenty, "tresc") for e in d.elementy if e.rodzaj == "akapit" and not e.atrybuty.get("cytat")]
    podpisy = [tekst(e.fragmenty, "tresc") for e in d.elementy if e.rodzaj == "podpis"]
    stopka = [tekst(e.fragmenty, "stopka") for e in d.elementy if e.rodzaj == "stopka"]
    # wątek cytowany (warstwa trudna, `cytowane_watki_vcard`): akapity z atrybutem `cytat` idą pod podpisem, jak w odpowiedzi
    cytaty = [tekst(e.fragmenty, "tresc") for e in d.elementy if e.rodzaj == "akapit" and e.atrybuty.get("cytat")]
    bloki = ["\n".join(gora)] * bool(gora) + akapity + ["\n".join(podpisy)] * bool(podpisy)
    tresc = "\n\n".join(bloki)
    if stopka:
        tresc += f"\n\n{SEPARATOR_STOPKI}\n" + "\n".join(stopka)
    if cytaty:
        tresc += "\n\n" + "\n\n".join(cytaty)
    tresc += "\n"
    html_tresc = None
    if "html" in utrudnienia:
        def p(t: str) -> str:
            return "<p>" + html.escape(t, quote=False).replace("\n", "<br>\n") + "</p>"
        czesci = [p(b) for b in bloki]
        if stopka:
            czesci.append('<div class="sig">' + SEPARATOR_STOPKI.rstrip() + "<br>\n"
                          + "<br>\n".join(html.escape(s, quote=False) for s in stopka) + "</div>")
        if cytaty:
            czesci.append('<div class="quote">\n' + "\n".join(p(c) for c in cytaty) + "\n</div>")
        html_tresc = ('<!DOCTYPE html>\n<html><head><meta charset="utf-8"></head><body>\n' + "\n".join(czesci)
                      + "\n</body></html>\n")

    # --- załącznik DOCX
    zal = None
    if "zalacznik" in utrudnienia:
        with tempfile.TemporaryDirectory() as tmp:
            sciezka = Path(tmp) / "zal.docx"
            wz = renderuj_docx(zalacznik, sciezka, set(utrudnienia_zalacznika))
            zal = (f"{zalacznik.typ}.docx", sciezka.read_bytes())
        for w in wz.wartosci:
            if w.miejsce != "obraz":
                wynik.wartosci.append(dataclasses.replace(w, id=f"zal:{w.id}", miejsce="zalacznik"))
        for o in wz.obrazy:
            wynik.obrazy_zalacznika.append(dataclasses.replace(
                o, id=f"zal:{o.id}", wartosci=[dataclasses.replace(w, id=f"zal:{w.id}") for w in o.wartosci],
                ramki=[(f"zal:{wid}", bbox) for wid, bbox in o.ramki]))

    data = dt.datetime(rng.randint(2023, 2026), rng.randint(1, 12), rng.randint(1, 28), rng.randint(8, 18),
                       rng.randint(0, 59), rng.randint(0, 59), tzinfo=dt.timezone(dt.timedelta(hours=1)))
    if d.wyslano is not None:       # warstwa trudna: data spójna z treścią i wątkiem (losowania wyżej – bez zmian)
        data = dt.datetime.fromisoformat(d.wyslano)
    return Wiadomosc(naglowki, tresc, html_tresc, zal, data, f"<{rng.randrange(16 ** 24):024x}@pbench.invalid>", wynik)
