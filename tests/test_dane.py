"""Testy generatorów wartości syntetycznych (PL/EN/ES/DE/FR). Walidacja przez python-stdnum i libphonenumber –
niezależnie od kodu generatora (sumy kontrolne w generatorze liczone własnym kodem)."""
from __future__ import annotations

import datetime as dt
import ipaddress
import re
from pathlib import Path

import phonenumbers
import pytest
from stdnum import iban as stdnum_iban
from stdnum.de import idnr as de_idnr, vat as de_vat
from stdnum.es import cif as es_cif, dni as es_dni, nie as es_nie
from stdnum.eu import vat as eu_vat
from stdnum.fr import nir as fr_nir, siren as fr_siren, siret as fr_siret
from stdnum.gb import nhs as gb_nhs, vat as gb_vat
from stdnum.pl import nip as pl_nip, pesel as pl_pesel, regon as pl_regon
from stdnum.us import ein as us_ein, rtn as us_rtn, ssn as us_ssn

from pbench.dane import Generator
from pbench.dane.wspolne import Adres, Firma, Osoba

JEZYKI = ["pl", "en", "es", "de", "fr"]
SLOWNIKI = Path(__file__).resolve().parents[1] / "pbench" / "dane" / "slowniki"
N = 500


def _osoby(jezyk: str, kraj: str | None = None, n: int = N, ziarno: int = 1) -> list[Osoba]:
    g = Generator(jezyk, ziarno)
    return [g.osoba(kraj) for _ in range(n)]


def _firmy(jezyk: str, kraj: str | None = None, n: int = N, ziarno: int = 1) -> list[Firma]:
    g = Generator(jezyk, ziarno)
    return [g.firma(kraj) for _ in range(n)]


# --- identyfikatory osób i firm: stdnum ------------------------------------------------------------
OSOBY_STDNUM = [
    ("pl", None, "PESEL", pl_pesel.is_valid),
    ("pl", None, "NIP", pl_nip.is_valid),
    ("en", "GB", "NHS", gb_nhs.is_valid),
    ("en", "US", "SSN", us_ssn.is_valid),
    ("es", None, "DNI", es_dni.is_valid),
    ("de", None, "STEUER_ID", de_idnr.is_valid),
    ("fr", None, "NIR", fr_nir.is_valid),
]


@pytest.mark.parametrize("jezyk,kraj,typ,sprawdz", OSOBY_STDNUM)
def test_identyfikatory_osob_waliduja_stdnum(jezyk, kraj, typ, sprawdz):
    wartosci = [o.ids[typ] for o in _osoby(jezyk, kraj) if typ in o.ids]  # ES: DNI albo NIE (cudzoziemcy)
    assert len(wartosci) > 400
    for w in wartosci:
        assert sprawdz(w) is True, (typ, w)


def test_nie_waliduje_stdnum():
    nie = [o.ids["NIE"] for o in _osoby("es", n=N) if "NIE" in o.ids]
    assert len(nie) > 20  # część osób to cudzoziemcy z NIE zamiast DNI
    assert all(es_nie.is_valid(x) for x in nie)


FIRMY_STDNUM = [
    ("pl", None, "NIP", pl_nip.is_valid),
    ("pl", None, "REGON", pl_regon.is_valid),
    ("pl", None, "VAT", lambda v: eu_vat.is_valid(v)),
    ("es", None, "CIF", es_cif.is_valid),
    ("es", None, "VAT", lambda v: eu_vat.is_valid(v)),
    ("de", None, "VAT", de_vat.is_valid),
    ("fr", None, "SIREN", fr_siren.is_valid),
    ("fr", None, "SIRET", fr_siret.is_valid),
    ("fr", None, "VAT", lambda v: eu_vat.is_valid(v)),
    ("en", "GB", "VAT", gb_vat.is_valid),  # po Brexicie eu.vat nie obsługuje GB
    ("en", "US", "EIN", us_ein.is_valid),
]


