"""Długie dokumenty (spec §11 pkt 5, zadanie H2): `skroty_po_pelnym`, `granica_okna`, `dlugie_listy_osob`.

* `skroty_po_pelnym` – opinia/pismo o 10–25 tys. znaków (> 3 okna modelu): pełne imię i nazwisko stron raz, dalej
  „Pan K.”, „p. Kowalski”, „J.K.”, „Powód”. Gold: każde odniesienie zawierające nazwisko albo inicjał (OSOBA/INICJALY,
  `encja` = strona); rola procesowa („Powód”) NIE jest gold. Wzorzec inicjałów nie występuje poza spanami gold („C.” w „k.c.”),
  a inicjały stron się nie pokrywają (`trudne_wspolne.inicjaly_jednoznaczne`; inaczej kolejne ziarno).
* `granica_okna` – te same dokumenty, ale wartości gold (OSOBA, PESEL/ID, rachunek, adres, e-mail, telefon) stoją tak, że
  ICH POCZĄTEK leży w odległości <= `TOLERANCJA_ZNAKI` od granicy okna modelu w tekście płaskim (`.txt` korpusu): okna
  mają `GRANICA_OKNA_ZNAKI` znaków i zakładkę `ZAKLADKA_ZNAKI`, czyli [0, 2560), [2112, 4672)…; granice to początki
  okien 2112·k (k >= 1) i końce okien 2112·k + 2560 (k >= 0). Co najmniej dwie wartości zaczynają się PRZED granicą i ją
  przecinają. Położenie liczone jest po finalnym tekście (nagłówek + akapity, bez metadanych); wypełniacz to akapity
  z realistycznych zdań-formułek (`trudne_wypelniacz`), dobranych tak, by początek wartości trafił w pasmo
  ±`TOLERANCJA_ZNAKI` (albo przed granicą – dla wartości przecinających). W `cechy` wartości: `granica_okna`,
  `granica_offset:<±n>` (początek wartości minus granica), `granica_typ:<poczatek_okna|koniec_okna>`, `przecina_granice`.
* `dlugie_listy_osob` – listy 100–150 osób (lista obecności, wykaz wspólników, załącznik z pracownikami) jako tabela
  (DOCX, PDF, XLSX); każda osoba to osobna wartość gold (`encja` = osoba), adresy, e-maile i identyfikatory tylko dla części.
"""
from __future__ import annotations

import random
import re

from . import przypadki as P
from .budowa import Kontekst
from .dane.wspolne import BazowyGenerator
from .odmiana_pl import odmien
from .skladacz import G, Skladacz
from .trudne_wspolne import JEZYKI, Os, data_gold, inicjaly, nowy_kontekst, osoba, rng_h2, z_inicjalami_jednoznacznymi
from .trudne_wypelniacz import akapit_w_pasie

_ZNACZNIK = re.compile(r"\{(R?[AB])(?:_([a-z]+))?\}")
_HONORYFIKATY_PL = {"mian": "Pan", "dop": "Pana", "cel": "Panu", "bier": "Pana", "narz": "Panem", "msc": "Panu"}
_HONORYFIKATY_PL_K = {"mian": "Pani", "dop": "Pani", "cel": "Pani", "bier": "Panią", "narz": "Panią", "msc": "Pani"}

# ----------------------------------------------------------------------------- kity językowe
#: Role procesowe: język -> (rola A [mężczyzna], rola B [kobieta]); PL ma odmianę w przypadkach.
_ROLE: dict[str, tuple] = {
    "pl": ({"mian": "Powód", "dop": "Powoda", "cel": "Powodowi", "bier": "Powoda", "narz": "Powodem", "msc": "Powodzie"},
           {"mian": "Pozwana", "dop": "Pozwanej", "cel": "Pozwanej", "bier": "Pozwaną", "narz": "Pozwaną", "msc": "Pozwanej"}),
    "en": ("the Claimant", "the Defendant"),
    # DE: mian/gen/dat/akk z rodzajnikiem; FR i ES: mian oraz frazy z przyimkiem („du/au demandeur”, „del/al demandante”)
    "de": ({"mian": "der Kläger", "gen": "des Klägers", "dat": "dem Kläger", "akk": "den Kläger"},
           {"mian": "die Beklagte", "gen": "der Beklagten", "dat": "der Beklagten", "akk": "die Beklagte"}),
    "es": ({"mian": "el demandante", "de": "del demandante", "a": "al demandante"},
           {"mian": "la demandada", "de": "de la demandada", "a": "a la demandada"}),
    "fr": ({"mian": "le demandeur", "de": "du demandeur", "a": "au demandeur"},
           {"mian": "la défenderesse", "de": "de la défenderesse", "a": "à la défenderesse"}),
}
#: Honoryfik przed nazwiskiem (M, K) – poza PL (PL: „p.”, „Pan/Pani”).
_HONORYFIK: dict[str, tuple[str, str]] = {"en": ("Mr", "Ms"), "de": ("Herr", "Frau"), "es": ("D.", "Dña."), "fr": ("M.", "Mme")}
_TYTUL: dict[str, str] = {"pl": "OPINIA PRAWNA w sprawie sporu wynikającego z umowy o roboty budowlane",
                          "en": "LEGAL OPINION on the dispute arising from the construction contract",
                          "de": "RECHTSGUTACHTEN zum Streit aus dem Bauvertrag",
                          "es": "DICTAMEN JURÍDICO sobre el litigio derivado del contrato de obra",
                          "fr": "CONSULTATION JURIDIQUE sur le litige né du contrat d'entreprise"}
