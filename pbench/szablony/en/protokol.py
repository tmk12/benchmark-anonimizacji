"""Protokół zgromadzenia wspólników: minutes of a general meeting (spółka brytyjska, Companies Act 2006) albo minutes
of a special meeting of stockholders (spółka amerykańska, DGCL); lista obecnych w tabeli, uchwały, kapitał z `Kontekst`."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="en", typ="protokol", dorosli=True, warianty=("gb", "us"),
    role={"company": "firma", "chair": "osoba", "secretary": "osoba", "holder1": "osoba", "holder2": "osoba",
          "holder3": "osoba", "ceo": "osoba", "newdirector": "osoba", "auditor": "osoba", "counsel": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{company.nazwa}",
               W("gb", "{company.adres} | Company No. {company.company_no} | VAT No. {company.vat}"),
               W("us", "{company.adres} | EIN {company.ein}")),
        sekcja("title", "akapit",
               W("gb", "MINUTES OF A GENERAL MEETING OF THE MEMBERS OF {company.nazwa}"),
               W("us", "MINUTES OF A SPECIAL MEETING OF THE STOCKHOLDERS OF {company.nazwa}"),
               W("gb", "Held at {company.adres} on {ctx.dok}"),
               W("us", "Held at the offices of the Company, {company.adres}, on {ctx.dok}")),
        sekcja("open", "akapit",
               "1. CALL TO ORDER. {chair.pelne} took the chair and called the meeting to order. {secretary.pelne} "
               "acted as secretary and recorded the minutes.",
               W("gb", "2. NOTICE. The chair noted that notice of the meeting had been sent to all members entitled "
                 "to attend on the required notice period, in accordance with section 307 of the Companies Act "
                 "2006, and the notice was taken as read."),
               W("us", "2. NOTICE. The secretary confirmed that written notice of the time, place and purpose of "
                 "the meeting had been mailed to every stockholder of record not less than ten nor more than sixty "
                 "days before the meeting, as required by Section 222 of the Delaware General Corporation Law."),
               "3. APOLOGIES. {holder3.pelne} had notified the secretary in advance that "
               "{holder3.rodzaj:he|she} could not attend.",
               min=3, max=4),
        sekcja("attendance_label", "akapit", "Attendance register:"),
        sekcja("attendance", "komorka",
               W("gb", "No. | Member | Date of birth | Shares held | Votes\n"
                 "1 | {holder1.pelne} | {holder1.data_ur} | {ctx.udzialy1} | {ctx.udzialy1}\n"
                 "2 | {holder2.pelne} | {holder2.data_ur} | {ctx.udzialy2} | {ctx.udzialy2}\n"
                 "3 | {holder3.pelne} | {holder3.data_ur} | {ctx.udzialy3} | {ctx.udzialy3}\n"
                 "Total | | | {ctx.udzialy_suma3} | {ctx.udzialy_suma3}"),
               W("us", "No. | Stockholder | Address | Shares held | Votes\n"
                 "1 | {holder1.pelne} | {holder1.adres} | {ctx.udzialy1} | {ctx.udzialy1}\n"
                 "2 | {holder2.pelne} | {holder2.adres} | {ctx.udzialy2} | {ctx.udzialy2}\n"
                 "3 | {holder3.pelne} | {holder3.adres} | {ctx.udzialy3} | {ctx.udzialy3}\n"
                 "Total | | | {ctx.udzialy_suma3} | {ctx.udzialy_suma3}")),
        sekcja("quorum", "akapit",
               W("gb", "4. QUORUM. The chair declared that a quorum was present, holders of all {ctx.udzialy_suma3} "
                 "issued shares being represented in person or by proxy, so that the meeting was validly "
                 "constituted."),
               W("us", "4. QUORUM. The chair declared that stockholders holding all {ctx.udzialy_suma3} outstanding "
                 "shares of common stock were present in person or by proxy, constituting a quorum."),
               "5. The share capital of the Company is {ctx.kapital3}, divided into {ctx.udzialy_suma3} shares of "
               "equal nominal value.",
               min=2, max=2),
        sekcja("accounts", "akapit",
               "6. ACCOUNTS. The meeting received the annual accounts for the previous financial year and the "
               "report of {auditor.pelne}, the Company's auditor.",
               W("gb", "{auditor.rodzaj:Mr|Ms} {auditor.nazwisko} confirmed that the accounts give a true and fair "
                 "view."),
               W("us", "{auditor.rodzaj:Mr.|Ms.} {auditor.nazwisko} confirmed that the financial statements fairly "
                 "present the Corporation's position."),
               "7. PERFORMANCE. {ceo.pelne} presented the report on trading and the outlook for the coming year.",
               min=2, max=4),
        sekcja("resolutions", "akapit",
               W("gb", "8. ORDINARY RESOLUTION. It was resolved by ordinary resolution that {newdirector.pelne}, "
                 "of {newdirector.adres}, be appointed a director of the Company with effect from the date of the "
                 "meeting. Votes for: {ctx.glosy_za2}; against: {ctx.glosy_przeciw2}."),
               W("us", "8. ELECTION OF DIRECTOR. Upon motion duly made and seconded, it was RESOLVED that "
                 "{newdirector.pelne} be elected a director of the Corporation to serve until the next annual "
                 "meeting. Votes for: {ctx.glosy_za2}; against: {ctx.glosy_przeciw2}."),
               W("gb", "9. SPECIAL RESOLUTION. It was resolved by special resolution, in accordance with section "
                 "283 of the Companies Act 2006, that the articles of association be amended as set out in the "
                 "document tabled at the meeting."),
               W("us", "9. AMENDMENT OF BYLAWS. It was RESOLVED that the bylaws of the Corporation be amended as "
                 "set out in the document presented at the meeting."),
               "10. DIVIDEND. It was resolved that a dividend of {ctx.dywidenda} be paid to holders of shares "
               "pro rata to their holdings, in the next quarter.",
               min=3, max=4),
        sekcja("close", "akapit",
               "11. There being no further business, the chair declared the meeting closed.",
               "The next ordinary meeting was scheduled for {ctx.dok_pozniej}.",
               W("gb", "These minutes, once signed by the chair, are evidence of the proceedings under section 356 of "
                 "the Companies Act 2006 and will be kept at the registered office for at least ten years."),
               W("us", "These minutes will be filed in the Corporation's minute book. Counsel to the Corporation, "
                 "{counsel.pelne} (tel. {counsel.telefon}), reviewed the form of the resolutions."),
               min=2, max=3),
        sekcja("sign_label", "akapit",
               "Chair:                                   Secretary:"),
        sekcja("signatures", "podpis", "{chair.pelne}", "{secretary.pelne}"),
        sekcja("footer", "stopka",
               W("gb", "{company.nazwa} | {company.adres} | Company No. {company.company_no} | tel. "
                 "{company.telefon} | {company.email}"),
               W("us", "{company.nazwa} | {company.adres} | EIN {company.ein} | tel. {company.telefon} | "
                 "{company.email}")),
    ],
    metadane={"author": "{secretary.pelne}", "subject": "Minutes of general meeting"},
)
