"""Generator wartości syntetycznych dla Polski (PESEL, NIP, REGON, KRS, dowód, paszport, KW, IBAN PL)."""
from __future__ import annotations

import datetime as dt

from .wspolne import ZGODNA_PLEC, Adres, BazowyGenerator, cyfry, cyfry_kontrolne_iban, wagowo

_ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII")
_KW_ZNAKI = {str(i): i for i in range(10)} | {c: n for n, c in enumerate("XABCDEFGHIJKLMNOPRSTUWYZ", start=10)}
# Kody wydziałów ksiąg wieczystych: załącznik nr 1 do rozp. MS (t.j. Dz.U. 2024 poz. 1583) – LU1S i ZG1E zamiast nieistniejących LU1L, ZG1Z.
_KW_SADY = ("WA1M", "WA2M", "WA3M", "WA4M", "WA5M", "WA1P", "KR1P", "KR1K", "KR2K", "PO1P", "PO1S", "GD1G", "GD1Y",
            "WR1K", "WR1L", "LU1I", "LU1S", "BI1B", "SZ1S", "KA1K", "KA1T", "LD1M", "LD1P", "CZ1C", "OP1O", "RZ1R",
            "TB1T", "BY1B", "TO1T", "OL1O", "KI1K", "ZG1E", "SL1S", "PL1P", "EL1E", "SW1S", "SR1S", "KN1N")
_BANKI = ("102", "105", "109", "114", "116", "124", "154", "160", "175", "187", "194", "203", "212", "213", "215",
          "249", "106", "113")
# Prefiksy numerów rejestracyjnych (wyróżniki powiatów): podzbiór załącznika nr 13 do rozp. MI z 8.11.2024 (Dz.U. 2024
# poz. 1709); prefiksów spoza załącznika (LL, KA, OL, ZG, BY, LD) nie używamy.
_TABLICA_PREFIKSY = ("WA", "WX", "WB", "WE", "WU", "WW", "WY", "WF", "KR", "KK", "KT", "PO", "PZ", "PY", "GD", "GA",
                     "GS", "SZ", "SG", "WR", "WD", "LU", "BI", "SK", "TK", "RZ", "OP", "CT", "DW", "EL", "FZ", "KN",
                     "RK", "NOL", "TSA", "WPL", "WSK", "GWE", "PGN")
# Litery wyróżnika pojazdu: § 31 ust. 1 tego rozporządzenia wyłącza B, D, I, O i Z.
_TABLICA_LITERY = "ACEFGHJKLMNPRSTUVWXY"
_SADY = (
    "Sąd Rejonowy dla Warszawy-Mokotowa w Warszawie", "Sąd Rejonowy dla Warszawy-Śródmieścia w Warszawie",
    "Sąd Rejonowy dla m.st. Warszawy w Warszawie", "Sąd Okręgowy w Warszawie", "Sąd Apelacyjny w Warszawie",
    "Sąd Rejonowy dla Krakowa-Śródmieścia w Krakowie", "Sąd Okręgowy w Krakowie", "Sąd Apelacyjny w Krakowie",
    "Sąd Rejonowy Poznań-Stare Miasto w Poznaniu", "Sąd Okręgowy w Poznaniu", "Sąd Rejonowy dla Wrocławia-Śródmieścia we Wrocławiu",
    "Sąd Okręgowy we Wrocławiu", "Sąd Apelacyjny we Wrocławiu", "Sąd Rejonowy Gdańsk-Północ w Gdańsku",
    "Sąd Okręgowy w Gdańsku", "Sąd Rejonowy Szczecin-Prawobrzeże i Zachód w Szczecinie", "Sąd Okręgowy w Szczecinie",
    "Sąd Rejonowy w Lublinie", "Sąd Okręgowy w Lublinie", "Sąd Rejonowy Katowice-Wschód w Katowicach",
    "Sąd Okręgowy w Katowicach", "Sąd Apelacyjny w Katowicach", "Sąd Rejonowy dla Łodzi-Śródmieścia w Łodzi",
    "Sąd Okręgowy w Łodzi", "Sąd Rejonowy w Bydgoszczy", "Sąd Okręgowy w Bydgoszczy", "Sąd Rejonowy w Białymstoku",
    "Sąd Okręgowy w Białymstoku", "Sąd Rejonowy w Rzeszowie", "Sąd Okręgowy w Rzeszowie", "Sąd Rejonowy w Kielcach",
    "Sąd Rejonowy w Opolu", "Sąd Okręgowy w Opolu", "Sąd Rejonowy w Toruniu", "Sąd Okręgowy w Toruniu",
    "Sąd Rejonowy w Olsztynie", "Sąd Okręgowy w Gliwicach", "Sąd Rejonowy w Radomiu", "Sąd Rejonowy w Płocku",
    "Sąd Najwyższy", "Wojewódzki Sąd Administracyjny w Warszawie", "Naczelny Sąd Administracyjny",
)


