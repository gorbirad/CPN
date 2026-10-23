"""CPN - maksymalne ceny detaliczne paliw z gov.pl."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_change

from .const import DOMAIN, FEED_REFRESH_VERSION, REFRESH_MINUTES
from .coordinator import CpnCoordinator
from .history import import_history

PLATFORMS = ["sensor"]
HISTORY_IMPORT_VERSION = "1.1.2"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    should_force_feed_refresh = (
        entry.data.get("feed_refresh_version") != FEED_REFRESH_VERSION
    )
    coordinator = CpnCoordinator(hass, force_refresh=should_force_feed_refresh)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    def mark_feed_refresh_complete() -> None:
        if (
            coordinator.fetched_from_network
            and entry.data.get("feed_refresh_version") != FEED_REFRESH_VERSION
        ):
            hass.config_entries.async_update_entry(
                entry,
                data={
                    **entry.data,
                    "feed_refresh_version": FEED_REFRESH_VERSION,
                },
            )

    async def _midnight_update(_now) -> None:
        # Po północy "obecna" cena zmienia się bez nowego artykułu
        coordinator.async_update_listeners()

    async def _scheduled_refresh(_now) -> None:
        await coordinator.async_request_refresh()
        mark_feed_refresh_complete()

    entry.async_on_unload(
        async_track_time_change(hass, _midnight_update, hour=0, minute=0, second=5)
    )
    entry.async_on_unload(
        async_track_time_change(
            hass, _scheduled_refresh, minute=REFRESH_MINUTES, second=0
        )
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    mark_feed_refresh_complete()
    if entry.data.get("history_import_version") != HISTORY_IMPORT_VERSION:
        imported = import_history(hass, (coordinator.data or {}).get("articles", []))
        if imported:
            hass.config_entries.async_update_entry(
                entry,
                data={
                    **entry.data,
                    "history_imported": True,
                    "history_import_version": HISTORY_IMPORT_VERSION,
                },
            )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        return True
    return False
