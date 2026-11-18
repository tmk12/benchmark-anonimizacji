"""Wspólna baza generatorów wartości syntetycznych (gold publicznego benchmarku anonimizacji).

Zasady (wiążące dla wszystkich krajów):

* Zakresy są **realistyczne** – PESEL z datą urodzenia 1940–2005, NIP z prawdziwym kodem urzędu skarbowego,
  IBAN z kodem banku w krajowym formacie. Nie używamy „bezpiecznych” zakresów Privatizera (PESEL 2090–2099,
  NIP z urzędem 000, bank 999) – inaczej korpus faworyzowałby jedno narzędzie.
* Sumy kontrolne liczymy własnym kodem; w testach waliduje je niezależnie `python-stdnum`. Moduł **nie** importuje
  `lgprivatizer` (niezależność pomiaru).
* Generator jest deterministyczny: ten sam `(jezyk, ziarno)` i ta sama kolejność wywołań dają te same wartości.
* E-maile: wyłącznie domeny zarezerwowane (RFC 2606/6761): `example.com|org|net` i `*.test`.
* Wartość określonego typu (PESEL, DNI, NIR, e-mail…) nie powtarza się w obrębie jednego generatora.

Telefony: wartości są wyraźnie fikcyjne – z oficjalnych pul zarezerwowanych do fikcji albo, gdy kraj takiej puli
nie ma, w formacie, który nie istnieje w planie numeracji. Numery NIE muszą przechodzić `phonenumbers.is_valid_number`
(pule fikcyjne bywają dla libphonenumber nieważne); część narzędzi może ich nie rozpoznać jako telefonów, co dotyczy
wszystkich uczestników jednakowo (`metodyka/znane-ograniczenia.md`).

* GB: Ofcom, numery do fikcji (020 7946 0xxx, 0113/0114/0115/0116/0117/0118/0121/0151/0161 496 0xxx, 0191 498 0xxx,
  028 9649 6xxx, 029 2018 0xxx, 01632 960xxx) i komórkowe 07700 900000–900999.
* US: tylko 555-0100–0199 (NANPA), z prawdziwym kodem obszaru.
* DE: pule Bundesnetzagentur „Drama Numbers” – stacjonarne 030 23125, 040 66969, 069 90009, 089 99998, 0221 4710
  (+ 3 cyfry) i zarezerwowane numery komórkowe z listy BNetzA.
* FR: sześć racines ARCEP (decyzja 2018-0881) do dzieł audiowizualnych: 01 99 00, 02 61 91, 03 53 01, 04 65 71,
  05 36 49, 06 39 98 (+ 4 cyfry).
* PL, ES, UA: brak oficjalnej puli – numer krajowy zaczyna się od `00` (PL: `000 123 456`, ES: `000 123 456`, UA:
  `00 123 45 67` po kodzie operatora), a długość i grupowanie są jak w realnym formacie kraju; taki prefiks nie
  istnieje w planach numeracji UKE, CNMC ani NKRZI.

Klucze słownika `Osoba.ids` / `Firma.rejestry` (mapowanie na kategorie robi zadanie 3):
PL PESEL, NIP, DOWOD, PASZPORT / NIP, REGON, KRS, VAT; GB NINO, NHS / COMPANY_NO, VAT; US SSN / EIN;
ES DNI|NIE, NUSS / CIF, VAT; DE STEUER_ID, SVNR, PERSONALAUSWEIS / HRB, VAT; FR NIR / SIREN, SIRET, VAT.
"""
from __future__ import annotations

import datetime as dt
import functools
import ipaddress
import random
import re
import unicodedata
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import phonenumbers

SLOWNIKI = Path(__file__).resolve().parent / "slowniki"

