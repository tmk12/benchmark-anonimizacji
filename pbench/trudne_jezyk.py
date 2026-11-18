"""Pułapki językowe (spec §11 pkt 2, zadanie H2): przypadki `odmiana_nazwisk`, `nazwiska_zwykle_slowa`, `zdrobnienia`,
`nazwisko_imie`, `parafy`, `liczby_slownie`.

Każdy generator składa dokument kodem (`pbench.skladacz`) z danych jednego `Generator`-a i `Kontekst`-u (daty w dni
robocze, nie późniejsze niż 2026-10-29; osoby pełnoletnie), więc dokument jest spójny jak w trzonie. Tekst zwykły nie
zawiera cyfr ani nazw własnych poza wartościami gold (inaczej wykrycie niezaznaczone w gold liczyłoby się jako
nadmiarowe).

* `odmiana_nazwisk` (PL) – liczba mnoga i formy rodzinne („Państwo Kowalscy”, „u Wiśniewskich”, „z Nowakami”) oraz
  przypadki zależne osób występujących imiennie. Gold = forma z tekstu (OSOBA). `encja` formy rodzinnej = encja głowy
  rodziny (mąż), który w dokumencie występuje imiennie.
* `nazwiska_zwykle_slowa` – nazwisko = zwykłe słowo (Kowal, Mróz, Baker, Müller, Herrero, Boulanger…). W tym samym
  dokumencie to słowo w znaczeniu pospolitym NIE jest gold; offsety takich wystąpień są w polu manifestu
  `pulapki_pospolite` (lista `{start, end, tekst, encja}` w tekście poziomu 1; `encja` = osoba o tym nazwisku).
* `zdrobnienia` – osoba pełnym imieniem, potem zdrobnieniem (Kasia Nowak, Bill, Hansi, Pepe, Manu); wspólna `encja`.
* `nazwisko_imie` – tabela uczestników z zapisem „KOWALSKI Jan”, „Nowak Anna”, „SMITH, John”; gold = całość.
* `parafy` – inicjały w stopce, na marginesie i w oznaczeniu pisma („JK”, „J.K.”, „/AN/”, „jk/ak”): INICJALY; inicjały
  osoby występującej w dokumencie z nazwiskiem mają jej `encja`. Wzorzec inicjałów nie występuje poza spanami gold, a różne
  osoby mają różne inicjały (`trudne_wspolne.inicjaly_jednoznaczne`; inaczej kolejne ziarno).
* `liczby_slownie` – umowa pożyczki z datą, datą urodzenia i kwotami zapisanymi cyframi I słownie (5 języków,
  `pbench.liczebniki`), w PL także PESEL słownie. Każdy zapis to osobna wartość gold.
"""
from __future__ import annotations

import dataclasses
import random
from typing import Callable

from .budowa import Kontekst
from .dane.wspolne import BazowyGenerator, Osoba
from .liczebniki import cyfry_slownie, data as data_slownie, kwota as kwota_slownie
from .odmiana_pl import odmien
from .skladacz import G, Pulapka, Skladacz
from .trudne_wspolne import (JEZYKI, ZABLOKOWANE, Os, bez_blokady, data_gold, inicjaly, nowy_kontekst,  # noqa: F401
                             z_inicjalami_jednoznacznymi,
                             osoba, rng_h2, zmien)

#: Wynik generatora: (Wynik, generator, dodatki manifestu: `pulapki` = lista PulapkaWTekscie)
Generator_H2 = Callable[[str, str, int], tuple]

#: Nazwiska polskie wyłączone z rodzin „Państwo X” (nazwiska osób publicznych).
NAZWISKA_WYLACZONE: frozenset[str] = frozenset({"Kwaśniewski", "Nawrocki", "Komorowski", "Kaczyński", "Morawiecki",
                                                 "Wałęsa", "Jaruzelski", "Mazowiecki", "Buzek", "Duda", "Tusk"})


_bez_blokady = bez_blokady


# ============================================================================= 1. odmiana_nazwisk (PL)
_PANSTWO = {"mian": "Państwo", "dop": "Państwa", "cel": "Państwu", "bier": "Państwa", "narz": "Państwem", "msc": "Państwu"}
_PRZYP_AKT = ("mian", "dop", "cel", "bier", "narz", "msc")
#: Nazwiska męskie na spółgłoskę ze słownika generatora, odmieniające się regularnie w liczbie mnogiej (-owie, -ów…).
NAZWISKA_SPOLGLOSKOWE: frozenset[str] = frozenset({"Nowak", "Kowalczyk", "Wójcik", "Mazur", "Krawczyk", "Pawlak",
                                                    "Michalak", "Król"})

_RAMKI_RODZINY: dict[str, tuple[str, ...]] = {
    "mian": ("{P} {F} zgłosili się do kancelarii w sprawie sporu z wykonawcą remontu.",
             "Na spotkaniu byli obecni {P} {F}.",
             "{P} {F} zawarli umowę o remont łazienki."),
    "dop": ("Dokumentacja {P} {F} obejmuje umowę, protokół odbioru i korespondencję z wykonawcą.",
            "Wizyta w mieszkaniu u {F} odbyła się w piątek po południu.",
            "Mieszkanie {P} {F} znajduje się na drugim piętrze."),
    "cel": ("Kancelaria przekazała {P} {F} projekt ugody.",
            "Wykonawca zaproponował {P} {F} obniżenie ceny."),
    "bier": ("Zawiadomiono {P} {F} o terminie rozprawy.",
             "Kancelaria reprezentuje {P} {F} w postępowaniu."),
    "narz": ("Pełnomocnik uzgodnił z {P} {F} treść pełnomocnictwa.",
             "Spotkanie z {F} odbyło się w kancelarii."),
    "msc": ("Mowa była o {F}, którzy złożyli reklamację.",
            "Sąsiedzi wspominali o {F} i o terminie zakończenia prac."),
}
_RAMKI_POJEDYNCZE: dict[str, dict[str, tuple[str, ...]]] = {
    "M": {"dop": ("Pełnomocnictwo dotyczy majątku {X}.",),
          "cel": ("Kancelaria przesłała {X} wzór pełnomocnictwa.",),
          "bier": ("Kancelaria reprezentuje {X} w tej sprawie.",),
          "narz": ("Rozmowa z {X} trwała kwadrans.",),
          "msc": ("Mowa była o {X} i jego małżonce.",)},
    "K": {"dop": ("Dokumenty należą do {X}.",),
          "cel": ("Projekt ugody przesłano {X}.",),
          "bier": ("Kancelaria poinformowała {X} o terminie rozprawy.",),
          "narz": ("Rozmowa telefoniczna z {X} trwała kwadrans.",),
          "msc": ("Mowa była o {X}.",)},
}


