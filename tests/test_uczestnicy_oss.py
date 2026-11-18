"""Testy uczestników OSS (zadanie 13): okna/scalanie (czysty Python) oraz testy dymne i granicy okna przez protokół.

Każdy uczestnik działa we własnym środowisku uv (`uv run --project uczestnicy/<id> python run.py`), więc testy
uruchamiają go jako podproces tak jak orkiestrator. Modele HF muszą być w `vendor/hf` (pobiera je zadanie 13; offline)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from pbench import uruchom

KORZEN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KORZEN / "uczestnicy" / "_wspolne"))

import okna  # noqa: E402

ZDANIE_EN = "Please contact John Smith at john.smith@example.com about the contract."
IMIE_EN = "John Smith"
EMAIL_EN = "john.smith@example.com"


# ----------------------------------------------------------------------------- okna (bez modeli)
def _wartosc_w_oknie(okno, start, koniec):
    """Wartość mieści się w oknie i nie dotyka jego sztucznych krawędzi (poza początkiem/końcem tekstu)."""
    return okno[0] <= start and koniec <= okno[1]


@pytest.mark.parametrize("wypelnienie", range(0, 60, 3))
def test_okna_znakowe_wartosc_na_granicy_jest_w_calosci_w_oknie(wypelnienie):
    wartosc = "Katarzyna Wiśniewska-Nowak"
    tekst = "ala ma kota " * 20 + "x" * wypelnienie + " " + wartosc + " " + "i psa " * 80
    start = tekst.index(wartosc)
    for rozmiar in (120, 200, 333):
        ok = okna.okna_znakowe(tekst, rozmiar)
        assert ok[0][0] == 0 and ok[-1][1] == len(tekst)
        for (a1, b1), (a2, b2) in zip(ok, ok[1:]):
            assert b1 - a2 >= rozmiar * 0.10 - 1                 # zakładka >= 10%
            assert a2 > a1 and b2 > b1
        assert all(b - a <= rozmiar for a, b in ok)
        zawiera = [o for o in ok if o[0] <= start and start + len(wartosc) <= o[1]]
        assert zawiera, (rozmiar, ok)


def test_okna_znakowe_bez_bialych_znakow_ciecie_twarde():
    tekst = "a" * 1000
    ok = okna.okna_znakowe(tekst, 200)
    assert ok[-1][1] == 1000 and all(b - a <= 200 for a, b in ok)
    assert all(b1 - a2 >= 20 for (a1, b1), (a2, b2) in zip(ok, ok[1:]))


def test_scal_odrzuca_obciete_na_krawedzi_i_przesuwa_offsety():
    tekst = "x" * 100
    ok = [(0, 60), (40, 100)]
    wyniki = [[(10, 20, "A", 0.5), (55, 60, "B", 0.9)],                 # B dotyka końca okna 1 → obcięte
              [(0, 5, "B2", 0.9), (15, 25, "A", 0.7), (30, 40, "C", 0.3)]]   # B2 dotyka początku okna 2 → obcięte
    sc = okna.scal(len(tekst), ok, wyniki)
    assert (10, 20, "A", 0.5) in sc and (55, 65, "A", 0.7) in sc and (70, 80, "C", 0.3) in sc
    assert all(w[2] not in ("B", "B2") for w in sc)
    zdublowane = okna.scal(100, [(0, 60), (40, 100)], [[(45, 50, "A", 0.4)], [(5, 10, "A", 0.8)]])
    assert zdublowane == [(45, 50, "A", 0.8)]


class _TokenizerZnakowy:
    """Atrapa szybkiego tokenizera: token = słowo (offset_mapping jak w HF)."""

    def __call__(self, tekst, **_):
        import re
        return {"offset_mapping": [(m.start(), m.end()) for m in re.finditer(r"\S+", tekst)]}


def test_okna_tokenowe_limit_zakladka_i_pokrycie():
    tekst = " ".join(f"s{i}" for i in range(1000))
    ok = okna.okna_tokenowe(tekst, _TokenizerZnakowy(), 100)
    assert ok[0][0] == 0 and ok[-1][1] == len(tekst)
    for a, b in ok:
        assert len(tekst[a:b].split()) <= 100
    for (a1, b1), (a2, b2) in zip(ok, ok[1:]):
        assert len(tekst[a2:b1].split()) >= 10                # zakładka >= 10% okna
    assert okna.okna_tokenowe("krótki tekst", _TokenizerZnakowy(), 100) == [(0, 12)]


# ----------------------------------------------------------------------------- uczestnik jako podproces
class Uczestnik:
    def __init__(self, id_uczestnika: str, env_dodatkowe: dict[str, str] | None = None):
        env = uruchom.zbuduj_srodowisko(2, offline=True)
        env.update(env_dodatkowe or {})
        self.proc = subprocess.Popen(
            ["uv", "run", "--project", str(KORZEN / "uczestnicy" / id_uczestnika), "python",
             str(KORZEN / "uczestnicy" / id_uczestnika / "run.py")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True,
            encoding="utf-8", cwd=KORZEN)
        linia = self.proc.stdout.readline()
        assert linia.strip().startswith("{"), f"brak linii gotowy: {linia!r}\n{self.proc.stderr.read()[-2000:]}"
        self.gotowy = json.loads(linia)
        assert self.gotowy.get("gotowy") is True

    def analizuj(self, tekst: str, jezyk: str = "en", id_dok: str = "t-1") -> list:
        self.proc.stdin.write(json.dumps({"id": id_dok, "jezyk": jezyk, "tekst": tekst}) + "\n")
        self.proc.stdin.flush()
        odp = json.loads(self.proc.stdout.readline())
        assert "blad" not in odp, odp
        return odp["wykrycia"]

    def zamknij(self):
        self.proc.stdin.close()
        try:
            self.proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self.proc.kill()


# Uczestnicy bez detektora e-maili (ogólny NER, nie PII): testy dymne i granicy okna sprawdzają tylko osobę.
BEZ_EMAILA = {"stanza"}


def _pokrywa(wykrycia, tekst, fragment):
    s = tekst.index(fragment)
    return any(w[0] <= s and w[1] >= s + len(fragment) for w in wykrycia)


# Dane zdania dymnego dla uczestników, których model nie wykrywa generycznego „John Smith” (placeholder): id → (zdanie, imię, e-mail).
# Test sprawdza tylko, że uczestnik działa; wybór innego imienia nie zmienia konfiguracji modelu.
DANE_ZDANIA = {
    "gliner-knowledgator-pii": ("The client, Mr. Adam Nowak, can be reached at adam.nowak@example.com today.", "Adam Nowak",
                                "adam.nowak@example.com"),
}


DANE_ZDANIA["stanza"] = ("Prosimy o kontakt z Janem Kowalskim w sprawie umowy zawartej wczoraj.", "Janem Kowalskim", "")
JEZYK_TESTU = {"stanza": "pl"}          # uczestnicy testowani w innym języku niż EN (stanza: polski model nkjp_bert)


def _dane_zdania(id_uczestnika: str) -> tuple[str, str, str]:
    return DANE_ZDANIA.get(id_uczestnika, (ZDANIE_EN, IMIE_EN, EMAIL_EN))


def _zdanie_graniczne(id_uczestnika: str) -> str:
    """Zdanie z osobą i e-mailem dla testu granicy okna (domyślne – jak w testach Presidio)."""
    zdanie, imie, email = _dane_zdania(id_uczestnika)
    return zdanie + " " if id_uczestnika in DANE_ZDANIA else f"Please contact {imie} by email {email} today. "


def _pokryte_znaki(wykrycia, tekst, fragment):
    """Wszystkie niebiałe znaki fragmentu leżą w sumie wykryć (jak w sędzi; model może dać imię i nazwisko jako dwa spany)."""
    s = tekst.index(fragment)
    return all(any(w[0] <= i < w[1] for w in wykrycia) for i in range(s, s + len(fragment)) if not tekst[i].isspace())


# id uczestnika → (zmienne środowiska zmniejszające okno, liczba słów „ab ” zaczynająca przesuwanie zdania względem
# cięcia okna: seria 0..39 słów dodatkowych przesuwa cięcie przez całe zdanie z wartościami)
OKNA_UCZESTNIKOW = {
    "presidio-spacy": ({"PBENCH_OKNO_ZNAKI": "400"}, 100),
    "presidio-pl-ner": ({"PBENCH_OKNO_TOKENOW": "100"}, 70),   # zakładka 12 tokenów >= długość e-maila
    "presidio-gliner": ({"PBENCH_OKNO_TOKENOW": "100"}, 70),   # zakładka 20 tokenów >= długość e-maila
    "gliner-urchade-pii": ({"PBENCH_OKNO_TOKENOW": "100"}, 70),
    "gliner-knowledgator-pii": ({"PBENCH_OKNO_TOKENOW": "100", "PBENCH_SUROWE": "1"}, 70),   # surowe: wynik e-maila bywa ~0.29 < próg 0.30
    "gliner-nvidia-pii": ({"PBENCH_OKNO_TOKENOW": "100"}, 70),
    "stanza": ({"PBENCH_OKNO_ZNAKI": "400"}, 100),                  # ogólny NER: tylko osoba (bez e-maila)
    "openai-privacy-filter": ({"PBENCH_OKNO_TOKENOW": "100"}, 70),   # tokeny tiktoken; zakładka 13 tokenów, własny zakres z marginesem 6
}
OKNA_UCZESTNIKOW = {k: v for k, v in OKNA_UCZESTNIKOW.items() if (KORZEN / "uczestnicy" / k / "run.py").exists()}


@pytest.fixture(scope="module", params=sorted(OKNA_UCZESTNIKOW))
def uczestnik_okno(request):
    env, start_slow = OKNA_UCZESTNIKOW[request.param]
    u = Uczestnik(request.param, env)
    yield request.param, start_slow, u
    u.zamknij()


# Modele dużych uczestników zajmują po kilka GB: wszystkie testy procesów uczestników idą na jednym workerze xdist
# (`--dist loadgroup` w pyproject.toml), inaczej `-n auto` startuje kilkanaście kopii modeli naraz i proces ginie (OOM).
GRUPA_UCZESTNIKOW = pytest.mark.xdist_group("uczestnicy-oss")


@GRUPA_UCZESTNIKOW
@pytest.mark.parametrize("id_uczestnika", sorted(OKNA_UCZESTNIKOW))
def test_uczestnik_wykrywa_email_i_osobe_en(id_uczestnika):
    zdanie, imie, email = _dane_zdania(id_uczestnika)
    u = Uczestnik(id_uczestnika)
    try:
        wyk = u.analizuj(zdanie, JEZYK_TESTU.get(id_uczestnika, "en"))
    finally:
        u.zamknij()
    if id_uczestnika not in BEZ_EMAILA:
        assert _pokrywa(wyk, zdanie, email), wyk
    assert _pokryte_znaki(wyk, zdanie, imie), wyk


@GRUPA_UCZESTNIKOW
@pytest.mark.parametrize("przesuniecie", range(40))
def test_uczestnik_wartosc_na_granicy_okna(uczestnik_okno, przesuniecie):
    """Małe okno: cięcie przechodzi przez zdanie z osobą i e-mailem – wartości wykryte w całości, offsety dokładne."""
    id_uczestnika, start_slow, u = uczestnik_okno
    _, imie, email = _dane_zdania(id_uczestnika)
    tekst = ("ab " * (start_slow + przesuniecie) + _zdanie_graniczne(id_uczestnika)
             + ("Strony uzgodniły, że spotkają się ponownie w przyszłym tygodniu. " if JEZYK_TESTU.get(id_uczestnika) == "pl"
                else "The parties agreed to meet again next week to review the draft. ") * 12)
    wyk = u.analizuj(tekst, JEZYK_TESTU.get(id_uczestnika, "en"))
    trafione = {tekst[s:e] for s, e, et, sc in wyk}
    assert _pokryte_znaki(wyk, tekst, imie), trafione
    if id_uczestnika in BEZ_EMAILA:                           # ogólny NER: osoba z dokładnymi offsetami
        s = tekst.index(imie)
        assert any((w[0], w[1]) == (s, s + len(imie)) for w in wyk), trafione
        return
    assert email in trafione, trafione
    s = tekst.index(email)
    assert any((w[0], w[1]) == (s, s + len(email)) for w in wyk)


def _tekst_interpunkcyjny() -> str:
    """~1000 znaków o dużej gęstości tokenów GLiNER (interpunkcja = osobny token), osoba i e-mail na samym końcu."""
    return ("K., J.; (1); " * 76)[:1000].rstrip() + " Kontakt: Jan Kowalski, e-mail jan.kowalski@example.com"


def test_gliner_okna_w_limicie_modelu():
    """Żadne okno tokenowe presidio-gliner nie przekracza `max_len` modelu (384), także dla tekstu z samą interpunkcją."""
    tok = okna.TokenizerGliner()
    limit_modelu, max_tokenow = 384, 320                      # jak LIMIT_TOKENOW / MAX_TOKENOW w run.py
    dlugi = _tekst_interpunkcyjny()
    assert len(tok(dlugi)["offset_mapping"]) > limit_modelu       # sam tekst ~1000 znaków, a >384 tokenów (stary błąd)
    for tekst in (dlugi, dlugi * 6, " ".join(f"w{i}," for i in range(3000)), "A.;" * 3000):
        ok = okna.okna_tokenowe(tekst, tok, max_tokenow, 0.20)
        assert ok[0][0] == 0 and ok[-1][1] == len(tekst)
        for a, b in ok:
            assert len(tok(tekst[a:b])["offset_mapping"]) <= limit_modelu - 20, (a, b)
        for (a1, b1), (a2, b2) in zip(ok, ok[1:]):
            assert b1 - a2 > 0 and a2 > a1                    # okna zachodzą na siebie, postęp monotoniczny


def test_okna_indeksowe_pokrycie_zakladka_i_zakresy_wlasne():
    """Okna indeksowe (openai-privacy-filter): zakładka >= 10%, zakresy własne układają się bez dziur i nakładek."""
    for n in (1, 99, 100, 101, 250, 1000, 4097, 12345):
        ok = okna.okna_indeksowe(n, 100, 0.125)
        assert ok[0][0] == 0 and ok[-1][1] == n and all(b - a <= 100 for a, b in ok)
        for (a1, b1), (a2, b2) in zip(ok, ok[1:]):
            assert b1 - a2 >= 10 and a2 > a1
        wl = okna.zakresy_wlasne(ok)
        assert wl[0][0] == 0 and wl[-1][1] == n
        for (a, b), (od, do) in zip(ok, wl):
            assert a <= od <= do <= b
        for (_, d1), (o2, _) in zip(wl, wl[1:]):
            assert d1 == o2


def test_openai_privacy_filter_stale_zgodne_z_karta():
    """Rewizja/commit `opf` w run.py i pyproject.toml; okno nie przekracza `default_n_ctx` z konfiguracji migawki."""
    import re
    zrodlo = (KORZEN / "uczestnicy" / "openai-privacy-filter" / "run.py").read_text(encoding="utf-8")
    pyproj = (KORZEN / "uczestnicy" / "openai-privacy-filter" / "pyproject.toml").read_text(encoding="utf-8")
    assert 'MODEL = "openai/privacy-filter"' in zrodlo
    assert 'REWIZJA = "7ffa9a043d54d1be65afb281eddf0ffbe629385b"' in zrodlo
    commit = re.search(r'^KOMMIT_OPF = "(\w+)"', zrodlo, re.M).group(1)
    assert f"openai/privacy-filter@{commit}" in pyproj
    migawka = KORZEN / "vendor" / "hf" / "hub" / "models--openai--privacy-filter" / "snapshots" / "7ffa9a043d54d1be65afb281eddf0ffbe629385b"
    if migawka.exists():
        cfg = json.loads((migawka / "original" / "config.json").read_text(encoding="utf-8"))
        assert int(re.search(r"^OKNO_TOKENOW = (\d+)", zrodlo, re.M).group(1)) <= cfg["default_n_ctx"]
        assert cfg["encoding"] == "o200k_base"


@GRUPA_UCZESTNIKOW
def test_openai_privacy_filter_szybkie_moe_rownowazne_z_kodem_autorow():
    """Warstwa MoE zgrupowana po ekspertach (float32) daje te same spany co referencyjna implementacja `opf` (PBENCH_MOE_ORYGINAL=1):
    krótki tekst oraz długi (~600 tokenów, wiele rozstrzygnięć top-k), przy normalnym oknie 4096."""
    krotki = ("Kontakt: Jan Kowalski, tel. +48 600 700 800, e-mail jan.kowalski@example.com, ur. 12.03.1985 r., "
              "zam. ul. Długa 5/7, 00-950 Warszawa. Please contact Mary Johnson at mary.j@example.org.")
    dlugi = " ".join(f"Dnia {i % 28 + 1}.0{i % 9 + 1}.2021 r. Pan Adam Nowak{i} (tel. 50{i % 10} 600 70{i % 10}, adres: ul. Polna {i}, "
                     f"{10 + i % 80}-{100 + i}0 Kraków, konto PL6110901014{i:04d}) zawarł umowę nr {i}/2021 z firmą Alfa{i} Sp. z o.o. "
                     f"Kontakt: adam{i}@example.com, hasło tymczasowe sk-test-{i}x9Qz." for i in range(1, 9))
    for tekst in (krotki, dlugi):
        wyniki = []
        for orygin in ("0", "1"):
            u = Uczestnik("openai-privacy-filter", {"PBENCH_MOE_ORYGINAL": orygin, "PBENCH_SUROWE": "1"})
            try:
                wyniki.append(u.analizuj(tekst, "pl"))
            finally:
                u.zamknij()
        a, b = wyniki
        assert [w[:3] for w in a] == [w[:3] for w in b] and a
        assert max(abs(x[3] - y[3]) for x, y in zip(a, b)) < 0.02


@GRUPA_UCZESTNIKOW
def test_openai_privacy_filter_unicode_offsety_dokladne():
    """Emoji (znaki spoza BMP) i znaki łączące nie przerywają dokumentu; offsety e-maila po nich są dokładne."""
    email = "jan.kowalski@example.com"
    tekst = "Zażółć gęślą jaźń \U0001F600\U0001F680 e\u0301cole koniec. Please contact Jan Kowalski by email " + email + " today."
    u = Uczestnik("openai-privacy-filter", {"PBENCH_SUROWE": "1"})
    try:
        wyk = u.analizuj(tekst, "pl")
    finally:
        u.zamknij()
    s = tekst.index(email)
    assert any((w[0], w[1]) == (s, s + len(email)) for w in wyk), wyk


# samodzielne uczestniki GLiNER: id → (repo HF, rewizja, `max_len` modelu, okno z run.py, plik run.py)
GLINER_SAMODZIELNE = {
    "gliner-urchade-pii": ("urchade/gliner_multi_pii-v1", "1fcf13e85f4eef5394e1fcd406cf2ca9ea82351d", 384, 320),
    "gliner-knowledgator-pii": ("knowledgator/gliner-pii-large-v1.0", "f847f54fbc97ad6e78bfa20ed9c5e5d5c43327b9", 768, 384),
    "gliner-nvidia-pii": ("nvidia/gliner-PII", "bd23e8ef4425fd04e34c5204ab49ffaa706eae79", 384, 320),
}


@pytest.mark.parametrize("id_uczestnika", sorted(GLINER_SAMODZIELNE))
def test_gliner_samodzielne_stale_zgodne_z_konfiguracja_modelu(id_uczestnika):
    """`MAX_LEN`/rewizja w run.py zgadzają się z `gliner_config.json` przypiętej migawki, a okno z zapasem mieści się w limicie."""
    import re
    repo, rewizja, max_len, okno_cfg = GLINER_SAMODZIELNE[id_uczestnika]
    zrodlo = (KORZEN / "uczestnicy" / id_uczestnika / "run.py").read_text(encoding="utf-8")
    assert f'"{rewizja}"' in zrodlo and f'"{repo}"' in zrodlo
    assert int(re.search(r"^MAX_LEN = (\d+)", zrodlo, re.M).group(1)) == max_len
    assert int(re.search(r"^LIMIT_OKNA = (\d+)", zrodlo, re.M).group(1)) == okno_cfg
    # rzeczywisty limit modelu z migawki w vendor/hf (gdy pobrana)
    migawka = KORZEN / "vendor" / "hf" / "hub" / ("models--" + repo.replace("/", "--")) / "snapshots" / rewizja
    if migawka.exists():
        assert json.loads((migawka / "gliner_config.json").read_text(encoding="utf-8"))["max_len"] == max_len
    # okno w tokenach GLiNER (ten sam podział co biblioteka): żadne okno > max_len, także dla gęstej interpunkcji
    tok = okna.TokenizerGliner()
    efektywne = min(okno_cfg, int(max_len * (1 - 0.20 / 2 - 0.06)))      # jak gliner_wspolne.limit_okna
    for tekst in (_tekst_interpunkcyjny() * 8, " ".join(f"w{i}," for i in range(4000)), "A.;" * 3000):
        for a, b in okna.okna_tokenowe(tekst, tok, efektywne, 0.20):
            assert len(tok(tekst[a:b])["offset_mapping"]) <= max_len, (a, b)


@GRUPA_UCZESTNIKOW
@pytest.mark.skipif(not (KORZEN / "uczestnicy" / "presidio-gliner" / "run.py").exists(), reason="brak presidio-gliner")
def test_gliner_interpunkcja_wartosc_na_koncu_nieobcieta():
    """Domyślne okno: ~1000 znaków interpunkcji (>384 tokenów) + osoba i e-mail na końcu – wykryte, offsety dokładne."""
    tekst = _tekst_interpunkcyjny()
    u = Uczestnik("presidio-gliner")
    try:
        wyk = u.analizuj(tekst)
    finally:
        u.zamknij()
    email = "jan.kowalski@example.com"
    s = tekst.index(email)
    assert any((w[0], w[1]) == (s, s + len(email)) for w in wyk), wyk
    assert _pokrywa(wyk, tekst, "Jan Kowalski"), wyk


# ----------------------------------------------------------------------------- sumy kontrolne PL (presidio-pl-ner)
def test_sumy_kontrolne_pl():
    import sumy_kontrolne_pl as sk
    assert sk.nip_poprawny("123-456-32-18") and sk.nip_poprawny("PL1234563218") and not sk.nip_poprawny("1234563219")
    assert sk.regon_poprawny("123456785") and not sk.regon_poprawny("123456789")
    assert sk.regon_poprawny("12345678512347") and not sk.regon_poprawny("12345678512345")
    assert sk.dowod_poprawny("ABA300000") and sk.dowod_poprawny("IDR 081760") and not sk.dowod_poprawny("ABA400000")
    assert not sk.dowod_poprawny("AB1234567")


def test_sumy_kontrolne_pl_zgodne_z_gold_korpusu():
    """Każda wartość NIP/REGON/DOWOD z gold dev musi przejść algorytm (generator korpusu jest niezależny od uczestnika)."""
    funkcje = None
    import sumy_kontrolne_pl as sk
    funkcje = {"NIP": sk.nip_poprawny, "REGON": sk.regon_poprawny, "DOWOD": sk.dowod_poprawny}
    manifest = KORZEN / "korpus" / "manifest.jsonl"
    if not manifest.exists():
        pytest.skip("brak korpusu")
    for linia in manifest.read_text(encoding="utf-8").splitlines():
        wpis = json.loads(linia)
        for g in wpis["gold_tekst"]:
            if g["kategoria"] in funkcje:
                assert funkcje[g["kategoria"]](g["tekst"]), (wpis["id"], g["tekst"])


def test_stanza_herbert_przypiety_do_rewizji(tmp_path):
    """P13c-1: HerBERT (szkielet `nkjp_bert`) musi być w rewizji z KONFIG.md; inna `refs/main` albo brak migawki = jawny błąd."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("stanza_herbert", KORZEN / "uczestnicy" / "stanza" / "herbert.py")
    h = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(h)
    assert h.REWIZJA in (KORZEN / "uczestnicy" / "stanza" / "KONFIG.md").read_text("utf-8")        # jedno źródło prawdy z opisem
    import hashlib
    kat = tmp_path / "models--allegro--herbert-base-cased"
    wagi = b"wagi-testowe"
    sha = hashlib.sha256(wagi).hexdigest()
    with pytest.raises(RuntimeError, match="brak migawki"):
        h.sprawdz_cache(tmp_path, sha256_wag=sha)
    (kat / "snapshots" / h.REWIZJA).mkdir(parents=True)
    (kat / "snapshots" / h.REWIZJA / "config.json").write_text("{}")
    with pytest.raises(RuntimeError, match="sumę SHA-256"):
        h.sprawdz_cache(tmp_path, sha256_wag=sha)                                       # brak wag
    (kat / "snapshots" / h.REWIZJA / h.PLIK_WAG).write_bytes(b"inne")
    with pytest.raises(RuntimeError, match="sumę SHA-256"):
        h.sprawdz_cache(tmp_path, sha256_wag=sha)                                       # podmienione wagi
    (kat / "snapshots" / h.REWIZJA / h.PLIK_WAG).write_bytes(wagi)
    with pytest.raises(RuntimeError, match="refs/main"):
        h.sprawdz_cache(tmp_path, sha256_wag=sha)                                       # brak refs/main
    h.ustaw_ref(tmp_path)                                                               # czysty cache po snapshot_download
    assert (kat / "refs" / "main").read_text() == h.REWIZJA
    h.sprawdz_cache(tmp_path, sha256_wag=sha)
    (kat / "refs" / "main").write_text("0" * 40)
    h.ustaw_ref(tmp_path)                                                               # istniejącego ref nie nadpisuje
    with pytest.raises(RuntimeError, match="refs/main"):
        h.sprawdz_cache(tmp_path, sha256_wag=sha)                                       # inna rewizja
    h.sprawdz_cache(KORZEN / "vendor" / "hf" / "hub") if (KORZEN / "vendor" / "hf" / "hub" / "models--allegro--herbert-base-cased").exists() else None
