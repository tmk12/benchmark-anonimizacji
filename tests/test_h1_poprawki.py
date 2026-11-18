"""Testy regresyjne poprawek H1 po przeglądach (runda 1): cyfra płci РНОКПП ФОП, odmiana (nazwiska żeńskie
przymiotnikowe, Бондар, wołacz Олег), płeć w szablonach, pule sądów wg rodzaju sprawy, osoby publiczne, leki
(jednostki i dobór do rozpoznań), transliteracja polska, tryb ukraiński odmiany polskiej, stałe przypadku
`granica_okna`, pomocnik `warstwa`. Trzon korpusu pilnuje `tests/test_trudne.py` (sumy sha256 sprzed warstwy)."""
from __future__ import annotations

import random
import datetime as dt
import re
from pathlib import Path

import pytest
from stdnum.ua import edrpou as ua_edrpou

from pbench import korpus, odmiana_uk, przypadki as P
from pbench.budowa import zbuduj_z_kontekstem
from pbench.dane import Generator
from pbench.dane import uk as dane_uk
from pbench.dane.uk import (GeneratorUK, _SADY_APELACYJNE, _SADY_GOSPODARCZE, _SADY_POWSZECHNE, _ZABRONIONE_PARY,
                            plec_z_rnokpp)
from pbench.linearyzacja import linearyzuj_z_wartosciami
from pbench.odmiana_pl import odmien as odmien_pl
from pbench.szablony.trudne import SZABLONY_UK
from pbench.translit import transliteruj

SLOWNIKI = Path(__file__).resolve().parents[1] / "pbench" / "dane" / "slowniki" / "uk"
GOSPODARCZE = {n for n, _ in _SADY_GOSPODARCZE}


def _tekst(typ: str, seed: int) -> tuple[str, object]:
    w = zbuduj_z_kontekstem(SZABLONY_UK[typ], Generator("uk", seed), random.Random(seed))
    return linearyzuj_z_wartosciami(w.dokument)[0], w


# ----------------------------------------------------------------------------- I-1: cyfra płci РНОКПП ФОП
def test_fop_cyfra_plci_zgodna_z_plcia_osoby_w_nazwie():
    g = Generator("uk", 11)
    fop = 0
    for _ in range(600):
        f = g.firma()
        if f.forma != "ФОП":
            continue
        fop += 1
        po_batkovi = f.nazwa.split()[-1]
        plec_nazwy = "K" if po_batkovi.endswith(("івна", "ївна")) else "M"
        assert plec_z_rnokpp(f.rejestry["RNOKPP"]) == plec_nazwy, f.nazwa
    assert fop >= 40


# ----------------------------------------------------------------------------- M-1, M-3
def test_stale_granicy_okna_i_opis_przypadku():
    assert (P.GRANICA_OKNA_ZNAKI, P.ZAKLADKA_ZNAKI, P.TOLERANCJA_ZNAKI) == (2560, 448, 50)
    assert "2560" in P.PRZYPADKI[P.GRANICA_OKNA] and "448" in P.PRZYPADKI[P.GRANICA_OKNA]


def test_warstwa_wpisu_brak_pola_to_trzon():
    assert korpus.warstwa({"id": "x"}) == "trzon"
    assert korpus.warstwa({"id": "h-cu-uk-umowa-001", "warstwa": "trudne"}) == "trudne"


# ----------------------------------------------------------------------------- I1, I2, M5: odmiana ukraińska
@pytest.mark.parametrize("nazwisko,formy", [
    ("Біла", ["Білої", "Білій", "Білу", "Білою", "Білій"]),
    ("Бережна", ["Бережної", "Бережній", "Бережну", "Бережною", "Бережній"]),
    ("Підгорна", ["Підгорної", "Підгорній", "Підгорну", "Підгорною", "Підгорній"]),
])
def test_zenskie_nazwiska_przymiotnikowe_na_na_la(nazwisko, formy):
    assert [odmiana_uk.odmien_slowo(nazwisko, "nazwisko", "K", p) for p in ("rod", "dav", "zna", "oru", "mis")] == formy
    assert odmiana_uk.odmien("Ганна", "Петрівна", "Біла", "K", "rod") == "Білої Ганни Петрівни"


