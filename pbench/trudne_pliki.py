"""Warstwa trudnych przypadków, zadanie H4a – punkt 6 specyfikacji (kodowanie i układ) i część PDF punktu 1.

Dokument to zwykły dokument trzonu (szablon: umowa, pismo, faktura…) z dodatkiem przypadku; ziarno dokumentu daje cały
dodatek (deterministycznie). Generatory przypadków (`GENERATORY`: przypadek -> {(język, typ): funkcja
`(język, typ, ziarno, format) -> (Wynik, Generator, dodatki)`}):

* `znaki_zerowej_szerokosci` – wartości PII (osoby, PESEL i inne identyfikatory, telefony, e-maile, rachunki) z U+200B,
  U+200C, U+200D, U+2060 i U+00AD wewnątrz (w PDF bez U+00AD – krój DejaVu rysuje go jak widoczny „-”); gold = tekst dokładnie z dokumentu (znaki są w `Wartosc.tekst`, więc w `.txt`,
  DOCX i PDF);
* `rtl` – dodatkowe akapity: nazwa i adres kontrahenta po hebrajsku albo arabsku (dane własne, fikcyjne), osoba łacińska
  w izolacji RTL (U+2067/U+2069) i e-mail zapisany odwrotnie pod U+202E; gold = zapis jak w strumieniu znaków: w tekście
  i DOCX e-mail odwrócony, w PDF – jak w pliku wygenerowanym przez Worda/LibreOffice: renderer kształtuje litery arabskie
  (`arabic-reshaper`) i układa je w porządku wizualnym (`python-bidi`), znaki sterujące nie trafiają do strumienia, a e-mail
  pod RLO leży w nim prosto (`gold_plik` = to, co widać); bez bidi PDFium oddawał wyrazy odwrócone (pismo lustrzane);
* `zepsuty_tounicode` – PDF z zepsutą mapą ToUnicode czcionek (`pliki_pdf.zepsuj_tounicode`; tryby `pua`, `przesuniecie`,
  `usuniete`): tekst wygląda poprawnie, kopiowanie daje śmieci;
* `przeniesienia` – PDF z wartościami łamanymi w wierszu: nazwisko z łącznikiem na końcu linii („Kowal-\\nski”), rachunek
  przez dwie linie; gold = tekst z dokumentu (ze znakiem nowego wiersza);
* `dwie_kolumny` – PDF (renderer z `kolumny=2`, akapity nie dzielą się między kolumnami) i DOCX (`w:cols`);
* `obrocone_strony` – PDF z `/Rotate` 90/180/270 i skan z obrazami obróconymi fizycznie;
* `skan_pieczatki`, `zrzut_ekranu` – obraz (pieczątka firmy z NIP/REGON/adresem; okno poczty z nazwiskiem, e-mailem i
  telefonem) na dodatkowej stronie PDF albo w DOCX; wartości w pikselach (`miejsce` `obraz`), `gold_obrazy` z ramkami;
* `znak_wodny` – znak wodny z nazwą klienta: PDF – obraz osadzony poziomo i ustawiony ukośnie macierzą strony, półprzezroczysty,
  na każdej stronie (`obraz`); DOCX – WordArt w nagłówku (`naglowek`);
* `ukryta_pdf` (`pbench.trudne_ukryta`, `ukryta_pdf`) – aneks z zaczernieniem nad tekstem i skan z niewidoczną warstwą OCR.

Dopiski obrazowe i znak wodny są elementami `Dokument.ukryte` (rodzaje `obraz.pieczatka`, `obraz.zrzut_ekranu`,
`znak_wodny.pdf`, `znak_wodny.docx`), więc uczestnik „idealny” (`Maskowanie`) maskuje je razem z resztą; po zwykłym renderowaniu
`obrob` dopisuje je do pliku, a ich gold trafia do `gold_plik` i `gold_obrazy`.
"""
from __future__ import annotations

