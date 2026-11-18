"""Warstwa trudnych przypadków, zadanie H3 – punkt 1 specyfikacji (treść ukryta w DOCX, XLSX i PPTX).

Dokument ma zwykłą treść z danymi (szablon trzonu: umowa, pismo, lista płac, faktura, prezentacja…) oraz dodatek:
`Dokument.ukryte` – elementy, które żyją w pakiecie pliku poza widokiem, jaki ogląda użytkownik przed wysłaniem
(`w:vanish`, kody pól, nazwy zakładek, `customXml/`, ukryte wiersze/arkusze, `pivotCache`, notatki prelegenta…).
Każdy element niesie własne wartości gold (inne osoby niż w treści – żeby „naiwny” uczestnik, który czyści tylko widoczną
treść, zostawiał wyciek dokładnie w elementach ukrytych), z `miejsce` wg `metodyka/miejsca-ukryte.md`. Tekstu poziomu 1
elementy ukryte nie zmieniają (gold tylko w `gold_plik`). Wstrzykiwanie do pliku: `ukryta_docx`, `ukryta_xlsx`,
`ukryta_pptx` – wywoływane po zwykłym renderowaniu (`BudowaTrudna.po_renderze`).

`krotnosc`: wartość występuje w pliku tyle razy, ile razy ją zapisano (np. instrukcja pola i wynik pola, wersja `wps` i
VML pola tekstowego); gold listuje ją tyle razy (tak liczy wystąpienia sędzia plikowy – bez tego wartość uznałby za
niejednoznaczną).
"""
from __future__ import annotations

import random
import re
from pathlib import Path

from . import przypadki as P
from .budowa import MAPA_KATEGORII, Kontekst, Wynik, zbuduj_z_kontekstem
from .dane import Generator
from .dane.wspolne import BazowyGenerator, Osoba
from .model import Dokument, Element, Wartosc
from .odmiana_pl import odmien, przyimek_pl
from .szablony import SZABLONY_TRUDNE as SZABLONY       # wariant warstwy trudnej (J1, S5)
from .trudne_wspolne import KLUCZ_ID, osoba
from .ukryta_pakiet import ROZDZIELACZ

#: Cecha wartości `obraz`, której tekst leży w XML (alt text, wykres, obiekt osadzony), a nie w pikselach: sędzia plikowy
#: szuka jej w tekście części pakietu, nie w OCR (zob. `Wartosc.w_pikselach`).
CECHA_TEKST_XML = "tekst_xml"
#: Typy dokumentów trzonu, w których przypadek ma sens, wg formatu pliku.
_TYPY_TEKSTOWE = tuple(sorted({t for (_, t) in SZABLONY} - {"email", "lista_plac", "prezentacja"}))
TYPY_FORMATU: dict[str, tuple[str, ...]] = {
    "docx": _TYPY_TEKSTOWE,
    "pdf": _TYPY_TEKSTOWE,
    "xlsx": ("faktura", "lista_plac"),
    "pptx": ("prezentacja",),
}
_TOKEN = re.compile(r"\w+")
#: Domena e-maili osób treści ukrytej i dopisków wg języka dokumentu (H6b-fix1: dotąd polskie „poufne.example” we wszystkich
#: językach). Słowo domeny nie występuje w żadnym tekście szablonów ani słowników (inaczej, np. „POUFNE” w polskiej notatce,
#: token domeny bywałby w sędzi plikowym tekstem spoza wartości).
DOMENY_UKRYTYCH: dict[str, str] = {"pl": "skrytka.example", "en": "lockbox.example", "es": "casillero.example",
                                   "de": "briefkasten.example", "fr": "casier.example", "uk": "skhovanka.example"}

#: Dwukropek po etykiecie wg języka (francuski: spacja przed dwukropkiem, jak w szablonach trzonu).
DWUKROPEK: dict[str, str] = {"fr": " : "}


def dwukropek(jezyk: str) -> str:
    return DWUKROPEK.get(jezyk, ": ")


