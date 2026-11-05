# AStudio Daily

[简体中文](../README.md) · [English](README.en.md) · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Português (BR)](README.pt-BR.md)

**Trigger the AStudio (iFlytek Astron Studio) desktop account initialization and reconcile both credit pools with account cookies.**

## What it does

AStudio does not expose a separate daily-credit claim endpoint. The reference client triggers the daily flow with a bodyless `tenant-app/v2/init-app` POST.

This script:

1. reads `membership/plan-config`;
2. stops only when the boolean `dailyLoginEnabled` is `false`;
3. reads `totalBalance` and `sparkTotalBalance` before activation;
4. sends a bodyless `POST tenant-app/v2/init-app`;
5. waits 2.5 seconds;
6. reads both credit pools from `points/balance` again;
7. reports `observed` when either pool increases clearly.

If initialization succeeds but neither pool increases, the account is reported as `failed` and the process exits non-zero. A positive delta proves only that the balance changed; it does not identify the source.

## Account formats

Pipe format:

```text
name|token|account_id|ssoSessionId
```

Without `ssoSessionId`:

```text
name|token|account_id
```

Raw cookie:

```text
token=TOKEN; account_id=ACCOUNT_ID; ssoSessionId=SSO_SESSION_ID
```

Multiple accounts may be separated by newlines or `&`.

## Run

```bash
pip install -r requirements.txt
export ASTUDIO_COOKIES='name|TOKEN|ACCOUNT_ID|SSO_SESSION_ID'
python astudio_daily.py
```

Commands:

```bash
python astudio_daily.py --query
python astudio_daily.py --only 1,3
python astudio_daily.py --no-notify
```

## Environment

| Variable | Required | Purpose |
| :--- | :---: | :--- |
| `ASTUDIO_COOKIES` | yes* | Multi-account cookie payload. |
| `ASTUDIO_ACCOUNT_FILE` | optional | Path to an account file. |
| `ASTUDIO_PROXY` | optional | HTTP(S) proxy. |
| `ASTUDIO_CLIENT_TYPE` | optional | Overrides `clientType`. Defaults to `21` on Windows and `22` on macOS; omitted on Linux. |
| `ASTUDIO_TIMEOUT` | optional | Request timeout, default `20`. |
| `ASTUDIO_WAIT_SECONDS` | optional | Balance recheck delay, default `2.5`. |
| `PUSHPLUS_TOKEN` | optional | PushPlus. |
| `BARK_URL` | optional | Bark. |
| `WECOM_WEBHOOK` | optional | WeCom bot URL or key. |

\* `astudio_accounts.txt` may be used instead.

## Status

| Status | Meaning |
| :--- | :--- |
| `observed` | At least one credit pool increased in this run; the source is not inferred. |
| `disabled` | Daily login activity is disabled. |
| `query` | Read-only query mode. |
| `failed` | Session, HTTP, contract, unreadable balance, initialization failure, or zero growth after successful initialization. |

## HTTP contract

- Product: AStudio (iFlytek Astron Studio)
- API base: `https://agent.xfyun.cn/xingchen-studio/`
- Cookie names: `ssoSessionId`, `sso_sessionid`, `account_id`, `token`
- Daily reads: `GET membership/plan-config`, `GET points/balance`
- Activation: bodyless `POST tenant-app/v2/init-app` with the account cookie
- All account requests send `studioVersion: 3.5.1`
- `clientType` is `21` on Windows and `22` on macOS; Linux omits it unless `ASTUDIO_CLIENT_TYPE` overrides it
- Success requires `flag=true`, `code=0`, and complete `data`; `init-app` also requires `banned=false`
- GeeTest is required for SMS sending and password login
- No separate CSRF token/header is visible in the reference evidence

See [PROTOCOL.md](PROTOCOL.md) for source-level evidence.

## Version

- Script: `v1.1.0`
- Baseline: `Agent2Providers v3.4.2` / `3055f416841c1393ec04294a702603fd41e840aa`
- Offline regression: 49 unittest cases

## Security

- Credentials are read only from environment variables or an account file.
- API redirects are not followed.
- Tokens, cookies, full account IDs, and UIDs are not printed.
- Unit tests do not use a real account.

## License

MIT. The project is independent and is not affiliated with iFlytek or AStudio.
