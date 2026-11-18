"""Tabele raportu (HTML): rankingi, składniki, rozbicia, szybkość, wrażliwość wag, tryby, aneks wariantów, wersje, odcisk, zakres, źródła prawne.

Każda tabela: `(r: Raport, …) -> str` (HTML do wstawienia przez `{{ tabela('nazwa', …) }}`); rejestr `TABELE_FUNKCJE` zasila `buduj.TABELE`.
Wartość nieliczona (None) to zawsze „n/d” – nigdy `nan`, `0` ani pusta komórka. Nazwy uczestników łamią się po myślniku (`<wbr>`),
tabele mają stałe szerokości kolumn (`<colgroup>`), więc nie wylewają się poza blok tekstu A4."""
from __future__ import annotations

import html as _html
import re
from typing import Callable

from raport.dane import (ND, TRYBY, Raport, Wiersz, etykieta_miejsca, kontrola_domen_wiersze, liczba, porownanie_trybow, prywatizer as _prywatizer, procent, przedzial, przedzial_procent, roznica, roznica_pp, sekundy as _sek, suma_bez_szybkosci, wagi_testow, wiersze_podsumowania, zakresy_przykladow,
                         wiersz as _wiersz_uczestnika)
from raport.zrodla import wczytaj_rejestr

TESTY_RANKINGU = {"tekst": ["T1", "T2", "T3", "T4", "T5", "T6"], "pliki": ["P1", "P2", "P3", "P4", "P5", "P6", "P7"]}
TEST_SZYBKOSCI = {"tekst": "T6", "pliki": "P7"}
NAZWY_TESTOW = {
    "T1": "dokumenty bez wycieku (ważone kategorią)", "T2": "wyciek ważony kategorią", "T3": "trudne przypadki", "T4": "najsłabszy język",
    "T5": "brak nadmiarowego maskowania", "T6": "szybkość",
    "P1": "pliki bez wycieku (ważone kategorią)", "P2": "wyciek ważony miejscem", "P3": "trudne przypadki plikowe", "P4": "integralność",
    "P5": "brak nadmiarowego maskowania", "P6": "pokrycie formatów", "P7": "szybkość",
}
ZESTAWY_WAG = {"rowne": "równe wagi testów", "prywatnosc": "nacisk na prywatność", "uzytecznosc": "nacisk na użyteczność"}
ZESTAWY_NAZWY = {"rowne": "równe", "prywatnosc": "prywatność", "uzytecznosc": "użyteczność"}
JEZYKI = ["pl", "en", "es", "de", "fr"]

# Opisy uczestników aneksu i ich odpowiedników samodzielnych (źródło: metodyka/uczestnicy.md, prerejestracja.md).
OPISY = {
    "privatizer-tekst": "Silnik Privatizera na tekście: model Legal Geek Privatizer (RC) + reguły z sumami kontrolnymi, pola, scalanie, lista wyjątków, rozchodzenie powtórzeń; tryb domyślny.",
    "privatizer-model": "Sam model Legal Geek Privatizer (RC), bez reguł i bez reszty potoku.",
    "privatizer-reguly": "Same reguły Privatizera, bez modelu.",
    "presidio-lgp": "Presidio jak w presidio-gliner, ale rozpoznawaczem NER jest model Legal Geek Privatizer (RC); bez potoku Privatizera.",
    "gliner-nvidia-pii": "Sam model GLiNER nvidia/gliner-PII.",
    "privatizer-tekst-gliner": "Potok Privatizera z modelem GLiNER nvidia/gliner-PII w miejsce modelu Legal Geek Privatizer (RC).",
    "openai-privacy-filter": "Sam model OpenAI Privacy Filter.",
    "privatizer-tekst-opf": "Potok Privatizera z modelem OpenAI Privacy Filter w miejsce modelu Legal Geek Privatizer (RC).",
    "privatizer-tekst-maks": "Potok privatizer-tekst w trybie „Maksymalna ochrona” (czułość modelu, kwoty pieniężne).",
    "privatizer-plik-maks": "Aplikacja plik → plik w trybie „Maksymalna ochrona”.",
}
APLIKACJA_VS_MODELE = ["privatizer-tekst", "presidio-lgp", "privatizer-model", "privatizer-reguly", "gliner-nvidia-pii", "privatizer-tekst-gliner",
                       "openai-privacy-filter", "privatizer-tekst-opf"]


# ---------------------------------------------------------------- budowa HTML

def _e(x) -> str:
    return _html.escape(str(x), quote=True)


def _nazwa(u: str, pogrub: bool = True) -> str:
    """Nazwa uczestnika z możliwością złamania po myślniku; Privatizer pogrubiony (wyróżnienie bez koloru)."""
    t = _e(u).replace("-", "-<wbr>")
    return f"<strong>{t}</strong>" if pogrub and _prywatizer(u) else t


def _kol(naglowek: str, szer: float, num: bool = False, obrot: bool = False) -> dict:
    return {"h": naglowek, "w": szer, "num": num, "obrot": obrot}


def _tabela(klasa: str, kolumny: list[dict], wiersze: list[list[str]], podpis: str = "", przypis: str = "", pusta: str = f"{ND} (brak danych)") -> str:
    """Tabela HTML: szerokości kolumn względne (suma = 100%); pusta lista wierszy → pojedynczy wiersz z komunikatem `pusta` (domyślnie „n/d”)."""
    razem = sum(k["w"] for k in kolumny) or 1
    cols = "".join(f'<col style="width:{k["w"] / razem * 100:.2f}%">' for k in kolumny)
    glowa = "".join(f'<th{_klasy(k)}>' + (f'<span>{k["h"]}</span>' if k["obrot"] else k["h"]) + "</th>" for k in kolumny)
    if wiersze:
        cialo = "".join("<tr>" + "".join(f'<td{" class=num" if k["num"] else ""}>{c or "–"}</td>' for k, c in zip(kolumny, w)) + "</tr>" for w in wiersze)
    else:
        cialo = f'<tr><td colspan="{len(kolumny)}">{pusta}</td></tr>'
    napis = f"<caption>{podpis}</caption>" if podpis else ""
    return (f'<table class="{klasa}">{napis}<colgroup>{cols}</colgroup><thead><tr>{glowa}</tr></thead><tbody>{cialo}</tbody></table>'
            + (f'<p class="przypis">{przypis}</p>' if przypis else ""))


