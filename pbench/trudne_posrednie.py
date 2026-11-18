"""Identyfikacja pośrednia (spec §11 pkt 4, zadanie H5): przypadki `posrednie_funkcja_firma`, `posrednie_rzadka_choroba`,
`posrednie_wiek_miejscowosc`, `posrednie_dzialka_gps`.

Dokument opisuje osobę-cel, która NIE jest nazwana nigdzie w dokumencie (ani imieniem, ani nazwiskiem, ani inicjałami), ale
da się ją wskazać z połączenia kilku informacji – kombinacji. Inne osoby dokumentu (autor notatki, rozmówca, lekarz, świadek,
sąsiad) są nazwane i są zwykłym gold. Dokument składa kod (`pbench.skladacz`); składnik kombinacji wstawia gniazdo `Skladnik`:

* składnik będący kategorią gold trzonu (ORGANIZACJA, MIEJSCOWOSC, ADRES) jest zwykłą wartością gold, oznaczoną
  tak samo jak w trzonie (`wartosc_id` w strukturze kombinacji);
* składnik spoza kategorii (funkcja, wiek, rocznik, choroba – rozpoznania nie są gold, szkoła, numer działki, współrzędne GPS) jest zwykłym tekstem, NIE gold
  miary głównej (`wartosc_id` = null), i stoi wyłącznie w akapicie treści.

Każdy składnik ma rdzeń identyfikujący (`Skladnik.rdzen`, pole `rdzen`): liczbę wieku, rok, numer albo nazwę szkoły, numer
działki z obrębem, liczby współrzędnych, nazwę choroby bez słów rodzajowych (`rdzen_choroby`); funkcja, firma, miejscowość
i adres – cały tekst.

Kombinacje trafiają do pola manifestu `posrednie` (dodatek generatora `posrednie`; struktura i walidacja – `pbench.posrednie`).
Tekst każdego składnika występuje w dokumencie dokładnie raz (bez rozróżniania wielkości liter), tokeny składników nie
pokrywają się z imionami i nazwiskami osób nazwanych, a imię, nazwisko i inicjały osoby-celu (wylosowanej tylko po to, by
płeć, wiek i rocznik były spójne – dodatek `cele`) nie występują w tekście; gdy któryś warunek nie zachodzi, generator
losuje dokument od nowa (kolejna próba – inne ziarno).

* `posrednie_funkcja_firma` (`notatka_kontrahent`) – notatka kancelarii o dwóch kontrahentach klienta: dwie kombinacje
  „funkcja + firma” (Prezes Zarządu …, główna księgowa w spółce …, jedyny wspólnik …; Chief Financial Officer of …,
  Geschäftsführer der …, administrador único de …, gérant de …; forma prawna firmy zawsze dopuszczalna dla funkcji –
  tabela w `_FUNKCJE`) albo „kierownik budowy + adres inwestycji”;
* `posrednie_rzadka_choroba` – wniosek kadrowy (`wniosek_kadrowy`: choroba rzadka + pracodawca + miejscowość zakładu albo
  rocznik) i notatka zespołu szkolnego (`notatka_szkolna`: choroba ucznia + szkoła + miejscowość);
* `posrednie_wiek_miejscowosc` (`notatka_zdarzenie`) – notatka ze zdarzenia drogowego: wiek + mała miejscowość (wieś,
  village, Ortsteil, pedanía, hameau) z gminą/gminą-siedzibą (gmina – zwykłe gold MIEJSCOWOSC, poza kombinacją);
* `posrednie_dzialka_gps` (`protokol_ogledzin`) – protokół oględzin domu: oznaczenie działki ewidencyjnej (obręb, Flur/
  Flurstück, section cadastrale, polígono/parcela; EN – numer tytułu HM Land Registry) i współrzędne domu (punkt lądowy
  w kraju dokumentu, dziesiętne albo stopnie-minuty-sekundy) – DWIE osobne kombinacje jednoskładnikowe (każde samo wskazuje
  dom; żadne nie jest gold, więc uczestnik maskujący tylko kategorie ich nie przerywa); w połowie dokumentów nieruchomość
  wskazuje też zwykłe gold miary głównej – księga wieczysta (PL) albo adres.

Słowniki są w tym module: choroby rzadkie (wiedza ogólna – choroby z list chorób rzadkich typu Orphanet; eponimy nie
pokrywają się z nazwiskami osób dokumentu – sprawdzenie wyżej), małe miejscowości (własna kompilacja nazw – nazwy miejscowości
nie są danymi osobowymi; pary miejscowość–gmina są syntetyczne), funkcje i szkoły (bez nazw własnych osób). Nic
z danych treningowych modelu.
"""
from __future__ import annotations

import random
import re
from typing import Callable

from . import przypadki as P
from .dane.wspolne import Osoba
from .odmiana_pl import odmien
from .skladacz import G, Skladacz, Skladnik
from .trudne_wspolne import JEZYKI, Os, bez_blokady, data_gold, inicjaly, nowy_kontekst, osoba

#: Wynik generatora: (Wynik, generator, dodatki: `posrednie` – kombinacje, `cele` – osoby-cele, których nie wolno nazwać)
Generator_H5 = Callable[[str, str, int], tuple]
#: Liczba prób wylosowania dokumentu spełniającego warunki jednoznaczności (zob. docstring modułu).
PROBY = 60
_TOKEN = re.compile(r"\w+")


def rng_h5(seed: int, *czesci: object) -> random.Random:
    return random.Random(":".join(["pbench-h5", str(seed), *map(str, czesci)]))


def _rodzaj(plec: str, m: str, k: str) -> str:
    return m if plec == "M" else k


def kombinacje(s: Skladacz, rodzaj: str) -> list[dict]:
    """Kombinacje dokumentu z zapamiętanych składników (kolejność pierwszego wystąpienia): pole manifestu `posrednie` przed
    uzupełnieniem miejsc składników gold (`pbench.posrednie.do_manifestu`)."""
    wynik: dict[str, dict] = {}
    for x in s.skladniki:
        k = wynik.setdefault(x.kombinacja, {"id": x.kombinacja, "rodzaj": rodzaj, "skladniki": []})
        k["skladniki"].append({"id": f"{x.kombinacja}.{x.rola}", "rola": x.rola, "tekst": x.tekst, "miejsce": x.miejsce,
                               "wartosc_id": x.wartosc_id, "rdzen": list(x.rdzen)})
    return list(wynik.values())


def jednoznaczny(s: Skladacz, cele: list[Osoba]) -> bool:
    """Warunki dokumentu (docstring modułu): tekst składnika raz w dokumencie, tokeny składników rozłączne z imionami
    i nazwiskami osób nazwanych, osoba-cel nienazwana (żaden człon imienia i nazwiska od wielkiej litery jako słowo tekstu,
    inicjały „JK”, „J.K.”, „J. K.”)."""
    tekst = "\n".join("".join(f if isinstance(f, str) else f.tekst for f in e.fragmenty) for e in s.elementy)
    maly = tekst.casefold()
    if any(maly.count(x.tekst.casefold()) != 1 for x in s.skladniki):
        return False
    osoby = {t.casefold() for e in s.elementy for f in e.fragmenty if not isinstance(f, str) and f.kategoria == "OSOBA"
             for t in _TOKEN.findall(f.tekst) if len(t) >= 3}
    if any(t.casefold() in osoby for x in s.skladniki for t in _TOKEN.findall(x.tekst)):
        return False
    slowa = set(_TOKEN.findall(tekst))      # wielkość liter ma znaczenie: „Will” (imię) ≠ „will” (czasownik)
    for o in cele:
        if any(t in slowa for t in _TOKEN.findall(f"{o.imie} {o.nazwisko}") if len(t) >= 3 and t[0].isupper()):
            return False
        i, n = inicjaly(o)
        if re.search(rf"(?<!\w)(?:{i}{n}|{i}\.\s?{n}\.)(?!\w)", tekst):
            return False
    return True


def _z_probami(budowa: Callable[[str, str, int, int], tuple | None]) -> Generator_H5:
    """Generator przypadku: kolejne próby `budowa(język, typ, ziarno, próba)` do pierwszego dokumentu jednoznacznego."""
    def generator(jezyk: str, typ: str, seed: int) -> tuple:
        for proba in range(PROBY):
            wynik = budowa(jezyk, typ, seed, proba)
            if wynik is not None:
                return wynik
        raise RuntimeError(f"nie udało się złożyć jednoznacznego dokumentu ({jezyk}, {typ}, {seed})")  # pragma: no cover
    generator.__name__ = budowa.__name__
    return generator


def _kontekst(jezyk: str, seed: int, proba: int):
    return nowy_kontekst(jezyk, seed + 7919 * proba)


