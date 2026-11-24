"""BharatToolBench entry point (foundation stage).

    python run.py demo      # no-LLM vertical slice: resolve -> search -> details -> availability -> fare -> book

The model runner and evaluation commands arrive in later phases.
"""
from __future__ import annotations

import argparse
import json

from environment import RailwayEnv


def _step(env: RailwayEnv, n: int, tool: str, args: dict) -> dict:
    out = env.call(tool, args)
    print(f"\n[{n}] {tool}({json.dumps(args, ensure_ascii=False)})")
    print("    ->", json.dumps(out, ensure_ascii=False)[:420])
    return out


def demo() -> int:
    """Scripted (hard-coded, NOT an agent) workflow:
    'Book a 3A ticket from Mumbai to Ahmedabad, departing after 14:00 on 2026-10-07, for Rohan Mehta.'"""
    env = RailwayEnv()
    env.reset()
    print(f"reference datetime: {env.reference_datetime.isoformat()}")
    print(f"state hash before : {env.state_hash()[:16]}")

    src = _step(env, 1, "resolve_station", {"name": "Mumbai"})["data"]["candidates"][0]["code"]
    dst = _step(env, 2, "resolve_station", {"name": "Ahmedabad"})["data"]["candidates"][0]["code"]
    trains = _step(env, 3, "search_trains", {"source": src, "destination": dst, "date": "2026-10-07",
                                             "time_window": {"start": "14:00", "end": "23:59"}})["data"]["trains"]
    candidates = [t for t in trains if "3A" in t["classes"]]  # search results list each train's classes
    assert candidates, "demo expects a train offering 3A"
    tid = candidates[0]["train_id"]
    _step(env, 4, "get_train_details", {"train_id": tid})
    avail = _step(env, 5, "check_availability", {"train_id": tid, "travel_class": "3A"})
    _step(env, 6, "get_fare", {"train_id": tid, "travel_class": "3A"})
    if not avail["ok"] or avail["data"]["seats_available"] <= 0:
        print("\nNo 3A seats; demo stops.")
        return 1
    booking = _step(env, 7, "book_ticket", {"train_id": tid, "travel_class": "3A", "passenger": "Rohan Mehta"})
    after = _step(env, 8, "check_availability", {"train_id": tid, "travel_class": "3A"})
    print(f"\nseats before booking: {avail['data']['seats_available']}  after: {after['data']['seats_available']}")
    print(f"booking id: {booking['data']['booking_id']}  pnr: {booking['data']['pnr']}")
    print(f"state hash after  : {env.state_hash()[:16]}")
    env.reset()
    print(f"state hash reset  : {env.state_hash()[:16]}  (matches 'before' => reset is exact)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="BharatToolBench")
    parser.add_argument("command", choices=["demo"], help="demo: run the no-LLM vertical slice")
    args = parser.parse_args()
    return demo() if args.command == "demo" else 2


if __name__ == "__main__":
    raise SystemExit(main())
