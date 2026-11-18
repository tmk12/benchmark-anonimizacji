"""J1 – poprawki sędziego po pilocie: etykiety w spanach gold identyfikatorów (A/S1), słowa opisowe nazw organizacji (D),
miara „w deklarowanym zakresie” w ocenie (S4/C), płeć imienia i stanowiska w warstwie trudnej (S5). J1-fix1: tylko czyste
etykiety (I1 a), próg i łączenie ciągu ponad etykietą (m1, m2), strażnik słów opisowych (m3); J2 – deklaracje zakresu.
J1-fix3: cytat innej sprawy w sędzi plikowym (I1), zakres deklarowany per język (I2), jednakowy próg części sygnatury (m1),
część wspólna całą częścią (m2), deklaracje Presidio i modelu Privatizera (m3, m4)."""
from __future__ import annotations

import ast
import dataclasses
import json
import random
import re
from pathlib import Path

import pytest
from docx import Document

from pbench.linearyzacja import GoldSpan
from pbench.model import Wartosc, Wykrycie
from pbench.sedzia.plik import SLOWA_ZASTRZEZONE
from pbench.sedzia.plik import ocen_plik as _ocen_plik
from pbench.sedzia.tekst import RegulyWycieku, ocen_tekst, zakresy_etykiet

pytestmark = pytest.mark.filterwarnings("ignore")

R = RegulyWycieku()
RACHUNEK_EN = "Routing No. 015757092, Account No. 60431799632"


def _gold(tekst: str, wartosc: str, kategoria: str, wid: str = "w#1") -> GoldSpan:
    i = tekst.index(wartosc)
    return GoldSpan(i, i + len(wartosc), wid, kategoria, "tresc")


def _wyk(tekst: str, *fragmenty: str) -> list[Wykrycie]:
    return [Wykrycie(tekst.index(f), tekst.index(f) + len(f), "X") for f in fragmenty]


def _rodzaje(o) -> list[str]:
    return [w[3] for w in o.wycieki]


# ----------------------------------------------------------------------------- A/S1: etykiety identyfikatorów (sędzia tekstowy)
def test_rachunek_en_oba_numery_zamaskowane_etykiety_zostaja_brak_wycieku():
    t = f"Employee: John Smith | {RACHUNEK_EN} | gross pay"
    g = [_gold(t, RACHUNEK_EN, "RACHUNEK")]
    o = ocen_tekst(g, _wyk(t, "015757092", "60431799632"), t, R)
    assert o.wycieki == [] and o.wartosci_ocenione == 1


def test_rachunek_en_routing_odsloniety_czesciowy_calosc_pelny():
    t = f"Employee: John Smith | {RACHUNEK_EN} | gross pay"
    g = [_gold(t, RACHUNEK_EN, "RACHUNEK")]
    assert _rodzaje(ocen_tekst(g, _wyk(t, "60431799632"), t, R)) == ["czesciowy"]
    assert _rodzaje(ocen_tekst(g, [], t, R)) == ["pelny"]
    # etykiety zamaskowane, numery odsłonięte – wyciek pełny (etykieta nie jest częścią wartości)
    assert _rodzaje(ocen_tekst(g, _wyk(t, "Routing No.", "Account No."), t, R)) == ["pelny"]
    # odsłonięte ostatnie cyfry numeru konta (≥ 4) – nadal wyciek częściowy
    assert _rodzaje(ocen_tekst(g, _wyk(t, "015757092", "6043179"), t, R)) == ["czesciowy"]


@pytest.mark.parametrize("kat,wartosc,numer", [
    ("SYGNATURA", "Claim No. QB-2020-014548", "QB-2020-014548"),
    ("SYGNATURA", "Case No. 2:21-cv-01234-JSR", "2:21-cv-01234-JSR"),
    ("SYGNATURA", "Autos n.º 123/2024", "123/2024"),
    ("SYGNATURA", "RG n° 21/01234", "21/01234"),
    ("SYGNATURA", "N° RG 21/01234", "21/01234"),
    ("SYGNATURA", "Sygn. akt I C 123/21", "I C 123/21"),
    ("SYGNATURA", "Az. 12 C 345/24", "12 C 345/24"),
    ("RACHUNEK", "Nr rachunku 12 1090 1014 0000 0712 1981 2874", "12 1090 1014 0000 0712 1981 2874"),
    ("RACHUNEK", "Kontonummer 0532013000", "0532013000"),
    ("RACHUNEK", "N.º de cuenta ES91 2100 0418 4502 0005 1332", "ES91 2100 0418 4502 0005 1332"),
    ("RACHUNEK", "N° de compte FR14 2004 1010 0505 0001 3M02 606", "FR14 2004 1010 0505 0001 3M02 606"),
    ("RACHUNEK", "IBAN DE89 3704 0044 0532 0130 00", "DE89 3704 0044 0532 0130 00"),
])
def test_etykiety_w_jezykach_numer_zamaskowany_brak_wycieku(kat, wartosc, numer):
    t = f"Dane: {wartosc}."
    g = [_gold(t, wartosc, kat)]
    assert ocen_tekst(g, _wyk(t, numer), t, R).wycieki == []
    assert _rodzaje(ocen_tekst(g, [], t, R)) == ["pelny"]


def test_wydzial_i_repertorium_to_nie_etykieta():
    """„VII Ca” to część sygnatury (wydział, repertorium) – odsłonięte przy zamaskowanym numerze nadal wycieka."""
    t = "Sąd Okręgowy, sygn. VII Ca 1234/21."
    g = [_gold(t, "VII Ca 1234/21", "SYGNATURA")]
    assert zakresy_etykiet("VII Ca 1234/21", "SYGNATURA") == []
    assert _rodzaje(ocen_tekst(g, _wyk(t, "1234/21"), t, R)) == ["czesciowy"]