def _wynik(s: Skladacz, typ: str, ctx, gen, przypadek: str, cele: list[Osoba]) -> tuple | None:
    if not jednoznaczny(s, cele):
        return None
    return s.wynik(typ, ctx), gen, {"posrednie": kombinacje(s, przypadek), "cele": cele}


# ============================================================================= małe miejscowości
#: (mała miejscowość, gmina/miasto w pobliżu) – własna kompilacja nazw (nie dane osobowe); pary syntetyczne. Nazwy FR zaczynają
#: się od spółgłoski („du hameau de …”), ES – bez rodzajnika („de …”).
MALE_MIEJSCOWOSCI: dict[str, tuple[tuple[str, str], ...]] = {
    "pl": (("Zawady", "Kobylin"), ("Wola Rafałowska", "Chmielnik"), ("Dąbrówka Mała", "Strzegowo"),
           ("Bukowiec Górny", "Włoszakowice"), ("Pniewite", "Chełmno"), ("Sadłowo", "Rypin"), ("Kozłówek", "Kamionka"),
           ("Rudka Kijańska", "Spiczyn"), ("Huta Komorowska", "Majdan Królewski"), ("Ostrowite", "Golub-Dobrzyń"),
           ("Brzeziny Małe", "Gorzyce"), ("Jeżewo", "Dragacz"), ("Moszczanka", "Prudnik"), ("Sowia Wola", "Czosnów"),
           ("Wierzbica Górna", "Wołczyn"), ("Lipnik", "Kłodawa"), ("Czarnocin", "Wolbórz"), ("Grabowiec", "Mniów")),
    "en": (("Nether Wallop", "Stockbridge"), ("Great Snoring", "Fakenham"), ("Little Hadham", "Bishop's Stortford"),
           ("Upper Slaughter", "Stow-on-the-Wold"), ("Long Compton", "Shipston-on-Stour"), ("East Knoyle", "Shaftesbury"),
           ("Brightwell Baldwin", "Watlington"), ("Much Marcle", "Ledbury"), ("Slad", "Stroud"), ("Kersey", "Hadleigh"),
           ("Ribchester", "Longridge"), ("Castle Combe", "Chippenham"), ("Bibury", "Cirencester"), ("Hutton-le-Hole", "Kirkbymoorside"),
           ("Blanchland", "Hexham"), ("Clovelly", "Bideford")),
    "de": (("Zastler", "Oberried"), ("Wolfsbuch", "Beilngries"), ("Kleinengstingen", "Engstingen"), ("Hohenroth", "Gemünden"),
           ("Gräfenhausen", "Birkenfeld"), ("Unterwilden", "Sinnersdorf"), ("Niederhambach", "Heimbach"),
           ("Oberkirnach", "Sankt Georgen"), ("Rehweiler", "Geiselwind"), ("Mittelsinn", "Obersinn"), ("Kleinweitzschen", "Döbeln"),
           ("Tannenkirch", "Kandern"), ("Bärnau-Altglashütte", "Bärnau"), ("Hinterweidenthal", "Hauenstein"),
           ("Schönbrunn", "Wunsiedel"), ("Dornhan-Weiden", "Dornhan")),
    "es": (("Valdelacasa", "Alberca de Záncara"), ("Aldehuela de Yeltes", "Ciudad Rodrigo"), ("Cañada Juncosa", "Moratalla"),
           ("Fuentelsaz", "Tordesilos"), ("Cerezal de Peñahorcada", "Villarino de los Aires"), ("Torrecilla del Ducado", "Sigüenza"),
           ("Villacorta", "Riaza"), ("Bustarviejo de Arriba", "Valdemanco"), ("Quintanilla del Agua", "Lerma"),
           ("Penilla", "Santiurde de Toranzo"), ("Valverdejo", "Cardenete"), ("Moraleja de Cuéllar", "Cuéllar"),
           ("Navarredondilla", "Burgohondo"), ("Somosierra de Abajo", "Robregordo"), ("Huérmeces", "Villadiego"),
           ("Pajares de Adaja", "Arévalo")),
    "fr": (("Montrigaud", "Peyrins"), ("Chazelet", "Saint-Bonnet-de-Joux"), ("Vauxrenard", "Beaujeu"), ("Boissieu", "Trept"),
           ("Pontaubert", "Avallon"), ("Rochepot", "Nolay"), ("Coulandon", "Souvigny"), ("Fontenelles", "Rioz"),
           ("Brémoncourt", "Pierrepont"), ("Lantilly", "Semur-en-Auxois"), ("Mazerier", "Gannat"), ("Vernusse", "Montmarault"),
           ("Grandvelle", "Scey-sur-Saône"), ("Pouillenay", "Venarey-les-Laumes"), ("Sermizelles", "Vézelay"),
           ("Champeaux", "Dinan")),
}

