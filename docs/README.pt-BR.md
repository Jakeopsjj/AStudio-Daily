# AStudio Daily

[简体中文](../README.md) · [English](README.en.md) · [繁體中文](README.zh-Hant.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Português (BR)](README.pt-BR.md)

**Faz o login diário no AStudio (iFlytek Astron Studio), resgata popups de recompensa e reconcilia os dois pools de pontos com cookies de sessão web.**

## Funcionamento

1. lê `membership/plan-config`;
2. encerra apenas quando o booleano `dailyLoginEnabled=false`;
3. lê `totalBalance` e `sparkTotalBalance` antes da inicialização;
4. envia `POST tenant-app/v2/init-app`, sem body;
5. lê `client-popups/pending`;
6. conclui apenas itens `DAILY_REWARD_DIALOG` ou que contenham `REWARD`;
7. aguarda 2,5 segundos;
8. lê novamente os dois pools de pontos;
9. relata `observed`, `claimed`, `done` ou `failed` conforme a evidência do servidor.

O `init-app` registra apenas o login do dia e não concede pontos sozinho. Um delta positivo prova apenas que o saldo mudou; a origem não é inferida.

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
| `ASTUDIO_CLIENT_TYPE` | opcional | Substitui `clientType`. Windows/Linux usam `21`, macOS `22`. |
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
| `claimed` | O servidor confirmou a conclusão do popup, mas o saldo ainda não foi atualizado. |
| `done` | Login concluído e nenhuma recompensa pendente, normalmente porque já foi resgatada hoje. |
| `disabled` | Atividade diária desativada. |
| `query` | Consulta somente leitura. |
| `failed` | Falha de sessão, HTTP, contrato, leitura de saldo, inicialização ou resgate da recompensa. |

## Contrato HTTP

- Produto: AStudio (iFlytek Astron Studio)
- API: `https://agent.xfyun.cn/xingchen-studio/`
- Cookies: `ssoSessionId`, `sso_sessionid`, `account_id`, `token`
- Leituras diárias: `GET membership/plan-config`, `GET points/balance`
- Ativação: `POST tenant-app/v2/init-app` sem body, com o cookie da conta
- Recompensas pendentes: `GET client-popups/pending`
- Resgate: `POST client-popups/complete` com `{popupId, instanceKey, completed:true}`
- Todas as requisições usam `studioVersion: 3.6.0` e `User-Agent: AStudio/3.6.0`
- Windows/Linux usam `clientType=21`, macOS `22`
- Sucesso exige `flag=true`, `code=0` e `data` completo; `init-app` também exige `banned=false`
- `client-popups/complete` pode retornar `data:null` em caso de sucesso
- GeeTest é necessário para envio de SMS e login por senha
- Não foi encontrado token/header CSRF separado na evidência atual do protocolo

Consulte [PROTOCOL.md](PROTOCOL.md).

## Versão

- Script: `v1.2.0`
- Protocolo: AStudio desktop `3.6.0`
- Regressão offline: 52 testes unittest

## Segurança

- Credenciais vêm apenas de variáveis de ambiente ou arquivo de contas.
- Redirecionamentos da API não são seguidos.
- Token, cookie, account_id completo e UID não são exibidos.
- Os testes não usam conta real.

## Licença

MIT. Projeto independente, sem vínculo com a iFlytek ou o AStudio oficial.
