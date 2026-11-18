"""Sędzia obrazowy: OCR obrazów osadzonych w pliku (Tesseract, języki dokumentu) z pamięcią podręczną po sha256 obrazu.

Obrazy (loga, podpisy, strony skanów) nie mają warstwy tekstowej, więc wartość na obrazie „wycieka”, gdy OCR wyniku ją
odczyta. OCR się myli (podpis pismem skryptowym, mały krój), dlatego:

* strony (duże obrazy) są sprawdzane pod kątem obrotu (OSD Tesseracta, `--psm 0`): obraz obrócony o 90/180/270 stopni jest
  czytany także po wyprostowaniu (odczyty rozdzielone `ODDZIELACZ`), więc skan włożony bokiem albo do góry nogami nie jest
  „niewykrywalny”,
* dopasowanie jest rozmyte (`podobienstwo` ≥ 0,85 na tokenach i ciągach alfanumerycznych identyfikatorów),
* kalibracja na oryginale – `wykrywalne_obrazy(oryginal, gold)` zwraca identyfikatory wartości obrazowych, które sędzia
  odnajduje w OCR oryginału. Pozostałe są `niewykrywalne` (słabość OCR, nie uczestnika) i wyłączone z gold dla
  WSZYSTKICH uczestników (symetrycznie) – `ocen_plik` robi to sam.

Trafienie częściowe z OCR obrazu osadzonego liczy się tylko z potwierdzeniem w odczycie tego obrazu INNYM TRYBEM Tesseracta
albo tym samym trybem w innej skali, gdy wspólny token jest w którymś z odczytów słowem dokładnie (`plik._trafienia_ocr`,
`tryby_odczytow`; długi token dokładny – `plik.MIN_DL_TOKENU_BEZ_POTWIERDZENIA` – wystarcza z jednego odczytu); obraz
z trafieniem bez potwierdzenia dostaje drugi odczyt (`ocr_tekst(drugi=True)`, `_odczytaj_drugi`).

Inicjały (wzorzec 1–3 liter) w pikselach mają dwa odczyty dodatkowe (`plik._trafienia_ocr`, poprawka H6a I-R1): render strony
bez obiektów tekstowych (`ocr_stron_pdf(bez_tekstu=True)`, `ekstrakcja.renderuj_strony`) i odczyt potwierdzający obrazu
z wybielonymi polami zamalowanymi (`bez_pol`, `ocr_tekst(wybiel=True)`, `ocr_stron_pdf(wybiel=True)`).

Pamięć podręczna OCR: pliki `<sha256 obrazu>-<język>-<wersja>.txt` (drugi odczyt: `…-<wersja>-<WERSJA_DRUGIEGO_ODCZYTU>.txt`,
odczyt bez pól: `…-<WERSJA_BEZ_POL>.txt`) oraz `strony-<sha256 pliku PDF>-<dpi>dpi-<język>-<wersje>.json`
(OCR wszystkich stron renderu, `ocr_stron_pdf`; render bez tekstu – przyrostek `-bt`, bez pól – `-<WERSJA_BEZ_POL>`)
w `PBENCH_OCR_CACHE` (domyślnie `.cache/ocr` w repozytorium, poza gitem); każda nazwa kończy się `-td<skrót tessdata>`
(`ocr.skrot_tessdata` – inne dane Tesseracta dają nowe odczyty zamiast starych z pamięci, T17a),
zapisywane atomowo, więc równoległe procesy mogą ją współdzielić. Małe obrazy (loga, podpisy) są powiększane
i czytane w trybach psm 6 i 11 (tekst wiersza/rzadki), duże (strony) w psm 3.

Nie wykrywamy twarzy (w korpusie nie ma zdjęć – ograniczenie badania).
"""
from __future__ import annotations

import difflib
import hashlib
import io
import json
import os
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

from .. import ocr as _ocr

