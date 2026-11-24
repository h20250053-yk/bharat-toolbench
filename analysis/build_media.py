"""Phase 4 media: examples.md (real traces from the runs) and an animated GIF that walks one real item through the pipeline.
All content is taken from the run files (query, tool calls, environment replies, final text, scores); the English gloss of a query is the English
query of the same task (`benchmark/languages/en.jsonl`). Text is drawn with Pillow + Raqm (shaped Devanagari/Gujarati), one font per script run.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from . import results_data as D

FONT_DIR = Path("/usr/share/fonts/truetype")
LATIN, MONO = FONT_DIR / "dejavu" / "DejaVuSans.ttf", FONT_DIR / "dejavu" / "DejaVuSansMono.ttf"
DEVA, GUJ = FONT_DIR / "noto" / "NotoSansDevanagari-Regular.ttf", FONT_DIR / "noto" / "NotoSansGujarati-Regular.ttf"
STAGES = ["Request", "Model", "Tool call", "Environment", "Answer", "Scorer"]
_FONTS: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    k = (str(path), size)
    if k not in _FONTS:
        _FONTS[k] = ImageFont.truetype(str(path), size, layout_engine=ImageFont.Layout.RAQM)
    return _FONTS[k]


def script_of(ch: str) -> str:
    o = ord(ch)
    return "deva" if 0x0900 <= o <= 0x097F else "guj" if 0x0A80 <= o <= 0x0AFF else "latin"


def runs(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for ch in text:
        s = script_of(ch) if not ch.isspace() and ch not in ",.;:!?()[]{}\"'-" else (out[-1][0] if out else "latin")
        if out and out[-1][0] == s:
            out[-1] = (s, out[-1][1] + ch)
        else:
            out.append((s, ch))
    return out


def width(text: str, size: int, mono: bool = False) -> float:
    return sum(font({"deva": DEVA, "guj": GUJ, "latin": MONO if mono else LATIN}[s], size).getlength(t) for s, t in runs(text))


def draw_text(d: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, size: int, fill: str = "#212121", mono: bool = False) -> None:
    x, y = xy
    for s, t in runs(text):
        f = font({"deva": DEVA, "guj": GUJ, "latin": MONO if mono else LATIN}[s], size)
        d.text((x, y), t, font=f, fill=fill)
        x += f.getlength(t)


def wrap(text: str, size: int, max_w: int, mono: bool = False) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        cur = ""
        for tok in para.split(" "):
            cand = tok if not cur else cur + " " + tok
            if width(cand, size, mono) <= max_w:
                cur = cand
            else:
                if cur:
                    lines.append(cur)
                while width(tok, size, mono) > max_w and len(tok) > 1:        # break an over-long token
                    k = max(1, int(len(tok) * max_w / width(tok, size, mono)))
                    lines.append(tok[:k])
                    tok = tok[k:]
                cur = tok
        lines.append(cur)
    return lines


# ================================================================================================ item choice
def best_run(runs_: dict[str, D.Run]) -> D.Run:
    return max(D.ordered(runs_), key=lambda r: r.rate(r.items())[0])


def calls_of(row: dict[str, Any]) -> list[dict[str, Any]]:
    traj = row.get("trajectory") or row.get("partial_trajectory") or []
    return [e for e in traj if e.get("event") == "tool_call"]


def english_query(task: str, root: Path = D.ROOT) -> str:
    for line in (root / "benchmark" / "languages" / "en.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r["semantic_task_id"] == task:
            return r["query"]
    return ""


def choose_story(runs_: dict[str, D.Run], gold: dict[str, Any]) -> tuple[D.Run, dict[str, Any]]:
    """A real success of the best model in Hindi or Marathi that shows the whole pipeline: station resolution, a search, then a booking or a lookup (3-6 calls, own final text)."""
    r = best_run(runs_)
    cands = []
    for tid in r.items():
        row = r.rows[tid]
        cs = calls_of(row)
        tools = {e["tool"] for e in cs}
        if row["language"] in ("hi", "mr") and r.ok(tid) and 3 <= len(cs) <= 6 and row["semantic_task_id"] != "T71" and (row.get("final_text") or "").split("<FINAL_ANSWER_JSON>")[0].strip():
            booked = bool(gold[row["semantic_task_id"]]["final_state"].get("expected_bookings"))
            full = {"resolve_station", "search_trains"} <= tools
            cands.append((not full, not booked, len(cs), tid))
    cands.sort()
    return r, r.rows[cands[0][3]]


def clip(obj: Any, n: int = 360) -> str:
    s = json.dumps(obj, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + " ..."


def answer_block(final_text: str) -> dict[str, Any] | None:
    import re
    m = re.search(r"<FINAL_ANSWER_JSON>(.*?)</FINAL_ANSWER_JSON>", final_text or "", re.S)
    try:
        return json.loads(m.group(1)) if m else None
    except json.JSONDecodeError:
        return None


# ================================================================================================ GIF
def frame(stage: int, title: str, body: list[tuple[str, int, str, bool]], footer: str, w: int = 1000, h: int = 560) -> Image.Image:
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    bw = (w - 40) // len(STAGES)
    for i, name in enumerate(STAGES):
        x = 20 + i * bw
        on = i == stage
        d.rounded_rectangle((x, 14, x + bw - 8, 54), radius=8, fill="#1565C0" if on else "#ECEFF1", outline="#37474F")
        tw = width(name, 15)
        draw_text(d, (int(x + (bw - 8 - tw) / 2), 24), name, 15, "white" if on else "#455A64")
    draw_text(d, (24, 70), title, 20, "#0D47A1")
    y = 104
    for text, size, color, mono in body:
        for line in wrap(text, size, w - 56, mono):
            if y > h - 54:
                break
            draw_text(d, (28, y), line, size, color, mono)
            y += int(size * 1.45)
        y += 6
    d.line((20, h - 40, w - 20, h - 40), fill="#CFD8DC")
    draw_text(d, (24, h - 32), footer, 13, "#607D8B")
    return im


def frame_phone(stage: int, title: str, body: list[tuple[str, int, str, bool]], footer: str, w: int = 600, h: int = 680) -> Image.Image:
    """Portrait frame for phones: the six stages in two rows of three, large text (a 600 px wide image shown on a ~390 px screen keeps text >= ~13 px)."""
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    bw = (w - 40) // 3
    for i, name in enumerate(STAGES):
        x, y = 20 + (i % 3) * bw, 14 + (i // 3) * 54
        on = i == stage or (isinstance(stage, tuple) and i in stage)
        d.rounded_rectangle((x, y, x + bw - 8, y + 44), radius=8, fill="#1565C0" if on else "#ECEFF1", outline="#37474F")
        tw = width(name, 22)
        draw_text(d, (int(x + (bw - 8 - tw) / 2), y + 8), name, 22, "white" if on else "#455A64")
    draw_text(d, (22, 124), title, 29, "#0D47A1")
    y = 176
    for text, size, color, mono in body:
        for line in wrap(text, size, w - 44, mono):
            if y > h - 60:
                break
            draw_text(d, (22, y), line, size, color, mono)
            y += int(size * 1.4)
        y += 10
    d.line((20, h - 48, w - 20, h - 48), fill="#CFD8DC")
    draw_text(d, (22, h - 40), footer, 19, "#607D8B")
    return im


def build_gif(runs_: dict[str, D.Run], gold: dict[str, Any], out: Path, phone: bool = False) -> dict[str, Any]:
    r, row = choose_story(runs_, gold)
    k = 1.6 if phone else 1.0                      # text-size factor
    frame_fn = frame_phone if phone else frame
    sz = lambda n: int(round(n * k))
    cl = (lambda o, n: clip(o, int(n * 0.55))) if phone else clip
    tid = row["task_id"]
    g = gold[row["semantic_task_id"]]
    calls = calls_of(row)
    en = english_query(row["semantic_task_id"])
    foot = f"{D.DISPLAY[r.key]} | item {tid} | real run" if phone else f"{D.DISPLAY[r.key]} | item {tid} | benchmark v2.1.0 | real run, nothing edited"
    frames: list[Image.Image] = []
    dur: list[int] = []
    f = frame_fn
    frames.append(f(0, f"1. The request ({D.LANG_NAME[row['language']]})", [(row["query"], sz(24), "#212121", False), ("English gloss: " + en, sz(15), "#546E7A", False)], foot)); dur.append(3800)
    sysnote = "The runner sends the request with a fixed system prompt and the schemas of six tools (resolve_station, search_trains, get_train_details, check_availability, get_fare, book_ticket)." if not phone else \
        "The runner sends the request, a fixed system prompt and six tool schemas to the model."
    sysbody = [(sysnote, sz(16), "#37474F", False)]
    if phone:
        sysbody.append(("resolve_station\nsearch_trains\nget_train_details\ncheck_availability\nget_fare\nbook_ticket", 25, "#1B5E20", True))
        sysbody.append(("The model answers with a tool call, or with its final answer.", 24, "#37474F", False))
    frames.append(f(1, "2. The model decides which tool to call", sysbody, foot)); dur.append(2800 if phone else 2400)
    for i, e in enumerate(calls[:6], 1):
        if phone:                                     # one frame per call: the call and the environment's reply together
            obs = e["observation"]
            frames.append(f((2, 3), f"Call {i} of {min(len(calls), 6)}: {e['tool']}", [
                ("TOOL CALL", 24, "#1B5E20", False), (f"{e['tool']}({clip(e['arguments'], 130)})", 27, "#1B5E20", True),
                ("ENVIRONMENT REPLY: " + ("ok" if obs["ok"] else f"error {obs['error']['code']}"), 24, "#2E7D32" if obs["ok"] else "#C62828", False),
                (clip(obs.get("data") if obs["ok"] else obs["error"], 170), 25, "#37474F", True)], foot)); dur.append(4800)
            continue
        frames.append(f(2, f"3.{i} Tool call {i}: {e['tool']}", [(f"{e['tool']}({cl(e['arguments'], 300)})", sz(17) if not phone else 23, "#1B5E20", True)], foot)); dur.append(2000)
        obs = e["observation"]
        frames.append(f(3, f"4.{i} Environment reply" + ("" if phone else " (deterministic, synthetic railway)"), [("ok" if obs["ok"] else f"error {obs['error']['code']}", sz(18), "#2E7D32" if obs["ok"] else "#C62828", False),
                                                                                              (cl(obs.get("data") if obs["ok"] else obs["error"], 520), sz(15) if not phone else 22, "#37474F", True)], foot)); dur.append(2400)
    blk = answer_block(row["final_text"]) or {}
    natural = (row["final_text"] or "").split("<FINAL_ANSWER_JSON>")[0].strip()
    body = [(natural, sz(20), "#212121", False)]
    if blk:
        body.append((f"answer block: status={blk.get('status')}, train={blk.get('selected_train')}, class={blk.get('selected_class')}, booking_ids={blk.get('booking_ids')}", sz(15) if not phone else 22, "#455A64", True))
    frames.append(f(4, "5. The final answer" if phone else "5. The final answer (in the language of the request)", body, foot)); dur.append(3600)
    sc, ss = row["score"], row.get("score_strict") or row["score"]
    exp_book = g["final_state"].get("expected_bookings") or []
    got_book = (row.get("state_snapshot") or {}).get("bookings") or []
    ok_c = "#2E7D32" if sc.get("task_success") else "#C62828"
    if phone:
        lines = [(f"final state: {len(got_book)} booking(s), gold expects {len(exp_book)}: {'match' if sc.get('state_success') else 'MISMATCH'}", 26, "#212121", False),
                 (f"answer block: {'ok' if sc.get('final_answer_parse') == 'ok' else sc.get('final_answer_parse')}", 26, "#212121", False),
                 (f"tool process (required calls, order): {'ok' if sc.get('process_success') else 'FAILED'}", 26, "#212121", False),
                 (f"TASK SUCCESS: {'YES' if sc.get('task_success') else 'NO'}", 38, ok_c, False),
                 (f"lenient {sc.get('task_success')}, strict {ss.get('task_success')}; format recoveries used: {len(sc.get('format_recoveries') or [])}", 23, "#455A64", False),
                 ("No LLM judge: the score compares state, answer block and tool process with generated gold.", 22, "#607D8B", False)]
    else:
        lines = [(f"final environment state: {len(got_book)} booking(s), gold expects {len(exp_book)}: {'match' if sc.get('state_success') else 'MISMATCH'}", 17, "#212121", False),
                 (f"answer block: {sc.get('final_answer_parse')} | tool process (required calls, order): {'ok' if sc.get('process_success') else 'FAILED'}", 17, "#212121", False),
                 (f"TASK SUCCESS: {'YES' if sc.get('task_success') else 'NO'}   (lenient {sc.get('task_success')}, strict {ss.get('task_success')}, format recoveries used: {len(sc.get('format_recoveries') or [])})", 19, ok_c, False),
                 ("No LLM judge: the score compares state, answer block and tool process with generated gold.", 14, "#607D8B", False)]
    frames.append(f(5, "6. The score", lines, foot)); dur.append(4200)
    out.mkdir(parents=True, exist_ok=True)
    pal = [f.convert("P", palette=Image.Palette.ADAPTIVE, colors=96) for f in frames]
    suffix = "_phone" if phone else ""
    path = out / f"pipeline_walkthrough{suffix}.gif"
    pal[0].save(path, save_all=True, append_images=pal[1:], duration=dur, loop=0, optimize=True, disposal=1)
    frames[-1].save(out / f"pipeline_walkthrough{suffix}_last_frame.png")
    return {"item": tid, "model": r.key, "frames": len(frames), "bytes": path.stat().st_size, "path": str(path), "size": frames[0].size}


# ================================================================================================ examples.md
def trace_md(title: str, r: D.Run, row: dict[str, Any], gold: dict[str, Any], note: str, root: Path = D.ROOT) -> list[str]:
    sc = row["score"]
    ss = row.get("score_strict") or sc
    L = [f"## {title}", "", f"- model: **{D.DISPLAY[r.key]}** (`{r.model}`), item `{row['task_id']}`, language: {D.LANG_NAME[row['language']]}, status `{row['status']}`",
         f"- query ({D.LANG_NAME[row['language']]}): {row['query']}", f"- English gloss (the English query of the same task): {english_query(row['semantic_task_id'], root)}", "", "Tool calls (as executed) and environment replies:", ""]
    calls = calls_of(row)
    if not calls:
        L.append("- (no tool call)")
    for i, e in enumerate(calls[:10], 1):
        o = e["observation"]
        L.append(f"{i}. `{e['tool']}({clip(e['arguments'], 200)})`  ->  " + ("ok: `" + clip(o.get("data"), 220) + "`" if o["ok"] else f"**error {o['error']['code']}**: {o['error']['message'][:100]}"))
    if len(calls) > 10:
        L.append(f"... ({len(calls) - 10} more calls)")
    ft = (row.get("final_text") or "").strip()
    blk = answer_block(ft)
    L += ["", "Final answer (model's own text):", "", "> " + (ft.split("<FINAL_ANSWER_JSON>")[0].strip() or "(none)").replace("\n", "\n> ")]
    if blk:
        L += ["", f"Answer block (authors' summary): status `{blk.get('status')}`, train `{blk.get('selected_train')}`, class `{blk.get('selected_class')}`, bookings `{blk.get('booking_ids')}`."]
    L += ["", f"Score: lenient **{'success' if sc.get('task_success') else 'failure'}**, strict {'success' if ss.get('task_success') else 'failure'}; labels: `{(sc.get('failure_labels') or [])[:4]}`; "
          f"recoveries: `{sorted({x['rule'] for x in sc.get('format_recoveries', [])})}`; final environment state: {len((row.get('state_snapshot') or {}).get('bookings') or [])} booking(s) "
          f"(gold expects {len(gold[row['semantic_task_id']]['final_state'].get('expected_bookings') or [])}).", "", f"What happened: {note}", ""]
    return L


def find_examples(runs_: dict[str, D.Run], gold: dict[str, Any]) -> list[tuple[str, D.Run, dict[str, Any], str]]:
    out: list[tuple[str, D.Run, dict[str, Any], str]] = []
    r, row = choose_story(runs_, gold)
    out.append(("Example 1: a clean success", r, row, f"{D.DISPLAY[r.key]} made {len(calls_of(row))} tool calls ({', '.join(e['tool'] for e in calls_of(row))}) and answered in {D.LANG_NAME[row['language']]}; the final environment state, the answer block and the tool process all match the gold."))
    # 2: a clear tool-SELECTION failure by Llama-3.1-8B (fallback Llama-3.2-3B): the required resolve_station is never called; the station names go straight into search_trains
    #    and the environment answers INVALID_STATION; the model ends with a clean cannot_complete block. Hindi first, then Marathi, Gujarati; lowest task id.
    ex2 = None
    for mk in ("local_llama31_8b", "local_llama32_3b"):
        m = runs_.get(mk)
        if not m or ex2:
            continue
        for lang in ("hi", "mr", "gu"):
            for t in m.items():
                row = m.rows[t]
                labels = row["score"].get("failure_labels") or []
                req = {c["tool"] for c in gold[row["semantic_task_id"]]["required_calls"] if not c.get("optional")}
                called = [e["tool"] for e in calls_of(row)]
                bad = [e for e in calls_of(row) if e["tool"] == "search_trains" and (e["observation"].get("error") or {}).get("code") == "INVALID_STATION"]
                if (row["language"] == lang and not m.ok(t) and row["status"] == "completed" and "resolve_station" in req and "resolve_station" not in called and bad
                        and any(x.startswith("status:expected_success_got_cannot_complete") for x in labels) and (row.get("final_text") or "").split("<FINAL_ANSWER_JSON>")[0].strip()):
                    ex2 = (m, row, bad[0])
                    break
            if ex2:
                break
    if ex2:
        m, row, e = ex2
        out.append(("Example 2: a tool-selection failure, `resolve_station` is never called", m, row, f"The task needs `resolve_station` before the search, but the model never called it: it passed the station names `{e['arguments'].get('source')}` -> `{e['arguments'].get('destination')}` "
                                                                                                  f"straight to `search_trains`, the environment returned INVALID_STATION, and the model gave up with a cannot-complete answer. Missing tool selection is the failure the benchmark is built to expose."))
    # 3: unwanted booking (weakest reliable model first)
    mids = sorted([x for x in D.ordered(runs_) if x.key not in D.FLAGGED], key=lambda x: x.rate(x.items())[0])
    ex3 = None
    for m in mids:
        for t in m.items():
            row = m.rows[t]
            o = m.obs[t]
            if "unexpected_booking" in o["secondary_tags"] and row["language"] != "en" and gold[row["semantic_task_id"]].get("prohibited_actions"):
                ex3 = (m, row)
                break
        if ex3:
            break
    if ex3:
        m, row = ex3
        out.append(("Example 3: an unwanted booking", m, row, "The user had forbidden or conditioned a booking, but the model called `book_ticket`; the final environment state holds a booking the gold does not expect, which the scorer counts as an unsafe action."))
    # 4: language contrast for Qwen2.5-14B: the English item succeeds, the Marathi (else Gujarati) item of the same task fails because a station lookup in that language
    #    returned STATION_NOT_FOUND; lowest task id
    ex4 = None
    m = runs_.get("local_qwen25_14b")
    if m:
        for lang in ("mr", "gu"):
            for t in m.items():
                row = m.rows[t]
                nf = [e for e in calls_of(row) if e["tool"] == "resolve_station" and (e["observation"].get("error") or {}).get("code") == "STATION_NOT_FOUND"]
                en_calls = calls_of(m.rows.get(f"{row['semantic_task_id']}_en", {})) if f"{row['semantic_task_id']}_en" in m.rows else []
                clean_en = not any((e["observation"].get("error") or {}).get("code") == "INVALID_TRAIN" for e in en_calls)       # prefer an English run without invented train ids
                if row["language"] == lang and not m.ok(t) and m.ok(f"{row['semantic_task_id']}_en") and row["status"] == "completed" and nf and clean_en:
                    ex4 = (m, row, nf[0])
                    break
            if ex4:
                break
    if ex4:
        m, row, nf = ex4
        en_row = m.rows[f"{row['semantic_task_id']}_en"]
        out.append((f"Example 4: the same task, English succeeds, {D.LANG_NAME[row['language']]} fails", m, row,
                    f"Same model ({D.DISPLAY[m.key]}) and same task `{row['semantic_task_id']}`: the English item succeeded with {len(calls_of(en_row))} tool call(s). In {D.LANG_NAME[row['language']]} the model passed the inflected form `{nf['arguments'].get('name')}` (with the Marathi case ending) "
                    f"to `resolve_station`, got STATION_NOT_FOUND, never reached the search and failed with labels `{(row['score'].get('failure_labels') or [])[:3]}`. For comparison, the English item of the same task is shown below."))
        L4 = trace_md("(English item of the same task, for comparison)", m, en_row, gold, "the English item of the same task, scored as a success.")
        out.append(("__append__", m, en_row, "\n".join(L4)))
    return out


def build(runs_: dict[str, D.Run], gold: dict[str, Any], out: Path) -> dict[str, Any]:
    gif = build_gif(runs_, gold, out)
    gif_phone = build_gif(runs_, gold, out, phone=True)
    hero_info = hero(runs_, gold, out)
    ex = find_examples(runs_, gold)
    L = ["# Real examples from the runs", "", "Every example is a row of a run file (nothing edited); the English gloss of a query is the English query of the same task. Tool calls are shown as executed (after the recorded format normalisation).", ""]
    for title, r, row, note in ex:
        if title == "__append__":
            L += ["### The English item of the same task (success), for comparison"] + note.split("\n")[1:]
            continue
        L += trace_md(title, r, row, gold, note)
    (out / "examples.md").write_text("\n".join(L), encoding="utf-8")
    return {"gif": gif, "gif_phone": gif_phone, "examples": [(t, r.key, row["task_id"]) for t, r, row, _ in ex if t != "__append__"]}


# ================================================================================================ hero image
LATIN_BOLD = FONT_DIR / "dejavu" / "DejaVuSans-Bold.ttf"


def _fit_lines(text: str, size: int, max_w: int) -> list[str]:
    return wrap(text, size, max_w)


def hero(runs_: dict[str, D.Run], gold: dict[str, Any], out: Path, task: str = "T35") -> dict[str, Any]:
    """Hero image: one booking request in all five languages on a stylised ticket / departure board. Text from benchmark/languages/*.jsonl; the counts on the
    tagline come from the gold file (tasks), the language list and the finished runs (models). Drawn at 2x (3200x1800) and saved also at 1x (1600x900)."""
    queries = {}
    for l in D.LANGS:
        for line in (D.ROOT / "benchmark" / "languages" / f"{l}.jsonl").read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r["semantic_task_id"] == task:
                queries[l] = r["query"]
    n_tasks = sum(1 for k in gold if not k.startswith("_"))
    tagline = f"{n_tasks} tasks \u00d7 {len(D.LANGS)} languages \u00d7 {len(runs_)} models"
    names = {"en": "English", "hinglish": "Hinglish", "hi": "\u0939\u093f\u0928\u094d\u0926\u0940", "mr": "\u092e\u0930\u093e\u0920\u0940", "gu": "\u0a97\u0ac1\u0a9c\u0ab0\u0abe\u0aa4\u0ac0"}
    S = 2
    W, H = 1600 * S, 900 * S
    im = Image.new("RGB", (W, H), "#0B1F3A")
    d = ImageDraw.Draw(im)
    for y in range(H):                                   # subtle vertical gradient
        t = y / H
        d.line((0, y, W, y), fill=(int(11 + 14 * t), int(31 + 30 * t), int(58 + 40 * t)))
    for x in range(0, W, 60 * S):                        # faint rails
        d.line((x, H - 40 * S, x + 30 * S, H - 40 * S), fill="#26456E", width=3 * S)
    d.line((0, H - 52 * S, W, H - 52 * S), fill="#2F5589", width=4 * S)
    d.line((0, H - 28 * S, W, H - 28 * S), fill="#2F5589", width=4 * S)
    # ticket
    tx0, ty0, tx1, ty1 = 70 * S, 60 * S, W - 70 * S, H - 90 * S
    d.rounded_rectangle((tx0, ty0, tx1, ty1), radius=30 * S, fill="#FFF6E0", outline="#E0C98F", width=3 * S)
    for yy in (ty0 + 160 * S,):                          # perforation line under the header
        for xx in range(tx0 + 30 * S, tx1 - 20 * S, 26 * S):
            d.ellipse((xx, yy - 3 * S, xx + 8 * S, yy + 5 * S), fill="#E0C98F")
    for cx, cy in ((tx0, ty0 + 160 * S), (tx1, ty0 + 160 * S)):       # ticket notches
        d.ellipse((cx - 22 * S, cy - 22 * S, cx + 22 * S, cy + 22 * S), fill="#0B1F3A")
    # header
    tf = font(LATIN_BOLD, 74 * S)
    d.text((tx0 + 50 * S, ty0 + 22 * S), "BharatToolBench", font=tf, fill="#0B1F3A")
    sf = font(LATIN, 27 * S)
    d.text((tx0 + 56 * S, ty0 + 112 * S), tagline, font=sf, fill="#5B4A1E")
    bf = font(LATIN_BOLD, 24 * S)
    badge = "TOOL-USE TEST  \u00b7  SYNTHETIC RAILWAY"
    bw = bf.getlength(badge)
    d.rounded_rectangle((tx1 - 50 * S - bw - 30 * S, ty0 + 40 * S, tx1 - 50 * S, ty0 + 100 * S), radius=14 * S, fill="#0B1F3A")
    d.text((tx1 - 50 * S - bw - 15 * S, ty0 + 56 * S), badge, font=bf, fill="#FFF6E0")
    # departure-board rows
    y = ty0 + 190 * S
    row_h = (ty1 - y - 20 * S) // len(D.LANGS)
    qsize = 28 * S
    for i, l in enumerate(D.LANGS):
        ry0 = y + i * row_h
        d.rounded_rectangle((tx0 + 36 * S, ry0 + 6 * S, tx1 - 36 * S, ry0 + row_h - 6 * S), radius=12 * S, fill="#13294B" if i % 2 == 0 else "#183258")
        draw_text(d, (tx0 + 62 * S, ry0 + row_h // 2 - 20 * S), names[l], 30 * S, "#F5C542")
        lines = _fit_lines(queries[l], qsize, tx1 - tx0 - 400 * S)
        total = len(lines) * int(qsize * 1.38)
        yy = ry0 + (row_h - total) // 2 + (7 * S if l in ("hi", "mr", "gu") else 0)     # Indic line boxes sit high: nudge down
        for ln in lines:
            draw_text(d, (tx0 + 300 * S, yy), ln, qsize, "#FFFFFF")
            yy += int(qsize * 1.38)
    out.mkdir(parents=True, exist_ok=True)
    im.save(out / "hero@2x.png")
    im.resize((1600, 900), Image.Resampling.LANCZOS).save(out / "hero.png")
    return {"task": task, "queries": queries, "tagline": tagline, "files": ["hero.png", "hero@2x.png"]}
