"""Polskie rozpoznawacze z sumą kontrolną napisane w stylu Presidio (`PatternRecognizer` + `validate_result`).

To „najlepsza uczciwa konfiguracja PL”, jaką zbudowałby integrator Presidio: wydanie 2.2.366 ma tylko PESEL (z sumą
kontrolną); NIP, REGON, KRS i numer dowodu osobistego dopisujemy według obowiązujących algorytmów (NIP: ustawa o zasadach
ewidencji i identyfikacji podatników; REGON: rozporządzenie w sprawie sposobu i metod prowadzenia i aktualizacji rejestru
REGON; dowód osobisty: rozporządzenie w sprawie dowodów osobistych – numer 3 litery + 6 cyfr, cyfra kontrolna na 4.
pozycji). Wartości spoza algorytmu są odrzucane (`validate_result` → False); KRS nie ma sumy kontrolnej, więc wymaga
kontekstu (wzmocnienie wyniku słowami „KRS”)."""
from __future__ import annotations

from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer
from sumy_kontrolne_pl import dowod_poprawny, nip_poprawny, regon_poprawny


class PlNipRecognizer(PatternRecognizer):
    """NIP: 10 cyfr (opcjonalnie prefiks PL, myślniki/spacje w układzie 3-3-2-2 lub 3-2-2-3) i suma kontrolna."""

    PATTERNS = [
        Pattern("NIP (ciągły)", r"\b(?:PL ?)?\d{10}\b", 0.3),
        Pattern("NIP (3-3-2-2)", r"\b(?:PL ?)?\d{3}[- ]\d{3}[- ]\d{2}[- ]\d{2}\b", 0.4),
        Pattern("NIP (3-2-2-3)", r"\b(?:PL ?)?\d{3}[- ]\d{2}[- ]\d{2}[- ]\d{3}\b", 0.4),
    ]
    CONTEXT = ["NIP", "numer identyfikacji podatkowej", "VAT", "podatnik"]

    def __init__(self, patterns: Optional[List[Pattern]] = None, context: Optional[List[str]] = None,
                 supported_language: str = "pl", supported_entity: str = "PL_NIP", name: Optional[str] = None):
        super().__init__(supported_entity=supported_entity, patterns=patterns or self.PATTERNS,
                         context=context or self.CONTEXT, supported_language=supported_language, name=name)

    def validate_result(self, pattern_text: str) -> bool:  # noqa: D102
        return nip_poprawny(pattern_text)


class PlRegonRecognizer(PatternRecognizer):
    """REGON: 9 lub 14 cyfr z sumą kontrolną (14-cyfrowy także z poprawnym 9-cyfrowym prefiksem)."""

    PATTERNS = [Pattern("REGON (9/14)", r"\b\d{9}(?:\d{5})?\b", 0.2)]
    CONTEXT = ["REGON", "rejestr gospodarki narodowej"]

    def __init__(self, patterns: Optional[List[Pattern]] = None, context: Optional[List[str]] = None,
                 supported_language: str = "pl", supported_entity: str = "PL_REGON", name: Optional[str] = None):
        super().__init__(supported_entity=supported_entity, patterns=patterns or self.PATTERNS,
                         context=context or self.CONTEXT, supported_language=supported_language, name=name)

    def validate_result(self, pattern_text: str) -> bool:  # noqa: D102
        return regon_poprawny(pattern_text)


class PlKrsRecognizer(PatternRecognizer):
    """KRS: 10 cyfr zaczynających się od 000 (numery KRS mają zera wiodące); bez sumy kontrolnej – wynik niski, podnosi go
    kontekst („KRS”)."""

    PATTERNS = [Pattern("KRS (000…)", r"\b000\d{7}\b", 0.3)]
    CONTEXT = ["KRS", "Krajowy Rejestr Sądowy", "Krajowego Rejestru Sądowego", "rejestr przedsiębiorców"]

    def __init__(self, patterns: Optional[List[Pattern]] = None, context: Optional[List[str]] = None,
                 supported_language: str = "pl", supported_entity: str = "PL_KRS", name: Optional[str] = None):
        super().__init__(supported_entity=supported_entity, patterns=patterns or self.PATTERNS,
                         context=context or self.CONTEXT, supported_language=supported_language, name=name)


class PlDowodRecognizer(PatternRecognizer):
    """Numer dowodu osobistego: 3 litery + 6 cyfr (opcjonalnie spacja), cyfra kontrolna na 4. pozycji."""

    PATTERNS = [Pattern("Dowód (AAA 123456)", r"\b[A-Z]{3} ?\d{6}\b", 0.3)]
    CONTEXT = ["dowód", "dowodu", "dowodem", "dowód osobisty", "seria i numer", "seria", "legitymuje się"]

    def __init__(self, patterns: Optional[List[Pattern]] = None, context: Optional[List[str]] = None,
                 supported_language: str = "pl", supported_entity: str = "PL_ID_CARD", name: Optional[str] = None):
        super().__init__(supported_entity=supported_entity, patterns=patterns or self.PATTERNS,
                         context=context or self.CONTEXT, supported_language=supported_language, name=name)

    def validate_result(self, pattern_text: str) -> bool:  # noqa: D102
        return dowod_poprawny(pattern_text)


def rozpoznawacze_pl() -> list:
    return [PlNipRecognizer(), PlRegonRecognizer(), PlKrsRecognizer(), PlDowodRecognizer()]
