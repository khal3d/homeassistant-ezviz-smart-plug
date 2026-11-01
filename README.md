# EZVIZ Smart Plug
A Home Assistant custom Integration for Ezviz Smart Plugs.

## Supported Devices
- CS-T30-10A-EU
- CS-T30-10B-EU

## Compatibility with recent Home Assistant (1.0.1)
Home Assistant stopped shipping the `pyezviz` library (the core `ezviz` integration now uses `pyezvizapi`), and removed `async_forward_entry_setup`, so the integration failed to load with
`No module named 'pyezviz'` / `Platform ezviz_plug.config_flow not found`. Version 1.0.1:
- uses `pyezvizapi` (`requirements: pyezvizapi>=1.0.5.0`) instead of `pyezviz`;
- uses `hass.config_entries.async_forward_entry_setups` and adds `async_unload_entry`, so the entry can be reloaded;
- uses `asyncio.timeout` instead of `async_timeout`.

Tested on Home Assistant 2026.10.4 with an EZVIZ smart plug whose serial starts with `Q`: login, config flow, switch on/off and state update work.
Plugs whose serial does not start with `Q` are still not detected (see #5).
