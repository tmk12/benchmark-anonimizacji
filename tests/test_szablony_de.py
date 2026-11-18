"""Testy szablonów DE: jedna jurysdykcja (Niemcy), spójność dat i kwot, poziomy sądów i Aktenzeichen, rodzaj gramatyczny
(w tym przyimki z rodzajnikiem), medycyna (ICD-10-GM, KVNR, LANR), kapitał GmbH."""
from __future__ import annotations

import datetime as dt
import random
import re

import phonenumbers
import pytest

from pbench.budowa import MAPA_KATEGORII, zbuduj_z_kontekstem
from pbench.dane import Generator
from pbench.linearyzacja import linearyzuj_z_wartosciami
from pbench.szablony import SZABLONY, TYPY

TYPY_DE = list(TYPY)
MIESIACE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November",
            "Dezember"]
#: Kategorie identyfikatorów innych krajów – w dokumencie niemieckim nie mogą wystąpić.
OBCE = {"PESEL", "NIP", "REGON", "KRS", "NINO", "NHS", "SSN", "EIN", "NIR", "SIREN", "DNI", "NUSS", "CIF", "PASZPORT"}
#: Wyrażenia obcych krajów (waluty, formy prawne, urzędy), których nie wolno znaleźć w tekście dokumentu.
ZAKAZANE = re.compile(r"\$|£| zł\b|\bSARL\b|\bLtd\b|\bLLC\b|\bSp\. z o\.o\.|\bSIRET\b|\bPESEL\b|\bNHS\b|\bHMRC\b|"
                      r"\bURSSAF\b|\bJuzgado\b|\bSąd\b|\bTribunal\b|\bS\.L\.\b")
TELEFON = re.compile(r"^(?:\+49|0)[\d ]+$")
ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
#: Aktenzeichen wg poziomu sądu (`Kontekst.poziom_sadu`).
AZ = {"amtsgericht": r"\d{1,2} C \d{1,4}/\d{2}", "landgericht": r"\d{1,2} O \d{1,3}/\d{2}",
      "berufung": r"\d{1,2} S \d{1,3}/\d{2}"}


def _buduj(typ: str, ziarno: int, wariant: str | None = None):
    s = SZABLONY[("de", typ)]
    w = zbuduj_z_kontekstem(s, Generator("de", ziarno), random.Random(ziarno), wariant)
    return w, linearyzuj_z_wartosciami(w.dokument)


def _data(tekst: str) -> dt.date:
    """Data w zapisie niemieckim: „12. März 2024” albo „12.03.2024”."""
    m = re.fullmatch(r"(\d{1,2})\. ([A-Za-zä]+) (\d{4})", tekst)
    if m:
        return dt.date(int(m.group(3)), MIESIACE.index(m.group(2)) + 1, int(m.group(1)))
    m = re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})", tekst)
    assert m, tekst
    return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))


def _grosze(tekst: str) -> int:
    m = re.fullmatch(r"(\d{1,3}(?:\.\d{3})*),(\d{2}) (?:€|EUR)", tekst)
    assert m, tekst
    return int(m.group(1).replace(".", "")) * 100 + int(m.group(2))


def _pole(wartosci, nazwa: str) -> str:
    return next(w.tekst for w in wartosci if w.id == f"ctx.{nazwa}#1")


def _sygnatura(wartosci, id_: str = "sad.sygnatura#1") -> str:
    return next(x.tekst for x in wartosci if x.id == id_)


