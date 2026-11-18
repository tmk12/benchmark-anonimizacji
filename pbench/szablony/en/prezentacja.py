"""Prezentacja kancelarii dla zarządu klienta: wyniki due diligence spółki (krótkie slajdy, tabela ryzyk);
Wielka Brytania (Companies House, CMA) albo USA (UCC, HSR)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="en", typ="prezentacja", warianty=("gb", "us"),
    role={"firm": "kancelaria", "presenter": "osoba", "contact": "osoba", "ceo": "osoba", "target": "firma",
          "client": "firma", "site": "sprawa"},
    sekcje=[
        sekcja("titles", "naglowek",
               "Legal due diligence: {target.nazwa}",
               "Summary of findings",
               "Key transaction risks",
               "Action plan to completion",
               "Contact and next steps"),
        sekcja("slide1", "akapit",
               "Presented by {presenter.pelne}, {firm.nazwa}",
               "Board meeting of {client.nazwa}, {ctx.dok}",
               "Strictly confidential – for the board only"),
        sekcja("slide2", "akapit",
               "Target: {target.nazwa}, {target.adres}",
               W("gb", "Company number {target.company_no}, VAT number {target.vat}"),
               W("us", "EIN {target.ein}, principal office {target.miasto}"),
               "Management interviews were held with {ceo.pelne}, chief executive",
               "Proposed purchase price for the shares: {ctx.cena}"),
        sekcja("slide3", "akapit",
               "Key customer contracts contain change-of-control clauses",
               W("gb", "Records of processing under UK GDPR (Article 30) are out of date"),
               W("us", "No written information security program under applicable state privacy law"),
               "Three disputes pending with an aggregate value of {ctx.sporow}",
               W("gb", "Software licences lack a confirmed chain of title"),
               W("us", "Software licenses lack a confirmed chain of title"),
               "No arrears of payroll taxes identified",
               min=3, max=5),
        sekcja("risks", "komorka",
               "Area | Rating | Recommendation\n"
               "Employment | Medium | Update remuneration policies\n"
               "Data protection | High | Adopt records and processor agreements\n"
               "Real estate | Low | No action\n"
               "Intellectual property | High | Obtain assignments from contractors"),
        sekcja("slide4", "akapit",
               "Sign the share purchase agreement by {ctx.dok_termin_dl}",
               "Conditions precedent: shareholder consent and lender consent",
               "Completion requires the approval of {ceo.pelne} as chief executive of the target",
               W("gb", "Merger control: check the CMA's share-of-supply and turnover thresholds under the "
                 "Enterprise Act 2002"),
               W("us", "Antitrust: assess Hart-Scott-Rodino filing thresholds before signing"),
               min=3, max=4),
        sekcja("slide5", "akapit",
               "Contact: {contact.pelne}, tel. {contact.telefon}, email {contact.email}",
               "Our website: {site.url}",
               "Thank you"),
        sekcja("footer", "stopka", "{firm.nazwa} – confidential"),
    ],
    metadane={"author": "{presenter.pelne}", "subject": "Legal due diligence"},
)