DOMENY_EMAIL = ("example.com", "example.org", "example.net", "mail.test", "poczta.test", "webmail.test")
#: Domeny e-mail osób wg języka (tylko zarezerwowane); „poczta.test” (polskie słowo) wyłącznie w PL.
DOMENY_EMAIL_JEZYK: dict[str, tuple[str, ...]] = {
    "pl": DOMENY_EMAIL,
    "en": ("example.com", "example.org", "example.net", "mail.test", "webmail.test", "inbox.test"),
    "es": ("example.com", "example.org", "example.net", "correo.test", "webmail.test", "buzon.test"),
    "de": ("example.com", "example.org", "example.net", "post.test", "webmail.test", "mailbox.test"),
    "fr": ("example.com", "example.org", "example.net", "courriel.test", "webmail.test", "messagerie.test"),
    "uk": ("example.com", "example.org", "example.net", "poshta.test", "webmail.test", "skrynka.test"),
}
#: Części lokalne ogólnych adresów firm wg języka (EN i ES nadpisują `_email_firmy` własnymi).
_EMAIL_FIRMY: dict[str, tuple[str, ...]] = {
    "pl": ("biuro@{s}.test", "kontakt.{s}@example.com", "office@{s}.example.org", "info@{s}.example.net"),
    "de": ("info@{s}.test", "kontakt.{s}@example.com", "buero@{s}.example.org", "zentrale@{s}.example.net"),
    "fr": ("contact@{s}.test", "info.{s}@example.com", "bureau@{s}.example.org", "accueil@{s}.example.net"),
}
#: Słowo „umowa” w ścieżkach URL wg języka.
_SLOWO_UMOWA = {"pl": "umowa", "en": "contract", "es": "contrato", "de": "vertrag", "fr": "contrat", "uk": "dohovir"}


# --------------------------------------------------------------------------------------------- modele
@dataclass(frozen=True)
class Adres:
    ulica: str
    numer: str
    kod: str
    miejscowosc: str
    kraj: str
    region: str = ""  # stan USA (dla innych krajów puste)

    def linia(self) -> str:
        """Adres w jednej linii wg konwencji kraju."""
        if self.kraj == "GB":
            return f"{self.numer} {self.ulica}, {self.miejscowosc} {self.kod}"
        if self.kraj == "US":
            return f"{self.numer} {self.ulica}, {self.miejscowosc}, {self.region} {self.kod}"
        if self.kraj == "FR":
            return f"{self.numer} {self.ulica}, {self.kod} {self.miejscowosc}"
        if self.kraj == "ES":
            return f"{self.ulica}, {self.numer}, {self.kod} {self.miejscowosc}"
        if self.kraj == "UA":    # „вул. Соборна, буд. 12, кв. 34, м. Львів, Львівська обл., 79000” (region pusty dla Kijowa)
            return ", ".join(x for x in (self.ulica, f"буд. {self.numer}", f"м. {self.miejscowosc}", self.region,
                                         self.kod) if x)
        return f"{self.ulica} {self.numer}, {self.kod} {self.miejscowosc}"  # PL, DE


@dataclass(frozen=True)
class Osoba:
    imie: str
    nazwisko: str
    plec: str  # "M" | "K"
    data_ur: dt.date
    adres: Adres
    telefon: str
    email: str
    login: str
    rachunek: str
    kraj: str  # PL | GB | US | ES | DE | FR
    ids: dict[str, str] = field(default_factory=dict)

    @property
    def pelne_imie(self) -> str:
        return f"{self.imie} {self.nazwisko}"


@dataclass(frozen=True)
class Firma:
    nazwa: str
    forma: str
    adres: Adres
    telefon: str
    email: str
    rachunek: str
    kraj: str
    rejestry: dict[str, str] = field(default_factory=dict)


# --------------------------------------------------------------------------------------------- pomocnicze
def kod_icd_plec(wpis: str) -> str | None:
    """Płeć, której dotyczy rozpoznanie ICD-10 (`M|K`), albo None dla rozpoznań bezpłciowych (po kodzie wpisu)."""
    m = re.match(r"([A-Z])(\d{2})", wpis)
    if m is None:
        return None
    lit, n = m.group(1), int(m.group(2))
    if lit == "N" and 40 <= n <= 53 or lit == "C" and 60 <= n <= 63 or lit == "E" and n == 29:
        return "M"
    if (lit == "N" and 60 <= n <= 64 or lit == "N" and 70 <= n <= 98 or lit == "O" or lit == "C" and 50 <= n <= 58
            or lit == "D" and 25 <= n <= 28 or lit == "E" and n == 28 or lit == "Z" and 32 <= n <= 39):
        return "K"
    return None


