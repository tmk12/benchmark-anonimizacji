"""Wypełniacz długich dokumentów H2 (`granica_okna`): realistyczne zdania-formułki zamiast losowych słów.

Pula zdań każdego języka to formułki typowe dla umów i pism (postanowienia końcowe, doręczenia, poufność…), bez cyfr
i nazw własnych. Formułka ma opcjonalne warianty w nawiasach ostrych: `<a|b|>` = jedna z opcji (pusta opcja dozwolona),
co daje drobne różnice długości (synonimy, opcjonalne wtrącenia). Akapit wypełniacza to kilka RÓŻNYCH formułek
(w jednym akapicie żadna się nie powtarza) o łącznej długości w zadanym paśmie; długość nie jest dopasowywana
„do znaku”, tylko losowo wybierana kombinacja zdań trafia w pasmo.
"""
from __future__ import annotations

import itertools
import random
import re

_WARIANTY = re.compile(r"<([^<>]*)>")

_FORMULKI: dict[str, tuple[str, ...]] = {
    "pl": (
        "Strony <zgodnie |>oświadczają, że znają treść <wszystkich|poszczególnych> postanowień niniejszego dokumentu i je akceptują.",
        "Wszelkie zmiany niniejszego dokumentu wymagają formy pisemnej<| pod rygorem nieważności>.",
        "Spory wynikłe z niniejszej sprawy strony <będą|zobowiązują się> rozstrzygać <polubownie|w drodze negocjacji>, "
        "<a w razie braku porozumienia|a gdy porozumienie nie zostanie osiągnięte> przez sąd właściwy <miejscowo|według przepisów o właściwości>.",
        "Dokument sporządzono w dwóch jednobrzmiących egzemplarzach, po jednym dla każdej ze stron.",
        "Korespondencję <związaną z niniejszą sprawą|dotyczącą niniejszej sprawy> strony <będą|zobowiązały się> doręczać "
        "<na adresy wskazane w treści dokumentu|listem poleconym lub za pośrednictwem poczty elektronicznej>.",
        "Zawiadomienie o zmianie danych kontaktowych <powinno|musi> nastąpić niezwłocznie<| i na piśmie>.",
        "Przepisy ogólne <o zobowiązaniach|dotyczące zobowiązań> <stosuje się|mają zastosowanie> w zakresie nieuregulowanym niniejszym dokumentem.",
        "Nagłówki użyte w dokumencie mają charakter <wyłącznie |>informacyjny i nie wpływają na wykładnię jego postanowień.",
        "Jeżeli którekolwiek z postanowień okaże się nieskuteczne, pozostałe postanowienia <zachowują moc|pozostają w mocy>.",
        "Załączniki stanowią integralną część dokumentu<| i podlegają tym samym zasadom>.",
        "Zakres prac <został|został szczegółowo> określony w <załączniku|odrębnym załączniku> do dokumentu.",
        "Ostateczne rozliczenie <nastąpi|zostanie dokonane> po <zakończeniu|odbiorze> <wszystkich |>prac.",
        "Każda ze stron <ponosi|pokrywa> <własne |>koszty związane z <przygotowaniem|zawarciem> niniejszego dokumentu.",
        "Poufnymi są wszelkie informacje <przekazane|udostępnione> przez jedną ze stron drugiej stronie "
        "<w związku z realizacją dokumentu|na potrzeby sprawy>.",
        "O wszelkich okolicznościach mogących wpłynąć na wykonanie dokumentu strony <poinformują się|będą się informować> <niezwłocznie|bez zbędnej zwłoki>.",
        "Termin <wykonania|realizacji> zobowiązań może zostać przedłużony <wyłącznie |>za zgodą obu stron.",
    ),
    "en": (
        "The parties <hereby |>confirm that they have read all provisions of this document and <accept|agree to> them.",
        "Any amendment to this document <must be|shall be> made in writing<| to be valid>.",
        "Disputes arising from this matter <shall|will> be settled <amicably|through negotiation> and, "
        "<failing that|if that fails>, by the court having jurisdiction.",
        "This document has been drawn up in two identical copies, one for each party.",
        "Correspondence <relating to|concerning> this matter <shall|will> be delivered "
        "<to the addresses stated in the document|by registered post or by electronic mail>.",
        "Notice of any change in contact details must be given <promptly|without delay><| and in writing>.",
        "The general rules on obligations <shall|will> apply to anything not regulated by this document.",
        "Headings are used for <convenience only|information only> and do not affect the interpretation of its provisions.",
        "If any provision proves ineffective, the remaining provisions <remain in force|shall remain valid>.",
        "The annexes form an integral part of the document<| and are subject to the same rules>.",
        "The scope of the works is <set out|described> in <the annex|a separate annex> to the document.",
        "Final settlement <shall be made|will take place> after <completion|handover> of <all |>works.",
        "Each party <bears|shall bear> its own costs <of preparing|in connection with> this document.",
        "All information <disclosed|made available> by one party to the other <in connection with this matter|for the purposes of the case> is confidential.",
        "The parties <shall|will> inform each other <promptly|without undue delay> of any circumstances that may affect performance.",
        "The time for performance may be extended only <with the consent of both parties|by mutual agreement of the parties>.",
    ),
    "de": (
        "Die Parteien <bestätigen|erklären>, dass ihnen der Inhalt <aller|sämtlicher> Bestimmungen dieses Dokuments bekannt ist "
        "und sie diese <annehmen|akzeptieren>.",
        "Änderungen dieses Dokuments bedürfen <zu ihrer Wirksamkeit |>der Schriftform.",
        "Streitigkeiten aus dieser Angelegenheit <werden die Parteien|sollen die Parteien> <zunächst |>gütlich beilegen; "
        "andernfalls entscheidet das <zuständige|örtlich zuständige> Gericht.",
        "Das Dokument wurde in zwei gleichlautenden Ausfertigungen erstellt, von denen jede Partei eine erhält.",
        "Der Schriftverkehr in dieser Angelegenheit wird <an die im Dokument genannten Anschriften|per Einschreiben oder auf elektronischem Weg> zugestellt.",
        "Eine Änderung der Kontaktdaten ist <unverzüglich |>mitzuteilen<| und schriftlich zu bestätigen>.",
        "Soweit dieses Dokument nichts anderes regelt, gelten die allgemeinen Vorschriften des Schuldrechts.",
        "Die Überschriften dienen <nur |>der Übersicht und beeinflussen die Auslegung der Bestimmungen nicht.",
        "Sollte eine Bestimmung unwirksam sein, <bleiben die übrigen Bestimmungen|bleibt die Wirksamkeit der übrigen Bestimmungen> <davon |>unberührt.",
        "Die Anlagen sind Bestandteil des Dokuments<| und unterliegen denselben Regeln>.",
        "Der Umfang der Arbeiten ist <in der Anlage|in einer gesonderten Anlage> zu diesem Dokument <festgelegt|beschrieben>.",
        "Die Schlussabrechnung erfolgt nach <Fertigstellung|Abnahme> <aller|der gesamten> Arbeiten.",
        "Jede Partei trägt ihre <eigenen |>Kosten <der Vorbereitung|im Zusammenhang mit der Erstellung> dieses Dokuments.",
        "Vertraulich sind alle Informationen, die eine Partei der anderen <im Zusammenhang mit dieser Angelegenheit|für Zwecke des Verfahrens> "
        "<mitgeteilt|zugänglich gemacht> hat.",
        "Die Parteien unterrichten sich <unverzüglich|ohne schuldhaftes Zögern> über alle Umstände, die die Erfüllung beeinflussen können.",
        "Die Erfüllungsfrist kann <nur |>mit Zustimmung beider Parteien verlängert werden.",
    ),
    "es": (
        "Las partes <declaran|manifiestan> que conocen el contenido de <todas|cada una de> las estipulaciones de este documento y las <aceptan|aprueban>.",
        "Cualquier modificación de este documento <deberá|habrá de> realizarse por escrito<| para su validez>.",
        "Las controversias derivadas de este asunto se resolverán <amistosamente|mediante negociación> y, "
        "<en su defecto|de no alcanzarse acuerdo>, ante el tribunal competente.",
        "El presente documento se extiende en dos ejemplares idénticos, uno para cada parte.",
        "La correspondencia relativa a este asunto se enviará <a los domicilios indicados en el documento|por correo certificado o por medios electrónicos>.",
        "El cambio de los datos de contacto deberá comunicarse <sin demora|de inmediato><| y por escrito>.",
        "En lo no previsto en este documento se aplicarán las normas generales sobre obligaciones.",
        "Los títulos tienen <carácter meramente informativo|solo carácter informativo> y no afectan a la interpretación de las estipulaciones.",
        "Si alguna estipulación resultara ineficaz, las demás <conservarán su validez|seguirán en vigor>.",
        "Los anexos forman parte integrante del documento<| y se rigen por las mismas reglas>.",
        "El alcance de los trabajos se <describe|detalla> en <el anexo|un anexo separado> de este documento.",
        "La liquidación final se practicará tras la <terminación|recepción> de <todos |>los trabajos.",
        "Cada parte soportará <sus propios |los >gastos derivados de la <preparación|formalización> de este documento.",
        "Se considera confidencial toda la información que una parte facilite a la otra <en relación con este asunto|para los fines del procedimiento>.",
        "Las partes se informarán <sin demora|de inmediato> de cualquier circunstancia que pueda afectar al cumplimiento.",
        "El plazo de ejecución solo podrá ampliarse <con el consentimiento de|por acuerdo entre> ambas partes.",
    ),
    "fr": (
        "Les parties <déclarent|reconnaissent> avoir pris connaissance de <toutes les|chacune des> stipulations du présent document "
        "et <les accepter sans réserve|en accepter la teneur>.",
        "Toute modification du présent document <doit|devra> être faite par écrit<| pour être valable>.",
        "Les différends nés de cette affaire seront réglés <à l'amiable|par la négociation> et, <à défaut|à défaut d'accord>, par la juridiction compétente.",
        "Le présent document est établi en deux exemplaires identiques, un pour chaque partie.",
        "La correspondance relative à cette affaire sera adressée <aux adresses indiquées dans le document|par lettre recommandée ou par voie électronique>.",
        "Tout changement de coordonnées doit être communiqué <sans délai|immédiatement><| et par écrit>.",
        "Pour tout ce qui n'est pas prévu par le présent document, les règles générales des obligations s'appliquent.",
        "Les intitulés ont <une valeur purement informative|une simple valeur indicative> et n'influent pas sur l'interprétation des stipulations.",
        "Si l'une des stipulations se révélait inefficace, les autres <demeureraient en vigueur|resteraient valables>.",
        "Les annexes font partie intégrante du document<| et sont soumises aux mêmes règles>.",
        "L'étendue des travaux est <décrite|précisée> dans <l'annexe|une annexe distincte> du présent document.",
        "Le décompte final sera établi après <l'achèvement|la réception> de <tous les|l'ensemble des> travaux.",
        "Chaque partie supporte <ses propres |les >frais liés à la <préparation|conclusion> du présent document.",
        "Sont confidentielles toutes les informations qu'une partie communique à l'autre <à l'occasion de cette affaire|pour les besoins de la procédure>.",
        "Les parties s'informeront <sans délai|immédiatement> de toute circonstance susceptible d'affecter l'exécution.",
        "Le délai d'exécution ne peut être prolongé que <du consentement des|d'un commun accord entre les> deux parties.",
    ),
}


