# AStudio Daily

[简体中文](../README.md) · [English](README.en.md) · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Português (BR)](README.pt-BR.md)

**使用網頁會話 Cookie 完成 AStudio（科大訊飛 Astron Studio）每日登入、領取獎勵彈窗，並分別核對兩個積分池。**

## 功能

流程：

1. 讀取 `membership/plan-config`；
2. 僅布林值 `dailyLoginEnabled=false` 時以中性狀態結束；
3. 讀取 `totalBalance` 與 `sparkTotalBalance` 前值；
4. 送出無 body 的 `POST tenant-app/v2/init-app`；
5. 讀取 `client-popups/pending`；
6. 僅完成 `DAILY_REWARD_DIALOG` 或含 `REWARD` 的獎勵彈窗；
7. 等待 2.5 秒；
8. 再次讀取兩個積分池；
9. 依服務端證據報告 `observed`、`claimed`、`done` 或 `failed`。

`init-app` 只記錄當日登入，不會單獨發放積分。正差額只證明餘額發生變化，不推斷來源。

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
| `ASTUDIO_CLIENT_TYPE` | 否 | 覆寫 `clientType`。Windows/Linux 預設 `21`、macOS `22`。 |
| `ASTUDIO_TIMEOUT` | 否 | 請求逾時，預設 `20` 秒。 |
| `ASTUDIO_WAIT_SECONDS` | 否 | 餘額複查等待，預設 `2.5` 秒。 |
| `PUSHPLUS_TOKEN` | 否 | PushPlus。 |
| `BARK_URL` | 否 | Bark。 |
| `WECOM_WEBHOOK` | 否 | 企業微信機器人 URL 或 key。 |

\* 也可使用 `astudio_accounts.txt`。

## 狀態

| 狀態 | 說明 |
| :--- | :--- |
| `observed` | 本輪至少一個積分池增加，不推斷增長來源。 |
| `claimed` | 服務端已確認獎勵彈窗領取成功，但本輪餘額尚未刷新。 |
| `done` | 登入完成且沒有待領取獎勵，通常表示今天已經領過。 |
| `disabled` | 每日登入活動未啟用。 |
| `query` | 僅查詢，未觸發活躍。 |
| `failed` | 會話、HTTP、契約、餘額不可讀、初始化或獎勵彈窗領取失敗。 |

## 協議摘要

- 產品：AStudio（科大訊飛 Astron Studio）
- API：`https://agent.xfyun.cn/xingchen-studio/`
- Cookie：`ssoSessionId`、`sso_sessionid`、`account_id`、`token`
- 日常讀取：`GET membership/plan-config`、`GET points/balance`
- 活躍觸發：帶 Cookie 的無 body `POST tenant-app/v2/init-app`
- 待領取獎勵：`GET client-popups/pending`
- 領取獎勵：`POST client-popups/complete`，JSON `{popupId, instanceKey, completed:true}`
- 所有帳號面請求帶 `studioVersion: 3.6.0`、`User-Agent: AStudio/3.6.0`
- Windows/Linux `clientType=21`、macOS `22`
- 成功信封必須同時滿足 `flag=true`、`code=0`、`data` 完整；`init-app` 另要求 `banned=false`
- `client-popups/complete` 成功時允許 `data:null`
- 發送簡訊與密碼登入需要極驗；現有協議證據未發現獨立 CSRF token/header

完整證據見 [PROTOCOL.md](PROTOCOL.md)。

## 版本

- 腳本：`v1.2.0`
- 協議版本：AStudio 桌面端 `3.6.0`
- 離線回歸：52 項 unittest

## 安全

- 憑據只從環境變數或帳號檔讀取。
- 不跟隨 API 重新導向。
- 不輸出 token、Cookie、完整 account_id 或 UID。
- 單元測試不使用真實帳號。

## 授權

MIT。本專案獨立維護，與科大訊飛或 AStudio 官方無隸屬關係。
