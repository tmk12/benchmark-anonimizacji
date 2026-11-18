"""Jugement du tribunal judiciaire (« RÉPUBLIQUE FRANÇAISE – AU NOM DU PEUPLE FRANÇAIS ») ou arrêt de la cour d'appel en
matière de remboursement d'un prêt entre particuliers: composition, parties, EXPOSÉ DU LITIGE, MOTIFS DE LA DÉCISION,
PAR CES MOTIFS; citations de la Cour de cassation (texte brut, pas de gold) – pożyczka, więc 1re chambre civile.

Trois variantes: `fr_tj_unique` (juge unique), `fr_tj_collegiale` (formation collégiale de trois juges) et `fr_appel`
(cour d'appel, chambre de trois magistrats, appel du jugement du tribunal judiciaire; numéro RG et juridiction de première
instance dans `ctx.sygn_pierwsza` et `ctx.sad_pierwsza`). Daty, kwoty i rok RG z `Kontekst`."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja
from ._formy import APP, APP_C, DEF, DEF_AU, DEF_C, DEM, DEM_AU, DEM_C, INT, INT_AU, INT_C, acte, civ, g

_TJ = ("fr_tj_unique", "fr_tj_collegiale")


def tj(tekst: str) -> tuple[W, ...]:
    """Blok dla obu wariantów pierwszej instancji (nie dla apelacji)."""
    return tuple(W(v, tekst) for v in _TJ)


_MAITRE_DEM = "Maître {avocat_dem.imie} {avocat_dem.nazwisko:upper}, " + g("avocat_dem", "avocat", "avocate") + " au {sad.barreau}"
_MAITRE_DEF = "Maître {avocat_def.imie} {avocat_def.nazwisko:upper}, " + g("avocat_def", "avocat", "avocate") + " au {sad.barreau}"
_TEMOINS = (civ("temoin1") + " {temoin1.pelne} et " + civ("temoin2") + " {temoin2.pelne}")

SZABLON = Szablon(
    jezyk="fr", typ="wyrok", przedmiot="pret", warianty=("fr_tj_unique", "fr_tj_collegiale", "fr_appel"),
    role={"sad": "sad", "juge1": "osoba", "juge2": "osoba", "juge3": "osoba", "greffier": "osoba",
          "demandeur": "osoba", "defendeur": "osoba", "avocat_dem": "osoba", "avocat_def": "osoba",
          "temoin1": "osoba", "temoin2": "osoba", "cit1": "cytat", "cit2": "cytat", "cit3": "cytat"},
    sekcje=[
        sekcja("caption", "naglowek", "RÉPUBLIQUE FRANÇAISE", "AU NOM DU PEUPLE FRANÇAIS", "{sad.nazwa:upper}"),
        sekcja("chambre", "naglowek",
               *tj("1re chambre civile"), *tj("2e chambre civile"), *tj("3e chambre civile"),
               W("fr_appel", "1re chambre civile"), W("fr_appel", "2e chambre civile"), W("fr_appel", "3e chambre civile"),
               min=1, max=1),
        sekcja("number", "naglowek",
               "{sad.sygnatura}",
               W("fr_appel", "Décision déférée : jugement rendu le {ctx.wyrok} par le {ctx.sad_pierwsza}, "
                 "{ctx.sygn_pierwsza}"),
               *tj("JUGEMENT DU {ctx.wyrok_koncowy}"),
               W("fr_appel", "ARRÊT DU {ctx.wyrok_koncowy}")),
        sekcja("composition", "akapit",
               W("fr_tj_unique", "COMPOSITION DU TRIBUNAL lors des débats et du délibéré : le tribunal a siégé à juge "
                 "unique en la personne de " + acte("juge1") + ", " + g("juge1", "vice-président", "vice-présidente")
                 + ", " + g("juge1", "assisté", "assistée") + " de " + acte("greffier") + ", "
                 + g("greffier", "greffier", "greffière") + "."),
               W("fr_tj_collegiale", "COMPOSITION DU TRIBUNAL lors des débats et du délibéré : le tribunal a statué en "
                 "formation collégiale, composé de " + acte("juge1") + ", " + g("juge1", "président", "présidente")
                 + ", " + acte("juge2") + ", juge, et " + acte("juge3") + ", juge, avec l'assistance de "
                 + acte("greffier") + ", " + g("greffier", "greffier", "greffière") + "."),
               W("fr_appel", "COMPOSITION DE LA COUR lors des débats et du délibéré : " + acte("juge1") + ", "
                 + g("juge1", "président", "présidente") + " de chambre, " + acte("juge2") + ", "
                 + g("juge2", "conseiller", "conseillère") + ", et " + acte("juge3") + ", "
                 + g("juge3", "conseiller", "conseillère") + ", assistés de " + acte("greffier") + ", "
                 + g("greffier", "greffier", "greffière") + "."),
               ),
        sekcja("parties", "akapit",
               "ENTRE :",
               *tj(acte("demandeur") + ", demeurant {demandeur.adres},"),
               *tj(g("demandeur", "DEMANDEUR", "DEMANDERESSE") + ", " + g("demandeur", "représenté", "représentée")
                   + " par " + _MAITRE_DEM + ","),
               W("fr_appel", acte("defendeur") + ", demeurant {defendeur.adres},"),
               W("fr_appel", g("defendeur", "APPELANT", "APPELANTE") + ", " + g("defendeur", "représenté", "représentée")
                 + " par " + _MAITRE_DEF + ","),
               "ET :",
               *tj(acte("defendeur") + ", demeurant {defendeur.adres},"),
               *tj(g("defendeur", "DÉFENDEUR", "DÉFENDERESSE") + ", " + g("defendeur", "représenté", "représentée")
                   + " par " + _MAITRE_DEF + "."),
               W("fr_appel", acte("demandeur") + ", demeurant {demandeur.adres},"),
               W("fr_appel", g("demandeur", "INTIMÉ", "INTIMÉE") + ", " + g("demandeur", "représenté", "représentée")
                 + " par " + _MAITRE_DEM + ".")),
        sekcja("expose_title", "akapit", "EXPOSÉ DU LITIGE"),
        sekcja("expose", "akapit",
               *tj("Par reconnaissance de dette du {ctx.umowa}, " + DEM + " a prêté " + DEF_AU + " la somme de "
                   "{ctx.glowna}, remboursable au plus tard le {ctx.termin_platnosci}."),
               *tj("Aucun remboursement complet n'étant intervenu, " + DEM + " a mis " + DEF + " en demeure de payer "
                   "par lettre recommandée du {ctx.wezwanie}, avec un délai expirant le {ctx.termin_wezwania}."),
               *tj("Par acte de commissaire de justice du {ctx.pozew}, " + DEM + " a fait assigner " + DEF + " devant le "
                   "{sad.nazwa}."),
               *tj("Aux termes de ses dernières conclusions, " + DEM + " demande au tribunal de condamner " + DEF
                   + " à payer " + DEM_AU + " la somme de {ctx.glowna} avec intérêts au taux légal à compter du "
                   "{ctx.wezwanie}, ainsi que {ctx.koszty_zast} au titre de l'article 700 du Code de procédure civile."),
               *tj(DEF_C + " conclut au rejet de la demande. " + g("defendeur", "Il", "Elle") + " soutient avoir déjà "
                   "remboursé une partie de la somme. " + DEM_C + " produit les attestations de " + _TEMOINS + "."),
               W("fr_tj_unique", "L'affaire a été plaidée à l'audience du {ctx.rozprawa_koncowa} devant le juge unique "
                 "et mise en délibéré au {ctx.wyrok_koncowy}, date à laquelle la décision a été mise à disposition au "
                 "greffe."),
               W("fr_tj_collegiale", "L'affaire a été plaidée à l'audience du {ctx.rozprawa_koncowa} devant la formation "
                 "collégiale et mise en délibéré au {ctx.wyrok_koncowy}, date à laquelle la décision a été mise à "
                 "disposition au greffe."),
               W("fr_appel", "Par jugement du {ctx.wyrok}, le {ctx.sad_pierwsza} a condamné " + APP + " à payer "
                 + INT_AU + " la somme de {ctx.zasadzona} avec intérêts au taux légal à compter du {ctx.wezwanie}, a "
                 "débouté " + INT + " du surplus de ses demandes et a condamné " + APP + " aux dépens."),
               W("fr_appel", APP_C + " a interjeté appel de cette décision le {ctx.apelacja}."),
               W("fr_appel", "Par ses dernières conclusions, " + APP + " demande à la cour d'infirmer le jugement et de "
                 "débouter " + INT + " de l'ensemble de ses demandes ; " + INT + " sollicite la confirmation du jugement."),
               W("fr_appel", "L'affaire a été plaidée à l'audience du {ctx.rozprawa_koncowa} et l'arrêt a été mis à "
                 "disposition au greffe le {ctx.wyrok_koncowy}.")),
        sekcja("motifs_title", "akapit", "MOTIFS DE LA DÉCISION"),
        sekcja("motifs", "akapit",
               *tj("Sur la demande en remboursement du prêt"),
               *tj("Aux termes de l'article 1902 du Code civil, l'emprunteur est tenu de rendre les choses prêtées, en "
                   "même quantité et qualité, au terme convenu."),
               *tj("Il incombe " + DEM_AU + " de prouver l'existence du prêt et la remise des fonds, et " + DEF_AU
                   + " de justifier de leur restitution ({cit1.sygnatura} ; {cit2.sygnatura})."),
               *tj("En l'espèce, la reconnaissance de dette du {ctx.umowa} et le virement sur le compte "
                   "{defendeur.rachunek} établissent la remise de la somme de {ctx.glowna}."),
               *tj("Les attestations de " + _TEMOINS + ", que le tribunal estime sincères et concordantes, établissent que "
                   + DEF + " a effectué des remboursements partiels, qui doivent être déduits de la créance "
                   "({cit3.sygnatura})."),
               *tj("Il en résulte que " + DEF + " reste redevable " + DEM_AU + " de la somme de {ctx.zasadzona}. "
                   + g("demandeur", "Le demandeur est débouté du surplus de sa demande.",
                       "La demanderesse est déboutée du surplus de sa demande.")),
               *tj("Sur les intérêts"),
               *tj("En application de l'article 1231-6 du Code civil, les dommages et intérêts dus à raison du retard "
                   "dans le paiement d'une somme d'argent consistent dans l'intérêt au taux légal, à compter de la mise en "
                   "demeure ; la condamnation portera donc intérêts à compter du {ctx.wezwanie}."),
               *tj("Sur les demandes accessoires"),
               *tj(DEF_C + ", partie qui succombe pour l'essentiel, sera " + g("defendeur", "condamné", "condamnée")
                   + " aux dépens. L'équité commande d'allouer " + DEM_AU + " la somme de {ctx.koszty_zast} au titre de "
                   "l'article 700 du Code de procédure civile."),
               *tj("La décision est exécutoire de droit à titre provisoire ; il n'y a pas lieu d'écarter cette exécution "
                   "provisoire."),
               W("fr_appel", "Sur la recevabilité de l'appel"),
               W("fr_appel", "L'appel, interjeté dans le délai légal, est recevable ; cette recevabilité n'est pas "
                 "contestée."),
               W("fr_appel", "Sur le bien-fondé de la demande en paiement"),
               W("fr_appel", "Le premier juge a exactement retenu que l'existence du prêt est établie par la reconnaissance "
                 "de dette du {ctx.umowa} et par la remise des fonds, conformément à l'article 1902 du Code civil."),
               W("fr_appel", "La charge de la preuve du remboursement pèse sur l'emprunteur ({cit1.sygnatura} ; "
                 "{cit2.sygnatura}). " + APP_C + " ne rapporte pas la preuve de remboursements supérieurs à ceux retenus "
                 "par le tribunal ({cit3.sygnatura})."),
               W("fr_appel", "Les attestations de " + _TEMOINS + " ont été examinées par le premier juge, dont "
                 "l'appréciation est approuvée par la cour."),
               W("fr_appel", "Sur les intérêts"),
               W("fr_appel", "Les intérêts au taux légal courent à compter de la mise en demeure du {ctx.wezwanie}, "
                 "ainsi que l'a jugé le tribunal."),
               W("fr_appel", "Sur les demandes accessoires"),
               W("fr_appel", "Le jugement sera confirmé en ce qu'il a statué sur les dépens et les frais irrépétibles de "
                 "première instance. " + APP_C + ", qui succombe en son recours, sera "
                 + g("defendeur", "condamné", "condamnée") + " aux dépens d'appel et à payer " + INT_AU
                 + " la somme de {ctx.koszty_apel} au titre de l'article 700 du Code de procédure civile.")),
        sekcja("dispositif_title", "akapit", "PAR CES MOTIFS"),
        sekcja("dispositif", "akapit",
               *tj("Le tribunal, statuant publiquement, par jugement contradictoire et en premier ressort, mis à "
                   "disposition au greffe :"),
               *tj("- CONDAMNE " + DEF + " à payer " + DEM_AU + " la somme de {ctx.zasadzona}, avec intérêts au taux légal "
                   "à compter du {ctx.wezwanie} ;"),
               *tj("- DÉBOUTE " + DEM + " du surplus de ses demandes ;"),
               *tj("- CONDAMNE " + DEF + " à payer " + DEM_AU + " la somme de {ctx.koszty_zast} au titre de l'article 700 "
                   "du Code de procédure civile ;"),
               *tj("- CONDAMNE " + DEF + " aux dépens ;"),
               *tj("- RAPPELLE que la présente décision est exécutoire de droit à titre provisoire."),
               W("fr_appel", "La cour, statuant publiquement, par arrêt contradictoire, mis à disposition au greffe :"),
               W("fr_appel", "- CONFIRME le jugement rendu le {ctx.wyrok} par le {ctx.sad_pierwsza} ({ctx.sygn_pierwsza}) "
                 "en toutes ses dispositions ;"),
               W("fr_appel", "- Y ajoutant, CONDAMNE " + APP + " à payer " + INT_AU + " la somme de {ctx.koszty_apel} au "
                 "titre de l'article 700 du Code de procédure civile pour la procédure d'appel ;"),
               W("fr_appel", "- CONDAMNE " + APP + " aux dépens d'appel ;"),
               W("fr_appel", "- REJETTE toute autre demande.")),
        sekcja("closing", "akapit",
               W("fr_tj_unique", "Ainsi jugé et prononcé par mise à disposition au greffe le {ctx.wyrok_koncowy}, la "
                 "minute étant signée par le juge et " + g("greffier", "le greffier", "la greffière") + "."),
               W("fr_tj_collegiale", "Ainsi jugé et prononcé par mise à disposition au greffe le {ctx.wyrok_koncowy}, la "
                 "minute étant signée par " + g("juge1", "le président", "la présidente") + " et "
                 + g("greffier", "le greffier", "la greffière") + "."),
               W("fr_appel", "Ainsi jugé et prononcé par mise à disposition au greffe le {ctx.wyrok_koncowy}, la minute "
                 "étant signée par " + g("juge1", "le président de chambre", "la présidente de chambre") + " et "
                 + g("greffier", "le greffier", "la greffière") + ".")),
        sekcja("signatures", "podpis",
               W("fr_tj_unique", "{juge1.pelne}"), W("fr_tj_collegiale", "{juge1.pelne}"), W("fr_appel", "{juge1.pelne}"),
               W("fr_tj_collegiale", "{juge2.pelne}"), W("fr_appel", "{juge2.pelne}"),
               W("fr_tj_collegiale", "{juge3.pelne}"), W("fr_appel", "{juge3.pelne}"),
               "{greffier.pelne}"),
        sekcja("footer", "stopka", "{sad.nazwa} | {sad.sygnatura} | Page 1"),
    ],
    metadane={"subject": "Décision en matière de remboursement d'un prêt", "case": "{sad.sygnatura}"},
)
