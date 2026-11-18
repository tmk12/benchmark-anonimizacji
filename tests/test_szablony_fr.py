"""Testy szablonów FR: jedna jurysdykcja (Francja), spójność dat i kwot, poziomy sądów i numery RG, rodzaj gramatyczny
(w tym ściągnięcia przyimka z rodzajnikiem), medycyna (CIM-10, NIR, RPPS), forma prawna ↔ reprezentant, geografia."""
from __future__ import annotations

import datetime as dt
import random
import re

import phonenumbers
import pytest
from stdnum import luhn

from pbench.budowa import MAPA_KATEGORII, zbuduj_z_kontekstem
from pbench.dane import Generator
from pbench.linearyzacja import linearyzuj_z_wartosciami
from pbench.szablony import SZABLONY, TYPY

TYPY_FR = list(TYPY)
MIESIACE = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
            "novembre", "décembre"]
#: Kategorie identyfikatorów innych krajów – w dokumencie francuskim nie mogą wystąpić.
OBCE = {"PESEL", "NIP", "REGON", "KRS", "NINO", "NHS", "SSN", "EIN", "SVNR", "KVNR", "DNI", "NUSS", "CIF", "PASZPORT",
        "NR_PODATKOWY"}
#: Wyrażenia obcych krajów (waluty, formy prawne, urzędy), których nie wolno znaleźć w tekście dokumentu.
ZAKAZANE = re.compile(r"\$|£| zł\b|\bGmbH\b|\bLtd\b|\bLLC\b|\bSp\. z o\.o\.|\bUSt-IdNr\b|\bPESEL\b|\bNHS\b|\bHMRC\b|"
                      r"\bJuzgado\b|\bSąd\b|\bAmtsgericht\b|\bLandgericht\b|\bS\.L\.\B|\bNIF\b|\bCompanies House\b")
TELEFON = re.compile(r"^(?:\+33|0)[\d ]+$")
ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
RG = r"(?:RG n° |N° RG )(\d{2})/\d{5}"


def _buduj(typ: str, ziarno: int, wariant: str | None = None):
    s = SZABLONY[("fr", typ)]
    w = zbuduj_z_kontekstem(s, Generator("fr", ziarno), random.Random(ziarno), wariant)
    return w, linearyzuj_z_wartosciami(w.dokument)


def _data(tekst: str) -> dt.date:
    """Data w zapisie francuskim: „12 mars 2024”, „1er mars 2024” albo „12/03/2024”."""
    m = re.fullmatch(r"(1er|\d{1,2}) ([a-zéû]+) (\d{4})", tekst)
    if m:
        return dt.date(int(m.group(3)), MIESIACE.index(m.group(2)) + 1, 1 if m.group(1) == "1er" else int(m.group(1)))
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", tekst)
    assert m, tekst
    return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))


def _grosze(tekst: str) -> int:
    m = re.fullmatch(r"(\d{1,3}(?: \d{3})*),(\d{2}) (?:€|EUR)", tekst)
    assert m, tekst
    return int(m.group(1).replace(" ", "")) * 100 + int(m.group(2))


def _pole(wartosci, nazwa: str) -> str:
    return next(w.tekst for w in wartosci if w.id == f"ctx.{nazwa}#1")


def _sygnatura(wartosci, id_: str = "sad.sygnatura#1") -> str:
    return next(x.tekst for x in wartosci if x.id == id_)


def _rok_rg(rg: str) -> int:
    m = re.fullmatch(RG, rg)
    assert m, rg
    return 2000 + int(m.group(1))


@pytest.mark.parametrize("typ", TYPY_FR)
def test_fr_jedna_jurysdykcja_waluta_data_telefon(typ):
    """200 budów: osoby z Francji, bez identyfikatorów obcych krajów, jeden symbol waluty i jeden styl dat."""
    for i in range(200):
        w, (tekst, _, wartosci) = _buduj(typ, 300 + i)
        assert w.kontekst.kraj == "FR" and {o.kraj for o in w.osoby.values()} <= {"FR"}
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
        assert len({bool(re.fullmatch(r"\d{2}/\d{2}/\d{4}", d)) for d in daty}) <= 1, daty
        assert not ISO.search(tekst), (typ, ISO.search(tekst).group())
        zle = ZAKAZANE.search(tekst)
        assert zle is None, (typ, zle and tekst[max(0, zle.start() - 40):zle.end() + 30])


WYROK = {
    "fr_tj_unique": ("tj", {"juge1"}),
    "fr_tj_collegiale": ("tj", {"juge1", "juge2", "juge3"}),
    "fr_appel": ("appel", {"juge1", "juge2", "juge3"}),
}


