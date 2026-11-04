# AStudio HTTP 协议证据

## 基线

- 仓库：`ProvidersPlugin/Agent2Providers`
- tag：`v3.4.1`
- commit：`604c4102d5becddc997052d997185a302ed9e74f`
- tag 时间：`2026-11-04T16:59:02+08:00`
- 许可证：AGPL-3.0
- 使用方式：只读 Rust 代码作为 HTTP 契约证据，不复制源码、目录结构、注释或内部抽象。

## 官方产品与域名

| 项目 | 结论 | 证据 |
| :--- | :--- | :--- |
| 产品名 | AStudio（科大讯飞 Astron Studio） | `README.zh-CN.md:44`、`README.zh-CN.md:55` |
| 账号面根地址 | `https://agent.xfyun.cn/xingchen-studio/` | `crates/providers/src/providers/astudio/endpoints.rs:30` |
| 模型网关 | `https://astronstudio-api-volces-prod.xf-yun.com/model-gateway/v1/responses` | `endpoints.rs:22-23` |
| 模型目录 | `https://astronstudio-api-volces-prod.xf-yun.com/api/v1/model-manager/models` | `endpoints.rs:26-27` |

每日签到只使用账号面 `agent.xfyun.cn/xingchen-studio/`，不需要调用模型网关，也不消耗模型积分。

## 账号面接口

所有账号面路径均为 `GET`，没有请求体。

| 用途 | 相对路径 | 证据 |
| :--- | :--- | :--- |
| 每日登录活动配置 | `membership/plan-config` | `checkin.rs:37`、`endpoints.rs:41` |
| 通用/星火积分余额 | `points/balance` | `checkin.rs:113-115`、`endpoints.rs:39` |
| 会员信息/活跃触发 | `membership/me` | `checkin.rs:71`、`endpoints.rs:40` |
| 积分汇总/活跃触发 | `points/summary` | `checkin.rs:72`、`endpoints.rs:42` |

### 请求头

签到和余额读取的账号面请求只显式设置：

```http
GET /xingchen-studio/<path> HTTP/1.1
Accept: application/json
Cookie: ssoSessionId=...; sso_sessionid=...; account_id=...; token=...
```

证据：`crates/providers/src/providers/astudio/client.rs:37-47`。

这些日常账号面请求没有显式 `clientType`、`studioVersion`、设备 ID 或 CSRF 头。

### Cookie 字段

Cookie 构造顺序与桌面端一致：

```text
ssoSessionId=<value>
sso_sessionid=<value>
account_id=<value>
token=<value>
```

其中 `ssoSessionId` 可选；`token` 与 `account_id` 是网页会话的必要字段。证据：`crates/providers/src/providers/astudio/accounts.rs:108-127`。

### 响应信封

账号面成功响应：

```json
{
  "flag": true,
  "code": 0,
  "data": {}
}
```

判定规则：

- HTTP `401` / `403`：会话失效。
- `code = 80000`：会话失效。
- `desc` 含“重新登录”：会话失效；“登录异常”单独出现时按普通业务错误处理。
- `flag = false`、非零 `code`、非 2xx HTTP：业务失败。
- 只有以上条件均满足才读取 `data`。

证据：`client.rs:52-83`。

### 余额字段

`points/balance` 的 `data` 至少使用：

- `totalBalance`：总余额，签到前后比较的核心字段。
- `activityBalance`：活动积分组成。
- `activityNextExpireTime`：活动积分下一次到期时间。
- `sparkTotalBalance`：星火积分余额。

证据：`checkin.rs:86-97`、`usage.rs:92-126`。

### 会员字段

`membership/me` 用于触发当天会话活跃，同时可显示：

- `planName`
- `uid`
- `endTime`

证据：`usage.rs:133-147`。

## 每日登录积分语义

上游没有独立领取接口。服务端在当天账号会话首次活跃时发放每日登录积分。参考实现采用：

```text
读取 membership/plan-config
  → dailyLoginEnabled == false：未启用
  → 读取 points/balance 前值
  → GET membership/me
  → GET points/summary
  → 等待 2.5 秒
  → 读取 points/balance 后值
  → 后值 > 前值：观察到本轮余额增长（不推断增长来源）
  → 后值未增加：不确认本轮有新发放
```

证据：`checkin.rs:37-110`。

本项目额外把“余额无变化”报告为中性 `unchanged`，文案明确“可能今日已签到或积分尚未发放”。不对 `points/summary` 的未知结构作“已签”推断。

## 登录流程与极验

本项目不执行账号密码登录，只消费已经取得的网页 Cookie。登录协议仅记录用于解释凭据来源：

| 操作 | 方法与路径 | 要求 |
| :--- | :--- | :--- |
| 读取极验配置 | `GET chat/gee-captcha` | 极验初始化 |
| 发送短信验证码 | `POST login/mobile/send-verify-code` | multipart；需要极验三件 |
| 手机号验证码登录 | `POST login/phone-quick-login` | mobile/verifyCode/countryCode；不需要极验 |
| 账号密码登录 | `POST login/check-account` | multipart；需要极验三件 |
| 初始化租户 App | `POST tenant-app/v2/init-app` | Cookie；无请求体 |
| 用户信息 | `GET userInfo` | Cookie |
| 模型凭据 | `GET bot/models/configs` | Cookie |

极验字段：

```text
geetest_challenge
geetest_validate
geetest_seccode = base64(上游 seccode)
```

登录流程请求显式带：

```http
clientType: 21
studioVersion: 3.5.1
```

`clientType` 在 Windows 为 `21`，macOS 为 `22`。证据：`auth.rs:3-28`、`auth.rs:36-107`、`auth.rs:244-333`。

未在参考代码中发现独立 CSRF token 或 CSRF 请求头。极验用于短信发送和账号密码登录，不等同于 CSRF。

## 未采用项

- 不使用 `modelBearerToken` 完成每日签到；它只覆盖模型调用。
- 不读取桌面端数据目录。
- 不实现无证据的“领取”请求。
- 不把未增加余额解释成成功。
- 不复制 AGPL 源码、结构或注释。