#: Próg podobieństwa (difflib.SequenceMatcher.ratio) tokenu/identyfikatora do słowa OCR.
PROG_PODOBIENSTWA = 0.85
#: Obrazy mniejsze (po dłuższym boku) niż tyle pikseli są powiększane i czytane trybami „wiersz” (psm 6, 11).
MALY_OBRAZ_PX = 900
MIN_BOK_PX = 24
CEL_SZEROKOSC_MALEGO_PX = 1800
#: OSD: pewność orientacji (Tesseract podaje ~2–30), od której obraz uznajemy za obrócony.
PROG_PEWNOSCI_OSD = 3.0
#: Odczyty jednego obrazu różnymi trybami są rozdzielone tym znakiem (strona formularza); przy liczeniu wystąpień
#: bierze się maksimum z odczytów, nie sumę.
ODDZIELACZ = "\f"
#: Wersja OCR w kluczach pamięci podręcznej (zmiana sposobu odczytu = nowa wersja, stare wpisy przestają pasować).
WERSJA_OCR = "v2"
#: Wersja odczytu stron PDF (`ocr_stron_pdf`): renderowanie PDFium + `_odczytaj`.
WERSJA_OCR_STRON = "s1"
#: Tryb Tesseracta dla stron PDF (pierwszy odczyt) i dla drugiego odczytu: psm 3 (automatyczny układ) potrafi pominąć blok
#: tekstu w układzie wielokolumnowym (np. dwie kolumny adresów faktury na skanie), psm 6 (jeden blok) czyta go wiersz po wierszu.
PSM_STRON: tuple[int, ...] = (3,)
PSM_DRUGIEGO_ODCZYTU: tuple[int, ...] = (3, 6)
#: Trzeci odczyt stron (`ekstrakcja.RENDER_DPI`, tylko psm 6) – dla stron z trafieniem bez potwierdzenia po drugim odczycie: blok,
#: który czyta tylko psm 6, ma wtedy, jak każdy inny blok, odczyty w dwóch rozdzielczościach (300 i 400 dpi).
PSM_TRZECIEGO_ODCZYTU: tuple[int, ...] = (6,)
#: Tryby Tesseracta małego obrazu (psm 6 – blok, psm 11 – tekst rzadki); w nich także drugi odczyt dużego obrazu.
PSM_MALEGO_OBRAZU: tuple[int, ...] = (6, 11)
#: Drugi odczyt obrazu osadzonego (`_odczytaj_drugi`) – tylko obrazu z trafieniem bez potwierdzenia (`plik._trafienia_ocr`): mały
#: obraz powiększony tyle razy bardziej niż w pierwszym odczycie (te same tryby `PSM_MALEGO_OBRAZU` w innej skali), duży
#: (pierwszy odczyt: `PSM_STRON`) – w trybach `PSM_MALEGO_OBRAZU`. Potwierdzeniem obrazu osadzonego jest odczyt INNYM trybem
#: (`tryby_odczytow`) albo tym samym trybem w innej skali z tokenem dokładnym: powiększenie tych samych pikseli – inaczej niż
#: render strony PDF w innym dpi – powtarza szum rozmyty („Osoba” z miniatury ODT czytane przez psm 6 jako „Osowa” w skali ×3,
#: ×5 i ×10), ale nie wymyśla dokładnego nazwiska.
SKALA_DRUGIEGO_ODCZYTU_MALEGO = 2
#: Wersja drugiego odczytu obrazu osadzonego w kluczu pamięci podręcznej (obok `WERSJA_OCR`).
WERSJA_DRUGIEGO_ODCZYTU = "d1"
#: Odczyt potwierdzający inicjałów w pikselach (`bez_pol`, poprawka H6a I-R1): czarne pola redakcji rastrowej (prostokąt na
#: wartość albo na każdy znak) OCR czyta w każdym odczycie jako to samo krótkie „słowo” („rs”, „jm”), więc potwierdzenie innym
#: odczytem nie odsiewa tego szumu – trafienie inicjałów liczy się tylko, gdy zostaje także po wybieleniu takich pól.
#: Pole zamalowane = piksele ciemniejsze niż `PROG_CIEMNEGO_POLA` (jasność L 0–255), w które mieści się kwadrat
#: `BOK_POLA_PX` × `BOK_POLA_PX` w pikselach obrazu czytanego przez OCR (otwarcie morfologiczne; 15 px ≈ 1,3 mm w 300 dpi);
#: w małym obrazie osadzonym (`MALY_OBRAZ_PX`) pole liczy się w pikselach obrazu źródłowego, przed powiększeniem do OCR.
#: Pociągnięcia pisma do ok. 14 pt przy ≤ 400 dpi – także pogrubionego – są cieńsze i zostają (grubsze bywa wybielane, zob.
#: metodyka). Pole wraz z wygładzoną krawędzią (`MARGINES_POLA_PX`) staje się białe.
PROG_CIEMNEGO_POLA = 100
BOK_POLA_PX = 15
MARGINES_POLA_PX = 3
#: Wersja odczytu bez pól w kluczu pamięci podręcznej (zmiana progów = nowa wersja).
WERSJA_BEZ_POL = "p2"


