"""Testy szablonów EN: jeden kraj (GB albo US) w całym dokumencie, spójność dat i kwot, poziomy sądów, rozpoznania."""
from __future__ import annotations

import datetime as dt
import random
import re

import pytest

from pbench.budowa import zbuduj_z_kontekstem
from pbench.dane import Generator
from pbench.linearyzacja import linearyzuj_z_wartosciami
from pbench.szablony import SZABLONY, TYPY

TYPY_EN = list(TYPY)
MIESIACE = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
            "November", "December"]
OBCE = {"GB": {"SSN", "EIN"}, "US": {"NINO", "NHS", "VAT", "NR_REJESTRU"}}
ZNAK_WALUTY = {"GB": "£", "US": "$"}
#: Wyrażenia obcego kraju, których nie wolno znaleźć w tekście dokumentu (pisownia i instytucje jednego kraju).
ZAKAZANE_TEKST = {
    "GB": re.compile(r"\$|\bEIN\b|\bMr\.|\bMs\.|\bInc\.|\bLLC\b|\bU\.S\.|\bSecretary of State|\bplaintiff\b|"
                     r"\bDefendant-Appellant|\bauthorized\b|\binstallment|\bedema|\bliters\b|\blicenses\b", re.I),
    "US": re.compile(r"£|\bVAT\b|\bNHS\b|Companies House|\bsolicitors?\b|\bSRA\b|\bauthorised\b|\binstalment|"
                     r"\boedema|\blitres\b|\blicences\b|\bcentre\b|\bdefence\b|\bHMRC\b|\bCPR\b|\bGMC\b|\bClaimant\b"),
}
TELEFON = {"GB": re.compile(r"^(?:\+44|0)[\d ]+$"), "US": re.compile(r"^(?:\+1[\d -]+|\(\d{3}\) \d{3}-\d{4})$")}


def _buduj(typ: str, ziarno: int, wariant: str | None = None):
    s = SZABLONY[("en", typ)]
    w = zbuduj_z_kontekstem(s, Generator("en", ziarno), random.Random(ziarno), wariant)
    return w, linearyzuj_z_wartosciami(w.dokument)


def _data(tekst: str, kraj: str) -> dt.date:
    """Data w zapisie danego kraju: „12 March 2024” / „12/03/2024” (GB), „March 12, 2024” / „03/12/2024” (US)."""
    if kraj == "GB":
        m = re.fullmatch(r"(\d{1,2}) ([A-Z][a-z]+) (\d{4})", tekst)
        if m:
            return dt.date(int(m.group(3)), MIESIACE.index(m.group(2)) + 1, int(m.group(1)))
        m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", tekst)
        assert m, tekst
        return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    m = re.fullmatch(r"([A-Z][a-z]+) (\d{1,2}), (\d{4})", tekst)
    if m:
        return dt.date(int(m.group(3)), MIESIACE.index(m.group(1)) + 1, int(m.group(2)))
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", tekst)
    assert m, tekst
    return dt.date(int(m.group(3)), int(m.group(1)), int(m.group(2)))


def _grosze(tekst: str) -> int:
    m = re.fullmatch(r"[£$](\d{1,3}(?:,\d{3})*)\.(\d{2})", tekst)
    assert m, tekst
    return int(m.group(1).replace(",", "")) * 100 + int(m.group(2))


def _pole(wartosci, nazwa: str) -> str:
    return next(w.tekst for w in wartosci if w.id == f"ctx.{nazwa}#1")


@pytest.mark.parametrize("typ", TYPY_EN)
def test_en_jeden_kraj_w_dokumencie(typ):
    """200 budów: osoby, waluta, format dat, telefony i identyfikatory z jednego kraju; oba kraje ~50/50."""
    kraje = []
    for i in range(200):
        w, (tekst, _, wartosci) = _buduj(typ, 300 + i)
        k = w.kontekst.kraj
        kraje.append(k)
        assert {o.kraj for o in w.osoby.values()} <= {k}
        kategorie = {x.kategoria for x in wartosci}
        assert not kategorie & OBCE[k], (typ, k, kategorie & OBCE[k])
        for x in wartosci:
            if x.kategoria == "KWOTA":
                assert x.tekst[0] == ZNAK_WALUTY[k], (typ, k, x.tekst)
            if x.kategoria == "TELEFON":
                assert TELEFON[k].match(x.tekst), (typ, k, x.tekst)
        daty = [x.tekst for x in wartosci if x.kategoria in ("DATA", "DATA_UR")]
        for d in daty:
            _data(d, k)
        assert len({bool(re.fullmatch(r"\d{2}/\d{2}/\d{4}", d)) for d in daty}) <= 1, daty     # jeden styl w dokumencie
        assert w.kontekst.wariant.split("_")[0] == k.lower()
        zle = ZAKAZANE_TEKST[k].search(tekst)
        assert zle is None, (typ, k, zle and tekst[max(0, zle.start() - 50):zle.end() + 30])
    assert 70 <= kraje.count("GB") <= 130, (typ, kraje.count("GB"))