@pytest.mark.parametrize("jezyk,kraj,typ,sprawdz", FIRMY_STDNUM)
def test_identyfikatory_firm_waliduja_stdnum(jezyk, kraj, typ, sprawdz):
    for f in _firmy(jezyk, kraj):
        assert sprawdz(f.rejestry[typ]) is True, (typ, f.rejestry[typ])


@pytest.mark.parametrize("jezyk,kraj", [("pl", None), ("en", "GB"), ("es", None), ("de", None), ("fr", None)])
def test_iban_waliduje_stdnum(jezyk, kraj):
    g = Generator(jezyk, 1)
    for _ in range(N):
        assert stdnum_iban.is_valid(g.iban(kraj)) is True
    for o in _osoby(jezyk, kraj, 50):
        assert stdnum_iban.is_valid(o.rachunek)
    for f in _firmy(jezyk, kraj, 50):
        assert stdnum_iban.is_valid(f.rachunek)


def test_iban_prefiks_kraju_i_realistyczny_kod_banku():
    for jezyk, kraj, prefiks in [("pl", None, "PL"), ("en", "GB", "GB"), ("es", None, "ES"), ("de", None, "DE"),
                                 ("fr", None, "FR")]:
        g = Generator(jezyk, 3)
        for _ in range(100):
            iban = g.iban(kraj)
            assert iban.startswith(prefiks)
            assert not re.search(r"(999999|000000)", iban[4:12])  # żadnych „bezpiecznych” kodów banków


def test_iban_pl_kod_rozliczeniowy_ma_poprawna_sume():
    g = Generator("pl", 5)
    for _ in range(N):
        d = g.iban()[4:12]
        w = (3, 9, 7, 1, 3, 9, 7)
        assert (10 - sum(int(c) * k for c, k in zip(d[:7], w)) % 10) % 10 == int(d[7])


def test_rachunek_us_to_routing_aba_i_konto():
    g = Generator("en", 2)
    for _ in range(N):
        r = g.rachunek("US")
        m = re.fullmatch(r"Routing No\. (\d{9}), Account No\. (\d{8,12})", r)
        assert m, r
        assert us_rtn.is_valid(m.group(1))
    for o in _osoby("en", "US", 50):
        assert o.rachunek.startswith("Routing No. ")


def test_en_mieszanka_uk_us():
    kraje = [o.kraj for o in _osoby("en", n=400)]
    assert 0.35 < kraje.count("GB") / 400 < 0.65
    assert set(kraje) == {"GB", "US"}


# --- identyfikatory bez walidatora w stdnum: weryfikacja niezależnym kodem w teście ----------------------
def test_krs_format():
    for f in _firmy("pl"):
        krs = f.rejestry.get("KRS")
        if krs:
            assert re.fullmatch(r"000\d{7}", krs)


def test_dowod_pl_suma_kontrolna():
    waga = (7, 3, 1, 0, 7, 3, 1, 7, 3)
    for o in _osoby("pl"):
        d = o.ids["DOWOD"]
        assert re.fullmatch(r"[A-Z]{3}\d{6}", d)
        w = [int(c) if c.isdigit() else ord(c) - 55 for c in d]
        assert sum(a * b for a, b in zip(w, waga)) % 10 == w[3]


def test_paszport_pl_format():
    assert all(re.fullmatch(r"[A-Z]{2}\d{7}", o.ids["PASZPORT"]) for o in _osoby("pl"))


def test_pwz_lekarza_format_i_suma_kontrolna():
    """PWZ: 7 cyfr, cyfra 1 = suma (cyfra i × i, i=1..6) mod 11 (nigdy 10); zgodne z mapą kategorii (NR_ID)."""
    from pbench.budowa import MAPA_KATEGORII
    osoby = _osoby("pl")
    for o in osoby:
        p = o.ids["PWZ"]
        assert re.fullmatch(r"\d{7}", p)
        assert int(p[0]) == sum(int(c) * i for i, c in enumerate(p[1:], start=1)) % 11
    assert len({o.ids["PWZ"] for o in osoby}) == len(osoby)
    assert MAPA_KATEGORII["PWZ"] == "NR_ID"