#: Etykiety tekstów widocznych wokół treści ukrytej (bez danych), wg języka dokumentu.
ETYKIETY: dict[str, dict[str, str]] = {
    "pl": {"uwaga": "Uwaga wewnętrzna", "klient": "Klient", "opis": "Zdjęcie:", "zakladka": "Odesłanie", "telefon": "Telefon",
           "korespondencja": "Zob. korespondencję", "przypis": "Przypis końcowy", "naglowek": "Sprawa prowadzona dla",
           "rachunek": "Rachunek", "notatki": "Notatki", "slajd": "Slajd roboczy", "recenzent": "Recenzent",
           "aneks": "Aneks – wykaz zaczerniony", "skan": "Skan formularza (kopia)"},
    "en": {"uwaga": "Internal note", "klient": "Client", "opis": "Photo of", "zakladka": "Cross-reference", "telefon": "Phone",
           "korespondencja": "See correspondence with", "przypis": "Endnote", "naglowek": "Matter handled for",
           "rachunek": "Account", "notatki": "Notes", "slajd": "Working slide", "recenzent": "Reviewer",
           "aneks": "Annex – redacted list", "skan": "Scanned form (copy)"},
    "es": {"uwaga": "Nota interna", "klient": "Cliente", "opis": "Foto de", "zakladka": "Referencia", "telefon": "Teléfono",
           "korespondencja": "Véase la correspondencia con", "przypis": "Nota final", "naglowek": "Asunto llevado para",
           "rachunek": "Cuenta", "notatki": "Notas", "slajd": "Diapositiva de trabajo", "recenzent": "Revisor",
           "aneks": "Anexo – lista tachada", "skan": "Formulario escaneado (copia)"},
    "de": {"uwaga": "Interne Notiz", "klient": "Mandant", "opis": "Foto von", "zakladka": "Verweis", "telefon": "Telefon",
           "korespondencja": "Siehe Schriftverkehr mit", "przypis": "Endnote", "naglowek": "Angelegenheit für",
           "rachunek": "Konto", "notatki": "Notizen", "slajd": "Arbeitsfolie", "recenzent": "Prüfer",
           "aneks": "Anlage – geschwärzte Liste", "skan": "Gescanntes Formular (Kopie)"},
    "fr": {"uwaga": "Note interne", "klient": "Client", "opis": "Photo de", "zakladka": "Renvoi", "telefon": "Téléphone",
           "korespondencja": "Voir la correspondance avec", "przypis": "Note de fin", "naglowek": "Dossier suivi pour",
           "rachunek": "Compte", "notatki": "Notes", "slajd": "Diapositive de travail", "recenzent": "Relecteur",
           "aneks": "Annexe – liste caviardée", "skan": "Formulaire numérisé (copie)"},
}
def opis(jezyk: str, nazwa: str) -> str:
    """Etykieta opisu zdjęcia przed nazwą osoby (francuski: elizja „Photo d'” przed samogłoską)."""
    et = ETYKIETY[jezyk]["opis"]
    if jezyk == "fr" and et.endswith(" de") and nazwa[:1].lower() in "aeiouyàâéèêîïôûœ":
        return et[:-2] + "d'"
    return f"{et} "


#: Miejsce gold (`Wartosc.miejsce`) wartości każdego rodzaju elementu ukrytego – decyzja kontrolera, bez zmiany wag
#: (`metodyka/wagi_punktow.json`); uzasadnienie: `metodyka/miejsca-ukryte.md` (tabela sprawdzana testem).
MIEJSCA: dict[str, str] = {
    "docx.vanish": "metadane", "docx.pole_author": "pole", "docx.pole_mergefield": "pole", "docx.pole_docproperty": "pole",
    "docx.pole_tekstowe": "tresc", "docx.alt_text": "obraz", "docx.zakladka": "metadane", "docx.custom_xml": "metadane",
    "docx.wykres": "obraz", "docx.obiekt": "obraz", "docx.naglowek_pierwszej_strony": "naglowek", "docx.przypis_koncowy": "przypis",
    "xlsx.wiersz_ukryty": "metadane", "xlsx.kolumna_ukryta": "metadane", "xlsx.arkusz_hidden": "metadane",
    "xlsx.arkusz_veryhidden": "metadane", "xlsx.pivot": "metadane", "xlsx.nazwa": "metadane", "xlsx.walidacja": "metadane",
    "xlsx.formula": "tabela", "xlsx.komentarz": "komentarz",
    "pptx.notatki": "komentarz", "pptx.slajd_ukryty": "metadane", "pptx.poza_slajdem": "metadane", "pptx.alt_text": "obraz",
    "pptx.komentarz": "komentarz",
    # H4a: PDF i dopiski obrazowe przypadków punktu 6
    "pdf.zaczernienie": "metadane", "pdf.warstwa_ocr": "metadane", "obraz.pieczatka": "obraz",
    "obraz.zrzut_ekranu": "obraz", "znak_wodny.pdf": "obraz", "znak_wodny.docx": "naglowek",
    # H4b: poczta (`pbench.trudne_poczta`); `poczta.cytat` to akapity treści z atrybutem `cytat`, nie element `ukryte`
    "poczta.wiadomosc": "zalacznik", "poczta.zalacznik_pdf": "zalacznik", "poczta.vcard": "zalacznik", "poczta.cytat": "tresc",
}
#: Krotność zapisu wartości w pliku (zob. docstring modułu); domyślnie 1.
KROTNOSC: dict[str, int] = {"docx.pole_author": 2, "docx.pole_mergefield": 2, "docx.pole_docproperty": 2,
                            "docx.pole_tekstowe": 2, "xlsx.formula": 2}


