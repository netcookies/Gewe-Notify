# Gewe-Notify

Gewe-Notify 是一个基于 Home Assistant HACS 的插件，允许用户通过 **Home Assistant** 系统接收来自 **Gewechat** 后端 API 的实时通知。该插件使得 Home Assistant 用户能够通过多个设备接收通知，支持各种类型的通知服务。

## 功能特点

- 支持通过 Home Assistant 接收 **Gewechat** 后端 API 的通知
- 可以自定义通知设置，选择不同的通知类型
- 轻量、易于安装和配置
- 适用于使用 **Home Assistant** 和 **Gewechat** 的用户

## 安装

### 先决条件

- 确保你已安装 [Home Assistant](https://www.home-assistant.io/) 并已配置好 HACS（Home Assistant Community Store）。
- 本插件依赖 **Gewechat** 后端 API，请参阅 [Gewechat 部署文档](https://github.com/Devo919/Gewechat) 进行配置。

### 安装插件

1. 打开 Home Assistant 系统并进入 HACS。
2. 搜索 **Gewe-Notify** 插件，并点击 **安装**。
3. 安装完成后，重启 Home Assistant 系统。

### 配置 Gewechat 后端

Gewe-Notify 插件需要配合 **Gewechat** 后端 API 使用。请按照以下步骤部署和配置 **Gewechat** 后端：

1. 根据 [Gewechat 配置指南](https://github.com/Devo919/Gewechat) 完成后端部署。

## 使用方法

1. 在 Home Assistant 中，进入插件设置页面，找到 **Gewe-Notify** 插件。
2. 配置 Gewechat API 的地址。
3. 首次运行请执行 **Action --> gewe.fetch_contacts**, 可搭配`https://github.com/netcookies/gewe-notify-card`卡片查找target值
4. 在 Action 中找到**notify.gewe_notify**填入message和target。

## 贡献指南

欢迎大家为 **Gewe-Notify** 插件贡献代码！如果你希望参与开发，请遵循以下步骤：

1. Fork 本仓库。
2. 创建一个新的分支（`git checkout -b feature-branch`）。
3. 提交你的修改（`git commit -am 'Add new feature'`）。
4. 将更改推送到你的分支（`git push origin feature-branch`）。
5. 创建一个 Pull Request。

## 许可证

本项目使用 **MIT 许可证** - 详细信息请参见 [LICENSE](LICENSE) 文件。

## 感谢

- [Devo919/Gewechat](https://github.com/Devo919/Gewechat) 提供了后端 API。
- 感谢所有为 Gewe-Notify 和 Gewechat 项目做出贡献的开发者。

## 联系方式

如果你有任何问题或建议，欢迎提出 issue 或联系项目维护者。

---

### 说明

1. **项目描述**：介绍 **Gewe-Notify** 插件的功能，并指出它与 **Gewechat** 后端 API 的依赖关系。
2. **安装方法**：提供插件的安装方法以及 Gewechat 后端 API 的部署指南。
3. **使用方法**：详细说明如何配置和使用插件。
4. **配置**：介绍插件的配置项以及需要设置的 Gewechat API 信息。
5. **贡献指南**：如何为插件贡献代码。
6. **感谢**：特别感谢 **Gewechat** 提供的后端 API。
