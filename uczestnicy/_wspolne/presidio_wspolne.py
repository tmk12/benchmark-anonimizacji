"""Wspólne dla uczestników Presidio: rejestr rozpoznawaczy per język, tłumaczenie wyników, wersje.

Konfiguracja „jak zrobiłby kompetentny integrator”: dla KAŻDEGO z 5 języków korpusu rejestrujemy z `supported_language`
wszystkie wbudowane rozpoznawacze wzorcowe (e-mail, telefon, IBAN, karta, IP, URL, data, krypto, MAC, UUID) oraz krajowe
dostępne w zainstalowanym wydaniu Presidio (PL: PESEL; EN: USA + Wielka Brytania; ES: NIF/NIE/paszport; DE: komplet
rozpoznawaczy niemieckich; FR: wydanie nie ma żadnych francuskich). Listę zapisano w KONFIG.md uczestników."""
from __future__ import annotations

from importlib import metadata
from typing import Iterable

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer import predefined_recognizers as pr

JEZYKI = ("pl", "en", "es", "de", "fr")

# Wzorcowe, niezależne od kraju (rejestrowane dla każdego języka).
OGOLNE = ("EmailRecognizer", "UrlRecognizer", "IpRecognizer", "IbanRecognizer", "CreditCardRecognizer",
          "CryptoRecognizer", "DateRecognizer", "MacAddressRecognizer", "UuidRecognizer")

# Krajowe wbudowane wydania 2.2.366, włączone dla języka dokumentu, w którym występują.
KRAJOWE = {
    "pl": ("PlPeselRecognizer",),
    "en": ("UsSsnRecognizer", "UsItinRecognizer", "UsPassportRecognizer", "UsLicenseRecognizer", "UsBankRecognizer",
           "UsMbiRecognizer", "UsNpiRecognizer", "NhsRecognizer", "UkNinoRecognizer", "UkPassportRecognizer",
           "UkDrivingLicenceRecognizer", "UkPostcodeRecognizer", "UkVehicleRegistrationRecognizer",
           "MedicalLicenseRecognizer"),
    "es": ("EsNifRecognizer", "EsNieRecognizer", "EsPassportRecognizer"),
    "de": ("DeTaxIdRecognizer", "DeTaxNumberRecognizer", "DeVatIdRecognizer", "DeSocialSecurityRecognizer",
           "DeHealthInsuranceRecognizer", "DeIdCardRecognizer", "DePassportRecognizer", "DeFuehrerscheinRecognizer",
           "DeKfzRecognizer", "DePlzRecognizer", "DeHandelsregisterRecognizer", "DeBsnrRecognizer",
           "DeLanrRecognizer"),
    "fr": (),
}

# Telefon: domyślne regiony Presidio (US GB DE FR IL IN CA BR) nie zawierają PL ani ES – integrator dopisuje region
# kraju języka dokumentu (numery międzynarodowe z „+” są rozpoznawane niezależnie od regionu).
REGION_JEZYKA = {"pl": "PL", "en": "GB", "es": "ES", "de": "DE", "fr": "FR"}


def regiony_telefonu(jezyk: str) -> tuple[str, ...]:
    domyslne = pr.PhoneRecognizer.DEFAULT_SUPPORTED_REGIONS
    return (REGION_JEZYKA[jezyk],) + tuple(r for r in domyslne if r != REGION_JEZYKA[jezyk]) + ("PL", "ES")


def rozpoznawacze_jezyka(jezyk: str, dodatkowe: Iterable = ()) -> list:
    """Instancje rozpoznawaczy wzorcowych i krajowych dla jednego języka (+ `dodatkowe` – gotowe instancje)."""
    wyniki = [pr.PhoneRecognizer(supported_language=jezyk, supported_regions=tuple(dict.fromkeys(regiony_telefonu(jezyk))))]
    for nazwa in OGOLNE + KRAJOWE[jezyk]:
        wyniki.append(getattr(pr, nazwa)(supported_language=jezyk))
    wyniki.extend(dodatkowe)
    return wyniki


def zbuduj_analizator(nlp_engine, jezyki: Iterable[str] = JEZYKI, dodatkowe=None,
                      rozpoznawacze_nlp: bool = True, rozpoznawacze_dodatkowe_wszystkie=()) -> AnalyzerEngine:
    """AnalyzerEngine z rejestrem budowanym ręcznie (nie z domyślnego yaml, który zna tylko `en`).

    `dodatkowe`: {jezyk: [instancje]} – rozpoznawacze dopisywane tylko dla danego języka."""
    jezyki = tuple(jezyki)
    rejestr = RecognizerRegistry(supported_languages=list(jezyki))
    for j in jezyki:
        for r in rozpoznawacze_jezyka(j, (dodatkowe or {}).get(j, ())):
            rejestr.add_recognizer(r)
    for r in rozpoznawacze_dodatkowe_wszystkie:
        rejestr.add_recognizer(r)
    if rozpoznawacze_nlp:
        rejestr.add_nlp_recognizer(nlp_engine)
    return AnalyzerEngine(nlp_engine=nlp_engine, registry=rejestr, supported_languages=list(jezyki),
                          default_score_threshold=0.0)


def lista_rozpoznawaczy(analizator: AnalyzerEngine) -> dict[str, list[str]]:
    """{język: [nazwa rozpoznawacza (encje)]} – do KONFIG.md i testów."""
    wynik: dict[str, list[str]] = {}
    for r in analizator.registry.recognizers:
        wynik.setdefault(r.supported_language, []).append(f"{r.name} -> {','.join(r.supported_entities)}")
    return {j: sorted(v) for j, v in sorted(wynik.items())}


def tlumacz_wyniki(wyniki) -> list[tuple[int, int, str, float]]:
    """RecognizerResult → (start, koniec, etykieta Presidio, wynik); pusty span odrzucony."""
    return [(int(w.start), int(w.end), w.entity_type, float(w.score)) for w in wyniki if w.end > w.start]


def wersja(pakiet: str) -> str:
    try:
        return metadata.version(pakiet)
    except metadata.PackageNotFoundError:
        return "?"