def test_en_wyrok_poziomy_sadow_skladow_i_sygnatur():
    wzory = {"gb_county": (r"County Court at .+", r"Claim No\. [A-Z]\d[A-Z]{2}\d{4}", {"judge1"}),
             "gb_appeal": (r"Court of Appeal \(Civil Division\)", r"Case No\. CA-\d{4}-\d{6}",
                           {"judge1", "judge2", "judge3"}),
             "us_federal": (r"United States District Court for the .+", r"Case No\. \d:\d{2}-cv-\d{5}-[A-Z]{3}",
                            {"judge1"}),
             "us_appeal": (r"United States Court of Appeals for the .+", r"No\. \d{2}-\d{4,5}",
                           {"judge1", "judge2", "judge3"})}
    for i in range(200):
        wariant = list(wzory)[i % 4]
        w, (tekst, _, wartosci) = _buduj("wyrok", 700 + i, wariant)
        sad, sygn, sedziowie = wzory[wariant]
        k, d = w.kontekst, w.kontekst.daty
        assert re.search(sad, tekst) and re.fullmatch(sygn, next(x.tekst for x in wartosci if x.id == "sad.sygnatura#1"))
        assert {x.id.split(".")[0] for x in wartosci if x.id.startswith("judge")} == sedziowie, wariant
        kraj = k.kraj
        assert _data(_pole(wartosci, "wyrok_koncowy"), kraj) == d["wyrok_koncowy"]
        assert d["rozprawa_koncowa"] <= d["wyrok_koncowy"]
        assert d["umowa"] < d["termin_platnosci"] < d["wezwanie"] < d["termin_wezwania"] < d["pozew"] <= d["rozprawa"]
        if wariant.endswith("appeal"):
            assert d["wyrok"] < d["apelacja"] < d["rozprawa_apel"] <= d["wyrok_apel"]
        assert k.kwoty["zasadzona"] < k.kwoty["glowna"] and k.kwoty["koszty_procesu"] < k.kwoty["glowna"]
        if wariant != "us_federal":
            assert k.kwoty["glowna"] <= 100_000_00
        sygn_rok = k.sygn_rok
        cyfry = re.findall(r"\d+", next(x.tekst for x in wartosci if x.id == "sad.sygnatura#1"))
        assert str(sygn_rok) in cyfry or f"{sygn_rok % 100:02d}" in (c[:2] for c in cyfry) or wariant == "gb_county", cyfry
        assert sygn_rok <= d["wyrok_koncowy"].year


def test_en_cytaty_to_zwykly_tekst_z_oznaczeniem_orzeczenia():
    for i in range(60):
        w, (tekst, _, wartosci) = _buduj("wyrok", 900 + i)
        assert not any(x.id.startswith("cite") for x in wartosci)
        pasuje = {"GB": r"[A-Z][a-z]+ v [A-Z][a-z]+ \[(?:19|20)\d{2}\]", "US": r"[A-Z][a-z]+ v\. [A-Z][a-z]+, \d+ "}
        assert re.search(pasuje[w.kontekst.kraj], tekst), (w.kontekst.kraj, tekst[:200])


def test_en_pozew_wezwanie_lancuch_dat_i_sumy():
    for typ in ("pozew", "wezwanie"):
        for i in range(120):
            w, (_, _, wartosci) = _buduj(typ, 1100 + i)
            d, k = w.kontekst.daty, w.kontekst.kraj
            assert d["umowa"] < d["termin_platnosci"] < d["wezwanie"] < d["termin_wezwania"] < d["pozew"]
            assert all(_data(x.tekst, k) <= d["pozew"] for x in wartosci if x.kategoria == "DATA"), typ
            wzgledem = {n: _grosze(_pole(wartosci, n)) for n in ("glowna", "odsetki", "koszty_wind", "razem_wez")} \
                if typ == "wezwanie" else {}
            if wzgledem:
                assert wzgledem["razem_wez"] == wzgledem["glowna"] + wzgledem["odsetki"] + wzgledem["koszty_wind"]
            else:
                assert _grosze(_pole(wartosci, "oplata_pozwu")) < _grosze(_pole(wartosci, "glowna"))
                assert w.kontekst.wariant in ("gb_county", "gb_high", "us_federal", "us_state")
                assert (w.kontekst.kwoty["glowna"] > 100_000_00) == (w.kontekst.wariant in ("gb_high", "us_federal"))