def test_fr_wyrok_poziomy_sadow_skladow_i_sygnatur():
    for i in range(210):
        wariant = list(WYROK)[i % 3]
        w, (tekst, _, wartosci) = _buduj("wyrok", 700 + i, wariant)
        poziom, sedziowie = WYROK[wariant]
        k, d = w.kontekst, w.kontekst.daty
        linie = tekst.split("\n")
        assert linie[:2] == ["RÉPUBLIQUE FRANÇAISE", "AU NOM DU PEUPLE FRANÇAIS"]         # kolejność jak na pierwszej stronie
        assert re.fullmatch(r"TRIBUNAL JUDICIAIRE D.+" if poziom == "tj" else r"COUR D'APPEL D.+", linie[2]), linie[2]
        rg = _sygnatura(wartosci)
        assert w.kontekst.poziom_sadu == poziom
        assert {x.id.split(".")[0] for x in wartosci if x.id.startswith("juge")} == sedziowie, wariant
        assert re.search(r"greffi[eè]r", tekst.lower())
        assert "RÉPUBLIQUE FRANÇAISE" in linie and "AU NOM DU PEUPLE FRANÇAIS" in linie
        assert "EXPOSÉ DU LITIGE" in linie and "MOTIFS DE LA DÉCISION" in linie and "PAR CES MOTIFS" in linie
        assert _data(_pole(wartosci, "wyrok_koncowy")) == d["wyrok_koncowy"]
        assert d["rozprawa_koncowa"] < d["wyrok_koncowy"]
        assert d["umowa"] < d["termin_platnosci"] < d["wezwanie"] < d["termin_wezwania"] < d["pozew"] < d["rozprawa"]
        assert k.kwoty["zasadzona"] < k.kwoty["glowna"] and k.kwoty["glowna"] > 10_000_00
        assert _rok_rg(rg) == k.sygn_rok <= d["wyrok_koncowy"].year
        if wariant == "fr_appel":
            assert d["wyrok"] < d["apelacja"] < d["rozprawa_apel"] <= d["wyrok_apel"]
            assert k.sygn_rok == d["apelacja"].year
            pierwsza = _sygnatura(wartosci, "ctx.sygn_pierwsza#1")
            assert _rok_rg(pierwsza) == d["pozew"].year and pierwsza != rg
            assert re.search(r"Tribunal judiciaire d", tekst) and "ARRÊT" in tekst
            assert re.search(r"chambre", linie[3])
            assert "juge unique" not in tekst
        else:
            assert k.sygn_rok == d["pozew"].year
            assert "JUGEMENT" in tekst and "ARRÊT" not in tekst
            assert ("juge unique" in tekst) == (wariant == "fr_tj_unique")
            assert ("formation collégiale" in tekst) == (wariant == "fr_tj_collegiale")


def test_fr_wyrok_cytaty_to_zwykly_tekst_cassation_izba_wg_przedmiotu():
    assert SZABLONY[("fr", "wyrok")].przedmiot == "pret"
    for i in range(60):
        w, (tekst, _, wartosci) = _buduj("wyrok", 900 + i)
        assert not any(x.id.startswith("cit") for x in wartosci)
        cytaty = re.findall(r"(?:Cass\. civ\. 1re|Cass\. 1re civ\.|Civ\. 1re), (?:1er|\d{1,2}) [a-zéû]+ \d{4}, "
                            r"(?:pourvoi )?n° \d{2}-\d{2}\.\d{3}", tekst)
        assert len(cytaty) == 3, tekst[-1800:]
        assert not re.search(r"Cass\. (?:com|soc|crim)\.|Civ\. [23]e", tekst)      # pożyczka: 1re chambre civile


def test_fr_wyrok_numeracja_i_struktura():
    for i in range(150):
        wariant = list(WYROK)[i % 3]
        _, (tekst, _, _) = _buduj("wyrok", 4300 + i, wariant)
        przed, motifs, dispositif = re.split(r"\nMOTIFS DE LA DÉCISION\n|\nPAR CES MOTIFS\n", tekst)[:3]
        assert "EXPOSÉ DU LITIGE" in przed
        wiersze = [l for l in dispositif.split("\n") if l.startswith("- ")]
        assert len(wiersze) >= 4, (wariant, dispositif)
        assert any(l.startswith("- CONDAMNE") for l in wiersze) and any("article 700" in l for l in wiersze)
        assert any("aux dépens" in l for l in wiersze)
        assert (any(l.startswith("- CONFIRME") for l in wiersze)) == (wariant == "fr_appel")
        sekcje = [l for l in motifs.split("\n") if l.startswith("Sur ")]
        assert len(sekcje) >= 3, motifs


def test_fr_pozew_wezwanie_lancuch_dat_i_sumy():
    for typ in ("pozew", "wezwanie"):
        for i in range(120):
            w, (tekst, _, wartosci) = _buduj(typ, 1100 + i)
            d, k = w.kontekst.daty, w.kontekst
            assert d["umowa"] < d["termin_platnosci"] < d["wezwanie"] < d["termin_wezwania"] < d["pozew"]
            assert all(_data(x.tekst) <= d["pozew"] or (typ == "pozew" and _data(x.tekst) == d["rozprawa"])
                       for x in wartosci if x.kategoria == "DATA"), typ       # assignation podaje datę audience d'orientation
            if typ == "wezwanie":
                n = {c: _grosze(_pole(wartosci, c)) for c in ("glowna", "odsetki", "koszty_wind", "razem_wez")}
                assert n["razem_wez"] == n["glowna"] + n["odsetki"] + n["koszty_wind"]
                assert k.kwoty["ugoda_rata"] < k.kwoty["glowna"]
                assert "lettre recommandée avec demande d'avis de réception" in tekst.lower()
            else:
                assert k.wariant in ("fr_tj_unique", "fr_tj_collegiale") and k.kwoty["glowna"] > 10_000_00
                assert "ASSIGNATION" in tekst and "PLAISE AU TRIBUNAL" in tekst and "PAR CES MOTIFS" in tekst
                assert re.search(r"^TRIBUNAL JUDICIAIRE D", tekst, re.M)
                assert _data(_pole(wartosci, "pozew")) == d["pozew"]
                assert d["pozew"] < d["rozprawa"] < d["wyrok"] and _data(_pole(wartosci, "rozprawa")) == d["rozprawa"]
                assert re.search(r"article 700 du Code de procédure civile", tekst)


