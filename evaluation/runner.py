"""BharatToolBench agent runner: prompt -> model -> tools -> observations -> final answer.

Per item (plan sections 6, 13, 19):
  * environment reset before every attempt; state hash recorded before and after
  * at most MAX_TURNS = 8 model turns (plan: "max 8 LLM turns/evaluation"); a model still requesting tools on its
    8th turn ends with status step_limit_exceeded (a MODEL failure, never retried)
  * only retryable provider failures (rate limit, 5xx, timeout, connection) are retried, with exponential backoff
    that honours Retry-After; every retry is recorded with its reason
  * malformed tool calls are recorded as trajectory events and reported back to the model; whole-turn malformed
    output (e.g. Gemini MALFORMED_FUNCTION_CALL) ends the item with status malformed_output (model failure)
  * token usage is SUMMED over all turns; raw requests/responses, tool requests/responses and timestamps are logged
Statuses: completed | malformed_output | context_overflow | output_truncated | step_limit_exceeded (model outcomes, scored) | provider_error | runner_error
(not scored; re-run on --resume).
"""
from __future__ import annotations

import hashlib
import json
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import yaml

from agents.base import ModelAdapter, ModelOutputError, ProviderError, ToolCall
from environment import RailwayEnv
from environment.railway_env import tool_specs

from .final_answer import CONTRACT_PROMPT, parse_final_answer
from .tolerance import (TOOL_NAMES, extract_text_tool_calls, final_text_from_turns, normalize_arguments, normalize_tool_name,
                        parse_final_answer_lenient, repair_arguments_json)
from .quota import QuotaTracker

ROOT = Path(__file__).resolve().parent.parent
MAX_TURNS = 8
# ModelOutputError kinds that get their own (scored) status instead of the generic malformed_output
MODEL_OUTPUT_ERROR_STATUS = {"context_overflow": "context_overflow", "output_truncated": "output_truncated"}

SYSTEM_PROMPT = """You are a railway assistant for a simulated Indian railway booking service.
Current date and time: 2026-10-05 09:00 IST (Monday). Bookings are only for future dates.
Rules: Use tools for facts; never invent train IDs, fares, availability or booking IDs.
Station names may be in any language; use resolve_station when you need a code.
If essential information is missing or ambiguous, ask the user instead of guessing.
Only call a tool that books, cancels, waitlists, changes, orders, files or registers something when the user asked for that action.
Follow the user's constraints exactly. If a condition fails, do not substitute a different action unless the user explicitly allowed that fallback.
""" + CONTRACT_PROMPT


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


SYSTEM_PROMPT_SHA256 = sha256_text(SYSTEM_PROMPT)
TOOL_SCHEMA_SHA256 = sha256_text(json.dumps(tool_specs(), sort_keys=True, ensure_ascii=False))


def benchmark_version() -> str:
    return str(yaml.safe_load((ROOT / "config" / "benchmark.yaml").read_text(encoding="utf-8"))["benchmark_version"])


def offered_tools(item: dict[str, Any]) -> list[str]:
    """Tools the model is given for this item: its row's allowed_tools (the tool stage it belongs to: T01-T75 six tools, T76-T100
    twelve, T101-T200 twenty), in the environment's order. With config offer_all_tools: true every item gets all twenty instead."""
    cfg = yaml.safe_load((ROOT / "config" / "benchmark.yaml").read_text(encoding="utf-8"))
    return list(TOOL_NAMES) if cfg.get("offer_all_tools") else [t for t in TOOL_NAMES if t in item["allowed_tools"]]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RunnerConfig:
    max_turns: int = MAX_TURNS
    max_attempts: int = 5              # plan: backoff 2,4,8,16,32 s +- jitter, max 5
    backoff_base: float = 2.0
    backoff_cap: float = 60.0
    jitter: float = 0.25
    max_retry_after: float = 300.0     # never wait longer than this for one Retry-After
    sleep: Callable[[float], None] = time.sleep
    rng: random.Random = field(default_factory=lambda: random.Random(0))

    def backoff(self, attempt: int, retry_after: float | None) -> float:
        if retry_after is not None:
            return min(float(retry_after), self.max_retry_after)
        base = min(self.backoff_base * (2 ** (attempt - 1)), self.backoff_cap)
        return max(0.0, base * (1 + self.rng.uniform(-self.jitter, self.jitter)))


