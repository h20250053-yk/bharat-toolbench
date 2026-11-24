"""Final-answer contract traced end to end: prompt -> (Ollama adapter) -> runner -> parser.

Pins the EXISTING parser behaviour (evaluation/final_answer.py is not changed): benchmark-compliant replies in every
language are accepted, non-compliant ones are rejected with the documented error, and the real qwen2.5:3b final
texts recorded in runs/local_qwen25_3b_pilot.jsonl are classified as missing_block. Offline: no Ollama, no keys."""
import json

import httpx
import pytest

from evaluation.final_answer import CLOSE, CONTRACT_PROMPT, OPEN, REQUIRED_KEYS, STATUSES, parse_final_answer
from evaluation.runner import SYSTEM_PROMPT

ANSWER = {"status": "success", "selected_train": "BTB103", "selected_class": "2A", "booking_ids": [],
          "requested_passengers": [], "notes": "fare lookup"}


def block(obj=None, raw=None):
    body = raw if raw is not None else json.dumps(obj if obj is not None else ANSWER, ensure_ascii=False)
    return f"{OPEN}\n{body}\n{CLOSE}"


# ---------------------------------------------------------------------------------------------------- prompt side
def test_system_prompt_carries_the_complete_contract():
    assert CONTRACT_PROMPT in SYSTEM_PROMPT and SYSTEM_PROMPT.endswith(CONTRACT_PROMPT)
    for tag in (OPEN, CLOSE):
        assert tag in CONTRACT_PROMPT
    for key in REQUIRED_KEYS:
        assert f'"{key}"' in CONTRACT_PROMPT
    for status in STATUSES:
        assert status in CONTRACT_PROMPT
    assert "same language as the user's request" in CONTRACT_PROMPT


# ---------------------------------------------------------------------------------------------------- accepted
@pytest.mark.parametrize("prose", [
    "The 2A fare on BTB103 is 3565.",
    "Train BTB103 mein 2A class ka fare 3565 rupaye hai.",
    "ट्रेन BTB103 में 2A क्लास का किराया ₹3565 है।",
    "ट्रेन BTB103 मध्ये 2A क्लासचे भाडे ₹३५६५ आहे.",
    "",
])
def test_compliant_reply_accepted_in_every_language(prose):
    p = parse_final_answer(f"{prose}\n{block()}")
    assert p["ok"] is True and p["error"] is None and p["answer"] == ANSWER and p["natural_text"] == prose.strip()


def test_crlf_line_endings_accepted():
    assert parse_final_answer(f"Fare is 3565.\r\n{OPEN}\r\n{json.dumps(ANSWER)}\r\n{CLOSE}\r\n")["ok"] is True


def test_markdown_fence_inside_tags_accepted():
    assert parse_final_answer(f"x\n{OPEN}\n```json\n{json.dumps(ANSWER)}\n```\n{CLOSE}")["ok"] is True


def test_non_ascii_values_and_answer_values_accepted():
    obj = dict(ANSWER, notes="किराया बताया", requested_passengers=["Vikram Singh"], answer_values={"seats_available": 4})
    p = parse_final_answer(block(obj))
    assert p["ok"] is True and p["answer"]["notes"] == "किराया बताया"


def test_last_complete_block_wins():
    first = dict(ANSWER, status="needs_clarification")
    p = parse_final_answer(f"draft {block(first)} final {block()}")
    assert p["ok"] is True and p["answer"]["status"] == "success"


# ---------------------------------------------------------------------------------------------------- rejected
@pytest.mark.parametrize("text,error", [
    ("The fare is 3565.", "missing_block"),
    (f"{OPEN}\n{json.dumps(ANSWER)}", "missing_block"),                                   # unclosed
    (json.dumps(ANSWER), "missing_block"),                                                 # bare JSON, no tags
    (f"<final_answer_json>\n{json.dumps(ANSWER)}\n</final_answer_json>", "missing_block"),  # wrong tag case
    (block(raw="{'status': 'success'}"), "malformed_json"),                                # single quotes
    (block(raw='{"status": "success",}'), "malformed_json"),                               # trailing comma
    (block(raw="[1, 2]"), "not_an_object"),
    (block({"status": "success"}), "missing_keys"),
    (block(dict(ANSWER, status="done")), "invalid_status"),
])
def test_non_compliant_reply_rejected(text, error):
    p = parse_final_answer(text)
    assert p["ok"] is False and p["error"].startswith(error)


