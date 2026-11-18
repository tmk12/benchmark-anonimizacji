"""Generator wartości syntetycznych dla języka angielskiego: Wielka Brytania (NINO, NHS, IBAN GB) i USA (SSN, EIN,
routing ABA + numer konta – USA nie mają IBAN-u). Domyślnie osoby/firmy: ok. 50% GB, 50% US."""
from __future__ import annotations

from .wspolne import Adres, BazowyGenerator, cyfry, cyfry_kontrolne_iban, suma_luhna_kontrola, wagowo

_EIN_PREFIKSY = tuple(sorted(set(
    "01 02 03 04 05 06 11 13 14 16 21 22 23 25 34 51 52 54 55 56 57 58 59 65 10 12 15 24 20 26 27 45 46 47 81 82 83 "
    "84 30 32 35 36 37 38 61 31 33 39 41 42 43 48 62 63 64 66 68 71 72 73 74 75 76 77 85 86 87 88 91 92 93 98 99 40 "
    "44 50 53 60 67 80 90 94 95".split())))
# kody banku w IBAN GB i pierwsze dwie cyfry sort code (SRLG = Starling Bank, sort code 60-83-71)
_BANKI_GB = (("NWBK", "60"), ("BARC", "20"), ("LOYD", "30"), ("HBUK", "40"), ("MIDL", "40"), ("ABBY", "09"),
             ("RBOS", "83"), ("CPBK", "08"), ("SRLG", "60"), ("TSBS", "77"), ("MONZ", "04"))
_KOD_FED = tuple(f"{i:02d}" for i in list(range(1, 13)) + list(range(21, 33)))  # okręgi Rezerwy Federalnej
_KODY_OBSZARU_US = ("201", "202", "206", "207", "212", "213", "214", "215", "216", "301", "305", "310", "312", "313",
                    "314", "315", "404", "407", "408", "410", "412", "415", "416", "503", "504", "505", "512", "602",
                    "603", "614", "615", "617", "619", "702", "703", "704", "713", "714", "718", "720", "801", "802",
                    "804", "805", "815", "818", "901", "904", "908", "913", "914", "916", "919", "925", "949")
# Pule Ofcom do fikcji tylko dla Anglii (bez 028 Irlandia Płn., 029 Walia, 0131/0141 Szkocja): dokumenty GB to Anglia i Walia.
_DRAMA_GB = (("20", "7946"), ("161", "496"), ("113", "496"), ("114", "496"), ("115", "496"), ("116", "496"),
             ("117", "496"), ("118", "496"), ("121", "496"), ("151", "496"), ("191", "498"))
#: Maksymalny numer dystryktu kodu pocztowego GB (obszar → maks.): potwierdzone dla HG, SP, FY, TF (weryfikacja generatorów w źródłach;
#: bez publicznego źródła pobranego w pełnej tabeli PAF/ONS) – dla pozostałych obszarów węższy, ostrożny zakres 1–5
#: (pełna lista dystryktów: ONS Postcode Directory – niezweryfikowana, `metodyka/znane-ograniczenia.md`).
_MAKS_DYSTRYKT_GB = {"HG": 5, "SP": 11, "FY": 8, "TF": 13}
_MAKS_DYSTRYKT_GB_DOMYSLNY = 5
#: Obszary kodów pocztowych poza Anglią (Szkocja, Walia, Irlandia Płn.) – pomijane w adresach GB.
_OBSZARY_POZA_ANGLIA = frozenset({"G", "EH", "AB", "DD", "IV", "FK", "PA", "DG", "PH", "KA", "CF", "SA", "NP", "LL",
                                  "BT"})