def forma_rodzinna(nazwisko_m: str, przyp: str) -> str:
    """Nazwisko rodziny w liczbie mnogiej („Państwo Kowalscy”): Kowalski -> Kowalscy/Kowalskich/Kowalskim/Kowalskimi,
    Nowak -> Nowakowie/Nowaków/Nowakom/Nowakami/Nowakach. Obsługuje nazwiska męskie na -ski/-cki/-dzki i
    regularne spółgłoskowe (`NAZWISKA_SPOLGLOSKOWE`)."""
    if przyp not in _PRZYP_AKT:
        raise ValueError(f"nieznany przypadek: {przyp!r}")
    if nazwisko_m.endswith(("ski", "cki", "dzki")):
        if przyp == "mian":
            return nazwisko_m[:-2] + "cy"
        return nazwisko_m[:-1] + {"dop": "ich", "bier": "ich", "msc": "ich", "cel": "im", "narz": "imi"}[przyp]
    if nazwisko_m not in NAZWISKA_SPOLGLOSKOWE:
        raise ValueError(f"nazwisko {nazwisko_m!r} spoza obsługiwanych odmian rodzinnych")
    return nazwisko_m + {"mian": "owie", "dop": "ów", "bier": "ów", "cel": "om", "narz": "ami", "msc": "ach"}[przyp]


def nazwisko_zenskie(nazwisko_m: str) -> str:
    """Forma żeńska (Kowalski -> Kowalska, Nowak -> Nowak)."""
    return nazwisko_m[:-1] + "a" if nazwisko_m.endswith(("ski", "cki", "dzki")) else nazwisko_m


def _buduj_odmiana(jezyk: str, typ: str, seed: int) -> tuple:
    gen, ctx = nowy_kontekst("pl", seed)
    rng = rng_h2(seed, "odmiana")
    adj = lambda o: o.nazwisko.endswith(("ski", "cki", "dzki")) and o.nazwisko not in NAZWISKA_WYLACZONE
    m1 = Os("m1", osoba(gen, ctx, "M", adj), "pl")
    k0 = osoba(gen, ctx, "K")
    k1 = Os("k1", dataclasses.replace(zmien(k0, nazwisko=nazwisko_zenskie(m1.o.nazwisko)), adres=m1.o.adres), "pl")
    m2 = Os("m2", osoba(gen, ctx, "M", lambda o: o.nazwisko in NAZWISKA_SPOLGLOSKOWE), "pl")
    s = Skladacz("pl")
    f1, f2 = m1.o.nazwisko, m2.o.nazwisko

    def rodz(przyp: str, head: Os, nazwisko_m: str) -> G:
        return head.g("rodzina", forma_rodzinna(nazwisko_m, przyp), cechy=("liczba_mnoga", "forma_rodzinna"))

    def poj(przyp: str, os_: Os) -> G:
        return os_.g("pelne", odmien(os_.o.imie, os_.o.nazwisko, os_.o.plec, przyp), cechy=("przypadek_zalezny",))

    def rama(przyp: str, head: Os, nazwisko_m: str) -> None:
        szablon = rng.choice(_RAMKI_RODZINY[przyp])
        s.akapit(szablon, F=rodz(przyp, head, nazwisko_m), P=_PANSTWO[przyp])

    dok = data_gold(ctx, "dok")
    if typ == "notatka_rodzina":
        s.naglowek("Notatka służbowa z rozmowy z klientami")
        s.akapit("Dnia {d} w kancelarii odbyło się spotkanie z klientami: {m1} oraz {k1}, zamieszkałymi przy {adres}. "
                 "Klienci występują wspólnie jako {P} {F}.", d=dok, m1=m1.pelne, k1=k1.pelne, adres=m1.adres,
                 P=_PANSTWO["mian"], F=rodz("mian", m1, f1))
    else:
        s.naglowek("Protokół ze spotkania w sprawie remontu")
        s.akapit("Spotkanie odbyło się w dniu {d} w kancelarii; oględziny lokalu przeprowadzono wcześniej u {F}. "
                 "Obecni: {m1}, {k1} oraz {m2}.",
                 d=dok, F=rodz("dop", m2, f2), m1=m1.pelne, k1=k1.pelne, m2=m2.pelne)
    for przyp in _PRZYP_AKT:                      # rodzina 1: każdy przypadek (mianownik jest już we wstępie protokołu)
        if przyp != "mian" or typ == "notatka_rodzina":
            rama(przyp, m1, f1)
    if typ == "notatka_rodzina":
        s.akapit("Sąsiedzi z piętra wyżej to {P} {F}, od lat zamieszkali w tym samym budynku; głową rodziny jest {m2}.",
                 P=_PANSTWO["mian"], F=rodz("mian", m2, f2), m2=m2.pelne)
    porzadek = list(_PRZYP_AKT)
    rng.shuffle(porzadek)
    for przyp in porzadek[:3]:                    # rodzina 2: trzy wylosowane przypadki
        rama(przyp, m2, f2)
    for plec_os, os_ in (("M", m1), ("K", k1)):   # przypadki zależne osób występujących imiennie
        for przyp in rng.sample(sorted(_RAMKI_POJEDYNCZE[plec_os]), 2):
            s.akapit(rng.choice(_RAMKI_POJEDYNCZE[plec_os][przyp]), X=poj(przyp, os_))
    s.akapit("Kancelaria nie otrzymała dotąd odpowiedzi od drugiej strony.")
    return s.wynik(typ, ctx), gen, {}