def test_kazde_zenskie_od_ij_ze_slownika_odmienia_sie_przymiotnikowo():
    for linia in (SLOWNIKI / "nazwiska.txt").read_text(encoding="utf-8").splitlines():
        uk = linia.partition("|")[0]
        if uk.endswith("ий") and not uk.endswith(("ський", "цький", "зький")):
            zen = dane_uk.nazwisko_zenskie(uk)
            assert odmiana_uk.odmien_slowo(zen, "nazwisko", "K", "rod").endswith("ої"), zen
    # rzeczownik na -на pozostaje rzeczownikiem
    assert odmiana_uk.odmien_slowo("Калина", "nazwisko", "K", "rod") == "Калини"


def test_bondar_odmiana_miekka_i_wolacz_oleh():
    assert [odmiana_uk.odmien_slowo("Бондар", "nazwisko", "M", p) for p in odmiana_uk.PRZYPADKI[1:]] == [
        "Бондаря", "Бондарю", "Бондаря", "Бондарем", "Бондарю", "Бондарю"]
    assert odmiana_uk.odmien_slowo("Олег", "imie", "M", "kl") == "Олеже"
    assert odmiana_uk.odmien_slowo("Олег", "imie", "M", "rod") == "Олега"


# ----------------------------------------------------------------------------- I3: rodzaj w szablonach
def test_rodzaj_w_pelnomocnictwie_notatce_i_zaswiadczeniu():
    wid_k = wid_m = 0
    for seed in range(30):
        t, w = _tekst("pelnomocnictwo", seed)
        if w.osoby["mocodawca"].plec == "K":
            wid_k += 1
            assert "довірительки встановлено" in t and "її дієздатність" in t and "його дієздатність" not in t
        else:
            wid_m += 1
            assert "довірителя встановлено" in t and "його дієздатність" in t
        assert "яким він передоручить" not in t and "яким представник передоручить" in t
        t, w = _tekst("notatka", seed)
        autor = w.osoby["autor"].plec
        assert (f"{'Відповідальним' if autor == 'M' else 'Відповідальною'} за ведення справи" in t)
        t, w = _tekst("med_zaswiadczenie", seed)
        if w.osoby["pacjent"].plec == "K":
            assert "уповноваженій нею особі" in t and "ним особі" not in t
        else:
            assert "уповноваженій ним особі" in t
    assert wid_k >= 5 and wid_m >= 5


# ----------------------------------------------------------------------------- I4, I5, M10: poświadczenie notarialne
def test_poswiadczenie_obowiazkowe_notariusz_w_narzedniku_i_przypis():
    for seed in range(25):
        t, w = _tekst("pelnomocnictwo", seed)
        n = w.osoby["notariusz"]
        assert f"посвідчено мною, {odmiana_uk.odmien(n.imie, n.po_batkovi, n.nazwisko, n.plec, 'oru')}, приватним нотаріусом" in t
        assert "статті 31 Закону України «Про нотаріат»" in t and "державне мито" not in t
        assert "до остаточного розгляду справи" not in t and "строком на три роки" in t
        assert "визнавати позов" not in t and "відповіді на відзиви" in t


# ----------------------------------------------------------------------------- I6, I7, M15, M16: sądy
def test_pule_sadow_rozlaczne_bez_zlikwidowanego_i_z_kodami():
    wszystkie = [n for n, _ in _SADY_POWSZECHNE + _SADY_GOSPODARCZE + _SADY_APELACYJNE]
    assert not any("Київський апеляційний" in n for n in wszystkie)
    assert not any("Салтівський" in n or "Індустріальний" in n for n in wszystkie)       # M16: nazwy niepewne
    assert len(wszystkie) == len(set(wszystkie))
    assert all(n.startswith("Господарський суд") for n in GOSPODARCZE)
    assert not any("апеляційн" in n for n, _ in _SADY_POWSZECHNE + _SADY_GOSPODARCZE)
    g = GeneratorUK("uk", 5)
    for _ in range(100):
        assert g.sad() in {n for n, _ in _SADY_POWSZECHNE}
        assert g.sad(poziom="gospodarczy") in GOSPODARCZE
        assert g.sad(poziom="apelacja").startswith("Північний апеляційний")


