# AStudio Daily

[简体中文](../README.md) · [English](README.en.md) · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Português (BR)](README.pt-BR.md)

**AStudio(iFlytek Astron Studio) 웹 세션 쿠키로 일일 로그인 포인트에 따른 잔액 변화를 전후 비교로 관측합니다.**

## 동작

참조 계약에는 별도의 일일 포인트 수령 API가 없습니다. 서버는 당일 계정 웹 세션이 처음 활성화될 때 일일 로그인 포인트를 지급합니다.

1. `membership/plan-config` 조회;
2. `dailyLoginEnabled=false`이면 중립 종료;
3. `points/balance` 이전 값 조회;
4. `membership/me`, `points/summary` 요청;
5. 2.5초 대기;
6. `points/balance` 재조회;
7. `totalBalance`가 실제로 증가하면 이번 실행의 잔액 증가로 관측.

잔액이 그대로면 `unchanged`로 보고합니다. 오늘 이미 서명했거나 아직 지급되지 않았을 수 있으며, 성공을 꾸며내지 않습니다. 잔액 증가는 변화 자체만 뜻하며 발생 원인은 추정하지 않습니다.

## 계정 형식

```text
이름|token|account_id|ssoSessionId
이름|token|account_id
token=TOKEN; account_id=ACCOUNT_ID; ssoSessionId=SSO_SESSION_ID
```

여러 계정은 줄바꿈 또는 `&`로 구분합니다.

## 실행

```bash
pip install -r requirements.txt
export ASTUDIO_COOKIES='이름|TOKEN|ACCOUNT_ID|SSO_SESSION_ID'
python astudio_daily.py
```

```bash
python astudio_daily.py --query
python astudio_daily.py --only 1,3
python astudio_daily.py --no-notify
```

## 환경 변수

| 변수 | 필수 | 설명 |
| :--- | :---: | :--- |
| `ASTUDIO_COOKIES` | 예* | 다중 계정 쿠키. |
| `ASTUDIO_ACCOUNT_FILE` | 선택 | 계정 파일 경로. |
| `ASTUDIO_PROXY` | 선택 | HTTP(S) 프록시. |
| `ASTUDIO_TIMEOUT` | 선택 | 요청 제한 시간, 기본 `20`초. |
| `ASTUDIO_WAIT_SECONDS` | 선택 | 잔액 재확인 대기, 기본 `2.5`초. |
| `PUSHPLUS_TOKEN` | 선택 | PushPlus. |
| `BARK_URL` | 선택 | Bark. |
| `WECOM_WEBHOOK` | 선택 | WeCom 봇 URL 또는 key. |

\* `astudio_accounts.txt`를 대신 사용할 수 있습니다.

## 상태

| 상태 | 의미 |
| :--- | :--- |
| `observed` | 이번 실행에서 잔액 증가를 관측. 증가 원인은 추정하지 않음. |
| `unchanged` | 이번 실행에서 증가 없음. 성공으로 보고하지 않음. |
| `disabled` | 일일 로그인 활동 비활성화. |
| `query` | 읽기 전용 조회. |
| `failed` | 세션, HTTP, 계약 또는 활성화 실패. |

## HTTP 계약

- 제품: AStudio(iFlytek Astron Studio)
- API: `https://agent.xfyun.cn/xingchen-studio/`
- 쿠키: `ssoSessionId`, `sso_sessionid`, `account_id`, `token`
- 엔드포인트: `membership/plan-config`, `points/balance`, `membership/me`, `points/summary`
- 일일 요청은 `Accept: application/json`과 `Cookie`만 사용
- 로그인은 `clientType`(Windows `21`, macOS `22`)과 `studioVersion: 3.5.1` 사용
- SMS 전송과 비밀번호 로그인에는 GeeTest 필요
- 참조 증거에서 별도 CSRF token/header는 확인되지 않음

자세한 내용은 [PROTOCOL.md](PROTOCOL.md)를 참조하세요.

## 보안

- 자격 증명은 환경 변수 또는 계정 파일에서만 읽습니다.
- API 리디렉션을 따르지 않습니다.
- token, 쿠키, 전체 account_id, UID를 출력하지 않습니다.
- 단위 테스트는 실제 계정을 사용하지 않습니다.

## 라이선스

MIT. iFlytek/AStudio 공식과 무관한 독립 프로젝트입니다.