import io
import random
import re
import dataclasses
from pathlib import Path

from . import obrazy_trudne, pliki_docx, pliki_pdf, przypadki as P
from .budowa import Wynik, zbuduj_z_kontekstem
from .dane import Generator
from .dane.wspolne import BazowyGenerator
from .korpus import TYPY_SKANU
from .model import Dokument, Element, Wartosc
from .render.pdf import ramka_pt
from .sedzia.normalizacja import same_alnum
from .szablony import SZABLONY_TRUDNE as SZABLONY       # wariant warstwy trudnej (J1, S5)
from .trudne_ukryta import TYPY_FORMATU, Fabryka, dwukropek
from .trudne_wspolne import KLUCZ_ID
from .utrudnienia import splaszcz_tabele

#: Znaki wstawiane do wartości (kolejno: ZWSP, ZWNJ, ZWJ, WJ, miękki łącznik).
ZNAKI_ZW: tuple[str, ...] = ("\u200b", "\u200c", "\u200d", "\u2060", "\u00ad")
#: Kategorie wartości, w które wstawiamy znaki zerowej szerokości (miejsce `tresc`/`tabela`).
KATEGORIE_ZW = frozenset({"OSOBA", "PESEL", "NIP", "NINO", "DNI", "NIR", "NR_PODATKOWY", "SSN", "TELEFON", "EMAIL", "RACHUNEK"})
CECHA_ZW = "zero_width"
CECHA_PRZENIESIENIE = "przeniesienie"
CECHA_RTL = "rtl"
#: Izolacja/osadzenie RTL wokół wartości łacińskiej: (początek, koniec) wg formatu pliku.
IZOLACJA_RTL = {"docx": ("\u2067", "\u2069"), "pdf": ("\u2067", "\u2069")}
RLO, PDF_RLO = "\u202e", "\u202c"
ZALACZNIK = {"pl": "Załącznik", "en": "Annex", "es": "Anexo", "de": "Anlage", "fr": "Annexe"}
KONTRAHENT = {"pl": ("Kontrahent", "Adres", "Osoba do kontaktu"), "en": ("Counterparty", "Address", "Contact person"),
              "es": ("Contraparte", "Dirección", "Persona de contacto"), "de": ("Vertragspartner", "Anschrift", "Ansprechpartner"),
              "fr": ("Cocontractant", "Adresse", "Personne de contact")}
#: Dane fikcyjne RTL (rdzeń nazwy, branża, ulica, miasto); złożone losowo – nazwy własne nie wskazują żadnej firmy.
HE = {"rdzen": ("אופק", "שחר", "תבור", "כרמל", "מצפן", "ארז", "דקל", "רימון", "נחל", "גלעד"),
      "branza": ("יזמות", "שירותים", "ייעוץ", "סחר", "הובלות"), "przyrostek": "בע״מ", "ulica": "רחוב",
      "ulice": ("הדקל", "הגפן", "השקד", "התמר", "הזית"), "miasta": ("חיפה", "באר שבע", "נתניה", "אשדוד", "רחובות"), "sep": ","}
AR = {"rdzen": ("الأفق", "النور", "الواحة", "السنديان", "الرمال", "الزيتون", "المنارة"),
      "branza": ("للتجارة", "للخدمات", "للاستشارات", "للمقاولات"), "przyrostek": "ش.م.م", "ulica": "شارع",
      "ulice": ("النخيل", "الزهور", "الصنوبر", "الياسمين"), "miasta": ("عمّان", "بيروت", "القاهرة", "الدار البيضاء"), "sep": "،"}


class FabrykaH4(Fabryka):
    """Fabryka osób i wartości dopisków H4a (identyfikatory `h.<rodzaj>.<pole>#n`)."""

    PREFIKS = "h"


