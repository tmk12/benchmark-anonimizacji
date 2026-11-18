"""Residential tenancy between two individuals: Assured Shorthold Tenancy Agreement (England and Wales) or Residential
Lease Agreement (USA). Landlord and tenant are private persons; the deposit equals one month's rent."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="en", typ="umowa_najmu", dorosli=True, warianty=("gb", "us"),
    role={"landlord": "osoba", "tenant": "osoba", "property": "osoba", "witness": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               W("gb", "ASSURED SHORTHOLD TENANCY AGREEMENT"),
               W("us", "RESIDENTIAL LEASE AGREEMENT"),
               "Landlord: {landlord.pelne} | Tenant: {tenant.pelne}"),
        sekcja("opening", "akapit",
               W("gb", "This Agreement is made on {ctx.dok} at {landlord.miasto} between:"),
               W("us", "This Lease Agreement is entered into on {ctx.dok} in {landlord.miasto} by and between:")),
        sekcja("parties", "akapit",
               W("gb", "(1) {landlord.pelne}, National Insurance number {landlord.nino}, of {landlord.adres}, tel. "
                 "{landlord.telefon}, e-mail {landlord.email} (the Landlord); and"),
               W("gb", "(2) {tenant.pelne}, National Insurance number {tenant.nino}, of {tenant.adres}, tel. "
                 "{tenant.telefon}, e-mail {tenant.email} (the Tenant)."),
               W("us", "{landlord.pelne}, SSN {landlord.ssn}, residing at {landlord.adres}, tel. {landlord.telefon}, "
                 "e-mail {landlord.email} (\"Landlord\"); and"),
               W("us", "{tenant.pelne}, SSN {tenant.ssn}, residing at {tenant.adres}, tel. {tenant.telefon}, "
                 "e-mail {tenant.email} (\"Tenant\").")),
        sekcja("premises", "akapit",
               "1. PREMISES",
               "1.1 The Landlord lets and the Tenant takes the residential dwelling at {property.adres} "
               "(the \"Property\"), together with the fixtures and fittings listed in the inventory, previously "
               "occupied by {property.pelne}, who vacated it on {ctx.umowa_dawna}.",
               "1.2 The Property may be used solely as a private residence for the Tenant and the persons named in "
               "writing to the Landlord."),
        sekcja("term", "akapit",
               "2. TERM",
               "2.1 The tenancy begins on {ctx.od_dnia} and continues for a fixed term ending on {ctx.dok_pozniej}.",
               W("gb", "2.2 After the fixed term the tenancy continues as a statutory periodic tenancy unless it is "
                 "ended by notice under section 21 or section 8 of the Housing Act 1988."),
               W("us", "2.2 After the fixed term the lease continues month to month unless either party gives sixty "
                 "days' written notice of termination.")),
        sekcja("rent", "akapit",
               "3. RENT AND DEPOSIT",
               "3.1 The Tenant shall pay rent of {ctx.zaliczka_kosztow} per calendar month in advance, by bank "
               "transfer to the Landlord's account {landlord.rachunek}, on or before the tenth day of each month.",
               W("gb", "3.2 The Tenant pays a tenancy deposit of {ctx.zaliczka_kosztow} (one month's rent), which the "
                 "Landlord shall protect in a government-authorised scheme within thirty days of receipt."),
               W("us", "3.2 The Tenant pays a security deposit of {ctx.zaliczka_kosztow} (one month's rent), which the "
                 "Landlord shall hold in a separate account and return within thirty days after the Tenant vacates, "
                 "less lawful deductions."),
               "3.3 The Tenant pays utilities and council or municipal charges directly to the suppliers according to "
               "consumption."),
        sekcja("duties", "akapit",
               "4. OBLIGATIONS",
               "4.1 The Tenant shall keep the Property clean and in good condition, shall not sublet or assign it "
               "without the Landlord's written consent, and shall report any damage promptly to the Landlord.",
               "4.2 The Landlord shall keep the structure and installations in repair and may enter the Property to "
               "inspect it, with at least twenty-four hours' written notice, in the Tenant's presence.",
               "4.3 The handover of keys and the meter readings are recorded in the check-in report; "
               "{witness.pelne} (tel. {witness.telefon}) attends the handover on behalf of the Landlord.",
               min=2, max=3),
        sekcja("table", "komorka",
               "Item | Reading at check-in | Notes\n"
               "Electricity meter | 04 213 kWh | read in both parties' presence\n"
               "Water meter | 118 units | no remarks\n"
               "Keys | 3 sets | handed to {tenant.pelne}",
               "Item | Due date | Responsible party\n"
               "Monthly rent | tenth day of the month | {tenant.pelne}\n"
               "Return of deposit | thirty days after move-out | {landlord.pelne}\n"
               "Check-in | {ctx.od_dnia} | {witness.pelne}",
               min=1, max=1),
        sekcja("general", "akapit",
               "5. GENERAL",
               "5.1 This Agreement is the entire agreement between the parties and may be varied only in writing "
               "signed by both of them.",
               "5.2 Notices shall be sent to the addresses above, or by e-mail to {landlord.email} and "
               "{tenant.email}.",
               W("gb", "5.3 This Agreement is governed by the law of England and Wales."),
               W("us", "5.3 This Lease is governed by the law of the state in which the Property is located.")),
        sekcja("sign_label", "akapit", "Landlord:                                                  Tenant:"),
        sekcja("signature", "podpis", "{landlord.pelne}", "{tenant.pelne}"),
        sekcja("footer", "stopka",
               "Tenancy agreement – {landlord.pelne} / {tenant.pelne} | Property: {property.adres}"),
        sekcja("note", "przypis",
               W("gb", "A copy of the \"How to rent\" guide, the gas safety certificate and the energy performance "
                 "certificate were given to the Tenant on {ctx.dok}."),
               W("us", "The Landlord has disclosed to the Tenant all known lead-based paint hazards in the Property "
                 "on {ctx.dok}.")),
    ],
    metadane={"author": "{landlord.pelne}", "title": "Residential tenancy agreement"},
)
