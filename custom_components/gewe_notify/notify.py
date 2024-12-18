import logging
from homeassistant.components.notify import BaseNotificationService
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from .const import DOMAIN, CONF_GEWE_TOKEN, CONF_APP_ID

_LOGGER = logging.getLogger(__name__)

class GeweNotifyService(BaseNotificationService):
    """Notification service for Gewe Notify."""

    def __init__(self, hass, token, app_id):
        """Initialize the notification service."""
        self.hass = hass
        self.token = token
        self.appid = app_id
        try:
            self.api = hass.data[DOMAIN]["api"]
        except KeyError:
            _LOGGER.error("API instance not found in hass.data. Ensure integration is set up correctly.")
            raise

    async def async_send_message(self, message="", **kwargs):
        """Send a message asynchronously."""
        targets = kwargs.get("target", [])
        if not targets or not isinstance(targets, list):
            _LOGGER.error("No valid target specified.")
            return

        to_wxid = targets[0]  # 如果只支持单个目标，可以直接取第一个
        _LOGGER.debug(f"Sending message to target: {to_wxid}")
        _LOGGER.debug(f"Read token: {self.token} appId: {self.appid}.")

        try:
            response = await self.api.send_message(
                self.token,
                self.appid,
                to_wxid,
                message
            )
            if response:
                _LOGGER.debug(f"Message sent successfully to {to_wxid}")
            else:
                _LOGGER.error(f"Failed to send message to {to_wxid}")
        except Exception as e:
            _LOGGER.error(f"Error sending message to {to_wxid}: {e}")

async def async_get_service(
    hass: HomeAssistant,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> GeweNotifyService | None:
    """Get the Gewe notify service."""
    if discovery_info is None:
        return
    token = discovery_info[CONF_GEWE_TOKEN]
    app_id = discovery_info[CONF_APP_ID]
    return GeweNotifyService(hass, token, app_id)

