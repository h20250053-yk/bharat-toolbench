"""Blog charts (phone-sized): the three result charts used in the blog post.

Reads only the result tables in analysis/results_final/ (built by analysis/build_results.py) and writes PNGs to
analysis/figures_blog_v2/. Same colour for the same model as every other chart (analysis/results_data.COLOR).

    python -m analysis.blog_v2_figures
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "analysis" / "results_final"
OUT = ROOT / "analysis" / "figures_blog_v2"

NAME = {"Qwen2.5-3B": "Qwen2.5-3B", "Llama-3.2-3B": "Llama-3.2-3B", "Llama-3.1-8B": "Llama-3.1-8B",
        "DeepSeek-R1-8B (distill)": "DeepSeek-R1-8B", "Qwen2.5-14B": "Qwen2.5-14B", "gpt-oss-20B": "gpt-oss-20B",
        "Gemma-4-26B-A4B": "Gemma-4-26B", "Mistral-Small-3.2-24B": "Mistral-Small-3.2-24B"}
COLOR = {"Qwen2.5-3B": "#56B4E9", "Llama-3.2-3B": "#E69F00", "Llama-3.1-8B": "#D55E00", "DeepSeek-R1-8B": "#999999",
         "Qwen2.5-14B": "#0072B2", "gpt-oss-20B": "#009E73", "Gemma-4-26B": "#CC79A7", "Mistral-Small-3.2-24B": "#F0E442"}
ORDER = ["Qwen2.5-3B", "Llama-3.2-3B", "Llama-3.1-8B", "DeepSeek-R1-8B", "Qwen2.5-14B", "gpt-oss-20B", "Gemma-4-26B"]
EXCLUDED = "Mistral-Small-3.2-24B"          # most replies discarded by the serving software (see RESULTS.md)
BASELINE = 12.0                             # do-nothing baseline: never calls a tool, always asks (9 of 75 tasks)

# Sized for a phone: about 6.4 inches wide, so 14-point text stays readable when Substack shrinks the image.
plt.rcParams.update({"font.size": 14, "axes.titlesize": 16, "axes.titleweight": "bold", "axes.spines.top": False,
                     "axes.spines.right": False, "font.family": "DejaVu Sans"})


def _rows(name: str) -> list[dict[str, str]]:
    with open(RES / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _short(model: str) -> str:
    return NAME.get(model.replace(" †", ""), model)


def _save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{name}.png", dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def model_language_chart() -> None:
    """One row per model, one marker per language: rows sit far apart, markers within a row sit close together."""
    langs = [("en", "English", "o"), ("hinglish", "Hinglish", "s"), ("hi", "Hindi", "^"), ("mr", "Marathi", "D"),
             ("gu", "Gujarati", "v")]
    per_lang: dict[str, dict[str, float]] = {}
    for r in _rows("by_language.csv"):
        per_lang.setdefault(_short(r["model"]), {})[r["language"]] = float(r["pct"])
    overall = {_short(r["model"]): float(r["lenient_pct"]) for r in _rows("overall.csv")}
    models = [EXCLUDED] + sorted(ORDER, key=lambda m: overall[m])
    labels = {m: ("Mistral-24B" if m == EXCLUDED else m) for m in models}
    fig, ax = plt.subplots(figsize=(4.9, 7.4))
    for i, m in enumerate(models):
        excluded = m == EXCLUDED
        vals = [per_lang[m][code] for code, _, _ in langs]
        ax.hlines(i, min(vals), max(vals), color="#BBBBBB" if excluded else COLOR[m], lw=8, alpha=0.35)
        for (code, _, marker), v in zip(langs, vals):
            ax.scatter(v, i, marker=marker, s=95, color="white" if excluded else COLOR[m],
                       edgecolor="#888888" if excluded else "black", linewidth=1.0, zorder=3)
        ax.text(104, i, "excl." if excluded else f"{overall[m]:.0f}%", va="center", ha="left",
                fontsize=14, color="#777777" if excluded else "black", fontweight="normal" if excluded else "bold",
                clip_on=False)
    ax.axvline(BASELINE, color="#555555", ls="--", lw=1.5)
    ax.text(BASELINE + 1.5, len(models) - 0.45, "do-nothing\nbaseline (12%)", fontsize=12, color="#555555", va="bottom")
    ax.text(104, len(models) - 0.45, "overall", fontsize=12, color="#555555", va="bottom", ha="left", clip_on=False)
    ax.set_yticks(range(len(models)), [labels[m] for m in models])
    ax.set_ylim(-0.6, len(models) + 0.5)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Requests handled correctly\n(% of 75 per language)")
    handles = [plt.Line2D([], [], marker=mk, ls="", color="white", markeredgecolor="black", markersize=9, label=lab)
               for _, lab, mk in langs]
    ax.legend(handles=handles, loc="lower right", bbox_to_anchor=(1.0, 0.08), frameon=False, fontsize=12.5,
              title="Language", title_fontsize=12.5)
    ax.set_title("Models differ hugely;\nlanguages barely move them", loc="left")
    _save(fig, "blog_model_language")


def funnel_chart() -> None:
    """Where requests that need a tool get lost, for four representative models (one panel per model)."""
    stages = [("funnel stage 1: uses a tool", "uses a tool"), ("funnel stage 2: right tools", "picks the right tools"),
              ("funnel stage 3: right arguments", "fills in the details"), ("funnel stage 4: right order", "right order"),
              ("funnel stage 5: task success", "whole task correct")]
    vals: dict[tuple[str, str], float] = {}
    for r in _rows("tool_metrics_by_model.csv"):
        if r["value_pct"] not in ("", "n/a"):
            vals[(_short(r["model"]), r["metric"])] = float(r["value_pct"])
    models = ["Llama-3.2-3B", "Qwen2.5-14B", "gpt-oss-20B", "Gemma-4-26B"]
    fig, axes = plt.subplots(4, 1, figsize=(6.4, 12.4), sharex=True)
    for ax, m in zip(axes, models):
        ys = [vals[(m, key)] for key, _ in stages]
        ax.barh(range(5), ys, color=COLOR[m], edgecolor="black", linewidth=0.6, height=0.72)
        for j, y in enumerate(ys):
            ax.text(y + 2, j, f"{y:.0f}%", va="center", fontsize=13.5, fontweight="bold")
        ax.set_yticks(range(5), [lab for _, lab in stages])
        ax.get_yticklabels()[1].set_color("#C62828"); ax.get_yticklabels()[1].set_fontweight("bold")
        ax.invert_yaxis()
        ax.set_xlim(0, 118)
        ax.set_title(m, fontsize=15, loc="left")
    axes[-1].set_xlabel("% of the 320 requests that need a tool")
    fig.suptitle("Requests get lost when\nmodels pick their tools", x=0.02, ha="left", fontweight="bold", fontsize=17)
    fig.tight_layout()
    _save(fig, "blog_funnel")


def unwanted_chart() -> None:
    """Share of requests that end with a ticket nobody asked for."""
    rows = {_short(r["model"]): r for r in _rows("unsafe_bookings.csv")}
    fig, ax = plt.subplots(figsize=(6.4, 5.4))
    for i, m in enumerate(ORDER):
        r = rows[m]; v = 100 * int(r["items_with_unwanted_booking"]) / int(r["n"])
        ax.barh(i, v, color=COLOR[m], edgecolor="black", linewidth=0.6, height=0.72)
        label = f"{v:.0f}%" if v > 0 else "0% (never used a tool)"
        ax.text(v + 0.3, i, label, va="center", fontsize=13.5, fontweight="bold" if v > 0 else "normal")
    ax.set_yticks(range(len(ORDER)), ORDER)
    ax.invert_yaxis()
    ax.set_xlim(0, 20)
    ax.set_xticks([0, 5, 10, 15, 20])
    ax.set_xlabel("Requests ending with a booking\nnobody asked for (% of 375)")
    ax.set_title("Every model that acts books\ntickets nobody asked for", loc="left")
    _save(fig, "blog_unwanted")


def main() -> None:
    model_language_chart()
    funnel_chart()
    unwanted_chart()
    print("wrote", sorted(p.name for p in OUT.glob("*.png")))


if __name__ == "__main__":
    main()
