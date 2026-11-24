# AStudio HTTP 协议证据

## 协议版本

- AStudio 桌面端：`3.6.0`
- 身份头：`studioVersion: 3.6.0`、`User-Agent: AStudio/3.6.0`
- 平台身份：Windows/Linux `clientType: 21`，macOS `clientType: 22`
- 协议目标：使用账号 Cookie 完成当天登录、领取奖励弹窗并回读两个积分池

本项目只实现完成互操作所需的公开 HTTP 事实，Python 脚本、测试、日志与错误模型均为独立实现。

## 官方产品与域名

| 项目 | 结论 |
| :--- | :--- |
| 产品名 | AStudio（科大讯飞 Astron Studio） |
| 账号面根地址 | `https://agent.xfyun.cn/xingchen-studio/` |
| 模型网关 | `https://astronstudio-api-volces-prod.xf-yun.com/model-gateway/v1/responses` |
| 模型目录 | `https://astronstudio-api-volces-prod.xf-yun.com/api/v1/model-manager/models` |

每日签到只使用账号面 `agent.xfyun.cn/xingchen-studio/`，不调用模型网关，也不消耗模型积分。

## 账号面接口

活跃触发和奖励领取不是只读 GET。当前账号面使用：

| 用途 | 方法 | 相对路径 | 请求体 |
| :--- | :--- | :--- | :--- |
| 每日活动配置 | `GET` | `membership/plan-config` | 无 |
| 通用/星火积分余额 | `GET` | `points/balance` | 无 |
| 桌面端账号初始化 | `POST` | `tenant-app/v2/init-app` | 无 |
| 待领取奖励弹窗 | `GET` | `client-popups/pending` | 无 |
| 完成奖励弹窗 | `POST` | `client-popups/complete` | JSON |

`membership/me` 与 `points/summary` 不再作为每日登录触发链路。查询会员或积分汇总不能替代
`init-app`。

### 请求头与客户端身份

账号面请求共同发送：

```http
Accept: application/json
Cookie: ssoSessionId=...; sso_sessionid=...; account_id=...; token=...
User-Agent: AStudio/3.6.0
studioVersion: 3.6.0
clientType: 21
```

`clientType` 默认值：

- Windows：`clientType: 21`
- Linux：`clientType: 21`
- macOS：`clientType: 22`
- 本地配置可通过 `ASTUDIO_CLIENT_TYPE` 显式覆盖

`init-app` 请求示例：

```http
POST /xingchen-studio/tenant-app/v2/init-app HTTP/1.1
Accept: application/json
Cookie: ssoSessionId=...; sso_sessionid=...; account_id=...; token=...
User-Agent: AStudio/3.6.0
studioVersion: 3.6.0
clientType: 21
```

该 POST 不附加 JSON、表单、multipart 或其他业务请求体。

现有协议证据中未发现独立 CSRF token 或 CSRF 请求头。极验用于短信发送和账号密码登录，不等同于 CSRF。

### Cookie 字段

Cookie 构造顺序与桌面端一致：

```text
ssoSessionId=<value>
sso_sessionid=<value>
account_id=<value>
token=<value>
```

其中 `ssoSessionId` 可选；`token` 与 `account_id` 是网页会话的必要字段。

## 响应信封

成功响应必须同时满足：

```json
{
  "flag": true,
  "code": 0,
  "data": {}
}
```

- `flag` 必须是布尔 `true`。
- `code` 必须是整数 `0` 或其等价字符串 `"0"`。
- `data` 必须存在且非 `null`；具体接口继续校验对象和必需字段。
- `client-popups/complete` 允许成功响应返回 `data: null`，其他接口仍要求数据完整。
- 非 2xx、`flag=false` 或非零 `code` 属于失败分支。

会话失效判定：

- HTTP `401` / `403` 直接判为会话失效。
- 仅在失败分支中，`code=80000` 或错误文案包含“重新登录”才判为会话失效。
- 成功信封即使文案包含“重新登录”，也不得被误判为会话失效。

`tenant-app/v2/init-app` 的 `data` 必须包含布尔字段 `banned`：

- `banned=false`：初始化成功。
- `banned=true`：账号封禁，直接失败。
- 缺失或非布尔 `banned`：响应数据不完整，直接失败。

## 余额字段

`points/balance` 的 `data` 使用：

