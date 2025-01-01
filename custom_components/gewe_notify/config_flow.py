import os
import logging
import json
import base64
import random
import aiofiles
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_registry import async_get as get_entity_registry
from .api import GeweAPI
from .const import CONF_API_URL, DOMAIN, CONF_GEWE_TOKEN, CONF_APP_ID, CONF_WXID, CONF_NICKNAME

_LOGGER = logging.getLogger(__name__)

USER_INPUT_SCHEMA = vol.Schema({vol.Required(CONF_API_URL): str})

class GeweConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gewe Notify."""

    VERSION = 2

    def __init__(self):
        """Initialize the configuration flow."""
        self.token = None
        self.api_url = None
        self.app_id = None
        self.uuid = None
        self.wxid = None
        self.qr_image_url = None
        self.api = None
        self.relogin_flag = False
        self.scaned_flag = False
        self.reconfigure_flag = False

    async def async_step_user(self, user_input=None):
        """Handle the initial step where the user inputs the API URL."""
        errors = {}

        # 如果已经有 api_url，则保留到 data_schema 中
        default_api_url = self.api_url or ""
        # 动态创建数据 Schema，填充默认值
        data_schema = vol.Schema({vol.Required(CONF_API_URL, default=default_api_url): str})

        # 保存输入的 user_input，避免重新输入
        if user_input is not None:
            self.api_url = user_input[CONF_API_URL]
        else:
            # 如果没有 user_input，则展示表单
            return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)

        if not self.api:
            session = async_get_clientsession(self.hass)
            self.api = GeweAPI(self.hass, self.api_url, session)

        # 如果之前已读取 token，不再重复读取
        if not self.token:
            self.token, self.app_id, self.wxid = await self._get_token_from_file()
            # Step 1: 获取 token
            if not self.token:
                self.token = await self.api.get_token()
                if not self.token:
                    errors["base"] = "token_fetch_failed"
                else:
                    _LOGGER.debug(f"Get token: {self.token}")
            else:
                _LOGGER.debug(f"Step 1: Get token from storage: **Token: {self.token}** **App Id: {self.app_id}** **Wxid: {self.wxid}**")

        if not errors:
            # Step 2: 检查 QR Code 或登录状态
            if self.relogin_flag:
                qr_data = await self.api.get_login_qr(self.token, self.app_id)
                if qr_data:
                    self.app_id = qr_data["appId"]
                    self.uuid = qr_data["uuid"]
                    qr_code_base64 = qr_data["qrImgBase64"]

                    # 保存 QR Code
                    self.qr_image_url = await self._save_qr_code_to_file(qr_code_base64)
                    if self.qr_image_url:
                        _LOGGER.debug(f"QR Code saved and accessible at: {self.qr_image_url}")
                        return await self.async_step_confirm()
                    else:
                        errors["base"] = "qr_code_save_failed"
                        _LOGGER.debug("QR code save failed.")
                else:
                    errors["base"] = "qr_code_fetch_failed"
                    _LOGGER.debug("QR code fetch failed.")
            else:
                # 检查在线状态
                check_online = await self.api.check_online(self.token, self.app_id)
                if check_online:
                    profile = await self.api.getProfile(self.token, self.app_id)
                    if profile:
                        nickname = profile["nickName"]
                        return self.async_create_entry(
                            title="Gewe Notify",
                            data={
                                CONF_API_URL: self.api_url,
                                CONF_GEWE_TOKEN: self.token,
                                CONF_APP_ID: self.app_id,
                                CONF_WXID: self.wxid,
                                CONF_NICKNAME: nickname,
                            },
                        )
                    else:
                        errors["base"] = "login_failed"
                        _LOGGER.debug("Profile detail fetch failed.")
                else:
                    errors["base"] = "device_offline"
                    _LOGGER.debug(f"Gewe backend {self.api_url} device(app_id) offline.")
                    data_schema = vol.Schema({vol.Required(CONF_API_URL, default=self.api_url): str})
                    self.relogin_flag = True

        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)


    async def async_step_confirm(self, user_input=None):
        """Handle the step where the user confirms the QR code scan."""
        _LOGGER.debug(f"Start confirm: API URL {self.api_url} Token: {self.token} App Id: {self.app_id} User Input: {user_input} relogin_flag {self.relogin_flag} scaned_flag: {self.scaned_flag}")

        errors = {}

        if self.scaned_flag:
            _LOGGER.debug(f"Checking login QR code: {self.qr_image_url}")
            login_data = await self.api.check_login(self.token, self.app_id, self.uuid)
            if login_data.get("loginInfo") and login_data["loginInfo"].get("wxid"):
                nickname = login_data["nickName"]
                self.wxid = login_data["loginInfo"]["wxid"]
                await self._save_token_to_file(self.token, self.app_id, self.wxid)
                if self.relogin_flag and self.reconfigure_flag:
                    # Update the existing config entry
                    current_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
                    if current_entry:
                        updated_data = {
                            CONF_API_URL: self.api_url,
                            CONF_GEWE_TOKEN: self.token,
                            CONF_APP_ID: self.app_id,
                            CONF_WXID: self.wxid,
                            CONF_NICKNAME: nickname  # Reset nickname until re-login completes
                        }
                        _LOGGER.debug("Update entry (reconfigure)!!")
                        self.hass.config_entries.async_update_entry(current_entry, data=updated_data)
                        return self.async_abort(reason="reconfigured_successfully")
                else:
                    # Create config entry
                    _LOGGER.debug("Create new entry!!")
                    return self.async_create_entry(
                        title="Gewe Notify",
                        data={
                            CONF_API_URL: self.api_url,
                            CONF_GEWE_TOKEN: self.token,
                            CONF_APP_ID: self.app_id,
                            CONF_WXID: self.wxid,
                            CONF_NICKNAME: nickname,
                        },
                    )
            else:
                self.scaned_flag = False
                errors["base"] = "scan_qrcode_failed"
                return await self.async_step_user(user_input={CONF_API_URL: self.api_url})

        self.scaned_flag = True
        _LOGGER.debug(f"Show QR code: {self.qr_image_url}")
        return self.async_show_form(
            step_id="confirm",
            errors=errors,
            description_placeholders={"qr_image_url": self.qr_image_url},
            data_schema=vol.Schema({}),
        )

    async def async_step_reconfigure(self, user_input=None):
        """Handle the reconfiguration step to logout and re-initiate login."""
        errors = {}

        # 获取当前的配置条目 (config_entry)
        current_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if current_entry:
            # 从 config_entry 的 data 中提取之前保存的数据
            self.api_url = current_entry.data.get(CONF_API_URL)
            self.token = current_entry.data.get(CONF_GEWE_TOKEN)
            self.app_id = current_entry.data.get(CONF_APP_ID)
            self.app_id = current_entry.data.get(CONF_APP_ID)
            self.wxid = current_entry.data.get(CONF_WXID)
        else:
            _LOGGER.error("Reconfigure failed: No existing config entry found.")
            errors["base"] = "config_entry_not_found"
            return self.async_abort(reason="config_entry_not_found")

        if not self.api:
            session = async_get_clientsession(self.hass)
            self.api = GeweAPI(self.hass, self.api_url, session)

        try:
            # Logout the user
            if self.token and self.app_id:
                await self.api.logout(self.token, self.app_id)

            self.relogin_flag = True
            self.reconfigure_flag = True

            return await self.async_step_user()
        except Exception as e:
            _LOGGER.error(f"Reconfiguration failed: {e}")
            errors["base"] = "reconfiguration_failed"

        return self.async_show_form(step_id="reconfigure", data_schema=USER_INPUT_SCHEMA, errors=errors)

    # 新增 async_get_options_flow
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Handle options flow for the config entry."""
        return OptionsFlowHandler()

    async def _get_token_from_file(self):
        """Get the token, app_id, and wxid from the file stored in .storage."""
        token_file_path = os.path.join(self.hass.config.path(".storage"), "gewe_token.json")
        if os.path.exists(token_file_path):
            try:
                async with aiofiles.open(token_file_path, "r") as file:
                    token_data = json.loads(await file.read())
                    return token_data.get("token"), token_data.get("app_id"), token_data.get("wxid")
            except Exception as e:
                _LOGGER.error(f"Failed to read token from file: {e}")
        return None, None, None

    async def _save_token_to_file(self, token, app_id, wxid):
        """Save the token, app_id, and wxid to a file in .storage."""
        token_file_path = os.path.join(self.hass.config.path(".storage"), "gewe_token.json")
        try:
            async with aiofiles.open(token_file_path, "w") as file:
                await file.write(json.dumps({
                    "token": token,
                    "app_id": app_id,
                    "wxid": wxid
                }))
        except Exception as e:
            _LOGGER.error(f"Failed to save token to file: {e}")

    async def _save_qr_code_to_file(self, qr_code_base64):
        """Save QR code image to the www directory and return its URL."""
        www_path = self.hass.config.path("www")
        os.makedirs(www_path, exist_ok=True)
        img_path = os.path.join(www_path, "gewe_qr_code.jpg")
        random_number = random.randint(1000,9999)
        try:
            img_data = base64.b64decode(qr_code_base64.split(",", 1)[-1])
            async with aiofiles.open(img_path, "wb") as file:
                await file.write(img_data)
            return f"/local/gewe_qr_code.jpg?v={random_number}"
        except Exception as e:
            _LOGGER.error(f"Failed to save QR code image: {e}")
            return None
 
 # 处理选项流的类