def _baza(jezyk: str, typ: str, seed: int, sol: str) -> tuple[Wynik, BazowyGenerator]:
    gen = Generator(jezyk, seed)
    return zbuduj_z_kontekstem(SZABLONY[(jezyk, typ)], gen, random.Random(f"pbench-h4a-{sol}:{seed}")), gen


def _wartosci(d: Dokument, kategorie: frozenset[str] | None, miejsca: tuple[str, ...]) -> list[tuple[Element, int, Wartosc]]:
    """Wartości elementów (poza podpisem – rysowanym jako obraz) z podanych kategorii i miejsc."""
    return [(e, i, f) for e in d.elementy if e.rodzaj != "podpis" for i, f in enumerate(e.fragmenty)
            if isinstance(f, Wartosc) and f.miejsce in miejsca and (kategorie is None or f.kategoria in kategorie)
            and f.tekst]


def _podmien(e: Element, i: int, f: Wartosc, tekst: str, cecha: str) -> None:
    e.fragmenty[i] = dataclasses.replace(f, tekst=tekst, cechy=[*f.cechy, cecha])


# ----------------------------------------------------------------------------- znaki zerowej szerokości
def _wstaw_zw(tekst: str, znak: str, rng: random.Random) -> str:
    """`znak` w losowym miejscu między dwoma znakami alfanumerycznymi (nie przy brzegu, nie obok innego znaku zerowej szerokości)."""
    miejsca = [p for p in range(1, len(tekst)) if tekst[p - 1].isalnum() and tekst[p].isalnum()]
    if not miejsca:
        return tekst
    p = rng.choice(miejsca)
    return tekst[:p] + znak + tekst[p:]


def _zw(jezyk: str, typ: str, seed: int, fmt: str) -> tuple[Wynik, BazowyGenerator, dict]:
    wynik, gen = _baza(jezyk, typ, seed, "zw")
    rng = random.Random(f"pbench-zw:{seed}")
    kandydaci = [k for k in _wartosci(wynik.dokument, KATEGORIE_ZW, ("tresc", "tabela")) if len(same_alnum(k[2].tekst)) >= 6]
    rng.shuffle(kandydaci)
    # U+00AD jest w PDF widocznym łącznikiem (DejaVu ma dla niego glif o szerokości „-”), w DOCX/tekście – niewidoczny
    znaki = [z for z in ZNAKI_ZW if not (fmt == "pdf" and z == "\u00ad")]
    rng.shuffle(znaki)
    if not kandydaci:
        raise RuntimeError(f"znaki zerowej szerokości: brak wartości do zmiany ({jezyk}/{typ}/{seed})")  # pragma: no cover
    teksty = [k[2].tekst for k in kandydaci]
    for n in range(max(5, min(len(kandydaci), 9))):
        j = n % len(kandydaci)
        teksty[j] = _wstaw_zw(teksty[j], znaki[n % len(znaki)], rng)
    for (e, i, f), t in zip(kandydaci, teksty):
        if t != f.tekst:
            _podmien(e, i, f, t, CECHA_ZW)
    return wynik, gen, {}


