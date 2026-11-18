"""Wyciąg z rejestru spółek: Companies House (Company Profile, Wielka Brytania) albo Certificate of Good Standing
stanu USA (Secretary of State); tabela organów — członkowie zarządu z datą urodzenia i identyfikatorem, wspólnicy,
kapitał, daty rejestracji z `Kontekst`."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="en", typ="odpis_rejestru", dorosli=True, warianty=("gb", "us"),
    role={"company": "firma", "d1": "osoba", "d2": "osoba", "d3": "osoba", "secretary": "osoba", "owner1": "osoba",
          "owner2": "osoba", "chair": "osoba", "agent": "osoba"},
    sekcje=[
        sekcja("titles", "naglowek",
               W("gb", "COMPANIES HOUSE – COMPANY PROFILE"),
               W("us", "STATE OF DELAWARE – SECRETARY OF STATE – CERTIFICATE OF GOOD STANDING"),
               "{company.nazwa}"),
        sekcja("identity", "komorka",
               W("gb", "Field | Details\n"
                 "Company name | {company.nazwa}\n"
                 "Company number | {company.company_no}\n"
                 "Registered office address | {company.adres}\n"
                 "VAT number | {company.vat}\n"
                 "Company status | Active"),
               W("us", "Field | Details\n"
                 "Entity name | {company.nazwa}\n"
                 "Federal EIN | {company.ein}\n"
                 "Principal office | {company.adres}\n"
                 "Registered agent | {agent.pelne}\n"
                 "Status | In good standing")),
        sekcja("dates", "komorka",
               W("gb", "Event | Date\n"
                 "Incorporated on | {ctx.kr_rejestracja}\n"
                 "Last accounts made up to | {ctx.kr_wpis}\n"
                 "Issued share capital | {ctx.kapital2}"),
               W("us", "Event | Date\n"
                 "Date of incorporation | {ctx.kr_rejestracja}\n"
                 "Date of last annual report | {ctx.kr_wpis}\n"
                 "Authorised capital stock | {ctx.kapital2}")),
        sekcja("officers_title", "akapit",
               W("gb", "Officers of the company (statutory register extract)"),
               W("us", "Directors and officers of record")),
        sekcja("officers", "komorka",
               W("gb", "No. | Surname | Forename | Date of birth | Role | Identifier\n"
                 "1 | {d1.nazwisko} | {d1.imie} | {d1.data_ur} | Director | {d1.nino}\n"
                 "2 | {d2.nazwisko} | {d2.imie} | {d2.data_ur} | Director | {d2.nino}\n"
                 "3 | {d3.nazwisko} | {d3.imie} | {d3.data_ur} | Director and secretary | {d3.nino}"),
               W("gb", "Role | Name | Date of birth | National Insurance no. | Correspondence address\n"
                 "Director | {d1.pelne} | {d1.data_ur} | {d1.nino} | {d1.adres}\n"
                 "Director | {d2.pelne} | {d2.data_ur} | {d2.nino} | {d2.adres}\n"
                 "Secretary | {secretary.pelne} | {secretary.data_ur} | {secretary.nino} | {secretary.adres}"),
               W("us", "No. | Last name | First name | Date of birth | Title | SSN\n"
                 "1 | {d1.nazwisko} | {d1.imie} | {d1.data_ur} | Chief Executive Officer | {d1.ssn}\n"
                 "2 | {d2.nazwisko} | {d2.imie} | {d2.data_ur} | President | {d2.ssn}\n"
                 "3 | {d3.nazwisko} | {d3.imie} | {d3.data_ur} | Secretary | {d3.ssn}"),
               W("us", "Title | Name | Date of birth | Taxpayer ID (SSN) | Residence address\n"
                 "Director | {d1.pelne} | {d1.data_ur} | {d1.ssn} | {d1.adres}\n"
                 "Director | {d2.pelne} | {d2.data_ur} | {d2.ssn} | {d2.adres}\n"
                 "Secretary | {secretary.pelne} | {secretary.data_ur} | {secretary.ssn} | {secretary.adres}"),
               min=1, max=1),
        sekcja("holders", "komorka",
               W("gb", "Persons with significant control | Name | Shares | Nature of control\n"
                 "1 | {owner1.pelne} | {ctx.udzialy1} | Ownership of shares – 25% to 50%\n"
                 "2 | {owner2.pelne} | {ctx.udzialy2} | Ownership of shares – 25% to 50%"),
               W("us", "Stockholder | Name | Shares | Class\n"
                 "1 | {owner1.pelne} | {ctx.udzialy1} | Common\n"
                 "2 | {owner2.pelne} | {ctx.udzialy2} | Common"),
               min=0, max=1),
        sekcja("oversight", "akapit",
               W("gb", "Chair of the board: {chair.pelne}. The company is not in liquidation and no administrator "
                 "has been appointed."),
               W("us", "Chair of the board of directors: {chair.pelne}. The corporation is not in dissolution and "
                 "no receiver has been appointed."),
               W("gb", "Nature of business (SIC): 69102 – solicitors; 70229 – management consultancy activities "
                 "other than financial management."),
               W("us", "Purpose: to engage in any lawful act or activity for which corporations may be organized "
                 "under the General Corporation Law of the State of Delaware."),
               "Accounting reference date: 31 December. The company's term is unlimited.",
               min=2, max=3),
        sekcja("certification", "akapit",
               W("gb", "This extract is generated from the public register under the Companies Act 2006 and shows "
                 "the position at the date of printing. It is not a certified copy."),
               W("us", "I, the Secretary of State, do hereby certify that the above-named entity is duly "
                 "incorporated and has paid all fees and franchise taxes due to date.")),
        sekcja("footer", "stopka",
               W("gb", "Extract generated from the Companies House register | Company {company.company_no} | "
                 "Page 1 of 2"),
               W("us", "Certificate generated by the Division of Corporations | EIN {company.ein} | Page 1 of 2")),
    ],
    metadane={"subject": "Company register extract", "entity": "{company.nazwa}"},
)
