#!/usr/bin/env python3
"""AStudio（科大讯飞 Astron Studio）每日登录积分观测工具。

上游事实（Agent2Providers v3.4.2 / 3055f416，只读协议证据）：
  - 每日登录奖励由桌面端启动时的账号初始化触发，没有独立 claim 接口。
  - 账号面根地址：https://agent.xfyun.cn/xingchen-studio/
  - 配置：GET membership/plan-config
  - 余额：GET points/balance
  - 活跃触发：POST tenant-app/v2/init-app，带 Cookie，无请求体
  - 账号面请求统一发送 studioVersion=3.5.1；仅在 Windows/macOS 或环境覆盖时
    发送 clientType（Windows 21、macOS 22）。
  - 成功信封必须同时满足 flag=true、code=0、data 非空；init-app 的 data
    还必须包含布尔 banned，且 banned=false。
  - 签到前后分别读取 totalBalance 与 sparkTotalBalance，任一积分池明确正增长
    才报告 observed；两池都无法成对读取时失败，零增长不伪报成功。

本脚本只使用网页会话 Cookie，不持久化凭据，不读取桌面端文件。

环境变量：
  ASTUDIO_COOKIES       多账号 Cookie，换行或 & 分隔
  ASTUDIO_ACCOUNT_FILE  可选账号文件；未设置时尝试 ./astudio_accounts.txt
  ASTUDIO_PROXY         可选 HTTP(S) 代理
  ASTUDIO_CLIENT_TYPE   可选客户端类型覆盖；Windows 默认 21、macOS 默认 22
  ASTUDIO_WAIT_SECONDS  活跃触发后的等待秒数，默认 2.5
  PUSHPLUS_TOKEN        PushPlus token
  BARK_URL              Bark URL
  WECOM_WEBHOOK         企业微信机器人完整 URL 或 key

用法：
  python astudio_daily.py
  python astudio_daily.py --query
  python astudio_daily.py --only 1,3
  python astudio_daily.py --no-notify
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import requests

VERSION = "1.1.0"
ACCOUNT_API_BASE = "https://agent.xfyun.cn/xingchen-studio/"
PLAN_CONFIG_PATH = "membership/plan-config"
POINTS_BALANCE_PATH = "points/balance"
INIT_APP_PATH = "tenant-app/v2/init-app"
STUDIO_VERSION = "3.5.1"
DEFAULT_ACCOUNT_FILE = "astudio_accounts.txt"
DEFAULT_TIMEOUT = 20
DEFAULT_WAIT_SECONDS = 2.5
USER_AGENT = "undici"
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?86[- ]?)?(1[3-9]\d{9})(?!\d)")
class AStudioError(Exception):
    """AStudio Daily 的受控错误基类。"""


class AccountConfigError(AStudioError):
    """账号配置格式错误。"""


class SessionExpired(AStudioError):
    """网页会话失效，需要重新获取 Cookie。"""


class APIError(AStudioError):
    """HTTP、JSON 信封或业务字段错误。"""


@dataclass(frozen=True)
class Account:
    name: str
    token: str
    account_id: str
    sso_session_id: str = ""

    @property
    def label(self) -> str:
        if self.name:
            return redact_phone(self.name)
        return "AStudio-%s" % mask_secret(self.account_id, keep=3)

    @property
    def cookie_header(self) -> str:
        parts: List[str] = []
        if self.sso_session_id:
            parts.append("ssoSessionId=%s" % self.sso_session_id)
            parts.append("sso_sessionid=%s" % self.sso_session_id)
        if self.account_id:
            parts.append("account_id=%s" % self.account_id)
        if self.token:
            parts.append("token=%s" % self.token)
        return "; ".join(parts)

    @property
    def fingerprint(self) -> Tuple[str, str]:
        return (self.token, self.account_id)


@dataclass
class Balance:
    total: Optional[Decimal] = None
    activity: Optional[Decimal] = None
    activity_next_expire: Optional[str] = None
    spark_total: Optional[Decimal] = None


@dataclass
class RunResult:
    index: int
    label: str
    status: str
    message: str
    before: Optional[Decimal] = None
    after: Optional[Decimal] = None
    delta: Optional[Decimal] = None
    before_spark: Optional[Decimal] = None
    after_spark: Optional[Decimal] = None
    spark_delta: Optional[Decimal] = None
    plan: str = ""
    plan_name: str = ""
    detail_lines: List[str] = field(default_factory=list)

    @property
    def failed(self) -> bool:
        return self.status == "failed"

    @property
    def observed(self) -> bool:
        return self.status == "observed"


def print_safe(text: str) -> None:
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        safe_text = text.encode(encoding, errors="replace").decode(
            encoding, errors="replace"
        )
        print(safe_text, flush=True)


def log(message: str) -> None:
    print_safe("%s %s" % (time.strftime("[%H:%M:%S]"), message))


def env_text(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def configured_client_type() -> Optional[str]:
    override = env_text("ASTUDIO_CLIENT_TYPE")
    if override:
        return override
    if sys.platform.startswith("win"):
        return "21"
    if sys.platform == "darwin":
        return "22"
    return None


def redact_phone(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        phone = match.group(1)
        return "%s****%s" % (phone[:3], phone[-4:])

    return PHONE_PATTERN.sub(replace, str(text or ""))


def mask_secret(value: Any, keep: int = 4) -> str:
    text = str(value or "").strip()
    if not text:
        return "-"
    if len(text) <= keep + 4:
        return "****"
    return "%s****%s" % (text[:keep], text[-4:])


def sanitize_message(message: Any, account: Optional[Account] = None) -> str:
    text = str(message or "").replace("\r", " ").replace("\n", " ").strip()
    if account is not None:
        for secret, replacement in (
            (account.token, "[redacted-token]"),
            (account.sso_session_id, "[redacted-sso]"),
            (account.account_id, mask_secret(account.account_id, keep=3)),
        ):
            if secret:
                text = text.replace(secret, replacement)
    for env_name in (
        "PUSHPLUS_TOKEN",
        "BARK_URL",
        "WECOM_WEBHOOK",
        "ASTUDIO_PROXY",
    ):
        value = env_text(env_name)
        if value:
            text = text.replace(value, "[redacted-%s]" % env_name.lower())
    return redact_phone(text)[:800]


def balance_pool_value(value: Any) -> Optional[Decimal]:
    """Read one balance pool without treating an invalid sibling as fatal."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite() or number < 0:
        return None
    return number


