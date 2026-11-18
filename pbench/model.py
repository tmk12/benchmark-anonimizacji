"""Model syntetycznego dokumentu z wartościami wzorcowymi (gold) i wykryć uczestników.

Wyłącznie dane syntetyczne. Nie importuje `lgprivatizer` – lista kategorii jest skopiowana
(źródło: `lgprivatizer/categories.py` repo privatizer, klucze kategorii).
"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from typing import Any, Literal

# Klucze kategorii Privatizera (kopia, nie import – niezależność pomiaru).
KATEGORIE: frozenset[str] = frozenset({
    "OSOBA", "INICJALY", "ORGANIZACJA", "LOGIN", "ADRES", "KOD_POCZTOWY", "MIEJSCOWOSC",
    "REGION", "KRAJ", "EMAIL", "TELEFON", "URL", "IP", "MAC", "UUID", "PESEL", "NIP", "REGON",
    "KRS", "DOWOD", "PASZPORT", "PRAWO_JAZDY", "NR_ID", "NR_REJESTRACYJNY", "KSIEGA_WIECZYSTA",
    "SYGNATURA", "NR_REJESTRU", "IDENTYFIKATOR", "MRZ", "DNI", "CIF", "NUSS", "SSN", "EIN",
    "MBI", "NINO", "NHS", "NR_PODATKOWY", "VAT", "SVNR", "KVNR", "NIR", "SIREN", "RACHUNEK",
    "KARTA", "KRYPTO", "KWOTA", "ZDROWIE", "DATA_UR", "MIEJSCE_UR", "DATA", "SEKRET", "TWARZ",
    "WLASNE",
})

Miejsce = Literal["tresc", "tabela", "naglowek", "stopka", "przypis", "komentarz", "zmiany",
                  "metadane", "pole", "obraz", "zalacznik"]
MIEJSCA: frozenset[str] = frozenset({
    "tresc", "tabela", "naglowek", "stopka", "przypis", "komentarz", "zmiany",
    "metadane", "pole", "obraz", "zalacznik",
})


@dataclass
class Wartosc:
    """Wartość wrażliwa wstawiona do dokumentu (gold)."""

    id: str
    kategoria: str
    tekst: str
    jezyk: str
    miejsce: Miejsce
    waga_klucz: str  # klucz ważenia/grupowania (np. ta sama osoba w wielu miejscach)
    #: system transliteracji zapisu (`kmu2010`, `polski`…; zob. `pbench.translit`); None = zapis oryginalny
    translit: str | None = None
    #: wspólny identyfikator osoby/podmiotu, gdy ta sama encja występuje w kilku zapisach (cyrylica, transliteracje,
    #: homoglify); None = nie dotyczy (trzon korpusu)
    encja: str | None = None
    #: cechy zapisu (warstwa trudnych przypadków), np. `pisownia_rosyjska`, `homoglify`
    cechy: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.kategoria not in KATEGORIE:
            raise ValueError(f"nieznana kategoria: {self.kategoria!r}")
        if self.miejsce not in MIEJSCA:
            raise ValueError(f"nieznane miejsce: {self.miejsce!r}")

    @property
    def w_pikselach(self) -> bool:
        """Wartość narysowana na obrazie (sędzia szuka jej w OCR). `obraz` z cechą `tekst_xml` (alt text, wykres, obiekt
        osadzony) to tekst w XML pakietu – sędzia szuka go jak zwykłego tekstu."""
        return self.miejsce == "obraz" and "tekst_xml" not in self.cechy

    def to_dict(self) -> dict[str, Any]:
        wynik: dict[str, Any] = {"id": self.id, "kategoria": self.kategoria, "tekst": self.tekst,
                                 "jezyk": self.jezyk, "miejsce": self.miejsce, "waga_klucz": self.waga_klucz}
        # pola warstwy trudnej tylko gdy ustawione: zapis wartości trzonu korpusu pozostaje bajtowo taki sam
        if self.translit is not None:
            wynik["translit"] = self.translit
        if self.encja is not None:
            wynik["encja"] = self.encja
        if self.cechy:
            wynik["cechy"] = list(self.cechy)
        return wynik

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Wartosc:
        return cls(d["id"], d["kategoria"], d["tekst"], d["jezyk"], d["miejsce"], d["waga_klucz"],
                   d.get("translit"), d.get("encja"), list(d.get("cechy", ())))


def _frag_do_dict(f: str | Wartosc) -> str | dict[str, Any]:
    return f if isinstance(f, str) else {"wartosc": f.to_dict()}


def _frag_z_dict(f: str | dict[str, Any]) -> str | Wartosc:
    return f if isinstance(f, str) else Wartosc.from_dict(f["wartosc"])


@dataclass
class Element:
    """Element struktury dokumentu (akapit, komórka, nagłówek…) z fragmentami tekstu i wartości."""

    rodzaj: str
    fragmenty: list[str | Wartosc]
    atrybuty: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"rodzaj": self.rodzaj, "fragmenty": [_frag_do_dict(f) for f in self.fragmenty],
                "atrybuty": self.atrybuty}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Element:
        return cls(d["rodzaj"], [_frag_z_dict(f) for f in d["fragmenty"]], d.get("atrybuty", {}))


@dataclass
class Obraz:
    """Obraz osadzony w dokumencie; `ramki` = (id wartości, bbox x0, y0, x1, y1)."""

    id: str
    png: bytes | None
    wartosci: list[Wartosc] = field(default_factory=list)
    ramki: list[tuple[str, tuple[int, int, int, int]]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        png = None if self.png is None else base64.b64encode(self.png).decode("ascii")
        return {"id": self.id, "png": png, "wartosci": [w.to_dict() for w in self.wartosci],
                "ramki": [[wid, list(bbox)] for wid, bbox in self.ramki]}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Obraz:
        png = None if d["png"] is None else base64.b64decode(d["png"])
        return cls(d["id"], png, [Wartosc.from_dict(w) for w in d["wartosci"]],
                   [(wid, tuple(bbox)) for wid, bbox in d["ramki"]])


@dataclass
class Dokument:
    """Syntetyczny dokument: struktura, metadane i obrazy z pełnym gold."""

    id: str
    jezyk: str
    typ: str
    format: str
    elementy: list[Element] = field(default_factory=list)
    metadane: dict[str, str | Wartosc] = field(default_factory=dict)
    obrazy: list[Obraz] = field(default_factory=list)
    #: treść ukryta w pakiecie pliku (warstwa trudnych przypadków, `pbench.trudne_ukryta`): elementy, których nie ma w
    #: tekście poziomu 1 (`Element.rodzaj` = `<format>.<rodzaj>`, np. `docx.zakladka`); dopisuje je `po_renderze` budowy
    ukryte: list[Element] = field(default_factory=list)
    #: data wysłania wiadomości e-mail (ISO 8601 ze strefą; warstwa trudna, `pbench.trudne_poczta`): nagłówek `Date` spójny
    #: z treścią i cytowanym wątkiem; None – data losowa renderera poczty (trzon)
    wyslano: str | None = None

    def to_dict(self) -> dict[str, Any]:
        wynik = {"id": self.id, "jezyk": self.jezyk, "typ": self.typ, "format": self.format,
                 "elementy": [e.to_dict() for e in self.elementy],
                 "metadane": {k: _frag_do_dict(v) for k, v in self.metadane.items()},
                 "obrazy": [o.to_dict() for o in self.obrazy]}
        if self.ukryte:      # tylko gdy ustawione: JSON dokumentów trzonu pozostaje bajtowo taki sam
            wynik["ukryte"] = [e.to_dict() for e in self.ukryte]
        if self.wyslano is not None:
            wynik["wyslano"] = self.wyslano
        return wynik

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Dokument:
        return cls(d["id"], d["jezyk"], d["typ"], d["format"],
                   [Element.from_dict(e) for e in d["elementy"]],
                   {k: _frag_z_dict(v) for k, v in d["metadane"].items()},
                   [Obraz.from_dict(o) for o in d["obrazy"]],
                   [Element.from_dict(e) for e in d.get("ukryte", ())], d.get("wyslano"))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, tekst: str) -> Dokument:
        return cls.from_dict(json.loads(tekst))


@dataclass
class Wykrycie:
    """Fragment wykryty przez uczestnika: [start, end) w tekście wejściowym."""

    start: int
    end: int
    etykieta: str
    wynik: float | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.start < self.end:
            raise ValueError(f"niepoprawny zakres wykrycia: [{self.start}, {self.end})")
