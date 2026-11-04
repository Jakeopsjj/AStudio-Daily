<div align="center">

<sub><strong>L0NE-6 · DAILY SIGNAL</strong></sub>

# 🛰️ AStudio Daily

**AStudio（科大讯飞 Astron Studio）每日登录积分观测工具。多账号 Cookie、余额前后回读、活跃触发与中性失败语义。**

[简体中文](README.md) · [English](docs/README.en.md) · [繁體中文](docs/README.zh-Hant.md) · [日本語](docs/README.ja.md) · [한국어](docs/README.ko.md) · [Português (BR)](docs/README.pt-BR.md)

<img src="https://img.shields.io/github/v/release/L0NE-6/AStudio-Daily?style=for-the-badge&label=Release&color=2ea44f&logo=github" />
<img src="https://img.shields.io/github/stars/L0NE-6/AStudio-Daily?style=for-the-badge&label=Stars&color=FFC75F&logo=github" />
<img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" />
<img src="https://img.shields.io/badge/%E9%9D%92%E9%BE%99-Qinglong-4EAA25?style=for-the-badge" />
<img src="https://img.shields.io/badge/GitHub%20Actions-Supported-2088FF?style=for-the-badge&logo=githubactions&logoColor=white" />
<img src="https://img.shields.io/badge/License-MIT-F472B6?style=for-the-badge" />
<a href="https://github.com/L0NE-6/AStudio-Daily/releases"><img src="https://img.shields.io/badge/%E2%AC%87%20Download-Releases-2ea44f?style=for-the-badge&logo=github" /></a>

