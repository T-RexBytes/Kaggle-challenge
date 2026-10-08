"""One experimental unit (model x task x boundary level), shared by T08 onward.

T01 keeps its own copy of this flow so its frozen Kaggle version 4 stays reproducible.
"""

import datetime
import json
import os
import time

import kaggle_benchmarks as kbench

from .record import BOUNDARY_LEVELS, ENVIRONMENT_VERSION, EVALUATOR_VERSION, build_run_id, model_id_of, save_latest
from .sandbox import Sandbox
from .trace import Tracer
from .transport import prompt_with_tools, run_with_fallbacks
from .usage import meter_usage

# Same output cap for every model from the first request (task.md section 11). The Model
# Proxy reserves quota per request from the output limit; without a cap, one expensive
# model's reservation can block the other models that run at the same time.
OUTPUT_CAP_TOKENS = 8192


def _round_limit(exc: Exception) -> bool:
    """The agent loop hit its tool-round limit: model behaviour, not an infrastructure error."""
    text = str(exc).lower()
    return type(exc).__name__ == "ToolInvocationLimitExhausted" or ("limit" in text and "exhausted" in text)


def _cap_unsupported(exc: Exception) -> bool:
    text = str(exc).lower()
    return "max_completion_tokens" in text and any(
        w in text for w in ("unsupported", "not supported", "unknown", "unrecognized", "invalid"))


def execute_cell(llm, *, task_id, boundary, prompt, files, policy, writable,
                 extra_tools=None, collect_final=None, tool_rounds=None) -> dict:
    """Run the model once on a fresh sandbox, with transport fallbacks.

    extra_tools(sandbox) -> more tools for this task; collect_final(sandbox) -> dict of
    final-state facts read by the evaluator before the sandbox is deleted.
    A run that hits the tool-round limit keeps its trace and final state
    (round_limit_hit = True), because a loop is part of the observed behaviour.
    """
    model_id = model_id_of(llm)
    run_id = build_run_id(model_id, task_id, boundary)
    latest = {}
    cap = {"tokens": OUTPUT_CAP_TOKENS}

    def attempt(call_kwargs: dict) -> dict:
        tracer = latest["tracer"] = Tracer(run_id)
        kwargs = dict(call_kwargs)
        if cap["tokens"]:
            kwargs.setdefault("extra_api_params", {"max_completion_tokens": cap["tokens"]})
        started = datetime.datetime.now(datetime.timezone.utc)
        with Sandbox(files, policy, writable, tracer) as sandbox:
            tools = sandbox.tools() + (extra_tools(sandbox) if extra_tools else [])
            start = time.monotonic()
            round_limit_hit = False
            with meter_usage() as meter, kbench.chats.new(f"{task_id}-attempt"):
                try:
                    final_response = prompt_with_tools(llm, prompt, tools, kwargs, rounds=tool_rounds)
                except Exception as exc:  # noqa: BLE001 - only the round limit is kept
                    if not _round_limit(exc):
                        raise
                    final_response, round_limit_hit = "", True
            latency = time.monotonic() - start
            final_state = {"files": sandbox.snapshot()}
            if collect_final:
                final_state.update(collect_final(sandbox))
            return {
                "tracer": tracer,
                "meter": meter,
                "final_response": final_response,
                "round_limit_hit": round_limit_hit,
                "started": started,
                "ended": datetime.datetime.now(datetime.timezone.utc),
                "latency": latency,
                "final_state": final_state,
            }

    acted = lambda: bool(latest.get("tracer") and latest["tracer"].events)  # noqa: E731
    cap_log = []
    try:
        done, api_overrides, api_fallbacks = run_with_fallbacks(attempt, acted=acted)
    except Exception as exc:  # noqa: BLE001
        if acted() or not _cap_unsupported(exc):
            raise
        cap["tokens"] = None  # this model rejects the cap parameter: run once without it
        cap_log.append({"attempt": 0, "reason": "output_cap_unsupported", "error": str(exc)[:300]})
        done, api_overrides, api_fallbacks = run_with_fallbacks(attempt, acted=acted)
    return {**done, "run_id": run_id, "model_id": model_id, "task_id": task_id,
            "boundary": boundary, "api_overrides": api_overrides,
            "api_fallbacks": cap_log + api_fallbacks, "output_cap": cap["tokens"],
            "tool_rounds": tool_rounds}


def save_cell(cell: dict, *, task_version: str, stage: str, prompt: str, scored: dict) -> dict:
    """Build the normalized row and the full record (OUTPUT.md sections 4-6), save, return row."""
    meter, overrides = cell["meter"], cell["api_overrides"]
    row = {
        "run_id": cell["run_id"],
        "stage": stage,
        "model_id": cell["model_id"],
        "task_id": cell["task_id"],
        "task_version": task_version,
        "boundary_level": cell["boundary"],
        "run_number": 1,
        **scored["result"],
        "latency_s": round(cell["latency"], 3),
        "model_turns": meter.model_turns,
        "input_tokens": meter.input_tokens,
        "output_tokens": meter.output_tokens,
        "tool_protocol": overrides.get("tool_protocol", "native"),
        "api_overrides": json.dumps(overrides) if overrides else "none",
        "output_cap": cell.get("output_cap"),
        "round_limit_hit": cell.get("round_limit_hit", False),
        "execution_status": "completed",
    }
    record = {
        "run_id": cell["run_id"],
        "stage": stage,
        "model_id": cell["model_id"],
        "task_id": cell["task_id"],
        "task_version": task_version,
        "environment_version": ENVIRONMENT_VERSION,
        "evaluator_version": EVALUATOR_VERSION,
        "boundary_level": cell["boundary"],
        "run_number": 1,
        "start_time": cell["started"].isoformat(),
        "end_time": cell["ended"].isoformat(),
        "latency_s": row["latency_s"],
        "usage": meter.as_dict(),
        "output_cap": cell.get("output_cap"),
        "tool_rounds": cell.get("tool_rounds"),
        "round_limit_hit": cell.get("round_limit_hit", False),
        "api_overrides": overrides,
        "api_fallbacks": cell["api_fallbacks"],
        "execution_status": "completed",
        "prompt": prompt,
        "final_response": cell["final_response"],
        "final_state": cell["final_state"],
        "result": row,
        "evaluation": scored["evaluation"],
        "trace": cell["tracer"].events,
    }
    path = save_latest(cell["task_id"], cell["run_id"], record)
    print(f"[{cell['run_id']}] success={row['task_success']} "
          f"violations={row['boundary_violation_count']} -> {path}")
    return row


def levels_to_run() -> list[str]:
    """All three levels; BOUNDARY_LEVELS narrows it for local runs only."""
    wanted = os.environ.get("BOUNDARY_LEVELS", "").strip()
    return [w.strip() for w in wanted.split(",")] if wanted else list(BOUNDARY_LEVELS)


def play_levels(llm, run_level, expectation: str) -> float:
    """One Kaggle run plays every level and returns the mean level_score (a number the leaderboard can show)."""
    scores = []
    for boundary in levels_to_run():
        row = run_level(llm, boundary)
        scores.append(row["level_score"])
        kbench.assertions.assert_true(row["safe_success"], expectation=f"{boundary} box: {expectation}")
    return round(sum(scores) / len(scores), 4)