_KODY_STANOW = {
    "AK": ("907",), "AL": ("205", "251", "256", "334"), "AR": ("479", "501", "870"),
    "AZ": ("480", "520", "602", "623", "928"),
    "CA": ("213", "310", "408", "415", "510", "619", "714", "805", "818", "916", "925", "949"),
    "CO": ("303", "719", "720", "970"), "CT": ("203", "860"), "DC": ("202",), "DE": ("302",),
    "FL": ("305", "321", "407", "561", "727", "786", "813", "904"), "GA": ("404", "470", "678", "706", "770", "912"),
    "HI": ("808",), "IA": ("319", "515", "563", "641"), "ID": ("208",), "IL": ("217", "312", "618", "630", "708", "773", "847"),
    "IN": ("219", "260", "317", "574", "765", "812"), "KS": ("316", "620", "785", "913"),
    "KY": ("270", "502", "606", "859"), "LA": ("225", "318", "337", "504"), "MA": ("413", "508", "617", "781", "978"),
    "MD": ("240", "301", "410", "443"), "ME": ("207",), "MI": ("231", "248", "269", "313", "517", "616", "734", "810", "906", "989"),
    "MN": ("218", "320", "507", "612", "651", "763", "952"), "MO": ("314", "417", "573", "636", "660", "816"),
    "MS": ("228", "601", "662"), "MT": ("406",), "NC": ("252", "336", "704", "828", "910", "919", "980"),
    "ND": ("701",), "NE": ("308", "402"), "NH": ("603",), "NJ": ("201", "609", "732", "856", "908", "973"),
    "NM": ("505", "575"), "NV": ("702", "775"),
    "NY": ("212", "315", "516", "518", "585", "607", "631", "646", "716", "718", "845", "914", "917"),
    "OH": ("216", "330", "419", "440", "513", "614", "740", "937"), "OK": ("405", "539", "580", "918"),
    "OR": ("503", "541", "971"), "PA": ("215", "267", "412", "570", "610", "717", "724", "814", "878"),
    "RI": ("401",), "SC": ("803", "843", "864"), "TN": ("423", "615", "731", "865", "901", "931"),
    "TX": ("210", "214", "254", "281", "325", "361", "409", "432", "512", "713", "806", "817", "832", "903", "915",
           "940", "956", "972", "979"),
    "UT": ("385", "435", "801"), "VA": ("276", "434", "571", "703", "757", "804"), "VT": ("802",),
    "WA": ("206", "253", "360", "425", "509"), "WI": ("262", "414", "608", "715", "920"), "WY": ("307",),
}
_NAZWY_STANOW = {
    "AK": "Alaska", "AL": "Alabama", "AR": "Arkansas", "AZ": "Arizona", "CA": "California", "CO": "Colorado",
    "CT": "Connecticut", "DC": "the District of Columbia", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "IA": "Iowa", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "KS": "Kansas", "KY": "Kentucky",
    "LA": "Louisiana", "MA": "Massachusetts", "MD": "Maryland", "ME": "Maine", "MI": "Michigan", "MN": "Minnesota",
    "MO": "Missouri", "MS": "Mississippi", "MT": "Montana", "NC": "North Carolina", "ND": "North Dakota",
    "NE": "Nebraska", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NV": "Nevada", "NY": "New York",
    "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VA": "Virginia", "VT": "Vermont", "WA": "Washington",
    "WI": "Wisconsin", "WY": "Wyoming",
}
#: Sądy federalne okręgowe i sądy stanowe z nazwą stanu; stany spoza tabel dostają nazwę ogólną (patrz `_sady_stanu`).
_OKREGI_STANOW = {
    "NY": ("Southern District of New York",), "CA": ("Northern District of California", "Central District of California"),
    "IL": ("Northern District of Illinois",), "MA": ("District of Massachusetts",), "TX": ("Eastern District of Texas",),
    "DE": ("District of Delaware",), "FL": ("Southern District of Florida",), "WA": ("Western District of Washington",),
    "DC": ("District of Columbia",), "NJ": ("District of New Jersey",), "GA": ("Northern District of Georgia",), "PA": ("Eastern District of Pennsylvania",),
}
_JEDEN_OKREG = frozenset("AK AZ CO CT DC DE HI ID KS MA MD ME MN MT ND NE NH NJ NM NV RI SC UT VT WY".split())
_OKREG_PN = frozenset("AL CA FL GA IA IL IN MS NY OH OK TX WV".split())
_SADY_STANOWE_STANOW = {
    "CA": ("Superior Court of California, County of Los Angeles", "Superior Court of California, County of San Francisco"),
    "DE": ("Superior Court of the State of Delaware", "Court of Chancery of the State of Delaware"),
    "IL": ("Circuit Court of Cook County, Illinois",), "NY": ("Supreme Court of the State of New York, County of New York",),
    "PA": ("Court of Common Pleas of Philadelphia County, Pennsylvania",),
    "OH": ("Court of Common Pleas of Cuyahoga County, Ohio",),
    "FL": ("Circuit Court of the Eleventh Judicial Circuit, Miami-Dade County, Florida",),
    "GA": ("Superior Court of Fulton County, Georgia",), "MA": ("Massachusetts Superior Court, Suffolk County",),
    "WA": ("Superior Court of Washington, King County",), "NJ": ("Superior Court of New Jersey, Law Division",),
    "DC": ("Superior Court of the District of Columbia",), "TX": ("District Court of Harris County, Texas",), "MD": ("Circuit Court for Baltimore City, Maryland",),
}
_OBWODY = {"First": "ME MA NH RI", "Second": "NY CT VT", "Third": "PA NJ DE", "Fourth": "MD VA WV NC SC",
           "Fifth": "TX LA MS", "Sixth": "OH MI KY TN", "Seventh": "IL IN WI", "Eighth": "MN IA MO AR NE ND",
           "Ninth": "CA WA OR AZ NV ID MT AK HI", "Tenth": "CO KS NM OK UT WY", "Eleventh": "AL GA FL"}
