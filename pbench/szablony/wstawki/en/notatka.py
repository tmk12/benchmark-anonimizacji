"""Attorney file note: telephone attendance on a Ukrainian client with an interpreter (Cyrillic and transliterations)."""
from __future__ import annotations

from ....budowa import Szablon
from ..._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="en", typ="notatka", dorosli=True, znacz_encje=True, warianty=("cw", "tr"),
    role={"kancelaria": "kancelaria", "autor": "osoba", "klient": "osoba_ua", "tlumacz": "osoba",
          "przeciwnik": "osoba"},
    sekcje=[
        sekcja("naglowek", "naglowek",
               "{kancelaria.nazwa}",
               "FILE NOTE – PRIVILEGED AND CONFIDENTIAL"),
        sekcja("dane", "akapit",
               "Date: {ctx.przed_rozprawa}",
               "Fee earner: {autor.pelne}",
               "Client: {klient.pelne_im:t_s1} ({klient.pelne_im:t_s2})"),
        sekcja("attendance", "akapit",
               "Telephone attendance on the client through an interpreter, {tlumacz.pelne}. The client "
               "confirmed the following contact details: address {klient.adres:t_s1} ({klient.adres:t_s2}); "
               "telephone {klient.telefon}; e-mail {klient.email}.",
               W("tr", "The client’s name is spelt in several ways in the documents received: {klient.pelne_im:t_s2}, "
                       "{klient.pelne_im:t_s3} and {klient.pelne_im:t_s4}. The client confirmed that all of them "
                       "refer to the same person; the spelling on the passport (no. {klient.paszport}) is to be used "
                       "in court documents."),
               "Identity: Ukrainian tax number (РНОКПП) {klient.rnokpp}; national ID card no. {klient.dowod}; "
               "date of birth {klient.data_ur}."),
        sekcja("matter", "akapit",
               "The client explained that the dispute with {przeciwnik.pelne} arose from a late delivery of goods "
               "ordered in the spring. The client holds the order confirmation and the e-mail correspondence "
               "and will send copies by the end of the week.",
               "Advice given: the client should not contact {przeciwnik.pelne} directly; we will send a letter "
               "before claim and diarise the response date of {ctx.notatka_termin}.",
               "Costs: the client was told our hourly rates and that an advance of {ctx.zaliczka_kosztow} will be "
               "requested before proceedings are issued.",
               min=2, max=3),
        sekcja("actions", "akapit",
               "Actions: (1) prepare the letter before claim; (2) obtain a certified translation of the "
               "Ukrainian contract documents; (3) update the client record with the transliterated name "
               "{klient.pelne_im:t_s1}.",
               "Next attendance on the client: after the response date."),
        sekcja("podpis", "podpis", "{autor.pelne}"),
        sekcja("stopka", "stopka", "{kancelaria.nazwa} | {kancelaria.adres} | {kancelaria.email}"),
    ],
    metadane={"author": "{autor.pelne}", "subject": "File note"},
)