def katalog_cache() -> Path:
    """Katalog pamięci podręcznej OCR (`PBENCH_OCR_CACHE` albo `.cache/ocr` w repozytorium)."""
    env = os.environ.get("PBENCH_OCR_CACHE")
    return Path(env) if env else _ocr.KORZEN / ".cache" / "ocr"


def _watki() -> int:
    return max(1, int(os.environ.get("PBENCH_OCR_WATKI", min(6, os.cpu_count() or 2))))


def _przygotuj(dane: bytes) -> Image.Image | None:
    """Obraz RGB na białym tle (przezroczystość nie może dać czarnego tła); `None`, gdy nie da się otworzyć/za mały."""
    try:
        with Image.open(io.BytesIO(dane)) as im:
            im.load()
            rgba = im.convert("RGBA")
    except Exception:  # noqa: BLE001 - uszkodzony lub nieobsługiwany obraz = brak tekstu
        return None
    if min(rgba.size) < MIN_BOK_PX:
        return None
    tlo = Image.new("RGB", rgba.size, "white")
    tlo.paste(rgba, mask=rgba.getchannel("A"))
    return tlo


def _tesseract(obraz: Image.Image, jezyk: str, psm: int) -> str:
    program = _ocr._tesseract()
    if program is None:
        raise FileNotFoundError("brak programu tesseract w PATH")
    with tempfile.TemporaryDirectory(prefix="pbench-ocr-") as tmp:
        wejscie = Path(tmp) / "we.png"
        obraz.save(wejscie)
        wynik = subprocess.run(
            [program, str(wejscie), "stdout", "-l", _ocr.KODY[jezyk], "--tessdata-dir", str(_ocr.tessdata_dir()),
             "--psm", str(psm)],
            capture_output=True, check=False, timeout=300, env={**os.environ, "OMP_THREAD_LIMIT": "1"})
    return wynik.stdout.decode("utf-8", errors="replace")


def kat_obrotu(obraz: Image.Image) -> int:
    """Kąt (0/90/180/270 stopni zgodnie z ruchem wskazówek zegara), o który trzeba obrócić obraz, żeby tekst stał prosto
    (OSD Tesseracta); 0, gdy OSD nie rozpozna orientacji albo nie jest jej pewne."""
    program = _ocr._tesseract()
    if program is None:
        return 0
    with tempfile.TemporaryDirectory(prefix="pbench-osd-") as tmp:
        wejscie = Path(tmp) / "we.png"
        obraz.save(wejscie)
        wynik = subprocess.run([program, str(wejscie), "stdout", "--psm", "0", "--tessdata-dir", str(_ocr.tessdata_dir())],
                               capture_output=True, check=False, timeout=300, env={**os.environ, "OMP_THREAD_LIMIT": "1"})
    tekst = wynik.stdout.decode("utf-8", errors="replace")
    kat = re.search(r"Rotate:\s*(\d+)", tekst)
    pewnosc = re.search(r"Orientation confidence:\s*([\d.]+)", tekst)
    if kat is None or pewnosc is None or float(pewnosc.group(1)) < PROG_PEWNOSCI_OSD:
        return 0
    return int(kat.group(1)) % 360


