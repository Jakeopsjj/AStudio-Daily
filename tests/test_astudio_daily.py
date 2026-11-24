import importlib.util
import json
import os
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "astudio_daily", ROOT / "astudio_daily.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["astudio_daily"] = MODULE
SPEC.loader.exec_module(MODULE)


class FakeResponse:
    def __init__(self, payload, status=200, text=None):
        self.status_code = status
        self.text = (
            text if text is not None else json.dumps(payload, ensure_ascii=False)
        )


class FakeHttpSession:
    def __init__(self, response):
        self.response = response
        self.headers = {}
        self.proxies = {}
        self.calls = []
        self.closed = False

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return self.response

    def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return self.response

    def close(self):
        self.closed = True


class FakeHttpTransport:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.sessions = []

    def __call__(self):
        if not self.responses:
            raise AssertionError("unexpected HTTP request")
        session = FakeHttpSession(self.responses.pop(0))
        self.sessions.append(session)
        return session


class FakeClient:
    def __init__(
        self,
        config=None,
        balances=None,
        init_app=None,
        rewards=None,
        claimed_rewards=0,
        claim_error=None,
        wait_seconds=2.5,
    ):
        self.config = config or {"dailyLoginEnabled": True}
        self.balances = list(balances or [{"totalBalance": 100}])
        self.init_app_data = init_app if init_app is not None else {"banned": False}
        self.rewards = list(rewards or [])
        self.claimed_rewards = claimed_rewards
        self.claim_error = claim_error
        self.wait_seconds = wait_seconds
        self.calls = []

    def plan_config(self, account):
        self.calls.append("plan-config")
        if isinstance(self.config, Exception):
            raise self.config
        return self.config

    def balance(self, account):
        self.calls.append("points-balance")
        value = self.balances.pop(0)
        if isinstance(value, Exception):
            raise value
        return MODULE.Balance(
            total=MODULE.balance_pool_value(value.get("totalBalance")),
            spark_total=MODULE.balance_pool_value(value.get("sparkTotalBalance")),
        )

    def init_app(self, account):
        self.calls.append("init-app")
        if isinstance(self.init_app_data, Exception):
            raise self.init_app_data
        return self.init_app_data

    def claim_daily_rewards(self, account):
        self.calls.append("client-popups-claim")
        if isinstance(self.claim_error, Exception):
            raise self.claim_error
        return self.claimed_rewards