def test_fr_pozew_bordereau_pieces_bez_luk():
    for i in range(100):
        _, (tekst, _, _) = _buduj("pozew", 1200 + i)
        numery = [int(m.group(1)) for m in re.finditer(r"^Pièce n° (\d+) :", tekst, re.M)]
        assert numery == [1, 2, 3, 4, 5], numery


def test_fr_faktura_sumy_i_tva_20():
    for i in range(120):
        w, (tekst, _, wartosci) = _buduj("faktura", 1300 + i)
        netto = sum(_grosze(_pole(wartosci, n)) for n in ("kf1", "kf2", "kf3"))
        assert _grosze(_pole(wartosci, "netto")) == netto
        assert _grosze(_pole(wartosci, "brutto")) == netto + _grosze(_pole(wartosci, "vat"))
        assert abs(_grosze(_pole(wartosci, "vat")) - netto * 0.20) <= 1
        assert "20 %" in tekst and "TVA intracommunautaire" in tekst and "SIREN" in tekst
        assert "indemnité forfaitaire" in tekst and "40 euros" in tekst
        assert _data(_pole(wartosci, "dok_sprzedaz")) <= _data(_pole(wartosci, "dok")) <= _data(_pole(wartosci, "dok_termin_fv"))
        assert {"VAT", "SIREN", "RACHUNEK"} <= {x.kategoria for x in wartosci}
        for x in wartosci:
            if x.kategoria == "VAT":
                assert re.fullmatch(r"FR\d{2}\d{9}", x.tekst)


def test_fr_lista_plac_sumy_i_identyfikatory():
    for i in range(6):
        w, (_, _, wartosci) = _buduj("lista_plac", 1500 + i)
        wiersze = [_grosze(x.tekst) for x in wartosci if x.id.startswith("ctx.brutto_")]
        assert len(wiersze) >= 200 and _grosze(_pole(wartosci, "suma_212")) == sum(wiersze[:212])
        ids = {x.kategoria for x in wartosci if x.miejsce == "tabela"}
        assert {"NIR", "RACHUNEK", "OSOBA"} <= ids
        nir = [x.tekst for x in wartosci if x.kategoria == "NIR"]
        assert len(nir) >= 200 and all(re.fullmatch(r"[12]\d{14}", n) for n in nir)


def test_fr_med_kolejnosc_dat_rozpoznania_wg_profilu_i_plci():
    from pbench.dane.wspolne import kod_icd_plec, slownik
    plcie = set()
    for typ, profil in (("med_wypis", "cardiologie"), ("med_zaswiadczenie", "medecine_interne")):
        assert SZABLONY[("fr", typ)].profil == profil
        glowne = set(slownik("fr", f"choroby_{profil}_glowne")) if profil == "cardiologie" else set()
        choroby = set(slownik("fr", f"choroby_{profil}")) | glowne
        leki = {x.split("|")[0] for x in slownik("fr", f"leki_{profil}")}
        if profil == "cardiologie":
            leki_glowne = {x.split("|")[0] for x in slownik("fr", "leki_cardiologie_glowne")}   # diuretyk pętlowy
            leki |= leki_glowne
        for i in range(200):
            w, (tekst, _, wartosci) = _buduj(typ, 1700 + i)
            plec = w.osoby["patient"].plec
            plcie.add(plec)
            diag = [d for d in w.encje["patient"].diagnozy if d in tekst]
            meds = [d for d in w.encje["patient"].leki if d in tekst]
            assert diag and meds
            assert all(d in choroby and kod_icd_plec(d) in (None, plec) for d in diag), diag
            assert all(re.fullmatch(r"[A-Z]\d{2}(?:\.\d)? .+", d) for d in diag)
            if glowne:     # lettre de liaison dotyczy niewydolności serca: główne z puli HF, reszta współistniejące
                assert diag[0] in glowne and not set(diag[1:]) & glowne, diag
            assert all(re.match(r"(.+?) [\d,/]+ mg, ", m) and re.match(r"(.+?) [\d,/]+ mg, ", m).group(1) in leki
                       and re.search(r"\d fois par jour|jusqu'à \d fois par jour", m) for m in meds), meds
            if glowne:     # niewydolność serca: w leczeniu zawsze doustny diuretyk pętlowy
                assert any(m.startswith(("furosémide", "torasémide")) for m in meds), meds
                assert len({m.split(" ")[0] for m in meds if m.startswith(("furosémide", "torasémide"))}) == 1
            assert len(set(diag)) == len(diag) and len(set(meds)) == len(meds)
            d = w.kontekst.daty
            if typ == "med_wypis":
                assert d["przyjecie"] < d["wypis"] < d["kontrola"] and d["wypis"] <= d["zwolnienie_do"]
                assert _data(_pole(wartosci, "przyjecie")) == d["przyjecie"]
                assert w.osoby["patient"].data_ur < d["przyjecie"]
            else:
                assert d["zas_od"] < d["zas_wystaw"] < d["rozprawa"] < d["zas_do"]
            nr_id = [x.tekst for x in wartosci if x.kategoria == "NR_ID"]
            assert nr_id and all(re.fullmatch(r"10\d{9}", n) and luhn.is_valid(n) for n in nr_id), nr_id
            nir = [x.tekst for x in wartosci if x.kategoria == "NIR"]
            assert nir and all(re.fullmatch(r"[12]\d{14}", n) for n in nir), nir
            assert all((n[0] == "1") == (plec == "M") for n in nir)
    assert plcie == {"M", "K"}


