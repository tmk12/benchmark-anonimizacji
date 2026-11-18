"""Présentation d'un cabinet d'avocats au comité stratégique d'une société cliente: résultats de la due diligence juridique
d'une société cible (SARL, cession de parts sociales) – diapositives courtes et tableau des risques; droit français."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja
from ._formy import civ, g

SZABLON = Szablon(
    jezyk="fr", typ="prezentacja",
    role={"cabinet": "kancelaria", "rapporteur": "osoba", "contact": "osoba", "gerant": "osoba",
          "cible": "spolka", "mandant": "spolka", "site": "sprawa"},
    sekcje=[
        sekcja("titles", "naglowek",
               "Due diligence juridique : {cible.nazwa}",
               "Synthèse des conclusions",
               "Principaux risques de l'opération",
               "Plan d'actions avant la signature",
               "Contact et prochaines étapes"),
        sekcja("slide1", "akapit",
               "Présenté par {rapporteur.pelne}, {cabinet.nazwa}",
               "Comité stratégique – {mandant.nazwa}, {ctx.dok}",
               "Strictement confidentiel – réservé au comité"),
        sekcja("slide2", "akapit",
               "Société cible : {cible.nazwa}, {cible.adres}",
               "{cible.rcs} {cible.siren} | TVA {cible.vat}",
               "Entretiens avec " + civ("gerant") + " {gerant.pelne}, " + g("gerant", "gérant", "gérante"),
               "Prix de cession des parts sociales proposé : {ctx.cena}"),
        sekcja("slide3", "akapit",
               "Clauses de changement de contrôle dans les contrats des clients clés",
               "Le registre des traitements (article 30 du RGPD) n'est pas à jour",
               "Trois litiges en cours pour un montant total de {ctx.sporow}",
               "Chaîne de droits incomplète sur les logiciels utilisés",
               "Aucun arriéré social ou fiscal identifié",
               min=3, max=5),
        sekcja("risks", "komorka",
               "Domaine | Niveau de risque | Recommandation\n"
               "Droit social | Moyen | Mettre à jour la politique de rémunération\n"
               "Protection des données | Élevé | Mettre à jour le registre et les contrats de sous-traitance\n"
               "Immobilier | Faible | Aucune action\n"
               "Propriété intellectuelle | Élevé | Obtenir les cessions de droits des prestataires indépendants"),
        sekcja("slide4", "akapit",
               "Signature de l'acte de cession des parts sociales avant le {ctx.dok_termin_dl}",
               "Conditions suspensives : accord des associés et de la banque qui finance l'opération",
               "La participation de " + civ("gerant") + " {gerant.pelne}, " + g("gerant", "gérant", "gérante")
               + " de la société cible, est requise pour la réalisation",
               "Contrôle des concentrations : vérifier les seuils de notification",
               min=3, max=4),
        sekcja("slide5", "akapit",
               "Contact : {contact.pelne}, tél. {contact.telefon}, courriel {contact.email}",
               "Notre site : {site.url}",
               "Merci"),
        sekcja("footer", "stopka", "{cabinet.nazwa} – confidentiel"),
    ],
    metadane={"author": "{rapporteur.pelne}", "subject": "Due diligence juridique"},
)