def _klasy(k: dict) -> str:
    c = [x for x, flaga in (("num", k["num"]), ("obrot", k["obrot"])) if flaga]
    return f' class="{" ".join(c)}"' if c else ""


def _n(x, miejsca: int = 1) -> str:
    return liczba(x, miejsca)


def _p(x, miejsca: int = 0) -> str:
    return procent(x, miejsca)


# ---------------------------------------------------------------- rankingi i aneks

def _wiersze_rankingu(r: Raport, ranking: str) -> list[Wiersz]:
    return sorted(r.rankingi.get(ranking, []), key=lambda w: (w.miejsce is None, w.miejsce or 0, w.uczestnik))


def _uwagi(w: Wiersz, ranking: str) -> str:
    """Uwagi z danych: test nieliczony → powód (P5 – nie dotyczy wg prerejestracji, T6/P7 – brak pomiaru czasu); inaczej uwagi z agregacji."""
    uwagi = []
    for t in TESTY_RANKINGU[ranking]:
        if w.testy[t].pkt is not None:
            continue
        if t == "P5":
            uwagi.append("P5: nie dotyczy")
        elif t == TEST_SZYBKOSCI[ranking]:
            uwagi.append(f"{t}: nie mierzono (brak pomiaru czasu)")
        else:
            uwagi.append(f"{t}: {ND}")
    if not uwagi and w.uwagi:
        uwagi.append(w.uwagi)
    return "; ".join(uwagi)


def _miejsce(w: Wiersz, wiersze: list[Wiersz]) -> str:
    """Etykieta miejsca; dopisek „remis” w drugiej linii (kolumna jest wąska)."""
    return _e(etykieta_miejsca(w, wiersze)).replace(" (remis)", "<br><small>remis</small>")


def _komorka_sumy(w: Wiersz) -> str:
    return f"{_n(w.suma)}<br><small>{przedzial(w.suma_ci)}</small>"


def _komorka_wycieku(w: Wiersz) -> str:
    if w.z_wyciekiem is None:
        return ND
    udzial = f"<br><small>{_p(w.z_wyciekiem / w.dokumenty, 0)}</small>" if w.dokumenty else ""
    return f"{_n(w.z_wyciekiem, 0)}{udzial}"


def _komorka_bledow(w: Wiersz) -> str:
    return " / ".join(ND if x is None else _n(x, 0) for x in (w.bledy, w.odmowy, w.nieobslugiwane))


def _tabela_wynikow(r: Raport, ranking: str, wiersze: list[Wiersz], z_miejscem: bool, podpis: str) -> str:
    testy = TESTY_RANKINGU[ranking]
    wagi = wagi_testow()
    kolumny = ([_kol("m.", 10, num=True)] if z_miejscem else []) + [_kol("Uczestnik", 23)]
    kolumny += [_kol(f"{t}<br><small>/{wagi[t]}</small>", 10.5, num=True) for t in testy]
    kolumny += [_kol("Suma<br><small>[95% CI]</small>", 14, num=True), _kol("Dok. z<br>wyciekiem", 15.5, num=True),
                _kol("Błędy / odmowy / nieobsł.", 14, num=True), _kol("Uwagi", 16)]
    wszystkie = r.rankingi.get(ranking, [])
    tresc = []
    for w in wiersze:
        wiersz = ([_miejsce(w, wszystkie)] if z_miejscem else []) + [_nazwa(w.uczestnik)]
        wiersz += [_n(w.testy[t].pkt) for t in testy]
        wiersz += [_komorka_sumy(w), _komorka_wycieku(w), _komorka_bledow(w), _e(_uwagi(w, ranking))]
        tresc.append(wiersz)
    legenda = "; ".join(f"{t} – {NAZWY_TESTOW[t]}" for t in testy)
    przypis = (f"Punkty za testy (pod nazwą testu – maksimum). {_e(legenda)}. „Dok. z wyciekiem” – liczba dokumentów, z których wyciekła choć jedna "
               "wartość (w nawiasie – udział). „Błędy / odmowy / nieobsł.” – dokumenty z błędem, odmową i nieobsługiwane.")
    if any(w.testy["P5"].pkt is None for w in wiersze if "P5" in testy):
        przypis += " „P5: nie dotyczy” – test P5 nie dotyczy uczestnika wg prerejestracji."
    return _tabela("wyniki", kolumny, tresc, podpis, przypis)


def ranking(r: Raport, ranking: str = "tekst") -> str:
    """Ranking w kolejności miejsc (tryb domyślny Privatizera); remisy statystyczne z etykietą „min–max (remis)”; aneks osobno (`aneks_x1`)."""
    if ranking not in TESTY_RANKINGU:
        return _tabela("wyniki", [_kol("Ranking", 1)], [], "")
    return _tabela_wynikow(r, ranking, _wiersze_rankingu(r, ranking), True, "")


