"""Data coordinator for CPN."""
from __future__ import annotations

import html
import logging
import re

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import BASE_URL, DOMAIN, NEWS_URL, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

ARTICLE_RE = re.compile(
    r'<a[^>]+href="(?P<href>/web/energia/maksymalna-cena-detaliczna-paliw[^"]*)"[^>]*>'
    r"(?P<title>.*?)</a>(?P<rest>.*?)(?=<a[^>]+href=\"/web/energia/|\Z)",
    re.S | re.I,
)
INTRO_RE = re.compile(r'<div class="intro">(?P<intro>.*?)</div>', re.S | re.I)
PRICE_RES = {
    "pb95": re.compile(r"benzyna\s*95\s*[-–—:]\s*(\d+[.,]\d+)", re.I),
    "pb98": re.compile(r"benzyna\s*98\s*[-–—:]\s*(\d+[.,]\d+)", re.I),
    "on": re.compile(r"olej\s*napędowy\s*[-–—:]\s*(\d+[.,]\d+)", re.I),
}
TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return " ".join(html.unescape(TAG_RE.sub(" ", text)).split())


def parse_articles(page: str) -> list[dict]:
    """Return fuel price articles found on the news list page (newest first)."""
    result = []
    for m in ARTICLE_RE.finditer(page):
        intro = INTRO_RE.search(m.group("rest"))
        text = _clean(intro.group("intro")) if intro else ""
        prices = {}
        for key, rx in PRICE_RES.items():
            pm = rx.search(text)
            if pm:
                prices[key] = float(pm.group(1).replace(",", "."))
        if not prices:
            continue
        result.append(
            {
                "url": BASE_URL + m.group("href"),
                "title": _clean(m.group("title")),
                "summary": text,
                "prices": prices,
            }
        )
    return result


class CpnCoordinator(DataUpdateCoordinator[dict]):
    """Poll gov.pl for the latest maximum fuel prices."""

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)

    async def _async_update_data(self) -> dict:
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(NEWS_URL, timeout=30) as resp:
                resp.raise_for_status()
                page = await resp.text()
        except Exception as err:
            raise UpdateFailed(f"Błąd pobierania {NEWS_URL}: {err}") from err

        articles = parse_articles(page)
        if not articles:
            if self.data:
                _LOGGER.warning("Nie znaleziono artykułu z cenami, zachowuję poprzednie dane")
                return self.data
            raise UpdateFailed("Nie znaleziono artykułu z maksymalnymi cenami paliw")
        return articles[0]