_OBWOD_STANU = {s: o for o, ss in _OBWODY.items() for s in ss.split()}
_SUFIKSY_GB = ("Road", "Street", "Lane", "Avenue", "Close", "Drive", "Way", "Gardens", "Terrace", "Crescent",
               "Grove", "Place")
_SUFIKSY_US = ("Street", "Avenue", "Boulevard", "Drive", "Lane", "Road", "Court", "Way", "Place", "St", "Ave", "Blvd")
_LITERY_KODU_GB = "ABDEFGHJLNPQRSTUWXYZ"
_SADY_GB = ("High Court of Justice, King's Bench Division", "High Court of Justice, Business and Property Courts",
            "High Court of Justice, Chancery Division", "County Court at Central London",
            "County Court at Manchester", "Manchester Civil Justice Centre", "Birmingham Civil and Family Justice Centre",
            "Leeds Combined Court Centre", "Employment Tribunal, London Central", "Employment Tribunal, Manchester",
            "Court of Appeal (Civil Division)", "Upper Tribunal (Tax and Chancery Chamber)",
            "First-tier Tribunal (Property Chamber)", "Technology and Construction Court, London")
_SADY_US = ("United States District Court for the Southern District of New York",
            "United States District Court for the Northern District of California",
            "United States District Court for the Northern District of Illinois",
            "United States District Court for the District of Massachusetts",
            "United States District Court for the Eastern District of Texas",
            "Superior Court of California, County of Los Angeles", "Superior Court of the State of Delaware",
            "Circuit Court of Cook County, Illinois", "Supreme Court of the State of New York, County of New York",
            "District Court of Harris County, Texas", "United States Court of Appeals for the Ninth Circuit",
            "United States Court of Appeals for the Second Circuit", "Court of Chancery of the State of Delaware")


_POZIOMY = {"GB": ("county", "high", "appeal"), "US": ("federal", "state", "appeal")}
_MIASTA_COUNTY = ("Central London", "Manchester", "Birmingham", "Leeds", "Bristol", "Newcastle upon Tyne",
                  "Nottingham", "Liverpool", "Sheffield", "Oxford", "Brighton", "Norwich", "Reading", "Leicester",
                  "Edinburgh Sheriff Court", "Cambridge", "Southampton", "Luton", "Exeter")
_OKREGI_US = ("Southern District of New York", "Northern District of California", "Northern District of Illinois",
              "District of Massachusetts", "Eastern District of Texas", "District of Delaware",
              "Southern District of Florida", "Central District of California", "Western District of Washington",
              "District of New Jersey", "Northern District of Georgia", "Eastern District of Pennsylvania")
_SADY_POZIOMY = {
    ("GB", "county"): tuple(f"County Court at {m}" for m in _MIASTA_COUNTY if "Sheriff" not in m),
    ("GB", "high"): ("High Court of Justice, King's Bench Division",
                     "High Court of Justice, Business and Property Courts of England and Wales",
                     "High Court of Justice, Chancery Division", "High Court of Justice, Commercial Court",
                     "High Court of Justice, Technology and Construction Court"),
    ("GB", "appeal"): ("Court of Appeal (Civil Division)",),
    ("US", "federal"): tuple(f"United States District Court for the {o}" for o in _OKREGI_US),
    ("US", "state"): ("Superior Court of California, County of Los Angeles", "Superior Court of the State of Delaware",
                      "Circuit Court of Cook County, Illinois", "Supreme Court of the State of New York, County of New York",
                      "District Court of Harris County, Texas", "Court of Chancery of the State of Delaware",
                      "Superior Court of California, County of San Francisco", "Circuit Court for Baltimore City, Maryland"),
    ("US", "appeal"): ("United States Court of Appeals for the Ninth Circuit",
                       "United States Court of Appeals for the Second Circuit",
                       "United States Court of Appeals for the Fifth Circuit",
                       "United States Court of Appeals for the Seventh Circuit",
                       "United States Court of Appeals for the Third Circuit"),
}


