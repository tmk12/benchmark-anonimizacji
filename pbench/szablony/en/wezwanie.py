"""Przedsądowe wezwanie do zapłaty: letter before action (Anglia i Walia, Pre-Action Protocol for Debt Claims) albo
demand letter (USA, z uwagą o Fair Debt Collection Practices Act) od kancelarii w imieniu wierzyciela-spółki."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="en", typ="wezwanie", warianty=("gb", "us"),
    role={"firm": "kancelaria", "counsel": "osoba", "creditor": "firma", "officer": "osoba", "debtor": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{firm.nazwa}",
               "{firm.adres} | tel. {firm.telefon}"),
        sekcja("date", "akapit",
               "{firm.miasto}, {ctx.wezwanie}",
               W("gb", "Our ref: LBA/{ctx.wezwanie}"),
               W("us", "Via certified mail, return receipt requested")),
        sekcja("addressee", "akapit",
               W("gb", "BY RECORDED DELIVERY AND EMAIL"),
               "{debtor.pelne}",
               "{debtor.adres}",
               W("gb", "By email: {debtor.email}"),
               W("us", "Email: {debtor.email}"),
               min=3, max=5),
        sekcja("salutation", "akapit",
               W("gb", "Dear {debtor.rodzaj:Mr|Ms} {debtor.nazwisko},"),
               W("us", "Dear {debtor.rodzaj:Mr.|Ms.} {debtor.nazwisko}:")),
        sekcja("heading", "akapit",
               W("gb", "LETTER BEFORE ACTION – FINAL DEMAND FOR PAYMENT"),
               W("us", "FINAL DEMAND FOR PAYMENT – NOTICE OF INTENT TO FILE SUIT")),
        sekcja("basis", "akapit",
               W("gb", "We act for {creditor.nazwa} (company number {creditor.company_no}) of {creditor.adres} "
                 "(the “Creditor”), which is represented by {officer.pelne}. We write to you in accordance with the "
                 "Pre-Action Protocol for Debt Claims."),
               W("us", "This firm represents {creditor.nazwa} of {creditor.adres} (EIN {creditor.ein}) (the "
                 "“Creditor”), through its authorized officer {officer.pelne}. This letter is a formal demand for "
                 "payment of the debt described below."),
               "Our client supplied services to you under an invoice dated {ctx.umowa}. Payment fell due on "
               "{ctx.termin_platnosci} and has not been made despite earlier reminders.",
               "The sums outstanding are: principal of {ctx.glowna}; interest accrued to the date of this letter of "
               "{ctx.odsetki}; and collection costs of {ctx.koszty_wind}. The total now due is {ctx.razem_wez}."),
        sekcja("payment", "akapit",
               "Payment must be received by {ctx.termin_wezwania}. Please pay to the account of the Creditor, "
               "{creditor.rachunek}, quoting the invoice number and your surname as the reference.",
               W("gb", "Interest continues to accrue at the rate of 8% a year under the Late Payment of Commercial "
                 "Debts (Interest) Act 1998 until payment in full."),
               W("us", "Interest will continue to accrue at the rate permitted by the parties' agreement or, in its "
                 "absence, by applicable state law, until payment in full."),
               W("gb", "If you wish to propose an instalment arrangement, please contact us before that date. Our "
                 "client will consider a first instalment of not less than {ctx.ugoda_rata}."),
               W("us", "If you wish to propose an installment arrangement, please contact us before that date. Our "
                 "client will consider a first installment of not less than {ctx.ugoda_rata}."),
               min=3, max=5),
        sekcja("consequences", "akapit",
               W("gb", "If we do not receive payment or a reasonable proposal by that date, our client intends to "
                 "issue proceedings in the County Court without further notice, and will ask the court to order you "
                 "to pay the debt, interest and costs under CPR Part 44."),
               W("us", "If we do not receive payment or a reasonable proposal by that date, our client intends to "
                 "file suit in the appropriate court without further notice, seeking the debt, interest, "
                 "court costs and attorneys' fees to the extent permitted by contract or law."),
               W("gb", "You should read the enclosed information sheet, reply form and financial statement form. "
                 "Free independent advice is available from Citizens Advice, StepChange and the National Debtline."),
               W("us", "Unless you notify this office within thirty days that you dispute the validity of the "
                 "debt, we will assume it is valid, as provided in the Fair Debt Collection Practices Act, 15 "
                 "U.S.C. § 1692g."),
               "This letter is sent without prejudice to any other right or remedy of our client, all of which are "
               "expressly reserved.",
               min=3, max=4),
        sekcja("contact", "akapit",
               "Please contact {counsel.pelne} on {counsel.telefon} or at {counsel.email}, quoting the reference "
               "above, if you have any questions.",
               "A copy of the invoice and the statement of account are enclosed.",
               min=1, max=2),
        sekcja("close", "akapit",
               W("gb", "Yours sincerely,"),
               W("us", "Very truly yours,")),
        sekcja("signature", "podpis", "{counsel.pelne}"),
        sekcja("cc", "akapit",
               "cc: {officer.pelne}, {creditor.nazwa}"),
        sekcja("footer", "stopka",
               W("gb", "{firm.nazwa} | {firm.adres} | Company No. {firm.company_no} | VAT No. {firm.vat} | "
                 "tel. {firm.telefon} | {firm.email}"),
               W("us", "{firm.nazwa} | {firm.adres} | EIN {firm.ein} | tel. {firm.telefon} | {firm.email}")),
    ],
    metadane={"author": "{counsel.pelne}", "subject": "Letter before action / demand letter"},
)
