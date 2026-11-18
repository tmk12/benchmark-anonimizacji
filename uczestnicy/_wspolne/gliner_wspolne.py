"""Wspólny kod samodzielnych uczestników GLiNER (`gliner-*-pii`): ładowanie przypiętego checkpointu, okna tokenowe
GLiNER z zakładką, predykcja z jawną listą etykiet i pętla protokołu.

Uczestnik nie używa Presidio ani spaCy: wywołuje `GLiNER.predict_entities` wprost, tak jak w karcie modelu. Różnice między
modelami (rewizja, etykiety, próg domyślny, limit okna) żyją w `run.py` danego uczestnika."""
from __future__ import annotations

import os
from importlib import metadata
from pathlib import Path

import okna
import protokol_uczestnika as pu
from huggingface_hub import snapshot_download

ZAKLADKA = 0.20                      # zakładka okien (>= 10% wymagane rozstrzygnięciem; 20% jak w presidio-gliner)
ZAPAS = 0.06                         # krawędź okna cofana do granicy słowa dodaje <= zakładka/2 tokenów (10% okna)


def wersja(pakiet: str) -> str:
    try:
        return metadata.version(pakiet)
    except metadata.PackageNotFoundError:
        return "?"


def pobierz(repo: str, rewizja: str, dodatkowe: tuple[str, ...] = ()) -> str:
    """Migawka repozytorium w `HF_HOME` (vendor/hf) z przypiętej rewizji; tylko wagi PyTorch i pliki tokenizera/konfiguracji
    (bez ONNX). `dodatkowe` = pary „repo@rewizja” szkieletu, którego tokenizer/konfigurację ładuje biblioteka po nazwie."""
    for d in dodatkowe:
        r, v = d.split("@")
        snapshot_download(r, revision=v, allow_patterns=["*.json", "*.model", "*.txt", "*.bin"],
                          ignore_patterns=["pytorch_model.generator.bin"])
    return snapshot_download(repo, revision=rewizja,
                             allow_patterns=["*.json", "*.bin", "*.model", "*.txt", "*.md", "*.jinja"],
                             ignore_patterns=["onnx/*"])


def zaladuj(sciezka: str):
    """Model GLiNER na CPU (`CUDA_VISIBLE_DEVICES` puste), tryb eval."""
    from gliner import GLiNER
    model = GLiNER.from_pretrained(sciezka, map_location="cpu")
    model.eval()
    return model


def limit_okna(max_len_modelu: int, limit_okna_cfg: int) -> int:
    """Liczba tokenów GLiNER w oknie: nie więcej niż `limit_okna_cfg` i z zapasem na cofnięcie krawędzi do granicy słowa
    (zakładka/2) poniżej `max_len` modelu. `PBENCH_OKNO_TOKENOW` (testy granicy okna) nadpisuje."""
    if "PBENCH_OKNO_TOKENOW" in os.environ:
        return int(os.environ["PBENCH_OKNO_TOKENOW"])
    return min(limit_okna_cfg, int(max_len_modelu * (1 - ZAKLADKA / 2 - ZAPAS)))


def analizator(*, model, etykiety: list[list[str]], flat_ner: bool = True, prog: float, max_tokenow: int):
    """`analizuj(tekst, jezyk)` uczestnika: okna tokenowe → `predict_entities` (bez multi_label) → scalenie → filtr progu.

    `flat_ner` wg karty modelu (parametr `flat_ner` uczestnika): domyślne `True` (płaski wybór spanów, jak w kartach i bibliotece);
    `False` tylko tam, gdzie karta/pomiar tego wymaga (nvidia/gliner-PII – zob. jego KONFIG.md).

    `etykiety` = lista grup po ≤ `max_types` modelu (model trenowano z ≤ `max_types` typami w jednym przebiegu); każda grupa
    to osobny przebieg na oknie, wykrycia z grup są sumowane (nakładające się z różnych grup zostają – sędzia scala pokrycie).
    Tej samej funkcji używa wariant krzyżowy `privatizer-tekst-gliner` (detektor w potoku Privatizera)."""
    def okno(podtekst: str) -> list:
        wyniki = []
        for grupa in etykiety:
            wyk = model.predict_entities(podtekst, grupa, flat_ner=flat_ner, threshold=min(pu.PODLOGA, prog), multi_label=False)
            wyniki += [(int(w["start"]), int(w["end"]), w["label"], float(w["score"])) for w in wyk]
        return wyniki

    def analizuj(tekst: str, jezyk: str) -> list:
        ok = okna.okna_tokenowe(tekst, okna.TokenizerGliner(), max_tokenow, ZAKLADKA)
        return [w for w in okna.analizuj_oknami(tekst, ok, okno) if w[3] >= prog]

    return analizuj


def main(*, model, etykiety: list[list[str]], flat_ner: bool = True, prog_domyslny: float, katalog: Path, max_tokenow: int, wersje: dict[str, str]) -> None:
    """Pętla uczestnika z `analizator` i progiem z `prog.json` (`PBENCH_SUROWE=1` → podłoga)."""
    prog = pu.wczytaj_prog(katalog, prog_domyslny)
    pu.petla(wersje, analizator(model=model, etykiety=etykiety, flat_ner=flat_ner, prog=prog, max_tokenow=max_tokenow))