def tokeny(tekst: str) -> set[str]:
    return {t.casefold() for t in _TOKEN.findall(tekst)}


class Fabryka:
    """Osoby i wartości gold elementów ukrytych; osoby ukryte nie dzielą tokenów (imię, nazwisko) z żadną wartością
    widoczną w dokumencie ani ze sobą nawzajem. `PREFIKS` identyfikatorów: `u` (treść ukryta), `h` (dopiski H4a)."""

    PREFIKS = "u"

    def __init__(self, gen: BazowyGenerator, ctx: Kontekst, wynik: Wynik) -> None:
        self.gen, self.ctx, self.jezyk = gen, ctx, wynik.dokument.jezyk
        self.zajete: set[str] = set()
        for e in wynik.dokument.elementy:
            for f in e.fragmenty:
                if isinstance(f, Wartosc):
                    self.zajete |= tokeny(f.tekst)
        for v in wynik.dokument.metadane.values():
            if isinstance(v, Wartosc):
                self.zajete |= tokeny(v.tekst)
        self.numery: dict[str, int] = {}
        self.osoby = 0

    def osoba(self) -> Osoba:
        o = osoba(self.gen, self.ctx, warunek=lambda x: not ((tokeny(x.imie) | tokeny(x.nazwisko)) & self.zajete))
        self.zajete |= tokeny(o.imie) | tokeny(o.nazwisko)
        self.osoby += 1
        return o

    def w(self, rodzaj: str, pole: str, tekst: str, kategoria: str, miejsce: str, osoba_nr: int,
          cechy: tuple[str, ...] = ()) -> Wartosc:
        klucz = f"{self.PREFIKS}.{rodzaj}.{pole}"
        self.numery[klucz] = self.numery.get(klucz, 0) + 1
        return Wartosc(f"{klucz}#{self.numery[klucz]}", kategoria, tekst, self.jezyk, miejsce, kategoria, None,
                       f"{self.PREFIKS}.{rodzaj}.{osoba_nr}", list(cechy))

    # skróty: wartości osoby
    def pelne(self, rodzaj: str, o: Osoba, miejsce: str, cechy: tuple[str, ...] = ()) -> Wartosc:
        return self.w(rodzaj, "pelne", o.pelne_imie, "OSOBA", miejsce, self.osoby, cechy)

    def telefon(self, rodzaj: str, o: Osoba, miejsce: str, cechy: tuple[str, ...] = ()) -> Wartosc:
        return self.w(rodzaj, "telefon", o.telefon, "TELEFON", miejsce, self.osoby, cechy)

    def email(self, rodzaj: str, o: Osoba, miejsce: str) -> Wartosc:
        """E-mail osoby z lokalną częścią generatora i własną domeną (`DOMENY_UKRYTYCH` języka dokumentu): domeny z puli
        generatora powtarzają się w treści dokumentu, a wspólny token domeny wyglądałby w sędzi jak częściowy wyciek wartości
        widocznej."""
        return self.w(rodzaj, "email", f"{o.email.split('@')[0]}@{DOMENY_UKRYTYCH[self.jezyk]}", "EMAIL", miejsce, self.osoby)

    def rachunek(self, rodzaj: str, o: Osoba, miejsce: str, cechy: tuple[str, ...] = ()) -> Wartosc:
        return self.w(rodzaj, "rachunek", o.rachunek, "RACHUNEK", miejsce, self.osoby, cechy)

    def id(self, rodzaj: str, o: Osoba, miejsce: str) -> Wartosc:
        k = next((k for k in (KLUCZ_ID[self.jezyk], "NINO", "SSN") if k in o.ids), None) or next(iter(o.ids))
        return self.w(rodzaj, k.lower(), o.ids[k], MAPA_KATEGORII[k], miejsce, self.osoby)