def load_items(lang_dir: Path, languages: list[str], semantic_ids: list[str]) -> list[dict[str, Any]]:
    wanted = set(semantic_ids)
    out: list[dict[str, Any]] = []
    for lang in languages:
        for line in (lang_dir / f"{lang}.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row["semantic_task_id"] in wanted:
                    out.append(row)
    expected = len(wanted) * len(languages)
    if len(out) != expected:
        raise ValueError(f"Expected {expected} items, found {len(out)}")
    return sorted(out, key=lambda r: (semantic_ids.index(r["semantic_task_id"]), languages.index(r["language"])))


def _add_usage(total: dict[str, int], usage: dict[str, int]) -> None:
    for k, v in (usage or {}).items():
        if isinstance(v, (int, float)):
            total[k] = total.get(k, 0) + int(v)


def _tag(recs: list[dict[str, Any]], turn_no: int, call_id: str | None = None) -> list[dict[str, Any]]:
    return [{**r, "turn": turn_no, **({"tool_call_id": call_id} if call_id else {})} for r in recs]


def execute_tool_call(env: RailwayEnv, call: ToolCall, allowed: list[str], turn_no: int, log: list, attempt: int,
                      recoveries: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run one model tool call through the shared format tolerance (tolerance.py) and the environment.
    Returns (observation, trajectory event). Format recoveries (tool-name spelling, broken argument JSON, argument formats, dropped
    unknown extra keys) are appended to `recoveries` and to the event; the environment and its contract are untouched, and a value that
    is wrong stays wrong (nothing is renamed or repaired)."""
    ts = _now()
    recs: list[dict[str, Any]] = []
    name = call.name
    name, r = normalize_tool_name(name, TOOL_NAMES)
    recs += r
    if not call.parse_ok and call.raw_arguments:
        fixed, r = repair_arguments_json(call.raw_arguments)
        if fixed is not None:
            call = ToolCall(id=call.id, name=name, arguments=fixed, raw_arguments=call.raw_arguments)
            recs += r
    if not call.parse_ok:
        obs = {"ok": False, "data": None, "error": {"code": "MALFORMED_ARGUMENTS",
                                                   "message": f"Tool arguments are not a valid JSON object: {call.parse_error}"}}
        event = {"event": "malformed_tool_call", "turn": turn_no, "tool_call_id": call.id, "tool": call.name,
                 "raw_arguments": call.raw_arguments, "parse_error": call.parse_error, "observation": obs}
    elif name not in allowed:
        obs = {"ok": False, "data": None, "error": {"code": "TOOL_NOT_ALLOWED", "message": f"Tool {call.name!r} is not allowed"}}
        event = {"event": "tool_not_allowed", "turn": turn_no, "tool_call_id": call.id, "tool": call.name,
                 "arguments": call.arguments, "observation": obs}
    else:
        args, r = normalize_arguments(name, call.arguments)
        recs += r
        log.append({"ts": ts, "attempt": attempt, "type": "tool_request", "tool": name, "tool_call_id": call.id,
                    "arguments": args, **({"arguments_original": call.arguments} if args != call.arguments else {})})
        obs = env.call(name, args)
        log.append({"ts": _now(), "attempt": attempt, "type": "tool_response", "tool_call_id": call.id, "observation": obs})
        event = {"event": "tool_call", "turn": turn_no, "tool_call_id": call.id, "tool": name, "arguments": args, "observation": obs}
        if args != call.arguments:
            event["arguments_original"] = call.arguments
    if recs:
        tagged = _tag(recs, turn_no, call.id)
        recoveries.extend(tagged)
        event["format_recoveries"] = tagged
        for t in tagged:
            log.append({"ts": _now(), "attempt": attempt, "type": "format_recovery", **t})
    return obs, event


def _conversation(item, adapter: ModelAdapter, env: RailwayEnv, cfg: RunnerConfig, log: list, attempt: int,
                  usage_total: dict[str, int], per_turn_usage: list, quota: QuotaTracker | None,
                  trajectory: list[dict[str, Any]] | None = None, recoveries: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """One attempt. Returns {status, trajectory, final_text}; raises ProviderError (classified) on provider failure.
    `trajectory` / `recoveries`, if given, are filled in place so the caller still holds them when this raises."""
    allowed = offered_tools(item)
    tools = [t for t in tool_specs() if t["name"] in allowed]
    trajectory = [] if trajectory is None else trajectory
    recoveries = [] if recoveries is None else recoveries
    turns_info: list[dict[str, Any]] = []

    def model_call(fn, *args):
        t0 = _now()
        turn = fn(*args)
        t1 = _now()
        log.append({"ts": t0, "attempt": attempt, "type": "model_request", "request": turn.request})
        log.append({"ts": t1, "attempt": attempt, "type": "model_response", "finish_reason": turn.finish_reason,
                    "usage": turn.usage, "response": turn.response})
        _add_usage(usage_total, turn.usage)
        per_turn_usage.append({"attempt": attempt, **turn.usage})
        if quota is not None:
            quota.record_request(adapter.provider, turn.usage)
        return turn

    turn = model_call(adapter.start, SYSTEM_PROMPT, item["query"], tools)
    for turn_no in range(1, cfg.max_turns + 1):
        calls = list(turn.tool_calls)
        text = turn.text
        if not calls and text and getattr(adapter, "SUPPORTS_TEXT_TOOL_RECOVERY", False):
            found, recs = extract_text_tool_calls(text, allowed)
            if found:  # the whole reply is tool-call JSON the serving layer did not convert: execute it as the model's calls
                calls = [ToolCall(id=f"recovered-{turn_no}-{i}", name=c["name"], arguments=c["arguments"], raw_arguments=json.dumps(c["arguments"], ensure_ascii=False))
                         for i, c in enumerate(found, 1)]
                tagged = _tag(recs, turn_no)
                recoveries.extend(tagged)
                for t in tagged:
                    log.append({"ts": _now(), "attempt": attempt, "type": "format_recovery", **t})
                adapter.attach_recovered_tool_calls(calls)
                text = ""   # consumed: the text was a tool call, not a reply
        turns_info.append({"text": text, "tool_calls": bool(calls)})
        if not calls:
            final_text, recs = final_text_from_turns(turns_info)
            recoveries.extend(_tag(recs, turn_no))
            return {"status": "completed", "trajectory": trajectory, "final_text": final_text, "turns": turn_no}
        if turn_no == cfg.max_turns:  # 8th model turn still wants tools: the model did not finish in time
            for call in calls:
                trajectory.append({"event": "unexecuted_step_limit", "turn": turn_no, "tool_call_id": call.id, "tool": call.name,
                                   "arguments": call.arguments, "raw_arguments": call.raw_arguments})
            return {"status": "step_limit_exceeded", "trajectory": trajectory, "final_text": text, "turns": turn_no}
        results: list[tuple[ToolCall, dict[str, Any]]] = []
        for call in calls:
            obs, event = execute_tool_call(env, call, allowed, turn_no, log, attempt, recoveries)
            trajectory.append(event)
            results.append((call, obs))
        turn = model_call(adapter.continue_turn, results)
    raise AssertionError("unreachable")  # pragma: no cover


def run_item(item: dict[str, Any], adapter_factory: Callable[[], ModelAdapter], env: RailwayEnv, cfg: RunnerConfig,
             *, quota: QuotaTracker | None = None, run_name: str = "run") -> dict[str, Any]:
    log: list[dict[str, Any]] = []
    retries: list[dict[str, Any]] = []
    usage_total: dict[str, int] = {}
    per_turn_usage: list[dict[str, Any]] = []
    started = _now()
    adapter = None
    outcome: dict[str, Any] = {}
    attempt = 0
    env_before = env_after = None
    attempt_trajectory: list[dict[str, Any]] = []
    attempt_recoveries: list[dict[str, Any]] = []
    while True:
        attempt += 1
        env.reset()
        env_before = env.state_hash()
        attempt_trajectory = []  # tool calls executed in THIS attempt (kept when the attempt ends in an error)
        attempt_recoveries = []  # format recoveries of THIS attempt
        try:
            adapter = adapter_factory()
            outcome = _conversation(item, adapter, env, cfg, log, attempt, usage_total, per_turn_usage, quota,
                                    trajectory=attempt_trajectory, recoveries=attempt_recoveries)
            break
        except ProviderError as exc:
            info = {"attempt": attempt, "kind": exc.kind, "status_code": exc.status_code, "retryable": exc.retryable,
                    "retry_after": exc.retry_after, "error": str(exc)[:500], "ts": _now()}
            log.append({"ts": info["ts"], "attempt": attempt, "type": "provider_error", **info})
            if exc.retryable and attempt < cfg.max_attempts:
                info["wait_seconds"] = round(cfg.backoff(attempt, exc.retry_after), 3)
                retries.append(info)
                if quota is not None:
                    quota.record_retry()
                cfg.sleep(info["wait_seconds"])
                continue
            retries.append(info)
            if quota is not None:
                quota.record_provider_error()
            outcome = {"status": "provider_error", "trajectory": [], "final_text": "",
                       "error": f"{exc.kind}: {str(exc)[:500]}", "error_kind": exc.kind}
            break
        except ModelOutputError as exc:
            log.append({"ts": _now(), "attempt": attempt, "type": "malformed_output", "kind": exc.kind, "raw": exc.raw})
            outcome = {"status": MODEL_OUTPUT_ERROR_STATUS.get(exc.kind, "malformed_output"), "trajectory": [], "final_text": "",
                       "error": f"{exc.kind}: {str(exc)[:500]}", "error_kind": exc.kind}
            break
        except Exception as exc:  # noqa: BLE001 - harness bug: recorded, never retried
            outcome = {"status": "runner_error", "trajectory": [], "final_text": "", "error": f"{type(exc).__name__}: {exc}"}
            break
    env_after = env.state_hash()
    final_parse = parse_final_answer(outcome.get("final_text", ""))
    lenient_parse = parse_final_answer_lenient(outcome.get("final_text", ""))
    log.append({"ts": _now(), "attempt": attempt, "type": "final_answer", "final_text": outcome.get("final_text", ""),
                "parsed": final_parse, "parsed_lenient": {k: lenient_parse[k] for k in ("ok", "error", "recoveries")}})
    settings = adapter.settings() if adapter is not None and hasattr(adapter, "settings") else {}
    return {
        # provenance
        "run_id": f"{run_name}:{getattr(adapter, 'model_key', '?')}:{item['task_id']}",
        "benchmark_version": benchmark_version(),
        "task_id": item["task_id"], "semantic_task_id": item["semantic_task_id"], "language": item["language"],
        "model_key": getattr(adapter, "model_key", None), "provider": getattr(adapter, "provider", None),
        "model": getattr(adapter, "model", None), "adapter_settings": settings,
        "system_prompt_sha256": SYSTEM_PROMPT_SHA256, "tool_schema_sha256": TOOL_SCHEMA_SHA256,
        "env_hash_before": env_before, "env_hash_after": env_after,
        "max_turns": cfg.max_turns, "started_at": started, "finished_at": _now(),
        # outcome
        "status": outcome["status"], "error": outcome.get("error"), "error_kind": outcome.get("error_kind"),
        "attempts": attempt, "retries": retries, "turns": outcome.get("turns"),
        "query": item["query"], "offered_tools": offered_tools(item),
        "trajectory": outcome.get("trajectory", []), "final_text": outcome.get("final_text", ""),
        # diagnostic only (never scored): tool calls the final attempt executed before it ended in malformed_output /
        # provider_error / runner_error. `trajectory` stays [] for those statuses, exactly as before.
        "partial_trajectory": list(attempt_trajectory) if outcome.get("status") in ("malformed_output", "context_overflow", "output_truncated", "provider_error", "runner_error") else [],
        "final_answer": {"ok": final_parse["ok"], "error": final_parse["error"], "answer": final_parse["answer"]},
        # format tolerance (tolerance.py): what the lenient reader makes of the reply, and every run-time recovery of the final attempt
        "final_answer_lenient": {"ok": lenient_parse["ok"], "error": lenient_parse["error"], "answer": lenient_parse["answer"],
                                 "recoveries": lenient_parse["recoveries"]},
        "format_recoveries": list(attempt_recoveries), "lenient_used": bool(attempt_recoveries or lenient_parse["recoveries"]),
        "usage": usage_total, "usage_per_turn": per_turn_usage,
        "state_snapshot": env.snapshot(),
        "raw_log": log,
    }