@pytest.mark.parametrize("wartosc,numer,opis", [
    ("VII Ca 1234/21", "1234/21", "VII Ca"),                                  # PL: wydział i repertorium
    ("Juicio Verbal n.º 1757/2021", "1757/2021", "Juicio Verbal"),            # ES: rodzaj postępowania
    ("Rollo de Apelación n.º 456/2022", "456/2022", "Rollo de Apelación"),
    ("Procedimiento de Jura de Cuentas n.º 1234/2023", "1234/2023", "Procedimiento de Jura de Cuentas"),
])
def test_opisowa_czesc_sygnatury_identyfikuje_w_kazdym_jezyku(wartosc, numer, opis):
    """I1 (a): część opisowa oznaczenia sprawy nie jest etykietą w żadnym języku – odsłonięta przy zamaskowanym numerze wycieka
    częściowo, zamaskowana razem z numerem – nie (zostaje sama etykieta „n.º”)."""
    t = f"Asunto / sprawa: {wartosc}."
    g = [_gold(t, wartosc, "SYGNATURA")]
    assert all(wartosc[a:b] == "n.º" for a, b in zakresy_etykiet(wartosc, "SYGNATURA"))
    assert _rodzaje(ocen_tekst(g, _wyk(t, numer), t, R)) == ["czesciowy"]
    assert ocen_tekst(g, _wyk(t, opis, numer), t, R).wycieki == []


def test_fragment_numeru_ponizej_progu_nie_wycieka():
    """m1: odsłonięte 2–3 znaki numeru („QB”, numer kolejny „776”) są poniżej zamrożonego `min_cyfr_id` = 4 – tak samo jak bez
    etykiety; ten sam numer z odsłoniętym rodzajem postępowania wycieka."""
    t = "Claim No. QB-2020-014548 i Rollo de Apelación n.º 776/2025."
    g = [_gold(t, "Claim No. QB-2020-014548", "SYGNATURA", "a#1"), _gold(t, "Rollo de Apelación n.º 776/2025", "SYGNATURA", "b#1")]
    assert ocen_tekst(g, _wyk(t, "2020-014548", "Rollo de Apelación", "2025"), t, R).wycieki == []
    assert [(w[0], w[3]) for w in ocen_tekst(g, _wyk(t, "2020-014548", "2025"), t, R).wycieki] == [("b#1", "czesciowy")]


def test_ciag_laczy_sie_ponad_etykieta():
    """m2: etykieta jest separatorem – 2 ostatnie cyfry routingu i 2 pierwsze cyfry konta dają ciąg 4 znaków (tylko zaostrza)."""
    t = f"Employee: John Smith | {RACHUNEK_EN} | gross pay"
    g = [_gold(t, RACHUNEK_EN, "RACHUNEK")]
    assert _rodzaje(ocen_tekst(g, _wyk(t, "0157570", "431799632"), t, R)) == ["czesciowy"]
    assert ocen_tekst(g, _wyk(t, "01575709", "431799632"), t, R).wycieki == []      # 1 + 2 znaki – poniżej progu


def test_etykiety_tylko_w_rachunku_i_sygnaturze_i_calymi_slowami():
    assert zakresy_etykiet("NO 12345", "NR_REJESTRACYJNY") == []           # tablica olsztyńska – nie etykieta „No.”
    assert zakresy_etykiet("NO1234567", "SYGNATURA") == []                 # bez kropki i bez granicy – nie etykieta
    assert zakresy_etykiet("IBANX 1234", "RACHUNEK") == []                 # etykieta tylko całym słowem
    assert zakresy_etykiet(RACHUNEK_EN, "RACHUNEK") == [(0, 11), (23, 34)]


# ----------------------------------------------------------------------------- D: słowa opisowe nazw organizacji (sędzia tekstowy)
ORG = "Kancelaria Radców Prawnych Ziemba i Wspólnicy sp.k."


def test_org_odsloniete_same_slowa_opisowe_to_nie_wyciek():
    t = f"Pełnomocnik: {ORG}, ul. Długa 5."
    g = [_gold(t, ORG, "ORGANIZACJA")]
    assert ocen_tekst(g, _wyk(t, "Ziemba"), t, R).wycieki == []
    assert _rodzaje(ocen_tekst(g, _wyk(t, "Kancelaria Radców Prawnych"), t, R)) == ["czesciowy"]   # odsłonięte „Ziemba”
    assert _rodzaje(ocen_tekst(g, [], t, R)) == ["pelny"]


@pytest.mark.parametrize("nazwa,rdzen", [
    ("Schröder & Krause Rechtsanwälte PartG mbB", "Schröder & Krause"),
    ("Ashford & Blackwood LLP", "Ashford & Blackwood"),
    ("SELARL Dubois & Mercier Avocats", "Dubois & Mercier"),
    ("Gómez Ruiz Abogados, S.L.P.", "Gómez Ruiz"),
])
def test_org_formy_prawne_i_rodzaj_kancelarii_w_jezykach(nazwa, rdzen):
    t = f"Firma: {nazwa}."
    g = [_gold(t, nazwa, "ORGANIZACJA")]
    assert ocen_tekst(g, _wyk(t, rdzen), t, R).wycieki == []
    assert _rodzaje(ocen_tekst(g, [], t, R)) == ["pelny"]


def test_org_z_samych_slow_opisowych_odslonieta_w_calosci_wycieka_pelnie():
    t = "Klient: Kancelaria Prawna sp.k."
    g = [_gold(t, "Kancelaria Prawna sp.k.", "ORGANIZACJA")]
    assert _rodzaje(ocen_tekst(g, [], t, R)) == ["pelny"]
    assert ocen_tekst(g, _wyk(t, "Prawna"), t, R).wycieki == []


