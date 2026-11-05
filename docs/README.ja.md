# AStudio Daily

[简体中文](../README.md) · [English](README.en.md) · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Português (BR)](README.pt-BR.md)

**AStudio（iFlytek Astron Studio）の Web セッション Cookie を使い、デスクトップ版のアカウント初期化を実行して 2 つの積分プールを照合するツールです。**

## 動作

参考契約には独立した「受け取り」API はありません。デスクトップ版は body なしの `POST tenant-app/v2/init-app` で当日の処理を開始します。

1. `membership/plan-config` を取得；
2. 真偽値 `dailyLoginEnabled=false` のときだけ中性終了；
3. `totalBalance` と `sparkTotalBalance` の前値を取得；
4. body なしの `POST tenant-app/v2/init-app` を送信；
5. 2.5 秒待機；
6. 2 つの積分プールを再取得；
7. いずれかが明確に増加した場合に `observed` を報告。

初期化に成功しても両方のプールが増加しない場合は `failed` とし、終了コードを非 0 にします。増加は残高変化だけを示し、発生源は推定しません。

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
| `ASTUDIO_CLIENT_TYPE` | 任意 | `clientType` を上書き。Windows は `21`、macOS は `22`、Linux は既定で送信しません。 |
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
| `disabled` | デイリーログイン活動が無効。 |
| `query` | 読み取り専用照会。 |
| `failed` | セッション、HTTP、契約、残高不能、初期化失敗、または初期化成功後のゼロ増加。 |

## HTTP 契約

- 製品：AStudio（iFlytek Astron Studio）
- API：`https://agent.xfyun.cn/xingchen-studio/`
- Cookie：`ssoSessionId`、`sso_sessionid`、`account_id`、`token`
- 日常取得：`GET membership/plan-config`、`GET points/balance`
- 活性化：Cookie 付きの body なし `POST tenant-app/v2/init-app`
- すべてのアカウント面リクエストに `studioVersion: 3.5.1`
- Windows は `clientType=21`、macOS は `22`、Linux は既定で省略し `ASTUDIO_CLIENT_TYPE` で上書き可能
- 成功封筒は `flag=true`、`code=0`、完全な `data` が必要。`init-app` は `banned=false` も必要
- SMS 送信とパスワードログインには GeeTest が必要
- 参考証拠に独立した CSRF token/header は見当たりません

詳細は [PROTOCOL.md](PROTOCOL.md) を参照してください。

## バージョン

- スクリプト：`v1.1.0`
- ベースライン：`Agent2Providers v3.4.2` / `3055f416841c1393ec04294a702603fd41e840aa`
- オフライン回帰：49 件の unittest

## セキュリティ

- 認証情報は環境変数またはアカウントファイルからのみ読み取ります。
- API のリダイレクトを追跡しません。
- token、Cookie、完全な account_id、UID を出力しません。
- 単体テストは実アカウントを使用しません。

## ライセンス

MIT。iFlytek / AStudio 公式とは無関係の独立プロジェクトです。