# ============================================================================= 1. funkcja + firma
#: (funkcja – forma męska, forma żeńska, ramka: `{f}` funkcja, `{firma}` albo `{adres}` – drugi składnik, formy prawne spółki,
#: w której funkcja jest możliwa prawnie – None dla ramki z adresem). Tabela par funkcja – forma prawna (wiedza ogólna o prawie
#: spółek): PL – zarząd mają sp. z o.o., S.A. i P.S.A. (sp.j./sp.k. – nie), jedyny wspólnik – tylko sp. z o.o. (sp.j./sp.k.
#: wymagają co najmniej dwóch wspólników; S.A. ma akcjonariuszy), komplementariusz – sp.k. i S.K.A. (w sp. z o.o. sp.k.
#: komplementariuszem jest spółka z o.o.); DE – Geschäftsführer i Alleingesellschafter – GmbH/UG, Vorstand – AG; FR – gérant
#: – SARL/EURL, président – SAS/SASU, associé unique – EURL/SASU; ES – administrador único – S.L./S.A./S.L.U., socio único –
#: S.L.U. (S.A. ma accionista único); EN – director – Ltd/Limited/PLC (LLP ma członków, nie dyrektorów), sole shareholder –
#: Ltd/Limited. Księgowość i finanse – każda forma spółki (z tym samym zastrzeżeniem dla LLP i form osobowych).
_FUNKCJE: dict[str, tuple[tuple[str, str, str, tuple[str, ...] | None], ...]] = {
    "pl": (("Prezes Zarządu", "Prezes Zarządu", "{f} {firma}", ("sp. z o.o.", "S.A.", "P.S.A.")),
           ("główny księgowy", "główna księgowa", "{f} w spółce {firma}",
            ("sp. z o.o.", "S.A.", "P.S.A.", "sp.j.", "sp.k.", "sp. z o.o. sp.k.")),
           ("jedyny wspólnik", "jedyna wspólniczka", "{f} spółki {firma}", ("sp. z o.o.",)),
           ("dyrektor finansowy", "dyrektor finansowa", "{f} w {firma}",
            ("sp. z o.o.", "S.A.", "P.S.A.", "sp.j.", "sp.k.", "sp. z o.o. sp.k.")),
           ("komplementariusz", "komplementariuszka", "{f} spółki {firma}", ("sp.k.", "S.K.A.")),
           ("kierownik budowy", "kierowniczka budowy", "{f} na inwestycji prowadzonej pod adresem {adres}", None)),
    "en": (("Chief Financial Officer", "Chief Financial Officer", "{f} of {firma}", ("Ltd", "Limited", "PLC")),
           ("Managing Director", "Managing Director", "{f} of {firma}", ("Ltd", "Limited", "PLC")),
           ("sole shareholder", "sole shareholder", "{f} of {firma}", ("Ltd", "Limited")),
           ("Head of Accounts", "Head of Accounts", "{f} at {firma}", ("Ltd", "Limited", "PLC", "LLP")),
           ("site manager", "site manager", "{f} on the development at {adres}", None)),
    "de": (("Geschäftsführer", "Geschäftsführerin", "{f} der {firma}", ("GmbH", "UG (haftungsbeschränkt)")),
           ("Leiter der Buchhaltung", "Leiterin der Buchhaltung", "{f} der {firma}",
            ("GmbH", "AG", "UG (haftungsbeschränkt)", "KG", "GmbH & Co. KG", "OHG")),
           ("Alleingesellschafter", "Alleingesellschafterin", "{f} der {firma}", ("GmbH", "UG (haftungsbeschränkt)")),
           ("Finanzvorstand", "Finanzvorständin", "{f} der {firma}", ("AG",)),
           ("Bauleiter", "Bauleiterin", "{f} auf der Baustelle {adres}", None)),
    "es": (("administrador único", "administradora única", "{f} de {firma}", ("S.L.", "S.A.", "S.L.U.")),
           ("director financiero", "directora financiera", "{f} de {firma}", ("S.L.", "S.A.", "S.L.U.")),
           ("socio único", "socia única", "{f} de {firma}", ("S.L.U.",)),
           ("jefe de contabilidad", "jefa de contabilidad", "{f} de {firma}", ("S.L.", "S.A.", "S.L.U.")),
           ("jefe de obra", "jefa de obra", "{f} de la promoción situada en {adres}", None)),
    "fr": (("gérant", "gérante", "{f} de {firma}", ("SARL", "EURL")),
           ("président", "présidente", "{f} de {firma}", ("SAS", "SASU")),
           ("directeur financier", "directrice financière", "{f} de {firma}", ("SA", "SAS", "SARL")),
           ("associé unique", "associée unique", "{f} de {firma}", ("EURL", "SASU")),
           ("chef comptable", "cheffe comptable", "{f} de {firma}", ("SARL", "SAS", "SA", "SASU", "EURL", "SNC")),
           ("conducteur de travaux", "conductrice de travaux", "{f} du chantier situé {adres}", None)),
}
#: Liczba losowań firmy z generatora trzonu w poszukiwaniu formy prawnej pasującej do funkcji (potem – kolejna próba dokumentu).
LOSOWANIA_FIRMY = 200
#: Rodzajnik przed funkcją (forma męska, żeńska; FR przed samogłoską – elizja).
_RODZAJNIK = {"de": ("der ", "die "), "es": ("el ", "la "), "fr": ("le ", "la "), "en": ("the ", "the "), "pl": ("", "")}
#: Zdania z kombinacją (`{X}` – rodzajnik + ramka funkcji; PL: `{czas}` – czasownik wg płci osoby-celu).
_ZDANIA_FUNKCJI: dict[str, tuple[str, ...]] = {
    "pl": ("Według relacji klienta {X} {czas0} telefonicznie, że spółka nie ureguluje faktur przed końcem kwartału.",
           "W piśmie przesłanym w ubiegłym tygodniu {X} {czas1} wysokość naliczonych kar umownych.",
           "Na spotkaniu ugodowym {X} {czas2} rozłożenie zadłużenia na sześć rat."),
    "en": ("According to the client, {X} said by telephone that the company would not settle the invoices before the end "
           "of the quarter.",
           "In a letter received last week, {X} disputed the amount of the contractual penalties.",
           "At the settlement meeting, {X} proposed spreading the debt over six instalments."),
    "de": ("Nach Angaben des Mandanten teilte {X} telefonisch mit, dass die Gesellschaft die Rechnungen nicht vor Quartalsende "
           "begleichen werde.",
           "In einem Schreiben aus der vergangenen Woche bestritt {X} die Höhe der Vertragsstrafen.",
           "In der Vergleichsbesprechung schlug {X} eine Zahlung in sechs Raten vor."),
    "es": ("Según el cliente, {X} comunicó por teléfono que la sociedad no abonaría las facturas antes del cierre del trimestre.",
           "En un escrito recibido la semana pasada, {X} discutió el importe de las penalizaciones contractuales.",
           "En la reunión de conciliación, {X} propuso el pago aplazado de la deuda en seis plazos."),
    "fr": ("D'après le client, {X} a indiqué par téléphone que la société ne réglerait pas les factures avant la fin du trimestre.",
           "Dans un courrier reçu la semaine dernière, {X} a contesté le montant des pénalités contractuelles.",
           "Lors de la réunion de conciliation, {X} a proposé un échelonnement de la dette en six mensualités."),
}
_CZASY_PL = (("poinformował", "poinformowała"), ("zakwestionował", "zakwestionowała"), ("zaproponował", "zaproponowała"))
_TRESC_FUNKCJI: dict[str, dict[str, str]] = {
    "pl": {"n": "Notatka służbowa – rozliczenia z kontrahentami klienta",
           "p1": "Dnia {d} kancelaria przeprowadziła rozmowę telefoniczną z {przedstawiciel} klienta ({pelne}, tel. {tel}).",
           "przedstawiciel": "przedstawicielem|przedstawicielką",
           "p2": "Rozmowa dotyczyła należności klienta od dwóch kontrahentów.",
           "p5": "Klient prosi o przygotowanie wezwań do zapłaty w terminie do {d2}.",
           "p6": "{sporzadzil}: {autor}.", "sporzadzil": "Sporządził|Sporządziła"},
    "en": {"n": "File note – the client's counterparties",
           "p1": "On {d} the firm spoke by telephone with the client's representative ({pelne}, tel. {tel}).",
           "p2": "The call concerned amounts owed to the client by two counterparties.",
           "p5": "The client asks for letters before action to be prepared by {d2}.",
           "p6": "{sporzadzil}: {autor}.", "sporzadzil": "Prepared by|Prepared by"},
    "de": {"n": "Aktenvermerk – Forderungen gegenüber Vertragspartnern des Mandanten",
           "p1": "Am {d} führte die Kanzlei ein Telefongespräch mit der Vertretung des Mandanten ({pelne}, Tel. {tel}).",
           "p2": "Gegenstand des Gesprächs waren offene Forderungen gegenüber zwei Vertragspartnern.",
           "p5": "Der Mandant bittet um Vorbereitung von Mahnschreiben bis zum {d2}.",
           "p6": "{sporzadzil}: {autor}.", "sporzadzil": "Erstellt von|Erstellt von"},
    "es": {"n": "Nota interna – cobros pendientes de las contrapartes del cliente",
           "p1": "El {d} el despacho mantuvo una conversación telefónica con la persona de contacto del cliente ({pelne}, tel. {tel}).",
           "p2": "La conversación se refirió a las cantidades adeudadas al cliente por dos contrapartes.",
           "p5": "El cliente solicita que se preparen los requerimientos de pago antes del {d2}.",
           "p6": "{sporzadzil}: {autor}.", "sporzadzil": "Redactado por|Redactado por"},
    "fr": {"n": "Note interne – créances sur les cocontractants du client",
           "p1": "Le {d}, le cabinet s'est entretenu par téléphone avec {przedstawiciel} du client ({pelne}, tél. {tel}).",
           "przedstawiciel": "l'interlocuteur|l'interlocutrice",
           "p2": "L'entretien portait sur les sommes dues au client par deux cocontractants.",
           "p5": "Le client demande la préparation de mises en demeure avant le {d2}.",
           "p6": "{sporzadzil} : {autor}.", "sporzadzil": "Rédigé par|Rédigé par"},
}


def _firma_dla(gen, formy: tuple[str, ...]):
    """Firma z generatora trzonu w jednej z form prawnych `formy` (None – nie wylosowano)."""
    for _ in range(LOSOWANIA_FIRMY):
        firma = gen.firma()
        if firma.forma in formy:
            return firma
    return None


def _elizja(jezyk: str, ramka: str, nazwa: str) -> str:
    """FR: „de” przed nazwą firmy zaczynającą się samogłoską → „d'” („gérant d'Étoile SARL”)."""
    if jezyk == "fr" and nazwa[:1].lower() in "aeiouyéèêëàâîïôû":
        return ramka.replace("de {firma}", "d'{firma}")
    return ramka


def _rodzajnik(jezyk: str, plec: str, funkcja: str) -> str:
    art = _RODZAJNIK[jezyk][0 if plec == "M" else 1]
    if jezyk == "fr" and funkcja[:1].lower() in "aeiouéèêh":
        return "l'"
    return art


def _plec_tekst(wzor: str, plec: str) -> str:
    m, k = wzor.split("|")
    return _rodzaj(plec, m, k)


