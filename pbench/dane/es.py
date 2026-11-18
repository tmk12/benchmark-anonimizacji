"""Generator wartości syntetycznych dla Hiszpanii (DNI/NIE, NUSS, CIF, IBAN ES)."""
from __future__ import annotations

import dataclasses
import datetime as dt

from .wspolne import Adres, BazowyGenerator, MIESIACE, SPOLGLOSKI_ES, cyfry, wagowo

_LITERY_DNI = "TRWAGMYFPDXBNJZSQVHLCKE"
_ENTIDADES = ("0049", "0182", "2100", "0081", "0128", "0075", "2038", "0030", "1465", "0073", "0487", "2085", "3058",
              "2080", "0138", "3025", "2095")
_CIF_FORMY = {"S.L.": "B", "S.A.": "A", "S.L.U.": "B", "S.Coop.": "F", "S.C.": "J", "C.B.": "E"}
_TIPOS = ("Juzgado de Primera Instancia", "Juzgado de lo Social", "Juzgado de lo Mercantil",
          "Juzgado de Instrucción", "Juzgado de lo Contencioso-Administrativo", "Juzgado de lo Penal")
_STALE = ("Tribunal Supremo", "Audiencia Nacional", "Tribunal Superior de Justicia de Madrid",
          "Tribunal Superior de Justicia de Andalucía", "Tribunal Superior de Justicia de Cataluña",
          "Tribunal Superior de Justicia de la Comunidad Valenciana", "Audiencia Provincial de Madrid",
          "Audiencia Provincial de Barcelona", "Audiencia Provincial de Valencia", "Audiencia Provincial de Sevilla")
_PESOS_DC = (1, 2, 4, 8, 5, 10, 9, 7, 3, 6)

