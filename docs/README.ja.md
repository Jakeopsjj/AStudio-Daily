# AStudio Daily

[简体中文](../README.md) · [English](README.en.md) · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Português (BR)](README.pt-BR.md)

**AStudio（iFlytek Astron Studio）の Web セッション Cookie を使い、デイリーログイン積分による残高変化を前後比較で観測するツールです。**

## 動作

参考契約には独立した「受け取り」API はありません。当日のアカウント Web セッションが初めてアクティブになったとき、サーバーがデイリー積分を付与します。

1. `membership/plan-config` を取得；
2. `dailyLoginEnabled=false` なら中性終了；
3. `points/balance` の前値を取得；
4. `membership/me` と `points/summary` を呼び出す；
5. 2.5 秒待機；
6. `points/balance` を再取得；
7. `totalBalance` が実際に増えた場合、残高増加を観測したものとして報告。

残高が変わらない場合は `unchanged` とし、本日すでに签到済み、または未付与の可能性を報告します。増加は残高変化だけを示し、発生源は推定しません。

## アカウント形式

```text
名前|token|account_id|ssoSessionId
名前|token|account_id
token=TOKEN; account_id=ACCOUNT_ID; ssoSessionId=SSO_SESSION_ID
```

複数アカウントは改行または `&` で区切ります。

## 実行

```bash
pip install -r requirements.txt
export ASTUDIO_COOKIES='名前|TOKEN|ACCOUNT_ID|SSO_SESSION_ID'
python astudio_daily.py
```

```bash
python astudio_daily.py --query
python astudio_daily.py --only 1,3
python astudio_daily.py --no-notify
```

## 環境変数

| 変数 | 必須 | 用途 |
| :--- | :---: | :--- |
| `ASTUDIO_COOKIES` | はい* | 複数アカウント Cookie。 |
| `ASTUDIO_ACCOUNT_FILE` | 任意 | アカウントファイル。 |
| `ASTUDIO_PROXY` | 任意 | HTTP(S) プロキシ。 |
| `ASTUDIO_TIMEOUT` | 任意 | タイムアウト。既定 `20` 秒。 |
| `ASTUDIO_WAIT_SECONDS` | 任意 | 残高再確認の待機。既定 `2.5` 秒。 |
| `PUSHPLUS_TOKEN` | 任意 | PushPlus。 |
| `BARK_URL` | 任意 | Bark。 |
| `WECOM_WEBHOOK` | 任意 | WeCom ボット URL または key。 |

\* `astudio_accounts.txt` も使用できます。

## 状態

| 状態 | 意味 |
| :--- | :--- |
| `observed` | 今回の実行で残高増加を観測。増加源は推定しない。 |
| `unchanged` | 今回の増加なし。成功とは報告しない。 |
| `disabled` | デイリーログイン活動が無効。 |
| `query` | 読み取り専用照会。 |
| `failed` | セッション、HTTP、契約、活性化の失敗。 |

## HTTP 契約

- 製品：AStudio（iFlytek Astron Studio）
- API：`https://agent.xfyun.cn/xingchen-studio/`
- Cookie：`ssoSessionId`、`sso_sessionid`、`account_id`、`token`
- エンドポイント：`membership/plan-config`、`points/balance`、`membership/me`、`points/summary`
- 日常リクエストは `Accept: application/json` と `Cookie` のみ
- ログインでは `clientType`（Windows `21`、macOS `22`）と `studioVersion: 3.5.1`
- SMS 送信とパスワードログインには GeeTest が必要
- 参考証拠に独立した CSRF token/header は見当たりません

詳細は [PROTOCOL.md](PROTOCOL.md) を参照してください。

## セキュリティ

- 認証情報は環境変数またはアカウントファイルからのみ読み取ります。
- API のリダイレクトを追跡しません。
- token、Cookie、完全な account_id、UID を出力しません。
- 単体テストは実アカウントを使用しません。

## ライセンス

MIT。iFlytek / AStudio 公式とは無関係の独立プロジェクトです。