# ---------------------------------------------------------------------------------------------------- recorded Qwen output
# Verbatim final texts from runs/local_qwen25_3b_pilot.jsonl (qwen2.5:3b). None contains the block.
RECORDED_QWEN_FINAL_TEXTS = {
    "T01_en": "The fare for 2A class on train BTB103 is 3565 INR.",
    "T01_hi": "ट्रेन BTB103 में 2A क्लास का किराया 3565 रुपये है।",
    "T04_en": "Cannot complete. There are no trains found for the given date and stations. Please provide another date or stations.",
    "T05_en": "I couldn't find the station named 'Vikram Singh'. Could you please provide the correct station name or station code?",
}


@pytest.mark.parametrize("task_id", sorted(RECORDED_QWEN_FINAL_TEXTS))
def test_recorded_qwen_final_texts_are_missing_block(task_id):
    p = parse_final_answer(RECORDED_QWEN_FINAL_TEXTS[task_id])
    assert p["ok"] is False and p["error"] == "missing_block"


@pytest.mark.parametrize("task_id", sorted(RECORDED_QWEN_FINAL_TEXTS))
def test_same_recorded_prose_with_a_compliant_block_would_parse(task_id):
    """The parser is not what rejects Qwen: the identical prose followed by a valid block is accepted."""
    status = "success" if task_id.startswith("T01") else "cannot_complete"
    obj = dict(ANSWER, status=status)
    assert parse_final_answer(f"{RECORDED_QWEN_FINAL_TEXTS[task_id]}\n{block(obj)}")["ok"] is True


# ---------------------------------------------------------------------------------------------------- adapter path
def test_ollama_adapter_and_runner_preserve_a_compliant_multilingual_block():
    """A compliant Marathi reply with CRLF and Devanagari digits, served by a mock Ollama, reaches the parser intact."""
    from agents import ollama_adapter
    from agents.registry import build_adapter
    from environment import RailwayEnv
    from evaluation.runner import RunnerConfig, run_item
    from evaluation.scorer import score
    from evaluation.selfcheck import gold_for

    ollama_adapter._MODEL_INFO_CACHE.clear()
    reply = f"ट्रेन BTB103 मध्ये 2A क्लासचे भाडे ₹३५६५ आहे.\r\n{OPEN}\r\n{json.dumps(ANSWER, ensure_ascii=False)}\r\n{CLOSE}"
    turns = [{"message": {"role": "assistant", "content": "", "tool_calls": [{"id": "c1", "function": {
                "name": "get_fare", "arguments": {"train_id": "BTB103", "travel_class": "2A"}}}]},
              "done": True, "done_reason": "stop", "prompt_eval_count": 1300, "eval_count": 25},
             {"message": {"role": "assistant", "content": reply}, "done": True, "done_reason": "stop",
              "prompt_eval_count": 1400, "eval_count": 90}]

    def handler(request):
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.40.18"})
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "qwen2.5:3b", "digest": "d", "details": {}}]})
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"capabilities": ["completion", "tools"]})
        return httpx.Response(200, json=turns.pop(0))

    factory = lambda: build_adapter("local_qwen25_3b", client=httpx.Client(transport=httpx.MockTransport(handler)))  # noqa: E731
    item = {"task_id": "T01_mr", "semantic_task_id": "T01", "language": "mr", "query": "ट्रेन BTB103 मध्ये 2A क्लासचे भाडे किती आहे?",
            "allowed_tools": ["resolve_station", "search_trains", "get_train_details", "check_availability", "get_fare", "book_ticket"]}
    row = run_item(item, factory, RailwayEnv(), RunnerConfig(sleep=lambda s: None), run_name="t")
    ollama_adapter._MODEL_INFO_CACHE.clear()
    assert row["final_text"] == reply  # byte-for-byte, including CRLF and Devanagari digits
    assert row["final_answer"]["ok"] is True and row["final_answer"]["answer"] == ANSWER
    sc = score(row, gold_for("T01"), row["state_snapshot"])
    assert sc["final_answer_parse"] == "ok" and sc["task_success"] is True, sc["failure_labels"]
