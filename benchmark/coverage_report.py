"""Coverage, tool-use and difficulty metrics for T01-T75. Run:  python -m benchmark.coverage_report
Writes benchmark/COVERAGE_REPORT.md (deterministic). Every number is COMPUTED from semantic_tasks.json, gold_labels.json and the
language files, except the behaviour labels in LABELS, which are hand-assigned semantic labels (documented below) used
only for reporting; they are not gold and never affect scoring.

Tool positions use each task's NON-OPTIONAL gold calls in gold order (a valid topological order of the dependency edges).
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .build_gold import GOLD_PATH, load_specs
from .semantic_overlap import MAX_JACCARD, analyse

BENCH = Path(__file__).resolve().parent
OUT = BENCH / "COVERAGE_REPORT.md"
LANGS = ["en", "hinglish", "hi", "mr", "gu"]
CATS = ["single_tool", "sequential", "constraint", "booking", "recovery", "clarification", "invalid_input"]
AB = {"resolve_station": "R", "search_trains": "S", "get_train_details": "D", "check_availability": "A", "get_fare": "F", "book_ticket": "B"}

# Hand-assigned behaviour labels (reporting only). Definitions:
#   conditional     the user states an if/else, only-if or fallback policy the agent must follow
#   comparison      the answer is chosen by ranking/optimising over >= 2 candidates
#   temporal        a time, date, weekday, overnight or relative-date fact changes the decision
#   multi_passenger more than one passenger is involved
#   multi_leg       more than one journey leg is involved
#   booking_request the user asked for a booking (whether or not the gold books)
LABELS: dict[str, set[str]] = {
    "conditional": {"T05", "T08", "T10", "T11", "T15", "T32", "T38", "T39", "T41", "T48", "T50",
                    "T61", "T70", "T73", "T75"},
    "comparison": {"T04", "T08", "T12", "T14", "T22", "T31", "T33", "T34", "T38", "T40",
                   "T51", "T52", "T53", "T57", "T60", "T64", "T65"},
    "temporal": {"T03", "T06", "T07", "T08", "T12", "T13", "T25", "T30", "T35", "T39", "T40", "T43", "T44",
                 "T52", "T55", "T56", "T57", "T60", "T62", "T63", "T65", "T66", "T67", "T73"},
    "multi_passenger": {"T13", "T15", "T33", "T42", "T46", "T48", "T50", "T61", "T65", "T68", "T71"},
    "multi_leg": {"T23", "T40", "T41"},
    "booking_request": {"T04", "T05", "T09", "T10", "T13", "T15", "T19", "T20", "T21", "T22", "T23", "T27", "T29", "T30", "T32", "T33",
                        "T35", "T36", "T38", "T39", "T41", "T42", "T43", "T46", "T47", "T48", "T49", "T50",
                        "T54", "T58", "T59", "T61", "T65", "T66", "T67", "T69", "T70", "T71", "T72", "T73", "T74", "T75"},
}
GROUPS = [("T01-T25", 1, 25), ("T26-T50", 26, 50), ("T51-T75", 51, 75)]  # design batches, reported side by side
DIFF_LABELS = ("conditional", "comparison", "temporal", "multi_passenger", "multi_leg")


def difficulty(n_calls: int, n_book: int, status: str, labels: set[str]) -> tuple[str, int]:
    """points = call-count band (0-1:0, 2-3:1, 4-6:2, 7+:3) + 1 if state mutates + 1 per reasoning label in DIFF_LABELS
    + 1 if the expected outcome is not plain success (agent must recognise failure/ambiguity).
    Easy 0-1, Medium 2-3, Hard 4-5, Very Hard >= 6."""
    pts = (0 if n_calls <= 1 else 1 if n_calls <= 3 else 2 if n_calls <= 6 else 3) + (n_book > 0) + len(labels & set(DIFF_LABELS)) + (status != "success")
    return ("Easy" if pts <= 1 else "Medium" if pts <= 3 else "Hard" if pts <= 5 else "Very Hard"), pts


def compute() -> dict:
    specs = {s.semantic_task_id: s for s in load_specs()}
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    rows = {l: [json.loads(x) for x in (BENCH / "languages" / f"{l}.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()] for l in LANGS}
    tasks = {}
    for t, s in specs.items():
        g = gold[t]
        req = [c for c in g["required_calls"] if not c.get("optional")]
        seq = "".join(AB[c["tool"]] for c in req)
        labels = {k for k, v in LABELS.items() if t in v}
        n_book = len(g["final_state"]["expected_bookings"])
        lvl, pts = difficulty(len(req), n_book, g["final_state"]["status"], labels)
        tasks[t] = {"category": s.category, "seq": seq, "collapsed": "".join(ch for i, ch in enumerate(seq) if i == 0 or seq[i - 1] != ch),
                    "n_calls": len(req), "n_optional": len(g["required_calls"]) - len(req), "n_book": n_book, "status": g["final_state"]["status"],
                    "forbidden": g["forbidden_tools"], "errors": sorted({c["expected_error"] for c in g["required_calls"] if c.get("expected_error")}),
                    "labels": labels, "difficulty": lvl, "points": pts, "kind": s.solver.kind}
    return {"tasks": tasks, "rows": rows, "overlap": analyse(specs, gold)}


def _table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    return "\n".join(out + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def render(d: dict) -> str:
    T = d["tasks"]
    grp = [(name, [t for t in T if lo <= int(t[1:]) <= hi]) for name, lo, hi in GROUPS]
    ALL = f"T01-{max(T)}"
    L = [f"# BharatToolBench coverage report ({ALL})", "",
         "Generated by `python -m benchmark.coverage_report` from the committed specs, gold and language files. "
         "Behaviour labels (conditional, comparison, temporal, multi-passenger, multi-leg, booking request) are hand-assigned "
         "reporting labels (definitions in `benchmark/coverage_report.py`); every other number is computed.", ""]
    # language balance
    n = {l: len(d["rows"][l]) for l in LANGS}
    drafts = sum(1 for l in LANGS for r in d["rows"][l] if r["review_status"] == "draft")
    reviewed = sum(1 for l in LANGS for r in d["rows"][l] if r["review_status"] == "reviewed")
    L += ["## Size and language balance", "", _table(["Semantic tasks", "Items", "English", "Hinglish", "Hindi", "Marathi", "Gujarati", "Human-reviewed items", "Items with review_status=draft"],
          [[len(T), sum(n.values()), n["en"], n["hinglish"], n["hi"], n["mr"], n["gu"], reviewed, drafts]]), ""]
    # categories
    cnt = lambda ids, c: sum(1 for t in ids if T[t]["category"] == c)  # noqa: E731
    L += ["## Category distribution", "", _table(["Category", *[g for g, _ in grp], ALL],
          [[c, *[cnt(ids, c) for _, ids in grp], cnt(T, c)] for c in CATS] + [["**total**", *[len(ids) for _, ids in grp], len(T)]]), ""]
    # behaviours
    beh = [("single-tool (exactly 1 required call)", [t for t in T if T[t]["n_calls"] == 1]),
           ("multi-tool (>= 2 required calls)", [t for t in T if T[t]["n_calls"] >= 2]),
           ("zero required calls (correct answer needs no tool)", [t for t in T if T[t]["n_calls"] == 0]),
           ("state-changing (gold books >= 1 ticket)", [t for t in T if T[t]["n_book"] > 0]),
           ("multi-booking (gold books >= 2 tickets)", [t for t in T if T[t]["n_book"] >= 2]),
           ("booking requested but must be WITHHELD (gold books 0)", [t for t in T if t in LABELS["booking_request"] and T[t]["n_book"] == 0]),
           ("explicit user prohibition (forbidden_tools)", [t for t in T if T[t]["forbidden"]]),
           ("expected tool error in gold", [t for t in T if T[t]["errors"]]),
           ("status needs_clarification", [t for t in T if T[t]["status"] == "needs_clarification"]),
           ("status cannot_complete", [t for t in T if T[t]["status"] == "cannot_complete"])]
    beh += [(f"{k} (label)", sorted(LABELS[k])) for k in ("conditional", "comparison", "temporal", "multi_passenger", "multi_leg")]
    L += ["## Behaviour coverage", "", _table(["Behaviour", *[g for g, _ in grp], ALL, "Tasks"],
          [[b, *[sum(1 for t in ids if t in gi) for _, gi in grp], len(ids), ", ".join(sorted(ids))] for b, ids in beh]), ""]
    # tools
    rows = []
    for tool, ab in AB.items():
        use = [t for t in T if ab in T[t]["seq"]]
        opt_only = [t for t in T if ab not in T[t]["seq"] and any(c["tool"] == tool for c in json.loads(GOLD_PATH.read_text(encoding="utf-8"))[t]["required_calls"])]
        fst = sum(1 for t in T if T[t]["seq"] and T[t]["seq"][0] == ab)
        lst = sum(1 for t in T if T[t]["seq"] and T[t]["seq"][-1] == ab)
        mid = sum(1 for t in T if ab in T[t]["seq"][1:-1])
        notcalled = (sum(1 for t in T if t in LABELS["booking_request"] and T[t]["n_book"] == 0) if tool == "book_ticket" else "-")
        rows.append([tool, len(use), len(opt_only), fst, mid, lst, notcalled])
    L += ["## Tool coverage", "",
          "Counts over non-optional gold calls. *optional-only* = the tool appears in gold only as an optional/alternative call. "
          "*intermediate* = the tool occurs strictly inside the sequence. *must NOT be called* is measurable only for `book_ticket` "
          "(booking requested but gold makes no booking); additionally the zero-call tasks listed above need no tool at all.", "",
          _table(["Tool", "Tasks (required)", "Optional-only", "First", "Intermediate", "Final", "Must NOT be called"], rows), ""]
    seqs = Counter(T[t]["seq"] or "(none)" for t in T)
    coll = Counter(T[t]["collapsed"] or "(none)" for t in T)
    lens = [T[t]["n_calls"] for t in T]
    L += ["## Tool-sequence patterns", "",
          "Letters: R resolve_station, S search_trains, D get_train_details, A check_availability, F get_fare, B book_ticket.", "",
          f"* distinct exact sequences: **{len(seqs)}**; distinct collapsed patterns (repeats merged, e.g. RRSFFB -> RSFB): **{len(coll)}**",
          f"* most common exact sequence: `{seqs.most_common(1)[0][0]}` ({seqs.most_common(1)[0][1]} tasks); "
          f"sequences used by exactly one task: {sum(1 for v in seqs.values() if v == 1)}",
          f"* required-call length: mean **{sum(lens) / len(lens):.2f}**, max **{max(lens)}** ({', '.join(t for t in T if T[t]['n_calls'] == max(lens))}), "
          f"min {min(lens)}", "",
          _table(["Exact sequence", "Tasks"], [[k, ", ".join(t for t in T if (T[t]["seq"] or "(none)") == k)] for k, _ in sorted(seqs.items(), key=lambda x: (-x[1], x[0]))]), ""]
    # difficulty
    dif = Counter(T[t]["difficulty"] for t in T)
    order = ["Easy", "Medium", "Hard", "Very Hard"]
    L += ["## Difficulty", "", "Rule (computed, `difficulty()`): points = required-call band (0-1 calls: 0, 2-3: 1, 4-6: 2, 7+: 3) "
          "+ 1 if the gold mutates state + 1 per label among conditional/comparison/temporal/multi-passenger/multi-leg "
          "+ 1 if the expected status is not `success`. Easy 0-1, Medium 2-3, Hard 4-5, Very Hard >= 6.", "",
          _table(["Level", *[g for g, _ in grp], ALL], [[o, *[sum(1 for t in gi if T[t]["difficulty"] == o) for _, gi in grp], dif[o]] for o in order]), ""]
    # per-task table
    L += ["## Per-task summary", "", _table(["Task", "Category", "Solver kind", "Required seq", "Opt", "Bookings", "Status", "Labels", "Difficulty (pts)"],
          [[t, T[t]["category"], T[t]["kind"], T[t]["seq"] or "-", T[t]["n_optional"], T[t]["n_book"], T[t]["status"],
            ", ".join(sorted(T[t]["labels"] - {"booking_request"})) or "-", f"{T[t]['difficulty']} ({T[t]['points']})"] for t in T]), ""]
    # overlap
    pairs = d["overlap"]["pairs"]
    L += [f"## Semantic overlap ({ALL}, global)", "",
          f"{len(pairs)} pairs checked; threshold {MAX_JACCARD}; maximum {pairs[0][0]:.2f}. Entity data (stations, trains, dates, passengers, "
          "classes) is excluded, so a data-swapped clone scores 1.0. Closest pairs:", "",
          _table(["Pair", "Jaccard"], [[f"{a} ~ {b}", f"{j:.2f}"] for j, a, b in pairs[:10]]), ""]
    return "\n".join(L) + "\n"


def main() -> int:
    OUT.write_text(render(compute()), encoding="utf-8")
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
