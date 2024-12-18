import os
import json
import logging
from homeassistant.components.http import HomeAssistantView
import asyncio

_LOGGER = logging.getLogger(__name__)

class GeweContactsAPI(HomeAssistantView):
    """Custom API for fetching Gewe contacts."""

    # 定义 API 的 URL 和名称
    url = "/api/gewe_contacts"
    name = "api:gewe_contacts"
    requires_auth = True  # 需要 Home Assistant 的登录认证

    def __init__(self, hass):
        """Initialize the API with Home Assistant instance."""
        self.hass = hass

    async def get(self, request):
        """Handle GET requests to return Gewe contacts."""
        # 文件路径定义
        file_path = self.hass.config.path(".storage", "gewe_contacts.json")
        _LOGGER.debug(f"Attempting to load contacts from {file_path}")

        # 尝试加载联系人数据
        try:
            if not os.path.exists(file_path):
                _LOGGER.warning(f"Contacts file does not exist: {file_path}")
                return self.json_message("Contacts file not found", status_code=404)

            # 使用 async_add_executor_job 来异步执行文件读取
            contacts_data = await self.hass.async_add_executor_job(self._load_contacts, file_path)

            # 返回数据
            return self.json(contacts_data)

        except Exception as e:
            _LOGGER.error(f"Error loading contacts: {e}")
            return self.json_message(f"Error loading contacts: {e}", status_code=500)

    def _load_contacts(self, file_path):
        """Blocking function to load contacts data from file."""
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)