def _suma_wazona(tekst: str, wagi: tuple[int, ...]) -> int:
    return sum(int(c) * w for c, w in zip(tekst, wagi))


def pesel(rng, data_ur: dt.date, plec: str) -> str:
    mm = data_ur.month + {1800: 80, 1900: 0, 2000: 20}[data_ur.year // 100 * 100]
    baza = f"{data_ur.year % 100:02d}{mm:02d}{data_ur.day:02d}{cyfry(rng, 3)}{rng.choice('13579' if plec == 'M' else '02468')}"
    return baza + str((10 - _suma_wazona(baza, (1, 3, 7, 9, 1, 3, 7, 9, 1, 3)) % 10) % 10)


def nip(rng) -> str:
    while True:
        baza = f"{rng.randint(101, 998)}{cyfry(rng, 6)}"
        k = _suma_wazona(baza, (6, 5, 7, 2, 3, 4, 5, 6, 7)) % 11
        if k != 10:
            return baza + str(k)


def regon(rng) -> str:
    baza = f"{rng.randint(1, 49):02d}{cyfry(rng, 6)}"
    return baza + str(_suma_wazona(baza, (8, 9, 2, 3, 4, 5, 6, 7)) % 11 % 10)


def krs(rng) -> str:
    return f"{rng.randint(10_000, 1_100_000):010d}"


def dowod(rng) -> str:
    lit = "".join(rng.choice("ABCDEFGHIJKLMNOPRSTUVWXYZ") for _ in range(3))
    cyf = cyfry(rng, 5)
    pelny = [ord(c) - 55 for c in lit] + [int(c) for c in cyf]  # 3 litery + 5 cyfr (bez cyfry kontrolnej)
    waga = (7, 3, 1, 7, 3, 1, 7, 3)
    k = sum(a * b for a, b in zip(pelny, waga)) % 10
    return f"{lit}{k}{cyf}"


def paszport(rng) -> str:
    return "".join(rng.choice("ABCDEFGHIJKLMNOPRSTUVWXYZ") for _ in range(2)) + cyfry(rng, 7)


def pwz(rng) -> str:
    """Numer prawa wykonywania zawodu lekarza: 7 cyfr, pierwsza to kontrolna (suma cyfr 2–7 z wagami 1–6 mod 11) i nie jest
    zerem (NIL, „Zasady weryfikowania nr prawa wykonywania zawodu”, nil.org.pl/rejestry/centralny-rejestr-lekarzy)."""
    while True:
        reszta = cyfry(rng, 6)
        k = _suma_wazona(reszta, (1, 2, 3, 4, 5, 6)) % 11
        if k not in (0, 10):        # NIL: numer PWZ nie zaczyna się od 0 (a reszta 10 nie ma cyfry kontrolnej)
            return str(k) + reszta


def ksiega_wieczysta(rng) -> str:
    sad = rng.choice(_KW_SADY)
    nr = f"{rng.randint(1, 9_999_999):08d}"
    k = sum(_KW_ZNAKI[c] * w for c, w in zip(sad + nr, (1, 3, 7) * 4)) % 10
    return f"{sad}/{nr}/{k}"


def _kod_rozliczeniowy(rng) -> str:
    baza = f"{rng.choice(_BANKI)}{cyfry(rng, 4)}"
    return baza + str((10 - _suma_wazona(baza, (3, 9, 7, 1, 3, 9, 7)) % 10) % 10)


class GeneratorPL(BazowyGenerator):
    kraje = ("PL",)

    def _imie_nazwisko(self, plec, kraj):
        imie = wagowo(self.rng, self._s("imiona_m" if plec == "M" else "imiona_k"))
        nazwisko = wagowo(self.rng, self._s("nazwiska"))
        if plec == "K":
            for koniec, zenskie in (("dzki", "dzka"), ("ski", "ska"), ("cki", "cka"), ("ny", "na"), ("wy", "wa")):
                if nazwisko.endswith(koniec):
                    nazwisko = nazwisko[: -len(koniec)] + zenskie
                    break
        elif ZGODNA_PLEC.get():
            # warstwa trudna (J1, S5): żeńska forma ze słownika („Sadowska”) dla mężczyzny – forma męska
            for zenskie, koniec in (("dzka", "dzki"), ("ska", "ski"), ("cka", "cki")):
                if nazwisko.endswith(zenskie):
                    nazwisko = nazwisko[: -len(zenskie)] + koniec
                    break
        return imie, nazwisko

    def _ids_osoby(self, kraj, plec, data_ur, nazwisko):
        return {"PESEL": pesel(self.rng, data_ur, plec), "NIP": nip(self.rng), "DOWOD": dowod(self.rng),
                "PASZPORT": paszport(self.rng),
                "PWZ": pwz(self.rng)}

    def _formy(self, kraj):
        return ("sp. z o.o.",) * 6 + ("S.A.",) * 2 + ("sp.j.", "sp.k.", "sp. z o.o. sp.k.")

    def _ids_firmy(self, kraj, forma):
        n = nip(self.rng)
        return {"NIP": n, "REGON": regon(self.rng), "KRS": krs(self.rng), "VAT": "PL" + n}

    def ksiega_wieczysta(self) -> str:
        return ksiega_wieczysta(self.rng)

    def _kandydat_telefonu(self, kraj):
        # brak oficjalnej puli fikcyjnej (UKE): numer krajowy 000 + 6 cyfr – prefiks 000 nie istnieje w planie numeracji
        return f"+48000{cyfry(self.rng, 6)}"

    def _formatuj_telefon(self, e164, fmt, kraj):
        d = e164[3:]            # 9 cyfr: 000 123 456
        grupy = f"{d[:3]} {d[3:6]} {d[6:]}"
        return {"krajowy": grupy, "miedzynarodowy": f"+48 {grupy}", "e164": e164}[fmt]

    def _nazwa_firmy(self, rdzen, forma, rodzaj):
        r = self.rng
        if rodzaj == "kancelaria":
            nazwisko = wagowo(r, self._s("nazwiska"))
            wzor = r.randrange(3)
            if wzor == 0:
                return f"Kancelaria Radców Prawnych {nazwisko} i Wspólnicy sp.k.", "sp.k."
            if wzor == 1:
                return f"{nazwisko} & {wagowo(r, self._s('nazwiska'))} Kancelaria Prawna sp.k.", "sp.k."
            return f"Kancelaria Prawna {rdzen} sp. z o.o.", "sp. z o.o."
        if rodzaj == "placowka":
            forma = r.choice(("sp. z o.o.", "sp. z o.o.", "S.A."))
            wzor = r.choice(("Szpital Specjalistyczny {} {}", "{} Centrum Medyczne {}",
                             "Niepubliczny Zakład Opieki Zdrowotnej {} {}", "Szpital Powiatowy {} {}",
                             "Specjalistyczne Centrum Medyczne {} {}"))
            return wzor.format(rdzen, forma), forma
        return f"{rdzen} {forma}", forma

    def _bban(self, kraj):
        return _kod_rozliczeniowy(self.rng) + cyfry(self.rng, 16)

    def adres(self, kraj=None):
        r = self.rng
        miasto, _, prefiks = wagowo(r, self._s("miejscowosci")).partition("|")
        numer = str(r.randint(1, 150)) + (r.choice("ABC") if r.random() < 0.08 else "")
        if r.random() < 0.55:
            numer += f"/{r.randint(1, 120)}"
        kod = f"{prefiks or cyfry(r, 2)}-{cyfry(r, 3)}"
        return Adres(wagowo(r, self._s("ulice")), numer, kod, miasto, "PL")

    def _kwota_txt(self, calk, grosze, kraj):
        s = f"{calk:,}".replace(",", " ")
        return f"{s},{grosze:02d} {('zł', 'PLN')[self.styl.get('waluta', self.rng.randrange(2))]}"

    def _data_txt(self, d, kraj):
        m = ("stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września",
             "października", "listopada", "grudnia")[d.month - 1]
        # w polskim tekście zawsze z „r.” i bez zapisu ISO; jeden styl na dokument (`styl["data"]`)
        styl = self.styl.get("data", self.rng.randrange(2))
        return f"{d.day} {m} {d.year} r." if styl == 0 else f"{d:%d.%m.%Y} r."

    def sygnatura(self, kraj=None, rodzaj=None, rok=None):
        r = self.rng
        rodzaj = rodzaj or r.choice(("C", "C", "K", "GC", "Ca", "ACa", "Cps", "Nc", "Co", "Ns", "P", "U", "Ga", "Cz"))
        rok = r.randint(15, 26) if rok is None else rok % 100
        return f"{r.choice(_ROMAN)} {rodzaj} {r.randint(1, 9999)}/{rok:02d}"

    def sygnatura_cytatu(self, kraj=None, data=None, przedmiot=""):
        """Sygnatura cytowanego orzeczenia (zwykły tekst). Z `data` (data orzeczenia): rok sygnatury o 1–2 lata
        wcześniejszy niż rok orzeczenia (sprawa wpłynęła przed wyrokiem)."""
        if data is None:
            return self.sygnatura()
        rodzaj = self.rng.choice(("C", "Ca", "ACa", "CSK", "CSKP"))
        return self.sygnatura(rodzaj=rodzaj, rok=data.year - self.rng.randint(1, 2))

    def sad(self, kraj=None, poziom=None):
        if poziom is None:
            return self.rng.choice(_SADY)
        przedrostek = {"rejonowy": "Sąd Rejonowy", "okregowy": "Sąd Okręgowy"}[poziom]
        return self.rng.choice([s for s in _SADY if s.startswith(przedrostek)])

    def tablica(self, kraj=None):
        """Numer rejestracyjny wg § 30 ust. 2 pkt 1 rozp. MI (Dz.U. 2024 poz. 1709): wyróżnik powiatu 2-literowy + 5 cyfr
        / 4 cyfry i litera / cyfra, litera i 3 cyfry; 3-literowy + litera i 3 cyfry / 2 cyfry i 2 litery / cyfra, litera
        i 2 cyfry. Część cyfrowa nie jest zerowa (00001…), litery bez B, D, I, O, Z (§ 31 ust. 1)."""
        r = self.rng
        pref = r.choice(_TABLICA_PREFIKSY)
        L = lambda: r.choice(_TABLICA_LITERY)        # noqa: E731
        while True:
            if len(pref) == 2:
                suf = r.choice((lambda: cyfry(r, 5), lambda: cyfry(r, 4) + L(), lambda: f"{r.randint(1, 9)}{L()}{cyfry(r, 3)}"))()
            else:
                suf = r.choice((lambda: f"{L()}{cyfry(r, 3)}", lambda: f"{cyfry(r, 2)}{L()}{L()}",
                                lambda: f"{r.randint(1, 9)}{L()}{cyfry(r, 2)}"))()
            if any(c in "123456789" for c in suf if c.isdigit()):
                return f"{pref} {suf}"
