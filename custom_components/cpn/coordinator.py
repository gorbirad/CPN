"""Data coordinator for CPN."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime, timedelta, timezone
from math import isfinite

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .article_history import select_history
from .const import CACHE_TTL_SECONDS, DOMAIN, FUELS, NEWS_JSON_URL

_LOGGER = logging.getLogger(__name__)


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as err:
        raise ValueError("timestamp is not valid ISO-8601") from err
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def validate_news_payload(payload: object) -> dict:
    """Validate and normalize the published JSON without trusting remote data."""
    if not isinstance(payload, dict):
        raise ValueError("news JSON root must be an object")
    last_update = payload.get("lastUpdate")
    _parse_timestamp(last_update)
    raw_articles = payload.get("articles")
    if not isinstance(raw_articles, list) or not raw_articles:
        raise ValueError("news JSON must contain a non-empty articles array")

    articles = []
    for index, raw in enumerate(raw_articles):
        if not isinstance(raw, dict):
            raise ValueError(f"article {index} must be an object")
        title, url, summary = raw.get("title"), raw.get("url"), raw.get("summary")
        if not all(isinstance(value, str) and value.strip() for value in (title, url, summary)):
            raise ValueError(f"article {index} has invalid title, url, or summary")
        if not url.startswith("https://www.gov.pl/"):
            raise ValueError(f"article {index} URL is not a gov.pl HTTPS URL")
        raw_date = raw.get("date")
        if raw_date is not None and not isinstance(raw_date, str):
            raise ValueError(f"article {index} date must be an ISO date or null")
        try:
            article_date = date.fromisoformat(raw_date) if raw_date else None
        except ValueError as err:
            raise ValueError(f"article {index} date is not a valid ISO date") from err

        raw_prices = raw.get("prices")
        if not isinstance(raw_prices, dict):
            raise ValueError(f"article {index} prices must be an object")
        prices = {}
        for key in FUELS:
            value = raw_prices.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"article {index} price {key} must be numeric")
            if not isfinite(value) or value <= 0:
                raise ValueError(f"article {index} price {key} must be finite and positive")
            prices[key] = round(float(value), 2)
        articles.append(
            {
                "title": title,
                "url": url,
                "date": article_date,
                "summary": summary,
                "prices": prices,
            }
        )

    articles.sort(key=lambda item: item["date"] or date.min, reverse=True)
    latest = articles[0]
    return {
        **latest,
        "articles": articles,
        "lastUpdate": _parse_timestamp(last_update),
    }


def split_current(articles: list[dict], today: date) -> tuple[dict | None, dict | None, dict | None]:
    """Return (current, next, previous) articles relative to today."""
    dated = sorted((a for a in articles if a.get("date")), key=lambda a: a["date"], reverse=True)
    current_idx = next((i for i, a in enumerate(dated) if a["date"] <= today), None)
    if current_idx is None:
        return None, (dated[-1] if dated else None), None
    future = dated[:current_idx]
    nxt = future[-1] if future else None
    prev = dated[current_idx + 1] if current_idx + 1 < len(dated) else None
    return dated[current_idx], nxt, prev


class CpnCoordinator(DataUpdateCoordinator[dict]):
    """Read published fuel-price data, using a one-hour persistent cache."""

    def __init__(self, hass: HomeAssistant, force_refresh: bool = False) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)
        self._store = Store(hass, 1, f"{DOMAIN}_news_cache")
        self._cached_data: dict | None = None
        self._cached_at: datetime | None = None
        self._cache_loaded = False
        self._force_refresh = force_refresh
        self.fetched_from_network = False

    async def _load_cache(self) -> None:
        if self._cache_loaded:
            return
        self._cache_loaded = True
        try:
            stored = await self._store.async_load()
            if not isinstance(stored, dict):
                return
            fetched_at = _parse_timestamp(stored.get("fetched_at"))
            data = validate_news_payload(stored.get("payload"))
        except (HomeAssistantError, OSError, TypeError, ValueError) as err:
            _LOGGER.warning("Lokalny cache CPN jest uszkodzony i zostanie odtworzony: %s", err)
            return
        self._cached_at = fetched_at
        self._cached_data = data

    async def _async_update_data(self) -> dict:
        await self._load_cache()
        now = datetime.now(timezone.utc)
        if (
            not self._force_refresh
            and self._cached_data is not None
            and self._cached_at is not None
            and timedelta(0) <= now - self._cached_at < timedelta(seconds=CACHE_TTL_SECONDS)
        ):
            return self._cached_data

        session = async_get_clientsession(self.hass)
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                async with session.get(NEWS_JSON_URL, timeout=15) as response:
                    response.raise_for_status()
                    payload = json.loads(await response.text())
                data = validate_news_payload(payload)
                fetched_at = datetime.now(timezone.utc)
                try:
                    await self._store.async_save(
                        {"fetched_at": fetched_at.isoformat(), "payload": payload}
                    )
                except (HomeAssistantError, OSError) as err:
                    _LOGGER.error("Nie udało się zapisać trwałego cache CPN: %s", err)
                self._cached_at = fetched_at
                self._cached_data = data
                self._force_refresh = False
                self.fetched_from_network = True
                return data
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError, ValueError) as err:
                last_error = err
                _LOGGER.warning(
                    "Błąd pobierania lub walidacji JSON CPN (próba %d/3): %s",
                    attempt + 1,
                    err,
                )
            if attempt < 2:
                await asyncio.sleep(2**attempt)

        if self._cached_data is not None:
            _LOGGER.warning("Nie udało się odświeżyć danych CPN, używam cache: %s", last_error)
            return self._cached_data
        raise UpdateFailed(f"Nie udało się pobrać poprawnych danych z {NEWS_JSON_URL}: {last_error}")