def test_kw_suma_kontrolna():
    g = Generator("pl", 4)
    waga = (1, 3, 7) * 4
    tab = {str(i): i for i in range(10)} | {c: n for n, c in enumerate("XABCDEFGHIJKLMNOPRSTUWYZ", start=10)}
    for _ in range(N):
        kw = g.ksiega_wieczysta()
        m = re.fullmatch(r"([A-Z]{2}\d[A-Z])/(\d{8})/(\d)", kw)
        assert m, kw
        znaki = m.group(1) + m.group(2)
        assert (sum(tab[c] * w for c, w in zip(znaki, waga)) % 10) == int(m.group(3))


def test_pesel_realistyczny_zakres_dat():
    lata = set()
    for o in _osoby("pl"):
        p = o.ids["PESEL"]
        rr, mm = int(p[0:2]), int(p[2:4])
        rok = (2000 if mm > 20 else 1900) + rr
        lata.add(rok)
        assert 1940 <= rok <= 2005
        assert o.data_ur.year == rok
        assert (int(p[9]) % 2 == 1) == (o.plec == "M")
    assert min(lata) < 1950 and max(lata) > 2000  # pełny zakres, nie wąski „bezpieczny” pas


def test_nip_urzad_skarbowy_nie_jest_zerowy():
    for f in _firmy("pl"):
        assert f.rejestry["NIP"][:3] != "000"


def test_nino_format_i_wylaczone_prefiksy():
    zle = {"BG", "GB", "KN", "NK", "NT", "TN", "ZZ"}
    for o in _osoby("en", "GB"):
        n = o.ids["NINO"]
        assert re.fullmatch(r"[A-CEGHJ-PR-TW-Z][A-CEGHJ-NPR-TW-Z]\d{6}[A-D]", n), n
        assert n[:2] not in zle


def test_dni_nie_cif_ukladaja_sie_w_formaty():
    for o in _osoby("es"):
        assert re.fullmatch(r"\d{8}[A-Z]|[XYZ]\d{7}[A-Z]", o.ids.get("DNI") or o.ids["NIE"])
        assert re.fullmatch(r"\d{2}/\d{8}/\d{2}", o.ids["NUSS"])


def test_nuss_suma_kontrolna():
    for o in _osoby("es"):
        prow, nr, kontrola = o.ids["NUSS"].split("/")
        n = int(prow + nr) if int(nr) >= 10_000_000 else int(prow) * 10_000_000 + int(nr)
        assert n % 97 == int(kontrola)


def test_svnr_suma_kontrolna_i_data():
    waga = (2, 1, 2, 5, 7, 1, 2, 1, 2, 1, 2, 1)
    for o in _osoby("de"):
        s = o.ids["SVNR"]
        m = re.fullmatch(r"(\d{2})(\d{2})(\d{2})(\d{2})([A-Z])(\d{2})(\d)", s)
        assert m, s
        assert o.data_ur.strftime("%d%m%y") == s[2:8]
        cyfry = s[:8] + f"{ord(s[8]) - 64:02d}" + s[9:11]
        suma = sum(sum(divmod(int(c) * w, 10)) for c, w in zip(cyfry, waga))
        assert suma % 10 == int(s[11])
        assert (int(s[9:11]) >= 50) == (o.plec == "K")


def test_personalausweis_alfanumeryczny():
    for o in _osoby("de"):
        assert re.fullmatch(r"[LMNPRTVWXYZ][CFGHJKLMNPRTVWXYZ0-9]{8}", o.ids["PERSONALAUSWEIS"])