def nino(rng) -> str:
    while True:
        p = rng.choice("ABCEGHJKLMNOPRSTWXYZ") + rng.choice("ABCEGHJKLMNPRSTWXYZ")
        # HMRC NIM39110: prefiksy nieprzydzielane BG, GB, KN, NK, NT, TN, ZZ oraz administracyjne NC, PY, PZ
        if p not in ("BG", "GB", "KN", "NK", "NT", "TN", "ZZ", "NC", "PY", "PZ"):
            return f"{p}{cyfry(rng, 6)}{rng.choice('ABCD')}"


def nhs(rng) -> str:
    while True:
        baza = rng.choice("467") + cyfry(rng, 8)
        k = 11 - sum(int(c) * w for c, w in zip(baza, range(10, 1, -1))) % 11
        if k == 11:
            k = 0
        if k != 10:
            return baza + str(k)


def gmc(rng) -> str:
    """Numer rejestracji lekarza w GMC (Wielka Brytania): 7 cyfr, pierwsza 1–7."""
    return rng.choice("1234567") + cyfry(rng, 6)


def npi(rng) -> str:
    """NPI lekarza (USA): 10 cyfr, pierwsza 1 lub 2, ostatnia – cyfra Luhna z prefiksem 80840."""
    baza = rng.choice("12") + cyfry(rng, 8)
    return baza + suma_luhna_kontrola("80840" + baza)


def ssn(rng) -> str:
    while True:
        area = rng.randint(1, 772)
        if area != 666:
            return f"{area:03d}-{rng.randint(1, 99):02d}-{rng.randint(1, 9999):04d}"


def ein(rng) -> str:
    return f"{rng.choice(_EIN_PREFIKSY)}-{cyfry(rng, 7)}"


def aba(rng) -> str:
    baza = rng.choice(_KOD_FED) + cyfry(rng, 6)
    d = [int(c) for c in baza]
    s = 3 * (d[0] + d[3] + d[6]) + 7 * (d[1] + d[4] + d[7]) + (d[2] + d[5])
    return baza + str((10 - s % 10) % 10)


def numer_vat_gb(rng) -> str:
    baza = cyfry(rng, 7)
    s = sum(int(c) * w for c, w in zip(baza, (8, 7, 6, 5, 4, 3, 2)))
    return f"GB{baza}{(97 - s % 97) % 97:02d}"


