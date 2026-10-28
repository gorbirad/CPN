# Changelog

Historia zmian integracji CPN. Opisy opublikowanych wydań w tym pliku są
zestawieniem opisów z GitHub Releases; same wydania pozostają dostępne na
[stronie Releases](https://github.com/gorbirad/CPN/releases).

## [1.1.5] - Unreleased

- Adaptacyjne odświeżanie: co 5 minut w oknie 11:00–17:00 (Europe/Warsaw), dopóki feed nie zawiera ceny na przyszły dzień; potem TTL jednej godziny.
- Dodano ręczne uruchamianie workflow (`workflow_dispatch`), także dla zewnętrznego harmonogramu.
- Harmonogram scrapera: co 10 minut od 08:04 do 14:54 UTC (PR #6).

## [1.1.4] - 2026-10-28

- Rozszerzono harmonogram scrapera do okna 12:00–14:00 Europe/Warsaw, co 10 minut (PR #5).
- Zaktualizowano dokumentację PL/EN o harmonogram UTC, czas letni/zimowy i opóźnione uruchomienia.

## [1.1.3] - 2026-10-27

- Naprawiono pomijanie opóźnionych uruchomień scrapera: usunięto sztywne ograniczenie do okna 12:00–13:00 Europe/Warsaw. Opóźniony przebieg nadal pobiera i publikuje aktualne ceny, a blokada w `state.json` dalej zapobiega zbędnym zapytaniom (PR #4).

## [1.1.2]

- Przy pierwszym imporcie historii używane są ceny z ostatnich 7 dni, a gdy ich brak — z 4 najnowszych artykułów.
- Migracja ponawia import historii na istniejących wpisach HA po udostępnieniu poprawnego feedu JSON.
- Nieudany import (brak punktów historycznych) nie jest oznaczany jako zakończony.
- Po aktualizacji integracji pierwsze pobranie feedu omija cache, aby jednorazowo sprawdzić aktualne dane.

## [1.1.1] - 2026-10-23

## [1.1.0] - 2026-10-23

- Dodano centralny scraper GitHub Actions i publikację cen przez GitHub Pages.
- Integracja Home Assistant pobiera wyłącznie `news.json`; bezpośrednie odpytywanie gov.pl usunięto.
- Dodano jednogodzinny, trwały cache oraz walidację danych i ponawianie żądań z backoffem.
- Dodano harmonogram 12:00–13:00 czasu polskiego i blokadę dalszego scrapowania po wykryciu zmian.
- Scraper pomija zapis i commity, jeśli semantyczne dane cenowe się nie zmieniły.
- README jest dostępne po polsku i angielsku z linkami wyboru języka na początku.

## [1.0.5] - 2026-10-16

### Nowe
- Sensory z ceną obowiązującą dziś (`*_obecna`) z atrybutami różnicy względem nowej i poprzedniej ceny oraz dat obowiązywania.
- Automatyczne przełączanie ceny obecnej o północy.
- Przykładowa karta Markdown z obecną ceną, nową ceną i zmianą; karta nie wymaga card-mod.

## [1.0.4] - 2026-10-16

### Poprawki
- Poprawne rozpoznawanie dat dla cen obowiązujących kilka dni, np. „w dniach 17-19 października”; jako datę obowiązywania przyjmuje pierwszy dzień zakresu.
- Obsługa zakresów obejmujących dwa miesiące, np. 31 października – 2 listopada.
- Import historii pomija artykuły z datą z przyszłości.
- README opisuje przybliżoną godzinę publikacji cen oraz interpretację dat dla zakresów.

## [1.0.3] - 2026-10-16

### Nowe
- Odświeżanie co 15 minut w minutach :05, :20, :35 i :50.
- Atrybut `valid_from` w sensorach paliw oraz sensor z datą obowiązywania.
- Przykładowa karta z informacją „Obowiązuje od”.

### Zmiany
- Usunięto nieużywane `suggested_object_id`.
- Rozszerzono README o przykładową kartę, wykres historii, wymaganie card-mod i poprawione nazwy encji.

## [1.0.2] - 2026-10-15

- Dokumentacja: przykładowa karta (wymaga card-mod) i poprawione nazwy encji.
- Usunięto nieużywane `suggested_object_id`.

## [1.0.1] - 2026-10-15

- Import historii cen (7 dni lub 3 ostatnie wpisy) do statystyk przy pierwszej konfiguracji.
- Dodano ikonę i logo integracji.
- Dodano licencję MIT i poprawiono manifest pod walidację hassfest/HACS.
- Rozszerzono README o instalację ręczną i strukturę projektu.

## [1.0.0] - 2026-10-15

- Pierwsze wydanie integracji CPN dla Home Assistant.
- Pobieranie maksymalnych cen paliw ze strony wiadomości Ministerstwa Energii.
- Sensory dla benzyny 95, benzyny 98 i oleju napędowego oraz konfiguracja przez interfejs Home Assistant.
- Dodano workflow walidacji HACS i hassfest.