def test_en_faktura_sumy_i_stawka_podatku():
    stawki = {"GB": 0.20, "US": 0.0825}
    for i in range(120):
        w, (tekst, _, wartosci) = _buduj("faktura", 1300 + i)
        k = w.kontekst.kraj
        netto = sum(_grosze(_pole(wartosci, n)) for n in ("kf1", "kf2", "kf3"))
        assert _grosze(_pole(wartosci, "netto")) == netto
        assert _grosze(_pole(wartosci, "brutto")) == netto + _grosze(_pole(wartosci, "vat"))
        assert abs(_grosze(_pole(wartosci, "vat")) - netto * stawki[k]) <= 1
        assert ("VAT" in tekst) == (k == "GB") or "VAT" not in tekst
        assert _data(_pole(wartosci, "dok_sprzedaz"), k) <= _data(_pole(wartosci, "dok"), k) <= _data(_pole(wartosci, "dok_termin_fv"), k)


def test_en_lista_plac_sumy_i_dokument_wlasciwego_kraju():
    for i in range(6):
        w, (_, _, wartosci) = _buduj("lista_plac", 1500 + i)
        k = w.kontekst.kraj
        wiersze = [_grosze(x.tekst) for x in wartosci if x.id.startswith("ctx.brutto_")]
        assert len(wiersze) >= 200 and _grosze(_pole(wartosci, "suma_212")) == sum(wiersze[:212])
        ids = {x.kategoria for x in wartosci if x.miejsce == "tabela"}
        assert ("NINO" in ids) == (k == "GB") and ("SSN" in ids) == (k == "US")


def test_en_med_kolejnosc_dat_rozpoznania_wg_profilu_i_plci():
    from pbench.dane.wspolne import kod_icd_plec, slownik
    plcie = set()
    for typ, profil in (("med_wypis", "cardiology"), ("med_zaswiadczenie", "internal")):
        assert SZABLONY[("en", typ)].profil == profil
        slowniki = {k: (set(slownik("en", f"choroby_{profil}{s}")),
                        {x.split("|")[0] for x in slownik("en", f"leki_{profil}{s}")})
                    for k, s in (("GB", ""), ("US", "_us"))}
        for i in range(200):
            w, (tekst, _, wartosci) = _buduj(typ, 1700 + i)
            k, plec = w.kontekst.kraj, w.osoby["patient"].plec
            choroby, leki = slowniki[k]
            plcie.add(plec)
            diag = [d for d in w.encje["patient"].diagnozy if d in tekst]
            meds = [d for d in w.encje["patient"].leki if d in tekst]
            assert diag and meds
            assert all(d in choroby and kod_icd_plec(d) in (None, plec) for d in diag), diag
            assert all(m.rsplit(" ", 2)[0] in leki for m in meds), meds
            assert len(set(diag)) == len(diag) and len(set(meds)) == len(meds)
            if typ == "med_wypis":
                d = w.kontekst.daty
                assert d["przyjecie"] < d["wypis"] < d["kontrola"] and d["wypis"] <= d["zwolnienie_do"]
                assert _data(_pole(wartosci, "przyjecie"), k) == d["przyjecie"]
                assert w.osoby["patient"].data_ur < d["przyjecie"]
            else:
                d = w.kontekst.daty
                assert d["zas_od"] < d["zas_wystaw"] < d["rozprawa"] < d["zas_do"]
            nr_id = [x.tekst for x in wartosci if x.kategoria == "NR_ID"]
            assert nr_id and all(re.fullmatch(r"[1-7]\d{6}", n) if k == "GB" else re.fullmatch(r"[12]\d{9}", n) for n in nr_id)
    assert plcie == {"M", "K"}


def test_en_odpis_protokol_cv_kolejnosc_dat_i_kapital():
    for i in range(120):
        w, (_, _, wartosci) = _buduj("odpis_rejestru", 1900 + i)
        d, k = w.kontekst.daty, w.kontekst.kraj
        assert d["kr_rejestracja"] <= d["kr_wpis"] <= d["dok"]
        assert _grosze(_pole(wartosci, "kapital2")) % 50_00 == 0
        w, (_, _, wartosci) = _buduj("protokol", 2100 + i)
        u = w.kontekst.liczby
        assert w.kontekst.kwoty["kapital3"] == (u["udzialy1"] + u["udzialy2"] + u["udzialy3"]) * 50_00
        w, (_, _, wartosci) = _buduj("cv", 2300 + i)
        d, k = w.kontekst.daty, w.kontekst.kraj
        assert d["cv_studia"] < d["cv_od2"] < d["cv_do2"] <= d["cv_od1"]


