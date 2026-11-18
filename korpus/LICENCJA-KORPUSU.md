# Licencja korpusu „Benchmark anonimizacji dokumentów” (wersja 1.0)

**Licencjodawca:** Legal Geek sp. z o.o. z siedzibą w Gdyni (81-451), al. Zwycięstwa 96/98, KRS 0000615169,
NIP 5862305970, REGON 364307021 („Legal Geek”). **Korpus:** zbiór syntetycznych dokumentów, plików tekstowych,
manifestu i danych wzorcowych (gold) opublikowany w repozytorium `github.com/tmk12/benchmark-anonimizacji`
(katalogi `korpus/` i `korpus-trudne/`), identyfikowany sumami SHA-256 z plików `metodyka/SHA256SUMS-trzon`
i `metodyka/SHA256SUMS-trudne`.

**Wersja Korpusu** (suma SHA-256 manifestu):

- trzon (`korpus/manifest.jsonl`): `5f23adedb58dcaa03b8441e016cc4a602d3126f379fd5a9622b105fe04770d63`
- warstwa trudnych przypadków (`korpus-trudne/manifest.jsonl`): `e733cc538392c063e31c0c7e66e941a2417430906ab4ff7e84dd6f9463d7c0f2`

1. **Udzielenie licencji.** Licencjodawca udziela nieodpłatnej, niewyłącznej, ogólnoświatowej licencji na
   korzystanie z Korpusu w celu testowania, oceny i porównywania narzędzi do wykrywania, maskowania lub
   anonimizacji danych, w tym publikowania wyników, oraz na zwielokrotnianie i rozpowszechnianie Korpusu w postaci
   niezmienionej, wraz z niniejszą licencją.
2. **Zakaz trenowania modeli.** Zabronione jest używanie Korpusu – w całości lub części, w postaci oryginalnej,
   przetworzonej, przetłumaczonej, rozszerzonej (augmentacja) lub jako wzoru do generowania danych podobnych – do:
   a) trenowania, dotrenowania, dostrajania, destylacji lub uczenia ze wzmocnieniem modeli uczenia maszynowego
      i sztucznej inteligencji;
   b) walidacji, wczesnego zatrzymania, doboru hiperparametrów, progów lub reguł modeli albo narzędzi;
   c) włączania do zbiorów danych przeznaczonych do celów z lit. a lub b.
   Uruchomienie narzędzia na Korpusie wyłącznie w celu jego oceny nie narusza zakazu.
3. **Zastrzeżenie eksploracji tekstu i danych.** Licencjodawca zastrzega, że Korpus nie może być przedmiotem
   eksploracji tekstu i danych w rozumieniu art. 4 dyrektywy (UE) 2019/790 oraz art. 26³ ustawy z dnia 4 lutego 1994 r. o prawie autorskim i prawach pokrewnych (t.j. Dz.U. z 2025 r. poz. 24 ze zm.) w celach, o których mowa
   w pkt 2. Zastrzeżenie ma także postać odczytu maszynowego (`tdmrep.json`).
4. **Publikacja wyników.** Publikując wyniki uzyskane na Korpusie, podaje się wersję Korpusu (sumę SHA-256
   manifestu), konfigurację narzędzia oraz oświadczenie, że badane narzędzie nie było trenowane, dostrajane ani
   walidowane na Korpusie. Wyniki narzędzia, które naruszyło pkt 2, nie mogą być przedstawiane jako wyniki tego
   benchmarku.
5. **Uznanie autorstwa.** Przy rozpowszechnianiu Korpusu lub publikacji wyników: „Benchmark anonimizacji
   dokumentów, © Legal Geek, 2026, wersja trzon `5f23aded…`, warstwa trudna `e733cc53…`” (lub pełne sumy SHA-256
   manifestów z nagłówka) z odnośnikiem do repozytorium.
6. **Dane syntetyczne.** Korpus zawiera wyłącznie dane wymyślone. Zbieżność z danymi istniejących osób, podmiotów
   lub adresów jest przypadkowa; Korpusu nie wolno używać do identyfikowania osób ani przedstawiać jako danych
   prawdziwych.