- `totalBalance`：通用积分余额。
- `sparkTotalBalance`：星火积分余额。
- `activityBalance`：活动积分组成，可选。
- `activityNextExpireTime`：活动积分下一次到期时间，可选。

签到流程分别读取：

```text
before.totalBalance
before.sparkTotalBalance
after.totalBalance
after.sparkTotalBalance
```

判定规则：

- 单次响应中两个核心池都不可读：失败。
- 单个池缺失或无效时不能按 0 处理。
- 只有前后两值都存在时才能计算该池 delta。
- 任一池明确正增长：`observed`。
- 服务端确认奖励弹窗领取成功但两池均未刷新：`claimed`。
- 登录完成且没有待领取奖励：`done`。
- 奖励弹窗领取失败：`failed`，退出码非 0。
- 两池都无法形成前后配对：`failed`。

## 每日登录语义

每日登录由账号初始化和奖励弹窗两步共同完成：

```text
读取 membership/plan-config
  → 仅当 dailyLoginEnabled 是布尔 false：disabled
  → dailyLoginEnabled 非布尔或缺失：继续探测
  → 读取 points/balance 的 totalBalance 与 sparkTotalBalance 前值
  → POST tenant-app/v2/init-app，Cookie，无 body
  → GET client-popups/pending
  → 过滤 componentType=DAILY_REWARD_DIALOG 或 popupCode 含 REWARD 的项
  → POST client-popups/complete，JSON {popupId, instanceKey, completed:true}
  → 等待 2.5 秒
  → 再读取两个积分池
  → 任一池正增长：observed
  → 已确认领取但余额未刷新：claimed
  → 没有待领取项：done
  → 领取失败：failed
```

`dailyLoginEnabled` 的关闭条件严格限定为布尔 `false`。数字 `0`、字符串 `"false"`、
`null` 等非布尔值不会静默跳过，而是继续执行初始化探测。

初始化成功只证明桌面端账号初始化完成，不证明奖励到账。领取成功也只证明服务端接受了
奖励弹窗完成请求；只有余额正增长才报告 `observed`。

## 账号隔离与请求安全

- 每个账号请求使用独立 Session，避免 Cookie Jar 跨账号串联。
- 账号 Cookie 由当前账号显式构造并随请求发送。
- 所有账号面请求禁用重定向，避免 Cookie 被带到非目标主机。
- 网络错误、服务端文案和账号状态在输出前脱敏。
- 不读取 AStudio 桌面端本地文件，不持久化网页凭据。

## 登录流程与极验

本项目不执行账号密码登录，只消费已经取得的网页 Cookie。登录协议仅记录用于解释凭据来源：

| 操作 | 方法与路径 | 要求 |
| :--- | :--- | :--- |
| 读取极验配置 | `GET chat/gee-captcha` | 极验初始化 |
| 发送短信验证码 | `POST login/mobile/send-verify-code` | multipart；需要极验三件 |
| 手机号验证码登录 | `POST login/phone-quick-login` | mobile、verifyCode、countryCode；不需要极验 |
| 账号密码登录 | `POST login/check-account` | multipart；需要极验三件 |
| 初始化租户 App | `POST tenant-app/v2/init-app` | Cookie；无请求体 |
| 用户信息 | `GET userInfo` | Cookie |
| 模型凭据 | `GET bot/models/configs` | Cookie |

极验字段：

```text
geetest_challenge
geetest_validate
geetest_seccode = base64(服务端 seccode)
```

## 离线回归

当前仓库包含 52 项 unittest，覆盖：

- 无 body POST `tenant-app/v2/init-app`；
- 奖励弹窗过滤、`client-popups/complete` JSON 与空 `data`；
- `flag=true`、`code=0`、`data` 完整与 `banned` 校验；
- `totalBalance` / `sparkTotalBalance` 双池独立增长判定；
- `observed` / `claimed` / `done` / `failed` 状态语义与退出码；
- `dailyLoginEnabled` 仅布尔 false 关闭；
- Windows/Linux 21、macOS 22；
- 401/403/80000、失败分支“重新登录”、成功信封误判保护；
- 多账号 Session 隔离、禁重定向与脱敏。

## 未采用项

- 不使用 `modelBearerToken` 完成每日签到；它只覆盖模型调用。
- 不读取桌面端数据目录。
- 不把非奖励类推广弹窗当作签到奖励。
- 不把初始化成功解释成奖励到账。
- 不把服务端确认领取解释成余额已经到账。
