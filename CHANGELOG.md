# Changelog

所有重要变更记录在这里。版本号遵循语义化版本。

## [1.2.0] - 2026-11-24

### Fixed

- 修复只调用 `tenant-app/v2/init-app` 导致“面板显示登录完成、积分余额不变”的假成功。
- 补齐真实发奖链路：`client-popups/pending` → 过滤 `DAILY_REWARD_DIALOG` / `REWARD` 推广位 → `client-popups/complete`。
- 领取请求使用 JSON `{popupId, instanceKey, completed:true}`，并允许 `complete` 接口返回 `data=null`。
- 余额正增长报告 `observed`；服务端确认领取但余额暂未刷新报告 `claimed`；没有待领取项报告 `done`。

### Changed

- AStudio 桌面身份升级到 `studioVersion=3.6.0`、`User-Agent=AStudio/3.6.0`。
- Windows 和 Linux 默认 `clientType=21`，macOS 默认 `22`，确保奖励弹窗接口不会返回 `11001001`。
- README、PROTOCOL 和六语文档同步真实签到链路。

### Tests

- 完整离线回归共 52 项 unittest。
- 新增奖励弹窗过滤、`complete` JSON、服务端确认领取、无待领取项和身份头回归。
- `ruff`、`py_compile`、Markdown 相对链接与 `git diff --check` 通过。

### Notes

- 本轮未使用真实 AStudio 账号执行线上领取；首次线上运行仍需以服务端奖励回执和余额回读为准。

## [1.1.0] - 2026-11-05

### Changed

- 桌面端身份升级到 AStudio `3.5.1`，实施账号初始化增量。
- 活跃触发改为无 body `POST tenant-app/v2/init-app`，不再使用 `membership/me` 与 `points/summary` 冒充签到动作。
- 账号面统一发送 `studioVersion: 3.5.1`；Windows 默认 `clientType=21`、macOS `22`，Linux 默认不发送。
- 签到前后同时读取 `totalBalance` 与 `sparkTotalBalance`，任一池明确正增长才报告 `observed`。
- 初始化成功但两池均无正增长改为 `failed`，进程退出码为 `1`。
- `dailyLoginEnabled` 仅布尔 `false` 关闭；数字、字符串、`null` 等非布尔值继续探测。
- 成功响应必须同时满足 `flag=true`、`code=0`、`data` 完整；`init-app` 还要求 `banned=false`。
- 会话文案“重新登录”仅在非 2xx、`flag=false` 或非零 `code` 的失败分支触发会话失效。
- README、PROTOCOL、六语文档和协议摘要全部同步到 `v1.1.0`。

### Fixed

- 修复零增长被标为中性并返回退出码 `0` 的问题。
- 修复 Linux/Ubuntu Actions 默认伪装 `clientType=21` 的问题。
- 修复成功信封文案含“重新登录”时被误判为会话失效的问题。
- 继续使用独立 Session、禁重定向和凭据脱敏，避免多账号 Cookie 串联。
- 补充模拟 HTTP 回归，覆盖无 body POST、双池、严格信封、封禁、会话失效、平台身份头和退出码。

### Tests

- 完整离线回归共 49 项 unittest。
- `ruff`、`py_compile`、GitHub Actions YAML 解析与 `git diff --check` 纳入发版前验证。

### Notes

- 未 commit、未 push、未创建 Release。

## [1.0.0] - 2026-11-04

### Added

- 依据 AStudio（科大讯飞 Astron Studio）HTTP 契约，完成独立 Python 实现。
- 单文件 `astudio_daily.py`，支持多账号 Cookie、账号文件、完整 Cookie、四段管道格式和 JSON 格式。
- `--query`、`--only`、`--no-notify` 命令行能力；查询模式只读配置与余额，不调用活跃触发接口。
- `membership/plan-config` 的 `dailyLoginEnabled` 活动开关检查。
- `points/balance` 签到前余额回读。
- `membership/me` 与 `points/summary` 会话活跃触发。
- 等待后 `points/balance` 二次回读；仅把余额真实增加报告为 `observed`，不推断增长来源。
- 已签/未观测到发放采用中性状态，不伪造成功。
- PushPlus、Bark、企业微信群机器人推送。
- 日志、账号状态和 API 错误的凭据脱敏。
- Daily Signal README、NOTICE、MIT License、六语导航文档和二维码资产。
- GitHub Actions 手动日任务与独立测试 workflow。
- 34 项离线 unittest，覆盖账号解析、HTTP 信封、会话失效、活动开关兼容、余额增长观测、CLI、脱敏与通知。

### Security

- HTTP 请求不跟随重定向，避免 Cookie 被带到非目标主机。
- 账号文件默认忽略；脚本不接受命令行明文凭据参数。
- `points/summary` 只用于触发活跃，不对未证实的响应结构作成功推断。

### Notes

- 本版本尚未使用真实账号执行线上签到。
- 未 commit、未 push、未创建 Release。