def _buduj_funkcja(jezyk: str, typ: str, seed: int, proba: int) -> tuple | None:
    gen, ctx = _kontekst(jezyk, seed, proba)
    rng = rng_h5(seed, "funkcja", proba)
    t = _TRESC_FUNKCJI[jezyk]
    # dwie różne funkcje: co najmniej jedna z firmą, druga dowolna (także kierownik budowy z adresem inwestycji)
    funkcje = rng.sample([f for f in _FUNKCJE[jezyk] if f[3] is not None], 1)
    funkcje.append(rng.choice([f for f in _FUNKCJE[jezyk] if f not in funkcje]))
    rng.shuffle(funkcje)
    cele = [osoba(gen, ctx) for _ in range(2)]
    kontakt = Os("kontakt", osoba(gen, ctx, None, bez_blokady), jezyk)
    autor = Os("autor", osoba(gen, ctx, None, bez_blokady), jezyk)
    zdania = list(_ZDANIA_FUNKCJI[jezyk])
    rng.shuffle(zdania)
    s = Skladacz(jezyk)
    s.naglowek(t["n"])
    przedstawiciel = _plec_tekst(t.get("przedstawiciel", "|"), kontakt.o.plec)      # PL, FR: forma wg płci osoby kontaktowej
    s.akapit(t["p1"], d=data_gold(ctx, "dok"), pelne=kontakt.pelne, tel=kontakt.telefon,
             przedstawiciel=przedstawiciel)
    s.akapit(t["p2"])
    for nr, ((fm, fk, ramka, formy), cel) in enumerate(zip(funkcje, cele), 1):
        k = f"k{nr}"
        f = _rodzaj(cel.plec, fm, fk)
        if formy is not None:
            firma = _firma_dla(gen, formy)
            if firma is None:
                return None
            ramka = _elizja(jezyk, ramka, firma.nazwa)
            drugi = {"firma": Skladnik(k, "firma", G(firma.nazwa, "ORGANIZACJA", f"firma{nr}.nazwa", f"firma{nr}"))}
        else:
            adres = gen.adres(gen.kraj_dok or gen.kraje[0])
            drugi = {"adres": Skladnik(k, "adres", G(adres.linia(), "ADRES", f"inwestycja{nr}.adres", f"inwestycja{nr}"))}
        zdanie = zdania[nr - 1]
        i = _ZDANIA_FUNKCJI[jezyk].index(zdanie)
        x = _rodzajnik(jezyk, cel.plec, f) + ramka
        sloty = {"f": Skladnik(k, "funkcja", f), **drugi}
        if jezyk == "pl":
            sloty[f"czas{i}"] = _rodzaj(cel.plec, *_CZASY_PL[i])
        s.akapit(zdanie.replace("{X}", x), **sloty)
    s.akapit(t["p5"], d2=data_gold(ctx, "dok_termin"))
    s.akapit(t["p6"], sporzadzil=_plec_tekst(t["sporzadzil"], autor.o.plec), autor=autor.pelne)
    return _wynik(s, typ, ctx, gen, P.POSREDNIE_FUNKCJA_FIRMA, cele)


# ============================================================================= 2. rzadka choroba
#: (nazwa w języku dokumentu, czy typowa u dziecka) – choroby z list chorób rzadkich (wiedza ogólna, typu Orphanet).
_CHOROBY: dict[str, tuple[tuple[str, bool], ...]] = {
    "pl": (("choroba Fabry'ego", True), ("zespół Ehlersa-Danlosa, typ naczyniowy", True), ("akromegalia", False),
           ("mukowiscydoza", True), ("choroba Gauchera typu 1", True), ("choroba Pompego o późnym początku", False),
           ("zespół Marfana", True), ("hemofilia A", True), ("rdzeniowy zanik mięśni typu 3", True),
           ("tętnicze nadciśnienie płucne", False)),
    "en": (("Fabry disease", True), ("vascular Ehlers-Danlos syndrome", True), ("acromegaly", False), ("cystic fibrosis", True),
           ("type 1 Gaucher disease", True), ("late-onset Pompe disease", False), ("Marfan syndrome", True),
           ("haemophilia A", True), ("spinal muscular atrophy type 3", True), ("pulmonary arterial hypertension", False)),
    "de": (("Morbus Fabry", True), ("vaskuläres Ehlers-Danlos-Syndrom", True), ("Akromegalie", False), ("Mukoviszidose", True),
           ("Morbus Gaucher Typ 1", True), ("Morbus Pompe mit spätem Beginn", False), ("Marfan-Syndrom", True),
           ("Hämophilie A", True), ("spinale Muskelatrophie Typ 3", True), ("pulmonal arterielle Hypertonie", False)),
    "es": (("enfermedad de Fabry", True), ("síndrome de Ehlers-Danlos vascular", True), ("acromegalia", False),
           ("fibrosis quística", True), ("enfermedad de Gaucher tipo 1", True), ("enfermedad de Pompe de inicio tardío", False),
           ("síndrome de Marfan", True), ("hemofilia A", True), ("atrofia muscular espinal tipo 3", True),
           ("hipertensión arterial pulmonar", False)),
    "fr": (("maladie de Fabry", True), ("syndrome d'Ehlers-Danlos vasculaire", True), ("acromégalie", False),
           ("mucoviscidose", True), ("maladie de Gaucher de type 1", True), ("maladie de Pompe à début tardif", False),
           ("syndrome de Marfan", True), ("hémophilie A", True), ("amyotrophie spinale de type 3", True),
           ("hypertension artérielle pulmonaire", False)),
}
#: Słowa rodzajowe przed i po nazwie choroby („choroba”, „zespół”, „disease”, „Morbus”, „-Syndrom”…) – poza rdzeniem składnika.
_RODZAJOWE_CHOROBY = re.compile(r"^(?:choroba|zespół|Morbus|enfermedad de|síndrome de|maladie de|syndrome de|syndrome d')\s*"
                                r"|\s+(?:disease|syndrome)$|-Syndrom$")


def rdzen_choroby(nazwa: str) -> str:
    """Rdzeń identyfikujący nazwy choroby: nazwa bez słów rodzajowych („choroba Fabry'ego” → „Fabry'ego”, „Marfan syndrome” →
    „Marfan”, „vaskuläres Ehlers-Danlos-Syndrom” → „vaskuläres Ehlers-Danlos”); nazwa bez nich – cała („akromegalia”)."""
    return _RODZAJOWE_CHOROBY.sub("", nazwa)


#: Rocznik osoby-celu (składnik spoza gold; `{r}` – rok urodzenia, wariant wg płci).
_ROCZNIK = {"pl": "rocznik {r}|rocznik {r}", "en": "born in {r}|born in {r}", "de": "Jahrgang {r}|Jahrgang {r}",
            "es": "nacido en {r}|nacida en {r}", "fr": "né en {r}|née en {r}"}
_TRESC_KADROWA: dict[str, dict[str, str]] = {
    "pl": {"n": "Notatka działu kadr – dostosowanie stanowiska pracy",
           "p1": "Dnia {d} do działu kadr wpłynął wniosek {pracownika} o dostosowanie stanowiska pracy do stanu zdrowia.",
           "pA": "{Pracownik} jest {zatrudniony} w {firma} w zakładzie w miejscowości {miejscowosc} i {przedstawil} zaświadczenie "
                 "lekarskie (rozpoznanie: {choroba}).",
           "pB": "{Pracownik} ({rocznik}) jest {zatrudniony} w {firma} w dziale logistyki i {przedstawil} zaświadczenie lekarskie "
                 "(rozpoznanie: {choroba}).",
           "p3": "{Lekarz} medycyny pracy, {lekarz_pelne}, {zalecil} ograniczenie pracy fizycznej i stały dostęp do pomieszczenia "
                 "socjalnego.",
           "p4": "{sporzadzil}: {autor}.",
           "pracownika": "pracownika|pracownicy", "Pracownik": "Pracownik|Pracownica", "zatrudniony": "zatrudniony|zatrudniona",
           "przedstawil": "przedstawił|przedstawiła", "Lekarz": "Lekarz|Lekarka", "zalecil": "zalecił|zaleciła",
           "sporzadzil": "Sporządził|Sporządziła"},
    "en": {"n": "HR note – request for workplace adjustments",
           "p1": "On {d} the HR department received a request from an employee for adjustments to their workplace on health grounds.",
           "pA": "The employee works for {firma} at the site in {miejscowosc} and has provided a medical certificate "
                 "(diagnosis: {choroba}).",
           "pB": "The employee ({rocznik}) works for {firma} in the logistics department and has provided a medical certificate "
                 "(diagnosis: {choroba}).",
           "p3": "The occupational health physician, {lekarz_pelne}, recommended limiting physical work and permanent access to a "
                 "rest room.",
           "p4": "{sporzadzil}: {autor}.", "sporzadzil": "Prepared by|Prepared by"},
    "de": {"n": "Personalvermerk – Antrag auf Anpassung des Arbeitsplatzes",
           "p1": "Am {d} ging in der Personalabteilung der Antrag {pracownika} auf gesundheitsbedingte Anpassung des Arbeitsplatzes "
                 "ein.",
           "pA": "{Pracownik} ist bei der {firma} im Werk {miejscowosc} beschäftigt und hat eine ärztliche Bescheinigung vorgelegt "
                 "(Diagnose: {choroba}).",
           "pB": "{Pracownik} ({rocznik}) ist bei der {firma} in der Logistikabteilung beschäftigt und hat eine ärztliche "
                 "Bescheinigung vorgelegt (Diagnose: {choroba}).",
           "p3": "{Lekarz} {lekarz_pelne} empfahl, die körperliche Arbeit zu begrenzen und einen ständigen Zugang zu einem "
                 "Ruheraum zu gewährleisten.",
           "p4": "{sporzadzil}: {autor}.",
           "pracownika": "eines Mitarbeiters|einer Mitarbeiterin", "Pracownik": "Der Mitarbeiter|Die Mitarbeiterin",
           "Lekarz": "Der Betriebsarzt|Die Betriebsärztin", "sporzadzil": "Erstellt von|Erstellt von"},
    "es": {"n": "Nota de recursos humanos – solicitud de adaptación del puesto de trabajo",
           "p1": "El {d} el departamento de recursos humanos recibió una solicitud de {pracownika} para adaptar su puesto de "
                 "trabajo por motivos de salud.",
           "pA": "{Pracownik} presta servicios en {firma} en el centro de trabajo de {miejscowosc} y ha aportado un informe médico "
                 "(diagnóstico: {choroba}).",
           "pB": "{Pracownik} ({rocznik}) presta servicios en {firma} en el departamento de logística y ha aportado un informe "
                 "médico (diagnóstico: {choroba}).",
           "p3": "{Lekarz} del trabajo, {lekarz_pelne}, recomendó limitar el trabajo físico y garantizar el acceso permanente a una "
                 "sala de descanso.",
           "p4": "{sporzadzil}: {autor}.",
           "pracownika": "un trabajador|una trabajadora", "Pracownik": "El trabajador|La trabajadora",
           "Lekarz": "El médico|La médica", "sporzadzil": "Redactado por|Redactado por"},
    "fr": {"n": "Note des ressources humaines – demande d'aménagement de poste",
           "p1": "Le {d}, le service des ressources humaines a reçu une demande d'aménagement de poste pour raisons de santé de "
                 "la part {pracownika}.",
           "pA": "{Pracownik} travaille chez {firma} sur le site de {miejscowosc} et a remis un certificat médical "
                 "(diagnostic : {choroba}).",
           "pB": "{Pracownik} ({rocznik}) travaille chez {firma} au service logistique et a remis un certificat médical "
                 "(diagnostic : {choroba}).",
           "p3": "Le médecin du travail, {lekarz_pelne}, a recommandé de limiter le travail physique et de garantir un accès "
                 "permanent à une salle de repos.",
           "p4": "{sporzadzil} : {autor}.",
           "pracownika": "d'un salarié|d'une salariée", "Pracownik": "Le salarié|La salariée",
           "sporzadzil": "Rédigé par|Rédigé par"},
}
#: Szkoła (składnik spoza gold, bez nazw własnych osób): wzór z `{n}` (numer) albo `{x}` (nazwa) i pula nazw.
_SZKOLY: dict[str, tuple[str, tuple[str, ...]]] = {
    "pl": ("Szkoła Podstawowa nr {n}", ()),
    "en": ("{x} Primary School", ("Hillside", "Meadowbank", "Oakfield", "Brookfield", "Westfield", "Ashgrove")),
    "de": ("Grundschule am {x}", ("Lindenhof", "Mühlbach", "Sonnenberg", "Eichenhain", "Wiesengrund", "Kirchberg")),
    "es": ("CEIP {x}", ("Los Almendros", "El Olivar", "Las Encinas", "Los Pinares", "Las Acacias", "El Romeral")),
    "fr": ("école élémentaire des {x}", ("Tilleuls", "Coquelicots", "Marronniers", "Peupliers", "Glycines", "Noisetiers")),
}
_KLASY = {"pl": ("3a", "4b", "5a", "6c", "2b"), "en": ("Year 3", "Year 4", "Year 5", "Year 6"), "de": ("3b", "4a", "2c", "4c"),
          "es": ("3.º de Primaria", "4.º de Primaria", "5.º de Primaria"), "fr": ("CE2", "CM1", "CM2")}
