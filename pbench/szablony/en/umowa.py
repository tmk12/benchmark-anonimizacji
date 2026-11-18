"""Umowa o świadczenie usług prawnych (kancelaria – spółka klienta) w formie brytyjskiej (agreement) i amerykańskiej
(engagement agreement): wynagrodzenie, poufność, odpowiedzialność, prawo właściwe wg kraju dokumentu."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="en", typ="umowa", dorosli=True, warianty=("gb", "us"),
    role={"firm": "kancelaria", "client": "firma", "partner": "osoba", "director": "osoba", "contact": "osoba",
          "coordinator": "osoba", "deputy": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{firm.nazwa}",
               W("gb", "{firm.adres} | Company No. {firm.company_no} | VAT No. {firm.vat}"),
               W("us", "{firm.adres} | EIN {firm.ein}"),
               W("gb", "Authorised and regulated by the Solicitors Regulation Authority")),
        sekcja("title", "akapit",
               W("gb", "AGREEMENT FOR THE PROVISION OF LEGAL SERVICES"),
               W("us", "ENGAGEMENT AGREEMENT FOR LEGAL SERVICES"),
               W("gb", "This Agreement is made on {ctx.dok} between:"),
               W("us", "This Engagement Agreement (the “Agreement”) is entered into as of {ctx.dok} by and between:")),
        sekcja("parties", "akapit",
               W("gb", "(1) {firm.nazwa} (company number {firm.company_no}), whose "
                 "registered office is at {firm.adres}, acting by {partner.pelne}, "
                 "a partner (the “Firm”); and"),
               W("gb", "(2) {client.nazwa} (company number {client.company_no}), whose "
                 "registered office is at {client.adres} (VAT number {client.vat}), "
                 "acting by {director.pelne}, a director (the “Client”)."),
               W("us", "{firm.nazwa}, with its principal office at {firm.adres} (EIN {firm.ein}), acting by "
                 "{partner.pelne}, Managing Partner (the “Firm”); and"),
               W("us", "{client.nazwa}, a corporation with its principal place of business at {client.adres} "
                 "(EIN {client.ein}), acting by {director.pelne}, Chief Executive Officer (the “Client”)."),
               "The Firm and the Client are each a “Party” and together the “Parties”."),
        sekcja("scope", "akapit",
               "1. SCOPE OF SERVICES",
               "1.1 The Firm shall provide the Client with general legal advice on commercial, employment and data "
               "protection matters, including drafting and reviewing contracts, preparing written advice and "
               "attending negotiations on the Client's behalf (the “Services”).",
               "1.2 The Services do not include representation in contentious proceedings before any court or "
               "tribunal. If such representation is required, the Parties shall agree a separate retainer and fee "
               "arrangement in writing before the Firm takes any step in the proceedings.",
               "1.3 The Firm's relationship partner for the Client is {contact.pelne}. If {contact.rodzaj:he|she} is "
               "unavailable, {deputy.pelne} will act as deputy. A change of relationship partner does not require "
               "an amendment to this Agreement.",
               "1.4 The Client shall provide the information and documents the Firm reasonably requires through "
               "{coordinator.pelne} (telephone {coordinator.telefon}, email {coordinator.email})."),
        sekcja("fees", "akapit",
               "2. FEES AND PAYMENT",
               W("gb", "2.1 In consideration of the Services the Client shall pay the Firm a fixed monthly fee of "
                 "{ctx.um_wyn} exclusive of VAT, which shall be added at the prevailing rate."),
               W("us", "2.1 In consideration of the Services the Client shall pay the Firm a fixed monthly retainer "
                 "of {ctx.um_wyn}, payable in advance on the first business day of each month."),
               "2.2 The fixed fee covers up to twenty hours of lawyers' time per month. Time beyond that allowance "
               "is charged at the Firm's standard hourly rates, and additional charges in any month shall not "
               "exceed {ctx.um_limit} without the Client's prior written approval.",
               "2.3 Invoices are payable within fourteen days of receipt by transfer to the Firm's account "
               "{firm.rachunek}, quoting the invoice number as the payment reference.",
               W("gb", "2.4 Interest accrues on overdue sums at 4% a year above the Bank of England base rate "
                 "in accordance with the Late Payment of Commercial Debts (Interest) Act 1998."),
               W("us", "2.4 Amounts not paid when due bear interest at the lesser of one percent per month and the "
                 "maximum rate permitted by applicable law."),
               min=5, max=6),
        sekcja("confidentiality", "akapit",
               "3. CONFIDENTIALITY",
               "3.1 Each Party shall keep confidential all non-public information received from the other in "
               "connection with this Agreement and shall use it only to perform or receive the Services.",
               "3.2 The obligations in clause 3.1 do not apply to information that is or becomes public other than "
               "through breach, that was lawfully known to the recipient beforehand, or that must be disclosed by "
               "law, regulation or court order, provided the recipient gives prompt notice where permitted.",
               "3.3 Nothing in this clause limits the Firm's professional duties of confidentiality and privilege "
               "owed to the Client, which continue after termination.",
               min=3, max=3),
        sekcja("data", "akapit",
               W("gb", "4. DATA PROTECTION. Each Party shall comply with the UK GDPR and the Data Protection Act "
                 "2018. The Firm processes personal data as an independent controller for the purposes of "
                 "providing the Services and its regulatory obligations."),
               W("us", "4. DATA PRIVACY. The Firm shall maintain commercially reasonable administrative, technical "
                 "and physical safeguards for personal information received from the Client and shall comply with "
                 "applicable state privacy and data breach notification laws."),
               W("gb", "The Firm's privacy notice is available at {client.nazwa}'s request and on the Firm's website."),
               min=1, max=3),
        sekcja("liability", "akapit",
               "5. LIMITATION OF LIABILITY",
               "5.1 Subject to clause 5.3, the Firm's total aggregate liability arising out of or in connection "
               "with the Services, whether in contract, tort or otherwise, shall not exceed {ctx.um_kara}.",
               "5.2 Neither Party is liable to the other for loss of profit, loss of goodwill or any indirect or "
               "consequential loss.",
               "5.3 Nothing in this Agreement limits or excludes liability for fraud, for death or personal injury "
               "caused by negligence, or for any liability that cannot lawfully be limited."),
        sekcja("term", "akapit",
               "6. TERM AND TERMINATION",
               "6.1 This Agreement takes effect on {ctx.od_dnia} and continues for an initial term of twelve "
               "months, after which it renews automatically for successive periods of twelve months.",
               "6.2 Either Party may terminate this Agreement at any time by giving thirty days' written notice "
               "to the other. Fees for Services performed up to the date of termination remain payable.",
               "6.3 On termination the Firm shall return the Client's documents on request, subject to any right "
               "of lien permitted by law.",
               min=3, max=3),
        sekcja("compliance", "akapit",
               W("gb", "7. Each Party shall comply with the Bribery Act 2010 and the Modern Slavery Act 2015 in "
                 "performing this Agreement."),
               W("us", "7. Each Party shall comply with the Foreign Corrupt Practices Act of 1977 and all other "
                 "applicable anti-corruption laws in performing this Agreement."),
               "8. This Agreement is the entire agreement between the Parties on its subject matter and may be "
               "varied only in writing signed by both Parties. No third party has any right to enforce its terms.",
               "9. Notices must be in writing and delivered by hand, by courier or by email with confirmation of "
               "receipt, to the Client at {client.adres} and to the Firm at {firm.adres}, or to any other address "
               "notified in accordance with this clause.",
               min=3, max=3),
        sekcja("law", "akapit",
               W("gb", "10. This Agreement and any non-contractual obligations arising out of or in connection with "
                 "it are governed by the law of England and Wales, and the courts of England and Wales have "
                 "exclusive jurisdiction over any dispute."),
               W("us", "10. This Agreement is governed by the laws of the state in which the Firm's principal office "
                 "is located, without regard to its conflict-of-law rules. The Parties submit to the exclusive "
                 "jurisdiction of the state and federal courts in the county of that office."),
               "11. This Agreement may be executed in counterparts, including by electronic signature, each of "
               "which is an original and all of which together are one instrument."),
        sekcja("signing", "akapit",
               W("gb", "Signed by {partner.pelne} for and on behalf of {firm.nazwa}"),
               W("gb", "Signed by {director.pelne} for and on behalf of {client.nazwa}"),
               W("us", "FOR THE FIRM: By: ____________  Name: {partner.pelne}  Title: Managing Partner"),
               W("us", "FOR THE CLIENT: By: ____________  Name: {director.pelne}  Title: Chief Executive Officer")),
        sekcja("signatures", "podpis", "{partner.pelne}", "{director.pelne}"),
        sekcja("footer", "stopka",
               W("gb", "{firm.nazwa} | {firm.adres} | Company No. {firm.company_no} | VAT No. {firm.vat} | "
                 "tel. {firm.telefon} | {firm.email}"),
               W("us", "{firm.nazwa} | {firm.adres} | EIN {firm.ein} | tel. {firm.telefon} | {firm.email}")),
    ],
    metadane={"author": "{partner.pelne}", "subject": "Agreement for the provision of legal services"},
)
