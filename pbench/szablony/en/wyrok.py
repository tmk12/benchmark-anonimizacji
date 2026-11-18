"""Wyrok w sprawie o zapłatę z umowy, z uzasadnieniem, składem sądu, stronami i cytatami innych orzeczeń.

Cztery warianty: „gb_county” – County Court (sędzia jednoosobowo), „gb_appeal” – Court of Appeal (trzech Lords Justices),
„us_federal” – opinia sądu okręgowego USA (jeden sędzia), „us_appeal” – opinia sądu apelacyjnego USA (trzech sędziów).
Daty, kwoty i rok sygnatury biorą się z `Kontekst`; cytowane sprawy (rola `cite*`) to zwykły tekst, nie gold.
"""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="en", typ="wyrok", warianty=("gb_county", "gb_appeal", "us_federal", "us_appeal"),
    role={"sad": "sad", "judge1": "osoba", "judge2": "osoba", "judge3": "osoba",
          "claimant": "osoba", "defendant": "osoba", "counsel1": "osoba", "counsel2": "osoba", "witness": "osoba",
          "witness2": "osoba", "expert": "osoba", "cite1": "cytat", "cite2": "cytat", "cite3": "cytat"},
    sekcje=[
        sekcja("caption", "naglowek",
               W("gb", "IN THE {sad.nazwa:upper}"),
               W("us", "{sad.nazwa:upper}"),
               "{sad.sygnatura}",
               W("gb_county", "BETWEEN {claimant.pelne} (Claimant) and {defendant.pelne} (Defendant)"),
               W("gb_appeal", "ON APPEAL FROM THE COUNTY COURT. BETWEEN {defendant.pelne} (Appellant) and "
                 "{claimant.pelne} (Respondent)"),
               W("us_federal", "{claimant.pelne}, Plaintiff, v. {defendant.pelne}, Defendant."),
               W("us_appeal", "{claimant.pelne}, Plaintiff-Appellee, v. {defendant.pelne}, Defendant-Appellant."),
               W("gb", "JUDGMENT"),
               W("us_federal", "FINDINGS OF FACT, CONCLUSIONS OF LAW AND ORDER FOR JUDGMENT"),
               W("us_appeal", "OPINION"),
               "{ctx.wyrok_koncowy}"),
        sekcja("panel", "akapit",
               W("gb_county", "Before: District Judge {judge1.nazwisko}, sitting alone."),
               W("gb_county", "Counsel for the Claimant: {counsel1.pelne}. Counsel for the Defendant: "
                 "{counsel2.pelne}."),
               W("gb_appeal", "Before: {judge1.rodzaj:Lord Justice|Lady Justice} {judge1.nazwisko} (presiding), "
                 "{judge2.rodzaj:Lord Justice|Lady Justice} {judge2.nazwisko} and "
                 "{judge3.rodzaj:Lord Justice|Lady Justice} {judge3.nazwisko}."),
               W("gb_appeal", "Counsel for the Appellant: {counsel2.pelne}. Counsel for the Respondent: "
                 "{counsel1.pelne}."),
               W("us_federal", "Before the Honorable {judge1.pelne}, United States District Judge. Appearances: "
                 "{counsel1.pelne} for Plaintiff; {counsel2.pelne} for Defendant."),
               W("us_appeal", "Before {judge1.pelne}, {judge2.pelne} and {judge3.pelne}, Circuit Judges. "
                 "Appearances: {counsel2.pelne} for Appellant; {counsel1.pelne} for Appellee.")),
        sekcja("hearing", "akapit",
               W("gb_county", "Heard on {ctx.rozprawa_koncowa}. Judgment handed down on {ctx.wyrok_koncowy}. This "
                 "judgment was given after trial of a claim for the price of goods and services supplied under a "
                 "written contract."),
               W("gb_appeal", "Heard on {ctx.rozprawa_koncowa}. Judgment given on {ctx.wyrok_koncowy}. This is an "
                 "appeal from the judgment of the County Court of {ctx.wyrok}, ordering the Appellant to pay the "
                 "sum of {ctx.zasadzona}. Notice of appeal was filed on {ctx.apelacja}."),
               W("us_federal", "This matter came before the Court for a bench trial on {ctx.rozprawa_koncowa}. "
                 "Having considered the testimony, the exhibits and the arguments of counsel, the Court enters "
                 "the following findings and conclusions pursuant to Fed. R. Civ. P. 52(a)."),
               W("us_appeal", "Argued {ctx.rozprawa_koncowa}; decided {ctx.wyrok_koncowy}. Defendant appeals from "
                 "the judgment of the district court entered on {ctx.wyrok} awarding Plaintiff {ctx.zasadzona}. "
                 "Notice of appeal was filed on {ctx.apelacja}.")),
        sekcja("introduction", "akapit",
               W("gb", "{#}. This is a claim by {claimant.pelne} for the unpaid price of works carried out under a "
                 "written agreement. {defendant.pelne} defends the claim on the grounds of part performance and "
                 "set-off."),
               W("us", "Plaintiff {claimant.pelne} seeks to recover amounts allegedly due under a written "
                 "contract. Defendant {defendant.pelne} denies liability, asserting partial performance and "
                 "setoff."),
               W("gb_county", "{#}. By a claim form issued on {ctx.pozew} the Claimant seeks {ctx.glowna} together "
                 "with interest from {ctx.termin_platnosci}. The Defendant filed a defence resisting the claim in "
                 "full."),
               W("us_federal", "Plaintiff filed this action on {ctx.pozew} seeking {ctx.glowna} plus interest "
                 "from {ctx.termin_platnosci}. Defendant answered and denied liability."),
               W("gb_appeal", "{#}. The Respondent's claim for {ctx.glowna} was issued on {ctx.pozew}. At trial the "
                 "judge awarded {ctx.zasadzona} with interest and costs. The Appellant now argues that the judge "
                 "misdirected himself on the evidence."),
               W("us_appeal", "Plaintiff's complaint, filed {ctx.pozew}, sought {ctx.glowna}. After a bench trial "
                 "the district court awarded {ctx.zasadzona} plus interest. Defendant argues on appeal that the "
                 "court clearly erred in its findings of fact."),
               min=3, max=3),
        sekcja("facts", "akapit",
               W("gb", "{#}. On {ctx.umowa} the parties entered into a written contract under which the claimant "
                 "undertook to carry out certain works and the defendant undertook to pay the price within "
                 "fourteen days of acceptance. The works were accepted without reservation."),
               W("us", "On {ctx.umowa} the parties entered into a written contract under which Plaintiff "
                 "undertook to perform certain work and Defendant undertook to pay the price within fourteen days "
                 "of acceptance. The work was accepted without reservation."),
               W("gb", "{#}. The price was not paid by {ctx.termin_platnosci}. A letter requiring payment was sent "
                 "on {ctx.wezwanie}. It went unanswered."),
               W("us", "The price was not paid by {ctx.termin_platnosci}. A letter requiring payment was sent on "
                 "{ctx.wezwanie}. It went unanswered."),
               W("gb_county", "{#}. {witness.pelne} gave evidence for the claimant and {witness2.pelne} gave evidence "
                 "for the defendant. I found both witnesses honest, although their recollections differed in "
                 "detail."),
               W("us_federal", "{witness.pelne} testified for Plaintiff and {witness2.pelne} testified for "
                 "Defendant. The Court finds both witnesses credible, although their recollections differed in "
                 "detail."),
               W("gb_county", "{#}. The expert evidence of {expert.pelne}, a quantity surveyor, was agreed in all "
                 "material respects and the court accepts it as reliable and persuasive."),
               W("us_federal", "The testimony of {expert.pelne}, a construction cost estimator, was unrebutted and "
                 "the Court accepts it as reliable."),
               W("gb_appeal", "{#}. The judge below preferred the evidence of {witness.pelne}; there is no basis on "
                 "which this court would interfere with that assessment of credibility."),
               W("us_appeal", "The district court credited the testimony of {witness.pelne}; credibility "
                 "determinations of this kind are entitled to deference on appeal."),
               min=4, max=5),
        sekcja("law", "akapit",
               W("gb_county", "{#}. The Claimant's right to payment arises from the contract and from section 49 of "
                 "the Sale of Goods Act 1979 as regards the price of goods. The burden of proving payment or a valid "
                 "set-off lay on the Defendant."),
               W("gb_appeal", "{#}. The principles governing an appeal on fact are well settled: an appellate court "
                 "will not interfere with findings of primary fact unless satisfied that the judge was plainly "
                 "wrong (CPR 52.21(3))."),
               W("us_federal", "Under the governing state law, a plaintiff proves breach of contract by showing "
                 "a valid contract, its own performance, the defendant's breach and resulting damages. Plaintiff "
                 "has carried that burden by a preponderance of the evidence."),
               W("us_appeal", "We review the district court's findings of fact for clear error and its "
                 "conclusions of law de novo. See Fed. R. Civ. P. 52(a)(6)."),
               W("gb", "{#}. The principle that a party who accepts work without reservation cannot later resist "
                 "payment on the basis of defects readily apparent on inspection is stated in {cite1.sprawa} "
                 "{cite1.sygnatura}, where the court held that acceptance is strong evidence of conformity with "
                 "the contract."),
               W("us", "The principle that a party who accepts work without reservation cannot later resist "
                 "payment on the basis of defects readily apparent on inspection is stated in {cite1.sprawa}, "
                 "{cite1.sygnatura}, where the court held that acceptance is strong evidence of conformity with "
                 "the contract."),
               W("gb", "{#}. See also {cite2.sprawa} {cite2.sygnatura}, in which it was decided that interest runs from "
                 "the contractual due date without any further demand."),
               W("us", "See also {cite2.sprawa}, {cite2.sygnatura} (holding that interest runs from the "
                 "contractual due date without any further demand)."),
               W("gb", "{#}. Compare {cite3.sprawa} {cite3.sygnatura}, and the authorities cited there on the "
                 "assessment of damages for unpaid contract sums."),
               W("us", "Compare {cite3.sprawa}, {cite3.sygnatura}, and the authorities cited there on the "
                 "assessment of damages for unpaid contract sums."),
               W("gb", "{#}. The defence of set-off fails because the cross-claim relied upon was not yet due when "
                 "notice of set-off was given."),
               W("us", "The setoff defense fails because the cross-claim on which Defendant relies had not "
                 "matured when Defendant invoked it."),
               min=6, max=8),
        sekcja("conclusion", "akapit",
               W("gb_county", "{#}. In my judgment the claim succeeds in the amount of {ctx.zasadzona}, being the "
                 "agreed price less the sum allowed for the proved defects."),
               W("gb_appeal", "{#}. In my judgment the appeal should be dismissed. The judge's findings were open to "
                 "him on the evidence and his award of {ctx.zasadzona} was correct."),
               W("us_federal", "Judgment is entered for Plaintiff in the amount of {ctx.zasadzona}, representing "
                 "the contract price less the credit allowed for defective work."),
               W("us_appeal", "The judgment of the district court awarding {ctx.zasadzona} is AFFIRMED."),
               W("gb_appeal", "{#}. I would dismiss the appeal; my Lords will wish to hear any submissions on "
                 "costs."),
               W("us_appeal", "Costs on appeal are taxed against Defendant-Appellant under Fed. R. App. P. "
                 "39(a)(2).")),
        sekcja("order", "akapit",
               W("gb_county", "ORDER: (1) The Defendant shall pay the Claimant {ctx.zasadzona} with interest under "
                 "section 69 of the County Courts Act 1984 from {ctx.termin_platnosci} until payment."),
               W("gb_county", "(2) The Defendant shall pay the Claimant's costs of {ctx.koszty_procesu}, of which "
                 "{ctx.koszty_zast} is for legal representation, and the unpaid court fee of {ctx.oplata_nieuisz} "
                 "is to be recovered from the Defendant."),
               W("gb_appeal", "ORDER: (1) The appeal is dismissed. (2) The Appellant shall pay the Respondent's costs "
                 "of the appeal, summarily assessed at {ctx.koszty_apel}."),
               W("us_federal", "ORDER: (1) Judgment is entered for Plaintiff against Defendant in the amount of "
                 "{ctx.zasadzona}, with pre-judgment interest from {ctx.termin_platnosci} and post-judgment interest "
                 "under 28 U.S.C. § 1961."),
               W("us_federal", "(2) Plaintiff shall recover its costs under Fed. R. Civ. P. 54(d)(1), taxed at "
                 "{ctx.koszty_procesu}, including attorneys' fees of {ctx.koszty_zast}."),
               W("us_appeal", "ORDER: AFFIRMED. Appellant shall pay the costs of this appeal, fixed at "
                 "{ctx.koszty_apel}."),
               min=2, max=4),
        sekcja("notice", "akapit",
               W("gb_county", "Permission to appeal must be sought within 21 days of this judgment, from this court "
                 "or from the appeal court (CPR 52.12). This judgment is enforceable on expiry of 14 days."),
               W("gb_appeal", "A second appeal requires the permission of the Court of Appeal and is limited to an "
                 "important point of principle or practice (CPR 52.7)."),
               W("us_federal", "Any notice of appeal must be filed within thirty days of entry of this judgment "
                 "under Fed. R. App. P. 4(a)(1)(A)."),
               W("us_appeal", "A petition for rehearing may be filed within fourteen days after entry of judgment "
                 "under Fed. R. App. P. 40; the mandate will issue seven days thereafter.")),
        sekcja("signatures", "podpis",
               W("gb_county", "{judge1.pelne}"),
               W("gb_appeal", "{judge1.pelne}"), W("gb_appeal", "{judge2.pelne}"), W("gb_appeal", "{judge3.pelne}"),
               W("us_federal", "{judge1.pelne}"),
               W("us_appeal", "{judge1.pelne}"), W("us_appeal", "{judge2.pelne}"), W("us_appeal", "{judge3.pelne}")),
        sekcja("footer", "stopka", "{sad.nazwa} | {sad.sygnatura} | Page 1"),
    ],
    metadane={"subject": "Judgment in a claim for payment under a contract", "case": "{sad.sygnatura}"},
)