_TRESC_SZKOLNA: dict[str, dict[str, str]] = {
    "pl": {"n": "Notatka ze spotkania zespołu pomocy psychologiczno-pedagogicznej",
           "p1": "Dnia {d} odbyło się spotkanie zespołu w sprawie {ucznia} klasy {klasa}.",
           "p2": "Szkoła: {szkola}, {miejscowosc}. Rozpoznanie przedstawione przez rodziców: {choroba}.",
           "p3": "{Wychowawca} klasy, {wych_pelne}, przygotuje plan dostosowań wymagań edukacyjnych.",
           "p4": "{sporzadzil}: {autor}, pedagog szkolny.",
           "ucznia": "ucznia|uczennicy", "Wychowawca": "Wychowawca|Wychowawczyni", "sporzadzil": "Sporządził|Sporządziła"},
    "en": {"n": "Note of meeting – support for a pupil",
           "p1": "On {d} the school support team met to discuss a pupil in {klasa}.",
           "p2": "School: {szkola}, {miejscowosc}. Diagnosis reported by the parents: {choroba}.",
           "p3": "The class teacher, {wych_pelne}, will prepare an individual support plan.",
           "p4": "{sporzadzil}: {autor}, school counsellor.", "sporzadzil": "Prepared by|Prepared by"},
    "de": {"n": "Gesprächsnotiz – Förderung im Schulalltag",
           "p1": "Am {d} beriet das Förderteam der Schule über {ucznia} der Klasse {klasa}.",
           "p2": "Schule: {szkola}, {miejscowosc}. Von den Eltern mitgeteilte Diagnose: {choroba}.",
           "p3": "{Wychowawca} {wych_pelne} erstellt einen individuellen Förderplan.",
           "p4": "{sporzadzil}: {autor}, Schulsozialarbeit.",
           "ucznia": "einen Schüler|eine Schülerin", "Wychowawca": "Der Klassenlehrer|Die Klassenlehrerin",
           "sporzadzil": "Erstellt von|Erstellt von"},
    "es": {"n": "Nota de reunión – apoyo al alumnado",
           "p1": "El {d} se reunió el equipo de orientación del centro para tratar el caso de {ucznia} de {klasa}.",
           "p2": "Centro: {szkola}, {miejscowosc}. Diagnóstico comunicado por la familia: {choroba}.",
           "p3": "{Wychowawca} del grupo, {wych_pelne}, preparará un plan de apoyo individual.",
           "p4": "{sporzadzil}: {autor}, orientación educativa.",
           "ucznia": "un alumno|una alumna", "Wychowawca": "El tutor|La tutora", "sporzadzil": "Redactado por|Redactado por"},
    "fr": {"n": "Compte rendu – accompagnement scolaire",
           "p1": "Le {d}, l'équipe éducative s'est réunie au sujet {ucznia} de {klasa}.",
           "p2": "École : {szkola}, {miejscowosc}. Diagnostic communiqué par la famille : {choroba}.",
           "p3": "{Wychowawca} de la classe, {wych_pelne}, préparera un projet d'accueil individualisé.",
           "p4": "{sporzadzil} : {autor}, psychologue scolaire.",
           "ucznia": "d'un élève|d'une élève", "Wychowawca": "L'enseignant|L'enseignante", "sporzadzil": "Rédigé par|Rédigé par"},
}


def _g_miejscowosc(nazwa: str, klucz: str) -> G:
    return G(nazwa, "MIEJSCOWOSC", f"{klucz}.miasto", klucz)