def test_numer_sprawy_zaczyna_sie_od_kodu_wylosowanego_sadu():
    g = GeneratorUK("uk", 8)
    kody = dict(_SADY_POWSZECHNE + _SADY_GOSPODARCZE)
    for _ in range(60):
        nazwa = g.sad(poziom=random.choice(("powszechny", "gospodarczy")))
        assert g.sygnatura(rok=2024).split("/")[0] == kody[nazwa]


def test_sady_w_szablonach_wg_rodzaju_sprawy():
    for seed in range(30):
        for typ in ("pelnomocnictwo", "email", "med_zaswiadczenie"):       # osoby fizyczne: sąd powszechny (ЦПК)
            t, w = _tekst(typ, seed)
            assert not any(n in t for n in GOSPODARCZE) and "апеляційний господарський суд" not in t, typ
            kod = dane_uk._SADY_POWSZECHNE
            assert any(n in t for n, _ in kod) or typ == "email", typ         # akapit z sądem jest w e-mailu opcjonalny
            m = re.search(r"№ (\d{3})/\d+/\d{2}", t)
            if m:
                assert dict(kod)[w.encje["sad"].sad_nazwa] == m.group(1), typ     # kod z numeru sprawy = kod sądu dokumentu
        t, w = _tekst("notatka", seed)                                      # spór ТОВ–ТОВ: sąd gospodarczy
        assert any(n in t for n in GOSPODARCZE) and "районний" not in t and "міський суд" not in t
    t, _ = _tekst("email", 1)
    assert "стаття 435 Цивільного процесуального кодексу України" in t


# ----------------------------------------------------------------------------- I8, I9, M14: e-mail
def test_email_role_stron_i_termin_odpowiedzi_na_pozew():
    from pbench import odmiana_uk as ou
    zgloszone = z_terminem = 0
    for seed in range(15):
        t, w = _tekst("email", seed)
        k, p = w.osoby["klient"], w.osoby["przeciwnik"]
        pozew = f"позовом {ou.odmien(p.imie, p.po_batkovi, p.nazwisko, p.plec, 'rod')} до {ou.odmien(k.imie, k.po_batkovi, k.nazwisko, k.plec, 'rod')}"
        assert "позовом" not in t or pozew in t         # akapit z opisem sprawy jest opcjonalny
        zgloszone += "позовом" in t
        assert "не підлягає продовженню" not in t and ("строк для подання відзиву" not in t or "встановлений ухвалою суду" in t)
        z_terminem += "встановлений ухвалою суду" in t
        assert "платіжного доручення" not in t
        for akapit in t.split("\n"):                                      # akapity treści nie zaczynają się małą literą
            if akapit.startswith(("відповідно", "повідомляю", "дякую")):
                pytest.fail(akapit[:40])
    assert zgloszone >= 3 and z_terminem >= 3


# ----------------------------------------------------------------------------- I10: dyplom w czerwcu–lipcu
def test_cv_dyplom_bez_przyimka_i_w_czerwcu_lipcu():
    for seed in range(40):
        t, w = _tekst("cv", seed)
        d = w.kontekst.daty
        assert d["cv_studia"].month in (6, 7) and d["cv_studia"] < d["cv_od2"] and d["cv_studia"].weekday() < 5
        assert "закінчив у" not in t and "закінчила у" not in t
        assert "диплом " + ("отримав" if w.osoby["kandydat"].plec == "M" else "отримала") in t