def test_nir_zgodny_z_plcia_i_data():
    for o in _osoby("fr"):
        n = o.ids["NIR"]
        assert (n[0] == "1") == (o.plec == "M")
        assert int(n[1:3]) == o.data_ur.year % 100
        assert int(n[3:5]) == o.data_ur.month


def test_firmy_formaty_krajowe():
    for f in _firmy("de"):
        rejestr = {"PartG mbB": "PR", "KG": "HRA", "OHG": "HRA", "e. K.": "HRA", "GmbH & Co. KG": "HRA"}.get(f.forma, "HRB")
        assert re.fullmatch(rejestr + r" \d{4,6}", f.rejestry[rejestr])
    for f in _firmy("en", "GB"):
        assert re.fullmatch(r"(SC|NI)?\d{6,8}", f.rejestry["COMPANY_NO"])


# --- własności ogólne ------------------------------------------------------------------------------
@pytest.mark.parametrize("jezyk", JEZYKI)
def test_deterministyczne_ziarno(jezyk):
    assert _osoby(jezyk, n=100, ziarno=7) == _osoby(jezyk, n=100, ziarno=7)
    assert _osoby(jezyk, n=100, ziarno=7) != _osoby(jezyk, n=100, ziarno=8)
    assert _firmy(jezyk, n=30, ziarno=7) == _firmy(jezyk, n=30, ziarno=7)


@pytest.mark.parametrize("jezyk", JEZYKI)
def test_deterministyczne_wszystkie_metody(jezyk):
    def seria(g):
        return [g.sygnatura(), g.sad(), g.diagnoza(), g.lek(), g.kwota(), g.data(), g.tablica(), g.ip(), g.url(),
                g.login(), g.telefon(), g.adres().linia()]
    assert seria(Generator(jezyk, 3)) == seria(Generator(jezyk, 3))


@pytest.mark.parametrize("jezyk,klucze", [("pl", ["PESEL", "NIP"]), ("en", ["EMAIL"]), ("es", ["DNI", "NUSS"]),
                                          ("de", ["STEUER_ID", "SVNR"]), ("fr", ["NIR"])])
def test_brak_kolizji_w_dokumencie(jezyk, klucze):
    osoby = _osoby(jezyk, n=1000, ziarno=11)
    for k in klucze:
        wart = [o.email if k == "EMAIL" else o.ids.get(k) for o in osoby]
        wart = [w for w in wart if w]
        assert len(wart) == len(set(wart)), k
    if jezyk == "es":
        glowne = [o.ids.get("DNI") or o.ids["NIE"] for o in osoby]
        assert len(glowne) == len(set(glowne))
    assert len({o.email for o in osoby}) == 1000
    assert len({(o.imie, o.nazwisko, o.data_ur) for o in osoby}) == 1000


DOMENA = re.compile(r"@(?:[\w-]+\.)*(?:example\.(?:com|org|net)|test)$")


@pytest.mark.parametrize("jezyk", JEZYKI)
def test_email_domeny_zarezerwowane(jezyk):
    g = Generator(jezyk, 1)
    for o in [g.osoba() for _ in range(300)]:
        assert DOMENA.search(o.email), o.email
        assert o.email.isascii()
    for f in [g.firma() for _ in range(100)]:
        assert DOMENA.search(f.email), f.email


REGION = {"pl": "PL", "en": None, "es": "ES", "de": "DE", "fr": "FR"}


@pytest.mark.parametrize("jezyk,kraj,region", [("pl", None, "PL"), ("en", "GB", "GB"), ("en", "US", "US"),
                                               ("es", None, "ES"), ("de", None, "DE"), ("fr", None, "FR")])
def test_telefon_ma_kod_kraju_i_jest_fikcyjny(jezyk, kraj, region):
    """Telefony z pul fikcyjnych (GB, US, DE, FR) albo w formacie 000… (PL, ES) – `tests/test_generatory_zrodla.py`;
    libphonenumber nie musi ich uznawać za ważne, ale numer ma kod kraju i da się sparsować."""
    for o in _osoby(jezyk, kraj, 300):
        num = phonenumbers.parse(o.telefon, region)
        assert num.country_code == phonenumbers.country_code_for_region(region), o.telefon


