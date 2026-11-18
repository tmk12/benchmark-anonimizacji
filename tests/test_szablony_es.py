"""Testy szablonów ES: jedna jurysdykcja (Hiszpania), spójność dat i kwot, poziomy sądów, rodzaj gramatyczny, medycyna."""
from __future__ import annotations

import datetime as dt
import random
import re

import pytest

from pbench.budowa import zbuduj_z_kontekstem
from pbench.dane import Generator
from pbench.linearyzacja import linearyzuj_z_wartosciami
from pbench.szablony import SZABLONY, TYPY

TYPY_ES = list(TYPY)
MIESIACE = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
            "noviembre", "diciembre"]
#: Kategorie identyfikatorów innych krajów – w dokumencie hiszpańskim nie mogą wystąpić.
OBCE = {"PESEL", "NIP", "REGON", "KRS", "NINO", "NHS", "SSN", "EIN", "NR_PODATKOWY", "SVNR", "NIR", "SIREN", "DOWOD",
        "PASZPORT"}
#: Wyrażenia obcych krajów (waluty, formy prawne, urzędy), których nie wolno znaleźć w tekście dokumentu.
ZAKAZANE = re.compile(r"\$|£| zł\b|\bGmbH\b|\bSARL\b|\bLtd\b|\bLLC\b|\bSp\. z o\.o\.|\bSIRET\b|\bPESEL\b|\bNHS\b|"
                      r"\bHMRC\b|\bFinanzamt\b|\bURSSAF\b|\bSąd\b")
TELEFON = re.compile(r"^(?:\+34)?[\d ]+$")
ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def _buduj(typ: str, ziarno: int, wariant: str | None = None):
    s = SZABLONY[("es", typ)]
    w = zbuduj_z_kontekstem(s, Generator("es", ziarno), random.Random(ziarno), wariant)
    return w, linearyzuj_z_wartosciami(w.dokument)


def _data(tekst: str) -> dt.date:
    """Data w zapisie hiszpańskim: „12 de marzo de 2024” albo „12/03/2024”."""
    m = re.fullmatch(r"(\d{1,2}) de ([a-z]+) de (\d{4})", tekst)
    if m:
        return dt.date(int(m.group(3)), MIESIACE.index(m.group(2)) + 1, int(m.group(1)))
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", tekst)
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


@pytest.mark.parametrize("typ", TYPY_ES)
def test_es_jedna_jurysdykcja_waluta_data_telefon(typ):
    """200 budów: osoby z Hiszpanii, bez identyfikatorów obcych krajów, jeden symbol waluty i jeden styl dat."""
    for i in range(200):
        w, (tekst, _, wartosci) = _buduj(typ, 300 + i)
        assert w.kontekst.kraj == "ES" and {o.kraj for o in w.osoby.values()} <= {"ES"}
        assert not {x.kategoria for x in wartosci} & OBCE
        symbole = {x.tekst.rsplit(" ", 1)[1] for x in wartosci if x.kategoria == "KWOTA"}
        assert len(symbole) <= 1 and symbole <= {"€", "EUR"}, (typ, symbole)
        for x in wartosci:
            if x.kategoria == "TELEFON":
                assert TELEFON.match(x.tekst), (typ, x.tekst)
        daty = [x.tekst for x in wartosci if x.kategoria in ("DATA", "DATA_UR")]
        for d in daty:
            _data(d)
        assert len({bool(re.fullmatch(r"\d{2}/\d{2}/\d{4}", d)) for d in daty}) <= 1, daty
        assert not ISO.search(tekst), (typ, ISO.search(tekst).group())
        zle = ZAKAZANE.search(tekst)
        assert zle is None, (typ, zle and tekst[max(0, zle.start() - 40):zle.end() + 30])