_WSTEP: dict[str, str] = {
    "pl": "Niniejsza opinia dotyczy sporu między {A} (dalej: „Powód”) a {B} (dalej: „Pozwana”).",
    "en": "This opinion concerns the dispute between {A} (hereinafter: the “Claimant”) and {B} (hereinafter: the “Defendant”).",
    "de": "Dieses Gutachten betrifft den Streit zwischen {A} (nachstehend: der „Kläger“) und {B} (nachstehend: die „Beklagte“).",
    "es": "El presente dictamen se refiere al litigio entre {A} (en adelante: el «demandante») y {B} (en adelante: la «demandada»).",
    "fr": "La présente consultation concerne le litige opposant {A} (ci-après : le « demandeur ») à {B} (ci-après : la « défenderesse »).",
}
_SEKCJE: dict[str, tuple[str, ...]] = {
    "pl": ("I. Stan faktyczny", "II. Stanowiska stron", "III. Ocena materiału dowodowego", "IV. Ocena prawna", "V. Wnioski"),
    "en": ("I. Facts", "II. The parties' positions", "III. Assessment of the evidence", "IV. Legal assessment", "V. Conclusions"),
    "de": ("I. Sachverhalt", "II. Standpunkte der Parteien", "III. Würdigung der Beweise", "IV. Rechtliche Würdigung", "V. Ergebnis"),
    "es": ("I. Hechos", "II. Posiciones de las partes", "III. Valoración de la prueba", "IV. Valoración jurídica", "V. Conclusiones"),
    "fr": ("I. Les faits", "II. Les positions des parties", "III. Appréciation des preuves", "IV. Appréciation juridique", "V. Conclusions"),
}
#: Zdania z odniesieniami do stron. Znaczniki: {A}/{B} osoba (albo rola procesowa), {RA}/{RB} rola; przypadek po `_`:
#: PL: dop, cel, bier, narz, msc; DE: gen, dat, akk (osoba: „Herrn K.”; rola: „dem Kläger”, „der Beklagten”);
#: FR/ES: `_de`, `_a` – FRAZA Z PRZYIMKIEM („du demandeur”/„de M. Dupont”, „al demandante”/„a D. Pérez”). Przyimki
#: FR/ES i DE (gen) stoją więc w znaczniku, nie w szablonie; DE `von`/`mit` stoją w szablonie przed `_dat`.
_NARRACJA: dict[str, tuple[str, ...]] = {
    "pl": ("Zdaniem {RA_dop} {B} nie wykonała zobowiązania w umówionym terminie, co skutkowało powstaniem szkody po jego stronie.",
           "{A} wskazuje, że wielokrotnie wzywał {B_bier} do wykonania umowy, jednak bez rezultatu.",
           "{B} kwestionuje roszczenie {A_dop} i wnosi o jego oddalenie w całości.",
           "W ocenie {RB_dop} brak jest podstaw do uwzględnienia żądania, gdyż {A} nie wykazał poniesienia szkody.",
           "Należy zauważyć, że {RA} nie przedstawił dowodów potwierdzających wysokość dochodzonej należności.",
           "Z zeznań świadków wynika, że {A} był obecny przy odbiorze prac, a {B} nie zgłaszała wówczas zastrzeżeń.",
           "Pełnomocnik {RB_dop} podniósł zarzut przedawnienia roszczenia.",
           "Rozmowy ugodowe z udziałem {A_dop} i {B_dop} nie doprowadziły do zawarcia porozumienia.",
           "Zgodnie z twierdzeniami {RA_dop} umowa została zawarta w formie pisemnej, co potwierdza dołączony dokument.",
           "{RB} nie zaprzeczyła, że otrzymała od {A_dop} zaliczkę na poczet wynagrodzenia.",
           "Uznać trzeba, że {A_bier} i {B_bier} łączyła umowa o charakterze rezultatu, a nie starannego działania.",
           "W piśmie procesowym {B} podniosła, że z {A_narz} uzgodniono zmianę terminu wykonania prac."),
    "en": ("In the view of {RA}, {B} failed to perform the obligation by the agreed date, which caused loss to {A}.",
           "{A} states that he repeatedly called on {B} to perform the contract, without result.",
           "{B} disputes the claim brought by {A} and asks for it to be dismissed in its entirety.",
           "According to {RB}, there is no basis for upholding the claim because {A} has not shown that any loss was suffered.",
           "It should be noted that {RA} has not produced evidence confirming the amount claimed.",
           "The witnesses' evidence shows that {A} was present at the handover of the works and that {B} raised no objections at the time.",
           "Counsel for {RB} raised a limitation defence.",
           "Settlement talks involving {A} and {B} did not lead to an agreement.",
           "As {RA} asserts, the contract was concluded in writing, which the attached document confirms.",
           "It is not disputed that {RB} received an advance payment from {A}.",
           "It must be concluded that {A} and {B} were bound by a contract for a result and not for a duty of care.",
           "In her statement of case {B} submitted that a change to the completion date had been agreed with {A}."),
    "de": ("Nach Auffassung {RA_gen} hat {B} die Verpflichtung nicht fristgerecht erfüllt, wodurch {A_dat} ein Schaden entstanden ist.",
           "{A} trägt vor, er habe {B_akk} mehrfach zur Vertragserfüllung aufgefordert, jedoch ohne Erfolg.",
           "{B} bestreitet den Anspruch von {A_dat} und beantragt, ihn vollständig abzuweisen.",
           "Nach Ansicht {RB_gen} gibt es keinen Grund, der Klage stattzugeben, da {A} keinen Schaden nachgewiesen hat.",
           "Zu beachten ist, dass {RA} keine Beweise für die Höhe der geltend gemachten Forderung vorgelegt hat.",
           "Aus den Zeugenaussagen ergibt sich, dass {A} bei der Abnahme der Arbeiten anwesend war und {B} damals keine Mängel rügte.",
           "Der Prozessbevollmächtigte {RB_gen} erhob die Einrede der Verjährung.",
           "Die Vergleichsgespräche mit {A_dat} und {B_dat} führten zu keiner Einigung.",
           "Nach dem Vortrag {RA_gen} wurde der Vertrag schriftlich geschlossen, was das beigefügte Dokument bestätigt.",
           "Unstreitig hat {RB} von {A_dat} einen Vorschuss erhalten.",
           "Es ist davon auszugehen, dass {A_akk} und {B_akk} ein Vertrag mit Erfolgsbezug verband und kein reiner Dienstvertrag.",
           "Im Schriftsatz machte {B} geltend, mit {A_dat} sei eine Verlängerung der Ausführungsfrist vereinbart worden."),
    "es": ("En opinión {RA_de}, {B} no cumplió la obligación en el plazo pactado, lo que causó un perjuicio {A_a}.",
           "{A} afirma que requirió en varias ocasiones {B_a} el cumplimiento del contrato, sin resultado.",
           "{B} impugna la pretensión {A_de} y solicita su desestimación íntegra.",
           "A juicio {RB_de}, no hay motivo para estimar la demanda, pues {A} no ha acreditado perjuicio alguno.",
           "Cabe señalar que {RA} no ha aportado pruebas que confirmen la cuantía reclamada.",
           "De las declaraciones de los testigos resulta que {A} estuvo presente en la recepción de las obras y que {B} no formuló reservas entonces.",
           "El abogado {RB_de} alegó la prescripción de la acción.",
           "Las negociaciones con {A} y {B} no condujeron a ningún acuerdo.",
           "Según afirma {RA}, el contrato se celebró por escrito, lo que confirma el documento adjunto.",
           "No se discute que {RB} recibió {A_de} un anticipo a cuenta del precio.",
           "Debe concluirse que {A} y {B} estaban vinculados por un contrato de resultado y no de medios.",
           "En su escrito {B} sostuvo que con {A} se había acordado un cambio del plazo de ejecución."),
    "fr": ("Selon {RA}, {B} n'a pas exécuté son obligation dans le délai convenu, ce qui a causé un préjudice {A_a}.",
           "{A} indique qu'il a mis {B} en demeure à plusieurs reprises d'exécuter le contrat, sans résultat.",
           "{B} conteste la demande {A_de} et conclut à son rejet intégral.",
           "Pour {RB}, rien ne justifie de faire droit à la demande, car {A} n'a pas démontré l'existence d'un préjudice.",
           "Il convient de relever que {RA} n'a produit aucune preuve du montant réclamé.",
           "Il ressort des témoignages que {A} était présent lors de la réception des travaux et que {B} n'a alors formulé aucune réserve.",
           "L'avocat {RB_de} a soulevé la prescription de l'action.",
           "Les pourparlers entre {A} et {B} n'ont abouti à aucun accord.",
           "Selon {RA}, le contrat a été conclu par écrit, ce que confirme la pièce jointe.",
           "Il est constant que {RB} a reçu {A_de} un acompte sur le prix.",
           "Il faut en conclure que {A} et {B} étaient liés par une obligation de résultat et non de moyens.",
           "Dans ses conclusions, {B} a soutenu qu'un report du délai d'exécution avait été convenu avec {A}."),
}
_NEUTRALNE: dict[str, tuple[str, ...]] = {
    "pl": ("Zgodnie z ogólnymi zasadami odpowiedzialności kontraktowej dłużnik obowiązany jest naprawić szkodę wynikłą z niewykonania zobowiązania.",
           "Ciężar udowodnienia faktu spoczywa na osobie, która z tego faktu wywodzi skutki prawne.",
           "Ocena materiału dowodowego dokonywana jest swobodnie, z uwzględnieniem zasad doświadczenia życiowego i logiki.",
           "Wysokość szkody ustala się, uwzględniając cenę rynkową usług porównywalnych w czasie wykonywania umowy.",
           "Strony mogą w każdym czasie zawrzeć ugodę, która wyłącza dalsze dochodzenie roszczeń objętych jej treścią.",
           "Dokumentacja zgromadzona w aktach sprawy obejmuje korespondencję stron, protokoły odbioru oraz zestawienia kosztów.",
           "Na etapie postępowania dowodowego dopuszczono dowód z opinii biegłego z zakresu budownictwa.",
           "Przepisy prawa nie wymagają zachowania szczególnej formy dla ważności tego rodzaju oświadczeń.",
           "Odsetki za opóźnienie przysługują od dnia następującego po upływie terminu spełnienia świadczenia.",
           "Wykonawca odpowiada za wady robót niezależnie od tego, czy ujawniły się one przed odbiorem, czy po nim."),
    "en": ("Under the general rules of contractual liability the debtor must make good the loss resulting from non-performance.",
           "The burden of proving a fact lies on the person who derives legal consequences from it.",
           "The evidence is assessed freely, having regard to the rules of experience and logic.",
           "The amount of the loss is determined by reference to the market price of comparable services at the time of performance.",
           "The parties may settle at any time, and a settlement excludes further pursuit of the claims it covers.",
           "The case file contains the correspondence of the parties, the handover protocols and the statements of costs.",
           "At the evidentiary stage an expert opinion in the field of construction was admitted.",
           "The law does not require any particular form for the validity of statements of this kind.",
           "Interest for delay is due from the day following the expiry of the time for performance.",
           "The contractor is liable for defects in the works whether they appear before or after handover."),
    "de": ("Nach den allgemeinen Regeln der vertraglichen Haftung hat der Schuldner den aus der Nichterfüllung entstandenen Schaden zu ersetzen.",
           "Die Beweislast für eine Tatsache trägt derjenige, der aus ihr Rechtsfolgen herleitet.",
           "Die Beweise werden frei gewürdigt, unter Berücksichtigung der Erfahrungssätze und der Denkgesetze.",
           "Die Höhe des Schadens bemisst sich nach dem Marktpreis vergleichbarer Leistungen zum Zeitpunkt der Vertragserfüllung.",
           "Die Parteien können jederzeit einen Vergleich schließen, der die weitere Verfolgung der erfassten Ansprüche ausschließt.",
           "Die Akte enthält den Schriftwechsel der Parteien, die Abnahmeprotokolle und die Kostenaufstellungen.",
           "Im Beweisverfahren wurde ein Sachverständigengutachten aus dem Bereich des Bauwesens eingeholt.",
           "Das Gesetz verlangt für die Wirksamkeit derartiger Erklärungen keine besondere Form.",
           "Verzugszinsen stehen ab dem Tag nach Ablauf der Leistungsfrist zu.",
           "Der Unternehmer haftet für Mängel der Arbeiten, gleichviel ob sie vor oder nach der Abnahme zutage treten."),
    "es": ("Conforme a las reglas generales de la responsabilidad contractual, el deudor debe reparar el daño derivado del incumplimiento.",
           "La carga de probar un hecho recae sobre quien deriva de él consecuencias jurídicas.",
           "La prueba se valora libremente, conforme a las reglas de la experiencia y de la lógica.",
           "La cuantía del daño se determina atendiendo al precio de mercado de servicios comparables en el momento de la ejecución.",
           "Las partes pueden transigir en cualquier momento, y la transacción excluye la reclamación de las pretensiones comprendidas en ella.",
           "Las actuaciones incluyen la correspondencia de las partes, las actas de recepción y los estados de costes.",
           "En fase probatoria se admitió un dictamen pericial en materia de construcción.",
           "La ley no exige forma especial para la validez de este tipo de declaraciones.",
           "Los intereses de demora se devengan desde el día siguiente al vencimiento del plazo de cumplimiento.",
           "El contratista responde de los defectos de la obra, aparezcan antes o después de la recepción."),
    "fr": ("Selon les règles générales de la responsabilité contractuelle, le débiteur doit réparer le dommage résultant de l'inexécution.",
           "La charge de la preuve d'un fait incombe à celui qui en tire des conséquences juridiques.",
           "Les preuves sont appréciées librement, au regard des règles de l'expérience et de la logique.",
           "Le montant du préjudice est fixé d'après le prix du marché de prestations comparables au moment de l'exécution.",
           "Les parties peuvent transiger à tout moment, la transaction excluant la poursuite des prétentions qu'elle couvre.",
           "Le dossier comprend la correspondance des parties, les procès-verbaux de réception et les états de frais.",
           "Au stade de l'instruction, une expertise en matière de construction a été ordonnée.",
           "La loi n'impose aucune forme particulière pour la validité de ce type de déclarations.",
           "Les intérêts de retard sont dus à compter du lendemain de l'expiration du délai d'exécution.",
           "L'entrepreneur répond des vices de l'ouvrage, qu'ils apparaissent avant ou après la réception."),
}

