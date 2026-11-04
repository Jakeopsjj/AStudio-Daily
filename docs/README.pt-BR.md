# AStudio Daily

[简体中文](../README.md) · [English](README.en.md) · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Português (BR)](README.pt-BR.md)

**Observa mudanças de saldo relacionadas aos pontos diários do AStudio (iFlytek Astron Studio) com cookies de sessão web e comparação honesta antes/depois.**

## Funcionamento

O contrato de referência não possui um endpoint separado de resgate dos pontos diários. O servidor concede o crédito quando a sessão web da conta se torna ativa no dia.

1. lê `membership/plan-config`;
2. encerra de forma neutra quando `dailyLoginEnabled=false`;
3. lê `points/balance` antes da ativação;
4. solicita `membership/me` e `points/summary`;
5. aguarda 2,5 segundos;
6. lê `points/balance` novamente;
7. relata aumento observado quando `totalBalance` realmente cresce.

Saldo sem alteração é reportado como `unchanged`: a conta pode já ter feito login no dia ou o crédito ainda não chegou. O script não inventa sucesso. Um delta positivo prova apenas que o saldo mudou; a origem não é inferida.

## Formatos de conta

```text
nome|token|account_id|ssoSessionId
nome|token|account_id
token=TOKEN; account_id=ACCOUNT_ID; ssoSessionId=SSO_SESSION_ID
```

Várias contas podem ser separadas por linhas ou `&`.

## Execução

```bash
pip install -r requirements.txt
export ASTUDIO_COOKIES='nome|TOKEN|ACCOUNT_ID|SSO_SESSION_ID'
python astudio_daily.py
```

```bash
python astudio_daily.py --query
python astudio_daily.py --only 1,3
python astudio_daily.py --no-notify
```

## Variáveis

| Variável | Obrigatória | Uso |
| :--- | :---: | :--- |
| `ASTUDIO_COOKIES` | sim* | Cookies de várias contas. |
| `ASTUDIO_ACCOUNT_FILE` | opcional | Arquivo de contas. |
| `ASTUDIO_PROXY` | opcional | Proxy HTTP(S). |
| `ASTUDIO_TIMEOUT` | opcional | Timeout, padrão `20` s. |
| `ASTUDIO_WAIT_SECONDS` | opcional | Espera antes da nova leitura, padrão `2,5` s. |
| `PUSHPLUS_TOKEN` | opcional | PushPlus. |
| `BARK_URL` | opcional | Bark. |
| `WECOM_WEBHOOK` | opcional | URL ou key do bot WeCom. |

\* `astudio_accounts.txt` também pode ser usado.

## Estados

| Estado | Significado |
| :--- | :--- |
| `observed` | O saldo aumentou nesta execução; a origem não é inferida. |
| `unchanged` | Sem aumento nesta execução; não confirma sucesso. |
| `disabled` | Atividade diária desativada. |
| `query` | Consulta somente leitura. |
| `failed` | Falha de sessão, HTTP, contrato ou ativação. |

## Contrato HTTP

- Produto: AStudio (iFlytek Astron Studio)
- API: `https://agent.xfyun.cn/xingchen-studio/`
- Cookies: `ssoSessionId`, `sso_sessionid`, `account_id`, `token`
- Endpoints: `membership/plan-config`, `points/balance`, `membership/me`, `points/summary`
- Requisições diárias usam somente `Accept: application/json` e `Cookie`
- Login usa `clientType` (`21` no Windows, `22` no macOS) e `studioVersion: 3.5.1`
- GeeTest é necessário para envio de SMS e login por senha
- Não foi encontrado token/header CSRF separado na evidência de referência

Consulte [PROTOCOL.md](PROTOCOL.md).

## Segurança

- Credenciais vêm apenas de variáveis de ambiente ou arquivo de contas.
- Redirecionamentos da API não são seguidos.
- Token, cookie, account_id completo e UID não são exibidos.
- Os testes não usam conta real.

## Licença

MIT. Projeto independente, sem vínculo com a iFlytek ou o AStudio oficial.
