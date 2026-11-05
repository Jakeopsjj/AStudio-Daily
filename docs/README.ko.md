# AStudio Daily

[简体中文](../README.md) · [English](README.en.md) · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Português (BR)](README.pt-BR.md)

**AStudio(iFlytek Astron Studio) 웹 세션 쿠키로 데스크톱 계정 초기화를 실행하고 두 포인트 풀을 각각 대조합니다.**

## 동작

참조 계약에는 별도의 일일 포인트 수령 API가 없습니다. 데스크톱 앱은 body 없는 `POST tenant-app/v2/init-app`으로 당일 흐름을 시작합니다.

1. `membership/plan-config` 조회;
2. 불리언 `dailyLoginEnabled=false`일 때만 중립 종료;
3. `totalBalance`와 `sparkTotalBalance` 이전 값 조회;
4. body 없는 `POST tenant-app/v2/init-app` 전송;
5. 2.5초 대기;
6. 두 포인트 풀 재조회;
7. 어느 한 풀이 명확히 증가해야 `observed` 보고.

초기화가 성공해도 두 풀 모두 증가하지 않으면 `failed`로 보고하고 프로세스 종료 코드를 0이 아닌 값으로 반환합니다. 잔액 증가는 변화 자체만 뜻하며 발생 원인은 추정하지 않습니다.

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
| `ASTUDIO_CLIENT_TYPE` | 선택 | `clientType` 재정의. Windows는 `21`, macOS는 `22`, Linux는 기본적으로 생략합니다. |
| `ASTUDIO_TIMEOUT` | 선택 | 요청 제한 시간, 기본 `20`초. |
| `ASTUDIO_WAIT_SECONDS` | 선택 | 잔액 재확인 대기, 기본 `2.5`초. |
| `PUSHPLUS_TOKEN` | 선택 | PushPlus. |
| `BARK_URL` | 선택 | Bark. |
| `WECOM_WEBHOOK` | 선택 | WeCom 봇 URL 또는 key. |

\* `astudio_accounts.txt`를 대신 사용할 수 있습니다.

## 상태

| 상태 | 의미 |
| :--- | :--- |
| `observed` | 이번 실행에서 하나 이상의 포인트 풀이 증가. 증가 원인은 추정하지 않음. |
| `disabled` | 일일 로그인 활동 비활성화. |
| `query` | 읽기 전용 조회. |
| `failed` | 세션, HTTP, 계약, 읽을 수 없는 잔액, 초기화 실패 또는 초기화 성공 후 제로 증가. |

## HTTP 계약

- 제품: AStudio(iFlytek Astron Studio)
- API: `https://agent.xfyun.cn/xingchen-studio/`
- 쿠키: `ssoSessionId`, `sso_sessionid`, `account_id`, `token`
- 일일 조회: `GET membership/plan-config`, `GET points/balance`
- 활성화: 쿠키를 사용하는 body 없는 `POST tenant-app/v2/init-app`
- 모든 계정 요청은 `studioVersion: 3.5.1` 전송
- Windows는 `clientType=21`, macOS는 `22`, Linux는 기본적으로 생략하며 `ASTUDIO_CLIENT_TYPE`으로 재정의 가능
- 성공 응답은 `flag=true`, `code=0`, 완전한 `data`가 필요하며 `init-app`은 `banned=false`도 필요
- SMS 전송과 비밀번호 로그인에는 GeeTest 필요
- 참조 증거에서 별도 CSRF token/header는 확인되지 않음

자세한 내용은 [PROTOCOL.md](PROTOCOL.md)를 참조하세요.

## 버전

- 스크립트: `v1.1.0`
- 기준: `Agent2Providers v3.4.2` / `3055f416841c1393ec04294a702603fd41e840aa`
- 오프라인 회귀: unittest 49개

## 보안

- 자격 증명은 환경 변수 또는 계정 파일에서만 읽습니다.
- API 리디렉션을 따르지 않습니다.
- token, 쿠키, 전체 account_id, UID를 출력하지 않습니다.
- 단위 테스트는 실제 계정을 사용하지 않습니다.

## 라이선스

MIT. iFlytek/AStudio 공식과 무관한 독립 프로젝트입니다.
