"""Services agreement with a Ukrainian contractor: name, address and identifiers in Cyrillic and transliteration."""
from __future__ import annotations

from ....budowa import Szablon
from ..._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="en", typ="umowa", dorosli=True, znacz_encje=True, warianty=("cw", "tr"),
    role={"klient": "firma", "reprezentant": "osoba", "wykonawca": "osoba_ua", "opiekun": "osoba"},
    sekcje=[
        sekcja("naglowek", "naglowek",
               "{klient.nazwa}",
               "{klient.adres}"),
        sekcja("tytul", "akapit",
               "CONSULTANCY SERVICES AGREEMENT",
               "This agreement is made on {ctx.dok} between:"),
        sekcja("strony", "akapit",
               "(1) {klient.nazwa}, whose registered office is at {klient.adres}, represented by "
               "{reprezentant.pelne}, Managing Director (the “Company”); and",
               "(2) {wykonawca.pelne_im:t_s1} ({wykonawca.pelne_im:t_s2}), born on {wykonawca.data_ur}, a citizen of "
               "Ukraine, residing at {wykonawca.adres:t_s1} ({wykonawca.adres:t_s2}), holder of Ukrainian tax "
               "number (РНОКПП) {wykonawca.rnokpp} and of passport no. {wykonawca.paszport} (the “Consultant”)."),
        sekcja("services", "akapit",
               "1. SERVICES",
               "1.1 The Consultant shall provide the Company with translation, interpreting and market research "
               "services relating to the Ukrainian market, as requested by the Company from time to time.",
               "1.2 The Consultant shall report to {opiekun.pelne} and shall comply with the Company’s reasonable "
               "instructions as to the manner of performance of the Services."),
        sekcja("fees", "akapit",
               "2. FEES AND PAYMENT",
               "2.1 The Company shall pay the Consultant a monthly fee of {ctx.um_wyn}, exclusive of any applicable "
               "taxes, within 14 days of receipt of a valid invoice.",
               "2.2 Payments shall be made by bank transfer to the Consultant’s account IBAN {wykonawca.rachunek}.",
               "2.3 The Consultant may be contacted on {wykonawca.telefon} or at {wykonawca.email}."),
        sekcja("identity", "akapit",
               "3. IDENTITY AND RECORDS",
               "3.1 The Company shall process the Consultant’s personal data, including the tax number "
               "{wykonawca.rnokpp}, only for the purposes of this agreement and in accordance with applicable data "
               "protection law.",
               W("tr", "3.2 The Consultant confirms that the personal details above match the identity document and "
                       "that his or her name may also appear in the Company’s records as {wykonawca.pelne_im:t_s2}, "
                       "{wykonawca.pelne_im:t_s3} or {wykonawca.pelne_im:t_s4}; all of these refer to one and the "
                       "same person.")),
        sekcja("term", "akapit",
               "4. TERM AND GOVERNING LAW",
               "4.1 This agreement starts on {ctx.od_dnia} and continues until terminated by either party on "
               "30 days’ written notice.",
               "4.2 This agreement is governed by the law of the country in which the Company has its registered "
               "office."),
        sekcja("podpis_opis", "akapit", "Signed by the Consultant:"),
        sekcja("podpis", "podpis", "{wykonawca.pelne_im:t_s1}"),
        sekcja("stopka", "stopka", "{klient.nazwa} | {klient.adres} | {klient.email}"),
    ],
    metadane={"author": "{reprezentant.pelne}", "subject": "Consultancy services agreement"},
)
