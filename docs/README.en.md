# AStudio Daily

[简体中文](../README.md) · [English](README.en.md) · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Português (BR)](README.pt-BR.md)

**Observe AStudio (iFlytek Astron Studio) daily login credits with account cookies and honest balance reconciliation.**

## What it does

AStudio does not expose a separate daily-credit claim endpoint in the reference contract. The server grants the daily login credit when the account web session becomes active for the day.

This script:

1. reads `membership/plan-config`;
2. stops neutrally when `dailyLoginEnabled` is `false`;
3. reads `points/balance` before activation;
4. requests `membership/me` and `points/summary`;
5. waits 2.5 seconds;
6. reads `points/balance` again;
7. reports an observed increase when `totalBalance` actually rises.

An unchanged balance is reported as `unchanged`: the account may already have signed in, or the credit may not have arrived yet. A positive delta proves only that the balance changed; it does not identify the source.

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
| `ASTUDIO_TIMEOUT` | optional | Request timeout, default `20`. |
| `ASTUDIO_WAIT_SECONDS` | optional | Balance recheck delay, default `2.5`. |
| `PUSHPLUS_TOKEN` | optional | PushPlus. |
| `BARK_URL` | optional | Bark. |
| `WECOM_WEBHOOK` | optional | WeCom bot URL or key. |

\* `astudio_accounts.txt` may be used instead.

## Status

| Status | Meaning |
| :--- | :--- |
| `observed` | Balance increased in this run; the source is not inferred. |
| `unchanged` | No increase in this run; no success claim. |
| `disabled` | Daily login activity is disabled. |
| `query` | Read-only query mode. |
| `failed` | Session, HTTP, contract, or activation failure. |

## HTTP contract

- Product: AStudio (iFlytek Astron Studio)
- API base: `https://agent.xfyun.cn/xingchen-studio/`
- Cookie names: `ssoSessionId`, `sso_sessionid`, `account_id`, `token`
- Endpoints: `membership/plan-config`, `points/balance`, `membership/me`, `points/summary`
- Daily requests set only `Accept: application/json` and `Cookie`
- Login flows use `clientType` (`21` on Windows, `22` on macOS) and `studioVersion: 3.5.1`
- GeeTest is required for SMS sending and password login
- No separate CSRF token/header is visible in the reference evidence

See [PROTOCOL.md](PROTOCOL.md) for source-level evidence.

## Security

- Credentials are read only from environment variables or an account file.
- API redirects are not followed.
- Tokens, cookies, full account IDs, and UIDs are not printed.
- Unit tests do not use a real account.

## License

MIT. The project is independent and is not affiliated with iFlytek or AStudio.