def test_es_wyrok_poziomy_sadow_skladow_i_sygnatur():
    wzory = {"es_primera": (r"JUZGADO DE PRIMERA INSTANCIA(?: E INSTRUCCIÓN)? N\.º \d+ DE .+",
                            r"Procedimiento Ordinario n\.º \d{1,4}/\d{4}", {"juez1"}),
             "es_apelacion": (r"AUDIENCIA PROVINCIAL DE .+, SECCIÓN \d+\.ª", r"Rollo de Apelación n\.º \d{1,4}/\d{4}",
                              {"juez1", "juez2", "juez3"})}
    for i in range(200):
        wariant = list(wzory)[i % 2]
        w, (tekst, _, wartosci) = _buduj("wyrok", 700 + i, wariant)
        sad, sygn, sedziowie = wzory[wariant]
        k, d = w.kontekst, w.kontekst.daty
        assert re.fullmatch(sad, tekst.split("\n")[0]), tekst.split("\n")[0]
        assert re.fullmatch(sygn, _sygnatura(wartosci))
        assert {x.id.split(".")[0] for x in wartosci if x.id.startswith("juez")} == sedziowie, wariant
        assert _data(_pole(wartosci, "wyrok_koncowy")) == d["wyrok_koncowy"]
        assert d["rozprawa_koncowa"] <= d["wyrok_koncowy"]
        assert d["umowa"] < d["termin_platnosci"] < d["wezwanie"] < d["termin_wezwania"] < d["pozew"] < d["rozprawa"]
        assert k.kwoty["zasadzona"] < k.kwoty["glowna"] and k.kwoty["glowna"] > 6000_00
        rok = int(_sygnatura(wartosci)[-4:])
        assert rok == k.sygn_rok <= d["wyrok_koncowy"].year
        if wariant == "es_apelacion":
            assert d["wyrok"] < d["apelacja"] < d["rozprawa_apel"] <= d["wyrok_apel"]
            assert rok == d["apelacja"].year and k.kwoty["koszty_apel"] < k.kwoty["glowna"]
            # w apelacji: wskazane postępowanie pierwszej instancji (inny sąd, rok wniesienia pozwu)
            pierwsza = _sygnatura(wartosci, "ctx.sygn_pierwsza#1")
            assert re.fullmatch(r"Procedimiento Ordinario n\.º \d{1,4}/\d{4}", pierwsza)
            assert int(pierwsza[-4:]) == d["pozew"].year
            assert re.search(r"Juzgado de Primera Instancia(?: e Instrucción)? n\.º \d+ de ", tekst)
        else:
            assert rok == d["pozew"].year


def test_es_wyrok_ordinales_bez_luk_w_kazdej_czesci():
    ordinales = ["PRIMERO", "SEGUNDO", "TERCERO", "CUARTO", "QUINTO", "SEXTO", "SÉPTIMO", "OCTAVO"]
    for i in range(160):
        wariant = ("es_primera", "es_apelacion")[i % 2]
        _, (tekst, _, _) = _buduj("wyrok", 4300 + i, wariant)
        serie, biezaca = [], []
        for linia in tekst.split("\n"):
            m = re.match(r"([A-ZÁÉÍÓÚ]+)\.- ", linia)
            if m:
                if m.group(1) == "PRIMERO" and biezaca:
                    serie.append(biezaca)
                    biezaca = []
                biezaca.append(m.group(1))
        serie.append(biezaca)
        assert len(serie) == 2, (wariant, serie)                      # ANTECEDENTES i FUNDAMENTOS
        for s in serie:
            assert s == ordinales[:len(s)] and len(s) >= 3, s
        assert "ANTECEDENTES DE HECHO" in tekst and "FUNDAMENTOS DE DERECHO" in tekst and "FALLO" in tekst


def test_es_wyrok_cytaty_to_zwykly_tekst_sts():
    for i in range(60):
        w, (tekst, _, wartosci) = _buduj("wyrok", 900 + i)
        assert not any(x.id.startswith("cita") for x in wartosci)
        assert re.search(r"STS \d{1,4}/(?:19|20)\d{2}|Sentencia del Tribunal Supremo", tekst), tekst[:200]
        assert re.search(r"ECLI:ES:TS:(?:19|20)\d{2}:\d{1,5}", tekst)


def test_es_pozew_wezwanie_lancuch_dat_i_sumy():
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
                assert k.wariant == "es_primera" and k.kwoty["glowna"] > 6000_00      # juicio ordinario: > 6.000 €
                assert re.search(r"JUZGADO DE PRIMERA INSTANCIA", tekst) and "AUDIENCIA PROVINCIAL" not in tekst
                assert _data(_pole(wartosci, "pozew")) == d["pozew"]


def test_es_faktura_sumy_i_iva_21():
    for i in range(120):
        w, (tekst, _, wartosci) = _buduj("faktura", 1300 + i)
        netto = sum(_grosze(_pole(wartosci, n)) for n in ("kf1", "kf2", "kf3"))
        assert _grosze(_pole(wartosci, "netto")) == netto
        assert _grosze(_pole(wartosci, "brutto")) == netto + _grosze(_pole(wartosci, "vat"))
        assert abs(_grosze(_pole(wartosci, "vat")) - netto * 0.21) <= 1
        assert "21 %" in tekst and "IVA" in tekst
        assert _data(_pole(wartosci, "dok_sprzedaz")) <= _data(_pole(wartosci, "dok")) <= _data(_pole(wartosci, "dok_termin_fv"))
        kategorie = {x.kategoria for x in wartosci}
        assert {"CIF", "VAT"} <= kategorie


