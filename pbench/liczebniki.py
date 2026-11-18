"""Liczebniki słownie w pięciu językach (PL, EN, DE, ES, FR): liczby, kwoty i daty (przypadek `liczby_slownie`, spec §11).

Własna implementacja bez zależności (niezależność pomiaru). Zakres: liczby 0–999 999 999. Funkcje:

* `liczba(n, jezyk)` – liczebnik główny („dwa tysiące pięćset”, „two thousand five hundred”, „zweitausendfünfhundert”,
  „dos mil quinientos”, „deux mille cinq cents”); w DE i ES forma „ein/un” przed rzeczownikiem (euro) – `rodzaj`;
* `kwota(grosze, jezyk, waluta)` – „dwa tysiące pięćset złotych i pięćdziesiąt groszy” (odmiana złoty/złote/złotych,
  grosz/grosze/groszy wg reguł polskich; EN: pounds/pence albo dollars/cents; DE/ES/FR: euro/Cent, euros/céntimos, euros/centimes);
* `data(d, jezyk)` – data słownie: PL „dwudziestego trzeciego marca tysiąc dziewięćset osiemdziesiątego piątego roku”
  (odmiana porządkowych w dopełniaczu), EN „the twenty-third of March nineteen eighty-five”, DE „am dreiundzwanzigsten
  März neunzehnhundertfünfundachtzig”, ES „veintitrés de marzo de mil novecientos ochenta y cinco”, FR „le vingt-trois
  mars mille neuf cent quatre-vingt-cinq”;
* `cyfry_slownie(cyfry, jezyk)` – ciąg cyfr (PESEL) czytany cyfra po cyfrze („osiem pięć zero trzy…”).
"""
from __future__ import annotations

import datetime as dt

JEZYKI = ("pl", "en", "de", "es", "fr")
MAX = 999_999_999

# ----------------------------------------------------------------------------- PL
_PL_JEDNOSCI = ("zero", "jeden", "dwa", "trzy", "cztery", "pięć", "sześć", "siedem", "osiem", "dziewięć", "dziesięć",
                "jedenaście", "dwanaście", "trzynaście", "czternaście", "piętnaście", "szesnaście", "siedemnaście",
                "osiemnaście", "dziewiętnaście")
_PL_DZIESIATKI = ("", "", "dwadzieścia", "trzydzieści", "czterdzieści", "pięćdziesiąt", "sześćdziesiąt",
                  "siedemdziesiąt", "osiemdziesiąt", "dziewięćdziesiąt")
_PL_SETKI = ("", "sto", "dwieście", "trzysta", "czterysta", "pięćset", "sześćset", "siedemset", "osiemset", "dziewięćset")
_PL_MIESIACE_DOP = ("stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września",
                    "października", "listopada", "grudnia")
# porządkowe w dopełniaczu (rodzaj męski): 1–19, dziesiątki i setki
_PL_POR_JEDN = ("", "pierwszego", "drugiego", "trzeciego", "czwartego", "piątego", "szóstego", "siódmego", "ósmego",
                "dziewiątego", "dziesiątego", "jedenastego", "dwunastego", "trzynastego", "czternastego", "piętnastego",
                "szesnastego", "siedemnastego", "osiemnastego", "dziewiętnastego")
_PL_POR_DZIES = ("", "", "dwudziestego", "trzydziestego", "czterdziestego", "pięćdziesiątego", "sześćdziesiątego",
                 "siedemdziesiątego", "osiemdziesiątego", "dziewięćdziesiątego")
_PL_POR_SETKI = ("", "setnego", "dwusetnego", "trzechsetnego", "czterechsetnego", "pięćsetnego", "sześćsetnego",
                 "siedemsetnego", "osiemsetnego", "dziewięćsetnego")


def _pl_forma(n: int, f1: str, f24: str, f5: str) -> str:
    """Forma rzeczownika po liczebniku: 1 – f1; kończące się na 2–4 (poza 12–14) – f24; reszta – f5."""
    if n == 1:
        return f1
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return f24
    return f5