@pytest.mark.parametrize("typ", TYPY_DE)
def test_de_jedna_jurysdykcja_waluta_data_telefon(typ):
    """200 budów: osoby z Niemiec, bez identyfikatorów obcych krajów, jeden symbol waluty i jeden styl dat."""
    for i in range(200):
        w, (tekst, _, wartosci) = _buduj(typ, 300 + i)
        assert w.kontekst.kraj == "DE" and {o.kraj for o in w.osoby.values()} <= {"DE"}
        assert not {x.kategoria for x in wartosci} & OBCE
        symbole = {x.tekst.rsplit(" ", 1)[1] for x in wartosci if x.kategoria == "KWOTA"}
        assert len(symbole) <= 1 and symbole <= {"€", "EUR"}, (typ, symbole)
        for x in wartosci:
            if x.kategoria == "TELEFON":
                assert TELEFON.match(x.tekst), (typ, x.tekst)
            if x.kategoria == "KOD_POCZTOWY":
                assert re.fullmatch(r"\d{5}", x.tekst)
        daty = [x.tekst for x in wartosci if x.kategoria in ("DATA", "DATA_UR")]
        for d in daty:
            _data(d)
        assert len({bool(re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", d)) for d in daty}) <= 1, daty
        assert not ISO.search(tekst), (typ, ISO.search(tekst).group())
        zle = ZAKAZANE.search(tekst)
        assert zle is None, (typ, zle and tekst[max(0, zle.start() - 40):zle.end() + 30])


WYROK = {
    "de_amtsgericht": (r"Amtsgericht .+", "amtsgericht", {"richter1"}),
    "de_landgericht": (r"Landgericht .+", "landgericht", {"richter1", "richter2", "richter3"}),
    "de_einzelrichter": (r"Landgericht .+", "landgericht", {"richter1"}),
    "de_berufung": (r"Landgericht .+", "berufung", {"richter1", "richter2", "richter3"}),
}


def test_de_wyrok_poziomy_sadow_skladow_i_sygnatur():
    for i in range(200):
        wariant = list(WYROK)[i % 4]
        w, (tekst, _, wartosci) = _buduj("wyrok", 700 + i, wariant)
        sad, poziom, sedziowie = WYROK[wariant]
        k, d = w.kontekst, w.kontekst.daty
        linie = tekst.split("\n")
        assert re.fullmatch(sad, linie[0]), linie[0]
        az = _sygnatura(wartosci)
        assert re.fullmatch(AZ[poziom], az), (wariant, az)
        assert {x.id.split(".")[0] for x in wartosci if x.id.startswith("richter")} == sedziowie, wariant
        assert "als Einzelrichter" in tekst if wariant == "de_einzelrichter" else "als Einzelrichter" not in tekst
        assert "IM NAMEN DES VOLKES" in linie and "URTEIL" in linie
        assert _data(_pole(wartosci, "wyrok_koncowy")) == d["wyrok_koncowy"]
        assert d["rozprawa_koncowa"] < d["wyrok_koncowy"]       # Verkündung po rozprawie
        assert d["umowa"] < d["termin_platnosci"] < d["wezwanie"] < d["termin_wezwania"] < d["pozew"] < d["rozprawa"]
        assert k.kwoty["zasadzona"] < k.kwoty["glowna"]
        rok = int(az[-2:])
        assert 2000 + rok == k.sygn_rok <= d["wyrok_koncowy"].year
        if poziom == "landgericht":
            assert k.kwoty["glowna"] > 5000_00 and rok == d["pozew"].year % 100
        else:           # Amtsgericht i Berufung: wartość sporu w I instancji <= 5 000 €, Beschwer > 600 €
            assert k.kwoty["glowna"] <= 5000_00 and k.kwoty["zasadzona"] > 600_00
        if wariant == "de_berufung":
            assert d["wyrok"] < d["apelacja"] < d["rozprawa_apel"] <= d["wyrok_apel"]
            assert 2000 + rok == d["apelacja"].year
            pierwsza = _sygnatura(wartosci, "ctx.sygn_pierwsza#1")
            assert re.fullmatch(AZ["amtsgericht"], pierwsza) and int(pierwsza[-2:]) == d["pozew"].year % 100
            assert linie[2].startswith("Vorinstanz: Amtsgericht ")
        else:
            assert "Vorinstanz" not in tekst
        udzial = k.liczby["kosten_kl"]
        assert 5 <= udzial <= 45 and udzial + k.liczby["kosten_bekl"] == 100
        assert abs(udzial - 100 * (1 - k.kwoty["zasadzona"] / k.kwoty["glowna"])) <= 2.5 + 1e-9


def test_de_wyrok_numeracja_bez_luk():
    rzymskie = ["I", "II", "III", "IV", "V"]
    for i in range(160):
        wariant = list(WYROK)[i % 4]
        _, (tekst, _, _) = _buduj("wyrok", 4300 + i, wariant)
        przed, tatbestand, gruende = re.split(r"\nTatbestand\n|\nEntscheidungsgründe\n", tekst)[:3]
        tenor = przed.split("für Recht erkannt:\n")[1].split("\n")
        numery = [int(m.group(1)) for l in tenor if (m := re.match(r"(\d)\. ", l))]
        assert numery == list(range(1, len(numery) + 1)) and len(numery) >= 4, (wariant, tenor)
        linie = gruende.split("\n")
        serie = [m.group(1) for l in linie if (m := re.match(r"(I|II|III|IV|V)\. ", l))]
        # LG (Anwaltsprozess) bez Rechtsbehelfsbelehrung: I.–III.; AG i Berufung: I.–IV.
        assert serie == rzymskie[:len(serie)] and len(serie) == (3 if wariant in ("de_landgericht", "de_einzelrichter") else 4), (wariant, serie)
        arabskie = [int(m.group(1)) for l in linie if (m := re.match(r"(?:II\. )?(\d)\. ", l))]
        assert arabskie == list(range(1, len(arabskie) + 1)) and len(arabskie) >= 3, (wariant, arabskie)


def test_de_wyrok_cytaty_to_zwykly_tekst_bgh():
    for i in range(60):
        w, (tekst, _, wartosci) = _buduj("wyrok", 900 + i)
        assert not any(x.id.startswith("zitat") for x in wartosci)
        cytaty = re.findall(r"BGH, (?:Urt\. v\. \d{1,2}\.\d{1,2}\.\d{4}|Urteil vom \d{1,2}\. [A-Za-zä]+ \d{4}|"
                            r"Beschl\. v\. \d{1,2}\.\d{1,2}\.\d{4}) – [IVX]+ ZR \d{1,3}/\d{2}", tekst)
        assert len(cytaty) == 3, tekst[-1500:]


def test_de_pozew_wezwanie_lancuch_dat_i_sumy():
    for typ in ("pozew", "wezwanie"):
        for i in range(120):
            w, (tekst, _, wartosci) = _buduj(typ, 1100 + i)
            d, k = w.kontekst.daty, w.kontekst
            assert d["umowa"] < d["termin_platnosci"] < d["wezwanie"] < d["termin_wezwania"] < d["pozew"]
            assert all(_data(x.tekst) <= d["pozew"] for x in wartosci if x.kategoria == "DATA"), typ
            if typ == "wezwanie":
                n = {c: _grosze(_pole(wartosci, c)) for c in ("glowna", "odsetki", "koszty_wind", "razem_wez")}
                assert n["razem_wez"] == n["glowna"] + n["odsetki"] + n["koszty_wind"]
                assert k.kwoty["ugoda_rata"] < k.kwoty["glowna"]
            else:
                assert k.wariant in ("de_amtsgericht", "de_landgericht")
                lg = k.wariant == "de_landgericht"
                assert (k.kwoty["glowna"] > 5000_00) == lg
                assert re.search(r"^(?:Land|Amts)gericht ", tekst, re.M) and ("Anwaltszwang" in tekst) == lg
                assert tekst.split("An das\n")[1].startswith("Landgericht" if lg else "Amtsgericht")
                assert _data(_pole(wartosci, "pozew")) == d["pozew"]
                assert k.kwoty["oplata_pozwu"] < k.kwoty["glowna"]


def test_de_faktura_sumy_i_ust_19():
    for i in range(120):
        w, (tekst, _, wartosci) = _buduj("faktura", 1300 + i)
        netto = sum(_grosze(_pole(wartosci, n)) for n in ("kf1", "kf2", "kf3"))
        assert _grosze(_pole(wartosci, "netto")) == netto
        assert _grosze(_pole(wartosci, "brutto")) == netto + _grosze(_pole(wartosci, "vat"))
        assert abs(_grosze(_pole(wartosci, "vat")) - netto * 0.19) <= 1
        assert "19 %" in tekst and "USt-IdNr." in tekst and "Steuernummer" in tekst
        assert _data(_pole(wartosci, "dok_sprzedaz")) <= _data(_pole(wartosci, "dok")) <= _data(_pole(wartosci, "dok_termin_fv"))
        assert {"VAT", "NR_PODATKOWY"} <= {x.kategoria for x in wartosci}
        for x in wartosci:
            if x.kategoria == "VAT":
                assert re.fullmatch(r"DE\d{9}", x.tekst)


def test_de_lista_plac_sumy_i_identyfikatory():
    for i in range(6):
        w, (_, _, wartosci) = _buduj("lista_plac", 1500 + i)
        wiersze = [_grosze(x.tekst) for x in wartosci if x.id.startswith("ctx.brutto_")]
        assert len(wiersze) >= 200 and _grosze(_pole(wartosci, "suma_212")) == sum(wiersze[:212])
        ids = {x.kategoria for x in wartosci if x.miejsce == "tabela"}
        assert {"NR_PODATKOWY", "SVNR", "RACHUNEK"} <= ids


def test_de_med_kolejnosc_dat_rozpoznania_wg_profilu_i_plci():
    from pbench.dane.wspolne import kod_icd_plec, slownik
    plcie = set()
    for typ, profil in (("med_wypis", "kardiologie"), ("med_zaswiadczenie", "innere")):
        assert SZABLONY[("de", typ)].profil == profil
        glowne = set(slownik("de", f"choroby_{profil}_glowne")) if profil == "kardiologie" else set()
        choroby = set(slownik("de", f"choroby_{profil}")) | glowne
        leki = {x.split("|")[0] for x in slownik("de", f"leki_{profil}")}
        for i in range(200):
            w, (tekst, _, wartosci) = _buduj(typ, 1700 + i)
            plec = w.osoby["patient"].plec
            plcie.add(plec)
            diag = [d for d in w.encje["patient"].diagnozy if d in tekst]
            meds = [d for d in w.encje["patient"].leki if d in tekst]
            assert diag and meds
            assert all(d in choroby and kod_icd_plec(d) in (None, plec) for d in diag), diag
            if glowne:     # narracja Arztbrief to niewydolność serca: rozpoznanie główne z puli HF, reszta współistniejące
                assert diag[0] in glowne and not set(diag[1:]) & glowne, diag
            assert all(m.rsplit(" ", 2)[0] in leki for m in meds), meds
            assert len(set(diag)) == len(diag) and len(set(meds)) == len(meds)
            d = w.kontekst.daty
            if typ == "med_wypis":
                assert d["przyjecie"] < d["wypis"] < d["kontrola"] and d["wypis"] <= d["zwolnienie_do"]
                assert _data(_pole(wartosci, "przyjecie")) == d["przyjecie"]
                assert w.osoby["patient"].data_ur < d["przyjecie"]
            else:
                assert d["zas_od"] < d["zas_wystaw"] < d["rozprawa"] < d["zas_do"]
                nr_id = [x.tekst for x in wartosci if x.kategoria == "NR_ID"]
                assert nr_id and all(re.fullmatch(r"\d{9}", n) for n in nr_id), nr_id
            kvnr = [x.tekst for x in wartosci if x.kategoria == "KVNR"]
            assert kvnr and all(re.fullmatch(r"[A-Z]\d{9}", n) for n in kvnr), kvnr
    assert plcie == {"M", "K"}


def test_de_odpis_protokol_cv_kolejnosc_dat_i_kapital():
    """GmbH: Stammkapital >= 25 000 € (§ 5 GmbHG), wielokrotność nominału 250 €; spółka dokumentu w formie GmbH."""
    for i in range(120):
        w, (tekst, _, wartosci) = _buduj("odpis_rejestru", 1900 + i)
        d = w.kontekst.daty
        assert d["kr_rejestracja"] <= d["kr_wpis"] <= d["dok"]
        kapital = _grosze(_pole(wartosci, "kapital2"))
        assert kapital >= 25_000_00 and kapital % 250_00 == 0
        for rola in ("gf1", "gf2", "gf3"):
            assert w.osoby[rola].data_ur < d["kr_rejestracja"]
        firma = next(x.tekst for x in wartosci if x.id == "gesellschaft.nazwa#1")
        assert firma.endswith(" GmbH"), firma
        assert re.search(r"Handelsregister B beim Amtsgericht [A-ZÄÖÜ]", tekst)
        assert next(x for x in wartosci if x.id == "gesellschaft.hrb#1").kategoria == "NR_REJESTRU"
        assert not {x.kategoria for x in wartosci} & {"NR_PODATKOWY", "SVNR", "DOWOD", "KVNR"}   # w odpisie brak ID osób
        assert "Abschlussprüfer" not in tekst
        w, (tekst, _, wartosci) = _buduj("protokol", 2100 + i)
        u = w.kontekst.liczby
        assert w.kontekst.kwoty["kapital3"] == (u["udzialy1"] + u["udzialy2"] + u["udzialy3"]) * 250_00 >= 25_000_00
        assert next(x.tekst for x in wartosci if x.id == "gesellschaft.nazwa#1").endswith(" GmbH")
        assert "Geschäftsanteile" in tekst and "Aktien" not in tekst
        w, (_, _, wartosci) = _buduj("cv", 2300 + i)
        d = w.kontekst.daty
        assert d["cv_studia"] < d["cv_od2"] < d["cv_do2"] <= d["cv_od1"]


#: (rola, formy męskie niedopuszczalne dla kobiety, formy żeńskie niedopuszczalne dla mężczyzny)
KLAEGER = ("klaeger", r"\bKläger\b|\bKlägers\b|\bBerufungsbeklagter\b", r"\bKlägerin\b|\bBerufungsbeklagte\b")
BEKLAGTER = ("beklagter", r"\bBeklagter\b|\bder Beklagte\b|\bdes Beklagten\b|\bdem Beklagten\b|\bden Beklagten\b|"
                          r"\bBerufungskläger\b",
             r"\bdie Beklagte\b|\bder Beklagten\b|– Beklagte –|\bBeklagte und\b|\bBerufungsklägerin\b")
GENERO = {
    "pozew": [KLAEGER, BEKLAGTER, ("anwalt", r"\bRechtsanwalt\b|\bunterzeichnenden Rechtsanwalt\b",
                                   r"\bRechtsanwältin\b")],
    "wyrok": [KLAEGER, BEKLAGTER],
    "wezwanie": [("schuldner", r"Sehr geehrter\b", r"Sehr geehrte\b"), ("anwalt", r"\bRechtsanwalt\b", r"\bRechtsanwältin\b")],
    "protokol": [("leiter", r"\bVersammlungsleiter\b", r"\bVersammlungsleiterin\b")],
    "med_wypis": [("patient", r"\bder Patient\b|\bHerrn?\b", r"\bdie Patientin\b|\bFrau\b")],
    "med_zaswiadczenie": [("patient", r"\bder Patient\b|\bdem Patienten\b|\bHerrn?\b|\bihm\b",
                           r"\bdie Patientin\b|\bder Patientin\b|\bFrau\b|\bihr\b")],
    "email": [("mandant", r"Sehr geehrter\b", r"Sehr geehrte\b")],
    "notatka": [("mandant", r"\bMandant\b|\bMandanten\b|\bder Mandant\b", r"\bMandantin\b")],
    "cv": [("kandidat", r"\bRechtsanwalt\b", r"\bRechtsanwältin\b")],
}


@pytest.mark.parametrize("typ", sorted(GENERO))
def test_de_rodzaj_gramatyczny_zgodny_z_plcia(typ):
    """200 budów: kobieta nigdy z formą męską, mężczyzna nigdy z żeńską (der Beklagte/die Beklagte, dem Kläger/der Klägerin…)."""
    plcie = set()
    for i in range(200):
        w, (tekst, _, _) = _buduj(typ, 2500 + i)
        for rola, meski, zenski in GENERO[typ]:
            plec = w.osoby[rola].plec
            plcie.add(plec)
            zly = re.search(meski if plec == "K" else zenski, tekst, re.I)
            assert zly is None, (typ, rola, plec, zly and tekst[max(0, zly.start() - 40):zly.end() + 30])
    assert plcie == {"M", "K"}


#: Słowa tytułu/funkcji bezpośrednio przed nazwiskiem: formy męskie / żeńskie (po usunięciu „Dr. med.” i „am …gericht”).
TYTUL_M = re.compile(r"(?:\bHerrn?|\bRechtsanwalt|\bRichter|\bZeuge|\bZeugen|\bOberarzt|\bChefarzt|\bGeschäftsführer|"
                     r"\bMandant|\bMandanten|\bFahrer|\bVersammlungsleiter|\bdes Sachverständigen|"
                     r"\bden Sachverständigen|\bFacharzt)$")
TYTUL_K = re.compile(r"(?:\bFrau|\bRechtsanwältin|\bRichterin|\bZeugin|\bOberärztin|\bChefärztin|\bGeschäftsführerin|"
                     r"\bMandantin|\bFahrerin|\bVersammlungsleiterin|\bder Sachverständigen|\bFachärztin)$")


def _przed(tekst: str, poz: int) -> str:
    przed = tekst[max(0, poz - 80):poz].rsplit("\n", 1)[-1].rstrip(" :")
    przed = re.sub(r"( am (?:Amts|Land)gericht)$", "", przed)
    przed = re.sub(r"( (?:Prof\. )?Dr\. med\.| Dr\.)+$", "", przed)
    return przed


@pytest.mark.parametrize("typ", [t for t in TYPY_DE if t != "lista_plac"])
def test_de_tytul_przed_nazwiskiem_zgodny_z_plcia(typ):
    """Każde wystąpienie imienia i nazwiska (pełnego albo samego nazwiska) ma przed sobą tytuł/funkcję w rodzaju osoby."""
    plcie = set()
    for i in range(120):
        w, (tekst, _, _) = _buduj(typ, 2900 + i)
        for rola, o in w.osoby.items():
            plcie.add(o.plec)
            niedozwolone = TYTUL_M if o.plec == "K" else TYTUL_K
            cudze = {t for r, x in w.osoby.items() if r != rola for t in (x.imie, x.nazwisko)}
            for nazwa in {o.pelne_imie} | ({o.nazwisko} - cudze):      # samo nazwisko tylko, gdy nikt inny go nie nosi
                for m in re.finditer(rf"(?<![\w-]){re.escape(nazwa)}(?![\w-])", tekst):
                    przed = _przed(tekst, m.start())
                    assert niedozwolone.search(przed) is None, (typ, rola, o.plec, przed[-40:], nazwa)
    assert plcie == {"M", "K"}


NIEGRAMATYCZNE = re.compile(
    r"\b(?:den|dem|des) Beklagte\b|\b(?:den|dem|der|die) Klägerin Klägerin\b|\b(?:den|dem) Klägerin\b|"
    r"\bdes Kläger\b|\bdie Kläger\b|\bvom (?:Klägerin|Beklagte)\b|\bzum (?:Klägerin|Beklagte)\b|"
    r"\b(?:dem|den|des) Herr\b|\bder Herrn\b|\b(?:des|dem|den) Frau\b|\bdem (?:Rechtsanwältin|Zeugin|Patientin)\b|"
    r"\bdes (?:Zeugin|Mandantin)\b|\bdie Patient\b|\bder Patient\b(?!in)(?=.*\bPatientin\b.*)")


@pytest.mark.parametrize("typ", TYPY_DE)
def test_de_bez_niegramatycznych_zbitek_rodzajnika(typ):
    """Przyimek i rodzajnik stoją razem z rodzajem osoby w gnieździe („vom Beklagten/von der Beklagten”)."""
    for i in range(200):
        _, (tekst, _, _) = _buduj(typ, 6000 + i)
        zly = NIEGRAMATYCZNE.search(tekst)
        assert zly is None, (typ, tekst[max(0, zly.start() - 50):zly.end() + 30])
        zly = re.search(r"\b(?:von|zu|bei|in|an|auf) dem (?:Beklagten|Kläger|Mandanten|Patienten|Zeugen)\b", tekst)
        assert zly is None, (typ, tekst[max(0, zly.start() - 50):zly.end() + 30])   # powinno być „vom/zum/beim”


def _sprawdz_spojnosc_sadu(w, tekst: str, wartosci) -> None:
    poziom = w.kontekst.poziom_sadu
    sygn = [x.tekst for x in wartosci if x.kategoria == "SYGNATURA" and not x.id.startswith("ctx.")]
    assert sygn and poziom in AZ, (poziom, sygn)
    for s in sygn:
        assert re.fullmatch(AZ[poziom], s), (poziom, s)
    pierwszy = re.search(r"\b((?:Amts|Land)gericht) [A-ZÄÖÜ]", tekst)
    assert pierwszy is not None and pierwszy.group(1) == ("Amtsgericht" if poziom == "amtsgericht" else "Landgericht"), tekst[:300]


@pytest.mark.parametrize("typ", ["email", "notatka", "med_zaswiadczenie"])
def test_de_numer_sprawy_zgodny_z_poziomem_sadu_w_dokumencie(typ):
    """Wyrok ma osobny test z wariantami (`test_de_wyrok_poziomy_sadow_skladow_i_sygnatur`)."""
    for i in range(200):
        w, (tekst, _, wartosci) = _buduj(typ, 3500 + i)
        _sprawdz_spojnosc_sadu(w, tekst, wartosci)


def test_de_email_daty_wg_kontekstu():
    for i in range(150):
        w, (tekst, _, wartosci) = _buduj("email", 3800 + i)
        d = w.kontekst.daty
        daty = {x.id: _data(x.tekst) for x in wartosci if x.kategoria == "DATA"}
        assert daty and set(daty.values()) <= {d["rozprawa"], d["odp_termin"]}
        assert d["pozew"] < d["odp_termin"] < d["rozprawa"]


def test_de_naglowek_wyroku_i_pozwu():
    for i in range(80):
        _, (tekst, _, _) = _buduj("wyrok", 4000 + i)
        assert re.match(r"(?:Amts|Land)gericht .+\nAktenzeichen: ", tekst)
        assert "IM NAMEN DES VOLKES\nURTEIL\nIn dem Rechtsstreit" in tekst
    for i in range(40):
        _, (tekst, _, _) = _buduj("pozew", 4100 + i)
        assert "\nKLAGE\n" in tekst and "In dem Rechtsstreit" not in tekst
        assert re.search(r"\n– (?:Klägerin|Kläger) –\n", tekst) and re.search(r"\n– (?:Beklagter|Beklagte) –\n", tekst)


def test_de_geografia_sad_i_adresy_w_jednym_miescie():
    """Sąd dokumentu leży w mieście dokumentu; adresy stron w większości w tym samym mieście; Landgericht istnieje tam."""
    from pbench.dane.de import _LG_SITZE
    zgodne = lacznie = 0
    for i in range(300):
        s = SZABLONY[("de", "wyrok")]
        g = Generator("de", 4700 + i)
        w = zbuduj_z_kontekstem(s, g, random.Random(4700 + i), "de_landgericht")
        linia = linearyzuj_z_wartosciami(w.dokument)[0].split("\n")[0]
        assert g.miasto_dok in _LG_SITZE and g.miasto_sadu == g.miasto_dok
        assert g.miasto_dok in linia or linia in ("Landgericht München I", "Landgericht Nürnberg-Fürth",
                                                  "Landgericht Halle", "Landgericht Freiburg",
                                                  "Landgericht Kempten (Allgäu)"), (linia, g.miasto_dok)
        for rola in ("klaeger", "beklagter"):
            lacznie += 1
            zgodne += w.osoby[rola].adres.miejscowosc == g.miasto_dok
    assert zgodne / lacznie >= 0.7, zgodne / lacznie


def test_de_telefon_stacjonarny_zgodny_z_miastem_adresu():
    from pbench.dane.de import _VORWAHL
    stacjonarne = 0
    for i in range(400):
        g = Generator("de", 4900 + i)
        o = g.osoba()
        nsn = str(phonenumbers.parse(o.telefon, "DE").national_number)
        if o.adres.miejscowosc in _VORWAHL and not nsn.startswith("1"):
            stacjonarne += 1
            assert nsn.startswith(_VORWAHL[o.adres.miejscowosc]), (o.adres.miejscowosc, o.telefon)
    assert stacjonarne > 30


def test_de_slownictwo_niemieckie_bez_anglicyzmow_i_obcych_form():
    for typ in TYPY_DE:
        for i in range(40):
            _, (tekst, _, _) = _buduj(typ, 5200 + i)
            assert not re.search(r"\b(?:Claimant|Defendant|Invoice|Agreement|Plaintiff|Counsel|Demandado|Actor)\b", tekst), typ


def test_de_generator_sygnatura_i_sad_wg_poziomu():
    g = Generator("de", 3)
    g.losuj_stan_dok()
    for _ in range(60):
        assert re.fullmatch(r"\d{1,2} C \d{1,4}/24", g.sygnatura(rodzaj="ag", rok=2024))
        assert re.fullmatch(r"\d{1,2} O \d{1,3}/25", g.sygnatura(rodzaj="lg", rok=2025))
        assert re.fullmatch(r"\d{1,2} S \d{1,3}/26", g.sygnatura(rodzaj="berufung", rok=2026))
        assert re.fullmatch(r"\d{1,2} [CO] \d{1,4}/\d{2}", g.sygnatura())
        assert g.sad(poziom="amtsgericht").startswith("Amtsgericht ")
        assert g.sad(poziom="landgericht").startswith("Landgericht ")
        assert g.sad(poziom="berufung").startswith("Landgericht ")
        assert re.fullmatch(r"BGH, (?:Urt\. v\.|Urteil vom|Beschl\. v\.) .+ – [IVX]+ ZR \d{1,3}/\d{2}", g.sygnatura_cytatu())
    with pytest.raises(ValueError):
        g.sad(poziom="nieznany")
    with pytest.raises(ValueError):
        g.sygnatura(rodzaj="nieznany")


def test_de_kvnr_lanr_steuernummer_i_mapowanie_kategorii():
    g = Generator("de", 5)
    assert MAPA_KATEGORII["KVNR"] == "KVNR" and MAPA_KATEGORII["LANR"] == "NR_ID"
    assert MAPA_KATEGORII["STEUERNR"] == "NR_PODATKOWY"
    for _ in range(200):
        o = g.osoba()
        kvnr, lanr = o.ids["KVNR"], o.ids["LANR"]
        assert re.fullmatch(r"[A-Z]\d{9}", kvnr) and re.fullmatch(r"\d{9}", lanr)
        cyfry = f"{ord(kvnr[0]) - 64:02d}" + kvnr[1:9]           # litera -> 01..26, potem 8 cyfr
        suma = sum(sum(divmod(int(c) * (1 if i % 2 == 0 else 2), 10)) for i, c in enumerate(cyfry))
        assert suma % 10 == int(kvnr[9])
        assert (10 - sum(int(c) * (4 if i % 2 == 0 else 9) for i, c in enumerate(lanr[:6])) % 10) % 10 == int(lanr[6])
        f = g.firma()
        assert re.fullmatch(r"\d{2,3}/\d{3,4}/\d{4,5}", f.rejestry["STEUERNR"])
    nazwy = {r: [g.firma(rodzaj=r) for _ in range(40)] for r in ("kancelaria", "placowka", "firma", "spolka")}
    assert all(re.search(r"Rechtsanwälte|Rechtsanwaltsgesellschaft", f.nazwa) and f.forma == "PartG mbB"
               for f in nazwy["kancelaria"])
    assert all(re.search(r"Klinikum|Krankenhaus|Fachklinik|Versorgungszentrum", f.nazwa) for f in nazwy["placowka"])
    assert all(f.forma == "GmbH" and f.nazwa.endswith(" GmbH") for f in nazwy["spolka"])
    assert not any(re.search(r"Rechtsanwälte|Klinikum|Krankenhaus", f.nazwa) for f in nazwy["firma"])
    assert all(f.nazwa.endswith(f.forma) for fs in nazwy.values() for f in fs)
    assert all(g.nazwa_rejestru(f.adres).startswith("Amtsgericht ") for fs in nazwy.values() for f in fs)


def test_de_kwota_i_data_styl_stalego_dokumentu():
    g = Generator("de", 1)
    d = dt.date(2024, 3, 5)
    g.styl = {"data": 0, "waluta": 0}
    assert g.formatuj_date(d) == "5. März 2024" and g._kwota_txt(1234, 5, "DE") == "1.234,05 €"
    g.styl = {"data": 1, "waluta": 1}
    assert g.formatuj_date(d) == "05.03.2024" and g._kwota_txt(1234, 5, "DE") == "1.234,05 EUR"
    g.styl = {}
    assert all(not ISO.search(g.formatuj_date(d)) for _ in range(30))


def test_de_rejestr_i_reprezentant_wg_formy_prawnej():
    """GmbH/UG/AG -> HRB, KG/OHG/e. K. -> HRA, PartG -> PR; szablony z „Geschäftsführer” używają tylko GmbH (rola spolka)."""
    g = Generator("de", 8)
    formy = set()
    for _ in range(400):
        f = g.firma()
        formy.add(f.forma)
        klucze = {k for k in f.rejestry if k in ("HRB", "HRA", "PR")}
        oczekiwany = {"GmbH": "HRB", "AG": "HRB", "UG (haftungsbeschränkt)": "HRB", "KG": "HRA", "OHG": "HRA",
                      "GmbH & Co. KG": "HRA", "e. K.": "HRA"}[f.forma]
        assert klucze == {oczekiwany} and re.fullmatch(oczekiwany + r" \d{4,6}", f.rejestry[oczekiwany]), f
    assert len(formy) >= 6
    for rodzaj, forma, rejestr in (("kancelaria", "PartG mbB", "PR"), ("placowka", None, "HRB"), ("spolka", "GmbH", "HRB")):
        for _ in range(30):
            f = g.firma(rodzaj=rodzaj)
            assert rejestr in f.rejestry and (forma is None or f.forma == forma)
    for typ in TYPY_DE:
        szablon = SZABLONY[("de", typ)]
        tresc = " ".join(b.tekst_z_gniazdami for sek in szablon.sekcje for b in sek.bloki)
        for rola in re.findall(r"\{([a-z_0-9]+)\.hrb\}", tresc):
            assert szablon.role[rola] == "spolka", (typ, rola)           # numer HRB tylko dla GmbH
        if "Geschäftsführer" in tresc and re.search(r"Handelsregister|\.hrb", tresc):
            assert "spolka" in szablon.role.values(), typ


def test_de_telefony_firm_pula_miasta_albo_zarezerwowany_numer_komorkowy():
    """Numer firmy to pula Drama miasta siedziby (030/040/069/089/0221), a dla innych miast zarezerwowany numer komórkowy."""
    from pbench.dane.de import _DRAMA, _VORWAHL
    pule = dict(_DRAMA)
    g = Generator("de", 12)
    g.losuj_stan_dok()
    for rodzaj in ("firma", "kancelaria", "placowka", "spolka"):
        for _ in range(80):
            f = g.firma(rodzaj=rodzaj)
            nsn = str(phonenumbers.parse(f.telefon, "DE").national_number)
            kier = _VORWAHL[f.adres.miejscowosc]
            if kier in pule:
                assert nsn.startswith(kier + pule[kier]), (f.adres.miejscowosc, f.telefon)
            else:
                assert nsn.startswith("1"), (f.adres.miejscowosc, f.telefon)


def test_de_poczatek_odsetek_spojny_w_tenorze_i_uzasadnieniu():
    for i in range(80):
        w, (tekst, _, wartosci) = _buduj("wyrok", 7000 + i, ("de_amtsgericht", "de_landgericht", "de_einzelrichter")[i % 3])
        d = w.kontekst.daty
        od = [_data(x.tekst) for x in wartosci if x.id.startswith("ctx.termin_wezwania")]
        assert tekst.count("seit dem " + _pole(wartosci, "termin_wezwania")) == 1     # Tenor
        assert "Verzug trat mit Ablauf der Frist am " + _pole(wartosci, "termin_wezwania") in tekst
        assert "zasadzona" not in tekst and od and d["termin_wezwania"] in od
    for i in range(80):
        w, (tekst, _, wartosci) = _buduj("pozew", 7200 + i)
        assert "Basiszinssatz seit dem " + _pole(wartosci, "termin_wezwania") in tekst


def test_de_lg_bez_pouczenia_o_srodkach_zaskarzenia_ag_z_pouczeniem():
    for i in range(80):
        _, (tekst, _, _) = _buduj("wyrok", 7400 + i, ("de_amtsgericht", "de_landgericht", "de_einzelrichter", "de_berufung")[i % 4])
        assert ("Rechtsbehelfsbelehrung" in tekst) == (i % 4 == 0)


def test_de_umowa_odpowiedzialnosc_bez_powolania_przepisow_o_sumie_ubezpieczenia():
    """Kanzlei bywa PartG mbB; nie powołujemy przepisów o minimalnej sumie ubezpieczenia, tylko kwotę umowną."""
    for i in range(60):
        _, (tekst, _, wartosci) = _buduj("umowa", 7500 + i)
        assert not re.search(r"§ 5[129]\w* ?(?:Abs\. \d )?BRAO|Mindestversicherungssumme", tekst)
        assert f"auf den Betrag von {_pole(wartosci, 'um_kara')} je Schadensfall begrenzt" in tekst


def test_de_arztbrief_narracja_spojna_z_rozpoznaniem_i_terapia():
    from pbench.dane.wspolne import slownik
    glowne = set(slownik("de", "choroby_kardiologie_glowne"))
    zakazane = re.compile(r"^(?:I26|I21|I20|I48|I47|I44)")      # PE/ACS/rytm wymagają innej narracji i leczenia
    for i in range(200):
        w, (tekst, _, wartosci) = _buduj("med_wypis", 7600 + i)
        diag = [d for d in w.encje["patient"].diagnozy if d in tekst]
        assert diag[0] in glowne and "Belastungsdyspnoe" in tekst and "Schleifendiuretika" in tekst
        assert not any(zakazane.match(d) for d in diag), diag
        assert "nach Anweisung" not in tekst
        assert len(re.findall(r" 1-0-0", tekst)) == 3
