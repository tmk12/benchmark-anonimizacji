"""Generator wartości syntetycznych dla Ukrainy (język `uk`): РНОКПП, ЄДРПОУ, ID-картка, паспорт для виїзду за кордон,
IBAN UA, telefony +380, adresy w konwencji ukraińskiej, ТОВ/ПП/АТ/ФОП, sądy i numery spraw.

Słowniki (`slowniki/uk`) ułożone własnoręcznie z wiedzy ogólnej (częste imiona, imiona odojcowskie, nazwiska różnych typów,
miasta z obwodem, prefiksem kodu pocztowego i numerem strefowym) – bez żadnych danych z korpusu treningowego Privatizera.
Dane wyłącznie ukraińskie: adresy, instytucje, identyfikatory. Rosyjska PISOWNIA imion i nazwisk osób ukraińskich
(Александр, Ковалёв) jest dozwolonym przypadkiem (`pisownia_rosyjska_imion`): druga kolumna wpisu słownika po `|`;
osoba z taką pisownią ma `OsobaUK.pisownia_ru`.

Algorytmy (testy: `python-stdnum` `stdnum.ua.rntrc` / `stdnum.ua.edrpou` oraz wektory z ich dokumentacji):

* РНОКПП – 10 cyfr: liczba dni od 31.12.1899 do daty urodzenia (5 cyfr), 3 cyfry numeru, cyfra płci (nieparzysta – mężczyzna,
  parzysta – kobieta), cyfra kontrolna = (Σ cyfra·waga mod 11) mod 10, wagi −1, 5, 7, 9, 4, 6, 10, 5, 7;
* ЄДРПОУ – 8 cyfr, suma ważona mod 11 (wagi 1–7; dla numerów 30 000 000–60 000 000 wagi 7, 1–6; przy wyniku 10 wagi
  zwiększone o 2, a wynik 10 daje 0);
* IBAN UA – 29 znaków: `UA`, 2 cyfry kontrolne mod 97, 6 cyfr MFO i 19 cyfr rachunku;
* ID-картка – 9 cyfr bez publicznej sumy kontrolnej; paszport zagraniczny – 2 litery serii i 6 cyfr;
* telefony: wyraźnie fikcyjne – kod operatora `00` (`+380 00 123 45 67`, krajowo `0 00 123 45 67`), którego nie ma w planie
  numeracji; nie muszą przechodzić `phonenumbers.is_valid_number`.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
from dataclasses import dataclass

import phonenumbers

from ..translit import transliteruj
from .wspolne import Adres, BazowyGenerator, DAWKI_MG, MIESIACE, Osoba, cyfry, losowa_data, wagowo

# Kody regionów w numerach rejestracyjnych (pierwsza para liter): zamknięta lista z ДСТУ 4278:2004, dod. Б (28 kodów).
_KODY_REGIONOW = ("AA", "AB", "AC", "AE", "AH", "AI", "AK", "AM", "AO", "AP", "AT", "AX", "BA", "BB", "BC", "BE", "BH",
                  "BI", "BK", "BM", "BO", "BT", "BX", "CA", "CB", "CE", "CH", "II")
_OPERATORZY = ("50", "63", "66", "67", "68", "73", "91", "92", "93", "94", "95", "96", "97", "98", "99")
#: Kody MFO banków (6 cyfr) – własna lista wiarygodnych kodów z zakresu 300000–399999.
_MFO = ("300023", "300465", "305299", "320984", "322001", "325365", "351005", "380805", "300528", "339500",
        "380526", "334851", "322313", "351533")
_LITERY_TABLIC = "ABCEHIKMOPTX"
_LITERY_SERII = "ABCEHKMOPTX"
#: Sądy pierwszej instancji (nazwa, kod sądu w numerze sprawy – 3 cyfry): sądy powszechne (sprawy osób fizycznych,
#: ЦПК) – kody z rejestru sądów (court.gov.ua), wpisane ręcznie z wiedzy ogólnej, bez weryfikacji w rejestrze.
#: Nazwy sądów, co do których brak pewności (zmiany nazw rejonów), pominięto.
_SADY_POWSZECHNE = (("Шевченківський районний суд міста Києва", "761"), ("Дніпровський районний суд міста Києва", "755"),
                    ("Подільський районний суд міста Києва", "758"), ("Личаківський районний суд міста Львова", "463"),
                    ("Приморський районний суд міста Одеси", "522"), ("Центральний районний суд міста Миколаєва", "490"),
                    ("Вінницький міський суд Вінницької області", "127"),
                    ("Івано-Франківський міський суд Івано-Франківської області", "344"),
                    ("Тернопільський міськрайонний суд Тернопільської області", "607"),
                    ("Рівненський міський суд Рівненської області", "569"),
                    ("Луцький міськрайонний суд Волинської області", "161"))
#: Sądy gospodarcze pierwszej instancji (spory między przedsiębiorcami, ГПК).
_SADY_GOSPODARCZE = (("Господарський суд міста Києва", "910"), ("Господарський суд Львівської області", "914"),
                     ("Господарський суд Харківської області", "922"), ("Господарський суд Одеської області", "916"),
                     ("Господарський суд Полтавської області", "917"),
                     ("Господарський суд Дніпропетровської області", "904"))
#: Sąd apelacyjny (nigdy w miejscu sądu pierwszej instancji; tylko `sad(poziom="apelacja")`). „Київський апеляційний
#: господарський суд” zlikwidowano w 2018 r. – obecna nazwa: Північний апеляційний господарський суд.
_SADY_APELACYJNE = (("Північний апеляційний господарський суд", "910"),)
#: Prosta mapa rozpoznanie (kod ICD-10: trzy znaki albo pełny kod z kropką) -> leki ze słownika `leki.txt`.
_LEKI_DO_ROZPOZNAN: dict[str, tuple[str, ...]] = {
    "I10": ("Амлодипін", "Лозартан", "Еналаприл", "Периндоприл", "Бісопролол", "Індапамід"),
    "E11": ("Метформін", "Гліклазид"), "K29": ("Омепразол", "Пантопразол"), "K21": ("Омепразол", "Пантопразол"),
    "I25": ("Аторвастатин", "Ацетилсаліцилова кислота", "Бісопролол", "Розувастатин"),
    "J45": ("Беклометазон", "Сальбутамол", "Лоратадин"), "E66": ("Орлістат", "Метформін"),
    "E03": ("Левотироксин натрію",), "I48": ("Ривароксабан", "Бісопролол"),
    "M54": ("Ібупрофен", "Диклофенак"), "M51": ("Ібупрофен", "Диклофенак"), "M17": ("Диклофенак", "Ібупрофен"),
    "N39": ("Нітрофурантоїн", "Амоксицилін"), "D50": ("Заліза сульфат",), "J06": ("Ібупрофен", "Лоратадин"),
    "G43": ("Ібупрофен",), "J18": ("Амоксицилін", "Кларитроміцин"), "L20": ("Лоратадин",),
    "K80": ("Дротаверин",), "N40": ("Тамсулозин",), "I83": ("Диосмін",)}
_TYPY_MED = ("Міська лікарня", "Медичний центр", "Клінічна лікарня", "Поліклініка", "Діагностичний центр")
_RDZENIE_MED = ("№ 3", "№ 5", "№ 7", "Святого Миколая", "Святої Параскеви", "№ 11", "Оберіг", "Здоров’я родини")
#: Pary (imię, nazwisko), których generator nie zwraca (osoby publiczne: politycy, urzędnicy, sportowcy, artyści,
#: duchowni). Para dotyczy formy męskiej nazwiska (żeńska forma nazwisk na -енко/-ук/-ець jest taka sama).
_ZABRONIONE_PARY = frozenset({
    ("Тарас", "Шевченко"), ("Андрій", "Шевченко"), ("Олександр", "Усик"), ("Богдан", "Хмельницький"),
    # politycy, urzędnicy, dyplomaci
    ("Леонід", "Кравчук"), ("Надія", "Савченко"), ("Андрій", "Мельник"), ("Ігор", "Клименко"), ("Сергій", "Марченко"),
    ("Павло", "Петренко"), ("Анатолій", "Гриценко"), ("Олексій", "Гончаренко"), ("Юрій", "Бойко"),
    ("Олександр", "Мороз"), ("Сергій", "Лещенко"), ("Олександр", "Ткаченко"), ("Олександр", "Литвиненко"),
    # działacz powiązany z Rosją (przywódca ДНР)
    ("Олександр", "Захарченко"),
    # kultura, sport, Kościół
    ("Микола", "Лисенко"), ("Дмитро", "Гнатюк"), ("Андрій", "Ярмоленко"), ("Олександр", "Зінченко"),
    ("Віктор", "Петренко"), ("Святослав", "Шевчук"), ("Олена", "Кравець"),
    # uzupełnienie po przeglądzie puli (krytyk literacki, piłkarze, minister MSW, malarz, działacze, bank centralny, muzycy)
    ("Іван", "Дзюба"), ("Артем", "Дзюба"), ("Віталій", "Захарченко"), ("Юрій", "Шевчук"), ("Андрій", "Кузьменко"),
    ("Оксана", "Марченко"), ("Михайло", "Гаврилюк"), ("Михайло", "Бойчук"), ("Юрій", "Кравченко"),
    ("Ростислав", "Павленко"), ("Кирило", "Шевченко")})


# ----------------------------------------------------------------------------- nazwiska żeńskie
_ZENSKIE_UK = (("ський", "ська"), ("цький", "цька"), ("зький", "зька"), ("ий", "а"), ("ов", "ова"), ("єв", "єва"),
               ("ев", "ева"), ("ін", "іна"), ("їн", "їна"))
_ZENSKIE_RU = (("ский", "ская"), ("цкий", "цкая"), ("зкий", "зкая"), ("ый", "ая"), ("ой", "ая"), ("ов", "ова"),
               ("ёв", "ёва"), ("ев", "ева"), ("ин", "ина"))


def nazwisko_zenskie(nazwisko: str, ru: bool = False) -> str:
    """Żeńska forma nazwiska (Підгорний → Підгорна, Ковальов → Ковальова); pozostałe są niezmienne (Шевченко, Мельник).
    `ru` – rosyjska pisownia (Подгорный → Подгорная)."""
    for konc, zam in (_ZENSKIE_RU if ru else _ZENSKIE_UK):
        if nazwisko.endswith(konc) and len(nazwisko) > len(konc):
            return nazwisko[:-len(konc)] + zam
    return nazwisko


# ----------------------------------------------------------------------------- identyfikatory
def rnokpp(rng, data_ur: dt.date, plec: str) -> str:
    """РНОКПП osoby: dni od 31.12.1899 (5 cyfr), numer (3 cyfry), cyfra płci, cyfra kontrolna."""
    dni = (data_ur - dt.date(1899, 12, 31)).days
    baza = f"{dni:05d}{cyfry(rng, 3)}{rng.choice('13579' if plec == 'M' else '02468')}"
    return baza + str(sum(int(c) * w for c, w in zip(baza, (-1, 5, 7, 9, 4, 6, 10, 5, 7))) % 11 % 10)


def data_z_rnokpp(numer: str) -> dt.date:
    """Data urodzenia zakodowana w РНОКПП (pierwsze 5 cyfr = dni od 31.12.1899)."""
    return dt.date(1899, 12, 31) + dt.timedelta(days=int(numer[:5]))


def plec_z_rnokpp(numer: str) -> str:
    """Płeć z 9. cyfry РНОКПП (nieparzysta – M, parzysta – K)."""
    return "M" if int(numer[8]) % 2 else "K"


def edrpou(rng) -> str:
    """ЄДРПОУ: 8 cyfr (zakres 05 000 000 – 49 999 999: realne kody podmiotów zaczynają się od 0xxxxxxx–4xxxxxxx)
    z cyfrą kontrolną."""
    while True:
        baza = rng.randint(500_000, 4_999_999)
        numer = f"{baza:07d}"
        pelny = int(numer) * 10
        wagi = (7, 1, 2, 3, 4, 5, 6) if 30_000_000 <= pelny <= 60_000_000 else (1, 2, 3, 4, 5, 6, 7)
        r = sum(w * int(c) for w, c in zip(wagi, numer)) % 11
        if r >= 10:
            r = sum((w + 2) * int(c) for w, c in zip(wagi, numer)) % 11 % 10
        return numer + str(r)


# ----------------------------------------------------------------------------- osoba
@dataclass(frozen=True)
class OsobaUK(Osoba):
    """Osoba ukraińska: `imie`, `nazwisko`, imię po ojcu; `pelne_imie` to ПІБ (nazwisko, imię, imię po ojcu)."""

    po_batkovi: str = ""
    #: człony zapisane po rosyjsku (`imie`, `nazwisko`, `po_batkovi`), tylko te, które różnią się od ukraińskich
    ru_czesci: tuple[str, ...] = ()

    @property
    def pisownia_ru(self) -> bool:
        return bool(self.ru_czesci)

    @property
    def pelne_imie(self) -> str:
        return f"{self.nazwisko} {self.imie} {self.po_batkovi}".strip()

    @property
    def pola_dodatkowe(self) -> dict[str, tuple[str, str]]:
        """Dodatkowe pola gniazd `{rola.<pole>}` (tekst, kategoria): imię po ojcu, „Імʼя Прізвище”, „Імʼя По батькові”,
        „Прізвище І. П.” (`pib_skr`, spisy) i „І. П. Прізвище” (`skr_pib`, podpisy)."""
        skrot = " ".join(f"{x[0]}." for x in (self.imie, self.po_batkovi) if x)
        return {"po_batkovi": (self.po_batkovi, "OSOBA"), "pelne_im": (f"{self.imie} {self.nazwisko}", "OSOBA"),
                "im_po": (f"{self.imie} {self.po_batkovi}".strip(), "OSOBA"),
                "pib_skr": (f"{self.nazwisko} {skrot}".strip(), "OSOBA"),
                "skr_pib": (f"{skrot} {self.nazwisko}".strip(), "OSOBA")}


class GeneratorUK(BazowyGenerator):
    kraje = ("UA",)

    def __init__(self, jezyk="uk", ziarno=0):
        super().__init__(jezyk, ziarno)
        #: prawdopodobieństwo rosyjskiej pisowni (tam, gdzie słownik ją podaje); ustawia budowa przypadku
        self.p_ru = 0.0
        self._kod_strefy = "44"
        self._rodzaj_firmy = "firma"
        self._firma_w_toku = False
        #: płeć osoby fizycznej w nazwie ФОП (ustawia `_ids_firmy`, czyta `_nazwa_firmy`): РНОКПП i nazwa zgodne
        self._fop_plec = "M"
        #: kod ostatnio wylosowanego sądu – numer sprawy zaczyna się od kodu sądu dokumentu
        self._kod_sadu: str | None = None
        #: rozpoznania ostatnio wylosowane (`diagnozy`) – leki dobierane do rozpoznań
        self._rozpoznania: list[str] = []

    # ----- imiona i nazwiska
    def _pib(self, plec: str) -> tuple[str, str, str, tuple[str, ...]]:
        """(imię, nazwisko, imię po ojcu, człony w pisowni rosyjskiej) – ukraińskie albo rosyjskie wg `p_ru`."""
        r = self.rng
        for _ in range(100):
            imie_uk, _, imie_ru = wagowo(r, self._s("imiona_m" if plec == "M" else "imiona_k")).partition("|")
            naz_uk, _, naz_ru = wagowo(r, self._s("nazwiska")).partition("|")
            ojciec = wagowo(r, self._s("imiona_ojcow")).split("|")
            po_uk, po_ru = ojciec[0 if plec == "M" else 1], ojciec[2 if plec == "M" else 3]
            if (imie_uk, naz_uk) in _ZABRONIONE_PARY:
                continue
            if plec == "K":
                naz_uk, naz_ru = nazwisko_zenskie(naz_uk), (nazwisko_zenskie(naz_ru, ru=True) if naz_ru else "")
            ru = r.random() < self.p_ru
            if ru:
                imie, naz, po = imie_ru or imie_uk, naz_ru or naz_uk, po_ru
            else:
                imie, naz, po = imie_uk, naz_uk, po_uk
            roznice = tuple(n for n, a, b in (("imie", imie, imie_uk), ("nazwisko", naz, naz_uk),
                                              ("po_batkovi", po, po_uk)) if a != b)
            return imie, naz, po, roznice if ru else ()
        raise RuntimeError("brak dopuszczalnej pary imię-nazwisko")  # pragma: no cover

    def _imie_nazwisko(self, plec, kraj):
        imie, nazwisko, _, _ = self._pib(plec)
        return imie, nazwisko

    def osoba(self, kraj=None) -> OsobaUK:
        k = self._kraj(kraj)
        for _ in range(1000):
            plec = self.rng.choice("MK")
            imie, nazwisko, po, ru = self._pib(plec)
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
        return OsobaUK(imie=imie, nazwisko=nazwisko, plec=plec, data_ur=data_ur, adres=self.adres(k),
                       telefon=self.telefon(k), email=self._email_osoby(imie, nazwisko, data_ur.year),
                       login=self._login_unikalny(imie, nazwisko), rachunek=self.rachunek(k), kraj=k, ids=ids,
                       po_batkovi=po, ru_czesci=ru)

    def _ids_osoby(self, kraj, plec, data_ur, nazwisko):
        r = self.rng
        return {"RNOKPP": rnokpp(r, data_ur, plec), "DOWOD": "0" + cyfry(r, 8),
                "PASZPORT": "".join(r.choice(_LITERY_SERII) for _ in range(2)) + cyfry(r, 6)}

    @staticmethod
    def _lac(tekst: str) -> str:
        return transliteruj(tekst, "kmu2010")

    def _login_z(self, imie, nazwisko):
        return super()._login_z(self._lac(imie), self._lac(nazwisko))

    def _email_osoby(self, imie, nazwisko, rok):
        return super()._email_osoby(self._lac(imie), self._lac(nazwisko), rok)

    # ----- firmy
    def _formy(self, kraj):
        if self._rodzaj_firmy == "kancelaria":
            return ("АО",)       # адвокатське бюро zakłada jeden adwokat – nie pasuje do „керуючого партнера” i „та партнери”
        if self._rodzaj_firmy == "placowka":
            return ("КНП", "КНП", "ТОВ")
        if self._rodzaj_firmy == "spolka":
            return ("ТОВ",)
        return ("ТОВ",) * 5 + ("ПП",) * 2 + ("АТ", "ФОП", "ФОП")

    def firma(self, kraj=None, rodzaj="firma"):
        self._rodzaj_firmy, self._firma_w_toku = rodzaj, True
        try:
            f = super().firma(kraj, rodzaj)
        finally:
            self._rodzaj_firmy, self._firma_w_toku = "firma", False
        # domena e-mail wynika z nazwy firmy (nie z niezależnie wylosowanego rdzenia słownika)
        return dataclasses.replace(f, email=self._email_firmy(self._slug_firmy(self._rdzen_nazwy(f.nazwa, f.forma))))

    @staticmethod
    def _rdzen_nazwy(nazwa: str, forma: str) -> str:
        """Człon nazwy firmy wyróżniający ją w domenie e-mail: pierwsze nazwisko kancelarii/ФОП albo treść w «…»."""
        if forma == "ФОП":
            return nazwa.split()[1]
        wewnatrz = nazwa.partition("«")[2].rpartition("»")[0] or nazwa
        return wewnatrz.split(",")[0].split(" та ")[0].split(" і ")[0]

    def _ids_firmy(self, kraj, forma):
        if forma == "ФОП":
            r = self.rng
            self._fop_plec = r.choice("MK")     # ta sama płeć w nazwie ФОП (`_nazwa_firmy`) i w cyfrze płci РНОКПП
            return {"RNOKPP": rnokpp(r, losowa_data(r, dt.date(1960, 1, 1), dt.date(2003, 12, 31)), self._fop_plec)}
        return {"EDRPOU": edrpou(self.rng)}

    @staticmethod
    def _zluka(slowo: str) -> str:
        """Spójnik „та”/„і” wg miłozwuczności (po samogłosce „та”, po spółgłosce „і”)."""
        return "та" if slowo[-1:].lower() in "аеєиіїоуюя" else "і"

    def _nazwa_firmy(self, rdzen, forma, rodzaj):
        r = self.rng
        if rodzaj == "kancelaria":
            n1 = wagowo(r, self._s("nazwiska")).partition("|")[0]
            n2 = wagowo(r, self._s("nazwiska")).partition("|")[0]
            return r.choice((f"Адвокатське об’єднання «{n1} {self._zluka(n1)} партнери»",
                             f"Адвокатське об’єднання «{n1}, {n2} {self._zluka(n2)} партнери»",
                             f"Адвокатське об’єднання «{n1}»")), forma
        if rodzaj == "placowka":
            return f"{forma} «{r.choice(_TYPY_MED)} {r.choice(_RDZENIE_MED)}»", forma
        if forma == "ФОП":
            imie, naz, po, _ = self._pib(self._fop_plec)
            return f"ФОП {naz} {imie} {po}", forma
        return f"{forma} «{rdzen}»", forma

    def _slug_firmy(self, rdzen):
        return super()._slug_firmy(self._lac(rdzen))

    def _email_firmy(self, slug):
        return self.rng.choice(("office@{s}.example.com", "info@{s}.test", "contact.{s}@example.org",
                                "mail@{s}.example.net")).format(s=slug)

    # ----- adresy i telefony
    def adres(self, kraj=None):
        r = self.rng
        miasto, obwod, indeks, strefa = wagowo(r, self._s("miejscowosci")).split("|")
        self._kod_strefy = strefa
        kod = indeks + cyfry(r, 3) if miasto != "Київ" else f"0{r.randint(1, 4)}{cyfry(r, 3)}"
        numer = str(r.randint(1, 180)) + r.choice(("", "", "", "А", "Б"))
        if self._firma_w_toku:      # placówka medyczna zajmuje budynek – bez numeru biura
            numer += f", оф. {r.randint(1, 60)}" if r.random() < 0.5 and self._rodzaj_firmy != "placowka" else ""
        elif r.random() < 0.85:
            numer += f", кв. {r.randint(1, 140)}"
        return Adres(wagowo(r, self._s("ulice")), numer, kod, miasto, "UA", obwod)

    def _kandydat_telefonu(self, kraj):
        # brak oficjalnej puli fikcyjnej (NKRZI): kod operatora 00 nie istnieje w planie numeracji; 7 cyfr abonenta jak w realnym numerze
        return f"+38000{cyfry(self.rng, 7)}"

    def _formatuj_telefon(self, e164, fmt, kraj):
        d = e164[6:]            # 7 cyfr abonenta po +380 00
        grupy = f"{d[:3]} {d[3:5]} {d[5:]}"
        return {"krajowy": f"0 00 {grupy}", "miedzynarodowy": f"+380 00 {grupy}", "e164": e164}[fmt]

    def _bban(self, kraj):
        return self.rng.choice(_MFO) + cyfry(self.rng, 19)

    # ----- kwoty i daty
    def _kwota_txt(self, calk, grosze, kraj):
        s = f"{calk:,}".replace(",", " ")
        return f"{s},{grosze:02d} грн"       # w tekście ukraińskim „грн” (nie „UAH”)

    def _data_txt(self, d, kraj):
        slownie = f"{d.day} {MIESIACE['uk'][d.month - 1]} {d.year} р."
        if self.styl:       # styl stały w obrębie dokumentu: 0 – data słownie, 1 – zapis liczbowy dd.mm.rrrr
            return slownie if self.styl["data"] == 0 else f"{d:%d.%m.%Y}"
        return self.rng.choice((slownie, f"{d:%d.%m.%Y}"))

    # ----- sądy, sprawy, tablice
    def sygnatura(self, kraj=None, rodzaj=None, rok=None):
        """Numer sprawy sądowej: kod sądu / numer / rok (dwie cyfry), np. „761/12345/24”. Kod to kod ostatnio
        wylosowanego sądu (`sad`), a bez sądu – kod losowego sądu pierwszej instancji; `rodzaj` (`powszechny`,
        `gospodarczy`) zawęża wybór w tym drugim przypadku."""
        r = self.rng
        yy = (rok % 100) if rok else r.randint(15, 26)
        kod = self._kod_sadu
        if kod is None:
            pula = _SADY_GOSPODARCZE if rodzaj == "gospodarczy" else _SADY_POWSZECHNE
            kod = r.choice(pula)[1]
        return f"{kod}/{r.randint(1, 29999)}/{yy:02d}"

    def sad(self, kraj=None, poziom=None):
        """Nazwa sądu pierwszej instancji; `poziom`: `powszechny` (domyślnie – sprawy osób fizycznych, ЦПК),
        `gospodarczy` (spory przedsiębiorców, ГПК) albo `apelacja` (sąd apelacyjny). Zapamiętuje kod sądu dla numeru sprawy."""
        pula = {"gospodarczy": _SADY_GOSPODARCZE, "apelacja": _SADY_APELACYJNE}.get(poziom, _SADY_POWSZECHNE)
        nazwa, self._kod_sadu = self.rng.choice(pula)
        return nazwa

    def tablica(self, kraj=None):
        r = self.rng
        l = lambda: "".join(r.choice(_LITERY_TABLIC) for _ in range(2))
        return f"{r.choice(_KODY_REGIONOW)} {r.randint(1, 9999):04d} {l()}"

    # ----- medycyna
    def diagnozy(self, n, profil=None, plec=None):
        self._rozpoznania = super().diagnozy(n, profil, plec)
        return self._rozpoznania

    def _leki_do_rozpoznan(self) -> list[tuple[str, ...]]:
        """Dla każdego z ostatnio wylosowanych rozpoznań – nazwy pasujących leków (`_LEKI_DO_ROZPOZNAN`)."""
        return [_LEKI_DO_ROZPOZNAN.get(r.split(" ", 1)[0][:3], ()) for r in self._rozpoznania]

    def leki(self, n, profil=None):
        """`n` różnych leków z dawką i jednostką (słownik: „nazwa|dawki|jednostka”, domyślnie mg). Leki dobrane do
        rozpoznań z ostatniego `diagnozy` (dwa pierwsze – do rozpoznania głównego, trzeci – do kolejnego), brakujące
        ze słownika profilu."""
        pula = {w.partition("|")[0]: w for w in self._pula("leki", None)}
        pula_profilu = self._pula("leki", profil)
        do_rozpoznan = self._leki_do_rozpoznan()
        wybrane: list[str] = []
        for i in range(n):
            zrodlo = (0, 0, 1, 2)[i] if i < 4 else 0
            kolejnosc = [do_rozpoznan[zrodlo] if zrodlo < len(do_rozpoznan) else (), *do_rozpoznan]
            nazwa = next((l for lista in kolejnosc for l in self.rng.sample(list(lista), len(lista)) if l in pula and l not in wybrane), None)
            if nazwa is None:
                nazwa = next(w.partition("|")[0] for w in self.rng.sample(pula_profilu, len(pula_profilu))
                             if w.partition("|")[0] not in wybrane)
            wybrane.append(nazwa)
        wynik = []
        for nazwa in wybrane:
            dawki, _, jednostka = pula[nazwa].partition("|")[2].partition("|") if nazwa in pula else ("", "", "")
            wynik.append(f"{nazwa} {self.rng.choice(dawki.split(';')) if dawki else self.rng.choice(DAWKI_MG)} {jednostka or 'мг'}")
        return wynik
