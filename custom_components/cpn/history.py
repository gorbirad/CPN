"""Import of historical prices into long-term statistics."""
from __future__ import annotations

import logging
from datetime import datetime, time

from homeassistant.components.recorder.models import StatisticData, StatisticMetaData
from homeassistant.components.recorder.statistics import async_import_statistics
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .article_history import select_history
from .const import DOMAIN, FUELS

_LOGGER = logging.getLogger(__name__)


def _metadata(entity_id: str) -> StatisticMetaData:
    meta = {
        "has_sum": False,
        "name": None,
        "source": "recorder",
        "statistic_id": entity_id,
        "unit_of_measurement": "PLN/l",
    }
    try:
        from homeassistant.components.recorder.models import StatisticMeanType

        meta["mean_type"] = StatisticMeanType.ARITHMETIC
        meta["unit_class"] = None
    except ImportError:
        meta["has_mean"] = True
    return meta  # type: ignore[return-value]


def import_history(hass: HomeAssistant, articles: list[dict]) -> int:
    """Write one statistic per day and fuel (price valid from 00:00 local time)."""
    history = select_history(articles, dt_util.now().date())
    registry = er.async_get(hass)
    imported = 0
    for key in FUELS:
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{DOMAIN}_{key}")
        if not entity_id:
            continue
        stats = []
        for art in history:
            price = art["prices"].get(key)
            if price is None:
                continue
            start = dt_util.as_utc(
                datetime.combine(art["date"], time.min, tzinfo=dt_util.DEFAULT_TIME_ZONE)
            )
            stats.append(StatisticData(start=start, mean=price, min=price, max=price))
        if stats:
            async_import_statistics(hass, _metadata(entity_id), stats)
            imported += len(stats)
    _LOGGER.debug("Zaimportowano %s punktów historii", imported)
    if not imported:
        _LOGGER.warning(
            "Nie zaimportowano historii cen: brak artykułów z poprawną datą i cenami"
        )
    return imported
