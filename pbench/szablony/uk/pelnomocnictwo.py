"""Довіреність фізичної особи на представництво в суді з правом передоручення, з нотаріальним посвідченням (обов’язковим)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="uk", typ="pelnomocnictwo", dorosli=True, znacz_encje=True,
    role={"mocodawca": "osoba", "pelnomocnik": "osoba", "substytut": "osoba", "notariusz": "osoba",
          "sprawa": "sprawa", "przeciwnik": "osoba", "sad": "sad"},
    sekcje=[
        sekcja("miejscowosc", "akapit", "м. {mocodawca.miasto}, {ctx.po_pozwie_slownie}"),
        sekcja("tytul", "akapit", "ДОВІРЕНІСТЬ"),
        sekcja("mocodawca", "akapit",
               "Я, {mocodawca.pelne}, дата народження: {mocodawca.data_ur}, реєстраційний номер облікової картки "
               "платника податків (РНОКПП) {mocodawca.rnokpp}, документ, що посвідчує особу, — ID-картка "
               "№ {mocodawca.dowod}, {mocodawca.rodzaj:зареєстрований|зареєстрована} за адресою: "
               "{mocodawca.adres}, тел. {mocodawca.telefon}, цією довіреністю уповноважую:"),
        sekcja("pelnomocnik", "akapit",
               "{pelnomocnik.pelne:zna}, РНОКПП {pelnomocnik.rnokpp}, адреса електронної пошти: "
               "{pelnomocnik.email},"),
        sekcja("zakres", "akapit",
               "бути моїм представником у справі № {sprawa.sygnatura} за моїм позовом до {przeciwnik.pelne:rod}, "
               "що розглядається судом першої інстанції ({sad.nazwa}), а також в апеляційному та касаційному провадженні й на стадії виконання судового "
               "рішення;",
               "з правом підписувати й подавати позовні заяви, відповіді на відзиви, апеляційні та касаційні скарги, "
               "заяви про забезпечення позову, заяви про перегляд судових рішень; укладати мирову угоду; "
               "відмовлятися від позову, змінювати предмет або підстави позову;",
               "отримувати від судів та інших органів копії процесуальних документів, а також кошти, присуджені "
               "на мою користь, у сумі до {ctx.limit_odb} на мій рахунок {mocodawca.rachunek};",
               "передоручати повноваження за цією довіреністю, зокрема {substytut.pelne:dav}, у порядку, "
               "встановленому законом;",
               "отримувати від державних органів, банків і страхових компаній документи, що стосуються мене, "
               "в обсязі, необхідному для ведення справи."),
        sekcja("zgoda", "akapit",
               "Я надаю згоду на обробку моїх персональних даних представником та особами, яким представник "
               "передоручить виконання окремих дій, в обсязі, необхідному для ведення справи, відповідно до Закону "
               "України «Про захист персональних даних».",
               "Довіреність видано строком на три роки з правом передоручення. Скасування довіреності "
               "здійснюється в письмовій формі з повідомленням представника та суду."),
        sekcja("podpis_opis", "akapit", "Підпис {mocodawca.rodzaj:довірителя|довірительки}: ____________ {mocodawca.skr_pib}"),
        sekcja("podpis", "podpis", "{mocodawca.pelne_im}"),
        sekcja("poswiadczenie", "akapit",
               "Цю довіреність посвідчено мною, {notariusz.pelne:oru}, приватним нотаріусом. Довіреність підписано "
               "{mocodawca.rodzaj:довірителем|довірителькою} у моїй присутності. Особу {mocodawca.rodzaj:довірителя|довірительки} встановлено на підставі "
               "ID-картки № {mocodawca.dowod}, {mocodawca.rodzaj:його|її} дієздатність перевірено. Зареєстровано в "
               "реєстрі за № 1204.",
               "Приватний нотаріус ____________ {notariusz.skr_pib}"),
        sekcja("stopka", "stopka", "Довіреність | {mocodawca.pib_skr} | {pelnomocnik.email}"),
        sekcja("oplata", "przypis",
               "За посвідчення довіреності стягнуто плату відповідно до статті 31 Закону України «Про нотаріат»."),
    ],
    metadane={"author": "{pelnomocnik.pelne}", "subject": "Довіреність на представництво в суді"},
)
