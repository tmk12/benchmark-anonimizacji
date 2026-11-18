"""Curriculum vitae d'un(e) avocat(e) collaborateur(trice) (jeune diplômé(e), France): état civil, profil, expérience,
formation (master 2, CAPA), langues et outils, références, consentement RGPD. Daty z `Kontekst`: master < stage < poste
précédent <= poste actuel."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja
from ._formy import g

SZABLON = Szablon(
    jezyk="fr", typ="cv",
    role={"candidat": "osoba", "employeur1": "kancelaria", "employeur2": "kancelaria", "responsable": "osoba",
          "ref1": "osoba", "ref2": "osoba", "site": "sprawa"},
    sekcje=[
        sekcja("header", "naglowek",
               "CURRICULUM VITAE",
               "{candidat.pelne}"),
        sekcja("contact", "akapit",
               g("candidat", "Né", "Née") + " le {candidat.data_ur}",
               "Nationalité : française",
               "Adresse : {candidat.adres}",
               "Téléphone : {candidat.telefon} | Courriel : {candidat.email}",
               "Profil professionnel : {site.url}",
               min=4, max=5),
        sekcja("summary", "akapit",
               g("candidat", "Avocat collaborateur", "Avocate collaboratrice") + " en droit des affaires, avec une "
               "expérience en droit commercial, droit des sociétés, contrats et contentieux, "
               + g("candidat", "rigoureux", "rigoureuse") + " et " + g("candidat", "orienté", "orientée") + " client.",
               "Intérêt particulier pour le droit des sociétés, la protection des données et la procédure civile.",
               g("candidat", "Inscrit", "Inscrite") + " au barreau, à l'aise avec le RPVA et les logiciels de gestion "
               "de cabinet.",
               min=2, max=3),
        sekcja("experience_title", "akapit", "EXPÉRIENCE PROFESSIONNELLE"),
        sekcja("experience", "akapit",
               "{ctx.cv_od1} – aujourd'hui : " + g("candidat", "Avocat collaborateur", "Avocate collaboratrice")
               + " chez {employeur1.nazwa}, {employeur1.adres}. Conseil de PME en droit commercial et en droit du travail, "
               "rédaction de contrats et préparation d'assemblées générales.",
               "Encadrement : {responsable.pelne}.",
               "{ctx.cv_od2} – {ctx.cv_do2} : " + g("candidat", "élève-avocat", "élève-avocate") + " en stage chez "
               "{employeur2.nazwa}, appui du pôle contentieux pour la rédaction d'assignations, de conclusions et de "
               "bordereaux de pièces.",
               min=3, max=3),
        sekcja("education_title", "akapit", "FORMATION"),
        sekcja("education", "akapit",
               "Master 2 Droit des affaires, diplôme obtenu le {ctx.cv_studia}.",
               "Certificat d'aptitude à la profession d'avocat (CAPA) après la scolarité à l'école d'avocats.",
               "Formations complémentaires : protection des données personnelles (RGPD) et droit des entreprises en "
               "difficulté.",
               min=2, max=3),
        sekcja("skills", "akapit",
               "Langues : français (langue maternelle), anglais (courant), espagnol (notions).",
               "Outils : suite bureautique, RPVA, bases de données juridiques, signature électronique qualifiée.",
               "Atouts : rédaction juridique, négociation, gestion du temps, travail en équipe.",
               min=2, max=3),
        sekcja("referees", "akapit",
               "Références : {ref1.pelne}, tél. {ref1.telefon} ; {ref2.pelne}, courriel {ref2.email}."),
        sekcja("interests", "akapit",
               "Centres d'intérêt : randonnée, échecs, bénévolat dans une permanence juridique gratuite.",
               "Disponibilité : immédiate, temps plein.",
               min=1, max=2),
        sekcja("consent", "akapit",
               "Je consens au traitement de mes données personnelles pour les besoins du processus de recrutement, "
               "conformément au RGPD ; je peux retirer mon consentement à tout moment."),
        sekcja("signature", "podpis", "{candidat.pelne}"),
        sekcja("footer", "stopka", "{candidat.pelne} | {candidat.email} | Tél. {candidat.telefon}"),
    ],
    metadane={"author": "{candidat.pelne}", "subject": "Curriculum vitae"},
)