def test_slowa_opisowe_tylko_w_organizacji():
    """„Partner” w nazwisku osoby nie jest słowem opisowym (kategoria OSOBA bez zmian)."""
    t = "Świadek: Jan Partner."
    g = [_gold(t, "Jan Partner", "OSOBA")]
    assert _rodzaje(ocen_tekst(g, _wyk(t, "Jan"), t, R)) == ["czesciowy"]


def test_slowa_opisowe_i_zastrzezone_poza_slownikami_osob_i_miejsc():
    """m3: sędzia plikowy stosuje słowa zastrzeżone (z opisowymi) we wszystkich kategoriach, tekstowy – tylko w ORGANIZACJA.
    Różnica nie zmienia wyniku, dopóki żadne z tych słów nie jest imieniem, nazwiskiem, ulicą ani miejscowością korpusu (trzon
    i warstwa trudna, w tym nazwiska-słowa pospolite H2)."""
    from pbench.sedzia.plik import normalizuj
    from pbench.sedzia.tekst import SLOWA_OPISOWE
    from pbench.trudne_jezyk import _SLOWA
    slowa = {normalizuj(x) for x in SLOWA_ZASTRZEZONE | SLOWA_OPISOWE if len(x) >= 3}
    katalog = Path(__file__).resolve().parents[1] / "pbench" / "dane" / "slowniki"
    pliki = [p for p in katalog.glob("*/*.txt") if p.stem in ("imiona_k", "imiona_m", "nazwiska", "ulice", "miejscowosci")]
    assert len(pliki) >= 20
    kolizje = {(p.parent.name, p.stem, t) for p in pliki for t in re.findall(r"\w+", p.read_text(encoding="utf-8"))
               if normalizuj(t) in slowa}
    kolizje |= {("trudne", "nazwiska_zwykle_slowa", n) for j in _SLOWA.values() for n in j if normalizuj(n) in slowa}
    assert not kolizje, sorted(kolizje)


# ----------------------------------------------------------------------------- sędzia plikowy
def ocen_plik(*a, **k):
    k.setdefault("leksykon", {})
    return _ocen_plik(*a, **k)


def _docx(sciezka: Path, *akapity: str) -> Path:
    d = Document()
    for a in akapity:
        d.add_paragraph(a)
    d.save(sciezka)
    return sciezka


def test_plik_rachunek_en_etykiety_pomijane(tmp_path):
    org = _docx(tmp_path / "o.docx", "Payroll.", f"John Smith | {RACHUNEK_EN} | $5,000.00")
    w = [Wartosc("p1.rachunek#1", "RACHUNEK", RACHUNEK_EN, "en", "tabela", "RACHUNEK")]

    def rodzaje(*akapity: str) -> list[str]:
        return [x[3] for x in ocen_plik(org, _docx(tmp_path / "w.docx", "Payroll.", *akapity), w).wycieki]

    assert rodzaje("[PERSON] | Routing No. [ACCOUNT], Account No. [ACCOUNT] | $5,000.00") == []
    assert rodzaje("[PERSON] | Routing No. 015757092, Account No. [ACCOUNT] | $5,000.00") == ["czesciowy"]
    assert rodzaje(f"[PERSON] | {RACHUNEK_EN} | $5,000.00") == ["pelny"]
    # etykiety zamienione, numery zostały – pełny (wcześniej sędzia szukał tylko całości z etykietami)
    assert rodzaje("[PERSON] | [L] 015757092, [L] 60431799632 | $5,000.00") == ["pelny"]


def test_plik_sygnatura_z_etykieta_numer_zostal(tmp_path):
    org = _docx(tmp_path / "o.docx", "In the High Court. Claim No. QB-2020-014548. Between the parties.")
    w = [Wartosc("sad.sygnatura#1", "SYGNATURA", "Claim No. QB-2020-014548", "en", "tresc", "SYGNATURA")]
    assert ocen_plik(org, _docx(tmp_path / "a.docx", "In the High Court. Claim No. [CASE]."), w).wycieki == []
    wyn = _docx(tmp_path / "b.docx", "In the High Court. [LABEL] QB-2020-014548.")
    assert [x[3] for x in ocen_plik(org, wyn, w).wycieki] == ["pelny"]


@pytest.mark.parametrize("wartosc,numer,opis", [
    ("VII Ca 1234/21", "1234/21", "VII Ca"),                                  # PL bez etykiety: wydział i repertorium
    ("Sygn. akt VII Ca 1234/21", "1234/21", "VII Ca"),                        # PL z etykietą
    ("Juicio Verbal n.º 1757/2021", "1757/2021", "Juicio Verbal"),            # ES: rodzaj postępowania
    ("Rollo de Apelación n.º 456/2022", "456/2022", "Rollo de Apelación"),
])
def test_plik_opisowa_czesc_sygnatury_tak_samo_z_etykieta_i_bez(tmp_path, wartosc, numer, opis):
    """J1-fix2: część opisowa sygnatury odsłonięta przy zamaskowanym numerze daje wyciek częściowy także w sędzi plikowym –
    niezależnie od tego, czy przed numerem stoi etykieta („n.º”, „Sygn. akt”); zgodnie z sędzią tekstowym."""
    org = _docx(tmp_path / "o.docx", f"Sprawa: {wartosc}. Dalsza treść pisma.")
    w = [Wartosc("sad.sygnatura#1", "SYGNATURA", wartosc, "pl", "tresc", "SYGNATURA")]
    zostal_opis = ocen_plik(org, _docx(tmp_path / "a.docx", f"Sprawa: {opis} [X]. Dalsza treść pisma."), w)
    assert [x[3] for x in zostal_opis.wycieki] == ["czesciowy"]
    assert ocen_plik(org, _docx(tmp_path / "b.docx", "Sprawa: [X]. Dalsza treść pisma."), w).wycieki == []
    assert ocen_plik(org, _docx(tmp_path / "c.docx", f"Sprawa: [X] {numer}. Dalsza treść pisma."), w).wycieki
    assert [x[3] for x in ocen_plik(org, org, w).wycieki] == ["pelny"]