def test_fr_med_zaswiadczenie_bez_surowego_kodu_w_zdaniu_i_traitement_habituel():
    for i in range(60):
        _, (tekst, _, _) = _buduj("med_zaswiadczenie", 1780 + i)
        assert "traitement habituel" in tekst.lower() and "notamment du fait de" not in tekst
        assert not re.search(r"du fait de [A-Z]\d{2}", tekst)


def test_fr_protokol_zwykla_ago_bez_zmiany_statutow_i_nominal_na_czesc():
    for i in range(60):
        w, (tekst, _, wartosci) = _buduj("protokol", 2170 + i)
        assert "statuts" not in tekst and "extraordinaires" not in tekst
        assert "six mois suivant sa clôture" in tekst
        assert _grosze(next(x.tekst for x in wartosci if x.id == "ctx.nominal#1")) == 10_00
    liczby = [m for i in range(30) for m in re.findall(r"(\d+(?: \d{3})*) parts sociales", _buduj("protokol", 2300 + i)[1][0])]
    assert any(re.fullmatch(r"\d \d{3}", x) for x in liczby) and not any(re.fullmatch(r"\d{4,}", x) for x in liczby)


def test_fr_cytaty_poza_wakacjami_sadowymi():
    from pbench.budowa import _Budowa
    for i in range(300):
        b = _Budowa(SZABLONY[("fr", "wyrok")], Generator("fr", 15000 + i), random.Random(15000 + i))
        for e in (e for e in b.encje.values() if e.rodzaj == "cytat"):
            d = e._data_cytatu()
            assert not (d.month == 8 or (d.month == 7 and d.day >= 15)) and d.weekday() < 5 and d < b.ctx.daty["wyrok_koncowy"], d


def test_fr_med_narracja_zgodna_z_rozpoznaniem():
    """Lettre de liaison: narracja i zalecenia dotyczą niewydolności serca (rozpoznanie główne z puli HF)."""
    for i in range(30):
        _, (tekst, _, _) = _buduj("med_wypis", 1750 + i)
        assert re.search(r"dyspnée|œdèmes", tekst) and re.search(r"diurétique", tekst)
        assert "CIM-10" in tekst and "lettre de liaison" in tekst.lower()


def test_fr_odpis_protokol_umowa_cv_kolejnosc_dat_i_kapital():
    """SARL: kapitał wielokrotność nominału 10 €; spółka dokumentu zawsze w formie SARL (gérant, nie président)."""
    for i in range(120):
        w, (tekst, _, wartosci) = _buduj("odpis_rejestru", 1900 + i)
        d = w.kontekst.daty
        assert d["kr_rejestracja"] <= d["kr_wpis"] <= d["dok"]
        kapital = _grosze(_pole(wartosci, "kapital2"))
        assert kapital % 10_00 == 0 and kapital >= 1_200_00
        for rola in ("gerant1", "gerant2"):
            assert w.osoby[rola].data_ur < d["kr_rejestracja"]
        firma = next(x.tekst for x in wartosci if x.id == "societe.nazwa#1")
        assert firma.endswith(" SARL"), firma
        assert "Greffe du tribunal de commerce d" in tekst and "Société à responsabilité limitée" in tekst
        assert re.search(r"R\.?C\.?S\.? [A-ZÉ]", tekst)
        gestion = next(x for x in wartosci if x.id == "ctx.nr_gestion#1")
        assert gestion.kategoria == "NR_REJESTRU"
        assert re.fullmatch(rf"{d['kr_rejestracja'].year}B\d{{5}}", gestion.tekst), gestion.tekst
        assert next(x for x in wartosci if x.id == "societe.siren#1").kategoria == "SIREN"
        assert not {x.kategoria for x in wartosci} & {"NIR", "DOWOD", "PASZPORT"}      # Kbis nie zawiera ID osób
        assert re.search(r"Gérant", tekst) and not re.search(r"Président|Directeur général", tekst)
        w, (tekst, _, wartosci) = _buduj("protokol", 2100 + i)
        u = w.kontekst.liczby
        assert w.kontekst.kwoty["kapital3"] == (u["udzialy1"] + u["udzialy2"] + u["udzialy3"]) * 10_00
        assert next(x.tekst for x in wartosci if x.id == "societe.nazwa#1").endswith(" SARL")
        assert "parts sociales" in tekst and "actions" not in tekst.lower()
        assert not re.search(r"\bPDG\b|Président-directeur|directeur général", tekst)
        w, (_, _, wartosci) = _buduj("cv", 2300 + i)
        d = w.kontekst.daty
        assert d["cv_studia"] < d["cv_od2"] < d["cv_do2"] <= d["cv_od1"]