class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Neta Vehicle Status configuration."""

    def __init__(self):
        self.config = {}
        self._conf_app_id: str | None = None
        self.token = None
        self.api_url = None
        self.app_id = None
        self.uuid = None
        self.wxid = None
        self.qr_image_url = None
        self.api = None
        self.scaned_flag = False
 
    async def async_step_init(self, user_input=None):
        """Manage the options."""
        self.config = dict(self.config_entry.data)
        # 从 config_entry 的 data 中提取之前保存的数据
        self.api_url = self.config_entry.data.get(CONF_API_URL)
        self.token = self.config_entry.data.get(CONF_GEWE_TOKEN)
        self.app_id = self.config_entry.data.get(CONF_APP_ID)
        self.app_id = self.config_entry.data.get(CONF_APP_ID)
        self.wxid = self.config_entry.data.get(CONF_WXID)
        return await self.async_step_confirm()
 
    async def async_step_confirm(self, user_input=None):
        """Handle the initial step where the user inputs the API URL."""
        errors = {}

        if not self.api:
            session = async_get_clientsession(self.hass)
            self.api = GeweAPI(self.hass, self.api_url, session)

        try:
            # Logout the user
            if self.token and self.app_id:
                await self.api.logout(self.token, self.app_id)
        except Exception as e:
            _LOGGER.error(f"OptionsFlow failed: {e}")
            errors["base"] = "optionsflow_failed"

        if not self.scaned_flag:
            # Step 2: 检查 QR Code 或登录状态
            qr_data = await self.api.get_login_qr(self.token, self.app_id)
            if qr_data:
                self.app_id = qr_data["appId"]
                self.uuid = qr_data["uuid"]
                qr_code_base64 = qr_data["qrImgBase64"]

                # 保存 QR Code
                self.qr_image_url = await self._save_qr_code_to_file(qr_code_base64)
                if self.qr_image_url:
                    _LOGGER.debug(f"QR Code saved and accessible at: {self.qr_image_url}")
                    #return await self.async_step_confirm()
                    self.scaned_flag = True
                    return self.async_show_form(
                        step_id="confirm",
                        errors=errors,
                        description_placeholders={"qr_image_url": self.qr_image_url},
                        data_schema=vol.Schema({}),
                    )
                else:
                    errors["base"] = "qr_code_save_failed"
                    _LOGGER.debug("QR code save failed.")
            else:
                errors["base"] = "qr_code_fetch_failed"
                _LOGGER.debug("QR code fetch failed.")
        else:
            _LOGGER.debug(f"Checking login QR code: {self.qr_image_url}")
            login_data = await self.api.check_login(self.token, self.app_id, self.uuid)
            if login_data.get("loginInfo") and login_data["loginInfo"].get("wxid"):
                nickname = login_data["nickName"]
                self.wxid = login_data["loginInfo"]["wxid"]
                await self._save_token_to_file(self.token, self.app_id, self.wxid)
                # 更新配置后，重新加载集成
                await self.hass.config_entries.async_reload(self.config_entry.entry_id)
                _LOGGER.debug("Update entry (options)!!")
                return self.async_abort(reason="options_successfully")
            else:
                self.scaned_flag = False
                errors["base"] = "scan_qrcode_failed"
                return await self.async_step_confirm()

    async def _save_qr_code_to_file(self, qr_code_base64):
        """Save QR code image to the www directory and return its URL."""
        www_path = self.hass.config.path("www")
        os.makedirs(www_path, exist_ok=True)
        img_path = os.path.join(www_path, "gewe_qr_code.jpg")
        random_number = random.randint(1000,9999)
        try:
            img_data = base64.b64decode(qr_code_base64.split(",", 1)[-1])
            async with aiofiles.open(img_path, "wb") as file:
                await file.write(img_data)
            return f"/local/gewe_qr_code.jpg?v={random_number}"
        except Exception as e:
            _LOGGER.error(f"Failed to save QR code image: {e}")
            return None

    async def _save_token_to_file(self, token, app_id, wxid):
        """Save the token, app_id, and wxid to a file in .storage."""
        token_file_path = os.path.join(self.hass.config.path(".storage"), "gewe_token.json")
        try:
            async with aiofiles.open(token_file_path, "w") as file:
                await file.write(json.dumps({
                    "token": token,
                    "app_id": app_id,
                    "wxid": wxid
                }))
        except Exception as e:
            _LOGGER.error(f"Failed to save token to file: {e}")