@functools.lru_cache(maxsize=None)
def slownik(jezyk: str, plik: str) -> tuple[str, ...]:
    tekst = (SLOWNIKI / jezyk / f"{plik}.txt").read_text(encoding="utf-8")
    return tuple(x for x in tekst.splitlines() if x.strip())


def ascii_(tekst: str) -> str:
    """Tekst bez znaków diakrytycznych, małe litery, tylko [a-z0-9]."""
    t = tekst.lower().replace("ł", "l").replace("ß", "ss").replace("æ", "ae").replace("œ", "oe")
    t = unicodedata.normalize("NFKD", t)
    return re.sub(r"[^a-z0-9]", "", t)


def cyfry(rng: random.Random, n: int) -> str:
    return "".join(rng.choice("0123456789") for _ in range(n))


#: Warstwa trudna (J1, S5): imię zgodne z płcią formy nazwiska – osoba męska nie dostaje żeńskiej formy nazwiska ze słownika
#: (polski słownik nazwisk zawiera „Sadowska”; trzon ma przez to „Mieczysław Sadowska” – znane ograniczenie, `metodyka/
#: znane-ograniczenia.md`). Domyślnie wyłączone: trzon korpusu ma opublikowane sumy kontrolne i nie może się zmienić;
#: `generuj_dokument_trudny` włącza (`zgodna_plec()`). Poprawka nie zużywa liczb losowych (ten sam ciąg losowań).
ZGODNA_PLEC: ContextVar[bool] = ContextVar("pbench_zgodna_plec", default=False)


@contextmanager
def zgodna_plec() -> Iterator[None]:
    """Kontekst warstwy trudnej: `ZGODNA_PLEC` włączone (zob. wyżej)."""
    znacznik = ZGODNA_PLEC.set(True)
    try:
        yield
    finally:
        ZGODNA_PLEC.reset(znacznik)


def wagowo(rng: random.Random, lista: tuple[str, ...]) -> str:
    """Losowanie z wagą malejącą z pozycją (słowniki są uporządkowane od najczęstszych)."""
    return rng.choices(lista, weights=[1.0 / (i + 15) for i in range(len(lista))])[0]


def suma_luhna_kontrola(baza: str) -> str:
    """Cyfra kontrolna Luhna dla `baza` (wynik dopisujemy na końcu)."""
    s = 0
    for i, c in enumerate(reversed(baza)):
        d = int(c)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        s += d
    return str((10 - s % 10) % 10)


def cyfry_kontrolne_iban(kraj: str, bban: str) -> str:
    """Dwie cyfry kontrolne IBAN (ISO 13616, mod 97)."""
    napis = (bban + kraj + "00").upper()
    liczba = int("".join(str(int(c, 36)) for c in napis))
    return f"{98 - liczba % 97:02d}"


def losowa_data(rng: random.Random, od: dt.date, do: dt.date) -> dt.date:
    return od + dt.timedelta(days=rng.randint(0, (do - od).days))


MIESIACE: dict[str, tuple[str, ...]] = {
    "pl": ("stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września",
           "października", "listopada", "grudnia"),
    "en": ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December"),
    "es": ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
           "noviembre", "diciembre"),
    "de": ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
           "November", "Dezember"),
    "fr": ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
           "novembre", "décembre"),
    "uk": ("січня", "лютого", "березня", "квітня", "травня", "червня", "липня", "серпня", "вересня", "жовтня",
           "листопада", "грудня"),
}

DAWKI_MG = (5, 10, 20, 40, 50, 75, 100, 150, 200, 250, 400, 500, 600, 850, 1000)