# ----------------------------------------------------------------------------- odniesienia do stron
_SAMOGLOSKI_FR = "aeiouyàâäéèêëîïôöûüAEIOUYÀÂÄÉÈÊËÎÏÔÖÛÜ"


def _przyimek(jezyk: str, przyp: str, nastepny: str) -> str:
    """Przyimek frazy „A_de”/„A_a” przed osobą (FR: „de”→„d'” przed samogłoską; ES: „de”, „a”). `przyp` mian = brak."""
    if przyp == "de":
        return "d'" if jezyk == "fr" and nastepny[:1] in _SAMOGLOSKI_FR else "de "
    if przyp == "a":
        return "à " if jezyk == "fr" else "a "
    return ""


def _odniesienie(jezyk: str, os_: Os, rola: str, styl: str, przyp: str, rola_txt: str) -> tuple[str, G | None]:
    """(tekst przed wartością gold, wartość gold albo None). Rola procesowa jest zwykłym tekstem (None)."""
    o = os_.o
    k = o.plec == "K"
    if styl == "rola":
        return rola_txt, None
    ini = inicjaly(o, kropki=True)
    if styl == "inicjaly":
        return "", os_.g("inicjaly", ini, "INICJALY", ("skrot",))
    if jezyk == "pl":
        if styl == "nazw":
            return "", os_.g("nazwisko", odmien("", o.nazwisko, o.plec, przyp), cechy=("skrot",))
        if styl == "p_nazw":
            return "p. ", os_.g("nazwisko", odmien("", o.nazwisko, o.plec, przyp), cechy=("skrot",))
        return (_HONORYFIKATY_PL_K if k else _HONORYFIKATY_PL)[przyp] + " ", os_.g("inicjal", o.nazwisko[0] + ".", "INICJALY", ("skrot",))
    hon = _HONORYFIK[jezyk][1 if k else 0]
    if jezyk == "de" and przyp in ("gen", "dat", "akk") and not k:
        hon = "Herrn"
    if styl == "nazw":
        return "", os_.g("nazwisko", o.nazwisko, cechy=("skrot",))
    if styl == "p_nazw":
        return hon + " ", os_.g("nazwisko", o.nazwisko, cechy=("skrot",))
    return hon + " ", os_.g("inicjal", o.nazwisko.split()[0][0] + ".", "INICJALY", ("skrot",))


