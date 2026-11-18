"""Pełnomocnictwo procesowe z prawem substytucji, z opcjonalnym poświadczeniem notarialnym podpisu."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="pl", typ="pelnomocnictwo", dorosli=True,
    role={"kancelaria": "kancelaria", "mocodawca": "osoba", "pelnomocnik": "osoba", "substytut": "osoba",
          "notariusz": "osoba", "sprawa": "sprawa", "przeciwnik": "osoba"},
    sekcje=[
        sekcja("naglowek", "naglowek",
               "{kancelaria.nazwa}",
               "{kancelaria.adres}"),
        sekcja("miejscowosc", "akapit", "{mocodawca.miasto}, dnia {ctx.po_pozwie}"),
        sekcja("tytul", "akapit", "PEŁNOMOCNICTWO"),
        sekcja("mocodawca", "akapit",
               "Ja, {mocodawca.pelne}, PESEL {mocodawca.pesel}, adres zamieszkania: {mocodawca.adres}, "
               "{mocodawca.rodzaj:legitymujący|legitymująca} się dowodem osobistym seria i numer {mocodawca.dowod}, tel. {mocodawca.telefon}, "
               "udzielam niniejszym pełnomocnictwa:"),
        sekcja("pelnomocnik", "akapit",
               "{pelnomocnik.pelne:cel} – adwokatowi lub radcy prawnemu prowadzącemu działalność w ramach "
               "{kancelaria.nazwa}, z adresem do doręczeń: {kancelaria.adres}, adres e-mail "
               "{pelnomocnik.email},"),
        sekcja("zakres", "akapit",
               "do reprezentowania mnie w sprawie o sygn. akt {sprawa.sygnatura} z mojego powództwa przeciwko "
               "{przeciwnik.pelne:cel} oraz we wszystkich postępowaniach związanych z tą sprawą, w tym w "
               "postępowaniu zabezpieczającym, apelacyjnym, kasacyjnym i egzekucyjnym.",
               "Pełnomocnictwo obejmuje prawo do: wnoszenia i cofania pism procesowych, w tym pozwu, apelacji i "
               "zażaleń; zawierania ugód sądowych i pozasądowych; uznania roszczenia i zrzeczenia się roszczenia; "
               "wnoszenia o uzasadnienie orzeczeń; składania i odbierania oświadczeń woli w mojej sprawie.",
               "Pełnomocnik jest upoważniony do odbioru pism sądowych, dokumentów i wszelkich kwot "
               "przysądzonych lub wyegzekwowanych w sprawie, do wysokości {ctx.limit_odb}, na rachunek "
               "wskazany przez {mocodawca.rodzaj:mocodawcę|mocodawczynię}: {mocodawca.rachunek}.",
               "Pełnomocnik może udzielać dalszych pełnomocnictw, w szczególności {substytut.pelne:cel}, "
               "oraz ustanawiać substytutów do poszczególnych czynności procesowych.",
               "Upoważniam pełnomocnika do żądania wydania dokumentów dotyczących mojej osoby od organów "
               "administracji, banków i instytucji ubezpieczeniowych w zakresie niezbędnym do prowadzenia sprawy."),
        sekcja("rodo", "akapit",
               "Wyrażam zgodę na przetwarzanie moich danych osobowych przez pełnomocnika i podmioty, którym "
               "powierzy on wykonanie czynności, w zakresie niezbędnym do prowadzenia sprawy, zgodnie z "
               "rozporządzeniem (UE) 2016/679 (RODO). Pełnomocnik przetwarza dane w celu wykonania zlecenia i "
               "przez okres przedawnienia roszczeń z nim związanych.",
               "Pełnomocnictwo wygasa z chwilą prawomocnego zakończenia postępowania, chyba że zostanie "
               "odwołane wcześniej. Odwołanie wymaga formy pisemnej i staje się skuteczne po zawiadomieniu "
               "pełnomocnika oraz sądu."),
        sekcja("poswiadczenie", "akapit",
               "Poświadczam, że powyższy podpis {mocodawca.pelne:dop} został złożony w mojej obecności; "
               "tożsamość osoby stwierdzono na podstawie dowodu osobistego nr {mocodawca.dowod}. Notariusz "
               "{notariusz.pelne}, repertorium A nr 1204/2025, opłata taksy notarialnej pobrana.",
               min=0, max=1),
        sekcja("podpis_opis", "akapit", "Podpis {mocodawca.rodzaj:mocodawcy|mocodawczyni}:"),
        sekcja("podpis", "podpis", "{mocodawca.pelne}"),
        sekcja("stopka", "stopka",
               "{kancelaria.nazwa}, {kancelaria.adres} | tel. {kancelaria.telefon} | {kancelaria.email}"),
        sekcja("oplata", "przypis",
               "Od pełnomocnictwa pobrano opłatę skarbową w wysokości 17 zł na podstawie ustawy z dnia 16 listopada "
               "2006 r. o opłacie skarbowej; zwolnienie dotyczy pełnomocnictw udzielanych małżonkowi, "
               "wstępnemu, zstępnemu lub rodzeństwu."),
    ],
    metadane={"author": "{pelnomocnik.pelne}", "subject": "Pełnomocnictwo procesowe"},
)