def podsumowanie(r: Raport) -> str:
    """Oba rankingi w skrócie: pięć pierwszych miejsc i każdy wiersz Privatizera spoza nich; punkty z przedziałem ufności i dokumenty z wyciekiem."""
    kolumny = [_kol("Ranking", 13), _kol("m.", 9, num=True), _kol("Uczestnik", 31), _kol("Suma<br><small>[95% CI]</small>", 17, num=True),
               _kol("Dok. z<br>wyciekiem", 14, num=True)]
    tresc = []
    for ranking, nazwa in (("tekst", "tekst"), ("pliki", "pliki")):
        wszystkie = r.rankingi.get(ranking, [])
        for w in wiersze_podsumowania(r, ranking):
            tresc.append([nazwa, _miejsce(w, wszystkie), _nazwa(w.uczestnik), _komorka_sumy(w), _komorka_wycieku(w)])
            nazwa = "&nbsp;"
    przypis = ("Tryb domyślny Privatizera. Pełne rankingi, składniki sum i uwagi do pojedynczych uczestników są w rozdziale „Wyniki”; "
               "„remis” oznacza przedziały ufności, które się nie rozdzielają.")
    return _tabela("wyniki", kolumny, tresc, "", przypis)


def aneks_x1(r: Raport, ranking: str = "tekst") -> str:
    """Uczestnicy aneksu (tryb „Maksymalna ochrona”, warianty krzyżowe, same reguły): poza rankingiem, od najwyższej sumy."""
    if ranking not in TESTY_RANKINGU:
        return _tabela("wyniki", [_kol("Ranking", 1)], [], "")
    wiersze = sorted(r.aneks.get(ranking, []), key=lambda w: (-(w.suma if w.suma is not None else -1), w.uczestnik))
    return _tabela_wynikow(r, ranking, wiersze, False, "")


# ---------------------------------------------------------------- rozbicia

_PER = {  # wymiar → (pole wartości, nagłówek wartości, kolumna liczn, nagłówek liczn)
    "jezyk": ("bez_wycieku_wazone", "Odsetek dokumentów bez wycieku (ważony kategorią)", "dokumenty", "Dok."),
    "format": ("bez_wycieku_wazone", "Odsetek dokumentów bez wycieku (ważony kategorią)", "dokumenty", "Dok."),
    "typ": ("bez_wycieku_wazone", "Odsetek dokumentów bez wycieku (ważony kategorią)", "dokumenty", "Dok."),
    "przypadek": ("bez_wycieku", "Odsetek dokumentów bez wycieku", "dokumenty", "Dok."),
    "kategoria": ("odsetek_wyciekow", "Odsetek wyciekłych wartości (mniej = lepiej)", "wartosci", "Wart."),
    "miejsce": ("odsetek_wyciekow", "Odsetek wyciekłych wartości (mniej = lepiej)", "wartosci", "Wart."),
}


def per(r: Raport, wymiar: str, ranking: str = "tekst") -> str:
    """Rozbicie rankingu (wiersze = wartości wymiaru, kolumny = uczestnicy w kolejności miejsc); nieliczone = „n/d”."""
    if wymiar not in _PER:
        return _tabela("per", [_kol("Wymiar", 1)], [], "")
    pole, opis, pole_n, naglowek_n = _PER[wymiar]
    uczestnicy = [w.uczestnik for w in _wiersze_rankingu(r, ranking)]
    dane = [x for x in r.per.get(wymiar, []) if x["ranking"] == ranking and x["uczestnik"] in uczestnicy]
    wartosci = {(x[wymiar], x["uczestnik"]): x.get(pole) for x in dane}
    liczn: dict[str, int] = {}
    nie_punktowane: set[str] = set()
    for x in dane:
        liczn[x[wymiar]] = max(liczn.get(x[wymiar], 0), x.get(pole_n) or 0)
        if x.get("punktowany") is False or str(x.get("punktowany")) == "False":
            nie_punktowane.add(x[wymiar])
    klucze = sorted(liczn, key=(lambda k: (JEZYKI.index(k) if k in JEZYKI else len(JEZYKI), k)) if wymiar == "jezyk" else str)
    uczestnicy = [u for u in uczestnicy if any((k, u) in wartosci for k in klucze)] or uczestnicy
    obrot = len(uczestnicy) > 5
    szer = 5.4 if obrot else 12
    kolumny = [_kol(wymiar.capitalize() if wymiar != "jezyk" else "Język", 22 if obrot else 20), _kol(naglowek_n, 7, num=True)]
    kolumny += [_kol(_nazwa(u), szer, num=True, obrot=obrot) for u in uczestnicy]
    tresc = []
    for k in klucze:
        etykieta = _e(k) + (" <small>(poza punktacją)</small>" if k in nie_punktowane else "")
        tresc.append([etykieta, _n(liczn[k], 0)] + [_p(wartosci.get((k, u))) for u in uczestnicy])
    return _tabela("per", kolumny, tresc, "", _e(opis) + ".")


# ---------------------------------------------------------------- szybkość i wrażliwość wag