_WAGI_STYLI = (("rola", 4), ("nazw", 2), ("p_nazw", 3), ("pan_inicjal", 3), ("inicjaly", 2))


class _Narrator:
    """Składa akapity narracyjne z odniesieniami do stron A i B (po pierwszym pełnym wystąpieniu: skróty i role)."""

    def __init__(self, s: Skladacz, jezyk: str, a: Os, b: Os, rng: random.Random) -> None:
        self.s, self.jezyk, self.a, self.b, self.rng = s, jezyk, a, b, rng
        self.licznik = 0

    def _role(self, symbol: str, przyp: str) -> str:
        r = _ROLE[self.jezyk][0 if symbol == "RA" else 1]
        return r[przyp] if isinstance(r, dict) else r       # brak przypadku w tabeli = KeyError (błąd szablonu)

    def zdanie(self, szablon: str, stale_style: dict[str, str] | None = None) -> tuple[str, dict[str, object]]:
        sloty: dict[str, object] = {}

        def podmien(m: re.Match) -> str:
            symbol, przyp = m.group(1), m.group(2) or "mian"
            poczatek = m.start() == 0
            if symbol.startswith("R"):
                r = self._role(symbol, przyp)
                return r[0].upper() + r[1:] if poczatek else r
            os_, rola = (self.a, "RA") if symbol == "A" else (self.b, "RB")
            styl = self.rng.choices([x for x, _ in _WAGI_STYLI], [w for _, w in _WAGI_STYLI])[0]
            if poczatek and self.jezyk == "pl" and styl == "p_nazw":
                styl = "nazw"                        # „p. Kowalski” nie zaczyna zdania
            przypadek = przyp if self.jezyk != "en" else "mian"
            if self.jezyk == "fr" and przypadek == "de" and styl in ("nazw", "inicjaly") and \
                    (os_.o.nazwisko if styl == "nazw" else os_.o.imie)[0] in "Hh":
                styl = "p_nazw"                      # „d'Henri” vs „de Hugo” – przy h unikamy gołego nazwiska/inicjałów
            przed, g = _odniesienie(self.jezyk, os_, rola, styl, przypadek, self._role(rola, przypadek))
            if g is None:
                return przed[0].upper() + przed[1:] if poczatek else przed
            if self.jezyk in ("fr", "es") and przypadek in ("de", "a"):
                przed = _przyimek(self.jezyk, przypadek, przed or g.tekst) + przed
            self.licznik += 1
            nazwa = f"g{self.licznik}"
            sloty[nazwa] = g
            return f"{przed}{{{nazwa}}}"
        tekst = _ZNACZNIK.sub(podmien, szablon)
        koncowy = re.search(r"\{(g\d+)\}\.$", tekst)
        if koncowy and sloty[koncowy.group(1)].tekst.endswith("."):
            tekst = tekst[:-1]                       # „Pan K.” na końcu zdania: jedna kropka, nie „K..”
        return tekst, sloty

    def akapit(self, liczba_zdan: int | None = None, neutralne: float = 0.35) -> str:
        """Dodaje akapit (1–3 zdania narracyjne + zdania neutralne); zwraca jego tekst bez gold-owych wartości."""
        n = liczba_zdan or self.rng.randint(2, 4)
        zdania, sloty = [], {}
        uzyte: set[str] = set()          # w jednym akapicie zdania się nie powtarzają
        for _ in range(n):
            pula = _NEUTRALNE[self.jezyk] if self.rng.random() < neutralne else _NARRACJA[self.jezyk]
            wybrane = self.rng.choice([z for z in pula if z not in uzyte] or list(pula))
            uzyte.add(wybrane)
            t, sl = self.zdanie(wybrane)
            zdania.append(t)
            sloty |= sl
        tekst = " ".join(zdania)
        self.s.akapit(tekst, **sloty)
        return tekst

    def probny_akapit(self, maks: int) -> bool:
        """Dodaje akapit tylko jeśli jego tekst płaski (z separatorem) nie przekracza `maks` znaków; w przeciwnym razie False."""
        stan = (len(self.s.elementy), self.s._dlugosc, dict(self.s._licznik), self.licznik)
        self.akapit(self.rng.randint(1, 3))
        if self.s._dlugosc - stan[1] > maks:
            del self.s.elementy[stan[0]:]
            self.s._dlugosc, self.s._licznik, self.licznik = stan[1], type(self.s._licznik)(stan[2]), stan[3]
            return False
        return True