def _buduj_choroba(jezyk: str, typ: str, seed: int, proba: int) -> tuple | None:
    gen, ctx = _kontekst(jezyk, seed, proba)
    rng = rng_h5(seed, "choroba", typ, proba)
    szkolna = typ == "notatka_szkolna"
    choroby = [c for c, dziecko in _CHOROBY[jezyk] if dziecko or not szkolna]
    nazwa_choroby = rng.choice(choroby)
    # nazwa choroby nie jest gold (ZDROWIE z rozpoznań poza zakresem) – zostaje w tekście jako składnik kombinacji
    choroba = Skladnik("k1", "choroba", nazwa_choroby, (rdzen_choroby(nazwa_choroby),))
    wies = rng.choice(MALE_MIEJSCOWOSCI[jezyk])[0]
    t = _TRESC_SZKOLNA[jezyk] if szkolna else _TRESC_KADROWA[jezyk]
    p = lambda klucz, plec: _plec_tekst(t[klucz], plec)        # noqa: E731
    s = Skladacz(jezyk)
    s.naglowek(t["n"])
    if szkolna:
        cel = osoba(gen, ctx)       # tylko płeć (uczeń jest nienazwany; dorosła osoba z generatora – wiek bez znaczenia)
        wzor, nazwy = _SZKOLY[jezyk]
        rdzen_szkoly = str(rng.randint(1, 12)) if not nazwy else rng.choice(nazwy)      # numer (PL) albo nazwa szkoły
        szkola = wzor.format(n=rdzen_szkoly, x=rdzen_szkoly)
        wych = Os("wychowawca", osoba(gen, ctx, None, bez_blokady), jezyk)
        autor = Os("autor", osoba(gen, ctx, None, bez_blokady), jezyk)
        s.akapit(t["p1"], d=data_gold(ctx, "dok"), klasa=rng.choice(_KLASY[jezyk]),
                 **({"ucznia": p("ucznia", cel.plec)} if "{ucznia}" in t["p1"] else {}))
        s.akapit(t["p2"], szkola=Skladnik("k1", "szkola", szkola, (rdzen_szkoly,)),
                 miejscowosc=Skladnik("k1", "miejscowosc", _g_miejscowosc(wies, "szkola")),
                 choroba=choroba)
        s.akapit(t["p3"], wych_pelne=wych.pelne, **({"Wychowawca": p("Wychowawca", wych.o.plec)} if "{Wychowawca}" in t["p3"] else {}))
    else:
        cel = osoba(gen, ctx, None, lambda o: _wiek(o, ctx.daty["dok"]) <= WIEK_PRACY)    # pracownik w wieku produkcyjnym
        firma = gen.firma()
        lekarz = Os("lekarz", osoba(gen, ctx, None, bez_blokady), jezyk)
        autor = Os("autor", osoba(gen, ctx, None, bez_blokady), jezyk)
        plec_sloty = {k: p(k, cel.plec) for k in ("pracownika", "Pracownik", "zatrudniony", "przedstawil") if k in t}
        s.akapit(t["p1"], d=data_gold(ctx, "dok"), **{k: v for k, v in plec_sloty.items() if "{" + k + "}" in t["p1"]})
        g_firma = Skladnik("k1", "firma", G(firma.nazwa, "ORGANIZACJA", "pracodawca.nazwa", "pracodawca"))
        if rng.random() < 0.5:
            sloty = {"miejscowosc": Skladnik("k1", "miejscowosc", _g_miejscowosc(wies, "zaklad"))}
            zdanie = t["pA"]
        else:
            rok = str(cel.data_ur.year)
            sloty = {"rocznik": Skladnik("k1", "rok_urodzenia", _plec_tekst(_ROCZNIK[jezyk], cel.plec).format(r=rok), (rok,))}
            zdanie = t["pB"]
        s.akapit(zdanie, firma=g_firma, choroba=choroba, **sloty,
                 **{k: v for k, v in plec_sloty.items() if "{" + k + "}" in zdanie})
        s.akapit(t["p3"], lekarz_pelne=lekarz.pelne,
                 **{k: p(k, lekarz.o.plec) for k in ("Lekarz", "zalecil") if "{" + k + "}" in t["p3"]})
    s.akapit(t["p4"], sporzadzil=p("sporzadzil", autor.o.plec), autor=autor.pelne)
    return _wynik(s, typ, ctx, gen, P.POSREDNIE_RZADKA_CHOROBA, [cel])


# ============================================================================= 3. wiek + mała miejscowość
#: Wiek osoby-celu (składnik spoza gold; `{n}` – lata, wariant wg płci).
_WIEK = {"pl": "{n}-letni|{n}-letnia", "en": "{n}-year-old|{n}-year-old", "de": "{n}-jähriger|{n}-jährige",
         "es": "{n} años|{n} años", "fr": "âgé de {n} ans|âgée de {n} ans"}
_TRESC_ZDARZENIA: dict[str, dict[str, object]] = {
    "pl": {"n": "Notatka z czynności wyjaśniających – zdarzenie drogowe",
           "p1": "Dnia {d} na drodze gminnej doszło do zdarzenia drogowego z udziałem samochodu osobowego kierowanego przez "
                 "{kierowca}, zam. {adres}.",          # PL: {kierowca} w bierniku („przez Tadeusza Kwiatkowskiego”)
           "cel": ("Drugim uczestnikiem zdarzenia był {wiek} mieszkaniec wsi {wies} (gm. {gmina}), który poruszał się rowerem.|"
                   "Drugą uczestniczką zdarzenia była {wiek} mieszkanka wsi {wies} (gm. {gmina}), która poruszała się rowerem.",
                   "Poboczem drogi szedł {wiek} mieszkaniec wsi {wies} (gm. {gmina}), który wracał z pracy.|"
                   "Poboczem drogi szła {wiek} mieszkanka wsi {wies} (gm. {gmina}), która wracała z pracy."),
           "p3": "Świadek zdarzenia: {swiadek}, tel. {tel}.",
           "p4": "Sprawę przekazano do likwidacji szkody; oględziny pojazdu wyznaczono na {d2}.",
           "p5": "{sporzadzil}: {autor}.", "sporzadzil": "Sporządził|Sporządziła"},
    "en": {"n": "Incident note – road traffic collision",
           "p1": "On {d} a collision occurred on a country lane involving a car driven by {kierowca} of {adres}.",
           "cel": ("The other party was a {wiek} resident of the village of {wies}, near {gmina}, who was riding a bicycle.|"
                   "The other party was a {wiek} resident of the village of {wies}, near {gmina}, who was riding a bicycle.",
                   "A {wiek} resident of the village of {wies}, near {gmina}, was walking along the verge on the way home from "
                   "work.|A {wiek} resident of the village of {wies}, near {gmina}, was walking along the verge on the way home "
                   "from work."),
           "p3": "Witness: {swiadek}, tel. {tel}.",
           "p4": "The claim has been passed to the claims team; the vehicle inspection is booked for {d2}.",
           "p5": "{sporzadzil}: {autor}.", "sporzadzil": "Prepared by|Prepared by"},
    "de": {"n": "Aktenvermerk – Verkehrsunfall",
           "p1": "Am {d} kam es auf einer Gemeindeverbindungsstraße zu einem Unfall mit einem Pkw, der von {kierowca}, "
                 "wohnhaft {adres}, gesteuert wurde.",
           "cel": ("Unfallbeteiligt war ein {wiek} Einwohner des Ortsteils {wies} der Gemeinde {gmina}, der mit dem Fahrrad "
                   "unterwegs war.|Unfallbeteiligt war eine {wiek} Einwohnerin des Ortsteils {wies} der Gemeinde {gmina}, die "
                   "mit dem Fahrrad unterwegs war.",
                   "Am Straßenrand ging ein {wiek} Einwohner des Ortsteils {wies} der Gemeinde {gmina}, der sich auf dem Heimweg "
                   "von der Arbeit befand.|Am Straßenrand ging eine {wiek} Einwohnerin des Ortsteils {wies} der Gemeinde "
                   "{gmina}, die sich auf dem Heimweg von der Arbeit befand."),
           "p3": "{zeuge}: {swiadek}, Tel. {tel}.", "zeuge": "Zeuge|Zeugin",
           "p4": "Der Schaden wurde an die Schadenabteilung weitergeleitet; die Fahrzeugbesichtigung ist für den {d2} angesetzt.",
           "p5": "{sporzadzil}: {autor}.", "sporzadzil": "Erstellt von|Erstellt von"},
    "es": {"n": "Nota de incidencia – accidente de circulación",
           "p1": "El {d} se produjo un accidente en un camino vecinal en el que estuvo implicado un turismo conducido por "
                 "{kierowca}, con domicilio en {adres}.",
           "cel": ("El otro implicado fue un vecino de {wiek} de la pedanía de {wies}, en el término municipal de {gmina}, que "
                   "circulaba en bicicleta.|La otra implicada fue una vecina de {wiek} de la pedanía de {wies}, en el término "
                   "municipal de {gmina}, que circulaba en bicicleta.",
                   "Por el arcén caminaba un vecino de {wiek} de la pedanía de {wies}, en el término municipal de {gmina}, que "
                   "volvía del trabajo.|Por el arcén caminaba una vecina de {wiek} de la pedanía de {wies}, en el término "
                   "municipal de {gmina}, que volvía del trabajo."),
           "p3": "Testigo: {swiadek}, tel. {tel}.",
           "p4": "El siniestro se ha remitido al departamento de siniestros; la peritación del vehículo está prevista para el {d2}.",
           "p5": "{sporzadzil}: {autor}.", "sporzadzil": "Redactado por|Redactado por"},
    "fr": {"n": "Note d'incident – accident de la circulation",
           "p1": "Le {d}, un accident s'est produit sur une route communale impliquant un véhicule conduit par {kierowca}, "
                 "demeurant {adres}.",
           "cel": ("L'autre partie était un habitant {wiek} du hameau de {wies}, commune de {gmina}, qui circulait à vélo.|"
                   "L'autre partie était une habitante {wiek} du hameau de {wies}, commune de {gmina}, qui circulait à vélo.",
                   "Sur le bas-côté marchait un habitant {wiek} du hameau de {wies}, commune de {gmina}, qui rentrait de son "
                   "travail.|Sur le bas-côté marchait une habitante {wiek} du hameau de {wies}, commune de {gmina}, qui rentrait "
                   "de son travail."),
           "p3": "Témoin : {swiadek}, tél. {tel}.",
           "p4": "Le sinistre a été transmis au service sinistres ; l'expertise du véhicule est prévue le {d2}.",
           "p5": "{sporzadzil} : {autor}.", "sporzadzil": "Rédigé par|Rédigé par"},
}