def _el(rodzaj: str, *fragmenty: str | Wartosc, **atrybuty) -> Element:
    return Element(rodzaj, list(fragmenty), atrybuty)


# ----------------------------------------------------------------------------- DOCX
def elementy_docx(f: Fabryka) -> list[Element]:
    et, X, dk = ETYKIETY[f.jezyk], CECHA_TEKST_XML, dwukropek(f.jezyk)
    wynik = []
    o = f.osoba()
    wynik.append(_el("docx.vanish", f"{et['uwaga']}{dk}", f.pelne("vanish", o, "metadane"), ", ", f.email("vanish", o, "metadane")))
    for rodzaj in ("pole_author", "pole_mergefield"):
        o = f.osoba()
        wynik.append(_el(f"docx.{rodzaj}", f.pelne(rodzaj, o, "pole"), etykieta=et["klient"]))
    o = f.osoba()
    wynik.append(_el("docx.pole_docproperty", f.id("pole_docproperty", o, "pole"), etykieta=et["klient"]))
    o = f.osoba()
    wynik.append(_el("docx.pole_tekstowe", f"{et['klient']}{dk}", f.pelne("pole_tekstowe", o, "tresc"), ";", ROZDZIELACZ,
                     f"{et['telefon']}{dk}", f.telefon("pole_tekstowe", o, "tresc"), "."))
    o = f.osoba()
    wynik.append(_el("docx.alt_text", opis(f.jezyk, o.pelne_imie), f.pelne("alt_text", o, "obraz", (X,)), ROZDZIELACZ,
                     f.telefon("alt_text", o, "obraz", (X,))))
    o = f.osoba()
    zakladka = re.sub(r"\W", "_", f"{o.nazwisko}_{o.imie}")[:40]
    wynik.append(_el("docx.zakladka", f.w("zakladka", "pelne", zakladka, "OSOBA", "metadane", f.osoby), etykieta=et["zakladka"]))
    o = f.osoba()
    wynik.append(_el("docx.custom_xml", f.pelne("custom_xml", o, "metadane"), ROZDZIELACZ, f.id("custom_xml", o, "metadane"), ROZDZIELACZ,
                     f.email("custom_xml", o, "metadane"), pola=["nazwa", "identyfikator", "email"]))
    wynik.append(_el("docx.wykres", f.pelne("wykres", f.osoba(), "obraz", (X,)), ROZDZIELACZ, f.pelne("wykres", f.osoba(), "obraz", (X,)), ROZDZIELACZ,
                     f.pelne("wykres", f.osoba(), "obraz", (X,))))
    o = f.osoba()
    wynik.append(_el("docx.obiekt", f.pelne("obiekt", o, "obraz", (X,)), ROZDZIELACZ, f.rachunek("obiekt", o, "obraz", (X,)),
                     pola=[et["klient"], et["rachunek"]]))
    o = f.osoba()
    wynik.append(_el("docx.naglowek_pierwszej_strony", f"{et['naglowek']}{dk}", f.pelne("naglowek_pierwszej_strony", o, "naglowek"), " | ",
                     f.telefon("naglowek_pierwszej_strony", o, "naglowek")))
    o = f.osoba()
    if f.jezyk == "pl":     # „korespondencję z” + narzędnik („ze” przed Zb-, St-, Sz- + spółgłoska)
        narz = odmien(o.imie, o.nazwisko, o.plec, "narz")
        z = (f"{et['korespondencja']} {przyimek_pl('z', narz)} ",
             f.w("przypis_koncowy", "pelne", narz, "OSOBA", "przypis", f.osoby, ("przypadek_zalezny",)))
    else:
        z = (f"{et['korespondencja']} ", f.pelne("przypis_koncowy", o, "przypis"))
    wynik.append(_el("docx.przypis_koncowy", *z, ", ", f.email("przypis_koncowy", o, "przypis"), etykieta=et["przypis"]))
    return wynik