@pytest.mark.parametrize("wartosc,odslonieta", [
    ("Sygn. akt I C 123/21", "I C"),               # opis „I C” = 2 znaki, poniżej progu
    ("n.º 1234/2021", ""),                         # sama etykieta i numer
    ("QB-2020-014548", "QB"),                      # prefiks wydziału sklejony z numerem – 2 znaki, poniżej progu
])
def test_plik_krotka_lub_brakujaca_czesc_opisowa_nie_wycieka(tmp_path, wartosc, odslonieta):
    org = _docx(tmp_path / "o.docx", f"Sprawa: {wartosc}. Dalsza treść pisma.")
    w = [Wartosc("sad.sygnatura#1", "SYGNATURA", wartosc, "pl", "tresc", "SYGNATURA")]
    etykieta = wartosc.split(" ")[0] if wartosc.startswith(("Sygn.", "n.º")) else ""
    wyn = _docx(tmp_path / "w.docx", f"Sprawa: {etykieta} {odslonieta} [X]. Dalsza treść pisma.")
    assert ocen_plik(org, wyn, w).wycieki == []


def test_plik_czesc_wspolna_z_inna_wartoscia_nie_daje_wycieku(tmp_path):
    """Ten sam numer routingu w dwóch wartościach: jego odsłonięcie nie wskazuje, której – część pomijana (jak niejednoznaczne)."""
    a, b = "Routing No. 015757092, Account No. 60431799632", "Routing No. 015757092, Account No. 77712345678"
    org = _docx(tmp_path / "o.docx", f"A | {a}", f"B | {b}")
    w = [Wartosc("a.rachunek#1", "RACHUNEK", a, "en", "tabela", "RACHUNEK"),
         Wartosc("b.rachunek#1", "RACHUNEK", b, "en", "tabela", "RACHUNEK")]
    wyn = _docx(tmp_path / "w.docx", "A | Routing No. 015757092, Account No. [X]", "B | Routing No. [X], Account No. [X]")
    assert ocen_plik(org, wyn, w).wycieki == []
    wyn2 = _docx(tmp_path / "w2.docx", "A | Routing No. [X], Account No. 60431799632", "B | [X]")
    assert [(x[0], x[3]) for x in ocen_plik(org, wyn2, w).wycieki] == [("a.rachunek#1", "pelny")]


# ----------------------------------------------------------------------------- J1-fix3: sędzia plikowy – sygnatury
WLASNA, CYTAT = "VII Ca 1554/21", "VII Ca 6470/18"


def _wyrok(sciezka: Path, wlasna: str, cytat: str) -> Path:
    return _docx(sciezka, f"Sygn. akt {wlasna}", "WYROK", f"Sąd Okręgowy, rozpoznając apelację w sprawie {wlasna}, zważył, "
                 f"że zgodnie z wyrokiem z 12.03.2019 r., {cytat}, apelacja jest zasadna.", f"Sygn. akt {wlasna}")


def test_plik_cytat_innej_sprawy_z_tym_samym_wydzialem_nie_jest_wyciekiem(tmp_path):
    """I1 (orzeczenie kontrolera): część sygnatury liczy się jako wyciek tylko przy własnym wystąpieniu – w wyniku musi wystąpić
    częściej niż w oryginale poza gold (cytat „VII Ca 6470/18” to nie gold; reguła krotności jak dla wartości niejednoznacznych).
    Konstrukcja jak `pl-wyrok-0001` splitu test (własna sygnatura ×3, cytat z tym samym wydziałem i repertorium ×1)."""
    org = _wyrok(tmp_path / "o.docx", WLASNA, CYTAT)
    w = [Wartosc(f"sad.sygnatura#{i}", "SYGNATURA", WLASNA, "pl", "tresc", "SYGNATURA") for i in (1, 2, 3)]

    def wycieki(wlasna: str, cytat: str = CYTAT) -> list[tuple[str, str]]:
        return [(x[0], x[3]) for x in ocen_plik(org, _wyrok(tmp_path / "w.docx", wlasna, cytat), w).wycieki]

    assert wycieki("[SYGN]") == []                                    # własna zamaskowana wszędzie, cytat zostaje
    assert wycieki("[SYGN]", "[SYGN]") == []
    assert {r for _, r in wycieki("VII Ca [X]")} == {"czesciowy"}     # własna część opisowa odsłonięta – wyciek
    assert {r for _, r in wycieki("[X] 1554/21")} == {"czesciowy"}    # numer odsłonięty: „VII Ca” z cytatu nie dopełnia do pełnego
    assert {r for _, r in wycieki(WLASNA)} == {"pelny"}
    # tekstowy (offsety) – cytat poza spanami gold i tak nie jest oceniany
    t = f"Sygn. akt {WLASNA}. Wyrok z 12.03.2019 r., {CYTAT}."
    g = [_gold(t, WLASNA, "SYGNATURA")]
    assert ocen_tekst(g, _wyk(t, WLASNA), t, R).wycieki == []


def _wyrok_z_zapisami(sciezka: Path, wlasne: tuple[str, str, str], cytat: str) -> Path:
    """Jak `_wyrok`, ale każde z trzech własnych wystąpień sygnatury ma osobny zapis (nagłówek, treść, stopka)."""
    return _docx(sciezka, f"Sygn. akt {wlasne[0]}", "WYROK", f"Sąd Okręgowy, rozpoznając apelację w sprawie {wlasne[1]}, zważył, "
                 f"że zgodnie z wyrokiem z 12.03.2019 r., {cytat}, apelacja jest zasadna.", f"Sygn. akt {wlasne[2]}")