def _sumy_okien(maska: np.ndarray, przed: int, po: int) -> np.ndarray:
    """Liczba pikseli maski w oknie (przed + po + 1) × (przed + po + 1) wokół każdego piksela (od y - przed do y + po, tak samo
    w poziomie; poza obrazem – zera). Obraz całkowy – czas liniowy względem liczby pikseli, niezależny od boku okna."""
    s = np.pad(maska.astype(np.int32), ((przed + 1, po), (przed + 1, po))).cumsum(0).cumsum(1)
    k = przed + po + 1
    return s[k:, k:] - s[:-k, k:] - s[k:, :-k] + s[:-k, :-k]


def bez_pol(obraz: Image.Image) -> Image.Image:
    """Obraz z wybielonymi polami zamalowanymi (`PROG_CIEMNEGO_POLA`, `BOK_POLA_PX`, `MARGINES_POLA_PX`); bez takich pól – ten
    sam obraz."""
    jasnosc = np.asarray(obraz.convert("L"))
    bok = BOK_POLA_PX
    if min(jasnosc.shape) < bok:
        return obraz
    # erozja: piksel, od którego w prawo i w dół zaczyna się kwadrat bok × bok samych ciemnych pikseli
    rogi = _sumy_okien(jasnosc < PROG_CIEMNEGO_POLA, 0, bok - 1) == bok * bok
    if not rogi.any():
        return obraz
    # dylatacja tym samym kwadratem (otwarcie: suma kwadratów mieszczących się w ciemnych pikselach), poszerzona o margines
    pole = _sumy_okien(rogi, bok - 1 + MARGINES_POLA_PX, MARGINES_POLA_PX) > 0
    piksele = np.asarray(obraz.convert("RGB")).copy()
    piksele[pole] = 255
    return Image.fromarray(piksele)


def _odczytaj(dane: bytes, jezyk: str, psm_stron: tuple[int, ...] = (3,), powiekszenie: int = 1, wybiel: bool = False) -> str:
    """OCR obrazu (bez pamięci podręcznej): małe obrazy powiększone, trybami `PSM_MALEGO_OBRAZU`; duże (strony) trybami
    `psm_stron` + OSD (strona obrócona – te same tryby po wyprostowaniu). Odczyty rozdzielone `ODDZIELACZ`. `powiekszenie` –
    dodatkowa skala małego obrazu (drugi odczyt, `_odczytaj_drugi`); `wybiel` – obraz w skali odczytu bez pól zamalowanych
    (`bez_pol`)."""
    im = _przygotuj(dane)
    if im is None:
        return ""
    if max(im.size) < MALY_OBRAZ_PX:
        skala = max(1, round(CEL_SZEROKOSC_MALEGO_PX / max(im.width, 1))) * powiekszenie
        if wybiel:      # pola w pikselach obrazu źródłowego, przed powiększeniem (po nim zwykłe pismo byłoby „polem”)
            im = bez_pol(im)
        duzy = Image.new("RGB", (im.width * skala + 80, im.height * skala + 80), "white")
        duzy.paste(im.resize((im.width * skala, im.height * skala), Image.LANCZOS), (40, 40))
        return ODDZIELACZ.join(_tesseract(duzy, jezyk, psm) for psm in PSM_MALEGO_OBRAZU)
    czytany = bez_pol(im) if wybiel else im
    odczyty = [_tesseract(czytany, jezyk, psm) for psm in psm_stron]
    kat = kat_obrotu(im)       # orientacja z obrazu bez zmian (wybielony – ten sam kąt co odczyt zwykły)
    if kat:      # strona obrócona: dodatkowy odczyt po wyprostowaniu
        prosty = czytany.rotate(-kat, expand=True, fillcolor=(255, 255, 255))
        odczyty += [_tesseract(prosty, jezyk, psm) for psm in psm_stron]
    return ODDZIELACZ.join(odczyty)


