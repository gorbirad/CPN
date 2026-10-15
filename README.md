<p align="center">
  <img src="logo.png" alt="CPN logo" width="200">
</p>

# CPN – maksymalne ceny detaliczne paliw

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/gorbirad/CPN/actions/workflows/validate.yaml/badge.svg)](https://github.com/gorbirad/CPN/actions/workflows/validate.yaml)
[![Autor](https://img.shields.io/badge/autor-gorbirad-blue?logo=github)](https://github.com/gorbirad)

Integracja Home Assistant. Co 15 minut sprawdza stronę
[gov.pl/web/energia/wiadomosci](https://www.gov.pl/web/energia/wiadomosci), znajduje najnowszy
artykuł „Maksymalna cena detaliczna paliw…” i tworzy sensory (PLN/l):

| Encja | Opis |
|-------|------|
| `sensor.cpn_pb95` | Benzyna 95 |
| `sensor.cpn_pb98` | Benzyna 98 |
| `sensor.cpn_on` | Olej napędowy |

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

## Przykładowa karta

Karta pokazuje cenę benzyny 95, podświetla się na żółto, gdy cena zmieniła się w ciągu ostatniej godziny,
i wyświetla czas ostatniej zmiany.

**Wymagania:** karta korzysta z [card-mod](https://github.com/thomasloven/lovelace-card-mod)
(instalacja przez HACS → Frontend → wyszukaj „card-mod”, a następnie odśwież przeglądarkę).
Bez card-mod karta wyświetli się, ale bez podświetlenia i dodatkowego opisu.

```yaml
type: entity
entity: sensor.cpn_pb95
name: Benzyna 95
icon: mdi:gas-station
card_mod:
  style: |
    ha-card {
      {% set last = states.sensor.cpn_pb95.last_changed %}
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
      content: "Ostatnia zmiana: {{ states.sensor.cpn_pb95.last_changed.strftime('%H:%M:%S') }}";
      display: block;
      font-size: 12px;
      color: var(--secondary-text-color);
      margin-top: 4px;
    }
```

Aby uzyskać kartę dla innego paliwa, zamień `sensor.cpn_pb95` na `sensor.cpn_pb98` lub `sensor.cpn_on`.

Wykres z historią cen (7 dni):

```yaml
type: statistics-graph
entities:
  - sensor.cpn_pb95
  - sensor.cpn_pb98
  - sensor.cpn_on
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