def szybkosc(r: Raport, ranking: str = "tekst") -> str:
    """Czas na stronę (mediana, s) i punkty szybkości dla t_ref = 1,0 (jak w rankingu) oraz 0,5 i 2,0 (wrażliwość); brak pomiaru = „n/d”."""
    if ranking not in TESTY_RANKINGU:
        return _tabela("szybkosc", [_kol("Ranking", 1)], [], "")
    test = TEST_SZYBKOSCI[ranking]
    waga = wagi_testow()[test]
    czasy = {c["uczestnik"]: c for c in r.czas if c["ranking"] == ranking}
    kolumny = [_kol("Uczestnik", 28), _kol("Próbka (dok.)", 10, num=True), _kol("Awarie", 8, num=True), _kol("s / stronę", 11, num=True),
               _kol(f"{test} pkt<br><small>t_ref 1,0</small>", 13, num=True), _kol(f"{test} pkt<br><small>t_ref 0,5</small>", 13, num=True),
               _kol(f"{test} pkt<br><small>t_ref 2,0</small>", 13, num=True)]

    def pkt(c, pole):
        return None if c is None or c.get(pole) is None else c[pole] * waga

    tresc = []
    for w in _wiersze_rankingu(r, ranking):
        c = czasy.get(w.uczestnik)
        sek = None if c is None else c.get("s_na_strone")
        tresc.append([_nazwa(w.uczestnik), _n(None if c is None else c.get("dokumenty_proby"), 0), _n(None if c is None else c.get("awarie"), 0),
                      _sek(sek),
                      _n(pkt(c, "wynik")), _n(pkt(c, "wynik_t_ref_0.5")), _n(pkt(c, "wynik_t_ref_2.0"))])
    przypis = (f"Czas = mediana sekund na stronę; punkty szybkości ({test}) = min(1, t_ref / czas) × {_n(waga, 0)}. Rankingi liczą t_ref = 1,0 s na stronę; "
               "0,5 i 2,0 to analiza wrażliwości. Warianty aneksu nie mają pomiaru czasu.")
    return _tabela("szybkosc", kolumny, tresc, "", przypis)


def wrazliwosc(r: Raport, ranking: str = "tekst") -> str:
    """Miejsca i sumy przy trzech alternatywnych zestawach wag testów (rowne, prywatnosc, uzytecznosc) obok miejsca domyślnego."""
    uczestnicy = [w.uczestnik for w in _wiersze_rankingu(r, ranking)]
    dane = {(x["zestaw"], x["uczestnik"]): x for x in r.wrazliwosc if x["ranking"] == ranking}
    zestawy = [z for z in ZESTAWY_WAG if any((z, u) in dane for u in uczestnicy)]
    domyslne = {w.uczestnik: w for w in _wiersze_rankingu(r, ranking)}
    kolumny = [_kol("Uczestnik", 25), _kol("m. domyśl.", 9, num=True)]
    for z in zestawy:
        kolumny += [_kol(f"m.<br><small>{ZESTAWY_NAZWY[z]}</small>", 10, num=True), _kol(f"Suma<br><small>{ZESTAWY_NAZWY[z]}</small>", 12, num=True)]
    tresc = []
    for u in uczestnicy:
        wiersz = [_nazwa(u), _miejsce(domyslne[u], list(domyslne.values()))]
        for z in zestawy:
            x = dane.get((z, u))
            wiersz += [_n(None if x is None else x.get("miejsce"), 0), _n(None if x is None else x.get("suma"))]
        tresc.append(wiersz)
    opis = "; ".join(f"{ZESTAWY_NAZWY[z]} – {ZESTAWY_WAG[z]}" for z in zestawy)
    return _tabela("wrazliwosc", kolumny, tresc, "", (f"Zestawy wag: {_e(opis)}. " if opis else "") + "Miejsce domyślne – z rankingu głównego (z etykietą remisu).")


# ---------------------------------------------------------------- tryby

def tryby(r: Raport, ranking: str = "tekst") -> str:
    """Tryb domyślny vs „Maksymalna ochrona”: wiersze „w tym kwoty” i „wyciek bez kwot” (układ zatwierdzony)."""
    if ranking not in TRYBY:
        return _tabela("tryby", [_kol("Ranking", 1)], [], "")
    domyslny, maks = TRYBY[ranking]
    wiersze = []
    for x in porownanie_trybow(r):
        if x["ranking"] != ranking:
            continue
        wiersze.append([_e(x["wiersz"]), _n(x["domyslny"], 0), _n(x["maks"], 0)])
    w_d, w_m = _wiersz_uczestnika(r, ranking, domyslny), _wiersz_uczestnika(r, ranking, maks)
    szybkosc = TEST_SZYBKOSCI[ranking]
    if wiersze:  # tryb „Maksymalna ochrona” nie ma pomiaru czasu, więc sumy porównuje się bez testu szybkości
        wiersze.insert(0, [f"Suma punktów bez {szybkosc}", _n(suma_bez_szybkosci(w_d, ranking)), _n(suma_bez_szybkosci(w_m, ranking))])
    kolumny = [_kol("", 40), _kol("Tryb domyślny", 20, num=True), _kol("Maksymalna ochrona", 20, num=True)]
    return _tabela("tryby", kolumny, wiersze, "", f"Liczba wyciekłych wartości w całym zakresie gold (ten sam dla obu trybów). Suma punktów bez {szybkosc}: tryb „Maksymalna ochrona” nie ma pomiaru czasu. „n/d” – brak pomiaru.")


# ---------------------------------------------------------------- wersje i odcisk

def wersje(r: Raport) -> str:
    """Wersja aplikacji i modelu z `wersje.json` – tylko te dwa pola (reszta zawiera ustawienia środowiska, nie trafia do raportu)."""
    rzad = {}
    for klucz in ("privatizer-tekst/tekst", "privatizer-plik/plik"):
        rzad[klucz] = (r.wersje.get(klucz) or {}).get("wersje", {})
    tekst, plik = rzad["privatizer-tekst/tekst"], rzad["privatizer-plik/plik"]
    wiersze = [
        ["Aplikacja – Privatizer by Legal Geek", _e(tekst.get("aplikacja") or ND), _e(plik.get("aplikacja") or ND)],
        ["Model – Legal Geek Privatizer (RC)", _e(tekst.get("model") or ND), _e(plik.get("model") or ND)],
        ["Wersja modelu", _e(tekst.get("model_wersja") or ND), _e(plik.get("model_wersja") or ND)],
    ]
    kolumny = [_kol("", 40), _kol("Ranking tekst", 20), _kol("Ranking pliki", 20)]
    return _tabela("wersje", kolumny, wiersze, "")


