import logging
from homeassistant.components.notify import BaseNotificationService
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from .const import DOMAIN, CONF_GEWE_TOKEN, CONF_APP_ID

_LOGGER = logging.getLogger(__name__)

class GeweNotifyService(BaseNotificationService):
    """Notification service for Gewe Notify."""

    def __init__(self, hass):
        """Initialize the notification service."""
        self.hass = hass
        self.token = None
        self.appid = None
        self.wxid = None
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
        self.token, self.appid, self.wxid = await self.api.get_token_from_file()
        _LOGGER.debug(f"Sending message to target: {to_wxid}")
        _LOGGER.debug(f"Read token: {self.token} appId: {self.appid}.")

        # 获取标题（可选）
        title = kwargs.get("title", None)

        # 从 data 中获取额外的参数
        data = kwargs.get("data", {}) or {}
        message_type = data.get("message_type", "text")  # 默认为文本消息
        file_url = data.get("file_url", None)
        img_url = data.get("img_url", None)
        ats = data.get("ats", None)
        voice_url = data.get("voice_url", None)
        video_url = data.get("video_url", None)
        video_duration = data.get("video_duration", None)
        thumb_url = data.get("thumb_url", None)

        try:
            response = await self.api.send_message(
                self.token,
                self.appid,
                to_wxid,
                message_type,  # 消息类型
                content=message,  # 必须的消息内容
                title=title,  # 标题（可选）
                ats=ats,  # @ 用户（可选）
                file_url=file_url,  # 文件 URL（可选）
                img_url=img_url,  # 图片 URL（可选）
                voice_url=voice_url,  # 语音 URL（可选）
                video_url=video_url,  # 视频 URL（可选）
                video_duration=video_duration,  # 视频时长（可选）
                thumb_url=thumb_url,  # 缩略图 URL（可选）
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
    return GeweNotifyService(hass)