# ----------------------------------------------------------------------------- RTL
def _rtl(jezyk: str, typ: str, seed: int, fmt: str) -> tuple[Wynik, BazowyGenerator, dict]:
    wynik, gen = _baza(jezyk, typ, seed, "rtl")
    d = wynik.dokument
    rng = random.Random(f"pbench-rtl:{seed}")
    f = FabrykaH4(gen, wynik.kontekst, wynik)
    pula = rng.choice((HE, AR))
    nazwa = f"{rng.choice(pula['rdzen'])} {rng.choice(pula['branza'])} {pula['przyrostek']}"
    adres = f"{pula['ulica']} {rng.choice(pula['ulice'])} {rng.randint(2, 98)}{pula['sep']} {rng.choice(pula['miasta'])}"
    et_k, et_a, et_o = KONTRAHENT[jezyk]
    dk = dwukropek(jezyk)
    o = f.osoba()
    otwarcie, zamkniecie = IZOLACJA_RTL.get(fmt, IZOLACJA_RTL["pdf"])
    email = f.email("rtl", o, "tresc")
    odwrocony = dataclasses.replace(email, id=email.id.replace("#", "_rlo#"), tekst=email.tekst[::-1], cechy=[CECHA_RTL, "odwrocony"])
    cechy = (CECHA_RTL,)
    dodatek = [
        Element("akapit", [f"{et_k}{dk}", f.w("rtl", "organizacja", nazwa, "ORGANIZACJA", "tresc", 0, cechy), f", {et_a}{dk}",
                           f.w("rtl", "adres", adres, "ADRES", "tresc", 0, cechy), "."]),
        Element("akapit", [f"{et_o}{dk}", otwarcie, f.pelne("rtl", o, "tresc", cechy), zamkniecie, f", e-mail{dk}", RLO,
                           odwrocony, PDF_RLO, "."]),
    ]
    miejsce = next((i for i, e in enumerate(d.elementy) if e.rodzaj == "podpis"), None)
    if miejsce is None:
        miejsce = max((i for i, e in enumerate(d.elementy) if e.rodzaj in ("akapit", "komorka")), default=-1) + 1
    d.elementy[miejsce:miejsce] = dodatek
    return wynik, gen, {}


# ----------------------------------------------------------------------------- zepsuty ToUnicode
def _tounicode(jezyk: str, typ: str, seed: int, fmt: str) -> tuple[Wynik, BazowyGenerator, dict]:
    wynik, gen = _baza(jezyk, typ, seed, "tu")
    return wynik, gen, {"tryb_tounicode": pliki_pdf.TRYBY_TOUNICODE[seed % len(pliki_pdf.TRYBY_TOUNICODE)]}


# ----------------------------------------------------------------------------- przeniesienia
_SAMOGLOSKI = frozenset("aąeęioóuyáéíúàèìòùâêîôûäëïöüÿœæ")
#: Dwuznaki i trójznaki, których przeniesienie nie rozdziela („Sán-chez”, nie „Sánc-hez”; „Szy-mańska”, nie „Sz-ymańska”).
_ZNAKI_LACZONE = ("sch", "ch", "cz", "dz", "dź", "dż", "rz", "sz", "ck", "ph", "th", "sh", "gu", "qu", "ll", "rr", "gn")


def miejsca_podzialu(wyraz: str) -> list[int]:
    """Pozycje, w których wyraz można przenieść jak przy dzieleniu na sylaby: każda część ma ≥ 2 znaki i samogłoskę, nowy
    wiersz nie zaczyna się samogłoską, granica nie dzieli dwuznaku, a podział to samogłoska–spółgłoska+samogłoska („Ko-walski”)
    albo spółgłoska–spółgłoska („Kowal-ski”, „Sán-chez”)."""
    w = wyraz.lower()
    wynik = []
    for k in range(2, len(w) - 1):
        if w[k] in _SAMOGLOSKI or not (_SAMOGLOSKI & set(w[:k]) and _SAMOGLOSKI & set(w[k:])):
            continue
        if any(w[j:j + len(z)] == z for z in _ZNAKI_LACZONE for j in range(max(0, k - len(z) + 1), k)):
            continue
        if (w[k - 1] in _SAMOGLOSKI and w[k + 1] in _SAMOGLOSKI) or w[k - 1] not in _SAMOGLOSKI:
            wynik.append(k)
    return wynik


