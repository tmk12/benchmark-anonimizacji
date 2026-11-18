"""Journal de paie d'une entreprise (état récapitulatif des rémunérations, tableur): en-tête, tableau de plus de 200 salariés
(NIR, IBAN), totaux et mentions. Chaque ligne a sa propre personne (`p000`…), parce que les occurrences d'une même rôle
n'ont qu'une valeur; salaires et totaux viennent de `Kontekst` (`ctx.brutto_<i>`, `ctx.suma_<n>`), la synthèse correspond
donc au tableau."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

WIERSZE = 212
_FONCTIONS = ("Gestionnaire de paie", "Comptable", "Responsable d'équipe", "Technicien", "Assistant de direction",
              "Chauffeur-livreur", "Magasinier", "Agent administratif", "Technicien senior", "Responsable sécurité",
              "Conseiller clientèle", "Administrateur systèmes")

_ROLE_WIERSZY = {f"p{i:03d}": "osoba" for i in range(WIERSZE)}


def _tabela() -> str:
    wiersze = ["N° | Prénom | Nom | NIR | Emploi | Salaire brut | IBAN"]
    for i in range(WIERSZE):
        p = f"p{i:03d}"
        wiersze.append(f"{i + 1} | {{{p}.pelne/1}} | {{{p}.pelne/2}} | {{{p}.nir}} | "
                       f"{_FONCTIONS[i % len(_FONCTIONS)]} | {{ctx.brutto_{i}}} | {{{p}.rachunek}}")
    return "\n".join(wiersze)


SZABLON = Szablon(
    jezyk="fr", typ="lista_plac",
    role={"employeur": "firma", "redacteur": "osoba", "valideur": "osoba", "controleur": "osoba"} | _ROLE_WIERSZY,
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{employeur.nazwa}",
               "{employeur.adres} | SIRET {employeur.siret} | TVA intracommunautaire {employeur.vat}"),
        sekcja("title", "akapit",
               "JOURNAL DE PAIE – ÉTAT RÉCAPITULATIF DES RÉMUNÉRATIONS",
               "Date de paiement : {ctx.dok_termin}",
               "Employeur : {employeur.nazwa}"),
        sekcja("table", "komorka", _tabela()),
        sekcja("summary", "komorka",
               "Poste | Montant\n"
               "Total des salaires bruts | {ctx.suma_212}\n"
               "Cotisations sociales salariales (estimation) | {ctx.zus_212}\n"
               "Prélèvement à la source (estimation) | {ctx.pit_212}"),
        sekcja("notes", "akapit",
               "Les cotisations sociales sont déclarées chaque mois à l'URSSAF par la déclaration sociale nominative (DSN).",
               "L'employeur conserve un double des bulletins de paie des salariés pendant cinq ans.",
               "Les absences pour maladie, les indemnités journalières de sécurité sociale et la subrogation éventuelle "
               "figurent sur chaque bulletin de paie.",
               "Ce document contient des données à caractère personnel, dont le numéro de sécurité sociale, soumises au "
               "RGPD ; son accès est réservé au service paie.",
               min=3, max=4),
        sekcja("prepared", "akapit",
               "Établi par : {redacteur.pelne}, service paie, tél. {redacteur.telefon}",
               "Contrôlé par : {controleur.pelne}",
               "Validé pour paiement : {valideur.pelne}"),
        sekcja("signatures", "podpis", "{redacteur.pelne}", "{valideur.pelne}"),
        sekcja("footer", "stopka",
               "{employeur.nazwa} | {employeur.adres} | Tél. {employeur.telefon} | {employeur.email}"),
    ],
    metadane={"author": "{redacteur.pelne}", "subject": "Journal de paie – état récapitulatif des rémunérations"},
)
