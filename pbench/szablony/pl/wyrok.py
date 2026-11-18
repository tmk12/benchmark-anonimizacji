"""Wyrok sądu cywilnego (zapłata z umowy) z uzasadnieniem; skład sądu, strony i cytaty orzeczeń.

Dwa warianty: „rejonowy” – pierwsza instancja, sąd rejonowy, sędzia jednoosobowo; „apelacyjny” – apelacja
rozpoznawana przez sąd okręgowy w składzie trzech sędziów. Daty, kwoty i rok sygnatury biorą się z `Kontekst`.
"""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="pl", typ="wyrok", warianty=("rejonowy", "apelacyjny"),
    role={"sad": "sad", "sedzia1": "osoba", "sedzia2": "osoba", "sedzia3": "osoba", "protokolant": "osoba",
          "powod": "osoba", "pozwany": "osoba", "pelp": "osoba", "pelpoz": "osoba", "swiadek": "osoba",
          "swiadek2": "osoba", "biegly": "osoba", "cytat1": "cytat", "cytat2": "cytat", "cytat3": "cytat"},
    sekcje=[
        sekcja("naglowek", "naglowek",
               "Sygn. akt {sad.sygnatura}",
               "WYROK",
               "W IMIENIU RZECZYPOSPOLITEJ POLSKIEJ",
               "{ctx.wyrok_koncowy}"),
        sekcja("sklad", "akapit",
               W("rejonowy", "{sad.nazwa} Wydział Cywilny w składzie jednoosobowym:"),
               W("rejonowy", "sędzia {sedzia1.pelne} jako {sedzia1.rodzaj:przewodniczący|przewodnicząca}"),
               W("apelacyjny", "{sad.nazwa} II Wydział Cywilny Odwoławczy w składzie następującym:"),
               W("apelacyjny", "{sedzia1.rodzaj:Przewodniczący|Przewodnicząca}: sędzia {sedzia1.pelne}"),
               W("apelacyjny", "Sędziowie: {sedzia2.pelne}, {sedzia3.pelne}"),
               "Protokolant: {protokolant.pelne}",
               W("rejonowy", "po rozpoznaniu w dniu {ctx.rozprawa_koncowa} na rozprawie sprawy z powództwa "
                 "{powod.pelne:dop} przeciwko {pozwany.pelne:cel} o zapłatę, przy udziale pełnomocnika {powod.rodzaj:powoda|powódki} "
                 "{pelp.pelne:dop} oraz pełnomocnika {pozwany.rodzaj:pozwanego|pozwanej} {pelpoz.pelne:dop},"),
               W("apelacyjny", "po rozpoznaniu w dniu {ctx.rozprawa_koncowa} na rozprawie apelacyjnej sprawy z "
                 "powództwa {powod.pelne:dop} przeciwko {pozwany.pelne:cel} o zapłatę, na skutek apelacji "
                 "{pozwany.rodzaj:pozwanego|pozwanej} od wyroku Sądu Rejonowego z dnia {ctx.wyrok}, przy udziale pełnomocnika {powod.rodzaj:powoda|powódki} "
                 "{pelp.pelne:dop} oraz pełnomocnika {pozwany.rodzaj:pozwanego|pozwanej} {pelpoz.pelne:dop},")),
        sekcja("sentencja", "akapit",
               W("rejonowy", "I. zasądza od {pozwany.rodzaj:pozwanego|pozwanej} {pozwany.pelne:dop} na rzecz {powod.rodzaj:powoda|powódki} {powod.pelne:dop} kwotę "
                 "{ctx.zasadzona} wraz z odsetkami ustawowymi za opóźnienie od dnia {ctx.termin_platnosci} do dnia "
                 "zapłaty;"),
               W("rejonowy", "II. oddala powództwo w pozostałej części;"),
               W("rejonowy", "III. zasądza od {pozwany.rodzaj:pozwanego|pozwanej} {pozwany.pelne:dop} na rzecz {powod.rodzaj:powoda|powódki} {powod.pelne:dop} kwotę "
                 "{ctx.koszty_procesu} tytułem zwrotu kosztów procesu, w tym {ctx.koszty_zast} tytułem kosztów "
                 "zastępstwa procesowego;"),
               W("rejonowy", "IV. nakazuje pobrać od {pozwany.rodzaj:pozwanego|pozwanej} {pozwany.pelne:dop} na rzecz Skarbu Państwa kwotę "
                 "{ctx.oplata_nieuisz} tytułem nieuiszczonej części opłaty sądowej od pozwu."),
               W("apelacyjny", "I. oddala apelację;"),
               W("apelacyjny", "II. zasądza od {pozwany.rodzaj:pozwanego|pozwanej} {pozwany.pelne:dop} na rzecz {powod.rodzaj:powoda|powódki} {powod.pelne:dop} kwotę "
                 "{ctx.koszty_apel} tytułem zwrotu kosztów postępowania apelacyjnego.")),
        sekcja("uzasadnienie_tytul", "akapit", "UZASADNIENIE"),
        sekcja("stan_faktyczny", "akapit",
               W("rejonowy", "Pozwem z dnia {ctx.pozew} {powod.pelne} domaga się zasądzenia od {pozwany.pelne:dop} "
                 "kwoty {ctx.glowna} wraz z odsetkami ustawowymi za opóźnienie od dnia {ctx.termin_platnosci}, "
                 "wskazując, że świadczenie wynika z umowy zawartej przez strony i nie zostało spełnione w "
                 "terminie."),
               W("rejonowy", "W odpowiedzi na pozew {pozwany.pelne} wnosi o oddalenie powództwa w całości, "
                 "podnosząc zarzut częściowego wykonania umowy oraz zarzut potrącenia wzajemnej wierzytelności."),
               W("rejonowy", "Sąd ustalił następujący stan faktyczny. W dniu {ctx.umowa} strony zawarły umowę, na "
                 "podstawie której zobowiązano {powod.rodzaj:powoda|powódkę} do wykonania robót, a {pozwany.rodzaj:pozwanego|pozwaną} – do zapłaty "
                 "wynagrodzenia w terminie czternastu dni od odbioru. Odbiór nastąpił bez zastrzeżeń."),
               W("rejonowy", "Okoliczności te Sąd ustalił na podstawie dokumentów złożonych do akt, zeznań "
                 "świadka {swiadek.pelne:dop} oraz zeznań świadka {swiadek2.pelne:dop}, którym dał wiarę jako "
                 "spójnym i zgodnym z dokumentami. Zeznania te korespondują z opinią {biegly.rodzaj:biegłego|biegłej} "
                 "{biegly.pelne:dop}, którą Sąd uznał za rzetelną i w pełni przekonującą."),
               W("apelacyjny", "Wyrokiem z dnia {ctx.wyrok} Sąd Rejonowy zasądził od {pozwany.rodzaj:pozwanego|pozwanej} {pozwany.pelne:dop} "
                 "na rzecz {powod.rodzaj:powoda|powódki} {powod.pelne:dop} kwotę {ctx.zasadzona} wraz z odsetkami ustawowymi za "
                 "opóźnienie od dnia {ctx.termin_platnosci}, oddalił powództwo w pozostałej części i orzekł o "
                 "kosztach procesu."),
               W("apelacyjny", "Apelację wniesiono w dniu {ctx.apelacja}. Zarzucono w niej naruszenie art. 233 § 1 "
                 "Kodeksu postępowania cywilnego przez dowolną ocenę zeznań świadka {swiadek.pelne:dop} oraz "
                 "pominięcie opinii {biegly.rodzaj:biegłego|biegłej} {biegly.pelne:dop}, a także naruszenie art. 647 Kodeksu cywilnego.")),
        sekcja("ocena", "akapit",
               W("rejonowy", "Powództwo zasługiwało na uwzględnienie w przeważającej części. Podstawę roszczenia "
                 "stanowi art. 647 Kodeksu cywilnego, zgodnie z którym przyjmujący zamówienie zobowiązuje się do "
                 "wykonania oznaczonego dzieła, a zamawiający do odebrania dzieła i zapłaty umówionego "
                 "wynagrodzenia."),
               W("rejonowy", "Zgodnie z art. 6 k.c. ciężar udowodnienia faktu spoczywa na osobie, która z faktu "
                 "tego wywodzi skutki prawne, a zgodnie z art. 232 Kodeksu postępowania cywilnego strony są "
                 "obowiązane wskazywać dowody dla stwierdzenia faktów, z których wywodzą skutki prawne."),
               W("rejonowy", "Zarzut potrącenia okazał się chybiony, ponieważ wierzytelność przedstawiona do "
                 "potrącenia nie była wymagalna w chwili złożenia oświadczenia (art. 498 § 1 k.c.)."),
               W("rejonowy", "Roszczenie o odsetki wynika z art. 481 § 1 k.c. i podlegało uwzględnieniu od dnia "
                 "następnego po upływie terminu zapłaty."),
               W("apelacyjny", "Apelacja nie zasługuje na uwzględnienie. Sąd Okręgowy podziela ustalenia "
                 "faktyczne i ocenę prawną Sądu pierwszej instancji i przyjmuje je za własne (art. 382 k.p.c.)."),
               W("apelacyjny", "Sąd pierwszej instancji ocenił materiał dowodowy swobodnie, ale z zachowaniem "
                 "zasad logiki i doświadczenia życiowego (art. 233 § 1 k.p.c.); sama możliwość odmiennej "
                 "oceny nie wystarcza do skutecznego podważenia tej oceny w apelacji."),
               W("apelacyjny", "Zarzut naruszenia art. 647 k.c. jest chybiony, gdyż odbiór dzieła bez zastrzeżeń "
                 "nastąpił, a {pozwany.rodzaj:pozwany nie wykazał|pozwana nie wykazała} wad uzasadniających obniżenie wynagrodzenia.")),
        sekcja("cytaty", "akapit",
               "Podobne stanowisko zajął Sąd Najwyższy w wyroku z dnia {cytat1.data}, sygn. "
               "{cytat1.sygnatura} ({cytat1.sprawa}), przyjmując, że bezskuteczny upływ terminu zapłaty "
               "wywołuje skutek opóźnienia bez potrzeby wezwania.",
               "Zob. także wyrok Sądu Apelacyjnego z dnia {cytat2.data}, {cytat2.sygnatura} "
               "(w sprawie {cytat2.sprawa}), w którym wskazano, że przyjęcie dzieła bez zastrzeżeń nie wyłącza "
               "odpowiedzialności z tytułu rękojmi.",
               "Por. wyrok Sądu Okręgowego z dnia {cytat3.data}, {cytat3.sygnatura} (sprawa {cytat3.sprawa}) "
               "oraz powołane tam orzecznictwo.",
               min=2, max=3),
        sekcja("koszty", "akapit",
               W("rejonowy", "O kosztach procesu orzeczono na podstawie art. 100 zdanie drugie k.p.c., obciążając "
                 "{pozwany.rodzaj:pozwanego|pozwaną} całością kosztów, gdyż {powod.rodzaj:powód uległ|powódka uległa} tylko co do nieznacznej części żądania."),
               W("rejonowy", "O nieuiszczonej opłacie sądowej orzeczono na podstawie art. 113 ust. 1 ustawy z dnia "
                 "28 lipca 2005 r. o kosztach sądowych w sprawach cywilnych."),
               W("apelacyjny", "O kosztach postępowania apelacyjnego orzeczono na podstawie art. 98 § 1 i 3 k.p.c. "
                 "w zw. z art. 391 § 1 k.p.c., zgodnie z zasadą odpowiedzialności za wynik postępowania.")),
        sekcja("pouczenie", "akapit",
               W("rejonowy", "Od niniejszego wyroku przysługuje apelacja do Sądu Okręgowego w terminie dwóch "
                 "tygodni od doręczenia stronie wyroku z uzasadnieniem, za pośrednictwem sądu, który wydał wyrok."),
               W("rejonowy", "Wyrok jest wykonalny z urzędu w części dotyczącej kosztów, o ile nie został "
                 "zaskarżony."),
               W("apelacyjny", "Wyrok jest prawomocny. Skarga kasacyjna do Sądu Najwyższego przysługuje w terminie "
                 "dwóch miesięcy od doręczenia wyroku z uzasadnieniem, jeżeli wartość przedmiotu zaskarżenia "
                 "wynosi co najmniej 50 000 zł (art. 398^2 k.p.c.).")),
        sekcja("podpisy", "podpis",
               W("rejonowy", "{sedzia1.pelne}"),
               W("apelacyjny", "{sedzia1.pelne}"), W("apelacyjny", "{sedzia2.pelne}"),
               W("apelacyjny", "{sedzia3.pelne}")),
        sekcja("stopka", "stopka", "{sad.nazwa} | sygn. akt {sad.sygnatura} | Strona 1"),
    ],
    metadane={"subject": "Wyrok w sprawie o zapłatę", "case": "{sad.sygnatura}"},
)