# ----------------------------------------------------------------------------- XLSX
def elementy_xlsx(f: Fabryka) -> list[Element]:
    et, dk = ETYKIETY[f.jezyk], dwukropek(f.jezyk)
    wynik = []
    o = f.osoba()
    wynik.append(_el("xlsx.wiersz_ukryty", f.pelne("wiersz_ukryty", o, "metadane"), ROZDZIELACZ, f.telefon("wiersz_ukryty", o, "metadane")))
    o = f.osoba()
    wynik.append(_el("xlsx.kolumna_ukryta", et["klient"], ROZDZIELACZ, f.pelne("kolumna_ukryta", o, "metadane"), ROZDZIELACZ,
                     f.email("kolumna_ukryta", o, "metadane")))
    o = f.osoba()
    wynik.append(_el("xlsx.arkusz_hidden", et["klient"], ROZDZIELACZ, f.pelne("arkusz_hidden", o, "metadane"), ROZDZIELACZ,
                     f.email("arkusz_hidden", o, "metadane"), nazwa="Dane_robocze"))
    o = f.osoba()
    wynik.append(_el("xlsx.arkusz_veryhidden", et["klient"], ROZDZIELACZ, f.pelne("arkusz_veryhidden", o, "metadane"), ROZDZIELACZ,
                     f.rachunek("arkusz_veryhidden", o, "metadane"), nazwa="Archiwum_systemowe"))
    o1, o2 = f.osoba(), f.osoba()
    wynik.append(_el("xlsx.pivot", f.pelne("pivot", o1, "metadane"), ROZDZIELACZ, f.pelne("pivot", o2, "metadane"), ROZDZIELACZ,
                     f.rachunek("pivot", o1, "metadane"), ROZDZIELACZ, f.rachunek("pivot", o2, "metadane")))
    o = f.osoba()
    wynik.append(_el("xlsx.nazwa", f.pelne("nazwa", o, "metadane"), nazwa="Klient_glowny"))
    wynik.append(_el("xlsx.walidacja", f.w("walidacja", "nazwisko", f.osoba().nazwisko, "OSOBA", "metadane", f.osoby), ROZDZIELACZ,
                     f.w("walidacja", "nazwisko", f.osoba().nazwisko, "OSOBA", "metadane", f.osoby), ROZDZIELACZ,
                     f.w("walidacja", "nazwisko", f.osoba().nazwisko, "OSOBA", "metadane", f.osoby)))
    o = f.osoba()
    wynik.append(_el("xlsx.formula", f.pelne("formula", o, "tabela")))
    o = f.osoba()
    wynik.append(_el("xlsx.komentarz", f"{et['uwaga']}{dk}", f.pelne("komentarz", o, "komentarz"), ", ", f.telefon("komentarz", o, "komentarz"),
                     nazwa="Notatki", tytul=et["notatki"], autor=et["recenzent"]))
    return wynik


# ----------------------------------------------------------------------------- PPTX
def elementy_pptx(f: Fabryka) -> list[Element]:
    et, X, dk = ETYKIETY[f.jezyk], CECHA_TEKST_XML, dwukropek(f.jezyk)
    wynik = []
    o = f.osoba()
    wynik.append(_el("pptx.notatki", f"{et['klient']}{dk}", f.pelne("notatki", o, "komentarz"), ROZDZIELACZ, f.telefon("notatki", o, "komentarz"),
                     slajd=1))
    o = f.osoba()
    wynik.append(_el("pptx.slajd_ukryty", et["slajd"], ROZDZIELACZ, f.pelne("slajd_ukryty", o, "metadane"), ROZDZIELACZ, f.email("slajd_ukryty", o, "metadane")))
    o = f.osoba()
    wynik.append(_el("pptx.poza_slajdem", f.pelne("poza_slajdem", o, "metadane"), ROZDZIELACZ, f.telefon("poza_slajdem", o, "metadane"), slajd=1))
    o = f.osoba()
    wynik.append(_el("pptx.alt_text", opis(f.jezyk, o.pelne_imie), f.pelne("alt_text", o, "obraz", (X,)), slajd=2))
    o = f.osoba()
    wynik.append(_el("pptx.komentarz", f"{et['uwaga']}{dk}", f.pelne("komentarz", o, "komentarz"), slajd=0, autor=et["recenzent"]))
    return wynik


