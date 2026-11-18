"""Warstwa trudnych przypadków, zadanie H4b – poczta (spec §11 pkt 1) i wątki cytowane z vCard (pkt 6).

Dokument to zwykły e-mail trzonu (szablon `email`, EML albo MSG) z dodatkiem przypadku; ziarno dokumentu daje cały dodatek.
Generatory (`GENERATORY`: przypadek -> {(język, typ): funkcja `(język, typ, ziarno, format) -> (Wynik, Generator, dodatki)`}):

* `ukryta_poczta` – załączniki, których uczestnik czyszczący samą wiadomość nie widzi: (a) wiadomość zagnieżdżona – w MSG obiekt
  osadzony (`ATTACH_EMBEDDED_MSG`, nie plik `.msg`), w EML część `message/rfc822` – z własnymi nagłówkami (nadawca i adresat:
  nazwa i adres), treścią z danymi klienta i własnym załącznikiem PDF; (b) załącznik PDF (karta klienta) w samej wiadomości.
  Element `Dokument.ukryte`: `poczta.wiadomosc` (pola nagłówków i treść rozdzielone `ROZDZIELACZ`), `poczta.zalacznik_pdf`
  (atrybut `w`: `glowna` albo `wiadomosc` – załącznik wiadomości zagnieżdżonej). Miejsce gold: `zalacznik`.
* `cytowane_watki_vcard` – wątek przekazany pod podpisem: 3–5 cytowanych wiadomości (nagłówki „Od/Wysłano/Do/Temat” za kreską
  Outlooka albo „W dniu … napisał(a):” z cytowaniem `>`, zagłębienie rośnie z każdą odpowiedzią), każda ze stopką z danymi
  kontaktowymi nadawcy; dane klienta w treści. Cytaty to akapity treści z atrybutem `cytat` (renderer poczty kładzie je pod
  stopką), wartości z cechą `cytat` i miejscem `tresc` – są też w tekście poziomu 1. Do tego załącznik vCard (`poczta.vcard`,
  `.vcf`, VERSION 3.0 albo 4.0: FN, N, ORG, TITLE, TEL, EMAIL, ADR) z danymi osoby trzeciej; miejsce `zalacznik`.

Osoby dodatku nie dzielą imion ani nazwisk (ani ich początków – `FabrykaH4b`) z wartościami e-maila ani ze sobą, firma z
wizytówki – słów nazwy, więc uczestnik „naiwny”, który czyści tylko główną treść wiadomości, zostawia wyciek w załącznikach, cytatach i wizytówce
(a wartości treści głównej trafia tylko przez wspólne słowa – np. to samo miasto w adresie). Rodzaj
wartości (`h.<rola>.<pole>#n`) wskazuje rolę osoby – encja tej samej osoby jest jedna w całym wątku (spójność zamienników).
`obrob` (wywoływane z `BudowaTrudna.po_renderze`) dopisuje `Dokument.ukryte` do gotowej wiadomości (`pbench.pliki_poczta`).
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import random
import re
import tempfile
import unicodedata
from pathlib import Path

from . import pliki_poczta, przypadki as P
from .budowa import MAPA_KATEGORII, Wynik, zbuduj_z_kontekstem
from .dane import Generator
from .dane.wspolne import Adres, BazowyGenerator, Osoba
from .model import Dokument, Element, Wartosc
from .render.wspolne import rng_dokumentu
from .szablony import SZABLONY_TRUDNE as SZABLONY       # wariant warstwy trudnej (J1, S5)
from .trudne_ukryta import DOMENY_UKRYTYCH, MIEJSCA, Fabryka, dwukropek, tokeny
from .trudne_wspolne import KLUCZ_ID, osoba
from .ukryta_pakiet import ROZDZIELACZ

CECHA_CYTAT = "cytat"
#: Miejsce gold załączników (`poczta.wiadomosc`, `poczta.zalacznik_pdf`, `poczta.vcard`) i cytatów (`metodyka/miejsca-ukryte.md`).
MIEJSCE = MIEJSCA["poczta.zalacznik_pdf"]
MIEJSCE_CYTATU = MIEJSCA["poczta.cytat"]
TYP_PDF = ("application", "pdf")
TYP_VCARD = ("text", "vcard")
#: Pola wiadomości zagnieżdżonej (`poczta.wiadomosc`) w kolejności fragmentów rozdzielonych `ROZDZIELACZ`.
POLA_WIADOMOSCI = ("od", "od_adres", "do", "do_adres", "temat", "tresc")
#: Etykieta identyfikatora osoby wg klucza `Osoba.ids`.
ETYKIETA_ID = {"PESEL": "PESEL", "NINO": "NI number", "SSN": "SSN", "DNI": "DNI", "STEUER_ID": "Steuer-ID", "NIR": "NIR"}

#: Teksty dodatku wg języka dokumentu (bez danych osobowych).
TEKSTY: dict[str, dict] = {
    "pl": {"karta": "Karta klienta", "nazwisko": "Imię i nazwisko", "adres": "Adres", "telefon": "Telefon", "rachunek": "Rachunek",
           "plik_karty": "karta_klienta.pdf", "plik_wiadomosci": "wiadomosc", "plik_vcard": "wizytowka.vcf",
           "temat_zagn": "Dane klienta do umowy", "powitanie": "Dzień dobry,",
           "w_zalaczeniu": "w załączeniu przesyłam kartę klienta {kto}, tel. {tel}. Proszę o przygotowanie umowy.",
           "pozdrawiam": "Pozdrawiam", "przekazuje": "Poniżej przekazuję wcześniejszą korespondencję w tej sprawie; w załączeniu "
           "wizytówka biegłego.",
           "naglowki": ("Od", "Wysłano", "Do", "Temat"), "napisal": "W dniu {data} {kto} <{adres}> napisał(a):",
           "tematy": ("Dokumenty do umowy", "Ustalenia po spotkaniu", "Dane do pełnomocnictwa", "Termin podpisania aneksu"),
           "zdania": (("Przesyłam dane do pełnomocnictwa: {k.pelne}, {k.id_etykieta} {k.id}.",), ("Adres do doręczeń klienta: {k.adres}.",),
                      ("Zaliczkę proszę przelać na rachunek {k.rachunek}.",), ("Klient prosi o kontakt pod numerem {k.telefon}.",),
                      ("Potwierdzam ustalenia; dokumenty prześlę do końca tygodnia.",)),
           "funkcje": (("radca prawny", "radca prawny"), ("aplikant adwokacki", "aplikantka adwokacka"),
                       ("asystent zarządu", "asystentka zarządu"), ("specjalista ds. kadr", "specjalistka ds. kadr")), "tel": "tel."},
    "en": {"karta": "Client data sheet", "nazwisko": "Full name", "adres": "Address", "telefon": "Phone", "rachunek": "Account",
           "plik_karty": "client_sheet.pdf", "plik_wiadomosci": "message", "plik_vcard": "contact.vcf",
           "temat_zagn": "Client details for the agreement", "powitanie": "Hello,",
           "w_zalaczeniu": "please find attached the data sheet of {kto}, phone {tel}. Kindly prepare the agreement.",
           "pozdrawiam": "Kind regards", "przekazuje": "Please see the earlier correspondence on this matter below; the expert's "
           "contact card is attached.",
           "naglowki": ("From", "Sent", "To", "Subject"), "napisal": "On {data}, {kto} <{adres}> wrote:",
           "tematy": ("Documents for the agreement", "Follow-up after the meeting", "Details for the power of attorney",
                      "Signing date of the addendum"),
           "zdania": (("Please find the details for the power of attorney: {k.pelne}, {k.id_etykieta} {k.id}.",),
                      ("The client's address for service: {k.adres}.",), ("Please transfer the advance to account {k.rachunek}.",),
                      ("The client asks to be contacted on {k.telefon}.",), ("I confirm the arrangements; documents to follow this week.",)),
           "funkcje": (("solicitor",) * 2, ("trainee solicitor",) * 2, ("office manager",) * 2, ("HR specialist",) * 2), "tel": "tel."},
    "es": {"karta": "Ficha del cliente", "nazwisko": "Nombre y apellidos", "adres": "Dirección", "telefon": "Teléfono",
           "rachunek": "Cuenta", "plik_karty": "ficha_cliente.pdf", "plik_wiadomosci": "mensaje", "plik_vcard": "contacto.vcf",
           "temat_zagn": "Datos del cliente para el contrato", "powitanie": "Buenos días:",
           "w_zalaczeniu": "adjunto la ficha de {kto}, tel. {tel}. Ruego preparen el contrato.",
           "pozdrawiam": "Saludos cordiales", "przekazuje": "A continuación reenvío la correspondencia anterior sobre este asunto; "
           "se adjunta la tarjeta de contacto del perito.",
           "naglowki": ("De", "Enviado", "Para", "Asunto"), "napisal": "El {data}, {kto} <{adres}> escribió:",
           "tematy": ("Documentos para el contrato", "Acuerdos tras la reunión", "Datos para el poder", "Fecha de firma de la adenda"),
           "zdania": (("Le envío los datos para el poder: {k.pelne}, {k.id_etykieta} {k.id}.",),
                      ("Domicilio del cliente a efectos de notificaciones: {k.adres}.",),
                      ("Ruego transfieran la provisión a la cuenta {k.rachunek}.",), ("El cliente pide que lo llamen al {k.telefon}.",),
                      ("Confirmo lo acordado; enviaré los documentos esta semana.",)),
           "funkcje": (("abogado", "abogada"), ("abogado asociado", "abogada asociada"), ("asistente de dirección",) * 2,
                       ("técnico de recursos humanos", "técnica de recursos humanos")), "tel": "tel."},
    "de": {"karta": "Mandantenblatt", "nazwisko": "Name", "adres": "Anschrift", "telefon": "Telefon", "rachunek": "Konto",
           "plik_karty": "mandantenblatt.pdf", "plik_wiadomosci": "nachricht", "plik_vcard": "kontakt.vcf",
           "temat_zagn": "Mandantendaten für den Vertrag", "powitanie": "Guten Tag,",
           "w_zalaczeniu": "anbei das Mandantenblatt von {kto}, Tel. {tel}. Bitte bereiten Sie den Vertrag vor.",
           "pozdrawiam": "Mit freundlichen Grüßen", "przekazuje": "Unten leite ich den bisherigen Schriftverkehr in dieser Sache weiter; "
           "die Visitenkarte des Sachverständigen ist beigefügt.",
           "naglowki": ("Von", "Gesendet", "An", "Betreff"), "napisal": "Am {data} schrieb {kto} <{adres}>:",
           "tematy": ("Unterlagen zum Vertrag", "Ergebnisse der Besprechung", "Angaben für die Vollmacht", "Unterzeichnung des Nachtrags"),
           "zdania": (("Anbei die Angaben für die Vollmacht: {k.pelne}, {k.id_etykieta} {k.id}.",),
                      ("Zustellanschrift des Mandanten: {k.adres}.",), ("Bitte überweisen Sie den Vorschuss auf das Konto {k.rachunek}.",),
                      ("Der Mandant bittet um Rückruf unter {k.telefon}.",), ("Ich bestätige die Absprachen; die Unterlagen folgen diese Woche.",)),
           "funkcje": (("Rechtsanwalt", "Rechtsanwältin"), ("Rechtsreferendar", "Rechtsreferendarin"), ("Büroleiter", "Büroleiterin"),
                       ("Personalreferent", "Personalreferentin")), "tel": "Tel."},
    "fr": {"karta": "Fiche client", "nazwisko": "Nom et prénom", "adres": "Adresse", "telefon": "Téléphone", "rachunek": "Compte",
           "plik_karty": "fiche_client.pdf", "plik_wiadomosci": "message", "plik_vcard": "contact.vcf",
           "temat_zagn": "Données du client pour le contrat", "powitanie": "Bonjour,",
           "w_zalaczeniu": "veuillez trouver ci-joint la fiche de {kto}, tél. {tel}. Merci de préparer le contrat.",
           "pozdrawiam": "Cordialement", "przekazuje": "Je vous transfère ci-dessous la correspondance antérieure sur ce dossier ; "
           "la carte de contact de l'expert est jointe.",
           "naglowki": ("De", "Envoyé", "À", "Objet"), "napisal": "Le {data}, {kto} <{adres}> a écrit :",
           "tematy": ("Documents pour le contrat", "Suite à la réunion", "Données pour la procuration", "Signature de l'avenant"),
           "zdania": (("Voici les données pour la procuration : {k.pelne}, {k.id_etykieta} {k.id}.",),
                      ("Adresse du client pour les notifications : {k.adres}.",), ("Merci de virer la provision sur le compte {k.rachunek}.",),
                      ("Le client souhaite être rappelé au {k.telefon}.",), ("Je confirme ce qui a été convenu ; les documents suivront cette semaine.",)),
           "funkcje": (("avocat", "avocate"), ("avocat collaborateur", "avocate collaboratrice"),
                       ("assistant de direction", "assistante de direction"),
                       ("chargé de ressources humaines", "chargée de ressources humaines")), "tel": "tél."},
}
_GNIAZDO = re.compile(r"\{([a-z_.]+)\}")
KRESKA_OUTLOOKA = "_" * 32


def _rdzenie(slowa: set[str]) -> set[str]:
    return {s[:5] for s in slowa if len(s) >= 5}


class FabrykaH4b(Fabryka):
    """Fabryka osób i wartości dodatków H4b (identyfikatory `h.<rola>.<pole>#n`). Osoba dodatku nie dzieli z dokumentem ani
    słów imienia i nazwiska, ani ich pięcioliterowych początków: forma odmieniona w treści („Wiśniewskiemu”) i mianownik w
    załączniku („Wiśniewski”) to dla sędziego (rdzeń wyrazu) ta sama osoba – wyciek w załączniku trafiałby wartość z treści."""

    PREFIKS = "h"

    def osoba(self) -> Osoba:
        rdzenie = _rdzenie(self.zajete)

        def rozlaczna(x: Osoba) -> bool:
            slowa = tokeny(x.imie) | tokeny(x.nazwisko)
            return not (slowa & self.zajete) and not (_rdzenie(slowa) & rdzenie)
        o = osoba(self.gen, self.ctx, warunek=rozlaczna)
        self.zajete |= tokeny(o.imie) | tokeny(o.nazwisko)
        self.osoby += 1
        return o


def _firma(gen: BazowyGenerator, f: Fabryka):
    """Fikcyjna firma, której nazwa nie dzieli słów (≥ 4 znaki) z wartościami dokumentu ani osobami dodatku."""
    for _ in range(500):
        firma = gen.firma(kraj=f.ctx.kraj)
        slowa = {t for t in tokeny(firma.nazwa) if len(t) >= 4}
        if not slowa & f.zajete:
            f.zajete |= slowa
            return firma
    raise RuntimeError("nie udało się wylosować firmy o nazwie rozłącznej z dokumentem")  # pragma: no cover


def _klucz_id(f: Fabryka, o: Osoba) -> str:
    return next((k for k in (KLUCZ_ID[f.jezyk], "NINO", "SSN") if k in o.ids), None) or next(iter(o.ids))


class Rola:
    """Osoba dodatku pod nazwą roli: wartości gold `h.<rola>.<pole>#n` z miejscem i cechami roli."""

    def __init__(self, f: Fabryka, rola: str, miejsce: str, cechy: tuple[str, ...] = ()) -> None:
        self.f, self.rola, self.miejsce, self.cechy = f, rola, miejsce, cechy
        self.o = f.osoba()
        self.nr = f.osoby
        self.klucz_id = _klucz_id(f, self.o)
        self.adres_email = f"{self.o.email.split('@')[0]}@{DOMENY_UKRYTYCH[f.jezyk]}"

    def w(self, pole: str, tekst: str, kategoria: str) -> Wartosc:
        return self.f.w(self.rola, pole, tekst, kategoria, self.miejsce, self.nr, self.cechy)

    def pole(self, nazwa: str) -> str | Wartosc:
        """Wartość (albo zwykły tekst – `id_etykieta`) pola osoby wg nazwy gniazda szablonu zdania."""
        o = self.o
        if nazwa == "pelne":
            return self.w("pelne", o.pelne_imie, "OSOBA")
        if nazwa == "email":
            return self.w("email", self.adres_email, "EMAIL")
        if nazwa == "telefon":
            return self.w("telefon", o.telefon, "TELEFON")
        if nazwa == "rachunek":
            return self.w("rachunek", o.rachunek, "RACHUNEK")
        if nazwa == "adres":
            return self.w("adres", o.adres.linia(), "ADRES")
        if nazwa == "id":
            return self.w(self.klucz_id.lower(), o.ids[self.klucz_id], MAPA_KATEGORII[self.klucz_id])
        if nazwa == "id_etykieta":
            return ETYKIETA_ID.get(self.klucz_id, self.klucz_id)
        raise KeyError(nazwa)


def _wypelnij(szablon: str, gniazda: dict[str, object]) -> list[str | Wartosc]:
    """Fragmenty zdania: tekst szablonu i wartości z `gniazda` (`{nazwa}` albo `{rola.pole}` – `Rola.pole`)."""
    wynik: list[str | Wartosc] = []
    poz = 0
    for m in _GNIAZDO.finditer(szablon):
        if m.start() > poz:
            wynik.append(szablon[poz:m.start()])
        nazwa = m.group(1)
        if "." in nazwa:
            rola, pole = nazwa.split(".", 1)
            v = gniazda[rola].pole(pole)       # type: ignore[attr-defined]
        else:
            v = gniazda[nazwa]
        wynik.append(v if isinstance(v, Wartosc) else str(v))
        poz = m.end()
    if poz < len(szablon):
        wynik.append(szablon[poz:])
    return wynik


def _baza(jezyk: str, typ: str, seed: int, sol: str) -> tuple[Wynik, BazowyGenerator]:
    gen = Generator(jezyk, seed)
    return zbuduj_z_kontekstem(SZABLONY[(jezyk, typ)], gen, random.Random(f"pbench-h4b-{sol}:{seed}")), gen


def _wstaw_przed_zakonczeniem(d: Dokument, elementy: list[Element]) -> None:
    """Akapity przed ostatnim akapitem wiadomości (formułą grzecznościową)."""
    ostatni = max((i for i, e in enumerate(d.elementy) if e.rodzaj == "akapit"), default=len(d.elementy) - 1)
    d.elementy[ostatni:ostatni] = elementy


def _ostatnia_niedziela(rok: int, miesiac: int) -> dt.date:
    d = dt.date(rok, miesiac, 31)
    return d - dt.timedelta(days=(d.weekday() + 1) % 7)


def strefa(kraj: str, chwila: dt.datetime) -> dt.timezone:
    """Przesunięcie czasu lokalnego kraju dokumentu w dniu `chwila` (czas letni UE: od ostatniej niedzieli marca do ostatniej
    niedzieli października; USA – czas wschodni, od drugiej niedzieli marca do pierwszej niedzieli listopada; dokładność do
    dnia – godzina zmiany czasu pomijana)."""
    dzien = chwila.date()
    if kraj == "US":
        marzec, listopad = dt.date(dzien.year, 3, 8), dt.date(dzien.year, 11, 1)
        start = marzec + dt.timedelta(days=(6 - marzec.weekday()) % 7)
        koniec = listopad + dt.timedelta(days=(6 - listopad.weekday()) % 7)
        return dt.timezone(dt.timedelta(hours=-4 if start <= dzien < koniec else -5))
    letni = _ostatnia_niedziela(dzien.year, 3) <= dzien < _ostatnia_niedziela(dzien.year, 10)
    return dt.timezone(dt.timedelta(hours={"GB": 0, "UA": 2}.get(kraj, 1) + letni))


def wyslano(wynik: Wynik, seed: int) -> dt.datetime:
    """Chwila wysłania wiadomości głównej (H6b-fix1): między wniesieniem pozwu a terminem z treści szablonu e-mail
    (`ctx.odp_termin` – „uwagi do …”), godziny pracy, strefa kraju dokumentu. Osobne losowanie (`pbench-wyslano:<seed>`) –
    pozostała treść dokumentu się nie zmienia."""
    rng = random.Random(f"pbench-wyslano:{seed}")
    daty = wynik.kontekst.daty
    dni = max(1, (daty["odp_termin"] - daty["pozew"]).days - 1)
    dzien = daty["pozew"] + dt.timedelta(days=rng.randint(1, dni))
    dzien -= dt.timedelta(days=max(0, dzien.weekday() - 4))         # dzień roboczy (weekend -> piątek, nadal po pozwie)
    chwila = dt.datetime(dzien.year, dzien.month, dzien.day, rng.randint(8, 17), rng.randint(0, 59), rng.randint(0, 59))
    return chwila.replace(tzinfo=strefa(wynik.kontekst.kraj, chwila))


def _w_godzinach_pracy(rng: random.Random, d: dt.datetime) -> dt.datetime:
    """Chwila przesunięta WSTECZ w godziny 8–19 (wieczór – wcześniej tego dnia, noc – poprzedni dzień po południu): porządek
    wiadomości wątku się nie zmienia."""
    if d.hour >= 20:
        return d.replace(hour=rng.randint(15, 19))
    if d.hour < 8:
        return (d - dt.timedelta(days=1)).replace(hour=rng.randint(14, 19))
    return d


def _daty(rng: random.Random, jezyk: str, n: int, przed: dt.datetime, kraj: str = "") -> list[str]:
    """Daty `n` wiadomości wątku od najnowszej (najnowsza 2–72 godziny przed odpowiedzią `przed`, każda następna starsza
    o 2–72 godziny, w godzinach 8–19 – chronologicznie przed wiadomością główną), w zapisie kraju dokumentu (czas lokalny;
    USA: miesiąc/dzień/rok i zegar 12-godzinny)."""
    d = _w_godzinach_pracy(rng, przed.replace(tzinfo=None) - dt.timedelta(hours=rng.randint(2, 72), minutes=rng.randint(0, 59)))
    wzor = ("%m/%d/%Y %I:%M %p" if kraj == "US" else "%d.%m.%Y %H:%M" if jezyk in ("pl", "de") else "%d/%m/%Y %H:%M")
    wynik = []
    for _ in range(n):
        wynik.append(d.strftime(wzor))
        d = _w_godzinach_pracy(rng, d - dt.timedelta(hours=rng.randint(2, 72), minutes=rng.randint(0, 59)))
    return wynik


# ----------------------------------------------------------------------------- ukryta_poczta
def _karta(f: Fabryka, k: Rola, w: str) -> Element:
    """Załącznik PDF – karta klienta: tytuł i wiersze „etykieta: wartość” (wiersze rozdzielone `ROZDZIELACZ`). Załącznik
    wiadomości zagnieżdżonej ma inną nazwę pliku niż załącznik wiadomości głównej."""
    t, dk = TEKSTY[f.jezyk], dwukropek(f.jezyk)
    wiersze: list[str | Wartosc] = [t["karta"], ROZDZIELACZ, f"{t['nazwisko']}{dk}", k.pole("pelne"), ROZDZIELACZ,
                                    f"{k.pole('id_etykieta')}{dk}", k.pole("id"), ROZDZIELACZ, f"{t['adres']}{dk}", k.pole("adres"),
                                    ROZDZIELACZ, f"{t['telefon']}{dk}", k.pole("telefon"), ROZDZIELACZ, f"{t['rachunek']}{dk}",
                                    k.pole("rachunek")]
    nazwa = t["plik_karty"] if w == "glowna" else t["plik_karty"].replace(".pdf", "_1.pdf")
    return Element("poczta.zalacznik_pdf", wiersze, {"nazwa": nazwa, "w": w})


def _ukryta_poczta(jezyk: str, typ: str, seed: int, fmt: str) -> tuple[Wynik, BazowyGenerator, dict]:
    wynik, gen = _baza(jezyk, typ, seed, "up")
    f = FabrykaH4b(gen, wynik.kontekst, wynik)
    t = TEKSTY[jezyk]
    karta_glowna = _karta(f, Rola(f, "karta", MIEJSCE), "glowna")
    nadawca, adresat, klient = Rola(f, "nadawca", MIEJSCE), Rola(f, "adresat", MIEJSCE), Rola(f, "klient", MIEJSCE)
    tresc = [t["powitanie"], "\n", *_wypelnij(t["w_zalaczeniu"], {"kto": klient.pole("pelne"), "tel": klient.pole("telefon")}),
             "\n\n", t["pozdrawiam"], "\n", nadawca.pole("pelne"), "\n"]
    wiadomosc = Element("poczta.wiadomosc", [nadawca.pole("pelne"), ROZDZIELACZ, nadawca.pole("email"), ROZDZIELACZ,
                                             adresat.pole("pelne"), ROZDZIELACZ, adresat.pole("email"), ROZDZIELACZ,
                                             t["temat_zagn"], ROZDZIELACZ, *tresc],
                        {"nazwa": f"{t['plik_wiadomosci']}.{fmt}", "pola": list(POLA_WIADOMOSCI)})
    # wiadomość zagnieżdżona (przekazywana) – 1–14 dni przed wiadomością główną
    chwila = wyslano(wynik, seed)
    wynik.dokument.wyslano = chwila.isoformat()
    rng = random.Random(f"pbench-up-data:{seed}")
    starsza = chwila.replace(tzinfo=None) - dt.timedelta(days=rng.randint(1, 14), hours=rng.randint(0, 6),
                                                          minutes=rng.randint(0, 59))
    wiadomosc.atrybuty["data"] = starsza.replace(tzinfo=strefa(wynik.kontekst.kraj, starsza)).isoformat()
    wynik.dokument.ukryte = [karta_glowna, wiadomosc, _karta(f, klient, "wiadomosc")]
    return wynik, gen, {}


# ----------------------------------------------------------------------------- cytowane_watki_vcard
def _vcard_esc(tekst: str) -> str:
    """Wartość tekstowa vCard (RFC 6350 3.4 / RFC 2426 4): ukośnik, przecinek, średnik i nowy wiersz poprzedzone `\\`."""
    return tekst.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def _ulica(a: Adres) -> str:
    return f"{a.numer} {a.ulica}" if a.kraj in ("GB", "US", "FR") else f"{a.ulica} {a.numer}"


def _bez_diakrytykow(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))


def _miasto_w_dokumencie(miasto: str, d: Dokument) -> bool:
    """Czy słowo nazwy miasta (albo jego cztero-/pięcioliterowy początek bez znaków diakrytycznych – forma odmieniona „w Krakowie”)
    jest w tekście dokumentu (treść, wątek, metadane)."""
    teksty = [f if isinstance(f, str) else f.tekst for e in d.elementy for f in e.fragmenty]
    teksty += [v if isinstance(v, str) else v.tekst for v in d.metadane.values()]
    slowa = {_bez_diakrytykow(t) for x in teksty for t in tokeny(x)}
    poczatki = {t[:n] for t in slowa for n in (4, 5) if len(t) >= n}
    for t in (_bez_diakrytykow(x) for x in tokeny(miasto)):
        if t in slowa or (len(t) >= 4 and t[:5] in poczatki):
            return True
    return False


def _vcard(f: Fabryka, gen: BazowyGenerator, rng: random.Random, d: Dokument) -> Element:
    """Wizytówka vCard osoby trzeciej (biegły, kontrahent): tekst pliku `.vcf` z wartościami (zapis już ze znakami ucieczki).
    Miasto adresu spoza miast dokumentu: to samo miasto w treści albo w wątku czyni wartość niejednoznaczną (wyłączoną z oceny)."""
    v = Rola(f, "vcard", MIEJSCE)
    for _ in range(500):
        if not _miasto_w_dokumencie(v.o.adres.miejscowosc, d):
            break
        v.o = dataclasses.replace(v.o, adres=gen.adres(v.o.kraj))
    o, firma = v.o, _firma(gen, f)
    wersja = rng.choice(("3.0", "4.0"))
    funkcja = rng.choice(TEKSTY[f.jezyk]["funkcje"])[o.plec == "K"]    # (forma męska, żeńska) wg płci osoby
    w = lambda pole, tekst, kat: v.w(pole, _vcard_esc(tekst), kat)       # noqa: E731
    typ_tel, typ_email, typ_adr = (("TYPE=WORK,VOICE", "TYPE=INTERNET,WORK", "TYPE=WORK") if wersja == "3.0"
                                   else ("TYPE=work,voice;VALUE=text", "TYPE=work", "TYPE=work"))
    k = "\r\n"
    fr: list[str | Wartosc] = [f"BEGIN:VCARD{k}VERSION:{wersja}{k}N:", w("nazwisko", o.nazwisko, "OSOBA"), ";",
                               w("imie", o.imie, "OSOBA"), f";;;{k}FN:", w("pelne", o.pelne_imie, "OSOBA"), f"{k}ORG:",
                               w("organizacja", firma.nazwa, "ORGANIZACJA"), f"{k}TITLE:{_vcard_esc(funkcja)}{k}TEL;{typ_tel}:",
                               w("telefon", o.telefon, "TELEFON"), f"{k}EMAIL;{typ_email}:", w("email", v.adres_email, "EMAIL"),
                               f"{k}ADR;{typ_adr}:;;", w("ulica", _ulica(o.adres), "ADRES"), ";",
                               w("miejscowosc", o.adres.miejscowosc, "MIEJSCOWOSC"), ";;", w("kod", o.adres.kod, "KOD_POCZTOWY"),
                               f";{k}END:VCARD{k}"]
    return Element("poczta.vcard", fr, {"nazwa": TEKSTY[f.jezyk]["plik_vcard"], "wersja": wersja})


def _linie_wiadomosci(f: Fabryka, t: dict, od: Rola, do: Rola, k: Rola, temat: str, data: str, styl: str,
                      zdania: list[tuple[str, ...]], funkcja: str) -> tuple[list[list[str | Wartosc]], list[list[str | Wartosc]]]:
    """(wiersze nagłówka, wiersze treści ze stopką) jednej cytowanej wiadomości."""
    if styl == "outlook":
        n_od, n_wys, n_do, n_temat = t["naglowki"]
        dk = dwukropek(f.jezyk)
        naglowek = [[KRESKA_OUTLOOKA], [f"{n_od}{dk}", od.pole("pelne"), " <", od.pole("email"), ">"], [f"{n_wys}{dk}{data}"],
                    [f"{n_do}{dk}", do.pole("pelne"), " <", do.pole("email"), ">"], [f"{n_temat}{dk}RE: {temat}"], []]
    else:
        naglowek = [_wypelnij(t["napisal"], {"data": data, "kto": od.pole("pelne"), "adres": od.pole("email")})]
    tresc: list[list[str | Wartosc]] = [[t["powitanie"]]]
    for zdanie in zdania:
        tresc.append(_wypelnij(zdanie[0], {"k": k}))
    tresc += [[], ["--"], [od.pole("pelne")], [funkcja], [f"{t['tel']} ", od.pole("telefon")], [od.pole("email")]]
    return naglowek, tresc


def _z_prefiksem(wiersze: list[list[str | Wartosc]], glebokosc: int) -> list[str | Wartosc]:
    prefiks = ">" * glebokosc + " " if glebokosc else ""
    wynik: list[str | Wartosc] = []
    for i, w in enumerate(wiersze):
        if i:
            wynik.append("\n")
        wynik += ([prefiks.rstrip()] if not w else [prefiks, *w]) if prefiks else w
    return wynik


def _watek(f: Fabryka, rng: random.Random, przed: dt.datetime) -> list[Element]:
    """3–5 cytowanych wiadomości (od najnowszej, wszystkie przed wiadomością główną wysłaną `przed`): akapity z atrybutem
    `cytat`, wartości z cechą `cytat`."""
    t = TEKSTY[f.jezyk]
    a, b, k = (Rola(f, rola, MIEJSCE_CYTATU, (CECHA_CYTAT,)) for rola in ("watek_a", "watek_b", "watek_klient"))
    funkcje = {kto: para[r.o.plec == "K"] for kto, r, para in zip(("a", "b"), (a, b), rng.sample(t["funkcje"], 2))}
    temat = rng.choice(t["tematy"])
    n = rng.randint(3, 5)
    style = ["outlook", "gmail"] + [rng.choice(("outlook", "gmail")) for _ in range(n - 2)]
    rng.shuffle(style)
    zdania = list(t["zdania"])
    rng.shuffle(zdania)
    daty = _daty(rng, f.jezyk, n, przed, f.ctx.kraj)
    elementy = []
    glebokosc = 0
    for i in range(n):
        od, do, kto = (a, b, "a") if i % 2 == 0 else (b, a, "b")
        moje = [zdania[(2 * i) % len(zdania)], zdania[(2 * i + 1) % len(zdania)]][:1 + (i % 2)]
        naglowek, tresc = _linie_wiadomosci(f, t, od, do, k, temat, daty[i], style[i], moje, funkcje[kto])
        if style[i] == "gmail":
            glebokosc += 1
            fragmenty = [*_z_prefiksem(naglowek, glebokosc - 1), "\n", *_z_prefiksem(tresc, glebokosc)]
        else:
            fragmenty = _z_prefiksem(naglowek + tresc, glebokosc)
        elementy.append(Element("akapit", fragmenty, {"cytat": True}))
    return elementy


def _cytowane(jezyk: str, typ: str, seed: int, fmt: str) -> tuple[Wynik, BazowyGenerator, dict]:
    wynik, gen = _baza(jezyk, typ, seed, "cv")
    rng = random.Random(f"pbench-cv:{seed}")
    f = FabrykaH4b(gen, wynik.kontekst, wynik)
    d = wynik.dokument
    _wstaw_przed_zakonczeniem(d, [Element("akapit", [TEKSTY[jezyk]["przekazuje"]])])
    chwila = wyslano(wynik, seed)
    d.wyslano = chwila.isoformat()
    d.elementy += _watek(f, rng, chwila)
    d.ukryte = [_vcard(f, gen, rng, d)]
    return wynik, gen, {}


_FUNKCJE = {P.UKRYTA_POCZTA: _ukryta_poczta, P.CYTOWANE_WATKI_VCARD: _cytowane}
#: Generatory przypadków pocztowych H4b: przypadek -> {(język, "email"): funkcja}.
GENERATORY: dict[str, dict] = {p: {k: fn for k in sorted(SZABLONY) if k[1] == "email"} for p, fn in _FUNKCJE.items()}


# ----------------------------------------------------------------------------- po renderowaniu: załączniki
def _pola(e: Element) -> dict[str, str]:
    """Teksty pól elementu (fragmenty rozdzielone `ROZDZIELACZ`) wg `atrybuty["pola"]`."""
    teksty = "".join(fr if isinstance(fr, str) else fr.tekst for fr in e.fragmenty).split(ROZDZIELACZ)
    return dict(zip(e.atrybuty["pola"], teksty))


def _wartosci(e: Element) -> list[Wartosc]:
    return [fr for fr in e.fragmenty if isinstance(fr, Wartosc)]


def _pdf(d: Dokument, e: Element, nr: int) -> tuple[bytes, list[Wartosc]]:
    """Karta klienta jako PDF (zwykły renderer PDF, wiersze elementu = akapity); gold z miejscem `zalacznik`."""
    from .render.pdf import renderuj_pdf
    akapity: list[Element] = [Element("akapit", [])]
    for fr in e.fragmenty:
        if fr == ROZDZIELACZ:
            akapity.append(Element("akapit", []))
        else:
            akapity[-1].fragmenty.append(fr)
    mini = Dokument(f"{d.id}-pdf{nr}", d.jezyk, "notatka", "pdf", akapity)
    with tempfile.TemporaryDirectory(prefix="pbench-h4b-") as tmp:
        sciezka = Path(tmp) / "karta.pdf"
        r = renderuj_pdf(mini, sciezka, set())
        dane = sciezka.read_bytes()
    return dane, [dataclasses.replace(w, miejsce=MIEJSCE) for w in r.wartosci]


def _vcf(e: Element) -> bytes:
    return "".join(fr if isinstance(fr, str) else fr.tekst for fr in e.fragmenty).encode("utf-8")


def obrob(b, plik: Path, d: Dokument, gold_obrazy: list[dict]) -> tuple[list[Wartosc], list[dict]]:
    """Dopisuje załączniki przypadku (`d.ukryte`) do gotowej wiadomości `plik`; zwraca (gold do `gold_plik`, `gold_obrazy`)."""
    rng = rng_dokumentu(d)
    znacznik = f"{rng.randrange(16 ** 8):08x}"
    gold: list[Wartosc] = []
    glowne: list[pliki_poczta.Zalacznik] = []
    zagniezdzone: list[pliki_poczta.Plik] = []
    wiadomosc: Element | None = None
    for nr, e in enumerate(d.ukryte, 1):
        if e.rodzaj == "poczta.zalacznik_pdf":
            dane, wart = _pdf(d, e, nr)
            gold += wart
            (glowne if e.atrybuty["w"] == "glowna" else zagniezdzone).append(pliki_poczta.Plik(e.atrybuty["nazwa"], TYP_PDF, dane))
        elif e.rodzaj == "poczta.vcard":
            gold += _wartosci(e)
            glowne.append(pliki_poczta.Plik(e.atrybuty["nazwa"], TYP_VCARD, _vcf(e)))
        elif e.rodzaj == "poczta.wiadomosc":
            wiadomosc = e
            gold += _wartosci(e)
        else:
            raise ValueError(f"nieznany element poczty: {e.rodzaj!r}")
    if wiadomosc is not None:
        p = _pola(wiadomosc)
        data = dt.datetime(rng.randint(2023, 2025), rng.randint(1, 12), rng.randint(1, 28), rng.randint(8, 18),
                           rng.randint(0, 59), tzinfo=dt.timezone(dt.timedelta(hours=1)))
        if "data" in wiadomosc.atrybuty:     # przed wiadomością główną (H6b-fix1); losowania wyżej – bez zmian
            data = dt.datetime.fromisoformat(wiadomosc.atrybuty["data"])
        glowne.insert(0, pliki_poczta.Wiadomosc(wiadomosc.atrybuty["nazwa"], (p["od"], p["od_adres"]), (p["do"], p["do_adres"]),
                                                p["temat"], p["tresc"], data, f"<{rng.randrange(16 ** 24):024x}@pbench.invalid>",
                                                zagniezdzone))
    pliki_poczta.dolacz(plik, d.format, glowne, znacznik)
    return gold, gold_obrazy