#: Najwyższy wiek osoby-celu opisanej jako pracownik albo wracającej z pracy.
WIEK_PRACY = 64


def _wiek(cel: Osoba, dzien) -> int:
    return dzien.year - cel.data_ur.year - ((dzien.month, dzien.day) < (cel.data_ur.month, cel.data_ur.day))


def _buduj_wiek(jezyk: str, typ: str, seed: int, proba: int) -> tuple | None:
    gen, ctx = _kontekst(jezyk, seed, proba)
    rng = rng_h5(seed, "wiek", proba)
    t = _TRESC_ZDARZENIA[jezyk]
    wies, gmina = rng.choice(MALE_MIEJSCOWOSCI[jezyk])
    cel = osoba(gen, ctx)
    kierowca = Os("kierowca", osoba(gen, ctx, None, bez_blokady), jezyk)
    swiadek = Os("swiadek", osoba(gen, ctx, None, bez_blokady), jezyk)
    autor = Os("autor", osoba(gen, ctx, None, bez_blokady), jezyk)
    d = data_gold(ctx, "dok")
    lata = _wiek(cel, ctx.daty["dok"])
    wiek = _plec_tekst(_WIEK[jezyk], cel.plec).format(n=lata)
    # ramka „wraca z pracy” (druga) tylko dla osoby w wieku produkcyjnym
    zdanie = _plec_tekst(rng.choice(t["cel"] if lata <= WIEK_PRACY else t["cel"][:1]), cel.plec)
    if jezyk == "en" and (str(lata).startswith("8") or lata in (11, 18)):     # „an 82-year-old”, „an 18-year-old”
        zdanie = zdanie.replace("a {wiek}", "an {wiek}").replace("A {wiek}", "An {wiek}")
    s = Skladacz(jezyk)
    s.naglowek(t["n"])
    g_kierowca = (kierowca.g("pelne", odmien(kierowca.o.imie, kierowca.o.nazwisko, kierowca.o.plec, "bier"),
                             cechy=("przypadek_zalezny",)) if jezyk == "pl" else kierowca.pelne)
    s.akapit(t["p1"], d=d, kierowca=g_kierowca, adres=kierowca.adres)
    s.akapit(zdanie, wiek=Skladnik("k1", "wiek", wiek, (str(lata),)),
             wies=Skladnik("k1", "miejscowosc", _g_miejscowosc(wies, "cel")), gmina=_g_miejscowosc(gmina, "gmina"))
    s.akapit(t["p3"], swiadek=swiadek.pelne, tel=swiadek.telefon,
             **({"zeuge": _plec_tekst(t["zeuge"], swiadek.o.plec)} if "zeuge" in t else {}))
    s.akapit(t["p4"], d2=data_gold(ctx, "dok_termin"))
    s.akapit(t["p5"], sporzadzil=_plec_tekst(t["sporzadzil"], autor.o.plec), autor=autor.pelne)
    return _wynik(s, typ, ctx, gen, P.POSREDNIE_WIEK_MIEJSCOWOSC, [cel])


# ============================================================================= 4. działka + GPS
#: Obszary lądowe kraju dokumentu (EN – Anglia): prostokąty (szerokość od–do, długość od–do) w głębi lądu, z dala od wybrzeża
#: i granic państwowych – wiedza ogólna o położeniu regionów, współrzędne zaokrąglone do 0,1°. Punkt w prostokącie leży na lądzie
#: w kraju dokumentu (nie musi odpowiadać miejscowości ani adresowi dokumentu – dane syntetyczne).
OBSZARY_LADOWE: dict[str, tuple[tuple[tuple[float, float], tuple[float, float]], ...]] = {
    "pl": (((51.5, 52.5), (16.5, 18.5)),        # Wielkopolska
           ((50.3, 51.0), (19.5, 21.5)),        # Małopolska północna, Świętokrzyskie
           ((52.6, 53.4), (19.5, 22.0)),        # Mazowsze północne
           ((51.0, 51.8), (22.0, 23.3))),       # Lubelszczyzna
    "en": (((51.6, 52.4), (-2.2, -0.5)),        # Cotswolds, Oxfordshire, Buckinghamshire
           ((52.6, 53.6), (-2.2, -1.0)),        # Peak District, East Midlands
           ((51.0, 51.4), (-2.0, -0.8)),        # Wiltshire, północny Hampshire
           ((52.0, 52.6), (0.0, 1.0))),         # Cambridgeshire, zachodni Suffolk
    "de": (((48.3, 49.3), (8.8, 12.0)),         # Badenia-Wirtembergia, Frankonia, Górny Palatynat
           ((50.0, 51.5), (7.5, 11.5)),         # Hesja, Turyngia
           ((51.8, 53.0), (8.0, 13.5))),        # Dolna Saksonia, Saksonia-Anhalt, Brandenburgia
    "es": (((39.0, 41.5), (-6.0, -2.0)),        # Meseta: Kastylia-La Mancha, Madryt, Kastylia i León
           ((37.3, 38.5), (-5.5, -3.0)),        # Andaluzja w głębi lądu (Kordoba, Jaén)
           ((41.5, 42.5), (-6.0, -1.5))),       # Kastylia i León, Rioja, Aragonia
    "fr": (((46.0, 48.0), (0.5, 4.5)),          # Centre-Val de Loire, Burgundia zachodnia
           ((44.0, 45.5), (1.0, 4.0)),          # Masyw Centralny
           ((47.0, 49.0), (4.5, 6.0)),          # Burgundia wschodnia, Szampania, Lotaryngia
           ((48.5, 49.5), (1.5, 3.5))),         # Île-de-France, Pikardia
}


def gps(rng: random.Random, jezyk: str, dms: bool) -> tuple[str, tuple[str, ...]]:
    """Współrzędne punktu lądowego w kraju dokumentu (`OBSZARY_LADOWE`) i ich rdzeń identyfikujący (liczby, bez liter półkul
    i symboli): dziesiętne („52.231234, 21.012345”) albo stopnie-minuty-sekundy („52°13′52.4″N 21°00′44.4″E”)."""
    (s0, s1), (d0, d1) = rng.choice(OBSZARY_LADOWE[jezyk])
    szer, dl = rng.uniform(s0, s1), rng.uniform(d0, d1)
    if not dms:
        a, b = f"{szer:.6f}", f"{dl:.6f}"
        return f"{a}, {b}", (a, b)

    def zapis(x: float) -> tuple[str, str, str]:
        dziesiate = round(abs(x) * 36000)          # dziesiąte części sekundy
        st, reszta = divmod(dziesiate, 36000)
        mi, se = divmod(reszta, 600)
        return str(st), f"{mi:02d}", f"{se // 10:02d}.{se % 10}"
    a, b = zapis(szer), zapis(dl)
    tekst = f"{a[0]}°{a[1]}′{a[2]}″{'N' if szer >= 0 else 'S'} {b[0]}°{b[1]}′{b[2]}″{'E' if dl >= 0 else 'W'}"
    return tekst, (*a, *b)


#: Prefiksy numerów tytułu HM Land Registry (Anglia; tylko format – numery syntetyczne).
_PREFIKSY_TYTULU = ("WK", "HP", "WT", "GR", "BK", "ON", "NK", "SK", "DY", "NN", "CB", "HD")


def dzialka(rng: random.Random, jezyk: str) -> tuple[str, tuple[str, ...]]:
    """Oznaczenie działki ewidencyjnej w zapisie kraju dokumentu i jego rdzeń identyfikujący (numer i identyfikator obrębu):
    obręb (PL), Flur/Flurstück (DE), section (FR), polígono/parcela (ES); EN – numer tytułu księgi HM Land Registry
    („title number WK123456”: Anglia nie ma numerów działek – nieruchomość wskazuje numer tytułu)."""
    nr = f"{rng.randint(1, 999)}/{rng.randint(1, 30)}" if rng.random() < 0.7 else str(rng.randint(10, 999))
    if jezyk == "pl":
        obreb = f"{rng.randint(1, 60):04d}"
        return f"{nr}, obręb {obreb}", (nr, obreb)
    if jezyk == "de":
        flur = str(rng.randint(1, 14))
        return f"Flur {flur}, Flurstück {nr}", (flur, nr)
    if jezyk == "fr":
        litery = "ABCDEHKLMNOPRSTWXYZ"
        sekcja, numer = rng.choice(litery) + rng.choice(litery), str(rng.randint(10, 999))
        return f"section {sekcja} n° {numer}", (sekcja, numer)
    if jezyk == "es":
        parcela, poligono = str(rng.randint(1, 250)), str(rng.randint(1, 40))
        return f"parcela {parcela} del polígono {poligono}", (parcela, poligono)
    tytul = f"{rng.choice(_PREFIKSY_TYTULU)}{rng.randint(100000, 999999)}"
    return f"title number {tytul}", (tytul,)


