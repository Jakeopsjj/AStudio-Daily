# AStudio Daily

[简体中文](../README.md) · [English](README.en.md) · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Português (BR)](README.pt-BR.md)

**Dispara a inicialização desktop do AStudio (iFlytek Astron Studio) e reconcilia os dois pools de pontos com cookies de sessão web.**

## Funcionamento

O contrato de referência não possui um endpoint separado de resgate. O cliente desktop inicia o fluxo diário com `POST tenant-app/v2/init-app`, sem body.

1. lê `membership/plan-config`;
2. encerra apenas quando o booleano `dailyLoginEnabled=false`;
3. lê `totalBalance` e `sparkTotalBalance` antes da inicialização;
4. envia `POST tenant-app/v2/init-app`, sem body;
5. aguarda 2,5 segundos;
6. lê novamente os dois pools de pontos;
7. relata `observed` quando qualquer pool cresce claramente.

Se a inicialização funcionar, mas nenhum pool crescer, a conta é reportada como `failed` e o processo termina com código diferente de zero. Um delta positivo prova apenas que o saldo mudou; a origem não é inferida.

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
| `ASTUDIO_CLIENT_TYPE` | opcional | Substitui `clientType`. Windows usa `21`, macOS `22`; Linux omite por padrão. |
| `ASTUDIO_TIMEOUT` | opcional | Timeout, padrão `20` s. |
| `ASTUDIO_WAIT_SECONDS` | opcional | Espera antes da nova leitura, padrão `2,5` s. |
| `PUSHPLUS_TOKEN` | opcional | PushPlus. |
| `BARK_URL` | opcional | Bark. |
| `WECOM_WEBHOOK` | opcional | URL ou key do bot WeCom. |

\* `astudio_accounts.txt` também pode ser usado.

## Estados

| Estado | Significado |
| :--- | :--- |
| `observed` | Pelo menos um pool de pontos aumentou nesta execução. |
| `disabled` | Atividade diária desativada. |
| `query` | Consulta somente leitura. |
| `failed` | Sessão, HTTP, contrato, saldo ilegível, inicialização ou zero crescimento após inicialização bem-sucedida. |

## Contrato HTTP

- Produto: AStudio (iFlytek Astron Studio)
- API: `https://agent.xfyun.cn/xingchen-studio/`
- Cookies: `ssoSessionId`, `sso_sessionid`, `account_id`, `token`
- Leituras diárias: `GET membership/plan-config`, `GET points/balance`
- Ativação: `POST tenant-app/v2/init-app` sem body, com o cookie da conta
- Todas as requisições da conta usam `studioVersion: 3.5.1`
- Windows usa `clientType=21`, macOS `22`; Linux omite por padrão e aceita `ASTUDIO_CLIENT_TYPE`
- Sucesso exige `flag=true`, `code=0` e `data` completo; `init-app` também exige `banned=false`
- GeeTest é necessário para envio de SMS e login por senha
- Não foi encontrado token/header CSRF separado na evidência de referência

Consulte [PROTOCOL.md](PROTOCOL.md).

## Versão

- Script: `v1.1.0`
- Base: `Agent2Providers v3.4.2` / `3055f416841c1393ec04294a702603fd41e840aa`
- Regressão offline: 49 testes unittest

## Segurança

- Credenciais vêm apenas de variáveis de ambiente ou arquivo de contas.
- Redirecionamentos da API não são seguidos.
- Token, cookie, account_id completo e UID não são exibidos.
- Os testes não usam conta real.

## Licença

MIT. Projeto independente, sem vínculo com a iFlytek ou o AStudio oficial.
