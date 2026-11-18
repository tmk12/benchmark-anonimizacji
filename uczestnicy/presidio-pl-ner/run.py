"""Uczestnik `presidio-pl-ner`: Presidio z silnikiem NLP `transformers` (NER HF per język) + rozpoznawacze PL z sumą kontrolną.

Konfiguracja, wybór modeli i uzasadnienie: KONFIG.md. Okna tokenowe (tokenizer modelu danego języka, limit 512 tokenów
minus tokeny specjalne i zapas) z zakładką 12% i scalaniem offsetów (`../_wspolne/okna.py`)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

KATALOG = Path(__file__).resolve().parent
sys.path.insert(0, str(KATALOG.parent / "_wspolne"))

import okna  # noqa: E402
import presidio_wspolne as pw  # noqa: E402
import protokol_uczestnika as pu  # noqa: E402
import rozpoznawacze_pl  # noqa: E402
from huggingface_hub import snapshot_download  # noqa: E402
from presidio_analyzer.nlp_engine import NlpEngineProvider  # noqa: E402

SPACY = {"pl": "pl_core_news_lg", "en": "en_core_web_lg", "es": "es_core_news_lg", "de": "de_core_news_lg",
         "fr": "fr_core_news_lg"}          # tylko tokenizacja/lematyzacja (NER robi model transformers)
# PBENCH_JEZYKI="pl" ładuje tylko wskazane języki (porównania modeli na dev); domyślnie wszystkie 5
JEZYKI = tuple(j for j in os.environ.get("PBENCH_JEZYKI", "pl,en,es,de,fr").split(",") if j in SPACY)
# Modele NER i przypięte rewizje: zob. KONFIG.md (wybór na dev / z kart modeli). Nadpisanie do porównań:
# PBENCH_MODEL_<JEZYK>="repo" albo "repo@rewizja".
MODELE = json.loads((KATALOG / "modele.json").read_text(encoding="utf-8"))
LIMIT_TOKENOW = 512
ZAPAS_TOKENOW = 40                          # tokeny specjalne + różnice retokenizacji podłańcucha
MAX_TOKENOW = int(os.environ.get("PBENCH_OKNO_TOKENOW", LIMIT_TOKENOW - ZAPAS_TOKENOW))
# Strategia agregacji tokenów HF. Domyślne „max” z conf/transformers.yaml autorów źle skleja encje wielowyrazowe dla
# tokenizerów BPE z końcówkami słów (HerBERT: „Jan Kowalski” → „Jan”), więc stosujemy „simple” (domyślną HF) – zob. KONFIG.md.
AGREGACJA = os.environ.get("PBENCH_AGREGACJA", "simple")
PROG_DOMYSLNY = 0.0                         # `default_score_threshold: 0` w konfiguracji autorów

# Etykiety modeli (CoNLL/WikiANN/KPWr/NKJP) → encje Presidio (baza: conf/transformers.yaml autorów).
MAPOWANIE_NER = {
    "PER": "PERSON", "PERSON": "PERSON", "persName": "PERSON", "PERS": "PERSON",
    "LOC": "LOCATION", "LOCATION": "LOCATION", "GPE": "LOCATION", "placeName": "LOCATION", "geogName": "LOCATION",
    "ORG": "ORGANIZATION", "ORGANIZATION": "ORGANIZATION", "orgName": "ORGANIZATION",
    "DATE": "DATE_TIME", "TIME": "DATE_TIME", "date": "DATE_TIME", "time": "DATE_TIME",
    "NORP": "NRP",
    # clarin-pl/FastPDN (NKJP/KPWr, etykiety hierarchiczne `nam_*`): osoby, miejsca, organizacje, telefon
    "nam_liv_person": "PERSON",
    "nam_org_company": "ORGANIZATION", "nam_org_institution": "ORGANIZATION", "nam_org_organization": "ORGANIZATION",
    "nam_org_organization_sub": "ORGANIZATION", "nam_org_group": "ORGANIZATION", "nam_org_nation": "ORGANIZATION",
    "nam_org_political_party": "ORGANIZATION",
    "nam_num_phone": "PHONE_NUMBER", "nam_oth_www": "URL",
    # lexedit/herbert-polish-legal-ner (prawniczy NER z klasami PII)
    "LOC_PUB": "LOCATION", "EMAIL": "EMAIL_ADDRESS", "IBAN": "IBAN_CODE", "PHONE": "PHONE_NUMBER", "ID": "ID",
    "MEDICAL_ID": "ID", "DIAGNOSIS": "MEDICAL_CONDITION", "HEALTH_FACILITY": "ORGANIZATION",
    **{etykieta: "LOCATION" for etykieta in (
        "nam_loc", "nam_loc_astronomical", "nam_loc_country_region", "nam_loc_gpe_admin1", "nam_loc_gpe_admin2",
        "nam_loc_gpe_admin3", "nam_loc_gpe_city", "nam_loc_gpe_conurbation", "nam_loc_gpe_country",
        "nam_loc_gpe_district", "nam_loc_gpe_subdivision", "nam_loc_historical_region", "nam_loc_land",
        "nam_loc_land_region", "nam_fac_goe", "nam_fac_road", "nam_fac_square", "nam_fac_park")},
}
POMIJANE = ["O", "MISC", "MIS", "misc"]


def _model(jezyk: str) -> tuple[str, str | None]:
    wartosc = os.environ.get(f"PBENCH_MODEL_{jezyk.upper()}") or MODELE[jezyk]["repo"] + "@" + MODELE[jezyk]["rewizja"]
    repo, _, rewizja = wartosc.partition("@")
    return repo, rewizja or None


def sciezka_modelu(jezyk: str) -> str:
    """Lokalna migawka modelu z przypiętej rewizji (HF_HOME = vendor/hf; offline po pierwszym pobraniu)."""
    repo, rewizja = _model(jezyk)
    return snapshot_download(repo, revision=rewizja)


def zbuduj():
    sciezki = {j: sciezka_modelu(j) for j in JEZYKI}
    konf = {
        "nlp_engine_name": "transformers",
        "models": [{"lang_code": j, "model_name": {"spacy": SPACY[j], "transformers": sciezki[j]}} for j in JEZYKI],
        "ner_model_configuration": {
            "labels_to_ignore": POMIJANE,
            "aggregation_strategy": AGREGACJA,
            "stride": 16,                   # jak w conf/transformers.yaml; okna robimy sami, więc nie powinien być używany
            "alignment_mode": "expand",
            "model_to_presidio_entity_mapping": MAPOWANIE_NER,
            "low_confidence_score_multiplier": 0.4,
            "low_score_entity_names": [],
        },
    }
    nlp = NlpEngineProvider(nlp_configuration=konf).create_engine()
    analizator = pw.zbuduj_analizator(nlp, jezyki=JEZYKI, dodatkowe={"pl": rozpoznawacze_pl.rozpoznawacze_pl()})
    return analizator, sciezki


def main() -> None:
    pu.ustaw_watki()
    from transformers import AutoTokenizer
    analizator, sciezki = zbuduj()
    tokenizery = {j: AutoTokenizer.from_pretrained(p) for j, p in sciezki.items()}
    prog = pu.wczytaj_prog(KATALOG, PROG_DOMYSLNY)

    def analizuj(tekst: str, jezyk: str) -> list:
        def okno(podtekst: str):
            return pw.tlumacz_wyniki(analizator.analyze(text=podtekst, language=jezyk))
        wyk = okna.analizuj_oknami(tekst, okna.okna_tokenowe(tekst, tokenizery[jezyk], MAX_TOKENOW), okno)
        return [w for w in wyk if w[3] >= prog]

    wersje = {"presidio-analyzer": pw.wersja("presidio-analyzer"), "spacy": pw.wersja("spacy"),
              "transformers": pw.wersja("transformers"), "torch": pw.wersja("torch"),
              **{f"hf:{j}": "{}@{}".format(*_model(j)) for j in JEZYKI}}
    pu.petla(wersje, analizuj)


if __name__ == "__main__":
    main()
