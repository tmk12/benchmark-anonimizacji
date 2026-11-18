"""Pełnomocnictwo: Lasting Power of Attorney (Wielka Brytania; mocodawca = donor, ustawa Mental Capacity Act 2005)
albo Durable Power of Attorney (USA; principal i agent, poświadczenie notarialne). Papier firmowy kancelarii."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="en", typ="pelnomocnictwo", dorosli=True, warianty=("gb", "us"),
    role={"firm": "kancelaria", "donor": "osoba", "attorney": "osoba", "replacement": "osoba",
          "certifier": "osoba", "notary": "osoba", "solicitor": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{firm.nazwa}",
               "{firm.adres}",
               W("gb", "Authorised and regulated by the Solicitors Regulation Authority")),
        sekcja("place", "akapit",
               "{donor.miasto}, {ctx.dok}",
               "Prepared for signature by {solicitor.pelne} of {firm.nazwa}"),
        sekcja("title", "akapit",
               W("gb", "LASTING POWER OF ATTORNEY FOR PROPERTY AND FINANCIAL AFFAIRS"),
               W("us", "DURABLE POWER OF ATTORNEY"),
               W("gb", "Made under the Mental Capacity Act 2005. This document is not valid until it has been "
                 "registered with the Office of the Public Guardian."),
               W("us", "Made under the Uniform Power of Attorney Act as enacted in the donor's state of residence. "
                 "NOTICE: this document gives your agent broad powers over your property. Read it carefully.")),
        sekcja("appointment", "akapit",
               W("gb", "1. The donor. I, {donor.pelne}, born on {donor.data_ur}, of {donor.adres}, National "
                 "Insurance number {donor.nino}, appoint {attorney.pelne}, of {attorney.adres}, born on "
                 "{attorney.data_ur}, to be my attorney to make decisions about my property and financial affairs."),
               W("us", "1. Appointment. I, {donor.pelne}, residing at {donor.adres} (Social Security No. "
                 "{donor.ssn}, date of birth {donor.data_ur}), the “Principal”, appoint {attorney.pelne}, residing "
                 "at {attorney.adres}, as my attorney-in-fact (my “Agent”)."),
               W("gb", "2. Replacement attorney. If {attorney.pelne} cannot act for any reason, I appoint "
                 "{replacement.pelne}, of {replacement.adres}, as my replacement attorney."),
               W("us", "2. Successor Agent. If {attorney.pelne} resigns, dies, becomes incapacitated or is "
                 "otherwise unable to serve, I appoint {replacement.pelne}, residing at {replacement.adres}, as "
                 "successor Agent.")),
        sekcja("powers", "akapit",
               W("gb", "3. How my attorneys may act. Where I have appointed more than one attorney they must act "
                 "jointly and severally, and my attorney may act while I still have capacity unless I direct "
                 "otherwise in writing."),
               W("us", "3. Powers. My Agent may transact business on my behalf in every matter of banking, real "
                 "estate, tax, insurance, investment and litigation, and may sign, deliver and file any "
                 "instrument I could sign myself."),
               "My attorney may operate my bank account {donor.rachunek}, pay my bills and deal with the tax "
               "authorities on my behalf, and may give a receipt for any sum due to me.",
               "My attorney may communicate with institutions on my behalf, including by telephone on "
               "{donor.telefon} or by email to {donor.email}, and may request copies of statements and records.",
               W("gb", "My attorney may not make a gift of my property except modest seasonal gifts and gifts "
                 "to charities to which I habitually gave, as permitted by section 12 of the Mental Capacity Act "
                 "2005."),
               W("us", "My Agent may not make gifts of my property, change the beneficiary of any life insurance "
                 "policy or create or amend a will or trust on my behalf, unless I have initialed the relevant "
                 "grant of authority below."),
               min=4, max=5),
        sekcja("duration", "akapit",
               W("gb", "4. This lasting power of attorney continues if I lose capacity, and my attorney's authority "
                 "to deal with my property is subject to the conditions in the Mental Capacity Act 2005."),
               W("us", "4. DURABILITY. This power of attorney is durable and is not affected by my subsequent "
                 "disability or incapacity. It takes effect immediately and remains effective until I revoke it "
                 "in writing or until my death.")),
        sekcja("revocation", "akapit",
               "5. I may revoke this power at any time while I have capacity by written notice delivered to my "
               "attorney and to any third party that has relied on it.",
               "6. A photocopy or electronically certified copy of this document shall be as effective as the "
               "original in dealings with banks, brokers and government agencies.",
               min=1, max=2),
        sekcja("certificate", "akapit",
               W("gb", "CERTIFICATE PROVIDER. I, {certifier.pelne}, of {certifier.adres}, certify that the donor "
                 "{donor.pelne} understands the purpose of this instrument and the scope of the authority "
                 "conferred, and that no fraud or undue pressure is being used to induce {donor.rodzaj:him|her} "
                 "to create it. I have known the donor for more than two years."),
               W("us", "ACKNOWLEDGMENT. On {ctx.dok}, before me, {notary.pelne}, a Notary Public, personally "
                 "appeared {donor.pelne}, who proved to me on the basis of satisfactory evidence to be the "
                 "person whose name is subscribed to this instrument and acknowledged that "
                 "{donor.rodzaj:he|she} executed it voluntarily."),
               W("us", "Notary contact: {notary.pelne}, {notary.adres}, tel. {notary.telefon}.")),
        sekcja("signing", "akapit",
               "Signature of the donor: ____________________",
               W("gb", "Witnessed by {certifier.pelne} on {ctx.dok}."),
               W("us", "Witnessed by {certifier.pelne}, residing at {certifier.adres}.")),
        sekcja("signature", "podpis", "{donor.pelne}"),
        sekcja("footer", "stopka",
               W("gb", "{firm.nazwa} | {firm.adres} | Company No. {firm.company_no} | VAT No. {firm.vat} | "
                 "tel. {firm.telefon} | {firm.email}"),
               W("us", "{firm.nazwa} | {firm.adres} | EIN {firm.ein} | tel. {firm.telefon} | {firm.email}")),
        sekcja("note", "przypis",
               W("gb", "The Office of the Public Guardian charges a registration fee, which may be reduced or "
                 "waived on the grounds of low income."),
               W("us", "This form should be recorded with the county recorder when real estate transactions are "
                 "contemplated."),
               min=0, max=1),
    ],
    metadane={"author": "{solicitor.pelne}", "subject": "Power of attorney"},
)