def odcisk(r: Raport) -> str:
    """Odciski kodu i reguł (SHA-256) oraz wersje narzędzi z `odcisk.csv`; puste = „–” (nie dotyczy poziomu)."""
    poziomy = r.odcisk
    pola = [("kod", "Kod (SHA-256)"), ("reguly", "Reguły (SHA-256)"), ("commit", "Commit"), ("leptonica", "Leptonica"), ("libreoffice", "LibreOffice"),
            ("tessdata", "Dane Tesseract"), ("tesseract", "Tesseract")]
    kolumny = [_kol("", 20)] + [_kol(f"Poziom: {_e(p['poziom'])}", 40) for p in poziomy]
    tresc = []
    for pole, etykieta in pola:
        komorki = []
        for p in poziomy:
            v = (p.get(pole) or "").strip()
            komorki.append("–" if v == "" else (ND if v == "None" else f'<code class="hash">{_e(v)}</code>'))
        tresc.append([etykieta] + komorki)
    return _tabela("odcisk", kolumny, tresc, "")


# ---------------------------------------------------------------- trudne przypadki, zakres

def trudne_przypadki(r: Raport, ranking: str = "tekst") -> str:
    """Per przypadek trudny: Privatizer vs najlepszy z pozostałych uczestników rankingu (odsetek dokumentów bez wycieku)."""
    domyslny = TRYBY.get(ranking, ("",))[0]
    inni = {w.uczestnik for w in _wiersze_rankingu(r, ranking) if not _prywatizer(w.uczestnik)}
    po_przypadku: dict[str, dict] = {}
    for x in r.per.get("przypadek", []):
        if x["ranking"] != ranking:
            continue
        p = po_przypadku.setdefault(x["przypadek"], {"n": 0, "punktowany": True, "wart": {}})
        p["n"] = max(p["n"], x.get("dokumenty") or 0)
        p["punktowany"] = p["punktowany"] and not (str(x.get("punktowany")) == "False")
        p["wart"][x["uczestnik"]] = x.get("bez_wycieku")
    kolumny = [_kol("Przypadek", 30), _kol("Dok.", 7, num=True), _kol("Privatizer", 12, num=True), _kol("Najlepszy inny uczestnik", 31),
               _kol("Jego wynik", 12, num=True)]
    tresc = []
    for nazwa in sorted(po_przypadku):
        p = po_przypadku[nazwa]
        inne = [(v, u) for u, v in p["wart"].items() if u in inni and v is not None]
        najlepszy = max(inne, key=lambda t: (t[0], -ord(t[1][0]))) if inne else None
        tresc.append([_e(nazwa) + ("" if p["punktowany"] else " <small>(poza punktacją)</small>"), _n(p["n"], 0), _p(p["wart"].get(domyslny)),
                      _nazwa(najlepszy[1]) if najlepszy else ND, _p(najlepszy[0]) if najlepszy else ND])
    return _tabela("trudne", kolumny, tresc, "", "Odsetek dokumentów przypadku bez wycieku (nie ważony). Przypadki „poza punktacją” nie wchodzą do T3/P3.")


def w_zakresie(r: Raport, ranking: str = "tekst") -> str:
    """Miary pomocnicze: tylko w zakresie kategorii deklarowanych przez uczestnika oraz tylko w jego językach oficjalnych."""
    kolumny = [_kol("Uczestnik", 25), _kol("Dok. w zakresie", 9, num=True), _kol("Z wyciekiem", 11, num=True), _kol("Bez wycieku", 9, num=True),
               _kol("Wartości", 10, num=True), _kol("Wyciekłe", 9, num=True), _kol("Odsetek wartości", 10, num=True), _kol("Dok. oficjalne", 9, num=True),
               _kol("Bez wycieku (oficjalne)", 10, num=True)]
    dane = {x["uczestnik"]: x for x in r.w_zakresie if x["ranking"] == ranking}
    tresc = []
    for w in _wiersze_rankingu(r, ranking) + sorted(r.aneks.get(ranking, []), key=lambda x: x.uczestnik):
        x = dane.get(w.uczestnik, {})
        tresc.append([_nazwa(w.uczestnik), _n(x.get("zakres_dokumenty"), 0), _n(x.get("zakres_z_wyciekiem"), 0), _p(x.get("zakres_bez_wycieku")),
                      _n(x.get("zakres_wartosci"), 0), _n(x.get("zakres_wyciekle"), 0), _p(x.get("zakres_odsetek_wartosci"), 1),
                      _n(x.get("oficjalne_dokumenty"), 0), _p(x.get("oficjalne_bez_wycieku"))])
    przypis = ("Miary pomocnicze, poza punktami: wartości tylko z kategorii, które uczestnik deklaruje (zakres per język dokumentu), oraz dokumenty "
               "tylko w językach oficjalnych uczestnika. Uczestnicy z aneksu – na końcu.")
    return _tabela("zakres", kolumny, tresc, "", przypis)


# ---------------------------------------------------------------- identyfikacja pośrednia

def posrednie(r: Raport, ranking: str = "tekst") -> str:
    """Identyfikacja pośrednia (`metodyka/posrednie.md`): odsetek kombinacji przerwanych z przedziałem ufności, poza punktami;
    uczestnicy rankingu w kolejności miejsc, potem aneks. Brak danych (brak kolumn w `pomocnicze.csv`) = „n/d”."""
    dane = {x["uczestnik"]: x for x in r.pomocnicze if x.get("ranking") == ranking}
    tresc = []
    for w in _wiersze_rankingu(r, ranking) + sorted(r.aneks.get(ranking, []), key=lambda x: x.uczestnik):
        x = dane.get(w.uczestnik, {})
        odsetek = x.get("posrednie_odsetek")
        ci = ND if odsetek is None else przedzial_procent(x.get("posrednie_ci_dol"), x.get("posrednie_ci_gora"))
        tresc.append([_nazwa(w.uczestnik), _n(x.get("posrednie_kombinacje"), 0), _n(x.get("posrednie_przerwane"), 0), _p(odsetek, 1), ci])
    kolumny = [_kol("Uczestnik", 32), _kol("Kombinacje", 15, num=True), _kol("Przerwane", 15, num=True), _kol("Odsetek przerwanych", 19, num=True),
               _kol("Przedział ufności<br><small>95%</small>", 19, num=True)]
    przypis = ("Miara opisowa, poza punktami (nie wpływa na miejsca w rankingach). Kombinacja jest przerwana, gdy "
               "co najmniej jeden jej składnik nie jest widoczny w wyniku. Uczestnicy z aneksu – na końcu.")
    return _tabela("posrednie", kolumny, tresc, "", przypis)