def test_en_osoby_wg_rodzaju_w_zaimkach():
    """Gniazda rodzaju w EN (he/she, Mr/Ms) zgadzają się z płcią osoby w całym dokumencie."""
    for typ in ("email", "notatka", "wezwanie", "protokol"):
        for i in range(60):
            w, (tekst, _, _) = _buduj(typ, 2500 + i)
            ms = {rola: o.plec for rola, o in w.osoby.items()}
            for rola, wzor in (("client", r"\b(?:Mr|Mr\.) {nazw}\b"), ("debtor", r"\b(?:Mr|Mr\.) {nazw}\b")):
                if rola in ms and ms[rola] == "K":
                    assert not re.search(wzor.format(nazw=re.escape(w.osoby[rola].nazwisko)), tekst), (typ, rola)


# ------------------------------------------------------------------------------------------ rozstrzygnięcia poprawki 1
SZKOCJA_WALIA_NI = re.compile(r"\b(?:Glasgow|Edinburgh|Cardiff|Belfast|Swansea|Aberdeen|Dundee|Inverness|Stirling|"
                              r"Newport|Wrexham|Londonderry|Paisley|Dumfries|Perth|Kilmarnock|Scotland|Wales|"
                              r"Northern Ireland|Sheriff)\b")


@pytest.mark.parametrize("typ", TYPY_EN)
def test_en_gb_tylko_anglia_i_walia_instytucji(typ):
    """Dokumenty GB: adresy z Anglii (bez Szkocji/Walii/Irlandii Płn.), numery spółek bez SC/NI, kody Ofcom z Anglii."""
    n = 0
    for i in range(120):
        w, (tekst, _, wartosci) = _buduj(typ, 3000 + i)
        if w.kontekst.kraj != "GB":
            continue
        n += 1
        assert not SZKOCJA_WALIA_NI.search(tekst.replace("England and Wales", "")), \
            (typ, SZKOCJA_WALIA_NI.search(tekst.replace("England and Wales", "")).group())
        for x in wartosci:
            if x.kategoria == "NR_REJESTRU":
                assert re.fullmatch(r"\d{8}", x.tekst), x.tekst
            if x.kategoria == "ADRES":
                assert not re.search(r"\b(?:G|EH|CF|BT|SA|AB|DD|IV|FK|NP|LL|PA|DG|PH|KA)\d{1,2} \d[A-Z]{2}$", x.tekst), x.tekst
            if x.kategoria == "TELEFON":
                assert not re.match(r"(?:\+44 ?|0)(?:131|141|28|29)\b", x.tekst) and \
                    not x.tekst.startswith(("+441314", "+441414", "+44289", "+44292")), x.tekst
    assert n > 30


def test_en_nhs_bez_linii_rejestru_spolek():
    for i in range(80):
        w, (tekst, _, wartosci) = _buduj("med_wypis", 3300 + i, "gb")
        assert "Company/charity" not in tekst
        assert not any(x.kategoria == "NR_REJESTRU" for x in wartosci)
        assert re.search(r"NHS (?:Foundation )?Trust", tekst)


def _sprawdz_spojnosc_sadu(tekst: str, wartosci) -> None:
    sygn = [x.tekst for x in wartosci if x.kategoria == "SYGNATURA"]
    assert sygn
    t = tekst.lower()
    for s in sygn:
        if re.match(r"Claim No\. (?:KB|QB)-", s):
            assert "high court" in t and "county court at" not in t, s
        elif re.fullmatch(r"Claim No\. [A-Z]\d[A-Z]{2}\d{4}", s):
            assert "county court at" in t and "high court of justice" not in t, s
        elif s.startswith("Case No. CA-"):
            assert "court of appeal (civil division)" in t, s
        elif re.match(r"Case No\. \d:\d{2}-cv-", s):
            assert "united states district court for the" in t, s
        elif re.fullmatch(r"No\. \d{2}-\d{4,5}", s):
            assert "united states court of appeals" in t, s
        else:      # numer stanowy
            assert re.fullmatch(r"Case No\. (?:\d{2}-CV-\d{6}|[A-Z]{3}-\d{2}-\d{6}|\d{2}[A-Z]{2}CV\d{5})", s), s
            assert "united states district court" not in t and "united states court of appeals" not in t, s