# ============================================================================= 2. nazwiska_zwykle_slowa
#: Nazwisko -> zdania ze słowem pospolitym (`{w}` = forma słowa w zdaniu, bez cyfr i nazw własnych).
_SLOWA: dict[str, dict[str, tuple[str, ...]]] = {
    "pl": {"Kowal": ("{w} wykonał na zamówienie bramę wjazdową według przesłanego rysunku.",
                     "W sąsiedniej wsi mieszka {w}, który naprawia ogrodzenia."),
           "Mróz": ("Silny {w} w styczniu uszkodził instalację wodną w piwnicy.",
                    "{w} trwał całe dwa tygodnie i zamarzły rury."),
           "Wilk": ("W nocy {w} zaatakował owce w zagrodzie sąsiada.",),
           "Baran": ("Na pastwisku pasł się {w}, który uciekł z gospodarstwa.",),
           "Zając": ("Przez pole przebiegł {w} i spłoszył konie.",),
           "Sowa": ("W starym budynku gnieździ się {w}, co utrudnia prace rozbiórkowe.",),
           "Lis": ("Z kurnika zniknęły trzy kury, prawdopodobnie zabrał je {w}.",),
           "Kruk": ("Nad dachem krążył {w} i zrzucił gałąź na rynnę.",)},
    "en": {"Baker": ("The {w} delivered the order two hours late, so the party started without the cake.",),
           "Smith": ("The {w} forged the new gate by hand over the course of a week.",),
           "Cook": ("The {w} had left the kitchen unlocked after the evening shift.",),
           "Fox": ("A {w} got into the henhouse during the night and killed several birds.",),
           "Wood": ("The {w} stored in the cellar was damaged by the damp.",),
           "Hunter": ("A local {w} had been using the field without permission.",),
           "Mason": ("The {w} repaired the garden wall before the winter.",),
           "Bird": ("A {w} built a nest in the chimney and blocked the flue.",)},
    "de": {"Müller": ("Der {w} hat das Mehl erst am nächsten Morgen geliefert.",),
           "Fischer": ("Ein {w} hat sein Netz im Teich des Nachbarn ausgeworfen.",),
           "Koch": ("Der {w} hatte die Küche nach der Abendschicht nicht abgeschlossen.",),
           "Wolf": ("In der Nacht hat ein {w} Schafe auf der Weide gerissen.",),
           "Fuchs": ("Ein {w} ist durch den Zaun in den Hühnerstall eingedrungen.",),
           "Vogel": ("Ein {w} hat im Schornstein genistet und den Abzug verstopft.",),
           "Bauer": ("Der {w} hat das Feld ohne Erlaubnis des Eigentümers befahren.",),
           "Schneider": ("Der {w} hat die Vorhänge zu kurz genäht.",)},
    "es": {"Herrero": ("El {w} forjó la reja de la entrada a mano en una semana.",),
           "Molinero": ("El {w} entregó la harina con dos días de retraso.",),
           "Zapatero": ("El {w} arregló el calzado antes de que cerrara el taller.",),
           "Pastor": ("Un {w} llevó el rebaño por la finca sin permiso del propietario.",),
           "Lobo": ("Un {w} atacó las ovejas durante la noche en el prado vecino.",),
           "Zorro": ("Un {w} entró en el gallinero y mató a varias aves.",),
           "Gallo": ("El {w} del vecino canta cada madrugada y molesta a los inquilinos.",),
           "Panadero": ("El {w} entregó el pedido con dos horas de retraso.",)},
    "fr": {"Boulanger": ("Le {w} a livré la commande avec deux heures de retard.",),
           "Meunier": ("Le {w} a livré la farine avec deux jours de retard.",),
           "Renard": ("Un {w} est entré dans le poulailler pendant la nuit.",),
           "Loup": ("Un {w} a attaqué les moutons dans le pré voisin.",),
           "Berger": ("Le {w} a conduit son troupeau sur le terrain sans autorisation.",),
           "Boucher": ("Le {w} a livré la viande après la fermeture de la cuisine.",),
           "Chevalier": ("Un {w} figure sur le blason sculpté au-dessus du portail.",),
           "Marchand": ("Le {w} a installé son étal devant la porte de l'immeuble.",)},
}
_TRESC_ZWYKLE: dict[str, dict[str, str]] = {
    "pl": {"naglowek": "Notatka dotycząca zgłoszenia szkody",
           "p1": "W dniu {d} {pan} {pelne} zgłosił szkodę w nieruchomości przy {adres}.",
           "p3": "Zgłaszający, PESEL {id}, wniósł o oględziny nieruchomości w ciągu siedmiu dni.",
           "p5": "{pan} {nazwisko} dołączył do zgłoszenia dokumentację zdjęciową.",
           "p6": "{pan} {nazwisko} otrzymał od ubezpieczyciela potwierdzenie przyjęcia zgłoszenia.", "pan": "Pan"},
    "en": {"naglowek": "Note on the damage report",
           "p1": "On {d} {pan} {pelne} reported damage to the property at {adres}.",
           "p3": "The claimant, National Insurance number {id}, asked for an inspection within seven days.",
           "p5": "{pan} {nazwisko} attached photographic documentation to the report.",
           "p6": "{pan} {nazwisko} received confirmation from the insurer that the report had been accepted.", "pan": "Mr"},
    "de": {"naglowek": "Vermerk zur Schadensmeldung",
           "p1": "Am {d} meldete {pan} {pelne} einen Schaden am Grundstück {adres}.",
           "p3": "Der Melder, Steuer-Identifikationsnummer {id}, beantragte eine Besichtigung innerhalb von sieben Tagen.",
           "p5": "{pan} {nazwisko} fügte der Meldung eine Fotodokumentation bei.",
           "p6": "{pan} {nazwisko} erhielt vom Versicherer die Bestätigung, dass die Meldung eingegangen ist.", "pan": "Herr"},
    "es": {"naglowek": "Nota sobre la comunicación del siniestro",
           "p1": "El {d} {pan} {pelne} comunicó un siniestro en el inmueble situado en {adres}.",
           "p3": "El declarante, con DNI {id}, solicitó una inspección del inmueble en el plazo de siete días.",
           "p5": "{pan} {nazwisko} adjuntó a la comunicación la documentación fotográfica.",
           "p6": "{pan} {nazwisko} recibió de la aseguradora la confirmación de recepción de la comunicación.", "pan": "D."},
    "fr": {"naglowek": "Note relative à la déclaration de sinistre",
           "p1": "Le {d}, {pan} {pelne} a déclaré un sinistre dans l'immeuble situé {adres}.",
           "p3": "Le déclarant, numéro de sécurité sociale {id}, a demandé une expertise dans un délai de sept jours.",
           "p5": "{pan} {nazwisko} a joint à la déclaration un dossier photographique.",
           "p6": "{pan} {nazwisko} a reçu de l'assureur la confirmation de réception de la déclaration.", "pan": "M."},
}


