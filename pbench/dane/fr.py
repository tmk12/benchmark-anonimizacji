"""Generator wartości syntetycznych dla Francji (NIR, RPPS, SIREN/SIRET, TVA, IBAN FR z kluczem RIB) oraz sądów
cywilnych (tribunal judiciaire / cour d'appel), numerów RG, greffe du tribunal de commerce i cytatów Cour de cassation."""
from __future__ import annotations

import dataclasses
import datetime as dt

from .wspolne import Adres, BazowyGenerator, DAWKI_MG, MIESIACE, LITERY_FR, SLOWNIKI, cyfry, suma_luhna_kontrola, wagowo

_DEPARTAMENTY = tuple(f"{i:02d}" for i in range(1, 96) if i != 20)
_BANQUES = ("30002", "30003", "30004", "30006", "20041", "10278", "40618", "17515", "11315", "18206", "30056", "16798",
            "12548", "13335", "14707", "30027")
_SADY = ("Tribunal judiciaire", "Tribunal de commerce", "Conseil de prud'hommes", "Cour d'appel", "Tribunal administratif",
         "Cour administrative d'appel")
_POZIOMY = ("tj", "appel")
_RODZAJE_SYGN = ("tj", "appel")
#: Miasta z siedzibą cour d'appel (i tribunal de commerce), obecne w słowniku miejscowości – miasto dokumentu sądowego.
#: Uproszczenie benchmarku: tribunal judiciaire pierwszej instancji leży w tym samym mieście co cour d'appel.
_VILLES_CA = ("Paris", "Lyon", "Toulouse", "Montpellier", "Bordeaux", "Rennes", "Reims", "Grenoble", "Dijon", "Angers",
              "Nîmes", "Aix-en-Provence", "Amiens", "Limoges", "Besançon", "Orléans", "Rouen", "Caen", "Nancy",
              "Poitiers", "Versailles", "Pau", "Bourges", "Chambéry", "Agen")
#: Miasta z tribunal de commerce (siedziby firm): miasta cour d'appel oraz inne duże ośrodki ze słownika.
_VILLES_TC = _VILLES_CA + ("Marseille", "Nice", "Nantes", "Saint-Étienne", "Toulon", "Clermont-Ferrand", "Brest", "Tours", "Annecy", "Perpignan", "Nanterre", "Avignon", "Créteil",
                           "La Rochelle", "Valence", "Quimper", "Troyes", "Grasse")
#: Pierwsza cyfra numeru stacjonarnego (01–05) wg departamentu adresu; 01 – Île-de-France, 02 – północny zachód,
#: 03 – północny wschód, 04 – południowy wschód (z Korsyką), 05 – południowy zachód.
_REGIONY_TEL = {
    "1": "75 77 78 91 92 93 94 95",
    "2": "14 18 22 27 28 29 35 36 37 41 44 45 49 50 53 56 61 72 76 85",
    "3": "02 08 10 21 25 39 51 52 54 55 57 58 59 60 62 67 68 70 71 80 88 89 90",
    "4": "01 03 04 05 06 07 11 13 15 20 26 30 34 38 42 43 48 63 66 69 73 74 83 84",
    "5": "09 12 16 17 19 23 24 31 32 33 40 46 47 64 65 79 81 82 86 87",
}
_PREFIKS_DEPT = {d: p for p, ds in _REGIONY_TEL.items() for d in ds.split()}
_TYPY_MED = ("Clinique", "Polyclinique", "Hôpital privé", "Centre hospitalier privé")
_RDZENIE_MED = ("Saint-Joseph", "Sainte-Marie", "Saint-Louis", "Saint-Martin", "du Parc", "des Cèdres", "Pasteur",
                "Les Lilas", "du Val", "Belle-Rive", "Sainte-Anne", "Saint-Vincent", "de la Source", "Beauregard",
                "des Tilleuls", "Notre-Dame", "Saint-Jean", "du Bosquet", "Les Oliviers", "de l'Europe")
