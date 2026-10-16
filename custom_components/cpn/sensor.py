"""Sensors for CPN."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, FUELS


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [CpnSensor(coordinator, key, name) for key, name in FUELS.items()]
    entities.append(CpnValidFromSensor(coordinator))
    async_add_entities(entities)


class CpnSensor(CoordinatorEntity, SensorEntity):
    _attr_native_unit_of_measurement = "PLN/l"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:gas-station"
    _attr_has_entity_name = True

    def __init__(self, coordinator, key: str, name: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{key}"

    @property
    def native_value(self):
        return (self.coordinator.data or {}).get("prices", {}).get(self._key)

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        valid_from = data.get("date")
        return {
            "valid_from": valid_from.isoformat() if valid_from else None,
            "title": data.get("title"),
            "url": data.get("url"),
            "summary": data.get("summary"),
        }


class CpnValidFromSensor(CoordinatorEntity, SensorEntity):
    """Date from which the currently published prices apply."""

    _attr_device_class = SensorDeviceClass.DATE
    _attr_icon = "mdi:calendar-check"
    _attr_has_entity_name = True
    _attr_name = "Cena obowiązuje od"
    _attr_unique_id = f"{DOMAIN}_valid_from"

    @property
    def native_value(self):
        return (self.coordinator.data or {}).get("date")