def _zapisz_atomowo(cache: Path, tekst: str) -> None:
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=cache.parent, delete=False, suffix=".tmp") as f:
            f.write(tekst)
        os.replace(f.name, cache)
    except OSError:
        pass


def _maly(dane: bytes) -> bool | None:
    """Czy obraz jest mały (`MALY_OBRAZ_PX`) – jak w `_odczytaj`; None, gdy nie da się go otworzyć."""
    try:
        with Image.open(io.BytesIO(dane)) as im:
            return max(im.size) < MALY_OBRAZ_PX
    except Exception:  # noqa: BLE001 - uszkodzony lub nieobsługiwany obraz = brak tekstu
        return None


def _odczytaj_drugi(dane: bytes, jezyk: str, wybiel: bool = False) -> str:
    """Drugi odczyt obrazu osadzonego (zob. `SKALA_DRUGIEGO_ODCZYTU_MALEGO`), odczyty rozdzielone `ODDZIELACZ`; `wybiel` – jak
    w `_odczytaj`."""
    if _maly(dane):
        return _odczytaj(dane, jezyk, powiekszenie=SKALA_DRUGIEGO_ODCZYTU_MALEGO, wybiel=wybiel)
    return _odczytaj(dane, jezyk, PSM_MALEGO_OBRAZU, wybiel=wybiel)


def tryby_odczytow(dane: bytes, liczba: int, drugi: bool = False) -> tuple[int, ...]:
    """Tryb Tesseracta (psm) każdego z `liczba` odczytów obrazu (części tekstu `ocr_tekst` rozdzielone `ODDZIELACZ`): tryby
    `_odczytaj`/`_odczytaj_drugi` po kolei, po wyprostowaniu obróconego obrazu – te same od nowa."""
    maly = _maly(dane)
    tryby = PSM_MALEGO_OBRAZU if maly or drugi else PSM_STRON
    return tuple(tryby[k % len(tryby)] for k in range(liczba))


def ocr_tekst(dane: bytes, jezyk: str, drugi: bool = False, wybiel: bool = False) -> str:
    """Tekst rozpoznany na obrazie (bajty PNG/JPEG/…); wynik z pamięci podręcznej po sha256 bajtów i języku. `drugi` – drugi
    odczyt (`_odczytaj_drugi`, osobny klucz z `WERSJA_DRUGIEGO_ODCZYTU`); `wybiel` – ten sam odczyt obrazu bez pól zamalowanych
    (`bez_pol`, osobny klucz z `WERSJA_BEZ_POL`)."""
    wersja = (f"{WERSJA_OCR}-{WERSJA_DRUGIEGO_ODCZYTU}" if drugi else WERSJA_OCR) + (f"-{WERSJA_BEZ_POL}" if wybiel else "")
    cache = (katalog_cache()
             / f"{hashlib.sha256(dane).hexdigest()}-{_ocr.KODY[jezyk]}-{wersja}-td{_ocr.skrot_tessdata()}.txt")
    try:
        return cache.read_text(encoding="utf-8")
    except OSError:
        pass
    tekst = _odczytaj_drugi(dane, jezyk, wybiel) if drugi else _odczytaj(dane, jezyk, wybiel=wybiel)
    _zapisz_atomowo(cache, tekst)
    return tekst


