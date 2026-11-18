"""Generator wartości syntetycznych dla Niemiec (Steuer-ID, SVNR, KVNR, LANR, Personalausweis, USt-IdNr, Steuernummer,
HRB, IBAN DE) oraz sądów cywilnych (Amtsgericht / Landgericht) i Aktenzeichen wg poziomu sądu."""
from __future__ import annotations

import dataclasses
import datetime as dt

from .wspolne import Adres, BazowyGenerator, MIESIACE, ascii_, cyfry, wagowo

_BLZ = ("10010010", "10020500", "10050000", "12030000", "37040044", "37050198", "50010517", "50050201", "50040000",
        "70070010", "70150000", "20010020", "20050550", "25050180", "30070010", "36010043", "60050101", "66050101",
        "76050101", "85050300", "86055592", "87050000", "10070000", "25010030", "44010046", "60010070", "68050101")
# Bereichsnummern (pierwsze dwie cyfry SVNR) wg VKVV, Anlage (Tabelle der Bereichsnummern; gesetze-im-internet.de/vkvv,
# BGBl. I 2004, 3290): regionalne DRV 02–04, 08–21, 23–26, 28, 29; DRV Bund (regionalny + 40) 42–44, 48–61, 63–66, 68, 69;
# Knappschaft-Bahn-See 38, 39, 80–82, 89. Numeru 40 nie ma (Zulagenstelle, nie SVNR).
_BEREICHE = ("02", "03", "04", "08", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21",
             "23", "24", "25", "26", "28", "29", "38", "39", "42", "43", "44", "48", "49", "50", "51", "52", "53",
             "54", "55", "56", "57", "58", "59", "60", "61", "63", "64", "65", "66", "68", "69", "80", "81", "82", "89")
# Bundesnetzagentur, „Rufnummern für Medienproduktionen (Drama Numbers)”: stacjonarne pule (kierunkowy, początek numeru; + 3 cyfry)
_DRAMA = (("30", "23125"), ("40", "66969"), ("69", "90009"), ("89", "99998"), ("221", "4710"))
# ... i zarezerwowane numery komórkowe z tej samej listy (numer bez zera wiodącego; ostatnie `n` cyfr to zakres 00–99)
_MOBIL = (("15228817386", 0), ("15228895456", 0), ("15254599371", 0), ("17139200", 2), ("1729925904", 0),
          ("1729968532", 0), ("1729973185", 0), ("1729973186", 0), ("1729980752", 0), ("1749091317", 0),
          ("1749464308", 0), ("176040690", 2))
_KENNZEICHEN = ("M", "B", "HH", "K", "F", "S", "D", "DO", "E", "L", "HB", "H", "N", "MS", "KA", "MA", "AC", "BN", "DD",
                "BS", "FR", "HD", "UL", "OS", "AUR", "MÜ", "GÖ", "WÜ", "KI", "MZ", "WI", "BO", "EN", "RE", "ST")
_GERICHTE = ("Amtsgericht Charlottenburg", "Amtsgericht Mitte", "Amtsgericht München", "Amtsgericht Hamburg",
             "Amtsgericht Köln", "Amtsgericht Frankfurt am Main", "Amtsgericht Stuttgart", "Amtsgericht Düsseldorf",
             "Landgericht Berlin", "Landgericht München I", "Landgericht München II", "Landgericht Hamburg",
             "Landgericht Köln", "Landgericht Frankfurt am Main", "Landgericht Stuttgart", "Landgericht Düsseldorf",
             "Landgericht Essen", "Landgericht Leipzig", "Oberlandesgericht Frankfurt am Main",
             "Oberlandesgericht München", "Oberlandesgericht Hamm", "Oberlandesgericht Köln",
             "Kammergericht Berlin", "Arbeitsgericht Berlin", "Arbeitsgericht Frankfurt am Main",
             "Landesarbeitsgericht Hamburg", "Sozialgericht Köln", "Verwaltungsgericht Stuttgart",
             "Finanzgericht München", "Bundesgerichtshof", "Bundesarbeitsgericht", "Bundesverwaltungsgericht")