def test_fr_protokol_numeracja_punktow_bez_luk():
    for i in range(100):
        _, (tekst, _, _) = _buduj("protokol", 2150 + i)
        numery = [int(m.group(1)) for m in re.finditer(r"^Point n° (\d+)", tekst, re.M)]
        assert numery == list(range(1, len(numery) + 1)) and len(numery) >= 8, numery


#: Forma prawna -> funkcja reprezentanta w „représentée par son/sa …” (rodzaj żeński sprowadzony do męskiego).
FUNKCJA_FORMY = {"SARL": "gérant", "EURL": "gérant", "SNC": "gérant", "SELARL": "gérant", "SAS": "président",
                 "SASU": "président", "SA": "directeur général"}
FUNKCJA_FORMA = {"gérant": "gérant", "gérante": "gérant", "président": "président", "présidente": "président",
                 "directeur général": "directeur général", "directrice générale": "directeur général"}


@pytest.mark.parametrize("typ", TYPY_FR)
def test_fr_forma_prawna_zgodna_z_reprezentantem(typ):
    """„<nazwa> <forma> … représentée par son gérant/président/directeur général” – funkcja zgodna z formą prawną."""
    wzor = re.compile(r"\b(SARL|EURL|SNC|SELARL|SASU|SAS|SA)\b[^\n]{0,260}?représentée par (?:son|sa) "
                      r"(gérant|gérante|président|présidente|directeur général|directrice générale)")
    znalezione = 0
    for i in range(120):
        _, (tekst, _, _) = _buduj(typ, 5600 + i)
        for m in wzor.finditer(tekst):
            znalezione += 1
            assert FUNKCJA_FORMY[m.group(1)] == FUNKCJA_FORMA[m.group(2)], (typ, m.group(0)[-120:])
    if typ in ("umowa", "wezwanie"):
        assert znalezione >= 100, znalezione


#: (rola, formy męskie niedopuszczalne dla kobiety, formy żeńskie niedopuszczalne dla mężczyzny) – słownictwo, które
#: w danym typie dotyczy wyłącznie tej osoby (wzorce bez rozróżniania wielkości liter, linie z `(?m)`)
DEMANDEUR = ("demandeur", r"\bdemandeur\b|\bintimé\b", r"\bdemanderesse\b|\bintimée\b")
DEFENDEUR = ("defendeur", r"\bdéfendeur\b|\bappelant\b", r"\bdéfenderesse\b|\bappelante\b")
GENERO = {
    "pozew": [DEMANDEUR, DEFENDEUR, ("avocat", r"\bavocat au\b", r"\bavocate au\b")],
    "wyrok": [DEMANDEUR, DEFENDEUR],       # avocats: forma po nazwisku sprawdza test tytułów (obaj mają „avocat au barreau”)
    "wezwanie": [("debiteur", r"(?m)^Monsieur,$|agréer, Monsieur,", r"(?m)^Madame,$|agréer, Madame,")],
    "protokol": [("president", r"\bprésident de séance\b", r"\bprésidente de séance\b")],
    "med_wypis": [("patient", r"\bné\b|\bpatient\b(?!e)", r"\bnée\b|\bpatiente\b")],
    "med_zaswiadczenie": [("patient", r"\bné\b|\bpatient\b(?!e)|\bsuivi\b|\bintéressé\b(?!e)",
                           r"\bnée\b|\bpatiente\b|\bsuivie\b|\bintéressée\b")],
    "email": [("client", r"\bCher Monsieur\b", r"\bChère Madame\b")],
    "notatka": [("client", r"\bclient\b|\bdemandeur\b", r"\bcliente\b|\bdemanderesse\b"),
                ("adversaire", r"\bdéfendeur\b", r"\bdéfenderesse\b")],
    "cv": [("candidat", r"\bné\b|\bavocat collaborateur\b|\brigoureux\b|\borienté\b|\binscrit\b|\bélève-avocat\b",
            r"\bnée\b|\bavocate collaboratrice\b|\brigoureuse\b|\borientée\b|\binscrite\b|\bélève-avocate\b")],
    "pelnomocnictwo": [("mandant", r"\bné\b|\bsoussigné\b|\binformé\b", r"\bnée\b|\bsoussignée\b|\binformée\b")],
}


