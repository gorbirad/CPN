<p align="center">
  <img src="logo.png" alt="CPN logo" width="200">
</p>

[PL](README.pl.md) | [**EN**](README.md)

# CPN — Maximum Retail Fuel Prices

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/gorbirad/CPN/actions/workflows/validate.yaml/badge.svg)](https://github.com/gorbirad/CPN/actions/workflows/validate.yaml)
[![Author](https://img.shields.io/badge/author-gorbirad-blue?logo=github)](https://github.com/gorbirad)
[![Sponsor](https://img.shields.io/badge/Sponsor-gorbirad-ea4aaa?logo=githubsponsors&logoColor=white)](https://github.com/sponsors/gorbirad)
[![Latest release](https://img.shields.io/github/v/release/gorbirad/CPN)](https://github.com/gorbirad/CPN/releases/latest)

Home Assistant integration for Poland's maximum retail fuel prices (PLN/l). A central GitHub Actions
scraper publishes data through GitHub Pages. Home Assistant instances only download the JSON feed;
they never connect directly to gov.pl.

The full change history is in [CHANGELOG.md](CHANGELOG.md); published release notes are also available
on [GitHub Releases](https://github.com/gorbirad/CPN/releases).

## Architecture

```text
gov.pl → GitHub Actions (scraper) → news.json → GitHub Pages → CPN integrations in Home Assistant
```

One central job checks the gov.pl news page during the price-publication window. When it finds new
price data, it publishes JSON. Home Assistant does not request the gov.pl page.

### Public JSON endpoint

`https://gorbirad.github.io/CPN/news.json`

The file contains `lastUpdate` (time of the latest data change in UTC) and `articles`. Each article
has `title`, `url`, `date` (ISO `YYYY-MM-DD` or `null`), `summary`, and `prices` (`pb95`, `pb98`, `on`).
Example:

```json
{
  "lastUpdate": "2026-10-23T10:40:00Z",
  "articles": [
    {
      "title": "Maximum retail fuel prices effective...",
      "url": "https://www.gov.pl/web/energia/maksymalna-cena-detaliczna-paliw-...",
      "date": "2026-10-24",
      "summary": "Benzyna 95 - 6,51 zł/l, benzyna 98 - 7,21 zł/l, olej napędowy - 7,99 zł/l.",
      "prices": { "pb95": 6.51, "pb98": 7.21, "on": 7.99 }
    }
  ]
}
```

### GitHub Actions and GitHub Pages

The `.github/workflows/publish-news.yaml` workflow fetches the source page, parses articles, and
publishes `news.json` to GitHub Pages. Before its first run, enable Pages in the repository:
**Settings → Pages → Build and deployment → Source: GitHub Actions**. The workflow requires
`contents: write`, `pages: write`, and `id-token: write` permissions. The endpoint may return 404
until the first successful publication.

GitHub Actions cron uses UTC and does not support time zones or daylight-saving changes. The schedule
runs at minutes 04, 14, 24, 34, 44, and 54 of UTC hours 08–14 (08:04–14:54 UTC). In `Europe/Warsaw`,
this corresponds to 09:04–15:54 in standard time and 10:04–16:54 in daylight time. GitHub may delay a
scheduled run; the scraper does not reject a delayed run based only on the local time, so new prices can
still be published.

### Schedule

The workflow is scheduled every 10 minutes from 08:04 through 14:54 UTC. These are targets, not exact
guarantees, because GitHub may delay a scheduled run. A delayed run still fetches and publishes the
current data.

### Manual and external triggers

The workflow supports `workflow_dispatch`: use **Actions → Publish fuel prices → Run workflow**.
The same trigger can be called by an external scheduler such as cron-job.org, which is more punctual
than GitHub's `schedule`:

- `POST https://api.github.com/repos/gorbirad/CPN/actions/workflows/publish-news.yaml/dispatches`
- Headers: `Authorization: Bearer <token>`, `Accept: application/vnd.github+json`
- Body: `{"ref": "main"}`
- Use a fine-grained token limited to this repository with only **Actions: Read and write**.
  Keep it only in the scheduler; never put it in the integration or the repository.

### Detecting new prices

The scraper compares the existing JSON with newly parsed articles semantically. It ignores timestamps,
JSON formatting, and article ordering. A price change or a changed set of articles (an article added
or removed) counts as a data change. If the business data is identical, the scraper does not rewrite
`news.json`, create a commit, or redeploy Pages.

### Lock after new prices are published

After detecting changed data, the scraper sets `disabledUntil` in `state.json` to 12:00 the next day
in `Europe/Warsaw` (stored in UTC). Subsequent scheduled runs read this state and exit before
contacting gov.pl until that time. If there are no new prices, the lock is not extended and the next
scheduled check runs normally. If `state.json` is corrupt, the scraper fails closed without contacting
gov.pl; repair the file manually to resume.

### Home Assistant cache

The integration uses Home Assistant's persistent `Store` with an adaptive TTL. Home Assistant checks
every 5 minutes. Between 11:00 and 17:00 Poland time, while the feed has no article for a future day,
the TTL is 4 minutes, so new prices are picked up within about 5 minutes of publication. Once the feed
contains tomorrow's price (or outside that window), the TTL is one hour. A fresh cache is used
without downloading JSON; after it expires, Home Assistant fetches the feed from GitHub Pages. The
cache survives restarts. HTTP, network, timeout, and invalid-JSON errors trigger up to three attempts
with 2- and 4-second backoff. If refresh fails, the integration retains the last valid cached data;
without a cache, it reports an update error instead of exposing empty prices. After an integration
upgrade, the first feed check bypasses the cache once; the version marker is saved only after a
successful network response. If Pages is unavailable, the integration retries on its scheduled
refreshes and keeps the previous cache when available.

## Entities

| Entity | Description |
|--------|-------------|
| `sensor.benzyna_95` | Latest published price for petrol 95 |
| `sensor.benzyna_95_obecna` | Petrol 95 price effective **today** |
| `sensor.benzyna_98` | Latest published price for petrol 98 |
| `sensor.benzyna_98_obecna` | Petrol 98 price effective **today** |
| `sensor.olej_napedowy` | Latest published price for diesel |
| `sensor.olej_napedowy_obecna` | Diesel price effective **today** |
| `sensor.cena_obowiazuje_od` | Date when the latest published prices take effect |

The “current” sensors (`*_obecna`) have these attributes: `valid_from`, `next_price`,
`next_valid_from`, `change_next` (new minus current), `previous_price`, and `change_previous`
(current minus previous). They switch to the price effective that day at midnight. The other sensors
always show the latest published price, which may already be for the next day.

Fuel price sensors also provide `valid_from` (`YYYY-MM-DD`), `title`, `url`, and `summary`. For a
multi-day price article (for example a weekend range), `valid_from` is the first day of the range.
The ministry usually publishes prices around 12:00–12:30, so a new price may appear with that delay.

### Price history

When the integration is first added or updated with a history-import change, it imports the last
7 days of prices (or the 4 latest articles if there are no articles in that period) into long-term
statistics, with one point per day from
00:00. This makes it possible to display a chart immediately, for example with a
`statistics-graph` card. Historical data comes from articles in the central JSON feed.

## Installation

### HACS (recommended)

1. In HACS, open the ⋮ menu and choose **Custom repositories**.
2. Add `https://github.com/gorbirad/CPN` with the **Integration** category.
3. Search for **CPN** and select **Download**.
4. Restart Home Assistant.

### Manual installation

1. Download the latest version from [Releases](https://github.com/gorbirad/CPN/releases), or clone
   this repository.
2. Copy `custom_components/cpn` into the `custom_components` directory in your Home Assistant
   configuration (the directory containing `configuration.yaml`). Create `custom_components` if it
   does not exist.
3. The resulting layout should look like this:

   ```text
   config/
   ├── configuration.yaml
   └── custom_components/
       └── cpn/
           ├── __init__.py
           ├── manifest.json
           └── ...
   ```

4. Restart Home Assistant.

## Setup

1. Go to **Settings → Devices & services → Add integration**.
2. Search for **CPN** and complete setup.

## Example cards (card-mod)

These three similar cards demonstrate the **latest published price**, the **price effective today**,
and the **price difference**. Each card also has a separate YAML file in this repository. To use
another fuel, replace `sensor.benzyna_95` with `sensor.benzyna_98` or `sensor.olej_napedowy`.

### Card 1: latest published price

See [example_card.yaml](example_card.yaml). It highlights the card when the price changed in the last
hour and shows the date from which the price is effective.

**Requirement:** this card uses [card-mod](https://github.com/thomasloven/lovelace-card-mod).
Install it from HACS → Frontend, then refresh the browser. Without card-mod, the card itself still
works but the highlight and additional date text are not shown.

```yaml
type: entity
entity: sensor.benzyna_95
name: Petrol 95
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
      content: "Effective from: {{ as_datetime(state_attr('sensor.benzyna_95', 'valid_from')).strftime('%d.%m.%Y') }}";
      display: block;
      font-size: 12px;
      color: var(--secondary-text-color);
      margin-top: 4px;
    }
```

### Card 2: price effective today

See [example_card_current_price.yaml](example_card_current_price.yaml).

```yaml
type: entity
entity: sensor.benzyna_95_obecna
name: Petrol 95 — current
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
      content: "Effective from: {{ as_datetime(state_attr('sensor.benzyna_95_obecna', 'valid_from')).strftime('%d.%m.%Y') }}";
      display: block;
      font-size: 12px;
      color: var(--secondary-text-color);
      margin-top: 4px;
    }
```

### Card 3: price difference (new minus current)

See [example_card_diff.yaml](example_card_diff.yaml). A green background means a price decrease;
red means an increase. The new price and its effective date appear below the value. If a new price
is not yet available, the card shows `unknown`.

```yaml
type: entity
entity: sensor.benzyna_95_obecna
attribute: change_next
name: Petrol 95 — price change (new − current)
unit: PLN
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
      content: "{{ state_attr('sensor.benzyna_95_obecna', 'next_price') }} PLN from {{ as_datetime(state_attr('sensor.benzyna_95_obecna', 'next_valid_from')).strftime('%d.%m.%Y') if state_attr('sensor.benzyna_95_obecna', 'next_valid_from') else '–' }}";
      display: block;
      font-size: 12px;
      color: var(--secondary-text-color);
      margin-top: 4px;
    }
```

### Combined Markdown card (no card-mod)

The [example_card_current.yaml](example_card_current.yaml) card shows the current price, the new
price (from the next effective date), and the difference in a table. It does not require card-mod.

```yaml
type: markdown
title: Maximum fuel prices
content: |
  {% set fuels = [('Petrol 95', 'sensor.benzyna_95_obecna'),
                  ('Petrol 98', 'sensor.benzyna_98_obecna'),
                  ('Diesel', 'sensor.olej_napedowy_obecna')] %}
  {% set e = fuels[0][1] %}
  Current price from **{{ state_attr(e, 'valid_from') }}**
  {%- if state_attr(e, 'next_valid_from') %}, new price from **{{ state_attr(e, 'next_valid_from') }}**{% endif %}

  | Fuel | Current | New | Change |
  |---|---|---|---|
  {% for name, ent in fuels -%}
  {% set now_p = states(ent) | float(none) -%}
  {% set nxt = state_attr(ent, 'next_price') -%}
  {% set d = state_attr(ent, 'change_next') -%}
  {% set dp = state_attr(ent, 'change_previous') -%}
  | {{ name }} | **{{ '%.2f' | format(now_p) if now_p is not none else '–' }} PLN** | {{ '%.2f' | format(nxt) ~ ' PLN' if nxt is not none else '–' }} | {% if d is not none %}{{ '🔺 +' if d > 0 else '🔻 ' if d < 0 else '' }}{{ '%.2f' | format(d) }} PLN (next){% elif dp is not none %}{{ '🔺 +' if dp > 0 else '🔻 ' if dp < 0 else '' }}{{ '%.2f' | format(dp) }} PLN (vs previous){% else %}–{% endif %} |
  {% endfor %}
```

Price history chart (7 days):

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

## Project structure

```text
CPN/
├── .github/
│   └── workflows/
│       ├── publish-news.yaml    # scheduled scraper and GitHub Pages deployment
│       └── validate.yaml        # HACS, hassfest, and scraper tests
├── custom_components/
│   └── cpn/
│       ├── __init__.py          # integration setup and unload
│       ├── article_history.py   # selects initial history articles
│       ├── config_flow.py       # UI setup flow
│       ├── const.py             # JSON URL, cache TTL, and fuel list
│       ├── coordinator.py       # JSON fetching and persistent cache
│       ├── history.py           # historical statistics import
│       ├── manifest.json        # integration metadata
│       ├── sensor.py            # fuel-price sensors
│       ├── strings.json
│       └── translations/
│           ├── en.json
│           └── pl.json
├── scripts/
│   └── update_news.py           # gov.pl scraper, comparison, and daily lock
├── tests/
│   └── test_update_news.py      # scraper, delayed-run, and lock tests
├── news.json                    # generated public feed (created by workflow)
├── state.json                   # scraper lock state
├── CHANGELOG.md
├── hacs.json
├── LICENSE
└── README.md
```