[✨ 30 秒速览](#-30-秒速览) · [🔑 账号格式](#-账号格式) · [🚀 青龙面板](#-青龙面板) · [☁️ GitHub Actions](#-github-actions) · [🔧 环境变量](#-环境变量) · [📡 协议证据](#-协议证据) · [❓ 常见问题](#-常见问题) · [✦ 星轨](#-星轨-star-trail)

</div>

---

## 🚫 使用边界

> [!IMPORTANT]
> **官方版本永久免费。** 未经作者书面许可，禁止付费包装、搬运引流、冒充作者，或使用作者身份与二维码制造官方授权假象。

本项目与科大讯飞、讯飞星火、Astron Studio 或 AStudio 官方无隶属关系。完整转载规则、clean-room 说明和凭据边界见 **[NOTICE.md](NOTICE.md)**。

---

## ✨ 30 秒速览

| 维度 | 说明 |
| :--- | :--- |
| **用途** | 触发 AStudio 当天网页会话活跃，并观测每日登录积分是否实际到账。 |
| **输入** | 一个或多个 AStudio 网页会话 Cookie。 |
| **输出** | 账号级前后余额、增量、中性状态和可选推送。 |
| **部署** | 青龙面板、GitHub Actions、Windows / Linux 本地运行。 |
| **依赖** | Python 3.8+ 与 `requests`。 |
| **观察判据** | 只有签到后 `totalBalance` 大于签到前余额，才报告 `observed`；不推断增长来源。 |
| **无变化** | 报告 `unchanged` 中性；可能是今日已签，也可能是尚未发放。 |
| **活动关闭** | `dailyLoginEnabled=false` 时报告 `disabled` 中性。 |

## ✨ 核心能力

- **多账号 Cookie**：支持完整 Cookie、管道格式、JSON 数组和账号文件。
- **活跃开关对齐**：先读取 `membership/plan-config`；仅明确 false 值视为活动关闭，其他值沿用上游继续触发。
- **前后余额回读**：签到前读取 `points/balance`，等待后再次读取并比较 `totalBalance`。
- **真实活跃触发**：依次请求 `membership/me` 与 `points/summary`，不调用未证实的领取接口。
- **不伪造成功**：余额不变只报中性，不写“已签成功”。
- **状态脱敏**：不打印 Cookie、token、完整 account_id、ssoSessionId 或 UID。
- **重定向隔离**：API 请求不跟随 3xx，避免 Cookie 被带往非目标主机。
- **多渠道推送**：PushPlus、Bark、企业微信群机器人，配置哪个发哪个。

## 🧩 工作流程

```text
读取 Cookie
  → GET membership/plan-config
  → dailyLoginEnabled=false：中性结束
  → GET points/balance（前值）
  → GET membership/me
  → GET points/summary
  → 等待 2.5 秒
  → GET points/balance（后值）
  → 后值 > 前值：observed
  → 后值未增加：unchanged
```

没有独立 claim 请求。签到依赖账号会话当天的首次活跃发放。

## 🔑 账号格式

### 方式一：四段管道

```text
备注|token|account_id|ssoSessionId
```

没有 `ssoSessionId` 时可写：

```text
备注|token|account_id
```

### 方式二：完整 Cookie

```text
token=TOKEN; account_id=ACCOUNT_ID; ssoSessionId=SSO_SESSION_ID
```

### 方式三：JSON

```json
[
  {
    "name": "主号",
    "session": {
      "token": "TOKEN",
      "accountId": "ACCOUNT_ID",
      "ssoSessionId": "SSO_SESSION_ID"
    }
  }
]
```

多账号可以用换行或 `&` 分隔。示例文件见 [astudio_accounts.example.txt](astudio_accounts.example.txt)。

> [!WARNING]
> `astudio_accounts*`（示例文件除外）、`.env` 和运行结果默认被 `.gitignore` 排除。不要把真实 Cookie 提交到仓库、Issue、Release 或 Actions 日志。

## 🚀 青龙面板

1. 安装依赖：

   ```bash
   pip3 install -r requirements.txt
   ```

2. 上传 `astudio_daily.py`。
3. 设置环境变量 `ASTUDIO_COOKIES`，或使用同目录 `astudio_accounts.txt`。
4. 新建任务：

   ```bash
   task astudio_daily.py
   ```

建议 cron：

```cron
17 9 * * *
```

实际执行时间应结合账号所在时区和官方发放策略调整。

## ☁️ GitHub Actions

仓库内置 [`.github/workflows/daily.yml`](.github/workflows/daily.yml)，默认只保留 `workflow_dispatch` 手动触发。

| Secret | 必填 | 说明 |
| :--- | :---: | :--- |
| `ASTUDIO_COOKIES` | 是 | 多账号 Cookie，换行或 `&` 分隔。 |
| `PUSHPLUS_TOKEN` | 否 | PushPlus。 |
| `BARK_URL` | 否 | Bark。 |
| `WECOM_WEBHOOK` | 否 | 企业微信群机器人。 |

需要定时执行时，在 `daily.yml` 取消以下注释：

```yaml
schedule:
  - cron: "17 1 * * *"
```

该 cron 使用 UTC，对应北京时间 09:17。

## 🔧 环境变量

| 变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `ASTUDIO_COOKIES` | 无 | 环境变量形式的账号配置。 |
| `ASTUDIO_ACCOUNT_FILE` | 无 | 账号文件路径；未设置时尝试脚本同目录的 `astudio_accounts.txt`。 |
| `ASTUDIO_PROXY` | 无 | 可选 HTTP(S) 代理。 |
| `ASTUDIO_TIMEOUT` | `20` | 单次 HTTP 超时，秒。 |
| `ASTUDIO_WAIT_SECONDS` | `2.5` | 活跃触发后的余额复查等待时间。 |
| `PUSHPLUS_TOKEN` | 无 | PushPlus token。 |
| `BARK_URL` | 无 | Bark URL。 |
| `WECOM_WEBHOOK` | 无 | 企业微信机器人完整 URL 或 key。 |

参考仓库没有提供名为 `XingChen` 的独立推送渠道，因此本项目不虚构对应环境变量。

## ⌨️ 命令行参数

| 参数 | 作用 |
| :--- | :--- |
| （无） | 运行全部账号并观测签到。 |
| `--query` | 只查询 `plan-config` 与余额，不调用 `membership/me` 或 `points/summary` 活跃触发。 |
| `--only N[,N\|A-B]` | 只运行指定序号，例如 `1`、`1,3`、`1-3`。 |
| `--no-notify` | 关闭本轮推送。 |
| `--version` | 输出版本。 |

## 📊 状态语义

| 状态 | 含义 |
| :--- | :--- |
| `observed` | 前后余额真实增加；只证明本轮观察到增长，不区分登录发放、活动、充值或并发任务来源。 |
| `unchanged` | 余额未增加；可能已签或尚未发放，本次不确认成功。 |
| `disabled` | `dailyLoginEnabled=false`，当前未启用活动。 |
| `query` | 仅查询，未执行活跃触发。 |
| `failed` | 会话失效、HTTP/业务错误、余额字段缺失，或活跃触发与余额复查无法形成完整证据。 |

脚本退出码：存在 `failed` 时为 `1`，配置错误为 `2`，其余为 `0`。

## 📡 协议证据

完整端点、Cookie、请求头、响应信封、极验与设备要求见 [docs/PROTOCOL.md](docs/PROTOCOL.md)。

核心事实：

- 产品：`AStudio（科大讯飞 Astron Studio）`
- 账号面：`https://agent.xfyun.cn/xingchen-studio/`
- Cookie：`ssoSessionId`、`sso_sessionid`、`account_id`、`token`
- 日常接口：`Accept: application/json` + `Cookie`
- 登录接口：Windows `clientType=21`、macOS `22`、`studioVersion=3.5.1`
- 极验：短信发送与账号密码登录需要；手机号验证码登录本身不需要
- CSRF：参考证据中未发现独立 CSRF token/header

## 🧪 测试与验证

```bash
python -m unittest discover -s tests -v
python -m py_compile astudio_daily.py tests/test_astudio_daily.py
```

测试覆盖：

- 账号格式与 Cookie 顺序；
- 成功/失败响应信封；
- 会话失效业务码；
- `dailyLoginEnabled` 明确 false 与兼容值；
- 只有余额增加才确认成功；
- 余额不变的中性状态；
- `--query` 不调用已识别的活跃触发接口；
- 日志与错误脱敏；
- PushPlus 与企业微信请求格式。

离线测试通过不等同于真实账号必然签到成功。首次线上运行应以脚本输出的前后余额和账号实际积分页为准。

## 🔒 隐私说明

- 不包含真实凭据或个人数据。
- 不接受命令行明文 Cookie。
- 不读取 AStudio 桌面端本地文件。
- 不把原始 API 错误体写入报告。
- 不打印完整账号 ID、UID、token 或 Cookie。
- 不跟随 API 重定向。

## ❓ 常见问题

<details>
<summary><b>为什么余额没涨却可能已经签到</b></summary>

每日积分是服务端在当天账号会话首次活跃时发放。你手动打开官方客户端或前一天/更早已触发过会话时，本轮第一次读取就可能已经包含当日积分，因此前后余额不变。脚本只能确认本轮观测到的增量，不会把没有发生在本轮的增加算作成功。
</details>

<details>
<summary><b>为什么只有 Cookie 也能运行</b></summary>

余额、会员与每日登录积分都走 `agent.xfyun.cn/xingchen-studio/` 网页会话。`modelBearerToken` 只用于模型调用，本签到流程不依赖它。
</details>

<details>
<summary><b>Cookie 多久失效</b></summary>

参考实现未发现续期接口。HTTP 401/403、业务码 `80000` 或响应提示重新登录时，需要重新获取 Cookie。
</details>

<details>
<summary><b>为什么 `points/summary` 不参与已签判断</b></summary>

参考证据只证明该接口可用于触发会话活跃，没有足够字段证据支持“今日已签”的结构化推断。脚本只把它作为活跃触发，不把未知结构猜成签到状态。
</details>

<details>
<summary><b>多账号顺序如何计算</b></summary>

`--only` 按最终合并后的账号列表计数。`ASTUDIO_COOKIES` 中的账号在前，账号文件中的新账号随后；重复凭据会自动去重。
</details>

## 📦 版本

- 当前脚本版本：`v1.0.0`
- 基线：`Agent2Providers v3.4.1`
- 变更记录：[CHANGELOG.md](CHANGELOG.md)

## ⚠️ 免责声明

本项目用于个人自动化实践与协议互操作研究。请遵守 AStudio 及相关平台的服务条款，并自行承担账号、网络、Cookie 有效期和自动化使用风险。

## ☕ 支持与反馈

遇到 Cookie 失效、字段变更或余额语义问题，请附脱敏日志、AStudio 版本、运行时间和复现步骤提交 Issue。

<p align="center">
  <img src="assets/donate-wechat.png" width="260" alt="微信赞赏码" />
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <img src="assets/donate-alipay.jpg" width="260" alt="支付宝赞赏码" />
</p>
<p align="center"><sub>💚 微信支付（左） &nbsp;|&nbsp; 💙 支付宝（右）</sub></p>

---

## ✦ 星轨 Star Trail

> 每颗 Star 都是一枚方位信号，标记 AStudio Daily 在会话触发、余额回读与诚实状态之间的航迹。

<a href="https://star-history.com/#L0NE-6/AStudio-Daily&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=L0NE-6/AStudio-Daily&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=L0NE-6/AStudio-Daily&type=Date&theme=light" />
    <img alt="AStudio Daily Star Trail" src="https://api.star-history.com/svg?repos=L0NE-6/AStudio-Daily&type=Date&theme=light" />
  </picture>
</a>

---

<div align="center">
  <a href="https://github.com/L0NE-6/AStudio-Daily/releases">Releases</a> ·
  <a href="https://github.com/L0NE-6/AStudio-Daily/issues">Issues</a> ·
  <a href="https://github.com/L0NE-6/AStudio-Daily">Star</a>
  <br />
  <sub>L0NE-6 · DAILY SIGNAL · 会话有触发，余额有复核，没涨不报成功</sub>
</div>