def _para_stron(gen: BazowyGenerator, ctx: Kontekst, jezyk: str) -> tuple[Os, Os]:
    return Os("a", osoba(gen, ctx, "M"), jezyk), Os("b", osoba(gen, ctx, "K"), jezyk)


def _wstep(s: Skladacz, jezyk: str, a: Os, b: Os) -> None:
    """Tytuł i akapit wprowadzający z PEŁNYM imieniem i nazwiskiem stron (jedyne pełne wystąpienie w treści)."""
    s.naglowek(_TYTUL[jezyk])
    if jezyk == "pl":      # „między Janem Kowalskim … a Anną Nowak”
        ga = a.g("pelne", odmien(a.o.imie, a.o.nazwisko, "M", "narz"), cechy=("przypadek_zalezny",))
        gb = b.g("pelne", odmien(b.o.imie, b.o.nazwisko, "K", "narz"), cechy=("przypadek_zalezny",))
    else:
        ga, gb = a.pelne, b.pelne
    s.akapit(_WSTEP[jezyk].replace("{A}", "{ga}").replace("{B}", "{gb}"), ga=ga, gb=gb)


# ----------------------------------------------------------------------------- 7. skroty_po_pelnym
def _buduj_skroty(jezyk: str, typ: str, seed: int) -> tuple:
    gen, ctx = nowy_kontekst(jezyk, seed)
    rng = rng_h2(seed, "skroty")
    a, b = _para_stron(gen, ctx, jezyk)
    s = Skladacz(jezyk)
    _wstep(s, jezyk, a, b)
    cel = rng.randint(10_000, 25_000)
    narr = _Narrator(s, jezyk, a, b, rng)
    sekcje = list(_SEKCJE[jezyk])
    par_na_sekcje = max(3, int(cel / 700 / len(sekcje)))
    for naglowek in sekcje:
        s.akapit(naglowek)
        for _ in range(par_na_sekcje):
            narr.akapit()
    while s._dlugosc < cel:
        narr.akapit()
    return s.wynik(typ, ctx), gen, {}