# ----------------------------------------------------------------------------- I11, M-2: osoby publiczne
OSOBY_PUBLICZNE = [
    ("Леонід", "Кравчук"), ("Надія", "Савченко"), ("Андрій", "Мельник"), ("Ігор", "Клименко"), ("Сергій", "Марченко"),
    ("Павло", "Петренко"), ("Анатолій", "Гриценко"), ("Олексій", "Гончаренко"), ("Юрій", "Бойко"),
    ("Олександр", "Мороз"), ("Сергій", "Лещенко"), ("Олександр", "Ткаченко"), ("Олександр", "Литвиненко"),
    ("Олександр", "Захарченко"), ("Микола", "Лисенко"), ("Дмитро", "Гнатюк"), ("Андрій", "Ярмоленко"),
    ("Олександр", "Зінченко"), ("Віктор", "Петренко"), ("Святослав", "Шевчук"), ("Олена", "Кравець"),
    ("Тарас", "Шевченко"), ("Андрій", "Шевченко"), ("Олександр", "Усик"), ("Богдан", "Хмельницький"),
    # N5 (partia 1): pary z przeglądu H1 i z przeglądu pul
    ("Іван", "Дзюба"), ("Артем", "Дзюба"), ("Віталій", "Захарченко"), ("Юрій", "Шевчук"), ("Андрій", "Кузьменко"),
    ("Оксана", "Марченко"), ("Михайло", "Гаврилюк"), ("Михайло", "Бойчук"), ("Юрій", "Кравченко"),
    ("Ростислав", "Павленко"), ("Кирило", "Шевченко")]


def test_zadna_para_osoby_publicznej_nie_powstaje(monkeypatch):
    assert set(OSOBY_PUBLICZNE) <= _ZABRONIONE_PARY
    g = GeneratorUK("uk", 3)
    for imie, nazwisko in OSOBY_PUBLICZNE:
        plec = "K" if imie in {"Надія", "Олена", "Оксана"} else "M"
        zrodlo = {tuple(g._s("imiona_m")): imie, tuple(g._s("imiona_k")): imie, tuple(g._s("nazwiska")): nazwisko}
        monkeypatch.setattr(dane_uk, "wagowo", lambda r, pula, zrodlo=zrodlo: zrodlo.get(tuple(pula), pula[0]))
        with pytest.raises(RuntimeError, match="brak dopuszczalnej pary"):      # wymuszona para jest odrzucana w każdej próbie
            g._pib(plec)
    monkeypatch.undo()
    for ziarno in range(4):
        g = GeneratorUK("uk", ziarno)
        for _ in range(1200):
            imie, nazwisko, _, _ = g._pib(random.Random(ziarno).choice("MK"))
            assert (imie, nazwisko) not in OSOBY_PUBLICZNE


def test_n5_dziesiec_tysiecy_osob_bez_pary_z_listy_osob_publicznych():
    g = GeneratorUK("uk", 99)
    r = random.Random(99)
    zakazane = set(OSOBY_PUBLICZNE)
    for _ in range(10_000):
        plec = r.choice("MK")
        imie, nazwisko, _, _ = g._pib(plec)
        meskie = nazwisko if plec == "M" else next((m for m, z in ((n, dane_uk.nazwisko_zenskie(n)) for n in g._s("nazwiska"))
                                                    if z == nazwisko), nazwisko)
        assert (imie, nazwisko) not in zakazane and (imie, meskie) not in zakazane, (imie, nazwisko)


# ----------------------------------------------------------------------------- I12, M11: leki
def test_lewotyroksyna_w_mikrogramach():
    g = GeneratorUK("uk", 2)
    znalezione = 0
    for _ in range(300):
        for profil in (None, "interna"):
            for l in g.leki(3, profil):
                if l.startswith("Левотироксин"):
                    znalezione += 1
                    assert l.endswith(" мкг") and not l.endswith(" мг")
                else:
                    assert l.endswith(" мг") or l.endswith(" мкг")
    assert znalezione > 10