_POZIOMY = ("amtsgericht", "landgericht", "berufung")
_RODZAJE_SYGN = ("ag", "lg", "berufung")
#: Miasta z siedzibą Landgericht (słownik miejscowości) -> nazwa Landgericht; reszta: „Landgericht <miasto>”.
_LG_WYJATKI = {"München": "Landgericht München I", "Nürnberg": "Landgericht Nürnberg-Fürth",
               "Fürth": "Landgericht Nürnberg-Fürth", "Halle (Saale)": "Landgericht Halle",
               "Freiburg im Breisgau": "Landgericht Freiburg", "Kempten": "Landgericht Kempten (Allgäu)"}
_LG_SITZE = ("Berlin", "Hamburg", "München", "Köln", "Frankfurt am Main", "Stuttgart", "Düsseldorf", "Leipzig",
             "Dortmund", "Essen", "Bremen", "Dresden", "Hannover", "Nürnberg", "Duisburg", "Bochum", "Wuppertal",
             "Bielefeld", "Bonn", "Münster", "Karlsruhe", "Mannheim", "Augsburg", "Wiesbaden", "Mönchengladbach",
             "Braunschweig", "Chemnitz", "Kiel", "Aachen", "Halle (Saale)", "Magdeburg", "Freiburg im Breisgau",
             "Krefeld", "Lübeck", "Erfurt", "Mainz", "Rostock", "Kassel", "Hagen", "Saarbrücken", "Potsdam",
             "Oldenburg", "Osnabrück", "Heidelberg", "Darmstadt", "Paderborn", "Regensburg", "Ingolstadt", "Würzburg",
             "Fürth", "Ulm", "Heilbronn", "Göttingen", "Trier", "Koblenz", "Hildesheim", "Siegen", "Cottbus", "Gera",
             "Zwickau", "Schwerin", "Flensburg", "Konstanz", "Bamberg", "Bayreuth", "Passau", "Landshut", "Kempten",
             "Tübingen", "Detmold")
#: Amtsgerichte w miastach z kilkoma (Berlin, Hamburg) – losowy z listy; pozostałe: „Amtsgericht <miasto>”.
_AG_MIASTA = {
    "Berlin": ("Amtsgericht Mitte", "Amtsgericht Charlottenburg", "Amtsgericht Pankow", "Amtsgericht Schöneberg",
               "Amtsgericht Neukölln", "Amtsgericht Köpenick", "Amtsgericht Spandau", "Amtsgericht Lichtenberg"),
    "Hamburg": ("Amtsgericht Hamburg", "Amtsgericht Hamburg-Altona", "Amtsgericht Hamburg-Wandsbek",
                "Amtsgericht Hamburg-Harburg", "Amtsgericht Hamburg-Barmbek"),
}
#: Registergericht (Handelsregister) właściwy dla siedziby: Berlin – Charlottenburg; kilka miast Zagłębia Ruhry
#: i Nadrenii podlega sąsiedniemu sądowi. Uproszczenie benchmarku – spójność w dokumencie, nie pełna mapa sądów.
_REGISTERGERICHT = {"Berlin": "Amtsgericht Charlottenburg", "Mülheim an der Ruhr": "Amtsgericht Duisburg",
                    "Oberhausen": "Amtsgericht Duisburg", "Moers": "Amtsgericht Duisburg",
                    "Bottrop": "Amtsgericht Essen", "Herne": "Amtsgericht Bochum", "Remscheid": "Amtsgericht Wuppertal",
                    "Solingen": "Amtsgericht Wuppertal", "Leverkusen": "Amtsgericht Köln",
                    "Bergisch Gladbach": "Amtsgericht Köln", "Viersen": "Amtsgericht Mönchengladbach",
                    "Ludwigshafen": "Amtsgericht Ludwigshafen am Rhein", "Hamburg": "Amtsgericht Hamburg"}