class AccountParsingTests(unittest.TestCase):
    def test_pipe_account_and_cookie_order(self):
        accounts = MODULE.parse_accounts("主号|tok-value|acct-123|sso-456")
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0].name, "主号")
        self.assertEqual(
            accounts[0].cookie_header,
            "ssoSessionId=sso-456; sso_sessionid=sso-456; "
            "account_id=acct-123; token=tok-value",
        )

    def test_cookie_header_account(self):
        accounts = MODULE.parse_accounts(
            "account_id=acct-1; token=tok-1; ssoSessionId=sso-1"
        )
        self.assertEqual(accounts[0].account_id, "acct-1")
        self.assertEqual(accounts[0].token, "tok-1")
        self.assertEqual(accounts[0].sso_session_id, "sso-1")
        self.assertEqual(
            accounts[0].cookie_header,
            "ssoSessionId=sso-1; sso_sessionid=sso-1; "
            "account_id=acct-1; token=tok-1",
        )

    def test_json_list_account(self):
        raw = json.dumps(
            [
                {
                    "name": "JSON 账号",
                    "session": {
                        "token": "tok-2",
                        "accountId": "acct-2",
                        "ssoSessionId": "sso-2",
                    },
                }
            ],
            ensure_ascii=False,
        )
        accounts = MODULE.parse_accounts(raw)
        self.assertEqual(accounts[0].name, "JSON 账号")
        self.assertEqual(accounts[0].account_id, "acct-2")

    def test_duplicate_accounts_are_removed(self):
        accounts = MODULE.parse_accounts(
            "a|tok|acct\nb|tok|acct",
        )
        self.assertEqual(len(accounts), 1)

    def test_duplicate_accounts_ignore_sso_session_difference(self):
        accounts = MODULE.parse_accounts(
            "a|tok|acct|sso-a\nb|tok|acct|sso-b",
        )
        self.assertEqual(len(accounts), 1)

    def test_missing_cookie_fields_is_rejected(self):
        with self.assertRaises(MODULE.AccountConfigError):
            MODULE.parse_accounts("token=only-token")

    def test_mask_does_not_expose_short_secret(self):
        self.assertEqual(MODULE.mask_secret("secret"), "****")

    def test_phone_in_name_and_message_is_redacted(self):
        phone = "".join(["138", "0013", "8000"])
        account = MODULE.Account(phone, "tok", "acct")
        self.assertEqual(account.label, "138****8000")
        message = MODULE.sanitize_message("contact %s failed" % phone, account)
        self.assertIn("138****8000", message)
        self.assertNotIn(phone, message)

    def test_push_credentials_are_redacted_from_errors(self):
        with mock.patch.dict(
            os.environ,
            {"PUSHPLUS_TOKEN": "push-secret-value"},
            clear=False,
        ):
            message = MODULE.sanitize_message(
                "request failed for push-secret-value"
            )
        self.assertIn("[redacted-pushplus_token]", message)
        self.assertNotIn("push-secret-value", message)

    def test_parse_only_supports_ranges(self):
        self.assertEqual(MODULE.parse_only("1,3-4", 5), {1, 3, 4})

    def test_parse_only_rejects_out_of_range(self):
        with self.assertRaises(MODULE.AccountConfigError):
            MODULE.parse_only("6", 5)

    def test_load_accounts_from_environment_and_file(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "accounts.txt"
            path.write_text("文件账号|tok-file|acct-file\n", encoding="utf-8")
            with mock.patch.dict(
                os.environ,
                {
                    "ASTUDIO_COOKIES": "环境账号|tok-env|acct-env",
                    "ASTUDIO_ACCOUNT_FILE": str(path),
                },
                clear=False,
            ):
                accounts = MODULE.load_accounts()
        self.assertEqual([item.name for item in accounts], ["环境账号", "文件账号"])


class ClientContractTests(unittest.TestCase):
    def make_client(self, *responses, client_type="21"):
        transport = FakeHttpTransport(*responses)
        client = MODULE.AStudioClient(
            wait_seconds=0,
            client_type=client_type,
            session_factory=transport,
        )
        return client, transport

    def account(self):
        return MODULE.Account("a", "tok", "acct", "sso")

    def test_success_envelope_headers_and_no_redirects(self):
        client, transport = self.make_client(
            FakeResponse(
                {
                    "flag": True,
                    "code": 0,
                    "data": {"totalBalance": 12.5, "sparkTotalBalance": 3},
                }
            )
        )
        balance = client.balance(self.account())
        self.assertEqual(balance.total, Decimal("12.5"))
        self.assertEqual(balance.spark_total, Decimal("3"))

        session = transport.sessions[0]
        self.assertEqual(session.headers["Accept"], "application/json")
        self.assertEqual(session.headers["clientType"], "21")
        self.assertEqual(session.headers["studioVersion"], "3.6.0")
        method, url, kwargs = session.calls[0]
        self.assertEqual(method, "GET")
        self.assertEqual(
            url,
            "https://agent.xfyun.cn/xingchen-studio/points/balance",
        )
        self.assertEqual(kwargs["headers"]["Cookie"], self.account().cookie_header)
        self.assertEqual(kwargs["headers"]["clientType"], "21")
        self.assertEqual(kwargs["headers"]["studioVersion"], "3.6.0")
        self.assertFalse(kwargs["allow_redirects"])
        self.assertTrue(session.closed)

    def test_http_401_and_403_are_session_expired(self):
        for status in (401, 403):
            with self.subTest(status=status):
                client, _ = self.make_client(FakeResponse({}, status=status))
                with self.assertRaises(MODULE.SessionExpired):
                    client.plan_config(self.account())

    def test_code_80000_is_session_expired(self):
        client, _ = self.make_client(
            FakeResponse(
                {"flag": False, "code": 80000, "desc": "登录异常，请重新登录"}
            )
        )
        with self.assertRaises(MODULE.SessionExpired):
            client.plan_config(self.account())

    def test_relogin_message_is_ignored_in_success_envelope(self):
        client, _ = self.make_client(
            FakeResponse(
                {
                    "flag": True,
                    "code": 0,
                    "desc": "网页会话失效，请重新登录",
                    "data": {},
                }
            )
        )
        self.assertEqual(client.plan_config(self.account()), {})

    def test_relogin_message_is_session_expired_only_in_failure_branches(self):
        cases = [
            (
                FakeResponse(
                    {"flag": False, "code": 0, "desc": "请重新登录", "data": {}}
                ),
                200,
            ),
            (
                FakeResponse(
                    {"flag": True, "code": 80000, "desc": "会话失效", "data": {}}
                ),
                200,
            ),
            (
                FakeResponse(
                    {"flag": True, "code": 0, "desc": "请重新登录", "data": {}},
                    status=500,
                ),
                500,
            ),
        ]
        for response, expected_status in cases:
            with self.subTest(status=expected_status):
                client, _ = self.make_client(response)
                with self.assertRaises(MODULE.SessionExpired):
                    client.plan_config(self.account())

    def test_business_error_is_not_success_and_is_sanitized(self):
        client, _ = self.make_client(
            FakeResponse(
                {
                    "flag": True,
                    "code": 7,
                    "desc": "bad request tok",
                    "data": {},
                }
            )
        )
        with self.assertRaises(MODULE.APIError) as raised:
            client.balance(self.account())
        self.assertNotIn(" tok", str(raised.exception))
        self.assertIn("[redacted-token]", str(raised.exception))

    def test_non_json_is_rejected(self):
        client, _ = self.make_client(
            FakeResponse({}, text="<html>login</html>")
        )
        with self.assertRaises(MODULE.APIError):
            client.plan_config(self.account())

    def test_plan_config_accepts_flag_variants(self):
        for value in ("true", 1, 0, None, False):
            with self.subTest(value=value):
                client, _ = self.make_client(
                    FakeResponse(
                        {
                            "flag": True,
                            "code": 0,
                            "data": {"dailyLoginEnabled": value},
                        }
                    )
                )
                config = client.plan_config(self.account())
                self.assertIn("dailyLoginEnabled", config)

    def test_only_boolean_false_disables_activity(self):
        self.assertFalse(MODULE.activity_enabled(False))
        for value in (True, 0, 1, "false", "0", "关闭", None, "unknown"):
            with self.subTest(value=value):
                self.assertTrue(MODULE.activity_enabled(value))

    def test_login_error_without_relogin_is_not_session_expired(self):
        client, _ = self.make_client(
            FakeResponse({"flag": False, "code": 7, "desc": "登录异常"})
        )
        with self.assertRaises(MODULE.APIError):
            client.plan_config(self.account())

    def test_balance_accepts_either_pool(self):
        cases = [
            ({"totalBalance": 5}, Decimal("5"), None),
            ({"sparkTotalBalance": "7.5"}, None, Decimal("7.5")),
        ]
        for data, expected_total, expected_spark in cases:
            with self.subTest(data=data):
                client, _ = self.make_client(
                    FakeResponse({"flag": True, "code": 0, "data": data})
                )
                balance = client.balance(self.account())
                self.assertEqual(balance.total, expected_total)
                self.assertEqual(balance.spark_total, expected_spark)

    def test_balance_rejects_when_both_pools_are_unreadable(self):
        client, _ = self.make_client(
            FakeResponse(
                {
                    "flag": True,
                    "code": 0,
                    "data": {"totalBalance": "bad", "sparkTotalBalance": -1},
                }
            )
        )
        with self.assertRaises(MODULE.APIError):
            client.balance(self.account())

    def test_success_envelope_requires_flag_code_and_data(self):
        payloads = [
            {"code": 0, "data": {}},
            {"flag": True, "data": {}},
            {"flag": True, "code": 0},
            {"flag": "true", "code": 0, "data": {}},
            {"flag": True, "code": "0", "data": None},
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                client, _ = self.make_client(FakeResponse(payload))
                with self.assertRaises(MODULE.APIError):
                    client.plan_config(self.account())

    def test_init_app_is_empty_post_and_requires_banned_false(self):
        client, transport = self.make_client(
            FakeResponse(
                {
                    "flag": True,
                    "code": 0,
                    "data": {"banned": False, "tenantApp": "ok"},
                }
            )
        )
        self.assertEqual(client.init_app(self.account()), {"banned": False, "tenantApp": "ok"})

        session = transport.sessions[0]
        method, url, kwargs = session.calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(
            url,
            "https://agent.xfyun.cn/xingchen-studio/tenant-app/v2/init-app",
        )
        self.assertNotIn("json", kwargs)
        self.assertNotIn("data", kwargs)
        self.assertNotIn("files", kwargs)
        self.assertFalse(kwargs["allow_redirects"])
        self.assertEqual(session.headers["studioVersion"], "3.6.0")

    def test_init_app_rejects_banned_and_incomplete_data(self):
        for data in ({"banned": True}, {}, {"banned": "false"}, []):
            with self.subTest(data=data):
                client, _ = self.make_client(
                    FakeResponse({"flag": True, "code": 0, "data": data})
                )
                with self.assertRaises(MODULE.APIError):
                    client.init_app(self.account())

    def test_claim_daily_rewards_filters_reward_popups_and_posts_complete(self):
        client, transport = self.make_client(
            FakeResponse(
                {
                    "flag": True,
                    "code": 0,
                    "data": [
                        {
                            "popupId": 2,
                            "popupCode": "DAILY_LOGIN_REWARD_V1",
                            "componentType": "DAILY_REWARD_DIALOG",
                            "instanceKey": "20261121",
                        },
                        {
                            "popupId": 7,
                            "componentType": "NEW_USER_DIALOG_V2",
                            "instanceKey": "keep",
                        },
                    ],
                }
            ),
            FakeResponse({"flag": True, "code": 0, "data": None}),
        )
        self.assertEqual(client.claim_daily_rewards(self.account()), 1)
        self.assertEqual(len(transport.sessions), 2)
        pending = transport.sessions[0].calls[0][2]
        self.assertEqual(pending["headers"]["clientType"], "21")
        self.assertEqual(pending["headers"]["studioVersion"], "3.6.0")
        complete = transport.sessions[1].calls[0][2]
        self.assertEqual(
            complete["json"],
            {"popupId": 2, "instanceKey": "20261121", "completed": True},
        )
        self.assertEqual(complete["headers"]["Content-Type"], "application/json")

    def test_each_request_uses_fresh_session_for_account_isolation(self):
        first = MODULE.Account("一", "tok-1", "acct-1", "sso-1")
        second = MODULE.Account("二", "tok-2", "acct-2", "sso-2")
        client, transport = self.make_client(
            FakeResponse(
                {"flag": True, "code": 0, "data": {"dailyLoginEnabled": True}}
            ),
            FakeResponse(
                {"flag": True, "code": 0, "data": {"dailyLoginEnabled": True}}
            ),
        )
        client.plan_config(first)
        client.plan_config(second)

        self.assertEqual(len(transport.sessions), 2)
        self.assertIsNot(transport.sessions[0], transport.sessions[1])
        self.assertEqual(
            transport.sessions[0].calls[0][2]["headers"]["Cookie"],
            first.cookie_header,
        )
        self.assertEqual(
            transport.sessions[1].calls[0][2]["headers"]["Cookie"],
            second.cookie_header,
        )
        self.assertNotIn("tok-2", transport.sessions[0].calls[0][2]["headers"]["Cookie"])
        self.assertNotIn("tok-1", transport.sessions[1].calls[0][2]["headers"]["Cookie"])

    def test_client_type_default_and_environment_override(self):
        cases = [
            ("win32", "", "21"),
            ("linux", "", "21"),
            ("darwin", "", "22"),
            ("linux", "21", "21"),
        ]
        for platform_name, override, expected in cases:
            with self.subTest(
                platform_name=platform_name,
                override=override,
                expected=expected,
            ):
                with mock.patch.object(MODULE.sys, "platform", platform_name):
                    with mock.patch.dict(
                        os.environ,
                        {"ASTUDIO_CLIENT_TYPE": override},
                        clear=False,
                    ):
                        transport = FakeHttpTransport(
                            FakeResponse(
                                {
                                    "flag": True,
                                    "code": 0,
                                    "data": {"totalBalance": 1},
                                }
                            )
                        )
                        client = MODULE.AStudioClient(
                            wait_seconds=0,
                            session_factory=transport,
                        )
                        client.balance(self.account())
                session = transport.sessions[0]
                self.assertEqual(session.headers["studioVersion"], "3.6.0")
                if expected is None:
                    self.assertNotIn("clientType", session.headers)
                    self.assertNotIn("clientType", session.calls[0][2]["headers"])
                else:
                    self.assertEqual(session.headers["clientType"], expected)
                    self.assertEqual(
                        session.calls[0][2]["headers"]["clientType"],
                        expected,
                    )


class FlowTests(unittest.TestCase):
    def account(self):
        return MODULE.Account("主号", "super-secret-token", "account-1234", "sso-5678")

    def test_disabled_plan_is_neutral_and_does_not_read_balance(self):
        client = FakeClient(config={"dailyLoginEnabled": False})
        result = MODULE.run_account(1, self.account(), client, sleeper=lambda _: None)
        self.assertEqual(result.status, "disabled")
        self.assertEqual(client.calls, ["plan-config"])
        self.assertFalse(result.observed)

    def test_non_boolean_daily_login_flag_continues_probe(self):
        for value in (0, 1, "false", "0", "关闭", None, "unknown"):
            with self.subTest(value=value):
                client = FakeClient(
                    config={"dailyLoginEnabled": value},
                    balances=[{"totalBalance": 10}, {"totalBalance": 11}],
                )
                result = MODULE.run_account(
                    1,
                    self.account(),
                    client,
                    sleeper=lambda _: None,
                )
                self.assertEqual(result.status, "observed")
                self.assertIn("init-app", client.calls)

    def test_total_balance_increase_is_only_reported_as_observed(self):
        client = FakeClient(balances=[{"totalBalance": 10}, {"totalBalance": 15}])
        result = MODULE.run_account(1, self.account(), client, sleeper=lambda _: None)
        self.assertEqual(result.status, "observed")
        self.assertEqual(result.delta, Decimal("5"))
        self.assertIn("未区分发放来源", result.message)
        self.assertTrue(result.observed)
        self.assertEqual(
            client.calls,
            [
                "plan-config",
                "points-balance",
                "init-app",
                "client-popups-claim",
                "points-balance",
            ],
        )

    def test_spark_balance_increase_is_observed(self):
        client = FakeClient(
            balances=[
                {"totalBalance": 10, "sparkTotalBalance": 2},
                {"totalBalance": 10, "sparkTotalBalance": 5},
            ]
        )
        result = MODULE.run_account(1, self.account(), client, sleeper=lambda _: None)
        self.assertEqual(result.status, "observed")
        self.assertEqual(result.delta, Decimal("0"))
        self.assertEqual(result.spark_delta, Decimal("3"))
        self.assertIn("星火积分 +3", result.message)
        self.assertTrue(result.observed)

    def test_increase_in_one_pool_is_enough_when_other_is_unreadable(self):
        client = FakeClient(
            balances=[
                {"totalBalance": 10},
                {"totalBalance": 12, "sparkTotalBalance": 5},
            ]
        )
        result = MODULE.run_account(1, self.account(), client, sleeper=lambda _: None)
        self.assertEqual(result.status, "observed")
        self.assertEqual(result.delta, Decimal("2"))
        self.assertIsNone(result.spark_delta)

    def test_zero_growth_without_pending_rewards_is_done(self):
        client = FakeClient(
            balances=[
                {"totalBalance": 10, "sparkTotalBalance": 2},
                {"totalBalance": 10, "sparkTotalBalance": 2},
            ]
        )
        result = MODULE.run_account(1, self.account(), client, sleeper=lambda _: None)
        self.assertEqual(result.status, "done")
        self.assertIn("今天已经领过", result.message)
        self.assertFalse(result.observed)

    def test_server_confirmed_reward_without_balance_refresh_is_claimed(self):
        client = FakeClient(
            balances=[
                {"totalBalance": 10},
                {"totalBalance": 10},
            ],
            claimed_rewards=1,
        )
        result = MODULE.run_account(1, self.account(), client, sleeper=lambda _: None)
        self.assertEqual(result.status, "claimed")
        self.assertEqual(result.claimed_rewards, 1)
        self.assertIn("服务端确认已领取 1 项", result.message)

    def test_claim_error_is_failed_even_after_login(self):
        client = FakeClient(
            balances=[{"totalBalance": 10}, {"totalBalance": 10}],
            claim_error=MODULE.APIError("推广位不存在"),
        )
        result = MODULE.run_account(1, self.account(), client, sleeper=lambda _: None)
        self.assertEqual(result.status, "failed")
        self.assertIn("推广位不存在", result.message)

    def test_init_app_failure_is_failed_without_after_balance(self):
        client = FakeClient(
            balances=[{"totalBalance": 10}, {"totalBalance": 10}],
            init_app=MODULE.APIError("init failed"),
        )
        result = MODULE.run_account(1, self.account(), client, sleeper=lambda _: None)
        self.assertEqual(result.status, "failed")
        self.assertIn("init failed", result.message)
        self.assertEqual(
            client.calls,
            ["plan-config", "points-balance", "init-app"],
        )

    def test_unpaired_pool_readings_fail(self):
        client = FakeClient(
            balances=[
                {"totalBalance": 10},
                {"sparkTotalBalance": 5},
            ]
        )
        result = MODULE.run_account(1, self.account(), client, sleeper=lambda _: None)
        self.assertEqual(result.status, "failed")
        self.assertIn("无法成对读取", result.message)

    def test_both_pools_unreadable_fail(self):
        client = FakeClient(
            balances=[
                MODULE.APIError("points/balance 缺少可读的 totalBalance 或 sparkTotalBalance")
            ]
        )
        result = MODULE.run_account(1, self.account(), client, sleeper=lambda _: None)
        self.assertEqual(result.status, "failed")
        self.assertIn("totalBalance 或 sparkTotalBalance", result.message)

    def test_query_mode_does_not_wait_or_use_after_balance(self):
        waits = []
        client = FakeClient(
            balances=[{"totalBalance": 20}],
        )
        result = MODULE.run_account(
            1,
            self.account(),
            client,
            query_only=True,
            sleeper=lambda seconds: waits.append(seconds),
        )
        self.assertEqual(result.status, "query")
        self.assertEqual(waits, [])
        self.assertIn("未调用 tenant-app/v2/init-app", result.message)
        self.assertEqual(client.calls, ["plan-config", "points-balance"])

    def test_query_mode_reads_balance_even_when_activity_is_disabled(self):
        client = FakeClient(
            config={"dailyLoginEnabled": False},
            balances=[{"totalBalance": 8}],
        )
        result = MODULE.run_account(
            1,
            self.account(),
            client,
            query_only=True,
            sleeper=lambda _: None,
        )
        self.assertEqual(result.status, "query")
        self.assertIn("每日登录活动=未启用", "\n".join(result.detail_lines))
        self.assertEqual(
            client.calls,
            [
                "plan-config",
                "points-balance",
            ],
        )

    def test_session_expired_is_reported_without_secret(self):
        client = FakeClient(
            config=MODULE.SessionExpired("session expired for super-secret-token")
        )
        result = MODULE.run_account(1, self.account(), client, sleeper=lambda _: None)
        self.assertEqual(result.status, "failed")
        self.assertNotIn("super-secret-token", result.message)
        self.assertIn("[redacted-token]", result.message)

    def test_simulated_http_spark_growth_end_to_end(self):
        transport = FakeHttpTransport(
            FakeResponse(
                {
                    "flag": True,
                    "code": 0,
                    "data": {"dailyLoginEnabled": True, "planName": "Free"},
                }
            ),
            FakeResponse(
                {
                    "flag": True,
                    "code": 0,
                    "data": {"totalBalance": 10, "sparkTotalBalance": 2},
                }
            ),
            FakeResponse(
                {
                    "flag": True,
                    "code": 0,
                    "data": {"banned": False, "tenantApp": "ready"},
                }
            ),
            FakeResponse(
                {
                    "flag": True,
                    "code": 0,
                    "data": [
                        {
                            "popupId": 2,
                            "popupCode": "DAILY_LOGIN_REWARD_V1",
                            "componentType": "DAILY_REWARD_DIALOG",
                            "instanceKey": "20261121",
                        }
                    ],
                }
            ),
            FakeResponse({"flag": True, "code": 0, "data": None}),
            FakeResponse(
                {
                    "flag": True,
                    "code": 0,
                    "data": {"totalBalance": 10, "sparkTotalBalance": 5},
                }
            ),
        )
        client = MODULE.AStudioClient(
            wait_seconds=0,
            client_type="22",
            session_factory=transport,
        )
        waits = []
        result = MODULE.run_account(
            1,
            self.account(),
            client,
            sleeper=lambda seconds: waits.append(seconds),
        )

        self.assertEqual(result.status, "observed")
        self.assertEqual(result.claimed_rewards, 1)
        self.assertEqual(result.spark_delta, Decimal("3"))
        self.assertEqual(waits, [0.0])
        self.assertEqual(len(transport.sessions), 6)
        self.assertEqual(
            [session.calls[0][0] for session in transport.sessions],
            ["GET", "GET", "POST", "GET", "POST", "GET"],
        )
        for session in transport.sessions:
            self.assertEqual(session.headers["clientType"], "22")
            self.assertEqual(session.headers["studioVersion"], "3.6.0")
            _, _, kwargs = session.calls[0]
            self.assertEqual(kwargs["headers"]["Cookie"], self.account().cookie_header)
            self.assertFalse(kwargs["allow_redirects"])
        init_kwargs = transport.sessions[2].calls[0][2]
        self.assertNotIn("json", init_kwargs)
        self.assertNotIn("data", init_kwargs)
        self.assertNotIn("files", init_kwargs)
        complete_kwargs = transport.sessions[4].calls[0][2]
        self.assertEqual(
            complete_kwargs["json"],
            {"popupId": 2, "instanceKey": "20261121", "completed": True},
        )
        self.assertEqual(
            complete_kwargs["headers"]["Content-Type"],
            "application/json",
        )

    def test_simulated_http_banned_skips_after_balance(self):
        transport = FakeHttpTransport(
            FakeResponse(
                {"flag": True, "code": 0, "data": {"dailyLoginEnabled": True}}
            ),
            FakeResponse(
                {
                    "flag": True,
                    "code": 0,
                    "data": {"totalBalance": 10, "sparkTotalBalance": 2},
                }
            ),
            FakeResponse(
                {"flag": True, "code": 0, "data": {"banned": True}}
            ),
        )
        client = MODULE.AStudioClient(
            wait_seconds=0,
            client_type="21",
            session_factory=transport,
        )
        result = MODULE.run_account(
            1,
            self.account(),
            client,
            sleeper=lambda _: self.fail("banned request must not wait"),
        )
        self.assertEqual(result.status, "failed")
        self.assertIn("封禁", result.message)
        self.assertEqual(len(transport.sessions), 3)

    def test_report_does_not_claim_success_without_observed_growth(self):
        results = [
            MODULE.RunResult(
                1,
                "a",
                "failed",
                "未观察到正增长",
                before=Decimal("1"),
                after=Decimal("1"),
            ),
            MODULE.RunResult(2, "b", "disabled", "未启用"),
        ]
        report = MODULE.build_report(results, False)
        self.assertIn("没有账号观察到余额增长", report)


class NotificationTests(unittest.TestCase):
    def test_pushplus_success(self):
        with mock.patch.dict(os.environ, {"PUSHPLUS_TOKEN": "token"}, clear=False):
            with mock.patch.object(MODULE, "post_json", return_value={"code": 200}):
                self.assertTrue(MODULE.notify_pushplus("title", "body"))

    def test_bark_success(self):
        captured = {}

        def fake_post(url, payload, timeout=15):
            captured["url"] = url
            captured["payload"] = payload
            return {"code": 200}

        with mock.patch.dict(
            os.environ, {"BARK_URL": "https://api.day.app/device-key/"}, clear=False
        ):
            with mock.patch.object(MODULE, "post_json", side_effect=fake_post):
                self.assertTrue(MODULE.notify_bark("title", "body"))
        self.assertEqual("https://api.day.app/device-key", captured["url"])
        self.assertEqual("body", captured["payload"]["body"])

    def test_wecom_key_is_expanded(self):
        captured = {}

        def fake_post(url, payload, timeout=15):
            captured["url"] = url
            captured["payload"] = payload
            return {"errcode": 0}

        with mock.patch.dict(os.environ, {"WECOM_WEBHOOK": "abc"}, clear=False):
            with mock.patch.object(MODULE, "post_json", side_effect=fake_post):
                self.assertTrue(MODULE.notify_wecom("title", "body"))
        self.assertIn("key=abc", captured["url"])
        self.assertEqual(captured["payload"]["msgtype"], "text")

    def test_no_channels_does_not_print_secret(self):
        with mock.patch.dict(
            os.environ,
            {"PUSHPLUS_TOKEN": "", "BARK_URL": "", "WECOM_WEBHOOK": ""},
            clear=False,
        ):
            with mock.patch.object(MODULE, "log") as logger:
                MODULE.notify_all("title", "super-secret-token")
        rendered = "\n".join(str(call) for call in logger.call_args_list)
        self.assertNotIn("super-secret-token", rendered)


class MainCliTests(unittest.TestCase):
    def test_only_no_notify_and_failed_exit_code_are_applied(self):
        accounts = [
            MODULE.Account("一号", "tok-1", "acct-1"),
            MODULE.Account("二号", "tok-2", "acct-2"),
        ]
        expected = MODULE.RunResult(2, "二号", "failed", "未观察到正增长")
        with mock.patch.object(MODULE, "load_accounts", return_value=accounts):
            with mock.patch.object(MODULE, "AStudioClient"):
                with mock.patch.object(
                    MODULE, "run_account", return_value=expected
                ) as runner:
                    with mock.patch.object(MODULE, "notify_all") as notifier:
                        with mock.patch.object(MODULE, "log"):
                            code = MODULE.main(["--only", "2", "--no-notify"])
        self.assertEqual(code, 1)
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(runner.call_args.args[0], 2)
        self.assertFalse(notifier.called)


if __name__ == "__main__":
    unittest.main()
