#!/usr/bin/env python3
"""Fetch gov.pl fuel-price articles and update the Pages JSON only on data changes."""
from __future__ import annotations

import html
import json
import logging
import math
import os
import re
import socket
import sys
import tempfile
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

NEWS_URL = "https://www.gov.pl/web/energia/wiadomosci"
LOCAL_ZONE = ZoneInfo("Europe/Warsaw")
FUEL_KEYS = ("pb95", "pb98", "on")
MONTHS = {
    "stycznia": 1,
    "lutego": 2,
    "marca": 3,
    "kwietnia": 4,
    "maja": 5,
    "czerwca": 6,
    "lipca": 7,
    "sierpnia": 8,
    "wrzesnia": 9,
    "pazdziernika": 10,
    "listopada": 11,
    "grudnia": 12,
}
ARTICLE_RE = re.compile(
    r'<a[^>]+href="(?P<href>/web/energia/maksymalna-cena-detaliczna-paliw[^"]*)"[^>]*>'
    r"(?P<title>.*?)</a>(?P<rest>.*?)(?=<a[^>]+href=\"/web/energia/|\Z)",
    re.I | re.S,
)
INTRO_RE = re.compile(r'<div class="intro">(?P<intro>.*?)</div>', re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
DATE_RE = re.compile(
    r"obowiazujaca-+(?:w-dniach-+)?(\d{1,2})(?:-+\d{1,2})?-+([a-z]+)"
    r"(?:-+\d{1,2}-+[a-z]+)?-+(\d{4})",
    re.I,
)
PRICE_RES = {
    "pb95": re.compile(r"benzyna\s*95\s*[-–—:]\s*(\d+[.,]\d+)", re.I),
    "pb98": re.compile(r"benzyna\s*98\s*[-–—:]\s*(\d+[.,]\d+)", re.I),
    "on": re.compile(r"olej\s*napędowy\s*[-–—:]\s*(\d+[.,]\d+)", re.I),
}

_LOGGER = logging.getLogger("cpn.scraper")


class ScraperError(Exception):
    """Invalid persisted state or source data."""


class FetchError(ScraperError):
    """gov.pl could not be reached (transient network failure)."""


def clean_text(value: str) -> str:
    return " ".join(html.unescape(TAG_RE.sub(" ", value)).split())


def article_date(url: str) -> date | None:
    match = DATE_RE.search(url)
    if not match or match.group(2).lower() not in MONTHS:
        return None
    try:
        return date(
            int(match.group(3)),
            MONTHS[match.group(2).lower()],
            int(match.group(1)),
        )
    except ValueError:
        return None


def parse_articles(page: str) -> list[dict]:
    """Parse fuel-price articles from the gov.pl news list."""
    articles = []
    for match in ARTICLE_RE.finditer(page):
        intro = INTRO_RE.search(match.group("rest"))
        summary = clean_text(intro.group("intro")) if intro else ""
        prices = {}
        for key, pattern in PRICE_RES.items():
            price_match = pattern.search(summary)
            if price_match:
                prices[key] = round(float(price_match.group(1).replace(",", ".")), 2)
        if len(prices) != len(FUEL_KEYS):
            if prices:
                _LOGGER.warning("Pomijam niepełny artykuł z cenami: %s", match.group("href"))
            continue
        href = match.group("href")
        effective_date = article_date(href)
        if effective_date is None:
            _LOGGER.warning("Nie rozpoznano daty artykułu: %s", href)
        articles.append(
            {
                "title": clean_text(match.group("title")),
                "url": f"https://www.gov.pl{href}",
                "date": effective_date.isoformat() if effective_date else None,
                "summary": summary,
                "prices": prices,
            }
        )
    return articles


def validate_news(payload: object) -> dict:
    """Validate an existing generated news file before using it as a baseline."""
    if not isinstance(payload, dict):
        raise ScraperError("news.json root must be an object")
    last_update = payload.get("lastUpdate")
    if not isinstance(last_update, str):
        raise ScraperError("news.json has no ISO-8601 lastUpdate")
    try:
        parsed_update = datetime.fromisoformat(last_update.replace("Z", "+00:00"))
    except ValueError as err:
        raise ScraperError("news.json lastUpdate is invalid") from err
    if parsed_update.tzinfo is None:
        raise ScraperError("news.json lastUpdate must include a timezone")
    articles = payload.get("articles")
    if not isinstance(articles, list) or not articles:
        raise ScraperError("news.json articles must be a non-empty array")
    for index, article in enumerate(articles):
        if not isinstance(article, dict):
            raise ScraperError(f"news.json article {index} must be an object")
        for key in ("title", "url", "summary"):
            if not isinstance(article.get(key), str) or not article[key].strip():
                raise ScraperError(f"news.json article {index} has invalid {key}")
        if not article["url"].startswith("https://www.gov.pl/"):
            raise ScraperError(f"news.json article {index} has invalid URL")
        article_day = article.get("date")
        if article_day is not None:
            if not isinstance(article_day, str):
                raise ScraperError(f"news.json article {index} date must be a string or null")
            try:
                date.fromisoformat(article_day)
            except ValueError as err:
                raise ScraperError(f"news.json article {index} date is invalid") from err
        prices = article.get("prices")
        if not isinstance(prices, dict) or any(key not in prices for key in FUEL_KEYS):
            raise ScraperError(f"news.json article {index} has incomplete prices")
        for key in FUEL_KEYS:
            value = prices[key]
            if isinstance(value, bool) or not isinstance(value, (float, int)) or value <= 0:
                raise ScraperError(f"news.json article {index} has invalid {key} price")
            if not math.isfinite(value):
                raise ScraperError(f"news.json article {index} has non-finite {key} price")
    return payload


def business_signature(payload: dict) -> tuple:
    """Ignore timestamps, formatting, list order, title, and summary."""
    records = []
    for article in payload["articles"]:
        prices = tuple((key, round(float(article["prices"][key]), 2)) for key in FUEL_KEYS)
        records.append((article["url"], article.get("date"), prices))
    return tuple(sorted(records))


def has_future_article(payload: dict, today: date) -> bool:
    """Return whether the feed already contains prices effective after today."""
    return any(
        article.get("date") is not None
        and date.fromisoformat(article["date"]) > today
        for article in payload["articles"]
    )


def _ipv4_only(func: Callable):
    """Run func with DNS limited to IPv4; GitHub runners often lack IPv6 routes."""
    original = socket.getaddrinfo

    def getaddrinfo(host, port, family=0, *args, **kwargs):
        return original(host, port, socket.AF_INET, *args, **kwargs)

    socket.getaddrinfo = getaddrinfo
    try:
        return func()
    finally:
        socket.getaddrinfo = original


def fetch_page() -> str:
    """Fetch gov.pl with bounded retries and request timeout."""
    request = Request(
        NEWS_URL,
        headers={"User-Agent": "CPN-Home-Assistant/1.0 (+https://github.com/gorbirad/CPN)"},
    )
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            def read() -> str:
                with urlopen(request, timeout=20) as response:
                    return response.read().decode("utf-8")

            return _ipv4_only(read)
        except (HTTPError, URLError, TimeoutError, OSError) as err:
            last_error = err
            _LOGGER.warning("Błąd pobierania gov.pl (próba %d/3): %s", attempt + 1, err)
            if attempt < 2:
                time.sleep(2**attempt)
    raise FetchError(f"Nie udało się pobrać strony gov.pl: {last_error}")


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False
        ) as temp_file:
            temp_name = temp_file.name
            temp_file.write(text)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def update_repository(
    root: Path,
    now: datetime,
    page_fetcher: Callable[[], str] = fetch_page,
) -> bool:
    """Update the news file only when article/pricing data changes."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    now_utc = now.astimezone(timezone.utc)
    news_path = root / "news.json"

    previous = None
    if news_path.exists():
        try:
            previous = validate_news(json.loads(news_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, ScraperError) as err:
            raise ScraperError(f"news.json is corrupt; refusing to replace it: {err}") from err
        if has_future_article(previous, now.astimezone(LOCAL_ZONE).date()):
            _LOGGER.info(
                "news.json zawiera już ceny na kolejny dzień; pomijam sprawdzanie gov.pl"
            )
            return False

    page = page_fetcher()
    articles = parse_articles(page)
    if not articles:
        raise ScraperError("Nie znaleziono kompletnych artykułów o cenach paliw")
    candidate = {
        "lastUpdate": now_utc.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "articles": articles,
    }
    validate_news(candidate)
    if previous is not None and business_signature(previous) == business_signature(candidate):
        _LOGGER.info("Dane biznesowe nie zmieniły się; pomijam zapis i commit")
        return False

    atomic_write(
        news_path,
        json.dumps(candidate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    _LOGGER.info("Zapisano %d artykułów", len(articles))
    return True


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    root = Path(__file__).resolve().parent.parent
    try:
        changed = update_repository(root, datetime.now(timezone.utc))
    except FetchError as err:
        # Transient outage: keep existing data and retry on the next scheduled run.
        _LOGGER.warning("%s; pomijam tę aktualizację", err)
        changed = False
    except (ScraperError, OSError, ValueError) as err:
        _LOGGER.error("%s", err)
        return 1
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as output:
            output.write(f"changed={'true' if changed else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
