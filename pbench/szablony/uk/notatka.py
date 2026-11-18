"""Службова записка начальника юридичного відділу директору про порушення договору контрагентом."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="uk", typ="notatka", dorosli=True, znacz_encje=True,
    role={"firma": "spolka", "dyrektor": "osoba", "autor": "osoba", "kolega": "osoba", "kontrahent": "spolka",
          "przeciwnik": "osoba", "sad": "sad_gosp"},
    sekcje=[
        sekcja("naglowek", "naglowek",
               "{dyrektor.rodzaj:Директору|Директорці} {firma.nazwa}",
               "{dyrektor.pelne:dav}"),
        sekcja("dane", "akapit",
               "СЛУЖБОВА ЗАПИСКА",
               "від {ctx.termin_wezwania}",
               "щодо порушення контрагентом {kontrahent.nazwa} умов договору поставки"),
        sekcja("autor", "akapit",
               "Від: {autor.rodzaj:начальника|начальниці} юридичного відділу {autor.pelne:rod}, тел. {autor.telefon}, електронна пошта: "
               "{autor.email}."),
        sekcja("stan", "akapit",
               "1. Договір поставки з контрагентом — {kontrahent.nazwa} (код ЄДРПОУ {kontrahent.edrpou}, "
               "місцезнаходження: {kontrahent.adres}) — укладено {ctx.umowa}. Строк оплати поставленого товару "
               "сплив {ctx.termin_platnosci}, однак оплату в повному обсязі не здійснено.",
               "2. Претензію про сплату боргу надіслано контрагентові {ctx.wezwanie}; встановлений у ній строк "
               "для відповіді закінчився {ctx.termin_wezwania}, відповіді не надійшло.",
               "3. Сума основного боргу становить {ctx.glowna}; нараховано пеню, інфляційні втрати та три проценти річних у розмірі "
               "{ctx.odsetki}; витрати на досудове врегулювання — {ctx.koszty_wind}. Загальна вимога до "
               "контрагента — {ctx.razem_wez}.",
               "4. Контрагента представляє {przeciwnik.rodzaj:директор|директорка} {przeciwnik.pelne}, контактний телефон {przeciwnik.telefon}."),
        sekcja("propozycje", "akapit",
               "Пропоную: надіслати контрагентові остаточну вимогу з попередженням про звернення до суду, а в разі "
               "відсутності оплати до {ctx.pozew} подати до суду ({sad.nazwa}) позов про стягнення основного боргу, "
               "пені, інфляційних втрат і трьох процентів річних (частина друга статті 625 Цивільного кодексу "
               "України).",
               "Для підготовки позову прошу доручити бухгалтерії надати акти звіряння взаєморозрахунків, "
               "видаткові накладні та платіжні інструкції; копію реєстру переписки підготує {kolega.pelne}.",
               "{autor.rodzaj:Відповідальним|Відповідальною} за ведення справи пропоную призначити {autor.pelne:zna}."),
        sekcja("zakonczenie", "akapit",
               "Прошу погодити запропонований порядок дій.",
               "Додатки: копія договору поставки, копія претензії."),
        sekcja("podpisy", "akapit", "{autor.rodzaj:Начальник|Начальниця} юридичного відділу ____________ {autor.skr_pib}"),
        sekcja("podpis", "podpis", "{autor.pelne_im}"),
        sekcja("stopka", "stopka", "{firma.nazwa} | {firma.adres} | {firma.email}"),
    ],
    metadane={"author": "{autor.pelne}", "subject": "Службова записка щодо порушення договору"},
)
