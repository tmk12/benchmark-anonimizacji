"""Pozew o zapłatę z umowy pożyczki: Particulars of Claim (Anglia i Walia: County Court albo High Court) albo
Complaint (USA: sąd federalny albo stanowy). Poziom sądu i sygnatura wynikają z wariantu; daty i kwoty z `Kontekst`."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="en", typ="pozew", warianty=("gb_county", "gb_high", "us_federal", "us_state"),
    role={"firm": "kancelaria", "counsel": "osoba", "claimant": "osoba", "defendant": "osoba", "witness": "osoba",
          "witness2": "osoba", "court": "sad", "prior": "sprawa"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{counsel.pelne} – {firm.nazwa}",
               "{firm.adres}, tel. {firm.telefon}"),
        sekcja("court", "akapit",
               W("gb", "IN THE {court.nazwa:upper}"),
               W("us", "{court.nazwa:upper}"),
               W("gb", "Claim No. {court.sygnatura}"),
               W("us", "{court.sygnatura}")),
        sekcja("parties", "akapit",
               W("gb", "BETWEEN:"),
               W("gb", "{claimant.pelne} (Claimant)"),
               W("gb", "– and –"),
               W("gb", "{defendant.pelne} (Defendant)"),
               W("us", "{claimant.pelne}, Plaintiff,"),
               W("us", "v."),
               W("us", "{defendant.pelne}, Defendant.")),
        sekcja("title", "akapit",
               W("gb", "PARTICULARS OF CLAIM"),
               W("us", "COMPLAINT FOR BREACH OF CONTRACT AND DEMAND FOR JURY TRIAL")),
        sekcja("jurisdiction", "akapit",
               W("gb_county", "1. The Claimant's claim is for repayment of a loan and interest. The value of the claim "
                 "is less than £100,000 and this Court has jurisdiction under section 15 of the County Courts Act "
                 "1984. The Claimant's address for service is {claimant.adres}."),
               W("gb_high", "1. The Claimant's claim is for repayment of a loan and interest. The value of the claim "
                 "exceeds £100,000 and the Claimant therefore issues in the High Court in accordance with the "
                 "Practice Direction to CPR Part 7. The Defendant is domiciled in England and Wales."),
               W("us_federal", "1. This Court has subject-matter jurisdiction under 28 U.S.C. § 1332(a): the amount in "
                 "controversy exceeds $75,000, exclusive of interest and costs, and the parties are alleged to be "
                 "citizens of different States. Venue is proper under 28 U.S.C. § 1391(b)."),
               W("us_state", "1. This Court has subject-matter jurisdiction over this action and personal "
                 "jurisdiction over Defendant. Venue is proper in this county under the applicable state venue "
                 "statute because the loan was negotiated and was to be repaid here."),
               W("gb", "2. The Claimant is an individual resident at {claimant.adres}. The Defendant is an individual "
                 "resident at {defendant.adres}."),
               W("us", "2. Plaintiff {claimant.pelne} is an individual residing at {claimant.adres}. Defendant "
                 "{defendant.pelne} is an individual residing at {defendant.adres}.")),
        sekcja("facts", "akapit",
               W("gb", "3. By a written loan agreement dated {ctx.umowa} the Claimant lent the Defendant the sum of "
                 "{ctx.glowna}, repayable by the date stated in the agreement. The sum was paid to the Defendant's "
                 "account {defendant.rachunek} on the day the agreement was signed."),
               W("us", "3. On {ctx.umowa}, Plaintiff and Defendant entered into a written loan agreement under "
                 "which Plaintiff lent Defendant {ctx.glowna}, to be repaid by the date stated in the agreement. "
                 "Plaintiff wired the funds to Defendant's account ({defendant.rachunek}) the same day."),
               "4. The loan fell due for repayment on {ctx.termin_platnosci}. The Defendant did not repay it.",
               W("gb", "5. On {ctx.wezwanie} the Claimant's solicitors sent the Defendant a letter before claim "
                 "to {defendant.adres}, giving fourteen days to pay. The Defendant did not reply."),
               W("us", "5. On {ctx.wezwanie}, Plaintiff's counsel sent Defendant a written demand by certified mail "
                 "to {defendant.adres}, giving fourteen days to pay. Defendant did not respond."),
               "6. In or around the same period the Defendant acknowledged the debt in conversation with "
               "{witness.pelne} and later in a telephone call witnessed by {witness2.pelne} (tel. "
               "{witness2.telefon}).",
               W("gb", "7. Separate interim injunction proceedings were previously brought in claim number "
                 "{prior.sygnatura}; those proceedings were concluded by consent."),
               W("us", "7. A prior action concerning the same loan was filed as {prior.sygnatura} and was "
                 "voluntarily dismissed without prejudice."),
               min=5, max=7),
        sekcja("law", "akapit",
               W("gb", "8. The Defendant is in breach of the loan agreement. The Claimant is entitled to repayment of "
                 "the principal and to interest under section 69 of the County Courts Act 1984 (alternatively "
                 "section 35A of the Senior Courts Act 1981) at such rate and for such period as the Court thinks "
                 "fit."),
               W("us", "8. Defendant has breached the loan agreement by failing to repay the principal when due. "
                 "Plaintiff has performed all of its obligations under the agreement and has been damaged in the "
                 "amount of the unpaid principal together with pre-judgment interest as permitted by law.")),
        sekcja("relief", "akapit",
               W("gb", "AND THE CLAIMANT CLAIMS:"),
               W("us", "WHEREFORE, Plaintiff respectfully requests that the Court enter judgment in its favor and "
                 "against Defendant as follows:"),
               W("gb", "(1) The sum of {ctx.glowna} by way of repayment of the loan;"),
               W("us", "(a) damages in the amount of {ctx.glowna};"),
               W("gb", "(2) Interest pursuant to the Court's statutory power, at the rate of 8% a year from "
                 "{ctx.termin_platnosci} until judgment or earlier payment;"),
               W("us", "(b) pre-judgment and post-judgment interest at the maximum rate permitted by law, running "
                 "from {ctx.termin_platnosci};"),
               W("gb", "(3) Costs."),
               W("us", "(c) the costs of this action, including reasonable attorneys' fees where permitted by "
                 "contract or statute; and such other relief as the Court deems just and proper.")),
        sekcja("fee", "akapit",
               W("gb", "The court fee payable on issue is {ctx.oplata_pozwu}."),
               W("us", "A filing fee of {ctx.oplata_pozwu} has been paid to the Clerk of Court.")),
        sekcja("truth", "akapit",
               W("gb", "STATEMENT OF TRUTH. I believe that the facts stated in these Particulars of Claim are "
                 "true. I am duly authorised by the Claimant to sign this statement."),
               W("us", "Dated: {ctx.pozew}. Respectfully submitted,")),
        sekcja("signature", "podpis", "{counsel.pelne}"),
        sekcja("service", "akapit",
               W("gb", "Dated {ctx.pozew}. Served at the Claimant's solicitors: {firm.nazwa}, {firm.adres}."),
               W("us", "Attorney for Plaintiff: {counsel.pelne}, {firm.nazwa}, {firm.adres}.")),
        sekcja("footer", "stopka",
               W("gb", "{firm.nazwa} | {firm.adres} | Company No. {firm.company_no} | tel. {firm.telefon} | "
                 "{firm.email}"),
               W("us", "{firm.nazwa} | {firm.adres} | EIN {firm.ein} | tel. {firm.telefon} | {firm.email}")),
    ],
    metadane={"author": "{counsel.pelne}", "subject": "Particulars of claim / complaint"},
)