#: Klasy leków, z których pacjent nie dostaje dwóch naraz (kolejność w `leki`).
# Racines ARCEP (decyzja 2018-0881, numery do dzieł audiowizualnych): 01 99 00, 02 61 91, 03 53 01, 04 65 71, 05 36 49, 06 39 98.
_RACINES_ARCEP = {"1": "19900", "2": "26191", "3": "35301", "4": "46571", "5": "53649", "6": "63998"}
_KLASY_LEKOW = {"furosémide": "pętlowy", "torasémide": "pętlowy", "spironolactone": "mra", "éplérénone": "mra",
                "ramipril": "raas", "candésartan": "raas", "sacubitril/valsartan": "raas", "bisoprolol": "bb",
                "métoprolol": "bb", "dapagliflozine": "sglt2", "empagliflozine": "sglt2", "apixaban": "doac",
                "rivaroxaban": "doac"}
#: Izba Cour de cassation wg przedmiotu sporu (cytowane orzeczenia): pożyczka, sprzedaż, umowy – 1re chambre civile;
#: wypadki i odpowiedzialność deliktowa – 2e civile; najem i budownictwo – 3e civile; spółki – chambre commerciale;
#: praca – chambre sociale. Bez przedmiotu – izby cywilne i handlowa.
_IZBY = {"pret": ("civ1",), "vente": ("civ1",), "accident": ("civ2",), "bail": ("civ3",), "societe": ("com",),
         "travail": ("soc",)}
_IZBY_WSZYSTKIE = ("civ1", "civ2", "civ3", "com")
_IZBA_STYL = {   # warianty zapisu: skrót izby przed datą
    "civ1": ("Cass. civ. 1re", "Cass. 1re civ.", "Civ. 1re"),
    "civ2": ("Cass. civ. 2e", "Cass. 2e civ.", "Civ. 2e"),
    "civ3": ("Cass. civ. 3e", "Cass. 3e civ.", "Civ. 3e"),
    "com": ("Cass. com.", "Cass. com.", "Com."),
    "soc": ("Cass. soc.", "Cass. soc.", "Soc."),
}


def nir(rng, data_ur, plec: str) -> str:
    baza = (f"{1 if plec == 'M' else 2}{data_ur.year % 100:02d}{data_ur.month:02d}{rng.choice(_DEPARTAMENTY)}"
            f"{rng.randint(1, 990):03d}{rng.randint(1, 999):03d}")
    return baza + f"{97 - int(baza) % 97:02d}"


def rpps(rng) -> str:
    """Numer RPPS lekarza: 11 cyfr – „10” (osoba fizyczna), 8 cyfr numeru i cyfra kontrolna Luhna."""
    baza = "10" + cyfry(rng, 8)
    return baza + suma_luhna_kontrola(baza)


def siren(rng) -> str:
    baza = str(rng.randint(3, 9)) + cyfry(rng, 7)
    return baza + suma_luhna_kontrola(baza)


def siret(rng, siren_: str) -> str:
    baza = siren_ + f"{rng.randint(1, 99):04d}"
    return baza + suma_luhna_kontrola(baza)


def tva(siren_: str) -> str:
    return f"FR{(12 + 3 * (int(siren_) % 97)) % 97:02d}{siren_}"


def _de_ville(ville: str) -> str:
    if ville.startswith("Le "):
        return "du " + ville[3:]
    if ville.startswith("Les "):
        return "des " + ville[4:]
    return ("d'" + ville) if ville[0] in "AEIOUÉÈÎ" else ("de " + ville)