#: Numery kierunkowe miast (bez zera); tylko dla miast z siedzibą Landgericht – telefon stacjonarny zgodny z adresem.
_VORWAHL = {
    "Berlin": "30", "Hamburg": "40", "München": "89", "Köln": "221", "Frankfurt am Main": "69", "Stuttgart": "711",
    "Düsseldorf": "211", "Leipzig": "341", "Dortmund": "231", "Essen": "201", "Bremen": "421", "Dresden": "351",
    "Hannover": "511", "Nürnberg": "911", "Duisburg": "203", "Bochum": "234", "Wuppertal": "202", "Bielefeld": "521",
    "Bonn": "228", "Münster": "251", "Karlsruhe": "721", "Mannheim": "621", "Augsburg": "821", "Wiesbaden": "611",
    "Mönchengladbach": "2161", "Braunschweig": "531", "Chemnitz": "371", "Kiel": "431", "Aachen": "241",
    "Halle (Saale)": "345", "Magdeburg": "391", "Freiburg im Breisgau": "761", "Krefeld": "2151", "Lübeck": "451",
    "Erfurt": "361", "Mainz": "6131", "Rostock": "381", "Kassel": "561", "Hagen": "2331", "Saarbrücken": "681",
    "Potsdam": "331", "Oldenburg": "441", "Osnabrück": "541", "Heidelberg": "6221", "Darmstadt": "6151",
    "Paderborn": "5251", "Regensburg": "941", "Ingolstadt": "841", "Würzburg": "931", "Fürth": "911", "Ulm": "731",
    "Heilbronn": "7131", "Göttingen": "551", "Trier": "651", "Koblenz": "261", "Hildesheim": "5121", "Siegen": "271",
    "Cottbus": "355", "Gera": "365", "Zwickau": "375", "Schwerin": "385", "Flensburg": "461", "Konstanz": "7531",
    "Bamberg": "951", "Bayreuth": "921", "Passau": "851", "Landshut": "871", "Kempten": "831", "Tübingen": "7071",
    "Detmold": "5231",
}
_RDZENIE_MED = ("St. Josef", "Marienhospital", "Nordstadt", "Rheinland", "am Park", "Bethesda", "St. Elisabeth",
                "Diakonie", "Süd", "Mitte", "Luisenhöhe", "St. Vincenz", "Sophienhospital", "Weserbergland",
                "Elbe", "Heilig Geist", "Johanniter", "Maria Hilf")
_TYPY_MED = ("Klinikum", "Krankenhaus", "Evangelisches Krankenhaus", "Fachklinik", "Städtisches Klinikum",
             "Katholisches Klinikum", "Medizinisches Versorgungszentrum")
#: Senat BGH właściwy dla przedmiotu sporu (cytowane orzeczenia): pożyczka/kredyt – XI ZR, kupno i najem – VIII ZR,
#: delikt i wypadki – VI ZR, umowa o dzieło – VII ZR; bez przedmiotu – Senaty cywilne ogólnie.
_SENATY = {"darlehen": ("XI",), "kauf": ("VIII",), "miete": ("VIII",), "delikt": ("VI",), "werk": ("VII",)}
#: Forma prawna -> rejestr: Abteilung B (spółki kapitałowe), A (osobowe, e. K.), Partnerschaftsregister (PartG).
_REJESTR_FORMY = {"GmbH": "HRB", "gGmbH": "HRB", "AG": "HRB", "UG (haftungsbeschränkt)": "HRB", "KG": "HRA",
                  "OHG": "HRA", "GmbH & Co. KG": "HRA", "e. K.": "HRA", "PartG mbB": "PR"}
_STEUERNR_FORMATY = ((2, 3, 5), (3, 3, 5), (3, 4, 4))