def _buduj_zwykle(jezyk: str, typ: str, seed: int) -> tuple:
    gen, ctx = nowy_kontekst(jezyk, seed)
    rng = rng_h2(seed, "zwykle")
    nazwisko = rng.choice(sorted(_SLOWA[jezyk]))
    bazowa = osoba(gen, ctx, "M", _bez_blokady)
    for _ in range(100):
        o = zmien(bazowa, nazwisko=nazwisko)
        if _bez_blokady(o):
            break
        bazowa = osoba(gen, ctx, "M", _bez_blokady)
    os_ = Os("os", o, jezyk)
    t = _TRESC_ZWYKLE[jezyk]
    de = jezyk == "de"
    s = Skladacz(jezyk)
    pan = t["pan"]
    s.naglowek(t["naglowek"])
    s.akapit(t["p1"], d=data_gold(ctx, "dok"), pan=pan, pelne=os_.pelne, adres=os_.adres)

    forma = nazwisko if de else nazwisko.lower()      # niemieckie rzeczowniki piszemy wielką literą (identycznie z nazwiskiem)
    for z in _SLOWA[jezyk][nazwisko]:
        poczatek = z.startswith("{w}")
        w = Pulapka(forma if not poczatek else forma[0].upper() + forma[1:], os_.rola)
        s.akapit(z, w=w)
    s.akapit(t["p3"], id=os_.id)
    s.akapit(t["p5"], pan=pan, nazwisko=os_.nazwisko)
    s.akapit(t["p6"], pan=pan, nazwisko=os_.nazwisko)
    return s.wynik(typ, ctx), gen, {"pulapki": s.pulapki}


# ============================================================================= 3. zdrobnienia
#: (pełne imię, płeć, zdrobnienia faktycznie używane w danym języku)
ZDROBNIENIA_IMION: dict[str, list[tuple[str, str, tuple[str, ...]]]] = {
    "pl": [("Katarzyna", "K", ("Kasia",)), ("Tomasz", "M", ("Tomek",)), ("Barbara", "K", ("Basia",)),
           ("Małgorzata", "K", ("Gosia", "Małgosia")), ("Krzysztof", "M", ("Krzysiek",)), ("Joanna", "K", ("Asia",)),
           ("Elżbieta", "K", ("Ela",)), ("Zofia", "K", ("Zosia",)), ("Aleksandra", "K", ("Ola",)),
           ("Piotr", "M", ("Piotrek",)), ("Jakub", "M", ("Kuba",)), ("Stanisław", "M", ("Staszek",))],
    "en": [("William", "M", ("Bill", "Will")), ("Robert", "M", ("Bob", "Rob")), ("Katherine", "K", ("Kate", "Kathy")),
           ("Elizabeth", "K", ("Liz", "Beth")), ("James", "M", ("Jim",)), ("Margaret", "K", ("Maggie",)),
           ("Michael", "M", ("Mike",)), ("Richard", "M", ("Rick",)), ("Jennifer", "K", ("Jen",)),
           ("Christopher", "M", ("Chris",)), ("Susan", "K", ("Sue",))],
    "de": [("Johannes", "M", ("Hannes",)), ("Hans", "M", ("Hansi",)), ("Andreas", "M", ("Andi",)),
           ("Susanne", "K", ("Susi",)), ("Katharina", "K", ("Kati",)), ("Matthias", "M", ("Matze",)),
           ("Stephanie", "K", ("Steffi",)), ("Bettina", "K", ("Betti",)), ("Michael", "M", ("Michi",))],
    "es": [("José", "M", ("Pepe",)), ("Francisco", "M", ("Paco",)), ("Dolores", "K", ("Lola",)),
           ("Ignacio", "M", ("Nacho",)), ("Manuel", "M", ("Manolo",)), ("Concepción", "K", ("Concha",)),
           ("Rosario", "K", ("Charo",)), ("Francisca", "K", ("Paca",)), ("Mercedes", "K", ("Merche",))],
    "fr": [("Emmanuel", "M", ("Manu",)), ("Sébastien", "M", ("Seb",)), ("Frédéric", "M", ("Fred",)),
           ("Nicolas", "M", ("Nico",)), ("Stéphanie", "K", ("Steph",)), ("Dominique", "K", ("Domi",)),
           ("Jean-Michel", "M", ("Jean-Mi",)), ("Véronique", "K", ("Véro",)), ("Isabelle", "K", ("Isa",))],
}
_TRESC_ZDROBNIENIA: dict[str, dict[str, str]] = {
    "pl": {"n": "Notatka z rozmowy telefonicznej",
           "p1": "Rozmowa telefoniczna z dnia {d}: rozmówczyni – {pelne1}, tel. {tel1}, adres korespondencyjny: {adr1}. "
                 "W rozmowie uczestniczył także {pelne2}.",
           "p2": "W trakcie rozmowy {dp1} {czas1} o przesłanie kopii umowy najmu.",
           "p3": "{dim2} {czas2}, że dokumenty zostaną dostarczone do końca tygodnia.",
           "p4": "{pani} {dim1} zgodziła się na termin spotkania w kancelarii.",
           "p5": "Uzgodniono, że {dim1} oraz {dim2} stawią się w kancelarii dnia {d2}.",
           "p6": "{dp2} dodał, że w razie zmiany terminu skontaktuje się z kancelarią.",
           "czas": {"M": ("poprosił", "zapewnił"), "K": ("poprosiła", "zapewniła")}, "pani": "Pani"},
    "en": {"n": "Note of telephone call",
           "p1": "Telephone call of {d}: caller – {pelne1}, tel. {tel1}, correspondence address: {adr1}. "
                 "{pelne2} also took part in the call.",
           "p2": "During the call {dp1} asked for a copy of the tenancy agreement to be sent.",
           "p3": "{dim2} assured us that the documents would be delivered by the end of the week.",
           "p4": "{dim1} agreed to the date of the meeting at the office.",
           "p5": "It was agreed that {dim1} and {dim2} would attend the office on {d2}.",
           "p6": "{dp2} added that he would contact the office if the date changed."},
    "de": {"n": "Vermerk über ein Telefongespräch",
           "p1": "Telefongespräch vom {d}: Anruferin – {pelne1}, Tel. {tel1}, Korrespondenzanschrift: {adr1}. "
                 "An dem Gespräch nahm auch {pelne2} teil.",
           "p2": "Im Verlauf des Gesprächs bat {dp1} um die Übersendung einer Kopie des Mietvertrags.",
           "p3": "{dim2} versicherte, dass die Unterlagen bis zum Ende der Woche zugestellt würden.",
           "p4": "{dim1} stimmte dem Termin in der Kanzlei zu.",
           "p5": "Vereinbart wurde, dass {dim1} und {dim2} am {d2} in der Kanzlei erscheinen.",
           "p6": "{dp2} fügte hinzu, dass er sich bei einer Terminänderung bei der Kanzlei melden werde."},
    "es": {"n": "Nota de conversación telefónica",
           "p1": "Conversación telefónica del {d}: interlocutora – {pelne1}, tel. {tel1}, dirección de correspondencia: {adr1}. "
                 "También participó en la llamada {pelne2}.",
           "p2": "Durante la llamada {dp1} pidió que se le enviara una copia del contrato de alquiler.",
           "p3": "{dim2} aseguró que los documentos se entregarían antes del fin de semana.",
           "p4": "{pani} {dim1} aceptó la fecha de la reunión en el despacho.",
           "p5": "Se acordó que {dim1} y {dim2} acudirían al despacho el {d2}.",
           "p6": "{dp2} añadió que se pondría en contacto con el despacho si cambiaba la fecha.", "pani": "La señora"},
    "fr": {"n": "Note d'entretien téléphonique",
           "p1": "Entretien téléphonique du {d} : interlocutrice – {pelne1}, tél. {tel1}, adresse de correspondance : {adr1}. "
                 "{pelne2} a également participé à l'appel.",
           "p2": "Au cours de l'entretien, {dp1} a demandé l'envoi d'une copie du bail.",
           "p3": "{dim2} a assuré que les documents seraient remis avant la fin de la semaine.",
           "p4": "{dim1} a accepté la date du rendez-vous au cabinet.",
           "p5": "Il a été convenu que {dim1} et {dim2} se présenteraient au cabinet le {d2}.",
           "p6": "{dp2} a ajouté qu'il préviendrait le cabinet en cas de changement de date."},
}