# Rodzaje tablic: litery bez samogłosek (ES), bez I/O/U (FR).
SPOLGLOSKI_ES = "BCDFGHJKLMNPRSTVWXYZ"
LITERY_FR = "ABCDEFGHJKLMNPQRSTVWXYZ"


# --------------------------------------------------------------------------------------------- baza
class BazowyGenerator:
    """Wspólna logika; kraje implementują hooki `_…` oraz `adres`, `sygnatura`, `sad`, `tablica`."""

    jezyk = ""
    kraje: tuple[str, ...] = ()
    #: wagi wyboru kraju (domyślnie równe)
    wagi_krajow: tuple[float, ...] | None = None

    def __init__(self, jezyk: str, ziarno: int = 0) -> None:
        self.jezyk = jezyk
        self.ziarno = ziarno
        self.rng = random.Random(f"pbench:{jezyk}:{ziarno}")
        #: style zapisu stałe w obrębie jednego dokumentu (ustawia budowa dokumentu): klucze `data`, `waluta`
        self.styl: dict[str, int] = {}
        #: kraj całego dokumentu w języku wielokrajowym (ustawia budowa dokumentu); None = losowanie per wywołanie
        self.kraj_dok: str | None = None
        #: stan USA całego dokumentu (EN/US; ustawia `losuj_stan_dok`) – adresy, telefony i sądy go preferują
        self.stan_dok: str | None = None
        #: najpóźniejsza data urodzenia kolejnej osoby (osoby pełniące funkcje muszą być pełnoletnie; ustawia budowa)
        self.max_ur: dt.date | None = None
        self._uzyte: set[tuple[str, str]] = set()
        self._uzyte_osoby: set[tuple] = set()

    # ----- słowniki
    def _s(self, plik: str) -> tuple[str, ...]:
        return slownik(self.jezyk, plik)

    def _kraj(self, kraj: str | None) -> str:
        if kraj is None:
            if self.kraj_dok is not None:
                return self.kraj_dok
            if len(self.kraje) == 1:
                return self.kraje[0]
            return self.rng.choices(self.kraje, weights=self.wagi_krajow)[0]
        if kraj not in self.kraje:
            raise ValueError(f"kraj {kraj!r} nie należy do języka {self.jezyk}: {self.kraje}")
        return kraj

    def losuj_stan_dok(self) -> None:
        """Hook budowy dokumentu: wybór regionu dokumentu po ustaleniu kraju (domyślnie nic; nie zużywa losowości)."""

    def _unikalny(self, typ: str, wartosc: str) -> bool:
        """Rejestruje wartość; False, gdy już była użyta."""
        klucz = (typ, wartosc)
        if klucz in self._uzyte:
            return False
        self._uzyte.add(klucz)
        return True

    # ----- hooki krajowe (nadpisywane)
    def _imie_nazwisko(self, plec: str, kraj: str) -> tuple[str, str]:
        imie = wagowo(self.rng, self._s("imiona_m" if plec == "M" else "imiona_k"))
        return imie, wagowo(self.rng, self._s("nazwiska"))

    def _ids_osoby(self, kraj: str, plec: str, data_ur: dt.date, nazwisko: str) -> dict[str, str]:
        raise NotImplementedError

    def _ids_firmy(self, kraj: str, forma: str) -> dict[str, str]:
        raise NotImplementedError

    def _formy(self, kraj: str) -> tuple[str, ...]:
        raise NotImplementedError

    def _kandydat_telefonu(self, kraj: str) -> str:
        raise NotImplementedError

    def _bban(self, kraj: str) -> str:
        raise NotImplementedError

    def _kwota_txt(self, calk: int, grosze: int, kraj: str) -> str:
        raise NotImplementedError

    def _data_txt(self, d: dt.date, kraj: str) -> str:
        raise NotImplementedError

    def adres(self, kraj: str | None = None) -> Adres:
        raise NotImplementedError

    def sygnatura(self, kraj: str | None = None, rodzaj: str | None = None, rok: int | None = None) -> str:
        """Sygnatura sprawy; `rodzaj` (repertorium, np. „C”) i `rok` (rok wpływu) – jeśli język je obsługuje."""
        raise NotImplementedError

    def sad(self, kraj: str | None = None, poziom: str | None = None) -> str:
        """Nazwa sądu; `poziom` (np. „rejonowy”, „okregowy”) zawęża wybór, jeśli język go obsługuje."""
        raise NotImplementedError

    def _nazwa_firmy(self, rdzen: str, forma: str, rodzaj: str) -> tuple[str, str]:
        """(nazwa, forma) firmy danego rodzaju (`firma|kancelaria|placowka`); domyślnie „rdzeń forma”."""
        return f"{rdzen} {forma}", forma

    def tablica(self, kraj: str | None = None) -> str:
        raise NotImplementedError

    def _urodzenia(self) -> tuple[dt.date, dt.date]:
        return dt.date(1940, 1, 1), dt.date(2005, 12, 31)

    # ----- konta
    def iban(self, kraj: str | None = None) -> str:
        k = self._kraj(kraj)
        bban = self._bban(k)
        return f"{k}{cyfry_kontrolne_iban(k, bban)}{bban}"

    def rachunek(self, kraj: str | None = None) -> str:
        return self.iban(kraj)

    # ----- telefon
    def telefon(self, kraj: str | None = None) -> str:
        """Fikcyjny numer w jednym z zapisów (krajowy, międzynarodowy, E.164 – wagi 4:4:1); `_kandydat_telefonu` zwraca E.164."""
        k = self._kraj(kraj)
        e164 = self._kandydat_telefonu(k)
        fmt = self.rng.choices(("krajowy", "miedzynarodowy", "e164"), weights=(4, 4, 1))[0]
        return self._formatuj_telefon(e164, fmt, k)

    def _formatuj_telefon(self, e164: str, fmt: str, kraj: str) -> str:
        """Zapis numeru E.164 (`+<kod kraju><numer>`) wg libphonenumber; kraje z własnym grupowaniem nadpisują."""
        num = phonenumbers.parse(e164, kraj)
        f = {"krajowy": phonenumbers.PhoneNumberFormat.NATIONAL,
             "miedzynarodowy": phonenumbers.PhoneNumberFormat.INTERNATIONAL,
             "e164": phonenumbers.PhoneNumberFormat.E164}[fmt]
        return phonenumbers.format_number(num, f)

    # ----- osoba, firma
    def login(self, osoba: Osoba | None = None) -> str:
        if osoba is not None:
            return self._login_z(osoba.imie, osoba.nazwisko)
        imie, nazwisko = self._imie_nazwisko(self.rng.choice("MK"), self._kraj(None))
        return self._login_z(imie, nazwisko)

    def _login_z(self, imie: str, nazwisko: str) -> str:
        i, n = ascii_(imie.split()[0]), ascii_(nazwisko.split()[0])
        wzor = self.rng.randrange(4)
        baza = (f"{i[0]}{n}", f"{i}.{n}", f"{i[0]}.{n}", f"{n}{i[0]}")[wzor]
        if self.rng.random() < 0.4:
            baza += str(self.rng.randint(1, 99))
        return baza

    def _email_osoby(self, imie: str, nazwisko: str, rok: int) -> str:
        i, n = ascii_(imie.split()[0]), ascii_(nazwisko.split()[0])
        for proba in range(1000):
            lokalna = self.rng.choice((f"{i}.{n}", f"{i[0]}.{n}", f"{i}{n}", f"{n}.{i}", f"{i[0]}{n}"))
            if proba or self.rng.random() < 0.3:
                lokalna += str(rok % 100 if proba == 0 else self.rng.randint(1, 9999))
            adres = f"{lokalna}@{self.rng.choice(DOMENY_EMAIL_JEZYK.get(self.jezyk, DOMENY_EMAIL))}"
            if self._unikalny("EMAIL", adres):
                return adres
        raise RuntimeError("brak unikalnego e-maila")  # pragma: no cover

    def osoba(self, kraj: str | None = None) -> Osoba:
        k = self._kraj(kraj)
        for _ in range(1000):
            plec = self.rng.choice("MK")
            imie, nazwisko = self._imie_nazwisko(plec, k)
            od, do = self._urodzenia()
            if self.max_ur is not None:
                do = min(do, self.max_ur)
            data_ur = losowa_data(self.rng, od, do)
            ids = self._ids_osoby(k, plec, data_ur, nazwisko)
            klucze = [(typ, w) for typ, w in ids.items()] + [("OSOBA", f"{imie}|{nazwisko}|{data_ur}")]
            if all(kl not in self._uzyte for kl in klucze):
                self._uzyte.update(klucze)
                break
        else:  # pragma: no cover
            raise RuntimeError("nie udało się wylosować unikalnej osoby")
        return Osoba(imie=imie, nazwisko=nazwisko, plec=plec, data_ur=data_ur, adres=self.adres(k),
                     telefon=self.telefon(k), email=self._email_osoby(imie, nazwisko, data_ur.year),
                     login=self._login_unikalny(imie, nazwisko), rachunek=self.rachunek(k), kraj=k, ids=ids)

    def _login_unikalny(self, imie: str, nazwisko: str) -> str:
        for _ in range(1000):
            l = self._login_z(imie, nazwisko)
            if self._unikalny("LOGIN", l):
                return l
        raise RuntimeError("brak unikalnego loginu")  # pragma: no cover

    def _email_firmy(self, slug: str) -> str:
        """Ogólny adres e-mail firmy w domenie zarezerwowanej (hook: EN nadpisuje angielskie części lokalne)."""
        return self.rng.choice(_EMAIL_FIRMY.get(self.jezyk, _EMAIL_FIRMY["pl"])).format(s=slug)

    def _slug_firmy(self, rdzen: str) -> str:
        """Slug z nazwy, cięty na granicy słowa (nie w środku słowa) do 24 znaków."""
        slug = ""
        for slowo in rdzen.split():
            kandydat = slug + ascii_(slowo)
            if len(kandydat) > 24 and slug:
                break
            slug = kandydat
        return slug[:24] or "firma"

    def firma(self, kraj: str | None = None, rodzaj: str = "firma") -> Firma:
        k = self._kraj(kraj)
        forma = self.rng.choice(self._formy(k))
        for _ in range(1000):
            rdzen = wagowo(self.rng, self._s("firmy_rdzenie"))
            ids = self._ids_firmy(k, forma)
            if all(kl not in self._uzyte for kl in ids.items()):
                self._uzyte.update(ids.items())
                break
        else:  # pragma: no cover
            raise RuntimeError("nie udało się wylosować unikalnej firmy")
        slug = self._slug_firmy(rdzen)
        email = self._email_firmy(slug)
        nazwa, forma = self._nazwa_firmy(rdzen, forma, rodzaj)
        return Firma(nazwa=nazwa, forma=forma, adres=self.adres(k), telefon=self.telefon(k),
                     email=email, rachunek=self.rachunek(k), kraj=k, rejestry=ids)

    # ----- pozostałe typy wartości
    def _pula(self, plik: str, profil: str | None) -> tuple[str, ...]:
        """Słownik `plik_profil_kraj` (kraj dokumentu małymi literami, np. `_us`), `plik_profil` albo ogólny `plik`."""
        if profil:
            kandydaci = ([f"{plik}_{profil}_{self.kraj_dok.lower()}"] if self.kraj_dok else []) + [f"{plik}_{profil}"]
            for nazwa in kandydaci:
                if (SLOWNIKI / self.jezyk / f"{nazwa}.txt").exists():
                    return self._s(nazwa)
        return self._s(plik)

    def diagnozy(self, n: int, profil: str | None = None, plec: str | None = None) -> list[str]:
        """`n` różnych rozpoznań ICD-10 z puli profilu (np. „kardiologia”), zgodnych z płcią pacjenta (`M|K`)."""
        pula = [w for w in self._pula("choroby", profil) if plec is None or kod_icd_plec(w) in (None, plec)]
        if profil and (SLOWNIKI / self.jezyk / f"choroby_{profil}_glowne.txt").exists():
            # rozpoznanie główne z osobnej puli (pasuje do stałej narracji szablonu), pozostałe z puli chorób współistniejących
            glowne = [w for w in self._s(f"choroby_{profil}_glowne") if plec is None or kod_icd_plec(w) in (None, plec)]
            pierwsze = self.rng.choice(glowne)
            reszta = [w for w in pula if w != pierwsze]
            return [pierwsze, *self.rng.sample(reszta, min(n - 1, len(reszta)))]
        return self.rng.sample(pula, min(n, len(pula)))

    def diagnoza(self, profil: str | None = None, plec: str | None = None) -> str:
        """Rozpoznanie ICD-10 w języku dokumentu, np. „J45.0 Astma oskrzelowa…”."""
        return self.diagnozy(1, profil, plec)[0]

    def leki(self, n: int, profil: str | None = None) -> list[str]:
        """`n` różnych leków z dawką; wpis słownika „nazwa|dawka;dawka” ogranicza dawki, bez „|” – dowolna."""
        wpisy = self.rng.sample(self._pula("leki", profil), n)
        wynik = []
        for w in wpisy:
            nazwa, _, dawki = w.partition("|")
            wynik.append(f"{nazwa} {self.rng.choice(dawki.split(';')) if dawki else self.rng.choice(DAWKI_MG)} mg")
        return wynik

    def lek(self, profil: str | None = None) -> str:
        return self.leki(1, profil)[0]

    def kwota(self, kraj: str | None = None) -> str:
        k = self._kraj(kraj)
        rzad = self.rng.choices((2, 3, 4, 5, 6, 7), weights=(2, 4, 4, 3, 2, 1))[0]
        calk = self.rng.randint(10 ** (rzad - 1), 10 ** rzad - 1)
        return self._kwota_txt(calk, self.rng.randint(0, 99), k)

    def data(self, kraj: str | None = None) -> str:
        """Data dokumentu (2019-01-01 … 2026-10-29) w formie pisanej w danym kraju."""
        d = losowa_data(self.rng, dt.date(2019, 1, 1), dt.date(2026, 10, 29))
        return self._data_txt(d, self._kraj(kraj))

    def formatuj_date(self, d: dt.date, kraj: str | None = None) -> str:
        """Dowolną datę (np. urodzenia) w formie pisanej w danym kraju."""
        return self._data_txt(d, self._kraj(kraj))

    def ip(self) -> str:
        r = self.rng
        los = r.random()
        if los < 0.15:
            return str(ipaddress.IPv6Address(0x20010DB8 << 96 | r.getrandbits(80)))
        if los < 0.50:
            return f"192.168.{r.randint(0, 254)}.{r.randint(1, 254)}"
        if los < 0.65:
            return f"10.{r.randint(0, 254)}.{r.randint(0, 254)}.{r.randint(1, 254)}"
        if los < 0.75:
            return f"172.{r.randint(16, 31)}.{r.randint(0, 254)}.{r.randint(1, 254)}"
        blok = r.choice(("192.0.2", "198.51.100", "203.0.113"))  # RFC 5737
        return f"{blok}.{r.randint(1, 254)}"

    def url(self) -> str:
        r = self.rng
        slug = self._slug_firmy(wagowo(r, self._s("firmy_rdzenie")))
        host = r.choice((f"www.{slug}.example.com", f"portal.{slug}.example.org", f"{slug}.example.net",
                         f"extranet.{slug}.test", f"{slug}.test"))
        sciezka = r.choice(("", "/", "/docs/" + cyfry(r, 5), "/client/" + cyfry(r, 6), "/case/" + cyfry(r, 4),
                            f"/files/{_SLOWO_UMOWA.get(self.jezyk, 'umowa')}-" + cyfry(r, 4) + ".pdf", "/login", "/portal/" + cyfry(r, 3)))
        return f"https://{host}{sciezka}"