# ----------------------------------------------------------------------------- 8. granica_okna
def granice_okien(dlugosc: int) -> list[tuple[int, str]]:
    """Granice okien modelu dla tekstu o danej długości: (położenie, `poczatek_okna`|`koniec_okna`), rosnąco.
    Okna mają `GRANICA_OKNA_ZNAKI` znaków i zakładkę `ZAKLADKA_ZNAKI`: [0, 2560), [2112, 4672)…"""
    krok = P.GRANICA_OKNA_ZNAKI - P.ZAKLADKA_ZNAKI
    wynik = []
    k = 0
    while k * krok < dlugosc:
        if k >= 1:
            wynik.append((k * krok, "poczatek_okna"))
        if k * krok + P.GRANICA_OKNA_ZNAKI < dlugosc:
            wynik.append((k * krok + P.GRANICA_OKNA_ZNAKI, "koniec_okna"))
        k += 1
    return sorted(wynik)


def najblizsza_granica(start: int, dlugosc: int) -> tuple[int, str]:
    """Najbliższa granica okna od `start` (położenie, typ)."""
    return min(granice_okien(max(dlugosc, start + 3 * P.GRANICA_OKNA_ZNAKI)), key=lambda g: abs(g[0] - start))


def pozycja_przy_granicy(start: int, koniec: int, dlugosc: int) -> tuple[int, str, int, bool]:
    """(granica, typ, offset = start - granica, czy wartość [start, koniec) ją przecina) dla najbliższej granicy."""
    g, typ = najblizsza_granica(start, dlugosc)
    return g, typ, start - g, start < g < koniec


_ETYKIETY_WARTOSCI: dict[str, dict[str, str]] = {
    "pl": {"osoba": "Strona postępowania", "id": "Numer PESEL", "rachunek": "Rachunek bankowy",
           "adres": "Adres do doręczeń", "email": "Adres e-mail", "telefon": "Telefon kontaktowy"},
    "en": {"osoba": "Party to the proceedings", "id": "National Insurance number", "rachunek": "Bank account",
           "adres": "Address for service", "email": "E-mail address", "telefon": "Contact telephone"},
    "de": {"osoba": "Verfahrensbeteiligter", "id": "Steuer-Identifikationsnummer", "rachunek": "Bankkonto",
           "adres": "Zustellanschrift", "email": "E-Mail-Adresse", "telefon": "Telefon"},
    "es": {"osoba": "Parte en el procedimiento", "id": "DNI", "rachunek": "Cuenta bancaria",
           "adres": "Domicilio a efectos de notificación", "email": "Correo electrónico", "telefon": "Teléfono de contacto"},
    "fr": {"osoba": "Partie à la procédure", "id": "Numéro de sécurité sociale", "rachunek": "Compte bancaire",
           "adres": "Adresse de signification", "email": "Adresse électronique", "telefon": "Téléphone"},
}


def _pole_wartosci(rodzaj: str, os_: Os) -> G:
    return {"osoba": os_.pelne, "id": os_.id, "rachunek": os_.rachunek, "adres": os_.adres, "email": os_.email,
            "telefon": os_.telefon}[rodzaj]


#: Ostatni akapit wypełniacza ma najwyżej tyle znaków (dłuższy odcinek wypełnia najpierw narracja); po narracji
#: zostaje co najmniej `_MIN_RESZTA` znaków na ostatni akapit.
_MAKS_WYPELNIACZ = 700
_MIN_RESZTA = 160