def _buduj_zdrobnienia(jezyk: str, typ: str, seed: int) -> tuple:
    gen, ctx = nowy_kontekst(jezyk, seed)
    rng = rng_h2(seed, "zdrobnienia")
    # pierwsza osoba kobieta (zwrot „Pani …”), druga – mężczyzna, jeśli pula pozwala
    kobiety = [w for w in ZDROBNIENIA_IMION[jezyk] if w[1] == "K"]
    mezczyzni = [w for w in ZDROBNIENIA_IMION[jezyk] if w[1] == "M"]
    w1, w2 = rng.choice(kobiety), rng.choice(mezczyzni)
    osoby = []
    for pelne_imie, plec, dims in (w1, w2):
        o = osoba(gen, ctx, plec, _bez_blokady)
        osoby.append((zmien(o, imie=pelne_imie), rng.choice(dims)))
    (o1, d1), (o2, d2) = osoby
    p1, p2 = Os("p1", o1, jezyk), Os("p2", o2, jezyk)
    t = _TRESC_ZDROBNIENIA[jezyk]

    def dim(os_: Os, zdrob: str, z_nazwiskiem: bool) -> G:
        tekst = f"{zdrob} {os_.o.nazwisko}" if z_nazwiskiem else zdrob
        return os_.g("pelne" if z_nazwiskiem else "imie", tekst, cechy=("zdrobnienie",))

    czas1, czas2 = "poprosiła", "zapewnił"         # tylko PL (inne języki nie mają gniazd {czas…})
    s = Skladacz(jezyk)
    s.naglowek(t["n"])
    s.akapit(t["p1"], d=data_gold(ctx, "dok"), pelne1=p1.pelne, tel1=p1.telefon, adr1=p1.adres, pelne2=p2.pelne)
    s.akapit(t["p2"], dp1=dim(p1, d1, True), czas1=czas1)
    s.akapit(t["p3"], dim2=dim(p2, d2, False), czas2=czas2)
    # forma grzecznościowa tylko przy zdrobnieniu naturalnym z nią (PL „Pani Kasia”, ES „La señora Merche”)
    s.akapit(t["p4"], dim1=dim(p1, d1, False), **({"pani": t["pani"]} if "{pani}" in t["p4"] else {}))
    s.akapit(t["p5"], dim1=dim(p1, d1, False), dim2=dim(p2, d2, False), d2=data_gold(ctx, "dok_termin"))
    s.akapit(t["p6"], dp2=dim(p2, d2, True))
    return s.wynik(typ, ctx), gen, {}


# ============================================================================= 4. nazwisko_imie
#: Funkcje w wykazie jako pary (forma męska, forma żeńska) – wybór wg płci osoby.
_ROLE_TABELI: dict[str, tuple[tuple[str, str], ...]] = {
    "pl": (("członek zarządu", "członkini zarządu"), ("prokurent", "prokurent"), ("pełnomocnik", "pełnomocniczka"),
           ("doradca", "doradczyni"), ("księgowy", "księgowa"), ("kierownik projektu", "kierowniczka projektu")),
    "en": tuple((x, x) for x in ("director", "attorney", "adviser", "accountant", "project manager", "secretary")),
    "de": (("Geschäftsführer", "Geschäftsführerin"), ("Prokurist", "Prokuristin"), ("Bevollmächtigter", "Bevollmächtigte"),
           ("Berater", "Beraterin"), ("Buchhalter", "Buchhalterin"), ("Projektleiter", "Projektleiterin")),
    "es": (("administrador", "administradora"), ("apoderado", "apoderada"), ("asesor", "asesora"), ("contable", "contable"),
           ("director de proyecto", "directora de proyecto"), ("secretario", "secretaria")),
    "fr": (("gérant", "gérante"), ("fondé de pouvoir", "fondée de pouvoir"), ("mandataire", "mandataire"),
           ("conseiller", "conseillère"), ("comptable", "comptable"), ("chef de projet", "cheffe de projet")),
}
_TRESC_LISTA: dict[str, dict[str, object]] = {
    "pl": {"n": "Wykaz osób uprawnionych do kontaktu", "podmiot": "Podmiot", "intro": "Wykaz sporządzono w dniu {d}. "
           "Osoby wymienione poniżej są uprawnione do odbioru korespondencji.",
           "kol": ("Lp.", "Nazwisko i imię", "PESEL", "Funkcja"), "koniec": "Wykaz zatwierdził {pelne}."},
    "en": {"n": "List of authorised contact persons", "podmiot": "Entity", "intro": "This list was prepared on {d}. "
           "The persons named below are authorised to receive correspondence.",
           "kol": ("No.", "Surname, first name", "National Insurance no.", "Position"), "koniec": "The list was approved by {pelne}."},
    "de": {"n": "Verzeichnis der empfangsberechtigten Personen", "podmiot": "Unternehmen", "intro": "Dieses Verzeichnis wurde am {d} erstellt. "
           "Die nachstehend genannten Personen sind zum Empfang von Korrespondenz berechtigt.",
           "kol": ("Nr.", "Nachname, Vorname", "Steuer-ID", "Funktion"), "koniec": "Das Verzeichnis wurde von {pelne} genehmigt."},
    "es": {"n": "Relación de personas autorizadas", "podmiot": "Entidad", "intro": "La presente relación se elaboró el {d}. "
           "Las personas indicadas a continuación están autorizadas para recibir la correspondencia.",
           "kol": ("N.º", "Apellidos, nombre", "DNI", "Cargo"), "koniec": "La relación fue aprobada por {pelne}."},
    "fr": {"n": "Liste des personnes habilitées", "podmiot": "Entité", "intro": "La présente liste a été établie le {d}. "
           "Les personnes mentionnées ci-dessous sont habilitées à recevoir la correspondance.",
           "kol": ("N°", "Nom et prénom", "Numéro de sécurité sociale", "Fonction"), "koniec": "La liste a été approuvée par {pelne}."},
}


