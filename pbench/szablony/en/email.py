"""E-mail kancelarii do klienta z projektem odpowiedzi na pozew i prośbą o dokumenty (nagłówki Od/Do/DW w metadanych);
brytyjski solicitor (Defence, CPR) albo amerykański attorney (Answer, Rule 12). Stopka z telefonem i zastrzeżeniem."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="en", typ="email", warianty=("gb", "us"),
    role={"firm": "kancelaria", "sender": "osoba", "client": "osoba", "colleague": "osoba", "opponent": "osoba",
          "witness": "osoba", "court": "sad", "matter": "sprawa", "portal": "sprawa"},
    sekcje=[
        sekcja("greeting", "akapit",
               W("gb", "Dear {client.rodzaj:Mr|Ms} {client.nazwisko},"),
               W("us", "Dear {client.rodzaj:Mr.|Ms.} {client.nazwisko},")),
        sekcja("intro", "akapit",
               W("gb", "Further to our telephone call, I attach a draft Defence in the claim brought by "
                 "{client.pelne} against {opponent.pelne} ({matter.sygnatura})."),
               W("us", "Following up on our call, I attach a draft Answer in the action brought by {client.pelne} "
                 "against {opponent.pelne}, {matter.sygnatura}."),
               "I can confirm that the court ({court.nazwa}) has listed the hearing for {ctx.rozprawa}. Please "
               "confirm that you are able to attend.",
               "Thank you for sending the documents. On a first review the case is well documented, although a few "
               "exhibits are still missing.",
               min=3, max=3),
        sekcja("draft", "akapit",
               "The draft is attached in Word format with tracked changes. Please send me your comments by "
               "{ctx.odp_termin}, as the deadline for filing the response is fixed by the court rules and cannot be "
               "extended without an application."),
        sekcja("body", "akapit",
               "What we still need from you: confirmation of {client.pelne}'s address ({client.adres}), a copy of "
               "the payment slip for the deposit to our client account, and scans of your correspondence for the "
               "last two years.",
               "The deposit towards court fees of {ctx.zaliczka_kosztow} should reach our account "
               "{firm.rachunek} no later than the day before the hearing.",
               "You can upload documents and photographs through our secure client portal: {portal.url}. Please do "
               "not send documents containing sensitive data by ordinary email.",
               "Our witness, {witness.pelne}, has been told that the court may require attendance; if "
               "{witness.rodzaj:his|her} contact details (tel. {witness.telefon}) change, please let us know.",
               W("gb", "On strategy, I suggest we first seek the dismissal of the claim and, in the alternative, ask "
                 "the court to allow payment by instalments under CPR Part 40."),
               W("us", "On strategy, I suggest we first move to dismiss for failure to state a claim and, in the "
                 "alternative, propose a payment plan, consistent with Rule 12 of the applicable rules of civil "
                 "procedure."),
               min=3, max=5),
        sekcja("closing", "akapit",
               "Please call me on {sender.telefon} or write to {sender.email} if you have any questions.",
               "I am copying my colleague {colleague.pelne} so that {colleague.rodzaj:he|she} can follow the file "
               "while I am out of the office.",
               W("gb", "Kind regards,"),
               W("us", "Best regards,"),
               min=3, max=4),
        sekcja("signature", "stopka",
               W("gb", "{sender.pelne} | Solicitor | {firm.nazwa} | {firm.adres} | tel. {firm.telefon}"),
               W("us", "{sender.pelne} | Attorney at Law | {firm.nazwa} | {firm.adres} | tel. {firm.telefon}")),
        sekcja("disclaimer", "stopka",
               W("gb", "This email is confidential and may be legally privileged. If you are not the intended "
                 "recipient, please notify the sender immediately and delete it. {firm.nazwa} is regulated by the "
                 "Solicitors Regulation Authority."),
               W("us", "This message is intended only for the addressee and may contain attorney-client privileged "
                 "information. If you received it in error, please notify the sender and delete it."),
               "Our privacy notice explains how we process personal data and is available on our website.",
               min=1, max=2),
    ],
    metadane={"from": "{sender.email}", "to": "{client.email}", "cc": "{colleague.email}",
              "subject": "Draft pleading – please review and send comments"},
)
