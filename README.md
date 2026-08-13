# 📮 XHS Sender — 小红书私信自动化发送系统
![GitHub图像](https://github.com/evi1s/XHS_sender/blob/main/xiaohongshu-e1677589496301.jpg)

> Docker 一键部署 · NiceGUI 可视化面板 · MCP 协议接入（Chatbox / Claude 等 AI 客户端）

XHS Sender 是一套**开箱即用的小红书私信自动化发送系统**。客户在自己服务器上通过 `docker compose up -d` 一键部署，即可拥有：

- 🖥️ **NiceGUI 可视化控制面板** —— 设备管理、接收方管理、文案管理、任务执行、健康检查，全部网页操作
- 🤖 **MCP Server** —— 接入 Chatbox / Claude / 任意支持 MCP 的 AI 客户端，**用自然语言直接发私信**
- 🔐 **服务端分离架构** —— 发送通道由独立服务端提供（API Key 鉴权），客户数据（设备、接收方、文案）**完全保存在自己的 MongoDB 中**

---

## 📦 功能特性

| 功能 | 说明 |
|---|---|
| 🚀 Docker 一键部署 | MongoDB 7 + 应用服务，一条命令启动 |
| 🖥️ NiceGUI 控制面板 | 设备 / UserId / 文案 / 短链 / 授权 / 设置 / 任务执行 |
| 🤖 MCP Server | FastMCP 实现，支持 Chatbox / Claude 等 MCP 客户端远程调用 |
| 🩺 健康检查机制 | 发送前通过检测号验证通道可用性，降低风控风险 |
| 🛡️ 接收方防丢失 | 领取-成功删除-失败退回，进程崩溃也不丢数据 |
| 📊 系统概览 | 主页仪表盘：设备数 / 今日使用量 / 接收方数 / 内存 / 网络 / 服务端状态 |
| 🌗 亮暗双主题 | 适配不同使用环境 |
| 🔑 多 Key 计费 | 对接服务端多租户鉴权，按月/季收费 |

---

## 🏗️ 架构说明

```
┌─────────────────────────────────────────────────────────┐
│                    客户服务器（本部署包）                  │
│                                                         │
│  [NiceGUI 面板 :8080]  ──┐                              │
│  [MCP Server   :8090]  ──┼──→ [MongoDB :27017]          │
│                          │      (设备/接收方/文案/用量)    │
└──────────────────────────┼──────────────────────────────┘
                           │  HTTPS + X-API-Key
                           ▼
                ┌──────────────────────┐
                │  XHS 发送服务端（收费）│
                │  协议层 / 执行器 /    │
                │  多租户鉴权与计费     │
                └──────────────────────┘
```

**关键设计**：

- **客户端（本仓库）**：负责 UI、任务调度、数据存储（客户自己的 MongoDB）、MCP 封装。**已开源**。
- **服务端（不公开）**：负责小红书协议连接、IP 获取、健康检查、消息发送执行、按 Key 计费。**仅提供服务**。
- 客户只需购买服务端 **API Key**，按月/季付费，数据始终在自己的服务器上。

---

## 📁 目录结构

```
xhs_docker_pkg/
├── docker-compose.yml      # 一键编排（MongoDB + App）
├── Dockerfile              # Python 3.12 应用镜像
├── requirements.txt        # 依赖清单
├── entrypoint.sh           # 启动脚本（等待 Mongo → 启动 MCP + NiceGUI）
├── .env.example            # 环境变量模板（复制为 .env 后填写）
├── MCP_GUIDE.md            # MCP 客户操作指南（可转发给客户）
└── app/                    # 应用源码
    ├── nicegui_app.py      # NiceGUI 主程序（控制面板 + 仪表盘）
    ├── xhs_mcp_server.py   # MCP Server（FastMCP）
    ├── main_sse.py         # 任务执行核心（调度/重试/防丢失）
    ├── config.py           # 环境变量配置（零硬编码）
    ├── database.py         # MongoDB 连接
    ├── runapp.py           # 任务执行页面
    ├── devices/            # 设备管理模块
    ├── settings.py         # 软件设置页面
    ├── adduserid.py        # UserId（接收方）管理
    ├── addtext.py          # 文字消息（文案）管理
    ├── authorize.py        # 授权设置
    ├── setproxy.py         # 代理设置
    ├── setcard.py          # 卡片模板
    ├── xhs_shorturl.py     # 短链生成
    ├── auth.py             # 登录鉴权
    └── DeviceManager.py    # 发送设备管理器
```

---

## 🚀 快速开始

### 环境要求

| 依赖 | 要求 |
|---|---|
| 操作系统 | Linux（推荐） / macOS / Windows（Docker Desktop） |
| Docker | 20.10+ |
| Docker Compose | v2 |
| 内存 | ≥ 2GB（建议 4GB） |
| 磁盘 | ≥ 5GB |
| 前置条件 | 已购买服务端 API Key（`PROXY_API_KEY`） |

### 第一步：获取代码

```bash
git clone https://github.com/evi1s/XHS_sender.git
cd xhs_sender
```

### 第二步：配置环境变量

```bash
cp .env.example .env
vim .env
```

### 第三步：启动

```bash
docker compose up -d
# 等待约 30~60 秒（首次需构建镜像 + 初始化 MongoDB）
docker compose ps
# 期望看到：
#   xhs_mongo   Up (healthy)
#   xhs_app     Up
```

### 第四步：访问

| 服务 | 地址 | 说明 |
|---|---|---|
| NiceGUI 面板 | `http://<服务器IP>:8080` | 默认账号 `admin` / `admin123456`（可在 .env 修改） |
| MCP Server | `http://<服务器IP>:8090/mcp` | 供 Chatbox / Claude 等客户端接入 |

> 如果8080端口被占用，修改 `.env` 中 `WEB_PORT` / `MCP_PORT` 后 `docker compose up -d` 重启。

---

## ⚙️ 环境变量详解（.env）

| 变量 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `MONGO_ROOT_USERNAME` | ✅ | `root` | MongoDB 管理员账号 |
| `MONGO_ROOT_PASSWORD` | ✅ | - | MongoDB 管理员密码（**请修改为强密码**） |
| `MONGO_DB_NAME` | ✅ | `xhs_demo` | 业务数据库名 |
| `PROXY_SERVER_URL` | ✅ | - | **服务端地址**，例如 `http://api.example.com/execute-task`（找服务商获取） |
| `PROXY_API_KEY` | ✅ | - | **服务端 API Key**（购买后获得，按 Key 计费） |
| `ADMIN_USERNAME` | - | `admin` | 控制面板登录账号 |
| `ADMIN_PASSWORD` | - | `admin123456` | 控制面板登录密码（**请修改**） |
| `CHECK_USER_ID` | ✅ | - | 健康检查检测号 UserId（用于发送前通道验证） |
| `WEB_PORT` | - | `8080` | 面板宿主机映射端口 |
| `MCP_PORT` | - | `8090` | MCP Server 宿主机映射端口 |
| `STORAGE_SECRET` | - | 随机 | NiceGUI 会话加密密钥 |
| `README_URL` | - | 空 | 主页公告地址（可指向自建公告页面） |
| `COOKIE_REMOTE_URL` | - | 空 | 短链生成远程服务地址（可自建） |

---

## 🖥️ 控制面板使用说明

### 登录
访问 `http://<IP>:8080`，使用 `.env` 中 `ADMIN_USERNAME` / `ADMIN_PASSWORD` 登录。
![GitHub图像](https://github.com/evi1s/XHS_sender/blob/main/%E7%95%8C%E9%9D%A2.jpg)

### 主页（仪表盘）
实时显示：**设备数量 / 今日使用量 / 接收方数量 / 系统内存 / 网络状态 / 服务端连接状态**（服务端状态带 Key 有效性检测，绿色=正常）。

### 设备管理
添加发送设备（昵称、UserId、DeviceId、Session 等），支持启用/停用、健康检测开关。**发送设备数据仅保存在你的 MongoDB**。
添加小红书的账号信息，这些信息都可以使用抓包工具抓取。如果勾选“健康检测号”则把该账号作为健康检测使用。
（抓包工具：windows端：Reqable，ios端：ProxyPin，设置好抓包，再打开小红书即可，在抓包工具中可以选择筛选链接：
api/im/v3/chats/info?chat_user_ids=，/api/sns/v1/user/login/acct_group/list）
具体抓包详细见(###抓包方法)

### 消息发送模式：
可选择发送“卡片”消息，“文本”消息，“卡片加文本”消息。小红书默认对陌生人只能发送一个消息。


### 客户管理(UserId)
维护接收方列表（支持批量添加），任务发送时自动领取未发送的接收方，**成功才消费、失败自动退回**。
添加接收方的userid，批量发送给对方的账号，此处内容自行挖掘。


### 文字消息
发送给接收方的文字消息，只作为文字内容发送，可以加入微信号，手机号，广告语等。

### 卡片消息
发送给接收方的卡片消息，卡片可以设置封面，广告词，点击之后即可跳转到微信加好友或者指定网站。默认格式，修改需注意。

### 任务执行
一键启动发送任务：自动获取可用设备信息 → 领取接收方 → 健康检查（hi 消息检测）→ 发送私信 → 记录用量。


### 软件设置
数据库连接参数、任务与连接参数（重试次数、间隔等）、集合名称配置。
基本都为默认设置。非必要不做修改即可。其中成功冷却时间的作用为发送私信消息成功后，休息的时间，用于避免封号。
首次失败冷却时间的作用为在测试发健康检测消息，如果健康检测号无法收到消息，则自动冻结24小时。（默认）
连续失败冷却时间的作用为在测试发送健康检测消息，连续2天都无法成功发送私信消息，则自动冻结30天。（默认）



### 短链生成 / 授权设置
用于生成小红书的跳转链接，生成的小红书链接填入到“卡片消息”中。以实现跳转。（需 `COOKIE_REMOTE_URL`）与授权信息维护。

### 抓包方法

![GitHub图像](https://github.com/evi1s/XHS_sender/blob/main/xhs%E6%8A%93%E5%8C%85.png)

------

## 🤖 接入 Chatbox（MCP）

> 📄 **客户操作指南**：完整的分步操作（端口放行、首次准备、对话示例、常见问题、安全提醒）见 **[MCP_GUIDE.md](./MCP_GUIDE.md)**，可直接转发给客户。

### 方式一：一键安装链接（推荐）

服务商可生成专属安装链接，Chatbox 点击即装：

```
chatbox://mcp/install?server=<base64编码的JSON>
```

JSON 格式：

```json
{"name": "xhs-sender", "url": "http://<你的服务器IP>:8090/mcp"}
```

### 方式二：手动添加

1. 打开 Chatbox → **设置** → **MCP** → **添加服务器**
2. 类型选择 **远程（HTTP）**
3. URL 填 `http://<你的服务器IP>:8090/mcp`
4. 测试连接 → 保存

### 可用工具

| 工具 | 说明 |
|---|---|
| `xhs_send_next` | 自动领取一个发送设备 + 一个接收方，调用服务端发送私信 |
| `xhs_list_devices` | 列出本机 MongoDB 中全部发送设备 |
| `xhs_server_status` | 查看服务端连接状态与 Key 是否有效 |
| `xhs_add_receiver` | 将接收方 UserId 加入待发送队列 |

### 对话示例

> 💬 “帮我给下一个用户发一条私信”
> 💬 “查看一下我的服务端连接状态”
> 💬 “添加 6931587600000000xxxxx 到接收队列”

---

## 🩺 健康检查机制（hi 检测）

发送正式私信前，系统会执行健康检查：

```
服务端 → 发送设备 → 向检测号发送 "hi"
检测号（checker 子进程）收到 → 写入 check_status
服务端确认 ok → 继续发送正式私信
失败 → 自动终止任务，接收方退回队列（不丢失）
```

- 检测号 UserId 在 `.env` 的 `CHECK_USER_ID` 配置
- 该机制显著降低因通道异常导致的发送失败与风控风险

- ⚠️⚠️健康检查之前，需要发私信的小红书号要给自己的主号（检测号）发一个消息，主号再回复一个任意消息，这样就从陌生人列表中拉出。为后续风控检测做判断的。
- ⚠️⚠️

---

## ❓ 常见问题（FAQ）

### 1. 启动后 xhs_mongo 一直 unhealthy？
检查 `.env` 中 `MONGO_ROOT_PASSWORD` 是否为空或包含特殊字符，然后：
```bash
docker compose down -v   # 注意：会清空数据卷！
docker compose up -d
```

### 2. 面板显示"服务端连接：状态码 401 无效key"？
- 401 且提示缺少 Key：`.env` 中 `PROXY_API_KEY` 未填
- 401 且提示无效：Key 错误、过期或已被暂停，联系服务商

### 3. 面板显示"服务端连接：无法连接"？
- `PROXY_SERVER_URL` 填错（需完整的 `/execute-task` 地址）
- 服务器出站网络被限制（部分机房需放行）

### 4. 端口 8080 被占用？
修改 `.env` 的 `WEB_PORT` / `MCP_PORT` 后重启。

### 5. 任务失败提示"套餐已过期 / 次数已用完"？
联系服务商续费充值，续费后自动恢复。

### 6. 如何备份数据？
MongoDB 数据在 Docker 卷 `xhs_docker_pkg_mongo_data`：
```bash
docker run --rm -v xhs_docker_pkg_mongo_data:/data -v $(pwd):/backup alpine tar czf /backup/mongo_backup.tar.gz -C /data .
```

---

## ⚠️ 免责声明

1. **合法使用**：本工具仅供合法合规场景使用（如客服通知、活动触达、自有用户维护等）。
2. **禁止滥用**：严禁用于骚扰、诈骗、垃圾广告、批量骚扰等违反平台规则或法律法规的行为。
3. **风险自负**：使用本工具产生的账号风险、平台处罚、法律后果由使用者自行承担。
4. **无担保**：本项目按现状提供，不对任何间接损失负责。

---

## 💳 购买服务端 API Key

客户端已开源，**发送通道由服务端提供**，需购买API Key：

| 套餐 | 价格 | 说明 |
|---|---|---|
| 按月 | 联系服务商 | 按自然月计费，到期自动停止 |
| 按季 | 联系服务商 | 3 个月，比月付更优惠 |
| 次数包 | 联系服务商 | 预付费次数，用完即止 |

- **联系渠道**：📧 m0s6f4@gmail.com / 💬 微信 ：
- 每个 Key 独立计费、独立任务流（多客户互不干扰）
- Key 过期/欠费时，客户端会明确提示"套餐已过期，请联系管理员续费"，接收方数据不会丢失

---

## 📄 License

本项目仅供学习与合法商业使用，禁止二次分发用于违法用途。
