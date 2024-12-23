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
        if isinstance(s, str):
            return s[:max_length] + ('...' if len(s) > max_length else '')
        return str(s)

    async def _handle_offline_error(self, error_message):
        """Trigger a persistent notification prompting reconfiguration."""
        _LOGGER.error(f"Reconfiguration required: {error_message}")
        notification_title = "Gewe 集成需要重新扫码登录"
        notification_message = (
            "Gewe 集成检测到你的微信已离线且无法重连. "
            "请前往集成配置页面点击重新配置."
        )
        # 添加跳转链接到集成重新配置页面
        reconfig_url = "/config/integrations"
        persistent_notification_data = {
            "title": notification_title,
            "message": f"{notification_message}\n\n[Reconfigure Here]({reconfig_url})",
            "notification_id": "gewe_reconfiguration_required"
        }
        # 调用 Home Assistant 服务发送持久化通知
        await self.hass.services.async_call(
            "persistent_notification", "create", persistent_notification_data
        )

    def _check_offline_error(self, data):
        """Check if the response indicates that the device is offline."""
        if data.get("ret") == 500 and data.get("data", {}).get("code") == "-1":
            return True
        return False

    async def get_token(self):
        """Create gewe-token."""
        url = f"{self.api_url}/v2/api/tools/getTokenId"
        try:
            async with self.session.post(url) as response:
                data = await response.json()
                if self._check_offline_error(data):
                    await self._handle_offline_error("微信已离线，无法获取 token")
                    return None
                if data["ret"] == 200:
                    return data["data"]
                else:
                    _LOGGER.error(f"Failed to get token: {data}")
        except Exception as e:
            _LOGGER.error(f"Error in get_token: {e}")
        return None

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
        try:
            async with self.session.post(url, json=payload, headers=headers) as response:
                data = await response.json()
                if self._check_offline_error(data):
                    await self._handle_offline_error("微信已离线，无法检查登录状态")
                    return None
                if data["ret"] == 200:
                    _LOGGER.debug(f"Step 3.1: Checking login response: {data}")
                    return data["data"]
                else:
                    _LOGGER.error(f"Failed to check login: {data}")
        except Exception as e:
            _LOGGER.error(f"Error in check_login: {e}")
        return None

    async def check_online(self, token, app_id):
        """Check if the device is online."""
        url = f"{self.api_url}/v2/api/login/checkOnline"
        headers = {"X-GEWE-TOKEN": token, "Content-Type": "application/json"}
        payload = {"appId": app_id}
        try:
            async with self.session.post(url, json=payload, headers=headers) as response:
                data = await response.json()
                if self._check_offline_error(data):
                    await self._handle_offline_error("微信已离线，无法检查在线状态")
                    return None
                if data["ret"] == 200:
                    _LOGGER.debug(f"Check online response: {data}")
                    return data["data"]
                else:
                    _LOGGER.error(f"Failed to check online: {data}")
        except Exception as e:
            _LOGGER.error(f"Error in check_online: {e}")
        return None

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
        try:
            async with self.session.post(url, json=payload, headers=headers) as response:
                data = await response.json()
                if self._check_offline_error(data):
                    await self._handle_offline_error("微信已离线，无法获取个人资料")
                    return None
                if data["ret"] == 200:
                    return data["data"]
                else:
                    _LOGGER.error(f"Failed to get person profile: {data}")
        except Exception as e:
            _LOGGER.error(f"Error in get person profile: {e}")
        return None

    async def send_message(self, token, app_id, to_wxid, content):
        """Send a message."""
        url = f"{self.api_url}/v2/api/message/postText"
        headers = {"X-GEWE-TOKEN": token, "Content-Type": "application/json"}
        payload = {"appId": app_id, "toWxid": to_wxid, "content": content}
        _LOGGER.debug(f"Send message to {to_wxid} with {content}. Token: {token} App Id: {app_id}")
        try:
            async with self.session.post(url, json=payload, headers=headers) as response:
                data = await response.json()
                if self._check_offline_error(data):
                    await self._handle_offline_error("微信已离线，无法发送消息")
                    return None
                if data["ret"] == 200:
                    _LOGGER.debug(f"Response of Send message: {data}")
                    return data["data"]
                else:
                    _LOGGER.error(f"Failed to send message: {data}")
        except Exception as e:
            _LOGGER.error(f"Error in send_message: {e}")
        return None

    async def fetch_contacts(self, token, app_id):
        """Fetch contact list."""
        url = f"{self.api_url}/v2/api/contacts/fetchContactsList"
        headers = {"X-GEWE-TOKEN": token, "Content-Type": "application/json"}
        payload = {"appId": app_id}
        try:
            async with self.session.post(url, json=payload, headers=headers) as response:
                data = await response.json()
                if self._check_offline_error(data):
                    await self._handle_offline_error("微信已离线，获取通讯录失败")
                    return None
                if data["ret"] == 200:
                    _LOGGER.debug(f"fetch contacts: {self.truncate_string(str(data))}")
                    return data["data"]
                else:
                    _LOGGER.error(f"Failed to fetch contacts: {self.truncate_string(str(data))}")
                    return None
        except Exception as e:
            _LOGGER.error(f"Error in fetch_contacts: {e}")
        return None

    async def fetch_contacts_cache(self, token, app_id):
        """Fetch contact list from cache."""
        url = f"{self.api_url}/v2/api/contacts/fetchContactsListCache"
        headers = {"X-GEWE-TOKEN": token, "Content-Type": "application/json"}
        payload = {"appId": app_id}
        try:
            async with self.session.post(url, json=payload, headers=headers) as response:
                data = await response.json()
                if self._check_offline_error(data):
                    await self._handle_offline_error("微信已离线，获取通讯录失败")
                    return None
                if data["ret"] == 200:
                    if "data" in data:
                        _LOGGER.debug(f"fetch contacts from cache: {self.truncate_string(str(data))}")
                        return data["data"]
                    else:
                        _LOGGER.debug(f"Contacts cache is empty.Data: {data}")
                        return None
                else:
                    _LOGGER.error(f"Failed to fetch contacts form cache: {self.truncate_string(str(data))}")
                    return None
        except Exception as e:
            _LOGGER.error(f"Error in fetch_contacts: {e}")
        return None

    async def fetch_contacts_info(self, token, app_id, wxids):
        """Fetch brief contact information in batches of up to 100 wxids."""
        url = f"{self.api_url}/v2/api/contacts/getBriefInfo"
        headers = {"X-GEWE-TOKEN": token, "Content-Type": "application/json"}

        # Function to split wxids into chunks of 100
        def chunkify(lst, chunk_size):
            for i in range(0, len(lst), chunk_size):
                yield lst[i:i + chunk_size]

        # Initialize a list to store results from all batches
        all_contacts = []

        # Split wxids into chunks of 100 and fetch data for each batch
        for wxid_batch in chunkify(wxids, 100):
            payload = {"appId": app_id, "wxids": wxid_batch}
            try:
                async with self.session.post(url, json=payload, headers=headers) as response:
                    data = await response.json()
                    if self._check_offline_error(data):
                        await self._handle_offline_error("微信已离线，获取个人信息失败")
                        return None
                    if data["ret"] == 200:
                        _LOGGER.debug(f"Fetch brief contact info for batch {self.truncate_string(str(wxid_batch))}: {self.truncate_string(str(data))}")
                        all_contacts.extend(data["data"])  # Add the fetched data to the result list
                    else:
                        _LOGGER.error(f"Failed to fetch brief contact info for batch {self.truncate_string(str(wxid_batch))}: {self.truncate_string(str(data))}")
            except Exception as e:
                _LOGGER.error(f"Error in fetch_brief_contact_info for batch {self.truncate_string(str(wxid_batch))}: {e}")

        # Return the accumulated contacts data
        if all_contacts:
            return all_contacts
        else:
            return None

    async def fetch_contacts_formated(self, token, app_id):
        """Fetch contacts from cache or contacts list, then get brief contact info with quanPin and remark."""

        # First, try fetching contacts from cache
        contact_data = await self.fetch_contacts_cache(token, app_id)

        # If no data in cache or no friends/chatrooms data, fetch from contacts list
        if not contact_data or contact_data is None:
            contact_data = await self.fetch_contacts(token, app_id)

        if contact_data is None or ("friends" not in contact_data or "chatrooms" not in contact_data):
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
