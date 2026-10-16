"""CPN - maksymalne ceny detaliczne paliw z gov.pl."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_change

from .const import DOMAIN, REFRESH_MINUTES
from .coordinator import CpnCoordinator
from .history import import_history

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = CpnCoordinator(hass)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    async def _midnight_update(_now) -> None:
        # Po północy "obecna" cena zmienia się bez nowego artykułu
        coordinator.async_update_listeners()

    async def _scheduled_refresh(_now) -> None:
        await coordinator.async_request_refresh()

    entry.async_on_unload(
        async_track_time_change(hass, _midnight_update, hour=0, minute=0, second=5)
    )
    entry.async_on_unload(
        async_track_time_change(
            hass, _scheduled_refresh, minute=REFRESH_MINUTES, second=0
        )
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    if not entry.data.get("history_imported"):
        import_history(hass, (coordinator.data or {}).get("articles", []))
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, "history_imported": True}
        )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        return True
    return False
