"""Used-car sale between two individuals (bill of sale): England and Wales (V5C, registration mark) or USA (title,
license plate). The vehicle is identified by its registration number; the VIN is not generated and is not mentioned."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="en", typ="umowa_sprzedazy_auta", dorosli=True, warianty=("gb", "us"),
    role={"seller": "osoba", "buyer": "osoba", "vehicle": "sprawa", "witness": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               W("gb", "VEHICLE SALE AGREEMENT"),
               W("us", "MOTOR VEHICLE BILL OF SALE"),
               "Seller: {seller.pelne} | Buyer: {buyer.pelne}"),
        sekcja("opening", "akapit",
               "This agreement is made on {ctx.dok} at {seller.miasto} between:"),
        sekcja("parties", "akapit",
               W("gb", "(1) {seller.pelne}, National Insurance number {seller.nino}, of {seller.adres}, tel. "
                 "{seller.telefon} (the Seller); and"),
               W("gb", "(2) {buyer.pelne}, National Insurance number {buyer.nino}, of {buyer.adres}, tel. "
                 "{buyer.telefon}, e-mail {buyer.email} (the Buyer)."),
               W("us", "{seller.pelne}, SSN {seller.ssn}, residing at {seller.adres}, tel. {seller.telefon} "
                 "(\"Seller\"); and"),
               W("us", "{buyer.pelne}, SSN {buyer.ssn}, residing at {buyer.adres}, tel. {buyer.telefon}, e-mail "
                 "{buyer.email} (\"Buyer\").")),
        sekcja("vehicle", "akapit",
               "1. THE VEHICLE",
               W("gb", "1.1 The Seller sells and the Buyer buys the used passenger car with registration number "
                 "{vehicle.tablica} (the Vehicle), with its V5C registration certificate, MOT certificate, two keys "
                 "and service history."),
               W("us", "1.1 The Seller sells and the Buyer buys the used passenger vehicle bearing license plate "
                 "{vehicle.tablica} (the Vehicle), together with its certificate of title, two keys and service "
                 "records."),
               "1.2 The Seller warrants that he or she is the sole lawful owner, that the Vehicle is free of finance "
               "and liens, and that it has not been written off.",
               "1.3 The Vehicle is insured until {ctx.dok_pozniej}; the Seller notifies the insurer of the sale."),
        sekcja("price", "akapit",
               "2. PRICE AND PAYMENT",
               "2.1 The price is {ctx.szkoda}.",
               "2.2 The Buyer paid a deposit of {ctx.zaliczka_ub} on signing and shall pay the balance by bank "
               "transfer to the Seller's account {seller.rachunek} no later than {ctx.dok_termin}.",
               "2.3 The Buyer bears the costs of re-registering the Vehicle."),
        sekcja("table", "komorka",
               "Item | Condition | Remarks\n"
               "Odometer | 74 310 miles | as shown on the dashboard\n"
               "Inspection | valid until {ctx.dok_pozniej} | certificate attached\n"
               "Accident history | none | declared by {seller.pelne}",
               "Item | Document | Handed to\n"
               "Registration papers | original | {buyer.pelne}\n"
               "Keys | 2 sets | {buyer.pelne}\n"
               "Service invoices | 9 items | {witness.pelne}",
               min=1, max=1),
        sekcja("handover", "akapit",
               "3. DELIVERY AND CONDITION",
               "3.1 The Vehicle will be delivered on {ctx.dok_sprzedaz} at the Seller's address; {witness.pelne} "
               "(tel. {witness.telefon}) attends as witness to the condition of the Vehicle.",
               "3.2 The Buyer has inspected and test-driven the Vehicle and buys it as seen, to the extent the law "
               "permits; risk passes to the Buyer on delivery.",
               W("gb", "3.3 The Seller confirms that the description of the Vehicle given in this agreement is "
                 "accurate, as required by the Consumer Rights Act 2015 where it applies."),
               W("us", "3.3 The Vehicle is sold \"as is\", without warranty of any kind, except as required by "
                 "applicable state law.")),
        sekcja("general", "akapit",
               "4. GENERAL",
               "4.1 Any change to this agreement must be made in writing and signed by both parties.",
               "4.2 Contact for follow-up: {seller.email} and {buyer.telefon}."),
        sekcja("sign_label", "akapit", "Seller:                                                  Buyer:"),
        sekcja("signature", "podpis", "{seller.pelne}", "{buyer.pelne}"),
        sekcja("footer", "stopka", "Vehicle sale – {vehicle.tablica} | {seller.pelne} / {buyer.pelne}"),
        sekcja("note", "przypis",
               W("gb", "The Seller must tell the DVLA about the sale; the Buyer must tax the Vehicle before driving it."),
               W("us", "The Buyer must transfer the title and register the Vehicle with the state motor vehicle "
                 "agency within the period required by state law.")),
    ],
    metadane={"author": "{seller.pelne}", "title": "Vehicle sale agreement"},
)
