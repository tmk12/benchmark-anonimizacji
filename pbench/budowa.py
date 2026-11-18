"""Budowa drzewa dokumentu z szablonu: encje ról, rozwiązywanie gniazd, gold.

Szablon (`Szablon`) = szkielet sekcji; sekcja (`Sekcja`) losuje od `min` do `max` bloków (`Blok`) i tworzy z nich
elementy jednego rodzaju. Tekst bloku zawiera gniazda `{rola.pole}`; `rola` odwzorowuje się (przez
`Szablon.role`) na rodzaj encji, a encje powstają z `Generator` (deterministycznie, w kolejności `Szablon.role`).

Rodzaje encji i pola gniazd
    osoba, lekarz, pacjent  pelne, imie, nazwisko, adres, miasto, kod, telefon, email, login, rachunek, data_ur,
                            pola identyfikatorów wg `Osoba.ids` (małymi literami: pesel, nip, dowod, paszport, nie,
                            dni, nuss, nino, nhs, ssn, steuer_id, svnr, personalausweis, kvnr, lanr, nir, rpps; alias `dni_nie` =
                            DNI albo NIE); pacjent dodatkowo diagnoza, diagnoza2, diagnoza3,
                            lek, lek2, lek3 (różne, z puli `Szablon.profil`, zgodne z płcią pacjenta)
    firma, kancelaria,      nazwa, adres, miasto, kod, telefon, email, rachunek, rejestry wg `Firma.rejestry`
                            (nip, regon, krs, vat, company_no, ein, cif, hrb, steuernr, siren, siret); ES, DE i FR dodatkowo
                            `registro` (zwykły tekst – „Registro Mercantil de Sevilla”, „Amtsgericht Köln”, „tribunal de
                            commerce de Lyon”, wg siedziby); FR dodatkowo `rcs` („RCS Lyon”) i `barreau` („barreau de Lyon”, zwykły tekst; także w roli `sad`)
    placowka                jak firma (placówka medyczna: osobna pula nazw – szpital, centrum medyczne)
    spolka                  jak firma, ale spółka z kapitałem w udziałach (ES: zawsze S.L.; DE: zawsze GmbH; FR: zawsze
                            SARL; inne języki: jak firma)
    ctx                     rola WBUDOWANA (bez deklaracji w `Szablon.role`): spójny kontekst dokumentu, patrz
                            `Kontekst` – daty w ustalonym porządku, kwoty w zależnościach, sygnatura rejestrowa
    sad                     nazwa (zwykły tekst – organ publiczny, miasto w nazwie nie jest gold), sygnatura (gold);
                            ES, DE i FR dodatkowo `miasto` (miasto siedziby sądu, zwykły tekst – „En Sevilla, a …”)
    sprawa                  sygnatura, kwota, data, tablica, ip, url (wszystko gold)
    cytat                   sygnatura, sprawa – cytat innego orzeczenia, ZWYKŁY TEKST (nie gold)

Rodzaj gramatyczny roli (wszystkie języki): `{rola.rodzaj:m|k}` albo `{rola.rodzaj:m|k|n}` – forma męska albo żeńska
wg płci osoby (firma, placówka, kancelaria: forma `n`, a przy dwóch formach – pierwsza), zwykły tekst (nie gold),
np. `{pozwany.rodzaj:pozwanego|pozwanej}`. Błędna liczba form albo rola bez płci/firmy → `ValueError`.

Numer akapitu: gniazdo `{#}` daje kolejny numer w dokumencie (1, 2, …) – numeracja bez luk mimo losowania bloków.
Wielkie litery: `{sad.nazwa:upper}` (nagłówki pism).

Jeden kraj na dokument: dla języka wielokrajowego (EN: GB i US) budowa losuje kraj RAZ (`Kontekst.kraj`, wagi
generatora) i ustawia `gen.kraj_dok` – wszystkie osoby, firmy, adresy, waluty, daty, sądy i sygnatury dokumentu
pochodzą z tego kraju. Warianty szablonu EN mają prefiks kraju (`gb_county`, `us_federal`…); wymuszony wariant
wymusza kraj. `Blok.wariant` pasuje, gdy równa się wariantowi, jest prefiksem wariantu przed `_` (`gb` pasuje do
`gb_county`) albo jest kodem kraju dokumentu (małymi literami).

Składnia gniazda: `{rola.pole}`, z przypadkiem `{klient.pelne:dop}` (tylko język pl, pola pelne|imie|nazwisko;
przypadki mian|dop|cel|bier|narz|msc), z częścią `{klient.pelne/1}` i `{klient.pelne/2}` (imię i reszta –
wartość rozbita na komórki/runy: obie części to osobne obiekty `Wartosc` z tym samym `id`; `/1` otwiera nowe
wystąpienie, `/2` dopełnia ostatnie). Gniazdo błędne (nieznana rola/pole/przypadek) → `ValueError` z jego nazwą.

Konwencje drzewa (czytają je renderery z zadań 5–7)
* `Wartosc.id` = `<rola>.<pole>#<n>`, n = numer wystąpienia w dokumencie. KLUCZEM ENCJI jest ROLA, czyli część
  `id` przed pierwszą kropką (`encja(wartosc_id)`): `klient.pelne#1` i `klient.nazwisko#2` to ta sama osoba.
  Wartość rozbita na części (`/1`, `/2`) ma jedno `id` dla wszystkich części.
  `waga_klucz` = kategoria. `Wartosc.miejsce` wynika z rodzaju elementu (`MIEJSCE_ELEMENTU`).
* `Element.atrybuty` to zawsze czysty JSON (dane osobowe żyją wyłącznie w `fragmenty`).
* `komorka`: `atrybuty={"tabela": k, "wiersz": i, "kolumna": j}` (k – numer tabeli w dokumencie, od 0).
  Blok komórkowy = jedna tabela; wiersze rozdziela `\\n`, komórki ` | `.
* `komentarz`: blok `<gniazdo autora> | <tekst>`; `fragmenty = [Wartosc autora, ": ", …]`,
  `atrybuty={"autor_fragment": 0}`.
* `zmiany`: blok `ins|del | <gniazdo autora> | <tekst>`; fragmenty jak w komentarzu,
  `atrybuty={"autor_fragment": 0, "typ": "ins"|"del"}`; tekst usunięty także wchodzi do linearyzacji.
* `pole` (pole formularza): blok `<etykieta> | <wartość>` (bez ` | ` – sama wartość); `fragmenty` to tylko
  wartość, etykieta w `atrybuty={"etykieta": …}`.
* `podpis`: imię i nazwisko pod pismem (renderer może je narysować jako obraz).
* Metadane (`Szablon.metadane`): wartość będąca jednym gniazdem staje się `Wartosc` (miejsce „metadane”),
  wartość bez gniazd – zwykłym napisem.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import random
import re
from dataclasses import dataclass, field

from . import odmiana_uk
from .dane.wspolne import BazowyGenerator, Firma, MIESIACE, Osoba, losowa_data, wagowo
from .homoglify import homoglify
from .linearyzacja import RODZAJE
from .model import Dokument, Element, Wartosc
from .odmiana_pl import PRZYPADKI, odmien, przyimek_przed
from .translit import SYSTEMY as SYSTEMY_TRANSLIT, transliteruj

# Klucze `Osoba.ids` / `Firma.rejestry` generatora -> kategoria Privatizera.
MAPA_KATEGORII: dict[str, str] = {
    "PESEL": "PESEL", "NIP": "NIP", "REGON": "REGON", "KRS": "KRS",
    "DOWOD": "DOWOD", "PASZPORT": "PASZPORT",
    "PERSONALAUSWEIS": "DOWOD",    # niemiecki dowód osobisty (numer alfanumeryczny) – kategoria dowodu
    "NIE": "DNI",                  # NIE (cudzoziemiec, Hiszpania) – kategoria „DNI / NIE”
    "DNI": "DNI", "NUSS": "NUSS", "CIF": "CIF",
    "NINO": "NINO", "NHS": "NHS", "SSN": "SSN", "EIN": "EIN",
    "STEUER_ID": "NR_PODATKOWY",   # niemiecki numer podatkowy osoby (kategoria zbiorcza, nie VAT)
    "SVNR": "SVNR", "NIR": "NIR",
    "KVNR": "KVNR",                # Krankenversichertennummer (Niemcy)
    "SIRET": "SIREN",              # SIRET (SIREN + NIC) – wspólna kategoria „SIREN / SIRET”
    "SIREN": "SIREN",
    "HRB": "NR_REJESTRU",          # Handelsregister B (Niemcy; spółki kapitałowe)
    "HRA": "NR_REJESTRU",          # Handelsregister A (Niemcy; KG, OHG, e. K.)
    "PR": "NR_REJESTRU",           # Partnerschaftsregister (Niemcy; PartG mbB)
    "STEUERNR": "NR_PODATKOWY",    # Steuernummer firmy (Niemcy; kategoria zbiorcza jak Steuer-ID osoby)
    "COMPANY_NO": "NR_REJESTRU",   # Companies House (Wielka Brytania); hiszpański Registro Mercantil – to samo
    "VAT": "VAT",
    "PWZ": "NR_ID",                # numer prawa wykonywania zawodu lekarza (PL)
    "GMC": "NR_ID", "NPI": "NR_ID",   # numer lekarza w GMC (GB) / NPI (USA)
    "COLEGIADO": "NR_ID",          # número de colegiado lekarza (Hiszpania)
    "LANR": "NR_ID",               # Lebenslange Arztnummer lekarza (Niemcy)
    "RPPS": "NR_ID",               # numer RPPS lekarza (Francja)
    "RNOKPP": "NR_PODATKOWY",      # РНОКПП (Ukraina): numer podatkowy osoby (także ФОП)
    "EDRPOU": "NR_REJESTRU",       # ЄДРПОУ (Ukraina): kod rejestru podmiotów
}

# Pozostałe pola gniazd -> kategoria (None = zwykły tekst, nie gold).
_KATEGORIE_POL: dict[str, str | None] = {
    "pelne": "OSOBA", "imie": "OSOBA", "nazwisko": "OSOBA", "adres": "ADRES", "miasto": "MIEJSCOWOSC",
    "kod": "KOD_POCZTOWY", "telefon": "TELEFON", "email": "EMAIL", "login": "LOGIN",
    "rachunek": "RACHUNEK",        # także „Routing No. …, Account No. …” (USA)
    "data_ur": "DATA_UR", "nazwa": "ORGANIZACJA",
    "diagnoza": None, "lek": None,   # rozpoznania (kod ICD + nazwa) i leki (z dawką) są tekstem dokumentu, nie gold
    "sygnatura": "SYGNATURA", "kwota": "KWOTA", "data": "DATA", "tablica": "NR_REJESTRACYJNY",
    "ip": "IP", "url": "URL",
}

#: Miejsce wartości zależne od rodzaju elementu, w którym stoi.
MIEJSCE_ELEMENTU: dict[str, str] = {
    "naglowek": "naglowek", "akapit": "tresc", "komorka": "tabela", "przypis": "przypis",
    "komentarz": "komentarz", "zmiany": "zmiany", "pole": "pole", "stopka": "stopka", "podpis": "tresc",
}

_RODZAJE_ENCJI = {"osoba", "lekarz", "pacjent", "firma", "kancelaria", "placowka", "spolka", "sad", "sad_gosp", "sprawa",
                  "cytat", "osoba_ua", "firma_ua"}
#: Sądy: `sad_gosp` (UK) – sąd gospodarczy (spór przedsiębiorców) niezależnie od wariantu dokumentu, `sad` – wg wariantu
_SADOWE = {"sad", "sad_gosp"}
_OSOBOWE = {"osoba", "lekarz", "pacjent", "osoba_ua"}
_FIRMOWE = {"firma", "kancelaria", "placowka", "spolka", "firma_ua"}
#: Encje z Ukrainy w dokumentach innego języka (warstwa trudna): dane z `GeneratorUK`, cyrylicą (i transliteracją)
_UKRAINSKIE = {"osoba_ua", "firma_ua"}
_POLA_ODMIENNE = {"pelne", "imie", "nazwisko"}
#: Pola osoby ukraińskiej odmieniane/transliterowane: pole -> (kolejność członów ПІБ dla `odmiana_uk.odmien`)
_POLA_UK = {"pelne": "NIP", "pelne_im": "IN", "im_po": "IP", "imie": "I", "nazwisko": "N", "po_batkovi": "P",
            "pib_skr": "", "skr_pib": ""}
_RODZAJE_CZLONOW_UK = {"N": "nazwisko", "I": "imie", "P": "po_batkovi"}

_SLOT = re.compile(r"\{([^{}]*)\}")
_SLOT_SKLADNIA = re.compile(r"([a-z_][a-z0-9_]*)\.([a-z0-9_]+)(?:/(\d+))?(?::([a-z0-9_]+(?:\+[a-z0-9_]+)*))?")
_SLOT_RODZAJ = re.compile(r"([a-z_][a-z0-9_]*)\.rodzaj(?::([^{}]*))?")

def encja(wartosc_id: str) -> str:
    """Klucz encji (rola) z `Wartosc.id`: część przed pierwszą kropką, np. `klient.pelne#1` -> `klient`."""
    return wartosc_id.split(".", 1)[0]


def _kategoria_klucza(klucz: str) -> str:
    try:
        return MAPA_KATEGORII[klucz]
    except KeyError:
        raise RuntimeError(f"klucz identyfikatora generatora {klucz!r} nie ma wpisu w MAPA_KATEGORII") from None


_PRZECIWKO = {"pl": "przeciwko", "en": "v.", "es": "contra", "de": "gegen", "fr": "c.", "uk": "проти"}

#: Stawka VAT / podatku od sprzedaży wg kraju dokumentu (faktury).
STAWKA_VAT = {"PL": 0.23, "GB": 0.20, "US": 0.0825, "ES": 0.21, "DE": 0.19, "FR": 0.20, "UA": 0.20}

#: Wariant szablonu -> (rodzaj sygnatury, poziom sądu) przekazywane do `Generator.sygnatura` / `Generator.sad`.
_SAD_WARIANTU = {
    "gb": ("county", "county"), "us": ("state", "state"),    # EN: warianty tylko krajowe (notatka, e-mail, zaświadczenie)
    "rejonowy": ("C", "rejonowy"), "okregowy": ("C", "okregowy"), "apelacyjny": ("Ca", "okregowy"),
    "gb_county": ("county", "county"), "gb_high": ("high", "high"), "gb_appeal": ("appeal", "appeal"),
    "us_federal": ("federal", "federal"), "us_state": ("state", "state"), "us_appeal": ("appeal", "appeal"),
    "es_primera": ("ordinario", "primera"), "es_apelacion": ("apelacion", "apelacion"),
    "de_amtsgericht": ("ag", "amtsgericht"), "de_landgericht": ("lg", "landgericht"),
    "de_einzelrichter": ("lg", "landgericht"), "de_berufung": ("berufung", "berufung"),
    "fr_tj_unique": ("tj", "tj"), "fr_tj_collegiale": ("tj", "tj"), "fr_appel": ("appel", "appel"),
}
#: Warianty drugiej instancji (łańcuch dat z apelacją) i warianty dużych roszczeń.
_APELACYJNE = frozenset({"apelacyjny", "gb_appeal", "us_appeal", "es_apelacion", "de_berufung", "fr_appel"})
_DUZE_ROSZCZENIA = frozenset({"okregowy", "gb_high", "us_federal"})
#: Warianty ES: juicio ordinario (cuantía > 6 000 €) w I instancji i apelacja do Audiencia Provincial.
_WARIANTY_ES = frozenset({"es_primera", "es_apelacion"})
#: Warianty DE: Amtsgericht (wartość sporu <= 5 000 €, § 23 GVG) i Berufung od jego wyroku do Landgericht (Beschwer > 600 €)
#: oraz Landgericht w I instancji (> 5 000 €; Kammer albo Einzelrichter).
_WARIANTY_DE_AG = frozenset({"de_amtsgericht", "de_berufung"})
_WARIANTY_DE_LG = frozenset({"de_landgericht", "de_einzelrichter"})
#: Warianty FR (kwoty w `Kontekst`): tribunal judiciaire (juge unique albo formation collégiale; roszczenie > 10 000 € –
#: postępowanie pisemne z obowiązkowym adwokatem) i cour d'appel od wyroku tribunal judiciaire (roszczenie nadal > 10 000 €).
#: Nominał jednego udziału w kapitale spółki wg kraju (grosze); domyślnie 50 (PL zł, ES €). DE: GmbH – Stammkapital
#: >= 25 000 €, więc udział 250 € (>= 120 udziałów w dokumencie).
#: FR: SARL – udział (part sociale) 10 €, więc kapitał 1 200–18 000 € (wybór benchmarku; bez powoływania minimum ustawowego).
NOMINAL_UDZIALU = {"DE": 250_00, "FR": 10_00}


# ----------------------------------------------------------------------------- szablon
@dataclass
class Blok:
    """Tekst z gniazdami `{rola.pole}` i role, które musi mieć szablon."""

    tekst_z_gniazdami: str
    wymagane_role: set[str] = field(default_factory=set)
    #: jeśli niepusty – blok wchodzi do dokumentu tylko w tym wariancie szablonu (`Szablon.warianty`)
    wariant: str = ""


@dataclass
class Sekcja:
    """Sekcja szablonu: z `bloki` losuje od `min` do `max` bloków (kolejność szablonu) jako elementy jednego rodzaju."""

    nazwa: str
    rodzaj_elementu: str
    bloki: list[Blok]
    min: int = 1
    max: int = 1


@dataclass
class Szablon:
    """Szkielet dokumentu; `role` mapuje rolę na rodzaj encji
    (osoba|lekarz|pacjent|firma|kancelaria|placowka|sad|sprawa|cytat)."""

    jezyk: str
    typ: str
    role: dict[str, str]
    sekcje: list[Sekcja]
    metadane: dict[str, str] = field(default_factory=dict)
    #: pula słowników medycznych („kardiologia”, „interna”) dla rozpoznań i leków pacjenta; pusty = pula ogólna
    profil: str = ""
    #: warianty dokumentu losowane raz na dokument (np. „rejonowy”, „okregowy”; EN: „gb_county”, „us_federal”);
    #: steruje `Blok.wariant`, sądem i – w językach wielokrajowych – krajem dokumentu (prefiks przed `_`)
    warianty: tuple[str, ...] = ()
    #: wszystkie osoby (rodzaj `osoba`) pełnią funkcje (zarząd, pełnomocnik, notariusz…): w dniu najwcześniejszej daty
    #: kontekstu mają >= 18 lat
    dorosli: bool = False
    #: przedmiot sporu (DE: „darlehen”, „kauf”, „delikt”, „werk”) – dobiera właściwy Senat BGH w cytowanych orzeczeniach
    przedmiot: str = ""
    #: warstwa trudna: wartości ról dostają `Wartosc.encja` (= rola), by warianty zapisu tej samej osoby były powiązane
    znacz_encje: bool = False
    #: warstwa trudna (H6b, polski): przyimek „z”/„w” przed gniazdem dostaje formę „ze”/„we”, gdy wymaga jej wartość
    #: (`odmiana_pl.przyimek_przed`: „ze Zbigniewem”, „we Wrocławiu”); trzon – bez zmian (sumy kontrolne)
    przyimki: bool = False


# ----------------------------------------------------------------------------- kontekst dokumentu
_ROMAN_KRS = ("V", "VIII", "XII", "XIII", "XIV")
_REJ_KRS = ("WA", "KR", "PO", "GD", "WR", "LU", "KA", "LD", "SZ", "BI")


class Kontekst:
    """Spójne daty i kwoty jednego dokumentu, losowane raz (gniazda `{ctx.<nazwa>}`, rola wbudowana `ctx`).

    Daty (kategoria DATA) mają ustalony porządek – łańcuch sporu: `umowa` < `termin_platnosci` < `wezwanie` <
    `termin_wezwania` < `pozew` < `rozprawa` < `wyrok` (< `apelacja` < `rozprawa_apel` < `wyrok_apel`), dalej
    `wyrok_koncowy`/`rozprawa_koncowa` (wg wariantu), `po_pozwie`, `przed_rozprawa`, `odp_termin`, `notatka_termin`,
    `zas_od` < `zas_wystaw` < `rozprawa` < `zas_do`; oraz niezależna data dokumentu `dok` (z `dok_termin`,
    `dok_pozniej`, `dok_sprzedaz`, `dok_termin_fv`, `umowa_dawna`, `od_dnia`, `dok_termin_dl`), medyczne `przyjecie` <
    `wypis` (= `dok`) < `kontrola`, `zwolnienie_do`, rejestrowe `kr_rejestracja` <= `kr_wpis` <= `dok`, życiorys
    `cv_studia` < `cv_od2` < `cv_do2` <= `cv_od1`. Wszystkie daty <= 2026-10-29 i przypadają w dni robocze (pon–pt; święta pomijamy).

    Kwoty (KWOTA, w groszach): `glowna` (roszczenie), `odsetki`, `koszty_wind`, `razem_wez` = suma tych trzech,
    `zasadzona` < `glowna`, `koszty_zast`, `oplata_pozwu`, `koszty_procesu` = zastępstwo + opłata + 17 zł (zawsze
    < `glowna`), `oplata_nieuisz` < `oplata_pozwu`, `koszty_apel`, `ugoda_rata`; faktura `kf1..kf3`, `netto`, `vat`,
    `brutto`; kapitał spółki z o.o. `kapital2` = (`udzialy1`+`udzialy2`) × 50 zł >= 5 000 zł, `kapital3` z trzema
    wspólnikami, `wartosc1..3`; lista płac `brutto_<i>`, `suma_<n>`, `zus_<n>`, `pit_<n>`; pozostałe `um_wyn`,
    `um_limit`, `um_kara`, `szkoda`, `zaliczka_ub` < `szkoda`, `cena`, `sporow`, `wyn_mies`, `dywidenda`,
    `zaliczka_kosztow`, `limit_odb`. Liczby (bez kategorii): `udzialy1..3`, `udzialy_suma3`, `glosy_za2`,
    `glosy_przeciw2`. `sygn_rej` – sygnatura akt rejestrowych KRS („WA.XIII NS-REJ.KRS/012345/24”, SYGNATURA).
    `sygn_rok` – rok wpływu sprawy: rok `pozew` (wariant „apelacyjny”: rok `apelacja`); sygnatury `sad`/`sprawa` go używają.

    Warianty (`Szablon.warianty`): „rejonowy” – pierwsza instancja w sądzie rejonowym (roszczenie <= 100 000 zł),
    „okregowy” – pierwsza instancja w sądzie okręgowym (roszczenie 100 000–500 000 zł), „apelacyjny” – apelacja
    rozpoznawana przez sąd okręgowy (roszczenie <= 100 000 zł; `wyrok_koncowy` = `wyrok_apel`).
    ES: „es_primera” (Juzgado de Primera Instancia, juicio ordinario, roszczenie > 6 000 €), „es_apelacion” (Audiencia
    Provincial, apelacja; łańcuch dat z apelacją); `sygn_pierwsza` i `sad_pierwsza` – sygnatura (gold) i nazwa sądu I
    instancji w prowincji dokumentu (wyrok apelacyjny).
    EN (kraj w `Kontekst.kraj`, waluta i format dat wg kraju, stawka podatku `STAWKA_VAT`): „gb_county” (County Court,
    roszczenie <= 100 000), „gb_high” (High Court, 100 000–500 000), „gb_appeal” (Court of Appeal; łańcuch dat z apelacją),
    „us_federal” (sąd okręgowy USA, roszczenie > 75 000), „us_state” (sąd stanowy, <= 100 000), „us_appeal” (sąd apelacyjny
    USA); samo „gb”/„us” (szablony bez poziomu sądu) – sąd hrabstwa / stanowy.
    DE: „de_amtsgericht” (Amtsgericht, wartość sporu 1 600–4 900 €), „de_landgericht” (Landgericht, Kammer, > 5 000 €),
    „de_einzelrichter” (Landgericht, Einzelrichter; kwoty jak wyżej), „de_berufung” (Landgericht jako sąd apelacyjny od
    wyroku Amtsgericht; łańcuch dat z apelacją, `sygn_pierwsza` i `sad_pierwsza` – Aktenzeichen i Amtsgericht I instancji);
    udział w kapitale spółki ma nominał `NOMINAL_UDZIALU` (DE 250 €, FR 10 €, `ctx.nominal`); `kosten_kl`/`kosten_bekl` –
    podział kosztów procesu w % (powód/pozwany) zgodny z `zasadzona`/`glowna`.
    FR: „fr_tj_unique” (Tribunal judiciaire, juge unique, roszczenie 10 000–59 000 €), „fr_tj_collegiale” (formation
    collégiale, 20 000–200 000 €), „fr_appel” (Cour d'appel od wyroku tribunal judiciaire, 12 500–100 000 €; łańcuch dat z apelacją,
    `sygn_pierwsza`/`sad_pierwsza` – numer RG i Tribunal judiciaire I instancji); `ctx.nr_gestion` – numéro de gestion
    Kbis („2015B01234”, rok = rok `kr_rejestracja`, NR_REJESTRU). Opłata sądowa (`oplata_pozwu`) we Francji nie występuje –
    szablony FR jej nie używają; `koszty_zast` to kwota z art. 700 CPC, `koszty_apel` – w apelacji.
    """

    OKRES = (dt.date(2018, 1, 1), dt.date(2023, 7, 1))   # początek łańcucha sporu (koniec <= 2026-10-29)
    DOK = (dt.date(2021, 1, 1), dt.date(2026, 10, 29))

    def __init__(self, gen: BazowyGenerator, wariant: str, kraj: str | None = None) -> None:
        self.gen, self.wariant = gen, wariant
        #: kraj dokumentu (jedyny kraj języka albo wybrany przez budowę); wymusza `gen._kraj(None)`
        self.kraj = kraj or gen.kraj_dok or gen.kraje[0]
        #: przedmiot sporu szablonu (ustawia `_Budowa`); steruje m.in. Senatem BGH w cytatach DE
        self.przedmiot = ""
        r = gen.rng
        D = dt.timedelta

        def roboczy(d: dt.date, kierunek: int) -> dt.date:
            """Najbliższy dzień roboczy (pon–pt) w kierunku `kierunek` (bez uwzględniania świąt)."""
            while d.weekday() >= 5:
                d += D(days=kierunek)
            return d

        def po(d: dt.date, lo: int, hi: int) -> dt.date:
            """Data o `lo..hi` dni od `d`, zawsze w dzień roboczy; przesunięcie wstecz, gdy przedział nie jest dodatni
            (zachowuje porządek dat „przed”), w przód w pozostałych przypadkach."""
            return roboczy(d + D(days=r.randint(lo, hi)), -1 if hi <= 0 else 1)

        d: dict[str, dt.date] = {}
        d["umowa"] = roboczy(losowa_data(r, *self.OKRES), -1)
        d["termin_platnosci"] = po(d["umowa"], 14, 365)
        d["wezwanie"] = po(d["termin_platnosci"], 5, 40)
        d["termin_wezwania"] = po(d["wezwanie"], 7, 14)
        d["pozew"] = po(d["termin_wezwania"], 5, 40)
        d["rozprawa"] = po(d["pozew"], 100, 400)
        d["wyrok"] = po(d["rozprawa"], 1, 14)
        d["apelacja"] = po(d["wyrok"], 20, 45)
        d["rozprawa_apel"] = po(d["apelacja"], 90, 250)
        d["wyrok_apel"] = po(d["rozprawa_apel"], 1, 14)
        apel = wariant in _APELACYJNE
        d["wyrok_koncowy"] = d["wyrok_apel"] if apel else d["wyrok"]
        d["rozprawa_koncowa"] = d["rozprawa_apel"] if apel else d["rozprawa"]
        d["po_pozwie"] = po(d["pozew"], 3, 30)
        d["odp_termin"] = po(d["pozew"], 14, 28)
        d["przed_rozprawa"] = po(d["rozprawa"], -90, -30)
        d["notatka_termin"] = po(d["przed_rozprawa"], 7, 25)
        d["zas_wystaw"] = po(d["rozprawa"], -10, -2)
        d["zas_od"] = po(d["zas_wystaw"], -20, -3)
        d["zas_do"] = po(d["rozprawa"], 5, 30)
        dok = d["dok"] = roboczy(losowa_data(r, *self.DOK), -1)
        d["dok_termin"] = po(dok, 7, 30)
        d["dok_pozniej"] = po(dok, 150, 365)
        d["dok_sprzedaz"] = po(dok, -10, 0)
        d["dok_termin_fv"] = po(dok, 14, 30)
        d["umowa_dawna"] = po(dok, -700, -100)
        d["od_dnia"] = po(dok, 0, 30)
        d["dok_termin_dl"] = po(dok, 30, 120)
        d["przyjecie"] = po(dok, -14, -2)
        d["wypis"] = dok
        d["kontrola"] = po(dok, 7, 30)
        d["zwolnienie_do"] = po(dok, 7, 21)
        d["kr_wpis"] = po(dok, -900, -5)
        d["kr_rejestracja"] = po(d["kr_wpis"], -3650, -30)
        d["cv_od1"] = po(dok, -1200, -300)
        d["cv_do2"] = po(d["cv_od1"], -60, 0)
        d["cv_od2"] = po(d["cv_do2"], -540, -180)
        d["cv_studia"] = po(d["cv_od2"], -300, -30)
        if gen.jezyk == "uk":       # UK: dyplom wydawany po sesji letniej (koniec czerwca – początek lipca), przed `cv_od2`
            rok = (d["cv_od2"] - D(days=30)).year
            studia = roboczy(dt.date(rok, 6, r.randint(20, 30)), -1)
            d["cv_studia"] = studia if studia < d["cv_od2"] else roboczy(dt.date(rok - 1, 6, r.randint(20, 30)), -1)
        self.daty = d
        self.sygn_rok = (d["apelacja"] if apel else d["pozew"]).year
        self.sygn_rodzaj, self.poziom_sadu = _SAD_WARIANTU.get(wariant, (None, None))

        def zl(lo: float, hi: float) -> int:      # losowa kwota w groszach, rozkład logarytmiczny
            return int(10 ** r.uniform(lo, hi)) * 100 + r.randint(0, 99)

        def czesc(kw: int, lo: float, hi: float) -> int:
            return round(kw * r.uniform(lo, hi))

        k: dict[str, int] = {}
        k["glowna"] = (zl(5.0, 5.7) if wariant in _DUZE_ROSZCZENIA else zl(3.8, 4.99) if wariant in _WARIANTY_ES
                       else zl(3.2, 3.69) if wariant in _WARIANTY_DE_AG else zl(3.72, 5.0) if wariant in _WARIANTY_DE_LG
                       else zl(4.01, 4.77) if wariant == "fr_tj_unique" else zl(4.31, 5.3) if wariant == "fr_tj_collegiale"
                       else zl(4.1, 5.0) if wariant == "fr_appel" else zl(3.5, 4.99) if wariant else zl(3.5, 5.6))
        k["odsetki"] = czesc(k["glowna"], 0.01, 0.12)
        k["koszty_wind"] = r.randint(50, 500) * 100
        k["razem_wez"] = k["glowna"] + k["odsetki"] + k["koszty_wind"]
        k["zasadzona"] = czesc(k["glowna"], 0.55, 0.95)
        k["koszty_zast"] = max(270_00, czesc(k["glowna"], 0.04, 0.08))
        k["oplata_pozwu"] = round(k["glowna"] * 0.05)
        k["koszty_procesu"] = k["koszty_zast"] + k["oplata_pozwu"] + 17_00
        k["oplata_nieuisz"] = czesc(k["oplata_pozwu"], 0.05, 0.4)
        k["koszty_apel"] = max(135_00, czesc(k["glowna"], 0.02, 0.04))
        k["ugoda_rata"] = czesc(k["glowna"], 0.1, 0.3)
        for n in ("kf1", "kf2", "kf3"):
            k[n] = zl(2.7, 4.3)
        k["netto"] = k["kf1"] + k["kf2"] + k["kf3"]
        k["vat"] = round(k["netto"] * STAWKA_VAT.get(self.kraj, 0.23))
        k["brutto"] = k["netto"] + k["vat"]
        u = [r.randint(60, 600) for _ in range(3)]
        nominal = NOMINAL_UDZIALU.get(self.kraj, 50_00)
        k["nominal"] = nominal
        for i, n in enumerate(u, 1):
            k[f"wartosc{i}"] = n * nominal
        k["kapital2"] = (u[0] + u[1]) * nominal
        k["kapital3"] = sum(u) * nominal
        k["dywidenda"] = czesc(k["kapital3"], 0.05, 0.5)
        self.liczby = {"udzialy1": u[0], "udzialy2": u[1], "udzialy3": u[2], "udzialy_suma3": sum(u),
                       "glosy_za2": u[0] + u[2], "glosy_przeciw2": u[1]}
        #: podział kosztów procesu w % (DE: „der Kläger zu 20 %, der Beklagte zu 80 %”) wg stosunku wygranej do żądania
        kosztow_powod = round((k["glowna"] - k["zasadzona"]) * 20 / k["glowna"]) * 5
        self.liczby |= {"kosten_kl": kosztow_powod, "kosten_bekl": 100 - kosztow_powod}
        k["um_wyn"] = r.randint(2500, 25000) * 100
        k["um_limit"] = czesc(k["um_wyn"], 0.2, 0.6)
        k["um_kara"] = czesc(k["um_wyn"], 1, 3)
        k["szkoda"] = (zl(3.3, 3.69) if wariant in _WARIANTY_DE_AG else zl(3.72, 4.8) if wariant in _WARIANTY_DE_LG
                       else zl(3.3, 4.8))
        k["zaliczka_ub"] = czesc(k["szkoda"], 0.2, 0.7)
        k["cena"] = zl(5.5, 7.3)
        k["sporow"] = czesc(k["cena"], 0.01, 0.1)
        k["wyn_mies"] = r.randint(4000, 30000) * 100
        k["zaliczka_kosztow"] = r.randint(500, 5000) * 100
        k["limit_odb"] = czesc(k["glowna"], 1.0, 1.5)
        self.kwoty = k
        self._brutto: list[int] = []
        self._cache: dict[str, tuple[str, str | None]] = {}
        wp = d["kr_wpis"].year % 100
        self._sygn_rej = f"{r.choice(_REJ_KRS)}.{r.choice(_ROMAN_KRS)} NS-REJ.KRS/{r.randint(1, 99999):06d}/{wp:02d}"

    def najpozniejsze_urodzenie(self) -> dt.date:
        """Data urodzenia osoby, która w najwcześniejszym dniu łańcucha dat dokumentu kończy dokładnie 18 lat."""
        d = min(self.daty.values())
        try:
            return d.replace(year=d.year - 18)
        except ValueError:      # 29 lutego
            return d.replace(year=d.year - 18, day=28)

    def _pensja(self, i: int) -> int:
        while len(self._brutto) <= i:
            self._brutto.append(self.gen.rng.randint(4300, 14000) * 100 + self.gen.rng.randint(0, 99))
        return self._brutto[i]

    def _kwota(self, grosze: int) -> str:
        return self.gen._kwota_txt(grosze // 100, grosze % 100, self.kraj)

    def _oblicz(self, nazwa: str) -> tuple[str, str | None]:
        if nazwa in self.daty:
            return self.gen.formatuj_date(self.daty[nazwa]), "DATA"
        if nazwa.endswith("_slownie") and nazwa[:-8] in self.daty and self.gen.jezyk == "uk":    # „п’ятнадцятого липня дві тисячі двадцять п’ятого року”
            return odmiana_uk.data_slownie_pelna(self.daty[nazwa[:-8]]), "DATA"
        if nazwa in self.kwoty:
            return self._kwota(self.kwoty[nazwa]), "KWOTA"
        if nazwa in self.liczby:
            v = self.liczby[nazwa]
            return (f"{v:,}".replace(",", " ") if self.gen.jezyk == "fr" else str(v)), None   # FR: „1 095”
        if nazwa == "sygn_rej":
            return self._sygn_rej, "SYGNATURA"
        pierwsza = {"es": ("ordinario", "primera"), "de": ("ag", "amtsgericht"), "fr": ("tj", "tj")}.get(self.gen.jezyk)
        if pierwsza and nazwa == "sygn_pierwsza":   # sprawa I instancji w apelacji (rok pozwu)
            return self.gen.sygnatura(rodzaj=pierwsza[0], rok=self.daty["pozew"].year), "SYGNATURA"
        if pierwsza and nazwa == "sad_pierwsza":    # sąd I instancji (zwykły tekst) w tym samym mieście
            return self.gen.sad(poziom=pierwsza[1]), None
        if self.gen.jezyk == "fr" and nazwa == "nr_gestion":      # numéro de gestion Kbis: rok immatriculation + B + numer
            return f"{self.daty['kr_rejestracja'].year}B{self.gen.rng.randint(1, 99999):05d}", "NR_REJESTRU"
        m = re.fullmatch(r"(brutto|suma|zus|pit)_(\d+)", nazwa)
        if m:
            n = int(m.group(2))
            if m.group(1) == "brutto":
                return self._kwota(self._pensja(n)), "KWOTA"
            suma = sum(self._pensja(i) for i in range(n))
            return self._kwota(round(suma * {"suma": 1, "zus": 0.2048, "pit": 0.11}[m.group(1)])), "KWOTA"
        raise KeyError(nazwa)

    def pole(self, nazwa: str) -> tuple[str, str | None]:
        """(tekst, kategoria) pola kontekstu; wartość raz policzona i zapamiętana. Nieznane pole → KeyError."""
        if nazwa not in self._cache:
            self._cache[nazwa] = self._oblicz(nazwa)
        return self._cache[nazwa]


# ----------------------------------------------------------------------------- encje ról
class _Encja:
    """Encja roli: pola liczone leniwie i zapamiętane (każde wystąpienie pola ma tę samą wartość)."""

    def __init__(self, rola: str, rodzaj: str, gen: BazowyGenerator, ctx: Kontekst, profil: str = "",
                 zakazane: frozenset[str] = frozenset(), dorosli: bool = False,
                 gen_dok: BazowyGenerator | None = None) -> None:
        if rodzaj not in _RODZAJE_ENCJI:
            raise ValueError(f"nieznany rodzaj encji {rodzaj!r} roli {rola!r}")
        self.rola, self.rodzaj, self.gen, self.ctx, self.zakazane = rola, rodzaj, gen, ctx, zakazane
        #: generator języka dokumentu (encje ukraińskie w dokumencie innego języka: daty w zapisie dokumentu)
        self.gen_dok = gen_dok
        gen.max_ur = ctx.najpozniejsze_urodzenie() if dorosli and rodzaj in ("osoba", "osoba_ua") else None
        try:
            self.osoba: Osoba | None = gen.osoba() if rodzaj in _OSOBOWE else None
        finally:
            gen.max_ur = None
        self.firma: Firma | None = (gen.firma(rodzaj=rodzaj) if rodzaj in ("kancelaria", "placowka", "spolka")
                                    else gen.firma() if rodzaj in ("firma", "firma_ua") else None)
        if rodzaj in _SADOWE:
            poziom = "gospodarczy" if rodzaj == "sad_gosp" else ctx.poziom_sadu
            self.sad_nazwa: str | None = gen.sad(poziom=poziom) if poziom else gen.sad()
            self.sad_miasto: str | None = getattr(gen, "miasto_sadu", None)
        else:
            self.sad_nazwa = self.sad_miasto = None
        self.diagnozy: list[str] = []
        self.leki: list[str] = []
        self.cyt_data: dt.date | None = None
        if rodzaj == "pacjent":
            assert self.osoba is not None
            self.diagnozy = gen.diagnozy(3, profil or None, self.osoba.plec)
            self.leki = gen.leki(3, profil or None)
        self._cache: dict[str, tuple[str, str | None]] = {}

    @property
    def _podmiot(self) -> Osoba | Firma | None:
        return self.osoba or self.firma

    def pole(self, nazwa: str) -> tuple[str, str | None]:
        """(tekst, kategoria) pola; kategoria None = zwykły tekst. Nieznane pole → KeyError."""
        if nazwa not in self._cache:
            self._cache[nazwa] = self._oblicz(nazwa)
        return self._cache[nazwa]

    def _data_cytatu(self) -> dt.date:
        """Data cytowanego orzeczenia: 4 miesiące – 3 lata przed datą orzeczenia dokumentu, w dzień roboczy (raz na rolę)."""
        if self.cyt_data is None:
            koniec = self.ctx.daty["wyrok_koncowy"]
            d = koniec - dt.timedelta(days=self.gen.rng.randint(120, 1095))
            while d.weekday() >= 5:          # orzeczenie zapada w dzień roboczy (pon–pt)
                d -= dt.timedelta(days=1)
            if self.gen.jezyk == "fr" and (d.month == 8 or (d.month == 7 and d.day >= 15)):
                d = dt.date(d.year, 9, 1)    # FR: nie w wakacjach sądowych (połowa lipca – sierpień); 1 IX lub najbliższy dzień roboczy
                while d.weekday() >= 5:
                    d += dt.timedelta(days=1)
            self.cyt_data = d
        return self.cyt_data

    def _nazwisko_cytatu(self) -> str:
        """Nazwisko rozłączne z każdym członem imienia/nazwiska/firmy gold w dokumencie (zwykły tekst ≠ gold)."""
        for _ in range(500):
            n = wagowo(self.gen.rng, self.gen._s("nazwiska"))
            if not {_token(t) for t in n.split()} & self.zakazane:
                return n
        raise RuntimeError("nie udało się wylosować nazwiska cytatu rozłącznego z gold")  # pragma: no cover

    def _oblicz(self, nazwa: str) -> tuple[str, str | None]:
        g, o, f = self.gen, self.osoba, self.firma
        if self.rodzaj == "cytat":
            if nazwa == "data":          # data cytowanego orzeczenia (zwykły tekst), zawsze przed datą dokumentu
                return g.formatuj_date(self._data_cytatu()), None
            if nazwa == "sygnatura":
                if hasattr(g, "sygnatura_cytatu"):
                    return g.sygnatura_cytatu(data=self._data_cytatu(), przedmiot=self.ctx.przedmiot), None
                return g.sygnatura(), None
            if nazwa == "sprawa":
                przeciw = "v" if g.jezyk == "en" and self.ctx.kraj == "GB" else _PRZECIWKO[g.jezyk]
                return f"{self._nazwisko_cytatu()} {przeciw} {self._nazwisko_cytatu()}", None
        elif self.rodzaj in _SADOWE:
            if nazwa == "nazwa":
                return self.sad_nazwa or "", None
            if nazwa == "miasto" and self.sad_miasto:
                return self.sad_miasto, None
            if nazwa == "barreau" and self.sad_miasto and hasattr(g, "barreau"):
                return g.barreau(self.sad_miasto), None
            if nazwa == "sygnatura":
                return g.sygnatura(rodzaj=self.ctx.sygn_rodzaj, rok=self.ctx.sygn_rok), "SYGNATURA"
        elif self.rodzaj == "sprawa":
            # EN: numer sprawy w formacie sądu dokumentu (County Court ↔ numer hrabstwa, sąd federalny ↔ 1:24-cv-…)
            sprawa_rodzaj = {"rodzaj": self.ctx.sygn_rodzaj} if g.jezyk in ("en", "de", "fr") else {}
            tresc = {"sygnatura": lambda: g.sygnatura(rok=self.ctx.sygn_rok, **sprawa_rodzaj), "kwota": g.kwota, "data": g.data, "tablica": g.tablica,
                     "ip": g.ip, "url": g.url}
            if nazwa in tresc:
                return tresc[nazwa](), _KATEGORIE_POL[nazwa]
        else:
            podmiot = self._podmiot
            assert podmiot is not None
            wspolne = {"adres": podmiot.adres.linia(), "miasto": podmiot.adres.miejscowosc,
                       "kod": podmiot.adres.kod, "telefon": podmiot.telefon, "email": podmiot.email,
                       "rachunek": podmiot.rachunek}
            if nazwa in wspolne:
                return wspolne[nazwa], _KATEGORIE_POL[nazwa]
            if o is not None:
                dodatkowe = getattr(o, "pola_dodatkowe", None)   # osoba ukraińska: imię po ojcu, „Імʼя Прізвище”…
                if dodatkowe is not None and nazwa in dodatkowe:
                    return dodatkowe[nazwa]
                data_ur = (self.gen_dok.formatuj_date(o.data_ur) if self.gen_dok is not None
                           else g.formatuj_date(o.data_ur, o.kraj))
                wlasne = {"pelne": o.pelne_imie, "imie": o.imie, "nazwisko": o.nazwisko, "login": o.login,
                          "data_ur": data_ur}
                if nazwa in wlasne:
                    return wlasne[nazwa], _KATEGORIE_POL[nazwa]
                m = re.fullmatch(r"(diagnoza|lek)([23]?)", nazwa)
                if self.rodzaj == "pacjent" and m:
                    lista = self.diagnozy if m.group(1) == "diagnoza" else self.leki
                    return lista[int(m.group(2) or 1) - 1], None    # poza gold (zob. `_KATEGORIE_POL`)
                ids = {k.lower(): (v, _kategoria_klucza(k)) for k, v in o.ids.items()}
                if "dni" in ids or "nie" in ids:
                    ids["dni_nie"] = ids.get("dni") or ids["nie"]
                if nazwa in ids:
                    return ids[nazwa]
            if f is not None:
                if nazwa == "nazwa":
                    return f.nazwa, "ORGANIZACJA"
                if nazwa == "registro" and hasattr(g, "nazwa_rejestru"):
                    return g.nazwa_rejestru(f.adres), None
                if nazwa == "rcs" and hasattr(g, "rcs"):
                    return g.rcs(f.adres), None
                if nazwa == "barreau" and hasattr(g, "barreau"):
                    return g.barreau(f.adres), None
                rejestry = {k.lower(): (v, _kategoria_klucza(k)) for k, v in f.rejestry.items()}
                if nazwa in rejestry:
                    return rejestry[nazwa]
        raise KeyError(nazwa)


def _token(t: str) -> str:
    return t.strip(".,;:()\"'").casefold()


def _tokeny_gold(encje: list[_Encja]) -> frozenset[str]:
    """Człony imion/nazwisk/nazw firm gold (także odmienione), których cytat nie może użyć."""
    wynik: set[str] = set()
    for e in encje:
        if e.osoba is not None:
            o = e.osoba
            formy = [o.imie, o.nazwisko]
            if e.gen.jezyk == "pl":
                formy += [odmien(o.imie, o.nazwisko, o.plec, p) for p in PRZYPADKI]
            wynik.update(_token(t) for f in formy for t in f.split())
        if e.firma is not None:
            wynik.update(_token(t) for t in e.firma.nazwa.split())
    return frozenset(wynik)


# ----------------------------------------------------------------------------- budowa
class _Budowa:
    def __init__(self, szablon: Szablon, gen: BazowyGenerator, rng: random.Random,
                 wariant: str | None = None, wspolne: Wynik | None = None) -> None:
        if gen.jezyk != szablon.jezyk:
            raise ValueError(f"język generatora ({gen.jezyk}) różni się od języka szablonu ({szablon.jezyk})")
        if wspolne is not None:
            wariant = wspolne.kontekst.wariant   # wspólny kontekst = ten sam wariant (i kraj) dokumentu
        if wariant and wariant not in szablon.warianty:
            raise ValueError(f"wariant {wariant!r} nie należy do wariantów szablonu: {szablon.warianty}")
        self.szablon, self.gen, self.rng = szablon, gen, rng
        if wspolne is None:
            gen.styl = {"data": gen.rng.randrange(2), "waluta": gen.rng.randrange(2)}   # jeden styl na dokument
            kraj, wybrany = self._kraj_i_wariant(szablon, gen, wariant)
            gen.kraj_dok = kraj if len(gen.kraje) > 1 else None   # jeden kraj na dokument (EN: GB albo US)
            gen.losuj_stan_dok()                                   # EN/US: stan dokumentu (adresy, telefony, sądy)
            self.ctx = Kontekst(gen, wybrany, kraj)
            self.ctx.przedmiot = szablon.przedmiot
        else:   # załącznik tego samego zdarzenia: kontekst, styl i kraj jak w dokumencie `wspolne`
            self.ctx = wspolne.kontekst
        #: przypisanie zapisów łacińskich gniazd `:t_s1…t_s3` (`cyr` = oryginał); ustawia budowa przypadku warstwy trudnej
        natur = {"pl": "polski", "de": "niemiecki"}.get(szablon.jezyk, "kmu2010")
        self.systemy: dict[str, str] = {"s1": natur, "s2": "cyr", "s3": "cyr", "s4": "cyr"} | getattr(gen, "systemy_translit", {})
        self.encje = {}
        self.gen_ua: BazowyGenerator | None = None
        for rola, rodzaj in szablon.role.items():
            if rodzaj == "cytat":
                continue
            wsp = wspolne.encje.get(rola) if wspolne is not None else None
            if rodzaj in _UKRAINSKIE:   # Ukraina w dokumencie innego języka: osobny generator (ziarno z ziarna dokumentu)
                if self.gen_ua is None:
                    from .dane.uk import GeneratorUK
                    self.gen_ua = GeneratorUK("uk", int.from_bytes(hashlib.sha256(f"ua:{gen.ziarno}".encode()).digest()[:6], "big"))
                    self.gen_ua.p_ru = getattr(gen, "p_ru_ua", 0.0)
                    self.gen_ua.styl = dict(gen.styl)
                self.encje[rola] = _Encja(rola, rodzaj, self.gen_ua, self.ctx, szablon.profil, dorosli=szablon.dorosli,
                                          gen_dok=gen)
                continue
            self.encje[rola] = (wsp if wsp is not None and wsp.rodzaj == rodzaj else
                                _Encja(rola, rodzaj, gen, self.ctx, szablon.profil, dorosli=szablon.dorosli))
        zakazane = _tokeny_gold(list(self.encje.values()))
        for rola, rodzaj in szablon.role.items():  # cytaty po wszystkich encjach – nazwiska rozłączne z gold
            if rodzaj == "cytat":
                self.encje[rola] = _Encja(rola, rodzaj, gen, self.ctx, szablon.profil, zakazane)
        self.liczniki: dict[str, int] = {}   # "<rola>.<pole>" -> ostatni numer wystąpienia
        self.tabele = 0
        self.numer_akapitu = 0
        self._sprawdz()

    @staticmethod
    def _kraj_i_wariant(szablon: Szablon, gen: BazowyGenerator, wariant: str | None) -> tuple[str, str]:
        """Kraj dokumentu i wariant. Język jednokrajowy: bez dodatkowego losowania kraju. Wielokrajowy: wymuszony
        wariant z prefiksem kraju (`gb_…`) wymusza kraj; inaczej kraj losowany (wagi generatora), a wariant – spośród
        wariantów tego kraju (gdy szablon nie ma wariantów z prefiksem kraju – spośród wszystkich)."""
        if len(gen.kraje) == 1:
            return gen.kraje[0], wariant or (gen.rng.choice(szablon.warianty) if szablon.warianty else "")
        kody = {k.lower(): k for k in gen.kraje}
        if wariant:
            return kody.get(wariant.split("_")[0]) or gen._kraj(None), wariant
        kraj = gen.rng.choices(gen.kraje, weights=gen.wagi_krajow)[0]
        pasujace = [w for w in szablon.warianty if w.split("_")[0] == kraj.lower()] or list(szablon.warianty)
        return kraj, gen.rng.choice(pasujace) if pasujace else ""

    def _pasuje(self, znacznik: str) -> bool:
        """Czy blok ze znacznikiem wariantu wchodzi do dokumentu (pusty = zawsze; patrz docstring modułu)."""
        w = self.ctx.wariant
        return (not znacznik or znacznik == w or w.startswith(znacznik + "_")
                or znacznik == self.ctx.kraj.lower())

    def _sprawdz(self) -> None:
        for sekcja in self.szablon.sekcje:
            if sekcja.rodzaj_elementu not in RODZAJE:
                raise ValueError(f"nieznany rodzaj elementu {sekcja.rodzaj_elementu!r} w sekcji {sekcja.nazwa!r}")
            if not 0 <= sekcja.min <= sekcja.max:
                raise ValueError(f"niepoprawne min/max sekcji {sekcja.nazwa!r}")
            for blok in sekcja.bloki:
                brak = blok.wymagane_role - set(self.szablon.role) - {"ctx"}
                if brak:
                    raise ValueError(f"blok wymaga ról spoza szablonu: {sorted(brak)}")

    # ----- gniazda
    def _rodzaj(self, gniazdo: str, rola: str, formy: str | None) -> str:
        """Forma rodzaju gramatycznego roli: `m|k` albo `m|k|n` (osoba wg płci; firma – `n` albo pierwsza)."""
        encja = self.encje.get(rola)
        if encja is None:
            raise ValueError(f"gniazdo {gniazdo}: rola {rola!r} nie występuje w szablonie")
        lista = (formy or "").split("|")
        if not 2 <= len(lista) <= 3 or not all(lista):
            raise ValueError(f"gniazdo {gniazdo}: rodzaj wymaga dwóch (m|k) albo trzech (m|k|n) form")
        if encja.osoba is not None:
            return lista[0 if encja.osoba.plec == "M" else 1]
        if encja.firma is not None:
            return lista[-1] if len(lista) == 3 else lista[0]
        raise ValueError(f"gniazdo {gniazdo}: rodzaj ma tylko rola osoby albo firmy, nie {encja.rodzaj!r}")

    def _gniazdo(self, tresc: str, miejsce: str) -> str | Wartosc:
        gniazdo = "{" + tresc + "}"
        if tresc == "#":                     # kolejny numer akapitu w dokumencie (bez luk mimo losowania bloków)
            self.numer_akapitu += 1
            return str(self.numer_akapitu)
        r = _SLOT_RODZAJ.fullmatch(tresc)
        if r is not None:
            return self._rodzaj(gniazdo, r.group(1), r.group(2))
        m = _SLOT_SKLADNIA.fullmatch(tresc)
        if m is None:
            raise ValueError(f"niepoprawna składnia gniazda {gniazdo}")
        rola, pole, czesc, przyp = m.group(1), m.group(2), m.group(3), m.group(4)
        if rola == "ctx":
            if przyp is not None or czesc is not None:
                raise ValueError(f"gniazdo {gniazdo}: kontekst nie ma przypadków ani części")
            try:
                tekst, kategoria = self.ctx.pole(pole)
            except KeyError:
                raise ValueError(f"gniazdo {gniazdo}: pole {pole!r} nie istnieje w kontekście dokumentu") from None
            encja = None
        else:
            encja = self.encje.get(rola)
            if encja is None:
                raise ValueError(f"gniazdo {gniazdo}: rola {rola!r} nie występuje w szablonie")
            try:
                tekst, kategoria = encja.pole(pole)
            except KeyError:
                raise ValueError(f"gniazdo {gniazdo}: pole {pole!r} nie istnieje dla encji {encja.rodzaj!r}") from None
        translit = None
        cechy: list[str] = []
        if przyp == "upper":                 # wielkie litery (nagłówki pism: „IN THE COUNTY COURT AT BRISTOL”)
            tekst = tekst.upper()
        elif przyp is not None:
            tekst, translit, cechy = self._modyfikatory(gniazdo, encja, pole, tekst, przyp)
        if (encja is not None and pole in _POLA_UK
                and any(_RODZAJE_CZLONOW_UK[k] in getattr(encja.osoba, "ru_czesci", ()) for k in _POLA_UK[pole])):
            cechy.append("pisownia_rosyjska")
        if czesc is not None:
            części = tekst.split(" ", 1)
            if czesc not in ("1", "2") or len(części) != 2:
                raise ValueError(f"gniazdo {gniazdo}: część {czesc} wymaga wartości z dwóch słów (część 1 lub 2)")
            tekst = części[int(czesc) - 1]
        if kategoria is None:
            return tekst
        klucz = f"{rola}.{pole}"
        if czesc == "2":
            if klucz not in self.liczniki:
                raise ValueError(f"gniazdo {gniazdo}: część 2 bez wcześniejszej części 1")
        else:
            self.liczniki[klucz] = self.liczniki.get(klucz, 0) + 1
        return Wartosc(f"{klucz}#{self.liczniki[klucz]}", kategoria, tekst, self.szablon.jezyk, miejsce, kategoria,
                       translit, rola if self.szablon.znacz_encje and encja is not None else None, cechy)

    def _modyfikatory(self, gniazdo: str, encja: _Encja | None, pole: str, tekst: str,
                      przyp: str) -> tuple[str, str | None, list[str]]:
        """Modyfikatory gniazda po dwukropku, łączone znakiem `+`: przypadek (`dop`, `rod`…), `t_<system>` (transliteracja
        cyrylicy, zob. `pbench.translit`), `homoglif` (wmieszane litery o podobnym kształcie), `upper`. Kolejność
        wykonania: transliteracja, odmiana (język dokumentu), homoglify, wielkie litery. Zwraca (tekst, system, cechy)."""
        przypadek = system = None
        homoglif = wielkie = False
        for m in przyp.split("+"):
            if m == "upper":
                wielkie = True
            elif m == "homoglif":
                homoglif = True
            elif m.startswith("t_"):
                system = self.systemy.get(m[2:], m[2:])       # t_s1…t_s3: zapis przypisany przez budowę przypadku
                if system == "cyr":                           # zapis oryginalny (cyrylica), bez transliteracji
                    system = None
                elif system not in SYSTEMY_TRANSLIT:
                    raise ValueError(f"gniazdo {gniazdo}: nieznany system transliteracji {system!r}")
            elif przypadek is None:
                przypadek = m
            else:
                raise ValueError(f"gniazdo {gniazdo}: dwa przypadki ({przypadek!r}, {m!r})")
        o = encja.osoba if encja is not None else None
        uk_osoba = o is not None and hasattr(o, "po_batkovi") and pole in _POLA_UK
        czlony = {"nazwisko": o.nazwisko, "imie": o.imie, "po_batkovi": o.po_batkovi} if uk_osoba else {}
        if system is not None:
            lac = {k: transliteruj(v, system, rosyjska=k in getattr(o, "ru_czesci", ())) for k, v in czlony.items()}   # zapis łaciński członów
            if przypadek is None:
                if uk_osoba and _POLA_UK[pole]:
                    tekst = " ".join(lac[_RODZAJE_CZLONOW_UK[k]] for k in _POLA_UK[pole])
                else:
                    tekst = transliteruj(tekst, system)
            elif uk_osoba and self.szablon.jezyk == "pl" and pole in ("pelne_im", "imie", "nazwisko"):
                imie, nazwisko = [lac[k] if kod in _POLA_UK[pole] else "" for k, kod in (("imie", "I"), ("nazwisko", "N"))]
                tekst = odmien(imie, nazwisko, o.plec, przypadek, ukrainskie=True)    # odmiana polska zapisu łacińskiego
            else:
                raise ValueError(f"gniazdo {gniazdo}: transliteracja z przypadkiem tylko dla pól imie|nazwisko|pelne_im "
                                 "osoby ukraińskiej w dokumencie pl")
        elif przypadek is not None:
            if przyp.startswith("t_") or "+t_" in przyp:
                raise ValueError(f"gniazdo {gniazdo}: zapis oryginalny (cyrylica) nie ma odmiany w dokumencie {self.szablon.jezyk}")
            if uk_osoba and self.szablon.jezyk == "uk" and _POLA_UK[pole]:
                tekst = odmiana_uk.odmien(o.imie, o.po_batkovi, o.nazwisko, o.plec, przypadek, _POLA_UK[pole])
            else:
                tekst = self._odmien(gniazdo, encja, pole, przypadek)
        cechy: list[str] = []
        if homoglif:
            tekst = homoglify(tekst)
            cechy.append("homoglify")
        return (tekst.upper() if wielkie else tekst), system, cechy

    def _odmien(self, gniazdo: str, encja: _Encja, pole: str, przyp: str) -> str:
        if self.szablon.jezyk != "pl":
            raise ValueError(f"gniazdo {gniazdo}: odmiana przez przypadki tylko w języku pl")
        if przyp not in PRZYPADKI or pole not in _POLA_ODMIENNE or encja.osoba is None:
            raise ValueError(f"gniazdo {gniazdo}: odmiana ({'|'.join(PRZYPADKI)}) tylko dla pól "
                             f"{'|'.join(sorted(_POLA_ODMIENNE))} osoby")
        o = encja.osoba
        if hasattr(o, "po_batkovi"):
            raise ValueError(f"gniazdo {gniazdo}: osoba ukraińska w dokumencie pl odmienia się tylko po transliteracji (:t_<system>+<przypadek>)")
        imie, nazwisko = {"pelne": (o.imie, o.nazwisko), "imie": (o.imie, ""), "nazwisko": ("", o.nazwisko)}[pole]
        return odmien(imie, nazwisko, o.plec, przyp)

    def _fragmenty(self, tekst: str, miejsce: str) -> list[str | Wartosc]:
        wynik: list[str | Wartosc] = []

        def dodaj_tekst(t: str) -> None:
            if "{" in t or "}" in t:
                raise ValueError(f"niezamknięte lub błędne gniazdo w tekście {t!r}")
            if (t.startswith(".") and wynik and isinstance(wynik[-1], Wartosc) and wynik[-1].kategoria == "DATA"
                    and wynik[-1].tekst.endswith(("r.", "р."))):
                t = t[1:]      # „2024 r.” kończy już zdanie – bez podwójnej kropki
            if t:
                if wynik and isinstance(wynik[-1], str):
                    wynik[-1] += t
                else:
                    wynik.append(t)

        poz = 0
        for m in _SLOT.finditer(tekst):
            dodaj_tekst(tekst[poz:m.start()])
            f = self._gniazdo(m.group(1), miejsce)
            if self.szablon.przyimki and wynik and isinstance(wynik[-1], str) and \
                    (nowy := przyimek_przed(wynik[-1], f if isinstance(f, str) else f.tekst)) is not None:
                wynik[-1] = nowy
            if isinstance(f, str):
                dodaj_tekst(f)
            else:
                wynik.append(f)
            poz = m.end()
        dodaj_tekst(tekst[poz:])
        return wynik

    def _autor(self, tekst: str, miejsce: str) -> Wartosc:
        if _SLOT.fullmatch(tekst) is None:
            raise ValueError(f"autor musi być jednym gniazdem, jest: {tekst!r}")
        frag = self._fragmenty(tekst, miejsce)
        if len(frag) != 1 or not isinstance(frag[0], Wartosc):
            raise ValueError(f"gniazdo autora {tekst} nie daje wartości gold")
        return frag[0]

    # ----- elementy
    def _elementy(self, rodzaj: str, tekst: str) -> list[Element]:
        miejsce = MIEJSCE_ELEMENTU[rodzaj]
        if rodzaj == "komorka":
            tabela, self.tabele = self.tabele, self.tabele + 1
            return [Element("komorka", self._fragmenty(komorka, miejsce),
                            {"tabela": tabela, "wiersz": i, "kolumna": j})
                    for i, wiersz in enumerate(tekst.split("\n")) for j, komorka in enumerate(wiersz.split(" | "))]
        if rodzaj == "komentarz":
            autor, sep, tresc = tekst.partition(" | ")
            if not sep:
                raise ValueError(f"komentarz wymaga postaci '<autor> | <tekst>': {tekst!r}")
            return [Element(rodzaj, [self._autor(autor, miejsce), ": ", *self._fragmenty(tresc, miejsce)],
                            {"autor_fragment": 0})]
        if rodzaj == "zmiany":
            części = tekst.split(" | ", 2)
            if len(części) != 3 or części[0] not in ("ins", "del"):
                raise ValueError(f"zmiany wymagają postaci 'ins|del | <autor> | <tekst>': {tekst!r}")
            return [Element(rodzaj, [self._autor(części[1], miejsce), ": ", *self._fragmenty(części[2], miejsce)],
                            {"autor_fragment": 0, "typ": części[0]})]
        if rodzaj == "pole":
            etykieta, sep, wartosc = tekst.partition(" | ")
            if not sep:
                etykieta, wartosc = "", tekst
            return [Element(rodzaj, self._fragmenty(wartosc, miejsce), {"etykieta": etykieta})]
        return [Element(rodzaj, self._fragmenty(tekst, miejsce))]

    def _metadane(self) -> dict[str, str | Wartosc]:
        wynik: dict[str, str | Wartosc] = {}
        for klucz, wartosc in self.szablon.metadane.items():
            if "{" not in wartosc:
                wynik[klucz] = wartosc
                continue
            if _SLOT.fullmatch(wartosc) is None:
                raise ValueError(f"metadana {klucz!r}: wartość musi być jednym gniazdem albo zwykłym tekstem")
            frag = self._fragmenty(wartosc, "metadane")
            wynik[klucz] = frag[0] if frag else ""
        return wynik

    def dokument(self) -> Dokument:
        d = Dokument(f"{self.szablon.typ}-{self.rng.getrandbits(32):08x}", self.szablon.jezyk, self.szablon.typ, "txt")
        for sekcja in self.szablon.sekcje:
            dostepne = [b for b in sekcja.bloki if self._pasuje(b.wariant)]
            n = min(self.rng.randint(sekcja.min, sekcja.max), len(dostepne))
            for i in sorted(self.rng.sample(range(len(dostepne)), n)):
                d.elementy.extend(self._elementy(sekcja.rodzaj_elementu, dostepne[i].tekst_z_gniazdami))
        d.metadane = self._metadane()
        return d


@dataclass
class Wynik:
    """Dokument razem z encjami osób (`osoby[rola]`) i kontekstem – do testów i diagnostyki."""

    dokument: Dokument
    osoby: dict[str, Osoba]
    kontekst: Kontekst
    #: encje ról (do wspólnego kontekstu załącznika: `zbuduj_z_kontekstem(..., wspolne=wynik)`)
    encje: dict[str, _Encja] = field(default_factory=dict)


def zbuduj_z_kontekstem(szablon: Szablon, gen: BazowyGenerator, rng: random.Random,
                        wariant: str | None = None, wspolne: Wynik | None = None) -> Wynik:
    """Jak `zbuduj`, ale zwraca też osoby ról i `Kontekst`; `wariant` wymusza wariant szablonu.

    `wspolne` (wynik wcześniejszej budowy tym samym `gen`): dokument powiązany (załącznik e-maila) dzieli kontekst
    (daty, kwoty, kraj, wariant) i encje ról o tej samej nazwie i rodzaju – te same osoby, firmy, sąd i sprawa."""
    b = _Budowa(szablon, gen, rng, wariant, wspolne)
    d = b.dokument()
    return Wynik(d, {r: e.osoba for r, e in b.encje.items() if e.osoba is not None}, b.ctx, b.encje)


def zbuduj(szablon: Szablon, gen: BazowyGenerator, rng: random.Random, wariant: str | None = None) -> Dokument:
    """Dokument z szablonu: encje ról z `gen`, wybór bloków z `rng`; wynik deterministyczny dla (ziarno gen, rng)."""
    return _Budowa(szablon, gen, rng, wariant).dokument()