#: Kod prowincji (pierwsze dwie cyfry kodu pocztowego) -> (nazwa w „Audiencia Provincial de …” / „Registro Mercantil
#: de …”, stolica jak w słowniku miejscowości, litery hoja registral Registro Mercantil).
PROVINCIAS = {
    "01": ("Álava", "Vitoria-Gasteiz", "VI"), "02": ("Albacete", "Albacete", "AB"), "03": ("Alicante", "Alicante", "A"),
    "04": ("Almería", "Almería", "AL"), "05": ("Ávila", "Ávila", "AV"), "06": ("Badajoz", "Badajoz", "BA"),
    "07": ("Illes Balears", "Palma", "PM"), "08": ("Barcelona", "Barcelona", "B"), "09": ("Burgos", "Burgos", "BU"),
    "10": ("Cáceres", "Cáceres", "CC"), "11": ("Cádiz", "Cádiz", "CA"), "12": ("Castellón", "Castellón de la Plana", "CS"),
    "13": ("Ciudad Real", "Ciudad Real", "CR"), "14": ("Córdoba", "Córdoba", "CO"), "15": ("A Coruña", "La Coruña", "C"),
    "16": ("Cuenca", "Cuenca", "CU"), "17": ("Girona", "Girona", "GI"), "18": ("Granada", "Granada", "GR"),
    "19": ("Guadalajara", "Guadalajara", "GU"), "20": ("Gipuzkoa", "San Sebastián", "SS"), "21": ("Huelva", "Huelva", "H"),
    "22": ("Huesca", "Huesca", "HU"), "23": ("Jaén", "Jaén", "J"), "24": ("León", "León", "LE"),
    "25": ("Lleida", "Lérida", "L"), "26": ("La Rioja", "Logroño", "LO"), "27": ("Lugo", "Lugo", "LU"),
    "28": ("Madrid", "Madrid", "M"), "29": ("Málaga", "Málaga", "MA"), "30": ("Murcia", "Murcia", "MU"),
    "31": ("Navarra", "Pamplona", "NA"), "32": ("Ourense", "Ourense", "OR"), "33": ("Asturias", "Oviedo", "O"),
    "34": ("Palencia", "Palencia", "P"), "35": ("Las Palmas", "Las Palmas de Gran Canaria", "GC"),
    "36": ("Pontevedra", "Pontevedra", "PO"), "37": ("Salamanca", "Salamanca", "SA"),
    "38": ("Santa Cruz de Tenerife", "Santa Cruz de Tenerife", "TF"), "39": ("Cantabria", "Santander", "S"),
    "40": ("Segovia", "Segovia", "SG"), "41": ("Sevilla", "Sevilla", "SE"), "42": ("Soria", "Soria", "SO"),
    "43": ("Tarragona", "Tarragona", "T"), "44": ("Teruel", "Teruel", "TE"), "45": ("Toledo", "Toledo", "TO"),
    "46": ("Valencia", "Valencia", "V"), "47": ("Valladolid", "Valladolid", "VA"), "48": ("Bizkaia", "Bilbao", "BI"),
    "49": ("Zamora", "Zamora", "ZA"), "50": ("Zaragoza", "Zaragoza", "Z"), "51": ("Ceuta", "Ceuta", "CE"),
    "52": ("Melilla", "Melilla", "ME"),
}
#: Prefiks telefonu stacjonarnego wg prowincji (kod 9xx: 91 Madryt, 93 Barcelona…).
PREFIKSY_TEL = {
    "01": "945", "02": "967", "03": "965", "04": "950", "05": "920", "06": "924", "07": "971", "08": "93", "09": "947",
    "10": "927", "11": "956", "12": "964", "13": "926", "14": "957", "15": "981", "16": "969", "17": "972", "18": "958",
    "19": "949", "20": "943", "21": "959", "22": "974", "23": "953", "24": "987", "25": "973", "26": "941", "27": "982",
    "28": "91", "29": "952", "30": "968", "31": "948", "32": "988", "33": "985", "34": "979", "35": "928", "36": "986",
    "37": "923", "38": "922", "39": "942", "40": "921", "41": "954", "42": "975", "43": "977", "44": "978", "45": "925",
    "46": "96", "47": "983", "48": "94", "49": "980", "50": "976", "51": "956", "52": "952",
}
#: Liczba juzgados I instancji w stolicy prowincji (górna granica numeru „n.º”); w pozostałych – do 6.
_JUZGADOS = {"28": 100, "08": 60, "46": 30, "41": 20, "29": 20, "48": 12, "50": 18, "35": 12, "38": 10, "30": 10, "03": 10}
_SECCIONES = {"28": 28, "08": 19, "46": 11, "41": 8, "29": 7, "03": 9, "48": 6, "35": 5, "30": 5, "11": 7, "15": 6}
_POZIOMY = ("primera", "apelacion")
_RODZAJE_SYGN = ("ordinario", "verbal", "apelacion")
_PROC_DODATKOWE = ("Procedimiento Ordinario", "Juicio Verbal", "Procedimiento Monitorio", "Procedimiento de Familia",
                   "Ejecución de Títulos Judiciales", "Autos", "Procedimiento de Jura de Cuentas")
_DOBRA_FORMA_KANC = ("{n1} {n2} Abogados", "Bufete {n1} y Asociados", "{rdzen} Abogados y Asesores", "{n1} & {n2} Letrados",
                     "Despacho {n1} Abogados")
_RDZENIE_MED = ("San Rafael", "Santa Elena", "Virgen del Mar", "Nuestra Señora de la Paz", "San Carlos", "La Milagrosa",
                "Santa Cruz", "Reina Isabel", "Virgen de la Luz", "San Juan de Dios", "Santa Lucía", "Sagrado Corazón",
                "La Concepción", "San Roque", "Virgen del Pilar", "Santa Clara")
_TIPOS_MED = ("Hospital Universitario", "Hospital General", "Clínica", "Centro Médico", "Hospital")


def letra_dni(n: int) -> str:
    return _LITERY_DNI[n % 23]


def dni(rng) -> str:
    n = rng.randint(1_000_000, 79_999_999)
    return f"{n:08d}{letra_dni(n)}"


def nie(rng) -> str:
    pref, n = rng.choice((("X", rng.randint(1_000_000, 4_999_999)), ("Y", rng.randint(1, 7_000_000)),
                          ("Z", rng.randint(1, 1_500_000))))
    return f"{pref}{n:07d}{letra_dni(int(str('XYZ'.index(pref)) + f'{n:07d}'))}"


