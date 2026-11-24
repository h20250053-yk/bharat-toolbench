"""scripts/full_phase.py helpers: the completeness rule (the driver itself starts real runs and is exercised in the full-run phase)."""
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("full_phase", Path(__file__).resolve().parent.parent / "scripts" / "full_phase.py")
fp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fp)


def write(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_completeness_uses_the_latest_row_per_item_across_files(tmp_path):
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    write(a, [{"task_id": f"T{i}", "status": "completed"} for i in range(3)] + [{"task_id": "T3", "status": "provider_error"}])
    c = fp.completeness([a], expected=4)
    assert not c["complete"] and c["unresolved"] == ["T3"] and c["statuses"] == {"completed": 3, "provider_error": 1}
    write(b, [{"task_id": f"T{i}", "status": "completed"} for i in range(3)] + [{"task_id": "T3", "status": "provider_error"}, {"task_id": "T3", "status": "malformed_output"}])
    assert fp.completeness([b], expected=4)["complete"]
    assert not fp.completeness([a, tmp_path / "missing.jsonl"], expected=5)["complete"]


def test_all_scored_model_statuses_count_as_final():
    assert fp.FINAL == {"completed", "malformed_output", "step_limit_exceeded", "context_overflow", "output_truncated"}
