<p align="center">
  <img src="logo.png" alt="CPN logo" width="200">
</p>

# CPN – maksymalne ceny detaliczne paliw

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/gorbirad/CPN/actions/workflows/validate.yaml/badge.svg)](https://github.com/gorbirad/CPN/actions/workflows/validate.yaml)
[![Autor](https://img.shields.io/badge/autor-gorbirad-blue?logo=github)](https://github.com/gorbirad)
[![Sponsor](https://img.shields.io/badge/Sponsor-gorbirad-ea4aaa?logo=githubsponsors&logoColor=white)](https://github.com/sponsors/gorbirad)
[![Latest release](https://img.shields.io/github/v/release/gorbirad/CPN)](https://github.com/gorbirad/CPN/releases/latest)

Integracja Home Assistant. Co 15 minut (:05, :20, :35, :50) sprawdza stronę
[gov.pl/web/energia/wiadomosci](https://www.gov.pl/web/energia/wiadomosci), znajduje najnowszy
artykuł „Maksymalna cena detaliczna paliw…” i tworzy sensory (PLN/l):

Pełna historia zmian znajduje się w [CHANGELOG.md](CHANGELOG.md); opisy wydań są też na
[GitHub Releases](https://github.com/gorbirad/CPN/releases).

| Encja | Opis |
|-------|------|
| `sensor.benzyna_95` | Benzyna 95 |
| `sensor.benzyna_95_obecna` | Cena benzyny 95 obowiązująca **dziś** |
| `sensor.benzyna_98` | Benzyna 98 |
| `sensor.benzyna_98_obecna` | Cena benzyny 98 obowiązująca **dziś** |
| `sensor.olej_napedowy` | Olej napędowy |
| `sensor.olej_napedowy_obecna` | Cena oleju napędowego obowiązująca **dziś** |
| `sensor.cena_obowiazuje_od` | Data, od której obowiązują aktualne ceny |

Sensory „obecna” mają atrybuty: `valid_from`, `next_price`, `next_valid_from`, `change_next` (nowa − obecna),
`previous_price`, `change_previous` (obecna − poprzednia). O północy przełączają się same na cenę obowiązującą
od danego dnia, a pozostałe sensory (`benzyna_95` itd.) pokazują zawsze **najnowszą opublikowaną** cenę
(często już na jutro).

Każdy sensor paliwa ma też atrybut `valid_from` (data obowiązywania, `RRRR-MM-DD`). Data pochodzi z adresu
artykułu; dla cen obowiązujących przez kilka dni (np. weekend „17-19 października”) jest to pierwszy dzień.
Ministerstwo publikuje ceny zwykle ok. godz. 12:00–12:30, więc nowa cena może pojawić się z takim opóźnieniem.

Atrybuty każdego sensora: `title`, `url`, `summary` (artykuł, z którego pochodzą ceny).

### Historia cen

Przy pierwszym dodaniu integracji pobierane są ceny z ostatnich 7 dni (a jeśli ich brak – z 3 ostatnich
artykułów) i zapisywane jako statystyki długoterminowe (jeden punkt na dobę, od 00:00). Dzięki temu
od razu można zobaczyć zmiany na wykresie, np. kartą `statistics-graph`. Dane pochodzą z pierwszej strony
listy wiadomości gov.pl.

## Instalacja

### HACS (zalecana)

1. HACS → menu ⋮ → **Custom repositories**.
2. Dodaj `https://github.com/gorbirad/CPN` jako kategorię **Integration**.
3. Wyszukaj **CPN**, kliknij **Download**.
4. Zrestartuj Home Assistant.

### Ręczna

1. Pobierz najnowsze wydanie z [Releases](https://github.com/gorbirad/CPN/releases) (lub sklonuj repozytorium).
2. Skopiuj katalog `custom_components/cpn` do katalogu `custom_components` w konfiguracji HA
   (tam, gdzie leży `configuration.yaml`). Jeśli `custom_components` nie istnieje, utwórz go.
3. Efekt powinien wyglądać tak:

   ```text
   config/
   ├── configuration.yaml
   └── custom_components/
       └── cpn/
           ├── __init__.py
           ├── manifest.json
           └── ...
   ```

4. Zrestartuj Home Assistant.

## Konfiguracja

1. **Ustawienia → Urządzenia i usługi → Dodaj integrację**.
2. Wyszukaj **CPN** i zatwierdź.

## Przykładowe karty (card-mod)

Trzy podobne karty dla benzyny 95: **nowa cena**, **cena obecna** i **różnica**. Każda jest też w osobnym
pliku w repozytorium. Dla innych paliw zamień `benzyna_95` na `benzyna_98` lub `olej_napedowy`.

### Karta 1: nowa (najnowsza opublikowana) cena

Plik: [example_card.yaml](example_card.yaml). Podświetla się na żółto, gdy cena zmieniła się w ciągu
ostatniej godziny, i wyświetla datę, od której cena obowiązuje.

**Wymagania:** karta korzysta z [card-mod](https://github.com/thomasloven/lovelace-card-mod)
(instalacja przez HACS → Frontend → wyszukaj „card-mod”, a następnie odśwież przeglądarkę).
Bez card-mod karta wyświetli się, ale bez podświetlenia i dodatkowego opisu.

```yaml
type: entity
entity: sensor.benzyna_95
name: Benzyna 95
icon: mdi:gas-station
card_mod:
  style: |
    ha-card {
      {% set last = states.sensor.benzyna_95.last_changed %}
      {% if (now() - last).total_seconds() < 3600 %}
        background: rgba(255, 200, 0, 0.3);
        border-radius: 12px;
      {% endif %}
      padding-bottom: 12px;
    }
    .value {
      position: relative;
    }
    .value:after {
      content: "Obowiązuje od: {{ as_datetime(state_attr('sensor.benzyna_95', 'valid_from')).strftime('%d.%m.%Y') }}";
      display: block;
      font-size: 12px;
      color: var(--secondary-text-color);
      margin-top: 4px;
    }
```

Aby uzyskać kartę dla innego paliwa, zamień `sensor.benzyna_95` na `sensor.benzyna_98` lub `sensor.olej_napedowy`.

### Karta 2: cena obecna (obowiązująca dziś)

Plik: [example_card_current_price.yaml](example_card_current_price.yaml).

```yaml
type: entity
entity: sensor.benzyna_95_obecna
name: Benzyna 95 – obecna
icon: mdi:gas-station
card_mod:
  style: |
    ha-card {
      padding-bottom: 12px;
    }

    .value {
      position: relative;
    }

    .value:after {
      content: "Obowiązuje od: {{ as_datetime(state_attr('sensor.benzyna_95_obecna', 'valid_from')).strftime('%d.%m.%Y') }}";
      display: block;
      font-size: 12px;
      color: var(--secondary-text-color);
      margin-top: 4px;
    }
```

### Karta 3: różnica cen (nowa − obecna)

Plik: [example_card_diff.yaml](example_card_diff.yaml). Zielone tło oznacza obniżkę, czerwone podwyżkę;
pod wartością widać nową cenę i datę od kiedy obowiązuje. Gdy nowa cena nie jest jeszcze znana, karta
pokazuje „unknown”.

```yaml
type: entity
entity: sensor.benzyna_95_obecna
attribute: change_next
name: Benzyna 95 – zmiana (nowa − obecna)
unit: zł
icon: mdi:swap-vertical
card_mod:
  style: |
    ha-card {
      {% set d = state_attr('sensor.benzyna_95_obecna', 'change_next') %}
      {% if d is not none and d | float(0) < 0 %}
        background: rgba(76, 175, 80, 0.25);
      {% elif d is not none and d | float(0) > 0 %}
        background: rgba(244, 67, 54, 0.25);
      {% endif %}
      border-radius: 12px;
      padding-bottom: 12px;
    }

    .value:after {
      content: "{{ state_attr('sensor.benzyna_95_obecna', 'next_price') }} zł od {{ as_datetime(state_attr('sensor.benzyna_95_obecna', 'next_valid_from')).strftime('%d.%m.%Y') if state_attr('sensor.benzyna_95_obecna', 'next_valid_from') else '–' }}";
      display: block;
      font-size: 12px;
      color: var(--secondary-text-color);
      margin-top: 4px;
    }
```

### Karta zbiorcza (Markdown, bez card-mod)

Jedna karta Markdown (nie wymaga card-mod) z tabelą: cena obecna, nowa (od jutra) i zmiana. Plik:
[example_card_current.yaml](example_card_current.yaml).

```yaml
type: markdown
title: Ceny paliw (max)
content: |
  {% set fuels = [('Benzyna 95', 'sensor.benzyna_95_obecna'),
                  ('Benzyna 98', 'sensor.benzyna_98_obecna'),
                  ('Olej napędowy', 'sensor.olej_napedowy_obecna')] %}
  {% set e = fuels[0][1] %}
  Obecna cena od **{{ state_attr(e, 'valid_from') }}**
  {%- if state_attr(e, 'next_valid_from') %}, nowa od **{{ state_attr(e, 'next_valid_from') }}**{% endif %}

  | Paliwo | Obecnie | Nowa | Zmiana |
  |---|---|---|---|
  {% for name, ent in fuels -%}
  {% set now_p = states(ent) | float(none) -%}
  {% set nxt = state_attr(ent, 'next_price') -%}
  {% set d = state_attr(ent, 'change_next') -%}
  {% set dp = state_attr(ent, 'change_previous') -%}
  | {{ name }} | **{{ '%.2f' | format(now_p) if now_p is not none else '–' }} zł** | {{ '%.2f' | format(nxt) ~ ' zł' if nxt is not none else '–' }} | {% if d is not none %}{{ '🔺 +' if d > 0 else '🔻 ' if d < 0 else '' }}{{ '%.2f' | format(d) }} zł (od jutra){% elif dp is not none %}{{ '🔺 +' if dp > 0 else '🔻 ' if dp < 0 else '' }}{{ '%.2f' | format(dp) }} zł (vs poprzednia){% else %}–{% endif %} |
  {% endfor %}
```

Wykres z historią cen (7 dni):

```yaml
type: statistics-graph
entities:
  - sensor.benzyna_95
  - sensor.benzyna_98
  - sensor.olej_napedowy
stat_types:
  - mean
days_to_show: 7
period: day
```

## Struktura projektu

```text
CPN/
├── .github/
│   └── workflows/
│       └── validate.yaml        # walidacja HACS + hassfest
├── custom_components/
│   └── cpn/
│       ├── __init__.py          # setup/unload wpisu konfiguracji
│       ├── config_flow.py       # prosty config flow (bez parametrów)
│       ├── const.py             # stałe: URL, interwał, lista paliw
│       ├── coordinator.py       # pobieranie i parsowanie strony gov.pl
│       ├── history.py           # import historii cen (statystyki)
│       ├── manifest.json        # metadane integracji
│       ├── sensor.py            # sensory cen paliw
│       ├── strings.json
│       └── translations/
│           ├── en.json
│           └── pl.json
├── .gitignore
├── hacs.json                    # metadane HACS
└── README.md
```
