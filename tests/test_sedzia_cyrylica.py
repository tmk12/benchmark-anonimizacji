"""Sędzia tekstu i pliku na cyrylicy (ukraińskiej, z transliteracjami i homoglifami): nic się nie wywraca, sanity działa –
oryginał jako wynik: wszystko wycieka; „idealny uczestnik” (każda wartość zamieniona na [KATEGORIA_n]): 0 wycieków.
Poziom encji („transliteracje jako ta sama encja”) i porównanie homoglifów po szkielecie (H6a) – `test_h6a.py`."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from pbench import przypadki as P, trudne
from pbench.model import Wartosc, Wykrycie
from pbench.sedzia import tekst as sedzia_tekst
from pbench.sedzia.normalizacja import normalizuj, same_alnum, zloz_diakrytyki
from pbench.sedzia.plik import ocen_plik
from pbench.sedzia.sanity import Maskowanie, wartosci_wpisu

os.environ.setdefault("PBENCH_OCR_WATKI", "2")


def test_normalizacja_cyrylicy():
    assert normalizuj("ШЕВЧЕНКО  Олександр\u00a0Петрович") == "шевченко олександр петрович"
    assert normalizuj("Мар’яна") == "мар’яна"
    assert same_alnum("РНОКПП 3125-523449") == "рнокпп3125523449"
    assert same_alnum("UA21 3223 1300 0002") == "ua21322313000002"
    assert zloz_diakrytyki(normalizuj("Їжак Йосип")) == "іжак иосип"          # ї → і, й → и (rozbicie NFKD)
    # homoglify nie są scalane (osobne punkty kodowe): normalizacja zachowuje mieszany zapis
    assert normalizuj("Kоwalski") != normalizuj("Kowalski")


def _dokument_uk(typ: str = "umowa", seed: int = 2):
    import random

    from pbench.budowa import zbuduj_z_kontekstem
    from pbench.dane import Generator
    from pbench.linearyzacja import linearyzuj_z_wartosciami
    from pbench.szablony.trudne import SZABLONY_UK
    w = zbuduj_z_kontekstem(SZABLONY_UK[typ], Generator("uk", seed), random.Random(seed))
    tekst, spany, wartosci = linearyzuj_z_wartosciami(w.dokument)
    return tekst, spany, wartosci


def test_sedzia_tekstowy_cyrylica_pelne_pokrycie_i_brak_wykryc():
    tekst, spany, _ = _dokument_uk()
    R = sedzia_tekst.RegulyWycieku()
    idealne = [Wykrycie(s.start, s.end, s.kategoria) for s in spany]
    o = sedzia_tekst.ocen_tekst(spany, idealne, tekst, R)
    assert o.wycieki == [] and o.fp_znaki == 0 and o.pokrycie_znakowe == 1.0 and o.char_f2 == 1.0
    pusto = sedzia_tekst.ocen_tekst(spany, [], tekst, R)
    assert len(pusto.wycieki) >= len(spany) * 0.8 and pusto.pokrycie_znakowe == 0.0       # offsety w znakach, nie bajtach UTF-8


def test_sedzia_tekstowy_cyrylica_czesciowe_pokrycie_nazwiska_to_wyciek():
    tekst, spany, wartosci = _dokument_uk("pelnomocnictwo", 4)
    R = sedzia_tekst.RegulyWycieku()
    i = next(k for k, w in enumerate(wartosci) if w.id.startswith("mocodawca.pelne"))
    s = spany[i]
    reszta = [Wykrycie(x.start, x.end, x.kategoria) for k, x in enumerate(spany) if k != i]
    imie_dlugosc = len(wartosci[i].tekst.split()[0])
    tylko_pierwsze_slowo = reszta + [Wykrycie(s.start, s.start + imie_dlugosc, "OSOBA")]
    o = sedzia_tekst.ocen_tekst(spany, tylko_pierwsze_slowo, tekst, R)
    assert any(w[0] == s.wartosc_id for w in o.wycieki)                   # nazwisko i imię po ojcu nie pokryte


def test_sedzia_tekstowy_transliteracje_to_osobne_wartosci_gold():
    """Każdy zapis (cyrylica i każda transliteracja) to osobna wartość: wykrycie samej cyrylicy zostawia wyciek zapisu
    łacińskiego (poziom encji – miara opisowa `pbench.ocen`, `test_h6a.py`)."""
    import random

    from pbench.budowa import zbuduj_z_kontekstem
    from pbench.dane import Generator
    from pbench.linearyzacja import linearyzuj_z_wartosciami
    from pbench.szablony.trudne import SZABLONY_WSTAWKI
    gen = Generator("pl", 9)
    gen.systemy_translit = {"s1": "polski", "s2": "cyr", "s3": "kmu2010", "s4": "iso9"}
    w = zbuduj_z_kontekstem(SZABLONY_WSTAWKI[("pl", "umowa")], gen, random.Random(9), "tr")
    tekst, spany, wartosci = linearyzuj_z_wartosciami(w.dokument)
    R = sedzia_tekst.RegulyWycieku()
    cyr = [k for k, v in enumerate(wartosci) if v.id.startswith("wykonawca.pelne_im") and v.translit is None]
    lac = [k for k, v in enumerate(wartosci) if v.id.startswith("wykonawca.pelne_im") and v.translit is not None]
    assert cyr and lac
    wykr = [Wykrycie(x.start, x.end, x.kategoria) for k, x in enumerate(spany) if k not in lac]
    o = sedzia_tekst.ocen_tekst(spany, wykr, tekst, R)
    assert {spany[k].wartosc_id for k in lac} <= {x[0] for x in o.wycieki}
    assert not ({spany[k].wartosc_id for k in cyr} & {x[0] for x in o.wycieki})


@pytest.fixture(scope="module")
def zestaw(tmp_path_factory):
    """Po kilka dokumentów każdego przypadku w formatach tekstowych."""
    wynik = {}
    for przypadek, n in ((P.CYRYLICA_DOKUMENT_UK, 10), (P.CYRYLICA_WSTAWKA, 8), (P.TRANSLITERACJA, 8), (P.HOMOGLIFY, 10)):
        cel = tmp_path_factory.mktemp(przypadek)
        wpisy = trudne.zbuduj_przypadek(cel, przypadek, n, formaty=("docx", "pdf", "eml", "msg"))
        wynik[przypadek] = (cel, wpisy)
    return wynik


#: Role e-mail z odnośników PDF, których wyciek w `pdf:surowe` jest znanym problemem trzonu (zob. test poniżej).
ROLE_EMAIL_Z_HIPERLACZY = ("kancelaria.email", "placowka.email", "nadawca.email")


def _pozycje(przypadek: str, wpisy: list[dict]) -> dict[str, trudne.PozycjaTrudna]:
    return {w["id"]: trudne.PozycjaTrudna(w["id"], w["jezyk"], w["typ"], w["format"], przypadek) for w in wpisy}


@pytest.mark.parametrize("przypadek", [P.CYRYLICA_DOKUMENT_UK, P.CYRYLICA_WSTAWKA, P.TRANSLITERACJA, P.HOMOGLIFY])
def test_sanity_oryginal_wycieka_idealny_nie(zestaw, tmp_path, przypadek):
    cel, wpisy = zestaw[przypadek]
    poz = _pozycje(przypadek, wpisy)
    assert wpisy
    for w in wpisy:
        ws = wartosci_wpisu(w)
        orig = cel / w["plik"]
        a = ocen_plik(orig, orig, ws, leksykon={})
        assert a.status == "OK"
        wyciekly = {x[0] for x in a.wycieki}
        pominiete = set(a.niewykrywalne) | set(a.niejednoznaczne)
        brak = [x.id for x in ws if x.id not in wyciekly and x.id not in pominiete]
        assert not brak, (w["id"], brak[:5])                      # oryginał: wyciekają wszystkie wartości możliwe do wycieku
        assert a.wartosci_ocenione >= len(ws) * 0.8
        wyjscie = tmp_path / w["id"]
        wyjscie.mkdir()
        r = trudne.generuj_dokument_trudny(poz[w["id"]], trudne.ZIARNO_TRUDNE, w["split"], wyjscie, maskuj=Maskowanie())
        b = ocen_plik(orig, wyjscie / r["plik"], ws, leksykon={})
        assert b.status == "OK" and b.integralnosc["otwiera_sie"]
        znane = [x for x in b.wycieki if x[0].startswith(ROLE_EMAIL_Z_HIPERLACZY)]
        zostaly = [x for x in b.wycieki if not x[0].startswith(ROLE_EMAIL_Z_HIPERLACZY)]
        # Znany problem trzonu (nie warstwy trudnej): maskowanie PDF nie zastępuje adresu e-mail w odnośniku (hiperłącze
        # mailto:) – ten sam wyciek daje korpus PL. Tolerancja dotyczy wyłącznie e-maili trzech ról nagłówkowych w
        # warstwie `pdf:surowe`; każdy inny wyciek (rola, kategoria, warstwa) jest błędem.
        assert all(x[1] == "EMAIL" and x[2] == "pdf:surowe" for x in znane), (w["id"], znane[:3])
        assert not zostaly, (w["id"], zostaly[:3])


def test_sanity_skan_ocr_ukr_oryginal_i_idealny(tmp_path):
    if not (Path(__file__).parents[1] / "vendor" / "tessdata" / "ukr.traineddata").exists():
        pytest.skip("brak ukr.traineddata")
    os.environ["PBENCH_OCR_CACHE"] = str(tmp_path / "ocr")
    wpisy = trudne.zbuduj_przypadek(tmp_path / "k", P.CYRYLICA_DOKUMENT_UK, 24, formaty=("skan",))
    assert wpisy
    w = next(x for x in wpisy if x["typ"] == "pelnomocnictwo")
    cel = tmp_path / "k"
    ws = wartosci_wpisu(w)
    orig = cel / w["plik"]
    a = ocen_plik(orig, orig, ws, leksykon={})
    assert a.wartosci_ocenione >= len(ws) * 0.7 and len(a.wycieki) >= a.wartosci_ocenione * 0.9      # OCR `ukr`: ≥ 90% ocenianych
    poz = trudne.PozycjaTrudna(w["id"], w["jezyk"], w["typ"], w["format"], P.CYRYLICA_DOKUMENT_UK)
    wyjscie = tmp_path / "idealny"
    wyjscie.mkdir()
    r = trudne.generuj_dokument_trudny(poz, trudne.ZIARNO_TRUDNE, w["split"], wyjscie, maskuj=Maskowanie())
    b = ocen_plik(orig, wyjscie / r["plik"], ws, leksykon={})
    assert b.status == "OK" and not [x for x in b.wycieki if x[1] != "EMAIL"]
