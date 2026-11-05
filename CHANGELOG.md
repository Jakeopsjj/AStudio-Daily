# Changelog

所有重要变更记录在这里。版本号遵循语义化版本。

## [1.1.0] - 2026-11-05

### Changed

- 基线升级到 `Agent2Providers v3.4.2` / `3055f416841c1393ec04294a702603fd41e840aa`，实施 AStudio 桌面端初始化增量。
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

- 基于 `Agent2Providers v3.4.1` 的 AStudio（科大讯飞 Astron Studio）HTTP 契约证据，完成独立 Python clean-room 实现。
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
