"""Assignation devant le tribunal judiciaire en remboursement d'un prêt entre particuliers (« À LA REQUÊTE DE … », « J'AI,
… commissaire de justice, DONNÉ ASSIGNATION À … », « PLAISE AU TRIBUNAL », « PAR CES MOTIFS ») avec bordereau de pièces.
Procédure écrite ordinaire: la demande dépasse 10 000 € (wariant `fr_tj_unique` albo `fr_tj_collegiale`), więc avocat
obligatoire. Daty i kwoty z `Kontekst`; opłaty sądowej nie ma (we Francji nie pobiera się jej w sprawach cywilnych)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja
from ._formy import DEF, DEF_AU, DEF_C, DEM, DEM_AU, DEM_C, DEM_DU, acte, g

SZABLON = Szablon(
    jezyk="fr", typ="pozew", warianty=("fr_tj_unique", "fr_tj_collegiale"),
    role={"cabinet": "kancelaria", "avocat": "osoba", "demandeur": "osoba", "defendeur": "osoba",
          "huissier": "osoba", "temoin1": "osoba", "temoin2": "osoba", "sad": "sad"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{cabinet.nazwa}",
               "{cabinet.adres} | Tél. {cabinet.telefon} | {cabinet.email}",
               "Réf. dossier : AV-{ctx.udzialy1}"),
        sekcja("court", "akapit",
               "{sad.nazwa:upper}",
               "ASSIGNATION EN PAIEMENT",
               "Procédure écrite ordinaire – représentation obligatoire par avocat",
               "Le {ctx.pozew}"),
        sekcja("requete", "akapit",
               "À LA REQUÊTE DE :",
               acte("demandeur") + ", " + g("demandeur", "né", "née") + " le {demandeur.data_ur} à {demandeur.miasto}, "
               "de nationalité française, demeurant {demandeur.adres},",
               "Ayant pour avocat Maître " + "{avocat.imie} {avocat.nazwisko:upper}" + ", "
               + g("avocat", "avocat", "avocate") + " au {cabinet.barreau}, {cabinet.nazwa}, {cabinet.adres}, "
               + g("avocat", "lequel", "laquelle") + " se constitue pour " + DEM + " sur la présente assignation.",
               "J'AI, Maître {huissier.pelne}, commissaire de justice, " + g("huissier", "soussigné", "soussignée")
               + ",",
               "DONNÉ ASSIGNATION À :",
               acte("defendeur") + ", " + g("defendeur", "né", "née") + " le {defendeur.data_ur} à {defendeur.miasto}, "
               "demeurant {defendeur.adres}, où étant et parlant à sa personne,",
               "D'AVOIR À COMPARAÎTRE devant le {sad.nazwa}, dont le siège est à {sad.miasto}, à l'audience d'orientation "
               "du {ctx.rozprawa}, selon les modalités de la procédure écrite ordinaire."),
        sekcja("notice", "akapit",
               "Il est rappelé que la constitution d'avocat est obligatoire. Faute pour " + DEF + " de constituer "
               "avocat dans un délai de quinze jours à compter de la délivrance du présent acte, un jugement pourra être "
               "rendu sur les seuls éléments fournis par " + DEM + ".",
               "Le présent acte est établi en vue de recouvrer une créance de {ctx.glowna}, outre intérêts et frais."),
        sekcja("plaise", "akapit", "PLAISE AU TRIBUNAL"),
        sekcja("facts_title", "akapit", "I. FAITS ET PROCÉDURE"),
        sekcja("facts", "akapit",
               "Par reconnaissance de dette signée le {ctx.umowa}, " + DEM + " a prêté " + DEF_AU + " la somme de "
               "{ctx.glowna}. Les fonds ont été remis par virement sur le compte {defendeur.rachunek}.",
               "Aux termes de cet acte, la somme prêtée devait être remboursée au plus tard le {ctx.termin_platnosci}. "
               + DEF_C + " n'a effectué aucun remboursement à cette date, malgré plusieurs rappels amiables.",
               "Par lettre recommandée avec demande d'avis de réception du {ctx.wezwanie}, " + DEM + " a mis " + DEF
               + " en demeure de payer avant le {ctx.termin_wezwania}. Ce délai est resté sans effet.",
               DEF_C + " a reconnu à plusieurs reprises devoir cette somme, ainsi que l'établissent les attestations de "
               "{temoin1.rodzaj:Monsieur|Madame} {temoin1.pelne}, demeurant {temoin1.adres}, et de "
               "{temoin2.rodzaj:Monsieur|Madame} {temoin2.pelne} (tél. {temoin2.telefon}), établies dans les formes de "
               "l'article 202 du Code de procédure civile.",
               min=4, max=4),
        sekcja("law_title", "akapit", "II. DISCUSSION"),
        sekcja("law", "akapit",
               "Le tribunal judiciaire est territorialement compétent en application de l'article 42 du Code de "
               "procédure civile, " + DEF + " demeurant dans son ressort.",
               W("fr_tj_unique", "Eu égard à la simplicité du litige, " + DEM + " ne s'oppose pas à ce que l'affaire "
                 "soit jugée par un juge unique."),
               W("fr_tj_collegiale", "Compte tenu de l'importance du litige, " + DEM + " sollicite que l'affaire soit "
                 "examinée en formation collégiale."),
               "Aux termes de l'article 1103 du Code civil, les contrats légalement formés tiennent lieu de loi à ceux "
               "qui les ont faits.",
               "L'article 1902 du Code civil impose à l'emprunteur de rendre les choses prêtées, en même quantité et "
               "qualité, au terme convenu.",
               "Celui qui réclame l'exécution d'une obligation doit la prouver (article 1353 du Code civil) : en "
               "l'espèce, le prêt est établi par la reconnaissance de dette du {ctx.umowa} et par la remise des fonds.",
               "Les intérêts au taux légal sont dus à compter de la mise en demeure du {ctx.wezwanie}, conformément à "
               "l'article 1231-6 du Code civil.",
               "Il serait inéquitable de laisser à la charge " + DEM_DU + " les frais irrépétibles exposés pour faire "
               "valoir ses droits ; une somme de {ctx.koszty_zast} lui sera allouée au titre de l'article 700 du Code de "
               "procédure civile.",
               min=6, max=6),
        sekcja("prayer_title", "akapit", "PAR CES MOTIFS"),
        sekcja("prayer", "akapit",
               "Vu les articles 1103, 1353 et 1902 du Code civil, vu les pièces versées aux débats,",
               "Il est demandé au tribunal de :",
               "- CONDAMNER " + DEF + " à payer " + DEM_AU + " la somme de {ctx.glowna} au titre du remboursement du "
               "prêt consenti le {ctx.umowa}, outre les intérêts au taux légal à compter de la mise en demeure du "
               "{ctx.wezwanie} ;",
               "- CONDAMNER " + DEF + " à payer " + DEM_AU + " la somme de {ctx.koszty_zast} sur le fondement de "
               "l'article 700 du Code de procédure civile ;",
               "- CONDAMNER " + DEF + " aux entiers dépens ;",
               "- RAPPELER que l'exécution provisoire est de droit.",
               "SOUS TOUTES RÉSERVES",
               min=7, max=7),
        sekcja("exhibits", "akapit",
               "BORDEREAU DE PIÈCES COMMUNIQUÉES",
               "Pièce n° 1 : reconnaissance de dette du {ctx.umowa}",
               "Pièce n° 2 : relevé de compte justifiant le virement des fonds",
               "Pièce n° 3 : lettre de mise en demeure du {ctx.wezwanie} et avis de réception",
               "Pièce n° 4 : attestation de {temoin1.rodzaj:Monsieur|Madame} {temoin1.pelne}",
               "Pièce n° 5 : attestation de {temoin2.rodzaj:Monsieur|Madame} {temoin2.pelne}"),
        sekcja("closing", "akapit",
               "Fait à {cabinet.miasto}, le {ctx.pozew}",
               "Maître {avocat.imie} {avocat.nazwisko:upper}",
               min=2, max=2),
        sekcja("signature", "podpis", "{avocat.pelne}"),
        sekcja("footer", "stopka",
               "{cabinet.nazwa} | {cabinet.adres} | SIREN {cabinet.siren} | TVA intracommunautaire {cabinet.vat} | "
               "Tél. {cabinet.telefon} | {cabinet.email}"),
    ],
    metadane={"author": "{avocat.pelne}", "subject": "Assignation en paiement d'un prêt"},
)