def _przenies_wyraz(tekst: str, rng: random.Random) -> str | None:
    """Tekst z łącznikiem i końcem wiersza w najdłuższym wyrazie (≥ 5 liter), który ma miejsce podziału na sylaby
    (`miejsca_podzialu`): „Kowal-\\nski”; None, gdy nie ma takiego wyrazu – wtedy łamana jest inna wartość (H6b-fix1: bez
    podziału awaryjnego w dowolnym miejscu, np. „Ch-loé”)."""
    wyrazy = [m for m in re.finditer(r"[^\W\d_]{5,}", tekst) if miejsca_podzialu(m.group(0))]
    if not wyrazy:
        return None
    m = max(wyrazy, key=lambda x: (x.end() - x.start(), -x.start()))
    miejsca = miejsca_podzialu(m.group(0))
    k = m.start() + rng.choice(miejsca)
    return tekst[:k] + "-\n" + tekst[k:]


def _przenies_rachunek(tekst: str) -> str | None:
    """Rachunek przez dwie linie: nowy wiersz w miejsce spacji najbliższej środka."""
    spacje = [i for i, c in enumerate(tekst) if c == " "]
    if not spacje:
        return None
    k = min(spacje, key=lambda i: abs(i - len(tekst) / 2))
    return tekst[:k] + "\n" + tekst[k + 1:]


def _przeniesienia(jezyk: str, typ: str, seed: int, fmt: str) -> tuple[Wynik, BazowyGenerator, dict]:
    wynik, gen = _baza(jezyk, typ, seed, "pr")
    rng = random.Random(f"pbench-pr:{seed}")
    d = wynik.dokument
    osoby = _wartosci(d, frozenset({"OSOBA"}), ("tresc", "tabela"))
    rng.shuffle(osoby)
    lamane = 0
    for e, i, f in osoby:
        if lamane >= 3:
            break
        t = _przenies_wyraz(f.tekst, rng)
        if t is not None:
            _podmien(e, i, f, t, CECHA_PRZENIESIENIE)
            lamane += 1
    for e, i, f in _wartosci(d, frozenset({"RACHUNEK"}), ("tresc", "tabela")):
        t = _przenies_rachunek(f.tekst)
        if t is not None:
            _podmien(e, i, f, t, CECHA_PRZENIESIENIE)
            lamane += 1
    # za mało osób z wyrazem dzielonym na sylaby (H6b-fix1: bez podziału awaryjnego) – nazwy firm i adresy
    inne = _wartosci(d, frozenset({"ORGANIZACJA", "ADRES"}), ("tresc", "tabela")) if lamane < 2 else []
    for e, i, f in inne:
        if lamane >= 2:
            break
        t = _przenies_wyraz(f.tekst, rng)
        if t is not None:
            _podmien(e, i, f, t, CECHA_PRZENIESIENIE)
            lamane += 1
    if lamane < 2:
        raise RuntimeError(f"przeniesienia: za mało wartości do złamania ({jezyk}/{typ}/{seed})")  # pragma: no cover
    return wynik, gen, {}


# ----------------------------------------------------------------------------- dwie kolumny
def _kolumny(jezyk: str, typ: str, seed: int, fmt: str) -> tuple[Wynik, BazowyGenerator, dict]:
    wynik, gen = _baza(jezyk, typ, seed, "dk")
    if fmt == "docx":    # tabele w kolumnie 8 cm nie mają sensu w Wordzie: komórki jako akapity „kolumna: wartość”
        wynik.dokument.elementy = splaszcz_tabele(wynik.dokument.elementy)
    return wynik, gen, {}


# ----------------------------------------------------------------------------- obrócone strony
def _obrocone(jezyk: str, typ: str, seed: int, fmt: str) -> tuple[Wynik, BazowyGenerator, dict]:
    wynik, gen = _baza(jezyk, typ, seed, "os")
    return wynik, gen, {}


# ----------------------------------------------------------------------------- obrazy: pieczątka, zrzut, znak wodny
def _firma_rozlaczna(gen: BazowyGenerator, f: Fabryka, kraj: str):
    """Fikcyjna firma, której nazwa i adres nie dzielą tokenów z wartościami dokumentu (wspólne miasto czy ulica wyglądałyby
    w sędzi jak częściowy wyciek wartości widocznej)."""
    for _ in range(200):
        firma = gen.firma(kraj=kraj)
        tokeny = {t.casefold() for t in re.findall(r"\w{4,}", f"{firma.nazwa} {firma.adres.linia()}")}
        if not tokeny & f.zajete:
            return firma
    raise RuntimeError("nie udało się wylosować firmy o nazwie i adresie rozłącznych z dokumentem")  # pragma: no cover


