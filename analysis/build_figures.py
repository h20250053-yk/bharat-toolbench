"""Phase 4 charts and the pipeline diagram. Every chart: PNG at 2x (dpi 200 of a 100-dpi base size) + PDF, labelled axes with units, the SAME colour
for each model in every chart (analysis/results_data.COLOR). All numbers come from the run files (results_data). Needs matplotlib (viz venv).
Each function returns the facts its caption states, so captions.md is generated from the same numbers.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Patch, Rectangle  # noqa: E402

from . import results_data as D  # noqa: E402

_orig_errorbar = matplotlib.axes.Axes.errorbar


def _errorbar_nonneg(self, *args, **kwargs):          # interval limits can differ from the estimate by -1e-16 at 0% / 100%: clip to 0
    if kwargs.get("yerr") is not None:
        kwargs["yerr"] = np.maximum(np.asarray(kwargs["yerr"], dtype=float), 0.0)
    return _orig_errorbar(self, *args, **kwargs)


matplotlib.axes.Axes.errorbar = _errorbar_nonneg
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False, "axes.titlesize": 10,
                     "axes.titleweight": "bold", "figure.dpi": 100, "pdf.fonttype": 42})
FAIL_COLOR = {"success": "#2E7D32", "wrong_answer": "#EF6C00", "format_only": "#F9A825", "tool_argument_error": "#C62828", "missing_required_call": "#AD1457",
              "missing_booking": "#6A1B9A", "unsafe_action": "#000000", "output_truncated": "#546E7A", "malformed_model_output": "#90A4AE",
              "step_limit": "#8D6E63", "context_overflow": "#A1887F", "infra_error": "#CFD8DC", "other": "#BDBDBD"}
FAIL_LABEL = {"success": "success", "wrong_answer": "wrong answer", "format_only": "only the final block failed", "tool_argument_error": "bad tool arguments",
              "missing_required_call": "required call missing", "missing_booking": "booking missing", "unsafe_action": "unwanted booking / prohibited action",
              "output_truncated": "output cut at 2048 tokens", "malformed_model_output": "reply discarded / malformed", "step_limit": "step limit (8 turns)",
              "context_overflow": "context overflow", "infra_error": "infrastructure error", "other": "other"}


READABILITY: dict[str, dict[str, Any]] = {}      # per saved figure: smallest text size and what it becomes on a 390 px wide screen


def save(fig: plt.Figure, out: Path, name: str, foot: bool = True) -> list[str]:
    out.mkdir(parents=True, exist_ok=True)
    if D.FLAGGED and foot and any(D.DAGGER.strip() in t.get_text() for t in fig.findobj(matplotlib.text.Text)):      # only when a flagged model is drawn
        fig.canvas.draw()
        bb = fig.get_tightbbox(fig.canvas.get_renderer())            # inches; place the footnote just below everything already drawn
        fig.text(0.01, (bb.y0 - 0.12) / fig.get_figheight(), D.footnote(), fontsize=6.5, color="#555555", ha="left", va="top")
    fig.canvas.draw()
    bb2 = fig.get_tightbbox(fig.canvas.get_renderer())
    sizes = [t.get_fontsize() for t in fig.findobj(matplotlib.text.Text) if t.get_text().strip() and t.get_visible()]
    READABILITY[name] = {"min_font_pt": min(sizes) if sizes else None, "width_px_at_2x": int(bb2.width * 200),
                         "min_font_px_on_390px_phone": round(min(sizes) * 390 / (bb2.width * 72), 1) if sizes else None}      # px = pt * 390 / (width_in * 72)
    fig.savefig(out / f"{name}.png", dpi=200, bbox_inches="tight", facecolor="white")      # 2x of the 100-dpi base size
    fig.savefig(out / f"{name}.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return [f"{name}.png", f"{name}.pdf"]


def _legend_models(ax: plt.Axes, runs: list[D.Run], **kw: Any) -> None:
    ax.legend(handles=[Patch(facecolor=D.COLOR[r.key], label=D.DISPLAY[r.key]) for r in runs], frameon=False, **kw)


# ------------------------------------------------------------------------------------------------ 1. overall score (lenient vs strict)
def fig_overall(runs: dict[str, D.Run], tool_required: set[str], out: Path) -> dict[str, Any]:
    rs = D.ordered(runs)
    tab = D.overall_table(runs, tool_required)
    fig, ax = plt.subplots(figsize=(8, 4.2))
    x = np.arange(len(rs))
    for i, t in enumerate(tab):
        c = D.COLOR[t["key"]]
        ax.bar(i - 0.2, 100 * t["lenient_rate"], 0.4, color=c, edgecolor="black", linewidth=0.6)
        ax.errorbar(i - 0.2, 100 * t["lenient_rate"], yerr=[[100 * (t["lenient_rate"] - t["ci_lo"])], [100 * (t["ci_hi"] - t["lenient_rate"])]], color="black", capsize=3, lw=1)
        ax.bar(i + 0.2, 100 * t["strict_rate"], 0.4, color=c, edgecolor="black", linewidth=0.6, hatch="///", alpha=0.65)
        ax.text(i - 0.2, 100 * t["ci_hi"] + 1, f"{100 * t['lenient_rate']:.1f}", ha="center", fontsize=7.5)
    ax.axhline(100 * tab[0]["null_baseline_rate"], color="gray", ls="--", lw=1)
    ax.text(-0.45, 100 * tab[0]["null_baseline_rate"] + 6.5, "null baseline (never uses a tool, always asks)", ha="left", fontsize=7.5, color="gray")
    ax.set_xticks(x)
    ax.set_xticklabels([D.DISPLAY[r.key].replace(" (", "\n(") for r in rs], rotation=35, ha="right", fontsize=7.5)
    ax.set_ylabel("Task success (% of 375 items; 95% Wilson CI)")
    ax.set_ylim(0, max(100 * t["ci_hi"] for t in tab) + 8)
    ax.legend(handles=[Patch(facecolor="white", edgecolor="black", label="lenient (headline)"), Patch(facecolor="white", edgecolor="black", hatch="///", label="strict (no format recovery)")],
              frameon=False, loc="upper left")
    ax.set_title("Overall task success on BharatToolBench v2.1.0 (75 tasks x 5 languages)")
    files = save(fig, out, "fig1_overall_success")
    best, worst = max(tab, key=lambda t: t["lenient_rate"]), min(tab, key=lambda t: t["lenient_rate"])
    return {"files": files, "best": best["model"], "best_rate": best["lenient_rate"], "worst": worst["model"], "worst_rate": worst["lenient_rate"], "table": tab}


# ------------------------------------------------------------------------------------------------ 2. model x language heatmap
def fig_heatmap(runs: dict[str, D.Run], out: Path) -> dict[str, Any]:
    rs = D.ordered(runs)
    lt = {(r["key"], r["lang"]): r for r in D.language_table(runs)}
    M = np.array([[100 * lt[(r.key, l)]["rate"] for l in D.LANGS] for r in rs])
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    im = ax.imshow(M, cmap="YlGnBu", vmin=0, vmax=max(60, M.max()), aspect="auto")
    for i in range(len(rs)):
        for j in range(len(D.LANGS)):
            k = lt[(rs[i].key, D.LANGS[j])]
            ax.text(j, i, f"{M[i, j]:.0f}%\n({k['lenient']}/{k['n']})", ha="center", va="center", fontsize=7.5, color="white" if M[i, j] > 0.55 * M.max() else "black")
    ax.set_xticks(range(len(D.LANGS)))
    ax.set_xticklabels([D.LANG_NAME[l] for l in D.LANGS])
    ax.set_yticks(range(len(rs)))
    ax.set_yticklabels([D.DISPLAY[r.key] for r in rs])
    for i, r in enumerate(rs):                                    # model colour swatch next to each row label
        ax.add_patch(Rectangle((-0.62, i - 0.3), 0.1, 0.6, color=D.COLOR[r.key], clip_on=False, transform=ax.transData))
    ax.set_xlabel("Language of the request")
    ax.set_ylabel("Model")
    cb = fig.colorbar(im, ax=ax)
    cb.set_label("Task success (% of 75 items)")
    ax.set_title("Task success by model and language (lenient score)")
    files = save(fig, out, "fig2_model_language_heatmap")
    per_lang = {l: float(np.mean(M[:, j])) for j, l in enumerate(D.LANGS)}
    return {"files": files, "mean_by_lang": per_lang, "matrix": M.tolist(), "best_lang": max(per_lang, key=per_lang.get), "worst_lang": min(per_lang, key=per_lang.get)}


# ------------------------------------------------------------------------------------------------ 3. score vs model size
def fig_size(runs: dict[str, D.Run], tool_required: set[str], out: Path) -> dict[str, Any]:
    tab = {t["key"]: t for t in D.overall_table(runs, tool_required)}
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    moe = {"local_gpt_oss_20b", "local_gemma4_26b"}
    for line, keys, ls in (("Qwen2.5 (3B -> 14B)", ["local_qwen25_3b", "local_qwen25_14b"], "-"), ("Llama (3.2-3B -> 3.1-8B)", ["local_llama32_3b", "local_llama31_8b"], "--")):
        ks = [k for k in keys if k in tab]
        if len(ks) == 2:
            ax.plot([tab[k]["size_b"] for k in ks], [100 * tab[k]["lenient_rate"] for k in ks], color="black", ls=ls, lw=1.3, zorder=1, label=line)
    for k, t in tab.items():
        y = 100 * t["lenient_rate"]
        ax.errorbar(t["size_b"], y, yerr=[[100 * (t["lenient_rate"] - t["ci_lo"])], [100 * (t["ci_hi"] - t["lenient_rate"])]], color=D.COLOR[k], capsize=3, lw=1, zorder=2)
        ax.scatter(t["size_b"], y, s=90, color="white" if k in D.FLAGGED else D.COLOR[k], edgecolor="black", marker="^" if k in moe else "o", zorder=3)
        ax.annotate(D.DISPLAY[k], (t["size_b"], y), textcoords="offset points", xytext=(6, 5), fontsize=7.5)
    ax.set_xscale("log")
    ax.set_xticks([3, 5, 8, 14, 20, 26])
    ax.set_xticklabels(["3", "5", "8", "14", "20", "26"])
    ax.set_xlabel("Model size (billion parameters, total; log scale)   [triangles: mixture-of-experts with ~4B active]")
    ax.set_ylabel("Task success (% of 375 items; 95% Wilson CI)")
    ax.legend(frameon=False, loc="upper left")
    ax.set_title("Task success versus model size (lines connect sizes within the Qwen and Llama families)")
    files = save(fig, out, "fig3_score_vs_size")
    xs = [t["size_b"] for k, t in tab.items() if k not in D.FLAGGED]
    ys = [t["lenient_rate"] for k, t in tab.items() if k not in D.FLAGGED]
    rho, p = D.spearman(xs, ys) if len(xs) >= 4 else (float("nan"), float("nan"))
    fam = {}
    for f, keys in (("Qwen", ("local_qwen25_3b", "local_qwen25_14b")), ("Llama", ("local_llama32_3b", "local_llama31_8b"))):
        if all(k in tab for k in keys):
            fam[f] = {"from": tab[keys[0]]["lenient_rate"], "to": tab[keys[1]]["lenient_rate"], "sizes": (tab[keys[0]]["size_b"], tab[keys[1]]["size_b"])}
    return {"files": files, "spearman_rho": rho, "spearman_p": p, "families": fam}


# ------------------------------------------------------------------------------------------------ 4. English vs each language
def fig_gap(runs: dict[str, D.Run], out: Path) -> dict[str, Any]:
    rs = D.ordered(runs)
    gaps = D.gap_table(runs)
    fig, axes = plt.subplots(1, 4, figsize=(12, 4.0), sharey=True)
    for ax, lang in zip(axes, D.LANGS[1:]):
        for i, r in enumerate(rs):
            g = next(x for x in gaps if x["key"] == r.key and x["lang"] == lang)
            ax.bar(i, 100 * g["diff"], color=D.COLOR[r.key], edgecolor="black", linewidth=0.6)
            ax.errorbar(i, 100 * g["diff"], yerr=[[100 * (g["diff"] - g["lo"])], [100 * (g["hi"] - g["diff"])]], color="black", capsize=2.5, lw=1)
        ax.axhline(0, color="black", lw=0.8)
        ax.set_title(f"{D.LANG_NAME[lang]} minus English")
        ax.set_xticks([])
        ax.set_xlabel("models (colours as in the legend)")
    axes[0].set_ylabel("Change in task success vs English\n(percentage points; 95% paired bootstrap CI over 75 tasks)")
    fig.legend(handles=[Patch(facecolor=D.COLOR[r.key], label=D.DISPLAY[r.key]) for r in rs], loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.12))
    fig.suptitle("English-versus-each-language gap per model (negative = the language is harder than English)", fontweight="bold", fontsize=10)
    files = save(fig, out, "fig4_english_gap")
    mean_gap = {l: float(np.mean([g["diff"] for g in gaps if g["lang"] == l])) for l in D.LANGS[1:]}
    sig = [(g["model"], g["lang"], g["diff"]) for g in gaps if g["lo"] > 0 or g["hi"] < 0]
    return {"files": files, "mean_gap": mean_gap, "significant": sig, "gaps": gaps}


# ------------------------------------------------------------------------------------------------ 5. failure types
def fig_failures(runs: dict[str, D.Run], out: Path) -> dict[str, Any]:
    rs = D.ordered(runs)
    ft = D.failure_table(runs)
    order = ["success", "wrong_answer", "format_only", "tool_argument_error", "missing_required_call", "missing_booking", "unsafe_action", "output_truncated",
             "malformed_model_output", "step_limit", "context_overflow", "infra_error", "other"]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    left = np.zeros(len(rs))
    for cat in order:
        vals = np.array([100 * ft[r.key].get(cat, 0) / len(r.obs) for r in rs])
        if vals.sum() == 0:
            continue
        ax.barh(range(len(rs)), vals, left=left, color=FAIL_COLOR[cat], edgecolor="white", linewidth=0.5, label=FAIL_LABEL[cat])
        left += vals
    ax.set_yticks(range(len(rs)))
    ax.set_yticklabels([D.DISPLAY[r.key] for r in rs])
    for i, r in enumerate(rs):
        ax.add_patch(Rectangle((-0.045, i - 0.4), 0.025, 0.8, color=D.COLOR[r.key], transform=ax.get_yaxis_transform(), clip_on=False))
    ax.invert_yaxis()
    ax.set_xlabel("Share of the 375 items (%)  [one primary failure type per item]")
    ax.set_ylabel("Model")
    ax.set_xlim(0, 100)
    ax.legend(frameon=False, bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=7.5)
    ax.set_title("What went wrong: primary failure type per model (colour block at the label = model colour)")
    files = save(fig, out, "fig5_failure_types")
    return {"files": files, "table": ft}


# ------------------------------------------------------------------------------------------------ 6. unwanted bookings
def fig_unsafe(runs: dict[str, D.Run], out: Path) -> dict[str, Any]:
    rs = D.ordered(runs)
    ut = {u["key"]: u for u in D.unsafe_table(runs)}
    fig, ax = plt.subplots(figsize=(8, 4.0))
    for i, r in enumerate(rs):
        u = ut[r.key]
        v = 100 * u["items_with_unwanted_booking"] / u["n"]
        ax.bar(i, v, color=D.COLOR[r.key], edgecolor="black", linewidth=0.6)
        ax.text(i, v + 0.3, f"{u['items_with_unwanted_booking']}\n({u['unwanted_bookings']} bookings)", ha="center", fontsize=7.5)
    ax.set_xticks(range(len(rs)))
    ax.set_xticklabels([D.DISPLAY[r.key].replace(" (", "\n(") for r in rs], fontsize=7.5)
    ax.set_ylabel("Items with an unwanted booking (% of 375 items)")
    ax.set_ylim(0, max(100 * u["items_with_unwanted_booking"] / u["n"] for u in ut.values()) * 1.35 + 1)
    ax.set_title("Unsafe actions: bookings the user did not ask for (final environment state vs gold)")
    files = save(fig, out, "fig6_unwanted_bookings")
    return {"files": files, "table": list(ut.values())}


# ------------------------------------------------------------------------------------------------ 7. pipeline diagram (Mermaid + PNG/PDF via Graphviz)
MERMAID = """flowchart LR
    Q["User request<br/>(en / hinglish / hi / mr / gu)"] --> R["Runner<br/>system prompt + 6 tool schemas<br/>format tolerance (recorded)"]
    R --> M["Model<br/>(local, Ollama 0.40.18)"]
    M -- "tool call" --> E["Railway environment<br/>6 tools - synthetic, deterministic<br/>state reset per item"]
    E -- "observation (JSON)" --> M
    M -- "final reply + answer block" --> S["Scorer (no LLM judge)<br/>final state + answer block + tool process<br/>lenient (headline) and strict"]
    G["Gold<br/>generated by solvers,<br/>checked by an independent oracle"] -.-> S
    S --> O["task success 0/1<br/>failure labels, recoveries"]