# ---------------------------------------------------------------- aplikacja a gołe modele

def aplikacja_vs_modele(r: Raport, ranking: str = "tekst") -> str:
    """Pełna aplikacja, składniki i obce modele w potoku i samodzielnie; suma BEZ T6 (warianty aneksu nie mają pomiaru czasu)."""
    kolumny = [_kol("Uczestnik", 21), _kol("Co to jest", 35), _kol("Suma bez T6", 11, num=True)]
    kolumny += [_kol(f"{t}<br><small>/{wagi_testow()[t]}</small>", 8.5, num=True) for t in ("T1", "T2", "T3", "T4", "T5")]
    tresc = []
    for u in APLIKACJA_VS_MODELE:
        w = _wiersz_uczestnika(r, ranking, u)
        if w is None:
            continue
        tresc.append([_nazwa(u), _e(OPISY[u]), _n(suma_bez_szybkosci(w))] + [_n(w.testy[t].pkt) for t in ("T1", "T2", "T3", "T4", "T5")])
    przypis = ("Suma punktów bez T6 (szybkości) to suma T1–T5; kolumny pokazują każdy z tych testów. Warianty z aneksu nie mają pomiaru czasu, więc wszystkie wiersze porównuje się na tej samej podstawie. "
               "Obcy model w potoku nie ma kalibracji Privatizera, a potok był strojony pod model Legal Geek Privatizer (RC) – to analiza wkładu składników, "
               "nie ocena żadnego z produktów.")
    return _tabela("aplikacja", kolumny, tresc, "", przypis)


# ---------------------------------------------------------------- gdzie Privatizer przegrywa

def przewagi(r: Raport, wymiar: str, ranking: str = "tekst") -> list[dict]:
    """Wycinki, w których najlepszy z pozostałych uczestników rankingu (bez wariantów Privatizera) ma lepszy wynik niż Privatizer.

    Wiersze `{wycinek, privatizer, inny, wartosc_inny, roznica, n}` od największej różnicy; `wymiar`: test, jezyk, format, typ, kategoria, miejsce (w dokumencie), szybkosc.
    Kierunek: więcej = lepiej (punkty, odsetek bez wycieku) albo mniej = lepiej (odsetek wycieków, czas)."""
    if ranking not in TRYBY:
        return []
    domyslny = TRYBY[ranking][0]
    inni = {w.uczestnik for w in _wiersze_rankingu(r, ranking) if not _prywatizer(w.uczestnik)}
    wycinki: dict[str, dict[str, float | None]] = {}
    n: dict[str, int] = {}
    wyzej = True
    if wymiar == "test":
        for w in _wiersze_rankingu(r, ranking):
            for t in TESTY_RANKINGU[ranking]:
                wycinki.setdefault(t, {})[w.uczestnik] = w.testy[t].pkt
    elif wymiar == "szybkosc":
        wyzej = False
        wycinki["s / stronę"] = {c["uczestnik"]: c.get("s_na_strone") for c in r.czas if c["ranking"] == ranking}
    elif wymiar in ("jezyk", "format", "typ", "kategoria", "miejsce"):
        pole, _, pole_n, _ = _PER[wymiar]
        wyzej = pole != "odsetek_wyciekow"
        for x in r.per.get(wymiar, []):
            if x["ranking"] == ranking:
                wycinki.setdefault(x[wymiar], {})[x["uczestnik"]] = x.get(pole)
                n[x[wymiar]] = max(n.get(x[wymiar], 0), x.get(pole_n) or 0)
    wynik = []
    for wycinek, wart in wycinki.items():
        moj = wart.get(domyslny)
        inne = [(v, u) for u, v in wart.items() if u in inni and v is not None]
        if moj is None or not inne:
            continue
        v, u = max(inne, key=lambda t: (t[0] if wyzej else -t[0], t[1]))
        lepszy = v > moj if wyzej else v < moj
        if lepszy:
            wynik.append({"wycinek": wycinek, "privatizer": moj, "inny": u, "wartosc_inny": v, "roznica": abs(v - moj), "n": n.get(wycinek)})
    return sorted(wynik, key=lambda x: (-x["roznica"], x["wycinek"]))


def liczba_przewag(r: Raport, wymiar: str, ranking: str = "tekst") -> int | None:
    """Liczba wycinków przewagi innych uczestników; None, gdy dla rankingu nie ma danych tego wymiaru (n/d, nie 0)."""
    if wymiar in ("jezyk", "format", "typ", "kategoria", "miejsce") and not any(x["ranking"] == ranking for x in r.per.get(wymiar, [])):
        return None
    if wymiar == "szybkosc" and not any(c["ranking"] == ranking for c in r.czas):
        return None
    return len(przewagi(r, wymiar, ranking))