@pytest.mark.parametrize("typ", sorted(GENERO))
def test_fr_rodzaj_gramatyczny_zgodny_z_plcia(typ):
    """200 budów: kobieta nigdy z formą męską, mężczyzna nigdy z żeńską (le défendeur/la défenderesse, né/née…)."""
    plcie = set()
    for i in range(200):
        w, (tekst, _, _) = _buduj(typ, 2500 + i)
        for rola, meski, zenski in GENERO[typ]:
            plec = w.osoby[rola].plec
            plcie.add(plec)
            zly = re.search(meski if plec == "K" else zenski, tekst, re.I)
            assert zly is None, (typ, rola, plec, zly and tekst[max(0, zly.start() - 50):zly.end() + 30])
    assert plcie == {"M", "K"}


#: Słowa tytułu bezpośrednio przed nazwiskiem: męskie / żeńskie.
PRZED_M = re.compile(r"(?:\bMonsieur|\bM\.|\bCher Monsieur|\bProfesseur)$")
PRZED_K = re.compile(r"(?:\bMadame|\bMme|\bChère Madame|\bProfesseure)$")
#: Pierwsze słowo po „imię nazwisko, …”: formy męskie / żeńskie.
PO_M = {"né", "avocat", "gérant", "président", "conseiller", "greffier", "associé", "domicilié", "représenté", "assigné",
        "salarié", "collaborateur", "intimé", "appelant", "demandeur", "défendeur", "vice-président", "expert-comptable",
        "chef", "suivi"}
PO_K = {"née", "avocate", "gérante", "présidente", "conseillère", "greffière", "associée", "domiciliée", "représentée",
        "assignée", "salariée", "collaboratrice", "intimée", "appelante", "demanderesse", "défenderesse", "vice-présidente",
        "experte-comptable", "cheffe", "suivie"}


def _przed(tekst: str, poz: int) -> str:
    przed = tekst[max(0, poz - 80):poz].rsplit("\n", 1)[-1].rstrip(" :")
    return re.sub(r"( (?:Docteur|Dr|Maître|Me))+$", "", przed)


@pytest.mark.parametrize("typ", [t for t in TYPY_FR if t != "lista_plac"])
def test_fr_tytul_przed_i_po_nazwisku_zgodny_z_plcia(typ):
    """Każde wystąpienie imienia i nazwiska (także z nazwiskiem wielkimi literami) ma tytuł przed nim i określenie
    funkcji/stanu po nim w rodzaju osoby."""
    plcie = set()
    for i in range(120):
        w, (tekst, _, _) = _buduj(typ, 2900 + i)
        for rola, o in w.osoby.items():
            plcie.add(o.plec)
            zle_przed = PRZED_M if o.plec == "K" else PRZED_K
            zle_po = PO_M if o.plec == "K" else PO_K
            cudze = {t for r, x in w.osoby.items() if r != rola for t in (x.imie, x.nazwisko)}
            formy = {o.pelne_imie, f"{o.imie} {o.nazwisko.upper()}"} | ({o.nazwisko} - cudze)
            for nazwa in formy:
                for m in re.finditer(rf"(?<![\w-]){re.escape(nazwa)}(?![\w-])", tekst):
                    przed = _przed(tekst, m.start())
                    assert zle_przed.search(przed) is None, (typ, rola, o.plec, przed[-40:], nazwa)
                    po = re.match(r"[,(]\s*([\w'’-]+)", tekst[m.end():m.end() + 40])
                    assert po is None or po.group(1) not in zle_po, (typ, rola, o.plec, nazwa, po and po.group(1))
    assert plcie == {"M", "K"}


ROLE_PL = r"demandeur|demanderesse|défendeur|défenderesse|appelant|appelante|intimé|intimée|avocat|avocate|gérant|gérante|" \
          r"associé|associée|président|présidente|conseiller|conseillère|greffier|greffière|débiteur|débitrice"
MESKIE = r"demandeur|défendeur|appelant|intimé|avocat|gérant|associé|président|conseiller|greffier|débiteur"
ZENSKIE = r"demanderesse|défenderesse|appelante|intimée|avocate|gérante|associée|présidente|conseillère|greffière|débitrice"
NIEGRAMATYCZNE = re.compile(
    r"\b(?:à|de) (?:le|les) (?!\s)\w|\bde un\b|\b(?:du|au|le|un|ce) (?:" + ZENSKIE + r")\b|"
    r"\b(?:la|une|cette) (?:" + MESKIE + r")\b|\b(?:de la|à la) (?:" + MESKIE + r")\b|"
    r"\b(?:le|la|du|au|de la|à la) (?:le|la|du|au)\b|\bMonsieur Madame\b|\bMadame Monsieur\b|"
    r"\b(?:Cher|Chère) (?:Madame|Monsieur) (?:Madame|Monsieur)\b|\b(?:de|d') (?:de|d')\b")