"""


def pipeline_diagram(out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    (out / "pipeline.mmd").write_text(MERMAID, encoding="utf-8")
    dot = r'''digraph G { rankdir=LR; bgcolor="white"; fontname="DejaVu Sans"; nodesep=0.45; ranksep=0.55;
 node [shape=box, style="rounded,filled", fontname="DejaVu Sans", fontsize=11, color="#37474F", fillcolor="#ECEFF1", penwidth=1.4];
 edge [fontname="DejaVu Sans", fontsize=10, color="#37474F", penwidth=1.3];
 Q [label="User request\n(en / hinglish / hi / mr / gu)", fillcolor="#E3F2FD"];
 R [label="Runner\nsystem prompt + 6 tool schemas\nformat tolerance (recorded)", fillcolor="#FFF8E1"];
 M [label="Model\n(local, Ollama 0.40.18)", fillcolor="#E8F5E9"];
 E [label="Railway environment\n6 tools, synthetic, deterministic\nstate reset per item", fillcolor="#F3E5F5"];
 S [label="Scorer (no LLM judge)\nfinal state + answer block + tool process\nlenient (headline) and strict", fillcolor="#FFEBEE"];
 G [label="Gold\ngenerated by solvers,\nchecked by an independent oracle", fillcolor="#FFFFFF", style="rounded,dashed"];
 O [label="task success (0/1)\nfailure labels, recoveries", fillcolor="#E0F2F1"];
 Q -> R; R -> M; M -> E [label="tool call"]; E -> M [label="observation (JSON)"]; M -> S [label="final reply +\nanswer block"]; G -> S [style=dashed]; S -> O; }'''
    (out / "pipeline.dot").write_text(dot, encoding="utf-8")
    for fmt, extra in (("png", ["-Gdpi=200"]), ("pdf", [])):
        subprocess.run(["dot", f"-T{fmt}", *extra, str(out / "pipeline.dot"), "-o", str(out / f"pipeline.{fmt}")], check=True)
    return {"files": ["pipeline.mmd", "pipeline.dot", "pipeline.png", "pipeline.pdf"]}


# ============================================================================================ tool-selection charts (METRICS.md)
FUNNEL_STAGES = ["funnel_uses_tools", "funnel_right_tools", "funnel_right_arguments", "funnel_right_order", "funnel_task_success"]
FUNNEL_LABELS = ["uses a\ntool", "right\ntools", "right\narguments", "right\norder", "task\nsuccess"]


def fig_funnel(runs: dict[str, D.Run], tm: dict[str, dict[str, Any]], out: Path) -> dict[str, Any]:
    rs = D.ordered(runs)
    fig, axes = plt.subplots(2, 4, figsize=(12, 6.2), sharey=True)
    for ax, r in zip(axes.flat, rs):
        s = tm[r.key]
        vals = [100 * s[k]["value"] for k in FUNNEL_STAGES]
        los = [100 * (s[k]["value"] - s[k]["lo"]) for k in FUNNEL_STAGES]
        his = [100 * (s[k]["hi"] - s[k]["value"]) for k in FUNNEL_STAGES]
        ax.bar(range(5), vals, color=D.COLOR[r.key], edgecolor="black", linewidth=0.6)
        ax.errorbar(range(5), vals, yerr=[los, his], fmt="none", ecolor="black", capsize=2, lw=0.9)
        for i, v in enumerate(vals):
            ax.text(i, v + 2.5 + his[i], f"{v:.0f}", ha="center", fontsize=7.5)
        ax.set_xticks(range(5))
        ax.set_xticklabels(FUNNEL_LABELS, fontsize=7)
        ax.set_title(D.DISPLAY[r.key], fontsize=9)
        ax.set_ylim(0, 112)
    for ax in list(axes.flat)[len(rs):]:
        ax.set_visible(False)
    for ax in axes[:, 0]:
        ax.set_ylabel("Share of tool-needed items (%)")
    fig.suptitle("Tool-use funnel per model: uses a tool -> right tools -> right arguments -> right order -> task success (320 tool-needed items; 95% Wilson CI)", fontweight="bold", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    files = save(fig, out, "fig7_tool_funnel")
    return {"files": files, "stage_values": {r.key: [tm[r.key][k]["value"] for k in FUNNEL_STAGES] for r in rs}}


def fig_selection_vs_size(runs: dict[str, D.Run], tm: dict[str, dict[str, Any]], out: Path) -> dict[str, Any]:
    rs = D.ordered(runs)
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    moe = {"local_gpt_oss_20b", "local_gemma4_26b"}
    size = {r.key: r.size_b for r in rs}
    for line, keys, ls in (("Qwen2.5 (3B -> 14B)", ["local_qwen25_3b", "local_qwen25_14b"], "-"), ("Llama (3.2-3B -> 3.1-8B)", ["local_llama32_3b", "local_llama31_8b"], "--")):
        if all(k in tm for k in keys):
            ax.plot([size[k] for k in keys], [100 * tm[k]["selection_f1"]["value"] for k in keys], color="black", ls=ls, lw=1.3, zorder=1, label=line)
    for r in rs:
        s = tm[r.key]["selection_f1"]
        y = 100 * s["value"]
        ax.errorbar(size[r.key], y, yerr=[[100 * (s["value"] - s["lo"])], [100 * (s["hi"] - s["value"])]], color=D.COLOR[r.key], capsize=3, lw=1, zorder=2)
        ax.scatter(size[r.key], y, s=90, color="white" if r.key in D.FLAGGED else D.COLOR[r.key], edgecolor="black", marker="^" if r.key in moe else "o", zorder=3)
        ax.annotate(D.DISPLAY[r.key], (size[r.key], y), textcoords="offset points", xytext=(6, 5), fontsize=7.5)
    ax.set_xscale("log")
    ax.set_xticks([3, 5, 8, 14, 20, 26])
    ax.set_xticklabels(["3", "5", "8", "14", "20", "26"])
    ax.set_xlabel("Model size (billion parameters, total; log scale)   [triangles: mixture-of-experts]")
    ax.set_ylabel("Tool-selection F1 (%; mean over tool-needed items; 95% bootstrap CI)")
    ax.legend(frameon=False, loc="upper left")
    ax.set_title("Tool-selection accuracy versus model size")
    files = save(fig, out, "fig8_selection_vs_size")
    xs = [size[r.key] for r in rs if r.key not in D.FLAGGED]
    ys = [tm[r.key]["selection_f1"]["value"] for r in rs if r.key not in D.FLAGGED]
    rho, p = D.spearman(xs, ys) if len(xs) >= 4 else (float("nan"), float("nan"))
    return {"files": files, "spearman_rho": rho, "spearman_p": p}


def fig_selection_heatmap(runs: dict[str, D.Run], tm_lang: dict[str, dict[str, dict[str, Any]]], out: Path) -> dict[str, Any]:
    rs = D.ordered(runs)
    M = np.array([[100 * tm_lang[r.key][l]["selection_f1"]["value"] for l in D.LANGS] for r in rs])
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    im = ax.imshow(M, cmap="YlGnBu", vmin=0, vmax=max(60, np.nanmax(M)), aspect="auto")
    for i in range(len(rs)):
        for j, l in enumerate(D.LANGS):
            ax.text(j, i, f"{M[i, j]:.0f}", ha="center", va="center", fontsize=8, color="white" if M[i, j] > 0.55 * np.nanmax(M) else "black")
    ax.set_xticks(range(len(D.LANGS)))
    ax.set_xticklabels([D.LANG_NAME[l] for l in D.LANGS])
    ax.set_yticks(range(len(rs)))
    ax.set_yticklabels([D.DISPLAY[r.key] for r in rs])
    for i, r in enumerate(rs):
        ax.add_patch(Rectangle((-0.62, i - 0.3), 0.1, 0.6, color=D.COLOR[r.key], clip_on=False, transform=ax.transData))
    ax.set_xlabel("Language of the request")
    ax.set_ylabel("Model")
    cb = fig.colorbar(im, ax=ax)
    cb.set_label("Tool-selection F1 (%; 64 tool-needed items per cell)")
    ax.set_title("Tool-selection F1 by model and language")
    files = save(fig, out, "fig9_selection_heatmap")
    lang_mean = {l: float(np.nanmean(M[:, j])) for j, l in enumerate(D.LANGS)}
    return {"files": files, "mean_by_lang": lang_mean, "matrix": M.tolist()}


def fig_arg_vs_selection(runs: dict[str, D.Run], tm_lang: dict[str, dict[str, dict[str, Any]]], out: Path) -> dict[str, Any]:
    rs = D.ordered(runs)
    fig, axes = plt.subplots(1, 5, figsize=(15, 4.2), sharey=True)
    for ax, l in zip(axes, D.LANGS):
        for i, r in enumerate(rs):
            sel = 100 * tm_lang[r.key][l]["selection_error_rate"]["value"]
            arg = 100 * tm_lang[r.key][l]["argument_error_rate"]["value"]
            ax.bar(i, sel, color=D.COLOR[r.key], edgecolor="black", linewidth=0.6)
            ax.bar(i, arg, bottom=sel, color=D.COLOR[r.key], edgecolor="black", linewidth=0.6, hatch="///", alpha=0.6)
        ax.set_title(D.LANG_NAME[l])
        ax.set_xticks([])
        ax.set_xlabel("models (colours as in the legend)")
        ax.set_ylim(0, 105)
    axes[0].set_ylabel("Share of tool-needed items (%)")
    fig.legend(handles=[Patch(facecolor=D.COLOR[r.key], label=D.DISPLAY[r.key]) for r in rs] +
               [Patch(facecolor="white", edgecolor="black", label="solid: selection error (a required tool never called)"),
                Patch(facecolor="white", edgecolor="black", hatch="///", label="hatched: argument error (right tools, a required call wrong)")],
               loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.17), fontsize=8)
    fig.suptitle("Selection errors versus argument errors by language (stacked per model)", fontweight="bold", fontsize=10)
    files = save(fig, out, "fig10_selection_vs_argument_errors")
    pooled = {}
    for l in D.LANGS:
        pooled[l] = {"selection": float(np.mean([tm_lang[r.key][l]["selection_error_rate"]["value"] for r in rs])),
                     "argument": float(np.mean([tm_lang[r.key][l]["argument_error_rate"]["value"] for r in rs]))}
    return {"files": files, "mean_by_language": pooled}


# ------------------------------------------------------------------------------------------------ 11. language focus: the models above the 0% floor
def fig_language_focus(runs: dict[str, D.Run], out: Path) -> dict[str, Any]:
    rs = [runs[k] for k in D.LANGUAGE_FOCUS if k in runs]
    lang = {(x["key"], x["lang"]): x for x in D.language_table({r.key: r for r in rs})}
    fig, ax = plt.subplots(figsize=(8, 4.2))
    w = 0.8 / max(len(rs), 1)
    for j, r in enumerate(rs):
        for i, l in enumerate(D.LANGS):
            x = lang[(r.key, l)]
            xp = i - 0.4 + w * (j + 0.5)
            ax.bar(xp, 100 * x["rate"], w * 0.95, color=D.COLOR[r.key], edgecolor="black", linewidth=0.6, label=D.DISPLAY[r.key] if i == 0 else None)
            ax.errorbar(xp, 100 * x["rate"], yerr=[[100 * (x["rate"] - x["ci_lo"])], [100 * (x["ci_hi"] - x["rate"])]], color="black", capsize=2.5, lw=1)
            ax.text(xp, 100 * x["ci_hi"] + 1, f"{100 * x['rate']:.0f}", ha="center", fontsize=7)
    ax.set_xticks(range(len(D.LANGS)))
    ax.set_xticklabels([D.LANG_NAME[l] for l in D.LANGS])
    ax.set_ylabel("Task success (% of 75 items; 95% Wilson CI)")
    ax.set_ylim(0, 112)
    ax.legend(frameon=False, loc="upper center", ncol=3, fontsize=8)
    ax.set_title("Task success by language, for the three models well above the floor")
    files = save(fig, out, "fig11_language_focus", foot=False)
    return {"files": files, "keys": [r.key for r in rs]}


# ------------------------------------------------------------------------------------------------ blog versions (phone friendly: 6 in x 200 dpi = 1200 px wide, large text)
BLOG_FUNNEL_MODELS = ["local_llama32_3b", "local_qwen25_14b", "local_gpt_oss_20b", "local_gemma4_26b"]


def fig7_blog(runs: dict[str, D.Run], tm: dict[str, dict[str, Any]], out: Path) -> dict[str, Any]:
    rs = [runs[k] for k in BLOG_FUNNEL_MODELS if k in runs]
    fig, axes = plt.subplots(2, 2, figsize=(6, 6.2), sharex=True, sharey=True)
    labels = ["uses a tool", "right tools", "right arguments", "right order", "task success"]
    for ax, r in zip(axes.flat, rs):
        s = tm[r.key]
        vals = [100 * s[k]["value"] for k in FUNNEL_STAGES]
        ax.barh(range(5), vals, color=D.COLOR[r.key], edgecolor="black", linewidth=0.7)
        for i, v in enumerate(vals):
            ax.text(v + 2, i, f"{v:.0f}", va="center", fontsize=12.5, fontweight="bold")
        ax.set_yticks(range(5))
        ax.set_yticklabels(labels, fontsize=12.5)
        ax.set_title(D.DISPLAY[r.key], fontsize=12.5)
        ax.set_xlim(0, 118)
        ax.set_xticks([0, 50, 100])
        ax.tick_params(axis="x", labelsize=12.5)
    axes.flat[0].invert_yaxis()          # shared y axis: invert once, so the funnel reads top to bottom
    for ax in axes[1, :]:
        ax.set_xlabel("% of tool-needed items", fontsize=12.5)
    fig.suptitle("Where tool use breaks: share of tool-needed\nitems that survive each step", fontweight="bold", fontsize=12.5)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    files = save(fig, out, "fig7_blog_funnel", foot=False)
    return {"files": files, "models": [r.key for r in rs]}


def fig10_blog(runs: dict[str, D.Run], tm_lang: dict[str, dict[str, dict[str, Any]]], out: Path) -> dict[str, Any]:
    rs = D.ordered(runs)
    mean = {l: {"selection": float(np.mean([tm_lang[r.key][l]["selection_error_rate"]["value"] for r in rs])),
                "argument": float(np.mean([tm_lang[r.key][l]["argument_error_rate"]["value"] for r in rs]))} for l in D.LANGS}
    fig, ax = plt.subplots(figsize=(6, 5.2))
    x = np.arange(len(D.LANGS))
    sel = np.array([100 * mean[l]["selection"] for l in D.LANGS])
    arg = np.array([100 * mean[l]["argument"] for l in D.LANGS])
    ax.bar(x, sel, 0.62, color="#3B3B3B", edgecolor="black", linewidth=0.7, label="lost at tool selection\n(a required tool never called)")
    ax.bar(x, arg, 0.62, bottom=sel, color="#D0D0D0", edgecolor="black", linewidth=0.7, label="lost at arguments\n(right tools, a call wrong)")
    for i in range(len(D.LANGS)):
        ax.text(x[i], sel[i] / 2, f"{sel[i]:.0f}%", ha="center", va="center", fontsize=13, fontweight="bold", color="white")
        ax.text(x[i], sel[i] + arg[i] + 1.5, f"{arg[i]:.0f}%", ha="center", va="bottom", fontsize=12.5)
    ax.set_xticks(x)
    ax.set_xticklabels([D.LANG_NAME[l] for l in D.LANGS], fontsize=12.5)
    ax.set_ylim(0, 100)
    ax.set_ylabel("% of tool-needed items lost", fontsize=12.5)
    ax.tick_params(axis="y", labelsize=12.5)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=1, fontsize=12.5)
    ax.set_title("Where tool-needed items are lost, by language\n(mean over the reliable models)", fontsize=12.5)
    files = save(fig, out, "fig10_blog_selection_vs_arguments", foot=False)
    return {"files": files, "mean_by_language": mean, "models": [r.key for r in rs]}


def pipeline_phone(out: Path) -> dict[str, Any]:
    """Vertical pipeline for phones: <= 1200 px wide at 200 dpi, large font. The wide diagram (pipeline.*) stays for the paper."""
    dot = r'''digraph G { rankdir=TB; bgcolor="white"; fontname="DejaVu Sans"; nodesep=0.4; ranksep=0.5; pad=0.1;
 node [shape=box, style="rounded,filled", fontname="DejaVu Sans", fontsize=19, color="#37474F", fillcolor="#ECEFF1", penwidth=1.8, margin="0.15,0.12", width=3.3];
 edge [fontname="DejaVu Sans", fontsize=17, color="#37474F", penwidth=1.8];
 Q [label="1  User request\nen / hinglish / hi / mr / gu", fillcolor="#E3F2FD"];
 R [label="2  Runner\nprompt + 6 tool schemas", fillcolor="#FFF8E1"];
 M [label="3  Model (local)\nchooses a tool or answers", fillcolor="#E8F5E9"];
 E [label="4  Railway environment\nsynthetic, deterministic", fillcolor="#F3E5F5"];
 S [label="5  Scorer (no LLM judge)\nstate + answer + process", fillcolor="#FFEBEE"];
 G [label="Gold\n(solvers)", fillcolor="#FFFFFF", style="rounded,dashed", width=1.2];
 O [label="6  Result\nsuccess 0/1 + failure labels", fillcolor="#E0F2F1"];
 Q -> R; R -> M; M -> E [dir=both, label="  ↓ tool call\l  ↑ reply\l"]; E -> S [label=" final state"]; M -> S [label="  answer  ", constraint=false]; G -> S [style=dashed, constraint=false]; S -> O;
 {rank=same; S; G} }'''
    out.mkdir(parents=True, exist_ok=True)
    (out / "pipeline_phone.dot").write_text(dot, encoding="utf-8")
    for fmt, extra in (("png", ["-Gdpi=200"]), ("pdf", [])):
        subprocess.run(["dot", f"-T{fmt}", *extra, str(out / "pipeline_phone.dot"), "-o", str(out / f"pipeline_phone.{fmt}")], check=True)
    return {"files": ["pipeline_phone.dot", "pipeline_phone.png", "pipeline_phone.pdf"]}


# ------------------------------------------------------------------------------------------------ more blog versions (>= ~11 px text on a 390 px wide screen)
def _blog_note(fig: plt.Figure, width: int = 40, size: float = 13) -> None:
    """Dagger footnote for the blog figures, large enough for a phone, wrapped; placed below everything already drawn."""
    import textwrap
    if not D.FLAGGED:
        return
    txt = "\n".join(textwrap.wrap(D.footnote(), width))
    fig.canvas.draw()
    bb = fig.get_tightbbox(fig.canvas.get_renderer())
    fig.text(0.02, (bb.y0 - 0.12) / fig.get_figheight(), txt, fontsize=size, color="#444444", ha="left", va="top")


def fig1_blog(runs: dict[str, D.Run], tool_required: set[str], out: Path) -> dict[str, Any]:
    rs = D.ordered(runs)
    tab = D.overall_table(runs, tool_required)
    fig, ax = plt.subplots(figsize=(5.2, 7.0))
    y = np.arange(len(rs))
    for i, t in enumerate(tab):
        c = D.COLOR[t["key"]]
        ax.barh(i - 0.19, 100 * t["lenient_rate"], 0.36, color=c, edgecolor="black", linewidth=0.7)
        ax.errorbar(100 * t["lenient_rate"], i - 0.19, xerr=[[100 * (t["lenient_rate"] - t["ci_lo"])], [100 * (t["ci_hi"] - t["lenient_rate"])]], color="black", capsize=2.5, lw=1)
        ax.barh(i + 0.19, 100 * t["strict_rate"], 0.36, color=c, edgecolor="black", linewidth=0.7, hatch="///", alpha=0.6)
        ax.text(100 * t["ci_hi"] + 2.5, i - 0.19, f"{100 * t['lenient_rate']:.1f}%", va="center", fontsize=13, fontweight="bold", bbox=dict(facecolor="white", edgecolor="none", pad=0.6))
    nb = 100 * tab[0]["null_baseline_rate"]
    ax.axvline(nb, color="gray", ls="--", lw=1.3)
    ax.text(nb + 0.8, len(rs) - 0.35, f"null baseline {nb:.0f}%", fontsize=13, color="#555555", va="bottom")
    ax.set_yticks(y)
    ax.set_yticklabels([D.DISPLAY[r.key].replace(" (", "\n(") for r in rs], fontsize=13)
    ax.invert_yaxis()
    ax.set_xlim(0, 100 * max(t["ci_hi"] for t in tab) + 16)
    ax.set_xlabel("Task success, % of 375 items", fontsize=13)
    ax.tick_params(axis="x", labelsize=13)
    ax.legend(handles=[Patch(facecolor="white", edgecolor="black", label="lenient (headline)"), Patch(facecolor="white", edgecolor="black", hatch="///", label="strict (no format recovery)")],
              frameon=False, loc="upper right", fontsize=13)
    ax.set_title("Task success by model", fontsize=13.5, fontweight="bold")
    _blog_note(fig)
    files = save(fig, out, "fig1_blog_overall_success", foot=False)
    return {"files": files}


def fig6_blog(runs: dict[str, D.Run], out: Path) -> dict[str, Any]:
    rs = D.ordered(runs)
    ut = {u["key"]: u for u in D.unsafe_table(runs)}
    fig, ax = plt.subplots(figsize=(5.2, 5.8))
    for i, r in enumerate(rs):
        u = ut[r.key]
        ax.barh(i, u["items_with_unwanted_booking"], 0.62, color=D.COLOR[r.key], edgecolor="black", linewidth=0.7)
        ax.text(u["items_with_unwanted_booking"] + 1, i, f"{u['items_with_unwanted_booking']}", va="center", fontsize=13, fontweight="bold")
    ax.set_yticks(range(len(rs)))
    ax.set_yticklabels([D.DISPLAY[r.key].replace(" (", "\n(") for r in rs], fontsize=13)
    ax.invert_yaxis()
    top = max(u["items_with_unwanted_booking"] for u in ut.values())
    ax.set_xlim(0, top * 1.2 + 2)
    ax.set_xlabel("Items with a booking nobody asked for (of 375)", fontsize=13)
    ax.tick_params(axis="x", labelsize=13)
    ax.set_title("Unwanted bookings by model", fontsize=13.5, fontweight="bold")
    _blog_note(fig)
    files = save(fig, out, "fig6_blog_unwanted_bookings", foot=False)
    return {"files": files}


def fig11_blog(runs: dict[str, D.Run], out: Path) -> dict[str, Any]:
    rs = [runs[k] for k in D.LANGUAGE_FOCUS if k in runs]
    lang = {(x["key"], x["lang"]): x for x in D.language_table({r.key: r for r in rs})}
    fig, ax = plt.subplots(figsize=(5.6, 7.2))
    h = 0.24
    for j, r in enumerate(rs):
        for i, l in enumerate(D.LANGS):
            x = lang[(r.key, l)]
            yy = i + (j - 1) * h * 1.08
            ax.barh(yy, 100 * x["rate"], h, color=D.COLOR[r.key], edgecolor="black", linewidth=0.7, label=D.DISPLAY[r.key] if i == 0 else None)
            ax.errorbar(100 * x["rate"], yy, xerr=[[100 * (x["rate"] - x["ci_lo"])], [100 * (x["ci_hi"] - x["rate"])]], color="black", capsize=2, lw=0.9)
            ax.text(100 * x["ci_hi"] + 1.5, yy, f"{100 * x['rate']:.0f}", va="center", fontsize=11.5)
    ax.set_yticks(range(len(D.LANGS)))
    ax.set_yticklabels([D.LANG_NAME[l] for l in D.LANGS], fontsize=12.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 108)
    ax.set_xlabel("Task success, % of 75 items per language", fontsize=12)
    ax.tick_params(axis="x", labelsize=11.5)
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=1, fontsize=11.5)
    ax.set_title("Success by language\n(the three models above the floor)", fontsize=13.5, fontweight="bold")
    files = save(fig, out, "fig11_blog_language_focus", foot=False)
    return {"files": files}
