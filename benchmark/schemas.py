"""Benchmark item / gold-trajectory schemas (DEFINITIONS ONLY in this phase).

Nothing here is used by the environment. A gold trajectory is NOT a rigid sequence: it is
  required calls  +  argument constraints  +  dependency edges  +  final-state / final-answer requirements.
Two calls with no edge between them may occur in either order; extra calls never change task success by themselves.
The gold generator and scorer that consume these schemas are later phases.
"""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Language = Literal["en", "hinglish", "hi", "mr", "gu"]
Category = Literal["single_tool", "sequential", "constraint", "booking", "recovery", "clarification", "invalid_input"]


class RequiredCall(BaseModel):
    call_id: str  # e.g. "c1"
    tool: str
    # exact canonical values the model must pass, e.g. {"travel_class": "3A"}
    required_args: dict[str, Any] = Field(default_factory=dict)
    # args whose value must be derived from an earlier call's output: {"train_id": "c2.trains[*].train_id"}
    args_from: dict[str, str] = Field(default_factory=dict)
    optional: bool = False  # e.g. resolve_station when a station code is unambiguous from the prompt
    # A required arg value may be an exact canonical value OR a matcher object {"resolves_to": "<station code>"}
    # (used for resolve_station.name, which is language-specific, so gold cannot hold one literal string).
    # Extra accepted values per arg (e.g. {"time_window": [null]} => omitting the window is also acceptable).
    arg_alternatives: dict[str, list[Any]] = Field(default_factory=dict)
    # Error code this call is EXPECTED to return (e.g. "CLASS_NOT_OFFERED"); None = the call must succeed.
    # Serialized only when set, so gold for tasks without expected errors is byte-identical to earlier versions.
    # A resolve_station matcher may also be {"resolves_ambiguous": ["NDLS", "NZM"]}: the name must resolve to
    # exactly these candidates (ambiguous=true), used by clarification tasks.
    expected_error: Optional[str] = None


class DependencyEdge(BaseModel):
    before: str  # call_id that must happen first
    after: str  # call_id that needs the result of `before`


class FinalStatePredicate(BaseModel):
    status: Literal["success", "cannot_complete", "needs_clarification"]
    allowed_train_ids: Optional[list[str]] = None  # set-valued gold when several answers are correct
    travel_class: Optional[str] = None
    expected_bookings: list[dict[str, Any]] = Field(default_factory=list)  # [] => no booking may exist
    # benchmark 3.0 (serialized only when set, so gold of tasks without them stays byte-identical):
    expected_cancellations: Optional[list[str]] = None  # PNRs that must end CANCELLED; None/absent => nothing may be cancelled
    expected_waitlist: Optional[list[dict[str, Any]]] = None  # waitlist entries (train, class, passenger); None/absent => none
    # 20-tool stage: {"tatkal_bookings"|"boarding_changes"|"meal_orders"|"tdr_claims"|"complaints": [...]}; absent kind => none may happen
    expected_effects: Optional[dict[str, list[dict[str, Any]]]] = None


class ProhibitedAction(BaseModel):
    """An action the USER explicitly forbade in the prompt (not an arbitrary extra call).

    Future scorer use: an extra harmless call that is NOT prohibited is never a failure by itself;
    a call matching a ProhibitedAction is a constraint violation. `tool` is forbidden outright when
    `match` is empty; otherwise only calls whose arguments contain every key/value of `match`.
    """

    tool: str
    match: dict[str, Any] = Field(default_factory=dict)
    prompt_phrase: str  # exact English phrase in the prompt that creates the prohibition (traceability)
    reason: str


class GoldSpec(BaseModel):
    """Language-independent; shared by the four variants of a semantic task."""

    semantic_task_id: str
    required_calls: list[RequiredCall]
    dependency_edges: list[DependencyEdge] = Field(default_factory=list)
    final_state: FinalStatePredicate
    min_calls: int
    # Language-independent expected structured final answer (values derived by code, never by an LLM).
    final_answer: dict[str, Any] = Field(default_factory=dict)
    # Machine-readable explicit prohibitions (empty for tasks where the user forbade nothing).
    forbidden_tools: list[str] = Field(default_factory=list)
    prohibited_actions: list[ProhibitedAction] = Field(default_factory=list)
    # Expected change of the mutable environment state vs. the baseline: {"bookings": [...], "availability_changes": {...}}.
    expected_env_diff: dict[str, Any] = Field(default_factory=dict)


class BenchmarkItem(BaseModel):
    """One language-specific item. Four items (en, hinglish, hi, mr) share one semantic_task_id and one GoldSpec."""

    task_id: str  # "T01_en"
    semantic_task_id: str  # "T01"
    language: Language
    query: str
    category: Category
    allowed_tools: list[str]
    tags: list[str] = Field(default_factory=list)
    author: Optional[str] = None
    reviewer: Optional[str] = None
    review_status: Literal["draft", "reviewed", "accepted"] = "draft"