@pytest.mark.parametrize("typ", TYPY_FR)
def test_fr_bez_niegramatycznych_zbitek_rodzajnika(typ):
    """Przyimek i rodzajnik stoją razem z rodzajem osoby w gnieździe („au défendeur/à la défenderesse”)."""
    for i in range(200):
        _, (tekst, _, _) = _buduj(typ, 6000 + i)
        zly = NIEGRAMATYCZNE.search(tekst)
        assert zly is None, (typ, tekst[max(0, zly.start() - 50):zly.end() + 30])
        zly = re.search(r"\b(?:à le|de le|à les|de les)\b", tekst)
        assert zly is None, (typ, tekst[max(0, zly.start() - 50):zly.end() + 30])


def _sprawdz_spojnosc_sadu(w, tekst: str, wartosci) -> None:
    sygn = [x.tekst for x in wartosci if x.kategoria == "SYGNATURA" and not x.id.startswith("ctx.")]
    assert sygn and w.kontekst.poziom_sadu == "tj", sygn
    for s in sygn:
        assert re.fullmatch(RG, s), s
        assert _rok_rg(s) == w.kontekst.sygn_rok
    assert re.search(r"[Tt]ribunal judiciaire d", tekst) and "Cour d'appel" not in tekst, tekst[:300]


@pytest.mark.parametrize("typ", ["email", "notatka", "med_zaswiadczenie"])
def test_fr_numer_sprawy_zgodny_z_poziomem_sadu_w_dokumencie(typ):
    """Wyrok ma osobny test z wariantami (`test_fr_wyrok_poziomy_sadow_skladow_i_sygnatur`)."""
    for i in range(200):
        w, (tekst, _, wartosci) = _buduj(typ, 3500 + i)
        _sprawdz_spojnosc_sadu(w, tekst, wartosci)


def test_fr_email_daty_wg_kontekstu():
    for i in range(150):
        w, (tekst, _, wartosci) = _buduj("email", 3800 + i)
        d = w.kontekst.daty
        daty = {x.id: _data(x.tekst) for x in wartosci if x.kategoria == "DATA"}
        assert daty and set(daty.values()) <= {d["rozprawa"], d["odp_termin"]}
        assert d["pozew"] < d["odp_termin"] < d["rozprawa"]


def test_fr_naglowek_wyroku_i_pozwu():
    for i in range(80):
        _, (tekst, _, _) = _buduj("wyrok", 4000 + i)
        assert re.match(r"RÉPUBLIQUE FRANÇAISE\nAU NOM DU PEUPLE FRANÇAIS\n(?:TRIBUNAL JUDICIAIRE|COUR D'APPEL) D.+\n", tekst)
    for i in range(40):
        _, (tekst, _, _) = _buduj("pozew", 4100 + i)
        assert "À LA REQUÊTE DE" in tekst and "DONNÉ ASSIGNATION À" in tekst
        assert re.search(r"\nPLAISE AU TRIBUNAL\n", tekst)
        assert re.search(r"commissaire de justice", tekst)


def test_fr_geografia_sad_i_adresy_w_jednym_miescie():
    """Sąd dokumentu leży w mieście dokumentu (siedziba cour d'appel); adresy stron w większości w tym mieście."""
    from pbench.dane.fr import _VILLES_CA
    zgodne = lacznie = 0
    for i in range(300):
        s = SZABLONY[("fr", "wyrok")]
        g = Generator("fr", 4700 + i)
        w = zbuduj_z_kontekstem(s, g, random.Random(4700 + i), "fr_tj_collegiale")
        linia = linearyzuj_z_wartosciami(w.dokument)[0].split("\n")[2]
        assert g.miasto_dok in _VILLES_CA and g.miasto_sadu == g.miasto_dok
        assert g.miasto_dok.upper() in linia, (linia, g.miasto_dok)
        for rola in ("demandeur", "defendeur"):
            lacznie += 1
            zgodne += w.osoby[rola].adres.miejscowosc == g.miasto_dok
    assert zgodne / lacznie >= 0.7, zgodne / lacznie


def test_fr_telefon_stacjonarny_zgodny_z_regionem_adresu():
    from pbench.dane.fr import _PREFIKS_DEPT
    stacjonarne = 0
    for i in range(500):
        g = Generator("fr", 4900 + i)
        o = g.osoba()
        nsn = str(phonenumbers.parse(o.telefon, "FR").national_number)
        dept = o.adres.kod[:2]
        if nsn[0] in "12345":
            stacjonarne += 1
            assert nsn[0] == _PREFIKS_DEPT[dept], (o.adres.linia(), o.telefon)
            if nsn.startswith("199"):                    # pula ARCEP 01 99 00 xx xx: tylko Île-de-France
                assert _PREFIKS_DEPT[dept] == "1"
    assert stacjonarne > 100


def test_fr_slownictwo_francuskie_bez_anglicyzmow_i_obcych_form():
    for typ in TYPY_FR:
        for i in range(40):
            _, (tekst, _, _) = _buduj(typ, 5200 + i)
            assert not re.search(r"\b(?:Claimant|Defendant|Invoice|Agreement|Plaintiff|Counsel|Demandado|Actor|"
                                 r"Kläger|Beklagte|Rechtsanwalt|Vertrag)\b", tekst), typ


