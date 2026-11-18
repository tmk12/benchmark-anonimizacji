"""Protokół rozprawy z przesłuchaniem świadka z Ukrainy z udziałem tłumacza języka ukraińskiego."""
from __future__ import annotations

from ....budowa import Szablon
from ..._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="pl", typ="protokol", dorosli=True, znacz_encje=True, warianty=("cw", "tr"),
    role={"sad": "sad", "sprawa": "sprawa", "sedzia": "osoba", "protokolant": "osoba", "powod": "osoba",
          "pozwany": "osoba", "swiadek": "osoba_ua", "tlumacz": "osoba"},
    sekcje=[
        sekcja("naglowek", "naglowek",
               "{sad.nazwa}",
               "PROTOKÓŁ ROZPRAWY"),
        sekcja("dane", "akapit",
               "Sygn. akt {sprawa.sygnatura}",
               "Data rozprawy: {ctx.rozprawa}",
               "Sąd w składzie: sędzia {sedzia.pelne}, {protokolant.rodzaj:protokolant|protokolantka}: {protokolant.pelne}"),
        sekcja("stawiennictwo", "akapit",
               "Po wywołaniu sprawy stawili się: {powod.rodzaj:powód|powódka} {powod.pelne} oraz "
               "{pozwany.rodzaj:pozwany|pozwana} {pozwany.pelne}.",
               "Ponadto stawili się: świadek {swiadek.pelne_im:t_s1} ({swiadek.pelne_im:t_s2}) oraz "
               "{tlumacz.rodzaj:tłumacz przysięgły|tłumaczka przysięgła} języka ukraińskiego {tlumacz.pelne}."),
        sekcja("pouczenie", "akapit",
               "Sąd pouczył świadka o prawie odmowy zeznań oraz o odpowiedzialności karnej za składanie "
               "fałszywych zeznań (art. 233 Kodeksu karnego). {tlumacz.rodzaj:Tłumacz został pouczony|Tłumaczka została "
               "pouczona} o odpowiedzialności za "
               "nieprawdziwe tłumaczenie. Świadek {swiadek.rodzaj:oświadczył|oświadczyła}, że rozumie pouczenie.",
               "Świadek {swiadek.rodzaj:zeznał|zeznała} za pośrednictwem {tlumacz.rodzaj:tłumacza|tłumaczki}, co następuje."),
        sekcja("dane_swiadka", "akapit",
               "Świadek {swiadek.rodzaj:podał|podała}: imię i nazwisko – {swiadek.pelne_im:t_s1}, w innym zapisie: "
               "{swiadek.pelne_im:t_s2}; data urodzenia – {swiadek.data_ur}; adres zamieszkania – "
               "{swiadek.adres:t_s1} ({swiadek.adres:t_s2}); obywatelstwo – ukraińskie; dokument tożsamości – "
               "paszport zagraniczny nr {swiadek.paszport}, numer РНОКПП {swiadek.rnokpp}; telefon "
               "{swiadek.telefon}.",
               "Świadek nie jest {swiadek.rodzaj:spokrewniony|spokrewniona} ani {swiadek.rodzaj:spowinowacony|spowinowacona} z żadną ze stron i nie pozostaje z nimi w stosunku "
               "zależności służbowej.",
               W("tr", "Imię i nazwisko świadka figuruje w aktach sprawy także w zapisach: {swiadek.pelne_im:t_s3} "
                       "oraz {swiadek.pelne_im:t_s4}; {tlumacz.rodzaj:tłumacz potwierdził|tłumaczka potwierdziła}, że dotyczą one tej samej osoby.")),
        sekcja("zeznanie", "akapit",
               "Świadek {swiadek.rodzaj:zeznał|zeznała}, że {swiadek.rodzaj:znał|znała} {powod.pelne:bier} od kilku lat, a o "
               "zawarciu umowy {swiadek.rodzaj:dowiedział|dowiedziała} się bezpośrednio od {powod.pelne:dop}. Świadek "
               "{swiadek.rodzaj:potwierdził|potwierdziła}, że w czasie rozmowy w dniu poprzedzającym podpisanie umowy "
               "{pozwany.pelne} nie {pozwany.rodzaj:zgłaszał|zgłaszała} zastrzeżeń do jej treści.",
               "Na pytanie pełnomocnika {pozwany.rodzaj:pozwanego|pozwanej} świadek {swiadek.rodzaj:odpowiedział|odpowiedziała}, że "
               "nie pamięta dokładnej daty rozmowy; {swiadek.rodzaj:wskazał|wskazała} jednak, że miała ona miejsce w "
               "miejscowości {powod.miasto}.",
               "Sąd odczytał świadkowi treść protokołu w języku ukraińskim za pośrednictwem {tlumacz.rodzaj:tłumacza|tłumaczki}. "
               "Świadek "
               "{swiadek.rodzaj:zatwierdził|zatwierdziła} jego treść bez uwag.",
               min=2, max=3),
        sekcja("zakonczenie", "akapit",
               "Sąd zwolnił świadka po złożeniu zeznań. Rozprawę odroczono do dnia {ctx.przed_rozprawa}. "
               "Wynagrodzenie {tlumacz.rodzaj:tłumacza|tłumaczki} ustalono postanowieniem na rachunek wskazany przez {tlumacz.pelne:bier}.",
               "Na tym protokół zakończono."),
        sekcja("podpis_opis", "akapit", "{protokolant.rodzaj:Protokolant|Protokolantka}: {protokolant.pelne} | Sędzia: {sedzia.pelne}"),
        sekcja("podpis", "podpis", "{sedzia.pelne}"),
        sekcja("stopka", "stopka", "{sad.nazwa} | protokół rozprawy w sprawie {sprawa.sygnatura}"),
    ],
    metadane={"author": "{protokolant.pelne}", "subject": "Protokół rozprawy"},
)