def przegrywa(r: Raport, wymiar: str, ranking: str = "tekst") -> str:
    """Tabela wycinków, w których któryś z pozostałych uczestników bije Privatizera (z `przewagi`); brak takich wycinków = jeden wiersz z informacją."""
    wiersze = przewagi(r, wymiar, ranking)
    jednostka = {"test": "pkt", "szybkosc": "s / stronę"}.get(wymiar, "%")

    def f(v):
        return _n(v, 1) if wymiar == "test" else (_sek(v) if wymiar == "szybkosc" else _p(v, 1))

    def fr(v):
        return f(v) if wymiar in ("test", "szybkosc") else _n(v * 100, 1) + "&nbsp;p.p."

    kolumny = [_kol({"test": "Test", "jezyk": "Język", "format": "Format", "typ": "Typ dokumentu", "kategoria": "Kategoria", "miejsce": "Miejsce w dokumencie", "szybkosc": "Miara"}.get(wymiar, "Wycinek"), 22),
               _kol(f"Privatizer<br><small>{jednostka}</small>", 14, num=True), _kol("Najlepszy inny uczestnik", 30),
               _kol(f"Jego wynik<br><small>{jednostka}</small>", 14, num=True), _kol("Różnica", 12, num=True)]
    if wymiar in ("kategoria", "miejsce"):
        kolumny.append(_kol("Wartości", 9, num=True))
    tresc = []
    for x in wiersze:
        etykieta = MIEJSCA.get(x["wycinek"], x["wycinek"]) if wymiar == "miejsce" else x["wycinek"]
        wiersz = [_e(etykieta), f(x["privatizer"]), _nazwa(x["inny"]), f(x["wartosc_inny"]), fr(x["roznica"])]
        if wymiar in ("kategoria", "miejsce"):
            wiersz.append(_n(x["n"], 0))
        tresc.append(wiersz)
    return _tabela("przegrywa", kolumny, tresc, "", pusta="Brak wycinków, w których inny uczestnik ma lepszy wynik niż Privatizer.")


def _odsetek_z_przedzialem(w: dict, klasa: str) -> str:
    if w.get(f"{klasa}_odsetek") is None:
        return ND
    return f'{_p(w[f"{klasa}_odsetek"], 1)}<br><small>{przedzial_procent(w.get(f"{klasa}_ci_dol"), w.get(f"{klasa}_ci_gora"))}</small>'


def kontrola_domen(r: Raport, ranking: str = "tekst", kategoria: str = "EMAIL") -> str:
    """Kontrola domen zarezerwowanych: odsetek wyciekłych wartości z domeną `example.*` i `*.test` z przedziałami, ich różnica, mediana różnic
    pozostałych uczestników i sygnał przewagi (test: `metodyka/kontrola-domen.md`, pkt 2); uczestnicy rankingu w kolejności miejsc."""
    tresc = []
    for w in kontrola_domen_wiersze(r, ranking, kategoria):
        sygnal = ND if w.get("sygnal") is None else ("tak" if w["sygnal"] == "tak" else "nie" + ("<br><small>mniejsza</small>" if w.get("kierunek") == "mniejsza" else ""))
        roznica = ND if w.get("roznica") is None else f'{roznica_pp(w["roznica"])}<br><small>{przedzial_procent(w.get("roznica_ci_dol"), w.get("roznica_ci_gora"))}</small>'
        mediana = ND if w.get("mediana_pozostalych") is None else f'{roznica_pp(w["mediana_pozostalych"])}<br><small>{przedzial_procent(w.get("mediana_ci_dol"), w.get("mediana_ci_gora"))}</small>'
        tresc.append([_nazwa(w["uczestnik"]), f'{_n(w["example_n"], 0)} / {_n(w["test_n"], 0)}', _odsetek_z_przedzialem(w, "example"),
                      _odsetek_z_przedzialem(w, "test"), roznica, mediana, sygnal])
    kolumny = [_kol("Uczestnik", 23), _kol("Wartości<br><small>example / .test</small>", 11, num=True),
               _kol("Wyciek<br><small>example.*</small>", 14, num=True), _kol("Wyciek<br><small>.test</small>", 14, num=True),
               _kol("Różnica<br><small>.test − example</small>", 15, num=True), _kol("Mediana różnic<br><small>pozostałych</small>", 15, num=True),
               _kol("Sygnał<br><small>przewagi</small>", 11)]
    return _tabela("kontrola-domen", kolumny, tresc, f"Kontrola domen, {'ranking tekstu' if ranking == 'tekst' else 'ranking plików'}, kategoria {kategoria}")


def ranking_bez_example(r: Raport, ranking: str = "tekst") -> str:
    """Ranking główny obok rankingu przeliczonego bez wartości EMAIL/URL w domenach `example.*` (te same wagi i bootstrap): miejsca, sumy z przedziałami, różnica."""
    wariant = r.ranking_bez_example.get(ranking, [])
    po_nazwie = {w.uczestnik: w for w in wariant}
    tresc = []
    for g in _wiersze_rankingu(r, ranking):
        w = po_nazwie.get(g.uczestnik)
        if w is None:
            continue
        delta = ND if g.suma is None or w.suma is None else roznica(w.suma - g.suma, 1)
        tresc.append([_nazwa(g.uczestnik), _miejsce(g, r.rankingi[ranking]), f"{_n(g.suma)}<br><small>{przedzial(g.suma_ci)}</small>",
                      _miejsce(w, wariant), f"{_n(w.suma)}<br><small>{przedzial(w.suma_ci)}</small>", delta])
    kolumny = [_kol("Uczestnik", 30), _kol("Miejsce<br><small>główny</small>", 12, num=True), _kol("Suma<br><small>główny, pkt</small>", 17, num=True),
               _kol("Miejsce<br><small>bez example.*</small>", 14, num=True), _kol("Suma<br><small>bez example.*, pkt</small>", 17, num=True),
               _kol("Różnica<br><small>pkt</small>", 10, num=True)]
    return _tabela("ranking-bez-example", kolumny, tresc, f"Ranking {'tekstu' if ranking == 'tekst' else 'plików'} bez wartości EMAIL i URL w domenach example.*")