@pytest.mark.parametrize("jezyk", JEZYKI)
def test_formaty_pomocnicze(jezyk):
    g = Generator(jezyk, 5)
    for _ in range(100):
        ipaddress.ip_address(g.ip())
        assert re.match(r"https://[\w.-]+\.(?:example\.(?:com|org|net)|test)(/|$)", g.url())
        assert re.fullmatch(r"[a-z][a-z0-9._-]{2,30}", g.login())
        assert re.search(r"\d", g.kwota())
        assert re.search(r"\d{4}", g.data())
        assert re.fullmatch(r"[A-Z]\d{2}(?:\.\d)? .+", g.diagnoza())
        assert g.lek() and g.sygnatura() and g.sad() and g.tablica()


TABLICA = {
    "pl": r"[A-Z]{2} (?:\d{5}|\d{4}[A-Z]|\d[A-Z]\d{3})|[A-Z]{3} (?:[A-Z]\d{3}|\d{2}[A-Z]{2}|\d[A-Z]\d{2})",
    "en": r"[A-Z]{2}\d{2} [A-Z]{3}|[1-9][A-Z]{3}\d{3}",
    "es": r"\d{4} [B-DF-HJ-NP-TV-Z]{3}",
    "de": r"[A-ZÄÖÜ]{1,3} [A-Z]{1,2} \d{1,4}",
    "fr": r"[A-HJ-NP-TV-Z]{2}-\d{3}-[A-HJ-NP-TV-Z]{2}",
}


@pytest.mark.parametrize("jezyk", JEZYKI)
def test_tablica_format(jezyk):
    g = Generator(jezyk, 2)
    for _ in range(200):
        assert re.fullmatch(TABLICA[jezyk], g.tablica()), g.tablica()


SYGNATURA = {
    "pl": r"[IVX]+ [A-Za-z]+ \d{1,4}/\d{2}",
    "de": r"\d{1,2} [A-Za-z]{1,3} \d{1,4}/\d{2}|[IVX]+ ZR \d{1,3}/\d{2}",
    "fr": r"(?:RG n° |N° RG )\d{2}/\d{5}",
    "es": r"[^\d/]+ n\.º \d{1,4}/\d{4}",
}


@pytest.mark.parametrize("jezyk", ["pl", "de", "fr", "es"])
def test_sygnatura_format(jezyk):
    g = Generator(jezyk, 2)
    for _ in range(200):
        assert re.fullmatch(SYGNATURA[jezyk], g.sygnatura()), g.sygnatura()


def test_sygnatura_i_sad_en_wg_kraju():
    g = Generator("en", 2)
    assert re.fullmatch(r"Claim No\. [A-Z]{2}-20\d{2}-\d{6}", g.sygnatura("GB"))
    assert re.fullmatch(r"Case No\. \d:\d{2}-cv-\d{5}-[A-Z]{3}", g.sygnatura("US"))
    assert all(re.search(r"Court|Tribunal|Centre", x) for x in (g.sad("GB") for _ in range(50)))
    assert all("Court" in x for x in (g.sad("US") for _ in range(50)))


def test_sad_pl_realistyczny():
    g = Generator("pl", 2)
    assert all("Sąd" in g.sad() for _ in range(50))


def test_kwota_symbol_waluty():
    assert re.fullmatch(r"\d{1,3}(?: \d{3})*,\d{2} (?:zł|PLN)", Generator("pl", 1).kwota())
    assert all(re.fullmatch(r"£\d{1,3}(?:,\d{3})*\.\d{2}", Generator("en", i).kwota("GB")) for i in range(30))
    assert all(re.fullmatch(r"\$\d{1,3}(?:,\d{3})*\.\d{2}", Generator("en", i).kwota("US")) for i in range(30))
    assert all(re.search(r"€|EUR", Generator(j, i).kwota()) for j in ("es", "de", "fr") for i in range(30))


