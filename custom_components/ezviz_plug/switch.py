"""Support for EzvizSwitch."""
from __future__ import annotations

import logging
from typing import Any, Dict
from datetime import datetime, timedelta
import voluptuous as vol

try:
    from homeassistant.components.switch import SwitchEntity
except ImportError:
    from homeassistant.components.switch import SwitchDevice as SwitchEntity
from homeassistant.components.switch import PLATFORM_SCHEMA
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant import core

from pyezviz import client
from pyezviz.exceptions import (
    AuthTestResultFailed,
    EzvizAuthVerificationCode,
    InvalidHost,
    InvalidURL,
    HTTPError,
    PyEzvizError,
)

from pyezviz.constants import (DeviceSwitchType)
from .const import DOMAIN
from .coordinator import EzvizDataUpdateCoordinator

SCAN_INTERVAL = timedelta(seconds=5)
_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_EMAIL): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
    }
)


async def async_unload_entry(hass, config_entry):
    _LOGGER.debug(f"async_unload_entry {DOMAIN}: {config_entry}")

    return True


async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Perform the setup for Ezviz Smart Plug devices."""

    _LOGGER.debug('calling setup_platform')

    email = config.get(CONF_EMAIL)
    password = config.get(CONF_PASSWORD)
    ezvizClient = client.EzvizClient(email, password)

    try:
        auth_data = await hass.async_add_executor_job(ezvizClient.login)
    except (InvalidHost, InvalidURL, HTTPError, PyEzvizError) as error:
        _LOGGER.exception('Invalid response from API: %s', error)
    except EzvizAuthVerificationCode:
        _LOGGER.exception('MFA Required')
    except (Exception) as error:
        _LOGGER.exception('Unexpected exception: %s', error)

    coordinator = EzvizDataUpdateCoordinator(hass, api=ezvizClient, api_timeout=10)

    # Add devices
    plugs = []
    switches = await coordinator._async_update_data();
    for key, switch in switches.items():
        plugs.append(Ezvizswitch(switch, ezvizClient))

    add_entities(plugs)

    _LOGGER.info('Closing the Client session.')
    ezvizClient.close_session()


async def async_setup_entry(hass: core.HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    """Set up Ezviz switch based on a config entry."""

    email = hass.data[DOMAIN][entry.entry_id][CONF_EMAIL]
    password = hass.data[DOMAIN][entry.entry_id][CONF_PASSWORD]
    ezvizClient = client.EzvizClient(email, password)

    try:
        auth_data = await hass.async_add_executor_job(ezvizClient.login)
    except (InvalidHost, InvalidURL, HTTPError, PyEzvizError) as error:
        _LOGGER.exception('Invalid response from API: %s', error)
    except EzvizAuthVerificationCode:
        _LOGGER.exception('MFA Required')
    except (Exception) as error:
        _LOGGER.exception('Unexpected exception: %s', error)

    coordinator = EzvizDataUpdateCoordinator(hass, api=ezvizClient, api_timeout=10)

    # Add devices
    plugs = []
    switches = await coordinator._async_update_data();
    for key, switch in switches.items():
        plugs.append(Ezvizswitch(switch, ezvizClient))

    async_add_entities(plugs)

    _LOGGER.debug('Closing the Client session.')
    ezvizClient.close_session()


class Ezvizswitch(SwitchEntity, RestoreEntity):
    """Representation of Ezviz Smart Plug Entity."""

    def __init__(self, switch, ezvizClient) -> None:
        """Initialize the Ezviz Smart Plug."""

        self._state = None
        self._last_run_success = None
        self._last_pressed: datetime | None = None
        self._switch = switch
        self._ezviz_client = ezvizClient

    async def async_added_to_hass(self):
        """Run when entity about to be added."""

        _LOGGER.info('async_added_to_hass called')

        await super().async_added_to_hass()

        state = await self.async_get_last_state()
        if not state:
            return
        self._state = state.state == "on"

    def turn_on(self, **kwargs) -> None:
        """Turn device on."""

        _LOGGER.debug('Turning on %s (current state is: %s cloud: %s)', self._switch['name'], self._state,
                     self._switch['enable'])

        # 14 = DeviceSwitchType.PLUG
        if self._ezviz_client.switch_status(self._switch["deviceSerial"], 14, 1):
            self._state = True
            self._switch['enable'] = True
            self._last_pressed = dt_util.utcnow()
            self._last_run_success = True
        else:
            self._last_run_success = False

    def turn_off(self, **kwargs) -> None:
        """Turn device off."""
        _LOGGER.debug('Turning off %s (current state is: %s cloud: %s)', self._switch['name'], self._state,
                     self._switch['enable'])

        if self._ezviz_client.switch_status(self._switch["deviceSerial"], 14, 0):
            self._state = False
            self._switch['enable'] = False
            self._last_pressed = dt_util.utcnow()
            self._last_run_success = True
        else:
            self._last_run_success = False

    async def async_update(self):
        _LOGGER.debug("calling update method.")

        coordinator = EzvizDataUpdateCoordinator(self.hass, api=self._ezviz_client, api_timeout=10)
        switches = await coordinator._async_update_data()
        self._switch = switches[self._switch["deviceSerial"]]

    @property
    def is_on(self) -> bool:
        """Return true if device is on."""

        if self._state is not bool:
            self._state = (True if self._switch['enable'] == 1 else False)

        return self._state

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return False if self._switch['status'] == 2 else True

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return self._switch['deviceSerial']

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return self._switch['name']

    def last_pressed(self) -> str:
        if self._last_pressed is None:
            return ''
        return self._last_pressed.isoformat()

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        return {"last_run_success": self._last_run_success, "last_pressed": self.last_pressed()}

    @property
    def icon(self) -> str:
        """Icon of the entity."""

        if self._switch["deviceType"].endswith("EU"):
            return "mdi:power-socket-de"
        elif self._switch["deviceSerial"].endswith("US"):
            return "mdi:power-socket-us"
        else:
            return "mdi:power-socket"