def _buduj_granica(jezyk: str, typ: str, seed: int) -> tuple:
    gen, ctx = nowy_kontekst(jezyk, seed)
    rng = rng_h2(seed, "granica")
    a, b = _para_stron(gen, ctx, jezyk)
    s = Skladacz(jezyk)
    _wstep(s, jezyk, a, b)
    narr = _Narrator(s, jezyk, a, b, rng)
    # granice do wykorzystania: z pierwszych 9; co najmniej 4, nie bliżej niż 400 znaków od siebie
    kandydaci = [g for g in granice_okien(14_000) if g[0] < 8_800]
    rng.shuffle(kandydaci)
    wybrane: list[tuple[int, str]] = []
    ile = rng.randint(4, 6)
    for g in kandydaci:
        if all(abs(g[0] - w[0]) >= 400 for w in wybrane):
            wybrane.append(g)
        if len(wybrane) == ile:
            break
    wybrane.sort()
    rodzaje = ["osoba", "id", "rachunek", "adres", "email", "telefon"]
    rng.shuffle(rodzaje)
    et = _ETYKIETY_WARTOSCI[jezyk]
    przecinajace = set(rng.sample(range(len(wybrane)), 2))      # co najmniej dwie wartości zaczynają się przed granicą
    ostatni_koniec = 0
    for i, (granica, gtyp) in enumerate(wybrane):
        rodzaj = rodzaje[i % len(rodzaje)]
        os_ = a if i % 2 == 0 else b
        wart = _pole_wartosci(rodzaj, os_)
        if i in przecinajace:                    # początek przed granicą, a wartość sięga za nią
            lo_s, hi_s = granica - min(P.TOLERANCJA_ZNAKI - 5, len(wart.tekst) - 2), granica - 2
        else:
            lo_s, hi_s = granica - P.TOLERANCJA_ZNAKI, granica + P.TOLERANCJA_ZNAKI
        etykieta = f"{et[rodzaj]}: "
        # pasmo długości wypełniacza (każdy akapit = długość + 1 separator)
        lo = lo_s - len(etykieta) - s.start_nastepnego
        hi = hi_s - len(etykieta) - s.start_nastepnego
        if hi < 0:
            continue                             # granica zbyt blisko poprzedniej wartości (nie powinno się zdarzyć)
        while hi > _MAKS_WYPELNIACZ:
            przed = s.start_nastepnego
            if not narr.probny_akapit(hi - _MIN_RESZTA):         # narracja, o ile nie zostawi zbyt wąskiej reszty
                s.akapit(akapit_w_pasie(rng, jezyk, 200, 320))   # akapit narracji za długi – formułki
            zuzyto = s.start_nastepnego - przed
            lo, hi = lo - zuzyto, hi - zuzyto
        s.akapit(akapit_w_pasie(rng, jezyk, max(lo, 60) - 1, hi - 1))
        start = s.start_nastepnego + len(etykieta)
        assert lo_s <= start <= hi_s, (start, lo_s, hi_s)
        g_ok, g_typ, offset, przecina = pozycja_przy_granicy(start, start + len(wart.tekst), 14_000)
        cechy = wart.cechy + ("granica_okna", f"granica_offset:{offset:+d}", f"granica_typ:{g_typ}") + (
            ("przecina_granice",) if przecina else ())
        s.akapit(etykieta + "{w}", w=G(wart.tekst, wart.kategoria, wart.klucz, wart.encja, cechy))
        ostatni_koniec = start + len(wart.tekst)
    while s._dlugosc < ostatni_koniec + 600:      # reszta dokumentu: narracja
        narr.akapit()
    return s.wynik(typ, ctx), gen, {}


