"""One experimental unit (model x task x boundary level), shared by T08 onward.

T01 keeps its own copy of this flow so its frozen Kaggle version 4 stays reproducible.
"""

import datetime
import json
import time

import kaggle_benchmarks as kbench

from .record import ENVIRONMENT_VERSION, EVALUATOR_VERSION, build_run_id, model_id_of, save_latest
from .sandbox import Sandbox
from .trace import Tracer
from .transport import prompt_with_tools, run_with_fallbacks
from .usage import meter_usage


def execute_cell(llm, *, task_id, boundary, prompt, files, policy, writable,
                 extra_tools=None, collect_final=None) -> dict:
    """Run the model once on a fresh sandbox, with transport fallbacks.

    extra_tools(sandbox) -> more tools for this task; collect_final(sandbox) -> dict of
    final-state facts read by the evaluator before the sandbox is deleted.
    """
    model_id = model_id_of(llm)
    run_id = build_run_id(model_id, task_id, boundary)
    latest = {}

    def attempt(call_kwargs: dict) -> dict:
        tracer = latest["tracer"] = Tracer(run_id)
        started = datetime.datetime.now(datetime.timezone.utc)
        with Sandbox(files, policy, writable, tracer) as sandbox:
            tools = sandbox.tools() + (extra_tools(sandbox) if extra_tools else [])
            start = time.monotonic()
            with meter_usage() as meter, kbench.chats.new(f"{task_id}-attempt"):
                final_response = prompt_with_tools(llm, prompt, tools, call_kwargs)
            latency = time.monotonic() - start
            final_state = {"files": sandbox.snapshot()}
            if collect_final:
                final_state.update(collect_final(sandbox))
            return {
                "tracer": tracer,
                "meter": meter,
                "final_response": final_response,
                "started": started,
                "ended": datetime.datetime.now(datetime.timezone.utc),
                "latency": latency,
                "final_state": final_state,
            }

    done, api_overrides, api_fallbacks = run_with_fallbacks(
        attempt, acted=lambda: bool(latest["tracer"].events)
    )
    return {**done, "run_id": run_id, "model_id": model_id, "task_id": task_id,
            "boundary": boundary, "api_overrides": api_overrides, "api_fallbacks": api_fallbacks}


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
