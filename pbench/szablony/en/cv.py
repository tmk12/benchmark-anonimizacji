"""Życiorys młodego prawnika: Curriculum Vitae (Wielka Brytania, trainee solicitor, NI number) albo résumé (USA, associate
attorney, bar admission); dane kontaktowe, doświadczenie, wykształcenie, referencje. Daty z `Kontekst`."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="en", typ="cv", warianty=("gb", "us"),
    role={"candidate": "osoba", "employer1": "firma", "employer2": "firma", "supervisor": "osoba",
          "advisor": "osoba", "referee": "osoba", "profile": "sprawa", "portfolio": "sprawa"},
    sekcje=[
        sekcja("header", "naglowek",
               "{candidate.pelne}",
               W("gb", "Trainee solicitor | company and commercial law, data protection"),
               W("us", "Associate attorney | corporate transactions and privacy law")),
        sekcja("contact", "akapit",
               "Address: {candidate.adres}",
               "Telephone: {candidate.telefon} | Email: {candidate.email}",
               "Date of birth: {candidate.data_ur}",
               W("gb", "National Insurance number: {candidate.nino}"),
               W("us", "LinkedIn: {profile.url} | GitHub: {candidate.login}"),
               W("gb", "Professional profile: {profile.url} | GitHub: {candidate.login}"),
               min=4, max=5),
        sekcja("summary", "akapit",
               W("gb", "PERSONAL STATEMENT"),
               W("us", "PROFESSIONAL SUMMARY"),
               "Lawyer with three years of experience advising companies on corporate transactions, M&A and data "
               "protection projects. I run matters independently and prepare advice and contracts in English and "
               "Spanish.",
               "I am looking for a role in a team handling cross-border matters, with scope to develop in "
               "technology law.",
               min=3, max=3),
        sekcja("experience", "akapit",
               "PROFESSIONAL EXPERIENCE",
               "{ctx.cv_od1} – present: Junior associate, {employer1.nazwa}, {employer1.adres}. Advising "
               "corporate clients, carrying out due diligence, drafting commercial contracts and attending "
               "negotiations. Line manager: {supervisor.pelne}.",
               "{ctx.cv_od2} – {ctx.cv_do2}: Paralegal, {employer2.nazwa}. Supported the disputes team with file "
               "review, draft pleadings and the deadlines register, working under {supervisor.pelne}.",
               "Secondment to the compliance function: built the record of processing activities and the personal "
               "data breach procedure.",
               min=3, max=3),
        sekcja("education", "akapit",
               "EDUCATION",
               W("gb", "LLB (Hons) in Law, completed {ctx.cv_studia}. Dissertation on company law supervised by "
                 "{advisor.pelne}; Solicitors Qualifying Examination stage 1 passed."),
               W("us", "Juris Doctor, conferred {ctx.cv_studia}. Law review note on corporate governance advised by "
                 "{advisor.pelne}; admitted to the state bar."),
               "Postgraduate certificate in data protection and cybersecurity law.",
               min=2, max=3),
        sekcja("skills", "akapit",
               "SKILLS AND LANGUAGES",
               "Languages: English (native), Spanish (B2). Systems: Westlaw, Practical Law, Microsoft Office, "
               "document management tools.",
               "Courses: negotiation skills, legal design, intellectual property in the technology sector.",
               "Selected publications and advice notes: {portfolio.url}",
               min=2, max=4),
        sekcja("referees", "akapit",
               "REFERENCES",
               "References are available on request. Referee: {referee.pelne}, tel. {referee.telefon}, email "
               "{referee.email}.",
               "A reference from {supervisor.pelne} can be provided at the offer stage.",
               min=2, max=2),
        sekcja("interests", "akapit",
               W("gb", "Interests: sailing, chess, volunteering at a legal advice centre."),
               W("us", "Interests: sailing, chess, volunteering at a legal aid clinic."),
               W("gb", "Full UK driving licence; willing to travel."),
               W("us", "Valid driver's license; willing to travel.")),
        sekcja("consent", "akapit",
               W("gb", "I consent to my personal data being processed for recruitment purposes in accordance with "
                 "the UK GDPR and the Data Protection Act 2018."),
               W("us", "I authorize the prospective employer to verify the information provided in this résumé "
                 "for employment purposes.")),
        sekcja("signature", "podpis", "{candidate.pelne}"),
        sekcja("footer", "stopka",
               W("gb", "CV – {candidate.pelne} | {candidate.email}"),
               W("us", "Résumé – {candidate.pelne} | {candidate.email}")),
    ],
    metadane={"author": "{candidate.pelne}", "subject": "Curriculum vitae"},
)
