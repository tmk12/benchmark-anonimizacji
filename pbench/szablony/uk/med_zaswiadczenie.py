"""Медична довідка про стан здоров’я для подання до суду (підтвердження поважних причин неявки)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="uk", typ="med_zaswiadczenie", profil="interna", znacz_encje=True,
    role={"placowka": "placowka", "pacjent": "pacjent", "lekarz": "lekarz", "sprawa": "sprawa", "sad": "sad"},
    sekcje=[
        sekcja("naglowek", "naglowek",
               "{placowka.nazwa}",
               "{placowka.adres} | тел. {placowka.telefon} | код ЄДРПОУ {placowka.edrpou}"),
        sekcja("miejscowosc", "akapit", "м. {placowka.miasto}, {ctx.zas_wystaw}"),
        sekcja("tytul", "akapit", "МЕДИЧНА ДОВІДКА про стан здоров’я"),
        sekcja("tresc", "akapit",
               "Видана {pacjent.pelne:dav}, дата народження: {pacjent.data_ur}, РНОКПП {pacjent.rnokpp}, місце "
               "проживання: {pacjent.adres}, про те, що {pacjent.rodzaj:він|вона} перебуває на обліку в закладі "
               "охорони здоров’я.",
               "Клінічний діагноз: {pacjent.diagnoza}. Супутні захворювання: {pacjent.diagnoza2}.",
               "Під час огляду {ctx.zas_od} у стані здоров’я {pacjent.pelne:rod} виявлено загострення основного "
               "захворювання, що потребує медикаментозного лікування, зокрема: {pacjent.lek} та {pacjent.lek2}. "
               "Рекомендовано обмеження фізичних навантажень з {ctx.zas_od} по {ctx.zas_do}."),
        sekcja("zdolnosc", "akapit",
               "За станом здоров’я {pacjent.rodzaj:пацієнт не може|пацієнтка не може} брати участь у заходах, що "
               "потребують тривалих поїздок або перебування в положенні сидячи понад дві години, зокрема в "
               "судовому засіданні, призначеному на {ctx.rozprawa}.",
               "Довідку видано на прохання {pacjent.pelne:rod} для подання до суду у справі № {sprawa.sygnatura} "
               "як підтвердження поважних причин неявки; суд, у провадженні якого перебуває справа: {sad.nazwa}.",
               "Рекомендовано повторний огляд після закінчення зазначеного періоду, а в разі погіршення стану — "
               "негайно звернутися до сімейного лікаря або у відділення невідкладної допомоги."),
        sekcja("pouczenie", "akapit",
               "Довідку видано на підставі огляду, проведеного {ctx.zas_wystaw}, та медичної документації закладу. "
               "Видача завідомо неправдивого документа тягне відповідальність, передбачену Кримінальним кодексом "
               "України.",
               "Ця довідка не є медичним висновком про тимчасову непрацездатність (листком непрацездатності).",
               "Довідка містить відомості про стан здоров’я, що становлять лікарську таємницю, і видається "
               "на руки {pacjent.rodzaj:пацієнту або уповноваженій ним особі|пацієнтці або уповноваженій нею особі}."),
        sekcja("lekarz", "akapit",
               "{lekarz.rodzaj:Лікар|Лікарка}: {lekarz.pelne}, {lekarz.rodzaj:лікар-терапевт|лікарка-терапевтка}",
               "М. П."),
        sekcja("podpis", "podpis", "{lekarz.pelne_im}"),
        sekcja("stopka", "stopka", "{placowka.nazwa} | {placowka.adres} | {placowka.email}"),
    ],
    metadane={"author": "{lekarz.pelne}", "subject": "Медична довідка"},
)