def test_es_lista_plac_sumy_i_identyfikatory():
    for i in range(6):
        w, (_, _, wartosci) = _buduj("lista_plac", 1500 + i)
        wiersze = [_grosze(x.tekst) for x in wartosci if x.id.startswith("ctx.brutto_")]
        assert len(wiersze) >= 200 and _grosze(_pole(wartosci, "suma_212")) == sum(wiersze[:212])
        ids = {x.kategoria for x in wartosci if x.miejsce == "tabela"}
        assert {"DNI", "NUSS", "RACHUNEK"} <= ids


def test_es_med_kolejnosc_dat_rozpoznania_wg_profilu_i_plci():
    from pbench.dane.wspolne import kod_icd_plec, slownik
    plcie = set()
    for typ, profil in (("med_wypis", "cardiologia"), ("med_zaswiadczenie", "interna")):
        assert SZABLONY[("es", typ)].profil == profil
        choroby = set(slownik("es", f"choroby_{profil}"))
        leki = {x.split("|")[0] for x in slownik("es", f"leki_{profil}")}
        for i in range(200):
            w, (tekst, _, wartosci) = _buduj(typ, 1700 + i)
            plec = w.osoby["paciente"].plec
            plcie.add(plec)
            diag = [d for d in w.encje["paciente"].diagnozy if d in tekst]
            meds = [d for d in w.encje["paciente"].leki if d in tekst]
            assert diag and meds
            assert all(d in choroby and kod_icd_plec(d) in (None, plec) for d in diag), diag
            assert all(m.rsplit(" ", 2)[0] in leki for m in meds), meds
            assert len(set(diag)) == len(diag) and len(set(meds)) == len(meds)
            d = w.kontekst.daty
            if typ == "med_wypis":
                assert d["przyjecie"] < d["wypis"] < d["kontrola"] and d["wypis"] <= d["zwolnienie_do"]
                assert _data(_pole(wartosci, "przyjecie")) == d["przyjecie"]
                assert w.osoby["paciente"].data_ur < d["przyjecie"]
            else:
                assert d["zas_od"] < d["zas_wystaw"] < d["rozprawa"] < d["zas_do"]
            nr_id = [x.tekst for x in wartosci if x.kategoria == "NR_ID"]
            assert nr_id and all(re.fullmatch(r"(?:0[1-9]|[1-4]\d|5[0-2])\d{7}", n) for n in nr_id), nr_id
    assert plcie == {"M", "K"}


def test_es_odpis_protokol_cv_kolejnosc_dat_i_kapital():
    """S.L. – kapitał >= 3.000 € (obecne minimum ustawowe to 1 €, Ley 18/2022; benchmark trzyma się wyższych,
    realistycznych kwot), wielokrotność nominału 50 €; spółka dokumentu w formie S.L."""
    for i in range(120):
        w, (tekst, _, wartosci) = _buduj("odpis_rejestru", 1900 + i)
        d = w.kontekst.daty
        assert d["kr_rejestracja"] <= d["kr_wpis"] <= d["dok"]
        kapital = _grosze(_pole(wartosci, "kapital2"))
        assert kapital >= 3000_00 and kapital % 50_00 == 0
        assert w.osoby["administrador1"].data_ur < d["kr_rejestracja"]
        firma = next(x.tekst for x in wartosci if x.id == "sociedad.nazwa#1")
        assert firma.endswith("S.L."), firma
        assert re.search(r"Registro Mercantil de [A-ZÁÉÍÓÚ]", tekst)
        assert next(x for x in wartosci if x.id == "sociedad.company_no#1").kategoria == "NR_REJESTRU"
        w, (tekst, _, wartosci) = _buduj("protokol", 2100 + i)
        u = w.kontekst.liczby
        assert w.kontekst.kwoty["kapital3"] == (u["udzialy1"] + u["udzialy2"] + u["udzialy3"]) * 50_00
        assert next(x.tekst for x in wartosci if x.id == "sociedad.nazwa#1").endswith("S.L.")
        assert "participaciones" in tekst and "acciones" not in tekst.lower()
        w, (_, _, wartosci) = _buduj("cv", 2300 + i)
        d = w.kontekst.daty
        assert d["cv_studia"] < d["cv_od2"] < d["cv_do2"] <= d["cv_od1"]