def test_plik_krotnosc_dotyczy_tylko_czesci_opisowych(tmp_path):
    """J1-fix4 (m1, m2): reguła krotności obejmuje wyłącznie części opisowe sygnatury, nie numer."""
    org = _wyrok(tmp_path / "o.docx", WLASNA, CYTAT)
    w = [Wartosc(f"sad.sygnatura#{i}", "SYGNATURA", WLASNA, "pl", "tresc", "SYGNATURA") for i in (1, 2, 3)]

    def wycieki(wlasne: tuple[str, str, str], cytat: str) -> set[str]:
        return {x[3] for x in ocen_plik(org, _wyrok_z_zapisami(tmp_path / "w.docx", wlasne, cytat), w).wycieki}

    # (a) własna część opisowa zostawiona raz + cytat zostawiony: 2 wystąpienia > 1 poza gold – częściowy
    assert wycieki(("VII Ca [X]", "[SYGN]", "[SYGN]"), CYTAT) == {"czesciowy"}
    # (b) cytat zamaskowany, własna część opisowa zostawiona raz (= liczbie cytatów): brak wycieku – UDOKUMENTOWANE OGRANICZENIE
    #     (sędzia plikowy nie ma offsetów, nie odróżni własnego „VII Ca” od cytatu; metodyka/zakres-gold.md, pkt 2)
    assert wycieki(("VII Ca [X]", "[SYGN]", "[SYGN]"), "[SYGN]") == set()
    # (c) własny numer odsłonięty, cytat z tym samym numerem zamaskowany: numer nie podlega krotności – wyciek
    assert wycieki(("[X] 1554/21", "[SYGN]", "[SYGN]"), "[SYGN]") == {"czesciowy"}
    org_c = _wyrok(tmp_path / "oc.docx", WLASNA, "II C 1554/21")          # cytat innego wydziału z tym samym numerem
    wyn_c = _wyrok_z_zapisami(tmp_path / "wc.docx", ("[X] 1554/21", "[SYGN]", "[SYGN]"), "[SYGN]")
    assert {x[3] for x in ocen_plik(org_c, wyn_c, w).wycieki} == {"czesciowy"}


@pytest.mark.parametrize("wartosc,maska", [
    ("12 C 345/24", ["12 C"]),                     # numer 5 znaków (m1: próg `min_cyfr_id`, jak w sędzi tekstowym)
    ("32 O 264/24", ["32 O"]),
    ("VII Ca 1554/21", ["VII Ca"]),
    ("WR.XII NS-REJ.KRS/033655/20", ["WR.XII", "033655/20"]),     # „NS-REJ.KRS” sklejone ukośnikiem z numerem
    ("Juicio Verbal n.º 1757/2021", ["1757/2021"]),
])
def test_plik_i_tekst_czesc_sygnatury_ten_sam_rodzaj(tmp_path, wartosc, maska):
    """m1: odsłonięta część sygnatury (numer 4–5 znaków, przedrostek rejestru sklejony z numerem) – „czesciowy” w obu sędziach."""
    t = f"Sprawa: {wartosc}. Dalsza treść pisma."
    assert _rodzaje(ocen_tekst([_gold(t, wartosc, "SYGNATURA")], _wyk(t, *maska), t, R)) == ["czesciowy"]
    wyn = t
    for m in maska:
        wyn = wyn.replace(m, "[X]", 1)
    w = [Wartosc("v#1", "SYGNATURA", wartosc, "pl", "tresc", "SYGNATURA")]
    assert _rodzaje(ocen_plik(_docx(tmp_path / "o.docx", t), _docx(tmp_path / "w.docx", wyn), w)) == ["czesciowy"]


def test_plik_czesc_wspolna_cala_czescia_nie_podciagiem(tmp_path):
    """m2: część opisowa „32 O” nie jest wspólna z adresem „Hauptstraße 32 Ost” (podciąg „32o”, ale nie cała część z granicami) –
    odsłonięty numer przy zamaskowanym „32 O” to „czesciowy” (wcześniej część wypadała i zostawał „pelny”)."""
    t = "Az. 32 O 264/24. Kläger: Hauptstraße 32 Ost, Berlin."
    w = [Wartosc("a#1", "SYGNATURA", "Az. 32 O 264/24", "de", "tresc", "SYGNATURA"),
         Wartosc("b#1", "ADRES", "Hauptstraße 32 Ost", "de", "tresc", "ADRES")]
    wyn = _docx(tmp_path / "w.docx", "Az. [X] 264/24. Kläger: [ADRES], Berlin.")
    assert [(x[0], x[3]) for x in ocen_plik(_docx(tmp_path / "o.docx", t), wyn, w).wycieki] == [("a#1", "czesciowy")]


def test_plik_slowa_opisowe_w_leksykonie_zastrzezonym(tmp_path):
    assert {"radców", "prawnych", "partg", "mbb", "selarl", "avocats", "abogados", "llp"} <= SLOWA_ZASTRZEZONE
    assert "chambers" not in SLOWA_ZASTRZEZONE                              # nazwisk nie dodajemy („law” – sprzed J1)
    org = _docx(tmp_path / "o.docx", f"Pełnomocnik: {ORG}.")
    w = [Wartosc("kanc.nazwa#1", "ORGANIZACJA", ORG, "pl", "tresc", "ORGANIZACJA")]
    assert ocen_plik(org, _docx(tmp_path / "a.docx", "Pełnomocnik: Kancelaria Radców Prawnych [ORG] i Wspólnicy sp.k."),
                     w).wycieki == []
    assert [x[3] for x in ocen_plik(org, _docx(tmp_path / "b.docx", "Pełnomocnik: [ORG] Ziemba [ORG]."), w).wycieki] \
        == ["czesciowy"]


# ----------------------------------------------------------------------------- S4/C: miara „w deklarowanym zakresie”
def test_kategorie_deklarowane_z_etykiet(tmp_path):
    from pbench.ocen import kategorie_deklarowane
    (tmp_path / "u").mkdir()
    assert kategorie_deklarowane(tmp_path / "u") is None
    (tmp_path / "u" / "etykiety.json").write_text(json.dumps({"PERSON": ["OSOBA"], "MONEY": [], "ID": ["PESEL", "NIP"]}),
                                                 encoding="utf-8")
    assert kategorie_deklarowane(tmp_path / "u") == ["NIP", "OSOBA", "PESEL"]


