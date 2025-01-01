
import aiohttp
import asyncio
import logging

_LOGGER = logging.getLogger(__name__)

class GeweAPI:
    """A helper class for handling asynchronous API calls."""

    def __init__(self, hass, api_url, session: aiohttp.ClientSession):
        """Initialize with API URL and aiohttp session."""
        self.api_url = api_url
        self.session = session
        self.hass = hass

    def truncate_dict(self, d, max_items=10):
        """ 截断字典，只保留前 max_items 个键值对 """
        truncated = dict(list(d.items())[:max_items])
        return str(truncated) + ('...' if len(d) > max_items else '')

    def truncate_string(self, s, max_length=100):
        """ 截断字符串，确保其长度不超过 max_length """
        return s[:max_length] + ('...' if len(s) > max_length else '') if isinstance(s, str) else str(s)

    async def _handle_offline_error(self, error_message):
        """Trigger a persistent notification prompting reconfiguration."""
        _LOGGER.error(f"Reconfiguration required: {error_message}")
        notification_title = "Gewe 集成需要重新扫码登录"
        notification_message = (
            "Gewe 集成检测到你的微信已离线且无法重连. "
            "请前往集成配置页面点击重新配置."
        )
        reconfig_url = "/config/integrations"
        persistent_notification_data = {
            "title": notification_title,
            "message": f"{notification_message}\n\n[Reconfigure Here]({reconfig_url})",
            "notification_id": "gewe_reconfiguration_required"
        }
        await self.hass.services.async_call("persistent_notification", "create", persistent_notification_data)

    def _check_offline_error(self, data):
        """Check if the response indicates that the device is offline."""
        return data.get("ret") == 500 and data.get("data", {}).get("code") == "-1"

    async def _api_post(self, url, headers, payload, offline_error_message):
        """General method for making POST requests to the API."""
        try:
            async with self.session.post(url, json=payload, headers=headers) as response:
                data = await response.json()
                if self._check_offline_error(data):
                    await self._handle_offline_error(offline_error_message)
                    return None
                if data.get("ret") == 200:
                    return data.get("data")
                else:
                    _LOGGER.error(f"Failed to process request: {data}")
        except Exception as e:
            _LOGGER.error(f"Error in API request: {e}")
        return None

    async def get_token(self):
        """Create gewe-token."""
        url = f"{self.api_url}/v2/api/tools/getTokenId"
        return await self._api_post(url, {}, {}, "微信已离线，无法获取 token")

    async def get_login_qr(self, token, app_id=""):
        """Get login QR code."""
        url = f"{self.api_url}/v2/api/login/getLoginQrCode"
        headers = {"X-GEWE-TOKEN": token, "Content-Type": "application/json"}
        payload = {"appId": app_id}
        try:
            async with self.session.post(url, json=payload, headers=headers) as response:
                data = await response.json()
                if self._check_offline_error(data):
                    await self._handle_offline_error("微信已离线，无法获取登录二维码")
                    return None
                if data["ret"] == 200:
                    _LOGGER.debug(f"Step 2: Generating QR code for token: {token} app_id: {app_id}")
                    return data["data"]
                elif data["ret"] == 500:
                    _LOGGER.warning("Device not found. Creating new device.")
                    return await self.get_login_qr(token, "")
                else:
                    _LOGGER.error(f"Failed to get QR code: {data}")
        except Exception as e:
            _LOGGER.error(f"Error in get_login_qr: {e}")
        return None

    async def check_login(self, token, app_id, uuid):
        """Check login status."""
        url = f"{self.api_url}/v2/api/login/checkLogin"
        headers = {"X-GEWE-TOKEN": token, "Content-Type": "application/json"}
        payload = {"appId": app_id, "uuid": uuid}
        return await self._api_post(url, headers, payload, "微信已离线，无法检查登录状态")

    async def check_online(self, token, app_id):
        """Check if the device is online."""
        url = f"{self.api_url}/v2/api/login/checkOnline"
        headers = {"X-GEWE-TOKEN": token, "Content-Type": "application/json"}
        payload = {"appId": app_id}
        return await self._api_post(url, headers, payload, "微信已离线，无法检查在线状态")

    async def logout(self, token, app_id):
        """Logout."""
        url = f"{self.api_url}/v2/api/login/logout"
        headers = {"X-GEWE-TOKEN": token, "Content-Type": "application/json"}
        payload = {"appId": app_id}
        try:
            async with self.session.post(url, json=payload, headers=headers) as response:
                data = await response.json()
                if self._check_offline_error(data):
                    await self._handle_offline_error("微信已离线，无法登出")
                    return False
                if data["ret"] == 200:
                    return True
                else:
                    _LOGGER.error(f"Failed to logout: {data}")
                    return False
        except Exception as e:
            _LOGGER.error(f"Error in logout: {e}")
        return None

    async def reconnection(self, token, app_id):
        """Reconnection."""
        url = f"{self.api_url}/v2/api/login/reconnection"
        headers = {"X-GEWE-TOKEN": token, "Content-Type": "application/json"}
        payload = {"appId": app_id}
        try:
            async with self.session.post(url, json=payload, headers=headers) as response:
                data = await response.json()
                if self._check_offline_error(data):
                    await self._handle_offline_error("微信已离线，无法重连")
                    return False
                if data["ret"] == 200:
                    _LOGGER.info(f"Gewe reconnection successful: {data}")
                    return True
                else:
                    _LOGGER.error(f"Failed to reconnection: {data}")
                    return False
        except Exception as e:
            _LOGGER.error(f"Error in reconnection: {e}")
        return None

    async def getProfile(self, token, app_id):
        """Get person profile."""
        url = f"{self.api_url}/v2/api/personal/getProfile"
        headers = {"X-GEWE-TOKEN": token, "Content-Type": "application/json"}
        payload = {"appId": app_id}
        return await self._api_post(url, headers, payload, "微信已离线，无法获取个人资料")

    async def send_text_message(self, token, app_id, to_wxid, content, ats=None):
        """Send a text message."""
        url = f"{self.api_url}/v2/api/message/postText"
        headers = {"X-GEWE-TOKEN": token, "Content-Type": "application/json"}
        # 构建基本的消息 payload
        payload = {"appId": app_id, "toWxid": to_wxid, "content": content}
        # 如果有 ats 参数，加入到 payload 中
        if ats:
            payload["ats"] = ats
        _LOGGER.debug(f"Sending text message to {to_wxid} with {content} and ats: {ats}.")
        return await self._api_post(url, headers, payload, "微信已离线，无法发送文本消息")

    async def send_file_message(self, token, app_id, to_wxid, file_url, file_name):
        """Send a file message."""
        url = f"{self.api_url}/v2/api/message/postFile"
        headers = {"X-GEWE-TOKEN": token, "Content-Type": "application/json"}
        payload = {"appId": app_id, "toWxid": to_wxid, "fileUrl": file_url, "fileName": file_name}
        _LOGGER.debug(f"Sending file message to {to_wxid} with file: {file_name}.")
        return await self._api_post(url, headers, payload, "微信已离线，无法发送文件消息")

    async def send_image_message(self, token, app_id, to_wxid, image_url):
        """Send an image message."""
        url = f"{self.api_url}/v2/api/message/postImage"
        headers = {"X-GEWE-TOKEN": token, "Content-Type": "application/json"}
        payload = {"appId": app_id, "toWxid": to_wxid, "imageUrl": image_url}
        _LOGGER.debug(f"Sending image message to {to_wxid} with image URL: {image_url}.")
        return await self._api_post(url, headers, payload, "微信已离线，无法发送图片消息")

    async def send_voice_message(self, token, app_id, to_wxid, voice_url, voice_duration):
        """Send a voice message."""
        url = f"{self.api_url}/v2/api/message/postVoice"
        headers = {"X-GEWE-TOKEN": token, "Content-Type": "application/json"}
        payload = {"appId": app_id, "toWxid": to_wxid, "voiceUrl": voice_url, "voiceDuration": voice_duration}
        _LOGGER.debug(f"Sending voice message to {to_wxid} with voice URL: {voice_url}.")
        return await self._api_post(url, headers, payload, "微信已离线，无法发送语音消息")

    async def send_video_message(self, token, app_id, to_wxid, video_url, video_duration, thumb_url):
        """Send a video message."""
        url = f"{self.api_url}/v2/api/message/postVideo"
        headers = {"X-GEWE-TOKEN": token, "Content-Type": "application/json"}
        payload = {"appId": app_id, "toWxid": to_wxid, "videoUrl": video_url, "videoDuration": video_duration, "thumbUrl": thumb_url}
        _LOGGER.debug(f"Sending video message to {to_wxid} with video URL: {video_url}.")
        return await self._api_post(url, headers, payload, "微信已离线，无法发送视频消息")

    async def send_link_message(self, token, app_id, to_wxid, link_url, title, desc, thumb_url):
        """Send a link message."""
        url = f"{self.api_url}/v2/api/message/postLink"
        headers = {"X-GEWE-TOKEN": token, "Content-Type": "application/json"}
        payload = {"appId": app_id, "toWxid": to_wxid, "linkUrl": link_url, "title": title, "desc": desc, "thumbUrl": thumb_url}
        _LOGGER.debug(f"Sending link message to {to_wxid} with URL: {link_url} and title: {title}.")
        return await self._api_post(url, headers, payload, "微信已离线，无法发送链接消息")

    async def send_message(self, token, app_id, to_wxid, message_type="text", **kwargs):
        """统一的发送消息方法入口，根据消息类型动态调用相应的方法"""
        
        # 判断消息类型，动态调用对应的发送方法
        if message_type == 'text':
            content = kwargs.get('content')
            ats = kwargs.get('ats')  # ats 是可选的，如果没有提供则默认为 None
            return await self.send_text_message(token, app_id, to_wxid, content, ats)
        
        elif message_type == 'file':
            file_url = kwargs.get('file_url')
            file_name = kwargs.get('file_name')
            return await self.send_file_message(token, app_id, to_wxid, file_url, file_name)
        
        elif message_type == 'image':
            image_url = kwargs.get('image_url')
            return await self.send_image_message(token, app_id, to_wxid, image_url)
        
        elif message_type == 'voice':
            voice_url = kwargs.get('voice_url')
            voice_duration = kwargs.get('voice_duration')
            return await self.send_voice_message(token, app_id, to_wxid, voice_url, voice_duration)
        
        elif message_type == 'video':
            video_url = kwargs.get('video_url')
            video_duration = kwargs.get('video_duration')
            thumb_url = kwargs.get('thumb_url')
            return await self.send_video_message(token, app_id, to_wxid, video_url, video_duration, thumb_url)
        
        elif message_type == 'link':
            link_url = kwargs.get('link_url')
            title = kwargs.get('title')
            desc = kwargs.get('desc')
            thumb_url = kwargs.get('thumb_url')
            return await self.send_link_message(token, app_id, to_wxid, link_url, title, desc, thumb_url)
        
        else:
            _LOGGER.error(f"Unsupported message type: {message_type}")
            raise ValueError(f"Unsupported message type: {message_type}")

    async def fetch_contacts(self, token, app_id):
        """Fetch contact list."""
        url = f"{self.api_url}/v2/api/contacts/fetchContactsList"
        headers = {"X-GEWE-TOKEN": token, "Content-Type": "application/json"}
        payload = {"appId": app_id}
        return await self._api_post(url, headers, payload, "微信已离线，获取通讯录失败")

    async def fetch_contacts_cache(self, token, app_id):
        """Fetch contact list from cache."""
        url = f"{self.api_url}/v2/api/contacts/fetchContactsListCache"
        headers = {"X-GEWE-TOKEN": token, "Content-Type": "application/json"}
        payload = {"appId": app_id}
        return await self._api_post(url, headers, payload, "微信已离线，获取通讯录失败")

    async def fetch_contacts_info(self, token, app_id, wxids):
        """Fetch brief contact information in batches of up to 100 wxids."""
        url = f"{self.api_url}/v2/api/contacts/getBriefInfo"
        headers = {"X-GEWE-TOKEN": token, "Content-Type": "application/json"}

        def chunkify(lst, chunk_size):
            for i in range(0, len(lst), chunk_size):
                yield lst[i:i + chunk_size]

        all_contacts = []
        for wxid_batch in chunkify(wxids, 100):
            payload = {"appId": app_id, "wxids": wxid_batch}
            data = await self._api_post(url, headers, payload, "微信已离线，获取个人信息失败")
            if data:
                all_contacts.extend(data)
        return all_contacts or None

    async def fetch_contacts_formated(self, token, app_id):
        """Fetch contacts from cache or contacts list, then get brief contact info."""
        contact_data = await self.fetch_contacts_cache(token, app_id) or await self.fetch_contacts(token, app_id)
        if not contact_data or ("friends" not in contact_data or "chatrooms" not in contact_data):
            _LOGGER.error("Failed to fetch contacts from cache or from contacts list.")
            return None

        # Initialize lists to store friends' and chatrooms' wxids separately
        friends_wxids = []
        chatrooms_wxids = []

        # Add friends' and chatrooms' wxids to the respective lists
        if "friends" in contact_data:
            friends_wxids.extend(contact_data["friends"])

        if "chatrooms" in contact_data:
            chatrooms_wxids.extend(contact_data["chatrooms"])

        # Fetch the brief contact info for friends and chatrooms separately
        brief_friends_info = await self.fetch_contacts_info(token, app_id, friends_wxids) if friends_wxids else []
        brief_chatrooms_info = await self.fetch_contacts_info(token, app_id, chatrooms_wxids) if chatrooms_wxids else []

        # Process friends' brief contact info
        if brief_friends_info:
            friends_result = [
                {
                    "userName": contact.get("userName"),
                    "nickName": contact.get("nickName"),
                    "smallHeadImgUrl": contact.get("smallHeadImgUrl"),
                    "quanPin": contact.get("quanPin"),
                    "remark": contact.get("remark")
                }
                for contact in brief_friends_info
            ]
            # Sort friends by quanPin
            friends_result.sort(key=lambda x: x["quanPin"] if x["quanPin"] else "")

        else:
            _LOGGER.error("Failed to fetch brief friends' contact info.")
            friends_result = []

        # Process chatrooms' brief contact info
        if brief_chatrooms_info:
            chatrooms_result = [
                {
                    "userName": contact.get("userName"),
                    "nickName": contact.get("nickName"),
                    "smallHeadImgUrl": contact.get("smallHeadImgUrl"),
                    "quanPin": contact.get("quanPin"),
                    "remark": contact.get("remark")
                }
                for contact in brief_chatrooms_info
            ]
            # Sort chatrooms by quanPin
            chatrooms_result.sort(key=lambda x: x["quanPin"] if x["quanPin"] else "")

        else:
            _LOGGER.error("Failed to fetch brief chatrooms' contact info.")
            chatrooms_result = []

        # Return both friends' and chatrooms' sorted results
        return {
            "friends": friends_result,
            "chatrooms": chatrooms_result
        }
