"""Claim for the unpaid balance of the price of a car sold between two individuals, filed by the claimant in person
(England and Wales: County Court claim form particulars; USA: pro se complaint in a state court)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="en", typ="pozew_zaplata_osoby", warianty=("gb_county", "us_state"), dorosli=True,
    role={"claimant": "osoba", "defendant": "osoba", "witness": "osoba", "witness2": "osoba", "vehicle": "sprawa",
          "court": "sad"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{claimant.pelne}",
               "{claimant.adres}, tel. {claimant.telefon}, e-mail {claimant.email}"),
        sekcja("court", "akapit",
               W("gb", "IN THE {court.nazwa:upper}"),
               W("us", "{court.nazwa:upper}"),
               W("gb", "Claim No. {court.sygnatura}"),
               W("us", "{court.sygnatura}")),
        sekcja("parties", "akapit",
               W("gb", "BETWEEN:"),
               W("gb", "{claimant.pelne} (Claimant), of {claimant.adres}"),
               W("gb", "– and –"),
               W("gb", "{defendant.pelne} (Defendant), of {defendant.adres}"),
               W("us", "{claimant.pelne}, Plaintiff, pro se,"),
               W("us", "v."),
               W("us", "{defendant.pelne}, Defendant, residing at {defendant.adres}.")),
        sekcja("title", "akapit",
               W("gb", "PARTICULARS OF CLAIM – UNPAID BALANCE OF PURCHASE PRICE"),
               W("us", "COMPLAINT FOR PAYMENT OF THE UNPAID BALANCE OF A PURCHASE PRICE")),
        sekcja("facts", "akapit",
               "1. On {ctx.umowa} the Claimant sold the Defendant a used car with registration number "
               "{vehicle.tablica} under a written sale agreement and delivered it the same day.",
               "2. The Defendant paid only part of the price. The balance of {ctx.glowna} was payable by "
               "{ctx.termin_platnosci} into the Claimant's account {claimant.rachunek} and has not been paid.",
               W("gb", "3. On {ctx.wezwanie} the Claimant wrote to the Defendant at {defendant.adres}, giving until "
                 "{ctx.termin_wezwania} to pay, in accordance with the Practice Direction on Pre-Action Conduct. "
                 "There was no reply."),
               W("us", "3. On {ctx.wezwanie} Plaintiff sent Defendant a written demand by certified mail to "
                 "{defendant.adres}, requiring payment by {ctx.termin_wezwania}. Defendant did not respond."),
               "4. The Defendant admitted the debt to {witness.pelne} and later in a call witnessed by "
               "{witness2.pelne} (tel. {witness2.telefon}).",
               min=3, max=4),
        sekcja("law", "akapit",
               W("gb", "5. The Defendant is in breach of the sale agreement. The Claimant is entitled to the balance of "
                 "the price and to interest under section 69 of the County Courts Act 1984."),
               W("us", "5. Defendant has breached the sale contract by failing to pay the balance of the price, and "
                 "Plaintiff has been damaged in the amount of the unpaid balance plus interest permitted by law.")),
        sekcja("relief", "akapit",
               W("gb", "AND THE CLAIMANT CLAIMS: (1) the sum of {ctx.glowna}; (2) interest at 8% a year from "
                 "{ctx.termin_platnosci}; (3) the court fee of {ctx.oplata_pozwu} and costs."),
               W("us", "WHEREFORE, Plaintiff requests judgment against Defendant for (a) {ctx.glowna}; (b) interest "
                 "from {ctx.termin_platnosci}; and (c) the filing fee of {ctx.oplata_pozwu} and costs of suit.")),
        sekcja("truth", "akapit",
               W("gb", "STATEMENT OF TRUTH. I believe that the facts stated in these Particulars of Claim are true."),
               W("us", "Dated: {ctx.pozew}. Respectfully submitted,")),
        sekcja("signature", "podpis", "{claimant.pelne}"),
        sekcja("footer", "stopka", "{claimant.pelne} | {claimant.adres} | tel. {claimant.telefon} | {claimant.email}"),
        sekcja("note", "przypis",
               "The court fee was paid from the Claimant's account {claimant.rachunek}; the Claimant acts without a lawyer."),
    ],
    metadane={"author": "{claimant.pelne}", "subject": "Claim for payment between individuals"},
)