#: Etykiety identyfikatorów na pieczątce wg kraju firmy i klucza rejestru (H6b-fix1: dotąd nazwy kategorii, np. polskie
#: „NR REJESTRU” na niemieckiej pieczątce); "" – bez etykiety (niemiecki numer „HRB 123456”, „HRA …” ma oznaczenie
#: rejestru w sobie).
ETYKIETY_PIECZATKI: dict[str, dict[str, str]] = {
    "PL": {"NIP": "NIP", "REGON": "REGON", "KRS": "KRS", "VAT": "NIP UE"},
    "GB": {"COMPANY_NO": "Company No.", "VAT": "VAT No."},
    "US": {"EIN": "EIN"},
    "ES": {"CIF": "CIF", "VAT": "NIF-IVA", "COMPANY_NO": "Hoja"},
    "DE": {"HRB": "", "HRA": "", "VAT": "USt-IdNr.", "STEUERNR": "St.-Nr."},
    "FR": {"SIREN": "SIREN", "SIRET": "SIRET", "VAT": "N° TVA"},
}


def _pieczatka(jezyk: str, typ: str, seed: int, fmt: str) -> tuple[Wynik, BazowyGenerator, dict]:
    wynik, gen = _baza(jezyk, typ, seed, "sp")
    rng = random.Random(f"pbench-sp:{seed}")
    f = FabrykaH4(gen, wynik.kontekst, wynik)
    firma = _firma_rozlaczna(gen, f, wynik.kontekst.kraj)
    ksztalt = rng.choice(("okragla", "prostokatna"))
    from .budowa import MAPA_KATEGORII
    wart = [f.w("pieczatka", "nazwa", firma.nazwa, "ORGANIZACJA", "obraz", 0)]
    etykiety = [""]
    if ksztalt == "prostokatna":
        wart.append(f.w("pieczatka", "adres", firma.adres.linia(), "ADRES", "obraz", 0))
        etykiety.append("")
    for klucz, wartosc in list(firma.rejestry.items()):
        if klucz in MAPA_KATEGORII and len([w for w in wart if w.kategoria not in ("ORGANIZACJA", "ADRES")]) < 2:
            wart.append(f.w("pieczatka", klucz.lower(), wartosc, MAPA_KATEGORII[klucz], "obraz", 0))
            etykiety.append(ETYKIETY_PIECZATKI[wynik.kontekst.kraj][klucz])
    kat = rng.choice((-1, 1)) * rng.uniform(2.0, 8.0)
    wynik.dokument.ukryte = [Element("obraz.pieczatka", wart, {"ksztalt": ksztalt, "kat": round(kat, 2), "ziarno": seed,
                                                              "tytul": ZALACZNIK[jezyk], "etykiety": etykiety})]
    return wynik, gen, {}


def _zrzut(jezyk: str, typ: str, seed: int, fmt: str) -> tuple[Wynik, BazowyGenerator, dict]:
    wynik, gen = _baza(jezyk, typ, seed, "ze")
    f = FabrykaH4(gen, wynik.kontekst, wynik)
    o1 = f.osoba()
    wart = [f.pelne("zrzut", o1, "obraz"), f.email("zrzut", o1, "obraz")]
    o2 = f.osoba()
    wart += [f.pelne("zrzut", o2, "obraz"), f.telefon("zrzut", o2, "obraz")]
    wynik.dokument.ukryte = [Element("obraz.zrzut_ekranu", wart, {"ziarno": seed, "tytul": ZALACZNIK[jezyk]})]
    return wynik, gen, {}


