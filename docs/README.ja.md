# AStudio Daily

[简体中文](../README.md) · [English](README.en.md) · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Português (BR)](README.pt-BR.md)

**AStudio（iFlytek Astron Studio）の Web セッション Cookie を使い、毎日のログイン、報酬ポップアップの受け取り、2 つの積分プールの照合を行うツールです。**

## 動作

1. `membership/plan-config` を取得；
2. 真偽値 `dailyLoginEnabled=false` のときだけ中性終了；
3. `totalBalance` と `sparkTotalBalance` の前値を取得；
4. body なしの `POST tenant-app/v2/init-app` を送信；
5. `client-popups/pending` を取得；
6. `DAILY_REWARD_DIALOG` または `REWARD` を含む報酬項目だけを完了；
7. 2.5 秒待機；
8. 2 つの積分プールを再取得；
9. サーバー証拠に基づき `observed`、`claimed`、`done`、`failed` を報告。

`init-app` は当日のログインを記録するだけで、単独では積分を付与しません。増加は残高変化だけを示し、発生源は推定しません。

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
| `ASTUDIO_CLIENT_TYPE` | 任意 | `clientType` を上書き。Windows/Linux は `21`、macOS は `22`。 |
| `ASTUDIO_TIMEOUT` | 任意 | タイムアウト。既定 `20` 秒。 |
| `ASTUDIO_WAIT_SECONDS` | 任意 | 残高再確認の待機。既定 `2.5` 秒。 |
| `PUSHPLUS_TOKEN` | 任意 | PushPlus。 |
| `BARK_URL` | 任意 | Bark。 |
| `WECOM_WEBHOOK` | 任意 | WeCom ボット URL または key。 |

\* `astudio_accounts.txt` も使用できます。

## 状態

| 状態 | 意味 |
| :--- | :--- |
| `observed` | 今回の実行で少なくとも 1 つの積分プールが増加。増加源は推定しない。 |
| `claimed` | サーバーが報酬ポップアップの完了を確認したが、今回の残高はまだ更新されていない。 |
| `done` | ログイン完了後、受け取り待ちの報酬がない。通常は当日分を受け取り済み。 |
| `disabled` | デイリーログイン活動が無効。 |
| `query` | 読み取り専用照会。 |
| `failed` | セッション、HTTP、契約、残高不能、初期化、または報酬受け取りの失敗。 |

## HTTP 契約

- 製品：AStudio（iFlytek Astron Studio）
- API：`https://agent.xfyun.cn/xingchen-studio/`
- Cookie：`ssoSessionId`、`sso_sessionid`、`account_id`、`token`
- 日常取得：`GET membership/plan-config`、`GET points/balance`
- 活性化：Cookie 付きの body なし `POST tenant-app/v2/init-app`
- 受け取り待ち報酬：`GET client-popups/pending`
- 報酬受け取り：`POST client-popups/complete`、JSON `{popupId, instanceKey, completed:true}`
- すべてのアカウント面リクエストに `studioVersion: 3.6.0`、`User-Agent: AStudio/3.6.0`
- Windows/Linux は `clientType=21`、macOS は `22`
- 成功封筒は `flag=true`、`code=0`、完全な `data` が必要。`init-app` は `banned=false` も必要
- `client-popups/complete` の成功時は `data:null` を許容
- SMS 送信とパスワードログインには GeeTest が必要
- 現行プロトコル証拠に独立した CSRF token/header は見当たりません

詳細は [PROTOCOL.md](PROTOCOL.md) を参照してください。

## バージョン

- スクリプト：`v1.2.0`
- プロトコル：AStudio デスクトップ `3.6.0`
- オフライン回帰：52 件の unittest

## セキュリティ

- 認証情報は環境変数またはアカウントファイルからのみ読み取ります。
- API のリダイレクトを追跡しません。
- token、Cookie、完全な account_id、UID を出力しません。
- 単体テストは実アカウントを使用しません。

## ライセンス

MIT。iFlytek / AStudio 公式とは無関係の独立プロジェクトです。
