"""ONE-REQUEST live smoke test for the EXPERIMENTAL OpenRouter model (`experimental_inkling`).

    python -m evaluation.openrouter_smoke              # dry run: builds and shows the request, sends NOTHING
    python -m evaluation.openrouter_smoke --live       # sends AT MOST ONE HTTP request, then stops

What it does (live): builds the configured adapter, sends exactly one chat-completion request containing the benchmark's
own system prompt, the synthetic T01 English query and T01's allowed tool schemas, and classifies the single response.
It never sends tool results back (that would be a second request), never retries, and never runs the pilot.

The one-request limit is enforced in three independent layers:
  1. this script calls the adapter exactly once (no loop, no continue_turn, no retry policy, no runner);
  2. the OpenAI SDK client is created with max_retries=0;
  3. a request hook on the SDK's own HTTP client (openai.DefaultHttpxClient) counts every outgoing HTTP request
     (including redirect hops)
     and raises BEFORE a second one leaves the process.

It does not touch run files, quota files, gold, tasks or the scorer. Its only output is a NEW JSON report
(default runs/experimental_inkling_smoke_<UTC>.json, created with exclusive mode, so nothing is ever overwritten).
The API key is read only from OPENROUTER_API_KEY, never printed, and redacted from everything written or shown.

Exit codes: 0 OK_TOOL_CALL | 10 OK_NO_TOOL_CALL | 20 REJECTED | 30 INCOMPATIBLE | 40 NOT_SENT | 50 HARNESS_ERROR | 0 DRY_RUN
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

from agents.base import ModelOutputError, ProviderError
from agents.openrouter_adapter import API_KEY_ENV, OpenRouterAdapter
from agents.registry import build_adapter, load_model_config
from environment import tool_specs

from .runner import SYSTEM_PROMPT, SYSTEM_PROMPT_SHA256, load_items

ROOT = Path(__file__).resolve().parent.parent
LANG_DIR = ROOT / "benchmark" / "languages"
RUNS_DIR = ROOT / "runs"
MODEL_KEY = "experimental_inkling"
ITEM_ID = "T01_en"
EXIT = {"OK_TOOL_CALL": 0, "DRY_RUN": 0, "OK_NO_TOOL_CALL": 10, "REJECTED": 20, "INCOMPATIBLE": 30, "NOT_SENT": 40,
        "HARNESS_ERROR": 50}
MEANING = {
    "OK_TOOL_CALL": "authenticated, endpoint reachable, valid chat completion with a well-formed call to an allowed tool",
    "OK_NO_TOOL_CALL": "authenticated, endpoint reachable, valid chat completion, but NO tool call in this one response "
                       "(native tool calling not demonstrated)",
    "REJECTED": "the provider refused or failed the request (see error_kind / status_code); not retried",
    "INCOMPATIBLE": "a response arrived but is unusable for the benchmark (malformed/unknown tool call, missing "
                    "required arguments, or empty output)",
    "NOT_SENT": "no request was sent (missing key or configuration problem)",
    "HARNESS_ERROR": "unexpected local error; see error",
    "DRY_RUN": "dry run: request built and shown, nothing sent",
}


class RequestLimitExceeded(RuntimeError):
    pass


class OneShotGuard:
    """Request hook for the SDK HTTP client: allows `limit` outgoing HTTP requests, raises before any further one is sent."""
    def __init__(self, limit: int = 1):
        self.limit, self.count = limit, 0

    def __call__(self, request: Any) -> None:
        if self.count >= self.limit:
            raise RequestLimitExceeded(f"blocked outgoing HTTP request #{self.count + 1}: smoke-test limit is {self.limit}")
        self.count += 1


def make_client(api_key: str, timeout: float, guard: OneShotGuard, transport: Any = None):
    """OpenAI client for OpenRouter: SDK retries off, every HTTP request passes through `guard`.
    (`transport` exists only so offline tests can inject a mock; live use keeps the SDK's default transport/proxy.)"""
    import openai
    http_kwargs: dict[str, Any] = {"event_hooks": {"request": [guard]}}
    if transport is not None:
        http_kwargs["transport"] = transport
    return openai.OpenAI(api_key=api_key, base_url=OpenRouterAdapter.BASE_URL, timeout=timeout, max_retries=0,
                         http_client=openai.DefaultHttpxClient(**http_kwargs))


def _redactor(secret: str | None) -> Callable[[Any], Any]:
    def scrub(obj: Any) -> Any:
        if not secret or len(secret) < 8:
            return obj
        return json.loads(json.dumps(obj, ensure_ascii=False, default=str).replace(secret, "[REDACTED]"))
    return scrub


def _check_call(call, tools_by_name: dict[str, dict]) -> str | None:
    """None if the tool call is usable, else the reason it is not."""
    if not call.parse_ok:
        return f"malformed arguments: {call.parse_error}"
    if call.name not in tools_by_name:
        return f"unknown or disallowed tool {call.name!r}"
    params = tools_by_name[call.name]["parameters"]
    missing = [k for k in params.get("required", []) if k not in call.arguments]
    if missing:
        return f"missing required argument(s) {missing} for {call.name}"
    unknown = [k for k in call.arguments if k not in params.get("properties", {})]
    if unknown and params.get("additionalProperties") is False:
        return f"unexpected argument(s) {unknown} for {call.name}"
    return None


def run_smoke(*, live: bool, out_path: Path | None = None, transport: Any = None, env: dict[str, str] | None = None,
              printer: Callable[[str], None] = print) -> tuple[str, dict[str, Any]]:
    env = os.environ if env is None else env
    secret = env.get(API_KEY_ENV) or None
    scrub = _redactor(secret)
    cfg = load_model_config()[MODEL_KEY]
    item = load_items(LANG_DIR, ["en"], [ITEM_ID.split("_")[0]])[0]
    tools = [t for t in tool_specs() if t["name"] in item["allowed_tools"]]
    tools_by_name = {t["name"]: t for t in tools}
    guard = OneShotGuard(limit=1)
    report: dict[str, Any] = {
        "kind": "openrouter_one_request_smoke_test", "model_key": MODEL_KEY, "provider": cfg["provider"], "model": cfg["model"],
        "base_url": OpenRouterAdapter.BASE_URL, "item": ITEM_ID, "query": item["query"], "allowed_tools": item["allowed_tools"],
        "system_prompt_sha256": SYSTEM_PROMPT_SHA256, "live": live, "started_at": datetime.now(timezone.utc).isoformat(),
        "max_http_requests": 1, "note": "synthetic benchmark data only; not live Indian Railways data",
    }
    verdict, error = "HARNESS_ERROR", None
    write_report = True
    try:
        if not live:
            # build the exact request with a fake client that records it; no network, no key needed
            captured: dict[str, Any] = {}

            def _record(**kw):
                captured.update(kw)
                raise _DryRunStop()
            adapter = build_adapter(MODEL_KEY, client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=_record))))
            report["adapter_settings"] = adapter.settings()
            try:
                adapter.start(SYSTEM_PROMPT, item["query"], tools)
            except _DryRunStop:
                pass
            report["request"] = {k: v for k, v in captured.items() if k not in ("messages", "tools")}
            report["request"]["messages"] = [{"role": m["role"], "chars": len(m["content"])} for m in captured["messages"]]
            report["request"]["tools"] = [t["function"]["name"] for t in captured["tools"]]
            verdict = "DRY_RUN"
        elif not secret:
            verdict, error = "NOT_SENT", f"{API_KEY_ENV} is not set; no request was sent"
        elif out_path is not None and out_path.exists():
            verdict, error = "NOT_SENT", f"report path {out_path} already exists; no request was sent"
            write_report = False  # never overwrite it, and never fall back to another path
        else:
            client = make_client(secret, float(cfg.get("timeout_seconds", 60)), guard, transport=transport)
            adapter = build_adapter(MODEL_KEY, client=client)
            report["adapter_settings"] = adapter.settings()
            t0 = time.monotonic()
            try:
                turn = adapter.start(SYSTEM_PROMPT, item["query"], tools)       # THE one request
            finally:
                report["latency_seconds"] = round(time.monotonic() - t0, 3)
            raw = turn.response if isinstance(turn.response, dict) else {}
            report["response"] = {
                "finish_reason": turn.finish_reason, "usage": turn.usage, "served_model": raw.get("model"),
                "upstream_provider": raw.get("provider"), "generation_id": raw.get("id"), "text_excerpt": (turn.text or "")[:500],
                "tool_calls": [{"id": c.id, "name": c.name, "arguments": c.arguments, "raw_arguments": c.raw_arguments,
                                "parse_ok": c.parse_ok, "parse_error": c.parse_error} for c in turn.tool_calls],
            }
            report["raw_response"] = raw
            problems = [p for p in (_check_call(c, tools_by_name) for c in turn.tool_calls) if p]
            if problems:
                verdict, error = "INCOMPATIBLE", "; ".join(problems)
            elif turn.tool_calls:
                verdict = "OK_TOOL_CALL"
            elif (turn.text or "").strip():
                verdict = "OK_NO_TOOL_CALL"
            else:
                verdict, error = "INCOMPATIBLE", f"empty response (finish_reason={turn.finish_reason!r})"
    except ProviderError as exc:
        verdict, error = "REJECTED", str(exc)
        report.update(error_kind=exc.kind, status_code=exc.status_code, retryable_in_runner=exc.retryable,
                      retried=False, retry_after=exc.retry_after)
    except ModelOutputError as exc:
        verdict, error = "INCOMPATIBLE", f"{exc.kind}: {exc}"
    except RequestLimitExceeded as exc:  # e.g. a redirect hop: blocked before it was sent
        verdict, error = "REJECTED", f"second HTTP request blocked by the smoke-test guard ({exc})"
        report.update(error_kind="request_limit", retried=False)
    except Exception as exc:  # noqa: BLE001 - reported, never retried
        cause = exc.__cause__ if isinstance(exc.__cause__, RequestLimitExceeded) else None
        if cause is not None:
            verdict, error = "REJECTED", f"second HTTP request blocked by the smoke-test guard ({cause})"
        else:
            verdict, error = "HARNESS_ERROR", f"{type(exc).__name__}: {exc}"
    report.update(verdict=verdict, meaning=MEANING[verdict], error=error, http_requests_sent=guard.count,
                  finished_at=datetime.now(timezone.utc).isoformat(),
                  cannot_verify=["tool-result round trip (needs a 2nd request)", "multi-turn behaviour", "final-answer "
                                 "contract compliance", "task success / scoring", "behaviour in hi/hinglish/mr",
                                 "rate-limit behaviour over many requests", "determinism across repeats"])
    report = scrub(report)
    if not write_report:
        out_path = None
    elif out_path is None and live:
        out_path = RUNS_DIR / f"{MODEL_KEY}_smoke_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("x", encoding="utf-8") as fh:   # exclusive: never overwrites an existing file
            json.dump(report, fh, ensure_ascii=False, indent=2)
        report["report_file"] = str(out_path)
    resp = report.get("response", {})
    lines = [f"OpenRouter smoke test ({'LIVE' if live else 'DRY RUN'}): model_key={MODEL_KEY} model={cfg['model']}",
             f"verdict: {verdict} - {MEANING[verdict]}",
             f"http_requests_sent: {guard.count} (limit 1, SDK retries 0, no automatic retry)"]
    if error:
        lines.append(f"error: {error}")
    for k in ("error_kind", "status_code"):
        if report.get(k) is not None:
            lines.append(f"{k}: {report[k]}")
    if resp:
        lines.append(f"finish_reason={resp.get('finish_reason')} upstream_provider={resp.get('upstream_provider')} "
                     f"usage={resp.get('usage')} latency_s={report.get('latency_seconds')}")
        for c in resp.get("tool_calls", []):
            lines.append(f"tool_call: {c['name']} {json.dumps(c['arguments'], ensure_ascii=False)} parse_ok={c['parse_ok']}")
    if report.get("request"):
        lines.append(f"request (not sent): {json.dumps(report['request'], ensure_ascii=False)}")
    if report.get("report_file"):
        lines.append(f"report: {report['report_file']}")
    for line in lines:
        printer(scrub(line))
    return verdict, report


class _DryRunStop(Exception):
    pass


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="One-request OpenRouter smoke test for experimental_inkling (dry run by default).")
    ap.add_argument("--live", action="store_true", help="actually send the single request (needs OPENROUTER_API_KEY)")
    ap.add_argument("--out", type=Path, default=None, help="report path (must not exist); default runs/experimental_inkling_smoke_<UTC>.json")
    args = ap.parse_args(argv)
    if args.out is not None and args.out.exists():
        ap.error(f"{args.out} already exists; choose a new path (existing files are never overwritten)")
    verdict, _ = run_smoke(live=args.live, out_path=args.out)
    return EXIT[verdict]


if __name__ == "__main__":
    raise SystemExit(main())