def zapis_nazwisko_imie(o: Osoba, jezyk: str, wielkie: bool) -> str:
    """„KOWALSKI Jan” / „Nowak Anna” (PL, FR) albo „SMITH, John” / „Müller, Hans” (EN, DE, ES)."""
    nazw = o.nazwisko.upper() if wielkie else o.nazwisko
    return f"{nazw} {o.imie}" if jezyk in ("pl", "fr") else f"{nazw}, {o.imie}"


def _buduj_wykaz(jezyk: str, typ: str, seed: int) -> tuple:
    gen, ctx = nowy_kontekst(jezyk, seed)
    rng = rng_h2(seed, "wykaz")
    t = _TRESC_LISTA[jezyk]
    firma = gen.firma()
    n = rng.randint(8, 14)
    osoby = [Os(f"w{i + 1}", osoba(gen, ctx, None, _bez_blokady), jezyk) for i in range(n)]
    s = Skladacz(jezyk)
    s.naglowek(t["n"])
    s.akapit(t["podmiot"] + ": {firma}", firma=G(firma.nazwa, "ORGANIZACJA", "firma.nazwa", "firma"))
    s.akapit(t["intro"], d=data_gold(ctx, "dok"))
    for j, kol in enumerate(t["kol"]):
        s.komorka(0, 0, j, kol)
    for i, os_ in enumerate(osoby, 1):
        wielkie = rng.random() < 0.6
        nazwa = G(zapis_nazwisko_imie(os_.o, jezyk, wielkie), "OSOBA", f"{os_.rola}.nazwisko_imie", os_.rola,
                  ("nazwisko_imie", "wielkie_litery") if wielkie else ("nazwisko_imie",))
        s.komorka(0, i, 0, str(i))
        s.komorka(0, i, 1, "{n}", n=nazwa)
        if rng.random() < 0.5:
            s.komorka(0, i, 2, "{id}", id=os_.id)
        else:
            s.komorka(0, i, 2, "–")
        s.komorka(0, i, 3, rng.choice(_ROLE_TABELI[jezyk])[0 if os_.o.plec == "M" else 1])   # feminatyw wg płci
    zatwierdza = rng.choice(osoby)        # ta sama osoba w zapisie zwykłym („Imię Nazwisko”) – wspólna encja
    s.akapit(t["koniec"], pelne=zatwierdza.pelne)
    return s.wynik(typ, ctx), gen, {}


# ============================================================================= 5. parafy
_TRESC_PARAFY: dict[str, dict[str, str]] = {
    "pl": {"adresat": "Do: {adresat}", "dotyczy": "Dotyczy: wezwania do zapłaty należności z tytułu faktury.",
           "p1": "W nawiązaniu do rozmowy z {b_narz} uprzejmie przypominamy o upływie terminu płatności wskazanego w fakturze.",
           "p2": "Prosimy o uregulowanie należności w terminie siedmiu dni od otrzymania pisma, pod rygorem skierowania sprawy na drogę sądową.",
           "pozdrowienie": "Z poważaniem,", "stanowisko": ("radca prawny", "radca prawny"), "oznaczenie": "Oznaczenie pisma: {jk}/{ak}",
           "marginesy": ("Parafa: {ab}", "/{ab}/"), "stopka": "Opracowanie: {a_k}; zatwierdzenie: {b_k}"},
    "en": {"adresat": "To: {adresat}", "dotyczy": "Re: reminder of payment due under the invoice.",
           "p1": "Further to the conversation with {b}, we kindly remind you that the payment date stated in the invoice has passed.",
           "p2": "Please settle the amount within seven days of receipt of this letter, failing which the matter will be referred to court.",
           "pozdrowienie": "Yours sincerely,", "stanowisko": ("solicitor", "solicitor"), "oznaczenie": "Our ref: {jk}/{ak}",
           "marginesy": ("Initialled: {ab}", "/{ab}/"), "stopka": "Prepared by: {a_k}; approved by: {b_k}"},
    "de": {"adresat": "An: {adresat}", "dotyczy": "Betreff: Zahlungsaufforderung aus der Rechnung.",
           "p1": "Im Nachgang zum Gespräch mit {b} erinnern wir Sie freundlich daran, dass die in der Rechnung genannte Zahlungsfrist abgelaufen ist.",
           "p2": "Bitte begleichen Sie den Betrag innerhalb von sieben Tagen nach Erhalt dieses Schreibens, andernfalls werden wir die Angelegenheit gerichtlich weiterverfolgen.",
           "pozdrowienie": "Mit freundlichen Grüßen", "stanowisko": ("Rechtsanwalt", "Rechtsanwältin"), "oznaczenie": "Unser Zeichen: {jk}/{ak}",
           "marginesy": ("Handzeichen: {ab}", "/{ab}/"), "stopka": "Bearbeitet von: {a_k}; genehmigt von: {b_k}"},
    "es": {"adresat": "A: {adresat}", "dotyczy": "Asunto: requerimiento de pago de la factura.",
           "p1": "En relación con la conversación mantenida con {b}, le recordamos amablemente que ha vencido el plazo de pago indicado en la factura.",
           "p2": "Le rogamos que abone el importe en el plazo de siete días desde la recepción de esta carta; de lo contrario, se acudirá a la vía judicial.",
           "pozdrowienie": "Atentamente,", "stanowisko": ("abogado", "abogada"), "oznaczenie": "Referencia: {jk}/{ak}",
           "marginesy": ("Rúbrica: {ab}", "/{ab}/"), "stopka": "Elaborado por: {a_k}; aprobado por: {b_k}"},
    "fr": {"adresat": "À : {adresat}", "dotyczy": "Objet : mise en demeure de payer la facture.",
           "p1": "Suite à l'entretien avec {b}, nous vous rappelons que le délai de paiement indiqué sur la facture est expiré.",
           "p2": "Nous vous prions de régler la somme dans un délai de sept jours à compter de la réception de la présente, faute de quoi l'affaire sera portée devant le tribunal.",
           "pozdrowienie": "Veuillez agréer nos salutations distinguées,", "stanowisko": ("avocat", "avocate"), "oznaczenie": "Référence : {jk}/{ak}",
           "marginesy": ("Paraphe : {ab}", "/{ab}/"), "stopka": "Rédigé par : {a_k} ; approuvé par : {b_k}"},
}