def test_fr_generator_sygnatura_i_sad_wg_poziomu():
    g = Generator("fr", 3)
    g.losuj_stan_dok()
    for _ in range(60):
        assert re.fullmatch(r"(?:RG n° |N° RG )24/\d{5}", g.sygnatura(rodzaj="tj", rok=2024))
        assert re.fullmatch(r"(?:RG n° |N° RG )25/\d{5}", g.sygnatura(rodzaj="appel", rok=2025))
        assert re.fullmatch(RG, g.sygnatura())
        assert g.sad(poziom="tj").startswith("Tribunal judiciaire d")
        assert g.sad(poziom="appel").startswith("Cour d'appel d")
        assert g.miasto_sadu == g.miasto_dok
        assert re.fullmatch(r"(?:Cass\. civ\. 1re|Cass\. 1re civ\.|Civ\. 1re|Cass\. com\.|Cass\. civ\. [23]e|"
                            r"Cass\. soc\.|Com\.|Soc\.|Cass\. [23]e civ\.|Civ\. [23]e), (?:1er|\d{1,2}) [a-zéû]+ \d{4}, "
                            r"(?:pourvoi )?n° \d{2}-\d{2}\.\d{3}", g.sygnatura_cytatu())
    with pytest.raises(ValueError):
        g.sad(poziom="nieznany")
    with pytest.raises(ValueError):
        g.sygnatura(rodzaj="nieznany")


def test_fr_cytat_izba_wg_przedmiotu_i_rok_pourvoi():
    g = Generator("fr", 5)
    for przedmiot, izba in (("pret", "1re"), ("accident", "2e"), ("bail", "3e")):
        for _ in range(40):
            s = g.sygnatura_cytatu(data=dt.date(2024, 5, 6), przedmiot=przedmiot)
            m = re.search(r"civ\. (\d)e?|(\d)(?:re|e) civ\.|Civ\. (\d)(?:re|e)", s)
            assert izba in s and m, s
            assert re.search(r"n° (22|23)-\d{2}\.\d{3}$", s) and "6 mai 2024" in s, s
    for przedmiot in ("societe", "travail"):
        assert all(("com." in s or "Com." in s) if przedmiot == "societe" else ("soc." in s or "Soc." in s)
                   for s in (g.sygnatura_cytatu(data=dt.date(2024, 5, 6), przedmiot=przedmiot) for _ in range(30)))


def test_fr_rpps_nir_siren_i_mapowanie_kategorii():
    g = Generator("fr", 5)
    assert MAPA_KATEGORII["RPPS"] == "NR_ID" and MAPA_KATEGORII["SIRET"] == "SIREN"
    for _ in range(200):
        o = g.osoba()
        assert re.fullmatch(r"10\d{9}", o.ids["RPPS"]) and luhn.is_valid(o.ids["RPPS"])
    nazwy = {r: [g.firma(rodzaj=r) for _ in range(40)] for r in ("kancelaria", "placowka", "firma", "spolka")}
    assert all(f.forma == "SELARL" and f.nazwa.startswith("SELARL ") and "Avocats" in f.nazwa
               for f in nazwy["kancelaria"])
    assert all(re.match(r"(?:Clinique|Polyclinique|Hôpital privé|Centre hospitalier privé) ", f.nazwa) and
               f.forma in ("SAS", "SA") and f.nazwa.endswith(f.forma) for f in nazwy["placowka"])
    assert all(f.forma == "SARL" and f.nazwa.endswith(" SARL") for f in nazwy["spolka"])
    assert not any(re.search(r"SELARL|Clinique|Hôpital", f.nazwa) for f in nazwy["firma"])
    for fs in nazwy.values():
        for f in fs:
            assert g.nazwa_rejestru(f.adres).startswith("tribunal de commerce d")
            assert g.rcs(f.adres) == f"RCS {f.adres.miejscowosc}"
            assert f.adres.miejscowosc in __import__("pbench.dane.fr", fromlist=["_VILLES_TC"])._VILLES_TC


def test_fr_kwota_i_data_styl_stalego_dokumentu():
    g = Generator("fr", 1)
    d = dt.date(2024, 3, 5)
    g.styl = {"data": 0, "waluta": 0}
    assert g.formatuj_date(d) == "5 mars 2024" and g._kwota_txt(1234, 5, "FR") == "1 234,05 €"
    assert g.formatuj_date(dt.date(2024, 3, 1)) == "1er mars 2024"
    g.styl = {"data": 1, "waluta": 1}
    assert g.formatuj_date(d) == "05/03/2024" and g._kwota_txt(1234, 5, "FR") == "1 234,05 EUR"
    g.styl = {}


def test_fr_dane_pomocnicze_kontekstu_fr():
    """Nominał udziału SARL 10 €, ctx.nr_gestion, rok sygnatury i `sygn_pierwsza` w apelacji."""
    from pbench.budowa import NOMINAL_UDZIALU
    assert NOMINAL_UDZIALU["FR"] == 10_00
    for i in range(40):
        w, (_, _, wartosci) = _buduj("wyrok", 7000 + i, "fr_appel")
        assert w.kontekst.sygn_rok == w.kontekst.daty["apelacja"].year
        assert re.fullmatch(RG, _sygnatura(wartosci, "ctx.sygn_pierwsza#1"))