def kontrola_mod_11_10(cyfry_: str) -> str:
    """Cyfra kontrolna ISO 7064 Mod 11,10 (Steuer-ID, USt-IdNr)."""
    produkt = 10
    for c in cyfry_:
        suma = (int(c) + produkt) % 10 or 10
        produkt = (2 * suma) % 11
    k = 11 - produkt
    return str(0 if k == 10 else k)


def steuer_id(rng) -> str:
    while True:
        if rng.random() < 0.8:
            d = rng.sample("0123456789", 9)
            d.append(rng.choice(d))  # jedna cyfra dwa razy
        else:
            d = rng.sample("0123456789", 8)
            d += [d[0]] * 2  # jedna cyfra trzy razy, nigdy obok siebie
        rng.shuffle(d)
        s = "".join(d)
        if s[0] != "0" and "000" not in s and not any(c * 3 in s for c in "123456789"):
            return s + kontrola_mod_11_10(s)


def svnr(rng, data_ur: dt.date, plec: str, nazwisko: str) -> str:
    litera = ascii_(nazwisko)[0].upper()
    seria = rng.randint(0, 49) if plec == "M" else rng.randint(50, 99)
    baza = f"{rng.choice(_BEREICHE)}{data_ur:%d%m%y}{litera}{seria:02d}"
    cyfry_ = baza[:8] + f"{ord(litera) - 64:02d}" + baza[9:]
    suma = 0
    for c, w in zip(cyfry_, (2, 1, 2, 5, 7, 1, 2, 1, 2, 1, 2, 1)):
        x = int(c) * w
        suma += x // 10 + x % 10
    return baza + str(suma % 10)


def kvnr(rng) -> str:
    """Krankenversichertennummer: litera A–Z + 8 cyfr + cyfra kontrolna (litera -> 01..26, wagi 1,2,1,2…, suma cyfr
    iloczynów mod 10; opis algorytmu GKV-Spitzenverband z pamięci autora, benchmark nie zależy od jego dokładności)."""
    litera = rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    cyfry_ = f"{ord(litera) - 64:02d}" + cyfry(rng, 8)
    suma = 0
    for i, c in enumerate(cyfry_):
        x = int(c) * (1 if i % 2 == 0 else 2)
        suma += x // 10 + x % 10
    return litera + cyfry_[2:] + str(suma % 10)


# Kody grupy lekarskiej (ostatnie 2 cyfry LANR) występujące w Anlage 2 Richtlinie KBV: 01–69, 85, 87, 91, 99.
_LANR_GRUPY = tuple(f"{n:02d}" for n in (*range(1, 70), 85, 87, 91, 99))


def lanr(rng) -> str:
    """Lebenslange Arztnummer: 6 cyfr numeru lekarza, cyfra kontrolna (wagi 4,9,4,9,4,9; 10 − suma mod 10) i 2 cyfry
    kodu grupy z `_LANR_GRUPY`. Źródło: KBV, Richtlinie nach § 75 Abs. 7 SGB V (1.1.2024), § 3 Abs. 1 i Anlage 2."""
    baza = str(rng.randint(1, 9)) + cyfry(rng, 5)
    suma = sum(int(c) * (4 if i % 2 == 0 else 9) for i, c in enumerate(baza))
    return baza + str((10 - suma % 10) % 10) + rng.choice(_LANR_GRUPY)


def steuernummer(rng) -> str:
    """Steuernummer firmy w jednym z formatów krajów związkowych (2/3/5, 3/3/5, 3/4/4 cyfr)."""
    dlugosci = rng.choice(_STEUERNR_FORMATY)
    czesci = [str(rng.randint(1, 9)) + cyfry(rng, dlugosci[0] - 1)] + [cyfry(rng, n) for n in dlugosci[1:]]
    return "/".join(czesci)