def test_leki_dobrane_do_rozpoznan():
    g = GeneratorUK("uk", 4)
    g._rozpoznania = ["N39.0 Інфекція сечовивідних шляхів без уточненої локалізації", "E11.9 Цукровий діабет 2 типу без ускладнень"]
    for _ in range(40):
        pierwszy, drugi, trzeci = g.leki(3, "interna")
        assert pierwszy.split(" ")[0] in {"Нітрофурантоїн", "Амоксицилін"} and drugi.split(" ")[0] in {"Нітрофурантоїн", "Амоксицилін"}
        assert trzeci.startswith(("Метформін", "Гліклазид"))
    g._rozpoznania = ["E03.9 Гіпотиреоз неуточнений"]
    assert g.leki(1)[0].startswith("Левотироксин")
    assert all(any(l.partition("|")[0] in x for x in (SLOWNIKI / "leki.txt").read_text(encoding="utf-8").splitlines())
               for lista in dane_uk._LEKI_DO_ROZPOZNAN.values() for l in lista)


def test_pacjent_w_zaswiadczeniu_ma_leki_do_rozpoznania():
    for seed in range(25):
        w = zbuduj_z_kontekstem(SZABLONY_UK["med_zaswiadczenie"], Generator("uk", seed), random.Random(seed))
        e = w.encje["pacjent"]
        glowne = e.diagnozy[0].split(" ", 1)[0][:3]
        zalecane = dane_uk._LEKI_DO_ROZPOZNAN.get(glowne)
        if zalecane:
            assert e.leki[0].split(" ")[0] in zalecane or e.leki[0].rsplit(" ", 2)[0] in zalecane, (e.diagnozy, e.leki)


# ----------------------------------------------------------------------------- M2, M3, M12, M17–M22: dane
def test_kancelarie_tylko_adwokackie_obiednania_i_email_z_nazwy():
    g = Generator("uk", 6)
    for _ in range(80):
        f = g.firma(rodzaj="kancelaria")
        assert f.forma == "АО" and f.nazwa.startswith("Адвокатське об’єднання «")
        n1 = re.search(r"«([^,»]+?)(?:,| та| і|»)", f.nazwa).group(1)
        assert transliteruj(n1, "kmu2010").lower().replace("’", "")[:6] in f.email, (f.nazwa, f.email)


def test_kwoty_tylko_hrn_i_brak_nazwy_prywatnej_kliniki():
    g = Generator("uk", 7)
    for _ in range(100):
        assert g.kwota().endswith(" грн")
    assert "Добробут" not in dane_uk._RDZENIE_MED


def test_placowki_bez_numeru_biura_ulice_i_telefony_stacjonarne():
    import phonenumbers
    g = Generator("uk", 9)
    for _ in range(100):
        assert "оф." not in g.firma(rodzaj="placowka").adres.numer
    ulice = (SLOWNIKI / "ulice.txt").read_text(encoding="utf-8").splitlines()
    assert not {"вул. Гагаріна", "пл. Ринок", "вул. Городоцька", "вул. Личаківська", "вул. Хортицька"} & set(ulice)
    for _ in range(400):
        assert re.fullmatch(r"(\+380|0) 00 \d{3} \d\d \d\d|\+38000\d{7}", g.osoba().telefon)      # fikcyjny format 00…
    assert "Кременчук|Полтавська обл.|39|536" in (SLOWNIKI / "miejscowosci.txt").read_text(encoding="utf-8").splitlines()


def test_edrpou_zaczyna_sie_od_0_do_4_i_poprawna_suma():
    rng = random.Random(1)
    for _ in range(2000):
        n = dane_uk.edrpou(rng)
        assert ua_edrpou.is_valid(n) and n[0] in "01234", n


def test_slownik_imion_po_ojcu_rosyjska_kolumna_kirillovich():
    wiersz = next(l for l in (SLOWNIKI / "imiona_ojcow.txt").read_text(encoding="utf-8").splitlines() if l.startswith("Кирилович|"))
    assert wiersz.split("|") == ["Кирилович", "Кирилівна", "Кириллович", "Кирилловна"]