def _buduj_parafy(jezyk: str, typ: str, seed: int) -> tuple:
    gen, ctx = nowy_kontekst(jezyk, seed)
    rng = rng_h2(seed, "parafy")
    t = _TRESC_PARAFY[jezyk]
    a, b, c = (Os(r, osoba(gen, ctx, None, _bez_blokady), jezyk) for r in ("a", "b", "c"))
    nadawca, adresat = gen.firma(rodzaj="kancelaria"), gen.firma()

    def ini(os_: Os, kropki: bool = False, male: bool = False, pole: str = "inicjaly") -> G:
        return os_.g(pole, inicjaly(os_.o, kropki, male), "INICJALY", ("parafa",))

    s = Skladacz(jezyk)
    s.naglowek("{firma}", firma=G(nadawca.nazwa, "ORGANIZACJA", "nadawca.nazwa", "nadawca"))
    s.akapit(t["adresat"], adresat=G(adresat.nazwa, "ORGANIZACJA", "adresat.nazwa", "adresat"))
    s.akapit(t["dotyczy"])
    s.akapit(t["p1"], b=b.pelne, b_narz=(b.g("pelne", odmien(b.o.imie, b.o.nazwisko, b.o.plec, "narz"),
                                                cechy=("przypadek_zalezny",)) if jezyk == "pl" else b.pelne))
    s.akapit(t["p2"])
    s.akapit(t["pozdrowienie"])
    s.akapit("{a}", a=a.pelne)
    s.akapit(t["stanowisko"][0 if a.o.plec == "M" else 1])
    s.akapit(t["oznaczenie"], jk=ini(a, male=True, pole="inicjaly_male"), ak=ini(c, male=True, pole="inicjaly_male"))
    for m in t["marginesy"]:
        s.akapit(m, ab=ini(b))
    s.stopka(t["stopka"], a_k=ini(a, kropki=True, pole="inicjaly_kropki"), b_k=ini(b, kropki=True, pole="inicjaly_kropki"))
    return s.wynik(typ, ctx), gen, {}


# ============================================================================= 6. liczby_slownie
_TRESC_POZYCZKA: dict[str, dict[str, str]] = {
    "pl": {"n": "UMOWA POŻYCZKI",
           "p1": "Zawarta w dniu {d} ({ds}) pomiędzy {pozyczkodawca}, {zam1} przy {adr1}, {zw1} dalej {pd_n}, "
                 "a {pozyczkobiorca}, PESEL {pesel} (słownie: {pesel_s}), {zw2} dalej {pb_n}.",
           "p2": "{pb_m} oświadcza, że {ur_v} w dniu {ur} ({ur_s}) i zamieszkuje przy {adr2}.",
           "p3": "{pd_m} udziela {pb_d} pożyczki w kwocie {k} (słownie: {k_s}).",
           "p4": "{pb_m} zobowiązuje się zwrócić pożyczkę w terminie do dnia {t} ({t_s}).",
           "p5": "Za korzystanie z kapitału strony ustalają odsetki w łącznej wysokości {o} (słownie: {o_s}).",
           "p6": "Wypłata pożyczki nastąpi na rachunek {pb_d} {rach}."},
    "en": {"n": "LOAN AGREEMENT",
           "p1": "Made on {d} ({ds}) between {pozyczkodawca}, residing at {adr1}, hereinafter the Lender, "
                 "and {pozyczkobiorca}, hereinafter the Borrower.",
           "p2": "The Borrower declares that {on_ona} was born on {ur} ({ur_s}) and resides at {adr2}.",
           "p3": "The Lender grants the Borrower a loan in the amount of {k} (in words: {k_s}).",
           "p4": "The Borrower undertakes to repay the loan by {t} ({t_s}).",
           "p5": "For the use of the capital the parties agree interest in the total amount of {o} (in words: {o_s}).",
           "p6": "The loan will be paid out to the Borrower's account {rach}."},
    "de": {"n": "DARLEHENSVERTRAG",
           "p1": "Geschlossen am {d} ({ds}) zwischen {pozyczkodawca}, wohnhaft {adr1}, nachstehend Darlehensgeber, "
                 "und {pozyczkobiorca}, nachstehend Darlehensnehmer.",
           "p2": "Der Darlehensnehmer erklärt, dass er am {ur} ({ur_s}) geboren wurde; seine Anschrift lautet {adr2}.",
           "p3": "Der Darlehensgeber gewährt dem Darlehensnehmer ein Darlehen in Höhe von {k} (in Worten: {k_s}).",
           "p4": "Der Darlehensnehmer verpflichtet sich, das Darlehen bis zum {t} ({t_s}) zurückzuzahlen.",
           "p5": "Für die Überlassung des Kapitals vereinbaren die Parteien Zinsen in Höhe von insgesamt {o} (in Worten: {o_s}).",
           "p6": "Das Darlehen wird auf das Konto des Darlehensnehmers {rach} ausgezahlt."},
    "es": {"n": "CONTRATO DE PRÉSTAMO",
           "p1": "Celebrado el {d} ({ds}) entre {pozyczkodawca}, con domicilio en {adr1}, en adelante el Prestamista, "
                 "y {pozyczkobiorca}, en adelante el Prestatario.",
           "p2": "El Prestatario declara que nació el {ur} ({ur_s}) y que reside en {adr2}.",
           "p3": "El Prestamista concede al Prestatario un préstamo por importe de {k} (en letra: {k_s}).",
           "p4": "El Prestatario se obliga a devolver el préstamo antes del {t} ({t_s}).",
           "p5": "Por el uso del capital las partes pactan unos intereses por importe total de {o} (en letra: {o_s}).",
           "p6": "El préstamo se abonará en la cuenta del Prestatario {rach}."},
    "fr": {"n": "CONTRAT DE PRÊT",
           "p1": "Conclu le {d} ({ds}) entre {pozyczkodawca}, domicilié {adr1}, ci-après le Prêteur, "
                 "et {pozyczkobiorca}, ci-après l'Emprunteur.",
           "p2": "L'Emprunteur déclare être né le {ur} ({ur_s}) et demeurer {adr2}.",
           "p3": "Le Prêteur consent à l'Emprunteur un prêt d'un montant de {k} (en toutes lettres : {k_s}).",
           "p4": "L'Emprunteur s'engage à rembourser le prêt avant le {t} ({t_s}).",
           "p5": "Pour l'usage du capital, les parties conviennent d'intérêts d'un montant total de {o} (en toutes lettres : {o_s}).",
           "p6": "Le prêt sera versé sur le compte de l'Emprunteur {rach}."},
}


