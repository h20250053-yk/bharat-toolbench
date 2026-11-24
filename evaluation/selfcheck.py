"""Offline helpers: build an IDEAL result row for a task by executing its gold calls in a fresh environment and
writing a contract-conformant final answer from gold. Used by the smoke test and the adversarial scorer tests.
No model, no API calls."""
from __future__ import annotations

import json
from typing import Any

from benchmark.build_gold import GOLD_PATH
from environment import RailwayEnv

from .final_answer import CLOSE, OPEN
from .scorer import STRUCTURED_VALUE_CHECKS, VALUE_CHECKS, requested_passengers, spec_for

_GOLD: dict[str, Any] | None = None


def gold_for(tid: str) -> dict[str, Any]:
    global _GOLD
    if _GOLD is None:
        _GOLD = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    return _GOLD[tid]


def gold_call_args(tid: str, call: dict[str, Any], env: RailwayEnv) -> dict[str, Any]:
    args = dict(call["required_args"])
    m = args.get("name")
    if isinstance(m, dict):
        if "resolves_to" in m:
            args["name"] = env.state.stations[m["resolves_to"]].name
        elif "resolves_ambiguous" in m:
            args["name"] = spec_for(tid)["solver"]["params"]["source_name"]
        elif "resolves_to_none" in m:
            args["name"] = spec_for(tid)["solver"]["params"]["source_name"]
    return args


def execute(calls: list[tuple[str, dict[str, Any]]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    env = RailwayEnv()
    env.reset()
    traj = []
    for i, (tool, args) in enumerate(calls, 1):
        traj.append({"event": "tool_call", "step": i, "tool_call_id": f"call_{i}", "tool": tool, "arguments": args,
                     "observation": env.call(tool, args)})
    return traj, env.snapshot()


def gold_calls(tid: str) -> list[tuple[str, dict[str, Any]]]:
    env = RailwayEnv()
    return [(c["tool"], gold_call_args(tid, c, env)) for c in gold_for(tid)["required_calls"] if not c.get("optional")]


def final_json(tid: str, snapshot: dict[str, Any], **override: Any) -> dict[str, Any]:
    g = gold_for(tid)
    fs, fa = g["final_state"], g["final_answer"]
    if fs.get("allowed_train_ids"):
        sel: Any = fs["allowed_train_ids"][0] if len(fs["allowed_train_ids"]) == 1 else fs["allowed_train_ids"]
    elif "first_leg_train_id" in fa:
        sel = [fa["first_leg_train_id"], fa["second_leg_train_id"]]
    elif "outbound_train_id" in fa:
        sel = [fa["outbound_train_id"], fa["return_train_id"]]
    else:
        sel = None
    obj = {"status": fs["status"], "selected_train": sel, "selected_class": fs.get("travel_class") if fs["status"] == "success" else None,
           "booking_ids": [b["booking_id"] for b in snapshot.get("bookings", [])],
           "requested_passengers": requested_passengers(spec_for(tid)), "notes": "ideal answer"}
    if tid in STRUCTURED_VALUE_CHECKS:  # requested facts, copied from gold (= tool results)
        obj["answer_values"] = {key: fa[gold_key] for gold_key, key, _ in STRUCTURED_VALUE_CHECKS[tid]}
    obj.update(override)
    return obj


def final_text(tid: str, obj: dict[str, Any] | None, natural: str | None = None, raw_json: str | None = None) -> str:
    g = gold_for(tid)
    if natural is None:
        parts = [f"{k}: {g['final_answer'][k]}" for k, _ in VALUE_CHECKS.get(tid, [])]
        natural = "Here is the result. " + "; ".join(parts)
    body = raw_json if raw_json is not None else json.dumps(obj, ensure_ascii=False)
    return f"{natural}\n{OPEN}\n{body}\n{CLOSE}" if (obj is not None or raw_json is not None) else natural


def ideal_result(tid: str) -> tuple[dict[str, Any], dict[str, Any]]:
    traj, snap = execute(gold_calls(tid))
    obj = final_json(tid, snap)
    row = {"task_id": f"{tid}_en", "semantic_task_id": tid, "language": "en", "status": "completed",
           "trajectory": traj, "final_text": final_text(tid, obj), "state_snapshot": snap}
    return row, snap
