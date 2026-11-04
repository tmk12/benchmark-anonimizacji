# Benchmark anonimizacji dokumentów – prerejestracja metodyki

Repozytorium publicznego testu porównawczego narzędzi do wykrywania i maskowania danych osobowych w dokumentach
(modele i narzędzia open source uruchamiane na CPU oraz Privatizer by Legal Geek). Autor testu: Legal Geek.

**Stan na 2026-11-04: prerejestracja zamrożona.** Metodykę (miary, wagi, reguły sędziów wycieku, progi z kalibracji
na części dev, listę uczestników, środowisko oceny) i sumy kontrolne korpusu publikujemy **przed** przebiegami na splicie
testowym, z których liczone są wyniki. Data commita w tym repozytorium jest dowodem, że ustalenia zapisano, zanim
ktokolwiek zobaczył wyniki. Kod testu (generator korpusu, sędziowie wycieków, uruchamianie uczestników), korpus i wyniki
zostaną opublikowane razem z raportem.

Zamrożenie potwierdza tag `prerejestracja-1` w repozytorium kodu testu (commit `071ebc81dc4e570b5ac96c16be0133217fc476af`).
Pliki w tym repozytorium to dokumenty z tego commita; w wersji publicznej pominięto wyłącznie nazwy wewnętrznych maszyn
i adnotacje organizacyjne – treść metodyki jest identyczna. Sumy kontrolne korpusu (`metodyka/SHA256SUMS-*`) są skopiowane
bez zmian.

## Zawartość

| Ścieżka | Co to |
|---|---|
| `metodyka/punktacja.md` | Rankingi „tekst” i „pliki”, wzór każdego testu, remis statystyczny, analiza wrażliwości |
| `metodyka/wagi_punktow.json` | Wagi testów, kategorii danych i miejsc w pliku |
| `metodyka/prerejestracja.md` | Reguły wycieku, definicje operacyjne miar, `t_ref` i pomiar czasu, kalibracja, uczestnicy, korpus, kontaminacja, środowisko oceny |
| `metodyka/progi.json` | Progi uczestników grupy A po kalibracji na części dev (pełne krzywe char-F2) i progi dziedziczone |
| `metodyka/uczestnicy.md` | Lista uczestników (grupy A, B, Privatizer, aneks), odstępstwa od konfiguracji autorów, rozważeni i odrzuceni |
| `metodyka/przypadki.md` | Warstwa trudnych przypadków: rozkład dokumentów per przypadek, przypadki punktowane |
| `metodyka/SHA256SUMS-trzon` | SHA-256 każdego pliku trzonu korpusu (1000 dokumentów syntetycznych, 5 języków), manifestu i statystyk |
| `metodyka/SHA256SUMS-trudne` | SHA-256 każdego pliku warstwy trudnych przypadków (290 dokumentów), manifestu i statystyk |

Dokumenty powołują się także na pliki repozytorium kodu (np. `metodyka/zakres-gold.md`, `metodyka/znane-ograniczenia.md`,
`uczestnicy/<id>/KONFIG.md`) – są objęte tym samym tagiem i zostaną opublikowane z kodem.

## Zobowiązania

- **Korpus jest w pełni syntetyczny** – żadnych danych prawdziwych osób; zbieżność wymyślonych danych z istniejącymi
  osobami jest przypadkowa.
- **Korpus jest deterministyczny:** wygenerował go kod z commita zamrożenia z ziarnami `20261103` (trzon) i `20261104`
  (warstwa trudna). Po publikacji kodu każdy może odtworzyć pliki i porównać je z `metodyka/SHA256SUMS-*`.
- **Metodyka jest zamrożona.** Każda zmiana miar, reguł sędziów, kalibracji, korpusu albo uczestników = nowa wersja
  (`prerejestracja-2` itd.), a raport pokaże wyniki obu wersji.
- **Ranking mierzy tryb domyślny Privatizera**; tryb „Maksymalna ochrona” i warianty krzyżowe są w aneksie, poza rankingami.
- Zespoły Privatizera nie mają dostępu do splitu testowego; korpus nie służy do treningu ani walidacji modelu.
- Wyniki pokażą punkty każdego uczestnika w każdym teście, surowe miary i przedziały ufności.

## Licencje

Kod: Apache-2.0 (`LICENSE`). Dokumentacja i wyniki: CC BY 4.0 (`LICENSE-docs.md`).
**Korpus** zostanie opublikowany na osobnej licencji: wolno go używać do testowania, oceny i porównywania narzędzi
oraz rozpowszechniać z uznaniem autorstwa, ale **nie wolno go używać do trenowania, dostrajania ani walidacji
modeli uczenia maszynowego** (z zastrzeżeniem eksploracji tekstu i danych zgodnie z art. 4 ust. 3 dyrektywy (UE)
2019/790). Pełne warunki zostaną opublikowane razem z korpusem.

---

# Document anonymization benchmark – methodology pre-registration (EN)

Public comparative test of tools that detect and mask personal data in documents (CPU-runnable open-source models
and tools, and Privatizer by Legal Geek). Author: Legal Geek.

**As of 2026-11-04 the pre-registration is frozen.** The methodology (measures, weights, leak-judge rules, thresholds
calibrated on the dev split, participants, evaluation environment) and corpus checksums are published **before** the
scored runs on the test split; the commit date here proves they were fixed before anyone saw results. The test code,
corpus and results will be published with the report.

The freeze is the tag `prerejestracja-1` in the test code repository (commit `071ebc81dc4e570b5ac96c16be0133217fc476af`).
Files here are the documents from that commit; the public version omits only internal machine names and organisational
notes – the methodology is identical. Corpus checksums are copied unchanged. Documents are in Polish.

Commitments: fully synthetic, deterministic corpus (seeds `20261103` core, `20261104` hard-case layer); any change after
the freeze is a new version reported alongside the original; the ranking measures Privatizer's default mode, the
“Maximum protection” mode and cross variants are in an annex outside the rankings; Privatizer teams have no access to the
test split, and the corpus is not used to train or validate the model.

Licences: code Apache-2.0, documentation and results CC BY 4.0. The corpus will be released under a separate licence
permitting testing, evaluation and comparison of tools but **prohibiting use for training, fine-tuning or validating
machine-learning models** (subject to text and data mining under Art. 4(3) of Directive (EU) 2019/790).
