"""Lista płac pracodawcy (arkusz XLSX): nagłówek, okres, tabela z ponad 200 pracownikami, podsumowanie, uwagi.

Każdy wiersz tabeli ma własną osobę (`p000`…), bo gniazda jednej roli mają jedną wartość; wynagrodzenia i sumy
bierze z kontekstu (`ctx.brutto_<i>`, `ctx.suma_<n>`), więc podsumowanie zgadza się z tabelą.
"""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja, z_zamianami

WIERSZE = 212
_STANOWISKA = ("Specjalista ds. kadr", "Księgowa", "Kierownik działu", "Młodszy prawnik", "Asystent zarządu",
               "Kierowca", "Magazynier", "Referent", "Starszy specjalista", "Inspektor BHP", "Konsultant",
               "Administrator IT")

#: Stanowiska tylko w formie żeńskiej -> forma męska (warstwa trudna, J1 S5: „Jakub Marciniak … Księgowa” w trzonie).
_STANOWISKA_ZENSKIE = {"Księgowa": "Księgowy"}

_ROLE_WIERSZY = {f"p{i:03d}": "osoba" for i in range(WIERSZE)}


def _tabela(zgodna_plec: bool = False) -> str:
    """Tabela płac; `zgodna_plec` (warstwa trudna) – stanowisko żeńskie jako gniazdo rodzaju (`{pNNN.rodzaj:m|k}`): forma
    zgodna z płcią osoby wiersza. Trzon – stała forma (sumy kontrolne trzonu)."""
    wiersze = ["Lp. | Imię | Nazwisko | PESEL | Stanowisko | Wynagrodzenie brutto | Rachunek bankowy"]
    for i in range(WIERSZE):
        p = f"p{i:03d}"
        stanowisko = _STANOWISKA[i % len(_STANOWISKA)]
        if zgodna_plec and stanowisko in _STANOWISKA_ZENSKIE:
            stanowisko = f"{{{p}.rodzaj:{_STANOWISKA_ZENSKIE[stanowisko]}|{stanowisko}}}"
        wiersze.append(f"{i + 1} | {{{p}.pelne/1}} | {{{p}.pelne/2}} | {{{p}.pesel}} | {stanowisko}"
                       f" | {{ctx.brutto_{i}}} | {{{p}.rachunek}}")
    return "\n".join(wiersze)


def _szablon(zgodna_plec: bool) -> Szablon:
    return Szablon(
        jezyk="pl", typ="lista_plac",
        role={"firma": "firma", "sporzadzil": "osoba", "zatwierdzil": "osoba", "kadry": "osoba",
              } | _ROLE_WIERSZY,
        sekcje=[
            sekcja("naglowek", "naglowek",
                   "{firma.nazwa}",
                   "{firma.adres} | NIP {firma.nip} | REGON {firma.regon}"),
            sekcja("tytul", "akapit",
                   "LISTA PŁAC PRACOWNIKÓW",
                   "Okres rozliczeniowy: miesiąc kalendarzowy, termin wypłaty: {ctx.dok_termin}",
                   "Pracodawca: {firma.nazwa}, KRS {firma.krs}"),
            sekcja("tabela", "komorka", _tabela(zgodna_plec)),
            sekcja("podsumowanie", "komorka",
                   "Pozycja | Kwota\n"
                   "Suma wynagrodzeń brutto | {ctx.suma_212}\n"
                   "Składki ZUS finansowane przez pracodawcę | {ctx.zus_212}\n"
                   "Zaliczki na podatek dochodowy (PIT-4R) | {ctx.pit_212}"),
            sekcja("uwagi", "akapit",
                   "Wynagrodzenia wypłacono na podstawie art. 85 Kodeksu pracy w terminie do 10. dnia następnego "
                   "miesiąca, przelewem na rachunki wskazane przez pracowników.",
                   "Składki na ubezpieczenia społeczne i zdrowotne oraz zaliczki na podatek dochodowy obliczono "
                   "zgodnie z ustawą z dnia 13 października 1998 r. o systemie ubezpieczeń społecznych i ustawą o "
                   "podatku dochodowym od osób fizycznych.",
                   "Lista została sporządzona z uwzględnieniem kwoty wolnej od potrąceń (art. 871 Kodeksu pracy) "
                   "oraz zajęć komorniczych zgłoszonych do dnia zamknięcia miesiąca.",
                   "Dokument zawiera dane osobowe pracowników i podlega ochronie zgodnie z RODO; przechowywanie: "
                   "10 lat od końca roku kalendarzowego, w którym stosunek pracy ustał (art. 94 pkt 9b Kodeksu pracy)."),
            sekcja("sporzadzil", "akapit",
                   "Sporządził: {sporzadzil.pelne}, dział kadr i płac, tel. {sporzadzil.telefon}",
                   "Sprawdził: {kadry.pelne}",
                   "Zatwierdził do wypłaty: {zatwierdzil.pelne}"),
            sekcja("podpisy", "podpis", "{sporzadzil.pelne}", "{zatwierdzil.pelne}"),
            sekcja("stopka", "stopka", "{firma.nazwa} | {firma.adres} | tel. {firma.telefon} | {firma.email}"),
        ],
        metadane={"author": "{sporzadzil.pelne}", "subject": "Lista płac"},
    )


SZABLON = _szablon(False)
#: Wariant warstwy trudnej (`szablony.SZABLONY_TRUDNE`): stanowisko zgodne z płcią osoby wiersza, czasowniki podpisów zgodne
#: z płcią osób, które sporządziły, sprawdziły i zatwierdziły listę.
SZABLON_ZGODNA_PLEC = z_zamianami(_szablon(True), {
    "Sporządził: {sporzadzil.pelne}": "{sporzadzil.rodzaj:Sporządził|Sporządziła}: {sporzadzil.pelne}",
    "Sprawdził: {kadry.pelne}": "{kadry.rodzaj:Sprawdził|Sprawdziła}: {kadry.pelne}",
    "Zatwierdził do wypłaty: {zatwierdzil.pelne}": "{zatwierdzil.rodzaj:Zatwierdził|Zatwierdziła} do wypłaty: {zatwierdzil.pelne}"})