def test_osoba_adres_kompletny():
    for jezyk in JEZYKI:
        for o in _osoby(jezyk, n=50):
            assert isinstance(o.adres, Adres)
            linia = o.adres.linia()
            assert o.adres.miejscowosc in linia and o.adres.kod in linia
            assert isinstance(o.data_ur, dt.date)
            assert o.plec in ("M", "K") and o.imie and o.nazwisko
            assert o.login and re.fullmatch(r"[a-z][a-z0-9._-]+", o.login)


def test_nazwiska_zenskie_pl():
    zenskie = [o.nazwisko for o in _osoby("pl", n=500) if o.plec == "K"]
    assert any(n.endswith("ska") or n.endswith("cka") for n in zenskie)
    assert not any(n.endswith("ski") or n.endswith("cki") for n in zenskie)


def test_es_dwa_nazwiska():
    assert all(len(o.nazwisko.split()) >= 2 for o in _osoby("es", n=100))


# --- słowniki i źródła -----------------------------------------------------------------------------
MINIMA = {"nazwiska": 300, "imiona_m": 100, "imiona_k": 100, "ulice": 200, "miejscowosci": 150,
          "firmy_rdzenie": 40, "choroby": 40, "leki": 20}


@pytest.mark.parametrize("jezyk", JEZYKI)
def test_slowniki_minimalne_rozmiary(jezyk):
    for plik, minimum in MINIMA.items():
        linie = [x for x in (SLOWNIKI / jezyk / f"{plik}.txt").read_text(encoding="utf-8").splitlines() if x.strip()]
        assert len(linie) >= minimum, (jezyk, plik, len(linie))
        assert len(linie) == len(set(linie)), (jezyk, plik, "duplikaty")


@pytest.mark.parametrize("jezyk", JEZYKI)
def test_ZRODLA_opisuje_kazdy_slownik(jezyk):
    tekst = (SLOWNIKI / "ZRODLA.md").read_text(encoding="utf-8")
    for plik in MINIMA:
        assert f"{jezyk}/" in tekst and f"{plik}.txt" in tekst, (jezyk, plik)
    assert "licencj" in tekst.lower()


def test_nie_importuje_lgprivatizer():
    """Niezależność pomiaru: generator nie może importować kodu Privatizera."""
    for p in (Path(__file__).resolve().parents[1] / "pbench" / "dane").glob("*.py"):
        assert not re.search(r"^\s*(?:from|import)\s+lgprivatizer", p.read_text(encoding="utf-8"), re.M), p


def test_kod_icd_plec_i_diagnozy_zgodne_z_plcia():
    """Rozpoznania swoiste dla płci (gruczoł krokowy, ciąża, pierś…) nie trafiają do pacjenta drugiej płci."""
    from pbench.dane.wspolne import kod_icd_plec
    assert [kod_icd_plec(k) for k in ("N40 Rozrost", "C61 Nowotwór", "O24.4 Cukrzyca ciążowa", "C50.9 Pierś",
                                      "I10 Nadciśnienie")] == ["M", "M", "K", "K", None]
    for jezyk in JEZYKI:
        g = Generator(jezyk, 3)
        for plec in "MK":
            for profil in (None, "kardiologia", "interna"):
                for _ in range(300):
                    assert kod_icd_plec(g.diagnoza(profil, plec)) in (None, plec), (jezyk, plec, profil)
        assert len(set(g.diagnozy(3, None, "M"))) == 3


