"""Uczestnik `presidio-gliner`: Presidio z `GLiNERRecognizer` (checkpoint PII `urchade/gliner_multi_pii-v1`) zamiast NER spaCy.

Konfiguracja wg `conf/slim.yaml` autorów Presidio: silnik NLP daje tylko tokenizację/lematyzację (spaCy `*_core_news_lg`),
encje osobowe wykrywa GLiNER, a rozpoznawacze wzorcowe i krajowe działają jak w pozostałych uczestnikach Presidio.
Szczegóły i uzasadnienie: KONFIG.md. Okna tokenowe (podział słów GLiNER) z zakładką 20% i scalaniem offsetów (`../_wspolne/okna.py`)."""
from __future__ import annotations

import copy
import os
import sys
from pathlib import Path

KATALOG = Path(__file__).resolve().parent
sys.path.insert(0, str(KATALOG.parent / "_wspolne"))

import okna  # noqa: E402
import presidio_wspolne as pw  # noqa: E402
import protokol_uczestnika as pu  # noqa: E402
from huggingface_hub import snapshot_download  # noqa: E402
from presidio_analyzer.nlp_engine import NlpEngineProvider  # noqa: E402
from presidio_analyzer.predefined_recognizers import GLiNERRecognizer  # noqa: E402

SPACY = {"pl": "pl_core_news_lg", "en": "en_core_web_lg", "es": "es_core_news_lg", "de": "de_core_news_lg",
         "fr": "fr_core_news_lg"}
MODEL = os.environ.get("PBENCH_GLINER_MODEL", "urchade/gliner_multi_pii-v1")
REWIZJE = {"urchade/gliner_multi_pii-v1": "1fcf13e85f4eef5394e1fcd406cf2ca9ea82351d"}
# Tokenizer/konfiguracja szkieletu modelu (gliner_config.json: model_name) – też z przypiętej rewizji w vendor/hf.
SZKIELET = ("microsoft/mdeberta-v3-base", "a0484667b22365f84929a935b5e50a51f71f159d")
LIMIT_TOKENOW = 384                         # `max_len` modelu (gliner_config.json): słowa/znaki interpunkcji wg własnego splittera GLiNER
# Okna liczone w tokenach GLiNER (nie w znakach – tekst z dużą ilością interpunkcji przekraczał 384 tokeny w 1000 znaków
# i GLiNER po cichu ucinał ogon okna). 320 + zapas: krawędź okna cofana do granicy słowa może dodać ≤ zakładka/2 tokenów
# (zakładka 20% = 64 → ≤ 352 < 384). Test `test_gliner_okna_w_limicie_modelu` pilnuje, że żadne okno nie przekracza limitu.
MAX_TOKENOW = int(os.environ.get("PBENCH_OKNO_TOKENOW", "320"))
PROG_DOMYSLNY = 0.30                        # `threshold` GLiNERRecognizer w Presidio (domyślny autorów)

# Etykiety PII podane jawnie (nazwy z zestawu treningowego checkpointu) → encje Presidio (albo nazwy własne, gdy Presidio
# nie ma odpowiednika). Nie więcej niż 25 etykiet naraz (`max_types` modelu).
ETYKIETY = {
    "person": "PERSON",
    "organization": "ORGANIZATION",
    "address": "LOCATION",
    "postal code": "POSTAL_CODE",
    "date of birth": "DATE_TIME",
    "email": "EMAIL_ADDRESS",
    "phone number": "PHONE_NUMBER",
    "ip address": "IP_ADDRESS",
    "iban": "IBAN_CODE",
    "bank account number": "BANK_ACCOUNT",
    "credit card number": "CREDIT_CARD",
    "passport number": "PASSPORT",
    "identity card number": "ID_CARD",
    "national id number": "NATIONAL_ID",
    "social security number": "SSN",
    "tax identification number": "TAX_ID",
    "driver's license number": "DRIVER_LICENSE",
    "license plate number": "LICENSE_PLATE",
    "registration number": "REGISTRATION_NUMBER",
    "health insurance number": "HEALTH_INSURANCE",
    "medical condition": "MEDICAL_CONDITION",
    "username": "USERNAME",
}


def sciezka_modelu() -> str:
    """Lokalne migawki modelu i jego szkieletu z przypiętych rewizji (HF_HOME = vendor/hf; offline po pobraniu)."""
    snapshot_download(SZKIELET[0], revision=SZKIELET[1], allow_patterns=["*.json", "*.model", "*.txt", "*.bin"],
                      ignore_patterns=["pytorch_model.generator.bin"])
    return snapshot_download(MODEL, revision=REWIZJE.get(MODEL))


def zbuduj():
    konf = {"nlp_engine_name": "spacy",
            "models": [{"lang_code": j, "model_name": m} for j, m in SPACY.items()]}
    nlp = NlpEngineProvider(nlp_configuration=konf).create_engine()
    sciezka = sciezka_modelu()
    # `chunk_size` ogromny: okna robimy sami (../_wspolne/okna.py), żeby test granicy okna dotyczył naszego kodu.
    wzor = GLiNERRecognizer(entity_mapping=ETYKIETY, model_name=sciezka, supported_language="pl", flat_ner=True,
                            multi_label=False, threshold=min(pu.PODLOGA, pu.wczytaj_prog(KATALOG, PROG_DOMYSLNY)),
                            map_location="cpu", chunk_size=10**9, chunk_overlap=0, name="GLiNERRecognizer")
    rozpoznawacze_gliner = []
    for j in SPACY:                           # jeden załadowany model, rozpoznawacz zarejestrowany dla każdego języka
        r = copy.copy(wzor)
        r.supported_language = j
        rozpoznawacze_gliner.append(r)
    analizator = pw.zbuduj_analizator(nlp, rozpoznawacze_nlp=False, rozpoznawacze_dodatkowe_wszystkie=rozpoznawacze_gliner)
    return analizator


def main() -> None:
    pu.ustaw_watki()
    analizator = zbuduj()
    prog = pu.wczytaj_prog(KATALOG, PROG_DOMYSLNY)

    def analizuj(tekst: str, jezyk: str) -> list:
        def okno(podtekst: str):
            return pw.tlumacz_wyniki(analizator.analyze(text=podtekst, language=jezyk))
        wyk = okna.analizuj_oknami(tekst, okna.okna_tokenowe(tekst, okna.TokenizerGliner(), MAX_TOKENOW, 0.20), okno)
        return [w for w in wyk if w[3] >= prog]

    wersje = {"presidio-analyzer": pw.wersja("presidio-analyzer"), "gliner": pw.wersja("gliner"),
              "torch": pw.wersja("torch"), "transformers": pw.wersja("transformers"),
              "hf:gliner": f"{MODEL}@{REWIZJE.get(MODEL, '?')}", "hf:szkielet": "{}@{}".format(*SZKIELET)}
    pu.petla(wersje, analizuj)


if __name__ == "__main__":
    main()