class GeneratorFR(BazowyGenerator):
    kraje = ("FR",)

    def __init__(self, jezyk, ziarno=0):
        super().__init__(jezyk, ziarno)
        #: miasto dokumentu (siedziba cour d'appel): adresy, sąd i rejestr go preferują (ustawia `losuj_stan_dok`)
        self.miasto_dok: str | None = None
        #: miasto ostatnio wylosowanego sądu (do gniazda `{sad.miasto}`); None dla sądów bez poziomu
        self.miasto_sadu: str | None = None
        self._dept_adresu: str | None = None
        self._rodzaj_firmy = "firma"
        self._firma_w_toku = False

    def _ids_osoby(self, kraj, plec, data_ur, nazwisko):
        return {"NIR": nir(self.rng, data_ur, plec), "RPPS": rpps(self.rng)}

    def _formy(self, kraj):
        """Spółka z kapitałem w udziałach („spolka”) – zawsze SARL (gérant, parts sociales); kancelaria – SELARL;
        placówka medyczna – SAS/SA; zwykła firma – mieszanka."""
        if self._rodzaj_firmy == "spolka":
            return ("SARL",)
        if self._rodzaj_firmy == "kancelaria":
            return ("SELARL",)
        if self._rodzaj_firmy == "placowka":
            return ("SAS",) * 3 + ("SA",)
        return ("SARL",) * 4 + ("SAS",) * 4 + ("SA",) * 2 + ("SASU", "EURL", "SNC")

    def firma(self, kraj=None, rodzaj="firma"):
        """Jak bazowa, ale forma prawna zależy od rodzaju; domena e-mail kancelarii i placówki wynika z jej nazwy."""
        self._rodzaj_firmy, self._firma_w_toku = rodzaj, True     # adres i telefon firmy: miasto z tribunal de commerce
        try:
            f = super().firma(kraj, rodzaj)
        finally:
            self._rodzaj_firmy, self._firma_w_toku = "firma", False
        if rodzaj in ("kancelaria", "placowka"):
            return dataclasses.replace(f, email=self._email_firmy(self._slug_firmy(
                f.nazwa.removeprefix(f"{f.forma} ").removesuffix(f" {f.forma}"))))
        return f

    def _nazwa_firmy(self, rdzen, forma, rodzaj):
        r = self.rng
        if rodzaj == "kancelaria":
            n1, n2 = (wagowo(r, self._s("nazwiska")) for _ in range(2))
            return r.choice((f"{forma} {n1} & {n2} Avocats", f"{forma} {n1} Avocats", f"{forma} {n1}-{n2} Avocats",
                             f"{forma} {n1}, {n2} & Associés Avocats")), forma
        if rodzaj == "placowka":
            return f"{r.choice(_TYPY_MED)} {r.choice(_RDZENIE_MED)} {forma}", forma
        return f"{rdzen} {forma}", forma

    def _ids_firmy(self, kraj, forma):
        s = siren(self.rng)
        return {"SIREN": s, "SIRET": siret(self.rng, s), "VAT": tva(s)}

    def _kandydat_telefonu(self, kraj):
        # tylko racines zarezerwowane przez ARCEP do dzieł audiowizualnych (decyzja 2018-0881): stacjonarna wg regionu
        # adresu (01–05), komórkowa 06 39 98; po racine 4 cyfry
        r = self.rng
        pref = _PREFIKS_DEPT.get(self._dept_adresu or "")
        if pref and (self._firma_w_toku or r.random() < 0.5):
            return f"+33{_RACINES_ARCEP[pref]}{cyfry(r, 4)}"
        return f"+33{_RACINES_ARCEP['6']}{cyfry(r, 4)}"

    def _formatuj_telefon(self, e164, fmt, kraj):
        d = e164[3:]            # 9 cyfr bez zera krajowego: 1 99 00 12 34
        grupy = f"{d[0]} {d[1:3]} {d[3:5]} {d[5:7]} {d[7:9]}"
        return {"krajowy": "0" + grupy, "miedzynarodowy": f"+33 {grupy}", "e164": e164}[fmt]

    def telefon(self, kraj=None):
        try:
            return super().telefon(kraj)
        finally:
            self._dept_adresu = None      # departament ostatniego adresu dotyczy tylko następującego po nim telefonu

    def _bban(self, kraj):
        r = self.rng
        banque, guichet, compte = r.choice(_BANQUES), cyfry(r, 5), cyfry(r, 11)
        cle = 97 - (89 * int(banque) + 15 * int(guichet) + 3 * int(compte)) % 97
        return f"{banque}{guichet}{compte}{cle:02d}"

    def losuj_stan_dok(self):
        """Miasto dokumentu (wśród siedzib cour d'appel, wg wag słownika miejscowości): adresy, sąd i rejestr w nim."""
        miasta = tuple(m for m in self._s("miejscowosci") if m.partition("|")[0] in _VILLES_CA)
        self.miasto_dok = wagowo(self.rng, miasta).partition("|")[0]
        self._dept_adresu = None

    def adres(self, kraj=None):
        r = self.rng
        # bez zamorskich (inny plan numeracji) i miast z rodzajnikiem w nazwie („à Le Mans” → „au Mans” – unikamy)
        miasta = tuple(m for m in self._s("miejscowosci") if not m.endswith("|97") and not m.startswith(("Le ", "Les ")))
        if self.miasto_dok and (self._rodzaj_firmy == "kancelaria" or r.random() < 0.85):   # zwykle w jednym mieście;
            # kancelaria zawsze w mieście sądu (postulation – adwokat z palestry właściwego sądu)
            miasta = tuple(m for m in miasta if m.partition("|")[0] == self.miasto_dok)
        elif self._firma_w_toku:                       # firmy poza miastem dokumentu: tylko miasta z tribunal de commerce
            miasta = tuple(m for m in miasta if m.partition("|")[0] in _VILLES_TC)
        miasto, _, dept = wagowo(r, miasta).partition("|")
        self._dept_adresu = dept
        numer = str(r.randint(1, 199)) + (" bis" if r.random() < 0.05 else "")
        kod = f"750{r.randint(1, 20):02d}" if miasto == "Paris" else f"{dept or r.choice(_DEPARTAMENTY)}{cyfry(r, 3)}"
        return Adres(wagowo(r, self._s("ulice")), numer, kod, miasto, "FR")

    def _kwota_txt(self, calk, grosze, kraj):
        s = f"{calk:,}".replace(",", " ")
        znak = "€" if (self.styl["waluta"] == 0 if self.styl else self.rng.random() < 0.7) else "EUR"
        return f"{s},{grosze:02d} {znak}"

    def _data_txt(self, d, kraj):
        jour = "1er" if d.day == 1 else str(d.day)
        slownie = f"{jour} {MIESIACE['fr'][d.month - 1]} {d.year}"
        if self.styl:       # styl stały w obrębie dokumentu: 0 – data słownie, 1 – zapis liczbowy jj/mm/aaaa
            return slownie if self.styl["data"] == 0 else f"{d:%d/%m/%Y}"
        return self.rng.choice((slownie, f"{d:%d/%m/%Y}"))

    def sygnatura(self, kraj=None, rodzaj=None, rok=None):
        """Numer RG sprawy cywilnej. `rodzaj`: `tj` (tribunal judiciaire, I instancja) albo `appel` (cour d'appel);
        None – dowolna sprawa. `rok` – rok wpływu (dwie pierwsze cyfry numeru: „RG n° 24/01234”)."""
        if rodzaj is not None and rodzaj not in _RODZAJE_SYGN:
            raise ValueError(f"rodzaj sygnatury {rodzaj!r} nie istnieje dla FR: {_RODZAJE_SYGN}")
        r = self.rng
        yy, n = (rok % 100) if rok else r.randint(15, 26), r.randint(1, 9999)
        return r.choice((f"RG n° {yy:02d}/{n:05d}", f"RG n° {yy:02d}/{n:05d}", f"N° RG {yy:02d}/{n:05d}"))

    def sygnatura_cytatu(self, kraj=None, data=None, przedmiot=""):
        """Oznaczenie cytowanego orzeczenia Cour de cassation (zwykły tekst): „Cass. civ. 1re, 12 mars 2019, n° 18-12.345”.
        Z `data` – orzeczenie z tego dnia, a rok numeru pourvoi o 1–2 lata wcześniejszy; `przedmiot` dobiera izbę."""
        r = self.rng
        if data is None:
            rok = r.randint(2009, 2022)
            data = dt.date(rok, 1, 1) + dt.timedelta(days=r.randint(0, 364))
        izba = r.choice(_IZBY.get(przedmiot) or _IZBY_WSZYSTKIE)
        jour = "1er" if data.day == 1 else str(data.day)
        pourvoi = f"n° {(data.year - r.randint(1, 2)) % 100:02d}-{r.randint(10, 29)}.{r.randint(100, 999)}"
        wariant = r.randrange(3)
        skrot = _IZBA_STYL[izba][wariant]
        return (f"{skrot}, {jour} {MIESIACE['fr'][data.month - 1]} {data.year}, "
                f"{'pourvoi ' if wariant == 1 else ''}{pourvoi}")

    def sad(self, kraj=None, poziom=None):
        """Nazwa sądu. `poziom`: `tj` (Tribunal judiciaire w mieście dokumentu) albo `appel` (Cour d'appel tamże);
        None – dowolny (także sądy handlowe, pracy, administracyjne)."""
        r = self.rng
        if poziom is None:
            self.miasto_sadu = None
            ville = wagowo(r, tuple(m.split("|")[0] for m in self._s("miejscowosci")[:45]))
            return f"{r.choice(_SADY)} {_de_ville(ville)}"
        if poziom not in _POZIOMY:
            raise ValueError(f"poziom sądu {poziom!r} nie istnieje dla FR: {_POZIOMY}")
        miasto = self.miasto_dok or wagowo(r, tuple(m.partition("|")[0] for m in self._s("miejscowosci")
                                                    if m.partition("|")[0] in _VILLES_CA))
        self.miasto_sadu = miasto
        nazwa = "Tribunal judiciaire" if poziom == "tj" else "Cour d'appel"
        return f"{nazwa} {_de_ville(miasto)}"

    def nazwa_rejestru(self, adres) -> str:
        """Greffe du tribunal de commerce właściwy dla siedziby firmy: „tribunal de commerce de Lyon”."""
        return f"tribunal de commerce {_de_ville(adres.miejscowosc)}"

    def rcs(self, adres) -> str:
        """Oznaczenie rejestru w tekście: „RCS Lyon” (zwykły tekst; po nim SIREN)."""
        return f"RCS {adres.miejscowosc}"

    def leki(self, n, profil=None):
        """`n` różnych leków z dawką i schematem: wpis słownika „nazwa|dawki|schemat” daje „bisoprolol 5 mg, 1 fois par
        jour le matin”. Gdy istnieje `leki_<profil>_glowne` (np. diuretyk w niewydolności serca), pierwszy lek pochodzi
        stamtąd, a pozostałe z puli ogólnej profilu. Słowniki bez schematu zachowują zachowanie bazowe."""
        r = self.rng
        pula = list(self._pula("leki", profil))
        wpisy = []
        if profil and (SLOWNIKI / self.jezyk / f"leki_{profil}_glowne.txt").exists():
            glowne = self._s(f"leki_{profil}_glowne")
            pierwszy = r.choice(glowne)
            wpisy.append(pierwszy)
            pula = [w for w in pula if w != pierwszy]
        uzyte = {_KLASY_LEKOW.get(w.partition("|")[0]) for w in wpisy} - {None}
        r.shuffle(pula)
        for w in pula:                    # bez dwóch leków tej samej klasy (dwa diuretyki pętlowe, dwa antagoniści aldosteronu…)
            if len(wpisy) == n:
                break
            klasa = _KLASY_LEKOW.get(w.partition("|")[0])
            if klasa is None or klasa not in uzyte:
                wpisy.append(w)
                uzyte.add(klasa)
        wynik = []
        for w in wpisy:
            nazwa, _, reszta = w.partition("|")
            dawki, _, schemat = reszta.partition("|")
            tekst = f"{nazwa} {r.choice(dawki.split(';')) if dawki else r.choice(DAWKI_MG)} mg"
            wynik.append(f"{tekst}, {schemat}" if schemat else tekst)
        return wynik

    def barreau(self, adres_lub_miasto) -> str:
        """Palestra: „barreau de Lyon” / „barreau d'Angers” (zwykły tekst); argument – adres albo nazwa miasta."""
        return f"barreau {_de_ville(getattr(adres_lub_miasto, 'miejscowosc', adres_lub_miasto))}"

    def tablica(self, kraj=None):
        r = self.rng
        l = lambda: "".join(r.choice(LITERY_FR) for _ in range(2))
        while True:
            pierwsza, druga = l(), l()
            # arrêté du 9.2.2009, Annexe VII: WW to numer tymczasowy (sekcja C), SS wykluczone (źródło wtórne) – oba pomijamy
            if not ({pierwsza, druga} & {"WW", "SS"}):
                return f"{pierwsza}-{r.randint(1, 999):03d}-{druga}"
