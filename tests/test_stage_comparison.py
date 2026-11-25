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
