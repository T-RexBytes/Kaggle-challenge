"""Model roster and the local multi-model runner.

`kaggle_slug` is the exact slug from `kaggle b t models` (used on the server).
`proxy_id` is the name the local Model Proxy expects. They are kept apart
because the local proxy serves only a subset of the server catalog.
"""

import os
from dataclasses import dataclass

import kaggle_benchmarks as kbench

from .record import BOUNDARY_LEVELS


@dataclass(frozen=True)
class RosterModel:
    display: str
    kaggle_slug: str
    proxy_id: str


ROSTER = (
    RosterModel("GPT-6 Astra", "gpt-6-astra", "openai/gpt-6-astra"),
    RosterModel("GPT-5.6 Sol", "gpt-5.6-sol", "openai/gpt-5.6-sol"),
    RosterModel("Gemini 3.8 Flash", "gemini-3.8-flash", "google/gemini-3.8-flash"),
    RosterModel("Gemma 4 31B", "gemma-4-31b-it", "google/gemma-4-31b-it"),
    RosterModel("Claude Sonnet 5", "claude-sonnet-5-default", "anthropic/claude-sonnet-5@default"),
    RosterModel("Claude Haiku 4.5", "claude-haiku-4-5-20251001", "anthropic/claude-haiku-4-5@20251001"),
)


def failure_class(exc: Exception) -> str:
    """Map an exception to a rulebook section 29 failure class."""
    name = type(exc).__name__
    if name == "NotFoundError":
        return "MODEL_UNAVAILABLE"
    if name == "RateLimitError":
        return "RATE_LIMIT"
    if name == "ToolInvocationLimitExhausted":
        return "TASK_RUNTIME"
    if name in ("APIConnectionError", "APITimeoutError", "InternalServerError"):
        return "SERVER"
    return "UNKNOWN"


def _is_available(llm) -> tuple[bool, str]:
    """One-word ping outside any task, so it leaves no run file or JSON."""
    try:
        with kbench.chats.new("availability-probe"):
            llm.prompt("Reply with the single word OK.")
        return True, ""
    except Exception as exc:  # noqa: BLE001 - classified and reported, not hidden
        return False, f"{failure_class(exc)}: {str(exc).splitlines()[0][:120]}"


def _selected() -> list[tuple[str, object]]:
    """BOUNDARY_MODELS: unset -> default model; 'roster' -> all six; or comma list of slugs."""
    from kaggle_benchmarks.kaggle.models import load_model

    wanted = os.environ.get("BOUNDARY_MODELS", "").strip()
    if not wanted:
        return [(kbench.llm.name, kbench.llm)]
    by_slug = {m.kaggle_slug: m for m in ROSTER}
    slugs = [m.kaggle_slug for m in ROSTER] if wanted == "roster" else [s.strip() for s in wanted.split(",")]
    unknown = [s for s in slugs if s not in by_slug]
    if unknown:
        raise SystemExit(f"Unknown model slug(s) {unknown}. Roster: {list(by_slug)}")
    return [(by_slug[s].display, load_model(by_slug[s].proxy_id)) for s in slugs]


def run_local(task_fn) -> None:
    """Run a task for each selected model and boundary level.

    Without BOUNDARY_MODELS (the Kaggle server, or a plain local run) it runs the
    default model and lets any error propagate, so a failed run is recorded as
    failed. With BOUNDARY_MODELS it loops the roster and reports a summary.
    """
    levels = [l.strip() for l in os.environ.get("BOUNDARY_LEVELS", ",".join(BOUNDARY_LEVELS)).split(",")]
    if not os.environ.get("BOUNDARY_MODELS", "").strip():
        for level in levels:
            task_fn.run(kbench.llm, boundary=level)
        return
    summary = []
    for label, llm in _selected():
        ok, why = _is_available(llm)
        if not ok:
            print(f"[skip] {label}: {why}")
            summary.append((label, "MODEL_UNAVAILABLE (local proxy)", ""))
            continue
        done = []
        for level in levels:
            try:
                task_fn.run(llm, boundary=level)
                done.append(level)
            except Exception as exc:  # noqa: BLE001
                print(f"[fail] {label} / {level}: {failure_class(exc)}: {exc}")
                summary.append((label, failure_class(exc), level))
        if len(done) == len(levels):
            summary.append((label, "completed", ",".join(done)))

    print("\n=== local summary ===")
    for label, status, detail in summary:
        print(f"{label:<20} {status:<34} {detail}")