def test_feminatywy_zgodne_z_rodzajem_w_cv_i_zaswiadczeniu():
    for seed in range(30):
        t, w = _tekst("cv", seed)
        k = w.osoby["kandydat"].plec
        assert (("Юристка |" in t) and "юрисконсультка" in t and "стажерка" in t) == (k == "K")
        assert (("Юрист |" in t) and "юрисконсульт," in t) == (k == "M")
        assert "Водійське" not in t and "конкурсу" not in t and "Посвідчення водія категорії B" in t
        t, w = _tekst("med_zaswiadczenie", seed)
        assert ("Лікарка:" in t and "лікарка-терапевтка" in t) == (w.osoby["lekarz"].plec == "K")


def test_cv_naglowki_zawsze_z_trescia():
    for seed in range(60):
        t, _ = _tekst("cv", seed)
        wiersze = t.split("\n")
        for naglowek in ("НАВИЧКИ ТА МОВИ", "РЕКОМЕНДАЦІЇ", "ОСВІТА", "ДОСВІД РОБОТИ"):
            assert naglowek in wiersze
            nastepny = wiersze[wiersze.index(naglowek) + 1]
            assert nastepny and nastepny.upper() != nastepny, (naglowek, nastepny)


def test_notatka_i_email_poprawki_tresci():
    for seed in range(20):
        t, w = _tekst("notatka", seed)
        assert "платіжні інструкції" in t and "платіжні доручення" not in t
        assert "інфляційні втрати" in t and "частина друга статті 625" in t
        assert "\nВід: " in t and "\nАвтор: " not in t.split("Тема:")[0].replace("\nАвтор: ", "", 1)
        assert "Додатки: копія договору поставки, копія претензії." in t and "(відсутня)" not in t and "сплив" in t


def test_data_slownie_tylko_w_ukrainskim():
    t, w = _tekst("pelnomocnictwo", 3)
    assert re.search(r"м\. .+, [а-яіїє’ ]+ дві тисячі [а-яіїє’ ]+ року", t) and not re.search(r"\d", t.splitlines()[0])   # M10: cała data słownie


# ----------------------------------------------------------------------------- M-8, M24: transliteracja polska
def test_transliteracja_polska_podwojne_l_i_koncowy_znak_miekki():
    assert transliteruj("Ілля", "polski") == "Illa"
    assert transliteruj("Кравець", "polski") == "Kraweć"
    assert transliteruj("Ірпінь", "polski") == "Irpiń"
    assert transliteruj("Василь", "polski") == "Wasyl" and transliteruj("Ольга", "polski") == "Olha"
    assert transliteruj("Ляшко", "polski") == "Laszko"
    assert transliteruj("Любомир", "polski") == "Lubomyr"
    assert transliteruj("Уляна", "polski") == "Ulana"
    assert transliteruj("Мар’яна", "iso9").startswith("Mar")          # M-9: apostrof – wybór opisany w docstringu


# ----------------------------------------------------------------------------- I13, M23: odmiana polska w trybie ukraińskim
@pytest.mark.parametrize("nazwisko,forma", [("Bereżna", "Bereżnej"), ("Biła", "Biłej"), ("Pidhorna", "Pidhornej"),
                                           ("Kowalowa", "Kowalowej"), ("Wasyliewa", "Wasyliewej")])
def test_zenskie_nazwiska_przymiotnikowe_po_polsku(nazwisko, forma):
    assert odmien_pl("Natalia", nazwisko, "K", "dop", ukrainskie=True) == f"Natalii {forma}"
    assert odmien_pl("", nazwisko, "K", "bier", ukrainskie=True) == forma[:-2] + "ą"
    assert odmien_pl("", nazwisko, "K", "narz", ukrainskie=True) == forma[:-2] + "ą"


def test_polskie_krawec_i_lesia_w_trybie_ukrainskim():
    assert [odmien_pl("", "Kraweć", "M", p, ukrainskie=True) for p in ("dop", "cel", "bier", "narz", "msc")] == [
        "Krawcia", "Krawciowi", "Krawcia", "Krawciem", "Krawciu"]
    assert [odmien_pl("Łesia", "", "K", p, ukrainskie=True) for p in ("dop", "cel", "bier", "narz", "msc")] == [
        "Łesi", "Łesi", "Łesię", "Łesią", "Łesi"]
    assert odmien_pl("Orysia", "Kravchuk", "K", "dop", ukrainskie=True).startswith("Orysi ")