def _pl_do_999(n: int) -> list[str]:
    s, r = divmod(n, 100)
    wynik = [_PL_SETKI[s]] if s else []
    if r < 20:
        if r:
            wynik.append(_PL_JEDNOSCI[r])
    else:
        wynik.append(_PL_DZIESIATKI[r // 10])
        if r % 10:
            wynik.append(_PL_JEDNOSCI[r % 10])
    return wynik


def _pl(n: int) -> str:
    if n == 0:
        return "zero"
    czesci: list[str] = []
    mln, reszta = divmod(n, 1_000_000)
    tys, jedn = divmod(reszta, 1000)
    if mln:
        czesci += ([] if mln == 1 else _pl_do_999(mln)) + [_pl_forma(mln, "milion", "miliony", "milionów")]
    if tys:
        czesci += ([] if tys == 1 else _pl_do_999(tys)) + [_pl_forma(tys, "tysiąc", "tysiące", "tysięcy")]
    if jedn:
        czesci += _pl_do_999(jedn)
    return " ".join(czesci)


def porzadkowa_pl_dop(n: int) -> str:
    """Liczebnik porządkowy w dopełniaczu, rodzaj męski (1–999 999): 23 -> „dwudziestego trzeciego”,
    1985 -> „tysiąc dziewięćset osiemdziesiątego piątego”, 2000 -> „dwutysięcznego”, 2005 -> „dwa tysiące piątego”."""
    if not 1 <= n <= 999_999:
        raise ValueError(f"porządkowa PL: liczba poza zakresem: {n}")
    tys, r = divmod(n, 1000)
    if r == 0:     # „dwutysięcznego”, „trzytysięcznego”… (okrągłe tysiące)
        if tys == 1:
            return "tysięcznego"
        return {2: "dwu", 3: "trzy", 4: "cztero", 5: "pięcio", 6: "sześcio", 7: "siedmio", 8: "ośmio",
                9: "dziewięcio"}[tys] + "tysięcznego"
    wstep = _pl(tys * 1000) + " " if tys else ""
    s, d = divmod(r, 100)
    if d == 0:
        return wstep + _PL_POR_SETKI[s]
    czesci = [_PL_SETKI[s]] if s else []
    if d < 20:
        czesci.append(_PL_POR_JEDN[d])
    else:
        czesci.append(_PL_POR_DZIES[d // 10])
        if d % 10:
            czesci.append(_PL_POR_JEDN[d % 10])
    return wstep + " ".join(czesci)


def _kwota_pl(zl: int, gr: int) -> str:
    return (f"{_pl(zl)} {_pl_forma(zl, 'złoty', 'złote', 'złotych')} i {_pl(gr)} "
            f"{_pl_forma(gr, 'grosz', 'grosze', 'groszy')}") if gr else f"{_pl(zl)} {_pl_forma(zl, 'złoty', 'złote', 'złotych')}"


# ----------------------------------------------------------------------------- EN
_EN_JEDN = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
            "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen")
_EN_DZIES = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")
_EN_POR = {"one": "first", "two": "second", "three": "third", "five": "fifth", "eight": "eighth", "nine": "ninth",
           "twelve": "twelfth"}
_EN_MIESIACE = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                "November", "December")


def _en_do_99(n: int) -> str:
    if n < 20:
        return _EN_JEDN[n]
    return _EN_DZIES[n // 10] + (f"-{_EN_JEDN[n % 10]}" if n % 10 else "")


def _en_do_999(n: int) -> str:
    s, r = divmod(n, 100)
    if not s:
        return _en_do_99(r)
    return f"{_EN_JEDN[s]} hundred" + (f" and {_en_do_99(r)}" if r else "")


def _en(n: int) -> str:
    if n == 0:
        return "zero"
    czesci: list[str] = []
    mln, reszta = divmod(n, 1_000_000)
    tys, jedn = divmod(reszta, 1000)
    if mln:
        czesci.append(f"{_en_do_999(mln)} million")
    if tys:
        czesci.append(f"{_en_do_999(tys)} thousand")
    if jedn:
        czesci.append(("and " if (mln or tys) and jedn < 100 else "") + _en_do_999(jedn))
    return " ".join(czesci)


def _en_porzadkowa(n: int) -> str:
    """Porządkowa 1–31: 23 -> „twenty-third”."""
    zwykla = _en_do_99(n)
    ostatnie = zwykla.split("-")[-1]
    if ostatnie in _EN_POR:
        inna = _EN_POR[ostatnie]
    elif ostatnie.endswith("y"):
        inna = ostatnie[:-1] + "ieth"
    else:
        inna = ostatnie + "th"
    return "-".join(zwykla.split("-")[:-1] + [inna])


def _en_rok(r: int) -> str:
    if 2000 <= r <= 2009:
        return "two thousand" + (f" and {_EN_JEDN[r - 2000]}" if r > 2000 else "")
    s, d = divmod(r, 100)
    if d == 0:
        return f"{_en_do_99(s)} hundred"
    return f"{_en_do_99(s)} {'oh-' + _EN_JEDN[d] if d < 10 else _en_do_99(d)}"


def _kwota_en(l: int, c: int, waluta: str) -> str:
    duza, mala = ("pound", "pence") if waluta == "GBP" else ("dollar", "cent")
    wynik = f"{_en(l)} {duza}{'' if l == 1 else 's'}"
    if c:
        wynik += f" and {_en(c)} {mala if waluta == 'GBP' else (mala if c == 1 else mala + 's')}"
        if waluta == "GBP" and c == 1:
            wynik = wynik.replace("one pence", "one penny")
    return wynik


# ----------------------------------------------------------------------------- DE
_DE_JEDN = ("null", "ein", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn", "elf", "zwölf",
            "dreizehn", "vierzehn", "fünfzehn", "sechzehn", "siebzehn", "achtzehn", "neunzehn")
_DE_DZIES = ("", "", "zwanzig", "dreißig", "vierzig", "fünfzig", "sechzig", "siebzig", "achtzig", "neunzig")
_DE_MIESIACE = ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
                "November", "Dezember")


def _de_do_99(n: int, koncowka_eins: str = "ein") -> str:
    if n < 20:
        return koncowka_eins if n == 1 else _DE_JEDN[n]
    j = n % 10
    return (f"{'ein' if j == 1 else _DE_JEDN[j]}und" if j else "") + _DE_DZIES[n // 10]


def _de_do_999(n: int, eins: str = "ein") -> str:
    s, r = divmod(n, 100)
    wynik = f"{_DE_JEDN[s]}hundert" if s else ""
    return wynik + (_de_do_99(r, eins) if r else "")


def _de(n: int, eins: str = "ein") -> str:
    """Liczebnik DE (jedno słowo poniżej miliona); `eins` = „ein” przed rzeczownikiem, „eins” samodzielnie."""
    if n == 0:
        return "null"
    wynik = ""
    mln, reszta = divmod(n, 1_000_000)
    tys, jedn = divmod(reszta, 1000)
    if mln:
        wynik += ("eine Million " if mln == 1 else f"{_de_do_999(mln)} Millionen ")
    if tys:
        wynik += ("eintausend" if tys == 1 else f"{_de_do_999(tys)}tausend")
    if jedn:
        wynik += _de_do_999(jedn, eins)
    return wynik.strip()


def _de_porzadkowa_en(n: int) -> str:
    """Porządkowa 1–31 w bierniku po rodzajniku męskim („am dreiundzwanzigsten”)."""
    wyjatki = {1: "ersten", 3: "dritten", 7: "siebten", 8: "achten"}
    if n in wyjatki:
        return wyjatki[n]
    return _de_do_99(n) + ("ten" if n < 20 else "sten")


def _de_rok(r: int) -> str:
    if r >= 2000:
        return _de(r, "eins")
    return f"{_de_do_99(r // 100)}hundert" + (_de_do_99(r % 100, "eins") if r % 100 else "")


# ----------------------------------------------------------------------------- ES
_ES_JEDN = ("cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "once", "doce",
            "trece", "catorce", "quince", "dieciséis", "diecisiete", "dieciocho", "diecinueve", "veinte", "veintiuno",
            "veintidós", "veintitrés", "veinticuatro", "veinticinco", "veintiséis", "veintisiete", "veintiocho",
            "veintinueve")
_ES_DZIES = ("", "", "", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa")
_ES_SETKI = ("", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos", "seiscientos", "setecientos",
             "ochocientos", "novecientos")
_ES_MIESIACE = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
                "noviembre", "diciembre")


def _es_do_99(n: int, uno: str = "uno") -> str:
    if n < 30:
        return uno if n == 1 else ("veintiún" if n == 21 and uno == "un" else _ES_JEDN[n])
    j = n % 10
    return _ES_DZIES[n // 10] + (f" y {uno if j == 1 else _ES_JEDN[j]}" if j else "")


def _es_do_999(n: int, uno: str = "uno") -> str:
    s, r = divmod(n, 100)
    if n == 100:
        return "cien"
    czesci = [_ES_SETKI[s]] if s else []
    if r:
        czesci.append(_es_do_99(r, uno))
    return " ".join(czesci)


def _es(n: int, uno: str = "uno") -> str:
    """Liczebnik ES; `uno` = „un” przed rzeczownikiem rodzaju męskiego (euro), „uno” samodzielnie."""
    if n == 0:
        return "cero"
    czesci: list[str] = []
    mln, reszta = divmod(n, 1_000_000)
    tys, jedn = divmod(reszta, 1000)
    if mln:
        czesci.append("un millón" if mln == 1 else f"{_es_do_999(mln, 'un')} millones")
    if tys:
        czesci.append("mil" if tys == 1 else f"{_es_do_999(tys, 'un')} mil")
    if jedn:
        czesci.append(_es_do_999(jedn, uno))
    return " ".join(czesci)


# ----------------------------------------------------------------------------- FR
_FR_JEDN = ("zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix", "onze", "douze",
            "treize", "quatorze", "quinze", "seize", "dix-sept", "dix-huit", "dix-neuf")
_FR_DZIES = ("", "", "vingt", "trente", "quarante", "cinquante", "soixante")
_FR_MIESIACE = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
                "novembre", "décembre")


def _fr_do_99(n: int) -> str:
    if n < 20:
        return _FR_JEDN[n]
    d, j = divmod(n, 10)
    if d in (2, 3, 4, 5, 6):
        if j == 0:
            return _FR_DZIES[d]
        return f"{_FR_DZIES[d]} et un" if j == 1 else f"{_FR_DZIES[d]}-{_FR_JEDN[j]}"
    if d == 7:    # 70–79: soixante-dix…, 71 = soixante et onze
        return "soixante et onze" if j == 1 else f"soixante-{_FR_JEDN[10 + j]}"
    if j == 0 and d == 8:
        return "quatre-vingts"
    return f"quatre-vingt-{_FR_JEDN[(n - 80)]}" if d == 8 else f"quatre-vingt-{_FR_JEDN[10 + j]}"


def _fr_do_999(n: int, koncowe: bool = True) -> str:
    """`koncowe` – czy liczba stoi na końcu (decyduje o „s” w „cents” i „quatre-vingts”)."""
    s, r = divmod(n, 100)
    czesci: list[str] = []
    if s:
        if s == 1:
            czesci.append("cent")
        else:
            czesci.append(f"{_FR_JEDN[s]} cent" + ("s" if r == 0 and koncowe else ""))
    if r:
        czesci.append(_fr_do_99(r))
    tekst = " ".join(czesci)
    if not koncowe and tekst.endswith("quatre-vingts"):
        tekst = tekst[:-1]
    return tekst


def _fr(n: int) -> str:
    if n == 0:
        return "zéro"
    czesci: list[str] = []
    mln, reszta = divmod(n, 1_000_000)
    tys, jedn = divmod(reszta, 1000)
    if mln:
        czesci.append(f"{_fr_do_999(mln)} million{'' if mln == 1 else 's'}")
    if tys:
        czesci.append("mille" if tys == 1 else f"{_fr_do_999(tys, False)} mille")
    if jedn:
        czesci.append(_fr_do_999(jedn))
    return " ".join(czesci)


# ----------------------------------------------------------------------------- API
def liczba(n: int, jezyk: str, przed_rzeczownikiem: bool = False) -> str:
    """Liczebnik główny słownie. `przed_rzeczownikiem`: DE „ein” zamiast „eins”, ES „un” zamiast „uno” (np. „un euro”)."""
    if not 0 <= n <= MAX:
        raise ValueError(f"liczba poza zakresem 0–{MAX}: {n}")
    if jezyk == "pl":
        return _pl(n)
    if jezyk == "en":
        return _en(n)
    if jezyk == "de":
        return _de(n, "ein" if przed_rzeczownikiem else "eins")
    if jezyk == "es":
        return _es(n, "un" if przed_rzeczownikiem else "uno")
    if jezyk == "fr":
        return _fr(n)
    raise ValueError(f"nieobsługiwany język: {jezyk!r}")


def cyfry_slownie(cyfry: str, jezyk: str) -> str:
    """Ciąg cyfr czytany cyfra po cyfrze, np. PESEL „85032312345” -> „osiem pięć zero trzy dwa trzy jeden dwa trzy cztery pięć”."""
    return " ".join(liczba(int(c), jezyk) for c in cyfry)


def kwota(grosze: int, jezyk: str, waluta: str | None = None) -> str:
    """Kwota słownie (`grosze` – całość w groszach/centach). Waluty: PL – złoty, EN – `GBP` (domyślnie) albo `USD`,
    DE/ES/FR – euro."""
    l, c = divmod(grosze, 100)
    if jezyk == "pl":
        return _kwota_pl(l, c)
    if jezyk == "en":
        return _kwota_en(l, c, waluta or "GBP")
    if jezyk == "de":
        return f"{liczba(l, 'de', True)} Euro" + (f" und {liczba(c, 'de', True)} Cent" if c else "")
    if jezyk == "es":
        return (f"{liczba(l, 'es', True)} euro{'' if l == 1 else 's'}"
                + (f" con {liczba(c, 'es', True)} céntimo{'' if c == 1 else 's'}" if c else ""))
    if jezyk == "fr":
        return (f"{liczba(l, 'fr')} euro{'' if l <= 1 else 's'}"
                + (f" et {liczba(c, 'fr')} centime{'' if c <= 1 else 's'}" if c else ""))
    raise ValueError(f"nieobsługiwany język: {jezyk!r}")


def data(d: dt.date, jezyk: str) -> str:
    """Data słownie w formie używanej w pismach (zob. docstring modułu)."""
    if jezyk == "pl":
        return (f"{porzadkowa_pl_dop(d.day)} {_PL_MIESIACE_DOP[d.month - 1]} {porzadkowa_pl_dop(d.year)} roku")
    if jezyk == "en":
        return f"the {_en_porzadkowa(d.day)} of {_EN_MIESIACE[d.month - 1]} {_en_rok(d.year)}"
    if jezyk == "de":
        return f"am {_de_porzadkowa_en(d.day)} {_DE_MIESIACE[d.month - 1]} {_de_rok(d.year)}"
    if jezyk == "es":
        dzien = "primero" if d.day == 1 else _es_do_99(d.day)
        return f"{dzien} de {_ES_MIESIACE[d.month - 1]} de {_es(d.year)}"
    if jezyk == "fr":
        dzien = "premier" if d.day == 1 else _fr_do_99(d.day)
        rok = _fr(d.year) if d.year >= 2000 else f"mille {_fr_do_999(d.year - 1000)}"
        return f"le {dzien} {_FR_MIESIACE[d.month - 1]} {rok}"
    raise ValueError(f"nieobsługiwany język: {jezyk!r}")