# ---------------------------------------------------------------- przykłady

MIEJSCA = {"tresc": "treść", "tabela": "tabela", "przypis": "przypis", "naglowek": "nagłówek", "stopka": "stopka", "pole": "pole", "obraz": "obraz",
           "zalacznik": "załącznik", "metadane": "metadane", "komentarz": "komentarz", "zmiany": "śledzenie zmian"}
RODZAJE = {"pelny": "pełny", "czesciowy": "częściowy"}
_MASKA = re.compile(r"\[[A-Za-z][A-Za-z _]{1,28}\]")


def _przed(p: dict, zakres: dict | None) -> str:
    """Okno tekstu przed anonimizacją: wartość wzorcowa, która wyciekła, w `<mark class="wyciek">` (podkreślenie i pogrubienie, nie tylko kolor);
    bez zgodnego zakresu (brak sidecara albo inny tekst pod offsetem) – okno bez podświetlenia."""
    tekst = p["przed"]
    if not zakres or tekst[zakres["od"]:zakres["do"]] != zakres["tekst"]:
        return f"{_e(tekst)}…"
    return f'{_e(tekst[:zakres["od"]])}<mark class="wyciek">{_e(zakres["tekst"])}</mark>{_e(tekst[zakres["do"]:])}…'


def _po(p: dict) -> str:
    """Okno tekstu po anonimizacji; oznaczenia maski uczestnika (np. `[PERSON]`) w ramce, żeby odróżnić je od tekstu dokumentu."""
    return _MASKA.sub(lambda m: f'<span class="maska">{m.group()}</span>', _e(p["po"])) + "…"


def przyklady(r: Raport, ranking: str = "tekst") -> str:
    """Pary przed/po z `przyklady.jsonl` (pierwsze dokumenty z wyciekiem w kolejności manifestu, po dwa na uczestnika rankingu) w kolejności miejsc;
    podświetlona wartość, która wyciekła w całości lub w części. Tylko syntetyczne dokumenty korpusu."""
    miejsca = {w.uczestnik: (w.miejsce is None, w.miejsce or 0) for w in r.rankingi.get(ranking, [])}
    zakresy = zakresy_przykladow()
    wiersze = []
    for p in sorted(r.przyklady, key=lambda x: (miejsca.get(x["uczestnik"], (True, 0)), x["uczestnik"], x["id"])):
        wyciek = p.get("wyciek")
        if isinstance(wyciek, list) and len(wyciek) >= 4:  # [wartosc_id, kategoria, miejsce, rodzaj]
            opis = f'{_e(wyciek[1])}<br><small>{_e(MIEJSCA.get(wyciek[2], wyciek[2]))}, {_e(RODZAJE.get(wyciek[3], wyciek[3]))}</small>'
            zakres = zakresy.get(f'{p["id"]}|{wyciek[0]}')
        else:
            opis, zakres = ND, None
        wiersze.append([f'{_nazwa(p["uczestnik"])}<br><small>{_e(p["id"])}</small>', f'<span class="okno">{_przed(p, zakres)}</span>',
                        f'<span class="okno">{_po(p)}</span>', opis])
    kolumny = [_kol("Uczestnik", 17), _kol("Przed anonimizacją", 35), _kol("Po anonimizacji", 35), _kol("Wyciek", 13)]
    return _tabela("przyklady", kolumny, wiersze, "Przykłady wycieków w rankingu tekstu (fragmenty dokumentów syntetycznych)",
                   "Podkreślona, pogrubiona wartość wzorcowa (gdy znane jest jej położenie w oknie) pozostała w wyniku w całości („pełny”) lub w części („częściowy”). Ramka oznacza oznaczenie maski wstawione przez uczestnika.")


def zrodla_prawne(r: Raport) -> str:
    """Aneks „Źródła prawne”: rejestr `raport/zrodla.md` – akt z publikatorem, jednostki redakcyjne, status weryfikacji, odnośnik (bez kolumny „Uwagi”)."""
    wiersze = []
    for w in wczytaj_rejestr():
        url = w["URL"] if w["URL"].startswith("https://") else ""
        zrodlo = f'<a href="{_e(url)}">{_e(w["Źródło"])}</a>' if url else _e(w["Źródło"])
        wiersze.append([f'{_e(w["Akt / źródło"])}<br><small>{_e(w["Publikator i wersja"])}</small>', _e(w["Jednostki redakcyjne"]), _e(w["Status"]), zrodlo])
    kolumny = [_kol("Akt / źródło i publikator", 42), _kol("Jednostki redakcyjne", 24), _kol("Status weryfikacji", 23), _kol("Źródło", 11)]
    return _tabela("zrodla", kolumny, wiersze, "Rejestr źródeł prawnych rozdziału „Dlaczego to ważne”")


TABELE_FUNKCJE: dict[str, Callable[..., str]] = {
    "przyklady": przyklady,
    "kontrola_domen": kontrola_domen,
    "ranking_bez_example": ranking_bez_example,
    "ranking": ranking,
    "aneks_x1": aneks_x1,
    "podsumowanie": podsumowanie,
    "per": per,
    "szybkosc": szybkosc,
    "wrazliwosc": wrazliwosc,
    "tryby": tryby,
    "wersje": wersje,
    "odcisk": odcisk,
    "trudne_przypadki": trudne_przypadki,
    "w_zakresie": w_zakresie,
    "posrednie": posrednie,
    "aplikacja_vs_modele": aplikacja_vs_modele,
    "przegrywa": przegrywa,
    "zrodla_prawne": zrodla_prawne,
}
