# Changelog

所有重要变更记录在这里。版本号遵循语义化版本。

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