#: Miejsce gold znaku wodnego wg formatu pliku (PDF: obraz, DOCX: WordArt w nagłówku).
MIEJSCE_ZNAKU_WODNEGO = {"pdf": "obraz", "docx": "naglowek"}


def _znak_wodny(jezyk: str, typ: str, seed: int, fmt: str) -> tuple[Wynik, BazowyGenerator, dict]:
    wynik, gen = _baza(jezyk, typ, seed, "zn")
    f = FabrykaH4(gen, wynik.kontekst, wynik)
    firma = _firma_rozlaczna(gen, f, wynik.kontekst.kraj)
    miejsce = MIEJSCE_ZNAKU_WODNEGO[fmt]
    w = f.w("znak_wodny", "klient", firma.nazwa, "ORGANIZACJA", miejsce, 0)
    wynik.dokument.ukryte = [Element(f"znak_wodny.{fmt}", [w], {})]
    return wynik, gen, {}


_FUNKCJE = {P.UKRYTA_PDF: None, P.ZNAKI_ZEROWEJ_SZEROKOSCI: _zw, P.RTL: _rtl, P.ZEPSUTY_TOUNICODE: _tounicode,
            P.PRZENIESIENIA: _przeniesienia, P.DWIE_KOLUMNY: _kolumny, P.OBROCONE_STRONY: _obrocone,
            P.SKAN_PIECZATKI: _pieczatka, P.ZRZUT_EKRANU: _zrzut, P.ZNAK_WODNY: _znak_wodny}


def _pary(przypadek: str) -> list[tuple[str, str]]:
    typy = set(TYPY_FORMATU["pdf"])
    if przypadek == P.OBROCONE_STRONY:
        typy |= set(TYPY_SKANU)
    return sorted((j, t) for (j, t) in SZABLONY if t in typy)


#: Generatory przypadków H4a poza `ukryta_pdf` (ten jest w `pbench.trudne_ukryta`): przypadek -> {(język, typ): funkcja}.
GENERATORY: dict[str, dict] = {p: {k: fn for k in _pary(p)} for p, fn in _FUNKCJE.items() if fn is not None}


# ----------------------------------------------------------------------------- po renderowaniu: dopisanie do pliku
def _strony(plik: Path) -> int:
    import pikepdf
    with pikepdf.open(plik) as pdf:
        return len(pdf.pages)


def _obraz_json(d: Dokument, nr: int, wartosci: list[Wartosc], ramki: dict[str, tuple[int, int, int, int]],
                polozenia: list | None = None) -> dict:
    wpis: dict = {"id": f"{d.id}-h4a{nr}", "wartosci": [w.to_dict() for w in wartosci],
                  "ramki": [[w.id, list(ramki[w.id])] for w in wartosci]}
    if polozenia:
        wpis["polozenia"] = polozenia
    return wpis


def _rysuj(e: Element, jezyk: str) -> tuple[bytes, dict[str, tuple[int, int, int, int]]]:
    wart = [f for f in e.fragmenty if isinstance(f, Wartosc)]
    if e.rodzaj == "obraz.pieczatka":
        return obrazy_trudne.pieczatka(wart, e.atrybuty["ksztalt"], e.atrybuty["kat"], e.atrybuty["ziarno"],
                                       e.atrybuty.get("etykiety"))
    return obrazy_trudne.zrzut_ekranu(jezyk, wart, e.atrybuty["ziarno"])