def test_zakres_deklarowany_per_jezyk(tmp_path):
    """I2: etykieta ze słownikiem język → kategorie działa tylko w tych językach („*” – w każdym); lista – w każdym."""
    from pbench.ocen import kategorie_deklarowane, zakres_deklarowany
    (tmp_path / "u").mkdir()
    (tmp_path / "u" / "etykiety.json").write_text(json.dumps({
        "PERSON": ["OSOBA"], "PL_PESEL": {"pl": ["PESEL"]}, "MONEY": {"en": ["KWOTA"]},
        "LOCATION": {"*": ["MIEJSCOWOSC"], "pl": ["ADRES"]}}), encoding="utf-8")
    assert zakres_deklarowany(tmp_path / "u") == {"*": ["MIEJSCOWOSC", "OSOBA"], "en": ["KWOTA"], "pl": ["ADRES", "PESEL"]}
    assert kategorie_deklarowane(tmp_path / "u", "pl") == ["ADRES", "MIEJSCOWOSC", "OSOBA", "PESEL"]
    assert kategorie_deklarowane(tmp_path / "u", "en") == ["KWOTA", "MIEJSCOWOSC", "OSOBA"]
    assert kategorie_deklarowane(tmp_path / "u", "fr") == ["MIEJSCOWOSC", "OSOBA"]
    assert kategorie_deklarowane(tmp_path / "u") == ["ADRES", "KWOTA", "MIEJSCOWOSC", "OSOBA", "PESEL"]   # opis: suma


def test_ocena_ma_miare_w_deklarowanym_zakresie(tmp_path, monkeypatch):
    from pbench import ocen
    from test_uruchom import uruchom_atrape, zrob_srodowisko
    sr = zrob_srodowisko(tmp_path)
    uruchom_atrape(sr, monkeypatch, "pusty")
    (sr["uczestnicy"] / "_atrapa" / "etykiety.json").write_text(json.dumps({"PER": ["OSOBA"]}), encoding="utf-8")
    assert ocen.main(["--uczestnik", "_atrapa", "--split", "dev", "--poziom", "tekst", "--korpus", str(sr["korpus"]),
                      "--wyniki", str(sr["wyniki"]), "--uczestnicy", str(sr["uczestnicy"]), "--procesy", "1"]) == 0
    p = sr["wyniki"] / "oceny" / "_atrapa" / "dev" / "tekst.jsonl"
    o = {r["id"]: r for r in map(json.loads, p.read_text(encoding="utf-8").splitlines())}
    z = o["pl-a-0004"]["w_zakresie_deklarowanym"]
    assert z["wartosci_ocenione"] == 2 and len(z["wycieki"]) == 2 and z["pokrycie_znakowe"] == 0.0
    z = o["pl-a-0002"]["w_zakresie_deklarowanym"]                       # PESEL poza zakresem
    assert z == {"wycieki": [], "wartosci_ocenione": 0, "pokrycie_znakowe": 1.0, "char_f2": 1.0}
    assert len(o["pl-a-0002"]["wycieki"]) == 1                           # miara główna bez zmian
    # I2: zakres w języku dokumentu – OSOBA zadeklarowana tylko dla „en” nie jest w zakresie dokumentu polskiego
    (sr["uczestnicy"] / "_atrapa" / "etykiety.json").write_text(json.dumps({"PER": {"en": ["OSOBA"]}, "ID": {"pl": ["PESEL"]}}),
                                                               encoding="utf-8")
    assert ocen.main(["--uczestnik", "_atrapa", "--split", "dev", "--poziom", "tekst", "--korpus", str(sr["korpus"]),
                      "--wyniki", str(sr["wyniki"]), "--uczestnicy", str(sr["uczestnicy"]), "--procesy", "1"]) == 0
    o = {r["id"]: r for r in map(json.loads, p.read_text(encoding="utf-8").splitlines())}
    assert o["pl-a-0004"]["w_zakresie_deklarowanym"]["wartosci_ocenione"] == 0
    assert o["pl-a-0002"]["w_zakresie_deklarowanym"]["wartosci_ocenione"] == 1


def test_w_zakresie_plikowo():
    from pbench.ocen import w_zakresie
    wyc = [("a#1", "OSOBA", "tresc", "pelny"), ("b#1", "KWOTA", "tabela", "pelny")]
    assert w_zakresie(wyc, ["a#1", "b#1", "c#1", "a#1"], {"a#1": "OSOBA", "b#1": "KWOTA", "c#1": "OSOBA"}, ["OSOBA"]) == \
        {"wycieki": [["a#1", "OSOBA", "tresc", "pelny"]], "wartosci_ocenione": 2}


# ----------------------------------------------------------------------------- S5: płeć w warstwie trudnej
def test_warstwa_trudna_mezczyzna_bez_zenskiej_formy_nazwiska():
    from pbench.dane import Generator, zgodna_plec
    from pbench.dane.wspolne import ZGODNA_PLEC

    def osoby(n: int) -> list:
        g = Generator("pl", 20261101)
        return [g.osoba() for _ in range(n)]
    trzon = osoby(3000)
    assert any(o.plec == "M" and o.nazwisko == "Sadowska" for o in trzon)        # znane ograniczenie trzonu
    with zgodna_plec():
        assert ZGODNA_PLEC.get()
        trudne = osoby(3000)
    assert not ZGODNA_PLEC.get()
    assert not any(o.plec == "M" and o.nazwisko.endswith(("ska", "cka", "dzka")) for o in trudne)
    # ten sam ciąg losowań: różnią się wyłącznie nazwiska męskie poprawione na formę męską
    for a, b in zip(trzon, trudne):
        assert (a.imie, a.plec, a.data_ur) == (b.imie, b.plec, b.data_ur)
        assert a.nazwisko == b.nazwisko or (a.nazwisko, b.nazwisko) == ("Sadowska", "Sadowski")


