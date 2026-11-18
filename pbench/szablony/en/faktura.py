"""Faktura za usługi prawne: VAT invoice (Wielka Brytania, VAT 20%) albo invoice z sales tax (USA); dane stron i pozycje
w tabelach, sumy z `Kontekst` (netto + podatek = brutto), uwagi o płatności."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="en", typ="faktura", warianty=("gb", "us"),
    role={"seller": "firma", "buyer": "firma", "issuer": "osoba", "recipient": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{seller.nazwa}",
               W("gb", "{seller.adres} | VAT Reg. No. {seller.vat}"),
               W("us", "{seller.adres} | EIN {seller.ein}")),
        sekcja("title", "akapit",
               W("gb", "VAT INVOICE"),
               W("us", "INVOICE"),
               "Invoice date: {ctx.dok}",
               "Date of supply: {ctx.dok_sprzedaz}"),
        sekcja("parties", "komorka",
               W("gb", "From | To\n"
                 "{seller.nazwa} | {buyer.nazwa}\n"
                 "{seller.adres} | {buyer.adres}\n"
                 "Company no. {seller.company_no} | Company no. {buyer.company_no}\n"
                 "VAT no. {seller.vat} | VAT no. {buyer.vat}"),
               W("us", "Bill from | Bill to\n"
                 "{seller.nazwa} | {buyer.nazwa}\n"
                 "{seller.adres} | {buyer.adres}\n"
                 "EIN {seller.ein} | EIN {buyer.ein}\n"
                 "Phone {seller.telefon} | Phone {buyer.telefon}")),
        sekcja("lines", "komorka",
               W("gb", "No. | Description | Qty | Unit price | Net amount | VAT rate\n"
                 "1 | Monthly retainer for general legal advice | 1 | {ctx.kf1} | {ctx.kf1} | 20%\n"
                 "2 | Advice on commercial lease | 1 | {ctx.kf2} | {ctx.kf2} | 20%\n"
                 "3 | Attendance at regulatory meeting | 1 | {ctx.kf3} | {ctx.kf3} | 20%"),
               W("gb", "No. | Service | Unit | Qty | Net amount | VAT rate\n"
                 "1 | Services under agreement dated {ctx.umowa_dawna} | lump sum | 1 | {ctx.kf1} | 20%\n"
                 "2 | Drafting and negotiation of documents | lump sum | 1 | {ctx.kf2} | 20%\n"
                 "3 | Attendance at board meetings | lump sum | 1 | {ctx.kf3} | 20%"),
               W("us", "Item | Description | Qty | Rate | Amount | Tax\n"
                 "1 | Monthly retainer for general legal counsel | 1 | {ctx.kf1} | {ctx.kf1} | 8.25%\n"
                 "2 | Review of commercial lease | 1 | {ctx.kf2} | {ctx.kf2} | 8.25%\n"
                 "3 | Regulatory filing and attendance | 1 | {ctx.kf3} | {ctx.kf3} | 8.25%"),
               W("us", "Item | Service | Unit | Qty | Amount | Tax\n"
                 "1 | Services under engagement dated {ctx.umowa_dawna} | flat fee | 1 | {ctx.kf1} | 8.25%\n"
                 "2 | Preparation and negotiation of documents | flat fee | 1 | {ctx.kf2} | 8.25%\n"
                 "3 | Attendance at board meetings | flat fee | 1 | {ctx.kf3} | 8.25%"),
               min=1, max=1),
        sekcja("totals", "komorka",
               W("gb", "Total net | VAT at 20% | Total payable\n{ctx.netto} | {ctx.vat} | {ctx.brutto}"),
               W("us", "Subtotal | Sales tax 8.25% | Total due\n{ctx.netto} | {ctx.vat} | {ctx.brutto}")),
        sekcja("payment", "akapit",
               "Payment due by {ctx.dok_termin_fv}. Please pay by bank transfer to {seller.rachunek}, quoting the "
               "invoice date as the reference.",
               "Queries about this invoice: {seller.email}, tel. {seller.telefon}."),
        sekcja("notes", "akapit",
               W("gb", "This invoice is issued in accordance with section 6 of the Value Added Tax Act 1994. The "
                 "domestic reverse charge does not apply to these services."),
               W("us", "Sales tax is charged where applicable under state law. Please retain this invoice for your "
                 "records; a Form W-9 is available on request."),
               W("gb", "Late payment interest and a fixed recovery sum are claimable under the Late Payment of "
                 "Commercial Debts (Interest) Act 1998."),
               W("us", "Balances unpaid after thirty days accrue a late charge of 1.5% per month."),
               "This invoice is issued electronically and is valid without a signature.",
               min=3, max=5),
        sekcja("issued", "akapit",
               W("gb", "The invoice was sent electronically to {recipient.pelne}, the person authorised to receive "
                 "accounting documents on behalf of the buyer."),
               W("us", "The invoice was sent electronically to {recipient.pelne}, the person authorized to receive "
                 "accounting documents on behalf of the buyer."),
               "Prepared and checked for accuracy by {issuer.pelne}."),
        sekcja("signature", "podpis", "{issuer.pelne}"),
        sekcja("footer", "stopka",
               W("gb", "{seller.nazwa} | {seller.adres} | Company No. {seller.company_no} | VAT No. {seller.vat} | "
                 "tel. {seller.telefon}"),
               W("us", "{seller.nazwa} | {seller.adres} | EIN {seller.ein} | tel. {seller.telefon}")),
    ],
    metadane={"author": "{issuer.pelne}", "subject": "Invoice for legal services"},
)