def personalausweis(rng) -> str:
    """Seriennummer: 9 znaków; dozwolone wyłącznie litery CFGHJKLMNPRTVWXYZ i cyfry 1–9 (PAuswV, Anlage 3, Vorbem. 9;
    PAuswG § 2 Abs. 8). Pierwszy znak – litera z zestawu walidatora Privatizera (LMNPRTVWXY)."""
    return rng.choice("LMNPRTVWXY") + "".join(rng.choice("CFGHJKLMNPRTVWXYZ123456789") for _ in range(8))


def ust_idnr(rng) -> str:
    baza = str(rng.randint(1, 9)) + cyfry(rng, 7)
    return "DE" + baza + kontrola_mod_11_10(baza)


class GeneratorDE(BazowyGenerator):
    kraje = ("DE",)

    def __init__(self, jezyk, ziarno=0):
        super().__init__(jezyk, ziarno)
        #: miasto dokumentu (siedziba Landgericht): adresy, sąd i rejestr go preferują (ustawia `losuj_stan_dok`)
        self.miasto_dok: str | None = None
        #: miasto ostatnio wylosowanego sądu (do gniazda `{sad.miasto}`); None dla sądów bez poziomu
        self.miasto_sadu: str | None = None
        self._miasto_adresu: str | None = None
        self._rodzaj_firmy = "firma"
        self._firma_w_toku = False

    def _ids_osoby(self, kraj, plec, data_ur, nazwisko):
        return {"STEUER_ID": steuer_id(self.rng), "SVNR": svnr(self.rng, data_ur, plec, nazwisko),
                "PERSONALAUSWEIS": personalausweis(self.rng), "KVNR": kvnr(self.rng), "LANR": lanr(self.rng)}

    def _formy(self, kraj):
        """Spółka z kapitałem w udziałach („spolka”) – zawsze GmbH (Stammkapital >= 25 000 €); kancelaria – PartG mbB;
        placówka medyczna – gGmbH/GmbH."""
        if self._rodzaj_firmy == "spolka":
            return ("GmbH",)
        if self._rodzaj_firmy == "kancelaria":
            return ("PartG mbB",)
        if self._rodzaj_firmy == "placowka":
            return ("gGmbH",) * 3 + ("GmbH",)
        return ("GmbH",) * 7 + ("AG",) * 2 + ("UG (haftungsbeschränkt)", "KG", "GmbH & Co. KG", "OHG", "e. K.")

    def firma(self, kraj=None, rodzaj="firma"):
        """Jak bazowa, ale forma prawna zależy od rodzaju; domena e-mail kancelarii i placówki wynika z jej nazwy."""
        self._rodzaj_firmy, self._firma_w_toku = rodzaj, True     # adres i telefon firmy: miasto z numerem kierunkowym
        try:
            f = super().firma(kraj, rodzaj)
        finally:
            self._rodzaj_firmy, self._firma_w_toku = "firma", False
        if rodzaj in ("kancelaria", "placowka"):
            return dataclasses.replace(f, email=self._email_firmy(self._slug_firmy(f.nazwa.removesuffix(f" {f.forma}"))))
        return f

    def _nazwa_firmy(self, rdzen, forma, rodzaj):
        r = self.rng
        if rodzaj == "kancelaria":
            n1, n2 = (wagowo(r, self._s("nazwiska")) for _ in range(2))
            return r.choice((f"{n1} & {n2} Rechtsanwälte {forma}", f"Rechtsanwälte {n1}, {n2} & Kollegen {forma}",
                             f"{n1}, {n2} & Partner Rechtsanwälte {forma}", f"{n1} Rechtsanwälte {forma}")), forma
        if rodzaj == "placowka":
            return f"{r.choice(_TYPY_MED)} {r.choice(_RDZENIE_MED)} {forma}", forma
        return f"{rdzen} {forma}", forma

    def _ids_firmy(self, kraj, forma):
        rejestr = _REJESTR_FORMY[forma]      # HRB (GmbH, AG, UG), HRA (KG, OHG, e. K.), PR (PartG mbB)
        return {rejestr: f"{rejestr} {self.rng.randint(1000, 299_999)}", "VAT": ust_idnr(self.rng),
                "STEUERNR": steuernummer(self.rng)}

    def _kandydat_telefonu(self, kraj):
        # tylko pule Bundesnetzagentur (Drama Numbers): stacjonarna pula miasta adresu albo zarezerwowany numer komórkowy
        r = self.rng
        miasto = self._miasto_adresu
        pula = {k: c for k, c in _DRAMA}.get(_VORWAHL.get(miasto))
        if pula is not None and (self._firma_w_toku or r.random() < 0.6):
            return f"+49{_VORWAHL[miasto]}{pula}{cyfry(r, 3)}"
        if miasto is None and r.random() < 0.3:
            kier, pula = r.choice(_DRAMA)
            return f"+49{kier}{pula}{cyfry(r, 3)}"
        numer, zakres = r.choice(_MOBIL)
        return f"+49{numer}{cyfry(r, zakres)}"

    def telefon(self, kraj=None):
        try:
            return super().telefon(kraj)
        finally:
            self._miasto_adresu = None      # miasto ostatniego adresu dotyczy tylko następującego po nim telefonu

    def _bban(self, kraj):
        return self.rng.choice(_BLZ) + cyfry(self.rng, 10)

    def losuj_stan_dok(self):
        """Miasto dokumentu (wśród siedzib Landgericht, wg wag słownika miejscowości): adresy, sąd i rejestr w nim."""
        miasta = tuple(m for m in self._s("miejscowosci") if m.partition("|")[0] in _LG_SITZE)
        self.miasto_dok = wagowo(self.rng, miasta).partition("|")[0]
        self._miasto_adresu = None

    def adres(self, kraj=None):
        r = self.rng
        miasta = self._s("miejscowosci")
        if self.miasto_dok and r.random() < 0.85:      # adresy dokumentu zwykle w jednym mieście
            miasta = tuple(m for m in miasta if m.partition("|")[0] == self.miasto_dok)
        elif self._firma_w_toku:                       # firmy poza miastem dokumentu: tylko miasta ze znanym kierunkowym
            miasta = tuple(m for m in miasta if m.partition("|")[0] in _VORWAHL)
        miasto, _, pref = wagowo(r, miasta).partition("|")
        self._miasto_adresu = miasto
        numer = str(r.randint(1, 199)) + (r.choice("abc") if r.random() < 0.1 else "")
        return Adres(wagowo(r, self._s("ulice")), numer, f"{pref or cyfry(r, 2)}{cyfry(r, 3)}", miasto, "DE")

    def _kwota_txt(self, calk, grosze, kraj):
        s = f"{calk:,}".replace(",", ".")
        znak = "€" if (self.styl["waluta"] == 0 if self.styl else self.rng.random() < 0.7) else "EUR"
        return f"{s},{grosze:02d} {znak}"

    def _data_txt(self, d, kraj):
        slownie = f"{d.day}. {MIESIACE['de'][d.month - 1]} {d.year}"
        if self.styl:       # styl stały w obrębie dokumentu: 0 – data słownie, 1 – zapis liczbowy dd.mm.rrrr
            return slownie if self.styl["data"] == 0 else f"{d:%d.%m.%Y}"
        return self.rng.choice((slownie, f"{d:%d.%m.%Y}", f"{d:%d.%m.%Y}"))

    def sygnatura(self, kraj=None, rodzaj=None, rok=None):
        """Aktenzeichen sprawy cywilnej. `rodzaj`: `ag` („12 C 345/24” – Zivilabteilung Amtsgericht), `lg` („2 O 123/24” –
        Zivilkammer Landgericht, I instancja), `berufung` („8 S 45/24” – Berufungskammer LG); None – dowolna sprawa
        cywilna I instancji. `rok` – rok wpływu (dwie ostatnie cyfry w numerze)."""
        if rodzaj is not None and rodzaj not in _RODZAJE_SYGN:
            raise ValueError(f"rodzaj sygnatury {rodzaj!r} nie istnieje dla DE: {_RODZAJE_SYGN}")
        r = self.rng
        rr = (rok or r.randint(2018, 2026)) % 100
        rodzaj = rodzaj or r.choices(("ag", "lg"), weights=(3, 1))[0]
        if rodzaj == "ag":
            return f"{r.randint(1, 70)} C {r.randint(1, 1999)}/{rr:02d}"
        if rodzaj == "lg":
            return f"{r.randint(1, 40)} O {r.randint(1, 999)}/{rr:02d}"
        return f"{r.randint(1, 40)} S {r.randint(1, 299)}/{rr:02d}"

    def sygnatura_cytatu(self, kraj=None, data=None, przedmiot=""):
        """Oznaczenie cytowanego orzeczenia BGH (zwykły tekst): „BGH, Urt. v. 12.3.2019 – VI ZR 123/18”. Z `data` –
        orzeczenie z tego dnia, a rok Aktenzeichen o 1–2 lata wcześniejszy; `przedmiot` dobiera Senat (`_SENATY`)."""
        r = self.rng
        if data is None:
            rok = r.randint(2009, 2022)
            data = dt.date(rok, 1, 1) + dt.timedelta(days=r.randint(0, 364))
        rok = data.year
        senat = r.choice(_SENATY.get(przedmiot) or ("I", "II", "III", "V", "VI", "VII", "VIII", "IX", "X", "XI"))
        az = f"{senat} ZR {r.randint(1, 250)}/{(rok - r.randint(1, 2)) % 100:02d}"
        wariant = r.randrange(3)
        if wariant == 0:
            return f"BGH, Urt. v. {data.day}.{data.month}.{rok} – {az}"
        if wariant == 1:
            return f"BGH, Urteil vom {data.day}. {MIESIACE['de'][data.month - 1]} {rok} – {az}"
        return f"BGH, Beschl. v. {data.day}.{data.month}.{rok} – {az}"

    def _ag(self, miasto: str) -> str:
        return self.rng.choice(_AG_MIASTA[miasto]) if miasto in _AG_MIASTA else f"Amtsgericht {miasto}"

    def sad(self, kraj=None, poziom=None):
        """Nazwa sądu. `poziom`: `amtsgericht` (w mieście dokumentu), `landgericht` (I instancja) albo `berufung`
        (Landgericht jako sąd apelacyjny – ta sama nazwa); None – dowolny (także sądy wyższe i specjalne)."""
        r = self.rng
        if poziom is None:
            self.miasto_sadu = None
            return r.choice(_GERICHTE)
        if poziom not in _POZIOMY:
            raise ValueError(f"poziom sądu {poziom!r} nie istnieje dla DE: {_POZIOMY}")
        miasto = self.miasto_dok or wagowo(r, tuple(m.partition("|")[0] for m in self._s("miejscowosci")
                                                    if m.partition("|")[0] in _LG_SITZE))
        self.miasto_sadu = miasto
        if poziom == "amtsgericht":
            return self._ag(miasto)
        return _LG_WYJATKI.get(miasto, f"Landgericht {miasto}")

    def nazwa_rejestru(self, adres) -> str:
        """Registergericht (Handelsregister) właściwy dla siedziby firmy (miasto adresu)."""
        miasto = adres.miejscowosc
        return _REGISTERGERICHT.get(miasto, f"Amtsgericht {miasto}")

    def tablica(self, kraj=None):
        r = self.rng
        miasto = r.choice(_KENNZEICHEN)
        while True:
            litery = "".join(r.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(r.randint(1, 2)))
            cyfry_ = str(r.randint(1, 9)) + cyfry(r, r.randint(0, 3))
            if len(miasto + litery + cyfry_) <= 8:
                return f"{miasto} {litery} {cyfry_}"