def test_pule_nazw_wg_rodzaju_firmy():
    """Kancelarie i placówki medyczne mają własne wzory nazw (nie „Rdzeń sp. z o.o.” jak zwykłe firmy)."""
    g = Generator("pl", 11)
    kanc = [g.firma(rodzaj="kancelaria").nazwa for _ in range(60)]
    plac = [g.firma(rodzaj="placowka").nazwa for _ in range(60)]
    zwykle = [g.firma().nazwa for _ in range(60)]
    assert all("Kancelaria" in n for n in kanc)
    assert all(re.search(r"Szpital|Centrum Medyczne|Zakład Opieki Zdrowotnej", n) for n in plac)
    assert not any(re.search(r"Kancelaria|Szpital|Centrum Medyczne|Opieki Zdrowotnej", n) for n in zwykle)
    assert not set(kanc) & set(plac) and not set(zwykle) & (set(kanc) | set(plac))
    for rodzaj in ("kancelaria", "placowka", "firma"):
        f = g.firma(rodzaj=rodzaj)
        assert f.nazwa.endswith(f.forma), (f.nazwa, f.forma)


def test_sygnatura_z_rokiem_i_repertorium_oraz_poziom_sadu_pl():
    g = Generator("pl", 4)
    assert re.fullmatch(r"[IVX]+ Ca \d{1,4}/25", g.sygnatura(rodzaj="Ca", rok=2025))
    assert all(g.sad(poziom="rejonowy").startswith("Sąd Rejonowy") for _ in range(50))
    assert all(g.sad(poziom="okregowy").startswith("Sąd Okręgowy") for _ in range(50))


def test_data_i_kwota_pl_styl_stalego_dokumentu():
    g = Generator("pl", 4)
    d = dt.date(2024, 3, 12)
    g.styl = {"data": 0, "waluta": 1}
    assert g.formatuj_date(d) == "12 marca 2024 r." and g._kwota_txt(1234, 5, "PL") == "1 234,05 PLN"
    g.styl = {"data": 1, "waluta": 0}
    assert g.formatuj_date(d) == "12.03.2024 r." and g._kwota_txt(1234, 5, "PL") == "1 234,05 zł"
    g.styl = {}
    assert all(re.fullmatch(r"(12 marca 2024|12\.03\.2024) r\.", g.formatuj_date(d)) for _ in range(30))


def test_gmc_i_npi_lekarza_format_i_suma_kontrolna():
    """GMC: 7 cyfr (pierwsza 1–7); NPI: 10 cyfr, pierwsza 1/2, Luhn z prefiksem 80840 (stdnum.luhn); kategoria NR_ID."""
    from stdnum import luhn
    from pbench.budowa import MAPA_KATEGORII
    gb, us = _osoby("en", "GB", 300), _osoby("en", "US", 300)
    assert all(re.fullmatch(r"[1-7]\d{6}", o.ids["GMC"]) for o in gb) and "NPI" not in gb[0].ids
    assert all(re.fullmatch(r"[12]\d{9}", o.ids["NPI"]) and luhn.is_valid("80840" + o.ids["NPI"]) for o in us)
    assert MAPA_KATEGORII["GMC"] == MAPA_KATEGORII["NPI"] == "NR_ID"


def test_pule_nazw_wg_rodzaju_firmy_en():
    """EN: kancelarie (LLP / P.C.) i placówki medyczne (trust / medical center) mają własne wzory nazw."""
    g = Generator("en", 12)
    for kraj in ("GB", "US"):
        kanc = [g.firma(kraj, "kancelaria") for _ in range(60)]
        plac = [g.firma(kraj, "placowka") for _ in range(60)]
        zwykle = [g.firma(kraj).nazwa for _ in range(60)]
        assert all(re.search(r"LLP|P\.C\.", f.nazwa) for f in kanc)
        assert all(re.search(r"NHS|Hospital|Medical Center|Health System|Infirmary", f.nazwa) for f in plac)
        assert not any(re.search(r"LLP.*Legal|NHS|Hospital|Medical Center", n) for n in zwykle)
        assert all(f.nazwa.endswith(f.forma) for f in kanc + plac)