def nuss(rng) -> str:
    prow, nr = rng.randint(1, 52), rng.randint(10_000_000, 99_999_999)
    return f"{prow:02d}/{nr:08d}/{int(f'{prow:02d}{nr:08d}') % 97:02d}"


def cif(rng, forma: str) -> str:
    litera = _CIF_FORMY.get(forma, "B")
    d = f"{rng.randint(1, 53):02d}{cyfry(rng, 5)}"
    suma = sum(int(c) for c in d[1::2])  # pozycje 2, 4, 6
    for c in d[0::2]:  # pozycje 1, 3, 5, 7 – podwojone, suma cyfr
        x = int(c) * 2
        suma += x // 10 + x % 10
    return f"{litera}{d}{(10 - suma % 10) % 10}"


def _dc(cyfry_: str) -> int:
    k = 11 - sum(int(c) * w for c, w in zip(cyfry_, _PESOS_DC)) % 11
    return {11: 0, 10: 1}.get(k, k)


class GeneratorES(BazowyGenerator):
    kraje = ("ES",)

    def __init__(self, jezyk, ziarno=0):
        super().__init__(jezyk, ziarno)
        #: prowincja dokumentu (kod): adresy, sądy i rejestr go preferują (ustawia `losuj_stan_dok`)
        self.prov_dok: str | None = None
        #: miasto ostatnio wylosowanego sądu (do gniazda `{sad.miasto}`); None dla sądów bez miasta w nazwie
        self.miasto_sadu: str | None = None
        self._prov_adresu: str | None = None
        self._rodzaj_firmy = "firma"

    def _imie_nazwisko(self, plec, kraj):
        imie = wagowo(self.rng, self._s("imiona_m" if plec == "M" else "imiona_k"))
        n1 = wagowo(self.rng, self._s("nazwiska"))
        n2 = wagowo(self.rng, self._s("nazwiska"))
        return imie, f"{n1} {n2}"

    def _ids_osoby(self, kraj, plec, data_ur, nazwisko):
        glowny = {"NIE": nie(self.rng)} if self.rng.random() < 0.12 else {"DNI": dni(self.rng)}
        return {**glowny, "NUSS": nuss(self.rng), "COLEGIADO": self.colegiado()}

    def colegiado(self):
        """Número de colegiado lekarza (Organización Médica Colegial): 9 cyfr, pierwsze dwie – kod prowincji 01–52."""
        return f"{self.rng.randint(1, 52):02d}{cyfry(self.rng, 7)}"

    def _formy(self, kraj):
        """Spółka z kapitałem w udziałach („spolka”) – zawsze S.L.; kancelaria – S.L.P.; placówka medyczna – S.L./S.A."""
        if self._rodzaj_firmy == "spolka":
            return ("S.L.",)
        if self._rodzaj_firmy == "kancelaria":
            return ("S.L.P.",)
        if self._rodzaj_firmy == "placowka":
            return ("S.L.",) * 2 + ("S.A.",)
        return ("S.L.",) * 8 + ("S.A.",) * 2 + ("S.L.U.",)    # formy z wpisem do Registro Mercantil

    def firma(self, kraj=None, rodzaj="firma"):
        """Jak bazowa, ale forma prawna zależy od rodzaju (kancelaria S.L.P., spółka S.L.) a numer hoja registral
        (kategoria NR_REJESTRU) pochodzi z prowincji adresu spółki (Registro Mercantil właściwy dla siedziby)."""
        self._rodzaj_firmy = rodzaj
        try:
            f = super().firma(kraj, rodzaj)
        finally:
            self._rodzaj_firmy = "firma"
        prow = f.adres.kod[:2]
        hoja = f"{PROVINCIAS[prow][2]}-{self.rng.randint(10_000, 999_999)}"
        email = f.email
        if rodzaj in ("kancelaria", "placowka"):       # domena e-mail zgodna z nazwą (a nie z samym rdzeniem)
            email = self._email_firmy(self._slug_firmy(f.nazwa.removesuffix(f", {f.forma}")))
        return dataclasses.replace(f, email=email, rejestry={**f.rejestry, "COMPANY_NO": hoja})

    def _nazwa_firmy(self, rdzen, forma, rodzaj):
        r = self.rng
        if rodzaj == "kancelaria":
            n1, n2 = wagowo(r, self._s("nazwiska")).split()[0], wagowo(r, self._s("nazwiska")).split()[0]
            return f"{r.choice(_DOBRA_FORMA_KANC).format(n1=n1, n2=n2, rdzen=rdzen)}, {forma}", forma
        if rodzaj == "placowka":
            return f"{r.choice(_TIPOS_MED)} {r.choice(_RDZENIE_MED)}, {forma}", forma
        return f"{rdzen}, {forma}", forma

    def _email_firmy(self, slug):
        return self.rng.choice((f"info@{slug}.test", f"contacto@{slug}.example.com", f"administracion@{slug}.example.org",
                                f"secretaria@{slug}.example.net", f"despacho@{slug}.test"))

    def _ids_firmy(self, kraj, forma):
        c = cif(self.rng, forma)
        return {"CIF": c, "VAT": "ES" + c}

    def _kandydat_telefonu(self, kraj):
        # brak oficjalnej puli fikcyjnej (CNMC): numer krajowy 000 + 6 cyfr – prefiks 000 nie istnieje w planie numeracji
        return f"+34000{cyfry(self.rng, 6)}"

    def _formatuj_telefon(self, e164, fmt, kraj):
        d = e164[3:]            # 9 cyfr: 000 123 456 (krajowo), +34 000 12 34 56 (międzynarodowo)
        return {"krajowy": f"{d[:3]} {d[3:6]} {d[6:]}", "miedzynarodowy": f"+34 {d[:3]} {d[3:5]} {d[5:7]} {d[7:]}",
                "e164": e164}[fmt]

    def telefon(self, kraj=None):
        try:
            return super().telefon(kraj)
        finally:
            self._prov_adresu = None       # prowincja ostatniego adresu dotyczy tylko następującego po nim telefonu

    def _bban(self, kraj):
        ent, ofi, cuenta = self.rng.choice(_ENTIDADES), cyfry(self.rng, 4), cyfry(self.rng, 10)
        return f"{ent}{ofi}{_dc('00' + ent + ofi)}{_dc(cuenta)}{cuenta}"

    def losuj_stan_dok(self):
        """Prowincja dokumentu (wg wag słownika miejscowości): adresy, sąd i rejestr leżą zwykle w niej."""
        self.prov_dok = wagowo(self.rng, self._s("miejscowosci")).partition("|")[2]
        self._prov_adresu = None

    def miasta_prowincji(self, prow: str) -> tuple[str, ...]:
        """Miejscowości słownika leżące w prowincji `prow` (kod); stolica pierwsza, jeśli jest w słowniku."""
        miasta = tuple(m.partition("|")[0] for m in self._s("miejscowosci") if m.partition("|")[2] == prow)
        stolica = PROVINCIAS[prow][1]
        return tuple(sorted(miasta, key=lambda m: m != stolica))

    def adres(self, kraj=None):
        r = self.rng
        miasta = self._s("miejscowosci")
        if self.prov_dok and r.random() < 0.85:      # adresy dokumentu zwykle w jednej prowincji
            miasta = tuple(m for m in miasta if m.partition("|")[2] == self.prov_dok) or miasta
        miasto, _, prow = wagowo(r, miasta).partition("|")
        self._prov_adresu = prow
        numer = str(r.randint(1, 200))
        if r.random() < 0.6:
            numer += f", {r.randint(1, 9)}º {r.choice('ABCD')}"
        kod = f"{prow}{r.randint(1, 999):03d}" if prow else cyfry(r, 5)
        return Adres(wagowo(r, self._s("ulice")), numer, kod, miasto, "ES")

    def _kwota_txt(self, calk, grosze, kraj):
        s = f"{calk:,}".replace(",", ".")
        znak = "€" if (self.styl["waluta"] == 0 if self.styl else self.rng.random() < 0.7) else "EUR"
        return f"{s},{grosze:02d} {znak}"

    def _data_txt(self, d, kraj):
        slownie = f"{d.day} de {MIESIACE['es'][d.month - 1]} de {d.year}"
        if self.styl:       # styl stały w obrębie dokumentu: 0 – data słownie, 1 – zapis liczbowy dd/mm/rrrr
            return slownie if self.styl["data"] == 0 else f"{d:%d/%m/%Y}"
        return self.rng.choice((slownie, f"{d:%d/%m/%Y}", slownie, f"{d:%d-%m-%Y}"))

    def sygnatura(self, kraj=None, rodzaj=None, rok=None):
        """Sygnatura sprawy. `rodzaj`: `ordinario` („Procedimiento Ordinario”), `verbal` („Juicio Verbal”), `apelacion`
        („Rollo de Apelación”, Audiencia Provincial); None – dowolne postępowanie I instancji. `rok` – rok wpływu."""
        if rodzaj is not None and rodzaj not in _RODZAJE_SYGN:
            raise ValueError(f"rodzaj sygnatury {rodzaj!r} nie istnieje dla ES: {_RODZAJE_SYGN}")
        r = self.rng
        nazwa = {"ordinario": "Procedimiento Ordinario", "verbal": "Juicio Verbal",
                 "apelacion": "Rollo de Apelación"}.get(rodzaj) or r.choice(_PROC_DODATKOWE)
        return f"{nazwa} n.º {r.randint(1, 1999)}/{rok or r.randint(2018, 2026)}"

    def sygnatura_cytatu(self, kraj=None, data=None, przedmiot=""):
        """Oznaczenie cytowanego wyroku Tribunal Supremo (zwykły tekst): „STS 345/2012, de 12 de marzo (ECLI:…)”;
        z `data` – orzeczenie z tego dnia (rok i data w oznaczeniu zgodne z nią)."""
        r = self.rng
        if data is None:
            rok = r.randint(2001, 2018)
            data = dt.date(rok, 1, 1) + dt.timedelta(days=r.randint(0, 364))
        rok = data.year
        return (f"STS {r.randint(1, 999)}/{rok}, de {data.day} de {MIESIACE['es'][data.month - 1]} "
                f"(ECLI:ES:TS:{rok}:{r.randint(100, 9999)})")

    def sad(self, kraj=None, poziom=None):
        """Nazwa sądu. `poziom`: `primera` (Juzgado de Primera Instancia [e Instrucción] w prowincji dokumentu) albo
        `apelacion` (Audiencia Provincial, sección); None – dowolny (także Tribunal Supremo i in.)."""
        r = self.rng
        if poziom is None:
            self.miasto_sadu = None
            if r.random() < 0.3:
                return r.choice(_STALE)
            ciudad = wagowo(r, self._s("miejscowosci")).split("|")[0]
            self.miasto_sadu = ciudad
            return f"{r.choice(_TIPOS)} n.º {r.randint(1, 30)} de {ciudad}"
        if poziom not in _POZIOMY:
            raise ValueError(f"poziom sądu {poziom!r} nie istnieje dla ES: {_POZIOMY}")
        prow = self.prov_dok or wagowo(r, self._s("miejscowosci")).partition("|")[2]
        nazwa_prow, stolica, _ = PROVINCIAS[prow]
        if poziom == "apelacion":
            self.miasto_sadu = stolica
            return f"Audiencia Provincial de {nazwa_prow}, Sección {r.randint(1, _SECCIONES.get(prow, 4))}.ª"
        miasta = self.miasta_prowincji(prow)
        ciudad = stolica if stolica in miasta and (r.random() < 0.7 or len(miasta) == 1) else r.choice(miasta)
        self.miasto_sadu = ciudad
        if ciudad == stolica:
            return f"Juzgado de Primera Instancia n.º {r.randint(1, _JUZGADOS.get(prow, 6))} de {ciudad}"
        return f"Juzgado de Primera Instancia e Instrucción n.º {r.randint(1, 5)} de {ciudad}"

    def nazwa_rejestru(self, adres) -> str:
        """Registro Mercantil właściwy dla siedziby (prowincja z kodu pocztowego adresu)."""
        return f"Registro Mercantil de {PROVINCIAS[adres.kod[:2]][0]}"

    def tablica(self, kraj=None):
        return f"{cyfry(self.rng, 4)} {''.join(self.rng.choice(SPOLGLOSKI_ES) for _ in range(3))}"
