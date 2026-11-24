"""Audit I-10: null baselines and the tool-required breakdown (no task or gold change)."""
import json

from analysis import null_baseline as nb

NO_TOOL = ["T09", "T19", "T29", "T30", "T36", "T37", "T45", "T46", "T67", "T69", "T74"]


def test_tool_required_split_matches_the_coverage_report():
    need = nb.tool_required_tasks()
    assert len(need) == 64 and not set(NO_TOOL) & set(need)


def test_always_needs_clarification_without_tools_passes_the_clarification_notool_tasks_and_T71():
    # T71 is the one tool-required task whose accepted alternative outcome (needs_clarification, no booking) needs no tool call
    assert nb.null_baseline("needs_clarification") == ["T09", "T19", "T36", "T37", "T46", "T67", "T69", "T71", "T74"]


def test_always_cannot_complete_passes_only_the_refusal_notool_tasks_and_success_baseline_passes_nothing():
    assert nb.null_baseline("cannot_complete") == ["T29", "T30", "T45"]
    assert nb.null_baseline("success") == []


def test_null_baseline_passes_no_tool_required_task_except_the_documented_T71_alternative():
    for st in nb.STATUSES:
        assert set(nb.null_baseline(st)) & set(nb.tool_required_tasks()) == ({"T71"} if st == "needs_clarification" else set()), st


def test_table_and_markdown(tmp_path):
    t = nb.baseline_table()
    b = t["baselines"]["always_needs_clarification_no_tools"]
    assert b["passes"] == 9 and b["of"] == 75 and b["passes_on_tool_required_tasks"] == 1 and abs(b["rate"] - 9 / 75) < 1e-3
    assert "always_needs_clarification_no_tools | 9/75" in nb.render_md(t)
    out = tmp_path / "bl"
    assert nb.main(["--out", str(out)]) == 0 and json.loads((out / "baseline.json").read_text(encoding="utf-8"))["tool_required_tasks"] == 64


def test_breakdown_on_observations():
    obs = [{"semantic_task_id": "T01", "scored": True, "task_success": True, "language": "en"},
           {"semantic_task_id": "T02", "scored": True, "task_success": False, "language": "en"},
           {"semantic_task_id": "T09", "scored": True, "task_success": True, "language": "en"},
           {"semantic_task_id": "T29", "scored": False, "task_success": None, "language": "en"}]
    r = nb.tool_required_breakdown(obs)
    assert r["tool_required_tasks"] == {"scored": 2, "task_success": 1, "rate": 0.5}
    assert r["no_tool_tasks"]["scored"] == 1 and r["no_tool_tasks"]["task_success"] == 1
    assert r["always_needs_clarification_baseline"]["passes_per_language"] == 9