def test_warstwa_trudna_stanowisko_zgodne_z_plcia_trzon_bez_zmian():
    from pbench.budowa import zbuduj_z_kontekstem
    from pbench.dane import Generator
    from pbench.linearyzacja import linearyzuj_z_wartosciami
    from pbench.szablony import SZABLONY, SZABLONY_TRUDNE

    def wiersze(szablon) -> list[list[str]]:
        d = zbuduj_z_kontekstem(szablon, Generator("pl", 11), random.Random(11)).dokument
        return [l.split("\t") for l in linearyzuj_z_wartosciami(d)[0].splitlines()]

    # H6b: polskie szablony warstwy trudnej różnią się od trzonu tylko `przyimki` („ze”/„we”)
    assert dataclasses.replace(SZABLONY_TRUDNE[("pl", "umowa")], przyimki=False) == SZABLONY[("pl", "umowa")]
    trzon, trudne = wiersze(SZABLONY[("pl", "lista_plac")]), wiersze(SZABLONY_TRUDNE[("pl", "lista_plac")])
    assert len(trzon) == len(trudne)
    meskie = set(Generator("pl", 0)._s("imiona_m"))
    ksiegowi = [(a, b) for a, b in zip(trzon, trudne) if len(a) > 4 and a[4] == "Księgowa"]
    assert ksiegowi and any(b[1] in meskie for _, b in ksiegowi)
    for a, b in zip(trzon, trudne):
        if (a, b) in ksiegowi:
            assert b[:4] + b[5:] == a[:4] + a[5:] and b[4] == ("Księgowy" if b[1] in meskie else "Księgowa")
        else:     # H6b: czasowniki podpisów zgodne z płcią („Sporządziła”) – poza tym wiersze jak w trzonie
            assert a == [re.sub(r"\b(Sporządził|Sprawdził|Zatwierdził)a\b", r"\1", k) for k in b]


# ----------------------------------------------------------------------------- J2: deklaracje zakresu uczestników
UCZESTNICY = Path(__file__).resolve().parents[1] / "uczestnicy"
#: Kategorie domyślnie wyłączone w Privatizerze v1.3.0b24 (`lgprivatizer/categories.py` tagu, `default=False`) – kopia, nie import.
#: `ZDROWIE` jest wyłączona także (deklarują ją tylko warianty maks – spany D39 w trybie privacy), ale zestaw służy sprawdzeniu `INICJALY`.
PRIVATIZER_WYLACZONE = {"INICJALY", "MAC", "UUID", "KWOTA"}


def _zakres(uczestnik: str, jezyk: str | None = None) -> set[str]:
    """Zakres deklarowany w języku `jezyk` (None – suma po językach)."""
    from pbench.ocen import kategorie_deklarowane
    return set(kategorie_deklarowane(UCZESTNICY / uczestnik, jezyk))


def _kategorie_etykiety(v) -> set[str]:
    """Kategorie etykiety `etykiety.json` we wszystkich językach (lista albo słownik język → lista)."""
    return {k for x in (v.values() if isinstance(v, dict) else [v]) for k in x}


def _etykiety_run(uczestnik: str) -> set[str]:
    """Lista `ETYKIETY` z `run.py` uczestnika GLiNER (bez importu – środowisko uczestnika jest osobne)."""
    drzewo = ast.parse((UCZESTNICY / uczestnik / "run.py").read_text(encoding="utf-8"))
    wartosc = next(ast.literal_eval(w.value) for w in drzewo.body
                   if isinstance(w, ast.Assign) and any(getattr(c, "id", None) == "ETYKIETY" for c in w.targets))
    if isinstance(wartosc, dict):
        return set(wartosc)
    return {e for x in wartosc for e in (x if isinstance(x, list) else [x])}


@pytest.mark.parametrize("uczestnik", ["privatizer-tekst", "privatizer-plik", "privatizer-model"])
def test_j2_privatizer_bez_kategorii_wylaczonych(uczestnik):
    """Klucze = kategorie zwracane w ustawieniach domyślnych; INICJALY w zakresie tylko przez model (inicjały pod OSOBA)."""
    d = json.loads((UCZESTNICY / uczestnik / "etykiety.json").read_text(encoding="utf-8"))
    assert not set(d) & PRIVATIZER_WYLACZONE
    assert _zakres(uczestnik) & PRIVATIZER_WYLACZONE == {"INICJALY"} and "INICJALY" in d["OSOBA"]


def test_j2_privatizer_komponenty():
    assert not _zakres("privatizer-reguly") & (PRIVATIZER_WYLACZONE | {"ZDROWIE"})         # bez modelu: bez inicjałów i zdrowia
    assert {"MRZ", "KRYPTO"} <= _zakres("privatizer-reguly") and not {"MRZ", "KRYPTO"} & _zakres("privatizer-model")
    assert _zakres("privatizer-tekst") == _zakres("privatizer-plik")


def test_j2_zdrowie_tylko_w_wariantach_maks():
    """`ZDROWIE` jest w wydaniu domyślnie wyłączona: warianty rankingowe (tryb domyślny) jej nie deklarują, warianty maks tak (D39)."""
    for u in ("privatizer-tekst", "privatizer-plik", "privatizer-model", "privatizer-reguly", "privatizer-tekst-gliner", "privatizer-tekst-opf"):
        assert "ZDROWIE" not in _zakres(u), u
    for u in ("privatizer-tekst-maks", "privatizer-plik-maks"):
        assert "ZDROWIE" in _zakres(u), u