def _buduj_pozyczka(jezyk: str, typ: str, seed: int) -> tuple:
    gen, ctx = nowy_kontekst(jezyk, seed)
    rng = rng_h2(seed, "pozyczka")
    t = _TRESC_POZYCZKA[jezyk]
    pd, pb = Os("pd", osoba(gen, ctx), jezyk), Os("pb", osoba(gen, ctx), jezyk)
    kwota_gr = rng.randint(30, 600) * 50_000 + rng.choice((0, 0, 0, 5_000, 25_000))
    odsetki_gr = rng.randint(4, 40) * 10_000 + rng.choice((0, 0, 5_000))
    waluta = "GBP" if jezyk == "en" else None

    def liczby(gr: int, klucz: str) -> tuple[G, G]:
        cyfry = gen._kwota_txt(gr // 100, gr % 100, gen.kraj_dok or gen.kraje[0])
        return (G(cyfry, "KWOTA", f"ctx.{klucz}", cechy=("cyframi",)),
                G(kwota_slownie(gr, jezyk, waluta), "KWOTA", f"ctx.{klucz}_slownie", cechy=("slownie",)))

    def daty(nazwa: str, kat: str = "DATA") -> tuple[G, G]:
        d = ctx.daty[nazwa]
        return (G(gen.formatuj_date(d), kat, f"ctx.{nazwa}", cechy=("cyframi",)),
                G(data_slownie(d, jezyk), kat, f"ctx.{nazwa}_slownie", cechy=("slownie",)))

    d, ds = daty("dok")
    tt, t_s = daty("dok_termin_dl")
    ur_d = pb.o.data_ur
    ur = G(gen.formatuj_date(ur_d), "DATA_UR", "pb.data_ur", "pb", ("cyframi",))
    ur_s = G(data_slownie(ur_d, jezyk), "DATA_UR", "pb.data_ur_slownie", "pb", ("slownie",))
    k, k_s = liczby(kwota_gr, "kwota")
    o, o_s = liczby(odsetki_gr, "odsetki")
    sloty: dict[str, object] = dict(d=d, ds=ds, pozyczkodawca=pd.pelne, adr1=pd.adres, pozyczkobiorca=pb.pelne,
                                    adr2=pb.adres, ur=ur, ur_s=ur_s, k=k, k_s=k_s, t=tt, t_s=t_s, o=o, o_s=o_s,
                                    rach=pb.rachunek, on_ona="she" if pb.o.plec == "K" else "he")
    if jezyk == "pl":      # „pomiędzy Krzysztofem Jakubowskim … a Barbarą Ozimek” (narzędnik), czasowniki wg płci
        def narz(os_: Os) -> G:
            return os_.g("pelne", odmien(os_.o.imie, os_.o.nazwisko, os_.o.plec, "narz"), cechy=("przypadek_zalezny",))
        k1, k2 = pd.o.plec == "K", pb.o.plec == "K"
        sloty |= {"pozyczkodawca": narz(pd), "pozyczkobiorca": narz(pb), "zam1": "zamieszkałą" if k1 else "zamieszkałym",
                  "zw1": "zwaną" if k1 else "zwanym", "zw2": "zwaną" if k2 else "zwanym",
                  "ur_v": "urodziła się" if k2 else "urodził się"}
        # role umowy wg płci osoby: Pożyczkodawca/-czyni, Pożyczkobiorca/-czyni (mian., dop./cel., narz.)
        sloty |= {"pd_m": "Pożyczkodawczyni" if k1 else "Pożyczkodawca", "pd_n": "Pożyczkodawczynią" if k1 else "Pożyczkodawcą",
                  "pb_m": "Pożyczkobiorczyni" if k2 else "Pożyczkobiorca", "pb_n": "Pożyczkobiorczynią" if k2 else "Pożyczkobiorcą",
                  "pb_d": "Pożyczkobiorczyni" if k2 else "Pożyczkobiorcy"}
        sloty |= {"pesel": pb.id, "pesel_s": pb.g("pesel_slownie", cyfry_slownie(pb.o.ids["PESEL"], "pl"), "PESEL",
                                                    ("slownie",))}
    s = Skladacz(jezyk)
    s.naglowek(t["n"])
    for klucz in ("p1", "p2", "p3", "p4", "p5", "p6"):
        s.akapit(t[klucz], **sloty)
    return s.wynik(typ, ctx), gen, {}


# ============================================================================= rejestr
#: przypadek -> {(język, typ): generator}; generator: (język, typ, ziarno dokumentu) -> (Wynik, generator, dodatki)
GENERATORY: dict[str, dict[tuple[str, str], Generator_H2]] = {
    "odmiana_nazwisk": {("pl", "notatka_rodzina"): _buduj_odmiana, ("pl", "protokol_spotkania"): _buduj_odmiana},
    "nazwiska_zwykle_slowa": {(j, "notatka_szkoda"): _buduj_zwykle for j in JEZYKI},
    "zdrobnienia": {(j, "notatka_rozmowy"): _buduj_zdrobnienia for j in JEZYKI},
    "nazwisko_imie": {(j, "wykaz_osob"): _buduj_wykaz for j in JEZYKI},
    "parafy": {(j, "pismo_z_parafami"): z_inicjalami_jednoznacznymi(_buduj_parafy) for j in JEZYKI},
    "liczby_slownie": {(j, "umowa_pozyczki"): _buduj_pozyczka for j in JEZYKI},
}
