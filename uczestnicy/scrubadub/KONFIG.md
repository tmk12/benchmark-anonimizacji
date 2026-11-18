# scrubadub

**scrubadub** (LeapBeyond, <https://github.com/LeapBeyond/scrubadub>) – biblioteka usuwania danych osobowych z tekstu.
Grupa B (bez kalibracji), punkt odniesienia **„same regexy”**. Poziom: tylko **tekst**.

## Wersje (przypięte, `uv.lock` w repo)

| Składnik | Wersja | Licencja |
|---|---|---|
| scrubadub | 2.0.1 (ostatnie wydanie, 2023-09-01; repozytorium niezarchiwizowane, bez zmian od tego dnia) | Apache-2.0 (plik `LICENSE` w pakiecie i licencja repozytorium; pole `License: MIT` w metadanych PyPI jest sprzeczne z plikiem – rozstrzyga `LICENSE`) |
| phonenumbers / python-stdnum / faker / dateparser / textblob | 9.0.42 / 2.2 / 40.44.0 / 1.4.3 / 0.15.3 | Apache-2.0 / LGPL-2.1+ / MIT / BSD-3 / MIT |

Bez modeli – nic do pobierania do `vendor/`.

## Konfiguracja – domyślna autorów

Dokumentacja (<https://scrubadub.readthedocs.io/en/stable/usage.html>, „Localization”): `scrubadub.Scrubber(locale=…)` ładuje
wszystkie detektory z `autoload = True` obsługujące locale; locale dokumentu wskazuje integrator. Locale wg języka dokumentu:
pl → `pl_PL`, en → **`en_US`** (domyślne locale `Scrubber()`; korpus EN miesza realia USA i Wielkiej Brytanii, a detektory `en_GB`
zastąpiłyby SSN numerami brytyjskimi), es → `es_ES`, de → `de_DE`, fr → `fr_FR`.

Detektory załadowane (lista w `wersje`, pole `detektory:<język>`):

| Locale | Detektory |
|---|---|
| wszystkie | `credential` (login/hasło po słowach-kluczach), `credit_card`, `email`, `phone` (`phonenumbers`, region z locale), `twitter`, `url` |
| `en_US` | + `social_security_number` |

**Ograniczenie narzędzia (nie nadmiar deklaracji):** słowa-klucze detektora `credential` (username/login/password/pw) są wyłącznie
angielskie, więc w es/de/fr/pl wykrywa on loginy i hasła tylko przy angielskich etykietach w tekście; `etykiety.json` deklaruje go
w każdym języku, bo komponent jest uruchamiany w każdym locale.

Detektory nazwisk, adresów i organizacji (`spacy`, `stanford`, `text_blob`, `address`, `spacy_entity`…) **nie** są ładowane domyślnie
(wymagają dodatkowych pakietów i jawnego dodania) – zgodnie z rolą „same regexy” zostają wyłączone. Wykrycia: `iter_filth(tekst)`;
`MergedFilth` (nakładające się wykrycia różnych detektorów) rozbijamy na składowe z własnymi zakresami. Filth nie ma pewności –
`wynik` = 1.0 (próg nie ma zastosowania). Bez okien (wzorce na całym tekście).

**Zaobserwowane zachowanie narzędzia (bez poprawek):** wzorzec e-maila przyjmuje zapis zaciemniony „x at y dot z”, więc w zdaniu
„John Smith at john.smith@example.com” wykrywa „Smith at john.smith” zamiast adresu. Nie poprawiamy tego – to zachowanie wydania.

## Etykiety → kategorie gold (`etykiety.json`)

email → EMAIL; url → URL; phone → TELEFON; credit_card → KARTA; credential → LOGIN, SEKRET; twitter → LOGIN;
social_security_number → SSN (tylko en – detektor jest tylko w `en_US`).

## Języki

Uruchamiany na 5 językach (R37). Oficjalnie: **en** – dokumentacja „Localization” wymienia detektory krajowe tylko dla `en_GB`
i `en_US`; detektory ogólne (e-mail, URL, telefon) działają w każdym locale.