@pytest.mark.parametrize("typ", ["pozew", "wyrok", "email", "notatka", "med_zaswiadczenie", "wezwanie"])
def test_en_numer_sprawy_zgodny_z_poziomem_sadu_w_dokumencie(typ):
    for i in range(200):
        w, (tekst, _, wartosci) = _buduj(typ, 3500 + i)
        if not any(x.kategoria == "SYGNATURA" for x in wartosci):
            continue
        _sprawdz_spojnosc_sadu(tekst, wartosci)


def test_en_email_daty_wg_kontekstu():
    for i in range(150):
        w, (tekst, _, wartosci) = _buduj("email", 3800 + i)
        d, k = w.kontekst.daty, w.kontekst.kraj
        daty = {x.id: _data(x.tekst, k) for x in wartosci if x.kategoria == "DATA"}
        assert daty and set(daty.values()) <= {d["rozprawa"], d["odp_termin"]}
        assert d["pozew"] < d["odp_termin"] < d["rozprawa"]


def test_en_nagłowek_sadu_wielkimi_literami_i_brak_urzednika():
    for i in range(80):
        w, (tekst, _, _) = _buduj("wyrok", 4000 + i)
        pierwsza = tekst.split("\n")[0]
        assert pierwsza == pierwsza.upper() and "COURT" in pierwsza, pierwsza
        assert "clerk" not in tekst.lower()
    for i in range(40):
        _, (tekst, _, _) = _buduj("pozew", 4100 + i)
        assert any(l == l.upper() and "COURT" in l for l in tekst.split("\n")[:4])


def test_en_wyrok_gb_akapity_numerowane_bez_luk():
    for i in range(120):
        for wariant in ("gb_county", "gb_appeal"):
            _, (tekst, _, _) = _buduj("wyrok", 4300 + i, wariant)
            numery = [int(m.group(1)) for m in re.finditer(r"^(\d+)\. ", tekst, re.M)]
            assert numery == list(range(1, len(numery) + 1)) and len(numery) >= 5, (wariant, numery)
    for i in range(20):
        _, (tekst, _, _) = _buduj("wyrok", 4500 + i, "us_federal")
        assert not re.search(r"^\d+\. ", tekst, re.M)


def test_en_us_geografia_osoba_adres_telefon_stan():
    from pbench.dane.en import _KODY_STANOW
    zgodne = lacznie = 0
    for i in range(300):
        s = SZABLONY[("en", "med_wypis")]
        w = zbuduj_z_kontekstem(s, Generator("en", 4700 + i), random.Random(4700 + i), "us")
        _, _, wartosci = linearyzuj_z_wartosciami(w.dokument)
        for rola in ("patient", "physician", "consultant", "relative"):
            o = w.osoby[rola]
            cyfry = re.sub(r"\D", "", o.telefon)
            kod = cyfry[1:4] if len(cyfry) == 11 else cyfry[:3]
            assert kod in _KODY_STANOW[o.adres.region], (o.adres.region, o.telefon)
        adresy = {x.id.split(".")[0]: x.tekst for x in wartosci if x.kategoria == "ADRES"}
        stany = {r: re.search(r", ([A-Z]{2}) \d{5}$", a).group(1) for r, a in adresy.items()}
        lacznie += 1
        zgodne += stany["patient"] == stany["hospital"]
    assert zgodne / lacznie >= 0.6, zgodne / lacznie     # losowanie stanu (85% w stanie dokumentu); próg 0,6 – rozrzut ziaren


def test_en_us_podpis_kancelarii_jeden_stan_adres_telefon():
    """Stopka/podpis e-maila: adres i telefon kancelarii z tego samego stanu."""
    from pbench.dane.en import _KODY_STANOW
    for i in range(150):
        w = zbuduj_z_kontekstem(SZABLONY[("en", "email")], Generator("en", 4900 + i), random.Random(4900 + i), "us")
        tekst, _, _ = linearyzuj_z_wartosciami(w.dokument)
        m = re.search(r"\| ([^|]*, ([A-Z]{2}) \d{5}) \| tel\. ([^|\n]+)", tekst)
        assert m
        cyfry = re.sub(r"\D", "", m.group(3))
        assert (cyfry[1:4] if len(cyfry) == 11 else cyfry[:3]) in _KODY_STANOW[m.group(2)], m.group(0)


def test_en_us_slownictwo_wypisu():
    for i in range(120):
        w, (tekst, _, _) = _buduj("med_wypis", 5200 + i, "us")
        assert "TTO" not in tekst and "full blood count" not in tekst and "ECG" not in tekst
        assert re.search(r"\bCBC\b", tekst)
        assert not re.search(r"bisoprolol|ramipril|paracetamol|oedema|haemo|aemia|oesoph", tekst)
