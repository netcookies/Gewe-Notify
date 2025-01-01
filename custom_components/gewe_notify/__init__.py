import logging
import os
import json
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform, CONF_NAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import discovery
from .const import CONF_API_URL, DOMAIN, CONF_GEWE_TOKEN, CONF_APP_ID, CONF_WXID
from .notify import GeweNotifyService
from .api import GeweAPI
from .http_api import GeweContactsAPI

_LOGGER = logging.getLogger(__name__)

# 只包含需要的支持平台
PLATFORMS: list[Platform] = [
        Platform.SENSOR,
        Platform.NOTIFY
        ]

def save_contacts_to_file(file_path, contacts):
    """Saves contacts data to a file."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(contacts, f, ensure_ascii=False, indent=4)
        _LOGGER.info(f"Contacts data saved to {file_path}")
    except Exception as e:
        _LOGGER.error(f"Error saving contacts to file: {e}")

async def fetch_contacts_formated_service(hass: HomeAssistant, entry: ConfigEntry, call: ServiceCall):
    """Call the fetch_contacts_formated method."""
    token = entry.data.get(CONF_GEWE_TOKEN)
    app_id = entry.data.get(CONF_APP_ID)
    api = hass.data[DOMAIN].get("api")

    if not api:
        _LOGGER.error("API instance not found during fetch_contacts_formated_service")
        return

    try:
        result = await api.fetch_contacts_formated(token, app_id)
        if result:
            storage_path = hass.config.path(".storage/gewe_contacts.json")
            os.makedirs(os.path.dirname(storage_path), exist_ok=True)
            await hass.async_add_executor_job(save_contacts_to_file, storage_path, result)
            _LOGGER.info(f"Contacts data saved to {storage_path}")

            persistent_notification_data = {
                "title": "Gewe 通讯录更新成功通知",
                "message": f"通讯录已缓存至{storage_path}。如需更新请手动触发Action: gewe_notify.fetch_contacts。",
                "notification_id": "gewe_notify_contacts_updated"
            }
            # 调用 Home Assistant 服务发送持久化通知
            await hass.services.async_call(
                "persistent_notification", "create", persistent_notification_data
            )

        else:
            _LOGGER.error("Failed to fetch formatted contacts.")
    except Exception as e:
        _LOGGER.error(f"Error in fetch_contacts_formated_service: {e}")

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Gewe Notify integration as a config entry."""
    _LOGGER.debug("Setting up Gewe Notify integration with entry: %s", entry.as_dict())

    # 从 config entry 获取配置数据
    api_url = entry.data[CONF_API_URL]
    gewe_token = entry.data[CONF_GEWE_TOKEN]
    app_id = entry.data[CONF_APP_ID]

    # 将 API 客户端添加到 hass 数据中
    session = async_get_clientsession(hass)
    api = GeweAPI(hass, api_url, session)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["api"] = api
    _LOGGER.debug(f"Instance {hass.data[DOMAIN]['api']} of Gewe Notify regeisted.")

    # 注册自定义 HTTP API
    api_view = GeweContactsAPI(hass)
    hass.http.register_view(api_view)
    hass.data[DOMAIN]["api_view"] = api_view
    _LOGGER.debug("Custom Api of Gewe Notify regeisted.")

    async def fetch_contacts_service_wrapper(call: ServiceCall):
        await fetch_contacts_formated_service(hass, entry, call)

    # 注册自定义服务
    hass.services.async_register( DOMAIN, "fetch_contacts", fetch_contacts_service_wrapper)
    _LOGGER.debug("Action of Gewe Notify regeisted.")

    # Notify doesn't support config entry setup yet, load with discovery for now
    await discovery.async_load_platform(
        hass,
        Platform.NOTIFY,
        DOMAIN,
        {
            CONF_NAME: "gewe_notify",
            CONF_GEWE_TOKEN: gewe_token,
            CONF_APP_ID: app_id
        },
        entry.data,
    )
    _LOGGER.debug("Notify of Gewe Notify regeisted.")

    await hass.config_entries.async_forward_entry_setups(entry, [
        platform for platform in PLATFORMS if platform != Platform.NOTIFY
        ])
    _LOGGER.debug("Sensor of Gewe Notify regeisted.")

    _LOGGER.info("Gewe Notify integration setup complete.")
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Gewe Notify integration with entry: %s", entry.as_dict())

    api = hass.data[DOMAIN].get("api")
    if api:
        token = entry.data.get(CONF_GEWE_TOKEN)
        app_id = entry.data.get(CONF_APP_ID)
        await api.logout(token, app_id)

    # 取消注册服务
    hass.services.async_remove(DOMAIN, "fetch_contacts")

    # 卸载非 NOTIFY 平台
    unload_ok = await hass.config_entries.async_unload_platforms(
         entry, [platform for platform in PLATFORMS if platform != Platform.NOTIFY]
    )
    if unload_ok:
        hass.data[DOMAIN].pop("api", None)
        hass.data[DOMAIN].pop("api_view", None)

    return unload_ok
