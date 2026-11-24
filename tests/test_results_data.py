"""Phase 4 statistics and helpers (analysis/results_data.py, build_media helpers, scripts/backup_full_runs.py). numpy/scipy/Pillow are only in the visualisation venv
(~/FreeModel/viz-venv), so these tests are skipped in the project venv:  PYTHONPATH=. ~/FreeModel/viz-venv/bin/python -m pytest tests/test_results_data.py"""
import importlib.util
import json
import tarfile
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")
from analysis import results_data as D  # noqa: E402


class FakeRun:
    def __init__(self, key, succ):
        self.key, self.succ = key, succ
        self.rows = {t: {"language": t.split("_")[1], "semantic_task_id": t.split("_")[0], "score": {"task_success": s}, "score_strict": {"task_success": s}} for t, s in succ.items()}

    def ok(self, t, strict=False):
        return bool(self.succ[t])


def items(pattern):
    return {f"T{i:02d}_{l}": p for i in range(1, 76) for l, p in zip(D.LANGS, pattern(i))}


def test_wilson_known_values_and_edges():
    lo, hi = D.wilson(8, 10)
    assert lo == pytest.approx(0.4902, abs=1e-3) and hi == pytest.approx(0.9433, abs=1e-3)
    assert D.wilson(0, 10)[0] == 0.0 and D.wilson(10, 10)[1] == pytest.approx(1.0) and D.wilson(0, 0)[0] != D.wilson(0, 0)[0]


def test_holm_is_monotone_and_never_below_the_raw_p():
    p = [0.001, 0.04, 0.03, 0.5]
    adj = D.holm(p)
    assert adj[0] == pytest.approx(0.004) and all(a >= x for a, x in zip(adj, p)) and max(adj) <= 1.0
    order = sorted(range(4), key=lambda i: p[i])
    assert [adj[i] for i in order] == sorted(adj[i] for i in order)


def test_mcnemar_exact_counts_and_symmetry():
    a = FakeRun("a", items(lambda i: (1, 1, 1, 1, 1) if i <= 30 else (0, 0, 0, 0, 0)))
    b = FakeRun("b", items(lambda i: (0, 0, 0, 0, 0)))
    r = D.mcnemar_exact(a, b)
    assert r["only_a"] == 150 and r["only_b"] == 0 and r["p"] < 1e-10
    same = D.mcnemar_exact(a, a)
    assert same["only_a"] == same["only_b"] == 0 and same["p"] == 1.0


def test_paired_bootstrap_gap_is_deterministic_and_has_the_right_sign():
    r = FakeRun("a", items(lambda i: (1, 0, 0, 0, 0) if i % 2 else (0, 0, 0, 0, 0)))     # English succeeds on odd tasks, other languages never
    g1, g2 = D.paired_bootstrap_gap(r, "hi"), D.paired_bootstrap_gap(r, "hi")
    assert g1 == g2 and g1["diff"] == pytest.approx(-38 / 75) and g1["lo"] < g1["diff"] < g1["hi"] < 0 and g1["lang_rate"] == 0 and g1["base_rate"] == pytest.approx(38 / 75)


def test_model_colours_and_names_are_unique_and_complete():
    assert len(set(D.COLOR.values())) == len(D.COLOR) == len(D.PLAN_ORDER) == 8 and set(D.COLOR) == set(D.DISPLAY) == set(D.FAMILY) == set(D.PLAN_ORDER)


def test_spearman_perfect_and_inverse():
    assert D.spearman([1, 2, 3, 4], [10, 20, 30, 40])[0] == pytest.approx(1.0) and D.spearman([1, 2, 3, 4], [4, 3, 2, 1])[0] == pytest.approx(-1.0)


# ---- media helpers
def test_script_runs_and_wrapping_use_the_right_font_per_script():
    pytest.importorskip("PIL")
    from analysis import build_media as BM
    assert [s for s, _ in BM.runs("BTB103 मध्ये 2A")] == ["latin", "deva", "latin"]
    assert [s for s, _ in BM.runs("ભાડું BTB103")] == ["guj", "latin"]
    lines = BM.wrap("9 ऑक्टोबर 2026 रोजी मुंबईहून पुण्याला जाण्यासाठी ट्रेन BTB115 मध्ये प्रवाशांची 3A तिकिटे बुक करा", 24, 500)
    assert len(lines) >= 2 and all(BM.width(l, 24) <= 500 + 1 for l in lines)
    im = BM.frame(2, "title", [("hello", 16, "#000000", False)], "footer")
    assert im.size == (1000, 560)


# ---- backup script
def test_backup_collects_only_the_requested_timestamps_and_verifies(tmp_path):
    spec = importlib.util.spec_from_file_location("bk", Path(__file__).resolve().parent.parent / "scripts" / "backup_full_runs.py")
    bk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bk)
    root = tmp_path / "repo"
    for rel, text in {"runs/a_full_T1.jsonl": "x\n", "runs/a_full_T1.prerun.json": "{}", "runs/b_full_OLD.jsonl": "old", "runs/a_pilot_P1.jsonl": "p", "analysis/results/a_full_T1/summary.json": "{}",
                      "analysis/results/b_full_OLD/summary.json": "{}", "config/models.yaml": "m", "config/benchmark.yaml": "b", "benchmark/gold_labels.json": "{}", "benchmark/semantic_tasks.json": "{}",
                      "benchmark/languages/en.jsonl": "e"}.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)
    names = {p.relative_to(root).as_posix() for p in bk.collect("T1", "P1", root)}
    assert "runs/a_full_T1.jsonl" in names and "runs/a_pilot_P1.jsonl" in names and "analysis/results/a_full_T1/summary.json" in names
    assert "runs/b_full_OLD.jsonl" not in names and "analysis/results/b_full_OLD/summary.json" not in names
    out = tmp_path / "bk"
    assert bk.main(["--full-ts", "T1", "--pilot-ts", "P1", "--out-dir", str(out), "--root", str(root)]) == 0
    arc = next(out.glob("bharat_full_runs_*.tar.gz"))
    with tarfile.open(arc) as t:
        assert "SHA256SUMS" in t.getnames() and "runs/a_full_T1.jsonl" in t.getnames()
    assert (root / "runs/a_full_T1.jsonl").read_text() == "x\n"             # originals untouched
