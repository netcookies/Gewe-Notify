import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components import persistent_notification
from .const import DOMAIN, CONF_GEWE_TOKEN, CONF_APP_ID

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up Gewe Notify sensor based on a config entry."""
    api = hass.data[DOMAIN]["api"]

    # 从配置中获取 token 和 app_id
    token = entry.data[CONF_GEWE_TOKEN]
    app_id = entry.data[CONF_APP_ID]

    sensors = [
            GeweOnlineSensor(api, token, app_id)
            ]

    # 将传感器添加到系统中
    async_add_entities(sensors)
    _LOGGER.debug("Gewe Notify sensor setup complete.")

class GeweOnlineSensor(SensorEntity):
    """Representation of a Gewe Notify online sensor."""

    def __init__(self, api, token, app_id):
        self.api = api
        self.token = token
        self.app_id = app_id
        self._state = None


    @property
    def name(self):
        """Return the name of the sensor."""
        return "Gewe Notify Online Status"

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return "gewe_notify_online_status"

    @property
    def state(self):
        """Return the state of the sensor."""
        # 这里获取 coordinator 中的数据，它将包含 check_online 返回的状态
        return self._state

    async def async_update(self):
        """Fetch online status from Gewe API."""
        try:
            # 使用 get_online 方法时传入 token 和 app_id
            online_status = await self.api.check_online(self.token, self.app_id)
            self._state = online_status
        except Exception as e:
            _LOGGER.error(f"Error fetching online status: {e}")
        _LOGGER.debug(f"Instance {self.api}. Gewe Notify sensor updated.state: {online_status}")