GENERO = {
    "pozew": [("actor", r"\bel actor\b", r"\bla actora\b"), ("demandado", r"\bdemandado\b", r"\bdemandada\b")],
    "wyrok": [("actor", r"\bel actor\b", r"\bla actora\b"), ("demandado", r"\bdemandado\b", r"\bdemandada\b")],
    "wezwanie": [("deudor", r"\bdeudor\b", r"\bdeudora\b")],
    "pelnomocnictwo": [("poderdante", r"\bel compareciente\b", r"\bla compareciente\b"),
                       ("apoderado1", r"\bapoderado\b|\bel Letrado\b", r"\bapoderada\b|\bla Letrada\b")],
    "med_wypis": [("paciente", r"\b(?:el paciente|nacido|ingresado|dado de alta)\b",
                   r"\b(?:la paciente|nacida|ingresada|dada de alta)\b")],
    "med_zaswiadczenie": [("paciente", r"\b(?:el paciente|nacido|ingresado)\b", r"\b(?:la paciente|nacida|ingresada)\b")],
    "email": [("cliente", r"\bestimado\b|\bel cliente\b", r"\bestimada\b|\bla cliente\b")],
    "notatka": [("cliente", r"\bel cliente\b", r"\bla cliente\b|\bla clienta\b")],
    "cv": [("candidato", r"\bnacido\b", r"\bnacida\b")],
}


@pytest.mark.parametrize("typ", sorted(GENERO))
def test_es_rodzaj_gramatyczny_zgodny_z_plcia(typ):
    """200 budów: kobieta nigdy z formą męską, mężczyzna nigdy z żeńską (demandado/demandada, el actor/la actora…)."""
    plcie = set()
    for i in range(200):
        w, (tekst, _, _) = _buduj(typ, 2500 + i)
        for rola, meski, zenski in GENERO[typ]:
            plec = w.osoby[rola].plec
            plcie.add(plec)
            zly = re.search(meski if plec == "K" else zenski, tekst, re.I)
            assert zly is None, (typ, rola, plec, zly and tekst[max(0, zly.start() - 40):zly.end() + 30])
    assert plcie == {"M", "K"}


def _sprawdz_spojnosc_sadu(tekst: str, wartosci) -> None:
    sygn = [x.tekst for x in wartosci if x.kategoria == "SYGNATURA" and not x.id.startswith("ctx.")]
    t = tekst.lower()
    for s in sygn:
        if s.startswith("Rollo de Apelación"):
            assert "audiencia provincial" in t, s
        elif s.startswith("Procedimiento Ordinario"):
            assert "juzgado de primera instancia" in t and "audiencia provincial de" not in t.split("\n")[0], s
        else:                                       # sprawa poboczna (np. monitorio, conciliación) – dowolny juzgado I inst.
            assert re.fullmatch(r"[^\d/]+ n\.º \d{1,4}/\d{4}", s), s


@pytest.mark.parametrize("typ", ["pozew", "wyrok", "email", "notatka", "med_zaswiadczenie", "wezwanie"])
def test_es_numer_sprawy_zgodny_z_poziomem_sadu_w_dokumencie(typ):
    for i in range(200):
        w, (tekst, _, wartosci) = _buduj(typ, 3500 + i)
        if not any(x.kategoria == "SYGNATURA" for x in wartosci):
            continue
        _sprawdz_spojnosc_sadu(tekst, wartosci)


def test_es_email_daty_wg_kontekstu():
    for i in range(150):
        w, (tekst, _, wartosci) = _buduj("email", 3800 + i)
        d = w.kontekst.daty
        daty = {x.id: _data(x.tekst) for x in wartosci if x.kategoria == "DATA"}
        assert daty and set(daty.values()) <= {d["rozprawa"], d["odp_termin"]}
        assert d["pozew"] < d["odp_termin"] < d["rozprawa"]


def test_es_naglowek_sadu_wielkimi_literami():
    for i in range(80):
        _, (tekst, _, _) = _buduj("wyrok", 4000 + i)
        pierwsza = tekst.split("\n")[0]
        assert pierwsza == pierwsza.upper() and re.match(r"JUZGADO|AUDIENCIA", pierwsza), pierwsza
    for i in range(40):
        _, (tekst, _, _) = _buduj("pozew", 4100 + i)
        assert any(l == l.upper() and "JUZGADO" in l for l in tekst.split("\n")[:5])


