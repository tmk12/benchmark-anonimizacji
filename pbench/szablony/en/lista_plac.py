"""Lista płac pracodawcy (arkusz XLSX): payroll register — Wielka Brytania (NI number, PAYE) albo USA (SSN, FICA);
nagłówek, okres, tabela z ponad 200 pracownikami, podsumowanie, uwagi.

Każdy wiersz tabeli ma własną osobę (`p000`…), bo gniazda jednej roli mają jedną wartość; wynagrodzenia i sumy
bierze z kontekstu (`ctx.brutto_<i>`, `ctx.suma_<n>`), więc podsumowanie zgadza się z tabelą.
"""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja

WIERSZE = 212
_STANOWISKA = ("HR administrator", "Accountant", "Team leader", "Junior associate", "Executive assistant", "Driver",
               "Warehouse operative", "Clerk", "Senior specialist", "Health and safety officer", "Consultant",
               "IT administrator")

_ROLE_WIERSZY = {f"p{i:03d}": "osoba" for i in range(WIERSZE)}


def _tabela(kraj: str) -> str:
    id_pola, id_naglowek = ("nino", "NI number") if kraj == "gb" else ("ssn", "SSN")
    nazwisko = "Surname" if kraj == "gb" else "Last name"
    wiersze = [f"No. | First name | {nazwisko} | {id_naglowek} | Job title | Gross pay | Bank account"]
    for i in range(WIERSZE):
        p = f"p{i:03d}"
        wiersze.append(f"{i + 1} | {{{p}.pelne/1}} | {{{p}.pelne/2}} | {{{p}.{id_pola}}} | "
                       f"{_STANOWISKA[i % len(_STANOWISKA)]} | {{ctx.brutto_{i}}} | {{{p}.rachunek}}")
    return "\n".join(wiersze)


SZABLON = Szablon(
    jezyk="en", typ="lista_plac", warianty=("gb", "us"),
    role={"employer": "firma", "prepared": "osoba", "approved": "osoba", "hr": "osoba"} | _ROLE_WIERSZY,
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{employer.nazwa}",
               W("gb", "{employer.adres} | Company No. {employer.company_no} | PAYE reference 120/AB{ctx.udzialy1}"),
               W("us", "{employer.adres} | EIN {employer.ein}")),
        sekcja("title", "akapit",
               W("gb", "PAYROLL REGISTER – MONTHLY"),
               W("us", "PAYROLL REGISTER – SEMI-MONTHLY PAY PERIOD"),
               "Pay date: {ctx.dok_termin}",
               "Employer: {employer.nazwa}"),
        sekcja("table", "komorka", W("gb", _tabela("gb")), W("us", _tabela("us"))),
        sekcja("summary", "komorka",
               W("gb", "Item | Amount\n"
                 "Total gross pay | {ctx.suma_212}\n"
                 "Employer and employee National Insurance contributions | {ctx.zus_212}\n"
                 "Income tax deducted under PAYE | {ctx.pit_212}"),
               W("us", "Item | Amount\n"
                 "Total gross wages | {ctx.suma_212}\n"
                 "Employer and employee payroll taxes (Social Security and Medicare) | {ctx.zus_212}\n"
                 "Federal income tax withheld | {ctx.pit_212}")),
        sekcja("notes", "akapit",
               W("gb", "Pay has been calculated under the PAYE Real Time Information rules; a Full Payment "
                 "Submission is made to HMRC on or before the pay date."),
               W("us", "Payroll taxes have been calculated under the Internal Revenue Code and deposited under the "
                 "semiweekly schedule; Forms 941 are filed quarterly."),
               W("gb", "Statutory sick pay, statutory maternity pay and automatic enrolment pension contributions "
                 "are reflected in the individual payslips."),
               W("us", "Wage garnishments and child-support withholdings received before the close of the pay period "
                 "are reflected in the individual pay statements."),
               W("gb", "This register contains personal data processed under the UK GDPR and must be retained for "
                 "at least three years from the end of the tax year to which it relates."),
               W("us", "This register contains confidential employee information and must be retained for at least "
                 "four years under IRS record-keeping requirements."),
               min=3, max=4),
        sekcja("prepared", "akapit",
               "Prepared by: {prepared.pelne}, Payroll, tel. {prepared.telefon}",
               "Checked by: {hr.pelne}",
               "Approved for payment: {approved.pelne}"),
        sekcja("signatures", "podpis", "{prepared.pelne}", "{approved.pelne}"),
        sekcja("footer", "stopka",
               "{employer.nazwa} | {employer.adres} | tel. {employer.telefon} | {employer.email}"),
    ],
    metadane={"author": "{prepared.pelne}", "subject": "Payroll register"},
)
