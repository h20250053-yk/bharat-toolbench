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


def _rows(spec):
    """spec: {task_id: (status, n_calls)} -> rows keyed by task_id (only the fields model_flags reads)."""
    return {t: {"semantic_task_id": t.split("_")[0], "status": st, "trajectory": [{"event": "tool_call"}] * n} for t, (st, n) in spec.items()}


def _calls(r):
    return r["trajectory"]


def test_model_that_never_calls_a_tool_is_flagged_for_the_whole_model():
    f = SC.model_flags(_rows({"T01_en": ("completed", 0), "T80_en": ("completed", 0), "T150_en": ("completed", 0)}), _calls)
    assert f["no_tools"] and f["malformed_stages"] == []
    assert not SC.model_flags(_rows({"T01_en": ("completed", 0), "T150_en": ("completed", 1)}), _calls)["no_tools"]


def test_more_than_half_malformed_is_flagged_per_stage():
    # stage 1: 2 of 3 malformed (flagged); stage 3: 1 of 3 (not flagged); overall 3 of 6 = 50% (not more than half)
    f = SC.model_flags(_rows({"T01_en": ("malformed_output", 0), "T02_en": ("malformed_output", 0), "T03_en": ("completed", 1),
                              "T150_en": ("malformed_output", 0), "T151_en": ("completed", 1), "T152_en": ("completed", 1)}), _calls)
    assert f["malformed_stages"] == ["S1"] and abs(f["malformed_overall"] - 0.5) < 1e-9 and not f["no_tools"]


def test_pools_leave_out_flagged_model_stages():
    class D:  # the three pool rules on a stub with one clean model, one no-tool model and one stage-1 malformed model
        models = ["a", "b", "c"]
        flagged = {"b"}
        flags = {"a": {"malformed_stages": []}, "b": {"malformed_stages": []}, "c": {"malformed_stages": ["S1"]}}
        flagged_in = SC.Data.flagged_in
        any_flag = SC.Data.any_flag
        pool_models = SC.Data.pool_models
    d = D()
    assert d.pool_models("all", "S1") == ["a", "b", "c"]
    assert d.pool_models("reliable", "S1") == ["a"] and d.pool_models("reliable", "S3") == ["a", "c"]
    assert d.pool_models("no_flag", "S3") == ["a"]