# ----------------------------------------------------------------------------- PDF (H4a)
def elementy_pdf(f: Fabryka) -> list[Element]:
    et, dk = ETYKIETY[f.jezyk], dwukropek(f.jezyk)
    klucz = KLUCZ_ID[f.jezyk]
    wynik = []
    o = f.osoba()
    wynik.append(_el("pdf.zaczernienie", f"{et['klient']}{dk}", f.pelne("zaczernienie", o, "metadane"), ROZDZIELACZ,
                     f"{et['telefon']}{dk}", f.telefon("zaczernienie", o, "metadane"), ROZDZIELACZ,
                     f"{et['rachunek']}{dk}", f.rachunek("zaczernienie", o, "metadane"), tytul=et["aneks"]))
    o = f.osoba()
    wynik.append(_el("pdf.zaczernienie", f"{et['klient']}{dk}", f.pelne("zaczernienie", o, "metadane"), ROZDZIELACZ,
                     "E-mail: ", f.email("zaczernienie", o, "metadane"), tytul=et["aneks"]))
    o = f.osoba()
    wynik.append(_el("pdf.warstwa_ocr", f"{et['klient']}{dk}", f.pelne("warstwa_ocr", o, "metadane"), ROZDZIELACZ,
                     f"{klucz}{dk}", f.id("warstwa_ocr", o, "metadane"), ROZDZIELACZ,
                     f"{et['telefon']}{dk}", f.telefon("warstwa_ocr", o, "metadane"), tytul=et["skan"]))
    return wynik


ELEMENTY = {"docx": elementy_docx, "xlsx": elementy_xlsx, "pptx": elementy_pptx, "pdf": elementy_pdf}


def zloz_gold(ukryte: list[Element]) -> list[Wartosc]:
    """Lista `Wartosc` do `gold_plik`: każda wartość tyle razy, ile razy zapisano ją w pliku (`KROTNOSC`)."""
    return [f for e in ukryte for f in e.fragmenty if isinstance(f, Wartosc) for _ in range(KROTNOSC.get(e.rodzaj, 1))]


def wstrzyknij(plik: Path, d: Dokument) -> list[Wartosc]:
    """Dopisuje `d.ukryte` do pliku `plik` (format `d.format`) i zwraca ich gold (do `gold_plik`)."""
    if d.format == "docx":
        from .ukryta_docx import wstrzyknij_docx as wstrzyknij_format
    elif d.format == "xlsx":
        from .ukryta_xlsx import wstrzyknij_xlsx as wstrzyknij_format
    elif d.format == "pptx":
        from .ukryta_pptx import wstrzyknij_pptx as wstrzyknij_format
    elif d.format == "pdf":
        from .ukryta_pdf import wstrzyknij_pdf as wstrzyknij_format
    else:
        raise ValueError(f"treść ukryta: nieobsługiwany format {d.format!r}")
    if d.format == "pdf":
        wstrzyknij_format(plik, d.ukryte, d.id)          # szum skanu zależy od dokumentu
    else:
        wstrzyknij_format(plik, d.ukryte)
    return zloz_gold(d.ukryte)


# ----------------------------------------------------------------------------- generatory (kontrakt jak w H2)
def _generator(przypadek: str, jezyk: str, typ: str):
    def generuj(_jezyk: str, _typ: str, seed: int) -> tuple[Wynik, BazowyGenerator, dict]:
        gen = Generator(jezyk, seed)
        wynik = zbuduj_z_kontekstem(SZABLONY[(jezyk, typ)], gen, random.Random(f"pbench-ukryta:{seed}"))
        fmt = P.FORMAT_PRZYPADKU.get(przypadek) or P.FORMATY_PRZYPADKU[przypadek][0]
        wynik.dokument.ukryte = ELEMENTY[fmt](Fabryka(gen, wynik.kontekst, wynik))
        return wynik, gen, {}
    return generuj


GENERATORY: dict[str, dict] = {
    przypadek: {(jezyk, typ): _generator(przypadek, jezyk, typ)
                for (jezyk, typ) in SZABLONY
                if typ in TYPY_FORMATU[P.FORMAT_PRZYPADKU.get(przypadek) or P.FORMATY_PRZYPADKU[przypadek][0]]}
    for przypadek in (*P.H3, P.UKRYTA_PDF)
}