def activity_enabled(value: Any) -> bool:
    """Only boolean false disables the activity; other types continue probing."""
    return value is not False


def format_decimal(value: Optional[Decimal]) -> str:
    if value is None:
        return "-"
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(normalized.quantize(Decimal("1")))
    return format(normalized, "f").rstrip("0").rstrip(".")


def split_account_entries(raw: str) -> List[str]:
    text = (raw or "").strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as error:
            raise AccountConfigError("账号 JSON 格式错误：%s" % error.msg)
        if not isinstance(payload, list):
            raise AccountConfigError("账号 JSON 顶层必须是数组")
        return [json.dumps(item, ensure_ascii=False) for item in payload]
    entries: List[str] = []
    for line in re.split(r"\r?\n|&", text):
        entry = line.strip().strip('"').strip("'")
        if entry and not entry.startswith("#"):
            entries.append(entry)
    return entries


def parse_cookie_header(cookie: str, name: str = "") -> Account:
    values: Dict[str, str] = {}
    for part in cookie.split(";"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        normalized = key.strip().lower()
        if normalized in {
            "token",
            "account_id",
            "accountid",
            "sso_sessionid",
            "ssosessionid",
            "sso_session_id",
        }:
            values[normalized] = value.strip()
    token = values.get("token", "")
    account_id = values.get("account_id", "") or values.get("accountid", "")
    sso_session_id = (
        values.get("sso_sessionid", "")
        or values.get("ssosessionid", "")
        or values.get("sso_session_id", "")
    )
    if not account_id:
        raise AccountConfigError("Cookie 必须包含 account_id")
    return Account(
        name=name.strip(),
        token=token,
        account_id=account_id,
        sso_session_id=sso_session_id,
    )


def account_from_json_object(
    payload: Dict[str, Any], fallback_name: str = ""
) -> Account:
    session = payload.get("session")
    session_value = session if isinstance(session, dict) else {}

    def pick(*keys: str) -> str:
        for key in keys:
            value = payload.get(key)
            if value is None:
                value = session_value.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return ""

    token = pick("token", "sessionToken")
    account_id = pick("accountId", "account_id")
    sso_session_id = pick("ssoSessionId", "sso_sessionid")
    name = pick("name") or fallback_name
    if not account_id:
        raise AccountConfigError(
            "JSON 账号必须包含 accountId/session.accountId"
        )
    return Account(
        name=name.strip(),
        token=token,
        account_id=account_id,
        sso_session_id=sso_session_id,
    )


def parse_account_entry(entry: str, index: int) -> Account:
    text = entry.strip()
    if text.startswith("{"):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as error:
            raise AccountConfigError("第 %d 个账号 JSON 错误：%s" % (index, error.msg))
        if not isinstance(payload, dict):
            raise AccountConfigError("第 %d 个账号 JSON 必须是对象" % index)
        return account_from_json_object(payload)
    if "|" in text:
        parts = [part.strip() for part in text.split("|")]
        if len(parts) not in (3, 4):
            raise AccountConfigError(
                "第 %d 个账号格式应为 备注|token|account_id|sso_session_id" % index
            )
        name, token, account_id = parts[:3]
        sso_session_id = parts[3] if len(parts) == 4 else ""
        if not token or not account_id:
            raise AccountConfigError("第 %d 个账号缺少 token 或 account_id" % index)
        return Account(
            name=name,
            token=token,
            account_id=account_id,
            sso_session_id=sso_session_id,
        )
    return parse_cookie_header(text)


def parse_accounts(raw: str) -> List[Account]:
    accounts: List[Account] = []
    seen: Set[Tuple[str, str, str]] = set()
    for index, entry in enumerate(split_account_entries(raw), 1):
        account = parse_account_entry(entry, index)
        if account.fingerprint in seen:
            continue
        seen.add(account.fingerprint)
        accounts.append(account)
    return accounts


def load_accounts() -> List[Account]:
    sources: List[Tuple[str, str]] = []
    env_cookies = env_text("ASTUDIO_COOKIES")
    if env_cookies:
        sources.append(("ASTUDIO_COOKIES", env_cookies))

    configured_path = env_text("ASTUDIO_ACCOUNT_FILE")
    default_path = Path(__file__).resolve().with_name(DEFAULT_ACCOUNT_FILE)
    account_path = Path(configured_path) if configured_path else default_path
    if configured_path or account_path.exists():
        try:
            file_text = account_path.read_text(encoding="utf-8")
        except OSError as error:
            raise AccountConfigError(
                "读取账号文件失败：%s" % (error.strerror or "I/O error")
            )
        if file_text.strip():
            sources.append((account_path.name, file_text))

    if not sources:
        raise AccountConfigError(
            "未配置账号。请设置 ASTUDIO_COOKIES，或创建 "
            "ASTUDIO_ACCOUNT_FILE/astudio_accounts.txt"
        )

    accounts: List[Account] = []
    seen: Set[Tuple[str, str, str]] = set()
    for source_name, raw in sources:
        try:
            parsed = parse_accounts(raw)
        except AccountConfigError as error:
            raise AccountConfigError("%s：%s" % (source_name, error))
        for account in parsed:
            if account.fingerprint in seen:
                continue
            seen.add(account.fingerprint)
            accounts.append(account)
    if not accounts:
        raise AccountConfigError("账号配置中没有有效账号")
    return accounts


def parse_only(value: str, account_count: int) -> Set[int]:
    selected: Set[int] = set()
    for chunk in value.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start_text, end_text = chunk.split("-", 1)
            try:
                start, end = int(start_text), int(end_text)
            except ValueError:
                raise AccountConfigError("--only 格式错误：%s" % chunk)
            if start > end:
                start, end = end, start
            selected.update(range(start, end + 1))
        else:
            try:
                selected.add(int(chunk))
            except ValueError:
                raise AccountConfigError("--only 格式错误：%s" % chunk)
    if not selected:
        raise AccountConfigError("--only 不能为空")
    invalid = sorted(
        number for number in selected if number < 1 or number > account_count
    )
    if invalid:
        raise AccountConfigError(
            "--only 超出账号范围 1..%d：%s"
            % (account_count, ",".join(str(number) for number in invalid))
        )
    return selected


class AStudioClient:
    def __init__(
        self,
        proxy: str = "",
        timeout: int = DEFAULT_TIMEOUT,
        wait_seconds: float = DEFAULT_WAIT_SECONDS,
        client_type: Optional[str] = None,
        session_factory: Any = None,
    ) -> None:
        self.timeout = timeout
        self.wait_seconds = wait_seconds
        self.proxy = proxy
        resolved_client_type = client_type or configured_client_type()
        self.client_type = (
            str(resolved_client_type).strip() if resolved_client_type else None
        )
        self.session_factory = session_factory or requests.Session
        self.headers = {
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            "studioVersion": STUDIO_VERSION,
        }
        if self.client_type:
            self.headers["clientType"] = self.client_type

    def _url(self, path: str) -> str:
        return ACCOUNT_API_BASE + path.lstrip("/")

    def _new_session(self) -> requests.Session:
        session = self.session_factory()
        session.headers.update(self.headers)
        if self.proxy:
            session.proxies.update({"http": self.proxy, "https": self.proxy})
        return session

    def _request(self, account: Account, method: str, path: str) -> Any:
        url = self._url(path)
        session = self._new_session()
        try:
            headers = dict(self.headers)
            headers["Cookie"] = account.cookie_header
            kwargs = {
                "headers": headers,
                "timeout": self.timeout,
                "allow_redirects": False,
            }
            if method == "GET":
                response = session.get(url, **kwargs)
            elif method == "POST":
                response = session.post(url, **kwargs)
            else:
                raise APIError("不支持的账号面请求方法：%s" % method)
        except requests.RequestException as error:
            raise APIError(
                sanitize_message("%s 网络请求失败：%s" % (path, error), account)
            )
        finally:
            session.close()

        status = response.status_code
        if status in (401, 403):
            raise SessionExpired(
                "AStudio 会话已失效（HTTP %d），请重新获取 Cookie" % status
            )

        try:
            payload = json.loads(
                response.text,
                parse_float=Decimal,
                parse_int=int,
            )
        except (json.JSONDecodeError, TypeError):
            raise APIError("%s 返回的不是 JSON（HTTP %d）" % (path, status))
        if not isinstance(payload, dict):
            raise APIError("%s 返回的 JSON 顶层不是对象（HTTP %d）" % (path, status))

        code = payload.get("code")
        desc = payload.get("desc") or payload.get("message") or payload.get("msg") or ""
        desc_text = sanitize_message(desc, account)
        code_text = str(code).strip() if code is not None else ""

        failed = (
            not 200 <= status < 300
            or payload.get("flag") is False
            or (code is not None and code_text != "0")
        )
        if failed:
            if code_text == "80000" or "重新登录" in desc_text:
                raise SessionExpired(
                    "AStudio 会话已失效：%s" % (desc_text or "需要重新登录")
                )
            detail = "：%s" % desc_text if desc_text else ""
            raise APIError("%s 失败（HTTP %d）%s" % (path, status, detail))

        if payload.get("flag") is not True or code_text != "0":
            raise APIError("%s 返回的成功状态不完整（HTTP %d）" % (path, status))

        if "data" not in payload or payload.get("data") is None:
            raise APIError("%s 返回的数据不完整（HTTP %d）" % (path, status))

        data = payload.get("data")
        return data

    def get(self, account: Account, path: str) -> Any:
        return self._request(account, "GET", path)

    def post_empty(self, account: Account, path: str) -> Any:
        return self._request(account, "POST", path)

    def plan_config(self, account: Account) -> Dict[str, Any]:
        data = self.get(account, PLAN_CONFIG_PATH)
        if not isinstance(data, dict):
            raise APIError("membership/plan-config 的 data 不是对象")
        return data

    def balance(self, account: Account) -> Balance:
        data = self.get(account, POINTS_BALANCE_PATH)
        if not isinstance(data, dict):
            raise APIError("points/balance 的 data 不是对象")
        balance = Balance(
            total=balance_pool_value(data.get("totalBalance")),
            activity=balance_pool_value(data.get("activityBalance")),
            activity_next_expire=(
                str(data.get("activityNextExpireTime"))
                if data.get("activityNextExpireTime") is not None
                else None
            ),
            spark_total=balance_pool_value(data.get("sparkTotalBalance")),
        )
        if balance.total is None and balance.spark_total is None:
            raise APIError(
                "points/balance 缺少可读的 totalBalance 或 sparkTotalBalance"
            )
        return balance

    def init_app(self, account: Account) -> Dict[str, Any]:
        data = self.post_empty(account, INIT_APP_PATH)
        if not isinstance(data, dict):
            raise APIError("tenant-app/v2/init-app 的 data 不是对象")
        if not isinstance(data.get("banned"), bool):
            raise APIError("tenant-app/v2/init-app 的 data 缺少布尔字段 banned")
        if data["banned"]:
            raise APIError("AStudio 账号已被封禁，无法签到")
        return data


def balance_detail(balance: Balance) -> str:
    parts: List[str] = []
    if balance.total is not None:
        parts.append("通用积分=%s" % format_decimal(balance.total))
    if balance.spark_total is not None:
        parts.append("星火积分=%s" % format_decimal(balance.spark_total))
    if balance.activity is not None:
        parts.append("活动积分=%s" % format_decimal(balance.activity))
    if balance.activity_next_expire:
        parts.append("活动积分到期=%s" % balance.activity_next_expire)
    return "；".join(parts) if parts else "无可读积分"


def result_line(result: RunResult) -> str:
    icon = {
        "observed": "✅",
        "disabled": "ℹ️",
        "query": "🔎",
        "failed": "❌",
    }.get(result.status, "•")
    return "%s 账号%d %s：%s" % (icon, result.index, result.label, result.message)


def run_account(
    index: int,
    account: Account,
    client: AStudioClient,
    query_only: bool = False,
    sleeper: Any = time.sleep,
) -> RunResult:
    label = account.label
    try:
        config = client.plan_config(account)
        enabled = activity_enabled(config.get("dailyLoginEnabled"))

        if query_only:
            balance = client.balance(account)
            details = [
                "每日登录活动=%s" % ("启用" if enabled else "未启用"),
                balance_detail(balance),
            ]
            return RunResult(
                index=index,
                label=label,
                status="query",
                message="查询完成；未调用 tenant-app/v2/init-app",
                before=balance.total,
                before_spark=balance.spark_total,
                plan="AStudio",
                plan_name=str(config.get("planName") or ""),
                detail_lines=details,
            )

        if not enabled:
            return RunResult(
                index=index,
                label=label,
                status="disabled",
                message="当前没有启用每日登录积分活动",
                plan="AStudio",
                plan_name=str(config.get("planName") or ""),
            )

        before = client.balance(account)
        client.init_app(account)
        wait_seconds = max(0.0, float(client.wait_seconds))
        sleeper(wait_seconds)
        after = client.balance(account)

        delta = (
            after.total - before.total
            if before.total is not None and after.total is not None
            else None
        )
        spark_delta = (
            after.spark_total - before.spark_total
            if before.spark_total is not None and after.spark_total is not None
            else None
        )

        detail_lines = [
            "签到前：%s" % balance_detail(before),
            "签到后：%s" % balance_detail(after),
        ]

        if delta is None and spark_delta is None:
            return RunResult(
                index=index,
                label=label,
                status="failed",
                message="签到前后两个积分池都无法成对读取，不能核对奖励到账",
                before=before.total,
                after=after.total,
                before_spark=before.spark_total,
                after_spark=after.spark_total,
                plan="AStudio",
                detail_lines=detail_lines,
            )

        growth_lines: List[str] = []
        if delta is not None and delta > 0:
            growth_lines.append("通用积分 +%s" % format_decimal(delta))
        if spark_delta is not None and spark_delta > 0:
            growth_lines.append("星火积分 +%s" % format_decimal(spark_delta))

        if growth_lines:
            return RunResult(
                index=index,
                label=label,
                status="observed",
                message=(
                    "本轮观察到积分正增长：%s；仅证明观察到余额变化，未区分发放来源"
                    % "，".join(growth_lines)
                ),
                before=before.total,
                after=after.total,
                delta=delta,
                before_spark=before.spark_total,
                after_spark=after.spark_total,
                spark_delta=spark_delta,
                plan="AStudio",
                detail_lines=detail_lines,
            )

        return RunResult(
            index=index,
            label=label,
            status="failed",
            message=(
                "每日登录初始化成功，但未观察到任何积分池正增长；"
                "可能今日已领取或尚未到账，本次不确认成功"
            ),
            before=before.total,
            after=after.total,
            delta=delta,
            before_spark=before.spark_total,
            after_spark=after.spark_total,
            spark_delta=spark_delta,
            plan="AStudio",
            detail_lines=detail_lines,
        )
    except SessionExpired as error:
        return RunResult(
            index=index,
            label=label,
            status="failed",
            message=sanitize_message(error, account),
            plan="AStudio",
        )
    except AStudioError as error:
        return RunResult(
            index=index,
            label=label,
            status="failed",
            message=sanitize_message(error, account),
            plan="AStudio",
        )


def post_json(url: str, payload: Dict[str, Any], timeout: int = 15) -> Dict[str, Any]:
    try:
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {}
    except (requests.RequestException, ValueError) as error:
        log("⚠️ 推送请求失败：%s" % error.__class__.__name__)
        return {}


def notify_pushplus(title: str, content: str) -> bool:
    token = env_text("PUSHPLUS_TOKEN")
    if not token:
        return False
    text = content[:18000] + "\n...(已截断)" if len(content) > 18000 else content
    answer = post_json(
        "https://www.pushplus.plus/send",
        {"token": token, "title": title, "content": text, "template": "txt"},
    )
    ok = str(answer.get("code")) == "200"
    log("📢 PushPlus：%s" % ("成功" if ok else "失败"))
    return ok


def notify_bark(title: str, content: str) -> bool:
    endpoint = env_text("BARK_URL").rstrip("/")
    if not endpoint:
        return False
    answer = post_json(
        endpoint,
        {"title": title, "body": content[:5000], "group": "AStudio Daily"},
    )
    ok = answer.get("code") == 200
    log("📢 Bark：%s" % ("成功" if ok else "失败"))
    return ok


def notify_wecom(title: str, content: str) -> bool:
    hook = env_text("WECOM_WEBHOOK")
    if not hook:
        return False
    if not hook.startswith("http"):
        hook = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=" + hook
    answer = post_json(
        hook,
        {
            "msgtype": "text",
            "text": {"content": ("%s\n%s" % (title, content))[:2000]},
        },
    )
    ok = answer.get("errcode") == 0
    log("📢 企业微信：%s" % ("成功" if ok else "失败"))
    return ok


def notify_all(title: str, content: str) -> None:
    configured = False
    results = [notify_pushplus, notify_bark, notify_wecom]
    for handler in results:
        try:
            configured = handler(title, content) or configured
        except Exception as error:
            log("⚠️ 推送异常：%s" % sanitize_message(error))
    if not configured:
        log("ℹ️ 未配置可用推送渠道，或本轮所有渠道均失败")


def build_report(results: Sequence[RunResult], query_only: bool) -> str:
    observed = sum(1 for item in results if item.status == "observed")
    disabled = sum(1 for item in results if item.status == "disabled")
    queried = sum(1 for item in results if item.status == "query")
    failed = sum(1 for item in results if item.status == "failed")
    lines = [
        "AStudio Daily %s" % VERSION,
        "模式：%s" % ("仅查询" if query_only else "每日登录积分观测"),
        (
            "账号：%d；查询完成：%d；失败：%d"
            % (len(results), queried, failed)
            if query_only
            else "账号：%d；观察增长：%d；未启用：%d；失败：%d"
            % (len(results), observed, disabled, failed)
        ),
        "",
    ]
    for result in results:
        lines.append(result_line(result))
        lines.extend("  %s" % detail for detail in result.detail_lines)
    if observed == 0:
        lines.extend(["", "结论：本轮没有账号观察到余额增长。"])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AStudio 每日登录积分观测")
    parser.add_argument(
        "--query",
        action="store_true",
        help="只查询活动配置与余额，不调用已识别的活跃触发接口",
    )
    parser.add_argument(
        "--only",
        metavar="N[,N|A-B]",
        help="只运行指定账号序号，例如 1、1,3、1-3",
    )
    parser.add_argument("--no-notify", action="store_true", help="关闭本轮推送")
    parser.add_argument("--version", action="version", version=VERSION)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        accounts = load_accounts()
        selected = (
            parse_only(args.only, len(accounts))
            if args.only
            else set(range(1, len(accounts) + 1))
        )
    except AccountConfigError as error:
        log("❌ %s" % error)
        return 2

    try:
        wait_seconds = float(
            env_text("ASTUDIO_WAIT_SECONDS", str(DEFAULT_WAIT_SECONDS))
        )
    except ValueError:
        log("❌ ASTUDIO_WAIT_SECONDS 不是有效数字")
        return 2
    if not math.isfinite(wait_seconds) or wait_seconds < 0:
        log("❌ ASTUDIO_WAIT_SECONDS 必须是非负有限数字")
        return 2

    timeout_text = env_text("ASTUDIO_TIMEOUT", str(DEFAULT_TIMEOUT))
    try:
        timeout = int(timeout_text)
    except ValueError:
        log("❌ ASTUDIO_TIMEOUT 不是有效整数")
        return 2
    if timeout <= 0:
        log("❌ ASTUDIO_TIMEOUT 必须大于 0")
        return 2

    client = AStudioClient(
        proxy=env_text("ASTUDIO_PROXY"),
        timeout=timeout,
        wait_seconds=wait_seconds,
    )

    log("╔══════════════════════════════════════╗")
    log("║ 🛰️ AStudio 每日登录积分观测          ║")
    log("╚══════════════════════════════════════╝")
    log(
        "👥 已载入 %d 个账号，本轮运行 %d 个；模式=%s"
        % (len(accounts), len(selected), "query" if args.query else "daily")
    )

    results: List[RunResult] = []
    for index, account in enumerate(accounts, 1):
        if index not in selected:
            continue
        log(
            "👤 账号%d %s；account_id=%s"
            % (index, account.label, mask_secret(account.account_id, keep=3))
        )
        result = run_account(index, account, client, query_only=args.query)
        results.append(result)
        log(result_line(result))
        for detail in result.detail_lines:
            log("   %s" % detail)

    report = build_report(results, args.query)
    print_safe("\n" + report)
    if not args.no_notify:
        notify_all("AStudio Daily %s" % time.strftime("%Y-%m-%d"), report)
    return 1 if any(result.failed for result in results) else 0


if __name__ == "__main__":
    sys.exit(main())
