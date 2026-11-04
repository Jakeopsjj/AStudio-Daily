# AStudio Daily

[简体中文](../README.md) · [English](README.en.md) · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Português (BR)](README.pt-BR.md)

**使用網頁會話 Cookie 觀測 AStudio（科大訊飛 Astron Studio）每日登入積分，以前後餘額作唯一成功判據。**

## 功能

參考契約中沒有獨立的每日積分領取介面。伺服器會在帳號當天網頁會話首次活躍時發放積分。

流程：

1. 讀取 `membership/plan-config`；
2. `dailyLoginEnabled=false` 時以中性狀態結束；
3. 讀取 `points/balance` 前值；
4. 請求 `membership/me` 與 `points/summary`；
5. 等待 2.5 秒；
6. 再次讀取 `points/balance`；
7. `totalBalance` 真實增加時只報告觀察到增長。

餘額不變時回報 `unchanged`，表示可能今日已簽，或積分尚未發放，不會偽造成功。正差額只證明餘額發生變化，不推斷來源。

## 帳號格式

```text
備註|token|account_id|ssoSessionId
備註|token|account_id
token=TOKEN; account_id=ACCOUNT_ID; ssoSessionId=SSO_SESSION_ID
```

多帳號可用換行或 `&` 分隔。

## 執行

```bash
pip install -r requirements.txt
export ASTUDIO_COOKIES='備註|TOKEN|ACCOUNT_ID|SSO_SESSION_ID'
python astudio_daily.py
```

```bash
python astudio_daily.py --query
python astudio_daily.py --only 1,3
python astudio_daily.py --no-notify
```

## 環境變數

| 變數 | 必填 | 說明 |
| :--- | :---: | :--- |
| `ASTUDIO_COOKIES` | 是* | 多帳號 Cookie。 |
| `ASTUDIO_ACCOUNT_FILE` | 否 | 帳號檔路徑。 |
| `ASTUDIO_PROXY` | 否 | HTTP(S) 代理。 |
| `ASTUDIO_TIMEOUT` | 否 | 請求逾時，預設 `20` 秒。 |
| `ASTUDIO_WAIT_SECONDS` | 否 | 餘額複查等待，預設 `2.5` 秒。 |
| `PUSHPLUS_TOKEN` | 否 | PushPlus。 |
| `BARK_URL` | 否 | Bark。 |
| `WECOM_WEBHOOK` | 否 | 企業微信機器人 URL 或 key。 |

\* 也可使用 `astudio_accounts.txt`。

## 狀態

| 狀態 | 說明 |
| :--- | :--- |
| `observed` | 本輪觀察到餘額增加，不推斷增長來源。 |
| `unchanged` | 本輪未見增加，不確認成功。 |
| `disabled` | 每日登入活動未啟用。 |
| `query` | 僅查詢，未觸發活躍。 |
| `failed` | 會話、HTTP、契約或活躍觸發失敗。 |

## 協議摘要

- 產品：AStudio（科大訊飛 Astron Studio）
- API：`https://agent.xfyun.cn/xingchen-studio/`
- Cookie：`ssoSessionId`、`sso_sessionid`、`account_id`、`token`
- 端點：`membership/plan-config`、`points/balance`、`membership/me`、`points/summary`
- 日常請求只帶 `Accept: application/json` 與 `Cookie`
- 登入流程帶 `clientType`（Windows `21`、macOS `22`）與 `studioVersion: 3.5.1`
- 發送簡訊與密碼登入需要極驗；參考證據未發現獨立 CSRF token/header

完整證據見 [PROTOCOL.md](PROTOCOL.md)。

## 安全

- 憑據只從環境變數或帳號檔讀取。
- 不跟隨 API 重新導向。
- 不輸出 token、Cookie、完整 account_id 或 UID。
- 單元測試不使用真實帳號。

## 授權

MIT。本專案獨立維護，與科大訊飛或 AStudio 官方無隸屬關係。