def _dopisz_obraz(plik: Path, d: Dokument, e: Element, nr: int) -> tuple[list[Wartosc], dict]:
    """Pieczątka albo zrzut ekranu: dodatkowa strona PDF (załącznik) albo obraz na końcu DOCX; zwraca (gold, `Obraz` do manifestu)."""
    png, ramki = _rysuj(e, d.jezyk)
    wart = [f for f in e.fragmenty if isinstance(f, Wartosc)]
    tytul = e.atrybuty["tytul"]
    szer_pt = 300.0 if e.rodzaj == "obraz.pieczatka" else 470.0
    if d.format == "pdf":
        bajty, (x, y, szer, wys) = pliki_pdf.strona_zalacznika(tytul, png, szer_pt)
        strona = pliki_pdf.dolacz_strony(plik, bajty)
        from PIL import Image
        iw, ih = Image.open(io.BytesIO(png)).size
        polozenia = [[w.id, strona, [round(float(v), 2) for v in ramka_pt(ramki[w.id], x, y, szer, wys, iw, ih)]] for w in wart]
        return wart, _obraz_json(d, nr, wart, ramki, polozenia)
    pliki_docx.obraz_na_koncu(plik, png, szer_pt / 28.3465, tytul, "")
    return wart, _obraz_json(d, nr, wart, ramki)


def _znak_wodny_pdf(plik: Path, d: Dokument, e: Element, nr: int) -> tuple[list[Wartosc], dict]:
    w = next(f for f in e.fragmenty if isinstance(f, Wartosc))
    png, ramka = obrazy_trudne.znak_wodny(w)
    polozenia = [[w.id, strona, [round(v, 2) for v in prostokat]] for strona, prostokat in pliki_pdf.naloz_znak_wodny(plik, png)]
    return [w], _obraz_json(d, nr, [w], {w.id: ramka}, polozenia)


def kolumny_pdf(przypadek: str) -> int:
    """Liczba kolumn renderera PDF dla przypadku (1 = zwykły układ)."""
    return 2 if przypadek == P.DWIE_KOLUMNY else 1


def obrob(b, plik: Path, d: Dokument, gold_obrazy: list[dict]) -> tuple[list[Wartosc], list[dict]]:
    """Dopisuje dodatek przypadku H4a do gotowego pliku `plik`; zwraca (gold do `gold_plik`, `gold_obrazy`). `b` – budowa
    (`BudowaTrudna`: `przypadek`, `seed`, `dodatki`, `manifest`)."""
    przypadek, gold = b.przypadek, []
    rng = random.Random(f"pbench-h4a-obrob:{b.seed}")
    if przypadek == P.ZEPSUTY_TOUNICODE:
        tryb = b.dodatki["tryb_tounicode"]
        pliki_pdf.zepsuj_tounicode(plik, tryb)
        b.manifest["tounicode"] = tryb
    elif przypadek == P.DWIE_KOLUMNY:
        if d.format == "docx":
            pliki_docx.kolumny(plik, 2)
        b.manifest["kolumny"] = 2
    elif przypadek == P.OBROCONE_STRONY:
        katy = [rng.choice((0, 90, 180, 270)) for _ in range(_strony(plik))]
        if not any(katy):
            katy[0] = rng.choice((90, 180, 270))
        if d.format == "skan":
            gold_obrazy = pliki_pdf.obroc_skan(plik, katy, gold_obrazy)
        else:
            pliki_pdf.obroc_strony(plik, katy)
        b.manifest["obroty"] = katy
    elif przypadek in (P.SKAN_PIECZATKI, P.ZRZUT_EKRANU):
        for nr, e in enumerate(d.ukryte, 1):
            wart, obraz = _dopisz_obraz(plik, d, e, nr)
            gold += wart
            gold_obrazy = [*gold_obrazy, obraz]
    elif przypadek == P.ZNAK_WODNY:
        e = d.ukryte[0]
        w = next(f for f in e.fragmenty if isinstance(f, Wartosc))
        if d.format == "pdf":
            wart, obraz = _znak_wodny_pdf(plik, d, e, 1)
            gold += wart
            gold_obrazy = [*gold_obrazy, obraz]
        else:
            pliki_docx.znak_wodny(plik, w.tekst)
            gold.append(w)
    return gold, gold_obrazy
