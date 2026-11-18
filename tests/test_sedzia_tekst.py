"""Testy sędziego tekstowego: wyciek wartości (bez względu na etykietę), FP, pokrycie znakowe, char-F2."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from pbench.linearyzacja import GoldSpan
from pbench.model import KATEGORIE, Wykrycie
from pbench.sedzia.normalizacja import normalizuj, same_alnum
from pbench.sedzia.tekst import (KATEGORIE_ID, OcenaDokumentu, RegulyWycieku, gold_z_wpisu, ocen_tekst)

R = RegulyWycieku()


def _gold(tekst: str, wartosc: str, kategoria: str = "OSOBA", wid: str = "w#1", miejsce: str = "tresc",
          od: int = 0) -> GoldSpan:
    i = tekst.index(wartosc, od)
    return GoldSpan(i, i + len(wartosc), wid, kategoria, miejsce)


def _wyk(tekst: str, fragment: str, etykieta: str = "OSOBA", od: int = 0) -> Wykrycie:
    i = tekst.index(fragment, od)
    return Wykrycie(i, i + len(fragment), etykieta)


def test_pelne_pokrycie_brak_wycieku():
    t = "Pozwany Jan Kowalski mieszka w Łodzi."
    g = [_gold(t, "Jan Kowalski")]
    o = ocen_tekst(g, [_wyk(t, "Jan Kowalski")], t, R)
    assert o.wycieki == []
    assert o.fp_znaki == 0 and o.fp_spany == 0
    assert o.pokrycie_znakowe == 1.0 and o.char_f2 == 1.0


def test_zla_etykieta_to_nie_wyciek():
    t = "Pozwany Jan Kowalski mieszka w Łodzi."
    g = [_gold(t, "Jan Kowalski")]
    o = ocen_tekst(g, [_wyk(t, "Jan Kowalski", etykieta="ORGANIZACJA")], t, R)
    assert o.wycieki == []
    assert o.fp_spany == 0


def test_brak_wykryc_to_wyciek_pelny():
    t = "Pozwany Jan Kowalski mieszka w Łodzi."
    o = ocen_tekst([_gold(t, "Jan Kowalski", miejsce="tabela")], [], t, R)
    assert o.wycieki == [("w#1", "OSOBA", "tabela", "pelny")]
    assert o.pokrycie_znakowe == 0.0 and o.char_f2 == 0.0


def test_samo_imie_odsloniete_to_wyciek_czesciowy():
    t = "Pozwany Jan Kowalski mieszka w Łodzi."
    g = [_gold(t, "Jan Kowalski")]
    o = ocen_tekst(g, [_wyk(t, "Kowalski")], t, R)  # imię „Jan” zostaje
    assert o.wycieki == [("w#1", "OSOBA", "tresc", "czesciowy")]
    assert 0 < o.pokrycie_znakowe < 1


def test_samo_nazwisko_odsloniete_to_wyciek_czesciowy():
    t = "Pozwany Jan Kowalski mieszka w Łodzi."
    o = ocen_tekst([_gold(t, "Jan Kowalski")], [_wyk(t, "Jan")], t, R)
    assert [w[3] for w in o.wycieki] == ["czesciowy"]


def test_krotkie_tokeny_nie_licza_sie():
    # „ul.” i numer domu (1 znak) poniżej progu 3 – odsłonięte nie powodują wycieku
    t = "Adres: ul. Długa 5 w Krakowie"
    g = [_gold(t, "ul. Długa 5", kategoria="ADRES")]
    assert ocen_tekst(g, [_wyk(t, "Długa")], t, R).wycieki == []
    assert [w[3] for w in ocen_tekst(g, [_wyk(t, "ul.")], t, R).wycieki] == ["pelny"]  # „Długa” odsłonięta (jedyny token ≥3)


def test_wartosc_bez_tokenow_powyzej_progu_nie_wycieka():
    # kategoria słowna bez tokenu ≥ 3 znaków nie może wyciec; inicjały (INICJALY) mają własną regułę (H6a, `test_h6a.py`)
    t = "Pełnomocnik J. K. wniósł."
    g = [_gold(t, "J. K.", kategoria="OSOBA")]
    o = ocen_tekst(g, [], t, R)
    assert o.wycieki == []
    assert [w[3] for w in ocen_tekst([_gold(t, "J. K.", kategoria="INICJALY")], [], t, R).wycieki] == ["pelny"]


def test_pesel_pokryty_w_10_z_11_cyfr_nie_wycieka_wg_progu():
    # Reguła z rozstrzygnięć: wyciek dopiero od ≥4 odsłoniętych kolejnych cyfr; jedna cyfra to nie wyciek.
    t = "PESEL 44051401359 podano."
    g = [_gold(t, "44051401359", kategoria="PESEL")]
    o = ocen_tekst(g, [Wykrycie(g[0].start, g[0].start + 10, "PESEL")], t, R)
    assert o.wycieki == []
    assert o.pokrycie_znakowe == pytest.approx(10 / 11)


def test_pesel_odsloniete_4_cyfry_to_wyciek():
    t = "PESEL 44051401359 podano."
    g = [_gold(t, "44051401359", kategoria="PESEL")]
    o = ocen_tekst(g, [Wykrycie(g[0].start, g[0].start + 7, "PESEL")], t, R)
    assert o.wycieki == [("w#1", "PESEL", "tresc", "czesciowy")]


def test_pesel_odsloniete_3_cyfry_to_nie_wyciek():
    t = "PESEL 44051401359 podano."
    g = [_gold(t, "44051401359", kategoria="PESEL")]
    assert ocen_tekst(g, [Wykrycie(g[0].start, g[0].start + 8, "PESEL")], t, R).wycieki == []


def test_pesel_ze_spacjami_po_maskowaniu_czesci():
    # separatory nie przerywają ciągu odsłoniętych cyfr: „1234 5678 9012”, zamaskowane środkowe 4 cyfry
    t = "Karta 1234 5678 9012 3456 koniec"
    g = [_gold(t, "1234 5678 9012 3456", kategoria="KARTA")]
    w = [Wykrycie(g[0].start + 5, g[0].start + 9, "KARTA")]  # „5678”
    o = ocen_tekst(g, w, t, R)
    assert [x[3] for x in o.wycieki] == ["czesciowy"]
    # odsłonięte 2+2 cyfry po obu stronach separatora = ciąg 4 -> wyciek; po zakryciu „34 56” zostaje 2+... -> sprawdzamy brak
    w2 = [Wykrycie(g[0].start + 2, g[0].end, "KARTA")]  # odsłonięte tylko „12” – poniżej progu
    assert ocen_tekst(g, w2, t, R).wycieki == []


def test_iban_odslonieto_ostatnie_4_cyfry_to_wyciek():
    iban = "PL61 1090 1014 0000 0712 1981 2874"
    t = f"Rachunek: {iban}."
    g = [_gold(t, iban, kategoria="RACHUNEK")]
    w = [Wykrycie(g[0].start, g[0].end - 4, "RACHUNEK")]
    assert [x[3] for x in ocen_tekst(g, w, t, R).wycieki] == ["czesciowy"]
    assert ocen_tekst(g, w, t, RegulyWycieku(min_cyfr_id=5)).wycieki == []


def test_wartosc_krotsza_niz_prog_id_uzywa_swojej_dlugosci():
    t = "Nr 12 sprawy."
    g = [_gold(t, "12", kategoria="IDENTYFIKATOR")]
    assert [x[3] for x in ocen_tekst(g, [], t, R).wycieki] == ["pelny"]


def test_fragment_neutralnego_slowa_nie_jest_gold():
    t = "Jan Kowal prowadzi kowalstwo artystyczne."
    g = [_gold(t, "Jan Kowal")]
    w = [_wyk(t, "Jan Kowal"), _wyk(t, "kowalstwo")]
    o = ocen_tekst(g, w, t, R)
    assert o.wycieki == []           # „kowal” w „kowalstwo” nie jest gold
    assert o.fp_spany == 1 and o.fp_znaki == len("kowalstwo")


def test_odmiana_pl():
    # gold = forma wstawiona: „Jana Kowalskiego”; wykrycie nominatywu-skrótu „Jana Kowalski” nie pokrywa końcówki
    t = "Wyrok dla Jana Kowalskiego zapadł."
    g = [_gold(t, "Jana Kowalskiego")]
    ok = ocen_tekst(g, [_wyk(t, "Jana Kowalskiego")], t, R)
    assert ok.wycieki == []
    czesc = ocen_tekst(g, [Wykrycie(g[0].start, g[0].end - 6, "OSOBA")], t, R)  # brak „lskiego” (6 znaków)
    assert [x[3] for x in czesc.wycieki] == ["czesciowy"]  # „Jana” pokryta, „Kowalskiego” ma niepokryte 6 z 11


def test_wykrycie_w_srodku_tokenu_zostawia_wyciek():
    t = "Pozwany Kowalski."
    g = [_gold(t, "Kowalski")]
    w = [Wykrycie(g[0].start + 2, g[0].start + 3, "OSOBA")]  # pokryte tylko „w”: niepokryte ciągi 2 i 5
    assert [x[3] for x in ocen_tekst(g, w, t, R).wycieki] == ["pelny"]


def test_fp_liczone_poza_gold():
    t = "Jan Kowalski złożył pozew w Sądzie."
    g = [_gold(t, "Jan Kowalski")]
    w = [_wyk(t, "Jan Kowalski"), _wyk(t, "pozew"), _wyk(t, "Sądzie")]
    o = ocen_tekst(g, w, t, R)
    assert o.fp_spany == 2
    assert o.fp_znaki == len("pozew") + len("Sądzie")
    assert o.wycieki == []
    # precyzja = 11/(11+11)
    p, r = 11 / 22, 1.0
    assert o.char_f2 == pytest.approx(5 * p * r / (4 * p + r))


def test_wykrycie_dluzsze_niz_gold_nadmiar_to_fp_a_wartosc_nie_wycieka():
    t = "Pozwany Jan Kowalski mieszka w Łodzi."
    g = [_gold(t, "Jan Kowalski")]
    i = t.index("Pozwany")
    w = [Wykrycie(i, t.index("Łodzi") + 5, "OSOBA")]
    o = ocen_tekst(g, w, t, R)
    assert o.wycieki == []
    assert o.fp_spany == 0                      # wykrycie przecina gold
    assert o.fp_znaki == sum(1 for c in "Pozwany" + "mieszka" + "w" + "Łodzi" if not c.isspace())


def test_znaki_biale_nie_licza_sie_do_fp():
    t = "Jan Kowalski   i   Anna"
    g = [_gold(t, "Jan Kowalski")]
    w = [Wykrycie(0, len(t), "OSOBA")]
    o = ocen_tekst(g, w, t, R)
    assert o.fp_znaki == len("iAnna")


def test_nakladajace_sie_wykrycia_scalane():
    t = "Zbędne słowo tutaj."
    w = [_wyk(t, "słowo tutaj"), _wyk(t, "słowo")]
    o = ocen_tekst([], w, t, R)
    assert o.fp_znaki == len("słowotutaj")
    assert o.fp_spany == 1                      # zagnieżdżone wykrycie nie zawyża liczby FP-spanów


def test_wartosc_rozbita_na_dwie_komorki_jedna_odslonieta():
    t = "Jan\tKowalski\n"
    g = [GoldSpan(0, 3, "os#1", "OSOBA", "tabela"), GoldSpan(4, 12, "os#1", "OSOBA", "tabela")]
    o = ocen_tekst(g, [Wykrycie(0, 3, "OSOBA")], t, R)
    assert o.wycieki == [("os#1", "OSOBA", "tabela", "czesciowy")]
    o2 = ocen_tekst(g, [Wykrycie(0, 3, "OSOBA"), Wykrycie(4, 12, "OSOBA")], t, R)
    assert o2.wycieki == []
    o3 = ocen_tekst(g, [], t, R)
    assert o3.wycieki == [("os#1", "OSOBA", "tabela", "pelny")]


def test_wartosc_wyciekajaca_raz_a_nie_dwa_razy():
    t = "Jan Kowalski i Jan Kowalski."
    g = [_gold(t, "Jan Kowalski", wid="a#1"), _gold(t, "Jan Kowalski", wid="a#1", od=5)]
    o = ocen_tekst(g, [], t, R)
    assert len(o.wycieki) == 1


def test_email_odslonieta_domena_to_wyciek():
    t = "Pisz na anna.nowak@example.org dziś."
    g = [_gold(t, "anna.nowak@example.org", kategoria="EMAIL")]
    w = [Wykrycie(g[0].start, g[0].start + 10, "EMAIL")]  # „anna.nowak” – zostaje domena
    assert [x[3] for x in ocen_tekst(g, w, t, R).wycieki] == ["czesciowy"]
    assert ocen_tekst(g, [Wykrycie(g[0].start, g[0].end, "EMAIL")], t, R).wycieki == []


def test_kategorie_filtruja_wartosci_ale_nie_fp():
    t = "Jan Kowalski, PESEL 44051401359, pozew."
    g = [_gold(t, "Jan Kowalski", wid="o#1"), _gold(t, "44051401359", kategoria="PESEL", wid="p#1")]
    w = [_wyk(t, "Jan Kowalski"), _wyk(t, "pozew")]
    pelna = ocen_tekst(g, w, t, R)
    assert [x[0] for x in pelna.wycieki] == ["p#1"]
    zakres = ocen_tekst(g, w, t, R, kategorie={"OSOBA"})
    assert zakres.wycieki == []
    assert zakres.pokrycie_znakowe == 1.0
    assert zakres.fp_znaki == pelna.fp_znaki == len("pozew")
    tylko_pesel = ocen_tekst(g, w, t, R, kategorie={"PESEL"})
    assert [x[0] for x in tylko_pesel.wycieki] == ["p#1"]
    assert tylko_pesel.fp_znaki == len("pozew")        # wykrycie osoby (gold spoza zakresu) nie jest FP


def test_pusty_gold_i_brak_wykryc():
    o = ocen_tekst([], [], "abc", R)
    assert o.wycieki == [] and o.pokrycie_znakowe == 1.0 and o.char_f2 == 1.0


def test_wykrycie_poza_tekstem_jest_przycinane():
    t = "Jan Kowalski"
    o = ocen_tekst([_gold(t, "Jan Kowalski")], [Wykrycie(0, 500, "OSOBA"), Wykrycie(100, 200, "X")], t, R)
    assert o.wycieki == [] and o.fp_znaki == 0


def test_normalizacja():
    assert normalizuj("Ｊan Kowalski – x") == "jan kowalski - x"
    assert same_alnum("44-05 14.01") == "44051401"


def test_kategorie_id_podzbior_kategorii():
    assert KATEGORIE_ID <= KATEGORIE
    assert "PESEL" in KATEGORIE_ID and "OSOBA" not in KATEGORIE_ID


def test_wczytaj_reguly(tmp_path: Path):
    p = tmp_path / "prerejestracja.md"
    p.write_text("# X\n\n```yaml\nreguly_wycieku:\n  min_dl_tokenu: 4\n  min_cyfr_id: 6\n  kategorie_id: [PESEL, NIP]\n```\n", encoding="utf-8")
    r = RegulyWycieku.wczytaj(p)
    assert (r.min_dl_tokenu, r.min_cyfr_id, r.kategorie_id) == (4, 6, frozenset({"PESEL", "NIP"}))
    assert RegulyWycieku.wczytaj(tmp_path / "brak.md") == RegulyWycieku()
    p.write_text("brak bloku", encoding="utf-8")
    with pytest.raises(ValueError, match="reguly_wycieku"):
        RegulyWycieku.wczytaj(p)
    p.write_text("```yaml\nreguly_wycieku:\n  ulamek_tokenu: 0.7\n```\n", encoding="utf-8")
    assert RegulyWycieku.wczytaj(p).ulamek_tokenu == 0.7


def test_wczytaj_reguly_odrzuca_nieznany_klucz(tmp_path: Path):
    p = tmp_path / "p.md"
    p.write_text("```yaml\nreguly_wycieku:\n  min_dl: 4\n```\n", encoding="utf-8")
    with pytest.raises(ValueError):
        RegulyWycieku.wczytaj(p)


def _o(t, wartosc, pokryte, kat="OSOBA"):
    """Ocena wartości z pokrytym zakresem [a, b) względem początku wartości."""
    g = _gold(t, wartosc, kategoria=kat)
    a, b = pokryte
    w = [Wykrycie(g.start + a, g.start + b, "X")] if b > a else []
    return ocen_tekst([g], w, t, R).wycieki


def test_token_ostatni_znak_niepokryty_to_nie_wyciek():
    assert _o("Pan Kowalski.", "Kowalski", (0, 7)) == []


def test_odmiana_trzon_zamaskowany_koncowka_odslonieta():
    assert _o("Pan Kowalskiego.", "Kowalskiego", (0, 7)) == []


def test_odmiana_koniec_zamaskowany_trzon_odslonity_to_wyciek():
    assert len(_o("Pan Kowalskiego.", "Kowalskiego", (7, 11))) == 1  # „Kowalsk” niepokryte


def test_nowak_cztery_znaki_niepokryte_to_wyciek():
    assert len(_o("Pan Nowak.", "Nowak", (4, 5))) == 1


def test_jan_samo_j_pokryte_to_nie_wyciek():
    assert _o("Pan Jan.", "Jan", (0, 1)) == []


def test_jan_calkiem_niepokryty_to_wyciek():
    assert len(_o("Pan Jan.", "Jan", (0, 0))) == 1


def test_span_przesuniety_o_1_w_lewo_nie_wycieka():
    t = "Pozwany Jan Kowalski mieszka."
    g = [_gold(t, "Jan Kowalski")]
    assert ocen_tekst(g, [Wykrycie(g[0].start - 1, g[0].end - 1, "OSOBA")], t, R).wycieki == []


def test_email_tld_niepokryte_to_nie_wyciek():
    t = "Pisz: jan.kowalski@example.com dziś."
    g = [_gold(t, "jan.kowalski@example.com", kategoria="EMAIL")]
    assert ocen_tekst(g, [Wykrycie(g[0].start, g[0].end - 4, "E")], t, R).wycieki == []
    # „example” niepokryte (pokryta część lokalna i „.com”) → wyciek
    w = [Wykrycie(g[0].start, g[0].start + 12, "E"), Wykrycie(g[0].end - 4, g[0].end, "E")]
    assert len(ocen_tekst(g, w, t, R).wycieki) == 1


def test_url_schemat_www_i_tld_niepokryte_to_nie_wyciek():
    t = "Zob. https://www.kowalski-legal.pl/umowa tutaj."
    g = [_gold(t, "https://www.kowalski-legal.pl/umowa", kategoria="URL")]
    w = [Wykrycie(g[0].start + len("https://www."), g[0].end - len(umowa := "/umowa") - 3, "U"),
         Wykrycie(g[0].end - len(umowa) + 1, g[0].end, "U")]
    assert ocen_tekst(g, w, t, R).wycieki == []
    assert len(ocen_tekst(g, [], t, R).wycieki) == 1


def test_lone_surrogate_w_tekscie_nie_przewraca_sedziego():
    t = "Jan \ud800 Kowalski"
    g = [_gold(t, "Jan")]
    assert ocen_tekst(g, [Wykrycie(0, 3, "X")], t, R).wycieki == []


# --- Sanity na prawdziwym korpusie -------------------------------------------------------------------------------

KORPUS = Path(__file__).resolve().parent.parent / "korpus"
_E = None


def _wczytaj_korpus():
    global _E
    if _E is None:
        wpisy = [json.loads(l) for l in (KORPUS / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l]
        _E = [(w, (KORPUS / w["plik_txt"]).read_text(encoding="utf-8")) for w in wpisy]
    return _E


@pytest.mark.skipif(not (KORPUS / "manifest.jsonl").exists(), reason="brak wygenerowanego korpusu")
def test_sanity_korpus_uczestnik_idealny_pusty_i_regex_email():
    import re
    dane = _wczytaj_korpus()
    email = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
    t0 = time.perf_counter()
    for w, t in dane:
        g = gold_z_wpisu(w)
        # uczestnik idealny
        o = ocen_tekst(g, [Wykrycie(s.start, s.end, "X") for s in g], t, R)
        assert o.wycieki == [] and o.fp_znaki == 0 and o.fp_spany == 0, w["id"]
        # uczestnik pusty: wyciekają wszystkie wartości mające choć jeden kwalifikujący się token
        o0 = ocen_tekst(g, [], t, R)
        przewidywane = {s.wartosc_id for s in g if _ma_kwalifikujacy(s, t)}
        assert {x[0] for x in o0.wycieki} == przewidywane, w["id"]
        assert all(x[3] == "pelny" for x in o0.wycieki)
        # regex e-mail: wyciekają wszystkie oprócz e-maili
        wyk = [Wykrycie(m.start(), m.end(), "EMAIL") for m in email.finditer(t)]
        oe = ocen_tekst(g, wyk, t, R)
        assert not any(x[1] == "EMAIL" for x in oe.wycieki), w["id"]
    assert time.perf_counter() - t0 < 60


@pytest.mark.skipif(not (KORPUS / "manifest.jsonl").exists(), reason="brak wygenerowanego korpusu")
def test_sanity_korpus_odpornosc_na_granice_gold_skrocony_o_1_znak():
    for w, t in _wczytaj_korpus():
        g = gold_z_wpisu(w)
        o = ocen_tekst(g, [Wykrycie(s.start, max(s.start + 1, s.end - 1), "X") for s in g], t, R)
        assert [x for x in o.wycieki if x[1] not in KATEGORIE_ID] == [], w["id"]


def _ma_kwalifikujacy(s: GoldSpan, t: str) -> bool:
    import re
    tekst = t[s.start:s.end]
    if s.kategoria in KATEGORIE_ID:
        return len([c for c in tekst if c.isalnum()]) > 0
    return any(len(m.group()) >= 3 for m in re.finditer(r"\w+", tekst))


def test_fp_spany_po_scaleniu_zagniezdzonych_i_zdublowanych_wykryc():
    """Zagnieżdżone/identyczne wykrycia poza gold (np. flat_ner=False) to jeden fałszywy span; rozłączne – osobne."""
    t = "Jan Kowalski złożył pozew w Sądzie Okręgowym."
    g = [_gold(t, "Jan Kowalski")]
    pozew = _wyk(t, "pozew")
    o = ocen_tekst(g, [_wyk(t, "Jan Kowalski"), pozew, pozew, Wykrycie(pozew.start, pozew.start + 3, "X")], t, R)
    assert o.fp_spany == 1 and o.fp_znaki == len("pozew")
    o = ocen_tekst(g, [pozew, _wyk(t, "Sądzie Okręgowym"), _wyk(t, "Okręgowym")], t, R)
    assert o.fp_spany == 2


def test_j3_kod_pocztowy_regula_ciagu_identyfikatora():
    """J3: kod pocztowy jak identyfikator – wyciek = ≥ `min_cyfr_id` kolejnych odsłoniętych znaków alfanumerycznych (separator
    pomijany), jednakowo w każdym języku."""
    assert "KOD_POCZTOWY" in KATEGORIE_ID
    t = "Adres: ul. Polna 4, 28-333 Pińczów."
    g = [_gold(t, "28-333", "KOD_POCZTOWY")]
    assert ocen_tekst(g, [_wyk(t, "28-333")], t, R).wycieki == []
    assert ocen_tekst(g, [_wyk(t, "28-")], t, R).wycieki == []                  # „333” – 3 znaki < 4
    assert ocen_tekst(g, [_wyk(t, "2")], t, R).wycieki == [("w#1", "KOD_POCZTOWY", "tresc", "czesciowy")]
    assert ocen_tekst(g, [], t, R).wycieki == [("w#1", "KOD_POCZTOWY", "tresc", "pelny")]