def ocr_wiele(obrazy: list[tuple[str, bytes]], jezyk: str, drugi: bool = False) -> list[tuple[str, str]]:
    """OCR wielu obrazów (nazwa, bajty) równolegle (wątki; Tesseract to osobne procesy); kolejność zachowana. `drugi` – drugi
    odczyt (`ocr_tekst`)."""
    if not obrazy:
        return []
    with ThreadPoolExecutor(max_workers=_watki()) as ex:
        teksty = list(ex.map(lambda nb: ocr_tekst(nb[1], jezyk, drugi), obrazy))
    return [(n, t) for (n, _), t in zip(obrazy, teksty)]


def _polacz_kafelki(teksty: list[str]) -> str:
    """Odczyty kafelków jednej strony: k-ty odczyt strony to k-te odczyty kafelków (wiersz po wierszu), rozdzielone `ODDZIELACZ`."""
    if len(teksty) == 1:
        return teksty[0]
    czesci = [t.split(ODDZIELACZ) for t in teksty]
    return ODDZIELACZ.join("\n".join(c[k] for c in czesci if k < len(c)) for k in range(max(map(len, czesci))))


def ocr_stron_pdf(sciezka: Path, jezyk: str, drugi: bool = False, trzeci: bool = False, bez_tekstu: bool = False,
                  wybiel: bool = False) -> list[tuple[str, str]]:
    """OCR KAŻDEJ strony PDF wyrenderowanej przez PDFium: lista (nazwa `ekstrakcja.nazwa_renderu`, tekst). Odczyt pierwszy –
    `ekstrakcja.RENDER_DPI`, tryb `PSM_STRON`; `drugi` – `ekstrakcja.DRUGI_ODCZYT_DPI`, tryby `PSM_DRUGIEGO_ODCZYTU`; `trzeci` –
    `ekstrakcja.RENDER_DPI`, tryb `PSM_TRZECIEGO_ODCZYTU` (nazwa z przyrostkiem „(psm 6)”). `bez_tekstu` – render bez obiektów
    tekstowych (`ekstrakcja.renderuj_strony`; nazwa z przyrostkiem „(bez tekstu)”), `wybiel` – odczyt renderu bez pól zamalowanych
    (`bez_pol`); oba dla inicjałów (docstring modułu). Strona
    renderowana kafelkami (`ekstrakcja.renderuj_strony`) ma tekst złożony z odczytów kafelków (`_polacz_kafelki`). Pamięć
    podręczna po sha256 PLIKU, dpi, trybach, języku i wersji OCR (`WERSJA_OCR`, `WERSJA_OCR_STRON`; „-kafelki” dla pliku ze
    stroną większą niż `ekstrakcja.MAKS_BOK_RENDERU_PX`): oryginał oceniany dla wielu uczestników jest renderowany i czytany raz,
    a trafienie w pamięć podręczną pomija renderowanie. Pusta lista, gdy PDFium pliku nie otwiera."""
    from . import ekstrakcja as _ekstr  # import leniwy, jak w `wykrywalne_obrazy`
    dpi, psm = ((_ekstr.DRUGI_ODCZYT_DPI, PSM_DRUGIEGO_ODCZYTU) if drugi else
                (_ekstr.RENDER_DPI, PSM_TRZECIEGO_ODCZYTU) if trzeci else (_ekstr.RENDER_DPI, PSM_STRON))
    kafelki = "-kafelki" if _ekstr.ma_duze_strony(sciezka, dpi) else ""
    wariant = ("-bt" if bez_tekstu else "") + (f"-{WERSJA_BEZ_POL}" if wybiel else "")
    cache = (katalog_cache() / f"strony-{_ekstr.skrot_pliku(sciezka)}-{dpi}dpi-psm{'_'.join(map(str, psm))}"
                               f"-{_ocr.KODY[jezyk]}-{WERSJA_OCR}-{WERSJA_OCR_STRON}{kafelki}{wariant}"
                               f"-td{_ocr.skrot_tessdata()}.json")
    try:
        teksty = json.loads(cache.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        strony = _ekstr.renderuj_strony(sciezka, dpi, bez_tekstu=True) if bez_tekstu else _ekstr.renderuj_strony(sciezka, dpi)
        obrazy = [(i, b) for i, s in enumerate(strony) for b in s]
        with ThreadPoolExecutor(max_workers=_watki()) as ex:
            odczyty = list(ex.map(lambda ib: _odczytaj(ib[1], jezyk, psm, wybiel=wybiel), obrazy))
        teksty = [_polacz_kafelki([t for (j, _), t in zip(obrazy, odczyty) if j == i]) for i in range(len(strony))]
        _zapisz_atomowo(cache, json.dumps(teksty, ensure_ascii=False))
    przyrostek = (f" (psm {'_'.join(map(str, psm))})" if trzeci and not drugi else "") + (" (bez tekstu)" if bez_tekstu else "")
    return [(_ekstr.nazwa_renderu(i + 1, dpi) + przyrostek, t) for i, t in enumerate(teksty)]


def ocr_stron_osadzonych(pdfy: list[tuple[str, bytes]], jezyk: str, drugi: bool = False, trzeci: bool = False,
                         bez_tekstu: bool = False, wybiel: bool = False) -> list[tuple[str, str]]:
    """OCR stron PDF-ów zagnieżdżonych (`ekstrakcja.Wydobycie.pdfy`: przedrostek części i bajty, np. załączniki poczty) – każdy
    tak samo jak samodzielny PDF (`ocr_stron_pdf`, ta sama pamięć podręczna po sumie pliku, te same odczyty i warianty); nazwa
    strony z przedrostkiem części (`zal(karta.pdf):pdf:render strona 1`). Kolejność: PDF-y w kolejności pliku, w nich strony."""
    wynik: list[tuple[str, str]] = []
    for pref, dane in pdfy:
        with tempfile.TemporaryDirectory(prefix="pbench-pdf-osadzony-") as tmp:
            sciezka = Path(tmp) / "osadzony.pdf"
            sciezka.write_bytes(dane)
            warianty = {k: True for k, v in (("bez_tekstu", bez_tekstu), ("wybiel", wybiel)) if v}
            wynik += [(f"{pref}{n}", t) for n, t in ocr_stron_pdf(sciezka, jezyk, drugi=drugi, trzeci=trzeci, **warianty)]
    return wynik


# ----------------------------------------------------------------------------- dopasowanie rozmyte
def podobienstwo(a: str, b: str) -> float:
    """Podobieństwo dwóch ciągów 0–1 (difflib; odpowiednik `ratio` z rapidfuzz)."""
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def _alnum_z_granicami(tekst: str) -> tuple[str, list[bool], list[bool]]:
    """Litery i cyfry tekstu oraz dla każdej z nich: czy zaczyna ciąg liter/cyfr (poprzedni znak tekstu nie jest literą ani
    cyfrą) i czy go kończy (następny nie jest)."""
    znaki: list[str] = []
    pocz: list[bool] = []
    kon: list[bool] = []
    poprzedni = False
    for ch in tekst:
        if ch.isalnum():
            znaki.append(ch)
            pocz.append(not poprzedni)
            kon.append(False)
            poprzedni = True
        else:
            if poprzedni:
                kon[-1] = True
            poprzedni = False
    if kon:
        kon[-1] = True
    return "".join(znaki), pocz, kon


def zawiera_rozmyto(wzor: str, tekst: str, prog: float = PROG_PODOBIENSTWA, granice: bool = False) -> bool:
    """Czy w `tekst` jest okno długości ~`wzor` o podobieństwie ≥ `prog` (identyfikatory zlane w ciąg alfanumeryczny).
    `granice`: `tekst` jest zwykłym tekstem (ze spacjami i znakami przestankowymi), a okno ciągu jego liter i cyfr musi zaczynać
    się i kończyć na granicy (nie może sąsiadować z literą ani cyfrą: „912345678” nie zawiera „12345678”)."""
    n = len(wzor)
    if n == 0:
        return False
    if granice:
        tekst, pocz, kon = _alnum_z_granicami(tekst)
    if len(tekst) < max(1, int(n * prog)):
        return False
    if not granice and wzor in tekst:
        return True
    sm = difflib.SequenceMatcher(None, autojunk=False)
    sm.set_seq2(wzor)
    for dl in (n, max(1, n - 1), n + 1):
        for i in range(0, max(1, len(tekst) - dl + 1)):
            if granice and not (pocz[i] and i + dl - 1 < len(kon) and kon[i + dl - 1]):
                continue
            sm.set_seq1(tekst[i:i + dl])
            if sm.real_quick_ratio() >= prog and sm.quick_ratio() >= prog and sm.ratio() >= prog:
                return True
    return False


def slowo_rozmyte(token: str, slowa: set[str], prog: float = PROG_PODOBIENSTWA) -> bool:
    """Czy któreś słowo OCR jest podobne do `token` (≥ `prog`); wcześniej tani filtr po długości."""
    if token in slowa:
        return True
    return bool(slowa_rozmyte(token, slowa, prog, pierwsze=True))


def slowa_rozmyte(token: str, slowa: set[str], prog: float = PROG_PODOBIENSTWA, pierwsze: bool = False) -> set[str]:
    """Słowa OCR podobne do `token` (≥ `prog`; `pierwsze` – wystarczy jedno)."""
    wynik = {token} & slowa
    if wynik and pierwsze:
        return wynik
    n = len(token)
    sm = difflib.SequenceMatcher(None, autojunk=False)
    sm.set_seq2(token)
    for s in slowa:
        if abs(len(s) - n) > max(1, round(n * (1 - prog) * 1.5)):
            continue
        sm.set_seq1(s)
        if sm.real_quick_ratio() >= prog and sm.quick_ratio() >= prog and sm.ratio() >= prog:
            wynik.add(s)
            if pierwsze:
                break
    return wynik




_WYKRYWALNE: dict[tuple, frozenset[str]] = {}


def wykrywalne_obrazy(oryginal: Path, gold, jezyk: str | None = None, reguly=None,
                      leksykon: frozenset[str] = frozenset()) -> set[str]:
    """Identyfikatory wartości obrazowych (`miejsce == "obraz"`) z `gold`, które sędzia odnajduje w OCR oryginału.

    Reszta to `niewykrywalne` – wyłączona z gold dla wszystkich uczestników. Wynik zapamiętany w procesie (klucz: skrót
    pliku, identyfikatory i teksty wartości, język, reguły, leksykon, skrót danych Tesseracta – `ocr.skrot_tessdata`); OCR
    dodatkowo w pamięci podręcznej na dysku.
    """
    from . import ekstrakcja as _ekstr
    from . import plik as _plik  # import leniwy: `plik` importuje ten moduł

    ob = [w for w in gold if w.w_pikselach]
    if not ob:
        return set()
    jezyk = jezyk or _plik.jezyk_wartosci(ob)
    reguly = reguly or _plik.RegulyWycieku()
    klucz = (_ekstr.skrot_pliku(oryginal), tuple(sorted((w.id, w.tekst, w.kategoria) for w in ob)), jezyk, reguly, leksykon,
             _ocr.skrot_tessdata())
    if klucz not in _WYKRYWALNE:
        wyd = _ekstr.wydobadz(oryginal)
        teksty = [t for _, t in ocr_wiele(wyd.obrazy, jezyk)]
        _WYKRYWALNE[klucz] = frozenset(_plik.wykrywalne_w_ocr(oryginal, gold, ob, teksty, reguly, leksykon))
    return set(_WYKRYWALNE[klucz])