def rozwin(formulka: str) -> tuple[str, ...]:
    """Wszystkie warianty formułki (iloczyn opcji `<a|b|>`), bez duplikatów, w stałej kolejności."""
    grupy = [m.split("|") for m in _WARIANTY.findall(formulka)]
    szkielet = _WARIANTY.split(formulka)[0::2]
    wynik = []
    for wybor in itertools.product(*grupy):
        tekst = szkielet[0]
        for opcja, reszta in zip(wybor, szkielet[1:]):
            tekst += opcja + reszta
        if tekst not in wynik:
            wynik.append(tekst)
    return tuple(wynik)


#: język -> krotka formułek, każda jako krotka swoich wariantów (do wyboru jednego na akapit)
FORMULKI: dict[str, tuple[tuple[str, ...], ...]] = {j: tuple(rozwin(f) for f in fs) for j, fs in _FORMULKI.items()}


def wszystkie_zdania(jezyk: str) -> frozenset[str]:
    """Zbiór wszystkich zdań, z których może składać się wypełniacz danego języka."""
    return frozenset(z for warianty in FORMULKI[jezyk] for z in warianty)


def akapit_w_pasie(rng: random.Random, jezyk: str, dl_min: int, dl_max: int) -> str:
    """Akapit z kilku różnych formułek o długości w [dl_min, dl_max] (znaki, ze spacjami między zdaniami).
    Zdania się nie powtarzają. ValueError, gdy po wielu próbach żadna kombinacja nie trafia w pasmo."""
    pula = FORMULKI[jezyk]
    dl_min = max(dl_min, 1)
    if dl_max < dl_min:
        raise ValueError(f"puste pasmo długości wypełniacza [{dl_min}, {dl_max}]")
    k_min, k_max = max(1, dl_min // 170), max(1, min(len(pula), dl_max // 45))
    for _ in range(20_000):
        k = rng.randint(k_min, max(k_min, k_max))
        zdania = [rng.choice(pula[i]) for i in rng.sample(range(len(pula)), k)]
        if dl_min <= sum(map(len, zdania)) + k - 1 <= dl_max:
            return " ".join(zdania)
    raise ValueError(f"brak kombinacji zdań o długości w [{dl_min}, {dl_max}] dla języka {jezyk}")
