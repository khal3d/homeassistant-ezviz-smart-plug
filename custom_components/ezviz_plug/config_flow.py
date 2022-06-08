from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD, CONF_URL, CONF_TIMEOUT, CONF_CUSTOMIZE
from .const import DOMAIN, DEFAULT_TIMEOUT, EU_URL, RUSSIA_URL, CONF_RFSESSION_ID, CONF_SESSION_ID
from pyezviz.client import EzvizClient
from pyezviz.exceptions import (
    AuthTestResultFailed,
    EzvizAuthVerificationCode,
    InvalidHost,
    InvalidURL,
    PyEzvizError,
)
import logging
import voluptuous as vol
from typing import Any, Dict

_LOGGER = logging.getLogger(__name__)

# TODO adjust the data schema to the data that you need
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(
            CONF_EMAIL, description="The username used with EZVIZ App, so your email"
        ): str,
        vol.Required(
            CONF_PASSWORD, description="The password used with EZVIZ App"
        ): str,
        vol.Required(CONF_URL, default=EU_URL): vol.In(
            [EU_URL, RUSSIA_URL, CONF_CUSTOMIZE]
        ),
    }
)


def _validate_and_create_auth(data: dict) -> dict[str, Any]:
    """Try to login to ezviz cloud account and return token."""
    # Verify cloud credentials by attempting a login request with username and password.
    # Return login token.
    ezviz_client = EzvizClient(
        data[CONF_EMAIL],
        data[CONF_PASSWORD],
        data[CONF_URL],
        data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
    )

    ezviz_token = ezviz_client.login()

    auth_data = {
        CONF_EMAIL: data[CONF_EMAIL],
        CONF_PASSWORD: data[CONF_PASSWORD],
        CONF_SESSION_ID: ezviz_token[CONF_SESSION_ID],
        CONF_RFSESSION_ID: ezviz_token[CONF_RFSESSION_ID],
        CONF_URL: ezviz_token["api_url"],
    }

    return auth_data


class EzvizConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ezviz Plugs."""

    async def async_step_user(self, user_input):

        errors = {}
        auth_data = {}

        if user_input is not None:
            try:
                auth_data = await self.hass.async_add_executor_job(
                    _validate_and_create_auth, user_input
                )
            except InvalidURL:
                errors["base"] = "invalid_host"
            except InvalidHost:
                errors["base"] = "cannot_connect"
            except EzvizAuthVerificationCode:
                errors["base"] = "mfa_required"
            except PyEzvizError:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                return self.async_abort(reason="unknown")
            else:
                return self.async_create_entry(
                    title=user_input[CONF_EMAIL],
                    data=auth_data,
                    options={},
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