@pytest.mark.parametrize("uczestnik", ["gliner-knowledgator-pii", "gliner-nvidia-pii", "gliner-urchade-pii"])
def test_j2_gliner_klucze_to_etykiety_zadane_modelowi(uczestnik):
    assert set(json.loads((UCZESTNICY / uczestnik / "etykiety.json").read_text(encoding="utf-8"))) == _etykiety_run(uczestnik)


def test_j2_ta_sama_regula_dla_wszystkich():
    """Kwota tylko u uczestników z etykietą kwoty; numery ubezpieczenia społecznego razem; lokalizacja z NER bez adresu;
    numer lekarza (NR_ID) nie jako „national id”."""
    wszyscy = sorted(p.parent.name for p in UCZESTNICY.glob("*/etykiety.json"))
    assert len(wszyscy) == 23                                  # + grupa B (zadanie 14): 3 tekstowi, 3 plikowi; + 3 warianty krzyżowe (X1); + 2 „maks”
    assert {u for u in wszyscy if "KWOTA" in _zakres(u)} == {"gliner-knowledgator-pii", "stanza", "privatizer-tekst-maks",
                                                              "privatizer-plik-maks"}
    for u in wszyscy:
        d = json.loads((UCZESTNICY / u / "etykiety.json").read_text(encoding="utf-8"))
        for k in ("ssn", "social security number", "SSN"):     # ogólne etykiety OSS (u Privatizera „SSN” to kategoria krajowa)
            assert k not in d or u.startswith("privatizer") or {"SSN", "SVNR", "NUSS", "NINO", "NIR"} <= _kategorie_etykiety(d[k]), u
        for k in ("national id number", "NATIONAL_ID"):
            assert "NR_ID" not in _kategorie_etykiety(d.get(k, [])), u
        assert "CIF" not in _kategorie_etykiety(d.get("ES_NIF", [])), u    # m3: wzorzec DNI (cyfry + litera kontrolna)
    for u in ("stanza", "presidio-spacy"):
        assert "ADRES" not in _zakres(u)
    assert "ADRES" in _zakres("presidio-pl-ner")                                 # LOC lexedit = adres prywatny
    assert json.loads((UCZESTNICY / "_wspolne" / "etykiety_presidio.json").read_text(encoding="utf-8")) == \
        json.loads((UCZESTNICY / "presidio-spacy" / "etykiety.json").read_text(encoding="utf-8"))


#: (I2) Języki, w których działa rozpoznawacz krajowy Presidio (`presidio_wspolne.KRAJOWE`, `rozpoznawacze_pl` – tylko „pl”).
JEZYK_PRZEDROSTKA = {"PL_": "pl", "US_": "en", "UK_": "en", "ES_": "es", "DE_": "de"}


@pytest.mark.parametrize("uczestnik", ["presidio-spacy", "presidio-gliner", "presidio-pl-ner"])
def test_j2_presidio_rozpoznawacze_krajowe_tylko_w_swoim_jezyku(uczestnik):
    """I2: encja rozpoznawacza zarejestrowanego dla jednego języka jest w zakresie tylko dokumentów tego języka."""
    d = json.loads((UCZESTNICY / uczestnik / "etykiety.json").read_text(encoding="utf-8"))
    for et, v in d.items():
        jezyk = next((j for p, j in JEZYK_PRZEDROSTKA.items() if et.startswith(p)), "en" if et == "MEDICAL_LICENSE" else None)
        if jezyk is not None:
            assert isinstance(v, dict) and set(v) == {jezyk}, (et, v)
    assert "PESEL" not in _zakres("presidio-spacy", "en") and "PESEL" in _zakres("presidio-spacy", "pl")
    assert "KVNR" not in _zakres("presidio-spacy", "pl") and "KVNR" in _zakres("presidio-spacy", "de")


def test_j2_komponenty_jednojezyczne_per_jezyk():
    """I2: Stanza – daty tylko z NKJP (pl) i OntoNotes (en), kwoty tylko z OntoNotes; presidio-pl-ner – lexedit (adres, ID,
    diagnoza) tylko w pl; uczestnicy z jednym modelem wielojęzycznym albo regułami we wszystkich profilach (GLiNER, OPF,
    Privatizer – D21) – ten sam zakres w każdym języku."""
    assert {j for j in ("pl", "en", "es", "de", "fr") if "KWOTA" in _zakres("stanza", j)} == {"en"}
    assert {j for j in ("pl", "en", "es", "de", "fr") if "DATA" in _zakres("stanza", j)} == {"pl", "en"}
    for k in ("ADRES", "SYGNATURA", "ZDROWIE"):
        assert {j for j in ("pl", "en", "es", "de", "fr") if k in _zakres("presidio-pl-ner", j)} == {"pl"}, k
    assert "MIEJSCOWOSC" in _zakres("presidio-pl-ner", "fr")
    for u in ("gliner-knowledgator-pii", "gliner-nvidia-pii", "gliner-urchade-pii", "openai-privacy-filter", "privatizer-tekst",
              "privatizer-plik", "privatizer-model", "privatizer-reguly"):
        d = json.loads((UCZESTNICY / u / "etykiety.json").read_text(encoding="utf-8"))
        assert all(isinstance(v, list) for v in d.values()), u


def test_j2_privatizer_model_numery_ubezpieczenia_zdrowotnego():
    """m4: „contract or account reference” (taksonomia etykiet modelu w tagu: „client, contract, policy, order, membership or
    account number”) obejmuje numer ubezpieczonego (KVNR, NHS, MBI) – etykieta modelu pod `IDENTYFIKATOR`."""
    d = json.loads((UCZESTNICY / "privatizer-model" / "etykiety.json").read_text(encoding="utf-8"))
    assert {"KVNR", "NHS", "MBI"} <= set(d["IDENTYFIKATOR"])
    assert {"KVNR", "NHS", "MBI"} <= _zakres("privatizer-model") <= _zakres("privatizer-tekst")