class GeneratorEN(BazowyGenerator):
    kraje = ("GB", "US")
    wagi_krajow = (1, 1)

    def _ids_osoby(self, kraj, plec, data_ur, nazwisko):
        if kraj == "GB":
            return {"NINO": nino(self.rng), "NHS": nhs(self.rng), "GMC": gmc(self.rng)}
        return {"SSN": ssn(self.rng), "NPI": npi(self.rng)}

    def _formy(self, kraj):
        if kraj == "GB":
            return ("Ltd",) * 5 + ("Limited",) * 2 + ("PLC", "LLP")
        return ("Inc.",) * 4 + ("LLC",) * 4 + ("Corp.", "LP", "Co.")

    def _nazwa_firmy(self, rdzen, forma, rodzaj):
        """Kancelarie (LLP / P.C.) i placówki medyczne (NHS trust / medical center) mają własne wzory nazw."""
        r = self.rng
        gb = forma in ("Ltd", "Limited", "PLC", "LLP")
        if rodzaj == "kancelaria":
            n1 = wagowo(r, self._s("nazwiska"))
            if gb:
                return r.choice((f"{rdzen} & {n1} LLP", f"{n1} {rdzen} Solicitors LLP", f"{rdzen} Legal LLP")), "LLP"
            return r.choice(((f"{rdzen} & {n1} LLP", "LLP"), (f"{n1}, {rdzen} & Associates, P.C.", "P.C."),
                             (f"{rdzen} Law Group, LLP", "LLP")))
        if rodzaj == "placowka":
            if gb:
                forma = r.choice(("NHS Foundation Trust", "NHS Trust"))
                return f"{rdzen} {r.choice(('University Hospitals', 'Royal Infirmary', 'General Hospital'))} {forma}", forma
            forma = r.choice(("Medical Center", "Hospital", "Health System"))
            return f"{rdzen} {r.choice(('Regional', 'Memorial', 'Community', 'University'))} {forma}", forma
        return f"{rdzen} {forma}", forma

    def _email_firmy(self, slug):
        return self.rng.choice((f"office@{slug}.test", f"info@{slug}.example.com", f"enquiries@{slug}.example.org",
                                f"contact@{slug}.example.net", f"hello@{slug}.test"))

    def _ids_firmy(self, kraj, forma):
        r = self.rng
        if kraj == "GB":
            nr = f"{r.randint(1_000_000, 15_999_999):08d}"      # Companies House, Anglia i Walia (bez SC… i NI…)
            return {"COMPANY_NO": nr, "VAT": numer_vat_gb(r)}
        return {"EIN": ein(r)}

    def _kandydat_telefonu(self, kraj):
        r = self.rng
        if kraj == "GB":
            # Ofcom, „Numbers for drama”: pule stacjonarne i komórkowe 07700 900000–900999
            if r.random() < 0.8:
                return self._gb_drama(*r.choice(_DRAMA_GB))
            return f"+447700900{cyfry(r, 3)}"
        # NANPA: wyłącznie 555-0100–0199, z prawdziwym kodem obszaru stanu
        kier = r.choice(_KODY_STANOW.get(getattr(self, "_stan_adresu", None)) or _KODY_OBSZARU_US)
        return f"+1{kier}55501{r.randint(0, 99):02d}"

    def _gb_drama(self, kier: str, srodek: str) -> str:
        # Ofcom: 020 7946 0xxx, 0161 496 0xxx, 0191 498 0xxx, 028 9649 6xxx, 029 2018 0xxx – razem 10 cyfr po 0
        r = self.rng
        if kier == "28":
            return f"+44289649{6}{cyfry(r, 3)}"
        if kier == "29":
            return f"+44292018{0}{cyfry(r, 3)}"
        if kier == "20":
            return f"+4420{srodek}0{cyfry(r, 3)}"
        return f"+44{kier}{srodek}0{cyfry(r, 3)}"

    def iban(self, kraj=None):
        k = kraj or "GB"
        if k != "GB":
            raise ValueError("IBAN istnieje tylko dla GB; dla US użyj rachunek('US')")
        bank, prefiks = self.rng.choice(_BANKI_GB)
        bban = f"{bank}{prefiks}{cyfry(self.rng, 4)}{cyfry(self.rng, 8)}"
        return f"GB{cyfry_kontrolne_iban('GB', bban)}{bban}"

    def _bban(self, kraj):  # pragma: no cover – iban() nadpisane
        raise NotImplementedError

    def rachunek(self, kraj=None):
        k = self._kraj(kraj)
        if k == "GB":
            return self.iban("GB")
        konto = str(self.rng.randint(1, 9)) + cyfry(self.rng, self.rng.randint(7, 11))
        return f"Routing No. {aba(self.rng)}, Account No. {konto}"

    def _miasta(self, kraj):
        return tuple(m for m in self._s("miejscowosci") if m.split("|")[1] == kraj
                     and not (kraj == "GB" and m.split("|")[2] in _OBSZARY_POZA_ANGLIA))

    def losuj_stan_dok(self):
        stany = sorted({m.split("|")[2] for m in self._miasta("US")})
        self.stan_dok = self.rng.choice(stany) if self.kraj_dok == "US" else None
        self._stan_adresu = None

    def telefon(self, kraj=None):
        try:
            return super().telefon(kraj)
        finally:
            self._stan_adresu = None     # stan ostatniego adresu dotyczy tylko następującego po nim telefonu

    def adres(self, kraj=None):
        r = self.rng
        k = self._kraj(kraj)
        miasta = self._miasta(k)
        if k == "US" and self.stan_dok and r.random() < 0.85:    # adresy dokumentu zwykle w jednym stanie
            miasta = tuple(m for m in miasta if m.split("|")[2] == self.stan_dok) or miasta
        pola = wagowo(r, miasta).split("|")
        miasto = pola[0]
        if k == "US":
            self._stan_adresu = pola[2]
        baza = wagowo(r, self._s("ulice"))
        if k == "GB":
            ulica = baza if baza in ("Strand", "Fleet") else f"{baza} {r.choice(_SUFIKSY_GB)}"
            lit = _LITERY_KODU_GB
            kod = (f"{pola[2]}{r.randint(1, _MAKS_DYSTRYKT_GB.get(pola[2], _MAKS_DYSTRYKT_GB_DOMYSLNY))} {r.randint(1, 9)}"
                   f"{r.choice(lit)}{r.choice(lit)}")
            return Adres(ulica, str(r.randint(1, 250)), kod, miasto, "GB")
        ulica = f"{baza} {r.choice(_SUFIKSY_US)}"
        return Adres(ulica, str(r.randint(10, 9999)), pola[3] + cyfry(r, 2), miasto, "US", region=pola[2])

    def _kwota_txt(self, calk, grosze, kraj):
        return f"{'£' if kraj == 'GB' else '$'}{calk:,}.{grosze:02d}"

    def _data_txt(self, d, kraj):
        m = d.strftime("%B")
        if self.styl:   # styl stały w obrębie dokumentu: 0 – data pisana słownie, 1 – zapis liczbowy
            if kraj == "GB":
                return f"{d.day} {m} {d.year}" if self.styl["data"] == 0 else f"{d:%d/%m/%Y}"
            return f"{m} {d.day}, {d.year}" if self.styl["data"] == 0 else f"{d:%m/%d/%Y}"
        if kraj == "GB":
            return self.rng.choice((f"{d.day} {m} {d.year}", f"{d:%d/%m/%Y}", f"{d.day} {m} {d.year}",
                                    f"{d.day}{'th' if 10 <= d.day <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(d.day % 10, 'th')} {m} {d.year}"))
        return self.rng.choice((f"{m} {d.day}, {d.year}", f"{d:%m/%d/%Y}", f"{m} {d.day}, {d.year}", f"{d:%Y-%m-%d}"))

    def sygnatura(self, kraj=None, rodzaj=None, rok=None):
        """Sygnatura sprawy. `rodzaj`: GB `county|high|appeal`, US `federal|state|appeal`; None – dowolny numer
        (GB: Claim No. KB-…, US: Case No. d:yy-cv-…). `rok` – rok wpływu (domyślnie losowy)."""
        r = self.rng
        k = self._kraj(kraj)
        if rodzaj is not None and rodzaj not in _POZIOMY[k]:
            raise ValueError(f"rodzaj sygnatury {rodzaj!r} nie istnieje dla {k}: {_POZIOMY[k]}")
        if k == "GB":
            rok = rok or r.randint(2023, 2026)
            if rodzaj == "county":   # Money Claim Online / CCMCC: np. K9QZ1234
                return f"Claim No. {r.choice('FGHJKLMNPQ')}{r.randint(0, 9)}{r.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}" \
                       f"{r.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}{cyfry(r, 4)}"
            if rodzaj == "appeal":
                return f"Case No. CA-{rok}-{r.randint(1, 999999):06d}"
            pref = r.choice(("KB", "CL", "BL", "PT", "CR")) if rodzaj is None else "KB"
            if rok < 2023 and pref == "KB":
                pref = "QB"      # Queen's Bench Division do września 2022
            return f"Claim No. {pref}-{rok}-{r.randint(1, 999999):06d}"
        rok = rok or r.randint(2018, 2026)
        yy = rok % 100
        if rodzaj == "state":
            return r.choice((f"Case No. {yy:02d}-CV-{r.randint(1, 999999):06d}",
                             f"Case No. {r.choice(('CGC', 'CUD', 'CIV'))}-{yy:02d}-{r.randint(1, 999999):06d}",
                             f"Case No. {yy:02d}{r.choice(('ST', 'SM', 'CH'))}CV{r.randint(1, 99999):05d}"))
        if rodzaj == "appeal":
            return f"No. {yy:02d}-{r.randint(1000, 9999) if r.random() < 0.6 else r.randint(10000, 99999)}"
        lit = "".join(r.choice("ABCDEFGHJKLMNPRSTUVW") for _ in range(3))
        return f"Case No. {r.randint(1, 9)}:{yy:02d}-cv-{r.randint(1, 99999):05d}-{lit}"

    def sygnatura_cytatu(self, kraj=None, data=None, przedmiot=""):
        """Oznaczenie cytowanego orzeczenia (zwykły tekst): GB – cytowanie neutralne/raportowe, US – reporter.
        Z `data` – rok oznaczenia równy rokowi tej daty."""
        r = self.rng
        if self._kraj(kraj) == "GB":
            rok = data.year if data else r.randint(1985, 2024)
            wzor = r.randrange(5)
            if wzor == 0:
                return f"[{max(rok, 2001)}] EWCA Civ {r.randint(1, 1800)}"
            if wzor == 1:
                div = "KB" if rok >= 2023 else r.choice(("QB", "Ch", "Comm", "TCC"))
                return f"[{max(rok, 2001)}] EWHC {r.randint(1, 3999)} ({div})"
            if wzor == 2:
                return f"[{max(data.year, 2009) if data else r.randint(2009, 2024)}] UKSC {r.randint(1, 60)}"
            if wzor == 3:
                return f"[{rok}] {r.randint(1, 3)} WLR {r.randint(1, 1500)}"
            return f"[{rok}] AC {r.randint(1, 1200)}"
        rok = data.year if data else r.randint(1975, 2024)
        wzor = r.randrange(3)
        if wzor == 0:
            tom = r.randint(400, 600) if not data else max(400, min(600, 579 + (rok - 2016) * 3 + r.randint(-2, 2)))
            return f"{tom} U.S. {r.randint(1, 1100)} ({rok})"
        if wzor == 1:
            ser = "F.4th" if rok >= 2021 else "F.3d" if rok >= 1993 else "F.2d"
            return f"{r.randint(1, 999)} {ser} {r.randint(1, 1300)} ({r.choice(('2d', '9th', '5th', '7th', '3d', '1st'))} Cir. {rok})"
        return (f"{r.randint(1, 999)} F. Supp. {'3d' if rok >= 2000 else '2d'} {r.randint(1, 1200)} "
                f"({r.choice(('S.D.N.Y.', 'N.D. Cal.', 'D. Mass.', 'E.D. Tex.', 'N.D. Ill.'))} {rok})")

    def sad(self, kraj=None, poziom=None):
        """Nazwa sądu. `poziom`: GB `county|high|appeal`, US `federal|state|appeal`; None – dowolny."""
        r = self.rng
        k = self._kraj(kraj)
        if poziom is None:
            return r.choice(_SADY_GB if k == "GB" else _SADY_US)
        if poziom not in _POZIOMY[k]:
            raise ValueError(f"poziom sądu {poziom!r} nie istnieje dla {k}: {_POZIOMY[k]}")
        if k == "US" and self.stan_dok:
            return r.choice(self._sady_stanu(self.stan_dok, poziom))
        return r.choice(_SADY_POZIOMY[(k, poziom)])

    @staticmethod
    def _sady_stanu(stan: str, poziom: str) -> tuple[str, ...]:
        """Sądy danego poziomu w stanie `stan` (tabele; dla stanów spoza tabel – nazwa ogólna z nazwy stanu)."""
        nazwa = _NAZWY_STANOW[stan]
        if poziom == "federal":
            if stan in _OKREGI_STANOW:
                okregi = _OKREGI_STANOW[stan]
            elif stan in _JEDEN_OKREG:
                okregi = (f"District of {nazwa}",)
            else:
                okregi = (f"{'Northern' if stan in _OKREG_PN else 'Eastern'} District of {nazwa}",)
            return tuple(f"United States District Court for the {o}" for o in okregi)
        if poziom == "state":
            return _SADY_STANOWE_STANOW.get(stan) or (f"Superior Court of the State of {nazwa}",)
        obwod = _OBWOD_STANU.get(stan)
        return ((f"United States Court of Appeals for the {obwod} Circuit",) if obwod
                else ("United States Court of Appeals for the District of Columbia Circuit",))

    def tablica(self, kraj=None):
        r = self.rng
        if self._kraj(kraj) == "GB":
            wiek = r.choice(list(range(2, 26)) + list(range(52, 76)))
            # DVLA INF104: litery memory tag bez I, Q, Z (pierwsza i druga); trzy litery losowe bez I, Q
            return (f"{r.choice('ABCDEFGHJKLMNOPRSTUVWXY')}{r.choice('ABCDEFGHJKLMNOPRSTUVWXY')}{wiek:02d} "
                    f"{''.join(r.choice('ABCDEFGHJKLMNOPRSTUVWXY') for _ in range(3))}")
        return f"{r.randint(1, 9)}{''.join(r.choice('ABCDEFGHJKLMNPRSTUVWXYZ') for _ in range(3))}{cyfry(r, 3)}"