_TRESC_OGLEDZIN: dict[str, dict[str, str]] = {
    "pl": {"n": "Protokół oględzin nieruchomości",
           "p1": "W dniu {d} rzeczoznawca majątkowy {rzecz} {przeprowadzil} oględziny nieruchomości gruntowej zabudowanej "
                 "budynkiem mieszkalnym jednorodzinnym.",
           "polozenie": "Nieruchomość położona jest w miejscowości {miejscowosc} (gm. {gmina}).",
           "adres": "Nieruchomość położona jest pod adresem {adres}.",
           "kw": "Dla nieruchomości prowadzona jest księga wieczysta nr {kw}.",
           "dz": "Nieruchomość stanowi działkę ewidencyjną nr {dzialka}.",
           "cel": "Budynek zamieszkuje właściciel nieruchomości wraz z rodziną; w trakcie oględzin był nieobecny.",
           "gps": "Współrzędne geograficzne wejścia do budynku mieszkalnego (WGS 84): {gps}.",
           "sasiad": "Przy oględzinach {obecny} {sasiada}, {sasiad_pelne}.",
           "koniec": "Protokół {sporzadzil} {rzecz}.",
           "przeprowadzil": "przeprowadził|przeprowadziła", "obecny": "obecny był|obecna była", "sasiada": "sąsiad|sąsiadka",
           "sporzadzil": "sporządził|sporządziła"},
    "en": {"n": "Property inspection report",
           "p1": "On {d} the chartered surveyor {rzecz} inspected a detached residential house and its plot.",
           "polozenie": "The property is situated in {miejscowosc}, near {gmina}.",
           "adres": "The property is situated at {adres}.",
           "dz": "The property is registered under {dzialka}.",
           "cel": "The house is occupied by the owner and their family; the owner was not present during the inspection.",
           "gps": "Coordinates of the front door of the house (WGS 84): {gps}.",
           "sasiad": "A neighbour, {sasiad_pelne}, was present during the inspection.",
           "koniec": "Report prepared by {rzecz}."},
    "de": {"n": "Protokoll der Grundstücksbesichtigung",
           "p1": "Am {d} besichtigte {rzecz_art} {rzecz} ein mit einem Einfamilienhaus bebautes Grundstück.",
           "polozenie": "Das Grundstück liegt im Ortsteil {miejscowosc} der Gemeinde {gmina}.",
           "adres": "Anschrift des Grundstücks: {adres}.",
           "dz": "Es ist im Liegenschaftskataster als {dzialka} verzeichnet.",
           "cel": "Das Haus wird vom Eigentümer mit Familie bewohnt; der Eigentümer war bei der Besichtigung nicht anwesend.",
           "gps": "Koordinaten des Hauseingangs (WGS 84): {gps}.",
           "sasiad": "Bei der Besichtigung war {sasiada} {sasiad_pelne} anwesend.",
           "koniec": "Protokoll erstellt von {rzecz}.",
           "rzecz_art": "der Sachverständige|die Sachverständige", "sasiada": "der Nachbar|die Nachbarin"},
    "es": {"n": "Acta de inspección de inmueble",
           "p1": "El {d} {rzecz_art} {rzecz} inspeccionó una vivienda unifamiliar aislada y su parcela.",
           "polozenie": "La finca se encuentra en la pedanía de {miejscowosc}, término municipal de {gmina}.",
           "adres": "La finca se encuentra en {adres}.",
           "dz": "Figura en el Catastro como {dzialka}.",
           "cel": "La vivienda está ocupada por su propietario y su familia; el propietario no estuvo presente durante la "
                  "inspección.",
           "gps": "Coordenadas de la entrada de la vivienda (WGS 84): {gps}.",
           "sasiad": "Asistió a la inspección {sasiada}, {sasiad_pelne}.",
           "koniec": "Acta redactada por {rzecz}.",
           "rzecz_art": "el perito tasador|la perita tasadora", "sasiada": "un vecino|una vecina"},
    "fr": {"n": "Procès-verbal de visite d'un bien immobilier",
           "p1": "Le {d}, {rzecz_art} {rzecz} a visité une maison individuelle et son terrain.",
           "polozenie": "Le bien est situé au hameau de {miejscowosc}, commune de {gmina}.",
           "adres": "Le bien est situé {adres}.",
           "dz": "Il est cadastré {dzialka}.",
           "cel": "La maison est occupée par son propriétaire et sa famille ; le propriétaire était absent lors de la visite.",
           "gps": "Coordonnées de l'entrée de la maison (WGS 84) : {gps}.",
           "sasiad": "{sasiada}, {sasiad_pelne}, a assisté à la visite.",
           "koniec": "Procès-verbal rédigé par {rzecz}.",
           "rzecz_art": "l'expert immobilier|l'experte immobilière", "sasiada": "Un voisin|Une voisine"},
}


def _buduj_dzialka(jezyk: str, typ: str, seed: int, proba: int) -> tuple | None:
    gen, ctx = _kontekst(jezyk, seed, proba)
    rng = rng_h5(seed, "dzialka", proba)
    t = _TRESC_OGLEDZIN[jezyk]
    p = lambda klucz, plec: _plec_tekst(t[klucz], plec)        # noqa: E731
    cel = osoba(gen, ctx)       # właściciel – nienazwany; płeć bez znaczenia (forma ogólna „właściciel”)
    rzecz = Os("rzeczoznawca", osoba(gen, ctx, None, bez_blokady), jezyk)
    sasiad = Os("sasiad", osoba(gen, ctx, None, bez_blokady), jezyk)
    wies, gmina = rng.choice(MALE_MIEJSCOWOSCI[jezyk])
    # połowa dokumentów wskazuje nieruchomość także zwykłym gold (PL: księga wieczysta albo adres; inne języki: adres – miara
    # główna), połowa – tylko miejscowością; działka i GPS to osobne kombinacje jednoskładnikowe (każde samo wskazuje dom)
    gold = rng.choice(("kw", "adres")) if jezyk == "pl" else "adres"
    gold = gold if rng.random() < 0.5 else None
    s = Skladacz(jezyk)
    s.naglowek(t["n"])
    s.akapit(t["p1"], d=data_gold(ctx, "dok"), rzecz=rzecz.pelne,
             **{k: p(k, rzecz.o.plec) for k in ("przeprowadzil", "rzecz_art") if "{" + k + "}" in t["p1"]})
    if gold == "adres":
        a = gen.adres(gen.kraj_dok or gen.kraje[0])
        s.akapit(t["adres"], adres=G(a.linia(), "ADRES", "nieruchomosc.adres", "nieruchomosc"))
    else:
        s.akapit(t["polozenie"], miejscowosc=_g_miejscowosc(wies, "nieruchomosc"), gmina=_g_miejscowosc(gmina, "gmina"))
    if gold == "kw":
        s.akapit(t["kw"], kw=G(gen.ksiega_wieczysta(), "KSIEGA_WIECZYSTA", "nieruchomosc.kw", "nieruchomosc"))
    tekst_dz, rdzen_dz = dzialka(rng, jezyk)
    s.akapit(t["dz"], dzialka=Skladnik("k1", "dzialka", tekst_dz, rdzen_dz))
    s.akapit(t["cel"])
    tekst_gps, rdzen_gps = gps(rng, jezyk, dms=rng.random() < 0.5)
    s.akapit(t["gps"], gps=Skladnik("k2", "gps", tekst_gps, rdzen_gps))
    s.akapit(t["sasiad"], sasiad_pelne=sasiad.pelne,
             **{k: p(k, sasiad.o.plec) for k in ("obecny", "sasiada") if "{" + k + "}" in t["sasiad"]})
    s.akapit(t["koniec"], rzecz=rzecz.pelne, **({"sporzadzil": p("sporzadzil", rzecz.o.plec)} if jezyk == "pl" else {}))
    return _wynik(s, typ, ctx, gen, P.POSREDNIE_DZIALKA_GPS, [cel])


GENERATORY: dict[str, dict[tuple[str, str], Generator_H5]] = {
    P.POSREDNIE_FUNKCJA_FIRMA: {(j, "notatka_kontrahent"): _z_probami(_buduj_funkcja) for j in JEZYKI},
    P.POSREDNIE_RZADKA_CHOROBA: {(j, t): _z_probami(_buduj_choroba) for j in JEZYKI
                                 for t in ("wniosek_kadrowy", "notatka_szkolna")},
    P.POSREDNIE_WIEK_MIEJSCOWOSC: {(j, "notatka_zdarzenie"): _z_probami(_buduj_wiek) for j in JEZYKI},
    P.POSREDNIE_DZIALKA_GPS: {(j, "protokol_ogledzin"): _z_probami(_buduj_dzialka) for j in JEZYKI},
}