# ----------------------------------------------------------------------------- 9. dlugie_listy_osob
_LISTY: dict[str, dict] = {
    "pl": {"lista_obecnosci": ("Lista obecności na walnym zgromadzeniu", "Lp.", "Imię i nazwisko", "Adres e-mail", "Podpis"),
           "wykaz_wspolnikow": ("Wykaz wspólników spółki", "Lp.", "Wspólnik", "Adres", "PESEL", "Liczba udziałów"),
           "zalacznik_pracownicy": ("Załącznik nr 1 – wykaz pracowników objętych układem", "Lp.", "Pracownik", "PESEL", "Stanowisko", "Adres"),
           "intro": "Dokument sporządzono w dniu {d} dla podmiotu {firma}", "stanowiska": (("referent", "referentka"), ("specjalista", "specjalistka"), ("kierownik zmiany", "kierowniczka zmiany"),
                       ("magazynier", "magazynierka"), ("księgowy", "księgowa"), ("technik", "technik")),
           "koniec": "Listę sporządził i zatwierdził {pelne}"},
    "en": {"lista_obecnosci": ("Attendance list for the general meeting", "No.", "Name", "E-mail address", "Signature"),
           "wykaz_wspolnikow": ("Register of the company's members", "No.", "Member", "Address", "National Insurance no.", "Number of shares"),
           "zalacznik_pracownicy": ("Schedule 1 – employees covered by the agreement", "No.", "Employee", "National Insurance no.", "Position", "Address"),
           "intro": "This document was prepared on {d} for {firma}", "stanowiska": tuple((x, x) for x in ("clerk", "specialist", "shift supervisor", "storekeeper", "accountant", "technician")),
           "koniec": "The list was prepared and approved by {pelne}"},
    "de": {"lista_obecnosci": ("Anwesenheitsliste zur Gesellschafterversammlung", "Nr.", "Name", "E-Mail-Adresse", "Unterschrift"),
           "wykaz_wspolnikow": ("Gesellschafterliste", "Nr.", "Gesellschafter", "Anschrift", "Steuer-ID", "Anzahl der Anteile"),
           "zalacznik_pracownicy": ("Anlage 1 – vom Tarifvertrag erfasste Beschäftigte", "Nr.", "Beschäftigter", "Steuer-ID", "Position", "Anschrift"),
           "intro": "Dieses Dokument wurde am {d} für {firma} erstellt", "stanowiska": (("Sachbearbeiter", "Sachbearbeiterin"), ("Fachkraft", "Fachkraft"), ("Schichtleiter", "Schichtleiterin"),
                       ("Lagerist", "Lageristin"), ("Buchhalter", "Buchhalterin"), ("Techniker", "Technikerin")),
           "koniec": "Die Liste wurde von {pelne} erstellt und genehmigt"},
    "es": {"lista_obecnosci": ("Lista de asistentes a la junta general", "N.º", "Nombre y apellidos", "Correo electrónico", "Firma"),
           "wykaz_wspolnikow": ("Libro registro de socios", "N.º", "Socio", "Domicilio", "DNI", "Número de participaciones"),
           "zalacznik_pracownicy": ("Anexo 1 – trabajadores incluidos en el convenio", "N.º", "Trabajador", "DNI", "Puesto", "Domicilio"),
           "intro": "El presente documento se elaboró el {d} para {firma}", "stanowiska": (("auxiliar", "auxiliar"), ("especialista", "especialista"), ("jefe de turno", "jefa de turno"),
                       ("almacenero", "almacenera"), ("contable", "contable"), ("técnico", "técnica")),
           "koniec": "La lista fue elaborada y aprobada por {pelne}"},
    "fr": {"lista_obecnosci": ("Feuille de présence à l'assemblée générale", "N°", "Nom et prénom", "Adresse électronique", "Signature"),
           "wykaz_wspolnikow": ("Registre des associés", "N°", "Associé", "Adresse", "N° de sécurité sociale", "Nombre de parts"),
           "zalacznik_pracownicy": ("Annexe 1 – salariés couverts par l'accord", "N°", "Salarié", "N° de sécurité sociale", "Poste", "Adresse"),
           "intro": "Le présent document a été établi le {d} pour {firma}", "stanowiska": (("employé", "employée"), ("spécialiste", "spécialiste"), ("chef d'équipe", "cheffe d'équipe"),
                       ("magasinier", "magasinière"), ("comptable", "comptable"), ("technicien", "technicienne")),
           "koniec": "La liste a été établie et approuvée par {pelne}"},
}


def _buduj_liste(jezyk: str, typ: str, seed: int) -> tuple:
    gen, ctx = nowy_kontekst(jezyk, seed)
    rng = rng_h2(seed, "lista")
    t = _LISTY[jezyk]
    tytul, *kolumny = t[typ]
    n = rng.randint(100, 150)
    osoby = [Os(f"p{i + 1}", osoba(gen, ctx), jezyk) for i in range(n)]
    firma = gen.firma()
    s = Skladacz(jezyk)
    s.naglowek(tytul)
    # firma raz (intro zawiera już {firma}); bez drugiej kropki po „sp. z o.o.”
    s.akapit(t["intro"] + ("" if firma.nazwa.endswith(".") else "."), d=data_gold(ctx, "dok"),
             firma=G(firma.nazwa, "ORGANIZACJA", "firma.nazwa", "firma"))
    for j, kol in enumerate(kolumny):
        s.komorka(0, 0, j, kol)
    for i, os_ in enumerate(osoby, 1):
        s.komorka(0, i, 0, str(i))
        s.komorka(0, i, 1, "{o}", o=os_.pelne)
        if typ == "lista_obecnosci":
            s.komorka(0, i, 2, "{e}" if rng.random() < 0.4 else "–", e=os_.email)
            s.komorka(0, i, 3, "……………")
        elif typ == "wykaz_wspolnikow":
            s.komorka(0, i, 2, "{a}" if rng.random() < 0.6 else "–", a=os_.adres)
            s.komorka(0, i, 3, "{id}" if rng.random() < 0.4 else "–", id=os_.id)
            s.komorka(0, i, 4, str(rng.randint(1, 400)))
        else:
            s.komorka(0, i, 2, "{id}" if rng.random() < 0.5 else "–", id=os_.id)
            s.komorka(0, i, 3, rng.choice(t["stanowiska"])[0 if os_.o.plec == "M" else 1])       # feminatyw wg płci osoby
            s.komorka(0, i, 4, "{a}" if rng.random() < 0.3 else "–", a=os_.adres)
    s.akapit(t["koniec"] + ".", pelne=rng.choice(osoby).pelne)
    return s.wynik(typ, ctx), gen, {}


# ----------------------------------------------------------------------------- rejestr
GENERATORY: dict[str, dict] = {
    "skroty_po_pelnym": {(j, "opinia_dluga"): z_inicjalami_jednoznacznymi(_buduj_skroty) for j in JEZYKI},
    "granica_okna": {(j, "pismo_dlugie"): _buduj_granica for j in JEZYKI},
    "dlugie_listy_osob": {(j, typ): _buduj_liste for j in JEZYKI
                          for typ in ("lista_obecnosci", "wykaz_wspolnikow", "zalacznik_pracownicy")},
}
