"""The worked example in the contract prompt (FORMAT_ROBUSTNESS decision 2): no answer leakage, one prompt for every model and language."""
import glob
import json
import re

from evaluation.final_answer import CLOSE, CONTRACT_PROMPT, OPEN, parse_final_answer
from evaluation.runner import SYSTEM_PROMPT, TOOL_SCHEMA_SHA256

EXAMPLE_TOKENS = ["BTB999", "BK9999", "Alpha Junction", "Beta Road", "Zed Quill", "3 December 2026"]


def example_block():
    m = re.search(re.escape(OPEN) + r"(.*?)" + re.escape(CLOSE), CONTRACT_PROMPT[CONTRACT_PROMPT.index("Example of a complete reply"):], re.S)
    return json.loads(m.group(1))


def test_the_example_is_a_valid_strict_block_and_is_plain_text_not_a_tool_call():
    text = CONTRACT_PROMPT[CONTRACT_PROMPT.index("Reply:") + len("Reply:"):]
    r = parse_final_answer(text)
    assert r["ok"] and r["answer"]["status"] == "success" and r["answer"]["selected_train"] == "BTB999"
    assert "plain text inside your reply, not a tool call" in CONTRACT_PROMPT and "<tool_call>" in CONTRACT_PROMPT.split("never wrap")[1][:80]


def test_the_example_leaks_no_task_content():
    blob = "".join(open(f, encoding="utf-8").read() for f in ["benchmark/semantic_tasks.json", "benchmark/gold_labels.json", "environment/data/trains.json",
                                                         "environment/data/stations.json", *glob.glob("benchmark/languages/*.jsonl")])
    for tok in EXAMPLE_TOKENS + ["Zed", "Quill", "Alpha", "Beta"]:
        assert tok not in blob, tok
    gold = json.load(open("benchmark/gold_labels.json", encoding="utf-8"))
    nums: set[int] = set()

    def walk(x):
        if isinstance(x, bool):
            return
        if isinstance(x, int):
            nums.add(x)
        elif isinstance(x, dict):
            [walk(v) for v in x.values()]
        elif isinstance(x, list):
            [walk(v) for v in x]
    for t, g in gold.items():
        if not t.startswith("_"):
            walk(g["final_answer"])
    ex = example_block()
    assert ex["answer_values"]["seats_remaining_at_end"] == 13 and 13 not in nums           # no gold answer equals an example value
    assert not set(ex["booking_ids"]) & {b["booking_id"] for g in gold.values() if isinstance(g, dict) and "expected_env_diff" in g for b in g["expected_env_diff"]["bookings"]}


def test_one_prompt_for_every_model_and_language():
    assert SYSTEM_PROMPT.endswith(CONTRACT_PROMPT)                      # the same constant is sent to every model; the query alone carries the language
    assert "user's language" in CONTRACT_PROMPT                         # the instruction to reply in the user's language is kept
    assert len(TOOL_SCHEMA_SHA256) == 64
