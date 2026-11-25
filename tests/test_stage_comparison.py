"""analysis/stage_comparison helpers (the full report is built from real runs; here only the pieces that decide what is counted)."""
import json

from analysis import stage_comparison as SC


def test_stages_cover_t01_t200_with_6_12_20_tools():
    assert [SC.stage_of(f"T{i:02d}") for i in (1, 75, 76, 100, 101, 200)] == ["S1", "S1", "S2", "S2", "S3", "S3"]
    assert [n for *_, n in SC.STAGES] == [6, 12, 20]
    assert sum(b - a + 1 for _, a, b in SC.GROUPS) == 100


def test_newcombe_difference_interval_contains_the_difference():
    d, lo, hi = SC.newcombe(30, 100, 20, 100)
    assert abs(d + 0.10) < 1e-9 and lo < d < hi and hi < 0.05


def test_status_from_files_needs_the_manifest_and_orders_resumes(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    for name in ("local_qwen25_3b_v3_new_TS.jsonl", "local_qwen25_3b_v3_new_TS_resume2.jsonl", "local_qwen25_3b_v3_new_TS_resume1.jsonl",
                 "local_qwen25_3b_v3_new_TS.manifest.json", "local_llama32_3b_v3_new_TS.jsonl"):
        (runs / name).write_text("{}\n")
    st = SC.status_from_files("TS", "v3_new", tmp_path)["models"]
    assert st["local_qwen25_3b"]["done"] and not st["local_llama32_3b"]["done"]
    assert st["local_qwen25_3b"]["run_files"] == ["runs/local_qwen25_3b_v3_new_TS.jsonl", "runs/local_qwen25_3b_v3_new_TS_resume1.jsonl",
                                                  "runs/local_qwen25_3b_v3_new_TS_resume2.jsonl"]


def _call(tool, code, value, key="station", message=None):
    msg = message if message is not None else (f"No station matches {value!r}." if code == "STATION_NOT_FOUND" else f"Unknown station code: {value!r}")
    return {"event": "tool_call", "tool": tool, "arguments": {key: value},
            "observation": {"ok": False, "data": None, "error": {"code": code, "message": msg}}}


def _code(e):
    return (e["observation"].get("error") or {}).get("code")


def test_station_errors_are_split_by_cause():
    gold = {"required_calls": []}
    assert SC.station_error_buckets([_call("resolve_station", "STATION_NOT_FOUND", "Mumbaila", key="name")], gold, _code) == {"not_resolved"}
    assert SC.station_error_buckets([_call("order_meal", "INVALID_STATION", "Nagpur")], gold, _code) == {"name_not_code"}
    assert SC.station_error_buckets([_call("search_trains", "INVALID_STATION", "KTM", key="source")], gold, _code) == {"name_not_code"}
    for v in ("", "  ", "next_stop", "resolve_station_result.Mumbai", "<station_code>", "{code}"):
        assert SC.station_error_buckets([_call("order_meal", "INVALID_STATION", v)], gold, _code) == {"placeholder"}, v
    assert not SC.is_placeholder("Hazrat Nizamuddin") and not SC.is_placeholder("St. Thomas Mount")
    # a person's name sent to resolve_station is still "not resolved"; other error codes are not station errors
    assert SC.station_error_buckets([_call("resolve_station", "STATION_NOT_FOUND", "Deepa Nair", key="name"),
                                     _call("order_meal", "NOT_EN_ROUTE", "NGP")], gold, _code) == {"not_resolved"}


def test_station_error_expected_by_the_gold_is_not_counted():
    gold = {"required_calls": [{"tool": "resolve_station", "expected_error": "STATION_NOT_FOUND"}]}
    calls = [_call("resolve_station", "STATION_NOT_FOUND", "Atlantis", key="name"), _call("get_platform_info", "INVALID_STATION", "Mumbai")]
    assert SC.station_error_buckets(calls, gold, _code) == {"name_not_code"}