def test_es_geografia_sad_adresy_w_jednej_prowincji():
    """Sąd dokumentu leży w prowincji dokumentu; adresy stron w większości z tej samej prowincji (kod pocztowy)."""
    from pbench.dane.es import PROVINCIAS
    zgodne = lacznie = 0
    for i in range(300):
        s = SZABLONY[("es", "wyrok")]
        g = Generator("es", 4700 + i)
        w = zbuduj_z_kontekstem(s, g, random.Random(4700 + i), "es_primera")
        linia = linearyzuj_z_wartosciami(w.dokument)[0].split("\n")[0]
        prow = g.prov_dok
        assert any(linia.endswith(" DE " + m.upper()) for m in g.miasta_prowincji(prow)), (linia, prow)
        assert prow in PROVINCIAS
        for rola in ("actor", "demandado"):
            lacznie += 1
            zgodne += w.osoby[rola].adres.kod[:2] == prow
    assert zgodne / lacznie >= 0.7, zgodne / lacznie


def test_es_telefon_stacjonarny_zgodny_z_prowincja_adresu():
    from pbench.dane.es import PREFIKSY_TEL
    for i in range(300):
        g = Generator("es", 4900 + i)
        o = g.osoba()
        cyfry = re.sub(r"\D", "", o.telefon)
        cyfry = cyfry[2:] if cyfry.startswith("34") and len(cyfry) == 11 else cyfry
        if cyfry[0] == "9":
            assert cyfry.startswith(PREFIKSY_TEL[o.adres.kod[:2]]), (o.adres.kod, o.telefon)


def test_es_slownictwo_hiszpanskie_bez_katalanizmow_i_anglicyzmow():
    for typ in TYPY_ES:
        for i in range(40):
            _, (tekst, _, _) = _buduj(typ, 5200 + i)
            assert not re.search(r"\b(?:Claimant|Defendant|Invoice|Agreement|Plaintiff|Counsel)\b", tekst), typ


def test_es_generator_sygnatura_i_sad_wg_poziomu():
    g = Generator("es", 3)
    for _ in range(60):
        assert re.fullmatch(r"Procedimiento Ordinario n\.º \d{1,4}/2024", g.sygnatura(rodzaj="ordinario", rok=2024))
        assert re.fullmatch(r"Rollo de Apelación n\.º \d{1,4}/2025", g.sygnatura(rodzaj="apelacion", rok=2025))
        assert re.fullmatch(r"Juzgado de Primera Instancia(?: e Instrucción)? n\.º \d+ de .+", g.sad(poziom="primera"))
        assert re.fullmatch(r"Audiencia Provincial de .+, Sección \d+\.ª", g.sad(poziom="apelacion"))
        assert "Rollo" not in g.sygnatura()
    with pytest.raises(ValueError):
        g.sad(poziom="nieznany")
    with pytest.raises(ValueError):
        g.sygnatura(rodzaj="nieznany")


def test_es_colegiado_i_registro_mercantil():
    from pbench.budowa import MAPA_KATEGORII
    g = Generator("es", 5)
    assert MAPA_KATEGORII["COLEGIADO"] == "NR_ID"
    for _ in range(100):
        assert re.fullmatch(r"(?:0[1-9]|[1-4]\d|5[0-2])\d{7}", g.osoba().ids["COLEGIADO"])
        f = g.firma()
        assert re.fullmatch(r"[A-Z]{1,2}-\d{5,6}", f.rejestry["COMPANY_NO"])
        assert f.rejestry["COMPANY_NO"] == f.rejestry["COMPANY_NO"].upper()
    nazwy = {r: [g.firma(rodzaj=r) for _ in range(40)] for r in ("kancelaria", "placowka", "firma", "spolka")}
    assert all(re.search(r"Abogados|Bufete|Asesores|Letrados", f.nazwa) and f.forma == "S.L.P." for f in nazwy["kancelaria"])
    assert all(re.search(r"Hospital|Clínica|Centro Médico", f.nazwa) for f in nazwy["placowka"])
    assert all(f.forma == "S.L." and f.nazwa.endswith("S.L.") for f in nazwy["spolka"])
    assert not any(re.search(r"Abogados|Hospital|Clínica(?! Dental)|Bufete", f.nazwa) for f in nazwy["firma"])    # „Clínica Dental Sonrisa” to zwykła firma ze słownika
    assert all(f.nazwa.endswith(f.forma) for fs in nazwy.values() for f in fs)


@pytest.mark.parametrize("typ", TYPY_ES)
def test_es_bez_niegramatycznych_kontrakcji(typ):
    """„a el” / „de el” – przyimek i rodzajnik muszą stać razem w gnieździe rodzaju („al demandado”, „del Procurador”)."""
    for i in range(200):
        _, (tekst, _, _) = _buduj(typ, 6000 + i)
        zly = re.search(r"\b(?:[Aa]|[Dd]e) el\b", tekst)
        assert zly is None, (typ, tekst[max(0, zly.start() - 50):zly.end() + 30])