7. **Brak gwarancji i odpowiedzialności.** Korpus udostępnia się „w stanie, w jakim jest”, bez gwarancji;
   odpowiedzialność Licencjodawcy jest wyłączona w najszerszym zakresie dopuszczalnym przez prawo.
8. **Wygaśnięcie.** Naruszenie warunków licencji powoduje jej wygaśnięcie wobec naruszającego z chwilą naruszenia.
9. **Prawo i sąd.** Prawo polskie; sąd właściwy dla siedziby Licencjodawcy.

---

# Corpus licence “Document anonymization benchmark” (version 1.0) – English translation

*This is a translation provided for convenience. Only the Polish version above is binding; in case of any
discrepancy, the Polish version prevails.*

**Licensor:** Legal Geek sp. z o.o., registered office in Gdynia (81-451), al. Zwycięstwa 96/98, Poland, KRS 0000615169,
NIP 5862305970, REGON 364307021 (“Legal Geek”). **Corpus:** the collection of synthetic documents, text files,
manifest and reference (gold) data published in the repository `github.com/tmk12/benchmark-anonimizacji`
(directories `korpus/` and `korpus-trudne/`), identified by the SHA-256 checksums in `metodyka/SHA256SUMS-trzon`
and `metodyka/SHA256SUMS-trudne`.

**Corpus version** (SHA-256 of the manifest):

- core (`korpus/manifest.jsonl`): `5f23adedb58dcaa03b8441e016cc4a602d3126f379fd5a9622b105fe04770d63`
- hard-case layer (`korpus-trudne/manifest.jsonl`): `e733cc538392c063e31c0c7e66e941a2417430906ab4ff7e84dd6f9463d7c0f2`

1. **Grant.** The Licensor grants a free, non-exclusive, worldwide licence to use the Corpus for testing, evaluating
   and comparing tools that detect, mask or anonymize data, including publishing the results, and to reproduce and
   distribute the Corpus in unmodified form together with this licence.
2. **No model training.** It is prohibited to use the Corpus – in whole or in part, in original, processed,
   translated or extended (augmented) form, or as a template for generating similar data – for:
   a) training, further training, fine-tuning, distillation or reinforcement learning of machine-learning and
      artificial-intelligence models;
   b) validation, early stopping, selection of hyperparameters, thresholds or rules of models or tools;
   c) inclusion in datasets intended for the purposes in (a) or (b).
   Running a tool on the Corpus solely to evaluate it does not breach this prohibition.
3. **Text and data mining reservation.** The Licensor reserves that the Corpus may not be subject to text and data
   mining within the meaning of Article 4 of Directive (EU) 2019/790 and Article 26³ of the Polish Act of 4 February 1994 on Copyright and Related Rights (consolidated text: Journal of Laws of 2025, item 24, as amended) for the purposes referred to
   in point 2. The reservation is also expressed in machine-readable form (`tdmrep.json`).
4. **Publishing results.** Anyone publishing results obtained on the Corpus states the Corpus version (SHA-256 of
   the manifest), the tool configuration and a declaration that the tool was not trained, fine-tuned or validated
   on the Corpus. Results of a tool that breached point 2 may not be presented as results of this benchmark.
5. **Attribution.** When distributing the Corpus or publishing results: “Document anonymization benchmark,
   © Legal Geek, 2026, version core `5f23aded…`, hard-case layer `e733cc53…`” (or the full SHA-256 manifest
   checksums given above) with a link to the repository.
6. **Synthetic data.** The Corpus contains only invented data. Any resemblance to data of existing persons, entities
   or addresses is coincidental; the Corpus may not be used to identify persons or presented as real data.
7. **No warranty or liability.** The Corpus is provided “as is”, without warranty; the Licensor’s liability is
   excluded to the fullest extent permitted by law.
8. **Termination.** A breach of the licence terms terminates the licence for the breaching party upon the breach.
9. **Governing law and jurisdiction.** Polish law; the court having jurisdiction over the Licensor’s registered
   office.