def test_tryb_polski_bez_zmian_znane_bledy_trzonu_zachowane():
    """Trzon korpusu zawiera te formy (zob. metodyka/znane-ograniczenia.md) – poprawka zmieniłaby opublikowane sumy."""
    assert odmien_pl("Anna", "Czarna", "K", "dop") == "Anny Czarniej"
    assert odmien_pl("Anna", "Mała", "K", "dop") == "Anny Małiej"


# ----------------------------------------------------------------------------- N1/N2 (partia 1)
def test_n2_pelnomocnictwo_podpis_mocodawcy_przed_poswiadczeniem_i_podpis_notariusza():
    for seed in range(1, 6):
        t, _ = _tekst("pelnomocnictwo", seed)
        assert t.index("Підпис довірител") < t.index("Цю довіреність посвідчено")          # mocodawca podpisuje pierwszy
        assert re.search(r"Приватний нотаріус _+ \S+", t.split("Цю довіреність посвідчено")[1])  # linia podpisu notariusza
        assert re.search(r"підписано довірител(ем|ькою) у моїй присутності", t)


@pytest.mark.parametrize("nazwisko,dop,bier", [("Bereżnaja", "Bereżnej", "Bereżną"), ("Bełaja", "Bełej", "Bełą"),
                                               ("Pidhornaja", "Pidhornej", "Pidhorną"), ("Tołstaja", "Tołstej", "Tołstą")])
def test_n4_rosyjska_pisownia_zenskich_nazwisk_przymiotnikowych(nazwisko, dop, bier):
    assert odmien_pl("Natalia", nazwisko, "K", "dop", ukrainskie=True) == f"Natalii {dop}"
    assert odmien_pl("", nazwisko, "K", "bier", ukrainskie=True) == bier
    assert odmien_pl("", nazwisko, "K", "msc", ukrainskie=True) == dop


def test_m10_data_slownie_w_calosci():
    from pbench.odmiana_uk import data_slownie_pelna
    assert data_slownie_pelna(dt.date(2023, 12, 22)) == "двадцять другого грудня дві тисячі двадцять третього року"
    assert data_slownie_pelna(dt.date(2020, 1, 1)) == "першого січня дві тисячі двадцятого року"
    assert data_slownie_pelna(dt.date(2025, 3, 31)) == "тридцять першого березня дві тисячі двадцять п’ятого року"
    assert data_slownie_pelna(dt.date(2024, 7, 30)) == "тридцятого липня дві тисячі двадцять четвертого року"
    assert data_slownie_pelna(dt.date(2019, 5, 15)) == "п’ятнадцятого травня дві тисячі дев’ятнадцятого року"
    assert data_slownie_pelna(dt.date(2010, 9, 10)) == "десятого вересня дві тисячі десятого року"


def test_n6_leki_miedzynarodowe_nazwy_i_rozna_kolejnosc_dla_rozpoznania():
    assert "Фурадонін" not in (SLOWNIKI / "leki.txt").read_text(encoding="utf-8")
    assert "Нітрофурантоїн" in (SLOWNIKI / "leki.txt").read_text(encoding="utf-8")
    pierwsze = set()
    for ziarno in range(60):
        g = GeneratorUK("uk", ziarno)
        g._rozpoznania = ["N39.0 Інфекція сечовивідних шляхів без уточненої локалізації"]
        pierwsze.add(g.leki(1)[0].split(" ")[0])
    assert pierwsze == {"Нітрофурантоїн", "Амоксицилін"}               # lek losowany z listy dla rozpoznania


def test_m21_nazwa_placowki_nie_jest_znana_marka():
    assert "Лелека" not in dane_uk._RDZENIE_MED
