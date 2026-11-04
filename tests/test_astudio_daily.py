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


class FakeClient:
    def __init__(
        self,
        config=None,
        balances=None,
        membership=None,
        summary=None,
        wait_seconds=2.5,
    ):
        self.config = config or {"dailyLoginEnabled": True}
        self.balances = list(balances or [{"totalBalance": 100}])
        self.membership_data = (
            membership if membership is not None else {"planName": "Free"}
        )
        self.summary_data = summary if summary is not None else {"today": []}
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
            total=MODULE.decimal_value(value["totalBalance"], "totalBalance")
        )

    def membership(self, account):
        self.calls.append("membership-me")
        if isinstance(self.membership_data, Exception):
            raise self.membership_data
        return self.membership_data

    def points_summary(self, account):
        self.calls.append("points-summary")
        if isinstance(self.summary_data, Exception):
            raise self.summary_data
        return self.summary_data


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
    def make_client(self):
        client = MODULE.AStudioClient(wait_seconds=0)
        client.session.get = mock.Mock()
        return client

    def test_success_envelope_and_request_headers(self):
        client = self.make_client()
        client.session.get.return_value = FakeResponse(
            {"flag": True, "code": 0, "data": {"totalBalance": 12.5}}
        )
        account = MODULE.Account("a", "tok", "acct", "sso")
        balance = client.balance(account)
        self.assertEqual(balance.total, Decimal("12.5"))
        kwargs = client.session.get.call_args.kwargs
        self.assertEqual(
            kwargs["headers"]["Cookie"],
            "ssoSessionId=sso; sso_sessionid=sso; account_id=acct; token=tok",
        )
        self.assertEqual(kwargs["headers"], {"Cookie": account.cookie_header})
        self.assertFalse(kwargs["allow_redirects"])

    def test_http_401_is_session_expired(self):
        client = self.make_client()
        client.session.get.return_value = FakeResponse({}, status=401)
        with self.assertRaises(MODULE.SessionExpired):
            client.plan_config(MODULE.Account("a", "tok", "acct"))

    def test_code_80000_is_session_expired(self):
        client = self.make_client()
        client.session.get.return_value = FakeResponse(
            {"flag": False, "code": 80000, "desc": "登录异常，请重新登录"}
        )
        with self.assertRaises(MODULE.SessionExpired):
            client.plan_config(MODULE.Account("a", "tok", "acct"))

    def test_business_error_is_not_success(self):
        client = self.make_client()
        client.session.get.return_value = FakeResponse(
            {"flag": True, "code": 7, "desc": "bad request", "data": {}}
        )
        with self.assertRaises(MODULE.APIError):
            client.balance(MODULE.Account("a", "tok", "acct"))

    def test_non_json_is_rejected(self):
        client = self.make_client()
        client.session.get.return_value = FakeResponse({}, text="<html>login</html>")
        with self.assertRaises(MODULE.APIError):
            client.plan_config(MODULE.Account("a", "tok", "acct"))

    def test_plan_config_accepts_upstream_flag_variants(self):
        client = self.make_client()
        for value in ("true", 1, 0, None, False):
            with self.subTest(value=value):
                client.session.get.return_value = FakeResponse(
                    {
                        "flag": True,
                        "code": 0,
                        "data": {"dailyLoginEnabled": value},
                    }
                )
                config = client.plan_config(MODULE.Account("a", "tok", "acct"))
                self.assertIn("dailyLoginEnabled", config)

    def test_explicit_false_flag_variants_are_disabled(self):
        for value in (False, 0, "false", "0", "关闭"):
            with self.subTest(value=value):
                self.assertFalse(MODULE.activity_enabled(value))
        for value in (True, 1, "true", "1", None, "unknown"):
            with self.subTest(value=value):
                self.assertTrue(MODULE.activity_enabled(value))

    def test_login_error_without_relogin_is_not_session_expired(self):
        client = self.make_client()
        client.session.get.return_value = FakeResponse(
            {"flag": False, "code": 7, "desc": "登录异常"}
        )
        with self.assertRaises(MODULE.APIError):
            client.plan_config(MODULE.Account("a", "tok", "acct"))

    def test_balance_requires_total_balance(self):
        client = self.make_client()
        client.session.get.return_value = FakeResponse(
            {"flag": True, "code": 0, "data": {"activityBalance": 1}}
        )
        with self.assertRaises(MODULE.APIError):
            client.balance(MODULE.Account("a", "tok", "acct"))


class FlowTests(unittest.TestCase):
    def account(self):
        return MODULE.Account("主号", "super-secret-token", "account-1234", "sso-5678")

    def test_disabled_plan_is_neutral_and_does_not_read_balance(self):
        client = FakeClient(config={"dailyLoginEnabled": False})
        result = MODULE.run_account(1, self.account(), client, sleeper=lambda _: None)
        self.assertEqual(result.status, "disabled")
        self.assertEqual(client.calls, ["plan-config"])
        self.assertFalse(result.observed)

    def test_balance_increase_is_only_reported_as_observed(self):
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
                "membership-me",
                "points-summary",
                "points-balance",
            ],
        )

    def test_unchanged_balance_is_neutral(self):
        client = FakeClient(balances=[{"totalBalance": 10}, {"totalBalance": 10}])
        result = MODULE.run_account(1, self.account(), client, sleeper=lambda _: None)
        self.assertEqual(result.status, "unchanged")
        self.assertIn("可能今日已签到", result.message)
        self.assertFalse(result.observed)

    def test_failed_touch_plus_no_increase_is_failed(self):
        client = FakeClient(
            balances=[{"totalBalance": 10}, {"totalBalance": 10}],
            summary=MODULE.APIError("summary failed"),
        )
        result = MODULE.run_account(1, self.account(), client, sleeper=lambda _: None)
        self.assertEqual(result.status, "failed")
        self.assertIn("活跃触发不完整", result.message)

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
        self.assertIn("未调用 membership/me", result.message)
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

    def test_report_does_not_claim_success_when_all_neutral(self):
        results = [
            MODULE.RunResult(
                1,
                "a",
                "unchanged",
                "余额无变化",
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
    def test_only_and_no_notify_are_applied(self):
        accounts = [
            MODULE.Account("一号", "tok-1", "acct-1"),
            MODULE.Account("二号", "tok-2", "acct-2"),
        ]
        expected = MODULE.RunResult(2, "二号", "unchanged", "余额无变化")
        with mock.patch.object(MODULE, "load_accounts", return_value=accounts):
            with mock.patch.object(MODULE, "AStudioClient"):
                with mock.patch.object(
                    MODULE, "run_account", return_value=expected
                ) as runner:
                    with mock.patch.object(MODULE, "notify_all") as notifier:
                        with mock.patch.object(MODULE, "log"):
                            code = MODULE.main(["--only", "2", "--no-notify"])
        self.assertEqual(code, 0)
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(runner.call_args.args[0], 2)
        self.assertFalse(notifier.called)


if __name__ == "__main__":
    unittest.main()
