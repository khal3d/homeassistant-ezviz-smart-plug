"""Ezviz Smart Plug integration."""

from homeassistant import config_entries, core
from .const import DOMAIN


async def async_setup_entry(hass: core.HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    """Set up platform from a ConfigEntry."""

    hass.data.setdefault(DOMAIN, {})
    hass_data = dict(entry.data)

    # Registers update listener to update config entry when options are updated.
    unsub_options_update_listener = entry.add_update_listener(options_update_listener)

    # Store a reference to the unsubscribe function to cleanup if an entry is unloaded.
    hass_data["unsub_options_update_listener"] = unsub_options_update_listener
    hass.data[DOMAIN][entry.entry_id] = hass_data

    # Forward the setup to the switch platform.
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "switch")
    )

    return True


async def options_update_listener(hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Set up the Ezviz Smart Plug custom component from yaml configuration."""
    hass.data.setdefault(DOMAIN, {})
    return True
